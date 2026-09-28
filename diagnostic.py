import json
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, HTTPException

TARGET_DETAIL_IDS = [8479764928, 8461285020, 8324639588, 8305258576, 4228840511, 4228587935]


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


def _detail_summary(payload: Any, requested_id: int) -> dict[str, Any]:
    result: dict[str, Any] = {"requested_id": requested_id}
    if not isinstance(payload, dict):
        result["response_type"] = type(payload).__name__
        return result
    for key in (
        "id",
        "title",
        "status",
        "price",
        "address",
        "city",
        "category",
        "category_id",
        "url",
    ):
        value = payload.get(key)
        if isinstance(value, (str, int, float, bool)):
            result[key] = value
    result["keys"] = sorted(str(k) for k in payload.keys())[:30]
    return result


def register_readonly_diagnostic(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
    count_items: Callable[[Any], int | None],
    account_id_getter: Callable[[], Awaitable[int]],
) -> None:
    @app.on_event("startup")
    async def readonly_diagnostic() -> None:
        diag: dict[str, Any] = {
            "autoload_profile_ok": False,
            "autoload_uploads_count": None,
            "active_items": None,
            "active_sample": [],
            "selected_details": [],
        }

        try:
            profile = await avito_get("/autoload/v2/profile")
            diag["autoload_profile_ok"] = isinstance(profile, dict)
            if isinstance(profile, dict):
                diag["autoload_profile_keys"] = sorted(str(k) for k in profile.keys())[:25]
                for key in ("autoload_enabled", "uploadMode", "schedule", "allow_pay_over_limit"):
                    value = profile.get(key)
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        diag[f"autoload_{key}"] = value
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

        try:
            user_id = await account_id_getter()
            for item_id in TARGET_DETAIL_IDS:
                try:
                    detail = await avito_get(f"/core/v1/accounts/{user_id}/items/{item_id}/")
                    diag["selected_details"].append(_detail_summary(detail, item_id))
                except HTTPException as exc:
                    diag["selected_details"].append(
                        {"requested_id": item_id, "http": exc.status_code}
                    )
        except HTTPException as exc:
            diag["selected_details_account_http"] = exc.status_code

        print(
            "AVITO_READONLY_DIAGNOSTIC "
            + json.dumps(diag, ensure_ascii=False, sort_keys=True),
            flush=True,
        )
