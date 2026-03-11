#!/usr/bin/env python3
"""Crawl B3 market data pages using Cloudflare Browser Rendering API."""

import asyncio
import os
import re
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/crawl"
POLL_INTERVAL = 5
POLL_TIMEOUT = 300  # 5 minutes
OUTPUT_DIR = Path("output")

CRAWL_PAYLOAD = {
    "url": "https://www.b3.com.br/pt_br/market-data-e-indices/indices/",
    "limit": 15,
    "formats": ["markdown"],
    "render": True,
    "gotoOptions": {"waitUntil": "networkidle2", "timeout": 60000},
    "rejectResourceTypes": ["image", "media", "font"],
    "options": {
        "includePatterns": ["https://www.b3.com.br/pt_br/market-data-e-indices/**"],
    },
}

TERMINAL_STATUSES = {
    "completed",
    "cancelled_due_to_timeout",
    "cancelled_due_to_limits",
    "cancelled_by_user",
    "errored",
}


def get_config() -> tuple[str, str]:
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not account_id or not api_token:
        print("Error: CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be set.")
        sys.exit(1)
    return account_id, api_token


def slugify(url: str) -> str:
    path = url.split("b3.com.br")[-1].strip("/")
    if not path:
        return "index"
    return re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-")


async def start_crawl(client: httpx.AsyncClient, url: str) -> str:
    print(f"Starting crawl job...")
    resp = await client.post(url, json=CRAWL_PAYLOAD)

    if resp.status_code == 401:
        print("Error: Authentication failed. Check your CLOUDFLARE_API_TOKEN.")
        sys.exit(1)
    if resp.status_code == 429:
        print("Error: Rate limited. Try again later.")
        sys.exit(1)

    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        print(f"Error: API returned failure: {data}")
        sys.exit(1)

    job_id = data["result"]
    print(f"Job created: {job_id}")
    return job_id


async def poll_job(client: httpx.AsyncClient, url: str) -> dict:
    start = time.monotonic()
    poll_url = f"{url}?limit=1"

    while True:
        elapsed = time.monotonic() - start
        if elapsed > POLL_TIMEOUT:
            print(f"Error: Polling timed out after {POLL_TIMEOUT}s.")
            sys.exit(1)

        resp = await client.get(poll_url)

        if resp.status_code == 404:
            print(f"  [{elapsed:5.0f}s] Job not ready yet, retrying...")
            await asyncio.sleep(POLL_INTERVAL)
            continue

        resp.raise_for_status()
        data = resp.json()
        result = data["result"]

        status = result["status"]
        finished = result.get("finished", 0)
        total = result.get("total", 0)
        print(f"  [{elapsed:5.0f}s] status={status}  finished={finished}/{total}")

        if status in TERMINAL_STATUSES:
            return result

        await asyncio.sleep(POLL_INTERVAL)


async def fetch_all_records(client: httpx.AsyncClient, url: str) -> list[dict]:
    """Fetch all records using cursor pagination."""
    records = []
    cursor = None

    while True:
        params = {"limit": 100}
        if cursor is not None:
            params["cursor"] = cursor

        resp = await client.get(url, params=params, timeout=120)
        resp.raise_for_status()
        result = resp.json()["result"]

        batch = result.get("records", [])
        records.extend(batch)

        cursor = result.get("cursor")
        if cursor is None or not batch:
            break

    return records


def save_records(records: list[dict]) -> tuple[int, int, int]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    success = 0
    skipped = 0
    errored = 0

    for rec in records:
        url = rec.get("url", "unknown")
        status = rec.get("status", "unknown")

        if status != "completed":
            label = "SKIP" if status in ("skipped", "disallowed") else "ERR"
            print(f"  [{label}] {url} ({status})")
            if status in ("skipped", "disallowed"):
                skipped += 1
            else:
                errored += 1
            continue

        markdown = rec.get("markdown", "")
        if not markdown:
            skipped += 1
            continue

        title = rec.get("metadata", {}).get("title", "")
        filename = f"{slugify(url)}.md"
        filepath = OUTPUT_DIR / filename

        header = f"# {title}\n\n> Source: {url}\n\n---\n\n" if title else f"> Source: {url}\n\n---\n\n"
        filepath.write_text(header + markdown, encoding="utf-8")
        print(f"  [OK]  {filename}")
        success += 1

    return success, skipped, errored


async def main():
    account_id, api_token = get_config()
    base = BASE_URL.format(account_id=account_id)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    t0 = time.monotonic()

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        job_id = await start_crawl(client, base)
        job_url = f"{base}/{job_id}"

        print("Polling for results...")
        result = await poll_job(client, job_url)

        if result["status"] != "completed":
            print(f"Warning: Job ended with status '{result['status']}'")

        print("Fetching records...")
        records = await fetch_all_records(client, job_url)

    print("\nSaving files...")
    success, skipped, errored = save_records(records)

    elapsed = time.monotonic() - t0
    browser_seconds = result.get("browserSecondsUsed", 0)

    print(f"\n{'='*50}")
    print(f"Total pages:          {result.get('total', len(records))}")
    print(f"Succeeded:            {success}")
    print(f"Skipped/disallowed:   {skipped}")
    print(f"Errored:              {errored}")
    print(f"Browser time used:    {browser_seconds:.1f}s")
    print(f"Total elapsed:        {elapsed:.1f}s")
    print(f"Output dir:           {OUTPUT_DIR.resolve()}")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
