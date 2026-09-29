from pathlib import Path

from fastapi import FastAPI, HTTPException, Response


HAIER_FEED_PATH = Path(__file__).with_name("avito_feed_batch_01_haier.xml")
AQUA_VLADIMIR_RECOVERY_FEED_PATH = Path(__file__).with_name("avito_feed_aqua_vladimir_recovery.xml")


def _xml_response(path: Path) -> Response:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Feed file is missing")
    return Response(
        content=path.read_text(encoding="utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


def register_feed_server(app: FastAPI) -> None:
    @app.get("/feeds/avito/haier-batch-01.xml", include_in_schema=False)
    async def haier_feed() -> Response:
        """Public static XML feed draft for Avito Autoload."""
        return _xml_response(HAIER_FEED_PATH)

    @app.get("/feeds/avito/aqua-vladimir-recovery.xml", include_in_schema=False)
    async def aqua_vladimir_recovery_feed() -> Response:
        """Single existing-ad recovery feed for Avito ID 8341283876.

        The row includes AvitoId so Autoload targets the already-created blocked
        Vladimir card instead of intentionally creating a second listing.
        """
        return _xml_response(AQUA_VLADIMIR_RECOVERY_FEED_PATH)
