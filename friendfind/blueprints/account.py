"""Settings, email preferences, one-click unsubscribe, data export, hard delete."""
from __future__ import annotations

import json
from datetime import datetime

from flask import (Blueprint, Response, flash, g, redirect, render_template,
                   request, session, url_for)

from .. import login_required
from ..emailer import send_email
from ..models import AuditLog, MemberMute, User, Vouch, db, purge_user
from ..security import SALT_UNSUBSCRIBE, read_token, verify_password

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.route("/settings", methods=["GET"])
@login_required
def settings():
    return render_template("account/settings.html")


@bp.route("/preferences", methods=["POST"])
@login_required
def preferences():
    g.user.notify_new_handles = bool(request.form.get("notify_new_handles"))
    g.user.notify_checkin_reminders = bool(request.form.get("notify_checkin_reminders"))
    db.session.commit()
    flash("Email preferences saved. 💌", "success")
    return redirect(url_for("account.settings"))


@bp.route("/unsubscribe/<token>")
def unsubscribe(token):
    """One-click unsubscribe — signed link, no login required."""
    payload = read_token(token, SALT_UNSUBSCRIBE)
    user = db.session.get(User, payload["uid"]) if payload else None
    if user is None:
        return render_template("account/unsubscribed.html", ok=False), 404
    category = payload.get("cat")
    if category == "new_handle":
        user.notify_new_handles = False
    elif category == "checkin_reminder":
        user.notify_checkin_reminders = False
    else:
        user.notify_new_handles = False
        user.notify_checkin_reminders = False
    db.session.commit()
    return render_template("account/unsubscribed.html", ok=True, category=category)


@bp.route("/contact-admin", methods=["GET", "POST"])
@login_required
def contact_admin():
    """Emails both admins directly — no public contact info listed anywhere."""
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if not message:
            flash("Write a message first!", "error")
        else:
            admins = User.query.filter_by(is_admin=True).all()
            for admin in admins:
                # Direct member-to-admin mail: bypasses notification prefs
                # and mute (it's correspondence, not a group notification).
                send_email(
                    admin.email,
                    f"📮 FriendFind message from {g.user.display_name}",
                    f"From: {g.user.display_name} <{g.user.email}>\n\n{message}",
                )
            flash("Your message is on its way to the admins. 📮💗", "success")
            return redirect(url_for("account.contact_admin"))
    return render_template("account/contact_admin.html")


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


@bp.route("/export")
@login_required
def export():
    """Self-serve JSON export of everything the app stores about the user."""
    u = g.user
    data = {
        "exported_at": _iso(datetime.utcnow()),
        "account": {
            "email": u.email,
            "display_name": u.display_name,
            "created_at": _iso(u.created_at),
            "email_verified": u.email_verified,
            "is_admin": u.is_admin,
            "two_factor_enabled": bool(u.totp_secret),
            "last_checkin_at": _iso(u.last_checkin_at),
            "preferences": {
                "notify_new_handles": u.notify_new_handles,
                "notify_checkin_reminders": u.notify_checkin_reminders,
            },
        },
        "handles": [
            {
                "platform": h.platform,
                "username": h.username,
                "note": h.note,
                "status": h.status,
                "created_at": _iso(h.created_at),
                "verified_at": _iso(h.verified_at),
            }
            for h in u.handles
        ],
        # Only mutes this user created — who muted *them* is other members'
        # private data (muting is silent by design).
        "members_muted": [
            {"display_name": (db.session.get(User, m.muted_id).display_name
                              if db.session.get(User, m.muted_id) else "?"),
             "created_at": _iso(m.created_at)}
            for m in MemberMute.query.filter_by(muter_id=u.id).all()
        ],
        "vouches_given": [
            {"handle_owner": v.handle.owner.display_name,
             "platform": v.handle.platform, "username": v.handle.username,
             "created_at": _iso(v.created_at)}
            for v in Vouch.query.filter_by(voucher_id=u.id).all()
        ],
        "audit_log_entries": [
            {"action": a.action, "platform": a.platform, "username": a.username,
             "detail": a.detail, "created_at": _iso(a.created_at)}
            for a in AuditLog.query.filter_by(actor_id=u.id).all()
        ],
    }
    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=friendfind-export.json"},
    )


@bp.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    """Hard delete: full purge of the user's data, with confirmation."""
    if request.method == "POST":
        password = request.form.get("password", "")
        phrase = request.form.get("confirm_phrase", "").strip().lower()
        if not verify_password(g.user.password_hash, password):
            flash("Wrong password — nothing was deleted.", "error")
        elif phrase != "delete forever":
            flash('Type "delete forever" exactly to confirm.', "error")
        else:
            purge_user(g.user)
            db.session.commit()
            session.clear()
            return render_template("account/deleted.html")
    return render_template("account/delete.html")
