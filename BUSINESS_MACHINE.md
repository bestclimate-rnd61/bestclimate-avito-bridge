# Business Machine staging Avito worker

The standalone worker is a separate process: `python -m business_machine_worker`. It imports
only the safe local draft store and new adapter. Do not start `main:app`, `app:app`,
legacy recovery scripts, Telegram webhook setup or Avito API jobs for this service.

The control-center API/Postgres queue is the only job/result journal. This worker
registers only `avito`, and handles only `plan`, `validate` and `draft`. Each result
reports `published=false`, `external_writes=0`; `schema_validated=false` is explicit
because local Id/Title/Price validation is not complete Avito schema validation.
The worker has no publishing, paid action, messaging or model-provider adapter.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| BM_API_URL | http://api:8080 | Internal queue API; remote plaintext HTTP rejected |
| BM_SERVICE_TOKEN | required unless file supplied | Service credential, never logged |
| BM_SERVICE_TOKEN_FILE | empty | Private mounted service token file fallback |
| BM_WORKER_ID | avito plus hostname | Raw ID returned from registration is used in requests |
| BM_ARTIFACT_DIR | /data/business-machine/artifacts | Persistent private writable artifact volume |
| BM_LEASE_SECONDS | 90 | Fenced job lease length |
| BM_HEARTBEAT_SECONDS | 20 | Separate worker/job heartbeat interval, below half lease |
| BM_POLL_SECONDS | 2 | Idle poll delay |
| BM_API_TIMEOUT_SECONDS | 10 | Per-request timeout; TLS verification remains enabled |

Only the BM service credential is needed. Do not mount production Avito, Telegram,
Buffer or GitHub credentials. Dockerfile.business-machine copies three safe Python
files, uses stdlib only, starts the new worker and runs as UID/GID 10001. A mounted
artifact volume must be writable by the selected container UID.

## Queue contract and recovery

Requests use `Authorization: Bearer <BM_SERVICE_TOKEN>`. The worker registers via
POST `/v1/worker/register`; only a returned avito registration allows claims. It
uses POST `/v1/worker/heartbeat`, `/v1/jobs/claim`, and per-job `/heartbeat`,
`/complete`, `/fail`. Job fields are snake_case; request fields use workerId,
leaseToken, leaseSeconds. Every completion/failure carries the claimed lease token.
An HTTP 409 or lease expiry discards the result; a stale attempt cannot attach its
artifact paths to the central job. Heartbeat runs independently of draft rendering.

Temporary API failure backs off and heartbeat does not extend local ownership
without a successful server acknowledgement. Permanent invalid payload/action
fails without retry; artifact I/O and shutdown failures request retry. The API owns
attempt limits and the terminal dead-letter state. SIGTERM/SIGINT stops claiming,
rejects unfinished output and attempts a fenced retryable release; if the API is
unreachable the server reclaims the expired lease. Redirects are rejected so the
service credential cannot be forwarded to a different host.

## Private draft artifacts

`payload.items` uses legacy safe item validation, always staged as bulk_edit inside
a fresh temporary directory. The legacy storage module is unchanged. The adapter
commits XML, JSON metadata and hashed manifest together by atomic directory rename
on the same volume. Uncommitted orphan staging directories are discarded on replay;
committed hashes and the input digest are checked before replay. Conflicting input
for an existing attempt is rejected.

Paths are scoped by SHA256(job ID) and SHA256(lease token). Raw lease tokens never
appear in paths/manifests/results/logs. Concurrent attempts cannot overwrite one
another; same-attempt writers serialize with a filesystem lock. A lost lease may
leave a private attempt artifact, but the central queue accepts only the current
owner's fenced completion. Returned descriptors contain name, media_type, sha256,
size_bytes, path and attempt_key. Outgoing descriptors also carry bounded inline
UTF-8 content so the Node quality agent independently checks hashes/XML without a
shared filesystem. Each file is capped at 64 KiB; the result+artifact JSON budget
is 60 KiB. Larger outputs keep their private files and return manual_qa_required,
inline_artifacts_complete=false and ARTIFACT_INLINE_LIMIT, without inline content.
Persisted manifests stay metadata-only. These are private local paths, not public
feeds. Python reports only local safe-item/XML staging checks, qa_required=true and
schema_validated=false; independent Node QA records its own structural evidence.

Production publishing and object-store export remain separate integrations
requiring explicit account/scopes/approval. Never treat a saved XML draft as an
accepted or published Avito listing.

## Existing Railway service integration

The existing FastAPI app now registers an opt-in supervised thread. It shares
the existing service, mounted `/data` volume and central PostgreSQL queue; no
additional Railway service or database is required. The existing Railway start
command, feed overrides and customer integrations are preserved.

Set private Railway variables `BM_API_URL` to the control-center `/bm` endpoint,
`BM_SERVICE_TOKEN` to its avito-only worker credential, and
`BM_EMBEDDED_WORKER_ENABLED=1`. The token is never returned by the bridge.
`GET /business-machine/status` reports only local thread/registration metadata,
and `publishing_enabled=false`. Queue heartbeat and completed job history provide
the separate evidence of actual execution. Worker crashes restart a new generation;
termination drains the active fenced attempt. New generations have unique IDs.

Before any deployment, neutralize the legacy one-shot startup mutation triggers
`AVITO_RECOVERY_TARGET`, `AVITO_RECOVERY_RETRY_TARGET`, `AVITO_OPTIMIZE_TARGET`,
`AVITO_GROWTH_V3_ACTION`, `CPXPROMO_LOWER_TARGETS`. Leave feed configuration and
all unrelated variables intact. They were cleared with deploys skipped during
P1 preparation; that alone does not prove the new worker is deployed.

An avito `plan` job with `payload={"source":"avito-api"}` makes actual read-only
profile/items/autoload calls using the existing server-side adapter and records
only verified booleans/status codes in the queue result. It also records the
low-balance boolean without the wallet amount. Read access never proves publish
scope, so `publication_write_verified` remains false until a separately authorized
official publishing mechanism is verified.

An avito `draft` or `validate` job may supply `payload.product_urls` (1–10 unique
HTTPS product URLs on `bestclimate-rnd.ru`). The worker reads fresh Webasyst
JSON-LD or main-product microdata, requires exactly one product, one exact RUB
offer and explicit `InStock`, and derives stable IDs from source URLs. Caller
prices/items cannot override observed data. The queue result stores source URL,
retrieval time, page SHA256, currency and observed availability. It does not
invent warehouse quantities or promise that storefront stock equals supplier
stock. Ambiguous, missing, unavailable and fractional offers fail closed.
Related-product card prices are excluded from the explicit Webasyst main object.

For example, submit through the authorized central API:

```json
{"role":"avito","action":"draft","environment":"staging","mode":"dry_run",
 "payload":{"product_urls":["https://bestclimate-rnd.ru/split-sistema-newtek-nt-65cha07/"]}}
```

This reads the current product again at execution time. Its XML remains a private
draft with `published=false`, `publishable=false`, `schema_validated=false`,
`publication_status=blocked`. A balance restriction never deletes prepared drafts.
Provider-category schema, official write scope, account allowlist, approval and
fresh price/availability checks are required before any future publication.

## Local validation and staging CI

No dependency install is needed for existing or BM tests:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
```

The new suite uses fake queue clients, temp directories and synthetic tokens only.
It covers lease loss/expiry, graceful stop, outage retry, registration roles,
idempotent concurrent replay, separate-attempt fencing, artifact integrity and
partial-pair crash recovery. Run tests from the BM staging checkout with a minimal
environment, no business credentials and no network. The existing bridge PR workflow runs the full suite for BM worker, adapter,
Dockerfile, documentation and test changes. The control-center BM staging workflow
also checks out this branch for a cross-repository contract test. Do not change production CI or deploy from
the production-tracked main branch to test this worker.
