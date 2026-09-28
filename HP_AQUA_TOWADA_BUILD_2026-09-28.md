# AQUA TOWADA — Avito Campaign Build — 2026-09-28

## Status
Campaign content build: READY FOR ASSET/PRICE CHECK

Feed publish: LOCKED until exact inventory price + image URLs are confirmed for each SKU.

## Important verification note
Current official AQUA Russia product data for the verified TOWADA 25-class shows guaranteed outdoor heating operation down to **-20 °C**, not -30 °C. Therefore this campaign must **not** use “-30 °C” for TOWADA unless AQUA provides a newer exact model specification proving it.

This supersedes older/secondary marketing notes for this specific current SKU.

---

## Verified current TOWADA lineup anchors

### 1) AQUA TOWADA 25
- SKU/system: `AQI-25FIS1/R3-W(IN) + AQI-25FIS1/R3(OUT)`
- Color: white
- Cooling: 2.6 kW
- Heating: 3.0 kW
- Recommended area: up to 25 m²
- Seasonal cooling efficiency class: A+++
- Seasonal heating efficiency class: A++
- Heating outdoor range: -20…+24 °C
- Cooling outdoor range: -20…+43 °C
- Quiet mode: 19 dB(A)
- Refrigerant: R32
- Official AQUA price reference on 2026-09-28: 65,400 RUB

### 2) AQUA TOWADA 35
- SKU/system family: `AQI-35FIS1/R3-W/B + AQI-35FIS1/R3(OUT)`
- Cooling: 3.5 kW
- Heating: 3.7 kW
- Recommended area: up to 35 m²
- Current official catalog reference: 75,600 RUB for black version shown in current product list
- Secondary dealer data confirms 20 dB(A) low-noise figure and heating operation to -20 °C for the current 35-class.

### 3) AQUA TOWADA 50
- SKU/system family: `AQI-50FIS1/R3-W/B + AQI-50FIS1/R3(OUT)`
- Cooling: 5.3 kW
- Heating: 6.0 kW
- Recommended area: up to 50 m²
- Current official catalog reference: 109,300 RUB white / 111,100 RUB black
- Heating operation in current dealer specs: -20…+24 °C

---

## Recommended Avito architecture

Do **not** collapse 25/35/50 into one fake “universal” item for Autoload. Use concrete SKU rows so price and Vendor remain truthful.

### Ad A — 25 class
**Internal campaign ID:** `HP-AQUA-TOWADA-25`

**Title A:** `AQUA TOWADA 25 | Инверторный кондиционер`

**Title B test:** `AQUA TOWADA до 25 м² | Инвертор | Wi-Fi`

**First screen copy:**
`Флагманская серия AQUA TOWADA для квартиры, дома и офиса. 2,6 кВт холод / 3,0 кВт тепло, A+++ на охлаждении, тихий режим 19 дБ.`

`Подберём монтаж под объект, доставим по РФ. Цена оборудования и монтаж считаются отдельно.`

**Core factual bullets:**
- до 25 м²;
- инвертор;
- 2.6 kW cooling / 3.0 kW heating;
- A+++ cooling / A++ heating;
- heating down to -20 °C;
- 19 dB(A) quiet mode;
- R32;
- white color; black variant only if exact SKU is available.

**CTA:** `Напишите площадь помещения и город — рассчитаем оборудование, доставку и монтаж.`

### Ad B — 35 class
**Internal campaign ID:** `HP-AQUA-TOWADA-35`

**Title A:** `AQUA TOWADA 35 | Инвертор | До 35 м²`

**First screen copy:**
`AQUA TOWADA 35: 3,5 кВт на охлаждение и 3,7 кВт на обогрев. Подходит для помещений до 35 м² при корректном теплотехническом подборе.`

`Есть профессиональный монтаж, доставка и запуск системы.`

### Ad C — 50 class
**Internal campaign ID:** `HP-AQUA-TOWADA-50`

**Title A:** `AQUA TOWADA 50 | Инвертор | До 50 м²`

**First screen copy:**
`AQUA TOWADA 50 для больших комнат, домов, офисов и коммерческих помещений: 5,3 кВт холод / 6,0 кВт тепло.`

`Подберём трассу, монтаж и доставку под объект.`

---

## Visual hierarchy for first image

Use only 3–5 verified claims:
1. `AQUA TOWADA`
2. exact area class: `до 25 м²` / `до 35 м²` / `до 50 м²`
3. `INVERTER`
4. `A+++` where exact model supports it
5. `19–20 дБ` only on the exact 25/35 model where verified

Do not place `-30 °C` on TOWADA first images for the currently verified SKUs.

## Pricing rule
- Keep existing Best Climate live prices if they correspond to real stock and are lower than official catalog reference.
- Do not automatically overwrite live Avito pricing with the official recommended/catalog price.
- Every ad row gets its own real SKU price.

## Autoload mapping
Use the already-probed household AC category fields:
- Category = Бытовая техника
- GoodsType = Климатическое оборудование
- ProductType = Кондиционеры и запчасти
- GoodsSubType = Кондиционеры
- Vendor = AQUA (confirm exact accepted Avito enum at feed validation)
- Condition = Новое
- AirConditionerType = Сплит-система
- AirConditionerSubType = Настенный
- AdType = Товар приобретен на продажу
- ListingFee = Package
- AdStatus = Free

## Blockers before feed-ready
1. Confirm current Best Climate stock and selling price for 25/35/50.
2. Confirm direct image URLs / owned product images for each exact SKU.
3. Confirm Avito `Vendor` accepted value for AQUA.
4. Decide whether 25/35/50 will be new listings or mapped to any existing AvitoIds.
5. Run validator before upload.

## Next build
After AQUA assets are resolved:
1. Ballu ICE PEAK exact SKU matrix with verified -30 °C claim.
2. GREE low-temperature exact SKU verification.
3. Midea low-temperature exact SKU verification.
