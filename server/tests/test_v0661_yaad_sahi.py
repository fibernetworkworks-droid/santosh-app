"""v0.661 YAAD SAHI (owner: "GO" on Wave 3 of the deep audit - memory accuracy: 19, 20, 21, 22, 24, 25).

19 memory never masks a phone / order number (only card, Aadhaar, bank, PAN, CVV)
20 an update carrying a number (a new address with its PIN code) is kept and replaces the old fact
21 a pinned fact changes in place when her words change it; 'yaad rakhna X' twice is one fact
22 a correction / preference is hers in every Session; replacing a fact retires its copies in other Sessions
24 search finds an old memory of this Session even when thousands of newer rows belong to others
25 a second fact said within 15 s waits its turn; a short line about herself still counts
"""
from __future__ import annotations

import asyncio
import types
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import Conversation, MemoryFact, session

T = "default"


def _chat(cid: str, project: str | None = None) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, project_id=project))
    return cid


def _fact(text, conv=None, pinned=False):
    with session() as s:
        f = MemoryFact(tenant_id=T, text=text, conversation_id=conv, pinned=pinned, source="auto")
        s.add(f)
        s.flush()
        return f.id


def _texts():
    with session() as s:
        return sorted(f.text for f in s.scalars(select(MemoryFact).where(MemoryFact.tenant_id == T)).all())


# ---------------------------------------------------------------- 19 numbers
def test_only_secret_numbers_are_masked():
    from app import pii
    t = ("Sharma ji ka number 9876543210, order 4500012345, PIN 410501, card 4111 1111 1111 1111, "
         "account no 123456789012, PAN ABCPE1234F, cvv 123")
    out = pii.mask_sensitive(t)
    for keep in ("9876543210", "4500012345", "410501"):
        assert keep in out, keep
    for gone in ("4111 1111 1111 1111", "123456789012", "ABCPE1234F", "cvv 123"):
        assert gone not in out, gone


def test_summary_and_index_keep_her_customers_numbers():
    from app import yaad
    from app.agent import compact
    t = "Sharma ji ka number 9876543210, OTP 482910"
    assert "9876543210" in compact.scrub(t) and "482910" not in compact.scrub(t)
    assert "9876543210" in yaad._scrub("Sharma ji ka number 9876543210")


# ---------------------------------------------------------------- 20 an update with a number
def test_an_address_update_with_a_pin_code_replaces_the_old_fact(env):
    from app import yaad
    old = _fact("Godown is at Bhosari MIDC, Pune")
    assert yaad.fact_ok("Godown is now at Plot 12, Chakan MIDC, Pune 410501") == ""
    assert yaad.fact_ok("Her card is 4111111111111111") != ""
    got = yaad.save_fact(T, "Godown is now at Plot 12, Chakan MIDC, Pune 410501", "auto", "", [old])
    assert got and got["id"] and got["replaced"] == ["Godown is at Bhosari MIDC, Pune"]
    assert _texts() == ["Godown is now at Plot 12, Chakan MIDC, Pune 410501"]


# ---------------------------------------------------------------- 21 pinned facts
def test_a_pinned_fact_changes_in_place(env):
    from app import yaad
    pid = _fact("Office 10 baje khulta hai", pinned=True)
    got = yaad.save_fact(T, "Office ab 9 baje khulta hai", "auto", "", [pid])
    assert got["id"] == pid and got["pinned"] and got["replaced"] == ["Office 10 baje khulta hai"]
    with session() as s:
        f = s.get(MemoryFact, pid)
        assert f.text == "Office ab 9 baje khulta hai" and f.pinned
    assert _texts() == ["Office ab 9 baje khulta hai"]


def test_remember_updates_a_pinned_fact_and_never_saves_twice(env):
    from app.agent import life_tools
    pid = _fact("Office 10 baje khulta hai", pinned=True)
    ctx = types.SimpleNamespace(tenant_id=T, conversation_id="")
    out = asyncio.run(life_tools.remember(ctx, "Office ab 9 baje khulta hai", replaces=pid))
    assert out["fact_id"] == pid and out["replaced"] == "Office 10 baje khulta hai"
    assert _texts() == ["Office ab 9 baje khulta hai"]
    asyncio.run(life_tools.remember(ctx, "Riya is her daughter, class 5 at DPS"))
    again = asyncio.run(life_tools.remember(ctx, "Riya is her daughter, class 5 at DPS"))
    assert again.get("already_known") and _texts().count("Riya is her daughter, class 5 at DPS") == 1


# ---------------------------------------------------------------- 22 across Sessions
def test_a_preference_is_hers_in_every_session(env, monkeypatch):
    from app import yaad
    _chat("sx", project="p-client-x")
    got = yaad.save_fact(T, "Quotations: she wants GST shown as a separate line", "auto", "sx", [])
    with session() as s:
        assert s.get(MemoryFact, got["id"]).conversation_id is None
    plain = yaad.save_fact(T, "Client X uses Tally Prime", "auto", "sx", [])
    with session() as s:
        assert s.get(MemoryFact, plain["id"]).conversation_id == "sx"     # a plain fact keeps its fence


def test_replacing_a_fact_retires_its_copy_in_another_session(env):
    from app import yaad
    _chat("general")
    _chat("sy", project="p-y")
    here = _fact("Godown is at Bhosari MIDC, Pune", conv="general")
    _fact("Godown is at Bhosari MIDC, Pune", conv="sy")                   # the same old fact, picked up in Session Y
    yaad.save_fact(T, "Godown is now at Chakan MIDC, Pune", "auto", "general", [here])
    assert _texts() == ["Godown is now at Chakan MIDC, Pune"]


# ---------------------------------------------------------------- 24 search beyond the newest 5,000
def test_search_finds_this_sessions_old_memory_behind_thousands_of_others(env, monkeypatch):
    from app import yaad
    _chat("mine", project="p-mine")
    _chat("other", project="p-other")
    monkeypatch.setattr(yaad, "backfill", lambda t: None)
    monkeypatch.setattr(yaad, "_embed", lambda texts: None)
    old = datetime.now(timezone.utc) - timedelta(days=40)
    with session() as s:
        s.add(yaad.YaadItem(tenant_id=T, conversation_id="mine", kind="exchange", ref="x1",
                            text="Sharma ji ka quotation marble flooring 45000", at=old))
        s.flush()
        s.bulk_save_objects([yaad.YaadItem(tenant_id=T, conversation_id="other", kind="exchange", ref=f"o{i}",
                                           text=f"doosri baat {i} marble", at=datetime.now(timezone.utc))
                             for i in range(5100)])
    hits = yaad._search(T, "Sharma quotation marble", top=5, words=False, conversation_id="mine")
    assert any("Sharma ji ka quotation" in h.get("text", "") for h in hits), hits[:2]


# ---------------------------------------------------------------- 25 timing gates
def test_a_short_self_fact_and_a_quick_second_fact_are_both_kept(env, monkeypatch):
    from app import yaad
    from app.config import get_settings
    monkeypatch.setenv("MEMORY_AUTO", "true")
    get_settings.cache_clear()
    _chat("c25")
    saved = []

    async def fake_ask(system, prompt):
        return '{"facts": ["Her name is Riya"]}' if "Riya" in prompt else '{"facts": ["She is vegetarian"]}'
    monkeypatch.setattr(yaad, "_ask", fake_ask)
    monkeypatch.setattr(yaad, "save_fact", lambda t, text, *a, **k: saved.append(text) or {"id": len(saved), "text": text})
    monkeypatch.setattr(yaad, "FACT_GAP_S", 0.3)
    yaad._LAST_EXTRACT.pop(T, None)

    async def go():
        await yaad.extract_facts(T, "c25", "Mera naam Riya", "Namaste Riya")          # 3 words, about herself
        await yaad.extract_facts(T, "c25", "Main vegetarian hoon yaad rakhna", "Theek hai")   # inside the gap
    asyncio.run(go())
    assert saved == ["Her name is Riya", "She is vegetarian"]
    assert get_settings().memory_auto
