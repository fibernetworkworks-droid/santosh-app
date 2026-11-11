"""v0.771 PROOF APPS: the five proof apps of docs/COMPLEX_APPS_PLAN.md go the whole road on the server.

Each one is a hand-written naksha (no model), checked by Pillar K, built module by module through the real engines,
its brain applied through the real logic engine, and proved by hand-written Pillar J scenarios on a twin - every
privacy step a 'must be refused'. These tests fail the moment any of that stops being true.
"""
from __future__ import annotations

import pytest

from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


@pytest.fixture()
def card(droid_env):
    from app.appmaker import proofapps as PA
    return PA.run()


def test_all_five_proof_apps_are_proved_on_the_server(card):
    bad = [a["says"] for a in card["apps"] if not a["proved"]]
    assert not bad, "\n".join(bad)
    assert card["proved"] == card["total"] == 5


def test_every_app_checks_real_refusals_and_names_what_is_not_proved(card):
    for a in card["apps"]:
        assert a.get("refused_checked", 0) >= 2, a["key"]
        assert a["not_proved"], a["key"]
    assert card["on_a_phone"] is False and "real phone" in card["says"]


def test_her_credentials_stay_next_steps_never_passes(card):
    food = next(a for a in card["apps"] if a["key"] == "food_delivery")
    joined = " ".join(food["next_steps"])
    assert "Payment" in joined and "tracking" in joined, food["next_steps"]


def test_the_proof_runs_only_on_its_own_hidden_tenant(card):
    from app.appmaker.models import AppProject
    from app.db import session
    from app.appmaker import proofapps as PA
    with session() as s:
        tenants = {p.tenant_id for p in s.query(AppProject).all() if p.stage in ("proof", "jaanch")}
    assert tenants == {PA.TENANT}


def test_a_second_run_starts_fresh(droid_env):
    from app.appmaker import proofapps as PA
    from app.appmaker.models import AppProject
    from app.db import session
    PA.run("clinic")
    again = PA.run("clinic")
    assert again["apps"][0]["proved"], again["apps"][0]["says"]
    with session() as s:
        n = s.query(AppProject).filter(AppProject.tenant_id == PA.TENANT).count()
    assert n == 2          # the app + its twin, not two of each
