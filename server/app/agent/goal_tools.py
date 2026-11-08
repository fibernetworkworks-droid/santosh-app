"""v0.186 the `kaam_plan` tool: the brain writes its own plan for a long job and ticks every step as it goes.

One tool, five actions (the model cannot invent states or skip the card):
- set    goal + steps (max 15)          -> a new goal card; any previous working goal in this chat is stopped
- step   n + done|failed|skipped|current (+ note) -> progress on the card, live in chat and in the call
- add    one more step                  -> when the real work reveals a step the plan lacked
- show   the plan as it stands
- finish done | blocked_on_her | failed | stopped (+ reason) -> closes the card; blocked_on_her is ONLY for a real
  dependency on her (her tap, an OTP, a missing fact) — never for "a tool failed" (that is what the ladder is for).
"""
from __future__ import annotations

from . import goal as goal_mod
from .tools import Ctx, ToolError

KAAM_PLAN_DEF = {
    "name": "kaam_plan",
    "description": (
        "Plan and track a long job (3+ steps) so it finishes end to end: set the plan first, then work through it "
        "step by step, marking each step done / failed as you go. Never stop with just text while steps are open. "
        "Actions: set (goal, steps), step (n, state done|failed|skipped|current, reason, check), add (text), show, "
        "finish (outcome done|blocked_on_her|failed|stopped, reason, made, left, your_turn). "
        "`done` is CHECKED IN CODE before the card closes: every file / page / link you list in `made` must really "
        "exist, and every step `check` must hold - so put the real file id / link in the step's reason and in `made`. "
        "Where a step produces something checkable, give it a `check`: file_pages>=3, file_rows>=20, file_slides>=6, "
        "file:<name>, link_ok, artifact, reminder>=3, list:<name>>=5, tool:<name>. After every big step write "
        "ONE short line to her (what you found / made, what is next), then the next tool. blocked_on_her is only when you truly need "
        "HER: her tap on a card, an OTP, or a fact only she knows. "
        "On a CALL, show / add / step reach the job already running in the chat the call came from: 'isme ye bhi jodo' = "
        "add (never a second set), 'kahan tak pahuncha' = show."),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["set", "step", "add", "show", "finish"]},
            "goal": {"type": "string", "description": "(set) the job in her words, one line"},
            "steps": {"type": "array", "items": {"type": "string"}, "description": "(set) the concrete steps, in order"},
            "n": {"type": "integer", "description": "(step) the step number, 1-based"},
            "state": {"type": "string", "enum": ["done", "failed", "skipped", "current"], "description": "(step)"},
            "check": {"type": "string",
                      "description": "(set step / step / add) how this step's doneness is PROVED in code: "
                                     "file_pages>=N | file_rows>=N | file_slides>=N | file:<name> | link_ok | "
                                     "artifact | reminder>=N | list:<name>>=N | tool:<name>. Leave empty when the "
                                     "step makes nothing checkable."},
            "text": {"type": "string", "description": "(add) the new step"},
            "outcome": {"type": "string", "enum": ["done", "blocked_on_her", "failed", "stopped"], "description": "(finish)"},
            "reason": {"type": "string", "description": "(step/finish) one short line: what happened / what she must do"},
            "made": {"type": "array", "items": {"type": "string"},
                     "description": "(finish) links / file names / ids that the job produced (real ones from tool results)"},
            "left": {"type": "string", "description": "(finish) anything still left that is not a plan step"},
            "your_turn": {"type": "string", "description": "(finish) what SHE must do now, if anything (one line)"},
            "goal_id": {"type": "string", "description": "(step/add/show/finish) from the set result; the active plan needs none"},
        },
        "required": ["action"],
    },
}


def _goal_for(conv: str):
    """CALL PAR TEAM: the running job THIS conversation can act on - its own, or (on a call record) the job running in
    the chat the call came from, so "isme ye bhi jodo" / "kahan tak pahuncha" on a call reaches her chat's long job."""
    a = goal_mod.active_for(conv)
    if a is not None:
        return a
    try:
        from .. import callconv
        chat = callconv.chat_of(conv)
        if chat and chat != conv:
            return goal_mod.active_for(chat)
    except Exception:
        return None
    return None


async def kaam_plan(ctx: Ctx, action: str = "set", goal: str = "", steps: list[str] | None = None, n: int = 0,
                    state: str = "", text: str = "", outcome: str = "", reason: str = "", goal_id: str = "",
                    made: list[str] | None = None, left: str = "", your_turn: str = "", note: str = "",
                    check: str = "") -> dict:
    # v0.260: `note` is an alias for `reason`. The schema used to document "step (n, state, note)" while the code
    # took `reason`, so a model that followed the description died with a TypeError mid-job (it cost the owner a
    # whole step on 29 Oct). The description is fixed above; this keeps any future guess from crashing her work.
    reason = reason or note
    tenant, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "set":
            v = goal_mod.set_goal(tenant, conv, goal, steps or [], origin=getattr(ctx, "actor", "owner") or "owner")
        elif action == "step":
            if not goal_id:
                a = _goal_for(conv)
                if a is None:
                    raise ToolError("Is chat ka koi goal chal nahi raha; pehle kaam_plan set karo.")
                goal_id = a["id"]
                conv = a.get("conversation_id") or conv
            if not state:
                # v0.703: a missing state used to fail the step (her G8 run: three times in a row, the goal stuck
                # and the 'doosra tareeka' loop began). A step reported with what it made / a note = done;
                # a bare call = the step she is on now.
                state = "done" if (reason or made) else "current"
            state = {"completed": "done", "complete": "done", "finished": "done", "ok": "done", "success": "done",
                     "in_progress": "current", "working": "current", "started": "current", "doing": "current",
                     "skip": "skipped", "fail": "failed", "error": "failed"}.get(str(state).strip().lower(),
                                                                               str(state).strip().lower())
            v = goal_mod.mark_step(tenant, goal_id, int(n), state, reason or "", conv, check=check)
        elif action == "add":
            if not goal_id:
                a = _goal_for(conv)
                if a is None:
                    raise ToolError("Is chat ka koi goal chal nahi raha; pehle kaam_plan set karo.")
                goal_id = a["id"]
                conv = a.get("conversation_id") or conv
            v = goal_mod.add_step(tenant, goal_id, text, conv, check=check)
        elif action == "show":
            v = goal_mod.show(tenant, goal_id) if goal_id else (_goal_for(conv) or {})
            if not v:
                raise ToolError("Is chat ka koi goal chal nahi raha.")
        elif action == "finish":
            if not goal_id:
                a = _goal_for(conv)
                if a is None:
                    raise ToolError("Is chat ka koi goal chal nahi raha.")
                goal_id = a["id"]
                conv = a.get("conversation_id") or conv
            if not outcome:
                raise ToolError("outcome chahiye: done | blocked_on_her | failed | stopped")
            v = goal_mod.finish(tenant, goal_id, outcome, reason, conv, made=made or [], left=left,
                                your_turn=your_turn, calls=getattr(ctx, "calls", None))
        else:
            raise ToolError("action set | step | add | show | finish")
    except ToolError:
        raise
    except ValueError as e:
        raise ToolError(str(e)) from None
    if action == "finish" and v.get("verified") is False:
        # v0.443 DONE = VERIFIED: the job stays open; the model must really do the failing part
        from . import verify as _verify
        g = v.get("verify") or {}
        return {"result": "goal band NAHI hua - jaanch fail", "goal_id": v["id"], "status": v["status"],
                "done": f"{v['done']}/{v['total']}", "verified": False,
                "failures": [{"item": f["item"], "why": f["why"]} for f in (g.get("failures") or [])][:6],
                "unknown": [{"item": u["item"], "why": u["why"]} for u in (g.get("unknown") or [])][:3],
                "note": _verify.NUDGE.format(line=g.get("line") or "jaanch fail")}
    left = goal_mod.steps_left(v)
    say = (f"plan ban gaya: {v['total']} steps" if action == "set" else
           f"step {n} = {state}" if action == "step" else
           f"step juda (ab {v['total']})" if action == "add" else
           "goal band: " + v["status"] if action == "finish" else "plan aageya")
    out = {"result": say, "goal_id": v["id"], "status": v["status"], "done": f"{v['done']}/{v['total']}",
           "steps": [{ "n": x["n"], "state": x["state"], "text": x["text"]} for x in (v.get("steps") or [])]}
    if left:
        out["baaki"] = "; ".join(f"{x['n']}. {x['text']}" for x in left[:10])
        out["note"] = ("Steps baaki hain: tools se kaam karte raho, text par mat ruko. Poora hone par kaam_plan finish done. "
                       "Sirf uska tap / OTP / uska fact chahiye to finish blocked_on_her.")
    if action == "step" and state == "done" and left:
        # v0.258 CHALTE CHALTE BOLO: v0.240 said "write no line for this step", which contradicted PLAN_FIRST in the
        # same turn and left her staring at a silent card. Claude writes one line per step - the finding, not the dump.
        out["note"] += (" Ab ek chhoti line: is step se jo asli cheez mili (number / id / link) aur ab kya kar rahe "
                        "ho - ek vaakya, koi bullet ya heading nahi. Phir agla tool.")
    elif action == "step" and v["done"] == v["total"]:
        out["note"] = ("Sab steps done: kaam_plan finish done laga do — made mein asli links / files, aur your_turn "
                       "mein agar use kuch karna hai.")
    if action == "finish" and v.get("report"):
        # v0.240 CHHOTA JAWAB: the four parts are ALREADY on her card (phone _Report + console goalReport). The chat
        # gets ONE short human line, like Claude's end-of-work sentence - never the bullets again. The text rides as
        # `card_shows` (what she is already looking at), not as a template to echo.
        out["card_shows"] = goal_mod.report_text(v["report"])
        out["note"] = ("Yeh report uske CARD par pehle se dikh rahi hai. Chat mein sirf EK chhoti insaani line do - "
                       "ek ya do vaakya: kaam ho gaya (ya kahan atka), aur agar uska khud ka koi kaam baaki hai to "
                       "woh. Bullet list, '✅ Kya hua' / '📎 Kya bana' / '⏳ Kya baaki' / '👉 Aapko kya karna hai' "
                       "heading, step-by-step detail, links ki list - kuch bhi nahi. Card par jo hai usey chat mein "
                       "dohraao mat.")
    return out


GOAL_HANDLERS = {"kaam_plan": kaam_plan}
GOAL_LABELS = {"kaam_plan": "Lamba kaam ka plan (goal mode)"}
GOAL_TOOLS = [KAAM_PLAN_DEF]
