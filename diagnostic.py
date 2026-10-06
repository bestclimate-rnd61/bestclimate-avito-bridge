import json
import os
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, HTTPException

TARGET_DETAIL_IDS = [8479764928, 8461285020, 8324639588, 8305258576, 4228840511, 4228587935]
BLOCKED_AQUA_ID = 8341283876


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


def _aqua_towada_matches(payload: Any) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for row in _list_from_payload(payload):
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or row.get("name") or "")
        haystack = title.lower()
        if "aqua" not in haystack and "towada" not in haystack and "тепловой насос" not in haystack:
            continue
        compact = _item_sample({"resources": [row]}, limit=1)
        if compact:
            matches.append(compact[0])
    return matches


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


def _safe_feed_profile(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("autoload_enabled", "uploadMode", "allow_pay_over_limit"):
        value = profile.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
    feeds = profile.get("feeds_data")
    if isinstance(feeds, list):
        safe_feeds: list[dict[str, Any]] = []
        for feed in feeds:
            if not isinstance(feed, dict):
                continue
            row: dict[str, Any] = {}
            for key in ("feed_name", "feed_url", "name", "url"):
                value = feed.get(key)
                if isinstance(value, str):
                    row[key] = value[:500]
            if row:
                safe_feeds.append(row)
        out["feeds_data"] = safe_feeds
    schedule = profile.get("schedule")
    if isinstance(schedule, list):
        out["schedule"] = schedule
    return out


def register_readonly_diagnostic(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
    count_items: Callable[[Any], int | None],
    account_id_getter: Callable[[], Awaitable[int]],
) -> None:
    @app.on_event("startup")
    async def readonly_diagnostic() -> None:
        if os.getenv("SKIP_STARTUP_DIAGNOSTIC", "") == "1":
            print("AVITO_READONLY_DIAGNOSTIC_SKIPPED", flush=True)
            return
        diag: dict[str, Any] = {
            "autoload_profile_ok": False,
            "autoload_uploads_count": None,
            "autoload_profile_safe": {},
            "blocked_autoload_mapping": None,
            "active_items": None,
            "active_sample": [],
            "blocked_items": None,
            "blocked_sample": [],
            "blocked_details": [],
            "aqua_history_matches": {},
            "aqua_history_details": [],
            "selected_details": [],
        }

        try:
            profile = await avito_get("/autoload/v2/profile")
            diag["autoload_profile_ok"] = isinstance(profile, dict)
            diag["autoload_profile_safe"] = _safe_feed_profile(profile)
            if isinstance(profile, dict):
                diag["autoload_profile_keys"] = sorted(str(k) for k in profile.keys())[:25]
                for key in ("autoload_enabled", "uploadMode", "schedule", "allow_pay_over_limit"):
                    value = profile.get(key)
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        diag[f"autoload_{key}"] = value
        except HTTPException as exc:
            diag["autoload_profile_http"] = exc.status_code

        try:
            diag["blocked_autoload_mapping"] = await avito_get(
                "/autoload/v2/items/ad_ids",
                params={"query": str(BLOCKED_AQUA_ID)},
            )
        except HTTPException as exc:
            diag["blocked_autoload_mapping_http"] = exc.status_code

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

        active_rows: list[Any] = []
        try:
            items = await avito_get(
                "/core/v1/items",
                params={"status": "active", "page": 1, "per_page": 100},
            )
            diag["active_items"] = count_items(items)
            active_rows = _list_from_payload(items)
            diag["active_sample"] = _item_sample(items)
            diag["aqua_history_matches"]["active"] = _aqua_towada_matches(items)
        except HTTPException as exc:
            diag["items_http"] = exc.status_code

        blocked_rows: list[Any] = []
        try:
            blocked = await avito_get(
                "/core/v1/items",
                params={"status": "blocked", "page": 1, "per_page": 100},
            )
            diag["blocked_items"] = count_items(blocked)
            blocked_rows = _list_from_payload(blocked)
            if diag["blocked_items"] is None:
                diag["blocked_items"] = len(blocked_rows)
            diag["blocked_sample"] = _item_sample(blocked, limit=100)
            diag["aqua_history_matches"]["blocked"] = _aqua_towada_matches(blocked)
        except HTTPException as exc:
            diag["blocked_items_http"] = exc.status_code

        history_rows: list[Any] = []
        for status_name in ("old", "removed", "rejected"):
            try:
                payload = await avito_get(
                    "/core/v1/items",
                    params={"status": status_name, "page": 1, "per_page": 100},
                )
                rows = _list_from_payload(payload)
                history_rows.extend(rows)
                diag["aqua_history_matches"][status_name] = _aqua_towada_matches(payload)
            except HTTPException as exc:
                diag[f"{status_name}_items_http"] = exc.status_code

        try:
            user_id = await account_id_getter()

            blocked_ids: list[int] = []
            for row in blocked_rows:
                if not isinstance(row, dict):
                    continue
                raw_id = row.get("id") or row.get("item_id") or row.get("avito_id")
                try:
                    blocked_ids.append(int(raw_id))
                except (TypeError, ValueError):
                    continue

            for item_id in blocked_ids[:100]:
                try:
                    detail = await avito_get(f"/core/v1/accounts/{user_id}/items/{item_id}/")
                    diag["blocked_details"].append(_detail_summary(detail, item_id))
                except HTTPException as exc:
                    diag["blocked_details"].append({"requested_id": item_id, "http": exc.status_code})

            seen_history: set[int] = set()
            for row in active_rows + history_rows:
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or row.get("name") or "").lower()
                if "aqua" not in title and "towada" not in title and "тепловой насос" not in title:
                    continue
                raw_id = row.get("id") or row.get("item_id") or row.get("avito_id")
                try:
                    item_id = int(raw_id)
                except (TypeError, ValueError):
                    continue
                if item_id in seen_history:
                    continue
                seen_history.add(item_id)
                try:
                    detail = await avito_get(f"/core/v1/accounts/{user_id}/items/{item_id}/")
                    diag["aqua_history_details"].append(_detail_summary(detail, item_id))
                except HTTPException as exc:
                    diag["aqua_history_details"].append({"requested_id": item_id, "http": exc.status_code})

            for item_id in TARGET_DETAIL_IDS:
                try:
                    detail = await avito_get(f"/core/v1/accounts/{user_id}/items/{item_id}/")
                    diag["selected_details"].append(_detail_summary(detail, item_id))
                except HTTPException as exc:
                    diag["selected_details"].append({"requested_id": item_id, "http": exc.status_code})
        except HTTPException as exc:
            diag["selected_details_account_http"] = exc.status_code

        print(
            "AVITO_READONLY_DIAGNOSTIC "
            + json.dumps(diag, ensure_ascii=False, sort_keys=True),
            flush=True,
        )
