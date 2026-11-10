# ========= v0.688 KAAM MANCH — the work-discipline layer =========
# Kaam = work. KAAM MANCH is not a tool and not a family: it is the discipline layer over the
# work Hoola already does — the search habits, the done-needs-proof law, and the honest ledger
# line at the end of a turn.
#
# IDEA-ONLY port from github.com/camel-ai/owl @ 2df367e (Apache-2.0): ZERO upstream code crossed
# the wall, zero new dependencies, zero network, zero keys. What ported is OWL's orchestration
# doctrine, rewritten in the house register:
#   - the Web/Document/Coding workers' heuristic tips (examples/run.py prompts +
#     owl/utils/enhanced_role_playing.py's <tips> block)  -> TIPS below
#   - the <TASK_DONE> law ("never say done unless my responses have solved your task")
#     -> the DONE_CLAIM backstop + the done-means-proven tip line
#   - run_society's per-round honest record ({user, assistant, tool_calls} + the token tally)
#     -> ledger(), one (Kaam: ...) note per turn (steps/calls/plan only: state holds no
#        per-turn token tally and a made-up count is worse than none — the house's own
#        after_call law is "never a made-up count")
# The caps/loop machinery was NOT ported: the house already owns stricter ones (kaam_plan goal
# mode v0.187, agent_max_steps 24 / goal 80, the replan breaker, Pakka kaam v0.78).
#
# LAWS (pinned by test_v0688_kaam_manch.py):
#   1. IDENTITY  — zero tools, zero imports beyond stdlib, zero network, zero keys, zero side
#                   effects on import. Registry unchanged.
#   2. SWITCH    — everything the layer does is gated by settings.kaam_enabled (default True);
#                   off = byte-identical prompts, no ledger, no backstop.
#   3. TIPS      — TIPS is pure text, deterministic, house-written (no upstream sentence
#                   verbatim); it rides the system prompt ALWAYS (never admission-cut).
#   4. DONE      — done_note fires only on a strong done-claim while every non-skipped tool
#                   call of the turn failed; it costs no model call and never loops.
#   5. LEDGER    — one line per turn that ran tools; honest arithmetic, capped display, empty
#                   state = no line; it never raises (any missing key = skip that field).
#   6. PURITY    — this module is pure functions + string constants; a fresh interpreter
#                   imports it with zero threads, env, files or network touched.
import re

__all__ = ["TIPS", "LEDGER_MARK", "DONE_NOTE_MARK", "tips_block", "ledger", "done_note", "SOURCE"]

SOURCE = "camel-ai/owl@2df367e (Apache-2.0, idea-only)"

# The tips block, appended to the system prompt (always-on; gated by kaam_enabled at the caller).
# House register; OWL's heuristics rewritten, never quoted.
TIPS = """KAAM MANCH (v0.688, work discipline — how you WORK, whatever the tool):
- Search like a researcher: start broad to find the right site first, then go narrow. One or two good keywords beat a pasted sentence. For general facts check Wikipedia first, then the official page.
- A snippet is not a number: for any price, date, amount, ID or figure, open the page itself and read it there. If a snippet and the page disagree, the page wins.
- Name your sources: one line at the end - the sites and files you actually used.
- If one road fails, take another: a different query, a different tool, the page instead of the search. The answer usually exists; finding it is the job.
- Code is not work until you RUN it: execute what you wrote, read the output, and only then say what it did. Excel and data files go through code, not by eye.
- Done means PROVEN: say the kaam is done only when you can name the proof - the file path, the order/booking ID, the exact number a tool returned. A 'ho gaya' without a proof is not done; if something is left, say exactly what.
- Lamba kaam: one step at a time (kaam_plan), tick a step only when its result is real, verify the whole before saying the whole is done."""

LEDGER_MARK = "(Kaam:"          # the note rows start with this mark (the "(Dhyaan:" precedent)
DONE_NOTE_MARK = "(Kaam:"       # the done backstop rides as a state["correct"] note

# A strong completion claim in her final answer (Hinglish + English). Careful by design: only
# phrases that ASSERT finished work. A bare "ho gaya" is NOT enough — "kya ho gaya?" is a
# question — so the ho-gaya form needs a work noun in front of it (kaam/sab/payment/bill/...);
# the verb forms (ban gaya, bhej diya, save/book ho gaya) are claims on their own.
_DONE_CLAIM = re.compile(
    r"(?<![a-z])(ban\s+ga(ya|yi|ye)|bhej\s+diya|save\s+ho\s+ga(ya|yi|ye)|book\s+ho\s+ga(ya|yi|ye)|"
    r"(kaam|sab|payment|bill|file|order|booking|message|invoice|list|email|mail|site|website|"
    r"template|design|post|card)\s+ho\s+ga(ya|yi|ye)|"
    r"complete(d)?|finished|it'?s\s+done|sent\s+the|created\s+the)",
    re.I)

_CAP_ITEMS = 12                  # ledger display cap for the per-tool breakdown


def tips_block() -> str:
    """The tips text (pure; the caller gates on kaam_enabled and owns the join)."""
    return TIPS


def ledger(state: dict, ran_steps: int, cap: int, plan_left: int | None = None,
           plan_total: int = 0) -> str:
    """One honest work-receipt line for a turn that ran tools. '' when nothing ran.

    Pure: reads only the state dict the turn already keeps (calls, left, kept_going); every
    field is arithmetic over real counters, never an estimate. LAW-LEDGER: never raises —
    a missing key just drops that field from the line.
    """
    try:
        calls = state.get("calls") or []
        if not calls:
            return ""
        parts: list[str] = []
        steps = int(ran_steps or 0)
        parts.append(f"{steps}/{int(cap or 0)} steps" if cap else f"{steps} steps")
        ok = sum(1 for c in calls if c.get("ok"))
        parts.append(f"{len(calls)} calls ({ok} ok)")
        if plan_total:
            done_n = max(int(plan_total) - int(plan_left or 0), 0)
            parts.append(f"plan {done_n}/{int(plan_total)}")
        if state.get("left"):
            parts.append("left: " + str(state["left"])[:40])
        elif not state.get("kept_going"):
            parts.append("done ✓")
        per: list[str] = []
        seen: dict[str, int] = {}
        for c in calls:
            n = str(c.get("tool") or "?")
            seen[n] = seen.get(n, 0) + 1
        for n, k in seen.items():
            per.append(f"{n}×{k}" if k > 1 else n)
        if per:
            shown = per[:_CAP_ITEMS]
            more = "" if len(per) <= _CAP_ITEMS else f" +{len(per) - _CAP_ITEMS}"
            parts.append(", ".join(shown) + more)
        return f"{LEDGER_MARK} " + " · ".join(parts) + ")"
    except Exception:
        return ""


# An honest negation just before the claim ("not done", "nahi hua", "poora nahi hua") means the
# answer is NOT claiming completion — the backstay stays silent for those.
_NEGATED = re.compile(r"(not\s+(yet\s+)?(done|complete|finished)|didn'?t\s+(send|create|finish)|"
                      r"nah(i|in)\s+hua|poora\s+nah(i|in)\s+hua|atak\s+ga(ya|yi))", re.I)


def done_note(state: dict, final_text: str) -> str:
    """The TASK_DONE backstop: a strong done-claim while EVERY non-skipped call of the turn
    failed. '' otherwise. Costs no model call, never loops (the caller sets it as the turn's
    correction note, the existing single-check flow)."""
    try:
        text = str(final_text or "")
        if not _DONE_CLAIM.search(text) or _NEGATED.search(text):
            return ""
        calls = state.get("calls") or []
        if not calls:
            return ""
        if any(c.get("ok") for c in calls):
            return ""
        return ("(Kaam: every tool in this turn failed - what was asked is not done. "
                "To be clear about what did happen: what was tried, where it got stuck, and what should be done now.)")
    except Exception:
        return ""
