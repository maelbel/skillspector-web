# Configuration

Skillspector Web is configured with environment variables. `pnpm setup` writes the common ones to
`backend/.env.local` (see [`backend/.env.example`](../backend/.env.example)). Environment
variables always win over that file.

For the hosted (Vercel) deployment, [VERCEL.md](./VERCEL.md) lists which of these to set, and in
which environments.

## Scan service (`api`)

Every variable is prefixed with `SKILLSPECTOR_WEB_` — for example `SKILLSPECTOR_WEB_AUTH`.

| Variable | Default | Description |
|---|---|---|
| `MODE` | `self_hosted` | Deployment mode: `self_hosted` (one server, as documented here) or `hosted` (Vercel). `hosted` refuses to start while a setting it needs is missing, and names it; see [VERCEL.md](./VERCEL.md). |
| `AUTH` | *by mode* | Who can use the server: `none` (the `self_hosted` default: no sign-in, every visitor has full access, admin page included) or `accounts` (sign-in required; the first account becomes the admin, users see only their own scans, admins see all and manage the server). Always `accounts` when hosted. |
| `ALLOW_SIGNUP` | *unset* | With accounts, whether visitors may create their own account from the landing page. Unset allows it; admins can also turn it on and off in the backoffice, which takes precedence. The very first account is always the admin. |
| `SESSION_DAYS` | `30` | How long a sign-in lasts. |
| `SMTP_HOST`<br>`SMTP_PORT`<br>`SMTP_USERNAME`<br>`SMTP_PASSWORD`<br>`SMTP_SECURITY` | *unset*<br>`587`<br>*unset*<br>*unset*<br>`starttls` | SMTP server for password reset emails: any provider works (your own, your mailbox provider's, or a sending service such as Resend). `SMTP_SECURITY` is `starttls` (port 587), `ssl` (465) or `none` (a local relay only). |
| `SECRET_KEY` | *unset* | Encrypts the Claude keys users save to their account (AES-256-GCM). Generate one with `uv run python -m app.secrets_box`. Without it, users paste a key per scan. Required in hosted mode. Keep it: if it changes, saved keys can't be decrypted and users have to connect again. |
| `MAIL_FROM` | *unset* | Sender of those emails, e.g. `Skillspector <noreply@example.com>`. |
| `PUBLIC_URL` | *unset* | This app's public address, e.g. `https://skillspector.example.com`, used for links in emails. Email features switch on when `SMTP_HOST`, `MAIL_FROM` and `PUBLIC_URL` are all set. |
| `JOB_RUNNER` | *by mode* | How scans run: `in_process` (the `self_hosted` default: tasks inside the API) or `vercel_queues` (the `hosted` default: a durable Vercel Queues topic consumed by a queue-triggered function). |
| `LOG_STORE` | *by mode* | Where live scan logs and step progress go: `memory` (the `self_hosted` default; lost on restart) or `database` (the `hosted` default; the scan database, so logs survive restarts and are shared between instances). |
| `RATE_LIMIT_STORE` | *by mode* | Where rate limits count requests: `memory` (the `self_hosted` default: this process only) or `database` (the `hosted` default: the scan database, so every instance enforces the same limits). |
| `SCAN_EXECUTOR` | *by mode* | Where a scan's fetch and analysis happen: `local` (the `self_hosted` default: inside the API) or `sandbox` (the `hosted` default: a fresh Vercel Sandbox microVM per scan). |
| `SANDBOX_SNAPSHOT_ID` | *unset* | Snapshot sandboxed scans boot from, with skillspector preinstalled. Build it with `uv run python -m app.sandbox_snapshot` (needs Vercel credentials). Required with `SCAN_EXECUTOR=sandbox`. |
| `SANDBOX_VCPUS`<br>`SANDBOX_TIMEOUT_SECONDS` | `2`<br>`240` | vCPUs per scan sandbox, and how long a sandboxed scan may run before it's stopped and reported as timed out. |
| `MAX_CONCURRENT_SCANS` | `2` | Scans running at once. Scans with AI analysis also run one at a time. |
| `MAX_QUEUED_SCANS` | `20` | Running + waiting scans; beyond this, new scans get `503`. |
| `SCAN_RATE_LIMIT`<br>`SCAN_RATE_LIMIT_WINDOW_SECONDS` | `5`<br>`60` | Scans allowed per signed-in user (per client IP with `AUTH=none`) within the window. |
| `SCAN_IP_RATE_LIMIT` | `20` | Scans allowed per client IP within the same window, however many accounts sign in from it. |
| `DAILY_SCAN_QUOTA`<br>`CONCURRENT_SCAN_QUOTA` | *by mode* | With accounts, how many scans each user other than an admin may start per rolling 24 hours, and have in progress at once. `0` means no limit. Unset means no limits `self_hosted`, and 10 a day and 2 at once `hosted`. Admins change both from the backoffice, which takes precedence, and can pause new scans there too. |
| `LOGIN_RATE_LIMIT`<br>`LOGIN_RATE_LIMIT_WINDOW_SECONDS` | `10`<br>`300` | Sign-in, first-run setup and sign-up attempts allowed per client IP within the window. |
| `SCAN_RETENTION_DAYS` | *unset* | Retention when the database is first created (unset keeps scans forever). Change it later from the admin page. |
| `CRON_SECRET` (no prefix) | *unset* | Hosted only, and required there: Vercel's own variable, which Vercel Cron sends when it calls the daily retention sweep (`vercel.ts`). The sweep endpoint refuses callers without it, and doesn't exist while it's unset. Self-hosted servers sweep hourly in the background instead. Generate one with `openssl rand -hex 32`, and set it for the web app too. |
| `DATABASE_URL` | *unset* | A `postgres://` or `postgresql://` URL stores scans in Postgres instead of SQLite. Required in hosted mode. The schema is created and migrated on startup. |
| `DB_PATH` | `data/scans.db` | SQLite file, relative to `backend/`, used when `DATABASE_URL` is unset. |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Origins allowed to call the API directly. The UI goes through its own proxy, so this rarely matters. |

## Web app (`web`)

| Variable | Default | Description |
|---|---|---|
| `NUXT_API_BASE` | `http://localhost:8000` | Where the Nitro proxy reaches the API (`http://api:8000` in Compose; set by the service binding on Vercel). |
| `NUXT_TRUST_PROXY` | `false` | Set to `true` behind a reverse proxy so rate limits use the client IP it appends to `X-Forwarded-For`. |
| `NUXT_PUBLIC_BOTID` | `false` | Hosted on Vercel only: `true` turns on [BotID](https://vercel.com/docs/botid) for scan submissions, refusing ones it classifies as bots (`403`). Read at build time too. |
| `NUXT_ALLOWED_HOST` | *unset* | Public hostname allowed by the development server (`nuxt dev`) only. |

## AI analysis

Deep analysis is chosen per scan in the form — no server setup is needed for the bring-your-own-key
providers.

| Provider | What the visitor supplies | Where the skill's content is sent |
|---|---|---|
| Claude via this server | nothing | Anthropic, through the server's `claude` CLI login |
| Anthropic | API key | Anthropic, or the base URL provided |
| OpenAI | API key | OpenAI, or any OpenAI-compatible base URL |
| Ollama | base URL | That Ollama server |

To enable the server's Claude login, sign in once — from the admin page, or from a terminal:

```bash
docker exec -it skillspector-api claude auth login
```

The login is stored in the `claude_cli_auth` volume and survives rebuilds. Every visitor's
Claude-backed scans share it — see the [security model](./SECURITY_MODEL.md).
