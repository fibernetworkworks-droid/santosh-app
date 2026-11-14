"""v0.906 NEW CHAT HOME: a new chat holding only the server's greeting is the home with the composer."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_greeting_does_not_open_the_chat():
    state = (ROOT / "lib/state.dart").read_text()
    shell = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    chat = (ROOT / "lib/ui/chat/hoola_chat.dart").read_text()
    assert "bool feedIsGreeting(FeedItem f) => f.kind == 'message' && f.data['source'] == 'greeting';" in state
    assert "f.kind == 'message' && !feedIsGreeting(f)" in shell
    assert "if (!feedIsGreeting(f)) f]" in chat and "feedIsGreeting(f)) continue;" in chat


def test_server_greeting_carries_its_source():
    main = (ROOT / "server/app/main.py").read_text()
    assert '"source": "greeting"' in main


def test_pinned_by_golden_62():
    shots = (ROOT / "test/goldens/screens_test.dart").read_text()
    assert "62_new_chat_" in shots and "find.byType(HoolaHome), findsOneWidget" in shots


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.906.0"
    assert "version: 0.906.0+905" in (ROOT / "pubspec.yaml").read_text()
