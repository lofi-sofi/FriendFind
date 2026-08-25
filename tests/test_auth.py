import re

import pyotp

from friendfind.emailer import outbox
from friendfind.models import User, db

from conftest import login, make_invite, make_user


def test_register_requires_invite(client):
    resp = client.get("/register")
    assert resp.status_code == 403
    resp = client.post("/register?invite=not-a-real-code", data={
        "email": "eve@example.com", "display_name": "Eve",
        "password": "longenoughpw1",
    })
    assert resp.status_code == 403
    assert User.query.count() == 0


def test_register_verify_login_flow(client, app):
    invite = make_invite()
    resp = client.post(f"/register?invite={invite.code}", data={
        "email": "cara@example.com", "display_name": "Cara",
        "password": "longenoughpw1",
    })
    assert resp.status_code == 200
    user = User.query.filter_by(email="cara@example.com").first()
    assert user is not None and not user.email_verified
    assert user.password_hash.startswith("$argon2")
    assert invite.is_used

    # invite is single-use
    resp = client.post(f"/register?invite={invite.code}", data={
        "email": "eve@example.com", "display_name": "Eve",
        "password": "longenoughpw1"})
    assert resp.status_code == 403

    # cannot log in before verifying — a fresh verification mail is sent
    outbox.clear()
    resp = login(client, "cara@example.com", "longenoughpw1")
    assert b"verification" in resp.data.lower() or b"inbox" in resp.data.lower()

    link = re.search(r"http://localhost(/verify/\S+)", outbox[-1]["body"]).group(1)
    resp = client.get(link, follow_redirects=True)
    assert user.email_verified
    assert user.last_checkin_at is not None  # first check-in cycle started

    resp = login(client, "cara@example.com", "longenoughpw1")
    assert resp.request.path == "/directory/"


def test_wrong_password_rejected(client, alice):
    resp = login(client, "alice@example.com", "wrong-password")
    assert b"Wrong email or password" in resp.data


def test_totp_2fa_flow(client, app, alice):
    login(client, "alice@example.com")
    resp = client.get("/2fa/setup")
    secret = re.search(rb"<code>([A-Z2-7]+)</code>", resp.data).group(1).decode()

    # wrong code rejected
    resp = client.post("/2fa/setup", data={"code": "000000"})
    assert alice.totp_secret is None

    code = pyotp.TOTP(secret).now()
    client.post("/2fa/setup", data={"code": code})
    assert alice.totp_secret == secret

    # login now requires the TOTP step
    client.post("/logout")
    resp = login(client, "alice@example.com")
    assert resp.request.path == "/login/2fa"
    resp = client.post("/login/2fa", data={"code": pyotp.TOTP(secret).now()},
                       follow_redirects=True)
    assert resp.request.path == "/directory/"
