"""Opt-in supervisor on the existing bridge; no new service or publisher."""
from __future__ import annotations

import asyncio
import os
import socket
import threading
import uuid
from datetime import datetime, timezone
from urllib.error import URLError

from business_machine_adapter import ALLOWED_ACTIONS, DraftAdapter
from business_machine_products import fetch_product
from business_machine_worker import BusinessMachineWorker, QueueAPI, service_token_from_environment


class LiveDraftAdapter:
    def __init__(self, root, avito_get, *, product_fetch=fetch_product):
        self.drafts = DraftAdapter(root)
        self.avito_get = avito_get
        self.product_fetch = product_fetch

    async def _capabilities(self):
        checks = {}
        account_id = None
        low_balance = None
        for name, path, params in (
                ("profile_read", "/core/v1/accounts/self", None),
                ("items_read", "/core/v1/items", {"page": 1, "per_page": 1}),
                ("autoload_profile_read", "/autoload/v2/profile", None),
                ("autoload_schema_read", "/autoload/v1/user-docs/tree", None)):
            try:
                value = await self.avito_get(path, params)
                checks[name] = {"verified": isinstance(value, (dict, list)), "http_status": 200}
                if name == "profile_read" and isinstance(value, dict):
                    raw = value.get("id") or value.get("user_id") or value.get("account_id")
                    if isinstance(raw, (int, str)) and str(raw).isdigit():
                        account_id = int(raw)
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                checks[name] = {"verified": False, "http_status": status if isinstance(status, int) else None}
        if account_id:
            try:
                balance = await self.avito_get(f"/core/v1/accounts/{account_id}/balance/")
                if isinstance(balance, dict) and isinstance(balance.get("real"), (int, float, str)):
                    from decimal import Decimal
                    amount = Decimal(str(balance["real"]))
                    if amount.is_finite():
                        low_balance = amount <= 150
            except Exception:
                pass
        # No write request is used to probe permissions. The account's autoload
        # contract and balance remain independent publication gates.
        blockers = ["PUBLICATION_SCOPE_NOT_VERIFIED", "PROVIDER_SCHEMA_NOT_VALIDATED"]
        if low_balance is True:
            blockers.append("LOW_BALANCE")
        return {"checked_at": datetime.now(timezone.utc).isoformat(), "checks": checks,
                "low_balance": low_balance,
                "publication_write_verified": False, "external_writes": 0,
                "publication_blockers": blockers}

    def execute(self, job, ensure_lease):
        payload = job.get("payload", {})
        if job.get("role") != "avito" or job.get("action") not in ALLOWED_ACTIONS:
            raise ValueError("action_not_allowed")
        if not isinstance(payload, dict):
            raise ValueError("invalid_payload")
        if job.get("action") == "plan" and payload.get("source") == "avito-api":
            ensure_lease()
            capabilities = asyncio.run(self._capabilities())
            ensure_lease()
            result, artifacts = self.drafts.execute(job, ensure_lease)
            result["capabilities"] = capabilities
            return result, artifacts
        urls = payload.get("product_urls")
        if urls is None:
            # Synthetic contract tests and explicit local drafts remain possible,
            # but are never upgraded to verified catalog products.
            result, artifacts = self.drafts.execute(job, ensure_lease)
            result["products_verified"] = False
            return result, artifacts
        if (not isinstance(urls, list) or not 1 <= len(urls) <= 10
                or any(not isinstance(url, str) for url in urls)
                or len(set(urls)) != len(urls) or payload.get("items") is not None):
            raise ValueError("invalid_product_urls")
        observed = []
        for url in urls:
            ensure_lease()
            try:
                observed.append(self.product_fetch(url))
            except (URLError, TimeoutError, OSError):
                raise OSError("product_source_unavailable") from None
        ensure_lease()
        normalized = {**job, "payload": {**payload, "synthetic": False,
                                         "items": [value["item"] for value in observed]}}
        # Evidence timestamps are excluded from the idempotent artifact input;
        # the exact observed prices/title remain included. A changed price never
        # silently overwrites a committed attempt.
        result, artifacts = self.drafts.execute(normalized, ensure_lease)
        result.update({"products_verified": True, "product_evidence": [value["evidence"] for value in observed],
                       "publication_status": "blocked", "publication_blocker": "PUBLICATION_SCOPE_NOT_VERIFIED"})
        return result, artifacts


class EmbeddedWorker:
    def __init__(self, avito_get, *, env=None, worker_factory=None, restart_seconds=30):
        self.env = os.environ if env is None else env
        self.avito_get = avito_get
        self.worker_factory = worker_factory
        self.restart_seconds = restart_seconds
        self.stop_event = threading.Event()
        self.thread = None
        self.worker = None
        self.state = "disabled"
        self.error_code = None

    def status(self):
        return {"enabled": self.env.get("BM_EMBEDDED_WORKER_ENABLED") == "1", "state": self.state,
                "thread_alive": bool(self.thread and self.thread.is_alive()),
                "queue_registered": bool(self.state == "running" and self.worker and self.worker.worker_id),
                "worker_id": self.worker.worker_id if self.worker else None,
                "error_code": self.error_code, "publishing_enabled": False}

    def _make_worker(self):
        if self.worker_factory:
            return self.worker_factory(threading.Event())
        api = QueueAPI(self.env.get("BM_API_URL", "https://bestclimate-ai-control-center.onrender.com/bm"),
                       service_token_from_environment(), timeout=10)
        adapter = LiveDraftAdapter(self.env.get("BM_ARTIFACT_DIR", "/data/business-machine/artifacts"), self.avito_get)
        return BusinessMachineWorker(api, adapter, "railway-avito-" + socket.gethostname() + "-" + uuid.uuid4().hex[:12],
                                     stop_event=threading.Event())

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self.worker = self._make_worker()
                self.state, self.error_code = "running", None
                self.worker.run()
            except Exception:
                self.error_code = "WORKER_UNAVAILABLE"
            if not self.stop_event.is_set():
                self.state = "recovering"
                # A worker sets its local stop flag on exit. Its next generation
                # gets a fresh event while the supervisor keeps its own shutdown.
                self.stop_event.wait(self.restart_seconds)
        self.state = "stopped"

    def start(self):
        if self.env.get("BM_EMBEDDED_WORKER_ENABLED") != "1" or self.thread and self.thread.is_alive():
            return
        self.state = "starting"
        self.thread = threading.Thread(target=self._run, name="bm-avito-supervisor", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.worker:
            self.worker.stopping.set()
        if self.thread:
            self.thread.join(timeout=15)


def register_embedded_worker(app, avito_get):
    supervisor = EmbeddedWorker(avito_get)
    app.state.business_machine_worker = supervisor

    @app.on_event("startup")
    async def start_worker():
        supervisor.start()

    @app.on_event("shutdown")
    async def stop_worker():
        await asyncio.to_thread(supervisor.stop)

    @app.get("/business-machine/status")
    async def status():
        return supervisor.status()
