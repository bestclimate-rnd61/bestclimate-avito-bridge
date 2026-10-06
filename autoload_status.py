
from typing import Any, Awaitable, Callable
from fastapi import FastAPI, HTTPException


def register_autoload_status(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
) -> None:
    def compact_upload(data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {"valid": False}
        safe: dict[str, Any] = {"valid": True}
        for key in ("upload_id", "id", "status", "start_time", "finish_time", "url", "total", "count"):
            if key in data:
                safe[key] = data.get(key)
        return safe

    def compact_items(data: Any) -> dict[str, Any]:
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items") or data.get("resources") or data.get("result") or []
        else:
            items = []
        if not isinstance(items, list):
            items = []
        statuses: dict[str, int] = {}
        samples: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or item.get("state") or "unknown")
            statuses[status] = statuses.get(status, 0) + 1
            if len(samples) < 10:
                samples.append({
                    k: item.get(k)
                    for k in ("ad_id", "id", "avito_id", "status", "state", "title", "error", "message")
                    if k in item
                })
        return {"count": len(items), "statuses": statuses, "sample": samples}

    @app.get("/admin/autoload/status-safe", include_in_schema=False)
    async def autoload_status_safe() -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, path in (
            ("current", "/autoload/v4/uploads/current"),
            ("last_successful", "/autoload/v4/uploads/last_successful"),
        ):
            try:
                result[name] = compact_upload(await avito_get(path))
            except HTTPException as exc:
                result[name] = {"http": exc.status_code}
        for name, path in (
            ("current_items", "/autoload/v4/uploads/current/items"),
            ("last_successful_items", "/autoload/v4/uploads/last_successful/items"),
        ):
            try:
                result[name] = compact_items(await avito_get(path))
            except HTTPException as exc:
                result[name] = {"http": exc.status_code}
        return result
