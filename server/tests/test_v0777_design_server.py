"""v0.777 HOOLA DESIGN, the server half (docs/HOOLA_DESIGN_PLAN.md is the contract): fractional index order, the
document's rules for every op, the REST routes with tenant isolation, images checked by content, the share link,
and the multiplayer room over a real WebSocket - two editors in one file, acks and rejections, presence, join /
leave, the journal and the snapshot a later visit loads from, and a view-only guest whose ops are refused."""
import io
import json
import random
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.design import fracidx
from app.design.doc import APPLIED, DROPPED, REJECTED, ROOT, Doc, new_document

H = {"Authorization": "Bearer kd"}
PAGE = "0:1"
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="12" viewBox="0 0 24 12"><rect width="24" height="12"/></svg>'


@pytest.fixture()
def design_env(env, tmp_path, monkeypatch):
    """Fresh database (env) + the API key for HTTP + images under the test folder + quick idle checkpoints off."""
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    from app.config import get_settings
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def client():
    from app.main import app
    return TestClient(app)


def other_tenant():
    """A second signed-in person: her own tenant, her own token."""
    from app import accounts
    from app.db import User, session
    with session() as s:
        u = User(email="other@example.com", name="Other Person")
        s.add(u)
        s.flush()
        uid = u.id
    return {"Authorization": f"Bearer {accounts.issue_session(uid)}"}


def new_file(c, **body):
    r = c.post("/api/design/files", headers=H, json=body)
    assert r.status_code == 200, r.text
    return r.json()


def ws(c, file_id, **kw):
    return c.websocket_connect(f"/api/design/ws?file={file_id}", headers=H, **kw)


def take(sock, kind):
    """The next frame of one kind (cursor / join frames in between are skipped)."""
    for _ in range(50):
        frame = sock.receive_json()
        if frame["t"] == kind:
            return frame
    raise AssertionError(f"no {kind} frame")


def rect(nid, idx="V", **props):
    return {"id": nid, "p": {"type": "RECT", "parent": PAGE, "idx": idx, "name": "Rect", **props}}


def png(w=4, h=3):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


# ------------------------------------------------------------------------------------- fractional index
def test_fracidx_first_key_and_open_sides():
    first = fracidx.between(None, None)
    assert first and first == fracidx.between(None, "") and not first.endswith("0")
    assert fracidx.between(first, None) > first > fracidx.between(None, first)
    above = fracidx.between(first, None)
    assert first < fracidx.between(first, above) < above
    assert "A" < fracidx.between("A", "B") < "B"                   # keys of another shape: the plain midpoint
    assert "0V" < fracidx.between("0V", "0W") < "0W"
    assert fracidx.between("zz", None) > "zz" and fracidx.between(None, "01") < "01"
    assert fracidx.between("b", "a") == fracidx.between("a", "b")  # a wrong order still gets a usable key ...
    assert fracidx.between(first, first) > first                   # ... and so do two equal keys: never an error


def test_fracidx_random_inserts_stay_sorted():
    rng = random.Random(7)
    for _ in range(40):
        keys = []
        for _ in range(250):
            roll = rng.random()
            at = len(keys) if roll < 0.3 else 0 if roll < 0.5 else rng.randint(0, len(keys))
            key = fracidx.between(keys[at - 1] if at else None, keys[at] if at < len(keys) else None)
            assert key.isascii() and key.isalnum() and not key.endswith("0")
            keys.insert(at, key)
        assert keys == sorted(keys) and len(set(keys)) == len(keys)
    for _ in range(300):                                           # between any two keys a browser might hold
        a, b = sorted("".join(rng.choice(fracidx.DIGITS[1:]) for _ in range(rng.randint(1, 4))) for _ in range(2))
        if a != b:
            assert a < fracidx.between(a, b) < b
        assert fracidx.between(a, None) > a and fracidx.between(None, a) < a


def test_fracidx_appends_stay_short_and_n_between():
    key, keys = None, []
    for _ in range(20000):
        key = fracidx.between(key, None)
        keys.append(key)
    assert keys == sorted(keys) and len(key) <= 4                  # 20,000 layers on top: still a 4-character key
    key = None
    for _ in range(20000):
        key = fracidx.between(None, key)
    assert len(key) <= 4
    lo, hi = keys[0], keys[1]
    many = fracidx.n_between(lo, hi, 60)
    assert many == sorted(many) and len(set(many)) == 60 and all(lo < k < hi for k in many)
    assert fracidx.n_between(None, None, 3) == keys[:3]
    below = fracidx.n_between(None, lo, 9)
    assert below == sorted(below) and len(set(below)) == 9 and all(k < lo for k in below)
    assert fracidx.n_between("A", "B", 0) == []


def test_fracidx_and_the_browser_order_each_others_keys():
    """Only the ORDER is shared between HD.frac (hd-core.js) and this module: each side must be able to put a key
    between any two keys the other side made, and both must sort the result the same way."""
    import shutil
    import subprocess

    from app.main import STATIC
    core = STATIC / "console" / "design" / "hd-core.js"
    node = shutil.which("node")
    if not node or not core.is_file():
        pytest.skip("needs node and the browser half (hd-core.js)")
    rng = random.Random(11)

    def grow(keys, n, make):
        for _ in range(n):
            roll = rng.random()
            at = len(keys) if roll < 0.3 else 0 if roll < 0.5 else rng.randint(0, len(keys))
            keys.insert(at, make(keys[at - 1] if at else None, keys[at] if at < len(keys) else None))
        return keys

    ours = grow([], 400, fracidx.between)
    script = """
        const fs = require('fs'), vm = require('vm');
        const code = fs.readFileSync(process.argv[1], 'utf8');
        const cut = code.indexOf(String.fromCharCode(10), code.indexOf('HD.frac = {'));
        const ctx = {window: {}};
        vm.createContext(ctx);
        vm.runInContext(code.slice(0, cut + 1) + '})();', ctx);
        const F = ctx.window.HD.frac, job = JSON.parse(fs.readFileSync(0, 'utf8')), keys = job.keys;
        for (const at of job.at) keys.splice(at, 0, F.between(at ? keys[at - 1] : null, at < keys.length ? keys[at] : null));
        console.log(JSON.stringify({keys: keys, fresh: [F.between(null, null), F.nBetween(null, null, 3)]}));
    """
    places, size = [], len(ours)
    for _ in range(400):
        roll = rng.random()
        places.append(size if roll < 0.3 else 0 if roll < 0.5 else rng.randint(0, size))
        size += 1
    run = subprocess.run([node, "-e", script, str(core)], input=json.dumps({"keys": ours, "at": places}),
                         capture_output=True, text=True, timeout=60)
    if run.returncode != 0:
        pytest.skip("HD.frac could not be loaded on its own from hd-core.js: " + run.stderr.strip()[-200:])
    out = json.loads(run.stdout)
    mixed = out["keys"]
    assert len(mixed) == 800 and mixed == sorted(mixed) and len(set(mixed)) == 800    # the browser fitted 400 between ours
    grow(mixed, 400, fracidx.between)                                                 # and we fit 400 between theirs
    assert mixed == sorted(mixed) and len(set(mixed)) == 1200 and max(map(len, mixed)) < 40
    first, three = out["fresh"]
    assert fracidx.between(first, None) > first and three == sorted(three)


# ---------------------------------------------------------------------------------------- document rules
def doc():
    return Doc(new_document())


def test_new_document_and_templates():
    nodes = new_document()
    assert set(nodes) == {ROOT, PAGE} and nodes[ROOT]["type"] == "DOCUMENT" and "parent" not in nodes[ROOT]
    assert nodes[PAGE] == {"type": "PAGE", "parent": ROOT, "idx": fracidx.between(None, None), "name": "Page 1"}
    phone = new_document("phone")
    assert phone["0:2"]["type"] == "FRAME" and (phone["0:2"]["w"], phone["0:2"]["h"]) == (390, 844)
    assert set(new_document("no-such-template")) == {ROOT, PAGE}   # an unknown template is a blank file


def test_last_writer_wins_per_property_and_null_removes():
    d = doc()
    assert d.apply(rect("1:1", x=10, y=20, fills=[{"type": "solid", "color": "#FF0000"}])) == APPLIED
    assert d.apply({"id": "1:1", "p": {"x": 50}}) == APPLIED                       # one person moves it ...
    assert d.apply({"id": "1:1", "p": {"name": "Card"}}) == APPLIED                # ... another renames it: both win
    assert d.apply({"id": "1:1", "p": {"x": 70}}) == APPLIED                       # the same property: the last one wins
    n = d.nodes["1:1"]
    assert (n["x"], n["y"], n["name"]) == (70, 20, "Card")
    assert d.apply({"id": "1:1", "p": {"fills": None, "future": {"kept": True}}}) == APPLIED
    assert "fills" not in n and n["future"] == {"kept": True}                      # null removes; unknown props are kept
    assert d.apply({"id": "1:1", "p": {"never": None}}) == APPLIED                 # removing what is not there is fine


def test_create_needs_a_known_type_a_real_parent_and_an_index():
    d = doc()
    assert d.apply({"id": "1:1", "p": {"type": "BLOB", "parent": PAGE, "idx": "V"}}) == REJECTED
    assert d.apply({"id": "1:1", "p": {"type": "DOCUMENT", "parent": PAGE, "idx": "V"}}) == REJECTED
    assert d.apply({"id": "1:1", "p": {"type": ["RECT"], "parent": PAGE, "idx": "V"}}) == REJECTED
    assert d.apply({"id": "1:1", "p": {"type": "RECT", "idx": "V"}}) == REJECTED
    assert d.apply({"id": "1:1", "p": {"type": "RECT", "parent": "9:9", "idx": "V"}}) == REJECTED
    assert d.apply({"id": "1:1", "p": {"type": "RECT", "parent": PAGE}}) == REJECTED
    assert d.apply({"id": "1:1", "p": {"type": "RECT", "parent": PAGE, "idx": 3}}) == REJECTED
    assert "1:1" not in d.nodes
    assert d.apply({"id": "1:1", "p": {"x": 5}}) == DROPPED and "1:1" not in d.nodes   # deleted by someone else
    assert d.apply({"id": "", "p": {}}) == REJECTED and d.apply("junk") == REJECTED and d.apply({"id": "1:1"}) == REJECTED
    assert d.apply(rect("1:1", x=None)) == APPLIED and "x" not in d.nodes["1:1"]
    assert d.apply({"id": "1:1", "p": {"type": "ELLIPSE"}}) == APPLIED             # a shape may become another shape
    assert d.apply({"id": "1:1", "p": {"type": "NOPE"}}) == REJECTED
    assert d.apply({"id": "1:1", "p": {"type": None}}) == REJECTED
    assert d.apply({"id": "1:1", "p": {"idx": None}}) == REJECTED
    assert d.nodes["1:1"]["type"] == "ELLIPSE"


def test_a_refused_op_changes_nothing():
    d = doc()
    d.apply(rect("1:1", x=1))
    before = json.dumps(d.nodes, sort_keys=True)
    assert d.apply({"id": "1:1", "p": {"x": 99, "name": "New", "parent": "9:9"}}) == REJECTED
    assert json.dumps(d.nodes, sort_keys=True) == before


def test_delete_takes_the_whole_subtree():
    d = doc()
    d.apply({"id": "1:1", "p": {"type": "FRAME", "parent": PAGE, "idx": "V"}})
    d.apply({"id": "1:2", "p": {"type": "GROUP", "parent": "1:1", "idx": "V"}})
    d.apply(rect("1:3") | {"p": {"type": "RECT", "parent": "1:2", "idx": "V"}})
    d.apply(rect("1:4", idx="W"))
    assert d.apply({"id": "1:1", "del": 1}) == APPLIED
    assert set(d.nodes) == {ROOT, PAGE, "1:4"} and d.children(PAGE) == ["1:4"]
    assert d.apply({"id": "1:1", "del": 1}) == DROPPED                             # already gone: not an error
    assert d.apply({"id": "1:3", "p": {"x": 1}}) == DROPPED
    assert d.apply({"id": "1:5", "p": {"type": "RECT", "parent": "1:2", "idx": "V"}}) == REJECTED   # its parent is gone


def test_cycles_are_refused_and_the_root_is_protected():
    d = doc()
    for nid, parent in (("1:1", PAGE), ("1:2", "1:1"), ("1:3", "1:2")):
        assert d.apply({"id": nid, "p": {"type": "FRAME", "parent": parent, "idx": "V"}}) == APPLIED
    assert d.apply({"id": "1:1", "p": {"parent": "1:3", "idx": "V"}}) == REJECTED  # under its own grandchild
    assert d.apply({"id": "1:1", "p": {"parent": "1:1"}}) == REJECTED              # under itself
    assert d.nodes["1:1"]["parent"] == PAGE
    assert d.apply({"id": "1:3", "p": {"parent": PAGE, "idx": "W"}}) == APPLIED    # a real move is fine
    assert d.children(PAGE) == ["1:1", "1:3"] and d.children("1:2") == []
    assert d.apply({"id": "1:1", "p": {"parent": "1:3", "idx": "V"}}) == APPLIED   # ... and now this is no cycle
    assert d.apply({"id": "1:3", "p": {"parent": "1:2"}}) == REJECTED
    assert d.apply({"id": ROOT, "del": 1}) == REJECTED
    assert d.apply({"id": ROOT, "p": {"parent": PAGE}}) == REJECTED
    assert d.apply({"id": ROOT, "p": {"type": "PAGE"}}) == REJECTED
    assert d.apply({"id": PAGE, "p": {"parent": None}}) == REJECTED
    assert d.apply({"id": ROOT, "p": {"styles": {"s1": {"kind": "fill", "name": "Brand"}}}}) == APPLIED
    assert ROOT in d.nodes and "parent" not in d.nodes[ROOT]


def test_sibling_order_and_the_node_limit():
    d = Doc(new_document(), max_nodes=5)
    for nid, idx in (("2:1", "k"), ("1:1", "V"), ("1:2", "A"), ):
        assert d.apply(rect(nid, idx=idx)) == APPLIED
    assert d.children(PAGE) == ["1:2", "1:1", "2:1"]
    assert d.apply(rect("3:1")) == REJECTED                                        # the file is full: creates refused
    assert d.apply({"id": "1:1", "p": {"x": 4}}) == APPLIED                        # edits still land
    d.apply({"id": "2:1", "p": {"idx": "V"}})
    assert d.children(PAGE) == ["1:2", "1:1", "2:1"]                               # equal keys: by id, the same everywhere
    d.apply({"id": "2:1", "p": {"idx": "5"}})
    assert d.children(PAGE) == ["2:1", "1:2", "1:1"]


# ------------------------------------------------------------------------------------------------- REST
def test_switch_off_hides_the_page_and_every_route(design_env):
    with client() as c:
        assert c.get("/api/console/config").json()["design"] is True
        assert c.get("/api/design/files").status_code == 401                       # the key is needed
    design_env.setenv("DESIGN_PAGE", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    with client() as c:
        assert c.get("/api/console/config").json()["design"] is False
        assert c.get("/api/design/files", headers=H).status_code == 404
        for path in ("/console/design", "/console/design/"):
            r = c.get(path, follow_redirects=False)
            assert r.status_code == 307 and r.headers["location"] == "/console/"
        with ws(c, "df_x") as sock, pytest.raises(WebSocketDisconnect) as e:
            sock.receive_json()
        assert e.value.code == 4404


def test_the_page_is_served_with_the_console_csp(design_env):
    from app.main import STATIC
    if not (STATIC / "console" / "design" / "design.html").is_file():
        pytest.skip("the browser half (static/console/design/design.html) is not in this checkout")
    with client() as c:
        for path in ("/console/design", "/console/design/"):
            r = c.get(path)
            assert r.status_code == 200 and "text/html" in r.headers["content-type"]
            assert "script-src 'self'" in r.headers["content-security-policy"] and r.headers["x-frame-options"] == "DENY"


def test_files_crud_trash_restore_duplicate(design_env):
    with client() as c:
        f = new_file(c, name="  Landing   page ")
        fid = f["id"]
        assert f["name"] == "Landing page" and f["nodes"] == 2 and f["trashed"] is False and f["star"] is False
        assert new_file(c)["name"] == "Untitled"
        assert c.post("/api/design/files", headers=H).json()["name"] == "Untitled"          # no body at all
        phone = new_file(c, name="App", template="phone")
        assert phone["nodes"] == 3
        got = c.get(f"/api/design/files/{fid}", headers=H).json()
        assert got["id"] == fid and got["role"] == "edit" and got["share"] is None
        body = c.get(f"/api/design/files/{fid}/doc", headers=H).json()
        assert body["seq"] == 0 and set(body["doc"]["nodes"]) == {ROOT, PAGE}
        assert c.get(f"/api/design/files/{phone['id']}/doc", headers=H).json()["doc"]["nodes"]["0:2"]["w"] == 390

        p = c.patch(f"/api/design/files/{fid}", headers=H, json={"name": "Home", "star": True}).json()
        assert p["name"] == "Home" and p["star"] is True
        assert c.patch(f"/api/design/files/{fid}", headers=H, json={"name": "   "}).json()["name"] == "Home"
        names = [x["name"] for x in c.get("/api/design/files", headers=H).json()["files"]]
        assert names[0] == "Home" and len(names) == 4                                       # newest change first
        assert [x["name"] for x in c.get("/api/design/files?q=hom", headers=H).json()["files"]] == ["Home"]
        assert c.get("/api/design/files?q=100%25", headers=H).json()["files"] == []         # % is a letter, not a wildcard

        dup = c.post(f"/api/design/files/{phone['id']}/duplicate", headers=H).json()
        assert dup["name"] == "App copy" and dup["id"] != phone["id"] and dup["nodes"] == 3
        assert "0:2" in c.get(f"/api/design/files/{dup['id']}/doc", headers=H).json()["doc"]["nodes"]

        assert c.delete(f"/api/design/files/{fid}?forever=1", headers=H).status_code == 409  # only out of the trash
        assert c.delete(f"/api/design/files/{fid}", headers=H).json()["trashed"] is True
        assert fid not in [x["id"] for x in c.get("/api/design/files", headers=H).json()["files"]]
        assert [x["id"] for x in c.get("/api/design/files?trash=1", headers=H).json()["files"]] == [fid]
        assert c.post(f"/api/design/files/{fid}/restore", headers=H).json()["trashed"] is False
        assert fid in [x["id"] for x in c.get("/api/design/files", headers=H).json()["files"]]
        c.delete(f"/api/design/files/{fid}", headers=H)
        assert c.delete(f"/api/design/files/{fid}?forever=1", headers=H).json()["deleted"] is True
        assert c.get(f"/api/design/files/{fid}", headers=H).status_code == 404
        assert c.get(f"/api/design/files/{fid}/doc", headers=H).status_code == 404
        assert c.post("/api/design/files/df_nope/restore", headers=H).status_code == 404


def test_another_tenant_gets_404_everywhere(design_env):
    with client() as c:
        fid = new_file(c, name="Mine")["id"]
        ver = c.post(f"/api/design/files/{fid}/versions", headers=H, json={"label": "v1"}).json()
        com = c.post(f"/api/design/files/{fid}/comments", headers=H, json={"text": "Hi", "x": 1, "y": 2, "page": PAGE}).json()
        sha = c.post(f"/api/design/files/{fid}/assets", headers=H, content=png()).json()["hash"]
        other = other_tenant()
        assert c.get("/api/design/files", headers=other).json()["files"] == []
        for method, path, kw in (
                ("get", f"/api/design/files/{fid}", {}), ("patch", f"/api/design/files/{fid}", {"json": {"name": "x"}}),
                ("delete", f"/api/design/files/{fid}", {}), ("post", f"/api/design/files/{fid}/restore", {}),
                ("post", f"/api/design/files/{fid}/duplicate", {}), ("get", f"/api/design/files/{fid}/doc", {}),
                ("get", f"/api/design/files/{fid}/thumb", {}), ("put", f"/api/design/files/{fid}/thumb", {"content": png()}),
                ("get", f"/api/design/files/{fid}/versions", {}), ("post", f"/api/design/files/{fid}/versions", {"json": {}}),
                ("get", f"/api/design/versions/{ver['id']}/doc", {}), ("post", f"/api/design/versions/{ver['id']}/restore", {}),
                ("get", f"/api/design/files/{fid}/comments", {}),
                ("post", f"/api/design/files/{fid}/comments", {"json": {"text": "x"}}),
                ("patch", f"/api/design/comments/{com['id']}", {"json": {"resolved": True}}),
                ("delete", f"/api/design/comments/{com['id']}", {}),
                ("post", f"/api/design/files/{fid}/assets", {"content": png()}), ("get", f"/api/design/assets/{sha}", {}),
                ("post", f"/api/design/files/{fid}/share", {"json": {"role": "view"}})):
            r = getattr(c, method)(path, headers=other, **kw)
            assert r.status_code == 404, (method, path, r.status_code)
        assert c.get(f"/api/design/files/{fid}", headers=H).json()["name"] == "Mine"       # and nothing of hers changed
        assert c.get(f"/api/design/files/{fid}/comments", headers=H).json()["comments"][0]["resolved"] is False
        with c.websocket_connect(f"/api/design/ws?file={fid}", headers=other) as sock, pytest.raises(WebSocketDisconnect) as e:
            sock.receive_json()
        assert e.value.code == 4404
        mine = new_file(c, name="Other's own")                                              # the other person's files are hers
        theirs = c.post("/api/design/files", headers=other, json={"name": "Theirs"}).json()
        assert c.get(f"/api/design/files/{theirs['id']}", headers=H).status_code == 404
        assert [x["id"] for x in c.get("/api/design/files", headers=other).json()["files"]] == [theirs["id"]]
        assert mine["id"] in [x["id"] for x in c.get("/api/design/files", headers=H).json()["files"]]


def test_versions_create_list_read_restore(design_env):
    with client() as c:
        fid = new_file(c, name="Versions")["id"]
        with ws(c, fid) as a:
            take(a, "init")
            a.send_json({"t": "ops", "n": 1, "ops": [rect("1:1", name="First")]})
            take(a, "ack")
            v1 = c.post(f"/api/design/files/{fid}/versions", headers=H, json={"label": "With one rect"}).json()
            assert v1["label"] == "With one rect" and v1["auto"] is False and v1["nodes"] == 3 and v1["seq"] == 1
            a.send_json({"t": "ops", "n": 2, "ops": [rect("1:2", idx="W", name="Second"), {"id": "1:1", "del": 1}]})
            assert take(a, "ack")["seq"] == 2
            old = c.get(f"/api/design/versions/{v1['id']}/doc", headers=H).json()
            assert old["seq"] == 1 and "1:1" in old["doc"]["nodes"] and "1:2" not in old["doc"]["nodes"]

            r = c.post(f"/api/design/versions/{v1['id']}/restore", headers=H).json()
            assert r["ok"] is True and r["seq"] == 3 and r["saved"]["label"] == "Before restore"
            assert take(a, "reload") == {"t": "reload"}                                    # the open editor is told
            now_doc = c.get(f"/api/design/files/{fid}/doc", headers=H).json()
            assert now_doc["seq"] == 3 and "1:1" in now_doc["doc"]["nodes"] and "1:2" not in now_doc["doc"]["nodes"]
            a.send_json({"t": "ops", "n": 3, "ops": [{"id": "1:1", "p": {"x": 44}}, {"id": "1:2", "p": {"x": 1}}]})
            assert take(a, "ack") == {"t": "ack", "n": 3, "seq": 4, "rejected": []}        # edits land on the restored document
        labels = [v["label"] for v in c.get(f"/api/design/files/{fid}/versions", headers=H).json()["versions"]]
        assert labels == ["Before restore", "With one rect"]
        kept = c.get(f"/api/design/files/{fid}/versions", headers=H).json()["versions"][0]
        undo = c.get(f"/api/design/versions/{kept['id']}/doc", headers=H).json()["doc"]["nodes"]
        assert "1:2" in undo and "1:1" not in undo                                          # the restore itself can be undone
        final = c.get(f"/api/design/files/{fid}/doc", headers=H).json()
        assert final["doc"]["nodes"]["1:1"]["x"] == 44 and final["seq"] == 4
        c.post(f"/api/design/versions/{kept['id']}/restore", headers=H)                     # with nobody in the file
        assert "1:2" in c.get(f"/api/design/files/{fid}/doc", headers=H).json()["doc"]["nodes"]
        assert c.get("/api/design/versions/dv_nope/doc", headers=H).status_code == 404


def test_automatic_versions_are_cut_and_pruned(design_env):
    from app.design import store
    from app.design.doc import dumps_nodes
    with client() as c:
        fid = new_file(c)["id"]
    blob = store.pack(dumps_nodes(new_document()))
    for seq in range(1, 6):
        store.save_snapshot(fid, blob, seq, 2, 0.0001, 3)                                   # "30 minutes" have always passed
        time.sleep(0.002)
    with client() as c:
        vs = c.get(f"/api/design/files/{fid}/versions", headers=H).json()["versions"]
        assert [v["seq"] for v in vs] == [5, 4, 3] and all(v["auto"] for v in vs)           # the newest three are kept
        named = c.post(f"/api/design/files/{fid}/versions", headers=H, json={"label": "Keep me"}).json()
    for seq in range(6, 12):
        store.save_snapshot(fid, blob, seq, 2, 0.0001, 3)
        time.sleep(0.002)
    kept = store.list_versions("default", fid)
    assert named["id"] in [v["id"] for v in kept] and sum(v["auto"] for v in kept) == 3     # a named one is never pruned
    store.save_snapshot(fid, blob, 12, 2, 0, 3)                                             # 0 = no automatic versions
    assert len(store.list_versions("default", fid)) == 4


def test_comments_threads_resolve_delete(design_env):
    with client() as c:
        fid = new_file(c)["id"]
        base = f"/api/design/files/{fid}/comments"
        a = c.post(base, headers=H, json={"text": "  Make this bigger ", "x": 120.5, "y": 40, "page": PAGE, "node": "1:1"}).json()
        assert a["text"] == "Make this bigger" and (a["x"], a["y"], a["page"], a["node"]) == (120.5, 40, PAGE, "1:1")
        assert a["resolved"] is False and a["parent"] is None and a["author"]
        b = c.post(base, headers=H, json={"text": "Done", "parent": a["id"]}).json()
        d = c.post(base, headers=H, json={"text": "Thanks", "parent": b["id"]}).json()
        assert b["parent"] == a["id"] and d["parent"] == a["id"]                            # threads are one level deep
        assert c.post(base, headers=H, json={"text": "   "}).status_code == 400
        assert c.post(base, headers=H, json={"text": "x", "parent": "dc_nope"}).status_code == 400
        assert [x["id"] for x in c.get(base, headers=H).json()["comments"]] == [a["id"], b["id"], d["id"]]
        up = c.patch(f"/api/design/comments/{a['id']}", headers=H, json={"resolved": True, "text": "Bigger"}).json()
        assert up["resolved"] is True and up["text"] == "Bigger"
        assert c.patch(f"/api/design/comments/{a['id']}", headers=H, json={"text": " "}).status_code == 400
        assert c.delete(f"/api/design/comments/{a['id']}", headers=H).json() == {"ok": True}
        assert c.get(base, headers=H).json()["comments"] == []                              # the replies went with it
        assert c.delete(f"/api/design/comments/{a['id']}", headers=H).status_code == 404


def test_images_are_checked_by_content(design_env, tmp_path):
    with client() as c:
        fid = new_file(c)["id"]
        url = f"/api/design/files/{fid}/assets"
        good = png(40, 20)
        up = c.post(url, headers=H, content=good)
        assert up.status_code == 200, up.text
        meta = up.json()
        assert meta["mime"] == "image/png" and (meta["w"], meta["h"], meta["size"]) == (40, 20, len(good)) and len(meta["hash"]) == 64
        assert c.post(url, headers=H, content=good).json()["hash"] == meta["hash"]          # the same bytes are one file
        assert (tmp_path / "design" / "default" / "assets" / meta["hash"]).read_bytes() == good
        got = c.get(f"/api/design/assets/{meta['hash']}", headers=H)
        assert got.content == good and got.headers["content-type"] == "image/png"
        assert got.headers["x-content-type-options"] == "nosniff" and "sandbox" in got.headers["content-security-policy"]
        form = c.post(url, headers=H, files={"file": ("pic.png", good, "image/png")})       # a form upload works too
        assert form.json()["hash"] == meta["hash"]

        fake = c.post(url, headers={**H, "Content-Type": "image/png"}, content=b"this is not a png at all")
        assert fake.status_code == 415                                                      # the claimed type is not believed
        broken = c.post(url, headers=H, content=good[:8] + b"\x00" * 60)
        assert broken.status_code == 415                                                    # right first bytes, no picture
        assert c.post(url, headers=H, content=b"").status_code == 415
        assert c.post(url, headers=H, content=b"%PDF-1.7 not an image").status_code == 415
        assert c.post(url, headers=H, content=b"x" * (10 * 1024 * 1024 + 70 * 1024)).status_code == 413

        ok_svg = c.post(url, headers=H, content=SVG.encode())
        assert ok_svg.status_code == 200 and ok_svg.json()["mime"] == "image/svg+xml" and ok_svg.json()["w"] == 24
        assert c.get(f"/api/design/assets/{ok_svg.json()['hash']}", headers=H).headers["content-type"].startswith("image/svg+xml")
        for bad in (SVG.replace("<rect", "<script>alert(1)</script><rect"),
                    SVG.replace("<rect", '<rect onclick="steal()"'),
                    SVG.replace("<svg ", '<svg onload="x()" '),
                    SVG.replace("<rect", '<a href="java\nscript:alert(1)"><rect').replace("/></svg>", "/></a></svg>"),
                    SVG.replace("<rect", '<foreignObject><iframe xmlns="http://www.w3.org/1999/xhtml"/></foreignObject><rect'),
                    SVG.replace("<rect", '<set attributeName="onmouseover" to="x()"/><rect'),
                    '<!DOCTYPE svg [<!ENTITY a "aaaa">]>' + SVG, SVG[:-6]):
            r = c.post(url, headers=H, content=bad.encode())
            assert r.status_code == 415, bad
        assert c.get("/api/design/assets/" + "0" * 64, headers=H).status_code == 404
        assert c.get("/api/design/assets/..%2F..%2Fetc", headers=H).status_code == 404

        thumb = f"/api/design/files/{fid}/thumb"
        assert c.get(thumb, headers=H).status_code == 404
        assert c.put(thumb, headers=H, content=SVG.encode()).status_code == 415             # a thumbnail is a PNG
        assert c.put(thumb, headers=H, content=b"\x89PNG\r\n\x1a\n" + b"0" * (301 * 1024)).status_code == 413
        put = c.put(thumb, headers=H, content=good).json()
        assert put["ok"] is True and put["thumb_at"]
        assert c.get(thumb, headers=H).content == good
        assert c.get(f"/api/design/files/{fid}", headers=H).json()["thumb_at"] == put["thumb_at"]


def test_share_link_is_read_only_and_can_be_switched_off(design_env):
    with client() as c:
        fid = new_file(c, name="Shared deck")["id"]
        sha = c.post(f"/api/design/files/{fid}/assets", headers=H, content=png()).json()["hash"]
        assert c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "edit"}).status_code == 400
        token = c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "view"}).json()["token"]
        assert len(token) >= 24
        assert c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "view"}).json()["token"] == token
        assert c.get(f"/api/design/files/{fid}", headers=H).json()["share"] == {"role": "view", "token": token}
        pub = c.get(f"/api/design/shared/{token}/doc")                                      # no key at all
        assert pub.status_code == 200
        body = pub.json()
        assert body["file"] == {"id": fid, "name": "Shared deck", "role": "view"} and ROOT in body["doc"]["nodes"]
        assert c.get(f"/api/design/shared/{token}/assets/{sha}").content == png()
        assert c.get("/api/design/shared/nope/doc").status_code == 404
        for method in ("post", "put", "patch", "delete"):                                   # the link reads; it changes nothing
            assert getattr(c, method)(f"/api/design/shared/{token}/doc").status_code == 405
        assert c.get(f"/api/design/files/{fid}/doc").status_code == 401                     # and it opens nothing else

        c.delete(f"/api/design/files/{fid}", headers=H)                                     # in the trash: the link is dead
        assert c.get(f"/api/design/shared/{token}/doc").status_code == 404
        c.post(f"/api/design/files/{fid}/restore", headers=H)
        assert c.get(f"/api/design/shared/{token}/doc").status_code == 200
        assert c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "none"}).json() == {"token": None, "role": "none"}
        assert c.get(f"/api/design/shared/{token}/doc").status_code == 404
        assert c.get(f"/api/design/shared/{token}/assets/{sha}").status_code == 404


# -------------------------------------------------------------------------------------------- WebSocket
def test_socket_needs_a_sign_in_and_a_real_file(design_env):
    with client() as c:
        fid = new_file(c)["id"]
        for url, kw, code in ((f"/api/design/ws?file={fid}", {}, 4401),
                              (f"/api/design/ws?file={fid}&key=kd", {}, 4401),              # never from the address
                              (f"/api/design/ws?file={fid}", {"headers": {"Authorization": "Bearer wrong"}}, 4401),
                              ("/api/design/ws?file=df_nope", {"headers": H}, 4404),
                              ("/api/design/ws", {"headers": H}, 4404)):
            with c.websocket_connect(url, **kw) as sock, pytest.raises(WebSocketDisconnect) as e:
                sock.receive_json()
            assert e.value.code == code, url
        with c.websocket_connect(f"/api/design/ws?file={fid}", subprotocols=["hoola", "hoola-key.kd"]) as sock:
            init = sock.receive_json()                                                      # the browser's way in
            assert sock.accepted_subprotocol == "hoola"
            assert init["t"] == "init" and init["file"] == {"id": fid, "name": "Untitled", "role": "edit"}
            assert init["seq"] == 0 and set(init["doc"]["nodes"]) == {ROOT, PAGE} and init["users"] == []
            assert init["you"]["cid"] == init["cid"] and init["you"]["color"].startswith("#")
            sock.send_json({"t": "ping"})
            assert sock.receive_json() == {"t": "pong"}
        c.delete(f"/api/design/files/{fid}", headers=H)
        with ws(c, fid) as sock, pytest.raises(WebSocketDisconnect) as e:                   # a file in the trash
            sock.receive_json()
        assert e.value.code == 4404


def test_two_editors_ops_acks_rejections_presence_join_leave(design_env):
    with client() as c:
        fid = new_file(c, name="Together")["id"]
        with ws(c, fid) as a:
            ia = take(a, "init")
            with ws(c, fid) as b:
                ib = take(b, "init")
                assert ia["cid"] != ib["cid"] and ia["cid"] > 0 and ib["cid"] > 0           # never the server's 0
                assert ib["users"] == [ia["you"]] and ia["you"]["color"] != ib["you"]["color"]
                assert take(a, "join") == {"t": "join", "user": ib["you"]}

                a.send_json({"t": "ops", "n": 1, "ops": [rect(f"{ia['cid']}:1", x=10, y=10)]})
                assert take(a, "ack") == {"t": "ack", "n": 1, "seq": 1, "rejected": []}
                got = take(b, "ops")
                assert got == {"t": "ops", "seq": 1, "by": ia["cid"], "ops": [rect(f"{ia['cid']}:1", x=10, y=10)]}

                batch = [{"id": f"{ia['cid']}:1", "p": {"x": 99}},                           # fine
                         {"id": f"{ib['cid']}:1", "p": {"type": "RECT", "parent": "7:7", "idx": "V"}},   # no such parent
                         {"id": "gone:1", "p": {"x": 1}},                                    # deleted by someone: dropped
                         {"id": ROOT, "del": 1},                                             # never
                         {"id": f"{ib['cid']}:2", "p": {"type": "TEXT", "parent": PAGE, "idx": "W", "chars": "नमस्ते 🎨"}}]
                b.send_json({"t": "ops", "n": 7, "ops": batch})
                assert take(b, "ack") == {"t": "ack", "n": 7, "seq": 2, "rejected": [1, 3]}  # the indexes she rolls back
                seen = take(a, "ops")
                assert seen["seq"] == 2 and seen["by"] == ib["cid"] and seen["ops"] == [batch[0], batch[4]]   # only the accepted

                b.send_json({"t": "ops", "n": 8, "ops": [{"id": ROOT, "del": 1}]})           # nothing accepted: no new seq
                assert take(b, "ack") == {"t": "ack", "n": 8, "seq": 2, "rejected": [0]}

                a.send_json({"t": "pres", "x": 12.5, "y": -3, "page": PAGE, "sel": [f"{ia['cid']}:1"], "vp": [0, 0, 1], "cid": 999})
                pres = take(b, "pres")
                assert pres == {"t": "pres", "x": 12.5, "y": -3, "page": PAGE, "sel": [f"{ia['cid']}:1"], "vp": [0, 0, 1],
                                "cid": ia["cid"]}                                            # the server says who it is from
                with ws(c, fid) as late:                                                     # a third person sees where A is
                    il = take(late, "init")
                    assert {u["cid"] for u in il["users"]} == {ia["cid"], ib["cid"]}
                    assert il["doc"]["nodes"][PAGE]["name"] == "Page 1"
                    assert take(late, "pres")["cid"] == ia["cid"]
                assert take(a, "leave")["cid"] == il["cid"] and take(b, "leave")["cid"] == il["cid"]

                c.patch(f"/api/design/files/{fid}", headers=H, json={"name": "Renamed"})
                assert take(a, "file") == {"t": "file", "name": "Renamed"} and take(b, "file")["name"] == "Renamed"
                made = c.post(f"/api/design/files/{fid}/comments", headers=H, json={"text": "Look", "x": 1, "y": 1, "page": PAGE}).json()
                note = take(b, "comment")
                assert note["action"] == "add" and note["comment"] == made
                c.delete(f"/api/design/comments/{made['id']}", headers=H)
                assert take(a, "comment")["action"] == "add" and take(a, "comment") == {
                    "t": "comment", "action": "delete", "comment": {"id": made["id"], "file": fid}}
            assert take(a, "leave") == {"t": "leave", "cid": ib["cid"]}
            live = c.get(f"/api/design/files/{fid}/doc", headers=H).json()                   # the open room answers
            assert live["seq"] == 2 and live["doc"]["nodes"][f"{ia['cid']}:1"]["x"] == 99
            assert live["doc"]["nodes"][f"{ib['cid']}:2"]["chars"] == "नमस्ते 🎨"


def test_a_late_joiner_gets_the_snapshot_and_the_ops_after_it(design_env):
    with client() as c:
        fid = new_file(c)["id"]
        with ws(c, fid) as a:
            ia = take(a, "init")
            for n in range(1, 4):
                a.send_json({"t": "ops", "n": n, "ops": [rect(f"{ia['cid']}:{n}", idx=fracidx.DIGITS[20 + n])]})
                take(a, "ack")
            with ws(c, fid) as b:
                ib = take(b, "init")
                nodes, seq = dict(ib["doc"]["nodes"]), ib["seq"]
                while seq < 3:                                                              # init + the frames after it
                    f = take(b, "ops")
                    assert f["seq"] == seq + 1
                    for op in f["ops"]:
                        nodes[op["id"]] = op["p"]
                    seq = f["seq"]
                assert {f"{ia['cid']}:{n}" for n in (1, 2, 3)} <= set(nodes)
                a.send_json({"t": "ops", "n": 9, "ops": [{"id": f"{ia['cid']}:1", "p": {"x": 5}}]})
                assert take(b, "ops")["seq"] == 4                                           # nothing missed, nothing twice


def test_everyone_leaves_and_a_later_visit_loads_the_same_document(design_env):
    from app.design import store
    from app.design.room import HUB, _read
    with client() as c:
        fid = new_file(c)["id"]
        with ws(c, fid) as a:
            ia = take(a, "init")
            mine = f"{ia['cid']}:1"
            a.send_json({"t": "ops", "n": 1, "ops": [rect(mine, x=1, name="Kept")]})
            take(a, "ack")
            a.send_json({"t": "ops", "n": 2, "ops": [{"id": mine, "p": {"x": 222, "fills": [{"type": "solid", "color": "#00FF00"}]}}]})
            assert take(a, "ack")["seq"] == 2
            # While she is still in the file nothing is checkpointed yet: the JOURNAL holds her work. A crash now
            # must lose nothing - the database alone (snapshot + journal) already gives the same document.
            for _ in range(200):
                raw = store.load_raw(fid, "default")
                if len(raw["journal"]) == 2:
                    break
                time.sleep(0.01)
            assert raw["seq"] == 0 and [row[:2] for row in raw["journal"]] == [(1, ia["cid"]), (2, ia["cid"])]
            assert mine not in raw["doc"]
            seq, doc_json = _read(fid, "default", False)
            assert seq == 2 and json.loads(doc_json)["nodes"][mine]["x"] == 222
        for _ in range(200):                                                                # the last person left
            if fid not in HUB.rooms:
                break
            time.sleep(0.01)
        assert fid not in HUB.rooms                                                         # the room is unloaded ...
        raw = store.load_raw(fid, "default")
        assert raw["seq"] == 2 and raw["journal"] == [] and mine in raw["doc"]              # ... snapshot written, journal trimmed
        assert c.get(f"/api/design/files/{fid}", headers=H).json()["nodes"] == 3
        with ws(c, fid) as again:
            ig = take(again, "init")
            assert ig["seq"] == 2 and ig["cid"] > ia["cid"]                                 # a client number is never reused
            node = ig["doc"]["nodes"][mine]
            assert node["x"] == 222 and node["name"] == "Kept" and node["fills"][0]["color"] == "#00FF00"
            again.send_json({"t": "ops", "n": 1, "ops": [{"id": mine, "del": 1}]})
            assert take(again, "ack")["seq"] == 3                                           # seq carries on
    with client() as c:                                                                     # a server restart
        after = c.get(f"/api/design/files/{fid}/doc", headers=H).json()
        assert after["seq"] == 3 and set(after["doc"]["nodes"]) == {ROOT, PAGE}
        copy = c.post(f"/api/design/files/{fid}/duplicate", headers=H).json()
        with ws(c, copy["id"]) as sock:                                                     # a copy keeps its nodes' ids,
            assert take(sock, "init")["cid"] > ig["cid"]                                    # so it keeps the counter too


def test_a_crash_before_the_checkpoint_loses_nothing(design_env):
    """The process died with ops only in the journal: the next visit replays them on the old snapshot."""
    from app.db import now
    from app.design import store
    from app.design.doc import dumps
    with client() as c:
        fid = new_file(c)["id"]
        store.append_ops(fid, [(1, 4, dumps([rect("4:1", name="Before the crash")]), now()),
                               (2, 4, dumps([{"id": "4:1", "p": {"x": 77}}, rect("4:2", idx="W")]), now()),
                               (3, 5, dumps([{"id": "4:2", "del": 1}]), now())])
        assert c.get(f"/api/design/files/{fid}/doc", headers=H).json()["seq"] == 3         # read without opening a room
        with ws(c, fid) as a:
            ia = take(a, "init")
            nodes = dict(ia["doc"]["nodes"])
            assert ia["seq"] == 0 and "4:1" not in nodes                                    # the stored snapshot ...
            frames = [take(a, "ops") for _ in range(3)]                                     # ... and the journal after it
            assert [(f["seq"], f["by"]) for f in frames] == [(1, 4), (2, 4), (3, 5)]
            a.send_json({"t": "ops", "n": 1, "ops": [{"id": "4:1", "p": {"y": 5}}]})
            assert take(a, "ack")["seq"] == 4                                               # seq carries on after the journal
        after = c.get(f"/api/design/files/{fid}/doc", headers=H).json()
        assert after["seq"] == 4 and after["doc"]["nodes"]["4:1"] == {
            "type": "RECT", "parent": PAGE, "idx": "V", "name": "Before the crash", "x": 77, "y": 5}
        assert "4:2" not in after["doc"]["nodes"] and store.load_raw(fid, "default")["journal"] == []


def test_a_database_born_before_hoola_design_heals_itself(design_env):
    from app import db
    from app.design import models
    for model in (models.DesignShare, models.DesignComment, models.DesignVersion, models.DesignOp, models.DesignFile):
        model.__table__.drop(db._engine)
    models._ready_for = None
    with client() as c:
        assert c.get("/api/design/files", headers=H).json() == {"files": []}
        assert new_file(c, name="After the upgrade")["nodes"] == 2


def test_checkpoint_every_n_ops_trims_the_journal(design_env):
    from app.design import store
    design_env.setenv("DESIGN_CHECKPOINT_OPS", "5")
    from app.config import get_settings
    get_settings.cache_clear()
    with client() as c:
        fid = new_file(c)["id"]
        with ws(c, fid) as a:
            ia = take(a, "init")
            for n in range(1, 8):
                a.send_json({"t": "ops", "n": n, "ops": [rect(f"{ia['cid']}:{n}", idx=fracidx.DIGITS[10 + n])]})
                take(a, "ack")
            for _ in range(300):
                raw = store.load_raw(fid, "default")
                if raw["seq"] >= 5 and raw["seq"] + len(raw["journal"]) == 7:
                    break
                time.sleep(0.01)
            assert raw["seq"] >= 5 and all(row[0] > raw["seq"] for row in raw["journal"])   # still in the file, already saved
            assert raw["seq"] + len(raw["journal"]) == 7
            with ws(c, fid) as b:                                                           # joins on the new snapshot
                ib = take(b, "init")
                assert ib["seq"] >= 5 and f"{ia['cid']}:5" in ib["doc"]["nodes"]


def test_idle_checkpoint(design_env):
    from app.design import store
    design_env.setenv("DESIGN_CHECKPOINT_IDLE_S", "0.2")
    from app.config import get_settings
    get_settings.cache_clear()
    with client() as c:
        fid = new_file(c)["id"]
        with ws(c, fid) as a:
            ia = take(a, "init")
            a.send_json({"t": "ops", "n": 1, "ops": [rect(f"{ia['cid']}:1")]})
            take(a, "ack")
            for _ in range(300):
                raw = store.load_raw(fid, "default")
                if raw["seq"] == 1:
                    break
                time.sleep(0.01)
            assert raw["seq"] == 1 and raw["journal"] == []                                 # quiet for a moment: saved


def test_a_view_only_guest_sees_everything_and_changes_nothing(design_env):
    with client() as c:
        fid = new_file(c, name="For the client")["id"]
        token = c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "view"}).json()["token"]
        with ws(c, fid) as a:
            ia = take(a, "init")
            with c.websocket_connect(f"/api/design/ws?share={token}") as guest:              # no key: the link is the pass
                ig = take(guest, "init")
                assert ig["file"] == {"id": fid, "name": "For the client", "role": "view"} and ig["you"]["name"] == "Guest"
                assert take(a, "join")["user"]["cid"] == ig["cid"]
                a.send_json({"t": "ops", "n": 1, "ops": [rect(f"{ia['cid']}:1")]})
                take(a, "ack")
                assert take(guest, "ops")["seq"] == 1                                       # the guest follows live

                guest.send_json({"t": "ops", "n": 1, "ops": [rect(f"{ig['cid']}:1"), {"id": f"{ia['cid']}:1", "del": 1}]})
                assert take(guest, "ack") == {"t": "ack", "n": 1, "seq": 1, "rejected": [0, 1]}   # every op refused
                guest.send_json({"t": "pres", "x": 3, "y": 4, "page": PAGE})
                assert take(a, "pres") == {"t": "pres", "x": 3, "y": 4, "page": PAGE, "cid": ig["cid"]}   # but she can point
                nodes = c.get(f"/api/design/files/{fid}/doc", headers=H).json()["doc"]["nodes"]
                assert f"{ia['cid']}:1" in nodes and f"{ig['cid']}:1" not in nodes

                guest.send_json({"t": "ops", "n": 2, "ops": [{"id": PAGE, "del": 1}]})
                guest.send_json({"t": "ops", "n": 3, "ops": [{"id": PAGE, "del": 1}]})
                with pytest.raises(WebSocketDisconnect) as e:                               # a guest that keeps writing is shown out
                    for _ in range(10):
                        guest.receive_json()
                assert e.value.code == 4403
            assert PAGE in c.get(f"/api/design/files/{fid}/doc", headers=H).json()["doc"]["nodes"]
        with c.websocket_connect("/api/design/ws?share=not-a-link") as sock, pytest.raises(WebSocketDisconnect) as e:
            sock.receive_json()
        assert e.value.code == 4404
        c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "none"})
        with c.websocket_connect(f"/api/design/ws?share={token}") as sock, pytest.raises(WebSocketDisconnect) as e:
            sock.receive_json()
        assert e.value.code == 4404


def test_frames_the_server_can_not_read_end_the_visit_not_the_room(design_env):
    with client() as c:
        fid = new_file(c)["id"]
        with ws(c, fid) as a:
            ia = take(a, "init")
            for bad in ("not json", '{"t":"ops","n":1,"ops":[{"id":"1:1","p":{"x":NaN}}]}', '{"t":"ops","n":"1","ops":[]}',
                        '{"t":"ops","n":1}', "[1,2]"):
                with ws(c, fid) as b, pytest.raises(WebSocketDisconnect) as e:
                    take(b, "init")
                    b.send_text(bad)
                    for _ in range(10):
                        b.receive_json()
                assert e.value.code == 1003, bad
                assert take(a, "leave")["t"] == "leave"
            with ws(c, fid) as b:
                take(b, "init")
                b.send_json({"t": "something-new", "x": 1})                                 # a newer client's frame: ignored
                b.send_json({"t": "ops", "n": 1, "ops": [rect("9:1", huge="x" * (300 * 1024)), rect("9:2")]})
                assert take(b, "ack") == {"t": "ack", "n": 1, "seq": 1, "rejected": [0]}    # one op over 256 KB
            a.send_json({"t": "ops", "n": 1, "ops": [rect(f"{ia['cid']}:1")]})
            assert take(a, "ack")["seq"] == 2                                               # the room never noticed


def test_trashing_a_file_shows_everyone_out(design_env):
    with client() as c:
        fid = new_file(c)["id"]
        with ws(c, fid) as a:
            ia = take(a, "init")
            a.send_json({"t": "ops", "n": 1, "ops": [rect(f"{ia['cid']}:1")]})
            take(a, "ack")
            c.delete(f"/api/design/files/{fid}", headers=H)
            with pytest.raises(WebSocketDisconnect) as e:
                for _ in range(10):
                    a.receive_json()
            assert e.value.code == 4404
        c.post(f"/api/design/files/{fid}/restore", headers=H)
        nodes = c.get(f"/api/design/files/{fid}/doc", headers=H).json()["doc"]["nodes"]
        assert f"{ia['cid']}:1" in nodes                                                    # her last edit was saved first


def test_a_slow_reader_is_dropped_and_the_room_carries_on(design_env):
    """A connection whose queue is full is closed; nobody else waits for it and cursor frames are shed first."""
    import asyncio

    from app.design import room as R

    class Stuck:                                             # a browser that stopped reading
        def __init__(self):
            self.closed = None

        async def send_text(self, _):
            await asyncio.sleep(3600)

        async def close(self, code):
            self.closed = code

    async def run():
        raw = {"tenant": "default", "name": "F", "doc": Doc(new_document()), "seq": 0, "base_json": "{}", "base_seq": 0,
               "tail": [], "replayed": 0}
        room = R.Room("df_slow", raw)
        slow_ws = Stuck()
        slow = R.Conn(room, slow_ws, 1, "Slow", "#111111", "edit")
        room.conns[1] = slow
        await asyncio.sleep(0)
        for i in range(R.QUEUE_MAX):
            slow.send('{"t":"pres"}', lossy=True)
        assert slow.queue.qsize() <= R.QUEUE_MAX // 2 + 1 and not slow.dead                 # cursors shed, still in the room
        started = time.perf_counter()
        for i in range(R.QUEUE_MAX + 5):
            room._commit([{"id": ROOT, "p": {"n": i}}], 2, False, None)
        assert time.perf_counter() - started < 5 and slow.dead                              # the room never waited for it
        await asyncio.sleep(0.05)
        assert 1 not in room.conns and slow_ws.closed == 1013
        assert room.seq == R.QUEUE_MAX + 5 and room.doc.nodes[ROOT]["n"] == R.QUEUE_MAX + 4
        room._ticker.cancel()
        if room._writer:
            room._writer.cancel()

    from app.design import store
    design_env.setattr(store, "append_ops", lambda *a: None)   # this room has no file row; the journal is not under test here
    asyncio.run(run())


def test_server_made_ops_go_through_the_room(design_env):
    """The hook the AI route and the agent tool use: checked, journaled, and seen by every open editor."""
    from app.design.room import HUB
    with client() as c:
        fid = new_file(c)["id"]
        with ws(c, fid) as a:
            take(a, "init")
            cid = c.portal.call(HUB.new_cid, fid)
            out = c.portal.call(HUB.apply_ops, fid, "default", [rect(f"{cid}:1", name="By Hoola"), {"id": ROOT, "del": 1}])
            assert out == {"seq": 1, "rejected": [1]}
            assert take(a, "ops") == {"t": "ops", "seq": 1, "by": 0, "ops": [rect(f"{cid}:1", name="By Hoola")]}
            with pytest.raises(LookupError):
                c.portal.call(HUB.apply_ops, fid, "someone-else", [])
    with client() as c:                                                                     # and with nobody in the file
        out = c.portal.call(HUB.apply_ops, fid, "default", [{"id": f"{cid}:1", "p": {"x": 5}}])
        assert out == {"seq": 2, "rejected": []}
        assert c.get(f"/api/design/files/{fid}/doc", headers=H).json()["doc"]["nodes"][f"{cid}:1"]["x"] == 5
