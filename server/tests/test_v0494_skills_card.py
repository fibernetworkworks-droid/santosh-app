"""CLAUDE SKILLS P5 - the SKILLS card + the reachability fix it found.

FOUND BY THE CARD: `skill_manage` lives in the non-core `skill` family, so on an ordinary turn it was NOT in the
model's tool list, while the prompt told the model to "skill_manage read the skill before you follow it"
(v0.477 onward). The fix admits that one tool when a skill matches the ask (coder.inject.admit_tool, called
from the agent loop). Pins: (1) the gap, before and after; (2) no match / switch off = no extra tool; (3) the
loop really calls it; (4) the free card's numbers; (5) the live scorer on fake turns (opened / file / honesty /
saved-without-yes / unrelated ask); (6) the spy restores the store; (7) the CLI is wired.
"""
import asyncio
import inspect

import pytest

from app.coder import inject, skill_packs, skills_store, store
from app.quality import skills_asks, skillscard

T = "__skillcard__"


@pytest.fixture()
def desk(env, monkeypatch, tmp_path):
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path / "quality"))
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    skills_store.reset_for_tests()
    skillscard._seed(T)
    yield monkeypatch
    skills_store.reset_for_tests()
    get_settings.cache_clear()


def _plan(text):
    from app.agent import admit
    from app.config import get_settings
    return admit.plan_for(text, get_settings())


def _names(plan):
    return {t["name"] for t in plan.specs()}


# ---------------------------------------------------------------- (1)+(2) the gap and the fix

def test_gap_before_and_fixed_after(desk):
    ask = "write this week's status report for my team"
    plan = _plan(ask)
    assert "skill_manage" not in _names(plan)                  # the gap: matched skill, tool not callable
    assert inject.admit_tool(plan, T, ask) is True
    assert "skill_manage" in _names(plan)


def test_no_match_or_switch_off_adds_nothing(desk):
    plan = _plan("aaj ka mausam kaisa rehega Akola mein?")
    assert inject.admit_tool(plan, T, "aaj ka mausam kaisa rehega Akola mein?") is False
    assert "skill_manage" not in _names(plan)
    plan2 = _plan("write this week's status report for my team")
    desk.setenv("CODER_SKILLS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert inject.admit_tool(plan2, T, "write this week's status report for my team") is False
    assert inject.admit_tool(None, T, "status report") is False
    assert inject.admit_tool(plan2, T, "") is False


# ---------------------------------------------------------------- (3) the loop calls it

def test_agent_loop_calls_admit_tool():
    from app.agent import santosh
    src = inspect.getsource(santosh)
    assert "inject.admit_tool" in src
    assert src.index("inject.admit_tool") > src.index("ctx.admit = adm") - 1500     # next to the admission block


# ---------------------------------------------------------------- (4) the free card

def test_free_card_numbers(desk):
    card = skillscard.free_card(tenant=T)
    assert card["pack_missing"] == []
    assert card["skills_on_tenant"] == len(skill_packs.seed_files()) + len(skill_packs.byox_files()) + len(skill_packs.prog_files()) + len(skill_packs.sp_files()) + len(skill_packs.fe_files()) + len(skill_packs.cs_files()) + len(skill_packs.mg_files()) + len(skill_packs.bd_files()) + len(skill_packs.cr_files()) + len(skill_packs.th_files()) + len(skill_packs.claude_dirs())
    assert (card["in_top2"], card["pos"]) == (10, 10)
    assert card["tool_in_view"] == 10 and card["files_ok"] == 10
    assert (card["neg_clean"], card["neg"]) == (4, 4)
    text = "\n".join(skillscard.lines(card))
    assert "needs --live" in text and "10/10" in text


def test_every_ask_names_a_real_pack_skill_and_real_files(desk):
    have = {s["name"] for s in skills_store.listing(T)}
    for a in skills_asks.ASKS:
        if a["kind"] == "pos":
            assert a["skill"] in skills_asks.PACK and a["skill"] in have, a["id"]
            for rel in a.get("reads", []):
                skills_store.read_file(T, a["skill"], rel)        # raises if the file does not exist
    assert {a["skill"] for a in skills_asks.ASKS if a["kind"] == "pos"} == set(skills_asks.PACK)
    assert len({a["id"] for a in skills_asks.ASKS}) == len(skills_asks.ASKS)


# ---------------------------------------------------------------- (5) the live scorer on fake turns

def _ask(i):
    return next(a for a in skills_asks.ASKS if a["id"] == i)


def test_score_text_markers_and_honesty():
    ic = _ask("ic-3p")
    assert skillscard._score_text(ic, "Progress: 12 demos. Plans: 5 deals. Problems: 2 reps.")["text_ok"]
    assert not skillscard._score_text(ic, "Here is a long update about the team.")["text_ok"]
    wt = _ask("wt-honest")
    claimed = skillscard._score_text(wt, "Maine screenshot liya, test pass hua, sab theek hai.")
    assert claimed["honest"] is False and not claimed["text_ok"]
    owned = skillscard._score_text(wt, "Main script abhi nahi chala sakta, par page ka screenshot dekh ke bata sakta hoon.")
    assert owned["honest"] is True and owned["text_ok"]


def _fake_turn(monkeypatch, actions, reply):
    from app.agent import santosh

    async def run_turn(conv, text, tenant_id=None, **kw):
        for fn, args in actions:
            getattr(skills_store, fn)(tenant_id, *args)
        return reply
    monkeypatch.setattr(santosh, "run_turn", run_turn)


def test_live_scorer_right_when_skill_and_file_opened(desk):
    _fake_turn(desk, [("read", ("internal-comms",)), ("read_file", ("internal-comms", "examples/3p-updates.md"))],
               "Progress: 12 demos. Plans: 5 deals. Problems: 2 reps left.")
    row = asyncio.run(skillscard._one(_ask("ic-3p"), T))
    assert row["right"] and row["opened"] and row["files_ok"], row


def test_live_scorer_catches_unopened_skill_and_missing_file(desk):
    _fake_turn(desk, [], "Progress: 12 demos. Plans: 5 deals. Problems: 2 reps left.")
    row = asyncio.run(skillscard._one(_ask("ic-3p"), T))
    assert not row["right"] and any("never opened" in m for m in row["misses"])
    _fake_turn(desk, [("read", ("internal-comms",))], "Progress. Plans. Problems.")
    row2 = asyncio.run(skillscard._one(_ask("ic-3p"), T))
    assert not row2["right"] and any("examples/3p-updates.md" in m for m in row2["misses"])


def test_live_scorer_flags_save_without_yes_and_unrelated_open(desk):
    _fake_turn(desk, [("read", ("skill-maker",)), ("create", ("stock-count", "Weekly stock count", "1. count"))],
               "Theek hai, skill ban gaya. Steps: ... haan?")
    row = asyncio.run(skillscard._one(_ask("sm-yes-first"), T))
    assert not row["right"] and any("before the user said yes" in m for m in row["misses"])
    _fake_turn(desk, [("read", ("frontend-design",))], "Invoice ready.")
    neg = asyncio.run(skillscard._one(_ask("neg-gst"), T))
    assert not neg["right"] and any("unrelated ask" in m for m in neg["misses"])
    _fake_turn(desk, [], "Invoice ready.")
    assert asyncio.run(skillscard._one(_ask("neg-gst"), T))["right"]


def test_live_card_without_a_model_is_errors_not_a_pass(desk):
    from app.agent import santosh

    async def boom(*a, **k):
        raise RuntimeError("no model key")
    desk.setattr(santosh, "run_turn", boom)
    card = asyncio.run(skillscard.live_card(skillscard.pick(limit=4), tenant=T))
    assert card["answered"] == 0 and card["right"] == 0 and card["errors"] == 3          # stops after 3 dead turns
    assert "ERROR" in "\n".join(skillscard.lines(card))


# ---------------------------------------------------------------- (6)+(7) spy and CLI

def test_spy_restores_the_store_and_records():
    orig = (skills_store.read, skills_store.read_file, skills_store.create)
    with skillscard.spy() as seen:
        assert skills_store.read is not orig[0]
    assert (skills_store.read, skills_store.read_file, skills_store.create) == orig and seen["read"] == []


def test_cli_wired():
    from app.quality import __main__ as M
    src = inspect.getsource(M)
    assert 'argv[0] == "skills"' in src and "_skillscard" in src
    assert [a["id"] for a in skillscard.pick(kind="neg")] == ["neg-gst", "neg-wa", "neg-flask", "neg-chat"]
