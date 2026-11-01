"""v0.371 POOCHH LO + FAIR CARD (hard card result 9/12): a vague coding ask ("checkout mein kuch gadbad hai") is answered with
ONE question and no edits - Hoola had guessed and changed orders.py; the chat line carries no tail after the question.
And two hard-card checks were stricter than the jobs: the shared-cart check accepted only one way of writing the fix, and
the red-test job refused ANY edit to test_orders.py (adding a test beside the red one is fine; weakening it is not)."""
from app.quality import code_repos as R
from app.quality import code_tasks2 as C2
from app.quality import codecard as K
from tests.test_tech_devsahayak import T, _join, dev  # noqa: F401
from tests.test_v0350_kadam_ba_kadam import Script, tu


def _task(tid):
    return next(t for t in C2.TASKS if t["id"] == tid)


def test_every_honest_way_to_fix_the_shared_cart_counts():
    t = _task("fix_shared_default")
    test = {"tests/test_cart.py": t["solution"]["tests/test_cart.py"]}
    for line in ("self.items = items if items is not None else []", "self.items = list(items) if items is not None else []",
                 "self.items = list(items or [])"):
        cart = R.CART.replace("self.items = items if items is not None else []", line)
        assert K.score(t, {"app/cart.py": cart, **test})["right"], line
    assert not K.score(t, test)["works"]                                    # the bug itself still fails


def test_a_new_test_beside_the_red_one_is_fine_but_weakening_it_is_not():
    t = _task("fix_from_test_run")
    added = {"app/orders.py": R.ORDERS, "tests/test_orders.py": C2.TEST_ORDERS_LEAK + "\n\ndef test_more():\n    pass\n"}
    assert K.score(t, added)["right"]
    weak = {"app/orders.py": R.ORDERS,
            "tests/test_orders.py": C2.TEST_ORDERS_LEAK.replace('assert inventory.STOCK["TEA-250"] == 50', "assert True")}
    row = K.score(t, weak)
    assert not row["right"] and not row["rules"]


def test_the_coding_rules_say_ask_one_question_on_a_vague_request():
    from app.devsahayak import loop as L
    from app.devsahayak import service as S
    assert "VAGUE request" in L.SYSTEM and "do NOT guess" in L.SYSTEM and "never answered with a question" in L.SYSTEM
    done = next(x for x in L.TOOLS if x["name"] == "done")
    assert "ONE short question" in done["input_schema"]["properties"]["explain"]["description"]
    assert "VAGUE request" in S.WRITE_SYSTEM


def test_a_question_reaches_her_without_a_tail(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.devsahayak import loop as L
    q = "Checkout mein kya dikh raha hai - koi error, ya kis step par atakta hai?"
    monkeypatch.setattr(L, "BRAIN", Script([[tu(1, "list_dir", path="")], [tu(2, "done", explain=q)]]))
    v = S.start(T, "fix", "Checkout mein kuch gadbad hai, theek kar do.")
    assert v["status"] == "explained" and v["say"].startswith(q) and "Koi file" not in v["say"]
    assert not any(r.startswith("hoola/") for r in S.FAKE.refs)              # nothing pushed
