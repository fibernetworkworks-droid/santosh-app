"""v0.955 HOOLA CODE ASK FIRST (owner: "Done, check" -> hard card 11/12 on v0.952: the vague ask still guessed - 26 steps,
628 s, changed _probe.py + tests/test_api.py despite the note and the done reminder): a no-symptom ask is now enforced in
code - writes refused, a short step cap, anything changed (even by a command) undone at the end, and the closing words
always hold ONE question."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


def test_ask_only_refuses_writes_and_the_round_is_undone(tmp_path, monkeypatch):
    from app.devsahayak import engine as EN
    monkeypatch.setattr(EN, "folder", lambda tid: tmp_path / tid)
    ses = EN.Session("t1")
    repo = ses.repo
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty", "-m", "base")
    (repo / "app.py").write_text("x = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "-m", "app")
    ses.meta["round_base"] = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    tools = EN.Tools(ses, False)
    tools.ask_only = True
    assert tools.t_write("app.py", "x = 2\n").startswith("Refused: her request names no symptom")
    assert (repo / "app.py").read_text() == "x = 1\n"
    # a command can still write: the end of the round puts it all back
    (repo / "app.py").write_text("x = 3\n")
    (repo / "_probe.py").write_text("print(1)\n")
    assert ses.changed()
    assert ses.undo_round()
    assert not ses.changed()
    assert (repo / "app.py").read_text() == "x = 1\n" and not (repo / "_probe.py").exists()


def test_the_closing_words_always_hold_one_question():
    from app.devsahayak import engine as EN
    from app.quality import codecard as C
    task = {"id": "vague_ask", "kind": "fix", "repo": "dukaan", "ask": True, "request": "x", "files": {},
            "allow": r"^$", "check": "", "solution": {}}
    for said in ("", "I looked at checkout and it seems fine.", "Is it the total? Or the step? Or the button? Or the page?",
                 "The step / time limit for this round was reached; what was done so far is below for review."):
        e = EN.unclear_finish(said)
        assert e.endswith("?") and e.count("?") <= 3, e
        assert C.score(task, {}, {"explain": e})["works"]
    assert EN.unclear_finish("Which step fails - payment or the address?") == "Which step fails - payment or the address?"


def test_wired_into_the_round():
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "tools.ask_only = True" in src and '"dev_unclear_steps"' in src
    assert "ses.undo_round()" in src and "unclear_finish(" in src
    assert "if self.ask_only:" in src


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.38"' in main
    assert "version: 0.999.38+1036" in (ROOT / "pubspec.yaml").read_text()
