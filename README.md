# FriendFind 🎀

A private, invite-only web app for a closed friend group to track each other's
social media handles — so if anyone's account gets banned or deleted, they add
their new handle, a friend vouches for it, and the whole group gets an email.
The network never fractures.

Not automated ban detection: members self-report. The app's job is fast,
trustworthy re-connection.

## Features

- **Invite-only** — no public signup; members create single-use invite links
  (or use `flask create-invite` from the terminal to bootstrap the first member).
- **Auth & security** — Argon2 password hashing, email verification before the
  account activates, optional TOTP 2FA (QR-code setup, opt-in), and self-serve
  password reset via a signed email link (1-hour expiry, strictly single-use,
  enumeration-safe messaging, logged to the audit trail). The app stores
  *only* email, password hash, and platform+username pairs — never any
  credentials for external platforms.
- **Handles** — add/edit/remove, each tagged with a custom "charm" icon
  (original bows/hearts/cute-skulls, not platform logos). Every change lands in
  an audit log (who, what, when).
- **Peer vouching** — a new handle stays *pending* until another member clicks
  "I recognize this account". The vouch unlocks the broadcast: an email to
  every subscribed member. Renaming a handle resets its verification.
- **Platform directory** — a page per platform (Instagram, TikTok, X, …)
  listing only the members who are actually on it.
- **120-day check-ins** — an in-app "I'm still here 💗" prompt with reminder
  emails 14, 7, and 1 day before the deadline, and a heart-sparkle burst on
  confirm. Missing the window mutes *incoming* email (never deletes anything);
  checking in un-mutes instantly.
- **Notifications** — granular email preferences, one-click unsubscribe links
  (signed token, no login, `List-Unsubscribe` headers), and an optional
  in-browser chime pack (three synthesized chimes, no audio files).
- **Data rights** — self-serve JSON export of everything stored about you, and
  self-serve **hard delete** (password + typed confirmation) that purges the
  account, handles, vouches, and audit entries immediately.
- **Two moods** — 🌸 *My Melody mode* (soft pastel pink) and 💀 *Kuromi mode*
  (dark and punkier), with sparkle micro-animations throughout.
- **Admin role** — admins can view/edit/hard-delete any member's account,
  revoke or reissue invite links, and reverse a disputed vouch. Every admin
  action is written to the change history tagged 🛡️ as an admin action, so
  nothing is ever silent. There is deliberately **no web UI path to admin
  status** — only `flask set-admin <email>` or a direct DB edit — and regular
  members see no admin controls at all (admin URLs 404 for them).
- **Contact admin** — an in-app form that emails both admins directly over the
  existing SMTP setup, so no contact info needs to be listed anywhere.

## Stack

Flask + SQLAlchemy + SQLite, server-rendered templates, no build step.
Chosen deliberately for a small private group: one process, one file of data,
nearly zero maintenance. Email goes out over SMTP, so any transactional
provider (Postmark, Mailgun, SES, …) works via its SMTP endpoint.

## Running locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=wsgi.py
flask create-invite        # prints the first registration URL
flask run
```

Without SMTP configured, outgoing email (including verification links) is
printed to the console — handy for local testing.

### Seeding the two launch admins

After the founding member (Nova) and the designated backup have registered
and verified, grant each admin status from the server — this is the only way
to do it (no UI path exists):

```bash
flask set-admin nova@example.com
flask set-admin backup@example.com
```

`flask set-admin <email> --revoke` removes it again.

## Deploying

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export SERVER_NAME=friendfind.example.com   # used for links in emails/CLI
export SMTP_HOST=smtp.postmarkapp.com SMTP_USER=... SMTP_PASSWORD=...
export MAIL_FROM="FriendFind <hello@friendfind.example.com>"
gunicorn wsgi:app
```

The database defaults to `instance/friendfind.db` (SQLite); set `DATABASE_URL`
for Postgres if you prefer. Schedule the reminder job daily:

```cron
17 9 * * *  cd /srv/friendfind && .venv/bin/flask send-reminders
```

## Tests

```bash
python -m pytest
```
