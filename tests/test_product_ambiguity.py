"""Synthetic parser fixtures only; no commercial feed or network access."""
import json
import unittest

from business_machine_products import observed_product

URL = "https://bestclimate-rnd.ru/isolated-parser-fixture/"


def microdata(extra="", name_extra=""):
    return ('<div id="js-product-page" itemscope itemtype="https://schema.org/Product">'
            '<meta itemprop="name" content="Parser fixture">' + name_extra +
            '<div itemscope itemtype="https://schema.org/Offer">'
            '<meta itemprop="price" content="42000">'
            '<meta itemprop="priceCurrency" content="RUB">'
            '<link itemprop="availability" href="https://schema.org/InStock">' +
            extra + '</div></div>').encode()


class AmbiguityTests(unittest.TestCase):
    def test_conflicting_price_cannot_be_chosen_by_document_order(self):
        for extra in ('<meta itemprop="price" content="1">',
                      '<span itemprop="price">1</span>'):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(ValueError, "product_microdata_conflict"):
                    observed_product(URL, microdata(extra))

    def test_conflicting_stock_cannot_be_chosen_by_document_order(self):
        body = microdata('<link itemprop="availability" href="https://schema.org/OutOfStock">')
        for content in (body, body.replace(b"InStock", b"TEMP").replace(b"OutOfStock", b"InStock").replace(b"TEMP", b"OutOfStock")):
            with self.assertRaisesRegex(ValueError, "product_microdata_conflict"):
                observed_product(URL, content)

    def test_repeated_identical_microdata_facts_remain_usable(self):
        value = observed_product(URL, microdata('<meta itemprop="price" content="42000">'
                                               '<span itemprop="price">42000</span>'))
        self.assertEqual(value["item"]["price"], 42000)
        self.assertFalse(value["evidence"]["stock_quantity"])

    def test_conflicting_name_does_not_invent_identity(self):
        with self.assertRaisesRegex(ValueError, "product_microdata_conflict"):
            observed_product(URL, microdata(name_extra='<span itemprop="name">Different model</span>'))

    def test_jsonld_duplicate_offer_keys_and_duplicate_identity_rejected(self):
        offer = '"@type":"Offer","price":"42000","priceCurrency":"RUB","availability":"https://schema.org/InStock"'
        base = '"@type":"Product","url":' + json.dumps(URL) + ',"name":"Parser fixture"'
        for duplicate in ('"price":"1"', '"availability":"https://schema.org/OutOfStock"', '"priceCurrency":"USD"'):
            data = '{' + base + ',"offers":{' + offer + ',' + duplicate + '}}'
            with self.subTest(duplicate=duplicate):
                with self.assertRaisesRegex(ValueError, "product_structured_data_invalid"):
                    observed_product(URL, ('<script type="application/ld+json">' + data + '</script>').encode())
        data = '{' + base + ',"url":"https://bestclimate-rnd.ru/other/","offers":{' + offer + '}}'
        with self.assertRaisesRegex(ValueError, "product_structured_data_invalid"):
            observed_product(URL, ('<script type="application/ld+json">' + data + '</script>').encode())


if __name__ == "__main__":
    unittest.main()
