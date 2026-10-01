# AI Business Audit — v1

Purpose: free diagnostic lead magnet for `sitkoalex.ai.business`. Keep separate from Best Climate HVAC certificate funnel.

## Promise
A short 7-question intake that identifies where AI can save time, reduce lead leakage, or remove repetitive work. Do not promise guaranteed revenue or savings.

## 7 questions
1. Business / niche: What do you sell and to whom?
2. Lead sources: Where do new enquiries arrive now (Instagram, WhatsApp, Telegram, Avito, website, calls, other)?
3. Lead volume: Roughly how many new enquiries per week? `0–10 / 11–30 / 31–100 / 100+`.
4. Main bottleneck: `slow replies / lost leads / content production / repetitive admin / sales follow-up / analytics / other`.
5. Current workflow: What happens from a new enquiry to sale? Short free-text answer.
6. Existing stack: Which CRM, messengers, bots, spreadsheets, schedulers or AI tools are already used?
7. Desired 30-day result: What one measurable improvement matters most? Include preferred contact method for receiving the audit.

## Qualification
Score for prioritisation only; never present it as an objective business valuation.
- +2: 31+ leads/week
- +2: lead loss or slow response is selected
- +2: clear repetitive workflow suitable for automation
- +1: existing CRM/structured lead source
- +1: measurable 30-day goal supplied

Segments:
- 0–2: Education — give 1 simple automation recommendation.
- 3–5: Opportunity — return top 3 automation opportunities and invite to implementation discussion.
- 6–8: Priority — return top 3 opportunities, estimated implementation sequence, and offer a human strategy call.

## User-facing audit output
1. Current bottleneck summary.
2. Top 3 AI/automation opportunities.
3. First automation to implement and why.
4. What data/access would be needed.
5. 30-day test metric.
6. Clear next step: self-implement / request implementation discussion.

## Funnel state machine
`instagram_reel_or_bio -> telegram_or_salebot_start -> consent_notice -> q1..q7 -> qualification -> audit_result -> optional_strategy_call -> crm_or_manager_handoff`

### Required fields
`source`, `utm_campaign`, `answers`, `score`, `segment`, `contact_method`, `consent_timestamp`, `status`, `created_at`.

### Statuses
`new`, `intake_started`, `intake_complete`, `audit_ready`, `audit_sent`, `call_requested`, `handoff`, `closed`.

## Messaging logic
- Entry CTA before intake is live: `Сохрани и подпишись — скоро открою бесплатный AI-разбор бизнеса.`
- Entry CTA after intake is live: `Напиши «РАЗБОР» — за 7 ответов покажу, где AI может снять рутину и потери заявок.`
- Completion: thank user, set expectation for audit result, do not claim guaranteed financial outcome.

## Safety / privacy
- Ask only for business-process information needed for the audit.
- Do not request passwords, API keys, payment-card data, 2FA codes, identity documents or unnecessary sensitive personal data.
- Show a concise consent/privacy notice before collecting contact information.
- Keep marketing opt-in separate from receiving the requested audit where technically possible.
- Public CTA stays disabled until the intake route has been tested end-to-end.

## Implementation order
1. Build intake in SaleBot or Telegram bot.
2. Add consent notice and 7-question state machine.
3. Store answers + source/UTM + status.
4. Generate audit output from a fixed template plus answers.
5. Test one synthetic lead end-to-end.
6. Only then switch PIN 2 CTA from pre-launch to `РАЗБОР` and request explicit approval for public publication.
