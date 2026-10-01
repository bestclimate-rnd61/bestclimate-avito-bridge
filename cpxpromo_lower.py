import asyncio
import json
import os

import httpx
from fastapi import FastAPI, HTTPException


def register_cpxpromo_lower(app: FastAPI, avito_get, get_token, api_base: str):
    @app.on_event("startup")
    async def lower_cpxpromo_bids_once():
        raw = os.getenv("CPXPROMO_LOWER_TARGETS", "").strip()
        if not raw:
            return
        await asyncio.sleep(12)
        target_ids = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                target_ids.append(int(part))
        results = {}
        for item_id in target_ids:
            if item_id == 8341283876:
                results[str(item_id)] = {"skipped": "vladimir_protected"}
                continue
            try:
                bids = await avito_get(f"/cpxpromo/1/getBids/{item_id}")
                if not isinstance(bids, dict):
                    results[str(item_id)] = {"error": "unexpected_getBids"}
                    continue
                action_type = bids.get("actionTypeID")
                manual = bids.get("manual") if isinstance(bids.get("manual"), dict) else {}
                allowed = []
                for row in manual.get("bids", []) if isinstance(manual.get("bids"), list) else []:
                    if isinstance(row, dict) and isinstance(row.get("valuePenny"), int):
                        allowed.append(row["valuePenny"])
                allowed = sorted(set(allowed))
                min_bid = manual.get("minBidPenny")
                whole_ruble_allowed = [value for value in allowed if value % 100 == 0]
                new_bid = whole_ruble_allowed[0] if whole_ruble_allowed else None
                if action_type != 5 or not isinstance(new_bid, int):
                    results[str(item_id)] = {"skipped": "unsupported_action_or_bid", "actionTypeID": action_type, "minBidPenny": min_bid, "allowed": allowed[:12]}
                    continue
                token = await get_token()
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        f"{api_base}/cpxpromo/1/setManual",
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        json={"itemID": item_id, "bidPenny": new_bid, "actionTypeID": action_type},
                    )
                safe_body = response.text[:400] if response.status_code >= 400 else ""
                results[str(item_id)] = {
                    "http": response.status_code,
                    "actionTypeID": action_type,
                    "minBidPenny": min_bid,
                    "newBidPenny": new_bid,
                    "errorBody": safe_body,
                }
                await asyncio.sleep(0.15)
            except HTTPException as exc:
                results[str(item_id)] = {"http": exc.status_code, "detail": str(exc.detail)[:250]}
            except Exception as exc:
                results[str(item_id)] = {"error": type(exc).__name__}
        print("AVITO_CPXLOWER " + json.dumps(results, ensure_ascii=False, sort_keys=True), flush=True)
