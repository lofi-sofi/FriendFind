"""Invite-only registration, email verification, login with optional TOTP 2FA."""
from __future__ import annotations

import io

import pyotp
import segno
from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, session, url_for)

from .. import login_required
from ..emailer import send_email
from ..models import Invite, User, db, utcnow
from ..security import (SALT_VERIFY_EMAIL, hash_password, make_token,
                        read_token, verify_password)

bp = Blueprint("auth", __name__)

VERIFY_MAX_AGE = 60 * 60 * 48  # 48h


def _send_verification(user: User) -> None:
    token = make_token({"uid": user.id}, SALT_VERIFY_EMAIL)
    link = url_for("auth.verify_email", token=token, _external=True)
    send_email(
        user.email,
        "Verify your FriendFind email 🎀",
        f"Hi {user.display_name}!\n\nTap this link to verify your email and "
        f"activate your account:\n\n{link}\n\nThe link is valid for 48 hours.",
    )


@bp.route("/register", methods=["GET", "POST"])
def register():
    code = request.values.get("invite", "").strip()
    invite = Invite.query.filter_by(code=code).first() if code else None
    if invite is None or invite.is_used:
        return render_template("auth/no_invite.html"), 403

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        if not email or "@" not in email or not display_name:
            flash("Please fill in a valid email and a display name.", "error")
        elif len(password) < 10:
            flash("Password must be at least 10 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
        else:
            user = User(email=email, display_name=display_name,
                        password_hash=hash_password(password))
            db.session.add(user)
            db.session.flush()
            invite.used_by_id = user.id
            invite.used_at = utcnow()
            db.session.commit()
            _send_verification(user)
            return render_template("auth/check_inbox.html", email=email)

    return render_template("auth/register.html", invite=code)


@bp.route("/verify/<token>")
def verify_email(token):
    payload = read_token(token, SALT_VERIFY_EMAIL, max_age=VERIFY_MAX_AGE)
    if not payload:
        abort(404)
    user = db.session.get(User, payload["uid"])
    if user is None:
        abort(404)
    if not user.email_verified:
        user.email_verified = True
        user.check_in()  # start the first 120-day check-in cycle
        db.session.commit()
    flash("Email verified — welcome in! 💗", "success")
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user is None or not verify_password(user.password_hash, password):
            flash("Wrong email or password.", "error")
        elif not user.email_verified:
            _send_verification(user)
            return render_template("auth/check_inbox.html", email=user.email)
        elif user.totp_secret:
            session.clear()
            session["pending_2fa_user"] = user.id
            return redirect(url_for("auth.login_2fa"))
        else:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("directory.home"))
    return render_template("auth/login.html")


@bp.route("/login/2fa", methods=["GET", "POST"])
def login_2fa():
    uid = session.get("pending_2fa_user")
    user = db.session.get(User, uid) if uid else None
    if user is None:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        code = request.form.get("code", "").strip().replace(" ", "")
        if user.totp_secret and pyotp.TOTP(user.totp_secret).verify(code, valid_window=1):
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("directory.home"))
        flash("That code didn't match — try again.", "error")
    return render_template("auth/login_2fa.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


# -- TOTP 2FA opt-in ------------------------------------------------------

def _totp_uri(user: User, secret: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="FriendFind")


@bp.route("/2fa/setup", methods=["GET", "POST"])
@login_required
def twofa_setup():
    if g.user.totp_secret:
        return redirect(url_for("account.settings"))
    secret = session.get("totp_setup_secret")
    if not secret:
        secret = pyotp.random_base32()
        session["totp_setup_secret"] = secret

    if request.method == "POST":
        code = request.form.get("code", "").strip().replace(" ", "")
        if pyotp.TOTP(secret).verify(code, valid_window=1):
            g.user.totp_secret = secret
            db.session.commit()
            session.pop("totp_setup_secret", None)
            flash("Two-factor authentication is on. 🔒✨", "success")
            return redirect(url_for("account.settings"))
        flash("Code didn't match — scan the QR again and retry.", "error")

    qr = segno.make(_totp_uri(g.user, secret))
    buf = io.BytesIO()
    qr.save(buf, kind="svg", xmldecl=False, svgclass=None, lineclass=None,
            scale=4, dark="#5b3a5e", light=None)
    return render_template("auth/twofa_setup.html", secret=secret,
                           qr_svg=buf.getvalue().decode("utf-8"))


@bp.route("/2fa/disable", methods=["POST"])
@login_required
def twofa_disable():
    password = request.form.get("password", "")
    if not verify_password(g.user.password_hash, password):
        flash("Wrong password — 2FA stays on.", "error")
    else:
        g.user.totp_secret = None
        db.session.commit()
        flash("Two-factor authentication is off.", "success")
    return redirect(url_for("account.settings"))


# -- Invites --------------------------------------------------------------

@bp.route("/invites", methods=["GET", "POST"])
@login_required
def invites():
    if request.method == "POST":
        invite = Invite(created_by_id=g.user.id)
        db.session.add(invite)
        db.session.commit()
        flash("Invite link created — share it with your friend. 💌", "success")
        return redirect(url_for("auth.invites"))
    mine = (Invite.query.filter_by(created_by_id=g.user.id)
            .order_by(Invite.created_at.desc()).all())
    return render_template("auth/invites.html", invites=mine)
