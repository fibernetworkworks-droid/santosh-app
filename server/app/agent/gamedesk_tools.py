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

GAMEDESK_TOOLS.append(
    {"name": "game_studio", "description": (
        "Studio Project: her LONG game project (weeks / months) around one Game Desk game - task board, milestones "
        "(proto, playable, alpha, beta, release), decisions log, nightly build, morning report. Each task = ONE small "
        "change that Hoola builds and plays, then it WAITS for her OK. Actions: new (game = G-0001, or brief = a new "
        "idea; title, goal) / list / status / add (title, detail, milestone, priority 1-3) / plan (words): Hoola proposes "
        "the next small tasks into To do / start (task optional) / ok (task, note = her reason, saved as a decision) / "
        "back (task, note): the version before plays again / drop (task) / decide (text, why) / why (q): answer ONLY from "
        "what it returns, empty 'found' = say there is no record, never guess / summary / nightly: rebuild + replay now / "
        "restore (n): an old version back as a new one / settings (auto, nightly_on, summary_on, summary_hour, status) / "
        "github (repo, private): a card, only her tap sends it. id = S-0001 (optional when she has one project). Only "
        "while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "list", "status", "add", "plan", "start", "ok", "back", "drop",
                                               "decide", "why", "summary", "nightly", "restore", "settings", "github"]},
         "id": {"type": "string", "description": "Studio project id or number (S-0001)"},
         "game": {"type": "string", "description": "action=new: an existing game (G-0001)"},
         "brief": {"type": "string", "description": "action=new without game: the new game's idea in her words"},
         "orientation": {"type": "string", "enum": ["portrait", "landscape", "square"]},
         "title": {"type": "string"}, "goal": {"type": "string"},
         "task": {"type": "string", "description": "Task id or number (T-0001)"},
         "detail": {"type": "string"}, "milestone": {"type": "string", "enum": ["proto", "playable", "alpha", "beta", "release"]},
         "priority": {"type": "integer"}, "note": {"type": "string"}, "words": {"type": "string"},
         "text": {"type": "string"}, "why": {"type": "string"}, "q": {"type": "string"}, "n": {"type": "integer"},
         "auto": {"type": "boolean"}, "nightly_on": {"type": "boolean"}, "summary_on": {"type": "boolean"},
         "summary_hour": {"type": "integer"}, "repo": {"type": "string"}, "private": {"type": "boolean"}, "status": {"type": "string", "enum": ["active", "paused", "archived"]}},
         "required": ["action"]}})

GAMEDESK_LABELS = {"game_desk": "Game bana raha hoon", "game_studio": "Game project dekh raha hoon"}


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


def _brief_studio(v: dict) -> dict:
    keep = ("id", "number", "title", "goal", "status", "milestone", "counts", "auto", "night")
    out = {k: v.get(k) for k in keep if v.get(k) not in (None, "", [], {})}
    out["milestones"] = [{k: m.get(k) for k in ("key", "name", "done", "total", "pct", "target")} for m in v.get("milestones") or []]
    g = v.get("game") or {}
    out["game"] = {k: g.get(k) for k in ("number", "status", "say", "play_url", "version") if g.get(k)}
    tasks = v.get("tasks") or (v.get("review", []) + v.get("next", []))
    show = [t for t in tasks if t.get("status") in ("working", "review", "blocked")] + \
           [t for t in tasks if t.get("status") == "todo"][:8]
    out["tasks"] = [{k: t.get(k) for k in ("number", "title", "status", "milestone", "priority", "error", "notes", "version")
                     if t.get(k) not in (None, "", 0)} for t in show[:16]]
    if v.get("decisions"):
        out["decisions"] = [f"{d['text']} - {d['why']}" if d.get("why") else d["text"] for d in v["decisions"][:6]]
    return out


async def game_studio(ctx: Ctx, action="", id="", game="", brief="", orientation="portrait", title="", goal="", task="",
                      detail="", milestone="", priority=2, note="", words="", text="", why="", q="", n=0, auto=None,
                      nightly_on=None, summary_on=None, summary_hour=None, status="", repo="", private=True, **_):
    from ..employee import hire
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer hired nahi hai: Employees mein ek tap mein hire kijiye, phir game project chalega.")
    reads = ("list", "status", "why", "summary")
    if action not in reads and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Game project badalna sirf owner ka kaam hai.")
    run = asyncio.to_thread
    try:
        if action == "new":
            return _brief_studio(await run(S.create, t, ctx.conversation_id, title, goal, game, brief, orientation, ctx.actor))
        if action == "list":
            return {"projects": [_brief_studio(v) for v in await run(S.studios, t)]}
        if not id:
            mine = await run(S.studios, t)
            if len(mine) == 1:
                id = mine[0]["id"]
            else:
                raise ToolError("Kaunsa project? id / number (S-0001) dijiye; action=list se dekhiye.")
        if action == "status":
            return _brief_studio(await run(S.get, t, id))
        if action == "add":
            return {"added": await run(S.add_task, t, id, title or words, detail, milestone, "feature", priority or 2),
                    "note": "Added to To do. It builds when started (action=start) or by itself if the project is on auto."}
        if action == "plan":
            res = await run(S.plan, t, id, words)
            return {"made": [f"{x['number']} [{x['milestone']}] {x['title']}" for x in res["made"]],
                    "note": "Show her these in a short list; she can drop or change any. Nothing is built yet."}
        if action == "start":
            return {"started": await run(S.start_task, t, id, task),
                    "note": "Building in the background; it will wait for her OK. Do not poll in a loop."}
        if action == "ok":
            res = await run(S.approve_task, t, id, task, note)
            return {"done": res["done"], "next": (res.get("next") or {}).get("number", ""), "studio": _brief_studio(res["studio"])}
        if action == "back":
            return _brief_studio(await run(S.reject_task, t, id, task, note))
        if action == "drop":
            return {"task": await run(S.edit_task, t, id, task, status="dropped")}
        if action == "decide":
            return _brief_studio(await run(S.decide, t, id, text or note, why))
        if action == "why":
            return await run(S.why, t, id, q or words or text)
        if action == "summary":
            return {"summary": await run(S.summary, t, id)}
        if action == "nightly":
            return {"night": await run(S.nightly, t, id)}
        if action == "restore":
            return _brief_studio(await run(S.restore, t, id, int(n or 0)))
        if action == "github":
            from ..gamedesk import github as GGH
            from ..site.github import GithubError
            try:
                card = await run(GGH.request, t, id, repo, bool(private), ctx.conversation_id)
            except GithubError as e:
                raise ToolError(f"GitHub: {e} (GitHub token Hoola app > Website > GitHub mein daaliye)")
            return {"card": card["say"], "note": "The card is on her screen; only her tap pushes."}
        if action == "settings":
            return _brief_studio(await run(S.settings, t, id, title=title, goal=goal, auto=auto, nightly_on=nightly_on,
                                           summary_on=summary_on, summary_hour=summary_hour, status=status or None))
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = new | list | status | add | plan | start | ok | back | drop | decide | why | summary | "
                    "nightly | restore | settings | github")


GAMEDESK_HANDLERS = {"game_desk": game_desk, "game_studio": game_studio}
