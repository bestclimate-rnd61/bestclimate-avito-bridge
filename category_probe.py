import asyncio
import json
import os

import httpx

BASE = os.getenv("AVITO_API_BASE", "https://api.avito.ru").rstrip("/")
CID = os.getenv("AVITO_CLIENT_ID", "")
CSEC = os.getenv("AVITO_CLIENT_SECRET", "")

async def token(client):
    r = await client.post(
        f"{BASE}/token",
        data={"grant_type":"client_credentials","client_id":CID,"client_secret":CSEC},
        headers={"Content-Type":"application/x-www-form-urlencoded"},
    )
    r.raise_for_status()
    return r.json()["access_token"]

def walk(node, out):
    if isinstance(node, dict):
        name = str(node.get("name") or node.get("title") or node.get("label") or "")
        slug = node.get("slug") or node.get("id") or node.get("value")
        text = json.dumps(node, ensure_ascii=False).lower()
        keys = ("кондиц", "сплит", "климат", "бытовая техник", "вентиляц", "теплов")
        if any(k in text for k in keys):
            out.append({"name": name, "slug": slug, "keys": sorted(node.keys())})
        for v in node.values():
            walk(v, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, out)

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        t = await token(client)
        h = {"Authorization": f"Bearer {t}"}
        r = await client.get(f"{BASE}/autoload/v1/user-docs/tree", headers=h)
        print("CATEGORY_TREE_STATUS", r.status_code, flush=True)
        try:
            data = r.json()
        except Exception:
            print("CATEGORY_TREE_NONJSON", r.text[:500], flush=True)
            return
        hits=[]
        walk(data, hits)
        print("CATEGORY_HITS", json.dumps(hits[:100], ensure_ascii=False), flush=True)

        slugs=[]
        for x in hits:
            s=x.get("slug")
            if isinstance(s,str) and s and s not in slugs:
                slugs.append(s)
        for s in slugs[:20]:
            fr = await client.get(f"{BASE}/autoload/v1/user-docs/node/{s}/fields", headers=h)
            if fr.status_code != 200:
                continue
            try:
                fd=fr.json()
            except Exception:
                continue
            txt=json.dumps(fd, ensure_ascii=False).lower()
            if any(k in txt for k in ("кондиц", "сплит", "мощност", "бренд", "описан", "цена")):
                print("CATEGORY_FIELDS", json.dumps({"slug":s,"fields":fd}, ensure_ascii=False)[:12000], flush=True)

if __name__ == "__main__":
    asyncio.run(main())
