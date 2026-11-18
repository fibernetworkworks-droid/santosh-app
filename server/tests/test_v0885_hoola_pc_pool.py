"""v0.885 HOOLA PC POOL - every user gets a Hoola PC from a shared pool, her own locked folder on it, files and a proof
screenshot to her chat, and repeat jobs over her sheet with her tap after row 1 (owner: "EVERY HOOLA USER WILL HAS ITS
OWN HOOLA PC ... BEST FOR LEGACY PORTALS AND GOV PORTALS WHERE NEED A HUGE REPEATED MANUAL WORK", "Shared pool AND
HUMAN IN LOOP")."""
import asyncio
import base64
import importlib.util
import io
import shutil
import types
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0193_hoola_pc import FakePC, Scripted, _wire, tu

ROOT = Path(__file__).resolve().parents[2]
KIND = "hoola_pc"
JPEG = base64.b64encode(b"\xff\xd8\xff\xe0fakejpeg").decode()


def _agent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOOLA_DATA", str(tmp_path / "data"))
    spec = importlib.util.spec_from_file_location("hoola_agent_pool", ROOT / "desktop-linux" / "agent.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m, "_close_user_apps", lambda: 0)
    return m


# ---------------------------------------------------------------- the PC: one locked folder per user
@pytest.mark.skipif(shutil.which("openssl") is None or shutil.which("tar") is None, reason="needs openssl + tar")
def test_folders_lock_and_open_with_her_secret_only(tmp_path, monkeypatch):
    a = _agent(tmp_path, monkeypatch)
    d = a.DATA
    (d / "chrome").mkdir(exist_ok=True)
    (d / "chrome" / "Cookies").write_text("owner login")
    (d / "Downloads" / "old.pdf").write_text("owner file")
    A, B, SA, SB = "a" * 24, "b" * 24, "s" * 64, "t" * 64
    r = a.use_profile(A, SA, home=True)                    # the PC's first user: her old logins + files move in
    assert r["switched"] and (a.PROFILE / "Cookies").read_text() == "owner login"
    assert (d / "Downloads").is_symlink() and (d / "Downloads" / "old.pdf").read_text() == "owner file"
    (d / "work" / "mine.txt").write_text("A only")
    assert a.allowed(d / "work" / "mine.txt") and not a.allowed(d / "profiles" / B)
    r = a.use_profile(B, SB)                               # another user: A's folder is encrypted, readable copy gone
    assert r["locked_previous"] is True
    assert not (d / "profiles" / A).exists() and (d / "profiles" / (A + ".tar.enc")).exists()
    assert not a.allowed(d / "profiles" / (A + ".tar.enc")) and not a.allowed(d / "identity.json")
    assert not (d / "work" / "mine.txt").exists()          # B never sees A's files
    with pytest.raises(a.ActionError):
        a.use_profile(A, "x" * 64)                         # a wrong secret opens nothing and changes nothing
    assert a.CUR["key"] == B and (d / "profiles" / B).is_dir()
    r = a.use_profile(A, SA)
    assert r["opened"] == "opened" and (d / "work" / "mine.txt").read_text() == "A only"
    assert a.use_profile(A, SA)["switched"] is False       # same user again = nothing to do
    with pytest.raises(a.ActionError):
        a.Actions().do_read(str(d / "profiles" / (B + ".tar.enc")))


def test_background_commands_and_install_replay(tmp_path, monkeypatch):
    a = _agent(tmp_path, monkeypatch)
    act = a.Actions()
    j = act.do_run("echo started; sleep 0.3; echo finished", background=True)
    assert j["running"] and j["job"].startswith("job")
    import time
    for _ in range(40):
        st = act.do_run_status(j["job"])
        if not st["running"]:
            break
        time.sleep(0.1)
    assert st["exit"] == 0 and "finished" in st["output"]
    assert act.do_run_status()["jobs"][0]["job"] == j["job"]
    log = tmp_path / "installed.log"
    log.write_text("11-13 10:00 apt ffmpeg libreoffice-calc rc=0\n11-13 10:01 apt badpkg rc=100\n"
                   "11-13 10:02 pip pandas rc=0\n11-13 10:03 apt ffmpeg rc=0\n")
    assert a.replay_installs(log, dry=True) == ["ffmpeg", "libreoffice-calc", "pip:pandas"]   # failed + repeats out
    src = (ROOT / "desktop-linux" / "agent.py").read_text()
    assert a.VERSION == "1.6.0" and "threading.Thread(target=replay_installs" in src
    dk = (ROOT / "desktop-linux" / "Dockerfile").read_text()
    assert "useradd -m -u 1500 -s /bin/bash hoolawork" in dk and "openssl" in dk
    assert "never mkdir over them" in (ROOT / "desktop-linux" / "start.sh").read_text()
    # found in the real-Chromium walk: a SIGTERM'd Chrome dropped a fresh login - a user switch closes it cleanly first
    assert '"Browser.close"' in src and src.index('"Browser.close"') < src.index("_chrome.terminate()")
    assert 'PROFILE = Path("/tmp/hoola-check-profile")' in src     # the deploy check never opens a user's folder


# ---------------------------------------------------------------- the server: the pool
class _Conn:
    def __init__(self, dev, tenant, name="Hoola PC"):
        self.device_id, self.tenant_id, self.info = dev, tenant, {"kind": KIND, "name": name, "control": True}


@pytest.fixture
def pool_hub(bz, monkeypatch):  # noqa: F811
    from app.pc import operator
    from app.pc.hub import hub
    saved = dict(hub.conns)
    hub.conns.clear()
    hub.conns["owner"] = {"hp1": _Conn("hp1", "owner", "Hoola PC"), "hp2": _Conn("hp2", "owner", "Hoola PC 2")}
    yield hub
    hub.conns.clear()
    hub.conns.update(saved)
    operator.OPS.clear()
    from app.pc import pool
    pool.QUEUE.clear()
    pool.LAST.clear()


def test_every_user_sees_the_pool_and_her_last_pc_first(pool_hub, monkeypatch):
    from app.config import get_settings
    from app.pc import pool
    assert [c.device_id for c in pool_hub.hoola_pcs("other")] == ["hp1", "hp2"]
    assert pool_hub.is_online("other", kind=KIND)
    assert not pool_hub.is_online("other")                 # her own PC (none) is still offline: never the pool
    pool.LAST["other"] = "hp2"
    assert pool.pick("other").device_id == "hp2"
    assert pool.profile_key("a") != pool.profile_key("b") and pool.profile_key("a") == pool.profile_key("a")
    assert len(pool.profile_secret("a")) == 64 and pool.profile_secret("a") != pool.profile_key("a")
    monkeypatch.setattr(get_settings(), "hoola_pc_pool", False)
    assert pool_hub.hoola_pcs("other") == [] and not pool_hub.is_online("other", kind=KIND)


@pytest.mark.asyncio
async def test_a_task_for_another_user_switches_the_pc_to_her_folder(pool_hub, monkeypatch):
    from app.pc import operator, pool
    pc = FakePC(expect_kind=KIND)
    monkeypatch.setattr(pool_hub, "call", pc.call)
    _wire(monkeypatch, Scripted([tu(1, "done", answer="form bhar diya")]))
    r = await operator.start("other", "c9", "GST portal par form bharo", wait=30, kind=KIND)
    assert r["status"] == "done"
    prof = [c for c in pc.calls if c[0] == "profile"]
    assert prof and prof[0][1]["key"] == pool.profile_key("other") and prof[0][1]["home"] is False
    assert prof[0][1]["secret"] == pool.profile_secret("other")
    op = operator.get("other", r["session_id"])
    assert op.proof.get("file_id")                          # the screen at the end, as a chat file
    assert pool.LAST["other"] == op.device_id


@pytest.mark.asyncio
async def test_all_busy_means_a_queue_never_taking_over_someone_else(pool_hub, monkeypatch):
    from app.pc import operator, pool
    hold = asyncio.Event()

    async def slow(o):
        await hold.wait()
        o.status = "done"
        o.done_event.set()
    monkeypatch.setattr(operator, "_run", slow)
    pool_hub.conns["owner"].pop("hp2")
    first = await operator.start("owner", "c1", "kaam ek", wait=0, kind=KIND)
    assert first["status"] == "running"
    second = await operator.start("other", "c2", "kaam do", wait=0, kind=KIND)
    assert second["status"] == "queued" and second["queue_place"] == 1
    assert "in line" in second["say"]
    assert operator.get("owner", first["session_id"]).status == "running"   # never replaced by another user
    hold.set()
    op2 = operator.get("other", second["session_id"])
    await asyncio.wait_for(op2.done_event.wait(), 10)
    assert op2.status == "done" and op2.device_id == "hp1" and not pool.QUEUE


@pytest.mark.asyncio
async def test_send_to_chat_gives_her_the_file(bz, monkeypatch):  # noqa: F811
    from app.pc import operator, pool, service as pcs
    from app.db import PcFile, session

    published = []
    monkeypatch.setattr(pool, "publish", lambda conv, f, title, source="hoola_pc": published.append((conv, f, title)))
    path = pcs.files_dir() / "upfile"
    path.write_bytes(b"%PDF-1.4 receipt")
    with session() as s:
        s.add(PcFile(id="file_rcpt1", tenant_id="owner", device_id="hp1", direction="to_pc", name="ack.pdf", size=16,
                     sha256="x", pc_path="/data/Downloads/ack.pdf", stored_path=str(path)))

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        assert action == "send_file" and args["path"] == "/data/Downloads/ack.pdf"
        return {"file_id": "file_rcpt1", "name": "ack.pdf"}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    op = operator.Op(id="pcop_x", tenant="other", conv="c5", task="t", kind=KIND, device_id="hp1")
    out = await operator._send_to_chat(op, "/data/Downloads/ack.pdf", "GST acknowledgement")
    assert "in her chat" in out and op.sent_files == ["ack.pdf"]
    assert published[0][0] == "c5" and published[0][2] == "GST acknowledgement"
    row = pcs.get_file("file_rcpt1")
    assert row.tenant_id == "other" and row.direction == "to_phone"   # HER download now, not the PC owner's


def test_batch_approval_never_covers_money_or_deletes():
    from app.pc import operator
    assert not operator._batch_needs_tap("Submit the application form")
    assert not operator._batch_needs_tap("Save the record")
    for w in ("Pay Rs 500 fee", "Delete the old entry", "Enter OTP", "install the plugin", "UPI payment"):
        assert operator._batch_needs_tap(w)


def test_prompt_and_tools_say_shared_pc_and_files():
    from app.pc import operator
    from app.agent.pc_tools import PC_TOOLS
    assert "THIS PC IS SHARED" in operator.HOOLA_PC_ADDENDUM and "send_to_chat" in operator.HOOLA_PC_ADDENDUM
    names = {t["name"] for t in operator.HOOLA_TOOLS}
    assert {"send_to_chat", "run_status"} <= names
    assert not ({"send_to_chat", "run_status"} & {t["name"] for t in operator.TOOLS})
    d = next(t for t in PC_TOOLS if t["name"] == "hoola_pc_do")["description"]
    assert "GOVERNMENT / LEGACY PORTAL" in d and "HER CHAT" in d and "shared pool" in d
    assert any(t["name"] == "hoola_pc_batch" for t in PC_TOOLS)


# ---------------------------------------------------------------- repeat jobs
def test_rows_from_excel_and_csv_and_blanks():
    import openpyxl
    from app.pc import batch
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "GSTIN", "Amount"])
    ws.append(["Ramesh", "27AAAAA0000A1Z5", 1500.0])
    ws.append([None, None, None])
    ws.append(["Sita", "27BBBBB0000B1Z5", 2200])
    out = io.BytesIO()
    wb.save(out)
    cols, rows = batch.rows_from_bytes("list.xlsx", out.getvalue())
    assert cols == ["Name", "GSTIN", "Amount"] and len(rows) == 2 and rows[0]["Amount"] == "1500"
    cols2, rows2 = batch.rows_from_bytes("list.csv", b"Name,City\nA,Pune\nB,Akola\n")
    assert rows2[1] == {"Name": "B", "City": "Akola"}
    ok, bad = batch.blanks("Fill {name} with {GSTIN} and {Phone}", cols)
    assert ok == ["name", "GSTIN"] and bad == ["Phone"]
    assert batch.fill("Fill {name} for {gstin}", cols, rows[1]) == "Fill Sita for 27BBBBB0000B1Z5"
    b = {"task": "Fill {Name}", "columns": cols, "rows": rows}
    assert batch.row_task(b, 0).startswith("REPEAT JOB row 1 of 2 (the FIRST row")
    assert "do it exactly like row 1" in batch.row_task(b, 1) and "Name = Sita" in batch.row_task(b, 1)


@pytest.mark.asyncio
async def test_batch_needs_her_tap_after_row_1_then_runs_every_row(bz, monkeypatch):  # noqa: F811
    from app.pc import batch, operator, pool
    started, published, told = [], [], []
    taps = [True]

    async def fake_start(tenant, conv, task, wait=0, kind="", pc="", quiet=False, batch_ok=False, **_):
        op = operator.Op(id=f"pcop_{len(started)}", tenant=tenant, conv=conv, task=task, kind=KIND, device_id="hp1")
        op.quiet, op.batch_ok = quiet, batch_ok
        op.status, op.summary = "done", f"row ok {len(started) + 1}"
        op.proof = {"url": "/api/pc/files/x?exp=1&sig=s"}
        op.done_event.set()
        operator.OPS[op.id] = op
        started.append((task, quiet, batch_ok, pc))
        return op.live()

    async def fake_tap(op, what):
        told.append(what)
        return taps.pop(0)
    monkeypatch.setattr(operator, "start", fake_start)
    monkeypatch.setattr(operator, "ask_tap", fake_tap)
    monkeypatch.setattr(pool, "publish", lambda conv, f, title, source="hoola_pc": published.append(title))
    r = await batch.create("tA", "c1", "Portal par {Name} ka form bharo", rows=[{"Name": "A"}, {"Name": "B"},
                                                                                {"Name": "C"}])
    assert r["rows"] == 3 and r["state"] == "row1"
    await asyncio.wait_for(batch.RUNNERS[r["batch_id"]], 10)
    b = batch.load("tA", r["batch_id"])
    assert b["state"] == "done" and all(x["status"] == "done" for x in b["results"])
    assert started[0][1:3] == (False, False)                # row 1: she watches + approves its submit herself
    assert all(s[1:3] == (True, True) for s in started[1:]) and started[1][3] == "hp1"   # same PC, her tap covers them
    assert "Baaki 2 rows" in told[0] and published == ["Repeat job results (every row)"]
    import openpyxl
    data = batch.sheet_bytes(b)
    ws = openpyxl.load_workbook(io.BytesIO(data)).active
    assert [c.value for c in ws[1]][:3] == ["Row", "Name", "Result"] and ws.cell(4, 3).value == "Done"
    operator.OPS.clear()


@pytest.mark.asyncio
async def test_no_tap_no_rows_and_a_restart_pauses_never_resubmits(bz, monkeypatch):  # noqa: F811
    from app.pc import batch, operator
    started = []

    async def fake_start(tenant, conv, task, wait=0, kind="", pc="", quiet=False, batch_ok=False, **_):
        op = operator.Op(id=f"pcop_n{len(started)}", tenant=tenant, conv=conv, task=task, kind=KIND, device_id="hp1")
        op.status = "done"
        op.done_event.set()
        operator.OPS[op.id] = op
        started.append(task)
        return op.live()

    async def no_tap(op, what):
        return False
    monkeypatch.setattr(operator, "start", fake_start)
    monkeypatch.setattr(operator, "ask_tap", no_tap)
    r = await batch.create("tA", "c1", "Upload {File}", rows=[{"File": "a"}, {"File": "b"}])
    await asyncio.wait_for(batch.RUNNERS[r["batch_id"]], 10)
    b = batch.load("tA", r["batch_id"])
    assert b["state"] == "waiting_go" and len(started) == 1 and not b["go"]   # the model cannot run the rest
    with pytest.raises(batch.BatchError):
        batch.load("someone-else", r["batch_id"])
    # a job that was running when the server restarted: paused, the cut row marked for checking
    b["state"], b["go"] = "running", True
    batch.save(b)
    batch.RUNNERS.clear()
    assert batch.sweep_after_restart() == 1
    b = batch.load("tA", r["batch_id"])
    assert b["state"] == "paused" and b["results"][1]["status"] == "unknown"
    with pytest.raises(batch.BatchError):
        await batch.create("tA", "c1", "Upload {Missing} file now", rows=[{"File": "a"}])
    operator.OPS.clear()
