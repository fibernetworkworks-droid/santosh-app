"""Santosh PC Operator: the screen -> Claude -> one action loop, approvals on the phone, refusals, live view."""
import asyncio
import base64
import types

import pytest

from tests.test_bazar import _events, _notices, bz  # noqa: F401

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0fakejpeg").decode()


class FakePC:
    def __init__(self, control=True):
        self.calls = []
        self.control = control

    async def __call__(self, op, action, args=None, timeout=40):
        self.calls.append((action, dict(args or {})))
        if action == "screen":
            return {"image_b64": JPEG, "width": 1280, "height": 720, "active_window": "Excel - Book1", "windows": ["Excel - Book1"]}
        if action == "open_app":
            return {"opened": args["name"]}
        if action == "apps":
            return {"apps": ["Excel", "Tally"], "windows": []}
        return {"ok": True}


def tu(i, tool, **inp):
    return types.SimpleNamespace(model_dump=lambda exclude_none=True: {"type": "tool_use", "id": f"t{i}", "name": tool, "input": inp})


def txt(t):
    return types.SimpleNamespace(model_dump=lambda exclude_none=True: {"type": "text", "text": t})


class FakeClaude:
    def __init__(self, script):
        self.script = list(script)
        self.seen = []
        self.messages = self

    async def create(self, **kw):
        self.seen.append(kw)
        return types.SimpleNamespace(content=self.script.pop(0))


@pytest.fixture
def op(bz, monkeypatch):  # noqa: F811
    from app.pc import operator
    pc = FakePC()
    monkeypatch.setattr(operator, "_pc", pc)

    class Conn:
        info = {"control": True}
    from app.pc.hub import hub
    monkeypatch.setattr(hub, "is_online", lambda t, d=None: True)
    monkeypatch.setattr(hub, "online", lambda t: [Conn()])
    yield operator, pc, bz


def run(coro):
    return asyncio.run(coro)


def test_task_with_approval_runs_to_the_end(op, monkeypatch):
    operator, pc, bz = op
    conv, svc = bz["conv"], bz["svc"]
    claude = FakeClaude([
        [txt("Excel kholta hoon"), tu(1, "open_app", name="Excel")],
        [tu(2, "type", text="Sales Oct")],
        [tu(3, "ask_approval", what="File ko 'Sales Oct.xlsx' naam se save karna")],
        [tu(4, "key", keys="ctrl+s")],
        [tu(5, "done", answer="Excel sheet 'Sales Oct' bana kar save kar di.", success=True)],
    ])
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: claude)

    async def go():
        r = await operator.start("default", conv, "Excel mein Sales Oct sheet banao aur save karo", wait=0)
        sid = r["session_id"]
        for _ in range(200):
            await asyncio.sleep(0.01)
            o = operator.get("default", sid)
            if o.status == "needs_confirm" and _events(conv, "bazar_approval"):
                break
        assert o.status == "needs_confirm"
        assert ("control", {"op": "key", "keys": "ctrl+s"}) not in pc.calls      # nothing saved before the tap
        card = [e for e in _events(conv, "bazar_approval")][-1]
        assert card["title"].startswith("Aapka PC: File ko") and card["amount_paise"] == 0
        await asyncio.to_thread(svc.decide, "default", card["id"], "approve")
        await asyncio.wait_for(o.done_event.wait(), 5)
        return o
    o = run(go())
    assert o.status == "done" and "Sales Oct" in o.summary
    assert ("open_app", {"name": "Excel"}) in pc.calls and ("control", {"op": "key", "keys": "ctrl+s"}) in pc.calls
    assert o.frame and o.frame_seq >= 5 and [t["do"] for t in o.timeline][:2] == ["open_app", "type"]
    assert any("Sales Oct" in (n or "") for n in _notices(conv))          # result posted (tool had returned early)
    imgs = sum(1 for m in claude.seen[-1]["messages"] for b in (m["content"] if isinstance(m["content"], list) else [])
               for c in ([b] + (b.get("content") if isinstance(b.get("content"), list) else [])) if c.get("type") == "image")
    assert imgs <= operator.KEEP_IMAGES


def test_refuses_system_tools_and_needs_permission(op, monkeypatch):
    operator, pc, bz = op
    claude = FakeClaude([[tu(1, "open_app", name="PowerShell")], [tu(2, "key", keys="win+r")],
                         [tu(3, "done", answer="Nahi kar sakta", success=False)]])
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: claude)
    r = run(operator.start("default", bz["conv"], "powershell kholo", wait=5))
    assert r["status"] == "partial"
    assert not any(c[0] == "open_app" for c in pc.calls) and ("control", {"op": "key", "keys": "win+r"}) not in pc.calls
    results = [b for m in claude.seen[-1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
               for b in m["content"] if b.get("type") == "tool_result"]
    assert any("REFUSED" in str(b["content"]) for b in results)

    from app.pc.hub import hub

    class Off:
        info = {"control": False}
    monkeypatch.setattr(hub, "online", lambda t: [Off()])
    with pytest.raises(PermissionError):
        run(operator.start("default", bz["conv"], "excel kholo", wait=0))


def test_live_view_api_and_stop(op, monkeypatch):
    operator, pc, bz = op

    class Slow(FakeClaude):
        async def create(self, **kw):
            await asyncio.sleep(0.05)
            return types.SimpleNamespace(content=[tu(len(self.seen) + 1, "wait", seconds=0.5)])
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: Slow([]))

    async def go():
        r = await operator.start("default", bz["conv"], "kuch karo", wait=0.3)
        sid = r["session_id"]
        live = operator.get("default", sid).live()
        assert live["source"] == "pc" and live["status"] == "running" and live["seq"] >= 1
        assert operator.get("someone-else", sid) is None
        assert operator.stop("default", sid)
        o = operator.get("default", sid)
        await asyncio.wait_for(o.done_event.wait(), 5)
        return o
    o = run(go())
    assert o.status == "cancelled"


def test_hub_keeps_the_control_switch_from_the_pc():
    """Regression: the PC's 'Santosh ko PC chalane dein' tick must survive the hub's info message."""
    import asyncio
    import json

    from app.pc.hub import Hub

    class WS:
        def __init__(self):
            self.msgs = [json.dumps({"type": "info", "name": "Office PC", "control": True, "paused": False})]
            self.sent = []

        async def send_text(self, t):
            self.sent.append(t)

        async def send_json(self, d):
            self.sent.append(d)

        async def receive_text(self):
            if self.msgs:
                return self.msgs.pop(0)
            await asyncio.sleep(0.05)
            raise RuntimeError("closed")

        async def close(self, code=1000):
            pass

    h = Hub()
    seen = {}

    async def go():
        ws = WS()
        task = asyncio.create_task(h.serve(ws, "dev-x", "t-x"))
        for _ in range(20):
            await asyncio.sleep(0.01)
            c = h.online("t-x")
            if c and c[0].info:
                seen.update(c[0].info)
                break
        try:
            await task
        except Exception:
            pass
    import app.pc.service as svc
    orig = (svc.touch_device, svc.save_info)
    svc.touch_device = lambda *a, **k: None
    svc.save_info = lambda *a, **k: None
    try:
        asyncio.run(go())
    finally:
        svc.touch_device, svc.save_info = orig
    assert seen.get("control") is True
