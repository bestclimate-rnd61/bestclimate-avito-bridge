"""Safety tests for Avito XML draft staging."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
import avito_draft_store as drafts


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch = patch.object(drafts, "ROOT", self.root)
        self.patch.start()
        self.items = [{"id": "12345", "title": "Aqua & Haier", "price": 59000}]

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_xml_and_metadata(self):
        result = drafts.stage("job-1", "bulk_edit", self.items)
        self.assertFalse(result["published"])
        tree = ET.parse(result["path"])
        self.assertEqual(tree.findtext("./Ad/Title"), "Aqua & Haier")
        meta = json.loads((self.root / "job-1.json").read_text())
        self.assertEqual(meta["status"], "awaiting_schema_validation")

    def test_repeat_same_payload_idempotent(self):
        drafts.stage("job-1", "bulk_edit", self.items)
        result = drafts.stage("job-1", "bulk_edit", self.items)
        self.assertTrue(result["idempotent"])

    def test_repeat_different_payload_rejected(self):
        drafts.stage("job-1", "bulk_edit", self.items)
        with self.assertRaises(ValueError):
            drafts.stage("job-1", "bulk_edit", [{"id": "12345", "title": "Other", "price": 100}])

    def test_invalid_task_id_no_write(self):
        with self.assertRaises(ValueError):
            drafts.stage("../escape", "bulk_edit", self.items)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_protected_id_no_write(self):
        with self.assertRaises(ValueError):
            drafts.stage("job-2", "bulk_publish", [{"id": "8341283876", "title": "Protected", "price": 1}])
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
