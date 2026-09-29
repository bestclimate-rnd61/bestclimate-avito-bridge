import asyncio
import json
import os
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI

TARGET_AVITO_ID = 8341283876
RECOVERY_AD_ID = "BC-8341283876-RECOVERY"
RECOVERY_FEED_URL = "https://bestclimate-avito-bridge-live-production.up.railway.app/feeds/avito/aqua-vladimir-recovery.xml"


def _rows(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("resources", "items", "result", "uploads"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


async def _post_upload(api_base: str, get_token: Callable[..., Awaitable[str]]) -> int:
    token = await get_token()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{api_base}/autoload/v1/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401:
            token = await get_token(force_refresh=True)
            response = await client.post(
                f"{api_base}/autoload/v1/upload",
                headers={"Authorization": f"Bearer {token}"},
            )
    return response.status_code


def register_recovery_retry(app: FastAPI, avito_get, get_token, api_base: str) -> None:
    async def _run() -> None:
        await asyncio.sleep(20)
        if os.getenv("AVITO_RECOVERY_RETRY_TARGET", "").strip() != str(TARGET_AVITO_ID):
            return
        result: dict[str, Any] = {"target": TARGET_AVITO_ID, "retry": False}
        try:
            blocked = await avito_get("/core/v1/items", params={"status": "blocked", "page": 1, "per_page": 100})
            target = next((r for r in _rows(blocked) if isinstance(r, dict) and r.get("id") == TARGET_AVITO_ID), None)
            if not target or target.get("price") != 65400:
                result["aborted"] = "target_or_price_changed"
                print("AVITO_RECOVERY_RETRY " + json.dumps(result, ensure_ascii=False), flush=True)
                return

            profile = await avito_get("/autoload/v2/profile")
            if not isinstance(profile, dict) or profile.get("allow_pay_over_limit") is not False:
                result["aborted"] = "payment_safety_not_confirmed"
                print("AVITO_RECOVERY_RETRY " + json.dumps(result, ensure_ascii=False), flush=True)
                return
            feeds = profile.get("feeds_data") or []
            if not any(isinstance(f, dict) and f.get("feed_url") == RECOVERY_FEED_URL for f in feeds):
                result["aborted"] = "recovery_feed_not_configured"
                print("AVITO_RECOVERY_RETRY " + json.dumps(result, ensure_ascii=False), flush=True)
                return

            current_items = await avito_get(
                "/autoload/v4/uploads/current/items",
                params={"page": 1, "perPage": 100, "query": RECOVERY_AD_ID},
            )
            rows = _rows(current_items)
            messages = []
            for row in rows:
                if isinstance(row, dict) and row.get("ad_id") == RECOVERY_AD_ID:
                    messages.extend(row.get("messages") or [])
            image_error = any(
                isinstance(m, dict)
                and m.get("type") == "error"
                and "Images" in str(m.get("title", ""))
                for m in messages
            )
            if not image_error:
                result["aborted"] = "previous_image_error_not_confirmed"
                print("AVITO_RECOVERY_RETRY " + json.dumps(result, ensure_ascii=False), flush=True)
                return

            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                image_check = await client.get(
                    "https://bestclimate-avito-bridge-live-production.up.railway.app/media/aqua-towada-aqi-25fis1-r3-w.jpg"
                )
            if image_check.status_code != 200 or not image_check.headers.get("content-type", "").startswith("image/") or len(image_check.content) < 1024:
                result["aborted"] = "image_endpoint_not_ready"
                result["image_http"] = image_check.status_code
                print("AVITO_RECOVERY_RETRY " + json.dumps(result, ensure_ascii=False), flush=True)
                return

            status = await _post_upload(api_base, get_token)
            result["upload_http"] = status
            result["retry"] = status < 400
            print("AVITO_RECOVERY_RETRY " + json.dumps(result, ensure_ascii=False), flush=True)
            if status >= 400:
                return

            await asyncio.sleep(50)
            follow = await avito_get(
                "/autoload/v4/uploads/current/items",
                params={"page": 1, "perPage": 100, "query": RECOVERY_AD_ID},
            )
            print("AVITO_RECOVERY_RETRY_RESULT " + json.dumps(follow, ensure_ascii=False, sort_keys=True), flush=True)
        except Exception as exc:
            result["exception"] = type(exc).__name__
            print("AVITO_RECOVERY_RETRY " + json.dumps(result, ensure_ascii=False), flush=True)

    @app.on_event("startup")
    async def schedule_recovery_retry() -> None:
        if os.getenv("AVITO_RECOVERY_RETRY_TARGET", "").strip() == str(TARGET_AVITO_ID):
            asyncio.create_task(_run())
