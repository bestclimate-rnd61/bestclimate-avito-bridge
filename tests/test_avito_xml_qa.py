"""Entirely synthetic, offline fixtures; example.invalid URLs are never fetched."""
import unittest
from avito_xml_qa import Limits, validate_bytes

def ad(ident="synthetic-a", extra="", price="123"):
    return (f"<Ad><Id>{ident}</Id><Title>Synthetic fixture</Title>"
            "<Description>Not a real advertisement</Description><Category>Fixture</Category>"
            f"<Price>{price}</Price><Address>Fixture address</Address>"
            "<ContactMethod>Fixture</ContactMethod>"
            '<Images><Image url="https://example.invalid/fixture.png"/></Images>'
            f"{extra}</Ad>")

def feed(body):
    return ('<Ads formatVersion="3" target="Avito.ru">' + body + '</Ads>').encode()

class StructuralTests(unittest.TestCase):
    def reject(self, data, code=None, **limits):
        result = validate_bytes(data, Limits(**limits))
        self.assertFalse(result["structural_valid"])
        self.assertFalse(result["publication_ready"])
        if code:
            self.assertIn(code, [item["code"] for item in result["errors"]])
        return result

    def test_batch_and_never_publication_ready(self):
        result = validate_bytes(feed(ad() + ad("synthetic-b", price="456")))
        self.assertTrue(result["structural_valid"], result)
        self.assertEqual(result["ads_checked"], 2)
        self.assertFalse(result["publication_ready"])
        self.assertEqual(len(result["publication_blockers"]), 3)

    def test_duplicate_ids(self):
        self.reject(feed(ad() + ad()), "duplicate_Id")

    def test_duplicate_avito_ids(self):
        self.reject(feed(ad(extra="<AvitoId>11</AvitoId>") +
                         ad("b", extra="<AvitoId>11</AvitoId>")), "duplicate_AvitoId")

    def test_duplicate_critical_and_unknown_fields(self):
        for field in ("Price", "Id", "Title", "Images", "CustomField"):
            extra = f"<{field}>123</{field}>"
            if field == "CustomField":
                extra += extra
            with self.subTest(field=field):
                self.reject(feed(ad(extra=extra)), "duplicate_direct_field")

    def test_price_format(self):
        for value in ("0", "000", "-3", "+3", "1.2", "1e3", "NaN", "\u0661\u0662", ""):
            with self.subTest(value=value):
                self.reject(feed(ad(price=value)), "price_must_be_positive_integer")

    def test_no_numeric_conversion_limit(self):
        # No int() conversion; large numeric content is still bounded by byte budget.
        self.assertTrue(validate_bytes(feed(ad(price="9" * 5000)))["structural_valid"])

    def test_dtd_and_entities(self):
        for prefix in ('<!DOCTYPE Ads>', '<!DOCTYPE Ads [<!ENTITY x "123">]>',
                       '<!DOCTYPE Ads SYSTEM "file:///synthetic-not-read">'):
            self.reject(prefix.encode() + feed(ad()), "dtd_or_entity_declaration_forbidden")

    def test_utf16_and_declared_encoding(self):
        self.reject(feed(ad()).decode().encode("utf-16"), "only_utf8_supported")
        self.reject(b'<?xml version="1.0" encoding="iso-8859-1"?>' + feed(ad()),
                    "only_utf8_supported")

    def test_utf16_without_bom_cannot_bypass_dtd_guard(self):
        payload = '<!DOCTYPE Ads [<!ENTITY x "expanded">]><Ads>&x;</Ads>'
        for encoding in ("utf-16-le", "utf-16-be"):
            with self.subTest(encoding=encoding):
                self.reject(payload.encode(encoding), "only_utf8_supported")
                self.reject(feed(ad()).decode().encode(encoding), "only_utf8_supported")

    def test_xml_nul_rejected(self):
        self.reject(feed(ad()).replace(b"Synthetic", b"Syn\x00thetic"),
                    "only_utf8_supported")

    def test_parse_and_root(self):
        self.reject(b"<Ads>", "xml_parse_error")
        self.reject(feed(ad()).replace(b"<Ads ", b"<Other ").replace(b"</Ads>", b"</Other>"),
                    "root_must_be_Ads")

    def test_empty_and_unknown_root_child(self):
        self.reject(feed(""), "empty_batch")
        self.reject(feed(ad() + "<Other/>"), "unexpected_root_child")

    def test_missing_required(self):
        self.reject(feed(ad()).replace(b"<Price>123</Price>", b""),
                    "required_field_missing_or_empty")

    def test_nested_scalar(self):
        self.reject(feed(ad()).replace(b"<Price>123</Price>", b"<Price><N>123</N></Price>"),
                    "scalar_field_contains_elements")

    def test_local_budgets(self):
        for limits, code in (({"max_bytes": 10}, "local_byte_budget_exceeded"),
                             ({"max_ads": 1}, "local_ad_budget_exceeded"),
                             ({"max_nodes": 2}, "local_tree_budget_exceeded"),
                             ({"max_depth": 2}, "local_tree_budget_exceeded"),
                             ({"max_title_chars": 2}, "local_text_budget_exceeded"),
                             ({"max_description_chars": 2}, "local_text_budget_exceeded")):
            with self.subTest(limits=limits):
                self.reject(feed(ad() + ad("b")), code, **limits)

    def test_invalid_limits(self):
        for value in (0, -1, True):
            with self.assertRaises(ValueError):
                validate_bytes(feed(ad()), Limits(max_ads=value))

    def test_image_safety(self):
        for value in ("javascript:fixture", "file:///fixture", "https://[",
                      "https://u:p@example.invalid/a", "https://example.invalid:bad/a",
                      "https://example.invalid/a b"):
            with self.subTest(value=value):
                self.reject(feed(ad()).replace(b"https://example.invalid/fixture.png",
                                               value.encode()), "invalid_image_element_or_url")

    def test_images_required_and_budget(self):
        self.reject(feed(ad()).replace(b'<Image url="https://example.invalid/fixture.png"/>', b""),
                    "image_required")
        image = b'<Image url="https://example.invalid/fixture.png"/>'
        self.reject(feed(ad()).replace(image, image + image), "local_image_budget_exceeded",
                    max_images=1)

    def test_report_does_not_echo_input(self):
        result = self.reject(feed(ad(price="SECRET_MARKER")))
        self.assertNotIn("SECRET_MARKER", str(result))

if __name__ == "__main__":
    unittest.main()
