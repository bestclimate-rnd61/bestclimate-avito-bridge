import asyncio
import json
import os
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI, HTTPException

TARGET_AVITO_ID = 8341283876
RECOVERY_AD_ID = "BC-8341283876-RECOVERY"
RECOVERY_FEED_URL = (
    "https://bestclimate-avito-bridge-live-production.up.railway.app"
    "/feeds/avito/aqua-vladimir-recovery.xml"
)


def _rows(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("resources", "items", "result", "uploads"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


async def _post_avito(
    api_base: str,
    get_token: Callable[..., Awaitable[str]],
    path: str,
    json_body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    token = await get_token()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{api_base}{path}",
            json=json_body,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401:
            token = await get_token(force_refresh=True)
            response = await client.post(
                f"{api_base}{path}",
                json=json_body,
                headers={"Authorization": f"Bearer {token}"},
            )
    payload: Any = None
    if response.content:
        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text[:1000]}
    return response.status_code, payload


def _compact_upload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    out: dict[str, Any] = {}
    for key in (
        "id",
        "status",
        "source",
        "created_at",
        "started_at",
        "finished_at",
        "sections_stats",
    ):
        if key in payload:
            out[key] = payload.get(key)
    return out or {"keys": sorted(str(k) for k in payload.keys())[:30]}


def register_recovery(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
    get_token: Callable[..., Awaitable[str]],
    api_base: str,
) -> None:
    async def _run_once() -> None:
        await asyncio.sleep(15)
        requested = os.getenv("AVITO_RECOVERY_TARGET", "").strip()
        if requested != str(TARGET_AVITO_ID):
            return

        result: dict[str, Any] = {
            "target": TARGET_AVITO_ID,
            "feed": RECOVERY_FEED_URL,
            "profile_updated": False,
            "upload_requested": False,
        }

        try:
            blocked = await avito_get(
                "/core/v1/items",
                params={"status": "blocked", "page": 1, "per_page": 100},
            )
            target_row = None
            for row in _rows(blocked):
                if not isinstance(row, dict):
                    continue
                raw_id = row.get("id") or row.get("item_id") or row.get("avito_id")
                try:
                    if int(raw_id) == TARGET_AVITO_ID:
                        target_row = row
                        break
                except (TypeError, ValueError):
                    continue
            if target_row is None:
                result["aborted"] = "target_not_blocked"
                print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return
            result["target_title"] = target_row.get("title")
            result["target_price"] = target_row.get("price")
            if target_row.get("price") != 65400:
                result["aborted"] = "unexpected_price"
                print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return

            mapping = await avito_get(
                "/autoload/v2/items/ad_ids",
                params={"query": str(TARGET_AVITO_ID)},
            )
            mapped_ad_id = None
            for row in _rows(mapping):
                if isinstance(row, dict) and row.get("avito_id") == TARGET_AVITO_ID:
                    mapped_ad_id = row.get("ad_id")
                    break
            result["existing_feed_id"] = mapped_ad_id
            if mapped_ad_id not in (None, "", RECOVERY_AD_ID):
                result["aborted"] = "already_managed_by_different_feed_id"
                print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return

            profile = await avito_get("/autoload/v2/profile")
            if not isinstance(profile, dict):
                result["aborted"] = "unexpected_profile"
                print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return

            if profile.get("allow_pay_over_limit") is not False:
                result["aborted"] = "over_limit_protection_not_confirmed"
                print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return

            existing_feeds = profile.get("feeds_data")
            if isinstance(existing_feeds, list) and existing_feeds:
                only_recovery = all(
                    isinstance(feed, dict) and feed.get("feed_url") == RECOVERY_FEED_URL
                    for feed in existing_feeds
                )
                if not only_recovery:
                    result["aborted"] = "existing_feed_configuration_present"
                    result["existing_feed_count"] = len(existing_feeds)
                    print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                    return

            uploads = await avito_get(
                "/autoload/v4/uploads",
                params={"page": 1, "perPage": 10},
            )
            upload_rows = _rows(uploads)
            if upload_rows:
                result["aborted"] = "upload_history_not_empty"
                result["upload_history_count"] = len(upload_rows)
                print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return

            report_email = profile.get("report_email")
            if not isinstance(report_email, str) or "@" not in report_email:
                report_email = "bestclimate-rnd@mail.ru"
            schedule = profile.get("schedule") if isinstance(profile.get("schedule"), list) else []

            profile_body = {
                "autoload_enabled": True,
                "feeds_data": [
                    {
                        "feed_name": "AQUA Vladimir existing-ad recovery",
                        "feed_url": RECOVERY_FEED_URL,
                    }
                ],
                "report_email": report_email,
                "schedule": schedule,
            }

            status, payload = await _post_avito(
                api_base,
                get_token,
                "/autoload/v2/profile",
                profile_body,
            )
            result["profile_http"] = status
            if status >= 400:
                result["profile_error"] = payload
                print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return
            result["profile_updated"] = True

            # Give Avito profile settings a moment to become consistent before the
            # manual upload request. ListingFee=Package and the account-level
            # allow_pay_over_limit=false prevent wallet fallback beyond package.
            await asyncio.sleep(3)
            status, payload = await _post_avito(
                api_base,
                get_token,
                "/autoload/v1/upload",
                None,
            )
            result["upload_http"] = status
            result["upload_response"] = payload
            if status >= 400:
                print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
                return
            result["upload_requested"] = True
            print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)

            await asyncio.sleep(45)
            followup: dict[str, Any] = {"target": TARGET_AVITO_ID}
            try:
                current = await avito_get("/autoload/v4/uploads/current")
                followup["current"] = _compact_upload(current)
            except HTTPException as exc:
                followup["current_http"] = exc.status_code
            try:
                last = await avito_get("/autoload/v4/uploads/last_successful")
                followup["last_successful"] = _compact_upload(last)
            except HTTPException as exc:
                followup["last_successful_http"] = exc.status_code
            try:
                current_items = await avito_get(
                    "/autoload/v4/uploads/current/items",
                    params={"page": 1, "perPage": 100, "query": RECOVERY_AD_ID},
                )
                followup["current_items"] = current_items
            except HTTPException as exc:
                followup["current_items_http"] = exc.status_code
            print("AVITO_RECOVERY_RESULT " + json.dumps(followup, ensure_ascii=False, sort_keys=True), flush=True)
        except HTTPException as exc:
            result["exception_http"] = exc.status_code
            result["exception_detail"] = exc.detail
            print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        except Exception as exc:
            result["exception_type"] = type(exc).__name__
            print("AVITO_RECOVERY " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)

    @app.on_event("startup")
    async def schedule_recovery() -> None:
        if os.getenv("AVITO_RECOVERY_TARGET", "").strip() == str(TARGET_AVITO_ID):
            asyncio.create_task(_run_once())
