"""v0.999 HOOLA CODE PICKS THE RIGHT FLOW (owner: 'NOW CHECK ALL HOOLA CODE --- DOES IT NOW DO ANY COMPLEX CODING BY
CHOOSING PROPER FLOW'): the check ran real-looking asks through Hoola Code's own choosers (kind of work, plan size, wait
for her yes, process skills, ECC skills) and found three wrong choices, fixed here and held by this table."""
from __future__ import annotations

import pytest

from app.devsahayak import eccskills as EK
from app.devsahayak import plan as PL
from app.devsahayak import service as S
from app.devsahayak import superpowers as SP

FLOW = [
    # ask, kind, tier, waits for her yes, a process skill that must load, an ECC skill that must load
    ("Fix the typo in README", "docs", "trivial", False, None, None),
    ("Checkout gives a 500 error when the cart is empty - fix it", "fix", "standard", False, "systematic-debugging", None),
    ("Add a discount code field to checkout", "write", "standard", False, "test-driven-development", None),
    ("Add Razorpay payments, order emails and an admin refund page", "write", "standard", False, "test-driven-development",
     "security-review"),
    ("Refactor the whole order system into services and add tests everywhere", "write", "large", True,
     "test-driven-development", "change-impact"),
    ("Migrate the app from Django to FastAPI", "write", "large", True, "test-driven-development", "change-impact"),
    ("Users sometimes get logged out randomly after a deploy", "fix", "standard", False, "systematic-debugging",
     "security-review"),
    ("The orders page doesn't load on mobile", "fix", "standard", False, "systematic-debugging", None),
    ("Checkout is very slow since yesterday", "fix", "standard", False, "systematic-debugging", None),
    ("Write tests for shop/views.py", "tests", "standard", False, "test-driven-development", None),
    ("Explain how the cart works", "explain", "trivial", False, None, None),
    ("Build a multi-tenant SaaS billing module with usage metering, invoices, GST and a dashboard", "write", "large", True,
     "test-driven-development", "security-review"),
    ("Migrate the database to Postgres", "write", "large", True, None, "database-migrations"),
    ("add an API endpoint for orders", "write", "standard", False, None, "api-design"),
]


@pytest.mark.parametrize("ask,kind,tier,waits,process,ecc", FLOW)
def test_each_ask_gets_its_flow(ask, kind, tier, waits, process, ecc):
    k = S.guess_kind(ask)
    assert k == kind, (ask, k)
    r = PL.assess(k, ask)
    assert r["tier"] == tier, (ask, r)
    assert PL.waits(r["tier"]) is waits
    if process:
        assert process in SP.pick(k, ask)
    if ecc:
        assert ecc in EK.for_words(ask)


def test_a_new_feature_with_a_symptom_word_stays_a_feature():
    assert S.guess_kind("Add caching so the dashboard is not slow") == "write"
    assert S.guess_kind("Add more unit tests for the cart") == "tests"
    assert S.guess_kind("Add tests for checkout and refactor the payment module") == "write"
