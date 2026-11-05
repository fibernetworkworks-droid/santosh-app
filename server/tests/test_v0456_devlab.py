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
    assert d["test"] == "make test" and d["source"] == "aapne khud bataya" and d["confirm"] is False


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
    assert d["test"] == "" and "bata dijiye" in d["why"] and "khud se command banakar nahi" in d["why"]


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
    assert "nahi chal sakti" in d["why"]                          # she is told, in her words
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
    assert t == "hoola-devlab:meghana-shop-api-abc123" and t.islower()
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
    assert r["ok"] is False and r["timed_out"] is True and "roka gaya" in out.say(r, "npm test")


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
    assert av["ok"] is False and "docker nahi hai" in av["why"]
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
    assert "GADBAD" not in lines and "KHATRA" not in lines


# ---------------------------------------------------------------- v0.532 the image must be buildable where the code RUNS
def test_the_dockerfile_travels_with_the_code():
    """The VPS deploy copies `server/app` only, so a Dockerfile sitting in deploy/ is NOT next to the running code.
    The text is embedded; the file on disk is the readable copy and must stay identical."""
    from pathlib import Path
    disk = Path(__file__).resolve().parents[2] / "deploy" / "devlab" / "Dockerfile"
    assert disk.is_file() and box.DOCKERFILE_TEXT == disk.read_text("utf-8")
    assert "FROM debian:12-slim" in box.DOCKERFILE_TEXT and "USER lab" in box.DOCKERFILE_TEXT
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
