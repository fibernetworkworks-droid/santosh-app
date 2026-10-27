"""v0.127 Hoola Screen: view-only live board for a second screen (mini screen / TV / any browser)."""
import time

from fastapi.testclient import TestClient

from app.db import Conversation, session
from app.events import bus


def _conv(tenant="default"):
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


def test_token_signed_expiring_and_revocable(env):
    from app import screen
    tok, exp = screen.make_token("default", 1)
    assert screen.tenant_of(tok) == "default" and exp > time.time()
    body, sig = tok.split(".")
    for bad in (f"{body}.x{sig[1:]}", "nope", "", f"{body}"):
        try:
            screen.tenant_of(bad)
            raise AssertionError(bad)
        except screen.ScreenError:
            pass
    screen.revoke("default")
    try:
        screen.tenant_of(tok)
        raise AssertionError("revoked link still works")
    except screen.ScreenError as e:
        assert "band" in str(e)
    assert screen.tenant_of(screen.make_token("default")[0]) == "default"
    assert screen.make_token("default", 9999)[1] <= time.time() + screen.MAX_DAYS * 86400 + 5


def test_board_shows_live_work_cards_and_masks(env):
    from app import screen
    conv = _conv()
    other = _conv("someone_else")
    bus.publish(conv, "work", {"id": "w1", "tool": "browse_web", "scene": "browser", "phase": "done", "label": "Site khola"})
    bus.publish(conv, "work", {"id": "w2", "tool": "email", "scene": "email", "phase": "start",
                               "label": "Email bhej raha 9876543210 ko"})
    bus.publish(conv, "message", {"role": "assistant", "text": "Account 123456789012 check kiya"})
    bus.publish(conv, "operator_ask", {"id": "a1", "kind": "otp", "site": "uidai", "reason": "OTP 445566 bharo"})
    bus.publish(other, "work", {"id": "x", "phase": "start", "label": "SECRET of another owner"})
    b = screen.board("default")
    labels = [x["label"] for x in b["now"]]
    assert any("Email bhej raha" in l for l in labels) and "9876543210" not in str(b)
    assert [x["label"] for x in b["recent"]] == ["Site khola"]
    assert "123456789012" not in b["said"] and "SECRET" not in str(b)
    ask = [c for c in b["cards"] if c["kind"] == "operator_ask"]
    assert ask and "445566" not in str(ask) and "phone" in ask[0]["body"]
    # a step that finishes leaves "now"
    bus.publish(conv, "work", {"id": "w2", "phase": "done", "label": "Email bhej diya"})
    b = screen.board("default")
    assert not b["now"] and b["recent"][0]["label"] == "Email bhej diya"


def test_api_link_page_board_and_revoke(env):
    from app import main
    conv = _conv()
    bus.publish(conv, "work", {"id": "w1", "phase": "start", "label": "Poster bana raha"})
    with TestClient(main.app) as c:
        ln = c.get("/api/screen/link").json()
        assert ln["path"].startswith("/screen/") and "dekhne" in ln["say"]
        pg = c.get(ln["path"])
        assert pg.status_code == 200 and "Hoola Screen" in pg.text
        assert "default-src 'none'" in pg.headers["content-security-policy"]
        bd = c.get(ln["path"].replace("/screen/", "/api/screen/") + "/board").json()
        assert bd["now"][0]["label"] == "Poster bana raha"
        assert c.get("/api/screen/preview").json()["now"]
        assert c.get("/api/screen/garbage.x/board").status_code == 403
        assert c.post("/api/screen/revoke").json()["ok"]
        assert c.get(ln["path"]).status_code == 403
        assert c.get(ln["path"].replace("/screen/", "/api/screen/") + "/board").status_code == 403
        # nothing on the board route can change anything
        assert c.post(ln["path"].replace("/screen/", "/api/screen/") + "/board").status_code == 405
