"""v0.487.0 BYOX tools — Build-Your-Own-X skill pack.

Three tools:
  byox_list   list all 31 BYOX categories, optionally filtered
  byox_guide  full guide for one category (phases, concepts, reference)
  byox_plan   personalised learning plan given what the user wants to build
"""
from __future__ import annotations

from ..byox.guide import get_guide, list_categories, plan_learning

BYOX_TOOLS = [
    {
        "name": "byox_list",
        "description": (
            "List the Build-Your-Own-X categories Hoola knows (3D Renderer, BitTorrent, "
            "Database, Docker, Git, OS, Shell, Web Server, …). "
            "Use when the user asks what systems they can build from scratch, wants to explore "
            "BYOX projects, or is choosing a learning project. "
            "Filter with q= for a keyword match. Returns slug, display_name, description, "
            "best_languages for every matching category."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "Optional keyword filter (e.g. 'web', 'database', 'rust')",
                },
            },
        },
    },
    {
        "name": "byox_guide",
        "description": (
            "Return a detailed guide for one Build-Your-Own-X category: "
            "core concepts, 5 build phases, best languages and a reference URL. "
            "Use when the user picks a specific project to build (e.g. 'build a git clone', "
            "'how do I build a database from scratch'). "
            "level='quick' returns phases only; level='standard' (default) returns everything; "
            "level='deep' adds practitioner tips. "
            "language= filters tutorials to that language (e.g. 'Python', 'Rust', 'Go')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slug_or_name": {
                    "type": "string",
                    "description": "Category slug (e.g. 'byox-git') or display name (e.g. 'Git')",
                },
                "level": {
                    "type": "string",
                    "enum": ["quick", "standard", "deep"],
                    "description": "Detail level (default: standard)",
                },
                "language": {
                    "type": "string",
                    "description": "Optional language filter, e.g. 'Python', 'Rust', 'Go', 'JavaScript'",
                },
            },
            "required": ["slug_or_name"],
        },
    },
    {
        "name": "byox_plan",
        "description": (
            "Create a personalised BYOX learning plan. "
            "Use when the user says they want to learn systems programming, "
            "wants a project roadmap, or describes what kind of system they want to build. "
            "Returns a week-by-week plan with matched categories and milestones."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "want": {
                    "type": "string",
                    "description": "What the user wants to build or learn (free text)",
                },
                "background": {
                    "type": "string",
                    "description": "Comma-separated languages or skills the user already knows",
                },
                "time_weeks": {
                    "type": "integer",
                    "description": "Number of weeks available (default 4)",
                    "default": 4,
                },
            },
            "required": ["want"],
        },
    },
]

BYOX_LABELS: dict[str, str] = {
    "byox_list": "BYOX categories dhundh raha hoon…",
    "byox_guide": "BYOX guide padh raha hoon…",
    "byox_plan": "BYOX learning plan bana raha hoon…",
}


class _Ctx:
    """Minimal context shim so handlers work with the real Ctx signature."""
    def __init__(self, args: dict):
        self._args = args

    def get(self, key: str, default=None):
        return self._args.get(key, default)


async def _handle_byox_list(ctx) -> dict:
    q = ctx.get("q", "") or ""
    cats = list_categories(q)
    return {"categories": cats, "count": len(cats)}


async def _handle_byox_guide(ctx) -> dict:
    slug_or_name = ctx.get("slug_or_name", "") or ""
    level = ctx.get("level", "standard") or "standard"
    language = ctx.get("language", "") or ""
    return get_guide(slug_or_name, level=level, language=language)


async def _handle_byox_plan(ctx) -> dict:
    want = ctx.get("want", "") or ""
    background = ctx.get("background", "") or ""
    time_weeks = int(ctx.get("time_weeks") or 4)
    return plan_learning(want, background=background, time_weeks=time_weeks)


BYOX_HANDLERS: dict[str, object] = {
    "byox_list": _handle_byox_list,
    "byox_guide": _handle_byox_guide,
    "byox_plan": _handle_byox_plan,
}
