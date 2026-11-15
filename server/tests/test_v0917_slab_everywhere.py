"""v0.917 SLAB EVERYWHERE: the thick glass slab on every Create sheet, the chat composer and every chat card."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_slab_is_the_glass_itself():
    s = (ROOT / "lib/ui/create/create_colour.dart").read_text()
    assert "final slab = !d.circle && size.shortestSide >= 56;" in s
    assert "rr.deflate(5)" in s, "the second edge"
    assert "_SlabGlass" not in (ROOT / "lib/ui/create/create_home.dart").read_text(), "no double edge on the studios"


def test_chat_composer_and_cards_are_slabs():
    shell = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    assert "crGlass(c, radius: (_files.isEmpty && !_research) ? 999 : 28, strong: true" in shell
    card = (ROOT / "lib/ui/chat/hoola_card.dart").read_text()
    assert "crGlass(c," in card and "tint: highlight ? c.warn : CreateHues.third" in card


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.917.0"
    assert "version: 0.917.0+916" in (ROOT / "pubspec.yaml").read_text()
