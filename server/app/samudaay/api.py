"""HTTP routes for Community Sahayak. Every route that removes / bans / mutes / deletes / announces is HER tap from the app
(decide / alert act with by_tap=True). The Telegram webhook is public and checks Telegram's secret-token header itself."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from . import service as S


def _run(fn, *a, **k):
    try:
        return fn(*a, **k)
    except S.SamError as e:
        raise HTTPException(400, str(e)) from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()
    dep = [Depends(require_key)]

    # ---------------- public webhook (Telegram)
    @r.post("/api/samudaay/hook/telegram/{hook_id}")
    async def tg_hook(hook_id: str, request: Request):
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        try:
            update = await request.json()
        except Exception:
            raise HTTPException(400, "bad json") from None
        if not isinstance(update, dict):
            raise HTTPException(400, "bad update")
        try:
            return await asyncio.to_thread(S.telegram_hook, hook_id, secret, update)
        except PermissionError:
            raise HTTPException(403, "forbidden") from None

    # ---------------- overview + communities
    @r.get("/api/samudaay", dependencies=dep)
    def overview(tenant: str = Depends(current_tenant)):
        return S.day(tenant)

    @r.get("/api/samudaay/communities", dependencies=dep)
    def comms(tenant: str = Depends(current_tenant)):
        return {"communities": S.communities(tenant)}

    @r.patch("/api/samudaay/communities/{cid}", dependencies=dep)
    def comm_save(cid: str, body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.save_community, tenant, cid, **{k: body[k] for k in S.SETTABLE if k in body})

    @r.post("/api/samudaay/hoola", dependencies=dep)
    def hoola_link(body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.link_hoola, tenant, str(body.get("group") or ""))

    @r.get("/api/samudaay/communities/{cid}/report", dependencies=dep)
    def comm_report(cid: str, days: int = 7, tenant: str = Depends(current_tenant)):
        return _run(S.report, tenant, cid, days)

    # ---------------- Telegram bot (token typed only here)
    @r.get("/api/samudaay/telegram", dependencies=dep)
    def tg_get(tenant: str = Depends(current_tenant)):
        return {"bot": S.bot_view(tenant)}

    @r.put("/api/samudaay/telegram", dependencies=dep)
    def tg_put(body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        try:
            return _run(S.connect_telegram, tenant, str(body.get("token") or ""))
        except S.A.AdapterError as e:
            raise HTTPException(400, str(e)) from None

    @r.delete("/api/samudaay/telegram", dependencies=dep)
    def tg_del(tenant: str = Depends(current_tenant)):
        return S.disconnect_telegram(tenant)

    # ---------------- members
    @r.get("/api/samudaay/members", dependencies=dep)
    def mem_list(community: str = "", status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"members": _run(S.members, tenant, community, status, q)}

    @r.patch("/api/samudaay/members/{mid}", dependencies=dep)
    def mem_roles(mid: str, body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.set_roles, tenant, mid, list(body.get("roles") or ["member"]), note=body.get("note"))

    @r.delete("/api/samudaay/members/{mid}", dependencies=dep)
    def mem_forget(mid: str, tenant: str = Depends(current_tenant)):
        return _run(S.forget_member, tenant, mid)

    @r.post("/api/samudaay/register", dependencies=dep)
    def register(body: dict[str, Any] = Body(default={}), tenant: str = Depends(current_tenant)):
        return _run(S.register_file, tenant, str(body.get("community") or ""))

    # ---------------- templates (welcome / rules)
    @r.get("/api/samudaay/templates", dependencies=dep)
    def tpl_list(tenant: str = Depends(current_tenant)):
        return {"templates": S.templates(tenant)}

    @r.post("/api/samudaay/templates", dependencies=dep)
    def tpl_draft(body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.draft_template, tenant, str(body.get("text") or ""), str(body.get("community") or ""),
                    str(body.get("language") or ""), str(body.get("kind") or "welcome"), str(body.get("from_words") or ""))

    @r.post("/api/samudaay/templates/{tid}/approve", dependencies=dep)
    def tpl_approve(tid: str, body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.approve_template, tenant, tid, str(body.get("hash") or ""), by_tap=True)

    # ---------------- FAQ + questions
    @r.get("/api/samudaay/faqs", dependencies=dep)
    def faq_list(community: str = "", tenant: str = Depends(current_tenant)):
        return {"faqs": _run(S.faqs, tenant, community)}

    @r.post("/api/samudaay/faqs", dependencies=dep)
    def faq_add(body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.add_faq, tenant, str(body.get("question") or ""), str(body.get("answer") or ""),
                    str(body.get("community") or ""), list(body.get("keywords") or []), True, str(body.get("id") or ""))

    @r.delete("/api/samudaay/faqs/{fid}", dependencies=dep)
    def faq_del(fid: str, tenant: str = Depends(current_tenant)):
        return _run(S.delete_faq, tenant, fid)

    @r.get("/api/samudaay/questions", dependencies=dep)
    def q_list(status: str = "open", tenant: str = Depends(current_tenant)):
        return {"questions": S.questions(tenant, status=status)}

    @r.post("/api/samudaay/questions/{qid}", dependencies=dep)
    def q_answer(qid: str, body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        if body.get("ignore"):
            return _run(S.ignore_question, tenant, qid)
        return _run(S.answer_question, tenant, qid, str(body.get("answer") or ""), bool(body.get("save_faq", True)),
                    bool(body.get("send", True)), str(body.get("faq_id") or ""))

    # ---------------- join requests
    @r.post("/api/samudaay/joins/{rid}", dependencies=dep)
    def join(rid: str, body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.join_decide, tenant, rid, bool(body.get("yes")), "owner")

    # ---------------- alerts + actions (HER tap)
    @r.get("/api/samudaay/alerts", dependencies=dep)
    def al_list(status: str = "open", community: str = "", tenant: str = Depends(current_tenant)):
        return {"alerts": _run(S.alerts, tenant, community, status)}

    @r.post("/api/samudaay/alerts/{aid}/act", dependencies=dep)
    def al_act(aid: str, body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.alert_act, tenant, aid, str(body.get("kind") or ""), str(body.get("reason") or ""),
                    int(body.get("hours") or 24), str(body.get("text") or ""), by_tap=True)

    @r.post("/api/samudaay/alerts/{aid}/dismiss", dependencies=dep)
    def al_dismiss(aid: str, body: dict[str, Any] = Body(default={}), tenant: str = Depends(current_tenant)):
        return _run(S.dismiss_alert, tenant, aid, str(body.get("note") or ""), bool(body.get("allow_site")), bool(body.get("ok_word")))

    @r.get("/api/samudaay/actions", dependencies=dep)
    def act_list(status: str = "pending", tenant: str = Depends(current_tenant)):
        return {"actions": S.actions(tenant, status)}

    @r.post("/api/samudaay/actions", dependencies=dep)
    def act_new(body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.request_action, tenant, str(body.get("kind") or ""), str(body.get("community") or ""),
                    str(body.get("member") or ""), str(body.get("post") or ""), str(body.get("text") or ""),
                    str(body.get("reason") or ""), int(body.get("hours") or 24), asked_by="app")

    @r.post("/api/samudaay/actions/{xid}/decide", dependencies=dep)
    def act_decide(xid: str, body: dict[str, Any] = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.decide, tenant, xid, bool(body.get("yes")), str(body.get("hash") or ""), str(body.get("reason") or ""),
                    by_tap=True)

    @r.get("/api/samudaay/log", dependencies=dep)
    def act_log(days: int = 30, tenant: str = Depends(current_tenant)):
        return {"log": S.reason_log(tenant, days=days)}

    return r
