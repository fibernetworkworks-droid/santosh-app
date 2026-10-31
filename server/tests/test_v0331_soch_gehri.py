"""v0.331 the rest of the long-task plan (owner: "GO" after all v0.330 tests passed; docs/LONG_TASK_RCA.md parts C + D):
1. SOCH GEHRI - a long job / hard ask runs on Claude at a higher effort (output_config.effort, once per turn), with room
   for thinking (goal calls 16k tokens); ordinary chat keeps the model's default.
2. EK KAAM EK AUZAAR - every overlapping tool opens with its LANE (use for / not for -> the neighbour).
3. SAAF KATAI - a too-long tool result shrinks its lists first (valid JSON, a "how to get the rest" note), never a
   mid-JSON cut with no hint.
4. NAAP - the held-out FRESH ask set + `tools --live --fresh` + the vps-ops `tool_card` job."""
import asyncio
import json
from pathlib import Path

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- 1. effort for long jobs
def test_effort_levels():
    from app.agent.santosh import effort_for
    from app.config import get_settings
    st = get_settings()
    assert effort_for(st, True, False) == "xhigh" and effort_for(st, False, True) == "high"
    assert effort_for(st, False, False) == ""                      # plain chat: the model's own default
    assert st.agent_goal_max_tokens == 16000


def _eff(call):
    return ((call.get("extra_body") or {}).get("output_config") or {}).get("effort")


def test_a_big_ask_runs_at_long_effort_and_plain_chat_does_not(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([([tu(1, "kaam_status", q="a")], "tool_use"),
                                               ([txt("Ho gaya, sab dekh liya.")], "end_turn"),
                                               ([txt("Namaste!")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "Meri bakery ka plan banao: research karo, ideas likho, calendar banao, PDF do.",
                         tenant_id="default"))
    assert _eff(brain.seen[0]) == "xhigh" and _eff(brain.seen[1]) == "xhigh"   # stable inside the turn (cache)
    asyncio.run(run_turn(conv, "namaste", tenant_id="default"))
    assert _eff(brain.seen[2]) is None


def test_a_refused_effort_is_dropped_and_the_reply_still_comes(gz, monkeypatch):  # noqa: F811
    import types
    from app.agent import santosh as S

    class Picky(FakeBrain):
        async def create(self, **kw):
            if "extra_body" in kw:
                raise RuntimeError("Error code: 400 - output_config.effort: unexpected field")
            return await super().create(**kw)
    brain = _set_brain(monkeypatch, Picky([([txt("Jawab yeh hai.")], "end_turn")]))
    monkeypatch.setattr(S, "EFFORT", {"ok": True, "calls": 0, "refused": 0})
    out = asyncio.run(S.run_turn(gz["conv"], "Meri bakery ka plan banao: research karo, ideas likho, calendar "
                                              "banao, PDF do.", tenant_id="default"))
    del types
    assert "Jawab yeh hai" in out                                     # the reply still came
    assert S.EFFORT["calls"] >= 1 and S.EFFORT["ok"] is False and S.EFFORT["refused"] == 1
    assert "extra_body" not in brain.seen[-1]                         # retried without it


def test_a_long_job_goes_to_claude_even_when_a_cheap_brain_is_set(gz, monkeypatch):  # noqa: F811
    from app.agent import llm
    monkeypatch.setattr(llm, "cheap_brain", lambda: "glm")
    monkeypatch.setattr(llm, "choose", lambda msgs: "glm")
    called = []

    async def glm(*a, **k):
        called.append("glm")
        return [{"type": "text", "text": "glm"}], "end_turn", {}
    monkeypatch.setattr(llm, "openai_create", glm)
    monkeypatch.setattr(llm, "openai_stream", glm)
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Claude ne kiya.")], "end_turn")]))
    from app.agent.santosh import run_turn
    out = asyncio.run(run_turn(gz["conv"], "Meri bakery ka plan banao: research karo, ideas likho, calendar "
                                            "banao, PDF do.", tenant_id="default"))
    assert "Claude ne kiya" in out and not called and len(brain.seen) == 1


# ---------------------------------------------------------------- 2. lanes
def test_overlapping_tools_open_with_their_lane():
    from app.agent.tools import TOOL_LANES, TOOLS, VOICE_SPECS
    d = {t["name"]: t["description"] for t in TOOLS}
    for name, lane in TOOL_LANES.items():
        assert d[name].startswith("LANE: "), name
    assert "-> web_sources" in d["google_search"] and "-> data_fetch" in d["api_call"]
    assert "-> doc_studio" in d["make_document"] and "-> yaad_khojo" in d["memory_search"]
    v = {t["name"]: t["description"] for t in VOICE_SPECS}
    assert not v["google_search"].startswith("LANE:")               # the call keeps its short budgeted form


# ---------------------------------------------------------------- 3. clean cuts
def test_a_long_result_shrinks_its_lists_and_stays_json():
    from app.agent.santosh import _short
    big = {"total": 300, "repos": [{"name": f"r{i}", "url": f"https://github.com/x/r{i}", "d": "x" * 60}
                                   for i in range(300)]}
    out = _short(big)
    j = json.loads(out)
    assert len(out) <= 6000 and j["total"] == 300 and j["repos"][0]["url"].endswith("/r0")
    assert "more not shown" in j["repos"][-1] and "data_fetch" in j["repos"][-1]


def test_a_long_text_is_cut_with_a_way_to_get_the_rest():
    from app.agent.santosh import _short
    out = _short({"text": "x" * 9000})
    assert "showing 6,000 of" in out and "next page" in out
    assert len(_short({"a": 1})) < 20                                # small results untouched


# ---------------------------------------------------------------- 4. measuring
def test_fresh_asks_all_route_right():
    from app.quality.toolchoice import fresh_asks, router_card
    asks = fresh_asks()
    assert len(asks) == 26 and all(a["ok"] for a in asks)
    card = router_card(asks)
    assert card["right_in_view"] == 26 and card["wrong_loaded"] == 0


def test_the_vps_ops_tool_card_job():
    y = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert "          - tool_card\n" in y and "tools --live --fresh" in y
    assert "tool_card)" in y
