"""120-day "I'm still here 💗" check-ins."""
from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, request, url_for

from .. import login_required
from ..models import db

bp = Blueprint("checkin", __name__, url_prefix="/checkin")


@bp.route("/", methods=["GET"])
@login_required
def prompt():
    return render_template("checkin/prompt.html")


@bp.route("/confirm", methods=["POST"])
@login_required
def confirm():
    was_muted = g.user.is_muted
    g.user.check_in()
    db.session.commit()
    return render_template("checkin/celebrate.html", was_muted=was_muted)
