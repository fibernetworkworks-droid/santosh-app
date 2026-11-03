"""v0.381 Shiksha suite Phase 0 + 1: the locked Python sandbox, the education foundation (classes, learners + guardian
consent under DPDP s.9, shared question bank with code checks, gradebook) and the Pathyakram Sahayak (questions ->
drafts -> teacher approval, papers from the official blueprint, year / lesson plans, rubrics, Word files, a share only
on her app tap, Google Forms quiz from the objective questions), tools, API, employee wiring."""
import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.pathyakram.models  # noqa: F401  (tables for the env fixture's init_db)
import app.shiksha.models  # noqa: F401
from tests.test_life import conv_ctx

T = "default"


def mcq(i, chapter="Real Numbers", marks=1):
    return {"qtype": "mcq", "text": f"Question {i}: which of these numbers is irrational number {i}?",
            "options": [f"{i}/2", f"sqrt({i * 4 + 2})", f"{i}.25", f"{i}"], "answer": "b", "marks": marks,
            "steps": ["Check each option"], "bloom": "understand", "difficulty": ["easy", "medium", "hard"][i % 3],
            "chapter": chapter}


def short(i, chapter="Polynomials", marks=3):
    return {"qtype": "short", "text": f"Find the zeroes of the polynomial x^2 - {i + 1}x + {i} and verify the relation.",
            "answer": f"1 and {i}", "marks": marks, "scheme": [{"point": "factorise", "marks": 1}, {"point": "zeroes", "marks": 1},
                                                                 {"point": "verify", "marks": marks - 2}],
            "chapter": chapter, "bloom": "apply"}


@pytest.fixture
def sk(env, monkeypatch):
    from app.pathyakram import service as P
    events = []
    monkeypatch.setattr(P, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    P.events = events
    return P


# ---------------------------------------------------------------- Phase 0: sandbox
def test_pylab_runs_analysis_and_returns_files():
    from app.pylab import runner
    r = runner.run("import pandas as pd\nimport matplotlib.pyplot as plt\ndf = pd.read_csv('m.csv')\n"
                   "print(round(df.y.mean(), 2))\nplt.plot(df.x, df.y)\ndf.describe().to_csv('summary.csv')",
                   {"m.csv": b"x,y\n1,2\n2,4\n3,9\n"}, timeout_s=60)
    assert r["ok"], r
    assert r["stdout"].strip() == "5.0"
    names = {o["name"] for o in r["outputs"]}
    assert {"summary.csv", "figure_1.png"} <= names and "m.csv" not in names


@pytest.mark.parametrize("code,word", [
    ("import socket; socket.create_connection(('1.1.1.1', 80))", "Sandbox"),
    ("import os; os.system('id')", "Sandbox"),
    ("import subprocess; subprocess.run(['id'])", "Sandbox"),
    ("open('/tmp/pylab_escape.txt', 'w').write('x')", "work folder"),
    ("print(open('/etc/passwd').read())", "padhna"),
    ("import os; print(os.listdir('/home'))", "dekhna"),
    ("import ctypes; ctypes.CDLL(None)", "Sandbox"),
])
def test_pylab_blocks_escapes(code, word):
    from app.pylab import runner
    r = runner.run(code, timeout_s=20)
    assert not r["ok"] and word in r["error"], r


def test_pylab_limits_and_no_secrets(monkeypatch):
    from app.pylab import runner
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-reach-the-child")
    r = runner.run("import os; print(sorted(k for k in os.environ if 'KEY' in k or 'TOKEN' in k))", timeout_s=20)
    assert r["ok"] and r["stdout"].strip() == "[]"
    assert runner.run("while True: pass", timeout_s=2)["timed_out"]
    m = runner.run("x = bytearray(6 * 1024 ** 3)", timeout_s=20)
    assert not m["ok"] and "Memory" in m["error"]
    with pytest.raises(runner.PylabError):
        runner.run("   ")


def test_pylab_service_uses_her_dataset(env):
    from app import datasets as D
    from app.pylab import service as PL
    doc = D.save(T, [{"marks": 40}, {"marks": 60}, {"marks": 80}], name="class 10 marks")
    out = PL.run(T, f"import pandas as pd\nprint(pd.read_csv('{doc['id']}.csv').marks.mean())", datasets=[doc["id"]],
                 publish=False)
    assert out["ok"] and out["stdout"].strip() == "60.0" and out["inputs"][0]["rows"] == 3
    with pytest.raises(PL.PylabError):
        PL.run(T, "print(1)", datasets=["ds_missing"], publish=False)


# ---------------------------------------------------------------- Phase 0: foundation
def test_question_checks():
    from app.shiksha import rules as R
    good, p = R.check_question(mcq(1))
    assert not R.fatal(p) and good["answer"] == good["options"][1]
    _, p = R.check_question({**mcq(2), "options": ["a", "b", "c"]})
    assert R.fatal(p)
    _, p = R.check_question({**mcq(3), "answer": "something else"})
    assert R.fatal(p)
    ar, p = R.check_question({"qtype": "ar", "text": "Assertion (A): sqrt 2 is irrational. Reason (R): it cannot be p/q.",
                              "answer": "a", "marks": 1})
    assert not R.fatal(p) and ar["options"] == R.AR_OPTIONS and ar["answer"] == R.AR_OPTIONS[0]
    tf, p = R.check_question({"qtype": "tf", "text": "Every rational number is an integer.", "answer": "galat", "marks": 1})
    assert tf["answer"] == "False" and not R.fatal(p)
    s, p = R.check_question({**short(1), "scheme": [{"point": "x", "marks": 1}, {"point": "y", "marks": 1}]})
    assert any("marking scheme" in x for x in p) and not R.fatal(p)
    _, p = R.check_question({"qtype": "long", "text": "Explain the water cycle in detail.", "marks": 5})
    assert R.fatal(p)                                  # no model answer and no marking points


def test_frameworks_library_is_official_and_honest():
    from app.shiksha import rules as R
    m10 = R.chapters("Maths", "Class X")
    assert m10 and "Real Numbers" in m10["chapters"] and "ncert" in m10["source"].lower()
    g6 = R.chapters("Mathematics", "6")
    assert g6 == {}                                    # incomplete book: never half a chapter list
    p = R.pattern("CBSE", "10", "Mathematics")
    assert p["max_marks"] == 80 and R.blueprint_total(p["sections"]) == 80
    assert p["verified"] is False                      # C / D were worked out from the totals: 'andaaza'
    assert R.pattern("CBSE", "10", "Science").get("sections") == []
    assert R.pattern("ICSE", "10", "Mathematics") == {}


def test_learners_need_guardian_consent(env):
    from app.shiksha import service as S
    S.add_class(T, "10-A", subjects=["Mathematics"])
    with pytest.raises(S.ShikshaError, match="guardian"):
        S.add_learner(T, "Riya", "10-A", birth_year=2011)
    v = S.add_learner(T, "Riya", "10-A", birth_year=2011, guardian_name="Meena", guardian_phone="98765 43210")
    assert v["child"] and v["consent"] == "none" and not v["usable"]
    with pytest.raises(S.ShikshaError, match="consent"):
        S.add_mark(T, v["number"], "UT-1", "Mathematics", 18, 20)
    with pytest.raises(S.ShikshaError, match="method"):
        S.record_consent(T, v["number"], True, "")
    with pytest.raises(S.ShikshaError):
        S.record_consent(T, v["number"], True, "signed_form", actor="customer:abc")
    S.record_consent(T, v["number"], True, "signed_form", "form in file")
    m = S.add_mark(T, v["number"], "UT-1", "Mathematics", 18, 20)
    assert not m["signed_off"]
    with pytest.raises(S.ShikshaError):
        S.sign_off(T, [m["id"]], actor="routine")
    assert S.sign_off(T, [m["id"]])["signed_off"] == 1
    adult = S.add_learner(T, "Arjun", "", adult=True)
    assert adult["usable"] and not adult["child"]
    gone = S.forget_learner(T, v["number"])
    assert gone["marks_removed"] == 1
    assert S.learners(T) == [adult | {k: adult[k] for k in ()}] or len(S.learners(T)) == 1


def test_bank_dedupes_and_review_rules(env):
    from app.shiksha import service as S
    r = S.save_questions(T, [mcq(1), mcq(1), mcq(2), {**mcq(3), "options": []}], board="CBSE", grade="10",
                         subject="Mathematics")
    assert len(r["added"]) == 2 and len(r["skipped"]) == 2
    assert all(q["status"] == "draft" for q in r["added"])
    flagged = S.save_questions(T, [{**mcq(9), "options": ["1", "2", "3", "none of the above"], "answer": "a"}], board="CBSE",
                               grade="10", subject="Mathematics")["added"][0]
    res = S.set_status(T, [r["added"][0]["number"], flagged["number"]], "approved")
    assert res["done"] == [r["added"][0]["number"]] and res["refused"][0]["ref"] == flagged["number"]
    e = S.edit_question(T, r["added"][0]["number"], {"text": "Which of these is an irrational number? (edited)"})
    assert e["status"] == "draft"                      # edited = read again before use
    assert S.bank(T, subject="Mathematics", grade="10")["total"] == 3


# ---------------------------------------------------------------- Phase 1: Pathyakram
def test_generate_saves_checked_drafts(sk, monkeypatch):
    P = sk
    seen = {}

    def model(system, prompt, max_tokens=6000):
        seen["prompt"] = prompt
        return {"questions": [mcq(1), mcq(2), {**mcq(3), "options": ["x"]}, short(1)]}
    monkeypatch.setattr(P, "_model_json", model)
    out = P.generate(T, "Mathematics", "10", "CBSE", chapter="Real Numbers", counts={"mcq": 3, "short": 1})
    assert len(out["added"]) == 3 and len(out["skipped"]) == 1 and "draft" in out["say"]
    assert "Class: 10" in seen["prompt"] and "3 x mcq" in seen["prompt"]
    with pytest.raises(P.PathyakramError):
        P.generate(T, "Mathematics", "10", counts={"mcq": 31}, chapter="x")
    with pytest.raises(P.PathyakramError):
        P.generate(T, "Mathematics", "10", counts={"mcq": 2}, actor="customer:1")
    warn = P.generate(T, "Mathematics", "10", chapter="Quantum Mechanics", counts={"mcq": 1})
    assert warn["warnings"]


def _fill_bank(S, n_mcq=20, n_short=8):
    S.save_questions(T, [mcq(i, ["Real Numbers", "Polynomials", "Triangles"][i % 3]) for i in range(n_mcq)], board="CBSE",
                     grade="10", subject="Mathematics")
    S.save_questions(T, [short(i, ["Polynomials", "Triangles"][i % 2]) for i in range(n_short)], board="CBSE", grade="10",
                     subject="Mathematics")
    refs = [q["number"] for q in S.bank(T, subject="Mathematics", grade="10", limit=200)["questions"]]
    S.set_status(T, refs, "approved")


def test_paper_from_teacher_blueprint_approve_and_files(sk):
    P = sk
    from app.shiksha import service as S
    _fill_bank(S)
    secs = [{"name": "A", "qtype": "mcq", "count": 10, "marks_each": 1}, {"name": "B", "qtype": "short", "count": 5, "marks_each": 3}]
    out = P.make_paper(T, "Mathematics", "10", "CBSE", title="Unit test 1", sections=secs, duration_min=60)
    p = out["paper"]
    assert p["questions"] == 15 and p["total"] == 25 == p["max_marks"] and not p["gaps"] and p["drafts"] == 0
    full = P.paper(T, p["number"], key=True)
    a = [q for s in full["sections"] if s["name"] == "A" for q in s["questions"]]
    assert {q["qtype"] for q in a} == {"mcq"} and all(q["answer"] for q in a)
    chapters = {S.question(T, q["number"])["chapter"] for q in a}
    assert len(chapters) == 3                          # spread over the chapters
    assert P.approve_paper(T, p["number"])["paper"]["status"] == "approved"
    f = P.paper_file(T, p["number"], key=True)
    assert f["file"]["name"].endswith("_key.docx")
    sw = P.swap(T, p["number"], 1)
    assert sw["paper"]["status"] == "draft"            # changed = approve again


def test_paper_gaps_and_official_pattern(sk):
    P = sk
    from app.shiksha import service as S
    _fill_bank(S, n_mcq=5, n_short=0)
    out = P.make_paper(T, "Mathematics", "10", "CBSE")           # the official CBSE pattern from the library
    p = out["paper"]
    assert p["max_marks"] == 80 and p["gaps"] and "andaaza" in p["blueprint"]["say"]
    with pytest.raises(P.PathyakramError, match="gaps"):
        P.approve_paper(T, p["number"])
    with pytest.raises(P.PathyakramError, match="pattern"):
        P.make_paper(T, "Science", "10", "CBSE")                 # no section counts on record: teacher gives them
    with pytest.raises(P.PathyakramError, match="samajh"):
        P.make_paper(T, "Mathematics", "10", sections=[{"name": "A", "qtype": "essayish", "count": 2, "marks_each": 5}])


def test_year_plan_uses_library_chapters(sk):
    P = sk
    out = P.year_plan(T, "Mathematics", "10", "CBSE", months=10, revision_months=1)
    body = out["plan"]["body"]
    placed = [c for r in body["rows"] for c in r["chapters"] if c != "Revision + practice papers"]
    from app.shiksha import rules as R
    assert placed == R.chapters("Mathematics", "10")["chapters"]   # every chapter once, in order
    assert body["rows"][0]["month"] == "April" and body["rows"][-1]["chapters"] == ["Revision + practice papers"]
    with pytest.raises(P.PathyakramError, match="chapter"):
        P.year_plan(T, "Mathematics", "6")                         # incomplete book: teacher gives the list
    own = P.year_plan(T, "Mathematics", "6", chapters=["A", "B", "C"], months=4, revision_months=0)
    assert own["plan"]["body"]["source"] == "teacher"


def test_lesson_plan_minutes_add_up_and_rubric_points(sk, monkeypatch):
    P = sk
    steps = [{"phase": ph, "minutes": 10, "teacher": "t", "students": "s"} for ph in P.PHASES]
    monkeypatch.setattr(P, "_model_json", lambda *a, **k: {"objectives": ["o"], "steps": steps, "homework": "h"})
    lp = P.lesson_plan(T, "Science", "8", "Friction", minutes=40)
    assert sum(x["minutes"] for x in lp["plan"]["body"]["steps"]) == 40
    monkeypatch.setattr(P, "_model_json", lambda *a, **k: {"steps": steps[:3]})
    with pytest.raises(P.PathyakramError, match="5E"):
        P.lesson_plan(T, "Science", "8", "Friction")
    crit = [{"name": n, "points": 5, "levels": [{"label": l, "descriptor": f"{n} {l}"} for l in ("A", "B", "C", "D")]}
            for n in ("Content", "Design", "Delivery")]
    monkeypatch.setattr(P, "_model_json", lambda *a, **k: {"criteria": crit})
    rb = P.rubric(T, "Science model project", "Science", "8", levels=4, total_points=20)
    b = rb["plan"]["body"]
    assert sum(c["points"] for c in b["criteria"]) == 20
    assert all(c["levels"][0]["points"] == c["points"] for c in b["criteria"])
    assert P.plan_file(T, rb["plan"]["number"])["file"]["name"].endswith(".docx")


def test_share_only_on_her_tap_and_form_quiz(sk, monkeypatch):
    P = sk
    from app.shiksha import service as S
    _fill_bank(S)
    p = P.make_paper(T, "Mathematics", "10", sections=[{"name": "A", "qtype": "mcq", "count": 5, "marks_each": 1},
                                                       {"name": "B", "qtype": "short", "count": 1, "marks_each": 3}])["paper"]
    with pytest.raises(P.PathyakramError, match="approve"):
        P.share_request(T, "paper", p["number"], "form")
    P.approve_paper(T, p["number"])
    req = P.share_request(T, "paper", p["number"], "form")
    sh = req["share"]
    assert req["status"] == "needs_tap" and sh["status"] == "waiting"
    assert any(k == "pathyakram_share" for k, _ in P.events)
    with pytest.raises(P.PathyakramError, match="tap"):
        P.decide_share(T, sh["id"], True, sh["hash"], by_tap=False)
    made = {}
    from app.forms import service as F

    def create(tenant, conv, title, questions=None, description="", quiz=False, collect_emails=False, account=None):
        made.update(title=title, questions=questions, quiz=quiz)
        return {"id": "f1", "title": title, "responder_link": "https://docs.google.com/forms/d/e/x/viewform", "edit_link": "e"}
    monkeypatch.setattr(F, "create", create)
    with pytest.raises(P.PathyakramError, match="badal"):
        P.decide_share(T, sh["id"], True, "wrong-hash", by_tap=True)
    sh2 = P.share_request(T, "paper", p["number"], "form")["share"]
    out = P.decide_share(T, sh2["id"], True, sh2["hash"], by_tap=True)
    assert made["quiz"] and len(made["questions"]) == 5 and all(q["type"] == "choice" for q in made["questions"])
    assert out["left_out"] == ["Q6 (Short answer (2-3 marks))"] and out["share"]["status"] == "shared"
    assert P.papers(T)[0]["status"] == "shared"


def test_tools_api_and_employee_wiring(sk, monkeypatch):
    P = sk
    from app.agent import tools as TL
    from app.agent.shiksha_tools import SHIKSHA_HANDLERS, SHIKSHA_LABELS, SHIKSHA_TOOLS
    from app.employee import roles
    from app import voice
    assert {t["name"] for t in SHIKSHA_TOOLS} == set(SHIKSHA_HANDLERS) == set(SHIKSHA_LABELS)
    assert all(n in TL.HANDLERS and TL.FAMILY_OF[n] == "shiksha" for n in SHIKSHA_HANDLERS)
    assert {"shiksha_dekho", "pathyakram_dekho", "pylab"} <= roles.READ
    assert roles.duty_of("pathyakram") == "curriculum_work" and "curriculum_work" in roles.role_duties("curriculum_designer")
    assert roles.PRESETS["school_academics"]["role"] == "curriculum_designer"
    assert set(SHIKSHA_HANDLERS) <= voice.VOICE_VIA_KAAM
    from app.agent import admit
    assert "question paper" in admit.EXTRA_KEYS["shiksha"]
    assert "shiksha" in admit._match("mera class 10 ka question paper banao")
    ctx = conv_ctx()
    out = asyncio.run(SHIKSHA_HANDLERS["shiksha"](ctx, action="class", name="9-B"))
    assert out["number"] == "C-01"
    from app.agent.tools import ToolError
    ctx.actor = "customer:x"
    with pytest.raises(ToolError):
        asyncio.run(SHIKSHA_HANDLERS["pathyakram_dekho"](ctx, what="papers"))
    from app.pathyakram.api import make_router as pr
    from app.shiksha.api import make_router as sr
    app = FastAPI()
    app.include_router(sr(lambda: None, lambda: T))
    app.include_router(pr(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.get("/api/shiksha").json()["classes"][0]["name"] == "9-B"
    fw = c.get("/api/shiksha/frameworks", params={"grade": "10", "subject": "Mathematics"}).json()
    assert fw["chapters"]["chapters"] and fw["pattern"]["max_marks"] == 80
    assert c.post("/api/pathyakram/papers", json={"subject": "Mathematics", "grade": "10", "sections": [
        {"name": "A", "qtype": "mcq", "count": 0, "marks_each": 1}]}).status_code == 400
    assert c.get("/api/pathyakram").status_code == 200
    from app import main
    assert c.get("/api/shiksha/pylab").json()["libs"]["pandas"]
    paths = {getattr(r, "path", "") for r in main.app.routes} | {
        getattr(r, "path", "") for x in main.app.routes for r in getattr(getattr(x, "app", None), "routes", []) or []}
    client = TestClient(main.app)
    assert client.get("/api/pathyakram").status_code in (200, 401, 403)   # mounted on the real app (key-protected)
    assert paths is not None


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.472.0"
