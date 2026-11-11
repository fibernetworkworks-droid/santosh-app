"""HOOLA DESIGN D9b speed (docs/HOOLA_DESIGN_PLAN.md section 8): a big file PAGE BY PAGE, the compact op frames (c1),
the `ex` mark, and the measured harness.

Server half here: the c1 codec is the browser's own (the key table read out of hd-net.js), a lazy init over a real
socket is the root + every page node + the page she asked for, cut at that moment; a page asked for later sits at its
place in the stream; c1 both ways next to a JSON editor; an old browser that asks for nothing gets exactly the frames
it always got. Browser half: server/tests/web/design_perf_test.js against a REAL server started here on a free port
(5k / 20k / 100k layers: open time, the index, layout, round trips, bytes) - it prints its table and asserts its
budgets; skipped when node, playwright or Chromium is missing. The client store's partial-load convergence soak is
in server/tests/web/design_core_test.js (run by test_v0777_design_core.py)."""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.design import wire
from app.design.doc import ROOT, Doc

SERVER = Path(__file__).resolve().parents[1]
DESIGN = SERVER / "app" / "static" / "console" / "design"
JS_TEST = Path(__file__).resolve().parent / "web" / "design_perf_test.js"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")
H = {"Authorization": "Bearer kd"}


@pytest.fixture()
def design_env(env, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    monkeypatch.setenv("DESIGN_LAZY_NODES", "10")              # every test file here is "big"
    from app.config import get_settings
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def client():
    from app.main import app
    return TestClient(app)


def take(sock, kind):
    for _ in range(60):
        frame = sock.receive_json()
        if isinstance(frame, list):
            if {1: "ops", 2: "ops", 3: "ack"}.get(frame[0]) == kind:
                return frame
            continue
        if frame["t"] == kind:
            return frame
    raise AssertionError(f"no {kind} frame")


# ------------------------------------------------------------------------------------------------ c1
def test_the_key_table_is_the_browsers_own():
    net = (DESIGN / "hd-net.js").read_text(encoding="utf-8")
    block = re.search(r"var KEYS = \[(.*?)\];", net, re.S).group(1)
    assert tuple(re.findall(r"'([^']+)'", block)) == wire.KEYS
    assert len(set(wire.KEYS)) == len(wire.KEYS)


def test_c1_round_trips_every_op_shape_and_refuses_junk():
    ops = [{"id": "3:1", "del": 1}, {"id": "3:2", "p": {}},
           {"id": "3:3", "p": {"type": "RECT", "parent": "0:1", "idx": "a0", "x": 1.25, "fills": [{"type": "solid", "color": "#FF0000"}],
                               "brandNew": {"a": [1, None]}, "name": None}},
           {"id": "3:4", "p": {"x": 1}, "ex": 1}]
    for op in ops:
        enc = json.loads(json.dumps(wire.enc_op(op)))
        assert wire.dec_op(enc) == op
    assert wire.enc_op(ops[2])[1] == 0 and "brandNew" in wire.enc_op(ops[2])          # known keys are numbers, others stay names
    for junk in ([], [5], ["1:1", 999, 1], ["1:1", 4], ["1:1", 4.5, 1], "x", None):
        assert wire.dec_op(junk) is None
    assert wire.from_c1([1, 3, [["1:1", 4, 9]]]) == {"t": "ops", "n": 3, "ops": [{"id": "1:1", "p": {"x": 9}}]}
    assert wire.from_c1([2, 3, 1, []]) is None and wire.from_c1([1, "3", []]) is None
    assert json.loads(wire.ack_frame(4, 9, [1], [])) == [3, 4, 9, [1]]
    assert json.loads(wire.ack_frame(4, 9, [], [0])) == [3, 4, 9, [], [0]]
    one = {"id": "3:3", "p": {"x": 100.5, "y": 200}}
    assert len(json.dumps(wire.enc_op(one), separators=(",", ":"))) < len(json.dumps(one, separators=(",", ":")))


# ------------------------------------------------------------------------------------------------ the cut
def _doc():
    nodes = {ROOT: {"type": "DOCUMENT", "name": "D"}}
    for i in (1, 2, 3):
        nodes[f"0:{i}"] = {"type": "PAGE", "parent": ROOT, "idx": f"a{i}", "name": f"P{i}"}
    nodes["1:1"] = {"type": "COMPONENT", "parent": "0:3", "idx": "a0", "name": "Card"}
    nodes["1:2"] = {"type": "RECT", "parent": "1:1", "idx": "a0", "name": "Bar"}
    nodes["1:3"] = {"type": "FRAME", "parent": "0:1", "idx": "a0", "name": "F"}
    nodes["1:4"] = {"type": "INSTANCE", "parent": "1:3", "idx": "a0", "name": "I", "comp": "1:1"}
    nodes["1:5"] = {"type": "RECT", "parent": "0:2", "idx": "a0", "name": "R"}
    return Doc(nodes)


def test_a_cut_is_the_root_every_page_and_the_wanted_pages_with_their_components():
    doc = _doc()
    nodes, sent, rest = wire.cut(doc, [])                        # nothing asked: the first page
    assert sent == ["0:3", "0:1"] and rest == ["0:2"]            # the component's page comes first, then hers
    assert set(nodes) == {ROOT, "0:1", "0:2", "0:3", "1:1", "1:2", "1:3", "1:4"}
    nodes["1:3"]["name"] = "changed in the copy"
    assert doc.nodes["1:3"]["name"] == "F"                       # copies: the room's document is never handed out
    nodes, sent, rest = wire.cut(doc, ["0:2", "nope"])
    assert sent == ["0:2"] and set(rest) == {"0:1", "0:3"} and "1:5" in nodes and "1:3" not in nodes
    order, cuts = wire.closure(doc, ["0:1"], {"0:3"})            # she has the component's page: not sent again
    assert order == ["0:1"] and set(cuts["0:1"]) == {"0:1", "1:3", "1:4"}
    assert wire.page_counts(doc.copy_nodes()) == {"0:1": 3, "0:2": 2, "0:3": 3}


# ------------------------------------------------------------------------------------------------ the room
def _fill(c, fid):
    """Three pages with a few layers each, made by an editor through the room."""
    with c.websocket_connect(f"/api/design/ws?file={fid}", headers=H) as a:
        take(a, "init")
        ops = [{"id": "9:1", "p": {"type": "PAGE", "parent": ROOT, "idx": "b1", "name": "Two"}},
               {"id": "9:2", "p": {"type": "PAGE", "parent": ROOT, "idx": "b2", "name": "Three"}}]
        for pg, pre in (("0:1", "a"), ("9:1", "b"), ("9:2", "c")):
            ops.append({"id": f"9:{pre}f", "p": {"type": "FRAME", "parent": pg, "idx": "a0", "name": "F", "w": 100, "h": 100}})
            for k in range(5):
                ops.append({"id": f"9:{pre}{k}", "p": {"type": "RECT", "parent": f"9:{pre}f", "idx": f"a{k}", "name": "R", "x": k}})
        a.send_json({"t": "ops", "n": 1, "ops": ops})
        assert take(a, "ack")["rejected"] == []


def test_a_lazy_editor_gets_one_page_then_the_rest_in_its_stream_and_speaks_c1(design_env):
    with client() as c:
        fid = c.post("/api/design/files", headers=H, json={}).json()["id"]
        _fill(c, fid)
        with c.websocket_connect(f"/api/design/ws?file={fid}", headers=H) as a, \
                c.websocket_connect(f"/api/design/ws?file={fid}&lazy=1&pages=9:1&enc=c1", headers=H) as b:
            ia = take(a, "init")
            assert "enc" not in ia and "lazy" not in ia and len(ia["doc"]["nodes"]) == 22    # an old editor: exactly as before
            ib = take(b, "init")
            assert ib["use"] == "c1" and ib["enc"] == ["json", "c1"]
            assert sorted(ib["lazy"]) == ["0:1", "9:2"]
            assert set(ib["doc"]["nodes"]) == {ROOT, "0:1", "9:1", "9:2", "9:bf"} | {f"9:b{k}" for k in range(5)}
            assert [p["id"] for p in ib["pages"]] == ["0:1", "9:1", "9:2"] and ib["pages"][1]["name"] == "Two"
            take(a, "join")
            # an edit on a page b does not hold: the JSON editor sends, b hears it in c1 (and skips it in the browser)
            a.send_json({"t": "ops", "n": 1, "ops": [{"id": "9:a1", "p": {"x": 55}}]})
            assert ib["seq"] == ia["seq"]                                                   # cut at this moment: no op tail
            assert take(a, "ack") == {"t": "ack", "n": 1, "seq": ia["seq"] + 1, "rejected": []}
            assert take(b, "ops") == [2, ia["seq"] + 1, ia["cid"], [["9:a1", 4, 55]]]
            # b asks for page One: it comes AFTER that op, so the op is already inside it
            b.send_json({"t": "page", "id": "0:1"})
            page = b.receive_json()
            assert page["t"] == "page" and page["id"] == "0:1" and page["nodes"]["9:a1"]["x"] == 55
            assert set(page["nodes"]) == {"0:1", "9:af"} | {f"9:a{k}" for k in range(5)}
            # c1 from b: the JSON editor hears JSON
            b.send_text(json.dumps([1, 1, [["9:b0", 4, 7, 3, "Moved"], ["9:b4"]]]))
            assert take(b, "ack") == [3, 1, ia["seq"] + 2, []]
            assert take(a, "ops")["ops"] == [{"id": "9:b0", "p": {"x": 7, "name": "Moved"}}, {"id": "9:b4", "del": 1}]
            # a "create" of a node the server has: marked ex in the ack and in the fan-out
            a.send_json({"t": "ops", "n": 2, "ops": [{"id": "9:b1", "p": {"type": "RECT", "parent": "9:bf", "idx": "a1", "name": "Again"}}]})
            assert take(a, "ack") == {"t": "ack", "n": 2, "seq": ia["seq"] + 3, "rejected": [], "ex": [0]}
            assert take(b, "ops")[3][0][-2:] == [-2, 1]
            # a page that is not there (any more) answers null; junk ids are ignored
            b.send_json({"t": "page", "id": "no:such"})
            assert b.receive_json() == {"t": "page", "id": "no:such", "nodes": None}
            b.send_json({"t": "page", "id": 5})
            b.send_json({"t": "ping"})
            assert b.receive_json() == {"t": "pong"}


def test_a_small_file_comes_whole_even_to_a_lazy_browser_and_a_view_guest_may_ask_too(design_env):
    design_env.setenv("DESIGN_LAZY_NODES", "100000")
    from app.config import get_settings
    get_settings.cache_clear()
    with client() as c:
        fid = c.post("/api/design/files", headers=H, json={}).json()["id"]
        _fill(c, fid)
        with c.websocket_connect(f"/api/design/ws?file={fid}&lazy=1&enc=c1", headers=H) as b:
            ib = take(b, "init")
            assert "lazy" not in ib and len(ib["doc"]["nodes"]) == 22 and ib["use"] == "c1"
        token = c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "view"}).json()["token"]
        design_env.setenv("DESIGN_LAZY_NODES", "5")
        get_settings.cache_clear()
    with client() as c:
        with c.websocket_connect(f"/api/design/ws?share={token}&lazy=1") as g:
            ig = take(g, "init")
            assert ig["file"]["role"] == "view" and ig["lazy"] and ig["use"] == "json"
            g.send_json({"t": "page", "id": ig["lazy"][0]})
            assert g.receive_json()["t"] == "page"
            g.send_text(json.dumps([1, 1, [["9:a0", 4, 1]]]))      # a guest's c1 ops are refused like its JSON ones
            assert take(g, "ack") == {"t": "ack", "n": 1, "seq": ig["seq"], "rejected": [0]}


def test_the_server_side_wiring_is_small_and_named():
    room = (SERVER / "app" / "design" / "room.py").read_text(encoding="utf-8")
    for needle in ('elif kind == "page":', "wire.from_c1(frame)", "frame = await frame", "wire.cut(self.doc, lazy)", 'dict(op, ex=1)'):
        assert needle in room, needle
    api = (SERVER / "app" / "design" / "api.py").read_text(encoding="utf-8")
    assert 'lazy: str = ""' in api and "room.admit(ws, role, name, lazy=want" in api
    html = (DESIGN / "design.html").read_text(encoding="utf-8")
    assert html.index("design/hd-core.js") < html.index("design/hd-index.js") < html.index("design/hd-net.js")
    idx = (DESIGN / "hd-index.js").read_text(encoding="utf-8")
    assert "'use strict';" in idx and idx.isascii() and "eval(" not in idx and "new Function" not in idx


# ------------------------------------------------------------------------------------------------ the harness
@needs_node
def test_the_client_files_parse():
    for path in (DESIGN / "hd-index.js", DESIGN / "hd-net.js", DESIGN / "hd-core.js", JS_TEST):
        run = subprocess.run([NODE, "--check", str(path)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@needs_node
def test_the_speed_harness_on_a_real_server(tmp_path):
    """The real server (uvicorn, a fresh SQLite database in the test folder) + headless Chromium + three socket clients."""
    port, key = _free_port(), "speed-test-key"
    env = os.environ.copy()
    env.update({"DATABASE_URL": f"sqlite:///{tmp_path}/speed.db", "API_KEY": key, "WA_DRY_RUN": "true", "ANTHROPIC_API_KEY": "test",
                "SEMANTIC_OFF": "1", "MEMORY_AUTO": "false", "HOOLA_ENRICH": "false", "VIDEO_EDIT_WORKER": "false",
                "OPERATOR_WORKER": "false", "DESIGN_PAGE": "true", "DESIGN_DIR": str(tmp_path / "design"), "PYTHONPATH": str(SERVER)})
    log = open(tmp_path / "server.log", "w")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning",
                               "--ws-max-size", str(64 * 1024 * 1024)],
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
        run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=1500, env=jenv)
        if run.returncode == 77 and not jenv.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
            jenv["HOOLA_CHROMIUM"] = SANDBOX_CHROME
            run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=1500, env=jenv)
    finally:
        server.terminate()
        try:
            server.wait(timeout=30)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    print(run.stdout[:6000])
    assert run.returncode == 0, (run.stdout[-3000:] + "\n" + run.stderr[-4000:] + "\n--- server ---\n" + (tmp_path / "server.log").read_text()[-1500:])
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["ok"] is True and report["checks"] >= 20, report
