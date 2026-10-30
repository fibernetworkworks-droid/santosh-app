"""v0.227.4 each console chat keeps its own cards. The v0.158 rule (a card from ANY of her chats shows in every chat)
was made for the phone's single chat; with the console's many chats it poured every chat's files, pages and
briefings into whichever chat was open. The console now asks for `own=1`; the phone's timeline is unchanged."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

KEY = "owner-key-for-own-chat-tests"
H = {"Authorization": f"Bearer {KEY}"}
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def api(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import convs, main
    convs._CACHE.clear()
    with TestClient(main.app) as c:
        yield c, get_settings()
    get_settings.cache_clear()


def _conv(tenant):
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


def test_console_timeline_keeps_only_its_own_cards(api):
    c, st = api
    from app.events import bus
    t = st.tenant_id
    a, b = _conv(t), _conv(t)
    bus.publish(a, "message", {"role": "user", "text": "chat A"})
    bus.publish(a, "pc_file", {"id": "fA", "name": "a.pdf"})
    bus.publish(b, "message", {"role": "user", "text": "chat B"})
    bus.publish(b, "pc_file", {"id": "fB", "name": "video_platform.pdf"})
    bus.publish(b, "artifact", {"id": "pB", "title": "Build a single-page front-end"})

    own = c.get(f"/api/conversations/{a}/timeline?steps=1&own=1", headers=H).json()["events"]
    kinds = [(e["kind"], (e["payload"] or {}).get("id") or (e["payload"] or {}).get("text")) for e in own]
    assert ("pc_file", "fA") in kinds and ("message", "chat A") in kinds
    assert all(e["conv"] == a for e in own), kinds

    phone = c.get(f"/api/conversations/{a}/timeline", headers=H).json()["events"]   # the phone: v0.158 rule kept
    assert any((e["payload"] or {}).get("id") == "fB" for e in phone)


def test_console_asks_for_its_own_chat_and_never_mirrors():
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert js.count("&steps=1&own=1`") == 2
    assert "if (ev.conv && ev.conv !== conv) return;" in js
    assert "&& !LOADING && CONV) onEvent(ev);" not in js
    assert "!PROGRESS_POLICY.quiet(ev.kind,ev.payload)) CH.unread(c);" in js


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.282.0"
    assert "0.282.0+322" in (ROOT / "pubspec.yaml").read_text()
