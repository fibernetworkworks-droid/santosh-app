"""v0.373 TPM KE HISAAB - the technical PM's work done in code (owner: "WORK ON TPM -- THAT AI CAN PERFROM ALL
TASKS IN IT").

v0.372 gave the TPM desk its twelve parts and its papers. This makes it DO the job, and the job is not prose - it
is six questions that each have one right answer:

    what is really blocking the release   -> critical path through the dependency graph
    who is over-committed, by how much    -> capacity against real estimates
    are we getting faster or slower       -> median lead / cycle time, escaped bugs, say-do
    what is rotting in the RAID log       -> overdue, gone quiet, unowned, high-and-open
    can we ship                           -> every gate, with the failures NAMED
    who owes me an update                 -> owners silent on open work

All six are arithmetic, so they live in `enterprise/tpm.py` and not in a prompt. The model picks the question and
reads the answer out; it never does the sum. That is the whole point: **a wrong critical path looks exactly as
confident as a right one**, and a TPM who cannot trust the number has nothing.

These tests use worked examples with answers computed by hand, not round-trips.
"""
import pytest

from app.enterprise import tpm as T


# ---------------------------------------------------------------- critical path
def test_the_critical_path_is_the_longest_chain_not_the_biggest_item():
    """A(3) and B(5) both feed C(2) -> E(4). The answer is B+C+E = 11, not A's branch and not E alone."""
    rows = [{"id": "A", "days": 3}, {"id": "B", "days": 5},
            {"id": "C", "days": 2, "depends_on": ["A", "B"]},
            {"id": "E", "days": 4, "depends_on": ["C"]}, {"id": "D", "days": 1}]
    r = T.critical_path(rows)
    assert r["din"] == 11.0
    assert r["raasta"] == ["B", "C", "E"]
    assert [x["id"] for x in r["kaam"]] == ["B", "C", "E"]      # none are done, so all still block


def test_finished_work_stops_delaying_the_release():
    rows = [{"id": "A", "days": 3}, {"id": "B", "days": 5, "status": "done"},
            {"id": "C", "days": 2, "depends_on": ["A", "B"]},
            {"id": "E", "days": 4, "depends_on": ["C"]}]
    r = T.critical_path(rows)
    assert r["din"] == 9.0                                       # A3 + C2 + E4; B contributes nothing now
    assert "B" not in [x["id"] for x in r["kaam"]]


def test_a_dependency_loop_is_reported_never_silently_broken():
    """A loop is a real planning bug. Returning a number here would be worse than refusing."""
    with pytest.raises(T.TpmError, match="chakkar"):
        T.critical_path([{"id": "X", "days": 1, "depends_on": ["Y"]},
                         {"id": "Y", "days": 1, "depends_on": ["X"]}])


def test_a_dependency_on_something_not_in_the_rows_is_named():
    r = T.critical_path([{"id": "A", "days": 2, "depends_on": ["GHOST"]}])
    assert r["jo_nahi_mile"] == ["GHOST"] and r["din"] == 2.0


def test_every_row_needs_an_id():
    with pytest.raises(T.TpmError):
        T.critical_path([{"title": "no id", "days": 1}])


# ---------------------------------------------------------------- capacity
def test_capacity_counts_only_open_work_and_names_who_is_over():
    rows = [{"owner": "Asha", "days": 12}, {"owner": "Asha", "days": 3},
            {"owner": "Ravi", "days": 4}, {"owner": "Ravi", "days": 99, "status": "done"},
            {"owner": "", "days": 2}]
    c = T.capacity(rows, days_available=10)
    asha = [x for x in c["log"] if x["owner"] == "Asha"][0]
    ravi = [x for x in c["log"] if x["owner"] == "Ravi"][0]
    assert asha["lagega"] == 15.0 and asha["zyada"] == 5.0 and asha["bhara"] == 150.0
    assert ravi["lagega"] == 4.0 and ravi["zyada"] == 0.0        # the done 99 days does not count
    assert c["bina_maalik"] == 2.0
    assert [x["owner"] for x in c["zyada_bhare"]] == ["Asha"]


def test_capacity_can_be_per_person():
    c = T.capacity([{"owner": "Asha", "days": 12}], days_available=10, per_owner={"asha": 20})
    assert c["zyada_bhare"] == []


# ---------------------------------------------------------------- delivery metrics
def test_metrics_use_the_median_so_one_outlier_cannot_lie():
    """Three tickets, one of them 90 days. The mean would read ~34; the median reads 9."""
    rows = [{"created": "2026-01-01", "started": "2026-01-05", "done": "2026-01-10"},
            {"created": "2026-01-01", "started": "2026-01-02", "done": "2026-01-03"},
            {"created": "2026-01-01", "started": "2026-01-02", "done": "2026-04-01", "escaped": True}]
    m = T.delivery_metrics(rows, committed=5)
    assert m["lead_time_din"] == 9.0
    assert m["cycle_time_din"] == 5.0
    assert m["poore_hue"] == 3 and m["baad_mein_mile_bugs"] == 1
    assert m["vaada_vs_hua"] == 60.0                             # 3 of 5 committed


def test_metrics_say_so_when_there_are_no_dates():
    m = T.delivery_metrics([{"title": "x"}])
    assert m["lead_time_din"] is None and "samay nahi" in m["note"]


# ---------------------------------------------------------------- RAID, readiness, chase
def test_the_raid_sweep_finds_what_is_rotting():
    rows = [{"id": "1", "due": "2026-01-01", "owner": "A", "updated": "2026-01-01",
             "status": "open", "severity": "high"},
            {"id": "2", "owner": "", "status": "open"},
            {"id": "3", "due": "2020-01-01", "owner": "B", "status": "done"}]
    s = T.raid_sweep(rows, today="2026-02-01")
    assert [x["id"] for x in s["tareekh_nikli"]] == ["1"] and s["tareekh_nikli"][0]["kitne_din"] == 31
    assert [x["id"] for x in s["koi_khabar_nahi"]] == ["1"]
    assert [x["id"] for x in s["bina_maalik"]] == ["2"]
    assert [x["id"] for x in s["bade"]] == ["1"]
    # closed work is not rotting: check the ids, not a substring - "3" also lives inside "31" and "2026"
    seen = {x["id"] for k in ("tareekh_nikli", "koi_khabar_nahi", "bina_maalik", "bade") for x in s[k]}
    assert "3" not in seen


def test_readiness_names_the_gates_that_fail():
    g = T.release_readiness([{"name": "tests", "ok": True},
                             {"name": "perf", "ok": False},
                             {"name": "docs", "ok": False, "blocking": False}])
    assert g["ja_sakte_hain"] is False
    assert [x["gate"] for x in g["ruke_hue"]] == ["perf"]
    assert [x["gate"] for x in g["chetavni"]] == ["docs"]        # non-blocking: a warning, not a stop
    assert "perf" in g["note"]
    assert T.release_readiness([{"name": "tests", "ok": True}])["ja_sakte_hain"] is True


def test_chase_finds_who_has_gone_quiet_and_never_invents_their_status():
    c = T.chase([{"id": "1", "owner": "Ravi", "updated": "2026-01-01", "status": "open"},
                 {"id": "2", "owner": "Asha", "updated": "2026-01-19", "status": "open"},
                 {"id": "3", "owner": "", "status": "open"}], today="2026-01-20")
    owed = {x["owner"]: len(x["cheezein"]) for x in c["kisse_poochna_hai"]}
    assert owed == {"Ravi": 1}                                   # Asha spoke yesterday
    assert [x["id"] for x in c["bina_maalik"]] == ["3"]
    assert "khud se koi status nahi likhta" in c["note"]


# ---------------------------------------------------------------- the sums belong to tpm alone
def test_the_sums_are_offered_on_tpm_and_nowhere_else():
    from app.agent.enterprise_tools import ENTERPRISE_TOOLS
    tpm = [x for x in ENTERPRISE_TOOLS if x["name"] == "tpm"][0]
    acts = tpm["input_schema"]["properties"]["action"]["enum"]
    for a in ("critical_path", "capacity", "metrics", "raid", "readiness", "chase"):
        assert a in acts, a
    assert "as confident as a right one" in tpm["description"]
    for other in ("erp", "crm_arch", "plm"):
        d = [x for x in ENTERPRISE_TOOLS if x["name"] == other][0]["description"]
        assert "critical_path" not in d, other


def test_the_row_cap_holds():
    with pytest.raises(T.TpmError):
        T.capacity([{"owner": "x", "days": 1} for _ in range(T.MAX_ROWS + 1)])


def test_version():
    from pathlib import Path

    from app.main import APP_VERSION
    assert APP_VERSION == "0.393.0"
    assert "0.393.0+437" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
