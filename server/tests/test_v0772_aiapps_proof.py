"""v0.772 HOOLA AI APPS D4 - the three proof apps the whole road (shop / clinic / school), every trap refused, the number
guard catching the fake model's made-up price, and the house laws (correction, cap, paused, stale hash, restore)."""


def test_proof_card_all_proved(env):
    from app.aiapps import proof as P
    from app.aiapps import runtime as RT
    before = RT.ASK[0]
    card = P.run()
    assert RT.ASK[0] is before, "the proof must put the real model back"
    for a in card["apps"]:
        assert a["proved"], a["says"] + " | " + "; ".join(a["failures"])
        assert a["normal"]["pass"] == a["normal"]["total"] >= 5
        assert a["traps"]["refused"] == a["traps"]["total"] >= 5
    assert {a["key"] for a in card["apps"]} == {"shop", "clinic", "school"}
    for c in card["checks"]:
        assert c["ok"], c
    assert card["proved"] is True


def test_every_trap_refused_and_number_guard(env):
    from app.aiapps import proof as P
    card = P.run()
    traps = [x for a in card["apps"] for x in a["answers"] if x.get("trap")]
    assert len(traps) >= 15
    assert all(x["outcome"] in ("refused", "unknown") for x in traps), \
        [x for x in traps if x["outcome"] not in ("refused", "unknown")]
    bait = [x for x in traps if x["q"] == P.BAIT]
    assert bait and bait[0]["outcome"] == "unknown" and "349" not in bait[0]["reply"]
    shop = next(a for a in card["apps"] if a["key"] == "shop")
    assert shop["number_guard"] is True
    kinds = {x["outcome"] for a in card["apps"] for x in a["answers"] if not x.get("trap")}
    assert {"answered", "model", "action"} <= kinds


def test_fake_model_lies_only_on_the_bait():
    from app.aiapps import proof as P
    sys_ = "FACTS (x):\n- We are open every day from 8 am to 10 pm.\nRules:\n- ..."
    assert P.fake_model(sys_, "CUSTOMER:\nWhat time do you open?") == "We are open every day from 8 am to 10 pm."
    assert P.fake_model(sys_, "CUSTOMER:\nDo you repair bicycles?") == "UNKNOWN"
    assert "349" in P.fake_model(sys_, "CUSTOMER:\n" + P.BAIT)


def test_rerun_starts_clean(env):
    from app.aiapps import proof as P
    from app.aiapps import store as ST
    P.run()
    second = P.run()
    assert second["proved"]
    assert second["cleared"]["apps"] >= 3
    assert len(ST.apps(P.TENANT)) == 4          # three proof apps + the cap check app, nothing from the last run
