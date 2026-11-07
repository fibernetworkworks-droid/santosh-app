"""v0.342 APNA CODE (App Sahayak Phase 9): her app's whole code (android/ + ios/ + README + CHANGELOG) in HER GitHub, one new
commit per build, through the same card + her-tap-only push as the website export; never a signing key or a password."""
import base64
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _shop_app
from tests.test_v0332_iphone import FakeMac, FakeSwift
from tests.test_v128_appdesign import T
from tests.test_v132_android import FakeBuild, droid_env  # noqa: F401  (fixture)


class FakeGitHub:
    """github.com stand-in: records blobs / trees / commits; the repo exists after the first push."""
    def __init__(self):
        self.repo = False
        self.blobs, self.trees, self.commits, self.refs = {}, [], [], {}

    def __call__(self, req: httpx.Request) -> httpx.Response:
        assert req.headers["Authorization"] == "Bearer tok"
        p, m = req.url.path, req.method
        body = json.loads(req.content) if req.content else None
        j = lambda o, code=200: httpx.Response(code, json=o)        # noqa: E731
        if p == "/user":
            return j({"login": "meghana"})
        if p == "/repos/meghana/sharma-kirana-app" and m == "GET":
            return j({"default_branch": "main"}) if self.repo else j({"message": "Not Found"}, 404)
        if p == "/user/repos":
            assert body["private"] is True and body["name"] == "sharma-kirana-app"
            self.repo = True
            return j({"default_branch": "main"}, 201)
        if p.endswith("/git/ref/heads/main"):
            return j({"object": {"sha": self.refs["main"]}}) if "main" in self.refs else j({"message": "Not Found"}, 404)
        if p.endswith("/git/blobs"):
            sha = f"b{len(self.blobs)}"
            self.blobs[sha] = base64.b64decode(body["content"]) if body["encoding"] == "base64" else body["content"].encode()
            return j({"sha": sha}, 201)
        if p.endswith("/git/trees"):
            assert "base_tree" not in body                             # a full tree: removed files leave the repo too
            self.trees.append(body["tree"])
            return j({"sha": f"t{len(self.trees)}"}, 201)
        if p.endswith("/git/commits"):
            self.commits.append(body)
            return j({"sha": f"c{len(self.commits)}"}, 201)
        if p.endswith("/git/refs/heads/main") and m == "PATCH":
            self.refs["main"] = body["sha"]
            return j({})
        if p.endswith("/git/refs") and m == "POST":
            self.refs["main"] = body["sha"]
            return j({}, 201)
        raise AssertionError(f"unexpected {m} {p}")


@pytest.fixture
def gh(monkeypatch):
    from app.site import github as GH
    fake = FakeGitHub()
    GH.set_transport(httpx.MockTransport(fake))
    monkeypatch.setattr(GH, "_token", lambda tenant: "tok")
    yield fake
    GH.set_transport(None)


def test_app_code_to_her_github_two_builds(droid_env, gh, monkeypatch):
    fake, _kt = droid_env
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.appmaker.ios import service as IO
    from app.main import app
    c = TestClient(app)
    aid, conv = _shop_app(fake)
    assert c.post(f"/api/apps/{aid}/github", json={}).status_code == 400          # no build yet: nothing to send
    RN.set_runner(FakeBuild())
    monkeypatch.setattr(IO, "_ask", FakeSwift())
    IO.set_runner(FakeMac())
    try:
        AN.build(T, aid, conv)
        IO.build(T, aid, conv)
        card = c.post(f"/api/apps/{aid}/github", json={}).json()
        assert card["repo"] == "meghana/sharma-kirana-app" and card["private"] is True and card["files"] > 40
        assert "iPhone" in card["say"] and "haan" in card["say"]
        assert gh.commits == []                                          # the card alone sends nothing
        assert c.post(f"/api/sites-github/{card['id']}/push", json={"hash": "wrong"}).status_code == 400
        done = c.post(f"/api/sites-github/{card['id']}/push", json={"hash": card["hash"]}).json()
        assert done["ok"] and done["url"] == "https://github.com/meghana/sharma-kirana-app"
        files = {t["path"]: gh.blobs[t["sha"]] for t in gh.trees[0]}
        assert "android/settings.gradle.kts" in files and "android/app/src/main/java/hoola/kit/Backend.kt" in files
        assert "ios/project.yml" in files and "ios/Sources/Kit/Backend.swift" in files
        assert "README.md" in files and "CHANGELOG.md" in files and ".gitignore" in files
        assert not [p for p in files if p.endswith((".p12", ".jks", ".p8")) or "/keys/" in p or p.startswith("android/keys")]
        gradle = files["android/app/build.gradle.kts"].decode()
        key = AN._key(AN.AS._load(aid))
        assert key["password"] not in gradle and '?: ""' in gradle           # the preview key's password never leaves
        assert next(t["mode"] for t in gh.trees[0] if t["path"] == "android/gradlew") == "100755"
        assert gh.commits[0]["parents"] == [] and gh.commits[0]["message"].startswith("Hoola app build 1")
        assert "Android build 1" in files["CHANGELOG.md"].decode() and "xcodegen generate" in files["README.md"].decode()
        assert c.post(f"/api/sites-github/{card['id']}/push", json={"hash": card["hash"]}).status_code == 400   # once
        # build 2 -> a NEW commit on top of the first (her repo keeps the history)
        AN.build(T, aid, conv)
        card2 = c.post(f"/api/apps/{aid}/github", json={}).json()
        c.post(f"/api/sites-github/{card2['id']}/push", json={"hash": card2["hash"]})
        assert gh.commits[1]["parents"] == ["c1"] and gh.commits[1]["message"].startswith("Hoola app build 2")
        v = c.get(f"/api/apps/{aid}/github").json()
        assert [x["build"] for x in v["commits"]] == [2, 1] and v["ready"]
        # a card made before a newer build cannot push the old content
        card3 = c.post(f"/api/apps/{aid}/github", json={}).json()
        AN.build(T, aid, conv)
        r = c.post(f"/api/sites-github/{card3['id']}/push", json={"hash": card3["hash"]})
        assert r.status_code == 400 and "naya" in r.json()["detail"]
    finally:
        RN.set_runner(None)
        IO.set_runner(None)


def test_tool_makes_only_a_card(droid_env, gh):
    fake, _kt = droid_env
    from app.agent.app_tools import APP_TOOLS, _act
    from app.agent.tools import Ctx
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    aid, conv = _shop_app(fake)
    RN.set_runner(FakeBuild())
    try:
        AN.build(T, aid, conv)
        tool = next(t for t in APP_TOOLS if t["name"] == "app_banao")
        assert "github" in tool["input_schema"]["properties"]["action"]["enum"] and "never a signing key" in tool["description"]
        out = _act(Ctx(tenant_id=T, conversation_id=conv), "github", {"app": aid})
        assert out["repo"] == "meghana/sharma-kirana-app" and gh.commits == [] and not gh.repo
    finally:
        RN.set_runner(None)
