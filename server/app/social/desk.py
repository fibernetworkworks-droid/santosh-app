"""v0.353 THE SOCIAL MEDIA MANAGER, Phase 1 of docs/SOCIAL_EMPLOYEE_PLAN.md: hire -> set up -> connect Instagram /
Facebook Page (official Meta sign-in, tokens sealed) -> read her last posts and their numbers -> frozen BASELINE ->
STRATEGY (pillars, rhythm, languages, hashtags) + a 30-day CALENDAR of post drafts for her approval.

Phase 1 is read + draft only: nothing is published, no comment is answered. The 24/7 loop (run_due, from the worker,
only while the employee is hired and not paused): hourly - tokens alive and refreshed before they end; daily - fresh
numbers for her recent posts; weekly - a short note on what worked; first run as soon as an account is connected."""
from __future__ import annotations

import json
import logging
import secrets
import threading
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, new_id, now, session
from . import meta as M

log = logging.getLogger("santosh.social")
KEY = "social"
PLATFORMS = ("instagram", "facebook")
FORMATS = ("reel", "carousel", "image", "story")
POST_STATUS = ("draft", "approved", "skipped")
_RUNNING: set[str] = set()
_RUN_LOCK = threading.Lock()
_LAST_SWEEP = {"at": 0.0}


class SocialError(Exception):
    pass


class SocialAccount(Base):
    """One connected Instagram professional account or Facebook Page. Tokens sealed (accounts.encrypt)."""
    __tablename__ = "social_accounts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(12), default="instagram")
    account_id: Mapped[str] = mapped_column(String(64), default="", index=True)    # IG user id / Page id
    meta_user_id: Mapped[str] = mapped_column(String(64), default="", index=True)  # for Meta's data-deletion callback
    handle: Mapped[str] = mapped_column(String(120), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    picture: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(30), default="")                       # BUSINESS / CREATOR / Page category
    followers: Mapped[int] = mapped_column(Integer, default=0)
    token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)        # Facebook: the 60-day user token
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="ok")                  # ok | expired | error
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocialMedia(Base):
    """Her published posts as read from the platform, with their numbers (upserted by media id)."""
    __tablename__ = "social_media"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    account: Mapped[str] = mapped_column(String(40), index=True)                   # SocialAccount.id
    platform: Mapped[str] = mapped_column(String(12), default="")
    media_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    fmt: Mapped[str] = mapped_column(String(12), default="image")                  # reel | carousel | image | video | text
    caption: Mapped[str] = mapped_column(Text, default="")
    permalink: Mapped[str] = mapped_column(Text, default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int | None] = mapped_column(Integer, nullable=True)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocialDesk(Base):
    __tablename__ = "social_desk"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile: Mapped[str] = mapped_column(Text, default="{}")        # business, city, sells, customers, languages, goal
    strategy: Mapped[str] = mapped_column(Text, default="{}")       # pillars, rhythm, hashtags, best hours, goal metric
    baseline: Mapped[str] = mapped_column(Text, default="{}")
    baseline_at: Mapped[str] = mapped_column(String(20), default="")
    latest: Mapped[str] = mapped_column(Text, default="{}")
    stamps: Mapped[str] = mapped_column(Text, default="{}")
    state: Mapped[str] = mapped_column(String(16), default="new")   # new | first_run | ready | error
    calendar_status: Mapped[str] = mapped_column(String(12), default="none")   # none | draft | approved
    settings: Mapped[str | None] = mapped_column(Text, nullable=True)            # v0.365 {paused, pause_reason, quiet}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocialPost(Base):
    """One calendar slot: a post draft for her approval (Phase 2 adds publishing)."""
    __tablename__ = "social_posts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    slot: Mapped[str] = mapped_column(String(20), default="")       # local ISO date-time "2026-11-05T19:00"
    platforms: Mapped[str] = mapped_column(String(40), default="instagram")      # comma list
    fmt: Mapped[str] = mapped_column(String(12), default="image")
    pillar: Mapped[str] = mapped_column(String(60), default="")
    hook: Mapped[str] = mapped_column(String(200), default="")
    caption: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[str] = mapped_column(Text, default="[]")
    visual: Mapped[str] = mapped_column(Text, default="")
    cta: Mapped[str] = mapped_column(String(160), default="")
    language: Mapped[str] = mapped_column(String(20), default="")
    occasion: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(12), default="draft")   # draft | approved | skipped | publishing | published | failed | missed
    source: Mapped[str] = mapped_column(String(8), default="rules")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    media: Mapped[str | None] = mapped_column(Text, nullable=True)               # v0.355 [SocialAsset ids]
    approved_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)  # v0.355 exactly what she approved
    result: Mapped[str | None] = mapped_column(Text, nullable=True)              # v0.355 {platform: {id, link} | {error}}
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seen: Mapped[int | None] = mapped_column(Integer, nullable=True)   # v0.365 1 = she OK'd this post itself, 0 = only via the plan


class SocialEvent(Base):
    __tablename__ = "social_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="run")    # alert | recovered | run | note | connect
    level: Mapped[str] = mapped_column(String(6), default="info")   # bad | warn | info | ok
    text: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()
TABLES = (SocialAccount, SocialMedia, SocialDesk, SocialPost, SocialEvent)   # + publish.SocialAsset (v0.355)


def ensure_tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for t in TABLES:
            t.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except ValueError:
        return default


def _hired(tenant: str) -> None:
    from ..employee import hire
    if not hire.is_hired(tenant, KEY):
        raise SocialError("Social Media Manager abhi hired nahi hai. Employees mein jaakar hire kijiye.")


def _event(tenant: str, kind: str, level: str, text: str) -> None:
    with session() as s:
        s.add(SocialEvent(tenant_id=tenant, kind=kind, level=level, text=text[:600]))


def _desk(s, tenant: str) -> SocialDesk:
    d = s.get(SocialDesk, tenant)
    if d is None:
        d = SocialDesk(tenant_id=tenant)
        s.add(d)
        s.flush()
    return d


def _local(tenant: str) -> datetime:
    from ..life import tz_of
    return datetime.now(tz_of(tenant))


# ---------------------------------------------------------------- set-up
def profile_defaults(tenant: str) -> dict[str, Any]:
    """Pre-fill the set-up from what Hoola already knows (SEO site, Brand kit, Kalam voice)."""
    out: dict[str, Any] = {}
    try:
        from ..seo import service as SEO
        sites = SEO.sites(tenant)
        if sites:
            out.update(business=sites[0].get("name") or "", city=(sites[0].get("business") or {}).get("city", ""),
                       sells=", ".join(sites[0].get("services") or [])[:200], website=sites[0].get("url", ""))
    except Exception:            # noqa: BLE001 - a missing module / table never blocks set-up
        pass
    try:
        from ..brand import service as BR
        k = BR.kit(tenant) or {}
        out.setdefault("business", k.get("name") or "")
        if k.get("language"):
            out.setdefault("languages", [k["language"]])
    except Exception:            # noqa: BLE001
        pass
    return {k: v for k, v in out.items() if v}


def onboard(tenant: str, business: str = "", city: str = "", sells: str = "", customers: str = "", goal: str = "",
            languages: list[str] | None = None, trust: str = "", website: str = "", facts: str = "") -> dict[str, Any]:
    from ..employee import hire
    _hired(tenant)
    ensure_tables()
    if not str(business or "").strip():
        raise SocialError("Business ka naam bataiye.")
    langs = [str(x).strip()[:20] for x in (languages or ["Hinglish"]) if str(x).strip()][:4] or ["Hinglish"]
    prof = {"business": str(business).strip()[:120], "city": str(city).strip()[:80], "sells": str(sells).strip()[:300],
            "customers": str(customers).strip()[:300], "goal": str(goal).strip()[:200], "languages": langs,
            "website": str(website).strip()[:200], "facts": str(facts or "").strip()[:2000]}   # v0.364 reply facts
    with session() as s:
        d = _desk(s, tenant)
        d.profile = json.dumps(prof, ensure_ascii=False)
    if trust in hire.TRUST:
        hire.save_settings(tenant, KEY, trust=trust)
    _event(tenant, "note", "info", "Set-up saved. Connect Instagram or your Facebook Page so I can read your posts.")
    return {"profile": prof}


# ---------------------------------------------------------------- connect (official Meta sign-in)
def is_link_state(state: str) -> bool:
    return (state or "").startswith("soc_")


def connect_url(tenant: str, platform: str) -> str:
    from ..db import MailLinkState
    _hired(tenant)
    if platform not in PLATFORMS:
        raise SocialError("platform: instagram | facebook")
    if not M.configured(platform):
        raise SocialError("Server par Meta app ki keys abhi nahi lagi (.env: " +
                          ("INSTAGRAM_APP_ID / INSTAGRAM_APP_SECRET" if platform == "instagram" else "META_APP_ID / META_APP_SECRET")
                          + ", PUBLIC_BASE_URL).")
    state = f"soc_{platform[:2]}_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider=f"social_{platform[:2]}"))
    return M.ig_auth_url(state) if platform == "instagram" else M.fb_auth_url(state)


def _take_state(state: str, platform: str) -> str:
    from ..db import MailLinkState, as_utc
    with session() as s:
        row = s.get(MailLinkState, state)
        if row is None or row.provider != f"social_{platform[:2]}" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise SocialError("Yeh link purana ho gaya. Social Desk se dobara Connect dabaiye.")
        tenant = row.tenant_id
        s.delete(row)
    return tenant


def finish_link(platform: str, code: str, state: str, background: bool = True) -> dict[str, Any]:
    """The platform sent her back with a code: exchange it, read who she connected, keep the account(s)."""
    from .. import accounts as acc
    tenant = _take_state(state, platform)
    ensure_tables()
    added: list[str] = []
    try:
        if platform == "instagram":
            tok = M.ig_exchange(code)
            prof = M.ig_profile(tok["access_token"])
            if str(prof.get("account_type") or "").upper() not in ("", "BUSINESS", "MEDIA_CREATOR", "CREATOR"):
                raise SocialError("Yeh Instagram account professional nahi hai. Instagram Settings > Account type > "
                                  "Switch to professional account (free), phir dobara connect kijiye.")
            with session() as s:
                row = _upsert_account(s, tenant, "instagram", str(prof.get("user_id") or prof.get("id") or tok["user_id"]))
                row.meta_user_id = tok.get("user_id") or row.account_id
                row.handle = "@" + str(prof.get("username") or "")
                row.name = str(prof.get("name") or prof.get("username") or "")[:200]
                row.picture = str(prof.get("profile_picture_url") or "")
                row.kind = str(prof.get("account_type") or "")
                row.followers = int(prof.get("followers_count") or 0)
                row.token_enc = acc.encrypt(tok["access_token"])
                row.expires_at = now() + timedelta(seconds=tok["expires_in"])
                row.scopes = ",".join(tok.get("scopes") or [])
                row.status, row.last_error = "ok", ""
                added.append(row.handle)
        else:
            tok = M.fb_exchange(code)
            pages = M.fb_pages(tok["access_token"])
            try:                                   # v0.364 which permissions she granted (inbox needs engagement + messaging)
                granted = ",".join(str(x) for x in (M.fb_debug_token(tok["access_token"]).get("scopes") or []))
            except M.MetaError:
                granted = ""
            if not pages:
                raise SocialError("Koi Facebook Page nahi mila. Login mein Page chuniye (aap us Page ki admin hon).")
            with session() as s:
                for p in pages[:10]:
                    row = _upsert_account(s, tenant, "facebook", str(p["id"]))
                    row.meta_user_id = tok["user_id"]
                    row.handle = str(p.get("name") or "")[:120]
                    row.name = str(p.get("name") or "")[:200]
                    row.picture = str(((p.get("picture") or {}).get("data") or {}).get("url") or "")
                    row.kind = str(p.get("category") or "")[:30]
                    row.followers = int(p.get("followers_count") or p.get("fan_count") or 0)
                    row.token_enc = acc.encrypt(p["access_token"])
                    row.user_token_enc = acc.encrypt(tok["access_token"])
                    row.expires_at = now() + timedelta(seconds=tok["expires_in"])
                    row.scopes = granted
                    row.status, row.last_error = "ok", ""
                    added.append(row.name)
    except M.MetaError as e:
        raise SocialError(str(e))
    _event(tenant, "connect", "ok", f"Connected {platform.title()}: {', '.join(added)}.")
    with session() as s:
        d = _desk(s, tenant)
        first = d.state in ("new", "error")
    if first:
        if background:
            threading.Thread(target=run_now, args=(tenant, "first"), daemon=True).start()
        else:
            first_run(tenant)
    else:                                      # v0.364 a second account: read its posts now (not at tomorrow's 7 am)
        with session() as s:
            ids = [a.id for a in s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant,
                                                                       SocialAccount.platform == platform)).all()]

        def _read_new() -> None:
            for aid in ids:
                try:
                    sync_account(aid)
                except Exception as e:   # noqa: BLE001 - the daily read tries again
                    log.info("social sync after connect failed: %s", e)
        if background:
            threading.Thread(target=_read_new, daemon=True).start()
        else:
            _read_new()
    return {"platform": platform, "accounts": added}


def _upsert_account(s, tenant: str, platform: str, account_id: str) -> SocialAccount:
    row = s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant, SocialAccount.platform == platform,
                                                SocialAccount.account_id == account_id)).first()
    if row is None:
        row = SocialAccount(tenant_id=tenant, platform=platform, account_id=account_id)
        s.add(row)
    return row


def disconnect(tenant: str, account: str) -> dict[str, Any]:
    with session() as s:
        row = s.get(SocialAccount, account)
        if row is None or row.tenant_id != tenant:
            raise SocialError("Yeh account nahi mila.")
        name = row.handle or row.name
        for m in s.scalars(select(SocialMedia).where(SocialMedia.account == row.id)).all():
            s.delete(m)
        s.delete(row)
    _event(tenant, "note", "info", f"Disconnected {name}. Its token and read posts are deleted.")
    return {"removed": name}


def meta_deletion(signed_request: str) -> dict[str, Any]:
    """Meta's data-deletion / deauthorize callback: delete every account (and its read posts) of that Meta user."""
    payload = M.parse_signed_request(signed_request)
    uid = str(payload.get("user_id") or "")
    code = "hoola-" + secrets.token_hex(6)
    removed = 0
    ensure_tables()
    if uid:
        with session() as s:
            rows = s.scalars(select(SocialAccount).where((SocialAccount.meta_user_id == uid) | (SocialAccount.account_id == uid))).all()
            for row in rows:
                for m in s.scalars(select(SocialMedia).where(SocialMedia.account == row.id)).all():
                    s.delete(m)
                s.add(SocialEvent(tenant_id=row.tenant_id, kind="note", level="warn",
                                  text=f"{row.handle or row.name} was removed from Hoola in your Meta settings; its data is deleted."))
                s.delete(row)
                removed += 1
    return {"confirmation_code": code, "removed": removed}


def _inbox_ok(a) -> dict[str, bool]:
    from .inbox import can_read
    return can_read(a)


def accounts(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [{"id": a.id, "platform": a.platform, "handle": a.handle, "name": a.name, "picture": a.picture, "kind": a.kind,
                 "followers": a.followers, "status": a.status, "error": a.last_error,
                 "can_post": a.platform != "instagram" or not a.scopes or M.IG_PUBLISH_SCOPE in (a.scopes or "").split(","),
                 "can_reply": all(_inbox_ok(a).values()),
                 "expires_at": as_utc(a.expires_at).isoformat() if a.expires_at else "",
                 "last_sync": as_utc(a.last_sync).isoformat() if a.last_sync else ""}
                for a in s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant).order_by(SocialAccount.connected_at)).all()]


# ---------------------------------------------------------------- reading her posts
_FMT_IG = {"REELS": "reel", "CAROUSEL_ALBUM": "carousel", "IMAGE": "image", "VIDEO": "video", "STORY": "story"}


def sync_account(account: str, limit: int = 50, insights: bool = True) -> dict[str, Any]:
    """Read the latest posts of one account with their numbers. A dead token marks the account and alerts once."""
    from .. import accounts as acc
    with session() as s:
        a = s.get(SocialAccount, account)
        if a is None:
            raise SocialError("Account nahi mila.")
        tenant, platform, pid, tok = a.tenant_id, a.platform, a.account_id, acc.decrypt(a.token_enc) or ""
    got: list[dict[str, Any]] = []
    try:
        if platform == "instagram":
            prof = M.ig_profile(tok)
            for m in M.ig_media(tok, limit):
                fmt = _FMT_IG.get(str(m.get("media_product_type") or ""), _FMT_IG.get(str(m.get("media_type") or ""), "image"))
                if m.get("media_type") == "CAROUSEL_ALBUM":
                    fmt = "carousel"
                ins = M.ig_media_insights(tok, m["id"]) if insights else {}
                got.append({"media_id": m["id"], "fmt": fmt, "caption": m.get("caption") or "", "permalink": m.get("permalink") or "",
                            "posted_at": m.get("timestamp"), "likes": int(m.get("like_count") or 0),
                            "comments": int(m.get("comments_count") or 0), "shares": ins.get("shares", 0),
                            "saves": ins.get("saved", 0), "reach": ins.get("reach"), "views": ins.get("views")})
            followers = int(prof.get("followers_count") or 0)
        else:
            for p in M.fb_posts(pid, tok, limit):
                reach = M.fb_post_reach(p["id"], tok) if insights else None
                got.append({"media_id": p["id"], "fmt": "video" if "video" in str(p.get("status_type") or "") else
                            "image" if "photo" in str(p.get("status_type") or "") else "text",
                            "caption": p.get("message") or "", "permalink": p.get("permalink_url") or "",
                            "posted_at": p.get("created_time"),
                            "likes": int(((p.get("reactions") or {}).get("summary") or {}).get("total_count") or 0),
                            "comments": int(((p.get("comments") or {}).get("summary") or {}).get("total_count") or 0),
                            "shares": int((p.get("shares") or {}).get("count") or 0), "saves": 0, "reach": reach, "views": None})
            followers = None
    except M.MetaError as e:
        dead = getattr(e, "code", None) == 190
        with session() as s:
            a = s.get(SocialAccount, account)
            was = a.status if a else "ok"
            if a:
                a.status, a.last_error = ("expired" if dead else "error"), str(e)[:300]
        if was == "ok":
            _event(tenant, "alert", "bad", (f"{platform.title()} connection has ended. Please connect it again on the Social Desk."
                                            if dead else f"Could not read {platform.title()}: {str(e)[:160]}"))
        raise SocialError(str(e))
    with session() as s:
        if s.get(SocialAccount, account) is None:      # removed (by her or Meta's deletion callback) while we were reading
            return {"account": account, "posts": 0, "removed": True}
        have = {m.media_id: m for m in s.scalars(select(SocialMedia).where(SocialMedia.account == account)).all()}
        for g in got:
            row = have.get(g["media_id"]) or SocialMedia(tenant_id=tenant, account=account, platform=platform, media_id=g["media_id"])
            s.add(row)
            row.fmt, row.caption, row.permalink = g["fmt"], g["caption"][:2200], g["permalink"][:500]
            row.posted_at = _parse_time(g["posted_at"])
            row.likes, row.comments, row.shares, row.saves = g["likes"], g["comments"], g["shares"], g["saves"]
            row.reach, row.views, row.fetched_at = g["reach"], g["views"], now()
        a = s.get(SocialAccount, account)
        was_bad = bool(a and a.status != "ok")
        if a:
            if followers is not None:
                a.followers = followers
            a.status, a.last_error, a.last_sync = "ok", "", now()
    if was_bad:
        _event(tenant, "recovered", "ok", f"{platform.title()} is reading again.")
    return {"account": account, "posts": len(got)}


def _parse_time(v: Any) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00").replace("+0000", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------- baseline
def _eng(m: SocialMedia) -> int:
    return int(m.likes or 0) + int(m.comments or 0) + int(m.shares or 0) + int(m.saves or 0)


def measure(tenant: str) -> dict[str, Any]:
    """Numbers from what was read: followers, posts in 30 days, reach + engagement per post, best formats / hours / days, top posts."""
    from ..life import tz_of
    tz = tz_of(tenant)
    with session() as s:
        accs = s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant)).all()
        media = s.scalars(select(SocialMedia).where(SocialMedia.tenant_id == tenant)).all()
        acc_view = [{"platform": a.platform, "handle": a.handle or a.name, "followers": a.followers} for a in accs]
        rows = [{"platform": m.platform, "fmt": m.fmt, "eng": _eng(m), "reach": m.reach, "likes": m.likes, "comments": m.comments,
                 "saves": m.saves, "shares": m.shares, "caption": (m.caption or "")[:140], "permalink": m.permalink,
                 "at": as_utc(m.posted_at) if m.posted_at else None} for m in media]
    out: dict[str, Any] = {"accounts": acc_view, "followers": sum(a["followers"] for a in acc_view), "posts_read": len(rows),
                           "date": _local(tenant).date().isoformat()}
    if not rows:
        return out
    cut = now() - timedelta(days=30)
    out["posts_30d"] = sum(1 for r in rows if r["at"] and r["at"] >= cut)
    reach = [r["reach"] for r in rows if isinstance(r["reach"], int) and r["reach"] > 0]
    out["avg_eng"] = round(sum(r["eng"] for r in rows) / len(rows), 1)
    if reach:
        out["avg_reach"] = round(sum(reach) / len(reach))
        er = [r["eng"] / r["reach"] for r in rows if isinstance(r["reach"], int) and r["reach"] > 0]
        out["eng_rate"] = round(100 * sum(er) / len(er), 2)
    elif out["followers"]:
        out["eng_rate"] = round(100 * out["avg_eng"] / out["followers"], 2)
    by_fmt: dict[str, list[int]] = defaultdict(list)
    by_hour: dict[int, list[int]] = defaultdict(list)
    by_day: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        by_fmt[r["fmt"]].append(r["eng"])
        if r["at"]:
            loc = r["at"].astimezone(tz)
            by_hour[loc.hour].append(r["eng"])
            by_day[loc.weekday()].append(r["eng"])
    avg = lambda xs: sum(xs) / len(xs)                                              # noqa: E731
    out["formats"] = [{"fmt": f, "posts": len(v), "avg_eng": round(avg(v), 1)} for f, v in
                      sorted(by_fmt.items(), key=lambda kv: -avg(kv[1]))]
    good_hours = [h for h, v in sorted(by_hour.items(), key=lambda kv: -avg(kv[1])) if len(v) >= 2][:3]
    out["best_hours"] = good_hours or [12, 19]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    out["best_days"] = [days[d] for d, v in sorted(by_day.items(), key=lambda kv: -avg(kv[1])) if len(v) >= 2][:3]
    top = sorted(rows, key=lambda r: -r["eng"])[:5]
    out["top_posts"] = [{"platform": r["platform"], "fmt": r["fmt"], "eng": r["eng"], "reach": r["reach"], "caption": r["caption"],
                         "permalink": r["permalink"], "date": r["at"].date().isoformat() if r["at"] else ""} for r in top]
    return out


# ---------------------------------------------------------------- strategy + 30-day calendar
PLAN_SYSTEM = """You are the senior social media strategist at a top Indian agency, planning one month for a small Indian
business from its REAL numbers. Decide 3-5 content pillars from what the business sells and what worked for it, a rhythm
it can keep (3-5 feed posts a week; Reels lead reach, carousels lead saves), the posting times from its best hours, the
languages it asked for, and 8-15 hashtags (local + niche + brand; no banned or spammy tags, no 30-tag walls). Then a
30-day calendar: each slot one concrete post a person can make - format, pillar, a scroll-stopping hook (first line),
the caption in the asked language (Hinglish = Roman Hindi mixed with English), 3-8 hashtags from the set, a short brief
for the picture / video, one call to action (WhatsApp / call / visit / DM). Use Indian festivals and local moments given.
NEVER invent prices, offers, discounts, awards, years in business or claims that are not in the facts - write
"[price]" or leave the claim out. No fake urgency. Be warm and human, not salesy."""

PLAN_FIELDS = ('Reply JSON: {"pillars": [{"name": "...", "why": "one line"}], "rhythm": {"feed_per_week": 3-5, '
               '"stories_per_week": 0-7, "reels_share": 0-1}, "goal_metric": "the one number this month is judged on", '
               '"hashtags": ["#..."], "best_hours": [hour 0-23], "posts": [{"date": "YYYY-MM-DD", "time": "HH:MM", '
               '"platforms": ["instagram","facebook"], "format": "reel|carousel|image|story", "pillar": "...", '
               '"hook": "...", "caption": "...", "hashtags": ["#..."], "visual": "brief", "cta": "...", '
               '"occasion": "festival or empty"}]}')

PILLARS_DEFAULT = [("Our work", "Show the product / service in action - what customers actually get."),
                   ("Tips & how-to", "Useful, saveable advice from her expertise."),
                   ("Happy customers", "Reviews, results and real stories (with permission)."),
                   ("Behind the scenes", "The team, the place, the making - builds trust."),
                   ("Offers & festivals", "Seasonal posts and offers she actually runs.")]


def _occasions(tenant: str, start, days: int = 30) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        from ..india.days import holidays_for
        for y in {start.year, (start + timedelta(days=days)).year}:
            for h in holidays_for(y) or []:
                d = str(h.get("date") or "")[:10]
                if start.isoformat() <= d <= (start + timedelta(days=days)).isoformat():
                    out[d] = str(h.get("name") or "")[:80]
    except Exception:            # noqa: BLE001 - the holidays package is optional
        pass
    return out


def _plan_inputs(tenant: str) -> dict[str, Any]:
    with session() as s:
        d = _desk(s, tenant)
        prof, base = _j(d.profile, {}), _j(d.baseline, {})
    start = (_local(tenant) + timedelta(days=1)).date()
    try:
        from ..kalam import service as KS
        facts = (KS.settings(tenant) or {}).get("facts") or []
    except Exception:            # noqa: BLE001
        facts = []
    return {"business": prof, "baseline": {k: base.get(k) for k in ("followers", "posts_30d", "avg_reach", "eng_rate", "formats",
                                                                     "best_hours", "best_days", "top_posts")},
            "facts": facts[:20] if isinstance(facts, list) else [], "start": start.isoformat(), "days": 30,
            "occasions": _occasions(tenant, start), "best_times": _best_times(tenant)}


def _best_times(tenant: str) -> dict[str, Any]:
    try:
        from .pulse import best_times
        bt = best_times(tenant)
        return {"slots": bt["slots"][:3], "by_day": bt["by_day"], "sure": bt["sure"]}
    except Exception:            # noqa: BLE001
        return {}


def _rules_plan(inp: dict[str, Any]) -> dict[str, Any]:
    """The month without a model: 4 posts a week at her best hours, pillars rotated, festivals on their day."""
    from datetime import date
    prof, base = inp["business"], inp["baseline"]
    biz, city = prof.get("business") or "Hum", prof.get("city") or ""
    lang = (prof.get("languages") or ["Hinglish"])[0]
    hours = base.get("best_hours") or [12, 19]
    fmts = [f["fmt"] for f in base.get("formats") or [] if f.get("fmt") in FORMATS][:2] or ["reel", "carousel"]
    tag = lambda s: "#" + "".join(ch for ch in s.title() if ch.isalnum())                           # noqa: E731
    tags = [t for t in [tag(city) if city else "", tag(biz), tag(city + " " + (prof.get("sells") or "").split(",")[0]) if city else "",
                        "#SmallBusiness", "#MadeInIndia", "#ShopLocal"] if len(t) > 2][:8]
    start = date.fromisoformat(inp["start"])
    posts, k = [], 0
    for i in range(inp["days"]):
        dt = start + timedelta(days=i)
        occ = inp["occasions"].get(dt.isoformat(), "")
        if not occ and dt.weekday() not in (0, 2, 4, 5):
            continue
        name, why = PILLARS_DEFAULT[4] if occ else PILLARS_DEFAULT[k % 4]
        k += 0 if occ else 1
        fmt = "image" if occ else fmts[k % len(fmts)] if k % 3 else "carousel"
        hook = (f"{occ} ki dher saari shubhkaamnayein!" if occ else
                {"Our work": f"{biz} mein aaj kya bana? 👀", "Tips & how-to": "Yeh 3 baatein zaroor jaan lijiye",
                 "Happy customers": "Hamare graahak kya kehte hain", "Behind the scenes": f"{biz} ke peeche ki kahani"}[name])
        bt = inp.get("best_times") or {}
        h = (bt.get("by_day") or {}).get(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]) \
            if bt.get("sure") in ("medium", "high") else None
        posts.append({"date": dt.isoformat(), "time": f"{h if h is not None else hours[k % len(hours)]:02d}:00",
                      "platforms": ["instagram", "facebook"],
                      "format": fmt, "pillar": name, "hook": hook,
                      "caption": f"{hook}\n\n{why}\n\n{biz}{', ' + city if city else ''}. Details ke liye DM ya WhatsApp kijiye.",
                      "hashtags": tags[:5], "visual": f"{name}: {why}", "cta": "DM / WhatsApp kijiye", "occasion": occ, "language": lang})
    return {"pillars": [{"name": n, "why": w} for n, w in PILLARS_DEFAULT], "rhythm": {"feed_per_week": 4, "stories_per_week": 3,
            "reels_share": 0.5}, "goal_metric": "Profile visits and WhatsApp / DM enquiries", "hashtags": tags, "best_hours": hours,
            "posts": posts}


def _clean_plan(raw: Any, inp: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("posts"), list):
        return None
    start, end = inp["start"], (datetime.fromisoformat(inp["start"]) + timedelta(days=inp["days"] + 1)).date().isoformat()
    lang = ((inp["business"].get("languages") or ["Hinglish"])[0])
    posts = []
    for p in raw["posts"][:45]:
        if not isinstance(p, dict) or not str(p.get("caption") or p.get("hook") or "").strip():
            continue
        d = str(p.get("date") or "")[:10]
        if not (start <= d <= end):
            continue
        t = str(p.get("time") or "12:00")[:5]
        if len(t) != 5 or not t[:2].isdigit() or not t[3:].isdigit() or int(t[:2]) > 23:
            t = "12:00"
        plats = [x for x in (p.get("platforms") or ["instagram"]) if x in PLATFORMS] or ["instagram"]
        tags = [("#" + str(h).lstrip("#")).replace(" ", "")[:40] for h in (p.get("hashtags") or [])][:10]
        posts.append({"date": d, "time": t, "platforms": plats, "format": p.get("format") if p.get("format") in FORMATS else "image",
                      "pillar": str(p.get("pillar") or "")[:60], "hook": str(p.get("hook") or "")[:200],
                      "caption": str(p.get("caption") or "")[:2200], "hashtags": tags, "visual": str(p.get("visual") or "")[:400],
                      "cta": str(p.get("cta") or "")[:160], "occasion": str(p.get("occasion") or "")[:80], "language": lang})
    if len(posts) < 6:
        return None
    pillars = [{"name": str(x.get("name") or "")[:60], "why": str(x.get("why") or "")[:200]} for x in raw.get("pillars") or []
               if isinstance(x, dict) and x.get("name")][:6]
    rh = raw.get("rhythm") if isinstance(raw.get("rhythm"), dict) else {}
    return {"pillars": pillars or [{"name": n, "why": w} for n, w in PILLARS_DEFAULT],
            "rhythm": {"feed_per_week": max(1, min(14, int(rh.get("feed_per_week") or 4))),
                       "stories_per_week": max(0, min(14, int(rh.get("stories_per_week") or 3))),
                       "reels_share": max(0.0, min(1.0, float(rh.get("reels_share") or 0.5)))},
            "goal_metric": str(raw.get("goal_metric") or "")[:160],
            "hashtags": [("#" + str(h).lstrip("#")).replace(" ", "")[:40] for h in raw.get("hashtags") or []][:15],
            "best_hours": [int(h) for h in raw.get("best_hours") or [] if isinstance(h, int) and 0 <= h <= 23][:3]
            or inp["baseline"].get("best_hours") or [12, 19], "posts": posts}


def build_plan(tenant: str, ask: Any = None) -> dict[str, Any]:
    """Opus writes the strategy + 30 days from her real numbers; the rules plan when Opus is off / slow / unusable. A new
    plan replaces only DRAFT slots - what she approved stays."""
    from ..config import get_settings
    ensure_tables()
    inp = _plan_inputs(tenant)
    plan, source = None, "rules"
    st = get_settings()
    if ask is not None or (getattr(st, "social_ai", True) and st.anthropic_api_key):
        try:
            from ..docstudio.htmlpdf import _ask_opus
            raw = (ask or _ask_opus)(PLAN_SYSTEM, json.dumps(inp, ensure_ascii=False, default=str)[:12000] + "\n\n" + PLAN_FIELDS,
                                     "social_plan", None, 150.0, max_tokens=12000)
            plan = _clean_plan(raw, inp)
            source = "opus" if plan else "rules"
        except Exception as e:   # noqa: BLE001
            log.info("social plan model skipped: %s", e)
    plan = plan or _clean_plan(_rules_plan(inp), inp) or _rules_plan(inp)
    with session() as s:
        for old in s.scalars(select(SocialPost).where(SocialPost.tenant_id == tenant, SocialPost.status == "draft")).all():
            s.delete(old)
        for p in plan["posts"]:
            s.add(SocialPost(tenant_id=tenant, slot=f"{p['date']}T{p['time']}", platforms=",".join(p["platforms"]), fmt=p["format"],
                             pillar=p["pillar"], hook=p["hook"], caption=p["caption"],
                             hashtags=json.dumps(p["hashtags"], ensure_ascii=False), visual=p["visual"], cta=p["cta"],
                             language=p.get("language", ""), occasion=p.get("occasion", ""), status="draft", source=source))
        d = _desk(s, tenant)
        d.strategy = json.dumps({k: v for k, v in plan.items() if k != "posts"} | {"source": source}, ensure_ascii=False)
        if d.calendar_status != "approved":
            d.calendar_status = "draft"
    return {"posts": len(plan["posts"]), "source": source}


def calendar(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [{"id": p.id, "slot": p.slot, "platforms": p.platforms.split(","), "format": p.fmt, "pillar": p.pillar,
                 "hook": p.hook, "caption": p.caption, "hashtags": _j(p.hashtags, []), "visual": p.visual, "cta": p.cta,
                 "occasion": p.occasion, "status": p.status, "source": p.source, "media": _media_views(_j(p.media, [])),
                 "result": _j(p.result, {}), "error": p.error or "", "problems": _problems(p) if p.status in ("draft", "approved", "failed") else [],
                 "plan_only": p.status == "approved" and p.seen == 0}                # v0.365 OK'd via the plan, not one by one
                for p in s.scalars(select(SocialPost).where(SocialPost.tenant_id == tenant).order_by(SocialPost.slot)).all()]


def _media_views(ids: list[str]) -> list[dict[str, Any]]:
    from .publish import SocialError as _E, asset_view
    out = []
    for a in ids:
        try:
            out.append(asset_view(a))
        except _E:
            continue
    return out


def _problems(p) -> list[str]:
    from .publish import problems
    return problems(p)


def _stamp_ok(p) -> None:
    from .publish import post_hash
    p.approved_hash = post_hash(p)


def approve_calendar(tenant: str) -> dict[str, Any]:
    _hired(tenant)
    n = 0
    with session() as s:
        for p in s.scalars(select(SocialPost).where(SocialPost.tenant_id == tenant, SocialPost.status == "draft")).all():
            p.status = "approved"
            _stamp_ok(p)                           # v0.355 exactly this post (caption, pictures, time) is what she said yes to
            p.seen = 0                             # v0.365 OK'd as part of the plan only: trust decides if it goes alone
            n += 1
        _desk(s, tenant).calendar_status = "approved"
    from .pulse import trust_of
    how = ("Each one waits for your OK on its day (one tap)." if trust_of(tenant) not in ("saathi", "bharosa") else
           "Each goes out at its time once it has its picture; I tell you the same day.")
    _event(tenant, "note", "ok", f"You approved the calendar ({n} posts). {how} A post you change needs your OK again.")
    return {"approved": n}


def set_post(tenant: str, post_id: str, status: str = "", caption: str | None = None, hook: str | None = None,
             slot: str | None = None, hashtags: list[str] | None = None) -> dict[str, Any]:
    with session() as s:
        p = s.get(SocialPost, post_id)
        if p is None or p.tenant_id != tenant:
            raise SocialError("Yeh post nahi mila.")
        edited = False
        if caption is not None:
            p.caption, edited = str(caption)[:2200], True
        if hook is not None:
            p.hook, edited = str(hook)[:200], True
        if hashtags is not None:
            p.hashtags, edited = json.dumps([("#" + str(h).lstrip("#")).replace(" ", "")[:40] for h in hashtags][:15]), True
        if slot:
            try:
                datetime.fromisoformat(slot)
            except ValueError:
                raise SocialError("slot: YYYY-MM-DDTHH:MM")
            p.slot, edited = slot[:16], True
        if p.status in ("published", "publishing"):
            raise SocialError("Yeh post ja chuka hai; ise badla nahi ja sakta.")
        if status:
            if status not in POST_STATUS:
                raise SocialError("status: draft | approved | skipped")
            p.status = status
            p.approved_hash = ""
            if status == "approved":
                _stamp_ok(p)
                p.seen = 1                         # v0.365 her own OK for this one post
        elif edited and p.status in ("approved", "failed", "missed"):
            p.status, p.approved_hash = "draft", ""   # an edit after approval needs her OK again
        return {"id": p.id, "status": p.status}


# ---------------------------------------------------------------- the first run + 24/7 jobs
def _claim(key: str) -> bool:
    with _RUN_LOCK:
        if key in _RUNNING:
            return False
        _RUNNING.add(key)
        return True


def _release(key: str) -> None:
    with _RUN_LOCK:
        _RUNNING.discard(key)


def _sync_all(tenant: str, insights: bool = True) -> list[str]:
    errs = []
    with session() as s:
        ids = [a.id for a in s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant)).all()]
    for a in ids:
        try:
            sync_account(a, insights=insights)
        except SocialError as e:
            errs.append(str(e)[:160])
    return errs


def first_run(tenant: str, ask: Any = None) -> dict[str, Any]:
    """Read every connected account -> frozen baseline -> strategy + 30-day calendar draft."""
    if not _claim(f"{tenant}:first"):
        return {"state": "busy"}
    try:
        with session() as s:
            _desk(s, tenant).state = "first_run"
        errs = _sync_all(tenant)
        base = measure(tenant)
        with session() as s:
            d = _desk(s, tenant)
            d.baseline, d.baseline_at = json.dumps(base, ensure_ascii=False, default=str), now().isoformat(timespec="seconds")
            st0 = _j(d.stamps, {})
            st0["baseline_month"] = _local(tenant).strftime("%Y-%m")
            d.stamps = json.dumps(st0)
            d.latest = d.baseline
        plan = build_plan(tenant, ask=ask)
        with session() as s:
            _desk(s, tenant).state = "ready"
        _event(tenant, "run", "ok" if not errs else "warn",
               f"Read {base.get('posts_read', 0)} posts; baseline saved. A {plan['posts']}-post calendar for the next 30 days is ready for your OK."
               + (f" Some reads failed: {errs[0]}" if errs else ""))
        _publish(tenant, "Social calendar ready for your OK")
        return {"baseline": base, "plan": plan, "errors": errs}
    except Exception as e:       # noqa: BLE001
        log.exception("social first run failed")
        with session() as s:
            _desk(s, tenant).state = "error"
        _event(tenant, "run", "bad", f"First check stopped: {type(e).__name__}. I will try again in the next hour.")
        return {"state": "error", "error": str(e)[:300]}
    finally:
        _release(f"{tenant}:first")


def _publish(tenant: str, text: str) -> None:
    try:
        from ..events import bus
        bus.publish("", "social_update", {"tenant": tenant, "text": text})
    except Exception:            # noqa: BLE001
        pass


def watch(tenant: str) -> dict[str, Any]:
    """Hourly: refresh Instagram tokens with < 20 days left (>= 24 h old); warn once when a Facebook login nears its end."""
    from .. import accounts as acc
    out = {"refreshed": 0, "warned": 0}
    with session() as s:
        rows = [(a.id, a.platform, a.expires_at, a.connected_at, a.status, a.token_enc, a.handle or a.name)
                for a in s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant)).all()]
    for aid, plat, exp, conn, status, tok_enc, name in rows:
        if status != "ok" or exp is None:
            continue
        left = as_utc(exp) - now()
        if plat == "instagram" and left < timedelta(days=20) and now() - as_utc(conn) > timedelta(hours=24):
            try:
                r = M.ig_refresh(acc.decrypt(tok_enc) or "")
                with session() as s:
                    a = s.get(SocialAccount, aid)
                    a.token_enc = acc.encrypt(r["access_token"])
                    a.expires_at = now() + timedelta(seconds=r["expires_in"] or 60 * 86400)
                out["refreshed"] += 1
            except M.MetaError as e:
                _event(tenant, "alert", "warn", f"Could not renew the Instagram connection for {name}: {str(e)[:120]}")
        elif plat == "facebook" and left < timedelta(days=7):
            with session() as s:
                d = _desk(s, tenant)
                st = _j(d.stamps, {})
                if st.get(f"fbwarn_{aid}") != as_utc(exp).date().isoformat():
                    st[f"fbwarn_{aid}"] = as_utc(exp).date().isoformat()
                    d.stamps = json.dumps(st)
                    s.add(SocialEvent(tenant_id=tenant, kind="alert", level="warn",
                                      text=f"Facebook login for {name} ends in {max(0, left.days)} days. Tap Connect Facebook again to renew."))
                    out["warned"] += 1
    return out


def daily(tenant: str) -> dict[str, Any]:
    errs = _sync_all(tenant)
    latest = measure(tenant)
    with session() as s:
        _desk(s, tenant).latest = json.dumps(latest, ensure_ascii=False, default=str)
    return {"latest": latest, "errors": errs}


def _daily_and_boosts(tenant: str) -> dict[str, Any]:
    out = daily(tenant)
    try:
        from .pulse import flag_boosts
        out["boosts"] = flag_boosts(tenant)            # v0.365 boost-worthy posts, told once each
    except Exception as e:       # noqa: BLE001
        log.info("boost flags failed: %s", e)
    return out


def weekly(tenant: str) -> dict[str, Any]:
    m = measure(tenant)
    top = (m.get("top_posts") or [{}])[0]
    fm = (m.get("formats") or [{}])[0]
    if top:
        _event(tenant, "note", "info", f"This week: your best post was a {top.get('fmt')} ({top.get('eng')} interactions). "
               f"{str(fm.get('fmt') or '').title()}s are working best for you; best hours {', '.join(f'{h}:00' for h in m.get('best_hours') or [])}.")
    return m


def kpis(base: dict[str, Any], latest: dict[str, Any]) -> list[dict[str, Any]]:
    def k(name, key, better="up"):
        n, b = latest.get(key), base.get(key)
        ch = round((n - b) * 100 / abs(b)) if isinstance(n, (int, float)) and isinstance(b, (int, float)) and b else None
        return {"name": name, "now": n, "baseline": b, "change_pct": ch, "good": None if ch is None else (ch >= 0 if better == "up" else ch <= 0)}
    out = [k("Followers", "followers"), k("Posts in 30 days", "posts_30d"), k("Interactions per post", "avg_eng")]
    if base.get("avg_reach") is not None or latest.get("avg_reach") is not None:
        out.append(k("Reach per post", "avg_reach"))
    if base.get("eng_rate") is not None or latest.get("eng_rate") is not None:
        out.append(k("Engagement rate %", "eng_rate"))
    return out


def schedule_view(stamps: dict[str, str]) -> list[dict[str, str]]:
    return [{"job": "Post approved posts at their time", "every": "Every few minutes", "last": stamps.get("publish", "")},
            {"job": "Read comments + DMs, draft / send replies", "every": "Every 15 minutes", "last": stamps.get("inbox", "")},
            {"job": "Check connections, renew Instagram tokens", "every": "Every hour", "last": stamps.get("hourly", "")},
            {"job": "Fresh numbers for your recent posts", "every": "Every day, 7 am", "last": stamps.get("daily", "")},
            {"job": "Morning note (only when something needs you)", "every": "Every day, 9 am", "last": stamps.get("morning", "")},
            {"job": "Weekly pulse in your chat", "every": "Every Monday", "last": stamps.get("weekly", "")},
            {"job": "Monthly PDF report", "every": "1st of the month", "last": stamps.get("monthly", "")}]


def desk_view(tenant: str) -> dict[str, Any]:
    from ..employee import hire
    ensure_tables()
    st = hire.status(tenant, KEY)
    if st not in ("hired", "paused"):
        return {"hired": False, "status": st}
    trust = next((c.get("trust") for c in hire.catalog(tenant) if c["key"] == KEY), "seekh")
    with session() as s:
        d = s.get(SocialDesk, tenant)
        prof = _j(d.profile, {}) if d else {}
        info = {"state": d.state if d else "new", "calendar_status": d.calendar_status if d else "none",
                "baseline": _j(d.baseline, {}) if d else {}, "latest": _j(d.latest, {}) if d else {},
                "strategy": _j(d.strategy, {}) if d else {}, "baseline_at": d.baseline_at if d else "",
                "stamps": _j(d.stamps, {}) if d else {}}
        events = [{"kind": e.kind, "level": e.level, "text": e.text, "at": e.at.isoformat() if e.at else ""}
                  for e in s.scalars(select(SocialEvent).where(SocialEvent.tenant_id == tenant).order_by(SocialEvent.at.desc())).all()[:25]]
    return {"hired": True, "status": st, "trust": trust, "onboarded": bool(prof), "profile": prof or profile_defaults(tenant),
            "connect": {p: M.configured(p) for p in PLATFORMS}, "accounts": accounts(tenant), **info,
            "kpis": kpis(info["baseline"], info["latest"]), "calendar": calendar(tenant), "events": events,
            "schedule": schedule_view(info["stamps"]), "inbox": _inbox_counts(tenant), "pulse": _pulse_view(tenant)}


def _pulse_view(tenant: str) -> dict[str, Any]:
    from .pulse import view
    return view(tenant)


def _inbox_counts(tenant: str) -> dict[str, int]:
    from .inbox import counts
    return counts(tenant)


def due_jobs(tenant: str, at: datetime | None = None) -> list[str]:
    from ..life import tz_of
    local = (at or datetime.now(tz_of(tenant))).astimezone(tz_of(tenant))
    with session() as s:
        d = s.get(SocialDesk, tenant)
        stamps = _j(d.stamps, {}) if d else {}
        state = d.state if d else "new"
        has_acc = s.scalars(select(SocialAccount.id).where(SocialAccount.tenant_id == tenant)).first() is not None
    if not has_acc:
        return []
    out = ["publish"] if state == "ready" else []      # v0.355 every sweep (~4 min): approved posts whose time has come
    last_i = stamps.get("inbox", "")
    if state == "ready" and (not last_i or local - datetime.fromisoformat(last_i) >= timedelta(minutes=14)):
        out.append("inbox")                            # v0.364 comments + DMs every ~15 min
    if state in ("new", "error"):
        out.append("first")
    last_h = stamps.get("hourly", "")
    if not last_h or local - datetime.fromisoformat(last_h) >= timedelta(minutes=55):
        out.append("hourly")
    if state == "ready" and local.hour >= 7 and stamps.get("daily", "")[:10] != local.date().isoformat():
        out.append("daily")
    wk = f"{local.isocalendar()[0]}-W{local.isocalendar()[1]}"
    if state == "ready" and local.weekday() == 0 and local.hour >= 9 and stamps.get("weekly_key") != wk:
        out.append("weekly")
    if state == "ready" and local.hour >= 9 and stamps.get("morning", "")[:10] != local.date().isoformat():
        out.append("morning")                          # v0.365
    mk = local.strftime("%Y-%m")
    if state == "ready" and local.day == 1 and local.hour >= 9 and stamps.get("monthly_key") != mk and stamps.get("baseline_month") != mk:
        out.append("monthly")                          # v0.365 (not in the month the baseline was taken)
    return out


def run_job(tenant: str, job: str, at: datetime | None = None) -> dict[str, Any]:
    from ..life import tz_of
    local = (at or datetime.now(tz_of(tenant))).astimezone(tz_of(tenant))
    from .inbox import run_inbox
    from .publish import run_publisher
    from .pulse import monthly_report, morning, weekly_pulse
    fn = {"first": first_run, "hourly": watch, "daily": _daily_and_boosts, "weekly": weekly_pulse, "plan": build_plan,
          "publish": run_publisher, "inbox": run_inbox, "morning": morning, "monthly": monthly_report}.get(job)
    if fn is None:
        raise SocialError("job: first | hourly | daily | weekly | plan | publish | inbox | morning | monthly")
    res = fn(tenant)
    with session() as s:
        d = _desk(s, tenant)
        st = _j(d.stamps, {})
        st[job] = local.isoformat(timespec="seconds")
        if job == "weekly":
            st["weekly_key"] = f"{local.isocalendar()[0]}-W{local.isocalendar()[1]}"
        if job == "monthly":
            st["monthly_key"] = local.strftime("%Y-%m")
        d.stamps = json.dumps(st)
    return res


def run_now(tenant: str, job: str) -> None:
    try:
        run_job(tenant, job)
    except Exception as e:       # noqa: BLE001
        log.info("social run-now %s failed: %s", job, e)
        _event(tenant, "run", "warn", f"{job.title()} could not run: {str(e)[:200]}")


def run_due(at: datetime | None = None, force: bool = False) -> list[tuple[str, str]]:
    import time as _t
    if not force and _t.time() - _LAST_SWEEP["at"] < 240:
        return []
    _LAST_SWEEP["at"] = _t.time()
    from ..employee import hire
    ensure_tables()
    done = []
    for tenant in hire.working_tenants(KEY):
        for job in due_jobs(tenant, at):
            key = f"due:{tenant}:{job}"          # not the first run's own lock name, or a retry would find itself busy
            if not _claim(key):
                continue
            try:
                run_job(tenant, job, at)
                done.append((tenant, job))
            except Exception as e:   # noqa: BLE001
                log.exception("social job %s failed", job)
                _event(tenant, "run", "bad", f"{job} run stopped: {str(e)[:200]}")
            finally:
                _release(key)
    return done
