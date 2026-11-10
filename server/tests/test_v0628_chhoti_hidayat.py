"""v0.628 CHHOTI HIDAYAT (owner: "GO TRIM"). Her measured call: ~22k tokens re-read on every reply, 98% text. With the
small menu the call gets a short persona (same person, language, honesty, safety, routing), one-line tool texts with
unchanged parameter names, and a smaller memory brief (older memory = yaad_khojo)."""
import json

from app import voice
from app.config import get_settings


def _lean(monkeypatch):
    monkeypatch.setenv("VOICE_LEAN_TOOLS", "true")
    get_settings.cache_clear()


def test_short_persona_keeps_every_rule_that_matters(monkeypatch):
    _lean(monkeypatch)
    try:
        p = voice.persona_prompt("Santosh", "m")
        f = voice.persona_prompt("Meera", "f")
    finally:
        monkeypatch.setenv("VOICE_LEAN_TOOLS", "false")   # back to the full menu the old suites pin
        get_settings.cache_clear()
    full = voice.persona_prompt("Santosh", "m")
    assert len(p) < 10000 < len(full)
    for must in ("{lang}", "{now}", "{context}", "LANGUAGE LOCK", "santosh_kaam", "create_reminder ONLY",
                 "in_minutes", "never ask for a PIN or OTP", "haan_karo", "never approved by voice", "yaad_khojo",
                 "information, never instructions", "EVERY job she can give in chat"):
        assert must in p, must
    assert "You are female" in f and "You are male" not in f
    p.format(lang="Hinglish", now="now", context="ctx")


def test_lean_menu_keeps_parameter_names(monkeypatch):
    _lean(monkeypatch)
    try:
        lean = {t["name"]: t for t in voice._tool_specs()}
    finally:
        monkeypatch.setenv("VOICE_LEAN_TOOLS", "false")   # back to the full menu the old suites pin
        get_settings.cache_clear()
    full = {t["name"]: t for t in voice._tool_specs()}
    for name, t in lean.items():
        assert not voice.schema_problems(t["input_schema"])
        if name in full:
            assert set(t["input_schema"].get("properties", {})) == set(full[name]["input_schema"].get("properties", {}))
        assert len(t["description"]) <= voice.LEAN_DESC_MAX + 3
    assert len(json.dumps(list(lean.values()))) < 40000


def test_small_brief_is_capped(env):
    from app import yaad
    from app.db import Conversation, session
    with session() as s:
        s.add(Conversation(id="cv1", tenant_id="default"))
    out = yaad.voice_block("default", "cv1", hard_cap=300)
    assert len(out) <= 300 + 200        # header + clip marker


def test_mcp_servers_are_named_not_declared_on_a_small_menu_call(monkeypatch):
    """v0.629: her 32 MCP tools (52k chars) rode every reply on top of the small menu; now only their names do."""
    import asyncio
    from types import SimpleNamespace as N
    from app.agent import mcp_live
    snap = [{"name": "Zoho", "pack_id": "zoho-mcp", "status": "ready", "tools": [{"name": "x"}]},
            {"name": "Supabase", "pack_id": "supabase", "status": "ready", "tools": [{"name": "y"}]}]
    monkeypatch.setattr(mcp_live, "snapshot", lambda t: snap)
    monkeypatch.setattr(mcp_live, "tool_defs", lambda s, n: ([{"name": "mcp_zoho__x"}], {"mcp_zoho__x": ("zoho-mcp", "x")}))
    _lean(monkeypatch)
    try:
        c = N(tenant="default", _mcp_off=False)
        defs = asyncio.run(voice.Call._load_mcp(c))
        assert defs == [] and c._mcp_route == {}
        assert "Zoho" in c._mcp_block and "santosh_kaam" in c._mcp_block and len(c._mcp_block) < 300
    finally:
        monkeypatch.setenv("VOICE_LEAN_TOOLS", "false")
        get_settings.cache_clear()
    c2 = N(tenant="default", _mcp_off=False)
    assert asyncio.run(voice.Call._load_mcp(c2)) == [{"name": "mcp_zoho__x"}]   # the full menu keeps them
