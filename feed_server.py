import base64
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response


HAIER_FEED_PATH = Path(__file__).with_name("avito_feed_batch_01_haier.xml")
AQUA_VLADIMIR_RECOVERY_FEED_PATH = Path(__file__).with_name("avito_feed_aqua_vladimir_recovery.xml")
AQUA_VLADIMIR_IMAGE_B64_PATH = Path(__file__).with_name("aqua_vladimir_main_sq400_q15.b64")


def _xml_response(path: Path) -> Response:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Feed file is missing")
    return Response(
        content=path.read_text(encoding="utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


def _local_aqua_image() -> bytes:
    if not AQUA_VLADIMIR_IMAGE_B64_PATH.exists():
        raise HTTPException(status_code=404, detail="AQUA recovery image payload is missing")
    try:
        content = base64.b64decode(
            AQUA_VLADIMIR_IMAGE_B64_PATH.read_text(encoding="ascii").strip(),
            validate=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AQUA recovery image payload is invalid") from exc
    if len(content) < 1024 or not content.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=500, detail="AQUA recovery image is not a valid JPEG")
    return content


def register_feed_server(app: FastAPI) -> None:
    @app.get("/feeds/avito/haier-batch-01.xml", include_in_schema=False)
    async def haier_feed() -> Response:
        return _xml_response(HAIER_FEED_PATH)

    @app.get("/feeds/avito/aqua-vladimir-recovery.xml", include_in_schema=False)
    async def aqua_vladimir_recovery_feed() -> Response:
        return _xml_response(AQUA_VLADIMIR_RECOVERY_FEED_PATH)

    @app.get("/feeds/avito/growth.xml", include_in_schema=False)
    async def growth_feed() -> Response:
        content = os.environ.get("AVITO_GROWTH_FEED_XML", "").strip()
        if not content:
            raise HTTPException(status_code=404, detail="Growth feed is not configured")
        return Response(
            content=content,
            media_type="application/xml; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    @app.get("/media/aqua-towada-aqi-25fis1-r3-w.jpg", include_in_schema=False)
    async def aqua_towada_product_image() -> Response:
        return Response(
            content=_local_aqua_image(),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )
