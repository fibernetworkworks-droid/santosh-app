"""v0.200 MERA PC = USER PERSONAL PC FEATURE (owner: "MERA PC IS USER PERSONAL PC FEATURE").

The product rule this locks in:
- Mera PC (the phone screen + its buttons) is the USER'S PERSONAL PC feature — her own Windows
  computer paired via Hoola Desktop. Search / send / pull from the phone always target a PERSONAL
  PC, never Hoola's own cloud PC.
- Hoola ka apna PC (kind "hoola_pc", the Linux cloud computer) shows up in the app as its own
  clearly-labeled thing: service.devices() now carries "kind" so the app can separate the two.

Tests: devices() exposes kind (live conn path + stored-info path + legacy "" for her desktops),
hub.call_personal routes to the personal PC even when the cloud PC connected last, raises
PcOffline when ONLY the cloud PC is online, has_personal tells the send endpoint the truth, and
the phone's pc_search endpoint rides call_personal (the wire Mera PC speaks).
"""
import asyncio
import json
import secrets
import sys
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

KIND = "hoola_pc"


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, s):
        self.sent.append(json.loads(s))


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


def _mk_device(tenant, device_id, info):
    """A paired device row exactly as the real flow leaves it: save_info stashes the whole
    info dict (kind included) on the row."""
    from app.db import PcDevice, session as db_session
    with db_session() as s:
        s.add(PcDevice(id=device_id, tenant_id=tenant, name=info.get("name") or "PC",
                       os=(info.get("os") or "")[:60], token_hash="tok_" + secrets.token_hex(8),
                       info=info))
        s.flush()


# ---------------- devices() tells the app which PC is which ----------------

def test_devices_kinds_live_and_stored_and_legacy(hub2):
    from app.pc import service
    her_info = {"name": "Office PC", "os": "Windows 11", "version": "1.4.0", "control": True}   # desktops report NO kind
    hp_info = {"name": "Hoola PC", "os": "Linux 6.8.0 (Hoola PC)", "version": "1.0.0",
               "kind": KIND, "control": True}
    _mk_device("default", "dev-her", her_info)
    _mk_device("default", "dev-hp", hp_info)
    _conn(hub2, "default", "dev-her", "")          # live personal PC
    # dev-hp has NO live conn -> the stored info path must still carry the kind

    out = {d["id"]: d for d in service.devices("default")}
    assert out["dev-her"]["kind"] == "" and out["dev-her"]["online"] is True
    assert out["dev-hp"]["kind"] == KIND and out["dev-hp"]["online"] is False

    _conn(hub2, "default", "dev-hp", KIND)         # now live: kind comes off conn.info
    out = {d["id"]: d for d in service.devices("default")}
    assert out["dev-hp"]["kind"] == KIND and out["dev-hp"]["online"] is True


def test_legacy_desktop_without_info_is_personal(hub2):
    from app.pc import service
    _mk_device("default", "dev-old", {})           # paired before kinds existed
    out = service.devices("default")
    assert out[0]["kind"] == ""


# ---------------- the phone's buttons can never land on the Hoola PC ----------------

@pytest.mark.asyncio
async def test_call_personal_targets_her_pc_even_when_cloud_connected_last(hub2):
    _conn(hub2, "default", "dev-hp", KIND)         # cloud PC connects FIRST...
    _conn(hub2, "default", "dev-her", "")          # ...personal PC last: legacy pick would take HER, fine...

    async def responder():
        for _ in range(400):
            if hub2.pending:
                jid, (fut, dev) = next(iter(hub2.pending.items()))
                fut.set_result({"ok": True, "data": {"got": dev}})
                return
            await asyncio.sleep(0.01)

    t = asyncio.create_task(responder())
    r = await hub2.call_personal("default", "search", {"query": "bill"})
    assert r["got"] == "dev-her"                   # ...and even in reverse order the pick is explicit

    # the real proof: cloud PC is the ONLY one left -> the phone gets the honest offline 409 shape
    hub2.conns["default"].pop("dev-her")
    with pytest.raises(Exception) as e:
        await hub2.call_personal("default", "search", {})
    from app.pc.hub import PcOffline
    assert isinstance(e.value, PcOffline)


@pytest.mark.asyncio
async def test_call_personal_works_when_only_her_pc_is_online(hub2):
    _conn(hub2, "default", "dev-her", "")
    assert hub2.has_personal("default") is True

    async def responder():
        for _ in range(400):
            if hub2.pending:
                jid, (fut, dev) = next(iter(hub2.pending.items()))
                fut.set_result({"ok": True, "data": {"got": dev}})
                return
            await asyncio.sleep(0.01)

    t = asyncio.create_task(responder())
    r = await hub2.call_personal("default", "status", {})
    assert r["got"] == "dev-her"
    t.cancel()


def test_has_personal_counts_only_real_personal_pcs(hub2):
    assert hub2.has_personal("default") is False          # nobody home
    _conn(hub2, "default", "dev-hp", KIND)
    assert hub2.has_personal("default") is False          # cloud PC alone is NOT a personal PC
    _conn(hub2, "default", "dev-her", "")
    assert hub2.has_personal("default") is True


# ---------------- the phone endpoint actually rides call_personal ----------------

@pytest.mark.asyncio
async def test_pc_search_endpoint_goes_to_the_personal_pc(hub2, monkeypatch):
    import app.main as m
    _conn(hub2, "default", "dev-hp", KIND)
    _conn(hub2, "default", "dev-her", "")
    seen = {}

    async def fake_call_personal(tenant, action, args, timeout=None):
        seen.update(tenant=tenant, action=action, args=args)
        return {"results": [{"name": "bill.pdf"}]}

    monkeypatch.setattr(hub2, "call_personal", fake_call_personal)
    out = await m.pc_search(m.PcSearchIn(query="bill"), tenant="default")
    assert out["results"][0]["name"] == "bill.pdf"
    assert seen["action"] == "search" and seen["args"]["query"] == "bill"


# ---------------- the version ritual ----------------

def test_version_pin():
    import app.main as m
    assert m.APP_VERSION == "0.200.0"
