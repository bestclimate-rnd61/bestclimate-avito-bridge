"""Restricted browser worker foundation. No credentials, navigation or writes by default.

Runs as an optional role in the existing durable queue. A browser task is a
structured request, not arbitrary Python, JavaScript or an unrestricted URL.
"""
from urllib.parse import urlsplit

ALLOWED_HOSTS = frozenset({
    "www.avito.ru", "avito.ru", "www.instagram.com",
    "business.facebook.com", "bestclimate-rnd.ru",
    "www.bestclimate-rnd.ru", "hosting.timeweb.ru",
})
READ_ACTIONS = frozenset({"inspect_title", "inspect_text"})
WRITE_ACTIONS = frozenset({"fill", "click", "upload", "publish"})
# Writes are opt-in per service and task, not a blanket read-only architecture.
# A service-specific executor must implement each action and verify the result.

def validate_request(payload):
    if not isinstance(payload, dict):
        raise ValueError("browser payload must be an object")
    action = payload.get("action")
    if action not in READ_ACTIONS | WRITE_ACTIONS:
        raise ValueError("unsupported browser action")
    raw = payload.get("url")
    if not isinstance(raw, str) or len(raw) > 2048:
        raise ValueError("valid URL required")
    url = urlsplit(raw)
    if url.scheme != "https" or url.username or url.password or url.port:
        raise ValueError("only HTTPS URLs without credentials or ports")
    if url.hostname not in ALLOWED_HOSTS:
        raise ValueError("host not allowlisted")
    if action in WRITE_ACTIONS:
        if not payload.get("authorized_write"):
            raise PermissionError("explicit authorized_write required")
        if not isinstance(payload.get("task_id"), str) or not payload["task_id"].strip():
            raise ValueError("write requires durable task_id")
        if action == "publish" and not payload.get("publish_approved"):
            raise PermissionError("publish approval required")
    return {"action": action, "url": raw}

def execute(payload):
    request = validate_request(payload)
    if request["action"] in WRITE_ACTIONS:
        raise NotImplementedError("write adapter not yet implemented; never report success")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright not installed in current runtime") from exc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(accept_downloads=False)
            page = context.new_page()
            page.goto(request["url"], wait_until="domcontentloaded", timeout=15000)
            # Fail closed on redirects outside the allowlist.
            target = urlsplit(page.url)
            if target.scheme != "https" or target.hostname not in ALLOWED_HOSTS:
                raise PermissionError("redirect outside allowlist")
            result = {"status": "inspected", "url": page.url, "title": page.title()}
            if request["action"] == "inspect_text":
                result["text_preview"] = page.locator("body").inner_text(timeout=5000)[:2000]
            return result
        finally:
            browser.close()
