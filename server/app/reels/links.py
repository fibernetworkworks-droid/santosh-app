"""Recognise reel / short-video links from the text another app shares (the official share sheet)."""
from __future__ import annotations

import re
from urllib.parse import urlparse

URL = re.compile(r"https?://[^\s<>\"']+", re.I)

# (platform, host pattern, path pattern with the id as group 1)
RULES = [
    ("youtube", r"(^|\.)youtube\.com$", r"^/shorts/([\w-]{6,20})"),
    ("youtube", r"(^|\.)youtube\.com$", r"^/watch.*?[?&]v=([\w-]{6,20})"),
    ("youtube", r"^youtu\.be$", r"^/([\w-]{6,20})"),
    ("instagram", r"(^|\.)instagram\.com$", r"^/(?:[\w.]+/)?(?:reel|reels|p|tv)/([\w-]{5,40})"),
    ("facebook", r"(^|\.)facebook\.com$", r"^/(?:reel|watch|share/r|share/v)/?(?:\?v=)?([\w-]{4,40})"),
    ("facebook", r"^fb\.watch$", r"^/([\w-]{4,40})"),
    ("snapchat", r"(^|\.)snapchat\.com$", r"^/(?:spotlight|t)/([\w-]{4,80})"),
    ("moj", r"(^|\.)mojapp\.in$", r"^/(?:.*?/)?([\w-]{4,80})"),
    ("josh", r"(^|\.)myjosh\.in$", r"^/(?:.*?/)?([\w-]{4,80})"),
    ("sharechat", r"(^|\.)sharechat\.com$", r"^/(?:.*?/)?([\w-]{4,80})"),
]
NAMES = {"youtube": "YouTube Shorts", "instagram": "Instagram Reels", "facebook": "Facebook Reels",
         "snapchat": "Snapchat Spotlight", "moj": "Moj", "josh": "Josh", "sharechat": "ShareChat", "file": "Video"}


def find(text: str) -> dict | None:
    """{'platform', 'id', 'url', 'key'} for the first reel link in the text, else None."""
    for raw in URL.findall(text or ""):
        raw = raw.rstrip(").,!?]")
        u = urlparse(raw)
        host = (u.hostname or "").lower()
        if host.startswith("m."):
            host = host[2:]
        path = u.path + (("?" + u.query) if u.query else "")
        for platform, hp, pp in RULES:
            if re.search(hp, host) and (m := re.search(pp, path)):
                rid = m.group(1)
                if platform == "youtube":
                    url = f"https://www.youtube.com/shorts/{rid}"
                else:   # tracking parameters (igsh, si, utm...) dropped
                    url = f"https://{u.hostname}{u.path}".rstrip("/")
                return {"platform": platform, "id": rid, "url": url, "key": f"{platform}:{rid}"}
    return None


def caption_text(text: str, link: dict | None) -> str:
    """What the sharing app wrote besides the link (often the reel's caption or title)."""
    t = URL.sub(" ", text or "")
    return re.sub(r"\s+", " ", t).strip()[:1500]
