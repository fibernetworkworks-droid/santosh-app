"""Product Sahayak tools (product manager). `product_dekho` only reads; `product` does the work.
Nothing goes outside (GitHub release, public page) from a tool: action=publish only makes the card, her app tap sends it.
Numbers for scoring are hers only; a missing one comes back as a question. GitHub tokens are never taken in chat."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

PRODUCT_TOOLS = [
    {"name": "product", "description": (
        "Product manager's coworker: feedback -> roadmap -> specs -> release notes. action=harvest (days): read Feedback Sahayak "
        "themes, Seva support tickets / unanswered questions and Telecaller objections into the opportunity backlog (same "
        "problem = joined, never doubled). action=idea: text or file_id (her ideas / notes; source=competitor + competitor name "
        "for competitor notes) -> customer problems. action=opportunity: title, problem, who, quote, note. action=update: ref, "
        "title / problem / who / theme / goal (KPI) / note / status. action=score: ref + HER numbers only: reach (people in 3 "
        "months), impact 3|2|1|0.5|0.25, confidence 100|80|50, effort ('2 hafte', '1 mahina', person-months); ICE: ice_impact, "
        "ice_confidence, ease 1-10; use_seen=true ONLY when she says use the people seen in the evidence as reach. NEVER invent a "
        "number: ask her. action=kano: ref + answers [[functional, dysfunctional]] (pasand / zaroori / farak nahi / chalega / bura) "
        "or category. action=solution: ref, text, assumption, chosen. action=merge: ref, into. action=drop: ref, reason. "
        "action=depends: ref, on [refs], remove. action=place: ref, bucket now|next|later|none, theme. action=plan (apply=true to "
        "put the suggestion on the roadmap). action=roadmap_files. action=ship: ref, day. action=result: ref (before / after). "
        "action=spec: ref (opportunity), note -> PRD with Given/When/Then. action=spec_edit: spec, fields {section: value}. "
        "action=spec_revise: spec, instruction. action=spec_files: spec (Word + Markdown + .feature). action=tasks: spec (dev / QA "
        "task list for the Developer / QA Sahayak). action=release: version, text (what shipped), opps, since, github (merged PRs), "
        "day. action=release_edit: release, hinglish [lines], english [lines], title. action=release_files: release. "
        "action=publish: what release|roadmap, ref, dest github|page|copy, lang -> a CARD for her tap (never published by you). "
        "action=metric: kpi, value, day, note (her number). action=kpi*: name, definition, unit, target, better up|down, remove. "
        "action=settings*: product, who, scoring rice|ice, capacity {now, next, later} person-months, cycle_weeks, repo owner/name, "
        "app_ref, site_ref, north_star {name, definition, unit, target}, rules, morning_time. (* owner only)"),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["harvest", "idea", "opportunity", "update", "score", "kano", "solution", "merge", "drop",
                                               "depends", "place", "plan", "roadmap_files", "ship", "result", "spec", "spec_edit",
                                               "spec_revise", "spec_files", "tasks", "release", "release_edit", "release_files",
                                               "publish", "metric", "kpi", "settings"]},
         "days": {"type": "integer"}, "text": {"type": "string"}, "file_id": {"type": "string"}, "source": {"type": "string"},
         "competitor": {"type": "string"}, "ref": {"type": "string"}, "title": {"type": "string"}, "problem": {"type": "string"},
         "who": {"type": "string"}, "quote": {"type": "string"}, "note": {"type": "string"}, "theme": {"type": "string"},
         "goal": {"type": "string"}, "status": {"type": "string"}, "reach": {"type": ["number", "string"]},
         "impact": {"type": ["number", "string"]}, "confidence": {"type": ["number", "string"]}, "effort": {"type": ["number", "string"]},
         "ease": {"type": "number"}, "ice_impact": {"type": "number"}, "ice_confidence": {"type": "number"}, "use_seen": {"type": "boolean"},
         "answers": {"type": "array", "items": {}}, "category": {"type": "string"}, "assumption": {"type": "string"},
         "chosen": {"type": "boolean"}, "into": {"type": "string"}, "reason": {"type": "string"},
         "on": {"type": "array", "items": {"type": "string"}}, "remove": {"type": "boolean"}, "bucket": {"type": "string"},
         "apply": {"type": "boolean"}, "day": {"type": "string"}, "spec": {"type": "string"}, "fields": {"type": "object"},
         "instruction": {"type": "string"}, "version": {"type": "string"}, "opps": {"type": "array", "items": {"type": "string"}},
         "since": {"type": "string"}, "github": {"type": "boolean"}, "release": {"type": "string"},
         "hinglish": {"type": "array", "items": {"type": "string"}}, "english": {"type": "array", "items": {"type": "string"}},
         "what": {"type": "string"}, "dest": {"type": "string"}, "lang": {"type": "string"}, "kpi": {"type": "string"},
         "value": {"type": "number"}, "name": {"type": "string"}, "definition": {"type": "string"}, "unit": {"type": "string"},
         "target": {"type": "number"}, "better": {"type": "string"}, "product": {"type": "string"}, "scoring": {"type": "string"},
         "capacity": {"type": "object"}, "cycle_weeks": {"type": "integer"}, "repo": {"type": "string"}, "app_ref": {"type": "string"},
         "site_ref": {"type": "string"}, "north_star": {"type": "object"}, "rules": {"type": "string"}, "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "product_dekho", "description": (
        "Read product work (nothing changes). what=day | backlog (status now|next|later|open|shipped, q) | opportunity (ref: "
        "evidence, score, missing numbers, solutions, specs) | roadmap (Now / Next / Later, capacity, dependency problems) | plan "
        "(suggested roadmap, not applied) | duplicates | specs | spec (spec) | releases | release (release) | metrics (KPIs + "
        "shipped results) | prs (merged pull requests, since) | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "backlog", "opportunity", "roadmap", "plan", "duplicates", "specs", "spec",
                                             "releases", "release", "metrics", "prs", "settings", "rules"]},
         "status": {"type": "string"}, "q": {"type": "string"}, "ref": {"type": "string"}, "spec": {"type": "string"},
         "release": {"type": "string"}, "since": {"type": "string"}},
         "required": ["what"]}},
]
PRODUCT_LABELS = {"product": "Product ka kaam kar raha hoon", "product_dekho": "Roadmap aur specs dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


_SETTING_KEYS = ("product", "who", "scoring", "capacity", "cycle_weeks", "repo", "app_ref", "site_ref", "north_star", "rules", "morning_time")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..product import rules as R
    from ..product import service as S
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi hai.")
    t, conv = ctx.tenant_id, ctx.conversation_id
    blob = " ".join(_s(v) for v in a.values())
    if R.has_token(blob):
        raise ToolError("Token / key chat mein nahi: Product sahayak > Niyam mein app se jodiye. Jo token likha, use GitHub par badal dijiye.")
    ref = _s(a.get("ref"))
    try:
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return S.save_settings(t, **{k: a[k] for k in _SETTING_KEYS if k in a})
        if action == "kpi":
            if not _owner(ctx):
                raise ToolError("KPI sirf owner badalti hain.")
            return S.set_kpi(t, _s(a.get("name")), _s(a.get("definition")), _s(a.get("unit")), a.get("target"),
                             _s(a.get("better")) or "up", _s(a.get("kpi")), bool(a.get("remove")))
        if action == "harvest":
            return S.harvest(t, a.get("days"), conv)
        if action == "idea":
            return S.add_ideas(t, _s(a.get("text")), _s(a.get("file_id")), _s(a.get("source")) or "idea", _s(a.get("competitor")), conv)
        if action == "opportunity":
            return S.add_opportunity(t, _s(a.get("title")), _s(a.get("problem")), _s(a.get("who")), "her", _s(a.get("quote")),
                                     _s(a.get("note")), conv=conv)
        if action == "update":
            return S.update_opportunity(t, ref, **{k: a[k] for k in ("title", "problem", "who", "theme", "goal", "note", "status") if k in a})
        if action == "score":
            return S.score(t, ref, a.get("reach"), a.get("impact"), a.get("confidence"), a.get("effort"), a.get("ease"),
                           a.get("ice_impact"), a.get("ice_confidence"), bool(a.get("use_seen")))
        if action == "kano":
            return S.kano_set(t, ref, a.get("answers"), _s(a.get("category")))
        if action == "solution":
            return S.add_solution(t, ref, _s(a.get("text")), _s(a.get("assumption")), bool(a.get("chosen")))
        if action == "merge":
            return S.merge(t, ref, _s(a.get("into")))
        if action == "drop":
            return S.drop(t, ref, _s(a.get("reason")))
        if action == "depends":
            return S.set_depends(t, ref, a.get("on") or [], bool(a.get("remove")))
        if action == "place":
            return S.place(t, ref, _s(a.get("bucket")), _s(a.get("theme")))
        if action == "plan":
            if a.get("apply") and not _owner(ctx):
                raise ToolError("Roadmap lagana sirf owner.")
            return S.plan(t, bool(a.get("apply")))
        if action == "roadmap_files":
            return S.roadmap_files(t, conv)
        if action == "ship":
            return S.ship(t, ref, _s(a.get("day")))
        if action == "result":
            return S.before_after(t, ref)
        if action == "spec":
            return S.write_spec(t, ref, _s(a.get("note")), conv)
        if action == "spec_edit":
            return S.edit_spec(t, _s(a.get("spec")), a.get("fields") or {})
        if action == "spec_revise":
            return S.revise_spec(t, _s(a.get("spec")), _s(a.get("instruction")))
        if action == "spec_files":
            return S.spec_files(t, _s(a.get("spec")), conv)
        if action == "tasks":
            return S.tasks(t, _s(a.get("spec")))
        if action == "release":
            gh = a.get("github")
            return S.release_new(t, _s(a.get("version")), _s(a.get("text")), a.get("opps") or None, _s(a.get("since")),
                                 None if gh is None else bool(gh), _s(a.get("day")), conv)
        if action == "release_edit":
            return S.release_edit(t, _s(a.get("release")), a.get("hinglish"), a.get("english"), _s(a.get("title")))
        if action == "release_files":
            return S.release_files(t, _s(a.get("release")), conv)
        if action == "publish":
            return S.publish_request(t, _s(a.get("what")) or "release", _s(a.get("release")) or ref, _s(a.get("dest")) or "copy",
                                     _s(a.get("lang")) or "both", conv)
        if action == "metric":
            return S.metric_add(t, _s(a.get("kpi")), a.get("value"), _s(a.get("day")), _s(a.get("note")))
    except (S.ProductError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..product import rules as R
    from ..product import service as S
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh graahak ke liye nahi hai.")
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "backlog":
            return S.backlog(t, _s(a.get("status")), _s(a.get("q")))
        if what == "opportunity":
            return S.opportunity(t, _s(a.get("ref")))
        if what == "roadmap":
            return S.roadmap(t)
        if what == "plan":
            return S.plan(t, False)
        if what == "duplicates":
            return {"pairs": S.duplicates(t)}
        if what == "specs":
            return {"specs": S.specs(t)}
        if what == "spec":
            return S.spec(t, _s(a.get("spec")) or _s(a.get("ref")))
        if what == "releases":
            return {"releases": S.releases(t)}
        if what == "release":
            return S.release(t, _s(a.get("release")) or _s(a.get("ref")))
        if what == "metrics":
            return S.metrics(t)
        if what == "prs":
            return {"prs": S.merged_prs(t, _s(a.get("since")))}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "impact": R.IMPACT, "confidence": R.CONFIDENCE, "kano": R.KANO_LABEL,
                    "change_types": list(R.CHANGE_TYPES), "play_max": R.PLAY_MAX, "appstore_max": R.APPSTORE_MAX}
    except (S.ProductError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def product(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def product_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


PRODUCT_HANDLERS = {"product": product, "product_dekho": product_dekho}
