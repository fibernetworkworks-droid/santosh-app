"""v0.227.2 - a long pasted brief no longer fails with 422: the server takes a message (and an edit) up to 32,000
characters, and the console sends anything longer as an attached .txt file instead of an error. Any 4xx stops the
console's retry loop at once."""
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
KEY = "owner-key-long-message"


def _conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def test_long_message_is_accepted_and_the_rest_refused(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from tests.test_campaign_flow import ScriptedClaude, text
    from app.agent import set_client
    set_client(ScriptedClaude([text("Theek hai.")]))
    from app.main import MESSAGE_MAX, app
    assert MESSAGE_MAX == 32000
    conv = _conv()
    H = {"Authorization": f"Bearer {KEY}"}
    brief = ("Build the first working version of a YouTube-style video platform. " * 120)[:7900]   # the owner's case: ~8k
    with TestClient(app) as c:
        assert c.post(f"/api/conversations/{conv}/messages", json={"text": brief}, headers=H).status_code == 202
        too_long = c.post(f"/api/conversations/{conv}/messages", json={"text": "x" * (MESSAGE_MAX + 1)}, headers=H)
        assert too_long.status_code == 422
        assert c.post(f"/api/conversations/{conv}/edit", json={"event_id": 1, "text": "y" * (MESSAGE_MAX + 1)},
                      headers=H).status_code == 422


def test_console_sends_longer_text_as_a_file():
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "const INLINE_MAX = 30000;" in js
    assert "if (text.length > INLINE_MAX) {" in js and "new File([text], `pasted-text-" in js
    assert "(er.status >= 400 && er.status < 500)" in js                    # 4xx never retried three times
    assert "if (t.length > 32000) return toast(" in js


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.275.0"
    assert "0.275.0+315" in (ROOT / "pubspec.yaml").read_text()
