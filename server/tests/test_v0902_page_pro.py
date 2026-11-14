"""v0.902 PAGE PRO: a page Hoola makes is shown like Claude's artifact on the phone. The phone's real checks are
test/page_pro_test.dart (CI app-screens); these pin the wiring and the version."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _r(p):
    return (ROOT / p).read_text()


def test_chat_card_is_the_new_page_card():
    card = _r("lib/ui/chat/hoola_card.dart")
    assert "return HCArtifact(v: it.data, app: app);" in card and "class HCPage" not in card
    art = _r("lib/ui/chat/hoola_artifact.dart")
    for word in ("class HCArtifact", "artifactSteps", "Writing the page", "Checking it opens", "artifactStop", "openArtifactShare",
                 "class PagesPill", "Pages in this chat"):
        assert word in art, word


def test_viewer_in_the_new_design():
    v = _r("lib/ui/artifact_screen.dart")
    assert "HoolaTheme(appearance: app.appearance, child: ArtifactScreen(" in v
    for word in ("Open in browser", "Copy link", "Undo the last change", "Stop sharing", "Ask for a change to this page",
                 "Making version", "openArtifactShare"):
        assert word in v, word
    assert "backgroundColor: const Color(0xF21A1438)" not in v      # the old dark glass versions sheet is gone
    api = _r("lib/api.dart")
    assert "artifactStop" in api and "artifactUndo" in api and "/undo'" in api


def test_pages_pill_in_chat():
    chat = _r("lib/ui/chat/hoola_chat.dart")
    assert "PagesPill(app: app)" in chat


def test_server_routes_the_phone_uses_exist():
    main = _r("server/app/main.py")
    assert '"/api/artifacts/{aid}/stop"' in main and '"/api/artifacts/{aid}/undo"' in main


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.913.0")
    assert "version: 0.913.0+912" in _r("pubspec.yaml")
