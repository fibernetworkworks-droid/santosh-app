"""v0.201 MERA PC IS FOR THE USER'S PC, NOT FOR HOOLA'S OWN CONTAINER PC (owner, twice:
"MERA PC IS USER PERSONAL PC FEATURE" then "MERA PC IS FOR USER PC NOT FOR HOOLA OWN CONTAINER PC").

The product rule this locks in, in its final form:
- Mera PC (the phone screen + its buttons + its history) is the USER'S PERSONAL PC feature and
  NOTHING else: the Hoola PC (kind "hoola_pc", the Linux cloud container) NEVER appears in the
  devices list and its jobs NEVER appear in the personal-PC activity history. Hoola's own PC is
  Hoola infrastructure - it shows up in chat when Hoola works and is managed via vps-ops.
- The phone's search / send / pull still route to a PERSONAL PC explicitly (v0.200 hub.call_personal),
  and raise the honest PcOffline 409 when only the cloud PC is online.
- service.devices() filters the cloud PC OUT server-side, so even OLD APKs never show it.

Tests: devices() excludes the hoola_pc device on both the live-conn and stored-info paths while
personal PCs keep their kind field, jobs() hides the Hoola PC's work, hub.call_personal routes to
the personal PC even when the cloud PC connected first, raises PcOffline when ONLY the cloud PC is
online, has_personal tells the truth, the pc_search endpoint rides call_personal, version pin.
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


# ---------------- devices() is the user's personal PCs ONLY ----------------

def test_devices_hides_the_hoola_pc_on_both_paths(hub2):
    from app.pc import service
    her_info = {"name": "Office PC", "os": "Windows 11", "version": "1.4.0", "control": True}   # desktops report NO kind
    hp_info = {"name": "Hoola PC", "os": "Linux 6.8.0 (Hoola PC)", "version": "1.0.0",
               "kind": KIND, "control": True}
    _mk_device("default", "dev-her", her_info)
    _mk_device("default", "dev-hp", hp_info)

    out = service.devices("default")                    # dev-hp has NO live conn: stored-info path
    assert [d["id"] for d in out] == ["dev-her"]        # the cloud PC is not in the list, even offline
    assert out[0]["kind"] == "" and out[0]["online"] is False

    _conn(hub2, "default", "dev-her", "")
    _conn(hub2, "default", "dev-hp", KIND)             # now BOTH live: live-conn path
    out = service.devices("default")
    assert [d["id"] for d in out] == ["dev-her"]        # still personal-only, cloud PC online or not
    assert out[0]["online"] is True


def test_legacy_desktop_without_info_is_personal(hub2):
    from app.pc import service
    _mk_device("default", "dev-old", {})           # paired before kinds existed
    out = service.devices("default")
    assert out[0]["kind"] == ""


def test_jobs_hide_the_hoola_pcs_work(hub2):
    from app.db import PcJob, session as db_session
    from app.pc import service
    _mk_device("default", "dev-her", {"name": "Office PC"})
    _mk_device("default", "dev-hp", {"name": "Hoola PC", "kind": KIND})
    with db_session() as s:
        s.add(PcJob(id="job-her", tenant_id="default", device_id="dev-her", action="open_url",
                    summary="Chrome mein bill khola", status="done"))
        s.add(PcJob(id="job-hp", tenant_id="default", device_id="dev-hp", action="install",
                    summary="ffmpeg install kiya", status="done"))
    out = service.jobs("default")
    assert [j["id"] for j in out] == ["job-her"]        # her personal-PC history stays personal


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
    assert m.APP_VERSION == "0.296.0"
