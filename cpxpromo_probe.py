import asyncio
import json

from fastapi import FastAPI, HTTPException


ITEM_IDS = [7556388793, 8305258576, 8324765982, 7716200879, 8324639588, 8461285020, 8479764928]


def _compact(payload):
    if not isinstance(payload, dict):
        return {"type": type(payload).__name__}
    manual = payload.get("manual") if isinstance(payload.get("manual"), dict) else None
    auto = payload.get("auto") if isinstance(payload.get("auto"), dict) else None
    result = {
        "actionTypeID": payload.get("actionTypeID"),
        "selectedType": payload.get("selectedType"),
    }
    if manual:
        for key in ("minBidPenny", "maxBidPenny", "recBidPenny", "bidPenny", "minLimitPenny", "maxLimitPenny", "recLimitPenny"):
            if key in manual:
                result[key] = manual.get(key)
        bids = manual.get("bids")
        if isinstance(bids, list):
            values = []
            for row in bids:
                if isinstance(row, dict) and isinstance(row.get("valuePenny"), int):
                    values.append(row["valuePenny"])
            result["allowedBidPennyFirst10"] = sorted(set(values))[:10]
    if auto:
        for key in ("budgetPenny", "budgetType"):
            if key in auto:
                result[f"auto_{key}"] = auto.get(key)
    return result


def register_cpxpromo_probe(app: FastAPI, avito_get):
    @app.on_event("startup")
    async def cpxpromo_startup_probe():
        await asyncio.sleep(8)
        results = {}
        for item_id in ITEM_IDS:
            try:
                payload = await avito_get(f"/cpxpromo/1/getBids/{item_id}")
                results[str(item_id)] = _compact(payload)
            except HTTPException as exc:
                results[str(item_id)] = {"http": exc.status_code, "detail": str(exc.detail)[:250]}
            except Exception as exc:
                results[str(item_id)] = {"error": type(exc).__name__}
        print("AVITO_CPXPROBE " + json.dumps(results, ensure_ascii=False, sort_keys=True), flush=True)
