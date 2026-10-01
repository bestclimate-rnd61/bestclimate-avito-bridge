# AI Automation Control Plane

## Goal
Run the user's Instagram / Best Climate / Avito automation stack with minimal manual intervention and minimal recurring cost.

## MASTER TЗ — AI INSTAGRAM SITKOALEX

This MASTER TЗ is the permanent operating instruction for `@sitkoalex.ai.business`.

### Main goal
Turn Instagram `@sitkoalex.ai.business` into a strong personal AI-business brand focused on:
- audience growth;
- reach;
- inbound leads;
- sales of AI implementation services;
- Alexander Sitko's personal brand;
- later monetization.

### Core rule
A result counts only when something actually changed and can be verified externally.

Do NOT count the following as a result by themselves:
- plans;
- ideas;
- lists;
- specifications;
- scripts;
- internal documents;
- drafts;
- automation settings;
- “prepared” / “analyzing”.

Order of work: DO -> VERIFY -> REPORT.

Priority: Instagram profile -> content -> funnel -> analytics -> optimization.

Each work cycle must produce either:
A) a real visible result; or
B) a concrete technical blocker + one exact action required from Alexander + continuation of all other tasks in parallel.

Visible results include:
- published Reel/post/Story;
- changed BIO/name/category;
- added working profile link;
- created Highlight;
- pinned content;
- connected and tested funnel;
- working CTA;
- verified lead;
- visible packaging improvement;
- measurable optimization based on published-content analytics.

Never say “done” until verified. Never invent account state. Never treat internal preparation as visible progress. Never wait for Alexander if other safe work can continue.

### User authorization for organic publishing
The user explicitly authorized autonomous publication of organic content to `@sitkoalex.ai.business` through the connected Buffer account **without separate approval for each post**, provided the content follows this MASTER TЗ.

Still requires separate explicit approval:
- paid advertising;
- any spend;
- password changes;
- 2FA changes;
- account ownership changes;
- payment/tax/billing data changes.

### Content rules
Optimize for retention -> saves -> shares -> follows -> leads.

Core content pillars:
- AI in real business;
- automation;
- AI employees;
- leads and sales;
- real Alexander Sitko business cases;
- Avito;
- Instagram;
- websites;
- bots;
- analytics;
- implementation mistakes;
- ROI from AI;
- entrepreneur journey.

Every Reel should have:
- hook in first 1–2 seconds;
- one strong idea;
- dynamic edit;
- large captions;
- clear cover;
- CTA;
- caption;
- SEO keywords;
- final pre-publish check.

Do not copy competitors. Use competitors only to understand mechanics.

No fake reviews, numbers, cases or promises. The brand is Alexander Sitko, a real entrepreneur implementing AI in his own projects.

### Continuous improvement permission
The system may proactively add new ideas, workflows, optimizations and quality/speed improvements when they strengthen results, provided they:
- stay within this MASTER TЗ;
- do not add unnecessary paid services;
- do not create spend without approval;
- do not weaken safety, truthfulness or account ownership controls;
- are measured by visible progress rather than planning volume.

### Reporting format
Only report:
- ✅ What actually changed
- 🔧 What was actually executed
- ⚠️ What blocks progress
- ➡️ What action is next

Main KPI: Alexander should open Instagram and visibly see the profile developing.

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
- As of 2026-10-01: 0 posts / 0 followers / 0 following before first autonomous publish cycle
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

Planned Highlights: `СТАРТ`, `КЕЙСЫ`, `AI-БИЗНЕС`, `ИНСТРУМЕНТЫ`, `РАЗБОР`; later `ОБО МНЕ`, `FAQ`.

Feed cover families: FACE + CLAIM, SYSTEM, CASE. Keep 3–5 word mobile-readable titles, high contrast, one focal point, consistent typography and no visual clutter.

Recognizable content series: `AI за 60 секунд`, `Разбор бизнеса`, `Что автоматизировать первым`, `AI-ошибка недели`, `Кейс до/после`, `1 инструмент — 1 задача`.

Reels operating rules: original/meaningfully transformed content, no foreign-platform watermarks, 1080x1920, first-frame hook within 1–2 seconds, captions/on-screen text, clear cover, and CTA toward save/send/follow when appropriate. Measure retention/watch time, sends, saves, profile visits and follows. Trial Reels are a native/manual experiment only when available in the Instagram account; do not make Buffer automation depend on them.

## Publishing layer
- Buffer Free for sitkoalex.ai.business
- Content is staged in `instagram_content_queue.json`
- Worker: `instagram_buffer_bridge.py`
- Only items with `approved=true` are eligible for queueing/publishing.
- Because the user granted general autonomous organic-publishing permission, the system may set `approved=true` itself for content that complies with MASTER TЗ and has a valid media URL.
- No paid promotion, spend, or paid ads without separate approval.
- After each attempted publication, verify the result through Buffer/API and, when available, Instagram itself.

### Launch content architecture
Three future pinned Reels are selected by role:
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
- 2026-10-01: worker deployment for first autonomous publish cycle reached SUCCESS after queue update.
- Continue log verification and verify each published item externally.

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
Ask the user only when genuinely required for login/password entry, 2FA, CAPTCHA/identity verification, OAuth approval unavailable to connectors, secure secret paste, physical local media upload, or irreversible/security-sensitive settings.

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
1. Verify first autonomous Reel publication end-to-end in Buffer and Instagram.
2. Implement/test the 7-question audit intake before enabling `РАЗБОР` as a live lead CTA.
3. Create premium Highlight cover masters and publish Stories/Highlights when supported by current tool path.
4. Continue converting prepared Reels into real media assets and publish under MASTER TЗ.
5. Use analytics from published content to change hooks, covers, cadence and CTA based on evidence.
