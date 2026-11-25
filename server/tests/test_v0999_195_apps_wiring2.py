"""v0.999.195 APPS WIRING 2: every built-in connector a user sees in Connectors (UPI apps, cabs, banks, food apps,
home devices, her helper plugins) reaches a chat turn when she names it - bazar_find / bazar_run come into view.
Before this not one of the ~160 shown connectors opened the bazar family by name (chat_core_tools)."""
from __future__ import annotations

import asyncio

from app.agent import admit
from app.agent.core_prompt import core_prompt


class _S:
    chat_core_tools = True


def _opens(text: str) -> bool:
    a = admit.plan_for(text, _S())
    return a is not None and "bazar" in a.families


def test_every_shown_connector_opens_by_name():
    from app.bazar.config import get_settings as bz
    from app.bazar.service import CORE_EQUIVALENT, HIDDEN_EXECUTORS, registry
    bills = bz().bills_live
    missed = []
    for p in registry().all():
        if p.executor in HIDDEN_EXECUTORS or p.executor == "shop" or (p.executor == "bbps" and not bills):
            continue
        if p.executor == "native" and p.config.get("skill") in CORE_EQUIVALENT:
            continue
        if not _opens(f"use {p.name} for me"):
            missed.append(p.id)
    assert not missed, missed


def test_named_asks_open_connectors():
    for t in ("book an ola cab", "pay with google pay", "check my axis bank balance", "order on zepto",
              "show my connectors", "book a taxi to the airport", "slice card bill"):
        assert _opens(t), t


def test_everyday_asks_stay_clean():
    for t in ("namaste kaise ho", "what is the weather today", "write an email to rahul", "make a pdf report",
              "remind me at 5", "good morning", "udhar rakh do", "ek slice pizza", "kitchen cabinet design", "a kiwi shake"):
        assert not _opens(t), t


def test_tool_search_finds_a_connector():
    from app.agent.tools import Ctx
    ctx = Ctx(tenant_id="t-apps2", conversation_id="c1")
    out = asyncio.run(admit.tool_search(ctx, need="book a rapido"))
    assert "bazar" in str(out)


def test_prompt_names_connectors():
    p = core_prompt("default", False)
    assert 'tool_search("connectors")' in p and "bazar_run" in p
    assert len(p) < 11000
