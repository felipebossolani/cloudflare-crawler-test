# cloudflare-crawler-test

Script Python que utiliza a [Cloudflare Browser Rendering API (endpoint /crawl)](https://developers.cloudflare.com/browser-rendering/rest-api/crawl-endpoint/) para crawlear páginas de Market Data da B3, renderizando JavaScript via headless browser e exportando o conteúdo em Markdown.

O endpoint `/crawl` foi lançado em open beta em 10 de março de 2026.

## O que faz

1. Envia um job de crawl para a API da Cloudflare apontando para `https://www.b3.com.br/pt_br/market-data-e-indices/indices/`
2. Faz polling assíncrono até o job finalizar (timeout de 5 minutos)
3. Busca todos os registros usando paginação por cursor
4. Salva cada página crawleada como arquivo `.md` no diretório `output/`

### Parâmetros do crawl

| Parâmetro | Valor | Descrição |
|---|---|---|
| `limit` | 15 | Máximo de páginas a crawlear |
| `formats` | `["markdown"]` | Formato de saída |
| `render` | `true` | Renderiza JS (headless browser) |
| `waitUntil` | `networkidle2` | Espera rede ficar idle antes de capturar |
| `rejectResourceTypes` | `image, media, font` | Ignora recursos desnecessários |
| `includePatterns` | `b3.com.br/pt_br/market-data-e-indices/**` | Restringe crawl a esse path |

## Pré-requisitos

- Python 3.10+
- Conta na Cloudflare com plano Workers (Free ou Paid)

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install httpx python-dotenv
```

## Configuração do `.env`

Copie o arquivo de exemplo e preencha com suas credenciais:

```bash
cp .env.example .env
```

O arquivo `.env` precisa de duas variáveis:

```
CLOUDFLARE_ACCOUNT_ID=your_account_id_here
CLOUDFLARE_API_TOKEN=your_api_token_here
```

### Como obter o Account ID

1. Acesse o [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. No menu lateral, vá em **Workers & Pages**
3. O **Account ID** aparece na barra lateral direita da página de overview
4. Copie e cole no `.env`

### Como obter o API Token

1. Acesse o [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Clique no ícone do seu perfil (canto superior direito) > **My Profile**
3. Vá na aba **API Tokens**
4. Clique em **Create Token**
5. Clique em **Create Custom Token** (Get started)
6. Configure o token:
   - **Token name**: um nome descritivo (ex: `browser-rendering-crawl`)
   - **Permissions**: selecione **Account** > **Browser Rendering** > **Edit**
   - **Account Resources**: selecione a conta onde o Workers está habilitado
7. Clique em **Continue to summary** > **Create Token**
8. Copie o token gerado e cole no `.env` (ele só é exibido uma vez)

## Execução

```bash
python crawl.py
```

O script exibe o progresso do job em tempo real e salva os resultados em `output/`.

Exemplo de saída:

```
Starting crawl job...
Job created: abc123-def456
Polling for results...
  [    0s] Job not ready yet, retrying...
  [    5s] Job not ready yet, retrying...
  [   30s] status=running  finished=0/15
  [   35s] status=running  finished=3/15
  [   40s] status=completed  finished=15/15
Fetching records...

Saving files...
  [OK]  pt-br-market-data-e-indices-indices.md
  ...

==================================================
Total pages:          15
Succeeded:            12
Skipped/disallowed:   2
Errored:              1
Browser time used:    45.3s
Total elapsed:        75.1s
Output dir:           /path/to/output
==================================================
```

> **Nota:** Os valores acima são ilustrativos. O tempo total varia com a carga do edge da Cloudflare e a complexidade das páginas. O browser time é o tempo efetivo de renderização no headless browser; o elapsed inclui criação do job, polling e download dos records.

## Gotchas

Coisas que a documentação não deixa claras e que descobri testando:

**Job retorna 404 nos primeiros ~30 segundos.** Depois de criar o job via POST, o GET com o job_id retorna 404 por um tempo até o job propagar internamente. O script já trata isso no polling (retry em loop), mas se você estiver escrevendo seu próprio client, precisa lidar com esse 404 como "ainda não está pronto" e não como erro real.

**O cursor da paginação é offset-based.** A doc menciona `cursor` como parâmetro de paginação, o que sugere um token opaco. Na prática é um offset numérico: `cursor=0`, `cursor=10`, `cursor=20`. O script usa `offset += len(batch)` pra avançar.

**O Markdown inclui lixo de navegação.** O output contém menus, rodapés, sidebars e todo o chrome do site junto com o conteúdo real. Não é conteúdo limpo pronto pra ingestão direta. Se o objetivo é alimentar um pipeline de RAG/LLM, vai precisar de pós-processamento pra extrair só o conteúdo relevante.

## Custos e limites

A Browser Rendering API cobra **$0.09 por hora** de uso de browser, com free tier:

| Plano | Uso gratuito | Browsers simultâneos |
|---|---|---|
| Workers Free | 10 min/dia | 3 |
| Workers Paid ($5/mês) | 10 horas/mês | 10 |

O endpoint `/crawl` tem limites adicionais no plano Free:

| Limite | Workers Free | Workers Paid |
|---|---|---|
| Jobs por dia | 5 | Sem limite* |
| Páginas por job | 100 | 100.000 |
| Tempo máximo do job | 7 dias | 7 dias |
| Retenção dos resultados | 14 dias | 14 dias |

\* Sujeito ao limite de browser time do plano.

Crawls com `render: true` (padrão deste script) consomem tempo de browser. Um crawl de 15 páginas tipicamente usa menos de 1 minuto de browser time. Com `render: false` é possível crawlear sites estáticos sem consumir browser time (gratuito durante o beta).

## Referências

- [Cloudflare Browser Rendering - Documentação](https://developers.cloudflare.com/browser-rendering/)
- [/crawl Endpoint](https://developers.cloudflare.com/browser-rendering/rest-api/crawl-endpoint/)
- [Pricing](https://developers.cloudflare.com/browser-rendering/pricing/)
- [Limites](https://developers.cloudflare.com/browser-rendering/limits/)
- [Changelog - Crawl endpoint](https://developers.cloudflare.com/changelog/post/2026-03-10-br-crawl-endpoint/)