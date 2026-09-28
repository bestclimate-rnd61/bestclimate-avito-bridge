import os
import time
import secrets
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query

app = FastAPI(title="Best Climate Avito Bridge", version="0.2.1")

AVITO_API_BASE = os.getenv("AVITO_API_BASE", "https://api.avito.ru").rstrip("/")
AVITO_CLIENT_ID = os.getenv("AVITO_CLIENT_ID", "")
AVITO_CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET", "")
BRIDGE_SECRET = os.getenv("BRIDGE_SECRET", "")

_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def _require_config() -> None:
    missing = [
        name
        for name, value in {
            "AVITO_CLIENT_ID": AVITO_CLIENT_ID,
            "AVITO_CLIENT_SECRET": AVITO_CLIENT_SECRET,
            "BRIDGE_SECRET": BRIDGE_SECRET,
        }.items()
        if not value
    ]
    if missing:
        raise HTTPException(status_code=503, detail={"missing_env": missing})


def _safe_token_diag(response: httpx.Response) -> dict[str, Any]:
    diag: dict[str, Any] = {
        "status": response.status_code,
        "content_type": response.headers.get("content-type", "")[:120],
    }
    try:
        payload = response.json()
    except ValueError:
        diag["json_keys"] = []
        return diag

    if isinstance(payload, dict):
        diag["json_keys"] = sorted(str(k) for k in payload.keys())[:30]
        for key in ("error", "error_description", "message", "code", "type"):
            value = payload.get(key)
            if isinstance(value, (str, int, float, bool)):
                diag[key] = str(value)[:300]
    else:
        diag["json_keys"] = []
    return diag


def authorize_bridge(
    x_bridge_secret: str | None = Header(default=None, alias="X-Bridge-Secret"),
    authorization: str | None = Header(default=None),
) -> None:
    _require_config()
    candidate = x_bridge_secret
    if not candidate and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization[7:].strip()
    if not candidate or not secrets.compare_digest(candidate, BRIDGE_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _get_token(force_refresh: bool = False) -> str:
    _require_config()
    now = time.time()
    if (
        not force_refresh
        and _token_cache.get("access_token")
        and _token_cache.get("expires_at", 0) > now + 60
    ):
        return str(_token_cache["access_token"])

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{AVITO_API_BASE}/token",
            data={
                "grant_type": "client_credentials",
                "client_id": AVITO_CLIENT_ID,
                "client_secret": AVITO_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    diag = _safe_token_diag(response)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail={"stage": "token", **diag})

    try:
        payload = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail={"stage": "token", **diag})

    access_token = payload.get("access_token") if isinstance(payload, dict) else None
    if not access_token:
        raise HTTPException(status_code=502, detail={"stage": "token", **diag})

    expires_in = int(payload.get("expires_in", 3600))
    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = now + expires_in
    return str(access_token)


async def _avito_get(path: str, params: dict[str, Any] | None = None) -> Any:
    token = await _get_token()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{AVITO_API_BASE}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401:
            token = await _get_token(force_refresh=True)
            response = await client.get(
                f"{AVITO_API_BASE}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail={"path": path, "body": response.text[:1000]},
        )
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return {"text": response.text}


async def _account_id() -> int:
    profile = await _avito_get("/core/v1/accounts/self")
    if not isinstance(profile, dict):
        raise HTTPException(status_code=502, detail="Unexpected Avito profile response")
    raw = profile.get("id") or profile.get("user_id") or profile.get("account_id")
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=502, detail="Avito account id is missing")


@app.on_event("startup")
async def startup_avito_probe() -> None:
    """Verify Avito credentials on each deploy without logging secrets or tokens."""
    try:
        profile = await _avito_get("/core/v1/accounts/self")
        account_id = None
        name = None
        if isinstance(profile, dict):
            account_id = profile.get("id") or profile.get("user_id") or profile.get("account_id")
            name = profile.get("name") or profile.get("profile_name") or profile.get("company_name")
        print(f"AVITO_AUTH_OK account_id={account_id!r} name={name!r}", flush=True)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        safe = {
            "http_status": exc.status_code,
            "stage": detail.get("stage"),
            "upstream_status": detail.get("status"),
            "content_type": detail.get("content_type"),
            "json_keys": detail.get("json_keys"),
            "error": detail.get("error"),
            "error_description": detail.get("error_description"),
            "message": detail.get("message"),
            "code": detail.get("code"),
            "path": detail.get("path"),
        }
        print(f"AVITO_AUTH_FAIL {safe!r}", flush=True)
    except Exception as exc:
        print(f"AVITO_AUTH_FAIL error_type={type(exc).__name__}", flush=True)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "bestclimate-avito-bridge",
        "version": "0.2.1",
        "avito_base": AVITO_API_BASE,
        "configured": bool(AVITO_CLIENT_ID and AVITO_CLIENT_SECRET and BRIDGE_SECRET),
        "mode": "read-only",
    }


@app.get("/avito/self", dependencies=[Depends(authorize_bridge)])
async def avito_self() -> Any:
    return await _avito_get("/core/v1/accounts/self")


@app.get("/avito/balance", dependencies=[Depends(authorize_bridge)])
async def avito_balance() -> Any:
    user_id = await _account_id()
    return await _avito_get(f"/core/v1/accounts/{user_id}/balance/")


@app.get("/avito/items", dependencies=[Depends(authorize_bridge)])
async def avito_items(
    status: str = Query(default="active"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
) -> Any:
    return await _avito_get(
        "/core/v1/items",
        params={"status": status, "page": page, "per_page": per_page},
    )


@app.get("/avito/item/{item_id}", dependencies=[Depends(authorize_bridge)])
async def avito_item(item_id: int = Path(ge=1)) -> Any:
    user_id = await _account_id()
    return await _avito_get(f"/core/v1/accounts/{user_id}/items/{item_id}/")


@app.get("/avito/autoload/profile", dependencies=[Depends(authorize_bridge)])
async def avito_autoload_profile() -> Any:
    return await _avito_get("/autoload/v2/profile")


@app.get("/avito/autoload/tree", dependencies=[Depends(authorize_bridge)])
async def avito_autoload_tree() -> Any:
    return await _avito_get("/autoload/v1/user-docs/tree")


@app.get("/avito/autoload/category/{slug}/fields", dependencies=[Depends(authorize_bridge)])
async def avito_autoload_category_fields(
    slug: str = Path(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")
) -> Any:
    return await _avito_get(f"/autoload/v1/user-docs/node/{slug}/fields")


@app.get("/avito/autoload/ad-ids", dependencies=[Depends(authorize_bridge)])
async def avito_autoload_ad_ids(
    query: str = Query(min_length=1, max_length=2000)
) -> Any:
    return await _avito_get("/autoload/v2/items/ad_ids", params={"query": query})


@app.get("/avito/ping", dependencies=[Depends(authorize_bridge)])
async def avito_ping() -> dict[str, Any]:
    profile = await _avito_get("/core/v1/accounts/self")
    return {"ok": True, "profile": profile}
