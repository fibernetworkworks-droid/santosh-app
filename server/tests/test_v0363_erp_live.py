"""v0.363 ASLI ERP KAAM - Hoola really reads and really writes her ERP (owner: "I WANT ALL ERP WORK TO BE DONE BY
HOOLA BOTH READ AND WRITE ... COMPLEX AND VERY HARD").

Up to v0.362 the ERP desk produced papers. This makes it do the work. A read is one call. A WRITE IS NEVER ONE
CALL, and that is the whole design:

    plan  ->  dry run (before -> after, row by row)  ->  HER TAP  ->  batches  ->  verify  ->  report

These tests exist because a wrong write into a live ERP is not undoable by apology, so every guard below is
proved against a fake ERP rather than asserted in a prompt:

  - delete is refused at ANY size, because there is no safe way to offer it
  - more than MAX_ROWS in one go is refused, so a mistake stays small
  - execute before a dry run is refused
  - a production write needs the word "production" from her as well as her tap
  - the approval is tied to THOSE rows: change them afterwards and the run refuses
  - a resume never posts a done row twice - the property that makes a real migration safe
  - the before-image is captured, and a rollback plan says plainly which rows it CANNOT put back
"""
import json

import pytest

from app.enterprise import run as RUN

from .entfake import fake_call


@pytest.fixture()
def erp(env, monkeypatch):
    """A fake ERP on the odata rail: every 7th write fails, like a real load."""
    calls = []

    def answer(method, path, body):
        if method == "GET":
            return 200, {"name": "PURANA", "city": "Nagpur"}
        return (400, {"error": "field too long"}) if len(calls) % 7 == 0 else (201, {"ok": True})

    def fake(ep, method, path, body=None, params=None, page=0):
        calls.append((method, path, body))
        return answer(method, path, body)

    # v0.388: writes go through dialect.Call now (one session, for the CSRF token), reads still here.
    monkeypatch.setattr(RUN, "_odata_call", fake)
    monkeypatch.setattr(RUN.dialect, "Call", fake_call(calls, answer))
    RUN.set_endpoint("t1", "erp", "sap", "https://erp.example.com/odata", "SECRET", env="test")
    return calls


def _rows(n=14):
    return [{"id": f"V{i}", "name": f"Vendor {i}"} for i in range(n)]


# ---------------------------------------------------------------- the refusals
def test_delete_is_refused_at_any_size(erp):
    with pytest.raises(RUN.RunError, match="Mitane"):
        RUN.plan_write("t1", "erp", "sap", "DELETE_VENDORS", "create", [{"a": 1}])
    with pytest.raises(RUN.RunError):
        RUN.plan_write("t1", "erp", "sap", "Vendors", "delete", [{"a": 1}])


def test_a_load_bigger_than_the_cap_is_refused(erp):
    with pytest.raises(RUN.RunError, match=str(RUN.MAX_ROWS)):
        RUN.plan_write("t1", "erp", "sap", "Vendors", "create", [{"n": i} for i in range(RUN.MAX_ROWS + 1)])


def test_nothing_runs_before_a_dry_run(erp):
    r = RUN.plan_write("t1", "erp", "sap", "Vendors", "update", _rows(3), key_field="id")
    with pytest.raises(RUN.RunError):
        RUN.execute("t1", r["run"])
    with pytest.raises(RUN.RunError):
        RUN.approve("t1", r["run"])
    assert not [c for c in erp if c[0] in ("POST", "PATCH")]        # her ERP was never touched


def test_a_production_write_needs_the_word_as_well_as_the_tap(env, monkeypatch):
    monkeypatch.setattr(RUN, "_odata_call", lambda *a, **k: (200, {"name": "OLD"}))
    RUN.set_endpoint("t1", "erp", "sap", "https://erp.example.com/odata", "S", env="production")
    r = RUN.plan_write("t1", "erp", "sap", "Vendors", "update", _rows(2), key_field="id")
    RUN.dry_run("t1", r["run"])
    with pytest.raises(RUN.RunError, match="PRODUCTION"):
        RUN.approve("t1", r["run"])
    assert RUN.approve("t1", r["run"], confirm_env="production")["status"] == "running"


def test_the_approval_is_tied_to_those_exact_rows(erp):
    """Change the rows after she taps and the run must refuse - her Haan was for what she SAW."""
    from app.db import session
    from app.enterprise.models import EntRunRow
    r = RUN.plan_write("t1", "erp", "sap", "Vendors", "update", _rows(3), key_field="id")
    RUN.dry_run("t1", r["run"])
    with session() as s:
        row = s.scalars(__import__("sqlalchemy").select(EntRunRow).where(EntRunRow.run_id == r["run"])).first()
        row.idem = "tampered"
    with pytest.raises(RUN.RunError, match="badal"):
        RUN.approve("t1", r["run"])


# ---------------------------------------------------------------- the work itself
def test_dry_run_shows_before_and_after_and_writes_nothing(erp):
    r = RUN.plan_write("t1", "erp", "sap", "Vendors", "update", _rows(4), key_field="id")
    d = RUN.dry_run("t1", r["run"])
    assert d["status"] == "dry_run" and d["dikhaye"] == 4
    assert d["jhalak"][0]["ab"]["name"] == {"pehle": "PURANA", "baad": "Vendor 0"}
    assert not [c for c in erp if c[0] in ("POST", "PATCH")]


def test_a_run_goes_in_batches_and_reaches_a_terminal_state(erp):
    r = RUN.plan_write("t1", "erp", "sap", "Vendors", "update", _rows(14), key_field="id")
    RUN.dry_run("t1", r["run"])
    RUN.approve("t1", r["run"])
    first = RUN.execute("t1", r["run"], batch=6)
    assert first["baaki"] > 0 and first["status"] == "running"
    RUN.execute("t1", r["run"], batch=50)
    s = RUN.status("t1", r["run"])
    assert s["baaki"] == 0
    assert s["status"] in ("done", "failed")        # failed stays resumable, it does not hang on "running"
    assert s["hue"] + s["fail"] == 14


def test_a_resume_never_posts_a_done_row_twice(erp):
    """The property that makes a real migration safe."""
    r = RUN.plan_write("t1", "erp", "sap", "Vendors", "update", _rows(14), key_field="id")
    RUN.dry_run("t1", r["run"])
    RUN.approve("t1", r["run"])
    RUN.execute("t1", r["run"], batch=50)
    s1 = RUN.status("t1", r["run"])
    writes1 = len([c for c in erp if c[0] in ("POST", "PATCH")])
    RUN.execute("t1", r["run"], batch=50)           # a crash-resume
    writes2 = len([c for c in erp if c[0] in ("POST", "PATCH")])
    assert writes2 - writes1 == s1["fail"], "only the failures may be retried"
    assert RUN.status("t1", r["run"])["hue"] == 14


def test_the_rollback_plan_is_honest_about_what_it_cannot_undo(erp):
    r = RUN.plan_write("t1", "erp", "sap", "Vendors", "update", _rows(5), key_field="id")
    RUN.dry_run("t1", r["run"])
    RUN.approve("t1", r["run"])
    RUN.execute("t1", r["run"], batch=50)
    rb = RUN.rollback_plan("t1", r["run"])
    assert rb["wapas_ho_sakte"] + rb["nahi_ho_sakte"] == RUN.status("t1", r["run"])["hue"]
    assert rb["rows"] and "wapas" in rb["rows"][0]


# ---------------------------------------------------------------- the credential
def test_the_credential_is_sealed_and_never_readable(erp):
    from app.db import session
    from app.enterprise.models import EntEndpoint
    eps = RUN.endpoints("t1", "erp")
    assert eps[0]["auth"] and "SECRET" not in eps[0]["auth"]
    with session() as s:
        row = s.scalars(__import__("sqlalchemy").select(EntEndpoint)).first()
        assert "SECRET" not in (row.auth_enc or ""), "the clear value must not sit in the database"
    assert "auth_enc" not in json.dumps(eps)


def test_an_endpoint_must_be_https_and_a_system_of_that_job(env):
    with pytest.raises(RUN.RunError):
        RUN.set_endpoint("t1", "erp", "sap", "http://erp.example.com", "S")      # not https
    with pytest.raises(RUN.RunError):
        RUN.set_endpoint("t1", "erp", "shopify", "https://x.com", "S")           # not an ERP system


def test_chat_can_never_carry_the_credential():
    """The tool refuses the endpoint action outright: it is an app job, not a chat job."""
    from app.agent.enterprise_tools import ENTERPRISE_TOOLS
    do = [t for t in ENTERPRISE_TOOLS if t["name"] == "erp"][0]
    assert "endpoint" in do["input_schema"]["properties"]["action"]["enum"]
    assert "never here" in do["description"] or "chat mein nahi" in do["description"]


def test_version():
    from pathlib import Path

    from app.main import APP_VERSION
    assert APP_VERSION == "0.717.0"
    assert "0.717.0+716" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
