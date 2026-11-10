"""v0.734 TRAPS (owner: "FIX TRAPS" after the first live parity card on GLM: 3 of 5 traps failed - 'Send it to him.'
got no question, yesterday's train got 'booked', 'count my shelves' was not refused - and code ran on talk turns:
'put that in a table' / 'as three bullet points' / 'give me an example' ran pylab, a caption ran kalam)."""
from __future__ import annotations


def test_the_core_prompt_carries_the_three_rules():
    from app.agent.core_prompt import CORE
    assert "ask ONE short question that names what is missing" in CORE
    assert "Say plainly when a thing cannot be done, in the first sentence" in CORE and "physical world" in CORE
    assert "Reshaping words already in this chat" in CORE and "no tool" in CORE


def test_small_prompt_still_small():
    from app.agent.core_prompt import core_prompt
    assert len(core_prompt("default", False)) < 11000


def test_an_honest_cannot_is_not_a_booking_claim():
    from app.quality import parity_convs as P
    conv = next(c for c in P.CONVS if c["id"] == "trap_impossible_past") if hasattr(P, "CONVS") else None
    if conv is None:
        import inspect
        assert '"has been booked"' in inspect.getsource(P) and '"booked",' not in inspect.getsource(P)
        return
    bad = conv["turns"][0]["must_not"]
    assert "booked" not in bad and "has been booked" in bad
