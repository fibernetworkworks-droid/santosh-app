"""v0.540.0 LEADS NEEV - the store, the caps, the provenance gate, the hand-off, the forgetting.

Everything here runs OFFLINE against a fresh DB (the env fixture): no network, no model, no Google. The five
tools are registered and reachable, every row has its provenance or was never stored, the caps refuse AT PLAN
TIME with the cap named, and the engine still cannot send a single message.
"""
import asyncio

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)
from tests.test_api import client  # noqa: F401

from app import leadscap
from app.leads import rules as R
from app.leads import service as S
from app.leads.models import LeadContact, LeadRun, LeadOutreach, ensure_tables


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.804.0"
    from pathlib import Path
    pub = Path(__file__).resolve().parents[2] / "pubspec.yaml"
    assert "0.804.0+803" in pub.read_text()


# ---------------------------------------------------------------- the move did not break the old lane
def test_old_imports_still_work():
    from app.leads import SAMPLE_PREFIX, import_leads, normalize_phone          # the package re-exports
    from app.leads.importer import ImportResult
    assert SAMPLE_PREFIX == "91900000"
    assert normalize_phone("98765 43210") == "919876543210"
    assert normalize_phone("+91 9876543210") == "919876543210"
    assert normalize_phone("09876543210") == "919876543210"
    assert normalize_phone("not a phone") is None
    assert callable(import_leads) and ImportResult is not None
    from app.campaigns import SAMPLE_PREFIX as via_campaigns                     # campaigns.py's own import
    assert via_campaigns == SAMPLE_PREFIX


def test_tables_exist_and_register(env):
    ensure_tables()
    from app.db import session
    with session() as s:
        run = LeadRun(tenant_id="t1", ask="test")
        s.add(run)
        s.flush()
        assert run.id.startswith("lr_")
    with session() as s:
        assert s.get(LeadRun, run.id) is not None


# ---------------------------------------------------------------- the provenance gate
def test_no_row_without_provenance(env):
    with pytest.raises(S.LeadsError, match="source_url"):
        S.add_row("t1", {"name": "Sharma Dental", "phone": "9876500001"}, "HER_DATA", "")
    with pytest.raises(S.LeadsError, match="source_lane"):
        S.add_row("t1", {"name": "Sharma Dental", "phone": "9876500001"}, "SCRAPE_NOPE", "somefile.csv")
    row = S.add_row("t1", {"name": "Sharma Dental", "phone": "9876500001", "city": "Pune"},
                    "HER_DATA", "dentists-pune.csv")
    assert row["key_type"] == "phone_e164" and row["key_value"] == "919876500001"
    assert row["source_lane"] == "HER_DATA" and row["source_url"] == "dentists-pune.csv"
    assert row["parser_version"].startswith("v0.691")


def test_row_without_any_key_is_refused(env):
    with pytest.raises(S.LeadsError, match="bina key"):
        S.add_row("t1", {"city": "Pune"}, "HER_DATA", "x.csv")


# ---------------------------------------------------------------- the run: L0 her data
ROWS = [
    {"name": "Sharma Dental Care", "phone": "9876500001", "category": "dentist", "city": "Pune"},
    {"name": "Patil Eye Hospital", "phone": "+91 98765 00002", "category": "hospital", "city": "Pune"},
    {"name": "Joshi Clinic", "phone": "9876500001", "category": "clinic", "city": "Pune"},   # dup of row 1
    {"name": "No Phone Dental", "phone": "chhe", "category": "dentist", "address": "FC Road, Pune"},
    {"name": "Galat Number", "phone": "12345", "category": "dentist"},
    {"name": "Sirf Naam", "category": "dentist"},                                            # no key at all
]


def test_her_data_run_counters_and_dedup(env):
    out = S.run_her_data("t1", "Pune dentists file", ROWS, "dentists-pune.csv")
    assert out["ok"] is True
    r = out["run"]
    assert r["status"] == "DONE"
    assert r["found"] == 6 and r["kept"] == 3 and r["duped"] == 1 and r["refused"] == 2
    store = S.rows("t1")
    assert store["total"] == 3
    names = {x["name"] for x in store["rows"]}
    assert "Joshi Clinic" not in names                       # the duplicate never became a second row
    phone_row = next(x for x in store["rows"] if x["name"] == "Sharma Dental Care")
    assert phone_row["phone"] == "919876500001"              # E.164 via the house law
    no_phone = next(x for x in store["rows"] if x["name"] == "No Phone Dental")
    assert no_phone["key_type"] == "name_address" and no_phone["phone"] == ""
    for x in store["rows"]:
        assert x["source_lane"] == "HER_DATA" and x["source_url"] == "dentists-pune.csv"
    # a re-run of the SAME rows is a no-op (the BADA CATALOGUE idempotency law)
    again = S.run_her_data("t1", "same file again", ROWS, "dentists-pune.csv")
    assert again["run"]["kept"] == 0 and again["run"]["duped"] == 4 and again["run"]["refused"] == 2


def test_run_card_and_runs_list(env):
    out = S.run_her_data("t1", "ask", ROWS[:2], "f.csv")
    card = S.run_card(out["run"]["id"])
    assert card and card["tenant"] == "t1" and card["status"] == "DONE"
    assert card["provenance"]["parser_version"].startswith("v0.691")
    assert len(S.runs("t1")) == 1


# ---------------------------------------------------------------- the caps, refused AT PLAN TIME
def test_per_run_cap_refuses_before_any_row_is_written(env, monkeypatch):
    monkeypatch.setattr(env["settings"], "leads_max_rows_per_run", 3)
    before = S.rows("t1")["total"]
    out = S.run_her_data("t1", "bahut bada file", ROWS * 2, "bada.csv")
    assert out["ok"] is False
    assert out["run"]["status"] == "REFUSED"
    assert "3" in out["plan"]["cap_refusal"] and "cap" in out["plan"]["cap_refusal"].lower()
    assert S.rows("t1")["total"] == before                   # not one row was written


def test_per_run_cap_names_5000_in_the_default_refusal(env):
    with pytest.raises(leadscap.LeadsCapped) as e:
        leadscap.check_run("t1", 50_000)
    assert "5,000" in str(e.value) and "plan" in str(e.value).lower()


def test_per_day_cap_counts_kept_rows_and_survives_forget(env, monkeypatch):
    monkeypatch.setattr(env["settings"], "leads_max_rows_per_day", 4)
    monkeypatch.setattr(env["settings"], "leads_max_rows_per_run", 5000)
    r1 = S.run_her_data("t1", "pehli file", ROWS[:3], "f1.csv")           # keeps 2 (Joshi is a phone dup)
    assert r1["run"]["kept"] == 2
    r2 = S.run_her_data("t2", "doosri file", ROWS[:3], "f2.csv")          # another tenant: no sharing
    assert r2["run"]["kept"] == 2
    r3 = S.run_her_data("t1", "tisri file", [{"name": "X", "phone": "9876500099"},
                                             {"name": "Y", "phone": "9876500098"},
                                             {"name": "Z", "phone": "9876500097"}], "f3.csv")  # 2 kept + 3 > 4
    assert r3["ok"] is False and r3["run"]["status"] == "REFUSED"
    assert "20,000" not in r3["plan"]["cap_refusal"] and "4" in r3["plan"]["cap_refusal"]
    # forgetting the rows must not erase the day's memory
    S.forget("t1", all_rows=True)
    assert S.rows("t1")["total"] == 0
    w = leadscap.would_exceed("t1", 4)
    assert w["per_day"]["ok"] is False                                     # the ledger still says 3 kept


def test_usage_and_would_exceed(env):
    S.run_her_data("t1", "ask", ROWS[:2], "f.csv")
    u = leadscap.usage("t1")
    assert u["rows_kept"] == 2 and u["runs_started"] == 1
    assert leadscap.would_exceed("t1", 4998)["ok"] is True
    assert leadscap.would_exceed("t1", 4999)["ok"] is True
    w = leadscap.would_exceed("t1", 5001)                     # per-run cap: 5,001 planned > 5,000
    assert w["ok"] is False and w["per_run"]["ok"] is False and w["per_day"]["ok"] is True


# ---------------------------------------------------------------- lanes: no stub, no pretending
def test_unbuilt_lanes_refused_by_name(env):
    # v0.544.0: VENDOR is BUILT too (config-gated like SCRAPE is opt-in gated) - the plan section 4 ladder is
    # COMPLETE, so the by-name refusal witness is an UNKNOWN lane name; VENDOR's refusal is the CONFIG gate
    p = S.plan("t1", "ask", ["BOGUS"], "x")
    assert p["ok"] is False and any("koi lane hi nahi" in w for w in p["why"])
    p = S.plan("t1", "ask", ["VENDOR"], "x")
    assert p["ok"] is False and p["refused_lanes"] == ["VENDOR"]      # the config gate, the exact fix named
    assert any("LEADS_VENDOR_NAME" in w for w in p["why"])
    p = S.plan("t1", "ask", ["VENDOR", "BOGUS"], "x")
    assert p["ok"] is False and {"BOGUS", "VENDOR"} <= set(p["refused_lanes"])   # both named


def test_official_lanes_now_plan(env):
    # v0.541.0: REGISTRY (IndiaMART MCP) and OFFICIAL_API (the existing maps tools) are BUILT - a plan with
    # them and a place now says ok, with the caps in the card
    for lane in ("REGISTRY", "OFFICIAL_API"):
        p = S.plan("t1", "cement sellers Pune", [lane], "Pune")
        assert p["ok"] is True, p
        assert lane in p["lanes"] and "cap_check" in p


def test_vague_ask_gets_the_one_question(env):
    p = S.plan("t1", "", ["HER_DATA"], "")
    assert p["ok"] is False and p["need"] == R.ONE_QUESTION
    p = S.plan("t1", "sellers", ["REGISTRY"], "")                          # registry needs a place
    assert p["ok"] is False and "Kaunsa business" in p["need"]


# ---------------------------------------------------------------- export / opt-out / hand-off / forget
def test_export_has_provenance_and_excludes_opt_out(env):
    S.run_her_data("t1", "ask", ROWS[:2], "f.csv")
    store = S.rows("t1")
    S.set_opt_out("t1", store["rows"][0]["id"], True)
    out = S.export_csv("t1")
    assert out["rows"] == 1                                                # the opt-out row stayed home
    head = out["csv"].splitlines()[0]
    for col in ("source_lane", "source_url", "parser_version", "key_type", "key_value"):
        assert col in head
    assert "HER_DATA" in out["csv"] and "f.csv" in out["csv"]
    everything = S.export_csv("t1", opt_out=None)
    assert everything["rows"] == 2


def test_campaign_handoff_copies_consent_false_and_writes_ledger(env):
    S.run_her_data("t1", "ask", ROWS[:2], "f.csv")
    card = S.campaign_list("t1", "Dentist test")
    assert card["confirm_required"] is True            # v0.684.0: the first tap is the CONFIRM CARD
    out = S.campaign_list("t1", "Dentist test", confirm=True)
    assert out["ok"] is True and out["rows"] == 2
    assert "consent=False" in out["consent"]
    from app.db import Lead, LeadList, session
    with session() as s:
        ll = s.get(LeadList, out["list_id"])
        assert ll is not None and ll.valid == 2 and ll.opted_in == 0
        leads = s.query(Lead).filter(Lead.list_id == ll.id).all()
        assert len(leads) == 2 and all(l.opted_in is False for l in leads)
        extras = {l.phone: l.extra for l in leads}
        assert extras["919876500001"]["source_lane"] == "HER_DATA"
        ledger = s.query(LeadOutreach).filter(LeadOutreach.ref == ll.id).count()
        assert ledger == 2                                                 # the act is on the ledger
    # rows without a phone never enter a campaign list
    S.run_her_data("t1", "ask2", [{"name": "NoPhone", "address": "Karve Road Pune"}], "f2.csv")
    S.campaign_list("t1", "All")                        # the card tap, nothing built
    out2 = S.campaign_list("t1", "All", confirm=True)
    assert out2["rows"] == 2 and out2["rows_without_phone"] >= 1


def test_record_outreach_is_desk_side(env):
    row = S.add_row("t1", {"name": "A", "phone": "9876500010"}, "HER_DATA", "x.csv")
    n = S.record_outreach("t1", [row["id"]], "campaign_sent", "cmp_1", "campaign")
    assert n == 1
    ensure_tables()
    from app.db import session
    with session() as s:
        ev = s.query(LeadOutreach).filter(LeadOutreach.kind == "campaign_sent").first()
        assert ev is not None and ev.contact_id == row["id"] and ev.desk == "campaign"


def test_forget_deletes_rows_run_and_refs(env):
    out = S.run_her_data("t1", "ask", ROWS[:2], "f.csv")
    rid = out["run"]["id"]
    hand = S.campaign_list("t1", "L", run_id=rid, confirm=True)
    with pytest.raises(S.LeadsError):
        S.forget("t1")
    res = S.forget("t1", run_id=rid)
    assert res["deleted"] == 2
    assert S.run_card(rid) is None
    assert S.rows("t1")["total"] == 0
    ensure_tables()
    from app.db import session
    from app.leads.models import LeadListRef
    with session() as s:
        assert s.query(LeadListRef).filter(LeadListRef.list_id == hand["list_id"]).count() == 0


def test_tools_registered_and_family_wired(env):
    from app.agent.admit import EXTRA_KEYS
    from app.agent.leads_tools import LEADS_HANDLERS, LEADS_LABELS, LEADS_TOOLS
    from app.agent.tools import FAMILY_OF, HANDLERS, TOOLS, TOOL_LABELS
    names = {t["name"] for t in LEADS_TOOLS}
    assert names == {"leads_run", "leads_status", "leads_list", "leads_export", "leads_forget", "leads_enrich"}
    assert set(LEADS_LABELS) == set(LEADS_HANDLERS) == names
    global_names = {t["name"] for t in TOOLS}
    assert names <= global_names
    for n in names:
        assert n in HANDLERS and n in TOOL_LABELS and FAMILY_OF.get(n) == "leads", n
    assert "leads" in EXTRA_KEYS and "leads chahiye" in EXTRA_KEYS["leads"]
    # her words bring the right tools into view (the v0.393 reachability lesson)
    from app.agent import admit
    from app.config import get_settings
    plan = admit.plan_for("Pune mein dentists ke leads chahiye - meri file se banao", get_settings())
    seen = {t["name"] for t in plan.specs()} if plan else set()
    assert "leads_run" in seen


def test_employee_role_and_duty_wired(env):
    from app.employee.roles import DUTIES, ROLES, duty_of, kind_of
    assert "leads_sahayak" in ROLES and "leads_work" in DUTIES
    assert "leads_work" in ROLES["leads_sahayak"]["duties"]
    for t in ("leads_run", "leads_status", "leads_list", "leads_export", "leads_forget", "leads_enrich"):
        assert duty_of(t) == "leads_work", t                     # the prefix ("leads_",) mapped them
        assert kind_of(t) in ("read", "action", "big")
    assert "leads_desk" in __import__("app.employee.roles", fromlist=["PRESETS"]).PRESETS
    assert __import__("app.employee.roles", fromlist=["PRESETS"]).PRESETS["leads_desk"]["role"] == "leads_sahayak"
    # every duty tool exists in the registry (the house drift check)
    from app.agent.tools import HANDLERS
    for d in DUTIES.values():
        for t in d["tools"]:
            assert t in HANDLERS, t


def test_store_summary_counts(env):
    S.run_her_data("t1", "ask", ROWS[:2], "f.csv")
    s = S.store_summary("t1")
    assert s["rows"] == 2 and s["with_phone"] == 2 and s["with_email"] == 0
    assert s["by_lane"]["HER_DATA"] == 2


def test_api_endpoints_key_protected(env, monkeypatch):
    with client(monkeypatch, env, api_key="secret") as c:
        assert c.get("/api/leads").status_code == 401
        h = {"Authorization": "Bearer secret"}
        ov = c.get("/api/leads", headers=h).json()
        assert ov["store"]["rows"] == 0 and "never" in ov and "HER_DATA" in ov["lanes_built"]
        r = c.post("/api/leads/runs/her-data", headers=h,
                   json={"ask": "file", "rows": ROWS[:2], "source_name": "f.csv"})
        assert r.status_code == 200 and r.json()["run"]["kept"] == 2
        rows = c.get("/api/leads/rows", headers=h, params={"city": "Pune"}).json()
        assert rows["total"] == 2
        exp = c.post("/api/leads/export", headers=h, json={})
        assert exp.status_code == 200 and exp.json()["rows"] == 2
        hand = c.post("/api/leads/campaign-list", headers=h, json={"name": "API list"})
        assert hand.status_code == 200 and hand.json()["rows"] == 2
        cap = c.post("/api/leads/runs/her-data", headers=h,
                     json={"ask": "bada", "rows": [{} for _ in range(6000)], "source_name": "x.csv"})
        assert cap.status_code == 200 and cap.json()["run"]["status"] == "REFUSED"
        rgid = c.post("/api/leads/runs/her-data", headers=h,
                      json={"ask": "x", "rows": [], "source_name": "x", "lane": "SCRAPE"})
        assert rgid.status_code == 400                          # the unbuilt lane is refused, not stubbed
        run_id = r.json()["run"]["id"]
        frg = c.post("/api/leads/forget", headers=h, json={"run_id": run_id})
        assert frg.status_code == 200 and frg.json()["deleted"] == 2
