"""v0.946 HOOLA CODE ON ITS OWN (owner: "ALSO CHECK DOES HOOLA CODE CAN DO ENTIER AUTONOMOUS CODING OWN ITS OWN OR NOT"
-> "GO").

A round that stops early goes on by itself, unfinished work never goes out alone, model failures are said plainly, a
broken CI round does not use one up, a new commit on her PR is watched by CI, her limit counts her rounds, deleted files
reach the PR, a new package is installed, a waiting plan is said again, and a session never spends past its limit."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _res(finished, budget=False):
    return ("sha", [], {"found": {"loop": {"finished": finished, "budget": budget}}}, {"files": []})


def test_an_unfinished_round_goes_on_by_itself_then_says_why(monkeypatch):
    from app.devsahayak import service as S
    calls = []

    def call(fu, first):
        calls.append((fu, first))
        return _res(len(calls) >= 3)
    monkeypatch.setattr(S, "_Step", lambda tid: type("X", (), {"event": lambda self, e: None})())
    monkeypatch.setattr(S, "_over_budget", lambda tid: False)
    res, done, why = S._until_done("t1", call, "her words")
    assert done and why == "" and len(calls) == 3
    assert calls[0] == ("her words", True) and calls[1][0] == S.CONTINUE_WORDS and calls[1][1] is False
    calls.clear()
    res, done, why = S._until_done("t1", lambda fu, first: (calls.append(1), _res(False))[1], "")
    assert not done and "did not finish in 4 rounds" in why and len(calls) == 4       # 1 + dev_auto_continue (3)


def test_the_spending_limit_ends_it_and_says_so(monkeypatch):
    from app.devsahayak import service as S
    monkeypatch.setattr(S, "_Step", lambda tid: type("X", (), {"event": lambda self, e: None})())
    res, done, why = S._until_done("t1", lambda fu, first: _res(False, budget=True), "")
    assert not done and "spending limit" in why
    monkeypatch.setattr(S, "_spent_inr", lambda tid: 2000.0)
    assert S._over_budget("t1") is True
    monkeypatch.setattr(S, "_spent_inr", lambda tid: 10.0)
    assert S._over_budget("t1") is False
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "if over and over():" in eng and "budget_hit = True" in eng and '"budget": budget_hit' in eng


def test_a_change_that_ends_in_words_is_not_finished():
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert 'finish = {"explain": said, "words_only": not explain_ask}' in eng
    assert 'finish.get("words_only") and not str(finish.get("explain") or "").rstrip().endswith("?")' in eng
    assert "finished = not ses.changed()" in eng


def test_unfinished_work_never_goes_out_alone():
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert "if unfinished or public or ask_pr" in svc and "Hoola is not finished - {unfinished}" in svc
    assert "if unfinished and on_branch:" in svc and "the working copy keeps the work" in svc


def test_model_failures_are_said_plainly():
    from app.devsahayak import brain as B
    from app.devsahayak import service as S
    w = S._why_broke(B.QwenError("OpenRouter answered 402: no credit"))
    assert "out of credit" in w and "openrouter.ai" in w and "working copy is kept" in w
    assert "busy" in S._why_broke(B.QwenError("OpenRouter answered 429: slow down"))
    assert "ValueError" in S._why_broke(ValueError("x"))


def test_a_broken_ci_round_does_not_use_one_up(env):
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    init_db()
    with S.session() as s:
        t = DevTask(tenant_id="ten", repo="a/b", text="x", status="ci_running", changes="[]", ci_round=2)
        s.add(t)
        s.flush()
        tid = t.id
    S._ci_round_back(tid)
    with S.session() as s:
        assert s.get(DevTask, tid).ci_round == 1


def test_her_limit_counts_her_rounds_and_ci_watches_new_commits():
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert "hers_round: bool = True" in svc and "if hers_round:" in svc
    assert '"unless the test is wrong: then say why in risk).", "", hers_round=False)' in svc
    assert 'row.status, row.ci_since, row.ci_round = "ci_running", now(), 0' in svc
    assert 'if g.pr(t.repo, t.pr_number).get("draft", True):' in svc


def test_a_deleted_file_reaches_the_pr(monkeypatch):
    from app.devsahayak import gh as G
    from app.devsahayak import service as S
    sent = []

    class Fake(G.Gh):
        def __init__(self):
            pass

        def req(self, method, path, body=None, **k):
            sent.append((method, path, body))
            if path.endswith("/git/blobs"):
                return {"sha": "blob1"}
            if "/git/commits/" in path:
                return {"tree": {"sha": "base"}}
            if path.endswith("/git/trees"):
                return {"sha": "tree1"}
            if path.endswith("/git/commits"):
                return {"sha": "c1"}
            return {}

        def branch_sha(self, full, branch):
            return "x"
    Fake().commit_files("a/b", "hoola/d-1", "p", [("keep.py", "x"), ("old.py", None)], "m")
    tree = next(b for m, p, b in sent if p.endswith("/git/trees"))["tree"]
    assert {"path": "old.py", "mode": "100644", "type": "blob", "sha": None} in tree
    assert sum(1 for m, p, b in sent if p.endswith("/git/blobs")) == 1          # no blob for a deletion
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert svc.count('(c["path"], None if c.get("delete") else c["new"])') == 5 and '"delete": True, "added": 0' in svc
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert 'files.append({"path": p, "why": "deleted", "delete": True})' in eng


def test_a_deletion_is_prepared_like_a_change(env):
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    init_db()
    t = DevTask(tenant_id="ten", repo="a/b", text="x", kind="write")

    class G:
        def file(self, repo, path, ref):
            return ("line1\nline2\n", "sha-old") if path == "old.py" else ("", "")
    out = S._prepare("ten", t, {"files": [{"path": "old.py", "delete": True}, {"path": "gone.py", "delete": True}]}, [], G(), "main")
    assert out["problems"] == [] and len(out["changes"]) == 1
    c = out["changes"][0]
    assert c["delete"] and c["removed"] == 2 and c["new"] == "" and "-line1" in c["diff"]
    merged = S._merge_files(out["changes"], [])
    assert merged == [{"path": "old.py", "why": "deleted", "delete": True}]


def test_a_new_package_is_installed_again(tmp_path, monkeypatch):
    from app.devsahayak import engine as EN
    monkeypatch.setattr(EN, "folder", lambda tid: tmp_path / tid)
    ses = EN.Session("t1")
    ses.repo.mkdir(parents=True)
    (ses.repo / "requirements.txt").write_text("flask\n")
    tools = EN.Tools(ses, False, {"setup": "pip install -r requirements.txt", "deps_key": "old"})
    tools.image = "hoola-snap:old"
    tools.read.add("requirements.txt")
    out = tools.t_edit("requirements.txt", "flask\n", "flask\nrequests\n")
    assert "installs it again" in out and tools.image == "" and tools.spec["deps_key"] != "old"
    tools.read.add("app.py")
    (ses.repo / "app.py").write_text("x = 1\n")
    tools.image = "img"
    assert "installs" not in tools.t_edit("app.py", "x = 1", "x = 2") and tools.image == "img"


def test_a_waiting_plan_is_said_again_once(env, monkeypatch):
    from datetime import timedelta
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    init_db()
    told = []
    monkeypatch.setattr(S, "_card", lambda tenant, t, say: told.append(say))
    with S.session() as s:
        t = DevTask(tenant_id="ten", number="D-1", repo="a/b", text="add dark mode", status="plan_wait", plan="{}", changes="[]")
        s.add(t)
        s.flush()
    later = S.now() + timedelta(hours=3)
    S._plan_reminders(later)
    S._plan_reminders(later + timedelta(hours=5))
    assert len(told) == 1 and "still waiting for your yes" in told[0]


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.981.0"' in main
    assert "version: 0.981.0+980" in (ROOT / "pubspec.yaml").read_text()
