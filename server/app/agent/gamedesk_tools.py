"""v0.379 GAME DESK tool: `game_desk` = the Game Developer employee (gamedesk/service.py). Original games from her words
in Godot 4: a design doc first (her OK), then code -> headless play -> Web export -> Hoola plays it -> a private play
link. Only while the Game Developer is hired (Employees). Nothing is published: the link is hers to share."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

KEY = "game_dev"

GAMEDESK_TOOLS = [
    {"name": "game_desk", "description": (
        "Game Developer employee (Godot 4): makes an ORIGINAL small game from her words and gives a private link she plays "
        "on any phone. action=new (brief = her idea in her words, orientation portrait|landscape|square) writes a short "
        "design doc FIRST and waits; show her the design and ask for OK. action=approve (id; feedback = her changes, empty = "
        "build it): builds in the background (code, headless play, Web export, Hoola plays it, fixes its own errors) - the "
        "card updates live and carries the play link. action=change (id, words) = a new version from the current game. "
        "action=status / list / cancel. Refuses copies of a named existing game, real-money / betting games and weapon "
        "targeting; offers an original game in the same genre instead."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "approve", "change", "status", "list", "cancel"]},
         "brief": {"type": "string", "description": "action=new: her game idea, in her words"},
         "orientation": {"type": "string", "enum": ["portrait", "landscape", "square"]},
         "id": {"type": "string", "description": "Game id or number (G-0001)"},
         "feedback": {"type": "string", "description": "action=approve: her changes to the design (empty = build it)"},
         "words": {"type": "string", "description": "action=change: what to change in the game"}},
         "required": ["action"]}},
]

GAMEDESK_LABELS = {"game_desk": "Game bana raha hoon"}


def _short(v: dict) -> dict:
    out = {k: v.get(k) for k in ("id", "number", "title", "status", "say", "stage", "error", "play_url", "version", "notes",
                                 "numbers", "warnings") if v.get(k) not in (None, "", [], {})}
    if v.get("status") == "design_ready" and v.get("design"):
        out["design"] = v["design"]
        out["note"] = "Show her this design doc (short) and ask: build it as is, or what to change? Then action=approve."
    if v.get("status") in ("designing", "queued", "writing", "building", "testing"):
        out["note"] = "Working in the background; the card on her screen updates live. Do not wait or poll in a loop."
    if v.get("status") == "done" and v.get("play_url"):
        out["note"] = ("Give her the play link in one line (private until she shares it) and what to try. Never claim "
                       "numbers that are not here.")
    return out


async def game_desk(ctx: Ctx, action="", brief="", orientation="portrait", id="", feedback="", words="", **_):
    from ..employee import hire
    from ..gamedesk import service as G
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer hired nahi hai: Employees (Hoola app / console) mein ek tap mein hire kijiye, "
                        "phir game ban jayega.")
    if action in ("new", "approve", "change", "cancel") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Game banana / badalna sirf owner ka kaam hai.")
    try:
        if action == "new":
            return _short(await asyncio.to_thread(G.start, t, ctx.conversation_id, brief, orientation, ctx.actor))
        if action == "approve":
            return _short(await asyncio.to_thread(G.approve, t, id, feedback))
        if action == "change":
            return _short(await asyncio.to_thread(G.change, t, id, words))
        if action == "cancel":
            return _short(await asyncio.to_thread(G.cancel, t, id))
        if action == "status":
            return _short(await asyncio.to_thread(G.get, t, id))
        if action == "list":
            return {"games": [_short(v) for v in await asyncio.to_thread(G.projects, t, 10)]}
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = new | approve | change | status | list | cancel")


GAMEDESK_HANDLERS = {"game_desk": game_desk}
