import unittest
from browser_worker import validate_request

class BrowserWorkerValidationTests(unittest.TestCase):
    def test_allowlisted_read(self):
        self.assertEqual(validate_request({"action":"inspect_title","url":"https://www.avito.ru/profile"})["action"],"inspect_title")

    def test_block_local_address(self):
        with self.assertRaises(ValueError):
            validate_request({"action":"inspect_title","url":"http://127.0.0.1/admin"})

    def test_block_unapproved_host(self):
        with self.assertRaises(ValueError):
            validate_request({"action":"inspect_title","url":"https://example.com/"})

    def test_block_url_credentials(self):
        with self.assertRaises(ValueError):
            validate_request({"action":"inspect_title","url":"https://user:pass@avito.ru/"})

    def test_block_writes(self):
        with self.assertRaises(PermissionError):
            validate_request({"action":"publish","url":"https://www.avito.ru/profile"})

    def test_block_arbitrary_action(self):
        with self.assertRaises(ValueError):
            validate_request({"action":"execute_js","url":"https://www.avito.ru/profile"})

if __name__ == "__main__":
    unittest.main()
