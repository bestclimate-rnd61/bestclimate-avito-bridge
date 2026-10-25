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

    def test_protected_identity_aliases_no_write(self):
        for extra in ({"avito_id": "8341283876"}, {"AvitoId": 8341283876},
                      {"AvitoId": " 8341283876 "}, {"source_upload_id": "612013427"},
                      {"upload_id": 612013427}, {"UploadId": "612013427"}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                drafts.stage("protected-alias", "bulk_edit", [dict(self.items[0], **extra)])
            self.assertEqual(list(self.root.iterdir()), [])

    def test_preserves_avito_mapping_and_blocks_duplicate_targets(self):
        mapped = dict(self.items[0], avito_id="12345678")
        result = drafts.stage("mapped", "bulk_edit", [mapped])
        self.assertEqual(ET.parse(result["path"]).findtext("./Ad/AvitoId"), "12345678")
        with self.assertRaises(ValueError):
            drafts.stage("duplicate-target", "bulk_edit", [mapped, dict(mapped, id="other")])
        self.assertFalse((self.root / "duplicate-target.xml").exists())

    def test_conflicting_or_invalid_mapping_rejected(self):
        for extra in ({"avito_id": "123", "AvitoId": "456"}, {"avito_id": True},
                      {"avito_id": ""}, {"avito_id": "0123"}, {"avito_id": "not-numeric"},
                      {"upload_id": "100", "source_upload_id": "612013427"}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                drafts.stage("bad-mapping", "bulk_edit", [dict(self.items[0], **extra)])
            self.assertEqual(list(self.root.iterdir()), [])

    def test_excluded_sources_no_write(self):
        for extra in ({"manual": True}, {"is_manual": True}, {"source": "manual"},
                      {"account_name": " Авито 2 "}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                drafts.stage("excluded", "bulk_edit", [dict(self.items[0], **extra)])
            self.assertEqual(list(self.root.iterdir()), [])

    def test_unknown_provenance_is_never_publication_ready(self):
        drafts.stage("unknown", "bulk_edit", self.items)
        metadata = json.loads((self.root / "unknown.json").read_text())
        self.assertFalse(metadata["publication_ready"])
        self.assertIn("account_and_managed_ownership_not_verified", metadata["publication_blockers"])

    def test_changed_provenance_is_not_idempotent(self):
        drafts.stage("provenance", "bulk_edit", [dict(self.items[0], price_source="snapshot-a")])
        with self.assertRaises(ValueError):
            drafts.stage("provenance", "bulk_edit", [dict(self.items[0], price_source="snapshot-b")])


if __name__ == "__main__":
    unittest.main()
