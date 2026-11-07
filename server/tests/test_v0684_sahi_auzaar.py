"""Wave 12 SAHI AUZAAR of the third deep audit (owner: "GO WAVE 12" - the right tool, the right skill).

29 "bank statement check karo" reaches the money-safety checker, not the enterprise bank integrator / smart home
30 everyday words no longer open the wrong family (cab book -> book publishing, blood pressure -> newsroom ...)
31 a skill is "matching" on its name + description and 2+ of her words, never one shared word in its body
32 every keyword family names a family that has tools (blog / instagram / credit card bill reach something)
33 overlapping tools carry a lane rule (two calendars, the page readers, the knowledge graph)
34 a read skill says which tools it names are not this agent's
35 "mera phone slow hai" reaches the phone doctor
"""
from __future__ import annotations

import asyncio
import types

import pytest


def _r(t):
    from app.agent import admit
    return set(admit.route(t))


@pytest.mark.parametrize("text,wrong", [
    ("cab book karo airport ke liye", "kitab"), ("table book karo 8 baje", "kitab"),
    ("mera blood pressure 150 hai", "patrakar"), ("express delivery chahiye", "patrakar"),
    ("mera credit card bill dekho", "video"), ("company ki information do", "forms"),
    ("company ki information do", "sheets"), ("printer troubleshoot karo", "filmdesk"),
    ("short mein batao", "reel"), ("copy clipboard pe karo", "video"), ("yeh link kholo", "home"),
    ("bacche ka homework", "home"), ("landing page banao", "land"), ("mera bank statement check karo", "enterprise"),
    ("press release likho", "gamedesk"),
])
def test_everyday_words_do_not_open_the_wrong_family(text, wrong):
    assert wrong not in _r(text), (text, _r(text))


@pytest.mark.parametrize("text,right", [
    ("mera bank statement check karo", "finguard"), ("mera credit card bill dekho", "finguard"),
    ("mera phone slow hai", "phonedoc"), ("blog likho diwali offer pe", "kalam"),
    ("meri book likhni hai bacchon ke liye", "kitab"), ("press release likho", "patrakar"),
    ("ghar ki light band karo", "home"), ("admission ka form bharo", "forms"),
])
def test_the_right_family_opens(text, right):
    assert right in _r(text), (text, _r(text))


def test_every_keyword_family_has_tools():
    from app.agent import admit
    fams = set(admit.FAMILY_OF.values())
    assert [f for f in admit.EXTRA_KEYS if f not in fams] == []


def test_overlapping_tools_have_lanes():
    from app.agent.tools import TOOL_LANES
    for n in ("add_calendar_event", "calendar_add_event", "scrape", "scrape_page", "reach", "kgmemory"):
        assert n in TOOL_LANES and TOOL_LANES[n].startswith("LANE:"), n


def test_a_skill_needs_more_than_one_shared_word(env):
    from app.coder import store
    tenant = "t-skill"
    store.skill_mirror("hs-wellbeing", tenant, "Screen time and sleep habits",
                       "Use `set_phone_timer` when she wants a break from the phone.", enabled=1)
    store.skill_mirror("phone-slow-fix", tenant, "Phone slow or hanging: what to check", "Run phone_doctor first.", enabled=1)
    got = [r["name"] for r in store.skills_search(tenant, "mera phone slow hai")]
    assert "hs-wellbeing" not in got and "phone-slow-fix" in got


def test_a_read_skill_names_tools_that_are_not_ours():
    from app.coder import skills_tool
    res = {"ok": True, "results": [{"name": "se-hardening", "body": "First `ask_approval`, then `ax_find`, then `remember`."}]}
    skills_tool._mark_foreign_tools(res)
    note = res["results"][0]["not_your_tools"]
    assert "ask_approval" in note and "ax_find" in note and "remember" not in note.split(" - ")[0]
