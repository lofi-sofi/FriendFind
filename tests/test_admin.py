from friendfind.emailer import outbox
from friendfind.models import AuditLog, Handle, Invite, User, Vouch, db

from conftest import login, make_invite, make_user


def make_admin(email="nova@example.com", name="Nova"):
    user = make_user(email, name)
    user.is_admin = True
    db.session.commit()
    return user


# -- access control -------------------------------------------------------

def test_non_admin_gets_404_everywhere(client, alice, bob):
    login(client, "alice@example.com")
    assert client.get("/admin/").status_code == 404
    assert client.get(f"/admin/members/{bob.id}").status_code == 404
    assert client.post(f"/admin/members/{bob.id}/delete",
                       data={"confirm_phrase": "delete forever"}).status_code == 404
    assert client.post("/admin/invites/reissue").status_code == 404
    assert db.session.get(User, bob.id) is not None


def test_admin_link_hidden_from_members(client, alice):
    login(client, "alice@example.com")
    resp = client.get("/directory/")
    assert b"/admin" not in resp.data
    admin = make_admin()
    client.post("/logout")
    login(client, "nova@example.com")
    assert b"/admin" in client.get("/directory/").data


def test_no_web_path_sets_admin(client, app, alice):
    """No registered route may ever write is_admin — CLI/DB only."""
    login(client, "alice@example.com")
    # Even posting is_admin fields at every form endpoint changes nothing.
    for path in ["/account/preferences", f"/admin/members/{alice.id}"]:
        client.post(path, data={"is_admin": "1", "display_name": "Alice",
                                "email": "alice@example.com"})
    assert alice.is_admin is False


def test_set_admin_cli(app, alice):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["set-admin", "alice@example.com"])
    assert "now an admin" in result.output
    assert alice.is_admin
    result = runner.invoke(args=["set-admin", "alice@example.com", "--revoke"])
    assert "no longer an admin" in result.output
    assert not alice.is_admin
    result = runner.invoke(args=["set-admin", "ghost@example.com"])
    assert "No member" in result.output


# -- member management -----------------------------------------------------

def test_admin_edit_member_logged(client, alice):
    make_admin()
    login(client, "nova@example.com")
    client.post(f"/admin/members/{alice.id}", data={
        "display_name": "Alice B", "email": "aliceb@example.com"})
    assert alice.display_name == "Alice B"
    assert alice.email == "aliceb@example.com"
    entry = AuditLog.query.filter_by(action="admin_edit").one()
    assert entry.is_admin_action
    assert entry.actor_name == "Nova"


def test_admin_delete_member_purges_and_logs(client, alice, bob):
    admin = make_admin()
    # alice has a handle vouched by bob
    login(client, "alice@example.com")
    client.post("/handles/add", data={"platform": "x", "username": "al_x"})
    h = Handle.query.one()
    client.post("/logout")
    login(client, "bob@example.com")
    client.post(f"/handles/{h.id}/vouch")
    client.post("/logout")

    login(client, "nova@example.com")
    # confirmation phrase required
    client.post(f"/admin/members/{alice.id}/delete", data={"confirm_phrase": "nope"})
    assert db.session.get(User, alice.id) is not None

    client.post(f"/admin/members/{alice.id}/delete",
                data={"confirm_phrase": "delete forever"})
    assert User.query.filter_by(email="alice@example.com").count() == 0
    assert Handle.query.count() == 0
    assert Vouch.query.count() == 0
    # accountability record survives, admin-tagged
    entry = AuditLog.query.filter_by(action="admin_delete").one()
    assert entry.is_admin_action and entry.username == "Alice"


def test_admin_cannot_hard_delete_self_here(client):
    admin = make_admin()
    login(client, "nova@example.com")
    client.post(f"/admin/members/{admin.id}/delete",
                data={"confirm_phrase": "delete forever"})
    assert db.session.get(User, admin.id) is not None


# -- invites ---------------------------------------------------------------

def test_admin_invite_revoke_and_reissue(client):
    make_admin()
    inv = make_invite()
    used = make_invite()
    used.used_at = used.created_at
    db.session.commit()

    login(client, "nova@example.com")
    client.post(f"/admin/invites/{inv.id}/revoke")
    assert db.session.get(Invite, inv.id) is None
    assert AuditLog.query.filter_by(action="admin_invite_revoke").count() == 1

    # a used invite can't be revoked
    client.post(f"/admin/invites/{used.id}/revoke")
    assert db.session.get(Invite, used.id) is not None

    client.post("/admin/invites/reissue")
    assert Invite.query.filter_by(used_at=None).count() == 1
    assert AuditLog.query.filter_by(action="admin_invite_issue").count() == 1


# -- vouch override --------------------------------------------------------

def test_admin_vouch_override(client, alice, bob):
    make_admin()
    login(client, "alice@example.com")
    client.post("/handles/add", data={"platform": "tiktok", "username": "al_tok"})
    h = Handle.query.one()
    client.post("/logout")
    login(client, "bob@example.com")
    client.post(f"/handles/{h.id}/vouch")
    assert h.is_verified
    client.post("/logout")

    login(client, "nova@example.com")
    outbox.clear()
    client.post(f"/admin/handles/{h.id}/revoke-vouch")
    assert h.status == "pending"
    assert h.vouches == []
    assert outbox == []  # reversal never broadcasts
    entry = AuditLog.query.filter_by(action="admin_vouch_revoke").one()
    assert entry.is_admin_action and "Bob" in entry.detail


# -- contact admin ---------------------------------------------------------

def test_contact_form_emails_both_admins(client, alice):
    make_admin("nova@example.com", "Nova")
    make_admin("backup@example.com", "Backup")
    login(client, "alice@example.com")
    outbox.clear()
    client.post("/account/contact-admin", data={"message": "help, dispute!"})
    assert {m["to"] for m in outbox} == {"nova@example.com", "backup@example.com"}
    assert "alice@example.com" in outbox[0]["body"]
    assert "help, dispute!" in outbox[0]["body"]

    outbox.clear()
    client.post("/account/contact-admin", data={"message": "   "})
    assert outbox == []
