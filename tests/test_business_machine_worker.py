"""Pure stdlib BM worker tests; fake queue only, no network or legacy startup."""
import hashlib
import io
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import avito_draft_store as legacy
from business_machine_adapter import DraftAdapter
from business_machine_worker import (
    APIError, BusinessMachineWorker, LeaseGuard, LeaseLost, NoRedirects,
    QueueAPI, ShutdownRequested, service_token_from_environment,
)


def make_job(**overrides):
    job = {"id": "job-1", "role": "avito", "action": "draft", "attempts": 1,
           "payload": {"synthetic": True, "items": [{"id": "BC-LOCAL-1", "title": "Aqua & Haier", "price": 1}]},
           "lease_token": "synthetic-lease-1", "lease_until": time.time() + 90}
    return {**job, **overrides}


class FakeQueue:
    timeout = 0.1

    def __init__(self, job=None):
        self.job = job
        self.calls = []
        self.heartbeat_error = None
        self.heartbeat_seen = threading.Event()

    def post(self, path, payload):
        self.calls.append((path, payload))
        if path == "/v1/worker/register":
            return {"workerId": payload["workerId"],
                    "worker": {"worker_id": "internal-identity:" + payload["workerId"], "roles": ["avito"]}}
        if path == "/v1/jobs/claim":
            job, self.job = self.job, None
            return {"job": job}
        if path.endswith("/heartbeat") and "/jobs/" in path:
            self.heartbeat_seen.set()
            if self.heartbeat_error:
                raise self.heartbeat_error
            return {"ok": True, "owned": True}
        return {"ok": True}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.adapter = DraftAdapter(self.root / "artifacts")

    def tearDown(self):
        self.temporary.cleanup()

    def test_draft_has_atomic_manifest_and_verified_hashes(self):
        result, artifacts = self.adapter.execute(make_job(), lambda: None)
        self.assertFalse(result["published"])
        self.assertEqual(result["external_writes"], 0)
        self.assertFalse(result["schema_validated"])
        self.assertTrue(result["synthetic"])
        self.assertTrue(result["inline_artifacts_complete"])
        self.assertEqual(len(artifacts), 3)
        for artifact in artifacts:
            content = Path(artifact["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), artifact["sha256"])
            self.assertEqual(len(content), artifact["size_bytes"])
            self.assertEqual(content, artifact["content"].encode())
            self.assertNotIn("synthetic-lease-1", artifact["path"])
        result2, artifacts2 = self.adapter.execute(make_job(), lambda: None)
        self.assertEqual((result, artifacts), (result2, artifacts2))

    def test_inline_content_is_not_persisted_recursively_in_manifest(self):
        _, artifacts = self.adapter.execute(make_job(), lambda: None)
        manifest = json.loads(artifacts[2]["content"])
        self.assertTrue(all("content" not in item for item in manifest["artifacts"]))
        self.assertLess(len(json.dumps({"artifacts": artifacts}, ensure_ascii=False).encode()), 64 * 1024)

    def test_over_inline_budget_preserves_private_files_for_manual_qa(self):
        with patch("business_machine_adapter.MAX_INLINE_RESULT_BYTES", 1):
            result, artifacts = self.adapter.execute(make_job(), lambda: None)
        self.assertTrue(result["manual_qa_required"])
        self.assertFalse(result["inline_artifacts_complete"])
        self.assertTrue(all("content" not in item for item in artifacts))
        self.assertTrue(all(Path(item["path"]).exists() for item in artifacts))

    def test_partial_legacy_write_replays_cleanly_without_committed_pair(self):
        original = legacy._atomic_write
        calls = 0

        def interrupted(path, content):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated crash")
            original(path, content)

        with patch.object(legacy, "_atomic_write", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.adapter.execute(make_job(), lambda: None)
        self.assertEqual(list(self.root.rglob("draft.xml")), [])
        result, artifacts = self.adapter.execute(make_job(), lambda: None)
        self.assertEqual(result["status"], "draft_saved")
        self.assertEqual(len(artifacts), 3)

    def test_orphan_staging_directory_removed_on_replay(self):
        job = make_job()
        job_key = hashlib.sha256(job["id"].encode()).hexdigest()
        attempt = hashlib.sha256(job["lease_token"].encode()).hexdigest()
        orphan = self.adapter.root / "jobs" / job_key / "attempts" / (".staging-" + attempt + "-orphan")
        orphan.mkdir(parents=True)
        (orphan / "draft.xml").write_text("incomplete")
        self.adapter.execute(job, lambda: None)
        self.assertFalse(orphan.exists())

    def test_same_attempt_concurrent_replay_is_idempotent(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.adapter.execute, make_job(), lambda: None) for _ in range(2)]
        self.assertEqual(futures[0].result(), futures[1].result())
        self.assertEqual(len(list(self.root.rglob("manifest.json"))), 1)

    def test_separate_lease_attempts_cannot_replace_each_others_artifacts(self):
        second = make_job(lease_token="synthetic-lease-2", payload={"items": [
            {"id": "BC-LOCAL-1", "title": "Changed draft", "price": 2}]})
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(self.adapter.execute, make_job(), lambda: None)
            b = pool.submit(self.adapter.execute, second, lambda: None)
        path_a, path_b = a.result()[1][0]["path"], b.result()[1][0]["path"]
        self.assertNotEqual(path_a, path_b)
        self.assertIn(b"Aqua &amp; Haier", Path(path_a).read_bytes())
        self.assertIn(b"Changed draft", Path(path_b).read_bytes())

    def test_conflicting_payload_same_attempt_rejected(self):
        self.adapter.execute(make_job(), lambda: None)
        with self.assertRaisesRegex(ValueError, "artifact_conflict"):
            self.adapter.execute(make_job(payload={"items": [{"id": "BC-LOCAL-1", "title": "Other", "price": 2}]}), lambda: None)

    def test_tampered_committed_artifact_rejected(self):
        _, artifacts = self.adapter.execute(make_job(), lambda: None)
        Path(artifacts[0]["path"]).write_text("changed")
        with self.assertRaisesRegex(ValueError, "artifact_integrity_error"):
            self.adapter.execute(make_job(), lambda: None)

    def test_lease_loss_before_commit_has_no_committed_artifacts(self):
        checks = 0

        def lease():
            nonlocal checks
            checks += 1
            if checks == 3:
                raise LeaseLost("test")

        with self.assertRaises(LeaseLost):
            self.adapter.execute(make_job(), lease)
        self.assertEqual(list(self.root.rglob("manifest.json")), [])

    def test_validate_and_plan_have_no_durable_artifacts(self):
        validated, artifacts = self.adapter.execute(make_job(action="validate"), lambda: None)
        self.assertEqual(validated["status"], "validated")
        self.assertEqual(artifacts, [])
        planned, artifacts = self.adapter.execute(make_job(action="plan", payload={}), lambda: None)
        self.assertEqual(planned["status"], "planned")
        self.assertEqual(artifacts, [])
        self.assertFalse(self.adapter.root.exists())

    def test_publication_and_paid_promotion_rejected(self):
        with self.assertRaisesRegex(ValueError, "action_not_allowed"):
            self.adapter.execute(make_job(action="publish"), lambda: None)
        job = make_job()
        job["payload"]["items"][0]["paid_promotion"] = True
        with self.assertRaises(ValueError):
            self.adapter.execute(job, lambda: None)
        self.assertEqual(list(self.root.rglob("draft.xml")), [])


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.adapter = DraftAdapter(Path(self.temporary.name) / "artifacts")

    def tearDown(self):
        self.temporary.cleanup()

    def worker(self, queue, adapter=None, **kwargs):
        worker = BusinessMachineWorker(queue, adapter or self.adapter, "raw-worker", **kwargs)
        worker.register()
        return worker

    def test_register_uses_returned_raw_identity_and_completes_fenced_draft(self):
        queue = FakeQueue(make_job())
        worker = self.worker(queue)
        self.assertEqual(worker.worker_id, "raw-worker")
        self.assertTrue(worker.process_one())
        complete = [(path, body) for path, body in queue.calls if path.endswith("/complete")]
        self.assertEqual(len(complete), 1)
        body = complete[0][1]
        self.assertEqual(body["workerId"], "raw-worker")
        self.assertEqual(body["leaseToken"], "synthetic-lease-1")
        self.assertFalse(body["result"]["published"])
        self.assertEqual(len(body["artifacts"]), 3)

    def test_unregistered_or_wrong_registration_role_never_claims(self):
        queue = FakeQueue(make_job())
        worker = BusinessMachineWorker(queue, self.adapter, "raw-worker")
        with self.assertRaises(RuntimeError):
            worker.process_one()
        with patch.object(queue, "post", return_value={"workerId": "raw-worker", "worker": {"roles": ["sales"]}}):
            with self.assertRaises(APIError):
                worker.register()
        self.assertEqual(queue.calls, [])

    def test_claim_none_is_idle(self):
        worker = self.worker(FakeQueue())
        self.assertFalse(worker.process_one())

    def test_heartbeat_lease_loss_discards_result_without_complete_or_fail(self):
        queue = FakeQueue(make_job())
        queue.heartbeat_error = APIError(409, False)

        class SlowAdapter:
            def execute(self, job, ensure):
                self.assert_seen = queue.heartbeat_seen.wait(1)
                time.sleep(0.01)
                ensure()
                return {"status": "wrong"}, []

        adapter = SlowAdapter()
        worker = self.worker(queue, adapter, lease_seconds=3, heartbeat_seconds=0.02)
        worker.process_one()
        self.assertTrue(adapter.assert_seen)
        self.assertFalse(any(path.endswith(("/complete", "/fail")) for path, _ in queue.calls))

    def test_invalid_input_is_nonretryable(self):
        queue = FakeQueue(make_job(action="publish"))
        self.worker(queue).process_one()
        failures = [body for path, body in queue.calls if path.endswith("/fail")]
        self.assertEqual(failures[0]["errorCode"], "ACTION_NOT_ALLOWED")
        self.assertFalse(failures[0]["retryable"])

    def test_io_error_is_retryable(self):
        class BrokenAdapter:
            def execute(self, *_):
                raise OSError("not included in event")

        queue = FakeQueue(make_job())
        self.worker(queue, BrokenAdapter()).process_one()
        failures = [body for path, body in queue.calls if path.endswith("/fail")]
        self.assertEqual(failures[0]["errorCode"], "ARTIFACT_IO_ERROR")
        self.assertTrue(failures[0]["retryable"])

    def test_shutdown_aborts_result_and_releases_with_retryable_failure(self):
        stopping = threading.Event()

        class StoppingAdapter:
            def execute(self, job, ensure):
                stopping.set()
                ensure()

        queue = FakeQueue(make_job())
        self.worker(queue, StoppingAdapter(), stop_event=stopping).process_one()
        self.assertFalse(any(path.endswith("/complete") for path, _ in queue.calls))
        failures = [body for path, body in queue.calls if path.endswith("/fail")]
        self.assertEqual(failures[0]["errorCode"], "WORKER_STOPPING")

    def test_expired_lease_never_completes(self):
        queue = FakeQueue(make_job(lease_until=time.time() - 1))
        self.worker(queue).process_one()
        self.assertFalse(any(path.endswith(("/complete", "/fail")) for path, _ in queue.calls))

    def test_transient_register_outage_has_exponential_backoff(self):
        class ImmediateStop(threading.Event):
            def __init__(self):
                super().__init__()
                self.delays = []

            def wait(self, timeout=None):
                self.delays.append(timeout)
                return self.is_set()

        queue = FakeQueue()
        stop = ImmediateStop()
        worker = BusinessMachineWorker(queue, self.adapter, "raw-worker", stop_event=stop)
        with patch.object(queue, "post", side_effect=[APIError(503, True), APIError(503, True), APIError(403, False)]):
            with self.assertRaises(APIError):
                worker.run()
        self.assertGreaterEqual(stop.delays[0], 1)
        self.assertGreaterEqual(stop.delays[1], 2)
        self.assertTrue(stop.is_set())

    def test_retryable_heartbeat_outage_does_not_extend_local_expiry(self):
        queue = FakeQueue()
        queue.heartbeat_error = APIError(503, True)
        guard = LeaseGuard(queue, "raw-worker", make_job(lease_until=time.time() + 0.04),
                           3, 0.01, threading.Event())
        guard.start()
        try:
            time.sleep(0.06)
            with self.assertRaises(LeaseLost):
                guard.ensure()
        finally:
            guard.close()


class QueueClientTests(unittest.TestCase):
    def test_api_token_required_and_http_remote_host_rejected(self):
        with self.assertRaises(ValueError):
            QueueAPI("http://api:8080", "")
        with self.assertRaises(ValueError):
            QueueAPI("http://outside.example", "synthetic-service-token")

    def test_service_token_env_precedes_private_file(self):
        with patch.dict(os.environ, {"BM_SERVICE_TOKEN": "synthetic-env-token", "BM_SERVICE_TOKEN_FILE": "/does/not/exist"}):
            self.assertEqual(service_token_from_environment(), "synthetic-env-token")

    def test_service_token_private_file_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "service.token"
            path.write_text("synthetic-file-token\n")
            with patch.dict(os.environ, {"BM_SERVICE_TOKEN": "", "BM_SERVICE_TOKEN_FILE": str(path)}):
                self.assertEqual(service_token_from_environment(), "synthetic-file-token")

    def test_http_error_body_and_token_never_in_exception(self):
        api = QueueAPI("http://api:8080", "synthetic-service-token")
        error = urllib.error.HTTPError("http://api:8080/claim", 409, "private upstream detail", {}, io.BytesIO(b"private"))
        with patch.object(api.opener, "open", side_effect=error):
            with self.assertRaises(APIError) as raised:
                api.post("/v1/jobs/claim", {})
        self.assertEqual(raised.exception.status, 409)
        self.assertFalse(raised.exception.retryable)
        self.assertNotIn("private", str(raised.exception))
        self.assertNotIn("synthetic-service-token", str(raised.exception))

    def test_redirect_handler_does_not_forward_authorization(self):
        self.assertIsNone(NoRedirects().redirect_request(None, None, 302, "redirect", {}, "https://outside.example"))


if __name__ == "__main__":
    unittest.main()
