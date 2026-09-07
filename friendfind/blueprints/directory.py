"""Platform-grouped directory: one page per platform, listing only the
members who actually have a handle there."""
from __future__ import annotations

from flask import Blueprint, abort, g, render_template
from sqlalchemy import func

from flask import abort, flash, redirect, request, url_for

from .. import login_required
from ..models import Handle, MemberMute, User, db
from ..platforms import PLATFORMS

bp = Blueprint("directory", __name__, url_prefix="/directory")


@bp.route("/")
@login_required
def home():
    counts = dict(
        db.session.query(Handle.platform, func.count(func.distinct(Handle.user_id)))
        .group_by(Handle.platform).all()
    )
    pending = (Handle.query.filter(Handle.status == "pending",
                                   Handle.user_id != g.user.id)
               .order_by(Handle.created_at.desc()).all())
    members = User.query.order_by(User.display_name).all()
    muted_ids = {m.muted_id for m in
                 MemberMute.query.filter_by(muter_id=g.user.id).all()}
    return render_template("directory/home.html", counts=counts,
                           pending=pending, members=members,
                           muted_ids=muted_ids)


@bp.route("/members/<int:user_id>/mute-toggle", methods=["POST"])
@login_required
def mute_toggle(user_id):
    """Silently mute/unmute another member's new-handle emails for yourself.

    One-directional and private: nothing is sent to the other member, no
    audit entry is written (the change history is group-visible, which
    would break the silence), and their access to the app is untouched.
    """
    member = db.session.get(User, user_id)
    if member is None or member.id == g.user.id:
        abort(404)
    existing = MemberMute.query.filter_by(muter_id=g.user.id,
                                          muted_id=member.id).first()
    if existing:
        db.session.delete(existing)
        flash(f"You'll get {member.display_name}'s new-handle emails again. 🔔",
              "success")
    else:
        db.session.add(MemberMute(muter_id=g.user.id, muted_id=member.id))
        flash(f"Muted {member.display_name}'s new-handle emails — just for "
              "you, and they won't know. 🔕", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("directory.home"))


@bp.route("/<platform>")
@login_required
def platform(platform):
    if platform not in PLATFORMS:
        abort(404)
    handles = (Handle.query.filter_by(platform=platform)
               .join(User, Handle.user_id == User.id)
               .order_by(User.display_name, Handle.created_at).all())
    return render_template("directory/platform.html", slug=platform,
                           handles=handles)
