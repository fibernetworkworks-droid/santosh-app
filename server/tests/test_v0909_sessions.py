"""v0.909 SESSIONS: the console's sessions (projects) on the phone, same server routes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phone_sessions_match_the_console():
    console = (ROOT / "server/app/static/console/projects.js").read_text()
    page = (ROOT / "lib/ui/shell/hoola_sessions.dart").read_text()
    for words in ("Use my main memory here", "Its chats stay; they just leave the session.", "Remove from session",
                  "Session created. Its instructions, files and chats live here."):
        assert words in console, words
        assert words in page, words
    assert "New chat in this session" in page and "'Add to session'" in (ROOT / "lib/ui/shell/hoola_chat_menu.dart").read_text()


def test_same_routes():
    api = (ROOT / "lib/api.dart").read_text()
    for route in ("'/api/projects'", "'/api/projects/${Uri.encodeComponent(id)}'", "/files'", "query: {'project_id': sessionId}",
                  "'/api/console/conversations', query: {'project': id}"):
        assert route in api, route
    main = (ROOT / "server/app/main.py").read_text()
    for route in ('@app.get("/api/projects"', '@app.post("/api/projects"', '@app.patch("/api/projects/{pid}"',
                  '@app.delete("/api/projects/{pid}"', '@app.post("/api/projects/{pid}/files"'):
        assert route in main, route


def test_drawer_wiring():
    shell = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    assert "_sessionsLabel(c)" in shell and "_sessionHead(" in shell and "HoolaSessionPage(" in shell
    assert "app.closedSessions.contains" in shell
    assert "sessions_test.dart" in (ROOT / ".github/workflows/app-screens.yml").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.911.0"
    assert "version: 0.911.0+910" in (ROOT / "pubspec.yaml").read_text()
