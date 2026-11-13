"""v0.836 DESKTOP TEAM + HOOLA PC TEAM (owner: "GO DESKTOP TEAM + HOOLA PC TEAM --- PERFECT, SYSTEMATIC, SMOOTH
AND ADVANCE").

Before: one PC task per PERSON - a new pc_do cancelled whatever ran on ANY of her PCs, so her office PC, her home
PC and Hoola's own cloud PC could never work at the same time, she could not say which PC, and "band karo" never
reached a running PC task (the stop path had no branch for it).

Now: one task per PC. These tests hold:
- hub.find picks the PC she named (exact name / id, then every word of a short name), ambiguous = None;
- a task stays on ITS PC for every step (device_id rides each hub.call) and never jumps to another PC;
- two PCs work at once; a new task on the SAME PC replaces the old one (old pc_do behaviour) unless
  replace=False (PcBusy, the old one keeps going);
- pc_team gives each part its own PC, picks different FREE Hoola PCs for 'hoola' parts, never interrupts a busy
  PC, refuses one PC twice / unknown names with reasons, caps the team size, and shares one team id;
- 'band karo' (kaamstop.cancel) stops every running PC task, a named stop only that one;
- the new tools are registered in the 'pc' family, labelled, reachable on a call; vps-ops runs 1-4 Hoola PCs.
"""
import asyncio
import json
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

KIND = "hoola_pc"
ROOT = Path(__file__).resolve().parents[2]


class FakeWS:
    async def send_text(self, s):
        pass


def _conn(h, tenant, device_id, name, kind=None, control=True):
    from app.pc.hub import Conn
    c = Conn(ws=FakeWS(), device_id=device_id, tenant_id=tenant)
    c.info = {"name": name, "control": control, "paused": False, **({"kind": kind} if kind else {})}
    h.conns.setdefault(tenant, {})[device_id] = c
    return c


@pytest.fixture
def team(bz, monkeypatch):  # noqa: F811
    """A real Hub with four PCs: her office + home PCs and two of Hoola's own PCs. The operator's vision loop is
    replaced by a gate so tasks stay 'running' until the test lets them finish."""
    from app.pc import hub as H, operator
    h = H.Hub()
    monkeypatch.setattr(H, "hub", h)
    _conn(h, "t1", "dev-office", "Office PC")
    _conn(h, "t1", "dev-home", "Ghar Laptop")
    _conn(h, "t1", "dev-hp1", "Hoola PC", kind=KIND)
    _conn(h, "t1", "dev-hp2", "Hoola PC 2", kind=KIND)
    gate = asyncio.Event()

    async def fake_run(op):
        try:
            await gate.wait()
            op.status, op.summary = "done", f"done on {op.device_name}"
        except asyncio.CancelledError:
            op.status = "cancelled"
            raise
        finally:
            op.done_event.set()
    monkeypatch.setattr(operator, "_run", fake_run)
    monkeypatch.setattr(operator, "_event", lambda op: None)
    yield h, operator, gate
    for o in list(operator.OPS.values()):
        if o.task_obj and not o.task_obj.done():
            o.task_obj.cancel()
    operator.OPS.clear()


# ---------------- hub: the PC she named ----------------

def test_hub_find_by_name_words_and_id(team):
    h, _, _ = team
    assert h.find("t1", "Office PC").device_id == "dev-office"
    assert h.find("t1", "office").device_id == "dev-office"
    assert h.find("t1", "ghar wala laptop").device_id == "dev-home"
    assert h.find("t1", "dev-hp2").device_id == "dev-hp2"
    assert h.find("t1", "hoola pc 2").device_id == "dev-hp2"
    assert h.find("t1", "hoola") is None              # two Hoola PCs: ambiguous, never a guess
    assert h.find("t1", "kitchen") is None
    assert h.find("t1", "office", kind=KIND) is None   # kind filter: her office PC is not a Hoola PC
    assert h.find("t2", "office") is None              # never another person's PC


def test_hub_devices_and_pick_stays_on_device(team):
    h, _, _ = team
    d = {x["device_id"]: x for x in h.devices("t1")}
    assert d["dev-office"]["kind"] == "her_pc" and d["dev-hp2"]["kind"] == "hoola_pc" and d["dev-hp2"]["name"] == "Hoola PC 2"
    # a task on Hoola PC 2 stays there even though kind alone would pick Hoola PC 1
    assert h._pick("t1", "dev-hp2", KIND).device_id == "dev-hp2"
    del h.conns["t1"]["dev-hp2"]                      # it went offline: the step fails, it does NOT jump to PC 1
    assert h._pick("t1", "dev-hp2", KIND) is None
    assert h._pick("t1", None, KIND).device_id == "dev-hp1"   # old kind-only path unchanged


# ---------------- operator: one task per PC ----------------

@pytest.mark.asyncio
async def test_two_pcs_work_at_the_same_time(team):
    h, operator, gate = team
    a = await operator.start("t1", "c1", "Tally kholo", wait=0, pc="office")
    b = await operator.start("t1", "c1", "Excel bharo", wait=0, pc="ghar laptop")
    oa, ob = operator.get("t1", a["session_id"]), operator.get("t1", b["session_id"])
    assert oa.device_id == "dev-office" and ob.device_id == "dev-home"
    assert a["pc"] == "Office PC" and b["pc"] == "Ghar Laptop"
    assert oa.status == ob.status == "running"        # the second never cancelled the first
    assert {o.id for o in operator.running_all("t1")} == {oa.id, ob.id}
    gate.set()
    await asyncio.wait_for(asyncio.gather(oa.done_event.wait(), ob.done_event.wait()), 2)
    assert oa.status == ob.status == "done"


@pytest.mark.asyncio
async def test_same_pc_replaces_or_refuses(team):
    h, operator, gate = team
    a = await operator.start("t1", "c1", "pehla kaam", wait=0, pc="office")
    with pytest.raises(operator.PcBusy) as e:          # pc_team's way: never interrupt her running work
        await operator.start("t1", "c1", "doosra kaam", wait=0, pc="office", replace=False)
    assert e.value.op.id == a["session_id"] and operator.get("t1", a["session_id"]).status == "running"
    b = await operator.start("t1", "c1", "naya kaam", wait=0, pc="office")   # pc_do's way: the new one replaces
    await asyncio.sleep(0.05)
    assert operator.get("t1", a["session_id"]).status == "cancelled"
    assert operator.busy("t1", "dev-office").id == b["session_id"]


@pytest.mark.asyncio
async def test_unknown_pc_and_free_hoola_pc_pick(team):
    h, operator, gate = team
    with pytest.raises(RuntimeError) as e:
        await operator.start("t1", "c1", "kaam", wait=0, pc="kitchen")
    assert "PC_NOT_FOUND" in str(e.value) and "Office PC" in str(e.value)   # names what IS online
    x = await operator.start("t1", "c1", "ffmpeg", wait=0, kind=KIND)
    y = await operator.start("t1", "c1", "pandoc", wait=0, kind=KIND)   # PC 1 busy -> the FREE Hoola PC 2
    assert {operator.get("t1", x["session_id"]).device_id, operator.get("t1", y["session_id"]).device_id} == {"dev-hp1", "dev-hp2"}


@pytest.mark.asyncio
async def test_control_off_is_refused(team):
    h, operator, _ = team
    _conn(h, "t1", "dev-shop", "Shop PC", control=False)
    with pytest.raises(PermissionError):
        await operator.start("t1", "c1", "kaam", wait=0, pc="shop")


@pytest.mark.asyncio
async def test_every_step_goes_to_its_own_pc(team, monkeypatch):
    h, operator, _ = team
    seen = []

    async def fake_call(tenant, action, args=None, device_id=None, timeout=None, log=True, kind=None):
        seen.append((device_id, kind))
        return {}
    monkeypatch.setattr(h, "call", fake_call)
    op = operator.Op(id="pcop_x", tenant="t1", conv="c1", task="t", kind=KIND, device_id="dev-hp2")
    await operator._pc(op, "screen", {})
    assert seen == [("dev-hp2", KIND)]
    legacy = operator.Op(id="pcop_y", tenant="t1", conv="c1", task="t")   # an Op with no device keeps the old call
    await operator._pc(legacy, "screen", {})
    assert seen[-1] == (None, None)


# ---------------- pc_team ----------------

def _ctx():
    from app.agent.tools import Ctx
    return Ctx(tenant_id="t1", conversation_id="c1")


@pytest.mark.asyncio
async def test_pc_team_runs_each_part_on_its_own_pc(team):
    from app.agent.pc_tools import pc_team
    h, operator, gate = team
    r = await pc_team(_ctx(), goal="month-end", _wait=0, tasks=[
        {"pc": "office", "task": "Tally se ledger export karo"},
        {"pc": "ghar laptop", "task": "Excel mein ledger bharo"},
        {"pc": "hoola", "task": "GST portal se status dekho"},
        {"pc": "hoola", "task": "bank site se statement lo"}])
    assert r["team"].startswith("pcteam_") and not r["skipped"] and r["running"] == 4
    ops = [operator.get("t1", p["session_id"]) for p in r["parts"]]
    assert sorted(o.device_id for o in ops) == ["dev-home", "dev-hp1", "dev-hp2", "dev-office"]   # 4 different PCs
    assert {o.team for o in ops} == {r["team"]} and all(o.reported for o in ops)
    assert all(o.task.startswith("[Team job: month-end]") for o in ops)
    gate.set()
    await asyncio.wait_for(asyncio.gather(*(o.done_event.wait() for o in ops)), 2)


@pytest.mark.asyncio
async def test_pc_team_never_interrupts_and_explains(team):
    from app.agent.pc_tools import pc_team
    h, operator, gate = team
    mine = await operator.start("t1", "c1", "her own running work", wait=0, pc="office")
    r = await pc_team(_ctx(), _wait=0, tasks=[
        {"pc": "office", "task": "Tally kholo"},
        {"pc": "Ghar Laptop", "task": "Excel"},
        {"pc": "ghar laptop", "task": "Word bhi"},          # same PC twice -> refused with a reason
        {"pc": "kitchen", "task": "kuch bhi"}])
    parts = {p["pc"]: p for p in r["parts"]}
    assert parts["Office PC"]["status"] == "busy" and parts["Office PC"]["session_id"] == mine["session_id"]
    assert operator.get("t1", mine["session_id"]).status == "running"   # NOT interrupted
    assert parts["Ghar Laptop"]["status"] == "running"
    assert any("already has a part" in x for x in r["skipped"]) and any("kitchen" in x for x in r["skipped"])
    assert "could not start" in r["say"]


@pytest.mark.asyncio
async def test_pc_team_caps_and_empty(team, monkeypatch):
    from app.agent.pc_tools import pc_team
    from app.agent.tools import ToolError
    h, operator, _ = team
    monkeypatch.setenv("PC_TEAM_MAX", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(ToolError) as e:
        await pc_team(_ctx(), _wait=0, tasks=[{"pc": "office", "task": "aaa"}, {"pc": "ghar", "task": "bbb"},
                                              {"pc": "hoola", "task": "ccc"}])
    assert "At most 2" in str(e.value)
    with pytest.raises(ToolError):
        await pc_team(_ctx(), tasks=[])
    with pytest.raises(ToolError) as e2:                   # nothing could start at all -> one clear error
        await pc_team(_ctx(), _wait=0, tasks=[{"pc": "kitchen", "task": "aaa"}])
    assert "Online PCs" in str(e2.value)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pc_devices_lists_busy_state(team):
    from app.agent.pc_tools import pc_devices
    h, operator, _ = team
    await operator.start("t1", "c1", "Tally ka kaam", wait=0, pc="office")
    r = await pc_devices(_ctx())
    by = {p["name"]: p for p in r["pcs"]}
    assert r["count"] == 4 and by["Office PC"]["busy"] and "Tally" in by["Office PC"]["doing"]
    assert not by["Hoola PC 2"]["busy"] and by["Hoola PC 2"]["kind"] == "hoola_pc"


# ---------------- stop ----------------

@pytest.mark.asyncio
async def test_band_karo_stops_every_pc_and_named_stop_one(team):
    from app import kaamstop
    h, operator, _ = team
    a = await operator.start("t1", "c1", "Tally ledger export", wait=0, pc="office")
    b = await operator.start("t1", "c1", "Excel sheet bharo", wait=0, pc="ghar")
    out = await asyncio.to_thread(kaamstop.cancel, "t1", "excel wala band karo")
    await asyncio.sleep(0.05)
    assert operator.get("t1", b["session_id"]).status == "cancelled"
    assert operator.get("t1", a["session_id"]).status == "running"
    assert any("Excel" in x for x in out["stopped"])
    await asyncio.to_thread(kaamstop.cancel, "t1", "sab band karo")
    await asyncio.sleep(0.05)
    assert operator.get("t1", a["session_id"]).status == "cancelled"
    assert operator.running_all("t1") == []


@pytest.mark.asyncio
async def test_stop_all_helper(team):
    h, operator, _ = team
    await operator.start("t1", "c1", "a", wait=0, pc="office")
    await operator.start("t1", "c1", "b", wait=0, kind=KIND)
    assert operator.stop_all("t1") == 2


# ---------------- wiring ----------------

def test_registry_family_labels_voice(bz):  # noqa: F811
    from app.agent import tools as T
    from app.agent.labels_en import LABELS_EN
    from app import voice
    names = {t["name"]: t for t in T.TOOLS}
    for n in ("pc_team", "pc_devices"):
        assert n in names and n in T.HANDLERS and T.FAMILY_OF[n] == "pc"
        assert T.TOOL_LABELS.get(n) and LABELS_EN.get(n)
        assert voice.call_route(n) in ("declared", "kaam")
    assert "pc" in names["pc_do"]["input_schema"]["properties"]
    assert "pc" in names["hoola_pc_do"]["input_schema"]["properties"]
    assert len(T.TOOLS) == 630   # +1 hoola_pc_batch (v0.885); 627 + pc_team + pc_devices (v0.836 DESKTOP TEAM)


def test_prompt_and_vps_ops_team_shapes():
    from app.agent import prompts
    assert "DESKTOP TEAM (v0.836)" in Path(prompts.__file__).read_text()
    wf = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert 'case "$LINES_IN" in 1|2|3|4) PCS=$LINES_IN ;; *) PCS=1 ;; esac' in wf
    assert 'C=hoola-pc-$i; V=hoola-pc-$i-data; NM="Hoola PC $i"' in wf   # PC 1 keeps its old container + pairing
    assert 'case "$PC_IN" in [1-4]-*)' in wf
    compose = (ROOT / "desktop-linux/docker-compose.yml").read_text()
    assert 'profiles: ["team"]' in compose and "HOOLA_PC_NAME: Hoola PC 2" in compose


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.889.0"
