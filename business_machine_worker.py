"""Standalone Business Machine worker. Only internal queue HTTP and local drafts.

Run with `python -m business_machine_worker`; never starts main:app or calls
Avito, Telegram, Buffer, a model provider, or publication endpoints.
"""
from __future__ import annotations

import json
import logging
import os
import random
import signal
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from business_machine_adapter import DraftAdapter

LOG = logging.getLogger("business_machine_worker")
SAFE_DRAFT_ERROR_CODES = frozenset({
    "action_not_allowed", "invalid_payload", "missing_job_identity", "artifact_conflict", "artifact_integrity_error",
    "invalid_product_urls", "invalid_product_url", "product_response_too_large", "product_structured_data_invalid",
    "product_encoding_invalid", "product_identity_ambiguous", "product_title_invalid", "product_offer_ambiguous",
    "product_currency_invalid", "product_price_invalid", "product_stock_not_confirmed", "product_sources_conflict",
    "product_http_error",
})


class APIError(Exception):
    def __init__(self, status: int | None, retryable: bool):
        super().__init__("queue_api_unavailable" if retryable else "queue_api_rejected")
        self.status = status
        self.retryable = retryable


class LeaseLost(Exception):
    pass


class ShutdownRequested(Exception):
    pass


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # Never forward the internal service credential to a redirect target.
        return None


def service_token_from_environment() -> str:
    value = os.getenv("BM_SERVICE_TOKEN", "")
    if value:
        return value
    path = os.getenv("BM_SERVICE_TOKEN_FILE", "")
    if not path:
        return ""
    with open(path, encoding="utf-8") as handle:
        value = handle.read(16 * 1024 + 1).strip()
    if not value or len(value) > 16 * 1024:
        raise ValueError("invalid_service_token_file")
    return value


def _job(response):
    if response is None:
        return None
    if isinstance(response, dict):
        value = response.get("job", response)
        if value is None or (isinstance(value, dict) and "id" in value):
            return value
    raise APIError(None, False)


def _remaining(lease_until, fallback: float) -> float:
    if isinstance(lease_until, (int, float)):
        remaining = float(lease_until) - time.time()
    elif isinstance(lease_until, str):
        try:
            remaining = datetime.fromisoformat(lease_until.replace("Z", "+00:00")).timestamp() - time.time()
        except ValueError as exc:
            raise LeaseLost("invalid_lease") from exc
    else:
        remaining = fallback
    return max(0, min(fallback, remaining))


class QueueAPI:
    def __init__(self, base_url: str, service_token: str, timeout: float = 10):
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("invalid_api_url")
        if parsed.scheme == "http" and parsed.hostname not in {"api", "localhost", "127.0.0.1", "::1"}:
            raise ValueError("http_requires_internal_api")
        if not service_token:
            raise ValueError("BM_SERVICE_TOKEN_required")
        self.base_url = base_url.rstrip("/")
        self._token = service_token
        self.timeout = timeout
        if timeout <= 0 or timeout > 30:
            raise ValueError("invalid_api_timeout")
        handlers = [urllib.request.HTTPSHandler(context=ssl.create_default_context()), NoRedirects()]
        if parsed.hostname in {"api", "localhost", "127.0.0.1", "::1"}:
            handlers.append(urllib.request.ProxyHandler({}))
        self.opener = urllib.request.build_opener(*handlers)

    def post(self, path: str, payload: dict):
        request = urllib.request.Request(self.base_url + path, data=json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(),
                                         headers={"Authorization": "Bearer " + self._token,
                                                  "Content-Type": "application/json"}, method="POST")
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                content = response.read(2 * 1024 * 1024 + 1)
                if len(content) > 2 * 1024 * 1024:
                    raise APIError(None, False)
                return json.loads(content) if content else None
        except urllib.error.HTTPError as exc:
            # Do not log response bodies, headers or tokens.
            status = exc.code
            exc.close()
            raise APIError(status, status == 429 or status >= 500) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise APIError(None, True) from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise APIError(None, False) from None


class LeaseGuard:
    def __init__(self, api, worker_id: str, job: dict, lease_seconds: int,
                 heartbeat_seconds: float, stopping: threading.Event):
        self.api, self.worker_id, self.job = api, worker_id, job
        self.lease_seconds, self.interval = lease_seconds, heartbeat_seconds
        self.stopping = stopping
        self.lost, self.closed = threading.Event(), threading.Event()
        self._lock = threading.Lock()
        self._deadline = time.monotonic() + _remaining(job.get("lease_until"), lease_seconds)
        self.thread = threading.Thread(target=self._heartbeat_loop, name="bm-job-heartbeat", daemon=True)

    def start(self):
        self.ensure()
        self.thread.start()

    def owns(self) -> bool:
        with self._lock:
            expired = time.monotonic() >= self._deadline
        if expired:
            self.lost.set()
        return not self.lost.is_set()

    def ensure(self):
        if not self.owns():
            raise LeaseLost("lease_lost")
        if self.stopping.is_set():
            raise ShutdownRequested("worker_stopping")

    def payload(self):
        return {"workerId": self.worker_id, "leaseToken": self.job["lease_token"]}

    def _heartbeat_loop(self):
        while not self.closed.wait(self.interval):
            if not self.owns():
                return
            try:
                response = self.api.post("/v1/jobs/" + urllib.parse.quote(self.job["id"], safe="") + "/heartbeat",
                                         {**self.payload(), "leaseSeconds": self.lease_seconds})
                if not self.owns() or not isinstance(response, dict) or response.get("owned") is not True:
                    self.lost.set()
                    return
                value = response.get("job", response) if isinstance(response, dict) else {}
                if isinstance(value, dict) and value.get("lease_token", self.job["lease_token"]) != self.job["lease_token"]:
                    self.lost.set()
                    return
                with self._lock:
                    self._deadline = time.monotonic() + _remaining(value.get("lease_until") if isinstance(value, dict) else None,
                                                                  self.lease_seconds)
            except APIError as exc:
                if not exc.retryable:
                    self.lost.set()
                    return
                LOG.warning("job_heartbeat_unavailable")
            except (LeaseLost, ValueError, TypeError):
                self.lost.set()
                return

    def close(self):
        self.closed.set()
        if self.thread.is_alive():
            self.thread.join(timeout=self.api.timeout + 1 if hasattr(self.api, "timeout") else 2)


class BusinessMachineWorker:
    def __init__(self, api, adapter, worker_id: str, *, lease_seconds=90,
                 heartbeat_seconds=20, poll_seconds=2, stop_event=None):
        if lease_seconds < 3 or not 0 < heartbeat_seconds < lease_seconds / 2:
            raise ValueError("invalid_lease_timing")
        self.api, self.adapter, self.requested_id = api, adapter, worker_id
        self.worker_id = None
        self.lease_seconds, self.heartbeat_seconds = lease_seconds, heartbeat_seconds
        self.poll_seconds = poll_seconds
        self.stopping = stop_event or threading.Event()
        self._registry_thread = None

    def register(self):
        response = self.api.post("/v1/worker/register", {"workerId": self.requested_id, "roles": ["avito"]})
        value = response.get("worker", response) if isinstance(response, dict) else None
        if not isinstance(value, dict) or value.get("roles") != ["avito"]:
            raise APIError(None, False)
        # The DB row has an internally namespaced worker_id. Requests must keep
        # the raw ID returned by the API, never adopt that DB identity.
        worker_id = response.get("workerId") or value.get("workerId")
        if not isinstance(worker_id, str) or not worker_id:
            raise APIError(None, False)
        self.worker_id = worker_id

    def _registry_heartbeat_loop(self):
        while not self.stopping.wait(self.heartbeat_seconds):
            try:
                self.api.post("/v1/worker/heartbeat", {"workerId": self.worker_id})
            except APIError as exc:
                LOG.warning("worker_heartbeat_unavailable")
                if not exc.retryable:
                    self.stopping.set()

    def _terminal(self, guard: LeaseGuard, suffix: str, payload: dict):
        delay = 0.25
        while guard.owns():
            if suffix == "complete":
                guard.ensure()
            try:
                self.api.post("/v1/jobs/" + urllib.parse.quote(guard.job["id"], safe="") + "/" + suffix,
                              {**guard.payload(), **payload})
                return True
            except APIError as exc:
                if not exc.retryable:
                    guard.lost.set()
                    return False
                # Retry an ambiguous delivery using the same fenced identity.
                if self.stopping.wait(delay):
                    return False
                delay = min(5, delay * 2)
        return False

    def process_one(self) -> bool:
        if not self.worker_id:
            raise RuntimeError("worker_not_registered")
        if self.stopping.is_set():
            raise ShutdownRequested("worker_stopping")
        job = _job(self.api.post("/v1/jobs/claim", {"workerId": self.worker_id, "leaseSeconds": self.lease_seconds}))
        if job is None:
            return False
        if not isinstance(job.get("lease_token"), str) or not job["lease_token"]:
            raise APIError(None, False)
        guard = LeaseGuard(self.api, self.worker_id, job, self.lease_seconds, self.heartbeat_seconds, self.stopping)
        try:
            guard.start()
            result, artifacts = self.adapter.execute(job, guard.ensure)
            guard.ensure()
            self._terminal(guard, "complete", {"result": result, "artifacts": artifacts})
        except LeaseLost:
            LOG.warning("lease_lost_result_discarded")
        except ShutdownRequested:
            self._terminal(guard, "fail", {"errorCode": "WORKER_STOPPING", "retryable": True,
                                           "retryAfterSeconds": 1})
        except ValueError as exc:
            code = str(exc) if str(exc) in SAFE_DRAFT_ERROR_CODES else "invalid_draft_input"
            self._terminal(guard, "fail", {"errorCode": code.upper(), "retryable": False})
        except OSError:
            self._terminal(guard, "fail", {"errorCode": "ARTIFACT_IO_ERROR", "retryable": True,
                                           "retryAfterSeconds": 10})
        except Exception:
            LOG.error("job_execution_failed")
            self._terminal(guard, "fail", {"errorCode": "WORKER_INTERNAL_ERROR", "retryable": True,
                                           "retryAfterSeconds": 10})
        finally:
            guard.close()
        return True

    def run(self):
        outage_delay = 1.0
        try:
            while not self.stopping.is_set():
                try:
                    if not self.worker_id:
                        self.register()
                        self._registry_thread = threading.Thread(target=self._registry_heartbeat_loop,
                                                                 name="bm-worker-heartbeat", daemon=True)
                        self._registry_thread.start()
                    processed = self.process_one()
                    outage_delay = 1.0
                    if not processed:
                        self.stopping.wait(self.poll_seconds)
                except ShutdownRequested:
                    break
                except APIError as exc:
                    LOG.warning("queue_api_unavailable" if exc.retryable else "queue_api_rejected")
                    if not exc.retryable:
                        raise
                    self.stopping.wait(outage_delay + random.uniform(0, outage_delay / 4))
                    outage_delay = min(30, outage_delay * 2)
        finally:
            self.stopping.set()
            if self._registry_thread:
                self._registry_thread.join(timeout=self.api.timeout + 1 if hasattr(self.api, "timeout") else 2)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    try:
        api = QueueAPI(os.getenv("BM_API_URL", "http://api:8080"), service_token_from_environment(),
                       timeout=float(os.getenv("BM_API_TIMEOUT_SECONDS", "10")))
        worker = BusinessMachineWorker(api, DraftAdapter(os.getenv("BM_ARTIFACT_DIR", "/data/business-machine/artifacts")),
                                       os.getenv("BM_WORKER_ID", "avito-" + socket.gethostname()),
                                       lease_seconds=int(os.getenv("BM_LEASE_SECONDS", "90")),
                                       heartbeat_seconds=float(os.getenv("BM_HEARTBEAT_SECONDS", "20")),
                                       poll_seconds=float(os.getenv("BM_POLL_SECONDS", "2")), stop_event=stop)
        worker.run()
    except (ValueError, APIError, OSError):
        LOG.error("worker_configuration_or_authorization_failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
