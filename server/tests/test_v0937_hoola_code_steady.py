"""v0.937 HOOLA CODE STEADY (owner, her screen recording of a Hoola Code session: "REPLY TEXT LANDING ... VERY FAST AND
INSTANT", "ENTIRE CHAT SECTION VIBRATE", "BEFORE THINKING THERE SHOULD BE THE EXISTING HOOLA ANIMATE ICON", "FEED ... VERY
LARGE ... NEED ... 2 TO 3 LINER", "PLAN CARD ... HTML CREATION PREVIEW CARD ... COMING AND GOING").

ROOT CAUSE of the vibration and the cards coming and going: while a session waited on CI the server looked at its CI on
EVERY worker tick (~2 s, not once a minute as the code said) and marked the session "working" during each look - the
phone flipped between working and finished every second or two (the typing box, the PR card, the Thinking row, the
plan card's place all swapped)."""
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_a_ci_look_happens_once_a_minute_not_every_worker_tick():
    from app.devsahayak import service as S
    S._CI_AT.pop("tidX", None)
    assert [S._ci_due("tidX") for _ in range(3)] == [True, False, False]
    S._CI_AT["tidX"] = time.time() - 61
    assert S._ci_due("tidX") is True
    S._CI_AT.pop("tidX", None)
    src = (ROOT / "server/app/devsahayak/service.py").read_text()
    loop = src[src.index("for tenant, tid in looping:"):src.index("ci_threads.append(_ci_bg(tenant, tid, at))")]
    assert "if not _ci_due(tid):" in loop


def test_a_session_in_a_ci_look_is_not_working_on_her_screen():
    from app.devsahayak import service as S
    S._RUNNING.add("tq")
    S._QUIET.add("tq")
    try:
        assert S.running("tq") is False
    finally:
        S._RUNNING.discard("tq")
        S._QUIET.discard("tq")
    src = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert '"running": t.id in _RUNNING and t.id not in _QUIET' in src
    step = src[src.index("def _ci_step("):src.index('_SWEPT = {"at": 0.0}')]
    # every branch that starts real work (a fix round, the own review, the proof) says it is working
    assert step.count("_QUIET.discard(tid)") >= 5
    assert "return _round(" in step and "_QUIET.discard(tid)\n        return _round(" in step


def test_words_between_steps_are_two_or_three_lines_and_never_repeated():
    from app.devsahayak import engine as EN
    long = ("This is a rich, existing system. The owner already has a Team live-map and a per-technician monitor. "
            "She wants a dedicated owner panel. The repo has an established pattern for this. Let me read it.")
    short = EN.short_say(long)
    assert short.count(".") == 3 and long.startswith(short)          # a prefix: the phone's live words agree with it
    assert EN.short_say("Found it. Fixing now.") == "Found it. Fixing now."
    assert EN.short_say("Plan:\n- one\n- two") == "Plan:"
    a = "There's already a NetworkMap screen with technician positions and a track endpoint. Let me read its DTOs."
    b = "There's already a NetworkMap screen with technician positions and a track endpoint. Let me read its DTOs and screen."
    assert EN.said_before(b, [a]) and not EN.said_before("The tests pass now. Opening the pull request.", [a])
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    # v0.962 (owner: "GO BUILD 1 2 3" after the Claude Code comparison) the words are never cut any more - the model
    # keeps them short itself; short_say stays for older callers
    assert "LIVE_TEXT[tid] = txt[:20000]" in src and "txt = short_say(txt)" not in src
    assert "At most 40 words" in EN.SYSTEM and "**bold**" in EN.SYSTEM and "Never repeat" in EN.SYSTEM


def test_the_phone_is_steady_and_the_words_land_slowly():
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    words = (ROOT / "lib/ui/code/code_words.dart").read_text()
    md = (ROOT / "lib/ui/chat/hoola_md.dart").read_text()
    # no flip on a one-check gap, no scroll fight, the list end fixed
    assert "DateTime.now().difference(_runSeen!) < const Duration(seconds: 3)" in ses
    assert "final n = steps.length;" in ses
    assert "p.isScrollingNotifier.value" in ses   # v0.957 the one follow (_stick) never pulls against her scroll
    assert "a + r > 0 || _away ? 76 : 24" not in ses
    # the Hoola mark on the working row, one row kept between checks
    run = ses[ses.index("Widget _runningRow("):ses.index("Widget _changesPill(")]
    assert "const HoolaMark(size: 22)" in run and "ValueKey('working')" in run and "'>_'" not in run
    # slower landing, each word fading in; the closing answer lands too
    assert "CodeLanding.msPerWord(waiting)" in words and "sans: true, fade: true" in words
    assert "final bool fade;" in md and "_fadeSteps = [.82, .62, .42, .22]" in md
    assert "_land(ex, 'explain', done: true, actions: true)" in ses


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.107"' in main
    assert "version: 0.999.107+1102" in (ROOT / "pubspec.yaml").read_text()
