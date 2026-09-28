# Best Climate Rostov — SAFE Avito Feed Readiness Copy Pack — 2026-09-28

Purpose: prepare non-paid, non-destructive copy/structure for future profile/feed updates without publishing duplicates, changing prices, or touching proven live ads.

## Global rules
- Never invent stock, price, warranty, delivery, certificates, energy savings, or installation timing.
- Never claim free delivery unless that exact offer qualifies.
- AQUA air-to-air heat pumps may use owner-confirmed heating claim: **обогрев до −30 °C**.
- Other brands/models require exact model verification before temperature/Wi-Fi/efficiency claims.
- Keep live winners unchanged until controlled A/B replacement is ready.
- One real SKU/service intent per feed row; avoid city/keyword clones that cannibalize each other.

## Standard first-response CTA
Здравствуйте! Подберём. Напишите, пожалуйста: город, площадь/размер помещения и что нужно — только оборудование или с монтажом. Для тепловой завесы дополнительно укажите ширину и высоту проёма, а также 220/380 В.

## Delivery wording — safe baseline
**Ростов-на-Дону и область:** доставка и монтаж — по условиям конкретного заказа.
**По РФ:** отправка оборудования транспортной компанией доступна для подходящих товарных позиций; стоимость и сторона оплаты доставки согласуются до заказа.

## Payment wording — safe baseline
Наличный и безналичный расчёт — по доступным на момент сделки способам. Кредит/рассрочку указывать только после подтверждения доступности для конкретного заказа.

## Warranty wording — safe baseline
Гарантия на оборудование и монтаж указывается по конкретной модели/работе и подтверждается до заказа. Не использовать единый срок для всего каталога без документального подтверждения.

## Cluster templates

### AQUA heat pump
Title direction: **Тепловой насос AQUA до −30 °C | подбор + монтаж**
First image hierarchy:
1. ТЕПЛОВОЙ НАСОС AQUA
2. ОБОГРЕВ ДО −30 °C
3. ПОДБОР + МОНТАЖ
Body opening:
**Тепловой насос воздух‑воздух AQUA для отопления и охлаждения. По внутренней спецификации бренда — работа на обогрев до −30 °C. Подберём мощность под площадь и задачу объекта, рассчитаем оборудование и монтаж.**
CTA: **Напишите город + площадь + нужен ли монтаж.**

### Cassette AC
Title direction: **Кассетный кондиционер 24/36/48/60 | монтаж**
First image:
1. КАССЕТНЫЙ КОНДИЦИОНЕР
2. МАГАЗИН • ОФИС • КАФЕ
3. ПОДБОР + МОНТАЖ
Body opening:
**Подбор кассетного кондиционера для коммерческого помещения. Мощность, бренд, цена и сроки — после уточнения площади, высоты потолка и условий монтажа.**
CTA: **Пришлите город, площадь, высоту потолка и фото/план помещения.**

### Floor-ceiling AC
Title direction: **Напольно‑потолочный кондиционер | подбор + монтаж**
Body opening:
**Подберём напольно‑потолочную систему под помещение и схему размещения. Рассчитаем оборудование, трассу и монтаж после исходных данных объекта.**
CTA: **Город + площадь + высота потолка + фото/план.**

### VRF/VRV
Title direction: **VRF / VRV кондиционирование под ключ | проект + монтаж**
Body opening:
**Подбор и реализация VRF/VRV для коммерческих и крупных объектов: расчёт, оборудование, трассы и монтаж. Конкретные характеристики и стоимость — по проекту/исходным данным.**
CTA: **Пришлите город, тип объекта, площадь и проект/план при наличии.**

### Ventilation
Title direction: **Вентиляция под ключ | расчёт + монтаж**
Body opening:
**Приточная, вытяжная и приточно‑вытяжная вентиляция для жилых и коммерческих объектов. Состав оборудования и стоимость определяются после расчёта воздухообмена и условий объекта.**
CTA: **Город + назначение объекта + площадь + план/проект.**

### Air curtain
Title direction: **Тепловая завеса 3–18 кВт | подбор + монтаж**
Body opening:
**Подберём тепловую завесу под входную группу. Мощность и модель определяем по ширине/высоте проёма, напряжению и условиям помещения.**
CTA: **Пришлите ширину и высоту проёма, 220/380 В, город и нужен ли монтаж.**

### Baskets / brackets / stands
Title direction: **Корзины и кронштейны для кондиционеров | производство**
Body opening:
**Корзины, кронштейны и одно-/двухуровневые подставки для наружных блоков. Размер, исполнение, цвет и стоимость — по конкретной задаче и количеству.**
CTA: **Пришлите размеры, количество, город и требуемый цвет RAL, если он задан.**

### Repair / cleaning
Title direction: **Ремонт и обслуживание кондиционеров | выезд**
Body opening:
**Диагностика, ремонт, чистка и обслуживание климатического оборудования. Итоговая стоимость зависит от неисправности, типа оборудования и условий доступа.**
CTA: **Пришлите город, модель/тип оборудования и кратко опишите проблему.**

## Feed QA checklist before any future upload
1. Unique external ID per real offer.
2. No duplicate SKU/service intent already active.
3. Category and required attributes verified against current Avito schema.
4. Brand/model spelling exact.
5. Price confirmed current; otherwise do not publish/change.
6. Stock/availability confirmed current.
7. Images load and contain no obsolete price/phone/claim.
8. Delivery wording matches actual offer.
9. Warranty claim supported for exact product/work.
10. No paid promotion flag enabled unintentionally.
11. Strong existing ads excluded from bulk rewrites.
12. Preview validation passes before upload.

## Next safe execution target
When live API/UI access is available, audit profile completeness and Autoload validation first. Apply only confirmed missing fields or feed corrections; do not create duplicates or alter prices automatically.