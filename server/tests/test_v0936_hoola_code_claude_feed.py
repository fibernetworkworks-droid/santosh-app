"""v0.936 HOOLA CODE LIKE CLAUDE CODE'S CHAT (owner, on her Claude Code screenshots: "A PERFECT SMALL 2 SENTENCE FEED AND
COMMAND RUN, CREATED FILES ETC IN FAINT" + "COMMAND RUN/RAN ... DONT EXPOSE THE RUN COMMAND TILL USER CLICK ON ARROW" ->
design canvas claude.ai/artifact/27Hw4XRUj5qG83sWaeX2J5 round 2 -> "PERFECT. DEPLOY"): short words before each part of
the work, every part one faint line, a sheet of steps with plain descriptions, the command only under its arrow."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_every_command_gets_plain_words():
    from app.devsahayak import engine as EN
    assert EN.cmd_words("cd app && ./gradlew test", "run the unit tests.") == "Run the unit tests"
    assert EN.cmd_words("python -m pytest -q tests/") == "Run the tests"
    assert EN.cmd_words("npm ci") == "Install the dependencies"
    assert EN.cmd_words("grep -rn startService app/src") == "Search the files"
    assert EN.cmd_words("git diff") == "Look at the changes"
    assert EN.cmd_words("echo hi") == "Run a command"
    assert EN.now_words("bash", {"command": "./gradlew test", "description": "Run the unit tests"}) == "Running the unit tests"
    assert EN.now_words("bash", {"command": "pytest"}) == "Running the tests"
    assert EN.now_words("read", {"path": "app/src/LoginActivity.java"}) == "Reading LoginActivity.java"
    assert EN.now_words("grep", {"pattern": "x"}) == "Searching the code"
    assert "./gradlew" not in EN.now_words("bash", {"command": "./gradlew test"})          # never the raw command


def test_the_command_tool_takes_a_description_and_the_step_carries_it():
    import inspect

    from app.devsahayak import engine as EN
    bash = next(t for t in EN.TOOLS if t["name"] == "bash")
    assert "description" in bash["input_schema"]["properties"]
    assert "description" in inspect.signature(EN.Tools.t_bash).parameters
    tools = EN.Tools.__new__(EN.Tools)
    tools.last_bash = {"cmd": "./gradlew test", "rc": 0, "secs": 41, "tail": ["BUILD SUCCESSFUL"]}
    ev = EN.event(tools, "bash", {"command": "./gradlew test", "description": "Run the unit tests"}, "ok")[0]
    assert ev["desc"] == "Run the unit tests" and ev["cmd"] == "./gradlew test"
    assert "Before each set of tool calls, write one or two short sentences" in EN.SYSTEM
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "NOW_STEP[tid] = now_words(b[\"name\"], inp)" in src and "NOW_STEP.pop(tid, None)" in src


def test_the_view_says_what_runs_now_and_which_model():
    from app.devsahayak import engine as EN
    from app.devsahayak import service as S
    EN.NOW_STEP["t9"] = "Running the unit tests"
    assert S._now_step("t9") == ""
    S._RUNNING.add("t9")
    try:
        assert S._now_step("t9") == "Running the unit tests"
    finally:
        S._RUNNING.discard("t9")
        EN.NOW_STEP.pop("t9", None)
    src = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert '"now": _now_step(t.id)' in src and '"model_label": _model_label(t)' in src


def test_the_phone_draws_claude_codes_feed():
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    words = (ROOT / "lib/ui/code/code_words.dart").read_text()
    md = (ROOT / "lib/ui/chat/hoola_md.dart").read_text()
    kit = (ROOT / "lib/ui/code/code_kit.dart").read_text()
    start = (ROOT / "lib/ui/code/code_start.dart").read_text()
    # each part = one faint line that opens the steps sheet
    assert "Widget _group(HoolaColors c, List<Map<String, dynamic>> g)" in ses and "onTap: () => _openSteps(label, g)" in ses
    assert "'ran ${cPlural(n({'bash'}), 'command')}'" in ses
    # the running line: the Hoola mark (v0.937, was >_) and her words, never the command
    run = ses[ses.index("Widget _runningRow("):ses.index("Widget _changesPill(")]
    assert "HoolaMark(" in run and "cs(t['now'])" in run and "cmd" not in run
    # the sheet: X + title, "Ran" + plain words, the command only under the arrow
    sheet = words[words.index("class CodeStepsSheet"):]
    assert "'Ran', _s(s['desc'])" in sheet and "Icons.close_rounded" in sheet
    assert "if (open) Padding(padding: const EdgeInsets.only(bottom: 12), child: _detail(c, s))" in sheet
    assert "'\\$ ${_s(s['cmd'])}'" in sheet                       # the command lives only in the opened detail
    # top bar, floating changes, words in the sans, suggestion inside the box
    assert "centered: true," in ses and "final bool centered;" in kit
    assert "if (a + r > 0) _changesPill(c, a, r)" in ses
    assert "sans: true" in words and "final bool sans;" in md
    assert "final Widget? top;" in start and "top: hint.isNotEmpty && _msg.text.isEmpty" in ses


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.981.0"' in main
    assert "version: 0.981.0+980" in (ROOT / "pubspec.yaml").read_text()
