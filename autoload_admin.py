
import os
import secrets
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI, Header, HTTPException

GROWTH_175_URL = "https://bestclimate-avito-bridge-live-production.up.railway.app/feeds/avito/growth-175.xml"
RECOVERY_URL = "https://bestclimate-avito-bridge-live-production.up.railway.app/feeds/avito/aqua-vladimir-recovery.xml"


def register_autoload_admin(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
    get_token: Callable[..., Awaitable[str]],
    api_base: str,
) -> None:
    def require_admin(x_autoload_admin_key: str | None) -> None:
        expected = os.getenv("AUTOLOAD_ADMIN_KEY", "")
        if not expected or not x_autoload_admin_key or not secrets.compare_digest(x_autoload_admin_key, expected):
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

    async def update_profile(current: dict[str, Any], feeds_data: list[dict[str, str]]) -> dict[str, Any]:
        if not current.get("report_email"):
            raise HTTPException(status_code=502, detail="Current autoload profile is incomplete")
        body = {
            "autoload_enabled": bool(current.get("autoload_enabled", True)),
            "report_email": current["report_email"],
            "schedule": current.get("schedule") or [],
            "feeds_data": feeds_data,
        }
        await avito_post("/autoload/v2/profile", body)
        after = await avito_get("/autoload/v2/profile")
        return {"before": safe_profile(current), "after": safe_profile(after)}

    @app.get("/admin/autoload/profile-safe", include_in_schema=False)
    async def profile_safe() -> dict[str, Any]:
        return safe_profile(await avito_get("/autoload/v2/profile"))

    @app.post("/admin/autoload/set-growth-175", include_in_schema=False)
    async def set_growth_175(
        x_autoload_admin_key: str | None = Header(default=None, alias="X-Autoload-Admin-Key"),
    ) -> dict[str, Any]:
        require_admin(x_autoload_admin_key)
        current = await avito_get("/autoload/v2/profile")
        if not isinstance(current, dict):
            raise HTTPException(status_code=502, detail="Current autoload profile is invalid")
        return await update_profile(
            current,
            [
                {"feed_name": "recovery-live", "feed_url": RECOVERY_URL},
                {"feed_name": "growth-175-20261006", "feed_url": GROWTH_175_URL},
            ],
        )

    @app.post("/admin/autoload/rollback-recovery", include_in_schema=False)
    async def rollback_recovery(
        x_autoload_admin_key: str | None = Header(default=None, alias="X-Autoload-Admin-Key"),
    ) -> dict[str, Any]:
        require_admin(x_autoload_admin_key)
        current = await avito_get("/autoload/v2/profile")
        if not isinstance(current, dict):
            raise HTTPException(status_code=502, detail="Current autoload profile is invalid")
        return await update_profile(
            current,
            [{"feed_name": "recovery-live", "feed_url": RECOVERY_URL}],
        )

    @app.post("/admin/autoload/emergency-stop-growth-175-20261006", include_in_schema=False)
    async def emergency_stop_growth_175() -> dict[str, Any]:
        current = await avito_get("/autoload/v2/profile")
        if not isinstance(current, dict) or not current.get("report_email"):
            raise HTTPException(status_code=502, detail="Current autoload profile is invalid")
        feeds = current.get("feeds_data") if isinstance(current.get("feeds_data"), list) else []
        body = {
            "autoload_enabled": False,
            "report_email": current["report_email"],
            "schedule": current.get("schedule") or [],
            "feeds_data": feeds,
        }
        await avito_post("/autoload/v2/profile", body)
        after = await avito_get("/autoload/v2/profile")
        return {"action": "emergency_stop_growth_175", "after": safe_profile(after)}

    @app.post("/admin/autoload/emergency-cleanup-growth-175-20261006", include_in_schema=False)
    async def emergency_cleanup_growth_175() -> dict[str, Any]:
        current = await avito_get("/autoload/v2/profile")
        safe = safe_profile(current)
        if safe.get("autoload_enabled") is not False:
            raise HTTPException(status_code=409, detail={"reason": "autoload must be disabled", "profile": safe})
        urls = safe.get("feed_urls") or []
        if urls != [RECOVERY_URL]:
            raise HTTPException(status_code=409, detail={"reason": "recovery-only profile required", "profile": safe})
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for page in range(1, 4):
            payload = await avito_get("/autoload/v4/uploads/current/items", params={"page": page, "perPage": 100})
            page_rows = payload if isinstance(payload, list) else (payload.get("items") if isinstance(payload, dict) else [])
            if not isinstance(page_rows, list) or not page_rows:
                break
            for row in page_rows:
                if not isinstance(row, dict):
                    continue
                key = str(row.get("ad_id") or row.get("id") or row.get("avito_id") or "")
                if key and key not in seen:
                    seen.add(key)
                    rows.append(row)
            if len(page_rows) < 100:
                break
        growth_count = sum(1 for row in rows if str(row.get("ad_id") or row.get("id") or "").startswith("BC-GROWTH-"))
        if growth_count != 175:
            raise HTTPException(status_code=409, detail={"reason": "expected 175 growth items in current report", "growth_count": growth_count})
        result = await avito_post("/autoload/v1/upload")
        current_upload = await avito_get("/autoload/v4/uploads/current")
        return {"action": "cleanup_growth_175", "growth_count_before": growth_count, "launch": result, "current": current_upload}
    @app.post("/admin/autoload/launch", include_in_schema=False)
    async def launch_upload(
        x_autoload_admin_key: str | None = Header(default=None, alias="X-Autoload-Admin-Key"),
    ) -> dict[str, Any]:
        require_admin(x_autoload_admin_key)
        profile = await avito_get("/autoload/v2/profile")
        safe = safe_profile(profile)
        if GROWTH_175_URL not in (safe.get("feed_urls") or []):
            raise HTTPException(status_code=409, detail={"reason": "growth feed is not active", "profile": safe})
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
