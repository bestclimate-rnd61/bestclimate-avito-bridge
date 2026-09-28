# Best Climate Rostov — Avito Growth Loop Status — 2026-09-28

## Verified live infrastructure
- Railway project: `bestclimate-avito-bridge`.
- Live service: `bestclimate-avito-bridge-live`.
- Production deployment `6ebc0e85-d9a6-4dd6-a2a4-6f6537232631` is SUCCESS on commit `b50a31578a0cd14041eb871551a3e13cc148e3dd`.
- Avito API auth is confirmed in production logs for account `90352839` / `Бест Климат Ростов - Климат, Отопление, Вентиляция`.
- Railway `/health` returned HTTP 200 in production logs.
- Bridge remains read-only for Avito mutation actions.

## Live loop snapshot
First successful sanitized production monitor run reported:
- `active_items = 21`;
- `auth_ok = true`;
- `low_balance = true` using bridge safety threshold `150`;
- `/autoload/v4/uploads/current` returned HTTP 404;
- `/autoload/v4/uploads/last_successful` returned HTTP 404.

Interpretation lock: the two Autoload 404 responses are recorded as an unresolved state, not automatically interpreted as a broken account. No Autoload upload will be triggered until the profile/upload state is verified through a supported read path.

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

## Monitor improvement
The safe periodic read-only monitor is now LIVE in Railway production. It logs only sanitized state: API auth, active-item count, low-balance boolean, and current/last-successful Autoload status. It does not change Avito listings, prices or promotions and does not spend money.

## Next safe execution order
1. Resolve Autoload 404 state using read-only profile/uploads diagnostics; do not upload anything.
2. Treat `low_balance=true` as a hard paid-action risk lock.
3. Inspect profile completeness and apply profile/banner/avatar fields only where UI/API access safely supports them.
4. Continue controlled migration: VRF/ventilation truthful fields -> basket leaf category -> concrete SKU rows.
5. Prepare AQUA TOWADA 25/35/50 only after current selling price, inventory, images and exact Avito Vendor value are confirmed.
6. Upload nothing until the relevant feed passes validation and duplicate/price safety checks.
