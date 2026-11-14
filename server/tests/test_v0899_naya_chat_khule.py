"""v0.899 NAYA CHAT KHULE: New chat on the phone stayed on the old chat. The live stream was an async* generator whose
cancel waited for the chat's next event (a quiet chat only pings), so `await _sub?.cancel()` never returned. The
phone's real check is test/new_chat_test.dart (a local SSE server that only pings); these pin the source shape."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
API = (REPO / "lib" / "api.dart").read_text()
STATE = (REPO / "lib" / "state.dart").read_text()


def _body(src: str, sig: str, n: int = 1400) -> str:
    i = src.index(sig)
    return src[i:i + n]


def test_streams_are_cancellable_controllers_not_generators():
    ev = _body(API, "Stream<SantoshEvent> events(String conv")
    acc = _body(API, "Stream<SantoshEvent> accountEvents(")
    assert "async*" not in ev.split("\n")[0] and "async*" not in acc.split("\n")[0]
    assert "_sse(" in ev and "_sse(" in acc
    sse = _body(API, "Stream<SantoshEvent> _sse(", 3200)
    assert "StreamController<SantoshEvent>" in sse
    assert "onCancel" in sse and "client?.close()" in sse   # cancel ends the read in flight
    assert "stopped" in sse


def test_the_app_never_waits_on_the_old_stream():
    assert "await _sub?.cancel()" not in STATE
    assert "void _dropSub()" in STATE and "unawaited(s?.cancel())" in STATE
    nc = _body(STATE, "Future<void> newChat(", 1400)
    assert nc.index("conversationId = null;") < nc.index("unawaited(old?.cancel())")
    assert "await a.newConversation(" in nc


def test_phone_test_runs_on_ci():
    wf = (REPO / ".github" / "workflows" / "app-screens.yml").read_text()
    assert "test/new_chat_test.dart" in wf
    assert (REPO / "test" / "new_chat_test.dart").exists()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.904.0"
    assert "version: 0.904.0+903" in (REPO / "pubspec.yaml").read_text()
