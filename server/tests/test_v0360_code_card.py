"""v0.360 CODE CARD (owner: "GO 6"): 12 fixed practice coding jobs run through Developer Sahayak's real 8-tool loop and are
marked by hidden checks - works / stayed in scope / project rules / tests that prove the fix. Offline here: the reference
answers prove every check is right, and a scripted model drives the real loop end to end."""
import pytest

from app.quality import code_tasks as C
from app.quality import codecard as K
from tests.test_v0350_kadam_ba_kadam import Script, tu


def _task(tid):
    return next(t for t in C.TASKS if t["id"] == tid)


def test_the_set_is_fixed_and_covers_every_kind():
    assert C.SET == 1 and len(C.TASKS) == 12 and len({t["id"] for t in C.TASKS}) == 12
    assert {t["kind"] for t in C.TASKS} == {"fix", "write", "tests", "docs", "explain"}
    assert all("AGENTS.md" in C.repo(t) for t in C.TASKS)                  # every repo has project rules


@pytest.mark.parametrize("task", C.TASKS, ids=[t["id"] for t in C.TASKS])
def test_every_reference_answer_is_right_and_the_untouched_repo_is_not(task):
    out = {"explain": "len(nums) 0 hai, to zero se divide hota hai"} if task["kind"] == "explain" else {}
    row = K.score(task, task["solution"], out)
    assert row["right"], row["why"]
    if task["check"]:
        assert not K.score(task, {}, {})["works"]                            # the check really tests the change


def test_the_marks_catch_the_usual_mistakes():
    t = _task("fix_root_cause_elsewhere")
    patched_caller = {"app/invoice.py": C.INVOICE.replace("to_paise(p) * q", "(to_paise(p) + 45) * q")}
    row = K.score(t, {**patched_caller, **{k: v for k, v in t["solution"].items() if k.startswith("tests/")}})
    assert not row["scope"] and not row["right"] and "changed app/invoice.py" in row["why"][0]
    row = K.score(t, {"app/money.py": t["solution"]["app/money.py"]})           # fixed but no test
    assert row["works"] and row["test"] is False and not row["right"]
    weak = {"tests/test_money.py": "from app.money import to_paise\n\n\ndef test_whole():\n    assert to_paise('7') == 700\n"}
    row = K.score(t, {"app/money.py": t["solution"]["app/money.py"], **weak})  # test passes on the old code too
    assert row["proves"] is False and not row["right"]
    s = _task("fix_sql_injection")
    escaped = {"app/users.py": C.USERS.replace("'{name}'", "'{name.replace(chr(39), chr(39) * 2)}'"),
               "tests/test_users.py": s["solution"]["tests/test_users.py"]}
    row = K.score(s, escaped)
    assert not row["rules"] and not row["right"]                              # f-string SQL is refused even if it "works"
    d = _task("tests_for_discount")
    soft = {"tests/test_discount.py": "from app.discount import apply_discount\n\n\ndef test_a():\n"
                                      "    assert apply_discount(1000, 10) == 900\n\n\ndef test_b():\n"
                                      "    assert apply_discount(0, 10) == 0\n\n\ndef test_c():\n"
                                      "    assert apply_discount(1000, 0) == 1000\n"}
    row = K.score(d, soft)
    assert not row["right"] and "do not catch the broken version" in " ".join(row["why"])
    e = _task("explain_only")
    assert not K.score(e, {"app/stats.py": "x = 1\n"}, {"explain": "len 0"})["right"]


def test_unsafe_code_is_never_run(monkeypatch):
    t = _task("write_gst")
    ran = []
    monkeypatch.setattr(K, "_py", lambda *a, **k: ran.append(1) or (0, ""))
    row = K.score(t, {"app/tax.py": C.TAX + "\nimport subprocess\nsubprocess.run(['curl', 'x'])\n"})
    assert row["unsafe"] == ["app/tax.py"] and not row["right"] and not ran


def test_the_child_has_no_secrets(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-not-leak")
    rc, log = K._py({"x.py": "import os\nprint(sorted(os.environ))\nassert 'ANTHROPIC_API_KEY' not in os.environ\n"},
                    ["x.py"])
    assert rc == 0 and "ANTHROPIC" not in log


def test_a_job_runs_through_the_real_loop_and_the_card_adds_up(monkeypatch):
    from app.devsahayak import loop as L
    t = _task("fix_empty_average")

    def brain_for(task):
        sol = task["solution"]
        return Script([
            [tu(1, "read_file", path="app/stats.py"), tu(2, "read_file", path="tests/test_stats.py")],
            [tu(3, "edit_file", path="app/stats.py", old=C.STATS, new=sol["app/stats.py"]),
             tu(4, "edit_file", path="tests/test_stats.py", old=C.STATS_TEST, new=sol["tests/test_stats.py"])],
            [tu(5, "done", explain="khaali list", pr_title="Fix average", rules_followed="tests in tests/")],
        ])
    script = brain_for(t)
    monkeypatch.setattr(L, "BRAIN", script)
    cd = K.card(only=["fix_empty_average"], parallel=1)
    row = cd["rows"][0]
    assert row["right"] and row["proves"] and row["steps"] == 3 and row["finished"] and row["rules_read"] == ["AGENTS.md"]
    assert cd["right"] == 1 and cd["jobs"] == 1 and cd["proves_of"] == 1
    assert '<project_rules path="AGENTS.md">' in script.seen[0]                # the job saw the project's rules first
    text = "\n".join(K.lines(cd))
    assert "1/1 jobs fully right (100%)" in text and "OK   fix_empty_average" in text

    monkeypatch.setattr(L, "BRAIN", Script([[tu(1, "done", explain="kuch nahi kiya")]]))
    cd = K.card(only=["fix_page_offset"], parallel=1)
    assert cd["right"] == 0 and "MISS fix_page_offset" in "\n".join(K.lines(cd))


def test_cli_and_vps_job(monkeypatch, capsys, tmp_path):
    from pathlib import Path

    from app.quality import __main__ as M
    from app.quality import toolchoice
    monkeypatch.setattr(toolchoice, "_dir", lambda: tmp_path)
    monkeypatch.setattr(K, "card", lambda only=None, limit=0, set_=1: {
        "kind": "code", "set": 1, "model": "m", "jobs": 1, "right": 1, "works": 1, "scope": 1, "rules": 1, "tests": 1,
        "tests_of": 1, "proves": 1, "proves_of": 1, "steps_avg": 3, "minutes": 0.1,
        "rows": [{"id": (only or ["x"])[0], "kind": "fix", "right": True, "steps": 3, "seconds": 5}]})
    assert M.main(["code", "--only", "fix_page_offset"]) == 0
    out = capsys.readouterr().out
    assert "OK   fix_page_offset" in out and list(tmp_path.glob("code-*.json"))
    yml = (Path(__file__).resolve().parents[2] / ".github/workflows/vps-ops.yml").read_text()
    assert "- code_card" in yml and "python -m app.quality code --label vps-ops" in yml
