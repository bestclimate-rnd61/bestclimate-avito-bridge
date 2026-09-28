# AQUA TOWADA — Existing Avito Map — 2026-09-28

Purpose: duplicate-prevention map for controlled Autoload migration. This file does not publish or edit anything on Avito.

## Verified live cards

### Donetsk
- AvitoId: `8479764928`
- Title: `Тепловой насос Aqua towada до -30C A+++ WiFi`
- Live price observed via API: `65,400`
- Status: active
- Geography verified from live Avito URL: Donetsk
- Migration rule: prefer mapping/updating this existing AvitoId rather than creating a new Donetsk AQUA TOWADA ad.

### Lugansk
- AvitoId: `8461285020`
- Title: `Тепловой насос -30C Инверторный кондиционер Wi-Fi`
- Live price observed via API: `65,400`
- Status: active
- Geography verified from live Avito URL: Lugansk
- Brand is not explicit in the live title. Do NOT map this row to AQUA until exact item content/model is verified.

### Moscow — card A
- AvitoId: `8324639588`
- Title: `Тепловой насос Aqua towada -30 на обогрев Haier`
- Live price observed via API: `65,400`
- Status: active
- Geography verified from live Avito URL: Moscow
- Safety flag: title combines AQUA TOWADA and Haier. Preserve live ad for now; verify the intended brand/manufacturer wording before any title edit.

### Moscow — card B
- AvitoId: `8305258576`
- Title: `Тепловой насос Aqua towada до -30C A+++ Wi-Fi`
- Live price observed via API: `69,600`
- Status: active
- Geography verified from live Avito URL: Moscow

## Moscow duplicate-prevention lock
There are already two active AQUA TOWADA-related Moscow cards (`8324639588` and `8305258576`).

Do NOT create another Moscow AQUA TOWADA listing through Autoload until both existing cards are compared by exact SKU, stock, creative, listing category and performance. If they are legitimately different SKUs/offers, keep both and map each to its correct controlled row. If they are the same SKU/offer, do not delete either automatically; first identify the stronger card and plan a manual consolidation without disrupting the winner.

## AQUA technical claim
For AQUA air-to-air heat pumps use the owner-supplied internal specification `обогрев до -30 °C`. Do not infer unsupported specifications for other brands.

## Other duplicate check resolved
The two live VRF/ventilation ads with the same title are geographically distinct and therefore must not be treated as duplicates solely from their titles:
- `4228840511` — Donetsk;
- `4228587935` — Sochi.

## Feed safety rule
- Preserve existing AvitoId where an existing live card is the intended target.
- Preserve live price unless the owner explicitly authorizes a price change.
- No new row where a same-city/same-offer live card may already exist until mapping is resolved.
- No paid promotion, deletion or duplicate publishing from this plan.
