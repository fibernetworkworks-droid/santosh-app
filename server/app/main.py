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
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
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


app = FastAPI(title="Santosh Core", version="0.6.0", lifespan=lifespan)


def require_key(request: Request) -> None:
    key = get_settings().api_key
    if not key:
        return
    got = request.headers.get("authorization", "").removeprefix("Bearer ").strip() or request.query_params.get("key", "")
    if not hmac.compare_digest(got, key):
        raise HTTPException(401, "Missing or wrong API key")


def _conv_or_404(conversation_id: str) -> Conversation:
    with session() as s:
        c = s.get(Conversation, conversation_id)
        if not c or c.tenant_id != get_settings().tenant_id:
            raise HTTPException(404, "Conversation not found")
        return c


# ---------------- health + demo page ----------------
@app.get("/healthz")
def healthz():
    st = get_settings()
    from .voice import MALE_VOICES
    from . import mail
    features = ["routines", "voice", "web"] + (["realtime_voice", "google_search"] if st.gemini_api_key else []) \
        + (["email"] if mail.configured() else [])
    return {"ok": True, "version": app.version, "dry_run": st.wa_dry_run, "model": st.anthropic_model,
            "brain_configured": bool(st.anthropic_api_key), "features": features,
            "voices": [{"id": k, "style": v} for k, v in MALE_VOICES.items()], "voice_default": st.voice_default}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------------- conversations ----------------
class NewMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: bool = False   # spoken in voice mode: Santosh answers short and speakable


@app.post("/api/conversations", dependencies=[Depends(require_key)])
def create_conversation():
    with session() as s:
        c = Conversation(tenant_id=get_settings().tenant_id)
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
def list_messages(conversation_id: str):
    _conv_or_404(conversation_id)
    with session() as s:
        rows = s.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.display.is_not(None))
                         .order_by(Message.id)).all()
        return {"messages": [{"id": r.id, "role": r.role, "text": r.display, "at": r.created_at.isoformat()} for r in rows]}


@app.post("/api/conversations/{conversation_id}/messages", status_code=202, dependencies=[Depends(require_key)])
async def post_message(conversation_id: str, body: NewMessage, background: BackgroundTasks):
    _conv_or_404(conversation_id)
    bus.publish(conversation_id, "message", {"role": "user", "text": body.text, "source": "user"})
    background.add_task(run_turn, conversation_id, body.text, None, body.voice)
    return {"accepted": True}


@app.get("/api/conversations/{conversation_id}/events", dependencies=[Depends(require_key)])
async def events(conversation_id: str, request: Request, after: int = 0):
    """Server-sent events: replays everything after `after`, then streams live."""
    _conv_or_404(conversation_id)
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
async def upload_leads(file: UploadFile = File(...), conversation_id: str | None = Form(None)):
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File is larger than 10 MB")
    try:
        res = import_leads(file.filename or "leads.csv", data, get_settings().tenant_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    out = res.as_dict()
    if conversation_id:
        _conv_or_404(conversation_id)
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
def get_reminders(include_done: bool = False):
    return {"reminders": life.upcoming_reminders(get_settings().tenant_id, include_done=include_done)}


@app.post("/api/reminders/{reminder_id}/cancel", dependencies=[Depends(require_key)])
def cancel_reminder_api(reminder_id: str):
    with session() as s:
        r = s.get(Reminder, reminder_id)
        if not r or r.tenant_id != get_settings().tenant_id:
            raise HTTPException(404, "Reminder not found")
        r.status = "cancelled"
        conv = r.conversation_id
    reminders = life.upcoming_reminders(get_settings().tenant_id)
    bus.publish(conv, "reminders", {"reminders": reminders})
    return {"reminders": reminders}


@app.websocket("/api/voice/ws")
async def voice_ws(ws: WebSocket, conv: str = "", voice: str = "", lang: str = "hi-IN"):
    """Realtime voice call (Baat tab). See app/voice.py for the protocol."""
    from . import voice as v
    st = get_settings()
    got = ws.headers.get("authorization", "").removeprefix("Bearer ").strip() or ws.query_params.get("key", "")
    if st.api_key and not hmac.compare_digest(got, st.api_key):
        await ws.close(code=4401)
        return
    with session() as s:
        c = s.get(Conversation, conv)
        ok = bool(c and c.tenant_id == st.tenant_id)
    if not ok:
        await ws.close(code=4404)
        return
    await ws.accept()
    if not st.gemini_api_key:
        await ws.send_text(json.dumps({"type": "error", "message": "Server par GEMINI_API_KEY set nahi hai."}))
        await ws.close()
        return
    await v.Call(ws, conv, voice, lang).run()


@app.get("/api/emails/pending", dependencies=[Depends(require_key)])
def pending_emails():
    from .db import EmailDraft
    tenant = get_settings().tenant_id
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
async def send_email_draft(draft_id: str, body: EmailEdit | None = None):
    """Approve and send. Optional fields let the user edit before sending."""
    from . import mail
    from .db import EmailDraft
    tenant = get_settings().tenant_id
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
def cancel_email_draft(draft_id: str):
    from .db import EmailDraft
    tenant = get_settings().tenant_id
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
def get_routines():
    from . import life
    return {"routines": life.active_routines(get_settings().tenant_id)}


@app.post("/api/routines/{routine_id}/cancel", dependencies=[Depends(require_key)])
def cancel_routine_api(routine_id: str):
    from . import life
    from .db import Routine
    tenant = get_settings().tenant_id
    with session() as s:
        r = s.get(Routine, routine_id)
        if not r or r.tenant_id != tenant:
            raise HTTPException(404, "Routine not found")
        r.status = "cancelled"
        conv = r.conversation_id
    bus.publish(conv, "routines", {"routines": life.active_routines(tenant)})
    return {"cancelled": routine_id}


@app.get("/api/lists", dependencies=[Depends(require_key)])
def get_lists():
    with session() as s:
        rows = s.scalars(select(ListItem).where(ListItem.tenant_id == get_settings().tenant_id, ListItem.done.is_(False))
                         .order_by(ListItem.list_name, ListItem.id)).all()
        out: dict[str, list[dict]] = {}
        for r in rows:
            out.setdefault(r.list_name, []).append({"id": r.id, "text": r.text})
        return {"lists": out}


@app.post("/api/lists/items/{item_id}/done", dependencies=[Depends(require_key)])
def tick_item(item_id: int):
    with session() as s:
        it = s.get(ListItem, item_id)
        if not it or it.tenant_id != get_settings().tenant_id:
            raise HTTPException(404, "Item not found")
        it.done = True
    return get_lists()


@app.get("/api/memory", dependencies=[Depends(require_key)])
def get_memory():
    return {"facts": [{"id": f.id, "text": f.text} for f in life.memory_facts(get_settings().tenant_id)]}


@app.delete("/api/memory/{fact_id}", dependencies=[Depends(require_key)])
def delete_memory(fact_id: int):
    with session() as s:
        f = s.get(MemoryFact, fact_id)
        if not f or f.tenant_id != get_settings().tenant_id:
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
def get_profile_api():
    return _profile_out(life.get_profile(get_settings().tenant_id))


@app.put("/api/profile", dependencies=[Depends(require_key)])
def put_profile(body: ProfileIn):
    tenant = get_settings().tenant_id
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
def pending_actions():
    """The phone asks this on start, so actions created while it was offline still run (within 15 minutes)."""
    with session() as s:
        rows = s.scalars(select(DeviceAction).where(DeviceAction.tenant_id == get_settings().tenant_id,
                                                    DeviceAction.status == "pending").order_by(DeviceAction.created_at)).all()
        return {"actions": [{"id": a.id, "type": a.type, **a.payload} for a in rows]}


@app.post("/api/device-actions/{action_id}/result", dependencies=[Depends(require_key)])
def action_result(action_id: str, body: ActionResult):
    with session() as s:
        a = s.get(DeviceAction, action_id)
        if not a or a.tenant_id != get_settings().tenant_id:
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
