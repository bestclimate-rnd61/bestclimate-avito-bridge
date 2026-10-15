# Business Machine staging Avito worker

This worker is a separate process: `python -m business_machine_worker`. It imports
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

Production publishing, read-only business-account adapters and object-store export
remain separate future integrations requiring explicit account/scopes/approval.

## Local validation and staging CI

No dependency install is needed for existing or BM tests:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
```

The new suite uses fake queue clients, temp directories and synthetic tokens only.
It covers lease loss/expiry, graceful stop, outage retry, registration roles,
idempotent concurrent replay, separate-attempt fencing, artifact integrity and
partial-pair crash recovery. Run tests from the BM staging checkout with a minimal
environment, no business credentials and no network. Existing GitHub Actions uses
PR path filters that do not include the new files; wire this command into the new
BM staging workflow in control-center. Do not change production CI or deploy from
the production-tracked main branch to test this worker.
