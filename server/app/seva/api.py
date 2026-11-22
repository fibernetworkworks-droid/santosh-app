"""HTTP routes for Seva Sahayak (Profile > Seva sahayak in the app). main.py:
`app.include_router(seva_api.make_router(require_key, current_tenant))`.

The ONLY way a refund / exception is decided is `POST /api/seva/exceptions/{id}/decide` (her tap in the app); a money card
answers 428 `fingerprint_needed` until the phone signs `POST /api/seva/exceptions/{id}/challenge`."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, UploadFile


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S
    r = APIRouter(prefix="/api/seva", dependencies=[Depends(require_key)])

    async def run(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except S.SevaError as e:
            msg = str(e)
            if msg in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, msg)
            raise HTTPException(400, msg)

    def _b(body: Any) -> dict:
        return body if isinstance(body, dict) else {}

    @r.get("")
    async def seva_all(tenant: str = Depends(current_tenant)):
        return await run(S.all_in_one, tenant)

    @r.get("/day")
    async def seva_day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def seva_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def seva_save_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        keys = ("kind", "sla", "ecommerce", "officer", "officer_contact", "lang", "csat_on", "auto_ack", "morning_time", "policy") + S.POLICY_KEYS
        return await run(S.save_settings, tenant, **{k: v for k, v in _b(body).items() if k in keys})

    # ---- knowledge base
    @r.get("/kb")
    async def kb(status: str = "", q: str = "", kind: str = "", tenant: str = Depends(current_tenant)):
        return {"entries": await run(S.kb_list, tenant, status, q, kind), "gaps": await run(S.gaps, tenant, 30, 10)}

    @r.post("/kb")
    async def kb_add(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.kb_add, tenant, b.get("question", ""), b.get("answer", ""), b.get("kind") or "faq", b.get("aliases") or [],
                         b.get("lang", ""))

    @r.post("/kb/import")
    async def kb_import(file: UploadFile | None = File(None), file_id: str = Form(""), url: str = Form(""), text: str = Form(""),
                        tenant: str = Depends(current_tenant)):
        data = await file.read() if file is not None else None
        if data is not None and len(data) > 20 * 1024 * 1024:
            raise HTTPException(413, "The file is larger than 20 MB.")
        return await run(S.kb_import, tenant, file_id, data, (file.filename or "file") if file is not None else "", url, text)

    @r.post("/kb/import_link")
    async def kb_import_link(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.kb_import, tenant, str(b.get("file_id") or ""), None, "", str(b.get("url") or ""), str(b.get("text") or ""))

    @r.post("/kb/ask")
    async def kb_ask(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Test: what would Hoola answer a customer? (logged as channel 'test')"""
        return await run(S.answer, tenant, _b(body).get("question", ""), "test", "", _b(body).get("lang", ""))

    @r.post("/kb/approve")
    async def kb_approve(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.kb_approve, tenant, _b(body).get("ids") or [])

    @r.patch("/kb/{entry_id}")
    async def kb_edit(entry_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = {k: v for k, v in _b(body).items() if k in ("question", "answer", "aliases", "kind")}
        return await run(S.kb_edit, tenant, entry_id, **b)

    @r.delete("/kb/{entry_id}")
    async def kb_remove(entry_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.kb_remove, tenant, entry_id)

    # ---- G1 one business brain: versions, owner / review date, stale, help-center import, suggestions
    async def brun(fn, *a, **kw):
        from . import brain as B
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (B.BrainError, S.SevaError) as e:
            raise HTTPException(400, str(e))

    @r.get("/brain")
    async def kb_brain(tenant: str = Depends(current_tenant)):
        from . import brain as B
        return await brun(B.overview, tenant)

    @r.get("/kb/{entry_id}/history")
    async def kb_history(entry_id: str, tenant: str = Depends(current_tenant)):
        from . import brain as B
        return await brun(B.history, tenant, entry_id)

    @r.post("/kb/{entry_id}/restore")
    async def kb_restore(entry_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import brain as B
        return await brun(B.restore, tenant, entry_id, int(_b(body).get("version") or 0))

    @r.post("/kb/{entry_id}/meta")
    async def kb_meta(entry_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import brain as B
        b = _b(body)
        return await brun(B.meta, tenant, entry_id, b.get("owner"), b.get("review_by"), bool(b.get("checked")))

    @r.post("/kb/helpcenter")
    async def kb_helpcenter(file: UploadFile | None = File(None), url: str = Form(""), tenant: str = Depends(current_tenant)):
        from . import brain as B
        data = await file.read() if file is not None else None
        if data is not None and len(data) > 20 * 1024 * 1024:
            raise HTTPException(413, "The file is larger than 20 MB.")
        return await brun(B.import_helpcenter, tenant, url, data, (file.filename or "file") if file is not None else "")

    @r.post("/suggestions/{sid}")
    async def kb_suggestion(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Her tap on a suggestion from solved tickets: approve (words may be edited) or dismiss."""
        from . import brain as B
        b = _b(body)
        return await brun(B.suggestion_decide, tenant, sid, bool(b.get("yes")), str(b.get("question") or ""), str(b.get("answer") or ""))

    # ---- G2 the answer engine: try a message, trust levels, drafts a person sends
    async def erun(fn, *a, **kw):
        from . import engine as E
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (E.EngineError, S.SevaError) as e:
            raise HTTPException(400, str(e))

    @r.post("/engine/try")
    async def engine_try(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """What would Hoola do with this customer message? (no customer, nothing sent; drafts are not saved)"""
        from . import engine as E
        b = _b(body)
        ch = str(b.get("channel") or "whatsapp")
        out = await erun(E.reply, tenant, str(b.get("text") or b.get("question") or ""), ch if ch in E.CHANNELS else "whatsapp", "", "test")
        if out.get("draft_id"):
            await erun(E.draft_decide, tenant, out["draft_id"], "discard")
        return out

    @r.get("/trust")
    async def trust_get(tenant: str = Depends(current_tenant)):
        from . import engine as E
        return await erun(E.trust, tenant)

    @r.put("/trust")
    async def trust_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import engine as E
        b = _b(body)
        return await erun(E.set_trust, tenant, str(b.get("level") or ""), str(b.get("topic") or "*"), str(b.get("channel") or "*"))

    @r.get("/drafts")
    async def drafts_get(tenant: str = Depends(current_tenant)):
        from . import engine as E
        return {"drafts": await erun(E.drafts, tenant)}

    @r.post("/drafts/{draft_id}")
    async def drafts_decide(draft_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """A person's tap on a reply Hoola drafted: send (words may be edited), I sent it, or discard."""
        from . import engine as E
        b = _b(body)
        return await erun(E.draft_decide, tenant, draft_id, str(b.get("action") or ""), str(b.get("text") or ""))

    # ---- G8 her ticket workflow
    async def frun(fn, *a, **kw):
        from . import flow as FL
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (FL.FlowError, S.SevaError) as e:
            raise HTTPException(400, str(e))

    @r.get("/flows")
    async def flows_get(tenant: str = Depends(current_tenant)):
        from . import flow as FL
        return {"flows": await frun(FL.flows, tenant), "board": await frun(FL.board, tenant), "owners": list(FL.OWNER_KINDS)}

    @r.put("/flows/{key}")
    async def flows_put(key: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import flow as FL
        return await frun(FL.save, tenant, _b(body) | {"key": key})

    @r.delete("/flows/{key}")
    async def flows_del(key: str, tenant: str = Depends(current_tenant)):
        from . import flow as FL
        return await frun(FL.remove, tenant, key)

    @r.post("/tickets/{ref}/move")
    async def ticket_move(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import flow as FL
        b = _b(body)
        return await frun(FL.move, tenant, ref, str(b.get("to") or ""), "owner", str(b.get("why") or ""),
                          b.get("fields") if isinstance(b.get("fields"), dict) else {})

    @r.get("/tickets/{ref}/moves")
    async def ticket_moves(ref: str, tenant: str = Depends(current_tenant)):
        from . import flow as FL
        t = await frun(S.ticket, tenant, ref)
        return {"moves": await frun(FL.history, tenant, t["id"])}

    @r.get("/stuck")
    async def stuck_get(stage: str = "", older_h: float = 0, tenant: str = Depends(current_tenant)):
        from . import flow as FL
        from . import watch as W
        if stage or older_h:
            return {"stuck": await frun(FL.stuck, tenant, stage, older_h)}
        return {"stuck": await wrun(W.stuck_all, tenant)}

    # ---- G9 watching until solved
    async def wrun(fn, *a, **kw):
        from . import watch as W
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (W.WatchError, S.SevaError) as e:
            raise HTTPException(400, str(e))

    @r.get("/watch")
    async def watch_get(tenant: str = Depends(current_tenant)):
        from . import watch as W
        return await wrun(W.watching, tenant)

    @r.put("/watch")
    async def watch_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import watch as W
        return await wrun(W.save, tenant, _b(body))

    @r.get("/reminders")
    async def reminders_get(ticket: str = "", tenant: str = Depends(current_tenant)):
        from . import watch as W
        tid = (await frun(S.ticket, tenant, ticket))["id"] if ticket else ""
        return {"reminders": await wrun(W.reminders, tenant, tid, 100)}

    # ---- G4 messaging apps
    async def crun(fn, *a, **kw):
        from . import channels as CH
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (CH.ChannelError, S.SevaError) as e:
            raise HTTPException(400, str(e))

    @r.get("/channels")
    async def channels_get(tenant: str = Depends(current_tenant)):
        from . import channels as CH
        return await crun(CH.overview, tenant)

    @r.post("/channels")
    async def channels_add(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Her keys, typed in the app: sealed at once, never returned."""
        from . import channels as CH
        b = _b(body)
        return await crun(CH.connect, tenant, str(b.get("kind") or ""), b.get("keys") if isinstance(b.get("keys"), dict) else {},
                          str(b.get("name") or ""), str(b.get("brand") or ""), str(b.get("region") or ""))

    @r.post("/channels/{cid}/check")
    async def channels_check(cid: str, tenant: str = Depends(current_tenant)):
        from . import channels as CH
        return await crun(CH.check, tenant, cid)

    @r.delete("/channels/{cid}")
    async def channels_del(cid: str, tenant: str = Depends(current_tenant)):
        from . import channels as CH
        return await crun(CH.remove, tenant, cid)

    @r.get("/webchat")
    async def webchat_get(tenant: str = Depends(current_tenant)):
        from . import webchat as WC
        return await wrun_web(WC.view, tenant)

    @r.put("/webchat/{kind}")
    async def webchat_put(kind: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import webchat as WC
        return await wrun_web(WC.setup, tenant, kind, _b(body))

    @r.post("/webchat/{kind}/rotate")
    async def webchat_rotate(kind: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import webchat as WC
        return await wrun_web(WC.rotate, tenant, kind, str(_b(body).get("what") or ""))

    async def mrun(fn, *a, **kw):
        from . import supportmail as SM
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except SM.MailError as e:
            raise HTTPException(400, str(e))

    @r.get("/email")
    async def email_get(tenant: str = Depends(current_tenant)):
        from . import supportmail as SM
        return {"email": await mrun(SM.view, tenant)}

    @r.put("/email")
    async def email_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Her mailbox password typed in the app: sealed at once, never returned."""
        from . import supportmail as SM
        return await mrun(SM.setup, tenant, _b(body))

    @r.post("/email/check")
    async def email_check(tenant: str = Depends(current_tenant)):
        from . import supportmail as SM
        return await mrun(SM.check, tenant)

    @r.post("/email/poll")
    async def email_poll(tenant: str = Depends(current_tenant)):
        from . import supportmail as SM
        return {"read": await mrun(SM.poll, tenant, True)}

    async def prun(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @r.get("/phone")
    async def phone_get(tenant: str = Depends(current_tenant)):
        """G3: her phone line in the support desk: warm transfer, WhatsApp calls, the latest calls with their tickets."""
        from . import calls as SC
        return {"phone": await prun(SC.phone_view, tenant)}

    @r.put("/phone")
    async def phone_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import calls as SC
        b = _b(body)
        warm = b.get("warm_transfer")
        return {"phone": await prun(SC.save_phone, tenant, None if warm is None else bool(warm), b.get("wa_calls"))}

    # ---------------------------------------------------------------- G12 her own helpdesk (layer mode)
    async def lrun(fn, *a, **kw):
        from . import layer as LY
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except LY.LayerError as e:
            raise HTTPException(400, str(e))
        except (TypeError, ValueError) as e:
            raise HTTPException(400, f"Invalid details: {e}")

    @r.get("/helpdesk")
    async def helpdesk_get(tenant: str = Depends(current_tenant)):
        from . import layer as LY
        return {"helpdesk": await lrun(LY.view, tenant)}

    @r.put("/helpdesk")
    async def helpdesk_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Her helpdesk's key, typed in the app: sealed at once, never returned."""
        from . import layer as LY
        return {"helpdesk": await lrun(LY.connect, tenant, _b(body))}

    @r.put("/helpdesk/settings")
    async def helpdesk_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import layer as LY
        return {"helpdesk": await lrun(LY.save_settings, tenant, _b(body))}

    @r.post("/helpdesk/check")
    async def helpdesk_check(tenant: str = Depends(current_tenant)):
        from . import layer as LY
        return {"helpdesk": await lrun(LY.check, tenant)}

    @r.post("/helpdesk/run")
    async def helpdesk_run(tenant: str = Depends(current_tenant)):
        from . import layer as LY
        return await lrun(LY.run, tenant, True)

    @r.delete("/helpdesk")
    async def helpdesk_off(tenant: str = Depends(current_tenant)):
        from . import layer as LY
        return await lrun(LY.disconnect, tenant)

    # ---------------------------------------------------------------- G11 quality, simulations, the law, data rights, audit
    async def qrun(fn, *a, **kw):
        from . import quality as QL
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (QL.QualityError, S.SevaError) as e:
            raise HTTPException(400, str(e))
        except (TypeError, ValueError) as e:
            raise HTTPException(400, f"Invalid details: {e}")

    @r.get("/quality")
    async def quality_all(tenant: str = Depends(current_tenant)):
        from . import quality as QL
        return await qrun(QL.overview, tenant)

    @r.put("/quality/settings")
    async def quality_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import quality as QL
        return {"settings": await qrun(QL.save_settings, tenant, _b(body))}

    @r.get("/quality/sample")
    async def quality_sample(n: int = 0, tenant: str = Depends(current_tenant)):
        from . import quality as QL
        return {"sample": await qrun(QL.sample, tenant, n)}

    @r.post("/quality/marks/{qid}")
    async def quality_mark(qid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import quality as QL
        b = _b(body)
        return await qrun(QL.mark, tenant, qid, str(b.get("mark") or ""), str(b.get("note") or ""))

    @r.post("/quality/card")
    async def quality_card(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """The simulated customers through her answer engine. Nothing is saved or sent."""
        from . import quality as QL
        b = _b(body)
        return await qrun(QL.run_card, tenant, b.get("channels") or None, b.get("languages") or None)

    @r.post("/quality/replay")
    async def quality_replay(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import quality as QL
        return await qrun(QL.replay, tenant, int(_b(body).get("days") or 7))

    @r.post("/quality/export")
    async def quality_export(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import quality as QL
        return await qrun(QL.export_customer, tenant, str(_b(body).get("customer") or ""))

    @r.post("/quality/delete")
    async def quality_delete(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import quality as QL
        b = _b(body)
        return await qrun(QL.delete_customer, tenant, str(b.get("customer") or ""), str(b.get("confirm") or ""))

    @r.get("/quality/audit")
    async def quality_audit(days: int = 30, kind: str = "", tenant: str = Depends(current_tenant)):
        from . import quality as QL
        return {"audit": await qrun(QL.audit, tenant, max(1, min(365, days)), kind)}

    @r.get("/quality/audit.csv")
    async def quality_audit_csv(days: int = 30, tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response as R_
        from . import quality as QL
        body = await qrun(QL.audit_csv, tenant, max(1, min(365, days)))
        return R_(content=body, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=support-audit.csv"})

    @r.post("/translate")
    async def translate(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """A customer's words in her language, beside the original (the original is never changed)."""
        from . import engine as E
        b = _b(body)
        text = S._clean(b.get("text"), 3000)
        to = str(b.get("to") or "en")[:10]
        if not text:
            raise HTTPException(400, "Nothing to translate.")
        words, done = await asyncio.to_thread(E.in_lang, text, to, E.lang_code(text))
        return {"text": words, "translated": done, "from": E.lang_code(text)}

    # ---------------------------------------------------------------- G10 teams, queues and rules
    async def trun(fn, *a, **kw):
        from . import teams as TM
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (TM.TeamError, S.SevaError) as e:
            raise HTTPException(400, str(e))
        except (TypeError, ValueError) as e:
            raise HTTPException(400, f"Invalid details: {e}")

    @r.get("/team")
    async def team_all(tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.overview, tenant)

    @r.get("/team/board")
    async def team_board(tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return {"board": await trun(TM.board, tenant)}

    @r.post("/team/people")
    async def team_person_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return {"person": await trun(TM.save_agent, tenant, _b(body))}

    @r.put("/team/people/{aid}")
    async def team_person_put(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return {"person": await trun(TM.save_agent, tenant, _b(body), aid)}

    @r.delete("/team/people/{aid}")
    async def team_person_del(aid: str, tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.remove_agent, tenant, aid)

    @r.put("/team/queues")
    async def team_queue_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return {"queue": await trun(TM.save_queue, tenant, _b(body))}

    @r.delete("/team/queues/{key}")
    async def team_queue_del(key: str, tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.remove_queue, tenant, key)

    @r.put("/team/routes")
    async def team_routes(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.save_routes, tenant, _b(body).get("routes") or [])

    @r.post("/team/rules")
    async def team_rule_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return {"rule": await trun(TM.save_rule, tenant, _b(body))}

    @r.put("/team/rules/{rid}")
    async def team_rule_put(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return {"rule": await trun(TM.save_rule, tenant, _b(body), rid)}

    @r.delete("/team/rules/{rid}")
    async def team_rule_del(rid: str, tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.remove_rule, tenant, rid)

    @r.put("/team/roles")
    async def team_role(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        b = _b(body)
        return await trun(TM.save_role, tenant, str(b.get("name") or ""), list(b.get("perms") or []))

    @r.put("/team/bands")
    async def team_bands(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        b = _b(body)
        return await trun(TM.save_bands, tenant, b.get("bands") or [], str(b.get("currency") or ""))

    @r.put("/team/fields")
    async def team_fields(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.save_fields, tenant, _b(body).get("fields") or [])

    @r.put("/team/views")
    async def team_view_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        b = _b(body)
        return await trun(TM.save_view, tenant, str(b.get("name") or ""), b.get("filters") or {})

    @r.delete("/team/views/{name}")
    async def team_view_del(name: str, tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.remove_view, tenant, name)

    @r.get("/team/views/{name}")
    async def team_view_get(name: str, tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.view_tickets, tenant, name)

    @r.put("/tickets/{ref}/custom")
    async def ticket_custom(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.set_custom, tenant, ref, _b(body))

    @r.post("/tickets/{ref}/macro/{mid}")
    async def ticket_macro(ref: str, mid: str, tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.run_macro, tenant, ref, mid)

    @r.put("/macros/{mid}/actions")
    async def macro_actions(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import teams as TM
        return await trun(TM.set_macro_actions, tenant, mid, _b(body))

    @r.post("/exceptions/{exc_id}/steps/{sid}/link")
    async def step_link(exc_id: str, sid: str, tenant: str = Depends(current_tenant)):
        """A new one-time approval link for the person at this step (the old one stops working)."""
        from . import teams as TM
        await trun(TM.new_link, tenant, sid)
        return {"chain": await trun(TM.chain, tenant, exc_id)}

    @r.get("/chatfiles/{fid}")
    async def webchat_file(fid: str, tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response as R_
        from . import webchat as WC
        data, mime, name = await wrun_web(WC.file_for_owner, tenant, fid)
        return R_(content=data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{name}"',
                                                          "X-Content-Type-Options": "nosniff"})

    async def wrun_web(fn, *a, **kw):
        from . import webchat as WC
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except WC.WebError as e:
            raise HTTPException(e.status, str(e))

    @r.get("/chats/{customer}")
    async def chat_thread(customer: str, tenant: str = Depends(current_tenant)):
        from . import channels as CH
        return await crun(CH.thread, tenant, customer)

    @r.post("/chats/{customer}/send")
    async def chat_send(customer: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import channels as CH
        b = _b(body)
        return await crun(CH.reply_as_person, tenant, customer, str(b.get("text") or ""), str(b.get("by") or "owner"))

    # ---- G7 hand-over to a person
    async def hrun(fn, *a, **kw):
        from . import handover as H
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (H.HandoverError, S.SevaError) as e:
            raise HTTPException(400, str(e))

    @r.get("/handovers")
    async def handovers_get(status: str = "open", ticket: str = "", tenant: str = Depends(current_tenant)):
        from . import handover as H
        if ticket or status != "open":
            return {"handovers": await hrun(H.handovers, tenant, status if status != "all" else "", ticket)}
        return await hrun(H.overview, tenant)

    @r.post("/handovers")
    async def handovers_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """She hands a ticket to a person herself (e.g. a call she took)."""
        from . import handover as H
        b = _b(body)
        return await hrun(H.start, tenant, "", str(b.get("channel") or "other"), str(b.get("reason") or ""), str(b.get("rule") or "asked"),
                          "", "", "", str(b.get("ticket") or ""), "owner")

    @r.get("/handovers/{hid}")
    async def handover_get(hid: str, tenant: str = Depends(current_tenant)):
        from . import handover as H
        return await hrun(H.get, tenant, hid)

    @r.post("/handovers/{hid}/take")
    async def handover_take(hid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import handover as H
        return await hrun(H.take, tenant, hid, str(_b(body).get("by") or "owner"))

    @r.post("/handovers/{hid}/back")
    async def handover_back(hid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import handover as H
        b = _b(body)
        return await hrun(H.hand_back, tenant, hid, str(b.get("note") or ""), str(b.get("by") or "owner"))

    @r.get("/handover/rules")
    async def handover_rules(tenant: str = Depends(current_tenant)):
        from . import handover as H
        return await hrun(H.view, tenant)

    @r.put("/handover/rules")
    async def handover_rules_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import handover as H
        return await hrun(H.save, tenant, _b(body))

    @r.post("/tickets/{ref}/confirm")
    async def ticket_confirm(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """She records the customer's answer herself (they told her on the phone)."""
        from . import watch as W
        b = _b(body)
        return await wrun(W.confirm, tenant, ref, bool(b.get("yes")), "owner", str(b.get("words") or ""))

    # ---- macros
    @r.get("/macros")
    async def macros(tenant: str = Depends(current_tenant)):
        return {"macros": await run(S.macros, tenant)}

    @r.post("/macros")
    async def macro_add(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.macro_add, tenant, b.get("name", ""), b.get("text", ""), b.get("lang", ""))

    @r.post("/macros/{macro_id}/approve")
    async def macro_approve(macro_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.macro_approve, tenant, macro_id, _b(body).get("texts"))

    @r.delete("/macros/{macro_id}")
    async def macro_remove(macro_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.macro_remove, tenant, macro_id)

    # ---- tickets
    @r.get("/tickets")
    async def tickets(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"tickets": await run(S.tickets, tenant, status, q), "duplicates": await run(S.duplicates, tenant)}

    @r.post("/tickets")
    async def ticket_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.new_ticket, tenant, b.get("text", ""), b.get("channel") or "phone", "", b.get("name", ""), b.get("phone", ""),
                         b.get("category", ""), b.get("priority", ""), "owner")

    @r.get("/tickets/{ref}")
    async def ticket_get(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.ticket, tenant, ref)

    @r.post("/tickets/{ref}/{action}")
    async def ticket_act(ref: str, action: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if action == "update":
            return await run(S.update, tenant, ref, b.get("status", ""), b.get("priority", ""), b.get("public", ""), b.get("note", ""),
                             b.get("assignee"), b.get("category", ""), "owner")
        if action == "reply":
            return await run(S.reply, tenant, ref, b.get("text", ""), b.get("macro", ""))
        if action == "note":
            return await run(S.note, tenant, ref, b.get("text", ""))
        if action == "merge":
            return await run(S.merge, tenant, ref, b.get("into", ""))
        if action == "csat":
            return await run(S.csat, tenant, ref, b.get("score", 0), b.get("comment", ""))
        if action == "exception":
            return await run(S.exception_request, tenant, b.get("kind") or "refund", b.get("reason", ""), b.get("amount", 0), ref,
                             b.get("days_since"), "owner")
        raise HTTPException(404, "action not found")

    # ---- exceptions (her tap only)
    @r.get("/exceptions")
    async def exceptions(status: str = "", tenant: str = Depends(current_tenant)):
        return {"exceptions": await run(S.exceptions, tenant, status)}

    @r.post("/exceptions")
    async def exception_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.exception_request, tenant, b.get("kind") or "other", b.get("reason", ""), b.get("amount", 0), b.get("ticket", ""),
                         b.get("days_since"), "owner", "", "", b.get("customer", ""))

    @r.post("/exceptions/{exc_id}/challenge")
    async def exception_challenge(exc_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.fp_challenge, tenant, exc_id)

    @r.post("/exceptions/{exc_id}/decide")
    async def exception_decide(exc_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide, tenant, exc_id, bool(b.get("yes")), b.get("hash", ""), b.get("proof"), b.get("note", ""), b.get("amount"),
                         by_tap=True)

    @r.post("/exceptions/{exc_id}/sent")
    async def exception_sent(exc_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.mark_sent, tenant, exc_id, _b(body).get("ref", ""))

    @r.post("/exceptions/{exc_id}/cancel")
    async def exception_cancel(exc_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel_exception, tenant, exc_id)

    # ---- numbers
    @r.get("/report")
    async def report(days: int = 30, tenant: str = Depends(current_tenant)):
        return await run(S.report, tenant, days)

    @r.get("/gaps")
    async def gaps(days: int = 30, tenant: str = Depends(current_tenant)):
        return {"gaps": await run(S.gaps, tenant, days, 20)}

    return r


def make_public_router() -> APIRouter:
    """G4: the webhook door her messaging apps call (no Hoola key: every call is checked against that app's own signature)."""
    from fastapi.responses import Response
    r = APIRouter(prefix="/api/support/in")

    async def door(token: str, request: Request) -> Response:
        from . import channels as CH
        raw = await request.body()
        form: dict = {}
        if "application/x-www-form-urlencoded" in (request.headers.get("content-type") or ""):
            from urllib.parse import parse_qsl
            form = dict(parse_qsl(raw.decode("utf-8", "replace"), keep_blank_values=True))
        from ..config import get_settings
        base = (get_settings().public_base_url or str(request.base_url)).rstrip("/")
        url = base + request.url.path + (("?" + request.url.query) if request.url.query else "")
        st, body, media = await asyncio.to_thread(CH.inbound, token, request.method, dict(request.headers), raw, url, form,
                                                  dict(request.query_params))
        return Response(content=body, status_code=st, media_type=media)

    r.add_api_route("/{token}", door, methods=["GET", "POST"])
    return r


def make_web_router() -> APIRouter:
    """G5: the website chat, the hosted chat page, the contact form and her app's API (no Hoola key: the website's address,
    a signed visitor token, or her app's own API key)."""
    from fastapi.responses import HTMLResponse, JSONResponse, Response
    from . import webchat as WC
    r = APIRouter()

    def _own(request: Request) -> tuple[str, bool]:
        origin = request.headers.get("origin") or request.headers.get("referer") or ""
        mine = WC._host(str(request.base_url))
        from ..config import get_settings
        pub = WC._host(get_settings().public_base_url or "")
        return origin, bool(WC._host(origin)) and WC._host(origin) in (mine, pub)

    def _cors(request: Request, resp: Response) -> Response:
        o = request.headers.get("origin")
        if o:
            resp.headers["Access-Control-Allow-Origin"] = o
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return resp

    async def _do(request: Request, fn, *a, **kw) -> Response:
        try:
            out = await asyncio.to_thread(fn, *a, **kw)
            return _cors(request, JSONResponse(out))
        except WC.WebError as e:
            return _cors(request, JSONResponse({"detail": str(e)}, status_code=e.status))
        except S_err() as e:
            return _cors(request, JSONResponse({"detail": str(e)}, status_code=400))

    def S_err():
        from . import service as S
        return S.SevaError

    async def _json(request: Request) -> dict:
        try:
            b = await request.json()
        except Exception:   # noqa: BLE001
            b = {}
        return b if isinstance(b, dict) else {}

    def _ip(request: Request) -> str:
        return (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0].strip()

    @r.options("/api/support/web/{key}/{what}")
    async def web_pre(key: str, what: str, request: Request):
        return _cors(request, Response(status_code=204))

    @r.options("/api/support/form/{key}")
    async def form_pre(key: str, request: Request):
        return _cors(request, Response(status_code=204))

    @r.post("/api/support/web/{key}/session")
    async def web_session(key: str, request: Request):
        b = await _json(request)
        o, own = _own(request)
        return await _do(request, WC.session_start, key, o, own, str(b.get("user_id") or ""), str(b.get("user_hash") or ""),
                         str(b.get("name") or ""), _ip(request))

    @r.post("/api/support/web/{key}/messages")
    async def web_send(key: str, request: Request):
        b = await _json(request)
        o, own = _own(request)
        return await _do(request, WC.visitor_send, key, o, own, str(b.get("token") or ""), str(b.get("text") or ""),
                         str(b.get("name") or ""), _ip(request))

    @r.get("/api/support/web/{key}/messages")
    async def web_poll(key: str, request: Request, token: str = "", after: str = ""):
        o, own = _own(request)
        return await _do(request, WC.visitor_poll, key, o, own, token, after)

    @r.post("/api/support/web/{key}/file")
    async def web_file(key: str, request: Request, token: str = Form(""), file: UploadFile = File(...)):
        o, own = _own(request)
        data = await file.read(WC.MAX_FILE + 1)
        return await _do(request, WC.visitor_file, key, o, own, token, file.filename or "file", data)

    @r.post("/api/support/web/{key}/callme")
    async def web_callme(key: str, request: Request):
        b = await _json(request)
        o, own = _own(request)
        return await _do(request, WC.call_me, key, o, own, str(b.get("token") or ""), str(b.get("phone") or ""),
                         str(b.get("note") or ""), str(b.get("name") or ""), _ip(request))

    @r.post("/api/support/form/{key}")
    async def web_form(key: str, request: Request):
        ct = request.headers.get("content-type") or ""
        if "json" in ct:
            b = await _json(request)
        else:
            b = dict(await request.form())
        o, own = _own(request)
        return await _do(request, WC.form, key, o, own, {k: str(v) for k, v in b.items()}, _ip(request))

    @r.post("/api/support/v1/messages")
    async def api_send(request: Request):
        return await _do(request, WC.api_send, request.headers.get("authorization") or "", await _json(request))

    @r.get("/api/support/v1/messages")
    async def api_get(request: Request, user_id: str = "", after: str = ""):
        return await _do(request, WC.api_messages, request.headers.get("authorization") or "", user_id, after)

    def _approve_page(body: str, status: int = 200) -> HTMLResponse:
        page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>Approval</title><style>body{margin:0;font-family:system-ui,sans-serif;background:#f7f7f8;color:#1b1b1f}"
                "main{max-width:520px;margin:32px auto;padding:24px;background:#fff;border-radius:14px;border:1px solid #e6e6ea}"
                "h1{font-size:20px;margin:0 0 6px}.big{font-size:28px;font-weight:600;margin:10px 0}.s{color:#555;font-size:14px;line-height:1.5}"
                "textarea{width:100%;box-sizing:border-box;border:1px solid #d9d9e0;border-radius:10px;padding:10px;font:inherit}"
                "button{border:0;border-radius:10px;padding:12px 18px;font-size:15px;cursor:pointer;margin-right:8px}"
                ".y{background:#1b1b1f;color:#fff}.n{background:#f0f0f3}</style></head><body><main>" + body + "</main></body></html>")
        return HTMLResponse(page, status_code=status, headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
                                                                                          "form-action 'self'; frame-ancestors 'none'",
                                                               "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                                                               "Cache-Control": "no-store"})

    @r.post("/api/support/layer/{token}")
    async def layer_ping(token: str):
        """G12: her helpdesk's webhook - only a nudge to read it now (the body is never trusted or stored)."""
        from . import layer as LY
        tenant = await asyncio.to_thread(LY.by_hook, token)
        if not tenant:
            raise HTTPException(404, "unknown")

        def _go():
            try:
                LY.run(tenant)
            except Exception:   # noqa: BLE001
                pass
        asyncio.get_running_loop().run_in_executor(None, _go)
        return {"ok": True}

    @r.get("/support/approve/{token}", response_class=HTMLResponse)
    async def approve_page(token: str):
        """G10: one person's step of a money approval chain, on their own one-time link (bound to the request)."""
        import html
        from . import teams as TM
        try:
            i = await asyncio.to_thread(TM.step_by_token, token)
        except TM.TeamError as e:
            return _approve_page(f"<h1>Approval</h1><p class='s'>{html.escape(str(e))}</p>", 410)
        q = i["request"]
        e = html.escape
        return _approve_page(
            f"<h1>{e(q['kind'])} · {e(q['number'])}</h1><p class='s'>For {e(i['person'] or 'you')} ({e(i['role'])}). Customer: "
            f"{e(q['customer'] or '')}</p><div class='big'>{e(q['amount'] or '')}</div><p class='s'>{e(q['reason'] or '')}</p>"
            f"<p class='s'>{'Within the written policy.' if q['within'] else 'Outside the written policy.'} Saying yes does not move "
            "money: the owner pays from her own bank or gateway.</p>"
            f"<form method='post' action='/support/approve/{e(token)}'><p><textarea name='note' rows='2' placeholder='A note (optional)'>"
            "</textarea></p><button class='y' name='yes' value='1' type='submit'>Yes</button><button class='n' name='yes' value='0' "
            "type='submit'>No</button></form>")

    @r.post("/support/approve/{token}", response_class=HTMLResponse)
    async def approve_post(token: str, request: Request):
        import html
        from . import teams as TM
        from .service import SevaError
        form = await request.form()
        try:
            out = await asyncio.to_thread(TM.decide_step, token, str(form.get("yes") or "") == "1", str(form.get("note") or ""))
        except (TM.TeamError, SevaError) as e:
            return _approve_page(f"<h1>Approval</h1><p class='s'>{html.escape(str(e))}</p>", 410)
        return _approve_page(f"<h1>Done</h1><p class='s'>{html.escape(out['say'])}</p>")

    @r.get("/support/chat/{key}", response_class=HTMLResponse)
    async def hosted(key: str):
        import html
        k = html.escape(key, quote=True)
        page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>Chat</title><style>html,body{margin:0;height:100%;background:#fff;font-family:system-ui,sans-serif}</style></head>"
                f"<body><script src='/static/support/widget.js' data-hoola-support='{k}' data-mode='page'></script></body></html>")
        return HTMLResponse(page, headers={"Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                                                                      "frame-ancestors *", "X-Content-Type-Options": "nosniff"})
    return r
