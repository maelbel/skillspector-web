"""Monitoring: what's going wrong, in the logs, the backoffice, and alerts.

Each event is written three ways:

- a structured log line (JSON, `"event": "skillspector.<kind>"`) on stdout, for Vercel's log
  alerts, a log drain, or `docker compose logs`;
- for the ones worth counting, a row in monitor_events, which the backoffice's health panel reads;
- when a rule below trips, an alert to SKILLSPECTOR_WEB_ALERT_WEBHOOK_URL and/or by email to
  SKILLSPECTOR_WEB_ALERT_EMAIL, at most once per rule per cooldown.

Alerts carry what went wrong, scrubbed of keys, tokens, email addresses and URL paths (scrub()):
never a scan's target, a user, or a key. They work the same self-hosted and hosted, where they're
sent from whichever instance saw the event; two instances may both send one now and then.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

from app import db, mail
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Counted kinds.
SCAN_FAILED = "scan_failed"
SANDBOX_ERROR = "sandbox_error"
QUEUE_REDELIVERED = "queue_redelivered"
BOT_REFUSED = "bot_refused"
ALERT_SENT = "alert_sent"
ERROR_KINDS = (SCAN_FAILED, SANDBOX_ERROR)

KEEP_DAYS = 30
_MESSAGE_LIMIT = 500
_WEBHOOK_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class Rule:
    name: str
    title: str
    window_seconds: float
    cooldown_seconds: float


SANDBOX_RULE = Rule("sandbox_error", "Scans can't start their sandbox", 30 * 60, 30 * 60)
FAILURE_RULE = Rule("failure_rate", "Many scans are failing", 30 * 60, 60 * 60)
REDELIVERY_RULE = Rule("queue_redeliveries", "Scans are being redelivered by the queue", 30 * 60, 60 * 60)
BOT_RULE = Rule("bot_refusals", "Every scan submission is being refused as a bot", 15 * 60, 60 * 60)
# Failure rate: at least this many failures, and at least this share of the scans that finished.
FAILURE_MIN = 3
FAILURE_SHARE = 0.5
REDELIVERY_MIN = 3
# Refused submissions, with no scan started in the window: real visitors are refused too.
BOT_MIN = 10

_SECRETS = [
    re.compile(r"sk-ant-[\w-]+"),
    re.compile(r"\bsk-[\w-]{16,}"),
    re.compile(r"\bsst_[\w-]+"),
    re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_\w+"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bbearer\s+[\w.~+/=-]+"),
    re.compile(r"(?i)\b(api[_-]?key|token|password|secret)=[^\s&]+"),
]
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"\b(https?)://([^/\s?#'\"<>)]+)([^\s'\"<>)]*)")


def _host_only(match: re.Match[str]) -> str:
    return f"{match[1]}://{match[2]}" + ("/…" if match[3].strip("/") else "")


def scrub(text: str | None) -> str | None:
    """A message fit for an alert or a log: no keys or tokens, no email addresses, and URLs cut
    to their host, which leaves out which repository or file a user scanned."""
    if text is None:
        return None
    for pattern in _SECRETS:
        text = pattern.sub("[redacted]", text)
    text = _EMAIL.sub("[email]", text)
    text = _URL.sub(_host_only, text)
    return text[:_MESSAGE_LIMIT]


def log_event(kind: str, **fields: Any) -> None:
    """One JSON line on stdout. Fields are ids, counts and scrubbed messages, never user data."""
    line = {"event": f"skillspector.{kind}", "at": round(time.time(), 3), **{key: value for key, value in fields.items() if value is not None}}
    print(json.dumps(line, ensure_ascii=False), file=sys.stdout, flush=True)


def record(kind: str, message: str | None = None, *, scan_id: str | None = None, count: int = 1, **fields: Any) -> None:
    """Log a counted event, store it, and alert if a rule trips. Never raises: monitoring mustn't
    break what it watches. Blocking (it may send an alert): async code calls it in a thread."""
    message = scrub(message)
    log_event(kind, scan_id=scan_id, message=message, count=count if count != 1 else None, **fields)
    try:
        db.add_monitor_event(created_at=time.time(), kind=kind, message=message, scan_id=scan_id, count=count)
        _check(kind, message)
    except Exception:
        logger.warning("Couldn't record the %s monitoring event", kind, exc_info=True)


def _check(kind: str, message: str | None) -> None:
    now = time.time()
    if kind == SANDBOX_ERROR:
        _alert(SANDBOX_RULE, f"A scan couldn't run in its sandbox: {message}", now)
    elif kind == SCAN_FAILED:
        outcomes = db.scan_outcomes(since=now - FAILURE_RULE.window_seconds)
        failed, finished = outcomes["failed"], max(outcomes["finished"], 1)
        if failed >= FAILURE_MIN and failed / finished >= FAILURE_SHARE:
            _alert(FAILURE_RULE, f"{failed} of the {outcomes['finished']} scans that finished in the last 30 minutes failed. The last error: {message}", now)
    elif kind == QUEUE_REDELIVERED:
        count = db.monitor_counts(since=now - REDELIVERY_RULE.window_seconds).get(QUEUE_REDELIVERED, 0)
        if count >= REDELIVERY_MIN:
            _alert(
                REDELIVERY_RULE,
                f"The scan queue redelivered {count} messages in the last 30 minutes: scans are being stopped before they finish (function timeouts or crashes).",
                now,
            )
    elif kind == BOT_REFUSED:
        since = now - BOT_RULE.window_seconds
        refused = db.monitor_counts(since=since).get(BOT_REFUSED, 0)
        if refused >= BOT_MIN and db.scan_outcomes(since=since)["started"] == 0:
            _alert(
                BOT_RULE,
                f"BotID refused {refused} scan submissions in the last 15 minutes, and no scan started: check BotID's setup (its rewrites in vercel.ts, and the deployment's protection).",
                now,
            )


def _alert(rule: Rule, text: str, now: float) -> None:
    last = db.last_monitor_event(ALERT_SENT, message=rule.name)
    if last is not None and now - last["created_at"] < rule.cooldown_seconds:
        return
    channels = send_alert(rule.title, text)
    if channels:
        db.add_monitor_event(created_at=now, kind=ALERT_SENT, message=rule.name, scan_id=None, count=1)


def channels(settings: Settings | None = None) -> list[str]:
    """Where alerts go: 'webhook', 'email', both or neither."""
    settings = settings or get_settings()
    found = []
    if settings.alert_webhook_url:
        found.append("webhook")
    if settings.alert_email and mail.is_configured(settings):
        found.append("email")
    return found


def send_alert(title: str, text: str, settings: Settings | None = None) -> list[str]:
    """Send an alert to every channel set up; the ones it reached."""
    settings = settings or get_settings()
    sent = []
    link = mail.public_link("/admin") if settings.public_url else None
    body = f"{text}\n\nThe backoffice's overview has the details: {link}" if link else text
    if settings.alert_webhook_url:
        payload = {
            # Slack reads `text`, Discord `content`; other endpoints get both, and the fields.
            "text": f"*Skillspector Web: {title}*\n{body}",
            "content": f"**Skillspector Web: {title}**\n{body}",
            "title": title,
            "message": text,
            "link": link,
        }
        request = urllib.request.Request(
            settings.alert_webhook_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "skillspector-web"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=_WEBHOOK_TIMEOUT_SECONDS):
                sent.append("webhook")
        except (OSError, ValueError) as exc:
            logger.warning("Couldn't send an alert to the webhook: %s", exc)
    if settings.alert_email and mail.is_configured(settings):
        for address in (part.strip() for part in settings.alert_email.split(",")):
            if not address:
                continue
            try:
                mail.send(address, f"Skillspector Web: {title}", body, settings)
                if "email" not in sent:
                    sent.append("email")
            except OSError as exc:
                logger.warning("Couldn't email an alert: %s", exc)
    log_event("alert", title=title, channels=sent)
    return sent


def health(*, hours: int = 24) -> dict[str, Any]:
    """The backoffice's health panel: the last day's failures and refusals, the last error, and
    where alerts go."""
    since = time.time() - hours * 3600
    counts = db.monitor_counts(since=since)
    outcomes = db.scan_outcomes(since=since)
    last_error = db.last_monitor_event(*ERROR_KINDS)
    last_alert = db.last_monitor_event(ALERT_SENT)
    return {
        "hours": hours,
        "finished": outcomes["finished"],
        "failed": outcomes["failed"],
        "sandbox_errors": counts.get(SANDBOX_ERROR, 0),
        "redeliveries": counts.get(QUEUE_REDELIVERED, 0),
        "bot_refusals": counts.get(BOT_REFUSED, 0),
        "last_error": (
            {"kind": last_error["kind"], "message": last_error["message"], "at": last_error["created_at"], "scan_id": last_error["scan_id"]}
            if last_error
            else None
        ),
        "alert_channels": channels(),
        "last_alert": {"rule": last_alert["message"], "at": last_alert["created_at"]} if last_alert else None,
    }


def prune() -> int:
    return db.delete_monitor_events_older_than(time.time() - KEEP_DAYS * 86400)
