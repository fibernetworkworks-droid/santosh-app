"""Her saved prompts (plan P3: Save) and P7 MERE PROMPT: every change kept as a version (restore any = a new version,
undoable), parts she fills each time ("this week's offer"), a schedule handed to Hoola's routines, and a share link a
teammate opens and copies from (screened: a shared prompt is data, never instructions)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import hashlib
import re
import secrets
from datetime import timedelta

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, new_id, now, session

MAX_SAVED = 200
MAX_VERSIONS = 50
SHARE_DAYS = 30
SCHEDULE_REPEATS = ("daily", "weekdays", "weekly", "monthly")


class PromptSaved(Base):
    __tablename__ = "prompt_saved"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    section: Mapped[str] = mapped_column(String(20), default="")
    brief: Mapped[str] = mapped_column(Text, default="{}")
    prompt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # P7 (nullable so an older table gains them)
    ask: Mapped[str | None] = mapped_column(Text, nullable=True, default="[]")          # slot keys she fills each time
    version: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)
    routine_id: Mapped[str | None] = mapped_column(String(40), nullable=True, default="")
    share_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, default="", index=True)
    share_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    copied_from: Mapped[str | None] = mapped_column(String(160), nullable=True, default="")


class PromptVersion(Base):
    """One kept state of a saved prompt. Never edited; a restore adds a new one."""
    __tablename__ = "prompt_saved_versions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    saved_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    n: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(160), default="")
    brief: Mapped[str] = mapped_column(Text, default="{}")
    prompt: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PromptError(ValueError):
    pass


_OK: set[int] = set()


def ensure_table() -> None:
    """Self-heal, keyed on the engine (a fresh test database is a new engine)."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _OK:
        PromptSaved.__table__.create(eng, checkfirst=True)
        PromptVersion.__table__.create(eng, checkfirst=True)
        try:                                     # P7 columns on an older prompt_saved table (own tables only)
            from ..db import add_missing_columns_for
            add_missing_columns_for(eng, PromptSaved.__table__)
        except Exception:       # noqa: BLE001 - init_db heals it on the next start too
            pass
        _OK.add(id(eng))


def _ask(r: PromptSaved) -> list[str]:
    try:
        v = json.loads(r.ask or "[]")
        return [str(x) for x in v][:12] if isinstance(v, list) else []
    except ValueError:
        return []


def _labels(section: str, keys: list[str]) -> str:
    from . import anatomy as A
    return ", ".join((A.slot(section, k) or {"label": k})["label"].lower() for k in keys) if section in A.SECTIONS else ", ".join(keys)


def _view(r: PromptSaved, full: bool = False) -> dict[str, Any]:
    out = {"id": r.id, "title": r.title, "section": r.section, "prompt": r.prompt if full else r.prompt[:200],
           "updated_at": as_utc(r.updated_at).isoformat() if r.updated_at else None, "version": int(r.version or 1),
           "ask": _ask(r), "scheduled": bool(r.routine_id), "copied_from": r.copied_from or "",
           "shared": bool(r.share_hash) and bool(r.share_until) and as_utc(r.share_until) > now(),
           "share_until": as_utc(r.share_until).isoformat() if r.share_hash and r.share_until else None}
    if full:
        try:
            out["brief"] = json.loads(r.brief or "{}")
        except ValueError:
            out["brief"] = {}
    return out


def save(tenant: str, brief: dict[str, Any], prompt: str, title: str = "", pid: str = "", note: str = "") -> dict[str, Any]:
    ensure_table()
    title = (title or brief.get("intent") or "Prompt").strip()[:160]
    with session() as s:
        r = s.get(PromptSaved, pid) if pid else None
        if r is not None and r.tenant_id != tenant:
            r = None
        if r is None:
            n = len(s.execute(select(PromptSaved.id).where(PromptSaved.tenant_id == tenant)).all())
            if n >= MAX_SAVED:
                raise ValueError(f"You have {MAX_SAVED} saved prompts. Delete one you no longer use first.")
            r = PromptSaved(id=new_id("pr"), tenant_id=tenant)
            s.add(r)
        new_brief = json.dumps(brief, ensure_ascii=False)
        changed = r.brief != new_brief or r.title != title
        r.title, r.section = title, str(brief.get("section") or "")[:20]
        r.brief, r.prompt, r.updated_at = new_brief, str(prompt or "")[:6000], now()
        if changed:
            _keep(s, r, note)
        s.flush()
        _sync_routine(s, r)
        return _view(r, full=True)


def _keep(s, r: PromptSaved, note: str = "") -> int:
    """A version of the prompt as it now is. The oldest go past MAX_VERSIONS (version 1 is kept)."""
    last = s.execute(select(PromptVersion.n).where(PromptVersion.saved_id == r.id).order_by(PromptVersion.n.desc()).limit(1)).scalar()
    n = int(last or 0) + 1
    s.add(PromptVersion(id=new_id("prv"), saved_id=r.id, tenant_id=r.tenant_id, n=n, title=r.title, brief=r.brief,
                        prompt=r.prompt, note=(note or ("Saved" if n == 1 else "Changed"))[:160]))
    r.version = n
    s.flush()
    old = list(s.execute(select(PromptVersion).where(PromptVersion.saved_id == r.id, PromptVersion.n > 1)
                         .order_by(PromptVersion.n.desc()).offset(MAX_VERSIONS - 1)).scalars())
    for v in old:
        s.delete(v)
    return n


def listing(tenant: str, section: str = "") -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        q = select(PromptSaved).where(PromptSaved.tenant_id == tenant).order_by(PromptSaved.updated_at.desc()).limit(MAX_SAVED)
        return [_view(r) for r in s.execute(q).scalars() if not section or r.section == section]


def get(tenant: str, pid: str) -> dict[str, Any] | None:
    ensure_table()
    with session() as s:
        r = s.get(PromptSaved, pid)
        return _view(r, full=True) if r is not None and r.tenant_id == tenant else None


def delete(tenant: str, pid: str) -> bool:
    ensure_table()
    with session() as s:
        r = s.get(PromptSaved, pid)
        if r is None or r.tenant_id != tenant:
            return False
        _stop_routine(s, r)
        for v in s.execute(select(PromptVersion).where(PromptVersion.saved_id == pid)).scalars():
            s.delete(v)
        s.delete(r)
        return True


def _mine(s, tenant: str, pid: str) -> PromptSaved:
    r = s.get(PromptSaved, pid)
    if r is None or r.tenant_id != tenant:
        raise KeyError(pid)
    return r


# ---------------------------------------------------------------- versions
def versions(tenant: str, pid: str) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        _mine(s, tenant, pid)
        rows = s.execute(select(PromptVersion).where(PromptVersion.saved_id == pid).order_by(PromptVersion.n.desc())).scalars()
        return [{"n": v.n, "title": v.title, "note": v.note, "prompt": v.prompt[:240],
                 "at": as_utc(v.created_at).isoformat() if v.created_at else None} for v in rows]


def version(tenant: str, pid: str, n: int) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        _mine(s, tenant, pid)
        v = s.execute(select(PromptVersion).where(PromptVersion.saved_id == pid, PromptVersion.n == int(n))).scalar()
        if v is None:
            raise KeyError(f"version {n}")
        return {"n": v.n, "title": v.title, "note": v.note, "prompt": v.prompt, "brief": json.loads(v.brief or "{}")}


def restore(tenant: str, pid: str, n: int) -> dict[str, Any]:
    """Version n comes back as a NEW version (so the restore itself can be undone by restoring the one before)."""
    ensure_table()
    with session() as s:
        r = _mine(s, tenant, pid)
        v = s.execute(select(PromptVersion).where(PromptVersion.saved_id == pid, PromptVersion.n == int(n))).scalar()
        if v is None:
            raise KeyError(f"version {n}")
        if r.brief == v.brief and r.title == v.title:
            return _view(r, full=True)
        r.title, r.brief, r.prompt, r.updated_at = v.title, v.brief, v.prompt, now()
        _keep(s, r, f"Restored version {v.n}")
        _sync_routine(s, r)
        return _view(r, full=True)


# ---------------------------------------------------------------- the parts she fills each time
def set_ask(tenant: str, pid: str, keys: list[str] | None = None, title: str | None = None) -> dict[str, Any]:
    ensure_table()
    from . import anatomy as A
    with session() as s:
        r = _mine(s, tenant, pid)
        if keys is not None:
            ok = [k for k in dict.fromkeys(str(x) for x in keys) if k in A.keys(r.section)]
            if ok and r.routine_id:
                raise PromptError("A scheduled prompt runs without you, so it cannot ask for anything. Stop the schedule "
                                  "first, or fill those parts in.")
            r.ask = json.dumps(ok[:12])
        if title is not None and title.strip() and title.strip()[:160] != r.title:
            r.title = title.strip()[:160]
            _keep(s, r, "Renamed")
        r.updated_at = now()
        s.flush()
        return _view(r, full=True)


# ---------------------------------------------------------------- the schedule (Hoola's own routines run it)
SCHEDULE_NOTE = ("This is her saved prompt '{title}' from Hoola Prompting, run on its schedule. Do it now. Anything that "
                 "sends, spends money or goes public still waits for her tap on a card.\n\n")


def _stop_routine(s, r: PromptSaved) -> None:
    if not r.routine_id:
        return
    from ..db import Routine
    rt = s.get(Routine, r.routine_id)
    if rt is not None and rt.tenant_id == r.tenant_id and rt.status == "active":
        rt.status = "cancelled"
    r.routine_id = ""


def _run_text(r: PromptSaved) -> str:
    from . import brief as B
    from . import dialect as D
    out = D.render(B.validate(json.loads(r.brief or "{}")))
    return out["run"]["text"] if out["run"]["to"] == "chat" else ""


def _sync_routine(s, r: PromptSaved) -> None:
    """A changed or restored prompt: its schedule runs the new words from the next run on."""
    if not r.routine_id:
        return
    from ..db import Routine
    rt = s.get(Routine, r.routine_id)
    if rt is None or rt.status != "active":
        r.routine_id = ""
        return
    text = _run_text(r)
    if text:
        rt.instruction = (SCHEDULE_NOTE.format(title=r.title) + text)[:2000]
        rt.title = ("Prompt: " + r.title)[:200]


def schedule(tenant: str, pid: str, repeat: str, at: str, conversation_id: str = "") -> dict[str, Any]:
    """Run the saved prompt on a schedule through Hoola's routines (repeat daily / weekdays / weekly / monthly, first run
    at `at`, local ISO). Only prompts that run in the chat; never one with parts she fills each time."""
    ensure_table()
    from .. import life
    from ..db import Routine
    from sqlalchemy import func
    if repeat not in SCHEDULE_REPEATS:
        raise PromptError("Choose daily, weekdays, weekly or monthly.")
    tz = life.tz_of(tenant)
    try:
        due = life.parse_local(at, tz)
    except ValueError:
        raise PromptError("Choose a date and time for the first run.") from None
    if due < now() - timedelta(minutes=1):
        raise PromptError("That time has already passed. Choose the next one.")
    with session() as s:
        r = _mine(s, tenant, pid)
        if _ask(r):
            raise PromptError("This prompt asks you for " + _labels(r.section, _ask(r)) + " each time, so it cannot run by itself. "
                              "Fill those parts in or stop asking for them first.")
        text = _run_text(r)
        if not text:
            raise PromptError("This prompt opens a studio where you press Build yourself, so it cannot run on a schedule.")
        _stop_routine(s, r)
        n = s.scalar(select(func.count()).select_from(Routine).where(Routine.tenant_id == tenant, Routine.status == "active")) or 0
        if n >= 20:
            raise PromptError(f"You already have {n} automatic jobs (the limit is 20). Stop one first.")
        conv = conversation_id
        if not conv:
            try:
                from .. import convs
                conv = convs.notice_chat(tenant)
            except Exception:       # noqa: BLE001
                conv = ""
        rt = Routine(tenant_id=tenant, conversation_id=conv or "", title=("Prompt: " + r.title)[:200],
                     instruction=(SCHEDULE_NOTE.format(title=r.title) + text)[:2000], next_run=due, repeat=repeat)
        s.add(rt)
        s.flush()
        r.routine_id = rt.id
        r.updated_at = now()
        return {**_view(r, full=True), "routine": life.routine_view(rt, tz)}


def unschedule(tenant: str, pid: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _mine(s, tenant, pid)
        _stop_routine(s, r)
        return _view(r, full=True)


def schedule_of(tenant: str, pid: str) -> dict[str, Any] | None:
    ensure_table()
    from .. import life
    from ..db import Routine
    with session() as s:
        r = _mine(s, tenant, pid)
        rt = s.get(Routine, r.routine_id) if r.routine_id else None
        if rt is None or rt.status != "active":
            return None
        return life.routine_view(rt, life.tz_of(tenant))


# ---------------------------------------------------------------- the share link (her team opens it, saves a copy)
def _h(token: str) -> str:
    return hashlib.sha256(("hoola-prompt-share:" + token).encode()).hexdigest()


def share(tenant: str, pid: str) -> dict[str, Any]:
    """A new link (shown once; only its hash is kept), good for SHARE_DAYS. A new link replaces the old one."""
    ensure_table()
    token = secrets.token_urlsafe(18)
    with session() as s:
        r = _mine(s, tenant, pid)
        r.share_hash, r.share_until = _h(token), now() + timedelta(days=SHARE_DAYS)
        return {"token": token, "until": as_utc(r.share_until).isoformat(), "path": f"/console/prompting#/shared/{token}"}


def unshare(tenant: str, pid: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _mine(s, tenant, pid)
        r.share_hash, r.share_until = "", None
        return _view(r, full=True)


def _by_token(s, token: str) -> PromptSaved:
    if not token or len(token) > 80:
        raise KeyError("share")
    r = s.execute(select(PromptSaved).where(PromptSaved.share_hash == _h(token))).scalar()
    if r is None or not r.share_until or as_utc(r.share_until) <= now():
        raise KeyError("share")
    return r


# what a shared prompt may never carry into someone else's account (the plan's part 9 safety wall)
_BAD = [(re.compile(r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|above|earlier|prior|all)\b.{0,30}\b(instructions?|rules?|prompts?)\b", re.I),
         "it tells the AI to ignore its rules"),
        (re.compile(r"\b(system prompt|developer message|jailbreak|you are now|act as an? (?:unfiltered|unrestricted))\b", re.I),
         "it tries to change how the AI behaves"),
        (re.compile(r"\b(password|passcode|otp|one[- ]time code|cvv|pin number|card number|upi pin|aadhaar number|pan number)\b", re.I),
         "it asks for a password, OTP, card or ID number"),
        (re.compile(r"(?:https?://|www\.)\S+", re.I), "it carries a web link"),
        (re.compile(r"\b(send|transfer|pay|delete|publish)\b.{0,30}\b(all|every|everyone|without asking|automatically)\b", re.I),
         "it asks for sending, paying or deleting without her tap")]


def screen(brief: dict[str, Any]) -> list[str]:
    """Why a shared prompt cannot be copied (empty = clean). Applied on every copy, so an old link is screened too."""
    text = " ".join([str(brief.get("intent") or "")] + [str((v or {}).get("value") or "") for v in (brief.get("slots") or {}).values()])
    return list(dict.fromkeys(why for rx, why in _BAD if rx.search(text)))


def shared(token: str) -> dict[str, Any]:
    """What a teammate sees before copying: the prompt and its parts. Never the owner's id, versions or schedule."""
    ensure_table()
    with session() as s:
        r = _by_token(s, token)
        brief = json.loads(r.brief or "{}")
        return {"title": r.title, "section": r.section, "prompt": r.prompt, "ask": _ask(r), "brief": brief,
                "problems": screen(brief), "until": as_utc(r.share_until).isoformat()}


def copy_shared(tenant: str, token: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _by_token(s, token)
        if r.tenant_id == tenant:
            raise PromptError("This is your own prompt - it is already in My prompts.")
        brief, title, prompt, ask, src = json.loads(r.brief or "{}"), r.title, r.prompt, _ask(r), r.id
    bad = screen(brief)
    if bad:
        raise PromptError("This shared prompt cannot be copied: " + "; ".join(bad) + ".")
    from . import brief as B
    clean = B.validate(brief)
    for v in clean["slots"].values():               # in her account, what came from the owner is not HER words any more
        if v["source"] in ("her_words", "her_memory", "her_answer", "her_default"):
            v["source"] = "recipe"
    clean = B.validate(clean)
    out = save(tenant, clean, prompt, title, "", "Copied from a shared link")
    with session() as s:
        mine = s.get(PromptSaved, out["id"])
        mine.copied_from = "shared link"
        mine.ask = json.dumps(ask)
        out = _view(mine, full=True)
    return out
