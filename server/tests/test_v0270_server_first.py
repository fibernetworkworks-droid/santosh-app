"""v0.270 SERVER PEHLE - "do deep research and give PDF" ran on the server tools, not wandering between Hoola's cloud PC
and her PC (owner: "INSTEAD OF USING SERVER FOR IT HOOLA IS WONDERING BETWEEN HIS PC AND MERA PC - FIND ROOT CAUSE").

Root causes found in the code (the main turn's router was already clean - no PC tool in view for this ask):
1. the BACKGROUND rounds of her long job (actor "goal") skipped the router and saw all 425 tools, pc_do /
   hoola_pc_do with their long "do anything" descriptions;
2. deploy_agents told the brain sub-agents may use "(mail, sheets, web, pc...)" - a research crew got both PC tools,
   and pick.py let a research task through;
3. Hoola's OWN notes named the place: "(Result from HER PC ...)" read as her PC, a plan step "Hoola ke PC pe ..."
   as the cloud PC - the last note moved the next website step there, so the job flip-flopped between the two PCs;
4. a job she put on HER PC could still be sent to the cloud PC (no refusal for hoola_pc_do when she named pc).
"""
import asyncio

import pytest

from tests.test_v0186_long_goal import gz  # noqa: F401
from tests.test_bazar import bz  # noqa: F401


def _st():
    from app.config import get_settings
    return get_settings()


class _Ctx:
    tenant_id, conversation_id, user_id, actor = "t1", "c-srv", "u1", "owner"

    def __init__(self, place="", admit=None):
        self.place = place
        self.admit = admit


# ---------------------------------------------------------------- (2) the crew stays on the server
def test_sub_agents_get_no_pc_unless_the_main_turn_had_one():
    from app.agent import team
    adm = team._agent_admit({"name": "r", "task": "research EV market", "tools": ["web", "pc", "docstudio"]},
                            {"web", "docstudio"}, _st())
    names = {t["name"] for t in team._agent_tools(adm, _st())}
    assert "pc_do" not in names and "hoola_pc_do" not in names and "web_sources" in names
    adm = team._agent_admit({"name": "r", "task": "Tally ledger", "tools": ["pc"]}, {"pc"}, _st())
    assert "pc_do" in {t["name"] for t in team._agent_tools(adm, _st())}   # she put the job on her PC
    desc = next(t for t in team.TEAM_TOOLS if t["name"] == "deploy_agents")["input_schema"]["properties"]["agents"]
    assert "pc..." not in str(desc) and "A PC only when she put the job on a PC" in str(desc)


def test_a_sub_agent_never_inherits_a_pc_lock(env, monkeypatch):
    from app.agent import team, where
    from app.agent.tools import HANDLERS
    where.forget("c-crew")
    where.touch("c-crew", "pc")                         # an older job of this chat ran on her PC
    seen = {}

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        if not seen:
            seen["first"] = True
            return [{"type": "tool_use", "id": "t1", "name": "browse_web",
                     "input": {"task": "read EV market reports", "start_url": "https://example.com"}}], "tool_use", "claude"
        return [{"type": "text", "text": "EV market: 3 facts."}], "end_turn", "claude"
    ran = []

    async def browse(ctx, **kw):
        ran.append(("browse_web", ctx.place))
        return {"text": "page"}

    async def pc(ctx, **kw):
        ran.append(("pc_do", ctx.place))
        return {"ok": True}
    from app.agent import santosh
    monkeypatch.setattr(santosh, "_think", fake_think)
    monkeypatch.setitem(HANDLERS, "browse_web", browse)
    monkeypatch.setitem(HANDLERS, "pc_do", pc)
    out = asyncio.run(team._run_agent({"name": "res", "task": "research EV market"}, "tm1", "EV report", {"web"},
                                      "default", "c-crew", "turn1", _st(), {"place": ""}))
    assert ran == [("browse_web", "server")]            # stayed in Hoola's server browser, never steered to her PC
    assert "EV market" in out.get("deliverable", "")
    where.forget("c-crew")


# ---------------------------------------------------------------- (4) the pick check: a PC is her choice
def test_a_research_job_on_a_pc_she_did_not_name_is_refused(env):
    from app.agent import pick, where
    from app.agent.tools import ToolError
    where.forget("c-srv")
    for name, task in (("hoola_pc_do", "Open Chromium and research EV market reports on several websites, make a PDF"),
                       ("pc_do", "Open Chrome and research AI agent news, write a report")):
        with pytest.raises(ToolError) as e:
            pick.check(name, {"task": task}, _Ctx())
        assert "web_sources" in str(e.value) and "doc_studio" in str(e.value)
    with pytest.raises(ToolError):                      # a sub-agent ("server") is refused even under a chat PC lock
        where.touch("c-srv", "pc")
        pick.check("pc_do", {"task": "research EV news in Chrome"}, _Ctx(place="server"))
    where.forget("c-srv")


def test_her_own_pc_jobs_still_run(env):
    from app.agent import pick, where
    where.forget("c-srv")
    pick.check("pc_do", {"task": "Open irctc.co.in in Chrome"}, _Ctx(place="pc"))                  # she named her PC
    pick.check("pc_do", {"task": "Tally mein aaj ki sale entry karo"}, _Ctx(place="pc"))         # her PC, her Tally
    pick.check("hoola_pc_do", {"task": "compress video with ffmpeg"}, _Ctx(place="hoolapc"))      # she named Hoola's
    pick.check("hoola_pc_do", {"task": "open example.com in Chromium"}, _Ctx(place="hoolapc"))    # she named it
    where.touch("c-srv", "pc")                                                                     # her running PC job
    pick.check("pc_do", {"task": "now open the next page of the IRCTC site"}, _Ctx())
    where.forget("c-srv")


def test_her_pc_named_never_goes_to_the_cloud_pc():
    from app.agent import where
    from app.agent.tools import ToolError
    with pytest.raises(ToolError) as e:
        where.steer("hoola_pc_do", {"task": "open irctc"}, "pc")
    assert "pc_do" in str(e.value)


# ---------------------------------------------------------------- (3) only her own words name a place
def test_notes_and_nudges_never_name_a_place(gz, monkeypatch):  # noqa: F811
    from app.agent import santosh, where
    conv = gz["conv"]
    where.forget(conv)
    seen = []

    async def fake_steps(*a, **k):
        seen.append(a[1].place if len(a) > 1 and hasattr(a[1], "place") else None)
        return "ok"
    import inspect
    src = inspect.getsource(santosh)
    assert "_hers = (getattr(ctx, \"actor\", \"owner\") or \"owner\") == \"owner\"" in src
    assert "where.remember(conversation_id, user_text if _hers else \"\")" in src
    # the rule itself: a bracketed note / another actor never sets the place, her words do
    assert where.remember(conv, "") == ""
    assert where.place("(Result from HER PC task s1: done)") == "pc"      # what the note WOULD have named
    where.forget(conv)


# ---------------------------------------------------------------- (1) the long job's rounds are routed
def test_goal_rounds_are_routed_like_her_own_turns():
    import inspect
    from app.agent import santosh
    src = inspect.getsource(santosh)
    assert 'in ("owner", "wake", "goal")' in src


def test_deep_research_asks_never_see_a_pc_and_find_the_server_tools():
    from app.agent import admit
    for text in ("Do deep research and give PDF", "Deep research karo EV market pe aur PDF do",
                 "DO DEEP RESEARCH ON AI AGENTS AND GIVE PDF", "Hoola, deep research karke ek PDF report banao"):
        plan = admit.plan_for(text, _st())
        names = {t["name"] for t in plan.specs()}
        assert {"web_sources", "google_search", "open_website", "doc_studio", "deploy_agents"} <= names, text
        assert "pc_do" not in names and "hoola_pc_do" not in names, text
    # a goal round's nudge (plan steps + the ladder words) routes to the same server set
    plan = admit.plan_for('[System: goal "EV report PDF" ke yeh steps baaki hain: 1. web research; 2. PDF banao]',
                          _st())
    names = {t["name"] for t in plan.specs()}
    assert "doc_studio" in names and "pc_do" not in names


def test_tool_chooser_says_deep_research_is_server_work():
    from app.agent import prompts
    slim = prompts.system_text(["core"])
    assert "Deep research / a report on a topic" in slim and "never a PC" in slim


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.298.0"


# ---------------------------------------------------------------- v0.271 SAB SERVER PAR: a PC only on her word
@pytest.mark.parametrize("name,task", [
    ("pc_do", "Tally mein aaj ki sale entry karo"),
    ("pc_do", "Excel mein sales sheet banao"),
    ("pc_do", "print this bill on the printer"),
    ("hoola_pc_do", "compress this video with ffmpeg"),
    ("hoola_pc_do", "pip install pandoc and convert the docx"),
])
def test_desktop_software_alone_never_opens_a_pc_hoola_asks_her(env, name, task):
    from app.agent import pick, where
    from app.agent.tools import ToolError
    where.forget("c-srv")
    with pytest.raises(ToolError) as e:
        pick.check(name, {"task": task}, _Ctx())
    assert "Yeh aapke PC pe karun?" in str(e.value) and "SERVER" in str(e.value)


@pytest.mark.parametrize("text", ["Tally mein aaj ki sale dikhao", "ffmpeg se video chhota karo",
                                  "Excel mein sales sheet banao", "is bill ka printout nikal do"])
def test_software_words_alone_do_not_load_the_pc(text):
    from app.agent import admit
    assert "pc" not in admit.plan_for(text, _st()).families


@pytest.mark.parametrize("text", ["Mere PC pe Tally kholo", "mere laptop pe excel file kholo",
                                  "Hoola ke PC pe ffmpeg se video compress karo", "apne computer pe pandoc chalao"])
def test_her_words_still_load_the_pc(text):
    from app.agent import admit
    assert "pc" in admit.plan_for(text, _st()).families


def test_the_guide_says_server_first_and_ask_before_a_pc():
    from app.agent import prompts
    slim = prompts.system_text(["core"])
    assert "EVERY job runs on the SERVER" in slim and "Yeh aapke PC pe karun?" in slim
