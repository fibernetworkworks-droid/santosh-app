"""v0.892 CLAUDE KE AKSHAR: claude.ai's own stylesheet sets the reply in Anthropic Serif 16px / 1.5, weight 400 in light
mode and 360 in dark mode, bold 600 / 530. Anthropic's fonts are private, so Hoola keeps Literata (free, OFL) and copies
the numbers: the console loads the variable Literata and thins the reply in dark mode, the phone carries Literata cut at
360 / 530 ('Literata Dark'). Claude's "Chat font" choice too (Serif / Sans / System / Dyslexic), replies only."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def _css():
    return (CON / "v2.css").read_text()


def test_console_dark_reply_weights_match_claude():
    css = _css()
    blk = css[css.index("v0.892 CLAUDE KE AKSHAR"):]
    assert ":root{--fchat:var(--fr);--rw:400;--rb:600}" in blk                      # light: 400 / 600
    assert ':root:not([data-theme="light"]){--rw:360;--rb:530}' in blk              # dark (system): 360 / 530
    assert ':root[data-theme="dark"]{--rw:360;--rb:530}' in blk                     # dark (picked)
    assert "#app .mh .txt,.mh .txt{font-family:var(--fchat);font-weight:var(--rw)" in blk
    assert "#app .mh .txt :is(b,strong),#app .textmd :is(b,strong){font-weight:var(--rb)}" in blk
    assert "font-optical-sizing:auto" in blk


def test_console_loads_variable_literata():
    html = (CON / "v2.html").read_text()
    assert "Literata:ital,opsz,wght@0,7..72,300..700;1,7..72,300..700" in html   # any weight 300-700, so 360 is exact
    assert "Anthropic" not in html                                                  # never Anthropic's own fonts


def test_console_chat_font_choice():
    js = (CON / "theme.js").read_text()
    assert "font: 'hoola.chatfont'" in js and "['serif', 'sans', 'system', 'dyslexic']" in js
    assert "d.setAttribute('data-chatfont'" in js and "setChatFont:" in js
    v2 = (CON / "v2.js").read_text()
    for f in ("serif", "sans", "system", "dyslexic"):
        assert f'data-font-set="{f}"' in v2
    assert "TH.setChatFont(b.dataset.fontSet)" in v2
    css = _css()
    assert ':root[data-chatfont="sans"]{--fchat:var(--fd)}' in css
    assert "url(/static/console/fonts/OpenDyslexic-Regular.otf)" in css
    for f in ("OpenDyslexic-Regular.otf", "OpenDyslexic-Bold.otf", "OpenDyslexic-OFL.txt"):
        assert (CON / "fonts" / f).stat().st_size > 1000
    assert "SIL Open Font License" in (CON / "fonts/OpenDyslexic-OFL.txt").read_text()


def test_phone_carries_literata_cut_at_claudes_dark_weights():
    from fontTools.ttLib import TTFont
    fonts = ROOT / "assets/fonts"
    assert TTFont(fonts / "LiterataDark-Regular.ttf")["OS/2"].usWeightClass == 360
    assert TTFont(fonts / "LiterataDark-SemiBold.ttf")["OS/2"].usWeightClass == 530
    assert TTFont(fonts / "LiterataDark-Italic.ttf")["OS/2"].usWeightClass == 360
    assert "fvar" not in TTFont(fonts / "LiterataDark-Regular.ttf")              # a plain static cut, as Flutter wants
    pub = (ROOT / "pubspec.yaml").read_text()
    assert "- family: Literata Dark" in pub and "- family: OpenDyslexic" in pub
    theme = (ROOT / "lib/ui/hoola_theme.dart").read_text()
    assert "static const serifDark = 'Literata Dark';" in theme
    assert "_ => c.dark ? HoolaFont.serifDark : HoolaFont.serif," in theme
    assert "TextStyle(fontFamily: ChatFont.family(c), fontSize: 16," in theme


def test_phone_chat_font_setting():
    state = (ROOT / "lib/state.dart").read_text()
    assert "String get chatFont" in state and "_prefs.setString('chat_font', f)" in state
    assert "ChatFont.current = chatFont;" in state
    st = (ROOT / "lib/ui/shell/hoola_settings.dart").read_text()
    assert "title: 'Chat font'" in st and "_pickChatFont" in st


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.910.0"
    assert "0.910.0+909" in (ROOT / "pubspec.yaml").read_text()
    assert (CON / "v2.html").read_text().count("?v=0.910.0") == 35
