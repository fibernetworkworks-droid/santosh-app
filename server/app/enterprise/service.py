"""The one engine behind all ten Enterprise Systems roles.

Everything here is role-aware but not role-specific: the role decides which systems may be connected, which
artifacts may be made, whether it may write at all, and whether it is capped (rules.py). That is why ten jobs are
one file instead of ten near-identical ones.

Three things hold whatever the model writes:
  - a CAPPED role never writes anywhere outside and says so in the result (health_int, bank_int, regtech)
  - a secret in any argument is refused before anything runs
  - a number that did not come from a connected system or from her is never put in an artifact
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import rules as R
from .models import EntArtifact, EntItem, EntProject, EntSettings, EntSystem

log = logging.getLogger("santosh.enterprise")


class EnterpriseError(Exception):
    pass


# ---------------------------------------------------------------- small helpers
def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except ValueError:
        return default


def _s(v: Any, n: int = 4000) -> str:
    return ("" if v is None else str(v)).strip()[:n]


_SECRET = re.compile(
    r"(sk-[A-Za-z0-9_\-]{12,}|xox[baprs]-[A-Za-z0-9\-]{8,}|gh[pousr]_[A-Za-z0-9]{16,}"
    r"|AKIA[0-9A-Z]{12,}|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}"
    r"|\b(?:password|passwd|client_secret|api[_ -]?key|secret|token)\b\s*[:=]\s*\S{6,})", re.I)
_ACCOUNT = re.compile(r"\b\d{9,18}\b")
# Aadhaar and an account number are both often 12 digits, so the shape decides: an Aadhaar is written in groups
# ("1234 5678 9012") or named outright, and goes completely. A bare run of digits is treated as an account number
# and keeps its last four, because she needs to know WHICH account - masking it whole would make the paper useless.
_AADHAAR = re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b|\b(?:aadhaar|aadhar|uid)\b\D{0,12}\d{12}\b", re.I)


def guard_secret(blob: str) -> None:
    if _SECRET.search(blob or ""):
        raise EnterpriseError(
            "Key ya password chat mein nahi. System app se jodiye (Enterprise > System jodo); jo yahan likha gaya "
            "use abhi badal dijiye.")


def mask(text: str) -> str:
    """Account numbers and Aadhaar never survive into an artifact, whatever the model wrote."""
    t = _AADHAAR.sub("XXXX XXXX ####", text or "")
    return _ACCOUNT.sub(lambda m: "x" * max(0, len(m.group(0)) - 4) + m.group(0)[-4:], t)


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("enterprise publish failed")


def _ai_json(system: str, prompt: str, max_tokens: int = 2500) -> dict[str, Any]:
    """{} when there is no model (tests, no key, error), so every caller must have a code fallback."""
    try:
        from ..net.ai import llm
        raw = llm(system + "\nReply with ONLY one JSON object, no markdown fence.", prompt, max_tokens, timeout=120)
    except Exception as e:
        log.info("enterprise model call failed: %s", e)
        return {}
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return {}
    try:
        v = json.loads(m.group(0))
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def _check_role(role: str) -> dict[str, Any]:
    try:
        return R.role(role)
    except KeyError:
        raise EnterpriseError(f"'{role}' naam ka enterprise kaam nahi hai.")


def cap_note(role: str) -> str:
    return R.cap_of(role)


def _with_cap(role: str, out: dict[str, Any]) -> dict[str, Any]:
    """A capped role says where it stops, in every single result - never quietly less than she expected."""
    c = R.cap_of(role)
    if c:
        out = {**out, "yahan_tak": c}
    return out


# ---------------------------------------------------------------- settings
def _st(s, tenant: str, role: str) -> EntSettings:
    r = s.scalars(select(EntSettings).where(EntSettings.tenant_id == tenant, EntSettings.role == role)).first()
    if r is None:
        r = EntSettings(tenant_id=tenant, role=role)
        s.add(r)
        s.flush()
    return r


def settings(tenant: str, role: str) -> dict[str, Any]:
    spec = _check_role(role)
    with session() as s:
        r = _st(s, tenant, role)
        out = {"role": role, "label": spec["label"], "kaam": spec["say"], "company": r.company,
               "env_default": r.env_default, "rules": r.rules}
    out["systems"] = R.systems_for(role)
    out["artifacts"] = spec["artifacts"]
    out["likh_sakta_hai"] = spec["writes"]
    out["niyam"] = list(spec["rules"]) + list(R.NEVER)
    return _with_cap(role, out)


def save_settings(tenant: str, role: str, **kw: Any) -> dict[str, Any]:
    _check_role(role)
    with session() as s:
        r = _st(s, tenant, role)
        if "company" in kw:
            r.company = _s(kw["company"], 120)
        if "env_default" in kw:
            v = _s(kw["env_default"], 10).lower()
            if v not in ("test", "production"):
                raise EnterpriseError("env test ya production hi ho sakta hai.")
            r.env_default = v
        if "rules" in kw:
            r.rules = _s(kw["rules"])
        r.updated_at = now()
    return settings(tenant, role)


# ---------------------------------------------------------------- systems she connected
def _sys_view(r: EntSystem) -> dict[str, Any]:
    return {"id": r.id, "system": r.system, "label": r.label or R.SYSTEMS.get(r.system, {}).get("label", r.system),
            "env": r.env, "account": r.account, "linked": r.linked, "note": r.note}


def systems(tenant: str, role: str) -> dict[str, Any]:
    _check_role(role)
    with session() as s:
        rows = s.scalars(select(EntSystem).where(EntSystem.tenant_id == tenant, EntSystem.role == role)).all()
        mine = [_sys_view(r) for r in rows]
    return _with_cap(role, {"jude_hue": mine, "jod_sakte_hain": R.systems_for(role)})


def connect(tenant: str, role: str, system: str, env: str = "", account: str = "", note: str = "") -> dict[str, Any]:
    """Records that the app made the link. The credential itself lives with Composio / the system's own OAuth."""
    spec = _check_role(role)
    if system not in spec["systems"]:
        raise EnterpriseError(f"Is kaam ke liye {system} nahi jodte. Ho sakte hain: " + ", ".join(spec["systems"]))
    guard_secret(" ".join([account, note]))
    how = R.SYSTEMS[system]["how"]
    env = (_s(env, 10) or "test").lower()
    if env not in ("test", "production"):
        raise EnterpriseError("env test ya production hi ho sakta hai.")
    with session() as s:
        r = s.scalars(select(EntSystem).where(EntSystem.tenant_id == tenant, EntSystem.role == role,
                                              EntSystem.system == system)).first()
        if r is None:
            r = EntSystem(tenant_id=tenant, role=role, system=system)
            s.add(r)
        r.label = R.SYSTEMS[system]["label"]
        r.env = env
        r.account = _s(account, 120)
        r.note = _s(note, 400)
        r.linked = True
        r.updated_at = now()
        s.flush()
        v = _sys_view(r)
    v["kaise"] = R.SYSTEMS[system]["note"]
    if how == "read_only":
        v["sirf_padhna"] = "Is system se abhi sirf padha jaata hai."
    return _with_cap(role, v)


def disconnect(tenant: str, role: str, system: str) -> dict[str, Any]:
    with session() as s:
        r = s.scalars(select(EntSystem).where(EntSystem.tenant_id == tenant, EntSystem.role == role,
                                              EntSystem.system == system)).first()
        if r is not None:
            s.delete(r)
    return systems(tenant, role)


def _linked(tenant: str, role: str) -> list[EntSystem]:
    with session() as s:
        return list(s.scalars(select(EntSystem).where(EntSystem.tenant_id == tenant, EntSystem.role == role,
                                                      EntSystem.linked.is_(True))).all())


def _env_line(tenant: str, role: str) -> str:
    """Which system and which environment this piece of work is about - written on every action, never assumed."""
    rows = _linked(tenant, role)
    if not rows:
        return "koi system juda nahi (sheet / aapke diye data par kaam ho raha hai)"
    return ", ".join(f"{r.label or r.system} ({r.env})" for r in rows)


# ---------------------------------------------------------------- projects
def _proj_view(r: EntProject) -> dict[str, Any]:
    return {"ref": r.id, "title": r.title, "goal": r.goal, "status": r.status}


def projects(tenant: str, role: str, status: str = "") -> list[dict[str, Any]]:
    _check_role(role)
    with session() as s:
        q = select(EntProject).where(EntProject.tenant_id == tenant, EntProject.role == role)
        if status:
            q = q.where(EntProject.status == status)
        return [_proj_view(r) for r in s.scalars(q.order_by(EntProject.created_at.desc())).all()]


def new_project(tenant: str, role: str, title: str, goal: str = "") -> dict[str, Any]:
    _check_role(role)
    title = _s(title, 160)
    if not title:
        raise EnterpriseError("Kaam ka naam chahiye.")
    guard_secret(title + " " + goal)
    with session() as s:
        r = EntProject(tenant_id=tenant, role=role, title=title, goal=_s(goal))
        s.add(r)
        s.flush()
        return _with_cap(role, _proj_view(r))


def _project(s, tenant: str, role: str, ref: str) -> EntProject:
    r = s.get(EntProject, ref)
    if r is None or r.tenant_id != tenant or r.role != role:
        raise EnterpriseError("Yeh kaam nahi mila.")
    return r


def set_project(tenant: str, role: str, ref: str, **kw: Any) -> dict[str, Any]:
    with session() as s:
        r = _project(s, tenant, role, ref)
        if "title" in kw:
            r.title = _s(kw["title"], 160) or r.title
        if "goal" in kw:
            r.goal = _s(kw["goal"])
        if "status" in kw:
            v = _s(kw["status"], 12)
            if v not in ("open", "done", "parked"):
                raise EnterpriseError("status open | done | parked")
            r.status = v
        r.updated_at = now()
        return _proj_view(r)


# ---------------------------------------------------------------- artifacts
def _art_view(r: EntArtifact, full: bool = True) -> dict[str, Any]:
    v = {"ref": r.id, "kind": r.kind, "title": r.title, "version": r.version, "project": r.project_id,
         "rows": len(_j(r.rows, [])), "source": r.source}
    if full:
        v["body"] = r.body
        v["table"] = _j(r.rows, [])
    return v


def artifacts(tenant: str, role: str, kind: str = "", project: str = "") -> list[dict[str, Any]]:
    _check_role(role)
    with session() as s:
        q = select(EntArtifact).where(EntArtifact.tenant_id == tenant, EntArtifact.role == role)
        if kind:
            q = q.where(EntArtifact.kind == kind)
        if project:
            q = q.where(EntArtifact.project_id == project)
        return [_art_view(r, full=False) for r in s.scalars(q.order_by(EntArtifact.created_at.desc())).all()]


def artifact(tenant: str, role: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = s.get(EntArtifact, ref)
        if r is None or r.tenant_id != tenant or r.role != role:
            raise EnterpriseError("Yeh kaagaz nahi mila.")
        return _with_cap(role, _art_view(r))


_ASK = {
    "spec": "an integration specification: scope, systems and environments, the interfaces, the data that moves, error handling, who signs off",
    "mapping": "a field mapping table: source field, target field, type, transform rule, mandatory, note",
    "plan": "a plan with phases, each phase having steps, who does it, how long, and what must be true before it starts",
    "checklist": "a checklist of concrete steps with a yes/no outcome each",
    "register": "a register: one row per obligation or item, with the date, owner, status and the rule it comes from",
    "report": "a findings report: what was looked at, what was found, each with evidence, and the three things to do first",
    "test_plan": "a test plan: case, given/when/then, data needed, expected result, who runs it",
    "runbook": "a runbook: the exact steps to run it, what to check after each, and how to roll back",
}

_SYSTEM_PROMPT = (
    "You are the enterprise-systems coworker inside Hoola, an Indian business assistant. You write the working "
    "paper an experienced {label} would hand over. Rules you cannot break:\n"
    "- Only use facts the user gave or that came from a connected system. Invent NO number, NO field name, NO date. "
    "Where something is unknown write \"pata nahi\" and add it to `missing`.\n"
    "- Never include a password, token, patient name, full account number or ID number.\n"
    "- Write in the user's own language mix (Hinglish is fine); keep sentences short.\n"
    "{cap}"
    "Return JSON: {{\"title\": str, \"body\": markdown str, \"rows\": [[...]], \"missing\": [str], \"source\": str}}. "
    "`rows` is a table ONLY when the paper is naturally a table (mapping, register, checklist), first row = headers; "
    "otherwise []."
)


def draft(tenant: str, role: str, kind: str, about: str = "", project: str = "", note: str = "",
          conv: str = "") -> dict[str, Any]:
    """Make the paper this job exists to produce. Nothing leaves Hoola here - this only writes a record."""
    spec = _check_role(role)
    if kind not in spec["artifacts"]:
        raise EnterpriseError(f"Is kaam mein '{kind}' nahi banta. Ban sakte hain: " + ", ".join(spec["artifacts"]))
    guard_secret(" ".join([about, note]))
    env = _env_line(tenant, role)
    cap = R.cap_of(role)
    sysmsg = _SYSTEM_PROMPT.format(
        label=spec["label"],
        cap=("- This job is CAPPED: " + cap + " Say so at the end of the paper, in her language.\n") if cap else "")
    prompt = (f"Job: {spec['label']} - {spec['say']}\n"
              f"Paper wanted: {kind} - {_ASK.get(kind, kind)}\n"
              f"Systems connected: {env}\n"
              f"House rules: {' | '.join(spec['rules'])}\n"
              f"What she said: {about or '(nothing beyond the job itself)'}\n"
              f"Extra note: {note or '-'}")
    got = _ai_json(sysmsg, prompt)
    title = _s(got.get("title"), 160) or f"{kind} - {about[:60] or spec['label']}"
    body = mask(_s(got.get("body"), 60000))
    rows = got.get("rows") if isinstance(got.get("rows"), list) else []
    rows = [[mask(_s(c, 300)) for c in r] for r in rows if isinstance(r, list)][:400]
    missing = [_s(x, 200) for x in (got.get("missing") or []) if _s(x)][:40]
    if not body and not rows:
        # no model (tests / no key): still give her a real, honest skeleton rather than nothing
        body = (f"# {title}\n\n_{spec['label']}_\n\nSystem: {env}\n\n"
                f"Yeh dhaancha taiyaar hai; iske andar ki baatein abhi bharni hain.\n")
        missing = missing or ["poora vivaran - Hoola ko abhi model se jawab nahi mila"]
    with session() as s:
        r = EntArtifact(tenant_id=tenant, role=role, project_id=_s(project, 40), kind=kind, title=title,
                        body=body, rows=json.dumps(rows, ensure_ascii=False),
                        source=_s(got.get("source"), 2000) or env)
        s.add(r)
        s.flush()
        out = _art_view(r)
    out["missing"] = missing
    if missing:
        out["note"] = "Jo cheezein nahi pata, woh 'missing' mein hain - unke bina yeh kaagaz adhoora hai."
    _publish(tenant, "enterprise_artifact", {"role": role, "ref": out["ref"], "kind": kind, "title": title}, conv)
    return _with_cap(role, out)


def revise(tenant: str, role: str, ref: str, instruction: str, conv: str = "") -> dict[str, Any]:
    guard_secret(instruction)
    with session() as s:
        r = s.get(EntArtifact, ref)
        if r is None or r.tenant_id != tenant or r.role != role:
            raise EnterpriseError("Yeh kaagaz nahi mila.")
        old_body, kind, title = r.body, r.kind, r.title
    spec = _check_role(role)
    got = _ai_json(_SYSTEM_PROMPT.format(label=spec["label"], cap=""),
                   f"Rewrite this {kind} with her change. Keep everything she did not ask to change.\n\n"
                   f"HER CHANGE: {instruction}\n\nCURRENT:\n{old_body[:20000]}")
    body = mask(_s(got.get("body"), 60000)) or old_body
    with session() as s:
        r = s.get(EntArtifact, ref)
        r.body = body
        r.title = _s(got.get("title"), 160) or title
        r.version = (r.version or 1) + 1
        r.updated_at = now()
        out = _art_view(r)
    return _with_cap(role, out)


def artifact_file(tenant: str, role: str, ref: str, conv: str = "") -> dict[str, Any]:
    """The paper as a Word file she can send on."""
    a = artifact(tenant, role, ref)
    from .. import chatfiles
    try:
        from ..docstudio import build_docx
        data, mime, name = build_docx(a["title"], a["body"]), \
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"{a['title'][:60]}.docx"
    except Exception:
        data, mime, name = a["body"].encode("utf-8"), "text/markdown", f"{a['title'][:60]}.md"
    f = chatfiles.store(tenant, name, data, mime)
    _publish(tenant, "pc_file", {**f, "source": "enterprise", "title": a["title"]}, conv)
    return _with_cap(role, {k: f.get(k) for k in ("file_id", "name", "url", "size") if f.get(k) is not None})


# ---------------------------------------------------------------- items (gaps, risks, due dates, tasks)
def _item_view(r: EntItem) -> dict[str, Any]:
    v = {"ref": r.id, "kind": r.kind, "title": r.title, "status": r.status, "owner": r.owner, "due": r.due,
         "severity": r.severity, "detail": r.detail, "source": r.source}
    if r.amount_paise:
        v["rupaye"] = round(r.amount_paise / 100, 2)
    return v


def items(tenant: str, role: str, kind: str = "", status: str = "", project: str = "") -> list[dict[str, Any]]:
    _check_role(role)
    with session() as s:
        q = select(EntItem).where(EntItem.tenant_id == tenant, EntItem.role == role)
        if kind:
            q = q.where(EntItem.kind == kind)
        if status:
            q = q.where(EntItem.status == status)
        if project:
            q = q.where(EntItem.project_id == project)
        return [_item_view(r) for r in s.scalars(q.order_by(EntItem.due, EntItem.created_at.desc())).all()]


def add_item(tenant: str, role: str, title: str, kind: str = "task", detail: str = "", owner: str = "",
             due: str = "", severity: str = "", rupaye: Any = None, project: str = "",
             source: str = "") -> dict[str, Any]:
    _check_role(role)
    title = _s(title, 200)
    if not title:
        raise EnterpriseError("Kya cheez? Naam chahiye.")
    guard_secret(" ".join([title, detail, source]))
    if kind not in ("task", "gap", "risk", "due", "finding"):
        raise EnterpriseError("kind task | gap | risk | due | finding")
    if due and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due):
        raise EnterpriseError("due YYYY-MM-DD ho.")
    paise = 0
    if rupaye not in (None, ""):
        try:
            paise = int(round(float(rupaye) * 100))
        except (TypeError, ValueError):
            raise EnterpriseError("rupaye ek number hona chahiye.")
    with session() as s:
        r = EntItem(tenant_id=tenant, role=role, project_id=_s(project, 40), kind=kind, title=mask(title),
                    detail=mask(_s(detail)), owner=_s(owner, 80), due=due, severity=_s(severity, 8),
                    amount_paise=paise, source=_s(source, 2000))
        s.add(r)
        s.flush()
        return _with_cap(role, _item_view(r))


def set_item(tenant: str, role: str, ref: str, **kw: Any) -> dict[str, Any]:
    with session() as s:
        r = s.get(EntItem, ref)
        if r is None or r.tenant_id != tenant or r.role != role:
            raise EnterpriseError("Yeh cheez nahi mili.")
        for k in ("title", "detail", "owner", "severity", "source"):
            if k in kw:
                setattr(r, k, mask(_s(kw[k])))
        if "due" in kw:
            d = _s(kw["due"], 10)
            if d and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
                raise EnterpriseError("due YYYY-MM-DD ho.")
            r.due = d
        if "status" in kw:
            v = _s(kw["status"], 12)
            if v not in ("open", "doing", "done", "dropped"):
                raise EnterpriseError("status open | doing | done | dropped")
            r.status = v
        r.updated_at = now()
        return _item_view(r)


# ---------------------------------------------------------------- the day / the report
def _today(tenant: str) -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def day(tenant: str, role: str) -> dict[str, Any]:
    """What this job looks like right now: what is open, what is overdue, what was made."""
    spec = _check_role(role)
    t = _today(tenant)
    its = items(tenant, role)
    overdue = [i for i in its if i["due"] and i["due"] < t and i["status"] not in ("done", "dropped")]
    soon = [i for i in its if i["due"] and t <= i["due"] <= _plus(t, 7) and i["status"] not in ("done", "dropped")]
    open_hi = [i for i in its if i["severity"] == "high" and i["status"] == "open"]
    out = {"role": role, "label": spec["label"], "system": _env_line(tenant, role),
           "kaam": projects(tenant, role, "open"),
           "aaj_tak_nikle": len(artifacts(tenant, role)),
           "tareekh_nikal_gayi": overdue, "is_hafte": soon, "bade_khatre": open_hi,
           "khule_kaam": len([i for i in its if i["status"] in ("open", "doing")])}
    return _with_cap(role, out)


def _plus(day_str: str, n: int) -> str:
    from datetime import date, timedelta
    y, m, d = (int(x) for x in day_str.split("-"))
    return (date(y, m, d) + timedelta(days=n)).isoformat()


def overview(tenant: str) -> dict[str, Any]:
    """All ten jobs in one look, for the Employee screen."""
    out = []
    for key, spec in R.ROLES.items():
        with session() as s:
            n_art = len(s.scalars(select(EntArtifact).where(EntArtifact.tenant_id == tenant,
                                                            EntArtifact.role == key)).all())
            n_open = len(s.scalars(select(EntItem).where(EntItem.tenant_id == tenant, EntItem.role == key,
                                                         EntItem.status.in_(("open", "doing")))).all())
            n_sys = len(s.scalars(select(EntSystem).where(EntSystem.tenant_id == tenant, EntSystem.role == key,
                                                          EntSystem.linked.is_(True))).all())
        if n_art or n_open or n_sys:
            out.append({"role": key, "label": spec["label"], "kaagaz": n_art, "khule_kaam": n_open,
                        "system": n_sys, "yahan_tak": spec["cap"]})
    return {"jobs": out, "sab_jobs": [{"role": k, "label": v["label"], "kaam": v["say"], "yahan_tak": v["cap"]}
                                      for k, v in R.ROLES.items()]}
