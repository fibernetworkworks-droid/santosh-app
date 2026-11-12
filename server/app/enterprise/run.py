"""Real read and write against her ERP - the complex half.

A read is one call. A WRITE IS NEVER ONE CALL, and that is the whole of this file:

    plan  ->  dry run (what would change, row by row)  ->  HER TAP  ->  batches  ->  verify  ->  report

Four things are true in code, not in a prompt, because a wrong write into a live ERP is not undoable by apology:

1. A write run cannot start until it has been dry-run and she has approved THAT run. The approval is tied to the
   plan hash, so if the rows change after she taps, the run refuses and asks again.
2. Every row carries an idempotency key written BEFORE the call. A run that dies half way resumes without ever
   posting the same record twice - the thing that makes a real migration safe.
3. Production is never the default and never inferred: the endpoint says test or production, and a production
   write needs that word from her as well.
4. Mass delete is refused outright, at any size. There is no business reason Hoola needs it, and no safe way to
   offer it.

Two rails reach her system, both official and both with HER credential, never one of ours:
  composio - her connected account (~1,600 apps; NetSuite and friends)
  odata    - her own endpoint for what Composio does not carry (SAP OData, Windchill REST), credential SEALED
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import dialect, rules as R
from .models import EntEndpoint, EntRun, EntRunRow

log = logging.getLogger("santosh.enterprise.run")

MAX_ROWS = 500              # one run; a bigger load is split, so a mistake stays small
BATCH = 25
READ_LIMIT = 2000           # rows a read may bring back before it must be narrowed
DELETE_WORDS = ("DELETE", "DESTROY", "PURGE", "DROP", "TRUNCATE")


class RunError(Exception):
    pass


def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except ValueError:
        return default


def _hash(*parts: Any) -> str:
    return hashlib.sha256("||".join(str(p) for p in parts).encode()).hexdigest()[:32]


def _mask_auth(v: str) -> str:
    v = v or ""
    return (v[:3] + "…" + v[-3:]) if len(v) > 10 else "…"


# ---------------------------------------------------------------- her own endpoint (sealed)
def set_endpoint(tenant: str, role: str, system: str, base_url: str, auth: str, auth_kind: str = "bearer",
                 env: str = "test", header_name: str = "", note: str = "") -> dict[str, Any]:
    """Called from the APP, never from chat: the clear credential is sealed at once and never read back."""
    from ..bazar.security import vault
    spec = R.role(role)
    if system not in spec["systems"]:
        raise RunError(f"For this job, {system} is not used.")
    if not re.match(r"^https://", base_url or ""):
        raise RunError("The address must start with https://.")
    env = (env or "test").lower()
    if env not in ("test", "production"):
        raise RunError("env can only be test or production.")
    if auth_kind not in ("bearer", "basic", "header"):
        raise RunError("auth_kind bearer | basic | header")
    with session() as s:
        r = s.scalars(select(EntEndpoint).where(EntEndpoint.tenant_id == tenant, EntEndpoint.role == role,
                                                EntEndpoint.system == system)).first()
        if r is None:
            r = EntEndpoint(tenant_id=tenant, role=role, system=system)
            s.add(r)
        r.base_url = base_url[:400]
        r.env = env
        r.auth_kind = auth_kind
        r.header_name = header_name[:60]
        r.note = note[:400]
        if auth:
            r.auth_enc = vault().seal(auth)
            r.auth_masked = _mask_auth(auth)
        s.flush()
        return {"system": r.system, "base_url": r.base_url, "env": r.env, "auth": r.auth_masked,
                "note": "Credential sealed; it is not visible in the database or to the model."}


def endpoints(tenant: str, role: str) -> list[dict[str, Any]]:
    with session() as s:
        return [{"system": r.system, "base_url": r.base_url, "env": r.env, "auth": r.auth_masked,
                 "verified": bool(r.verified_at)}
                for r in s.scalars(select(EntEndpoint).where(EntEndpoint.tenant_id == tenant,
                                                             EntEndpoint.role == role)).all()]


def _endpoint(tenant: str, role: str, system: str) -> EntEndpoint | None:
    with session() as s:
        return s.scalars(select(EntEndpoint).where(EntEndpoint.tenant_id == tenant, EntEndpoint.role == role,
                                                   EntEndpoint.system == system)).first()


# ---------------------------------------------------------------- the two rails
def _odata_call(ep: EntEndpoint, method: str, path: str, body: Any = None,
                params: dict | None = None, page: int = 0) -> tuple[int, Any]:
    """A single READ against her endpoint. Writes do NOT come through here any more: they need one session
    held open for the CSRF token (see dialect.Call), which a per-call client cannot give."""
    with dialect.Call(ep) as c:
        if method.upper() == "GET":
            return c.get(path, params=params, page=page)
        code, data, _ = c.raw(method, path, body=body, params=params)
        return code, data


class Ambiguous(Exception):
    """The call may or may not have landed. This is NOT a failure, because a failure gets retried and a retry
    here would double-post. The row is parked for her to decide."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def _composio_call(tenant: str, slug: str, args: dict[str, Any]) -> tuple[int, Any]:
    from ..bazar import composio as cmp
    from ..db import session as _s
    toolkit = cmp.tool_toolkit(slug)                 # v0.389: never slug.split("_")[0] - see composio.toolkit_of
    with _s() as s:
        acc, state = cmp.account(s, cmp.composio_user(tenant), toolkit)
        if acc is None or state != "active":
            raise RunError(f"{toolkit} is not connected. Connect it in the app under Connectors.")
        ca_id = acc.account_id
    try:
        out = cmp.client().execute(slug, cmp.composio_user(tenant), ca_id, args)
    except Exception as ex:                          # noqa: BLE001
        # Composio does not retry a non-idempotent write after a timeout, and says an ambiguous timeout must
        # be resolved by reading the provider's state. So we never decide it for her.
        if _looks_timeout(ex):
            raise Ambiguous(f"No answer came back ({str(ex)[:120]}). This row may have gone through.")
        raise
    if not isinstance(out, dict):
        raise Ambiguous("Composio's answer could not be understood.")
    # v0.389: this used to default to TRUE when the field was missing, so a changed response shape would
    # report a FAILED write as done - and the idempotency key would then mark the row complete for ever.
    if "successful" in out:
        ok = bool(out.get("successful"))
    elif "success" in out:
        ok = bool(out.get("success"))
    elif out.get("error"):
        ok = False
    else:
        raise Ambiguous("Composio did not say clearly whether the work was done.")
    return (200 if ok else 400), out.get("data", out)


def _looks_timeout(ex: Exception) -> bool:
    s = (type(ex).__name__ + " " + str(ex)).lower()
    return any(w in s for w in ("timeout", "timed out", "readerror", "connectionreset", "remoteprotocol",
                                "incomplete", "502", "503", "504"))


# Each system spells its own URLs. Salesforce records live under /sobjects, its CONFIGURATION lives behind the
# Tooling API under /tooling/sobjects - a different surface with different risk, which is why `api` is on the run
# and not guessed from the target.
def _paths(system: str, api: str, target: str, key: str = "") -> tuple[str, str]:
    if system == "salesforce":
        base = "tooling/sobjects" if api == "tooling" else "sobjects"
        return f"{base}/{target}", f"{base}/{target}/{key}"
    return target, f"{target}('{key}')"


def _describe_path(system: str, api: str, what: str) -> str:
    if system == "salesforce":
        root = "tooling" if api == "tooling" else ""
        if what in ("", "objects"):
            return f"{root}/sobjects".lstrip("/")
        return f"{root}/sobjects/{what}/describe".lstrip("/")
    return f"{what}" if what else "$metadata"


def describe(tenant: str, role: str, system: str, what: str = "", api: str = "data") -> dict[str, Any]:
    """Read the SHAPE of her system - objects, fields, flows, permission sets. Changes nothing, so it runs now."""
    R.role(role)
    api = "tooling" if api == "tooling" else "data"
    ep = _endpoint(tenant, role, system)
    if ep is None:
        raise RunError(f"{system} address is not connected. Connect it in the app under Enterprise > Connect system.")
    code, data = _odata_call(ep, "GET", _describe_path(system, api, what))
    if code >= 300:
        raise RunError(f"{system} answered {code}: " + json.dumps(data, default=str)[:300])
    out: dict[str, Any] = {"system": system, "env": ep.env, "api": api, "what": what or "objects"}
    if isinstance(data, dict) and isinstance(data.get("fields"), list):
        out["fields"] = [{"name": f.get("name"), "label": f.get("label"), "type": f.get("type"),
                          "zaroori": not f.get("nillable", True), "badal_sakte": bool(f.get("updateable"))}
                         for f in data["fields"]][:400]
        out["count"] = len(out["fields"])
    elif isinstance(data, dict) and isinstance(data.get("sobjects"), list):
        out["objects"] = [{"name": o.get("name"), "label": o.get("label"),
                           "custom": bool(o.get("custom"))} for o in data["sobjects"]][:600]
        out["count"] = len(out["objects"])
    else:
        out["raw"] = data if not isinstance(data, list) else data[:200]
    return out


def soql(tenant: str, role: str, system: str, query: str, api: str = "data", limit: int = 200) -> dict[str, Any]:
    """Her own SOQL, read-only. A query that writes is not a query - anything but SELECT is refused."""
    R.role(role)
    q = (query or "").strip()
    if not q.upper().startswith("SELECT"):
        raise RunError("Only SELECT runs here.")
    ep = _endpoint(tenant, role, system)
    if ep is None:
        raise RunError(f"{system} address is not connected.")
    root = "tooling/query" if api == "tooling" else "query"
    code, data = _odata_call(ep, "GET", root, params={"q": q})
    if code >= 300:
        raise RunError(f"{system} answered {code}: " + json.dumps(data, default=str)[:300])
    rows = _rows_of(data)[:max(1, min(int(limit or 200), READ_LIMIT))]
    return {"system": system, "env": ep.env, "api": api, "rows": rows, "count": len(rows),
            "aur_hai": bool(isinstance(data, dict) and data.get("nextRecordsUrl"))}


def _rail_for(tenant: str, role: str, system: str) -> str:
    if _endpoint(tenant, role, system) is not None:
        return "odata"
    return "composio"


# ---------------------------------------------------------------- READ
def read(tenant: str, role: str, system: str, target: str, query: dict[str, Any] | None = None,
         limit: int = 200) -> dict[str, Any]:
    """A read runs at once - it changes nothing. It is capped so a careless query cannot pull the whole ledger."""
    R.role(role)
    limit = max(1, min(int(limit or 200), READ_LIMIT))
    rail = _rail_for(tenant, role, system)
    q = dict(query or {})
    if rail == "odata":
        ep = _endpoint(tenant, role, system)
        q.setdefault("$top", limit)
        # Windchill pages at 25 rows by DEFAULT, so our 2,000-row cap was never the thing truncating a read -
        # silent pagination was. `Prefer: odata.maxpagesize` asks for a real page (server ceiling 2,000).
        code, data = _odata_call(ep, "GET", target, params=q, page=limit)
        env = ep.env
    else:
        if not _is_read_slug(target):
            raise RunError(f"'{target}' does not look like a read job. To write, use write/plan.")
        code, data = _composio_call(tenant, target, {**q, "limit": limit})
        env = "production"
    rows = _rows_of(data)
    return {"system": system, "env": env, "rail": rail, "target": target, "status": code,
            "rows": rows[:limit], "count": len(rows[:limit]),
            "note": ("Not all data came back - make the query smaller." if len(rows) >= limit else "")}


def _is_read_slug(slug: str) -> bool:
    from ..bazar import composio as cmp
    return cmp.is_read(slug)        # v0.389: resolves the toolkit properly; was slug.split("_")[0]


def _rows_of(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("value", "items", "results", "rows", "d", "data", "records"):
            v = data.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict) and isinstance(v.get("results"), list):
                return v["results"]
        return [data]
    return []


# ---------------------------------------------------------------- WRITE: plan -> dry run -> tap -> batches
def plan_write(tenant: str, role: str, system: str, target: str, verb: str, rows: list[dict[str, Any]],
               key_field: str = "", job: str = "", project: str = "", title: str = "",
               api: str = "data") -> dict[str, Any]:
    """Build the run and freeze it. Nothing touches her ERP here."""
    R.role(role)
    verb = (verb or "").lower()
    if verb not in ("create", "update", "upsert"):
        raise RunError("verb create | update | upsert. Hoola never deletes.")
    if any(w in (target or "").upper() for w in DELETE_WORDS):
        raise RunError("Hoola does not delete - at any size.")
    if not isinstance(rows, list) or not rows:
        raise RunError("Rows are needed to write.")
    if len(rows) > MAX_ROWS:
        raise RunError(f"No more than {MAX_ROWS} at once. Do it in parts - mistakes stay small.")
    rail = _rail_for(tenant, role, system)
    ep = _endpoint(tenant, role, system)
    env = ep.env if ep is not None else "production"
    api = "tooling" if api == "tooling" else "data"
    _guard_target(system, api, env, target, rail)
    with session() as s:
        run = EntRun(tenant_id=tenant, role=role, job=job[:24], project_id=project[:40], system=system, env=env,
                     rail=rail, op="write", verb=verb, target=target[:120],
                     api=("tooling" if api == "tooling" else "data"),
                     title=(title or f"{verb} {len(rows)} rows in {target}")[:200],
                     total=len(rows), status="planned")
        run.plan = json.dumps({"key_field": key_field, "rows": len(rows)}, ensure_ascii=False)
        s.add(run)
        s.flush()
        rid = run.id
        for i, row in enumerate(rows):
            key = str(row.get(key_field) or "") if key_field else ""
            s.add(EntRunRow(run_id=rid, tenant_id=tenant, n=i, key=key[:160],
                            idem=_hash(rid, i, key, json.dumps(row, sort_keys=True, default=str)),
                            payload=json.dumps(row, ensure_ascii=False)))
    return status(tenant, rid)


# ---------------------------------------------------------------- what the vendor itself refuses
# v0.389, from Salesforce's own documentation: "CRUD operations on the following Tooling API objects in an
# active org generate the error `Save or update not supported in active organizations`: ApexClass,
# ApexComponent, ApexPage, ApexTrigger, CustomField, CustomObject."
# developer.salesforce.com .../api_tooling/intro_crud_operations.htm
# So these were never going to work in HER live org, whatever we did. Saying so at plan time - before she
# taps - is the whole difference between an honest tool and one that fails at the last step.
SF_NO_WRITE_IN_PRODUCTION = ("apexclass", "apexcomponent", "apexpage", "apextrigger", "customfield",
                             "customobject")
# No write path at all over Tooling REST, in any org: read-only, or SOAP-only (Layout).
SF_NO_WRITE_EVER = {"customobject": "CustomObject can only be read - there is no create/change route in Tooling "
                                   "at all.",
                    "profile": "Profile has no write route in the Tooling API.",
                    "permissionset": "PermissionSet has no write route in the Tooling API.",
                    "layout": "Layout changes only through SOAP; Hoola runs on REST."}
SF_METADATA_HINT = ("This goes through a Metadata deploy (checkOnly preview -> your approval -> deploy), "
                    "not Tooling. See Enterprise > CRM > Deploy.")


def _guard_target(system: str, api: str, env: str, target: str, rail: str) -> None:
    """Refuse at PLAN time what the vendor will refuse at write time. A tool that discovers this after her tap
    has already spent her attention on a run that could never work."""
    t = (target or "").strip().lower()
    if system == "salesforce" and api == "tooling":
        why = SF_NO_WRITE_EVER.get(t)
        if why:
            raise RunError(why + " " + SF_METADATA_HINT)
        if env == "production" and t in SF_NO_WRITE_IN_PRODUCTION:
            raise RunError(
                f"Salesforce itself refuses this on {target} in a live org "
                "('Save or update not supported in active organizations'). " + SF_METADATA_HINT)
    if rail == "composio":
        from ..bazar import composio as cmp
        exists = cmp.tool_exists(target)
        if exists is False:
            raise RunError(f"'{target}' is not a Composio tool. The right name is in the Connect tab.")


def dry_run(tenant: str, run_id: str) -> dict[str, Any]:
    """What WOULD change. For update/upsert it reads the current record first, so she sees before -> after, and
    that before-image is also the only honest rollback material we will ever have."""
    run = _run(tenant, run_id)
    if run.status in ("running", "done"):
        raise RunError("This run has already run.")
    ep = _endpoint(tenant, run.role, run.system)
    changes, read_fail = [], 0
    with session() as s:
        rows = list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id).order_by(EntRunRow.n)).all())
    for r in rows[:50]:                      # a sample she can actually read; the cap keeps it honest
        payload = _j(r.payload, {})
        before = None
        if run.verb in ("update", "upsert") and r.key and ep is not None:
            try:
                code, data = _odata_call(ep, "GET", _paths(run.system, run.api, run.target, r.key)[1])
                before = data if code < 300 else None
            except Exception:
                read_fail += 1
        changes.append({"n": r.n, "key": r.key, "ab": _diff_preview(before, payload), "naya": payload})
        if before is not None:
            with session() as s:
                row = s.get(EntRunRow, r.id)
                row.before = json.dumps(before, ensure_ascii=False)[:20000]
    with session() as s:
        run2 = s.get(EntRun, run_id)
        run2.status = "dry_run"
        plan = _j(run2.plan, {})
        plan["hash"] = _plan_hash(run_id)
        run2.plan = json.dumps(plan, ensure_ascii=False)
    out = status(tenant, run_id)
    out["jhalak"] = changes
    out["dikhaye"] = len(changes)
    if read_fail:
        out["padh_nahi_paye"] = read_fail
    out["aage"] = ("This is only a preview - nothing has been written yet. It runs only after your approval."
                   if run.env != "production" else
                   "This is a PRODUCTION system. This is only a preview; to run it you must approve and type production.")
    return out


def _diff_preview(before: Any, after: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(before, dict):
        return {"naya_record": True}
    out = {}
    for k, v in after.items():
        old = before.get(k)
        if old != v:
            out[k] = {"pehle": old, "baad": v}
    return out or {"koi_badlav_nahi": True}


def _plan_hash(run_id: str) -> str:
    with session() as s:
        rows = s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id).order_by(EntRunRow.n)).all()
        return _hash(*[r.idem for r in rows])


def approve(tenant: str, run_id: str, by: str = "owner", confirm_env: str = "") -> dict[str, Any]:
    """Her tap. Tied to THIS set of rows: change them after she approves and the run refuses."""
    run = _run(tenant, run_id)
    if run.status != "dry_run":
        raise RunError("You must see the dry run (preview) first.")
    if run.env == "production" and (confirm_env or "").lower() != "production":
        raise RunError("This is PRODUCTION. Typing 'production' with your approval is required.")
    if run.api == "tooling" and run.env == "production":
        # A config change is not a record change: it can break the org for everyone, and Salesforce itself wants
        # tests behind it. Hoola does not pretend that is routine.
        log.warning("tooling deploy to production tenant=%s run=%s", tenant, run_id)
    plan = _j(run.plan, {})
    if plan.get("hash") != _plan_hash(run_id):
        raise RunError("The rows changed after the preview - look at the preview again.")
    with session() as s:
        r = s.get(EntRun, run_id)
        r.status = "running"
        r.approved_by = by[:80]
        r.started_at = now()
    return status(tenant, run_id)


def execute(tenant: str, run_id: str, batch: int = BATCH) -> dict[str, Any]:
    """Run the approved rows. Safe to call again after a crash: a `done` row is never posted twice."""
    run = _run(tenant, run_id)
    if run.status not in ("running", "failed"):
        raise RunError("This run is not ready to run yet (first the preview + your approval).")
    ep = _endpoint(tenant, run.role, run.system)
    done = failed = 0
    with session() as s:
        todo = list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                      EntRunRow.status.in_(("todo", "failed")))
                              .order_by(EntRunRow.n).limit(max(1, int(batch or BATCH)))).all())
        todo = [(r.id, r.n, r.key, r.payload) for r in todo]
    # ONE session for the whole batch. A SAP CSRF token is bound to the security session, so fetching it on
    # one connection and writing on another - which is what a per-call client did - can never work.
    unsure = 0
    call = dialect.Call(ep) if (run.rail == "odata" and ep is not None) else None
    try:
        for rid, n, key, payload in todo:
            body = _j(payload, {})
            note: dict[str, Any] = {}
            try:
                if run.rail == "odata":
                    if call is None:
                        raise RunError("The endpoint has been removed.")
                    coll, item = _paths(run.system, run.api, run.target, key)
                    if run.verb == "create":
                        code, data, note = call.create(coll, body, idem_key=_idem_of(rid))
                    else:
                        # Windchill demands the object be RESERVED before a PATCH and released after. A
                        # reservation we took and never gave back locks HER object against her own engineers,
                        # so `writing()` always releases, and a failed reserve means we never PATCH at all.
                        with call.writing(item):
                            code, data, note = call.update(item, body)
                else:
                    code, data = _composio_call(tenant, run.target, body)
                ok = code < 300
            except Ambiguous as amb:
                # Parked, NOT failed: execute() retries a failed row, and a retry here could post twice.
                with session() as s:
                    row = s.get(EntRunRow, rid)
                    row.status = "ambiguous"
                    row.error = amb.detail[:2000]
                    row.at = now()
                unsure += 1
                continue
            except dialect.DialectError as ex:
                code, data, ok = 0, {"error": str(ex)[:400], "bheja_nahi": True}, False
            except Exception as ex:                  # one bad row must never stop the rest
                code, data, ok = 0, {"error": str(ex)[:400]}, False
            if note:
                data = {"jawab": data, "note": note} if isinstance(data, (dict, list)) else {"note": note}
            with session() as s:
                row = s.get(EntRunRow, rid)
                # a 412 means somebody changed the row between our read and our write: the row we planned
                # against is not the row that is there now, so it must never be blind-retried.
                row.status = "done" if ok else ("ambiguous" if note.get("dobara_na_bhejo") else "failed")
                row.result = json.dumps(data, ensure_ascii=False, default=str)[:8000]
                row.error = "" if ok else json.dumps(data, ensure_ascii=False, default=str)[:2000]
                row.at = now()
            done += 1 if ok else 0
            failed += 0 if ok else 1
    finally:
        if call is not None:
            call.close()
    with session() as s:
        r = s.get(EntRun, run_id)
        # only a row never tried keeps the run "running". A failed row is retryable but must not hold the run
        # open for ever - the run goes to `failed`, which still resumes on the next execute().
        left = len(list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                          EntRunRow.status == "todo")).all()))
        r.ok_count = len(list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                                EntRunRow.status == "done")).all()))
        r.fail_count = len(list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                                  EntRunRow.status == "failed")).all()))
        unsure_left = len(list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                                  EntRunRow.status == "ambiguous")).all()))
        if left == 0:
            # an UNSURE row is not a pass and not a retryable fail: the run waits for her, because only she
            # can look in the system and say whether that record landed.
            r.status = "done" if (r.fail_count == 0 and unsure_left == 0) else "failed"
            r.done_at = now()
    out = status(tenant, run_id)
    out["is_baar"] = {"hue": done, "fail": failed, "pata_nahi": unsure}
    return out


def resolve(tenant: str, run_id: str, n: int, landed: bool, by: str = "owner") -> dict[str, Any]:
    """Clear an AMBIGUOUS row - the one thing only she can do.

    A row goes `ambiguous` when the answer never arrived: it may or may not have landed in her system, and
    `execute()` deliberately will not retry it, because a retry is how a record gets posted twice. Nobody but
    a person looking at the actual system can say which it was, so this is her answer coming back:

      landed=True  -> mark it done. Nothing is sent. The row is CLOSED, not written.
      landed=False -> put it back in the queue, so the next execute() sends it once.

    Shipped in v0.389 the state existed with no way out, which left such a run stuck at `failed` for ever.
    """
    run = _run(tenant, run_id)
    with session() as s:
        row = s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id, EntRunRow.n == int(n))).first()
        if row is None:
            raise RunError(f"Row {n} is not in this run.")
        if row.status != "ambiguous":
            raise RunError(f"Row {n} is '{row.status}' - only 'not known' rows are settled here.")
        if landed:
            row.status = "done"
            row.result = json.dumps({"aapne_bataya": "this row had gone through in the system", "by": by[:60],
                                     "bheja_nahi_gaya": True}, ensure_ascii=False)
            row.error = ""
        else:
            row.status = "todo"                  # back in the queue; the idempotency key is unchanged
            row.error = ""
        row.at = now()
    with session() as s:
        r = s.get(EntRun, run_id)
        r.ok_count = len(list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                                EntRunRow.status == "done")).all()))
        r.fail_count = len(list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                                  EntRunRow.status == "failed")).all()))
        left = len(list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                          EntRunRow.status.in_(("todo", "ambiguous")))).all()))
        if left:
            r.status = "running"                 # there is work again, so the run reopens
            r.done_at = None
        else:
            r.status = "done" if r.fail_count == 0 else "failed"
            r.done_at = now()
    out = status(tenant, run_id)
    out["aage"] = ("Row closed - nothing was sent." if landed else
                   "The row is back in the queue; it will go once on the next execute.")
    return out


def _idem_of(row_id: str) -> str:
    """The row's own idempotency hash - 32 stable hex characters, which is exactly what SAP wants for
    RequestID, and the same on every retry (that is the whole point)."""
    with session() as s:
        r = s.get(EntRunRow, row_id)
        return (r.idem if r else "") or ""


def _run(tenant: str, run_id: str) -> EntRun:
    with session() as s:
        r = s.get(EntRun, run_id)
        if r is None or r.tenant_id != tenant:
            raise RunError("Run not found.")
        return r


def status(tenant: str, run_id: str) -> dict[str, Any]:
    run = _run(tenant, run_id)
    with session() as s:
        fails = [{"n": r.n, "key": r.key, "error": (r.error or "")[:300]}
                 for r in s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                            EntRunRow.status == "failed").limit(20)).all()]
    with session() as s:
        unsure = [{"n": r.n, "key": r.key, "kyon": (r.error or "")[:300]}
                  for r in s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                             EntRunRow.status == "ambiguous").limit(20)).all()]
    out = {"run": run.id, "title": run.title, "system": run.system, "env": run.env, "rail": run.rail,
           "verb": run.verb, "target": run.target, "api": run.api, "status": run.status, "total": run.total,
           "hue": run.ok_count, "fail": run.fail_count, "baaki": run.total - run.ok_count - run.fail_count}
    if fails:
        out["jo_fail_hue"] = fails
    if unsure:
        out["pata_nahi"] = unsure
        out["pata_nahi_kya_karein"] = ("No answer came for these rows - they may have gone through. Hoola will "
                                       "NOT send them again (to avoid posting twice). Check in the system "
                                       "and tell me, then we continue.")
    if run.status == "dry_run":
        out["aage"] = "It runs after your approval."
    return out


def runs(tenant: str, role: str, limit: int = 20) -> list[dict[str, Any]]:
    with session() as s:
        return [{"run": r.id, "title": r.title, "status": r.status, "total": r.total, "hue": r.ok_count,
                 "fail": r.fail_count, "env": r.env, "at": r.created_at.isoformat() if r.created_at else ""}
                for r in s.scalars(select(EntRun).where(EntRun.tenant_id == tenant, EntRun.role == role)
                                   .order_by(EntRun.created_at.desc()).limit(limit)).all()]


def rollback_plan(tenant: str, run_id: str) -> dict[str, Any]:
    """What it would take to put it back. Only the rows whose BEFORE we actually captured can be restored, and
    saying which ones cannot is the point - a rollback that silently misses rows is worse than none."""
    run = _run(tenant, run_id)
    with session() as s:
        rows = list(s.scalars(select(EntRunRow).where(EntRunRow.run_id == run_id,
                                                      EntRunRow.status == "done").order_by(EntRunRow.n)).all())
        back = [{"key": r.key, "wapas": _j(r.before, {})} for r in rows if r.before]
        no_before = [r.key for r in rows if not r.before]
    return {"run": run.id, "wapas_ho_sakte": len(back), "nahi_ho_sakte": len(no_before),
            "rows": back[:50],
            "note": ("Rows that were NEWLY created cannot be undone - you must remove them in the system."
                     if no_before else "Every row's earlier version is kept."),
            "kaise": "This is a plan. To run it, make it a new update run and run it with preview + approval."}


# ---------------------------------------------------------------- Salesforce config deploy (sfmeta)
# v0.389 shipped sfmeta.py with NO caller, so the only documented way to change her org's configuration was
# unreachable. These three wrap it on the SAME discipline as every other write: nothing happens without a
# validation she has seen, and production rules are the vendor's, enforced in sfmeta.
def deploy_validate(tenant: str, role: str, components: list[dict[str, Any]],
                    test_level: str = "") -> dict[str, Any]:
    """The DRY RUN. Salesforce checks every component and runs the tests, and commits nothing."""
    from . import sfmeta
    R.role(role)
    if not R.may_write(role):
        raise RunError("This job never writes anywhere outside.")
    ep = _endpoint(tenant, role, "salesforce")
    if ep is None:
        raise RunError("The Salesforce address is not connected. Connect it in the app under Enterprise > Connect system.")
    if not isinstance(components, list) or not components:
        raise RunError("You must say what to deploy.")
    try:
        out = sfmeta.validate(ep, components, test_level)
    except sfmeta.MetaError as ex:
        raise RunError(str(ex))
    out["aage"] = ("This is only a check - nothing in the org changed. Look at the status; if it comes out clean, with your approval "
                   "this same check deploys directly for 10 days, without running the tests again.")
    return out


def deploy_status(tenant: str, role: str, deploy_id: str) -> dict[str, Any]:
    """One look. The caller keeps the id and comes back - it NEVER resubmits, because that deploys twice."""
    from . import sfmeta
    R.role(role)
    ep = _endpoint(tenant, role, "salesforce")
    if ep is None:
        raise RunError("The Salesforce address is not connected.")
    try:
        return sfmeta.poll(ep, deploy_id)
    except sfmeta.MetaError as ex:
        raise RunError(str(ex))


def deploy_go(tenant: str, role: str, validated_id: str, by: str = "owner",
              confirm_env: str = "") -> dict[str, Any]:
    """HER TAP. Quick-deploys the validation she saw; production needs the word as well, exactly like a row
    write, because a config change breaks the org for everyone, not one record."""
    from . import sfmeta
    R.role(role)
    if not R.may_write(role):
        raise RunError("This job never writes anywhere outside.")
    ep = _endpoint(tenant, role, "salesforce")
    if ep is None:
        raise RunError("The Salesforce address is not connected.")
    if ep.env == "production" and (confirm_env or "").lower() != "production":
        raise RunError("This is a PRODUCTION org. Typing 'production' with your approval is required.")
    try:
        out = sfmeta.quick_deploy(ep, validated_id)
    except sfmeta.MetaError as ex:
        raise RunError(str(ex))
    log.warning("salesforce config deploy tenant=%s role=%s env=%s deploy=%s by=%s",
                tenant, role, ep.env, out.get("deploy"), by)
    out["env"] = ep.env
    return out

# ---------------------------------------------------------------- v0.396 CONNECT: prove the address works
# Everything the enterprise suite does has, until now, been tested against the vendors' documentation and
# recorded HTTP - never against a customer system, because there was nowhere for her to put a credential. This
# is that place, and `verify` is the first call that ever reaches a real tenant.
#
# It is deliberately READ-ONLY and it writes NOTHING. What it reports is not "connected" as a feeling: it is
# what the endpoint actually did when asked -
#   - did the address answer at all, and with what HTTP code
#   - did the credential get past authentication (401 / 403 are told apart: wrong key vs no permission)
#   - could a CSRF token be fetched, where this system needs one for writes (SAP, Windchill)
#   - does a row carry an ETag, where this system demands If-Match on an update (SAP)
#   - does it accept the documented idempotent create (recorded, never assumed)
# so that a write later fails for a real reason, not because we believed a green tick.
VERIFY_PROBES = {
    "sap":        "$metadata",
    "windchill":  "PTC/GetCSRFToken()",
    "salesforce": "sobjects",
    "oracle":     "$metadata",
    "teamcenter": "$metadata",
}


def verify(tenant: str, role: str, system: str) -> dict[str, Any]:
    """Ask her endpoint, read-only, whether it really works - and say exactly what it answered."""
    R.role(role)
    ep = _endpoint(tenant, role, system)
    if ep is None:
        raise RunError(f"{system} address is not connected.")
    d = dialect.of(system)
    out: dict[str, Any] = {"system": system, "env": ep.env, "address": ep.base_url, "key": ep.auth_masked,
                           "jaanch": []}
    def step(name: str, ok: bool | None, detail: str = "") -> None:
        out["jaanch"].append({"kya": name, "theek": ok, "kaha": detail[:300]})

    probe = VERIFY_PROBES.get(system, "$metadata")
    try:
        with dialect.Call(ep, timeout=30) as c:
            code, data = c.get(probe, page=1)
            if code == 401:
                step("credential", False, "401 - the key is wrong or has expired.")
                out["theek"] = False
                out["aage"] = "Enter the key again. The address looks right (it answered)."
                return out
            if code == 403:
                step("credential", True, "The key worked, but 403 - this user has no permission for this.")
            elif code >= 400:
                step("address", False, f"HTTP {code}: " + json.dumps(data, default=str)[:180])
                out["theek"] = False
                out["aage"] = "This does not look like this system's API address. Ask your admin for the full API URL."
                return out
            else:
                step("address and credential", True, f"HTTP {code} - it answered.")

            # the write prerequisites, each only where that vendor needs it
            if d["csrf"]:
                try:
                    c.token(probe if system == "sap" else "")
                    step("CSRF token (needed to write)", True, "received.")
                except dialect.DialectError as ex:
                    step("CSRF token (needed to write)", False, str(ex))
            if d["etag"] == "required":
                step("If-Match / ETag", None,
                     "Not known without reading the row; it is taken from the row at update time. If it is missing, "
                     "Hoola skips that row - better than writing wrong.")
            if d["reserve"]:
                step("Reserve / UndoReservation", None,
                     "An object is changed only after checking it out; Hoola always checks it back in.")
            if d["idem"] == "sap":
                step("Idempotent create (RequestID)", None,
                     "Whether this job is on in your system will show at the first create.")
            out["kya_kya_chahiye"] = c.support()
    except RunError:
        raise
    except Exception as ex:                              # noqa: BLE001 - a network error is an ANSWER here
        step("address", False, f"{type(ex).__name__}: {str(ex)[:200]}")
        out["theek"] = False
        out["aage"] = ("Could not reach the address at all. Is the server open from outside? Check the firewall / VPN.")
        return out

    bad = [j for j in out["jaanch"] if j["theek"] is False]
    out["theek"] = not bad
    if not bad:
        with session() as s:
            r = s.scalars(select(EntEndpoint).where(EntEndpoint.tenant_id == tenant, EntEndpoint.role == role,
                                                    EntEndpoint.system == system)).first()
            if r is not None:
                r.verified_at = now()
        out["aage"] = ("Reading works. Writing still goes step by step: plan -> preview -> your approval."
                       + (" It is PRODUCTION, so you must also type 'production' with your approval."
                          if ep.env == "production" else ""))
    else:
        out["aage"] = "Fix what is marked red first; until then Hoola will not write to it."
    return out


def forget_endpoint(tenant: str, role: str, system: str) -> dict[str, Any]:
    """Remove the address and the sealed credential. Her runs and papers stay - only the way in is gone."""
    R.role(role)
    with session() as s:
        r = s.scalars(select(EntEndpoint).where(EntEndpoint.tenant_id == tenant, EntEndpoint.role == role,
                                                EntEndpoint.system == system)).first()
        if r is None:
            raise RunError(f"{system} address is not connected at all.")
        s.delete(r)
    return {"system": system, "hata_diya": True,
            "note": "Address and key both removed. Old runs and papers stay as they are."}
