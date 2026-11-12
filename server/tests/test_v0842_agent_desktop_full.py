"""v0.842 AGENT-DESKTOP FULL (owner: "IS ALL THIS REPO FEATURE IS NOW IN HOOLA DESKTOP" -> "GO AGENT-DESKTOP FULL").

Before: Hoola wrapped 10 of agent-desktop's 61 commands (v1.1.0), typed set-value text ON THE COMMAND LINE (an
Aadhaar from her ID locker was readable by any program listing processes), threw away element states, printed
click surfaces as a broken Python repr, and Hoola's own Linux PC had no exact mode at all.

Now (desktop 1.10.0 + agent-desktop v1.2.0, checksum-pinned): every useful HEADLESS command - get / is / check /
uncheck / toggle / expand / collapse / clear / scroll-to / right-click / select / type / scroll / close-app /
list-displays / window screenshot / surfaces / system surfaces / notifications / clipboard / batch - all text over
--stdin, states in every snapshot, readable surfaces; 13 new operator tools with the safety rules in code; the
same axtree.py inside the Hoola PC image. Headed-only commands (focus, double / triple click, hover, mouse-*,
key-down / up) are left out on purpose: exact mode never moves her cursor or steals focus.

The real binary was walked on a real Linux desktop (Xvfb + AT-SPI + zenity) through this axtree.py while this
was built; these tests pin the same contract against a recording fake helper so CI needs no desktop.
"""
import asyncio
import json
import stat
import sys
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "desktop"))

from app.pc import operator as op_mod  # noqa: E402

NEW_TOOLS = ("ax_get", "ax_is", "ax_act", "ax_select", "ax_type", "ax_scroll", "ax_window_shot", "ax_displays",
             "ax_system", "ax_notifications", "ax_notification", "ax_clipboard", "ax_close_app", "ax_batch")

# a fake agent-desktop that RECORDS every call (argv + stdin) and answers in the real v1.2.0 shapes
FAKE = r'''#!/usr/bin/env python3
import json, os, sys
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
args = sys.argv[2:]
stdin = sys.stdin.read() if "--stdin" in args else ""
with open(os.environ["FAKE_AX_LOG"], "a") as f:
    f.write(json.dumps({"cmd": cmd, "args": args, "stdin": stdin}) + "\n")
def ok(d): print(json.dumps({"version": "2.6", "ok": True, "command": cmd, "data": d}))
def err(code, msg): print(json.dumps({"version": "2.6", "ok": False, "command": cmd,
    "error": {"code": code, "message": msg, "disposition": {"delivery": "not_delivered", "retry": "safe"}}}))
V = {"delivery": "delivered_verified", "retry": "unsafe"}
if cmd == "snapshot":
    ok({"snapshot_id": "s1", "app": "Tally", "complete": True, "tree": {"role": "window", "children": [
        {"role": "checkbox", "name": "Inclusive of tax", "ref_id": "@s1:e1", "states": ["checked", "focused"]},
        {"role": "button", "name": "Accept", "ref_id": "@s1:e2", "states": ["disabled"]}]},
        "surfaces": [{"id": "w-9", "type": "menu", "title": "Gateway"}]})
elif cmd == "get":
    ok({"ref": args[0], "property": args[2], "value": "500.00"})
elif cmd == "is":
    ok({"ref": args[0], "property": args[2], "value": True})
elif cmd in ("check", "uncheck", "toggle", "expand", "collapse", "clear", "right-click", "select", "type", "scroll",
             "set-value", "clipboard-set", "clipboard-clear", "dismiss-notification", "notification-action"):
    ok({"action": cmd, "disposition": V, "surfaces": [{"id": "w-1", "type": "menu", "title": "Context"}] if cmd == "right-click" else []})
elif cmd == "scroll-to":
    ok({"action": cmd, "disposition": {"delivery": "not_delivered"}})
elif cmd == "close-app":
    ok({"app": args[0], "details": {"evidence": "process_instance_exited"}, "disposition": V})
elif cmd == "list-displays":
    ok([{"bounds": {"width": 1920, "height": 1080}, "is_primary": True, "scale": 1.25},
        {"bounds": {"width": 1280, "height": 1024}, "is_primary": False, "scale": 1.0}])
elif cmd == "list-surfaces":
    ok({"surfaces": [{"id": "w-1", "title": "Tally", "type": "window"}]})
elif cmd == "open-system-surface":
    ok({"window": {"id": "w-start", "title": "Start"}})
elif cmd == "list-notifications":
    ok([{"index": 1, "app": "WhatsApp", "title": "Sharma ji", "body": "Bill bhejo", "actions": [{"name": "Reply"}, {"name": "Mark as read"}]}])
elif cmd == "clipboard-get":
    ok({"type": "text", "text": "card 4111 1111 1111 1111 total 500"})
elif cmd == "screenshot":
    from PIL import Image
    Image.new("RGB", (400, 300), "white").save(args[-1])
    ok({"path": args[-1], "width": 400, "height": 300, "format": "png"})
elif cmd == "batch":
    steps = json.loads(args[0])
    ok({"completed_entries": len(steps), "not_started_entries": 0,
        "results": [{"command": s["command"], "data": {"value": "ok"}} for s in steps]})
else:
    err("INTERNAL", "unknown " + cmd)
'''


@pytest.fixture()
def helper(tmp_path, monkeypatch):
    p = tmp_path / "agent-desktop"
    p.write_text(FAKE)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("HOOLA_AGENT_DESKTOP", str(p))
    monkeypatch.setenv("FAKE_AX_LOG", str(log))

    def calls():
        return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    return calls


# ---------------- the device side (desktop/santosh_desktop/axtree.py) ----------------

def test_text_never_on_the_command_line(helper):
    import santosh_desktop.axtree as ax
    secret = "AADHAAR 1234 5678 9012"
    ax.set_value("@s1:e1", secret)
    ax.type_text("@s1:e1", secret)
    ax.clipboard_set(secret)
    for c in helper():
        assert "--stdin" in c["args"] and secret not in " ".join(c["args"]), c
        assert c["stdin"] == secret


def test_snapshot_keeps_states_and_readable_surfaces(helper):
    import santosh_desktop.axtree as ax
    d = ax.snapshot(app="Tally")
    rows = {e["ref"]: e for e in d["elements"]}
    assert rows["@s1:e1"]["states"] == ["checked", "focused"] and rows["@s1:e2"]["states"] == ["disabled"]
    assert d["surfaces"] == ["menu: Gateway"]               # was "{'id': 'w-9', 'type..." cut at 20 chars


def test_get_is_act_select_scroll_shapes(helper):
    import santosh_desktop.axtree as ax
    assert ax.get("@s1:e1", "value")["value"] == "500.00"
    assert ax.is_state("@s1:e2", "enabled")["value"] is True
    for op in ("check", "uncheck", "toggle", "expand", "collapse", "clear", "right-click"):
        assert ax.act(op, "@s1:e1")["verified"] is True
    assert ax.act("right-click", "@s1:e1")["surfaces"] == ["menu: Context"]
    assert ax.act("scroll_to", "@s1:e1")["delivery"] == "not_delivered"   # the honest not-taken answer
    assert ax.select("@s1:e3", "GST 18%")["selected"] == "GST 18%"
    s = ax.scroll("@s1:e4", "down", 99)
    assert s["amount"] == 20
    cmds = [c["cmd"] for c in helper()]
    assert cmds[:2] == ["get", "is"] and "scroll-to" in cmds and "select" in cmds


def test_local_refusals(helper):
    import santosh_desktop.axtree as ax
    for bad in (lambda: ax.act("focus", "@s1:e1"),               # headed-only: never moves her focus
                lambda: ax.act("double-click", "@s1:e1"),
                lambda: ax.get("@s1:e1", "password"),
                lambda: ax.is_state("@s1:e1", "secret"),
                lambda: ax.click("e12"),                         # a bare ref is never guessed at
                lambda: ax.open_surface("registry-editor"),
                lambda: ax.dismiss_notification(1),              # which one? never the wrong popup
                lambda: ax.notification_action(1, "Reply"),
                lambda: ax.scroll("@s1:e1", "sideways")):
        with pytest.raises(ax.AxError):
            bad()
    assert helper() == []                                        # none of them reached the helper


def test_batch_is_safe_only(helper):
    import santosh_desktop.axtree as ax
    r = ax.batch([{"command": "check", "args": {"ref_id": "@s1:e1"}}, {"command": "get", "args": {"ref_id": "@s1:e2"}},
                  {"command": "wait", "args": {"ms": 99999}}])
    assert r["completed"] == 3
    sent = json.loads(helper()[-1]["args"][0])
    assert sent[2]["args"]["ms"] == 5000                          # waits are clamped
    for bad in ([{"command": "type", "args": {"ref_id": "@s1:e1", "text": "x"}}],
                [{"command": "press", "args": {"combo": "alt+f4"}}],
                [{"command": "launch", "args": {"app": "cmd"}}],
                [{"command": "click", "args": {"ref_id": "@s1:e1", "text": "1234"}}],
                [{"command": "click", "args": {}}] * 9):
        with pytest.raises(ax.AxError):
            ax.batch(bad)


def test_close_app_never_forces(helper):
    import santosh_desktop.axtree as ax
    assert ax.close_app("Notepad")["closed"] is True
    assert "--force" not in helper()[-1]["args"]


def test_window_shot_displays_notifications_clipboard(helper):
    import santosh_desktop.axtree as ax
    w = ax.window_shot(app="Tally")
    assert w["image_b64"][:4] == "/9j/" and w["width"] == 400       # a JPEG of ONE window
    assert [d["scale"] for d in ax.displays()["displays"]] == [1.25, 1.0]
    n = ax.notifications()["notifications"][0]
    assert n["app"] == "WhatsApp" and n["actions"] == ["Reply", "Mark as read"]
    assert ax.open_surface("start-menu")["window_id"] == "w-start"
    assert ax.clipboard_get()["text"].startswith("card")


def test_desktop_actions_gate_and_close_refusals(helper, tmp_path, monkeypatch):
    from santosh_desktop import actions as A
    from santosh_desktop.actions import ActionError
    for n in ("ax_get", "ax_is", "ax_act", "ax_select", "ax_type", "ax_scroll", "ax_close_app", "ax_displays",
              "ax_window_shot", "ax_surfaces", "ax_open_surface", "ax_notifications", "ax_notification_dismiss",
              "ax_notification_action", "ax_clipboard", "ax_batch"):
        assert hasattr(A.Actions, "do_" + n), n
    obj = A.Actions.__new__(A.Actions)
    obj.log = lambda *_: None
    monkeypatch.setattr(A.Actions, "_control_on", lambda self: None)
    for app in ("Santosh Desktop", "Hoola Desktop", "explorer.exe", "PowerShell"):
        with pytest.raises(ActionError):
            obj.do_ax_close_app(app=app)
    assert obj.do_ax_close_app(app="Notepad")["closed"] is True

    def off(self):
        raise ActionError("control is off")
    monkeypatch.setattr(A.Actions, "_control_on", off)          # the 'Hoola ko PC chalane dein' switch gates all
    with pytest.raises(ActionError):
        obj.do_ax_get(ref="@s1:e1")


# ---------------- the server side (pc/operator.py) ----------------

class FakePC:
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    async def __call__(self, op, action, args=None, timeout=40, log=True):
        self.calls.append((action, dict(args or {})))
        a = self.answers.get(action, {})
        if isinstance(a, Exception):
            raise a
        return a


def _do(monkeypatch, name, args, answers, approved=False):
    pc = FakePC(answers)
    monkeypatch.setattr(op_mod, "_pc", pc)
    op = op_mod.Op(id="pcop_t", tenant="t1", conv="c1", task="t")
    op.approved = approved
    out = asyncio.run(op_mod._do(op, name, args))
    return out, pc, op


def test_tools_registered_for_her_pc_and_hoola_pc():
    for tools in (op_mod.TOOLS, op_mod.HOOLA_TOOLS):
        names = [t["name"] for t in tools]
        for n in NEW_TOOLS:
            assert n in names, n
    assert "v0.842 the full exact kit" in op_mod.SYSTEM
    for n in NEW_TOOLS:
        assert op_mod._say(n, {"op": "get", "action": "Reply", "steps": [1]})


def test_type_and_clipboard_fill_id_refs_and_mask_reads(bz, monkeypatch):  # noqa: F811
    from app import idvault
    monkeypatch.setattr(idvault, "fill_value", lambda text, tenant: (text.replace("{id:aadhaar}", "1234 5678 9012"), ["aadhaar"]))
    out, pc, _ = _do(monkeypatch, "ax_type", {"ref": "@s1:e1", "text": "{id:aadhaar}"}, {"ax_type": {"length": 14, "verified": True}})
    assert pc.calls[0][1]["text"] == "1234 5678 9012" and "1234" not in out
    out, pc, _ = _do(monkeypatch, "ax_clipboard", {"op": "get"}, {"ax_clipboard": {"text": "card 4111 1111 1111 1111"}})
    assert "4111 1111 1111 1111" not in out                     # a card number read from the clipboard is masked


def test_notification_button_that_sends_needs_a_fresh_yes(bz, monkeypatch):  # noqa: F811
    base = {"index": 1, "expected_app": "WhatsApp"}
    out, pc, _ = _do(monkeypatch, "ax_notification", {**base, "action": "Send"}, {})
    assert out.startswith("REFUSED") and "ask_approval" in out and pc.calls == []
    out, pc, op = _do(monkeypatch, "ax_notification", {**base, "action": "Send"}, {"ax_notification_action": {}}, approved=True)
    assert pc.calls[0][0] == "ax_notification_action" and op.approved is False   # one yes = one press
    out, pc, _ = _do(monkeypatch, "ax_notification", {"index": 1, "action": "Open"}, {})
    assert out.startswith("REFUSED") and "expected_app" in out                     # which popup? never a guess
    out, pc, _ = _do(monkeypatch, "ax_notification", {**base, "action": "dismiss"}, {"ax_notification_dismiss": {}})
    assert pc.calls[0][0] == "ax_notification_dismiss"


def test_close_app_refusals_and_honest_answers(bz, monkeypatch):  # noqa: F811
    for app in ("Santosh Desktop", "explorer", "powershell", "agent-desktop"):
        out, pc, _ = _do(monkeypatch, "ax_close_app", {"app": app}, {})
        assert out.startswith("REFUSED") and pc.calls == []
    out, _, _ = _do(monkeypatch, "ax_close_app", {"app": "Excel"}, {"ax_close_app": {"closed": False}})
    assert "save changes" in out                                 # may be waiting on her 'save?' prompt
    out, _, _ = _do(monkeypatch, "ax_act", {"ref": "@s1:e1", "op": "scroll_to"}, {"ax_act": {"delivery": "not_delivered"}})
    assert "NOT taken" in out


def test_policy_refusal_points_to_the_pixel_lane_and_old_desktop_upgrade(bz, monkeypatch):  # noqa: F811
    out, _, _ = _do(monkeypatch, "ax_act", {"ref": "@s1:e1", "op": "check"},
                    {"ax_act": RuntimeError("ACTION_NOT_SUPPORTED: no Toggle")})
    assert "pixel tools" in out and "do not retry" in out
    out, _, _ = _do(monkeypatch, "ax_get", {"ref": "@s1:e1"}, {"ax_get": RuntimeError("Unknown action ax_get")})
    assert out == op_mod._OLD_DESKTOP
    for n in op_mod.AX_FULL:
        assert op_mod._desktop_says(RuntimeError("Unknown action " + n), n) == op_mod._OLD_DESKTOP


def test_window_shot_rides_as_an_image(bz, monkeypatch):  # noqa: F811
    pc = FakePC({"ax_window_shot": {"image_b64": "/9j/AAAA", "width": 400, "height": 300}})
    monkeypatch.setattr(op_mod, "_pc", pc)
    op = op_mod.Op(id="pcop_t", tenant="t1", conv="c1", task="t")
    blocks = asyncio.run(op_mod._ax_window_blocks(op, {"app": "Tally"}))
    assert blocks[1]["type"] == "image" and "NOT screen coordinates" in blocks[0]["text"]


# ---------------- Hoola's own Linux PC + the build ----------------

def test_linux_pc_has_the_same_axtree_and_routes_every_action():
    assert (ROOT / "desktop-linux" / "axtree.py").read_text() == (ROOT / "desktop" / "santosh_desktop" / "axtree.py").read_text()
    src = (ROOT / "desktop-linux" / "agent.py").read_text()
    for n in ("ax_snapshot", "ax_click", "ax_set_value", "ax_get", "ax_act", "ax_type", "ax_clipboard", "ax_batch",
              "ax_window_shot", "ax_notification_action", "ax_close_app"):
        assert f'"{n}"' in src, n
    dock = (ROOT / "desktop-linux" / "Dockerfile").read_text()
    assert "ARG AGENT_DESKTOP=1.2.0" in dock and "sha256sum -c -" in dock and "at-spi2-core" in dock
    assert "COPY agent.py axtree.py ./" in dock
    start = (ROOT / "desktop-linux" / "start.sh").read_text()
    assert "at-spi2-registryd" in start and "dbus-launch --sh-syntax" in start


def test_windows_build_pins_v120_and_desktop_1_10():
    wf = (ROOT / ".github/workflows/build-desktop.yml").read_text()
    assert "agent-desktop-v1.2.0-x86_64-pc-windows-msvc.tar.gz" in wf and "releases/download/v1.2.0/checksums.txt" in wf
    assert "v1.1.0" not in wf
    import santosh_desktop
    assert santosh_desktop.__version__ == "1.10.0"
