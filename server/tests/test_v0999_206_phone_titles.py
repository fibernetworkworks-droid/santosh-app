"""v0.999.206 the phone like Claude in every section: the greeting cut (Literata opsz 48 at 330 / dark 290), the page
title cut (opsz 28 at 530), every home greeting on HoolaType.hero, the serif page titles on pageTitle, and the
Vocal / Music / Notebook chats landing her message at the top (ThreadLander)."""
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "assets" / "fonts"


def _src(p):
    return (ROOT / p).read_text(encoding="utf-8")


def _axes(name):
    f = TTFont(FONTS / name)
    assert "fvar" not in f                       # a plain static cut, as Flutter wants
    return f["OS/2"].usWeightClass


def test_the_cuts_are_claudes_weights():
    assert _axes("LiterataGreet-Regular.ttf") == 330
    assert _axes("LiterataGreetDark-Regular.ttf") == 290
    assert _axes("LiterataTitle-SemiBold.ttf") == 530
    pub = _src("pubspec.yaml")
    for fam, f in [("Literata Greet", "LiterataGreet-Regular"), ("Literata Greet Dark", "LiterataGreetDark-Regular"),
                   ("Literata Title", "LiterataTitle-SemiBold")]:
        assert f"- family: {fam}\n" in pub and f"assets/fonts/{f}.ttf" in pub


def test_the_type_scale():
    t = _src("lib/ui/hoola_theme.dart")
    assert "fontFamily: c.dark ? HoolaFont.greetDark : HoolaFont.greet, fontSize: 38" in t
    assert "static TextStyle pageTitle(HoolaColors c)" in t and "fontFamily: HoolaFont.title, fontSize: 28" in t


def test_every_home_greeting_is_the_greeting():
    for p, words in [
        ("lib/ui/shell/hoola_shell.dart", "Text(_greeting(), textAlign: TextAlign.center, style: HoolaType.hero(c))"),
        ("lib/ui/code/code_home.dart", "Text('What should we build today?', style: HoolaType.hero(c))"),
        ("lib/ui/code/code_start.dart", "Text('What should we build today?', textAlign: TextAlign.center, style: HoolaType.hero(c))"),
        ("lib/ui/create/create_home.dart", "style: HoolaType.hero(c)),"),
        ("lib/ui/vocal/vocal_home.dart", "Text('What should Hoola say?', textAlign: TextAlign.center, style: HoolaType.hero(c))"),
        ("lib/ui/create/create_music.dart", "Text('What shall we make?', textAlign: TextAlign.center, style: HoolaType.hero(c))"),
        ("lib/ui/shell/hoola_computer.dart", "Text('Connect your PC', style: HoolaType.hero(c))"),
        ("lib/ui/shell/hoola_employees.dart", "Text('AI Employees', style: HoolaType.hero(c))"),
        ("lib/ui/setup_screen.dart", "style: HoolaType.hero(c));"),
    ]:
        assert words in _src(p), p


def test_serif_page_titles():
    assert "child: Text(dept.name, textAlign: TextAlign.center, style: HoolaType.pageTitle(c))" in _src("lib/ui/shell/hoola_employees.dart")
    assert "Text('Hoola Wallet', style: HoolaType.pageTitle(c))" in _src("lib/ui/wallet/hoola_wallet.dart")
    assert "style: HoolaType.pageTitle(c)" in _src("lib/ui/shell/hoola_sessions.dart")
    assert "style: HoolaType.pageTitle(c)" in _src("lib/ui/create/create_kit.dart")


def test_the_other_phone_chats_land():
    for p in ["lib/ui/vocal/vocal_home.dart", "lib/ui/create/create_music.dart", "lib/ui/notebook_screen.dart"]:
        s = _src(p)
        assert "ThreadLander(" in s and "_lander.land();" in s and "_lander.listen(" in s, p
        assert "ValueKey('landroom'), height: _lander.room" in s, p
        assert "HoolaRiseIn(" in s, p
    for p in ["lib/ui/vocal/vocal_home.dart", "lib/ui/create/create_music.dart"]:
        s = _src(p)
        assert "if (_lander.held) return;" in s                       # a reply arriving never pulls her message away
        assert "HoolaType.bodyLarge(c).copyWith(height: 1.4)" in s     # her bubble 16 / 1.4
