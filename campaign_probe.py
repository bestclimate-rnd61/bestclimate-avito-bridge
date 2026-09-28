from typing import Any

from fastapi import FastAPI


def _items_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("resources", "items", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def _safe_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id") or item.get("item_id") or item.get("avito_id"),
        "title": item.get("title") or item.get("name"),
        "price": item.get("price"),
        "status": item.get("status") or item.get("state"),
        "url": item.get("url") or item.get("uri") or item.get("link"),
    }


def _safe_profile(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict):
        return {"available": False}
    feed_urls = profile.get("feed_urls") or profile.get("feeds_urls") or profile.get("feed_url")
    return {
        "available": True,
        "enabled": profile.get("enabled") if "enabled" in profile else profile.get("is_enabled"),
        "status": profile.get("status") or profile.get("state"),
        "feed_urls": feed_urls,
        "schedule": profile.get("schedule") or profile.get("autoload_schedule"),
    }


def register_campaign_probe(app: FastAPI, avito_get) -> None:
    @app.get("/campaign/audit")
    async def campaign_audit() -> dict[str, Any]:
        result: dict[str, Any] = {"ok": True, "profile": None, "aqua_items": []}
        try:
            profile = await avito_get("/autoload/v2/profile")
            result["profile"] = _safe_profile(profile)
        except Exception as exc:
            result["profile_error"] = type(exc).__name__

        matches: list[dict[str, Any]] = []
        for page in range(1, 6):
            try:
                payload = await avito_get(
                    "/core/v1/items",
                    params={"status": "active", "page": page, "per_page": 100},
                )
            except Exception as exc:
                result["items_error"] = type(exc).__name__
                break
            items = _items_list(payload)
            if not items:
                break
            for item in items:
                title = str(item.get("title") or item.get("name") or "")
                upper = title.upper()
                if "AQUA" in upper or "TOWADA" in upper or "АКВА" in upper or "ТОВАД" in upper:
                    matches.append(_safe_item(item))
            if len(items) < 100:
                break
        result["aqua_items"] = matches

        for key, path in (
            ("autoload_current", "/autoload/v4/uploads/current"),
            ("autoload_last_successful", "/autoload/v4/uploads/last_successful"),
        ):
            try:
                payload = await avito_get(path)
                if isinstance(payload, dict):
                    result[key] = {
                        "id": payload.get("id") or payload.get("upload_id"),
                        "status": payload.get("status") or payload.get("state") or payload.get("uploadStatus"),
                    }
                else:
                    result[key] = {"available": payload is not None}
            except Exception as exc:
                result[f"{key}_error"] = type(exc).__name__
        return result
