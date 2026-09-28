import json
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, HTTPException


def _list_from_payload(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("resources", "items", "result", "uploads"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _item_sample(payload: Any, limit: int = 30) -> list[dict[str, Any]]:
    rows = _list_from_payload(payload)
    result: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        compact: dict[str, Any] = {}
        for out_key, keys in {
            "id": ("id", "item_id", "avito_id"),
            "title": ("title", "name"),
            "status": ("status", "state"),
            "price": ("price",),
        }.items():
            for key in keys:
                value = row.get(key)
                if isinstance(value, (str, int, float, bool)):
                    compact[out_key] = value
                    break
        if compact:
            result.append(compact)
    return result


def register_readonly_diagnostic(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
    count_items: Callable[[Any], int | None],
) -> None:
    @app.on_event("startup")
    async def readonly_diagnostic() -> None:
        diag: dict[str, Any] = {
            "autoload_profile_ok": False,
            "autoload_uploads_count": None,
            "active_items": None,
            "active_sample": [],
        }

        try:
            profile = await avito_get("/autoload/v2/profile")
            diag["autoload_profile_ok"] = isinstance(profile, dict)
            if isinstance(profile, dict):
                diag["autoload_profile_keys"] = sorted(str(k) for k in profile.keys())[:25]
        except HTTPException as exc:
            diag["autoload_profile_http"] = exc.status_code

        try:
            uploads = await avito_get(
                "/autoload/v4/uploads",
                params={"page": 1, "perPage": 20},
            )
            diag["autoload_uploads_count"] = count_items(uploads)
            if diag["autoload_uploads_count"] is None:
                diag["autoload_uploads_count"] = len(_list_from_payload(uploads))
        except HTTPException as exc:
            diag["autoload_uploads_http"] = exc.status_code

        try:
            items = await avito_get(
                "/core/v1/items",
                params={"status": "active", "page": 1, "per_page": 100},
            )
            diag["active_items"] = count_items(items)
            diag["active_sample"] = _item_sample(items)
        except HTTPException as exc:
            diag["items_http"] = exc.status_code

        print(
            "AVITO_READONLY_DIAGNOSTIC "
            + json.dumps(diag, ensure_ascii=False, sort_keys=True),
            flush=True,
        )
