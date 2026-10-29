"""v0.223 CONSOLE R3 - the conversation. A header (title, session, export, the chat's own menu), the new bubble /
reply / approval-card / working-line looks, a red Stop, "Reply to <avatar>" in the dock, and chat chrome in English.
Tool steps and goal cards stay quiet in the console (the dev's HoolaProgressPolicy, tested in tests/web)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "server" / "app" / "static" / "console"


def _read(name: str) -> str:
    return (CONSOLE / name).read_text()


def test_chat_header():
    html = _read("v2.html")
    for needle in ('id="chead"', 'id="ctitle"', 'id="ctag"', 'id="cShare"', 'id="cExportMenu"', 'id="cMore"'):
        assert needle in html, needle
    assert html.index('id="chead"') < html.index('id="thread"')          # inside the chat view, above the thread
    js = _read("v2.js")
    assert "function drawHead()" in js and "CH?.menu(CONV, e.currentTarget)" in js
    assert "async function exportChat(fmt)" in js and js.count("exportChat(b.dataset.fmt)") == 2
    assert "loaded: () => drawHead()" in js
    cl = _read("chatlist.js")
    assert "menu: (id, btn) => openMenu(id, btn)" in cl and "ctx.loaded?.()" in cl


def test_approval_card_layout():
    js = _read("v2.js")
    assert "row.className = 'decrow'" in js and "'.decrow,.slidec,.acts.dec'" in js
    assert '<div class="kvg">' in js
    css = _read("v2.css")
    tail = css[css.index("v0.223 R3: the conversation"):]
    for rule in ("#app .chead{", "#app .cd.ask{", "#app .cd .kvg{", "#app .decrow{", "#app .slidec .knob{",
                 "#app #composer .stopb{", "#app .mh>.av{"):
        assert rule in tail, rule
    assert css.count("{") == css.count("}")


def test_live_resume_needs_a_turn():
    js = _read("v2.js")
    assert "if (s?.turn) {" in js                                         # an empty /live never draws an empty reply


def test_chat_chrome_speaks_english():
    js, cl = _read("v2.js"), _read("chatlist.js")
    gone = ["kadam", "ne socha", "Accha jawab", "Kharab jawab", "LAMBA KAAM", "Mana kiya", "Bhej diya", "Bhejo ka intezaar",
            ">Bhejo<", ">Kholo<", "Seekha:", "Hoola ne padha", "First jawab", "'Aapka PC'", "Pichhla mila", "Agla mila",
            "Din par jao", "chalta kaam rok do", "Chat export ho gayi", "['Kisne'", "['nayi'", "['dhoondo'", "['rok'",
            "'Kaam'],['main','Main']"]
    for g in gone:
        assert g not in js, g
    for g in ("Naam badlo", "Archive se wapas", "delete ho gayi", "akshar likhiye", "jagah mila"):
        assert g not in cl, g
    assert "Kholo" not in _read("results.js")
    for label in ("'Good reply'".strip("'"), "Edit message", "'LONG JOB RUNNING'", "['new', 'New chat'", "['tools', 'All tools'",
                  "['kaam','Tools'],['main','Account']", "Reply to ${AV}"):
        assert label in js, label
    # the slash menu still runs every command
    assert len(re.findall(r"^\s*\['\w+', '[^']+', '[^']+', \(\) =>", js, re.M)) == 12   # v0.243 + appearance / light / dark / system


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.245.0"
    assert "0.245.0+285" in (ROOT / "pubspec.yaml").read_text()
