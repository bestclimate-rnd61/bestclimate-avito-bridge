"""Credential-free Avito validation and atomic, attempt-scoped draft artifacts.

This adapter never imports the legacy HTTP app and never publishes a feed.
The final attempt directory is the commit marker: incomplete staging directories
are discarded on replay, while committed manifests must match input and hashes.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

import avito_draft_store as legacy_drafts

ALLOWED_ACTIONS = frozenset({"draft", "validate", "plan"})
_LEGACY_LOCK = threading.Lock()
MAX_INLINE_ARTIFACT_BYTES = 64 * 1024
MAX_INLINE_RESULT_BYTES = 60 * 1024


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _attempt_lock(path: Path):
    with path.open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _legacy_stage(root: Path, items: list) -> dict:
    # Legacy ROOT is process-global; serialise only local rendering. No legacy
    # queue/main/startup is imported. Every call renders into a fresh temp path.
    with _LEGACY_LOCK:
        previous_root = legacy_drafts.ROOT
        try:
            legacy_drafts.ROOT = root
            return legacy_drafts.stage("draft", "bulk_edit", items)
        finally:
            legacy_drafts.ROOT = previous_root


class DraftAdapter:
    def __init__(self, root: str | Path):
        self.root = Path(root).absolute()

    def execute(self, job: dict, ensure_lease: Callable[[], None]) -> tuple[dict, list]:
        ensure_lease()
        action, payload = job.get("action"), job.get("payload")
        if job.get("role") != "avito" or action not in ALLOWED_ACTIONS:
            raise ValueError("action_not_allowed")
        if not isinstance(payload, dict):
            raise ValueError("invalid_payload")
        if action == "plan":
            result = {"status": "planned", "action": "plan", "role": "avito",
                      "steps": ["validate_items", "create_private_draft", "request_review"],
                      "published": False, "external_writes": 0, "publishable": False,
                      "review_required": True, "qa_required": True,
                      "synthetic": payload.get("synthetic") is True}
            ensure_lease()
            return result, []

        items = payload.get("items")
        # Legacy validation checks IDs, title, integer price, protected item,
        # batch bounds and rejects paid promotion/deletion before local writes.
        if not isinstance(items, list):
            raise ValueError("invalid_payload")
        if action == "validate":
            with tempfile.TemporaryDirectory(prefix="bm-validate-") as temporary:
                _legacy_stage(Path(temporary), items)
            ensure_lease()
            return {"status": "validated", "role": "avito", "action": action,
                    "count": len(items), "published": False, "external_writes": 0,
                    "schema_validated": False, "publishable": False,
                    "review_required": True, "qa_required": True,
                    "synthetic": payload.get("synthetic") is True,
                    "validation_scope": "local-safe-items+xml only"}, []

        job_id, lease_token = job.get("id"), job.get("lease_token")
        if not isinstance(job_id, str) or not job_id or not isinstance(lease_token, str) or not lease_token:
            raise ValueError("missing_job_identity")
        input_hash = _digest(_canonical({"role": "avito", "action": action, "payload": payload}))
        job_key, attempt_key = _digest(job_id.encode()), _digest(lease_token.encode())
        parent = self.root / "jobs" / job_key / "attempts"
        parent.mkdir(parents=True, exist_ok=True)
        target = parent / attempt_key
        with _attempt_lock(parent / (attempt_key + ".lock")):
            ensure_lease()
            if target.exists():
                result = self._read_committed(target, job_id, attempt_key, input_hash)
                ensure_lease()
                return result
            # These directories have no commit marker and belong only to this
            # attempt. The lock excludes an active same-attempt writer.
            for orphan in parent.glob(".staging-" + attempt_key + "-*"):
                if orphan.is_dir() and not orphan.is_symlink():
                    shutil.rmtree(orphan)
            temporary = Path(tempfile.mkdtemp(prefix=".staging-" + attempt_key + "-", dir=parent))
            try:
                _legacy_stage(temporary, items)
                descriptors = [self._descriptor(temporary / name, target / name, kind, attempt_key)
                               for name, kind in (("draft.xml", "avito_xml_draft"),
                                                  ("draft.json", "avito_draft_metadata"))]
                manifest = {"version": 1, "jobId": job_id, "attemptKey": attempt_key,
                            "inputSha256": input_hash, "count": len(items),
                            "published": False, "external_writes": 0,
                            "schemaValidated": False, "synthetic": payload.get("synthetic") is True,
                            "title": items[0]["title"].strip(), "artifacts": descriptors}
                legacy_drafts._atomic_write(temporary / "manifest.json", _canonical(manifest))
                _fsync_directory(temporary)
                ensure_lease()
                # Atomic directory rename commits XML, metadata and manifest
                # together. Lease generations use different target directories.
                os.rename(temporary, target)
                _fsync_directory(parent)
                ensure_lease()
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
            return self._read_committed(target, job_id, attempt_key, input_hash)

    @staticmethod
    def _descriptor(source: Path, final: Path, kind: str, attempt_key: str) -> dict:
        content = source.read_bytes()
        return {"name": final.name, "media_type": "application/xml" if final.suffix == ".xml" else "application/json",
                "path": str(final), "sha256": _digest(content),
                "size_bytes": len(content), "attempt_key": attempt_key}

    def _read_committed(self, target: Path, job_id: str, attempt_key: str, input_hash: str) -> tuple[dict, list]:
        try:
            if target.is_symlink():
                raise ValueError("artifact_integrity_error")
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            if (manifest.get("version") != 1 or manifest.get("jobId") != job_id
                    or manifest.get("attemptKey") != attempt_key
                    or manifest.get("inputSha256") != input_hash
                    or manifest.get("published") is not False):
                raise ValueError("artifact_conflict")
            artifacts = manifest["artifacts"]
            if not isinstance(artifacts, list) or len(artifacts) != 2:
                raise ValueError("artifact_integrity_error")
            for descriptor, name in zip(artifacts, ("draft.xml", "draft.json")):
                path = target / name
                if path.is_symlink() or descriptor.get("path") != str(path):
                    raise ValueError("artifact_integrity_error")
                content = path.read_bytes()
                if descriptor.get("sha256") != _digest(content) or descriptor.get("size_bytes") != len(content):
                    raise ValueError("artifact_integrity_error")
            artifacts = [dict(item) for item in artifacts] + [self._descriptor(
                target / "manifest.json", target / "manifest.json", "avito_draft_manifest", attempt_key)]
            result = {"status": "draft_saved", "role": "avito", "action": "draft",
                      "count": manifest["count"], "published": False, "external_writes": 0,
                      "publishable": False, "schema_validated": False,
                      "review_required": True, "qa_required": True,
                      "synthetic": manifest.get("synthetic") is True,
                      "validation_scope": "local-safe-items+xml only", "attemptKey": attempt_key,
                      "draft": {"title": manifest.get("title", "Private Avito draft"),
                                "description": "Private XML draft; provider schema validation and review are required.",
                                "publishable": False, "review_required": True}}
            # Inline a bounded copy for independent Node QA without shared-FS
            # access. Persisted manifests remain metadata-only and never recurse.
            inline = [dict(item) for item in artifacts]
            if all(item["size_bytes"] <= MAX_INLINE_ARTIFACT_BYTES for item in inline):
                for item in inline:
                    item["content"] = Path(item["path"]).read_text(encoding="utf-8")
                if len(_canonical({"result": result, "artifacts": inline})) <= MAX_INLINE_RESULT_BYTES:
                    result["inline_artifacts_complete"] = True
                    return result, inline
            result.update({"inline_artifacts_complete": False, "manual_qa_required": True,
                           "inline_omission_reason": "ARTIFACT_INLINE_LIMIT"})
            return result, artifacts
        except (KeyError, TypeError, json.JSONDecodeError, FileNotFoundError) as exc:
            raise ValueError("artifact_integrity_error") from exc
