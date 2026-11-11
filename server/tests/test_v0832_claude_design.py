"""v0.832.0 CLAUDE-STYLE PHONE DESIGN - the Hoola phone app takes the shape of the best chat app on a phone.

Flutter cannot be compiled in this sandbox (pub.dev is unreachable), so this suite pins the design the way every
phone suite does: by reading the Dart source. It pins what the design IS (one neutral ground, a hairline panel with no
blur, the floating tab pill, the chat bar and pill composer, the neutral bubble, flat serif replies) and what must not
come back (the raised glowing mic, the purple chrome, the drifting Aurora, a card around Hoola's reply).
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GLASS = (REPO / "lib/ui/glass.dart").read_text(encoding="utf-8")
MAIN = (REPO / "lib/main.dart").read_text(encoding="utf-8")
CHAT = (REPO / "lib/ui/chat_screen.dart").read_text(encoding="utf-8")


def _body(src: str, start: str, end: str) -> str:
    a = src.index(start)
    return src[a:src.index(end, a)]


def _balanced(src: str) -> bool:
    t = re.sub(r"//[^\n]*", "", src)
    t = re.sub(r"'(?:\\.|[^'\\\n])*'", "''", t)
    t = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', t)
    pr, st = {"(": ")", "[": "]", "{": "}"}, []
    for c in t:
        if c in pr:
            st.append(c)
        elif c in pr.values():
            if not st or pr[st[-1]] != c:
                return False
            st.pop()
    return not st


def test_edited_dart_files_are_bracket_balanced():
    for name, src in (("glass", GLASS), ("main", MAIN), ("chat", CHAT)):
        assert _balanced(src), name
        assert "<<<<<<<" not in src and ">>>>>>>" not in src, name


def test_tokens_are_one_neutral_ground():
    for tok in ("bgTop = Color(0xFF151515)", "surface = Color(0xFF202020)", "bubble = Color(0xFF2A2A28)",
                "hair = Color(0xFF30302D)", "accent = Color(0xFFF4A24C)", "ink = Color(0xFFF3F1EC)",
                "onAccent = Color(0xFF1B1305)"):
        assert tok in GLASS, tok
    # the old night-glass indigo is gone from the shared tokens
    for old in ("0xFF0B0A1A", "0xFF120E2A", "0xFFFFB15C);    // saffron"):
        assert old not in GLASS, old


def test_aurora_is_a_static_ground_and_the_notifier_survives():
    aur = _body(GLASS, "class Aurora", "class Glass")
    assert "extends StatelessWidget" in aur
    for gone in ("AnimationController", "ImageFilter", "BackdropFilter", "_blob", "SingleTickerProviderStateMixin"):
        assert gone not in aur, gone
    assert "tint" in aur and "C.bgTop" in aur
    # chat_screen still drives it: the notifier must stay declared
    assert "ValueNotifier<bool> auroraPaused" in GLASS and "auroraPaused" in CHAT


def test_glass_is_a_hairline_panel_without_blur():
    g = _body(GLASS, "class Glass", "/// Press feedback")
    assert "BackdropFilter" not in g and "ImageFilter" not in g and "boxShadow" not in g
    assert "C.hair" in g
    for param in ("this.flat = false", "this.opacity = .07", "this.radius = 24", "this.border", "this.tint"):
        assert param in g, param          # every caller keeps compiling
    assert "dart:ui" not in GLASS and "dart:math" not in GLASS


def test_interface_sans_is_looked_up_by_name_with_a_fallback():
    assert "GoogleFonts.getFont('Schibsted Grotesk'" in GLASS
    assert "GoogleFonts.getTextTheme('Schibsted Grotesk'" in GLASS
    assert "GoogleFonts.manrope(" in GLASS and "manropeTextTheme" in GLASS      # the fallback
    assert "GoogleFonts.sora" not in GLASS
    assert "GoogleFonts.literata" in GLASS                                        # the reply serif is unchanged


def test_dialogs_sheets_and_chrome_lost_their_purple():
    lib = REPO / "lib"
    for hexv in ("0xF2141029", "0xF21A1438", "0xF2221A47", "0xFF17122F"):
        hits = [str(p) for p in lib.rglob("*.dart") if hexv in p.read_text(encoding="utf-8", errors="ignore")]
        assert not hits, (hexv, hits)
    assert "systemNavigationBarColor: Color(0xFF151515)" in MAIN


def test_tab_pill_has_five_equal_slots_and_no_raised_mic():
    nav = _body(MAIN, "class _NavBar", "/// Live human-like call")
    idx = [int(m) for m in re.findall(r"_item\((\d),", nav)]
    assert idx == [0, 1, 2, 3, 4], idx
    labels = re.findall(r"_item\(\d, [^,]+, [^,]+, '([^']+)'\)", nav)
    assert labels == ["Today", "Chat", "Talk", "Connect", "Main"], labels
    assert "BorderRadius.circular(37)" in nav and "C.hair" in nav and "C.surface" in nav
    for gone in ("Positioned(", "RadialGradient", "Clip.none", "Glass("):
        assert gone not in nav, gone
    # the destinations other code relies on did not move: 2 = the live voice screen
    assert "_tab == 2" in MAIN and "onVoice: () => _go(2)" in MAIN


def test_chat_bar_is_not_a_glass_card():
    h = _body(CHAT, "Widget _header()", "// ---- v0.158")
    assert "Glass(" not in h
    assert "Icons.menu_rounded" in h and "_showChats" in h
    assert "LiveAvatar(" in h and "Icons.graphic_eq_rounded" in h and "app.connect(fresh: true)" in h
    assert "Icons.history_rounded" not in h and "Icons.add_comment_outlined" not in h


def test_pill_composer_shape_and_every_old_action_survives():
    c = _body(CHAT, "Widget _composer()", "/// Santosh at work")
    assert "BorderRadius.circular(32)" in c and "C.surface" in c and "C.hair" in c
    assert "Icons.add_rounded" in c and "onTap: _attach" in c                    # attach is the + button
    assert "onTap: _send" in c and "Icons.arrow_upward_rounded" in c             # send when there is text
    assert "onTap: _mic" in c and "Icons.mic_none_rounded" in c and "Icons.stop_rounded" in c
    assert "onTap: widget.onVoice" in c and "Icons.graphic_eq_rounded" in c      # the white voice-call button
    assert "_listening ? C.accent : C.hair" in c                                 # the rim warms while she speaks
    assert "C.gradient" not in c and "Glass(" not in c
    for label in ("'Send'", "Stop listening", "Photo, PDF, video ya koi bhi file"):
        assert label in c, label


def test_her_message_is_a_neutral_bubble_and_the_reply_is_flat_text():
    msg = _body(CHAT, "case 'message':", "return Padding(")
    assert "color: C.bubble" in msg and "youGradient" not in msg
    assert "BorderRadius.circular(22)" in msg
    assert "Colors.white, fontSize: 16" not in msg
    reply = msg[msg.index(": Padding("):]
    assert "Glass(" not in reply and "MdText(" in reply and "replyText()" in reply
    assert "(me ? .82 : 1.0)" in CHAT                                            # replies use the full width


def test_frozen_pc_files_are_untouched_by_this_design():
    # the Mera PC freeze: the phone PC screen must not carry any of this release's new tokens or helpers
    pc = (REPO / "lib/ui/pc_screen.dart").read_text(encoding="utf-8")
    for marker in ("uiSans(", "C.bubble", "C.hair", "v0.488"):
        assert marker not in pc, marker


def test_version_layer():
    main = (REPO / "server/app/main.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.832.0"' in main and "CLAUDE-STYLE PHONE DESIGN" in main
    assert "0.832.0+831" in (REPO / "pubspec.yaml").read_text(encoding="utf-8")
