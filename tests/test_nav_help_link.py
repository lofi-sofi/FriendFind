"""The tutorial link lives in the members-only nav, never on public pages."""
from conftest import login, make_invite

VIDEO_URL = "https://youtu.be/m1Tv0EIFBCQ"
LABEL = "Tutorial &amp; Features"


def test_visible_to_logged_in_members(client, alice):
    login(client, "alice@example.com")
    for path in ["/directory/", "/handles/", "/checkin/", "/account/settings"]:
        html = client.get(path).data.decode()
        assert VIDEO_URL in html, path
        assert LABEL in html, path
        # opens in a new tab, without leaking the app URL via Referer
        assert f'href="{VIDEO_URL}" target="_blank" rel="noopener noreferrer"' in html


def test_hidden_on_public_pages(client, app):
    invite = make_invite()
    public = ["/login", "/request-invite", "/forgot",
              f"/register?invite={invite.code}"]
    for path in public:
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert VIDEO_URL not in resp.data.decode(), path


def test_members_are_redirected_off_every_public_page(client, alice):
    """Signed-in members never land on a public page, so the nav can't leak."""
    invite = make_invite()
    login(client, "alice@example.com")
    for path in ["/login", "/request-invite", f"/register?invite={invite.code}"]:
        resp = client.get(path)
        assert resp.status_code == 302, path
        assert resp.headers["Location"].endswith("/directory/"), path
        resp = client.get(path, follow_redirects=True)
        assert resp.request.path == "/directory/", path
        assert VIDEO_URL in resp.data.decode()  # nav renders where it belongs
    # the invite is untouched — still usable by its intended recipient
    assert not invite.is_used


def test_hidden_after_logout(client, alice):
    login(client, "alice@example.com")
    client.post("/logout")
    assert VIDEO_URL not in client.get("/login").data.decode()


def test_styled_like_other_nav_items(client, alice):
    """Plain <a> inside #site-nav, so `.nav a` CSS applies with no overrides."""
    login(client, "alice@example.com")
    html = client.get("/directory/").data.decode()
    nav = html.split('id="site-nav"')[1].split("</nav>")[0]
    assert VIDEO_URL in nav                      # inside the nav element
    assert f'<a href="{VIDEO_URL}"' in nav       # no extra class/style attrs
    assert "style=" not in nav
