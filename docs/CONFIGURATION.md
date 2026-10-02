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
| `SECRET_KEY` | *unset* | Encrypts the Claude keys users save to their account (AES-256-GCM). Generate one with `uv run python -m app.secrets_box`. Without it, users paste a key per scan, and an AI scan with a pasted key can't be run again if the API restarts mid-scan. Required in hosted mode. Keep it: if it changes, saved keys can't be decrypted and users have to connect again. |
| `MAIL_FROM` | *unset* | Sender of those emails, e.g. `Skillspector <noreply@example.com>`. |
| `PUBLIC_URL` | *unset* | This app's public address, e.g. `https://skillspector.example.com`, used for links in emails. Email features switch on when `SMTP_HOST`, `MAIL_FROM` and `PUBLIC_URL` are all set. |
| `ALERT_WEBHOOK_URL` | *unset* | Where to POST alerts: a Slack or Discord incoming webhook, or any endpoint taking JSON. See [Monitoring](./MONITORING.md). |
| `ALERT_EMAIL` | *unset* | Addresses to email alerts to, comma-separated. Needs email set up (above). |
| `JOB_RUNNER` | *by mode* | How scans run: `in_process` (the `self_hosted` default: tasks inside the API) or `vercel_queues` (the `hosted` default: a durable Vercel Queues topic consumed by a queue-triggered function). |
| `LOG_STORE` | *by mode* | Where live scan logs and step progress go: `memory` (the `self_hosted` default; lost on restart) or `database` (the `hosted` default; the scan database, so logs survive restarts and are shared between instances). |
| `RATE_LIMIT_STORE` | *by mode* | Where rate limits count requests: `memory` (the `self_hosted` default: this process only) or `database` (the `hosted` default: the scan database, so every instance enforces the same limits). |
| `SCAN_EXECUTOR` | *by mode* | Where a scan's fetch and analysis happen: `local` (the `self_hosted` default: inside the API) or `sandbox` (the `hosted` default: a fresh Vercel Sandbox microVM per scan). |
| `UPLOAD_STORE` | *by mode* | Where a skill uploaded from the browser is held until its scan ends: `local` (the `self_hosted` default: under `data/uploads/`, sent to the API with the scan) or `blob` (the `hosted` default: a private Vercel Blob store the browser uploads to directly, which needs `BLOB_READ_WRITE_TOKEN`; uploads are off without it). Either way the file is deleted once scanned, whatever the outcome. Uploads are a `.zip` of the skill, or a `.md` file on its own, up to 25 MB. |
| `SANDBOX_SNAPSHOT_ID` | *unset* | Snapshot sandboxed scans boot from, with skillspector preinstalled, when `backend/app/sandbox_snapshot_record.py` records none. `uv run python -m app.sandbox_snapshot` builds one and records it (needs Vercel credentials). Sandboxed scans need one or the other. |
| `SANDBOX_VCPUS`<br>`SANDBOX_TIMEOUT_SECONDS` | `2`<br>`240` | vCPUs per scan sandbox, and how long a sandboxed scan may run before it's stopped and reported as timed out. skillspector's own analysis deadline is set 30 seconds shorter, so a slow scan ends with a partial report instead of being stopped. |
| `MAX_CONCURRENT_SCANS` | `2` | Scans running at once. Scans with AI analysis also run one at a time. |
| `MAX_QUEUED_SCANS` | `20` | Running + waiting scans; beyond this, new scans get `503`. |
| `TRANSITIVE_MAX_DEPTH` | `2` | How many levels of a skill's external references a scan may follow ("Follow external references" on the scan form), up to 5; `0` turns the option off. skillspector only follows Git repositories and raw files on the code hosts it can fetch from, never `/blob/` or `/tree/` web pages. Scans that follow references run through skillspector's CLI, and don't offer a baseline download. |
| `TRANSITIVE_ALLOW_PREFIXES`<br>`TRANSITIVE_DENY_PREFIXES` | *empty* | JSON lists of URL prefixes, e.g. `["https://github.com/acme"]`: only follow references matching one of the first, and never those matching the second. An invalid prefix stops the API from starting. |
| `SCAN_RATE_LIMIT`<br>`SCAN_RATE_LIMIT_WINDOW_SECONDS` | `5`<br>`60` | Scans allowed per signed-in user (per client IP with `AUTH=none`) within the window. |
| `SCAN_IP_RATE_LIMIT` | `20` | Scans allowed per client IP within the same window, however many accounts sign in from it. |
| `DAILY_SCAN_QUOTA`<br>`CONCURRENT_SCAN_QUOTA` | *by mode* | With accounts, how many scans each user other than an admin may start per rolling 24 hours, and have in progress at once. `0` means no limit. Unset means no limits `self_hosted`, and 10 a day and 2 at once `hosted`. Admins change both from the backoffice, which takes precedence, and can pause new scans there too. A user's own quotas, set on their page in the backoffice, take precedence over all of these. |
| `LOGIN_RATE_LIMIT`<br>`LOGIN_RATE_LIMIT_WINDOW_SECONDS` | `10`<br>`300` | Sign-in, first-run setup and sign-up attempts allowed per client IP within the window. |
| `SCAN_RETENTION_DAYS` | *unset* | Retention when the database is first created (unset keeps scans forever). Change it later from the admin page. |
| `CRON_SECRET` (no prefix) | *unset* | Hosted only, and required there: Vercel's own variable, which Vercel Cron sends when it calls the daily retention sweep (`vercel.ts`). The sweep endpoint refuses callers without it, and doesn't exist while it's unset. Self-hosted servers sweep hourly in the background instead. Generate one with `openssl rand -hex 32`, and set it for the web app too. |
| `DATABASE_URL` | *unset* | A `postgres://` or `postgresql://` URL stores scans in Postgres instead of SQLite. Required in hosted mode. The schema is created and migrated on startup. |
| `DB_PATH` | `data/scans.db` | SQLite file, relative to `backend/`, used when `DATABASE_URL` is unset. |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Origins allowed to call the API directly. The UI goes through its own proxy, so this rarely matters. |

## Analysis (skillspector)

These tune skillspector itself, for every scan, whether it runs inside the API (`local`) or in a
scan sandbox. Each sets the skillspector variable named; only these are passed on, never the rest
of the API's environment. Unset keeps skillspector's own default, given here for the pinned
version (2.12.0). They're also prefixed `SKILLSPECTOR_WEB_`, and a value skillspector would refuse
or silently ignore stops the API from starting instead.

| Variable | skillspector variable | skillspector's default | Description |
|---|---|---|---|
| `YARA_RULES_DIR` | `--yara-rules-dir` | *none* | A directory of extra YARA rules (`.yar`, `.yara`, or base64-encoded `.yar.b64` and `.yara.b64`, in subfolders too), loaded alongside skillspector's own. A rule's `category` meta (`malware`, `webshell`, `cryptominer`, `hack_tool`, `exploit`) sets its finding's rule and severity; without one, a match is a medium `YR4`, and a `severity` meta overrides the severity. Relative to `backend/`. The rules are read when the API starts and uploaded with every sandboxed scan, so the snapshot never needs rebuilding for them. With Docker Compose, mount the directory into the `api` container; on Vercel, commit it under `backend/`. |
| `OUTPUT_LANGUAGE` | `SKILLSPECTOR_OUTPUT_LANGUAGE` | *none*: the model answers its English prompts in English | The language AI review writes its explanations and remediations in, e.g. `French`: up to 64 letters, digits, spaces, `-` or `_`. Rule names, severities and the report's structure stay as they are. |
| `REASONING_EFFORT` | `SKILLSPECTOR_REASONING_EFFORT` | the model's | Reasoning effort for AI review, e.g. `low` or `high`, passed to the provider as is: which values work depends on the provider and model. |
| `TEMPERATURE` | `SKILLSPECTOR_TEMPERATURE` | the model's | Sampling temperature for AI review, from `0` to `1`. |
| `MAX_LLM_CONCURRENCY` | `SKILLSPECTOR_MAX_LLM_CONCURRENCY` | `10` | AI review requests in flight at once, per scan. Lower it for a provider plan with tight rate limits. |
| `OSV_TIMEOUT_SECONDS` | `SKILLSPECTOR_OSV_TIMEOUT` | `30` | How long to wait for [OSV.dev](https://osv.dev) when checking a skill's dependencies for known vulnerabilities, before falling back to skillspector's built-in list. Scan sandboxes can't reach OSV.dev, so sandboxed scans always use that list. |
| `MAX_WORKFLOW_SECONDS` | `SKILLSPECTOR_MAX_WORKFLOW_SECONDS` | `600` | How long a scan's analysis may take before skillspector stops and reports what it inspected so far. A repository holding several skills shares it between them. In the sandbox it never exceeds `SANDBOX_TIMEOUT_SECONDS` minus 30 seconds, which is also its value there when unset. |
| `MAX_STATIC_ANALYSIS_SECONDS_PER_ARTIFACT` | `SKILLSPECTOR_MAX_STATIC_ANALYSIS_SECONDS_PER_ARTIFACT` | `300` | How long the static analyzers may spend on any one file before moving on and marking it partly inspected. |

## Web app (`web`)

| Variable | Default | Description |
|---|---|---|
| `NUXT_API_BASE` | `http://localhost:8000` | Where the Nitro proxy reaches the API (`http://api:8000` in Compose; set by the service binding on Vercel). |
| `NUXT_TRUST_PROXY` | `false` | Set to `true` behind a reverse proxy so rate limits use the client IP it appends to `X-Forwarded-For`. |
| `NUXT_PUBLIC_BOTID` | `false` | Hosted on Vercel only: `true` turns on [BotID](https://vercel.com/docs/botid) for scan submissions, refusing ones it classifies as bots (`403`). Read at build time too. |
| `NUXT_PUBLIC_ANALYTICS` | `false` | Hosted on Vercel only: `true` builds in [Vercel Web Analytics](https://vercel.com/docs/analytics). Read at build time only: without it the build holds none of it, and pages make no request to Vercel. See [what it records](./SECURITY_MODEL.md#web-analytics). |
| `NUXT_PUBLIC_SPEED_INSIGHTS` | `false` | Hosted on Vercel only: `true` builds in [Vercel Speed Insights](https://vercel.com/docs/speed-insights), Core Web Vitals from real visits. Read at build time only, like `NUXT_PUBLIC_ANALYTICS`. |
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
