import json
from datetime import timedelta

from friendfind.cli import send_due_reminders
from friendfind.emailer import outbox
from friendfind.models import AuditLog, Handle, User, Vouch, db

from conftest import login, make_user


def test_checkin_resets_timer_and_unmutes(client, alice):
    alice.last_checkin_at -= timedelta(days=200)
    db.session.commit()
    assert alice.is_muted

    login(client, "alice@example.com")
    resp = client.post("/checkin/confirm")
    assert b"you're here" in resp.data.lower()
    assert not alice.is_muted
    assert alice.days_until_checkin >= 119


def test_reminder_schedule(app, alice):
    # 20 days out: nothing due
    alice.last_checkin_at -= timedelta(days=100)
    db.session.commit()
    outbox.clear()
    assert send_due_reminders() == 0

    # 14 days out
    alice.last_checkin_at -= timedelta(days=5)
    db.session.commit()
    assert send_due_reminders() == 1
    assert "14 days" in outbox[-1]["subject"]
    assert send_due_reminders() == 0  # not resent

    # 7 days out
    alice.last_checkin_at -= timedelta(days=7)
    db.session.commit()
    assert send_due_reminders() == 1
    assert "7 days" in outbox[-1]["subject"]

    # 1 day out
    alice.last_checkin_at -= timedelta(days=6)
    db.session.commit()
    assert send_due_reminders() == 1
    assert "1 day" in outbox[-1]["subject"]

    # overdue: muted, no more reminder mail
    alice.last_checkin_at -= timedelta(days=3)
    db.session.commit()
    assert send_due_reminders() == 0

    # checking in resets the cycle
    alice.check_in()
    db.session.commit()
    assert alice.reminder_stage_sent == 0


def test_reminder_respects_preference(app, alice):
    alice.notify_checkin_reminders = False
    alice.last_checkin_at -= timedelta(days=110)
    db.session.commit()
    outbox.clear()
    send_due_reminders()
    assert outbox == []


def test_one_click_unsubscribe(client, app, alice, bob):
    login(client, "bob@example.com")
    client.post("/handles/add", data={"platform": "x", "username": "bobby"})
    h = Handle.query.one()
    client.post("/logout")
    login(client, "alice@example.com")
    outbox.clear()
    client.post(f"/handles/{h.id}/vouch")

    mail = next(m for m in outbox if m["to"] == "alice@example.com")
    link = [l for l in mail["body"].splitlines() if "/account/unsubscribe/" in l][0].strip()
    path = link.split("localhost")[1]

    fresh = app.test_client()  # not logged in — one-click, no login required
    resp = fresh.get(path)
    assert resp.status_code == 200
    assert alice.notify_new_handles is False
    assert alice.notify_checkin_reminders is True  # granular: only that category


def test_export_contains_everything(client, alice):
    login(client, "alice@example.com")
    client.post("/handles/add", data={"platform": "tumblr", "username": "al"})
    resp = client.get("/account/export")
    data = json.loads(resp.data)
    assert data["account"]["email"] == "alice@example.com"
    assert data["handles"][0]["username"] == "al"
    assert data["audit_log_entries"][0]["action"] == "add"
    assert "password" not in json.dumps(data).lower().replace("password_", "")


def test_hard_delete_purges_everything(client, alice, bob):
    login(client, "bob@example.com")
    client.post("/handles/add", data={"platform": "x", "username": "bobby"})
    h = Handle.query.one()
    client.post("/logout")

    login(client, "alice@example.com")
    client.post(f"/handles/{h.id}/vouch")
    client.post("/handles/add", data={"platform": "x", "username": "alice_x"})

    # wrong password: nothing deleted
    client.post("/account/delete", data={"password": "nope",
                                         "confirm_phrase": "delete forever"})
    assert User.query.count() == 2

    resp = client.post("/account/delete", data={
        "password": "supersecret123", "confirm_phrase": "delete forever"})
    assert b"permanently" in resp.data
    assert User.query.filter_by(email="alice@example.com").count() == 0
    assert Handle.query.filter_by(username="alice_x").count() == 0
    assert Vouch.query.count() == 0
    assert AuditLog.query.filter_by(actor_name="Alice").count() == 0
    # bob's own data survives
    assert Handle.query.filter_by(username="bobby").count() == 1
