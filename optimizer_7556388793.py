import asyncio
import json
import os
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI, HTTPException

FEED_URL = "https://bestclimate-avito-bridge-live-production.up.railway.app/feeds/avito/aqua-vladimir-recovery.xml"
TARGETS = {
    7556388793: {
        "price": 79990,
        "ad_id": "BC-7556388793-OPTIMIZED",
        "label": "flagship",
    },
    8324765982: {
        "price": 73305,
        "ad_id": "BC-8324765982-OPTIMIZED",
        "label": "ballu_ice_peak",
    },
}


def _rows(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("resources", "items", "result", "uploads"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


async def _post_avito(api_base: str, get_token: Callable[..., Awaitable[str]], path: str) -> tuple[int, Any]:
    token = await get_token()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{api_base}{path}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401:
            token = await get_token(force_refresh=True)
            response = await client.post(
                f"{api_base}{path}",
                headers={"Authorization": f"Bearer {token}"},
            )
    payload: Any = None
    if response.content:
        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text[:1000]}
    return response.status_code, payload


def register_flagship_optimizer(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
    get_token: Callable[..., Awaitable[str]],
    api_base: str,
) -> None:
    async def _run() -> None:
        await asyncio.sleep(20)
        raw_target = os.getenv("AVITO_OPTIMIZE_TARGET", "").strip()
        try:
            target_id = int(raw_target)
        except (TypeError, ValueError):
            return
        config = TARGETS.get(target_id)
        if config is None:
            return

        target_price = int(config["price"])
        target_ad_id = str(config["ad_id"])
        result: dict[str, Any] = {
            "target": target_id,
            "label": config["label"],
            "upload_requested": False,
        }
        try:
            active = await avito_get(
                "/core/v1/items",
                params={"status": "active", "page": 1, "per_page": 100},
            )
            target = None
            for row in _rows(active):
                if not isinstance(row, dict):
                    continue
                raw_id = row.get("id") or row.get("item_id") or row.get("avito_id")
                try:
                    if int(raw_id) == target_id:
                        target = row
                        break
                except (TypeError, ValueError):
                    continue
            if target is None:
                result["aborted"] = "target_not_active"
                print("AVITO_SAFE_OPTIMIZE " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return
            result["title_before"] = target.get("title")
            result["price_before"] = target.get("price")
            if target.get("price") != target_price:
                result["aborted"] = "unexpected_price"
                print("AVITO_SAFE_OPTIMIZE " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return

            mapping = await avito_get("/autoload/v2/items/ad_ids", params={"query": str(target_id)})
            mapped_ad_id = None
            for row in _rows(mapping):
                if not isinstance(row, dict):
                    continue
                raw = row.get("avito_id")
                try:
                    same = int(raw) == target_id
                except (TypeError, ValueError):
                    same = False
                if same:
                    mapped_ad_id = row.get("ad_id")
                    break
            result["existing_feed_id"] = mapped_ad_id
            if mapped_ad_id not in (None, "", target_ad_id):
                result["aborted"] = "already_managed_by_different_feed_id"
                print("AVITO_SAFE_OPTIMIZE " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return

            profile = await avito_get("/autoload/v2/profile")
            if not isinstance(profile, dict) or profile.get("allow_pay_over_limit") is not False:
                result["aborted"] = "over_limit_protection_not_confirmed"
                print("AVITO_SAFE_OPTIMIZE " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return
            feeds = profile.get("feeds_data")
            if not isinstance(feeds, list) or not any(
                isinstance(feed, dict) and feed.get("feed_url") == FEED_URL for feed in feeds
            ):
                result["aborted"] = "expected_feed_not_configured"
                print("AVITO_SAFE_OPTIMIZE " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return

            status, payload = await _post_avito(api_base, get_token, "/autoload/v1/upload")
            result["upload_http"] = status
            if status >= 400:
                result["upload_error"] = payload
                print("AVITO_SAFE_OPTIMIZE " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return
            result["upload_requested"] = True
            print("AVITO_SAFE_OPTIMIZE " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)

            await asyncio.sleep(50)
            followup: dict[str, Any] = {"target": target_id, "label": config["label"]}
            try:
                current_items = await avito_get(
                    "/autoload/v4/uploads/current/items",
                    params={"page": 1, "perPage": 100, "query": target_ad_id},
                )
                followup["current_items"] = current_items
            except HTTPException as exc:
                followup["current_items_http"] = exc.status_code
            try:
                active_after = await avito_get(
                    "/core/v1/items",
                    params={"status": "active", "page": 1, "per_page": 100},
                )
                for row in _rows(active_after):
                    if not isinstance(row, dict):
                        continue
                    raw_id = row.get("id") or row.get("item_id") or row.get("avito_id")
                    try:
                        if int(raw_id) == target_id:
                            followup["active_after"] = {
                                "id": target_id,
                                "title": row.get("title"),
                                "price": row.get("price"),
                                "status": row.get("status"),
                            }
                            break
                    except (TypeError, ValueError):
                        continue
            except HTTPException as exc:
                followup["active_after_http"] = exc.status_code
            print("AVITO_SAFE_OPTIMIZE_RESULT " + json.dumps(followup, ensure_ascii=False, sort_keys=True), flush=True)
        except HTTPException as exc:
            result["exception_http"] = exc.status_code
            result["exception_detail"] = exc.detail
            print("AVITO_SAFE_OPTIMIZE " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        except Exception as exc:
            result["exception_type"] = type(exc).__name__
            print("AVITO_SAFE_OPTIMIZE " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)

    @app.on_event("startup")
    async def schedule_optimizer() -> None:
        raw_target = os.getenv("AVITO_OPTIMIZE_TARGET", "").strip()
        try:
            target_id = int(raw_target)
        except (TypeError, ValueError):
            return
        if target_id in TARGETS:
            asyncio.create_task(_run())
