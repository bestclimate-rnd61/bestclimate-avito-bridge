"""Durable, atomic Avito XML draft staging. Never publishes automatically."""
import json
import hashlib
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(os.getenv("AVITO_DRAFT_DIR", "/data/avito_drafts"))
_VALID_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_PROTECTED_IDS = {"8341283876"}
_PROTECTED_UPLOADS = {"612013427"}


def _identity(item, *keys):
    """Reject ambiguous aliases instead of silently choosing an update target."""
    values = []
    for key in keys:
        if key not in item:
            continue
        raw = item[key]
        if type(raw) not in (str, int):
            raise ValueError("invalid identity")
        value = str(raw).strip()
        if not value:
            raise ValueError("empty identity")
        values.append(value)
    if len(set(values)) > 1:
        raise ValueError("conflicting identity aliases")
    return values[0] if values else None


def _atomic_write(path, content):
    fd, tmp = tempfile.mkstemp(prefix=".staging-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def stage(task_id, action, items):
    if action not in ("bulk_edit", "bulk_publish"):
        raise ValueError("unsupported action")
    if not isinstance(task_id, str) or not _VALID_ID.fullmatch(task_id):
        raise ValueError("invalid task id")
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError("invalid batch size")
    root = ET.Element("Ads", {"formatVersion": "3", "target": "Avito.ru"})
    seen = set()
    seen_avito = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("invalid item")
        item_id = str(item.get("id", ""))
        avito_id = _identity(item, "avito_id", "AvitoId")
        upload_id = _identity(item, "source_upload_id", "upload_id", "UploadId")
        if avito_id is not None and not re.fullmatch(r"[1-9][0-9]*", avito_id):
            raise ValueError("invalid Avito id")
        if (avito_id in _PROTECTED_IDS or upload_id in _PROTECTED_UPLOADS
                or avito_id is not None and avito_id in seen_avito):
            raise ValueError("duplicate or protected Avito identity")
        # Explicitly identified manual ads and the separate account stay outside
        # this integration. Unknown ownership is a publication blocker below.
        if (item.get("manual") or item.get("is_manual")
                or str(item.get("source", "")).strip().casefold() == "manual"
                or str(item.get("account_name", "")).strip().casefold() == "авито 2"):
            raise ValueError("manual or excluded account item")
        title = item.get("title")
        price = item.get("price")
        if not _VALID_ID.fullmatch(item_id) or item_id in seen or item_id in _PROTECTED_IDS:
            raise ValueError("invalid, duplicate, or protected item id")
        if not isinstance(title, str) or not title.strip() or len(title) > 150:
            raise ValueError("invalid title")
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0:
            raise ValueError("invalid price")
        if item.get("paid_promotion") or item.get("delete"):
            raise ValueError("forbidden paid promotion or deletion")
        seen.add(item_id)
        if avito_id is not None:
            seen_avito.add(avito_id)
        ad = ET.SubElement(root, "Ad")
        for tag, value in (("Id", item_id), ("Title", title.strip()), ("Price", price)):
            ET.SubElement(ad, tag).text = str(value)
        if avito_id is not None:
            ET.SubElement(ad, "AvitoId").text = avito_id
    # Bind idempotency to the full preparation request, including provenance
    # that is deliberately absent from the eventual Avito XML.
    try:
        payload_hash = hashlib.sha256(json.dumps(items, ensure_ascii=False,
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid draft payload") from exc
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / (task_id + ".xml")
    metadata_path = ROOT / (task_id + ".json")
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    # Do not silently replace an already staged draft for a repeated task ID.
    if path.exists() or metadata_path.exists():
        if path.exists() and path.read_bytes() == xml_bytes and metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if (metadata.get("action") == action and metadata.get("published") is False
                    and metadata.get("payload_sha256") == payload_hash):
                return {"status": "draft_saved", "path": str(path), "published": False, "count": len(items), "idempotent": True}
        raise ValueError("task id already exists with different draft")
    metadata = {"action": action, "status": "awaiting_schema_validation", "published": False,
                "count": len(items), "payload_sha256": payload_hash,
                "publication_ready": False, "publication_blockers": [
                    "official_category_schema_not_validated",
                    "fresh_price_and_stock_not_verified",
                    "account_and_managed_ownership_not_verified",
                    "owner_publication_approval_required"]}
    _atomic_write(path, xml_bytes)
    _atomic_write(metadata_path, json.dumps(metadata, ensure_ascii=False).encode("utf-8"))
    return {"status": "draft_saved", "path": str(path), "published": False, "count": len(items)}
