"""Daftar Sahayak tools (school admin operations, Shiksha suite Phase 3). `daftar_dekho` only reads; `daftar` works.

Every mark Hoola makes is UNSIGNED in the gradebook until a teacher signs it off (shiksha action=sign_off). Absence
alerts and report cards reach guardians only through her app tap, as drafts she sends herself."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

DAFTAR_TOOLS = [
    {"name": "daftar", "description": (
        "School office work (Daftar Sahayak). action=attendance: class, day (YYYY-MM-DD, default today), absent [], late [], "
        "leave [] (rolls / names / S-numbers; everyone else present; marking a day again replaces it). action=alerts: class, "
        "day -> a CARD for her tap with one WhatsApp draft per absent child's guardian. action=grade_sheet: class, "
        "assessment, subject, key [Q1, Q2 ...] or paper (P-0001), rows [{roll, answers}] or file_id (CSV: roll, Q1, Q2 ...). "
        "action=omr: file_id (photo of one answer sheet), questions -> what is marked, for the teacher to confirm (nothing "
        "saved). action=grade_forms: class, assessment, form, paper (a Pathyakram Google Forms quiz). action=grade_code: "
        "learner, assessment, code, tests [{call, expected}], max_marks (Python in the locked sandbox). action=grade_rubric: "
        "learner, assessment, answer, rubric (RB-001) -> AI suggestion per criterion. action=report_card: learner, term -> "
        "Word file (signed-off marks only). action=report_share: learner, term -> a card for her tap. action=timetable: "
        "needs [{class, subject, teacher, per_week}], periods, days, max_same -> clash-free grid. All marks are UNSIGNED "
        "until a teacher signs off."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["attendance", "alerts", "grade_sheet", "omr", "grade_forms", "grade_code",
                                               "grade_rubric", "report_card", "report_share", "timetable"]},
         "class": {"type": "string"}, "day": {"type": "string"}, "absent": {"type": "array", "items": {"type": "string"}},
         "late": {"type": "array", "items": {"type": "string"}}, "leave": {"type": "array", "items": {"type": "string"}},
         "assessment": {"type": "string"}, "subject": {"type": "string"}, "key": {"type": "array", "items": {"type": "string"}},
         "paper": {"type": "string"}, "rows": {"type": "array", "items": {"type": "object"}}, "file_id": {"type": "string"},
         "questions": {"type": "integer"}, "form": {"type": "string"}, "learner": {"type": "string"},
         "code": {"type": "string"}, "tests": {"type": "array", "items": {"type": "object"}}, "max_marks": {"type": "number"},
         "answer": {"type": "string"}, "rubric": {"type": "string"}, "term": {"type": "string"},
         "needs": {"type": "array", "items": {"type": "object"}}, "periods": {"type": "integer"},
         "days": {"type": "array", "items": {"type": "string"}}, "max_same": {"type": "integer"}},
         "required": ["action"]}},
    {"name": "daftar_dekho", "description": (
        "Read school office records (nothing changes). what=day | attendance (class, month YYYY-MM: % per child, below 75%) | "
        "gradings | unsigned (class, assessment: marks waiting for sign-off with ids) | report (learner, term) | timetables | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "attendance", "gradings", "unsigned", "report", "timetables", "rules"]},
         "class": {"type": "string"}, "month": {"type": "string"}, "assessment": {"type": "string"},
         "learner": {"type": "string"}, "term": {"type": "string"}}, "required": ["what"]}},
]
DAFTAR_LABELS = {"daftar": "Working on the school office", "daftar_dekho": "Checking the school register"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    a = getattr(ctx, "actor", "owner") or "owner"
    if a.startswith("customer:"):
        raise ToolError("This is school office work; not for customers.")
    return a


async def daftar(ctx: Ctx, action, **a: Any):
    from ..daftar import service as D
    t, actor, conv, action = ctx.tenant_id, _actor(ctx), ctx.conversation_id, str(action)
    c, L = _s(a.get("class")), _s(a.get("learner"))
    try:
        if action == "attendance":
            return await asyncio.to_thread(D.mark_attendance, t, c, _s(a.get("day")), a.get("absent"), a.get("late"), a.get("leave"), actor)
        if action == "alerts":
            return await asyncio.to_thread(D.absent_alerts, t, c, _s(a.get("day")), actor, conv)
        if action == "grade_sheet":
            return await asyncio.to_thread(D.grade_sheet, t, c, _s(a.get("assessment")), _s(a.get("subject")), a.get("key"),
                                           _s(a.get("paper")), a.get("rows"), _s(a.get("file_id")), actor)
        if action == "omr":
            return await asyncio.to_thread(D.omr_read, t, _s(a.get("file_id")), int(a.get("questions") or 0), actor)
        if action == "grade_forms":
            return await asyncio.to_thread(D.grade_forms, t, c, _s(a.get("assessment")), _s(a.get("form")), _s(a.get("paper")), actor)
        if action == "grade_code":
            return await asyncio.to_thread(D.grade_code, t, L, _s(a.get("assessment")), _s(a.get("code")), a.get("tests") or [],
                                           float(a.get("max_marks") or 10), _s(a.get("subject")) or "Computer Science", actor)
        if action == "grade_rubric":
            return await asyncio.to_thread(D.grade_rubric, t, L, _s(a.get("assessment")), _s(a.get("answer")), _s(a.get("rubric")),
                                           _s(a.get("subject")), actor)
        if action == "report_card":
            return await asyncio.to_thread(D.report_card_file, t, L, _s(a.get("term")), conv)
        if action == "report_share":
            return await asyncio.to_thread(D.report_card_share, t, L, _s(a.get("term")), actor, conv)
        if action == "timetable":
            return await asyncio.to_thread(D.timetable, t, a.get("needs") or [], int(a.get("periods") or 8), a.get("days"),
                                           int(a.get("max_same") or 2), actor)
    except (D.DaftarError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("unknown action")


async def daftar_dekho(ctx: Ctx, what, **a: Any):
    from ..daftar import rules as R
    from ..daftar import service as D
    _actor(ctx)
    t, what = ctx.tenant_id, str(what)

    def go():
        if what == "day":
            return D.day(t)
        if what == "attendance":
            return D.attendance(t, _s(a.get("class")), _s(a.get("month")))
        if what == "gradings":
            return {"gradings": D.gradings(t)}
        if what == "unsigned":
            return D.unsigned(t, _s(a.get("class")), _s(a.get("assessment")))
        if what == "report":
            return D.report_card(t, _s(a.get("learner")), _s(a.get("term")))
        if what == "timetables":
            return {"timetables": D.timetables(t)}
        if what == "rules":
            return {"never": R.NEVER, "grade_scale": R.GRADE_SCALE}
        raise ToolError("unknown what")
    try:
        return await asyncio.to_thread(go)
    except (D.DaftarError, ValueError) as e:
        raise ToolError(str(e))


DAFTAR_HANDLERS = {"daftar": daftar, "daftar_dekho": daftar_dekho}
