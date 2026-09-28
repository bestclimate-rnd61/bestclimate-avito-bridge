# Best Climate Rostov — Avito Growth Loop Status — 2026-09-28

## Verified live infrastructure
- Railway project: `bestclimate-avito-bridge`.
- Live service: `bestclimate-avito-bridge-live`.
- Current production diagnostic deployment: `0f04ba09-ca17-49aa-a145-1288b970292b`, commit `db214b9d8ae8d8edefd10d96e645b979f7a4e83c`.
- Avito API auth confirmed for account `90352839` / `Бест Климат Ростов - Климат, Отопление, Вентиляция`.
- `/health` returns HTTP 200.
- Bridge/diagnostics are read-only for Avito mutation actions.

## Live loop snapshot
- `active_items = 21`.
- `auth_ok = true`.
- `low_balance = true` using bridge safety threshold `150`.
- Autoload profile is accessible and `autoload_enabled = true`.
- Autoload `uploadMode = manual`.
- Autoload `allow_pay_over_limit = false`.
- Autoload upload history count = `0`.
- Therefore `/autoload/v4/uploads/current` and `/autoload/v4/uploads/last_successful` returning HTTP 404 is consistent with there being no managed upload yet, not evidence by itself of broken API access.

## Current confirmed Autoload readiness
- 10/10 selected priority listings have optimized controlled drafts.
- 1/10 is feed-ready: Haier AvitoId `7748832830`.
- 0/10 have been uploaded through the new managed feed.
- Haier staging row preserves current AvitoId and current price and uses `ListingFee=Package` + `AdStatus=Free`.
- Existing strong listings remain protected from bulk changes.

## Duplicate-prevention findings
- VRF/ventilation ads `4228840511` and `4228587935` have the same title but are geographically different: Donetsk and Sochi. Do not treat them as duplicates solely from title.
- Existing AQUA/TOWADA-related live cards include Donetsk `8479764928`, Moscow `8324639588`, Moscow `8305258576`, plus Lugansk `8461285020` whose title does not explicitly identify AQUA.
- Because Moscow already has two AQUA TOWADA-related live cards, no new Moscow AQUA TOWADA row may be published until exact SKU/offer/performance mapping is resolved.
- Duplicate-prevention map is stored in `AQUA_EXISTING_AVITO_MAP_2026-09-28.md`.

## AQUA rule
- AQUA air-to-air heat pumps: owner-confirmed internal specification `обогрев до -30 °C` is allowed and should be used consistently for AQUA heat-pump campaign copy.
- No unsupported temperature/spec claims for other brands without exact model verification.

## Safety locks
- No duplicate publishing.
- No deletions.
- No automatic paid promotion.
- No automatic price changes.
- No unsupported technical claims.
- Preserve strong live listings until a controlled replacement is validated.
- Never publish unresolved category/vendor/image rows.
- While `low_balance=true`, do not initiate paid actions or any workflow that could unexpectedly consume balance.

## Profile optimization pack already ready
Priority catalog order:
1. Кондиционеры с установкой
2. Тепловые насосы воздух-воздух
3. Кассетные кондиционеры
4. Напольно-потолочные кондиционеры
5. Канальные кондиционеры
6. VRF / VRV
7. Вентиляция
8. Тепловые завесы
9. Корзины / кронштейны / подставки
10. Ремонт / обслуживание / чистка

Profile copy, delivery/payment/warranty wording, avatar brief, banner brief and first-image rules are prepared in `AVITO_PROFILE_FINAL_PACK_2026-09-28.md`.

## Next safe execution order
1. Keep low-balance hard lock on all paid actions.
2. Map existing live AQUA cards to exact SKU/offer before any new feed row; compare the two Moscow cards first.
3. Inspect profile completeness and apply profile/banner/avatar fields only where supported safe write access becomes available.
4. Continue controlled migration: VRF/ventilation truthful fields -> basket leaf category -> concrete SKU rows.
5. Upload nothing until each feed batch passes validation and duplicate/price safety checks.
