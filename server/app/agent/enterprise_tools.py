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
from .tools import Ctx, ToolError

_DO_ACTIONS = ["connect", "disconnect", "project", "project_update", "draft", "revise", "file", "item",
               "item_update", "settings"]
_SEE_WHAT = ["day", "systems", "projects", "papers", "paper", "items", "settings", "rules"]


def _do_description(key: str, spec: dict[str, Any]) -> str:
    arts = " | ".join(spec["artifacts"])
    syss = " | ".join(spec["systems"])
    d = (f"{spec['label']}: {spec['say']}. "
         f"action=connect: system ({syss}), env test|production, account, note - she links her OWN system from the "
         f"app; a key or token in chat is refused. action=disconnect: system. "
         f"action=project: title, goal. action=project_update: ref, title / goal / status open|done|parked. "
         f"action=draft: kind ({arts}), about (what she said), project, note -> the working paper, with a `missing` "
         f"list for anything not known (a number that did not come from a system or from her is NEVER invented). "
         f"action=revise: ref, instruction. action=file: ref -> Word file. "
         f"action=item: title, kind task|gap|risk|due|finding, detail, owner, due YYYY-MM-DD, severity high|medium|low, "
         f"rupaye, project, source. action=item_update: ref, status open|doing|done|dropped, + any field. "
         f"action=settings (owner only): company, env_default, rules.")
    if spec["cap"]:
        d += " YAHAN TAK: " + spec["cap"]
    if not spec["writes"]:
        d += " Yeh kaam kisi bahar ke system mein kuch likhta nahi - sirf padhta aur kaagaz banata hai."
    return d


def _see_description(key: str, spec: dict[str, Any]) -> str:
    return (f"Read {spec['label']} work (nothing changes). what=day (khule kaam, nikli tareekhen, bade khatre) | "
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
            "detail": {"type": "string"}, "owner": {"type": "string"}, "due": {"type": "string"},
            "severity": {"type": "string"}, "rupaye": {"type": ["number", "string"]},
            "source": {"type": "string"}, "company": {"type": "string"}, "env_default": {"type": "string"},
            "rules": {"type": "string"}},
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


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, role: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..enterprise import service as S
    if (getattr(ctx, "actor", "owner") or "owner").startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi hai.")
    t, conv = ctx.tenant_id, ctx.conversation_id
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
            return S.draft(t, role, _s(a.get("kind")), _s(a.get("about")), _s(a.get("project")), _s(a.get("note")), conv)
        if action == "revise":
            return S.revise(t, role, _s(a.get("ref")), _s(a.get("instruction")), conv)
        if action == "file":
            return S.artifact_file(t, role, _s(a.get("ref")), conv)
        if action == "item":
            return S.add_item(t, role, _s(a.get("title")), _s(a.get("kind")) or "task", _s(a.get("detail")),
                              _s(a.get("owner")), _s(a.get("due")), _s(a.get("severity")), a.get("rupaye"),
                              _s(a.get("project")), _s(a.get("source")))
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
