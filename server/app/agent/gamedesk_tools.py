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
        "Studio Project: her LONG game project around one Game Desk game - task board, milestones, decisions log, "
        "nightly build, morning report, and a CREW of 49 studio roles (each task has one: builders change the game, "
        "writers write a result). Every task = ONE small change with acceptance criteria; it WAITS for her OK. Actions: "
        "new (game = G-0001 or brief; title, goal) / list / status / add (title, detail, milestone, priority, role, "
        "criteria) / plan (words) / team (team, words): that team's roles plan linked tasks / start (task) / ok (task, "
        "note) / back (task, note): the version before plays again / drop / review (task): its lead checks screenshots + "
        "code against the criteria / gate (milestone_key): PASS|CONCERNS|FAIL|NOT ASSESSED counted in code, advice only / "
        "crew / decide (text, why) / why (q): answer ONLY from what it returns / summary / nightly / restore (n) / "
        "settings / github (repo, private): a card for her tap. Quote only returned verdicts and numbers. id = S-0001 "
        "(optional with one project). Only while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "list", "status", "add", "plan", "start", "ok", "back", "drop",
                                               "decide", "why", "summary", "nightly", "restore", "settings", "github",
                                               "crew", "team", "gate", "review"]},
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
         "summary_hour": {"type": "integer"}, "repo": {"type": "string"}, "private": {"type": "boolean"},
         "role": {"type": "string", "description": "action=add: a crew role key (optional; picked from the words)"},
         "criteria": {"type": "array", "items": {"type": "string"}, "description": "action=add: how 'done' is checked"},
         "team": {"type": "string"}, "milestone_key": {"type": "string"}, "status": {"type": "string", "enum": ["active", "paused", "archived"]}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_bible", "description": (
        "Game Bible of a Studio Project: the game's names and numbers as DATA (meta, style palette, glossary, player, "
        "curves, and entities: character, enemy, item, level, quest, screen). Every change is checked in code (types, "
        "ranges, references, palette, banned words, no real money); the game reads it (HoolaBible.DATA). Actions: show / "
        "template (kind) / set (kind, entity = JSON object; her edit, applies at once) / remove (kind, eid) / section "
        "(section, value) / seed: first Bible from the design doc as a DRAFT / generate (kind, n, words): a DRAFT - names "
        "from the model, numbers from the curves / accept (ids optional) / reject / check / simulate: seeded balance runs "
        "(win rate per level, spikes, levels to afford items) - quote ONLY its numbers / apply: the Bible into the live "
        "game with no new code / recurve (kind). Show a draft to her and ask before accept. id = S-0001 (optional with "
        "one project). Only while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["show", "template", "set", "remove", "section", "seed", "generate", "accept",
                                               "reject", "check", "simulate", "apply", "recurve"]},
         "id": {"type": "string", "description": "Studio project (S-0001)"},
         "kind": {"type": "string", "enum": ["character", "enemy", "item", "level", "quest", "screen"]},
         "entity": {"type": "object", "description": "action=set: the entry, e.g. {id, name, tier, behaviour, color}"},
         "eid": {"type": "string"}, "section": {"type": "string", "enum": ["meta", "style", "terms", "player", "curves", "economy"]},
         "value": {"type": "object"}, "n": {"type": "integer"}, "words": {"type": "string"},
         "ids": {"type": "array", "items": {"type": "string"}}, "runs": {"type": "integer"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_assets", "description": (
        "Asset pipeline of a Studio Project: the game's art (sprite, icon, ui, background - style-locked to the Game "
        "Bible palette), sounds (sfx made in code: free, preset + seed), music, voice lines and 3D models (Hoola's 3D "
        "Studio). Every file is checked in code and enters the game only after her OK. Actions: list / suggest (what the "
        "Bible still needs) / make (kind, key, words; sprite size, quality fast|best, palette_lock check|strict; sfx preset, "
        "seed; voice text) - PAID kinds (pictures, music, voice) only get a PRICE CARD: tell her the rupees and that her "
        "tap on the card starts it, you can never start a paid one / approve (key, v optional) / reject (key) / apply: "
        "approved assets into the live game with no new code. Keys follow the Bible ids (enemy red_bat -> sprite red_bat, "
        "level l1 -> bg_l1, sounds sfx_jump). id = S-0001 (optional with one project). Only while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "suggest", "make", "approve", "reject", "apply"]},
         "id": {"type": "string"}, "kind": {"type": "string", "enum": ["sprite", "icon", "ui", "background", "sfx", "music",
                                                                        "voice", "model"]},
         "key": {"type": "string"}, "words": {"type": "string"}, "size": {"type": "integer"},
         "quality": {"type": "string", "enum": ["fast", "best"]}, "palette_lock": {"type": "string", "enum": ["off", "check", "strict"]},
         "preset": {"type": "string"}, "seed": {"type": "integer"}, "text": {"type": "string"}, "v": {"type": "integer"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_qa", "description": (
        "QA farm + bug tracker of a Studio Project: Hoola's bots (idle, monkey, tapper, keys, restarter; seeded = "
        "repeatable) play a DEBUG web build on desktop / mid phone / low phone speeds, compare the start screen with the "
        "golden one she approved, measure fps / load / memory against the last run, and file numbered bugs with the "
        "exact bot + seed that finds them. Actions: run (background, 2-4 min; also every night after the nightly build) "
        "/ report (the last verdict PASS|CONCERNS|FAIL|NOT ASSESSED, quote only its facts) / bugs / report_bug (title, "
        "detail, severity crash|blocker|major|minor|visual|perf) / fix (bug = B-0001): a board task whose criterion is "
        "that the same bot no longer finds it - a bot bug is FIXED only when its bot cannot find it again / status (bug, "
        "status open|wontfix|duplicate) / golden: her OK that the last start screen is how the game should look. "
        "id = S-0001 (optional with one project). Only while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["run", "report", "bugs", "report_bug", "fix", "status", "golden"]},
         "id": {"type": "string"}, "bug": {"type": "string"}, "title": {"type": "string"}, "detail": {"type": "string"},
         "severity": {"type": "string", "enum": ["crash", "blocker", "major", "minor", "visual", "perf"]},
         "status": {"type": "string", "enum": ["open", "wontfix", "duplicate"]}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_release", "description": (
        "Platforms of a Studio Project: the live game as real downloads - linux / windows / macos (built on Hoola's "
        "server) and android (APK to install, AAB for Google Play; built in her private builds repo, signed with the "
        "game's own upload key). Each file is checked in code; macOS is not notarised and Windows not code-signed (the "
        "README says what players see). Actions: targets (where each platform can be built now) / build (platforms, "
        "android_format apk|aab; background) / list / store_kit (store texts for itch.io / Steam / Google Play within "
        "their limits, store images in exact sizes, AI disclosure, Steam upload scripts - a ZIP, nothing published) / "
        "rating (an IARC-style DRAFT; the real rating comes from IARC) / itch (release, target user/game): a CARD - only "
        "her tap uploads; her itch.io key is typed in the app, never in chat. Hoola never logs into her Steam or "
        "publishes alone. id = S-0001 (optional with one project). Only while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["targets", "build", "list", "store_kit", "rating", "itch"]},
         "id": {"type": "string"}, "platforms": {"type": "array", "items": {"type": "string", "enum": ["linux", "windows", "macos", "android"]}},
         "android_format": {"type": "string", "enum": ["apk", "aab"]}, "release": {"type": "string", "description": "R-001 or the id"},
         "target": {"type": "string", "description": "itch.io page: user/game"}},
         "required": ["action"]}})

GAMEDESK_LABELS = {"game_desk": "Game bana raha hoon", "game_studio": "Game project dekh raha hoon",
                   "game_bible": "Game Bible dekh raha hoon", "game_assets": "Game ke assets dekh raha hoon",
                   "game_qa": "Game ki QA dekh raha hoon", "game_release": "Game ki release dekh raha hoon"}

# v0.420 Phase 7 batch 1: the Game Desk ROLE PACKS - each its own employee, each gated on ITS hire
GAMEDESK_TOOLS.append(
    {"name": "game_world", "description": (
        "Procedural World Generation Engineer employee: makes a world from RULES and a SEED in code (no model, free) - "
        "kind terrain (island / map: biomes, rivers, villages), dungeon (rooms + corridors, exit), city (roads, blocks, "
        "buildings) or level (side-view platformer: gaps, steps, platforms, spikes, goal; jump_h / jump_w = her player's "
        "jump in tiles). Every world is CHECKED in code: made twice (same seed = same world), every village / room / exit "
        "/ goal reachable from the spawn, a level walked with her jump. Actions: make (words; or kind + params, seed, key, "
        "id = S-0001 to attach it to her game project) -> a DRAFT with preview + checks / list / status (world W-001) / "
        "approve / reject / demo (world): Hoola builds a walk-it link in Godot and plays it (background) / apply (id): "
        "the approved worlds go into her game as HoolaWorld, no new code. Quote only the checks and numbers it returns. "
        "Only while this employee is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["make", "list", "status", "approve", "reject", "demo", "apply"]},
         "words": {"type": "string", "description": "action=make: her world in her words"},
         "kind": {"type": "string", "enum": ["terrain", "dungeon", "city", "level"]},
         "params": {"type": "object", "description": "exact numbers, e.g. {w, h, sea, rivers, rooms, jump_h, jump_w}"},
         "seed": {"type": "integer"}, "key": {"type": "string", "description": "the name the game uses (default = kind)"},
         "id": {"type": "string", "description": "Studio project (S-0001) - attach / apply"},
         "world": {"type": "string", "description": "W-001 or the id"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_physics", "description": (
        "Physics Engine Developer employee: sets up her game's physics and PROVES it in the real engine (Godot run "
        "headless, free). Her numbers - fastest body speed (px/s), thinnest wall (px), physics ticks, gravity (px/s^2) - "
        "come from her words, the inputs, or her Game Bible's biggest 'speed'. Settings are worked out in code (ticks or "
        "cast-ray continuous collision so nothing tunnels: safe without CCD only when one step <= half the wall), then "
        "Hoola's lab checks free fall, projectile range, an elastic collision, tunnelling at HER speed (6 start points, "
        "with and without CCD), a box stack, a 3D drop, and the whole lab run twice - each against its formula. Actions: "
        "setup (words / inputs, id = S-0001) -> the lab runs in the background / list / status (setup P-001) / approve "
        "(only a PASS) / reject / apply (id): HoolaPhysics goes into her game. Quote only measured numbers. Fluids are "
        "not part of this yet - say so if asked. Only while this employee is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["setup", "list", "status", "approve", "reject", "apply"]},
         "words": {"type": "string"},
         "inputs": {"type": "object", "description": "{speed, wall, ticks, gravity, g3d}"},
         "id": {"type": "string", "description": "Studio project (S-0001)"},
         "setup": {"type": "string", "description": "P-001 or the id"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_world": "World bana raha hoon", "game_physics": "Game ki physics jaanch raha hoon"})


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
    out["tasks"] = [{**{k: t.get(k) for k in ("number", "title", "status", "milestone", "priority", "error", "version",
                                              "role_name", "verdict") if t.get(k) not in (None, "", 0)},
                     **({"notes": t["notes"][:600]} if t.get("notes") else {})} for t in show[:16]]
    if v.get("decisions"):
        out["decisions"] = [f"{d['text']} - {d['why']}" if d.get("why") else d["text"] for d in v["decisions"][:6]]
    return out


async def game_studio(ctx: Ctx, action="", id="", game="", brief="", orientation="portrait", title="", goal="", task="",
                      detail="", milestone="", priority=2, note="", words="", text="", why="", q="", n=0, auto=None,
                      nightly_on=None, summary_on=None, summary_hour=None, status="", repo="", private=True, role="",
                      criteria=None, team="", milestone_key="", **_):
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
        if action == "crew":
            from ..gamedesk import crew as CR
            ro = CR.roster()
            return {"count": ro["count"], "builds": ro["builds"], "note": ro["note"], "teams": [x["key"] for x in ro["teams"]],
                    "tiers": {x["label"]: [f"{r['key']} ({r['mode']})" for r in x["roles"]] for x in ro["tiers"]}}
        if not id:
            mine = await run(S.studios, t)
            if len(mine) == 1:
                id = mine[0]["id"]
            else:
                raise ToolError("Kaunsa project? id / number (S-0001) dijiye; action=list se dekhiye.")
        if action == "status":
            return _brief_studio(await run(S.get, t, id))
        if action == "add":
            crit = [{"text": c, "by": "screen"} for c in criteria] if isinstance(criteria, list) else None
            return {"added": await run(S.add_task, t, id, title or words, detail, milestone, "feature", priority or 2, "her",
                                       role, crit),
                    "note": "Added to To do. It builds when started (action=start) or by itself if the project is on auto."}
        if action == "plan":
            res = await run(S.plan, t, id, words)
            return {"made": [f"{x['number']} [{x['milestone']}] {x['title']}" for x in res["made"]],
                    "note": "Show her these in a short list; she can drop or change any. Nothing is built yet."}
        if action == "team":
            res = await run(S.plan, t, id, words, team)
            return {"made": [f"{x['number']} [{x['role_name']}] {x['title']}" for x in res["made"]],
                    "note": "Show her the team's tasks in a short list; nothing is built yet."}
        if action == "review":
            v = await run(S.review_task, t, id, task)
            return {"task": v["number"], "verdict": v["verdict"], "review": v["review"],
                    "criteria": [f"[{c['status']}] {c['text']}" for c in v["criteria"]]}
        if action == "gate":
            return await run(S.gate, t, id, milestone_key or milestone)
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


def _bible_short(v: dict) -> dict:
    d = v.get("data") or {}
    out = {"version": v.get("version"), "in_game": v.get("applied"), "counts": v.get("counts"),
           "errors": (v.get("check") or {}).get("errors", [])[:8], "warnings": (v.get("check") or {}).get("warnings", [])[:8],
           "meta": d.get("meta"), "palette": (d.get("style") or {}).get("palette"), "player": d.get("player"),
           "entities": {k: [{f: e.get(f) for f in ("id", "name", "tier", "order", "hp", "damage", "price", "behaviour", "effect")
                             if e.get(f) not in (None, "")} for e in rows][:25]
                        for k, rows in (d.get("entities") or {}).items() if rows}}
    dr = v.get("draft") or {}
    if dr:
        out["draft"] = {"kind": dr.get("kind"), "add": [{f: e.get(f) for f in ("id", "name", "tier", "hp", "damage", "price", "order")
                                                         if e.get(f) not in (None, "")} for e in dr.get("add") or []],
                        "errors": (dr.get("check") or {}).get("errors", [])[:6]}
        out["note"] = "A DRAFT waits: show it to her briefly and ask; only her yes = action=accept."
    if v.get("applied", 0) < v.get("version", 0):
        out["note_game"] = "The live game has an older Bible; action=apply rebuilds it with no new code."
    return out


async def game_bible(ctx: Ctx, action="", id="", kind="", entity=None, eid="", section="", value=None, n=3, words="",
                     ids=None, runs=0, **_):
    from ..employee import hire
    from ..gamedesk import bible as B
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer hired nahi hai: Employees mein ek tap mein hire kijiye.")
    if action not in ("show", "template", "check", "simulate") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Game Bible badalna sirf owner ka kaam hai.")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Kaunsa project? id (S-0001) dijiye; game_studio action=list se dekhiye.")
            id = mine[0]["id"]
        if action == "show":
            return _bible_short(await run(B.view, t, id))
        if action == "template":
            if kind not in B.KINDS:
                raise ToolError("kind = " + ", ".join(B.KINDS))
            return {"kind": kind, "fields": {f: {"type": ty, "default": d, **o} for f, (ty, d, o) in B.KINDS[kind]["fields"].items()},
                    "note": "Numbers of enemy / item / level come from the curves by tier; set only to override."}
        if action == "set":
            return _bible_short(await run(B.set_entity, t, id, kind, entity if isinstance(entity, dict) else {}))
        if action == "remove":
            return _bible_short(await run(B.remove_entity, t, id, kind, eid))
        if action == "section":
            return _bible_short(await run(B.set_section, t, id, section, value if isinstance(value, dict) else {}))
        if action == "seed":
            return _bible_short(await run(B.seed, t, id))
        if action == "generate":
            return _bible_short(await run(B.generate, t, id, kind, int(n or 3), words))
        if action == "accept":
            return _bible_short(await run(B.accept, t, id, list(ids) if ids else None))
        if action == "reject":
            return _bible_short(await run(B.reject, t, id))
        if action == "check":
            v = await run(B.view, t, id)
            return {"errors": v["check"]["errors"], "warnings": v["check"]["warnings"]}
        if action == "simulate":
            res = await run(B.sim, t, id, int(runs or B.SIM_RUNS))
            res["note"] = "Quote only these numbers. Same Bible = same numbers (seeded)."
            return res
        if action == "apply":
            await run(B.apply, t, id)
            return {"ok": True, "note": "Rebuilding the live game with the Bible (no new code); the card updates live."}
        if action == "recurve":
            return _bible_short(await run(B.recurve, t, id, kind))
    except (B.BibleError, G.GameError) as e:
        raise ToolError(str(e))
    raise ToolError("action = show | template | set | remove | section | seed | generate | accept | reject | check | "
                    "simulate | apply | recurve")


def _asset_short(v: dict) -> dict:
    return {"assets": [{k: a.get(k) for k in ("key", "kind", "status", "version", "approved", "cost_inr", "error")
                        if a.get(k) not in (None, "", 0)} | ({"problems": a["checks"].get("errors")} if (a.get("checks") or {}).get("errors") else {})
                       for a in v.get("assets", [])][:40],
            "price_card": v.get("card"), "in_game": v.get("in_game"), "spent_inr": v.get("spent_inr")}


async def game_assets(ctx: Ctx, action="", id="", kind="", key="", words="", size=0, quality="fast", palette_lock="check",
                      preset="", seed=0, text="", v=0, **_):
    from ..employee import hire
    from ..gamedesk import assets as A
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer hired nahi hai: Employees mein ek tap mein hire kijiye.")
    if action not in ("list", "suggest") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Game assets badalna sirf owner ka kaam hai.")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Kaunsa project? id (S-0001) dijiye.")
            id = mine[0]["id"]
        if action == "list":
            await run(A.collect_models, t, id)
            return _asset_short(await run(A.assets, t, id))
        if action == "suggest":
            sug = await run(A.suggest, t, id)
            return {"suggest": sug, "total_inr_if_all": sum(x["cost_inr"] for x in sug),
                    "note": "Nothing is made or priced yet; ask her which ones to make."}
        if action == "make":
            spec = {"size": size or None, "quality": quality, "palette_lock": palette_lock, "preset": preset or None,
                    "seed": seed or None, "text": text or None}
            a = await run(A.request, t, id, kind, key, words, **{k: x for k, x in spec.items() if x is not None})
            if a["status"] == "priced":
                return {"asset": a["key"], "status": "priced", "cost_inr": a["cost_inr"],
                        "note": f"A price card for about Rs {a['cost_inr']} is on her Assets page; ONLY her tap starts it. Never say it is made."}
            return {"asset": a["key"], "status": a["status"], "note": "Free kind: being made now; it waits for her OK."}
        if action == "approve":
            return {"asset": (await run(A.approve, t, id, key, int(v or 0)))["key"], "status": "approved",
                    "note": "Approved. action=apply puts the approved assets into the game."}
        if action == "reject":
            return {"asset": (await run(A.reject, t, id, key))["key"], "status": "rejected"}
        if action == "apply":
            await run(A.apply, t, id)
            return {"ok": True, "note": "Rebuilding the live game with the approved assets (no new code)."}
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = list | suggest | make | approve | reject | apply")


async def game_qa(ctx: Ctx, action="", id="", bug="", title="", detail="", severity="major", status="", **_):
    from ..employee import hire
    from ..gamedesk import qa as Q
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer hired nahi hai: Employees mein ek tap mein hire kijiye.")
    if action not in ("report", "bugs") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Game QA badalna sirf owner ka kaam hai.")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Kaunsa project? id (S-0001) dijiye.")
            id = mine[0]["id"]
        if action == "run":
            res = await run(Q.start, t, id)
            return {**res, "note": "The bots play in the background (2-4 minutes); the report lands on the QA page. Do not poll."}
        if action in ("report", "bugs"):
            d = await run(Q.bugs, t, id)
            last = d.get("last") or {}
            out = {"open": d["open"], "crash_open": d["crash_open"],
                   "last": {k: last.get(k) for k in ("at", "version", "verdict", "blockers", "concerns", "missing", "filed", "fixed", "perf")}}
            if action == "bugs":
                out["bugs"] = [{k: b.get(k) for k in ("number", "title", "severity", "status", "seen", "regression", "task")}
                               for b in d["bugs"][:30]]
            return out
        if action == "report_bug":
            return {"bug": await run(Q.report_bug, t, id, title, detail, severity)}
        if action == "fix":
            res = await run(Q.fix_bug, t, id, bug)
            return {"bug": res["bug"]["number"], "task": res["task"]["number"],
                    "note": "A board task now carries the fix; the bug closes only when the same bot cannot find it again."}
        if action == "status":
            return {"bug": await run(Q.set_bug, t, id, bug, status)}
        if action == "golden":
            return await run(Q.approve_golden, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = run | report | bugs | report_bug | fix | status | golden")


async def game_release(ctx: Ctx, action="", id="", platforms=None, android_format="apk", release="", target="", **_):
    from ..employee import hire
    from ..gamedesk import platforms as PF
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer hired nahi hai: Employees mein ek tap mein hire kijiye.")
    if action not in ("targets", "list", "rating") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Game release sirf owner ka kaam hai.")
    run = asyncio.to_thread
    try:
        if action == "targets":
            return {"targets": PF.targets()}
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Kaunsa project? id (S-0001) dijiye.")
            id = mine[0]["id"]
        if action == "build":
            v = await run(PF.release, t, id, list(platforms or []), android_format)
            return {"release": v["number"], "version": v["version_name"], "platforms": list(v["platforms"]),
                    "note": "Building in the background; downloads appear on the Release page. A platform that cannot be built here says why."}
        if action == "list":
            d = await run(PF.releases, t, id)
            return {"releases": [{"number": x["number"], "status": x["status"], "version": x["version_name"],
                                  "platforms": {k: {kk: v.get(kk) for kk in ("status", "mb", "note") if v.get(kk)} for k, v in x["platforms"].items()}}
                                 for x in d["releases"][:8]], "targets": {k: v["ready"] for k, v in d["targets"].items()}}
        if action == "store_kit":
            k = await run(PF.store_kit, t, id)
            return {k2: k[k2] for k2 in ("itch", "steam", "play", "ai_disclosure", "notes", "images")} | {
                "note": "Show her the texts briefly; the ZIP (images, Steam scripts) is on the Release page. Nothing was published."}
        if action == "rating":
            st = await run(S.get, t, id)
            return await run(PF.rating_draft, t, st["id"])
        if action == "itch":
            d = await run(PF.releases, t, id)
            rel = next((x for x in d["releases"] if x["number"] == str(release).upper() or x["id"] == release), None)
            if rel is None:
                raise ToolError("Kaunsi release? R-001 dijiye.")
            card = await run(PF.itch_card, t, id, rel["id"], target)
            return {"card": card["say"], "note": "The card waits for her tap on the Release page; you cannot upload."}
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = targets | build | list | store_kit | rating | itch")


def _owner_only(ctx: Ctx, what: str) -> None:
    if str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError(f"{what} sirf owner ka kaam hai.")


def _world_short(v: dict) -> dict:
    out = {k: v.get(k) for k in ("number", "key", "kind", "seed", "status", "version") if v.get(k) not in (None, "")}
    ch = v.get("checks") or {}
    out["checks"] = {"errors": ch.get("errors", []), "warnings": ch.get("warnings", []), "passed": ch.get("passed", [])[:6]}
    st = v.get("stats") or {}
    out["numbers"] = {k: st.get(k) for k in ("w", "h", "ms", "rivers", "rivers_to_sea", "rooms", "buildings", "reachable_share") if st.get(k) is not None}
    if (v.get("demo") or {}).get("status"):
        out["demo"] = {k: v["demo"].get(k) for k in ("status", "play_url", "errors", "numbers") if v["demo"].get(k)}
    return out


async def game_world(ctx: Ctx, action="", words="", kind="", params=None, seed=None, key="", id="", world="", **_):
    from ..employee import hire
    from ..gamedesk import service as G
    from ..gamedesk import world as W
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, W.KEY):
        raise ToolError("Procedural World Engineer hired nahi hai: Employees mein ek tap mein hire kijiye.")
    if action not in ("list", "status"):
        _owner_only(ctx, "World banana / badalna")
    run = asyncio.to_thread
    try:
        if action == "make":
            v = await run(W.make, t, words, kind, seed, params if isinstance(params, dict) else None, id, key)
            return _world_short(v) | {"note": ("Show her the checks in one or two lines and ask OK / another seed. The preview "
                                               "is on the World page; a walk-it link: action=demo.")}
        if action == "list":
            return {"worlds": [_world_short(v) for v in (await run(W.worlds, t, id))[:12]]}
        if action in ("status", "approve", "reject", "demo"):
            fn = {"status": W.get, "approve": W.approve, "reject": W.reject, "demo": W.demo}[action]
            v = await run(fn, t, world)
            out = _world_short(v)
            if action == "demo":
                out["note"] = "Building in the background; the walk-it link appears on the World page. Do not poll."
            return out
        if action == "apply":
            return await run(W.apply, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = make | list | status | approve | reject | demo | apply")


def _phys_short(v: dict) -> dict:
    lab = v.get("lab") or {}
    out = {"number": v.get("number"), "status": v.get("status"), "inputs": v.get("inputs"),
           "settings": {k: (v.get("settings") or {}).get(k) for k in ("ticks", "gravity", "ccd", "ccd_min_speed", "why")},
           "risk": v.get("risk"), "fluids": "not built yet"}
    if lab:
        out["lab"] = {"verdict": lab.get("verdict"), "passed": f"{lab.get('passed')}/{lab.get('total')}",
                      "cases": [{"case": c["case"], "ok": c["ok"], "note": c["note"]} for c in lab.get("cases", [])],
                      "before": (lab.get("before") or {}).get("say")}
    if v.get("error"):
        out["error"] = v["error"]
    if v.get("status") == "testing":
        out["note"] = "The lab runs in the background (well under a minute); its result shows on the Physics page. Do not poll."
    return out


async def game_physics(ctx: Ctx, action="", words="", inputs=None, id="", setup="", **_):
    from ..employee import hire
    from ..gamedesk import physics as P
    from ..gamedesk import service as G
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, P.KEY):
        raise ToolError("Physics Engine Developer hired nahi hai: Employees mein ek tap mein hire kijiye.")
    if action not in ("list", "status"):
        _owner_only(ctx, "Physics setup")
    run = asyncio.to_thread
    try:
        if action == "setup":
            return _phys_short(await run(P.setup, t, words, inputs if isinstance(inputs, dict) else None, id))
        if action == "list":
            return {"setups": [_phys_short(v) for v in (await run(P.setups, t, id))[:10]]}
        if action in ("status", "approve", "reject"):
            fn = {"status": P.get, "approve": P.approve, "reject": P.reject}[action]
            return _phys_short(await run(fn, t, setup))
        if action == "apply":
            return await run(P.apply, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = setup | list | status | approve | reject | apply")


GAMEDESK_HANDLERS = {"game_desk": game_desk, "game_studio": game_studio, "game_bible": game_bible, "game_assets": game_assets,
                     "game_qa": game_qa, "game_release": game_release, "game_world": game_world,
                     "game_physics": game_physics}
