"""Transactional email.

Uses plain SMTP (any transactional provider — Postmark, Mailgun, SES —
exposes an SMTP endpoint, which keeps this small deployment simple).
If SMTP is not configured, messages are logged to the app logger and
appended to `outbox` (which the test-suite inspects).

Every notification email carries a one-click unsubscribe link (signed
token, no login required) plus List-Unsubscribe headers.
"""
from __future__ import annotations

import smtplib
import sys
from email.message import EmailMessage

from flask import current_app, url_for

from .security import SALT_UNSUBSCRIBE, make_token

# In-memory record of sent mail when SMTP isn't configured (dev + tests).
outbox: list[dict] = []


def _unsubscribe_url(user, category: str) -> str:
    token = make_token({"uid": user.id, "cat": category}, SALT_UNSUBSCRIBE)
    return url_for("account.unsubscribe", token=token, _external=True)


def send_email(to: str, subject: str, body: str,
               unsubscribe_url: str | None = None) -> None:
    cfg = current_app.config
    if unsubscribe_url:
        body += f"\n\n---\nOne-click unsubscribe (no login needed):\n{unsubscribe_url}\n"

    msg = EmailMessage()
    msg["From"] = cfg.get("MAIL_FROM", "friendfind@localhost")
    msg["To"] = to
    msg["Subject"] = subject
    if unsubscribe_url:
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.set_content(body)

    host = cfg.get("SMTP_HOST")
    if not host:
        # Print straight to stderr rather than logger.info: Flask's app
        # logger sits at WARNING outside debug mode, which would silently
        # swallow the message (verification links included).
        if not cfg.get("TESTING"):
            print(f"\n──── email (SMTP not configured) ────\n"
                  f"To: {to}\nSubject: {subject}\n\n{body}\n"
                  f"─────────────────────────────────────\n",
                  file=sys.stderr, flush=True)
        outbox.append({"to": to, "subject": subject, "body": body})
        return

    with smtplib.SMTP(host, cfg.get("SMTP_PORT", 587), timeout=20) as smtp:
        if cfg.get("SMTP_STARTTLS", True):
            smtp.starttls()
        user, password = cfg.get("SMTP_USER"), cfg.get("SMTP_PASSWORD")
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)


def send_notification(user, category: str, subject: str, body: str) -> None:
    """Send a category email iff the member's prefs + check-in state allow it."""
    if not user.wants_email(category):
        return
    send_email(user.email, subject, body,
               unsubscribe_url=_unsubscribe_url(user, category))
