from fastapi import FastAPI, Response, HTTPException
import httpx

app = FastAPI()

SOURCES = {
    "start": "https://at.adobe.com/Q9yNDGlWoDN4tG5f",
    "ai-business": "https://at.adobe.com/hPucrN3WEMY2uPHw",
    "automation": "https://at.adobe.com/rFOWGiVRopESmgUg",
    "cases": "https://at.adobe.com/GeJXp7ZbaZO5UyLw",
    "tools": "https://at.adobe.com/hg5NgAyscbbaJnWB",
    "audit": "https://at.adobe.com/PmUOzEEQw1w3tgaq",
    "about": "https://at.adobe.com/5CWj31wSiQZdX1vF",
    "faq": "https://at.adobe.com/sPq539cYMcLUaHbr",
}

@app.get('/health')
def health():
    return {'ok': True}

@app.get('/highlights/{slug}.png')
async def highlight(slug: str):
    url = SOURCES.get(slug)
    if not url:
        raise HTTPException(status_code=404, detail='not found')
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        r = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f'upstream {r.status_code}')
    content_type = r.headers.get('content-type', 'image/png')
    return Response(content=r.content, media_type=content_type, headers={'Cache-Control':'public, max-age=3600'})
