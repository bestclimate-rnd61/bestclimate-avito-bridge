import json
import re
from pathlib import Path

PATH = Path('managed_ads_draft_2026-09-28.json')
data = json.loads(PATH.read_text(encoding='utf-8'))
items = data['items']
errors = []
warnings = []
seen_avito = set()
seen_internal = set()

for item in items:
    aid = item['avito_id']
    iid = item['internal_id']
    title = item['proposed_title']
    desc = item['description']

    if aid in seen_avito:
        errors.append(f'{aid}: duplicate avito_id')
    seen_avito.add(aid)
    if iid in seen_internal:
        errors.append(f'{aid}: duplicate internal_id')
    seen_internal.add(iid)

    if len(title) > 50:
        errors.append(f'{aid}: title too long ({len(title)})')
    if '₽' in title or re.search(r'\b\d{4,6}\s*(?:руб|р\.)', title, re.I):
        errors.append(f'{aid}: price-like text in title')
    if re.search(r'(?:\+?7|8)[\s\-()]?\d{3}', title):
        errors.append(f'{aid}: phone-like text in title')
    if len(desc) > 7500:
        errors.append(f'{aid}: description too long ({len(desc)})')
    if item['proposed_price'] != item['current_price']:
        warnings.append(f'{aid}: price changed {item["current_price"]} -> {item["proposed_price"]}')
    if item.get('feed_ready') and item.get('blockers'):
        errors.append(f'{aid}: feed_ready=true but blockers remain')
    if not item.get('content_ready'):
        warnings.append(f'{aid}: content not ready')

safety = data.get('safety', {})
if safety.get('listing_fee') != 'Package':
    errors.append('Safety: ListingFee must be Package')
if safety.get('ad_status') != 'Free':
    errors.append('Safety: AdStatus must be Free')
if not safety.get('no_paid_promotion'):
    errors.append('Safety: no_paid_promotion must be true')
if not safety.get('preserve_avito_id'):
    errors.append('Safety: preserve_avito_id must be true')

print(f'VALIDATION_ITEMS {len(items)}')
print(f'VALIDATION_ERRORS {len(errors)}')
for e in errors:
    print('ERROR', e)
print(f'VALIDATION_WARNINGS {len(warnings)}')
for w in warnings:
    print('WARNING', w)
print(f'CONTENT_READY {sum(1 for x in items if x.get("content_ready"))}')
print(f'FEED_READY {sum(1 for x in items if x.get("feed_ready"))}')

if errors:
    raise SystemExit(1)
