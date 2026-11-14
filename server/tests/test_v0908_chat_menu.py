"""v0.908 CHAT MENU: the console's chat menu (rename / pin / archive / delete) on the phone drawer, same server routes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phone_menu_matches_the_console():
    console = (ROOT / "server/app/static/console/chatlist.js").read_text()
    menu = (ROOT / "lib/ui/shell/hoola_chat_menu.dart").read_text()
    for label in ("'Pin'", "'Unpin'", "'Rename'", "'Compact chat'", "'Archive'", "'Restore from archive'", "'Delete'"):
        assert label in console, label
        assert label in menu, label
    assert "It leaves the chat list, search and its link." in console
    assert "It leaves the chat list, search and its link." in menu


def test_same_routes():
    api = (ROOT / "lib/api.dart").read_text()
    assert "_send('PATCH', '/api/conversations/${Uri.encodeComponent(id)}'" in api
    assert "_send('DELETE', '/api/conversations/${Uri.encodeComponent(id)}')" in api
    assert "'archived': 'true'" in api
    main = (ROOT / "server/app/main.py").read_text()
    assert '@app.patch("/api/conversations/{conversation_id}"' in main
    assert '@app.delete("/api/conversations/{conversation_id}"' in main


def test_drawer_wiring():
    shell = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    assert "onLongPress: onMenu" in shell and "'Chat options: $text'" in shell
    assert "_section('Pinned', c)" in shell and "HoolaArchivePage(" in shell
    assert "chat_menu_test.dart" in (ROOT / ".github/workflows/app-screens.yml").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.913.0"
    assert "version: 0.913.0+912" in (ROOT / "pubspec.yaml").read_text()
