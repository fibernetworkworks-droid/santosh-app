"""HTTP routes of the Cyber Suraksha Sahayak (/api/cyber/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY way a block / disable / quarantine / wipe card is decided: POST /api/cyber/actions/{id}/decide from her app (her tap);
wiping also needs her fingerprint once a phone key is set up (428 -> POST /api/cyber/actions/{id}/challenge, sign, resend with proof).
API keys are typed only here (PUT /api/cyber/keys/{provider}); they are never returned."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

MAX_UPLOAD = 25 * 1024 * 1024


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/cyber", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.CyberError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    async def _read(f: UploadFile | None) -> tuple[str, bytes | None]:
        if f is None:
            return "", None
        data = await f.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "File 25 MB se badi hai.")
        return f.filename or "file", data

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("own_ips", "vip_names", "crown_hosts", "work_emails", "link_provider", "morning_time", "rules")
        return await run(S.save_settings, tenant, **{k: b[k] for k in keys if k in b})

    @r.put("/keys/{provider}")
    async def put_key(provider: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_key, tenant, provider, str(b.get("token") or ""), str(b.get("extra") or ""))

    @r.delete("/keys/{provider}")
    async def del_key(provider: str, tenant: str = Depends(current_tenant)):
        return await run(S.del_key, tenant, provider)

    # ---- alerts
    @r.post("/intake")
    async def intake(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.intake, tenant, str(b.get("text") or ""), str(b.get("file_id") or ""), None, "", str(b.get("source") or ""),
                         bool(b.get("include_hoola")))

    @r.post("/intake/file")
    async def intake_file(file: UploadFile = File(...), source: str = Form(""), tenant: str = Depends(current_tenant)):
        name, data = await _read(file)
        return await run(S.intake, tenant, "", "", data, name, source)

    @r.get("/alerts")
    async def list_alerts(level: str = "", status: str = "open", limit: int = 60, tenant: str = Depends(current_tenant)):
        return {"alerts": await run(S.alerts, tenant, level, status, limit)}

    @r.get("/alerts/{aid}")
    async def get_alert(aid: str, tenant: str = Depends(current_tenant)):
        return await run(S.get_alert, tenant, aid)

    @r.post("/alerts/{aid}/status")
    async def alert_status(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.set_alert, tenant, aid, str(_b(body).get("status") or ""))

    @r.post("/alerts/{aid}/teach")
    async def alert_teach(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.teach, tenant, aid, str(b.get("reason") or ""), str(b.get("scope") or ""))

    @r.get("/rules")
    async def list_rules(tenant: str = Depends(current_tenant)):
        return {"rules": await run(S.rules_list, tenant)}

    @r.delete("/rules/{rid}")
    async def del_rule(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.rule_remove, tenant, rid)

    # ---- checks
    @r.post("/check/email")
    async def check_email(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        did = {k: bool(b.get(k)) for k in ("clicked", "entered_password", "opened_attachment", "money", "gave_otp", "remote_access")}
        return await run(S.check_email, tenant, str(b.get("text") or ""), str(b.get("sender") or ""), b.get("links") or [],
                         b.get("attachments") or [], bool(b.get("report")), **did)

    @r.post("/check/link")
    async def check_link(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.check_link, tenant, b.get("urls") or b.get("url") or [])

    @r.post("/check/file")
    async def check_file(file: UploadFile | None = File(None), sha256: str = Form(""), tenant: str = Depends(current_tenant)):
        name, data = await _read(file)
        return await run(S.check_file, tenant, "", data, name, sha256)

    @r.post("/check/hash")
    async def check_hash(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.check_file, tenant, str(b.get("file_id") or ""), None, "", str(b.get("sha256") or ""))

    @r.get("/checks")
    async def list_checks(kind: str = "", tenant: str = Depends(current_tenant)):
        return {"checks": await run(S.checks, tenant, kind)}

    # ---- domains / breaches / software / advisories
    @r.get("/domains")
    async def list_domains(tenant: str = Depends(current_tenant)):
        return {"domains": await run(S.domains, tenant)}

    @r.post("/domains")
    async def add_domain(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.add_domain, tenant, str(_b(body).get("domain") or ""))

    @r.post("/domains/{did}/verify")
    async def verify_domain(did: str, tenant: str = Depends(current_tenant)):
        return await run(S.verify_domain, tenant, did)

    @r.post("/domains/{did}/check")
    async def domain_check(did: str, tenant: str = Depends(current_tenant)):
        return await run(S.posture, tenant, did)

    @r.post("/domains/{did}/breach")
    async def domain_breach(did: str, tenant: str = Depends(current_tenant)):
        def go():
            d = next((x for x in S.domains(tenant) if x["id"] == did), None)
            if not d:
                raise S.CyberError("Domain nahi mila.")
            return S.breach(tenant, d["domain"])
        return await run(go)

    @r.delete("/domains/{did}")
    async def del_domain(did: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_domain, tenant, did)

    @r.post("/breach")
    async def breach(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.breach, tenant, str(_b(body).get("domain") or ""))

    @r.get("/software")
    async def list_software(tenant: str = Depends(current_tenant)):
        return {"software": await run(S.software, tenant)}

    @r.post("/software")
    async def add_software(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_software, tenant, str(b.get("product") or ""), str(b.get("vendor") or ""), str(b.get("version") or ""),
                         str(b.get("cpe") or ""), str(b.get("where") or ""))

    @r.post("/software/sync")
    async def sync_software(tenant: str = Depends(current_tenant)):
        return await run(S.sync_assets, tenant)

    @r.delete("/software/{sid}")
    async def del_software(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_software, tenant, sid)

    @r.post("/advisories/refresh")
    async def refresh(tenant: str = Depends(current_tenant)):
        return await run(S.refresh_advisories, tenant)

    @r.get("/advisories")
    async def list_adv(status: str = "new", tenant: str = Depends(current_tenant)):
        return {"advisories": await run(S.advisories, tenant, status)}

    @r.post("/advisories/{aid}/status")
    async def adv_status(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.mark_advisory, tenant, aid, str(_b(body).get("status") or ""))

    # ---- incidents
    @r.get("/incidents")
    async def list_incidents(status: str = "", tenant: str = Depends(current_tenant)):
        return {"incidents": await run(S.incidents, tenant, status)}

    @r.post("/incidents")
    async def new_incident(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        did = {k: bool(b.get(k)) for k in ("clicked", "entered_password", "opened_attachment", "money", "gave_otp", "remote_access")}
        return await run(S.new_incident, tenant, str(b.get("title") or ""), str(b.get("kind") or ""), b.get("alert_ids") or [],
                         b.get("check_ids") or [], str(b.get("what") or ""), str(b.get("systems") or ""), bool(b.get("personal_data")),
                         bool(b.get("clock", True)), **did)

    @r.get("/incidents/{iid}")
    async def get_incident(iid: str, tenant: str = Depends(current_tenant)):
        return await run(S.get_incident, tenant, iid)

    @r.patch("/incidents/{iid}")
    async def patch_incident(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("title", "what", "impact", "done", "lessons", "systems", "personal_data")
        return await run(S.incident_update, tenant, iid, **{k: b[k] for k in keys if k in b})

    @r.post("/incidents/{iid}/timeline")
    async def add_tl(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.incident_add, tenant, iid, str(b.get("what") or ""), str(b.get("at") or ""))

    @r.post("/incidents/{iid}/cert_in")
    async def inc_cert_in(iid: str, tenant: str = Depends(current_tenant)):
        return await run(S.cert_in, tenant, iid)

    @r.post("/incidents/{iid}/close")
    async def inc_close(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.incident_close, tenant, iid, str(_b(body).get("lessons") or ""))

    @r.post("/incidents/{iid}/note")
    async def inc_note(iid: str, tenant: str = Depends(current_tenant)):
        return await run(S.note_files, tenant, iid)

    # ---- containment: HER tap
    @r.get("/actions")
    async def list_actions(status: str = "", tenant: str = Depends(current_tenant)):
        return {"actions": await run(S.actions, tenant, status)}

    @r.post("/actions")
    async def new_action(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_action, tenant, str(b.get("kind") or ""), str(b.get("target") or ""), str(b.get("reason") or ""),
                         str(b.get("incident") or ""), str(b.get("alert") or ""))

    @r.post("/actions/{aid}/challenge")
    async def act_challenge(aid: str, tenant: str = Depends(current_tenant)):
        return await run(S.action_challenge, tenant, aid)

    @r.post("/actions/{aid}/decide")
    async def act_decide(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        try:
            return await asyncio.to_thread(S.decide_action, tenant, aid, bool(b.get("yes")), str(b.get("hash") or ""), b.get("proof"),
                                           str(b.get("reason") or ""), by_tap=True)
        except S.CyberError as e:
            if str(e) in ("fingerprint_needed", "fingerprint_invalid"):
                return JSONResponse({"detail": str(e), "fingerprint": True}, status_code=428)
            raise HTTPException(400, str(e))

    @r.post("/actions/{aid}/done")
    async def act_done(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.action_done, tenant, aid, bool(b.get("ok", True)), str(b.get("note") or ""))

    return r
