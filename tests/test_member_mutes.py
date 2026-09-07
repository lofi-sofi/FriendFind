import json
from datetime import timedelta

from friendfind.emailer import outbox
from friendfind.models import AuditLog, Handle, MemberMute, User, db

from conftest import login, make_user


def add_and_vouch(client, owner_email, voucher_email, platform="instagram",
                  username="new_handle"):
    """Owner adds a handle; voucher vouches -> broadcast fires."""
    login(client, owner_email)
    client.post("/handles/add", data={"platform": platform, "username": username})
    h = Handle.query.filter_by(username=username).one()
    client.post("/logout")
    login(client, voucher_email)
    outbox.clear()
    client.post(f"/handles/{h.id}/vouch")
    client.post("/logout")
    return h


def test_default_everyone_subscribed(client, alice, bob):
    carol = make_user("carol@example.com", "Carol")
    add_and_vouch(client, "alice@example.com", "bob@example.com")
    assert {m["to"] for m in outbox} == {"bob@example.com", "carol@example.com"}


def test_mute_suppresses_only_that_person_for_only_the_muter(client, alice, bob):
    carol = make_user("carol@example.com", "Carol")
    dave = make_user("dave@example.com", "Dave")

    # carol mutes alice — silently
    login(client, "carol@example.com")
    outbox.clear()
    client.post(f"/directory/members/{alice.id}/mute-toggle")
    assert MemberMute.query.filter_by(muter_id=carol.id, muted_id=alice.id).count() == 1
    assert outbox == []  # the muted person is never notified
    assert AuditLog.query.count() == 0  # and nothing lands in the shared history
    client.post("/logout")

    # alice's broadcast skips carol only; bob and dave still get it
    add_and_vouch(client, "alice@example.com", "bob@example.com")
    assert {m["to"] for m in outbox} == {"bob@example.com", "dave@example.com"}

    # ...but carol still gets everyone else's broadcasts
    add_and_vouch(client, "bob@example.com", "dave@example.com",
                  platform="tiktok", username="bob_tok")
    assert "carol@example.com" in {m["to"] for m in outbox}


def test_unmute_restores_broadcasts(client, alice, bob):
    login(client, "bob@example.com")
    client.post(f"/directory/members/{alice.id}/mute-toggle")  # mute
    client.post(f"/directory/members/{alice.id}/mute-toggle")  # unmute
    assert MemberMute.query.count() == 0
    client.post("/logout")
    add_and_vouch(client, "alice@example.com", "bob@example.com")
    assert "bob@example.com" in {m["to"] for m in outbox}


def test_muted_member_can_still_interact(client, alice, bob):
    """Muting only touches email — the muted member vouches/sees as normal."""
    login(client, "alice@example.com")
    client.post(f"/directory/members/{bob.id}/mute-toggle")  # alice mutes bob
    client.post("/handles/add", data={"platform": "x", "username": "al_x"})
    h = Handle.query.one()
    client.post("/logout")

    login(client, "bob@example.com")
    assert b"al_x" in client.get("/directory/x").data  # bob still sees alice
    client.post(f"/handles/{h.id}/vouch")  # and can still vouch for her
    assert h.is_verified


def test_cannot_mute_self_or_ghost(client, alice):
    login(client, "alice@example.com")
    assert client.post(f"/directory/members/{alice.id}/mute-toggle").status_code == 404
    assert client.post("/directory/members/9999/mute-toggle").status_code == 404


def test_separate_from_checkin_mute(client, alice, bob):
    """Personal mute and the 120-day overdue mute are independent systems."""
    login(client, "bob@example.com")
    client.post(f"/directory/members/{alice.id}/mute-toggle")
    client.post("/logout")
    assert not bob.is_muted  # muting someone doesn't touch check-in state
    assert not alice.is_muted  # nor the muted person's

    # bob checking in (clearing any overdue state) leaves his personal mute intact
    alice.last_checkin_at -= timedelta(days=10)
    db.session.commit()
    login(client, "bob@example.com")
    client.post("/checkin/confirm")
    assert MemberMute.query.filter_by(muter_id=bob.id, muted_id=alice.id).count() == 1


def test_export_and_purge(client, alice, bob):
    login(client, "alice@example.com")
    client.post(f"/directory/members/{bob.id}/mute-toggle")

    data = json.loads(client.get("/account/export").data)
    assert data["members_muted"][0]["display_name"] == "Bob"
    # who muted YOU is never exported (silence preserved)
    client.post("/logout")
    login(client, "bob@example.com")
    assert "members_muted" in json.loads(client.get("/account/export").data)
    assert json.loads(client.get("/account/export").data)["members_muted"] == []

    # deleting an account clears mutes in both directions
    client.post("/account/delete", data={"password": "supersecret123",
                                         "confirm_phrase": "delete forever"})
    assert MemberMute.query.count() == 0
    assert db.session.get(User, alice.id) is not None  # muter unaffected


def test_directory_shows_toggle_state(client, alice, bob):
    login(client, "alice@example.com")
    assert "🔔 notifying".encode() in client.get("/directory/").data
    client.post(f"/directory/members/{bob.id}/mute-toggle")
    assert "🔕 muted for you".encode() in client.get("/directory/").data
