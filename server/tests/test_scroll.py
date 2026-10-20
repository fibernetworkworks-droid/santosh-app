"""Reel scroll analysis: Usage Access numbers + the owner's own history download, summaries only."""
import asyncio
import io
import json
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.reels import scroll

TODAY = date(2026, 10, 20)


def _day(d, ig, yt=0.0, late=0.0, sessions=10, longest=20.0):
    hours = [0.0] * 24
    hours[21] = ig + yt - late
    hours[23] = late
    apps = {"Instagram": {"min": ig, "sessions": sessions, "longest": longest}}
    if yt:
        apps["YouTube"] = {"min": yt, "sessions": 3, "longest": 15}
    apps["NotAReelApp"] = {"min": 999, "sessions": 1, "longest": 1}
    return {"date": d, "apps": apps, "hours": hours}


def test_week_report(env):
    week = [_day(f"2026-10-{14 + i:02d}", 60 + i * 10, 20, late=30 if i in (5, 6) else 0, longest=45 if i == 6 else 20)
            for i in range(7)]
    prev = [_day(f"2026-10-{7 + i:02d}", 40, 10) for i in range(7)]
    assert scroll.sync("default", week + prev + [{"date": "bad"}])["days"] == 14
    scroll.set_budget("default", 90)
    r = scroll.report("default", 7, today=TODAY)
    assert r["has_data"] and [a["app"] for a in r["apps"]] == ["Instagram", "YouTube"]      # unknown apps dropped
    assert r["total_min"] == sum(60 + i * 10 + 20 for i in range(7)) == 770
    assert r["avg_text"] == "1 ghanta 50 min" and r["reels_est"] == 770 * 2
    assert r["trend_pct"] == 120                         # 110/day vs 50/day
    assert r["late_days"] == 2 and r["late_min"] == 60 and r["peak_hour"] == 21 and r["peak_text"] == "raat 9 baje"
    assert r["longest"] == {"app": "Instagram", "min": 45.0, "date": "2026-10-20"}
    assert r["today_min"] == 140 and r["over_budget"] is True
    text = " ".join(r["insights"])
    assert "120% zyada" in text and "Raat 11 ke baad 2 din" in text and "limit" in text and "Instagram" in text
    empty = scroll.report("nobody", 7, today=TODAY)
    assert not empty["has_data"] and "Usage Access" in empty["insights"][0]


YT_JSON = json.dumps([
    {"header": "YouTube", "title": "Watched 5 min paneer recipe", "titleUrl": "https://www.youtube.com/watch?v=a1",
     "subtitles": [{"name": "Kabita's Kitchen"}], "time": "2026-10-19T17:10:00.000Z"},
    {"header": "YouTube", "title": "Watched Nifty tip: 100% profit tomorrow", "titleUrl": "https://www.youtube.com/watch?v=a2",
     "subtitles": [{"name": "Stock Guru 007"}], "time": "2026-10-19T18:40:00.000Z"},
    {"header": "YouTube", "title": "Searched for paneer", "time": "2026-10-19T17:00:00.000Z"},
    {"header": "YouTube Music", "title": "Watched song", "time": "2026-10-19T17:00:00.000Z"},
])
YT_HTML = ('<div class="content-cell">Watched&nbsp;<a href="https://www.youtube.com/watch?v=b1">Gym &amp; diet</a><br>'
           '<a href="https://www.youtube.com/channel/x">FitIndia</a><br>Oct 18, 2026, 11:45:10 PM IST<br></div>')
IG_WATCHED = json.dumps({"impressions_history_videos_watched": [
    {"string_map_data": {"Author": {"value": "chef.ranveer"}, "Time": {"timestamp": 1792400000}}},
    {"string_map_data": {"Author": {"value": "chef.ranveer"}, "Time": {"timestamp": 1792410000}}},
    {"string_map_data": {"Author": {"value": "memes.daily"}, "Time": {"timestamp": 1792420000}}}]})
IG_LIKED = json.dumps({"likes_media_likes": [
    {"title": "travel.goa", "string_list_data": [{"href": "https://www.instagram.com/p/X/", "timestamp": 1792430000}]}]})


def test_history_parsers():
    yt = scroll.parse_youtube_json(YT_JSON)
    assert [i["title"] for i in yt] == ["5 min paneer recipe", "Nifty tip: 100% profit tomorrow"]
    assert yt[0]["author"] == "Kabita's Kitchen" and yt[0]["t"] > 0
    h = scroll.parse_youtube_html(YT_HTML)
    assert h[0]["title"] == "Gym & diet" and h[0]["author"] == "FitIndia" and h[0]["t"] > 0
    ig = scroll.parse_instagram_json("your_instagram_activity/videos_watched.json", IG_WATCHED)
    assert [i["author"] for i in ig] == ["chef.ranveer", "chef.ranveer", "memes.daily"] and ig[0]["kind"] == "watched"
    liked = scroll.parse_instagram_json("likes/liked_posts.json", IG_LIKED)
    assert liked[0]["author"] == "travel.goa" and liked[0]["kind"] == "liked"
    assert scroll.parse_instagram_json("messages/inbox.json", IG_WATCHED) == []          # DMs are never read


@pytest.fixture()
def taste(env, monkeypatch):
    seen = []

    def fake(prompt):
        seen.append(prompt)
        return {"topics": [{"name": "Khana / recipes", "share": 55}, {"name": "Share market tips", "share": 30}, {"x": 1}],
                "summary": "Aapki feed mein zyada khana aur share tips hain.", "good": ["Recipes se naya seekh rahe ho"],
                "watch_out": ["Unknown finfluencers ke stock tips"], "suggestions": ["SEBI-registered creators follow kijiye"]}
    monkeypatch.setattr(scroll, "_ask_taste", fake)
    return seen


def test_import_keeps_only_the_summary(taste):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Takeout/YouTube and YouTube Music/history/watch-history.json", YT_JSON)
        z.writestr("instagram/ads_information/ads_and_topics/videos_watched.json", IG_WATCHED)
        z.writestr("instagram/your_instagram_activity/likes/liked_posts.json", IG_LIKED)
        z.writestr("instagram/messages/inbox/friend/message_1.json", '{"messages": [{"content": "secret"}]}')
    r = scroll.import_history("default", "export.zip", buf.getvalue())
    yt, ig = r["imported"]["youtube"], r["imported"]["instagram"]
    assert yt["items"] == 2 and yt["top_creators"][0]["count"] == 1 and yt["topics"][0]["name"] == "Khana / recipes"
    assert len(yt["topics"]) == 2 and yt["watch_out"] and yt["ai_label"]
    assert ig["items"] == 4 and ig["top_creators"][0] == {"name": "chef.ranveer", "count": 2} and ig["kinds"] == {"watched": 3, "liked": 1}
    assert "secret" not in json.dumps(r) and all("secret" not in p for p in taste)
    assert any("Kabita's Kitchen | 5 min paneer recipe" in p for p in taste)
    with pytest.raises(scroll.ScrollError):
        scroll.import_history("default", "x.json", b'{"nothing": 1}')
    rep = scroll.report("default", 7, today=TODAY)
    assert set(rep["tastes"]) == {"youtube", "instagram"}
    assert scroll.forget("default")["forgotten"] and scroll.report("default", 7, today=TODAY)["tastes"] == {}


def test_api_and_avatar(taste):
    from app import main
    from app.agent.tools import Ctx, dispatch
    with TestClient(main.app) as c:
        cid = c.post("/api/conversations").json()["id"]
        d = date.today().isoformat()
        assert c.post("/api/reels/scroll/sync", json={"days": [_day(d, 75, 15)]}).json() == {"days": 1}
        assert c.post("/api/reels/scroll/budget", json={"minutes": 60}).json() == {"budget_min": 60}
        r = c.get("/api/reels/scroll/report").json()
        assert r["today_min"] == 90 and r["over_budget"] is True
        up = c.post("/api/reels/scroll/import", files={"file": ("watch-history.json", YT_JSON.encode(), "application/json")}).json()
        assert up["imported"]["youtube"]["items"] == 2
        assert c.post("/api/reels/scroll/import", files={"file": ("a.txt", b"hello", "text/plain")}).status_code == 400
        out = asyncio.run(dispatch("reel", {"action": "scroll"}, Ctx("default", cid)))
        assert out["over_budget"] is True and out["apps"][0]["app"] == "Instagram"
        assert out["watching"]["youtube"]["topics"][0]["name"] == "Khana / recipes"
        assert c.delete("/api/reels/scroll").json()["forgotten"] is True
        assert c.get("/api/reels/scroll/report").json()["has_data"] is False
