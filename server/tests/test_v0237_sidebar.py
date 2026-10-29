"""v0.237.0 the console sidebar adapts to its width; a chat with words is never titled "Naya chat"."""
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def test_sidebar_adapts():
    js, css = (CON / "v2.js").read_text(), (CON / "v2.css").read_text()
    assert "classList.toggle('narrow', e.contentRect.width < 236)" in js
    assert "#app .side.narrow .newc kbd,#app .side.narrow .sn kbd{display:none}" in css
    assert "#app .side .newc,#app .side .sn{white-space:nowrap;min-width:0}" in css


def test_untitled_not_naya(env):
    from app.main import app
    from app.db import Message, session
    with TestClient(app) as c:
        cid = c.post("/api/conversations").json()["id"]
        with session() as s:
            s.add(Message(conversation_id=cid, role="user", content="x", display=""))   # a file-only first message
            s.add(Message(conversation_id=cid, role="user", content="y",
                          display="[Web console language preference: Reply in English]"))
        row = next(r for r in c.get("/api/console/conversations").json()["conversations"] if r["id"] == cid)
        assert row["title"] == "Untitled chat"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.252.0"
    assert "0.252.0+292" in (ROOT / "pubspec.yaml").read_text()
