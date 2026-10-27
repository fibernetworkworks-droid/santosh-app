"""Hoola Reels: a shared reel becomes something useful (save, remind, shop, family, fact-check), official routes only."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.reels import links

RECIPE = {"title": "Paneer butter masala in 10 min", "summary": "Chef 10 minute mein paneer butter masala banata hai.",
          "language": "Hindi", "kind": "recipe", "tags": ["paneer", "dinner"],
          "products": [{"name": "Kadai 24cm", "brand": "Prestige", "search": "prestige kadai 24cm"}],
          "places": [{"name": "Juhu Beach", "city": "Mumbai"}],
          "recipe": {"dish": "Paneer butter masala", "ingredients": ["paneer 200g", "butter", "tamatar"], "steps": ["Pyaaz bhuno"]},
          "events": [{"what": "Big Billion Days sale", "when": "25 October"}],
          "claims": ["Paneer khane se 10 din mein 5 kilo weight kam hota hai"],
          "song": "Kesariya - Arijit Singh", "warnings": [{"type": "health_claim", "why": "weight loss claim"}, {"type": "bogus"}],
          "seen": "video", "ignored_field": "x"}


def test_links_from_every_app():
    f = links.find
    assert f("Check this https://youtube.com/shorts/AbCdEf12345?si=xyz") == {
        "platform": "youtube", "id": "AbCdEf12345", "url": "https://www.youtube.com/shorts/AbCdEf12345", "key": "youtube:AbCdEf12345"}
    assert f("https://youtu.be/AbCdEf12345")["key"] == "youtube:AbCdEf12345"
    ig = f("https://www.instagram.com/reel/C9xYz_AbC12/?igsh=MWQ1ZGUxMzBkMA==")
    assert ig["platform"] == "instagram" and ig["url"] == "https://www.instagram.com/reel/C9xYz_AbC12"
    assert f("https://www.facebook.com/reel/1234567890")["platform"] == "facebook"
    assert f("https://fb.watch/abcDEF/")["platform"] == "facebook"
    assert f("https://www.snapchat.com/spotlight/W7_EDlXWTBiXAEEniNoMPwAAYYmJ0")["platform"] == "snapchat"
    assert f("https://mojapp.in/@user/video/12345abc")["platform"] == "moj"
    assert f("hello https://example.com/reel/123") is None and f("") is None
    assert links.caption_text("Wow recipe!! https://www.instagram.com/reel/X1/ #food", None) == "Wow recipe!! #food"


@pytest.fixture()
def reels(env, monkeypatch):
    from app.reels import service as rs
    calls = []

    def fake(parts):
        calls.append(parts)
        return dict(RECIPE)
    monkeypatch.setattr(rs, "_ask_gemini", fake)

    async def fake_search(q):
        return {"answer": "GALAT: aisa koi saboot nahi hai, doctor bhi nahi maante.", "sources": [{"title": "WHO", "url": "https://who.int"}]}
    from app import web
    monkeypatch.setattr(web, "google_search", fake_search)
    return calls


def test_youtube_short_is_watched_once_for_everyone(reels):
    from app.reels import service as rs
    v = rs.look_link("default", "Dekho https://youtube.com/shorts/AbCdEf12345?si=1")
    assert v["platform_name"] == "YouTube Shorts" and v["seen"] == "video" and v["needs_video"] is False
    assert reels[0][0] == {"uri": "https://www.youtube.com/shorts/AbCdEf12345"}      # official Gemini YouTube-URL input
    assert v["kind"] == "recipe" and v["recipe"]["ingredients"][0] == "paneer 200g"
    assert v["products"][0]["links"][0]["url"].startswith("https://www.amazon.in/s?k=prestige")
    assert v["places"][0]["map"].startswith("https://www.google.com/maps/search/?api=1&query=Juhu")
    assert [w["type"] for w in v["warnings"]] == ["health_claim"] and "doctor" in v["warnings"][0]["say"]
    assert "ignored_field" not in v and v["ai_label"]
    again = rs.look_link("someone-else", "https://youtu.be/AbCdEf12345")
    assert again["cached"] is True and again["reel_id"] == v["reel_id"] and len(reels) == 1


def test_instagram_gives_only_the_link(reels):
    from app.reels import service as rs
    v = rs.look_link("default", "https://www.instagram.com/reel/C9xYz_AbC12/?igsh=abc")
    assert v["needs_video"] is True and "Screen Recorder" in v["how_to_show"] and reels == []    # no AI call for a bare link
    v2 = rs.look_link("default", "Ghar baithe kamao 5000 daily, DM for link https://www.instagram.com/reel/Z1Z1Z1Z1/")
    assert v2["seen"] == "text" and any(w["type"] == "scam_signs" for w in v2["warnings"])
    with pytest.raises(rs.ReelError):
        rs.look_link("default", "no link here")
    with pytest.raises(rs.ReelError):                        # another owner's private look is not visible
        rs.get("other", v["reel_id"])


def test_own_recording_is_understood(reels):
    from app.reels import service as rs
    data = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 2000
    v = rs.look_file("default", "screen.mp4", "video/mp4", data, "https://www.instagram.com/reel/C9xYz_AbC12/")
    assert v["seen"] == "video" and v["platform"] == "instagram" and reels[0][0]["mime"] == "video/mp4"
    assert rs.look_file("default", "screen.mp4", "video/mp4", data)["cached"] is True
    with pytest.raises(rs.ReelError):
        rs.look_file("default", "a.txt", "text/plain", b"hello")


def test_five_actions_over_the_api(reels):
    from app import main
    with TestClient(main.app) as c:
        c.post("/api/conversations")
        v = c.post("/api/reels/look", json={"text": "https://youtube.com/shorts/AbCdEf12345"}).json()
        rid = v["reel_id"]
        # 1 save + find again
        assert c.post(f"/api/reels/{rid}/save", json={"note": "Sunday dinner"}).json()["saved"] is True
        found = c.get("/api/reels", params={"q": "wo paneer wali reel"}).json()["reels"]
        assert [x["reel_id"] for x in found] == [rid] and found[0]["note"] == "Sunday dinner"
        assert c.get("/api/reels", params={"q": "goa trip"}).json()["reels"] == []
        # 2 remind
        r = c.post(f"/api/reels/{rid}/remind", json={"when": "2099-01-01T19:00"}).json()
        assert "Paneer butter masala" in r["reminder"]["text"] and "youtube.com/shorts" in r["reminder"]["text"]
        assert c.post(f"/api/reels/{rid}/remind", json={"when": "2001-01-01T19:00"}).status_code == 400
        # 3 shop
        s = c.post(f"/api/reels/{rid}/shop", json={}).json()
        assert "Prestige Kadai 24cm" in s["added"] and "paneer 200g" in s["added"] and s["list"] == "shopping"
        assert c.post(f"/api/reels/{rid}/shop", json={"items": ["butter"]}).json()["added"] == []
        # 4 family message (the owner sends it from the share sheet)
        t = c.get(f"/api/reels/{rid}/share").json()["text"]
        assert "Paneer butter masala" in t and "AI se" in t and "youtube.com/shorts/AbCdEf12345" in t
        # 5 ye sach hai?
        chk = c.post(f"/api/reels/{rid}/check").json()
        assert chk["overall"] == "galat" and chk["checks"][0]["sources"][0]["url"] == "https://who.int"
        assert c.get(f"/api/reels/{rid}").json()["overall"] == "galat"
        assert c.delete(f"/api/reels/{rid}/save").json()["removed"] is True
        assert c.get("/api/reels").json()["reels"] == []
        assert c.get("/api/reels/nope").status_code == 404


def test_avatar_reel_tool(reels):
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.db import Conversation, session
    with session() as s:
        conv = Conversation(tenant_id="default")
        s.add(conv)
        s.flush()
        cid = conv.id
    ctx = Ctx("default", cid)
    v = asyncio.run(dispatch("reel", {"action": "look", "link": "https://youtube.com/shorts/AbCdEf12345"}, ctx))
    assert v["title"].startswith("Paneer") and "links" not in v["products"][0] and v["warnings"]
    asyncio.run(dispatch("reel", {"action": "save", "reel_id": v["reel_id"]}, ctx))
    got = asyncio.run(dispatch("reel", {"action": "saved", "query": "paneer"}, ctx))
    assert got["reels"][0]["reel_id"] == v["reel_id"]
    chk = asyncio.run(dispatch("reel", {"action": "check", "reel_id": v["reel_id"]}, ctx))
    assert chk["overall"] == "galat"
    with pytest.raises(ToolError):
        asyncio.run(dispatch("reel", {"action": "look"}, ctx))
    from app.voiceid.permissions import allowed
    assert allowed("family", "reel")
