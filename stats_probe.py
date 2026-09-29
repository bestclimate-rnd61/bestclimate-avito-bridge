import asyncio
import json
from datetime import date, timedelta
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI


def _rows(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("resources", "items", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        result = payload.get("result")
        if isinstance(result, dict):
            items = result.get("items")
            if isinstance(items, list):
                return items
    return []


async def _post_avito(
    api_base: str,
    get_token: Callable[..., Awaitable[str]],
    path: str,
    body: dict[str, Any],
) -> tuple[int, Any]:
    token = await get_token()
    async with httpx.AsyncClient(timeout=30) as client:
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
            payload = {"text": response.text[:1000]}
    return response.status_code, payload


def _aggregate_stats(payload: Any, titles: dict[int, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rows = []
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, dict) and isinstance(result.get("items"), list):
            rows = result["items"]
        elif isinstance(payload.get("items"), list):
            rows = payload["items"]
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_id = row.get("itemId") or row.get("item_id") or row.get("id")
        try:
            item_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        totals = {"uniqViews": 0, "uniqContacts": 0, "uniqFavorites": 0}
        stats = row.get("stats")
        if isinstance(stats, list):
            for stat in stats:
                if not isinstance(stat, dict):
                    continue
                for key in totals:
                    value = stat.get(key)
                    if isinstance(value, (int, float)):
                        totals[key] += int(value)
        views = totals["uniqViews"]
        contacts = totals["uniqContacts"]
        favorites = totals["uniqFavorites"]
        out.append(
            {
                "id": item_id,
                "title": titles.get(item_id, "")[:100],
                "views": views,
                "contacts": contacts,
                "favorites": favorites,
                "contact_rate_pct": round((contacts / views * 100), 2) if views else 0.0,
                "favorite_rate_pct": round((favorites / views * 100), 2) if views else 0.0,
            }
        )
    out.sort(key=lambda row: (row["contacts"], row["views"]), reverse=True)
    return out


def register_stats_probe(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
    account_id_getter: Callable[[], Awaitable[int]],
    get_token: Callable[..., Awaitable[str]],
    api_base: str,
) -> None:
    async def _run() -> None:
        await asyncio.sleep(8)
        try:
            active = await avito_get(
                "/core/v1/items",
                params={"status": "active", "page": 1, "per_page": 100},
            )
            item_ids: list[int] = []
            titles: dict[int, str] = {}
            for row in _rows(active):
                if not isinstance(row, dict):
                    continue
                raw_id = row.get("id") or row.get("item_id") or row.get("avito_id")
                try:
                    item_id = int(raw_id)
                except (TypeError, ValueError):
                    continue
                item_ids.append(item_id)
                titles[item_id] = str(row.get("title") or row.get("name") or "")
            if not item_ids:
                print("AVITO_STATS_SNAPSHOT {\"error\":\"no_active_items\"}", flush=True)
                return

            user_id = await account_id_getter()
            today = date.today()
            periods = {
                "7d": today - timedelta(days=6),
                "30d": today - timedelta(days=29),
            }
            snapshot: dict[str, Any] = {"active_items": len(item_ids), "periods": {}}
            for label, start in periods.items():
                body = {
                    "dateFrom": start.isoformat(),
                    "dateTo": today.isoformat(),
                    "itemIds": item_ids,
                    "periodGrouping": "day",
                    "fields": ["uniqViews", "uniqContacts", "uniqFavorites"],
                }
                status, payload = await _post_avito(
                    api_base,
                    get_token,
                    f"/stats/v1/accounts/{user_id}/items",
                    body,
                )
                period_result: dict[str, Any] = {"http": status}
                if status < 400:
                    rows = _aggregate_stats(payload, titles)
                    period_result["items"] = rows
                    period_result["top_by_contacts"] = rows[:10]
                    period_result["zero_contact_high_views"] = [
                        row for row in rows if row["views"] >= 10 and row["contacts"] == 0
                    ][:10]
                    period_result["heat_pumps"] = [
                        row
                        for row in rows
                        if "теплов" in row["title"].lower()
                        or "aqua" in row["title"].lower()
                        or "midea" in row["title"].lower()
                        or "ballu" in row["title"].lower()
                    ]
                else:
                    period_result["error"] = payload
                snapshot["periods"][label] = period_result
            print(
                "AVITO_STATS_SNAPSHOT " + json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                flush=True,
            )
        except Exception as exc:
            print(
                "AVITO_STATS_SNAPSHOT "
                + json.dumps({"error_type": type(exc).__name__}, ensure_ascii=False),
                flush=True,
            )

    @app.on_event("startup")
    async def schedule_stats_probe() -> None:
        asyncio.create_task(_run())
