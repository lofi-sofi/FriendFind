from friendfind.emailer import outbox
from friendfind.models import AuditLog, Handle, db

from conftest import login, make_user


def add_handle(client, platform="instagram", username="alice_new"):
    return client.post("/handles/add", data={
        "platform": platform, "username": username, "note": "new after ban",
    }, follow_redirects=True)


def test_add_starts_pending_no_broadcast(client, alice, bob):
    login(client, "alice@example.com")
    outbox.clear()
    add_handle(client)
    h = Handle.query.one()
    assert h.status == "pending"
    assert outbox == []  # broadcast only after a vouch
    assert AuditLog.query.filter_by(action="add").count() == 1


def test_cannot_vouch_own_handle(client, alice):
    login(client, "alice@example.com")
    add_handle(client)
    h = Handle.query.one()
    client.post(f"/handles/{h.id}/vouch")
    assert h.status == "pending"


def test_vouch_verifies_and_broadcasts(client, alice, bob):
    carol = make_user("carol@example.com", "Carol")
    dave = make_user("dave@example.com", "Dave")
    dave.notify_new_handles = False  # opted out
    db.session.commit()

    login(client, "alice@example.com")
    add_handle(client)
    h = Handle.query.one()
    client.post("/logout")

    login(client, "bob@example.com")
    outbox.clear()
    client.post(f"/handles/{h.id}/vouch")
    assert h.status == "verified"

    recipients = {m["to"] for m in outbox}
    # bob + carol notified; alice (owner) and dave (opted out) not
    assert recipients == {"bob@example.com", "carol@example.com"}
    assert "@alice_new" in outbox[0]["subject"]
    assert "unsubscribe" in outbox[0]["body"].lower()
    assert AuditLog.query.filter_by(action="vouch").count() == 1


def test_muted_member_not_notified(client, alice, bob):
    from datetime import timedelta
    bob.last_checkin_at -= timedelta(days=200)  # overdue -> muted
    db.session.commit()
    assert bob.is_muted

    login(client, "alice@example.com")
    add_handle(client)
    h = Handle.query.one()
    client.post("/logout")

    carol = make_user("carol@example.com", "Carol")
    login(client, "carol@example.com")
    outbox.clear()
    client.post(f"/handles/{h.id}/vouch")
    assert {m["to"] for m in outbox} == {"carol@example.com"}


def test_edit_username_resets_verification(client, alice, bob):
    login(client, "alice@example.com")
    add_handle(client)
    h = Handle.query.one()
    h.status = "verified"
    db.session.commit()

    client.post(f"/handles/{h.id}/edit", data={"username": "alice_v3", "note": ""})
    assert h.status == "pending"
    assert h.username == "alice_v3"
    assert AuditLog.query.filter_by(action="edit").count() == 1


def test_delete_handle_and_ownership(client, alice, bob):
    login(client, "alice@example.com")
    add_handle(client)
    h = Handle.query.one()
    client.post("/logout")

    # bob can't edit or delete alice's handle
    login(client, "bob@example.com")
    assert client.post(f"/handles/{h.id}/delete").status_code == 404
    assert client.get(f"/handles/{h.id}/edit").status_code == 404
    client.post("/logout")

    login(client, "alice@example.com")
    client.post(f"/handles/{h.id}/delete")
    assert Handle.query.count() == 0
    assert AuditLog.query.filter_by(action="remove").count() == 1


def test_platform_directory_pages(client, alice, bob):
    login(client, "alice@example.com")
    add_handle(client, "instagram", "alice_ig")
    resp = client.get("/directory/instagram")
    assert b"alice_ig" in resp.data
    resp = client.get("/directory/tiktok")
    assert b"alice_ig" not in resp.data
    assert client.get("/directory/not-a-platform").status_code == 404
