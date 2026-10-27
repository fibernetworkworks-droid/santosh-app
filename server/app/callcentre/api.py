"""HTTP + WebSocket routes of the Call Centre Sahayak.

Her app (API key): /api/callcentre/... settings, keys, script (draft / edit / submit / HER decide), calls, messages, report.
The phone provider (public, each request checked by itself): /api/callcentre/hook/{provider}/{token}/... and the media
WebSocket /api/callcentre/ws/{provider}/{token}. The route token picks the business; Plivo requests must also carry a
valid X-Plivo-Signature-V3 made with HER Plivo auth token; the stream needs a one-time ticket from our own answer (or,
for Exotel's static stream URL, the Basic Auth pair we generated).
"""
from __future__ import annotations

import asyncio
import base64
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse, Response

from . import providers as P
from . import rules as R
from . import service as S

log = logging.getLogger("santosh.callcentre")


def _err(e: Exception) -> HTTPException:
    return HTTPException(400, str(e))


def _public_url(request: Request) -> str:
    from ..config import get_settings
    base = (get_settings().public_base_url or "").rstrip("/") or f"{request.url.scheme}://{request.url.netloc}"
    q = request.url.query
    return base + request.url.path + (f"?{q}" if q else "")


async def _params(request: Request) -> dict[str, Any]:
    out: dict[str, Any] = {}
    ct = request.headers.get("content-type", "")
    try:
        if "json" in ct:
            body = await request.json()
            out = dict(body) if isinstance(body, dict) else {}
        elif request.method == "POST":
            form = await request.form()
            out = {k: v for k, v in form.items() if isinstance(v, str)}
    except Exception:
        out = {}
    return out


def _provider_for(tenant: str, name: str) -> P.Provider:
    with S.session() as s:
        r = S._row(s, tenant)
        if r.provider != name:
            raise HTTPException(404, "not this provider")
    return P.get(name, S.creds(tenant))


async def _checked(request: Request, name: str, token: str) -> tuple[str, P.Provider, dict[str, Any]]:
    tenant = await asyncio.to_thread(S.by_token, token)
    if not tenant:
        raise HTTPException(404, "unknown line")
    prov = await asyncio.to_thread(_provider_for, tenant, name)
    params = await _params(request)
    secret = str(S.creds(tenant).get("secret") or "") if name == "fake" else ""
    if not prov.verify(request.method, _public_url(request), params if request.method == "POST" else {}, dict(request.headers), secret):
        log.warning("callcentre: bad signature on %s for %s", request.url.path, tenant)
        raise HTTPException(403, "bad signature")
    return tenant, prov, params


def _reply(prov: P.Provider, body: tuple[str, str]) -> Response:
    return Response(content=body[0], media_type=body[1])


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()
    dep = [Depends(require_key)]

    async def run(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except S.CcError as e:
            raise _err(e)

    # ---------------------------------------------------------------- her app
    @r.get("/api/callcentre", dependencies=dep)
    async def cc_all(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/api/callcentre/settings", dependencies=dep)
    async def cc_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/api/callcentre/settings", dependencies=dep)
    async def cc_save(body: dict, tenant: str = Depends(current_tenant)):
        keys = ("provider", "number", "agent_name", "voice", "hours", "after_hours", "max_concurrent", "queue_max", "overflow",
                "handover", "transfer_on", "record", "max_minutes", "rate_inr_per_min")
        return await run(S.save_settings, tenant, **{k: body[k] for k in keys if k in body})

    @r.put("/api/callcentre/keys", dependencies=dep)
    async def cc_keys(body: dict, tenant: str = Depends(current_tenant)):
        return await run(S.set_creds, tenant, str(body.get("provider") or ""), body)

    @r.post("/api/callcentre/line", dependencies=dep)
    async def cc_line(body: dict, tenant: str = Depends(current_tenant)):
        return await run(S.set_line, tenant, bool(body.get("on")))

    @r.post("/api/callcentre/script", dependencies=dep)
    async def cc_script(body: dict, tenant: str = Depends(current_tenant)):
        text = ""
        if body.get("file_id"):
            text = await asyncio.to_thread(_file_text, tenant, str(body["file_id"]))
        return await run(S.make_script, tenant, str(body.get("words") or ""), text)

    @r.put("/api/callcentre/script", dependencies=dep)
    async def cc_edit(body: dict, tenant: str = Depends(current_tenant)):
        fields = {k: body[k] for k in ("business", "about", "greeting", "closing", "hours_text", "languages", "default_lang",
                                       "never", "handover_words", "can") if k in body}
        return await run(S.edit_script, tenant, body.get("faq_add"), body.get("faq_remove"), **fields)

    @r.post("/api/callcentre/script/submit", dependencies=dep)
    async def cc_submit(tenant: str = Depends(current_tenant)):
        return await run(S.submit, tenant)

    @r.get("/api/callcentre/scripts", dependencies=dep)
    async def cc_scripts(tenant: str = Depends(current_tenant)):
        return {"scripts": await run(S.scripts, tenant), "running": await run(S.approved, tenant)}

    @r.post("/api/callcentre/scripts/{script_id}/decide", dependencies=dep)
    async def cc_decide(script_id: str, body: dict, tenant: str = Depends(current_tenant)):
        """HER tap. The only way a script version reaches the phone line."""
        return await run(S.decide_script, tenant, script_id, bool(body.get("yes")), str(body.get("hash") or ""),
                         str(body.get("note") or ""))

    @r.post("/api/callcentre/try", dependencies=dep)
    async def cc_try(body: dict, tenant: str = Depends(current_tenant)):
        return await run(_try, tenant, str(body.get("question") or ""), bool(body.get("draft")))

    @r.get("/api/callcentre/calls", dependencies=dep)
    async def cc_calls(outcome: str = "", limit: int = 50, tenant: str = Depends(current_tenant)):
        return {"calls": await run(S.calls, tenant, limit, outcome)}

    @r.get("/api/callcentre/calls/{call_id}", dependencies=dep)
    async def cc_call(call_id: str, tenant: str = Depends(current_tenant)):
        try:
            return await asyncio.to_thread(S.call, tenant, call_id)
        except S.CcError as e:
            raise HTTPException(404, str(e))

    @r.get("/api/callcentre/messages", dependencies=dep)
    async def cc_msgs(status: str = "open", tenant: str = Depends(current_tenant)):
        return {"messages": await run(S.messages, tenant, status)}

    @r.post("/api/callcentre/messages/{msg_id}/done", dependencies=dep)
    async def cc_msg_done(msg_id: str, body: dict, tenant: str = Depends(current_tenant)):
        return await run(S.message_done, tenant, msg_id, str(body.get("note") or ""))

    @r.get("/api/callcentre/report", dependencies=dep)
    async def cc_report(days: int = 7, tenant: str = Depends(current_tenant)):
        return await run(S.report, tenant, days)

    @r.post("/api/callcentre/forget", dependencies=dep)
    async def cc_forget(body: dict, tenant: str = Depends(current_tenant)):
        return await run(S.forget_caller, tenant, str(body.get("number") or ""))

    # ---------------------------------------------------------------- the phone provider (public, verified)
    @r.post("/api/callcentre/hook/{name}/{token}/answer")
    async def hook_answer(name: str, token: str, request: Request):
        tenant, prov, params = await _checked(request, name, token)
        info = prov.call_info(params)
        tries = int(request.query_params.get("try") or 0)
        d = await asyncio.to_thread(S.incoming, tenant, info, tries)
        return _reply(prov, await asyncio.to_thread(_answer_body, tenant, prov, d, request))

    @r.post("/api/callcentre/hook/{name}/{token}/hangup")
    async def hook_hangup(name: str, token: str, request: Request):
        tenant, prov, params = await _checked(request, name, token)
        info = prov.call_info(params)
        dur = params.get("Duration") or params.get("BillDuration") or params.get("seconds")
        try:
            secs = float(dur) if dur not in (None, "") else None
        except ValueError:
            secs = None
        if info.get("call"):
            await asyncio.to_thread(S.hung_up, tenant, info["call"], secs)
        return Response(status_code=200)

    @r.post("/api/callcentre/hook/{name}/{token}/transfer/{call_id}")
    async def hook_transfer(name: str, token: str, call_id: str, request: Request):
        tenant, prov, _ = await _checked(request, name, token)
        if not S.ticket_ok(call_id, request.query_params.get("t", "")):
            raise HTTPException(403, "bad ticket")
        row = await asyncio.to_thread(S.call_row, call_id)
        if not row or row.get("tenant") != tenant or not row.get("transfer_to"):
            raise HTTPException(404, "no transfer")
        with S.session() as s:
            num = S._row(s, tenant).number
        return _reply(prov, prov.say(R.CONNECTING[R.lang3(row.get("lang") or "hi-IN")], row.get("lang") or "hi-IN",
                                     dial=row["transfer_to"], caller_id=num))

    # Exotel flow helpers (Passthru = 200 / 302 branch; Connect applet dynamic URL; Voicebot dynamic stream URL)
    @r.get("/api/callcentre/hook/exotel/{token}/stream_url")
    async def exotel_stream_url(token: str, request: Request):
        tenant, prov, _ = await _checked(request, "exotel", token)
        info = prov.call_info(dict(request.query_params))
        d = await asyncio.to_thread(S.incoming, tenant, info, 0)
        if d["action"] != "stream":
            return JSONResponse({"url": ""}, status_code=404)
        return {"url": await asyncio.to_thread(_ws_url, tenant, d)}

    @r.get("/api/callcentre/hook/exotel/{token}/after")
    async def exotel_after(token: str, request: Request):
        tenant, _, _ = await _checked(request, "exotel", token)
        row = await asyncio.to_thread(_by_provider_call, tenant, request.query_params.get("CallSid", ""))
        return Response(status_code=200 if row and row.get("transfer_to") else 302)

    @r.get("/api/callcentre/hook/exotel/{token}/connect")
    async def exotel_connect(token: str, request: Request):
        tenant, _, _ = await _checked(request, "exotel", token)
        row = await asyncio.to_thread(_by_provider_call, tenant, request.query_params.get("CallSid", ""))
        if not row or not row.get("transfer_to"):
            raise HTTPException(404, "no transfer")
        with S.session() as s:
            st = S._row(s, tenant)
            num, rec = st.number, st.record
        return {"fetch_after_attempt": False, "destination": {"numbers": [row["transfer_to"]]},
                "outgoing_phone_number": num, "record": rec, "max_ringing_duration": 30, "max_conversation_duration": 3600}

    @r.websocket("/api/callcentre/ws/{name}/{token}")
    async def line_ws(ws: WebSocket, name: str, token: str):
        tenant = await asyncio.to_thread(S.by_token, token)
        if not tenant:
            await ws.close(code=1008)
            return
        try:
            prov = await asyncio.to_thread(_provider_for, tenant, name)
        except HTTPException:
            await ws.close(code=1008)
            return
        call_id, t = ws.query_params.get("c", ""), ws.query_params.get("t", "")
        ok = bool(call_id) and S.ticket_ok(call_id, t)
        if ok and name == "plivo" and ws.headers.get("x-plivo-signature-v3"):
            ok = prov.verify("GET", _ws_public(ws), {}, dict(ws.headers))
        if not ok and name == "exotel":
            ok = _basic_ok(tenant, ws.headers.get("authorization", ""))
            call_id = ""
        if not ok:
            log.warning("callcentre: stream refused for %s", tenant)
            await ws.close(code=1008)
            return
        await ws.accept()
        from .bridge import CallBridge, Sock
        sock = Sock(ws)
        line = prov.line()
        provider_call = ""
        if not call_id:      # Exotel static URL: the call becomes known at the stream's start event
            first: list[dict[str, Any]] = []
            for _ in range(20):
                text = await sock.recv()
                if text is None:
                    return
                first = [e for e in line.parse(text) if e["type"] == "start"]
                if first:
                    break
            if not first:
                await sock.close()
                return
            st = first[0]
            d = await asyncio.to_thread(S.incoming, tenant, {"call": st.get("call", ""), "from": st.get("from", ""),
                                                             "to": st.get("to", "")}, 99)
            if d["action"] != "stream":
                if d["action"] == "dial":
                    await asyncio.to_thread(_mark_transfer, d["call_id"], d.get("dial", ""))
                await sock.close()
                return
            call_id, provider_call = d["call_id"], st.get("call", "")
        else:
            row = await asyncio.to_thread(S.call_row, call_id)
            if not row or row.get("tenant") != tenant:
                await sock.close()
                return
            provider_call = row.get("provider_call", "")
        bridge = CallBridge(tenant, prov, line, sock, call_id, provider_call)
        try:
            await bridge.run()
        except Exception:
            log.exception("callcentre call %s failed", call_id)
            S.release_slot(tenant, call_id)

    return r


# ---------------------------------------------------------------- helpers
def _ws_public(ws: WebSocket) -> str:
    from ..config import get_settings
    base = (get_settings().public_base_url or "").rstrip("/")
    base = base.replace("https://", "wss://").replace("http://", "ws://") if base else f"{ws.url.scheme}://{ws.url.netloc}"
    q = ws.url.query
    return base + ws.url.path + (f"?{q}" if q else "")


def _basic_ok(tenant: str, header: str) -> bool:
    if not header.lower().startswith("basic "):
        return False
    try:
        user, _, pw = base64.b64decode(header[6:]).decode().partition(":")
    except Exception:
        return False
    u, p = S.ws_auth(tenant)
    return bool(u and p) and hmac.compare_digest(user, u) and hmac.compare_digest(pw, p)


def _ws_url(tenant: str, d: dict[str, Any]) -> str:
    with S.session() as s:
        urls = S._urls(tenant, S._row(s, tenant))
    if not urls:
        raise S.CcError("PUBLIC_BASE_URL set nahi.")
    return f"{urls['stream']}?c={d['call_id']}&t={d['ticket']}"


def _answer_body(tenant: str, prov: P.Provider, d: dict[str, Any], request: Request) -> tuple[str, str]:
    lang = d.get("lang") or "hi-IN"
    with S.session() as s:
        r = S._row(s, tenant)
        record, number = r.record, r.number
    if d["action"] == "stream":
        return prov.stream(_ws_url(tenant, d), record, {"cc": d["call_id"]})
    if d["action"] == "hold":
        url = _public_url(request).split("?")[0] + f"?try={d['tries']}"
        return prov.hold(d["text"], lang, url)
    if d["action"] == "dial":
        return prov.say(d["text"], lang, dial=d["dial"], caller_id=number)
    return prov.say(d["text"], lang)


def _by_provider_call(tenant: str, provider_call: str) -> dict[str, Any] | None:
    if not provider_call:
        return None
    from sqlalchemy import select

    from .models import CcCall
    with S.session() as s:
        c = s.scalar(select(CcCall).where(CcCall.tenant_id == tenant, CcCall.provider_call == provider_call))
        return S.call_row(c.id) if c else None


def _mark_transfer(call_id: str, to: str) -> None:
    from .models import CcCall
    with S.session() as s:
        c = s.get(CcCall, call_id)
        if c:
            c.transfer_to = to


def _try(tenant: str, question: str, use_draft: bool = False) -> dict[str, Any]:
    """'Script aazmao': what the line would find for this question (no call, no model)."""
    sc = S.draft(tenant) if use_draft else S.approved(tenant)
    sc = sc or S.draft(tenant)
    if not sc:
        raise S.CcError("Abhi koi script nahi.")
    f, score = R.best_faq(question, sc["content"].get("faqs") or [])
    if f is None:
        return {"found": False, "score": score, "say": "Script mein iska jawab nahi: line message lega ya insaan ko jodegi."}
    return {"found": True, "q": f["q"], "a": f["a"], "score": score, "version": sc["version"], "status": sc["status"]}


def _file_text(tenant: str, file_id: str) -> str:
    try:
        from .. import docread
        from ..analyst.service import _load_file
        name, data = _load_file(tenant, file_id)
        return str(docread.read_text(name, "", data, limit=20000).get("text") or "")
    except Exception:
        log.exception("callcentre: file read failed")
        return ""
