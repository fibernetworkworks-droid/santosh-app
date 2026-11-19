"""v0.931 HOOLA CODE IN THE SIDE PANEL (owner: "ON TOP SHOW A HOOLA CODE ICON ... REMOVE THE HOOLA CODE FROM TOOL SECTION
... TOP RIGHT CORNER A NEW CHAT ICON REMOVE THAT" -> design option B -> "GO WITH B")."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
TOOLS = (ROOT / "lib/ui/shell/hoola_tools.dart").read_text()
CHAT = (ROOT / "lib/ui/chat/hoola_chat.dart").read_text()


def test_the_side_panel_has_the_code_button():
    assert "HoolaCodeButton(live: _codeLive, onTap: _openCode)" in SHELL
    assert "Expanded(child: Text('Hoola', style: HoolaType.hero(c)))" in SHELL
    assert "class HoolaCodeButton extends StatelessWidget" in SHELL
    assert "Text('Code'" in SHELL and "Icons.terminal_rounded" in SHELL
    assert "hoolaOpenNew(nav.context, app, HoolaCode(app: app))" in SHELL      # the native Hoola Code screen
    assert "closeDrawer()" in SHELL                                             # the panel closes first
    assert "api.call('GET', '/api/devsahayak')" in SHELL and "t['running'] == true" in SHELL   # the working dot


def test_hoola_code_left_the_tools_tab_but_its_opener_stays():
    more = TOOLS[TOOLS.index("const List<HoolaTool> hoolaMoreTools"):TOOLS.index("];", TOOLS.index("const List<HoolaTool> hoolaMoreTools"))]
    assert "(title: 'Hoola Code'" not in more and "Game Dev" in more
    assert "? hoolaOpenNew(context, app, HoolaCode(app: app))" in TOOLS       # AI team > Developer keeps working


def test_no_new_chat_icon_top_right():
    assert "Icons.edit_square" not in SHELL and "Icons.edit_square" not in CHAT
    assert "onNew" not in CHAT


def test_design_rules_and_version():
    i = SHELL.index("class HoolaCodeButton")
    btn = SHELL[i:]
    assert "Color(0x" not in btn and "blur" not in btn.lower() and "w800" not in btn and "w900" not in btn
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.39"' in main
    assert "version: 0.999.39+1037" in (ROOT / "pubspec.yaml").read_text()
