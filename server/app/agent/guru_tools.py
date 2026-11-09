"""Guru Sahayak tools (personal tutor, Shiksha suite Phase 2). `guru_dekho` only reads; `guru` teaches.

A doubt is taught with a hint ladder: show ONLY the rung the tool returns (hint -> nudge -> steps -> answer); never add
the answer yourself. A child (under 18) is taught only after the guardian's consent is recorded. Graded work / exam mode =
hints only. The weekly report reaches the guardian only through her app tap (POST /api/guru/shares/{id}/decide)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

GURU_TOOLS = [
    {"name": "guru", "description": (
        "Personal tutor for one learner (Shiksha learner S-0001, from shiksha). action=start: learner, mode doubt|practice|"
        "language, subject, grade, topic, language -> GS-00001. action=doubt: session, text (the student's question, their "
        "own words) or file_id (a photo of the question) -> rung 1 (a hint). action=hint: session, attempt (what the student "
        "tried) -> the next rung (nudge, then worked steps, then the full answer; never in exam mode / graded work). "
        "action=practice: session -> the next question from the APPROVED bank (due revision first, else the weakest topic, "
        "difficulty matched). action=answer: session, given, hints -> checked (objective in code, written answers by AI as a "
        "suggestion), mastery + next revision day. action=language: session, text -> reply in the target language + gentle "
        "corrections + new words. action=end: session. action=report: learner, via whatsapp|email -> a weekly report CARD for "
        "the guardian (her tap sends). action=path: learner, subject, grade, chapters [] (else the NCERT book) -> a mastery "
        "path: practice then stays in the CURRENT chapter (plus due revision) and the next chapter opens only when this one "
        "clears the gate. action=settings: day_minutes (a child's daily limit), exam_mode, report_weekday, language, "
        "strategy long_term|cramming, exam_date YYYY-MM-DD (revisions squeeze to fit before it), gate (0.5-1), "
        "gate_attempts, grounded (explain from her own books in Gyaan with page cites) (owner only). Show the student EXACTLY the text returned; never solve it yourself on top."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["start", "doubt", "hint", "practice", "answer", "language", "end", "report",
                                               "path", "settings"]},
         "learner": {"type": "string"}, "session": {"type": "string"}, "mode": {"type": "string"},
         "subject": {"type": "string"}, "grade": {"type": "string"}, "topic": {"type": "string"},
         "language": {"type": "string"}, "text": {"type": "string"}, "file_id": {"type": "string"},
         "attempt": {"type": "string"}, "given": {"type": "string"}, "hints": {"type": "integer"},
         "via": {"type": "string"}, "day_minutes": {"type": "integer"}, "exam_mode": {"type": "boolean"},
         "report_weekday": {"type": "integer"}, "chapters": {"type": "array", "items": {"type": "string"}},
         "strategy": {"type": "string"}, "exam_date": {"type": "string"}, "gate": {"type": "number"},
         "gate_attempts": {"type": "integer"}, "grounded": {"type": "boolean"}},
         "required": ["action"]}},
    {"name": "guru_dekho", "description": (
        "Read tutoring (nothing changes). what=day | progress (learner: mastery per topic, this week's minutes / accuracy, weak "
        "and due topics) | path (learner, subject: chapters passed / current / locked with mastery) | report (learner: the "
        "weekly report text) | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "progress", "path", "report", "settings", "rules"]},
         "learner": {"type": "string"}, "subject": {"type": "string"}}, "required": ["what"]}},
]
GURU_LABELS = {"guru": "Padha raha hoon", "guru_dekho": "Padhai ki pragati dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    a = getattr(ctx, "actor", "owner") or "owner"
    if a.startswith("customer:"):
        raise ToolError("The tutor is only for the home / school team; not for customers.")
    return a


async def guru(ctx: Ctx, action, **a: Any):
    from ..guru import service as G
    t, actor, action, conv = ctx.tenant_id, _actor(ctx), str(action), ctx.conversation_id
    sid = _s(a.get("session"))
    try:
        if action == "start":
            return await asyncio.to_thread(G.start, t, _s(a.get("learner")), _s(a.get("mode")) or "doubt", _s(a.get("subject")),
                                           _s(a.get("grade")), _s(a.get("topic")), _s(a.get("language")), actor)
        if action == "doubt":
            return await asyncio.to_thread(G.doubt, t, sid, _s(a.get("text")), _s(a.get("file_id")), actor)
        if action == "hint":
            return await asyncio.to_thread(G.hint, t, sid, _s(a.get("attempt")), actor)
        if action == "practice":
            return await asyncio.to_thread(G.next_question, t, sid, actor)
        if action == "answer":
            return await asyncio.to_thread(G.answer, t, sid, _s(a.get("given")), int(a.get("hints") or 0), actor)
        if action == "language":
            return await asyncio.to_thread(G.language_turn, t, sid, _s(a.get("text")), actor)
        if action == "end":
            return await asyncio.to_thread(G.end, t, sid, actor)
        if action == "report":
            return await asyncio.to_thread(G.share_request, t, _s(a.get("learner")), _s(a.get("via")) or "whatsapp", actor, conv)
        if action == "path":
            return await asyncio.to_thread(G.build_path, t, _s(a.get("learner")), _s(a.get("subject")), _s(a.get("grade")),
                                           a.get("chapters"), actor)
        if action == "settings":
            return await asyncio.to_thread(G.save_settings, t, actor, **{k: a.get(k) for k in
                                           ("day_minutes", "exam_mode", "report_weekday", "language", "strategy", "exam_date",
                                            "gate", "gate_attempts", "grounded")})
    except (G.GuruError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("action galat")


async def guru_dekho(ctx: Ctx, what, **a: Any):
    from ..guru import rules as R
    from ..guru import service as G
    _actor(ctx)
    t, what = ctx.tenant_id, str(what)

    def go():
        if what == "day":
            return G.day(t)
        if what == "progress":
            return G.progress(t, _s(a.get("learner")))
        if what == "path":
            return G.path_view(t, _s(a.get("learner")), _s(a.get("subject")))
        if what == "report":
            return G.report(t, _s(a.get("learner")))
        if what == "settings":
            return G.settings(t)
        if what == "rules":
            return {"never": R.NEVER, "disclaimer": R.DISCLAIMER, "ladder": R.LEVEL_SAY}
        raise ToolError("what galat")
    try:
        return await asyncio.to_thread(go)
    except (G.GuruError, ValueError) as e:
        raise ToolError(str(e))


GURU_HANDLERS = {"guru": guru, "guru_dekho": guru_dekho}
