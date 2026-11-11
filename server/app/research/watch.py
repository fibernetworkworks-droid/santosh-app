"""v0.480 R9 NIGRANI - a research topic she WATCHES: it re-runs on a schedule and tells her only what CHANGED.

Plan: `docs/RESEARCH_PRO_PLAN.md` R9 (Parallel's monitors / Exa websets, in Hoola's words). A watch is created only after she says yes to its cost; each scheduled run is an
ordinary background run (R4) on the same engine and goals, under the same R5 ceilings, with its own monthly cap. When it finishes, the new findings are compared with the last
snapshot BY CODE (`diff`): a finding whose figures moved, a finding that is new, a finding not seen this time. A run that changed nothing material sends NOTHING - it is only
counted (she can ask `research_watch list`). A run that did change something wakes the brain with the diff (kind `research_watch`), which writes a SHORT change message - and that
message goes through the same held + checked answer as a report (R3 figure check with the earlier values admitted, then the R9 review).

Safety: creation needs `confirm=true` after the cost is shown; at most MAX_ACTIVE active watches per tenant; never faster than daily; a run the daily ceiling refuses is skipped
(noted, tried again later); a watch that has spent its monthly cap, or failed three runs in a row, PAUSES itself and says so once. The baseline run says nothing.
"""
from __future__ import annotations

import copy
import json
import logging
import re
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import figures as F

log = logging.getLogger("santosh.research.watch")

MAX_ACTIVE = 3
MIN_DAYS = 1
FREQ = {"daily": 1, "weekly": 7, "fortnightly": 14, "monthly": 30}
FAIL_PAUSE = 3
OVERLAP = 0.6
STATS = {"started": 0, "quiet": 0, "changed": 0, "paused": 0, "skipped": 0}
STOP = {"the", "and", "for", "was", "were", "with", "from", "that", "this", "are", "has", "have", "had", "its", "into", "than", "then", "over", "under", "per", "ka", "ki", "ke",
        "hai", "tha", "thi", "mein", "se", "par", "aur", "ko"}


class ResearchWatch(Base):
    __tablename__ = "research_watches"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    question: Mapped[str] = mapped_column(Text, default="")
    goals: Mapped[str] = mapped_column(Text, default="[]")
    over: Mapped[str] = mapped_column(Text, default="{}")
    engine: Mapped[str] = mapped_column(String(16), default="hoola")
    hi: Mapped[int] = mapped_column(Integer, default=0)
    every_days: Mapped[int] = mapped_column(Integer, default=7)
    status: Mapped[str] = mapped_column(String(10), default="active", index=True)          # active | paused | deleted
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_run_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    last_diff: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    checks: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    changes: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    fail_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    month_cap_inr: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


_ready = False


def ensure_table() -> None:
    global _ready
    if _ready:
        return
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        ResearchWatch.__table__.create(eng, checkfirst=True)
    _ready = True


def _aware(d: datetime | None) -> datetime | None:
    return None if d is None else (d if d.tzinfo else d.replace(tzinfo=timezone.utc))


def _j(s: Any, default: Any) -> Any:
    try:
        return json.loads(s) if s else default
    except ValueError:
        return default


def view(w: ResearchWatch) -> dict[str, Any]:
    return {"id": w.id, "tenant": w.tenant_id, "conv": w.conversation_id, "question": w.question, "goals": _j(w.goals, []), "over": _j(w.over, {}), "engine": w.engine,
            "hi": bool(w.hi), "every_days": w.every_days, "status": w.status, "next_run_at": _aware(w.next_run_at), "last_run_id": w.last_run_id or "",
            "last_checked_at": _aware(w.last_checked_at), "last_change_at": _aware(w.last_change_at), "snapshot": _j(w.snapshot, None), "last_diff": _j(w.last_diff, None),
            "checks": int(w.checks or 0), "changes": int(w.changes or 0), "fail_count": int(w.fail_count or 0), "month_cap_inr": float(w.month_cap_inr or 0.0), "note": w.note or ""}


# ---------------------------------------------------------------- the snapshot and the diff (pure)
def snapshot_of(dossier: dict) -> list[dict]:
    """What a later run is compared with: the findings that were verified, backed by their quoted words, at medium or high confidence."""
    out = []
    for f in dossier.get("fields", []):
        if f["verified"] and f["supported"] and f["confidence"] in ("high", "medium"):
            out.append({"claim": f["claim"], "figures": list(f.get("figures") or []), "host": F.host_of(f["url"]), "date": f.get("date", ""), "conf": f["confidence"],
                        "url": f["url"], "n": f.get("n")})
    return out


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-zऀ-ॿ]{3,}", str(s or "").lower()) if w not in STOP}


def _overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0


def diff(old: list[dict] | None, new: list[dict]) -> dict[str, Any]:
    """CHANGED (same finding, figures moved beyond rounding), NEW, GONE (not seen this time), UNCHANGED count. `baseline` when there is nothing to compare with."""
    if not old:
        return {"baseline": True, "changed": [], "new": [], "gone": [], "unchanged": 0, "material": False}
    used: set[int] = set()
    changed, fresh, unchanged = [], [], 0
    for nf in new:
        best, best_s = None, 0.0
        for i, of in enumerate(old):
            if i in used:
                continue
            s = _overlap(nf["claim"], of["claim"]) + (0.05 if of["host"] == nf["host"] else 0.0)
            if s > best_s and _overlap(nf["claim"], of["claim"]) >= OVERLAP:
                best, best_s = i, s
        if best is None:
            fresh.append(nf)
            continue
        used.add(best)
        of = old[best]
        same = (not nf["figures"] and not of["figures"]) or (len(nf["figures"]) == len(of["figures"]) and all(F.near(v, of["figures"]) for v in nf["figures"]))
        if same:
            unchanged += 1
        else:
            changed.append({"claim": nf["claim"], "old_claim": of["claim"], "old_figures": of["figures"], "new_figures": nf["figures"], "date": nf.get("date", ""),
                            "old_date": of.get("date", ""), "url": nf["url"], "n": nf.get("n"), "old_n": of.get("n")})
    gone = [of for i, of in enumerate(old) if i not in used]
    return {"baseline": False, "changed": changed, "new": fresh, "gone": gone, "unchanged": unchanged, "material": bool(changed or fresh)}


def check_dossier(new_dossier: dict, d: dict) -> dict:
    """The dossier the change message is CHECKED against: the new one plus the earlier values (a 'was 412.5, now 430' sentence must not trip the figure check).
    An earlier value takes the new finding's source number; a finding no longer seen has none."""
    out = copy.deepcopy(new_dossier)
    extra = []
    for i, c in enumerate(d.get("changed", [])):
        extra.append({"id": f"prior-c{i}", "goal": "prior", "claim": c["old_claim"], "url": c["url"], "n": c.get("n"), "excerpt": "", "verified": True, "supported": True,
                      "figures": list(c["old_figures"]), "figures_in_words": list(c["old_figures"]), "date": c.get("old_date", ""), "confidence": "medium", "why": ["the earlier run"]})
    for i, g in enumerate(d.get("gone", [])):
        extra.append({"id": f"prior-g{i}", "goal": "prior", "claim": g["claim"], "url": g["url"], "n": None, "excerpt": "", "verified": True, "supported": True,
                      "figures": list(g["figures"]), "figures_in_words": list(g["figures"]), "date": g.get("date", ""), "confidence": "medium", "why": ["the earlier run"]})
    out["fields"] = list(out.get("fields", [])) + extra
    return out


def _fmt(figs: list[float], claim: str = "") -> str:
    """The figures as the claim writes them ('430.0', '18,240'), else the plain number."""
    toks = re.findall(r"\d[\d,]*(?:\.\d+)?", claim or "")
    out = []
    for v in figs:
        hit = next((x for x in toks if F.numbers(x) and abs(F.numbers(x)[0] - v) <= max(abs(v) * 1e-9, 1e-9)), None)
        out.append(hit or f"{v:g}")
    return ", ".join(out) or "-"


def render_change(w: dict, d: dict, run: dict, new_dossier: dict) -> str:
    """The change digest the brain writes the message from."""
    out = [f"RESEARCH WATCH CHANGE REPORT - watch {w['id']} (every {w['every_days']} day(s)), checked {now().strftime('%d %b %Y')}"
           + (f", previous check {w['last_checked_at'].strftime('%d %b %Y')}" if w.get("last_checked_at") else ""),
           f"Question: {w['question'][:300]}", ""]
    if d["changed"]:
        out.append(f"CHANGED ({len(d['changed'])}):")
        out += [f"- {c['claim']} [{c['n']}]: was {_fmt(c['old_figures'], c.get('old_claim', ''))}{(' (' + c['old_date'] + ')') if c.get('old_date') else ''} -> now {_fmt(c['new_figures'], c['claim'])}"
                f"{(' (' + c['date'] + ')') if c.get('date') else ''}" for c in d["changed"]]
    if d["new"]:
        out.append(f"NEW ({len(d['new'])}):")
        out += [f"- {n['claim']} [{n['n']}]{(' (' + n['date'] + ')') if n.get('date') else ''}" for n in d["new"]]
    if d["gone"]:
        out.append(f"NOT SEEN THIS TIME ({len(d['gone'])}) - not proof it changed, only that this run did not find it again:")
        out += [f"- {g['claim']}" for g in d["gone"][:6]]
    out.append(f"UNCHANGED: {d['unchanged']} finding(s)")
    out.append("SOURCES of this run (cite as [n]):")
    out += [f"[{s['n']}] {s['url']}" for s in new_dossier.get("sources", [])[:12]]
    cost = run.get("cost") or {}
    if cost:
        out.append(f"This check cost Rs {cost.get('total_inr', 0):.1f}.")
    return "\n".join(out)


# ---------------------------------------------------------------- the lifecycle
def _count_active(tenant: str) -> int:
    ensure_table()
    with session() as s:
        return len(s.scalars(select(ResearchWatch).where(ResearchWatch.tenant_id == tenant, ResearchWatch.status == "active")).all())


def estimate_run_inr(tenant: str, n_goals: int) -> tuple[float | None, str]:
    from . import bill
    m = bill.measured_per_goal(tenant)
    if m:
        return round(m["per_goal_inr"] * max(1, n_goals), 0), f"from your last {m['runs']} runs"
    return None, "no measured cost yet - unknown until a run has finished"


def add(tenant: str, conv: str, question: str, goals: list[str], every_days: int, engine: str = "hoola", over: dict | None = None, hi: bool = False,
        baseline: dict | None = None) -> dict[str, Any]:
    ensure_table()
    every = max(MIN_DAYS, int(every_days))
    if _count_active(tenant) >= MAX_ACTIVE:
        raise ValueError(f"You already watch {MAX_ACTIVE} topics - pause or delete one first (list them with research_watch list).")
    from ..config import get_settings
    cap = float(getattr(get_settings(), "research_watch_month_inr", 300.0))
    with session() as s:
        w = ResearchWatch(tenant_id=tenant, conversation_id=conv, question=question[:3000], goals=json.dumps(goals, ensure_ascii=False), over=json.dumps(over or {}),
                          engine=engine or "hoola", hi=1 if hi else 0, every_days=every, month_cap_inr=cap,
                          next_run_at=(now() + timedelta(days=every)) if baseline else now())
        if baseline:
            w.snapshot = json.dumps(snapshot_of(baseline), ensure_ascii=False)
            w.last_checked_at = now()
        s.add(w)
        s.flush()
        return view(w)


def get(watch_id: str) -> dict | None:
    ensure_table()
    with session() as s:
        w = s.get(ResearchWatch, watch_id)
        return view(w) if w is not None else None


def list_for(tenant: str, include_deleted: bool = False) -> list[dict]:
    ensure_table()
    with session() as s:
        q = select(ResearchWatch).where(ResearchWatch.tenant_id == tenant)
        if not include_deleted:
            q = q.where(ResearchWatch.status != "deleted")
        return [view(w) for w in s.scalars(q.order_by(ResearchWatch.created_at)).all()]


def set_status(watch_id: str, tenant: str, status: str, note: str = "") -> bool:
    ensure_table()
    with session() as s:
        w = s.get(ResearchWatch, watch_id)
        if w is None or w.tenant_id != tenant:
            return False
        if status == "active" and w.status != "active" and _count_active(tenant) >= MAX_ACTIVE:
            raise ValueError(f"You already watch {MAX_ACTIVE} topics - pause or delete one first.")
        w.status = status
        if note:
            w.note = note[:300]
        if status == "active":
            w.fail_count = 0
            w.next_run_at = now() + timedelta(days=w.every_days)
        return True


def spent_this_month(watch_id: str, tenant: str) -> float:
    from . import store
    since = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = 0.0
    for v in store.recent(tenant, "", 200):
        if (v["policy"] or {}).get("watch") == watch_id and (v["created_at"] or since) >= since:
            total += float(v.get("cost_inr") or 0.0)
    return round(total, 2)


def _publish(w: dict, run_id: str, status: str, say: str) -> None:
    try:
        from ..events import bus
        bus.publish(w["conv"], "research_watch", {"id": run_id, "number": f"watch {w['id'][-4:]}", "name": w["question"][:60], "status": status, "say": say, "watch": w["id"]})
    except Exception:       # noqa: BLE001
        log.debug("watch publish failed", exc_info=True)


async def tick() -> int:
    """The worker slot: start a run for each watch that is due (and affordable), pause the ones that hit their rules. At most two per pass."""
    from ..config import get_settings
    from . import bill, runner, store, vendors
    st = get_settings()
    if not getattr(st, "research_engine_on", True) or not getattr(st, "research_background", True):
        return 0
    ensure_table()
    started = 0
    with session() as s:
        due = [view(w) for w in s.scalars(select(ResearchWatch).where(ResearchWatch.status == "active", ResearchWatch.next_run_at <= now()).order_by(ResearchWatch.next_run_at).limit(6)).all()]
    for w in due:
        if started >= 2:
            break
        if w["last_run_id"]:
            lr = store.get(w["last_run_id"])
            if lr and lr["status"] in ("queued", "running"):
                continue                                                  # its last run is still going
        if w["month_cap_inr"] and spent_this_month(w["id"], w["tenant"]) >= w["month_cap_inr"]:
            set_status(w["id"], w["tenant"], "paused", "monthly cap reached")
            STATS["paused"] += 1
            _publish(w, w["id"], "stopped", f"watch paused: it has spent its monthly cap of Rs {w['month_cap_inr']:.0f}")
            continue
        ok, why = vendors.check(w["engine"], "", st)
        if not ok:
            _skip(w["id"], f"engine not available: {why}", days=1)
            continue
        try:
            bill.preflight(w["tenant"])
        except bill.ResearchCapped as e:
            _skip(w["id"], f"skipped: {str(e)[:120]}", hours=6)
            continue
        rid = runner.start(w["tenant"], w["conv"], w["question"], w["goals"], w["over"].get("over") or {}, bool(w["hi"]), w["over"].get("asked") or [], w["engine"], watch=w["id"])
        with session() as s:
            row = s.get(ResearchWatch, w["id"])
            row.last_run_id, row.next_run_at = rid, now() + timedelta(days=w["every_days"])
        started += 1
        STATS["started"] += 1
    return started


def _skip(watch_id: str, note: str, days: int = 0, hours: int = 0) -> None:
    STATS["skipped"] += 1
    with session() as s:
        w = s.get(ResearchWatch, watch_id)
        if w is not None:
            w.note, w.next_run_at = note[:300], now() + timedelta(days=days, hours=hours)


def on_run_done(run: dict, status: str, dossier: dict | None) -> str:
    """Called by the runner when a watch run ends. Returns what happened: 'baseline' | 'quiet' | 'changed' | 'failed' | 'paused' | 'stopped'. Only a material change wakes the brain."""
    ensure_table()
    wid = (run.get("policy") or {}).get("watch", "")
    w = get(wid)
    if w is None:
        return "gone"
    with session() as s:
        row = s.get(ResearchWatch, wid)
        if status == "stopped":
            return "stopped"
        if status != "done" or dossier is None:
            row.fail_count = int(row.fail_count or 0) + 1
            row.note = (run.get("error") or "the run failed")[:300]
            if row.fail_count >= FAIL_PAUSE:
                row.status = "paused"
                STATS["paused"] += 1
                _publish(w, run["id"], "stopped", f"watch paused: {FAIL_PAUSE} checks in a row could not finish ({row.note[:80]})")
                return "paused"
            return "failed"
        new = snapshot_of(dossier)
        d = diff(w["snapshot"], new)
        row.fail_count = 0
        row.checks = int(row.checks or 0) + 1
        row.last_checked_at = now()
        row.snapshot = json.dumps(new, ensure_ascii=False)
        row.note = ""
        if d["baseline"]:
            row.last_diff = json.dumps(d, ensure_ascii=False)
            return "baseline"
        if not d["material"]:
            STATS["quiet"] += 1
            row.last_diff = json.dumps(d, ensure_ascii=False)
            return "quiet"
        row.changes = int(row.changes or 0) + 1
        row.last_change_at = now()
        row.last_diff = json.dumps(d, ensure_ascii=False)
        STATS["changed"] += 1
    n = len(d["changed"]) + len(d["new"])
    _publish(w, run["id"], "done", (f"{n} badlaav mile" if w["hi"] else f"{n} change(s) found") + f" - watch {wid}")
    return "changed"


def result_for(tenant: str, run_id: str) -> dict[str, Any] | None:
    """For the wake turn: the change digest for this run + the dossier to CHECK the message against (new + earlier values)."""
    from . import store
    run = store.get(run_id)
    if run is None or run["tenant"] != tenant or run["dossier"] is None:
        return None
    wid = (run["policy"] or {}).get("watch", "")
    w = get(wid)
    if w is None or not w.get("last_diff"):
        return None
    d = w["last_diff"]
    return {"watch": w, "diff": d, "digest": render_change(w, d, run, run["dossier"]), "check": check_dossier(run["dossier"], d), "dossier": run["dossier"]}
