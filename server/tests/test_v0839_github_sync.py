"""v0.839 GITHUB DO TARAF (L14 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L14"): an App Engine app and one GitHub branch, both
directions, plus import from a ZIP or a repository. The proof the plan asks for: the ROUND TRIP - app A pushed to a (fake)
GitHub, a change made on GitHub pulled back in under the app's own rules, the repository imported as app B whose files equal A's,
and the ZIP export imported back the same way. GitHub is a fake that speaks the Git Data API (no network)."""
import base64
import hashlib
import io
import json
import zipfile

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0814_app_engine import _refused, _tool, ae_env  # noqa: F401  (fixture + helpers)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

PAGE = ('export default function Home() {\n  return <main className="p-6 bg-surface text-ink"><h1 className="text-2xl">Sweets</h1></main>;\n}\n')


def sha(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


class FakeGitHub:
    """Just enough of GitHub's REST + Git Data API for one user ('asha') and her repositories."""

    def __init__(self):
        self.repos, self.n, self.log = {}, 0, []

    def _id(self, what: str) -> str:
        self.n += 1
        return hashlib.sha1(f"{what}{self.n}".encode()).hexdigest()

    def new_repo(self, name: str, files: dict[str, bytes] | None = None, private=True):
        r = {"private": private, "blobs": {}, "trees": {}, "commits": {}, "heads": {}}
        self.repos[name] = r
        if files is not None:
            self.commit(name, files)
        return r

    def commit(self, name: str, files: dict[str, bytes], parent_ok=True) -> str:
        r = self.repos[name]
        tree = {}
        for p, b in files.items():
            r["blobs"][sha(b)] = b
            tree[p] = sha(b)
        tid = self._id("tree")
        r["trees"][tid] = tree
        cid = self._id("commit")
        r["commits"][cid] = {"tree": tid, "parents": [r["heads"]["main"]] if "main" in r["heads"] else []}
        r["heads"]["main"] = cid
        return cid

    def files(self, name: str) -> dict[str, bytes]:
        r = self.repos[name]
        t = r["trees"][r["commits"][r["heads"]["main"]]["tree"]]
        return {p: r["blobs"][s] for p, s in t.items()}

    def __call__(self, req: httpx.Request) -> httpx.Response:
        path, m = req.url.path, req.method
        body = json.loads(req.content) if req.content else {}
        self.log.append((m, path))

        def J(x, code=200):
            return httpx.Response(code, json=x)
        if path == "/user":
            return J({"login": "asha"})
        if path == "/user/repos" and m == "POST":
            self.new_repo(body["name"], {"README.md": b"# new\n"}, body.get("private", True))
            return J({"default_branch": "main", "private": body.get("private", True)}, 201)
        parts = path.strip("/").split("/")
        if parts[0] != "repos":
            return J({"message": "no"}, 404)
        name = parts[2]
        r = self.repos.get(name)
        if r is None or parts[1] != "asha":
            return J({"message": "Not Found"}, 404)
        rest = "/".join(parts[3:])
        if rest == "":
            return J({"default_branch": "main", "private": r["private"]})
        if rest == "git/ref/heads/main":
            return J({"object": {"sha": r["heads"]["main"]}}) if "main" in r["heads"] else J({"message": "Not Found"}, 404)
        if rest.startswith("git/commits/") and m == "GET":
            return J({"tree": {"sha": r["commits"][parts[-1]]["tree"]}})
        if rest.startswith("git/trees/") and m == "GET":
            t = r["trees"][parts[-1]]
            return J({"truncated": False, "tree": [{"path": p, "type": "blob", "sha": s} for p, s in t.items()]})
        if rest == "git/blobs" and m == "POST":
            raw = base64.b64decode(body["content"]) if body.get("encoding") == "base64" else body["content"].encode()
            r["blobs"][sha(raw)] = raw
            return J({"sha": sha(raw)}, 201)
        if rest.startswith("git/blobs/") and m == "GET":
            return J({"encoding": "base64", "content": base64.b64encode(r["blobs"][parts[-1]]).decode()})
        if rest == "git/trees" and m == "POST":
            tid = self._id("tree")
            r["trees"][tid] = {e["path"]: e["sha"] for e in body["tree"]}
            return J({"sha": tid}, 201)
        if rest == "git/commits" and m == "POST":
            cid = self._id("commit")
            r["commits"][cid] = {"tree": body["tree"], "parents": body.get("parents", [])}
            return J({"sha": cid}, 201)
        if rest == "git/refs/heads/main" and m == "PATCH":
            if body.get("force") is not True and r["commits"][body["sha"]]["parents"] != [r["heads"]["main"]]:
                return J({"message": "Update is not a fast forward"}, 422)
            r["heads"]["main"] = body["sha"]
            return J({"ref": "refs/heads/main"})
        if rest == "git/refs" and m == "POST":
            r["heads"]["main"] = body["sha"]
            return J({"ref": body["ref"]}, 201)
        return J({"message": "unhandled " + path}, 404)


@pytest.fixture
def gh(ae_env):
    from app.site import dns
    from app.site import github as GH
    fake = FakeGitHub()
    GH.set_transport(httpx.MockTransport(fake))
    dns.set_key(T, "github", "ghp_" + "t" * 36)
    yield fake
    GH.set_transport(None)


def _app(name="Mithai orders"):
    aid = _tool(action="create", name=name)["id"]
    _tool(action="write", app=aid, path="src/pages/Home.tsx", code=PAGE)
    return aid


def _src(aid):
    from app.appengine import gitsync as GS
    from app.appengine import service as AE
    return GS.local_files(AE._load(T, aid))


# ---------------------------------------------------------------- 1. link, push, pull: the round trip
def test_round_trip_push_pull_and_import(gh):
    from app.appengine import gitsync as GS
    from app.appengine import service as AE
    aid = _app()
    with pytest.raises(GS.SyncError) as e:
        GS.link(T, aid, "mithai-app", True, confirm=False)
    assert e.value.code == 403                                                          # her tap first
    out = GS.link(T, aid, "mithai-app", True, confirm=True)
    assert out["linked"] and out["created"] and out["repo"] == "asha/mithai-app" and out["branch"] == "main"
    AE._save(aid, version=1)                                                            # a built version (the build itself is not the point)
    p = GS.push(T, aid, confirm=True)
    assert p["pushed"] and p["changed"] == 0
    remote = gh.files("mithai-app")
    assert remote["src/pages/Home.tsx"] == PAGE.encode() and "package.json" in remote and "src/lib/hoola.ts" in remote
    assert GS.push(T, aid, confirm=True)["pushed"] is False                              # nothing new
    # a change made on GitHub comes back under the app's own rules
    new_page = PAGE.replace("Sweets", "Fresh sweets").encode()
    files = dict(remote); files["src/pages/Home.tsx"] = new_page; files["src/pages/About.tsx"] = PAGE.replace("Home", "About").encode()
    gh.commit("mithai-app", files)
    cmp_ = GS.compare(T, aid)
    assert cmp_["remote_moved"] and {x["say"] for x in cmp_["changed"]} == {"src/pages/Home.tsx", "src/pages/About.tsx"} and not cmp_["conflicts"]
    with pytest.raises(GS.SyncError, match="Pull first"):
        GS.push(T, aid, confirm=True)                                                    # never over commits she has not pulled
    pl = GS.pull(T, aid, confirm=True)
    assert pl["pulled"] and sorted(pl["written"]) == ["src/pages/About.tsx", "src/pages/Home.tsx"]
    assert _src(aid)["src/pages/Home.tsx"] == new_page and "Fresh sweets" in AE.read_file(T, aid, "src/pages/Home.tsx")["code"]
    # a local change goes back as one commit on top
    _tool(action="write", app=aid, path="src/pages/Menu.tsx", code=PAGE.replace("Home", "Menu"))
    assert GS.status(AE._load(T, aid))["changes"] == [{"path": "src/pages/Menu.tsx", "what": "added"}]
    GS.push(T, aid, confirm=True)
    assert gh.files("mithai-app")["src/pages/Menu.tsx"].startswith(b"export default function Menu")
    # the repository imported as a NEW app has the same files; the ZIP export imported back too
    b = GS.import_github(T, "Copy from GitHub", "asha/mithai-app", confirm=True)
    assert not b["refused"] and b["linked"] == "asha/mithai-app"
    a_src, b_src = _src(aid), _src(b["id"])
    for k in ("src/pages/Home.tsx", "src/pages/About.tsx", "src/pages/Menu.tsx"):
        assert a_src[k] == b_src[k], k
    name, z = GS.export_zip(T, aid)
    c = GS.import_zip(T, "Copy from ZIP", z)
    assert not c["refused"] and _src(c["id"])["src/pages/Menu.tsx"] == a_src["src/pages/Menu.tsx"]
    assert GS.status(AE._load(T, b["id"]))["linked"] and not GS.status(AE._load(T, c["id"])).get("linked")
    GS.unlink(T, aid)
    assert GS.status(AE._load(T, aid))["linked"] is False


# ---------------------------------------------------------------- 2. conflicts named, rules enforced, locked files kept apart
def test_conflicts_are_named_and_incoming_files_obey_the_rules(gh):
    from app.appengine import gitsync as GS
    from app.appengine import service as AE
    aid = _app()
    GS.link(T, aid, "mithai-app", True, confirm=True)
    AE._save(aid, version=1)
    GS.push(T, aid, confirm=True)
    remote = gh.files("mithai-app")
    # BOTH sides change Home.tsx
    theirs = PAGE.replace("Sweets", "GitHub sweets").encode()
    gh.commit("mithai-app", {**remote, "src/pages/Home.tsx": theirs})
    _tool(action="write", app=aid, path="src/pages/Home.tsx", code=PAGE.replace("Sweets", "App sweets"))
    cmp_ = GS.compare(T, aid)
    assert [c["say"] for c in cmp_["conflicts"]] == ["src/pages/Home.tsx"]
    with pytest.raises(GS.SyncError) as e:
        GS.pull(T, aid, confirm=True)
    assert e.value.code == 409 and "src/pages/Home.tsx" in str(e.value) and "both the app and GitHub changed" in str(e.value)
    assert "App sweets" in _src(aid)["src/pages/Home.tsx"].decode()                      # nothing applied
    GS.pull(T, aid, {"src/pages/Home.tsx": "site"}, confirm=True)                         # keep the app's: nothing written, GitHub head taken
    assert "App sweets" in _src(aid)["src/pages/Home.tsx"].decode()
    assert GS.status(AE._load(T, aid))["changes"] == [{"path": "src/pages/Home.tsx", "what": "changed"}]   # still to push
    GS.push(T, aid, confirm=True)
    assert b"App sweets" in gh.files("mithai-app")["src/pages/Home.tsx"]
    # an incoming file that breaks the design rules: the pull is refused as a whole and nothing changes
    bad = b'export default function X() { return <div className="bg-blue-500 text-white">x</div>; }\n'
    gh.commit("mithai-app", {**gh.files("mithai-app"), "src/pages/Bad.tsx": bad, "src/pages/Fine.tsx": PAGE.encode()})
    with pytest.raises(GS.SyncError) as e:
        GS.pull(T, aid, confirm=True)
    assert e.value.code == 422 and "src/pages/Bad.tsx" in str(e.value) and "nothing was changed" in str(e.value)
    s = _src(aid)
    assert "src/pages/Bad.tsx" not in s and "src/pages/Fine.tsx" not in s
    # a locked file changed on GitHub is never written, is listed, and the next push keeps GitHub's copy
    gh.commit("mithai-app", {**gh.files("mithai-app"), "src/pages/Bad.tsx": PAGE.encode(), "vite.config.ts": b"// theirs\n"})
    pl = GS.pull(T, aid, confirm=True)
    assert "src/pages/Bad.tsx" in pl["written"] and pl["kept_apart_count"] >= 1 and "locked" in pl["say"]
    assert b"// theirs" not in _src(aid)["vite.config.ts"]
    _tool(action="write", app=aid, path="src/pages/Menu.tsx", code=PAGE.replace("Home", "Menu"))
    GS.push(T, aid, confirm=True)
    assert gh.files("mithai-app")["vite.config.ts"] == b"// theirs\n"                    # her other builder's copy was not overwritten


# ---------------------------------------------------------------- 3. import: foreign files that break the rules are listed, not brought in
def test_import_lists_what_breaks_the_rules_and_zips_are_safe(gh):
    from app.appengine import gitsync as GS
    pkg = json.dumps({"dependencies": {"react": "^18", "left-pad": "1.3.0"}}).encode()
    good = PAGE.encode()
    bad = b'import pad from "left-pad";\nexport default function B() { return <div className="bg-red-500">x</div>; }\n'
    secret = b'export const K = "sk-' + b"a1B2c3D4e5F6g7H8i9J0k1L2" + b'";\n'
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as zf:
        for k, v in {"proj-main/package.json": pkg, "proj-main/src/pages/Home.tsx": good, "proj-main/src/pages/Bad.tsx": bad,
                     "proj-main/src/lib/keys.ts": secret, "proj-main/src/assets/logo.png": b"\x89PNG....", "proj-main/node_modules/x/y.js": b"x",
                     "proj-main/../evil.txt": b"x"}.items():
            zf.writestr(k, v)
    out = GS.import_zip(T, "Foreign app", z.getvalue())
    assert out["imported"] == ["src/pages/Home.tsx"] and {x["file"] for x in out["refused"]} == {"src/pages/Bad.tsx", "src/lib/keys.ts"}
    why = {x["file"]: x["why"] for x in out["refused"]}
    assert "secret" in why["src/lib/keys.ts"] and "palette" in why["src/pages/Bad.tsx"].lower() or "token" in why["src/pages/Bad.tsx"].lower()
    assert "left-pad" in out["packages"] and "package.json" in out["kept_apart"]
    # zip safety
    with pytest.raises(GS.SyncError, match="not a ZIP"):
        GS.read_zip(b"nope")
    with pytest.raises(GS.SyncError, match="does not look like a web app"):
        GS.import_zip(T, "x", _zip({"readme.txt": b"hi"}))
    sym = zipfile.ZipInfo("src/link.ts"); sym.external_attr = (0o120777 << 16)
    z2 = io.BytesIO()
    with zipfile.ZipFile(z2, "w") as zf:
        zf.writestr(sym, "/etc/passwd"); zf.writestr("src/ok.ts", "export const a = 1;\n")
    assert list(GS.read_zip(z2.getvalue())) == ["src/ok.ts"]                              # a link is never followed


def _zip(files):
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as zf:
        for k, v in files.items():
            zf.writestr(k, v)
    return z.getvalue()


# ---------------------------------------------------------------- 4. routes
def test_routes(gh, monkeypatch):
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    aid = _app()
    c = TestClient(main.app)
    h = {"Authorization": f"Bearer {KEY}"}
    assert c.get(f"/api/appengine/{aid}/github", headers={}).status_code == 401
    assert c.get(f"/api/appengine/{aid}/github", headers=h).json()["linked"] is False
    assert c.post(f"/api/appengine/{aid}/github/link", headers=h, json={"repo": "r1"}).status_code == 403
    assert c.post(f"/api/appengine/{aid}/github/link", headers=h, json={"repo": "r1", "confirm": True}).json()["linked"] is True
    from app.appengine import service as AE
    AE._save(aid, version=1)
    assert c.post(f"/api/appengine/{aid}/github/push", headers=h, json={"confirm": True}).json()["pushed"] is True
    assert c.get(f"/api/appengine/{aid}/github/compare", headers=h).json()["conflicts"] == []
    z = c.get(f"/api/appengine/{aid}/export.zip", headers=h)
    assert z.status_code == 200 and "src/pages/Home.tsx" in zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    imp = c.post("/api/appengine-import/zip?name=From+zip", headers=h, content=z.content).json()
    assert imp["imported"] and imp["app"]["name"] == "From zip"
    r = c.post("/api/appengine-import/github", headers=h, json={"repo": "asha/r1"})
    assert r.status_code == 403
    assert c.post("/api/appengine-import/github", headers=h, json={"repo": "asha/r1", "confirm": True}).json()["linked"] == "asha/r1"
    assert c.post("/api/appengine-import/github", headers=h, json={"repo": "asha/none", "confirm": True}).status_code == 404


# ---------------------------------------------------------------- 5. the Studio, in a real browser
def test_github_in_the_studio(arena_server, gh):
    base, browser, key = arena_server
    from app.appengine import service as AE
    aid = AE.create(T, "Mithai orders")["id"]                  # plain calls: Playwright's loop is running here
    AE.write(T, aid, "src/pages/Home.tsx", PAGE)
    AE._save(aid, version=1)
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(f"{base}/console/web#/app/{aid}/publish")
    page.locator("[data-ae-form=git-link] input").wait_for(timeout=20000)
    page.fill("[data-ae-form=git-link] input", "studio-app")
    page.click("[data-ae-form=git-link] button")
    page.locator("#aeGit a", has_text="asha/studio-app").wait_for(timeout=20000)
    page.click("[data-ae-git=push]")
    for _ in range(40):
        if "src/pages/Home.tsx" in gh.files("studio-app"):
            break
        page.wait_for_timeout(250)
    assert gh.files("studio-app")["src/pages/Home.tsx"] == PAGE.encode()
    gh.commit("studio-app", {**gh.files("studio-app"), "src/pages/Menu.tsx": PAGE.encode()})
    page.click("[data-ae-git=compare]")
    page.locator("#aeGitCmp", has_text="GitHub has new commits").wait_for(timeout=20000)
    assert "src/pages/Menu.tsx" in page.inner_text("#aeGitCmp")
    page.click("[data-ae-git=pull]")
    for _ in range(40):
        if "src/pages/Menu.tsx" in _src(aid):
            break
        page.wait_for_timeout(250)
    assert "src/pages/Menu.tsx" in _src(aid)
    # import a ZIP from the Apps home
    page.goto(f"{base}/console/web#/apps")
    page.locator("[data-ae-form=imp-zip]").wait_for(timeout=20000)
    page.set_input_files("[data-ae-form=imp-zip] input[type=file]", files=[{"name": "Brought in.zip", "mimeType": "application/zip",
                                                                         "buffer": _zip({"src/pages/Home.tsx": PAGE.encode(), "package.json": b"{}"})}])
    page.click("[data-ae-form=imp-zip] button")
    page.locator("#aeImpOut", has_text="Imported 1 file").wait_for(timeout=30000)
    assert page.locator("#aeImpOut a", has_text="Open the app").count() == 1
    ctx.close()
    assert not errors, errors
