"""The ten Enterprise Systems & ERP jobs as agent tools.

Each job gets a pair - `<role>` does the work, `<role>_dekho` only reads - and all twenty are GENERATED from
`enterprise/rules.ROLES`, so a new job is a row in that table, never a new file. They are separate tools on
purpose: the Employee gate maps one tool to one duty (`employee/roles.duty_of`), so separate tools are what let
her set trust per job - ERP work and banking work are not the same risk.

A capped job (health_int, bank_int, regtech) carries its limit in its own description AND in every result, so
neither the model nor she can mistake how far it goes.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..enterprise import rules as R
from ..enterprise.run import MAX_ROWS
from .tools import Ctx, ToolError

_DO_ACTIONS = ["connect", "disconnect", "endpoint", "project", "project_update", "draft", "revise", "file", "item",
               "item_update", "settings",
               # v0.363 the real thing: read and write against her live system
               "read", "describe", "soql", "plan_write", "dry_run", "approve", "execute", "run_status",
               "runs", "rollback_plan", "resolve",
               # v0.389 the Salesforce config deploy (sfmeta): Tooling cannot change these in a live org
               "deploy_validate", "deploy_status", "deploy_go",
               # the sums: arithmetic on rows, never guessed by the model. Which ones a job gets is in SUMS.
               "critical_path", "capacity", "metrics", "raid", "readiness", "chase",
               "reorder", "dead_stock", "bom", "where_used", "reconcile", "due_calendar"]
_SEE_WHAT = ["day", "jobs", "systems", "endpoints", "runs", "run", "projects", "papers", "paper",
             "items", "settings", "rules"]


# Which job gets which sums, and the one-line help each adds to its own tool description. A job that is not here
# has no sums - the enterprise jobs whose work is judgement, not arithmetic.
SUMS: dict[str, tuple[str, ...]] = {
    "tpm": ("critical_path", "capacity", "metrics", "raid", "readiness", "chase"),
    "supply_opt": ("reorder", "dead_stock"),
    "plm": ("bom", "where_used"),
    "bank_int": ("reconcile",),
    "regtech": ("due_calendar",),
}

SUMS_HELP: dict[str, str] = {
    "tpm": ("action=critical_path: rows [{id, title, days, depends_on[], status, owner}] -> the longest chain, "
            "and a REFUSAL if the dependencies form a loop. action=capacity: rows [{owner, days, status}], "
            "days_available, per_owner -> who is over-committed and by how many days. action=metrics: rows "
            "[{created, started, done, escaped}], committed -> MEDIAN lead / cycle time, escaped, say-do %. "
            "action=raid: rows [{id, owner, due, severity, status, updated}], today, stale_days. "
            "action=readiness: gates [{name, ok, note, blocking}] -> go / no-go with failures NAMED. "
            "action=chase: rows [{id, owner, updated, status}], today, quiet_days."),
    "supply_opt": ("action=reorder: rows [{sku, sold, days, on_hand, lead_days, unit_cost, sold_daily[]}], "
                   "service_level 80|85|90|95|97|99, days_of_history -> reorder point, safety stock, what to "
                   "order NOW and the stockout date. Under 14 days of history it REFUSES rather than give a "
                   "number nobody should trust. action=dead_stock: rows [{sku, on_hand, unit_cost, last_sold, "
                   "sold}], days -> where the money is sitting still."),
    "plm": ("action=bom: rows [{parent, child, qty, unit_cost}], top, qty -> the flattened BOM, every part's "
            "total quantity, and the cost rolled up from the leaves; a BOM loop is REFUSED, and parts with no "
            "price are listed rather than silently counted as free. action=where_used: rows [{parent, child}], "
            "part -> every assembly a part ends up in, which is what a change order really asks."),
    "bank_int": ("action=reconcile: statement [{amount, date, ref, desc}], ledger [...], days, paise -> what "
                 "matched (by reference first, then amount AND a date inside the window - amount alone is how "
                 "reconciliations go wrong), what is only in the bank, what is only in the books, and the "
                 "difference. Each line is used once."),
    "regtech": ("action=due_calendar: rows [{name, due, owner, status, penalty_per_day, penalty_flat, rule}], "
                "today, ahead -> late, coming up, done, and the exposure - computed ONLY from penalty figures "
                "she gave. A filing with no figure is listed late with the amount blank, never a guessed fine."),
}


def _do_description(key: str, spec: dict[str, Any]) -> str:
    arts = " | ".join(spec["artifacts"])
    syss = " | ".join(spec["systems"])
    d = (f"{spec['label']}: {spec['say']}. "
         f"action=connect: system ({syss}), env test|production, account, note - she links her OWN system from the "
         f"app; a key or token in chat is refused. action=disconnect: system. "
         f"action=project: title, goal. action=project_update: ref, title / goal / status open|done|parked. "
         f"action=draft: kind ({arts}), job (the part of the desk this is - see <job>_dekho what=jobs; leave empty "
         f"when the job has no parts), about (what she said), project, note -> the working paper, with a `missing` "
         f"list for anything not known (a number that did not come from a system or from her is NEVER invented). "
         f"action=revise: ref, instruction. action=file: ref -> Word file. "
         f"action=item: title, kind task|gap|risk|due|finding, detail, owner, due YYYY-MM-DD, severity high|medium|low, "
         f"rupaye, project, source. action=item_update: ref, status open|doing|done|dropped, + any field. "
         f"action=settings (owner only): company, env_default, rules. "
         f"--- REAL WORK ON HER LIVE SYSTEM --- Reads run at once because they change nothing: action=read "
         f"(system, target, query, limit) for records; action=describe (system, what, api) for the SHAPE - objects, "
         f"fields, flows, permission sets; action=soql (system, query, api) for her own SELECT (anything but "
         f"SELECT is refused). `api` is data (records) or tooling (CONFIGURATION - objects, fields, flows: it can "
         f"break the org for everyone, so it is never routine and never the default). A WRITE IS NEVER ONE CALL: action=plan_write (system, target, verb "
         f"create|update|upsert, rows [objects], key_field, api, job, title) freezes the rows; action=dry_run (run) "
         f"shows before -> after row by row and touches nothing; action=approve (run, confirm_env) is HER tap and "
         f"is tied to those exact rows; action=execute (run, batch) posts them, safe to call again after a crash "
         f"because a done row is never posted twice; action=run_status / runs / rollback_plan. "
         f"Delete is refused at any size. Over {MAX_ROWS} rows in one go is refused - split it. A production write "
         f"needs confirm_env='production' as well as her tap. action=endpoint (owner only): her own system's "
         f"address when Composio does not carry it - the credential is typed in the APP, never here. "
         f"A row whose answer never arrived is marked 'pata nahi' and is NEVER re-sent on its own, because a "
         f"retry can post the same record twice: only she can look in the system and say, with "
         f"action=resolve (run, n, landed true|false).")
    if key == "crm_arch":
        # Salesforce REFUSES Tooling CRUD on these in a live org ("Save or update not supported in active
        # organizations"), so the model must know the other road exists or it will keep hitting a wall.
        d += (" --- CONFIGURATION IN A LIVE ORG --- Salesforce itself refuses Tooling writes to CustomField, "
              "CustomObject, ApexClass and ApexTrigger in an active org, and gives Profile, PermissionSet and "
              "Layout no REST write path at all. Those go by METADATA DEPLOY: action=deploy_validate "
              "(components [{type, name, body}], test_level) is the dry run - Salesforce checks every component "
              "and runs the tests and commits NOTHING; action=deploy_status (deploy) until done; "
              "action=deploy_go (deploy, confirm_env) is HER tap, which quick-deploys that same validation "
              "without re-running the tests (good for 10 days). Each component must bring its OWN complete "
              "file. A single FIELD cannot be deployed alone - it lives inside its object's file - so ask for "
              "the whole CustomObject or make that change in a sandbox.")
    if SUMS.get(key):
        d += (" --- THE SUMS, DONE IN CODE (never work these out yourself: a wrong number looks exactly as "
              "confident as a right one) --- " + SUMS_HELP[key])
    js = R.jobs_of(key)
    if js:
        d += (" Is desk ke hisse (action=draft mein `job`): "
              + ", ".join(f"{k} ({v['label']})" for k, v in js.items()) + ".")
    if spec["cap"]:
        d += " YAHAN TAK: " + spec["cap"]
    if not spec["writes"]:
        d += " Yeh kaam kisi bahar ke system mein kuch likhta nahi - sirf padhta aur kaagaz banata hai."
    return d


def _see_description(key: str, spec: dict[str, Any]) -> str:
    return (f"Read {spec['label']} work (nothing changes). what=day (khule kaam, nikli tareekhen, bade khatre) | "
            f"jobs (is desk ke saare hisse aur har hisse ke kaagaz) | "
            f"systems | projects (status) | papers (kind, project) | paper (ref) | items (kind, status, project) | "
            f"settings | rules.")


ENTERPRISE_TOOLS: list[dict[str, Any]] = []
ENTERPRISE_LABELS: dict[str, str] = {}

for _key, _spec in R.ROLES.items():
    ENTERPRISE_TOOLS.append({
        "name": _key,
        "description": _do_description(_key, _spec),
        "input_schema": {"type": "object", "properties": {
            "action": {"type": "string", "enum": _DO_ACTIONS},
            "system": {"type": "string"}, "env": {"type": "string"}, "account": {"type": "string"},
            "note": {"type": "string"}, "title": {"type": "string"}, "goal": {"type": "string"},
            "status": {"type": "string"}, "ref": {"type": "string"}, "kind": {"type": "string"},
            "about": {"type": "string"}, "project": {"type": "string"}, "instruction": {"type": "string"},
            "job": {"type": "string"},
            "detail": {"type": "string"}, "owner": {"type": "string"}, "due": {"type": "string"},
            "severity": {"type": "string"}, "rupaye": {"type": ["number", "string"]},
            "source": {"type": "string"}, "company": {"type": "string"}, "env_default": {"type": "string"},
            "rules": {"type": "string"},
            "target": {"type": "string"}, "query": {"type": "object"}, "limit": {"type": "integer"},
            "verb": {"type": "string"}, "rows": {"type": "array", "items": {"type": "object"}},
            "key_field": {"type": "string"}, "run": {"type": "string"}, "batch": {"type": "integer"},
            "confirm_env": {"type": "string"}, "base_url": {"type": "string"}, "auth_kind": {"type": "string"},
            "api": {"type": "string"}, "what": {"type": "string"},
            "days_available": {"type": "number"}, "per_owner": {"type": "object"},
            "committed": {"type": "integer"}, "today": {"type": "string"},
            "stale_days": {"type": "integer"}, "quiet_days": {"type": "integer"},
            "gates": {"type": "array", "items": {"type": "object"}},
            "service_level": {"type": "integer"}, "days_of_history": {"type": "integer"},
            "top": {"type": "string"}, "part": {"type": "string"}, "qty": {"type": "number"},
            "statement": {"type": "array", "items": {"type": "object"}},
            "ledger": {"type": "array", "items": {"type": "object"}},
            "paise": {"type": "boolean"}, "ahead": {"type": "integer"},
            # v0.389: resolve an unanswered row, and the Salesforce config deploy
            "n": {"type": "integer"}, "landed": {"type": "boolean"},
            "components": {"type": "array", "items": {"type": "object"}},
            "test_level": {"type": "string"}, "deploy": {"type": "string"},
            "header_name": {"type": "string"}},
            "required": ["action"]}})
    ENTERPRISE_TOOLS.append({
        "name": _key + "_dekho",
        "description": _see_description(_key, _spec),
        "input_schema": {"type": "object", "properties": {
            "what": {"type": "string", "enum": _SEE_WHAT},
            "kind": {"type": "string"}, "status": {"type": "string"}, "project": {"type": "string"},
            "ref": {"type": "string"}},
            "required": ["what"]}})
    ENTERPRISE_LABELS[_key] = f"{_spec['label']} ka kaam kar raha hoon"
    ENTERPRISE_LABELS[_key + "_dekho"] = f"{_spec['label']} ka kaam dekh raha hoon"

ENTERPRISE_ROLE_TOOLS = tuple(R.ROLES)
ENTERPRISE_READ_TOOLS = tuple(k + "_dekho" for k in R.ROLES)


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def rows_in(a: dict[str, Any]) -> list[Any]:
    return a.get("rows") if isinstance(a.get("rows"), list) else []


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, role: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..enterprise import service as S
    if (getattr(ctx, "actor", "owner") or "owner").startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi hai.")
    t_id, conv = ctx.tenant_id, ctx.conversation_id
    t = t_id
    try:
        S.guard_secret(" ".join(_s(v) for v in a.values()))
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            keys = {k: a[k] for k in ("company", "env_default", "rules") if k in a}
            return S.save_settings(t, role, **keys) if keys else S.settings(t, role)
        if action == "connect":
            if not _owner(ctx):
                raise ToolError("System sirf owner jodti hain.")
            return S.connect(t, role, _s(a.get("system")), _s(a.get("env")), _s(a.get("account")), _s(a.get("note")))
        if action == "disconnect":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return S.disconnect(t, role, _s(a.get("system")))
        if action == "project":
            return S.new_project(t, role, _s(a.get("title")), _s(a.get("goal")))
        if action == "project_update":
            return S.set_project(t, role, _s(a.get("ref")),
                                 **{k: a[k] for k in ("title", "goal", "status") if k in a})
        if action == "draft":
            return S.draft(t, role, _s(a.get("kind")), _s(a.get("about")), _s(a.get("project")), _s(a.get("note")),
                           conv, _s(a.get("job")))
        if action == "revise":
            return S.revise(t, role, _s(a.get("ref")), _s(a.get("instruction")), conv)
        if action == "file":
            return S.artifact_file(t, role, _s(a.get("ref")), conv)
        if action == "item":
            return S.add_item(t, role, _s(a.get("title")), _s(a.get("kind")) or "task", _s(a.get("detail")),
                              _s(a.get("owner")), _s(a.get("due")), _s(a.get("severity")), a.get("rupaye"),
                              _s(a.get("project")), _s(a.get("source")))
        # ---- the TPM's sums: arithmetic on rows, in code (enterprise/tpm.py)
        if action in ("critical_path", "capacity", "metrics", "raid", "readiness", "chase",
                      "reorder", "dead_stock", "bom", "where_used", "reconcile", "due_calendar"):
            if action not in SUMS.get(role, ()):
                raise ToolError(f"'{action}' is kaam ka hisaab nahi hai.")
            from ..enterprise import calc as CALC
            from ..enterprise import tpm as TPM
            try:
                if action == "reorder":
                    return CALC.reorder(rows_in(a), int(a.get("service_level") or 95),
                                        int(a.get("days_of_history") or 0))
                if action == "dead_stock":
                    return CALC.dead_stock(rows_in(a), int(a.get("days") or 90))
                if action == "bom":
                    return CALC.bom_explode(rows_in(a), _s(a.get("top")), float(a.get("qty") or 1))
                if action == "where_used":
                    return CALC.where_used(rows_in(a), _s(a.get("part")))
                if action == "reconcile":
                    stt = a.get("statement") if isinstance(a.get("statement"), list) else []
                    lgr = a.get("ledger") if isinstance(a.get("ledger"), list) else []
                    return CALC.reconcile(stt, lgr, int(a.get("days") or 3), bool(a.get("paise")))
                if action == "due_calendar":
                    return CALC.due_calendar(rows_in(a), _s(a.get("today")), int(a.get("ahead") or 30))
            except CALC.CalcError as ex:
                raise ToolError(str(ex))
            rows = rows_in(a)
            try:
                if action == "critical_path":
                    return TPM.critical_path(rows)
                if action == "capacity":
                    per = a.get("per_owner") if isinstance(a.get("per_owner"), dict) else None
                    return TPM.capacity(rows, float(a.get("days_available") or 10), per)
                if action == "metrics":
                    return TPM.delivery_metrics(rows, int(a.get("committed") or 0))
                if action == "raid":
                    return TPM.raid_sweep(rows, _s(a.get("today")), int(a.get("stale_days") or 14))
                if action == "readiness":
                    gates = a.get("gates") if isinstance(a.get("gates"), list) else rows
                    return TPM.release_readiness(gates)
                if action == "chase":
                    return TPM.chase(rows, _s(a.get("today")), int(a.get("quiet_days") or 3))
            except TPM.TpmError as ex:
                raise ToolError(str(ex))
        # ---- real work on her live system (enterprise/run.py holds the safety, not this layer)
        if action in ("read", "describe", "soql", "plan_write", "dry_run", "approve", "execute",
                      "run_status", "runs", "rollback_plan", "endpoint", "resolve",
                      "deploy_validate", "deploy_status", "deploy_go"):
            from ..enterprise import run as RUN
            try:
                if action == "endpoint":
                    if not _owner(ctx):
                        raise ToolError("Endpoint sirf owner jodti hain - aur credential app mein, chat mein nahi.")
                    raise ToolError("System ka address aur key app se jodiye (Enterprise > System jodo). "
                                    "Chat mein credential nahi li jaati.")
                if action == "read":
                    return RUN.read(t_id, role, _s(a.get("system")), _s(a.get("target")),
                                    a.get("query") if isinstance(a.get("query"), dict) else {},
                                    int(a.get("limit") or 200))
                if action == "describe":
                    return RUN.describe(t_id, role, _s(a.get("system")), _s(a.get("what")),
                                        _s(a.get("api")) or "data")
                if action == "soql":
                    return RUN.soql(t_id, role, _s(a.get("system")), _s(a.get("query") if isinstance(a.get("query"), str) else ""),
                                    _s(a.get("api")) or "data", int(a.get("limit") or 200))
                if action == "plan_write":
                    if not R.may_write(role):
                        raise ToolError("Yeh kaam kahin bahar likhta hi nahi.")
                    rows = a.get("rows")
                    if not isinstance(rows, list):
                        raise ToolError("rows ek list honi chahiye.")
                    return RUN.plan_write(t_id, role, _s(a.get("system")), _s(a.get("target")), _s(a.get("verb")),
                                          rows, _s(a.get("key_field")), _s(a.get("job")), _s(a.get("project")),
                                          _s(a.get("title")), _s(a.get("api")) or "data")
                if action == "dry_run":
                    return RUN.dry_run(t_id, _s(a.get("run")))
                if action == "approve":
                    if not _owner(ctx):
                        raise ToolError("Haan sirf owner deti hain.")
                    return RUN.approve(t_id, _s(a.get("run")), "owner", _s(a.get("confirm_env")))
                if action == "execute":
                    return RUN.execute(t_id, _s(a.get("run")), int(a.get("batch") or 25))
                if action == "run_status":
                    return RUN.status(t_id, _s(a.get("run")))
                if action == "runs":
                    return {"runs": RUN.runs(t_id, role)}
                if action == "rollback_plan":
                    return RUN.rollback_plan(t_id, _s(a.get("run")))
                if action == "resolve":
                    # only SHE can say whether an unanswered row landed; this is that answer coming back
                    if not _owner(ctx):
                        raise ToolError("Yeh sirf owner bata sakti hain - system mein dekhkar.")
                    if "landed" not in a:
                        raise ToolError("landed=true (chadh gayi thi) ya landed=false (nahi gayi) batana zaroori hai.")
                    return RUN.resolve(t_id, _s(a.get("run")), int(a.get("n") or 0), bool(a.get("landed")))
                if action == "deploy_validate":
                    comps = a.get("components")
                    if not isinstance(comps, list):
                        raise ToolError("components ek list honi chahiye: [{type, name, body}].")
                    return RUN.deploy_validate(t_id, role, comps, _s(a.get("test_level")))
                if action == "deploy_status":
                    return RUN.deploy_status(t_id, role, _s(a.get("deploy")))
                if action == "deploy_go":
                    if not _owner(ctx):
                        raise ToolError("Haan sirf owner deti hain.")
                    return RUN.deploy_go(t_id, role, _s(a.get("deploy")), "owner", _s(a.get("confirm_env")))
            except RUN.RunError as ex:
                raise ToolError(str(ex))
        if action == "item_update":
            return S.set_item(t, role, _s(a.get("ref")),
                              **{k: a[k] for k in ("title", "detail", "owner", "due", "severity", "status", "source")
                                 if k in a})
    except S.EnterpriseError as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, role: str, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..enterprise import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t, role)
        if what == "jobs":
            return S.jobs(role)
        if what == "endpoints":
            from ..enterprise import run as RUN
            return {"endpoints": RUN.endpoints(t, role)}
        if what == "runs":
            from ..enterprise import run as RUN
            return {"runs": RUN.runs(t, role)}
        if what == "run":
            from ..enterprise import run as RUN
            try:
                return RUN.status(t, _s(a.get("ref")))
            except RUN.RunError as ex:
                raise ToolError(str(ex))
        if what == "systems":
            return S.systems(t, role)
        if what == "projects":
            return {"kaam": S.projects(t, role, _s(a.get("status")))}
        if what == "papers":
            return {"kaagaz": S.artifacts(t, role, _s(a.get("kind")), _s(a.get("project")))}
        if what == "paper":
            return S.artifact(t, role, _s(a.get("ref")))
        if what == "items":
            return {"cheezein": S.items(t, role, _s(a.get("kind")), _s(a.get("status")), _s(a.get("project")))}
        if what == "settings":
            return S.settings(t, role)
        if what == "rules":
            spec = R.role(role)
            return {"niyam": list(spec["rules"]) + list(R.NEVER), "yahan_tak": spec["cap"],
                    "likh_sakta_hai": spec["writes"], "system": R.systems_for(role),
                    "kaagaz": spec["artifacts"]}
    except S.EnterpriseError as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


def _make(role: str):
    async def do(ctx: Ctx, action, **a: Any):
        return await asyncio.to_thread(_act, ctx, role, str(action), a)

    async def see(ctx: Ctx, what, **a: Any):
        return await asyncio.to_thread(_read, ctx, role, str(what), a)

    do.__name__, see.__name__ = role, role + "_dekho"
    return do, see


ENTERPRISE_HANDLERS: dict[str, Any] = {}
for _key in R.ROLES:
    _do, _see = _make(_key)
    ENTERPRISE_HANDLERS[_key] = _do
    ENTERPRISE_HANDLERS[_key + "_dekho"] = _see
