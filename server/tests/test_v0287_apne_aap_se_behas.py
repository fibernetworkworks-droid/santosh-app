"""v0.287 APNE AAP SE BEHAS - the honesty guard stops arguing with itself (found in her own live test run: three
of seven replies ended with a "nothing was actually done" disclaimer she never asked for).

What really happened, reproduced on her exact text: the guard WROTE that disclaimer.

    "I haven't sent, saved, submitted or created anything"   -> claims_done() returned 'sent'
    "Nothing has been sent, saved, submitted or created"     -> claims_done() returned 'sent'

_DONE matches the bare English word `sent`, and _NOT_A_CLAIM - the list of phrasings that are NOT a claim - was
Hinglish only: aap ne, nahi bhej, hoga, agar. It had no English negation in it at all. So a perfectly honest
sentence read as a false claim of work done, and the loop ran:

    1. she asks for an explanation; Hoola writes a clean answer
    2. the guard sees a "claim" and nudges: "say plainly in one line that it is NOT done yet"
    3. the model obeys and writes "I haven't sent anything" - which contains `sent`
    4. that matches a SECOND time, and the second match staples SAID onto a pure explainer

Three fixes: English negation / future / offer forms in _NOT_A_CLAIM, a hard _ALREADY_HONEST guard so a reply
that already says it is not done is never nudged to say it again (the loop's root), and the note now speaks the
language the reply is written in - v0.260 made HER LANGUAGE the first rule, and this note is part of the reply.
"""
from app.agent import draftcheck as D

READS = [{"tool": "google_search", "ok": True}]          # a turn where nothing was actually DONE


def _run(text):
    st = {"calls": list(READS)}
    nudge = D.fake_done(st, text)
    D.fake_done(st, text)                                 # the second pass is what used to append the line
    return nudge, st.get("correct")


# ---------------------------------------------------------------- her own four replies
def test_her_replies_no_longer_trip_the_guard():
    for text in (
        "That was only an explanation. I haven't sent, saved, submitted or created anything: no template, "
        "no campaign and no messages.",
        "This was only a written note. Nothing has been sent, saved, submitted or created, so no template, "
        "campaign or file exists yet.",
        "Abhi maine kuch set ya save nahi kiya hai.",
    ):
        nudge, correct = _run(text)
        assert nudge == "" and correct is None, text[:40]


def test_an_offer_or_the_future_was_never_a_claim_and_still_is_not():
    for text in ("If you want a first campaign, send me the offer details and I'll draft the template.",
                 "Aap haan karenge to main mail bhej dunga.",
                 "I can send this once you approve it.",
                 "Shall I send it now?"):
        assert _run(text) == ("", None), text[:40]


# ---------------------------------------------------------------- the guard still does its job
def test_a_real_claim_with_nothing_behind_it_is_still_caught():
    for text in ("Maine aapka mail bhej diya hai.",
                 "Done - your invoice has been sent to the customer.",
                 "Reminder laga diya hai kal 10 baje ka.",
                 "Maine woh file save kar di hai."):
        nudge, correct = _run(text)
        assert nudge and "not the user" in nudge, text[:40]
        assert correct, text[:40]


def test_a_real_claim_is_left_alone_when_a_doing_tool_really_ran():
    st = {"calls": [{"tool": "send_email", "ok": True}]}
    assert D.fake_done(st, "Maine aapka mail bhej diya hai.") == ""


# ---------------------------------------------------------------- the loop itself
def test_the_guards_own_denial_cannot_retrigger_it():
    """Step 3 of the loop: the model obeys the nudge. What it writes must not count as a fresh claim."""
    st = {"calls": list(READS)}
    assert D.fake_done(st, "Maine aapka mail bhej diya hai.")              # 1st: a real claim, nudged
    obedient = "Saaf baat - maine abhi tak nahi kiya. Mail abhi bheja nahi hai; aap kahein to bhej dun."
    assert D.fake_done(st, obedient) == ""                                 # the denial is not a new claim
    assert st.get("correct") is None                                       # and nothing is stapled on


# ---------------------------------------------------------------- her language
def test_the_note_speaks_the_language_of_the_reply():
    assert D.said_line("Done - your invoice has been sent to the customer.") == D.SAID_EN
    assert D.said_line("Maine aapka mail bhej diya hai.") == D.SAID
    assert D.said_line("मैंने मेल भेज दिया है।") == D.SAID
    assert "(" in D.SAID_EN and D.SAID_EN.endswith(")")


def test_version():
    from app.main import APP_VERSION
    from pathlib import Path
    assert APP_VERSION == "0.289.0"
    assert "0.289.0+329" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
