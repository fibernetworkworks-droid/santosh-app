"""HTTP API for the Santosh app, the Meta webhook, and the demo chat page."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select

from . import campaigns as camp
from . import worker
from .agent import run_turn
from .config import get_settings
from .db import Conversation, Message, init_db, session
from .events import bus
from .leads import import_leads

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("santosh.api")
STATIC = Path(__file__).parent / "static"
MAX_UPLOAD = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run_forever(stop))
    yield
    stop.set()
    await task


app = FastAPI(title="Santosh Core", version="0.12.0", lifespan=lifespan)


def _bearer(request: Request) -> str:
    return request.headers.get("authorization", "").removeprefix("Bearer ").strip() or request.query_params.get("key", "")


def current_tenant(request: Request) -> str:
    """Resolve the caller: a product session token -> that user; the legacy API key -> 'default'."""
    t = _resolve_tenant(request)
    from . import offline
    offline.touch(t)   # any call from the phone means it is online
    return t


def _resolve_tenant(request: Request) -> str:
    from . import accounts
    tok = _bearer(request)
    st = get_settings()
    if st.api_key and tok and hmac.compare_digest(tok, st.api_key):
        return st.tenant_id
    uid = accounts.tenant_for_session(tok) if tok else None
    if uid:
        return accounts.tenant_of_user(uid)
    if not st.api_key:
        return st.tenant_id
    raise HTTPException(401, "Sign in first")


def require_key(request: Request) -> None:
    from . import accounts
    key = get_settings().api_key
    got = request.headers.get("authorization", "").removeprefix("Bearer ").strip() or request.query_params.get("key", "")
    if key and got and hmac.compare_digest(got, key):
        return
    if got and accounts.tenant_for_session(got):   # a signed-in product user
        return
    if not key:
        return
    raise HTTPException(401, "Missing or wrong API key")


def _conv_or_404(conversation_id: str, tenant: str) -> Conversation:
    with session() as s:
        c = s.get(Conversation, conversation_id)
        if not c or c.tenant_id != tenant:
            raise HTTPException(404, "Conversation not found")
        return c


# ---------------- health + demo page ----------------
@app.get("/healthz")
def healthz():
    st = get_settings()
    from .voice import MALE_VOICES
    from . import mail
    features = ["routines", "voice", "web", "bazar"] + (["realtime_voice", "google_search"] if st.gemini_api_key else []) \
        + (["email"] if mail.configured() else []) + (["calendar"] if __import__("app.gcal", fromlist=["x"]).configured() else []) \
        + (["drive"] if __import__("app.gdrive", fromlist=["x"]).configured() else []) \
        + (["maps"] if __import__("app.maps", fromlist=["x"]).configured() else [])
    from . import accounts
    return {"ok": True, "version": app.version, "google_login": accounts.oauth_configured(),
            "dry_run": st.wa_dry_run, "model": st.anthropic_model,
            "chat_brain": ("glm:" + st.glm_model) if (st.glm_api_key and st.chat_llm != "claude") else "claude",
            "brain_configured": bool(st.anthropic_api_key), "features": features,
            "voices": [{"id": k, "style": v} for k, v in MALE_VOICES.items()], "voice_default": st.voice_default,
            "bazar": {"packs": len(__import__("app.bazar.packs.registry", fromlist=["x"]).registry().packs),
                      "bills_live": __import__("app.bazar.config", fromlist=["x"]).get_settings().bills_live,
                      "mcp_directory": len(__import__("app.bazar.directory", fromlist=["x"]).servers())}}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------------- conversations ----------------
class NewMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: bool = False   # spoken in voice mode: Santosh answers short and speakable


@app.post("/api/conversations", dependencies=[Depends(require_key)])
def create_conversation(tenant: str = Depends(current_tenant)):
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        cid = c.id
    greeting = "Namaskar! Main Santosh hoon, aapka AI coworker. Aaj kya kaam poora karna hai?"
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=greeting, display=greeting,
                      in_history=False, delivered_to_agent=True))
    bus.publish(cid, "message", {"role": "assistant", "text": greeting, "source": "greeting"})
    return {"id": cid}


@app.get("/api/conversations/{conversation_id}/messages", dependencies=[Depends(require_key)])
def list_messages(conversation_id: str, tenant: str = Depends(current_tenant)):
    _conv_or_404(conversation_id, tenant)
    with session() as s:
        rows = s.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.display.is_not(None))
                         .order_by(Message.id)).all()
        return {"messages": [{"id": r.id, "role": r.role, "text": r.display, "at": r.created_at.isoformat()} for r in rows]}


@app.post("/api/conversations/{conversation_id}/messages", status_code=202, dependencies=[Depends(require_key)])
async def post_message(conversation_id: str, body: NewMessage, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    _conv_or_404(conversation_id, tenant)
    bus.publish(conversation_id, "message", {"role": "user", "text": body.text, "source": "user"})
    background.add_task(run_turn, conversation_id, body.text, tenant, body.voice)
    return {"accepted": True}


@app.get("/api/conversations/{conversation_id}/events", dependencies=[Depends(require_key)])
async def events(conversation_id: str, request: Request, after: int = 0, tenant: str = Depends(current_tenant)):
    """Server-sent events: replays everything after `after`, then streams live."""
    _conv_or_404(conversation_id, tenant)
    last = int(request.headers.get("last-event-id") or after or 0)
    q = bus.subscribe(conversation_id)

    async def gen():
        try:
            sent = last
            for ev in bus.backlog(conversation_id, last):
                sent = ev["id"]
                yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    from . import offline
                    offline.touch(tenant)   # the stream is still open: the phone is online
                    yield ": ping\n\n"
                    continue
                if ev["id"] <= sent:
                    continue
                sent = ev["id"]
                yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            bus.unsubscribe(conversation_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------- leads ----------------
@app.post("/api/leads/upload", dependencies=[Depends(require_key)])
async def upload_leads(file: UploadFile = File(...), conversation_id: str | None = Form(None), tenant: str = Depends(current_tenant)):
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File is larger than 10 MB")
    try:
        res = import_leads(file.filename or "leads.csv", data, tenant)
    except ValueError as e:
        raise HTTPException(400, str(e))
    out = res.as_dict()
    if conversation_id:
        _conv_or_404(conversation_id, tenant)
        bus.publish(conversation_id, "upload", {"filename": file.filename, **out})
    return out


# ---------------- campaigns ----------------
@app.get("/api/campaigns/{campaign_id}", dependencies=[Depends(require_key)])
def get_campaign(campaign_id: str):
    try:
        return camp.campaign_view(campaign_id)
    except camp.CampaignError as e:
        raise HTTPException(404, str(e))


class CampaignAction(BaseModel):
    action: str = Field(pattern="^(pause|resume|cancel|send)$")


@app.post("/api/campaigns/{campaign_id}/action", dependencies=[Depends(require_key)])
def campaign_action(campaign_id: str, body: CampaignAction):
    try:
        v = camp.campaign_view(campaign_id)
        if body.action == "send":
            return camp.confirm_send(campaign_id)
        if body.action == "pause":
            return camp.set_campaign_status(campaign_id, "paused", "Paused from the app")
        if body.action == "resume" and v["status"] == "paused":
            return camp.set_campaign_status(campaign_id, "sending" if v["template"]["status"] == "APPROVED" else "awaiting_approval")
        if body.action == "cancel":
            return camp.set_campaign_status(campaign_id, "cancelled", "Cancelled from the app")
        return v
    except camp.CampaignError as e:
        raise HTTPException(404, str(e))


# ---------------- Meta webhook ----------------
@app.get("/webhooks/whatsapp")
def verify_webhook(request: Request):
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and hmac.compare_digest(p.get("hub.verify_token", ""), get_settings().wa_verify_token):
        return PlainTextResponse(p.get("hub.challenge", ""))
    raise HTTPException(403, "Verify token does not match")


def _signature_ok(secret: str, raw: bytes, header: str | None) -> bool:
    if not secret:
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@app.post("/webhooks/whatsapp")
async def receive_webhook(request: Request):
    raw = await request.body()
    if not _signature_ok(get_settings().wa_app_secret, raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(401, "Bad signature")
    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "Body is not JSON")
    updates: list[dict] = []
    for entry in payload.get("entry", []):
        for ch in entry.get("changes", []):
            field, value = ch.get("field"), ch.get("value") or {}
            if field == "messages":
                updates.extend(value.get("statuses") or [])
                for m in value.get("messages") or []:
                    updates.append({"reply_from": m.get("from"), "text": (m.get("text") or {}).get("body")})
            elif field == "message_template_status_update":
                camp.apply_template_status(str(value.get("message_template_id")), value.get("event", ""), value.get("reason"))
    if updates:
        for cid in camp.apply_message_status(updates):
            camp.publish_campaign(cid)
    return {"ok": True}


# ---------------- daily life (used by the Santosh phone app) ----------------
from . import life  # noqa: E402
from .db import DeviceAction, ListItem, MemoryFact, Profile, Reminder  # noqa: E402


@app.get("/api/reminders", dependencies=[Depends(require_key)])
def get_reminders(include_done: bool = False, tenant: str = Depends(current_tenant)):
    return {"reminders": life.upcoming_reminders(tenant, include_done=include_done)}


@app.post("/api/reminders/{reminder_id}/cancel", dependencies=[Depends(require_key)])
def cancel_reminder_api(reminder_id: str, tenant: str = Depends(current_tenant)):
    with session() as s:
        r = s.get(Reminder, reminder_id)
        if not r or r.tenant_id != tenant:
            raise HTTPException(404, "Reminder not found")
        r.status = "cancelled"
        conv = r.conversation_id
    reminders = life.upcoming_reminders(tenant)
    bus.publish(conv, "reminders", {"reminders": reminders})
    return {"reminders": reminders}


# ---------------- accounts (product: Sign in with Google) ----------------
@app.get("/auth/google/start")
def google_start(app_session: bool = True):
    """The app opens this; we redirect to Google's consent screen."""
    from . import accounts
    try:
        return RedirectResponse(accounts.start_google())
    except accounts.AuthError as e:
        raise HTTPException(503, str(e))


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    """Google returns here. We store tokens and hand the app a session token via a deep link."""
    from . import accounts
    code = request.query_params.get("code")
    state = request.query_params.get("state", "")
    err = request.query_params.get("error")
    if err:
        return HTMLResponse(f"<h3>Sign-in cancelled</h3><p>{err}</p>", status_code=400)
    if not code:
        raise HTTPException(400, "Missing code")
    try:
        res = await accounts.finish_google(code, state)
    except accounts.AuthError as e:
        return HTMLResponse(f"<h3>Sign-in nahi hua</h3><p>{e}</p>", status_code=400)
    scheme = get_settings().app_redirect_scheme
    deep = f"{scheme}://auth?session={res['session_token']}"
    # the app registers this scheme; the page also shows the token in case the link doesn't auto-open
    html = f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">
<h2>Santosh se juda! ✅</h2><p>{res['email']}</p>
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>location.href={deep!r};</script></body>"""
    return HTMLResponse(html)


class LocationIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(None, ge=0)


@app.put("/api/location", dependencies=[Depends(require_key)])
def put_location(body: LocationIn, tenant: str = Depends(current_tenant)):
    """The phone's position, so 'near me', directions and cab pickup use where the user actually is."""
    from . import maps
    maps.save_location(tenant, body.lat, body.lng, body.accuracy_m)
    return {"ok": True}


@app.get("/api/me", dependencies=[Depends(require_key)])
def api_me(request: Request):
    from . import accounts
    tok = _bearer(request)
    uid = accounts.tenant_for_session(tok) if tok else None
    if not uid:
        return {"signed_in": False, "tenant": current_tenant(request)}
    info = accounts.user_info(uid)
    return {"signed_in": True, **(info or {})}


@app.post("/api/logout", dependencies=[Depends(require_key)])
def api_logout(request: Request):
    from . import accounts
    accounts.logout(_bearer(request))
    return {"ok": True}


@app.delete("/api/connections/{provider}", dependencies=[Depends(require_key)])
def api_disconnect(provider: str, request: Request):
    from . import accounts
    uid = accounts.tenant_for_session(_bearer(request))
    if not uid:
        raise HTTPException(401, "Sign in first")
    return {"disconnected": accounts.disconnect(uid, provider)}


@app.websocket("/api/voice/ws")
async def voice_ws(ws: WebSocket, conv: str = "", voice: str = "", lang: str = "hi-IN"):
    """Realtime voice call (Baat tab). See app/voice.py for the protocol."""
    from . import voice as v
    st = get_settings()
    got = ws.headers.get("authorization", "").removeprefix("Bearer ").strip() or ws.query_params.get("key", "")
    from . import accounts
    if st.api_key and got and hmac.compare_digest(got, st.api_key):
        tenant = st.tenant_id
    elif got and accounts.tenant_for_session(got):
        tenant = accounts.tenant_of_user(accounts.tenant_for_session(got))
    elif not st.api_key:
        tenant = st.tenant_id
    else:
        await ws.close(code=4401)
        return
    with session() as s:
        c = s.get(Conversation, conv)
        ok = bool(c and c.tenant_id == tenant)
    if not ok:
        await ws.close(code=4404)
        return
    await ws.accept()
    if not st.gemini_api_key:
        await ws.send_text(json.dumps({"type": "error", "message": "Server par GEMINI_API_KEY set nahi hai."}))
        await ws.close()
        return
    await v.Call(ws, conv, voice, lang, tenant).run()


@app.get("/api/emails/pending", dependencies=[Depends(require_key)])
def pending_emails(tenant: str = Depends(current_tenant)):
    from .db import EmailDraft
    with session() as s:
        rows = s.scalars(select(EmailDraft).where(EmailDraft.tenant_id == tenant, EmailDraft.status == "pending")
                         .order_by(EmailDraft.id)).all()
        return {"emails": [{"id": d.id, "to": d.to_addr, "cc": d.cc_addr, "subject": d.subject, "body": d.body,
                            "status": d.status} for d in rows]}


class EmailEdit(BaseModel):
    to: str | None = None
    cc: str | None = None
    subject: str | None = None
    body: str | None = None


@app.post("/api/emails/{draft_id}/send", dependencies=[Depends(require_key)])
async def send_email_draft(draft_id: str, body: EmailEdit | None = None, tenant: str = Depends(current_tenant)):
    """Approve and send. Optional fields let the user edit before sending."""
    from . import mail
    from .db import EmailDraft
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if not d or d.tenant_id != tenant:
            raise HTTPException(404, "Draft not found")
        if d.status == "sent":
            return {"status": "sent", "already": True}
        if body:
            if body.to is not None: d.to_addr = body.to.strip()[:1000]
            if body.cc is not None: d.cc_addr = body.cc.strip()[:1000]
            if body.subject is not None: d.subject = body.subject.strip()[:500]
            if body.body is not None: d.body = body.body
        to_addr, cc, subject, bod = d.to_addr, d.cc_addr, d.subject, d.body
        irt, refs, conv = d.in_reply_to, d.references, d.conversation_id
    if "@" not in to_addr:
        raise HTTPException(400, "Recipient email is not valid")
    try:
        await mail.send_email(to_addr, subject, bod, cc=cc, in_reply_to=irt, references=refs)
    except mail.MailError as e:
        with session() as s:
            d = s.get(EmailDraft, draft_id); d.status, d.error = "failed", str(e)
        bus.publish(conv, "email_sent", {"id": draft_id, "status": "failed", "error": str(e), "to": to_addr})
        raise HTTPException(502, str(e))
    from .db import now as _now
    with session() as s:
        d = s.get(EmailDraft, draft_id); d.status, d.sent_at = "sent", _now()
    bus.publish(conv, "email_sent", {"id": draft_id, "status": "sent", "to": to_addr, "subject": subject})
    from .events import notify
    notify(conv, f"Email bhej diya: {to_addr} ko \"{subject}\".")
    return {"status": "sent", "to": to_addr}


@app.post("/api/emails/{draft_id}/cancel", dependencies=[Depends(require_key)])
def cancel_email_draft(draft_id: str, tenant: str = Depends(current_tenant)):
    from .db import EmailDraft
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if not d or d.tenant_id != tenant:
            raise HTTPException(404, "Draft not found")
        if d.status == "pending":
            d.status = "cancelled"
        conv = d.conversation_id
    bus.publish(conv, "email_sent", {"id": draft_id, "status": "cancelled"})
    return {"status": "cancelled"}


@app.get("/api/routines", dependencies=[Depends(require_key)])
def get_routines(tenant: str = Depends(current_tenant)):
    from . import life
    return {"routines": life.active_routines(tenant)}


@app.post("/api/routines/{routine_id}/cancel", dependencies=[Depends(require_key)])
def cancel_routine_api(routine_id: str, tenant: str = Depends(current_tenant)):
    from . import life
    from .db import Routine
    with session() as s:
        r = s.get(Routine, routine_id)
        if not r or r.tenant_id != tenant:
            raise HTTPException(404, "Routine not found")
        r.status = "cancelled"
        conv = r.conversation_id
    bus.publish(conv, "routines", {"routines": life.active_routines(tenant)})
    return {"cancelled": routine_id}


@app.get("/api/lists", dependencies=[Depends(require_key)])
def get_lists(tenant: str = Depends(current_tenant)):
    with session() as s:
        rows = s.scalars(select(ListItem).where(ListItem.tenant_id == tenant, ListItem.done.is_(False))
                         .order_by(ListItem.list_name, ListItem.id)).all()
        out: dict[str, list[dict]] = {}
        for r in rows:
            out.setdefault(r.list_name, []).append({"id": r.id, "text": r.text})
        return {"lists": out}


@app.post("/api/lists/items/{item_id}/done", dependencies=[Depends(require_key)])
def tick_item(item_id: int, tenant: str = Depends(current_tenant)):
    with session() as s:
        it = s.get(ListItem, item_id)
        if not it or it.tenant_id != tenant:
            raise HTTPException(404, "Item not found")
        it.done = True
    return get_lists()


@app.get("/api/memory", dependencies=[Depends(require_key)])
def get_memory(tenant: str = Depends(current_tenant)):
    return {"facts": [{"id": f.id, "text": f.text} for f in life.memory_facts(tenant)]}


@app.delete("/api/memory/{fact_id}", dependencies=[Depends(require_key)])
def delete_memory(fact_id: int, tenant: str = Depends(current_tenant)):
    with session() as s:
        f = s.get(MemoryFact, fact_id)
        if not f or f.tenant_id != tenant:
            raise HTTPException(404, "Not found")
        s.delete(f)
    return get_memory()


class ProfileIn(BaseModel):
    name: str | None = Field(None, max_length=120)
    city: str | None = Field(None, max_length=120)
    language: str | None = Field(None, max_length=32)
    timezone: str | None = Field(None, max_length=64)
    briefing_time: str | None = Field(None, pattern=r"^(\d{2}:\d{2}|off)$")
    conversation_id: str | None = None


def _profile_out(p: Profile) -> dict:
    return {"name": p.name, "city": p.city, "language": p.language, "timezone": p.timezone,
            "briefing_time": p.briefing_time}


@app.get("/api/profile", dependencies=[Depends(require_key)])
def get_profile_api(tenant: str = Depends(current_tenant)):
    return _profile_out(life.get_profile(tenant))


@app.put("/api/profile", dependencies=[Depends(require_key)])
def put_profile(body: ProfileIn, tenant: str = Depends(current_tenant)):
    life.get_profile(tenant)
    with session() as s:
        p = s.get(Profile, tenant)
        if body.name is not None:
            p.name = body.name.strip() or None
        if body.city is not None and body.city.strip() != (p.city or ""):
            p.city, p.lat, p.lon = body.city.strip() or None, None, None
        if body.language is not None:
            p.language = body.language
        if body.timezone:
            from zoneinfo import ZoneInfo
            try:
                ZoneInfo(body.timezone)
            except Exception:
                raise HTTPException(400, "Unknown time zone")
            p.timezone = body.timezone
        if body.briefing_time is not None:
            p.briefing_time = None if body.briefing_time == "off" else body.briefing_time
            p.last_briefing_date = None
            if body.conversation_id:
                p.briefing_conversation_id = body.conversation_id
        return _profile_out(p)


class ActionResult(BaseModel):
    ok: bool
    detail: str | None = Field(None, max_length=500)


@app.get("/api/device-actions/pending", dependencies=[Depends(require_key)])
def pending_actions(tenant: str = Depends(current_tenant)):
    """The phone asks this on start, so actions created while it was offline still run (within 15 minutes)."""
    with session() as s:
        rows = s.scalars(select(DeviceAction).where(DeviceAction.tenant_id == tenant,
                                                    DeviceAction.status == "pending").order_by(DeviceAction.created_at)).all()
        return {"actions": [{"id": a.id, "type": a.type, **a.payload} for a in rows]}


@app.post("/api/device-actions/{action_id}/result", dependencies=[Depends(require_key)])
def action_result(action_id: str, body: ActionResult, tenant: str = Depends(current_tenant)):
    with session() as s:
        a = s.get(DeviceAction, action_id)
        if not a or a.tenant_id != tenant:
            raise HTTPException(404, "Action not found")
        if a.status != "pending":
            return {"status": a.status}
        a.status = "done" if body.ok else "failed"
        a.result = body.detail
        conv, typ, status = a.conversation_id, a.type, a.status
    bus.publish(conv, "device_action_result", {"id": action_id, "type": typ, "status": status, "detail": body.detail})
    if status == "failed":
        from .events import notify
        notify(conv, f"Phone par yeh nahi ho paya ({typ.replace('_', ' ')}): {body.detail or 'permission ya app ki dikkat'}. "
                     "Phone settings mein Santosh ko permission dekh lijiye.")
    return {"status": status}


# ---------------- Santosh Bazar (159 packs) ----------------
from .bazar import service as bazar  # noqa: E402
from .bazar.connectors.base import ToolError as BazarError  # noqa: E402


def _bz(fn, *a, **k):
    try:
        return fn(*a, **k)
    except BazarError as e:
        raise HTTPException(400, str(e))
    except PermissionError:
        raise HTTPException(403, "Not allowed for this shop")


def _maybe_tenant(request: Request) -> str | None:
    try:
        return current_tenant(request)
    except HTTPException:
        return None


@app.get("/api/bazar/catalog", dependencies=[Depends(require_key)])
def bazar_catalog(tenant: str = Depends(current_tenant)):
    return _bz(bazar.catalog, tenant)


@app.get("/api/bazar/find", dependencies=[Depends(require_key)])
def bazar_find_api(q: str = "", category: str = "", tenant: str = Depends(current_tenant)):
    return _bz(bazar.find, tenant, q, category)


class BazarDecision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


@app.get("/api/bazar/approvals/pending", dependencies=[Depends(require_key)])
def bazar_pending(tenant: str = Depends(current_tenant)):
    return {"approvals": bazar.pending_approvals(tenant)}


@app.post("/api/bazar/approvals/{approval_id}", dependencies=[Depends(require_key)])
async def bazar_decide(approval_id: str, body: BazarDecision, tenant: str = Depends(current_tenant)):
    try:
        return await asyncio.to_thread(bazar.decide, tenant, approval_id, body.decision)
    except BazarError as e:
        raise HTTPException(400, str(e))


@app.get("/api/bazar/activity", dependencies=[Depends(require_key)])
def bazar_activity_api(tenant: str = Depends(current_tenant)):
    return bazar.activity(tenant)


class BazarSettingsIn(BaseModel):
    cap_per_order_rupees: float | None = Field(None, ge=0, le=5000)
    cap_per_day_rupees: float | None = Field(None, ge=0, le=20000)
    pincode: str | None = Field(None, max_length=10)
    address: str | None = Field(None, max_length=400)
    language: str | None = None
    phone: str | None = Field(None, max_length=16)


@app.get("/api/bazar/settings", dependencies=[Depends(require_key)])
def bazar_settings_get(tenant: str = Depends(current_tenant)):
    return bazar.get_user_settings(tenant)


@app.put("/api/bazar/settings", dependencies=[Depends(require_key)])
def bazar_settings_put(body: BazarSettingsIn, tenant: str = Depends(current_tenant)):
    return _bz(bazar.set_user_settings, tenant, body.model_dump(exclude_none=True))


class BazarContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    upi_id: str = ""
    phone: str = ""
    relation: str = ""


@app.get("/api/bazar/contacts", dependencies=[Depends(require_key)])
def bazar_contacts(tenant: str = Depends(current_tenant)):
    return {"contacts": bazar.list_contacts(tenant)}


@app.post("/api/bazar/contacts", dependencies=[Depends(require_key)])
def bazar_contact_add(body: BazarContactIn, tenant: str = Depends(current_tenant)):
    return _bz(bazar.add_contact, tenant, body.name, body.upi_id, body.phone, body.relation)


@app.get("/api/bazar/connections", dependencies=[Depends(require_key)])
def bazar_connections(tenant: str = Depends(current_tenant)):
    return {"apps": bazar.connections(tenant)}


@app.post("/api/bazar/connections/{pack_id}/link", dependencies=[Depends(require_key)])
async def bazar_link(pack_id: str, tenant: str = Depends(current_tenant)):
    try:
        return {"url": await asyncio.to_thread(bazar.link_start, tenant, pack_id)}
    except BazarError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/bazar/connections/{pack_id}", dependencies=[Depends(require_key)])
def bazar_unlink(pack_id: str, tenant: str = Depends(current_tenant)):
    return {"unlinked": _bz(bazar.unlink, tenant, pack_id)}


class McpAddIn(BaseModel):
    url: str
    name: str = ""
    ref: str = ""
    key: str = ""
    key_header: str = ""


class McpKeyIn(BaseModel):
    key: str
    header: str = ""


@app.get("/api/bazar/mcp", dependencies=[Depends(require_key)])
def bazar_mcp_list(tenant: str = Depends(current_tenant)):
    return {"servers": _bz(bazar.mcp_list, tenant)}


@app.get("/api/bazar/mcp/directory", dependencies=[Depends(require_key)])
def bazar_mcp_directory(q: str = "", field: str = "", limit: int = 20):
    return _bz(bazar.mcp_directory, q, field, max(1, min(limit, 50)))


@app.post("/api/bazar/mcp", dependencies=[Depends(require_key)])
async def bazar_mcp_add(body: McpAddIn, tenant: str = Depends(current_tenant)):
    try:
        return await asyncio.to_thread(bazar.mcp_add, tenant, body.url, body.name, body.ref, body.key, body.key_header)
    except BazarError as e:
        raise HTTPException(400, str(e))


@app.put("/api/bazar/mcp/{pack_id}/key", dependencies=[Depends(require_key)])
def bazar_mcp_key(pack_id: str, body: McpKeyIn, tenant: str = Depends(current_tenant)):
    return _bz(bazar.mcp_set_key, tenant, pack_id, body.key, body.header)


@app.delete("/api/bazar/mcp/{pack_id}", dependencies=[Depends(require_key)])
def bazar_mcp_remove(pack_id: str, tenant: str = Depends(current_tenant)):
    return {"removed": _bz(bazar.mcp_remove, tenant, pack_id)}


@app.get("/bazar/link/callback")
async def bazar_link_callback(state: str = "", code: str = "", error: str = ""):
    from html import escape
    scheme = get_settings().app_redirect_scheme
    if error or not code:
        msg, ok = f"Linking was cancelled ({escape(error or 'no code')}).", False
    else:
        try:
            _, name = await asyncio.to_thread(bazar.link_finish, state, code)
            msg, ok = f"{escape(name)} is now linked to Santosh.", True
        except BazarError as e:
            msg, ok = escape(str(e)), False
    link = f"{scheme}://bazar?linked={'1' if ok else '0'}"
    from fastapi.responses import HTMLResponse
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:sans-serif;padding:32px;text-align:center"><h2>{'✅' if ok else '⚠️'} {msg}</h2>
<p><a href="{link}" style="font-size:18px">Back to Santosh</a></p><script>setTimeout(()=>location.href="{link}",800)</script>""")


class BazarTokenIn(BaseModel):
    tenant: str
    provider: str
    access_token: str = Field(min_length=8)
    expires_in: int | None = None


@app.post("/api/bazar/admin/connections")
def bazar_admin_link(body: BazarTokenIn, request: Request):
    st = get_settings()
    if not st.api_key or not hmac.compare_digest(_bearer(request), st.api_key):
        raise HTTPException(401, "Admin API key required")
    _bz(bazar.link_token, body.tenant, body.provider, body.access_token, body.expires_in)
    return {"linked": body.provider}


@app.post("/bazar/webhooks/payment")
async def bazar_payment_webhook(request: Request):
    raw = await request.body()
    if not bazar.verify_webhook(raw, request.headers.get("x-signature", "")):
        raise HTTPException(401, "Bad or missing signature (set BAZAR_WEBHOOK_SECRET)")
    try:
        data = json.loads(raw)
        ref, status = str(data["txn_ref"]), str(data.get("status", "")).upper()
    except Exception:
        raise HTTPException(422, "Body must be JSON with txn_ref and status")
    return await asyncio.to_thread(lambda: _bz(bazar.payment_confirmed, ref, status == "SUCCESS", str(data.get("provider_ref", ""))))


@app.post("/api/bazar/dev/simulate-payment/{txn_ref}", dependencies=[Depends(require_key)])
def bazar_simulate(txn_ref: str, ok: bool = True):
    from .bazar.config import get_settings as bz_settings
    if bz_settings().env != "dev":
        raise HTTPException(404, "Not found")
    return _bz(bazar.payment_confirmed, txn_ref, ok, "SIMULATED")


# merchants: a shop manages its orders with its own X-Shop-Token (shown once at onboarding)
class ShopIn(BaseModel):
    template_id: str
    name: str = Field(min_length=2, max_length=160)
    owner_phone: str
    upi_id: str
    city: str = ""
    pincodes: list[str] = []
    aliases: list[str] = []
    languages: list[str] = ["mr", "hi", "en"]
    min_order_rupees: float = 0
    delivery_fee_rupees: float = 0
    slots: list[str] = []


class ShopItemIn(BaseModel):
    name: str
    price_rupees: float = Field(gt=0)
    unit: str = "pc"
    unit_qty: float = 1.0
    aliases: list[str] = []
    in_stock: bool = True
    kind: str = "product"


class OrderUpdateIn(BaseModel):
    status: str | None = None
    paid: bool = False


class DueIn(BaseModel):
    customer_ref: str
    amount_rupees: float = Field(gt=0)
    customer_phone: str = ""
    description: str = ""
    due_on: str | None = None


@app.post("/api/bazar/shops", dependencies=[Depends(require_key)])
def bazar_create_shop(body: ShopIn, tenant: str = Depends(current_tenant)):
    return _bz(bazar.create_shop, tenant, body.model_dump())


@app.get("/bazar/shops")
def bazar_list_shops(template: str | None = None, pincode: str | None = None):
    return bazar.list_shops(template, pincode)


@app.post("/bazar/shops/{shop_id}/items")
def bazar_shop_items(shop_id: str, items: list[ShopItemIn], request: Request):
    return _bz(bazar.add_items, shop_id, [i.model_dump() for i in items], _maybe_tenant(request), request.headers.get("x-shop-token"))


@app.get("/bazar/shops/{shop_id}/orders")
def bazar_shop_orders(shop_id: str, request: Request, status: str | None = None):
    return _bz(bazar.shop_orders, shop_id, _maybe_tenant(request), request.headers.get("x-shop-token"), status)


@app.post("/bazar/shops/{shop_id}/orders/{order_id}")
def bazar_shop_order_update(shop_id: str, order_id: str, body: OrderUpdateIn, request: Request):
    return _bz(bazar.update_order, shop_id, order_id, body.status, body.paid, _maybe_tenant(request),
               request.headers.get("x-shop-token"))


@app.post("/bazar/shops/{shop_id}/dues")
def bazar_shop_dues(shop_id: str, dues: list[DueIn], request: Request):
    return _bz(bazar.upload_dues, shop_id, [d.model_dump() for d in dues], _maybe_tenant(request), request.headers.get("x-shop-token"))


# ---------------- catch-up: what Santosh did while the phone was off ----------------
@app.get("/api/catchup", dependencies=[Depends(require_key)])
def catchup(since: str, tenant: str = Depends(current_tenant)):
    from datetime import datetime, timezone
    try:
        t = datetime.fromisoformat(since.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(400, "since must be an ISO time")
    with session() as s:
        convs = [c.id for c in s.scalars(select(Conversation).where(Conversation.tenant_id == tenant)).all()]
        rows = s.scalars(select(Message).where(Message.conversation_id.in_(convs), Message.role == "assistant",
                                               Message.in_history.is_(False), Message.created_at > t)
                         .order_by(Message.id).limit(60)).all() if convs else []
        items = [{"text": r.display or "", "at": r.created_at.isoformat()} for r in rows if (r.display or "").strip()]
    pending = bazar.pending_approvals(tenant)
    return {"items": items, "pending": pending, "count": len(items)}


# ---------------- "Hey Santosh" wake word (runs on the phone; the server only hands out the keyword) ----------------
def _wake_file():
    import os
    st = get_settings()
    f = st.wake_keyword_file.strip()
    return f if f and os.path.isfile(f) else ""


@app.get("/api/wake", dependencies=[Depends(require_key)])
def wake_config(tenant: str = Depends(current_tenant)):
    import os
    st = get_settings()
    f = _wake_file()
    if not st.picovoice_access_key.strip():
        return {"available": False, "reason": "Server par PICOVOICE_ACCESS_KEY set nahi hai"}
    if not f:
        return {"available": False, "reason": "Server par 'Hey Santosh' keyword file (WAKE_KEYWORD_FILE) nahi mili"}
    return {"available": True, "access_key": st.picovoice_access_key.strip(), "sensitivity": st.wake_sensitivity,
            "version": str(int(os.path.getmtime(f)))}


@app.get("/api/wake/keyword", dependencies=[Depends(require_key)])
def wake_keyword(tenant: str = Depends(current_tenant)):
    f = _wake_file()
    if not f:
        raise HTTPException(404, "No keyword file")
    return FileResponse(f, media_type="application/octet-stream", filename="hey_santosh.ppn")
