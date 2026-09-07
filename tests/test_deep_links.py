from friendfind.models import Handle, db
from friendfind.platforms import PLATFORMS, profile_url

from conftest import login


def test_profile_url_patterns():
    assert profile_url("instagram", "nova") == "https://www.instagram.com/nova/"
    assert profile_url("tiktok", "nova") == "https://www.tiktok.com/@nova"
    assert profile_url("x", "nova") == "https://x.com/nova"
    assert profile_url("youtube", "nova") == "https://www.youtube.com/@nova"
    assert profile_url("twitch", "nova") == "https://www.twitch.tv/nova"
    assert profile_url("tumblr", "nova") == "https://www.tumblr.com/nova"
    assert profile_url("bluesky", "nova.bsky.social") == "https://bsky.app/profile/nova.bsky.social"
    assert profile_url("snapchat", "nova") == "https://www.snapchat.com/add/nova"
    assert profile_url("pinterest", "nova") == "https://www.pinterest.com/nova/"
    assert profile_url("telegram", "nova") == "https://t.me/nova"
    # no public profile URL on these two
    assert profile_url("discord", "nova") is None
    assert profile_url("signal", "nova") is None


def test_username_is_url_encoded():
    assert profile_url("x", "weird name/../") == "https://x.com/weird%20name%2F..%2F"


def test_every_platform_is_linkable_or_tooltipped():
    for slug in PLATFORMS:
        assert profile_url(slug, "u") is not None or slug in ("discord", "signal")


def test_linked_handle_renders_with_new_tab_attrs(client, alice):
    login(client, "alice@example.com")
    client.post("/handles/add", data={"platform": "instagram", "username": "al_ig"})
    html = client.get("/directory/instagram").data.decode()
    assert 'href="https://www.instagram.com/al_ig/"' in html
    assert 'target="_blank"' in html and 'rel="noopener noreferrer"' in html


def test_unlinkable_handle_shows_manual_add_tooltip(client, alice):
    login(client, "alice@example.com")
    client.post("/handles/add", data={"platform": "discord", "username": "al#1"})
    html = client.get("/directory/discord").data.decode()
    assert "No profile link available" in html
    assert "add them manually on Discord" in html
    assert 'tabindex="0"' in html  # tappable/focusable on touch
    assert "https://" not in html.split("info-tip")[1][:400]  # no bogus link
