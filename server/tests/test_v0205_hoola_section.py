"""v0.205 HOOLA PC AND MERA PC ARE DIFFERENT SECTIONS (owner: "NOW HOOAL PC AND MERA PC IS
DIFFRENT SECTIONS").

v0.201 removed the Hoola PC from the Mera PC screen entirely (correct: Mera PC is ONLY the
user's personal PC) - which left Hoola's own cloud PC invisible in the app. This version makes
them TWO DIFFERENT SECTIONS, each with its own endpoint and its own screen:

- service.hoola_devices()  = the mirror of devices(): ONLY kind "hoola_pc", never a personal PC.
- service.hoola_jobs()     = the mirror of the v0.201-filtered jobs(): ONLY the Hoola PC's work.
- GET /api/pc/hoola + /api/pc/hoola/jobs feed the phone's new "Hoola ka PC" section;
  /api/pc/devices + /api/pc/jobs stay personal-only (the v0.201 rule byte-untouched).
- Flutter: NEW HoolaPcScreen - read-only by design (no pairing, no search, no file buttons:
  the Hoola PC is Hoola infrastructure, it pairs itself), plus the "Hoola ka PC" profile entry
  right next to "Mera PC".

Tests: hoola_devices picks only the cloud PC on the stored-info and live-conn paths while
devices() stays personal-only (both directions, same DB), hoola_jobs shows only the Hoola PC's
work while jobs() shows only hers, empty cases, endpoint shapes, version pin.
"""
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


def _mk_job(tenant, job_id, device_id, summary, status="done"):
    from app.db import PcJob, session as db_session
    with db_session() as s:
        s.add(PcJob(id=job_id, tenant_id=tenant, device_id=device_id, action="open_url",
                    summary=summary, status=status))


# ---------------- hoola_devices() is the Hoola PC ONLY ----------------

def test_hoola_devices_shows_only_the_cloud_pc(hub2):
    from app.pc import service
    _mk_device("default", "dev-her", {"name": "Office PC", "os": "Windows 11", "version": "1.4.0"})
    _mk_device("default", "dev-hp", {"name": "Hoola PC", "os": "Linux (Hoola PC)", "version": "1.0.0", "kind": KIND})

    out = service.hoola_devices("default")              # stored-info path
    assert [d["id"] for d in out] == ["dev-hp"]         # ONLY the cloud PC
    assert out[0]["kind"] == KIND and out[0]["online"] is False

    out = service.devices("default")                    # and the Mera PC endpoint stays personal-only
    assert [d["id"] for d in out] == ["dev-her"]
    assert out[0]["kind"] == ""


def test_hoola_devices_reads_the_live_conn(hub2):
    from app.pc import service
    _mk_device("default", "dev-hp", {"name": "Hoola PC", "kind": KIND})
    _conn(hub2, "default", "dev-hp", KIND)              # the container dialed home
    out = service.hoola_devices("default")
    assert len(out) == 1 and out[0]["online"] is True and out[0]["kind"] == KIND


def test_hoola_devices_never_leaks_a_personal_pc(hub2):
    from app.pc import service
    _mk_device("default", "dev-her", {"name": "Office PC"})          # only her PC exists
    assert service.hoola_devices("default") == []                    # the Hoola section shows nothing of hers
    _conn(hub2, "default", "dev-her", "")                            # even live
    assert service.hoola_devices("default") == []


# ---------------- hoola_jobs() is the Hoola PC's work ONLY ----------------

def test_hoola_jobs_show_only_the_hoola_pcs_work(hub2):
    from app.pc import service
    _mk_device("default", "dev-her", {"name": "Office PC"})
    _mk_device("default", "dev-hp", {"name": "Hoola PC", "kind": KIND})
    _mk_job("default", "job-her", "dev-her", "Chrome mein bill khola")
    _mk_job("default", "job-hp", "dev-hp", "ffmpeg install kiya")

    out = service.hoola_jobs("default")
    assert [j["id"] for j in out] == ["job-hp"]          # the Hoola section's own feed
    out = service.jobs("default")
    assert [j["id"] for j in out] == ["job-her"]         # her personal history stays personal (v0.201 intact)


def test_hoola_jobs_empty_when_no_hoola_pc(hub2):
    from app.pc import service
    _mk_device("default", "dev-her", {"name": "Office PC"})
    _mk_job("default", "job-her", "dev-her", "quotation print kiya")
    assert service.hoola_jobs("default") == []           # no cloud PC paired -> empty feed, never hers


# ---------------- the phone endpoints ----------------

def test_hoola_endpoints_serve_their_own_kind(hub2):
    import app.main as m
    from app.pc import service
    _mk_device("default", "dev-her", {"name": "Office PC"})
    _mk_device("default", "dev-hp", {"name": "Hoola PC", "kind": KIND})
    _mk_job("default", "job-hp", "dev-hp", "Chromium update")

    out = m.pc_hoola_devices(tenant="default")
    assert [d["id"] for d in out["devices"]] == ["dev-hp"]
    out = m.pc_hoola_jobs(tenant="default")
    assert [j["id"] for j in out["jobs"]] == ["job-hp"]
    # the personal endpoints stayed personal (same DB, same moment)
    assert [d["id"] for d in m.pc_devices(tenant="default")["devices"]] == ["dev-her"]
    assert service.hoola_devices("default")[0]["name"] == "Hoola PC"


# ---------------- the version ritual ----------------

def test_version_pin():
    import app.main as m
    assert m.APP_VERSION == "0.215.0"
