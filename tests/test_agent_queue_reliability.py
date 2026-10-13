"""Regression tests for durable queue; no external Avito writes."""
import os
import tempfile
import time
import unittest
from unittest.mock import patch

import cloud_task_worker as worker


class QueueReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp.name, "queue.sqlite3")
        self.path_patch = patch.object(worker, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.db = worker.connect()

    def tearDown(self):
        self.db.close()
        self.path_patch.stop()
        self.temp.cleanup()

    def test_persistent_storage_and_idempotency(self):
        worker.enqueue(self.db, "watchdog", {"action": "plan"}, "task-1")
        worker.enqueue(self.db, "watchdog", {"action": "plan"}, "task-1")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 1)
        self.db.close()
        self.db = worker.connect()
        self.assertEqual(worker.claim(self.db)[0], "task-1")
        self.assertTrue(worker.finish(self.db, "task-1", {"ok": True}))
        self.assertEqual(self.db.execute("SELECT state FROM tasks").fetchone()[0], "done")

    def test_retry_and_dead_letter(self):
        worker.enqueue(self.db, "quality", {"action": "plan"}, "retry")
        for attempt in range(worker.MAX_ATTEMPTS):
            self.db.execute("UPDATE tasks SET available_at=0 WHERE id='retry'")
            self.db.commit()
            task = worker.claim(self.db)
            self.assertIsNotNone(task)
            worker.finish(self.db, "retry", {"error": "test"}, error=True)
        self.assertEqual(self.db.execute("SELECT state FROM tasks WHERE id='retry'").fetchone()[0], "failed")

    def test_expired_lease_recovered(self):
        worker.enqueue(self.db, "catalog", {"action": "plan"}, "expired")
        self.assertEqual(worker.claim(self.db, lease_seconds=1)[0], "expired")
        self.db.execute("UPDATE tasks SET lease_until=? WHERE id='expired'", (time.time()-1,))
        self.db.commit()
        self.assertEqual(worker.claim(self.db)[0], "expired")

    def test_no_external_write_on_bulk_edit(self):
        items = [{"id": "123456", "title": "Кондиционер", "price": 59000}]
        with patch("avito_draft_store.stage", return_value={"state": "staged"}) as stage:
            result = worker.execute("listing", {"action": "bulk_edit", "items": items})
        self.assertEqual(result["external_writes"], 0)
        stage.assert_called_once()

    def test_protected_item_rejected(self):
        with self.assertRaises(ValueError):
            worker.execute("listing", {"action": "bulk_publish", "items": [
                {"id": "8341283876", "title": "Protected", "price": 1}
            ]})


if __name__ == "__main__":
    unittest.main()
