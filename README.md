# Best Climate Avito Bridge

Secure server-side bridge between ChatGPT/automation workflows and the Avito Business API for the **Бест Климат Ростов** account.

## Security

- Avito `client_id` and `client_secret` are **never committed to GitHub**.
- Secrets must be stored only as Render environment variables.
- All bridge endpoints except `/health` require `X-Bridge-Secret` or `Authorization: Bearer <BRIDGE_SECRET>`.
- The first deployment is intentionally **read-only**. Write/publish/message actions are added only after the Avito account identity and API permissions are verified.

## Required environment variables

- `AVITO_CLIENT_ID`
- `AVITO_CLIENT_SECRET`
- `BRIDGE_SECRET`
- `AVITO_API_BASE` (default: `https://api.avito.ru`)

## Initial endpoints

- `GET /health`
- `GET /avito/self`
- `GET /avito/balance`
- `GET /avito/items`

## Render

Runtime: Python 3

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```
