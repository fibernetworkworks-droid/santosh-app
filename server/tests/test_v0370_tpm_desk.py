"""v0.370 TPM DESK - the technical PM desk, and the BIG list stops drifting (owner: "Technical PM (tpm) ---
CHECK AND MAKE THIS 100 %").

The check found two things.

1. `tpm` was the thinnest of the three desks - three paper kinds, no sub-jobs, and it could not write anywhere.
2. More important: as written it would have DUPLICATED the existing `product` tool, which is 1,789 lines and
   already owns the product side end to end - discovery, RICE / ICE scoring, Kano, PRDs, roadmap, releases, KPIs.

So the TPM desk is deliberately the ENGINEERING counterpart, not a second product manager: what blocks what,
what was decided and why, what must be true to ship, and what is owed. The role's own rules say so, which is what
keeps the model from reaching for the wrong one.

It also now WRITES - a technical PM updates the tracker - and that exposed a real drift: `employee/roles.BIG`
was a hand-written list, so `tpm` kept its old "action" class after becoming a writer. BIG is now DERIVED from
`enterprise.rules.WRITERS`, so the two can never disagree again.
"""
import pytest

from app.employee import roles as E
from app.enterprise import rules as R
from app.enterprise import service as S


def test_the_tpm_desk_is_the_engineering_side():
    js = R.jobs_of("tpm")
    assert len(js) == 12
    for must in ("roadmap", "dependencies", "architecture", "nfr", "debt", "capacity", "release", "risk",
                 "vendor", "incident", "metrics", "status"):
        assert must in js, must
        assert set(js[must]["papers"]) <= set(R.ARTIFACTS), must


def test_it_does_not_duplicate_the_product_tool():
    """The product side has a far richer home. The role says so, so the model picks the right tool."""
    rules = R.role("tpm")["rules"]
    assert any("`product` tool" in r for r in rules)
    assert any("discovery" in r.lower() for r in rules)
    from app.agent.product_tools import PRODUCT_TOOLS
    product_actions = PRODUCT_TOOLS[0]["description"]
    for owned in ("score", "kano", "spec", "release"):
        assert f"action={owned}" in product_actions, owned      # still the product tool's job, not tpm's


def test_every_part_makes_its_own_papers(env):
    for k, v in R.jobs_of("tpm").items():
        out = S.draft("t1", "tpm", v["papers"][0], f"test {k}", job=k)
        assert out["hissa"]["job"] == k, k
    with pytest.raises(S.EnterpriseError):
        S.draft("t1", "tpm", "runbook", "x", job="metrics")      # a metrics report is not a runbook
    assert S.draft("t1", "tpm", "runbook", "go/no-go", job="release")["kind"] == "runbook"


def test_it_can_write_and_so_it_always_asks():
    """A technical PM updates the tracker; a tracker write is a real change, so it is a card."""
    assert R.may_write("tpm") is True
    assert "tpm" in R.WRITERS
    assert E.kind_of("tpm") == "big"
    assert E.kind_of("tpm_dekho") == "read"
    assert any("aapki haan se" in r for r in R.role("tpm")["rules"])


def test_it_never_invents_a_status_it_was_not_given():
    assert any("update nahi aaya" in r for r in R.role("tpm")["rules"])
    assert any("vaada nahi" in r for r in R.role("tpm")["rules"])


# ---------------------------------------------------------------- the drift that caused this
def test_the_big_list_is_derived_not_hand_written():
    """`tpm` became a writer and silently stayed "action" because BIG was a literal list. Deriving it is the fix:
    add a writer to enterprise/rules and the gate follows by itself."""
    src = (__import__("pathlib").Path(E.__file__)).read_text()
    assert "_enterprise_writers" in src and "BIG |= _enterprise_writers()" in src
    assert all(E.kind_of(k) == "big" for k in R.WRITERS), sorted(R.WRITERS)
    assert all(E.kind_of(k) == "action" for k in R.CAPPED)


def test_the_gate_still_works_without_the_suite(monkeypatch):
    """The derivation must never be able to break the Employee gate itself."""
    import builtins
    real = builtins.__import__

    def boom(name, *a, **k):
        if "enterprise.rules" in name:
            raise ImportError("gone")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", boom)
    assert E._enterprise_writers() == set()


def test_all_three_desks_now_stand_together():
    assert len(R.jobs_of("erp")) == 16
    assert len(R.jobs_of("crm_arch")) == 12
    assert len(R.jobs_of("tpm")) == 12


def test_version():
    from pathlib import Path

    from app.main import APP_VERSION
    assert APP_VERSION == "0.846.0"
    assert "0.846.0+845" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
