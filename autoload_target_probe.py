import asyncio
import json
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, HTTPException

TARGETS = {
    "BC-7556388793-OPTIMIZED": 7556388793,
    "BC-8341283876-RECOVERY": 8341283876,
}


def _rows(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "resources", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _safe_item(row: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "ad_id", "id", "avito_id", "status", "status_detail", "statusDetail",
        "error", "errors", "warning", "warnings", "message", "messages",
        "url", "title", "price", "section", "code", "description",
    )
    out = {key: row.get(key) for key in keep if key in row}
    # Some API versions nest useful moderation/report information.
    for key in ("error_params", "errorParams", "validation", "result"):
        value = row.get(key)
        if value is not None:
            out[key] = value
    return out


def register_autoload_target_probe(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
) -> None:
    async def collect() -> dict[str, Any]:
        result: dict[str, Any] = {"targets": {}}
        try:
            upload = await avito_get("/autoload/v4/uploads/last_successful")
            if isinstance(upload, dict):
                result["upload"] = {
                    key: upload.get(key)
                    for key in ("upload_id", "id", "status", "start_time", "finish_time", "url")
                    if key in upload
                }
        except HTTPException as exc:
            result["upload_http"] = exc.status_code

        payload = None
        try:
            payload = await avito_get(
                "/autoload/v4/uploads/last_successful/items",
                params={"page": 1, "perPage": 100},
            )
        except HTTPException as exc:
            result["items_http"] = exc.status_code
            result["items_detail"] = str(exc.detail)[:500]
            return result

        rows = _rows(payload)
        result["item_count_returned"] = len(rows)
        if isinstance(payload, dict) and isinstance(payload.get("meta"), dict):
            result["meta"] = payload["meta"]

        for ad_id, avito_id in TARGETS.items():
            matches = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                row_ad = row.get("ad_id") or row.get("id")
                row_avito = row.get("avito_id") or row.get("avitoId")
                same = str(row_ad) == ad_id
                if not same:
                    try:
                        same = int(row_avito) == avito_id
                    except (TypeError, ValueError):
                        same = False
                if same:
                    matches.append(_safe_item(row))
            result["targets"][ad_id] = {"avito_id": avito_id, "matches": matches}
        return result

    @app.get("/diagnostic/autoload-targets", include_in_schema=False)
    async def autoload_targets() -> dict[str, Any]:
        return await collect()

    @app.on_event("startup")
    async def schedule_probe() -> None:
        async def run() -> None:
            await asyncio.sleep(12)
            try:
                data = await collect()
                print("AVITO_AUTOLOAD_TARGETS " + json.dumps(data, ensure_ascii=False, sort_keys=True), flush=True)
            except Exception as exc:
                print("AVITO_AUTOLOAD_TARGETS " + json.dumps({"error": type(exc).__name__}), flush=True)
        asyncio.create_task(run())
