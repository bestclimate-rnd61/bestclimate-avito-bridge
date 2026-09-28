from app import _avito_get, _count_items, app
from diagnostic import register_readonly_diagnostic

register_readonly_diagnostic(app, _avito_get, _count_items)
