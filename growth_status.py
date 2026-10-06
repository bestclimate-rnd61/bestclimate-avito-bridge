from typing import Any, Awaitable, Callable

from fastapi import FastAPI, HTTPException


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("items", "resources", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def register_growth_status(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
) -> None:
    @app.get("/admin/autoload/growth-status", include_in_schema=False)
    async def growth_status() -> dict[str, Any]:
        current = await avito_get("/autoload/v4/uploads/current")
        items: list[dict[str, Any]] = []
        seen: set[str] = set()

        for page in range(1, 12):
            try:
                payload = await avito_get(
                    "/autoload/v4/uploads/current/items",
                    params={"page": page, "perPage": 100},
                )
            except HTTPException:
                break
            page_rows = _rows(payload)
            if not page_rows:
                break
            added = 0
            for row in page_rows:
                key = str(row.get("ad_id") or row.get("id") or row.get("avito_id") or "")
                if not key or key in seen:
                    continue
                seen.add(key)
                items.append(row)
                added += 1
            if added == 0 or len(page_rows) < 100:
                break

        statuses: dict[str, int] = {}
        with_avito_id = 0
        growth_items = 0
        samples: list[dict[str, Any]] = []
        for row in items:
            status = str(row.get("status") or row.get("state") or "unknown")
            statuses[status] = statuses.get(status, 0) + 1
            ad_id = str(row.get("ad_id") or row.get("id") or "")
            if ad_id.startswith("BC-GROWTH-"):
                growth_items += 1
            if row.get("avito_id"):
                with_avito_id += 1
            if len(samples) < 12:
                samples.append({
                    k: row.get(k)
                    for k in ("ad_id", "id", "avito_id", "status", "state", "title", "error", "message")
                    if k in row
                })

        return {
            "upload": {
                k: current.get(k)
                for k in ("upload_id", "id", "status", "start_time", "finish_time")
                if isinstance(current, dict) and k in current
            },
            "items_total": len(items),
            "growth_items": growth_items,
            "with_avito_id": with_avito_id,
            "statuses": statuses,
            "sample": samples,
        }
