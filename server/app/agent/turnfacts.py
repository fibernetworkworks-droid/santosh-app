"""G3 of docs/LANGGRAPH_TURN_PLAN.md - done-truth from the turn's FACTS, and the check node's one decision (only when
`chat_graph` is on; the old loop never imports this module).

TURN FACTS. After every tools node the graph writes one fact per tool_use of the step into its checkpoint:

    {"id": tool_use id, "tool": name, "step": n, "effect": did | card | read | failed | ambiguous | stopped | skipped,
     "ledger": the G1 ledger state (done / failed / intent / ''), "object": recipient / address / id when the call
     names one, "error": a short reason}

The effect comes from what really happened, never from the reply's words:
  * the G1 ledger row (a row still `intent` after the step = the outcome is unknown; `failed` / `stopped` = her Stop
    cut it - G2) and the tool_result block the model got (is_error, the ambiguous text);
  * the turn's call record (`ok` = santosh.tool_failure, i.e. {"ok": False} / status failed is a failure too);
  * `draftcheck.effect()` on a call that finished ok: did (changed something) / card (a draft or card that waits for
    her tap) / read (only looked). A timed-out send is `ambiguous` (the work may still be running).

THE CHECK. `draftcheck.all_claims` still FINDS the claim sentences ("bhej diya", "I've sent", "has been booked" ...)
- that is the one regex left on this path - and `draftcheck.family_of` names the kind of tool that could make each
claim true. The VERDICT comes from the facts of that kind (object-matched when the claim names an address / a name
a fact carries):

    true      a fact of that kind DID it (and to the object the claim names, when it names one)
    card      only a card / draft is waiting for her tap - nothing happened yet
    failed    the tool that would do it failed
    unknown   it was cut off (a restart: G1 ambiguous; a time-out) - never "done"
    stopped   her Stop cut it (G2) - never "done"
    wrong     it was done, but for someone else than the claim names
    none      no tool of that kind ran at all

`none` / `card` / `failed` may still be excused by EARLIER facts: the job's own earlier rounds (`since` a goal began)
and a true report of work done in an earlier turn - both read from the harness event log (draftcheck.ran_before /
nothing_ran_in_job, the facts the earlier turns left). `unknown` / `stopped` are never excused.

THE DECISION (`Judge`): the check node's one place that may send the model back to work - a false claim (once, then
the honest note), a reminder promised with none set (once), the model self-check (the old non-plain mode only), an
open kaam_plan step (the goal nudge), a promise with no action (aage, MAX_PER_TURN) and a max_tokens cut - one budget
(today's per-kind caps + a total), every decision written into the checkpoint (`decision` / `decisions`) with WHY it
sent the model back (or why the answer stands). The texts the model sees are the old ones (draftcheck.NUDGE /
NUDGE_CARD / NUDGE_PART / NUDGE_PROMISE, aage.NUDGE, goal.nudge_text) plus three for verdicts the old check could not
tell apart (failed / unknown-or-stopped / wrong object)."""
from __future__ import annotations

import json
import logging
import re

log = logging.getLogger("santosh.turnfacts")

STATS = {"facts": 0, "checked": 0, "true": 0, "false": 0, "nudged": 0, "noted": 0, "budget_spent": 0}

DONE_LIKE = ("did",)
NEVER_DONE = ("ambiguous", "stopped")

# the check node's one budget: today's per-kind caps (the helpers keep their own counters with the same numbers) and
# a total no turn can pass, whatever mix of nudges it collects
CAPS = {"claim": 1, "reminder_promise": 1, "done_failed": 1, "self_check": 4, "plan": 8, "promise": 2, "max_tokens": 8}
TOTAL = 16

NUDGE_FAILED = ("[System check, not the user] Your message says \"{what}\" is done, but the tool that would do it "
                "FAILED this turn ({tools}) - nothing happened. Say plainly that it did not go through and why, and "
                "what can be done next (or do it again the right way now, every card / approval rule as usual). Never "
                "say done for something that failed.")
NUDGE_UNKNOWN = ("[System check, not the user] Your message says \"{what}\" is done, but the step that would do it "
                 "({tools}) was cut off - stopped, timed out or interrupted by a restart - so its outcome is UNKNOWN. "
                 "Do not call it done. Check what really happened (its own status / sent / list tool) or tell her "
                 "plainly that it may or may not have gone through. Never repeat a send, order, payment or booking "
                 "without checking first.")
NUDGE_WRONG = ("[System check, not the user] Your message says it was done for {named}, but the tool did it for "
               "{actual}. Say exactly what was done and for whom; if {named} still needs it, say that it is not "
               "done yet.")
SAID_UNKNOWN = "(To be clear: I cannot confirm this went through - the step was cut off, so please check before trying again.)"
SAID_FAILED = "(To be clear: this did not go through - the step failed.)"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ID = re.compile(r"[\"']?(?:id|message_id|order_id|booking_id|draft_id|event_id|payment_id)[\"']?\s*[:=]\s*[\"']?"
                 r"([\w-]{3,60})", re.I)
_NOUN = re.compile(r"^sent\s+(?:folder|items?|box|mail\s+folder|tab|list|messages?\s+folder)\b", re.I)
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")
_OBJ_KEYS = ("to", "recipient", "recipients", "email", "emails", "phone", "number", "mobile", "contact", "name",
             "chat", "channel", "page", "title")
_AMBIG_ERRORS = ("outcome unknown after a restart",)
_STOP_ERRORS = ("stopped by the owner",)
_STOP_RESULT = ("The user tapped Stop", "Stopped by the owner while this step was running")


# ---------------------------------------------------------------- the facts

def _obj(args) -> str:
    """The thing a call acts on, when its arguments name one (recipient / address / name / title)."""
    if not isinstance(args, dict):
        return ""
    for k in _OBJ_KEYS:
        v = args.get(k)
        if isinstance(v, (list, tuple)):
            v = ", ".join(str(x) for x in v[:5])
        if v not in (None, "", [], {}):
            return str(v)[:120]
    return ""


def _result_text(block: dict | None) -> str:
    if not block:
        return ""
    c = block.get("content")
    if isinstance(c, str):
        return c
    try:
        return json.dumps(c, ensure_ascii=False, default=str)
    except Exception:   # noqa: BLE001
        return str(c)


def classify(call: dict | None, result: dict | None, ledger: dict | None, read_only: bool) -> tuple[str, str]:
    """(effect, short error) of one tool_use from its call record, its tool_result block and its ledger row."""
    from . import draftcheck
    err = str((call or {}).get("error") or "")
    res = _result_text(result)
    lkind = (ledger or {}).get("error_kind") or ""
    if lkind == "stopped" or any(e in err for e in _STOP_ERRORS) or res.startswith(_STOP_RESULT):
        return "stopped", err or "stopped by the owner"
    if any(e in err for e in _AMBIG_ERRORS) or "MAY ALREADY HAVE RUN" in res:
        return "ambiguous", err or "outcome unknown"
    if call is None:
        return "skipped", res[:160]          # held by the breaker / never started: nothing happened
    if not call.get("ok"):
        if (err == "timeout" or lkind == "timeout") and not read_only:
            return "ambiguous", "timed out - it may still be running"
        return "failed", err[:160]
    return (draftcheck.effect(call) or "failed"), ""


def step_facts(blocks: list, results: list, calls: list, step: int, ledger_rows: dict | None = None) -> list[dict]:
    """One fact per tool_use block of a finished tools step. `calls` = the call records this step appended
    (santosh state['calls'] after the step minus before), `results` = the tool_result blocks the model gets,
    `ledger_rows` = {tool_use id: the G1 ledger row} when the turn has a ledger."""
    from . import santosh as S
    from . import toolledger as L
    by_id = {r.get("tool_use_id"): r for r in results or [] if isinstance(r, dict) and r.get("type") == "tool_result"}
    left = list(calls or [])
    out = []
    for b in blocks or []:
        if b.get("type") != "tool_use":
            continue
        name, args = b.get("name") or "", b.get("input") or {}
        key = S._key(name, args)
        call = next((c for c in left if c.get("tool") == name and c.get("key") == key), None) \
            or next((c for c in left if c.get("tool") == name), None)
        if call is not None:
            left.remove(call)
        try:
            ro = L.read_only(b)
        except Exception:   # noqa: BLE001
            ro = False
        eff, err = classify(call, by_id.get(b.get("id")), (ledger_rows or {}).get(b.get("id")), ro)
        obj = _obj(args)
        if not obj and call is not None and eff in ("did", "card"):
            m = _ID.search(str(call.get("result") or ""))
            obj = m.group(1) if m else ""
        out.append({"id": b.get("id") or "", "tool": name, "step": int(step or 0), "effect": eff,
                    "ledger": ((ledger_rows or {}).get(b.get("id")) or {}).get("state") or "", "object": obj,
                    "error": err[:160]})
    STATS["facts"] += len(out)
    return out


# ---------------------------------------------------------------- the verdicts

def _named(obj: str, clause: str) -> bool:
    """Does the claim's clause name this fact's object (an address, a phone, a name)?"""
    o, c = (obj or "").lower(), (clause or "").lower()
    if not o:
        return False
    if any(e.lower() in c for e in _EMAIL.findall(o)):
        return True
    toks = [t for t in re.split(r"[\s,;<>\"']+", o) if len(t) >= 3 and "@" not in t]
    return any(re.search(r"\b" + re.escape(t) + r"\b", c) for t in toks)


def _checked_after(pool: list[dict], facts: list[dict]) -> bool:
    """A cut-off step (ambiguous / stopped) followed, later in the turn, by a successful READ of the same kind (its
    sent list, its status) - the model did what the nudge asks: it checked before saying anything."""
    order = {id(f): i for i, f in enumerate(facts or [])}
    cut = [order.get(id(f), -1) for f in pool if f.get("effect") in NEVER_DONE]
    return bool(cut) and any(f.get("effect") == "read" and order.get(id(f), -1) > max(cut) for f in pool)


def verdicts(text: str, facts: list[dict]) -> list[dict]:
    """Every claim of the answer with its verdict from the facts (see the module note)."""
    from . import draftcheck
    out = []
    sentences = [x for x in _SENT.split(text or "") if x.strip()]
    for phrase, window, clause in draftcheck.all_claims(text):
        at = clause.lower().find(phrase.lower()) if phrase else -1
        if at >= 0 and _NOUN.search(clause[at:]):
            continue                       # "the sent folder" names a place, it claims nothing
        fam, tools = draftcheck.family_of(phrase, window)
        mine = [f for f in facts or [] if draftcheck._backs_claim({"tool": f.get("tool")}, tools)]
        head = clause.strip()[:40]
        sent = next((x for x in sentences if head and head in x), clause)   # an address may hold a "." itself
        named = [f for f in mine if _named(f.get("object", ""), sent)]
        pool = named or mine
        effs = {f.get("effect") for f in pool}
        v = {"phrase": phrase, "family": fam, "clause": clause.strip()[:200], "tools": [f["tool"] for f in pool][:6],
             "action": draftcheck.is_action(phrase, fam)}
        emails = [e.rstrip(".") for e in _EMAIL.findall(sent or "")]
        if "did" in effs:
            did = [f for f in pool if f.get("effect") == "did"]
            if emails and not named and all(_EMAIL.findall(f.get("object") or "") for f in did):
                v.update(verdict="wrong", named=emails[0], actual=did[0].get("object", ""))
            else:
                v["verdict"] = "true"
        elif effs & set(NEVER_DONE) and _checked_after(pool, facts):
            v["verdict"] = "true"              # cut off, then LOOKED UP by a read of the same kind: the model checked
            v["checked"] = True
        elif "ambiguous" in effs:
            v["verdict"] = "unknown"
        elif "stopped" in effs:
            v["verdict"] = "stopped"
        elif "card" in effs:
            v["verdict"] = "card"
        elif "failed" in effs:
            v["verdict"] = "failed"
        else:
            v["verdict"] = "none"
        out.append(v)
    STATS["checked"] += len(out)
    return out


def _excused(v: dict, state: dict, conv: str, since, tools_re) -> bool:
    """`none` / `card` / `failed` backed by EARLIER facts (the job's earlier rounds, a true report of earlier work)."""
    from . import draftcheck
    if v["verdict"] not in ("none", "card", "failed"):
        return False
    if v["verdict"] != "failed" and since is not None and not draftcheck.nothing_ran_in_job(conv, since):
        return True                       # an earlier round of this job did it; this round only reported
    report = (state.get("actor") == "wake") or bool(draftcheck._STATUS_ASK.search(str(state.get("request") or "")))
    return bool(conv and (report or draftcheck._PAST.search(v.get("clause") or ""))
                and draftcheck.ran_before(conv, tools_re))


def claim_check(state: dict, text: str, facts: list[dict], conv: str = "", since=None, plain: bool = False,
                stopped: bool = False) -> tuple[str, list[dict], str]:
    """The facts-based twin of draftcheck.fake_done (same state counters: fake_done / false_action / correct /
    promise_nudged). Returns (nudge, verdicts, kind). `plain` = the parity 5b rule (only ACTION claims are sent back);
    `stopped` = she stopped the run: nothing is sent back, a false action claim gets the honest note."""
    from . import draftcheck
    if draftcheck._ALREADY_HONEST.search(text or ""):
        return "", [], "honest"
    if not stopped and draftcheck._PROMISE_REMIND.search(text or "") and not state.get("promise_nudged") \
            and not any(str(f.get("tool") or "").startswith(("create_reminder", "reminder"))
                        and f.get("effect") in ("did", "card") for f in facts or []):
        state["promise_nudged"] = True
        return draftcheck.NUDGE_PROMISE, [], "reminder_promise"
    vs = verdicts(text, facts)
    bad = []
    for v in vs:
        if v["verdict"] == "true":
            STATS["true"] += 1
            continue
        _f, tools_re = draftcheck.family_of(v["phrase"], v["clause"])
        if _excused(v, state, conv, since, tools_re):
            v["excused"] = True
            STATS["true"] += 1
            continue
        bad.append(v)
    if not bad:
        return "", vs, "true" if vs else "no_claim"
    STATS["false"] += 1
    act = any(v["action"] for v in bad)
    if plain and not act:
        return "", vs, "dropped"          # parity 5b: a claim that is not an action stands as written
    if stopped:
        if act and not state.get("correct"):
            worst = {v["verdict"] for v in bad}
            state["correct"] = (SAID_UNKNOWN if worst & {"unknown", "stopped"} else
                                draftcheck.SAID_CARD_EN if worst == {"card"} else
                                SAID_FAILED if "failed" in worst else draftcheck.SAID_EN)
            STATS["noted"] += 1
        return "", vs, "noted_stopped"
    state["false_action"] = act
    seen = state.get("fake_done", 0) + 1
    state["fake_done"] = seen
    worst = {v["verdict"] for v in bad}
    what = ", ".join(dict.fromkeys(v["phrase"] for v in bad))[:120]
    tools = ", ".join(dict.fromkeys(t for v in bad for t in v["tools"]))[:120] or "none"
    if seen == 1:
        if worst & {"unknown", "stopped"}:
            return NUDGE_UNKNOWN.format(what=what, tools=tools), vs, "unknown"
        if "wrong" in worst:
            w = next(v for v in bad if v["verdict"] == "wrong")
            return NUDGE_WRONG.format(named=w.get("named", "?"), actual=w.get("actual", "?")), vs, "wrong"
        if "failed" in worst:
            return NUDGE_FAILED.format(what=what, tools=tools), vs, "failed"
        if worst == {"card"}:
            return draftcheck.NUDGE_CARD, vs, "card"
        if any(f.get("effect") == "did" for f in facts or []):
            return draftcheck.NUDGE_PART.format(what=what), vs, "part"
        return draftcheck.NUDGE, vs, "none"
    if seen == 2 and not state.get("correct"):
        if state.get("answer_only") and not act:
            return "", vs, "dropped"
        state["correct"] = (SAID_UNKNOWN if worst & {"unknown", "stopped"} else
                            draftcheck.SAID_CARD_EN if worst == {"card"} else
                            SAID_FAILED if "failed" in worst else draftcheck.said_line(text))
        STATS["noted"] += 1
        return "", vs, "noted"
    return "", vs, "noted"


def left_note(facts: list[dict]) -> str:
    """What stays open after the turn because a doing step's outcome is unknown (never reported as done): a G1
    ambiguous / timed-out send with no later success of the same tool."""
    open_ = []
    for i, f in enumerate(facts or []):
        if f.get("effect") != "ambiguous":
            continue
        later = any(g.get("tool") == f.get("tool") and g.get("effect") in DONE_LIKE for g in (facts or [])[i + 1:])
        if not later:
            open_.append(f.get("tool") or "?")
    if not open_:
        return ""
    return ("the outcome of " + ", ".join(dict.fromkeys(open_)) + " is unknown (it was cut off) - check before "
            "trying again")


# ---------------------------------------------------------------- the decision

class Judge:
    """The graph check node's one decision about an answer: stand, or send the model back (and why). Lives on the
    santosh _Turn (`t.judge`) for the life of the turn; its lists / dict are the ones checkpointed by turngraph."""

    def __init__(self, t, facts: list, decisions: list, used: dict, stopped=None):
        self.t = t
        self.facts = facts
        self.decisions = decisions
        self.used = used
        self.last: dict | None = None
        self._stopped = stopped or (lambda: False)

    # -- the budget
    def left(self, kind: str) -> bool:
        return self.used.get(kind, 0) < CAPS.get(kind, 1) and sum(self.used.values()) < TOTAL

    def take(self, kind: str, why: str, **extra) -> bool:
        """Spend one 'send back' of this kind; False (and the decision says so) when the budget is spent."""
        if not self.left(kind):
            STATS["budget_spent"] += 1
            self._record("stand", f"{kind} budget spent ({self.used.get(kind, 0)}/{CAPS.get(kind, 1)}, "
                                  f"total {sum(self.used.values())}/{TOTAL}) - the answer stands", **extra)
            return False
        self.used[kind] = self.used.get(kind, 0) + 1
        STATS["nudged"] += 1
        self._record(kind, why, back=True, **extra)
        return True

    def _record(self, kind: str, why: str, back: bool = False, **extra) -> None:
        d = {"kind": kind, "why": why, "back": back, "step": int(getattr(self.t, "ran_steps", 0) or 0)}
        d.update({k: v for k, v in extra.items() if v not in (None, "", [])})
        self.last = d
        self.decisions.append(d)
        del self.decisions[:-30]

    def _since(self):
        from . import santosh as S
        st, conv = self.t.state, self.t.conversation_id
        g0 = st.get("goal") or S._goal_now(conv, self.t.settings)
        if g0 and g0.get("id"):
            from . import goal as _g
            return _g.started_at(g0["id"])
        return None

    def _claims(self, text: str, plain: bool) -> str:
        t = self.t
        if not t.settings.draft_check:
            return ""
        stopped = bool(self._stopped() or t.state["breaker"].stopped or t.state.get("halted"))
        nudge, vs, kind = claim_check(t.state, text, self.facts, t.conversation_id, self._since(), plain=plain,
                                      stopped=stopped)
        brief = [{k: v[k] for k in ("phrase", "verdict", "tools") if k in v} for v in vs][:8]
        if not nudge:
            if kind in ("noted", "noted_stopped"):
                self._record("note", "a false claim stayed after its one correction: the honest note is added",
                             claims=brief)
            elif vs:
                self._record("claims", f"claims judged against the turn's facts: {kind}", claims=brief)
            return ""
        budget = "reminder_promise" if kind == "reminder_promise" else "claim"
        why = ("a reminder was promised but no reminder is set" if kind == "reminder_promise" else
               f"the answer claims work the facts do not show ({kind})")
        return nudge if self.take(budget, why, claims=brief) else ""

    async def plain(self, text: str) -> str:
        """parity 5b: before the answer is shown (in place of santosh._plain_check)."""
        from . import santosh as S
        self.last = None
        n = self._claims(text, plain=True)
        if n:
            return n
        if self.t.state.get("correct"):
            return ""
        rest = S._plain_rest(self.t.state, text, self.t.settings)
        if rest and not self.take("done_failed", "every tool of the turn failed and the answer claims an action"):
            return ""
        return rest

    async def final(self, text: str) -> str:
        """After the answer is shown: the claims (non-plain mode), the self-check, the open plan, the promise."""
        from . import santosh as S
        from . import aage as _aage
        t = self.t
        nudge = ""
        if not S.plain_loop_on(t.settings):
            nudge = self._claims(text, plain=False)
            if not nudge and sum(self.used.values()) < TOTAL:
                nudge = await S._pakka_rest(t.state, text, t.settings, t.ran_tools, t.conversation_id)
                if nudge and not self.take("self_check", "the self-check found the task not finished"):
                    nudge = ""
        if not nudge and self.left("plan"):
            nudge = S._goal_nudge(t, text)
            if nudge:
                g = t.state.get("goal") or {}
                from . import goal as _goal
                nl = len(_goal.steps_left(g)) if g else 0
                self.take("plan", f"the kaam_plan has {nl} open step(s)")
        if not nudge and self.left("promise"):
            nudge = S._promise_nudge(t, text)
            if nudge:
                self.take("promise", "the answer only promises more work and no tool ran after it")
        elif not nudge and _aage.promised(text):
            self._record("stand", "the answer still only promises work, but the promise budget is spent")
        if not nudge and (self.last is None or self.last.get("back")):
            self._record("stand", "the answer stands: no claim the facts contradict, no open plan step, no promise")
        return nudge
