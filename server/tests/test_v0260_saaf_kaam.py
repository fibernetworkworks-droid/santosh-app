"""v0.260 SAAF KAAM - four flaws the owner's own test run turned up on live v0.258 ("CHECK ALL RESULTS").

Her four prompts proved CHALTE CHALTE BOLO works: the 20-mails job wrote seven between-step lines, every one of
them carrying a real figure or id ("sirf 9 mails dikhe", "40 mails mile hain", "Do mails ke ids (env~9824,
env~9821)", "Ab 20 ke 20 mails mil gaye hain, env~9812 se env~9831 tak"). The same run exposed four things:

  1. `kaam_plan() got an unexpected keyword argument 'note'` killed a step mid-job. The TOOL'S OWN DESCRIPTION
     said "step (n, state, note)" while the code took `reason` and no `note` property existed at all.
  2. Raw backend errors were printed into her chat by pakka's try-another-way line - her "BULK BACKEND UNWANTED
     RESPONSES" in the literal sense.
  3. Two of the four replies came out in English although she had written Hinglish.
  4. Two final answers on a finished job: the real reply, then a second wake turn repeating it.

(3) and (4) are one chain: the wake's duplicate guard matched the job TITLE's words against the reply, so an
English reply to a Hinglish title never matched and the wake fired.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- 1. the tool lied to the model
def test_kaam_plan_description_names_a_parameter_that_exists():
    from app.agent.goal_tools import GOAL_TOOLS
    spec = [t for t in GOAL_TOOLS if t["name"] == "kaam_plan"][0]
    desc = spec["description"]
    props = spec["input_schema"]["properties"]
    assert "step (n, state done|failed|skipped|current, reason)" in desc
    assert "current, note)" not in desc                       # the parameter that never existed
    # every parameter the description names in its Actions line is really declared
    for named in ("goal", "steps", "n", "state", "reason", "text"):
        assert named in props, named


def test_kaam_plan_accepts_note_as_an_alias_and_never_crashes_again():
    """Belt and braces: the description is fixed, and a model that still guesses `note` must not kill her job."""
    import inspect
    from app.agent.goal_tools import kaam_plan
    sig = inspect.signature(kaam_plan)
    assert "note" in sig.parameters
    src = inspect.getsource(kaam_plan)
    assert "reason = reason or note" in src


def test_a_step_note_passed_either_way_lands_in_the_same_place(gz):  # noqa: F811
    import asyncio
    from app.agent.goal_tools import kaam_plan
    from app.agent.tools import Ctx
    ctx = Ctx(tenant_id="default", conversation_id=gz["conv"])
    run = lambda **kw: asyncio.run(kaam_plan(ctx, **kw))     # noqa: E731
    run(action="set", goal="Do kaam", steps=["pehla", "doosra"])
    out = run(action="step", n=1, state="done", note="note se aaya")      # the shape that used to raise TypeError
    assert isinstance(out, dict) and not out.get("error")
    # it lands exactly where `reason` would have: the step's own note on the card
    from app.agent import goal as G
    steps = G.show("default", out.get("goal_id") or "")["steps"]
    assert [x for x in steps if x["n"] == 1][0]["note"] == "note se aaya"


# ---------------------------------------------------------------- 2. no backend text in her chat
def test_the_try_another_way_line_carries_no_raw_error():
    src = (ROOT / "server/app/agent/pakka.py").read_text()
    assert 'say = "Yeh raasta nahi chala — ek doosra tareeka try karta hoon…"' in src
    assert 'say = f"Yeh raasta nahi chala ({reason})' not in src
    # the detail is NOT lost - the step chip still carries it, one click away
    agent = (ROOT / "server/app/agent/santosh.py").read_text()
    assert '"state": "error"' in agent and '"detail": str(e)[:300]' in agent


# ---------------------------------------------------------------- 3. her language, first
def test_the_language_rule_is_the_first_rule_she_gets():
    from app.agent import replystyle as R
    head = R.CHAT.split("How you understand her")[0]
    assert "Her language, first and always" in head
    assert "Answer in the language and script SHE used" in head
    assert "for the lines you write while you work" in head   # the narration lines too, not only the final answer
    for t in (R.CHAT, R.QUICK, R.VOICE):
        assert "{" not in t and "}" not in t                  # voice.PERSONA is .format()ed


# ---------------------------------------------------------------- 4. one answer, not two
def test_a_finished_job_does_not_report_twice_when_the_turn_already_did():
    """The old guard compared the TITLE's words with the reply, so a paraphrase - or another language - slipped
    through and she got the answer twice. The new one asks WHEN, so it holds in any language."""
    import inspect
    from app import kaam_followup as K
    assert callable(K._answered_since)
    src = inspect.getsource(K._answered_since)
    assert "in_history" in src                                # progress notes are not an answer
    assert "len(text) >= 40" in src                           # nor is a one-word ack
    tick = (ROOT / "server/app/kaam_followup.py").read_text()
    assert '_recent_said(conv, title) or _answered_since(conv, getattr(r, "created_at", None))' in tick
    assert K._answered_since("missing-conv", None) is False   # no timestamp = never block the news


def test_the_news_is_never_lost_when_nothing_answered():
    """The guard must not swallow a real background result: an empty chat still gets the wake."""
    from app import kaam_followup as K
    from app.db import now
    assert K._answered_since("conv-that-does-not-exist", now()) is False


# ---------------------------------------------------------------- what v0.258 won is still there
def test_the_between_step_narration_still_stands():
    from app.agent import goal as G
    from app.config import get_settings
    st = get_settings()
    assert st.agent_narrate_every == 1 and st.agent_narrate_max == 6
    assert "asli number / id / naam / link" in G.NARRATE
    assert "12 naye mails aaye" in G.narrate_line(["12 naye mails aaye"])
    p = (ROOT / "server/app/agent/prompts.py").read_text()
    assert "CHALTE CHALTE BOLO" in p and "bade kaam se PEHLE ek vaakya" in p


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.330.0"
    assert "0.330.0+370" in (ROOT / "pubspec.yaml").read_text()


from tests.test_bazar import bz  # noqa: E402,F401
from tests.test_v0186_long_goal import gz  # noqa: E402,F401
