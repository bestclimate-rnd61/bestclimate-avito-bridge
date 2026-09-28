# Avito Autoload Migration Report — 2026-09-28

## Completed
- Confirmed Avito API authentication for account `90352839` / «Бест Климат Ростов - Климат, Отопление, Вентиляция».
- Selected 10 priority active listings for controlled migration/optimization.
- Pulled current Avito IDs, titles, prices, categories, addresses and URLs via API.
- Pulled current Avito Autoload field schemas for household AC, commercial conditioning, commercial ventilation and ventilation services.
- Confirmed that `AvitoId` can be included when bringing an existing manually-created listing under Autoload control, reducing duplicate risk.
- Built `managed_ads_draft_2026-09-28.json` with stable internal IDs, preserved Avito IDs, preserved current prices, optimized titles/descriptions and explicit blockers.
- Built `validate_managed_ads.py` safety validator; hard checks passed.
- Added permanent read-only bridge endpoints for Autoload profile/tree/category field inspection and listing detail inspection.
- Added a focused dependency probe and confirmed that wholesale fields in household AC are conditional rather than universally required.
- Verified the live Haier listing `7748832830`: manufacturer Haier, new product, wall-mounted split-system category, and current listing images were confirmed from the public listing.
- Built `avito_feed_batch_01_haier.xml` as a single-item staging feed. It preserves `AvitoId=7748832830`, base price `18990`, uses `ListingFee=Package` and `AdStatus=Free`, and enables no paid promotion.
- Built `validate_feed_xml.py`. The feed passes local structural/safety checks: valid XML, required tags present, title under 50 characters, positive integer price, three valid HTTP(S) image URLs, stable Id/AvitoId, and safe placement flags.
- Built `managed_ads_ready_2026-09-28.json`; Haier is the first item marked `feed_ready=true`, while `uploaded_to_avito=false` remains locked.
- Latest schema-probe Railway deployment completed successfully; startup logs showed `AVITO_AUTH_OK` and `/health` HTTP 200.

## Safety rules locked
- `ListingFee = Package`
- `AdStatus = Free`
- No automatic paid promotion.
- Preserve existing `AvitoId` when migrating existing ads.
- Preserve current/base price until the specific price is verified.
- Never upload an item while required category fields or images are unresolved.
- Do not make large changes to high-converting basket/Taganrog listings until an A/B replacement is ready.
- Staging feed creation does not mean Avito upload; attachment to Autoload is a separate controlled step.

## Current readiness
- 10/10 selected listings: optimized content draft ready.
- 1/10 feed-ready: Haier `7748832830`.
- 0/10 uploaded through the new feed.
- Main blockers for the remaining items: exact Vendor/SKU for generic product ads, truthful service fields for VRF/ventilation, exact basket leaf category, exact model confirmation for low-temperature heat-pump claims, and usable image URLs.

## Key schema findings
### Household conditioners (`kondicioneri`)
Required core fields include Title, Description, images, Address, Price, Category=`Бытовая техника`, GoodsType=`Климатическое оборудование`, ProductType=`Кондиционеры и запчасти`, GoodsSubType=`Кондиционеры`, Vendor, Condition, AirConditionerType and AirConditionerSubType.

`AdType` supports `Товар приобретен на продажу` and `Товар от производителя`. For the Haier reseller listing the staging feed uses `Товар приобретен на продажу`.

Wholesale fields such as `WholesaleMinOrderType`, `WholesaleMinOrderCount` and `WholesaleDiscountLadderType` become required only when wholesale mode is enabled. The Haier managed title was therefore simplified to `Кондиционеры Haier | Продажа и установка` and wholesale mode is not enabled in Batch 01.

### Commercial conditioning (`kondicionirovanie`)
Supports `Мультисплит-система`, but under business-equipment taxonomy. Do not move the existing household multi-split listing into this category without deliberate category review.

### Ventilation services (`ventiljatsija`)
Requires Specialty, WorkExperience, TeamSize, Guarantee and MaterialPurchase in addition to normal content/address/images. Price is not generally mandatory in this service category, so a misleading teaser price does not need to be preserved in a future managed feed.

### Baskets
The tree node `zapchasti_kondicionery` is not directly usable as a leaf field schema (fields request returned 400). Exact basket leaf category still must be resolved before Autoload migration. Existing high-performing basket listings remain untouched.

## Next execution order
1. Finish Donetsk ventilation/VRF public-listing verification and collect truthful service parameters/images.
2. Build and validate the VRF/ventilation staging row without inventing WorkExperience or TeamSize.
3. Resolve exact basket leaf category without touching current high-converting listings.
4. Resolve generic multi-brand AC strategy as concrete SKU/brand rows rather than ambiguous multi-brand feed rows.
5. Validate each controlled batch before attaching any feed to Avito Autoload.
