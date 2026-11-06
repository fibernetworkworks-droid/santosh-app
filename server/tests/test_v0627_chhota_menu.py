"""v0.627 CHHOTA MENU (owner: "it is going to every tool why --- i just given instructio regarding gmail"; "even call is off
--- money is deducting"). Gemini Live bills the declared tool list on every reply, so the call declares only the everyday
LEAN_TOOLS; everything else still reaches the full brain through santosh_kaam."""
import json

from app import voice
from app.config import Settings, get_settings


def test_production_declares_the_small_menu(monkeypatch):
    assert Settings.model_fields["voice_lean_tools"].default is True
    monkeypatch.setenv("VOICE_LEAN_TOOLS", "true")
    get_settings.cache_clear()
    try:
        names = {t["name"] for t in voice._tool_specs()}
        size = len(json.dumps(voice._tool_specs()))
    finally:
        get_settings.cache_clear()
    assert names == voice.LEAN_TOOLS and "santosh_kaam" in names and "email_draft" in names
    assert size < 45000                       # the full list was ~91k chars, billed on every reply


def test_every_lean_tool_is_a_real_call_tool():
    full = {t["name"] for t in voice._tool_specs()}       # conftest keeps the full list for the old suites
    assert voice.LEAN_TOOLS <= full | {"side_talk"}


def test_an_undeclared_tool_still_reaches_the_full_brain():
    assert voice.registered("darzi_dekho") and "darzi_dekho" not in voice.LEAN_TOOLS
