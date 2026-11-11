"""v0.825 HOOLA DESIGN D9c branches + merge (docs/HOOLA_DESIGN_PLAN.md section 8, design/branches.py).

Server half: the three-way diff on hand-built documents (every change and conflict kind), the merged document and
its ops, then the routes on a real app: make a branch (full copy, its own id range, base kept), list, preview,
merge (non-conflicting changes exactly, her choices honoured, 409 while a conflict is open or main moved), the
"Before merging" version that undoes it, a merged branch read only, the merge seen LIVE by an editor on main,
update from main, the rules (tenant, branch of a branch, 20 open).

Browser half: server/tests/web/design_branches_test.js against a REAL server on a free port (skips cleanly where
node, playwright or Chromium is missing)."""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
JS_TEST = HERE / "web" / "design_branches_test.js"
DESIGN = SERVER / "app" / "static" / "console" / "design"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")
H = {"Authorization": "Bearer kd"}
PAGE = "0:1"


def solid(c):
    return [{"type": "solid", "color": c, "opacity": 1, "visible": True}]


def doc(**extra):
    """A small hand-built document: page 0:1 with frame F holding A, B, C (+ D in its own frame G)."""
    nodes = {
        "0:0": {"type": "DOCUMENT", "name": "Document"},
        "0:1": {"type": "PAGE", "parent": "0:0", "idx": "a1", "name": "Page 1"},
        "F": {"type": "FRAME", "parent": "0:1", "idx": "a1", "name": "Phone", "w": 390, "h": 700},
        "G": {"type": "FRAME", "parent": "0:1", "idx": "a2", "name": "Tablet", "w": 800, "h": 600},
        "A": {"type": "RECT", "parent": "F", "idx": "a1", "name": "Hero", "fills": solid("#FF8800"), "x": 10},
        "B": {"type": "RECT", "parent": "F", "idx": "a2", "name": "Card", "x": 20},
        "C": {"type": "TEXT", "parent": "F", "idx": "a3", "name": "Title", "chars": "Hello"},
        "D": {"type": "RECT", "parent": "G", "idx": "a1", "name": "Box"},
    }
    nodes.update(extra)
    return nodes


def clone(nodes):
    return json.loads(json.dumps(nodes))


# ============================================================================================ pure: the diff
def test_one_sided_changes_are_listed_and_not_conflicts():
    from app.design import branches as BR
    B = doc()
    O, T = clone(B), clone(B)
    O["A"]["x"] = 50                                           # changed here
    O["N"] = {"type": "RECT", "parent": "F", "idx": "a4", "name": "New"}  # added here
    del O["C"]                                                 # removed here
    T["B"]["name"] = "Card on main"                            # changed on main
    out = BR.analyse(B, O, T)
    assert out["conflicts"] == []
    ours = {c["id"]: c for c in out["changes"]["ours"]}
    assert ours["chg:A"]["props"] == ["X"] and ours["add:N"]["kind"] == "added" and ours["del:C"]["kind"] == "removed"
    assert ours["chg:A"]["path"] == "Page 1 / Phone / Hero" and ours["chg:A"]["page"] == "0:1"
    assert [c["id"] for c in out["changes"]["theirs"]] == ["chg:B"]
    assert out["counts"]["ours"] == {"added": 1, "removed": 1, "changed": 1, "total": 3} and out["counts"]["conflicts"] == 0


def test_same_change_on_both_sides_is_no_conflict():
    from app.design import branches as BR
    B = doc()
    O, T = clone(B), clone(B)
    O["A"]["fills"] = T["A"]["fills"] = solid("#000000")
    assert BR.analyse(B, O, T)["conflicts"] == []


def test_every_conflict_kind_is_found_and_said_plainly():
    from app.design import branches as BR
    B = doc(E={"type": "RECT", "parent": "G", "idx": "a2", "name": "Spare"})
    O, T = clone(B), clone(B)
    O["A"]["fills"], T["A"]["fills"] = solid("#11AA11"), solid("#2266FF")       # the fill changed on both sides
    O["B"]["parent"], O["B"]["idx"] = "G", "a3"                                  # moved to G here ...
    T["B"]["parent"], T["B"]["idx"] = "0:1", "a3"                                # ... to the page on main
    O["C"]["idx"], T["C"]["idx"] = "a0V", "a2V"                                  # re-ordered differently
    O["D"]["name"] = "Box here"                                                  # changed here ...
    del T["G"], T["D"], T["E"]                                                   # ... its frame deleted on main
    T2 = clone(B)
    out = BR.analyse(B, O, T)
    kinds = {c["id"]: c for c in out["conflicts"]}
    assert kinds["prop:A:fills"]["text"] == "Fill: #11AA11 here, #2266FF on main"
    assert kinds["move:B"]["kind"] == "move" and "Tablet" in kinds["move:B"]["text"] and "Page 1" in kinds["move:B"]["text"]
    assert kinds["order:C"]["kind"] == "order"
    gone = kinds["del-main:G"]
    assert gone["kind"] == "deleted_main" and gone["count"] == 2                 # D renamed + B moved in
    # deleted here, changed on main
    O2 = clone(B)
    del O2["G"], O2["D"], O2["E"]
    T2["D"]["fills"] = solid("#123456")
    here = {c["id"]: c for c in BR.analyse(B, O2, T2)["conflicts"]}
    assert list(here) == ["del-here:G"] and here["del-here:G"]["kind"] == "deleted_here"
    # deleted here, nothing changed on main: no conflict, just a removal
    assert BR.analyse(B, O2, clone(B))["conflicts"] == []


def test_the_merged_document_takes_each_side_and_her_choices():
    from app.design import branches as BR
    B = doc()
    O, T = clone(B), clone(B)
    O["A"]["x"] = 50                                           # ours only
    T["A"]["name"] = "Hero (main)"                             # theirs only, same node, other prop: both win
    O["B"]["fills"], T["B"]["fills"] = solid("#111111"), solid("#222222")
    O["N"] = {"type": "RECT", "parent": "F", "idx": "a2", "name": "New"}      # its idx collides with B on main
    T["M"] = {"type": "RECT", "parent": "F", "idx": "a5", "name": "Main new"}
    del O["C"]
    merged, open_ids, _ = BR.build(B, O, T, {})
    assert open_ids == ["prop:B:fills"]
    merged, open_ids, _ = BR.build(B, O, T, {"prop:B:fills": "ours"})
    assert open_ids == []
    assert merged["A"]["x"] == 50 and merged["A"]["name"] == "Hero (main)"
    assert merged["B"]["fills"] == solid("#111111") and "C" not in merged and "M" in merged
    assert merged["N"]["parent"] == "F" and "a2" < merged["N"]["idx"] < "a5"                 # re-fractioned above B, under M
    merged, _, _ = BR.build(B, O, T, {"prop:B:fills": "theirs"})
    assert merged["B"]["fills"] == solid("#222222")
    # the ops, applied to main, give exactly the merged document
    from app.design.doc import Doc
    ops = BR.ops_between(T, merged)
    d = Doc(clone(T))
    assert all(d.apply(op) == 1 for op in ops)
    assert d.nodes == merged


def test_structure_choices_bring_a_frame_back_or_let_it_go():
    from app.design import branches as BR
    from app.design.doc import Doc
    B = doc()
    O, T = clone(B), clone(B)
    O["D"]["name"] = "Box here"
    O["K"] = {"type": "ELLIPSE", "parent": "G", "idx": "a2", "name": "Dot"}      # made inside G here
    O["A"]["parent"], O["A"]["idx"] = "G", "a3"                                    # moved into G here
    del T["G"], T["D"]                                                             # G deleted on main
    keep, _, _ = BR.build(B, O, T, {"del-main:G": "ours"})
    assert keep["G"]["name"] == "Tablet" and keep["D"]["name"] == "Box here" and keep["K"]["parent"] == "G"
    assert keep["A"]["parent"] == "G"
    drop, _, _ = BR.build(B, O, T, {"del-main:G": "theirs"})
    assert "G" not in drop and "K" not in drop and drop["A"]["parent"] == "F"      # A stays where main has it
    for merged in (keep, drop):
        d = Doc(clone(T))
        assert all(d.apply(op) == 1 for op in BR.ops_between(T, merged)) and d.nodes == merged


def test_moves_that_cross_never_make_a_cycle():
    from app.design import branches as BR
    from app.design.doc import Doc
    B = doc()
    O, T = clone(B), clone(B)
    O["F"]["parent"], O["F"]["idx"] = "G", "a5"                    # F inside G here
    T["G"]["parent"], T["G"]["idx"] = "F", "a9"                    # G inside F on main
    merged, open_ids, notes = BR.build(B, O, T, {})
    assert open_ids == [] and notes and merged["G"]["parent"] == "F" and merged["F"]["parent"] == "0:1"
    # a swap: main nests B under A; the merge un-nests and nests the other way - shallow first, every step valid
    B2 = doc()
    T2 = clone(B2)
    T2["B"]["parent"] = "A"
    O2 = clone(B2)
    O2["A"]["parent"], O2["A"]["idx"] = "B", "a1"
    merged2, _, notes2 = BR.build(B2, O2, T2, {})
    d = Doc(clone(T2))
    assert all(d.apply(op) == 1 for op in BR.ops_between(T2, merged2))


def test_plain_words():
    from app.design.branches import label, say
    assert say(solid("#ff8800")) == "#FF8800" and say(None) == "not set" and say(True) == "on" and say(12.5) == "12.5"
    assert say("Hello there") == "“Hello there”" and say([]) == "none" and label("fontSize") == "Font size"
    assert label("someNewProp") == "Some new prop"


# ============================================================================================ the routes
@pytest.fixture()
def design_env(env, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    from app.config import get_settings
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def client():
    from app.main import app
    return TestClient(app)


def take(sock, kind):
    for _ in range(50):
        frame = sock.receive_json()
        if frame["t"] == kind:
            return frame
    raise AssertionError(f"no {kind} frame")


def send(sock, n, ops):
    sock.send_json({"t": "ops", "n": n, "ops": ops})
    ack = take(sock, "ack")
    assert ack["rejected"] == [], ack
    return ack


def rect(nid, parent=PAGE, idx="a5", **props):
    return {"id": nid, "p": {"type": "RECT", "parent": parent, "idx": idx, "name": "Rect", **props}}


def nodes_of(c, fid):
    return c.get(f"/api/design/files/{fid}/doc", headers=H).json()["doc"]["nodes"]


def edit(c, fid, ops, n=1):
    with c.websocket_connect(f"/api/design/ws?file={fid}", headers=H) as ws:
        init = take(ws, "init")
        send(ws, n, ops)
        return init


def other_tenant():
    from app import accounts
    from app.db import User, session
    with session() as s:
        u = User(email="other@example.com", name="Other Person")
        s.add(u)
        s.flush()
        uid = u.id
    return {"Authorization": f"Bearer {accounts.issue_session(uid)}"}


def seeded(c):
    fid = c.post("/api/design/files", headers=H, json={"name": "Poster"}).json()["id"]
    edit(c, fid, [rect("1:1", name="Hero", fills=solid("#FF8800"), x=10), rect("1:2", idx="a6", name="Card", x=20)])
    return fid


def test_a_branch_is_a_full_copy_with_its_base_and_its_own_ids(design_env):
    with client() as c:
        fid = seeded(c)
        r = c.post(f"/api/design/files/{fid}/branches", headers=H, json={"name": "Try blue"})
        assert r.status_code == 200, r.text
        br = r.json()
        assert br["name"] == "Try blue" and br["main"] == fid and br["state"] == "open" and br["main_name"] == "Poster"
        assert nodes_of(c, br["id"]) == nodes_of(c, fid)
        with c.websocket_connect(f"/api/design/ws?file={br['id']}", headers=H) as ws:
            assert take(ws, "init")["cid"] > 1_000_000                         # its own client-number range
        base = c.get(f"/api/design/files/{br['id']}/merge/base", headers=H).json()
        assert base["doc"]["nodes"] == nodes_of(c, fid) and base["seq"] == br["base_seq"]
        listed = c.get(f"/api/design/files/{fid}/branches", headers=H).json()
        assert listed["is_branch"] is False and [b["id"] for b in listed["branches"]] == [br["id"]]
        from_branch = c.get(f"/api/design/files/{br['id']}/branches", headers=H).json()
        assert from_branch["is_branch"] is True and from_branch["main"]["id"] == fid
        idx = c.get("/api/design/branches", headers=H).json()["branches"]
        assert idx == [{"id": br["id"], "main": fid, "main_name": "Poster", "state": "open"}]
        # rules: a branch of a branch, another tenant, a missing file
        assert c.post(f"/api/design/files/{br['id']}/branches", headers=H, json={}).status_code == 409
        other = other_tenant()
        assert c.post(f"/api/design/files/{fid}/branches", headers=other, json={}).status_code == 404
        assert c.get(f"/api/design/files/{br['id']}/merge", headers=other).status_code == 404
        assert c.post(f"/api/design/files/{br['id']}/merge", headers=other, json={"main_seq": 1}).status_code == 404
        assert c.get(f"/api/design/files/{fid}/branches", headers=other).status_code == 404
        assert c.get("/api/design/branches", headers=other).json()["branches"] == []
        assert c.post("/api/design/files/df_nope/branches", headers=H, json={}).status_code == 404
        assert c.post(f"/api/design/files/{fid}/branches").status_code == 401
        assert c.get(f"/api/design/files/{fid}/merge", headers=H).status_code == 409     # main is not a branch


def test_twenty_open_branches_at_most(design_env):
    from app.design import branches as BR
    with client() as c:
        fid = seeded(c)
        design_env.setattr(BR, "MAX_OPEN", 3)
        for i in range(3):
            assert c.post(f"/api/design/files/{fid}/branches", headers=H, json={"name": f"b{i}"}).status_code == 200
        r = c.post(f"/api/design/files/{fid}/branches", headers=H, json={})
        assert r.status_code == 409 and "3 open branches" in r.json()["detail"]
    assert BR.MAX_OPEN == 3 and __import__("app.design.branches", fromlist=["x"]).ID_RANGE == 1_000_000


def test_merge_applies_exactly_honours_choices_and_can_be_undone(design_env):
    with client() as c:
        fid = seeded(c)
        br = c.post(f"/api/design/files/{fid}/branches", headers=H, json={"name": "Blue"}).json()
        bid = br["id"]
        with c.websocket_connect(f"/api/design/ws?file={bid}", headers=H) as ws:
            cid = take(ws, "init")["cid"]
            send(ws, 1, [{"id": "1:1", "p": {"fills": solid("#2266FF"), "x": 99}},     # fill conflicts, x does not
                         rect(f"{cid}:1", idx="a7", name="Badge"),
                         {"id": "1:2", "del": 1}])
        edit(c, fid, [{"id": "1:1", "p": {"fills": solid("#00AA00"), "name": "Hero on main"}}])
        pv = c.get(f"/api/design/files/{bid}/merge", headers=H)
        assert pv.status_code == 200, pv.text
        pv = pv.json()
        conflicts = {x["id"]: x for x in pv["conflicts"]}
        assert list(conflicts) == ["prop:1:1:fills"]
        assert conflicts["prop:1:1:fills"]["text"] == "Fill: #2266FF here, #00AA00 on main"
        assert "ours_value" not in conflicts["prop:1:1:fills"]
        ours = {x["id"] for x in pv["changes"]["ours"]}
        assert ours == {"chg:1:1", f"add:{cid}:1", "del:1:2"}
        # an open conflict refuses; so does a stale preview
        r = c.post(f"/api/design/files/{bid}/merge", headers=H, json={"main_seq": pv["main_seq"], "resolutions": {}})
        assert r.status_code == 409 and "not decided" in r.json()["detail"]
        r = c.post(f"/api/design/files/{bid}/merge", headers=H, json={"main_seq": pv["main_seq"] - 1,
                                                                      "resolutions": {"prop:1:1:fills": "ours"}})
        assert r.status_code == 409 and "Review it again" in r.json()["detail"]
        assert c.post(f"/api/design/files/{bid}/merge", headers=H, json={"main_seq": pv["main_seq"],
                                                                         "resolutions": {"prop:1:1:fills": "maybe"}}).status_code == 400
        before = nodes_of(c, fid)
        r = c.post(f"/api/design/files/{bid}/merge", headers=H, json={"main_seq": pv["main_seq"], "branch_seq": pv["branch_seq"],
                                                                      "resolutions": {"prop:1:1:fills": "ours"}})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["state"] == "merged" and out["rejected"] == [] and out["saved"]["label"] == "Before merging Blue"
        after = nodes_of(c, fid)
        assert after["1:1"]["fills"] == solid("#2266FF") and after["1:1"]["x"] == 99 and after["1:1"]["name"] == "Hero on main"
        assert after[f"{cid}:1"]["name"] == "Badge" and "1:2" not in after
        assert set(after) == set(before) - {"1:2"} | {f"{cid}:1"}
        # the branch is read only now: its editors join as viewers and their ops are refused
        with c.websocket_connect(f"/api/design/ws?file={bid}", headers=H) as ws:
            assert take(ws, "init")["file"]["role"] == "view"
            ws.send_json({"t": "ops", "n": 1, "ops": [{"id": "1:1", "p": {"x": 1}}]})
            assert take(ws, "ack")["rejected"] == [0]
        assert c.post(f"/api/design/files/{bid}/merge", headers=H, json={"main_seq": out["seq"]}).status_code == 409
        assert c.get(f"/api/design/files/{fid}/branches", headers=H).json()["branches"][0]["state"] == "merged"
        # restoring "Before merging" undoes the merge
        assert c.post(f"/api/design/versions/{out['saved']['id']}/restore", headers=H).status_code == 200
        assert nodes_of(c, fid) == before


def test_choosing_main_keeps_main_and_the_rest_still_lands(design_env):
    with client() as c:
        fid = seeded(c)
        bid = c.post(f"/api/design/files/{fid}/branches", headers=H, json={}).json()["id"]
        edit(c, bid, [{"id": "1:1", "p": {"fills": solid("#2266FF"), "y": 7}}])
        edit(c, fid, [{"id": "1:1", "p": {"fills": solid("#00AA00")}}])
        pv = c.get(f"/api/design/files/{bid}/merge", headers=H).json()
        r = c.post(f"/api/design/files/{bid}/merge", headers=H, json={"main_seq": pv["main_seq"],
                                                                      "resolutions": {"prop:1:1:fills": "theirs"}})
        assert r.status_code == 200, r.text
        n = nodes_of(c, fid)["1:1"]
        assert n["fills"] == solid("#00AA00") and n["y"] == 7


def test_an_editor_on_main_sees_the_merge_live(design_env):
    with client() as c:
        fid = seeded(c)
        bid = c.post(f"/api/design/files/{fid}/branches", headers=H, json={"name": "Live"}).json()["id"]
        edit(c, bid, [{"id": "1:1", "p": {"name": "Merged name"}}])
        with c.websocket_connect(f"/api/design/ws?file={fid}", headers=H) as main_ws, \
                c.websocket_connect(f"/api/design/ws?file={bid}", headers=H) as branch_ws:
            take(main_ws, "init")
            assert take(branch_ws, "init")["file"]["role"] == "edit"
            pv = c.get(f"/api/design/files/{bid}/merge", headers=H).json()
            r = c.post(f"/api/design/files/{bid}/merge", headers=H, json={"main_seq": pv["main_seq"]})
            assert r.status_code == 200, r.text
            frame = take(main_ws, "ops")
            assert frame["by"] == 0 and frame["ops"] == [{"id": "1:1", "p": {"name": "Merged name"}}]
            take(branch_ws, "reload")                      # the branch's editor reloads and comes back as a viewer
        with c.websocket_connect(f"/api/design/ws?file={bid}", headers=H) as ws:
            assert take(ws, "init")["file"]["role"] == "view"


def test_update_branch_from_main(design_env):
    with client() as c:
        fid = seeded(c)
        bid = c.post(f"/api/design/files/{fid}/branches", headers=H, json={}).json()["id"]
        edit(c, bid, [{"id": "1:1", "p": {"x": 55, "fills": solid("#2266FF")}}])
        edit(c, fid, [{"id": "1:2", "p": {"name": "Card v2"}}, {"id": "1:1", "p": {"fills": solid("#00AA00")}},
                      rect("9:1", idx="a8", name="From main")])
        pv = c.get(f"/api/design/files/{bid}/merge", headers=H).json()
        assert [x["id"] for x in pv["conflicts"]] == ["prop:1:1:fills"]
        r = c.post(f"/api/design/files/{bid}/update", headers=H, json={"main_seq": pv["main_seq"],
                                                                       "resolutions": {"prop:1:1:fills": "ours"}})
        assert r.status_code == 200, r.text
        assert r.json()["state"] == "open" and r.json()["saved"]["label"] == "Before updating from main"
        n = nodes_of(c, bid)
        assert n["1:2"]["name"] == "Card v2" and n["9:1"]["name"] == "From main" and n["1:1"]["x"] == 55
        assert n["1:1"]["fills"] == solid("#2266FF")
        assert nodes_of(c, fid)["1:1"].get("x") == 10                         # main untouched by an update
        # the base moved forward: no conflict any more, the branch's fill now reads as its own change
        pv2 = c.get(f"/api/design/files/{bid}/merge", headers=H).json()
        assert pv2["conflicts"] == [] and pv2["base_seq"] == pv["main_seq"]
        assert {x["id"] for x in pv2["changes"]["ours"]} == {"chg:1:1"}
        assert pv2["changes"]["theirs"] == []


def test_the_page_carries_the_branch_files():
    html = (DESIGN / "design.html").read_text()
    assert "design-branches.css" in html and "hd-branches.js" in html
    order = [html.index(f"design/{n}") for n in ("hd-collab.js", "hd-branches.js", "hd-app.js")]
    assert order == sorted(order)
    stamp = html.split("hd-app.js?v=")[1].split('"')[0]
    assert f"hd-branches.js?v={stamp}" in html and f"design-branches.css?v={stamp}" in html


@needs_node
def test_the_client_files_parse():
    for name in ("hd-branches.js", "../../../../tests/web/design_branches_test.js"):
        run = subprocess.run([NODE, "--check", str((DESIGN / name).resolve())], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@needs_node
def test_branch_review_and_merge_in_a_real_browser(tmp_path):
    port, key = _free_port(), "branch-test-key"
    env = os.environ.copy()
    env.update({"DATABASE_URL": f"sqlite:///{tmp_path}/branches.db", "API_KEY": key, "WA_DRY_RUN": "true", "ANTHROPIC_API_KEY": "test",
                "SEMANTIC_OFF": "1", "MEMORY_AUTO": "false", "HOOLA_ENRICH": "false", "VIDEO_EDIT_WORKER": "false",
                "OPERATOR_WORKER": "false", "DESIGN_PAGE": "true", "PYTHONPATH": str(SERVER)})
    env.pop("DESIGN_DIR", None)
    log = open(tmp_path / "server.log", "w")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
                              cwd=tmp_path, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        base, up = f"http://127.0.0.1:{port}", False
        for _ in range(240):
            if server.poll() is not None:
                break
            try:
                with urllib.request.urlopen(base + "/console/design", timeout=2) as r:
                    up = r.status == 200
                    break
            except Exception:                            # noqa: BLE001 - not listening yet
                time.sleep(0.5)
        if not up:
            log.flush()
            pytest.fail("the server did not start: " + (tmp_path / "server.log").read_text()[-1500:])
        jenv = os.environ.copy()
        jenv.update({"HD_BASE": base, "HD_KEY": key})
        if jenv.get("HOOLA_CHROMIUM"):
            jenv["CHROMIUM_EXECUTABLE"] = jenv["HOOLA_CHROMIUM"]
        run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=600, env=jenv)
        if run.returncode == 77 and not jenv.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
            jenv["HOOLA_CHROMIUM"] = SANDBOX_CHROME
            run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=600, env=jenv)
    finally:
        server.terminate()
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    assert run.returncode == 0, (run.stdout[-1500:] + "\n" + run.stderr[-4000:] + "\n--- server ---\n" + (tmp_path / "server.log").read_text()[-1500:])
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["ok"] is True and report["checks"] >= 25, report
