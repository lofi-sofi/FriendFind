from friendfind.emailer import outbox
from friendfind.models import Handle, Invite, User, db

from conftest import make_user


def make_admin(email, name):
    user = make_user(email, name)
    user.is_admin = True
    db.session.commit()
    return user


def submit(client, **overrides):
    data = {"name": "Star", "email": "star@example.com",
            "platform": "instagram", "username": "@star.gazer",
            "message": "I know Nova from the art server"}
    data.update(overrides)
    outbox.clear()
    return client.post("/request-invite", data=data)


def test_login_page_offers_both_paths(client):
    html = client.get("/login").data.decode()
    assert "Get an invite link from a member" in html
    assert "Request an invite" in html
    assert "/request-invite" in html
    assert "No public signup" not in html
    assert "One account banned shouldn't mean one friend lost." in html


def test_request_emails_all_admins_with_deep_link(client, app):
    make_admin("nova@example.com", "Nova")
    make_admin("backup@example.com", "Backup")
    make_user("regular@example.com", "Regular")

    resp = submit(client)
    assert b"only submit once" in resp.data
    # both admins, nobody else
    assert {m["to"] for m in outbox} == {"nova@example.com", "backup@example.com"}
    body = outbox[0]["body"]
    assert "Star" in body and "star@example.com" in body
    assert "https://www.instagram.com/star.gazer/" in body  # clickable deep link
    assert "I know Nova from the art server" in body
    assert "No account or invite was created" in body


def test_request_with_unlinkable_platform(client, app):
    make_admin("nova@example.com", "Nova")
    submit(client, platform="discord", username="star#1")
    assert "look them up manually" in outbox[0]["body"]
    assert "https://" not in outbox[0]["body"].split("Primary handle")[1].split("How")[0]


def test_request_creates_nothing(client, app):
    make_admin("nova@example.com", "Nova")
    submit(client)
    assert User.query.count() == 1          # just the admin
    assert Invite.query.count() == 0        # no auto-invite
    assert Handle.query.count() == 0        # handle lives only in the email


def test_request_validation(client, app):
    make_admin("nova@example.com", "Nova")
    for bad in [{"name": ""}, {"email": "nope"}, {"username": ""},
                {"platform": "not-a-platform"}]:
        resp = submit(client, **bad)
        assert outbox == [], bad
        assert b"required" in resp.data

    # message is optional
    submit(client, message="")
    assert len(outbox) == 1


def test_footer_donate_label(client):
    html = client.get("/login").data.decode()
    assert "HELP KEEP THIS APP RUNNING" in html
    assert 'href="https://ko-fi.com/novastarlust"' in html


def test_logo_used_in_nav_and_brand_block(client, alice):
    html = client.get("/login").data.decode()
    assert html.count("img/logo.svg") >= 3  # favicon + nav + brand block
    from conftest import login
    login(client, "alice@example.com")
    assert "img/logo.svg" in client.get("/directory/").data.decode()
