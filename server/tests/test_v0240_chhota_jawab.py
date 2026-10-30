"""v0.240 CHHOTA JAWAB (owner: "IT GIVE HUGE REPLY FOR EVERY SMALL WORK IN BACKEND -- EVERY MINUE DETAILS ---
IT MUST WORK ON BACKGOUD AND ON CHAT SCREEN IT MUST SHOW JUST A SMALL PERFECT HUMAN UNDERSTANDABLE [line]
PERFECLY LIKE CLAUDE DOES").

The detail was never missing - it was DOUBLE. The four-part report already renders on her card (phone _Report,
console goalReport), and v0.228 ALSO ordered the model to write those same four parts as its chat answer, plus a
line after every finished step, plus a progress line every 3 silent rounds. These tests pin the chat space back
to one short human line, and pin that nothing was lost from the card.
"""
import asyncio
from pathlib import Path

from app.agent import goal as G
from app.agent import replystyle as R
from app.config import get_settings
from tests.test_bazar import bz  # noqa: F401  (fresh DB + a real conversation)
from tests.test_v0186_long_goal import gz  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


def _run(ctx, **kw):
    from app.agent.goal_tools import kaam_plan
    return asyncio.run(kaam_plan(ctx, **kw))


def _ctx(conv):
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id=conv)


def _finish_out(conv):
    ctx = _ctx(conv)
    _run(ctx, action="set", goal="teen bill banao", steps=["bill 1", "bill 2", "bill 3"])
    for n in (1, 2, 3):
        _run(ctx, action="step", n=n, state="done", text=f"B-000{n} ban gaya")
    return _run(ctx, action="finish", outcome="done", made=["https://x.test/b1.pdf"])


def test_finish_no_longer_orders_the_four_part_reply(gz):  # noqa: F811
    out = _finish_out(gz["conv"])
    note = out["note"]
    # the old order is gone
    assert "chaar hisson mein do" not in note
    # and the new one forbids every shape of the dump, by name
    for ban in ("Bullet list", "Kya hua", "Kya bana", "Kya baaki", "dohraao mat"):
        assert ban in note, ban
    assert "EK chhoti insaani line" in note and "ek ya do vaakya" in note


def test_the_report_text_is_handed_over_as_what_she_already_sees(gz):  # noqa: F811
    out = _finish_out(gz["conv"])
    # renamed: not a template called "report", but "what the card shows"
    assert "report" not in out
    assert "card_shows" in out and "✅ Kya hua" in out["card_shows"]
    assert "CARD par pehle se dikh rahi hai" in out["note"]


def test_nothing_is_lost_from_the_card(gz):  # noqa: F811
    """The four parts still exist in full - the card is where the detail belongs."""
    conv = gz["conv"]
    v = G.set_goal("default", conv, "do kaam", ["pehla", "doosra"], origin="owner")
    G.mark_step("default", v["id"], 1, "done", note="ho gaya")
    out = G.finish("default", v["id"], "blocked_on_her", reason="aapka OTP chahiye", made=["https://x.test/f.pdf"])
    rep = out["report"]
    assert rep["hua"] and "pehla" in rep["hua"][0]        # done steps = what happened
    assert "https://x.test/f.pdf" in rep["bana"]          # links = what was made
    assert any("doosra" in x for x in rep["baaki"])       # not-done steps = what is left
    assert rep["aapka"]                                   # her part
    # and the card's own text still renders all four (the phone / console read this dict)
    txt = G.report_text(rep)
    for part in ("✅ Kya hua", "📎 Kya bana", "⏳ Kya baaki hai", "👉 Aapko kya karna hai"):
        assert part in txt, part


# ---------------------------------------------------------------- per-step silence

def test_a_finished_step_asks_for_the_finding_not_a_dump(gz):  # noqa: F811
    """v0.257 reversed v0.240's silence: Claude writes a line per step. What stays banned is the DUMP."""
    ctx = _ctx(gz["conv"])
    _run(ctx, action="set", goal="paanch kaam", steps=[f"kaam {i}" for i in range(1, 6)])
    out = _run(ctx, action="step", n=1, state="done", text="ho gaya")
    note = out["note"]
    assert "chat mein iska koi line mat likho" not in note       # the v0.240 silence is gone
    assert "is step se jo asli cheez mili" in note               # ...replaced by the finding
    assert "koi bullet ya heading nahi" in note                  # the dump stays banned
    assert "agla tool" in note


# ---------------------------------------------------------------- the progress line: rare, short, capped

def test_narration_keeps_claudes_cadence_by_default():
    """v0.240 set 8 / 2, which the owner read as silence ("HOOLA DIRECTLY LOADS THE RESULT"). Claude writes one
    line per tool group, so v0.257 is 1 / 6 - still capped, so a 40-step job cannot produce 40 lines."""
    st = get_settings()
    assert st.agent_narrate_every == 1
    assert st.agent_narrate_max == 6


def test_narrate_text_asks_for_the_real_finding_plus_what_is_next():
    """v0.240 forbade numbers and links, which left the line empty filler. Claude's line IS the number."""
    n = G.NARRATE
    # v0.268 rewrote this ask into the measured two halves; the demand for the REAL figure only got stronger
    assert "do vaakya" in n
    assert "asli number / id / naam / link" in n and "banaya hua nahi" in n
    assert "AB KYA" in n and "KYA MILA" in n                     # what it found + what it is doing now
    assert "koi number ya link nahi" not in n                    # the v0.240 ban is still gone
    assert "Bina number wali line bekaar hai" in n               # ...and the opposite is now demanded
    for ban in ("bullet, heading, emoji",):
        assert ban in n, ban
    assert "kaam ab POORA ho gaya hai to yeh line mat likho" in n   # never filler right before the answer
    # the true facts the tools returned ride into the ask (app/agent/say.py), never invented
    with_fact = G.narrate_line(["12 naye mails aaye", "site v0.256.0 par hai"])
    assert "12 naye mails aaye" in with_fact and "naya mat banao" in with_fact
    assert G.narrate_line([]) == n and G.narrate_line(None) == n


def test_the_loop_stops_narrating_after_the_cap():
    """A 40-step job can never produce 13 progress lines: the cap holds however long it runs."""
    asked = []
    state = {"goal": {"id": "g1"}, "quiet": 0, "narrated": 0}
    settings = get_settings()

    # drive the exact branch the loop runs, 60 silent rounds in a row
    for _ in range(60):
        blocks, results = [{"type": "tool_use", "name": "web_search"}], []
        spoke = any(b.get("type") == "text" and (b.get("text") or "").strip() for b in blocks)
        state["quiet"] = 0 if spoke else state.get("quiet", 0) + 1
        every = int(getattr(settings, "agent_narrate_every", 1) or 0)
        cap = int(getattr(settings, "agent_narrate_max", 6) or 0)
        if every and state["quiet"] >= every and state.get("narrated", 0) < cap:
            state["quiet"] = 0
            state["narrated"] = state.get("narrated", 0) + 1
            results.append({"type": "text", "text": G.NARRATE})
        asked += [r for r in results if r.get("text") == G.NARRATE]
    assert len(asked) == 6, f"narration must stop at the cap, got {len(asked)}"
    # and the real loop carries the same cap (source pin)
    txt = (ROOT / "server/app/agent/santosh.py").read_text()
    assert "agent_narrate_max" in txt and 'state.get("narrated", 0) < cap' in txt


# ---------------------------------------------------------------- the rulebook itself

def test_the_rulebook_demands_a_short_work_reply_on_both_surfaces():
    c = R.CHAT
    assert "Results of work, the short way" in c
    assert "one or two sentences" in c
    for ban in ("never repeat them in the reply", "never a bullet list of the steps you ran",
                "Kya hua / Kya bana / Kya baaki"):
        assert ban in c, ban
    assert "A twenty-step job gets the same short line as a one-step job" in c
    # the old wording that invited the dump is gone
    assert "say what was really done with the real details from the tool" not in c
    # a call gets the same discipline
    v = R.VOICE
    assert "one short spoken line" in v and "never every number" in v
    # and the rules still carry no braces (voice.PERSONA is .format()ed)
    for s in (R.CHAT, R.QUICK, R.VOICE):
        assert "{" not in s and "}" not in s


def test_the_rulebook_still_rides_in_the_prompt():
    from app.agent import prompts
    assert "Results of work, the short way" in prompts.SYSTEM
    from app.agent.admit import CORE_FAMILIES
    assert "Results of work, the short way" in prompts.system_text(CORE_FAMILIES)   # core: on every turn


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.271.0"
