import json
import os
import httpx

BASE = os.getenv('AVITO_API_BASE', 'https://api.avito.ru').rstrip('/')
CID = os.getenv('AVITO_CLIENT_ID', '')
SECRET = os.getenv('AVITO_CLIENT_SECRET', '')

TARGETS = {
    'kondicioneri': {
        'AdType','Vendor','AirConditionerType','AirConditionerSubType','Images','ImageUrls','ImageNames',
        'WholesaleMinOrderType','WholesaleMinOrderCount','WholesalePacking','WholesaleDiscountLadderType',
        'DiscountLadderList','NDS','ContactMethod','Address','Price'
    },
    'ventiljatsija': {
        'Specialty','WorkExperience','TeamSize','Guarantee','MaterialPurchase','Images','ImageUrls','ImageNames',
        'ContactMethod','Address','Price'
    },
}


def compact_content(entry):
    if not isinstance(entry, dict):
        return entry
    return {
        'required': bool(entry.get('required')),
        'required_by_dependency': bool(entry.get('required_by_dependency')),
        'dependencies_text': entry.get('dependencies_text'),
        'default': entry.get('default'),
        'field_type': entry.get('field_type'),
        'data_type': entry.get('data_type'),
        'values': [v.get('value') for v in (entry.get('values') or []) if isinstance(v, dict) and 'value' in v],
    }

with httpx.Client(timeout=30) as c:
    tok = c.post(
        f'{BASE}/token',
        data={'grant_type':'client_credentials','client_id':CID,'client_secret':SECRET},
        headers={'Content-Type':'application/x-www-form-urlencoded'}
    )
    tok.raise_for_status()
    token = tok.json()['access_token']
    h = {'Authorization': f'Bearer {token}'}

    for slug, wanted in TARGETS.items():
        r = c.get(f'{BASE}/autoload/v1/user-docs/node/{slug}/fields', headers=h)
        print('COND_SCHEMA_STATUS', slug, r.status_code, flush=True)
        r.raise_for_status()
        data = r.json()
        for field in data.get('fields') or []:
            if not isinstance(field, dict) or field.get('tag') not in wanted:
                continue
            row = {
                'slug': slug,
                'tag': field.get('tag'),
                'label': field.get('label'),
                'descriptions': field.get('descriptions'),
                'content': [compact_content(x) for x in (field.get('content') or [])],
            }
            print('COND_FIELD', json.dumps(row, ensure_ascii=False), flush=True)
