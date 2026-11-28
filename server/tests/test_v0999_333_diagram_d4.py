"""HOOLA DIAGRAM D4 (docs/DIAGRAM_TOOL_PLAN.md): the diagram tool inside Hoola Code. A diagram of her code is drawn
from files Hoola has READ in this session (refused otherwise), lands as a checked card in "Made in this session" with
those files on it (never in her chat, never in the repo); archify's Code Analysis runs on the working copy; the PR
walkthrough compares where the session started with the working copy now on a snapshot commit that never moves her
branch. Real working copy, real tools, real engines - only the model is scripted."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.devsahayak import diagrams as DG
from app.devsahayak import engine as EN
from app.devsahayak import made as MD
from app.diagram import runners as R
from app.diagram import service as S
from app.diagram import vendor as V
from tests.test_tech_devsahayak import dev  # noqa: F401
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

T = "t-d4"
FILES = {
    "package.json": '{"name": "shop", "version": "1.0.0"}\n',
    "src/auth/login.ts": ('import { findUser } from "../db/users";\nimport { hash } from "./hash";\n'
                          'export function login(name: string, pw: string): boolean {\n  const u = findUser(name);\n'
                          '  if (!u) return false;\n  return u.pw === hash(pw);\n}\n'),
    "src/auth/hash.ts": "export function hash(s: string): string { return String(s.length * 31); }\n",
    "src/db/users.ts": ('import { login } from "../auth/login";\n'
                        'export function findUser(n: string) { return n === "a" ? { pw: "1" } : null; }\n'
                        'export const again = () => login("a", "b");\n'),
}
NODE = bool(R.node_bin())


def _arch() -> dict:
    """archify's own example architecture, with its demo sources taken out (we add OUR files)."""
    d = json.loads((V.ARCHIFY / "examples" / "checkout-ledger.architecture.json").read_text())
    d["meta"]["title"] = "Login flow"
    return d


@pytest.fixture()
def ws(env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from app.events import bus
    monkeypatch.setattr(bus, "publish", lambda *a, **k: None)
    tid = f"d4-{tmp_path.name[-8:]}"
    EN.LOCAL_FILES[tid] = dict(FILES)
    ses = EN.Session(tid)
    ses.ensure("meghana/shop", "a" * 40, "")
    tools = EN.Tools(ses, allow_workflows=False, lab_spec={})
    yield tid, ses, tools
    EN.LOCAL_FILES.pop(tid, None)


# ------------------------------------------------------------------ the session's made list holds engine-built pages
def test_built_kinds_are_cards_with_versions_and_never_written_by_make(env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert MD.TOOL["input_schema"]["properties"]["kind"]["enum"] == ["doc", "page", "prototype", "artboard", "sheet"]
    assert "kind" in MD.tool("t9", {"action": "start", "kind": "diagram", "title": "x"})[0].lower()   # refused, said
    assert MD._kind("diagram") == "" and MD._kind("prd") == "doc"          # make cannot start a built kind
    r1 = MD.keep_built("t9", "diagram", "Login flow", "<html>v1</html>", {"line": "Diagram · Architecture"},
                       extra={"tenant": "secret-tenant", "diagram_id": "dg-1", "files": ["src/auth/login.ts"]})
    r2 = MD.keep_built("t9", "diagram", "Login flow", "<html>v2</html>", {"line": "fixed"}, mid=r1["id"],
                       extra={"tenant": "secret-tenant", "diagram_id": "dg-1", "files": ["src/auth/login.ts"]})
    assert r2["id"] == r1["id"] and r2["version"] == 2 and r2["kind_label"] == "Diagram"
    rows = MD.listing("t9")
    assert len(rows) == 1 and rows[0]["extra"]["files"] == ["src/auth/login.ts"]
    assert "tenant" not in json.dumps(rows) and "secret-tenant" not in json.dumps(rows)   # never on the card
    d = MD.detail("t9", r1["id"])
    assert d["shown"] == 2 and "/api/devsahayak/made/t9/" in d["url"] and "editor" not in d
    body, ctype, head = MD.open_file("t9", r1["id"], 2, "out.html", *_exp_sig(d["url"]))
    assert body == b"<html>v2</html>" and "sandbox" in head["Content-Security-Policy"]
    back = MD.restore("t9", r1["id"], 1)
    assert back["version"] == 3 and MD.open_file("t9", r1["id"], 3, "out.html", *_exp_sig(MD.detail("t9", r1["id"])["url"]))[0] == b"<html>v1</html>"


def _exp_sig(url: str) -> tuple[int, str]:
    from urllib.parse import parse_qs, urlparse
    q = parse_qs(urlparse(url).query)
    return int(q["exp"][0]), q["sig"][0]


# ------------------------------------------------------------------ read the code first
def test_a_diagram_of_her_code_is_refused_until_the_files_are_read(ws):
    tid, ses, tools = ws
    out, pic, ev = DG.tool(tools, tid, "default", {"action": "draw", "type": "architecture", "content": _arch()})
    assert "Read the code first" in out and pic is None and ev is None             # no files named at all
    out, _, _ = DG.tool(tools, tid, "default", {"action": "draw", "type": "architecture", "content": _arch(),
                                                "files": ["src/auth/login.ts"]})
    assert out.startswith("Not drawn: read these files first") and "src/auth/login.ts" in out
    a = _arch()
    a["components"][0]["sources"] = [{"path": "src/db/users.ts", "line": 1}]
    tools.t_read("src/auth/login.ts")
    out, _, _ = DG.tool(tools, tid, "default", {"action": "draw", "type": "architecture", "content": a,
                                                "files": ["src/auth/login.ts"]})
    assert "src/db/users.ts" in out and out.startswith("Not drawn")                # archify's own sources count too
    out, _, _ = DG.tool(tools, tid, "default", {"action": "draw", "type": "architecture", "content": _arch(),
                                                "files": ["../../etc/passwd", "src/nope.ts"]})
    assert out.startswith("Not drawn")                                             # outside the copy / not a file
    assert not MD.listing(tid)                                                     # nothing was kept


@pytest.mark.skipif(not NODE, reason="needs node for archify")
def test_login_flow_diagram_becomes_a_checked_card_linked_to_the_files(ws):
    tid, ses, tools = ws
    for f in ("src/auth/login.ts", "src/db/users.ts"):
        tools.t_read(f)
    before = sorted(p.relative_to(ses.repo).as_posix() for p in ses.repo.rglob("*") if ".git" not in p.parts)
    a = _arch()
    a["components"][1]["sources"] = [{"path": "src/auth/login.ts", "line": 3}]
    out, pic, ev = DG.tool(tools, tid, "default", {"action": "draw", "type": "architecture", "title": "Login flow",
                                                   "content": a, "files": ["src/auth/login.ts", "src/db/users.ts"]})
    r = json.loads(out.split("\nThe picture")[0])
    assert r["ok"] and r["made_id"] and "artifact_id" not in r, json.dumps(r)[:1500]   # a session card, not a chat page
    assert pic and pic["type"] == "image" and pic["source"]["media_type"] == "image/jpeg"   # the model looks at it
    assert r["source_check"], r                                                    # archify checked the cited lines
    assert ev == {"k": "made", "id": r["made_id"], "v": 1, "kind": "diagram", "title": "Login flow"}
    row = MD.listing(tid)[0]
    assert row["kind"] == "diagram" and row["extra"]["files"] == ["src/auth/login.ts", "src/db/users.ts"]
    assert row["extra"]["engine"] == "archify" and row["extra"]["diagram_id"] == r["diagram_id"]
    d = MD.detail(tid, row["id"])
    assert d["url"] and b"<html" in MD.open_file(tid, row["id"], 1, "out.html", *_exp_sig(d["url"]))[0][:400].lower()
    assert S.listing("default") == []                                              # not in her chat's diagrams
    from app.db import session
    from app.db import Artifact
    with session() as db:
        assert db.query(Artifact).count() == 0                                     # no page in her chat's library
    after = sorted(p.relative_to(ses.repo).as_posix() for p in ses.repo.rglob("*") if ".git" not in p.parts)
    assert after == before and not ses.changed()                                    # nothing written into her repo
    # a fix round keeps the same card: version 2
    out2, _, _ = DG.tool(tools, tid, "default", {"action": "update", "diagram_id": r["diagram_id"],
                                                 "edits": [{"old_str": '"Edge Gateway"', "new_str": '"Web app"'}]})
    assert json.loads(out2.split("\nThe picture")[0])["version"] == 2 and MD.listing(tid)[0]["version"] == 2
    # another session cannot touch it
    other = f"{tid}-x"
    assert "No diagram" in DG.tool(tools, other, "default", {"action": "read", "diagram_id": r["diagram_id"]})[0]


@pytest.mark.skipif(not NODE, reason="needs node for archify")
def test_a_cited_line_that_is_not_in_the_file_is_sent_back(ws):
    tid, ses, tools = ws
    tools.t_read("src/auth/hash.ts")                                              # one line long
    a = _arch()
    a["components"][1]["sources"] = [{"path": "src/auth/hash.ts", "line": 40}]
    out, pic, _ = DG.tool(tools, tid, "default", {"action": "draw", "type": "architecture", "content": a,
                                                  "files": ["src/auth/hash.ts"]})
    r = json.loads(out)
    assert r["ok"] is False and r["problems"] and pic is None and not MD.listing(tid), r


# ------------------------------------------------------------------ Code Analysis + PR walkthrough
@pytest.mark.skipif(not NODE, reason="needs node for archify")
def test_code_analysis_runs_on_the_working_copy_and_finds_the_cycle(ws):
    tid, ses, tools = ws
    out, pic, ev = DG.tool(tools, tid, "default", {"action": "analyze"})
    r = json.loads(out)
    assert r["ok"] and r["language"] == "ts" and r["files"] == 3, r
    assert any(x["code"] == "coupling/cycle" and "src/auth" in x["message"] for x in r["leads"])
    assert "coupling/import-cycle" in r["rules_run"] and "resume" not in out and str(ses.repo) not in out
    assert ev["kind"] == "analysis" and pic is None
    row = next(x for x in MD.listing(tid) if x["kind"] == "analysis")
    assert row["kind_label"] == "Code analysis" and row["extra"]["counts"]["error"] >= 1
    d = MD.detail(tid, row["id"])
    page = MD.open_file(tid, row["id"], 1, "out.html", *_exp_sig(d["url"]))[0]
    assert len(page) > 100_000 and b"<script" in page                              # archify's full workbench
    assert str(ses.repo.resolve()).encode() not in page and str(Path("data").resolve()).encode() not in page
    again = json.loads(DG.tool(tools, tid, "default", {"action": "analyze"})[0])
    assert again["card"] == row["id"] and again["version"] == 2                     # a re-run is a new version
    assert "No folder" in DG.tool(tools, tid, "default", {"action": "analyze", "scope": "../../"})[0]
    assert not list(MD._tdir(tid).parent.glob("_work/hoola-ca-*"))                 # scratch output cleaned up


@pytest.mark.skipif(not NODE, reason="needs node for archify")
def test_pr_walkthrough_compares_the_start_with_now_and_never_moves_her_branch(ws):
    tid, ses, tools = ws
    assert "Nothing has changed" in DG.tool(tools, tid, "default", {"action": "pr"})[0]
    tools.t_read("src/auth/login.ts")
    assert tools.t_edit("src/auth/login.ts", "  if (!u) return false;\n",
                        "  if (!u) return false;\n  if (pw.length > 64) return false;\n").startswith("Edited")
    assert tools.t_write("src/auth/session.ts", 'import { login } from "./login";\nexport const start = (n: string, p: string) => login(n, p);\n').startswith("Created")
    ses.changed()                                                                 # the engine's own diff stages, as always
    head0 = subprocess.run(["git", "-C", str(ses.repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
    status0 = subprocess.run(["git", "-C", str(ses.repo), "status", "--porcelain"], capture_output=True, text=True).stdout
    out, _, ev = DG.tool(tools, tid, "default", {"action": "pr"})
    r = json.loads(out)
    assert r["ok"] and set(r["changed_files"]) == {"src/auth/login.ts", "src/auth/session.ts"}, r
    assert ev["kind"] == "review"
    head1 = subprocess.run(["git", "-C", str(ses.repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
    status1 = subprocess.run(["git", "-C", str(ses.repo), "status", "--porcelain"], capture_output=True, text=True).stdout
    assert head1 == head0 and status1 == status0                                   # her branch and index untouched
    row = next(x for x in MD.listing(tid) if x["kind"] == "review")
    assert row["kind_label"] == "PR walkthrough" and row["extra"]["base"] == ses.meta["base"][:12]
    assert {c["path"] for c in ses.changed()} == {"src/auth/login.ts", "src/auth/session.ts"}   # the change is still hers


def test_snapshot_is_a_commit_of_the_working_tree(ws):
    tid, ses, tools = ws
    (ses.repo / "src" / "new.ts").write_text("export const x = 1;\n")
    sha = DG.snapshot(ses.repo)
    assert len(sha) == 40
    files = subprocess.run(["git", "-C", str(ses.repo), "ls-tree", "-r", "--name-only", sha], capture_output=True,
                           text=True).stdout.split()
    assert "src/new.ts" in files
    log = subprocess.run(["git", "-C", str(ses.repo), "log", "--format=%H"], capture_output=True, text=True).stdout
    assert sha not in log                                                         # not on her branch


def test_the_language_is_the_repos_main_one_and_missing_toolchains_are_said(ws, monkeypatch):
    tid, ses, tools = ws
    assert DG._language(ses.repo, "", "")[0] == "ts"
    monkeypatch.setattr(DG.shutil, "which", lambda x: None)
    assert "needs go" in DG._language(ses.repo, "", "go")[1]
    assert "must be one of" in DG._language(ses.repo, "", "cobol")[1]


# ------------------------------------------------------------------ an editable diagram in a session
def test_an_editable_diagram_stays_in_the_session_and_her_edits_become_its_versions(ws, monkeypatch):
    tid, ses, tools = ws
    from app.diagram import drawio as DR
    from app.diagram import live as L
    monkeypatch.setattr(DR, "ready", lambda: True)

    def export(xml, out, fmt="png"):
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        if fmt == "png":
            Path(out).write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
        else:
            Path(out).write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>x</text></svg>')
        return {"ok": True, "file": str(out), "png": str(out)}
    monkeypatch.setattr(R, "drawio_export", export)
    tools.t_read("src/auth/login.ts")
    cells = ('<mxCell id="a" value="login()" vertex="1" parent="1"><mxGeometry x="40" y="40" width="120" height="50" '
             'as="geometry"/></mxCell>')
    out, _, ev = DG.tool(tools, tid, "default", {"action": "draw", "type": "drawio", "title": "Login", "content": cells,
                                                 "files": ["src/auth/login.ts"]})
    r = json.loads(out.split("\nThe picture")[0])
    assert r["ok"] and "editor" not in r and "/diagram-edit/" not in out           # her link is on the card only
    d = MD.detail(tid, r["made_id"], base_url="https://h.example")
    assert d["editor"].startswith("https://h.example/diagram-edit/") and d["extra"]["editor_ready"]
    st = L.state("default", r["diagram_id"])
    moved = st["xml"].replace('x="40"', 'x="90"')
    assert L.save("default", r["diagram_id"], moved, '<svg xmlns="http://www.w3.org/2000/svg"/>', st["rev"])["changed"]
    assert MD.listing(tid)[0]["version"] == 2                                       # her edit = the card's new version
    with pytest.raises(ValueError):
        MD.restore(tid, r["made_id"], 1)                                            # it goes back in its editor


# ------------------------------------------------------------------ the engine, the web page, the phone
def test_the_coding_loop_offers_it_and_reads_the_rule():
    names = [t["name"] for t in EN.tools_for_round()]
    assert "diagram" in names and names.count("diagram") == 1
    src = Path(EN.__file__).read_text()
    assert 'b["name"] == "diagram"' in src and "DG.HOWTO" in src and "dg_pics" in src
    assert "READ THE CODE FIRST" in DG.TOOL["description"] and "never run her code" in DG.TOOL["description"]
    assert set(DG.TOOL["input_schema"]["properties"]["action"]["enum"]) >= {"draw", "analyze", "pr", "read", "change"}


def test_web_and_phone_show_the_cards():
    root = Path(__file__).resolve().parents[2]
    js = (root / "server/app/static/console/code.js").read_text()
    assert "function madeCard" in js and "async function openMade" in js and "Made in this session" in js
    assert 'sandbox="allow-scripts allow-popups allow-downloads"' in js and "Edit by hand" in js and "Drawn from" in js
    assert "Ran Code Analysis" in js and "Wrote the PR walkthrough" in js
    dart = (root / "lib/ui/code/code_made.dart").read_text()
    assert "'diagram'" in dart and "'Diagrams'" in dart and "Drawn from" in dart and "'analysis', 'review'" in dart
    css = (root / "server/app/static/console/hoolacode.css").read_text()
    assert ".hcd-dlg.hcd-dlgw" in css and ".hcd-madeframe" in css


# ------------------------------------------------------------------ the web page, in a real browser
def test_web_rail_card_opens_full_screen_and_edit_by_hand_swaps_in_the_editor(arena_server):  # noqa: F811
    from tests import test_v0768_hoola_code_shell as SH
    made = [{"id": "login-flow", "kind": "diagram", "kind_label": "Diagram", "title": "Login flow", "version": 2,
             "ready_version": 2, "state": "ready", "parts": [{"name": "Diagram", "done": True}], "line": "Diagram · Architecture",
             "extra": {"files": ["src/auth/login.ts", "src/db/users.ts"], "diagram_id": "dg-1", "editable": True,
                       "editor_ready": True}},
            {"id": "code-analysis", "kind": "analysis", "kind_label": "Code analysis", "title": "Code analysis", "version": 1,
             "ready_version": 1, "state": "ready", "parts": [], "line": "3 files (ts) · 2 errors, 0 warnings, 0 notes",
             "extra": {"counts": {"error": 2}}}]
    done = {**SH.DONE, "made": made}
    detail = {**made[0], "shown": 2, "shown_state": "ready", "url": "/api/devsahayak/made/dt3/login-flow/2/out.html?exp=9&sig=s",
              "editor": "/diagram-edit/tok-1", "versions": [{"v": 2, "state": "ready", "note": "fixed"},
                                                             {"v": 1, "state": "ready", "note": ""}]}
    ctx, pg, errs, calls, state = SH._console(arena_server)
    seen = []
    pg.route("**/api/devsahayak/tasks/dt3", lambda r: r.fulfill(json=done))
    pg.route("**/api/devsahayak/tasks/dt3/made/*", lambda r: (seen.append(r.request.url), r.fulfill(json=detail))[1])
    pg.route("**/api/devsahayak/made/**", lambda r: r.fulfill(body="<html><body><h1 id=pic>DIAGRAM PAGE</h1></body></html>",
                                                              content_type="text/html"))
    pg.route("**/diagram-edit/tok-1*", lambda r: r.fulfill(body="<html><body><h1 id=ed>EDITOR</h1></body></html>",
                                                           content_type="text/html"))
    pg.locator("[data-tid='dt3']").first.click()
    card = pg.locator(".hcd-madec")
    card.wait_for(timeout=15000)
    assert "Made in this session" in card.inner_text() and "Drawn from" in card.inner_text()
    assert pg.locator(".hcd-made").count() == 2
    pg.locator(".hcd-made[data-mid='login-flow']").click()
    dlg = pg.locator("#hcdDlg.hcd-dlgw")
    dlg.wait_for(timeout=10000)
    box = dlg.bounding_box()
    assert box["width"] > 900 and box["height"] > 600                              # full screen, not the small dialog
    frame = pg.locator(".hcd-madeframe")
    assert "allow-same-origin" not in (frame.get_attribute("sandbox") or "")
    assert "src/auth/login.ts" in dlg.inner_text() and pg.locator(".hcd-madev option").count() == 2
    pg.frame_locator(".hcd-madeframe").locator("#pic").wait_for(timeout=10000)
    dlg.get_by_role("button", name="Edit by hand").click()
    pg.frame_locator(".hcd-madeframe").locator("#ed").wait_for(timeout=10000)      # her editor in the same place
    assert "/diagram-edit/tok-1?lang=" in frame.get_attribute("src")
    pg.keyboard.press("Escape")
    pg.wait_for_function("() => !document.querySelector('#hcdDlg').open && !document.querySelector('#hcdDlg').classList.contains('hcd-dlgw')")
    errs = [e for e in errs if "lacks the 'allow-same-origin'" not in e]          # the harness's own token script in a sandbox
    assert not pg.locator("#hcdDlg.hcd-dlgw").count() and seen and not errs, errs
    ctx.close()
