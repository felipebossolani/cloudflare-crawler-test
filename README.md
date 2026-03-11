# cloudflare-crawler-test

Script Python que utiliza a [Cloudflare Browser Rendering API (endpoint /crawl)](https://developers.cloudflare.com/browser-rendering/rest-api/crawl-endpoint/) para crawlear páginas de Market Data da B3, renderizando JavaScript via headless browser e exportando o conteúdo em Markdown.

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
  [    0s] status=running  finished=0/15
  [    5s] status=running  finished=3/15
  [   10s] status=completed  finished=15/15
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
Total elapsed:        25.1s
Output dir:           /path/to/output
==================================================
```

## Custos

A Browser Rendering API cobra **$0.09 por hora** de uso de browser, com free tier:

| Plano | Uso gratuito | Browsers simultâneos |
|---|---|---|
| Workers Free | 10 min/dia | 3 |
| Workers Paid ($5/mês) | 10 horas/mês | 10 |

Crawls com `render: true` (padrão deste script) consomem tempo de browser. Um crawl de 15 páginas tipicamente usa menos de 1 minuto de browser time.

## Referências

- [Cloudflare Browser Rendering - Documentação](https://developers.cloudflare.com/browser-rendering/)
- [/crawl Endpoint](https://developers.cloudflare.com/browser-rendering/rest-api/crawl-endpoint/)
- [Pricing](https://developers.cloudflare.com/browser-rendering/pricing/)
- [Limites](https://developers.cloudflare.com/browser-rendering/limits/)
- [Changelog - Crawl endpoint](https://developers.cloudflare.com/changelog/post/2026-03-10-br-crawl-endpoint/)
