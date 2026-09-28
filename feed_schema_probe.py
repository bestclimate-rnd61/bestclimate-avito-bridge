import asyncio, json, os
import httpx

BASE=os.getenv('AVITO_API_BASE','https://api.avito.ru').rstrip('/')
CID=os.getenv('AVITO_CLIENT_ID','')
CSEC=os.getenv('AVITO_CLIENT_SECRET','')
SELECTED={8036734662,8036643856,8036277086,7748832830,3717069010,8292735844,8292158882,7556388793,4228840511,7332855703}
SLUGS=['kondicioneri','zapchasti_kondicionery','kondicionirovanie','ventilyaciya','ventiljatsija']

async def token(c):
    r=await c.post(f'{BASE}/token',data={'grant_type':'client_credentials','client_id':CID,'client_secret':CSEC},headers={'Content-Type':'application/x-www-form-urlencoded'})
    r.raise_for_status(); return r.json()['access_token']

def summarize_field(f):
    contents=f.get('content') or []
    required=any(bool(x.get('required') or x.get('required_by_dependency')) for x in contents if isinstance(x,dict))
    vals=[]
    for x in contents:
        if isinstance(x,dict):
            for v in x.get('values') or []:
                if isinstance(v,dict) and 'value' in v: vals.append(v['value'])
    return {'tag':f.get('tag'),'label':f.get('label'),'required':required,'values':vals[:30]}

def compact_item(x):
    keep=['id','itemId','title','status','url','price','category','categoryId','category_id','address','location','description','images','imageUrls','photos']
    d={k:x.get(k) for k in keep if x.get(k) is not None}
    d['_keys']=sorted(x.keys())
    return d

async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        t=await token(c); h={'Authorization':f'Bearer {t}'}
        for slug in SLUGS:
            r=await c.get(f'{BASE}/autoload/v1/user-docs/node/{slug}/fields',headers=h)
            print('SCHEMA_STATUS',slug,r.status_code,flush=True)
            if r.status_code==200:
                data=r.json(); fs=data.get('fields') or []
                rows=[summarize_field(f) for f in fs if isinstance(f,dict)]
                keytags={'Id','AvitoId','Category','GoodsType','AdType','Title','Description','Price','Address','SellerAddressID','ContactPhone','ManagerName','Images','ImageUrls','ImageNames','Condition','Brand','Model','Type','ListingFee','AdStatus','ContactMethod','NDS'}
                picked=[x for x in rows if x['required'] or x['tag'] in keytags]
                print('SCHEMA',slug,json.dumps(picked,ensure_ascii=False),flush=True)
        found=[]
        for page in range(1,11):
            r=await c.get(f'{BASE}/core/v1/items',headers=h,params={'status':'active','page':page,'per_page':100})
            r.raise_for_status(); data=r.json(); resources=data.get('resources') or []
            for x in resources:
                try: iid=int(x.get('id') or x.get('itemId'))
                except Exception: continue
                if iid in SELECTED: found.append(compact_item(x))
            if len(resources)<100: break
        print('SELECTED_COUNT',len(found),flush=True)
        for x in found: print('SELECTED_ITEM',json.dumps(x,ensure_ascii=False)[:20000],flush=True)

if __name__=='__main__': asyncio.run(main())
