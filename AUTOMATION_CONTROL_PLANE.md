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
- Launch queue now contains 12 Reel drafts `ai-reel-001` through `ai-reel-012`; all remain `approved=false` with empty `media_url`.
- Do not publish any draft until a valid video media URL exists and the user explicitly approves public publication.

### Launch content architecture
Three future pinned Reels are selected by role, but remain unpublished:
1. `ai-reel-001-start` — PIN 1 / POSITIONING: who Alexander is, why this profile exists, real AI implementation in his own businesses. Primary profile-conversion asset.
2. `ai-reel-003-audit` — PIN 2 / LEAD MAGNET: 7-answer AI business audit, CTA toward the free diagnostic funnel. Primary lead-capture asset.
3. `ai-reel-011-case` — PIN 3 / PROOF: case-study framework problem -> baseline -> automation -> cost -> result -> failure/lesson. Primary trust/proof asset; publish only when the first real case has verifiable before/after data.

Production-ready shot lists, cover specs, edit rules and safety gates for all three pins are stored in `instagram_launch_production_specs.md`. PIN 2 must use a save/follow pre-launch CTA until the Telegram/SaleBot audit intake actually exists; PIN 3 remains evidence-gated until real before/after data is available.

Supporting launch sequence: 002 AI team/system, 004 lead handling 24/7, 005 content factory, 006 AI does not fix chaos, 007 cloud processes 24/7, 008 three implementation mistakes, 009 AI ROI metrics, 010 no-code architecture, 012 30-day roadmap. Keep claims factual and demonstrable.

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

Current verified state:
- `BUFFER_API_KEY` is present in Railway Variables.
- Railway config deploy completed successfully after the secret was saved.
- Service runs hourly cron `5 * * * *`.
- Temporary pre-deploy test hook removed; `preDeployCommand=[]`.
- Scheduled worker has logged `BUFFER_BRIDGE_DONE` for channel `sitkoalex.ai.business` with no errors and no unplanned additions while drafts are unapproved.
- 2026-10-01 04:08 MSK check: `BUFFER_BRIDGE_DONE {channel: sitkoalex.ai.business, added: 0, skipped: 0, errors: 0}`.
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
Instagram -> free AI business audit -> Telegram/SaleBot capture -> qualification -> manager/offer handoff.
Existing Best Climate certificate funnel can remain separate unless deliberately used for HVAC traffic; do not confuse the AI-business profile proposition with HVAC lead incentives.
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
Build the free 7-question AI audit intake specification and Telegram/SaleBot funnel logic before enabling a public lead CTA. Continue scheduled Buffer worker verification. Keep all 12 Reels unapproved until media exists and the user explicitly approves publication.
