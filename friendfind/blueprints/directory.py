"""Platform-grouped directory: one page per platform, listing only the
members who actually have a handle there."""
from __future__ import annotations

from flask import Blueprint, abort, g, render_template
from sqlalchemy import func

from .. import login_required
from ..models import Handle, User, db
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
    return render_template("directory/home.html", counts=counts,
                           pending=pending, members=members)


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
