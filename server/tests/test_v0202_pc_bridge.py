"""v0.202 HOOLA PC CAN REACH MERA PC (owner: "hoola must run on its own container and can access
mera pc of user").

Hoola ka apna PC stays Hoola's own container (the v0.201 rule is untouched - nothing of it appears
on the Mera PC screen), and NOW while it works on its own VM it can also use the USER'S personal PC
for FILES through a code-enforced bridge:

- user_pc_search / user_pc_read: read-only looks at her PC, always via hub.call_personal (HER PC
  explicitly - the legacy last-connected pick can never land a bridge job on the wrong machine).
- user_pc_pull: her PC uploads the file to the server (its normal send_file), THIS VM fetches it with
  a signed expiring link into /data/Downloads.
- user_pc_push: THIS VM uploads the file with the new direction=to_pc, and the system raises her
  confirm card IN CODE (_push_to_user_pc -> _approval) before anything is written to her PC; her
  desktop then saves it into Santosh Inbox over the normal /api/pc/fetch path.
- HER PC's operator never sees the bridge tools (TOOLS untouched; HOOLA_TOOLS only).
- A missing personal PC comes back as an honest "user's PC is offline" tool result.
- /api/pc/files takes an optional direction form field; old desktops (no direction) keep to_phone.

Tests: tool surface (bridge tools only on the Hoola PC operator), search rides call_personal, pull
moves her file into the VM through the signed link, push refuses without her approval and lands in
her inbox with it, honest PC_OFFLINE, the upload endpoint's direction handling, the model-facing
descriptions teach the bridge, version pin.
"""
import asyncio
import secrets
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

KIND = "hoola_pc"
BRIDGE = {"user_pc_search", "user_pc_read", "user_pc_pull", "user_pc_push"}


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, s):
        self.sent.append(s)


def _conn(h, tenant, device_id, kind):
    from app.pc.hub import Conn
    c = Conn(ws=FakeWS(), device_id=device_id, tenant_id=tenant)
    c.info = {"control": True, "kind": kind, "paused": False, "name": device_id}
    h.conns.setdefault(tenant, {})[device_id] = c
    return c


@pytest.fixture
def hub2(bz, monkeypatch):  # noqa: F811
    from app.pc.hub import Hub
    h = Hub()
    monkeypatch.setattr("app.pc.hub.hub", h)
    return h


def _op():
    from app.pc.operator import Op
    return Op(id="pcop_" + secrets.token_hex(4), tenant="default", conv="conv-1",
              task="meri Excel Hoola ke PC pe kholo", kind=KIND)


def _tool_names():
    from app.pc.operator import TOOLS, HOOLA_TOOLS
    return [t["name"] for t in TOOLS], [t["name"] for t in HOOLA_TOOLS]


# ---------------- the tool surface: the bridge lives ONLY on Hoola's own PC ----------------

def test_bridge_tools_only_on_the_hoola_operator():
    her, hoola = _tool_names()
    assert not (set(her) & BRIDGE)                 # HER PC's operator never gets the bridge
    assert set(hoola) & BRIDGE == BRIDGE           # the Hoola PC operator has all four
    added = set(hoola) - set(her)
    assert added == BRIDGE | {"install", "run"}    # and they join only the v0.193 coworker tools


def test_her_operator_still_lacks_install_and_run():
    her, hoola = _tool_names()
    assert "install" not in her and "run" not in her
    assert "install" in hoola and "run" in hoola


def test_model_facing_descriptions_teach_the_bridge():
    from app.agent.pc_tools import PC_TOOLS
    by = {t["name"]: t for t in PC_TOOLS}
    assert "user_pc_pull" in by["hoola_pc_do"]["description"]
    assert "user_pc_push" in by["hoola_pc_do"]["description"]
    assert "user_pc_" not in by["pc_do"]["description"]   # her own tool teaches no bridge


# ---------------- search / read: read-only looks at her PC, routed by call_personal ----------------

@pytest.mark.asyncio
async def test_user_pc_search_rides_call_personal(hub2, monkeypatch):
    from app.pc import operator
    op = _op()
    seen = {}

    async def fake_call_personal(tenant, action, args=None, timeout=None):
        seen.update(tenant=tenant, action=action, args=args)
        if args and args.get("query") == "march bill":
            return {"results": [{"path": "C:/Bills/march bill.pdf", "size_text": "120 KB"}]}
        return {"results": []}

    monkeypatch.setattr(hub2, "call_personal", fake_call_personal)
    out = await operator._do(op, "user_pc_search", {"query": "march bill"})
    assert seen["action"] == "search" and seen["args"]["query"] == "march bill"
    assert "C:/Bills/march bill.pdf" in out and "USER'S PC" in out

    out = await operator._do(op, "user_pc_search", {"query": "nothing here"})
    assert "Nothing found" in out


@pytest.mark.asyncio
async def test_user_pc_read_rides_call_personal(hub2, monkeypatch):
    from app.pc import operator
    op = _op()
    seen = {}

    async def fake_call_personal(tenant, action, args=None, timeout=None):
        seen.update(tenant=tenant, action=action, args=args)
        return {"name": "note.txt", "text": "kirana ka hisab"}

    monkeypatch.setattr(hub2, "call_personal", fake_call_personal)
    out = await operator._do(op, "user_pc_read", {"path": "C:/notes/note.txt"})
    assert seen["action"] == "read" and seen["args"]["path"] == "C:/notes/note.txt"
    assert "note.txt" in out and "kirana ka hisab" in out


# ---------------- pull: her file lands in THIS VM through the signed link ----------------

@pytest.mark.asyncio
async def test_user_pc_pull_moves_her_file_into_the_vm(hub2, monkeypatch):
    from app.pc import operator
    op = _op()
    seen = {"personal": [], "vm": []}

    async def fake_call_personal(tenant, action, args=None, timeout=None):
        seen["personal"].append((action, args))
        return {"file_id": "file_x", "name": "march.xlsx"}

    async def fake_call(tenant, action, args=None, device_id=None, timeout=None, log=True, kind=None):
        seen["vm"].append((action, args, kind))
        return {"saved_path": "/data/Downloads/march.xlsx", "name": "march.xlsx"}

    monkeypatch.setattr(hub2, "call_personal", fake_call_personal)
    monkeypatch.setattr(hub2, "call", fake_call)
    import app.pc.service as pcs
    monkeypatch.setattr(pcs, "download_path", lambda fid, hours=None: f"/api/pc/files/{fid}?exp=1&sig=s")

    out = await operator._do(op, "user_pc_pull", {"path": "C:/Bills/march.xlsx"})
    assert seen["personal"] == [("send_file", {"path": "C:/Bills/march.xlsx"})]
    action, args, kind = seen["vm"][0]
    assert action == "save_file" and kind == KIND          # the fetch job goes to THIS VM (by kind)
    assert args["file_id"] == "file_x" and args["name"] == "march.xlsx"
    assert args["url"].startswith("/api/pc/files/file_x")  # signed expiring link, not the PC-fetch path
    assert "/data/Downloads/march.xlsx" in out


# ---------------- push: her approval first (in code), then the to_pc upload -> her inbox ----------------

@pytest.mark.asyncio
async def test_push_refuses_without_her_approval(hub2, monkeypatch):
    from app.pc import operator
    _conn(hub2, "default", "dev-her", "")      # her PC IS online - the refusal is the approval, not offline
    op = _op()
    calls = []

    async def fake_call(tenant, action, args=None, device_id=None, timeout=None, log=True, kind=None):
        calls.append(action)
        return {}

    async def fake_call_personal(tenant, action, args=None, timeout=None):
        calls.append(action)
        return {}

    monkeypatch.setattr(hub2, "call", fake_call)
    monkeypatch.setattr(hub2, "call_personal", fake_call_personal)

    async def denied(op_, what):
        return False

    monkeypatch.setattr(operator, "_approval", denied)
    out = await operator._do(op, "user_pc_push", {"path": "/data/Downloads/report.pdf"})
    assert out.startswith("REFUSED")
    assert calls == []                          # nothing moved without her tap


@pytest.mark.asyncio
async def test_push_with_approval_uploads_to_pc_and_lands_in_her_inbox(hub2, monkeypatch):
    from app.pc import operator
    _conn(hub2, "default", "dev-her", "")
    op = _op()
    seen = {"personal": [], "vm": [], "approval": ""}

    async def fake_call(tenant, action, args=None, device_id=None, timeout=None, log=True, kind=None):
        seen["vm"].append((action, args, kind))
        return {"file_id": "file_y", "name": "report.pdf"}     # the VM's to_pc upload

    async def fake_call_personal(tenant, action, args=None, timeout=None):
        seen["personal"].append((action, args))
        return {"saved_path": "C:/Santosh Inbox/report.pdf"}

    async def approved(op_, what):
        seen["approval"] = what
        return True

    monkeypatch.setattr(hub2, "call", fake_call)
    monkeypatch.setattr(hub2, "call_personal", fake_call_personal)
    monkeypatch.setattr(operator, "_approval", approved)

    out = await operator._do(op, "user_pc_push", {"path": "/data/Downloads/report.pdf"})
    assert "report.pdf" in seen["approval"] and "Santosh Inbox" in seen["approval"]
    assert seen["vm"] == [("send_file", {"path": "/data/Downloads/report.pdf"}, KIND)]
    action, args = seen["personal"][0]
    assert action == "save_file"                              # her PC fetches over its normal path
    assert args["file_id"] == "file_y" and args["url"] == "/api/pc/fetch/file_y"
    assert "Santosh Inbox" in out


@pytest.mark.asyncio
async def test_push_is_honest_when_her_pc_is_offline(hub2, monkeypatch):
    from app.pc import operator
    _conn(hub2, "default", "dev-hp", KIND)     # only the cloud PC: nobody to receive the file
    op = _op()
    out = await operator._do(op, "user_pc_push", {"path": "/data/Downloads/x.pdf"})
    assert "PC_OFFLINE" in out


# ---------------- read tools are honest when her PC is away ----------------

@pytest.mark.asyncio
async def test_user_pc_search_offline_comes_back_honest(hub2):
    from app.pc import operator
    op = _op()
    out = await operator._do(op, "user_pc_search", {"query": "bill"})
    assert "ERROR: PC_OFFLINE" in out           # the model is told the truth about HER PC, plainly


# ---------------- the upload endpoint carries the direction safely ----------------

@pytest.mark.asyncio
async def test_pc_upload_direction_to_pc(monkeypatch):
    import app.main as m
    import app.pc.service as pcs
    seen = {}

    def fake_device(request):
        return SimpleNamespace(tenant_id="default", id="dev-hp")

    async def fake_store(upload, tenant_id, device_id, direction, pc_path=""):
        seen.update(tenant=tenant_id, device=device_id, direction=direction, path=pc_path)
        return SimpleNamespace(id="file_1", name="out.pdf", size=5)

    monkeypatch.setattr(m, "_pc_device", fake_device)
    monkeypatch.setattr(pcs, "store_upload", fake_store)

    class _Up:
        filename = "out.pdf"

        async def read(self, n=0):
            return b""

    await m.pc_upload(request=None, file=_Up(), path="/data/Downloads/out.pdf", direction="to_pc")
    assert seen["direction"] == "to_pc" and seen["device"] == "dev-hp"

    await m.pc_upload(request=None, file=_Up(), path="x", direction="bogus")
    assert seen["direction"] == "to_phone"      # unknown value = the safe old behaviour


# ---------------- the version ritual ----------------

def test_version_pin():
    import app.main as m
    assert m.APP_VERSION == "0.282.0"
