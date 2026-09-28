# Best Climate Rostov — Avito Growth Loop Status — 2026-09-28

## Verified live infrastructure
- Railway project: `bestclimate-avito-bridge`.
- Live service: `bestclimate-avito-bridge-live`.
- Avito API auth is confirmed in production logs for account `90352839` / `Бест Климат Ростов - Климат, Отопление, Вентиляция`.
- Railway `/health` returned HTTP 200 in production logs.
- Bridge remains read-only for Avito mutation actions.

## Current confirmed Autoload readiness
- 10/10 selected priority listings have optimized controlled drafts.
- 1/10 is feed-ready: Haier AvitoId `7748832830`.
- 0/10 have been uploaded through the new managed feed.
- Haier staging row preserves current AvitoId and current price and uses `ListingFee=Package` + `AdStatus=Free`.
- Existing high-converting basket/Taganrog listings remain protected from bulk changes.

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

## Monitor improvement
A safe periodic read-only monitor was added to `app.py` in GitHub commit `b50a31578a0cd14041eb871551a3e13cc148e3dd`. It is designed to log only sanitized state: API auth, active-item count, low-balance boolean, and current/last-successful Autoload status. It does not change Avito listings or spend money.

## Current infrastructure blocker
The Railway service is redeploying a pinned snapshot with commit `5247721f1cf138f97403fc8a7637bdd26fa8ca9a` rather than the newer GitHub `main`. Ordinary Railway `redeploy` therefore does not yet activate the new monitor. Do not create a duplicate production service merely to work around this; reconnect/update the existing Railway source when a supported source-control action is available.

## Next safe execution order
1. Restore existing Railway service source tracking to current GitHub `main` without creating a duplicate service.
2. Read sanitized monitor status (active count, balance risk, Autoload current/last-successful).
3. Apply profile fields/banner/avatar in Avito UI only where currently missing and supported.
4. Continue controlled migration: VRF/ventilation truthful fields -> basket leaf category -> concrete SKU rows.
5. Prepare AQUA TOWADA 25/35/50 only after current selling price, inventory, images and exact Avito Vendor value are confirmed.
6. Upload nothing until the relevant feed passes validation and duplicate/price safety checks.
