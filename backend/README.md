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
| `POST` | `/auth/reset` | accounts | Set a new password with `{ token, password }` from a reset link; ends the user's other sessions and signs in. |
| `POST` | `/auth/password` | signed in | Change your password with `{ current_password, new_password }`; your other sessions end. |
| `POST` | `/auth/logout` | — | End the bearer token's session. |
| `GET` · `POST` | `/admin/users` | admin | List users, or add one with `{ email, password, role }`. |
| `POST` | `/admin/users/{id}/reset` | admin | Issue a one-time password reset link, valid 24 hours: `{ path, expires_at }`. Cancels earlier links. |
| `DELETE` | `/admin/users/{id}` | admin | Remove a user and end their sessions; their scans stay. Not yourself, not the last admin. |
| `POST` | `/scan` | rate-limited | Queue a scan. Returns `{ id, status }`. |
| `GET` | `/scan` | — | Scan history, newest first: `?limit=` (1–100, default 20) and `?offset=`. Returns `{ items, total }`. |
| `GET` | `/scan/{id}` | — | Status (`pending` · `running` · `done` · `error`), step progress and, once done, the report. |
| `GET` | `/scan/{id}/logs` | — | Captured log lines for a scan (in memory, or in the database with `LOG_STORE=database`). |
| `DELETE` | `/scan/{id}` | — | Delete a scan. `204` on success. |
| `GET` | `/settings` | — | `{ scan_retention_days }` (`null` = keep forever). |
| `PUT` | `/settings` | admin | Update retention; runs a sweep immediately. |
| `POST` | `/admin/claude-login/start` | admin | Start `claude auth login`; returns the URL to open. |
| `POST` | `/admin/claude-login/complete` | admin | Finish the login with `{ code }`. |

**Access** follows `SKILLSPECTOR_WEB_AUTH` (`app/auth/`):

- **`none`:** every request has full access, admin endpoints included, and the `/auth/*` account
  endpoints return `404`.
- **`accounts`:** every scan, settings and admin endpoint needs `Authorization: Bearer <token>`
  from a sign-in (`401` without one).
  - Scan endpoints only show a user their own scans, and answer `404` for anyone else's.
  - `admin` endpoints need the admin role (`403`).

The web app keeps the token in an `httpOnly` cookie and adds the header when it proxies a request.
Sign-in attempts and scan submissions are rate-limited per client IP (`429`), keyed on the
`X-Forwarded-For` value the web proxy sets.

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

## Behaviour worth knowing

- **Deployment mode.** `SKILLSPECTOR_WEB_MODE` is `self_hosted` by default, which is everything
  described here. `hosted` (Vercel) is being built piece by piece; until every piece exists, the
  service refuses to start in that mode and lists what's missing.
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
  - The VM boots from `SKILLSPECTOR_WEB_SANDBOX_SNAPSHOT_ID`, which has skillspector preinstalled.
    `uv run python -m app.sandbox_snapshot` builds it from the version pinned in `pyproject.toml`
    and prints the ID. A scan logs a warning if the snapshot's skillspector differs from the API's.
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
- **Retention.** An hourly sweep deletes finished scans older than the configured number of days;
  scans still in progress are never swept.

Configuration options are listed in the [main README](../README.md#configuration).

## Development

```bash
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000, docs at /docs
uv run pytest                          # add TEST_DATABASE_URL=postgresql://… to also test Postgres
uv run ruff check .
```

Settings are read from the environment, then `backend/.env.local`, then `backend/.env`.
