"""QA Sahayak tools. `qa_dekho` only reads; `qa` writes test cases, runs checks on HER OWN sites / apps, logs and retests bugs.
Filing into her GitHub issues only makes a CARD (her tap files it); test-account passwords are never taken here (app only)."""
from __future__ import annotations

import asyncio
import re
from typing import Any

from .tools import Ctx, ToolError

QA_TOOLS = [
    {"name": "qa", "description": (
        "App tester (QA) for HER OWN websites / web apps / Hoola-built sites and apps. action=target_add: kind site (a Website "
        "Sahayak site: ref = site id / S-0001) | app (an App Sahayak design prototype: ref = app id / A-0001) | apk (Android "
        "preview: manual checklist) | url (her own website: url; ownership must be proved by DNS TXT / meta tag / file, or it is "
        "her live Hoola host), name, govt_facing, sector general|govt|securities|bank|health|edu. action=verify: target (after she "
        "added the TXT / meta / file). action=discover: target (opens it in Chromium, notes pages / forms / screens). "
        "action=write: target, text (her spec / requirements in her words: DATA), file_ids (PRD / spec file) -> test cases (code "
        "cases from what was found + cases for her requirements; steps only in the safe step language). action=case_add: target, "
        "title, steps (step language JSON list, see qa_dekho what=steps; [] = manual), steps_text, expected, type, priority, area, "
        "viewport, account. action=case_edit: case + fields. action=case_retire: case. action=run: target, which all|smoke|"
        "regression|failed|<type>, cases (ids / numbers) -> runs in the background, result comes as a card (don't poll). "
        "action=mark: case, result pass|fail|blocked, note (manual / APK cases she checked herself). action=bug: bug, status "
        "fixed|open|wont_fix|duplicate|closed, reason, duplicate_of, severity. action=retest: bug (runs its case again). "
        "action=ready: target (release readiness). action=github: bug, repo owner/name -> ONLY a card for her tap (never say it "
        "is filed). action=register (Excel + Jira CSV). action=target_edit: target, name, govt_facing, sector, schedule HH:MM "
        "(daily regression), allow_writes (owner; staging sites only). action=target_remove / settings (owner). Never asks for a "
        "password (test accounts are typed in the app), never tests someone else's site, never pays."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["target_add", "target_edit", "target_remove", "verify", "discover", "write", "case_add",
                                               "case_edit", "case_retire", "run", "mark", "bug", "retest", "ready", "github", "register",
                                               "settings"]},
         "kind": {"type": "string"}, "ref": {"type": "string"}, "url": {"type": "string"}, "name": {"type": "string"},
         "govt_facing": {"type": "boolean"}, "sector": {"type": "string"}, "allow_writes": {"type": "boolean"},
         "schedule": {"type": "string"}, "target": {"type": "string"}, "text": {"type": "string"},
         "file_ids": {"type": "array", "items": {"type": "string"}}, "rediscover": {"type": "boolean"}, "title": {"type": "string"},
         "steps": {"type": "array", "items": {"type": "object"}}, "steps_text": {"type": "array", "items": {"type": "string"}},
         "expected": {"type": "string"}, "type": {"type": "string"}, "priority": {"type": "string"}, "area": {"type": "string"},
         "viewport": {"type": "integer"}, "account": {"type": "string"}, "preconditions": {"type": "string"},
         "tags": {"type": "array", "items": {"type": "string"}}, "case": {"type": "string"}, "which": {"type": "string"},
         "cases": {"type": "array", "items": {"type": "string"}}, "result": {"type": "string"}, "note": {"type": "string"},
         "bug": {"type": "string"}, "status": {"type": "string"}, "reason": {"type": "string"}, "duplicate_of": {"type": "string"},
         "severity": {"type": "string"}, "repo": {"type": "string"}, "team_name": {"type": "string"}, "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "qa_dekho", "description": (
        "Read QA work (nothing changes). what=overview | targets | target (target: ownership, accounts as masked hints, standard) | "
        "cases (target, status, type, result) | case (case) | runs (target) | run (run: every result) | bugs (target, status "
        "open|fixed|verified|..., severity) | bug (bug: steps, expected vs actual, console, history) | ready (target: release "
        "readiness) | steps (the safe step language) | rules (types, severities, accessibility standards by sector) | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["overview", "targets", "target", "cases", "case", "runs", "run", "bugs", "bug", "ready", "steps",
                                             "rules", "settings"]},
         "target": {"type": "string"}, "case": {"type": "string"}, "run": {"type": "string"}, "bug": {"type": "string"},
         "status": {"type": "string"}, "type": {"type": "string"}, "result": {"type": "string"}, "severity": {"type": "string"}},
         "required": ["what"]}},
]
QA_LABELS = {"qa": "App / website test kar raha hoon", "qa_dekho": "Test cases aur bugs dekh raha hoon"}

_OWNER_ONLY = {"target_remove", "settings", "github"}
_PASSWORDISH = re.compile(r"\b(password|passwd|pwd|otp)\b\s*(?:[:=]|is|hai|h)\s*(?=\S*[\d@#$%!&*])\S{4,}", re.I)


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..qa import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Testing graahakon ke liye nahi hai.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    if action == "target_edit" and "allow_writes" in a and not _owner(ctx):
        raise ToolError("Forms submit ki ijazat sirf owner de sakti hain.")
    blob = " ".join(_s(a.get(k)) for k in ("text", "note", "title", "expected"))
    if _PASSWORDISH.search(blob) or any("account." not in _s(x.get("value")) and re.search(r"password", _s(x.get("target")), re.I)
                                          for x in (a.get("steps") or []) if isinstance(x, dict) and x.get("do") == "fill"):
        raise ToolError("Password / OTP chat mein nahi: test account app mein (QA > target > Test account) bhariye. Asli password badal dijiye agar likh diya ho.")
    tg = _s(a.get("target"))
    try:
        if action == "target_add":
            return S.add_target(t, _s(a.get("kind")), _s(a.get("ref")), _s(a.get("url")), _s(a.get("name")), bool(a.get("govt_facing")),
                                _s(a.get("sector") or "general"), False, conv)
        if action == "target_edit":
            keys = ("name", "govt_facing", "sector", "allow_writes", "schedule")
            return S.update_target(t, tg, **{k: a[k] for k in keys if k in a})
        if action == "target_remove":
            return S.remove_target(t, tg)
        if action == "verify":
            return S.verify(t, tg)
        if action == "discover":
            return S.discover(t, tg)
        if action == "write":
            return S.generate(t, tg, _s(a.get("text")), a.get("file_ids") or [], bool(a.get("rediscover")), conv)
        if action == "case_add":
            return S.add_case(t, tg, _s(a.get("title")), a.get("steps") or [], a.get("steps_text") or None, _s(a.get("expected")),
                              _s(a.get("type") or "functional"), _s(a.get("priority") or "P3"), _s(a.get("area")), _s(a.get("account")),
                              int(a.get("viewport") or 1280), _s(a.get("preconditions")), a.get("tags") or None)
        if action == "case_edit":
            keys = ("title", "area", "expected", "preconditions", "account", "note", "steps", "steps_text", "type", "priority", "viewport", "tags")
            return S.edit_case(t, _s(a.get("case")), **{k: a[k] for k in keys if k in a})
        if action == "case_retire":
            return S.edit_case(t, _s(a.get("case")), status="retired")
        if action == "run":
            return S.start_run(t, tg, _s(a.get("which") or "all"), a.get("cases") or None, actor, conv)
        if action == "mark":
            return S.mark(t, _s(a.get("case")), _s(a.get("result")), _s(a.get("note")), actor, conv)
        if action == "bug":
            st = _s(a.get("status"))
            if st in ("wont_fix", "closed") and not _owner(ctx):
                raise ToolError("Bug band / 'nahi badlenge' sirf owner kar sakti hain.")
            return S.set_bug(t, _s(a.get("bug")), st, _s(a.get("reason")), _s(a.get("duplicate_of")), _s(a.get("severity")), actor)
        if action == "retest":
            return S.retest(t, _s(a.get("bug")), actor, conv, background=True)
        if action == "ready":
            return S.readiness(t, tg, conv, publish=True)
        if action == "github":
            return S.github_request(t, _s(a.get("bug")), _s(a.get("repo")), conv)
        if action == "register":
            return S.register_file(t, tg, conv)
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in ("team_name", "rules") if k in a})
    except (S.QaError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..qa import rules as R
    from ..qa import service as S
    from ..qa.steps import GUIDE
    t = ctx.tenant_id
    try:
        if what == "overview":
            return S.overview(t)
        if what == "targets":
            return {"targets": S.targets(t)}
        if what == "target":
            return S.target(t, _s(a.get("target")))
        if what == "cases":
            return {"cases": S.cases(t, _s(a.get("target")), _s(a.get("status") or "active"), _s(a.get("type")), _s(a.get("result")))}
        if what == "case":
            return S.case(t, _s(a.get("case")))
        if what == "runs":
            return {"runs": S.runs(t, _s(a.get("target")))}
        if what == "run":
            return S.run_view(t, _s(a.get("run")))
        if what == "bugs":
            return {"bugs": S.bugs(t, _s(a.get("target")), _s(a.get("status")), _s(a.get("severity")))}
        if what == "bug":
            return S.bug(t, _s(a.get("bug")))
        if what == "ready":
            return S.readiness(t, _s(a.get("target")))
        if what == "steps":
            return {"steps": GUIDE}
        if what == "rules":
            return {"types": R.TYPE_LABEL, "severities": R.SEV_LABEL, "statuses": R.BUG_LABEL, "standards": R.STANDARDS,
                    "never": ["kisi aur ki website test karna", "asli password / OTP / card bharna", "pay / checkout dabana",
                              "live site par form sach mein bhejna (jab tak staging ke liye ijazat na ho)", "GitHub issue bina uske tap ke"]}
        if what == "settings":
            return S.settings(t)
    except (S.QaError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def qa(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def qa_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


QA_HANDLERS = {"qa": qa, "qa_dekho": qa_dekho}
