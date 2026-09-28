from app import _account_id, _avito_get, _count_items, app
from campaign_probe import register_campaign_probe
from diagnostic import register_readonly_diagnostic

register_readonly_diagnostic(app, _avito_get, _count_items, _account_id)
register_campaign_probe(app, _avito_get)
