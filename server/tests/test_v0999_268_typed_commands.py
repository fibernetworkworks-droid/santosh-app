"""v0.999 EVERY CLAUDE CODE COMMAND, TYPED (owner: 'Typing every built-in command --- WORK ON IT'): in a Hoola Code session the
box takes Claude Code's built-in commands - /help /clear /compact /context /init /review /security-review /pr-comments /export
/rewind /resume /model /output-style /cost /usage /status /doctor /todos /bashes /agents /hooks /permissions /memory /mcp
/plugin /config /add-dir /login - each doing the same job here; built-in names win over a repo command of the same name;
terminal-only ones (/vim /terminal-setup /exit ...) say so instead of being sent to Hoola."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CLAUDE_CODE_BUILTINS = ["help", "clear", "compact", "context", "init", "review", "security-review", "pr-comments", "export", "rewind",
                        "resume", "model", "output-style", "cost", "usage", "status", "doctor", "todos", "bashes", "agents", "hooks",
                        "permissions", "memory", "mcp", "plugin", "config", "add-dir", "login", "logout", "install-github-app",
                        "vim", "terminal-setup", "statusline", "ide", "exit", "upgrade", "bug", "release-notes", "privacy-settings"]


def test_every_built_in_has_a_meaning_on_the_web():
    js = (ROOT / "server/app/static/console/code.js").read_text()
    block = js[js.index("const TERMINAL_ONLY"):js.index("const HOOLA_CMDS")]
    for n in CLAUDE_CODE_BUILTINS:
        if n == "security-review":
            continue                                           # sent to the server as it is (it runs the review)
        assert re.search(r"(^|[\s{'])'?%s'?:\s*\{" % re.escape(n), block) or f"'{n}'" in block, n


def test_every_built_in_has_a_meaning_on_the_phone():
    d = "".join(p.read_text() for p in (ROOT / "lib/ui/code").glob("*.dart"))
    missing = [n for n in CLAUDE_CODE_BUILTINS if f"'{n}'" not in d and f"'/{n}'" not in d and f"/{n}" not in d]
    assert not missing, missing


@pytest.mark.skipif(not os.environ.get("HOOLA_CHROMIUM") and not Path("/opt/pw-browsers/chromium-1243/chrome-linux64/chrome").exists(),
                    reason="no Chromium here")
def test_typing_the_commands_in_a_real_browser(arena_server):  # noqa: F811
    from tests.test_v0768_hoola_code_shell import TASKS, _console, _shot
    ctx, pg, errs, calls, state = _console(arena_server)
    task = {**TASKS[0], "running": False, "status": "explained", "can_continue": True, "steps": [
        {"k": "todo", "items": [{"content": "Fix the cart total", "status": "completed"}, {"content": "Add a test", "status": "in_progress"}], "at": "2026-11-10T10:00:01+00:00"}],
        "notes": [], "log": [], "diff": "", "found": {}, "last_n": 0, "ctx": 42, "mode": "auto", "branch": "hoola/fix-cart",
        "cost": {"inr": 12.5, "calls": 7}, "ws": {"exists": True, "checkpoints": [{"n": 1, "label": "round 1"}, {"n": 2, "label": "round 2"}]}}
    sent, files = [], []
    pg.route("**/api/devsahayak/tasks/dt1", lambda r: r.fulfill(json=task))
    pg.route("**/api/devsahayak/tasks/dt1/stream", lambda r: r.fulfill(status=200, headers={"Content-Type": "text/event-stream"}, body=""))
    pg.route("**/api/devsahayak/tasks/dt1/commands", lambda r: r.fulfill(json={"commands": [{"name": "review", "description": "the repo's own"}, {"name": "ship", "description": "Ship it"}],
                                                                                 "mcp": [{"name": "db", "ok": False, "why": "its command names a variable Hoola does not have"}], "files": []}))
    pg.route("**/api/devsahayak/tasks/dt1/bg/revise", lambda r: sent.append(r.request.post_data_json) or r.fulfill(json=task))
    pg.route("**/api/devsahayak/tasks/dt1/claude-file*", lambda r: files.append(r.request.url) or r.fulfill(status=404, json={"detail": "Not found"}))
    pg.locator("[data-tid='dt1']").click()
    pg.wait_for_selector("#hcdNote")

    def typed(cmd):
        pg.locator("#hcdNote").fill(cmd)
        pg.locator("#hcdNote").press("Escape")
        pg.locator("#hcdNote").press("Enter")

    typed("/help")
    pg.wait_for_selector("#hcdDlg[open] .hcd-cmdlist")
    d = pg.locator("#hcdDlg").text_content()
    for w in ("/rewind", "/status", "/doctor", "/memory", "/permissions", "/todos", "/ship", "Terminal-only"):
        assert w in d, w
    _shot(pg, "help")
    pg.locator("#hcdDlg button[value='no']").click()
    typed("/doctor")
    pg.wait_for_selector("#hcdDlg[open]")
    d = pg.locator("#hcdDlg").text_content()
    assert "hoola/fix-cart" in d and "42% used" in d and "MCP server db cannot be used" in d
    pg.locator("#hcdDlg button[value='no']").click()
    typed("/todos")
    pg.wait_for_selector("#hcdDlg[open]")
    assert "Add a test" in pg.locator("#hcdDlg").text_content()
    pg.locator("#hcdDlg button[value='no']").click()
    typed("/cost")
    pg.wait_for_selector("#hcdDlg[open]")
    assert "7 model calls" in pg.locator("#hcdDlg").text_content()
    pg.locator("#hcdDlg button[value='no']").click()
    typed("/hooks")                                            # no settings.json yet: the editor opens on the template
    pg.wait_for_selector("#hcdCfText")
    assert '"permissions"' in pg.locator("#hcdCfText").input_value()
    pg.locator("#hcdDlg button[value='no']").click()
    typed("/rewind")
    pg.wait_for_selector("#hcdDlg[open] .hcd-cfrow")
    assert "Checkpoint 2" in pg.locator("#hcdDlg").text_content()
    pg.locator("#hcdDlg button[value='no']").click()
    typed("/vim")
    pg.wait_for_timeout(300)
    typed("/review")                                           # the built-in wins over the repo's /review
    pg.wait_for_timeout(500)
    assert sent and "Review the changes on this branch" in sent[0]["text"]
    assert pg.locator("#hcdNote").input_value() == ""
    assert not errs, errs
    ctx.close()
