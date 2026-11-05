"""HOOLA SKILLS tool (v0.478.0) - ONE tool for the whole skill surface, the Hermes skill_manage
shape: an operations array, batch-capped, applied atomically. Santosh herself can author and
improve skills mid-conversation (Hermes's precondition: skill_manage in valid tool names is what
arms the nudge's reset-on-use rule too).

The handler is registered into the agent's tool table by agent/tools.py; it lives here so the
coder module owns its surface and the import direction stays agent -> coder.
"""
from __future__ import annotations

from . import nudge, skills_store

SKILL_MANAGE_SCHEMA = {
    "name": "skill_manage",
    "description": (
        "Read, create, update or delete a REUSABLE SKILL: a short English how-to for a CLASS of "
        "task she would do again (deploy-a-flask-app), never for one specific incident. Skills "
        "are files she re-reads later. Operations is an array, max 10; delete must be the ONLY "
        "operation in its batch. update requires a prior read of that skill (list or read first). "
        "A read of a skill with bundled files lists them; read_file (name + path) opens one. "
        "name: lowercase-hyphenated <= 64 chars. description: <= 60 chars, one sentence. "
        "body: <= 4000 chars of instructions."),
    "input_schema": {
        "type": "object",
        "properties": {
            "operations": {
                "type": "array",
                "description": "One or more skill operations, applied in order, atomically.",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string",
                                   "enum": ["read", "list", "create", "update", "delete", "read_file"]},
                        "name": {"type": "string", "description": "lowercase-hyphenated skill id"},
                        "path": {"type": "string", "description": "read_file only: the bundled file, relative"},
                        "description": {"type": "string", "description": "<= 60 chars, one sentence"},
                        "body": {"type": "string", "description": "the instructions, markdown"},
                    },
                    "required": ["action"],
                },
            },
        },
        "required": ["operations"],
    },
}

SKILL_TOOLS = [SKILL_MANAGE_SCHEMA]
SKILL_LABELS = {"skill_manage": "Seekha hua kaam note kar raha hoon"}
SKILL_HANDLERS = {"skill_manage": None}      # set below (async handler)


async def skill_manage(ctx, operations=None, **_):
    """The one skill surface. Every write is linted, atomic and tenant-scoped; the nudge's
    turn counter resets on ANY successful use (Hermes's rule: a skill was just authored)."""
    from ..config import get_settings
    st = get_settings()
    if not getattr(st, "coder_enabled", True) or not getattr(st, "coder_skills", True):
        return {"error": "skills are switched off (coder_skills)"}
    res = skills_store.apply(ctx.tenant_id, operations if isinstance(operations, list) else [])
    if res.get("ok"):
        nudge.reset_counter(ctx.tenant_id, ctx.conversation_id)
    return res


SKILL_HANDLERS["skill_manage"] = skill_manage
