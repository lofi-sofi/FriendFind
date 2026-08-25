"""CLI commands.

  flask create-invite        -> prints an invite registration URL (bootstrap
                                the first member, or invite from the terminal)
  flask send-reminders       -> sends check-in reminder emails; run daily
                                from cron, e.g.:
                                  17 9 * * *  cd /srv/friendfind && .venv/bin/flask send-reminders
"""
from __future__ import annotations

import click
from flask import Flask, url_for

from .emailer import send_notification
from .models import CHECKIN_PERIOD_DAYS, Invite, User, db

REMINDER_STAGES = (14, 7, 1)  # days before the 120-day deadline


def send_due_reminders() -> int:
    """Send the 14/7/1-day reminder emails that are currently due.

    A member's `reminder_stage_sent` records the closest stage already sent
    this cycle, so each stage goes out at most once, and a missed cron day
    just means the next run sends the now-closest stage.
    """
    sent = 0
    for user in User.query.filter(User.email_verified.is_(True)).all():
        days_left = user.days_until_checkin
        if days_left is None or days_left < 0:
            continue  # overdue members are muted; the in-app prompt remains
        for stage in REMINDER_STAGES:
            if days_left <= stage and (user.reminder_stage_sent == 0
                                       or stage < user.reminder_stage_sent):
                checkin_url = url_for("checkin.prompt", _external=True)
                send_notification(
                    user, "checkin_reminder",
                    f"💗 FriendFind check-in — {days_left} day"
                    f"{'s' if days_left != 1 else ''} left",
                    f"Hi {user.display_name}!\n\n"
                    f"Your {CHECKIN_PERIOD_DAYS}-day \"I'm still here\" check-in "
                    f"is due in {days_left} day{'s' if days_left != 1 else ''}.\n"
                    f"Tap the button on this page to stay in the loop:\n\n"
                    f"{checkin_url}\n\n"
                    "If the window passes, you'll stop receiving group emails "
                    "(not a deletion — checking in un-mutes you instantly).",
                )
                user.reminder_stage_sent = stage
                sent += 1
                break
    db.session.commit()
    return sent


def register(app: Flask) -> None:
    @app.cli.command("create-invite")
    def create_invite():
        """Create an invite and print its registration URL."""
        invite = Invite()
        db.session.add(invite)
        db.session.commit()
        url = url_for("auth.register", invite=invite.code, _external=True)
        click.echo(f"Invite URL: {url}")

    @app.cli.command("send-reminders")
    def send_reminders():
        """Send due check-in reminder emails (run daily from cron)."""
        click.echo(f"Sent {send_due_reminders()} reminder(s).")
