# Offline XML structural QA

Run from the project root with Python 3.10 or newer:

```powershell
python -B avito_xml_qa.py PATH_TO_PRIVATE_FEED.xml
python -B -m unittest discover -s tests -p test_avito_xml_qa.py -v
```

This tool performs no HTTP requests, API calls, writes, uploads or publishing.
Input paths and field contents are not echoed in its JSON report.

Exit 0 means **structural_valid only**. The separate publication_ready field is
always false. Official category schema validation, fresh verified price and stock,
account permission/status checks and publisher controls remain mandatory.
This is not full Avito schema validation and does not establish image rights,
URL reachability, business accuracy, enum validity or category completeness.

The local base policy checks Ads/formatVersion=3/target=Avito.ru, nonempty batches,
unique Id and optional AvitoId, no duplicate direct fields, nonempty scalar base
fields, ASCII positive integer Price and at least one syntactically HTTP(S) Image.
Each category still requires an official schema and dependent-field validation.
New listings can omit AvitoId; if supplied, it must be nonempty and unique.
AvitoId must contain canonical positive ASCII digits without leading zeros.
Protected advertisement `8341283876` is rejected in either Id or AvitoId.
Different brands, prices and addresses are accepted without hardcoded commercial facts.

The private draft store preserves an optional `avito_id`/`AvitoId` mapping and
rejects conflicting aliases or duplicate targets. It rejects the protected ad,
protected upload `612013427` via `source_upload_id`/`upload_id`/`UploadId`, explicit
`manual`/`is_manual`/`source=manual`, and `account_name=Авито 2`. Input metadata is
not proof of managed ownership: every saved draft remains publication_ready=false
with schema, price/stock, ownership and owner-approval blockers. Unknown ownership
is allowed for private preparation only. No write adapter is enabled by this change.
Idempotency includes a SHA-256 of the full request, so changes to provenance cannot
silently reuse an earlier XML draft. Historical metadata without that hash must be
reviewed and staged under a fresh task ID; it is not silently overwritten.

DTD/entity declarations are rejected before parsing; only UTF-8 input is accepted.
Input reads are bounded. Configurable byte/ad/node/depth budgets protect local
resources. Optional --max-title-chars, --max-description-chars and --max-images
enforce caller-selected limits. All numeric limits must be positive. Defaults and
optional limits are local policy, **not claimed Avito requirements**.

The older ../validate_feed_xml.py remains a strict, explicitly named legacy Haier
fixture check. Its historical fixed values are not current price/stock evidence.
Its output now separates fixture validity from publication readiness. It is
unsuitable for validating arbitrary batches. Existing fixture checks are retained.

Tests use synthetic advertisements and example.invalid URLs only, without network,
real inventory, current prices, real ad identifiers or account writes.
