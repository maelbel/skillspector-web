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
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app import db, mail
from app.core.config import Settings, get_settings
from app.core.mode import Mode

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
class Measure:
    """Where a rule stands now: whether it trips, the numbers it read, and what an alert says."""

    tripped: bool
    current: str
    alert: str


@dataclass(frozen=True)
class Rule:
    name: str
    title: str
    # What trips it, for the monitoring page.
    condition: str
    # The event that makes it check.
    kind: str
    window_seconds: float
    cooldown_seconds: float
    measure: Callable[[float, str | None], Measure]
    # Only where it can happen: a queue that redelivers, BotID in front of the scan form.
    hosted_only: bool = False


# Failure rate: at least this many failures, and at least this share of the scans that finished.
FAILURE_MIN = 3
FAILURE_SHARE = 0.5
REDELIVERY_MIN = 3
# Refused submissions, with no scan started in the window: real visitors are refused too.
BOT_MIN = 10
_HALF_HOUR = 30 * 60


def _plural(count: int, word: str, plural: str | None = None) -> str:
    return f"{count} {word if count == 1 else plural or word + 's'}"


def _sandbox(now: float, message: str | None) -> Measure:
    errors = db.monitor_counts(since=now - _HALF_HOUR).get(SANDBOX_ERROR, 0)
    if message is None and errors:
        last = db.last_monitor_event(SANDBOX_ERROR)
        message = last["message"] if last else None
    return Measure(errors > 0, f"{_plural(errors, 'sandbox error')} in the last 30 minutes", f"A scan couldn't run in its sandbox: {message}")


def _failures(now: float, message: str | None) -> Measure:
    outcomes = db.scan_outcomes(since=now - _HALF_HOUR)
    failed, finished = outcomes["failed"], outcomes["finished"]
    tripped = failed >= FAILURE_MIN and failed / max(finished, 1) >= FAILURE_SHARE
    if message is None and failed:
        last = db.last_monitor_event(SCAN_FAILED)
        message = last["message"] if last else None
    return Measure(
        tripped,
        f"{failed} of {_plural(finished, 'finished scan')} failed in the last 30 minutes",
        f"{failed} of the {finished} scans that finished in the last 30 minutes failed. The last error: {message}",
    )


def _redeliveries(now: float, message: str | None) -> Measure:
    count = db.monitor_counts(since=now - _HALF_HOUR).get(QUEUE_REDELIVERED, 0)
    return Measure(
        count >= REDELIVERY_MIN,
        f"{_plural(count, 'redelivery', 'redeliveries')} in the last 30 minutes",
        f"The scan queue redelivered {count} messages in the last 30 minutes: scans are being stopped before they finish (function timeouts or crashes).",
    )


def _bots(now: float, message: str | None) -> Measure:
    since = now - 15 * 60
    refused = db.monitor_counts(since=since).get(BOT_REFUSED, 0)
    started = db.scan_outcomes(since=since)["started"]
    return Measure(
        refused >= BOT_MIN and started == 0,
        f"{refused} refused, {_plural(started, 'scan')} started in the last 15 minutes",
        f"BotID refused {refused} scan submissions in the last 15 minutes, and no scan started: check BotID's setup (its rewrites in vercel.ts, and the deployment's protection).",
    )


SANDBOX_RULE = Rule(
    "sandbox_error", "Scans can't start their sandbox", "Any scan fails because of its sandbox, not its skill",
    SANDBOX_ERROR, _HALF_HOUR, 30 * 60, _sandbox,
)
FAILURE_RULE = Rule(
    "failure_rate", "Many scans are failing",
    f"At least {FAILURE_MIN} scans failed in 30 minutes, and at least {FAILURE_SHARE:.0%} of those that finished",
    SCAN_FAILED, _HALF_HOUR, 60 * 60, _failures,
)
REDELIVERY_RULE = Rule(
    "queue_redeliveries", "Scans are being redelivered by the queue", f"The queue redelivered {REDELIVERY_MIN} or more scans in 30 minutes",
    QUEUE_REDELIVERED, _HALF_HOUR, 60 * 60, _redeliveries, hosted_only=True,
)
BOT_RULE = Rule(
    "bot_refusals", "Every scan submission is being refused as a bot",
    f"BotID refused {BOT_MIN} or more submissions in 15 minutes, and no scan started",
    BOT_REFUSED, 15 * 60, 60 * 60, _bots, hosted_only=True,
)
RULES = (SANDBOX_RULE, FAILURE_RULE, REDELIVERY_RULE, BOT_RULE)

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
    for rule in RULES:
        if rule.kind == kind:
            measure = rule.measure(now, message)
            if measure.tripped:
                _alert(rule, measure.alert, now)


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


def rules_status(settings: Settings | None = None) -> list[dict[str, Any]]:
    """Each alert rule: what trips it, where it stands now, and when it last alerted."""
    settings = settings or get_settings()
    now = time.time()
    hosted = settings.mode is Mode.HOSTED
    status = []
    for rule in RULES:
        applies = hosted or not rule.hosted_only
        measure = rule.measure(now, None) if applies else None
        last = db.last_monitor_event(ALERT_SENT, message=rule.name)
        quiet_until = last["created_at"] + rule.cooldown_seconds if last else None
        status.append({
            "name": rule.name,
            "title": rule.title,
            "condition": rule.condition,
            "cooldown_minutes": round(rule.cooldown_seconds / 60),
            "applies": applies,
            "tripped": bool(measure and measure.tripped),
            "current": measure.current if measure else None,
            "last_alert_at": last["created_at"] if last else None,
            "quiet_until": quiet_until if quiet_until and quiet_until > now else None,
        })
    return status


def channel_details(settings: Settings | None = None) -> dict[str, Any]:
    """Where alerts go, for an admin: the webhook by its host only (its path is its secret), and
    the email addresses, with whether email can be sent."""
    settings = settings or get_settings()
    webhook_host = None
    if settings.alert_webhook_url:
        match = _URL.match(settings.alert_webhook_url)
        webhook_host = match[2] if match else "set"
    emails = [part.strip() for part in (settings.alert_email or "").split(",") if part.strip()]
    return {"webhook_host": webhook_host, "emails": emails, "email_ready": mail.is_configured(settings)}


def prune() -> int:
    return db.delete_monitor_events_older_than(time.time() - KEEP_DAYS * 86400)
