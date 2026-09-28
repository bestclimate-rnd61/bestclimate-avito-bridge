import asyncio, json, os
import httpx

BASE=os.getenv('AVITO_API_BASE','https://api.avito.ru').rstrip('/')
CID=os.getenv('AVITO_CLIENT_ID','')
CSEC=os.getenv('AVITO_CLIENT_SECRET','')
SLUGS=['kondicioneri','kondicionery_i_zapchasti','kondicionery_i_ventilyaciya','kondicionirovanie','ventiljatsija']

async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.post(f'{BASE}/token',data={'grant_type':'client_credentials','client_id':CID,'client_secret':CSEC},headers={'Content-Type':'application/x-www-form-urlencoded'})
        r.raise_for_status(); t=r.json()['access_token']; h={'Authorization':f'Bearer {t}'}
        for s in SLUGS:
            fr=await c.get(f'{BASE}/autoload/v1/user-docs/node/{s}/fields',headers=h)
            print('EXACT_STATUS',json.dumps({'slug':s,'status':fr.status_code},ensure_ascii=False),flush=True)
            if fr.status_code!=200: continue
            fd=fr.json(); out=[]
            for f in fd.get('fields',[]):
                tag=f.get('tag'); label=f.get('label'); req=False; vals=[]
                for ct in f.get('content') or []:
                    req=req or bool(ct.get('required')) or bool(ct.get('required_by_dependency'))
                    for v in ct.get('values') or []:
                        if isinstance(v,dict) and 'value' in v: vals.append(v['value'])
                if tag in {'Id','AvitoId','Title','Description','Category','GoodsType','ProductType','Brand','Model','Condition','Price','ListingFee','AdStatus','Address','Images','ContactMethod','ManagerName','ContactPhone','NDS'} or req:
                    out.append({'tag':tag,'label':label,'required':req,'values':vals[:40]})
            print('EXACT_FIELDS',json.dumps({'slug':s,'fields':out},ensure_ascii=False),flush=True)

asyncio.run(main())
