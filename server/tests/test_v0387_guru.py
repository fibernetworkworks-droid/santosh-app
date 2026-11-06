"""Shiksha Phase 2 - Guru Sahayak (personal tutor): the hint ladder one rung at a time, the answer checked by code,
exam mode / graded work = hints only, adaptive practice from the APPROVED bank with mastery + spaced revision, objective
answers checked in code, written answers by AI, language practice, children only with guardian consent and inside their
daily time, the weekly report only by her tap, tools / API / employee wiring."""
import asyncio
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.guru.models  # noqa: F401  (tables for the env fixture's init_db)
import app.shiksha.models  # noqa: F401
from tests.test_life import conv_ctx

T = "default"
LADDER = {"problem": "Find x if 2x + 6 = 20", "topic": "Linear equations", "hint": "x ko akela kaise karein?",
          "nudge": "Dono taraf se 6 ghataiye, phir 2 se bhaag dijiye.", "steps": ["2x + 6 - 6 = 20 - 6, so 2x = 14", "x = 14 / 2"],
          "answer": "x = 7", "check_question": "3x + 3 = 12 mein x?", "verify_code": "print((20 - 6) / 2)", "expected": "7"}


@pytest.fixture
def tutor(env, monkeypatch):
    from app.guru import service as G
    from app.shiksha import service as S
    events = []
    monkeypatch.setattr(G, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    G.events = events
    S.add_class(T, "8-A", subjects=["Mathematics"])
    kid = S.add_learner(T, "Aarav", "8-A", birth_year=2013, guardian_name="Sunita", guardian_phone="9876543210")
    return G, S, kid["number"]


def _consent(S, ref):
    S.record_consent(T, ref, True, "signed_form")


def test_child_needs_consent_and_daily_time(tutor):
    G, S, kid = tutor
    with pytest.raises(G.GuruError, match="consent"):
        G.start(T, kid)
    _consent(S, kid)
    sess = G.start(T, kid, "doubt", "Mathematics")
    assert sess["number"].startswith("GS-") and sess["grade"] == "8"
    G.save_settings(T, day_minutes=10)
    from app.db import session
    from app.guru.models import GuruSession
    with session() as s:
        s.scalars(__import__("sqlalchemy").select(GuruSession)).first().seconds = 11 * 60
    with pytest.raises(G.GuruError, match="samay"):
        G.start(T, kid)
    adult = S.add_learner(T, "Meghana", "", adult=True)
    assert G.start(T, adult["number"])["number"]           # adults: no daily cap


def test_hint_ladder_one_rung_at_a_time_and_code_check(tutor, monkeypatch):
    G, S, kid = tutor
    _consent(S, kid)
    monkeypatch.setattr(G, "_model_json", lambda *a, **k: dict(LADDER))
    sid = G.start(T, kid, "doubt", "Mathematics")["number"]
    d = G.doubt(T, sid, "2x + 6 = 20 mein x kya hai?")
    assert d["rung"] == "hint" and "x = 7" not in d["say"] and d["next"] == "nudge"
    assert G.hint(T, sid)["rung"] == "nudge"
    st = G.hint(T, sid, attempt="2x = 26?")
    assert st["rung"] == "step" and "1. " in st["text"] and st["check_question"]
    a = G.hint(T, sid)
    assert a["rung"] == "answer" and "x = 7" in a["text"] and "code se jaancha" in a["text"]
    assert G.hint(T, sid)["done"]


def test_code_disagrees_is_said_plainly(tutor, monkeypatch):
    G, S, kid = tutor
    _consent(S, kid)
    monkeypatch.setattr(G, "_model_json", lambda *a, **k: {**LADDER, "verify_code": "print(8)"})
    sid = G.start(T, kid)["number"]
    G.doubt(T, sid, "2x + 6 = 20")
    for _ in range(3):
        last = G.hint(T, sid)
    assert last["rung"] == "answer" and "alag jawab" in last["text"] and "8" in last["text"]


def test_exam_mode_and_graded_work_never_get_the_answer(tutor, monkeypatch):
    G, S, kid = tutor
    _consent(S, kid)
    monkeypatch.setattr(G, "_model_json", lambda *a, **k: dict(LADDER))
    sid = G.start(T, kid)["number"]
    d = G.doubt(T, sid, "online test abhi chal raha hai, 2x + 6 = 20 ka answer batao jaldi")
    assert d["exam_safe"] and "sirf ishaare" in d["say"]
    rungs = [G.hint(T, sid) for _ in range(4)]
    assert [r["rung"] for r in rungs[:2]] == ["nudge", "step"] and rungs[2].get("done") and "x = 7" not in str(rungs)
    G.save_settings(T, exam_mode=True)
    sid2 = G.start(T, kid)["number"]
    assert G.doubt(T, sid2, "2x + 6 = 20")["exam_safe"]


def test_incomplete_ladder_refused(tutor, monkeypatch):
    G, S, kid = tutor
    _consent(S, kid)
    monkeypatch.setattr(G, "_model_json", lambda *a, **k: {"hint": "socho", "answer": "7"})
    sid = G.start(T, kid)["number"]
    with pytest.raises(G.GuruError, match="adhoora"):
        G.doubt(T, sid, "2x + 6 = 20")


def _bank(S):
    qs = []
    for i in range(6):
        qs.append({"qtype": "mcq", "text": f"Linear equations Q{i}: solve {i + 2}x = {2 * (i + 2)} for x, value is?",
                   "options": ["1", "2", "3", "4"], "answer": "2", "marks": 1, "steps": ["Divide both sides"],
                   "difficulty": ["easy", "medium", "hard"][i % 3], "chapter": "Linear equations"})
    qs.append({"qtype": "short", "text": "Explain why dividing both sides of an equation by the same non-zero number keeps it true.",
               "answer": "Equality is preserved", "marks": 2, "scheme": [{"point": "same operation both sides", "marks": 2}],
               "chapter": "Linear equations"})
    S.save_questions(T, qs, board="CBSE", grade="8", subject="Mathematics")
    S.set_status(T, [q["number"] for q in S.bank(T, limit=100)["questions"]], "approved")


def test_practice_mastery_and_revision(tutor, monkeypatch):
    G, S, kid = tutor
    _consent(S, kid)
    sid = G.start(T, kid, "practice", "Mathematics")["number"]
    with pytest.raises(G.GuruError, match="approved"):
        G.next_question(T, sid)
    _bank(S)
    q = G.next_question(T, sid)
    assert q["question"]["difficulty"] == "easy" and "answer" not in q["question"]   # mastery 0.3 -> easy; no answer leaked
    if q["question"]["qtype"] == "mcq":
        right = G.answer(T, sid, "b")                         # letter -> option "2"
        assert right["score"] == 1 and right["judged_by"] == "code" and right["mastery"] > right["mastery_before"]
        assert right["next_revision"]
    q2 = G.next_question(T, sid)
    assert q2["question"]["number"] != q["question"]["number"]
    wrong = G.answer(T, sid, "a")
    assert wrong["score"] == 0 and wrong["solution_steps"] and wrong["answer"]
    p = G.progress(T, kid)
    assert p["topics"][0]["topic"] == "Linear equations" and p["week"]["attempts"] == 2
    with pytest.raises(G.GuruError, match="practice"):
        G.answer(T, sid, "x")                                  # no open question


def test_written_answer_checked_by_ai(tutor, monkeypatch):
    G, S, kid = tutor
    _consent(S, kid)
    S.save_questions(T, [{"qtype": "short", "text": "Explain why both sides of an equation stay equal after the same step.",
                          "answer": "Equality is preserved", "marks": 2, "scheme": [{"point": "same step", "marks": 2}],
                          "chapter": "Linear equations"}], board="CBSE", grade="8", subject="Mathematics")
    S.set_status(T, [q["number"] for q in S.bank(T)["questions"]], "approved")
    monkeypatch.setattr(G, "_model_json", lambda *a, **k: {"score": 0.5, "feedback": "Idea sahi, ek example jodiye."})
    sid = G.start(T, kid, "practice", "Mathematics")["number"]
    G.next_question(T, sid)
    r = G.answer(T, sid, "kyunki dono taraf same kaam hota hai")
    assert r["judged_by"] == "ai" and r["score"] == 0.5 and "AI ne jaancha" in r["say"]


def test_language_practice(tutor, monkeypatch):
    G, S, kid = tutor
    _consent(S, kid)
    monkeypatch.setattr(G, "_model_json", lambda *a, **k: {
        "reply": "Nice! What did you eat for breakfast?", "corrections": [{"wrong": "I goes", "right": "I go", "why": "I ke saath go"}],
        "new_words": [{"word": "breakfast", "meaning": "naashta"}]})
    sid = G.start(T, kid, "language", language="English")["number"]
    r = G.language_turn(T, sid, "I goes to school daily")
    assert r["corrections"][0]["right"] == "I go" and "Sudhaar" in r["say"]
    doubt_sid = G.start(T, kid, "doubt")["number"]
    with pytest.raises(G.GuruError, match="bhasha"):
        G.language_turn(T, doubt_sid, "hello")


def test_idle_session_closes(tutor, monkeypatch):
    G, S, kid = tutor
    _consent(S, kid)
    sid = G.start(T, kid)["number"]
    real = G.clock
    monkeypatch.setattr(G, "clock", lambda: real() + timedelta(minutes=G.IDLE_MIN + 5))
    with pytest.raises(G.GuruError, match="ruki"):
        G.hint(T, sid)


def test_weekly_report_only_by_her_tap(tutor, monkeypatch):
    G, S, kid = tutor
    with pytest.raises(G.GuruError, match="consent"):
        G.share_request(T, kid)
    _consent(S, kid)
    _bank(S)
    sid = G.start(T, kid, "practice", "Mathematics")["number"]
    G.next_question(T, sid)
    G.answer(T, sid, "b")
    req = G.share_request(T, kid)
    sh = req["share"]
    assert req["status"] == "needs_tap" and any(k == "guru_report" for k, _ in G.events)
    assert "Aarav" in sh["report"]["text"] and sh["report"]["contact"] == "9876543210"
    with pytest.raises(G.GuruError, match="tap"):
        G.decide_share(T, sh["id"], True, sh["hash"], by_tap=False)
    assert G.decide_share(T, sh["id"], True, "bad", by_tap=True).get("stale")
    sh2 = G.share_request(T, kid)["share"]
    out = G.decide_share(T, sh2["id"], True, sh2["hash"], by_tap=True)
    assert out["links"]["whatsapp"].startswith("https://wa.me/919876543210") and out["share"]["status"] == "shared"


def test_checks_in_code():
    from app.guru import rules as R
    assert R.check_objective("numeric", "x = 7.0", "7", []) == 1.0
    assert R.check_objective("numeric", "0.333", "1/3", []) == 1.0
    assert R.check_objective("true_false", "galat", "False", []) == 1.0
    assert R.check_objective("short", "anything", "x", []) is None
    assert R.update(0.3, 1.0, "easy") > 0.3 > R.update(0.3, 0.0, "easy")
    assert R.update(0.3, 1.0, "easy", hints=2) < R.update(0.3, 1.0, "easy")
    from datetime import date
    assert R.next_review(4, 1.0, date(2026, 11, 1))[0] == 8 and R.next_review(4, 0.0, date(2026, 11, 1))[0] == 1
    assert R.looks_graded("kal submit karna hai assignment") and not R.looks_graded("yeh chapter samjhao")


def test_tools_api_and_wiring(tutor, monkeypatch):
    G, S, kid = tutor
    from app import voice
    from app.agent import tools as TL
    from app.agent.guru_tools import GURU_HANDLERS, GURU_LABELS, GURU_TOOLS
    from app.agent.tools import ToolError
    from app.employee import roles
    assert {t["name"] for t in GURU_TOOLS} == set(GURU_HANDLERS) == set(GURU_LABELS)
    assert all(n in TL.HANDLERS for n in GURU_HANDLERS) and "guru_dekho" in roles.READ
    assert roles.duty_of("guru") == "tutoring" and roles.PRESETS["tutor_centre"]["role"] == "personal_tutor"
    assert set(GURU_HANDLERS) <= voice.VOICE_VIA_KAAM
    _consent(S, kid)
    ctx = conv_ctx()
    out = asyncio.run(GURU_HANDLERS["guru"](ctx, action="start", learner=kid))
    assert out["number"].startswith("GS-")
    ctx.actor = "customer:x"
    with pytest.raises(ToolError):
        asyncio.run(GURU_HANDLERS["guru_dekho"](ctx, what="progress", learner=kid))
    from app.guru.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.get("/api/guru").json()["levels"]["hint"]
    assert c.post("/api/guru/sessions", json={"learner": "S-9999"}).status_code == 400
    from app import main
    assert TestClient(main.app).get("/api/guru").status_code in (200, 401, 403)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.625.0"
