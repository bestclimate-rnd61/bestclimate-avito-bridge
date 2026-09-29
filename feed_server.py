from pathlib import Path

from fastapi import FastAPI, HTTPException, Response


FEED_PATH = Path(__file__).with_name("avito_feed_batch_01_haier.xml")


def register_feed_server(app: FastAPI) -> None:
    @app.get("/feeds/avito/haier-batch-01.xml", include_in_schema=False)
    async def haier_feed() -> Response:
        """Public static XML feed draft for Avito Autoload.

        Serving the feed does NOT configure Avito or trigger an upload. The feed
        remains inert until the Autoload profile is explicitly pointed at this URL
        and a full upload is explicitly started.
        """
        if not FEED_PATH.exists():
            raise HTTPException(status_code=404, detail="Feed file is missing")
        return Response(
            content=FEED_PATH.read_text(encoding="utf-8"),
            media_type="application/xml; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
