"""v0.882 PC JOB YAAD: a PC keeps its last job card after the task ends (any chat / call continues it), and a long
task with nothing new done is told, then handed to the rescue."""
import inspect
import time
import types

from app.pc import steady, rescue


def _op(**kw):
    base = dict(id="pcop_x", tenant="t1", device_id="d1", device_name="FNW-FLOW", conv="conv_a", task="Aadhaar download",
                status="partial", step=9, progress=[{"step": 2, "text": "opened uidai.gov.in", "n": 1},
                                                    {"step": 5, "text": "typed 'Aadhaar number box'", "n": 1}],
                opened_urls={"uidai.gov.in": 2}, window="myAadhaar - Chrome", reason="waiting for her number",
                summary="", carry="", kind="")
    base.update(kw)
    return types.SimpleNamespace(**base)


def setup_function(_):
    steady.JOBS.clear()


def test_card_kept_after_end_and_given_to_the_next_task():
    card = steady.remember(_op())
    assert card and card["pc"] == "FNW-FLOW" and "opened uidai.gov.in" in card["done"]
    nxt = _op(id="pcop_y", conv="conv_other_call", task="ab number daalo", progress=[], opened_urls={}, carry="")
    assert steady.carry_job(nxt)
    assert nxt.carry.startswith("EARLIER WORK") and "opened uidai.gov.in" in nxt.carry and "do NOT redo" in nxt.carry
    assert nxt.opened_urls == {"uidai.gov.in": 2}


def test_card_chains_when_continued_and_expires(monkeypatch):
    steady.remember(_op())
    nxt = _op(id="pcop_y", task="number daalo", progress=[{"step": 1, "text": "typed number", "n": 1}],
              carry="EARLIER WORK on this PC ...")
    card = steady.remember(nxt)
    assert card["done"][:2] == ["opened uidai.gov.in", "typed 'Aadhaar number box'"] and card["done"][-1] == "typed number"
    steady.JOBS[("t1", "d1")]["at"] = time.time() - 46 * 60
    assert steady.job_for("t1", "d1") is None


def test_no_card_for_empty_task_or_other_tenant():
    assert steady.remember(_op(progress=[])) is None
    steady.remember(_op())
    assert steady.job_for("t2", "d1") is None and steady.job_block("t2") == ""


def test_job_block_for_the_manager():
    steady.remember(_op())
    b = steady.job_block("t1")
    assert "THE LAST JOB" in b and "FNW-FLOW" in b and "waiting for her number" in b and "CONTINUES" in b
    src = inspect.getsource(__import__("app.agent.santosh", fromlist=["x"]))
    assert "job_block(tenant_id)" in src


def test_card_masks_secret_numbers(monkeypatch):
    from app import pii
    monkeypatch.setattr(pii, "mask_sensitive", lambda t: str(t).replace("SECRET", "****"))
    steady.remember(_op(task="Aadhaar SECRET download", reason="stopped at SECRET"))
    c = steady.JOBS[("t1", "d1")]
    assert "SECRET" not in c["goal"] and "SECRET" not in c["why"]


def test_drift_note_then_rescue_flag(monkeypatch):
    op = _op(step=0, progress=[], task="mobile under 2000")
    assert steady.drift(op) == ""
    notes = []
    for s in range(1, 26):
        op.step = s
        notes.append(steady.drift(op))
    said = [n for n in notes if n]
    assert len(said) == 2 and "12 steps" in said[0] and getattr(op, "drift_stuck", False)
    op.progress.append({"step": 26, "text": "clicked filter", "n": 1})
    op.step = 26
    assert steady.drift(op) == "" and op._drift_said == 0          # real progress resets the count


def test_rescue_reads_drift_and_wiring():
    src = inspect.getsource(rescue.observe)
    assert "drift_stuck" in src
    from app.pc import operator
    s = inspect.getsource(operator)
    assert "steady.drift(op)" in s and "_sd.carry_job(op)" in s and "_sd.remember(op)" in s and "drifts=%d" in s
    from app.config import Settings
    assert Settings.model_fields["pc_job_memory_min"].default == 45.0
    assert Settings.model_fields["pc_drift_steps"].default == 12


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.88")
