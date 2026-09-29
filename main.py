import os
import re

# BotFather tokens can accidentally be pasted with hidden line breaks on mobile.
# Remove all whitespace before the Telegram integration reads the token.
if "LEAD_TELEGRAM_BOT_TOKEN" in os.environ:
    os.environ["LEAD_TELEGRAM_BOT_TOKEN"] = re.sub(r"\s+", "", os.environ["LEAD_TELEGRAM_BOT_TOKEN"])

from app import AVITO_API_BASE, _account_id, _avito_get, _count_items, _get_token, app
from campaign_probe import register_campaign_probe
from diagnostic import register_readonly_diagnostic
from feed_server import register_feed_server
from lead_funnel_v2 import router as lead_router
from recovery import register_recovery
from recovery_retry import register_recovery_retry

register_readonly_diagnostic(app, _avito_get, _count_items, _account_id)
register_campaign_probe(app, _avito_get)
register_feed_server(app)
register_recovery(app, _avito_get, _get_token, AVITO_API_BASE)
register_recovery_retry(app, _avito_get, _get_token, AVITO_API_BASE)
app.include_router(lead_router)
