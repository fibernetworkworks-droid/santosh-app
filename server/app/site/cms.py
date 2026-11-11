"""v0.538 HOOLA CMS (web Step 6 part 2 = W8 "a CMS for her team: editors with roles, drafts, review, scheduled publish,
version history for every page and post").

Her team works on her website WITHOUT her Hoola login and without AI:
  * TEAM: she invites a person by email with a role - writer (writes drafts), editor (edits anyone's draft, approves or
    sends it back with a note), publisher (publishes now or at a time, restores an old version). The invite is a one-time
    link (7 days, only its hash is kept); the person sets a password (PBKDF2) and works at /cms/<site>/. She removes
    anyone in one tap (every login of theirs ends at once). She (the owner, in her console) can do everything.
  * DRAFTS: a blog post (new or an edit of a live one) or a PAGE: new words / links for the texts of one page (the same
    elements her own Edit mode changes - nothing else on the page can be touched). draft -> review -> approved ->
    published (or scheduled); an editor never approves their own draft (maker-checker); a sent-back draft carries the note.
  * PUBLISH: a post goes to the blog, a page's changes are applied to the CURRENT page (a text that changed meanwhile is
    named, never silently overwritten); a new checked version is made and, when her live address shows the version
    before it, the new one goes live too (the blog's rule). A scheduled draft is published by the worker at its time.
  * HISTORY: every publish / restore keeps a revision with what was there BEFORE and who did it; a publisher restores any
    revision (itself a new revision - nothing is ever lost).
  Text the team writes is content for her site, never an instruction to Hoola."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import webapp as W

ROLES = ("writer", "editor", "publisher")
RANK = {"writer": 1, "editor": 2, "publisher": 3, "owner": 9}
STATES = ("draft", "review", "approved", "returned", "scheduled", "published", "withdrawn")
INVITE_DAYS = 7
TOKEN_HOURS = 12
MAX_TEAM = 50
MAX_BODY = 60_000
STATS = {"invites": 0, "logins": 0, "drafts": 0, "published": 0, "restored": 0, "conflicts": 0}


class CmsError(W.AppError):
    pass


class SiteCmsMember(Base):
    __tablename__ = "site_cms_member"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cmm"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    email: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(80), default="")
    role: Mapped[str] = mapped_column(String(12), default="writer")
    pw: Mapped[str] = mapped_column(String(200), default="")
    invite_h: Mapped[str] = mapped_column(String(64), default="")
    invite_exp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gen: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(10), default="invited")            # invited | active | removed
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SiteCmsDraft(Base):
    __tablename__ = "site_cms_draft"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cmd"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(6))                                   # post | page
    target: Mapped[str] = mapped_column(String(100), default="")                   # post slug (edit) / page slug
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")                            # post markdown
    ops: Mapped[str] = mapped_column(Text, default="[]")                           # page: [{key, e, op, value, was}]
    meta: Mapped[str] = mapped_column(Text, default="{}")                          # excerpt, category, cover
    status: Mapped[str] = mapped_column(String(10), default="draft")
    author: Mapped[str] = mapped_column(String(40), default="")
    author_name: Mapped[str] = mapped_column(String(80), default="")
    reviewer: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    log: Mapped[str] = mapped_column(Text, default="[]")


class SiteCmsRev(Base):
    __tablename__ = "site_cms_rev"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cmr"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(6))
    target: Mapped[str] = mapped_column(String(100), default="", index=True)
    draft_id: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(10), default="publish")             # publish | restore
    before: Mapped[str] = mapped_column(Text, default="{}")
    after: Mapped[str] = mapped_column(Text, default="{}")
    by_name: Mapped[str] = mapped_column(String(80), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_OK = False


def ensure_tables() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        for t in (SiteCmsMember, SiteCmsDraft, SiteCmsRev):
            t.__table__.create(_db._engine, checkfirst=True)
        _OK = True


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def _aware(t: datetime | None) -> datetime | None:
    return None if t is None else (t if t.tzinfo else t.replace(tzinfo=timezone.utc))


# ---------------------------------------------------------------- who is working
class Who:
    def __init__(self, m: SiteCmsMember | None = None, owner: bool = False, site_id: str = ""):
        self.m, self.owner, self.site_id = m, owner, site_id or (m.site_id if m else "")

    @property
    def role(self) -> str:
        return "owner" if self.owner else (self.m.role if self.m else "")

    @property
    def id(self) -> str:
        return "owner" if self.owner else (self.m.id if self.m else "")

    @property
    def name(self) -> str:
        return "Owner" if self.owner else (self.m.name or self.m.email.split("@")[0] if self.m else "")

    def can(self, role: str) -> bool:
        return RANK.get(self.role, 0) >= RANK[role]


def _need(w: Who, role: str) -> None:
    if not w.can(role):
        raise CmsError("Your role does not allow this.", 403)


def _sign(body: str) -> str:
    return hmac.new(W._secret(), ("cms|" + body).encode(), hashlib.sha256).hexdigest()[:40]


def _token(m: SiteCmsMember) -> str:
    body = f"{m.site_id}.{m.id}.{m.gen}.{int(time.time()) + TOKEN_HOURS * 3600}"
    return f"{body}.{_sign(body)}"


def who(site_id: str, token: str) -> Who:
    try:
        sid, mid, gen, exp, sig = str(token or "").split(".")
    except ValueError:
        raise CmsError("Sign in first.", 401)
    body = f"{sid}.{mid}.{gen}.{exp}"
    if sid != site_id or not exp.isdigit() or int(exp) < time.time() or not hmac.compare_digest(sig, _sign(body)):
        raise CmsError("The sign-in has expired; sign in again.", 401)
    ensure_tables()
    with session() as s:
        m = s.get(SiteCmsMember, mid)
        if m is None or m.site_id != site_id or m.status != "active" or str(m.gen) != gen:
            raise CmsError("This sign-in is turned off.", 401)
        m.seen = now()
        s.flush()
        s.expunge(m)
    return Who(m)


def _clean_email(e: str) -> str:
    e = str(e or "").strip().lower()
    if not re.fullmatch(r"[^@\s]{1,64}@[^@\s]{1,120}\.[a-z]{2,12}", e):
        raise CmsError("Enter a valid email.")
    return e


def invite(site_id: str, email: str, name: str, role: str, base: str = "") -> dict[str, Any]:
    """Her tap: a team member with a role; returns the one-time link she shares (only its hash is kept)."""
    ensure_tables()
    if role not in ROLES:
        raise CmsError("Role: writer / editor / publisher.")
    email = _clean_email(email)
    tok = secrets.token_urlsafe(24)
    with session() as s:
        team = s.scalars(select(SiteCmsMember).where(SiteCmsMember.site_id == site_id, SiteCmsMember.status != "removed")).all()
        m = next((x for x in team if x.email == email), None)
        if m is None:
            if len(team) >= MAX_TEAM:
                raise CmsError(f"A website can have up to {MAX_TEAM} people.")
            m = SiteCmsMember(site_id=site_id, email=email)
            s.add(m)
        m.name = re.sub(r"[\x00-\x1f<>]", "", str(name or "")).strip()[:80] or m.name or email.split("@")[0]
        m.role, m.invite_h = role, hashlib.sha256(tok.encode()).hexdigest()
        m.invite_exp = now() + timedelta(days=INVITE_DAYS)
        if m.status == "removed":
            m.status = "invited"
        s.flush()
        mid = m.id
    STATS["invites"] += 1
    link = f"{base.rstrip('/')}/cms/{site_id}/?invite={tok}"
    return {"member": mid, "link": link, "expires_days": INVITE_DAYS,
            "say": f"Send this link to {email} (works for {INVITE_DAYS} days, once): {link}"}


def accept(site_id: str, tok: str, password: str, name: str = "") -> dict[str, Any]:
    ensure_tables()
    if len(str(password or "")) < 10:
        raise CmsError("The password must be at least 10 characters.")
    h = hashlib.sha256(str(tok or "").encode()).hexdigest()
    with session() as s:
        m = s.scalars(select(SiteCmsMember).where(SiteCmsMember.site_id == site_id, SiteCmsMember.invite_h == h)).first()
        if m is None or m.status == "removed" or not m.invite_exp or _aware(m.invite_exp) < now():
            raise CmsError("This invite link is old or wrong; ask the website's owner for a new one.", 403)
        m.pw, m.invite_h, m.invite_exp, m.status = W.hash_pw(str(password)), "", None, "active"
        m.gen = (m.gen or 0) + 1
        if name:
            m.name = re.sub(r"[\x00-\x1f<>]", "", name).strip()[:80]
        s.flush()
        s.expunge(m)
    return {"token": _token(m), "me": _me(m)}


def login(site_id: str, email: str, password: str, ip: str = "") -> dict[str, Any]:
    ensure_tables()
    email = str(email or "").strip().lower()
    W.rate(f"cms-login:{site_id}:{email}", 8, 600)
    W.rate(f"cms-login-ip:{ip}", 30, 600)
    with session() as s:
        m = s.scalars(select(SiteCmsMember).where(SiteCmsMember.site_id == site_id, SiteCmsMember.email == email,
                                                  SiteCmsMember.status == "active")).first()
        ok = m is not None and W.check_pw(str(password or ""), m.pw)
        if ok:
            s.expunge(m)
    if not ok:
        raise CmsError("Wrong email or password.", 401)
    STATS["logins"] += 1
    return {"token": _token(m), "me": _me(m)}


def _me(m: SiteCmsMember) -> dict[str, Any]:
    return {"id": m.id, "email": m.email, "name": m.name, "role": m.role}


def team(site_id: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [{**_me(m), "status": m.status, "seen": m.seen.isoformat() if m.seen else "",
                 "invite_open": bool(m.invite_h and m.invite_exp and _aware(m.invite_exp) > now())}
                for m in s.scalars(select(SiteCmsMember).where(SiteCmsMember.site_id == site_id, SiteCmsMember.status != "removed")
                                   .order_by(SiteCmsMember.created)).all()]


def set_member(site_id: str, mid: str, role: str = "", remove: bool = False) -> dict[str, Any]:
    """Her tap: a new role, or the person leaves (every login of theirs ends now; their drafts stay)."""
    ensure_tables()
    with session() as s:
        m = s.get(SiteCmsMember, mid)
        if m is None or m.site_id != site_id:
            raise CmsError("This person is not in the team.", 404)
        if remove:
            m.status, m.invite_h = "removed", ""
        elif role in ROLES:
            m.role = role
        else:
            raise CmsError("Role: writer / editor / publisher.")
        m.gen = (m.gen or 0) + 1
    return {"team": team(site_id)}


# ---------------------------------------------------------------- what a page's texts are (the Edit mode elements)
def _site(site_id: str):
    from . import service as S
    return S._load(site_id)


def page_texts(site_id: str, slug: str) -> list[dict[str, Any]]:
    """Every text / link element of one page the team may change: {key, e, kind, text, href}."""
    from . import edit as E
    from . import service as S
    r = _site(site_id)
    S._ensure_tags(r)
    secs = S._sections(_site(site_id))
    plan = _j(r.plan, {})
    page = next((p for p in plan.get("pages", []) if p["slug"] == slug and not p.get("template_of")), None)
    if page is None:
        raise CmsError("This page is not in the website.", 404)
    out = []
    from bs4 import BeautifulSoup
    for sec in page.get("sections", []):
        key = f"{slug}__{sec['type']}"
        h = (secs.get(key) or {}).get("html") or ""
        for el in BeautifulSoup(h, "html.parser").find_all(attrs={"data-e": True}):
            d = E.describe(h, el["data-e"])
            if d["kind"] in ("text", "link") and d["text"]:
                out.append({"key": key, "e": d["e"], "kind": d["kind"], "tag": d["tag"], "text": d["text"], "href": d["href"]})
    return out


def pages(site_id: str) -> list[dict[str, str]]:
    plan = _j(_site(site_id).plan, {})
    return [{"slug": p["slug"], "title": p.get("title") or p["slug"]} for p in plan.get("pages", [])
            if not p.get("template_of") and p["slug"] not in ("privacy", "terms", "refund", "disclaimer", "account", "admin")]


# ---------------------------------------------------------------- drafts
def _view(d: SiteCmsDraft, full: bool = False) -> dict[str, Any]:
    out = {"id": d.id, "kind": d.kind, "target": d.target, "title": d.title, "status": d.status, "author": d.author,
           "author_name": d.author_name, "reviewer": d.reviewer, "note": d.note,
           "publish_at": _aware(d.publish_at).isoformat() if d.publish_at else "", "updated": d.updated.isoformat() if d.updated else "",
           "changes": len(_j(d.ops, [])) if d.kind == "page" else None}
    if full:
        out.update({"body": d.body, "ops": _j(d.ops, []), "meta": _j(d.meta, {}), "log": _j(d.log, [])})
    return out


def _log(d: SiteCmsDraft, w: Who, what: str) -> None:
    lg = _j(d.log, [])
    lg.append({"at": now().isoformat(), "by": w.name, "what": what})
    d.log = json.dumps(lg[-60:], ensure_ascii=False)


def drafts(site_id: str, w: Who, status: str = "") -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        q = select(SiteCmsDraft).where(SiteCmsDraft.site_id == site_id)
        if status:
            q = q.where(SiteCmsDraft.status == status)
        if not w.can("editor"):                          # a writer sees their own drafts + everything already published
            from sqlalchemy import or_
            q = q.where(or_(SiteCmsDraft.author == w.id, SiteCmsDraft.status == "published"))
        return [_view(d) for d in s.scalars(q.order_by(SiteCmsDraft.updated.desc()).limit(300)).all()]


def draft(site_id: str, w: Who, did: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        d = s.get(SiteCmsDraft, did)
        if d is None or d.site_id != site_id or (not w.can("editor") and d.author != w.id and d.status != "published"):
            raise CmsError("Draft not found.", 404)
        return _view(d, True)


def _clean_ops(site_id: str, slug: str, ops: Any) -> list[dict[str, Any]]:
    from . import build as B
    texts = {(t["key"], t["e"]): t for t in page_texts(site_id, slug)}
    out = []
    for o in (ops if isinstance(ops, list) else [])[:200]:
        if not isinstance(o, dict):
            continue
        k = (str(o.get("key") or ""), str(o.get("e") or ""))
        op = str(o.get("op") or "text")
        t = texts.get(k)
        if t is None or op not in ("text", "link") or (op == "link" and t["kind"] != "link"):
            raise CmsError("This part of the page cannot be changed.")
        v = re.sub(r"\s+", " ", str(o.get("value") or "")).strip()[:2000]
        if not v:
            raise CmsError("Empty text is not allowed.")
        if op == "link" and not B._ok_href(v):
            raise CmsError("Link: https://..., tel:, mailto: or one of the site's own pages.")
        out.append({"key": k[0], "e": k[1], "op": op, "value": v, "was": t["href"] if op == "link" else t["text"]})
    if not out:
        raise CmsError("No changes.")
    return out


def save(site_id: str, w: Who, body: dict[str, Any], did: str = "") -> dict[str, Any]:
    """A new draft, or changes to one (author while draft / returned; an editor any time before it is published)."""
    _need(w, "writer")
    ensure_tables()
    kind = str(body.get("kind") or "post")
    with session() as s:
        d = s.get(SiteCmsDraft, did) if did else None
        if did and (d is None or d.site_id != site_id):
            raise CmsError("Draft not found.", 404)
        if d is not None:
            if d.status in ("published", "withdrawn"):
                raise CmsError("A published draft cannot be changed; make a new draft.", 409)
            if not (w.can("editor") or (d.author == w.id and d.status in ("draft", "returned"))):
                raise CmsError("You cannot change this draft right now.", 403)
            kind = d.kind
        else:
            if kind not in ("post", "page"):
                raise CmsError("Post or page.")
            n = s.scalar(select(__import__("sqlalchemy").func.count()).select_from(SiteCmsDraft).where(
                SiteCmsDraft.site_id == site_id, SiteCmsDraft.status.in_(("draft", "review", "approved", "returned", "scheduled"))))
            if (n or 0) >= 500:
                raise CmsError("Too many open drafts; publish or remove some first.")
            d = SiteCmsDraft(site_id=site_id, kind=kind, author=w.id, author_name=w.name)
            s.add(d)
            STATS["drafts"] += 1
        if kind == "post":
            title = re.sub(r"[\x00-\x1f]", "", str(body.get("title") or d.title or "")).strip()[:200]
            text = str(body.get("body") if body.get("body") is not None else d.body or "")[:MAX_BODY]
            if not title or not text.strip():
                raise CmsError("A post needs both a title and its text.")
            target = str(body.get("target") if body.get("target") is not None else d.target or "")[:100]
            if target:
                from . import blog as BL
                if not any(p["slug"] == target for p in BL.posts(site_id)):
                    raise CmsError("This post is not in the blog.", 404)
            meta = {k: str(v)[:400] for k, v in (body.get("meta") or _j(d.meta, {})).items() if k in ("excerpt", "category", "cover")}
            d.title, d.body, d.target, d.meta = title, text, target, json.dumps(meta, ensure_ascii=False)
        else:
            slug = str(body.get("target") or d.target or "")
            d.target, d.title = slug, str(body.get("title") or d.title or f"Page: {slug}")[:200]
            d.ops = json.dumps(_clean_ops(site_id, slug, body.get("ops")), ensure_ascii=False)
        if d.status == "approved":                        # an approved draft that changes needs approving again
            d.status, d.reviewer = "review", ""
        d.updated = now()
        _log(d, w, "saved")
        s.flush()
        return _view(d, True)


def move(site_id: str, w: Who, did: str, to: str, note: str = "", when: str = "") -> dict[str, Any]:
    """submit (author) / approve + return (editor, never their own) / publish + schedule (publisher) / withdraw."""
    ensure_tables()
    publish_now = False
    with session() as s:
        d = s.get(SiteCmsDraft, did)
        if d is None or d.site_id != site_id:
            raise CmsError("Draft not found.", 404)
        st = d.status
        if to == "review":
            if not (d.author == w.id or w.can("editor")) or st not in ("draft", "returned"):
                raise CmsError("Send only your own draft for review.", 409)
        elif to in ("approved", "returned"):
            _need(w, "editor")
            if st != "review":
                raise CmsError("The draft must be in review first.", 409)
            if d.author == w.id and not w.owner:
                raise CmsError("You cannot approve your own draft - another editor must look at it.", 403)
            d.reviewer = w.name
            if to == "returned":
                d.note = re.sub(r"[\x00-\x08]", "", note or "").strip()[:1000] or "Please look again."
        elif to in ("published", "scheduled"):
            _need(w, "publisher")
            if st != "approved" and not w.owner:
                raise CmsError("Only an approved draft can be published.", 409)
            if to == "scheduled":
                try:
                    at = datetime.fromisoformat(str(when))
                except ValueError:
                    raise CmsError("Give the time like 2026-11-20T10:00+05:30.")
                at = at if at.tzinfo else at.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
                if at <= now() + timedelta(minutes=1):
                    raise CmsError("Pick a time in the future.")
                d.publish_at = at
            else:
                publish_now = True
        elif to == "withdrawn":
            if not (d.author == w.id or w.can("editor")) or st == "published":
                raise CmsError("This draft cannot be removed.", 409)
        else:
            raise CmsError("The action was not understood.")
        if not publish_now:
            d.status = to
        d.updated = now()
        _log(d, w, to + (f": {note[:80]}" if note else ""))
    if publish_now:
        return publish(site_id, did, w)
    return draft(site_id, w, did)


# ---------------------------------------------------------------- publishing + history
def publish(site_id: str, did: str, w: Who) -> dict[str, Any]:
    from . import blog as BL
    from . import edit as E
    from . import service as S
    from . import build as B
    with session() as s:
        d = s.get(SiteCmsDraft, did)
        if d is None or d.site_id != site_id or d.status in ("published", "withdrawn"):
            raise CmsError("The draft is not ready to publish.", 409)
        s.expunge(d)
    r = _site(site_id)
    conflicts: list[str] = []
    if d.kind == "post":
        meta = _j(d.meta, {})
        before: dict[str, Any] = {}
        if d.target:
            with session() as s:
                p = s.scalars(select(BL.SiteBlogPost).where(BL.SiteBlogPost.site_id == site_id, BL.SiteBlogPost.slug == d.target)).first()
                if p is None:
                    raise CmsError("That post is no longer in the blog.", 409)
                before = {"title": p.title, "body": p.body, "excerpt": p.excerpt, "category": p.category}
                p.title, p.body = d.title, d.body
                p.excerpt = meta.get("excerpt") or BL._first_line(d.body)
                p.category = meta.get("category", p.category)
                p.words, p.updated_at = BL.words_in(d.body), now()
                slug = p.slug
        else:
            post = BL.put(r.tenant_id, site_id, {"id": f"cms-{d.id}", "title": d.title, "body": d.body, "author": d.author_name,
                                                 "meta": {"excerpt": meta.get("excerpt", ""), "category": meta.get("category", "")}})
            slug = post["slug"]
        after = {"title": d.title, "body": d.body, "excerpt": meta.get("excerpt", ""), "category": meta.get("category", "")}
        target = slug
    else:
        secs = S._sections(r)
        before_ops, after_ops = [], []
        photos = {p["name"] for p in _j(r.photos, [])}
        for o in _j(d.ops, []):
            sec = secs.get(o["key"])
            if sec is None:
                conflicts.append(f"{o['key']}: the section is no longer there")
                continue
            try:
                now_d = E.describe(sec["html"], o["e"])
            except E.EditError:
                conflicts.append(f"{o['key']} #{o['e']}: the part is no longer there")
                continue
            cur = now_d["href"] if o["op"] == "link" else now_d["text"]
            if cur != o["was"]:                           # changed by someone else since the draft was written
                conflicts.append(f'"{o["was"][:40]}" is now "{cur[:40]}"')
                continue
            h, _what = E.apply(sec["html"], o["e"], o["op"], o["value"], photos, B._ok_href)
            secs[o["key"]] = {**sec, "html": h, "edited": True}
            before_ops.append({**o, "value": cur})
            after_ops.append(o)
        if conflicts and not after_ops:
            STATS["conflicts"] += 1
            raise CmsError("The page changed in the meantime; make the draft again. " + "; ".join(conflicts[:4]), 409)
        for k in {o["key"] for o in after_ops}:
            S._put_sec(r, k, secs[k])
        before, after, target = {"ops": before_ops}, {"ops": after_ops}, d.target
    with session() as s:
        s.add(SiteCmsRev(site_id=site_id, kind=d.kind, target=target, draft_id=d.id, before=json.dumps(before, ensure_ascii=False),
                         after=json.dumps(after, ensure_ascii=False), by_name=w.name))
        dd = s.get(SiteCmsDraft, did)
        dd.status, dd.publish_at, dd.updated = "published", None, now()
        if d.kind == "post":
            dd.target = target
        _log(dd, w, "published" + (f" ({len(conflicts)} skipped)" if conflicts else ""))
    STATS["published"] += 1
    S._blog_rebuild(_site(site_id), f"team: {d.title[:60]} ({w.name})", live=True)
    return {**draft(site_id, Who(owner=True, site_id=site_id), did), "skipped": conflicts,
            "say": "Published; after the checks the new version also goes to the live address (if the last version was live)."}


def history(site_id: str, kind: str = "", target: str = "") -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        q = select(SiteCmsRev).where(SiteCmsRev.site_id == site_id)
        if kind:
            q = q.where(SiteCmsRev.kind == kind)
        if target:
            q = q.where(SiteCmsRev.target == target)
        return [{"id": x.id, "kind": x.kind, "target": x.target, "action": x.action, "by": x.by_name, "at": x.at.isoformat() if x.at else "",
                 "draft": x.draft_id, "summary": _summary(x)} for x in s.scalars(q.order_by(SiteCmsRev.at.desc()).limit(200)).all()]


def _summary(x: SiteCmsRev) -> str:
    a = _j(x.after, {})
    if x.kind == "post":
        return str(a.get("title") or "")[:80]
    return f"{len(a.get('ops') or [])} text(s)"


def restore(site_id: str, rid: str, w: Who) -> dict[str, Any]:
    """A publisher brings back what was there BEFORE a revision (itself a new revision)."""
    _need(w, "publisher")
    ensure_tables()
    with session() as s:
        x = s.get(SiteCmsRev, rid)
        if x is None or x.site_id != site_id:
            raise CmsError("Revision not found.", 404)
        s.expunge(x)
    before = _j(x.before, {})
    if x.kind == "post":
        if not before:                                   # the revision CREATED the post: restoring = hiding it
            from . import blog as BL
            BL.set_status(site_id, x.target, "hidden")
            body = {"hidden": True}
        else:
            from . import blog as BL
            with session() as s:
                p = s.scalars(select(BL.SiteBlogPost).where(BL.SiteBlogPost.site_id == site_id, BL.SiteBlogPost.slug == x.target)).first()
                if p is None:
                    raise CmsError("That post is no longer in the blog.", 409)
                cur = {"title": p.title, "body": p.body, "excerpt": p.excerpt, "category": p.category}
                p.title, p.body, p.excerpt, p.category = before["title"], before["body"], before.get("excerpt", ""), before.get("category", "")
                p.words, p.updated_at = BL.words_in(p.body), now()
            body = {"was": cur}
        after = before
    else:
        from . import build as B
        from . import edit as E
        from . import service as S
        r = _site(site_id)
        secs = S._sections(r)
        photos = {p["name"] for p in _j(r.photos, [])}
        done = []
        for o in before.get("ops") or []:
            sec = secs.get(o["key"])
            if sec is None:
                continue
            try:
                cur = E.describe(sec["html"], o["e"])
                h, _ = E.apply(sec["html"], o["e"], o["op"], o["value"], photos, B._ok_href)
            except E.EditError:
                continue
            secs[o["key"]] = {**sec, "html": h, "edited": True}
            done.append({**o, "was": cur["href"] if o["op"] == "link" else cur["text"]})
        for k in {o["key"] for o in done}:
            S._put_sec(r, k, secs[k])
        body, after = {"ops": [{**o, "value": o["was"]} for o in done]}, {"ops": done}
    with session() as s:
        s.add(SiteCmsRev(site_id=site_id, kind=x.kind, target=x.target, draft_id=x.draft_id, action="restore",
                         before=json.dumps(body, ensure_ascii=False), after=json.dumps(after, ensure_ascii=False), by_name=w.name))
    STATS["restored"] += 1
    from . import service as S
    S._blog_rebuild(_site(site_id), f"team: restore {x.target} ({w.name})", live=True)
    return {"restored": rid, "history": history(site_id, x.kind, x.target)}


def tick(at: datetime | None = None) -> int:
    """Worker: scheduled drafts whose time came are published (by the publisher who scheduled them)."""
    ensure_tables()
    at = at or now()
    with session() as s:
        due = [(d.site_id, d.id, d.log) for d in s.scalars(select(SiteCmsDraft).where(SiteCmsDraft.status == "scheduled",
                                                                                     SiteCmsDraft.publish_at <= at)).all()]
    n = 0
    for site_id, did, lg in due:
        who_name = next((x["by"] for x in reversed(_j(lg, [])) if x.get("what") == "scheduled"), "Schedule")
        try:
            w = Who(owner=True, site_id=site_id)
            w_name = who_name
            publish(site_id, did, _Named(w, w_name))
            n += 1
        except Exception:                                 # noqa: BLE001 - one bad draft never stops the others
            with session() as s:
                d = s.get(SiteCmsDraft, did)
                if d is not None:
                    d.status, d.note = "returned", "Could not be published on time (did the page change in the meantime?) - look again."
    return n


class _Named(Who):
    def __init__(self, w: Who, name: str):
        super().__init__(w.m, w.owner, w.site_id)
        self._n = name

    @property
    def name(self) -> str:
        return self._n
