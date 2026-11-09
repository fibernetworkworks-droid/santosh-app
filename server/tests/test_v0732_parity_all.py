"""v0.732 PARITY 0-6 together (owner: "GO VIA THIS --- LARGE ISSUE FIRST"): every new switch on at once, the way the
server runs them - one model, a small fixed prompt, the core tools with the direct page tool, the answer only."""
from __future__ import annotations

import asyncio
import json

import pytest

from app.config import get_settings
from tests.test_bazar import bz  # noqa: F401

SWITCHES = ("CHAT_ONE_MODEL", "CHAT_SMALL_PROMPT", "CHAT_CORE_TOOLS", "CHAT_WORK_IN_TURN", "CHAT_ANSWER_ONLY",
            "CHAT_ARTIFACT_DIRECT")


@pytest.fixture()
def allon(bz, monkeypatch):
    for k in SWITCHES:
        monkeypatch.delenv(k, raising=False)        # the real defaults, not the old suites' pins
    monkeypatch.setenv("HOOLA_LANGUAGE", "en")
    get_settings.cache_clear()
    yield bz
    get_settings.cache_clear()


def test_every_switch_defaults_on():
    from app.config import Settings
    for k in SWITCHES:
        assert Settings.model_fields[k.lower()].default is True, k


def test_a_turn_with_everything_on(allon, monkeypatch):
    from app.agent import santosh
    seen = []

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        seen.append({"system": system if isinstance(system, str) else "".join(b.get("text", "") for b in system),
                     "tools": [t.get("name") for t in (tools or []) if not t.get("defer_loading")], "brain": brain})
        return ([{"type": "text", "text": "Here is the answer."}], "end_turn", brain)

    monkeypatch.setattr(santosh, "_think", fake_think)
    out = asyncio.run(santosh.run_turn(allon["conv"], "make me a small EMI calculator page"))
    s = seen[0]
    assert len(s["system"]) < 12000, len(s["system"])                  # Phase 2
    assert "write the page yourself with the artifact tool" in s["system"]   # Phase 2 + 6 joined
    assert "artifact" in s["tools"] and "web_fetch" in s["tools"]      # Phase 3 core + Phase 6 tool
    assert len(s["tools"]) <= 30, len(s["tools"])       # in view; the rest are deferred (tool search)
    assert len({x["brain"] for x in seen}) == 1                        # Phase 1
    assert out == "Here is the answer."                                # Phase 5: nothing stapled on
    assert "(Kaam:" not in json.dumps(out)


def test_artifact_is_hidden_when_the_direct_switch_is_off(allon, monkeypatch):
    monkeypatch.setenv("CHAT_ARTIFACT_DIRECT", "false")
    get_settings.cache_clear()
    from app.agent.admit import AdmitSet
    a = AdmitSet(get_settings())
    assert "artifact" not in a.extra and "artifact_make" in a.extra
    from app.agent.core_prompt import _pages_line, PAGES_BUILDER
    assert _pages_line() == PAGES_BUILDER
