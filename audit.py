import asyncio
import json
import os
from datetime import date, timedelta
from typing import Any

import httpx

BASE = os.getenv("AVITO_API_BASE", "https://api.avito.ru").rstrip("/")
CLIENT_ID = os.getenv("AVITO_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET", "")


def out(prefix: str, payload: Any) -> None:
    print(prefix + " " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")), flush=True)


async def token(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{BASE}/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    r.raise_for_status()
    data = r.json()
    return data["access_token"]


def safe_item(item: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "id", "itemId", "title", "status", "url", "price", "category", "categoryId",
        "category_id", "address", "location", "updatedAt", "updated_at", "createdAt", "created_at",
    ]
    result = {k: item.get(k) for k in keys if item.get(k) is not None}
    if isinstance(result.get("price"), dict):
        result["price"] = {k: v for k, v in result["price"].items() if k in {"value", "amount", "currency"}}
    return result


async def main() -> None:
    if not CLIENT_ID or not CLIENT_SECRET:
        out("AUDIT_ERROR", {"stage": "config", "message": "Avito credentials are missing"})
        return

    async with httpx.AsyncClient(timeout=30) as client:
        access_token = await token(client)
        headers = {"Authorization": f"Bearer {access_token}"}

        profile_r = await client.get(f"{BASE}/core/v1/accounts/self", headers=headers)
        profile_r.raise_for_status()
        profile = profile_r.json()
        user_id = profile.get("id") or profile.get("user_id") or profile.get("account_id")
        out("AUDIT_PROFILE", {
            "id": user_id,
            "name": profile.get("name") or profile.get("profile_name") or profile.get("company_name"),
            "type": profile.get("type"),
        })

        items: list[dict[str, Any]] = []
        for page in range(1, 11):
            r = await client.get(
                f"{BASE}/core/v1/items",
                headers=headers,
                params={"status": "active", "page": page, "per_page": 100},
            )
            r.raise_for_status()
            data = r.json()
            resources = data.get("resources", []) if isinstance(data, dict) else []
            if not isinstance(resources, list):
                resources = []
            items.extend(x for x in resources if isinstance(x, dict))
            if len(resources) < 100:
                break

        out("AUDIT_ITEMS", {"active_count": len(items)})
        for item in items:
            out("AUDIT_ITEM", safe_item(item))

        item_ids = []
        for item in items:
            raw_id = item.get("id") or item.get("itemId")
            try:
                item_ids.append(int(raw_id))
            except (TypeError, ValueError):
                pass

        if user_id and item_ids:
            date_to = date.today()
            date_from = date_to - timedelta(days=29)
            body = {
                "dateFrom": date_from.isoformat(),
                "dateTo": date_to.isoformat(),
                "itemIds": item_ids[:200],
                "fields": ["uniqViews", "uniqContacts", "uniqFavorites"],
                "periodGrouping": "day",
            }
            stats_r = await client.post(
                f"{BASE}/stats/v1/accounts/{user_id}/items",
                headers={**headers, "Content-Type": "application/json"},
                json=body,
            )
            if stats_r.status_code < 400:
                stats = stats_r.json()
                rows = []
                if isinstance(stats, dict):
                    result = stats.get("result", stats)
                    if isinstance(result, dict):
                        rows = result.get("items", []) or []
                totals: list[dict[str, Any]] = []
                for row in rows if isinstance(rows, list) else []:
                    if not isinstance(row, dict):
                        continue
                    sums = {"uniqViews": 0, "uniqContacts": 0, "uniqFavorites": 0}
                    daily = row.get("stats", [])
                    if isinstance(daily, list):
                        for d in daily:
                            if isinstance(d, dict):
                                for k in sums:
                                    try:
                                        sums[k] += int(d.get(k, 0) or 0)
                                    except (TypeError, ValueError):
                                        pass
                    totals.append({"itemId": row.get("itemId"), **sums})
                out("AUDIT_STATS", {
                    "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
                    "items": totals,
                })
            else:
                out("AUDIT_STATS_ERROR", {"status": stats_r.status_code})


if __name__ == "__main__":
    asyncio.run(main())
