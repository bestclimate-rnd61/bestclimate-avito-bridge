"""Offline structural QA only; never authorizes Avito publication."""
import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

@dataclass(frozen=True)
class Limits:
    # Local resource budgets, NOT Avito category specifications.
    max_bytes: int = 8 * 1024 * 1024
    max_ads: int = 10000
    max_nodes: int = 200000
    max_depth: int = 32
    max_title_chars: int | None = None
    max_description_chars: int | None = None
    max_images: int | None = None

REQUIRED = ("Id", "Title", "Description", "Category", "Price", "Address",
            "ContactMethod", "Images")
SCALARS = frozenset(REQUIRED) - {"Images"}

def report(errors, count=0):
    return {
        "profile": "generic_structural_qa_v1",
        "structural_valid": not errors,
        "publication_ready": False,
        "ads_checked": count,
        "errors": errors,
        "publication_blockers": [
            "official_category_schema_not_validated",
            "fresh_price_and_stock_not_verified",
            "account_permissions_and_publication_checks_not_verified",
        ],
        "scope": "Offline XML shape and local safety policy; no network or publication",
    }

def validate_bytes(data, limits=Limits()):
    errors = []
    def fail(code, path="feed"):
        errors.append({"code": code, "path": path})
    for name, value in vars(limits).items():
        if value is not None and (type(value) is not int or value <= 0):
            raise ValueError("Limits must be positive integers")
    if len(data) > limits.max_bytes:
        fail("local_byte_budget_exceeded")
        return report(errors)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        fail("only_utf8_supported")
        return report(errors)
    if "\x00" in text:
        fail("only_utf8_supported")
        return report(errors)
    if re.search(r"<!\s*(DOCTYPE|ENTITY)\b", text, re.I):
        fail("dtd_or_entity_declaration_forbidden")
        return report(errors)
    declaration = re.match(r"\s*<\?xml\b[^?]*\?>", text)
    if declaration:
        encoding = re.search(r"""encoding\s*=\s*['"]([^'"]+)['"]""",
                             declaration.group(), re.I)
        if encoding and encoding.group(1).lower() not in {"utf-8", "utf8"}:
            fail("only_utf8_supported")
            return report(errors)
    try:
        root = ET.fromstring(text)
    except (ET.ParseError, ValueError):
        fail("xml_parse_error")
        return report(errors)
    stack = [(root, 1)]
    nodes = 0
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > limits.max_nodes or depth > limits.max_depth:
            fail("local_tree_budget_exceeded")
            return report(errors)
        stack.extend((child, depth + 1) for child in node)
    if root.tag != "Ads":
        fail("root_must_be_Ads")
    if root.attrib.get("formatVersion") != "3":
        fail("expected_formatVersion_3")
    if root.attrib.get("target") != "Avito.ru":
        fail("expected_target_Avito_ru")
    if any(child.tag != "Ad" for child in root):
        fail("unexpected_root_child")
    ads = root.findall("Ad")
    if not ads:
        fail("empty_batch")
    if len(ads) > limits.max_ads:
        fail("local_ad_budget_exceeded")
        return report(errors)
    ids, avito_ids = set(), set()
    for index, ad in enumerate(ads, 1):
        path = f"Ad[{index}]"
        counts = Counter(child.tag for child in ad)
        # Reject ANY duplicate direct field, including category-specific fields.
        for tag, count in counts.items():
            if count > 1:
                fail("duplicate_direct_field", path)
        for tag in REQUIRED:
            el = ad.find(tag)
            if el is None or (tag != "Images" and not (el.text or "").strip()):
                fail("required_field_missing_or_empty", path + "/" + tag)
        for tag in SCALARS | {"AvitoId"}:
            el = ad.find(tag)
            if el is not None and len(el):
                fail("scalar_field_contains_elements", path + "/" + tag)
        ident = (ad.findtext("Id") or "").strip()
        if ident in ids:
            fail("duplicate_Id", path)
        ids.add(ident)
        avito_id = (ad.findtext("AvitoId") or "").strip()
        if ad.find("AvitoId") is not None:
            if not avito_id:
                fail("empty_AvitoId", path)
            elif avito_id in avito_ids:
                fail("duplicate_AvitoId", path)
            avito_ids.add(avito_id)
        price = (ad.findtext("Price") or "").strip()
        # ASCII digits, no float/exponent/sign/Unicode numerals or silent coercion.
        if not re.fullmatch(r"[0-9]+", price) or not price.strip("0"):
            fail("price_must_be_positive_integer", path + "/Price")
        for tag, budget in (("Title", limits.max_title_chars),
                            ("Description", limits.max_description_chars)):
            if budget is not None and len(ad.findtext(tag) or "") > budget:
                fail("local_text_budget_exceeded", path + "/" + tag)
        images = ad.find("Images")
        image_nodes = list(images) if images is not None else []
        if not image_nodes:
            fail("image_required", path + "/Images")
        if limits.max_images is not None and len(image_nodes) > limits.max_images:
            fail("local_image_budget_exceeded", path + "/Images")
        for image in image_nodes:
            valid_url = False
            try:
                parsed = urlsplit(image.attrib.get("url", ""))
                valid_url = (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                             and parsed.username is None and parsed.password is None
                             and not any(c.isspace() or ord(c) < 32
                                         for c in image.attrib.get("url", "")))
                _ = parsed.port  # Reject malformed ports without disclosing the URL.
            except ValueError:
                valid_url = False
            if image.tag != "Image" or len(image) or not valid_url:
                fail("invalid_image_element_or_url", path + "/Images")
    return report(errors, len(ads))

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", type=Path)
    for name, field in Limits.__dataclass_fields__.items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=field.default)
    args = parser.parse_args(argv)
    try:
        limits = Limits(**{key: getattr(args, key) for key in Limits.__dataclass_fields__})
        # Bounded read even when source is larger than the configured budget.
        with args.xml.open("rb") as source:
            data = source.read(limits.max_bytes + 1) if limits.max_bytes > 0 else b""
        result = validate_bytes(data, limits)
    except (OSError, ValueError, OverflowError):
        result = report([{"code": "input_or_configuration_error", "path": "feed"}])
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["structural_valid"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
