"""v0.559 CLAUDE JAISA - the owner: "BUILD 1 - 3" on the Claude vs Hoola comparison (the three stages Hoola only partly
matched). Each change is held here with its own measurement.

1. SKILL KI SOOCHI (Claude's level-1 skill metadata): every skill she has is NAMED on every chat turn and call, with
   one short line for the first ~36 (recently used first) and names only for the rest - before, only the top 2
   skills whose words matched her ask were ever seen. skill_manage is loadable whenever she has a skill.
2. SAHI GINTI (Anthropic: tool choice gets worse past 30-50 tools in view): a plain ask carried 75 tools. The maps
   family (20 tools) and the agent team left the always-on core (maps_search + maps_directions stay), her place
   words / a lat,lng pair open maps, a big ask opens the team, and two construction tools that had lost their family
   to a name clash stopped riding on every turn. Free cards: everyday tools 176/176 and maps 26/26 right tool in
   view, median tools a turn 80 -> 57.
3. SAAF MEZ (Claude's context editing): once a request's OLD tool results pass 40,000 chars, results older than the
   newest 3 steps are cleared to one line naming the tool (in batches of 4 so the prompt cache holds). A 12-step
   research turn sent 73,519 chars of history; now 18,756.
"""
import pytest

from app.agent import admit, prune, tools as T


class _S:
    agent_tool_admission = True
    tool_admit_cap = 220


def _view(text):
    a = admit.plan_for(text, _S())
    return [s["name"] for s in a.specs()]


# ---------------------------------------------------------------- 2. SAHI GINTI
def test_a_plain_ask_carries_far_fewer_tools():
    for ask in ("namaste", "Akola mein kal mausam kaisa rahega?", "Ek chhota birthday message likh do Riya ke liye"):
        n = _view(ask)
        assert len(n) <= 55, (ask, len(n))
        assert "maps_search" in n and "maps_directions" in n          # the everyday two stay in view
        assert "maps_route_plan" not in n and "deploy_agents" not in n


@pytest.mark.parametrize("ask", ["Paas mein petrol pump kahan hai?", "Pune se Nashik ka rasta batao",
                                 "Station kitni door hai yahan se", "Mere ghar ke paas 3 sabse acche doctor dhoondo",
                                 "Driver ne 20.705,77.012 bheja hai - yeh kaunsi jagah hai?"])
def test_her_place_words_open_the_whole_maps_family(ask):
    n = _view(ask)
    assert sum(1 for x in n if T.FAMILY_OF.get(x) == "maps") >= 18, ask


def test_a_big_ask_or_team_words_open_the_agent_team():
    assert "deploy_agents" in _view("Meri bakery ke liye ye sab banao: website, 30 din ka Instagram plan, "
                                    "price list PDF, aur WhatsApp offer message")
    assert "deploy_agents" in _view("agent team bana ke competitor research karo")


def test_no_tool_rides_on_every_turn_by_accident():
    unmapped = sorted(t["name"] for t in T.TOOLS if T.FAMILY_OF.get(t["name"]) is None)
    assert unmapped == ["haan_karo"], unmapped                  # the one deliberate always-on unmapped tool
    assert T.FAMILY_OF["const_contracts"] == "contracts"


def test_the_free_cards_still_find_the_right_tool():
    from app.quality import mapscard, maps_asks, toolchoice
    card = toolchoice.router_card(None)
    assert card["right_in_view"] == card["asks"] and card["wrong_loaded"] == 0
    assert card["median_tools"] <= 60                                   # was 80 before v0.559
    m = mapscard.free_card(getattr(maps_asks, "ASKS", None) or maps_asks.SET)
    assert all(r.get("in_view") for r in m["rows"]), [r["id"] for r in m["rows"] if not r.get("in_view")]


# ---------------------------------------------------------------- 1. SKILL KI SOOCHI
@pytest.fixture
def coder_on(env, monkeypatch, tmp_path):
    monkeypatch.setenv("CODER_ENABLED", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.coder import skill_packs, store
    store.ensure()
    skill_packs.seed_all("t-skills")
    for fn in ("seed_byox", "seed_progpack", "seed_fepack"):
        if hasattr(skill_packs, fn):
            getattr(skill_packs, fn)("t-skills")
    yield "t-skills"
    get_settings.cache_clear()


def test_every_skill_is_named_on_a_chat_turn(coder_on):
    from app.coder import inject, store
    names = [r["name"] for r in store.skill_index(coder_on)]
    assert len(names) >= 40
    tb = inject.turn_block(coder_on, "c1", query="namaste")
    assert "ALL HER SKILLS" in tb and "skill_manage read" in tb
    missing = [n for n in names if n not in tb]
    assert not missing or "skill_manage list" in tb, missing[:5]
    assert len(inject.skills_index(coder_on)) <= inject.SKILLS_INDEX_BUDGET + inject.NAMES_BUDGET + 200


def test_skill_manage_is_loadable_whenever_she_has_a_skill(coder_on):
    from app.coder import inject
    adm = admit.AdmitSet(_S())
    assert inject.admit_tool(adm, coder_on, "namaste") is True and "skill_manage" in adm.extra


def test_a_call_names_her_skills_too(coder_on):
    from app.coder import inject
    out = inject.voice_block(coder_on, "c1")
    assert "ALL HER SKILLS" in out


# ---------------------------------------------------------------- 3. SAAF MEZ
def _turn(n, size):
    h = [{"role": "user", "content": "research karo"}]
    for i in range(n):
        h.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"t{i}", "name": f"web_{i}", "input": {}}]})
        h.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": "x" * size}]})
    return h


def test_a_long_turn_clears_its_oldest_results():
    h = _turn(12, 6000)
    p = prune.prune_history(h)
    before, after = sum(len(str(m["content"])) for m in h), sum(len(str(m["content"])) for m in p)
    assert after < before * 0.35
    results = [m for m in p if m["role"] == "user" and isinstance(m["content"], list)]
    assert results[-1]["content"][0]["content"] == "x" * 6000                             # newest step whole
    assert not any(str(r["content"][0]["content"]).startswith("[Purana") for r in results[-3:])   # newest 3 never cleared
    cleared = [r for r in results if str(r["content"][0]["content"]).startswith("[Old tool result")]
    assert len(cleared) == 8 and "web_0" in cleared[0]["content"][0]["content"]
    for a, u in zip(p[1::2], p[2::2]):                                                    # every pair still paired
        assert a["content"][0]["id"] == u["content"][0]["tool_use_id"]
    assert h[2]["content"][0]["content"] == "x" * 6000                                    # input never changed


def test_small_turns_are_untouched_and_clearing_is_stable():
    small = _turn(6, 500)
    assert prune.prune_history(small) == small
    p = prune.prune_history(_turn(12, 6000))
    assert prune.prune_history(p) == p                                                    # idempotent
    a = prune.clear_old(_turn(13, 6000))
    b = prune.clear_old(_turn(14, 6000))                  # one more step inside the same batch: same set cleared
    ca = [i for i, m in enumerate(a) if str(m.get("content")).find("[Old tool result") >= 0]
    cb = [i for i, m in enumerate(b) if str(m.get("content")).find("[Old tool result") >= 0]
    assert ca == cb
