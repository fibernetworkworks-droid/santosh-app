"""v0.999 CLAUDE CODE PARITY, THE LAST TEN (owner: "NOW CHECK AGAIN HOOLA CODE IS 100% SAME AS CLAUDE CODE" -> "GO ALL"):
the repo's skills (.claude/skills), its remote MCP servers (.mcp.json, her OK first), CLAUDE.md @imports +
CLAUDE.local.md + a folder's rules when work moves there, settings.json env + defaultMode, four more hook events
(SubagentStop / PreCompact / SessionEnd / Notification), /compact with what to keep, /export, plugins (and marketplaces)
from a GitHub link, the .claude files changed from the screen, and output styles."""
from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

import pytest

from tests.test_tech_devsahayak import T, dev  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    yield EN


def _repo(EN, tid="t1"):
    ses = EN.Session(tid)
    r = ses.repo
    for d in (".claude/skills/release", ".claude/output-styles", "api/v2", "docs"):
        (r / d).mkdir(parents=True, exist_ok=True)
    (r / ".claude/skills/release/SKILL.md").write_text("---\nname: release\ndescription: How we ship a release\n---\n1. bump\n2. tag\n")
    (r / ".claude/skills/release/checklist.md").write_text("- notes\n")
    (r / ".claude/output-styles/terse.md").write_text("---\ndescription: Very short\n---\nAnswer in one line.\n")
    (r / ".claude/settings.json").write_text(json.dumps({
        "env": {"NODE_ENV": "test", "API_TOKEN": "nope", "bad name": "x"},
        "permissions": {"defaultMode": "acceptEdits"}, "outputStyle": "explanatory",
        "hooks": {"SubagentStop": [{"hooks": [{"type": "command", "command": "echo sub"}]}],
                  "PreCompact": [{"hooks": [{"type": "command", "command": "echo pre"}]}],
                  "Notification": [{"hooks": [{"type": "command", "command": "notify-send"}]}],
                  "SessionEnd": [{"hooks": [{"type": "command", "command": "echo bye"}]}]}}))
    (r / ".mcp.json").write_text(json.dumps({"mcpServers": {
        "linear": {"type": "http", "url": "https://mcp.linear.app/mcp", "headers": {"X-Team": "core", "Authorization": "Bearer ${LINEAR_KEY}"}},
        "local-db": {"command": "npx", "args": ["db-mcp"]}, "plain": {"type": "http", "url": "http://example.com/mcp"}}}))
    (r / "CLAUDE.md").write_text("# Rules\nUse tabs.\nSee @docs/style.md for style.\n")
    (r / "docs/style.md").write_text("Names in snake_case.\n@../CLAUDE.md\n")
    (r / "CLAUDE.local.md").write_text("My local note.\n")
    (r / "api/CLAUDE.md").write_text("API rule: every route has a test.\n")
    (r / "api/v2/handler.py").write_text("x = 1\n")
    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    ses.save_meta()
    return ses


def test_skills_mcp_env_mode_styles_and_hook_events_are_read(ws):
    EN = ws
    from app.devsahayak import repoconf as RC
    ses = _repo(EN)
    sk = RC.skills(ses.repo)["release"]
    assert sk["description"] == "How we ship a release" and "1. bump" in sk["body"] and sk["files"] == [".claude/skills/release/checklist.md"]
    mcp = RC.mcp_servers(ses.repo)
    assert mcp["linear"]["ok"] and mcp["linear"]["headers"] == {"X-Team": "core"}      # a ${SECRET} header is never sent
    assert mcp["local-db"]["ok"] and mcp["local-db"]["kind"] == "stdio" and mcp["local-db"]["argv"] == ["npx", "db-mcp"]   # v0.999 runs in the box now
    assert not mcp["plain"]["ok"] and "https" in mcp["plain"]["why"]
    conf = RC.settings(ses.repo)
    assert conf["env"] == {"NODE_ENV": "test"}                                          # a secret-looking name is left out
    assert conf["mode"] == "steps" and conf["accept_edits"] and conf["style"] == "explanatory"
    assert set(conf["hooks"]) == {"SubagentStop", "PreCompact", "Notification", "SessionEnd"}
    st = RC.styles(ses.repo)
    assert {"default", "explanatory", "learning", "terse"} <= set(st) and "Answer in one line." in st["terse"]["prompt"]


def test_claude_md_imports_local_and_folder_rules(ws):
    EN = ws
    from app.devsahayak import repoconf as RC
    ses = _repo(EN)
    txt = RC.rule_text(ses.repo, "CLAUDE.md")
    assert "Use tabs." in txt and '<imported path="docs/style.md">' in txt and "Names in snake_case." in txt
    assert txt.count("# Rules") == 1                                                   # an import cycle is read once
    assert RC.folder_rules(ses.walk(), "api/v2/handler.py") == ["api/CLAUDE.md"]
    tl = EN.Tools(ses, False)
    out = tl.run("read", {"path": "api/v2/handler.py"})
    assert '<folder_rules path="api/CLAUDE.md">' in out and "every route has a test" in out
    assert "folder_rules" not in tl.run("read", {"path": "api/v2/handler.py"})        # once a session
    from types import SimpleNamespace
    first = EN._first_message(SimpleNamespace(kind="fix", repo="o/r", base="main", text="x", tenant_id="", id="t1"), "", "", "", "", ses, "", "")
    assert "My local note." in first and "Names in snake_case." in first


def test_the_repo_skill_and_mcp_tools(ws, monkeypatch):
    EN = ws
    from app.devsahayak import repoconf as RC
    ses = _repo(EN)
    tl = EN.Tools(ses, False)
    tl.repo_skills, tl.repo_mcp = RC.skills(ses.repo), RC.mcp_servers(ses.repo)
    assert "- release (this repo): How we ship a release" in tl.t_skill("list")
    got = tl.t_skill("read", name="release")
    assert "1. bump" in got and ".claude/skills/release/checklist.md" in got
    assert "linear (this repo's .mcp.json, pack_id repo:linear): reachable" in tl.t_mcp("list")
    assert "could not start" in tl.t_mcp("call", pack_id="repo:local-db", tool="q")    # no box here: said plainly
    from app.agent import duniya_tools as DU
    import app.bazar.connectors.mcp_remote as MR
    monkeypatch.setattr(DU, "_guard_url", lambda u: u)

    class Fake:
        def __init__(self, url, token):
            self.url, self.token = url, token

        def call_tool(self, name, args):
            return {"issues": [{"id": 1, "title": f"{name} {args}"}]}

        def list_tools(self):
            return [{"name": "list_issues", "description": "List"}]
    monkeypatch.setattr(MR, "McpHttpRemote", Fake)
    assert "list_issues" in tl.t_mcp("list", pack_id="repo:linear")
    assert "list_issues {'team': 'core'}" in tl.t_mcp("call", pack_id="repo:linear", tool="list_issues", args={"team": "core"})
    # her OK first: a server the repo names asks once, then 'always' covers the session
    ask = EN.needs_ok("t1", "auto", ses, "mcp", {"action": "call", "pack_id": "repo:linear", "tool": "x"})
    assert ask["tool"] == "mcp" and ask["server"] == "linear"
    EN.PERMIT["t1"] = {**ask, "id": "p", "_ev": threading.Event(), "answer": None}
    assert EN.give_ok("t1", "p", "always")
    assert EN.needs_ok("t1", "auto", EN.Session("t1"), "mcp", {"action": "call", "pack_id": "repo:linear", "tool": "x"}) is None
    assert EN.needs_ok("t1", "auto", EN.Session("t1"), "mcp", {"action": "list", "pack_id": "repo:linear"}) is None   # after always, looking too


def test_compact_focus_and_the_hook_events(ws, monkeypatch):
    EN = ws
    from app.devsahayak import brain as B
    seen = {}

    def call(system, msgs, tools, **k):
        seen["ask"] = msgs[-1]["content"]
        return [{"type": "text", "text": "summary"}], "end_turn"
    monkeypatch.setattr(B, "call", call)
    msgs = [{"role": "user", "content": "start"}] + [{"role": r, "content": f"m{i}"} for i, r in enumerate(["assistant", "user"] * 8)]
    EN.compact(msgs, keep_tail=2, focus="the API changes")
    assert "focus on: the API changes" in str(seen.get("ask"))
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert 'run_hooks(tools, "PreCompact")' in src and "def notify_hook" in src and "def session_end_hook" in src
    assert "notify_hook(tools, ask)" in src and "notify_hook(self, ask)" in src
    assert '"SubagentStop"' in (ROOT / "server/app/devsahayak/subagent.py").read_text()
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert "_EN.session_end_hook(tid, tenant)" in svc and "target=_EN.session_end_hook" in svc


# ---------------------------------------------------------------- plugins
def test_plugins_and_marketplaces_from_a_github_link(ws, tmp_path):
    from app.devsahayak import plugins as PL
    from app.devsahayak import repoconf as RC

    def fake_clone(url, into):
        assert url == "https://github.com/acme/kit.git"
        (into / ".claude-plugin").mkdir(parents=True)
        (into / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"plugins": [
            {"name": "reviewer", "source": "./plugins/reviewer", "description": "Review kit"},
            {"name": "elsewhere", "source": {"github": "x/y"}}, {"name": "escape", "source": "./../../etc"}]}))
        p = into / "plugins" / "reviewer"
        (p / "commands").mkdir(parents=True)
        (p / "agents").mkdir()
        (p / "hooks").mkdir()
        (p / "commands" / "review-pr.md").write_text("---\ndescription: Review a PR\n---\nReview PR $1 carefully.\n")
        (p / "agents" / "nitpicker.md").write_text("---\nname: nitpicker\ntools: Read\n---\nFind small issues.\n")
        (p / "hooks" / "hooks.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "make lint"}]}]}}))
        (p / "link").symlink_to("/etc/passwd")
        (into / ".git").mkdir()
    with pytest.raises(PL.PluginError):
        PL.add("ten", "https://evil.example/x", clone=fake_clone)
    got = PL.add("ten", "https://github.com/acme/kit", clone=fake_clone)
    assert [p["name"] for p in got] == ["reviewer"] and got[0]["has"]["commands"] == 1 and got[0]["description"] == "Review kit"
    root = PL.shelf("ten") / "reviewer"
    assert not (root / "link").exists()                                              # links are never copied
    roots = PL.roots("ten")
    repo = tmp_path / "r"
    repo.mkdir()
    assert RC.expand_command(repo, "/review-pr 42", roots) == ("review-pr", "Review PR 42 carefully.")
    assert RC.agents(repo, roots)["nitpicker"]["origin"] == "plugin reviewer"
    assert RC.settings(repo, roots)["hooks"]["Stop"][0]["commands"] == ["make lint"]
    PL.set_enabled("ten", "reviewer", False)
    assert PL.roots("ten") == [] and RC.expand_command(repo, "/review-pr 1", PL.roots("ten")) is None
    assert PL.remove("ten", "reviewer") == [] and not root.exists()


# ---------------------------------------------------------------- the session routes
def _row(S):
    from app.db import session
    from app.devsahayak.models import DevTask
    with session() as s:
        t = DevTask(tenant_id=T, number="D-0200", kind="fix", repo="meghana/shop-api", text="Fix the cart", base="main",
                    status="explained", explain="Fixed it.",
                    steps=json.dumps([{"k": "say", "text": "Looking at the cart.", "n": 0, "at": "x"},
                                      {"k": "bash", "did": "Ran the tests", "n": 1, "at": "x"},
                                      {"k": "note", "her": True, "text": "also the coupon", "n": 2, "at": "x"}]))
        s.add(t)
        s.flush()
        return t.id


def test_export_claude_files_and_style(dev, ws):  # noqa: F811
    S, EN = dev, ws
    tid = _row(S)
    _repo(EN, tid)
    md = S.export(T, tid)
    assert md["name"].startswith("hoola-code-") and md["name"].endswith(".md")
    t = md["text"]
    assert "## You\n\nFix the cart" in t and "## Hoola\n\nLooking at the cart." in t and "- bash: Ran the tests" in t
    assert "## You\n\nalso the coupon" in t and "## Result\n\nFixed it." in t
    with pytest.raises(S.DevError):
        S.claude_write(T, tid, "src/app.py", "x")                                    # only Claude Code's own files
    with pytest.raises(S.DevError, match="valid JSON"):
        S.claude_write(T, tid, ".claude/settings.json", "{nope")
    with pytest.raises(S.DevError, match="key or a password"):
        S.claude_write(T, tid, ".claude/commands/x.md", "token: ghp_" + "a" * 36)
    out = S.claude_write(T, tid, ".claude/agents/tester.md", "---\nname: tester\n---\nWrite tests.")
    assert out["what"] == "saved" and ".claude/agents/tester.md" in out["files"]
    assert S.claude_file(T, tid, ".claude/agents/tester.md")["text"].endswith("Write tests.\n")
    assert S.claude_write(T, tid, ".claude/agents/tester.md", "")["what"] == "deleted"
    assert S.set_style(T, tid, "learning")["style"] == "learning" and EN.Session(tid).meta["style"] == "learning"
    with pytest.raises(S.DevError):
        S.set_style(T, tid, "nope")
    setup = S.repo_commands(T, tid)
    assert setup["style"] == "learning" and any(x["name"] == "release" for x in setup["skills"])
    assert any(x["name"] == "linear" and x["ok"] for x in setup["mcp"]) and setup["env"] == ["NODE_ENV"] and setup["mode"] == "steps"
    assert "CLAUDE.md" in setup["files"] and ".claude/skills/release/SKILL.md" in setup["files"]


def test_the_routes(dev):  # noqa: F811
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    for m, path in (("get", "/api/devsahayak/tasks/nope/export"), ("get", "/api/devsahayak/tasks/nope/claude-file?path=CLAUDE.md"),
                    ("put", "/api/devsahayak/tasks/nope/claude-file"), ("put", "/api/devsahayak/tasks/nope/style"),
                    ("get", "/api/devsahayak/plugins"), ("post", "/api/devsahayak/plugins"), ("patch", "/api/devsahayak/plugins/x"),
                    ("delete", "/api/devsahayak/plugins/x")):
        r = getattr(c, m)(path, **({"json": {}} if m in ("put", "post", "patch") else {}))
        assert r.status_code != 405 and (r.headers.get("content-type", "").startswith("text/markdown") or r.json().get("detail") != "Not Found"), (path, r.status_code)


# ---------------------------------------------------------------- the page, in a real browser
import os  # noqa: E402

from tests.test_v0312_arena_screen import arena_server  # noqa: F401,E402
from tests.test_v121_site import site_env  # noqa: F401,E402


@pytest.mark.skipif(not os.environ.get("HOOLA_CHROMIUM") and not Path("/opt/pw-browsers/chromium-1243/chrome-linux64/chrome").exists(),
                    reason="no Chromium here")
def test_the_page_has_export_styles_files_and_plugins(arena_server):  # noqa: F811
    from tests.test_v0768_hoola_code_shell import TASKS, _console, _shot
    ctx, pg, errs, calls, state = _console(arena_server)
    steps = [{"k": "claudefile", "path": ".claude/agents/tester.md", "what": "saved", "by": "you", "at": "2026-11-10T10:00:02+00:00", "n": 0}]
    ask = {"id": "p1", "tool": "mcp", "server": "linear", "what": "Use linear's list_issues (an MCP server this repo names)"}
    task = {**TASKS[0], "text": "Tidy the API", "steps": steps, "notes": [], "log": [], "diff": "", "found": {}, "last_n": 0,
            "now": "Waiting for your OK", "srv_now": 1_800_000_000.0, "now_info": {}, "ask": ask, "ctx": 20, "mode": "steps",
            "ws": {"exists": True, "checkpoints": []}}
    got = {"compact": [], "put": [], "style": [], "plug": []}
    plugins = [{"name": "reviewer", "url": "https://github.com/acme/kit", "description": "Review kit", "enabled": True, "version": "1.0", "has": {"commands": 2, "agents": 1}}]
    setup = {"commands": [], "agents": [], "hooks": ["Stop"], "rules": {"allow": 0, "ask": 0, "deny": 0},
             "skills": [{"name": "release", "description": "How we ship"}], "mcp": [{"name": "linear", "ok": True}, {"name": "local-db", "ok": False, "why": "It runs a program on your computer"}],
             "styles": [{"name": "default", "description": "", "origin": "hoola"}, {"name": "learning", "description": "Teaches", "origin": "hoola"}, {"name": "terse", "description": "Very short", "origin": "this repo"}],
             "style": "default", "env": ["NODE_ENV"], "mode": "steps", "plugins": plugins, "files": ["CLAUDE.md", ".claude/settings.json"]}
    pg.route("**/api/devsahayak/tasks/dt1", lambda r: r.fulfill(json=task))
    pg.route("**/api/devsahayak/tasks/dt1/stream", lambda r: r.fulfill(status=200, headers={"Content-Type": "text/event-stream"}, body=""))
    pg.route("**/api/devsahayak/tasks/dt1/commands", lambda r: r.fulfill(json=setup))
    pg.route("**/api/devsahayak/tasks/dt1/export", lambda r: r.fulfill(status=200, body="# Tidy the API\n",
                                                                       headers={"Content-Type": "text/markdown", "Content-Disposition": 'attachment; filename="hoola-code-tidy.md"'}))

    def compact(r):
        got["compact"].append(r.request.post_data_json)
        r.fulfill(json={"ok": True})
    pg.route("**/api/devsahayak/tasks/dt1/compact", compact)

    def style(r):
        got["style"].append(r.request.post_data_json)
        r.fulfill(json={"ok": True, "style": r.request.post_data_json["style"]})
    pg.route("**/api/devsahayak/tasks/dt1/style", style)

    def cfile(r):
        if r.request.method == "PUT":
            got["put"].append(r.request.post_data_json)
            return r.fulfill(json={"ok": True, "what": "saved", "path": r.request.post_data_json["path"], "files": setup["files"]})
        r.fulfill(json={"path": "CLAUDE.md", "text": "# Rules\nUse tabs.\n"})
    pg.route("**/api/devsahayak/tasks/dt1/claude-file*", cfile)

    def plug(r):
        if r.request.method != "GET":
            got["plug"].append((r.request.method, r.request.url.rsplit("/", 1)[-1], r.request.post_data_json if r.request.method != "DELETE" else None))
        r.fulfill(json={"plugins": plugins})
    pg.route("**/api/devsahayak/plugins**", plug)
    pg.locator("[data-tid='dt1']").click()
    pg.wait_for_selector("#hcdPerm")
    assert "You changed .claude/agents/tester.md" in pg.locator("#hcdCol").text_content()
    assert "allow linear for this session" in pg.locator("#hcdPerm").text_content()
    # /compact with what to keep
    pg.locator("#hcdNote").fill("/compact keep the API notes")
    pg.locator("#hcdNote").press("Enter")
    pg.wait_for_function("() => true")
    pg.wait_for_timeout(300)
    assert got["compact"] == [{"focus": "keep the API notes"}]
    # the slash menu has the new commands
    pg.locator("#hcdNote").fill("")
    pg.locator("#hcdNote").click()
    pg.keyboard.type("/ex")
    pg.wait_for_selector("#hcdPick .hcd-pickr")
    assert "/export" in pg.locator("#hcdPick").text_content()
    pg.keyboard.press("Escape")
    pg.locator("#hcdNote").fill("")
    # export downloads a file
    with pg.expect_download() as dl:
        pg.locator("[data-menu='smenu']").click()
        pg.get_by_text("Export the conversation", exact=True).click()
    assert dl.value.suggested_filename == "hoola-code-tidy.md"
    # output style
    pg.locator("[data-menu='smenu']").click()
    pg.get_by_text("Output style…", exact=True).click()
    pg.get_by_text("terse", exact=True).click()
    pg.wait_for_timeout(300)
    assert got["style"] == [{"style": "terse"}]
    # the setup dialog shows skills / MCP / mode / env / plugins
    pg.locator("[data-menu='smenu']").click()
    pg.get_by_text("This repo’s Claude Code setup", exact=True).click()
    pg.wait_for_selector("#hcdDlg[open]")
    d = pg.locator("#hcdDlg").text_content()
    for w in ("release", "How we ship", "linear", "runs a program on your computer", "NODE_ENV", "Ask each step", "reviewer"):
        assert w in d, w
    _shot(pg, "setup")
    pg.locator("#hcdDlg button[value='edit']").click()
    pg.wait_for_selector("#hcdDlg[open] .hcd-cfrow")
    pg.locator("#hcdDlg .hcd-cfrow").first.click()
    pg.wait_for_selector("#hcdCfText")
    assert "Use tabs." in pg.locator("#hcdCfText").input_value()
    pg.locator("#hcdCfText").fill("# Rules\nUse spaces.\n")
    _shot(pg, "editor")
    pg.locator("#hcdDlg button[value='ok']").click()
    pg.wait_for_timeout(400)
    assert got["put"] == [{"path": "CLAUDE.md", "text": "# Rules\nUse spaces.\n"}]
    # plugins
    pg.locator("[data-menu='smenu']").click()
    pg.get_by_text("Plugins…", exact=True).click()
    pg.wait_for_selector("#hcdDlg[open] .hcd-plug")
    assert "Review kit" in pg.locator("#hcdDlg").text_content() and "2 commands" in pg.locator("#hcdDlg").text_content()
    pg.locator("#hcdPlugUrl").fill("https://github.com/acme/more")
    _shot(pg, "plugins")
    pg.locator("#hcdDlg button[value='add']").click()
    pg.wait_for_timeout(400)
    assert ("POST", "plugins", {"url": "https://github.com/acme/more"}) in got["plug"]
    pg.wait_for_selector("#hcdDlg[open] .hcd-plug")
    pg.locator("#hcdDlg button[value='off:reviewer']").click()
    pg.wait_for_timeout(400)
    assert ("PATCH", "reviewer", {"enabled": False}) in got["plug"]
    assert not errs, errs
    ctx.close()


def test_the_phone_has_them_too():
    code = "".join(p.read_text() for p in (ROOT / "lib/ui/code").glob("*.dart"))
    for w in ("/export", "/style", "/claude-file", "/plugins", "'focus'", "'claudefile'", "Color(0x"):
        assert (w in code) == (w != "Color(0x"), w
