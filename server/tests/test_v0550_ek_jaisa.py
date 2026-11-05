"""v0.550 EK JAISA - the owner: "ALL VOICE CALL, CONSOLE CHAT, MOBILE APP CHAT ---- WIRED TO ALL 100 % AI WORK CHECK".

The whole-house wiring audit, held as a test so every future version keeps it:

1. ONE REGISTRY: every tool spec has a handler and every handler has a spec (a spec with no handler = the model
   can call a tool that does not exist; a handler with no spec = work nobody can ever ask for).
2. CHAT (console + phone share ONE pipeline: the same POST /api/conversations/{id}/messages -> turn_inbox ->
   run_turn -> the full registry) - every tool is reachable in a chat turn: core / unmapped, or its family is
   admitted by tool_search asked with the tool's own name.
3. VOICE CALL - every tool has a route (declared to the live model, or run by santosh_kaam = the full chat brain),
   and the declared set stays inside the live budget.
4. WHAT SHE SEES - every card kind the server publishes is drawn on BOTH clients: the console has a default card,
   and the phone (which used to DROP unknown kinds silently) now has the same default card.
5. SKILLS ON A CALL - the call's memory block used to be built with no ask, so learned skills never showed on a
   call; now it searches with her recent words and otherwise names her skills.
Runs standalone too: python tests/test_v0550_ek_jaisa.py
"""
import asyncio
import re
import sys
from pathlib import Path

from app import voice
from app.agent import admit, tools as agent_tools

REPO = Path(__file__).resolve().parents[2]
SERVER_APP = REPO / "server" / "app"
STATE_DART = REPO / "lib" / "state.dart"
CHAT_DART = REPO / "lib" / "ui" / "chat_screen.dart"
ANY_CARD_DART = REPO / "lib" / "ui" / "any_card.dart"
CONSOLE_APP = SERVER_APP / "static" / "console" / "app.js"

# Handlers that are deliberately not model-facing specs (the admission escape hatch rides its own spec).
_HANDLER_ONLY_OK = {"tool_search"}


class _Settings:
    agent_tool_admission = True
    tool_admit_cap = 220


def _spec_names() -> set:
    return {t["name"] for t in agent_tools.TOOLS if isinstance(t, dict) and t.get("name")}


def test_registry_specs_and_handlers_match():
    specs, handlers = _spec_names(), set(agent_tools.HANDLERS)
    no_handler = sorted(specs - handlers)
    # biz_* = customer-safe tools for her business WhatsApp inbox (employee/inbox.py): never offered to HER model
    no_spec = sorted(n for n in handlers - specs - _HANDLER_ONLY_OK if not n.startswith("biz_"))
    assert not no_handler, f"tool specs with no handler (the model can call a tool that does not exist): {no_handler}"
    assert not no_spec, f"handlers with no spec (nobody can ever ask for them): {no_spec}"


def test_every_tool_reachable_in_a_chat_turn():
    """Console and phone run the SAME turn, so one check covers both chats."""
    lost = []
    for name in sorted(_spec_names()):
        fam = agent_tools.FAMILY_OF.get(name)
        if fam is None or fam in admit.CORE_FAMILIES:
            continue                                            # always in view
        ctx = agent_tools.Ctx.__new__(agent_tools.Ctx)        # a real turn's admitted set, nothing else
        ctx.admit = admit.AdmitSet(_Settings())
        asyncio.run(admit.tool_search(ctx, need=name))
        if not ctx.admit._seen(name):
            lost.append(f"{name} ({fam})")
    assert not lost, f"tools tool_search cannot open by their own name: {lost}"


def test_every_tool_has_a_route_on_a_call():
    lost = sorted(n for n in _spec_names() if not voice.call_route(n))
    assert not lost, f"tools a voice call cannot reach: {lost}"
    import json
    specs = voice._tool_specs()
    assert len(json.dumps(specs, ensure_ascii=False)) <= voice.VOICE_TOOL_BUDGET


def test_console_and_phone_send_to_the_same_turn():
    js = CONSOLE_APP.read_text(encoding="utf-8")
    dart = (REPO / "lib" / "api.dart").read_text(encoding="utf-8")
    assert "/api/conversations/${encodeURIComponent(CONV)}/messages`" in js
    assert "'/api/conversations/$conv/messages'" in dart


def _published_kinds() -> set:
    pat = re.compile(r'bus\.publish\([^,]+,\s*"([a-z_0-9]+)"')
    kinds = set()
    for f in SERVER_APP.rglob("*.py"):
        kinds |= set(pat.findall(f.read_text(encoding="utf-8", errors="ignore")))
    return kinds


def test_console_draws_every_kind():
    js = CONSOLE_APP.read_text(encoding="utf-8")
    assert "default: landing(false); renderCard(ev.kind, p, ev.at, true);" in js
    body = js[js.index("function renderCard("):]
    assert "default: {" in body[:body.index("/* ================= events")], "renderCard lost its default card"


def test_phone_draws_every_kind_it_does_not_name():
    state = STATE_DART.read_text(encoding="utf-8")
    handle = state[state.index("Future<void> _handle(SantoshEvent ev)"):]
    handle = handle[:handle.index("    notifyListeners();\n  }")]
    assert "\n      default:" in handle, "the phone event switch lost its default - unknown cards are dropped again"
    assert "FeedItem('any_card'" in handle and "anyCardWorthShowing(ev.kind, p)" in handle
    assert "_anyCards.clear();" in state, "the generic cards must reset with the chat like every other card map"
    chat = CHAT_DART.read_text(encoding="utf-8")
    assert "case 'any_card':" in chat and "AnyEventCard(v: it.data" in chat and "import 'any_card.dart';" in chat
    card = ANY_CARD_DART.read_text(encoding="utf-8")
    assert "class AnyEventCard" in card and "launchUrl" in card
    # the kinds that used to vanish on the phone now reach the default (nothing named them)
    named = set(re.findall(r"case '([a-z_0-9]+)':", handle))
    for k in ("game_desk", "eng_project", "research_run", "agent_team", "drive_file", "bulk_mail", "voice_alert"):
        assert k in _published_kinds(), k        # still a real card kind, and with no case of its own it rides default
    unseen = sorted(k for k in _published_kinds() if k not in named)
    assert unseen, "sanity: some kinds ride the default card"


def test_any_card_filter_needs_something_to_read():
    state = STATE_DART.read_text(encoding="utf-8")
    fn = state[state.index("bool anyCardWorthShowing"):]
    for k in ("'title'", "'say'", "'text'", "'summary'"):
        assert k in fn
    assert "'resync'" in state[state.index("const Set<String> _notCards"):]


def test_call_names_her_skills_when_nothing_matched(monkeypatch):
    from app.coder import inject, store
    monkeypatch.setattr(inject, "_skills_enabled", lambda: True)
    monkeypatch.setattr(inject, "primer", lambda tenant, conv=None, compact=False, query="": "MEM")
    monkeypatch.setattr(store, "skill_names", lambda tenant, limit=8: ["gst-filing", "fe-ui-kit"])
    seen = {}

    def fake_recent(conv, n=4):
        seen["conv"] = conv
        return "gst return bharna hai"
    monkeypatch.setattr(inject, "_recent_asks", fake_recent)

    class S:
        coder_enabled = True
    monkeypatch.setattr("app.config.get_settings", lambda: S())
    out = inject.voice_block("t1", "c1")
    assert seen["conv"] == "c1"
    assert out.startswith("MEM") and "gst-filing" in out and "skill_manage read" in out


def test_call_uses_her_recent_words_as_the_skill_query(monkeypatch):
    from app.coder import inject
    got = {}
    monkeypatch.setattr(inject, "_recent_asks", lambda conv, n=4: "excel macro likho")

    def fake_primer(tenant, conv=None, compact=False, query=""):
        got["q"] = query
        return "LEARNED SKILLS matching this ask: prog-windows-script-lane"
    monkeypatch.setattr(inject, "primer", fake_primer)

    class S:
        coder_enabled = True
    monkeypatch.setattr("app.config.get_settings", lambda: S())
    out = inject.voice_block("t1", "c1")
    assert got["q"] == "excel macro likho" and "Her saved skills" not in out
    assert "skill_manage" in voice.VOICE_TOOL_NAMES and voice.call_route("skill_manage") == "declared"


def test_voice_still_calls_the_block_per_connect():
    src = (SERVER_APP / "voice.py").read_text(encoding="utf-8")
    assert "coder.inject.voice_block, self.ctx.tenant_id" in src


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
