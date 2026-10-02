# Skillspector Web — scan service

The FastAPI service behind [Skillspector Web](../README.md). It imports
[skillspector](https://github.com/NVIDIA/skillspector) as a library and streams its compiled
LangGraph pipeline (`skillspector.graph.graph`) for each scan — no CLI subprocess, no output
parsing. Scan history and settings are stored in SQLite by default, or in Postgres when
`SKILLSPECTOR_WEB_DATABASE_URL` is set; progress and logs are captured live.

The service is meant to sit on an internal network behind the web app's Nitro proxy
(`server/api/*`), which maps `/api/<path>` to `/<path>` here. Interactive OpenAPI docs are served at
`/docs` on the service itself.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Service status, deployment mode, auth mode, skillspector version, and whether the server's Claude login is usable. |
| `GET` | `/auth/session` | — | `{ auth, user, needs_setup, signup_allowed }` for the bearer token, if any. |
| `POST` | `/auth/setup` | accounts | Create the first account, as admin; `409` once any account exists. Returns `{ token, expires_at, user }`. |
| `POST` | `/auth/login` | accounts | Sign in with `{ email, password }`. Returns `{ token, expires_at, user }`. |
| `POST` | `/auth/signup` | accounts | Create an account when sign-up is allowed. |
| `POST` | `/auth/forgot` | accounts | Email a reset link to `{ email }` if it has an active account. Always `202 { accepted: true }`, sent after responding. |
| `POST` | `/auth/reset` | accounts | Set a new password with `{ token, password }` from a reset link; ends the user's other sessions and signs in. |
| `POST` | `/auth/password` | signed in | Change your password with `{ current_password, new_password }`; your other sessions end. |
| `POST` | `/auth/logout` | — | End the bearer token's session. |
| `GET` · `POST` | `/account/tokens` | signed in | Your API tokens (never the tokens themselves), or create one with `{ name, expires_in_days }` (`null`: never expires): the response holds the token, this once. See [API tokens](#api-tokens). |
| `DELETE` | `/account/tokens/{id}` | signed in | Revoke one of your API tokens. |
| `GET` · `PUT` · `DELETE` | `/account/claude` | signed in | Your saved Claude key: status `{ provider, hint, updated_at }` (never the key), connect or replace with `{ api_key }` (checked with Anthropic first), or disconnect. Needs accounts and `SECRET_KEY`. |
| `GET` | `/admin/overview` | admin | User and scan totals (with the last 7 days), sign-up and email status, recent activity. |
| `GET` | `/admin/activity` | admin | The audit log, newest first: `?limit=` and `?offset=`. Returns `{ items, total }`. |
| `GET` · `POST` | `/admin/users` | admin | The directory (`?query=` searches emails; each user has role, status, scan count, last sign-in), or add a user with `{ email, password, role }`. |
| `GET` · `PATCH` | `/admin/users/{id}` | admin | A user with their recent scans and account history, or change `{ role, status }`. Suspending signs them out. |
| `POST` | `/admin/users/{id}/reset-email` | admin | Email the user a reset link; `409` without SMTP. |
| `POST` | `/admin/users/{id}/reset` | admin | Issue a one-time password reset link, valid 24 hours: `{ path, expires_at }`. Cancels earlier links. |
| `GET` | `/admin/users/{id}/tokens` | admin | A user's API tokens, as they see them. |
| `DELETE` | `/admin/users/{id}/tokens/{token_id}` | admin | Revoke a user's API token. |
| `DELETE` | `/admin/users/{id}` | admin | Remove a user and end their sessions; their scans stay. Not yourself, not the last admin. |
| `POST` | `/scan` | token · rate-limited | Queue a scan of a `target`, or of an `upload` already in the Blob store (hosted). Returns `{ id, status }`. |
| `POST` | `/scan/upload` | token · rate-limited | Queue a scan of a `.zip` or `.md` sent as the multipart `file`, with the options as JSON in `options` (self-hosted). |
| `GET` | `/scan/upload-folder` | token | `{ folder }`: where your Blob uploads go, which the web app hands out upload tokens for (hosted). |
| `GET` | `/scan` | token | Scan history: `?limit=` (1–100, default 20), `?offset=`, `?target=` (one target's scans), `?sort=` (`created_at`, `target`, `risk_score`, `verdict`, `status`) and `?order=` (`asc`, `desc`; newest first by default). Returns `{ items, total }`. |
| `GET` | `/scan/{id}` | token | Status (`pending` · `running` · `done` · `error`), step progress and, once done, the report, with what changed since the target's previous scan (`comparison`). |
| `GET` | `/scan/{id}/export` | token | The finished report as a download: `?format=json` (skillspector's report) or `?format=sarif` (SARIF 2.1.0). |
| `POST` | `/scan/{id}/rescan` | token · rate-limited | Scan the target again as this scan did. |
| `GET` | `/scan/{id}/logs` | token | Captured log lines for a scan (in memory, or in the database with `LOG_STORE=database`). |
| `POST` · `DELETE` | `/scan/{id}/share` | signed in | Share the result at a read-only link (`{ token }`, for `/shared/{token}`), or revoke it. |
| `DELETE` | `/scan/{id}` | signed in | Delete a scan. `204` on success. |
| `POST` · `DELETE` | `/scan/{id}/badge` | signed in | Put the shared result on its target's status badge, or take it off. Refused for an unshared result (`409`), an upload or a scan with a baseline (`422`). Revoking the link takes it off too. |
| `GET` | `/badge` | — | `?target=`: the latest scan of the target on its badge, `{ recommendation, risk_score, scanned_at, share_token }`, all `null` when there's none. The web app renders it as an SVG at `/badge`. |
| `GET` | `/shared/{token}` | — | A shared result, read-only; also `/skills/{index}` and `/export`. |
| `GET` | `/settings` | — | `{ scan_retention_days }` (`null` = keep forever). |
| `PUT` | `/settings` | admin | Update retention; runs a sweep immediately. |
| `POST` | `/admin/claude-login/start` | admin | Start `claude auth login`; returns the URL to open. |
| `POST` | `/admin/claude-login/complete` | admin | Finish the login with `{ code }`. |

**Access** follows `SKILLSPECTOR_WEB_AUTH` (`app/auth/`):

- **`none`:** every request has full access, admin endpoints included, and the `/auth/*` account
  endpoints return `404`.
- **`accounts`:** every scan, settings and admin endpoint needs `Authorization: Bearer <token>`
  from a sign-in (`401` without one). The endpoints marked *token* also take a personal API token
  (see [API tokens](#api-tokens)); every other one refuses it (`403`).
  - Scan endpoints only show a user their own scans, and answer `404` for anyone else's.
  - `admin` endpoints need the admin role (`403`).

The web app keeps the token in an `httpOnly` cookie and adds the header when it proxies a request.
Rate limits answer `429` with a `Retry-After` header and a message saying when to try again:

- `POST /scan`: per signed-in user (`SCAN_RATE_LIMIT`, or per client IP with `AUTH=none`), plus a
  per-IP cap across every account signed in from one address (`SCAN_IP_RATE_LIMIT`).
- Sign-in, setup, sign-up, password reset and password change: per client IP (`LOGIN_RATE_LIMIT`).

The client IP is the `X-Forwarded-For` value the web proxy sets.

### Starting a scan

```http
POST /scan
Content-Type: application/json

{
  "target": "https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md",
  "llm": { "provider": "anthropic", "api_key": "sk-ant-…", "model": null, "base_url": null }
}
```

- `target` — an `https://` URL of a repository or file on a host skillspector accepts (GitHub,
  GitLab, Bitbucket, Hugging Face, raw.githubusercontent.com). Local paths are rejected.
- `llm` — optional; omit or `null` for a static scan. `provider` is `anthropic`, `openai`,
  `ollama` or `claude_cli`. `api_key` is required for `anthropic` and `openai`; `claude_cli` uses
  the server's own login. The key is used for this scan only and never stored.

| Status | Meaning |
|---|---|
| `200` | Queued — poll `GET /scan/{id}`. |
| `422` | Invalid body, e.g. a non-http(s) target or a hosted provider without a key. |
| `429` | Rate limit exceeded for this client. |
| `503` | The queue is full (`SKILLSPECTOR_WEB_MAX_QUEUED_SCANS`). |

The finished report is skillspector's JSON report (`risk_assessment`, `issues`, `metadata`, …).

### API tokens

Scripts and CI jobs authenticate with a personal API token instead of a browser session (with
`AUTH=accounts`; without accounts, no token is needed). Create one on the **Account** page, or with
`POST /account/tokens` from a session: it's shown once, and only its hash is stored. A token:

- acts as the user who made it: the same scans, quotas and rate limits. It stops working when it's
  revoked, when it expires, or when its owner is suspended or deleted: `401`.
- has the `scan` scope: it starts scans, and reads, exports and rescans them (the endpoints marked
  *token* above). Everything else, deleting or sharing a scan included, needs a session (`403`).
- is recorded in the activity log when it's created, revoked, and first used each day. Admins see
  and revoke any user's tokens from the user's page.

Start a scan, then poll it until it's done:

```bash
export SKILLSPECTOR_TOKEN=sst_…            # from the Account page
API=https://skillspector.example.com/api  # the web app proxies /api/* to this service

id=$(curl -fsS -X POST "$API/scan" \
  -H "Authorization: Bearer $SKILLSPECTOR_TOKEN" -H "Content-Type: application/json" \
  -d '{"target": "https://github.com/anthropics/skills/tree/main/skills/pdf"}' | jq -r .id)

until status=$(curl -fsS "$API/scan/$id" -H "Authorization: Bearer $SKILLSPECTOR_TOKEN" | jq -r .status);
      [ "$status" = done ] || [ "$status" = error ]; do sleep 5; done

curl -fsS "$API/scan/$id" -H "Authorization: Bearer $SKILLSPECTOR_TOKEN" \
  | jq '.result.risk_assessment'                      # { score, severity, recommendation }
curl -fsS "$API/scan/$id/export?format=sarif" -H "Authorization: Bearer $SKILLSPECTOR_TOKEN" -o skillspector.sarif
```

The recommendation is `SAFE`, `CAUTION` or `DO_NOT_INSTALL`, so a CI job can fail on, say,
`DO_NOT_INSTALL`; the SARIF file can be uploaded to GitHub code scanning.

## Behaviour worth knowing

- **Deployment mode.** `SKILLSPECTOR_WEB_MODE` is `self_hosted` by default, which is everything
  described here. `hosted` (Vercel) swaps in the hosted piece of each part below, and refuses to
  start while a setting it needs is missing, listing each one.
- **File links.** skillspector downloads a single-file link as is, so a code host's file view
  (GitHub's `/blob/`) would be scanned as the page's HTML. `POST /scan` rewrites these links to the
  raw file first (`app/targets.py`), and stores the rewritten target:
  - GitHub `/blob/` and `/raw/` become `raw.githubusercontent.com`.
  - GitLab `/-/blob/` becomes `/-/raw/`.
  - Hugging Face `/blob/` becomes `/resolve/`.
- **Storage.** `app/db.py` is the only module the app calls; it delegates to a SQLite or Postgres
  store (`app/storage/`). Each store applies its versioned migrations on startup and records them in
  `schema_migrations`; existing SQLite databases are adopted as they are. Scans aren't copied
  between engines when you switch.
- **Job runners.** `app/jobs/` picks how scans run (`SKILLSPECTOR_WEB_JOB_RUNNER`, defaulting by
  mode). Both call `scanner.run_job()`, which records the outcome on the scan.
  - `in_process` (self-hosted): asyncio tasks in the API process, as described below.
  - `vercel_queues` (hosted): `POST /scan` publishes `{scan_id}` to the `scans` topic, with the scan
    id as idempotency key. The `@subscribe` handler in `app/jobs/queue_worker.py`, registered under
    `[[tool.vercel.subscribers]]` in `pyproject.toml`, runs it. Delivery is at least once, so the
    handler skips scans that already finished and marks a scan failed after 3 deliveries that
    never completed. The queue limit counts pending and running scans in the database. Messages
    never carry API keys, so AI review is rejected in this runner until per-user keys land (#46).
- **Sandboxed scans.** With `SKILLSPECTOR_WEB_SCAN_EXECUTOR=sandbox` (the hosted default),
  `app/sandbox_executor.py` runs each scan in a fresh, non-persistent Vercel Sandbox instead of this
  process:
  - The VM boots from a snapshot with skillspector preinstalled: the one recorded in
    `app/sandbox_snapshot_record.py`, or `SKILLSPECTOR_WEB_SANDBOX_SNAPSHOT_ID` when there's no
    record. `uv run python -m app.sandbox_snapshot` builds one from the version pinned in
    `pyproject.toml` and records it; the Sandbox snapshot workflow does it when a pull request
    changes the pin. A scan logs a warning if the snapshot's skillspector differs from the API's.
  - The API uploads `app/sandbox_runner.py`, a standalone script, and runs it on the target. The
    script reports each finished step, log record and the final report as tagged JSON lines, which
    the API relays into the scan's log and progress as they arrive.
  - Outbound traffic is limited to the code hosts in `SCAN_HOSTS` (TLS, matched on SNI), with
    private, loopback, link-local and CGNAT ranges denied. No environment variables or
    credentials from the app are passed in.
  - The scan is killed after `SKILLSPECTOR_WEB_SANDBOX_TIMEOUT_SECONDS` and fails with a clear
    message; the VM is destroyed when the scan ends either way.
  - AI review isn't supported in the sandbox yet: #46 will broker the user's provider key at the
    sandbox firewall so it never enters the VM.
- **Saved Claude keys** (`app/claude_key.py`, `app/secrets_box.py`). A scan request with
  `"llm": { "provider": "anthropic", "use_saved_key": true }` uses the key saved to the user's
  account. Where the key comes from depends on the runner:
  - In-process runner: the key is decrypted when the scan is queued and held in memory for it.
  - Queue runner: messages still carry only the scan id. The worker decrypts the user's saved key,
    or the one-off key held encrypted in `scan_secrets`, when the scan runs, and deletes the held
    key afterwards.
  - Sandbox executor: skillspector in the VM gets a placeholder key. The sandbox firewall adds the
    real one as `x-api-key` on requests to `api.anthropic.com`, the only extra host allowed.
- **Concurrency.** Up to `SKILLSPECTOR_WEB_MAX_CONCURRENT_SCANS` scans run at once, each in a
  worker thread. Scans with AI analysis are additionally serialised, because the provider's
  credentials are passed to skillspector through process environment variables.
- **Restarts.** With the in-process runner, on startup any scan left `pending` or `running` is marked
  failed with an "interrupted" message.
- **Logs.** `SKILLSPECTOR_WEB_LOG_STORE` picks where log lines and step progress go (`app/scan_logs.py`):
  - `memory` (self-hosted default): the last 500 lines of each of the 50 most recent scans, lost on
    restart.
  - `database` (hosted default): the last 500 lines per scan in `scan_log_lines` and the step count
    on the scan, so any instance can serve a scan another one is running. Lines are deleted with
    their scan, including by the retention sweep.
  - A scan that runs again (a queue redelivery) starts its log and progress afresh.
- **Rate limits.** `SKILLSPECTOR_WEB_RATE_LIMIT_STORE` picks where hits are counted (`app/rate_limit.py`),
  as sliding windows:
  - `memory` (self-hosted default): in this process, for the 1000 most recently seen clients.
  - `database` (hosted default): in `rate_limit_hits`, so every instance counts the same hits. On
    Postgres each check holds an advisory lock on its key, so concurrent requests can't both take
    the last slot. Expired hits are deleted as new ones come in.
  - A refused request isn't counted, so retrying too early doesn't push the limit further out.
- **Quotas and pausing** (`app/quotas.py`), checked by `POST /scan`:
  - A paused server refuses every new scan with `503`, admins' included.
  - Signed-in users other than admins are limited per rolling 24 hours and in progress at once;
    either refusal is a `429`. The quota check runs last, so a scan refused for another reason
    doesn't count.
  - Daily scans are counted in `rate_limit_hits` whatever the rate-limit store, so the count
    survives restarts and deleting a scan doesn't give it back. The in-progress limit counts the
    user's pending and running scans. It isn't locked, so two requests sent at the same instant can
    both pass it; the per-minute rate limit bounds that.
  - Limits come from `app_settings` once an admin saves them (`PUT /settings`), otherwise from
    `DAILY_SCAN_QUOTA` and `CONCURRENT_SCAN_QUOTA`, otherwise from the mode. `GET /account/usage`
    reports them to the user with their counts.
- **Retention.** The sweep deletes finished scans older than the configured number of days, with
  their log lines and held keys; scans still in progress are never swept. Changing the retention
  sweeps straight away.
  - Self-hosted: a background task in the API process sweeps every hour.
  - Hosted: no process lives that long, so there is no background task. Vercel Cron calls
    `GET /api/internal/retention` on the web app daily (`vercel.ts` at the repository root), which
    forwards to `POST /internal/retention` here. That endpoint answers `401` unless the request
    carries `Authorization: Bearer $CRON_SECRET`, as Vercel Cron's do, and `404` while
    `CRON_SECRET` is unset.

Configuration options are listed in the [configuration reference](../docs/CONFIGURATION.md).

## Development

```bash
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000, docs at /docs
uv run pytest                          # add TEST_DATABASE_URL=postgresql://… to also test Postgres
uv run ruff check .
```

Settings are read from the environment, then `backend/.env.local`, then `backend/.env`.
