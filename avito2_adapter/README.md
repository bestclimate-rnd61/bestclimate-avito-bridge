# Avito 2 — isolated read-only adapter

This separate service is for the **personal Avito 2** account only. It is intentionally not connected to Avito 1 / Railway production.

## Render configuration

- Runtime: Node
- Root repository: `bestclimate-avito-bridge`
- Branch: `feature/avito2-readonly-20261101`
- Build command: `node --version`
- Start command: `node avito2_adapter/server.js`
- Plan: free (may spin down after inactivity)
- Auto-deploy: off
- Link Environment Group `avito2-private` manually using the Render Dashboard.

Expected variables:
- `AVITO2_CLIENT_ID`
- `AVITO2_CLIENT_SECRET`
- `AVITO2_WRITE_ENABLED=false`

Only `GET /health` is served. On startup, credentials are exchanged for a short-lived token and `GET /core/v1/accounts/self` verifies authentication. No account details or token are returned, stored, or logged. Never place API secrets in GitHub.

**Security:** The adapter has no content editing, message sending, autoload, or paid operations. If a previously disclosed client secret was saved, rotate it in Avito and replace the Render value.

A successful health response reports `auth=verified`. Merely seeing `configured=true` is not proof of authentication.
