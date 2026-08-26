import re
import time

from friendfind.blueprints import auth as auth_module
from friendfind.emailer import outbox
from friendfind.models import AuditLog

from conftest import login, make_user


def request_reset(client, email):
    outbox.clear()
    return client.post("/forgot", data={"email": email})


def extract_link(mail):
    return re.search(r"http://localhost(/reset/\S+)", mail["body"]).group(1)


def test_forgot_sends_link_to_verified_member(client, alice):
    resp = request_reset(client, "alice@example.com")
    assert b"If <strong>alice@example.com</strong> is registered" in resp.data
    assert len(outbox) == 1
    assert "/reset/" in outbox[0]["body"]
    assert "1 hour" in outbox[0]["body"]


def test_no_email_enumeration(client, alice):
    make_user("shy@example.com", "Shy", verified=False)
    # unknown address and unverified member: same page, no email
    for email in ["ghost@example.com", "shy@example.com"]:
        resp = request_reset(client, email)
        assert b"is registered" in resp.data  # identical generic message
        assert outbox == []


def test_reset_flow_end_to_end(client, alice):
    request_reset(client, "alice@example.com")
    link = extract_link(outbox[0])

    assert client.get(link).status_code == 200

    # too-short password rejected, token still usable
    client.post(link, data={"password": "short"})
    resp = client.post(link, data={"password": "brandnewsecret42"},
                       follow_redirects=True)
    assert b"Password updated" in resp.data

    # old password dead, new one works
    resp = login(client, "alice@example.com", "supersecret123")
    assert b"Wrong email or password" in resp.data
    resp = login(client, "alice@example.com", "brandnewsecret42")
    assert resp.request.path == "/directory/"

    # audit entry: self-service, not an admin action
    entry = AuditLog.query.filter_by(action="password_reset").one()
    assert entry.actor_name == "Alice"
    assert entry.is_admin_action is False


def test_reset_link_is_single_use(client, alice):
    request_reset(client, "alice@example.com")
    link = extract_link(outbox[0])
    client.post(link, data={"password": "brandnewsecret42"})
    # spent token: form gone, second reset attempt rejected
    assert client.get(link).status_code == 404
    resp = client.post(link, data={"password": "anothernewpass9"})
    assert resp.status_code == 404
    assert login(client, "alice@example.com", "brandnewsecret42"
                 ).request.path == "/directory/"


def test_stale_link_dies_when_password_changes_elsewhere(client, alice):
    """A link requested earlier stops working once the password changes."""
    request_reset(client, "alice@example.com")
    old_link = extract_link(outbox[0])
    request_reset(client, "alice@example.com")
    new_link = extract_link(outbox[0])
    client.post(new_link, data={"password": "brandnewsecret42"})
    assert client.get(old_link).status_code == 404


def test_expired_link_rejected(client, alice, monkeypatch):
    request_reset(client, "alice@example.com")
    link = extract_link(outbox[0])
    monkeypatch.setattr(auth_module, "RESET_MAX_AGE", 0)
    time.sleep(1.1)
    assert client.get(link).status_code == 404


def test_garbage_token_rejected(client, alice):
    assert client.get("/reset/not-a-real-token").status_code == 404
