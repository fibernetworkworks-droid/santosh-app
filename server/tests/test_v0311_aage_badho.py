"""v0.311 AAGE BADHO + SAHI AUZAAR 2 (owner: "DO EXTREEM DEEP RESEARCH HOW CLAUDE DO LONG TASK ... ALSO CHECK WHY
HOOLA IS FAILING FOR EVERY LONG TASK", then "HOOLA NOT ABLE TO PICK RIGHT TOOL", then "GO").

The RCA is docs/LONG_TASK_RCA.md. The first two tests here were the REPRODUCTIONS on v0.310 - they failed there:
  1. a text-only progress line ("ab doosra hissa dekh raha hoon") ended the job after one tool;
  2. a research job doing 4 parallel searches a round (every call fine) was stopped at round 8 as "atak gaya".
"""
import asyncio
import time

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


# ---------------------------------------------------------------- 1. a promise is not a finished job
def test_a_promise_line_no_longer_ends_the_job(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "kaam_status", q="pehla")], "tool_use"),
        ([txt("Status mein 3 kaam mile. Ab doosra hissa dekh raha hoon.")], "end_turn"),   # v0.310 stopped HERE
        ([tu(2, "kaam_status", q="doosra")], "tool_use"),
        ([tu(3, "kaam_status", q="teesra")], "tool_use"),
        ([txt("Teeno check ho gaye: sab theek hai.")], "end_turn"),
    ]))
    from app.agent import aage
    from app.agent.santosh import run_turn
    before = aage.STATS["nudged"]
    out = asyncio.run(run_turn(conv, "teen cheezein ek ek karke check karo aur phir report do", tenant_id="default"))
    assert brain.script == [] and len(brain.seen) == 5          # every tool ran
    assert "Teeno check ho gaye" in out
    assert aage.STATS["nudged"] == before + 1


def test_a_promise_nudge_is_capped(gz, monkeypatch):  # noqa: F811
    """A model that keeps promising cannot loop: two nudges a turn, then its words stand."""
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "kaam_status", q="a")], "tool_use"),
        ([txt("Ab dekh raha hoon.")], "end_turn"),
        ([txt("Ab dekh raha hoon.")], "end_turn"),
        ([txt("Ab dekh raha hoon.")], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "dekho", tenant_id="default"))
    assert brain.script == [] and len(brain.seen) == 4


def test_a_line_that_waits_on_her_still_ends_the_turn(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "kaam_status", q="a")], "tool_use"),
        ([txt("Card bhej diya hai - aap haan karein to main bhej deta hoon?")], "end_turn"),
        ([txt("never reached")], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "bhej do", tenant_id="default"))
    assert len(brain.seen) == 2


@pytest.mark.parametrize("text,want", [
    ("Status mein 3 kaam mile. Ab doosra hissa dekh raha hoon.", True),
    ("Ab sheet update karti hoon.", True),
    ("Found 12 repos. Next I'll build the PDF.", True),
    ("Let me check the sheet.", True),
    ("अब रिपोर्ट बना रहा हूँ।", True),
    ("Aapka video ban raha hai, 2 minute lagenge.", False),   # a THING is running, not Hoola promising
    ("Mail bhej diya.", False),
    ("Report taiyaar hai: drive.google.com/x", False),
    ("Kya main aage badhun?", False),
    ("Main aapke jawab ka intezaar kar raha hoon.", False),
    ("Card bhej diya hai, aap haan karein.", False),
    ("", False),
])
def test_promised(text, want):
    from app.agent.aage import promised
    assert promised(text) is want


def test_the_narrate_ask_now_says_line_and_tool_in_one_message():
    from app.agent import goal as G
    n = G.NARRATE
    assert "AGLA TOOL CALL ek hi jawab mein" in n and "sirf line likh ke mat ruko" in n
    assert "ab use EK chhoti line batao" in n and "15-30 shabd" in n       # v0.258 / v0.268 untouched


# ---------------------------------------------------------------- 2. a parallel batch is one call
def test_parallel_research_is_not_a_false_stuck(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    script = []
    for r in range(10):        # 40 searches in 10 rounds: v0.310 stopped this at round 8 ("atak gaya")
        script.append(([txt(f"Round {r}: 4 source mile, aage padh raha hoon.")]
                       + [tu(r * 10 + k, "google_search", query=f"topic {r}-{k}") for k in range(4)], "tool_use"))
    script.append(([txt("Report taiyaar: 40 source padhe.")], "end_turn"))
    brain = _set_brain(monkeypatch, FakeBrain(script))
    import app.agent.santosh as S

    async def tool(name, args, ctx, settings, route=None):
        return {"results": [str(args)]}
    monkeypatch.setattr(S, "_run_tool", tool)
    out = asyncio.run(S.run_turn(conv, "is topic par deep research karo", tenant_id="default"))
    assert "atak gaya" not in out and "40 source padhe" in out
    assert brain.script == []


def test_breaker_batch_counts_once():
    from app.agent.breaker import MAX_CALLS, Breaker
    assert MAX_CALLS == 48
    b = Breaker(max_calls=5)
    for _ in range(4):
        b.batch(4)
        for k in range(4):
            assert b.before("google_search", {"q": f"{_}-{k}"}) is None
    assert b.calls == 4 and not b.stopped


# ---------------------------------------------------------------- 3. a moving turn keeps its deadline
def test_a_moving_turn_gets_the_long_deadline():
    from app.agent import santosh as S
    conv = "c-moving"

    async def work():
        S._PROGRESS[conv] = time.time()      # a tool just finished
        await asyncio.sleep(0.3)
        return "done"
    assert asyncio.run(S._with_deadline(work(), conv, 0.1, 2.0)) == "done"


def test_a_stuck_turn_still_times_out():
    from app.agent import santosh as S
    conv = "c-stuck"
    S._PROGRESS.pop(conv, None)

    async def work():
        await asyncio.sleep(1.0)
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(S._with_deadline(work(), conv, 0.1, 2.0))


# ---------------------------------------------------------------- 4. the server writes the plan
def test_no_plan_after_the_ask_means_the_server_writes_one(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    script = [([tu(i, "kaam_status", q=f"kaam {i}")], "tool_use") for i in range(1, 10)]
    script.append(([txt("Saare 9 kaam dekh liye, sab theek.")], "end_turn"))
    brain = _set_brain(monkeypatch, FakeBrain(script))
    from app.agent import goal
    from app.agent.santosh import STATS_LONG, run_turn
    before = STATS_LONG["auto_plan"]
    out = asyncio.run(run_turn(conv, "saare kaam ek ek karke dekho", tenant_id="default"))
    assert STATS_LONG["auto_plan"] == before + 1
    assert any("server ne yeh plan bana diya" in str(c["messages"][-1]) for c in brain.seen)
    first = next(i for i, c in enumerate(brain.seen) if "server ne yeh plan bana diya" in str(c["messages"][-1]))
    assert first == 7                                    # asked at step 4, written at step 7
    assert "Saare 9 kaam" in out and brain.script == []  # the final answer closes the server's plan: no nudge loop
    assert goal.active_for(conv) is None                 # done, not left open


def test_a_short_job_never_gets_a_server_plan(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    _set_brain(monkeypatch, FakeBrain([([tu(1, "kaam_status", q="a")], "tool_use"), ([txt("Ho gaya.")], "end_turn")]))
    from app.agent.santosh import STATS_LONG, run_turn
    before = STATS_LONG["auto_plan"]
    asyncio.run(run_turn(conv, "status", tenant_id="default"))
    assert STATS_LONG["auto_plan"] == before


# ================================================================ SAHI AUZAAR 2: the right tool
def test_descriptions_keep_their_use_when_sentences():
    from app.agent.tools import TOOLS
    d = {t["name"]: t["description"] for t in TOOLS}
    assert "Prefer this over" in d["data_fetch"]                       # the 100-repo PDF rule (v0.238) reaches the model
    assert "could have changed since your training" in d["google_search"]
    assert "use google_search instead" in d["open_website"]
    assert "Returns file_id" in d["make_document"]
    cut = sum(1 for x in d.values() if x.endswith("…"))
    assert cut <= 5, f"{cut} descriptions still end mid-sentence"      # v0.310: 150


def test_campaign_tools_are_a_family_not_always_on():
    from app.agent import admit
    from app.agent.tools import FAMILY_OF
    from app.config import get_settings
    st = get_settings()
    assert FAMILY_OF["create_campaign"] == "campaign" and "haan_karo" not in FAMILY_OF
    hello = {t["name"] for t in admit.plan_for("hello ji", st).specs()}
    assert "create_campaign" not in hello and "haan_karo" in hello
    assert len(hello) <= 60                                              # v0.310: 65 on a plain hello
    wa = {t["name"] for t in admit.plan_for("Sab customers ko Diwali offer ka WhatsApp campaign bhejo", st).specs()}
    assert {"create_campaign", "list_lead_lists", "confirm_send"} <= wa


def test_a_campaign_chat_keeps_its_tools(gz):  # noqa: F811
    from app.agent import admit
    from app.db import Message, session
    conv = gz["conv"]
    assert "campaign" not in admit.sticky_families(conv)
    with session() as s:
        s.add(Message(conversation_id=conv, role="user", content="Diwali ka WhatsApp campaign bhejna hai",
                      display="Diwali ka WhatsApp campaign bhejna hai"))
    assert "campaign" in admit.sticky_families(conv)                    # "Kaisa raha?" next keeps the tools


def test_the_guide_says_which_named_tools_are_not_loaded():
    from app.agent import admit
    from app.agent.prompts import system_prompt
    from app.config import get_settings
    st = get_settings()
    plan = admit.plan_for("hello ji", st)
    text = system_prompt(st.wa_dry_run, "", None, families=frozenset(plan.families))
    note = admit.unloaded_note(text, plan)
    assert "TOOLS NOT LOADED IN THIS TURN" in note and "pc_do" in note and "hoola_pc_do" in note
    loaded = {t["name"] for t in plan.specs()}
    named = note.split("also names ", 1)[1].split(". They are NOT", 1)[0].split(", ")
    assert not set(named) & loaded                                       # only names she cannot call right now
    assert admit.unloaded_note(text, plan) == note                       # deterministic: the prompt cache holds


FRESH_ASKS = [   # written for the v0.311 check, never seen by the router's own 163-ask card
    ("kal subah 9 baje doctor ka appointment calendar mein daal do", "gcal"),
    ("Rahul ko mail karo ki meeting 4 baje hai", "email"),
    ("mera last month ka GST return status batao", "gst"),
    ("YouTube pe best biryani recipe video dhundo", "youtube"),
    ("meri Google sheet 'sales' mein aaj ki entry add karo", "sheets"),
    ("website bana do meri bakery ke liye", "site"),
    ("mere drive mein resume.pdf dhundo", "drive"),
    ("staff ki salary slip bana do", "payroll"),
    ("ek song bana do birthday ke liye", "create"),
    ("ek form bana do feedback ke liye", "forms"),
    ("presentation bana do 10 slides ki marketing par", "slides"),
    ("IndiaMART pe steel pipe ka rate batao", "indiamart"),
    ("Postgres database mein orders table dekho", "pgdb"),
    ("customer ki complaint register karo", "shikayat"),
    ("contract review karo jo maine bheja", "contracts"),
    ("purane customers ko WhatsApp pe offer bhejo", "campaign"),
]


@pytest.mark.parametrize("text,fam", FRESH_ASKS)
def test_fresh_asks_route_to_the_right_family(text, fam):
    from app.agent import admit
    from app.config import get_settings
    assert fam in admit.plan_for(text, get_settings()).families
