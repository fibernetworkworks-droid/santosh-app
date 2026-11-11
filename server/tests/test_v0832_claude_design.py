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


_NL, _BS, _S1, _S2 = chr(10), chr(92), chr(39), chr(34)
_PAIR = {"(": ")", "[": "]", "{": "}"}


def _skip_string(src: str, i: int) -> int:
    """src[i] opens a Dart string; return the index after its end ($name and ${expr} interpolation handled)."""
    c = src[i]
    raw = i > 0 and src[i - 1] == "r"
    tri = c * 3
    q = tri if src.startswith(tri, i) else c
    i += len(q)
    n = len(src)
    while i < n:
        if not raw and src[i] == _BS:
            i += 2
            continue
        if not raw and src.startswith("${", i):
            i = _scan(src, i + 2, True)
            continue
        if src.startswith(q, i):
            return i + len(q)
        if len(q) == 1 and src[i] == _NL:
            return i
        i += 1
    return i


def _scan(src: str, i: int, in_interp: bool = False):
    """Walk code from i; in_interp: stop after the closing brace of a ${...} and return the index there.
    At top level returns True when brackets balance, False otherwise."""
    st, n = [], len(src)
    while i < n:
        c = src[i]
        if src.startswith("//", i):
            j = src.find(_NL, i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in (_S1, _S2):
            i = _skip_string(src, i)
            continue
        if c in _PAIR:
            st.append(c)
        elif c in _PAIR.values():
            if not st:
                if in_interp and c == "}":
                    return i + 1
                return False if not in_interp else i + 1
            if _PAIR[st[-1]] != c:
                return False
            st.pop()
        i += 1
    return i if in_interp else not st


def _balanced(src: str) -> bool:
    return _scan(src, 0) is True


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


# ---- the all-screens pass (second commit of v0.832.0) ----
LIB = REPO / "lib"


def _dart(rel: str) -> str:
    return (LIB / rel).read_text(encoding="utf-8")


def test_no_indigo_or_old_saffron_literals_left_anywhere():
    import colorsys
    bad = []
    for p in LIB.rglob("*.dart"):
        for m in re.finditer(r"Color\(0x([0-9A-Fa-f]{8})\)", p.read_text(encoding="utf-8", errors="ignore")):
            h = m.group(1)
            r, g, b = (int(h[i:i + 2], 16) for i in (2, 4, 6))
            hh, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            if 230 <= hh * 360 <= 300 and l < .4 and s > .12 and h.upper() not in ("FFA21CAF", "FF2D2D5F"):
                bad.append((p.name, h))
    assert not bad, bad[:5]
    for old in ("FFB15C", "FFC27A"):
        assert old not in "".join(p.read_text(encoding="utf-8", errors="ignore") for p in LIB.rglob("*.dart")), old


def test_no_decorative_gradients_or_coloured_glows_on_the_shared_screens():
    for rel in ("ui/top_plugins.dart", "ui/artifacts_screen.dart", "ui/goal_card.dart", "ui/artifact_screen.dart", "ui/notebook_screen.dart"):
        src = _dart(rel)
        assert "gradient: C.gradient" not in src and "gradient: C.youGradient" not in src, rel
    for rel in ("ui/today_screen.dart", "ui/home_sections.dart", "ui/any_card.dart", "ui/approve_sheet.dart"):
        src = _dart(rel)
        assert not re.search(r"BoxShadow\(color: (?:grad\.last|glow|tone|col)\.withOpacity\([^)]*\), blurRadius: (?!0\b)", src), rel
        assert "Color(0x66FFA046)" not in src and "Color(0x66FF963C)" not in src, rel
    # the avatar orb keeps its gradient and soft glow - it is the person, not chrome
    assert "gradient: call.inCall ? null : C.gradient" in _dart("ui/live_voice_screen.dart")
    assert "gradient: C.gradient" in _dart("ui/voice_screen.dart")


def test_sentence_case_labels():
    assert "String softCaps(String t)" in GLASS and "softCaps(text)" in GLASS
    assert "softCaps(text)" in _dart("ui/home_sections.dart")
    # every converted label keeps a plain call - and an ordinary mixed-case label is returned untouched
    assert "t != t.toUpperCase()" in GLASS and "const keep = {" in GLASS
    for rel in ("ui/today_screen.dart", "ui/chat_screen.dart", "ui/scroll_screen.dart", "ui/approve_sheet.dart", "ui/setup_screen.dart"):
        assert "softCaps(" in _dart(rel), rel
    assert "letterSpacing: 1.2" not in _dart("ui/today_screen.dart")


def test_today_greeting_and_tiles_follow_the_design():
    t = _dart("ui/today_screen.dart")
    assert "replyText(size: 30)" in t                       # the greeting in the reply serif
    assert "BoxDecoration(color: C.bubble, borderRadius: BorderRadius.circular(17))" in t
    assert "LinearGradient(colors: grad" not in t           # no coloured gradient tiles
    assert "Press(\n          onTap: () => _ask(prompt)" in t   # tiles still ask the same prompts


def test_call_screen_captions_and_controls():
    v = _dart("ui/live_voice_screen.dart")
    cap = _body(v, "Widget _captions()", "Future<void> _attach()")
    assert "Glass(" not in cap and "replyText(size: 22)" in cap and "TextAlign.center" in cap
    assert "'YOU'" not in cap
    small = _body(v, "Widget _small(", "Widget _orb()")
    assert "BoxShape.circle" in small and "width: 56" in small
    orb = _body(v, "Widget _orb()", "class ")
    assert "color: call.inCall ? C.bad : null" in orb and "0xFFB91C1C" not in orb
    assert "onTap: call.act == CallAct.connecting ? null : (call.inCall ? call.end : call.start)" in orb   # the same action


def test_studio_kit_uses_the_interface_sans_and_no_dead_import():
    k = _dart("ui/studio/studio_kit.dart")
    assert "uiSans(" in k and "GoogleFonts" not in k and "google_fonts" not in k
    assert "static const bg = Color(0xFF151515)" in k


def test_all_edited_dart_files_balanced_after_the_all_screens_pass():
    import subprocess
    changed = subprocess.run(["git", "diff", "--name-only", "origin/main", "--", "lib"], cwd=REPO,
                             capture_output=True, text=True).stdout.split()
    for rel in changed:
        if rel.endswith(".dart"):
            src = (REPO / rel).read_text(encoding="utf-8")
            assert _balanced(src), rel
            assert "<<<<<<<" not in src, rel
