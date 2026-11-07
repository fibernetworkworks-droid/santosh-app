"""v0.472 SEMANTIC DESKTOP (ax_*) - the page_* cure for DESKTOP apps (Excel, Word, Tally UI, Explorer
dialogs), via vercel-labs/agent-desktop (owner: "NOW LETS WORK ON DESKTOP ACCESS FOR THIS" -> repo read
-> "START").

THE GAP (proved in code): the operator loop got its semantic browser lane in v0.208 (page_elements /
page_click / page_type BY REF), but every DESKTOP app still ran on pixel guesses - the vision model chose
x,y on a lossy JPEG, so DPI scaling, layout shifts and identical twin buttons kept making clicks miss.

THE FIX (all additive - pixel lane, browser lane, approvals and every existing suite untouched):
- desktop/santosh_desktop/axtree.py: one wrapper over the agent-desktop CLI (v1.1.0, Apache-2.0). JSON
  envelopes in, flat element lists out, refs like @s8f3k2p9:e12, delivery dispositions kept. Helper binary
  searched beside SantoshDesktop.exe > HOOLA_AGENT_DESKTOP > PATH; missing helper -> AxUnavailable so the
  model falls back to the pixel lane with one clear line.
- desktop/santosh_desktop/actions.py: do_ax_* bridge actions, EVERY one behind the same control switch
  (_ax -> _control_on) and log line; ax_launch also passes BLOCKED_APP_WORDS.
- server/app/pc/operator.py: 9 ax_* tools + _do dispatch + narration + DESKTOP-SEMANTIC-FIRST prompt +
  old-desktop upgrade hint + the v0.91.1 blind-pointing guards (ax_click in MOVES_SCREEN/POINTING).

Tests here pin: the operator wiring (TOOLS + HOOLA_TOOLS carry the tools; her-PC toolset unchanged apart
from the additive block), the _do dispatch through a fake _pc (ref formatting, twin/surface hints,
privacy: ax_set_value never echoes the value, blocked shortcuts and apps, wait clamps), the narration, the
upgrade hint for every ax_ action, the prompt pins, the blind-pointing guard pins, and the DEVICE side
against a FAKE agent-desktop binary (envelope parsing, tree flattening, stale-ref error mapping,
AxUnavailable, the control gate on every bridge action by source pin).
"""
import asyncio
import json
import os
import stat
import sys
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

from app.pc import operator as op_mod  # noqa: E402

AX_TOOLS = ("ax_apps", "ax_snapshot", "ax_text", "ax_find", "ax_click", "ax_set_value", "ax_press",
            "ax_launch", "ax_wait")                    # what the MODEL gets
AX_BRIDGE = AX_TOOLS + ("ax_status",)                  # what the DESKTOP answers (status is ops-only)
DESKTOP = Path(__file__).resolve().parents[2] / "desktop" / "santosh_desktop"


# ---------------- wiring: the model gets the ax tools, nothing else moved ----------------
def test_tools_carry_all_nine_ax_tools():
    names = [t["name"] for t in op_mod.TOOLS]
    for n in AX_TOOLS:
        assert n in names, n


def test_hoola_tools_carry_them_too_and_the_vm_extras_survive():
    names = [t["name"] for t in op_mod.HOOLA_TOOLS]
    for n in AX_TOOLS + ("install", "run", "user_pc_pull", "user_pc_push"):
        assert n in names, n


def test_pixel_and_browser_lanes_are_untouched():
    names = [t["name"] for t in op_mod.TOOLS]
    for n in ("click", "type", "key", "scroll", "drag", "open_app", "open_url", "page_elements", "page_click",
              "page_type", "page_select", "page_fill_form", "wait_for", "tabs", "switch_tab", "downloads",
              "screenshot", "window", "list_apps", "focus_window", "wait", "ask_approval", "ask_otp", "done"):
        assert n in names, n


def test_schemas_are_well_formed():
    for t in op_mod.TOOLS:
        if t["name"] not in AX_TOOLS:
            continue
        sch = t["input_schema"]
        assert sch.get("type") == "object"
        assert isinstance(sch.get("properties"), dict)
        req = sch.get("required", [])
        assert set(req) <= set(sch["properties"]), t["name"]
    reqs = {t["name"]: set(t["input_schema"].get("required", [])) for t in op_mod.TOOLS}
    assert reqs["ax_click"] == {"ref"}
    assert reqs["ax_set_value"] == {"ref", "text"}
    assert reqs["ax_press"] == {"keys"}
    assert reqs["ax_launch"] == {"name"}


# ---------------- the _do dispatch (fake _pc, same harness as v0.208) ----------------
class FakePC:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, op, action, args, timeout=30, log=True):
        self.calls.append((action, args, timeout))
        return self.result


async def _do_with(name, a, fake):
    real = op_mod._pc

    async def patched(op, action, args, timeout=30, log=True):
        return await fake(op, action, args, timeout, log)

    op_mod._pc = patched
    try:
        return await op_mod._do(op_mod.Op(id="t1", tenant="ten1", conv="c1", task="Excel mein sheet banao"), name, a)
    finally:
        op_mod._pc = real


def test_ax_snapshot_formats_refs_and_hints_surfaces():
    fake = FakePC({"app": "Excel", "window": "Book1 - Excel", "snapshot_id": "s1", "complete": True,
                   "elements": [{"ref": "@s1:e2", "role": "button", "name": "Save"},
                                {"ref": "@s1:e3", "role": "textfield", "name": "Name", "value": "old", "disabled": True}],
                   "surfaces": ["menu"]})
    out = asyncio.run(_do_with("ax_snapshot", {"app": "Excel"}, fake))
    assert "@s1:e2 button 'Save'" in out
    assert "@s1:e3 textfield 'Name'" in out and "= 'old'" in out and "[DISABLED]" in out
    assert "menu" in out and "ax_click / ax_set_value" in out
    assert fake.calls[0][0] == "ax_snapshot" and fake.calls[0][1]["app"] == "Excel"


def test_ax_snapshot_unproven_identity_tells_the_model_to_wait_longer():
    fake = FakePC({"app": "Chrome", "identity_unproven": True, "complete": True, "elements": []})
    out = asyncio.run(_do_with("ax_snapshot", {"app": "Chrome"}, fake))
    assert "longer timeout_ms" in out


def test_ax_snapshot_empty_tree_points_back_to_pixels():
    fake = FakePC({"app": "Paint", "elements": [], "complete": True})
    out = asyncio.run(_do_with("ax_snapshot", {"app": "Paint"}, fake))
    assert "pixel" in out.lower() and "screenshot" in out.lower()


def test_ax_snapshot_truncated_tree_tells_the_model_to_drill():
    fake = FakePC({"app": "Tally", "complete": False,
                   "elements": [{"ref": "@s1:e1", "role": "button", "name": "OK"}]})
    out = asyncio.run(_do_with("ax_snapshot", {"app": "Tally"}, fake))
    assert "skeleton=true" in out and "root=<ref>" in out


def test_ax_click_refuses_bare_refs():
    out = asyncio.run(_do_with("ax_click", {"ref": "e12"}, FakePC({})))
    assert out.startswith("REFUSED") and "ax_snapshot" in out


def test_ax_click_reports_an_opened_surface():
    fake = FakePC({"ref": "@s1:e2", "delivery": "delivered_unverified", "surfaces": ["menu"]})
    out = asyncio.run(_do_with("ax_click", {"ref": "@s1:e2"}, fake))
    assert "clicked @s1:e2" in out and "surface opened: menu" in out and "readback not proven" in out


def test_ax_set_value_never_echoes_the_text_privacy():
    fake = FakePC({"ref": "@s1:e3", "length": 18, "delivery": "delivered_verified", "verified": True})
    out = asyncio.run(_do_with("ax_set_value", {"ref": "@s1:e3", "text": "Aadhaar 1234 5678 9012"}, fake))
    assert "typed into @s1:e3" in out and "verified by readback" in out
    assert "1234" not in out, "the value itself must never come back to the model"


def test_ax_set_value_unverified_write_blocks_blind_submits():
    fake = FakePC({"ref": "@s1:e3", "length": 3, "delivery": "delivered_unverified"})
    out = asyncio.run(_do_with("ax_set_value", {"ref": "@s1:e3", "text": "abc"}, fake))
    assert "did not confirm" in out and "never submit blindly" in out


def test_ax_set_value_refuses_bad_refs():
    out = asyncio.run(_do_with("ax_set_value", {"ref": "nope", "text": "x"}, FakePC({})))
    assert out.startswith("REFUSED")


def test_ax_press_blocks_dangerous_shortcuts():
    out = asyncio.run(_do_with("ax_press", {"keys": "win+r"}, FakePC({})))
    assert out.startswith("REFUSED")
    out = asyncio.run(_do_with("ax_press", {"keys": "ctrl+s"}, FakePC({"delivery": "delivered_unverified"})))
    assert "pressed ctrl+s" in out


def test_ax_launch_blocked_apps_and_pass_through():
    out = asyncio.run(_do_with("ax_launch", {"name": "powershell"}, FakePC({})))
    assert out.startswith("REFUSED")
    fake = FakePC({"launched": "TallyPrime"})
    out = asyncio.run(_do_with("ax_launch", {"name": "TallyPrime"}, fake))
    assert "launched TallyPrime" in out and fake.calls[0][0] == "ax_launch"


def test_ax_wait_clamps_seconds():
    fake = FakePC({"found": True})
    asyncio.run(_do_with("ax_wait", {"text": "Gateway of Tally", "seconds": 999}, fake))
    action, args, timeout = fake.calls[0]
    assert args["seconds"] == 20 and timeout >= 20


def test_ax_wait_and_find_refuse_empty_queries():
    assert asyncio.run(_do_with("ax_wait", {}, FakePC({}))).startswith("REFUSED")
    assert asyncio.run(_do_with("ax_find", {"app": "Excel"}, FakePC({}))).startswith("REFUSED")


def test_ax_apps_lists_apps_and_windows():
    fake = FakePC({"apps": [{"name": "Excel"}, {"name": "TallyPrime"}],
                   "windows": [{"id": "w1", "title": "Book1 - Excel"}]})
    out = asyncio.run(_do_with("ax_apps", {}, fake))
    assert "Excel" in out and "TallyPrime" in out and "w1" in out


def test_desktop_errors_map_to_clear_lines_not_tracebacks():
    fake = FakePC({})

    async def boom(op, action, args, timeout=30, log=True):
        raise RuntimeError("STALE_REF: @s1:e2 gone")

    real = op_mod._pc
    op_mod._pc = boom
    try:
        out = asyncio.run(op_mod._do(op_mod.Op(id="t1", tenant="ten1", conv="c1", task="t"), "ax_click",
                                     {"ref": "@s1:e2"}))
    finally:
        op_mod._pc = real
    assert out.startswith("ERROR: STALE_REF")


# ---------------- old desktop / old agent upgrade hint ----------------
def test_upgrade_hint_for_every_ax_action():
    for n in AX_BRIDGE:
        line = op_mod._desktop_says(Exception(f"Unknown action {n}"), n)
        assert line is not None and "SantoshDesktop.exe" in line, n


# ---------------- narration (the live card) ----------------
def test_say_lines_are_exact_mode_and_privacy_safe():
    assert "exact mode" in op_mod._say("ax_snapshot", {"app": "Tally"})
    assert "@s1:e2" in op_mod._say("ax_click", {"ref": "@s1:e2"})
    assert op_mod._say("ax_set_value", {"ref": "@s1:e3", "text": "SECRET VALUE"}) == \
        "field mein likh raha hoon (12 akshar, exact mode)"
    assert "SECRET" not in op_mod._say("ax_set_value", {"ref": "@s1:e3", "text": "SECRET VALUE"})


# ---------------- the v0.91.1 blind-pointing guards know the ax movers ----------------
def test_screen_move_guards_cover_the_ax_steps():
    assert "ax_click" in op_mod.MOVES_SCREEN and "ax_click" in op_mod.POINTING
    assert "ax_launch" in op_mod.MOVES_SCREEN and "ax_launch" in op_mod.FOCUS_MOVERS
    assert op_mod.SETTLE_S["ax_click"] > 0 and op_mod.SETTLE_S["ax_launch"] > 0


# ---------------- semantic-first prompts ----------------
def test_system_prompt_teaches_desktop_semantic_first():
    s = op_mod.SYSTEM
    assert "DESKTOP APPS - SEMANTIC FIRST" in s and "ax_snapshot" in s
    assert "ax_set_value" in s and "never comes back" in s
    assert "BEFORE pixel clicks" in s          # pixels stay the fallback, not the default
    assert "pixel mode bhi kaam karta hai" in s  # missing-helper fallback line


# ---------------- the device side: desktop/santosh_desktop/axtree.py against a FAKE helper ----------------
FAKE_HELPER = r'''#!/usr/bin/env python3
import json, os, sys
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
def ok(d): print(json.dumps({"version": "2.6", "ok": True, "command": cmd, "data": d}))
def err(code, msg): print(json.dumps({"version": "2.6", "ok": False, "command": cmd,
    "error": {"code": code, "message": msg, "disposition": {"delivery": "not_delivered", "retry": "safe"}}}))
args = sys.argv[2:]
if cmd == "status":
    ok({"platform": "windows", "permissions": {"accessibility": {"state": "granted"}}})
elif cmd == "snapshot":
    d = {"snapshot_id": "s1", "window": {"title": "Book1 - Excel"}, "app": "Excel", "complete": True,
         "tree": {"role": "window", "name": "Book1", "children": [
             {"role": "button", "name": "Save", "ref_id": "@s1:e2"},
             {"role": "textfield", "name": "Name", "value": "old", "ref_id": "@s1:e3"},
             {"role": "statictext", "name": "no ref here"}]}}
    if os.environ.get("FAKE_AX_UNPROVEN"):
        d["identity_unproven"] = True
    if os.environ.get("FAKE_AX_TRUNCATED"):
        d["complete"] = False
    ok(d)
elif cmd == "click":
    ref = args[0] if args else ""
    if ref == "@s1:e9":
        err("STALE_REF", f"{ref} not found in current RefMap")
    else:
        ok({"action": "click", "disposition": {"delivery": "delivered_verified", "retry": "unsafe"},
            "surfaces": ["menu"]})
elif cmd == "set-value":
    ok({"action": "set-value", "disposition": {"delivery": "delivered_unverified", "retry": "unsafe"}})
elif cmd == "find":
    ok({"matches": [{"ref_id": "@s1:e2", "role": "button", "name": "Save"}]})
elif cmd == "press":
    ok({"disposition": {"delivery": "delivered_unverified"}})
elif cmd == "launch":
    ok({"name": args[0] if args else ""})
elif cmd == "wait":
    ok({"matched": True})
elif cmd == "list-apps":
    ok({"apps": [{"name": "Excel", "pid": 4242}]})
elif cmd == "list-windows":
    ok([{"id": "w1", "title": "Book1 - Excel", "app": "Excel"}])
else:
    err("INTERNAL", "unknown command " + cmd)
'''


@pytest.fixture()
def fake_helper(tmp_path, monkeypatch):
    p = tmp_path / "agent-desktop"
    p.write_text(FAKE_HELPER)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("HOOLA_AGENT_DESKTOP", str(p))
    monkeypatch.delenv("FAKE_AX_UNPROVEN", raising=False)
    monkeypatch.delenv("FAKE_AX_TRUNCATED", raising=False)
    return p


def test_helper_discovery_env_then_missing(fake_helper, monkeypatch):
    import santosh_desktop.axtree as ax
    assert ax.available() is True
    monkeypatch.setenv("HOOLA_AGENT_DESKTOP", str(fake_helper.parent / "nahi-hai"))
    assert ax.available() is False


def test_device_snapshot_flattens_the_tree(fake_helper):
    import santosh_desktop.axtree as ax
    d = ax.snapshot(app="Excel")
    assert d["snapshot_id"] == "s1" and d["window"] == "Book1 - Excel" and d["complete"] is True
    refs = [e["ref"] for e in d["elements"]]
    assert "@s1:e2" in refs and "@s1:e3" in refs
    assert all(e["role"] != "statictext" for e in d["elements"]), "only actionable nodes carry refs"
    rows = {e["ref"]: e for e in d["elements"]}
    assert rows["@s1:e3"]["value"] == "old"


def test_device_snapshot_reports_unproven_identity(fake_helper, monkeypatch):
    import santosh_desktop.axtree as ax
    monkeypatch.setenv("FAKE_AX_UNPROVEN", "1")
    d = ax.snapshot(app="Chrome")
    assert d["identity_unproven"] is True and "longer timeout" in d["note"]


def test_device_click_maps_the_envelope(fake_helper):
    import santosh_desktop.axtree as ax
    d = ax.click("@s1:e2")
    assert d["clicked"] is True and d["verified"] is True and "menu" in d["surfaces"]


def test_device_stale_ref_raises_a_structured_axerror(fake_helper):
    import santosh_desktop.axtree as ax
    with pytest.raises(ax.AxError) as ei:
        ax.click("@s1:e9")
    assert ei.value.code == "STALE_REF" and ei.value.retry_safe is True


def test_device_set_value_returns_only_delivery_and_length(fake_helper):
    import santosh_desktop.axtree as ax
    d = ax.set_value("@s1:e3", "Mehul Patel")
    assert d["length"] == 11 and d["verified"] is False and "Mehul" not in json.dumps(d)


def test_device_helpers_refuse_bare_refs_and_empty_text(fake_helper):
    import santosh_desktop.axtree as ax
    with pytest.raises(ax.AxError) as ei:
        ax.click("e2")
    assert ei.value.code == "INVALID_ARGS"
    with pytest.raises(ax.AxError):
        ax.set_value("@s1:e3", "")


def test_device_apps_and_windows_parse_both_shapes(fake_helper):
    import santosh_desktop.axtree as ax
    assert ax.list_apps()["apps"][0]["name"] == "Excel"
    w = ax.windows()
    assert w["windows"][0]["id"] == "w1" and w["windows"][0]["title"] == "Book1 - Excel"


def test_device_read_flattens_named_nodes_only(fake_helper):
    import santosh_desktop.axtree as ax
    d = ax.read(app="Excel")
    assert "button: Save" in d["text"] and "window: Book1" in d["text"]


# ---------------- the bridge actions all sit behind the control switch (source pins) ----------------
def test_every_ax_bridge_action_is_control_gated():
    src = (DESKTOP / "actions.py").read_text()
    for n in AX_BRIDGE:
        body = src.split(f"def do_{n}(", 1)[1].split("\n    def ", 1)[0]
        assert "self._ax()" in body or "self._control_on()" in body, n
    ax_src = src.split("v1.6.0 SEMANTIC DESKTOP", 1)[1]
    assert 'BLOCKED_APP_WORDS.search' in ax_src.split("def do_ax_launch", 1)[1].split("def ", 1)[0], \
        "ax_launch must refuse the same apps open_app refuses"


def test_axtree_is_stdlib_only():
    src = (DESKTOP / "axtree.py").read_text()
    for bad in ("import requests", "import httpx", "import pyautogui", "import PIL", "import comtypes"):
        assert bad not in src


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.684.0"
