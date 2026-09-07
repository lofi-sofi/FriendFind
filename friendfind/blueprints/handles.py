"""Handle CRUD, peer vouching, and the verified-handle broadcast."""
from __future__ import annotations

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, url_for)

from .. import login_required
from ..emailer import send_notification
from ..models import (AuditLog, Handle, MemberMute, User, Vouch, db,
                      log_event, utcnow)
from ..platforms import PLATFORMS, platform_name

bp = Blueprint("handles", __name__, url_prefix="/handles")


@bp.route("/")
@login_required
def mine():
    handles = (Handle.query.filter_by(user_id=g.user.id)
               .order_by(Handle.platform, Handle.created_at).all())
    return render_template("handles/mine.html", handles=handles)


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        platform = request.form.get("platform", "")
        username = request.form.get("username", "").strip().lstrip("@")
        note = request.form.get("note", "").strip() or None
        if platform not in PLATFORMS:
            flash("Pick a platform from the list.", "error")
        elif not username:
            flash("Username can't be empty.", "error")
        elif Handle.query.filter_by(user_id=g.user.id, platform=platform,
                                    username=username).first():
            flash("You already added that handle.", "error")
        else:
            handle = Handle(user_id=g.user.id, platform=platform,
                            username=username, note=note)
            db.session.add(handle)
            log_event(g.user, "add", platform, username, note)
            db.session.commit()
            flash("Handle added! It broadcasts to the group once a friend "
                  "vouches for it. 🎀", "success")
            return redirect(url_for("handles.mine"))
    return render_template("handles/form.html", handle=None)


@bp.route("/<int:handle_id>/edit", methods=["GET", "POST"])
@login_required
def edit(handle_id):
    handle = db.session.get(Handle, handle_id)
    if handle is None or handle.user_id != g.user.id:
        abort(404)
    if request.method == "POST":
        username = request.form.get("username", "").strip().lstrip("@")
        note = request.form.get("note", "").strip() or None
        if not username:
            flash("Username can't be empty.", "error")
        else:
            changed = username != handle.username
            old = handle.username
            handle.username = username
            handle.note = note
            if changed:
                # A renamed handle needs a fresh vouch before re-broadcast.
                handle.status = "pending"
                handle.verified_at = None
                for v in list(handle.vouches):
                    db.session.delete(v)
            log_event(g.user, "edit", handle.platform, username,
                      f"was @{old}" if changed else "note updated")
            db.session.commit()
            flash("Handle updated.", "success")
            return redirect(url_for("handles.mine"))
    return render_template("handles/form.html", handle=handle)


@bp.route("/<int:handle_id>/delete", methods=["POST"])
@login_required
def delete(handle_id):
    handle = db.session.get(Handle, handle_id)
    if handle is None or handle.user_id != g.user.id:
        abort(404)
    log_event(g.user, "remove", handle.platform, handle.username)
    db.session.delete(handle)
    db.session.commit()
    flash("Handle removed.", "success")
    return redirect(url_for("handles.mine"))


@bp.route("/<int:handle_id>/vouch", methods=["POST"])
@login_required
def vouch(handle_id):
    handle = db.session.get(Handle, handle_id)
    if handle is None:
        abort(404)
    if handle.user_id == g.user.id:
        flash("You can't vouch for your own handle — that's the whole point!",
              "error")
        return redirect(request.referrer or url_for("directory.home"))
    if handle.is_verified:
        return redirect(request.referrer or url_for("directory.home"))

    db.session.add(Vouch(handle_id=handle.id, voucher_id=g.user.id))
    handle.status = "verified"
    handle.verified_at = utcnow()
    log_event(g.user, "vouch", handle.platform, handle.username,
              f"vouched for {handle.owner.display_name}")
    db.session.commit()

    _broadcast_verified(handle, vouched_by=g.user)
    flash(f"You vouched for @{handle.username} — the group has been "
          "notified! ✨", "success")
    return redirect(request.referrer or url_for("directory.home"))


def _broadcast_verified(handle: Handle, vouched_by: User) -> None:
    """Email every subscribed, non-muted member about the verified handle."""
    pname = platform_name(handle.platform)
    subject = f"💗 {handle.owner.display_name} is now @{handle.username} on {pname}"
    body = (
        f"{handle.owner.display_name} added a new handle:\n\n"
        f"    {pname}: @{handle.username}\n"
        + (f"    note: {handle.note}\n" if handle.note else "")
        + f"\nVouched for by {vouched_by.display_name}, so it's confirmed real.\n"
        f"Give them a follow so nobody loses touch!"
    )
    # Members who personally muted the handle's owner are skipped — silent,
    # one-directional, and unrelated to the check-in mute (which
    # send_notification already enforces).
    muter_ids = {m.muter_id for m in
                 MemberMute.query.filter_by(muted_id=handle.user_id).all()}
    for member in User.query.filter(User.id != handle.user_id).all():
        if member.id in muter_ids:
            continue
        send_notification(member, "new_handle", subject, body)


@bp.route("/audit")
@login_required
def audit():
    events = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("handles/audit.html", events=events)
