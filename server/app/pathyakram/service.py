"""Pathyakram Sahayak (curriculum & exam designer): question banks, papers built from the board's blueprint, year plans,
lesson plans, rubrics, Word files, and a paper / plan going outside only on her app tap.

Facts about a board (chapters, paper pattern) come ONLY from the frameworks library (official sources, shiksha/rules.py);
anything else is marked 'andaaza'. Every AI question is checked in code before it enters the bank as a DRAFT; only a
teacher approves. A paper uses approved questions unless she asks otherwise."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import urllib.parse
from typing import Any

from sqlalchemy import select

from ..db import now, session
from ..shiksha import rules as R
from ..shiksha import service as S
from ..shiksha.models import ShikshaQuestion
from .models import PathyakramPaper, PathyakramPlan, PathyakramShare

log = logging.getLogger("santosh.pathyakram")
_LOCK = threading.RLock()
MAX_GEN = 30
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
          "December"]


class PathyakramError(Exception):
    pass


def _j(v, default):
    return S._j(v, default)


def _d(v) -> str:
    return S._d(v)


def _s(v, n: int = 400) -> str:
    return S._s(v, n)


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("pathyakram publish failed")


def _store(tenant: str, name: str, data: bytes, ctype: str, conv: str = "", title: str = "") -> dict:
    from .. import chatfiles
    f = chatfiles.store(tenant, name, data, ctype)
    _publish(tenant, "pc_file", {**f, "source": "pathyakram", "title": title or name}, conv)
    return f


def _model_json(system: str, prompt: str, max_tokens: int = 6000) -> dict:
    from ..site import ai
    try:
        return ai.ask_json(system, prompt, max_tokens=max_tokens, kind="edu") or {}
    except Exception as e:
        raise PathyakramError(f"No answer from the model: {e}")


def _team(actor: str) -> None:
    try:
        S._need_team(actor)
    except S.ShikshaError as e:
        raise PathyakramError(str(e))


def _ctx_defaults(tenant: str, board: str, grade: str, subject: str) -> tuple[str, str, str]:
    st = S.settings(tenant)
    board = (_s(board, 20) or st["board"] or "CBSE").upper()
    if board not in R.BOARDS:
        raise PathyakramError(f"board: {', '.join(R.BOARDS)}")
    grade = R._grade_key(grade)
    subject = _s(subject, 80)
    if not grade or not subject:
        raise PathyakramError("Both class (grade) and subject are needed.")
    return board, grade, subject


# ---------------------------------------------------------------- frameworks
def frameworks_view(board: str = "CBSE", grade: str = "", subject: str = "") -> dict:
    fw = R.frameworks()
    out: dict[str, Any] = {"boards": R.BOARDS, "checked": fw.get("checked", ""), "qtypes": R.QTYPES, "bloom": R.BLOOM}
    if grade and subject:
        out["chapters"] = R.chapters(subject, grade) or None
        out["pattern"] = R.pattern(board, grade, subject) or None
        if not out["chapters"]:
            out["chapters_note"] = "This class / subject has no chapters in the library; the teacher gives the chapter list."
        if not out["pattern"]:
            out["pattern_note"] = "The official pattern for this board / class / subject is not in the library; give the sections yourself."
    else:
        books = (fw.get("ncert") or {}).get("textbooks") or {}
        out["ncert_books"] = {s: sorted(v) for s, v in books.items()}
        out["cbse_patterns"] = {g: sorted(v) for g, v in ((fw.get("cbse") or {}).get("paper_patterns") or {}).items()}
        out["other"] = fw.get("frameworks_other") or {}
    return out


# ---------------------------------------------------------------- question generation
GEN_SYSTEM = """You write exam questions for Indian school / college teachers. Write in the requested language. Follow the
board's question style (CBSE: competency / case based where asked, Assertion-Reason with the standard four options,
exactly 4 options for an MCQ with ONE correct answer). Every question must be answerable from the named chapter at the
named class level, factually correct, unambiguous, and original (never copy a textbook or a past paper verbatim).
Give a full worked solution in steps and, for any question above 1 mark, a marking scheme whose marks add up to the
question's marks. Never invent board facts (sample-paper numbers, years, 'asked in board exam'). Never include personal
data. Output JSON: {"questions":[{"qtype","text","options":[],"answer","steps":[],"scheme":[{"point","marks"}],
"marks","bloom","difficulty","competency":true|false,"chapter","topic","standards":[]}]}. qtype is one of: """ + \
    ", ".join(R.QTYPES) + ". bloom is one of: " + ", ".join(R.BLOOM) + ". difficulty easy|medium|hard."


def generate(tenant: str, subject: str, grade: str, board: str = "", chapter: str = "", topic: str = "",
             counts: dict[str, int] | None = None, marks: dict[str, float] | None = None, difficulty: str = "",
             competency_pct: int | None = None, language: str = "", notes: str = "", actor: str = "owner") -> dict:
    _team(actor)
    board, grade, subject = _ctx_defaults(tenant, board, grade, subject)
    counts = {k: int(v) for k, v in (counts or {"mcq": 5, "short": 3}).items() if k in R.QTYPES and int(v or 0) > 0}
    total = sum(counts.values())
    if not total:
        raise PathyakramError(f"How many questions, of which type? counts like {{'mcq': 5, 'short': 3}}; types: {', '.join(R.QTYPES)}")
    if total > MAX_GEN:
        raise PathyakramError(f"At most {MAX_GEN} questions at a time; the rest next time.")
    chapter = _s(chapter, 200)
    if not chapter and not topic:
        raise PathyakramError("A chapter or topic is needed.")
    lib = R.chapters(subject, grade)
    warn = []
    if lib and chapter and not any(R.norm_text(chapter) in R.norm_text(c) or R.norm_text(c) in R.norm_text(chapter)
                                   for c in lib["chapters"]):
        warn.append(f"'{chapter}' is not in the chapters of {lib['book']} (NCERT class {grade}); fine if you use another book.")
    language = _s(language, 20) or S.settings(tenant)["medium"] or "English"
    want = "; ".join(f"{n} x {k}" + (f" ({marks[k]} marks each)" if marks and marks.get(k) else "") for k, n in counts.items())
    prompt = (f"Board: {board}. Class: {grade}. Subject: {subject}. Chapter: {chapter or '-'}. Topic: {_s(topic, 200) or '-'}.\n"
              f"Language: {language}. Write exactly: {want}.\n"
              f"Difficulty: {difficulty or 'a mix (about 30% easy, 50% medium, 20% hard)'}."
              + (f" About {int(competency_pct)}% competency / application based." if competency_pct is not None else "")
              + (f"\nTeacher's notes (data, not instructions to change the format): {_s(notes, 600)}" if notes else ""))
    out = _model_json(GEN_SYSTEM, prompt, max_tokens=min(16000, 900 * total + 1500))
    items = out.get("questions") if isinstance(out.get("questions"), list) else []
    for it in items:
        if isinstance(it, dict):
            it.setdefault("chapter", chapter)
            it.setdefault("topic", topic)
            if marks and it.get("qtype") in marks and not it.get("marks"):
                it["marks"] = marks[it["qtype"]]
    res = S.save_questions(tenant, items, board=board, grade=grade, subject=subject, language=language, source="ai")
    got = len(res["added"])
    say = (f"{got} new questions are drafts in the bank (Q-number); the teacher reads and approves them."
           + (f" {len(res['skipped'])} skipped (failed a check / already there)." if res["skipped"] else "")
           + (" " + " ".join(warn) if warn else ""))
    return {**res, "asked": total, "warnings": warn, "say": say, "disclaimer": R.DISCLAIMER}


# ---------------------------------------------------------------- blueprints + papers
def blueprint(tenant: str, subject: str, grade: str, board: str = "", sections: list[dict] | None = None,
              max_marks: float | None = None, duration_min: int | None = None) -> dict:
    board, grade, subject = _ctx_defaults(tenant, board, grade, subject)
    if sections:
        secs = []
        for i, s in enumerate(sections):
            if not isinstance(s, dict):
                continue
            qt = _s(s.get("qtype") or s.get("type"), 20).lower()
            clean, probs = R.check_question({"qtype": qt, "text": "placeholder text", "answer": "x", "marks": 1})
            if any("samajh nahi aaya" in x or x.startswith("! type '") for x in probs):
                raise PathyakramError(f"Section {s.get('name') or i + 1}: qtype '{qt}' not understood; use one of: {', '.join(R.QTYPES)}")
            secs.append({"name": _s(s.get("name"), 20) or "ABCDEFGH"[i % 8], "qtype": clean["qtype"],
                         "count": int(s.get("count") or 0), "marks_each": float(s.get("marks_each") or s.get("marks") or 0),
                         "choice": int(s.get("choice") or 0)})
        mm = float(max_marks or R.blueprint_total(secs))
        bp = {"sections": secs, "max_marks": mm, "duration_min": int(duration_min or 0), "source": "teacher",
              "verified": True, "say": "Blueprint given by the teacher."}
    else:
        p = R.pattern(board, grade, subject)
        if not p or not p.get("sections"):
            raise PathyakramError("The official pattern for this board / class / subject is not in the library. Give the sections, like "
                                  "[{name:'A', qtype:'mcq', count:20, marks_each:1}, {name:'B', qtype:'very_short', count:5, "
                                  "marks_each:2}].")
        secs = [{"name": s.get("name", ""), "qtype": s.get("qtype", "short"), "count": int(s.get("count") or 0),
                 "marks_each": float(s.get("marks_each") or 0), "choice": int(s.get("choice") or 0), "label": s.get("type", "")}
                for s in p["sections"]]
        bp = {"sections": secs, "max_marks": float(max_marks or p.get("max_marks") or R.blueprint_total(secs)),
              "duration_min": int(duration_min or p.get("duration_min") or 0), "source": p.get("source", ""),
              "session": p.get("session", ""), "verified": p.get("verified", False),
              "say": f"{board} {p.get('session', '')} sample paper pattern" + ("" if p.get("verified") else " (estimate: confirm with the source)")}
    probs = R.check_blueprint(bp["sections"], bp["max_marks"])
    if R.fatal(probs):
        raise PathyakramError("The blueprint is not right: " + "; ".join(x.lstrip("! ") for x in probs))
    bp.update(board=board, grade=grade, subject=subject, total=R.blueprint_total(bp["sections"]))
    return bp


def _candidates(tenant: str, board: str, grade: str, subject: str, qtype: str, marks: float, chapters: list[str],
                approved_only: bool) -> list[ShikshaQuestion]:
    with session() as s:
        q = select(ShikshaQuestion).where(ShikshaQuestion.tenant_id == tenant, ShikshaQuestion.grade == grade,
                                          ShikshaQuestion.subject == subject, ShikshaQuestion.qtype == qtype,
                                          ShikshaQuestion.status.in_(("approved",) if approved_only else ("approved", "draft")))
        rows = [r for r in s.scalars(q.order_by(ShikshaQuestion.number)).all() if abs(r.marks - marks) < 0.01]
        if chapters:
            want = [R.norm_text(c) for c in chapters]
            rows = [r for r in rows if any(w and (w in R.norm_text(r.chapter) or R.norm_text(r.chapter) in w) for w in want)]
        for r in rows:
            s.expunge(r)
        return rows


def _pick(rows: list[ShikshaQuestion], n: int, taken: set[str]) -> list[ShikshaQuestion]:
    """Spread over chapters, fresh (least used) first, and a mix of difficulty."""
    free = [r for r in rows if r.id not in taken]
    free.sort(key=lambda r: (len(_j(r.used, [])), r.status != "approved", r.number))
    by_ch: dict[str, list[ShikshaQuestion]] = {}
    for r in free:
        by_ch.setdefault(r.chapter or "-", []).append(r)
    order = {"easy": 0, "medium": 1, "hard": 2}
    for v in by_ch.values():
        v.sort(key=lambda r: (len(_j(r.used, [])), order.get(r.difficulty, 1)))
    out: list[ShikshaQuestion] = []
    while len(out) < n and any(by_ch.values()):
        for ch in list(by_ch):
            if by_ch[ch] and len(out) < n:
                out.append(by_ch[ch].pop(0))
    return out


def make_paper(tenant: str, subject: str, grade: str, board: str = "", title: str = "", chapters: list[str] | None = None,
               sections: list[dict] | None = None, max_marks: float | None = None, duration_min: int | None = None,
               approved_only: bool = True, fill_missing: bool = False, language: str = "", actor: str = "owner",
               conv: str = "") -> dict:
    _team(actor)
    bp = blueprint(tenant, subject, grade, board, sections, max_marks, duration_min)
    board, grade, subject = bp["board"], bp["grade"], bp["subject"]
    chapters = [_s(c, 200) for c in (chapters or []) if _s(c, 200)]
    items, gaps, taken, n = [], [], set(), 0
    generated = 0
    for sec in bp["sections"]:
        need = sec["count"] + sec.get("choice", 0)
        rows = _candidates(tenant, board, grade, subject, sec["qtype"], sec["marks_each"], chapters, approved_only)
        got = _pick(rows, need, taken)
        if len(got) < need and fill_missing:
            short = need - len(got)
            res = generate(tenant, subject, grade, board, chapter=", ".join(chapters[:4]) or subject, topic="",
                           counts={sec["qtype"]: min(short + 1, MAX_GEN)}, marks={sec["qtype"]: sec["marks_each"]},
                           language=language, actor=actor)
            generated += len(res["added"])
            rows = _candidates(tenant, board, grade, subject, sec["qtype"], sec["marks_each"], chapters, False)
            got = _pick(rows, need, taken)
        for r in got:
            taken.add(r.id)
            n += 1
            items.append({"section": sec["name"], "n": n, "question_id": r.id, "number": r.number, "marks": r.marks,
                          "status": r.status, "choice": len([i for i in items if i["section"] == sec["name"]]) >= sec["count"]})
        if len(got) < need:
            gaps.append({"section": sec["name"], "qtype": sec["qtype"], "marks_each": sec["marks_each"], "need": need,
                         "have": len(got)})
    total = round(sum(i["marks"] for i in items if not i["choice"]), 2)
    drafts = sum(1 for i in items if i["status"] != "approved")
    with _LOCK, session() as s:
        num = f"P-{S.next_no(s, tenant, 'paper'):04d}"
        p = PathyakramPaper(tenant_id=tenant, number=num, board=board, grade=grade, subject=subject,
                            title=_s(title, 240) or f"{subject} - Class {grade}", duration_min=bp["duration_min"],
                            max_marks=bp["max_marks"], blueprint=_d(bp), items=_d(items), gaps=_d(gaps),
                            instructions=_d(_instructions(bp)))
        s.add(p)
        s.flush()
        view = _paper_view(p)
    S.mark_used(tenant, [i["question_id"] for i in items], num)
    say = (f"{num} made: {len(items)} questions, {total}/{bp['max_marks']} marks." +
           (f" {len(gaps)} sections are short of questions ({', '.join(g['section'] for g in gaps)}): the bank needs more approved questions, "
            "or use fill_missing." if gaps else "") +
           (f" {drafts} questions are still drafts: read them before you approve." if drafts else "") +
           (f" {generated} new questions written." if generated else ""))
    _publish(tenant, "pathyakram_paper", {"paper": view, "say": say}, conv)
    return {"paper": view, "say": say, "disclaimer": R.DISCLAIMER}


def _instructions(bp: dict) -> list[str]:
    secs = bp["sections"]
    out = [f"This paper has {len(secs)} sections: " + ", ".join(f"{s['name']} ({s['count']} x {s['marks_each']:g})" for s in secs) + ".",
           "All questions are compulsory; where a choice is given, attempt one."]
    if bp.get("duration_min"):
        out.insert(0, f"Samay: {bp['duration_min']} minute. Poorna ank: {bp['max_marks']:g}.")
    return out


def _paper_row(s, tenant: str, ref: str) -> PathyakramPaper:
    ref = _s(ref, 40)
    p = s.scalars(select(PathyakramPaper).where(PathyakramPaper.tenant_id == tenant,
                                                (PathyakramPaper.id == ref) | (PathyakramPaper.number == ref))).first()
    if p is None:
        raise PathyakramError(f"Paper '{ref}' not found.")
    return p


def _paper_view(p: PathyakramPaper) -> dict:
    items = _j(p.items, [])
    return {"id": p.id, "number": p.number, "title": p.title, "board": p.board, "grade": p.grade, "subject": p.subject,
            "duration_min": p.duration_min, "max_marks": p.max_marks, "questions": len(items),
            "total": round(sum(i["marks"] for i in items if not i.get("choice")), 2),
            "drafts": sum(1 for i in items if i.get("status") != "approved"), "gaps": _j(p.gaps, []), "status": p.status,
            "blueprint": {k: v for k, v in _j(p.blueprint, {}).items() if k in ("source", "verified", "session", "say", "sections")},
            "approved_by": p.approved_by, "created_at": p.created_at}


def paper(tenant: str, ref: str, key: bool = False) -> dict:
    with session() as s:
        p = _paper_row(s, tenant, ref)
        view = _paper_view(p)
        items = _j(p.items, [])
        qs = {x.id: x for x in s.scalars(select(ShikshaQuestion).where(
            ShikshaQuestion.id.in_([i["question_id"] for i in items]))).all()}
        secs: dict[str, list] = {}
        for i in items:
            x = qs.get(i["question_id"])
            if x is None:
                continue
            row = {"n": i["n"], "number": x.number, "qtype": x.qtype, "marks": x.marks, "text": x.text,
                   "options": _j(x.options, []), "choice": bool(i.get("choice")), "status": x.status}
            if key:
                row.update(answer=x.answer, steps=_j(x.steps, []), scheme=_j(x.scheme, []))
            secs.setdefault(i["section"], []).append(row)
        view["sections"] = [{"name": k, "questions": v} for k, v in secs.items()]
        view["instructions"] = _j(p.instructions, [])
    # internal choice: the extra question in a section is shown as an OR of the one before it
    return view


def papers(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(PathyakramPaper).where(PathyakramPaper.tenant_id == tenant)
        if status:
            q = q.where(PathyakramPaper.status == status)
        return [_paper_view(p) for p in s.scalars(q.order_by(PathyakramPaper.created_at.desc())).all()[:100]]


def swap(tenant: str, ref: str, n: int, question_ref: str = "", actor: str = "owner") -> dict:
    """Replace question n of a paper: with the one she names, or the next best from the bank (same type and marks)."""
    _team(actor)
    with _LOCK, session() as s:
        p = _paper_row(s, tenant, ref)
        if p.status == "shared":
            raise PathyakramError("This paper has already been shared; make a new paper.")
        items = _j(p.items, [])
        it = next((i for i in items if i["n"] == int(n)), None)
        if it is None:
            raise PathyakramError(f"The paper has no question {n}.")
        old = s.get(ShikshaQuestion, it["question_id"])
        board, grade, subject, num = p.board, p.grade, p.subject, p.number
    taken = {i["question_id"] for i in items}
    if question_ref:
        with session() as s:
            new = S._q_row(s, tenant, question_ref)
            s.expunge(new)
        if new.qtype != old.qtype or abs(new.marks - old.marks) > 0.01:
            raise PathyakramError(f"{new.number}: its type / marks ({new.qtype}, {new.marks:g}) differ from the old question.")
        if new.id in taken:
            raise PathyakramError(f"{new.number} is already in this paper.")
    else:
        got = _pick(_candidates(tenant, board, grade, subject, old.qtype, old.marks, [], True), 1, taken)
        if not got:
            raise PathyakramError("The bank has no other approved question of this type / marks.")
        new = got[0]
    with _LOCK, session() as s:
        p = _paper_row(s, tenant, ref)
        items = _j(p.items, [])
        for i in items:
            if i["n"] == int(n):
                i.update(question_id=new.id, number=new.number, marks=new.marks, status=new.status)
        p.items, p.updated_at = _d(items), now()
        if p.status == "approved":
            p.status, p.approved_by = "draft", ""
        view = _paper_view(p)
    S.mark_used(tenant, [new.id], num)
    return {"paper": view, "say": f"{num}: question {n} is now {new.number}."}


def approve_paper(tenant: str, ref: str, actor: str = "owner") -> dict:
    """A teacher's approval: only a paper whose every question is approved and whose marks add up."""
    _team(actor)
    with _LOCK, session() as s:
        p = _paper_row(s, tenant, ref)
        items = _j(p.items, [])
        status = {x.id: x.status for x in s.scalars(select(ShikshaQuestion).where(
            ShikshaQuestion.id.in_([i["question_id"] for i in items]))).all()}
        drafts = [i["number"] for i in items if status.get(i["question_id"]) != "approved"]
        if drafts:
            raise PathyakramError("Approve these questions first: " + ", ".join(drafts[:20]))
        total = round(sum(i["marks"] for i in items if not i.get("choice")), 2)
        if abs(total - p.max_marks) > 0.01:
            raise PathyakramError(f"Marks {total}, but the paper is for {p.max_marks:g}; fill the gaps.")
        for i in items:
            i["status"] = "approved"
        p.items, p.status, p.approved_by, p.updated_at = _d(items), "approved", actor or "owner", now()
        return {"paper": _paper_view(p), "say": f"{p.number} approved."}


def _paper_text(view: dict, key: bool) -> str:
    lines = [f"**Class:** {view['grade']}   **Subject:** {view['subject']}   **Board:** {view['board']}",
             f"**Time:** {view['duration_min']} min   **Maximum marks:** {view['max_marks']:g}" if view["duration_min"] else
             f"**Maximum marks:** {view['max_marks']:g}", ""]
    if not key:
        lines += ["## General instructions"] + [f"- {x}" for x in view.get("instructions", [])]
    for sec in view["sections"]:
        lines.append(f"## Section {sec['name']}")
        for q in sec["questions"]:
            head = f"**Q{q['n']}.** " if not q["choice"] else "**OR** "
            lines.append(f"{head}{q['text']}  ({q['marks']:g} mark{'s' if q['marks'] != 1 else ''})")
            for i, o in enumerate(q.get("options") or []):
                lines.append(f"({'abcd'[i] if i < 4 else i + 1}) {o}")
            if key:
                lines.append(f"**Answer:** {q.get('answer') or '-'}")
                for st in q.get("steps") or []:
                    lines.append(f"- {st}")
                if q.get("scheme"):
                    lines.append("| Marking point | Marks |")
                    lines.append("|---|---|")
                    for sc in q["scheme"]:
                        lines.append(f"| {sc['point']} | {sc['marks']:g} |")
            lines.append("")
    return "\n".join(lines)


def paper_file(tenant: str, ref: str, key: bool = False, conv: str = "") -> dict:
    from ..officegen import make_docx
    view = paper(tenant, ref, key=key)
    title = f"{view['title']} ({view['number']})" + (" - Answer key & marking scheme" if key else "")
    data = make_docx(title, _paper_text(view, key))
    f = _store(tenant, f"{view['number']}{'_key' if key else ''}.docx", data,
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document", conv, title)
    return {"file": f, "paper": view["number"], "key": key}


# ---------------------------------------------------------------- year plan (deterministic: no invented chapters)
def year_plan(tenant: str, subject: str, grade: str, board: str = "", chapters: list[str] | None = None,
              weights: list[float] | None = None, start_month: str = "April", months: int = 10, revision_months: int = 1,
              periods_per_week: int = 6, actor: str = "owner", conv: str = "") -> dict:
    _team(actor)
    board, grade, subject = _ctx_defaults(tenant, board, grade, subject)
    src, verified = "teacher", True
    chs = [_s(c, 200) for c in (chapters or []) if _s(c, 200)]
    if not chs:
        lib = R.chapters(subject, grade)
        if not lib:
            raise PathyakramError("This class / subject has no chapters in the library; give the chapter list (in order).")
        chs, src, verified = lib["chapters"], lib["source"], lib["verified"]
    months = max(2, min(int(months or 10), 12))
    rev = max(0, min(int(revision_months or 0), months - 1))
    teach = months - rev
    w = [float(x) for x in (weights or [])][:len(chs)]
    w += [1.0] * (len(chs) - len(w))
    tot = sum(w) or 1.0
    try:
        m0 = [m.lower() for m in MONTHS].index(_s(start_month, 12).lower())
    except ValueError:
        m0 = 3
    names = [MONTHS[(m0 + i) % 12] for i in range(months)]
    rows = [{"month": names[i], "chapters": [], "periods": periods_per_week * 4, "assessment": ""} for i in range(months)]
    acc = 0.0
    for ch, wt in zip(chs, w):
        mid = acc + wt / 2
        idx = min(teach - 1, int(mid / tot * teach))
        rows[idx]["chapters"].append(ch)
        acc += wt
    for i in range(teach, months):
        rows[i]["chapters"] = ["Revision + practice papers"]
    for i, r in enumerate(rows):
        if i == teach - 1:
            r["assessment"] = "Final syllabus complete - prepare for the pre-board / annual exam"
        elif i < teach and (i + 1) % 3 == 0:
            r["assessment"] = "Periodic test (last 3 months)"
    if teach >= 6:
        rows[teach // 2]["assessment"] = rows[teach // 2]["assessment"] or "Half-yearly exam"
    body = {"rows": rows, "chapters": chs, "weights": w, "source": src, "verified": verified,
            "periods_per_week": periods_per_week, "note": "Assessments are suggestions: match them with the school calendar."}
    return _save_plan(tenant, "year", board, grade, subject, f"{subject} year plan - Class {grade}", body, conv)


def _save_plan(tenant: str, kind: str, board: str, grade: str, subject: str, title: str, body: dict, conv: str) -> dict:
    pre = {"year": "YP", "lesson": "LP", "rubric": "RB"}[kind]
    with _LOCK, session() as s:
        n = S.next_no(s, tenant, f"plan_{kind}")
        p = PathyakramPlan(tenant_id=tenant, number=f"{pre}-{n:03d}", kind=kind, board=board, grade=grade, subject=subject,
                           title=_s(title, 240), body=_d(body))
        s.add(p)
        s.flush()
        view = _plan_view(p)
    say = f"{view['number']} ({kind} plan) draft ready; the teacher reads and approves it."
    _publish(tenant, "pathyakram_plan", {"plan": {k: view[k] for k in ("id", "number", "kind", "title", "status")}, "say": say}, conv)
    return {"plan": view, "say": say, "disclaimer": R.DISCLAIMER}


def _plan_view(p: PathyakramPlan) -> dict:
    return {"id": p.id, "number": p.number, "kind": p.kind, "board": p.board, "grade": p.grade, "subject": p.subject,
            "title": p.title, "body": _j(p.body, {}), "status": p.status, "approved_by": p.approved_by,
            "created_at": p.created_at}


def _plan_row(s, tenant: str, ref: str) -> PathyakramPlan:
    ref = _s(ref, 40)
    p = s.scalars(select(PathyakramPlan).where(PathyakramPlan.tenant_id == tenant,
                                               (PathyakramPlan.id == ref) | (PathyakramPlan.number == ref))).first()
    if p is None:
        raise PathyakramError(f"Plan '{ref}' not found.")
    return p


def plans(tenant: str, kind: str = "") -> list[dict]:
    with session() as s:
        q = select(PathyakramPlan).where(PathyakramPlan.tenant_id == tenant)
        if kind:
            q = q.where(PathyakramPlan.kind == kind)
        return [{k: v for k, v in _plan_view(p).items() if k != "body"} for p in
                s.scalars(q.order_by(PathyakramPlan.created_at.desc())).all()[:100]]


def plan(tenant: str, ref: str) -> dict:
    with session() as s:
        return _plan_view(_plan_row(s, tenant, ref))


def approve_plan(tenant: str, ref: str, actor: str = "owner") -> dict:
    _team(actor)
    with _LOCK, session() as s:
        p = _plan_row(s, tenant, ref)
        p.status, p.approved_by, p.updated_at = "approved", actor or "owner", now()
        return {"plan": _plan_view(p), "say": f"{p.number} approved."}


# ---------------------------------------------------------------- lesson plan (5E) + rubric
PHASES = ["engage", "explore", "explain", "elaborate", "evaluate"]
LESSON_SYSTEM = """You plan one lesson for an Indian classroom teacher using the 5E model (engage, explore, explain,
elaborate, evaluate). Practical, low-cost activities that fit a real class of 30-45 students. No invented board facts.
Output JSON: {"objectives":[],"materials":[],"steps":[{"phase","minutes","teacher","students"}],
"check_questions":[],"homework":"","differentiation":{"support":"","stretch":""},"vocabulary":[]}."""


def lesson_plan(tenant: str, subject: str, grade: str, topic: str, board: str = "", minutes: int = 40, periods: int = 1,
                language: str = "", notes: str = "", actor: str = "owner", conv: str = "") -> dict:
    _team(actor)
    board, grade, subject = _ctx_defaults(tenant, board, grade, subject)
    topic = _s(topic, 200)
    if not topic:
        raise PathyakramError("A lesson topic is needed.")
    total = max(20, min(int(minutes or 40), 120)) * max(1, min(int(periods or 1), 6))
    language = _s(language, 20) or S.settings(tenant)["medium"] or "English"
    out = _model_json(LESSON_SYSTEM, f"Board {board}, class {grade}, {subject}. Topic: {topic}. Total time: {total} minutes "
                                     f"({periods} period(s)). Language: {language}."
                                     + (f" Teacher's notes (data): {_s(notes, 500)}" if notes else ""), 4000)
    steps = []
    for st in out.get("steps") or []:
        if isinstance(st, dict) and _s(st.get("phase"), 12).lower() in PHASES:
            steps.append({"phase": _s(st["phase"], 12).lower(), "minutes": max(1, int(float(st.get("minutes") or 1))),
                          "teacher": _s(st.get("teacher"), 900), "students": _s(st.get("students"), 900)})
    if not steps or {x["phase"] for x in steps} != set(PHASES):
        missing = sorted(set(PHASES) - {x["phase"] for x in steps})
        raise PathyakramError("The model's plan was incomplete (5E phases missing: " + ", ".join(missing or ["all"]) + "); try again.")
    got = sum(x["minutes"] for x in steps)                 # minutes always add up to the class time, in code
    if got != total:
        for x in steps:
            x["minutes"] = max(1, round(x["minutes"] * total / got))
        steps[-1]["minutes"] += total - sum(x["minutes"] for x in steps)
    body = {"topic": topic, "minutes": total, "periods": periods, "language": language,
            "objectives": [_s(x, 300) for x in out.get("objectives") or []][:8],
            "materials": [_s(x, 200) for x in out.get("materials") or []][:15], "steps": steps,
            "check_questions": [_s(x, 400) for x in out.get("check_questions") or []][:10],
            "homework": _s(out.get("homework"), 800), "vocabulary": [_s(x, 80) for x in out.get("vocabulary") or []][:20],
            "differentiation": {k: _s((out.get("differentiation") or {}).get(k), 600) for k in ("support", "stretch")}}
    return _save_plan(tenant, "lesson", board, grade, subject, f"Lesson plan: {topic} (Class {grade})", body, conv)


RUBRIC_SYSTEM = """You write an analytic rubric for a teacher. Each criterion has the SAME number of performance levels,
ordered best first, each with a clear observable descriptor (no vague words like 'good' alone). Output JSON:
{"criteria":[{"name","points","levels":[{"label","points","descriptor"}]}]}."""


def rubric(tenant: str, task: str, subject: str, grade: str, board: str = "", criteria: list[str] | None = None,
           levels: int = 4, total_points: float = 20, actor: str = "owner", conv: str = "") -> dict:
    _team(actor)
    board, grade, subject = _ctx_defaults(tenant, board, grade, subject)
    task = _s(task, 600)
    if not task:
        raise PathyakramError("A rubric for which task (project, essay, presentation...)?")
    levels = max(2, min(int(levels or 4), 6))
    total_points = max(1.0, float(total_points or 20))
    out = _model_json(RUBRIC_SYSTEM, f"Task: {task}. Class {grade} {subject} ({board}). {levels} levels per criterion. "
                                     f"Total {total_points:g} points." + (f" Criteria: {', '.join(_s(c, 80) for c in criteria)}." if criteria else ""), 4000)
    crit = []
    for c in out.get("criteria") or []:
        if not isinstance(c, dict) or not _s(c.get("name"), 120):
            continue
        lv = [x for x in c.get("levels") or [] if isinstance(x, dict) and _s(x.get("descriptor"), 600)]
        if len(lv) != levels:
            continue
        crit.append({"name": _s(c["name"], 120), "points": float(c.get("points") or 0),
                     "levels": [{"label": _s(x.get("label"), 40) or f"Level {i + 1}", "descriptor": _s(x.get("descriptor"), 600),
                                 "share": levels - i} for i, x in enumerate(lv)]})
    if len(crit) < 2:
        raise PathyakramError("The model's rubric was incomplete; try again.")
    # points in code: criteria shares rescaled to the total; each level = the criterion's points x share / levels
    raw = [c["points"] if c["points"] > 0 else 1.0 for c in crit]
    scale = total_points / sum(raw)
    for c, r in zip(crit, raw):
        c["points"] = round(r * scale * 2) / 2
    crit[-1]["points"] = round((crit[-1]["points"] + total_points - sum(c["points"] for c in crit)) * 2) / 2
    for c in crit:
        for x in c["levels"]:
            x["points"] = round(c["points"] * x.pop("share") / levels * 2) / 2
    body = {"task": task, "levels": levels, "total_points": total_points, "criteria": crit}
    return _save_plan(tenant, "rubric", board, grade, subject, f"Rubric: {task[:80]}", body, conv)


def _plan_text(view: dict) -> str:
    b = view["body"]
    lines = [f"**Board:** {view['board']}   **Class:** {view['grade']}   **Subject:** {view['subject']}", ""]
    if view["kind"] == "year":
        lines += ["| Month | Chapters | Periods | Assessment |", "|---|---|---|---|"]
        lines += [f"| {r['month']} | {'; '.join(r['chapters']) or '-'} | {r['periods']} | {r['assessment'] or '-'} |" for r in b["rows"]]
        lines += ["", f"Source: {b.get('source') or 'teacher'}", b.get("note", "")]
    elif view["kind"] == "lesson":
        lines += [f"**Topic:** {b['topic']}   **Time:** {b['minutes']} min", "## Objectives"] + [f"- {x}" for x in b["objectives"]]
        lines += ["## Materials"] + [f"- {x}" for x in b["materials"]]
        lines += ["## Steps", "| Phase | Min | Teacher | Students |", "|---|---|---|---|"]
        lines += [f"| {x['phase'].title()} | {x['minutes']} | {x['teacher']} | {x['students']} |" for x in b["steps"]]
        lines += ["## Check questions"] + [f"- {x}" for x in b["check_questions"]]
        lines += ["## Homework", b["homework"] or "-", "## Support / stretch",
                  f"- Support: {b['differentiation']['support']}", f"- Stretch: {b['differentiation']['stretch']}"]
    else:
        lines += [f"**Task:** {b['task']}   **Total:** {b['total_points']:g} points", ""]
        head = [x["label"] for x in b["criteria"][0]["levels"]]
        lines += ["| Criterion (points) | " + " | ".join(head) + " |", "|" + "---|" * (len(head) + 1)]
        for c in b["criteria"]:
            lines.append(f"| {c['name']} ({c['points']:g}) | " + " | ".join(f"{x['descriptor']} ({x['points']:g})" for x in c["levels"]) + " |")
    return "\n".join(lines)


def plan_file(tenant: str, ref: str, conv: str = "") -> dict:
    from ..officegen import make_docx
    view = plan(tenant, ref)
    data = make_docx(f"{view['title']} ({view['number']})", _plan_text(view))
    f = _store(tenant, f"{view['number']}.docx", data,
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document", conv, view["title"])
    return {"file": f, "plan": view["number"]}


# ---------------------------------------------------------------- going outside: only her tap
def _hash(show: dict) -> str:
    return hashlib.sha256(json.dumps(show, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _share_show(tenant: str, x: PathyakramShare) -> dict:
    content = paper(tenant, x.ref_id, key=x.with_key == "yes") if x.what == "paper" else plan(tenant, x.ref_id)
    content.pop("created_at", None)
    return {"what": x.what, "ref": x.ref_id, "via": x.via, "to": x.to_name, "contact": x.to_contact, "key": x.with_key,
            "content": hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()}


def _share_view(x: PathyakramShare) -> dict:
    return {"id": x.id, "number": x.number, "what": x.what, "ref_id": x.ref_id, "via": x.via, "to_name": x.to_name,
            "to_contact": x.to_contact, "with_key": x.with_key == "yes", "note": x.note, "hash": x.hash, "status": x.status,
            "result": _j(x.result, {}), "created_at": x.created_at, "decided_at": x.decided_at}


def share_request(tenant: str, what: str, ref: str, via: str = "file", to_name: str = "", to_contact: str = "",
                  with_key: bool = False, note: str = "", actor: str = "owner", conv: str = "") -> dict:
    _team(actor)
    what = "plan" if what == "plan" else "paper"
    via = via if via in ("file", "form", "whatsapp", "email") else "file"
    with session() as s:
        row = _paper_row(s, tenant, ref) if what == "paper" else _plan_row(s, tenant, ref)
        if row.status not in ("approved", "shared"):
            raise PathyakramError(f"{row.number} is not approved by the teacher yet; approve it first.")
        rid, rnum, title = row.id, row.number, row.title
    if via == "form" and what != "paper":
        raise PathyakramError("A Google Form quiz can be made only from a paper.")
    if via in ("whatsapp", "email") and not _s(to_contact, 160):
        raise PathyakramError("Who is it for: a phone / email is needed.")
    with _LOCK, session() as s:
        for old in s.scalars(select(PathyakramShare).where(PathyakramShare.tenant_id == tenant, PathyakramShare.ref_id == rid,
                                                           PathyakramShare.status == "waiting")).all():
            old.status = "stale"
        n = S.next_no(s, tenant, "share")
        x = PathyakramShare(tenant_id=tenant, number=f"SH-{n:03d}", what=what, ref_id=rid, via=via, to_name=_s(to_name, 160),
                            to_contact=_s(to_contact, 160), with_key="yes" if with_key else "no", note=_s(note, 500))
        s.add(x)
        s.flush()
        x.hash = _hash(_share_show(tenant, x))
        view = _share_view(x)
    say = (f"{view['number']}: {rnum} ({title[:60]}) " + {"file": "as a file", "form": "as a Google Form quiz",
           "whatsapp": f"WhatsApp draft for {view['to_name'] or view['to_contact']}", "email": f"email draft for {view['to_contact']}"}[via]
           + (" with the answer key" if with_key else "") + " - nothing happens without your tap.")
    _publish(tenant, "pathyakram_share", {"share": view, "title": title, "number": rnum, "say": say}, conv)
    return {"share": view, "status": "needs_tap", "say": say}


def _wa(phone: str, text: str) -> str:
    d = re.sub(r"\D", "", str(phone or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    q = urllib.parse.quote(text)
    return f"https://wa.me/91{d}?text={q}" if len(d) == 10 else f"https://wa.me/?text={q}"


def _form_questions(view: dict) -> tuple[list[dict], list[str]]:
    """Objective questions become graded Google Form items; the rest are listed as left out (never silently)."""
    out, left = [], []
    for sec in view["sections"]:
        for q in sec["questions"]:
            if q["choice"]:
                left.append(f"Q{q['n']} (OR choice)")
                continue
            if q["qtype"] in ("mcq", "assertion_reason", "true_false") and q.get("options"):
                out.append({"title": f"Q{q['n']}. {q['text']}"[:500], "type": "choice", "options": q["options"],
                            "correct": q.get("answer"), "points": max(1, int(round(q["marks"]))), "required": True})
            elif q["qtype"] in ("fill_blank", "numeric") and q.get("answer"):
                out.append({"title": f"Q{q['n']}. {q['text']}"[:500], "type": "short", "correct": q["answer"],
                            "points": max(1, int(round(q["marks"]))), "required": True})
            else:
                left.append(f"Q{q['n']} ({R.QTYPES.get(q['qtype'], q['qtype'])})")
    return out, left


def decide_share(tenant: str, share_id: str, yes: bool, card_hash: str = "", by_tap: bool = False, conv: str = "") -> dict:
    if not by_tap:
        raise PathyakramError("Approval to send a paper / plan outside comes only from your tap in the app.")
    with _LOCK, session() as s:
        x = s.get(PathyakramShare, share_id)
        if x is None or x.tenant_id != tenant:
            raise PathyakramError("Card not found.")
        if x.status != "waiting":
            return {"share": _share_view(x), "say": f"{x.number} is already '{x.status}'."}
    stale = not card_hash or card_hash != x.hash or _hash(_share_show(tenant, x)) != x.hash
    if stale:                                       # saved before refusing
        with _LOCK, session() as s:
            s.get(PathyakramShare, share_id).status = "stale"
        raise PathyakramError("The paper / plan or the card has changed; make a new card.")
    if not yes:
        with _LOCK, session() as s:
            y = s.get(PathyakramShare, share_id)
            y.status, y.decided_at = "rejected", now()
            return {"share": _share_view(y), "say": f"{y.number}: not sent."}
    result: dict[str, Any] = {}
    if x.what == "paper":
        result["paper_file"] = paper_file(tenant, x.ref_id, False, conv)["file"]
        if x.with_key == "yes":
            result["key_file"] = paper_file(tenant, x.ref_id, True, conv)["file"]
    else:
        result["plan_file"] = plan_file(tenant, x.ref_id, conv)["file"]
    say = f"{x.number}: file ready."
    if x.via == "form":
        view = paper(tenant, x.ref_id, key=True)
        qs, left = _form_questions(view)
        if not qs:
            raise PathyakramError("This paper has no objective question that can go into a Google Form quiz.")
        from ..forms import service as F
        try:
            form = F.create(tenant, conv, f"{view['title']} ({view['number']})", qs, description="; ".join(view["instructions"])[:3000],
                            quiz=True)
        except Exception as e:
            raise PathyakramError(f"Google Form could not be made: {e}")
        result.update(form={k: form.get(k) for k in ("id", "title", "responder_link", "edit_link")}, left_out=left)
        say = f"{x.number}: Google Form quiz made ({len(qs)} questions)." + (f" Not put in the form: {', '.join(left[:8])}." if left else "")
    elif x.via in ("whatsapp", "email"):
        text = f"Hello {x.to_name}, the {('paper' if x.what == 'paper' else 'plan')} file is attached. {x.note}".strip()
        result["links"] = {"whatsapp": _wa(x.to_contact, text)} if x.via == "whatsapp" else {
            "email": f"mailto:{urllib.parse.quote(x.to_contact)}?subject={urllib.parse.quote('File')}&body={urllib.parse.quote(text)}"}
        say = f"{x.number}: file + message draft ready; send the file yourself (Hoola does not send it)."
    with _LOCK, session() as s:
        y = s.get(PathyakramShare, share_id)
        y.status, y.decided_at, y.result = "shared", now(), _d(result)
        if x.what == "paper":
            p = s.get(PathyakramPaper, x.ref_id)
            if p:
                p.status = "shared"
        view = _share_view(y)
    _publish(tenant, "pathyakram_share", {"share": view, "say": say}, conv)
    return {"share": view, "say": say, **result}


def shares(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(PathyakramShare).where(PathyakramShare.tenant_id == tenant)
        if status:
            q = q.where(PathyakramShare.status == status)
        return [_share_view(x) for x in s.scalars(q.order_by(PathyakramShare.created_at.desc())).all()[:100]]


def day(tenant: str) -> dict:
    base = S.day(tenant)
    waiting = shares(tenant, "waiting")
    ps = papers(tenant)
    lines = [base["say"]] if base.get("drafts") or base.get("consent_pending") else []
    if waiting:
        lines.append(f"{len(waiting)} cards to send a paper / plan are waiting for your tap.")
    if ps:
        lines.append(f"Latest paper {ps[0]['number']} ({ps[0]['status']}).")
    return {**base, "papers": ps[:10], "waiting": waiting, "plans": plans(tenant)[:10],
            "say": " ".join(lines) or base["say"]}


def tick(now_=None) -> None:
    """Nothing time-based (papers and plans are made when she asks); kept so the worker wiring is uniform."""
    return None
