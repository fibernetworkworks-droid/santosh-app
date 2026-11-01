"""v0.392 SOCIAL MEDIA MANAGER - YouTube on the Social Desk (plan Y1). Built on Hoola's YouTube module (app/youtube: her
channel connected by Google sign-in with youtube.upload + youtube.force-ssl + yt-analytics; tokens there, sealed):
- her channel shows as a Social Desk account (subscribers, videos read into the baseline / pulse / monthly report);
- a calendar post with YouTube ticked goes up as a Short (a vertical Reel) or a normal video, exactly as she approved it:
  title = the hook (<= 100), description = caption + hashtags, tags, category, her "made for kids" answer (asked once -
  YouTube requires it), the post's picture as the thumbnail when the channel allows it, her playlist if she set one;
- YouTube comments come into the Social Inbox with the same sorting and trust rules; "hide" = held for review (her
  YouTube Studio decides), never deleted;
- a server-wide daily upload guard (YT_DAILY_UPLOADS) so one busy day cannot burn Hoola's YouTube API quota for everyone;
- Google keeps videos uploaded through an API project that has not passed the YouTube API audit PRIVATE - when YouTube
  answers "private" for a public upload, the post says so in plain words (make it public in YouTube Studio)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from ..config import get_settings
from ..db import as_utc, now, session
from .desk import SocialAccount, SocialError, SocialEvent, SocialMedia, SocialPost, _j

log = logging.getLogger("santosh.social.yt")
TITLE_MAX = 100
DESC_MAX = 5000
TAGS_MAX_CHARS = 500
SHORT_MAX_SECONDS = 180


def configured() -> bool:
    try:
        from ..youtube import accounts as YA
        return YA.oauth_ready()
    except Exception:            # noqa: BLE001
        return False


def connect_url(tenant: str) -> str:
    from ..youtube import accounts as YA
    try:
        return YA.start_link(tenant)
    except Exception as e:       # noqa: BLE001 - YTError: server sign-in not set up
        raise SocialError(str(e))


def _client(tenant: str, key: str = ""):
    from ..youtube import accounts as YA
    from ..youtube.client import NotConnected, YTError
    try:
        return YA.get_client(tenant, key or None)
    except (NotConnected, YTError) as e:
        raise SocialError(str(e))


def sync_channel(tenant: str) -> None:
    """Mirror her connected YouTube channel(s) as Social Desk accounts (DB only - no YouTube call)."""
    from ..youtube import accounts as YA
    from ..youtube.models import YouTubeAccount
    try:
        cs = YA.clients(tenant)
    except Exception:            # noqa: BLE001
        cs = []
    keys = {c.key: c for c in cs[:1]}           # the default channel posts; one channel per desk keeps it simple
    with session() as s:
        rows = {a.account_id: a for a in s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant,
                                                                                SocialAccount.platform == "youtube")).all()}
        for k, a in rows.items():
            if k not in keys:
                s.delete(a)
        for k, c in keys.items():
            a = rows.get(k)
            if a is None:
                a = SocialAccount(tenant_id=tenant, platform="youtube", account_id=k, status="ok", kind="Channel")
                s.add(a)
            yta = s.get(YouTubeAccount, k)
            title = (yta.channel_title if yta is not None else "") or c.address
            a.handle = a.handle if a.handle and a.handle != c.address else title[:120]
            a.name = title[:200]
            a.meta_user_id = (yta.channel_id if yta is not None else "") or a.meta_user_id
            if yta is not None and yta.status != "ok":
                a.status, a.last_error = "expired", yta.last_error[:300]
            elif a.status == "expired" and (yta is None or yta.status == "ok"):
                a.status, a.last_error = "ok", ""


def sync_youtube(account: str) -> dict[str, Any]:
    """Her channel's subscribers + latest videos (views, likes, comments) into the desk's numbers."""
    from ..youtube import service as YS
    from ..youtube.client import NotConnected, YTError
    with session() as s:
        a = s.get(SocialAccount, account)
        if a is None:
            raise SocialError("Account nahi mila.")
        tenant, key = a.tenant_id, a.account_id
    try:
        ch = YS.my_channel(tenant, key if key != "google" else None)
        vids = YS.my_videos(tenant, 50).get("videos") or []
    except (NotConnected, YTError) as e:
        with session() as s:
            row = s.get(SocialAccount, account)
            if row is not None:
                row.status, row.last_error = "error", str(e)[:300]
        raise SocialError(str(e))
    with session() as s:
        row = s.get(SocialAccount, account)
        if row is None:
            return {"read": 0}
        row.followers = int(ch.get("subscribers") or 0)
        if ch.get("handle"):
            row.handle = str(ch["handle"])[:120]
        row.meta_user_id = str(ch.get("id") or row.meta_user_id or "")
        row.picture = str(ch.get("thumbnail") or row.picture or "")
        row.last_sync, row.status, row.last_error = now(), "ok", ""
        have = {m.media_id: m for m in s.scalars(select(SocialMedia).where(SocialMedia.account == account)).all()}
        for v in vids:
            m = have.get(v["id"]) or SocialMedia(tenant_id=tenant, account=account, platform="youtube", media_id=v["id"])
            if v["id"] not in have:
                s.add(m)
            m.fmt = "reel" if 0 < int(v.get("seconds") or 0) <= SHORT_MAX_SECONDS else "video"
            m.caption = (v.get("title") or "")[:2000]
            m.permalink = v.get("url") or ""
            m.likes, m.comments, m.views = int(v.get("likes") or 0), int(v.get("comments") or 0), int(v.get("views") or 0)
            try:
                m.posted_at = as_utc(datetime.fromisoformat(str(v.get("published") or "")[:10]))
            except ValueError:
                pass
            m.fetched_at = now()
    return {"read": len(vids)}


# ---------------------------------------------------------------- publishing
def kids_answer(tenant: str) -> bool | None:
    from .pulse import settings
    return settings(tenant).get("yt_kids")


def problems(p: SocialPost, kinds: list[str], cap: str) -> list[str]:
    out = []
    if p.fmt not in ("reel", "video") or "video" not in kinds:
        out.append("YouTube par sirf video jaata hai: post ko Reel (Short) ya Video banaiye aur video file jodiye.")
    if kids_answer(p.tenant_id) is None:
        out.append("YouTube ke liye bataiye: aapke videos bachchon ke liye bane hain ya nahi (Posting controls).")
    if not (p.hook or cap).strip():
        out.append("YouTube video ka title chahiye (hook likhiye).")
    return out


def uploads_today() -> int:
    """Hoola's YouTube uploads in the last 24 h, all users (the API quota is the whole project's)."""
    since = now() - timedelta(hours=24)
    with session() as s:
        rows = s.scalars(select(SocialPost.result).where(SocialPost.published_at >= since,
                                                         SocialPost.platforms.like("%youtube%"))).all()
    return sum(1 for r in rows if (_j(r, {}).get("youtube") or {}).get("id"))


def _title(p: SocialPost) -> str:
    t = (p.hook or (p.caption or "").split("\n")[0]).strip().replace("<", "").replace(">", "")
    if p.fmt == "reel" and "#shorts" not in t.lower() and len(t) <= TITLE_MAX - 8:
        t += " #Shorts"
    return t[:TITLE_MAX]


def _tags(hashtags: list[str]) -> list[str]:
    out, n = [], 0
    for h in hashtags:
        t = str(h).lstrip("#").strip()
        if t and n + len(t) + 1 <= TAGS_MAX_CHARS:
            out.append(t[:30])
            n += len(t) + 1
    return out[:30]


def publish(acc: SocialAccount, p: SocialPost) -> tuple[str, str, str]:
    """Upload the post's video to her channel. Returns (video id, link, note)."""
    import mimetypes
    from pathlib import Path

    from .publish import SocialAsset
    st = get_settings()
    cap_n = int(getattr(st, "yt_daily_uploads", 90) or 90)
    if uploads_today() >= cap_n:
        raise SocialError(f"Aaj Hoola se YouTube uploads ki seema ({cap_n}) poori; kal subah yeh video jayega - post dobara approve kijiye.")
    with session() as s:
        assets = [s.get(SocialAsset, m) for m in _j(p.media, [])]
        vids = [a for a in assets if a is not None and a.kind == "video"]
        imgs = [a for a in assets if a is not None and a.kind == "image"]
        if not vids:
            raise SocialError("YouTube ke liye video file nahi mili.")
        vpath, ipath = vids[0].path, (imgs[0].path if imgs else "")
    tags = _j(p.hashtags, [])
    desc = ((p.caption or "").strip() + ("\n\n" + " ".join("#" + str(h).lstrip("#") for h in tags[:3]) if tags else ""))[:DESC_MAX]
    kids = bool(kids_answer(p.tenant_id))
    snippet = {"title": _title(p), "description": desc.replace("<", "").replace(">", ""), "tags": _tags(tags), "categoryId": "22"}
    status = {"privacyStatus": "public", "selfDeclaredMadeForKids": kids, "embeddable": True}
    c = _client(p.tenant_id, acc.account_id if acc.account_id != "google" else "")
    from ..youtube.client import NotConnected, YTError
    try:
        out = c.upload(Path(vpath).read_bytes(), mimetypes.guess_type(vpath)[0] or "video/mp4", snippet, status)
    except (YTError, NotConnected) as e:
        raise SocialError(str(e))
    vid = str(out.get("id") or "")
    if not vid:
        raise SocialError("YouTube ne video id nahi di.")
    notes = []
    got = ((out.get("status") or {}).get("privacyStatus") or "public")
    if got != "public":
        notes.append("YouTube ne video PRIVATE rakha (Hoola ka YouTube API audit abhi baaki hai): YouTube Studio mein "
                     "is video ko Public kar dijiye.")
    if ipath:
        try:
            c._req_raw("POST", "https://www.googleapis.com/upload/youtube/v3/thumbnails/set", params={"videoId": vid},
                       content=Path(ipath).read_bytes(), headers={"Content-Type": "image/jpeg"})
        except (YTError, NotConnected) as e:
            notes.append(f"Thumbnail nahi laga ({str(e)[:80]}) - channel verify hone par lagta hai.")
    from .pulse import settings
    pl = str(settings(p.tenant_id).get("yt_playlist") or "")
    if pl:
        try:
            c.post("/playlistItems", {"snippet": {"playlistId": pl, "resourceId": {"kind": "youtube#video", "videoId": vid}}}, "snippet")
        except (YTError, NotConnected) as e:
            notes.append(f"Playlist mein nahi juda ({str(e)[:80]}).")
    link = (f"https://www.youtube.com/shorts/{vid}" if p.fmt == "reel" else f"https://www.youtube.com/watch?v={vid}")
    return vid, link, " ".join(notes)


# ---------------------------------------------------------------- comments (Social Inbox)
def channel_id(tenant: str, key: str) -> str:
    with session() as s:
        a = s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant, SocialAccount.platform == "youtube",
                                                  SocialAccount.account_id == key)).first()
        cid = a.meta_user_id if a is not None else ""
    if cid:
        return cid
    c = _client(tenant, key if key != "google" else "")
    items = c.get("/channels", auth=True, part="id", mine="true").get("items") or []
    return str(items[0]["id"]) if items else ""


def comments(tenant: str, key: str) -> list[dict[str, Any]]:
    """Newest comment threads on her channel's videos (one call)."""
    cid = channel_id(tenant, key)
    if not cid:
        return []
    c = _client(tenant, key if key != "google" else "")
    from ..youtube.client import NotConnected, YTError
    try:
        js = c.get("/commentThreads", auth=True, part="snippet", allThreadsRelatedToChannelId=cid, maxResults=50, order="time",
                   textFormat="plainText")
    except (YTError, NotConnected) as e:
        raise SocialError(str(e))
    out = []
    for t in js.get("items") or []:
        top = ((t.get("snippet") or {}).get("topLevelComment") or {})
        sn = top.get("snippet") or {}
        author = ((sn.get("authorChannelId") or {}).get("value") or "")
        out.append({"id": str(top.get("id") or t.get("id") or ""), "video": str((t.get("snippet") or {}).get("videoId") or ""),
                    "author": str(sn.get("authorDisplayName") or "").lstrip("@"), "author_id": author,
                    "text": str(sn.get("textOriginal") or sn.get("textDisplay") or ""), "at": sn.get("publishedAt"),
                    "mine": author == cid, "replies": int((t.get("snippet") or {}).get("totalReplyCount") or 0)})
    return out


def reply(tenant: str, key: str, comment_id: str, text: str) -> str:
    c = _client(tenant, key if key != "google" else "")
    from ..youtube.client import NotConnected, YTError
    try:
        js = c.post("/comments", {"snippet": {"parentId": comment_id, "textOriginal": text}}, "snippet")
    except (YTError, NotConnected) as e:
        raise SocialError(str(e))
    return str(js.get("id") or "")


def hide(tenant: str, key: str, comment_id: str, hidden: bool = True) -> None:
    """Held for review (hidden from the public, her YouTube Studio decides) - never 'rejected', never deleted."""
    c = _client(tenant, key if key != "google" else "")
    from ..youtube.client import NotConnected, YTError, API
    try:
        c._req("POST", API + "/comments/setModerationStatus", auth=True,
               params={"id": comment_id, "moderationStatus": "heldForReview" if hidden else "published"})
    except (YTError, NotConnected) as e:
        raise SocialError(str(e))
