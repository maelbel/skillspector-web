# Skillspector Web — scan service

The FastAPI service behind [Skillspector Web](../README.md). It imports
[skillspector](https://github.com/NVIDIA/skillspector) as a library and streams its compiled
LangGraph pipeline (`skillspector.graph.graph`) for each scan — no CLI subprocess, no output
parsing. Scan history and settings are stored in SQLite; progress and logs are captured live.

The service is meant to sit on an internal network behind the web app's Nitro proxy
(`server/api/*`), which maps `/api/<path>` to `/<path>` here. Interactive OpenAPI docs are served at
`/docs` on the service itself.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Service status, skillspector version, and whether the server's Claude login is usable. |
| `POST` | `/scan` | rate-limited | Queue a scan. Returns `{ id, status }`. |
| `GET` | `/scan` | — | Scan history, newest first: `?limit=` (1–100, default 20) and `?offset=`. Returns `{ items, total }`. |
| `GET` | `/scan/{id}` | — | Status (`pending` · `running` · `done` · `error`), step progress and, once done, the report. |
| `GET` | `/scan/{id}/logs` | — | Captured log lines for a recent scan (kept in memory). |
| `DELETE` | `/scan/{id}` | — | Delete a scan. `204` on success. |
| `GET` | `/settings` | — | `{ scan_retention_days }` (`null` = keep forever). |
| `PUT` | `/settings` | admin | Update retention; runs a sweep immediately. |
| `POST` | `/admin/claude-login/start` | admin | Start `claude auth login`; returns the URL to open. |
| `POST` | `/admin/claude-login/complete` | admin | Finish the login with `{ code }`. |

**Admin** endpoints need an `X-Admin-Token` header matching `SKILLSPECTOR_WEB_ADMIN_TOKEN`; with no
token configured they return `404`. Admin attempts and scan submissions are rate-limited per
client IP (`429`), keyed on the `X-Forwarded-For` value the web proxy sets.

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

- **Concurrency.** Up to `SKILLSPECTOR_WEB_MAX_CONCURRENT_SCANS` scans run at once, each in a
  worker thread. Scans with AI analysis are additionally serialised, because the provider's
  credentials are passed to skillspector through process environment variables.
- **Restarts.** Jobs run in-process. On startup, any scan left `pending` or `running` is marked
  failed with an "interrupted" message.
- **Logs.** The last 500 lines of each of the 50 most recent scans are kept in memory.
- **Retention.** An hourly sweep deletes finished scans older than the configured number of days;
  scans still in progress are never swept.

Configuration options are listed in the [main README](../README.md#configuration).

## Development

```bash
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000, docs at /docs
uv run pytest
uv run ruff check .
```

Settings are read from the environment, then `backend/.env.local`, then `backend/.env`.
