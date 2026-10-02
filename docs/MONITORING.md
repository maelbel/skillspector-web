# Monitoring

Skillspector Web watches its own scans, self-hosted and hosted alike. When scans start failing,
can't run their sandbox, or every submission is refused, it says so three ways:

- **The backoffice's health panel** (Overview): the last 24 hours' failed scans and sandbox errors,
  queue redeliveries and refused submissions when there are any, the last error with a link to its
  scan, and where alerts go.
- **The Monitoring page** (Backoffice → Monitoring): the same counts over 24 hours, 7 or 30 days;
  each alert rule with what trips it, where it stands now, when it last alerted and how long it
  stays quiet; where alerts go, with a test; and every event kept, filterable by kind.
- **Alerts**, to a webhook (Slack, Discord or anything taking JSON) and/or by email, as it happens.
- **Structured logs**: one JSON line per event on stdout, for `docker compose logs`, Vercel's logs,
  or a log drain to your own alerting.

## Setting up alerts

Set one or both, on the API (`api` service):

| Variable | What it does |
|---|---|
| `SKILLSPECTOR_WEB_ALERT_WEBHOOK_URL` | POSTs each alert as JSON. A Slack or Discord incoming webhook works as is. |
| `SKILLSPECTOR_WEB_ALERT_EMAIL` | Emails each alert to these addresses, comma-separated. Needs [email](./CONFIGURATION.md) set up. |

Set `SKILLSPECTOR_WEB_PUBLIC_URL` too, so alerts link to the backoffice. Then open **Backoffice** →
**Monitoring** and use **Send a test alert** to check they arrive.

The webhook's body has `text` (Slack), `content` (Discord), and `title`, `message` and `link` for
anything else.

## What raises an alert

| Alert | When | Then waits |
|---|---|---|
| Scans can't start their sandbox | Any scan fails because of its sandbox rather than its skill: no snapshot, a deleted one, or the platform refusing or losing the VM (hosted). | 30 minutes |
| Many scans are failing | In the last 30 minutes, at least 3 scans failed, and at least half of those that finished. | 1 hour |
| Scans are being redelivered by the queue | The scan queue delivered 3 or more messages again in 30 minutes: scans are stopped before they finish (hosted). | 1 hour |
| Every scan submission is being refused as a bot | BotID refused 10 or more submissions in 15 minutes and no scan started: real visitors are refused too, the sign of a BotID misconfiguration (hosted). | 1 hour |

An alert isn't repeated within its wait, however many times it trips. A broken snapshot raises one
on the first scan that hits it.

**What an alert carries:** what went wrong, and counts. Messages are scrubbed of API keys, tokens,
passwords and email addresses, and URLs are cut to their host, so an alert never names a scan's
target, a user, or a key.

On the hosted version, alerts are sent from whichever function saw the event. Two instances can
now and then both send the same alert.

## Structured log events

Each line is a JSON object with `event`, `at` (Unix time) and the fields below. None holds user data.

| `event` | Fields |
|---|---|
| `skillspector.scan_started` | `scan_id`, `ai_review` |
| `skillspector.scan_finished` | `scan_id`, `duration_seconds`, `recommendation` |
| `skillspector.scan_failed` | `scan_id`, `reason` (`scan`, `sandbox`, `queue` or `restart`), `message`, `duration_seconds` |
| `skillspector.scan_interrupted` | `scan_id`: the API stopped mid-scan, which runs again on startup |
| `skillspector.scans_resumed` | `count`: scans a self-hosted API picked back up on startup |
| `skillspector.sandbox_error` | `scan_id`, `message` |
| `skillspector.queue_redelivered` | `scan_id`, `delivery` |
| `skillspector.bot_refused` | `path` from the web app; `count` from the API |
| `skillspector.alert` | `title`, `channels` it reached |

Failures, sandbox errors, redeliveries and refusals are also stored for the health panel, and kept
30 days.

## On Vercel

The built-in alerts above work on every plan. Vercel's own [alerts](https://vercel.com/docs/alerts)
(Pro and Enterprise, with Observability Plus) add anomaly detection on top: an **error anomaly**
alert on the project catches a spike of 5xx responses, and one configured for 4xx
on `/api/scan` catches BotID refusing submissions. They need enough traffic to pass Vercel's
minimum activity checks, which a quiet server may not, so keep the built-in ones on.

To route the structured events to another tool (Datadog, Better Stack, Grafana…), add a
[log drain](https://vercel.com/docs/drains) (Pro and Enterprise) and alert on the `event` field
there.
