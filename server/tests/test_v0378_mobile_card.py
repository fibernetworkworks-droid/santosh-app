"""v0.378 MOBILE CARD (owner: "GO 4"): set 3 of the coding card in the languages Hoola's own app is written in - 5 Dart jobs on
a Flutter app's logic layer (KHATA) and 5 Kotlin jobs on an Android app's domain layer (DUKAAN-KT), checked with the real Dart
SDK and kotlinc (quality/sdk.py). The toolchain-heavy tests run only where the SDKs are installed (CODECARD_SDK or PATH);
everywhere else they are skipped, exactly like the card skips a job whose toolchain is missing."""
import pytest

from app.quality import code_tasks3 as C3
from app.quality import codecard as K
from app.quality import sdk
from tests.test_v0350_kadam_ba_kadam import Script, tu


def _task(tid):
    return next(t for t in C3.TASKS if t["id"] == tid)


def test_the_mobile_set_is_fixed():
    assert C3.SET == 3 and len(C3.TASKS) == 10 and len({t["id"] for t in C3.TASKS}) == 10
    assert sum(t["lang"] == "dart" for t in C3.TASKS) == 5 and sum(t["lang"] == "kotlin" for t in C3.TASKS) == 5
    assert "AGENTS.md" in C3.KHATA and "AGENTS.md" in C3.DUKAAN_KT and C3.PARALLEL == 2
    assert all(not p.startswith("package:") for p in C3.KHATA)          # no pub.dev needed: plain Dart + its own harness


@pytest.mark.parametrize("task", C3.TASKS, ids=[t["id"] for t in C3.TASKS])
def test_every_reference_answer_is_right_and_the_untouched_repo_is_not(task):
    if not sdk.have(task["lang"]):
        pytest.skip(f"{task['lang']} toolchain not installed")
    row = K.score(task, task["solution"], {})
    assert row["right"], row["why"]
    assert not K.score(task, {}, {})["works"]
    if task.get("must_test") and task["kind"] == "fix":
        assert row["proves"]


def test_the_marks_catch_kotlin_shortcuts():
    if not sdk.have("kotlin"):
        pytest.skip("kotlin toolchain not installed")
    n = _task("kt_fix_null_crash")
    bang = n["solution"]["src/Customers.kt"].replace('find(id)?.name ?: "Guest"', '(customers[id] ?: Customer(id, "Guest"))!!.name')
    row = K.score(n, {"src/Customers.kt": bang, "test/CustomersTest.kt": n["solution"]["test/CustomersTest.kt"]})
    assert row["works"] and not row["rules"] and not row["right"]          # works, but !! breaks the project rule
    r = _task("kt_rename_deprecated")
    noalias = {"src/Money.kt": C3.K_MONEY.replace("fun formatPaise(", "fun formatRupees("),
               "src/Receipt.kt": C3.K_RECEIPT.replace("formatPaise", "formatRupees")}
    assert not K.score(r, noalias)["right"]


def test_unsafe_mobile_code_is_never_run(monkeypatch):
    ran = []
    monkeypatch.setattr(K, "_seq", lambda *a, **k: ran.append(1) or (0, ""))
    monkeypatch.setattr(K, "tool_ok", lambda lang: True)
    d = _task("dart_write_inr")
    row = K.score(d, {"lib/format.dart": C3.D_FORMAT + "import 'dart:io';\nvoid x() { Process.run('id', []); }\n"})
    assert row["unsafe"] == ["lib/format.dart"] and not ran
    k = _task("kt_feature_cod")
    row = K.score(k, {"src/Orders.kt": C3.K_ORDERS + "\nfun x() = ProcessBuilder(\"id\").start()\n"})
    assert row["unsafe"] == ["src/Orders.kt"] and not ran


def test_without_a_toolchain_the_jobs_are_skipped_not_failed(monkeypatch):
    monkeypatch.setattr(sdk, "dart", lambda: "")
    monkeypatch.setattr(sdk, "kotlinc", lambda: "")
    for tid in ("dart_fix_json_crash", "kt_fix_rounding"):
        row = K.score(_task(tid), {}, {})
        assert row["skipped"] and row["right"] is None and "not installed" in row["why"][0]


def test_kotlin_main_class_names():
    assert K._kt_main("test/OutboxTest.kt", "package hoola.test\n\nfun main() {}") == "hoola.test.OutboxTestKt"
    assert K._kt_main("HoolaCheck.kt", "package hoola.check\n") == "hoola.check.HoolaCheckKt"
    assert K._kt_main("test/pctTest.kt", "fun main() {}") == "PctTestKt"


def test_a_mobile_job_runs_through_the_real_loop(monkeypatch):
    if not sdk.have("dart"):
        pytest.skip("dart toolchain not installed")
    from app.devsahayak import loop as L
    t = _task("dart_fix_duplicate_order")
    script = Script([
        [tu(1, "read_file", path="lib/sync.dart"), tu(2, "read_file", path="test/harness.dart")],
        [tu(3, "edit_file", path="lib/sync.dart", old=C3.D_SYNC_BUG, new=C3.D_SYNC),
         tu(4, "new_file", path="test/sync_test.dart", content=t["solution"]["test/sync_test.dart"])],
        [tu(5, "done", explain="cid dedupe nahi tha", pr_title="Dedupe outbox by cid")],
    ])
    monkeypatch.setattr(L, "BRAIN", script)
    cd = K.card(only=["dart_fix_duplicate_order"], parallel=1, set_=3)
    assert cd["set"] == 3 and cd["right"] == 1 and cd["rows"][0]["proves"], cd["rows"][0]
    assert '<project_rules path="AGENTS.md">' in script.seen[0] and "Dart 3" in script.seen[0]


def test_cli_sdk_and_vps_job(monkeypatch, capsys, tmp_path):
    from pathlib import Path

    from app.quality import __main__ as M
    monkeypatch.setenv("CODECARD_SDK", str(tmp_path / "none"))
    monkeypatch.setattr(sdk.shutil, "which", lambda name: None)
    assert M.main(["sdk"]) == 0
    out = capsys.readouterr().out
    assert "dart:    missing" in out and "Dart jobs: will be SKIPPED" in out
    yml = (Path(__file__).resolve().parents[2] / ".github/workflows/vps-ops.yml").read_text()
    assert "- code_card_mobile" in yml and "app.quality sdk --setup" in yml and "code --set 3 --label vps-ops" in yml
    assert "timeout-minutes: 25" in yml
