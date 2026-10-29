"""v0.233.0 New chat lands on a clean chat (owner: "WHEN CLICK ON NEW CHAT IT LANDS ON ANY RANDOM CHAT").

Every tap made one more identical "Naya chat" that opened as a thread with the greeting and an unread dot.
Now the console asks POST /api/conversations?reuse=1: her newest untouched empty chat comes back; a chat that
something happened in (her message, a card, a note) is never reused. A greeting-only chat opens on the home."""
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
JS = (ROOT / "server/app/static/console/v2.js").read_text()


def _client(env):
    from app.main import app
    return TestClient(app)


def test_new_chat_reuses_untouched_empty_chat(env):
    with _client(env) as c:
        a = c.post("/api/conversations?reuse=1").json()
        b = c.post("/api/conversations?reuse=1").json()
        assert b["id"] == a["id"] and b.get("reused")
        # without reuse (phone / old consoles) a new one is always made
        assert c.post("/api/conversations").json()["id"] != a["id"]


def test_touched_chat_is_never_reused(env):
    from app.events import bus
    with _client(env) as c:
        a = c.post("/api/conversations?reuse=1").json()["id"]
        bus.publish(a, "reminder_due", {"id": "r1", "text": "doodh"})     # a background note landed in it
        b = c.post("/api/conversations?reuse=1").json()["id"]
        assert b != a
        from app.db import Message, session
        with session() as s:
            s.add(Message(conversation_id=b, role="user", content="hi", display="hi"))
        assert c.post("/api/conversations?reuse=1").json()["id"] not in (a, b)


def test_console_wiring():
    assert "/api/conversations?reuse=1'" in JS
    assert "reuse=1&project_id=" in JS
    assert "e.payload?.source !== 'greeting')" in JS            # a greeting-only chat opens on the home
    assert "ev.payload?.source !== 'greeting') CH.unread(c)" in JS   # the greeting never marks a chat unread


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.23")
    assert "+27" in (ROOT / "pubspec.yaml").read_text()
