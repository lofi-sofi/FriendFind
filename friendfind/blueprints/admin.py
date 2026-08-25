"""Admin-only tools: member management, invite control, vouch overrides.

Admin status itself is NEVER granted here (or anywhere in the web UI) —
only `flask set-admin <email>` or a direct DB edit can change it. Every
action taken here writes an admin-tagged audit entry so nothing is silent.
Non-admins get a 404, and see no admin controls anywhere in their UI.
"""
from __future__ import annotations

from functools import wraps

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, url_for)

from ..models import Handle, Invite, User, db, log_event, purge_user

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if not g.user.is_admin:
            abort(404)  # don't reveal the admin area exists
        return view(*args, **kwargs)
    return wrapped


@bp.route("/")
@admin_required
def home():
    members = User.query.order_by(User.display_name).all()
    invites = Invite.query.order_by(Invite.created_at.desc()).all()
    disputed = (Handle.query.filter_by(status="verified")
                .order_by(Handle.verified_at.desc()).all())
    return render_template("admin/home.html", members=members,
                           invites=invites, verified_handles=disputed)


# -- member accounts ------------------------------------------------------

@bp.route("/members/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_member(user_id):
    member = db.session.get(User, user_id)
    if member is None:
        abort(404)
    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        if not display_name or "@" not in email:
            flash("Display name and a valid email are required.", "error")
        elif (email != member.email
              and User.query.filter_by(email=email).first()):
            flash("That email is already registered to another member.", "error")
        else:
            changes = []
            if display_name != member.display_name:
                changes.append(f"name {member.display_name!r} -> {display_name!r}")
                member.display_name = display_name
            if email != member.email:
                changes.append("email changed")
                member.email = email
            if changes:
                log_event(g.user, "admin_edit", "account", member.display_name,
                          "; ".join(changes), admin=True)
                db.session.commit()
                flash("Member updated (logged as an admin action).", "success")
            return redirect(url_for("admin.home"))
    return render_template("admin/edit_member.html", member=member)


@bp.route("/members/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_member(user_id):
    member = db.session.get(User, user_id)
    if member is None:
        abort(404)
    if member.id == g.user.id:
        flash("Use Settings → Delete for your own account.", "error")
        return redirect(url_for("admin.home"))
    if request.form.get("confirm_phrase", "").strip().lower() != "delete forever":
        flash('Type "delete forever" exactly to confirm.', "error")
        return redirect(url_for("admin.edit_member", user_id=member.id))
    name = member.display_name
    purge_user(member)
    # The one record that survives the purge: an admin-tagged accountability
    # entry for the deletion itself.
    log_event(g.user, "admin_delete", "account", name, admin=True)
    db.session.commit()
    flash(f"{name}'s account was hard-deleted (logged as an admin action).",
          "success")
    return redirect(url_for("admin.home"))


# -- invites --------------------------------------------------------------

@bp.route("/invites/<int:invite_id>/revoke", methods=["POST"])
@admin_required
def revoke_invite(invite_id):
    invite = db.session.get(Invite, invite_id)
    if invite is None:
        abort(404)
    if invite.is_used:
        flash("That invite was already used — nothing to revoke.", "error")
        return redirect(url_for("admin.home"))
    log_event(g.user, "admin_invite_revoke", "invite", invite.code[:8] + "…",
              admin=True)
    db.session.delete(invite)
    db.session.commit()
    flash("Invite revoked — the link is now dead.", "success")
    return redirect(url_for("admin.home"))


@bp.route("/invites/reissue", methods=["POST"])
@admin_required
def reissue_invite():
    invite = Invite(created_by_id=g.user.id)
    db.session.add(invite)
    db.session.flush()
    log_event(g.user, "admin_invite_issue", "invite", invite.code[:8] + "…",
              admin=True)
    db.session.commit()
    flash("Fresh invite link created.", "success")
    return redirect(url_for("admin.home"))


# -- vouch override -------------------------------------------------------

@bp.route("/handles/<int:handle_id>/revoke-vouch", methods=["POST"])
@admin_required
def revoke_vouch(handle_id):
    """Reverse a disputed vouch: back to pending, no broadcast until re-vouched."""
    handle = db.session.get(Handle, handle_id)
    if handle is None or not handle.is_verified:
        abort(404)
    vouchers = ", ".join(v.voucher.display_name for v in handle.vouches
                         if v.voucher)
    for v in list(handle.vouches):
        db.session.delete(v)
    handle.status = "pending"
    handle.verified_at = None
    log_event(g.user, "admin_vouch_revoke", handle.platform, handle.username,
              f"vouch by {vouchers or 'unknown'} reversed; handle back to pending",
              admin=True)
    db.session.commit()
    flash(f"Vouch reversed — @{handle.username} is back to pending "
          "(logged as an admin action).", "success")
    return redirect(url_for("admin.home"))
