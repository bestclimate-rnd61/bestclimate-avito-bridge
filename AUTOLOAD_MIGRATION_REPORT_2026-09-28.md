# Avito Autoload Migration Report — 2026-09-28

## Completed
- Confirmed Avito API authentication for account `90352839` / «Бест Климат Ростов - Климат, Отопление, Вентиляция».
- Selected 10 priority active listings for controlled migration/optimization.
- Pulled current Avito IDs, titles, prices, categories, addresses and URLs via API.
- Pulled current Avito Autoload field schemas for household AC, commercial conditioning, commercial ventilation and ventilation services.
- Confirmed that `AvitoId` can be included when bringing an existing manually-created listing under Autoload control, reducing duplicate risk.
- Built `managed_ads_draft_2026-09-28.json` with stable internal IDs, preserved Avito IDs, preserved current prices, optimized titles/descriptions and explicit blockers.
- Built `validate_managed_ads.py` safety validator. Railway deployment with this validator completed successfully, so hard validation checks passed.
- Added permanent read-only bridge endpoints for Autoload profile/tree/category field inspection and listing detail inspection, removing the need for repeated temporary probe deployments.
- Latest bridge deployment completed successfully; startup logs show `AVITO_AUTH_OK` and `/health` returned HTTP 200.

## Safety rules locked
- `ListingFee = Package`
- `AdStatus = Free`
- No automatic paid promotion.
- Preserve existing `AvitoId` when migrating existing ads.
- Preserve current price until the specific price is verified.
- Never upload an item while required category fields or images are unresolved.
- Do not make large changes to high-converting basket/Taganrog listings until an A/B replacement is ready.

## Current readiness
- 10/10 selected listings: optimized content draft ready.
- 0/10: marked feed-ready yet, intentionally.
- Main blockers: required image URLs, exact Vendor/leaf-category fields for generic product ads, truthful service fields for VRF/ventilation, exact model confirmation for low-temperature heat-pump claims.

## Key schema findings
### Household conditioners (`kondicioneri`)
Required fields include Title, Description, images, Address, Price, Category=`Бытовая техника`, GoodsType=`Климатическое оборудование`, ProductType=`Кондиционеры и запчасти`, GoodsSubType=`Кондиционеры`, Vendor, Condition, AirConditionerType and AirConditionerSubType.

### Commercial conditioning (`kondicionirovanie`)
Supports `Мультисплит-система`, but under business-equipment taxonomy. Do not move the existing household multi-split listing into this category without deliberate category review.

### Ventilation services (`ventiljatsija`)
Requires Specialty, WorkExperience, TeamSize, Guarantee and MaterialPurchase in addition to normal content/address/images.

### Baskets
The tree node `zapchasti_kondicionery` is not directly usable as a leaf field schema (fields request returned 400). Exact basket leaf category still must be resolved before Autoload migration. Existing high-performing basket listings remain untouched.

## Next execution order
1. Bring the Haier listing to full feed-ready state after images/category details are resolved.
2. Bring the Donetsk ventilation/VRF service listing to full feed-ready state after truthful Specialty/WorkExperience/TeamSize values and images are fixed.
3. Resolve exact basket leaf category without touching current high-converting listings.
4. Resolve generic multi-brand AC strategy (one concrete SKU/brand per managed product listing rather than an ambiguous multi-brand feed row).
5. Only after validation: connect/upload feed in controlled batches and verify Avito reports before scaling.
