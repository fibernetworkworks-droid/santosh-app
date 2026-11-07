"""Shiksha Phase 3 - Daftar Sahayak (school office): attendance (everyone present except those named, re-marking
replaces, no consent = not recorded, monthly %), absence alerts only by her tap (one draft per guardian), grading into
the gradebook as UNSIGNED rows (answer key or a Pathyakram paper; rows or a CSV; OMR photo read for the teacher to
confirm; Google Forms quiz; Python code against tests in the sandbox; rubric suggestion capped per criterion), report
cards from signed-off marks only, a clash-free timetable, tools / API / wiring."""
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.daftar.models  # noqa: F401
import app.shiksha.models  # noqa: F401
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def office(env, monkeypatch):
    from app.daftar import service as D
    from app.shiksha import service as S
    events = []
    monkeypatch.setattr(D, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    D.events = events
    S.save_settings(T, institution="Sunrise Public School")
    S.add_class(T, "10-A", subjects=["Mathematics"])
    kids = []
    for i, (name, phone) in enumerate([("Riya", "9876500001"), ("Kabir", "9876500002"), ("Zoya", "9876500003")], 1):
        v = S.add_learner(T, name, "10-A", roll=str(i), birth_year=2011, guardian_name=f"{name}'s mother", guardian_phone=phone)
        kids.append(v["number"])
    for k in kids[:2]:
        S.record_consent(T, k, True, "school_record")        # Zoya: no consent yet
    return D, S, kids


def test_attendance_and_monthly_pct(office):
    D, S, kids = office
    r = D.mark_attendance(T, "10-A", absent=["Riya"], late=["2"])
    assert r["counts"] == {"present": 0, "absent": 1, "late": 1, "leave": 0} and r["no_consent"] == [kids[2]]
    again = D.mark_attendance(T, "10-A", absent=["9"])
    assert again["counts"]["present"] == 2 and again["unknown"] == ["9"]       # replaced, unknown roll said
    m = D.attendance(T, "10-A")
    riya = next(x for x in m["learners"] if x["name"] == "Riya")
    assert riya["pct"] == 100.0 and m["school_days"] == 1
    with pytest.raises(D.DaftarError, match="Aage"):
        D.mark_attendance(T, "10-A", day="2099-01-01")


def test_absent_alerts_only_by_her_tap(office):
    D, S, kids = office
    D.mark_attendance(T, "10-A", absent=["1"])
    req = D.absent_alerts(T, "10-A")
    sh = req["share"]
    assert req["status"] == "needs_tap" and sh["payload"]["people"][0]["phone"] == "9876500001"
    with pytest.raises(D.DaftarError, match="tap"):
        D.decide_share(T, sh["id"], True, sh["hash"], by_tap=False)
    out = D.decide_share(T, sh["id"], True, sh["hash"], by_tap=True)
    assert out["drafts"][0]["link"].startswith("https://wa.me/919876500001") and "Riya" in out["drafts"][0]["link"].replace("%20", " ")
    assert D.decide_share(T, sh["id"], True, sh["hash"], by_tap=True)["say"].endswith("'shared' hai.")


def test_grade_sheet_unsigned_and_report_card(office):
    D, S, kids = office
    rows = [{"roll": "1", "answers": ["b", "c", "42"]}, {"roll": "2", "answers": ["b", "a", "41"]},
            {"roll": "3", "answers": ["b", "c", "42"]}, {"roll": "99", "answers": ["a"]}]
    out = D.grade_sheet(T, "10-A", "Unit test 1", "Mathematics", key=["b", "c", "42"], rows=rows)
    res = {r["name"]: r for r in out["results"]}
    assert res["Riya"]["marks"] == 3 and res["Kabir"]["marks"] == 1 and res["Kabir"]["wrong"] == [2, 3]
    assert out["stats"]["unmatched"] == ["99"] and out["stats"]["no_consent"] == [kids[2]] and "UNSIGNED" in out["say"]
    rc = D.report_card(T, kids[0])
    assert rc["subjects"] == [] and rc["unsigned_left"] == 1                   # nothing signed yet
    with pytest.raises(D.DaftarError, match="sign-off"):
        D.report_card_file(T, kids[0])
    ids = [m["id"] for m in D.unsigned(T, "10-A")["marks"]]
    S.sign_off(T, ids)
    rc = D.report_card(T, kids[0])
    assert rc["total"] == 3 and rc["pct"] == 100.0 and rc["grade"] == "A1"
    f = D.report_card_file(T, kids[0])
    assert f["file"]["name"] == f"report_{kids[0]}.docx"
    sh = D.report_card_share(T, kids[0])["share"]
    done = D.decide_share(T, sh["id"], True, sh["hash"], by_tap=True)
    assert done["file"] and done["links"]["whatsapp"].startswith("https://wa.me/919876500001")


def test_grade_sheet_from_csv(office, monkeypatch):
    D, S, kids = office
    from pathlib import Path
    from app.mailbox import service as ms
    p = Path(__import__("tempfile").mkdtemp()) / "s.csv"
    p.write_bytes("Roll No,Name,Q1,Q2\n1,Riya,A,B\n2,Kabir,A,A\n".encode())
    monkeypatch.setattr(ms, "_file_row", lambda tenant, fid: type("F", (), {"stored_path": str(p)})())
    out = D.grade_sheet(T, "10-A", "Quiz 2", "Mathematics", key=["a", "b"], file_id="f1")
    assert {r["name"]: r["marks"] for r in out["results"]} == {"Riya": 2, "Kabir": 1}


def test_omr_read_is_for_the_teacher_to_confirm(office, monkeypatch):
    D, S, kids = office
    from app.mailbox import service as ms
    monkeypatch.setattr(ms, "_file_row", lambda tenant, fid: type("F", (), {"stored_path": __file__})())
    monkeypatch.setattr(D, "_model_json", lambda *a, **k: {"roll": "1", "answers": ["B", "", "D"], "unclear": [2]})
    r = D.omr_read(T, "f1", 4)
    assert r["answers"] == ["B", "", "D", ""] and r["unclear"] == [2, 4] and "save nahi" in r["say"]
    assert D.unsigned(T)["marks"] == []                     # nothing saved


def test_grade_forms_from_a_pathyakram_quiz(office, monkeypatch):
    D, S, kids = office
    from app.forms import service as F
    from app.pathyakram import service as P
    S.save_questions(T, [{"qtype": "mcq", "text": f"Forms question {i}: pick the right option for item {i}?",
                          "options": ["p", "q", "r", "s"], "answer": "q", "marks": 1, "chapter": "Real Numbers"} for i in range(2)],
                     board="CBSE", grade="10", subject="Mathematics")
    S.set_status(T, [q["number"] for q in S.bank(T)["questions"]], "approved")
    monkeypatch.setattr(P, "_publish", lambda *a, **k: None)
    paper = P.make_paper(T, "Mathematics", "10", sections=[{"name": "A", "qtype": "mcq", "count": 2, "marks_each": 1}])["paper"]
    monkeypatch.setattr(F, "responses", lambda tenant, form, limit=50: {
        "columns": ["Roll number", "Q1. Forms question 0...", "Q2. Forms question 1..."],
        "rows": [{"Roll number": "1", "Q1. Forms question 0...": "q", "Q2. Forms question 1...": "q"},
                 {"Roll number": "2", "Q1. Forms question 0...": "p", "Q2. Forms question 1...": "q"}]})
    out = D.grade_forms(T, "10-A", "Forms quiz", "f123", paper["number"])
    assert {r["name"]: r["marks"] for r in out["results"]} == {"Riya": 2, "Kabir": 1}


def test_grade_code_in_the_sandbox(office):
    D, S, kids = office
    code = "def add(a, b):\n    return a + b\n\ndef area(r):\n    return 3.14159 * r * r\n"
    tests = [{"call": "add(2, 3)", "expected": 5}, {"call": "add(-1, 1)", "expected": 0},
             {"call": "area(1)", "expected": 3.14159}, {"call": "missing()", "expected": 1}]
    r = D.grade_code(T, kids[0], "Lab 1", code, tests, max_marks=8)
    assert r["passed"] == 3 and r["marks"] == 6 and "NameError" in r["details"][3]["why"]
    bad = D.grade_code(T, kids[0], "Lab 2", "def add(a, b) return", tests[:1], max_marks=5)
    assert bad["passed"] == 0 and "chala hi nahi" in bad["details"][0]["why"]
    evil = D.grade_code(T, kids[0], "Lab 3", "import os\nos.system('id')\ndef add(a,b): return a+b", tests[:1], max_marks=5)
    assert evil["passed"] == 0                               # the sandbox refuses; nothing runs outside
    with pytest.raises(D.DaftarError, match="consent"):
        D.grade_code(T, kids[2], "Lab 1", code, tests)


def test_grade_rubric_is_a_capped_suggestion(office, monkeypatch):
    D, S, kids = office
    from app.pathyakram import service as P
    monkeypatch.setattr(P, "_publish", lambda *a, **k: None)
    crit = [{"name": n, "points": 5, "levels": [{"label": l, "descriptor": f"{n} {l}"} for l in ("A", "B", "C", "D")]}
            for n in ("Content", "Language")]
    monkeypatch.setattr(P, "_model_json", lambda *a, **k: {"criteria": crit})
    rb = P.rubric(T, "Essay", "English", "10", levels=4, total_points=10)["plan"]["number"]
    monkeypatch.setattr(D, "_model_json", lambda *a, **k: {"criteria": [{"name": "Content", "level": "A", "points": 99, "evidence": "x"},
                                                                       {"name": "Language", "level": "C", "points": 2}], "comment": "ok"})
    r = D.grade_rubric(T, kids[0], "Essay 1", "My essay text", rb)
    assert r["marks"] == 7 and r["criteria"][0]["points"] == 5 and "SUJHAAV" in r["say"]


def test_timetable_has_no_clashes(office):
    D, S, kids = office
    needs = [{"class": c, "subject": s, "teacher": t, "per_week": k}
             for c in ("9-A", "10-A") for s, t, k in (("Maths", "Mrs Rao", 6), ("Science", "Mr Das", 5), ("English", "Ms Iyer", 5))]
    r = D.timetable(T, needs, periods=6, max_same=2)
    grid = r["grid"]
    for c in ("9-A", "10-A"):
        cells = [x for d in grid[c].values() for x in d if x]
        assert sum(1 for x in cells if x.startswith("Maths")) == 6
        for d, ps in grid[c].items():
            assert sum(1 for x in ps if x.startswith("Maths")) <= 2
    for d in grid["9-A"]:
        for p in range(6):
            a, b = grid["9-A"][d][p], grid["10-A"][d][p]
            assert not (a and b and a.split(" / ")[1] == b.split(" / ")[1])    # no teacher in two rooms
    assert "Mrs Rao" in r["teachers"]
    with pytest.raises(D.DaftarError, match="hafte"):
        D.timetable(T, [{"class": "9-A", "subject": "Maths", "teacher": "X", "per_week": 50}], periods=6)


def test_grade_scale_and_sheet_reader():
    from app.daftar import rules as R
    assert [R.grade_of(p) for p in (95, 85, 72, 61, 55, 45, 33, 10)] == ["A1", "A2", "B1", "B2", "C1", "C2", "D", "E"]
    rows = R.read_sheet("roll,Q1,Q3\n5,a,c\n,,\n".encode())
    assert rows == [{"roll": "5", "name": "", "answers": ["a", "", "c"]}]


def test_tools_api_and_wiring(office):
    D, S, kids = office
    from app import voice
    from app.agent import tools as TL
    from app.agent.daftar_tools import DAFTAR_HANDLERS, DAFTAR_LABELS, DAFTAR_TOOLS
    from app.agent.tools import ToolError
    from app.employee import roles
    assert {t["name"] for t in DAFTAR_TOOLS} == set(DAFTAR_HANDLERS) == set(DAFTAR_LABELS)
    assert all(n in TL.HANDLERS for n in DAFTAR_HANDLERS) and "daftar_dekho" in roles.READ
    assert roles.duty_of("daftar") == "school_office" and roles.PRESETS["school_office"]["role"] == "school_admin"
    assert set(DAFTAR_HANDLERS) <= voice.VOICE_VIA_KAAM
    ctx = conv_ctx()
    out = asyncio.run(DAFTAR_HANDLERS["daftar"](ctx, action="attendance", **{"class": "10-A", "absent": ["1"]}))
    assert out["counts"]["absent"] == 1
    ctx.actor = "customer:x"
    with pytest.raises(ToolError):
        asyncio.run(DAFTAR_HANDLERS["daftar_dekho"](ctx, what="unsigned"))
    from app.daftar.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.get("/api/daftar").json()["attendance_pending"] == []
    assert c.get("/api/daftar/attendance", params={"class_ref": "10-A"}).json()["school_days"] == 1
    from app import main
    assert TestClient(main.app).get("/api/daftar").status_code in (200, 401, 403)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.655.0"
