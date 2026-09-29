import re
from pathlib import Path
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, HTTPException, Response


HAIER_FEED_PATH = Path(__file__).with_name("avito_feed_batch_01_haier.xml")
AQUA_VLADIMIR_RECOVERY_FEED_PATH = Path(__file__).with_name("avito_feed_aqua_vladimir_recovery.xml")
AQUA_OFFICIAL_PRODUCT_URL = (
    "https://aqua-russia.ru/catalog/house_split/towada/"
    "aqua-aqi-25fis1-r3-w-in-aqua-aqi-25fis1-r3-out/"
)


def _xml_response(path: Path) -> Response:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Feed file is missing")
    return Response(
        content=path.read_text(encoding="utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


async def _official_aqua_image() -> tuple[bytes, str]:
    """Fetch the exact AQI-25FIS1/R3-W product image from AQUA's official site.

    The upstream URL is fixed in code: callers cannot turn this endpoint into an
    arbitrary proxy. We prefer OpenGraph/Twitter product imagery and fall back to
    the first raster image URL present in the official product page.
    """
    headers = {"User-Agent": "BestClimate-Autoload/1.0"}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
        page = await client.get(AQUA_OFFICIAL_PRODUCT_URL)
        page.raise_for_status()
        html = page.text
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
            r'<img[^>]+src=["\']([^"\']+\.(?:jpe?g|png|webp)(?:\?[^"\']*)?)["\']',
        ]
        image_url = None
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                image_url = urljoin(AQUA_OFFICIAL_PRODUCT_URL, match.group(1))
                break
        if not image_url:
            raise HTTPException(status_code=502, detail="Official AQUA product image not found")
        image = await client.get(image_url)
        image.raise_for_status()
        content_type = image.headers.get("content-type", "image/jpeg").split(";", 1)[0].strip().lower()
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=502, detail="Official AQUA image has unsupported content type")
        if len(image.content) < 1024:
            raise HTTPException(status_code=502, detail="Official AQUA image payload is unexpectedly small")
        return image.content, content_type


def register_feed_server(app: FastAPI) -> None:
    @app.get("/feeds/avito/haier-batch-01.xml", include_in_schema=False)
    async def haier_feed() -> Response:
        return _xml_response(HAIER_FEED_PATH)

    @app.get("/feeds/avito/aqua-vladimir-recovery.xml", include_in_schema=False)
    async def aqua_vladimir_recovery_feed() -> Response:
        return _xml_response(AQUA_VLADIMIR_RECOVERY_FEED_PATH)

    @app.get("/media/aqua-towada-aqi-25fis1-r3-w.jpg", include_in_schema=False)
    async def aqua_towada_product_image() -> Response:
        content, content_type = await _official_aqua_image()
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )
