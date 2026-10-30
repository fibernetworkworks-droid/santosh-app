"""v0.245 SAHI AUZAAR - Hoola picks the right tool for EVERY ask, not just PDFs (owner: "I WANT IT UNIVERSALLY, NOT
FOR PDF ONLY - HOOLA MUST CHOOSE THE PERFECT TOOL FOR THAT PARTICULAR PROMPT").

Measured root causes: the router admitted families on single words - 'pdf' -> India holidays, 'make' -> notebook +
network + artifact, the word 'hoola' (in nearly every message) -> 35 network tools AND the PC tools, 'search' /
'phone' / 'report' / 'print' -> the PC tools - so doc_studio was missing for "make a PDF" while pc_do / hoola_pc_do
(long, persuasive descriptions) were in view; WhatsApp campaign tools (no family) were never in view at all.
Old router on 60 fresh asks: right tool in view 50/60, a wrong family loaded 9/60. New: 155/155 and 0/155.
"""
import asyncio

import pytest

from tests.test_bazar import bz  # noqa: F401


def _st():
    from app.config import get_settings
    return get_settings()


def _view(text):
    from app.agent import admit
    plan = admit.plan_for(text, _st())
    return {t["name"] for t in plan.specs()}, set(plan.families), plan


# ---------------------------------------------------------------- the set + the router card
def test_tool_set_is_valid_and_big():
    from app.quality import tool_asks as T
    assert T.check() == []
    assert len(T.ASKS) >= 150
    kinds = {a["id"].split("_")[0] for a in T.ASKS}
    assert {"doc", "data", "web", "mail", "cal", "pc", "hpc"} <= kinds


def test_router_puts_the_right_tool_in_view_for_every_ask_and_keeps_wrong_families_out():
    from app.quality import toolchoice as C
    card = C.router_card()
    bad = [r for r in card["rows"] if not r["in_view"] or r["wrong"]]
    assert not bad, bad
    assert card["right_in_view"] == card["asks"] and card["wrong_loaded"] == 0
    assert card["median_tools"] < 110                     # still a slim turn, not the 425-tool registry
    assert C.lines(card)[0].startswith("Tool choice (router")


# ---------------------------------------------------------------- the exact failures, pinned
def test_make_a_pdf_sees_doc_studio_and_not_holidays_notebook_or_the_pc():
    names, fams, plan = _view("Find top 100 AI repos on GitHub and make a PDF with a detailed note on each")
    assert {"doc_studio", "data_fetch", "data_note"} <= names
    assert not fams & {"india", "notebook", "hoola", "artifact", "pc"}
    assert plan.why.get("publicapi", "").startswith("intent:")
    names, fams, _ = _view("Ek company profile PDF bana do")
    assert "doc_studio" in names and "india" not in fams
    names, fams, _ = _view("In teeno PDF ko jod kar ek PDF bana do")
    assert "pdf_tools" in names                           # working ON a pdf is still the pdf tools


def test_saying_hoola_or_search_or_phone_never_loads_the_pc_or_the_network():
    for text in ("Hoola, aaj ka mausam kaisa hai?", "Hoola search karo best dentist", "Mera phone slow hai",
                 "Is report ko print karne layak bana do", "50 laptops ki price list chahiye"):
        _, fams, _ = _view(text)
        assert "pc" not in fams, text
        assert "hoola" not in fams, text


def test_the_pc_comes_into_view_only_when_she_names_it_or_desktop_software_is_needed():
    _, fams, plan = _view("Mere PC pe Tally kholo")
    assert "pc" in fams and plan.why["pc"] == "place"
    _, fams, plan = _view("ffmpeg se yeh video chhota kar do")
    assert "pc" in fams and plan.why["pc"] == "software"
    _, fams, _ = _view("Hoola ke PC pe pandoc se convert karo")
    assert "pc" in fams


def test_tools_without_a_family_are_always_in_view():
    names, _, _ = _view("hello ji")
    assert {"create_campaign", "list_lead_lists", "haan_karo", "confirm_send"} <= names
    assert {"doc_studio", "data_fetch"} <= names           # documents + data are core now


def test_auto_keys_are_never_everyday_words():
    from app.agent import admit
    every = set().union(*admit._AUTO.values())
    for w in ("make", "search", "phone", "report", "print", "hoola", "file", "pdf", "note", "video", "photo"):
        assert w not in every, w
    assert "computer operator" in admit._AUTO["operator"]  # joined tool names still route


def test_extra_text_routes_but_her_words_lead():
    from app.agent import admit
    plan = admit.plan_for("theek hai aage badho", _st(), extra_text="step 2: mail to the CA with the report")
    assert "email" in plan.families and "docstudio" in plan.families


# ---------------------------------------------------------------- the pick check in code
class _Ctx:
    tenant_id, conversation_id, user_id, actor, place = "t1", "c-pick", "u1", "owner", ""


def test_a_pc_tool_not_in_view_is_refused_with_the_right_tools(env):
    from app.agent import admit, pick, where
    from app.agent.tools import ToolError
    where.forget("c-pick")
    ctx = _Ctx()
    ctx.admit = admit.plan_for("Top 50 startups ki list PDF mein do", _st())
    with pytest.raises(ToolError) as e:
        pick.check("hoola_pc_do", {"task": "make a pdf of startups"}, ctx)
    assert "data_fetch" in str(e.value) and "tool_search" in str(e.value)
    with pytest.raises(ToolError):
        pick.check("pc_search", {"q": "x"}, ctx)
    pick.check("doc_studio", {}, ctx)                     # anything else passes untouched
    ctx.admit.admit_families(["pc"])                       # she meant a PC: tool_search opened it
    pick.check("pc_search", {"q": "x"}, ctx)


def test_a_data_job_sent_to_a_pc_she_did_not_name_is_refused(env):
    from app.agent import pick, where
    from app.agent.tools import ToolError
    where.forget("c-pick")
    ctx = _Ctx()
    ctx.admit = None                                       # routine / goal rounds see the full registry
    with pytest.raises(ToolError) as e:
        pick.check("hoola_pc_do", {"task": "collect top 100 github repos and make a pdf"}, ctx)
    assert "DATA job" in str(e.value)
    pick.check("hoola_pc_do", {"task": "compress this video with ffmpeg"}, ctx)   # desktop software: fine
    ctx.place = "hoolapc"
    pick.check("hoola_pc_do", {"task": "collect top 100 github repos"}, ctx)      # she named Hoola's PC: her call
    ctx.place = "pc"
    pick.check("pc_do", {"task": "Excel mein sales data ka chart banao"}, ctx)     # her PC, her data: fine


def test_dispatch_runs_the_pick_check_first(env, monkeypatch):
    from app.agent import admit
    from app.agent.tools import Ctx, ToolError, dispatch
    ran = []
    monkeypatch.setitem(__import__("app.agent.tools", fromlist=["HANDLERS"]).HANDLERS, "hoola_pc_do",
                        lambda ctx, **k: ran.append(k))
    ctx = Ctx(tenant_id="default", conversation_id="c-disp")
    ctx.admit = admit.plan_for("GitHub ke top 20 repos ki list", _st())
    with pytest.raises(ToolError):
        asyncio.run(dispatch("hoola_pc_do", {"task": "list repos"}, ctx))
    assert not ran


# ---------------------------------------------------------------- what the model reads
def test_tool_chooser_rides_every_slim_turn_and_names_only_real_tools():
    import re
    from app.agent import prompts
    from app.agent.tools import HANDLERS
    assert "- TOOL CHOOSER" in prompts.PINNED
    slim = prompts.system_text(["core"])
    blk = slim[slim.index("- TOOL CHOOSER"):]
    blk = blk[:blk.index("\n- ")]
    assert "never by one word" in blk and "tool_search" in blk
    for w in re.findall(r"\b[a-z]+_[a-z_]+\b", blk):
        w = w.rstrip("_")
        assert w in HANDLERS or any(n.startswith(w) for n in HANDLERS), w


# ---------------------------------------------------------------- the live card (fake brain, nothing runs)
def test_live_card_scores_the_first_pick_and_never_runs_a_tool(env, monkeypatch):
    from app.agent import santosh, tools as reg
    from app.quality import toolchoice as C
    asks = [{"id": "a", "text": "Ek company profile PDF bana do", "ok": ["doc_studio"]},
            {"id": "b", "text": "Kal 4 baje meeting calendar mein daal do", "ok": ["calendar_add_event"]},
            {"id": "c", "text": "Swiggy se biryani mangwa do", "ok": ["order_karo"]},
            {"id": "d", "text": "Aaj kya din hai", "ok": ["google_search"]}]
    picks = {"a": ("doc_studio", {}), "b": ("calendar_agenda", {}), "c": ("tool_search", {"need": "order food swiggy"})}
    seen = []

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        text = history[-1]["content"]
        seen.append({t["name"] for t in tools})
        a = next(x for x in asks if x["text"] == text)
        if a["id"] in picks:
            n, inp = picks[a["id"]]
            return [{"type": "tool_use", "id": "t1", "name": n, "input": inp}], "tool_use", "claude"
        return [{"type": "text", "text": "Aaj guruvar hai."}], "end_turn", "claude"
    monkeypatch.setattr(santosh, "_think", fake_think)

    async def boom(*a, **k):
        raise AssertionError("the card must never run a tool")
    monkeypatch.setattr(reg, "dispatch", boom)
    card = asyncio.run(C.live_card(asks, brain="claude"))
    rows = {r["id"]: r for r in card["rows"]}
    assert rows["a"]["right"] and not rows["b"]["right"]
    assert rows["c"]["pick"] == "tool_search" and rows["c"]["found"] and rows["c"]["right"]
    assert rows["d"]["pick"] == "" and "guruvar" in rows["d"]["words"]
    assert card["right"] == 2 and card["via_search"] == 1 and card["no_tool"] == 1
    assert "doc_studio" in seen[0] and "pc_do" not in seen[0]
    ln = C.lines(card)
    assert "right first pick 2/4" in ln[0] and any("picked calendar_agenda" in x for x in ln)


def test_cards_save_and_list(env, monkeypatch, tmp_path):
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path / "q"))
    from app.quality import toolchoice as C
    card = C.save(C.router_card(), "test")
    assert card["file"].startswith("tools-router-")
    assert C.saved()[0]["file"] == card["file"] and C.saved()[0]["right"] == card["right_in_view"]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.270.0"
