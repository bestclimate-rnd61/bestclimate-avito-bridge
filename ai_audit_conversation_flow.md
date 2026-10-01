# AI Business Audit — Conversation Flow v1

Target: `sitkoalex.ai.business` free lead magnet. This is implementation copy/state logic for Telegram/SaleBot. It does not activate a public CTA.

## Entry
Trigger: user opens the audit route from Instagram/BIO or sends `РАЗБОР` after launch.

Message:
`Привет! За 7 коротких ответов соберу вводные и покажу, где AI/автоматизация могут убрать рутину, ускорить обработку заявок или снизить их потери. Это диагностика, не обещание гарантированного дохода. Начать?`
Buttons: `Начать разбор` / `Не сейчас`.

## Consent notice
Before Q1:
`Для разбора нужны только данные о бизнес-процессах и способ связи для получения результата. Не отправляйте пароли, коды 2FA, данные карт, API-ключи или документы. Продолжая, вы соглашаетесь использовать ваши ответы для подготовки запрошенного разбора.`
Button: `Продолжить`.
Store `consent_timestamp`; status -> `intake_started`.

## Q1 — Business
`1/7. Что вы продаёте и кому? Коротко: ниша + основной клиент.`
Free text; reject empty answer.

## Q2 — Lead sources
`2/7. Откуда сейчас приходят новые обращения? Можно выбрать несколько.`
Buttons/multiselect: `Instagram`, `WhatsApp`, `Telegram`, `Avito`, `Сайт`, `Звонки`, `Другое`.

## Q3 — Lead volume
`3/7. Примерно сколько новых обращений приходит за неделю?`
Single choice: `0–10`, `11–30`, `31–100`, `100+`.

## Q4 — Bottleneck
`4/7. Где сейчас теряется больше всего времени или денег?`
Single/multiple choice: `Медленные ответы`, `Теряются заявки`, `Контент`, `Повторяющаяся рутина`, `Дожим/повторные касания`, `Аналитика`, `Другое`.

## Q5 — Workflow
`5/7. Что происходит после новой заявки до продажи? Опишите 3–6 шагов как есть сейчас.`
Free text.

## Q6 — Stack
`6/7. Что уже используете? CRM, мессенджеры, боты, таблицы, планировщики, AI-сервисы. Если ничего — так и напишите.`
Free text.

## Q7 — Goal + delivery
`7/7. Какой один измеримый результат хотите получить за ближайшие 30 дней? И куда удобнее получить разбор?`
Goal free text, then contact choice: `Telegram`, `WhatsApp`, `Email` and request only the minimum destination identifier needed.
Status -> `intake_complete`.

## Qualification
Internal only:
- +2 if 31+ leads/week.
- +2 if slow replies or lost leads selected.
- +2 if Q5 exposes a clear repetitive automatable workflow.
- +1 if CRM/structured source exists.
- +1 if Q7 contains a measurable 30-day goal.
Segments: 0–2 Education; 3–5 Opportunity; 6–8 Priority.
Never show the score as a business valuation.

## Audit generation contract
Input: Q1–Q7 + source/UTM + score/segment.
Output must contain exactly:
1. bottleneck summary;
2. top 3 automation opportunities;
3. first automation to implement + why;
4. required data/access (never ask for secrets in chat);
5. one 30-day test metric;
6. next step: self-implement or implementation discussion.
No guaranteed revenue/savings claims.

## Completion
Immediate message after Q7:
`Готово — вводные собраны. Разбор покажет 3 приоритетные точки автоматизации и первый шаг на 30 дней. Если для рекомендации не хватает данных, мы прямо это отметим, а не будем придумывать цифры.`
Set status `audit_ready` only after generation succeeds; `audit_sent` only after successful delivery.

## Synthetic E2E test fixture
Use before public launch:
- niche: HVAC installation/service for homes and small businesses;
- sources: Instagram + Avito + website;
- volume: 31–100/week;
- bottleneck: slow replies + lost leads;
- workflow: enquiry -> messenger -> manual qualification -> quote -> follow-up -> sale;
- stack: spreadsheets + Telegram + website forms;
- goal: reduce median first-response time below 5 minutes in 30 days;
- delivery: test-only Telegram destination, no real customer data.
Expected internal score: 7/8 (Priority) if workflow is judged clearly automatable and structured source credit applies.
Expected first recommendation: central lead capture + instant acknowledgement/routing, followed by qualification and follow-up automation.

## Launch gate
Do not enable public `РАЗБОР` CTA until:
1. the route is implemented in Telegram/SaleBot;
2. consent and all 7 answers persist correctly;
3. synthetic fixture reaches audit generation and delivery;
4. duplicate/restart behavior is tested;
5. user explicitly approves the public CTA/content.
