"""v0.924 HOOLA CODE FIRST SCREEN (owner, on her Claude Code screenshot: "WE WANT SAME ... FOR HOOLA CODE WHEN ITS OWN
HOOLA CODE CHAT SESSION ... AND BAR" -> design canvas claude.ai/artifact/Au9zBc5gmkVsNLwVc41rCM -> "GO"): a session starts
on its own New session screen, and the same pill bar is the typing box inside every session."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "lib/ui/code"
START = (CODE / "code_start.dart").read_text()
HOME = (CODE / "code_home.dart").read_text()
SESSION = (CODE / "code_session.dart").read_text()
API = (ROOT / "server/app/devsahayak/api.py").read_text()


def test_the_first_screen_is_the_design():
    assert "class CodeNewSessionPage extends StatefulWidget" in START
    assert "'New session'" in START and "'Ready when you are'" in START
    assert "HoolaMark(size: 58)" in START                    # Hoola's own mark, not anyone else's character
    assert "'Type or hold to talk'" in START
    assert "'Add repository'" in START and "CodeGitHubIcon" in START   # the repository chip
    assert "_pickEnv" in START and "'Environment'" in START  # the environment chip + sheet
    assert "'Branch to work from'" in START and "/api/devsahayak/branches" in START


def test_the_bar():
    assert "class CodeBar extends StatefulWidget" in START
    # send is grey until there are words; Stop only while Hoola works and the field is empty
    assert "fill: live && widget.onSend != null ? c.pill : c.navOn" in START
    assert "final stop = widget.onStop != null && !hasWords && !widget.canSendEmpty;" in START
    # the mic: tap = dictate, hold = talk, slide left = cancel, let go = send
    for s in ("onLongPressStart", "onLongPressMoveUpdate", "offsetFromOrigin.dx < -70", "onLongPressEnd", "'Slide left to cancel'", "'Let go to send'"):
        assert s in START, s
    assert "if (hold && !_pressing) return;" in START       # a quick let-go never leaves the mic on
    assert "widget.controller.text = _before;" in START      # cancel puts her words back
    assert "HoolaMotion.reduced(context)" in START           # the wave stands still under reduce motion


def test_nothing_starts_without_her_tap():
    # the only start is the send button; the body carries the environment she picked
    assert START.count("'/api/devsahayak/tasks/start'") == 1
    assert "'env': _env.isEmpty ? 'auto' : _env" in START
    assert '@r.post("/tasks/start")' in API and 'b.get("env")' in API
    assert '@r.get("/envs")' in API and '@r.put("/tasks/{tid}/env")' in API


def test_home_and_session_use_it():
    assert "class CodeComposer" not in HOME                  # the old in-page composer is gone
    assert "CodeMain('New session'" in HOME and "_newSession(fill)" in HOME
    assert "CodeBar(" in SESSION and "onStop: running ? () => _run('POST', '$_base/stop') : null" in SESSION
    assert "'$_base/env'" in SESSION and "_pickEnv(t)" in SESSION
    assert "TextField(" not in SESSION                        # one typing box: the bar


def test_design_rules():
    for src in (START, HOME, SESSION):
        assert "Color(0x" not in src
        assert "glass.dart'" not in src and "BackdropFilter" not in src and "ImageFilter.blur" not in src
        assert not re.search(r"FontWeight\.w(800|900)", src)
        for m in re.findall(r"code(?:Sans|Mono)\(c, size: (\d+(?:\.\d+)?)", src):
            assert float(m) >= 12, m


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.21"' in main and "HOOLA CODE" in main
    assert "version: 0.999.21+1019" in (ROOT / "pubspec.yaml").read_text()


def test_v0925_bar_has_one_outline():
    """v0.925 (owner, her phone: a second outlined box drawn round 'Type or hold to talk'): the app theme's
    enabledBorder / focusedBorder / filled win over border: InputBorder.none, so every bare field turns them all off."""
    kit = (CODE / "code_kit.dart").read_text()
    i = kit.index("InputDecoration codeBareInput(")
    body = kit[i:i + 1200]
    for k in ("filled: false", "enabledBorder: InputBorder.none", "focusedBorder: InputBorder.none",
              "disabledBorder: InputBorder.none", "errorBorder: InputBorder.none", "focusedErrorBorder: InputBorder.none"):
        assert k in body, k
    assert "decoration: codeBareInput(c, hint: widget.hint)" in START
    assert "decoration: codeBareInput(c, hint: 'Search your repositories'" in START
    assert "border: InputBorder.none" not in START          # no field here relies on border alone any more
    comp = (ROOT / "lib/ui/shell/hoola_computer.dart").read_text()
    assert "enabledBorder: InputBorder.none" in comp and "filled: false" in comp
