"""v0.224 The runner: the same 24 asks, measured the same way, written to a file that can be compared with the file
from before the change.

Two cards, because they can honestly measure two different things:

- `pipeline_card()` needs NO model and NO keys: per ask it reads what the turn would SEND - the system guide's size
  and how many tools are offered (v0.191 admission + v0.221 slim guide) - and that the rulebook really rides in the
  prompt. CI can run this on every change, so Phase 2's win can never quietly come undone.
- `reply_card()` runs the REAL turns on a dedicated tenant (never her chats, never her AI budget) and measures what
  she would actually get: time to the first word, the whole reply's time, its length and shape, and every rule the
  scorer can hold it to. Optionally one cheap-brain judge call per ask for "did it answer what she asked".

CLI:  python -m app.quality                  # the pipeline card (free, no keys)
      python -m app.quality --live           # the real replies too (costs model calls)
      python -m app.quality --live --judge   # plus the judge's 0-5 per ask
      python -m app.quality compare a.json b.json
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from . import score as S
from .asks import ASKS, SET_V, turns_of

log = logging.getLogger("santosh.quality")
TENANT = "__quality__"
PINS = ("How you understand her", "How you answer", "Answer first", "Length follows the question")


def _dir() -> Path:
    p = Path(os.getenv("QUALITY_DIR") or "./data/quality")
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------- the free card: what the turn would send

def pipeline_card(asks: list[dict] | None = None) -> dict:
    """No model, no keys, no DB: the prompt and tool surface of every ask."""
    from ..agent import admit, prompts
    from ..config import get_settings
    st = get_settings()
    full_kb = round(len(prompts.SYSTEM) / 1024, 1)
    rows, missing = [], set()
    for a in (asks or ASKS):
        last = turns_of(a)[-1]
        plan = admit.plan_for(last, st)
        text = prompts.system_text(plan.families if st.prompt_slim else None)
        for p in PINS:
            if p not in text:
                missing.add(p)
        rows.append({"id": a["id"], "kind": a["kind"], "prompt_kb": round(len(text) / 1024, 1),
                     "tools": plan.size(), "families": sorted(plan.families or [])[:12]})
    kb = sorted(r["prompt_kb"] for r in rows)
    tl = sorted(r["tools"] for r in rows)
    from ..agent.tools import TOOLS
    return {"rows": rows, "full_guide_kb": full_kb, "tools_all": len(TOOLS), "rules_present": not missing,
            "rules_missing": sorted(missing),
            "prompt_kb_median": kb[len(kb) // 2] if kb else None, "prompt_kb_max": kb[-1] if kb else None,
            "tools_median": tl[len(tl) // 2] if tl else None, "tools_max": tl[-1] if tl else None,
            "slim": bool(st.prompt_slim)}


# ---------------------------------------------------------------- the real card: what she would get

class _Watch:
    """Counts the model calls of one turn and remembers what was really sent to it."""

    def __init__(self) -> None:
        self.calls = 0
        self.prompt_kb: float | None = None
        self.tools: int | None = None
        self._orig = None

    def __enter__(self):
        from ..agent import santosh
        self._orig = santosh._think

        async def wrapped(brain, system, history, settings, tools=None, live=None, max_tokens=None):
            self.calls += 1
            if self.prompt_kb is None:
                txt = system if isinstance(system, str) else "".join(
                    b.get("text", "") for b in (system or []) if isinstance(b, dict))
                self.prompt_kb = round(len(txt) / 1024, 1)
                self.tools = len(tools or [])
            return await self._orig(brain, system, history, settings, tools, live, max_tokens)

        santosh._think = wrapped
        return self

    def __exit__(self, *a):
        from ..agent import santosh
        santosh._think = self._orig
        return False


def _new_conv(tenant: str) -> str:
    from ..db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


def _calls_of(conv: str) -> list[dict]:
    """What really ran, read back from the turn's own step events (tool + ok)."""
    from sqlalchemy import select

    from ..db import Event, session
    out: dict[str, dict] = {}
    with session() as s:
        for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "step")
                           .order_by(Event.id)).all():
            p = e.payload or {}
            if p.get("state") in ("done", "error"):
                out[str(p.get("id") or len(out))] = {"tool": p.get("tool"), "ok": p.get("state") == "done",
                                                     "result": "", "args": ""}
    return list(out.values())


async def _one_ask(ask: dict, tenant: str, judge: bool) -> dict:
    from ..agent import santosh
    from ..config import get_settings
    from ..events import bus
    turns = turns_of(ask)
    conv = _new_conv(tenant)
    for t in turns[:-1]:                                  # the set-up turns of a two-turn ask
        await santosh.run_turn(conv, t, tenant_id=tenant)
    q = bus.subscribe(conv)
    t0 = time.time()
    first: float | None = None
    try:            # the queue is given back whatever happens: a leaked subscriber is a leak for good (v0.208.1)
        with _Watch() as w:
            task = asyncio.ensure_future(santosh.run_turn(conv, turns[-1], tenant_id=tenant))
            while not task.done():
                try:
                    ev = await asyncio.wait_for(q.get(), 0.25)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
                if first is None and (ev.get("kind") == "delta" or
                                      (ev.get("kind") == "message"
                                       and (ev.get("payload") or {}).get("role") == "assistant")):
                    first = time.time()
            reply = await task
    finally:
        bus.unsubscribe(conv, q)
    total = time.time() - t0
    calls = _calls_of(conv)
    meta = {"ttfw_ms": round((first - t0) * 1000) if first else None, "total_ms": round(total * 1000),
            "steps": len(calls), "model_calls": w.calls, "prompt_kb": w.prompt_kb, "tools": w.tools, "calls": calls}
    card = S.score_one(ask, reply, meta)
    card["conv"] = conv
    if judge:
        card["judge"] = await _judge(ask, reply, get_settings())
    return card


JUDGE_SYSTEM = """You grade ONE reply of an Indian AI coworker (it talks Hinglish). You get the user's ask and the reply.
Answer ONLY with JSON: {"answered": 0-5, "useful": 0-5, "why": "<one short line>"}
- answered: did it answer what was actually asked? 5 = every part answered, 0 = it answered something else.
- useful: would a sharp, busy Indian shop owner be glad to get this? 5 = yes, straight to the point, honest about what
  it does not know; 0 = padded, vague or made-up.
- Judge the CONTENT and the FIT only. Never mark down Hinglish, a short answer that is complete, or a refusal that is
  honest. Never reward length. A made-up figure, price or date is a 0 on useful."""


async def _judge(ask: dict, reply: str, settings) -> dict | None:
    import re

    from ..agent import pakka
    msg = "Ask:\n" + "\n".join(turns_of(ask)) + f"\n\nReply:\n{str(reply)[:1600]}"
    try:
        raw = await asyncio.wait_for(pakka._ask(JUDGE_SYSTEM, msg, settings), 30)
        m = re.search(r"\{.*\}", raw or "", re.S)
        v = json.loads(m.group(0)) if m else {}
        return {"answered": int(v.get("answered", 0)), "useful": int(v.get("useful", 0)),
                "why": str(v.get("why") or "")[:160]}
    except Exception as e:
        log.info("judge skipped: %s", e)
        return None


async def reply_card(asks: list[dict] | None = None, tenant: str = TENANT, judge: bool = False) -> dict:
    cards = []
    for a in (asks or ASKS):
        try:
            cards.append(await _one_ask(a, tenant, judge))
        except Exception as e:                            # one broken ask never loses the rest of the run
            log.exception("quality ask %s failed", a["id"])
            cards.append({"id": a["id"], "kind": a["kind"], "error": str(e)[:200], "points": 0, "flags": ["error"],
                          "words": 0, "fit": "short", "script": "none", "fmt": {}, "reply": ""})
    out = {"cards": cards, **S.totals([c for c in cards if "error" not in c])}
    js = [c["judge"] for c in cards if c.get("judge")]
    if js:
        out["judge_answered"] = round(sum(j["answered"] for j in js) / len(js), 2)
        out["judge_useful"] = round(sum(j["useful"] for j in js) / len(js), 2)
    return out


# ---------------------------------------------------------------- snapshots and the before / after line

async def snapshot(live: bool = False, judge: bool = False, label: str = "") -> dict:
    from ..main import APP_VERSION
    snap = {"set": SET_V, "version": APP_VERSION, "label": label,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pipeline": pipeline_card()}
    if live:
        snap["replies"] = await reply_card(judge=judge)
    stamp = snap["at"].replace(":", "").replace("-", "") + ("-live" if live else "")
    path = _dir() / f"{stamp}.json"
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    snap["file"] = str(path)
    return snap


def snapshots() -> list[dict]:
    out = []
    for p in sorted(_dir().glob("*.json"), reverse=True):
        try:
            v = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append({"file": p.name, "at": v.get("at"), "version": v.get("version"), "set": v.get("set"),
                    "label": v.get("label", ""), "live": "replies" in v,
                    "points": (v.get("replies") or {}).get("points"),
                    "prompt_kb_median": (v.get("pipeline") or {}).get("prompt_kb_median")})
    return out


def load(name: str) -> dict:
    p = _dir() / Path(name).name
    return json.loads(p.read_text(encoding="utf-8"))


LOWER_IS_BETTER = {"prompt_kb_median", "prompt_kb_max", "tools_median", "tools_max", "ttfw_median_ms",
                   "ttfw_p90_ms", "total_median_ms"}


def compare(before: dict, after: dict) -> dict:
    """The before / after line: every number that moved, and whether moving that way is better or worse."""
    rows = []

    def add(name: str, a, b):
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return
        d = round(b - a, 2)
        if d == 0:
            verdict = "same"
        else:
            good = (d < 0) if name in LOWER_IS_BETTER else (d > 0)
            verdict = "behtar" if good else "bura"
        rows.append({"metric": name, "before": a, "after": b, "delta": d, "verdict": verdict})

    pa, pb = before.get("pipeline") or {}, after.get("pipeline") or {}
    for k in ("prompt_kb_median", "prompt_kb_max", "tools_median", "tools_max"):
        add(k, pa.get(k), pb.get(k))
    ra, rb = before.get("replies") or {}, after.get("replies") or {}
    for k in ("points", "clean", "words_median", "ttfw_median_ms", "ttfw_p90_ms", "total_median_ms",
              "judge_answered", "judge_useful"):
        add(k, ra.get(k), rb.get(k))
    fa, fb = ra.get("flags") or {}, rb.get("flags") or {}
    flags = []
    for k in sorted(set(fa) | set(fb)):
        a, b = int(fa.get(k, 0)), int(fb.get(k, 0))
        if a != b:
            flags.append({"flag": k, "before": a, "after": b,
                          "verdict": "behtar" if b < a else "bura"})
    worse = [r["metric"] for r in rows if r["verdict"] == "bura"] + [f["flag"] for f in flags if f["verdict"] == "bura"]
    return {"before": {"version": before.get("version"), "at": before.get("at")},
            "after": {"version": after.get("version"), "at": after.get("at")},
            "same_set": before.get("set") == after.get("set"), "rows": rows, "flags": flags,
            "worse": worse, "say": _say(rows, flags, worse, before.get("set") == after.get("set"))}


def _say(rows, flags, worse, same_set: bool) -> str:
    if not same_set:
        return "Sawaal ka set badal gaya hai - dono run ek jaise nahi hain, pehle set dobara chalaiye."
    if not rows and not flags:
        return "Kuch nahi badla."
    good = [r["metric"] for r in rows if r["verdict"] == "behtar"] + [f["flag"] for f in flags if f["verdict"] == "behtar"]
    bits = []
    if good:
        bits.append("Behtar: " + ", ".join(good[:6]))
    if worse:
        bits.append("Bura: " + ", ".join(worse[:6]))
    return " · ".join(bits) if bits else "Sab waise hi hai."


def lines(snap: dict) -> list[str]:
    """The scorecard in her words, for the terminal and the app."""
    p, r = snap.get("pipeline") or {}, snap.get("replies") or {}
    out = [f"Scorecard (set {snap.get('set')}, {snap.get('version')}, {snap.get('at')})",
           f"  Prompt: {p.get('prompt_kb_median')} KB (poora guide {p.get('full_guide_kb')} KB), "
           f"tools {p.get('tools_median')} of {p.get('tools_all')} (max {p.get('tools_max')})",
           f"  Rulebook prompt mein: {'haan' if p.get('rules_present') else 'NAHI - ' + ', '.join(p.get('rules_missing') or [])}"]
    if r:
        out += [f"  Score: {r.get('points')}/100, saaf jawab {r.get('clean')}/{r.get('asks')}",
                f"  Pehla shabd: {r.get('ttfw_median_ms')} ms (p90 {r.get('ttfw_p90_ms')} ms), "
                f"poora {r.get('total_median_ms')} ms, lambai {r.get('words_median')} shabd"]
        if r.get("flags"):
            out.append("  Galtiyan: " + ", ".join(f"{k} x{v}" for k, v in sorted(r["flags"].items())))
        if r.get("judge_answered") is not None:
            out.append(f"  Judge: jawab {r['judge_answered']}/5, kaam ka {r['judge_useful']}/5")
    return out
