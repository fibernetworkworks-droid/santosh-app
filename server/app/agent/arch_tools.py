"""v0.410 ARCHITECTURE DESK tool: `software_architect` = the Principal Software Architect employee (archdesk/service.py).
Her system designed like a principal architect would: repo read first (read only), decisions (ADRs), diagrams, capacity
worked out in code, risks, roadmap, a PDF - then PRs read against the APPROVED design (posting = her tap only).
Only while the Architect is hired (Employees)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

KEY = "architect"

ARCH_TOOLS = [
    {"name": "software_architect", "description": (
        "Principal Software Architect employee (MASTER): any architecture job on HER software, as a peer-reviewed "
        "document with diagrams, ADRs, risks, roadmap, PDF + every number worked out in code. kind = design (a new "
        "system), assess (judge her EXISTING repo: scorecard, problems with evidence, module map + dependency cycles "
        "from the real imports - needs repo), migrate (modernise / move her existing system: phases with rollback, data "
        "move, cut-over - needs repo), decide (one technology choice: options x weighted criteria, ranked + sensitivity "
        "in code), threat (STRIDE threat model, risk scores + coverage gaps), scale (what breaks at 10x / 100x). Every "
        "design also gets boundary rules checked by code on her repo and on each PR, an OpenAPI contract (api.yaml) and "
        "design checks. action=new (kind, brief = what the system must do / who uses it / how many people a day in her "
        "words; repo = owner/name of her GitHub repo to read first, optional; scale = her numbers: dau, "
        "requests_per_user_per_day, peak_factor, write_ratio, record_kb, retention_days...) works in the background - "
        "tell her it is being designed and the desk shows it. action=status (id) / list. action=change (id, words) = the "
        "next version. action=approve (id, watch_prs) ONLY when she says so. action=review_pr (id, pr = number): reads "
        "that PR against the approved design and returns DRAFT findings - show them; action=post (review) puts them on "
        "the PR and needs HER tap in the desk, never call it on your own. Quote numbers only from the capacity sheet it "
        "returns; never invent scale. It never pushes, merges, deploys or runs her code."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "list", "status", "change", "approve", "review_pr", "watch", "cancel"]},
         "kind": {"type": "string", "enum": ["design", "assess", "migrate", "decide", "threat", "scale"],
                  "description": "action=new: which architecture job (default design)"},
         "brief": {"type": "string", "description": "action=new: the system in her words"},
         "repo": {"type": "string", "description": "action=new: her GitHub repo owner/name (optional)"},
         "scale": {"type": "object", "description": "her numbers: dau, requests_per_user_per_day, peak_factor, "
                                                   "write_ratio, avg_response_kb, record_kb, retention_days, replication, server_rps"},
         "id": {"type": "string", "description": "the design id (arch_...)"},
         "words": {"type": "string", "description": "action=change: what to change"},
         "watch_prs": {"type": "boolean", "description": "approve / watch: read new PRs against the design on its own"},
         "pr": {"type": "integer", "description": "action=review_pr: the PR number"}},
         "required": ["action"]}},
]
ARCH_LABELS = {"software_architect": "Architecture par kaam kar raha hoon"}


def _short(v: dict[str, Any]) -> dict[str, Any]:
    """What the model needs to talk about a design (the full doc stays on the desk)."""
    d = v.get("design") or {}
    cap = v.get("capacity") or {}
    out = {k: v.get(k) for k in ("id", "title", "kind", "status", "stage", "error", "version", "repo", "pdf", "api_yaml", "watch_prs")}
    x = v.get("extra") or {}
    if (x.get("decision_result") or {}).get("totals"):
        out["decision"] = {k: x["decision_result"].get(k) for k in ("winner", "margin", "robust", "flips", "totals")}
    if (x.get("threat_result") or {}).get("rows"):
        out["threats"] = {"total": x["threat_result"]["total"], "open_high": x["threat_result"]["open_high"],
                          "not_considered": x["threat_result"]["letters_unused"]}
    if x.get("scorecard_result"):
        out["scorecard"] = x["scorecard_result"]
    if (x.get("scenarios") or {}).get("breaks"):
        out["breaks_first"] = x["scenarios"]["breaks"]
    if x.get("review"):
        out["peer_review"] = {"issues": len(x["review"].get("issues") or []), "fixed": bool(x["review"].get("revised"))}
    if x.get("checks"):
        out["checks"] = f"{sum(1 for c in x['checks'] if c['ok'])}/{len(x['checks'])} pass"
    if x.get("fitness_now") is not None:
        out["boundary_breaks_today"] = len(x["fitness_now"])
    if d:
        out["summary"] = d.get("summary", "")[:1500]
        out["adrs"] = [f"{a.get('id')}: {a.get('title')} - {str(a.get('decision') or '')[:200]}" for a in d.get("adrs") or []][:10]
        out["top_risks"] = [f"{r.get('risk')} ({r.get('likelihood')}/{r.get('impact')})" for r in d.get("risks") or []][:6]
        out["open_questions"] = (d.get("open_questions") or [])[:8]
        out["diagrams"] = [f"{g.get('name')}: {'drawn' if g.get('ok') else 'not drawn - ' + str(g.get('error'))[:80]}"
                           for g in v.get("diagrams") or []]
    if cap.get("rows"):
        out["capacity"] = {r["what"]: r["value"] for r in cap["rows"]}
        out["capacity_assumed"] = cap.get("assumed") or []
    elif cap.get("error"):
        out["capacity"] = cap["error"]
    if v.get("reviews"):
        out["reviews"] = [{k: r.get(k) for k in ("id", "pr", "title", "status", "verdict")} for r in v["reviews"][:5]]
    return out


async def software_architect(ctx: Ctx, action="", brief="", repo="", scale=None, id="", words="", watch_prs=None,
                             pr=0, kind="design", **_):
    from ..archdesk import service as A
    from ..employee import hire
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("The Principal Software Architect is not hired: hire it in Employees with one tap, then design "
                        "banega.")
    if action not in ("list", "status") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Architecture work is for the owner only.")
    try:
        if action == "new":
            return _short(await asyncio.to_thread(A.start, t, ctx.conversation_id, brief, repo,
                                                  scale if isinstance(scale, dict) else {}, kind or "design"))
        if action == "list":
            return {"designs": await asyncio.to_thread(A.projects, t)}
        if not id:
            ps = await asyncio.to_thread(A.projects, t)
            if not ps:
                raise ToolError("There is no design yet; start with action=new.")
            id = ps[0]["id"]
        if action == "status":
            return _short(await asyncio.to_thread(A.get, t, id))
        if action == "change":
            return _short(await asyncio.to_thread(A.change, t, id, words))
        if action == "approve":
            return _short(await asyncio.to_thread(A.approve, t, id, watch_prs))
        if action == "watch":
            return _short(await asyncio.to_thread(A.settings, t, id, bool(watch_prs)))
        if action == "review_pr":
            r = await asyncio.to_thread(A.review_pr, t, id, int(pr or 0))
            return {**r, "note": "DRAFT findings - show her; they reach the PR only when she taps 'Post on PR' in the "
                                 "Architecture Desk."}
        if action == "cancel":
            return await asyncio.to_thread(A.cancel, t, id)
    except A.ArchError as e:
        raise ToolError(str(e))
    raise ToolError("action: new, list, status, change, approve, review_pr, watch or cancel.")


ARCH_HANDLERS = {"software_architect": software_architect}
