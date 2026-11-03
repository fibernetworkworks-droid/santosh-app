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
        "cite only the listed sources; keep 'not confirmed' items in the report. Takes several minutes. "
        "NOT for one quick fact (use google_search / web_sources) and NOT for Indian official statistics alone (use mospi)."),
     "input_schema": {"type": "object", "properties": {
         "question": {"type": "string", "description": "Her research question in one or two sentences"},
         "sub_questions": {"type": "array", "items": {"type": "string"},
                           "description": "4-6 questions, each answerable from sources; the approved plan's questions if she approved one"},
         "include_domains": {"type": "array", "items": {"type": "string"},
                             "description": "ONLY these sites (e.g. [\"gov.in\"]) - set only when she asked for specific sources"},
         "exclude_domains": {"type": "array", "items": {"type": "string"}, "description": "Never use these sites"},
         "after_date": {"type": "string", "description": "ISO date: prefer material on or after it"}},
         "required": ["question", "sub_questions"]}},
]
RESEARCH_LABELS = {"research_run": "Research chala raha hoon (pages padh raha hoon)"}

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
                       after_date=None, **_) -> dict[str, Any]:
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
    pol = E.Policy.from_settings(st, include_domains=include_domains if isinstance(include_domains, list) else None,
                                 exclude_domains=exclude_domains if isinstance(exclude_domains, list) else None,
                                 after_date=after_date)
    asked = E._URL.findall(q + " " + " ".join(goals))
    d = await E.run(q or goals[0], goals, pol, _deps(ctx, st), asked_urls=asked)
    E.remember(ctx.conversation_id, d)           # v0.474 R3: the report check reads it back
    s = d["stats"]
    if s["verified_notes"] == 0 and s["pages_read"] == 0:
        say = ("The engine found no readable pages for this. Say so plainly; do not write findings from memory. "
               "Offer to try other words, another source, or google_search.")
    else:
        say = ("Write the report from this dossier only. A note marked NOT VERIFIED is unconfirmed - say so. Keep what was "
               "NOT CONFIRMED in the report. Cite only the listed sources as [n] with their dates. Every figure you write must "
               "be one a note's words carry (cited to THAT source) or one a calculation printed - a figure from memory is "
               "refused by a check before she sees the report.")
    return {"dossier": E.render(d), "stats": s, "stop_reason": d["stop_reason"], "say": say}


RESEARCH_HANDLERS = {"research_run": research_run}
