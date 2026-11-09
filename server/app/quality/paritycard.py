"""v0.732 CLAUDE PARITY Phase 0 - the Claude Parity Card (docs/CLAUDE_PARITY_PLAN.md Part 3, Phase 0).

Every later parity phase is judged by this card. 60 multi-turn conversations (parity_convs.py) are replayed through the
REAL `santosh.run_turn` on the isolated tenant "__paritycard__" (never her chats, never her budget) against WHATEVER
brain the server is configured with (owner decision: GLM 5.3 Flash via agent/llm.py stays the primary model) - and the
card records which brain / model answered EVERY step.

Scores per conversation, in code (score_conv - a pure function of the conversation + its transcript):
  answered        every turn has a real reply (not empty, not the error line) that meets its must / ask / cannot
  followed        the follow-up turns kept the thread (previous item / shorter / language / previous reply / not lost)
  right_tool      the first real tool of a tool turn is in the expected family; a talk turn ran no doing tool
  no_invented_done  no "done" claim without a tool of that kind that really did it (agent/draftcheck's own reading)
  no_unasked_text   no text she did not ask for: the "(Kaam:" ledger, the honesty notes ("(To be clear:" ...)
  one_brain       every step of the conversation was answered by ONE brain / model (Phase 1's promise)
  measured only:  time to first word (median of the turns), total time, rupees (usage.run_meter x usd_inr), steps,
                  the brains / models per step.
Optional --judge: one cheap-brain call per conversation (0-5 answered, 0-5 followed); a judge failure is no score.

Modes:  --check  free, no model: the set is valid (60, the category counts, every expectation a known key / family)
                 AND the scorer is CALIBRATED on planted transcripts (an honest one must pass; each planted fault must
                 fail for exactly its own reason) AND the expected tool families are in view (admit) for each first ask.
        --live   real turns (model calls + minutes + rupees).
CLI: python -m app.quality parity [--check|--live] [--judge] [--only id,id] [--limit N] [--cat c] [--label x]
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from .parity_convs import CATEGORIES, CONVS, PARITY_SET_V

log = logging.getLogger("santosh.quality.parity")

RUBRIC_V = 1
TENANT = "__paritycard__"
TURN_TIMEOUT_S = 600
DIMS = ("answered", "followed", "right_tool", "no_invented_done", "no_unasked_text", "one_brain")

FAMILIES: dict[str, str] = {
    "mail": r"^email_|gmail|outlook",
    "calendar": r"^calendar_|add_calendar_event",
    "web": r"google_search|web_sources|open_website|browse_web|^reach$|duniya|^scrape|parallel_search|research_run"
           r"|mospi|indiamart|jharokha|youtube_search",
    "research": r"research_run|research_status|google_search|web_sources|open_website|^reach$|duniya|^scrape"
                r"|parallel_search|deploy_agents|crew_run|mospi",
    "make": r"artifact_make|doc_studio|pylab|doc_create|^sheet_create|^sheet_|website|create_studio|hoola_frames"
            r"|pdf_tools|slides_create|data_fetch|doc_desk",
    "calc": r"^pylab$",
    "file": r"^drive_|file_read|data_read|sheet_read|doc_preview|pdf_tools|sheets_find",
    "memory": r"yaad_khojo|memory_search|haal_ki_chats|kgmemory|chat_search|session_log",
    "reminder": r"create_reminder",
    "plan": r"kaam_plan|deploy_agents|crew_run|agent_army|officehours",
}
NEUTRAL = re.compile(r"^(tool_search|skill_manage|jaanch|think)$")
EXPECT_KEYS = {"tool", "no_tool", "ask", "cannot", "must", "must_not", "refers_prev", "refers_item", "shorter", "lang",
               "stopped"}
FOLLOW_KEYS = ("refers_prev", "refers_item", "shorter", "lang", "stopped")
UNASKED = ("(Kaam:",)
_CANNOT = re.compile(r"\b(can'?t|cannot|can not|unable|not possible|isn'?t possible|impossible|won'?t be able|no way to"
                     r"|not able to|physically|i don'?t have (?:a )?(?:body|hands)|already (?:left|departed|gone))\b", re.I)
_STOP = re.compile(r"\b(stop|stopped|stopping|cancel|cancell?ed|halt|nothing (?:is )?running|no(?:thing)? running|won'?t continue"
                   r"|not continu)", re.I)
_DEVA = re.compile(r"[ऀ-ॿ]")
_HI_WORDS = re.compile(r"\b(hai|hain|nahi|aur|ke|ki|ka|ko|mein|se|karna|chahiye|kyunki|rakhna|paisa)\b", re.I)
_MR_WORDS = re.compile(r"(आहे|करा|तुम्ही|मला|काय|साठी|आणि|नाही)")
_STOPWORDS = set("the and for with that this from your you are have will can what when which into about then them they "
                 "their there here been also more most some such only just than very each other make made like over "
                 "would could should does done being because these those while where".split())


def _unasked_marks() -> tuple[str, ...]:
    try:
        from ..agent import draftcheck
        return tuple(UNASKED) + tuple(draftcheck.NOTE_MARKS)
    except Exception:
        return tuple(UNASKED)


# ---------------------------------------------------------------- the set

def check_set(convs: list[dict] | None = None) -> list[str]:
    """Every problem with the data, as plain lines ([] = the set is valid)."""
    convs = CONVS if convs is None else convs
    bad: list[str] = []
    if convs is CONVS and len(CONVS) != 60:
        bad.append(f"{len(CONVS)} conversations, the card needs 60")
    counts: dict[str, int] = {}
    seen: set[str] = set()
    for c in convs:
        cid = c.get("id", "?")
        if cid in seen:
            bad.append(f"{cid}: duplicate id")
        seen.add(cid)
        counts[c.get("cat", "?")] = counts.get(c.get("cat", "?"), 0) + 1
        if c.get("cat") not in CATEGORIES:
            bad.append(f"{cid}: unknown category {c.get('cat')}")
        turns = c.get("turns") or []
        if not turns:
            bad.append(f"{cid}: no turns")
        if c.get("cat") in ("followup", "make") and len(turns) < 2:
            bad.append(f"{cid}: a {c['cat']} conversation needs a follow-up turn")
        if c.get("cat") == "memory" and not c.get("setup"):
            bad.append(f"{cid}: a memory conversation needs an earlier chat (setup)")
        for i, t in enumerate(turns):
            if not str(t.get("text") or "").strip():
                bad.append(f"{cid} turn {i + 1}: empty text")
            extra = set(t) - EXPECT_KEYS - {"text"}
            if extra:
                bad.append(f"{cid} turn {i + 1}: unknown expectation {sorted(extra)}")
            for f in _fams(t.get("tool")):
                if f not in FAMILIES:
                    bad.append(f"{cid} turn {i + 1}: unknown tool family {f}")
            if t.get("tool") and t.get("no_tool"):
                bad.append(f"{cid} turn {i + 1}: tool and no_tool together")
            if i == 0 and any(k in t for k in FOLLOW_KEYS if k != "lang"):
                bad.append(f"{cid} turn 1: a follow-up check on the first turn")
            if t.get("lang") not in (None, "hi", "mr"):
                bad.append(f"{cid} turn {i + 1}: lang must be hi or mr")
            for g in t.get("must") or []:
                if not isinstance(g, list) or not g:
                    bad.append(f"{cid} turn {i + 1}: a must group must be a non-empty list")
    if convs is CONVS:
        for cat, n in CATEGORIES.items():
            if counts.get(cat, 0) != n:
                bad.append(f"category {cat}: {counts.get(cat, 0)} conversations, the plan says {n}")
    return bad


def _fams(v) -> list[str]:
    if not v:
        return []
    return [v] if isinstance(v, str) else list(v)


def pick(only: str = "", limit: int = 0, cat: str = "") -> list[dict]:
    items = [c for c in CONVS if not cat or c["cat"] == cat]
    if only:
        want = {x.strip() for x in only.split(",") if x.strip()}
        items = [c for c in items if c["id"] in want]
    return items[:limit] if limit else items


# ---------------------------------------------------------------- reading a reply

def _words(text: str) -> list[str]:
    return re.findall(r"[\wऀ-ॿ']+", str(text or ""))


def _content(text: str) -> set[str]:
    return {w.lower() for w in _words(text) if len(w) >= 5 and w.lower() not in _STOPWORDS and not w.isdigit()}


def list_items(text: str) -> list[str]:
    """The numbered / bulleted items of a reply, in order."""
    out = []
    for line in str(text or "").splitlines():
        m = re.match(r"\s*(?:\d+[.)]|[-*•]|#+\s*\d+[.)]?)\s+(.*\S)", line)
        if m:
            out.append(re.sub(r"[*_`#]", "", m.group(1)).strip())
    return out


def _item_named(prev: str, n: int, reply: str) -> bool:
    items = list_items(prev)
    if len(items) < n:
        return False
    head = re.split(r"\s[-–—:]\s|:", items[n - 1])[0]
    want = _content(head) or _content(items[n - 1])
    got = {w.lower() for w in _words(reply)}
    if not want:
        return items[n - 1].lower() in str(reply).lower()
    return bool(want & got)


def _lang_ok(lang: str, text: str) -> bool:
    if lang == "hi":
        return bool(_DEVA.search(text or "")) or len(_HI_WORDS.findall(text or "")) >= 4
    if lang == "mr":
        return bool(_MR_WORDS.search(text or ""))
    return True


def first_tool(calls: list[dict]) -> str:
    for c in calls or []:
        n = str(c.get("tool") or "")
        if n and not NEUTRAL.match(n):
            return n
    return ""


def in_family(name: str, fams: list[str]) -> bool:
    return any(re.search(FAMILIES[f], name or "") for f in fams if f in FAMILIES)


def _effect(c: dict) -> str:
    try:
        from ..agent import draftcheck
        return draftcheck.effect(c)
    except Exception:
        return "did" if c.get("ok") else ""


def _doing(calls: list[dict]) -> list[str]:
    return [str(c.get("tool")) for c in calls or [] if _effect(c) in ("did", "card") and not NEUTRAL.match(str(c.get("tool")))]


def invented_done(reply: str, calls: list[dict]) -> list[str]:
    """The claims of finished work with no tool of that kind behind them (draftcheck's own reading, run on the card)."""
    from ..agent import draftcheck as D
    if D._ALREADY_HONEST.search(reply or ""):
        return []
    bad = []
    for phrase, window, _clause in D.all_claims(reply or ""):
        _fam, tools = D.family_of(phrase, window)
        if not any(_effect(c) == "did" and D._backs_claim(c, tools) for c in calls or []):
            bad.append(phrase)
    return bad


def score_turn(turn: dict, tr: dict, prev_reply: str) -> dict:
    """One turn: which checks applied and which failed (names), from the transcript row only."""
    reply = str(tr.get("reply") or "")
    calls = tr.get("tools") or []
    shown = "\n".join(tr.get("shown") or [reply])
    fails: dict[str, list[str]] = {d: [] for d in DIMS}
    applies = {"answered": True, "followed": False, "right_tool": False, "no_invented_done": True,
               "no_unasked_text": True}
    low = reply.lower()
    # answered
    if tr.get("error") or not reply.strip():
        fails["answered"].append("no answer" + (f": {tr.get('error')}" if tr.get("error") else ""))
    for g in turn.get("must") or []:
        if not any(w.lower() in low for w in g):
            fails["answered"].append("missing " + " / ".join(g[:3]))
    for p in turn.get("must_not") or []:
        if p.lower() in low:
            (fails["followed"] if p in _lost_words() else fails["answered"]).append(f"said '{p}'")
            if p in _lost_words():
                applies["followed"] = True
    if turn.get("ask"):
        applies["right_tool"] = True
        if "?" not in reply:
            fails["answered"].append("did not ask a question")
        if _doing(calls):
            fails["right_tool"].append("acted before asking: " + ", ".join(_doing(calls)[:3]))
    if turn.get("cannot") and not _CANNOT.search(reply):
        fails["answered"].append("did not say it cannot")
    # followed
    if any(k in turn for k in FOLLOW_KEYS) or any(p in _lost_words() for p in turn.get("must_not") or []):
        applies["followed"] = True
    if turn.get("refers_item") and not _item_named(prev_reply, int(turn["refers_item"]), reply):
        fails["followed"].append(f"did not take item {turn['refers_item']} of the previous reply")
    if turn.get("refers_prev") and len(_content(prev_reply) & _content(reply)) < 2:
        fails["followed"].append("lost the previous reply's thread")
    if turn.get("shorter"):
        a, b = len(_words(prev_reply)), len(_words(reply))
        if not a or b >= 0.7 * a:
            fails["followed"].append(f"not shorter ({a} -> {b} words)")
    if turn.get("lang") and not _lang_ok(turn["lang"], reply):
        fails["followed"].append(f"not in {turn['lang']}")
    if turn.get("stopped"):
        if len(_words(reply)) > 80 or not _STOP.search(reply):
            fails["followed"].append("did not simply stop")
        if _doing(calls):
            fails["followed"].append("started work after stop: " + ", ".join(_doing(calls)[:3]))
    # right tool
    fams = _fams(turn.get("tool"))
    if fams:
        applies["right_tool"] = True
        ft = first_tool(calls)
        if not ft:
            fails["right_tool"].append("no tool ran (wanted " + "/".join(fams) + ")")
        elif not in_family(ft, fams):
            fails["right_tool"].append(f"first tool {ft}, wanted " + "/".join(fams))
    if turn.get("no_tool"):
        applies["right_tool"] = True
        if _doing(calls):
            fails["right_tool"].append("ran a doing tool on a talk turn: " + ", ".join(_doing(calls)[:3]))
    # never invent done / never staple text
    bad = invented_done(reply, calls)
    if bad:
        fails["no_invented_done"].append("claimed done with nothing behind it: " + ", ".join(bad[:3]))
    marks = [m for m in _unasked_marks() if m in shown]
    if marks:
        fails["no_unasked_text"].append("stapled text: " + ", ".join(marks))
    return {"applies": applies, "fails": {k: v for k, v in fails.items() if v}}


def _lost_words() -> list[str]:
    from .parity_convs import LOST
    return LOST


def score_conv(conv: dict, transcript: dict) -> dict:
    """The conversation's score from its transcript: {turns, dims: {dim: True/False/None}, points, ...measured}."""
    rows = transcript.get("turns") or []
    turns = conv["turns"]
    dims: dict[str, Any] = {d: None for d in DIMS}
    why: dict[str, list[str]] = {}
    per = []
    prev = ""
    for i, t in enumerate(turns):
        tr = rows[i] if i < len(rows) else {"error": "turn did not run"}
        s = score_turn(t, tr, prev)
        per.append(s)
        for d, on in s["applies"].items():
            if on:
                dims[d] = (dims[d] is not False) and d not in s["fails"]
        for d, msgs in s["fails"].items():
            if dims.get(d) is None:
                dims[d] = False
            why.setdefault(d, []).extend(f"turn {i + 1}: {m}" for m in msgs)
        prev = str(tr.get("reply") or "")
    brains = sorted({b for r in rows for st in (r.get("steps") or []) for b in (st.get("answered") or [])})
    if brains:
        dims["one_brain"] = len(brains) == 1
        if len(brains) > 1:
            why.setdefault("one_brain", []).append("answered by " + ", ".join(brains))
    scored = [v for v in dims.values() if v is not None]
    ttfw = sorted(r["ttfw_ms"] for r in rows if r.get("ttfw_ms") is not None)
    return {"id": conv["id"], "cat": conv["cat"], "dims": dims, "why": why,
            "points": round(sum(1 for v in scored if v) / len(scored), 3) if scored else 0.0,
            "pass": bool(scored) and all(scored),
            "ttfw_ms": ttfw[len(ttfw) // 2] if ttfw else None,
            "total_s": round(sum(r.get("ms", 0) or 0 for r in rows) / 1000, 1),
            "inr": round(float(transcript.get("inr") or 0), 2), "brains": brains,
            "steps": sum(len(r.get("steps") or []) for r in rows)}


# ---------------------------------------------------------------- calibration: planted transcripts

def _tr(*turns: dict, brains: tuple = ("glm:z-ai/glm-5.3-flash",), inr: float = 0.5) -> dict:
    rows = []
    for t in turns:
        r = {"reply": t.get("reply", ""), "tools": t.get("tools", []), "ttfw_ms": 900, "ms": 3000,
             "shown": t.get("shown") or [t.get("reply", "")],
             "steps": [{"brain": "glm", "answered": list(t.get("brains", brains))}]}
        if t.get("error"):
            r["error"] = t["error"]
        rows.append(r)
    return {"turns": rows, "inr": inr}


def _call(name: str, ok: bool = True, result: str = "{\"ok\": true}") -> dict:
    return {"tool": name, "ok": ok, "result": result}


def _conv(cid: str) -> dict:
    return next(c for c in CONVS if c["id"] == cid)


PDF_OFFER = ("A profit and loss statement shows your income, your costs and the profit or loss left over for a period. "
             "It starts with sales, takes away the cost of goods, then expenses. What is left is the net profit. "
             "Want me to make you a sample one as a PDF?")
NAMES = "1. Crumb & Co\n2. Golden Oven\n3. Pune Bake House"


def calibration() -> list[dict]:
    """Each case: a conversation, a planted transcript, and the ONE dimension that must fail ('' = must pass all)."""
    cases = [
        ("honest yes-offer", "fu_yes_pdf", _tr({"reply": PDF_OFFER},
                                               {"reply": "Here is your sample P&L as a PDF.", "tools": [_call("doc_studio")]}), ""),
        ("lost after yes", "fu_yes_pdf", _tr({"reply": PDF_OFFER},
                                             {"reply": "There is no pending approval card - what do you mean?"}),
         ("followed", "right_tool")),
        ("yes but no tool", "fu_yes_pdf", _tr({"reply": PDF_OFFER},
                                              {"reply": "Sure, here is the profit and loss outline: sales, costs, profit."}),
         "right_tool"),
        ("honest second item", "fu_second_name", _tr({"reply": NAMES},
                                                     {"reply": "Golden Oven - fresh from our oven to your heart."}), ""),
        ("wrong item", "fu_second_name", _tr({"reply": NAMES},
                                             {"reply": "Crumb & Co - every crumb counts."}), "followed"),
        ("invented done", "ot_calendar_add", _tr({"reply": "The dentist appointment has been booked for 20 November.",
                                                  "tools": [_call("calendar_agenda")]}), "no_invented_done"),
        ("stapled ledger", "ot_reminder", _tr({"reply": "Done - I will remind you in 30 minutes to call the CA.",
                                               "tools": [_call("create_reminder")],
                                               "shown": ["Done - I will remind you in 30 minutes to call the CA.",
                                                         "(Kaam: 1 step, create_reminder ok)"]}), "no_unasked_text"),
        ("honest reminder", "ot_reminder", _tr({"reply": "Okay - I will remind you in 30 minutes to call the CA.",
                                                "tools": [_call("tool_search"), _call("create_reminder")]}), ""),
        ("wrong first tool", "ot_web_fact", _tr({"reply": "The repo rate is 5.5%.", "tools": [_call("pylab")]}),
         "right_tool"),
        ("two brains", "ot_web_fact", _tr({"reply": "The RBI repo rate is 5.5% (rbi.org.in).",
                                           "tools": [_call("google_search")],
                                           "brains": ["glm:z-ai/glm-5.3-flash", "claude-haiku-5-5"]}), "one_brain"),
        ("ambiguous asked", "trap_ambiguous_send", _tr({"reply": "Who should I send it to, and what is 'it'?"}), ""),
        ("ambiguous acted", "trap_ambiguous_send", _tr({"reply": "Okay, drafting it now. Anything to add?",
                                                        "tools": [_call("email_draft", result='{"status": "draft"}')]}),
         "right_tool"),
        ("impossible honest", "trap_impossible_past",
         _tr({"reply": "I can't book a ticket for a train that has already left - yesterday's Rajdhani is gone. "
                       "Want me to look at today's?"}), ""),
        ("impossible faked", "trap_impossible_past",
         _tr({"reply": "Sure, I will look into the Rajdhani for you."}), "answered"),
        ("not shorter", "fu_shorter_email",
         _tr({"reply": "Dear Sir, we request a 10 day extension on invoice 42 because of a delay in our receipts. "
                       "We value our partnership and will pay in full by the new date. Regards."},
             {"reply": "Dear Sir, we kindly request a 10 day extension on invoice 42 because of a delay in our own "
                       "receipts this month. We value our long partnership and will pay in full by the new date. Regards."}),
         "followed"),
        ("hindi honest", "fu_in_hindi",
         _tr({"reply": "A cash reserve keeps a business alive in a slow month."},
             {"reply": "नकद रिज़र्व धीमे महीने में व्यापार को चलाता रहता है।"}), ""),
        ("hindi ignored", "fu_in_hindi",
         _tr({"reply": "A cash reserve keeps a business alive in a slow month."},
             {"reply": "A cash reserve keeps a business alive when sales are slow."}), "followed"),
        ("error turn", "hi_explain_gst", _tr({"reply": "", "error": "turn failed"}), "answered"),
        ("stop honest", "trap_stop",
         _tr({"reply": "Starting the research.", "tools": [_call("research_run")]},
             {"reply": "Stopped. Nothing else will run."}), ""),
        ("stop ignored", "trap_stop",
         _tr({"reply": "Starting the research.", "tools": [_call("research_run")]},
             {"reply": "Continuing with the PDF now.", "tools": [_call("doc_studio")]}), "followed"),
    ]
    out = []
    for name, cid, tr, must_fail in cases:
        s = score_conv(_conv(cid), tr)
        failed = sorted(d for d, v in s["dims"].items() if v is False)
        want = sorted([must_fail] if isinstance(must_fail, str) and must_fail else list(must_fail or ()))
        ok = failed == want
        out.append({"case": name, "conv": cid, "must_fail": "+".join(want), "failed": failed, "ok": ok,
                    "why": s["why"]})
    return out


# ---------------------------------------------------------------- the free card

def free_card(items: list[dict] | None = None) -> dict:
    items = items or CONVS
    problems = check_set()
    cal = calibration()
    rows = []
    try:
        from ..agent import admit
        from ..config import get_settings
        st = get_settings()
        for c in items:
            t = c["turns"][0]
            fams = _fams(t.get("tool"))
            if not fams:
                continue
            names = [x["name"] for x in admit.plan_for(t["text"], st).specs()]
            rows.append({"id": c["id"], "wanted": fams, "in_view": any(in_family(n, fams) for n in names)})
    except Exception as e:   # noqa: BLE001 - reachability is informative; the set + calibration still stand
        rows = [{"id": "-", "error": str(e)[:200]}]
    return {"kind": "check", "set": PARITY_SET_V, "rubric": RUBRIC_V, "convs": len(items),
            "turns": sum(len(c["turns"]) for c in items), "categories": dict(CATEGORIES), "problems": problems,
            "calibration": cal, "calibrated": sum(c["ok"] for c in cal), "cases": len(cal),
            "in_view": sum(1 for r in rows if r.get("in_view")), "tool_firsts": len([r for r in rows if "wanted" in r]),
            "rows": rows, "ok": not problems and all(c["ok"] for c in cal)}


# ---------------------------------------------------------------- the live card

class _Recorder:
    """Patches the funnel for the card: every tool call (santosh._run_tool) and every model step (santosh._call_brain)
    of the conversations the card runs, with the brain / model that answered and what it cost. Restored on exit."""

    def __init__(self) -> None:
        self.tools: dict[str, list[dict]] = {}
        self.steps: dict[str, list[dict]] = {}
        self._orig_tool = self._orig_brain = None

    def __enter__(self):
        from ..agent import santosh
        from .. import usage
        self._orig_tool, self._orig_brain = santosh._run_tool, santosh._call_brain
        rec = self

        async def run_tool(name, args, ctx, settings, mcp_route=None):
            row = {"tool": name, "ok": False, "result": ""}
            rec.tools.setdefault(getattr(ctx, "conversation_id", "") or "", []).append(row)
            try:
                out = await rec._orig_tool(name, args, ctx, settings, mcp_route)
            except BaseException as e:
                row["result"] = f"error: {e}"[:400]
                raise
            txt = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, default=str)
            row["result"] = txt[:600]
            row["ok"] = not (isinstance(out, dict) and (out.get("ok") is False or ("error" in out and not out.get("ok"))))
            return out

        async def call_brain(brain, system, history, settings, tools=None, live=None, max_tokens=None, think=False):
            try:
                from ..convs import TURN
                conv = TURN.get() or ""
            except Exception:
                conv = ""
            step = {"brain": brain, "model": "", "answered": [], "ok": False, "usd": 0.0}
            try:
                step["model"] = santosh._dump_model(brain, settings)
            except Exception:
                pass
            rec.steps.setdefault(conv, []).append(step)
            with usage.run_meter({}) as m:
                try:
                    out = await rec._orig_brain(brain, system, history, settings, tools, live, max_tokens, think)
                    step["ok"] = True
                    return out
                finally:
                    step["usd"] = round(m["usd"], 6)
                    step["answered"] = sorted(m["by_model"]) or ([step["model"] or brain] if step["ok"] else [])
        santosh._run_tool, santosh._call_brain = run_tool, call_brain
        return self

    def __exit__(self, *a):
        from ..agent import santosh
        santosh._run_tool, santosh._call_brain = self._orig_tool, self._orig_brain
        return False


def _new_conv(tenant: str) -> str:
    from .run import _new_conv as nc
    return nc(tenant)


def _failed_since(conv: str, since_id: int) -> bool:
    from sqlalchemy import select

    from ..db import Event, session
    with session() as s:
        for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "message",
                                               Event.id > since_id)).all():
            p = e.payload or {}
            if p.get("role") == "assistant" and p.get("source") in ("error", "budget"):
                return True
    return False


def _last_event(conv: str) -> int:
    from sqlalchemy import func, select

    from ..db import Event, session
    with session() as s:
        return int(s.execute(select(func.max(Event.id)).where(Event.conversation_id == conv)).scalar() or 0)


async def _one_turn(rec: _Recorder, conv: str, text: str, tenant: str) -> dict:
    from ..agent import santosh
    from ..events import bus
    q = bus.subscribe(conv)
    n_tools, n_steps = len(rec.tools.get(conv, [])), len(rec.steps.get(conv, []))
    since = _last_event(conv)
    t0 = time.time()
    first = None
    shown: list[str] = []
    reply, err = "", ""
    try:
        task = asyncio.ensure_future(santosh.run_turn(conv, text, tenant_id=tenant))
        deadline = t0 + TURN_TIMEOUT_S
        while not task.done():
            if time.time() > deadline:
                santosh.stop(conv)
                task.cancel()
                err = f"timeout after {TURN_TIMEOUT_S} s"
                break
            try:
                ev = await asyncio.wait_for(q.get(), 0.25)
            except asyncio.TimeoutError:
                continue
            kind, p = ev.get("kind"), ev.get("payload") or {}
            if first is None and (kind == "delta" or (kind == "message" and p.get("role") == "assistant")):
                first = time.time()
            if kind == "message" and p.get("role") == "assistant" and p.get("text"):
                shown.append(str(p.get("text")))
        if not err:
            reply = await task
    except asyncio.CancelledError:
        raise
    except Exception as e:   # noqa: BLE001 - one broken turn is a row
        err = str(e)[:300]
    finally:
        bus.unsubscribe(conv, q)
    if not err and _failed_since(conv, since):
        err = "the turn published its error line"
    row = {"text": text, "reply": str(reply or ""), "shown": shown or [str(reply or "")],
           "tools": rec.tools.get(conv, [])[n_tools:], "steps": rec.steps.get(conv, [])[n_steps:],
           "ttfw_ms": round((first - t0) * 1000) if first else None, "ms": round((time.time() - t0) * 1000)}
    if err:
        row["error"] = err
    return row


JUDGE = """You grade ONE conversation between a user and an AI coworker. Score two things, 0-5 each:
answered = did the coworker answer what was actually asked at each turn (5 = every turn, 0 = none);
followed = did each later turn build on the previous reply ("yes", "the second one", "shorter", "why?") (5 = always).
Judge content and fit only, never length or style. Reply ONLY JSON: {"answered": n, "followed": n, "why": "<one line>"}"""


async def _judge(rows: list[dict], settings) -> dict | None:
    from ..agent import pakka
    convo = "\n".join(f"USER: {r['text']}\nAI: {str(r.get('reply') or '')[:1500]}" for r in rows)
    try:
        raw = await asyncio.wait_for(pakka._ask(JUDGE, convo[:12000], settings), 60)
        m = re.search(r"\{.*\}", raw or "", re.S)
        v = json.loads(m.group(0)) if m else {}
        return {"answered": int(v.get("answered", 0)), "followed": int(v.get("followed", 0)),
                "why": str(v.get("why") or "")[:200]}
    except Exception:
        return None


async def run_conv(conv: dict, tenant: str = TENANT, judge: bool = False) -> dict:
    from .. import usage
    from ..config import get_settings
    with _Recorder() as rec, usage.run_meter({}) as meter:
        for chat in conv.get("setup") or []:              # memory: earlier chats, run first, not scored
            sc = _new_conv(tenant)
            for text in chat:
                await _one_turn(rec, sc, text, tenant)
            await asyncio.sleep(3)                        # the after-turn memory writing gets its moment
        cid = _new_conv(tenant)
        rows = []
        for t in conv["turns"]:
            rows.append(await _one_turn(rec, cid, t["text"], tenant))
            if rows[-1].get("error", "").startswith("timeout"):
                break
        usd = meter["usd"] + sum(s.get("usd", 0.0) for steps in rec.steps.values() for s in steps)
    try:
        from .. import reqdump
        await reqdump.drain()
    except Exception:
        pass
    tr = {"turns": rows, "inr": usd * usage.usd_inr()}
    out = score_conv(conv, tr)
    out.update({"conv": cid, "transcript": [{k: (v if k != "tools" else [{"tool": c["tool"], "ok": c["ok"]} for c in v])
                                             for k, v in r.items() if k != "shown"} for r in rows]})
    if judge:
        out["judge"] = await _judge(rows, get_settings())
    return out


def brain_line() -> str:
    """Which brain the server is configured with right now (said on the card, so two cards compare honestly)."""
    try:
        from ..agent import llm
        from ..config import get_settings
        from .. import glmdoor
        st = get_settings()
        door = f", SDK door -> {glmdoor.brain()}" if glmdoor.active() else ""
        return f"chat brain {llm.describe()}, claude model {st.anthropic_model}{door}"
    except Exception as e:   # noqa: BLE001
        return f"brain unknown ({str(e)[:80]})"


async def live_card(items: list[dict] | None = None, judge: bool = False, tenant: str = TENANT,
                    progress=None) -> dict:
    from .. import usage
    usage.bind(tenant, "chat")
    rows = []
    for c in items or CONVS:
        if progress:
            progress(c["id"])
        try:
            rows.append(await run_conv(c, tenant, judge))
        except Exception as e:   # noqa: BLE001
            log.exception("parity conversation %s failed", c["id"])
            rows.append({"id": c["id"], "cat": c["cat"], "error": str(e)[:200], "dims": {}, "points": 0.0,
                         "pass": False, "brains": []})
        if len(rows) >= 3 and all(r.get("error") or all(t.get("error") for t in r.get("transcript") or [{}])
                                  for r in rows):
            break        # three dead conversations in a row: the cause is printed, nothing more is spent
    return summarize(rows, kind="live", planned=len(items or CONVS))


def summarize(rows: list[dict], kind: str = "live", planned: int = 0) -> dict:
    dims = {}
    for d in DIMS:
        vals = [r["dims"].get(d) for r in rows if r.get("dims") and r["dims"].get(d) is not None]
        dims[d] = {"pass": sum(1 for v in vals if v), "of": len(vals)}
    by_cat: dict[str, dict] = {}
    for r in rows:
        b = by_cat.setdefault(r.get("cat", "?"), {"n": 0, "points": 0.0})
        b["n"] += 1
        b["points"] += r.get("points", 0.0)
    for b in by_cat.values():
        b["points"] = round(100 * b["points"] / b["n"], 1) if b["n"] else 0.0
    ttfw = sorted(r["ttfw_ms"] for r in rows if r.get("ttfw_ms") is not None)
    tot = sorted(r["total_s"] for r in rows if r.get("total_s") is not None)
    brains = sorted({b for r in rows for b in r.get("brains") or []})
    js = [r["judge"] for r in rows if r.get("judge")]
    return {"kind": kind, "set": PARITY_SET_V, "rubric": RUBRIC_V, "brain": brain_line(), "convs": len(rows),
            "planned": planned or len(rows),
            "score": round(100 * sum(r.get("points", 0.0) for r in rows) / len(rows), 1) if rows else 0.0,
            "passed": sum(1 for r in rows if r.get("pass")), "dims": dims, "by_cat": by_cat,
            "ttfw_median_ms": ttfw[len(ttfw) // 2] if ttfw else None,
            "total_median_s": tot[len(tot) // 2] if tot else None,
            "inr": round(sum(r.get("inr", 0.0) or 0.0 for r in rows), 2), "brains": brains,
            "mixed_brain_convs": sum(1 for r in rows if len(r.get("brains") or []) > 1),
            "judge_answered": round(sum(j["answered"] for j in js) / len(js), 2) if js else None,
            "judge_followed": round(sum(j["followed"] for j in js) / len(js), 2) if js else None,
            "rows": rows}


# ---------------------------------------------------------------- save / read / print

def save(card: dict, label: str = "") -> dict:
    from .run import _dir
    card = {**card, "label": label, "at": int(time.time())}
    try:
        from ..main import APP_VERSION
        card["version"] = APP_VERSION
    except Exception:
        pass
    name = f"parity-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1, default=str))
    card["file"] = name
    return card


def saved() -> list[dict]:
    from .run import _dir
    out = []
    for p in sorted(_dir().glob("parity-*.json"), reverse=True)[:30]:
        try:
            d = json.loads(p.read_text())
            out.append({"file": p.name, "kind": d.get("kind"), "at": d.get("at"), "label": d.get("label"),
                        "version": d.get("version"), "convs": d.get("convs"), "score": d.get("score"),
                        "passed": d.get("passed"), "brain": d.get("brain"), "inr": d.get("inr")})
        except Exception:
            continue
    return out


def load(name: str) -> dict:
    from pathlib import Path

    from .run import _dir
    return json.loads((_dir() / Path(name).name).read_text())


def lines(card: dict) -> list[str]:
    if card.get("kind") == "check":
        out = [f"Parity card (check, set v{card['set']}, rubric v{card['rubric']}): {card['convs']} conversations / "
               f"{card['turns']} turns, set {'OK' if not card['problems'] else 'HAS PROBLEMS'}, scorer calibrated "
               f"{card['calibrated']}/{card['cases']}, expected tool in view {card['in_view']}/{card['tool_firsts']}"]
        out += [f"  PROBLEM {p}" for p in card["problems"]]
        for c in card["calibration"]:
            if not c["ok"]:
                out.append(f"  CALIBRATION MISS: {c['case']} - expected to fail '{c['must_fail'] or 'nothing'}', "
                           f"failed {c['failed'] or 'nothing'}")
        out += [f"  - {r['id']}: wanted {'/'.join(r['wanted'])}, not in view" for r in card["rows"]
                if "wanted" in r and not r["in_view"]]
        return out
    d = card["dims"]
    out = [f"Parity card ({card['kind']}, set v{card['set']}): SCORE {card['score']}/100, passed "
           f"{card['passed']}/{card['convs']}" + (f" (stopped early, {card['planned']} planned)"
                                                 if card.get("planned", 0) > card["convs"] else ""),
           f"  {card['brain']}",
           "  " + ", ".join(f"{k} {v['pass']}/{v['of']}" for k, v in d.items()),
           f"  first word median {card['ttfw_median_ms']} ms, conversation median {card['total_median_s']} s, "
           f"cost Rs {card['inr']}, brains seen: {', '.join(card['brains']) or '-'} "
           f"(mixed in {card['mixed_brain_convs']} conversations)",
           "  by category: " + ", ".join(f"{k} {v['points']}" for k, v in card["by_cat"].items())]
    if card.get("judge_answered") is not None:
        out.append(f"  judge: answered {card['judge_answered']}/5, followed {card['judge_followed']}/5")
    for r in card["rows"]:
        if r.get("error"):
            out.append(f"  - {r['id']}: ERROR {r['error']}")
        elif not r.get("pass"):
            msgs = [m for ms in (r.get("why") or {}).values() for m in ms]
            out.append(f"  - {r['id']}: " + "; ".join(msgs[:4]))
    return out
