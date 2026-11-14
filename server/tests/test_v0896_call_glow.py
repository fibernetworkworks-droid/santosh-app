"""v0.896 CALL GLOW: the phone's live call screen looks like her Claude + Gemini call videos - the Hoola mark and a
serif line while it connects, a light from below that follows the voice, her words in a bubble and his in serif - in
two looks she picks (Settings > Call look, or the gear in the call): Glow from below and Living pill."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_call_screen_has_both_looks():
    talk = (ROOT / "lib/ui/talk/hoola_talk.dart").read_text()
    for part in ("class CallGlowPainter", "class CallPillPainter", "class CallMark", "class CallMotion",
                 "'Hold tight, connecting…'", "Let's talk", "'End the call'", "app.callLook == 'pill'"):
        assert part in talk, part
    assert "Color(0x" not in talk                      # colours come from the theme (design ratchet)
    state = (ROOT / "lib/state.dart").read_text()
    assert "callLooks = ['glow', 'pill']" in state and "'call_look'" in state
    settings = (ROOT / "lib/ui/shell/hoola_settings.dart").read_text()
    assert "title: 'Call look'" in settings and "_pickCallLook" in settings


def test_version():
    from app import main
    assert main.APP_VERSION == "0.910.0"
