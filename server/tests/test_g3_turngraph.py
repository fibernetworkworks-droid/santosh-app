"""G3 of docs/LANGGRAPH_TURN_PLAN.md: done-truth from the turn's FACTS + the nudges in the graph's check node.

Fake brain / fake tools in the style of test_g0 / g1 / g2. With `chat_graph` on, whether an answer may say "sent",
"booked", "done" is judged against what the turn's tools REALLY did (agent/turnfacts.py: the call record, the
tool_result, the G1 ledger row, draftcheck.effect on the result) and every "send the model back to work" decision is
made in one place with one budget and written into the checkpoint. With the switch off the old loop runs unchanged.

Most turns run in the production mode (CHAT_PLAIN_LOOP + CHAT_ANSWER_ONLY on); one runs in the old non-plain mode."""
import asyncio
import json
import time

import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_g0_turngraph import Scripted, _new_conv, _rows, _settings, tu, txt

PROD = {"CHAT_PLAIN_LOOP": "true", "CHAT_ANSWER_ONLY": "true", "CHAT_GRAPH_KEEP_FINISHED": "true"}


class Tools:
    """name -> the result dict, or an Exception to raise."""

    def __init__(self, answers=None, real=None):
        self.answers = dict(answers or {})
        self.count: dict[str, int] = {}
        self.real = real

    async def dispatch(self, name, args, ctx):
        self.count[name] = self.count.get(name, 0) + 1
        if name == "kaam_plan" and self.real is not None:
            return await self.real(name, args, ctx)
        a = self.answers.get(name, {"ok": True, "tool": name})
        if isinstance(a, Exception):
            raise a
        return a


def _go(monkeypatch, graph, script, ask, answers=None, extra=None, real_plan=False):
    _settings(monkeypatch, graph, {**PROD, **(extra or {})})
    from app import chats
    from app.agent import run_turn, santosh, set_client
    monkeypatch.setattr(chats, "enabled", lambda: False)
    tools = Tools(answers, real=santosh.dispatch if real_plan else None)
    monkeypatch.setattr(santosh, "dispatch", tools.dispatch)
    client = Scripted(list(script))
    sent = []
    orig = client._create

    async def create(**kw):
        sent.append(json.dumps(kw.get("messages"), ensure_ascii=False, default=str))
        return await orig(**kw)
    client.messages.create = create
    set_client(client)
    conv = _new_conv()
    out = asyncio.run(asyncio.wait_for(run_turn(conv, ask, tenant_id="default"), 120))
    return {"out": out, "calls": client.calls, "sent": sent, "conv": conv, "tools": tools.count,
            "outcome": (santosh.LAST_OUTCOME.get(conv) or {}).get("outcome")}


def _cp(conv):
    from app.agent import turngraph
    from app.config import get_settings
    rows = asyncio.run(turngraph.checkpoints(get_settings(), conv))
    assert rows, "no checkpoint kept"
    return rows[0]["values"]


def _kinds(values, back=None):
    return [d["kind"] for d in values.get("decisions") or [] if back is None or bool(d.get("back")) == back]


DRAFT = {"ok": True, "status": "draft", "draft_id": "d_17", "to": "ravi@x.in"}
SENT = {"ok": True, "status": "sent", "message_id": "m_42", "to": "ravi@x.in"}


# ---------------------------------------------------------------- the facts and the verdicts (no model)

def test_facts_classify_what_really_happened(env):  # noqa: F811
    from app.agent import turnfacts as F
    blocks = [tu(1, "email_draft", to="ravi@x.in"), tu(2, "email_send", to="a@b.in"), tu(3, "list_reminders"),
              tu(4, "email_send", to="c@d.in"), tu(5, "email_send", to="e@f.in"), tu(6, "email_send", to="g@h.in"),
              tu(7, "create_booking", slot="9")]
    from app.agent import santosh as S
    k = S._key
    calls = [{"tool": "email_draft", "ok": True, "key": k("email_draft", {"to": "ravi@x.in"}),
              "result": json.dumps(DRAFT)},
             {"tool": "email_send", "ok": True, "key": k("email_send", {"to": "a@b.in"}), "result": json.dumps(SENT)},
             {"tool": "list_reminders", "ok": True, "key": k("list_reminders", {}), "result": "[]"},
             {"tool": "email_send", "ok": False, "error": "smtp down", "key": k("email_send", {"to": "c@d.in"})},
             {"tool": "email_send", "ok": False, "error": "outcome unknown after a restart",
              "key": k("email_send", {"to": "e@f.in"})},
             {"tool": "email_send", "ok": False, "error": "stopped by the owner", "key": k("email_send", {"to": "g@h.in"})},
             {"tool": "create_booking", "ok": False, "error": "timeout", "key": k("create_booking", {"slot": "9"})}]
    facts = F.step_facts(blocks, [], calls, 3)
    assert [f["effect"] for f in facts] == ["card", "did", "read", "failed", "ambiguous", "stopped", "ambiguous"]
    assert facts[0]["object"] == "ravi@x.in" and facts[1]["step"] == 3
    # a tool that never ran (held by the breaker) did nothing; her Stop result / the ledger say "stopped" too
    held = F.step_facts([tu(9, "email_send", to="x@y.in")], [], [], 1)
    assert held[0]["effect"] == "skipped"
    led = F.step_facts([tu(8, "email_send")], [], [{"tool": "email_send", "ok": False, "error": "x",
                                                    "key": k("email_send", {})}], 1,
                       {"tu_8": {"state": "failed", "error_kind": "stopped"}})
    assert led[0]["effect"] == "stopped" and led[0]["ledger"] == "failed"


@pytest.mark.parametrize("effect,want", [("did", "true"), ("card", "card"), ("failed", "failed"),
                                         ("ambiguous", "unknown"), ("stopped", "stopped"), ("read", "none")])
def test_one_claim_many_verdicts(env, effect, want):  # noqa: F811
    from app.agent import turnfacts as F
    facts = [{"tool": "email_send" if effect != "read" else "email_check", "effect": effect, "object": "ravi@x.in"}]
    vs = F.verdicts("I've sent the email to Ravi.", facts)
    assert [v["verdict"] for v in vs] == [want]


def test_ambiguous_and_stopped_are_never_excused(env):  # noqa: F811
    from app.agent import turnfacts as F
    from app.agent.breaker import Breaker
    for eff in ("ambiguous", "stopped"):
        st = {"calls": [], "breaker": Breaker(), "request": "mail gaya kya?"}   # a status ask would excuse a none
        n, vs, kind = F.claim_check(st, "Haan, mail bhej diya tha.", [{"tool": "email_send", "effect": eff}], "c-none")
        assert kind == "unknown" and "UNKNOWN" in n, eff
        st2 = {"calls": [], "breaker": Breaker()}
        n2, _, kind2 = F.claim_check(st2, "I've sent the email.", [{"tool": "email_send", "effect": eff}], "",
                                     stopped=True)
        assert n2 == "" and kind2 == "noted_stopped" and st2["correct"] == F.SAID_UNKNOWN


def test_a_cut_off_send_that_was_then_checked_may_be_reported(env):  # noqa: F811
    from app.agent import turnfacts as F
    cut = {"tool": "email_send", "effect": "ambiguous"}
    assert F.verdicts("The email has been sent.", [cut])[0]["verdict"] == "unknown"
    looked = F.verdicts("The email has been sent.", [cut, {"tool": "email_check", "effect": "read"}])[0]
    assert looked["verdict"] == "true" and looked["checked"]
    before = F.verdicts("The email has been sent.", [{"tool": "email_check", "effect": "read"}, cut])[0]
    assert before["verdict"] == "unknown"                                      # a look BEFORE the cut proves nothing


def test_an_honest_negation_is_not_a_claim(env):  # noqa: F811
    from app.agent import turnfacts as F
    from app.agent.breaker import Breaker
    for text in ("I haven't sent anything - an email is sent only when you tap Send.",
                 "Nothing has been sent yet.", "Once you approve, the mail will be sent.",
                 "Please check the sent folder before I try again."):
        st = {"calls": [], "breaker": Breaker()}
        assert F.claim_check(st, text, [], "")[0] == "", text


def test_budget_caps(env):  # noqa: F811
    from app.agent import turnfacts as F

    class T:
        ran_steps = 1
    j = F.Judge(T(), [], [], {})
    assert [j.take("promise", "p") for _ in range(3)] == [True, True, False]
    assert j.last["kind"] == "stand" and "budget spent" in j.last["why"]
    assert [j.take("max_tokens", "m") for _ in range(9)].count(True) == F.CAPS["max_tokens"]
    j2 = F.Judge(T(), [], [], {k: v for k, v in F.CAPS.items()})
    assert not j2.left("claim")


# ---------------------------------------------------------------- whole turns

def test_mail_sent_after_only_a_draft_is_corrected(bz, monkeypatch):  # noqa: F811
    script = [[tu(1, "email_draft", to="ravi@x.in", subject="Bill")], txt("Mail bhej diya Ravi ko."),
              txt("The draft to Ravi is ready - it goes out only when you tap Send on the card.")]
    old = _go(monkeypatch, False, script, "ravi ko bill ka mail bhejo", {"email_draft": DRAFT})
    new = _go(monkeypatch, True, script, "ravi ko bill ka mail bhejo", {"email_draft": DRAFT})
    for r in (old, new):
        assert r["calls"] == 3 and r["out"].startswith("The draft to Ravi is ready")
        assert "CARD or DRAFT that waits for HER tap" in r["sent"][2]          # the same nudge words on both paths
    cp = _cp(new["conv"])
    assert cp["facts"][0]["effect"] == "card" and cp["facts"][0]["object"] == "ravi@x.in"
    first = next(d for d in cp["decisions"] if d.get("back"))
    assert first["kind"] == "claim" and first["claims"][0]["verdict"] == "card"
    assert cp["decision"]["back"] is False                                     # the honest answer stood
    assert cp["nudges"] == {"claim": 1}


def test_sent_after_a_real_send_stands(bz, monkeypatch):  # noqa: F811
    line = "I've sent the email to ravi@x.in."
    r = _go(monkeypatch, True, [[tu(1, "email_send", to="ravi@x.in")], txt(line)], "ravi ko mail bhejo",
            {"email_send": SENT})
    assert r["calls"] == 2 and r["out"] == line and r["outcome"] == "done"
    cp = _cp(r["conv"])
    assert cp["facts"][0]["effect"] == "did" and cp["nudges"] == {}
    assert cp["decision"]["kind"] == "claims" and cp["decision"]["claims"][0]["verdict"] == "true"


def test_sent_to_someone_else_is_corrected_on_the_graph_only(bz, monkeypatch):  # noqa: F811
    """The facts carry the object: the old regex check passes 'sent to asha@' after a send to ravi@."""
    script = [[tu(1, "email_send", to="ravi@x.in")], txt("I've sent the email to asha@y.in."),
              txt("The email went to ravi@x.in; Asha has not been sent anything yet.")]
    old = _go(monkeypatch, False, script, "mail bhejo", {"email_send": SENT})
    new = _go(monkeypatch, True, script, "mail bhejo", {"email_send": SENT})
    assert old["calls"] == 2 and old["out"] == "I've sent the email to asha@y.in."
    assert new["calls"] == 3 and "went to ravi@x.in" in new["out"]
    assert "the tool did it for ravi@x.in" in new["sent"][2]


def test_sent_after_a_failed_send_is_corrected(bz, monkeypatch):  # noqa: F811
    from app.agent.tools import ToolError
    script = [[tu(1, "email_send", to="ravi@x.in")], txt("I've sent the email to Ravi."),
              txt("The email to Ravi did not go through - the mail server refused it. Shall I try again?")]
    new = _go(monkeypatch, True, script, "ravi ko mail bhejo", {"email_send": ToolError("smtp refused")})
    assert new["calls"] == 3 and "did not go through" in new["out"]
    assert "FAILED this turn (email_send)" in new["sent"][2]
    cp = _cp(new["conv"])
    assert cp["facts"][0]["effect"] == "failed"
    assert next(d for d in cp["decisions"] if d.get("back"))["claims"][0]["verdict"] == "failed"
    # an {"ok": False} answer is a failure too (santosh.tool_failure), never a "did"
    new2 = _go(monkeypatch, True, script, "ravi ko mail bhejo", {"email_send": {"ok": False, "error": "quota"}})
    assert new2["calls"] == 3 and "FAILED this turn" in new2["sent"][2]


def test_old_non_plain_mode_judged_by_facts_too(bz, monkeypatch):  # noqa: F811
    """CHAT_PLAIN_LOOP off (the after-answer checks): the same facts verdict, the honest note on a second false try."""
    extra = {"CHAT_PLAIN_LOOP": "false", "CHAT_ANSWER_ONLY": "false"}
    script = [[tu(1, "email_draft", to="ravi@x.in")], txt("Mail bhej diya Ravi ko."), txt("Mail bhej diya Ravi ko.")]
    new = _go(monkeypatch, True, script, "ravi ko mail bhejo", {"email_draft": DRAFT}, extra)
    assert new["calls"] == 3
    assert "CARD or DRAFT" in new["sent"][2]
    from app.agent import draftcheck
    shown = [d for r, d in _rows(new["conv"]) if r == "assistant" and d]
    assert draftcheck.SAID_CARD_EN in shown                                    # said after the words she read
    assert "note" in _kinds(_cp(new["conv"]))


def test_ambiguous_send_after_a_restart_is_never_done(bz, monkeypatch):  # noqa: F811
    from tests.test_g1_turngraph import _crash_and_resume, _last_reply
    from app.agent import santosh
    for k, v in PROD.items():
        monkeypatch.setenv(k, v)
    honest = "I cannot confirm the email to Ravi went out - please check the sent folder before I try again."
    script = [[tu(1, "email_send", to="ravi@x.in")], txt("Mail bhej diya Ravi ko."), txt(honest)]
    conv, rid, brain, tools, n = _crash_and_resume(monkeypatch, script, "ravi ko mail bhejo",
                                                   crash_tools=("email_send",))
    assert n == 1 and tools.count == {"email_send": 1}                         # never sent again
    assert "MAY ALREADY HAVE RUN" in brain.sent[1]
    assert "its outcome is UNKNOWN" in brain.sent[2]                          # the false 'bhej diya' was sent back
    assert _last_reply(conv) == honest
    lo = santosh.LAST_OUTCOME.get(conv) or {}
    assert lo.get("outcome") == "partial" and "unknown" in lo.get("left", "")  # never reported as done


def test_stopped_tool_is_never_done(bz, monkeypatch):  # noqa: F811
    from tests.test_g2_turngraph import HALT, Brain, _accept, _later, _owned
    from tests.test_g2_turngraph import Tools as SlowTools
    from tests.test_g2_turngraph import _setup as g2_setup
    from app.agent import santosh
    conv = _new_conv()
    brain = Brain({"ASKA": [[tu(1, "email_send", to="ravi@x.in")], txt("I've sent the email.")]})
    tools = SlowTools(slow={"email_send": 8})
    g2_setup(monkeypatch, True, brain, tools, PROD)
    rid = _accept(conv, "ASKA mail", "cs")

    async def go():
        return (await asyncio.gather(_owned(conv, rid, "ASKA mail"),
                                     _later(0.2, lambda: santosh.stop(conv), tools)))[0]
    t0 = time.monotonic()
    out = asyncio.run(asyncio.wait_for(go(), 60))
    assert time.monotonic() - t0 < 4 and out.startswith(HALT) and brain.calls == 1
    assert (santosh.LAST_OUTCOME.get(conv) or {}).get("outcome") == "stopped"
    cp = _cp(conv)
    assert cp.get("stopped") and cp["facts"][0]["effect"] == "stopped"
    santosh._stopped.discard(conv)


def test_a_promise_with_no_tool_goes_back_once_then_honest(bz, monkeypatch):  # noqa: F811
    script = [txt("Starting the build now."), txt("I have not started any build - shall I start one now?")]
    old = _go(monkeypatch, False, script, "where do i check that")
    new = _go(monkeypatch, True, script, "where do i check that")
    from app.agent import aage
    for r in (old, new):
        assert r["calls"] == 2 and r["out"].startswith("I have not started")
        assert aage.NUDGE[:60] in r["sent"][1]
    cp = _cp(new["conv"])
    assert _kinds(cp, back=True) == ["promise"] and cp["nudges"] == {"promise": 1}
    assert cp["decision"]["kind"] == "stand"


def test_promise_caps_are_respected(bz, monkeypatch):  # noqa: F811
    script = [txt("Starting the build now.")] * 4
    old = _go(monkeypatch, False, script, "build it")
    new = _go(monkeypatch, True, script, "build it")
    assert old["calls"] == new["calls"] == 3                                   # 2 promise nudges, then it stands
    cp = _cp(new["conv"])
    assert cp["nudges"] == {"promise": 2}
    assert "promise budget is spent" in cp["decision"]["why"]


def test_max_tokens_continue_is_in_the_budget(bz, monkeypatch):  # noqa: F811
    from app.agent import turnfacts as F
    script = [(txt(f"part {i}"), "max_tokens") for i in range(12)]
    new = _go(monkeypatch, True, script, "lamba likho")
    assert new["calls"] == F.CAPS["max_tokens"] + 1
    cp = _cp(new["conv"])
    assert cp["nudges"] == {"max_tokens": F.CAPS["max_tokens"]}
    assert any("max_tokens budget spent" in d["why"] for d in cp["decisions"])
    one = _go(monkeypatch, True, [(txt("Pehla hissa"), "max_tokens"), txt("aur doosra hissa.")], "lamba likho")
    assert one["calls"] == 2 and _kinds(_cp(one["conv"]), back=True) == ["max_tokens"]


def test_an_open_plan_step_at_the_end_is_nudged(bz, monkeypatch):  # noqa: F811
    script = [[tu(1, "kaam_plan", action="set", goal="Do kaam", steps=["pehla kaam", "doosra kaam"])],
              [tu(2, "kaam_plan", action="step", n=1, state="done")],
              txt("Step one is finished."),
              [tu(3, "kaam_plan", action="step", n=2, state="done")],
              [tu(4, "kaam_plan", action="finish", outcome="done", reason="both steps finished")],
              txt("Both steps are finished.")]
    old = _go(monkeypatch, False, script, "do kaam karo", real_plan=True)
    new = _go(monkeypatch, True, script, "do kaam karo", real_plan=True)
    for r in (old, new):
        assert r["calls"] == 6 and r["out"] == "Both steps are finished."
        assert "these steps are still left: 2. doosra kaam" in r["sent"][3]
    cp = _cp(new["conv"])
    plan = [d for d in cp["decisions"] if d["kind"] == "plan"]
    assert plan and "1 open step" in plan[0]["why"] and plan[0]["back"]
    assert all(f["effect"] == "read" for f in cp["facts"])                      # kaam_plan is bookkeeping, not doing


def test_a_pure_explainer_with_sent_in_a_negation_is_left_alone(bz, monkeypatch):  # noqa: F811
    line = ("An email is sent only when you tap Send on its card - I haven't sent anything, and nothing goes out "
            "without your tap.")
    for graph in (False, True):
        r = _go(monkeypatch, graph, [txt(line)], "email kaise jaata hai?")
        assert r["calls"] == 1 and r["out"] == line
    cp = _cp(r["conv"])
    assert cp["nudges"] == {} and not _kinds(cp, back=True)


def test_switch_off_never_makes_a_judge(bz, monkeypatch):  # noqa: F811
    from app.agent import santosh, turnfacts

    class Boom:
        def __init__(self, *a, **k):
            raise AssertionError("a G3 judge was made with chat_graph off")
    monkeypatch.setattr(turnfacts, "Judge", Boom)
    seen = []
    real = santosh._turn_after_model

    async def spy(t, *a, **k):
        seen.append(t.judge)
        return await real(t, *a, **k)
    monkeypatch.setattr(santosh, "_turn_after_model", spy)
    r = _go(monkeypatch, False, [[tu(1, "email_draft", to="ravi@x.in")], txt("Mail bhej diya."),
                                 txt("The draft is ready for your tap.")], "mail bhejo", {"email_draft": DRAFT})
    assert r["calls"] == 3 and seen and all(j is None for j in seen)
