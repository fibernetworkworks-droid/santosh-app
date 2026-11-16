"""v0.938 HOOLA CODE CLOCK BESIDE (owner, her phone screenshot: "THINKING ... HAS TIMING AT EXTREEM CORNER ... MAKE IT NEAR
TO THINKING ... WITH MATCHING FONT WITH THINKING"): the working row's clock follows its words in the same font."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_clock_sits_beside_the_words_in_the_same_font():
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    run = ses[ses.index("Widget _runningRow("):ses.index("Widget _changesPill(")]
    assert "Flexible(" in run and "Expanded(" not in run                    # nothing pushes the clock to the far edge
    assert "Text('· ${codeClock(secs)}'" in run
    assert "codeSans(c, size: 16, color: c.ink3).copyWith(fontFeatures: const [FontFeature.tabularFigures()])" in run
    assert "codeMono(c, size: 12" not in run                                 # the small mono clock is gone
    assert "codeSans(c, size: 16, color: c.ink2)" in run                     # the words beside it: same sans, same size


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.955.0"' in main
    assert "version: 0.955.0+954" in (ROOT / "pubspec.yaml").read_text()
