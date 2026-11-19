"""v0.456 PRAYOGSHALA - the coding lab (owner: Docker on the VPS yes, third-party repos too, setup + cached snapshot).

Hoola runs HER DECLARED check on a repo's code in a locked Docker box, because without a command that comes back pass
or fail an agent only knows "looks done" (docs/CODING_HARNESS_PLAN.md 1.2). The tests below cover the parts that must
be right whether or not Docker exists on the machine running them: the command is DECLARED and never invented, a
command we read from her repo needs one tap, the output is shaped FAILURE-FIRST with a greppable log, and the snapshot
cache key moves only when the dependency files move. The box's own walls (no network, read-only root, non-root user)
are checked by `python -m app.devlab check` on the VPS and, where Docker is available, by the last test here."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.devlab import box, out, service, spec

AGENTS = """# Shop API

## Commands
- Install: pip install -e .
- Run one test file: python3 -m pytest -q tests/test_calc.py
- Typecheck: mypy app
"""
CI = """name: CI
on: [pull_request]
jobs:
  t:
    steps:
      - run: pip install -r requirements.txt
      - run: python -m pytest -q
"""


def _docker() -> bool:
    return bool(box.docker()) and box.available()["ok"]


docker_only = pytest.mark.skipif(not _docker(), reason="no docker on this machine (the VPS has it)")


# ---------------------------------------------------------------- the command is declared, never invented
def test_her_own_command_wins_and_needs_no_tap():
    d = spec.discover(["pyproject.toml"], {"AGENTS.md": AGENTS}, {"test": "make test"})
    assert d["test"] == "make test" and d["source"] == "given by you" and d["confirm"] is False


def test_the_repo_rules_beat_its_ci_and_the_language_default():
    d = spec.discover(["pyproject.toml", "tests/test_calc.py", ".github/workflows/ci.yml"],
                      {"AGENTS.md": AGENTS, ".github/workflows/ci.yml": CI, "pyproject.toml": "[project]\n"})
    assert d["test"] == "python3 -m pytest -q tests/test_calc.py" and d["source"] == "AGENTS.md"
    assert d["setup"] == "pip install -e ."                      # the labelled install line, not the language default
    assert d["confirm"] is True                                  # Hoola read it, so it waits for one tap
    assert [c["source"] for c in d["candidates"]][-1].endswith("ci.yml") or any(
        c["source"].endswith("ci.yml") for c in d["candidates"])


def test_a_repo_file_can_state_it_outright_and_is_trusted():
    d = spec.discover(["package.json"], {".hoola/lab.json": json.dumps({"test": "npm run ci", "setup": "npm ci",
                                                                        "timeout": 120})})
    assert d["test"] == "npm run ci" and d["setup"] == "npm ci" and d["confirm"] is False and d["timeout"] == 120


def test_nothing_declared_means_nothing_runs():
    d = spec.discover(["main.c", "Makefile.in"], {})
    assert d["test"] == "" and "Tell Hoola the command" in d["why"] and "will not make up a command" in d["why"]


def test_commands_that_are_refused_outright():
    for bad in ("sudo make test", "docker run x", "npm test && sudo reboot", "while true; do npm test; done",
                "export API_KEY=sk-live-123 && pytest", "x" * 500, ""):
        assert spec.refuse_reason(bad), bad
    for ok in ("npm test --silent", "python3 -m pytest -q tests/test_x.py", "./gradlew test", "make check",
               "go test ./...", "cargo test"):
        assert spec.refuse_reason(ok) == "", ok


def test_a_refused_command_is_reported_never_quietly_swapped():
    d = spec.discover(["pyproject.toml"], {"AGENTS.md": "## Testing\n- Test: sudo pytest\n",
                                           "pyproject.toml": "[project]\nname='x'\n"})
    assert d["refused"] and d["refused"][0]["cmd"] == "sudo pytest" and d["refused"][0]["source"] == "AGENTS.md"
    assert "cannot be run" in d["why"]                          # she is told, in her words
    assert d["test"] == "python3 -m pytest -q" and d["confirm"] is True   # the offer still waits for her tap


def test_the_language_default_is_the_last_resort_and_still_asks():
    d = spec.discover(["pyproject.toml", "app/x.py"], {"pyproject.toml": "[project]\nname='x'\n"})
    assert d["lang"] == "python" and d["test"] == "python3 -m pytest -q"
    assert d["source"] == "python default" and d["confirm"] is True


# ---------------------------------------------------------------- the snapshot cache key
def test_the_snapshot_key_moves_only_with_the_dependency_files():
    a = {"requirements.txt": "flask==3.0\n", "app/x.py": "print(1)\n"}
    b = {"requirements.txt": "flask==3.0\n", "app/x.py": "print(2)\n"}          # code changed
    c = {"requirements.txt": "flask==3.1\n", "app/x.py": "print(1)\n"}          # a dependency changed
    assert spec.deps_key(a) == spec.deps_key(b) != spec.deps_key(c)
    assert spec.deps_key({}) == spec.deps_key({"README.md": "hi"})
    assert len(spec.deps_key(a)) == 16


def test_the_image_tag_is_per_repo_and_per_key():
    t = service.image_for("Meghana/Shop-API", "abc123")
    assert t == f"hoola-devlab:meghana-shop-api-r{box.BASE_REV}-abc123" and t.islower()
    assert service.image_for("a/b", "k1") != service.image_for("a/b", "k2")


# ---------------------------------------------------------------- failure-first output (our correction of the contract)
def test_a_failure_keeps_its_END_and_hands_back_the_log():
    text = "collecting ...\n" + ("noise\n" * 20000) + "E   assert 0 == 1\nFAILED tests/test_calc.py::test_empty\n"
    r = out.shape(text, 1, "/tmp/run.log", 4.2)
    assert r["ok"] is False and r["cut"] > 0 and r["log"] == "/tmp/run.log"
    assert r["shown"].rstrip().endswith("FAILED tests/test_calc.py::test_empty")   # the end survives, not the start
    assert "collecting ..." in r["shown"] and "cut from the middle" in r["shown"]
    assert r["bytes"] == len(text) and "grep" in r["shown"]
    assert len(r["shown"]) < len(text)


def test_a_pass_is_shown_short_because_nobody_debugs_a_pass():
    r = out.shape("ok\n" * 10000, 0, "/tmp/run.log", 1.0)
    assert r["ok"] is True and len(r["shown"]) <= out.PASS_HEAD + 120 and "it passed" in r["shown"]
    assert out.shape("2 passed\n", 0, "", 0.4)["shown"] == "2 passed\n"


def test_a_timeout_is_not_a_pass():
    r = out.shape("still running", 124, "/tmp/x.log", 600.0, timed_out=True)
    assert r["ok"] is False and r["timed_out"] is True and "was stopped" in out.say(r, "npm test")


def test_the_log_can_be_asked_a_second_question():
    folder = tempfile.mkdtemp()
    try:
        body = "\n".join([f"line {i}" for i in range(500)] + ["E   assert total([]) == 0", "FAILED test_calc.py"])
        p = out.write_log(folder, "run one!", body)
        assert p and Path(p).is_file() and oct(Path(p).stat().st_mode)[-3:] == "600"
        hit = out.grep_log(p, "assert")
        assert "assert total" in hit and "line 49" in hit                  # the lines around it come too
        assert "No line of the log matches" in out.grep_log(p, "zzz-not-here")
        assert "Give a pattern" in out.grep_log(p, "")
        assert "log is gone" in out.grep_log(folder + "/nope.log", "x")
        assert out.grep_log(p, "[unclosed(") .count("line") >= 0          # a broken regex falls back to substring
        assert "FAILED test_calc.py" in out.tail(p, 5)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_grep_answers_are_capped():
    folder = tempfile.mkdtemp()
    try:
        p = out.write_log(folder, "big", "\n".join(["match me"] * 5000))
        ans = out.grep_log(p, "match")
        assert len(ans) <= out.GREP_MAX and ans.count("match me") < 5000
    finally:
        shutil.rmtree(folder, ignore_errors=True)


# ---------------------------------------------------------------- the walls, in code (no docker needed to read them)
def test_a_check_is_given_no_network_and_no_powers():
    a = box._limits(network=False)
    assert "--network" in a and a[a.index("--network") + 1] == "none"
    assert a[a.index("--user") + 1] == "1000:1000" and "--read-only" in a
    assert a[a.index("--cap-drop") + 1] == "ALL" and a[a.index("--security-opt") + 1] == "no-new-privileges"
    assert a[a.index("--memory") + 1] == box.MEM and a[a.index("--pids-limit") + 1] == box.PIDS
    assert not any("ANTHROPIC" in x or "API_KEY" in x or "TOKEN" in x for x in a)      # no secret can ride in
    s = box._limits(network=True)
    assert s[s.index("--network") + 1] == "bridge"                 # only the one-time setup step gets a route out


def test_the_box_says_why_when_docker_is_missing(monkeypatch):
    monkeypatch.setattr(box, "docker", lambda: "")
    av = box.available()
    assert av["ok"] is False and "docker is not on this machine" in av["why"]
    assert service.check("a/b")["stage"] == "box"                  # and a run stops there, with that reason
    assert box.run_in("img", "/tmp", "true")["rc"] == 127 and box.images() == [] and box.has_image("x") is False


def test_a_clone_never_leaves_the_token_behind(monkeypatch, tmp_path):
    seen = {}

    def fake_run(argv, cwd=None, env=None, capture_output=True, text=True, timeout=None):
        seen["argv"], seen["env"] = list(argv), dict(env or {})
        Path(cwd, ".git").mkdir(parents=True, exist_ok=True)
        Path(cwd, ".git", "config").write_text("[remote]\n  url = https://x-access-token:SEKRIT@github.com/a/b.git\n")
        Path(cwd, "app.py").write_text("x = 1\n")

        class R:
            returncode, stdout, stderr = 0, "cloned SEKRIT", ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    m = service.materialize("a/b", "main", "SEKRIT")
    try:
        assert m["ok"] and "app.py" in m["paths"]
        assert not Path(m["dir"], ".git").exists()                 # history, remote and credentials are stripped
        assert not any("SEKRIT" in x for x in seen["argv"])        # the token is never an argument (ps would show it)
        assert seen["env"].get("GIT_ASKPASS", "").endswith(".sh") and seen["env"]["GIT_TERMINAL_PROMPT"] == "0"
        assert not list(Path(m["dir"]).glob("hoola-ask-*"))        # the askpass file is deleted
    finally:
        shutil.rmtree(m.get("dir", "/nonexistent"), ignore_errors=True)


def test_a_declared_command_that_was_only_read_waits_for_one_tap(monkeypatch, tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "AGENTS.md").write_text(AGENTS)
    monkeypatch.setattr(box, "available", lambda: {"ok": True, "docker": "27", "base_built": True})
    monkeypatch.setattr(service, "materialize", lambda *a, **k: {"ok": True, "dir": str(tmp_path),
                                                                 "paths": ["pyproject.toml", "AGENTS.md"], "mb": 1})
    monkeypatch.setattr(box, "run_in", lambda *a, **k: pytest.fail("nothing may run before her haan"))
    r = service.check("a/b")
    assert r["ok"] is False and r["stage"] == "confirm" and "AGENTS.md" in r["why"]
    assert r["spec"]["test"] == "python3 -m pytest -q tests/test_calc.py"


# ---------------------------------------------------------------- with docker: the walls really hold
@docker_only
def test_the_real_box_is_sealed():
    for line in service.selftest():
        print(line)
    lines = "\n".join(service.selftest())
    assert "PROBLEM" not in lines and "DANGER" not in lines


# ---------------------------------------------------------------- v0.532 the image must be buildable where the code RUNS
def test_the_dockerfile_travels_with_the_code():
    """The VPS deploy copies `server/app` only, so a Dockerfile sitting in deploy/ is NOT next to the running code.
    The text is embedded; the file on disk is the readable copy and must stay identical."""
    from pathlib import Path
    disk = Path(__file__).resolve().parents[2] / "deploy" / "devlab" / "Dockerfile"
    assert disk.is_file() and box.DOCKERFILE_TEXT == disk.read_text("utf-8")
    assert "FROM python:3.13-slim-bookworm" in box.DOCKERFILE_TEXT and "USER lab" in box.DOCKERFILE_TEXT
    assert "\\\n" in box.DOCKERFILE_TEXT                     # the line continuations survived the embedding


def test_a_build_writes_the_dockerfile_itself(monkeypatch, tmp_path):
    seen = {}

    def fake(argv, timeout, cwd=""):
        seen["argv"] = list(argv)
        from pathlib import Path
        i = argv.index("-f")
        seen["text"] = Path(argv[i + 1]).read_text("utf-8")
        return 0, "built", 3.0
    monkeypatch.setattr(box, "docker", lambda: "/usr/bin/docker")
    monkeypatch.setattr(box, "_run", fake)
    monkeypatch.setattr(box, "DOCKERFILE", tmp_path / "nope" / "Dockerfile")   # the disk copy is NOT there
    r = box.build_base()
    assert r["ok"] and r["image"] == box.BASE_IMAGE
    assert seen["text"] == box.DOCKERFILE_TEXT and "--no-cache" not in seen["argv"]


# ---------------------------------------------------------------- v0.533 the switch is ON, and this repo declares its own
def test_the_lab_is_on_now_that_her_walls_held():
    from app.config import get_settings
    assert get_settings().dev_lab is True            # lab_check on her VPS: every wall held, 5 Nov 2026
    assert get_settings().dev_lab_timeout >= 300 and get_settings().dev_lab_keep >= 4


def test_this_repo_declares_its_own_commands_and_never_asks():
    """`.hoola/lab.json` is the one place a repo can state this outright - so the lab needs no tap on OUR repo."""
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / ".hoola" / "lab.json"
    assert p.is_file()
    d = json.loads(p.read_text("utf-8"))
    assert d["test"] == "cd server && python3 -m pytest -q -p no:randomly"
    assert "server/requirements.txt" in d["setup"] and d["timeout"] >= 600
    got = spec.discover([".hoola/lab.json", "server/requirements.txt"], {".hoola/lab.json": json.dumps(d)})
    assert got["test"] == d["test"] and got["setup"] == d["setup"] and got["confirm"] is False
    assert spec.refuse_reason(d["test"]) == "" and spec.refuse_reason(d["setup"]) == ""


# ---------------------------------------------------------------- v0.537 what her first live lab_try found
def test_setup_may_keep_what_it_writes_and_a_check_still_cannot():
    """The silent half of the v0.537 bug. `docker commit` keeps neither a read-only root nor a tmpfs, so the old
    walls threw every installed dependency away while reporting the snapshot cached - fast and wrong."""
    s = box._limits(network=True, writable=True)
    assert "--read-only" not in s                              # ... or the install cannot land anywhere
    assert not any(x.startswith("/home/lab:") for x in s)      # ... and nothing masks where it lands
    assert s[s.index("--user") + 1] == "1000:1000"             # every other wall stands
    assert s[s.index("--cap-drop") + 1] == "ALL" and s[s.index("--security-opt") + 1] == "no-new-privileges"
    assert s[s.index("--memory") + 1] == box.MEM and s[s.index("--pids-limit") + 1] == box.PIDS
    c = box._limits(network=False)
    assert "--read-only" in c and c[c.index("--network") + 1] == "none"
    assert not any(x.startswith("/home/lab") for x in c)       # the committed dependencies stay VISIBLE at check time
    assert f"HOME={box.CHECK_HOME}" in c and box.CHECK_HOME.startswith("/tmp/")   # ... with a writable home in the tmpfs
    assert f"HOME={box.SETUP_HOME}" in s
    assert f"PYTHONUSERBASE={box.USER_BASE}" in c              # ... and `pip --user` packages are still importable
    assert any(x.startswith(f"PATH={box.USER_BASE}/bin:") for x in c)


def test_no_caller_can_unseal_a_check(monkeypatch):
    """Writability is derived from commit_to, never asked for: there is no flag that makes a check writable."""
    import inspect
    assert "writable" not in inspect.signature(box.run_in).parameters
    seen: dict = {}
    monkeypatch.setattr(box, "docker", lambda: "/usr/bin/docker")
    monkeypatch.setattr(box, "_run", lambda argv, timeout, cwd="": (seen.setdefault("argv", argv), (0, "", 0.1))[1])
    box.run_in("img", ".", "pytest -q", network=False)
    assert "--read-only" in seen["argv"] and "none" in seen["argv"]
    assert 'mkdir -p "$HOME"' in seen["argv"][-1] and seen["argv"][-1].endswith("pytest -q")


def test_the_image_lets_a_repo_run_its_own_pip_command():
    """What spoke on 5 Nov: `error: externally-managed-environment`. A container IS the virtual environment, so the
    PEP 668 marker comes off once in the image - Hoola never rewrites a repo's declared command to get around it."""
    t = box.DOCKERFILE_TEXT
    assert "rm -f /usr/lib/python3*/EXTERNALLY-MANAGED" in t
    assert "--break-system-packages" not in t                   # ... so no command here needs the escape hatch
    assert "/home/lab/.local/bin" in t and "chown -R lab:lab /work /home/lab" in t
    import json
    from pathlib import Path
    d = json.loads((Path(__file__).resolve().parents[2] / ".hoola" / "lab.json").read_text("utf-8"))
    assert "--break-system-packages" not in d["setup"] and "--user" not in d["setup"]


def test_a_stale_image_is_named_and_rebuilt_not_used_quietly(monkeypatch):
    """Her VPS already held the pre-v0.537 image, and nothing in the old code could have told her so."""
    monkeypatch.setattr(box, "docker", lambda: "/usr/bin/docker")
    monkeypatch.setattr(box, "_run", lambda argv, timeout, cwd="": (
        (0, "29.8.1", 0.1) if "version" in argv else
        (0, "abc123", 0.1) if "images" in argv else
        (0, "1", 0.1) if "inspect" in argv else (0, "", 0.1)))
    av = box.available()
    assert av["ok"] is True and av["base_built"] is True
    assert av["base_stale"] is True and av["base_rev"] == "1" and av["base_rev_wanted"] == box.BASE_REV
    assert "old" in av["why"] and "--rebuild" in av["why"]
    assert f'LABEL hoola.devlab.rev="{box.BASE_REV}"' in box.DOCKERFILE_TEXT
    built = []
    monkeypatch.setattr(box, "build_base", lambda nocache=False: built.append(nocache) or {"ok": False, "why": "x"})
    lines = service.selftest()
    assert built == [True]                                        # a stale image is rebuilt from scratch, not reused
    assert any("OLD" in ln for ln in lines)


def test_the_selftest_proves_an_install_survives_the_commit():
    """The two stages that would have caught v0.537 before she ever ran it."""
    src = (Path(service.__file__).read_text("utf-8") if hasattr(service, "__file__") else "")
    assert "the repo's own `pip install` works" in src and "the install stays in the snapshot" in src
    assert "commit_to=tag" in src and "network=True" in src       # the real road: install with the net, then commit
    assert "import tabulate" in src                               # ... and ask the committed image for it back


# ---------------------------------------------------------------- v0.542 the box must speak her server's Python
def test_the_box_runs_the_same_python_as_the_server():
    """Her first WORKING lab_try died on app/notebook/render.py:517 - a backslash inside an f-string expression,
    which PEP 701 allows from 3.12 and Debian 12's python3 (3.11) refuses. The code is right; the box was wrong.
    A lab on another language version does not test her code, it invents failures."""
    t = box.DOCKERFILE_TEXT
    assert "FROM python:3.13-slim-bookworm" in t
    assert "python3-dev" not in t and "python3-venv" not in t    # apt's 3.11 must not shadow or mislead
    assert box.BASE_REV == "3"                                   # ... and her built image is named stale until rebuilt
    src = Path(service.__file__).read_text("utf-8")
    assert "box Python" in src and "sys.version_info" in src  # the self-test compares and says PROBLEM
    assert "render.py:517" in t                                  # the reason is written where the image is


def test_her_code_is_not_rewritten_to_suit_the_box():
    """The 3.12+ f-string stays: it is valid Python for the version she runs. The box moved, not her code."""
    p = Path(__file__).resolve().parents[1] / "app" / "notebook" / "render.py"
    assert "re.sub(r'^\\s*[-*•]\\s+', '', ln)" in p.read_text("utf-8")


def test_a_base_image_change_invalidates_every_repo_snapshot():
    """A snapshot is built ON the base. Keyed on lock files alone, her existing 3.11 snapshot would have been
    served on the new 3.13 base - cached, fast, and failing exactly as before."""
    tag = service.image_for("owner/repo", "abc123")
    assert f"-r{box.BASE_REV}-" in tag and tag.endswith("-abc123")
    assert service.image_for("owner/repo", "abc123") != tag.replace(f"-r{box.BASE_REV}-", "-r1-")
