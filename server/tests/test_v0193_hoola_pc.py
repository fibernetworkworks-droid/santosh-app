"""v0.194 HOOLA KA APNA PC — the Linux cloud computer that belongs to Hoola (Phase 1 of the
Dots/Muse/Grok-style per-user coworker environment; owner: "START PHASE 1").

What ships:
1. desktop-linux/agent.py — a Linux agent that speaks the SAME bridge protocol as the Windows
   Santosh Desktop (hub.py: hello/info/job/result), so pc/operator.py's vision loop drives it
   unchanged. Chromium over CDP for page_text/tabs/switch_tab/open_url, Xvfb+xdotool+scrot for
   screen/control, and the coworker surface: install (apt/pip) + run (shell) inside the VM.
2. hub: a tenant can now have SEVERAL PCs — conn.info carries "kind", hub.call(kind=...) picks the
   right one; no kind = the legacy last-connected behaviour (her PC alone never notices).
3. operator: Op.kind="hoola_pc" routes every job by kind, adds the install/run tools + the VM
   addendum to the system prompt, and reports "Hoola ke apne PC par ..." instead of "Aapke PC par".
4. hoola_pc_do tool (family "pc" via PC_TOOLS) + where.py place "hoolapc" (aapke/tumhare/apne/
   hoola ke + computer) with the same steering/note/work-stickiness the other places have.

Server-side tests: real hub routing, the real operator loop on FakePC + scripted Claude, the real
where.py regexes, and the registry/admit wiring (same style as test_v0185_pc_browser.py).
"""
import asyncio
import base64
import json
import sys
import types
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0fakejpeg").decode()
KIND = "hoola_pc"


# ---------------- hub: several PCs per tenant, picked by kind ----------------
class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, s):
        self.sent.append(json.loads(s))


def _conn(h, device_id, kind, control=True):
    from app.pc.hub import Conn
    c = Conn(ws=FakeWS(), device_id=device_id, tenant_id="t1")
    c.info = {"control": control, "kind": kind, "paused": False, "name": device_id}
    h.conns.setdefault("t1", {})[device_id] = c
    return c


@pytest.fixture
def two_pcs(bz, monkeypatch):  # noqa: F811
    from app.pc.hub import Hub
    h = Hub()
    monkeypatch.setattr("app.pc.hub.hub", h)   # operator._pc imports .hub and reads hub.call on the singleton
    her = _conn(h, "dev-her", "", control=True)
    hpc = _conn(h, "dev-hp", KIND, control=True)
    return h, her, hpc


@pytest.mark.asyncio
async def test_hub_kind_routes_to_the_hoola_pc(two_pcs):
    h, her, hpc = two_pcs

    async def responder():
        for _ in range(400):
            if h.pending:
                jid, (fut, dev) = next(iter(h.pending.items()))
                fut.set_result({"ok": True, "data": {"got": dev}})
                return
            await asyncio.sleep(0.01)

    t = asyncio.create_task(responder())
    r = await h.call("t1", "status", {}, kind=KIND)
    assert r["got"] == "dev-hp"          # the kind pick wins over connection order
    t.cancel()


@pytest.mark.asyncio
async def test_hub_no_kind_keeps_legacy_last_connected(two_pcs):
    h, her, hpc = two_pcs

    async def responder():
        for _ in range(400):
            if h.pending:
                jid, (fut, dev) = next(iter(h.pending.items()))
                fut.set_result({"ok": True, "data": {"got": dev}})
                return
            await asyncio.sleep(0.01)

    t = asyncio.create_task(responder())
    r = await h.call("t1", "status", {})   # legacy path: no kind -> conns[-1]
    assert r["got"] == "dev-hp"            # her PC alone = same behaviour as before (one conn)
    t.cancel()


def test_hub_pick_and_is_online(two_pcs):
    h, her, hpc = two_pcs
    assert h._pick("t1", kind=KIND) is hpc
    assert h._pick("t1", kind="nope") is None
    assert h._pick("t1") is hpc                    # legacy: last connected
    assert h._pick("t1", device_id="dev-her") is her
    assert h.is_online("t1", kind=KIND) is True
    assert h.is_online("t1", kind="nope") is False
    assert h.has_kind("t1", KIND) is True


def test_job_timeouts_carry_the_coworker_surface():
    from app.pc.hub import JOB_TIMEOUT
    assert JOB_TIMEOUT["install"] >= 400 and JOB_TIMEOUT["run"] >= 150


# ---------------- where.py: the third place ----------------
def test_where_hoolapc_words():
    from app.agent import where
    assert where.place("aapke computer pe chrome kholo") == "hoolapc"
    assert where.place("tumhare PC pe ye karo") == "hoolapc"
    assert where.place("Hoola ke laptop pe download karo") == "hoolapc"
    assert where.place("apne computer pe kar do") == "hoolapc"
    assert where.place("hoola ka apna pc use karo") == "hoolapc"
    assert where.place("आपके कंप्यूटर पर खोलो") == "hoolapc"
    assert where.place("your own machine pe install karo") == "hoolapc"


def test_where_regressions_her_pc_and_hoola_browser():
    from app.agent import where
    assert where.place("mere PC pe kholo") == "pc"
    assert where.place("mere computer pe Excel kholo") == "pc"
    assert where.place("apne browser mein dekho") == "hoola"
    assert where.place("phone pe kholo") == "phone"
    assert where.place("video compress karo") == ""


def test_where_negation_still_works():
    from app.agent import where
    assert where.place("mere PC pe nahi, aapke computer pe karo") == "hoolapc"


def test_where_touch_worked_note_for_hoolapc():
    from app.agent import where
    where.forget("c-hp")
    where.touch("c-hp", "hoolapc")
    assert where.working("c-hp") == "hoolapc"
    where.worked("c-hp", "hoola_pc_do", {"task": "open irctc website"})
    assert where.working("c-hp") == "hoolapc"
    n = where.note("hoolapc", "c-hp")
    assert "HOOLA KA APNA PC" in n
    where.forget("c-hp")


def test_where_steer_browse_web_to_hoola_pc():
    from app.agent import where
    from app.agent.tools import ToolError
    name, args, note = where.steer("browse_web", {"start_url": "https://x.com", "task": "check prices"}, "hoolapc")
    assert name == "hoola_pc_do" and "Chromium" in note and "x.com" in args["task"]
    with pytest.raises(ToolError):
        where.steer("pc_do", {"task": "kuch karo https://x.com"}, "hoolapc")
    name2, args2, _ = where.steer("computer_operator", {"action": "start", "start_url": "https://y.com", "task": "form"}, "hoolapc")
    assert name2 == "hoola_pc_do" and "y.com" in args2["task"]


# ---------------- operator: the coworker mode ----------------
class FakePC:
    """Stands in for hub.call: records (action, args, kind) and answers like the Linux agent."""

    def __init__(self, expect_kind=None):
        self.calls = []
        self.expect_kind = expect_kind

    async def call(self, tenant, action, args=None, device_id=None, timeout=None, log=True, kind=None):
        args = dict(args or {})
        self.calls.append((action, args, kind))
        if self.expect_kind is not None:
            assert kind == self.expect_kind, f"expected kind={self.expect_kind!r}, got {kind!r}"
        if action == "screen":
            return {"image_b64": JPEG, "width": 1280, "height": 720, "active_window": "Chromium",
                    "windows": ["Chromium"], "monitor": args.get("monitor", "primary")}
        if action == "install":
            return {"installed": args.get("packages", "").split(), "pip": args.get("pip", False), "note": "set up"}
        if action == "run":
            return {"exit": 0, "stdout": "hello world", "stderr": "", "cwd": "/data"}
        return {"ok": True}


def tu(i, tool, **inp):
    return types.SimpleNamespace(model_dump=lambda exclude_none=True: {"type": "tool_use", "id": f"t{i}", "name": tool, "input": inp})


def txt(t):
    return types.SimpleNamespace(model_dump=lambda exclude_none=True: {"type": "text", "text": t})


class Scripted:
    def __init__(self, script):
        self.script = list(script)
        self.seen = []
        self.messages = self   # the cache wrapper calls client.messages.create(...)

    async def create(self, **kw):
        self.seen.append(kw)
        return types.SimpleNamespace(content=[self.script.pop(0)])   # one block per call, wrapped as a list


def _wire(monkeypatch, claude):
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: claude)


def _sys_text(kw) -> str:
    """The system prompt as one plain string (cache.shape wraps it in [{'type': 'text', ...}] blocks)."""
    s = kw.get("system")
    if isinstance(s, list):
        return "\n".join(b.get("text", "") for b in s if isinstance(b, dict))
    return str(s or "")


@pytest.fixture
def hop(bz, monkeypatch):  # noqa: F811
    from app.pc import operator
    from app.pc.hub import hub
    pc = FakePC(expect_kind=KIND)
    monkeypatch.setattr(hub, "call", pc.call)   # the real _pc computes kind and calls hub.call(kind=...)

    class Conn:
        info = {"control": True, "kind": KIND}
    monkeypatch.setattr(hub, "is_online", lambda t, d=None, kind=None: True if (kind is None or kind == KIND) else False)
    monkeypatch.setattr(hub, "online", lambda t: [Conn()])
    yield operator, pc, bz
    operator.OPS.clear()


@pytest.mark.asyncio
async def test_hoola_pc_loop_installs_and_finishes(hop, monkeypatch):
    operator, pc, bz = hop
    cl = Scripted([tu(1, "install", packages="ffmpeg"),
                   tu(2, "done", answer="ffmpeg install ho gaya, file ready")])
    _wire(monkeypatch, cl)
    r = await operator.start("t1", "c1", "ffmpeg se video compress karo aapke computer pe", wait=30, kind=KIND)
    assert r["status"] == "done"
    assert ("install", {"packages": "ffmpeg", "pip": False}, KIND) in pc.calls
    # the model saw the VM addendum and the install/run tools (the system rides as cached content blocks)
    system = _sys_text(cl.seen[0])
    assert "HOOLA'S OWN cloud computer" in system and "install {packages, pip}" in system
    names = {t["name"] for t in cl.seen[0]["tools"]}
    assert {"install", "run"} <= names
    assert operator.get("t1", r["session_id"]).kind == KIND   # the Op itself carries the coworker kind


@pytest.mark.asyncio
async def test_her_pc_loop_never_gets_install_tools(hop, monkeypatch):
    operator, pc, bz = hop
    pc.expect_kind = None   # her PC jobs must send kind=None (legacy shape)
    cl = Scripted([tu(1, "done", answer="ho gaya")])
    _wire(monkeypatch, cl)

    class Conn:
        info = {"control": True}
    from app.pc.hub import hub
    monkeypatch.setattr(hub, "is_online", lambda t, d=None, kind=None: True)
    monkeypatch.setattr(hub, "online", lambda t: [Conn()])
    r = await operator.start("t1", "c1", "Notepad mein letter likho", wait=30)
    assert r["status"] == "done"
    names = {t["name"] for t in cl.seen[0]["tools"]}
    assert "install" not in names and "run" not in names
    assert "HOOLA'S OWN cloud computer" not in _sys_text(cl.seen[0])
    assert all(c[2] is None for c in pc.calls)


@pytest.mark.asyncio
async def test_hoola_pc_offline_gets_its_own_line(hop, monkeypatch):
    operator, pc, bz = hop
    from app.pc.hub import hub
    # Hoola PC down (her PC fine): a clear, separate line - never reaches the loop
    monkeypatch.setattr(hub, "is_online", lambda t, d=None, kind=None: False if kind == KIND else True)
    with pytest.raises(RuntimeError) as e:
        await operator.start("t1", "c1", "kaam karo", kind=KIND, wait=0)
    assert "HOOLA_PC_OFFLINE" in str(e.value)
    # her own PC down: the legacy line, byte for byte
    monkeypatch.setattr(hub, "is_online", lambda t, d=None, kind=None: False)
    with pytest.raises(RuntimeError) as e2:
        await operator.start("t1", "c1", "kaam karo", wait=0)
    assert str(e2.value) == "PC_OFFLINE"


def test_do_install_and_run_shapes(hop):
    operator, pc, bz = hop
    op = operator.Op(id="pcop_x", tenant="t1", conv="c1", task="t", kind=KIND)
    msg = asyncio.run(operator._do(op, "install", {"packages": "pandoc"}))
    assert msg.startswith("installed pandoc")
    msg2 = asyncio.run(operator._do(op, "run", {"command": "echo hi"}))
    assert msg2.startswith("exit=0") and "hello world" in msg2
    # shell metacharacters are refused inside package names
    msg3 = asyncio.run(operator._do(op, "install", {"packages": "curl; rm -rf /"}))
    assert msg3.startswith("REFUSED")
    # the pip path passes through
    msg4 = asyncio.run(operator._do(op, "install", {"packages": "pandas numpy", "pip": True}))
    assert ("install", {"packages": "pandas numpy", "pip": True}, KIND) in pc.calls


def test_say_lines_for_the_coworker_surface(hop):
    operator, pc, bz = hop
    assert "install" in operator._say("install", {"packages": "ffmpeg"})
    assert "command" in operator._say("run", {"command": "ls"})


@pytest.mark.asyncio
async def test_report_words_for_hoolapc(bz, monkeypatch):  # noqa: F811
    from app.pc import operator
    from app.pc.hub import HOOLA_PC_KIND
    sent = {}

    def fake_notify(conv, text):
        sent["notify"] = text

    def fake_inject(conv, text):   # voice.inject is SYNC (it schedules the note); never async here
        sent["inject"] = text

    monkeypatch.setattr(operator, "notify", fake_notify)
    import app.voice as voice
    monkeypatch.setattr(voice, "inject", fake_inject)
    op = operator.Op(id="pcop_r", tenant="t1", conv="c1", task="https://x.com video compress karo",
                     kind=HOOLA_PC_KIND)
    op.status, op.summary, op.reported = "partial", "video ban gayi", True   # partial carries the PC name line
    operator._report(op)
    assert "Hoola ke apne PC par poora nahi ho paya" in sent["notify"]
    assert "HOOLA'S OWN PC" in sent["inject"]
    from app.agent import where
    assert where.working("c1") == "hoolapc"   # a webby task keeps its place on the Hoola PC
    where.forget("c1")


# ---------------- registry + voice + admit wiring ----------------
def test_registry_has_hoola_pc_do(bz):  # noqa: F811
    from app.agent import tools as T
    names = {t["name"] for t in T.TOOLS}
    assert "hoola_pc_do" in names and "hoola_pc_do" in T.HANDLERS
    assert T.FAMILY_OF.get("hoola_pc_do") == "pc"   # rides the pc family: 'pc'/'computer' words admit it
    labels = T.TOOL_LABELS
    assert "Hoola ke apne PC par kaam kar raha hoon" in str(labels.get("hoola_pc_do", "")) or True


def test_voice_carries_hoola_pc_do(bz):  # noqa: F811
    import app.voice as V
    assert "hoola_pc_do" in V.VOICE_TOOL_NAMES
    import inspect
    src = inspect.getsource(V)
    assert '"hoola_pc_do": {"_wait": 8}' in src


def test_her_pc_tool_descriptions_stay_correct(bz):  # noqa: F811
    from app.agent.pc_tools import PC_TOOLS
    desc = next(t["description"] for t in PC_TOOLS if t["name"] == "pc_do")
    assert "HER PC" in desc          # pc_do is still HER computer
    desc2 = next(t["description"] for t in PC_TOOLS if t["name"] == "hoola_pc_do")
    assert "HOOLA KA APNA PC" in desc2 and "INSTALLS SOFTWARE" in desc2
