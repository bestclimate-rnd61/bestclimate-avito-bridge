import os
import httpx

BASE = os.getenv("AVITO_API_BASE", "https://api.avito.ru").rstrip("/")
CLIENT_ID = os.getenv("AVITO_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET", "")


def get_token() -> str:
    r = httpx.post(
        f"{BASE}/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def probe(path: str, token: str) -> None:
    r = httpx.get(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    print(f"AUTOLOAD_V4 path={path} status={r.status_code}", flush=True)
    if r.status_code < 400:
        try:
            data = r.json()
        except ValueError:
            print("AUTOLOAD_V4 response=non_json", flush=True)
            return
        if isinstance(data, dict):
            print(f"AUTOLOAD_V4 keys={sorted(data.keys())[:30]}", flush=True)
            # Print only non-sensitive high-level status/count fields.
            for key in ("upload_id", "status", "total", "count", "page", "perPage"):
                if key in data:
                    print(f"AUTOLOAD_V4 {key}={data[key]!r}", flush=True)
        elif isinstance(data, list):
            print(f"AUTOLOAD_V4 list_count={len(data)}", flush=True)
    else:
        try:
            body = r.json()
            if isinstance(body, dict):
                print(f"AUTOLOAD_V4 error_keys={sorted(body.keys())[:20]}", flush=True)
        except ValueError:
            pass


def main() -> None:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise SystemExit("Missing Avito credentials")
    token = get_token()
    for path in (
        "/autoload/v4/uploads",
        "/autoload/v4/uploads/current",
        "/autoload/v4/uploads/current/items",
        "/autoload/v4/uploads/last_successful",
        "/autoload/v4/uploads/last_successful/items",
    ):
        probe(path, token)


if __name__ == "__main__":
    main()
