"""v0.249 CLAUDE JAISA AKSHAR (owner: "NOW CHECK THE FONT AND ITS SIZE.... OF CLAUDE CHAT" then
"MAKE IT SAME LIKE CLAUDE - FONT AND SIZE BOTH").

Read off Claude's own live stylesheet, not from memory:
    --font-claude-response: var(--font-anthropic-serif)
    .font-claude-response-body  { font-family: SERIF; font-size: 1rem; font-weight: 400; line-height: 1.5 }
    .font-claude-response-small { ... .875rem ... }
    .font-claude-response-title { ... 1.75rem; 600; 1.3 }
    --font-user-message: var(--font-ui)        <- her OWN message is SANS, not serif
So: Hoola's reply is a serif at 16px / 400 / 1.5 on both surfaces, her own message stays sans at the
same 16 / 1.5, headings are serif at weight 600, and bold is 600 (Claude's), not 800.

Anthropic Serif is not ours to use. Source Serif 4 is the closest free one (a transitional serif with
the same optical-size axis), loaded the way Sora / Manrope already are.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def _css() -> str:
    return (CON / "v2.css").read_text()


# ---------------------------------------------------------------- the console
def test_console_loads_the_serif():
    html = (CON / "v2.html").read_text()
    assert "Source+Serif+4" in html                      # the font actually arrives
    assert "opsz" in html                                # the variable optical-size axis, like Claude's
    assert "--fr:'Source Serif 4'" in _css()
    assert "serif" in _css().split("--fr:")[1].split(";")[0]   # a real serif fallback chain, not sans


def test_console_reply_is_claude_serif_16_over_1_5():
    css = _css()
    # main's theme block adds a colour-only #app .mh .txt rule later; exactly ONE rule carries the typography
    live = [ln for ln in css.splitlines() if ln.startswith("#app .mh .txt{") and "font-family" in ln]
    assert len(live) == 1, live
    rule = live[0]
    for pin in ("font-family:var(--fr)", "font-size:16px", "font-weight:400", "line-height:1.5"):
        assert pin in rule, (pin, rule)
    assert "font-size:15.5px" not in rule and "line-height:1.7" not in rule   # the old shape is gone
    # the legacy (non-#app) path carries the same tokens
    base = [ln for ln in css.splitlines() if ln.startswith(".mh .txt{")]
    assert len(base) == 1 and "var(--fr)" in base[0] and "font-size:16px" in base[0]


def test_console_her_own_message_stays_sans():
    """Claude keeps the user message in its UI sans - only the reply is serif. Hoola does the same."""
    css = _css()
    mine = [ln for ln in css.splitlines() if ln.startswith("#app .mu .mut{") and "font-size" in ln]
    assert len(mine) == 1, mine
    assert "var(--fb)" in mine[0]                         # Manrope, the body sans
    assert "var(--fr)" not in mine[0]                     # never the serif
    assert "font-size:16px" in mine[0] and "line-height:1.5" in mine[0]


def test_console_reply_headings_are_serif_600():
    css = _css()
    mdh = [ln for ln in css.splitlines() if ln.startswith(".textmd .mdh{")]
    assert len(mdh) == 1 and "var(--fr)" in mdh[0] and "font-weight:600" in mdh[0]
    assert "var(--fd)" not in mdh[0]                      # not Sora any more
    assert "font-weight:800" not in mdh[0]


def test_default_size_lands_on_claudes_16px_and_her_setting_still_works():
    """Main added Small / Default / Large (`--fs`). Re-based so Default IS Claude's 16px, not overridden by it."""
    css = _css()
    assert "#app .mh .txt,#app .mu .mut{font-size:calc(var(--fs) + 1px);line-height:1.5}" in css
    assert "--fs:15px" in css                             # Default -> 15 + 1 = 16px, Claude's token
    assert ':root[data-size="sm"]{--fs:14px}' in css and ':root[data-size="lg"]{--fs:16.5px}' in css
    assert "calc(var(--fs) + .5px)" not in css            # the old fudge is gone


def test_console_code_at_claudes_small_size():
    """Claude's small token is .875rem = 14px; without this the code inherited an em of the serif body (13.76px)."""
    css = _css()
    assert ".textmd code,.textmd kbd{font-size:14px}" in css
    assert "ui-monospace" in css                          # code stays mono, never the serif
    assert ".cb pre{margin:0;padding:13px 15px;overflow-x:auto;font-size:14px;line-height:1.5}" in css


def test_console_nav_label_did_not_become_a_serif():
    """.txt is ALSO the sidebar nav label - the serif rule must stay scoped to the chat block."""
    css = _css()
    bare = [ln for ln in css.splitlines() if ln.startswith(".txt{") or ln.startswith("#app .txt{")]
    assert bare, "the generic .txt rule went missing"
    for ln in bare:                                       # the bare rule must never carry the serif
        assert "var(--fr)" not in ln, ln
    # and the serif rule must always name the chat block
    for ln in css.splitlines():
        if "var(--fr)" in ln and ".txt" in ln:
            assert ".mh .txt" in ln, ln


# ---------------------------------------------------------------- the phone
def test_phone_reply_style_is_the_same_serif():
    glass = (ROOT / "lib/ui/glass.dart").read_text()
    assert "TextStyle replyText(" in glass
    body = glass.split("TextStyle replyText(")[1].split(";")[0]
    assert "GoogleFonts.sourceSerif4" in body            # the same family as the console
    assert "fontSize: size" in body and "size = 16" in glass.split("TextStyle replyText(")[1][:80]
    assert "FontWeight.w400" in body and "height: 1.5" in body


def test_phone_chat_uses_it_everywhere_a_reply_is_drawn():
    chat = (ROOT / "lib/ui/chat_screen.dart").read_text()
    assert chat.count("MdText(") >= 3
    assert chat.count("style: replyText()") == 3          # saved reply, revealed reply, streaming reply
    assert "fontSize: 15, height: 1.45" not in chat       # the old 15 / 1.45 is gone from the chat
    # her own bubble: sans (the default theme font), at Claude's 16 / 1.5
    assert chat.count("color: Colors.white, fontSize: 16, height: 1.5") == 2
    assert "replyText()" not in chat.split("case 'message':")[1].split("Column(crossAxisAlignment: CrossAxisAlignment.end")[1][:600]


def test_phone_markdown_scaled_to_the_bigger_body():
    md = (ROOT / "lib/ui/md_text.dart").read_text()
    assert "b.level <= 1 ? 22.0 : b.level == 2 ? 20.0 : 17.0" in md
    assert "FontWeight.w600, height: 1.3" in md           # heading weight, Claude's 600
    assert "const TextStyle(fontWeight: FontWeight.w600)" in md   # inline bold, 600 not 800
    assert "FontWeight.w800" not in md                    # nothing left at the old weight
    assert "fontSize: 13.5" not in md and "fontSize: 13," not in md
    assert "fontFamily: 'monospace', fontSize: 14" in md  # code stays mono, sized with the body


def test_nothing_lost_the_reply_is_still_rendered_markdown():
    md = (ROOT / "lib/ui/md_text.dart").read_text()
    for pin in ("List<MdBlock> mdBlocks(", "List<InlineSpan> mdInline(", "String mdPlain(", "class MdText"):
        assert pin in md, pin
    chat = (ROOT / "lib/ui/chat_screen.dart").read_text()
    assert "mdPlain(text)" in chat                        # copy / quote still get the words, not the marks
    assert "WidgetSpan(child: _Caret())" in chat          # the streaming caret survives


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.252.0"
    assert "0.252.0+292" in (ROOT / "pubspec.yaml").read_text()
    assert (CON / "v2.html").read_text().count(f"?v={APP_VERSION}") == 13   # grows as main adds console files
