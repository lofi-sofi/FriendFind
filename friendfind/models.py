"""Database models.

Data-minimisation rule: we store ONLY each member's email, password hash,
optional TOTP secret, notification preferences, and platform+username pairs.
No credentials for any external platform are ever stored.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

CHECKIN_PERIOD_DAYS = 120


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    # Admin role. NEVER settable through the web UI — only via a direct DB
    # edit or the `flask set-admin <email>` CLI command, so there is no
    # privilege-escalation surface in request handlers.
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    # Optional TOTP 2FA (opt-in). Secret only set once the user confirms a code.
    totp_secret = db.Column(db.String(64), nullable=True)

    # Check-in system
    last_checkin_at = db.Column(db.DateTime, nullable=True)
    # Highest reminder stage already sent this cycle: 0 none, then 14, 7, 1.
    reminder_stage_sent = db.Column(db.Integer, nullable=False, default=0)

    # Granular email preferences
    notify_new_handles = db.Column(db.Boolean, nullable=False, default=True)
    notify_checkin_reminders = db.Column(db.Boolean, nullable=False, default=True)

    handles = db.relationship(
        "Handle", backref="owner", cascade="all, delete-orphan",
        foreign_keys="Handle.user_id",
    )

    # -- check-in helpers -------------------------------------------------
    @property
    def checkin_deadline(self) -> datetime | None:
        if not self.last_checkin_at:
            return None
        return self.last_checkin_at + timedelta(days=CHECKIN_PERIOD_DAYS)

    @property
    def days_until_checkin(self) -> int | None:
        deadline = self.checkin_deadline
        if deadline is None:
            return None
        return (deadline - utcnow()).days

    @property
    def is_muted(self) -> bool:
        """Overdue members stop *receiving* email until they check in again."""
        deadline = self.checkin_deadline
        return deadline is not None and utcnow() > deadline

    def check_in(self) -> None:
        self.last_checkin_at = utcnow()
        self.reminder_stage_sent = 0

    def wants_email(self, category: str) -> bool:
        """Whether this member should receive an email of the given category."""
        if not self.email_verified or self.is_muted:
            return False
        if category == "new_handle":
            return self.notify_new_handles
        if category == "checkin_reminder":
            return self.notify_checkin_reminders
        return False


class MemberMute(db.Model):
    """One member silently muting another's new-handle broadcast emails.

    One-directional and private: the muted member is never told, and it has
    no effect on anything except whether the muter receives that person's
    "new handle" emails. Entirely separate from the 120-day check-in mute
    (User.is_muted), which pauses ALL incoming email for an overdue member.
    """
    __tablename__ = "member_mutes"
    __table_args__ = (
        db.UniqueConstraint("muter_id", "muted_id", name="uq_member_mute"),
    )

    id = db.Column(db.Integer, primary_key=True)
    muter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    muted_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Invite(db.Model):
    __tablename__ = "invites"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True,
                     default=lambda: secrets.token_urlsafe(24))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                              nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    used_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                           nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)

    @property
    def is_used(self) -> bool:
        return self.used_at is not None


class Handle(db.Model):
    __tablename__ = "handles"
    __table_args__ = (
        db.UniqueConstraint("user_id", "platform", "username", name="uq_handle"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    platform = db.Column(db.String(40), nullable=False, index=True)
    username = db.Column(db.String(120), nullable=False)
    note = db.Column(db.String(200), nullable=True)  # e.g. "new acct after ban"

    status = db.Column(db.String(20), nullable=False, default="pending")  # pending|verified
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)

    vouches = db.relationship("Vouch", backref="handle", cascade="all, delete-orphan")

    @property
    def is_verified(self) -> bool:
        return self.status == "verified"


class Vouch(db.Model):
    """Peer confirmation: a member vouches they recognise the account."""
    __tablename__ = "vouches"
    __table_args__ = (
        db.UniqueConstraint("handle_id", "voucher_id", name="uq_vouch"),
    )

    id = db.Column(db.Integer, primary_key=True)
    handle_id = db.Column(db.Integer, db.ForeignKey("handles.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    voucher = db.relationship("User", foreign_keys=[voucher_id])


class AuditLog(db.Model):
    """Who did what, when — for handle add/edit/remove/vouch events."""
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=True, index=True)
    actor_name = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(30), nullable=False)  # add|edit|remove|vouch|verify
    platform = db.Column(db.String(40), nullable=False)
    username = db.Column(db.String(120), nullable=False)
    detail = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    # True for actions taken with admin powers (delete/edit of another
    # member's data, vouch overrides, invite revocation) — kept visually
    # distinct in the history so admin changes are never silent.
    is_admin_action = db.Column(db.Boolean, nullable=False, default=False)

    actor = db.relationship("User", foreign_keys=[actor_id])


def log_event(actor: User, action: str, platform: str, username: str,
              detail: str | None = None, *, admin: bool = False) -> None:
    db.session.add(AuditLog(
        actor_id=actor.id, actor_name=actor.display_name,
        action=action, platform=platform, username=username, detail=detail,
        is_admin_action=admin,
    ))


def purge_user(user: User) -> None:
    """Hard-delete a member and everything referencing them (GDPR-style).

    Shared by self-serve deletion and admin deletion. Does not commit.
    """
    Vouch.query.filter_by(voucher_id=user.id).delete()
    AuditLog.query.filter_by(actor_id=user.id).delete()
    MemberMute.query.filter(
        (MemberMute.muter_id == user.id) | (MemberMute.muted_id == user.id)
    ).delete()
    # Audit entries other members created about this user's handles
    # (vouches) also mention them — purge those too.
    for h in user.handles:
        AuditLog.query.filter_by(platform=h.platform, username=h.username).delete()
    db.session.delete(user)  # cascades: handles (and their vouches)
