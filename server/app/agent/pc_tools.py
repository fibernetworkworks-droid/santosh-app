"""Mera PC tools: the user's office/home computer through Santosh Desktop (files, printing, TallyPrime)."""
from __future__ import annotations

import logging

import asyncio
import time

from ..bazar import service
from ..bazar.connectors.base import ToolError as BazarError
from ..bazar.connectors.pc import SCHEMAS
from ..config import get_settings
from .tools import Ctx, ToolError

PACK = "pc-bridge"

_NAMES = {"pc_status": "status", "pc_search": "search", "pc_list": "list", "pc_read": "read",
          "pc_send_to_phone": "send_file", "pc_print": "print", "tally_report": "tally_report", "tally_entry": "tally_voucher"}

PC_TOOLS = [{"name": api, "description": "[HER PC - say 'aapka PC'] " + SCHEMAS[tool][0], "input_schema": SCHEMAS[tool][1]}
            for api, tool in _NAMES.items()]

PC_LABELS = {"pc_status": "PC dekh raha hoon", "pc_search": "PC par file dhoondh raha hoon", "pc_list": "PC ka folder dekh raha hoon",
             "pc_read": "File padh raha hoon", "pc_send_to_phone": "File phone par bhej raha hoon",
             "pc_print": "Print taiyar kar raha hoon", "tally_report": "Tally dekh raha hoon", "tally_entry": "Tally entry taiyar kar raha hoon"}

log = logging.getLogger("santosh.pcop")


def _handler(api: str):
    tool = _NAMES[api]

    async def h(ctx: Ctx, **args):
        try:
            return await asyncio.to_thread(service.run, ctx.tenant_id, ctx.conversation_id, PACK, tool, args)
        except BazarError as e:
            raise ToolError(str(e))
    return h


PC_HANDLERS = {api: _handler(api) for api in _NAMES}


# ---- Santosh uses the PC like a person (Santosh PC Operator) ----
PC_TOOLS.append({"name": "pc_do", "description": (
    "[HER PC - say 'aapka PC', never 'mera PC'] Santosh uses the user's OWN computer like a person: sees the screen, "
    "opens apps, clicks, types, presses keys, to finish a task end to end in ANY desktop app (Tally, Excel, Word, "
    "Chrome ON HER PC, Busy, Marg, email apps, any software). Use when the user wants something DONE on HER PC that the "
    "file/Tally tools can't do: 'Excel mein sales sheet banao', 'Tally kholo aur ledger dikhao', 'mere PC pe Chrome mein "
    "IRCTC kholo', 'laptop pe yeh site kholo', 'Word mein letter likho'. A website job she did NOT put on her PC goes to "
    "your own browser (browse_web / computer_operator), not here. "
    "Describe the full goal with every detail. The user watches it live; it asks on the phone before sending, "
    "submitting, deleting, paying, installing or changing settings, and never types passwords/OTPs. Needs 'Santosh "
    "ko PC chalane dein' switched on in Santosh Desktop. Slow (a few seconds per step). While her PC task runs, her "
    "follow-ups go here too (pc_do again): they steer THAT task - never hoola_pc_do / browse_web for them."),
    "input_schema": {"type": "object", "properties": {"task": {"type": "string"}, "model": {"type": "string", "enum": ["qwen", "sonnet"], "description": "Only when she names the PC model for this task (Qwen 3.8 Max / Sonnet 5.5); leave out = the server default."}, "pc": {"type": "string", "description": "Which of HER PCs, by her name for it ('office', 'ghar laptop'). Never a Hoola PC (that is hoola_pc_do). Leave out when she has one PC or did not say; pc_devices lists the names."}, "fresh": {"type": "boolean", "description": "Only for a completely NEW, different job while a PC task is running. Leave out for her follow-ups ('Chrome mein karo', 'yeh wala lo'): they go INTO the running task."}}, "required": ["task"]}})
PC_TOOLS.append({"name": "pc_task_result", "description": "[HER PC] Status or result of a pc_do task (session_id).",
                 "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}})
PC_LABELS.update({"pc_do": "Aapke PC par kaam kar raha hoon", "pc_task_result": "Aapke PC ka kaam dekh raha hoon"})


# ---- v0.193 HOOLA KA APNA PC: the Linux cloud computer that belongs to Hoola (the coworker VM) ----
PC_TOOLS.append({"name": "hoola_pc_do", "description": (
    "[HOOLA KA APNA PC - the cloud computer that belongs to YOU, the coworker] Use when the job needs desktop "
    "software she does not have ('ffmpeg se video compress karo', 'LibreOffice mein sheet banao', 'pandoc se "
    "convert karo'), a desktop app on screen, MANUAL WORK ON A GOVERNMENT / LEGACY PORTAL in Chrome that she hands "
    "over ('Hoola PC par GST portal pe yeh form bharo'), or when the user said 'aapke computer pe / tumhare PC pe / "
    "Hoola ke PC pe'. NOT for fetching, collecting or processing data / API lists / reports: use data_fetch, data_read, "
    "data_note and doc_studio on the server. Files the task makes or downloads (receipts, acknowledgement PDFs) come "
    "to HER CHAT (the PC sends them), and the task ends with a screenshot of the screen as proof. Every user gets a "
    "Hoola PC from a shared pool (her own folder and logins on it); if all are busy the task waits in line and starts "
    "by itself. The SAME portal job for many rows of her sheet = hoola_pc_batch, not this. Hoola uses its OWN Linux "
    "computer in the cloud like a person: sees the screen, opens apps, clicks, types, INSTALLS SOFTWARE (apt/pip, "
    "no permission needed - it is Hoola's own VM) and runs shell commands. "
    "While working there it can also use HER PC for FILES through the bridge: user_pc_search / user_pc_read / "
    "user_pc_pull bring one of her files into its VM (put that in the task when her file is the input: 'meri "
    "Excel Hoola ke PC pe kholo' = pull it first), user_pc_push hands a finished file back to her PC (she "
    "approves on the phone). "
    "Her-PC jobs ('mere PC pe') stay with pc_do; quick web look-ups stay with browse_web. Chromium is the browser here (her own Chrome is on HER PC: pc_do); "
    "files live in /data. Same safety rules as pc_do for anything that leaves the VM (sends, submits, pays). "
    "Describe the full goal with every detail. The user watches it live; it asks on the phone before sending, "
    "submitting, deleting or paying, and never types passwords/OTPs. Slow (a few seconds per step)."),
    "input_schema": {"type": "object", "properties": {"task": {"type": "string"}, "model": {"type": "string", "enum": ["qwen", "sonnet"], "description": "Only when she names the PC model for this task (Qwen 3.8 Max / Sonnet 5.5); leave out = the server default."}, "pc": {"type": "string", "description": "Which PC, by her name for it ('Hoola PC 2'); leave out = any FREE Hoola PC. Leave out when she has one PC or did not say; pc_devices lists the names."}, "fresh": {"type": "boolean", "description": "Only for a completely NEW job while a Hoola PC task of this chat runs; her follow-ups go INTO the running task."}}, "required": ["task"]}})
PC_LABELS.update({"hoola_pc_do": "Hoola ke apne PC par kaam kar raha hoon"})

# v0.885 REPEAT JOBS on Hoola PC (owner: "LEGACY PORTALS AND GOV PORTALS WHERE NEED A HUGE REPEATED MANUAL WORK" +
# "HUMAN IN LOOP"): the same portal job for every row of her sheet; row 1 she watches, then HER tap runs the rest.
PC_TOOLS.append({"name": "hoola_pc_batch", "description": (
    "[HOOLA PC - REPEAT JOB] The SAME manual job on a portal / website / desktop app for EVERY ROW of her Excel or CSV "
    "('is sheet ke har customer ka form portal pe bharo', '50 invoices ek ek karke upload karo'). action=start: task = "
    "the job written ONCE with {Column} blanks for what changes per row (column names exactly as in her sheet), "
    "file_id = her sheet from the chat (or rows = a list of objects). Row 1 runs first and she approves its submits "
    "like any task; then a confirm card asks HER to run the other rows (you can never approve it - only her tap). Then "
    "the rows run one by one on the same Hoola PC; money, deletes and OTPs still ask her. At the end one Excel with "
    "every row's result + proof screenshot comes to her chat. action=status / stop / resume (resume after a pause, "
    "when she says so) / go (shows her card again when she wants the rest to run). Give the batch_id from start."),
    "input_schema": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["start", "status", "go", "resume", "stop"]},
        "task": {"type": "string", "description": "start: the job once, with {Column} blanks"},
        "file_id": {"type": "string", "description": "start: her Excel / CSV in the chat"},
        "rows": {"type": "array", "items": {"type": "object"}, "description": "start: rows as objects, when there is no file"},
        "sheet": {"type": "string", "description": "start: which sheet of the Excel (default the first)"},
        "batch_id": {"type": "string"}}, "required": ["action"]}})
PC_LABELS.update({"hoola_pc_batch": "Hoola PC par repeat kaam chala raha hoon"})


async def hoola_pc_batch(ctx: Ctx, action="start", task="", file_id="", rows=None, sheet="", batch_id="", **_):
    from ..pc import batch
    try:
        if action == "start":
            r = await batch.create(ctx.tenant_id, ctx.conversation_id, task, file_id=str(file_id or ""), rows=rows,
                                   sheet=str(sheet or ""))
            r["say"] = (f"Tell her in one or two lines: {r['rows']} rows; row 1 is starting on Hoola PC now - she watches "
                        "it and approves its submit; after row 1 a card asks her to run the rest.")
            return r
        if not batch_id:
            jobs = batch.mine(ctx.tenant_id)
            if not jobs:
                raise ToolError("No repeat job yet.")
            batch_id = jobs[0]["id"]
        return await batch.control(ctx.tenant_id, str(batch_id), str(action))
    except batch.BatchError as e:
        raise ToolError(str(e))


async def hoola_pc_do(ctx: Ctx, task, pc="", model="", fresh=False, _wait=None, **_):
    from ..pc import operator
    from ..pc.hub import HOOLA_PC_KIND
    task = str(task or "").strip()
    if len(task) < 3:
        raise ToolError("Batayiye Hoola ke PC par kya karna hai")
    # v0.858 a follow-up while Hoola's PC works on this chat's task goes INTO that task (it started a parallel task on
    # another Hoola PC, or cancelled the running one and lost its progress)
    live = [o for o in operator.running_all(ctx.tenant_id) if o.kind == operator.HOOLA_PC_KIND
            and operator.same_chat(o.conv, ctx.conversation_id)]
    if live and not fresh:
        op = live[-1]
        op.notes.append("[Hoola] " + task[:1000])
        del op.notes[:-6]
        out = op.live()
        out.pop("timeline", None)
        out.update(where="Hoola ka apna PC - the SAME task that is already running", steered=True,
                   say="Her words went INTO the task already running on Hoola's PC. Tell her in one short line.")
        return out
    try:
        r = await operator.start(ctx.tenant_id, ctx.conversation_id, task, kind=HOOLA_PC_KIND, pc=str(pc or ""), brain=str(model or ""),
                                 wait=get_settings().pc_wait_seconds if _wait is None else float(_wait))
    except RuntimeError as e:
        if "PC_NOT_FOUND" in str(e):
            raise ToolError(str(e).split(": ", 1)[-1] + ". Ask her which PC, or call pc_devices.")
        if "HOOLA_PC_OFFLINE" in str(e):
            raise ToolError("Hoola ka apna PC abhi online nahi hai. Thodi der baad boliye.")
        if "PC_OFFLINE" in str(e):
            raise ToolError("Hoola ka apna PC abhi online nahi hai. Thodi der baad boliye.")
        raise ToolError(str(e))
    r.pop("timeline", None)
    r.setdefault("where", "Hoola ka apna PC (the cloud computer owned by Hoola, Linux + Chromium)")
    if r["status"] in ("running", "needs_confirm"):
        r["say"] = ("Still working on Hoola ke apne PC (live card in chat; a confirm card appears if a step needs "
                    "approval). The result is posted automatically; if asked before that, call pc_task_result with "
                    f"session_id '{r['session_id']}'.")
    return r


async def pc_do(ctx: Ctx, task, pc="", model="", fresh=False, _wait=None, **_):
    from ..pc import operator
    task = str(task or "").strip()
    if len(task) < 3:
        raise ToolError("Batayiye PC par kya karna hai")
    # v0.858 a pc_do while her PC task in THIS chat is still running = her follow-up ('Chrome mein karo', 'Margherita
    # lo') for THAT task: it goes into the running task, never a fresh task that throws the work away
    live = operator.live_for(ctx.tenant_id, ctx.conversation_id)
    if live is not None and operator.same_chat(live.conv, ctx.conversation_id) and live.kind != operator.HOOLA_PC_KIND and not fresh \
            and (not pc or str(pc).lower() in (live.device_name or "").lower() or str(pc) == live.device_id
                 or not live.device_name):
        # v0.861 her 11:29 pizza run: the chat brain re-sent its own instructions ('Step 3...', 'Status check only',
        # 'Do not repeat earlier steps') every 15-20 s; each one stopped the PC task to re-read. Words reach the task
        # once per ask of hers: a repeat inside the same ask (or a round with no ask of hers) is not passed in again.
        from .santosh import ASK_NOW
        key = (ASK_NOW.get() or "").strip()[:300]
        repeat = (key and key == live.hoola_key) or (not key and time.time() - live.hoola_at < 60)
        if repeat:
            log.info("pc_do repeat for running %s not passed in (same ask, chat %s)", live.id, ctx.conversation_id)
        else:
            operator.tell(ctx.tenant_id, ctx.conversation_id, task, hers=False)
            live.hoola_key, live.hoola_at = key, time.time()
            log.info("pc_do steered into running %s (chat %s)", live.id, ctx.conversation_id)
        wait = get_settings().pc_wait_seconds if _wait is None else float(_wait)   # v0.862 her reply never waits longer
        if wait > 0 and not live.done_event.is_set():
            try:
                await asyncio.wait_for(asyncio.shield(live.done_event.wait()), wait)
            except asyncio.TimeoutError:
                pass
        if not live.done_event.is_set():
            live.reported = True
        out = live.live()
        out.pop("timeline", None)
        out.update(where="Aapka PC (HER computer) - the SAME task that is already running", steered=not repeat,
                   say=(("The PC task already has these instructions; nothing new was passed in. " if repeat else
                         "Her words went INTO the PC task that is already running; no new task was started. ") +
                        ("It has finished - tell her its result." if live.done_event.is_set() else
                         "It is still working and posts its result to the chat by itself. Do NOT call pc_do again to "
                         "check on it or to repeat steps - only when SHE says something new. Tell her in one short "
                         "line that it is on it.")))
        return out
    other = [o for o in operator.running_all(ctx.tenant_id) if o.kind != operator.HOOLA_PC_KIND
             and not operator.same_chat(o.conv, ctx.conversation_id)]
    log.info("pc_do new task (chat %s, fresh=%s, running elsewhere=%s, running here=%s)", ctx.conversation_id,
             bool(fresh), [o.id for o in other], live.id if live is not None else "-")
    try:
        r = await operator.start(ctx.tenant_id, ctx.conversation_id, task, pc=str(pc or ""), brain=str(model or ""),
                                 wait=get_settings().pc_wait_seconds if _wait is None else float(_wait),
                                 replace=bool(fresh) or not other)
    except operator.PcBusy as e:
        raise ToolError(f"Her PC is busy with another task from a different chat ('{e.op.task[:80]}'). Ask her whether to "
                        "stop that one first (say which), or to wait; on her word call pc_do again with fresh=true.")
    except PermissionError as e:
        raise ToolError(str(e))
    except RuntimeError as e:
        if "PC_NOT_FOUND" in str(e):
            raise ToolError(str(e).split(": ", 1)[-1] + ". Ask her which PC, or call pc_devices.")
        if "PC_OFFLINE_HOOLA_ON" in str(e):
            raise ToolError("Her PC is offline (Santosh Desktop is not connected). Hoola's OWN cloud PC is online, but do "
                            "NOT move her job there by yourself: tell her her PC is off and ASK in one line whether to do "
                            "it on Hoola's own PC instead; only on her yes call hoola_pc_do.")
        if "PC_OFFLINE" in str(e):
            raise ToolError("Aapka PC offline hai. PC on karke Santosh Desktop kholiye (ya Santosh app > Mera PC se jodiye).")
        raise ToolError(str(e))
    r.pop("timeline", None)
    r.setdefault("where", "Aapka PC (HER computer, Santosh Desktop) - not your own browser")
    if r["status"] in ("running", "needs_confirm"):
        r["say"] = ("Still working on the PC (live card in chat; a confirm card appears if a step needs approval). The "
                    "result is posted to the chat automatically. Do NOT call pc_do again to check on it or to repeat its "
                    "steps (that interrupts it); if she asks for the status, call pc_task_result with session_id "
                    f"'{r['session_id']}'.")
    return r


async def pc_task_result(ctx: Ctx, session_id, **_):
    from ..pc import operator
    op = operator.get(ctx.tenant_id, str(session_id))
    if op is None:
        raise ToolError("That PC task isn't available any more.")
    if not op.done_event.is_set():
        try:
            await asyncio.wait_for(asyncio.shield(op.done_event.wait()), 4)
        except asyncio.TimeoutError:
            pass
    r = op.live()
    r.pop("timeline", None)
    return r


PC_HANDLERS.update({"pc_do": pc_do, "pc_task_result": pc_task_result, "hoola_pc_do": hoola_pc_do,
                    "hoola_pc_batch": hoola_pc_batch})


# ---- v0.836 DESKTOP TEAM + HOOLA PC TEAM: one agent per PC, several PCs at once ----
PC_TOOLS.append({"name": "pc_devices", "description": (
    "[HER PCs + HOOLA'S OWN PCs] Every computer online for her right now: its name, whether it is HER PC or one of "
    "Hoola's own cloud PCs, whether Hoola may drive it, and the task it is doing now (one task per PC). Call it "
    "before pc_team, or when she names a PC you do not know."),
    "input_schema": {"type": "object", "properties": {}}})
PC_TOOLS.append({"name": "pc_team", "description": (
    "[DESKTOP TEAM - several PCs at the SAME time] Run 2 or more screen jobs in parallel, ONE agent per PC: e.g. her "
    "office PC exports the Tally ledger while her home PC fills the Excel sheet, or two of Hoola's own PCs each check "
    "a different website. Use ONLY when the job really has separate screen parts on DIFFERENT computers (she named "
    "them, or the parts need desktop software and Hoola has several PCs). One PC never gets two parts (they would "
    "fight for the mouse) - give it one task that does both. Do the research / writing / data parts yourself on the "
    "server (crew_run / agent tools), and put only the on-screen parts here. pc = her name for the PC, or 'hoola' for "
    "any free Hoola PC; pc_devices lists them. A PC already busy is NOT interrupted: that part comes back 'busy'. "
    "Every PC shows its own live card; send / submit / pay / delete still waits for her tap on each. Results that "
    "are not ready inside the wait are posted to the chat one by one as each PC finishes."),
    "input_schema": {"type": "object", "properties": {
        "tasks": {"type": "array", "minItems": 1, "maxItems": 6, "items": {"type": "object", "properties": {
            "pc": {"type": "string", "description": "Her name for the PC, or 'hoola' / 'Hoola PC 2' for Hoola's own"},
            "task": {"type": "string", "description": "The full goal for THIS PC, every detail it needs"}},
            "required": ["pc", "task"]}},
        "goal": {"type": "string", "description": "One line: the whole job these parts belong to"}},
        "required": ["tasks"]}})
PC_LABELS.update({"pc_devices": "Checking which PCs are online", "pc_team": "Starting the desktop team"})

_HOOLA_WORDS = {"hoola", "hoola pc", "hoola ka pc", "hoola ka apna pc", "hoola's pc", "cloud", "cloud pc", "any hoola pc"}


def _team_max() -> int:
    try:
        return max(1, min(int(getattr(get_settings(), "pc_team_max", 4) or 4), 6))
    except Exception:
        return 4


async def pc_devices(ctx: Ctx, **_):
    from ..pc import operator
    from ..pc.hub import hub
    out = []
    for d in hub.devices(ctx.tenant_id):
        o = operator.busy(ctx.tenant_id, d["device_id"])
        out.append({**d, "busy": bool(o), "doing": (o.task[:120] if o else ""), "session_id": (o.id if o else "")})
    return {"pcs": out, "count": len(out), "team_max": _team_max(),
            "say": ("No PC is online. Her PC: open Hoola Desktop on it. Hoola's own PCs: the owner runs vps-ops pc_deploy."
                    if not out else "One task per PC. Use these names in pc_do / hoola_pc_do / pc_team.")}


async def pc_team(ctx: Ctx, tasks=None, goal="", _wait=None, **_):
    from ..pc import operator
    from ..pc.hub import HOOLA_PC_KIND, hub
    import secrets
    parts = [t for t in (tasks or []) if isinstance(t, dict) and len(str(t.get("task") or "").strip()) >= 3]
    if not parts:
        raise ToolError("Give each PC its task: tasks=[{pc, task}, ...]")
    cap = _team_max()
    if len(parts) > cap:
        raise ToolError(f"At most {cap} PCs work at once (pc_team_max). Merge parts or run the rest after.")
    tenant = ctx.tenant_id
    # 1. every part gets its OWN PC before anything starts (no half-started team on a bad name)
    taken: set[str] = set()
    plan: list[tuple[dict, object]] = []
    problems = []
    for t in parts:
        want = " ".join(str(t.get("pc") or "").lower().split())
        conn = None
        if want in _HOOLA_WORDS:
            hoola = [c for c in hub.online(tenant) if (c.info or {}).get("kind") == HOOLA_PC_KIND
                     and c.device_id not in taken]
            free = [c for c in hoola if operator.busy(tenant, c.device_id) is None]
            conn = (free or [None])[0]
            if conn is None:
                problems.append(f"'{t.get('pc') or 'hoola'}': no free Hoola PC left" +
                                (" (all busy)" if hoola else " (none online)"))
                continue
        else:
            conn = hub.find(tenant, want)
            if conn is None:
                problems.append(f"'{t.get('pc')}': no online PC by that name")
                continue
            if conn.device_id in taken:
                problems.append(f"'{t.get('pc')}': that PC already has a part - give it ONE task that does both")
                continue
            if (conn.info or {}).get("kind") != HOOLA_PC_KIND and not (conn.info or {}).get("control"):
                problems.append(f"'{t.get('pc')}': Hoola may not drive this PC (switch 'Hoola ko PC chalane dein' on there)")
                continue
        taken.add(conn.device_id)
        plan.append((t, conn))
    if problems and not plan:
        names = ", ".join(d["name"] for d in hub.devices(tenant)) or "none"
        raise ToolError("Desktop team could not start: " + "; ".join(problems) + f". Online PCs: {names}.")
    team = "pcteam_" + secrets.token_hex(5)
    head = f"[Team job: {str(goal).strip()[:300]}] " if str(goal or "").strip() else ""

    async def one(t, conn):
        try:
            r = await operator.start(tenant, ctx.conversation_id, head + str(t["task"]).strip(), wait=0,
                                     pc=conn.device_id, team=team, replace=False)
            return {"pc": str((conn.info or {}).get("name") or "PC"), "session_id": r["session_id"], "status": r["status"]}
        except operator.PcBusy as e:
            return {"pc": str((conn.info or {}).get("name") or "PC"), "status": "busy", "session_id": e.op.id,
                    "doing": e.op.task[:120], "say": "This PC is busy with another task; it was NOT interrupted."}
        except PermissionError as e:
            return {"pc": str((conn.info or {}).get("name") or "PC"), "status": "not_allowed", "error": str(e)[:200]}
        except Exception as e:
            return {"pc": str((conn.info or {}).get("name") or "PC"), "status": "failed", "error": str(e)[:200]}

    started = list(await asyncio.gather(*(one(t, c) for t, c in plan)))
    ops = [operator.get(tenant, r["session_id"]) for r in started if r.get("status") not in ("busy", "not_allowed", "failed")]
    ops = [o for o in ops if o is not None]
    wait = get_settings().pc_wait_seconds if _wait is None else float(_wait)
    if ops and wait > 0:
        try:
            await asyncio.wait_for(asyncio.gather(*(asyncio.shield(o.done_event.wait()) for o in ops)), wait)
        except asyncio.TimeoutError:
            pass
    for r in started:
        o = operator.get(tenant, r.get("session_id", ""))
        if o is not None and o.team == team:
            if not o.done_event.is_set():
                o.reported = True         # this PC's result arrives as its own note when it finishes
            r.update({"status": o.status, "step": o.step, "summary": o.summary if o.done_event.is_set() else ""})
    running = sum(1 for r in started if r.get("status") in ("running", "needs_confirm"))
    return {"team": team, "goal": str(goal or "")[:300], "parts": started, "skipped": problems,
            "running": running,
            "say": ("Each PC shows its own live card. " +
                    (f"{running} PC(s) still working: each one's result is posted to the chat when it finishes "
                     "(or check one with pc_task_result). Tell her in one line which PC is doing what. "
                     if running else "Every part has finished: merge their results into ONE answer for her. ") +
                    ("Some parts could not start - say which and why. " if problems or any(
                        r.get("status") in ("busy", "not_allowed", "failed") for r in started) else ""))}


PC_HANDLERS.update({"pc_devices": pc_devices, "pc_team": pc_team})
