"""v0.777 HOOLA DESIGN, phase D5 "together" (docs/HOOLA_DESIGN_PLAN.md): comments, version history, the share link
and signed-out viewing, follow + presence.

Server half (this file): a version carries a note and who made it, a version can become a NEW file, a comment
remembers its place inside its layer, the share link reads the comments (and only reads), switching the link off
shows its guests out while the editors stay, comments and share-link reads are rate limited, a database born
before the new columns heals itself, and uploaded images nothing draws any more are swept (never a fresh one,
never one a kept version still draws).

Browser half: server/tests/web/design_collab_test.js against a REAL server this file starts on a free port with a
fresh database - two signed-in editors and one signed-out share-link visitor in one file. It skips cleanly where
node, playwright or Chromium is missing."""
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
from starlette.websockets import WebSocketDisconnect

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
JS_TEST = HERE / "web" / "design_collab_test.js"
DESIGN = SERVER / "app" / "static" / "console" / "design"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")
H = {"Authorization": "Bearer kd"}
PAGE = "0:1"


@pytest.fixture()
def design_env(env, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    from app.config import get_settings
    from app.design import limits
    get_settings.cache_clear()
    for window in (limits.COMMENTS, limits.SHARED_READS, limits.SHARED_IMAGES):
        window.reset()
    yield monkeypatch
    get_settings.cache_clear()
    for window in (limits.COMMENTS, limits.SHARED_READS, limits.SHARED_IMAGES):
        window.reset()


def client():
    from app.main import app
    return TestClient(app)


def other_tenant():
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


def take(sock, kind):
    for _ in range(50):
        frame = sock.receive_json()
        if frame["t"] == kind:
            return frame
    raise AssertionError(f"no {kind} frame")


def rect(nid, idx="V", **props):
    return {"id": nid, "p": {"type": "RECT", "parent": PAGE, "idx": idx, "name": "Rect", **props}}


def png(colour=(200, 30, 30)):
    import io

    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (4, 3), colour).save(buf, "PNG")
    return buf.getvalue()


# ------------------------------------------------------------------------------------------- versions
def test_a_version_keeps_its_note_and_who_made_it_and_can_become_a_new_file(design_env):
    with client() as c:
        fid = new_file(c, name="Poster")["id"]
        with c.websocket_connect(f"/api/design/ws?file={fid}", headers=H) as a:
            me = take(a, "init")["you"]["name"]
            a.send_json({"t": "ops", "n": 1, "ops": [rect("1:1", name="First")]})
            take(a, "ack")
            v = c.post(f"/api/design/files/{fid}/versions", headers=H,
                       json={"label": "Before the call", "note": "  Hero in   violet \n"}).json()
            assert (v["label"], v["note"], v["by"], v["auto"]) == ("Before the call", "Hero in violet", me, False)
            a.send_json({"t": "ops", "n": 2, "ops": [{"id": "1:1", "p": {"name": "Changed"}}, rect("1:2", idx="W")]})
            take(a, "ack")
        listed = c.get(f"/api/design/files/{fid}/versions", headers=H).json()["versions"]
        assert listed[0]["note"] == "Hero in violet" and listed[0]["by"] == me
        assert c.post(f"/api/design/files/{fid}/versions", headers=H).json()["note"] == ""          # no body still works

        made = c.post(f"/api/design/versions/{v['id']}/duplicate", headers=H)
        assert made.status_code == 200, made.text
        copy = made.json()
        assert copy["id"] != fid and copy["name"] == "Poster (Before the call)" and copy["nodes"] == 3
        nodes = c.get(f"/api/design/files/{copy['id']}/doc", headers=H).json()["doc"]["nodes"]
        assert nodes["1:1"]["name"] == "First" and "1:2" not in nodes                              # the version, not the file
        live = c.get(f"/api/design/files/{fid}/doc", headers=H).json()["doc"]["nodes"]
        assert live["1:1"]["name"] == "Changed" and "1:2" in live                                  # the source is untouched
        named = c.post(f"/api/design/versions/{v['id']}/duplicate", headers=H, json={"name": "Client copy"}).json()
        assert named["name"] == "Client copy"
        # the copy never hands out a client number the copied nodes were minted under
        with c.websocket_connect(f"/api/design/ws?file={copy['id']}", headers=H) as b:
            assert take(b, "init")["cid"] >= 2
        assert c.post("/api/design/versions/dv_nope/duplicate", headers=H).status_code == 404
        assert c.post(f"/api/design/versions/{v['id']}/duplicate", headers=other_tenant()).status_code == 404
        assert c.post(f"/api/design/versions/{v['id']}/duplicate").status_code == 401


def test_an_automatic_version_names_the_last_editor(design_env):
    from app.design import store
    from app.design.doc import dumps_nodes, new_document
    with client() as c:
        fid = new_file(c)["id"]
    blob = store.pack(dumps_nodes(new_document()))
    store.save_snapshot(fid, blob, 1, 2, 0.0001, 5, "Asha")
    time.sleep(0.002)
    store.save_snapshot(fid, blob, 2, 2, 0.0001, 5)                                                # the old call shape
    got = store.list_versions("default", fid)
    assert [(v["auto"], v["by"]) for v in got] == [(True, ""), (True, "Asha")]
    from app.design import room
    src = Path(room.__file__).read_text(encoding="utf-8")
    assert "self._last_by = conn.name" in src and "self._keep, self._last_by)" in src             # the room passes it on


# ------------------------------------------------------------------------------------------- comments
def test_a_comment_remembers_its_place_inside_its_layer(design_env):
    with client() as c:
        fid = new_file(c)["id"]
        base = f"/api/design/files/{fid}/comments"
        a = c.post(base, headers=H, json={"text": "Bigger", "x": 120, "y": 40, "page": PAGE, "node": "1:1", "ox": 12.5, "oy": 8}).json()
        assert (a["node"], a["ox"], a["oy"], a["x"], a["y"]) == ("1:1", 12.5, 8, 120, 40) and a["author"]
        b = c.post(base, headers=H, json={"text": "On the page", "x": 5, "y": 6, "page": PAGE, "ox": 1, "oy": 2}).json()
        assert (b["node"], b["ox"], b["oy"]) == (None, None, None)                                 # no layer, no place inside one
        huge = c.post(base, headers={**H, "Content-Type": "application/json"}, content='{"text":"x","x":1,"y":1,"node":"1:1","ox":1e999}')
        assert huge.status_code in (400, 422)                                                       # not a number a pin can sit on
        rows = c.get(base, headers=H).json()["comments"]
        assert [(r["ox"], r["oy"]) for r in rows] == [(12.5, 8), (None, None)]


def test_the_share_link_reads_comments_and_only_reads(design_env):
    with client() as c:
        fid = new_file(c, name="Shared")["id"]
        base = f"/api/design/files/{fid}/comments"
        a = c.post(base, headers=H, json={"text": "First", "x": 1, "y": 2, "page": PAGE}).json()
        c.post(base, headers=H, json={"text": "Reply", "parent": a["id"]})
        token = c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "view"}).json()["token"]
        got = c.get(f"/api/design/shared/{token}/comments")                                         # no key at all
        assert got.status_code == 200 and [x["text"] for x in got.json()["comments"]] == ["First", "Reply"]
        for method in ("post", "put", "patch", "delete"):
            assert getattr(c, method)(f"/api/design/shared/{token}/comments").status_code == 405
        assert c.patch(f"/api/design/comments/{a['id']}", json={"resolved": True}).status_code == 401
        assert c.get("/api/design/shared/nope/comments").status_code == 404
        c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "none"})
        assert c.get(f"/api/design/shared/{token}/comments").status_code == 404


def test_comments_and_share_reads_are_rate_limited(design_env):
    from app.design import limits
    with client() as c:
        fid = new_file(c)["id"]
        base = f"/api/design/files/{fid}/comments"
        first = c.post(base, headers=H, json={"text": "0", "x": 0, "y": 0}).json()
        for i in range(1, 30):
            assert c.post(base, headers=H, json={"text": str(i), "x": 0, "y": 0}).status_code == 200
        over = c.post(base, headers=H, json={"text": "too many", "x": 0, "y": 0})
        assert over.status_code == 429 and "wait" in over.json()["detail"] and over.headers["retry-after"] == "60"
        assert c.patch(f"/api/design/comments/{first['id']}", headers=H, json={"text": "edited"}).status_code == 429
        assert c.patch(f"/api/design/comments/{first['id']}", headers=H, json={"resolved": True}).status_code == 200   # resolving is not writing
        assert len(c.get(base, headers=H).json()["comments"]) == 30
        other = other_tenant()                                                                      # one person's limit is not another's
        mine = c.post("/api/design/files", headers=other, json={}).json()["id"]
        assert c.post(f"/api/design/files/{mine}/comments", headers=other, json={"text": "hi", "x": 0, "y": 0}).status_code == 200

        token = c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "view"}).json()["token"]
        codes = [c.get(f"/api/design/shared/{token}/doc").status_code for _ in range(limits.SHARED_READS.limit)]
        assert set(codes) == {200}
        assert c.get(f"/api/design/shared/{token}/doc").status_code == 429
        assert c.get(f"/api/design/shared/{token}/comments").status_code == 429                     # the same budget
        assert c.get(f"/api/design/shared/{token}/doc", headers={"X-Real-IP": "203.0.113.9"}).status_code == 200      # another reader
        assert c.get(f"/api/design/files/{fid}/doc", headers=H).status_code == 200                  # the owner is never limited by it
    w = limits.Window(2, 10.0)
    assert [w.allow("k", t) for t in (0.0, 1.0, 2.0, 10.5, 11.5, 11.6)] == [True, True, False, True, True, False]


# ---------------------------------------------------------------------------------------------- share
def test_switching_the_link_off_shows_the_guests_out_and_keeps_the_editors(design_env):
    with client() as c:
        fid = new_file(c)["id"]
        token = c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "view"}).json()["token"]
        with c.websocket_connect(f"/api/design/ws?file={fid}", headers=H) as editor:
            take(editor, "init")
            with c.websocket_connect(f"/api/design/ws?share={token}") as guest:
                init = take(guest, "init")
                assert init["file"]["role"] == "view" and init["you"]["name"] == "Guest"
                assert take(editor, "join")["user"]["name"] == "Guest"
                guest.send_json({"t": "pres", "x": 1, "y": 2, "vp": [0, 0, 1], "vs": [800, 600], "chat": "hello", "spot": 7})
                seen = take(editor, "pres")                                                         # the extra presence fields travel
                assert (seen["vs"], seen["chat"], seen["spot"], seen["cid"]) == ([800, 600], "hello", 7, init["cid"])
                assert c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "none"}).json()["token"] is None
                with pytest.raises(WebSocketDisconnect) as gone:
                    for _ in range(20):
                        guest.receive_json()
                assert gone.value.code == 4404
            assert take(editor, "leave")["cid"] == init["cid"]
            editor.send_json({"t": "ops", "n": 1, "ops": [rect("1:1")]})                            # the editor is still in
            assert take(editor, "ack")["rejected"] == []
        with pytest.raises(WebSocketDisconnect) as refused:                                         # and the old link opens no socket
            with c.websocket_connect(f"/api/design/ws?share={token}") as late:
                late.receive_json()
        assert refused.value.code == 4404


# ---------------------------------------------------------------------------------------- old databases
def test_a_database_born_before_the_new_columns_heals_itself(design_env):
    from sqlalchemy import inspect, text

    from app import db
    from app.design import models, store
    with client() as c:
        fid = new_file(c)["id"]
        c.post(f"/api/design/files/{fid}/versions", headers=H, json={"label": "Old"})
    with db._engine.begin() as conn:
        conn.execute(text("ALTER TABLE design_versions DROP COLUMN note"))
        conn.execute(text("ALTER TABLE design_comments DROP COLUMN ox"))
        conn.execute(text("ALTER TABLE design_comments DROP COLUMN oy"))
    models._ready_for = None
    assert [v["note"] for v in store.list_versions("default", fid)] == [""]                         # healed on first use
    cols = {col["name"] for col in inspect(db._engine).get_columns("design_comments")}
    assert {"ox", "oy"} <= cols
    assert store.add_comment("default", fid, "Me", "hi", "1:1", PAGE, 1, 2, None, 3.0, 4.0)["ox"] == 3.0


# ------------------------------------------------------------------------------------------ image sweep
def test_images_nothing_draws_are_swept_but_never_a_fresh_or_a_kept_one(design_env, tmp_path):
    from app.design import assets
    paint = lambda sha: [{"type": "image", "hash": sha, "mode": "fill", "opacity": 1, "visible": True}]   # noqa: E731
    with client() as c:
        fid = new_file(c)["id"]
        up = lambda colour: c.post(f"/api/design/files/{fid}/assets", headers=H, content=png(colour)).json()["hash"]   # noqa: E731
        in_doc, in_version, in_journal, loose, fresh, trashed = (up((i * 40, 10, 10)) for i in range(6))
        with c.websocket_connect(f"/api/design/ws?file={fid}", headers=H) as a:
            take(a, "init")
            a.send_json({"t": "ops", "n": 1, "ops": [rect("1:1", fills=paint(in_doc)), rect("1:2", idx="W", fills=paint(in_version))]})
            take(a, "ack")
            c.post(f"/api/design/files/{fid}/versions", headers=H, json={"label": "Keeps the second picture"})
            a.send_json({"t": "ops", "n": 2, "ops": [{"id": "1:2", "del": 1}]})
            take(a, "ack")
        other = new_file(c, name="In the trash")["id"]
        with c.websocket_connect(f"/api/design/ws?file={other}", headers=H) as b:
            take(b, "init")
            b.send_json({"t": "ops", "n": 1, "ops": [rect("1:1", fills=paint(trashed))]})
            take(b, "ack")
        c.delete(f"/api/design/files/{other}", headers=H)
        # a third file whose only reference is still in the journal (no checkpoint yet): read it through the store
        from app.db import now
        from app.design import store
        third = new_file(c, name="Journal only")["id"]
        store.append_ops(third, [(1, 1, json.dumps([rect("1:1", fills=paint(in_journal))]), now())])

        folder = tmp_path / "design" / "default" / "assets"
        old = time.time() - 30 * 86400
        for sha in (in_doc, in_version, in_journal, loose, trashed):
            os.utime(folder / sha, (old, old))
        (folder / ".half.tmp").write_bytes(b"x")                                                    # not one of ours: left alone
        os.utime(folder / ".half.tmp", (old, old))
        assert assets.sweep(7) == {"checked": 6, "deleted": 1, "bytes": len(png((120, 10, 10)))}
        left = {p.name for p in folder.iterdir()}
        assert left == {in_doc, in_version, in_journal, fresh, trashed, ".half.tmp"} and loose not in left
        assert c.get(f"/api/design/assets/{loose}", headers=H).status_code == 404
        assert c.get(f"/api/design/assets/{in_version}", headers=H).status_code == 200               # a kept version still draws it
        assert assets.sweep(7)["deleted"] == 0                                                      # nothing more to take

        # uploaded again = fresh again: the sweep leaves it for another week
        os.utime(folder / fresh, (old, old))
        assert up((160, 10, 10)) == fresh and (folder / fresh).stat().st_mtime > time.time() - 60
        assert assets.sweep(7)["deleted"] == 0
        os.utime(folder / fresh, (old, old))
        assert assets.sweep(60)["deleted"] == 0 and assets.sweep(7)["deleted"] == 1                 # the age is the caller's
        # the other person's pictures are judged by their own documents only
        theirs = other_tenant()
        f2 = c.post("/api/design/files", headers=theirs, json={}).json()["id"]
        sha2 = c.post(f"/api/design/files/{f2}/assets", headers=theirs, content=png((1, 2, 3))).json()["hash"]
        their_folder = next(p for p in (tmp_path / "design").iterdir() if p.name != "default") / "assets"
        os.utime(their_folder / sha2, (old, old))
        assert assets.sweep(7)["deleted"] == 1 and not (their_folder / sha2).exists()


def test_the_sweep_is_a_guarded_worker_slot(design_env):
    import asyncio

    from app import worker
    from app.design import assets
    src = Path(worker.__file__).read_text(encoding="utf-8")
    assert "api_box_jobs, design_asset_jobs," in src                                                # it runs through _slot like the rest
    calls = []
    design_env.setattr(assets, "sweep", lambda days: calls.append(days) or {"checked": 0, "deleted": 0, "bytes": 0})
    design_env.setattr(worker, "_design_gc_last", 0.0)
    asyncio.run(worker.design_asset_jobs())                                                         # the first tick only arms it
    assert calls == [] and worker._design_gc_last > 0
    asyncio.run(worker.design_asset_jobs())
    assert calls == []                                                                              # not yet: 15 minutes after a start
    design_env.setattr(worker, "_design_gc_last", time.time() - 86401)
    asyncio.run(worker.design_asset_jobs())
    asyncio.run(worker.design_asset_jobs())
    assert calls == [7.0]                                                                           # once a day, the 7-day rule
    design_env.setenv("DESIGN_PAGE", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    design_env.setattr(worker, "_design_gc_last", time.time() - 86401)
    asyncio.run(worker.design_asset_jobs())
    assert calls == [7.0]                                                                           # switched off = no sweep


# ------------------------------------------------------------------------------------------- the client
def test_the_client_files_are_plain_strict_scripts_that_never_build_html_from_text():
    collab = (DESIGN / "hd-collab.js").read_text(encoding="utf-8")
    assert "'use strict';" in collab and collab.rstrip().endswith("})();") and collab.isascii()
    for name in ("hd-collab.js", "hd-net.js", "hd-app.js"):
        text = (DESIGN / name).read_text(encoding="utf-8")
        for banned in ("eval(", "new Function", "innerHTML", "insertAdjacentHTML", "document.write", "outerHTML"):
            assert banned not in text, (name, banned)
    # the four hooks + the panels are plugged in through HD.ui, and the preview is guarded by the net's hold
    for needle in ("ui.hook('comment', startDraft)", "ui.hook('versions', openVersions)", "ui.hook('share', shareDialog)",
                   "ui.registerPanel('left', 'comments'", "N().hold()", "N().release()", "/shared/"):
        assert needle in collab, needle
    net = (DESIGN / "hd-net.js").read_text(encoding="utf-8")
    assert "if (held) return;" in net and "'/api/design/ws?share=' + encodeURIComponent(shareToken)" in net
    assert "shareToken ? ['hoola'] : ['hoola', 'hoola-key.' + tk]" in net                           # a guest sends no key at all
    app = (DESIGN / "hd-app.js").read_text(encoding="utf-8")
    assert "SHARE_RE" in app and "/api/design/shared/" in app and "sharedProblem(" in app
    html = (DESIGN / "design.html").read_text(encoding="utf-8")
    order = [html.index(f"design/{n}") for n in ("hd-ui.js", "hd-collab.js", "hd-app.js")]
    assert order == sorted(order)


@needs_node
def test_the_client_files_parse():
    for name in ("hd-collab.js", "hd-net.js", "hd-app.js", "../../../../tests/web/design_collab_test.js"):
        run = subprocess.run([NODE, "--check", str((DESIGN / name).resolve())], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@needs_node
def test_two_editors_and_a_share_link_visitor_in_a_real_browser(tmp_path):
    """The real server (uvicorn, a fresh SQLite database in the test folder) + three real browsers."""
    port, key = _free_port(), "collab-test-key"
    env = os.environ.copy()
    env.update({"DATABASE_URL": f"sqlite:///{tmp_path}/collab.db", "API_KEY": key, "WA_DRY_RUN": "true", "ANTHROPIC_API_KEY": "test",
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
            jenv["HOOLA_CHROMIUM"] = SANDBOX_CHROME                  # the same fallback the other browser walks use
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
    assert report["ok"] is True and report["checks"] >= 60, report
    assert re.search(r"design_collab_test", str(JS_TEST))
