"""v0.473 R2 APNA ENGINE - the agent tool `research_run`: Hoola's own research engine (`app/research/engine.py`).

The main model calls it ONCE with the sub-questions (R1's approved plan) and gets back a DOSSIER to write the report from:
per goal the notes (claim + the page's own words + whether those words were found on the page), the calculations with their
code, what stayed unresolved, and the numbered source list. It is a tool of the `research` family: in view only for a
research ask (`admit.plan_for`), owner / her own long job only (it spends model calls and fetches pages)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

RESEARCH_TOOLS = [
    {"name": "research_run", "description": (
        "Hoola's OWN research engine - use it for a research ask that needs several sources (a report, a market / rule / "
        "supplier / paper review, 'with sources'). Give the question and the sub-questions (4-6; if she approved a plan, "
        "exactly those). It runs one worker per sub-question in parallel - each searches, READS the real pages (primary "
        "sources first), records every finding with the page's own words (checked against the page), and works figures out "
        "in code - then a planner adds goals for real gaps or stops. It returns a DOSSIER: notes with [n] sources and "
        "whether each note's words were found on its page, calculations with their code, what could NOT be confirmed, and "
        "the source list. Write the report ONLY from the dossier: state a note marked NOT VERIFIED as unconfirmed, never as fact; "
        "cite only the listed sources; keep 'not confirmed' items in the report. Runs in the BACKGROUND (10-40 minutes): you get a run id back "
        "at once - tell her in one short line that it has started and she will get the report here when it is done, and END the turn "
        "(do not write findings now; the finished run wakes you to write the report). "
        "NOT for one quick fact (use google_search / web_sources) and NOT for Indian official statistics alone (use mospi)."),
     "input_schema": {"type": "object", "properties": {
         "question": {"type": "string", "description": "Her research question in one or two sentences"},
         "sub_questions": {"type": "array", "items": {"type": "string"},
                           "description": "4-6 questions, each answerable from sources; the approved plan's questions if she approved one"},
         "include_domains": {"type": "array", "items": {"type": "string"},
                             "description": "ONLY these sites (e.g. [\"gov.in\"]) - set only when she asked for specific sources"},
         "exclude_domains": {"type": "array", "items": {"type": "string"}, "description": "Never use these sites"},
         "after_date": {"type": "string", "description": "ISO date: prefer material on or after it"},
         "engine": {"type": "string", "enum": ["hoola", "parallel", "exa", "openai", "linkup"],
                    "description": "Which engine gathers. Default hoola (Hoola's own). A vendor engine runs only when SHE has enabled it; the answer is "
                                   "checked by Hoola against the cited pages either way. Omit unless she named one."},
         "mode": {"type": "string", "enum": ["background", "inline"],
                  "description": "background (default) = it starts and you reply with ONE short line; the report is written when the run "
                                 "finishes. inline = wait here (short jobs only)"}},
         "required": ["question", "sub_questions"]}},
    {"name": "research_status", "description": (
        "A background research run: check = progress (goals done, pages read), result = the DOSSIER of a finished run (write the report from it "
        "- same rules as research_run), stop = Rokiye. Use it when she asks how the research is going, and when a research run has finished "
        "and you are asked to write the report."),
     "input_schema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["check", "result", "stop"]},
                                                       "id": {"type": "string", "description": "the run id; empty = the latest run of this chat"}},
                      "required": ["action"]}},
]
RESEARCH_LABELS = {"research_run": "Research chala raha hoon (pages padh raha hoon)", "research_status": "Research ki haalat dekh raha hoon"}

_ALLOWED = ("owner", "goal", "routine", "wake")


def _deps(ctx: Ctx, settings: Any):
    """The real outside parts: the model, the web, the page reader, and the locked Python sandbox."""
    from .. import web
    from ..events import bus
    from ..research import engine as E
    from . import santosh

    async def llm(system: str, history: list[dict], tools: list[dict], max_tokens: int):
        brain = santosh.llm.choose(history)
        blocks, stop, _brain = await santosh._think(brain, system, history, settings, tools or None, None, max_tokens)
        return blocks, stop

    async def search(goal: str, queries: list[str]) -> list[dict]:
        try:
            r = await web.parallel_search(goal, queries)
            return list(r.get("sources") or [])
        except web.WebError as first:
            try:                                   # Parallel down: Google's own answer + its source pages
                g = await web.search_any(queries[0] if queries else goal)
            except web.WebError:
                raise first
            ex = g.get("excerpts") or []
            if ex:
                return list(ex)
            return [{"title": s.get("title", ""), "url": s.get("url", ""), "excerpt": ""} for s in (g.get("sources") or [])]

    async def fetch(url: str) -> dict:
        try:
            return await web.open_website(url)
        except web.WebError as e:
            raise ToolError(str(e))

    async def calc(code: str, purpose: str) -> dict:
        from ..pylab import service as PL
        try:
            r = await asyncio.to_thread(PL.run, ctx.tenant_id, code, [], [], ctx.conversation_id, purpose, 60, False)
        except Exception as e:                      # noqa: BLE001 - a failed calculation is a result the worker reads
            return {"ok": False, "output": str(e)[:400]}
        out = (r.get("stdout") or "") if r.get("ok") else (r.get("error") or r.get("stderr") or "")
        return {"ok": bool(r.get("ok")), "output": out}

    def emit(goal: str, state: str, label: str) -> None:
        bus.publish(ctx.conversation_id, "step", {"tool": "research", "label": label, "state": state,
                                                  "id": "rs-" + str(abs(hash(goal)) % 10**8), "args": {"goal": goal[:120]}})

    def stopped() -> bool:
        return ctx.conversation_id in santosh._stopped

    return E.Deps(llm=llm, search=search, fetch=fetch, calc=calc, stopped=stopped, emit=emit)


async def research_run(ctx: Ctx, question="", sub_questions=None, include_domains=None, exclude_domains=None,
                       after_date=None, mode=None, engine=None, **_) -> dict[str, Any]:
    from ..config import get_settings
    from ..research import engine as E
    st = get_settings()
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor not in _ALLOWED and not actor.startswith("approved:"):
        raise ToolError("Research chalana sirf malik ka kaam hai.")
    if not getattr(st, "research_engine_on", True):
        raise ToolError("Hoola ka research engine band hai. google_search / web_sources se kaam chalayiye.")
    q = str(question or "").strip()
    goals = [str(x).strip() for x in (sub_questions or []) if str(x).strip()] if isinstance(sub_questions, list) else []
    if not q and not goals:
        raise ToolError("Batayiye kya research karna hai (question aur sub_questions).")
    from ..research import bill as _bill
    try:                 # v0.476 R5: no room left today = refused before anything starts
        _bill.preflight(ctx.tenant_id)
    except _bill.ResearchCapped as e:
        raise ToolError(str(e))
    from ..research import vendors as _vend
    fell_back = ""
    if engine:
        eng = str(engine).lower()
    else:
        eng, _why = _vend.effective_engine(st)                   # v0.478 R7: the run-off's applied default, else Hoola's own
    okv, whyv = _vend.check(eng, ctx.tenant_id, st)               # v0.477 R6: a vendor engine runs only when every gate is open
    if not okv:
        if engine or str(getattr(st, "research_engine", "auto")).lower() != "auto":
            raise ToolError(whyv)                                 # she named it: tell her why it cannot run
        fell_back, eng = f"The default engine ({eng}) cannot run now: {whyv} Hoola's own engine is used instead.", "hoola"
    over = {"include_domains": include_domains if isinstance(include_domains, list) else None,
            "exclude_domains": exclude_domains if isinstance(exclude_domains, list) else None, "after_date": after_date}
    asked = E._URL.findall(q + " " + " ".join(goals))
    background = bool(getattr(st, "research_background", True)) if mode in (None, "") else str(mode) == "background"
    if eng != "hoola":
        background = True                                          # a vendor's run takes minutes and is polled: never inside a turn
    if background:       # v0.475 R4: persisted, worker-run, self-reporting
        from ..research import runner
        import re as _re
        hi = bool(_re.search(r"(?i)\b(karo|hai|ka|ke|ki|mein|chahiye|batao|aur|kya)\b|[\u0900-\u097F]", q + " " + " ".join(goals)))
        rid = runner.start(ctx.tenant_id, ctx.conversation_id, q or goals[0], goals, {k: v for k, v in over.items() if v}, hi, asked, eng)
        return {"started": True, "run_id": rid, "goals": len(goals) or 1, "engine": eng, **({"engine_note": fell_back} if fell_back else {}),
                "say": ("The research run has STARTED in the background (it takes 10-40 minutes and survives a restart). Tell her in ONE short "
                        "line, in her language, that it has started and that you will bring the report here when it is done; "
                        "do NOT write any findings now and do not call research_run again. Her stop word is Rokiye."),
                "check": "research_status check " + rid}
    pol = E.Policy.from_settings(st, **over)
    from .. import usage
    from ..research import store
    deps = _deps(ctx, st)
    meter = _bill.Meter(ctx.tenant_id, "")
    deps.afford, deps.cost = meter.afford, meter.breakdown            # v0.476 R5: the ceiling holds inline too

    base_step = deps.step

    def step(goal, kind, detail):
        if kind == "search":
            meter.counts["searches"] += 1
        elif kind == "read":
            meter.counts["fetches"] += 1
        base_step(goal, kind, detail)
    deps.step = step
    with usage.run_meter(meter.acc):
        d = await E.run(q or goals[0], goals, pol, deps, asked_urls=asked)
    try:                 # an inline run is a ledger row too, so today's total and the measured cost per goal include it
        rid = store.create(ctx.tenant_id, ctx.conversation_id, q or goals[0], goals, {"over": {}, "hi": False, "asked": asked, "inline": True})
        store.finish(rid, "done", d, cost=d.get("cost") or {})
    except Exception:    # noqa: BLE001 - a ledger that cannot be written never costs her the research
        pass
    E.remember(ctx.conversation_id, d)           # v0.474 R3: the report check reads it back
    s = d["stats"]
    if d.get("cost", {}).get("stopped_by_cost"):
        return {"dossier": E.render(d), "stats": s, "stop_reason": d["stop_reason"], "cost": d["cost"],
                "say": ("The run STOPPED at its cost ceiling and returned what it had - say so plainly in the report (what is covered and what is "
                        "not), and offer to continue with a higher ceiling if she wants more. Write only from the dossier; cite only its sources.")}
    if s["verified_notes"] == 0 and s["pages_read"] == 0:
        say = ("The engine found no readable pages for this. Say so plainly; do not write findings from memory. "
               "Offer to try other words, another source, or google_search.")
    else:
        say = ("Write the report from this dossier only. A note marked NOT VERIFIED is unconfirmed - say so. Keep what was "
               "NOT CONFIRMED in the report. Cite only the listed sources as [n] with their dates. Every figure you write must "
               "be one a note's words carry (cited to THAT source) or one a calculation printed - a figure from memory is "
               "refused by a check before she sees the report.")
    return {"dossier": E.render(d), "stats": s, "stop_reason": d["stop_reason"], "say": say}


async def research_status(ctx: Ctx, action="check", id="", **_) -> dict[str, Any]:
    """check / result / stop for a background run of THIS tenant (the latest of this chat when no id)."""
    from ..research import runner, store
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor not in _ALLOWED and not actor.startswith("approved:"):
        raise ToolError("Research ki haalat sirf malik dekh sakta hai.")
    action = str(action or "check").lower()
    rows = runner.status(ctx.tenant_id, "" if id else ctx.conversation_id, str(id or ""))
    if not rows:
        return {"note": "Is chat mein abhi koi research run nahi mila."}
    rid = rows[0]["id"]
    if action == "stop":
        got = runner.stop(ctx.tenant_id, rid)
        return {"note": {"stopped": "Research roka gaya - jo mil chuka hai woh bacha rahega.", "missing": "Yeh run nahi mila."}.get(
            got, f"Woh run pehle hi {got} ho chuka hai.")}
    if action == "result":
        from ..research import engine as E
        v = store.get(rid)
        if v is None or v["tenant"] != ctx.tenant_id:
            return {"note": "Yeh run nahi mila."}
        if v["dossier"] is None:
            return {"status": v["status"], "note": "Is run ka dossier abhi taiyaar nahi hai.", "progress": rows[0]["progress"]}
        E.remember(ctx.conversation_id, v["dossier"])           # the report check reads it back
        s = v["dossier"]["stats"]
        return {"dossier": E.render(v["dossier"]), "stats": s, "stop_reason": v["dossier"]["stop_reason"], "run_id": rid,
                "say": ("Write the report from this dossier only. A note marked NOT VERIFIED is unconfirmed - say so. Keep what was NOT CONFIRMED "
                        "in the report. Cite only the listed sources as [n] with their dates. Every figure must be one a note's words carry "
                        "(cited to THAT source) or one a calculation printed - a check refuses a figure from memory before she sees the report. "
                        "A PDF with doc_studio when she asked for a file or it is long; the chat then carries the summary + the file.")}
    return {"runs": rows[:3]}


RESEARCH_HANDLERS = {"research_run": research_run, "research_status": research_status}
