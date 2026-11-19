"""v0.964 HOOLA CODE IN ORDER - her screen recording: the closing answer showed whole first, then the long message above
it started again from its first word. One check brought two new messages and the words already shown were handed to
the newest one (the closing answer). Pins: the hand-over goes to the message carrying the live words, and everything
after a still-landing message waits for it."""
from pathlib import Path

SRC = (Path(__file__).resolve().parents[2] / "lib/ui/code/code_session.dart").read_text(encoding="utf-8")


def test_handover_goes_to_message_with_live_words():
    assert "cs(x['text']).trim().startsWith(head)" in SRC
    assert "orElse: () => fresh.first" in SRC
    # the old rule (always the newest message) is gone
    assert "_landed['n$newest'] = _landed.remove('live')" not in SRC


def test_later_items_wait_for_landing_message():
    assert "if (_landBusy && _openN > -2 && sn0 > _openN && !_away) break;" in SRC
    assert "if (!running && !(_landBusy && !_away))" in SRC


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.18")
