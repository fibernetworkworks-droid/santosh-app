"""v0.491 EQUAL POWER - the owner: "GIVE EQUAL POWER TO ALL - WIRE ALL AI FUNCTIONALITIES, TOOLS, SKILLS ETC TO ALL
THUS CALL SECTION CAN WORK PROPERLY. FIND THE DIFFRENCE". The difference was found (mobile chat and web console chat
share ONE brain by construction - the same POST /api/conversations/{id}/messages -> run_turn -> the full registry;
the voice call was the unequal one). THIS file holds it equal forever: (1) every name listed for voice exists in the
registry (a dead name can never hide), (2) the everyday HEAD of every suite stays DECLARED on a call - campaigns,
Ghar, Forms / Slides / Photos / Notebook reads, scrape, research, skills, the 30 desk readers, (3) the fences that
guard money and secrets stay up, (4) the equal-power cards render on BOTH clients. Runs standalone too:
python tests/test_v0491_equal_power.py"""
import sys
from pathlib import Path

from app import voice
from app.agent import tools as agent_tools

REPO = Path(__file__).resolve().parents[2]
STATE_DART = REPO / "lib" / "state.dart"
CONSOLE_DIR = REPO / "server" / "app" / "static" / "console"


def _registry_names() -> set:
    names = {t["name"] for t in agent_tools.TOOLS if isinstance(t, dict) and t.get("name")}
    names |= set(agent_tools.HANDLERS.keys())
    names |= {t["name"] for t in agent_tools.VOICE_SPECS}
    return names


# v0.491 the everyday HEAD of every suite - if any of these gets fenced again, a call goes deaf to that suite.
EQUAL_POWER_HEADS = {
    # WhatsApp campaigns: create + status + controls (a call always sends auto_send=False; the SEND waits for her card)
    "create_campaign", "get_campaign_status", "control_campaign", "check_template_status",
    # Ghar (Home Assistant, v0.479)
    "home_link", "home_devices", "home_on", "home_off", "home_state",
    # suite READ heads unfenced again (writes and heavy bodies stay on santosh_kaam)
    "form_find", "form_responses", "slides_find", "slides_read", "doc_create",
    "photos_pick", "photos_picked", "notebook_open", "notebook_ask",
    # new doors: one public page, a research job's state, her skills
    "scrape_page", "research_status", "skill_manage",
} | set(voice.VOICE_HEADS)


def test_every_voice_listed_tool_exists():
    """A name in the voice lists that the registry does not know is a silent hole - it can never be declared or
    routed, and every rename must update the voice lists in the same commit."""
    reg = _registry_names()
    listed = set(voice.VOICE_TOOL_NAMES) | set(voice.VOICE_VIA_KAAM) | set(voice.VOICE_HEADS)
    dead = sorted(n for n in listed if n not in reg)
    assert not dead, f"dead names in the voice lists (remove them or fix the registry): {dead}"


def test_equal_power_heads_are_declared_on_a_call():
    specs = {t["name"] for t in agent_tools.VOICE_SPECS}
    for n in sorted(EQUAL_POWER_HEADS):
        assert n in voice.VOICE_TOOL_NAMES, f"{n} must stay listed for voice"
        assert not voice.via_kaam(n), f"{n} must stay DECLARED on a call (someone fenced it again)"
        assert n in specs, f"{n} has no tool spec (renamed in the registry?)"


def test_desk_changes_stay_fenced_only_readers_are_declared():
    for base in ("darzi", "gst", "payroll", "vakil", "chai", "office", "seo", "thok", "society",
                 "app_banao", "app_dekho", "hoola_deal", "form_create", "form_summary", "slides_create",
                 "sheet_update", "notebook_create", "photos_upload"):
        assert voice.via_kaam(base), f"{base} must stay on santosh_kaam (the card tap is the gate)"


def test_money_and_secret_guards_stay_up():
    # the campaign SEND is never a voice act: confirm_send stays undeclared (her card tap gates it)
    assert "confirm_send" not in voice.VOICE_TOOL_NAMES
    # the persona line the whole never-by-voice rule rides on
    assert "Money / UPI / bank-OTP / password cards are NEVER approved by voice" in voice.PERSONA
    # and the campaign line keeps auto_send off on a call
    assert "auto_send=False on a call" in voice.PERSONA
    # haan_karo stays non-money
    spec = next(t for t in agent_tools.TOOLS if isinstance(t, dict) and t.get("name") == "haan_karo")
    assert "money" in str(spec.get("description", "")).lower()
    # the SETUP ladder still sacrifices only gentle things in its persisted first three steps (v0.211 rule)
    assert set(voice.SETUP_STEPS[:voice.SETUP_SOFT_MAX]) == {"vocab", "langcodes", "mcp"}
    assert voice.SETUP_STEPS[voice.SETUP_SOFT_MAX:] == ("compression", "core_tools", "no_tools")


BOTH_CLIENT_CARD_KINDS = {"bazar_approval", "operator_ask", "goal", "artifact", "campaign",
                          "studio_approval", "employee_ask", "email_draft"}
PHONE_ONLY_CARD_KINDS = ("ask_form", "upi_result", "pg_write", "photos_pick")   # console renderers = the W4 pass


def test_equal_power_cards_render_on_both_clients():
    dart = STATE_DART.read_text()
    console = "".join(p.read_text() for p in CONSOLE_DIR.glob("*.js"))
    for k in sorted(BOTH_CLIENT_CARD_KINDS):
        assert k in dart, f"phone (lib/state.dart) stopped rendering the {k} card"
        assert k in console, f"web console stopped rendering the {k} card"
    for k in PHONE_ONLY_CARD_KINDS:
        assert k in dart, f"phone (lib/state.dart) stopped rendering the {k} card (console gets it in the W4 pass)"


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                failed += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if failed else 0)
