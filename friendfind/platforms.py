"""Platform registry with custom "charm" icons.

Charms are original hand-drawn SVG shapes matching the app's aesthetic
(bows, hearts, sparkles, cute skulls) — deliberately NOT the platforms'
own logos.
"""

# Each charm is a small inline SVG body drawn on a 24x24 viewBox.
# Colors use currentColor plus the theme accent variables.
_CHARMS = {
    "bow": (
        '<path d="M12 12 5 7c-2-1.4-3 .4-3 2v6c0 1.6 1 3.4 3 2l7-5Zm0 0 7-5c2-1.4 3 .4 3 2v6'
        'c0 1.6-1 3.4-3 2l-7-5Z" fill="var(--charm-a)"/>'
        '<circle cx="12" cy="12" r="2.6" fill="var(--charm-b)"/>'
    ),
    "heart": (
        '<path d="M12 20.5S3.5 15 3.5 9.3C3.5 6.4 5.8 4.5 8.2 4.5c1.6 0 3 .8 3.8 2.1.8-1.3 '
        '2.2-2.1 3.8-2.1 2.4 0 4.7 1.9 4.7 4.8C20.5 15 12 20.5 12 20.5Z" fill="var(--charm-a)"/>'
        '<circle cx="8.6" cy="8.6" r="1.1" fill="var(--charm-hi)"/>'
    ),
    "sparkle": (
        '<path d="M12 2.5c.8 4.6 2.9 6.7 7.5 7.5-4.6.8-6.7 2.9-7.5 7.5-.8-4.6-2.9-6.7-7.5-7.5'
        ' 4.6-.8 6.7-2.9 7.5-7.5Z" fill="var(--charm-a)"/>'
        '<path d="M18.5 14.5c.4 2.3 1.4 3.3 3.7 3.7-2.3.4-3.3 1.4-3.7 3.7-.4-2.3-1.4-3.3-3.7-3.7'
        ' 2.3-.4 3.3-1.4 3.7-3.7Z" fill="var(--charm-b)"/>'
    ),
    "star": (
        '<path d="m12 3 2.5 5.8 6.3.5-4.8 4.1 1.5 6.1L12 16.2l-5.5 3.3 1.5-6.1-4.8-4.1 6.3-.5Z" '
        'fill="var(--charm-a)"/><circle cx="12" cy="11" r="1.4" fill="var(--charm-hi)"/>'
    ),
    "cloud": (
        '<path d="M7 18a4 4 0 0 1-.5-8 5.5 5.5 0 0 1 10.7-1.2A4.2 4.2 0 0 1 17 18H7Z" '
        'fill="var(--charm-a)"/><circle cx="9" cy="13.5" r=".9" fill="var(--charm-b)"/>'
        '<circle cx="13" cy="13.5" r=".9" fill="var(--charm-b)"/>'
        '<path d="M9.6 15.6c.8.8 2 .8 2.8 0" stroke="var(--charm-b)" stroke-width="1" '
        'fill="none" stroke-linecap="round"/>'
    ),
    "skull": (
        '<path d="M12 3.5c-4.4 0-7.5 3-7.5 7 0 2.4 1.2 4.3 3 5.4v2.6c0 .8.7 1.5 1.5 1.5h6'
        'c.8 0 1.5-.7 1.5-1.5v-2.6c1.8-1.1 3-3 3-5.4 0-4-3.1-7-7.5-7Z" fill="var(--charm-a)"/>'
        '<circle cx="9" cy="10.5" r="1.7" fill="var(--charm-b)"/>'
        '<circle cx="15" cy="10.5" r="1.7" fill="var(--charm-b)"/>'
        '<path d="M12 13.2l.9 1.8h-1.8Z" fill="var(--charm-b)"/>'
        '<path d="M19 3.2 16.6 5c-.9.6-.5 1.9.5 2l2.9-.1c1 0 1.5-1.2.8-1.9Z" fill="var(--charm-b)"/>'
    ),
    "moon": (
        '<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10Z" fill="var(--charm-a)"/>'
        '<path d="M17 4c.3 1.7 1 2.4 2.7 2.7C18 7 17.3 7.7 17 9.4 16.7 7.7 16 7 14.3 6.7 '
        '16 6.4 16.7 5.7 17 4Z" fill="var(--charm-b)"/>'
    ),
    "butterfly": (
        '<path d="M11.2 12 5.6 6.2C4.3 4.9 2.5 6 3 7.8L4.8 13c.4 1.3 2 1.8 3.1 1l3.3-2Zm1.6 0'
        ' 5.6-5.8c1.3-1.3 3.1-.2 2.6 1.6L19.2 13c-.4 1.3-2 1.8-3.1 1l-3.3-2Z" fill="var(--charm-a)"/>'
        '<path d="M11 13.5 8.3 17c-.9 1.2.2 2.8 1.6 2.3l1.9-.7.3-5.1Zm2 0 2.7 3.5c.9 1.2-.2 2.8'
        '-1.6 2.3l-1.9-.7-.3-5.1Z" fill="var(--charm-b)"/>'
        '<rect x="11.3" y="10" width="1.4" height="8" rx=".7" fill="var(--charm-hi)"/>'
    ),
    "note": (
        '<path d="M9 18.5V6.2c0-.7.5-1.3 1.2-1.5l7-1.6c1-.2 1.8.5 1.8 1.5v11.9" '
        'stroke="var(--charm-a)" stroke-width="2" fill="none" stroke-linecap="round"/>'
        '<circle cx="6.5" cy="18.5" r="2.8" fill="var(--charm-a)"/>'
        '<circle cx="16.5" cy="16.5" r="2.8" fill="var(--charm-b)"/>'
    ),
    "diamond": (
        '<path d="M12 21 3.5 9.5 7 4h10l3.5 5.5Z" fill="var(--charm-a)"/>'
        '<path d="M3.5 9.5h17M7 4l5 5.5L17 4M12 21l-2.5-11.5M12 21l2.5-11.5" '
        'stroke="var(--charm-hi)" stroke-width=".9" fill="none"/>'
    ),
    "cherry": (
        '<path d="M13 4c-2.5 2-3.5 4.5-3.7 7.5M13 4c1.5 2.5 4 4 6.5 4.5" '
        'stroke="var(--charm-b)" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
        '<circle cx="8.5" cy="15.5" r="4" fill="var(--charm-a)"/>'
        '<circle cx="16" cy="13" r="3.2" fill="var(--charm-a)"/>'
        '<circle cx="7.3" cy="14.2" r="1" fill="var(--charm-hi)"/>'
    ),
    "lock": (
        '<rect x="5" y="10" width="14" height="10" rx="3" fill="var(--charm-a)"/>'
        '<path d="M8 10V8a4 4 0 0 1 8 0v2" stroke="var(--charm-b)" stroke-width="2" fill="none"/>'
        '<circle cx="12" cy="15" r="1.6" fill="var(--charm-b)"/>'
    ),
}

# slug -> (display name, charm key)
PLATFORMS = {
    "instagram": ("Instagram", "bow"),
    "tiktok": ("TikTok", "note"),
    "x": ("X", "skull"),
    "youtube": ("YouTube", "cherry"),
    "twitch": ("Twitch", "butterfly"),
    "discord": ("Discord", "cloud"),
    "tumblr": ("Tumblr", "moon"),
    "bluesky": ("Bluesky", "sparkle"),
    "snapchat": ("Snapchat", "star"),
    "pinterest": ("Pinterest", "heart"),
    "telegram": ("Telegram", "diamond"),
    "signal": ("Signal", "lock"),
}


# Predictable public profile URL patterns, {u} = URL-encoded username.
# Discord and Signal have no public profile URL — deliberately absent; the
# UI shows a "add them manually" tooltip instead. Links are always derived
# from the stored username, never entered or stored as URLs.
_PROFILE_URLS = {
    "instagram": "https://www.instagram.com/{u}/",
    "tiktok": "https://www.tiktok.com/@{u}",
    "x": "https://x.com/{u}",
    "youtube": "https://www.youtube.com/@{u}",
    "twitch": "https://www.twitch.tv/{u}",
    "tumblr": "https://www.tumblr.com/{u}",
    "bluesky": "https://bsky.app/profile/{u}",
    "snapchat": "https://www.snapchat.com/add/{u}",  # Snapchat's add-link format
    "pinterest": "https://www.pinterest.com/{u}/",
    "telegram": "https://t.me/{u}",
}


def profile_url(slug: str, username: str) -> str | None:
    """Outbound profile link for the handle, or None if the platform has
    no public profile URL pattern."""
    pattern = _PROFILE_URLS.get(slug)
    if not pattern:
        return None
    from urllib.parse import quote
    return pattern.format(u=quote(username, safe=""))


def platform_name(slug: str) -> str:
    entry = PLATFORMS.get(slug)
    return entry[0] if entry else slug


def charm_svg(slug: str, size: int = 24) -> str:
    entry = PLATFORMS.get(slug)
    body = _CHARMS[entry[1]] if entry else _CHARMS["sparkle"]
    return (
        f'<svg class="charm" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'aria-hidden="true">{body}</svg>'
    )
