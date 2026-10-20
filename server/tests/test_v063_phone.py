"""v0.63 Phone mein Hoola, server half: newest GitHub APK for the in-app updater, last-N messages for bubble / widget."""
import httpx
from fastapi.testclient import TestClient


def _rel(tag, apk=True, digest="sha256:" + "ab" * 32, **kw):
    assets = [{"name": "app-release.apk", "size": 61_000_000, "digest": digest,
               "browser_download_url": f"https://github.com/o/r/releases/download/{tag}/app-release.apk"}] if apk else []
    return {"tag_name": tag, "draft": False, "prerelease": False, "assets": assets,
            "body": "v0.62.0: Phone mein Hoola\n\nCo-Authored-By: x\nClaude-Session: y", "published_at": "2026-10-20T16:00:00Z", **kw}


def test_latest_picks_the_newest_app_release(env, monkeypatch):
    from app import appupdate
    seen = []

    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(200, json=[_rel("desktop-latest"), _rel("v0.60.0-b120"), _rel("v0.61.0-b121"),
                                         _rel("v0.62.0-b122", apk=False), _rel("v0.63.0-b123", draft=True),
                                         _rel("v0.9.0-b5")])
    monkeypatch.setattr(appupdate, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(appupdate, "_cache", {"at": 0.0, "value": None})
    r = appupdate.latest()
    assert r["tag"] == "v0.61.0-b121" and r["version"] == "0.61.0" and r["build"] == 121
    assert r["sha256"] == "ab" * 32 and r["size"] == 61_000_000 and r["apk_url"].startswith("https://github.com/")
    assert "Co-Authored-By" not in r["notes"] and "Phone mein Hoola" in r["notes"]
    assert "/repos/fibernetworkworks-droid/santosh-app/releases" in seen[0]
    appupdate.latest()
    assert len(seen) == 1                     # cached
    assert appupdate.newer("0.61.0", "0.59.0") and appupdate.newer("0.61.0", "0.60.9") and not appupdate.newer("0.61.0", "0.61.0")
    assert not appupdate.newer("0.9.0", "0.61.0")


def test_endpoint_says_if_an_update_is_there(env, monkeypatch):
    from app import appupdate
    from app.main import app
    monkeypatch.setattr(appupdate, "_transport", httpx.MockTransport(lambda req: httpx.Response(200, json=[_rel("v0.61.0-b121")])))
    monkeypatch.setattr(appupdate, "_cache", {"at": 0.0, "value": None})
    c = TestClient(app)
    assert c.get("/api/app/latest", params={"current": "0.59.0"}).json()["available"] is True
    assert c.get("/api/app/latest", params={"current": "0.61.0"}).json()["available"] is False


def test_github_down_keeps_the_last_answer(env, monkeypatch):
    from app import appupdate
    monkeypatch.setattr(appupdate, "_cache", {"at": 0.0, "value": None})
    monkeypatch.setattr(appupdate, "_transport", httpx.MockTransport(lambda req: httpx.Response(500)))
    assert appupdate.check("0.59.0")["available"] is False
    monkeypatch.setattr(appupdate, "_transport", httpx.MockTransport(lambda req: httpx.Response(200, json=[_rel("v0.61.0-b121")])))
    assert appupdate.latest(force=True)["tag"] == "v0.61.0-b121"
    monkeypatch.setattr(appupdate, "_transport", httpx.MockTransport(lambda req: httpx.Response(403, json={"message": "rate"})))
    assert appupdate.latest(force=True)["tag"] == "v0.61.0-b121"


def test_non_github_download_links_are_ignored(env, monkeypatch):
    from app import appupdate
    bad = _rel("v0.70.0-b200")
    bad["assets"][0]["browser_download_url"] = "https://evil.example/app-release.apk"
    monkeypatch.setattr(appupdate, "_cache", {"at": 0.0, "value": None})
    monkeypatch.setattr(appupdate, "_transport", httpx.MockTransport(lambda req: httpx.Response(200, json=[bad, _rel("v0.61.0-b121")])))
    assert appupdate.latest()["version"] == "0.61.0"


def test_messages_limit_gives_the_last_few_in_order(env):
    from app.db import session
    from app.main import app
    from app.db import Message
    c = TestClient(app)
    conv = c.post("/api/conversations").json()["id"]
    with session() as s:
        for i in range(30):
            s.add(Message(conversation_id=conv, role="user" if i % 2 == 0 else "assistant", content=f"m{i}", display=f"m{i}"))
    all_ = c.get(f"/api/conversations/{conv}/messages").json()["messages"]
    last = c.get(f"/api/conversations/{conv}/messages", params={"limit": 5}).json()["messages"]
    assert len(all_) == 31 and [m["text"] for m in last] == ["m25", "m26", "m27", "m28", "m29"]
