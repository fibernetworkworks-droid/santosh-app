"""P2 A ONE-PART CHAT MESSAGE THROUGH THE BOX (plan 5.1, 6.1, 6.3, 6.10).

Only while `pipeline_on` is True (default OFF until P7 - off = today's routing exactly). For her own chat message:

  begin  code reads the kind + level and chooses the model from the tables copy this message keeps (milliseconds, no
         model call); a job sheet is opened with one part; when the part's work is text and the chat runs on its
         OpenAI-shaped brain, the turn runs on the chosen model (`llm.MODEL_NOW` = "openrouter:<id>")
  run    the turn itself is unchanged (same tools, memory, voice); every tool result is noted for the facts list
  end    the hand-off package + the final check go on the sheet; the model's success / failure goes into the outage
         record (two failures in 10 minutes = paused, the Box picks a backup next time); a good answer keeps the same
         model for this chat for 30 minutes

Not through the Box (the sheet says why, the turn runs as today): calls (a later phase), routines / wakes / long-job
rounds, several parts in one message (P3's planner), media work (the studios keep their price cards - P5), a server
whose chat runs on Claude or OmniRoute, no OpenRouter key.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import threading
import time
from typing import Any

from ..config import get_settings
from . import box as B
from . import check as K
from . import sheet as S
from . import store
from .choose import out_of

log = logging.getLogger("santosh.pipeline")

TOOL_SINK: contextvars.ContextVar[list | None] = contextvars.ContextVar("hoola_box_tools", default=None)
# True while a turn runs on the Box's choice: the chat loop keeps it (no switch to Claude for hard / long asks)
APPLIED: contextvars.ContextVar[bool] = contextvars.ContextVar("hoola_box_applied", default=False)
PAUSE_FAILS = 2
PAUSE_WINDOW_S = 600
MIN_SAMPLES = 3
_OUT: dict[str, list[tuple[float, bool]]] = {}       # model id -> [(when, ok)] (the outage record, this process)
_OLOCK = threading.Lock()
_TABLES: dict[str, Any] = {"mtime": None, "doc": None}
STATS = {"turns": 0, "applied": 0, "skipped": 0, "check_problems": 0, "failed": 0}


# ------------------------------------------------------------------ the tables copy (read once per file change)
def tables() -> dict | None:
    p = store.root() / "current.json"
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return None
    if _TABLES["mtime"] != mt:
        try:
            _TABLES["doc"] = json.loads(p.read_text())
            _TABLES["mtime"] = mt
        except Exception:   # noqa: BLE001 - a half-written file: keep the last copy
            return _TABLES["doc"]
    return _TABLES["doc"]


# ------------------------------------------------------------------ the outage record (plan D1: only for outages)
def note(model_id: str, ok: bool, now: float | None = None) -> None:
    t = now if now is not None else time.time()
    with _OLOCK:
        rows = [r for r in _OUT.get(model_id, []) if t - r[0] <= 3600] + [(t, ok)]
        _OUT[model_id] = rows[-50:]


def health(now: float | None = None) -> dict[str, dict]:
    t = now if now is not None else time.time()
    out: dict[str, dict] = {}
    with _OLOCK:
        for mid, rows in _OUT.items():
            recent = [r for r in rows if t - r[0] <= 3600]
            if not recent:
                continue
            fails = [r for r in recent if not r[1] and t - r[0] <= PAUSE_WINDOW_S]
            h: dict = {"paused": len(fails) >= PAUSE_FAILS}
            if len(recent) >= MIN_SAMPLES:          # one bad answer is not a record (plan D1: outages only)
                h["ok_rate"] = round(sum(1 for r in recent if r[1]) / len(recent), 2)
            out[mid] = h
    return out


# ------------------------------------------------------------------ one turn
def _why_not(actor: str, voice: bool, r: dict) -> str:
    if voice:
        return "a live call - not through the Box yet"
    if not (actor == "owner" or actor.startswith("approved:")):
        return f"a {actor} turn - not through the Box yet"
    if r.get("several_parts"):
        return "several parts in one message - the planner comes in P3"
    if out_of(r["kind"]) != "text":
        return f"{r['kind']} - the studio keeps its own engine and price card until P5"
    m = r.get("model") or {}
    if not m:
        return "no model in the tables can do this part"
    if m.get("route") != "openrouter":
        return f"the chosen model is on {m.get('route')} - only OpenRouter models run a chat turn for now"
    try:
        from ..agent import llm
        if llm.cheap_brain() != "glm":
            return "this server's chat does not run on its OpenRouter brain"
        from ..agent import providers as pv
        if not pv.ready("openrouter:" + m["id"]):
            return "no OpenRouter key on this server"
    except Exception as e:   # noqa: BLE001
        return f"chat brain not known ({str(e)[:60]})"
    return ""


def begin(conv: str, tenant: str, text: str, actor: str = "owner", voice: bool = False) -> dict | None:
    """Choose for this message and open its sheet. None = the Box is off or has no tables (today's turn)."""
    st = get_settings()
    if not bool(getattr(st, "pipeline_on", False)):
        return None
    doc = tables()
    if not doc:
        if not STATS.get("no_tables_said"):      # said once per process, so a silent Box is never a mystery
            STATS["no_tables_said"] = 1
            log.warning("pipeline box: no tables at %s - today's turn (run the feed: vps-ops pipeline_feed)",
                        (store.root() / "current.json").resolve())
        return None
    t0 = time.time()
    pin = ""
    try:
        from .. import modelchoice
        pin = modelchoice.chosen(tenant) or ""
    except Exception:   # noqa: BLE001
        pin = ""
    try:
        r = B.choose_for(text or "", surface="chat", doc=doc, pin=pin, chat=conv, health=health(), tools=True,
                         now=t0)
    except Exception as e:   # noqa: BLE001 - the Box never breaks her turn
        log.warning("pipeline box: choosing failed (%s) - today's turn", str(e)[:120])
        return None
    why_not = _why_not(actor or "owner", bool(voice), r)
    part = {"kind": r["kind"], "language": r["language"], "level": r["level"], "level_used": r.get("level_used"),
            "level_why": r["level_why"], "signals": r["signals"], "model": r["model"], "backups": r["backups"],
            "why": r["choose_why"], "applied": not why_not, "not_applied": why_not}
    sh = S.new(conv, tenant, text, [part], read_on=doc.get("read_on") or "", surface="chat", now=t0)
    S.set_state(sh, 1, "running")
    tok = None
    if not why_not:
        from ..agent import llm
        tok = llm.MODEL_NOW.set("openrouter:" + r["model"]["id"])
    sink: list = []
    sink_tok = TOOL_SINK.set(sink)
    app_tok = APPLIED.set(not why_not)
    ms = round((time.time() - t0) * 1000, 1)
    sh["box_ms"] = ms
    S.save(sh)
    STATS["turns"] += 1
    STATS["applied" if not why_not else "skipped"] += 1
    log.warning("pipeline box %s: %s %s -> %s (%s) %.1f ms%s", conv, r["kind"], r["level"],
                (r["model"] or {}).get("id") or "-", "applied" if not why_not else "not applied", ms,
                f" - {why_not}" if why_not else "")
    return {"sheet": sh, "tok": tok, "sink": sink, "sink_tok": sink_tok, "app_tok": app_tok, "t0": t0,
            "text": text or ""}


def saw(name: str, out: Any) -> None:
    """Every tool result of a Box turn (from santosh._run_tool) - the facts list's source."""
    sink = TOOL_SINK.get()
    if sink is None:
        return
    try:
        txt = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, default=str)
    except Exception:   # noqa: BLE001
        txt = str(out)
    if len(sink) < 60:
        sink.append(str(txt)[:8000])


def end(b: dict | None, answer: str, failed: bool = False) -> dict | None:
    """Close the sheet: hand-off package, final check, outage record, the same model for 30 minutes."""
    if not b:
        return None
    sh = b["sheet"]
    try:
        tools_out = list(b["sink"])
        facts = K.facts_from(b["text"], tools_out)
        files = K.files_from(tools_out)
        chk = K.final_check(answer or "", b["text"], facts, files, [], tools_ran=len(tools_out))
        part = sh["parts"][0]
        empty = not str(answer or "").strip()
        bad = bool(failed or empty)
        pkg = S.package(result=str(answer or "")[:4000], facts=[f for f in facts if f["source"] != "her"][:80],
                        files=files, notes=[], not_done=["no answer"] if empty else [])
        S.set_state(sh, 1, "failed" if bad else "done", out=pkg, tools_ran=len(tools_out))
        S.finish(sh, chk)
        if not chk["ok"]:
            STATS["check_problems"] += 1
        if bad:
            STATS["failed"] += 1
        m = (part.get("model") or {}).get("id")
        if part.get("applied") and m:
            note(m, not bad)
            if not bad:
                B.remember(sh["conv"], part["kind"], part["level"], m)
        log.warning("pipeline box %s: done %s, check %s%s", sh["conv"], "failed" if bad else "ok",
                    "ok" if chk["ok"] else "problems", "" if chk["ok"] else " - " + "; ".join(chk["problems"][:3]))
        return chk
    except Exception as e:   # noqa: BLE001
        log.warning("pipeline box: closing the sheet failed (%s)", str(e)[:120])
        return None
    finally:
        try:
            if b.get("tok") is not None:
                from ..agent import llm
                llm.MODEL_NOW.reset(b["tok"])
        except Exception:   # noqa: BLE001 - a different context (reset across tasks) just leaves it
            pass
        try:
            TOOL_SINK.reset(b["sink_tok"])
        except Exception:   # noqa: BLE001
            TOOL_SINK.set(None)
        try:
            APPLIED.reset(b["app_tok"])
        except Exception:   # noqa: BLE001
            APPLIED.set(False)
