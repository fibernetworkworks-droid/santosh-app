"""v0.952 HOOLA CODE UNCLEAR ASK (owner: "Check" -> hard card 11/12 after v0.951: no probe.py left any more, but the vague
ask explored for 10 minutes and ended without a question): a short "something is wrong, fix it" with no symptom gets a
note up front (ask ONE question, no edits) and done is sent back once if its explain does not end in a question."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_unclear_asks_are_told_apart_from_real_ones():
    from app.devsahayak import engine as E
    assert E.unclear_ask("Checkout mein kuch gadbad hai, theek kar do.")
    assert E.unclear_ask("login kaam nahi kar raha")
    for ok in ("checkout ka total galat aa raha hai jab coupon lagate hain, theek karo", "app.py line 40 TypeError, fix it",
               "Add a COD fee of Rs 40 to checkout", "Make the login page better", ""):
        assert not E.unclear_ask(ok), ok


def test_the_note_and_the_done_check_are_wired():
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "UNCLEAR_NOTE if unclear" in src
    assert 'not reality.get("asked")' in src and 'endswith("?")' in src
    assert "unclear_ask(str(getattr(t, \"text\"" in src
    from app.devsahayak import engine as E
    assert "ONE short question" in E.UNCLEAR_NOTE and "Put back" in E.unclear_text(True)
    assert "Put back" not in E.unclear_text(False)


def test_card_miss_says_what_hoola_said():
    from app.quality import codecard as C
    task = {"id": "vague_ask", "kind": "fix", "repo": "dukaan", "ask": True, "request": "x", "files": {},
            "allow": r"^$", "check": "", "solution": {}}
    row = C.score(task, {}, {"explain": "I looked at checkout and it seems fine."})
    assert not row["works"] and "said: I looked at checkout" in row["why"][0]


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.17"' in main
    assert "version: 0.999.17+1015" in (ROOT / "pubspec.yaml").read_text()
