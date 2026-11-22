"""v0.948 HOOLA CODE HARD CARD FIXES (owner: "Check" on the hard coding card on her server = 10/12).

js_fix_gst_split went red on package-lock.json the box's own npm install rewrote; vague_ask died after 877 s on
"Qwen sent an empty answer" three times (it thought until its room ran out). Both fixed; the card reads deletions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_a_lock_file_the_install_rewrote_stays_out_of_the_change():
    from app.devsahayak import engine as EN
    assert EN.install_noise("package-lock.json", {"package-lock.json", "src/gst.js"})
    assert not EN.install_noise("package-lock.json", {"package-lock.json", "package.json"})   # she asked for a package
    assert EN.install_noise("web/yarn.lock", {"web/yarn.lock", "package.json"})               # its own folder's list
    assert not EN.install_noise("web/yarn.lock", {"web/yarn.lock", "web/package.json"})
    assert EN.install_noise("poetry.lock", set()) and not EN.install_noise("src/a.py", set())
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "if install_noise(p, changed_paths):" in eng and "rewritten by the package install" in eng


def test_an_empty_qwen_answer_tries_again_thinking_less(monkeypatch):
    from app.devsahayak import brain as B
    bodies = []

    def post(url, body, headers, timeout):
        bodies.append({"effort": body["reasoning"]["effort"], "max": body["max_tokens"]})
        if len(bodies) < 3:
            return {"choices": [{"finish_reason": "length", "message": {"role": "assistant", "content": ""}}]}
        return {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Which page is wrong?"}}],
                "usage": {}}
    monkeypatch.setattr(B, "QWEN_POST", post)
    monkeypatch.setattr(B, "_or_key", lambda: "k")
    monkeypatch.setattr(B.time if hasattr(B, "time") else __import__("time"), "sleep", lambda s: None)
    import time as _t
    monkeypatch.setattr(_t, "sleep", lambda s: None)
    B.PICK.effort = "high"
    try:
        blocks, stop = B._qwen_call("sys", [{"role": "user", "content": "fix it"}], [], 2000, True)
    finally:
        B.PICK.effort = ""
    assert blocks[0]["text"] == "Which page is wrong?"
    assert [b["effort"] for b in bodies] == ["high", "medium", "low"]
    assert bodies[1]["max"] == 2000 + B.ROOM["high"]         # the room is kept while the thinking shrinks


def test_the_card_reads_a_deletion():
    src = (ROOT / "server/app/quality/codecard.py").read_text()
    assert src.count('("" if f.get("delete") else f.get("content", ""))') == 2


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.117"' in main
    assert "version: 0.999.117+1112" in (ROOT / "pubspec.yaml").read_text()
