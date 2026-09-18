"""Transactional email.

Sends via the Resend HTTP API when RESEND_API_KEY is set — this is the
required path on Render's free tier, which blocks all outbound SMTP
ports (25, 465, 587) entirely, so smtplib just hangs until the gunicorn
worker times out and gets killed.

Falls back to plain SMTP when RESEND_API_KEY isn't set (any transactional
provider exposes an SMTP endpoint too — Postmark, Mailgun, SES, or Resend
itself on a paid Render instance), honoring SMTP_SSL for implicit-TLS
providers/ports (465) vs. STARTTLS (587, the default).

If neither is configured, messages are logged to the app logger and
appended to `outbox` (which the test-suite inspects).

Every notification email carries a one-click unsubscribe link (signed
token, no login required) plus List-Unsubscribe headers.
"""
from __future__ import annotations

import smtplib
import sys
from email.message import EmailMessage

import requests
from flask import current_app, url_for

from .security import SALT_UNSUBSCRIBE, make_token

# In-memory record of sent mail when nothing is configured (dev + tests).
outbox: list[dict] = []

RESEND_API_URL = "https://api.resend.com/emails"


def _unsubscribe_url(user, category: str) -> str:
    token = make_token({"uid": user.id, "cat": category}, SALT_UNSUBSCRIBE)
    return url_for("account.unsubscribe", token=token, _external=True)


def _send_via_resend(api_key: str, from_addr: str, to: str, subject: str,
                      body: str, unsubscribe_url: str | None) -> None:
    payload = {"from": from_addr, "to": [to], "subject": subject, "text": body}
    if unsubscribe_url:
        payload["headers"] = {
            "List-Unsubscribe": f"<{unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    resp = requests.post(
        RESEND_API_URL, json=payload, timeout=15,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    resp.raise_for_status()


def _send_via_smtp(cfg, host: str, from_addr: str, to: str, subject: str,
                    body: str, unsubscribe_url: str | None) -> None:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    if unsubscribe_url:
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.set_content(body)

    port = cfg.get("SMTP_PORT", 587)
    use_ssl = cfg.get("SMTP_SSL", port == 465)
    smtp_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_cls(host, port, timeout=20) as smtp:
        if not use_ssl and cfg.get("SMTP_STARTTLS", True):
            smtp.starttls()
        user, password = cfg.get("SMTP_USER"), cfg.get("SMTP_PASSWORD")
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)


def send_email(to: str, subject: str, body: str,
               unsubscribe_url: str | None = None) -> None:
    cfg = current_app.config
    if unsubscribe_url:
        body += f"\n\n---\nOne-click unsubscribe (no login needed):\n{unsubscribe_url}\n"

    from_addr = cfg.get("MAIL_FROM", "friendfind@localhost")

    resend_key = cfg.get("RESEND_API_KEY")
    if resend_key:
        _send_via_resend(resend_key, from_addr, to, subject, body, unsubscribe_url)
        return

    host = cfg.get("SMTP_HOST")
    if host:
        _send_via_smtp(cfg, host, from_addr, to, subject, body, unsubscribe_url)
        return

    # Print straight to stderr rather than logger.info: Flask's app
    # logger sits at WARNING outside debug mode, which would silently
    # swallow the message (verification links included).
    if not cfg.get("TESTING"):
        print(f"\n──── email (nothing configured) ────\n"
              f"To: {to}\nSubject: {subject}\n\n{body}\n"
              f"─────────────────────────────────────\n",
              file=sys.stderr, flush=True)
    outbox.append({"to": to, "subject": subject, "body": body})


def send_notification(user, category: str, subject: str, body: str) -> None:
    """Send a category email iff the member's prefs + check-in state allow it."""
    if not user.wants_email(category):
        return
    send_email(user.email, subject, body,
               unsubscribe_url=_unsubscribe_url(user, category))
