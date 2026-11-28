"""v0.999 FIVE FROM OPENCODE (owner, after reading anomalyco/opencode: 'GO 1 TO 5'):
(1) edits that survive small differences (typographic quotes / dashes / odd spaces, trailing spaces) and, on a miss, say
    why and show the closest lines; (2) a command still running at its time limit keeps running in the background
    instead of being killed; (3) tool inputs fixed only where the tool's own fields leave one reading - which also fixes
    a live bug: writing a .json file saved a Python dict; (4) the repo's own declared formatter runs on what a reply
    changed (real ruff / gofmt here), a whole-file rewrite is put back; (5) redo after going back to a checkpoint."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ses(tmp_path, monkeypatch):
    from app.devsahayak import engine as EN
    monkeypatch.setattr(EN, "root", lambda: tmp_path / "ws")
    EN.PERMIT.clear()
    s = EN.Session("t1")
    s.repo.mkdir(parents=True)
    (s.repo / "app.py").write_text('def greet(name):\n    msg = "It\u2019s ready \u2014 go"   \n    return msg\n')
    EN._git(s.repo, "init", "-q")
    s.meta.update({"repo": "o/r", "base": EN._commit(s.repo, "base"), "hidden": [], "checkpoints": []})
    s.save_meta()
    yield SimpleNamespace(EN=EN, s=s, tools=EN.Tools(s, False))


# ---------------------------------------------------------------- 1. tolerant edits + a useful miss
def test_edits_survive_quotes_dashes_and_trailing_spaces(ses):
    tl = ses.tools
    tl.run("read", {"path": "app.py"})
    out = tl.run("edit", {"path": "app.py", "old_string": 'msg = "It\'s ready - go"', "new_string": 'msg = "Ready"'})
    assert out.startswith("Edited app.py") and "matched ignoring quote / dash / space characters" in out
    assert '    msg = "Ready"   \n' in (ses.s.repo / "app.py").read_text()
    out = tl.run("edit", {"path": "app.py", "old_string": '    msg = "Ready"\n    return msg\n', "new_string": "    return 'Ready'\n"})
    assert "matched ignoring trailing spaces" in out and (ses.s.repo / "app.py").read_text() == "def greet(name):\n    return 'Ready'\n"


def test_a_miss_says_why_and_points_at_the_closest_lines(ses):
    tl = ses.tools
    tl.run("read", {"path": "app.py"})
    out = tl.run("edit", {"path": "app.py", "old_string": "    mesage = 1\n    return msg", "new_string": "x"})
    assert "The closest place in the file" in out and "     3\t    return msg" in out
    out = tl.run("edit", {"path": "app.py", "old_string": "nothing like it", "new_string": "return msg"})
    assert "already in the file" in out
    (ses.s.repo / "b.py").write_text("x = 1\nx = 1\n")
    tl.run("read", {"path": "b.py"})
    assert "appears 2 times" in tl.run("edit", {"path": "b.py", "old_string": "x = 1", "new_string": "y"})


# ---------------------------------------------------------------- 3. input repair (and the .json bug)
def test_a_json_file_is_written_as_json_text(ses):
    tl = ses.tools
    body = '{\n  "name": "shop",\n  "private": true\n}\n'
    tl.run("write", {"path": "package.json", "content": body})
    assert (ses.s.repo / "package.json").read_text() == body                        # was "{'name': 'shop', 'private': True}"
    out = tl.run("read", {"path": "package.json", "offset": "2", "limit": "1"})       # numbers sent as text
    assert '"name": "shop"' in out and '"private"' not in out
    out = tl.run("multi_edit", {"path": "package.json", "edits": '[{"old_string": "shop", "new_string": "store"}]'})
    assert out.startswith("Edited") and '"store"' in (ses.s.repo / "package.json").read_text()


def test_repair_only_where_one_reading_exists():
    from app.devsahayak.engine import repair_input
    sch = {"type": "object", "required": ["n"], "properties": {
        "n": {"type": "integer"}, "on": {"type": "boolean"}, "txt": {"type": "string"}, "items": {"type": "array", "items": {"type": "integer"}},
        "opt": {"type": "integer"}, "obj": {"type": "object", "properties": {"k": {"type": "number"}}}}}
    got = repair_input(sch, {"n": "20", "on": "false", "txt": "[1, 2]", "items": '["1", 2]', "opt": "null", "obj": '{"k": "2.5"}', "x": "7"})
    assert got == {"n": 20, "on": False, "txt": "[1, 2]", "items": [1, 2], "obj": {"k": 2.5}, "x": "7"}
    assert repair_input(sch, {"n": "twenty"}) == {"n": "twenty"}                     # no single reading: left alone


# ---------------------------------------------------------------- 2. past the time limit = background
def test_the_box_keeps_a_command_running_past_its_limit(monkeypatch):
    from app.devlab import box
    calls = []
    monkeypatch.setattr(box, "docker", lambda: "docker")
    monkeypatch.setattr(box, "_run", lambda argv, timeout, cwd="": (calls.append((argv, timeout)) or
                        ((124, "building...\n[timed out after 5s]", 5.0) if argv[1] == "run" else (0, "", 0.1))))
    monkeypatch.setattr(box, "bg_state", lambda name: {"running": True, "rc": None})
    r = box.run_in("img", "/tmp", "make all", timeout=5, move_to_bg={"name": "hoola-bg-t1-3", "task": "t1", "limit_s": 1800})
    run = calls[0][0]
    assert r["moved"] == "hoola-bg-t1-3" and "[timed out" not in r["out"] and calls[0][1] == 5
    assert "--rm" not in run and "hoola.bg=1" in run and "hoola.task=t1" in run and "timeout -s TERM 1800" in run[-1]
    assert not any(a[1] == "kill" for a, _ in calls)                                # never killed
    calls.clear()
    monkeypatch.setattr(box, "_run", lambda argv, timeout, cwd="": (calls.append((argv, timeout)) or (0, "ok", 1.0)))
    r = box.run_in("img", "/tmp", "true", timeout=5, move_to_bg={"name": "hoola-bg-t1-4", "task": "t1"})
    assert r["rc"] == 0 and not r.get("moved") and any(a[1:3] == ["rm", "-f"] for a, _ in calls)   # finished: removed


def test_bash_registers_the_moved_command(ses, monkeypatch):
    from app.devlab import box
    tl = ses.tools
    monkeypatch.setattr(tl, "_image", lambda: ("img", ""))
    seen = {}

    def fake(img, d, cmd, **kw):
        seen.update(kw)
        return {"rc": None, "out": "compiling 1/40\n", "secs": 120.0, "timed_out": True, "moved": kw["move_to_bg"]["name"]}
    monkeypatch.setattr(box, "run_in", fake)
    out = tl.run("bash", {"command": "make all", "timeout": 120})
    assert "NOT stopped" in out and "as bg1" in out and "compiling 1/40" in out and "Do not run it again" in out
    assert tl._bg()["bg1"]["name"] == seen["move_to_bg"]["name"] and tl._bg()["bg1"]["state"] == "running"
    ev = ses.EN.event(tl, "bash", {"command": "make all"}, out)[0]
    assert ev["k"] == "bgstart" and ev["moved"] and "Still running after 120 s" in ev["did"]


# ---------------------------------------------------------------- 4. the repo's own formatter
def _local(monkeypatch, tl):
    from app.devsahayak import fmt as FM
    monkeypatch.setattr(FM, "_exec", lambda tools, shell, timeout: {"rc": 0, "out": subprocess.run(
        ["bash", "-c", shell], cwd=str(tools.s.repo), capture_output=True, text=True, timeout=timeout).stdout})


def test_ruff_formats_what_the_reply_changed_when_the_repo_declares_it(ses, monkeypatch):
    from app.devsahayak import fmt as FM
    tl, repo = ses.tools, ses.s.repo
    _local(monkeypatch, tl)
    (repo / "app.py").write_text("def greet( name ):\n    return {'a':1}\n")
    assert FM.after_edits(tl, ["app.py"]) == ("", [])                              # the repo declares no formatter
    (repo / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")
    note, changed = FM.after_edits(tl, ["app.py"])
    assert changed == ["app.py"] and (repo / "app.py").read_text() == 'def greet(name):\n    return {"a": 1}\n'
    assert "The repo's formatter (ruff) changed app.py" in note and '+    return {"a": 1}' in note


def test_a_whole_file_rewrite_is_put_back_and_secrets_are_never_touched(ses, monkeypatch):
    from app.devsahayak import fmt as FM
    tl, repo = ses.tools, ses.s.repo
    _local(monkeypatch, tl)
    (repo / "go.mod").write_text("module x\n\ngo 1.22\n")
    ugly = "package main\nfunc main(){\n" + "".join(f"x{i}:=1;_ = x{i}\n" for i in range(80)) + "}\n"
    (repo / "main.go").write_text(ugly)
    monkeypatch.setattr(FM, "_set", lambda n, d: 20 if n == "dev_format_max_lines" else d)
    note, changed = FM.after_edits(tl, ["main.go"])
    assert changed == [] and "Not formatted" in note and (repo / "main.go").read_text() == ugly
    tl.hidden = {"secret.py"}
    (repo / "pyproject.toml").write_text("[tool.ruff]\n")
    (repo / "secret.py").write_text("x=1\n")
    assert FM.after_edits(tl, ["secret.py"]) == ("", []) and (repo / "secret.py").read_text() == "x=1\n"


def test_declared_formatters():
    from app.devsahayak import fmt as FM
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "package.json").write_text(json.dumps({"devDependencies": {"prettier": "^3"}}))
    (d / "Cargo.toml").write_text('[package]\nedition = "2018"\n')
    got = FM.declared(d)
    assert "prettier" in got and "node_modules/.bin/prettier" in got["prettier"]["shell"] and "--edition 2018" in got["rustfmt"]["shell"]
    (d / "biome.json").write_text("{}")
    assert "biome" in FM.declared(d) and "prettier" not in FM.declared(d)


# ---------------------------------------------------------------- 5. redo
def _cp(ses, label):
    msgs = ses.s.messages() + [{"role": "user", "content": label}]
    ses.s.save_messages(msgs)
    return ses.s.checkpoint(label, len(msgs))


@pytest.mark.parametrize("what", ["both", "code", "conversation"])
def test_redo_brings_back_what_going_back_threw_away(ses, what):
    s, EN = ses.s, ses.EN
    _cp(ses, "one")
    (s.repo / "app.py").write_text("v2\n")
    _cp(ses, "two")
    (s.repo / "app.py").write_text("v3 not saved in a checkpoint\n")
    (s.repo / "new.py").write_text("brand new\n")
    before_msgs, before_cps = s.messages(), [c["n"] for c in s.meta["checkpoints"]]
    s.rewind(1, what)
    s = EN.Session("t1")
    assert EN.view("t1")["redo"] == {"n": 1, "what": what}
    s.redo()
    s = EN.Session("t1")
    assert (s.repo / "app.py").read_text() == "v3 not saved in a checkpoint\n" and (s.repo / "new.py").is_file()
    assert s.messages() == before_msgs and [c["n"] for c in s.meta["checkpoints"]] == before_cps
    assert "redo" not in s.meta and EN.view("t1")["redo"] is None
    with pytest.raises(ValueError, match="nothing to redo"):
        s.redo()


def test_her_next_message_makes_the_going_back_final(ses):
    s, EN = ses.s, ses.EN
    _cp(ses, "one")
    (s.repo / "app.py").write_text("v2\n")
    _cp(ses, "two")
    s.rewind(1, "both")
    s = EN.Session("t1")
    EN.her_blocks(SimpleNamespace(conf={}), s, "carry on", lambda e: None)
    assert "redo" not in EN.Session("t1").meta and not (s.dir / "redo").exists()


def test_routes_and_screens():
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    assert '"/tasks/{tid}/redo"' in api
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "data-act=\"redo\"" in js and "case 'redo'" in js and "case 'format'" in js
    d = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "case 'redo':" in d and "case 'format':" in d and "'\\$_base/redo'" in d.replace("'$_base/redo'", "'\\$_base/redo'")
