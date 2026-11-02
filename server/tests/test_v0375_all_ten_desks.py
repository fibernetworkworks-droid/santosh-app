"""v0.375 SAB DAS DESK - the remaining seven brought to the ERP / CRM / TPM standard (owner: "MAKE ALL 7
REMAINING ROLES 100% LIKE ERP CRM TPM").

Two things make a role "100%" here, and they were applied to all seven:

1. A DESK - the job's real parts, each making only the papers that part produces. All ten roles now have one:
   90 parts in total.
2. THE SUMS, where the work IS arithmetic. `tpm.py` proved the shape in v0.374; four more jobs are the same
   kind of job, so `calc.py` answers their questions in code:

       supply_opt   when to reorder, how much, what is dead, what runs out when
       plm          what a part is used in, what an assembly costs
       bank_int     which statement lines matched the ledger and which did not
       regtech      what is due, what is late, what it could cost

   The other five (erp, crm_arch, bpa, ecom_arch, health_int) have no sums, because their work is judgement and
   execution, not arithmetic. Which job gets which is a TABLE (`SUMS`), not an if-chain, and a job cannot call a
   sum that is not its own.

Every function refuses rather than guesses when the data cannot answer: too little history for a reorder point,
a loop in a BOM, a penalty nobody supplied.
"""
import pytest

from app.employee import roles as E
from app.enterprise import calc as C
from app.enterprise import rules as R
from app.enterprise import service as S


# ---------------------------------------------------------------- every role is a desk now
def test_all_ten_roles_have_a_desk():
    missing = [k for k in R.ROLES if not R.jobs_of(k)]
    assert missing == [], missing
    assert sum(len(R.jobs_of(k)) for k in R.ROLES) == 90


def test_every_part_of_every_desk_can_make_its_first_paper(env):
    for role in R.ROLES:
        for job, spec in R.jobs_of(role).items():
            out = S.draft("t1", role, spec["papers"][0], f"test {job}", job=job)
            assert out["hissa"]["job"] == job, (role, job)


def test_a_part_still_only_makes_its_own_papers(env):
    with pytest.raises(S.EnterpriseError):
        S.draft("t1", "supply_opt", "runbook", "x", job="demand")      # not one of demand's kinds
    with pytest.raises(S.EnterpriseError):
        S.draft("t1", "plm", "training", "x", job="bom")


def test_the_capped_three_are_still_capped_with_their_desks(env):
    for k in R.CAPPED:
        assert R.jobs_of(k), k
        assert R.may_write(k) is False, k
        assert S.settings("t1", k)["yahan_tak"] == R.cap_of(k)
        out = S.draft("t1", k, R.jobs_of(k)["calendar" if k == "regtech" else list(R.jobs_of(k))[0]]["papers"][0],
                      "x", job=list(R.jobs_of(k))[0])
        assert out["yahan_tak"] == R.cap_of(k), k


# ---------------------------------------------------------------- supply_opt
def test_reorder_point_is_demand_times_lead_plus_safety():
    """60 sold in 30 days = 2/day, lead 10 -> 20 + a half-lead cushion of 10 = 30. On hand 15, so order now."""
    r = C.reorder([{"sku": "A", "sold": 60, "days": 30, "lead_days": 10, "on_hand": 15}])
    a = r["saman"][0]
    assert a["roz_bikta"] == 2.0 and a["safety"] == 10.0 and a["reorder_point"] == 30.0
    assert a["mangwana_hai"] is True and a["kitne_din_chalega"] == 7.5
    assert "roz ke numbers nahi the" in a["safety_kaise"]


def test_daily_numbers_give_a_real_safety_stock():
    daily = [2, 1, 3, 2, 2, 4, 1, 2, 3, 2, 2, 1, 3, 2]
    r = C.reorder([{"sku": "A", "sold": 30, "days": 14, "lead_days": 9, "on_hand": 5,
                    "sold_daily": daily}], service_level=95)
    assert "roz ke numbers se" in r["saman"][0]["safety_kaise"]
    assert r["saman"][0]["safety"] > 0


def test_too_little_history_is_refused_not_guessed():
    with pytest.raises(C.CalcError, match="kaafi nahi"):
        C.reorder([{"sku": "A", "sold": 5}], days_of_history=3)


def test_dead_stock_finds_where_the_money_is_sitting():
    d = C.dead_stock([{"sku": "X", "on_hand": 10, "unit_cost": 100, "last_sold": "2020-01-01"},
                      {"sku": "Y", "on_hand": 5, "unit_cost": 50, "last_sold": "2026-10-30"}])
    assert [x["sku"] for x in d["mara_hua"]] == ["X"]
    assert d["mare_hue_mein_paisa"] == 1000.0 and d["kul_stock_ka_paisa"] == 1250.0


# ---------------------------------------------------------------- plm
def test_a_bom_rolls_its_cost_up_from_the_leaves():
    b = C.bom_explode([{"parent": "CHAIR", "child": "LEG", "qty": 4, "unit_cost": 50},
                       {"parent": "CHAIR", "child": "SEAT", "qty": 1, "unit_cost": 200}], "CHAIR")
    assert b["laagat"] == 400.0
    assert {x["part"]: x["qty"] for x in b["kul_parts"]} == {"LEG": 4.0, "SEAT": 1.0}


def test_a_nested_bom_multiplies_through_every_level():
    """TABLE = 1 CHAIR (itself 4 LEG) + 2 LEG -> 6 legs, 300."""
    b = C.bom_explode([{"parent": "TABLE", "child": "CHAIR", "qty": 1},
                       {"parent": "CHAIR", "child": "LEG", "qty": 4, "unit_cost": 50},
                       {"parent": "TABLE", "child": "LEG", "qty": 2, "unit_cost": 50}], "TABLE")
    assert {x["part"]: x["qty"] for x in b["kul_parts"]}["LEG"] == 6.0
    assert b["laagat"] == 300.0


def test_a_part_with_no_price_is_named_not_counted_as_free():
    b = C.bom_explode([{"parent": "A", "child": "B", "qty": 1}], "A")
    assert b["daam_nahi_mila"] == ["B"] and "0 mana gaya" in b["note"]


def test_a_bom_loop_is_refused():
    with pytest.raises(C.CalcError, match="chakkar"):
        C.bom_explode([{"parent": "A", "child": "B", "qty": 1},
                       {"parent": "B", "child": "A", "qty": 1}], "A")


def test_where_used_walks_all_the_way_up():
    w = C.where_used([{"parent": "TABLE", "child": "CHAIR"}, {"parent": "CHAIR", "child": "LEG"}], "LEG")
    assert sorted(x["assembly"] for x in w["kahan_lagta_hai"]) == ["CHAIR", "TABLE"]
    assert w["sabse_upar"] == ["TABLE"]


# ---------------------------------------------------------------- bank_int
def test_reconciliation_needs_more_than_a_matching_amount():
    """Matching on amount alone is how reconciliations go wrong."""
    r = C.reconcile([{"amount": 1000, "date": "2026-01-01"}],
                    [{"amount": 1000, "date": "2026-03-01"}], days=3)
    assert r["mile"] == 0
    assert len(r["sirf_bank_mein"]) == 1 and len(r["sirf_kitaab_mein"]) == 1


def test_a_reference_match_is_taken_first_and_each_line_used_once():
    r = C.reconcile([{"amount": 1000, "date": "2026-01-01", "ref": "INV1"},
                     {"amount": 500, "date": "2026-01-05"}],
                    [{"amount": 1000, "date": "2026-01-03", "ref": "INV1"},
                     {"amount": 500, "date": "2026-01-06"}], days=3)
    assert r["mile"] == 2 and [p["kaise"] for p in r["jode"]] == ["ref", "amount+date"]
    two = C.reconcile([{"amount": 100, "date": "2026-01-01"}, {"amount": 100, "date": "2026-01-01"}],
                      [{"amount": 100, "date": "2026-01-01"}])
    assert two["mile"] == 1 and len(two["sirf_bank_mein"]) == 1


def test_reconciliation_reports_the_difference():
    r = C.reconcile([{"amount": 100}], [{"amount": 70}])
    assert r["antar"] == 30.0 and r["mile"] == 0


# ---------------------------------------------------------------- regtech
def test_the_calendar_never_invents_a_fine():
    c = C.due_calendar([{"name": "GSTR-1", "due": "2026-01-11", "penalty_per_day": 50},
                        {"name": "Audit", "due": "2026-01-01"},
                        {"name": "TDS", "due": "2026-01-07", "status": "done"},
                        {"name": "PF", "due": "2026-02-15"}], today="2026-02-01")
    late = {x["name"]: x for x in c["late"]}
    assert late["GSTR-1"]["kitne_din_late"] == 21 and late["GSTR-1"]["jurmana"] == 1050.0
    assert late["Audit"]["jurmana"] is None                       # no figure given -> none invented
    assert c["jurmana_jod"] == 1050.0 and c["jurmana_pata_nahi"] == ["Audit"]
    assert [x["name"] for x in c["aane_wale"]] == ["PF"]
    assert [x["name"] for x in c["ho_gaye"]] == ["TDS"]


# ---------------------------------------------------------------- the sums belong where they belong
def test_each_job_gets_only_its_own_sums():
    from app.agent.enterprise_tools import SUMS
    assert set(SUMS) == {"tpm", "supply_opt", "plm", "bank_int", "regtech"}
    for role in ("erp", "crm_arch", "bpa", "ecom_arch", "health_int"):
        assert role not in SUMS, role                             # judgement and execution, not arithmetic
    assert SUMS["plm"] == ("bom", "where_used")
    assert "critical_path" not in SUMS["plm"]


def test_the_sums_are_a_table_not_an_if_chain():
    import pathlib

    from app.agent import enterprise_tools as ET
    src = pathlib.Path(ET.__file__).read_text()
    assert "SUMS: dict[str, tuple[str, ...]]" in src
    assert 'if key == "tpm"' not in src                           # the special case is gone
    assert "if False" not in src                                  # and no dead branch left behind


def test_the_gate_classes_are_still_right():
    assert all(E.kind_of(k) == "big" for k in R.WRITERS)
    assert all(E.kind_of(k) == "action" for k in R.CAPPED)
    assert all(E.kind_of(k + "_dekho") == "read" for k in R.ROLES)


def test_version():
    from pathlib import Path

    from app.main import APP_VERSION
    assert APP_VERSION == "0.446.0"
    assert "0.446.0+491" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
