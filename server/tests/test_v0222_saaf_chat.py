"""v0.222 SAAF CHAT (phase 3 of the Claude-style reply plan): the phone renders Hoola's replies (lists, headings,
bold, code, tables, links) with its own small renderer, also while a reply streams in; places that can only show
raw text (notifications, bubble, widget) get plain words. The Dart logic itself is tested by
test/md_text_test.dart (flutter test, on CI's Flutter 3.24.5)."""
from pathlib import Path

from app.agent.replystyle import CHAT, plain

REPO = Path(__file__).resolve().parents[2]


def test_plain_strips_marks_but_keeps_words():
    src = "## Aaj ka plan\n- **450** rupaye `D-1001`\n1. [Hoola site](https://hoola.in)\n```\ncode\n```"
    out = plain(src)
    for raw in ("**", "##", "`", "]("):
        assert raw not in out
    assert "Aaj ka plan" in out and "• 450 rupaye D-1001" in out and "Hoola site (https://hoola.in)" in out
    assert plain("2 * 3 = 6 aur file_id") == "2 * 3 = 6 aur file_id"      # math and snake_case untouched
    assert plain("| a | b |\n|---|---|\n| 1 | 2 |") == "| a | b |\n| 1 | 2 |"


def test_notification_shows_words_never_marks():
    from app import push
    title, body = push.render("message", {"role": "assistant", "text": "**Ho gaya** - bill `B-12` ban gaya"})
    assert "**" not in body and "`" not in body and body.startswith("Ho gaya")


def test_rulebook_allows_light_formatting_now():
    assert "Formatting stays light" in CHAT
    assert "No bold, no ### headings" not in CHAT
    assert "only when comparing a few items" in CHAT


def test_phone_renders_markdown():
    md = (REPO / "lib/ui/md_text.dart").read_text()
    for pin in ("List<MdBlock> mdBlocks(", "List<InlineSpan> mdInline(", "String mdPlain(", "class MdText",
                "openInApp(", "streaming"):
        assert pin in md, pin
    assert "package:flutter_markdown" not in md          # our own renderer, no outside package
    chat = (REPO / "lib/ui/chat_screen.dart").read_text()
    assert "import 'md_text.dart';" in chat
    assert "MdText(t, style:" in chat and "streaming: true" in chat and "WidgetSpan(child: _Caret())" in chat
    assert "mdPlain(text)" in chat                        # copy / quote get the words, not the marks
    assert (REPO / "test/md_text_test.dart").exists()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.295.0"
    assert "0.295.0+335" in (REPO / "pubspec.yaml").read_text()
