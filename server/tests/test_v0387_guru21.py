"""Shiksha Phase 2.1 (after reading DeepTutor, Apache-2.0): mastery with a confidence cap, SM-2 revision with an exam
window / cramming, a mastery path over the NCERT chapters with a gate per chapter, and explanations grounded in her own
books (Gyaan) with page cites - a cite that points at no source is removed."""
from datetime import date, timedelta

import pytest

import app.guru.models  # noqa: F401
import app.shiksha.models  # noqa: F401
from tests.test_v0387_guru import LADDER

T = "default"


@pytest.fixture
def g10(env, monkeypatch):
    from app.guru import service as G
    from app.shiksha import service as S
    monkeypatch.setattr(G, "_publish", lambda *a, **k: None)
    monkeypatch.setattr(G, "_book_sources", lambda tenant, q: [])
    S.add_class(T, "10-A", subjects=["Mathematics"])
    kid = S.add_learner(T, "Isha", "10-A", birth_year=2011, guardian_name="Ravi", guardian_phone="9876501234")["number"]
    S.record_consent(T, kid, True, "school_record")
    return G, S, kid


def test_mastery_confidence_cap_and_recency():
    from app.guru import rules as R
    assert R.compute_mastery([]) == 0.0
    assert R.compute_mastery([1.0]) == 0.5                 # one lucky answer is not mastery
    assert R.compute_mastery([1.0, 1.0]) == 0.8
    assert R.compute_mastery([1.0] * 5) == 1.0
    assert R.compute_mastery([0, 0, 0, 1, 1]) > R.compute_mastery([1, 1, 0, 0, 0])   # recent answers count more
    assert R.credit(1.0, 2) == pytest.approx(0.6) and R.credit(1.0, 9) == pytest.approx(0.4)


def test_sm2_and_exam_window():
    from app.guru import rules as R
    iv, ease, streak, lapses = R.sm2(1, 2.5, 0, 0, "good")
    assert (iv, streak) == (3, 1)
    iv2, ease2, _, _ = R.sm2(iv, ease, streak, lapses, "good")
    assert iv2 == round(3 * 2.5)
    iv3, ease3, _, _ = R.sm2(iv2, ease2, 2, 0, "easy")
    assert iv3 > iv2 and ease3 > ease2
    again = R.sm2(20, 2.5, 4, 0, "again")
    assert again[0] == 1 and again[1] == pytest.approx(2.3) and again[2] == 0 and again[3] == 1
    assert R.sm2(20, 2.5, 4, 0, "again", cramming=True)[0] == 0
    assert R.rating(1.0, 0) == "easy" and R.rating(1.0, 1) == "good" and R.rating(0.6, 0) == "hard" and R.rating(0.2, 0) == "again"
    d = date(2026, 11, 1)
    assert R.fit_exam(30, d, d + timedelta(days=12)) == 4 and R.fit_exam(30, d, None) == 30
    assert R.cramming("long_term", d, d + timedelta(days=20)) and not R.cramming("long_term", d, d + timedelta(days=90))


def _bank(S, chapters):
    qs = []
    for ch in chapters:
        for i in range(4):
            qs.append({"qtype": "mcq", "text": f"{ch}: practice question number {i} about this chapter's idea?",
                       "options": ["w", "x", "y", "z"], "answer": "x", "marks": 1, "steps": ["Think"], "difficulty": "easy",
                       "chapter": ch})
    S.save_questions(T, qs, board="CBSE", grade="10", subject="Mathematics")
    S.set_status(T, [q["number"] for q in S.bank(T, limit=200)["questions"]], "approved")


def test_answer_uses_capped_mastery_and_sm2(g10):
    G, S, kid = g10
    _bank(S, ["Real Numbers"])
    sid = G.start(T, kid, "practice", "Mathematics")["number"]
    G.next_question(T, sid)
    r = G.answer(T, sid, "b")
    assert r["score"] == 1 and r["mastery"] == 0.5 and r["rating"] == "easy"
    G.save_settings(T, exam_date=(date.today() + timedelta(days=9)).isoformat())
    G.next_question(T, sid)
    r2 = G.answer(T, sid, "b")
    assert r2["cramming"] and date.fromisoformat(r2["next_revision"]) <= date.today() + timedelta(days=3)
    with pytest.raises(G.GuruError, match="YYYY"):
        G.save_settings(T, exam_date="15 Feb")


def test_mastery_path_gate_opens_chapters_in_order(g10):
    G, S, kid = g10
    from app.shiksha import rules as SR
    lib = SR.chapters("Mathematics", "10")["chapters"]
    p = G.build_path(T, kid, "Mathematics")
    assert [c["chapter"] for c in p["chapters"]] == lib
    assert p["chapters"][0]["state"] == "current" and p["chapters"][1]["state"] == "locked"
    _bank(S, lib[:2])
    sid = G.start(T, kid, "practice", "Mathematics")["number"]
    seen = []
    for _ in range(3):
        q = G.next_question(T, sid)
        assert q["question"]["topic"] == lib[0] and "Path" in q["path"]     # never a locked chapter
        seen.append(q["question"]["number"])
        G.answer(T, sid, "b")
    v = G.path_view(T, kid, "Mathematics")
    assert v["chapters"][0]["state"] == "passed" and v["current"] == lib[1]
    nxt = G.next_question(T, sid)
    assert nxt["question"]["topic"] == lib[1]
    with pytest.raises(G.GuruError, match="chapter"):
        G.build_path(T, kid, "Mathematics", grade="6")               # incomplete book: teacher gives the list
    own = G.build_path(T, kid, "Science", chapters=["Light", "Electricity"])
    assert own["source"] == "teacher" and own["current"] == "Light"


def test_grounded_doubt_cites_her_book_with_page(g10, monkeypatch):
    G, S, kid = g10
    seen = {}
    monkeypatch.setattr(G, "_book_sources", lambda tenant, q: [
        {"title": "NCERT Maths Class 10", "page": 12, "text": "To solve a linear equation, do the same operation on both sides.", "link": ""}])

    def model(system, prompt, max_tokens=3000, image=None):
        seen["prompt"] = prompt
        return {**LADDER, "hint": "Dono taraf ek hi kaam [1].", "steps": ["Subtract 6 from both sides [1]", "Divide by 2 [5]"]}
    monkeypatch.setattr(G, "_model_json", model)
    sid = G.start(T, kid, "doubt", "Mathematics")["number"]
    d = G.doubt(T, sid, "2x + 6 = 20")
    assert "[1] NCERT Maths Class 10 (page 12)" in seen["prompt"]
    assert d["sources"] == [{"n": 1, "title": "NCERT Maths Class 10", "page": 12, "link": ""}]
    G.hint(T, sid)
    steps = G.hint(T, sid)
    assert "[5]" not in steps["text"] and "From the book: [1] NCERT Maths Class 10, page 12" in steps["text"]
    G.save_settings(T, grounded=False)
    sid2 = G.start(T, kid, "doubt", "Mathematics")["number"]
    seen.clear()
    G.doubt(T, sid2, "2x + 6 = 20")
    assert "Her own books" not in seen["prompt"]


def test_path_tools(g10):
    import asyncio
    G, S, kid = g10
    from app.agent.guru_tools import GURU_HANDLERS
    from tests.test_life import conv_ctx
    ctx = conv_ctx()
    out = asyncio.run(GURU_HANDLERS["guru"](ctx, action="path", learner=kid, subject="Mathematics"))
    assert out["current"]
    v = asyncio.run(GURU_HANDLERS["guru_dekho"](ctx, what="path", learner=kid, subject="Mathematics"))
    assert v["chapters"][0]["state"] == "current"
    st = asyncio.run(GURU_HANDLERS["guru"](ctx, action="settings", strategy="cramming", gate=0.9))
    assert st["strategy"] == "cramming" and st["gate"] == 0.9
