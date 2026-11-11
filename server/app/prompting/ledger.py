"""BAHI - the outcome ledger (plan P4, part 7). One row per prompt she took out of Hoola Prompting, and what happened
to the result afterwards: kept, kept after an edit, redone, dropped, never used.

What a row holds is SHAPE, never her words: the section, the recipe, which slots were filled and from where, the
score, the engine, rupees, seconds, the grade. The prompt itself is kept only as a hash plus salted word-hashes (so a
run can be recognised when the engine starts with that text, even after a small edit). No price, phone, name or
sentence of hers is in this table - a test holds that.

Every function here fails quiet: the ledger must never break a build, a picture or a chat."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import statistics
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, new_id, now, session

log = logging.getLogger("prompting.ledger")

CLAIM_WINDOW = timedelta(hours=2)        # a handed prompt waits this long for its engine to start
REDO_WINDOW = timedelta(hours=6)         # the same prompt run again inside this = the first result was redone
UNUSED_AFTER = timedelta(hours=24)       # handed and never run
QUIET_AFTER = timedelta(days=3)          # a result still there, not redone, not deleted = kept (quiet)
MATCH = 0.6                              # word overlap that still counts as "this prompt, edited"
MIN_RUNS = 5                             # no rate is shown on fewer graded runs than this
MIN_SIDE = 8                             # score check: graded runs needed on each side
SIG_MAX = 160
GRADES = ("kept", "kept_after_edit", "redone", "dropped", "unused")
KEPT = ("kept", "kept_after_edit")
KEEP_EVENTS = {"published", "downloaded", "copied", "sent", "thumb_up"}
SECTIONS = ("web", "image", "script")


class PromptRun(Base):
    __tablename__ = "prompt_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str] = mapped_column(String(20), default="", index=True)
    recipe: Mapped[str] = mapped_column(String(60), default="")
    brief_hash: Mapped[str] = mapped_column(String(64), default="")
    sig: Mapped[str] = mapped_column(Text, default="[]")            # salted word hashes, never words
    slots: Mapped[str] = mapped_column(Text, default="{}")          # {slot: source} - names only
    score: Mapped[int] = mapped_column(Integer, default=0)
    dialect: Mapped[str] = mapped_column(String(30), default="")
    engine: Mapped[str] = mapped_column(String(40), default="")
    model: Mapped[str] = mapped_column(String(80), default="")
    lang: Mapped[str] = mapped_column(String(12), default="")
    origin: Mapped[str] = mapped_column(String(12), default="")     # page | improve | again
    how: Mapped[str] = mapped_column(String(12), default="")        # use | run | copy
    status: Mapped[str] = mapped_column(String(12), default="handed", index=True)   # handed | running | ready | settled
    grade: Mapped[str] = mapped_column(String(20), default="")
    strong: Mapped[bool] = mapped_column(Boolean, default=False)    # her own act (publish / download / thumb), not silence
    edited_before: Mapped[bool] = mapped_column(Boolean, default=False)   # she changed the prompt before running it
    edits: Mapped[int] = mapped_column(Integer, default=0)          # changes to the RESULT
    thumb: Mapped[str] = mapped_column(String(6), default="")
    refs: Mapped[str] = mapped_column(Text, default=" ")            # " site_x cj_y cr_z " - the engine's own ids
    usd: Mapped[float] = mapped_column(Float, default=0.0)
    seconds: Mapped[float] = mapped_column(Float, default=0.0)
    handed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ran_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PromptPref(Base):
    __tablename__ = "prompt_prefs"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    share: Mapped[bool] = mapped_column(Boolean, default=True)
    ledger: Mapped[bool] = mapped_column(Boolean, default=True)


_OK: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _OK:
        PromptRun.__table__.create(eng, checkfirst=True)
        PromptPref.__table__.create(eng, checkfirst=True)
        _OK.add(id(eng))


def _on() -> bool:
    try:
        from ..config import get_settings
        s = get_settings()
        return bool(getattr(s, "prompting_page", True)) and bool(getattr(s, "prompting_ledger", True))
    except Exception:
        return False


# ---------------------------------------------------------------- recognising a prompt without keeping it

_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def _norm(text: str) -> str:
    return " ".join(_WORD.findall((text or "").lower()))


def text_hash(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


def signature(tenant: str, text: str) -> list[str]:
    """Salted hashes of the prompt's distinct words. Enough to say 'this is that prompt, slightly edited'; not her words."""
    words = sorted(set(_norm(text).split()))
    out = [hashlib.sha256(f"{tenant}|{w}".encode("utf-8")).hexdigest()[:10] for w in words]
    return sorted(out)[:SIG_MAX]


def _overlap(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def _sig(r: PromptRun) -> list[str]:
    try:
        return list(json.loads(r.sig or "[]"))
    except ValueError:
        return []


# ---------------------------------------------------------------- her switches

def prefs(tenant: str) -> dict[str, bool]:
    ensure_table()
    with session() as s:
        p = s.get(PromptPref, tenant)
        return {"share": True if p is None else bool(p.share), "ledger": True if p is None else bool(p.ledger)}


def set_prefs(tenant: str, share: bool | None = None, ledger: bool | None = None) -> dict[str, bool]:
    ensure_table()
    with session() as s:
        p = s.get(PromptPref, tenant)
        if p is None:
            p = PromptPref(tenant_id=tenant, share=True, ledger=True)
            s.add(p)
        if share is not None:
            p.share = bool(share)
        if ledger is not None:
            p.ledger = bool(ledger)
        s.flush()
        return {"share": bool(p.share), "ledger": bool(p.ledger)}


# ---------------------------------------------------------------- writing

def hand(tenant: str, text: str, brief: dict[str, Any] | None = None, section: str = "", recipe: str = "",
         origin: str = "page", how: str = "use", incognito: bool = False) -> str | None:
    """She took a prompt out (Use this prompt / Open in ... / Copy). Returns the run id, or None when nothing is
    written: an incognito chat, her ledger switch off, the feature off."""
    if incognito or not _on() or not (text or "").strip():
        return None
    try:
        if not prefs(tenant)["ledger"]:
            return None
        b = brief or {}
        sec = str(b.get("section") or section or "")
        if sec not in SECTIONS:
            return None
        score, dialect, engine = 0, "", ""
        if b:
            from . import brief as B
            from . import dialect as D
            score = int(B.score(b).get("score") or 0)
            out = D.render(b)
            dialect, engine = str(out.get("dialect") or ""), str(out.get("engine") or "")
        else:
            from . import anatomy as A
            from . import dialect as D
            dialect, engine = D.DIALECT_V.get(sec, ""), str(A.SECTIONS[sec].get("engine") or "")
        slots = {k: str(v.get("source") or "") for k, v in (b.get("slots") or {}).items() if isinstance(v, dict)}
        with session() as s:
            r = PromptRun(id=new_id("prn"), tenant_id=tenant, section=sec,
                          recipe=str(b.get("recipe_id") or recipe or "")[:60], brief_hash=text_hash(text),
                          sig=json.dumps(signature(tenant, text)), slots=json.dumps(slots), score=score,
                          dialect=dialect[:30], engine=engine[:40], lang=str(b.get("lang") or "")[:12],
                          origin=origin if origin in ("page", "improve") else "page",
                          how=how if how in ("use", "run", "copy") else "use", status="handed", refs=" ")
            s.add(r)
            s.flush()
            return r.id
    except Exception:
        log.exception("ledger hand")
        return None


def _grade(r: PromptRun, grade: str, strong: bool) -> None:
    if r.grade in KEPT and r.strong and grade != "dropped":
        return                                   # her own keep stands; only her delete can undo it
    r.grade, r.strong, r.graded_at, r.status = grade, strong, now(), "settled"


def claim(tenant: str, section: str, text: str, *refs: str) -> str | None:
    """An engine is starting with `text`. If it is a prompt she took from Hoola Prompting (as is, or edited a little),
    the run is tied to the engine's ids. The same prompt started AGAIN means the earlier result was redone."""
    if not _on() or section not in SECTIONS or len((text or "").strip()) < 12:
        return None
    try:
        ensure_table()
        t, h, sig = now(), text_hash(text), signature(tenant, text)
        ref = " " + " ".join(x for x in refs if x) + " "
        with session() as s:
            rows = list(s.execute(select(PromptRun).where(
                PromptRun.tenant_id == tenant, PromptRun.section == section,
                PromptRun.handed_at >= t - REDO_WINDOW).order_by(PromptRun.handed_at.desc()).limit(40)).scalars())

            def near(r: PromptRun) -> float:
                return 1.0 if r.brief_hash == h else _overlap(_sig(r), sig)

            fresh = next((r for r in rows if r.status == "handed" and as_utc(r.handed_at) >= t - CLAIM_WINDOW
                          and near(r) >= MATCH), None)
            earlier = [r for r in rows if r.status in ("running", "ready") and not r.grade and near(r) >= MATCH]
            if fresh is None and not earlier:
                return None
            for r in earlier:
                _grade(r, "redone", True)
            if fresh is None:                    # she pressed Create again on the same prompt: a new run, same shape
                src = earlier[0]
                fresh = PromptRun(id=new_id("prn"), tenant_id=tenant, section=section, recipe=src.recipe, brief_hash=h,
                                  sig=json.dumps(sig), slots=src.slots, score=src.score, dialect=src.dialect,
                                  engine=src.engine, lang=src.lang, origin="again", how=src.how, handed_at=t, refs=" ")
                s.add(fresh)
            fresh.edited_before = fresh.brief_hash != h
            fresh.status, fresh.ran_at, fresh.refs = "running", t, ref
            s.flush()
            return fresh.id
    except Exception:
        log.exception("ledger claim")
        return None


def _by_ref(s, ref: str, tenant: str = "") -> list[PromptRun]:
    if not ref or " " in ref:
        return []
    q = select(PromptRun).where(PromptRun.refs.contains(f" {ref} "))
    if tenant:
        q = q.where(PromptRun.tenant_id == tenant)
    return list(s.execute(q.order_by(PromptRun.handed_at.desc()).limit(5)).scalars())


def ready(ref: str, more_refs: list[str] | None = None, model: str = "", usd: float = 0.0,
          seconds: float | None = None) -> None:
    """The engine finished the result for `ref`."""
    if not _on():
        return
    try:
        ensure_table()
        with session() as s:
            for r in _by_ref(s, ref):
                if r.status != "running":
                    continue
                t = now()
                r.status, r.ready_at = "ready", t
                r.seconds = float(seconds) if seconds is not None else max(0.0, (t - as_utc(r.ran_at or t)).total_seconds())
                r.usd, r.model = max(0.0, float(usd or 0)), (model or r.model or "")[:80]
                if more_refs:
                    r.refs = r.refs + " ".join(x for x in more_refs if x) + " "
    except Exception:
        log.exception("ledger ready")


def failed(ref: str) -> None:
    """The engine could not make it: not her verdict on the prompt, so the run is closed without a grade."""
    if not _on():
        return
    try:
        ensure_table()
        with session() as s:
            for r in _by_ref(s, ref):
                if r.status == "running":
                    r.status, r.grade = "settled", ""
    except Exception:
        log.exception("ledger failed")


def event(tenant: str, ref: str, ev: str, usd: float | None = None) -> None:
    """What she did with the result: published | downloaded | copied | sent | edited | deleted | redo | thumb_up | thumb_down."""
    if not _on():
        return
    try:
        ensure_table()
        with session() as s:
            for r in _by_ref(s, ref, tenant)[:1]:
                if usd is not None and usd > r.usd:
                    r.usd = float(usd)
                if ev == "edited":
                    r.edits += 1
                    if r.grade == "kept":
                        r.grade = "kept_after_edit"
                elif ev in KEEP_EVENTS:
                    if ev == "thumb_up":
                        r.thumb = "up"
                    _grade(r, "kept_after_edit" if r.edits else "kept", True)
                elif ev == "deleted":
                    _grade(r, "dropped", True)
                elif ev == "thumb_down":
                    r.thumb = "down"
                    _grade(r, "dropped", True)
                elif ev == "redo" and not r.grade:
                    _grade(r, "redone", True)
    except Exception:
        log.exception("ledger event")


def thumb(tenant: str, run_id: str, value: str) -> bool:
    """Her own thumb on a run, from the Results page."""
    ensure_table()
    with session() as s:
        r = s.get(PromptRun, run_id)
        if r is None or r.tenant_id != tenant or value not in ("up", "down"):
            return False
        r.thumb = value
        _grade(r, ("kept_after_edit" if r.edits else "kept") if value == "up" else "dropped", True)
        return True


def settle(tenant: str = "", at: datetime | None = None) -> int:
    """Silence read by rule: never run in a day = unused; a result still there after three days, not redone and not
    deleted = kept (marked quiet, counted apart from her own keeps)."""
    if not _on():
        return 0
    try:
        ensure_table()
        t, n = at or now(), 0
        with session() as s:
            q = select(PromptRun).where(PromptRun.status.in_(("handed", "ready")))
            if tenant:
                q = q.where(PromptRun.tenant_id == tenant)
            for r in s.execute(q.limit(2000)).scalars():
                if r.status == "handed" and r.how != "copy" and as_utc(r.handed_at) < t - UNUSED_AFTER:
                    r.status, r.grade, r.strong, r.graded_at = "settled", "unused", False, t
                    n += 1
                elif r.status == "handed" and r.how == "copy" and as_utc(r.handed_at) < t - UNUSED_AFTER:
                    r.status, r.grade = "settled", ""            # copied out of Hoola: what happened next is unknown
                    n += 1
                elif r.status == "ready" and as_utc(r.ready_at or r.handed_at) < t - QUIET_AFTER:
                    r.status, r.grade, r.strong, r.graded_at = "settled", "kept_after_edit" if r.edits else "kept", False, t
                    n += 1
        return n
    except Exception:
        log.exception("ledger settle")
        return 0


# ---------------------------------------------------------------- reading

def _usd_inr() -> float:
    try:
        from .. import usage
        return float(usage.usd_inr())
    except Exception:
        return 88.0


def _four(rows: list[PromptRun]) -> dict[str, Any]:
    graded = [r for r in rows if r.grade in GRADES and r.grade != "unused"]
    kept = [r for r in graded if r.grade in KEPT]
    out: dict[str, Any] = {"runs": len(rows), "graded": len(graded), "kept": len(kept),
                           "kept_by_her": sum(1 for r in kept if r.strong), "kept_quiet": sum(1 for r in kept if not r.strong),
                           "kept_after_edit": sum(1 for r in kept if r.grade == "kept_after_edit"),
                           "redone": sum(1 for r in graded if r.grade == "redone"),
                           "dropped": sum(1 for r in graded if r.grade == "dropped"),
                           "unused": sum(1 for r in rows if r.grade == "unused"),
                           "open": sum(1 for r in rows if not r.grade and r.status != "settled"),
                           "enough": len(graded) >= MIN_RUNS, "min_runs": MIN_RUNS,
                           "kept_rate": None, "redos_per_kept": None, "inr_per_kept": None, "minutes_to_kept": None}
    if out["enough"]:
        out["kept_rate"] = round(100 * len(kept) / len(graded))
        if kept:
            out["redos_per_kept"] = round(out["redone"] / len(kept), 2)
            spent = sum(r.usd for r in graded)
            out["inr_per_kept"] = round(spent * _usd_inr() / len(kept), 2) if spent > 0 else None
            mins = [(as_utc(r.graded_at) - as_utc(r.handed_at)).total_seconds() / 60 for r in kept if r.strong and r.graded_at]
            out["minutes_to_kept"] = round(statistics.median(mins), 1) if mins else None
    return out


def _score_check(rows: list[PromptRun]) -> dict[str, Any]:
    """Does a higher Prompt Score go with a higher kept rate? Said only when both sides have enough graded runs."""
    graded = [r for r in rows if r.grade in GRADES and r.grade != "unused" and r.score > 0]
    if len(graded) < 2 * MIN_SIDE:
        return {"verdict": "not_enough", "need": 2 * MIN_SIDE, "have": len(graded),
                "say": f"Not enough results yet to check the score ({len(graded)} of {2 * MIN_SIDE})."}
    mid = statistics.median(r.score for r in graded)
    hi, lo = [r for r in graded if r.score >= mid], [r for r in graded if r.score < mid]
    if len(hi) < MIN_SIDE or len(lo) < MIN_SIDE:
        return {"verdict": "not_enough", "need": 2 * MIN_SIDE, "have": len(graded),
                "say": "The scores are too alike to compare yet."}
    rate = lambda xs: round(100 * sum(1 for r in xs if r.grade in KEPT) / len(xs))   # noqa: E731
    a, b = rate(hi), rate(lo)
    verdict = "predicts" if a - b >= 10 else ("no_link" if abs(a - b) < 10 else "backwards")
    say = {"predicts": f"Higher-scored prompts were kept more often ({a}% against {b}%).",
           "no_link": f"The score did not go with the result here ({a}% against {b}%). Treat it as a checklist only.",
           "backwards": f"Higher-scored prompts were kept LESS often ({a}% against {b}%). The score needs changing here."}[verdict]
    return {"verdict": verdict, "high": a, "low": b, "split_at": mid, "say": say}


def _rows(tenant: str | None, days: int) -> list[PromptRun]:
    ensure_table()
    with session() as s:
        q = select(PromptRun).where(PromptRun.handed_at >= now() - timedelta(days=days))
        if tenant:
            q = q.where(PromptRun.tenant_id == tenant)
        else:                                    # the all-users view counts only users who share
            off = [p.tenant_id for p in s.execute(select(PromptPref).where(PromptPref.share.is_(False))).scalars()]
            if off:
                q = q.where(PromptRun.tenant_id.notin_(off))
        rows = list(s.execute(q.order_by(PromptRun.handed_at.desc()).limit(20000)).scalars())
        s.expunge_all()
        return rows


def numbers(tenant: str | None, days: int = 90) -> dict[str, Any]:
    """The four numbers the feature is judged by, overall and per section. tenant=None = every user who shares."""
    settle(tenant or "")
    rows = _rows(tenant, days)
    return {"days": days, "all": _four(rows),
            "sections": {sec: {**_four([r for r in rows if r.section == sec]),
                               "score_check": _score_check([r for r in rows if r.section == sec])} for sec in SECTIONS},
            "note": "Kept = you published, downloaded, sent or liked the result, or it was still there three days later "
                    "and you had not redone or deleted it. Rupees are the AI list price of the run, not a bill."}


def recent(tenant: str, limit: int = 30) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        q = select(PromptRun).where(PromptRun.tenant_id == tenant).order_by(PromptRun.handed_at.desc()).limit(limit)
        return [{"id": r.id, "section": r.section, "recipe": r.recipe, "score": r.score, "status": r.status,
                 "grade": r.grade, "by_her": bool(r.strong), "thumb": r.thumb, "edits": r.edits,
                 "edited_before": bool(r.edited_before), "origin": r.origin, "how": r.how,
                 "inr": round(r.usd * _usd_inr(), 2), "seconds": round(r.seconds),
                 "at": as_utc(r.handed_at).isoformat()} for r in s.execute(q).scalars()]


def recipe_rates(days: int = 180) -> dict[str, dict[str, int]]:
    """{recipe_id: {kept, of}} across users who share - only where enough runs were graded. Used to order recipes."""
    out: dict[str, dict[str, int]] = {}
    try:
        for r in _rows(None, days):
            if r.recipe and r.grade in GRADES and r.grade != "unused":
                d = out.setdefault(r.recipe, {"kept": 0, "of": 0})
                d["of"] += 1
                d["kept"] += 1 if r.grade in KEPT else 0
    except Exception:
        log.exception("ledger recipe rates")
        return {}
    return {k: v for k, v in out.items() if v["of"] >= MIN_RUNS}


def forget(tenant: str) -> int:
    """Her 'delete my prompt history': every row of hers goes."""
    ensure_table()
    with session() as s:
        rows = list(s.execute(select(PromptRun).where(PromptRun.tenant_id == tenant)).scalars())
        for r in rows:
            s.delete(r)
        return len(rows)
