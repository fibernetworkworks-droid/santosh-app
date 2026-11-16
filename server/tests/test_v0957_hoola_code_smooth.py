"""v0.957 HOOLA CODE SMOOTH (owner, her screen recording: "CHECK HOW THE PLAN CARD VIBRATES ... A REPLY LANDS VERY FAST
IT MUST BE PERFECT SMOOTH AND CONSISTENT AND MEDIUM SLOW ... CHAT LANDING, CONVERSATION FLAWS"). Seen frame by frame:
(1) the plan was a ~300 px card at the END of the thread, under the words being written - every wrapped word and every
coming and going of the working row pushed it; (2) the working row vanished while words streamed and came back (44 px
each time); (3) two scroll moves fought (a 260 ms slide, then a snap to the true end); (4) words landed at ~19 a second
and leapt to ~38 with a backlog; (5) two messages could land at once in two places. The phone code is Dart (CI compiles
it); these pins hold each fix in the source."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSION = (ROOT / "lib/ui/code/code_session.dart").read_text()
WORDS = (ROOT / "lib/ui/code/code_words.dart").read_text()


def test_plan_is_a_dock_not_a_card_in_the_thread():
    assert "Widget _planDock(" in SESSION and "_todoItems(t).isNotEmpty) _planDock(c, _todoItems(t))" in SESSION
    assert "_todo(c, cl(todo['items']))" not in SESSION and "Widget _todo(" not in SESSION
    # one steady line: the step it is on, the count, a bar that slides; every step only after her tap
    assert "_planOpen = !_planOpen" in SESSION and "TweenAnimationBuilder<double>" in SESSION and "AnimatedSize(" in SESSION


def test_working_row_stays_last_while_words_stream():
    assert "if (running) out.add(_runningRow(c, t, nowGroup));" in SESSION
    assert "running && live.isEmpty && !drewRunning" not in SESSION and "drewRunning" not in SESSION


def test_one_follow_mechanism():
    assert "void _stick()" in SESSION and "NotificationListener<ScrollMetricsNotification>" in SESSION
    assert "findChildIndexCallback: (k) => at[k]" in SESSION
    # the slide that raced the snap is gone from the follow paths (the Newest button still slides)
    assert "_toEnd(animate: !first)" not in SESSION and "_toEnd(animate: false);" not in SESSION.split("void _landedTo")[1][:600]


def test_landing_pace_is_medium_slow_and_even():
    assert "CodeLanding.msPerWord(waiting)" in WORDS and "(waiting > 160 ? 26 : 52)" not in WORDS
    import re
    body = WORDS.split("static double msPerWord(int waiting) {")[1].split("\n  }")[0]
    slow = float(re.search(r"slow = ([\d.]+)", body).group(1))
    fast = float(re.search(r"fast = ([\d.]+)", body).group(1))
    assert 80 <= slow <= 110 and 40 <= fast < slow          # ~9-12 words a second, a backlog never past ~25
    assert "smoothstep" in body                             # the pace eases, never a step


def test_one_message_lands_at_a_time():
    assert "this.hold = false" in WORDS and "if (widget.hold) {" in WORDS
    assert "hold: hold," in SESSION and "_landBusy = false;" in SESSION and "_landTotal[i] = total;" in SESSION
