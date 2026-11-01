"""v0.365 HARD CARD (owner: "GO HARD CARD"): set 2 of the coding card - two bigger projects (Python shop 30 files, JavaScript
billing 13 files), multi-file features, a rename with every caller, bugs far from the symptom, an access-control hole, a
refactor that keeps behaviour, a setting hard-coded in three places, a folder rules file, JavaScript, and a vague ask that
needs ONE question. Offline: reference answers prove every check; the marks catch the usual mistakes."""
import shutil

import pytest

from app.quality import code_repos as R
from app.quality import code_tasks2 as C2
from app.quality import codecard as K
from tests.test_v0350_kadam_ba_kadam import Script, tu

HAS_NODE = bool(shutil.which("node"))


def _task(tid):
    return next(t for t in C2.TASKS if t["id"] == tid)


def test_the_hard_set_is_bigger_and_fixed():
    assert C2.SET == 2 and len(C2.TASKS) == 12 and len({t["id"] for t in C2.TASKS}) == 12
    assert len(R.DUKAAN) >= 25 and len(R.HISAAB) >= 10
    assert sum(1 for t in C2.TASKS if t.get("lang") == "js") == 2 and any(t.get("ask") for t in C2.TASKS)
    assert "app/api/AGENTS.md" in R.DUKAAN and C2.STEPS >= 40


def test_the_base_projects_are_correct_and_their_own_tests_pass():
    rc, log = K._pytest(R.DUKAAN, ["tests"])
    assert rc == 0, log
    if HAS_NODE:
        rc, log = K._py(R.HISAAB, ["--test"], exe=K.node())
        assert rc == 0, log


@pytest.mark.parametrize("task", C2.TASKS, ids=[t["id"] for t in C2.TASKS])
def test_every_reference_answer_is_right_and_the_untouched_repo_is_not(task):
    if task.get("lang") == "js" and not HAS_NODE:
        pytest.skip("node not installed")
    out = {"explain": "Checkout mein kya gadbad dikh rahi hai - koi error message ya kis step par atakta hai?"} \
        if task.get("ask") else {}
    row = K.score(task, task["solution"], out)
    assert row["right"], row["why"]
    if task["check"]:
        assert not K.score(task, {}, {})["works"]
    if task.get("must_test") and task["kind"] == "fix":
        assert row["proves"]


def test_the_hard_marks_catch_the_usual_mistakes():
    v = _task("vague_ask")
    assert not K.score(v, {"app/orders.py": R.ORDERS + "\n# fixed\n"}, {"explain": "Theek kar diya."})["right"]
    assert not K.score(v, {}, {"explain": "Maine sab dekha, sab theek hai."})["right"]   # no question asked
    rn = _task("rename_with_alias")
    no_alias = {"app/discounts.py": R.DISCOUNTS.replace("def apply_coupon(", "def redeem_coupon("),
                "app/orders.py": R.ORDERS.replace("apply_coupon", "redeem_coupon"),
                "app/api/handlers.py": R.HANDLERS.replace("apply_coupon", "redeem_coupon")}
    assert "apply_coupon" in " ".join(K.score(rn, no_alias)["why"])                           # the alias is missing
    half = {**rn["solution"], "app/api/handlers.py": R.HANDLERS}                             # a caller missed
    assert not K.score(rn, half)["right"]
    s = _task("setting_everywhere")
    only_config = {"app/config.py": s["solution"]["app/config.py"]}
    assert "quote still says 499" in " ".join(K.score(s, only_config)["why"])
    leak = _task("fix_from_test_run")
    weakened = {"tests/test_orders.py": R.TEST_ORDERS}                                       # deleting the red test
    row = K.score(leak, weakened)
    assert not row["scope"] and not row["works"]
    ref = _task("refactor_same_behaviour")
    assert "still" in " ".join(K.score(ref, {})["why"])                                       # the long version fails


@pytest.mark.skipif(not HAS_NODE, reason="node not installed")
def test_unsafe_javascript_is_never_run(monkeypatch):
    t = _task("js_write_inr")
    ran = []
    monkeypatch.setattr(K, "_py", lambda *a, **k: ran.append(1) or (0, ""))
    bad = {"src/format.js": R.JS_FORMAT + '\nimport { execSync } from "child_process";\nexport const formatINR = () => execSync("id");\n'}
    row = K.score(t, bad)
    assert row["unsafe"] == ["src/format.js"] and not row["right"] and not ran


def test_without_node_the_javascript_jobs_are_skipped_not_failed(monkeypatch):
    monkeypatch.setattr(K, "node", lambda: "")
    row = K.score(_task("js_fix_gst_split"), {"src/gst.js": "x"})
    assert row["skipped"] and row["right"] is None


def test_a_hard_job_runs_through_the_real_loop(monkeypatch):
    from app.devsahayak import loop as L
    t = _task("fix_shared_default")
    sol = t["solution"]
    script = Script([
        [tu(1, "search_code", words="Cart"), tu(2, "read_file", path="app/cart.py"), tu(3, "read_file", path="tests/test_cart.py")],
        [tu(4, "edit_file", path="app/cart.py", old=C2.CART_SHARED, new=sol["app/cart.py"]),
         tu(5, "edit_file", path="tests/test_cart.py", old=R.TEST_CART, new=sol["tests/test_cart.py"])],
        [tu(6, "done", explain="items=[] default shared tha", pr_title="Fix shared cart")],
    ])
    monkeypatch.setattr(L, "BRAIN", script)
    cd = K.card(only=["fix_shared_default"], parallel=1, set_=2)
    assert cd["set"] == 2 and cd["right"] == 1 and cd["rows"][0]["proves"], cd["rows"][0]
    assert "app/api/AGENTS.md" in script.seen[0]                                # the folder rules were listed up front
    monkeypatch.setattr(L, "BRAIN", Script([[tu(1, "done", explain="Checkout ka kaunsa hissa - payment ya stock?")]]))
    assert K.card(only=["vague_ask"], parallel=1, set_=2)["right"] == 1


def test_cli_set_2_and_vps_job(monkeypatch, capsys, tmp_path):
    from pathlib import Path

    from app.quality import __main__ as M
    from app.quality import toolchoice
    monkeypatch.setattr(toolchoice, "_dir", lambda: tmp_path)
    seen = {}

    def fake(only=None, limit=0, set_=1):
        seen["set"] = set_
        return {"kind": "code", "set": set_, "model": "m", "jobs": 1, "skipped": 0, "right": 1, "works": 1, "scope": 1,
                "rules": 1, "tests": 1, "tests_of": 1, "proves": 1, "proves_of": 1, "steps_avg": 3, "minutes": 0.1,
                "rows": [{"id": "x", "kind": "fix", "right": True, "steps": 3, "seconds": 5}]}
    monkeypatch.setattr(K, "card", fake)
    assert M.main(["code", "--set", "2"]) == 0
    assert seen["set"] == 2 and "set v2" in capsys.readouterr().out and list(tmp_path.glob("code2-*.json"))
    yml = (Path(__file__).resolve().parents[2] / ".github/workflows/vps-ops.yml").read_text()
    assert "- code_card_hard" in yml and "python -m app.quality code --set 2 --label vps-ops" in yml
