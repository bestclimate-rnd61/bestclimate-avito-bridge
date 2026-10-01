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

## Full profile packaging
Packaging is a permanent workstream, not only Reels. Detailed plan: `instagram_profile_packaging_plan.md`.

Profile checklist before launch:
- avatar, searchable Name field, username, BIO, category, link/CTA;
- public/recommendation eligibility and Account Status;
- Professional Dashboard / creator-business tools;
- Highlights as navigation/funnel, never empty decoration;
- 3 pinned conversion assets;
- coherent feed cover system and Story system.

Planned Highlights: `СТАРТ`, `КЕЙСЫ`, `AI-БИЗНЕС`, `ИНСТРУМЕНТЫ`, `РАЗБОР`; later `ОБО МНЕ`, `FAQ`. Public Stories/Highlights remain approval-gated.

Feed cover families: FACE + CLAIM, SYSTEM, CASE. Keep 3–5 word mobile-readable titles, high contrast, one focal point, consistent typography and no visual clutter.

Recognizable content series: `AI за 60 секунд`, `Разбор бизнеса`, `Что автоматизировать первым`, `AI-ошибка недели`, `Кейс до/после`, `1 инструмент — 1 задача`.

Reels operating rules: original/meaningfully transformed content, no foreign-platform watermarks, 1080x1920, first-frame hook within 1–2 seconds, captions/on-screen text, clear cover, and CTA toward save/send/follow when appropriate. Measure retention/watch time, sends, saves, profile visits and follows. Trial Reels are a native/manual experiment only when available in the Instagram account; do not make Buffer automation depend on them.

## Publishing layer
- Buffer Free for sitkoalex.ai.business
- Content is staged in `instagram_content_queue.json`
- Worker: `instagram_buffer_bridge.py`
- Only items with `approved=true` are eligible for queueing/publishing.
- No unapproved public content, Stories, ad spend, or paid promotion.
- Launch queue contains 12 Reel drafts; all remain `approved=false` with empty `media_url`.
- Do not publish any draft until a valid video media URL exists and the user explicitly approves public publication.

### Launch content architecture
Three future pinned Reels are selected by role, but remain unpublished:
1. `ai-reel-001-start` — PIN 1 / POSITIONING.
2. `ai-reel-003-audit` — PIN 2 / LEAD MAGNET.
3. `ai-reel-011-case` — PIN 3 / PROOF; evidence-gated.

Production specs: `instagram_launch_production_specs.md`. PIN 2 must use a save/follow pre-launch CTA until the Telegram/SaleBot audit intake exists; PIN 3 requires real before/after data.

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
- 2026-10-01 09:07 MSK: `BUFFER_BRIDGE_DONE {channel: sitkoalex.ai.business, added: 0, skipped: 0, errors: 0}`; deployment SUCCESS.
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
- Funnel specification: `ai_audit_funnel_spec.md`.
- Public `РАЗБОР` CTA remains disabled until intake is implemented and tested end-to-end with a synthetic lead.
Existing Best Climate certificate funnel remains separate unless deliberately used for HVAC traffic.

## Manual-intervention policy
Ask the user only when genuinely required for login/password entry, 2FA, CAPTCHA/identity verification, OAuth approval unavailable to connectors, secure secret paste, physical local media upload, or explicit approval for public content/ad spend/irreversible settings.

When a manual action is needed, send one concise Gmail alert and continue all other cloud/preparation work in parallel. Do not repeat the same alert until blocker state changes.

## Cost policy
Prefer free tiers and reuse existing services safely. No paid upgrade without explicit approval.

## Recovery / fallback order
1. Direct API / connected app tool
2. Railway API/logs
3. GitHub configuration/code
4. Opera Browser Connector
5. User manual action only when unavoidable

Do not use TinyFish for this project.

## Next critical checkpoints
1. Verify Instagram UI Account Status/recommendation eligibility, Professional Dashboard/tools, Name/BIO/link alignment when browser access is available.
2. Implement/test the 7-question audit intake before enabling `РАЗБОР`.
3. Prepare premium Highlight cover masters and Story scripts without publishing.
4. Keep all 12 Reels unapproved until media exists and the user explicitly approves publication.
5. Continue scheduled Buffer worker verification.
