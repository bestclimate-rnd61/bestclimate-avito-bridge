"""Read observed Webasyst product data; never infer a price or stock quantity."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
import ssl

HOSTS = frozenset({"bestclimate-rnd.ru", "www.bestclimate-rnd.ru"})
MAX_BYTES = 1024 * 1024


def _unambiguous_object(pairs):
    """JSON-LD duplicate keys must never choose a price/stock by order."""
    value = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("product_structured_data_ambiguous")
        value[key] = child
    return value


def _microdata_field(scope, prop, value):
    # Equivalent repeated markup is common; differing facts in one scope are
    # ambiguous, even if the final value happens to look like a valid offer.
    if prop in scope and scope[prop] != value:
        raise ValueError("product_microdata_conflict")
    scope[prop] = value


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def product_url(value):
    if not isinstance(value, str) or len(value) > 1500:
        raise ValueError("invalid_product_url")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.port not in (None, 443)
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or not parsed.path or parsed.path == "/"):
        raise ValueError("invalid_product_url")
    return value


class StructuredData(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.reading, self.parts, self.documents = False, [], []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            self.reading = dict(attrs).get("type", "").lower() == "application/ld+json"
            self.parts = []

    def handle_data(self, data):
        if self.reading:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.reading:
            self.reading = False
            try:
                self.documents.append(json.loads("".join(self.parts), object_pairs_hook=_unambiguous_object))
            except (ValueError, TypeError):
                raise ValueError("product_structured_data_invalid") from None


class Microdata(HTMLParser):
    """Read one explicit Webasyst main Product, never related-card prices."""
    VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.products = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        scope = next((entry["scope"] for entry in reversed(self.stack) if entry["scope"] is not None), None)
        created = None
        if "itemscope" in attrs:
            kind = attrs.get("itemtype", "").rstrip("/").rsplit("/", 1)[-1]
            created = {"@type": kind}
            if kind == "Product":
                created.update({"offers": [], "_main": attrs.get("id") == "js-product-page"})
                self.products.append(created)
            elif kind == "Offer":
                owner = next((entry["scope"] for entry in reversed(self.stack)
                              if entry["scope"] is not None and entry["scope"].get("@type") == "Product"), None)
                if owner is not None:
                    owner["offers"].append(created)
            scope = created
        prop = attrs.get("itemprop")
        capture = None
        if scope is not None and prop in ("name", "price", "priceCurrency", "availability", "url"):
            value = attrs.get("content", attrs.get("href"))
            if value is not None:
                _microdata_field(scope, prop, value)
            else:
                capture = {"scope": scope, "prop": prop, "parts": []}
        if tag not in self.VOID:
            self.stack.append({"tag": tag, "scope": created, "capture": capture})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        for entry in self.stack:
            if entry["capture"]:
                entry["capture"]["parts"].append(data)

    def handle_endtag(self, tag):
        index = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i]["tag"] == tag), None)
        if index is None:
            return
        closed, self.stack = self.stack[index:], self.stack[:index]
        for entry in closed:
            capture = entry["capture"]
            if capture:
                _microdata_field(capture["scope"], capture["prop"], "".join(capture["parts"]).strip())


def _products(value):
    if isinstance(value, list):
        for child in value:
            yield from _products(child)
    elif isinstance(value, dict):
        kind = value.get("@type")
        if kind == "Product" or isinstance(kind, list) and "Product" in kind:
            yield value
        if "@graph" in value:
            yield from _products(value["@graph"])


def _fields(product):
    name, offers = product.get("name"), product.get("offers")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 150:
        raise ValueError("product_title_invalid")
    if isinstance(offers, list) and len(offers) == 1:
        offers = offers[0]
    if not isinstance(offers, dict) or offers.get("@type") != "Offer":
        raise ValueError("product_offer_ambiguous")
    if offers.get("priceCurrency") != "RUB":
        raise ValueError("product_currency_invalid")
    try:
        price = Decimal(str(offers.get("price")))
        if not price.is_finite() or price <= 0 or price != price.to_integral_value():
            raise InvalidOperation()
    except (InvalidOperation, ValueError):
        raise ValueError("product_price_invalid") from None
    availability = offers.get("availability")
    if availability not in ("https://schema.org/InStock", "http://schema.org/InStock"):
        raise ValueError("product_stock_not_confirmed")
    return name.strip(), int(price)


def _matches_url(product, requested):
    identity = product.get("url") or product.get("@id")
    if isinstance(identity, dict):
        identity = identity.get("@id")
    if not isinstance(identity, str) or len(identity) > 1600:
        return False
    try:
        candidate = urlsplit(urljoin(requested, identity))
        expected = urlsplit(requested)
        return (candidate.scheme in ("https", "http") and candidate.hostname in HOSTS
                and candidate.port in (None, 80, 443) and not candidate.query
                and not candidate.username and not candidate.password
                and candidate.path.rstrip("/") == expected.path.rstrip("/"))
    except ValueError:
        return False


def observed_product(url, body, *, now=None):
    product_url(url)
    if not isinstance(body, bytes) or len(body) > MAX_BYTES:
        raise ValueError("product_response_too_large")
    parser, microdata = StructuredData(), Microdata()
    try:
        html = body.decode("utf-8")
        parser.feed(html)
        microdata.feed(html)
    except UnicodeDecodeError:
        raise ValueError("product_encoding_invalid") from None
    structured = list(_products(parser.documents))
    matching = [value for value in structured if _matches_url(value, url)]
    main = [value for value in microdata.products if value.pop("_main", False)]
    if len(main) > 1 or len(matching) > 1:
        raise ValueError("product_identity_ambiguous")
    if main:
        # Webasyst explicitly scopes its main product. Related-card JSON-LD can
        # never replace that object. Conflicting data for the same URL blocks.
        product = main[0]
        source = "public_webasyst_product_microdata"
        fields = _fields(product)
        if matching and _fields(matching[0]) != fields:
            raise ValueError("product_sources_conflict")
    elif matching:
        product, source = matching[0], "public_webasyst_product_jsonld"
        fields = _fields(product)
    else:
        candidates = [value for value in microdata.products if _matches_url(value, url)]
        if len(candidates) != 1:
            raise ValueError("product_identity_ambiguous")
        product, source = candidates[0], "public_webasyst_product_microdata"
        fields = _fields(product)
    name, price = fields
    # Stock is only the site's observation; no quantity is invented. It must be
    # rechecked before any later publisher is enabled.
    return {"item": {"id": "BC-" + hashlib.sha256(url.encode()).hexdigest()[:24],
                     "title": name, "price": price},
            "evidence": {"source_url": url, "source_sha256": hashlib.sha256(body).hexdigest(),
                         "observed_at": (now or datetime.now(timezone.utc)).isoformat(),
                         "currency": "RUB", "availability": "InStock", "stock_quantity": None,
                         "source": source, "publication_recheck_required": True}}


def fetch_product(url, *, opener=None):
    product_url(url)
    opener = opener or build_opener(HTTPSHandler(context=ssl.create_default_context()), NoRedirects())
    request = Request(url, headers={"User-Agent": "BestClimateBusinessMachine/1.0 readonly-product-check"})
    with opener.open(request, timeout=15) as response:
        if response.status != 200 or urlsplit(response.geturl()).hostname not in HOSTS:
            raise ValueError("product_http_error")
        body = response.read(MAX_BYTES + 1)
    return observed_product(url, body)
