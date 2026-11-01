"""Prayogshala tool (v0.415, L0 + L1): find and open a 3D practical lab. Read-only: it never changes anything, so every
user, every employee role and the voice call (via santosh_kaam) may use it. Numbers in a lab come from the lab's
simulation code, never from the model - so this tool gives LINKS and the lab's own checked numbers, not explanations
with invented values."""
from __future__ import annotations

from typing import Any

from .tools import Ctx, ToolError

PRAYOG_TOOLS = [
    {"name": "prayog", "description": (
        "Prayogshala: real practical labs in 3D (knobs, meters, observation table, guided tour, quiz) that run on the "
        "learner's phone; every reading comes from the lab's simulation code, checked against the NCERT formula. "
        "action=find: q (topic words, e.g. 'pendulum', 'lens', 'ohm', 'resonance'), field -> matching labs with links. "
        "action=open: id -> the lab card (link, aim, knobs, steps) to show her. action=check: id -> the lab's own NCERT "
        "check (simulated reading vs textbook formula, % error). action=all -> the catalogue link. Use it whenever someone "
        "asks to SEE how something works or to do a practical; send the link, do not describe numbers yourself."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["find", "open", "check", "all"]},
         "q": {"type": "string"}, "field": {"type": "string"}, "id": {"type": "string"}},
         "required": ["action"]}},
]
PRAYOG_LABELS = {"prayog": "Finding a lab in Prayogshala"}


async def prayog(ctx: Ctx, action, q: str = "", field: str = "", id: str = "", **_: Any):
    from ..prayog import lsl
    from ..prayog import service as S

    action = str(action or "").strip()
    if action == "all":
        return {"url": S.catalogue_link(), "count": len(S.labs()), "note": S.NOTE}
    if action == "find":
        rows = S.search(q, field, 8)
        if not rows and q:                          # loose match: any word
            seen = {}
            for w in str(q).split():
                for r in S.search(w, field, 8):
                    seen[r["id"]] = r
            rows = list(seen.values())[:8]
        return {"labs": [{**r, "url": S.link(r["id"])} for r in rows], "count": len(rows), "all": S.catalogue_link(),
                "note": "No lab found: Prayogshala has physics practicals now (more fields are coming)." if not rows else S.NOTE}
    lab = S.get(id)
    if not lab:
        raise ToolError(f"Lab '{id}' not found. Get the id with action=find first.")
    if action == "open":
        return S.card(lab)
    if action == "check":
        r = lsl.run_check(lab)
        return {"id": lab["id"], "check": lab["check"]["textbook"], "simulated": r["measured"], "textbook": r["textbook"],
                "error_percent": round(r["error"] * 100, 3), "within": f"{r['tol'] * 100:.1f}%", "ok": r["ok"]}
    raise ToolError("action: find / open / check / all")


PRAYOG_HANDLERS = {"prayog": prayog}
