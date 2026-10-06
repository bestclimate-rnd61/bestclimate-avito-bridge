
import os
import secrets
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI, Header, HTTPException

GROWTH_175_URL = "https://bestclimate-avito-bridge-live-production.up.railway.app/feeds/avito/growth-175.xml"


def register_autoload_admin(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
    get_token: Callable[..., Awaitable[str]],
    api_base: str,
) -> None:
    def require_admin(x_autoload_admin_key: str | None) -> None:
        expected = os.getenv("AUTOLOAD_ADMIN_KEY", "")
        if (
            not expected
            or not x_autoload_admin_key
            or not secrets.compare_digest(x_autoload_admin_key, expected)
        ):
            raise HTTPException(status_code=401, detail="Unauthorized")

    async def avito_post(path: str, payload: dict[str, Any] | None = None) -> Any:
        token = await get_token()
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(
                f"{api_base}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 401:
                token = await get_token(force_refresh=True)
                response = await client.post(
                    f"{api_base}{path}",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail={"path": path, "body": response.text[:1200]},
            )
        if not response.content:
            return {"status": response.status_code}
        try:
            return response.json()
        except ValueError:
            return {"status": response.status_code, "text": response.text[:500]}

    def safe_profile(profile: Any) -> dict[str, Any]:
        if not isinstance(profile, dict):
            return {"valid": False}
        feeds = profile.get("feeds_data") if isinstance(profile.get("feeds_data"), list) else []
        return {
            "valid": True,
            "autoload_enabled": profile.get("autoload_enabled"),
            "allow_pay_over_limit": profile.get("allow_pay_over_limit"),
            "uploadMode": profile.get("uploadMode"),
            "feed_urls": [f.get("feed_url") for f in feeds if isinstance(f, dict)],
            "feed_names": [f.get("feed_name") for f in feeds if isinstance(f, dict)],
            "schedule_count": len(profile.get("schedule") or []),
            "report_email_present": bool(profile.get("report_email")),
        }

    @app.get("/admin/autoload/profile-safe", include_in_schema=False)
    async def profile_safe() -> dict[str, Any]:
        return safe_profile(await avito_get("/autoload/v2/profile"))

    @app.post("/admin/autoload/set-growth-175", include_in_schema=False)
    async def set_growth_175(
        x_autoload_admin_key: str | None = Header(default=None, alias="X-Autoload-Admin-Key"),
    ) -> dict[str, Any]:
        require_admin(x_autoload_admin_key)
        current = await avito_get("/autoload/v2/profile")
        if not isinstance(current, dict) or not current.get("report_email"):
            raise HTTPException(status_code=502, detail="Current autoload profile is incomplete")
        body = {
            "autoload_enabled": bool(current.get("autoload_enabled", True)),
            "report_email": current["report_email"],
            "schedule": current.get("schedule") or [],
            "feeds_data": [
                {
                    "feed_name": "growth-175-20261006",
                    "feed_url": GROWTH_175_URL,
                }
            ],
        }
        await avito_post("/autoload/v2/profile", body)
        after = await avito_get("/autoload/v2/profile")
        return {"before": safe_profile(current), "after": safe_profile(after)}

    @app.post("/admin/autoload/launch", include_in_schema=False)
    async def launch_upload(
        x_autoload_admin_key: str | None = Header(default=None, alias="X-Autoload-Admin-Key"),
    ) -> dict[str, Any]:
        require_admin(x_autoload_admin_key)
        profile = await avito_get("/autoload/v2/profile")
        safe = safe_profile(profile)
        if safe.get("feed_urls") != [GROWTH_175_URL]:
            raise HTTPException(
                status_code=409,
                detail={"reason": "growth feed is not active", "profile": safe},
            )
        result = await avito_post("/autoload/v1/upload")
        current = await avito_get("/autoload/v4/uploads/current")
        current_safe: dict[str, Any] = {}
        if isinstance(current, dict):
            current_safe = {
                k: current.get(k)
                for k in ("upload_id", "id", "status", "start_time", "finish_time", "url")
                if k in current
            }
        return {"launch": result, "current": current_safe}
