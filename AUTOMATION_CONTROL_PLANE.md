# AI Automation Control Plane

## Goal
Run the user's Instagram / Best Climate / Avito automation stack with minimal manual intervention and minimal recurring cost.

## Operating principle
Prefer OAuth/API tokens and connected tools over usernames/passwords. Never store plaintext passwords, 2FA codes, payment data, or private secrets in this repository. Secrets belong only in provider secret stores such as Railway Variables. Manual user interaction should be requested only for actions that cannot be completed safely by connected tools (e.g. login/2FA/CAPTCHA/identity verification/secret paste).

## Control layer
- ChatGPT automation: orchestration, hourly checks, decisioning, reports, escalation only on real blockers.
- Opera Browser Connector: local browser inspection/navigation when the laptop is online.
- Gmail connector: alerts only when the user must act.

## Instagram AI profile
- Instagram: sitkoalex.ai.business
- Professional account; category: Автор цифрового контента
- Public profile; BIO configured
- User-approved portrait avatar with watch/lavalier is installed and visually confirmed
- As of 2026-09-30 late evening: 0 posts / 0 followers / 0 following
- Buffer account: separate from alexandr.sitko stack
- Buffer channel: sitkoalex.ai.business
- Buffer timezone: Moscow
- Buffer API key name: AI Instagram Buffer
- API key validity: 2026-09-30 -> 2027-09-30
- Buffer key permissions: user explicitly approved all 9 selected permissions
- Never expose the key in chat, GitHub, logs, or screenshots.

## Publishing layer
- Buffer Free for sitkoalex.ai.business
- Content is staged in `instagram_content_queue.json`
- Worker: `instagram_buffer_bridge.py`
- Only items with `approved=true` are eligible for queueing/publishing.
- No unapproved public content, ad spend, or paid promotion.
- Staged draft Reels (all approved=false, media_url empty): `ai-reel-001-start`, `ai-reel-002-team`, `ai-reel-003-audit`.
- Do not publish these drafts until video media URLs exist and the user explicitly approves public publication.

## Railway
Project: bestclimate-avito-bridge
Project ID: b54c084c-9395-4bb9-8cd5-883f3f6c8d68
Production env ID: 7910fd44-9fad-4484-86c4-24481c600322

### Instagram Buffer worker
Service: bestclimate-avito-bridge
Service ID: 345003ca-8c70-47b0-8f9b-bf4c712d3610
Purpose: isolated Buffer cron worker
Start: `python instagram_buffer_bridge.py`
Cron: `5 * * * *`
Restart policy: NEVER
Watch patterns: `instagram_buffer_bridge.py`, `instagram_content_queue.json`
Required variables:
- BUFFER_CHANNEL_NAME=sitkoalex.ai.business
- BUFFER_QUEUE_FILE=instagram_content_queue.json
- BUFFER_MAX_ADD_PER_RUN=10
- BUFFER_API_KEY=<SECRET IN RAILWAY ONLY>

Current verified state as of 2026-10-01 00:06 Moscow:
- `BUFFER_API_KEY` is present in Railway Variables.
- Railway config deploy completed successfully after the secret was saved.
- Service runs hourly cron `5 * * * *`.
- Temporary pre-deploy test hook removed; `preDeployCommand=[]`.
- Scheduled worker run started successfully and logged `BUFFER_BRIDGE_DONE` for channel `sitkoalex.ai.business` with `added=0`, `skipped=0`, `errors=0`.
- Three draft Reels exist but remain `approved=false`, so no item was queued or published.
- Continue hourly log verification and keep public publication gated on explicit approval plus valid media_url.

### Live Avito service
Service: bestclimate-avito-bridge-live
Service ID: 7fd7de90-333f-440d-97c1-8c97394918cf
Do not mix Instagram runtime or secrets into this service unless explicitly redesigned.

## Metricool separation
- Old profile alexandr.sitko remains in Metricool.
- Do not connect/mix sitkoalex.ai.business into the old Metricool brand if it risks account crossover or paid-plan pressure.
- Buffer is the low-cost control path for sitkoalex.ai.business.

## Lead funnel
Instagram -> Telegram -> subscription check @bestclimate_club -> 3,000 RUB certificate -> manager handoff.
Keep irreversible/high-risk changes gated: payment data, account ownership, 2FA, secrets, identity documents.

## Manual-intervention policy
Ask the user only when one of these is genuinely required:
1. login/password entry on provider page;
2. 2FA/SMS/email code;
3. CAPTCHA or identity verification;
4. OAuth approval that cannot be completed by available connector;
5. secure secret paste into provider secret store;
6. physical upload of a local media file where no API/cloud route is available;
7. explicit approval for new public content, ad spend, or irreversible settings.

When a manual action is needed, send one concise Gmail alert and continue all other cloud/preparation work in parallel. Do not repeat the same alert until the blocker state changes.

## Cost policy
- Prefer free tiers and reuse existing services safely.
- Avoid new paid services unless the free path is insufficient.
- Railway trial/Hobby should only be upgraded when needed for uptime; no paid upgrade without explicit user approval.

## Recovery / fallback order
1. Direct API / connected app tool
2. Railway API/logs
3. GitHub configuration/code
4. Opera Browser Connector
5. User manual action only when unavoidable

Do not use TinyFish for this project.

## Next critical checkpoint
Continue scheduled Buffer worker verification. In parallel, expand the staged 12-Reel launch system and three pinned-post concepts without approving or publishing them. The first three drafts establish the pillars: founder/real implementation, AI team/system, and AI audit/lead magnet.
