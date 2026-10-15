"""P1 product provenance, capability evidence and same-service worker recovery."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from business_machine_live import EmbeddedWorker, LiveDraftAdapter
from business_machine_products import observed_product, product_url

URL = "https://bestclimate-rnd.ru/isolated-fixture-product/"


def document(**offer_changes):
    offer = {"@type": "Offer", "price": "143900", "priceCurrency": "RUB",
             "availability": "https://schema.org/InStock", **offer_changes}
    value = {"@context": "https://schema.org", "@type": "Product", "url": URL,
             "name": "Fixture product", "offers": offer}
    return ('<script type="application/ld+json">' + json.dumps(value) + '</script>').encode()


class ProductTests(unittest.TestCase):
    def test_observed_price_stock_and_source_hash_are_retained(self):
        product = observed_product(URL, document())
        self.assertEqual(product["item"]["price"], 143900)
        self.assertEqual(product["evidence"]["availability"], "InStock")
        self.assertIsNone(product["evidence"]["stock_quantity"])
        self.assertEqual(len(product["evidence"]["source_sha256"]), 64)
        self.assertTrue(product["evidence"]["publication_recheck_required"])
        self.assertEqual(product["item"]["id"], observed_product(URL, document(price=1))["item"]["id"])

    def test_missing_or_multiple_products_never_infer_data(self):
        for content in (b"<html>No data</html>", document() + document()):
            with self.assertRaisesRegex(ValueError, "product_identity_ambiguous"):
                observed_product(URL, content)

    def test_webasyst_main_microdata_excludes_related_product_prices(self):
        body = b'''<div itemscope itemtype="http://schema.org/Product" id="js-product-page">
        <h1><span itemprop="name">Actual storefront product</span></h1>
        <div itemscope itemtype="http://schema.org/AggregateOffer" itemprop="offers">
        <meta itemprop="lowPrice" content="1"><div itemscope itemtype="http://schema.org/Offer" itemprop="offers">
        <meta itemprop="price" content="21490"><meta itemprop="priceCurrency" content="RUB">
        <link itemprop="availability" href="http://schema.org/InStock" /></div></div></div>
        <div itemscope itemtype="http://schema.org/Product"><meta itemprop="name" content="Related">
        <div itemscope itemtype="http://schema.org/Offer"><meta itemprop="price" content="99"></div></div>'''
        value = observed_product(URL, body)
        self.assertEqual(value["item"]["price"], 21490)
        self.assertEqual(value["item"]["title"], "Actual storefront product")
        self.assertEqual(value["evidence"]["source"], "public_webasyst_product_microdata")

    def test_related_jsonld_never_overrides_explicit_main_product(self):
        main = b'''<div id="js-product-page" itemscope itemtype="https://schema.org/Product">
        <meta itemprop="name" content="Actual main product"><div itemscope itemtype="https://schema.org/Offer">
        <meta itemprop="price" content="143900"><meta itemprop="priceCurrency" content="RUB">
        <link itemprop="availability" href="https://schema.org/InStock"></div></div>'''
        related = document(price=1).replace(URL.encode(), b"https://bestclimate-rnd.ru/different-product/")
        value = observed_product(URL, main + related)
        self.assertEqual(value["item"]["title"], "Actual main product")
        self.assertEqual(value["item"]["price"], 143900)
        with self.assertRaisesRegex(ValueError, "product_sources_conflict"):
            observed_product(URL, main + document(price=1))

    def test_unbound_or_different_product_jsonld_cannot_verify_requested_page(self):
        for body in (document().replace(URL.encode(), b"https://bestclimate-rnd.ru/related/"),
                     document().replace(('"url": "' + URL + '", ').encode(), b"")):
            with self.assertRaisesRegex(ValueError, "product_identity_ambiguous"):
                observed_product(URL, body)

    def test_unavailable_stock_and_ambiguous_offer_are_rejected(self):
        for availability in (None, "OutOfStock", "https://schema.org/PreOrder", "https://schema.org/OutOfStock"):
            with self.assertRaisesRegex(ValueError, "product_stock_not_confirmed"):
                observed_product(URL, document(availability=availability))
        with self.assertRaisesRegex(ValueError, "product_offer_ambiguous"):
            observed_product(URL, document(**{"@type": "AggregateOffer"}))

    def test_invalid_currency_nonfinite_negative_and_fractional_price_rejected(self):
        for price in ("NaN", "Infinity", "-1", "0", "12.25", None, True, "not a price"):
            with self.assertRaisesRegex(ValueError, "product_price_invalid"):
                observed_product(URL, document(price=price))
        with self.assertRaisesRegex(ValueError, "product_currency_invalid"):
            observed_product(URL, document(priceCurrency="USD"))

    def test_credentials_foreign_host_plaintext_query_and_homepage_rejected(self):
        for url in ("http://bestclimate-rnd.ru/product/", "https://evil.invalid/", "https://bestclimate-rnd.ru/",
                    "https://user:password@bestclimate-rnd.ru/p/", "https://bestclimate-rnd.ru/p/?token=x",
                    "https://bestclimate-rnd.ru:444/p/", "https://bestclimate-rnd.ru/p/#secret"):
            with self.assertRaises(ValueError):
                product_url(url)


class LiveAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temporary.cleanup()

    def test_actual_product_price_replaces_no_user_data_and_xml_stays_private(self):
        async def provider(*_):
            return {}
        adapter = LiveDraftAdapter(self.temporary.name, provider,
                                   product_fetch=lambda url: observed_product(url, document()))
        job = {"id": "j", "lease_token": "test-lease", "role": "avito", "action": "draft",
               "payload": {"product_urls": [URL]}}
        result, artifacts = adapter.execute(job, lambda: None)
        self.assertTrue(result["products_verified"])
        self.assertFalse(result["published"])
        self.assertFalse(result["synthetic"])
        self.assertFalse(result["publishable"])
        self.assertEqual(result["publication_status"], "blocked")
        self.assertIn("<Price>143900</Price>", artifacts[0]["content"])
        self.assertEqual(result["product_evidence"][0]["source_url"], URL)

    def test_user_supplied_price_and_duplicate_urls_cannot_override_observation(self):
        adapter = LiveDraftAdapter(self.temporary.name, None)
        for payload in ({"product_urls": [URL], "items": []}, {"product_urls": [URL, URL]},
                        {"product_urls": [{}]}, {"product_urls": []}):
            with self.assertRaisesRegex(ValueError, "invalid_product_urls"):
                adapter.execute({"role": "avito", "action": "draft", "payload": payload}, lambda: None)

    def test_capability_check_uses_reads_does_not_claim_write_permission_or_expose_balance(self):
        called = []
        async def provider(path, params=None):
            called.append(path)
            if path.endswith("/self"):
                return {"id": 17, "private_phone": "never-return"}
            if path.endswith("/balance/"):
                return {"real": "1.29"}
            if path == "/autoload/v2/profile":
                error = RuntimeError("secret provider body")
                error.status_code = 403
                raise error
            return {}
        adapter = LiveDraftAdapter(self.temporary.name, provider)
        result, artifacts = adapter.execute({"role": "avito", "action": "plan", "payload": {"source": "avito-api"}}, lambda: None)
        capabilities = result["capabilities"]
        self.assertFalse(capabilities["publication_write_verified"])
        self.assertTrue(capabilities["checks"]["profile_read"]["verified"])
        self.assertEqual(capabilities["checks"]["autoload_profile_read"]["http_status"], 403)
        self.assertIn("LOW_BALANCE", capabilities["publication_blockers"])
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("1.29", json.dumps(result))
        self.assertNotIn("never-return", json.dumps(result))
        self.assertTrue(all(path.startswith(("/core/", "/autoload/")) for path in called))
        self.assertEqual(artifacts, [])

    def test_lease_loss_before_product_fetch_performs_no_external_read(self):
        called = []
        adapter = LiveDraftAdapter(self.temporary.name, None, product_fetch=lambda url: called.append(url))
        def lost():
            raise RuntimeError("lost")
        with self.assertRaisesRegex(RuntimeError, "lost"):
            adapter.execute({"role": "avito", "action": "draft", "payload": {"product_urls": [URL]}}, lost)
        self.assertEqual(called, [])

    def test_forbidden_action_or_role_is_rejected_before_provider_reads(self):
        called = []
        adapter = LiveDraftAdapter(self.temporary.name, None, product_fetch=lambda url: called.append(url))
        for role, action in (("avito", "publish"), ("content", "plan")):
            with self.assertRaisesRegex(ValueError, "action_not_allowed"):
                adapter.execute({"role": role, "action": action,
                                 "payload": {"source": "avito-api", "product_urls": [URL]}}, lambda: None)
        self.assertEqual(called, [])


class SupervisorTests(unittest.TestCase):
    def test_disabled_does_not_start_and_never_reveals_environment_secrets(self):
        supervisor = EmbeddedWorker(None, env={"BM_SERVICE_TOKEN": "test-private-value"})
        supervisor.start()
        self.assertIsNone(supervisor.thread)
        self.assertEqual(supervisor.status()["state"], "disabled")
        self.assertNotIn("test-private-value", json.dumps(supervisor.status()))

    def test_unexpected_exit_restarts_new_generation_then_gracefully_stops(self):
        generations = []
        started = threading.Event()
        class Worker:
            worker_id = "fake-registration"
            def __init__(self, stop):
                self.stopping = stop
            def run(self):
                if len(generations) == 1:
                    self.stopping.set()
                    raise RuntimeError("private diagnostics")
                started.set()
                self.stopping.wait(1)
        def factory(stop):
            worker = Worker(stop)
            generations.append(worker)
            return worker
        supervisor = EmbeddedWorker(None, env={"BM_EMBEDDED_WORKER_ENABLED": "1"},
                                    worker_factory=factory, restart_seconds=0.01)
        supervisor.start()
        self.assertTrue(started.wait(1))
        self.assertGreaterEqual(len(generations), 2)
        self.assertIsNot(generations[0].stopping, generations[1].stopping)
        self.assertFalse(supervisor.stop_event.is_set())
        supervisor.stop()
        self.assertFalse(supervisor.thread.is_alive())
        self.assertEqual(supervisor.status()["state"], "stopped")


if __name__ == "__main__":
    unittest.main()
