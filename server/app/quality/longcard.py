"""v0.436 LONG CARD (long-task report item 0b): how often does Hoola FINISH a long job - measured on the end state,
never on the model's own word.

Each ask of `long_asks.ASKS` runs k times (default 3) through the REAL `santosh.run_turn` on its own throw-away tenant
(`__longcard__<run>`: never her chats, never her AI budget), and the background goal rounds it schedules are waited
for until the job settles (done / blocked / stopped / failed / nothing running) or the card's clock runs out.
Then code reads what is REALLY there (files on disk with their pages / rows / slides / words, Hoola pages, lists,
reminders, routines, saved facts, the replies, the tools that ran) and scores the run.

Per run:
  passed       every check of the ask holds on the end state
  claimed_done Hoola SAID it was done: its goal card ended `done`, or (no goal) the turn's own outcome was `done`
  false_done   claimed done but a check fails (the number that matters most: a confident wrong "ho gaya")
  false_stuck  stopped to ask her / blocked although the ask needed nothing from her, and it did not pass
  cap_stopped  a budget stopped it: the goal waits on "aage badhaun?" (hold=limit), the turn hit its clock, or the
               card's own clock ran out
Per card: finished %, false-done %, false-stuck %, cap-stopped %, rupees per FINISHED job, pass@k and pass^k
(pass^k = every one of the k runs passed - Anthropic's "demystifying evals": a job she can rely on is pass^k).

CLI:  python -m app.quality longcard --check            # free: the set is valid, nothing runs
      python -m app.quality longcard [--k 3] [--only id,id] [--limit N] [--parallel 3] [--max-min 75] [--label x]
      python -m app.quality longcard --status           # the newest saved card (also while one is still running)
A full run is 25 asks x 3 = 75 long jobs on Claude: it costs real money (see `estimate()`), so it is started by
hand (vps-ops `long_card` starts it detached; `long_card_status` reads it)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .long_asks import ASKS, SET_V

log = logging.getLogger("santosh.quality.long")
PREFIX = "__longcard__"              # the card's tenants; goal sweeps of the live server never touch them (goal.CARD_PREFIX)
CHECK_KEYS = {"file", "artifact", "list", "reminder", "routine", "memory", "reply", "tools_any", "asked_her"}
FILE_KINDS = {"pdf", "xlsx", "docx", "pptx", "csv"}
SETTLE_POLL_S = 3.0
EST_INR_PER_RUN = (60, 220)          # rough: a long job on Claude at effort xhigh (filled from real cards later)

_URL = re.compile(r"https?://\S+", re.I)
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_ASK_HER = re.compile(r"\?|\bbata(?:iye|yein|ein|o| dijiye| do)\b|\bchahiye\b|\bkaun\s*sa\b|\bkis\b|\bkaunsi\b|"
                      r"\bplease (?:share|tell|confirm)\b|\bwhich\b|\bwhat is\b", re.I)


def is_card_tenant(tenant: str | None) -> bool:
    return str(tenant or "").startswith(PREFIX)


def _dir() -> Path:
    p = Path(os.getenv("QUALITY_DIR") or "./data/quality")
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------- the set itself (free)
def check_set(asks: list[dict] | None = None) -> list[str]:
    """Problems with the set (empty = fine): ids unique, every check a known kind, file kinds known, needs-her asks
    judged only by asked_her."""
    asks = asks if asks is not None else ASKS
    out, seen = [], set()
    for a in asks:
        aid = a.get("id") or "?"
        if aid in seen:
            out.append(f"{aid}: id twice")
        seen.add(aid)
        if not str(a.get("text") or "").strip():
            out.append(f"{aid}: no text")
        checks = a.get("checks") or []
        if not checks:
            out.append(f"{aid}: no checks")
        for c in checks:
            kinds = CHECK_KEYS & set(c)
            if len(kinds) != 1:
                out.append(f"{aid}: a check needs exactly one of {sorted(CHECK_KEYS)}: {c}")
                continue
            if "file" in c and c["file"] not in FILE_KINDS:
                out.append(f"{aid}: unknown file kind {c['file']}")
            if c.get("min") and c["min"] > len(c.get("words") or []):
                out.append(f"{aid}: min {c['min']} > {len(c.get('words') or [])} words")
        if a.get("needs_her") and any("asked_her" not in c for c in checks):
            out.append(f"{aid}: a needs-her ask is judged by asked_her only")
    return out


def estimate(n_runs: int) -> tuple[int, int]:
    return n_runs * EST_INR_PER_RUN[0], n_runs * EST_INR_PER_RUN[1]


# ---------------------------------------------------------------- reading the end state (code, no model)
def _words_hit(text: str, words: list[str]) -> int:
    """`words` entries may hold alternatives separated by | (any one counts)."""
    low = (text or "").lower()
    n = 0
    for w in words or []:
        alts = [x.strip().lower() for x in str(w).split("|") if x.strip()]
        if any((re.search(x, low) if x.startswith("\\") else x in low) for x in alts):
            n += 1
    return n


def _words_ok(text: str, c: dict) -> bool:
    words = c.get("words") or []
    if not words:
        return True
    need = int(c.get("min") or len(words))
    return _words_hit(text, words) >= need


def read_file(path: str, kind: str) -> dict[str, Any]:
    """What a delivered file really holds: text + pages / rows / slides. Unreadable = {'ok': False}."""
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return {"ok": False, "why": "missing or empty"}
    try:
        if kind == "pdf":
            from pypdf import PdfReader
            r = PdfReader(str(p))
            text = "\n".join((pg.extract_text() or "") for pg in r.pages)
            links = []
            for pg in r.pages:
                for an in (pg.get("/Annots") or []):
                    try:
                        uri = an.get_object().get("/A", {}).get("/URI")
                        if uri:
                            links.append(str(uri))
                    except Exception:
                        pass
            return {"ok": True, "text": text, "pages": len(r.pages), "links": links}
        if kind == "xlsx":
            from openpyxl import load_workbook
            wb = load_workbook(str(p), read_only=True, data_only=True)
            rows, cells, links = 0, [], []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    vals = [v for v in row if v not in (None, "")]
                    if vals:
                        rows += 1
                        cells += [str(v) for v in vals]
            text = "\n".join(cells)
            return {"ok": True, "text": text, "rows": max(0, rows - 1), "links": _URL.findall(text) + links}
        if kind == "docx":
            import docx
            d = docx.Document(str(p))
            parts = [x.text for x in d.paragraphs]
            for t in d.tables:
                for row in t.rows:
                    parts += [cell.text for cell in row.cells]
            text = "\n".join(parts)
            return {"ok": True, "text": text, "links": _URL.findall(text)}
        if kind == "pptx":
            from pptx import Presentation
            pr = Presentation(str(p))
            parts = []
            for sl in pr.slides:
                for sh in sl.shapes:
                    if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
                        parts.append(sh.text_frame.text)
            text = "\n".join(parts)
            return {"ok": True, "text": text, "slides": len(pr.slides), "links": _URL.findall(text)}
        text = p.read_text(errors="replace")
        return {"ok": True, "text": text, "rows": max(0, len([x for x in text.splitlines() if x.strip()]) - 1),
                "links": _URL.findall(text)}
    except Exception as e:   # noqa: BLE001 - a file that cannot be opened is a file she cannot use
        return {"ok": False, "why": f"unreadable: {type(e).__name__}"}


def evidence(tenant: str, conv: str) -> dict[str, Any]:
    """Everything the job left behind, read from the database and the disk."""
    from sqlalchemy import select

    from ..db import (Artifact, ArtifactVersion, Event, ListItem, MemoryFact, Message, PcFile, Reminder, Routine,
                      session)
    ev: dict[str, Any] = {"files": [], "artifacts": [], "lists": {}, "reminders": [], "routines": [], "memory": [],
                          "replies": [], "tools": [], "tools_ok": []}
    with session() as s:
        for f in s.scalars(select(PcFile).where(PcFile.tenant_id == tenant, PcFile.direction == "to_phone")).all():
            ext = (f.name or "").rsplit(".", 1)[-1].lower() if "." in (f.name or "") else ""
            ev["files"].append({"name": f.name, "kind": ext, "path": f.stored_path or "", "size": f.size or 0})
        for a in s.scalars(select(Artifact).where(Artifact.tenant_id == tenant, Artifact.deleted.is_(False))).all():
            html = ""
            if a.version:
                v = s.scalars(select(ArtifactVersion).where(ArtifactVersion.artifact_id == a.id,
                                                            ArtifactVersion.version == a.version)).first()
                html = (v.html or "") if v is not None else ""
            ev["artifacts"].append({"title": a.title, "status": a.status, "text": f"{a.title}\n{a.summary}\n{html}"})
        for li in s.scalars(select(ListItem).where(ListItem.tenant_id == tenant)).all():
            ev["lists"].setdefault((li.list_name or "").strip().lower(), []).append(li.text)
        ev["reminders"] = [r.text for r in s.scalars(select(Reminder).where(Reminder.tenant_id == tenant,
                                                                             Reminder.status == "active")).all()]
        ev["routines"] = [r.title for r in s.scalars(select(Routine).where(Routine.tenant_id == tenant,
                                                                            Routine.status == "active")).all()]
        ev["memory"] = [m.text for m in s.scalars(select(MemoryFact).where(MemoryFact.tenant_id == tenant)).all()]
        for m in s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "assistant")
                           .order_by(Message.id)).all():
            txt = m.display if m.display else (m.content if isinstance(m.content, str) else json.dumps(m.content))
            ev["replies"].append(str(txt or ""))
        for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "step")
                           .order_by(Event.id)).all():
            p = e.payload or {}
            if p.get("state") in ("done", "error") and p.get("tool"):
                ev["tools"].append(p["tool"])
                if p.get("state") == "done":
                    ev["tools_ok"].append(p["tool"])
    return ev


def judge(ask: dict, ev: dict[str, Any], waiting_on_her: bool = False, goal: dict | None = None) -> list[dict]:
    """One row per check: {check, ok, why}. Pure: the whole scoring logic, testable without a model."""
    rows = []
    replies = "\n\n".join(ev.get("replies") or [])
    for c in ask.get("checks") or []:
        ok, why = False, ""
        if "file" in c:
            kind = c["file"]
            cands = [f for f in ev.get("files") or [] if f["kind"] == kind]
            if not cands:
                why = f"no {kind} file delivered"
            for f in cands:
                info = f.get("_read") or read_file(f["path"], kind)
                if not info.get("ok"):
                    why = f"{f['name']}: {info.get('why')}"
                    continue
                bad = []
                if c.get("min_pages") and info.get("pages", 0) < c["min_pages"]:
                    bad.append(f"{info.get('pages', 0)} pages < {c['min_pages']}")
                if c.get("min_rows") and info.get("rows", 0) < c["min_rows"]:
                    bad.append(f"{info.get('rows', 0)} rows < {c['min_rows']}")
                if c.get("min_slides") and info.get("slides", 0) < c["min_slides"]:
                    bad.append(f"{info.get('slides', 0)} slides < {c['min_slides']}")
                links = len(set(info.get("links") or []) | set(_URL.findall(info.get("text") or "")))
                if c.get("min_links") and links < c["min_links"]:
                    bad.append(f"{links} links < {c['min_links']}")
                if not _words_ok(info.get("text") or "", c):
                    bad.append(f"words {_words_hit(info.get('text') or '', c.get('words') or [])}/"
                               f"{c.get('min') or len(c.get('words') or [])}")
                if not bad:
                    ok, why = True, f["name"]
                    break
                why = f"{f['name']}: " + ", ".join(bad)
        elif "artifact" in c:
            ready = [a for a in ev.get("artifacts") or [] if a.get("status") == "ready"]
            hit = [a for a in ready if _words_ok(a.get("text") or "", c)]
            ok = bool(hit)
            why = hit[0]["title"] if hit else ("no ready page" if not ready else "page lacks the words")
        elif "list" in c:
            items = []
            for name, its in (ev.get("lists") or {}).items():
                if c["list"].lower() in name:
                    items += its
            ok = len(items) >= int(c.get("min_items") or 1) and _words_ok("\n".join(items), c)
            why = f"{len(items)} items"
        elif "reminder" in c:
            n = len(ev.get("reminders") or [])
            ok = n >= int(c["reminder"]) and _words_ok("\n".join(ev.get("reminders") or []), c)
            why = f"{n} active reminders"
        elif "routine" in c:
            n = len(ev.get("routines") or [])
            ok, why = n >= int(c["routine"]), f"{n} active routines"
        elif "memory" in c:
            text = "\n".join(ev.get("memory") or [])
            ok, why = bool(text) and _words_ok(text, c), f"{len(ev.get('memory') or [])} facts"
        elif "reply" in c:
            bad = []
            if not _words_ok(replies, c):
                bad.append("words missing")
            if c.get("regex") and not re.search(c["regex"], replies):
                bad.append("shape missing")
            if c.get("min_numbers") and len(_NUM.findall(replies)) < c["min_numbers"]:
                bad.append("too few numbers")
            ok, why = not bad, ", ".join(bad) or "ok"
        elif "tools_any" in c:
            hit = sorted(set(c["tools_any"]) & set(ev.get("tools_ok") or []))
            ok, why = bool(hit), ",".join(hit) or f"none of {c['tools_any']} ran"
        elif "asked_her" in c:
            made = len(ev.get("files") or []) + len([a for a in ev.get("artifacts") or [] if a.get("status") == "ready"])
            last = (ev.get("replies") or [""])[-1]
            asked = waiting_on_her or bool(goal and goal.get("status") == "blocked" and goal.get("hold") != "limit") \
                or bool(_ASK_HER.search(last))
            ok = asked and made == 0
            why = ("asked" if asked else "did not ask") + (f", but made {made} thing(s)" if made else "")
        rows.append({"check": next(iter(CHECK_KEYS & set(c))), "ok": bool(ok), "why": why[:160]})
    return rows


def score_run(ask: dict, rows: list[dict], goal: dict | None, outcome: str, clock_out: bool,
              turn_timeout: bool) -> dict[str, Any]:
    """The run's verdict from its check rows + what Hoola itself claimed."""
    passed = bool(rows) and all(r["ok"] for r in rows)
    gstatus = (goal or {}).get("status") or ""
    claimed = gstatus == "done" if goal else outcome == "done"
    cap = clock_out or turn_timeout or (gstatus == "blocked" and (goal or {}).get("hold") == "limit")
    stopped_to_ask = (gstatus == "blocked" and (goal or {}).get("hold") != "limit") or outcome in ("stuck",)
    return {"passed": passed, "claimed_done": bool(claimed), "false_done": bool(claimed and not passed),
            "false_stuck": bool(stopped_to_ask and not ask.get("needs_her") and not passed),
            "cap_stopped": bool(cap and not passed), "goal_status": gstatus, "outcome": outcome}


# ---------------------------------------------------------------- running one ask once (real turns, real money)
def _new_conv(tenant: str) -> str:
    from ..db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id=tenant, title="long card")
        s.add(c)
        s.flush()
        return c.id


def _latest_goal(conv: str) -> dict | None:
    from sqlalchemy import select

    from ..agent.goal import GoalRun, _row_view
    from ..db import session
    with session() as s:
        r = s.scalars(select(GoalRun).where(GoalRun.conversation_id == conv)
                      .order_by(GoalRun.updated_at.desc())).first()
        return _row_view(r) if r is not None else None


def _latest_outcome(conv: str) -> str:
    from sqlalchemy import select

    from ..agent.pakka import TaskRun
    from ..db import session
    with session() as s:
        r = s.scalars(select(TaskRun).where(TaskRun.conversation_id == conv)
                      .order_by(TaskRun.created_at.desc())).first()
        return (r.outcome or "") if r is not None else ""


def _busy(conv: str, goal_id: str | None) -> bool:
    from ..agent import goal as G
    from ..agent.santosh import _locks
    if conv in _locks and _locks[conv].locked():
        return True
    return bool(goal_id and goal_id in G._PENDING)


def _turn_timed_out(conv: str, since: datetime) -> bool:
    from sqlalchemy import select

    from ..agent.eventlog import HarnessEvent, ensure_table
    from ..db import session
    ensure_table()
    with session() as s:
        rows = s.scalars(select(HarnessEvent.payload).where(HarnessEvent.conversation_id == conv,
                                                            HarnessEvent.kind == "turn_failed")).all()
    return any("timeout" in str(p or "").lower() for p in rows)


def _cleanup(tenant: str) -> None:
    """Nothing the card made may fire later: its reminders and routines are cancelled (routines would run real
    turns every week on a throw-away tenant)."""
    from sqlalchemy import update

    from ..db import Reminder, Routine, session
    with session() as s:
        s.execute(update(Reminder).where(Reminder.tenant_id == tenant).values(status="cancelled"))
        s.execute(update(Routine).where(Routine.tenant_id == tenant).values(status="cancelled"))


async def run_one(ask: dict, k: int, stamp: str, max_min: float = 75.0) -> dict[str, Any]:
    from .. import usage
    from ..agent import goal as G
    from ..agent import santosh
    tenant = f"{PREFIX}{stamp}_{ask['id']}_{k}"[:64]
    conv = _new_conv(tenant)
    t0 = time.time()
    since = datetime.now(timezone.utc)
    err = ""
    try:
        await asyncio.wait_for(santosh.run_turn(conv, ask["text"], tenant_id=tenant), timeout=max_min * 60)
    except asyncio.TimeoutError:
        err = "card clock (first turn)"
    except Exception as e:   # noqa: BLE001 - a crash is a result, never the end of the card
        err = f"crash: {type(e).__name__}: {e}"[:200]
    clock_out = bool(err.startswith("card clock"))
    # the goal's background rounds: wait until nothing runs any more, or the card's clock ends
    while not clock_out:
        g = _latest_goal(conv)
        if not _busy(conv, g and g["id"]):
            await asyncio.sleep(SETTLE_POLL_S * 2)        # a round is scheduled 2.5 s after a turn ends
            g = _latest_goal(conv)
            if not _busy(conv, g and g["id"]):
                break
        if time.time() - t0 > max_min * 60:
            clock_out = True
            break
        await asyncio.sleep(SETTLE_POLL_S)
    goal = _latest_goal(conv)
    outcome = _latest_outcome(conv)
    ev = await asyncio.to_thread(evidence, tenant, conv)
    rows = judge(ask, ev, waiting_on_her=G._waiting_on_her(conv), goal=goal)
    verdict = score_run(ask, rows, goal, outcome, clock_out, _turn_timed_out(conv, since))
    try:
        inr = round(usage.month_usd(tenant) * usage.usd_inr(), 2)
    except Exception:
        inr = None
    _cleanup(tenant)
    return {"id": ask["id"], "kind": ask.get("kind"), "k": k, "tenant": tenant, "conv": conv,
            "minutes": round((time.time() - t0) / 60, 1), "inr": inr, "error": err, "checks": rows,
            "files": [f["name"] for f in ev["files"]], "tools": len(ev["tools"]),
            "rounds": (goal or {}).get("rounds"), "steps": f"{(goal or {}).get('done', 0)}/{(goal or {}).get('total', 0)}",
            **verdict}


# ---------------------------------------------------------------- the card
def summarise(runs: list[dict], k: int) -> dict[str, Any]:
    n = len(runs)
    pct = lambda x: round(100 * x / n) if n else None   # noqa: E731
    by: dict[str, list[dict]] = {}
    for r in runs:
        by.setdefault(r["id"], []).append(r)
    complete = {i: rs for i, rs in by.items() if len(rs) >= k}
    passed = sum(1 for r in runs if r["passed"])
    spent = [r["inr"] for r in runs if r.get("inr") is not None]
    return {"runs": n, "asks": len(by), "k": k,
            "finished_pct": pct(passed), "false_done_pct": pct(sum(1 for r in runs if r["false_done"])),
            "false_stuck_pct": pct(sum(1 for r in runs if r["false_stuck"])),
            "cap_stopped_pct": pct(sum(1 for r in runs if r["cap_stopped"])),
            "inr_total": round(sum(spent), 2) if spent else None,
            "inr_per_finished": round(sum(spent) / passed, 2) if spent and passed else None,
            "pass_at_k_pct": round(100 * sum(1 for rs in complete.values() if any(r["passed"] for r in rs))
                                   / len(complete)) if complete else None,
            "pass_hat_k_pct": round(100 * sum(1 for rs in complete.values() if all(r["passed"] for r in rs))
                                    / len(complete)) if complete else None,
            "minutes_median": sorted(r["minutes"] for r in runs)[n // 2] if n else None}


def _save(card: dict, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(card, ensure_ascii=False, indent=1))
    tmp.replace(path)


async def card(asks: list[dict] | None = None, k: int = 3, parallel: int = 3, max_min: float = 75.0,
               label: str = "") -> dict[str, Any]:
    """Runs the set and saves after EVERY run (a card that dies half-way keeps what it measured)."""
    from ..main import APP_VERSION
    asks = list(asks if asks is not None else ASKS)
    stamp = datetime.now(timezone.utc).strftime("%m%d%H%M")
    path = _dir() / f"longcard-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}{('-' + label) if label else ''}.json"
    out: dict[str, Any] = {"set": SET_V, "version": APP_VERSION, "label": label, "started": stamp, "k": k,
                           "status": "running", "file": str(path), "runs": [], "summary": {}}
    _save(out, path)
    sem = asyncio.Semaphore(max(1, parallel))
    lock = asyncio.Lock()

    async def one(a: dict, i: int) -> None:
        async with sem:
            r = await run_one(a, i, stamp, max_min)
        async with lock:
            out["runs"].append(r)
            out["summary"] = summarise(out["runs"], k)
            _save(out, path)
            log.info("long card %s#%d: %s", a["id"], i, "PASS" if r["passed"] else "fail")

    await asyncio.gather(*(one(a, i) for i in range(1, k + 1) for a in asks))
    out["status"] = "done"
    out["summary"] = summarise(out["runs"], k)
    _save(out, path)
    return out


def saved() -> list[dict]:
    rows = []
    for p in sorted(_dir().glob("longcard-*.json")):
        try:
            rows.append(json.loads(p.read_text()))
        except ValueError:
            continue
    return rows


def lines(cd: dict) -> list[str]:
    s = cd.get("summary") or {}
    if not s:
        return [f"Long card {cd.get('set')} ({cd.get('status')}): no run finished yet."]
    rs = lambda v: "-" if v is None else f"Rs {v:,.0f}"   # noqa: E731
    out = [f"Long card {cd.get('set')} on v{cd.get('version')} ({cd.get('status')}, {s['runs']} runs of "
           f"{s['asks']} asks, k={s['k']}){' - ' + cd['label'] if cd.get('label') else ''}",
           f"  finished {s['finished_pct']}% | false done {s['false_done_pct']}% | false stuck {s['false_stuck_pct']}% "
           f"| stopped by a cap {s['cap_stopped_pct']}%",
           f"  pass@{s['k']} {s['pass_at_k_pct']}% | pass^{s['k']} {s['pass_hat_k_pct']}% | "
           f"{rs(s['inr_per_finished'])} per finished job | total {rs(s['inr_total'])} | median {s['minutes_median']} min"]
    bad = [r for r in cd.get("runs") or [] if not r["passed"]]
    if bad:
        out.append("Not finished:")
        for r in sorted(bad, key=lambda x: (x["id"], x["k"]))[:40]:
            why = "; ".join(f"{c['check']}: {c['why']}" for c in r["checks"] if not c["ok"])
            tag = "FALSE DONE" if r["false_done"] else "false stuck" if r["false_stuck"] else \
                "cap" if r["cap_stopped"] else (r["goal_status"] or r["outcome"] or "-")
            out.append(f"  - {r['id']}#{r['k']} [{tag}] {why}{(' | ' + r['error']) if r.get('error') else ''}")
    return out
