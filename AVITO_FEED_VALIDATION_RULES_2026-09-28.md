# Best Climate Rostov — Avito feed validation rules — 2026-09-28

Purpose: pre-publication gate for HVAC Autoload rows. This file does not publish or modify live ads.

## Global hard locks
- Never create a row when an existing live ad matches the same city + offer/SKU unless it is an intentional update tied to the existing AvitoId.
- Never change a live price through the feed unless the owner explicitly authorizes that exact price change.
- Never enable paid promotion or pay-over-limit automatically.
- Never delete or pause a strong live listing automatically.
- AQUA air-to-air heat pumps may use the owner-confirmed claim: heating down to -30 °C. Do not copy that temperature claim to other brands without model verification.
- Images: max 10; use ImageUrls or ImageNames according to Avito schema, not both as competing sources.
- Require Address or verified Latitude/Longitude before feed readiness.

## Кондиционеры — verified required fields
Source: live Avito Autoload schema probe, 2026-09-28.
- Price — required integer.
- Vendor — required select value; do not guess unsupported vendor strings.
- AdType — required. Allowed values observed: `Товар приобретен на продажу`, `Товар от производителя`.
- AirConditionerType — required. Observed values: `Сплит-система`, `Мобильный`, `Фанкойл`.
- AirConditionerSubType — required. Observed values: `Напольный`, `Настенный`, `Потолочный`, `Напольно-потолочный`, `Канальный`, `Кассетный`, `Настольный`, `Оконный`.
- Address — required unless Latitude + Longitude are supplied.
- Images/ImageUrls/ImageNames — photo source required under schema dependency; max 10 images.
- ContactMethod defaults to `По телефону и в сообщениях`; preserve unless there is a specific reason to change.

### Wholesale conditional fields
If WholesaleType = `Да`, require the dependent wholesale fields before validation, including minimum order basis/count and discount-ladder settings where applicable. Do not invent wholesale discounts.

## Вентиляция — verified required fields
Source: live Avito Autoload schema probe, 2026-09-28.
- Specialty — required. Observed values: `Проектирование`, `Монтаж`, `Ремонт и обслуживание`, `Чистка`, `Экспертиза`.
- WorkExperience — required. Use only truthful value; `10 лет и больше` is allowed by schema but must not be asserted unless verified for the business/service.
- TeamSize — required. Do not guess team size.
- Guarantee — required: `Есть` or `Нет`; use only the truthful service guarantee state.
- MaterialPurchase — required: `Возможна` or `Нет`; use only the actual operating model.
- Address — required unless Latitude + Longitude are supplied.
- Images/ImageUrls/ImageNames — photo source required under schema dependency; max 10 images.
- Price is not universally required in this probed ventilation schema; do not introduce a fake teaser price solely to satisfy feed formatting.
- ContactMethod observed default: `По телефону`.

## Existing-live duplicate protection snapshot
- AQUA/TOWADA: Donetsk AvitoId 8479764928.
- AQUA-related: Lugansk AvitoId 8461285020 (brand/SKU mapping still unresolved from title alone).
- AQUA/TOWADA: Moscow AvitoId 8324639588.
- AQUA/TOWADA: Moscow AvitoId 8305258576.
- VRF/ventilation: Donetsk AvitoId 4228840511.
- VRF/ventilation: Sochi AvitoId 4228587935.

The two VRF rows above are different cities and must not be treated as title duplicates. Moscow already has two AQUA/TOWADA-related live ads; no new Moscow AQUA row is feed-ready until exact SKU/offer mapping is resolved.

## Feed-ready decision
A row is READY only when all are true:
1. Existing-ad duplicate check passed.
2. Exact category/subtype passed against schema.
3. Required vendor/brand value is verified.
4. Current live price is preserved, or a new price is explicitly authorized.
5. Address/geography is verified.
6. Required images are present and accessible; <=10.
7. Technical claims are model-supported; AQUA -30 °C exception is owner-confirmed internal specification.
8. Conditional fields are complete.
9. No paid option is enabled.
10. For an existing listing update, its AvitoId is preserved.

## Current safe state
Autoload is enabled but uploadMode is manual, allow_pay_over_limit is false, and managed upload history count is 0. Keep the first managed batch in staging until every row passes this gate.