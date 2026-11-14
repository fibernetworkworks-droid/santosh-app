"""v0.900 SAB CARD NAYE: every card in the phone's new chat is drawn in the new design. The phone's real checks are
test/all_cards_test.dart + the picture tests 57 / 58; these pin the server field the long-task clock reads and the
shape of the phone code."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ALL = (REPO / "lib" / "ui" / "chat" / "hoola_cards_all.dart").read_text()
CHAT = (REPO / "lib" / "ui" / "chat" / "hoola_chat.dart").read_text()
TALK = (REPO / "lib" / "ui" / "talk" / "hoola_talk.dart").read_text()


def test_goal_event_carries_its_clock(env, monkeypatch):
    from app.agent import goal
    from app.events import bus
    seen = []
    monkeypatch.setattr(bus, "publish", lambda conv, kind, payload, *a, **k: seen.append((kind, payload)))
    view = {"id": "gr1", "goal": "Research banks", "status": "working", "stage": "", "pct": 0, "steps": [],
            "done": 0, "total": 0, "reason": "", "started_at": "2026-11-14T04:31:00+00:00",
            "updated_at": "2026-11-14T04:35:12+00:00"}
    goal._publish("c1", view)
    kind, p = seen[-1]
    assert kind == "goal"
    assert p["started_at"] == "2026-11-14T04:31:00+00:00" and p["updated_at"] == "2026-11-14T04:35:12+00:00"


def test_no_card_in_the_old_dark_frame():
    assert "_OldCard" not in CHAT and "feedCard(" not in CHAT
    assert "hoolaCardAll(context, app, it)" in CHAT
    assert "hoolaCardAll(context, app, focus)" in TALK and "santoshTheme" not in TALK


def test_every_kind_has_a_new_card():
    for k in ("goal", "operator_task", "operator_ask", "memory_saved", "memory_used", "compact", "google_reconnect",
              "link", "calendar_event", "maps_places", "photo_made"):
        assert f"case '{k}':" in ALL, k
    # every other kind: the new card + its full old card behind Details / Review
    assert "return HCLegacy(app: app, it: it);" in ALL
    assert "'Details'" in ALL and "'Review'" in ALL and "showOldCardSheet" in ALL
    # money and secrets never get a box in the chat card
    assert "{'otp', 'captcha', 'secret', 'payment', 'takeover'}" in ALL


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.906.0"
    assert "version: 0.906.0+905" in (REPO / "pubspec.yaml").read_text()
