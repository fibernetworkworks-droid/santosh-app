"""v0.365 CRM DESK - the Salesforce desk, 100% read and write (owner: "MAKE CRM DESK CAN PERFROM 100 % READ AND
WRITE WORK", after checking crm_arch and finding it half-built next to the ERP desk).

The split that makes this job different from ERP is DATA versus CONFIGURATION:

    api="data"      records - leads, accounts, opportunities       /sobjects/...
    api="tooling"   the org's SHAPE - objects, fields, flows,      /tooling/sobjects/...
                    permission sets

A wrong record is one bad row. A wrong field or flow breaks the org for everyone, so `api` is a declared property
of the run, never guessed from the target, never the default, and a tooling change to production is logged as the
exception it is. Everything else - dry run, her tap, batches, idempotent resume, rollback material - is the same
engine as v0.363, which is the point of having one engine.
"""
import pytest

from app.enterprise import rules as R
from app.enterprise import run as RUN

from .entfake import fake_call
from app.enterprise import service as S


class _Pairs:
    """This suite records (method, path) pairs; the shared fake records triples. Adapt, don't duplicate."""

    def __init__(self, out):
        self.out = out

    def append(self, triple):
        self.out.append((triple[0], triple[1]))

    def __len__(self):
        return len(self.out)


@pytest.fixture()
def sf(env, monkeypatch):
    """A fake Salesforce that records every path, so the dialect itself is under test."""
    paths = []

    def answer(method, path, body=None):
        if "describe" in path:
            return 200, {"fields": [{"name": "Status", "label": "Status", "type": "picklist",
                                     "nillable": False, "updateable": True}]}
        if path.endswith("sobjects"):
            return 200, {"sobjects": [{"name": "Lead", "label": "Lead", "custom": False}]}
        if "query" in path:
            return 200, {"records": [{"Id": "00Q1"}]}
        if method == "GET":
            return 200, {"Status": "Open"}
        return 201, {"id": "x"}

    def fake(ep, method, path, body=None, params=None, page=0):
        paths.append((method, path))
        return answer(method, path, body)

    # v0.388: the write path is dialect.Call; `paths` still records every (method, path) either way.
    monkeypatch.setattr(RUN, "_odata_call", fake)
    monkeypatch.setattr(RUN.dialect, "Call",
                        fake_call(_Pairs(paths), answer))
    RUN.set_endpoint("t1", "crm_arch", "salesforce",
                     "https://my.salesforce.com/services/data/v61.0", "TOK", env="test")
    return paths


# ---------------------------------------------------------------- the desk
def test_the_crm_desk_covers_the_whole_practice():
    js = R.jobs_of("crm_arch")
    assert len(js) == 12
    for must in ("admin", "config", "automation", "apex", "integration", "data", "security", "reporting",
                 "testing", "release", "adoption", "support"):
        assert must in js, must
        assert set(js[must]["papers"]) <= set(R.ARTIFACTS), must


def test_the_desk_can_make_every_paper_its_parts_need(env):
    for k, v in R.jobs_of("crm_arch").items():
        out = S.draft("t1", "crm_arch", v["papers"][0], f"test {k}", job=k)
        assert out["hissa"]["job"] == k, k


def test_security_work_produces_a_matrix_which_it_could_not_before(env):
    """The Salesforce security model IS a matrix - profiles, permission sets, sharing. v0.362 had no such paper."""
    a = S.draft("t1", "crm_arch", "matrix", "profiles and permission sets", job="security")
    assert a["kind"] == "matrix"
    with pytest.raises(S.EnterpriseError):
        S.draft("t1", "crm_arch", "matrix", "x", job="apex")      # code work does not write a matrix


# ---------------------------------------------------------------- reads: the shape and her own SOQL
def test_describe_reads_the_shape_on_the_right_surface(sf):
    d = RUN.describe("t1", "crm_arch", "salesforce", "Lead")
    assert d["count"] == 1 and d["fields"][0]["name"] == "Status"
    assert sf[-1][1] == "sobjects/Lead/describe"
    RUN.describe("t1", "crm_arch", "salesforce", "Flow", api="tooling")
    assert sf[-1][1] == "tooling/sobjects/Flow/describe"


def test_soql_runs_but_only_select(sf):
    q = RUN.soql("t1", "crm_arch", "salesforce", "SELECT Id FROM Lead")
    assert q["count"] == 1 and sf[-1][1] == "query"
    for bad in ("DELETE FROM Lead", "UPDATE Lead SET x=1", "   drop table"):
        with pytest.raises(RUN.RunError, match="SELECT"):
            RUN.soql("t1", "crm_arch", "salesforce", bad)


# ---------------------------------------------------------------- writes: records vs configuration
def test_a_record_write_uses_the_data_surface(sf):
    r = RUN.plan_write("t1", "crm_arch", "salesforce", "Lead", "update",
                       [{"Id": "00Q1", "Status": "Working"}], key_field="Id")
    RUN.dry_run("t1", r["run"])
    RUN.approve("t1", r["run"])
    out = RUN.execute("t1", r["run"])
    assert out["api"] == "data" and out["hue"] == 1
    assert sf[-1][1] == "sobjects/Lead/00Q1"


def test_a_config_write_uses_the_tooling_surface(sf):
    r = RUN.plan_write("t1", "crm_arch", "salesforce", "CustomField", "create",
                       [{"FullName": "Lead.Foo__c"}], api="tooling")
    RUN.dry_run("t1", r["run"])
    RUN.approve("t1", r["run"])
    out = RUN.execute("t1", r["run"])
    assert out["api"] == "tooling"
    assert sf[-1][1] == "tooling/sobjects/CustomField"


def test_the_surface_is_declared_never_guessed(sf):
    """A target name must not decide risk: the same word on the wrong surface is a different act."""
    r = RUN.plan_write("t1", "crm_arch", "salesforce", "CustomField", "create", [{"FullName": "x"}])
    assert RUN.status("t1", r["run"])["api"] == "data"     # not silently promoted to tooling


def test_every_v0363_guard_still_holds_on_the_crm_desk(sf):
    with pytest.raises(RUN.RunError, match="Mitane"):
        RUN.plan_write("t1", "crm_arch", "salesforce", "DELETE_LEAD", "create", [{"a": 1}])
    with pytest.raises(RUN.RunError):
        RUN.plan_write("t1", "crm_arch", "salesforce", "Lead", "create",
                       [{"n": i} for i in range(RUN.MAX_ROWS + 1)])
    r = RUN.plan_write("t1", "crm_arch", "salesforce", "Lead", "update", [{"Id": "1"}], key_field="Id")
    with pytest.raises(RUN.RunError):
        RUN.execute("t1", r["run"])                         # no dry run yet


def test_a_production_config_change_still_needs_the_word(env, monkeypatch):
    monkeypatch.setattr(RUN, "_odata_call", lambda *a, **k: (200, {"Status": "Open"}))
    RUN.set_endpoint("t1", "crm_arch", "salesforce", "https://my.salesforce.com", "T", env="production")
    r = RUN.plan_write("t1", "crm_arch", "salesforce", "Flow", "update", [{"Id": "1"}], key_field="Id",
                       api="tooling")
    RUN.dry_run("t1", r["run"])
    with pytest.raises(RUN.RunError, match="PRODUCTION"):
        RUN.approve("t1", r["run"])
    assert RUN.approve("t1", r["run"], confirm_env="production")["status"] == "running"


def test_version():
    from pathlib import Path

    from app.main import APP_VERSION
    assert APP_VERSION == "0.559.0"
    assert "0.559.0+582" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
