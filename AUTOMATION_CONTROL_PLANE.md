# AI Automation Control Plane

## Goal
Run the user's Instagram / Best Climate / Avito automation stack with minimal manual intervention and minimal recurring cost.

## MASTER TЗ — AI INSTAGRAM SITKOALEX

Permanent operating instruction for `@sitkoalex.ai.business`.

### Main goal
Build a strong personal AI-business brand focused on audience growth, reach, inbound leads, AI implementation services, Alexander Sitko's personal brand, and later monetization.

### Core rule
A result counts only when something actually changed and can be verified externally. Order of work: DO -> VERIFY -> REPORT. Internal plans, scripts, drafts, specifications, queues and reports are not visible results by themselves.

## PRE-LAUNCH FREEZE — HIGHEST PRIORITY
Effective 2026-10-01. This supersedes the earlier general autonomous organic-publishing permission until Alexander gives the exact separate command `СТАРТ ПУБЛИКАЦИЙ`.

Before that command:
- DO NOT publish or schedule any NEW Reel, post or Story.
- All new content remains draft/prelaunch only.
- If an earlier item was already sent/scheduled before this freeze, do not create another publication; inspect its state and prevent further new queueing where safely possible.
- `approved=true` is NOT allowed for new queue items during pre-launch.
- Buffer/Railway are infrastructure only, not permission to publish.

### LAUNCH GATE
Launch is ready only when ALL are simultaneously ready and verified:
1. Profile packaging: avatar; strong SEO Name field; username accepted or deliberately retained; BIO with no empty-arrow CTA; working link/CTA.
2. Growth/professional settings: public account; recommendations; comments; Story replies; tags/mentions; reposts; Story archive; hidden words/anti-spam; Direct configured for leads.
3. Highlights visually ready: START/ОБО МНЕ, КЕЙСЫ, AI-БИЗНЕС, АВТОМАТИЗАЦИЯ, ИНСТРУМЕНТЫ, FAQ/РАЗБОР. ОТЗЫВЫ only when genuine evidence exists.
4. Funnel passes end-to-end test: Instagram CTA -> working link -> Telegram/SaleBot/selected intake -> qualification -> AI-разбор/AI-карта -> consultation -> paid audit -> implementation -> support.
5. Minimum 9 final Reels, preferably 12: actual 9:16 final videos, covers, captions, CTA, SEO keywords, checked audio. Scripts alone do not count.
6. Three pin candidates finalized: `Кто я и зачем профиль`; `Что ИИ уже делает в моих проектах`; `AI-разбор/лид-магнит`.
7. Every Reel is full production: Alexander or his approved AI-double/live talking head, natural speech sync, 1–2 second hook, fast cuts, B-roll/screencasts/case inserts, large captions, pattern interrupts, quality transitions, cover, and suitable music based on current AI/business creator patterns; music must not overpower speech.
8. Static/animated slide is not acceptable as the primary Reel when the spec requires a talking head.
9. Final export QA: Alexander identity/face, voice, lip-sync, spelling, subtitles, Instagram safe zones, no unwanted logos/artifacts, duration, CTA.
10. After the package is complete, report launch-ready status. Publishing begins only after exact command `СТАРТ ПУБЛИКАЦИЙ`, then use a launch grid that avoids an empty one-post profile.

### Current pre-launch state
- Professional public Instagram: `sitkoalex.ai.business`.
- Category: Автор цифрового контента.
- Avatar installed; BIO exists but must be launch-gate checked together with Name/link/CTA.
- Buffer Free connected; Railway worker exists.
- `instagram_content_queue.json` contains 12 Reel drafts.
- IMPORTANT: `ai-reel-001-start` is currently stored with `approved=true` and a media URL from the earlier publishing phase. Under the new pre-launch freeze this is legacy state, NOT permission for any new publication. No additional items may be approved/scheduled. Inspect/reconcile the legacy item's external state without generating a new post.

### Production rules
Optimize for retention -> saves -> shares -> follows -> leads. Core pillars: AI in real business, automation, AI employees, leads/sales, real Alexander Sitko cases, Avito, Instagram, websites, bots, analytics, implementation mistakes, ROI, entrepreneur journey.

No fake reviews, numbers, cases or promises. Do not copy competitors. No paid advertising/spend, password/2FA/ownership/payment/tax changes without separate explicit approval.

## Operating principle
Prefer OAuth/API tokens and connected tools over usernames/passwords. Never store plaintext passwords, 2FA codes, payment data, or private secrets in this repository. Secrets belong only in provider secret stores such as Railway Variables.

## Control layer
- ChatGPT automation: orchestration, checks, decisioning, reports and escalation.
- Opera Browser Connector: browser inspection/navigation when available.
- Gmail connector: one alert only when the user must act.
- Do not use TinyFish.

## Publishing layer
- Buffer Free channel: `sitkoalex.ai.business`; timezone Moscow.
- Queue: `instagram_content_queue.json`.
- Worker: `instagram_buffer_bridge.py`.
- PRE-LAUNCH FREEZE overrides worker eligibility rules: do not approve/schedule NEW content before `СТАРТ ПУБЛИКАЦИЙ`.
- After launch permission, only final production assets passing MASTER TЗ and final QA can be approved.
- Verify every publication externally in Instagram after sending.

## Launch content architecture
Three pin roles:
1. POSITIONING — Кто я и зачем профиль.
2. SYSTEM/PROOF — Что ИИ уже делает в моих проектах.
3. LEAD MAGNET — AI-разбор/AI-карта бизнеса, only after funnel E2E passes.

Minimum launch package: 9 final Reels; target 12. Do not count scripts or simple slide animations as finished Reels.

## Lead funnel
Instagram -> free AI business audit/map -> Telegram/SaleBot or selected intake -> qualification -> consultation -> paid audit -> implementation -> support.
Public `РАЗБОР` CTA remains disabled until intake is implemented and tested end-to-end with a synthetic lead.

## Railway
Project: bestclimate-avito-bridge
Project ID: b54c084c-9395-4bb9-8cd5-883f3f6c8d68
Production env ID: 7910fd44-9fad-4484-86c4-24481c600322
Instagram Buffer worker service ID: 345003ca-8c70-47b0-8f9b-bf4c712d3610
Start: `python instagram_buffer_bridge.py`
Cron: `5 * * * *`
Restart policy: NEVER
Required secret `BUFFER_API_KEY` stays in Railway Variables only.

Live Avito service `bestclimate-avito-bridge-live` service ID `7fd7de90-333f-440d-97c1-8c97394918cf` must not be touched by Instagram work.

## Metricool separation
Old profile `alexandr.sitko` remains in Metricool. Do not mix it with `sitkoalex.ai.business`.

## Manual-intervention policy
Ask Alexander only when genuinely required for login/password entry, 2FA, CAPTCHA/identity verification, OAuth unavailable to connectors, secure secret paste, physical local media upload, or irreversible/security-sensitive settings. Send one concise Gmail alert when required and continue other safe work.

## Cost policy
Prefer free tiers and reuse existing services safely. No paid upgrade without explicit approval.

## Recovery / fallback order
1. Direct API / connected app tool
2. Railway API/logs
3. GitHub configuration/code
4. Opera Browser Connector
5. User manual action only when unavoidable

## Reporting
Only report:
- ✅ What actually changed
- 🔧 What was actually executed
- ⚠️ What blocks progress
- ➡️ What action is next

Main KPI: Alexander opens Instagram and visibly sees a professionally developing profile — but during PRE-LAUNCH this means profile/funnel packaging only, with zero new content publications until `СТАРТ ПУБЛИКАЦИЙ`.