import asyncio
import json
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, HTTPException


def _label(node: dict[str, Any]) -> str:
    for key in ("name", "title", "label", "value"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _slug(node: dict[str, Any]) -> str | None:
    for key in ("slug", "node_slug", "id", "code"):
        value = node.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value).strip()
    return None


def _walk(obj: Any, path: list[str], out: list[dict[str, Any]]) -> None:
    if isinstance(obj, dict):
        label = _label(obj)
        next_path = path + ([label] if label else [])
        low_path = " > ".join(next_path).lower()
        if "обогревател" in low_path or "климатическ" in low_path:
            slug = _slug(obj)
            if label or slug:
                out.append({"path": " > ".join(next_path), "label": label, "slug": slug})
        for value in obj.values():
            if isinstance(value, (dict, list)):
                _walk(value, next_path, out)
    elif isinstance(obj, list):
        for value in obj:
            _walk(value, path, out)


def _field_hits(obj: Any, wanted: str, out: list[dict[str, Any]]) -> None:
    if isinstance(obj, dict):
        identifiers = [obj.get(k) for k in ("tag", "name", "field", "code", "id")]
        if any(str(v).lower() == wanted.lower() for v in identifiers if v is not None):
            # Category docs contain no secrets; still keep only useful structure.
            safe = {}
            for key in (
                "tag", "name", "field", "code", "id", "title", "description",
                "required", "type", "values", "variants", "options", "dependencies",
                "value", "valuesCatalog", "catalog", "warning",
            ):
                if key in obj:
                    safe[key] = obj[key]
            out.append(safe)
        for value in obj.values():
            if isinstance(value, (dict, list)):
                _field_hits(value, wanted, out)
    elif isinstance(obj, list):
        for value in obj:
            _field_hits(value, wanted, out)


def register_autoload_category_probe(
    app: FastAPI,
    avito_get: Callable[..., Awaitable[Any]],
) -> None:
    async def collect() -> dict[str, Any]:
        result: dict[str, Any] = {"candidates": [], "heater_fields": []}
        try:
            tree = await avito_get("/autoload/v1/user-docs/tree")
        except HTTPException as exc:
            return {"tree_http": exc.status_code, "tree_detail": str(exc.detail)[:500]}

        candidates: list[dict[str, Any]] = []
        _walk(tree, [], candidates)
        # Deduplicate and prioritize the household/climate path.
        unique: dict[tuple[str, str | None], dict[str, Any]] = {}
        for item in candidates:
            unique[(item["path"], item["slug"])] = item
        candidates = list(unique.values())
        candidates.sort(
            key=lambda x: (
                0 if "бытовая техника" in x["path"].lower() else 1,
                0 if "климатическ" in x["path"].lower() else 1,
                0 if "обогревател" in x["path"].lower() else 1,
                len(x["path"]),
            )
        )
        result["candidates"] = candidates[:40]

        tried: set[str] = set()
        for item in candidates:
            slug = item.get("slug")
            path_low = item.get("path", "").lower()
            if not slug or slug in tried or "обогревател" not in path_low:
                continue
            # Prefer the exact household -> climate equipment -> heaters branch.
            if "бытовая техника" not in path_low and "климатическ" not in path_low:
                continue
            tried.add(slug)
            try:
                fields = await avito_get(f"/autoload/v1/user-docs/node/{slug}/fields")
            except HTTPException as exc:
                result["heater_fields"].append({"slug": slug, "path": item["path"], "http": exc.status_code})
                continue
            goods_subtype: list[dict[str, Any]] = []
            _field_hits(fields, "GoodsSubType", goods_subtype)
            # Collect names of required fields too, to avoid one-error-at-a-time retries.
            required_names: list[str] = []
            def scan_required(value: Any) -> None:
                if isinstance(value, dict):
                    if value.get("required") is True:
                        for k in ("tag", "name", "field", "code"):
                            v = value.get(k)
                            if isinstance(v, str) and v not in required_names:
                                required_names.append(v)
                                break
                    for child in value.values():
                        if isinstance(child, (dict, list)):
                            scan_required(child)
                elif isinstance(value, list):
                    for child in value:
                        scan_required(child)
            scan_required(fields)
            result["heater_fields"].append({
                "slug": slug,
                "path": item["path"],
                "goods_subtype": goods_subtype,
                "required_fields": required_names[:80],
            })
            if goods_subtype:
                break
        return result

    @app.get("/diagnostic/autoload-heater-fields", include_in_schema=False)
    async def autoload_heater_fields() -> dict[str, Any]:
        return await collect()

    @app.on_event("startup")
    async def schedule_probe() -> None:
        async def run() -> None:
            await asyncio.sleep(18)
            try:
                data = await collect()
                print("AVITO_HEATER_FIELDS " + json.dumps(data, ensure_ascii=False, sort_keys=True)[:15000], flush=True)
            except Exception as exc:
                print("AVITO_HEATER_FIELDS " + json.dumps({"error": type(exc).__name__}), flush=True)
        asyncio.create_task(run())
