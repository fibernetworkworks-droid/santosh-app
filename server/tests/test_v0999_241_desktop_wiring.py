"""v0.999.241 DESKTOP WIRING (owner: "CHECK ALL DESKTOP FUNCTIONS ARE WIRED PROPERLY" -> "GO FIX ALL 3"):
every PC tool, run once against a pretend Windows PC and a pretend Hoola PC, sends only actions that app really has;
the three gaps the check found are closed - Windows-only setup tools are never offered on Hoola PC or a Mac / Linux PC,
a background command a stopped job started is stopped with it (and Hoola can stop one), hover / drag / page tables on
her PC say plainly when her Chrome extension is not connected."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _handlers():
    win = set(re.findall(r"def do_([a-z0-9_]+)\(", (ROOT / "desktop/santosh_desktop/actions.py").read_text()))
    ls = (ROOT / "desktop-linux/agent.py").read_text()
    i = ls.index("AX_ACTIONS = {")
    lin = set(re.findall(r"def do_([a-z0-9_]+)\(", ls)) | set(re.findall(r'"(ax_[a-z_]+)"', ls[i:ls.index("}", i)]))
    return win, lin


@pytest.fixture
def fake_pcs(monkeypatch):
    from app.pc import operator as o
    from app.pc import extlink
    win, lin = _handlers()
    sent: list[tuple[str, str, dict]] = []

    async def raw(op, action, args, timeout, log, hub):
        sent.append((op.kind or "her_pc", action, dict(args or {})))
        if action not in (lin if op.kind == o.HOOLA_PC_KIND else win):
            raise Exception(f"Unknown action {action}")
        return {"ok": True, "job": "job1", "running": True, "tables": [], "title": "t", "url": "https://example.com/"}

    async def personal(op, action, args=None, timeout=60):
        sent.append(("personal", action, dict(args or {})))
        if action not in win:
            raise Exception(f"Unknown action {action}")
        return {"ok": True, "results": [], "text": "x", "files": []}

    async def yes(op, what):
        return True
    monkeypatch.setattr(o, "_pc_raw", raw)
    monkeypatch.setattr(o, "_pc_user", personal)
    monkeypatch.setattr(o, "_approval", yes)
    monkeypatch.setattr(extlink, "ready", lambda t: False)
    return o, sent, win, lin


ARGS = {"x": 10, "y": 10, "text": "a", "keys": "enter", "url": "https://example.com", "name": "Notepad", "app": "Notepad",
        "ref": 1, "to_ref": 2, "path": "/data/a.xlsx", "query": "a", "on": True, "op": "check", "value": "a",
        "values": {"a": "b"}, "fields": [{"ref": 1, "value": "a"}], "command": "echo hi", "packages": ["jq"], "seconds": 1,
        "title": "t", "id": "1", "job": "job1", "steps": [{"tool": "ax_click", "ref": "e1"}], "amount": 1, "to_x": 20,
        "to_y": 20, "rows": [["a"]], "template": "/data/t.docx", "out": "/data/o.docx"}
ASKS = {"ask_user", "ask_otp", "ask_login", "ask_approval", "done", "stage_done", "wait"}


def test_every_tool_reaches_an_action_its_computer_has(env, fake_pcs):
    o, sent, win, lin = fake_pcs

    async def go():
        bad = []
        for kind in ("", o.HOOLA_PC_KIND):
            op = o.Op(id="pcop_w", tenant="t", conv="c", task="test", kind=kind)
            for t in o._tools_for(op):
                n = t.get("name")
                if not n or n in ASKS:
                    continue
                sent.clear()
                try:
                    await asyncio.wait_for(o._do(o.Op(id="pcop_w", tenant="t", conv="c", task="test", kind=kind), n, dict(ARGS)), 20)
                except Exception as e:   # noqa: BLE001
                    bad.append((kind, n, f"{type(e).__name__}: {e}"))
                for k, action, _ in sent:
                    have = win if k in ("her_pc", "personal") else lin
                    if action not in have:
                        bad.append((kind, n, f"sends {action}, which that computer cannot do"))
        return bad
    assert asyncio.run(go()) == []


def test_windows_only_setup_tools_stay_on_windows(env, fake_pcs, monkeypatch):
    o, sent, *_ = fake_pcs
    names = lambda op: {t.get("name") for t in o._tools_for(op)}   # noqa: E731
    her = o.Op(id="pcop_a", tenant="t", conv="c", task="x", kind="")
    hoola = o.Op(id="pcop_b", tenant="t", conv="c", task="x", kind=o.HOOLA_PC_KIND)
    assert set(o.WINDOWS_ONLY) <= names(her)
    assert not set(o.WINDOWS_ONLY) & names(hoola)
    monkeypatch.setattr(o, "os_note", lambda op: o.MAC_NOTE)
    assert not set(o.WINDOWS_ONLY) & names(her)
    out = asyncio.run(o._do(her, "pt_run", {"on": True}))
    assert out.startswith("NOT AVAILABLE") and "Mac" in out and not sent
    out = asyncio.run(o._do(hoola, "ext", {"on": True}))
    assert "Hoola PC" in out and "out of date" not in out and not sent


def test_background_commands_stop_with_the_job(env, fake_pcs):
    o, sent, *_ = fake_pcs
    op = o.Op(id="pcop_r", tenant="t", conv="c", task="big download", kind=o.HOOLA_PC_KIND)
    assert "run_stop" in {t["name"] for t in o.HOOLA_TOOLS}
    out = asyncio.run(o._do(op, "run", {"command": "sleep 900", "background": True}))
    assert "job1" in out and op.bg_jobs == ["job1"]
    op.status = "done"                                     # a finished job may leave a long download running
    assert asyncio.run(o._stop_bg_jobs(op)) == 0 and op.bg_jobs == ["job1"]
    sent.clear()
    op.status = "cancelled"                                # her Stop: nothing of this job keeps running
    assert asyncio.run(o._stop_bg_jobs(op)) == 1 and op.bg_jobs == []
    assert [(a, x) for _, a, x in sent] == [("run_stop", {"job": "job1"})]
    op.bg_jobs = ["job1"]
    sent.clear()
    assert asyncio.run(o._do(op, "run_stop", {"job": "job1"})) == "stopped background job job1" and op.bg_jobs == []
    assert [a for _, a, _ in sent] == ["run_stop"]
    assert asyncio.run(o._do(op, "run_stop", {})).startswith("REFUSED")
    src = (Path(o.__file__)).read_text()
    assert "await _stop_bg_jobs(op)" in src[src.index("async def _run(op: Op)"):]   # wired into every job's end


def test_chrome_only_page_tools_say_when_the_extension_is_gone(env, fake_pcs, monkeypatch):
    o, sent, *_ = fake_pcs
    from app.pc import extlink
    her = o.Op(id="pcop_c", tenant="t", conv="c", task="x", kind="")
    for n in ("page_hover", "page_drag", "page_tables"):
        out = asyncio.run(o._do(her, n, {"ref": 1, "to_ref": 2}))
        assert out.startswith("NOT AVAILABLE") and "extension" in out and "Hoola PC" not in out
    assert not sent                                         # never sent on to Hoola Desktop, which cannot do them
    her.bg = True
    assert "background" in asyncio.run(o._do(her, "page_hover", {"ref": 1}))
    her.bg = False
    seen = []

    async def handle(tenant, action, args):
        seen.append(action)
        return {"ok": True, "tables": []}
    monkeypatch.setattr(extlink, "ready", lambda t: True)
    monkeypatch.setattr(extlink, "handle", handle)
    asyncio.run(o._do(her, "page_tables", {}))
    assert seen == ["page_tables"]                          # connected: her Chrome does it
    hoola = o.Op(id="pcop_d", tenant="t", conv="c", task="x", kind=o.HOOLA_PC_KIND)
    monkeypatch.setattr(extlink, "ready", lambda t: False)
    assert "pointing at #1" in asyncio.run(o._do(hoola, "page_hover", {"ref": 1}))   # Hoola PC has its own
