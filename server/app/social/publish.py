"""v0.355 SOCIAL MEDIA MANAGER Phase 2: a calendar post goes out to Instagram and / or her Facebook Page - only the exact
post she approved (caption + hashtags + pictures + platforms + format + time, hashed at her tap), at its time or when she
taps Publish now. Pictures come from her upload or a Brand poster made for the post; Instagram fetches them from a
short-lived signed link on this server (Meta's servers cannot log in). Every result (post id, link, or the plain reason it
failed) is written on the post and the desk; a post whose time passed more than a day ago is marked missed, never posted
late (a Diwali wish on 12 November helps no one)."""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, as_utc, new_id, now, session
from . import meta as M
from .desk import SocialAccount, SocialError, SocialEvent, SocialPost, _event, _j, _local, ensure_tables as _ensure_desk

IMG_MAX = 8 * 1024 * 1024
VID_MAX = 100 * 1024 * 1024
CAPTION_MAX = 2200          # Instagram's caption limit
HASHTAG_MAX = 30            # Instagram's hashtag limit
LATE = timedelta(hours=24)  # an approved post more than a day late is marked missed, not posted


class SocialAsset(Base):
    """A picture / video for a post: her upload or a poster Hoola made. Pictures are kept as JPEG (Instagram's format)."""
    __tablename__ = "social_assets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(8), default="image")          # image | video
    mime: Mapped[str] = mapped_column(String(40), default="image/jpeg")
    path: Mapped[str] = mapped_column(Text, default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    size: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(10), default="upload")     # upload | poster
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_tables() -> None:
    from .. import db as _db
    _ensure_desk()
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        SocialAsset.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _root() -> Path:
    return Path(os.environ.get("SOCIAL_DIR", "data/social"))


def _dir(tenant: str) -> Path:
    d = _root() / "".join(ch for ch in tenant if ch.isalnum() or ch in "-_")[:64]
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- pictures / videos
def add_asset(tenant: str, data: bytes, name: str = "", source: str = "upload") -> dict[str, Any]:
    """Check the bytes really are a picture / video (never trust the file name), keep pictures as JPEG up to 1440 px wide."""
    ensure_tables()
    if not data:
        raise SocialError("File khaali hai.")
    head = data[:16]
    is_video = head[4:8] == b"ftyp"                                   # MP4 / MOV
    if is_video:
        if len(data) > VID_MAX:
            raise SocialError("Video 100 MB se badi hai.")
        kind, mime, ext, w, h, out = "video", "video/mp4", ".mp4", 0, 0, data
    else:
        if len(data) > IMG_MAX * 2:
            raise SocialError("Photo 16 MB se badi hai.")
        try:
            from PIL import Image, ImageOps
            im = Image.open(io.BytesIO(data))
            im = ImageOps.exif_transpose(im).convert("RGB")
        except Exception:
            raise SocialError("Yeh photo ya video nahi lagti (JPG / PNG / WEBP / MP4 bhejiye).")
        if im.width > 1440:
            im = im.resize((1440, round(im.height * 1440 / im.width)))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88, optimize=True)
        out, kind, mime, ext, w, h = buf.getvalue(), "image", "image/jpeg", ".jpg", im.width, im.height
        ratio = w / h if h else 1
        if not 0.79 <= ratio <= 1.92 and ratio > 0.5:                 # Instagram feed takes 4:5 .. 1.91:1 (9:16 = Stories)
            pass                                                     # checked per format at publishing time
    with session() as s:
        a = SocialAsset(tenant_id=tenant, kind=kind, mime=mime, name=(name or "")[:200], width=w, height=h, size=len(out),
                        source=source)
        s.add(a)
        s.flush()
        aid = a.id
        p = _dir(tenant) / f"{aid}{ext}"
        p.write_bytes(out)
        a.path = str(p)
    return asset_view(aid)


def asset_view(aid: str, hours: int = 2) -> dict[str, Any]:
    with session() as s:
        a = s.get(SocialAsset, aid)
        if a is None:
            raise SocialError("Photo / video nahi mili.")
        return {"id": a.id, "kind": a.kind, "width": a.width, "height": a.height, "size": a.size, "source": a.source,
                "url": signed_url(a.id, hours)}


def _sig(aid: str, exp: int) -> str:
    key = (get_settings().secret_key or get_settings().api_key or "hoola-dev").encode()
    return hmac.new(key, f"social:{aid}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def signed_url(aid: str, hours: int = 2) -> str:
    exp = int(time.time()) + hours * 3600
    return get_settings().public_base_url.rstrip("/") + f"/api/social/media/{aid}?e={exp}&s={_sig(aid, exp)}"


def open_signed(aid: str, e: str, s: str) -> tuple[Path, str]:
    """For Meta's servers (and her own screen): the file behind a signed link that has not expired."""
    try:
        exp = int(e)
    except (TypeError, ValueError):
        raise SocialError("Link galat.")
    if exp < time.time() or not hmac.compare_digest(_sig(aid, exp), str(s or "")):
        raise SocialError("Link purana ya galat.")
    with session() as ss:
        a = ss.get(SocialAsset, aid)
        if a is None or not a.path or not Path(a.path).exists():
            raise SocialError("File nahi mili.")
        return Path(a.path), a.mime


def make_poster(tenant: str, post_id: str, render: Any = None) -> dict[str, Any]:
    """A poster for this post from her Brand kit (Brand Sahayak's layouts, checks and fonts), final quality, 4:5 for the feed or
    9:16 for a Story; attached to the post (so the post needs her OK again)."""
    with session() as s:
        p = s.get(SocialPost, post_id)
        if p is None or p.tenant_id != tenant:
            raise SocialError("Yeh post nahi mila.")
        brief = "\n".join(x for x in (p.hook, p.visual, p.occasion) if x)
        size = "story" if p.fmt == "story" else "insta_post"
    data = (render or _brand_poster)(tenant, brief, size)
    a = add_asset(tenant, data, f"poster-{post_id}.jpg", source="poster")
    attach(tenant, post_id, [a["id"]], append=False)
    return a


def _brand_poster(tenant: str, brief: str, size: str) -> bytes:
    from ..brand import render as RN
    from ..brand import service as BR
    try:
        d = BR.make(tenant, brief=brief or "Our work", sizes=[size])["design"]
        with session() as s:
            row = s.get(BR.BrandDesign, d["id"])
            kitv, logo_uri, _lh = BR._kit_for_page(tenant)
            html = BR._page_for(tenant, row, size, False, kitv, logo_uri)      # final, no PROOF mark
        res = RN.render([{"html": html, "size": size, "out": "jpg", "quality": 90, "scale_to": 1080}])
        return res[0]["data"]
    except BR.BrandError as e:
        raise SocialError(str(e))
    except RN.RenderError as e:
        raise SocialError(f"Poster nahi ban paya: {e}")


def attach(tenant: str, post_id: str, asset_ids: list[str], append: bool = True) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        p = s.get(SocialPost, post_id)
        if p is None or p.tenant_id != tenant:
            raise SocialError("Yeh post nahi mila.")
        if p.status in ("published", "publishing"):
            raise SocialError("Yeh post ja chuka hai; ise badla nahi ja sakta.")
        for aid in asset_ids:
            a = s.get(SocialAsset, aid)
            if a is None or a.tenant_id != tenant:
                raise SocialError("Photo / video nahi mili.")
        media = (_j(p.media, []) if append else []) + [a for a in asset_ids if a not in (_j(p.media, []) if append else [])]
        p.media = json.dumps(media[:10])
        if p.status == "approved":
            p.status, p.approved_hash = "draft", ""                # a change after her OK needs her OK again
        return {"id": p.id, "media": media[:10], "status": p.status}


def detach(tenant: str, post_id: str, asset_id: str) -> dict[str, Any]:
    with session() as s:
        p = s.get(SocialPost, post_id)
        if p is None or p.tenant_id != tenant:
            raise SocialError("Yeh post nahi mila.")
        if p.status in ("published", "publishing"):
            raise SocialError("Yeh post ja chuka hai; ise badla nahi ja sakta.")
        p.media = json.dumps([a for a in _j(p.media, []) if a != asset_id])
        if p.status == "approved":
            p.status, p.approved_hash = "draft", ""
        return {"id": p.id, "status": p.status}


# ---------------------------------------------------------------- what she approved
def post_hash(p: SocialPost) -> str:
    body = json.dumps([p.caption, _j(p.hashtags, []), _j(p.media, []), p.platforms, p.fmt, p.slot], ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()[:32]


def caption_of(p: SocialPost) -> str:
    tags = [t for t in _j(p.hashtags, []) if t and t.lower() not in (p.caption or "").lower()]
    text = (p.caption or "").strip()
    return (text + ("\n\n" + " ".join(tags) if tags else "")).strip()


def problems(p: SocialPost) -> list[str]:
    """What stops this post from going out, in plain words (checked before her OK is used)."""
    out = []
    media = _j(p.media, [])
    plats = [x for x in (p.platforms or "").split(",") if x]
    with session() as s:
        kinds = [(s.get(SocialAsset, m).kind if s.get(SocialAsset, m) else "") for m in media]
    cap = caption_of(p)
    if "instagram" in plats:
        if not media:
            out.append("Instagram ke liye photo ya video chahiye.")
        elif p.fmt == "reel" and kinds[:1] != ["video"]:
            out.append("Reel ke liye video chahiye.")
        elif p.fmt == "carousel" and (len(media) < 2 or "video" in kinds):
            out.append("Carousel ke liye 2 se 10 photo chahiye.")
        if len(cap) > CAPTION_MAX:
            out.append(f"Caption {len(cap)} akshar ka hai; Instagram {CAPTION_MAX} tak leta hai.")
        if cap.count("#") > HASHTAG_MAX:
            out.append(f"Instagram {HASHTAG_MAX} se zyada hashtag nahi leta.")
    if "facebook" in plats and not cap and not media:
        out.append("Facebook post khaali hai.")
    if "[price]" in cap or "[" in cap and "]" in cap:
        out.append("Caption mein khaali jagah [ ] bachi hai: asli jaankari bhariye ya hata dijiye.")
    return out


# ---------------------------------------------------------------- publishing
def _account(s, tenant: str, platform: str) -> SocialAccount | None:
    return s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant, SocialAccount.platform == platform,
                                                 SocialAccount.status == "ok").order_by(SocialAccount.connected_at)).first()


def _to_instagram(acc: SocialAccount, token: str, p: SocialPost, urls: list[tuple[str, str]], cap: str) -> tuple[str, str]:
    scopes = (acc.scopes or "").split(",")
    if acc.scopes and M.IG_PUBLISH_SCOPE not in scopes:
        raise SocialError("Instagram par post karne ki permission nahi di gayi: Social Desk par Reconnect Instagram dabaiye.")
    lim = M.ig_publish_limit(acc.account_id, token)
    if lim["used"] >= lim["total"] - 1:
        raise SocialError(f"Instagram ki aaj ki API post limit poori ({lim['used']}/{lim['total']}); kal subah dobara.")
    uid = acc.account_id
    if p.fmt == "carousel":
        kids = [M.ig_container(uid, token, image_url=u, is_carousel_item="true") if k == "image" else
                M.ig_container(uid, token, video_url=u, media_type="VIDEO", is_carousel_item="true") for k, u in urls[:10]]
        for kid, (k, _u) in zip(kids, urls):
            if k == "video":
                M.ig_wait(kid, token)
        cid = M.ig_container(uid, token, media_type="CAROUSEL", children=",".join(kids), caption=cap)
    elif p.fmt == "story":
        k, u = urls[0]
        cid = M.ig_container(uid, token, media_type="STORIES", **({"image_url": u} if k == "image" else {"video_url": u}))
        if k == "video":
            M.ig_wait(cid, token)
    elif urls[0][0] == "video":
        cid = M.ig_container(uid, token, media_type="REELS", video_url=urls[0][1], caption=cap)
        M.ig_wait(cid, token)
    else:
        cid = M.ig_container(uid, token, image_url=urls[0][1], caption=cap)
    mid = M.ig_publish(uid, token, cid)
    return mid, M.ig_permalink(mid, token)


def _to_facebook(acc: SocialAccount, token: str, p: SocialPost, urls: list[tuple[str, str]], cap: str) -> tuple[str, str]:
    page = acc.account_id
    if not urls:
        pid = M.fb_text(page, token, cap)
    elif urls[0][0] == "video":
        pid = M.fb_video(page, token, urls[0][1], cap)
    elif len(urls) > 1:
        pid = M.fb_photos_post(page, token, [u for k, u in urls if k == "image"], cap)
    else:
        pid = M.fb_photo(page, token, urls[0][1], cap)
    if not pid:
        raise SocialError("Facebook ne post id nahi diya.")
    return pid, M.fb_permalink(pid, token)


def publish_post(tenant: str, post_id: str, by_tap: bool = False) -> dict[str, Any]:
    """Send one post. by_tap = she tapped Publish now (that tap is her OK for exactly what she sees); otherwise the post
    must carry her earlier approval and still match it. Each platform is tried on its own; results land on the post."""
    from .. import accounts as accm
    ensure_tables()
    with session() as s:
        p = s.get(SocialPost, post_id)
        if p is None or p.tenant_id != tenant:
            raise SocialError("Yeh post nahi mila.")
        if p.status in ("published", "publishing"):
            raise SocialError("Yeh post pehle hi ja chuka hai / ja raha hai.")
        if by_tap:
            p.approved_hash = post_hash(p)
            p.seen = 1                                 # v0.359 her tap = her own OK
        elif p.status != "approved" or not p.approved_hash or p.approved_hash != post_hash(p):
            raise SocialError("Yeh post aapki haan ke baad badla hai (ya haan nahi mili): dobara approve kijiye.")
        bad = problems(p)
        if bad:
            p.error = " ".join(bad)[:500]
            raise SocialError(" ".join(bad))
        p.status, p.attempts = "publishing", (p.attempts or 0) + 1
        media = _j(p.media, [])
        plats = [x for x in (p.platforms or "").split(",") if x]
    urls: list[tuple[str, str]] = []
    with session() as s:
        for m in media:
            a = s.get(SocialAsset, m)
            if a:
                urls.append((a.kind, signed_url(a.id, 3)))
    results: dict[str, Any] = {}
    for plat in plats:
        with session() as s:
            acc = _account(s, tenant, plat)
            if acc is None:
                results[plat] = {"error": f"{'Instagram' if plat == 'instagram' else 'Facebook Page'} juda nahi hai."}
                continue
            s.expunge(acc)
        token = accm.decrypt(acc.token_enc) or ""
        with session() as s:
            p = s.get(SocialPost, post_id)
            s.expunge(p)
        try:
            pid, link = (_to_instagram if plat == "instagram" else _to_facebook)(acc, token, p, urls, caption_of(p))
            results[plat] = {"id": pid, "link": link}
        except (M.MetaError, SocialError) as e:
            results[plat] = {"error": str(e)[:300]}
            if getattr(e, "code", None) == 190:
                with session() as s:
                    a = s.get(SocialAccount, acc.id)
                    if a:
                        a.status, a.last_error = "expired", str(e)[:300]
    ok = [k for k, v in results.items() if v.get("id")]
    with session() as s:
        p = s.get(SocialPost, post_id)
        p.result = json.dumps(results, ensure_ascii=False)
        p.status = "published" if ok else "failed"
        p.error = "; ".join(f"{k}: {v['error']}" for k, v in results.items() if v.get("error"))[:600]
        if ok:
            p.published_at = now()
        hook = p.hook or (p.caption or "")[:60]
    if ok:
        _event(tenant, "run", "ok" if len(ok) == len(results) else "warn",
               f"Posted '{hook[:60]}' on {', '.join(x.title() for x in ok)}."
               + (f" Not on: {'; '.join(k + ' - ' + v['error'] for k, v in results.items() if v.get('error'))}" if len(ok) < len(results) else ""))
    else:
        _event(tenant, "alert", "bad", f"Could not post '{hook[:60]}': {'; '.join(v.get('error', '') for v in results.values())[:300]}")
    return {"id": post_id, "status": "published" if ok else "failed", "results": results}


def due(tenant: str, at: datetime | None = None) -> list[str]:
    """Approved posts whose time has come (her local clock). Older than a day = missed (marked, never posted late)."""
    from .pulse import auto_posts_today, may_go, settings, trust_of
    local = (at or _local(tenant)).astimezone(_local(tenant).tzinfo)
    stamp = local.strftime("%Y-%m-%dT%H:%M")
    late = (local - LATE).strftime("%Y-%m-%dT%H:%M")
    st = settings(tenant)
    if st["paused"]:
        return []                                   # v0.359 pause / emergency stop: nothing goes out
    trust, used = trust_of(tenant), auto_posts_today(tenant, local)
    out = []
    with session() as s:
        for p in s.scalars(select(SocialPost).where(SocialPost.tenant_id == tenant, SocialPost.status == "approved")
                           .order_by(SocialPost.slot)).all():
            if p.slot and p.slot <= stamp:
                if p.slot < late:
                    p.status, p.error = "missed", "Iska samay ek din se zyada pehle nikal gaya; purani post der se nahi daali."
                    s.add(SocialEvent(tenant_id=tenant, kind="note", level="warn", text=f"Missed: '{(p.hook or '')[:60]}' ({p.slot}) was not posted late."))
                elif not may_go(tenant, p, local, trust, st["quiet"], used):
                    out.append(p.id)
                    used += p.seen == 0
    return out


def _told_auto(tenant: str, pid: str, r: dict[str, Any]) -> None:
    """v0.359 Saathi: a plan post that went out on its own is told to her the same day (Bharosa: in the weekly pulse)."""
    from .pulse import _say, trust_of
    if r.get("status") != "published" or trust_of(tenant) != "saathi":
        return
    with session() as s:
        p = s.get(SocialPost, pid)
        if p is None or p.seen != 0:
            return
        hook = p.hook or ""
        link = next((v.get("link") for v in (_j(p.result, {}) or {}).values() if isinstance(v, dict) and v.get("link")), "")
    _say(tenant, "social_day", f"Posted from your approved plan: '{hook[:70]}'" + (f" - {link}" if link else "") + ".")


def run_publisher(tenant: str, at: datetime | None = None) -> dict[str, Any]:
    sent, failed = 0, 0
    for pid in due(tenant, at):
        try:
            r = publish_post(tenant, pid)
            sent += r["status"] == "published"
            _told_auto(tenant, pid, r)
            failed += r["status"] != "published"
        except SocialError as e:
            failed += 1
            with session() as s:
                p = s.get(SocialPost, pid)
                if p and p.status == "approved":
                    p.status, p.error = "failed", str(e)[:500]
            _event(tenant, "alert", "warn", f"A planned post could not go out: {str(e)[:200]}")
    return {"sent": sent, "failed": failed}
