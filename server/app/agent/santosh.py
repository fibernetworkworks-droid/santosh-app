"""Santosh's agent loop: the brain (OmniRoute, GLM or Claude; see llm.py) decides, tools act, every step is streamed to the UI."""
from __future__ import annotations

import asyncio
import contextlib
import random
import re
import time
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select

from ..config import get_settings
from ..db import Message, new_id, now, session
from ..events import bus
from .. import livework
from ..avatar.service import gendered, persona
from ..life import context_block
from . import llm
from . import say as _say
from . import admit as _admit   # v0.191 step-admitted tool subsets (HARNESS-2)
from . import eventlog as _evlog   # v0.193 the harness session log (event-sourced turns)
from .prune import prune_history   # v0.189 old tool results leave the request, the newest step stays whole
from .prompts import system_prompt
from . import mcp_live
from ..gyaan import answer as _gyaan
from .tools import TOOL_LABELS, TOOLS, Ctx, ToolError, dispatch

log = logging.getLogger("santosh.agent")

_client = None
_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_HOLDER: dict[str, str] = {}   # v0.667 who holds each chat's lock right now (owner / goal / wake / routine ...)


@contextlib.asynccontextmanager
async def _holding(lock: asyncio.Lock, conversation_id: str):
    """The chat lock; who holds it is forgotten the moment it is released."""
    async with lock:
        try:
            yield
        finally:
            _HOLDER.pop(conversation_id, None)
# v0.187 the truth about the last finished turn of this conversation, for the voice call's late result
# ({"outcome": done|partial|stuck|stopped|talk|continuing, "left": what remains, "goal": the goal line, "at": ts})
LAST_OUTCOME: dict[str, dict] = {}


def get_client():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic
        key = get_settings().anthropic_api_key
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set, so Santosh cannot think yet.")
        _client = AsyncAnthropic(api_key=key)
    return _client


def set_client(client) -> None:
    global _client
    _client = client


def _block_to_dict(b) -> dict:
    if isinstance(b, dict):
        return b
    t = getattr(b, "type", None)
    if t == "text":
        return {"type": "text", "text": b.text}
    if t == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
    if hasattr(b, "model_dump"):
        return b.model_dump(exclude_none=True)
    return dict(b)


def _load_history(conversation_id: str) -> list[dict]:
    """v0.108 the newest 40-49 EXCHANGES (not messages): a one-word chat and a 30-step job each count once.
    v0.237 FULL CLAUDE MODE (CHAT_CONTEXT=claude): the whole chat word for word; context.fit decides per model call."""
    from .. import yaad
    from . import context as _ctx
    if _ctx.full_mode():
        return _sanitize(yaad.full_history(conversation_id))
    return _sanitize(yaad.history(conversation_id))


def _now_note(tenant_id: str | None) -> str:
    """wave 9: "[Current time: Saturday 07 Nov 2026, 9:32 PM IST]" in her own time zone, for THIS message only."""
    try:
        from .. import life
        t = datetime.now(life.tz_of(tenant_id or "default"))
    except Exception:   # noqa: BLE001
        from zoneinfo import ZoneInfo
        t = datetime.now(ZoneInfo("Asia/Kolkata"))
    return f"[Current time: {t.strftime('%A %d %b %Y, %I:%M %p').replace(' 0', ' ')} {t.tzname() or ''}]".replace(" ]", "]")


def _with_memory(history: list[dict], block: str) -> None:
    """v0.108 the diary / recalled memories ride on THIS message only (never saved), so older history stays cached."""
    for m in reversed(history):
        if m["role"] != "user":
            continue
        c = m["content"]
        if isinstance(c, str):
            m["content"] = [{"type": "text", "text": block}, {"type": "text", "text": c}]
        elif isinstance(c, list) and not any(b.get("type") == "tool_result" for b in c):
            m["content"] = [{"type": "text", "text": block}] + c
        return


def _last_user_text(history: list[dict]) -> str:
    """v0.289 her latest words (skipping tool-result turns): which of a big MCP server's tools come first."""
    for m in reversed(history or []):
        if m.get("role") != "user":
            continue
        c = m.get("content")
        if isinstance(c, str):
            return c[:2000]
        txt = " ".join(b.get("text", "") for b in (c or []) if isinstance(b, dict) and b.get("type") == "text")
        if txt.strip():
            return txt[:2000]
    return ""


def _as_blocks(c) -> list[dict]:
    return c if isinstance(c, list) else [{"type": "text", "text": c}]


def _tool_ids(content) -> set:
    """v0.216 every tool_use id an assistant message carries."""
    return {b.get("id") for b in _as_blocks(content)
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id")}


def _result_ids(content) -> set:
    """v0.216 every tool_use id a user message answers."""
    return {b.get("tool_use_id") for b in _as_blocks(content)
            if isinstance(b, dict) and b.get("type") == "tool_result"}


def _results_first(blocks: list) -> list:
    """v0.216 the API wants tool_result blocks at the START of a user message, text after."""
    return ([b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_result"]
            + [b for b in blocks if not (isinstance(b, dict) and b.get("type") == "tool_result")])


# v0.216 the honest answer for a result the crash lost (the model is told to check the step, not to guess)
TOOL_RESULT_LOST = ("[System: this tool result was not saved because of a crash. Check the real status of this step "
                    "yourself (with a status/list kind of tool) and carry on; do not guess.]")
# v0.213 the prefill guard's continuation line (unchanged text, now inside _api_ready)
CONTINUE_NUDGE = "[System: carry on according to the conversation above.]"


def _sanitize(msgs: list[dict]) -> list[dict]:
    """Repair history after a crash: drop tool calls that never got results, drop results whose call is
    gone, and merge back-to-back turns from the same role, so the API always accepts the history.
    v0.216 TOOL-JOD: the check is now per-ID - the old 'any tool_result present' passed a PARTIAL pair
    (assistant asked A+B, only A's result survived the crash) straight through, and the API answered
    "messages.12: tool_use ids were found without tool_result blocks immediately after: toolu_01B..."
    on every later turn of that conversation (owner saw it on long work)."""
    out: list[dict] = []
    for i, m in enumerate(msgs):
        c = m["content"]
        if m["role"] == "assistant":
            ids = _tool_ids(c)
            if ids:
                nxt = msgs[i + 1] if i + 1 < len(msgs) else None
                answered = _result_ids(nxt["content"]) if nxt is not None and nxt.get("role") == "user" else set()
                if not ids <= answered:   # EVERY id must be answered, not just any result present
                    keep = [b for b in _as_blocks(c)
                            if not (isinstance(b, dict) and b.get("type") == "tool_use") or b.get("id") in answered]
                    if not keep:
                        continue
                    m = {"role": "assistant", "content": keep}
        if m["role"] == "user" and isinstance(m["content"], list):
            rb = [b for b in m["content"] if isinstance(b, dict) and b.get("type") == "tool_result"]
            if rb:
                prev = out[-1] if out else None
                pids = _tool_ids(prev.get("content")) if prev is not None and prev.get("role") == "assistant" else set()
                known = [b for b in rb if b.get("tool_use_id") in pids]
                if len(known) != len(rb):   # v0.216 orphan results leave wherever they sit in the content
                    rest = [b for b in m["content"] if not (isinstance(b, dict) and b.get("type") == "tool_result")]
                    if not known and not rest:
                        continue
                    m = {**m, "content": _results_first(known + rest)}
        if out and out[-1]["role"] == m["role"]:
            merged = _as_blocks(out[-1]["content"]) + _as_blocks(m["content"])
            out[-1] = {"role": m["role"], "content": _results_first(merged) if m["role"] == "user" else merged}
        else:
            out.append(m)
    return out


def _strip_orphans(msgs: list[dict]) -> tuple[list[dict], bool]:
    """v0.216 pass 1: a tool_result whose call is not the message right before it ('unexpected
    tool_use_id' 400) leaves the request - wherever it sits in the content. Returns (new list, changed)."""
    out: list[dict] = []
    changed = False
    for m in msgs:
        if isinstance(m, dict) and m.get("role") == "user" and isinstance(m.get("content"), list):
            rb = [b for b in m["content"] if isinstance(b, dict) and b.get("type") == "tool_result"]
            if rb:
                prev = out[-1] if out else None
                pids = _tool_ids(prev.get("content")) if isinstance(prev, dict) and prev.get("role") == "assistant" else set()
                known = [b for b in rb if b.get("tool_use_id") in pids]
                if len(known) != len(rb):
                    restb = [b for b in m["content"] if not (isinstance(b, dict) and b.get("type") == "tool_result")]
                    if not known and not restb:
                        changed = True
                        continue          # a results-only orphan row disappears
                    m = {**m, "content": _results_first(known + restb)}
                    changed = True
        out.append(m)
    return out, changed


def _api_ready(history: list[dict]) -> list[dict]:
    """v0.216 TOOL-JOD the last line of defence before EVERY model call (Claude / GLM / OmniRoute, team
    sub-agents and the mini-loop included): the conversation goes out with every tool_use answered.
    v0.213's guard fixed assistant-final arrays by appending a text nudge - but when that final assistant
    message carried tool_use blocks (a sub-agent interrupted mid-step and retried: Rokiye's CancelledError
    is a BaseException its `except Exception` never saw, or a max_tokens cut inside a tool call), the nudge
    landed right after the tool_use and the API 400ed: 'tool_use ids were found without tool_result blocks
    immediately after' (owner: 'THIS ERROR IS IT IS SAME', messages.12, toolu_01BDvvVMZtTnhnxv). Now every
    unanswered tool_use gets an honest synthetic result in the very next user message - mid-array partials
    are rebuilt, orphan results are dropped, and a tool-tailed array ends with its results, not with a text
    nudge. Clean user-final arrays return the SAME list untouched (byte-identical happy path); a broken
    shape is repaired on a COPY, never mutating the caller's list (team sub-agents share theirs)."""
    msgs, changed = _strip_orphans(history)
    out: list[dict] = []
    i, n = 0, len(msgs)
    while i < n:
        m = msgs[i]
        out.append(m)
        i += 1
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        ids = [b.get("id") for b in _as_blocks(m.get("content"))
               if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id")]
        if not ids:
            continue
        nxt = msgs[i] if i < n else None
        got: dict = {}
        rest: list = []
        if isinstance(nxt, dict) and nxt.get("role") == "user":
            for b in _as_blocks(nxt.get("content")):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    got[b.get("tool_use_id")] = b
                else:
                    rest.append(b)
        if len(got) == len(ids) and set(ids) <= set(got):
            continue   # healthy pair: the next user message answers every id and nothing else
        results = [got.get(tid) or {"type": "tool_result", "tool_use_id": tid, "is_error": True,
                                    "content": TOOL_RESULT_LOST} for tid in ids]
        out.append({"role": "user", "content": _results_first(results + rest)})
        changed = True
        if isinstance(nxt, dict) and nxt.get("role") == "user":
            i += 1     # the next user message was folded into the repaired one
    if not changed:
        if history and history[-1].get("role") == "user":
            return history   # clean and user-final: byte-identical, no copy, no mutation
        out = list(msgs)
    if not out or out[-1].get("role") != "user":
        lids = _tool_ids(out[-1].get("content")) if out and isinstance(out[-1], dict) else set()
        if lids:   # a tool-tailed array ends with its results (not with the text nudge - that was the 400)
            out.append({"role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": t, "is_error": True,
                                     "content": TOOL_RESULT_LOST} for t in lids]})
        else:
            out.append({"role": "user", "content": [{"type": "text", "text": CONTINUE_NUDGE}]})
    # same-role adjacency would 400 in its own way: merge it, exactly like _sanitize does
    merged: list[dict] = []
    for m in out:
        if merged and merged[-1].get("role") == m.get("role"):
            c = _as_blocks(merged[-1].get("content")) + _as_blocks(m.get("content"))
            merged[-1] = {"role": m["role"], "content": _results_first(c) if m["role"] == "user" else c}
        else:
            merged.append(m)
    return merged


STATS_LONG: dict[str, int] = {"extended": 0, "wake_saved": 0, "deadline_extended": 0, "narrate": 0, "plan_now": 0,
                               "plan_first": 0, "auto_plan": 0}   # v0.473 long-job counters
_LONG_TURN: set[str] = set()     # v0.473 turns that moved to the long-job caps mid-way (no plan when they began)
_PROGRESS: dict[str, float] = {}  # v0.311 conv -> when its running turn last finished a tool (the deadline reads it)


async def _with_deadline(coro, conversation_id: str, first: float, long: float):
    """v0.473 the turn's lock deadline. A turn that became a long job mid-way (kaam_plan written, or the short cap
    reached with work going) gets the long-job deadline instead of being killed at the short one."""
    task = asyncio.ensure_future(coro)
    try:
        done, _ = await asyncio.wait({task}, timeout=first)
        if not done and long > first:
            from . import goal as _g
            # v0.311 a turn still MOVING (a tool finished in the last few minutes) is a long job too, plan or no
            # plan: four ~270 s browser steps used to pass the 900 s cap at step 4 and die "bahut der se chal raha tha"
            win = float(getattr(get_settings(), "agent_progress_window_s", 300) or 0)
            moving = win > 0 and time.time() - _PROGRESS.get(conversation_id, 0.0) < win
            if conversation_id in _LONG_TURN or _g.active_for(conversation_id) is not None or moving:
                STATS_LONG["deadline_extended"] += 1
                done, _ = await asyncio.wait({task}, timeout=long - first)
        if not done:
            task.cancel()
            try:
                await task
            except BaseException:
                pass
            raise asyncio.TimeoutError()
        return task.result()
    except asyncio.CancelledError:
        task.cancel()
        raise


def _no_think(content):
    """v0.232 thinking blocks live only inside the running turn (Claude needs them back in its tool loop); they are
    never saved, never reach GLM / OmniRoute and never ride into a later turn."""
    if isinstance(content, list):
        return [b for b in content if not (isinstance(b, dict) and b.get("type") in THINK_TYPES)]
    return content


def _save(conversation_id: str, role: str, content, display: str | None = None, in_history: bool = True) -> None:
    content = _no_think(content)
    with session() as s:
        s.add(Message(conversation_id=conversation_id, role=role, content=content, display=display,
                      in_history=in_history))


def _save_pre(conversation_id: str, role: str, content, display: str | None = None) -> None:
    """v0.666 a reply given BEFORE the chat lock (a card's "haan", a research plan, a stop by words). When another turn
    holds the chat, its last saved row may be a tool_use whose tool_result is not written yet - a row saved now would
    land between them, the real result was dropped as an orphan next turn (TOOL_RESULT_LOST) and the model redid a
    send it had already done. Then the row is shown, but kept out of the model's history."""
    lk = _locks.get(conversation_id) if isinstance(_locks, dict) else None
    _save(conversation_id, role, content, display=display, in_history=not (lk is not None and lk.locked()))


# v0.657 PAKKA KAAM: run_turn never raises - a crash / timeout / budget stop RETURNS a friendly line, so callers
# (a finished job's wake report, a routine) could not tell it from a real answer and marked the work delivered.
# Every failed ending stamps the time here; `turn_failed_since(conv, t0)` asks "did the turn I started fail?".
_FAILED: dict[str, float] = {}
TIMEOUT_TEXT = ("This task had been running for too long, so I stopped it midway. The step that was running at that moment "
                "may be half done - please check what has already happened before asking again (or ask me and I will "
                "check and tell you), so that no email or message goes out twice.")
TIMEOUT_GOAL = ("This round ran out of time and the step in progress was stopped. The next round will first check what is "
                "already done and carry on from there - you do not need to say anything again.")


def _mark_failed(conversation_id: str) -> None:
    _FAILED[conversation_id] = time.time()
    if len(_FAILED) > 2000:
        for k in sorted(_FAILED, key=_FAILED.get)[:1000]:
            _FAILED.pop(k, None)


_BG_ERR: dict[str, tuple[str, float]] = {}
BG_ERROR_QUIET_S = 1800
BG_ERROR_NIGHT_S = 10 * 3600


def _say_error(tenant_id: str, who: str, text: str) -> bool:
    """v0.662 an outage (out of credit, the model down) used to post + push one error line PER background turn -
    every routine, goal round and job report, each with a new ref. Her own turn always hears it; a background turn
    says the same kind of error once per tenant per 30 minutes."""
    if (who or "owner") == "owner":
        return True
    if who == "wake":
        # wave 9: a failed job report says nothing itself - kaam_followup sees turn_failed_since and posts its own honest
        # line; both went out before ("AI busy, phir boliye" + "ho gaya") - two pushes, one asking her to repeat a thing
        # she never asked
        STATS_LONG["bg_errors_quiet"] = STATS_LONG.get("bg_errors_quiet", 0) + 1
        return False
    kind = re.sub(r"\(ref[^)]*\)|ref[:\s]*\w+|\d+", "", text or "").strip()[:80]
    last = _BG_ERR.get(tenant_id)
    quiet = BG_ERROR_QUIET_S
    try:   # wave 13: in her quiet hours the same background error is said once for the night, not every 30 minutes
        from .. import push as _push
        if _push.is_quiet_now(tenant_id):
            quiet = BG_ERROR_NIGHT_S
    except Exception:
        pass
    if last and last[0] == kind and time.time() - last[1] < quiet:
        STATS_LONG["bg_errors_quiet"] = STATS_LONG.get("bg_errors_quiet", 0) + 1
        return False
    _BG_ERR[tenant_id] = (kind, time.time())
    return True


def turn_failed_since(conversation_id: str, since: float) -> bool:
    return _FAILED.get(conversation_id, 0.0) >= since


def _pending_worker_notes(conversation_id: str) -> list[str]:
    with session() as s:
        rows = s.scalars(select(Message).where(Message.conversation_id == conversation_id,
                                               Message.in_history.is_(False),
                                               Message.delivered_to_agent.is_(False)).order_by(Message.id)).all()
        notes = [r.display or "" for r in rows]
        for r in rows:
            r.delivered_to_agent = True
        return notes


TRIM_STATS: dict[str, int] = {"lists": 0, "cut": 0}


# v0.473 R2: the research dossier IS the evidence (its source list ends it), so it is not cut at the usual 6,000 characters
RESULT_LIMIT = {"research_run": 40000,
                "email_check": 12000,   # v0.706 slimmed rows: 20-40 mails fit, the model no longer sees 6 of 50
                # wave 10: a crew's deliverables ARE the evidence of the job: at 6,000 the list-slimming cut agents 4+
                "deploy_agents": 24000, "agent_status": 24000}


_FAIL_STATUS = {"failed", "failure", "error", "refused"}


def tool_failure(out) -> str:
    """v0.665 SACH KA HISAAB: the failure text of a tool result, '' when it went fine. A result like
    {"ok": False, "stage": "check", "errors": [...]} (a failed video render, a refused promo) used to count as a
    success because only an "error" key was read - logged ok, outcome "done", and the honesty check switched off."""
    if not isinstance(out, dict):
        return ""
    if out.get("error"):
        return str(out.get("error"))
    if out.get("ok") is False or str(out.get("status") or "").strip().lower() in _FAIL_STATUS:
        for k in ("reason", "message", "say", "detail", "errors", "stage", "status"):
            if out.get(k):
                return str(out[k])[:300]
        return "the tool said it did not succeed"
    return ""


def _facts_of(content) -> str:
    """The numbers a tool result carries, as one compact string (for the after-reply figure check)."""
    nums = re.findall(r"\d[\d,.]*\d|\d", str(content or "")[:40000])
    return " ".join(dict.fromkeys(nums))[:6000]


def _short(obj, limit: int = 6000) -> str:
    """A tool result for the model, at most `limit` characters.
    v0.331 SAAF KATAI: it used to be cut mid-JSON with "…(truncated)" - broken JSON, ids / links lost, and no hint how
    to get the rest. Now long LISTS inside the result are shortened first (the JSON stays valid and says how many were
    left out and how to get them), and only a result still too long is cut - with that same hint."""
    s = json.dumps(obj, ensure_ascii=False, default=str)
    if len(s) <= limit:
        return s
    if isinstance(obj, (dict, list)):
        for keep in (50, 25, 12, 6, 3):
            slim, dropped = _slim_lists(obj, keep)
            if dropped:
                out = json.dumps(slim, ensure_ascii=False, default=str)
                if len(out) <= limit:
                    TRIM_STATS["lists"] += 1
                    return out
        # v0.667 a dict whose bulk is ONE long string (a page / mail body) lost every key after it in the raw cut - the
        # ids, the next-page cursor, the error / next hints - and the JSON broke. Long strings are shortened in place
        # first, so every key survives and the JSON stays valid.
        for cap in (3000, 1500, 600, 200):
            slim = _slim_strings(obj, cap)
            out = json.dumps(slim, ensure_ascii=False, default=str)
            if len(out) <= limit:
                TRIM_STATS["strings"] = TRIM_STATS.get("strings", 0) + 1
                return out
    TRIM_STATS["cut"] += 1
    return (s[:limit] + f"…[cut: showing {limit:,} of {len(s):,} characters. For the rest ask for less - a filter, a "
            "search word, a smaller limit or the next page - or save big data with data_fetch and read it with "
            "data_read.]")


def _slim_strings(obj, cap: int, depth: int = 0):
    """Every string longer than `cap` cut to its head + how much was left out (lists slimmed to 12 too)."""
    if depth > 8:
        return obj
    if isinstance(obj, str):
        if len(obj) <= cap:
            return obj
        return obj[:cap] + (f"…[{len(obj) - cap:,} more characters cut - for the rest ask for this part alone, a smaller "
                            "limit or the next page, or save big data with data_fetch and read it with data_read]")
    if isinstance(obj, dict):
        return {k: _slim_strings(v, cap, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        items = [_slim_strings(v, cap, depth + 1) for v in obj[:12]]
        if len(obj) > 12:
            items.append(f"…[{len(obj) - 12} more items left out - ask for fewer / the next page]")
        return items
    return obj


def _slim_lists(obj, keep: int, depth: int = 0):
    """(copy with every list longer than `keep` cut to its first `keep` items + a note, items dropped)."""
    if depth > 6:
        return obj, 0
    if isinstance(obj, list):
        dropped = 0
        items = []
        for x in obj[:keep]:
            y, d = _slim_lists(x, keep, depth + 1)
            items.append(y)
            dropped += d
        if len(obj) > keep:
            items.append(f"…{len(obj) - keep} more not shown (ask with a filter / limit / page, or data_fetch for all)")
            dropped += len(obj) - keep
        return items, dropped
    if isinstance(obj, dict):
        out, dropped = {}, 0
        for k, v in obj.items():
            out[k], d = _slim_lists(v, keep, depth + 1)
            dropped += d
        return out, dropped
    return obj, 0


VOICE_NOTE = ("[Voice mode: the user is speaking to you and your reply will be read aloud by the phone. Reply in 1-3 short, "
              "natural spoken sentences with no lists, markdown, emoji or URLs. If the user speaks Hindi or Hinglish, write your "
              "reply in Devanagari script so the voice pronounces it correctly; for other Indian languages use their own script.]")


def _claude_ready() -> bool:
    return bool(get_settings().anthropic_api_key or _client is not None)


THINK_TYPES = ("thinking", "redacted_thinking")
import contextvars as _cv
_THINK_NOW: _cv.ContextVar[bool] = _cv.ContextVar("hoola_think_now", default=False)   # set by the turn's step loop only
THINK = {"ok": True, "calls": 0, "refused": 0}   # v0.232 PHASE C: Claude's adaptive thinking on the chat brain
# v0.331 SOCH GEHRI: a long job / hard ask runs at a higher Claude effort (output_config.effort, set once per turn so the
# prompt cache inside the turn holds). Sent via extra_body so any SDK version carries it; a 400 about it turns it off.
_EFFORT_NOW: _cv.ContextVar[str] = _cv.ContextVar("hoola_effort_now", default="")
# v0.429 SOCH KE JAWAB step 2: the model for THIS step ('' = settings.anthropic_model). Set once per step from the
# turn's state, like _EFFORT_NOW, so sub-agents and every caller of _call_brain keep their signature.
_MODEL_NOW: _cv.ContextVar[str] = _cv.ContextVar("hoola_model_now", default="")
HARD_MODEL = {"ok": True, "calls": 0, "failed": 0}


def _model_refused(e: Exception) -> bool:
    m = str(e).lower()
    return ("not_found" in m or "404" in m or "unknown model" in m or "model:" in m) and "model" in m


def _research_delivered(conversation_id: str, state: dict) -> bool:
    """wave 13: a research dossier was handed to the model in THIS turn (any actor: a long-job round, a routine, a call)."""
    if not conversation_id:
        return False
    try:
        from ..research import engine as _reng
        d = _reng.recall(conversation_id)
        return d is not None and float(d.get("_delivered", 0)) >= float(state.get("t0", 0) or 0) > 0
    except Exception:
        return False


def _hard_held(state: dict, settings, conversation_id: str = "") -> bool:
    """v0.436 is this turn's answer held for the self-check? Her hard question, check switched on.
    wave 13: also every turn that writes from a research dossier - the figure check used to run only on HER hard
    turns, so a goal round / routine / call report reached her unchecked."""
    if not getattr(settings, "hard_check", True):
        return False
    return bool(state.get("hard")) or _research_delivered(conversation_id, state)


# wave 13: said under a corrected answer that still fails the free check (it used to go out as if checked)
STATS_HARD_UNSURE = {"n": 0}
HARD_UNSURE = ("\n\n_Please note: some figures in this answer could not be confirmed - check them once before "
               "you use them._")


async def _hard_check(conversation_id: str, state: dict, draft: str, history: list[dict], settings,
                      free_only: bool = False) -> list[str]:
    """v0.436 SOCH KE JAWAB step 5: the free code check, then ONE independent reviewer call. Problems or [].
    wave 13 free_only = the corrected answer's re-check: code + claim checks only, no model call."""
    from . import hard as _hardc
    bus.publish(conversation_id, "step", {"tool": "jaanch", "label": "Checking the answer", "state": "running",
                                          "id": "hard-check"})
    try:
        ev, names = _hardc.evidence(history)
        full, _ = _hardc.evidence(history, limit=400_000, per=200_000)   # v0.437 every link a tool returned
        why = ((state.get("hard_why") or {}).get("why")) or []
        problems = _hardc.code_check(state.get("request", ""), draft, why, names, full)
        reviewed = False
        if not problems and ("research_run" in names or "research_status" in names or "research_watch" in names):
            try:    # v0.474 R3 SABOOT: every figure in the report must be carried by a note's own words or a calculation
                from ..research import claims as _claims, engine as _reng
                _d = _reng.recall(conversation_id)
                if _d is not None and float(_d.get("_delivered", 0)) >= float(state.get("t0", 0)):   # handed to the model in THIS turn
                    problems = _claims.check_report(draft, _d)
                    if not problems and not free_only:    # v0.480 R9: then a reviewer reads the WORDING against the dossier's notes (the generic one only sees a truncated tail)
                        from ..research import review as _rrev
                        problems = await _rrev.review_report(state.get("request", ""), draft, _d, settings)
                        reviewed = bool(getattr(settings, "research_review", True)) and bool(_d.get("fields"))
            except Exception:
                log.exception("claim check failed")
        if not problems and not reviewed and not free_only:
            problems = await _hardc.review(state.get("request", ""), draft, ev, settings)
        state["hard_check"] = {"problems": problems, "tools": names[:12]}
        return problems
    except Exception:
        log.exception("hard check failed")
        return []
    finally:
        bus.publish(conversation_id, "step", {"tool": "jaanch", "label": "Jawab jaanch liya", "state": "done",
                                              "id": "hard-check"})


# v0.630 HAIKU DIMAAG: set by a voice call before it hands her words to the brain (copied into the turn's task)
VOICE_BRAIN_NOW: _cv.ContextVar[bool] = _cv.ContextVar("hoola_voice_brain_now", default=False)
# wave 9: HER words of this turn (only her own turns set it) - a bulk send is allowed only when THESE say send, never on
# the model's own reading of an earlier "haan" (create_campaign auto_send / confirm_send used to trust the model)
ASK_NOW: _cv.ContextVar[str] = _cv.ContextVar("hoola_ask_now", default="")
# v0.636 KAHAN RUKA: her 16:22 call ask waited 18 s BEFORE the first Claude call (the calls were 5.3 s + 3.3 s) - a call
# brain turn now times every stage before its first model call and logs them in one line (`brain prep ...`)
_PREP: _cv.ContextVar = _cv.ContextVar("hoola_brain_prep", default=None)
STATS_PREP = {"logged": 0, "compact_skipped": 0, "results_cut": 0}


def _mark(stage: str) -> None:
    p = _PREP.get()
    if p is None or p.get("done"):
        return
    now = time.monotonic()
    p["marks"].append((stage, now - p["last"]))
    p["last"] = now


def _prep_line() -> str:
    p = _PREP.get()
    if p is None or p.get("done"):
        return ""
    p["done"] = True
    total = time.monotonic() - p["t0"]
    return f"brain prep {total:.1f}s before the first call: " + ", ".join(f"{k} {v:.1f}s" for k, v in p["marks"])
SIMPLE_MODEL = {"ok": True, "calls": 0, "failed": 0}


def model_for(settings, hard: bool, long_job: bool) -> str:
    """'' = the chat model. A hard reasoning ask (not a long job - those run many steps and stay on the chat model at
    agent_long_effort) gets agent_hard_model. v0.630 HAIKU DIMAAG: an ordinary ask (not hard, not long) gets
    chat_simple_model (Haiku, ~13x cheaper than Sonnet); a voice call's brain turn gets voice_brain_model."""
    if VOICE_BRAIN_NOW.get() and getattr(settings, "voice_brain_model", ""):
        # v0.643 FIRST: a call question that LOOKS big ("PDF banao", an open long job in the chat) used to fall into
        # the long-job branch and ran on Sonnet with a 16k cap - her 17:44 call: 9.1 + 5.8 + 23.0 + 4.3 s. She is
        # waiting on the line; the call brain is always voice_brain_model (Haiku)
        return str(settings.voice_brain_model) if SIMPLE_MODEL["ok"] else ""
    if getattr(settings, "chat_one_model", False):
        return ""        # v0.732 PARITY PHASE 1: no Haiku / Sonnet / Opus split by ask size - the chat model, every step
    if hard and not long_job:
        return str(getattr(settings, "agent_hard_model", "") or "")
    if long_job:
        return ""
    simple = str(getattr(settings, "chat_simple_model", "") or "")
    return simple if simple and SIMPLE_MODEL["ok"] else ""
EFFORT = {"ok": True, "calls": 0, "refused": 0}


def effort_for(settings, long_job: bool, hard: bool) -> str:
    """'' = the model's own default. Long jobs (a plan, the step-24 switch, a clearly big ask) get agent_long_effort,
    hard reasoning asks agent_hard_effort; ordinary chat stays on the default (fast, cheap)."""
    if long_job:
        return str(getattr(settings, "agent_long_effort", "") or "")
    if hard:
        return str(getattr(settings, "agent_hard_effort", "") or "")
    return ""


def think_wanted(settings, goal_open: bool) -> bool:
    """v0.232 PHASE C (fix 6 of the long-task report): she sees Hoola THINK - the Soch card on the phone and console.
    chat_thinking = goal (default: only while a long job runs, short chats stay fast) | on | off."""
    mode = (getattr(settings, "chat_thinking", "goal") or "off").lower()
    return THINK["ok"] and (mode == "on" or (mode == "goal" and goal_open))


def _loop_ok(history: list[dict]) -> bool:
    """With thinking on, an assistant tool_use that is being answered must carry its own thinking block (Claude's
    rule). A tool loop started without thinking (cheap brain, or thinking off) finishes without it."""
    if not history or history[-1].get("role") != "user":
        return True
    c = history[-1].get("content")
    if not (isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)):
        return True
    prev = history[-2] if len(history) > 1 else {}
    pc = prev.get("content") if prev.get("role") == "assistant" else None
    return isinstance(pc, list) and any(isinstance(b, dict) and b.get("type") in THINK_TYPES for b in pc)


def _effort_refused(e: Exception) -> bool:
    m = str(e).lower()
    return ("effort" in m or "output_config" in m) and any(w in m for w in ("400", "invalid", "not support",
                                                                           "unsupported", "unexpected", "extra"))


def _think_refused(e: Exception) -> bool:
    m = str(e).lower()
    return "thinking" in m and any(w in m for w in ("400", "invalid", "not support", "unsupported", "unexpected"))


async def _call_brain(brain: str, system: str, history: list[dict], settings, tools: list[dict] | None = None,
                      live=None, max_tokens: int | None = None, think: bool = False) -> tuple[list[dict], str]:
    """v0.732 PARITY Phase 0: the one model-call funnel also keeps WHAT THE MODEL RECEIVED (reqdump: system text, tool
    names, messages, brain / model, max_tokens) for GET /api/conversations/{id}/request/{turn}. Fail-open and off the
    loop; behaviour unchanged (switch `request_dump`)."""
    _mark("request")      # v0.639 the step's request was built (prune / trim / sanitize)
    handle = _dump_start(brain, system, history, settings, tools, max_tokens)
    try:
        out = await _call_brain_once(brain, system, history, settings, tools, live, max_tokens, think)
    except BaseException as e:   # noqa: BLE001 - recorded, then re-raised untouched
        _dump_done(handle, False, f"{type(e).__name__}: {str(e)[:300]}")
        raise
    _dump_done(handle, True)
    return out


def _dump_model(brain: str, settings) -> str:
    """The brain / model this call goes to, as the request dump names it (the SDK door's GLM said when it answers)."""
    if brain == "omniroute":
        return str(getattr(settings, "omniroute_model", "") or "")
    if brain == "glm":
        return str(getattr(settings, "glm_model", "") or "")
    sent = _sent_model(_MODEL_NOW.get() or settings.anthropic_model)
    try:
        from .. import glmdoor
        if glmdoor.active():
            b = glmdoor.brain()
            m = settings.omniroute_model if b == "omniroute" else settings.glm_model
            return f"{b}:{m} via SDK door (asked {sent})"
    except Exception:
        pass
    return sent


def _dump_start(brain, system, history, settings, tools, max_tokens):
    try:
        from .. import reqdump
        if not reqdump.on():
            return None
        tl = tools if tools is not None else TOOLS
        if brain in ("glm", "omniroute"):
            from . import toolsearch as _ts
            tl = _ts.loaded(tl)
        return reqdump.start(brain, _dump_model(brain, settings), int(max_tokens or settings.agent_max_tokens or 0),
                             system, tl, history, prep=_api_ready)
    except Exception:
        return None


def _dump_done(handle, ok: bool, error: str = "") -> None:
    if handle is None:
        return
    try:
        from .. import reqdump
        reqdump.done(handle, ok, error)
    except Exception:
        pass


async def _call_brain_once(brain: str, system: str, history: list[dict], settings, tools: list[dict] | None = None,
                           live=None, max_tokens: int | None = None, think: bool = False) -> tuple[list[dict], str]:
    """One model call on one brain. Raises when that brain fails. With `live` (v0.161) the words stream as written.
    v0.187 goal mode raises max_tokens (6000) so a plan's steps are not cut at the chat-size 2000.
    v0.213 the prefill guard: the production model refuses a conversation whose LAST message is an assistant
    message ('This model does not support assistant message prefill', 400 - owner saw it on every long job's
    wake turn). v0.216 TOOL-JOD: the guard grew into _api_ready - every call goes out with EVERY tool_use
    answered (an interrupted sub-agent's tail tool_use + the old text nudge was exactly the owner's second
    error: 'tool_use ids were found without tool_result blocks immediately after'), mid-array partial pairs
    are rebuilt and orphan results dropped, always on a COPY so no caller's history list is ever mutated
    behind its back (team sub-agents share their history list across steps)."""
    history = _api_ready(history)
    tools = tools if tools is not None else TOOLS
    cap = max_tokens or settings.agent_max_tokens
    streaming = live is not None and live.streaming
    # v0.443 a held answer (a hard ask being checked, a Gyaan answer) and any big answer still STREAM from Claude: the
    # live reply decides what she sees (feed() only shows words while live.streaming), the API call is never one long
    # blocking request (16k tokens + thinking as one HTTP call is the shape a client / proxy refuses or times out) and
    # the thinking reaches the Soch card while the words are held
    api_stream = streaming or live is not None or cap > NONSTREAM_MAX_TOKENS
    if brain in ("glm", "omniroute"):
        from . import toolsearch as _ts   # v0.563 deferred tools + tool references are Claude-only
        tools = _ts.loaded(tools)
        history = _ts.fit_refs(history, [], keep=False)
        history = [{**m, "content": _no_think(m["content"])} for m in history]   # v0.232 Claude-only blocks
        if streaming:
            blocks, stop, usage = await llm.openai_stream(brain, system, tools, history, cap,
                                                          live.feed, on_think=live.feed_think)   # v0.171 thinking
        else:
            blocks, stop, usage = await llm.openai_create(brain, system, tools, history, cap)
        log.info("%s in=%s out=%s %s", llm.describe(), usage.get("prompt_tokens"), usage.get("completion_tokens"),
                 usage.get("route", ""))
        from . import context as _ctx   # v0.237 the gauge learns this brain's real chars-per-token
        _ctx.after_call(brain, system, tools, history, usage.get("prompt_tokens"), bool(usage.get("estimated")))
        return blocks, stop
    over = _MODEL_NOW.get()
    stat = HARD_MODEL if over == str(getattr(settings, "agent_hard_model", "") or "") else SIMPLE_MODEL
    if over and over != settings.anthropic_model and stat["ok"]:
        # v0.429 SOCH KE JAWAB step 2: a hard reasoning ask runs on the strongest model (agent_hard_model, Opus). Any
        # failure there (not available on this key, overloaded, ...) retries the SAME call on the chat model once, so
        # she always gets an answer; a 404 / unknown model turns the switch off for this process.
        try:
            stat["calls"] += 1
            return await _claude_call(over, system, history, settings, tools, live, cap, think, api_stream)
        except asyncio.CancelledError:
            raise
        except Exception as e:   # noqa: BLE001 - the chat model answers instead
            stat["failed"] += 1
            if _model_refused(e):
                stat["ok"] = False
            log.warning("model %s failed, answering on %s: %s", over, settings.anthropic_model, str(e)[:200])
            if live is not None:
                live.reset()
            if _sent_model(over) == _sent_model(settings.anthropic_model):
                # wave 9: SAB HAIKU would send the fallback to the very model that just failed - this one call goes to
                # the real fallback model instead (said in the log); every other call stays on the one model
                from .. import usage as _u
                tok = _u.ONE_MODEL_BYPASS.set(True)
                try:
                    log.warning("fallback bypasses the one-model rule once: %s failed, %s answers", _sent_model(over),
                                settings.anthropic_model)
                    return await _claude_call(settings.anthropic_model, system, history, settings, tools, live, cap,
                                              think, api_stream)
                finally:
                    _u.ONE_MODEL_BYPASS.reset(tok)
    try:
        return await _claude_call(settings.anthropic_model, system, history, settings, tools, live, cap, think, api_stream)
    except asyncio.CancelledError:
        raise
    except Exception as e:   # noqa: BLE001
        # wave 9: the ONE model (SAB HAIKU) is overloaded / down: the turn used to die there (the SDK's own retries are on
        # the same model). Once, the real chat model answers instead - never on a credit / bad-request error.
        low = str(e).lower()
        if getattr(settings, "chat_one_model", False) and not VOICE_BRAIN_NOW.get():
            raise        # v0.732 one model: _think asks the SAME model again, never another one mid-chat
        if _sent_model(settings.anthropic_model) == settings.anthropic_model or "credit" in low or "billing" in low \
                or not any(x in low for x in ("overloaded", "529", "error 5", "503", "502", "500", "timed out", "rate limit", "429")):
            raise
        from .. import usage as _u
        log.warning("one model %s failed (%s); %s answers this call", _sent_model(settings.anthropic_model), low[:120],
                    settings.anthropic_model)
        if live is not None:
            live.reset()
        tok = _u.ONE_MODEL_BYPASS.set(True)
        try:
            return await _claude_call(settings.anthropic_model, system, history, settings, tools, live, cap, think,
                                      api_stream)
        finally:
            _u.ONE_MODEL_BYPASS.reset(tok)


def _sent_model(model: str) -> str:
    """v0.643 the model the SDK door really sends (usage.one_model may rewrite it), for the `claude call` log line."""
    try:
        from .. import usage
        return str(usage.one_model({"model": model}).get("model") or model)
    except Exception:
        return model


async def _claude_call(model: str, system: str, history: list[dict], settings, tools: list[dict], live, cap: int,
                       think: bool, streaming: bool) -> tuple[list[dict], str]:
    """v0.635 every Claude call's own time + shape in the log (`claude call 4.2s ...`): her call turns spent 20 s before
    the first tool and the harness log could not say which part - now it can."""
    t0 = time.monotonic()
    try:
        _pl = _prep_line()
        if _pl:
            STATS_PREP["logged"] += 1
            log.info("%s", _pl)
    except Exception:
        pass
    try:
        return await _claude_call_once(model, system, history, settings, tools, live, cap, think, streaming)
    finally:
        try:
            log.info("claude call %.1fs model=%s msgs=%d chars=%d tools=%d think=%s effort=%s cap=%d voice=%s",
                     time.monotonic() - t0, _sent_model(model), len(history),
                     len(str(system)) + sum(len(str(m.get("content"))) for m in history),
                     len(tools or []), bool(think and THINK["ok"]), _EFFORT_NOW.get() or "-", cap,
                     VOICE_BRAIN_NOW.get())
        except Exception:
            pass


async def _claude_call_once(model: str, system: str, history: list[dict], settings, tools: list[dict], live, cap: int,
                            think: bool, streaming: bool) -> tuple[list[dict], str]:
    """One Claude call on `model` (v0.429 split out of _call_brain so a hard ask can try Opus and fall back)."""
    from . import cache, toolsearch as _ts
    deferred = any(isinstance(t, dict) and t.get("defer_loading") for t in (tools or []))
    if deferred and not _ts.NATIVE["ok"]:
        tools = _ts.loaded(tools)          # v0.563 refused earlier in this process: the old shape
        deferred = False
    history = _ts.fit_refs(history, tools, keep=deferred)   # a reference must resolve, or the whole call 400s
    kw = cache.shape(dict(model=model, max_tokens=cap,
                          system=system, tools=tools, messages=history), getattr(settings, "prompt_cache", True))
    api = get_client().messages
    if think and THINK["ok"] and _loop_ok(history):
        kw["thinking"] = {"type": "adaptive"}       # v0.232 Claude decides how much to think; thoughts stream to Soch
        THINK["calls"] += 1
    eff = _EFFORT_NOW.get()
    if eff and EFFORT["ok"]:
        kw["extra_body"] = {**(kw.get("extra_body") or {}), "output_config": {"effort": eff}}
        EFFORT["calls"] += 1
    try:
        if streaming and hasattr(api, "stream"):
            return await _claude_stream(api, kw, live)
        resp = await api.create(**kw)
    except Exception as e:
        if deferred and _ts.refused(e):
            # v0.563 this API refuses deferred tools / tool references: the same call the old way, off for this process
            log.warning("tool search refused, continuing with the loaded tools only: %s", str(e)[:200])
            kw = _ts.downgrade(kw)
            if live is not None:
                live.reset()
            if streaming and hasattr(api, "stream"):
                return await _claude_stream(api, kw, live)
            resp = await api.create(**kw)
            _learn_claude(kw, resp)
            return [_block_to_dict(b) for b in resp.content], resp.stop_reason
        if "extra_body" in kw and _effort_refused(e):
            # v0.331 this model / API refuses the effort setting: go on without it (the reply matters more)
            EFFORT["ok"], EFFORT["refused"] = False, EFFORT["refused"] + 1
            log.warning("effort refused, continuing without it: %s", str(e)[:200])
            kw.pop("extra_body", None)
            if live is not None:
                live.reset()
            if streaming and hasattr(api, "stream"):
                return await _claude_stream(api, kw, live)
            resp = await api.create(**kw)
            _learn_claude(kw, resp)
            return [_block_to_dict(b) for b in resp.content], resp.stop_reason
        if "thinking" not in kw or not _think_refused(e):
            raise
        THINK["ok"], THINK["refused"] = False, THINK["refused"] + 1   # this model / API refuses it: never again here
        log.warning("chat thinking refused, continuing without it: %s", str(e)[:200])
        kw.pop("thinking", None)
        if live is not None:
            live.think_reset()
        if streaming and hasattr(api, "stream"):
            return await _claude_stream(api, kw, live)
        resp = await api.create(**kw)
    _learn_claude(kw, resp)
    return [_block_to_dict(b) for b in resp.content], resp.stop_reason


def _learn_claude(kw: dict, resp) -> None:
    """v0.237 Claude's own token count (input + cache read + cache write) for the gauge."""
    u = getattr(resp, "usage", None)
    if u is None:
        return
    n = sum(int(getattr(u, k, 0) or 0) for k in ("input_tokens", "cache_read_input_tokens",
                                                  "cache_creation_input_tokens"))
    from . import context as _ctx
    _ctx.after_call("claude", kw.get("system"), kw.get("tools"), kw.get("messages") or [], n)


NONSTREAM_MAX_TOKENS = 8192     # v0.443 above this an answer is always streamed from the API (no live reply needed)


class _QuietLive:
    """v0.443 a stream with no live reply to show it in (a sub-agent, a check): the words are just collected."""
    def feed(self, piece: str) -> None:
        pass

    def feed_think(self, piece: str) -> None:
        pass

    def new_text_block(self) -> None:
        pass


async def _claude_stream(api, kw: dict, live) -> tuple[list[dict], str]:
    """v0.161 Claude's answer word by word: text deltas go to the live reply; tool input (input_json_delta) is left to
    the SDK, which parses it only when the block is complete. Prompt caching is the same request shape.
    v0.171 thinking deltas (adaptive / extended thinking) stream to the console's Soch card, never into the answer."""
    live = live if live is not None else _QuietLive()
    async with api.stream(**kw) as st:
        async for ev in st:
            t = getattr(ev, "type", "")
            if t == "content_block_start" and getattr(getattr(ev, "content_block", None), "type", "") == "text":
                live.new_text_block()
            elif t == "content_block_delta":
                dt = getattr(getattr(ev, "delta", None), "type", "")
                if dt == "text_delta":
                    live.feed(ev.delta.text)
                elif dt == "thinking_delta":
                    live.feed_think(getattr(ev.delta, "thinking", "") or "")
        msg = await st.get_final_message()
    from .. import usage   # the SDK wrapper counts messages.create only: a streamed answer is counted here
    usage.from_anthropic(_sent_model(kw.get("model", "")), msg)   # wave 9: the model the SDK door REALLY sent (SAB HAIKU)
    _learn_claude(kw, msg)
    return [_block_to_dict(b) for b in msg.content], msg.stop_reason


async def _think(brain: str, system: str, history: list[dict], settings, tools: list[dict] | None = None,
                 live=None, max_tokens: int | None = None) -> tuple[list[dict], str, str]:
    """One model call that survives a failing brain: the chosen brain first, then the other one, so an outage of
    either never leaves the user without an answer. Returns (blocks, stop_reason, the brain that answered).
    v0.161 a brain that fails after some streamed words: `delta_reset`, and the next brain writes them again."""
    order = [brain]
    if llm.one_model():
        # v0.732 PARITY PHASE 1 EK MODEL: the chat stays on its model - the SAME brain is asked again a few seconds
        # apart (a GLM timeout is never retried inside one request), never another brain; then the error goes up and
        # she reads the plain "busy, try again" line
        order = [brain] * (1 + max(0, int(getattr(settings, "chat_model_retries", 2) or 0)))
    elif brain == "claude":
        cheap = llm.cheap_brain()
        if cheap and not llm._has_media(history[-1:]):   # pictures and PDFs need Claude; plain text can go to the cheap brain
            order.append(cheap)
    elif _claude_ready():
        order.append("claude")
    last: Exception | None = None
    for i, b in enumerate(order):
        if i and llm.one_model():
            if last is not None and not _same_model_retry_ok(last):
                break
            STATS_ONE_MODEL["retries"] += 1
            await asyncio.sleep(float(getattr(settings, "chat_model_retry_s", 3.0) or 0) * i)
        try:
            extra = {"think": True} if (_THINK_NOW.get() and b == "claude") else {}   # v0.232 only when it thinks
            blocks, stop = await _call_brain(b, system, history, settings, tools, live, max_tokens, **extra)
            if live is not None:
                live.flush(final=True)     # the answer is complete: the held-back end can go (nothing can split now)
                live.think_flush(final=True)
            return blocks, stop, b
        except asyncio.CancelledError:
            raise
        except Exception as e:
            last = e
            if live is not None:
                live.reset()
            log.warning("%s failed%s: %s", b, "; asking the same model again" if llm.one_model() and i + 1 < len(order)
                        else ("; trying the other brain" if b != order[-1] else ""), e)
    assert last is not None
    raise last


STATS_ONE_MODEL = {"retries": 0}


def _same_model_retry_ok(e: BaseException) -> bool:
    """v0.732 a failure worth asking the same model again: busy / rate limit / timeout / unreachable / a 5xx. A wrong key,
    a refused request, an out-of-credit or a too-long chat will not get better a few seconds later."""
    low = str(e).lower()
    if "credit" in low or "billing" in low:
        return False
    from . import context as _ctx
    if _ctx.is_overflow(str(e)):
        return False
    return any(x in low for x in ("overloaded", "529", "error 5", "503", "502", "500", "timed out", "timeout",
                                  "rate limit", "429", "not reachable", "connection", "broken answer"))


OUTAGE_TEXT = "The Hoola AI service is paused for a little while - we are fixing it. Please try again in a moment."


def _operator(tenant_id: str | None) -> bool:
    """wave 9: the tenant that OWNS the server's AI key (it pays the Anthropic bill) - only that tenant is told to recharge."""
    try:
        op = str(getattr(get_settings(), "hoola_operator_tenant", "default") or "default")
    except Exception:   # noqa: BLE001
        op = "default"
    return (tenant_id or "default") == op


def _friendly_error(e: BaseException, tenant_id: str | None = None, who: str = "owner", spoken: bool = False) -> str:
    """v0.237 a clean line for her: never the raw technical text (it stays in the log under the same short ref,
    and the turn_failed event keeps it for the developer). An HTTP status, when there is one, rides as a code.
    wave 9: the AI key is ONE key for the whole server - a staff member, a customer or another tenant was told to recharge
    Anthropic on console.anthropic.com (and a call could read it aloud with its code / ref tail). Only the operator's own
    turn hears the billing line; everyone else hears a neutral outage line; a spoken line never carries the code / ref."""
    import re as _re
    s = str(e)
    low = s.lower()
    busy = any(x in low for x in ("not reachable", "error 429", "error 5", "overloaded", "rate limit", "timed out", "broken answer"))
    from . import context as _ctx
    if "credit balance is too low" in low or "billing" in low and "anthropic" in low:
        # v0.631 her account is out of credit: say it plainly, it is not a bug and waiting will not fix it
        log.error("ANTHROPIC CREDIT IS OUT - every Claude turn on this server fails until it is recharged")
        if _operator(tenant_id) and (who or "owner") == "owner":
            head = "The Anthropic credit has run out - recharge it at console.anthropic.com > Plans & Billing, then try again."
        else:
            head = OUTAGE_TEXT
    elif _ctx.is_overflow(s):
        head = "This chat has become too long. Start a new chat and say the same thing there - I will still remember the earlier parts."
    elif busy:
        head = "The AI service is busy or unreachable right now. Please try again in a moment."
    else:
        head = "Sorry, something went wrong just now."
    if not s:
        return head
    ref = format(random.getrandbits(24), "06x")
    log.warning("error ref %s: %s", ref, s[:2000])
    if spoken:
        return head            # a voice call speaks the line: no "code 529 · ref a3f9c2" read aloud
    m = _re.search(r"\b(?:error(?: code)?:?\s*|status\s*)(\d{3})\b", s, _re.I)
    return f"{head} (code {m.group(1)} · ref {ref})" if m else f"{head} (ref {ref})"


class _Halted(Exception):
    """v0.91 The owner stopped the turn (Rokiye), or paused the job mid-turn: the running step was cancelled."""

    def __init__(self, why: str):
        super().__init__(why)
        self.why = why


HALT_EVERY_S = 0.1           # how often a running step checks for Rokiye / Pause (OpenDots checks 10x a second too)
HALTS = {"stop": 0, "pause": 0}


def _halt_reason(conversation_id: str, ctx: Ctx, state: dict | None = None) -> str:
    if conversation_id in _stopped:
        return "stop"
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor in ("owner", "goal") or actor.startswith("approved:") or state is None or state.get("paused0") is None:
        return ""                      # her own turns: Pause holds job tools at the gate, her personal work goes on
    try:
        from ..employee import service as emp
        if emp.paused_now(ctx.tenant_id) and not state["paused0"]:
            return "pause"             # turned on while this routine / staff / customer turn was running
    except Exception:
        log.exception("pause check failed")
    return ""


async def _watched(work, conversation_id: str, ctx: Ctx, state: dict | None = None):
    """Run one model call or tool call, but cancel it the moment she taps Rokiye (or pauses the job), instead of
    waiting for the step to finish by itself. Exceptions of the work itself pass through unchanged."""
    task = asyncio.ensure_future(work)
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=HALT_EVERY_S)
            if done:
                return task.result()
            why = _halt_reason(conversation_id, ctx, state)
            if why:
                task.cancel()
                try:
                    await task
                except BaseException:
                    pass
                HALTS[why] += 1
                raise _Halted(why)
    except asyncio.CancelledError:
        task.cancel()
        raise


# wave 13: an error AFTER tools ran used to give only the generic line - she repeated the ask and a mail went twice
AFTER_TOOLS = (" Some steps had already run before this - please check what has happened before asking again, so that "
               "no email or message goes out twice.")


def _tools_since(history: list[dict], h0: int) -> list[str]:
    names: list[str] = []
    for m in history[h0:]:
        c = m.get("content") if isinstance(m, dict) else None
        for b in (c if isinstance(c, list) else []):
            if isinstance(b, dict) and b.get("type") == "tool_use":
                names.append(str(b.get("name") or ""))
    return names


HALTED_TEXT = {"stop": "Okay, I stopped the work.",
               "pause": "You paused the work, so I have stopped here. I will carry on when the work is started again."}

# v0.189 Tools that may run TOGETHER when one step asks for several (dsh's bounded pool, Claude Code's
# concurrency-safe read batching - kept deliberately small): pure look-ups only. Anything that writes,
# touches her PC's single WebSocket, reads her mail/Drive (nested SQLite writes, the v0.188 lesson), or
# sends anything stays strictly serial, exactly as before. Results still commit in the model's order.
PARALLEL_SAFE = frozenset({
    "google_search", "youtube_search", "open_website", "web_sources", "get_weather",
    "maps_search", "hoola_community_search", "memory_search", "kaam_status",
    "indiamart_khoj", "indiamart_detail",      # v0.277 read-only IndiaMART look-ups
    "mospi",                                   # v0.348 read-only MoSPI statistics
})


def _parallel_ok(b: dict) -> bool:
    """v0.666 by CALL, not only by name: kaam_status is a look-up only for action=status - action=stop cancels jobs
    across all her chats (DB writes), and two of those side by side were the nested-write race v0.188 keeps serial."""
    if b.get("name") not in PARALLEL_SAFE:
        return False
    if b.get("name") == "kaam_status":
        return str((b.get("input") or {}).get("action") or "status").strip().lower() != "stop"
    return True


async def _run_tool(name: str, args: dict, ctx: Ctx, settings, mcp_route: dict | None = None):
    """A tool call that can never hang the whole turn.
    v0.193 it also writes the harness session log (tool_call / tool_result, with the turn's context) - best-effort,
    the log can never break the call."""
    if mcp_route and name in mcp_route:   # a tool of one of the owner's MCP servers
        work = mcp_live.run(ctx, mcp_route, name, args or {})
    else:
        work = dispatch(name, args or {}, ctx)
    _meta = _evlog.CURRENT.get() or {}
    _ev_t = getattr(ctx, "tenant_id", "")
    _ev_c = getattr(ctx, "conversation_id", "")
    try:
        from .. import livework as _lw
        _brief = _lw.args_brief(args or {})
    except Exception:
        _brief = {}
    _evlog.log_event(_ev_t, _ev_c, "tool_call", {"tool": name, "args": _brief},
                     _meta.get("turn_id", ""), _meta.get("actor", ""))
    _t0 = time.time()
    try:
        out = await asyncio.wait_for(work, timeout=max(5, settings.agent_tool_timeout_s))
    except asyncio.CancelledError:
        raise
    except BaseException as e:
        _evlog.log_event(_ev_t, _ev_c, "tool_result", {"tool": name, "ok": False,
                                                         "line": f"{type(e).__name__}: {str(e)[:160]}"},
                         _meta.get("turn_id", ""), _meta.get("actor", ""))
        raise
    from ..scrub import scrub          # v0.91 a service that echoes one of our keys back never shows it to the model
    out = scrub(out)
    try:
        import json as _json
        _line = _json.dumps(out, ensure_ascii=False, default=str)[:180]
    except Exception:
        _line = str(out)[:180]
    _evlog.log_event(_ev_t, _ev_c, "tool_result", {"tool": name,
                                                    "ok": not (isinstance(out, dict) and out.get("error")),
                                                    "ms": int((time.time() - _t0) * 1000), "line": _line},
                     _meta.get("turn_id", ""), _meta.get("actor", ""))
    try:   # v0.473 HOOLA CODER: the same funnel the harness log rides becomes the memory capture -
           # best-effort, redacted at the capture boundary, a memory failure can never touch the call
        from .. import coder as _coder
        _coder.tool_observed(_ev_t, _ev_c, name, args or {}, out,
                             not (isinstance(out, dict) and out.get("error")),
                             int((time.time() - _t0) * 1000), _meta.get("turn_id", ""),
                             _meta.get("actor", ""))
    except Exception:
        pass
    return out


async def _steps(conversation_id: str, ctx: Ctx, gender: str, history: list[dict], settings, tenant_id: str,
                 user_text: str = "") -> str:
    """One turn with the v0.63 extras around it: seekhe hue kaam as hints, a circuit breaker, learning afterwards.
    v0.187: while a kaam_plan goal is open for this chat the caps rise (AGENT_GOAL_*), the breaker gets one replan
    rescue, and the real outcome lands in LAST_OUTCOME for the voice call to tell the truth about."""
    from .. import procedures
    from .breaker import Breaker, FAILS_IN_ROW_GOAL
    from . import pakka
    from . import goal as _goal
    _hers = (getattr(ctx, "actor", "owner") or "owner")
    ASK_NOW.set(user_text if (_hers == "owner" or _hers.startswith("approved:")) else "")
    state: dict = {"calls": [], "breaker": Breaker(), "used": [], "hint": "", "request": user_text, "t0": time.time(),
                   "conv": conversation_id, "actor": getattr(ctx, "actor", "owner") or "owner"}
    # v0.232 PHASE C a clearly big ask by her thinks from its FIRST call (the plan comes first, and Claude can't start
    # thinking in the middle of a tool loop, so waiting for kaam_plan set would keep this whole turn silent)
    state["big"] = bool(ctx.actor in ("owner", "goal") and settings.agent_goal and _goal.looks_big(user_text or ""))
    if state["big"]:   # v0.558 a big ask thinks at effort xhigh from its FIRST call: thinking tokens count, give it the long-job room
        state["max_tokens"] = max(state.get("max_tokens") or 0, int(settings.agent_goal_max_tokens or 16000))
    # v0.272 SOCH KE JAWAB step 1: a HARD question (analysis, calculation, decision, plan, root cause, proof, deep
    # explanation) is not a long job - looks_big missed 50 of 50 of them - but it needs thinking from its first call
    state["hard"] = False
    # v0.634 TEZ DIMAAG: a voice call's brain turn is never a "hard" turn - thinking, a held answer and a reviewer
    # call cost her 21 s of silence on "teen email ka detail summary" (her 15:27 call); she is waiting on the line
    if ctx.actor == "owner" and getattr(settings, "hard_detect", True) and not VOICE_BRAIN_NOW.get():
        try:
            from . import hard as _hard
            _hv = await _hard.decide(user_text or "", settings)
            state["hard"], state["hard_why"] = bool(_hv["hard"]), _hv
            # v0.437 a deep-research ask: the agent crew gets research room + must return sources
            ctx.research = bool(_hv["hard"] and "research" in (_hv.get("why") or []))
            if state["hard"]:   # v0.429 thinking tokens count against max_tokens: a hard answer gets real room
                state["max_tokens"] = max(state.get("max_tokens") or 0,
                                          int(getattr(settings, "agent_hard_max_tokens", 16000) or 16000))
        except Exception:
            log.exception("hard check failed")
    elif ctx.actor == "wake":
        try:    # v0.475 R4: the wake turn that WRITES a finished research report is a hard, held answer (Opus, room, the R3 check)
            from ..research import runner as _rrun
            if _rrun.is_report_due(user_text):
                # a WATCH change is a short message citing [n]: the link-list rule of a full report does not apply to it (the figure check + the review still do)
                state["hard"], state["hard_why"] = True, {"hard": True, "why": ["research_change" if _rrun.is_change_due(user_text) else "research"], "score": 3}
                state["max_tokens"] = max(state.get("max_tokens") or 0, int(getattr(settings, "agent_hard_max_tokens", 16000) or 16000))
        except Exception:
            log.exception("research report wake setup failed")
    if settings.agent_goal:
        g0 = _goal.active_for(conversation_id)
        if g0 is not None:   # goal open when the turn began: the goal caps apply from the first step
            state["goal"] = g0
            state["breaker"] = Breaker(max_calls=settings.agent_goal_max_calls, fails_in_row=FAILS_IN_ROW_GOAL,
                                       rescue=True)
            state["max_tokens"] = settings.agent_goal_max_tokens
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor not in ("owner", "goal") and not actor.startswith("approved:"):
        try:   # v0.91 remember whether the job was paused when this turn began: turning Pause on mid-turn stops it
            from ..employee import service as _emp
            state["paused0"] = _emp.paused_now(tenant_id)
        except Exception:
            state["paused0"] = None
    if user_text and actor in ("owner", "routine", "goal") and not VOICE_BRAIN_NOW.get():
        # (v0.638 a call's brain turn skips the learned-procedure lookup: 1.8 s on her 16:36 call, before any model call)
        try:
            state["hint"], state["used"] = await asyncio.to_thread(procedures.hint, tenant_id, user_text)
        except Exception:
            log.exception("procedure hint failed")
    _mark("hint")
    text = await _steps_inner(conversation_id, ctx, gender, history, settings, tenant_id, state)
    g = _goal.active_for(conversation_id) if settings.agent_goal else None
    if g is not None and _goal.steps_left(g):
        ok = False
        state["left"] = (f"goal '{g['goal']}': {g['done']}/{g['total']} steps done, "
                         f"{len(_goal.steps_left(g))} left ({g['stage'] or 'will carry on'})")
    else:
        ok = (bool(text.strip()) and not state["breaker"].stopped and conversation_id not in _stopped
              and not state.get("halted")
              and not text.startswith(("This task has become long", "Sorry")))
    if user_text:
        # wave 11: a reply the honesty check caught, or a turn that left work undone, is never LEARNED from as a good run
        # (the outcome itself is unchanged)
        good = ok and not state.get("fake_done") and not state.get("left")
        lessons = await asyncio.to_thread(pakka.learn, tenant_id, state["calls"], good, state.get("lessons_used", []))
        if lessons:
            bus.publish(conversation_id, "procedure", {"event": "lesson", "title": lessons[0][:120], "count": len(lessons)})
        outcome = ("stopped" if conversation_id in _stopped or state.get("halted") else "stuck" if state["breaker"].stopped else
                   "talk" if not state["calls"] else "partial" if state.get("left") else "done" if ok else "partial")
        LAST_OUTCOME[conversation_id] = {"outcome": outcome, "left": state.get("left", ""),
                                         "goal": (g or state.get("goal") or {}).get("goal", ""), "at": time.time()}
        from ..fence import is_incognito   # v0.250 an incognito chat leaves no line in the work diary
        if not await asyncio.to_thread(is_incognito, conversation_id):
            await asyncio.to_thread(pakka.record, tenant_id, user_text, outcome, state["calls"], state,
                                    time.time() - state["t0"], state.get("left", ""))
        learned = await asyncio.to_thread(procedures.after_turn, tenant_id, user_text, state["calls"], state["used"], good,
                                          "routine" if actor == "goal" else actor)
        if learned and learned.get("learned"):
            bus.publish(conversation_id, "procedure", {"event": "learned", "id": learned["learned"], "title": learned["title"]})
    if user_text and actor == "owner" and settings.draft_check and not state.get("hard_checked"):
        # (v0.436 a hard answer already passed the self-check before she saw it - no second, weaker look after)
        # v0.223 the last look, in the background: the reply is already on her screen, so nothing waits for this
        from . import draftcheck
        state["chat_tail"] = _chat_tail(history)
        _bg(draftcheck.after_turn(conversation_id, tenant_id, user_text, text, state, settings))
    return text


AUTO_PLAN_NOTE = ("[System: you did not write a plan, so the server made this plan and showed it on the card: "
                  "\"{goal}\" ({n} steps: {steps}). You now have the limits of a long job - do not stop. After each step "
                  "write `kaam_plan step n done` (it shows on the card); if you want, write better steps with "
                  "`kaam_plan set`. When the work is complete give the final answer directly.]")


def _auto_plan(conversation_id: str, tenant_id: str, state: dict, settings, ctx) -> str:
    """v0.311 PLAN HAMESHA: a one-step plan written by the server (her request as the goal). The goal caps rise at
    once, exactly like a kaam_plan set mid-turn. Returns the note for the model ('' when it could not be written)."""
    from . import goal as _goal
    from .breaker import FAILS_IN_ROW_GOAL
    req = " ".join(str(state.get("request") or "").split())
    if not req or req.startswith("["):
        return ""
    goal_line, steps = _ask_steps(req)
    line = goal_line if len(goal_line) <= 160 else goal_line[:157].rstrip() + "…"
    try:
        v = _goal.set_goal(tenant_id, conversation_id, line, steps or [line],
                           origin=getattr(ctx, "actor", "owner") or "owner")
        _goal.mark_step(tenant_id, v["id"], 1, "current", conv=conversation_id)
    except Exception:
        log.exception("auto plan failed")
        return ""
    state["auto_plan"] = v["id"]
    state["goal"] = v
    b = state["breaker"]
    b.max_calls, b.fails_in_row, b.rescue = settings.agent_goal_max_calls, FAILS_IN_ROW_GOAL, True
    state["max_tokens"] = max(state.get("max_tokens") or 0, settings.agent_goal_max_tokens)
    _LONG_TURN.add(conversation_id)
    STATS_LONG["auto_plan"] += 1
    return AUTO_PLAN_NOTE.format(goal=line.replace('"', "'"), n=len(v.get("steps") or [1]),
                                 steps="; ".join(f"{x['n']}. {x['text']}" for x in (v.get("steps") or []))[:900])


_CLAUSE_SPLIT = re.compile(r"\s*(?:[,;\n]|\s(?:aur\s+phir|aur\s+fir|uske\s+baad|iske\s+baad|phir|fir|then|and\s+then|"
                           r"after\s+that|aakhir\s+mein|finally)\s)\s*", re.I)
_CLAUSE_LEAD = re.compile(r"^(?:(?:aur|and|phir|fir|then|pehle|first|aakhir\s+mein|finally|uske\s+baad|iske\s+baad|"
                          r"after\s+that|[-*•]|\d{1,2}[.)])\s*)+", re.I)


def _ask_steps(req: str) -> tuple[str, list[str]]:
    """v0.315 her ask as (goal, steps) for the server's plan: 'X: a, b, phir c, aur d' -> goal X, steps a..d.
    Fewer than 2 real clauses = one step (the whole ask). Words only, never a model call."""
    head, rest = (req.split(":", 1) + [""])[:2] if ":" in req[:200] else (req, req)
    from .goal import _VERB
    parts: list[str] = []
    for c in _CLAUSE_SPLIT.split(re.sub(r"(?<=[.!?।])\s+", "\n", rest)):
        c = _CLAUSE_LEAD.sub("", (c or "").strip(" .")).strip(" .")
        if not c:
            continue
        if parts and not (_VERB.search(c) or re.search(r"\b(?:karo|karna|do|dena|dekho|batao|likho|bhejo|dhoondo|dhundo|dhoondho|nikalo|banao|lao|kholo|padho|bharo|check|socho|lagao|chuno|bhar|bata)\b", c, re.I)):
            parts[-1] = (parts[-1] + ", " + c)[:160]     # 'top 8 brands, unki price, range' is ONE step, not three
        elif len(c.split()) >= 2:
            parts.append(c[:160])
    if len(parts) < 2:
        return req, [req[:200]]
    return (head.strip(" .") or req), parts[:8]


def _lang_label(name: str) -> str:
    """v0.728 SAB ENGLISH: the working-row label in English when Hoola is set to English."""
    from .. import lang as _lang
    return _lang.label(name)


def _aage_promised(text: str) -> bool:
    from . import aage as _aage
    return _aage.promised(text)


_ASKS_HER = re.compile(r"\?\s*$|\b(bataiye|batayein|batao|bata\s*dijiye|chahiye|bhej\s*dijiye|share\s*kar|dijiye\s*to"
                       r"|confirm\s*kar|please\s+(?:share|send|tell|confirm)|could\s+you|can\s+you|let\s+me\s+know"
                       r"|which\s+one|kaun\s*s[aie]|kis\s+(?:date|din|time))\b", re.I)
_SAYS_FAILED = re.compile(r"\b(fail|failed|nahi\s*ho\s*pa(?:ya|yi|aya)|nahi\s*hua|nahi\s*ho\s*saka|error|atak\s*gay"
                          r"|could\s*n[o']t|couldn'?t|was\s+unable|unable\s+to|did\s*n[o']t\s+work)\b", re.I)


_OFFER = re.compile(r"[^.!?\n]*\b(aur\s+kuch|kuch\s+aur|aur\s+koi|anything\s+else|something\s+else|kuch\s+bhi\s+aur"
                    r"|aur\s+madad|more\s+help)\b[^.!?\n]*[.!?]?", re.I)


def _close_auto_plan(tenant_id: str, conversation_id: str, g: dict, final_text: str, calls: list | None = None) -> None:
    """v0.311 the server's own plan closes with the model's final answer.
    v0.665 SACH KA HISAAB: only a real finish closes it as DONE. A step that failed ("Step b fail ho gaya, API key
    chahiye") or a question back to her ("Kaunsi date chahiye?") used to tick every remaining step done and show the
    whole job finished on her card; now the first is `failed`, the second `blocked_on_her`, the steps left as they are."""
    from . import goal as _goal
    text = " ".join(str(final_text or "").split())
    did_ok = any(c.get("ok") for c in calls or [])
    some_failed = any(not c.get("ok") for c in calls or [])
    failed_only = bool(calls) and not did_ok
    # a polite closing offer ("Aur kuch karna hai?") is not a question about THIS job
    core = _OFFER.sub(" ", text).strip()
    try:
        if core and _ASKS_HER.search(core[-400:]):
            _goal.finish(tenant_id, g["id"], "blocked_on_her", reason=text[:300], your_turn=text[-300:])
            return
        if failed_only or (some_failed and _SAYS_FAILED.search(text)):
            _goal.finish(tenant_id, g["id"], "failed", reason=text[:300])
            return
        for x in _goal.steps_left(g):
            _goal.mark_step(tenant_id, g["id"], x["n"], "done", conv=conversation_id)
        _goal.finish(tenant_id, g["id"], "done", reason=text[:300])
    except Exception:
        log.exception("auto plan close failed")


def _chat_tail(history: list[dict], keep: int = 8) -> str:
    """What the chat really GAVE: her own words and the tool results of the last few messages (v0.223). Hoola's own
    prose is never a source for itself - least of all the reply being checked, which sits at the end of history."""
    out = []
    for m in (history or [])[-keep:]:
        if m.get("role") != "user":
            continue
        for b in _as_blocks(m.get("content")):
            if not isinstance(b, dict):
                continue
            t = b.get("text") or (b.get("content") if b.get("type") == "tool_result" else None)
            if t:
                out.append(_short(t, 1500) if not isinstance(t, str) else t)
    return "\n".join(out)[-4000:]


_BRAIN_POOL: dict = {}


def _brain_pool():
    import concurrent.futures as _cf
    p = _BRAIN_POOL.get("p")
    if p is None:
        p = _BRAIN_POOL["p"] = _cf.ThreadPoolExecutor(max_workers=6, thread_name_prefix="call-brain")
    return p


_BRAIN_CACHE: dict = {}
_LATE_SAY = {"kaam": "the latest state of her work", "kiya": "this week's finished work", "cards": "the cards still waiting",
             "chat": "recent things said in this chat", "saar": "the chat summary", "facts": "related facts",
             "coder": "coder notes", "yaad": "the diary"}


def _brain_keep(key, fut) -> None:
    try:
        if not fut.cancelled() and fut.exception() is None:
            _BRAIN_CACHE[key] = (time.time(), fut.result() or "")
    except Exception:
        pass
    if len(_BRAIN_CACHE) > 600:
        for k in sorted(_BRAIN_CACHE, key=lambda k: _BRAIN_CACHE[k][0])[:300]:
            _BRAIN_CACHE.pop(k, None)


def _call_chat_saar(conversation_id: str, max_chars: int = 2200) -> str:
    """v0.657 the chat's checkpoint for a call record's brain turn (head + the pending tail)."""
    from .. import callconv as _cc
    chat = _cc.origin_of(conversation_id)
    from . import compact as _compact
    from .. import yaad as _y
    if not chat:
        # a plain chat's brain turn reads its own checkpoint in its history - but a chat that was NEVER compacted has
        # none, and the call brain reads only the last 8 exchanges: wave 11 gives it the chat's rolling summary instead
        if _compact.active(conversation_id):
            return ""
        summ = _y.summary_block(conversation_id)
        return ("Summary of the older part of this chat (before the last 8 exchanges):\n" + _y._clip_ends(summ, max_chars)) \
            if summ else ""
    cp = _compact.active(chat)
    if cp and cp.get("summary"):
        return "CHAT KA SAAR (checkpoint of the chat she called from - open work and promises):\n" + \
            _y._clip_ends(cp["summary"], max_chars)
    summ = _y.summary_block(chat)
    return ("Summary of the older part of this chat:\n" + _y._clip_ends(summ, max_chars)) if summ else ""


def _call_facts(tenant_id: str, conversation_id: str, user_text: str) -> str:
    """v0.657 her facts by MEANING for this ask (an older preference / correction too), in the call's memory scope."""
    if not (user_text or "").strip():
        return ""
    from .. import yaad as _y
    from .. import callconv as _cc
    from ..life import memory_facts, recent_facts
    chat = _cc.chat_of(conversation_id)
    shown = {f.id for f in memory_facts(tenant_id, recent_facts(), chat)}
    rel = _y.relevant_facts(tenant_id, user_text, shown, top=6, conversation_id=chat)
    if not rel:
        return ""
    mk = _y.fact_marks([i for i, _ in rel])   # v0.665 dated; Hoola's own guesses marked as such
    return ("JUDE HUE FACTS (by meaning for this ask; 'Hoola ne samjha' = your own reading, not her words):\n"
            + "\n".join(f"- {t}{mk.get(i, '')}" for i, t in rel))



def _last_reply_at(conversation_id: str):
    """v0.704 when Hoola last replied in this chat (the 'since' of the card news)."""
    from ..db import Message
    from sqlalchemy import select as _sel
    with session() as s:
        return s.scalar(_sel(Message.created_at).where(Message.conversation_id == conversation_id,
                                                       Message.role == "assistant")
                        .order_by(Message.id.desc()).limit(1))


async def _chat_memory(tenant_id: str, conversation_id: str, user_text: str, settings) -> str:
    """v0.704 a chat turn's memory block: diary / facts (yaad), the real job state (kaamwatch), the coder primer and the
    card news read IN PARALLEL, waiting at most `chat_memory_s` in all (they used to run one after another)."""
    from .. import yaad, kaamwatch, events as _ev
    from .. import coder as _coder

    def _cards():
        return _ev.card_news_block(tenant_id, _last_reply_at(conversation_id), user_text or "", conversation_id)

    parts = [("yaad", lambda: yaad.turn_block(tenant_id, conversation_id, user_text)),
             ("kaam", lambda: kaamwatch.block(tenant_id, conversation_id)),
             ("cards", _cards),
             ("coder", lambda: _coder.inject.turn_block(tenant_id, conversation_id, query=user_text or ""))]
    tasks = {name: asyncio.ensure_future(asyncio.to_thread(fn)) for name, fn in parts}
    t0 = time.monotonic()
    done, pending = await asyncio.wait(tasks.values(), timeout=float(getattr(settings, "chat_memory_s", 6.0) or 6.0))
    out = []
    for name, t in tasks.items():
        if t in done:
            try:
                v = t.result()
            except Exception:
                log.exception("chat memory part %s failed", name)
                continue
            if v:
                out.append(v)
        else:
            log.info("chat memory: %s not ready in %.1fs, left out of this turn", name, time.monotonic() - t0)
    log.info("chat memory %.2fs (%s)", time.monotonic() - t0, ",".join(n for n, t in tasks.items() if t in done))
    return "\n\n".join(out)

async def _brain_memory(tenant_id: str, conversation_id: str, user_text: str, settings) -> str:
    """v0.638 the memory block of a call's brain turn: diary/facts (yaad), the real job state (kaamwatch) and the coder
    primer read IN PARALLEL, waiting at most `voice_brain_memory_s` in all. A part that is not ready in time is left out
    of THIS ask (it is not cancelled - it finishes in its thread and the next ask reads it again); the job state is
    the part that matters most on a call ("ho gaya kya?") and is a quick DB read."""
    from .. import yaad, kaamwatch
    from .. import coder as _coder
    parts = [
        ("kaam", lambda: kaamwatch.block(tenant_id, conversation_id)),
        ("coder", lambda: _coder.inject.turn_block(tenant_id, conversation_id, query=user_text or "")),
    ]
    from .. import kaamlist as _kaamlist
    # v0.648 KAAM KA HISAAB: what finished this week (two small queries), so "kal jo kaam diya tha" needs no extra step
    parts.append(("kiya", lambda: _kaamlist.brief(tenant_id, conversation_id)))
    from .. import events as _events_cb
    # v0.650 JAWAB MIL GAYA: the cards that really still wait for her (a tapped card is never asked about again)
    parts.append(("cards", lambda: _events_cb.cards_block(tenant_id)))
    from .. import callconv as _callconv
    # v0.646 ALAG CALL, EK YAAD: a call on its own record still knows what she just wrote in the chat she called from
    # (chat_block itself says "" for a plain chat - checked in its thread, never a DB read on the event loop, v0.650)
    parts.append(("chat", lambda: _callconv.chat_block(conversation_id)))
    # v0.657 a call record's brain turn reads the ORIGIN chat's checkpoint (open work, promises) - its own history is
    # the call's few exchanges, so the chat's pending work never reached it - and her facts BY MEANING (an older
    # standing preference / correction, not only the 15 newest facts in the prompt)
    parts.append(("saar", lambda: _call_chat_saar(conversation_id)))
    parts.append(("facts", lambda: _call_facts(tenant_id, conversation_id, user_text)))
    if getattr(settings, "voice_brain_yaad", False):
        # v0.644 off by default: on EVERY call ask since v0.638 the diary / facts read missed its wait (17:25, 17:34, 17:44,
        # 17:51 - "yaad not ready in 2.5s"), so each ask paid the full wait for nothing; old memory stays one
        # yaad_khojo call away when a question needs it
        parts.insert(0, ("yaad", lambda: yaad.turn_block(tenant_id, conversation_id, user_text)))
    # v0.639 its OWN small pool: on her 16:52 call even the quick job-status read missed 2.5 s, queued behind the
    # shared default pool (every to_thread in the server) - a call's reads never wait behind background work
    loop = asyncio.get_running_loop()
    import contextvars as _cvs
    tasks = [asyncio.ensure_future(loop.run_in_executor(_brain_pool(), _cvs.copy_context().run, fn)) for _, fn in parts]
    wait_s = float(getattr(settings, "voice_brain_memory_s", 2.5) or 2.5)
    done, pending = await asyncio.wait(tasks, timeout=wait_s)
    out, late = [], []
    for (name, _), t in zip(parts, tasks):
        if t in done:
            try:
                txt = t.result()
            except Exception:
                log.exception("call brain memory part %s failed", name)
                continue
            _BRAIN_CACHE[(conversation_id, name)] = (time.time(), txt or "")
            if txt:
                out.append(txt)
        else:
            late.append(name)
            # v0.657 the part finishes in its thread and is KEPT for the next ask (before, the next ask re-ran it)
            t.add_done_callback(lambda f, k=(conversation_id, name): _brain_keep(k, f))
            hit = _BRAIN_CACHE.get((conversation_id, name))
            if name != "kaam" and hit and time.time() - hit[0] < 600 and hit[1]:
                out.append(hit[1])        # a few minutes old is far better than nothing (job state never: it moves)
    if late:
        # v0.657 never a silent gap: the brain is told what it does NOT have, so it checks instead of guessing
        miss = [_LATE_SAY.get(n, n) for n in late]
        out.append("(This part of memory is not loaded yet: " + ", ".join(miss) + ". If she asks about these, first "
                   "look with a tool - the state of work with kaam_status, older things with yaad_khojo; do not guess.)")
        STATS_PREP["memory_late"] = STATS_PREP.get("memory_late", 0) + 1
        from .. import looplag
        log.info("call brain memory: %s not ready in %.1fs, left out of this ask (shared pool queue %d)",
                 ",".join(late), wait_s, looplag.pool_queue())
    return "\n\n".join(out)


def _cut_old_results(msgs: list[dict], cap: int) -> list[dict]:
    """v0.636 a call brain turn: an EARLIER exchange's big tool result (a whole email, a page) is cut to `cap` chars
    (her 16:22 call sent 143k chars a call, mostly old mails). This turn's own results are never passed here."""
    if cap <= 0:
        return msgs
    out = []
    for m in msgs:
        c = m.get("content") if isinstance(m, dict) else None
        if m.get("role") == "user" and isinstance(c, list):
            nb, changed = [], False
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result" and isinstance(b.get("content"), str) \
                        and len(b["content"]) > cap:
                    nb.append({**b, "content": b["content"][:cap] + " ...[old result shortened; run the tool again if you need all of it]"})
                    changed = True
                    STATS_PREP["results_cut"] += 1
                else:
                    nb.append(b)
            out.append({**m, "content": nb} if changed else m)
        else:
            out.append(m)
    return out


def _request(history: list[dict], system: str, tools, brain: str, conversation_id: str, state: dict,
             settings) -> list[dict]:
    """v0.237 FULL CLAUDE MODE: what this model call sends. Old tool results trimmed (v0.189 prune, as before), then the
    gauge: the whole chat while it fits, else the safety net (context.fit); after a "too long" answer, the hard form
    (context.squeeze) for the rest of the turn. Projections only: `history` itself is never changed."""
    from . import context as _ctx
    pruned = prune_history(history)
    start = state.get("turn_start", len(history))
    if state.get("squeezed"):
        return _sanitize(_ctx.squeeze(pruned, conversation_id, start))
    keep = int(getattr(settings, "voice_brain_history", 0) or 0)
    if VOICE_BRAIN_NOW.get() and keep > 0:
        # v0.634 TEZ DIMAAG: a call's brain turn reads the chat's checkpoint summary + the last few exchanges, not the
        # whole chat word for word (her 15:27 call: 3-5 s before every first step, 21 s on one ask). Older memory is
        # still one yaad_khojo away; this turn's own messages are never cut.
        start = max(0, min(start, len(pruned)))
        head, old = _ctx._split_head(pruned[:start])
        recent = [m for ex in _ctx._exchanges(old)[-keep:] for m in ex]
        return _sanitize(head + _cut_old_results(recent, int(getattr(settings, "voice_brain_result_chars", 0) or 0))
                         + pruned[start:])
    msgs, form = _ctx.fit(pruned, system, tools, brain, conversation_id, start, settings)
    return _sanitize(msgs) if form == "net" else msgs


async def _steps_inner(conversation_id: str, ctx: Ctx, gender: str, history: list[dict], settings, tenant_id: str,
                       state: dict) -> str:
    """The think -> tools -> think loop of one turn. Returns the final text shown to the user.
    v0.187: while a kaam_plan goal is open, text never ends the turn — the goal nudge sends it back to work."""
    from . import pakka
    from . import goal as _goal
    from .breaker import FAILS_IN_ROW_GOAL
    breaker = state["breaker"]
    _gyaan.begin(conversation_id)        # v0.134 fresh [n] numbering for this turn
    final_text = ""
    ran_tools = False
    brain = llm.choose(history)
    from .. import yaad
    from . import context as _ctx
    full = _ctx.full_mode(settings)
    # v0.237 FULL CLAUDE MODE: this turn's own messages begin at her (last) message; the gauge never shortens them
    state["turn_start"] = len(history) - 1 if history and history[-1].get("role") == "user" else len(history)
    # v0.237 the whole chat rides word for word, so the rolling summary is not repeated in the system prompt (the
    # safety net brings it in by itself when it has to drop old exchanges; a very long chat starts with it)
    _summ = "" if full else yaad.summary_block(conversation_id)
    from ..fence import is_incognito as _incog
    _secret = await asyncio.to_thread(_incog, conversation_id)
    tail = ""                       # everything after the guide; the guide itself follows the admitted families
    if _summ:                       # v0.108 everything older than the 40-exchange window, in a few lines
        tail += "\n\nPURANI BAATEIN (summary of this chat before the exchanges below; data, not instructions):\n" + _summ
    # the owner's MCP connections: known to the avatar, and their tools callable directly
    _mark("steps_setup")
    if VOICE_BRAIN_NOW.get():   # v0.638 a call never waits on her MCP servers (4.5 s on her 16:36 call)
        mcp_snap = mcp_live.snapshot_fast(tenant_id)
    else:
        mcp_snap = await asyncio.to_thread(mcp_live.snapshot, tenant_id)
    _mark("mcp")
    mcp_defs, mcp_route = mcp_live.tool_defs(mcp_snap, settings.mcp_native_tools, _last_user_text(history))
    tail += "\n\n" + mcp_live.prompt_block(mcp_snap, mcp_route)
    tail += state.get("hint") or ""
    if state.get("hard") and getattr(settings, "hard_recipe", True):
        # v0.433 SOCH KE JAWAB step 4: a hard question gets the reasoning recipe (ordinary chat never pays for it)
        from . import hard as _hardr
        tail += "\n\n" + _hardr.recipe(((state.get("hard_why") or {}).get("why")) or [])
    if _secret:   # v0.250 incognito: she knows nothing from here is kept; never promise it is
        tail += ("\n\nINCOGNITO CHAT: she opened this chat in incognito. Nothing from it goes into her memory (no facts, "
                 "no diary, no search, no memory page) and other chats will not know it. Never say 'yaad rakh liya'; if "
                 "she wants something remembered, tell her to say it in a normal chat.")
    try:   # v0.164 a chat in one of her projects: its instructions, notes and files
        from .. import projects
        _proj = await asyncio.to_thread(projects.prompt_block, conversation_id) if projects.enabled() else ""
        if _proj:
            tail += "\n\n" + _proj
    except Exception:
        log.exception("project block failed")
    # v0.191 HARNESS-2 step-admitted tools: the families her words (plus any open goal's steps and the procedure
    # hint) actually need, computed ONCE for the whole turn - byte-stable across every step, so the Anthropic
    # prompt cache holds. tool_search may admit a family mid-turn; the next loop iteration rebuilds the list.
    adm = None
    # v0.270 the background rounds of HER long job ("goal") are routed too: they used to see the whole 425-tool
    # registry (pc_do / hoola_pc_do with their long "do anything" text), so a deep-research + PDF job drifted onto a PC
    # v0.558 HER scheduled routines too: a routine call used to carry all ~570 tools (~740 KB, ~184k tokens) on every
    # call; core families stay always on, her words pick the rest, tool_search opens any other one - gates unchanged
    if (getattr(ctx, "actor", "owner") or "owner") in ("owner", "wake", "goal", "routine") or \
            str(getattr(ctx, "actor", "owner") or "owner").startswith("approved:"):
        _extra = state.get("hint") or ""
        _g0 = state.get("goal")
        if _g0:
            _extra += " " + " ".join(str(s.get("text") or "") for s in (_g0.get("steps") or []))
        adm = _admit.plan_for(state.get("request", ""), settings, extra_text=_extra)
        if adm is not None:   # v0.311 a family this chat already works in stays in view (campaign follow-ups)
            _sticky = await asyncio.to_thread(_admit.sticky_families, conversation_id)
            if _sticky - adm.families:
                adm.admit_families(_sticky)
                adm.why.update({f: "chat" for f in _sticky})
    if adm is not None and state.get("hard"):
        adm.extra.add("pylab")      # v0.430 a hard ask the judge (not the rules) found also gets the sandbox
    if adm is not None:             # v0.494 a LEARNED SKILL matched this ask: skill_manage must be callable to read it
        try:
            from .. import coder as _coder_adm
            await asyncio.to_thread(_coder_adm.inject.admit_tool, adm, tenant_id, state.get("request", "") or "")
        except Exception:
            log.exception("skill tool admission failed")
    _mark("admit")
    ctx.admit = adm                 # tool_search writes through here (None = admission off)
    ctx.calls = state["calls"]      # v0.443 kaam_plan's `tool:<name>` check reads what really ran this job
    # v0.645 KHULA LOOP: the context block + the system prompt read ~25 DB-backed blocks (aftersales due list, shop,
    # site, brand...) - built on the event loop they froze the WHOLE server (her 17:59 call: 2.1 s in aftersales.due)
    _ctxb = await asyncio.to_thread(context_block, tenant_id, conversation_id)   # v0.246 facts fenced to this chat's Session

    def _system(fams) -> str:
        # v0.473 PATLA PROMPT: only the guides of the admitted families ride (None = the full guide, as before)
        text = system_prompt(settings.wa_dry_run, _ctxb, tenant_id,
                             families=None if (fams is None or not settings.prompt_slim) else fams) + tail
        return text + (_admit.unloaded_note(text, adm) if adm is not None else "")
    sys_fams = frozenset(adm.families) if adm is not None else None
    system = await asyncio.to_thread(_system, sys_fams)
    tools = (adm.specs()) + mcp_defs if adm is not None else TOOLS + mcp_defs
    _mark("prompt")
    from .. import livereply
    live = None if conversation_id in _NO_STREAM else livereply.current(conversation_id)
    ran_steps = 0
    while ran_steps < (settings.agent_goal_max_steps if (state.get("goal") or state.get("extended"))
                       else settings.agent_max_steps):
        ran_steps += 1
        from . import toolsearch as _ts
        native = adm is not None and _ts.on(settings, brain)
        ctx.native_search = native
        if native:
            # v0.563 CLAUDE KA AUZAAR: the whole toolbox declared once (in view + the rest deferred) and never changed
            # inside the turn - tool_search answers with tool_reference blocks instead of growing the list
            if state.get("native_tools") is None:
                state["native_tools"] = _ts.build(adm.specs() + mcp_defs)
                _ts.NATIVE["turns"] += 1
            tools = state["native_tools"]
            ctx.native_loaded = {t.get("name") for t in tools if not t.get("defer_loading")}
        else:
            tools = (adm.specs()) + mcp_defs if adm is not None else TOOLS + mcp_defs   # v0.191 after tool_search
        if adm is not None and not native and frozenset(adm.families) != sys_fams:
            # tool_search opened a family mid-turn: its guide joins the system prompt too (one cache re-write)
            sys_fams = frozenset(adm.families)
            system = await asyncio.to_thread(_system, sys_fams)
        if settings.agent_goal and "goal" not in state:
            # v0.187 the plan can be written mid-turn (kaam_plan set): the goal caps rise from that moment
            g_top = _goal.active_for(conversation_id)
            if g_top is not None:
                state["goal"] = g_top
                b = state["breaker"]
                b.max_calls, b.fails_in_row, b.rescue = settings.agent_goal_max_calls, FAILS_IN_ROW_GOAL, True
                state["max_tokens"] = settings.agent_goal_max_tokens
        # v0.232 PHASE C: this step's model call thinks out loud when a long job runs (read by _think; a contextvar so
        # sub-agents and every caller of _think keep their signature, and the team's own calls never think)
        _long_now = bool(state.get("goal") or state.get("extended") or state.get("auto_plan") or state.get("big"))
        if _long_now and brain != "claude" and _claude_ready() and getattr(settings, "agent_long_on_claude", True):
            brain = "claude"   # v0.331 a long job runs on Claude even when a cheaper brain answers ordinary chat
        if state.get("hard") and brain != "claude" and _claude_ready() and getattr(settings, "agent_hard_on_claude", True):
            brain = "claude"   # v0.429 a hard reasoning ask runs on Claude even when a cheaper brain answers chat
        _EFFORT_NOW.set(effort_for(settings, _long_now, bool(state.get("hard"))))
        _MODEL_NOW.set(model_for(settings, bool(state.get("hard")), _long_now) if brain == "claude" else "")
        _THINK_NOW.set(think_wanted(settings, bool(state.get("goal") or state.get("big") or
                                                   (state.get("hard") and getattr(settings, "hard_thinking", True)))))
        if VOICE_BRAIN_NOW.get():
            # v0.635 she is waiting on the line: a call's brain turn never thinks out loud or runs at a raised effort
            # (an open long job in the chat used to switch both on for EVERY call question)
            _EFFORT_NOW.set("")
            _THINK_NOW.set(False)
        if live is not None:   # Gyaan answers are rewritten at the end (links, numbers): those show only when final
            # v0.436 SOCH KE JAWAB step 5: a hard answer is held too - it is checked before she sees it (thinking
            # still streams on the Soch card)
            live.block(stream=not (_gyaan.used(conversation_id) or _hard_held(state, settings, conversation_id)))
        _mark("step_setup")
        _conv_tok = _ctx.CONV.set(conversation_id)   # v0.237 the model's real token count lands on this chat's reading
        try:
            try:   # stays on the brain that worked; Rokiye cancels the model call itself, not just the next step
                blocks, stop, brain = await _watched(_think(brain, system, _request(history, system, tools, brain,
                                                                                   conversation_id, state, settings),
                                                             settings, tools, live, state.get("max_tokens")),
                                                     conversation_id, ctx, state)
            except _Halted:
                raise
            except Exception as e:
                if _ctx.is_overflow(e) and not state.get("squeezed"):
                    # v0.237 the model said the chat is too long: the hard form, ONCE - a chat never gets stuck on size
                    _ctx.overflowed(brain, e)
                    from . import compact as _compact
                    _compact.FORCE.add(conversation_id)   # v0.242 the next turn compacts first
                    state["squeezed"] = True
                    log.warning("context overflow on %s (%s); retrying once with the squeezed chat", brain, str(e)[:200])
                    if live is not None:
                        live.reset()
                elif mcp_defs and mcp_live.schema_trouble(e):
                    # a server's tool description the model refuses: go on without the direct MCP tools (bazar_run still works)
                    log.warning("MCP tool schemas refused (%s); continuing without them", str(e)[:200])
                    mcp_defs, mcp_route, tools = [], {}, TOOLS
                    if state.get("native_tools") is not None and adm is not None:   # v0.563 rebuilt without them
                        from . import toolsearch as _ts2
                        state["native_tools"] = tools = _ts2.build(adm.specs())
                    if live is not None:
                        live.reset()
                else:
                    raise
                blocks, stop, brain = await _watched(_think(brain, system, _request(history, system, tools, brain,
                                                                                   conversation_id, state, settings),
                                                             settings, tools, live, state.get("max_tokens")),
                                                     conversation_id, ctx, state)
        except _Halted as h:
            state["halted"] = h.why
            part = live.partial() if live is not None else ""
            if part:               # v0.161 she stopped it mid-sentence: what she saw is kept, marked stopped
                live.stopped = True
                bus.publish(conversation_id, "message", {"role": "assistant", "text": part, "source": "agent",
                                                         "stopped": True, **_tag(live)})
                _save(conversation_id, "assistant", [{"type": "text", "text": part}], display=part)
            final_text = gendered(HALTED_TEXT[h.why], gender)
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent",
                                                     **_tag(live, bool(part))})
            _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
            return final_text
        finally:
            _ctx.CONV.reset(_conv_tok)
        history.append({"role": "assistant", "content": blocks})
        texts = [b["text"] for b in blocks if b.get("type") == "text" and b.get("text", "").strip()]
        if texts and stop not in ("tool_use", "max_tokens") and state.get("hard_fixed") \
                and not state.get("hard_rechecked"):
            # wave 13: the corrected answer is checked again (free checks only); still failing = said plainly
            state["hard_rechecked"] = True
            if await _hard_check(conversation_id, state, "\n\n".join(texts), history, settings, free_only=True):
                STATS_HARD_UNSURE["n"] += 1
                blocks = blocks + [{"type": "text", "text": HARD_UNSURE.strip()}]
                history[-1] = {"role": "assistant", "content": blocks}
                texts = texts + [HARD_UNSURE.strip()]
        if texts and stop not in ("tool_use", "max_tokens") and _hard_held(state, settings, conversation_id) \
                and not state.get("hard_checked"):
            state["hard_checked"] = True
            problems = await _hard_check(conversation_id, state, "\n\n".join(texts), history, settings)
            if problems:   # v0.436 the draft is kept for the model but never shown; the fixed answer replaces it
                _save(conversation_id, "assistant", blocks, display=None)
                from . import hard as _hardc
                nudge = _hardc.fix_note(problems)
                state["hard_fixed"] = True
                history.append({"role": "user", "content": [{"type": "text", "text": nudge}]})
                _save(conversation_id, "user", [{"type": "text", "text": nudge}])
                continue
        _save(conversation_id, "assistant", blocks, display="\n\n".join(texts) or None)
        if texts:
            final_text = "\n\n".join(texts)
            if stop != "tool_use" and _gyaan.used(conversation_id):
                # v0.134 Gyaan: links from retrieved text removed, numbers checked against the cited sources, source chips
                final_text, srcs = _gyaan.finish(conversation_id, final_text, state.get("request", ""))
                final_text = await _gyaan.ground(conversation_id, final_text)      # v0.135 model check of cited sentences
                if srcs:
                    bus.publish(conversation_id, "gyaan_sources", {"sources": srcs})
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent", **_tag(live)})
        if stop != "tool_use":
            if stop == "max_tokens":
                # v0.187 the words were cut mid-thought: continue exactly where the cut happened, in goal mode and out
                # v0.473 and give the next call more room (a big tool input cut at 2,000 tokens would be cut again)
                state["max_tokens"] = min(16000, 2 * (state.get("max_tokens") or settings.agent_max_tokens))
                state["cuts"] = state.get("cuts", 0) + 1
                nudge = "[System: your reply was cut off in the middle (max_tokens). Continue exactly from there - finish the work or " \
                        "the rest of what you were saying; do not start again.]"
                history.append({"role": "user", "content": [{"type": "text", "text": nudge}]})
                _save(conversation_id, "user", [{"type": "text", "text": nudge}])
                continue
            nudge = await _pakka_check(state, final_text, settings, ran_tools, conversation_id)
            if not nudge and settings.agent_goal:
                # v0.187 goal mode: text never ends a turn while the goal's steps are open
                g = _goal.active_for(conversation_id)
                if g is not None and state.get("auto_plan") == g.get("id") and _goal.steps_left(g) \
                        and not _aage_promised(final_text):
                    # v0.311 the server's own one-step plan closes with the model's real final answer (no
                    # "text mein mat ruko" loop over a plan the model never wrote); a mere promise still goes on
                    _close_auto_plan(tenant_id, conversation_id, g, final_text, state.get("calls"))
                    g = None
                if g is not None and VOICE_BRAIN_NOW.get() and not any(
                        (c or {}).get("tool") == "kaam_plan" for c in (state.get("calls") or [])):
                    # CALL PAR TEAM: a call question that did not touch the job ("kal ka mausam?") is answered as it
                    # is - the open job's rounds carry on in the background, they do not take her call ask over
                    g = None
                if g is not None and _goal.steps_left(g) and state.get("goal_nudges", 0) < 8:
                    state["goal"] = g
                    state["goal_nudges"] = state.get("goal_nudges", 0) + 1
                    nudge = _goal.nudge_text(g)
            # v0.727 a promise with NO tool at all is checked too: "Starting one fresh build now." after "where do I
            # check that" ran nothing and nothing ever started (was gated on ran_tools)
            if not nudge and getattr(settings, "agent_aage", True) \
                    and conversation_id not in _stopped and not state.get("halted"):
                # v0.311 AAGE BADHO: a text-only reply that only PROMISES more work ("ab doosra hissa dekh raha
                # hoon") is not a finished job - before, the loop took it as the answer and nothing more ran
                from . import aage as _aage
                if state.get("aage", 0) < _aage.MAX_PER_TURN and _aage.promised(final_text):
                    state["aage"] = state.get("aage", 0) + 1
                    _aage.STATS["nudged"] += 1
                    nudge = _aage.NUDGE
            if nudge:
                history.append({"role": "user", "content": [{"type": "text", "text": nudge}]})
                _save(conversation_id, "user", [{"type": "text", "text": nudge}])
                continue
            if state.get("correct"):   # the correction is added after the words already shown (never rewrites them)
                # v0.668 only the correction line goes out as its own short message and its own row: the whole answer
                # again (answer + note) showed TWICE on the phone and sat twice in the model's history
                note = state.pop("correct")
                final_text = (final_text + "\n\n" + note).strip()
                bus.publish(conversation_id, "message", {"role": "assistant", "text": note, "source": "agent",
                                                         "note": True, **_tag(live, True)})
                _save(conversation_id, "assistant", [{"type": "text", "text": note}], display=note)
            # v0.688 KAAM MANCH: the work receipt - one (Kaam: ...) note row under the answer when tools ran
            # (OWL's per-round honest record, miniaturized; pure arithmetic over state, never an estimate). The
            # ledger switch is separate so the line can go quiet without touching the tips or the backstop.
            if settings.kaam_enabled and settings.kaam_ledger_enabled and state.get("calls"):
                from . import kaam_laws as _kaam
                _g0 = state.get("goal")
                _line = _kaam.ledger(state, ran_steps,
                                     (settings.agent_goal_max_steps if (state.get("goal") or state.get("extended"))
                                      else settings.agent_max_steps),
                                     plan_left=(len(_goal.steps_left(_g0)) if _g0 else None),
                                     plan_total=(len(_g0.get("steps") or []) if _g0 else 0))
                if _line:
                    bus.publish(conversation_id, "message", {"role": "assistant", "text": _line, "source": "agent",
                                                             "note": True, **_tag(live, True)})
                    _save(conversation_id, "assistant", [{"type": "text", "text": _line}], display=_line)
            break
        async def _one(b: dict) -> dict:
            """One tool_use block, run to its tool_result (v0.189: every path RETURNS exactly one result, so the
            same body serves the serial loop and the parallel gather - behaviour identical to the old inline loop)."""
            nonlocal ran_tools
            if conversation_id in _stopped or state.get("halted"):
                return {"type": "tool_result", "tool_use_id": b["id"], "is_error": True,
                        "content": "The user tapped Stop. Do not continue this task; say in one line what was done."}
            held = breaker.before(b["name"], b.get("input") or {})
            if held:                       # circuit breaker: steered / constrained / stopped, the call does not run
                return {"type": "tool_result", "tool_use_id": b["id"], "is_error": True, "content": held}
            ran_tools = True
            args_in = b.get("input") or {}
            from . import where as _where   # v0.93 the card / work line name the place where it REALLY runs
            shown = _where.shown(b["name"], args_in, getattr(ctx, "place", "") or _where.working(conversation_id))
            label = gendered(mcp_live.label(b["name"], mcp_route, mcp_snap) if b["name"] in mcp_route
                             else _lang_label(shown), gender)
            bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "running", "id": b["id"],
                                                  "args": livework.args_brief(args_in)})   # v0.171 masked, display-safe
            _work(conversation_id, b["id"], shown, label, "start", args_in)
            try:
                out = await _watched(_run_tool(b["name"], args_in, ctx, settings, mcp_route), conversation_id, ctx, state)
                _PROGRESS[conversation_id] = time.time()   # v0.311 the turn is moving (read by _with_deadline)
                _fail = tool_failure(out)   # v0.665 {"ok": False} / status failed is a failure too, not only "error"
                fine = not _fail
                breaker.after(b["name"], fine)
                refs = out.get("tool_references") if isinstance(out, dict) and getattr(ctx, "native_search", False) \
                    else None
                content = refs if refs else _short(out, RESULT_LIMIT.get(b["name"], 6000))   # v0.563 tool_reference
                call = {"tool": b["name"], "ok": fine, "error": "" if fine else _fail[:300],
                        "args": args_in, "key": _key(b["name"], args_in), "result": "" if not fine else str(content)[:300],
                        # v0.665 every figure the tool really returned (the 300-char result above hid row 10's amount,
                        # so the after-reply check called a correct number unsourced)
                        "digits": _facts_of(content) if fine else ""}
                if not fine:
                    content += await pakka.on_failure(tenant_id, b["name"], call["error"], state.get("request", ""), state)
                    call["internet_fix"] = (state.get("web_fix") or {}).get(b["name"], "")
                state["calls"].append(call)
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "done", "id": b["id"],
                                                      "args": livework.args_brief(args_in)})   # v0.171 again: late joiners see it too
                _work(conversation_id, b["id"], shown, label, livework.phase_of(out), args_in, out)
                try:   # v0.187 one true line about the result, out while the next model call thinks
                    _s = _say.line_for(label, shown, out)
                    if _s:
                        # v0.258 CHALTE CHALTE BOLO: the whisper used to die with the turn (livereply.feed_say:
                        # "gone the moment the reply arrives"). The same true fact now also rides into the
                        # narration line, so what she reads between the steps is the tool's own number, not a guess.
                        said_now = state.setdefault("saylines", [])
                        if _s not in said_now:
                            said_now.append(_s)
                            del said_now[:-4]
                        if live is not None:
                            live.feed_say(_s)
                except Exception:
                    log.debug("say line failed", exc_info=True)
                return {"type": "tool_result", "tool_use_id": b["id"], "content": content}
            except asyncio.CancelledError:
                # v0.668 the turn's time limit (or a stop) cancelled this step: say so on the step card before the
                # cancel goes on - it used to stay "running" with a spinner for ever (and "running" again on reload)
                try:
                    state["calls"].append({"tool": b["name"], "ok": False, "error": "cut off (time limit)",
                                           "args": args_in, "key": _key(b["name"], args_in)})
                    bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "error",
                                                          "id": b["id"], "detail": "samay khatam, beech mein roka"})
                    _work(conversation_id, b["id"], shown, label, "stopped", args_in, error="Samay khatam, roka gaya")
                except Exception:   # noqa: BLE001
                    log.debug("cut-off step card failed", exc_info=True)
                raise
            except _Halted as h:
                state["halted"] = h.why
                state["calls"].append({"tool": b["name"], "ok": False, "error": "stopped by the owner", "args": args_in,
                                       "key": _key(b["name"], args_in)})
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "error", "id": b["id"],
                                                      "detail": "roka gaya"})
                _work(conversation_id, b["id"], shown, label, "stopped", args_in, error="Roka gaya")
                return {"type": "tool_result", "tool_use_id": b["id"], "is_error": True,
                        "content": "Stopped by the owner while this step was running; it may have partly happened."}
            except ToolError as e:
                breaker.after(b["name"], False)
                help_ = await pakka.on_failure(tenant_id, b["name"], str(e), state.get("request", ""), state)
                state["calls"].append({"tool": b["name"], "ok": False, "error": str(e)[:300], "args": args_in,
                                       "key": _key(b["name"], args_in),
                                       "internet_fix": (state.get("web_fix") or {}).get(b["name"], "")})
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "error",
                                                      "id": b["id"], "detail": str(e)[:300]})
                _work(conversation_id, b["id"], shown, label, "error", args_in, error=str(e))
                return {"type": "tool_result", "tool_use_id": b["id"], "content": str(e) + help_, "is_error": True}
            except asyncio.TimeoutError:
                breaker.after(b["name"], False)
                state["calls"].append({"tool": b["name"], "ok": False, "error": "timeout", "args": args_in,
                                       "key": _key(b["name"], args_in)})
                # v0.666 the wait stopped, the WORK may not have: a tool running in a thread (a browser job, a render)
                # carries on and can still submit the form. "Try another way" made the model start a second one and
                # the form went twice - now the step's status is checked first and a send / submit is never repeated.
                msg = (f"{b['name']} did not answer in {settings.agent_tool_timeout_s} seconds. It MAY STILL BE "
                       "RUNNING or may be half done - the work was not cancelled. Before doing anything again, check "
                       "what really happened (its own status / result tool, kaam_status, the sent mail / order / "
                       "booking list). NEVER repeat a send, submit, order, payment or booking until you have seen "
                       "that it did not happen; if you cannot check, tell her plainly that it may or may not have gone "
                       "through. For a read-only step, a lighter way or another tool is fine.")
                log.warning("tool %s timed out", b["name"])
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "error",
                                                      "id": b["id"], "detail": "it was taking too long, so I stopped it"})
                _work(conversation_id, b["id"], shown, label, "error", args_in, error="It was taking too long, so I stopped it")
                return {"type": "tool_result", "tool_use_id": b["id"], "content": msg, "is_error": True}
            except Exception as e:  # unexpected bug: tell the model, keep the turn alive
                breaker.after(b["name"], False)
                state["calls"].append({"tool": b["name"], "ok": False, "error": f"crash: {e}"[:300], "args": args_in,
                                       "key": _key(b["name"], args_in)})
                log.exception("tool %s crashed", b["name"])
                help_ = await pakka.on_failure(tenant_id, b["name"], f"internal error: {e}", state.get("request", ""), state)
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "error", "id": b["id"]})
                _work(conversation_id, b["id"], shown, label, "error", args_in, error="Something went wrong")
                return {"type": "tool_result", "tool_use_id": b["id"],
                        "content": f"Internal error in {b['name']}: {e}" + help_, "is_error": True}

        tblocks = [b for b in blocks if b.get("type") == "tool_use"]
        results: list[dict] = []
        if len(tblocks) > 1 and getattr(settings, "agent_parallel_tools", True) \
                and all(_parallel_ok(b) for b in tblocks):
            # v0.189 one step asked for several pure look-ups: they run together (dsh's bounded pool, Claude Code's
            # concurrency-safe read batching), results commit strictly in the model's order. Her Rokiye still lands:
            # every _one watches for the halt itself and returns the stopped result.
            breaker.batch(len(tblocks))   # v0.311 one batch of look-ups = one call against the cap
            outs = await asyncio.gather(*(_one(b) for b in tblocks), return_exceptions=True)
            for b, o in zip(tblocks, outs):
                results.append(o if isinstance(o, dict) else
                               {"type": "tool_result", "tool_use_id": b["id"], "is_error": True,
                                "content": f"Internal error in {b['name']}: {o}"})
        else:
            for b in blocks:
                if b.get("type") != "tool_use":
                    continue
                results.append(await _one(b))
        for _g in (getattr(ctx, "native_guides", None) or []):   # v0.563 a family's guide, opened by tool_search
            results.append({"type": "text", "text": "[Guide for the tools just found]\n" + _g})
        if getattr(ctx, "native_guides", None):
            ctx.native_guides = []
        if getattr(settings, "agent_steer", True):
            try:   # v0.223 PHASE A: what she sent while this job ran rides with this step's results (Claude-style)
                from . import steer as _steer
                said = _steer.take(conversation_id, _held)
                if said:
                    results.append({"type": "text", "text": _steer.note(said)})
                    with session() as _s:   # her words stay in the chat record / her memory (never a 2nd model turn)
                        for _t in said:
                            _s.add(Message(conversation_id=conversation_id, role="user", content=_t, display=_t,
                                           in_history=False, delivered_to_agent=True))
            except Exception:
                log.exception("steering delivery failed")
        if settings.agent_goal and getattr(settings, "agent_plan_early", True):
            # v0.228 PHASE B (Claude-style): a long job narrates as it goes and has its plan early. In goal mode, a
            # run of tool rounds with no line to her asks for ONE progress line; without a plan, N tool steps ask for
            # the plan now (it used to come only at step 24).
            # v0.258 CHALTE CHALTE BOLO: narration is no longer goal-only. v0.228 put it behind `state["goal"]`,
            # so an ordinary ask that ran five tools without a kaam_plan said NOTHING until the answer appeared -
            # the owner's "HOOLA DIRECTLY LOADS THE RESULT". Claude writes a line after every tool group whether or
            # not there is a plan. Only a human-watched lane gets it; a routine talking to itself stays quiet.
            _narrate_lane = (getattr(ctx, "actor", "owner") or "owner") in ("owner", "goal")
            if _narrate_lane:
                spoke = any(b.get("type") == "text" and (b.get("text") or "").strip() for b in blocks)
                state["quiet"] = 0 if spoke else state.get("quiet", 0) + 1
                every = int(getattr(settings, "agent_narrate_every", 1) or 0)
                cap = int(getattr(settings, "agent_narrate_max", 6) or 0)
                if every and state["quiet"] >= every and state.get("narrated", 0) < cap:
                    state["quiet"] = 0
                    state["narrated"] = state.get("narrated", 0) + 1
                    STATS_LONG["narrate"] += 1
                    results.append({"type": "text", "text": _goal.narrate_line(state.get("saylines"))})
            if not state.get("goal") and (not state.get("plan_nudged") and not state.get("extended")
                  and ran_steps >= int(getattr(settings, "agent_plan_after_steps", 6) or 0) > 0
                  and (getattr(ctx, "actor", "owner") or "owner") in ("owner", "goal", "routine")
                  and not any(b.get("name") == "kaam_plan" for b in tblocks)):
                state["plan_nudged"] = True
                STATS_LONG["plan_now"] += 1
                results.append({"type": "text", "text": _goal.PLAN_NOW})
            if (not state.get("goal") and not state.get("auto_plan") and getattr(settings, "agent_auto_plan", True)
                  and (getattr(ctx, "actor", "owner") or "owner") in ("owner", "goal", "routine")
                  and not any(b.get("name") == "kaam_plan" for b in tblocks)
                  and _goal.active_for(conversation_id) is None
                  and (state.get("big")
                       or (state.get("plan_nudged")
                           and ran_steps >= int(getattr(settings, "agent_plan_after_steps", 4) or 0) + 3))):
                # v0.311 PLAN HAMESHA: the plan was asked for and the model still works without one. Everything that
                # keeps a long job alive (80 steps / 150 calls / 45 min, background rounds, restart pickup, her card)
                # only exists once a plan exists - so the SERVER writes it now instead of hoping the model will.
                # v0.315 a clearly big ask (PLAN_FIRST was given) gets it right after the FIRST tool round: her test
                # 3 ("marketing plan: research, ideas, calendar, PDF") finished in 5 steps with no card at all.
                note = _auto_plan(conversation_id, tenant_id, state, settings, ctx)
                if note:
                    results.append({"type": "text", "text": note})
        history.append({"role": "user", "content": results})
        if state["breaker"].rescue_note:   # v0.187 the replan rescue rides with the results, as data for the model
            note = state["breaker"].rescue_note
            state["breaker"].rescue_note = ""
            history[-1] = {"role": "user", "content": results + [{"type": "text", "text": note}]}
            if live is not None:
                live.new_text_block()
            bus.publish(conversation_id, "message", {"role": "assistant", "text": gendered("Changing my approach - taking a different route.", gender),
                                                     "source": "agent", **_tag(live, True)})
        _save(conversation_id, "user", results)
        if breaker.stopped:                # stuck: stop here and say so plainly
            log.warning("circuit breaker stopped a turn: %s", breaker.stopped)
            final_text = gendered(breaker.final_text(), gender)
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent",
                                                     **_tag(live, True)})
            bus.publish(conversation_id, "work", {"id": "breaker", "tool": "", "scene": "work", "phase": "stopped",
                                                  "label": "Atak gaya, roka gaya", "data": {}})
            _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
            return final_text
        if (settings.agent_goal and not state.get("goal") and not state.get("extended")
                and ran_steps >= settings.agent_max_steps
                and (getattr(ctx, "actor", "owner") or "owner") in ("owner", "routine", "wake", "goal")):
            # v0.473 the short-job cap is reached while work is still going (the model never wrote a plan): instead of
            # "Yeh kaam lamba ho gaya, yahin ruk raha hoon" the turn moves to the long-job caps ONCE and the model is
            # told to write the plan of what is left - long jobs no longer die at step 24.
            state["extended"] = True
            _LONG_TURN.add(conversation_id)
            STATS_LONG["extended"] += 1
            b = state["breaker"]
            b.max_calls, b.fails_in_row, b.rescue = settings.agent_goal_max_calls, FAILS_IN_ROW_GOAL, True
            state["max_tokens"] = max(state.get("max_tokens") or 0, settings.agent_goal_max_tokens)
            ext = ("[System: this job is long and not finished yet. Do not stop. Now write the steps of the remaining work with `kaam_plan set` "
                   "(mark what is already done as done), then carry on until it is complete.]")
            history[-1] = {"role": "user", "content": list(history[-1]["content"]) + [{"type": "text", "text": ext}]}
        if conversation_id in _stopped or state.get("halted"):
            final_text = gendered(HALTED_TEXT.get(state.get("halted") or "stop", HALTED_TEXT["stop"]), gender)
            if state.get("halted"):
                final_text += " The step that was running was stopped midway; please check how much got done before doing it again."
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent",
                                                     **_tag(live, True)})
            _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
            return final_text
    else:
        # the step cap ran out: an honest line, never the stale mid-task text
        g = _goal.active_for(conversation_id) if settings.agent_goal else None
        if g is not None and _goal.steps_left(g):
            state["goal"] = g
            honest = (f"Goal in progress: {g['done']}/{g['total']} steps done ({g['goal'][:120]}); "
                      f"{len(_goal.steps_left(g))} left - I am carrying on in the background.")
            final_text = (final_text + "\n\n" + honest).strip() if final_text else honest
            bus.publish(conversation_id, "message", {"role": "assistant", "text": honest, "source": "agent", **_tag(live, True)})
            _save(conversation_id, "assistant", [{"type": "text", "text": honest}], display=honest)
            return final_text
        # v0.665 SACH KA HISAAB: the honest line is said EVERY time (a mid-task "ab doosra hissa bhej raha hoon" used to
        # be returned as the final answer and the turn recorded "done"), and the outcome is partial, never done
        state["left"] = state.get("left") or "the step limit was reached, the work is not finished"
        honest = "This task has become long and is not finished yet - I am stopping here. Shall I carry on?"
        bus.publish(conversation_id, "message", {"role": "assistant", "text": honest, "source": "agent",
                                                 **_tag(live, True)})
        # v0.473 saved too: the next turn must know the work stopped half-way (before, only she saw this line)
        _save(conversation_id, "assistant", [{"type": "text", "text": honest}], display=honest)
        return (final_text + "\n\n" + honest).strip() if final_text else honest
    if not final_text.strip():
        # the model finished without a word: never leave the user staring at a silent chat
        # v0.665 only when a tool really finished: "Kaam ho gaya" after every tool failed was made up
        _cs = state.get("calls") or []
        _bad = [c for c in _cs if not c.get("ok")]
        if ran_tools and _cs and len(_bad) == len(_cs):
            state["left"] = state.get("left") or "no step finished"
            final_text = ("Sorry, I could not do this - the steps I ran got stuck ("
                          + (str(_bad[-1].get("error") or "")[:120] or "error") + "). Shall I try again?")
        elif ran_tools and _bad:
            state["left"] = state.get("left") or "some steps got stuck"
            final_text = gendered("Part of it is done, but not all - some steps got stuck. Shall I redo the rest?", gender)
        else:
            # wave 13: no "Aur kuch karna hai?" tail (the reply rule forbids it), and the not-understood line gendered too
            final_text = "Done." if ran_tools else \
                gendered("Sorry, I did not understand that. Could you say it once more?", gender)
        bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent",
                                                 **_tag(live, True)})
        _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
    return final_text


_stopped: set[str] = set()


def _record_cut(tenant_id: str, conversation_id: str, user_text: str, why: str, t0: float) -> None:
    """v0.652 SACHCHA NATIJA: a turn that hit its time limit or crashed used to leave NO outcome - a call then read the
    PREVIOUS ask's outcome (often "done") and said "ho gaya" for work that stopped, and the work diary / Kaam list never
    showed it. Now it is "stuck" in LAST_OUTCOME (fresh `at`) and in the task log."""
    LAST_OUTCOME[conversation_id] = {"outcome": "stuck", "left": why, "goal": "", "at": time.time()}
    if not user_text or str(user_text).lstrip().startswith(("[", "(")):
        return
    try:
        from ..fence import is_incognito
        from . import pakka
        if not is_incognito(conversation_id):
            pakka.record(tenant_id, user_text, "stuck", [], {"conv": conversation_id}, time.time() - t0, why)
    except Exception:
        log.exception("cut turn record failed")

# v0.191 wake turns never stream: a live call on this chat owns its own reply stream (livereply), and the
# wake turn's words must publish as plain messages instead of feeding into it.
_NO_STREAM: set[str] = set()

# v0.187 the first words come fast: a turn that says nothing for agent_ack_after_s seconds sends a tiny human
# line ("Ek second, dekh rahi hoon…") as an EPHEMERAL message - no Event row, no push, never in history, the
# real reply replaces it. One ack per turn, owner chats only (voice calls have their own ack clips).
_ACKED: set[str] = set()
ACK_LINES = ("One second, looking into it…", "On it, just a moment…", "Thinking, one minute…",
             "Started, it is running…", "Let me check, back in a moment…", "Got the task, getting going…")


def _assistant_spoke_recently(conversation_id: str, seconds: float) -> bool:
    """Any assistant words already out in this chat in the last `seconds` (any publish path saves them)."""
    try:
        cut = now() - timedelta(seconds=seconds)
        with session() as s:
            row = s.scalars(select(Message.id).where(Message.conversation_id == conversation_id,
                                                     Message.role == "assistant", Message.created_at >= cut)).first()
        return row is not None
    except Exception:
        return False


async def _ack_later(conversation_id: str, gender: str, delay: float | None = None) -> None:
    """The delayed ack itself: run as a background task the moment a turn takes the chat. Every condition is
    re-checked AFTER the wait - the turn may have finished, spoken, or been stopped meanwhile."""
    try:
        if delay is None:
            delay = float(getattr(get_settings(), "agent_ack_after_s", 5.0) or 0)
        if delay > 0:
            await asyncio.sleep(delay)
        if conversation_id not in _ACKED or conversation_id in _stopped:
            return
        if not _locks.get(conversation_id) or not _locks[conversation_id].locked():
            return                   # turn over - the reply is there, no comfort needed
        from .. import livereply
        lv = livereply.current(conversation_id)
        if lv is not None and lv.partial():
            return                   # words are already streaming
        if _assistant_spoke_recently(conversation_id, max(delay + 2.0, 6.0)):
            return                   # an interim message said something already
        line = gendered(random.choice(ACK_LINES), gender)
        bus.publish(conversation_id, "message", {"role": "assistant", "text": line, "source": "agent", "ack": True},
                    ephemeral=True)
    except asyncio.CancelledError:
        raise
    except Exception:
        log.debug("ack line failed", exc_info=True)
    finally:
        _ACKED.discard(conversation_id)

# v0.173 steering: a message she took back while it was only queued (Hoola busy with the previous kaam) never
# reaches the model. _active_msg remembers which message's turn is running right now, so a take-back can refuse
# the one that already started (Rokiye is for that) and allow the ones still waiting behind the lock.
_held: set[tuple[str, str]] = set()
_active_msg: dict[str, str] = {}


def hold_message(conversation_id: str, client_id: str) -> None:
    if client_id:
        _held.add((conversation_id, client_id))


def message_running(conversation_id: str, client_id: str) -> bool:
    """True when this exact message's turn is the one running now (take-back too late — Rokiye instead)."""
    from .. import livereply
    return _locks[conversation_id].locked() and client_id != "" and _active_msg.get(conversation_id, "") == client_id \
        or (livereply.current(conversation_id) is not None and client_id != ""
            and _active_msg.get(conversation_id, "") == client_id)


def _tag(live, new_block: bool = False) -> dict:
    """v0.161 `turn` / `seg` of the live reply for a message (nothing when streaming is off: messages as before)."""
    return live.tag(new_block) if live is not None else {}


def _key(name: str, args) -> str:
    from .breaker import _key as k
    return k(name, args)


def _goal_now(conversation_id: str, settings) -> dict | None:
    """The working goal of this chat (v0.443: the claim check asks the whole job, not one round)."""
    if not getattr(settings, "agent_goal", True):
        return None
    from . import goal as _g
    return _g.active_for(conversation_id)


async def _pakka_check(state: dict, final_text: str, settings, ran_tools: bool, conversation_id: str) -> str:
    """v0.78 self-check before the turn ends: real results vs. her request. Returns a nudge to keep working, or ''.
    Sets state['correct'] when the answer claims more than was done, state['left'] when something stays open.
    v0.187 goal mode: 4 self-checks a turn instead of 2."""
    from . import draftcheck, pakka
    cap = pakka.SELF_CHECKS_GOAL if state.get("goal") else pakka.SELF_CHECKS_PER_TURN
    if conversation_id in _stopped or state["breaker"].stopped or state.get("halted"):
        return ""
    if settings.draft_check:
        # v0.223 free, in code: the reply claims work that never ran. pakka below owns the case where tools DID run.
        # v0.443 (long-task report item 2) this used to be switched OFF for the whole of goal mode, on the idea that
        # the plan's own "X/Y steps ho gaye" line was truth enough - but a step is ticked by the MODEL, so a goal
        # could tick steps and claim sent / booked / saved with only reads behind it. Goal mode now gets the same
        # free check; its own honest lines never trip it (_ALREADY_HONEST + the goal line carries no claim verb).
        g0 = state.get("goal") or (_goal_now(conversation_id, settings))
        since = None
        if g0:
            from . import goal as _g
            since = _g.started_at(g0["id"]) if g0.get("id") else None
        fake = draftcheck.fake_done(state, final_text, conversation_id, since)
        if fake:
            return fake
    calls = state.get("calls") or []
    if not ran_tools or not calls or state.get("checks", 0) >= cap:
        return ""
    real = [c for c in calls if c.get("tool") not in pakka.SKIP]
    if not real:
        return ""
    # v0.688 KAAM MANCH (OWL's <TASK_DONE> law, in code): the free backstop for the paths the model self-check
    # never reaches (the simple-job skip below, the checks cap above) - a strong done-claim while EVERY real
    # call failed is always wrong, and it costs no model call to know it. Sets the correction note only.
    if settings.kaam_enabled:
        from . import kaam_laws as _kaam
        _note = _kaam.done_note(state, final_text)
        if _note:
            state["correct"] = _note
            return ""
    failed = any(not c.get("ok") for c in real)
    if not failed and len(real) < 3:          # a simple job that went fine: no extra model call
        return ""
    state["checks"] = state.get("checks", 0) + 1
    v = await pakka.self_check(state.get("request", ""), calls, final_text, settings)
    if not v:
        return ""
    if v["done"]:
        state.pop("left", None)
        return ""
    state["left"] = v["missing"] or "kuch hissa baaki"
    if v["next"]:
        state["kept_going"] = state.get("kept_going", 0) + 1
        pakka.STATS["kept_going"] += 1
        return ("[System self-check, not the user] The task is NOT finished yet: " + (v["missing"] or "something is left")
                + ". Next step: " + v["next"] + ". Do it now with the tools (follow every card / approval rule as usual). "
                "If it truly cannot be done, say plainly what is done, what is left and what she can do.")
    if not v["claim_ok"]:
        pakka.STATS["corrected_claims"] += 1
        state["correct"] = "(To be clear: this is still left - " + (v["missing"] or "some part") + ".)"
    return ""


_STOP_AT: dict[str, float] = {}
STOPPED_IN_PREP = "Okay, stopped - nothing was started this time."


def stop(conversation_id: str) -> None:
    """The owner tapped Stop: the running model call / tool call is cancelled at once (v0.91), nothing more runs,
    and an open goal of this chat is marked stopped (v0.187: Rokiye stops the goal, not just the turn)."""
    _stopped.add(conversation_id)
    _STOP_AT[conversation_id] = time.time()   # v0.662 when: a Stop during a turn's preparation is no longer erased
    bus.publish(conversation_id, "work", {"id": "stop", "tool": "", "scene": "work", "phase": "stopped",
                                          "label": "Roka gaya", "data": {}})
    try:
        from . import goal as _goal
        _goal.mark_stopped(conversation_id)
    except Exception:
        log.exception("goal stop failed")


def turn_running(conversation_id: str) -> bool:
    """v0.178 is a turn of this chat holding the lock right now? (The SSE stream refreshes the typing dots only
    while this is true, so a crashed turn's dots go away on the phone by themselves.)"""
    return _locks[conversation_id].locked()


def _work(conversation_id: str, call_id: str, tool: str, label: str, phase: str, args=None, out=None, error: str = "") -> None:
    if phase == "start":
        from . import quick
        quick.note_step(conversation_id, label)
    try:
        bus.publish(conversation_id, "work", livework.event(call_id, tool, label, phase, args, out, error))
    except Exception:
        log.exception("work event failed")


async def run_turn(conversation_id: str, user_text: str, tenant_id: str | None = None, voice: bool = False,
                   context: str = "", actor: str = "owner", place: str = "", client_id: str = "",
                   save_user: bool = True) -> str:
    """v0.178 the never-silent promise: WHATEVER happens around the turn (a crash before the inner guard, a DB
    hiccup, a bug in place / persona / memory code), the user always gets a reply and the typing dots always go
    away. (Owner: 'some tasks never replied'.) The real work is in _run_turn; CancelledError still passes through.
    v0.191 `save_user=False` = the inbox re-run of a crashed turn: her message row already exists, never double it."""
    try:
        return await _run_turn(conversation_id, user_text, tenant_id, voice, context, actor, place, client_id,
                               save_user)
    except asyncio.CancelledError:
        raise
    except BaseException as e:   # noqa: BLE001 - the last line of defence: silence is worse than any error text
        log.exception("agent turn crashed outside its guard")
        _mark_failed(conversation_id)
        try:
            text = _friendly_error(e, tenant_id, actor or "owner", bool(VOICE_BRAIN_NOW.get()))
            bus.publish(conversation_id, "message", {"role": "assistant", "text": text, "source": "error"})
            _save(conversation_id, "assistant", [{"type": "text", "text": text}], display=text)
            bus.publish(conversation_id, "typing", {"on": False})
            return text
        except Exception:
            log.exception("even the crash reply failed")
            return ""


async def _run_turn(conversation_id: str, user_text: str, tenant_id: str | None = None, voice: bool = False,
                    context: str = "", actor: str = "owner", place: str = "", client_id: str = "",
                    save_user: bool = True) -> str:
    """Handle one user message end to end. Returns Santosh's final reply text.
    v0.173 `client_id` (the console's steering): a message she took back while queued returns at once — nothing
    runs, nothing is published (the take-back endpoint already hid the bubble)."""
    try:   # v0.714 HAR CHAT ALAG: a tool that tells her something during this turn speaks in THIS chat
        from .. import convs as _cv_turn
        _cv_turn.TURN.set(conversation_id)
    except Exception:   # noqa: BLE001
        pass
    if client_id and (conversation_id, client_id) in _held:
        _held.discard((conversation_id, client_id))
        return ""
    # _active_msg is claimed only when the turn actually holds the lock (below): a message still waiting behind
    # it stays take-back-able, which is the whole point of the receipt.
    settings = get_settings()
    tenant_id = tenant_id or settings.tenant_id
    ctx = Ctx(tenant_id=tenant_id, conversation_id=conversation_id, actor=actor or "owner")
    from .. import usage
    who = actor or "owner"
    # v0.193 the harness session log: every turn gets an id and everything it does logs under it
    _turn_id = new_id("turn")
    _t_turn0 = time.time()
    if VOICE_BRAIN_NOW.get():
        _m0 = time.monotonic()
        _PREP.set({"t0": _m0, "last": _m0, "marks": []})
        try:   # v0.639 PAKDO: name whatever blocks the event loop (logs only)
            from .. import looplag
            looplag.start()
        except Exception:
            pass
    _evlog.CURRENT.set({"turn_id": _turn_id, "actor": who})
    # v0.222 a background round of HER long job ("goal") is her own chat: never refused by the monthly background limit
    feature = ("call" if usage.current()[1] == "call" else "chat") if (who == "goal" or who.startswith(("owner", "approved:"))) else \
        ("routine" if who in ("routine", "wake") else "employee")   # v0.191 wake = routine lane (never the employee budget)
    usage.bind(tenant_id, feature)       # v0.98 what this turn's model calls cost, and for whom
    if not usage.allowed(tenant_id, feature):
        text = usage.blocked_text(tenant_id)
        _mark_failed(conversation_id)
        if _say_error(tenant_id, who, text):
            bus.publish(conversation_id, "message", {"role": "assistant", "text": text, "source": "budget"})
        return text
    _gender = persona(tenant_id)[1]
    # v0.75 ID numbers the OWNER writes go into her Pehchaan Locker; the model and the saved chat get references.
    # Customers' / other avatars' messages are never captured into her locker.
    if (actor or "owner") == "owner" and not user_text.lstrip().startswith("[Hoola Network]"):
        # v0.76 a website job is waiting for an OTP / CAPTCHA and she just said it: straight into the page box, never
        # into chat history, memory or the model (like telling the Setu operator the OTP)
        try:
            from ..operator import service as _ops
            got = await _ops.answer_from_chat(tenant_id, user_text)
        except Exception:
            log.exception("operator chat answer failed")
            got = None
        if got:
            shown = ("OTP " if got["kind"] == "otp" else "CAPTCHA ") + got.get("masked", "••••")
            _save_pre(conversation_id, "user", shown, display=shown)
            _save_pre(conversation_id, "assistant", [{"type": "text", "text": got["say"]}], display=got["say"])
            bus.publish(conversation_id, "message", {"role": "assistant", "text": got["say"], "source": "operator"})
            return got["say"]
        if not voice and save_user and not str(user_text or "").lstrip().startswith(("[", "(")):
            try:   # v0.472 R1 PLAN PEHLE: a big research ask shows its plan and waits for her Haan; her Haan starts it
                from . import research_plan as _rplan
                _rp = await _rplan.gate(tenant_id, conversation_id, user_text, settings)
            except Exception:
                log.exception("research plan gate failed")      # a broken gate never blocks her ask
                _rp = None
            if _rp and _rp["action"] == "say":
                _save_pre(conversation_id, "user", user_text, display=user_text)
                _save_pre(conversation_id, "assistant", [{"type": "text", "text": _rp["text"]}], display=_rp["text"])
                bus.publish(conversation_id, "message", {"role": "assistant", "text": _rp["text"], "source": "research_plan"})
                bus.publish(conversation_id, "typing", {"on": False})
                return _rp["text"]
            if _rp and _rp["action"] == "start":
                # her words are what the chat shows; the SAME turn gets the ask + the plan she approved (never saved twice)
                _save_pre(conversation_id, "user", _rp["words"], display=_rp["words"])
                user_text, save_user = _rp["text"], False
        try:   # v0.191 SAMAJHDAR CARD: PC/browser step uski haan ka intezaar hai aur usne LIKH diya ('haan karo',
               # 'approve hai', 'confirm'...) — card khud resolve, tap ki zaroorat nahi (paise wali card par hi).
               # Sirf POORA uttar hi manzoori ho tabhi ('haan, address yeh raha' ka baaki hissa brain dekhega).
            from .. import approval_words
            if getattr(settings, "chat_approval_words", False) and approval_words.is_pure_approval(user_text):
                from ..bazar import service as _bz
                _ap = await asyncio.to_thread(_bz.voice_approve, tenant_id, conversation_id, user_text, True, "chat")
            else:
                _ap = None
        except Exception:
            log.exception("approval by chat text failed")
            _ap = None
        if _ap:
            _save_pre(conversation_id, "user", user_text, display=user_text)
            _save_pre(conversation_id, "assistant", [{"type": "text", "text": _ap["say"]}], display=_ap["say"])
            bus.publish(conversation_id, "message", {"role": "assistant", "text": _ap["say"], "source": "approval"})
            bus.publish(conversation_id, "typing", {"on": False})
            return _ap["say"]
        try:
            from ..idvault import capture
            user_text, _ids = capture(tenant_id, user_text)
        except Exception:
            log.exception("id capture failed")
        try:   # v0.93 "mere PC pe" vs "apne browser mein": the place she named holds for this turn's tools
            from . import where
            # v0.270 only HER own words can name a place: a job note "(Result from HER PC ...)", a goal nudge that
            # lists a plan step "... Hoola ke PC pe ..." or a wake report used to count as her naming that PC, and
            # whichever note came last moved the next website step there - Hoola flip-flopped between the two PCs
            _hers = (getattr(ctx, "actor", "owner") or "owner") == "owner" and \
                not str(user_text or "").lstrip().startswith(("[", "("))
            ctx.place = place or where.remember(conversation_id, user_text if _hers else "")
        except Exception:
            log.exception("place check failed")
        try:   # v0.223 PHASE A: her "haan aage badho" after a used-up budget reopens the SAME job (fresh budget)
            from . import goal as _g
            if settings.agent_goal and _g.held_for_limit(conversation_id) and _g.wants_continue(user_text):
                _g.reopen(tenant_id, conversation_id)
            elif settings.agent_goal and _hers and str(user_text or "").strip():
                _g.resume_on_answer(tenant_id, conversation_id, user_text)   # wave 10: her answer to a job that asked her
        except Exception:
            log.exception("goal reopen failed")
    if who == "owner" and save_user and getattr(settings, "kaam_stop_words", True):
        # v0.649 SACH MEIN ROKO: her "roko / cancel karo / band karo" stops the work NOW - before this turn waits for the
        # conversation lock that the very job she is cancelling holds. Only what really stopped is said; nothing
        # running (or her words name something else) = the normal turn handles it (a draft, a booking...).
        try:
            from .. import kaamstop
            if kaamstop.wants_stop(user_text):
                _ks = await asyncio.to_thread(kaamstop.cancel, tenant_id, user_text, conversation_id)
                if _ks.get("stopped"):
                    _save_pre(conversation_id, "user", user_text, display=user_text)
                    _save_pre(conversation_id, "assistant", [{"type": "text", "text": _ks["say"]}], display=_ks["say"])
                    bus.publish(conversation_id, "message", {"role": "assistant", "text": _ks["say"], "source": "kaam_stop"})
                    bus.publish(conversation_id, "typing", {"on": False})
                    return _ks["say"]
        except Exception:
            log.exception("kaam stop by words failed")   # a broken stop never blocks her ask
    _mark("checks")
    lock = _locks[conversation_id]
    _steer_e = None
    if VOICE_BRAIN_NOW.get() and lock.locked():
        log.info("call brain turn waits: this chat is busy with another turn (%s)", conversation_id)
    # v0.667 only a turn that is HERS (her own ask / her long job) may answer or take her new words early: a wake
    # report or a routine holding the chat used to swallow them (steer.take has no actor check) and her own turn
    # returned "" and never ran - now she simply waits her turn behind it, like a queued message
    _holder = _HOLDER.get(conversation_id, "owner")
    if lock.locked() and (actor or "owner") == "owner" and not voice and not VOICE_BRAIN_NOW.get() \
            and _holder in ("owner", "goal"):
        # v0.657 a call's brain ask never takes the no-tools quick lane (it answered "kaam chal raha hai" without
        # tools); the call sends a second ask to its own side record instead (voice.Call._delegate)
        # v0.86 a long job holds the chat: answer this message NOW from the quick lane; only real work waits
        from . import quick
        steer_on = bool(getattr(settings, "agent_steer", True)) and not context
        got = await quick.answer(conversation_id, tenant_id, user_text, steering=steer_on)
        if got and not got["queued"]:
            return got["text"]
        if steer_on:   # v0.223 the instruction reaches the RUNNING job at its next step (agent.steer)
            from . import steer as _steer
            _steer_e = _steer.offer(conversation_id, user_text, client_id)
    async with _holding(lock, conversation_id):
        if _steer_e is not None:
            from . import steer as _steer
            if _steer.claim(conversation_id, _steer_e):
                return ""                   # the running job already took her words and acted on them
        if client_id and (conversation_id, client_id) in _held:   # taken back while it waited behind this lock
            _held.discard((conversation_id, client_id))
            return ""
        if client_id:
            _active_msg[conversation_id] = client_id   # v0.173 this message's turn runs now (take-back refuses it)
        _HOLDER[conversation_id] = (actor or "owner") if not str(actor or "").startswith("approved:") else "owner"
        _mark("lock")
        _t_lock = time.time()
        notes = _pending_worker_notes(conversation_id)
        from . import quick as _quick
        notes += _quick.take_notes(conversation_id)
        agent_text = f"{VOICE_NOTE}\n{user_text}" if voice else user_text
        if context:                         # e.g. files the owner attached (only the words show in the chat)
            agent_text += "\n\n" + context
        if ctx.place:                       # v0.93 the place she named, said plainly to the model
            from . import where
            agent_text += "\n\n" + where.note(ctx.place, conversation_id)
        if notes:
            agent_text = "\n".join(f"[Santosh worker update] {n}" for n in notes) + "\n\n" + agent_text
        try:   # v0.242 FULL CLAUDE MODE Phase 2: a chat near its window is compacted BEFORE this turn (Claude's way)
            from . import compact as _compact
            if VOICE_BRAIN_NOW.get():
                # v0.636 a call brain turn reads only the last few exchanges (voice_brain_history), so it never needs
                # the whole chat compacted first - that is a full-chat model call while she waits; the next chat turn does it
                STATS_PREP["compact_skipped"] += 1
            else:
                await _compact.before_turn(conversation_id, tenant_id, settings)
        except Exception:
            log.exception("compact before turn failed")
        _mark("compact")
        saved_wake = False
        if save_user:
            # v0.473 a goal's background round is not her words: kept in history, but never shown as her message
            _save(conversation_id, "user", agent_text,
                  display=None if (who in ("routine", "goal") and user_text.startswith("[Goal jaari")) else user_text)
        elif who == "wake" and agent_text.strip():
            # v0.473 a finished job's RESULT is saved into the chat history (display None = never shown as her words,
            # never in her focus words). Before, only Hoola's reply about it was kept: from the next turn on the real
            # result - ids, links, what failed - was gone.
            _save(conversation_id, "user", agent_text, display=None)
            saved_wake = True
            STATS_LONG["wake_saved"] += 1
        bus.publish(conversation_id, "typing", {"on": True})
        if (actor or "owner") == "owner" and not voice:   # v0.187 the first words come fast (see _ack_later)
            _ACKED.add(conversation_id)
            _bg(_ack_later(conversation_id, _gender))
        _evlog.log_event(tenant_id, conversation_id, "turn_started", {"line": str(user_text or "")[:160],
                                                                       "voice": bool(voice)},
                         turn_id=_turn_id, actor=who)
        try:   # v0.473 HOOLA CODER: her ask itself is memory (redacted at the boundary; a <private>
               # turn stores nothing but its privacy marker)
            from .. import coder as _coder
            await asyncio.to_thread(_coder.turn_prompt, tenant_id, conversation_id, user_text or "")
        except Exception:
            pass
        try:   # v0.477 HOOLA NUDGE: a live turn began - any background reflection fork thinking
               # about this conversation drops its writes (it never makes the live turn wait)
            from .. import coder as _coder
            _coder.nudge.poke(conversation_id)
        except Exception:
            pass

        _mark("save")
        try:   # v0.657 PAKKA KAAM: the inbox row learns THIS turn really began (the restart sweep's anchor)
            from .. import turn_inbox as _ti
            await asyncio.to_thread(_ti.started, conversation_id)
        except Exception:
            log.debug("inbox started stamp failed", exc_info=True)
        # v0.668 read in a thread: up to 5,000 rows decoded on the event loop froze the WHOLE server (live call audio,
        # every SSE stream) for a moment on every turn of a long chat
        history = await asyncio.to_thread(_load_history, conversation_id)
        _mark("history")
        if not save_user and not saved_wake and agent_text.strip():
            # v0.213 wake / inbox re-run turns: this turn's words were deliberately NOT saved (save_user=False,
            # kaam_followup._wake_turn / turn_inbox re-runs), so the array below used to end with the PREVIOUS
            # turn's assistant reply - the production model refuses assistant-final arrays (400 'assistant
            # message prefill' on EVERY wake turn of every long job) and never saw this turn's words at all.
            # In-memory only: nothing is double-saved, the next turn still loads the DB fresh.
            history.append({"role": "user", "content": agent_text})
        block = ""
        if who == "owner" or who in ("routine", "wake", "goal") or who.startswith("approved:"):
            if VOICE_BRAIN_NOW.get():
                # v0.638 a call's brain turn: diary / job state / coder memory read TOGETHER under one short wait
                # (read one after another they cost 7.0 s on her 16:36 call); a slow one is left out of this ask only
                block = await _brain_memory(tenant_id, conversation_id, user_text, settings)
            else:
              try:   # v0.108 work diary, facts by meaning, recalled old exchanges: for this message only
                # v0.704 the parts are read TOGETHER (one after another they added up on every chat turn, the shape
                # v0.638 removed from calls) under one bounded wait; a part not ready is left out of THIS turn only.
                # The card news rides with them: her taps (Send / Approve / Cancel) since the last reply.
                block = await _chat_memory(tenant_id, conversation_id, user_text, settings)
                # v0.648: her recent calls reach a chat turn through the diary's "Pichhli calls" section (call records are
                # in the same memory scope) - the separate v0.646 recent-calls block said the same thing twice
                if settings.agent_goal:   # v0.187 an open goal rides above everything: this turn continues it
                    from . import goal as _goalb
                    gb = _goalb.goal_block(conversation_id)
                    if gb:
                        block = (gb + "\n\n" + block) if block else gb
                    elif (who == "owner" and getattr(settings, "agent_plan_early", True)
                          and _goalb.looks_big(user_text)):
                        # v0.228 a clearly big ask: the plan comes FIRST, before any work (Claude's todo list)
                        STATS_LONG["plan_first"] += 1
                        block = (_goalb.PLAN_FIRST + "\n\n" + block) if block else _goalb.PLAN_FIRST
              except Exception:
                log.exception("memory block failed")
            _now_line = _now_note(tenant_id)   # wave 9: the exact time rides HERE (volatile), never in the cached system prompt
            block = (_now_line + "\n\n" + block) if block else _now_line
            if block:
                _with_memory(history, block)
        _mark("memory")
        final_text = ""
        if _STOP_AT.get(conversation_id, 0.0) >= _t_lock and (actor or "owner") == "owner":
            # v0.662 she tapped Stop while this turn was preparing (saving, compaction, memory read): the discard below
            # used to wipe it and the whole turn ran anyway. Nothing has run yet - say so and end the turn.
            _stopped.discard(conversation_id)
            bus.publish(conversation_id, "message", {"role": "assistant", "text": STOPPED_IN_PREP, "source": "stop"})
            _save(conversation_id, "assistant", [{"type": "text", "text": STOPPED_IN_PREP}], display=STOPPED_IN_PREP)
            bus.publish(conversation_id, "typing", {"on": False})
            return STOPPED_IN_PREP
        _stopped.discard(conversation_id)
        _h0 = len(history)
        from .. import livereply
        # v0.191 a wake turn never streams into an already-open channel (a live call owns its own reply stream);
        # it publishes whole messages like every non-streaming path.
        live = livereply.begin(conversation_id, tenant_id)
        if who == "wake":
            live = None
            _NO_STREAM.add(conversation_id)
        try:
            # one stuck call must never keep this conversation locked forever (v0.187: an open goal gets the longer cap)
            from . import goal as _goalt
            goal_on = settings.agent_goal and _goalt.active_for(conversation_id) is not None
            _LONG_TURN.discard(conversation_id)
            final_text = await _with_deadline(
                _steps(conversation_id, ctx, _gender, history, settings, tenant_id, user_text), conversation_id,
                max(30, settings.agent_goal_turn_s if goal_on else settings.agent_turn_timeout_s),
                max(30, settings.agent_goal_turn_s) if settings.agent_goal else 0)
        except asyncio.TimeoutError:
            log.error("agent turn timed out after %ss", settings.agent_turn_timeout_s)
            _mark_failed(conversation_id)
            # v0.657 PAKKA KAAM: the deadline cancels the turn MID-TOOL, so a step may be half done (some mails gone,
            # some not). Never invite a blind resend; a background goal round says the next round carries on.
            final_text = TIMEOUT_GOAL if (goal_on and who == "goal") else gendered(TIMEOUT_TEXT, _gender)
            await asyncio.to_thread(_record_cut, tenant_id, conversation_id, user_text, "time limit par roka gaya", _t_turn0)
            _evlog.log_event(tenant_id, conversation_id, "turn_failed", {"line": f"turn timeout ({settings.agent_turn_timeout_s}s)"},
                             turn_id=_turn_id, actor=who)
            if live is not None:
                live.reset()
            if _say_error(tenant_id, who, final_text):
                bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "error",
                                                         **_tag(live, True)})
                _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
        except Exception as e:
            log.exception("agent turn failed")
            _mark_failed(conversation_id)
            final_text = _friendly_error(e, tenant_id, who, bool(VOICE_BRAIN_NOW.get()))
            _ran = _tools_since(history, _h0)
            if _ran:    # wave 13: steps already ran (a mail may be gone) - never invite a blind repeat
                final_text = final_text + AFTER_TOOLS
            await asyncio.to_thread(_record_cut, tenant_id, conversation_id, user_text, f"galti: {str(e)[:120]}", _t_turn0)
            _evlog.log_event(tenant_id, conversation_id, "turn_failed", {"line": str(e)[:200]},
                             turn_id=_turn_id, actor=who)
            if live is not None:
                live.reset()
            if _say_error(tenant_id, who, final_text):
                bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "error",
                                                         **_tag(live, True)})
                _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
        finally:
            _ACKED.discard(conversation_id)   # v0.187 no ack after this turn for any reason
            try:   # v0.315 EK HI FILE: a document draft held for a fix that nobody replaced reaches her now
                from .docstudio_tools import flush_held
                flush_held(conversation_id)
            except Exception:
                log.exception("held draft flush failed")
            _NO_STREAM.discard(conversation_id)   # v0.191 wake over: the chat streams normally again
            if live is not None:
                live.stopped = live.stopped or conversation_id in _stopped
                live.end()
            bus.publish(conversation_id, "typing", {"on": False})
            _evlog.log_event(tenant_id, conversation_id, "turn_finished",
                             {"line": str(final_text or "")[:160], "seconds": round(time.time() - _t_turn0, 1)},
                             turn_id=_turn_id, actor=who)
        if who in ("owner", "routine", "goal") or who.startswith("approved:"):
            try:   # v0.108 index this exchange, fold old ones into the summary, pick lasting facts (background)
                from .. import yaad   # a goal round's "[Goal jaari...]" text is never her words: no facts from it
                yaad.after_turn(tenant_id, conversation_id, user_text, final_text,
                                "owner" if who == "owner" else ("routine" if who == "goal" else who))
                if who == "owner":   # v0.612 YAAD SE: which memory this reply leaned on, each forgettable
                    yaad.publish_used(conversation_id, final_text)
                else:
                    yaad.USED.pop(conversation_id, None)
            except Exception:
                log.exception("memory after turn failed")
            try:   # v0.477 HOOLA NUDGE: the turn counter - at coder_nudge_every turns ONE quiet
                   # reflection writes memories + skills in the background (never this turn's path)
                from .. import coder as _coder
                _coder.nudge.count_turn(tenant_id, conversation_id)
            except Exception:
                log.exception("coder nudge count failed")
        if who == "owner":
            from .. import chats
            if chats.enabled():   # v0.162 the chat gets a short title after her first exchange (background)
                _bg(chats.auto_title(tenant_id, conversation_id))
            try:   # v0.191 her own words reset the wake budget: a fresh ask earns fresh wake-ups
                from .. import kaam_followup
                kaam_followup.wake_reset(conversation_id)
            except Exception:
                log.debug("wake reset failed", exc_info=True)
        if settings.agent_goal and who != "wake":   # v0.187 the turn ended but the goal is still open: ONE background continuation (a wake never chains into it)
            try:
                from . import goal as _goalc
                _goalc.maybe_continue(conversation_id, tenant_id, who)
            except Exception:
                log.exception("goal continuation scheduling failed")
        return final_text


_BG: set = set()


def _bg(coro) -> None:
    """A small background job that must not be garbage-collected before it finishes."""
    t = asyncio.ensure_future(coro)
    _BG.add(t)
    t.add_done_callback(_BG.discard)
