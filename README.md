# Best Climate Avito Bridge

Secure server-side bridge between ChatGPT/automation workflows and the Avito Business API for the **Бест Климат Ростов** account.

## Security

- Avito `client_id` and `client_secret` are **never committed to GitHub**.
- Secrets are stored only as Railway environment variables.
- Sensitive bridge endpoints require `X-Bridge-Secret` or `Authorization: Bearer <BRIDGE_SECRET>`.
- The bridge remains intentionally **read-only** for live Avito data; publishing or paid actions are not enabled automatically.
- `/avito/balance-watch` exposes only the low-balance state for automation and never exposes the wallet amount.

## Required environment variables

- `AVITO_CLIENT_ID`
- `AVITO_CLIENT_SECRET`
- `BRIDGE_SECRET`
- `AVITO_API_BASE` (default: `https://api.avito.ru`)

## Core endpoints

- `GET /health`
- `GET /avito/self`
- `GET /avito/balance`
- `GET /avito/balance-watch`
- `GET /avito/items`
- `GET /avito/item/{item_id}`
- `GET /avito/autoload/profile`
- `GET /avito/autoload/tree`
- `GET /avito/autoload/category/{slug}/fields`
- `GET /avito/autoload/ad-ids`

## Railway

Runtime: Python 3

Build command:

```bash
pip install -r requirements.txt
```

Start command used by the live service:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Healthcheck:

```text
/health
```

The production service tracks the repository `main` branch. Changes to repository files are intended to trigger a new source deployment; redeploying an old snapshot must not be treated as a source update.
