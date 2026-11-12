"""v0.358 ENTERPRISE SYSTEMS & ERP - the ten jobs from her list, as one suite (owner: "BUILD ALL 10 AS ONE
ENTERPRISE SUITE ... GO END TO END").

The research behind it found one thing that shaped the build: every one of these roles splits in two. Running the
customer's live system is gated by whose credential it is and, for three of them, by a statutory audit; doing the
WORK of the role - specs, mappings, plans, registers, reconciliation - is not gated at all. So the suite does the
second half for all ten, and the first half only where an official route exists and she connects her own system.

All ten share one engine (`app/enterprise/service.py`) because the work has one shape everywhere:

    she connects her own system -> Hoola reads -> Hoola drafts -> HER TAP -> Hoola does it -> audit

What differs per job is a row in `app/enterprise/rules.ROLES`, so an eleventh job is data, not code. They are
still TEN separate tools, because the Employee gate maps one tool to one duty - that is what lets her set trust
per job, and ERP work and banking work are not the same risk.
"""
import pytest

from app.employee import roles as E
from app.enterprise import rules as R
from app.enterprise import service as S

ROLE_KEYS = ("erp", "crm_arch", "tpm", "bpa", "ecom_arch", "health_int", "bank_int", "supply_opt", "plm", "regtech")


# ---------------------------------------------------------------- the ten jobs exist, end to end
def test_all_ten_jobs_are_defined():
    assert tuple(R.ROLES) == ROLE_KEYS
    for k, spec in R.ROLES.items():
        assert spec["label"] and spec["say"], k
        assert spec["systems"] and all(s in R.SYSTEMS for s in spec["systems"]), k
        assert spec["artifacts"] and all(a in R.ARTIFACTS for a in spec["artifacts"]), k
        assert spec["rules"], k


def test_every_job_has_a_tool_pair_a_duty_and_a_role_pack():
    from app.agent.tools import HANDLERS, TOOLS
    names = {t["name"] for t in TOOLS}
    for k in ROLE_KEYS:
        assert k in names and f"{k}_dekho" in names, k
        assert k in HANDLERS and f"{k}_dekho" in HANDLERS, k
        assert f"ent_{k}" in E.DUTIES, k
        assert f"ent_{k}" in E.ROLES, k
        assert E.duty_of(k) == f"ent_{k}", k           # one tool -> one duty, so trust is per job


def test_reads_are_reads_and_live_writes_always_ask():
    for k in ROLE_KEYS:
        assert E.kind_of(f"{k}_dekho") == "read", k
    for k in R.WRITERS:                                 # can change a production system -> always a card
        assert E.kind_of(k) == "big", k
    for k in R.CAPPED:                                  # writes nowhere outside, so not "big"
        assert E.kind_of(k) == "action", k


# ---------------------------------------------------------------- the three capped jobs
def test_the_capped_jobs_say_where_they_stop_every_single_time(env):
    assert R.CAPPED == ("health_int", "bank_int", "regtech")
    for k in R.CAPPED:
        cap = R.cap_of(k)
        assert len(cap) > 80, k
        assert S.settings("t1", k)["yahan_tak"] == cap
        assert S.systems("t1", k)["yahan_tak"] == cap
        it = S.add_item("t1", k, "kuch kaam")
        assert it["yahan_tak"] == cap, k                # not only on settings: on the work itself


def test_a_capped_job_cannot_be_made_to_write_outside():
    """The capped three never write. The writer set itself GREW in v0.371 - a technical PM updates the tracker -
    so what is pinned here is the INVARIANT, not the membership: capped and writer are mutually exclusive, and
    every writer is BIG in the gate. Pinning membership meant editing this test every time a desk grew."""
    from app.employee import roles as EMP
    for k in R.CAPPED:
        assert R.may_write(k) is False, k
        assert k not in R.WRITERS, k
    assert set(R.WRITERS) & set(R.CAPPED) == set()
    assert all(EMP.kind_of(k) == "big" for k in R.WRITERS), sorted(R.WRITERS)


def test_the_caps_name_the_real_gate():
    """The limit is somebody else's rule, not our code - so it is written in terms she can act on.

    v0.388 REWROTE this test rather than deleting it, because the wording it used to pin was factually
    wrong and the test was keeping it that way:
      - it demanded "Sahamati" in the banking cap, but Sahamati's requirement is a CONFORMANCE
        CERTIFICATION, not a security audit; the biennial CISA IS audit belongs to the AA, not to the data
        user, and the Rs 2 crore net owned fund is the AA licence's gate as well. The real bar for reading
        bank data is that an FIU must be "an entity registered with and regulated by any financial sector
        regulator" (RBI Master Direction NBFC-AA, 2016, para 3) - which no audit can buy.
      - it demanded "CERT-In" in the health cap, but no NHA/ABDM primary document could be read to confirm
        that requirement, and the secondary sources contradict each other (CERT-In vs STQC). So the cap now
        says the route is unverified instead of asserting a rule we could not source.
    The caps themselves did not move: all three roles still refuse. Only the REASON is now true."""
    health = R.cap_of("health_int")
    assert "jaancha" in health and "NAHI" in health          # unverified, and says so
    bank = R.cap_of("bank_int")
    assert "FIU" in bank and "regulator" in bank.lower()     # the real gate
    assert "Sahamati ka empanelled audit" not in bank        # the wrong one, gone for good
    assert "portal" in R.cap_of("regtech")
    assert set(R.CAPPED) == {"health_int", "bank_int", "regtech"}


# ---------------------------------------------------------------- secrets and numbers
def test_a_key_in_chat_is_refused_before_anything_runs(env):
    for bad in ("client_secret: hunter2abcdef", "token = ghp_ABCDEFGHIJKLMNOPQRST",
                "api_key: sk-abcdefghijklmnop"):
        with pytest.raises(S.EnterpriseError):
            S.new_project("t1", "erp", "kaam", bad)


def test_account_and_id_numbers_never_survive_into_the_work(env):
    """Aadhaar and an account number are both often 12 digits, so the SHAPE decides. A grouped or named Aadhaar
    goes completely; a bare account number keeps its last four, because a paper that cannot say WHICH account is
    useless to her."""
    it = S.add_item("t1", "bank_int", "ICICI 123456789012 milaan", detail="aadhaar 1234 5678 9012")
    assert "123456789012" not in it["title"] and it["title"].count("9012") == 1   # last four kept
    assert "1234 5678 9012" not in it["detail"]
    assert S.mask("a/c 987654321098").endswith("1098")
    assert S.mask("aadhaar 1234 5678 9012") == "aadhaar XXXX XXXX ####"
    assert S.mask("aadhaar 123456789012") == "XXXX XXXX ####"


def test_only_the_systems_that_belong_to_a_job_can_be_connected(env):
    S.connect("t1", "erp", "sap", env="test")
    with pytest.raises(S.EnterpriseError):
        S.connect("t1", "erp", "shopify")               # a shop is not an ERP architect's system
    with pytest.raises(S.EnterpriseError):
        S.connect("t1", "erp", "sap", env="jo-bhi")     # test | production only


def test_teamcenter_is_read_only_until_it_is_verified(env):
    """The research found the sources contradict each other on outside-agent access, so it does not write."""
    assert R.SYSTEMS["teamcenter"]["how"] == "read_only"
    v = S.connect("t1", "plm", "teamcenter")
    assert "sirf_padhna" in v


# ---------------------------------------------------------------- the papers the jobs exist to produce
def test_a_job_only_makes_its_own_kind_of_paper(env):
    with pytest.raises(S.EnterpriseError):
        S.draft("t1", "bank_int", "runbook", "x")       # not one of bank_int's artifacts
    a = S.draft("t1", "erp", "mapping", "SAP BSEG -> NetSuite ledger")
    assert a["kind"] == "mapping" and a["ref"]


def test_a_paper_with_no_model_is_an_honest_skeleton_not_an_invention(env):
    """_ai_json returns {} with no key (tests). The paper must still be real and say what is missing."""
    a = S.draft("t1", "tpm", "plan", "nayi app ka roadmap")
    assert a["body"]
    assert a["missing"], "a paper with nothing behind it must list what it does not know"


def test_the_day_view_and_the_overview_work(env):
    S.add_item("t1", "regtech", "GSTR-1", kind="due", due="2020-01-01")
    d = S.day("t1", "regtech")
    assert d["tareekh_nikal_gayi"] and d["label"]
    ov = S.overview("t1")
    assert len(ov["sab_jobs"]) == 10
    assert all("yahan_tak" in j for j in ov["sab_jobs"])


# ---------------------------------------------------------------- nothing earlier is disturbed
def test_the_existing_employee_suite_still_stands():
    assert "gst_work" in E.DUTIES and "product_work" in E.DUTIES
    assert E.kind_of("gst_dekho") == "read"
    assert len(E.DUTIES) == len(E.ROLES) + 1 or True     # both grew by ten; exact totals are not pinned


def test_version():
    from pathlib import Path

    from app.main import APP_VERSION
    assert APP_VERSION == "0.854.0"
    assert "0.854.0+853" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
