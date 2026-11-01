"""v0.370 SOCIAL MEDIA MANAGER Phase 5 of docs/SOCIAL_EMPLOYEE_PLAN.md - GROWTH (official routes only):
- Listening through her Facebook Page's linked Instagram professional account (hashtag search and Business Discovery exist
  only in the Instagram API with Facebook Login): posts that TAG her (daily), up to 5 hashtags of her niche and up to 5
  competitors (weekly: followers, posting rhythm, engagement, best format - against her own numbers). No scraping, no
  logging in as anyone, only public business / creator data Meta gives.
- UGC: a customer's post that tags her -> her tap asks permission with a comment from her account (the official mentions
  edge; never a DM to someone who did not write first) -> SHE marks "they said yes" with what they said -> Repost makes a
  credited calendar DRAFT (still needs her OK like every post). Hoola never reposts without a recorded yes.
- Collab check: any creator / business handle -> public numbers + the Influencer desk's fake-follower SIGNALS + the ASCI
  #ad rule for a paid collab caption.
- A/B hook styles: every planned post carries a hook style (question / number / story / offer); once posted, the numbers
  of each style are compared, and a winner is named only with >= 3 posts per style and a 20% lead."""
from __future__ import annotations

import json
import logging
import re
import statistics
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, new_id, now, session
from . import meta as M
from .desk import (SocialAccount, SocialDesk, SocialError, SocialEvent, SocialMedia, SocialPost, _desk, _eng, _hired, _j,
                   _local, ensure_tables, measure)

log = logging.getLogger("santosh.social.growth")
MAX_WATCH = 5
HOOK_STYLES = ("question", "number", "story", "offer")
_TAG = re.compile(r"^[A-Za-z0-9_ऀ-ॿ]{2,60}$")
_USER = re.compile(r"^[A-Za-z0-9._]{1,30}$")


class SocialWatch(Base):
    """A hashtag or a competitor she watches; `last` / `prev` = the latest two weekly snapshots."""
    __tablename__ = "social_watch"
    __table_args__ = (UniqueConstraint("tenant_id", "kind", "name", name="uq_social_watch"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="hashtag")      # hashtag | competitor
    name: Mapped[str] = mapped_column(String(80), default="")
    ref_id: Mapped[str] = mapped_column(String(64), default="")           # Meta hashtag id (searches are capped per week)
    last: Mapped[str] = mapped_column(Text, default="{}")
    prev: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SocialUgc(Base):
    """A post by someone else that tags her, and where its permission stands."""
    __tablename__ = "social_ugc"
    __table_args__ = (UniqueConstraint("tenant_id", "media_id", name="uq_social_ugc"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("su"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    media_id: Mapped[str] = mapped_column(String(80), default="")
    username: Mapped[str] = mapped_column(String(80), default="")
    caption: Mapped[str] = mapped_column(Text, default="")
    media_type: Mapped[str] = mapped_column(String(20), default="")
    media_url: Mapped[str] = mapped_column(Text, default="")
    permalink: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(10), default="new")       # new | asked | granted | refused | reposted | ignored
    asked_text: Mapped[str] = mapped_column(Text, default="")
    asked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proof: Mapped[str] = mapped_column(Text, default="")                  # what they said, as she recorded it
    post_id: Mapped[str] = mapped_column(String(40), default="")          # the credited draft
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_growth() -> None:
    from .. import db as _db
    ensure_tables()
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for t in (SocialWatch, SocialUgc):
            t.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ---------------------------------------------------------------- the Facebook-Login link to her Instagram
def link(tenant: str) -> dict[str, str]:
    """Her Page's linked Instagram professional account + tokens. Raises a plain SocialError when it is not there."""
    from .. import accounts as acc
    with session() as s:
        pages = s.scalars(select(SocialAccount).where(SocialAccount.tenant_id == tenant, SocialAccount.platform == "facebook",
                                                      SocialAccount.status == "ok").order_by(SocialAccount.connected_at)).all()
        rows = [(a.id, a.account_id, acc.decrypt(a.token_enc) or "", acc.decrypt(a.user_token_enc) or "", a.scopes or "") for a in pages]
        d = s.get(SocialDesk, tenant)
        cache = _j(d.stamps, {}).get("ig_link") if d else None
    if not rows:
        raise SocialError("Growth tools ke liye apna Facebook Page connect kijiye (jo aapke Instagram se juda ho). "
                          "Hashtag search aur competitor numbers Meta sirf is raaste se deta hai.")
    for aid, page, ptok, utok, scopes in rows:
        if scopes and not all(x in scopes.split(",") for x in ("instagram_basic",)):
            continue
        if isinstance(cache, dict) and cache.get("aid") == aid and cache.get("ig_id"):
            return {"aid": aid, "page": page, "ig_id": cache["ig_id"], "username": cache.get("username", ""), "token": ptok,
                    "user_token": utok or ptok}
        try:
            ig = M.fb_page_ig(page, ptok)
        except M.MetaError:
            continue
        if ig.get("id"):
            with session() as s:
                d = _desk(s, tenant)
                st = _j(d.stamps, {})
                st["ig_link"] = {"aid": aid, "ig_id": str(ig["id"]), "username": str(ig.get("username") or "")}
                d.stamps = json.dumps(st)
            return {"aid": aid, "page": page, "ig_id": str(ig["id"]), "username": str(ig.get("username") or ""), "token": ptok,
                    "user_token": utok or ptok}
    raise SocialError("Aapke Facebook Page se koi Instagram professional account juda nahi mila (ya Instagram ki permission "
                      "nahi di). Instagram Settings > Account > Sharing to other apps / Page se jodiye, phir Reconnect Facebook Page.")


# ---------------------------------------------------------------- what she watches
def set_watch(tenant: str, hashtags: list[str] | None = None, competitors: list[str] | None = None) -> dict[str, Any]:
    _hired(tenant)
    ensure_growth()

    def clean(xs, pat, strip):
        out = []
        for x in xs or []:
            x = str(x).strip().lstrip(strip)
            if not x:
                continue
            if not pat.match(x):
                raise SocialError(f"'{x}' sahi naam nahi hai.")
            if x.lower() not in [o.lower() for o in out]:
                out.append(x)
        if len(out) > MAX_WATCH:
            raise SocialError(f"Zyada se zyada {MAX_WATCH} (Meta ek hafte mein 30 hashtag search hi deta hai).")
        return out
    want = {}
    if hashtags is not None:
        want["hashtag"] = clean(hashtags, _TAG, "#")
    if competitors is not None:
        want["competitor"] = clean(competitors, _USER, "@")
    with session() as s:
        for kind, names in want.items():
            have = {w.name.lower(): w for w in s.scalars(select(SocialWatch).where(SocialWatch.tenant_id == tenant,
                                                                                   SocialWatch.kind == kind)).all()}
            for k, w in have.items():
                if k not in [n.lower() for n in names]:
                    s.delete(w)
            for n in names:
                if n.lower() not in have:
                    s.add(SocialWatch(tenant_id=tenant, kind=kind, name=n))
    return watch_view(tenant)


def watch_view(tenant: str) -> dict[str, Any]:
    ensure_growth()
    with session() as s:
        rows = s.scalars(select(SocialWatch).where(SocialWatch.tenant_id == tenant).order_by(SocialWatch.kind, SocialWatch.name)).all()
        out = {"hashtags": [], "competitors": []}
        for w in rows:
            v = {"id": w.id, "name": w.name, "last": _j(w.last, {}), "prev": _j(w.prev, {}), "error": w.error,
                 "updated": as_utc(w.updated_at).isoformat() if w.updated_at else ""}
            out["hashtags" if w.kind == "hashtag" else "competitors"].append(v)
    return out


# ---------------------------------------------------------------- reading
def _first_line(t: str) -> str:
    return (t or "").strip().split("\n")[0][:90]


def _media_stats(media: list[dict[str, Any]]) -> dict[str, Any]:
    eng = [int(m.get("like_count") or 0) + int(m.get("comments_count") or 0) for m in media]
    by: dict[str, list[int]] = {}
    for m, e in zip(media, eng):
        by.setdefault(str(m.get("media_type") or "IMAGE").replace("CAROUSEL_ALBUM", "CAROUSEL").lower(), []).append(e)
    fmts = sorted(({"fmt": k, "posts": len(v), "avg_eng": round(sum(v) / len(v), 1)} for k, v in by.items()), key=lambda x: -x["avg_eng"])
    return {"posts": len(media), "avg_eng": round(sum(eng) / len(eng), 1) if eng else 0, "formats": fmts}


def _hashtag(tenant: str, w: SocialWatch, lk: dict[str, str]) -> dict[str, Any]:
    hid = w.ref_id or M.ig_hashtag_id(lk["ig_id"], lk["user_token"], w.name)
    if not hid:
        raise SocialError("Meta ko yeh hashtag nahi mila.")
    top = M.ig_hashtag_top(hid, lk["ig_id"], lk["user_token"])
    st = _media_stats(top)
    best = sorted(top, key=lambda m: -(int(m.get("like_count") or 0) + int(m.get("comments_count") or 0)))[:3]
    st["ideas"] = [{"fmt": str(m.get("media_type") or "").lower(), "eng": int(m.get("like_count") or 0) + int(m.get("comments_count") or 0),
                    "line": _first_line(m.get("caption") or ""), "permalink": m.get("permalink") or ""} for m in best]
    st["ref_id"] = hid
    return st


def _competitor(tenant: str, w: SocialWatch, lk: dict[str, str]) -> dict[str, Any]:
    bd = M.ig_discover(lk["ig_id"], lk["token"], w.name)
    if not bd:
        raise SocialError("Yeh account Business / Creator nahi hai ya mila nahi; Meta sirf professional accounts ke numbers deta hai.")
    media = (bd.get("media") or {}).get("data") or []
    st = _media_stats(media)
    cut7, cut30 = now() - timedelta(days=7), now() - timedelta(days=30)
    times = [as_utc(datetime.strptime(str(m.get("timestamp"))[:19], "%Y-%m-%dT%H:%M:%S")) for m in media if m.get("timestamp")]
    fol = int(bd.get("followers_count") or 0)
    st.update({"username": bd.get("username") or w.name, "name": bd.get("name") or "", "followers": fol,
               "media_count": int(bd.get("media_count") or 0), "posts_7d": sum(1 for t in times if t >= cut7),
               "posts_30d": sum(1 for t in times if t >= cut30),
               "eng_rate": round(100 * st["avg_eng"] / fol, 2) if fol else None})
    return st


def listen(tenant: str, weekly: bool | None = None) -> dict[str, Any]:
    """Daily: posts that tag her. Weekly (Monday, or the first time): hashtags + competitors."""
    ensure_growth()
    try:
        lk = link(tenant)
    except SocialError as e:
        return {"ok": False, "reason": str(e)}
    out = {"ok": True, "ugc_new": 0, "watched": 0, "errors": []}
    try:
        for m in M.ig_tags(lk["ig_id"], lk["token"]):
            mid = str(m.get("id") or "")
            if not mid or (m.get("username") or "").lower() == lk["username"].lower():
                continue
            with session() as s:
                if s.scalars(select(SocialUgc.id).where(SocialUgc.tenant_id == tenant, SocialUgc.media_id == mid)).first():
                    continue
                ts = m.get("timestamp")
                s.add(SocialUgc(tenant_id=tenant, media_id=mid, username=str(m.get("username") or "")[:80],
                                caption=str(m.get("caption") or "")[:2000], media_type=str(m.get("media_type") or ""),
                                media_url=str(m.get("media_url") or ""), permalink=str(m.get("permalink") or ""),
                                at=as_utc(datetime.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S")) if ts else None,
                                likes=int(m.get("like_count") or 0)))
                out["ugc_new"] += 1
    except M.MetaError as e:
        out["errors"].append(f"tags: {str(e)[:160]}")
    if out["ugc_new"]:
        with session() as s:
            s.add(SocialEvent(tenant_id=tenant, kind="note", level="ok", text=(
                f"{out['ugc_new']} new post(s) by customers tag you. Ask before reposting - one tap sends a polite comment.")))
    if weekly is None:
        weekly = _local(tenant).weekday() == 0
    with session() as s:
        ids = [(w.id, w.kind, bool(w.updated_at)) for w in s.scalars(select(SocialWatch).where(SocialWatch.tenant_id == tenant)).all()]
    for wid, kind, seen in ids:
        if seen and not weekly:
            continue
        with session() as s:
            w = s.get(SocialWatch, wid)
            s.expunge(w)
        try:
            snap = _hashtag(tenant, w, lk) if kind == "hashtag" else _competitor(tenant, w, lk)
            err = ""
        except (M.MetaError, SocialError) as e:
            snap, err = None, str(e)[:300]
            out["errors"].append(f"{w.name}: {err[:120]}")
        with session() as s:
            w = s.get(SocialWatch, wid)
            if snap is not None:
                if kind == "hashtag" and snap.get("ref_id"):
                    w.ref_id = snap.pop("ref_id")
                snap["date"] = _local(tenant).date().isoformat()
                w.prev, w.last = w.last or "{}", json.dumps(snap, ensure_ascii=False)
                w.updated_at = now()
                out["watched"] += 1
            w.error = err
    if weekly and out["watched"]:
        note = competitor_note(tenant)
        if note:
            with session() as s:
                s.add(SocialEvent(tenant_id=tenant, kind="note", level="info", text=note[:600]))
    return out


def competitor_note(tenant: str) -> str:
    """One line: where she stands against the accounts she watches."""
    me = measure(tenant)
    comps = [c for c in watch_view(tenant)["competitors"] if c["last"].get("followers")]
    if not comps:
        return ""
    top = max(comps, key=lambda c: c["last"].get("avg_eng") or 0)
    my = me.get("avg_eng")
    bits = [f"Competitors: @{top['last'].get('username') or top['name']} gets {top['last'].get('avg_eng')} interactions a post"
            f" ({top['last'].get('posts_7d', 0)} posts this week, best format {((top['last'].get('formats') or [{}])[0]).get('fmt', '-')})"]
    if my is not None:
        bits.append(f"you get {my}")
    return "; ".join(bits) + "."


# ---------------------------------------------------------------- UGC permission flow (her taps)
def ugc_list(tenant: str) -> list[dict[str, Any]]:
    ensure_growth()
    with session() as s:
        return [{"id": u.id, "username": u.username, "caption": u.caption[:300], "media_type": u.media_type,
                 "permalink": u.permalink, "likes": u.likes, "status": u.status, "asked": u.asked_text, "proof": u.proof,
                 "post_id": u.post_id, "error": u.error, "at": as_utc(u.at).isoformat() if u.at else ""}
                for u in s.scalars(select(SocialUgc).where(SocialUgc.tenant_id == tenant).order_by(SocialUgc.created_at.desc())).all()[:40]]


def _ugc(s, tenant: str, uid: str) -> SocialUgc:
    u = s.get(SocialUgc, uid)
    if u is None or u.tenant_id != tenant:
        raise SocialError("Yeh post nahi mila.")
    return u


def ugc_ask(tenant: str, uid: str, text: str = "") -> dict[str, Any]:
    """Her tap: a polite public comment from her account asking to repost with credit (the official mentions edge)."""
    _hired(tenant)
    with session() as s:
        d = s.get(SocialDesk, tenant)
        biz = (_j(d.profile, {}) if d else {}).get("business") or "hum"
        u = _ugc(s, tenant, uid)
        if u.status in ("granted", "reposted"):
            raise SocialError("Permission pehle se mili hui hai.")
        mid, who = u.media_id, u.username
    body = (text or f"Bahut shukriya @{who}! 🙏 Kya {biz} ise apne page par aapke naam ke saath share kar sakta hai? "
                     "Agar haan, toh bas YES likh dijiye.").strip()[:600]
    lk = link(tenant)
    try:
        M.ig_mention_reply(lk["ig_id"], lk["token"], mid, body)
    except M.MetaError as e:
        with session() as s:
            _ugc(s, tenant, uid).error = str(e)[:300]
        raise SocialError(str(e))
    with session() as s:
        u = _ugc(s, tenant, uid)
        u.status, u.asked_text, u.asked_at, u.error = "asked", body, now(), ""
    return {"id": uid, "status": "asked"}


def ugc_permission(tenant: str, uid: str, granted: bool, proof: str = "") -> dict[str, Any]:
    """She records their answer. A yes needs what they said (their words / where), kept as the proof."""
    _hired(tenant)
    with session() as s:
        u = _ugc(s, tenant, uid)
        if granted and not str(proof or "").strip():
            raise SocialError("Unhone kya likha, woh likhiye (jaise: 'YES, share kar do' - comment par).")
        u.status = "granted" if granted else "refused"
        u.proof = str(proof or "").strip()[:500]
        return {"id": uid, "status": u.status}


def ugc_ignore(tenant: str, uid: str) -> dict[str, Any]:
    _hired(tenant)
    with session() as s:
        u = _ugc(s, tenant, uid)
        if u.status == "reposted":
            raise SocialError("Yeh pehle hi repost ho chuka.")
        u.status = "ignored"
        return {"id": uid, "status": "ignored"}


def ugc_repost(tenant: str, uid: str) -> dict[str, Any]:
    """Only with a recorded yes: their picture / video -> a credited calendar DRAFT (still needs her OK to go out)."""
    from .publish import add_asset
    _hired(tenant)
    with session() as s:
        u = _ugc(s, tenant, uid)
        if u.status != "granted":
            raise SocialError("Pehle unki permission chahiye (Ask, phir 'They said yes' unke jawab ke saath).")
        url, who, mtype, cap = u.media_url, u.username, u.media_type, u.caption
    if not url:
        raise SocialError("Meta ne is post ki file nahi di (carousel / purana post). Unse photo maang kar Add photo se daaliye.")
    c, own = M._client()
    try:
        r = c.get(url, timeout=60)
        r.raise_for_status()
        data = r.content
    except Exception as e:       # noqa: BLE001
        raise SocialError(f"Photo / video download nahi hua: {type(e).__name__}")
    finally:
        if own:
            c.close()
    a = add_asset(tenant, data, "ugc.mp4" if mtype == "VIDEO" else "ugc.jpg")
    slot = (_local(tenant) + timedelta(days=1)).replace(hour=19, minute=0).strftime("%Y-%m-%dT%H:%M")
    caption = (f"Hamare customer @{who} ka pyaar 💛 Thank you for sharing!\n\n📸 Credit: @{who}\n\n"
               f"{_first_line(cap)}").strip()
    with session() as s:
        p = SocialPost(tenant_id=tenant, slot=slot, platforms="instagram,facebook", fmt="reel" if mtype == "VIDEO" else "image",
                       pillar="Happy customers", hook=f"Customer love from @{who}", caption=caption[:2200],
                       hashtags=json.dumps([]), visual=f"Repost of @{who}'s post, with credit", cta="", status="draft",
                       source="ugc", media=json.dumps([a["id"]]), hook_style="story")
        s.add(p)
        s.flush()
        pid = p.id
        u = _ugc(s, tenant, uid)
        u.status, u.post_id = "reposted", pid
    return {"id": uid, "status": "reposted", "post_id": pid}


# ---------------------------------------------------------------- collab check (public numbers + signals + ASCI)
def creator_check(tenant: str, username: str, caption: str = "") -> dict[str, Any]:
    from ..influencer.rules import disclosure_check, fake_signals
    _hired(tenant)
    u = str(username or "").strip().lstrip("@")
    if not _USER.match(u):
        raise SocialError("Instagram username sahi likhiye.")
    lk = link(tenant)
    try:
        bd = M.ig_discover(lk["ig_id"], lk["token"], u)
    except M.MetaError as e:
        raise SocialError(str(e))
    if not bd:
        raise SocialError("Yeh account Business / Creator nahi hai; Meta sirf professional accounts ke numbers deta hai.")
    media = (bd.get("media") or {}).get("data") or []
    likes = [int(m.get("like_count") or 0) for m in media]
    comms = [int(m.get("comments_count") or 0) for m in media]
    fol = int(bd.get("followers_count") or 0)
    al = statistics.mean(likes) if likes else None
    ac = statistics.mean(comms) if comms else None
    out = {"username": bd.get("username") or u, "name": bd.get("name") or "", "followers": fol,
           "posts": int(bd.get("media_count") or 0), "avg_likes": round(al, 1) if al is not None else None,
           "avg_comments": round(ac, 1) if ac is not None else None,
           "eng_rate": round(100 * ((al or 0) + (ac or 0)) / fol, 2) if fol else None,
           "signals": fake_signals(fol, al, ac), "formats": _media_stats(media)["formats"],
           "note": "Signals only - never a verdict. A paid collab post must say #ad (or 'Paid partnership') on its first line."}
    if caption:
        out["disclosure"] = disclosure_check(caption, "instagram", "post", "paid")
    return out


# ---------------------------------------------------------------- A/B hook styles
def ab_report(tenant: str) -> dict[str, Any]:
    """Posts published through Hoola, matched to their numbers by media id, grouped by hook style."""
    with session() as s:
        posts = s.scalars(select(SocialPost).where(SocialPost.tenant_id == tenant, SocialPost.status == "published")).all()
        ids = {}
        for p in posts:
            for v in (_j(p.result, {}) or {}).values():
                if isinstance(v, dict) and v.get("id"):
                    ids[str(v["id"])] = p.hook_style or ""
        media = s.scalars(select(SocialMedia).where(SocialMedia.tenant_id == tenant, SocialMedia.media_id.in_(list(ids) or [""]))).all()
        by: dict[str, list[int]] = {}
        for m in media:
            st = ids.get(m.media_id) or ""
            if st:
                by.setdefault(st, []).append(_eng(m))
    rows = sorted(({"style": k, "posts": len(v), "avg_eng": round(sum(v) / len(v), 1)} for k, v in by.items()), key=lambda r: -r["avg_eng"])
    winner = None
    ready = [r for r in rows if r["posts"] >= 3]
    if len(ready) >= 2 and ready[0]["avg_eng"] >= 1.2 * max(ready[1]["avg_eng"], 0.1):
        winner = ready[0]["style"]
    return {"styles": rows, "winner": winner,
            "note": (f"'{winner}' hooks win: {ready[0]['avg_eng']} vs {ready[1]['avg_eng']} interactions a post. New calendars lean on them."
                     if winner else "Not enough posts per style yet (3 each) - the calendar keeps rotating styles.")}


def view(tenant: str) -> dict[str, Any]:
    ensure_growth()
    with session() as s:                       # the desk view never calls Meta: the daily job finds the link
        d = s.get(SocialDesk, tenant)
        cache = _j(d.stamps, {}).get("ig_link") if d else None
        has_page = s.scalars(select(SocialAccount.id).where(SocialAccount.tenant_id == tenant,
                                                            SocialAccount.platform == "facebook")).first() is not None
    linked = ({"ok": True, "username": cache.get("username", "")} if isinstance(cache, dict) and cache.get("ig_id") else
              {"ok": False, "reason": "Connect your Facebook Page (linked to your Instagram) - hashtag search and competitor "
                                      "numbers come only that way." if not has_page else
                                      "Checking your Page's Instagram link - it runs every morning (or tap Check now)."})
    return {"link": linked, "watch": watch_view(tenant), "ugc": ugc_list(tenant), "ab": ab_report(tenant)}
