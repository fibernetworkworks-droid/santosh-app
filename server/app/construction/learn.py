"""Wave 4 (v0.586.0) const_learn: the training & coaching desk (register #121, #122, #123).

Marks are FED, the pass line is HER policy, scores are arithmetic; the tutor explains and the coach
asks questions, but tax/investment advice stays with the CA (gates.py: "give tax or investment
advice"). Certificates are issued by the training centre, never by Hoola."""
from __future__ import annotations

from sqlalchemy import select

from ..db import session
from . import models as M
from .common import CstError, _dump, _j, _num, publish


def trainee_add(tenant: str, project: str, rows: list, conv: str = "") -> dict:
    """#121: rows [name, trade, batch]."""
    if not rows:
        raise CstError("Trainee rows are needed [name, trade, batch].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or not r:
                continue
            s.add(M.ClearnItem(tenant_id=tenant, project=project, kind="trainee", name=str(r[0])[:120],
                               data=_dump({"trade": str(r[1])[:80] if len(r) > 1 else "",
                                           "batch": str(r[2])[:40] if len(r) > 2 else ""})))
            made += 1
    publish(tenant, "const_learn", {"kind": "trainees", "project": project, "rows": made}, conv)
    return {"ok": True, "rows": made, "said": f"{made} trainee(s) in the register."}


def module_add(tenant: str, project: str, rows: list) -> dict:
    """rows [module, hours, status]."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or not r:
                continue
            s.add(M.ClearnItem(tenant_id=tenant, project=project, kind="module", name=str(r[0])[:120],
                               data=_dump({"hours": _num(r[1]) if len(r) > 1 else 0.0,
                                           "status": str(r[2])[:24] if len(r) > 2 else "planned"})))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} module row(s) - the training centre gives the certificate."}


def assess_add(tenant: str, project: str, rows: list) -> dict:
    """#121: rows [trainee, module, marks, max] - marks AS FED from HER sheets."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 4:
                continue
            m, mx = _num(r[2]), _num(r[3])
            if mx <= 0:
                raise CstError(f"Row '{r[0]}': give max marks greater than 0.")
            s.add(M.ClearnItem(tenant_id=tenant, project=project, kind="assess", name=str(r[0])[:120],
                               data=_dump({"module": str(r[1])[:120], "marks": m, "max": mx,
                                           "pct": round(m / mx * 100, 1)})))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} assessment row(s) written."}


def assess_sum(tenant: str, project: str, pass_pct: float) -> dict:
    """Pass list = arithmetic on HER pass line."""
    if not (0 < pass_pct <= 100):
        raise CstError("Give pass_pct between 0 and 100 (your pass policy).")
    with session() as s:
        rows = s.scalars(select(M.ClearnItem).where(M.ClearnItem.tenant_id == tenant,
                                                    M.ClearnItem.project == project,
                                                    M.ClearnItem.kind == "assess")).all()
    if not rows:
        raise CstError("No assessments found - run action=assess_add first.")
    by_trainee: dict[str, dict] = {}
    for r in rows:
        d = _j(r.data, {})
        o = by_trainee.setdefault(r.name, {"modules": 0, "passed": 0, "pcts": []})
        o["modules"] += 1
        o["pcts"].append(float(d.get("pct") or 0))
        if float(d.get("pct") or 0) >= pass_pct:
            o["passed"] += 1
    out = [{"trainee": k, "modules": v["modules"], "passed": v["passed"],
            "avg_pct": round(sum(v["pcts"]) / len(v["pcts"]), 1),
            "verdict": "pass" if v["passed"] == v["modules"] else "re-test"} for k, v in by_trainee.items()]
    return {"ok": True, "pass_pct": pass_pct, "results": out,
            "said": "The pass line is on YOUR policy; re-tests and certificates are in the training centre's hands."}


def topic_add(tenant: str, project: str, rows: list) -> dict:
    """#122: rows [topic, syllabus_ref, status]."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or not r:
                continue
            s.add(M.ClearnItem(tenant_id=tenant, project=project, kind="topic", name=str(r[0])[:160],
                               data=_dump({"syllabus_ref": str(r[1])[:120] if len(r) > 1 else "",
                                           "status": str(r[2])[:24] if len(r) > 2 else "pending"})))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} topic row(s) - with the syllabus mapping."}


def quiz_add(tenant: str, project: str, topic: str, rows: list) -> dict:
    """#122: rows [question, correct_answer, option_b, option_c, option_d] - answer key saath mein
    (row 1 = correct). Scoring attempt par hoti hai."""
    if not rows:
        raise CstError("Quiz rows are needed [question, correct, b, c, d].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(M.ClearnItem(tenant_id=tenant, project=project, kind="quiz", name=topic[:120],
                               data=_dump({"q": str(r[0])[:300], "answer": str(r[1])[:200],
                                           "opts": [str(x)[:200] for x in r[2:5]]})))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} question(s) in '{topic}', with the answer key."}


def quiz_score(tenant: str, project: str, topic: str, rows: list) -> dict:
    """rows [trainee, given_answer_1, given_answer_2, ...] against the topic's key, in order."""
    with session() as s:
        qs = s.scalars(select(M.ClearnItem).where(M.ClearnItem.tenant_id == tenant,
                                                  M.ClearnItem.project == project,
                                                  M.ClearnItem.kind == "quiz",
                                                  M.ClearnItem.name == topic)).all()
    if not qs:
        raise CstError(f"Topic '{topic}' has no quiz.")
    key = [_j(q.data, {}).get("answer") for q in qs]
    out = []
    for r in rows:
        if not isinstance(r, (list, tuple)) or not r:
            continue
        given = [str(x) for x in r[1:]]
        right = sum(1 for i, a in enumerate(key) if i < len(given)
                    and str(a).strip().lower() == given[i].strip().lower())
        out.append({"trainee": str(r[0])[:120], "score": right, "of": len(key),
                    "pct": round(right / len(key) * 100, 1) if key else 0.0})
    return {"ok": True, "topic": topic, "results": out,
            "said": "The score is arithmetic; explaining is the tutor's (my) job - the marks sheet is yours."}


def coach_check(tenant: str, project: str, rows: list) -> dict:
    """#123: records discipline checklist [item, status, note]."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(M.ClearnItem(tenant_id=tenant, project=project, kind="coach", name=str(r[0])[:120],
                               data=_dump({"status": str(r[1])[:40] if len(r) > 1 else "",
                                           "note": str(r[2])[:200] if len(r) > 2 else ""})))
            made += 1
    return {"ok": True, "rows": made,
            "said": "Checklist written - this is bookkeeping discipline; advice is the CA's (tier C)."}


def coach_note(tenant: str, project: str, text: str, conv: str = "") -> dict:
    if not text:
        raise CstError("Give the note's text.")
    with session() as s:
        s.add(M.ClearnItem(tenant_id=tenant, project=project, kind="coach_note", name=text[:160],
                           data=_dump({"text": text[:500]})))
    publish(tenant, "const_learn", {"kind": "coach_note", "project": project}, conv)
    return {"ok": True, "said": "Coaching note in the register."}
