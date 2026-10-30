"""v0.237.0 the console chat list shows only chats she wrote in; console notes never show in a title."""
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def test_empty_chats_hidden_from_console_list(env):
    from app.main import app
    from app.db import Message, session
    with TestClient(app) as c:
        empty = c.post("/api/conversations").json()["id"]
        wrote = c.post("/api/conversations").json()["id"]
        pinned = c.post("/api/conversations").json()["id"]
        with session() as s:
            s.add(Message(conversation_id=wrote, role="user", content="x",
                          display="Mausam batao\n\n[Web console language preference: Reply in English]"))
        c.patch(f"/api/conversations/{pinned}", json={"pinned": True})
        rows = {r["id"]: r for r in c.get("/api/console/conversations").json()["conversations"]}
        assert empty not in rows and wrote in rows and pinned in rows
        assert rows[wrote]["title"] == "Mausam batao"
        # the phone's list is unchanged: every chat
        ids = [r["id"] for r in c.get("/api/conversations").json()["conversations"]]
        assert empty in ids


def test_plain_strips_console_notes():
    from app.chats import plain
    assert plain("Hi\n\n[Web console mode: deep research]\n\n[Web console place: Hoola PC]") == "Hi"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.307.0"
    assert "0.307.0+347" in (ROOT / "pubspec.yaml").read_text()
