"""v0.136 Kaam ki nigraani: Hoola watches EVERY job it started, as it happens, and tells her.

Before: long jobs (app design, Android build, website, video edit, website jobs in Hoola's browser, video studio, posters ...)
updated their own cards, but the chat brain and the voice call never heard about it, so when she asked "kya hua?" Hoola said
"main dekh raha hoon" even when the card already said done.

Now every event on the bus passes through `observe` (cheap, never raises). Job events are turned into one shape {key, kind,
label, title, state working|waiting|done|failed|stopped, detail, pct}, kept per owner (table `kaam_jobs`) and:
- a change to done / failed / stopped / waiting-for-her = a plain chat line (unless the job's own service just said the same)
  + a quiet note into her live call (Hoola says it in its own words);
- work in progress = a short line when a job starts and at most every `KAAM_PROGRESS_S` (5 min) when its stage changes;
- a job that says working but hasn't moved for `KAAM_STUCK_S` (15 min) = "atka lag raha hai" once;
- every chat turn and every call gets `block()` = the live list (what is running, what finished, what waits for her), and the
  tool `kaam_status` reads the same list, so Hoola answers from the real state, never "dekh raha hoon" without checking.
Only states and short public lines are kept (no tool inputs, no file contents)."""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, Conversation, Message, new_id, now, session

log = logging.getLogger("santosh.kaam")

WORKING = {"queued", "running", "working", "writing", "building", "fixing", "designing", "checking", "watching", "planning",
           "rendering", "generating", "uploading", "compiling", "started", "in_progress", "processing", "assembling"}
WAITING = {"waiting", "needs_tap", "waiting_payment", "waiting_sign", "asking", "planned", "looks", "approval"}
DONE = {"done", "completed", "complete", "approved", "live", "placed", "finished", "delivered", "success", "ok", "zip",
        "published", "signed", "final", "sent"}
FAILED = {"failed", "error"}
STOPPED = {"stopped", "cancelled", "canceled", "rejected"}

# per-kind words: label, status -> state overrides, where the title / detail come from
KINDS: dict[str, dict[str, Any]] = {
    "app_board": {"label": "App design", "map": {"ready": "waiting", "approved": "done", "draft": "working"},
                  "waiting_say": "design taiyaar: dekh kar 'Design pakka' dabaiye"},
    "app_android": {"label": "Android app", "map": {"ready": "done", "zip": "done"}},
    "site_board": {"label": "Website", "map": {"ready": "waiting", "building": "working", "live": "done"},
                   "waiting_say": "website taiyaar: preview dekh kar live karne ka faisla aapka"},
    "video_job": {"label": "Video edit", "map": {}},
    "operator_task": {"label": "Website ka kaam (Hoola ka browser)", "map": {}},
    "studio": {"label": "Video Studio", "map": {}},
    "motion": {"label": "Motion reel", "map": {}, "done_always": True},
    "notebook_output": {"label": "Notebook Studio", "map": {"ready": "done", "queued": "working"}},
    "blender3d": {"label": "3D model (Blender)", "map": {"writing": "working", "building": "working", "rendering": "working", "checking": "working"}},
    "goal": {"label": "Lamba kaam", "map": {"blocked": "waiting"},   # v0.187 goal mode: blocked on her = aapki baari
             "waiting_say": "lamba kaam aapke jawab par ruka hai"},
}
# quick results made inside one tool call (letters, posters, photos, lekh) are told by the turn itself: not watched
# kinds whose events are steps of ONE agent turn: the turn itself reports them
SKIP = {"work", "message", "typing", "steps", "step", "memory_saved", "kaam"}

_LOCK = threading.Lock()
_CONV_TENANT: dict[str, str] = {}
_MEM: dict[str, dict[str, dict[str, Any]]] = {}      # tenant -> key -> job (in-memory mirror, newest state)
MARKS = set("▶🔄✅❌⏹⏳⚠")
STATS = {"seen": 0, "told": 0, "skipped_dup": 0, "stuck": 0, "progress": 0, "voice": 0}


def _on() -> bool:
    return os.environ.get("KAAM_WATCH", "true").lower() not in ("0", "false", "off")


def _secs(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class KaamJob(Base):
    __tablename__ = "kaam_jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kj"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    key: Mapped[str] = mapped_column(String(120), index=True)          # kind:job id
    kind: Mapped[str] = mapped_column(String(40), default="")
    label: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    state: Mapped[str] = mapped_column(String(16), default="working")
    status: Mapped[str] = mapped_column(String(40), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    pct: Mapped[int] = mapped_column(Integer, default=-1)
    told: Mapped[str] = mapped_column(String(40), default="")          # last state she was told about
    told_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stuck_told: Mapped[str] = mapped_column(String(40), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)   # last real change


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _tenant_of(conv: str) -> str:
    t = _CONV_TENANT.get(conv)
    if t is not None:
        return t
    try:
        with session() as s:
            c = s.get(Conversation, conv)
            t = c.tenant_id if c else ""
    except Exception:
        t = ""
    if len(_CONV_TENANT) > 5000:
        _CONV_TENANT.clear()
    _CONV_TENANT[conv] = t
    return t


def _tidy(s: Any, n: int = 200) -> str:
    t = re.sub(r"\s+", " ", str(s or "")).strip()
    t = re.sub(r"(?<!\d)\d{6,}(?!\d)", lambda m: "•" * 4 + m.group(0)[-2:], t)     # long numbers never repeated
    return t[:n]


# ---------------------------------------------------------------- 1. event -> job shape
def shape(kind: str, p: dict[str, Any]) -> dict[str, Any] | None:
    if kind in SKIP or not isinstance(p, dict):
        return None
    conf = KINDS.get(kind)
    if kind == "studio":
        p = _studio(p)
    status = str(p.get("status") or p.get("state") or "").lower().strip()
    if conf is None:
        # an unknown kind counts only when it clearly carries a job status
        if not status or status not in (WORKING | WAITING | DONE | FAILED | STOPPED) or not (p.get("id") or p.get("number")):
            return None
        conf = {"label": kind.replace("_", " ").capitalize(), "map": {}}
    jid = str(p.get("id") or p.get("number") or p.get("job") or "")
    if not jid:
        return None
    if conf.get("done_always") and not status:
        state = "done"
    else:
        state = conf["map"].get(status) or ("working" if status in WORKING else "waiting" if status in WAITING else
                                            "done" if status in DONE else "failed" if status in FAILED else
                                            "stopped" if status in STOPPED else "")
    if not state:
        return None
    num = str(p.get("number") or "")
    name = _tidy(p.get("name") or p.get("title") or p.get("brief") or p.get("task") or p.get("label") or "", 80)
    title = " · ".join(x for x in (num, name) if x) or jid[-6:]
    detail = _tidy(p.get("error") if state == "failed" else (p.get("say") or p.get("now") or p.get("stage_label")
                                                            or p.get("stage") or p.get("summary") or ""), 220)
    board = p.get("board") if isinstance(p.get("board"), dict) else {}
    pct = p.get("pct", p.get("progress", board.get("pct")))
    try:
        pct = int(pct) if pct is not None else -1
    except (TypeError, ValueError):
        pct = -1
    stage = _tidy(p.get("now") or board.get("now") or p.get("stage") or p.get("stage_label") or status, 80)
    link = _tidy(p.get("url") or p.get("link") or p.get("preview_url") or p.get("file_url") or p.get("share_url")
                 or p.get("download_url") or p.get("path") or p.get("file") or "", 300)   # v0.187 the result's own link
    return {"key": f"{kind}:{jid}", "kind": kind, "label": conf["label"], "title": title, "state": state, "status": status,
            "detail": detail, "pct": pct, "stage": stage, "waiting_say": conf.get("waiting_say", ""), "push": bool(p.get("push")),
            "link": link}


def _studio(p: dict[str, Any]) -> dict[str, Any]:
    """Video Studio cards carry no status: work it out from the shots / approvals / outputs."""
    st = "working" if p.get("working") else ("waiting" if p.get("approvals") else ("done" if p.get("outputs") else ""))
    live = sum(1 for x in p.get("shots") or [] if x.get("state") == "working")
    now_ = ("video jod raha hoon" if p.get("assembling") else f"{live} shot ban rahe hain" if live else "")
    say = ""
    if st == "waiting":
        a = (p.get("approvals") or [{}])[0]
        say = f"kharche ki haan chahiye ({a.get('inr') or a.get('amount_inr') or ''})".replace(" ()", "")
    return {"id": p.get("project"), "name": p.get("project"), "status": st, "now": now_, "say": say}


def _turn_running(conv: str) -> bool:
    try:
        from .agent import santosh
        lk = santosh._locks.get(conv)
        return bool(lk and lk.locked())
    except Exception:
        return False


# ---------------------------------------------------------------- 2. observe (from bus.publish)
def observe(conv: str, kind: str, payload: dict[str, Any]) -> None:
    if not _on() or not conv:
        return
    try:
        job = shape(kind, payload)
        if not job:
            return
        tenant = _tenant_of(conv)
        if not tenant:
            return
        STATS["seen"] += 1
        job["in_turn"] = _turn_running(conv)
        _update(tenant, conv, job)
    except Exception:
        log.debug("kaam observe failed", exc_info=True)


def _update(tenant: str, conv: str, job: dict[str, Any]) -> None:
    say: str = ""
    with _LOCK:
        with session() as s:
            r = s.scalars(select(KaamJob).where(KaamJob.tenant_id == tenant, KaamJob.key == job["key"])).first()
            t = now()
            new = r is None
            if new:
                r = KaamJob(tenant_id=tenant, conversation_id=conv, key=job["key"], kind=job["kind"], label=job["label"],
                            started_at=t)
                s.add(r)
            moved = new or r.state != job["state"] or r.status != job["status"] or (job["pct"] >= 0 and job["pct"] != r.pct) \
                or (job["stage"] and job["stage"] != (json.loads(r.detail or "{}").get("stage") if (r.detail or "").startswith("{") else ""))
            prev_state = r.state if not new else ""
            r.conversation_id = conv or r.conversation_id
            r.title, r.state, r.status, r.pct = job["title"][:200], job["state"], job["status"][:40], job["pct"]
            r.detail = json.dumps({"detail": job["detail"], "stage": job["stage"], "waiting_say": job["waiting_say"],
                                   "link": job.get("link", "")}, ensure_ascii=False)
            r.updated_at = t
            if moved:
                r.moved_at = t
                r.stuck_told = ""
            say = _decide(r, job, prev_state, new, t)
            if say and job["state"] in ("done", "failed", "stopped"):
                # v0.187 the dry line is replaced by ONE result message in Hoola's own words (the worker slot sends
                # it a few seconds later; the canned words stay as the fallback inside kaam_followup). The dry
                # line is also still told to her live call at once when the queue refused (outage safety).
                # v0.189: a stopped job reports too (band hone ki khabar bhi uski hai).
                try:
                    from . import kaam_followup
                    if kaam_followup.enqueue(tenant, r.conversation_id, job):
                        say = ""
                except Exception:
                    log.debug("followup enqueue failed", exc_info=True)
            young = (t - (_aware(r.started_at) or t)).total_seconds() < 120
            if job.get("in_turn") and (new or young):
                say = ""                 # the turn she is in started it and is telling her itself
                r.told = r.state if r.state != "working" else f"working:{job['stage'][:30]}"
                r.told_at = t
            if new and not r.told_at:
                r.told_at = t            # the start counts as told: progress lines only after KAAM_PROGRESS_S
            if say:
                r.told = r.state if r.state != "working" else f"working:{job['stage'][:30]}"
                r.told_at = t
            _MEM.setdefault(tenant, {})[job["key"]] = _row_view(r)
            conv_out = r.conversation_id
    if say:
        _tell(tenant, conv_out, say, job)


def _decide(r: KaamJob, job: dict[str, Any], prev: str, new: bool, t: datetime) -> str:
    """What (if anything) to tell her about this change."""
    st = job["state"]
    head = f"{job['label']} {job['title']}".strip()
    if st in ("done", "failed", "stopped", "waiting"):
        if r.told == st:
            return ""
        if st == "done":
            return f"✅ {head}: ho gaya." + (f" {job['detail']}" if job["detail"] else "")
        if st == "failed":
            return f"❌ {head}: ruk gaya, dikkat aayi." + (f" ({job['detail']})" if job["detail"] else "") + \
                " Bataiye to dobara koshish karun ya doosra raasta lun."
        if st == "stopped":
            return f"⏹ {head}: band kar diya gaya."
        return f"⏳ {head}: aapki baari." + (f" {job['detail'] or job['waiting_say']}" if (job["waiting_say"] or job["detail"]) else "")
    # working
    if new or prev in ("", "waiting", "done", "failed", "stopped"):
        if job.get("in_turn"):
            return ""          # started by the turn she is in: the reply itself says so
        if prev in ("done", "failed", "stopped"):
            return f"▶ {head}: dobara shuru." + (f" Abhi: {job['stage']}" if job["stage"] else "")
        return f"▶ {head}: kaam shuru." + (f" Abhi: {job['stage']}" if job["stage"] and job["stage"] != job["status"] else "")
    last = _aware(r.told_at)
    if last and (t - last).total_seconds() < _secs("KAAM_PROGRESS_S", 300):
        return ""
    key = f"working:{job['stage'][:30]}"
    if r.told == key or not job["stage"] or job["stage"] == job["status"]:
        return ""
    STATS["progress"] += 1
    return f"🔄 {head}: kaam chal raha hai. Abhi: {job['stage']}" + (f" ({job['pct']}%)" if 0 <= job["pct"] < 100 else "")


def _recent_same(conv: str, job: dict[str, Any], say: str) -> bool:
    """The job's own service already said it a moment ago (its own chat note): don't say it twice."""
    try:
        cut = now() - timedelta(seconds=150)
        with session() as s:
            rows = s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "assistant")
                             .order_by(Message.id.desc()).limit(4)).all()
        words = [w for w in re.split(r"[\s·]+", job["title"].lower()) if len(w) >= 3][:3]
        for m in rows:
            at = _aware(getattr(m, "created_at", None))
            if at and at < cut:
                continue
            text = (m.display or (m.content if isinstance(m.content, str) else json.dumps(m.content, ensure_ascii=False)) or "").lower()
            if text[:1] in MARKS:
                continue                 # one of our own lines, not the job's own note
            if words and all(w in text for w in words[:2]) and (job["state"] != "working" or "shuru" in text):
                return True
    except Exception:
        log.debug("dup check failed", exc_info=True)
    return False


def _tell(tenant: str, conv: str, say: str, job: dict[str, Any]) -> None:
    if job["state"] != "working" and _recent_same(conv, job, say):
        STATS["skipped_dup"] += 1
        _voice(tenant, conv, say)
        return
    try:
        from .events import notify
        notify(conv, say)
        STATS["told"] += 1
    except Exception:
        log.debug("kaam notify failed", exc_info=True)
    _voice(tenant, conv, say)


def _voice(tenant: str, conv: str, say: str) -> None:
    """A quiet note into her live call(s): Hoola tells her in its own words."""
    try:
        from . import voice
        note = (f"[Kaam update, tell her briefly in your own words when there is a natural pause; don't read symbols] {say}")
        n = voice.inject(conv, note)
        for c2, calls in list(getattr(voice, "ACTIVE", {}).items()):
            if c2 == conv:
                continue
            for _loop, call in list(calls):
                if getattr(call, "tenant", "") == tenant:
                    n += voice.inject(c2, note)
                    break
        if n:
            STATS["voice"] += 1
    except Exception:
        log.debug("kaam voice note failed", exc_info=True)


# ---------------------------------------------------------------- 3. stuck jobs (worker tick)
def tick() -> int:
    """A job still 'working' that hasn't moved for KAAM_STUCK_S: tell her once (per stage)."""
    if not _on():
        return 0
    lim = _secs("KAAM_STUCK_S", 900)
    cut = now() - timedelta(seconds=lim)
    old = now() - timedelta(days=2)
    out = []
    with session() as s:
        rows = s.scalars(select(KaamJob).where(KaamJob.state == "working", KaamJob.moved_at < cut)).all()
        for r in rows:
            moved = _aware(r.moved_at) or now()
            if moved < old:
                r.state, r.status = "stopped", "stale"
                continue
            if r.stuck_told:
                continue
            r.stuck_told = "1"
            mins = int((now() - moved).total_seconds() // 60)
            out.append((r.tenant_id, r.conversation_id, {"key": r.key, "title": r.title, "state": "working", "label": r.label},
                        f"⚠ {r.label} {r.title}: {mins} minute se aage nahi badha, atka lag raha hai. Main dekh kar batata "
                        f"hoon; chahiye to 'roko' ya 'dobara karo' kahiye."))
    for tenant, conv, job, say in out:
        STATS["stuck"] += 1
        try:
            from .events import notify
            notify(conv, say)
        except Exception:
            pass
        _voice(tenant, conv, say)
    return len(out)


# ---------------------------------------------------------------- 4. what Hoola knows each turn / the tool
def _row_view(r: KaamJob) -> dict[str, Any]:
    d = {}
    try:
        d = json.loads(r.detail or "{}")
    except ValueError:
        pass
    return {"key": r.key, "kind": r.kind, "label": r.label, "title": r.title, "state": r.state, "status": r.status,
            "stage": d.get("stage", ""), "detail": d.get("detail", ""), "link": d.get("link", ""), "pct": r.pct,
            "started_at": (_aware(r.started_at) or now()).isoformat(), "updated_at": (_aware(r.updated_at) or now()).isoformat(),
            "minutes_since_change": int((now() - (_aware(r.moved_at) or now())).total_seconds() // 60)}


def jobs(tenant: str, hours: int = 24, limit: int = 30) -> list[dict[str, Any]]:
    cut = now() - timedelta(hours=hours)
    with session() as s:
        rows = s.scalars(select(KaamJob).where(KaamJob.tenant_id == tenant, KaamJob.updated_at >= cut)
                         .order_by(KaamJob.updated_at.desc()).limit(limit)).all()
        return [_row_view(r) for r in rows]


STATE_WORD = {"working": "chal raha hai", "waiting": "AAPKA JAWAB CHAHIYE", "done": "ho gaya", "failed": "dikkat / ruk gaya",
              "stopped": "band"}


def status(tenant: str, q: str = "") -> dict[str, Any]:
    js = jobs(tenant, 48, 40)
    if q:
        ql = q.lower()
        hit = [j for j in js if ql in (j["label"] + " " + j["title"] + " " + j["kind"]).lower()]
        js = hit or js
    groups = {k: [j for j in js if j["state"] == k] for k in ("working", "waiting", "done", "failed", "stopped")}
    lines = []
    for k in ("waiting", "working", "failed", "done"):
        for j in groups[k][:6]:
            extra = j["stage"] if k == "working" else j["detail"]
            lines.append(f"{j['label']} {j['title']}: {STATE_WORD[k]}" + (f" ({extra})" if extra else "")
                         + (f" {j['pct']}%" if k == "working" and 0 <= j["pct"] < 100 else "")
                         + (f", {j['minutes_since_change']} min se nahi badla" if k == "working" and j["minutes_since_change"] >= 10 else ""))
    return {"counts": {k: len(v) for k, v in groups.items()}, "jobs": js[:20], "say": "; ".join(lines[:8]) or
            "Abhi koi lamba kaam nahi chal raha.", "checked_at": now().isoformat()}


def block(tenant: str) -> str:
    """For this turn / call: the REAL state of her jobs (last 24 h). Empty when nothing."""
    try:
        js = jobs(tenant, 24, 12)
    except Exception:
        return ""
    live = [j for j in js if j["state"] in ("working", "waiting")]
    fresh = [j for j in js if j["state"] in ("done", "failed", "stopped")
             and (now() - datetime.fromisoformat(j["updated_at"])).total_seconds() < 6 * 3600]
    if not live and not fresh:
        return ""
    rows = [f"- {j['label']} {j['title']}: {STATE_WORD[j['state']]}"
            + (f" (abhi: {j['stage']})" if j["state"] == "working" and j["stage"] else "")
            + (f" ({j['detail'][:120]})" if j["state"] != "working" and j["detail"] else "") for j in (live + fresh)[:10]]
    return ("KAAM KI HAALAT (live, from the jobs themselves; checked " + datetime.now(timezone.utc).strftime("%H:%M UTC") + "):\n"
            + "\n".join(rows) + "\nWhen she asks about any of these, answer from THIS list (or kaam_status for the newest) - "
            "never say 'dekh raha hoon / check kar raha hoon' without giving the real state.")


def forget_old(days: int = 30) -> int:
    cut = now() - timedelta(days=days)
    with session() as s:
        rows = s.scalars(select(KaamJob).where(KaamJob.updated_at < cut)).all()
        for r in rows:
            s.delete(r)
        return len(rows)
