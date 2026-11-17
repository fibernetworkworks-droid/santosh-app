"""v0.951 HOOLA CODE NO SCRATCH (owner: "Check" on the hard card after v0.949 = 11/12): the empty answers were rescued,
but on the vague ask Qwen then wrote a probe.py to look around and left it in the change. Scratch files are caught at
done (one chance to delete them), the engine's rules say so, and the answer-now line says: unclear = ask, no edits."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_scratch_files_are_found_and_real_tests_are_not():
    from app.devsahayak import engine as EN
    rows = [{"st": "A", "path": "probe.py"}, {"st": "A", "path": "tools/scratch_cart.js"},
            {"st": "A", "path": "debug_total.py"}, {"st": "A", "path": "tests/test_probe_checkout.py"},
            {"st": "M", "path": "probe.py"}, {"st": "A", "path": "app/checkout.py"}, {"st": "A", "path": "temp.txt"}]
    assert EN.scratch_files(rows) == ["probe.py", "tools/scratch_cart.js", "debug_total.py", "temp.txt"]
    txt = EN.scratch_text(["probe.py"])
    assert "probe.py" in txt and "Delete them" in txt and "ONE short question" in txt


def test_done_gets_one_scratch_look_before_finishing():
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert 'if not reality.get("scratch"):' in eng and 'reality["scratch"] = True' in eng
    assert eng.index('left = scratch_files(ses.changed())') < eng.index('note = reality_check(tools, ses, t, follow_up, inp')
    assert "never ships." in eng


def test_answer_now_says_unclear_means_ask():
    from app.devsahayak import brain as B
    assert "do not explore or edit anything" in B.ANSWER_NOW and "ONE short question" in B.ANSWER_NOW


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.988.0"' in main
    assert "version: 0.988.0+987" in (ROOT / "pubspec.yaml").read_text()
