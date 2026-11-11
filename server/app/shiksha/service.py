"""Shiksha suite foundation service: her institution settings, classes, learners (guardian consent for children, DPDP
Act 2023 s.9), the shared question bank and the gradebook. Every education employee builds on these."""
from __future__ import annotations

import json
import logging
import re
import threading
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import rules as R
from .models import ShikshaClass, ShikshaLearner, ShikshaMark, ShikshaQuestion, ShikshaSettings

log = logging.getLogger("santosh.shiksha")
_LOCK = threading.RLock()


class ShikshaError(Exception):
    pass


def _j(v, default):
    try:
        x = json.loads(v) if isinstance(v, str) and v else default
        return x if isinstance(x, type(default)) else default
    except (ValueError, TypeError):
        return default


def _d(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def _s(v, n: int = 400) -> str:
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip()[:n]


def is_owner(actor: str) -> bool:
    a = actor or "owner"
    return a == "owner" or a.startswith("approved:")


def _need_team(actor: str) -> None:
    if (actor or "").startswith("customer:"):
        raise ShikshaError("This is school / teacher work; it is not for a customer or an outsider.")


def _st(s, tenant: str) -> ShikshaSettings:
    r = s.get(ShikshaSettings, tenant)
    if r is None:
        r = ShikshaSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def next_no(s, tenant: str, key: str) -> int:
    st = _st(s, tenant)
    seq = _j(st.seq, {})
    seq[key] = int(seq.get(key) or 0) + 1
    st.seq = _d(seq)
    return seq[key]


def _phone(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if d and len(d) != 10:
        raise ShikshaError("The guardian's phone must have 10 digits.")
    return d


def _email(v) -> str:
    e = _s(v, 160).lower()
    if e and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", e):
        raise ShikshaError("The guardian's email does not look right.")
    return e


# ---------------------------------------------------------------- settings
SET_KEYS = ("institution", "kind", "board", "medium", "academic_year", "city")


def settings(tenant: str) -> dict:
    with session() as s:
        st = _st(s, tenant)
        return {k: getattr(st, k) for k in SET_KEYS}


def save_settings(tenant: str, actor: str = "owner", **k) -> dict:
    if not is_owner(actor):
        raise ShikshaError("Only the owner can change the settings.")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        for key in SET_KEYS:
            if key in k and k[key] is not None:
                v = _s(k[key], 200)
                if key == "board":
                    v = v.upper().replace(" ", "_")
                    if v not in R.BOARDS:
                        raise ShikshaError(f"board: {', '.join(R.BOARDS)}")
                if key == "kind" and v not in ("school", "coaching", "tutor", "college", "university"):
                    raise ShikshaError("kind: school | coaching | tutor | college | university")
                setattr(st, key, v)
        return {k: getattr(st, k) for k in SET_KEYS}


# ---------------------------------------------------------------- classes
def _class_view(c: ShikshaClass, learners: int | None = None) -> dict:
    out = {"id": c.id, "number": c.number, "name": c.name, "grade": c.grade, "board": c.board, "section": c.section,
           "subjects": _j(c.subjects, []), "teacher": c.teacher, "year": c.year, "status": c.status}
    if learners is not None:
        out["learners"] = learners
    return out


def _class_row(s, tenant: str, ref: str) -> ShikshaClass:
    ref = _s(ref, 80)
    for c in s.scalars(select(ShikshaClass).where(ShikshaClass.tenant_id == tenant)).all():
        if ref in (c.id, c.number) or ref.lower() == c.name.lower():
            return c
    raise ShikshaError(f"Class '{ref}' not found.")


def add_class(tenant: str, name: str, grade: str = "", board: str = "", subjects: list[str] | None = None, section: str = "",
              teacher: str = "", year: str = "", actor: str = "owner") -> dict:
    _need_team(actor)
    name = _s(name, 80)
    if not name:
        raise ShikshaError("The class needs a name (for example '10-A').")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        board = (_s(board, 20) or st.board or "CBSE").upper()
        if board not in R.BOARDS:
            raise ShikshaError(f"board: {', '.join(R.BOARDS)}")
        if s.scalars(select(ShikshaClass).where(ShikshaClass.tenant_id == tenant, ShikshaClass.name == name,
                                                ShikshaClass.status == "active")).first():
            raise ShikshaError(f"Class '{name}' already exists.")
        g = R._grade_key(grade) or R._grade_key(re.match(r"\s*(\d{1,2})", name).group(1) if re.match(r"\s*\d{1,2}", name) else "")
        c = ShikshaClass(tenant_id=tenant, number=f"C-{next_no(s, tenant, 'class'):02d}", name=name, grade=g, board=board,
                         section=_s(section, 20), subjects=_d([_s(x, 80) for x in (subjects or []) if _s(x, 80)][:20]),
                         teacher=_s(teacher, 120), year=_s(year, 12) or st.academic_year)
        s.add(c)
        s.flush()
        return _class_view(c, 0)


def classes(tenant: str, status: str = "active") -> list[dict]:
    with session() as s:
        rows = s.scalars(select(ShikshaClass).where(ShikshaClass.tenant_id == tenant)
                         .order_by(ShikshaClass.created_at)).all()
        out = []
        for c in rows:
            if status and c.status != status:
                continue
            n = len(s.scalars(select(ShikshaLearner.id).where(ShikshaLearner.class_id == c.id,
                                                              ShikshaLearner.status == "active")).all())
            out.append(_class_view(c, n))
        return out


def update_class(tenant: str, ref: str, actor: str = "owner", **k) -> dict:
    _need_team(actor)
    with _LOCK, session() as s:
        c = _class_row(s, tenant, ref)
        for key in ("name", "grade", "section", "teacher", "year"):
            if k.get(key) is not None:
                setattr(c, key, R._grade_key(k[key]) if key == "grade" else _s(k[key], 120))
        if k.get("subjects") is not None:
            c.subjects = _d([_s(x, 80) for x in k["subjects"] if _s(x, 80)][:20])
        if k.get("status") in ("active", "archived"):
            if not is_owner(actor):
                raise ShikshaError("Only the owner can archive a class.")
            c.status = k["status"]
        return _class_view(c)


# ---------------------------------------------------------------- learners (children's data under DPDP s.9)
def _learner_view(x: ShikshaLearner, cls: ShikshaClass | None = None, full: bool = False) -> dict:
    child = R.is_child(x.birth_year, x.adult, cls.grade if cls else "")
    out = {"id": x.id, "number": x.number, "name": x.name, "class": cls.name if cls else "", "class_id": x.class_id,
           "roll": x.roll, "child": child, "consent": x.consent if child else "not_needed", "status": x.status,
           "usable": (not child) or x.consent == "given", "language": x.language}
    if full:
        out.update(birth_year=x.birth_year or None, guardian_name=x.guardian_name, guardian_relation=x.guardian_relation,
                   guardian_phone=x.guardian_phone, guardian_email=x.guardian_email, consent_log=_j(x.consent_log, []))
    return out


def _learner_row(s, tenant: str, ref: str) -> ShikshaLearner:
    ref = _s(ref, 120)
    rows = s.scalars(select(ShikshaLearner).where(ShikshaLearner.tenant_id == tenant, ShikshaLearner.status != "forgotten")).all()
    for x in rows:
        if ref in (x.id, x.number):
            return x
    hits = [x for x in rows if x.name.lower() == ref.lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ShikshaError(f"There are {len(hits)} learners named '{ref}'; give the number (S-xxxx).")
    raise ShikshaError(f"Learner '{ref}' not found.")


def add_learner(tenant: str, name: str, class_ref: str = "", roll: str = "", birth_year: int | None = None,
                adult: bool = False, guardian_name: str = "", guardian_relation: str = "", guardian_phone: str = "",
                guardian_email: str = "", language: str = "", actor: str = "owner") -> dict:
    _need_team(actor)
    name = _s(name, 120)
    if not name:
        raise ShikshaError("The child's / learner's name is needed.")
    by = int(birth_year or 0)
    if by and not (1930 <= by <= now().year):
        raise ShikshaError("The year of birth is not right.")
    with _LOCK, session() as s:
        cls = _class_row(s, tenant, class_ref) if class_ref else None
        child = R.is_child(by, adult, cls.grade if cls else "")
        if child and not (guardian_name and (guardian_phone or guardian_email)):
            raise ShikshaError("Under 18: the guardian's name and phone / email are needed (DPDP Act: a child's details "
                               "only with the guardian's consent).")
        x = ShikshaLearner(tenant_id=tenant, number=f"S-{next_no(s, tenant, 'learner'):04d}", name=name,
                           class_id=cls.id if cls else "", roll=_s(roll, 20), birth_year=by, adult=bool(adult),
                           guardian_name=_s(guardian_name, 120), guardian_relation=_s(guardian_relation, 30),
                           guardian_phone=_phone(guardian_phone), guardian_email=_email(guardian_email), language=_s(language, 20))
        s.add(x)
        s.flush()
        v = _learner_view(x, cls, True)
    v["say"] = (f"{v['number']} {v['name']} added. This is a child: until the guardian's consent is recorded, no study / marks "
                "work will be done for them." if v["child"] else f"{v['number']} {v['name']} added.")
    return v


def learners(tenant: str, class_ref: str = "") -> list[dict]:
    with session() as s:
        cls_by = {c.id: c for c in s.scalars(select(ShikshaClass).where(ShikshaClass.tenant_id == tenant)).all()}
        q = select(ShikshaLearner).where(ShikshaLearner.tenant_id == tenant, ShikshaLearner.status == "active")
        if class_ref:
            q = q.where(ShikshaLearner.class_id == _class_row(s, tenant, class_ref).id)
        return [_learner_view(x, cls_by.get(x.class_id)) for x in s.scalars(q.order_by(ShikshaLearner.number)).all()]


def learner(tenant: str, ref: str) -> dict:
    with session() as s:
        x = _learner_row(s, tenant, ref)
        return _learner_view(x, s.get(ShikshaClass, x.class_id) if x.class_id else None, True)


def record_consent(tenant: str, ref: str, given: bool, method: str = "", note: str = "", actor: str = "owner") -> dict:
    """Her record that the GUARDIAN gave (or withdrew) consent, and how she verified it. Hoola never marks consent by
    itself: only the owner / an approved team member records it, with the verification method."""
    if not is_owner(actor) and not (actor or "").startswith("staff:"):
        raise ShikshaError("Only the owner / school team can record consent.")
    method = _s(method, 30)
    if given and method not in R.CONSENT_METHODS:
        raise ShikshaError("How was the consent checked? method: " + ", ".join(R.CONSENT_METHODS))
    with _LOCK, session() as s:
        x = _learner_row(s, tenant, ref)
        logs = _j(x.consent_log, [])
        logs.append({"at": now().isoformat(timespec="seconds"), "status": "given" if given else "withdrawn", "by": actor or "owner",
                     "method": method, "note": _s(note, 300)})
        x.consent, x.consent_log = ("given" if given else "withdrawn"), _d(logs[-50:])
        v = _learner_view(x, s.get(ShikshaClass, x.class_id) if x.class_id else None, True)
    v["say"] = (f"{v['number']}: guardian's consent recorded ({R.CONSENT_METHODS.get(method, method)})." if given else
                f"{v['number']}: consent withdrawn; no study / marks work will be done for them now.")
    return v


def need_usable(tenant: str, ref: str) -> dict:
    """Guard for every employee that works with ONE child's data (tutor, grading, reports): refuses until consent."""
    v = learner(tenant, ref)
    if not v["usable"]:
        raise ShikshaError(f"{v['number']} {v['name']} is under 18 and the guardian's consent is not recorded; record consent first "
                           "(shiksha action=consent).")
    return v


def forget_learner(tenant: str, ref: str, actor: str = "owner") -> dict:
    """Erasure (DPDP s.12 / a guardian's request): personal details and marks removed; the number stays as a stub."""
    if not is_owner(actor):
        raise ShikshaError("Only the owner can erase a learner's data.")
    with _LOCK, session() as s:
        x = _learner_row(s, tenant, ref)
        n = 0
        for m in s.scalars(select(ShikshaMark).where(ShikshaMark.learner_id == x.id)).all():
            s.delete(m)
            n += 1
        for k in ("name", "roll", "guardian_name", "guardian_relation", "guardian_phone", "guardian_email", "language"):
            setattr(x, k, "")
        x.birth_year, x.status, x.consent, x.consent_log = 0, "forgotten", "withdrawn", _d([{"at": now().isoformat(
            timespec="seconds"), "status": "forgotten", "by": actor or "owner"}])
        num = x.number
    return {"number": num, "marks_removed": n, "say": f"All personal data of {num} and {n} marks were erased."}


# ---------------------------------------------------------------- question bank (shared)
def q_view(x: ShikshaQuestion, full: bool = True) -> dict:
    out = {"id": x.id, "number": x.number, "board": x.board, "grade": x.grade, "subject": x.subject, "chapter": x.chapter,
           "topic": x.topic, "qtype": x.qtype, "bloom": x.bloom, "difficulty": x.difficulty, "competency": x.competency,
           "marks": x.marks, "text": x.text if full else x.text[:220], "status": x.status, "source": x.source,
           "language": x.language, "checks": _j(x.checks, [])}
    if full:
        out.update(options=_j(x.options, []), answer=x.answer, steps=_j(x.steps, []), scheme=_j(x.scheme, []),
                   standards=_j(x.standards, []), used=_j(x.used, []), approved_by=x.approved_by)
    return out


def _q_row(s, tenant: str, ref: str) -> ShikshaQuestion:
    ref = _s(ref, 40)
    x = s.scalars(select(ShikshaQuestion).where(ShikshaQuestion.tenant_id == tenant,
                                                (ShikshaQuestion.id == ref) | (ShikshaQuestion.number == ref))).first()
    if x is None:
        raise ShikshaError(f"Question '{ref}' not found.")
    return x


def save_questions(tenant: str, items: list[dict], *, board: str, grade: str, subject: str, language: str = "English",
                   source: str = "ai") -> dict:
    """Check every question in code and add the good ones to the bank as drafts. Fatal problems and near-duplicates of
    a question already in her bank are left out, with the reason."""
    added, skipped = [], []
    with _LOCK, session() as s:
        have = s.scalars(select(ShikshaQuestion).where(ShikshaQuestion.tenant_id == tenant, ShikshaQuestion.subject == subject,
                                                       ShikshaQuestion.grade == grade, ShikshaQuestion.status != "retired")).all()
        texts = [h.text for h in have]
        fps = {h.fingerprint for h in have}
        for raw in items:
            clean, probs = R.check_question(raw if isinstance(raw, dict) else {})
            if R.fatal(probs):
                skipped.append({"text": clean["text"][:160], "why": [p.lstrip("! ") for p in probs if p.startswith("!")]})
                continue
            fp = R.fingerprint(clean["text"], clean["options"])
            if fp in fps or any(R.similar(clean["text"], t) >= 0.85 for t in texts):
                skipped.append({"text": clean["text"][:160], "why": ["the bank already has a question like this"]})
                continue
            x = ShikshaQuestion(tenant_id=tenant, number=f"Q-{next_no(s, tenant, 'question'):05d}", board=board, grade=grade,
                                subject=subject, chapter=clean["chapter"], topic=clean["topic"], standards=_d(clean["standards"]),
                                qtype=clean["qtype"], bloom=clean["bloom"], difficulty=clean["difficulty"],
                                competency=clean["competency"], marks=clean["marks"], text=clean["text"],
                                options=_d(clean["options"]), answer=clean["answer"], steps=_d(clean["steps"]),
                                scheme=_d(clean["scheme"]), language=_s(language, 20) or "English",
                                source=source if source in ("ai", "teacher", "import") else "ai", status="draft",
                                checks=_d(probs), fingerprint=fp)
            s.add(x)
            s.flush()
            fps.add(fp)
            texts.append(clean["text"])
            added.append(q_view(x))
    return {"added": added, "skipped": skipped}


def bank(tenant: str, subject: str = "", grade: str = "", chapter: str = "", qtype: str = "", status: str = "",
         q: str = "", limit: int = 50) -> dict:
    with session() as s:
        stmt = select(ShikshaQuestion).where(ShikshaQuestion.tenant_id == tenant)
        if subject:
            stmt = stmt.where(ShikshaQuestion.subject == subject)
        if grade:
            stmt = stmt.where(ShikshaQuestion.grade == R._grade_key(grade))
        if qtype:
            stmt = stmt.where(ShikshaQuestion.qtype == qtype)
        stmt = stmt.where(ShikshaQuestion.status == status) if status else stmt.where(ShikshaQuestion.status != "retired")
        rows = s.scalars(stmt.order_by(ShikshaQuestion.number)).all()
        if chapter:
            rows = [r for r in rows if R.norm_text(chapter) in R.norm_text(r.chapter)]
        if q:
            rows = [r for r in rows if R.norm_text(q) in R.norm_text(r.text + " " + r.topic + " " + r.chapter)]
        counts: dict[str, int] = {}
        for r in rows:
            counts[r.status] = counts.get(r.status, 0) + 1
        return {"total": len(rows), "counts": counts, "questions": [q_view(r, full=False) for r in rows[: max(1, min(limit, 200))]]}


def question(tenant: str, ref: str) -> dict:
    with session() as s:
        return q_view(_q_row(s, tenant, ref))


def edit_question(tenant: str, ref: str, changes: dict, actor: str = "owner") -> dict:
    _need_team(actor)
    with _LOCK, session() as s:
        x = _q_row(s, tenant, ref)
        cur = q_view(x)
        merged = {**cur, **{k: v for k, v in (changes or {}).items() if v is not None}}
        clean, probs = R.check_question(merged)
        if R.fatal(probs):
            raise ShikshaError("The question is not valid after the change: " + "; ".join(p.lstrip("! ") for p in probs if p.startswith("!")))
        for k in ("qtype", "text", "answer", "marks", "bloom", "difficulty", "competency", "chapter", "topic"):
            setattr(x, k, clean[k])
        x.options, x.steps, x.scheme, x.standards = _d(clean["options"]), _d(clean["steps"]), _d(clean["scheme"]), _d(clean["standards"])
        x.checks, x.fingerprint, x.updated_at = _d(probs), R.fingerprint(clean["text"], clean["options"]), now()
        if x.status == "approved":
            x.status, x.approved_by = "draft", ""        # an edited question is read again before use
        x.source = "teacher" if x.source == "ai" and changes else x.source
        return q_view(x)


def set_status(tenant: str, refs: list[str], status: str, actor: str = "owner") -> dict:
    """Teacher review: approve (only a question with no open problems) or retire."""
    _need_team(actor)
    if status not in ("approved", "retired", "draft"):
        raise ShikshaError("status: approved | retired | draft")
    done, refused = [], []
    with _LOCK, session() as s:
        for ref in refs[:200]:
            try:
                x = _q_row(s, tenant, ref)
            except ShikshaError as e:
                refused.append({"ref": ref, "why": str(e)})
                continue
            if status == "approved" and _j(x.checks, []):
                refused.append({"ref": x.number, "why": "fix this first: " + "; ".join(_j(x.checks, []))[:300]})
                continue
            x.status, x.updated_at = status, now()
            x.approved_by = (actor or "owner") if status == "approved" else ""
            done.append(x.number)
    return {"done": done, "refused": refused, "status": status}


def mark_used(tenant: str, ids: list[str], paper_no: str) -> None:
    with _LOCK, session() as s:
        for i in ids:
            x = s.get(ShikshaQuestion, i)
            if x and x.tenant_id == tenant:
                u = _j(x.used, [])
                if paper_no not in u:
                    x.used = _d((u + [paper_no])[-30:])


# ---------------------------------------------------------------- gradebook (Phase 3 grades into it)
def add_mark(tenant: str, learner_ref: str, assessment: str, subject: str, marks: float, max_marks: float,
             actor: str = "owner", note: str = "") -> dict:
    _need_team(actor)
    v = need_usable(tenant, learner_ref)
    if not (0 <= float(marks) <= float(max_marks)) or float(max_marks) <= 0:
        raise ShikshaError("Marks must be between 0 and the maximum.")
    with _LOCK, session() as s:
        m = ShikshaMark(tenant_id=tenant, learner_id=v["id"], assessment=_s(assessment, 80), subject=_s(subject, 80),
                        marks=float(marks), max_marks=float(max_marks), by=actor or "owner", note=_s(note, 300))
        s.add(m)
        s.flush()
        return {"id": m.id, "learner": v["number"], "assessment": m.assessment, "marks": m.marks, "max": m.max_marks,
                "signed_off": False}


def marks(tenant: str, learner_ref: str) -> dict:
    v = need_usable(tenant, learner_ref)
    with session() as s:
        rows = s.scalars(select(ShikshaMark).where(ShikshaMark.learner_id == v["id"]).order_by(ShikshaMark.at)).all()
        return {"learner": v["number"], "name": v["name"],
                "marks": [{"id": m.id, "assessment": m.assessment, "subject": m.subject, "marks": m.marks, "max": m.max_marks,
                           "signed_off": m.signed_off, "by": m.by, "at": m.at} for m in rows]}


def sign_off(tenant: str, mark_ids: list[str], actor: str = "owner") -> dict:
    """Final marks are a teacher's word: only the owner or a team member signs them off, never Hoola by itself."""
    if not is_owner(actor) and not (actor or "").startswith("staff:"):
        raise ShikshaError("Only the teacher / owner makes marks final.")
    n = 0
    with _LOCK, session() as s:
        for i in mark_ids[:500]:
            m = s.get(ShikshaMark, i)
            if m and m.tenant_id == tenant and not m.signed_off:
                m.signed_off, n = True, n + 1
    return {"signed_off": n}


def day(tenant: str) -> dict:
    cl = classes(tenant)
    with session() as s:
        ls = s.scalars(select(ShikshaLearner).where(ShikshaLearner.tenant_id == tenant, ShikshaLearner.status == "active")).all()
        cls_by = {c.id: c for c in s.scalars(select(ShikshaClass).where(ShikshaClass.tenant_id == tenant)).all()}
        no_consent = sum(1 for x in ls if R.is_child(x.birth_year, x.adult, cls_by[x.class_id].grade if x.class_id in cls_by else "")
                         and x.consent != "given")
        drafts = len(s.scalars(select(ShikshaQuestion.id).where(ShikshaQuestion.tenant_id == tenant,
                                                                ShikshaQuestion.status == "draft")).all())
    lines = []
    if drafts:
        lines.append(f"{drafts} questions are waiting for the teacher's review.")
    if no_consent:
        lines.append(f"Guardian consent is pending for {no_consent} children.")
    return {"classes": cl, "learners": len(ls), "consent_pending": no_consent, "drafts": drafts, "settings": settings(tenant),
            "say": " ".join(lines) or (f"{len(cl)} classes, {len(ls)} learners." if cl else "No class has been added yet.")}
