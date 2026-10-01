import os
import re

import httpx

# BotFather tokens pasted from mobile can contain line breaks, zero-width chars
# or surrounding quotes/backticks. Normalize those without exposing the secret.
if "LEAD_TELEGRAM_BOT_TOKEN" in os.environ:
    raw_token = os.environ["LEAD_TELEGRAM_BOT_TOKEN"]
    token = re.sub(r"[\s\u200b\u200c\u200d\ufeff]+", "", raw_token).strip("`'\"")
    os.environ["LEAD_TELEGRAM_BOT_TOKEN"] = token
    token_parts = token.split(":", 1)
    token_id_ok = len(token_parts) == 2 and token_parts[0].isdigit()
    token_suffix = token_parts[1] if len(token_parts) == 2 else ""
    token_chars_ok = bool(token_suffix) and bool(re.fullmatch(r"[A-Za-z0-9_-]+", token_suffix))
    print(
        "TELEGRAM_TOKEN_DIAG "
        f"length={len(token)} colon_count={token.count(':')} "
        f"id_digits={token_id_ok} suffix_length={len(token_suffix)} allowed_chars={token_chars_ok}"
    )

from app import AVITO_API_BASE, _account_id, _avito_get, _count_items, _get_token, app
from autoload_category_probe import register_autoload_category_probe
from autoload_target_probe import register_autoload_target_probe
from campaign_probe import register_campaign_probe
from cpxpromo_probe import register_cpxpromo_probe
from diagnostic import register_readonly_diagnostic
from feed_server import register_feed_server
import lead_funnel_v2 as lead_funnel
from optimizer_7556388793 import register_flagship_optimizer
from recovery import register_recovery
from recovery_retry import register_recovery_retry
from stats_probe import register_stats_probe

# Safe Telegram diagnostics: log only HTTP status / Telegram error description,
# never the bot token or request URL containing it.
async def _telegram_api_with_diag(method, payload=None):
    token = lead_funnel.TELEGRAM_BOT_TOKEN
    if not token:
        print(f"TELEGRAM_API_DIAG method={method} error=missing_token")
        return None
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/{method}",
                json=payload or {},
            )
        try:
            data = response.json()
        except ValueError:
            data = None
        if response.status_code >= 400 or not isinstance(data, dict) or not data.get("ok"):
            description = ""
            if isinstance(data, dict):
                description = str(data.get("description", ""))[:180]
            print(
                f"TELEGRAM_API_DIAG method={method} status={response.status_code} "
                f"description={description!r}"
            )
            return data if isinstance(data, dict) else None
        return data
    except httpx.HTTPError as exc:
        print(f"TELEGRAM_API_DIAG method={method} http_error={type(exc).__name__}")
        return None

lead_funnel._telegram_api = _telegram_api_with_diag
lead_router = lead_funnel.router

register_readonly_diagnostic(app, _avito_get, _count_items, _account_id)
register_campaign_probe(app, _avito_get)
register_feed_server(app)
register_recovery(app, _avito_get, _get_token, AVITO_API_BASE)
register_recovery_retry(app, _avito_get, _get_token, AVITO_API_BASE)
register_stats_probe(app, _avito_get, _account_id, _get_token, AVITO_API_BASE)
register_flagship_optimizer(app, _avito_get, _get_token, AVITO_API_BASE)
register_autoload_target_probe(app, _avito_get)
register_autoload_category_probe(app, _avito_get)
register_cpxpromo_probe(app, _avito_get)
app.include_router(lead_router)
