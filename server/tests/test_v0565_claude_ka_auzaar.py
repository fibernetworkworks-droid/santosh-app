"""v0.565 CLAUDE KA AUZAAR (built as 0.563) - the owner: "NOW MAKE CHOOSING TOOL AND SKILL SAME AS CLAUDE AI".

1. TOOLS THE CLAUDE WAY (Anthropic's tool search, custom implementation): a Claude turn declares EVERY tool - the
   admitted ones in view, the rest with defer_loading - builds the list ONCE and never changes it; tool_search answers
   with tool_reference blocks (the API loads those definitions). A refused feature falls back for the process; a
   reference that cannot resolve becomes text; other brains never see either.
2. SKILLS THE CLAUDE WAY: every skill's whole description rides a chat turn (Claude's level 1), a call keeps its size.
"""
import asyncio
import json

import pytest

from app.agent import admit, cache, context as C, toolsearch as ts
from app.agent.tools import TOOLS
from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


@pytest.fixture(autouse=True)
def _native_on():
    ts.NATIVE["ok"] = True
    yield
    ts.NATIVE["ok"] = True


class _S:
    agent_tool_admission = True
    tool_admit_cap = 220


def test_the_whole_toolbox_is_declared_and_only_the_admitted_part_is_in_view():
    shown = admit.plan_for("namaste", _S()).specs()
    full = ts.build(shown)
    names = [t["name"] for t in full]
    assert len(names) == len(set(names)) and set(names) >= {t["name"] for t in TOOLS}
    assert full[:len(shown)] == shown                                    # in view first, unchanged
    assert all(t.get("defer_loading") for t in full[len(shown):])
    assert ts.loaded(full) == shown
    assert C.size(C._in_view(full)) == C.size(shown)                     # the gauge counts only what is in view


def test_the_cache_breakpoint_never_lands_on_a_deferred_tool():
    full = ts.build(admit.plan_for("namaste", _S()).specs())
    out = cache.tools(full)
    marked = [t for t in out if t.get("cache_control")]
    assert len(marked) == 1 and not marked[0].get("defer_loading")


def test_bm25_reads_name_description_and_arguments_like_claudes_search():
    assert "pdf_tools" in ts.bm25("merge pdf files")
    assert "computer_operator" in ts.bm25("fill a form on a government website")
    assert "get_weather" in ts.bm25("weather forecast")
    found = ts.find("send email to the client", {"email"})
    assert found and len(found) <= ts.MAX_REFS


def test_references_that_cannot_resolve_become_text_and_good_ones_stay_byte_identical():
    h = [{"role": "user", "content": "x"},
         {"role": "assistant", "content": [tu(1, "tool_search", need="pdf")]},
         {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                       "content": [{"type": "tool_reference", "tool_name": "pdf_tools"}]}]}]
    tools = ts.build([])
    assert ts.fit_refs(h, tools) is h
    gone = ts.fit_refs(h, [t for t in tools if t["name"] != "pdf_tools"])
    assert isinstance(gone[2]["content"][0]["content"], str) and "pdf_tools" in gone[2]["content"][0]["content"]
    assert isinstance(ts.fit_refs(h, tools, keep=False)[2]["content"][0]["content"], str)
    assert h[2]["content"][0]["content"][0]["type"] == "tool_reference"   # the caller's list is never changed


def test_tool_search_answers_with_references_and_opens_the_family_for_the_pc_gate():
    from app.agent.tools import Ctx
    ctx = Ctx(tenant_id="t", conversation_id="c")
    ctx.admit = admit.plan_for("namaste", _S())
    ctx.native_search = True
    ctx.native_loaded = {t["name"] for t in ctx.admit.specs()}
    out = asyncio.run(admit.tool_search(ctx, need="merge pdf files"))
    refs = out["tool_references"]
    assert refs and all(r["type"] == "tool_reference" for r in refs)
    assert "pdf_tools" in [r["tool_name"] for r in refs]
    assert not any(r["tool_name"] in ctx.native_loaded for r in refs)
    out = asyncio.run(admit.tool_search(ctx, need="pc"))
    assert "pc" in ctx.admit.families                                   # pick.py lets her PC tool run after this


def test_a_claude_turn_keeps_one_tool_list_and_reaches_a_deferred_tool(gz, monkeypatch):  # noqa: F811
    from app.agent.santosh import run_turn
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "tool_search", need="merge pdf files")], "tool_use"),
        ([txt("PDF tool mil gaya.")], "end_turn"),
    ]))
    asyncio.run(run_turn(gz["conv"], "namaste ji", tenant_id="default"))
    first, second = brain.seen[0], brain.seen[1]
    assert json.dumps(first["tools"], sort_keys=True) == json.dumps(second["tools"], sort_keys=True)
    deferred = [t for t in first["tools"] if t.get("defer_loading")]
    assert len(deferred) > 400 and not any(t.get("cache_control") for t in deferred)
    res = second["messages"][-1]["content"][0]
    assert res["type"] == "tool_result" and isinstance(res["content"], list)
    assert any(b.get("tool_name") == "pdf_tools" for b in res["content"])


def test_an_api_that_refuses_deferred_tools_gets_the_old_shape(gz, monkeypatch):  # noqa: F811
    from app.agent.santosh import run_turn

    class Refuses(FakeBrain):
        async def create(self, **kw):
            if any(t.get("defer_loading") for t in kw.get("tools") or []):
                self.seen.append(kw)
                raise Exception("Error code: 400 - tools.300.defer_loading: Extra inputs are not permitted")
            return await super().create(**kw)
    brain = _set_brain(monkeypatch, Refuses([([txt("Namaste!")], "end_turn")]))
    asyncio.run(run_turn(gz["conv"], "namaste", tenant_id="default"))
    assert ts.NATIVE["ok"] is False and not any(t.get("defer_loading") for t in brain.seen[-1]["tools"])


def test_other_brains_never_see_a_deferred_tool_or_a_reference(monkeypatch):
    from app.agent import llm, santosh
    from app.config import get_settings
    seen = {}

    async def fake(brain, system, tools, history, cap):
        seen.update(tools=tools, history=history)
        return [txt("ok")], "end_turn", {}
    monkeypatch.setattr(llm, "openai_create", fake)
    h = [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                       "content": [{"type": "tool_reference", "tool_name": "pdf_tools"}]}]}]
    asyncio.run(santosh._call_brain("glm", "s", [{"role": "assistant", "content": [tu(1, "tool_search")]}] + h,
                                    get_settings(), ts.build([admit.search_spec()])))
    assert not any(t.get("defer_loading") for t in seen["tools"])
    assert isinstance(seen["history"][-1]["content"][0]["content"], str)


def test_the_search_tool_names_every_family():
    d = admit.search_spec()["description"]
    assert str(len(TOOLS)) in d and "email" in d and "maps" in d
    assert admit.search_spec() == admit.search_spec()                   # byte-stable across turns (cache)


def test_a_chat_turn_carries_every_skill_description_and_a_call_keeps_its_size():
    from app.coder import inject
    assert inject.SKILLS_INDEX_BUDGET >= 9000 and inject.INDEX_DESC_MAX >= 200
    assert inject.VOICE_INDEX_BUDGET == 3000
    import inspect
    assert "budget=VOICE_INDEX_BUDGET" in inspect.getsource(inject.voice_block)


# ---------------------------------------------------------------- v0.571 SAB SCHEMA SAHI
def test_every_tool_schema_is_valid_json_schema_2020_12():
    """The live hard card found it: once every tool rides every Claude call, ONE invalid schema (dhara_save had
    `required` inside `properties`) 400s every chat turn. Every registered tool must pass the API's own rule."""
    jsonschema = pytest.importorskip("jsonschema")
    bad = []
    for t in TOOLS:
        try:
            jsonschema.Draft202012Validator.check_schema(t.get("input_schema") or {})
        except jsonschema.exceptions.SchemaError as e:
            bad.append((t["name"], e.message[:80]))
    assert not bad, bad


def test_a_bad_schema_never_rides_the_deferred_list_and_a_tools_400_falls_back():
    broken = {"name": "zz_broken", "description": "x",
              "input_schema": {"type": "object", "properties": {"required": ["a"]}}}
    ts._SCHEMA_OK.pop("zz_broken", None)
    assert ts.schema_ok(broken) is False
    assert ts.refused(Exception("Error code: 400 - tools.83.custom.input_schema: JSON schema is invalid"))
    assert not ts.refused(Exception("Error code: 529 - overloaded"))
