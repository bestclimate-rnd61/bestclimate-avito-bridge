import asyncio
import json
import os
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI

GROWTH_V3_URL = "https://bestclimate-avito-bridge-live-production.up.railway.app/feeds/avito/growth-v3.xml"

async def _post_avito(api_base: str, get_token: Callable[..., Awaitable[str]], path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    token = await get_token()
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post(
            f"{api_base}{path}",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401:
            token = await get_token(force_refresh=True)
            response = await client.post(
                f"{api_base}{path}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
    payload: Any = None
    if response.content:
        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text[:800]}
    return response.status_code, payload

def register_growth_v3_launch(app: FastAPI, avito_get, get_token, api_base: str) -> None:
    async def _run() -> None:
        await asyncio.sleep(15)
        if os.getenv("AVITO_GROWTH_V3_ACTION", "").strip() != "launch":
            return
        result: dict[str, Any] = {"action": "growth_v3_wave1", "feed": GROWTH_V3_URL}
        try:
            profile = await avito_get("/autoload/v2/profile")
            if not isinstance(profile, dict):
                result["aborted"] = "invalid_profile"
                print("AVITO_GROWTH_V3 " + json.dumps(result, ensure_ascii=False), flush=True)
                return
            if profile.get("allow_pay_over_limit") is not False:
                result["aborted"] = "payment_safety_not_confirmed"
                print("AVITO_GROWTH_V3 " + json.dumps(result, ensure_ascii=False), flush=True)
                return
            email = profile.get("report_email")
            if not isinstance(email, str) or "@" not in email:
                result["aborted"] = "report_email_missing"
                print("AVITO_GROWTH_V3 " + json.dumps(result, ensure_ascii=False), flush=True)
                return
            body = {
                "autoload_enabled": True,
                "report_email": email,
                "schedule": [],
                "feeds_data": [{"feed_name": "growth-v3-wave1", "feed_url": GROWTH_V3_URL}],
            }
            status, payload = await _post_avito(api_base, get_token, "/autoload/v2/profile", body)
            result["profile_http"] = status
            if status >= 400:
                result["profile_error"] = payload
                print("AVITO_GROWTH_V3 " + json.dumps(result, ensure_ascii=False), flush=True)
                return
            await asyncio.sleep(3)
            status, payload = await _post_avito(api_base, get_token, "/autoload/v1/upload")
            result["upload_http"] = status
            result["upload_response"] = payload
            print("AVITO_GROWTH_V3 " + json.dumps(result, ensure_ascii=False), flush=True)
            if status >= 400:
                return
            await asyncio.sleep(50)
            follow: dict[str, Any] = {}
            for label, path in (
                ("current", "/autoload/v4/uploads/current"),
                ("current_items", "/autoload/v4/uploads/current/items"),
            ):
                try:
                    follow[label] = await avito_get(path, params={"page": 1, "perPage": 100} if label == "current_items" else None)
                except Exception as exc:
                    follow[label] = {"error": type(exc).__name__}
            print("AVITO_GROWTH_V3_RESULT " + json.dumps(follow, ensure_ascii=False, sort_keys=True), flush=True)
        except Exception as exc:
            result["exception"] = type(exc).__name__
            print("AVITO_GROWTH_V3 " + json.dumps(result, ensure_ascii=False), flush=True)

    @app.on_event("startup")
    async def schedule_growth_v3() -> None:
        if os.getenv("AVITO_GROWTH_V3_ACTION", "").strip() == "launch":
            asyncio.create_task(_run())
