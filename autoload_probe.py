import json
import os
import httpx

BASE = os.getenv('AVITO_API_BASE', 'https://api.avito.ru').rstrip('/')
CID = os.getenv('AVITO_CLIENT_ID', '')
SECRET = os.getenv('AVITO_CLIENT_SECRET', '')
ITEM_IDS = [8036734662,8036643856,8036277086,7748832830,3717069010,8292735844,8292158882,7556388793,4228840511,7332855703]

def safe_print(prefix, payload):
    print(prefix + ' ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')), flush=True)

with httpx.Client(timeout=30) as client:
    tok = client.post(f'{BASE}/token', data={
        'grant_type':'client_credentials',
        'client_id': CID,
        'client_secret': SECRET,
    }, headers={'Content-Type':'application/x-www-form-urlencoded'})
    tok.raise_for_status()
    token = tok.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    r = client.get(f'{BASE}/autoload/v2/profile', headers=headers)
    profile = {'status': r.status_code}
    try:
        body = r.json()
        if isinstance(body, dict):
            profile['keys'] = sorted(body.keys())
            for k in ('autoload_enabled','autoloadEnabled','report_email','reportEmail','schedule','feeds_data','feedsData'):
                if k in body:
                    profile[k] = body[k]
        else:
            profile['body_type'] = type(body).__name__
    except Exception:
        profile['text'] = r.text[:300]
    safe_print('AUTOLOAD_PROFILE', profile)

    query = ','.join(str(x) for x in ITEM_IDS)
    m = client.get(f'{BASE}/autoload/v2/items/ad_ids', params={'query': query}, headers=headers)
    mapping = {'status': m.status_code}
    try:
        mb = m.json()
        mapping['body'] = mb
    except Exception:
        mapping['text'] = m.text[:500]
    safe_print('AUTOLOAD_MAPPING', mapping)
