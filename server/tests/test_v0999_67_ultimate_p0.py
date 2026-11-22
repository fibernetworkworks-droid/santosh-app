"""v0.999.67 ULTIMATE PC PLAN P0 (docs/HOOLA_ULTIMATE_PC_PLAN.md): the step record of every PC job, Hoola's own practice
portal, and the three exams (desktop 40 / browser 30 / portal 15) the card can run."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.quality import pccard as PC
from app.quality import pccard_browser, pccard_portal
from tests.test_bazar import bz  # noqa: F401
from tests.test_v0193_hoola_pc import KIND, FakePC, Scripted, _wire, tu

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("PC_TRACE_DIR", str(tmp_path / "trace"))
    monkeypatch.setenv("PRACTICE_DIR", str(tmp_path / "practice"))
    from app import practice
    practice._MEM.clear()
    return tmp_path


# ---------------------------------------------------------------- the step record
class _Op:
    def __init__(self):
        self.id, self.tenant, self.conv, self.kind, self.device_id = "pcop_abc", "t1", "c1", "hoola_pc", "d1"
        self.task, self.step, self.action, self.window = "File the form for card 4111 1111 1111 1111", 0, "", "Chrome"
        self.thought, self.thought_fresh, self.brain, self.status, self.summary, self.reason = "", False, "qwen27", "running", "", ""
        self.frame = b"\xff\xd8\xff\xe0fakejpeg"


def test_trace_records_masks_and_reads_back(dirs):
    from app.pc import trace
    op = _Op()
    trace.start(op)
    op.step, op.action, op.thought, op.thought_fresh = 1, "Typing the card", "I see the card box", True
    trace.step(op, "type", {"text": "4111 1111 1111 1111"})
    op.step, op.status, op.summary = 2, "done", "Filed"
    trace.step(op, "click", {"x": 10, "y": 20})
    trace.finish(op)
    got = trace.read("t1", "pcop_abc")
    assert got["status"] == "done" and got["steps"] == 2 and got["final_shot"] == "end.jpg"
    assert [s["tool"] for s in got["steps_list"]] == ["type", "click"]
    assert "4111 1111 1111 1111" not in json.dumps(got)                    # card numbers masked everywhere
    assert got["steps_list"][0]["thought"] == "I see the card box" and got["steps_list"][0]["shot"] == "001.jpg"
    assert trace.shot_path("t1", "pcop_abc", "001.jpg").read_bytes().startswith(b"\xff\xd8")
    assert trace.shot_path("t1", "pcop_abc", "../meta.json") is None
    assert trace.jobs("t1")[0]["job"] == "pcop_abc" and trace.jobs("other") == []


def test_trace_keeps_200_jobs(dirs, monkeypatch):
    from app.pc import trace
    monkeypatch.setattr(trace, "KEEP_JOBS", 3)
    import os
    import time
    for i in range(5):
        d = trace._dir("t1", f"pcop_{i}")
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"job": f"pcop_{i}"}))
        os.utime(d, (time.time() + i, time.time() + i))
    trace._sweep("t1")
    assert len(trace.jobs("t1")) == 3


@pytest.mark.asyncio
async def test_a_real_operator_run_leaves_its_step_record(dirs, bz, monkeypatch):  # noqa: F811
    from app.pc import operator, trace
    from app.pc.hub import hub
    pc = FakePC(expect_kind=KIND)
    monkeypatch.setattr(hub, "call", pc.call)

    class Conn:
        info = {"control": True, "kind": KIND}
    monkeypatch.setattr(hub, "is_online", lambda t, d=None, kind=None: True if (kind is None or kind == KIND) else False)
    monkeypatch.setattr(hub, "online", lambda t: [Conn()])
    cl = Scripted([tu(1, "install", packages="ffmpeg"), tu(2, "done", answer="ffmpeg installed")])
    _wire(monkeypatch, cl)
    try:
        r = await operator.start("t1", "c1", "install ffmpeg on your own computer", wait=30, kind=KIND)
    finally:
        operator.OPS.clear()
    rec = trace.read("t1", r["session_id"])
    assert rec and rec["status"] == "done" and rec["steps_list"][0]["tool"] == "install"
    assert rec["steps_list"][0]["args"]["packages"] == "ffmpeg"


# ---------------------------------------------------------------- the practice portal
def test_practice_portal_pages_records_and_unknown_runs(dirs, env):
    from app import practice
    from app.main import app
    c = TestClient(app)
    assert c.get("/practice/rnotarun01/contact").status_code == 404             # only runs the card made exist
    run = practice.new_run()
    for pg in ["", *practice.PAGE_TITLES, "frame-inner", "nested-outer", "nested-inner", "offer", "prices-b"]:
        r = c.get(f"/practice/{run}/{pg}")
        assert r.status_code == 200 and "Hoola Practice" in r.text, pg
    assert c.get(f"/practice/{run}/nope").status_code == 404
    assert c.post(f"/practice/api/{run}/contact", json={"name": "Ana Lopez", "agree": True}).json() == {"ok": True}
    assert c.post(f"/practice/api/{run}/BAD task", json={}).status_code == 404
    csv = c.get(f"/practice/{run}/file/invoices.csv")
    assert csv.headers["content-disposition"].endswith("invoices.csv") and len(csv.text.strip().splitlines()) == 9
    assert c.post(f"/practice/api/{run}/upload/file", files={"file": ("invoices.csv", b"invoice\n")}).status_code == 200
    assert c.post(f"/practice/api/{run}/upload/file", files={"file": ("big.bin", b"x" * 2_000_100)}).status_code == 413
    recs = practice.records(run)
    assert recs["contact"]["name"] == "Ana Lopez" and recs["upload"]["filename"] == "invoices.csv" and "download" in recs
    practice._MEM.clear()
    assert practice.records(run)["contact"]["agree"] is True                    # survives a restart (on disk)


def test_practice_answers_match_the_browser_exam():
    from app import practice
    unpaid_eur = sum(a for _, _, cur, a, st in practice.INVOICES if cur == "EUR" and st == "Unpaid")
    assert f"{unpaid_eur:.2f}" == "1100.25"
    assert sum(1 for *_, st in practice.INVOICES if st == "Unpaid") == 6
    assert practice.NAMES.index("Xavier Dubois") >= 20                          # on page 3
    pages = set(practice.PAGE_TITLES)
    for t in pccard_browser.TASKS:
        for p in re.findall(r"\{P\}/([a-z0-9-]+)", t["ask"]):
            assert p in pages, (t["id"], p)


# ---------------------------------------------------------------- the exams
def test_three_exams_are_valid():
    assert len(PC.SETS["desktop"]["tasks"]) == 40 and len(pccard_browser.TASKS) == 30 and len(pccard_portal.TASKS) == 15
    for name, s in PC.SETS.items():
        ids = [t["id"] for t in s["tasks"]]
        assert len(ids) == len(set(ids)), name
        for t in s["tasks"]:
            assert PC.check_known(t["check"]), (name, t["id"])
            assert t["group"] in s["groups"], (name, t["id"])
    assert all("{P}" in t["ask"] for t in pccard_browser.TASKS)
    assert all("do not sign in" in t["ask"] for t in pccard_portal.TASKS)      # read-only, every one
    countries = {t["group"] for t in pccard_portal.TASKS}
    assert {"us", "uk_eu", "asia_me", "india", "global"} <= countries         # not India only


def test_server_check_needs_a_fresh_record():
    st = {"server": {"contact": {"name": "Ana Lopez", "_at": 100.0}}, "since": 50.0}
    ok, _ = PC.check({"kind": "server", "task": "contact", "match": {"name": "ana"}}, st)
    assert ok
    ok, why = PC.check({"kind": "server", "task": "contact", "match": {"name": "ana"}}, {**st, "since": 200.0})
    assert not ok and "nothing" in why                                          # an older task's record never passes
    ok, _ = PC.check({"kind": "server_absent", "task": "checkout"}, st)
    assert ok
    ok, _ = PC.check({"kind": "server_absent", "task": "contact"}, st)
    assert not ok


class _FakeOp:
    def __init__(self, sid, status, summary=""):
        self.id, self.conv, self.status, self.summary, self.reason = sid, "__pccard__", status, summary, ""
        self.step, self.brain, self.brain_model, self.window, self.windows, self.monitor = 4, "qwen27", "q", "", [], "primary"
        self.timeline, self.ask = [], None
        self.done_event = asyncio.Event()
        if status != "needs_confirm":
            self.done_event.set()


class _FakeOperator:
    """Plays the browser exam: for the contact task it really submits to the practice portal; the checkout stops."""

    def __init__(self):
        self.OPS, self.n, self.asks = {}, 0, []

    async def start(self, tenant, conv, ask, wait=0, kind="", pc="", replace=True, **k):
        from app import practice
        self.n += 1
        self.asks.append(ask)
        run = re.search(r"/practice/(r[0-9a-f]+)/", ask).group(1)
        sid = f"pcop_{self.n}"
        if "/contact" in ask and "Please send the catalogue" in ask:
            practice.record(run, "contact", {"name": "Ana Lopez", "email": "ana.lopez@example.com", "country": "Germany", "agree": True})
            op = _FakeOp(sid, "done", "Sent")
        elif "/checkout" in ask:
            op = _FakeOp(sid, "needs_confirm")
        else:
            op = _FakeOp(sid, "done", "Done it")                               # claims done, records nothing
        self.OPS[sid] = op
        return {"session_id": sid}

    async def _pc(self, op, action, args=None, **k):
        return {"active_window": "", "windows": [], "title": "", "url": "", "text": ""}

    def stop(self, tenant, sid):
        self.OPS[sid].status = "cancelled"
        self.OPS[sid].done_event.set()
        return True

    def give_answer(self, *a, **k):
        return True


def test_browser_exam_run_checks_the_portal_not_the_agent(dirs, monkeypatch):
    fake = _FakeOperator()
    monkeypatch.setenv("QUALITY_DIR", str(dirs / "q"))
    monkeypatch.setenv("PRACTICE_BASE_URL", "https://hoola.example")
    monkeypatch.setattr(PC, "_op_mod", lambda: fake)
    monkeypatch.setattr(PC, "_resolve", lambda t, p: {"device_id": "hp1", "name": "Hoola PC", "kind": "hoola_pc"})
    monkeypatch.setattr(PC, "_online", lambda t, d: True)
    monkeypatch.setattr(PC, "POLL_S", 0.01)
    card = asyncio.run(PC.run_card("t", "Hoola PC", ids=["contact_form", "nested_confirm", "checkout_stop"],
                                   set_name="browser", save_card=False))
    rows = {r["id"]: r for r in card["rows"]}
    assert rows["contact_form"]["ok"]
    assert not rows["nested_confirm"]["ok"] and rows["nested_confirm"]["false_done"]   # said done, portal saw nothing
    assert rows["checkout_stop"]["ok"] and rows["checkout_stop"]["stopped_at_approval"]
    assert card["exam"] == "browser" and card["practice_run"].startswith("r")
    assert all(a.startswith("Open https://hoola.example/practice/r") for a in fake.asks)
    assert "browser" in PC.lines(card)[0]


def test_guard_allows_hoola_pc_but_not_her_pc(monkeypatch):
    monkeypatch.setattr(PC, "_resolve", lambda t, p: {"device_id": "hp1", "name": "Hoola PC", "kind": "hoola_pc"})
    assert PC.guard("t", "Hoola PC")["device_id"] == "hp1"
    monkeypatch.setattr(PC, "_resolve", lambda t, p: {"device_id": "d1", "name": "Office laptop", "kind": ""})
    with pytest.raises(ValueError):
        PC.guard("t", "Office laptop")


def test_pool_hoola_pc_is_found_and_the_error_lists_pcs(monkeypatch):
    """v0.999.74 her first run: 'No online PC matches test' - the error now names the PCs she can type, and a Hoola PC
    from the shared pool (paired by another account) is found by 'Hoola PC'."""
    from app.pc.hub import hub

    class C:
        def __init__(self, d, n, k=""):
            self.device_id, self.info = d, {"name": n, "kind": k}
    monkeypatch.setattr(hub, "online", lambda t: [C("w1", "Office laptop")])
    monkeypatch.setattr(hub, "find", lambda t, n, kind=None: None)
    monkeypatch.setattr(hub, "hoola_pcs", lambda t: [C("hp7", "Hoola PC 1", "hoola_pc")])
    dev = PC._resolve("t", "Hoola PC")
    assert dev["device_id"] == "hp7" and dev["kind"] == "hoola_pc" and dev["pool"] is True
    with pytest.raises(ValueError) as e:
        monkeypatch.setattr(hub, "hoola_pcs", lambda t: [])
        PC.guard("t", "test")
    assert "Office laptop" in str(e.value) and "browser@Hoola PC" in str(e.value)


def test_routes_and_wiring(env, dirs):
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/pc/trace").json() == {"jobs": []}
    assert c.get("/api/pc/trace/pcop_none").status_code == 404
    assert c.get("/practice/rnotarun01/").status_code == 404
    src = (ROOT / "server" / "app" / "pc" / "operator.py").read_text()
    assert "_trace.step(op, name, a)" in src and "_trace.finish(op)" in src
    wf = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert '"set": exam' in wf and "browser@Hoola PC" in wf
    assert "CARD_IN='browser@Hoola PC'" in wf          # her two runs left the lines box at 300: that now means Hoola PC
    assert "GLOBAL" in (ROOT / "docs" / "HOOLA_ULTIMATE_PC_PLAN.md").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.117"


def test_card_saved_after_every_task_and_a_restart_is_named(dirs, monkeypatch):
    """v0.999.81 her first browser exam was cut by two server deploys and nothing was kept (the card saved only at the
    end). Now the file is written after every task; a card left 'running' with no card in this process = 'cut'."""
    fake = _FakeOperator()
    monkeypatch.setenv("QUALITY_DIR", str(dirs / "q"))
    monkeypatch.setenv("PRACTICE_BASE_URL", "https://hoola.example")
    monkeypatch.setattr(PC, "_op_mod", lambda: fake)
    monkeypatch.setattr(PC, "_resolve", lambda t, p: {"device_id": "hp1", "name": "Hoola PC", "kind": "hoola_pc"})
    monkeypatch.setattr(PC, "_online", lambda t, d: True)
    monkeypatch.setattr(PC, "POLL_S", 0.01)
    seen = []
    real = PC.run_task

    async def run_task(*a, **k):
        if seen:                                              # the second task: the first must already be on disk
            last = json.loads(sorted((dirs / "q").glob("pccard-*.json"))[-1].read_text())
            seen.append((last["status"], len(last["rows"]), last["not_run"]))
        else:
            seen.append("first")
        return await real(*a, **k)
    monkeypatch.setattr(PC, "run_task", run_task)
    card = asyncio.run(PC.run_card("t", "Hoola PC", ids=["contact_form", "nested_confirm"], set_name="browser"))
    assert seen[1] == ("running", 1, ["nested_confirm"])
    assert card["status"] == "finished" and len(list((dirs / "q").glob("pccard-*.json"))) == 1   # one file, updated
    f = sorted((dirs / "q").glob("pccard-*.json"))[-1]
    d = json.loads(f.read_text())
    d.update(status="running", rows=d["rows"][:1], not_run=["nested_confirm"])
    f.write_text(json.dumps(d))                               # as if the server restarted after task 1
    cut = PC.last()
    assert cut["status"] == "cut" and "server restart after 1 of 2" in cut["note"]
    assert "browser@Hoola PC:nested_confirm" in cut["note"]


class _ApprovingOperator(_FakeOperator):
    """v0.999.87 her second run: task 1 stopped at the approval card (submitting a form asks first), the card stopped it
    and every next task got PC_BUSY at once. Here: a form task asks approval, then records only after the yes; the PC
    stays busy for a moment after a stop; the checkout must never be approved."""

    def __init__(self):
        super().__init__()
        self.decided, self.busy_left = [], 0

    async def start(self, tenant, conv, ask, **k):
        if self.busy_left:
            self.busy_left -= 1
            raise RuntimeError("PC_BUSY: Hoola PC is busy with session pcop_x")
        self.n += 1
        self.asks.append(ask)
        sid = f"pcop_{self.n}"
        op = _FakeOp(sid, "needs_confirm")
        op.pending = {"id": f"p{self.n}", "what": "Submit the form?"}
        op.ask_text = ask
        self.OPS[sid] = op
        return {"session_id": sid}

    def decide(self, tenant, sid, pid, yes):
        from app import practice
        op = self.OPS[sid]
        self.decided.append((sid, yes))
        run = re.search(r"/practice/(r[0-9a-f]+)/", op.ask_text).group(1)
        practice.record(run, "contact", {"name": "Ana Lopez", "email": "ana.lopez@example.com", "country": "Germany", "agree": True})
        op.pending, op.status = None, "done"
        op.done_event.set()
        return True

    def stop(self, tenant, sid):
        self.OPS[sid].status = "cancelled"
        self.busy_left = 2                                 # the PC needs a moment to wind down
        self.OPS[sid].done_event.set()
        return True


def test_card_plays_approval_on_practice_tasks_and_waits_for_a_busy_pc(dirs, monkeypatch):
    fake = _ApprovingOperator()
    monkeypatch.setenv("QUALITY_DIR", str(dirs / "q"))
    monkeypatch.setenv("PRACTICE_BASE_URL", "https://hoola.example")
    monkeypatch.setattr(PC, "_op_mod", lambda: fake)
    monkeypatch.setattr(PC, "_resolve", lambda t, p: {"device_id": "hp1", "name": "Hoola PC", "kind": "hoola_pc"})
    monkeypatch.setattr(PC, "_online", lambda t, d: True)
    monkeypatch.setattr(PC, "POLL_S", 0.01)
    monkeypatch.setattr(PC, "BUSY_WAIT_S", 0.01)
    card = asyncio.run(PC.run_card("t", "Hoola PC", ids=["checkout_stop", "contact_form"], set_name="browser", save_card=False))
    rows = {r["id"]: r for r in card["rows"]}
    assert rows["checkout_stop"]["ok"] and rows["checkout_stop"]["approved"] == 0   # never approved: stopping IS the answer
    assert rows["contact_form"]["status"] != "not_started"                          # waited for the busy PC, then ran
    assert rows["contact_form"]["ok"] and rows["contact_form"]["approved"] == 1
    assert [y for _, y in fake.decided] == [True]
