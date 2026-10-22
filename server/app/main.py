"""HTTP API for the Santosh app, the Meta webhook, and the demo chat page."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import logging
import time
import shutil
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response, StreamingResponse
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
    if get_settings().logo_warm:
        from .bazar import logos
        logos.warm_in_background()   # fetch every plugin logo once, gently, so the Connect tab is quick
    if get_settings().tv_refresh:
        from .tv import catalog as tv_catalog
        tv_catalog.refresh_in_background()   # Hoola TV: re-check the free channels every night
    if get_settings().video_edit_worker:
        from .videoedit import service as video_service
        video_service.resume_pending()        # v0.65 edits that were running when the server restarted
    if get_settings().ifsc_refresh:
        from .india import ifsc
        ifsc.refresh_in_background()          # v0.59 IFSC branch details, once a month
    from .operator import service as operator_service
    operator_service.MAIN_LOOP = asyncio.get_running_loop()   # v0.67 Computer Operator jobs run on this loop
    if get_settings().operator_worker:
        operator_service.resume_pending()     # a restart closes the browser: those jobs stop honestly
    if get_settings().studio_on and get_settings().operator_worker:
        from .studio import service as studio_service
        asyncio.ensure_future(studio_service.resume_all())   # v0.68 AI video shots already submitted keep being followed
    yield
    stop.set()
    await task
    try:
        await operator_service.shutdown()
    except Exception:
        pass


app = FastAPI(title="Santosh Core", version="0.98.0", lifespan=lifespan)


def _operator_ok() -> bool:
    try:
        from .operator.service import available
        return available()
    except Exception:
        return False


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
    from .voiceid import engine as _vid_engine
    features = ["routines", "voice", "web", "bazar", "avatar", "bluetooth", "theatre", "chat_files", "public_apis", "reels", "employee", "procedures", "darzi", "chai", "office", "lekhak", "mobile_shop", "phone_doctor", "gst", "payroll", "finance", "audit", "insurance"] + (["video_editor"] if shutil.which("ffmpeg") else []) + (["computer_operator"] if _operator_ok() else []) + (["video_studio"] if shutil.which("ffmpeg") and get_settings().studio_on else []) + (["voiceid"] if _vid_engine.available() else []) + (["realtime_voice", "google_search"] if st.gemini_api_key else []) \
        + (["email"] if (mail.configured() or __import__("app.mailbox.accounts", fromlist=["x"]).oauth_ready("google")
                         or __import__("app.mailbox.accounts", fromlist=["x"]).oauth_ready("microsoft")) else []) + (["calendar"] if (__import__("app.gcal", fromlist=["x"]).configured()
                            or __import__("app.cal.accounts", fromlist=["x"]).oauth_ready()) else []) \
        + (["drive"] if __import__("app.gdrive", fromlist=["x"]).configured() else []) \
        + (["sheets"] if __import__("app.sheets.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["gdrive"] if __import__("app.drive.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["forms"] if __import__("app.forms.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["slides"] if __import__("app.slides.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["photos"] if __import__("app.photos.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["youtube"] if (st.youtube_api_key or __import__("app.youtube.accounts", fromlist=["x"]).oauth_ready()) else []) \
        + (["maps"] if __import__("app.maps", fromlist=["x"]).configured() else []) \
        + (["browser"] if __import__("app.browser", fromlist=["x"]).configured() else []) \
        + (["push"] if __import__("app.push", fromlist=["x"]).configured() else [])
    from . import accounts
    return {"ok": True, "app": "Hoola", "version": app.version, "google_login": accounts.oauth_configured(),
            "dry_run": st.wa_dry_run, "model": st.anthropic_model,
            "chat_brain": __import__("app.agent.llm", fromlist=["x"]).describe(),
            "brain_configured": bool(st.anthropic_api_key), "features": features,
            "voices": [{"id": k, "style": v} for k, v in MALE_VOICES.items()], "voice_default": st.voice_default,
            "bazar": {"packs": len(__import__("app.bazar.packs.registry", fromlist=["x"]).registry().packs),
                      "bills_live": __import__("app.bazar.config", fromlist=["x"]).get_settings().bills_live,
                      "mcp_directory": len(__import__("app.bazar.directory", fromlist=["x"]).servers()),
                      "agent_army": len(__import__("app.bazar.agents", fromlist=["x"]).agents())}}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/privacy")
def privacy():
    """Privacy policy (Play listing link): what each permission is used for, incl. v0.84 payment-alert reading."""
    return FileResponse(STATIC / "privacy.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------------- conversations ----------------
class NewMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: bool = False   # spoken in voice mode: Santosh answers short and speakable
    client_id: str | None = Field(default=None, max_length=64)   # same id again = the phone retrying a send; run it once
    files: list[str] = Field(default_factory=list, max_length=6)   # file_ids from /conversations/{id}/files


# (tenant, conversation, client_id) of recent sends, so a retry after a timeout never makes Santosh act twice
_SEEN_SENDS: "OrderedDict[tuple[str, str, str], float]" = OrderedDict()


def _already_sent(tenant: str, conversation_id: str, client_id: str | None) -> bool:
    if not client_id:
        return False
    now = time.monotonic()
    while _SEEN_SENDS and (len(_SEEN_SENDS) > 2000 or now - next(iter(_SEEN_SENDS.values())) > 600):
        _SEEN_SENDS.popitem(last=False)
    key = (tenant, conversation_id, client_id)
    if key in _SEEN_SENDS:
        return True
    _SEEN_SENDS[key] = now
    return False


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



@app.post("/api/conversations/{conversation_id}/stop", dependencies=[Depends(require_key)])
def stop_turn(conversation_id: str, tenant: str = Depends(current_tenant)):
    """Rokiye: Hoola stops the task after the step it is on (nothing new starts)."""
    _conv_or_404(conversation_id, tenant)
    from .agent.santosh import stop
    stop(conversation_id)
    return {"stopped": True}

@app.get("/api/conversations/{conversation_id}/messages", dependencies=[Depends(require_key)])
def list_messages(conversation_id: str, limit: int = 0, tenant: str = Depends(current_tenant)):
    _conv_or_404(conversation_id, tenant)
    with session() as s:
        q = select(Message).where(Message.conversation_id == conversation_id, Message.display.is_not(None))
        if limit > 0:   # v0.62 the bubble / widget only need the last few
            rows = list(reversed(s.scalars(q.order_by(Message.id.desc()).limit(min(limit, 200))).all()))
        else:
            rows = s.scalars(q.order_by(Message.id)).all()
        return {"messages": [{"id": r.id, "role": r.role, "text": r.display, "at": r.created_at.isoformat()} for r in rows]}


@app.post("/api/conversations/{conversation_id}/messages", status_code=202, dependencies=[Depends(require_key)])
async def post_message(conversation_id: str, body: NewMessage, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    _conv_or_404(conversation_id, tenant)
    if _already_sent(tenant, conversation_id, body.client_id):
        return {"accepted": True, "duplicate": True}
    from . import chatfiles
    context = chatfiles.context(tenant, body.files) if body.files else ""
    shown = chatfiles.shown(tenant, body.files) if body.files else []
    bus.publish(conversation_id, "message", {"role": "user", "text": body.text, "source": "user",
                                             **({"files": shown} if shown else {})})
    if context:
        background.add_task(run_turn, conversation_id, body.text, tenant, body.voice, context=context)
    else:
        background.add_task(run_turn, conversation_id, body.text, tenant, body.voice)
    return {"accepted": True}


@app.post("/api/conversations/{conversation_id}/files", dependencies=[Depends(require_key)])
async def chat_file(conversation_id: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """The chat / voice-call paperclip: ANY file (photo, PDF, video, Excel...), kept as the owner's file so Hoola can
    read it and send it on. A CSV / Excel with a phone column is also imported as a leads list (no error if not)."""
    _conv_or_404(conversation_id, tenant)
    from . import chatfiles
    data = await file.read(chatfiles.MAX_BYTES + 1)
    try:
        return await asyncio.to_thread(chatfiles.store, tenant, file.filename or "file", data, file.content_type or "")
    except chatfiles.FileError as e:
        raise HTTPException(413 if len(data) > chatfiles.MAX_BYTES else 400, str(e))


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
                from .employee import inbox as biz_inbox
                try:   # Hoola Employee: customers writing to a business number (never breaks campaign tracking)
                    biz_inbox.receive(value)
                    biz_inbox.statuses(value.get("statuses") or [])
                except Exception:
                    logging.getLogger("santosh.webhook").exception("employee inbox webhook")
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
    from .mailbox.accounts import is_link_state
    if is_link_state(request.query_params.get("state", "")):   # "connect my Gmail" from the app, not a sign-in
        return await _finish_mail_link(request)
    from .cal.accounts import is_link_state as is_cal_state
    if is_cal_state(request.query_params.get("state", "")):    # "connect my Google Calendar"
        return await _finish_cal_link(request)
    from .sheets.accounts import is_link_state as is_sheets_state
    if is_sheets_state(request.query_params.get("state", "")):  # "connect my Google Sheets"
        return await _finish_sheets_link(request)
    from .youtube.accounts import is_link_state as is_youtube_state
    if is_youtube_state(request.query_params.get("state", "")):  # "connect my YouTube channel"
        return await _finish_youtube_link(request)
    from .slides.accounts import is_link_state as is_slides_state
    if is_slides_state(request.query_params.get("state", "")):  # "connect my Google Slides"
        return await _finish_slides_link(request)
    from .photos.accounts import is_link_state as is_photos_state
    if is_photos_state(request.query_params.get("state", "")):  # "connect my Google Photos"
        from .photos.api import finish_page as photos_finish
        return await photos_finish(request)
    from .drive.accounts import is_link_state as is_drive_state
    if is_drive_state(request.query_params.get("state", "")):   # "connect my Google Drive"
        from .drive.api import finish_page as drive_finish
        return await drive_finish(request)
    from .forms.accounts import is_link_state as is_form_state
    if is_form_state(request.query_params.get("state", "")):    # "connect my Google Forms"
        from .forms.api import finish_page as forms_finish
        return await forms_finish(request)
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


# ---------------------------------------------------------------- PC bridge (Santosh Desktop)
class PairIn(BaseModel):
    code: str
    name: str = "PC"
    os: str = ""


class PcSearchIn(BaseModel):
    query: str
    kind: str = "any"


class PcPullIn(BaseModel):
    path: str


def _pc_device(request: Request):
    from .pc import service as pcs
    tok = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    dev = pcs.device_for_token(tok)
    if dev is None:
        raise HTTPException(401, "This PC is not paired (or was removed). Pair it again from the Santosh app.")
    return dev


def _pc_err(e: Exception):
    from .pc.hub import PcOffline
    if isinstance(e, PcOffline):
        raise HTTPException(409, "PC offline hai. PC on karke Santosh Desktop kholiye.")
    raise HTTPException(400, str(e))


@app.post("/api/pc/pair/start", dependencies=[Depends(require_key)])
def pc_pair_start(tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    return pcs.pair_start(tenant)


@app.post("/api/pc/pair")
def pc_pair(body: PairIn, request: Request):
    from .pc import service as pcs
    try:
        return pcs.pair_finish(body.code, body.name, body.os, request.client.host if request.client else "")
    except pcs.PairError as e:
        raise HTTPException(400, str(e))


@app.websocket("/api/pc/ws")
async def pc_ws(ws: WebSocket):
    from fastapi import WebSocketDisconnect
    from .pc import service as pcs
    from .pc.hub import hub
    tok = ws.headers.get("authorization", "").removeprefix("Bearer ").strip() or ws.query_params.get("token", "")
    dev = pcs.device_for_token(tok)
    await ws.accept()
    if dev is None:
        await ws.close(code=4401)
        return
    try:
        await hub.serve(ws, dev.id, dev.tenant_id)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("pc socket failed")


@app.post("/api/pc/files")
async def pc_upload(request: Request, file: UploadFile = File(...), path: str = Form("")):
    """The PC uploads a file the phone asked for."""
    from .pc import service as pcs
    dev = _pc_device(request)
    try:
        row = await pcs.store_upload(file, dev.tenant_id, dev.id, "to_phone", path)
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    return {"file_id": row.id, "name": row.name, "size": row.size}


@app.get("/api/pc/files/{file_id}")
def pc_download(file_id: str, exp: int = 0, sig: str = ""):
    """Signed, expiring link the phone opens to download a PC file."""
    from .pc import service as pcs
    if not pcs.check_sig(file_id, exp, sig):
        raise HTTPException(403, "This link expired. Ask Santosh to send the file again.")
    f = pcs.get_file(file_id)
    if f is None or f.direction != "to_phone" or not Path(f.stored_path).exists():
        raise HTTPException(404, "File no longer available")
    return FileResponse(f.stored_path, filename=f.name)


@app.get("/api/pc/fetch/{file_id}")
def pc_fetch(file_id: str, request: Request):
    """The PC downloads a file the phone sent to it."""
    from .pc import service as pcs
    dev = _pc_device(request)
    f = pcs.get_file(file_id)
    if f is None or f.direction != "to_pc" or f.tenant_id != dev.tenant_id or not Path(f.stored_path).exists():
        raise HTTPException(404, "File not found")
    return FileResponse(f.stored_path, filename=f.name)


@app.get("/api/pc/devices", dependencies=[Depends(require_key)])
def pc_devices(tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    return {"devices": pcs.devices(tenant)}


@app.delete("/api/pc/devices/{device_id}", dependencies=[Depends(require_key)])
async def pc_remove(device_id: str, tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    from .pc.hub import hub
    ok = pcs.revoke(tenant, device_id)
    if ok:
        await hub.kick(tenant, device_id)
    return {"removed": ok}


@app.get("/api/pc/jobs", dependencies=[Depends(require_key)])
def pc_jobs(limit: int = 50, tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    return {"jobs": pcs.jobs(tenant, limit)}


@app.post("/api/pc/search", dependencies=[Depends(require_key)])
async def pc_search(body: PcSearchIn, tenant: str = Depends(current_tenant)):
    from .pc.hub import hub
    try:
        return await hub.call(tenant, "search", {"query": body.query, "kind": body.kind, "limit": 30})
    except Exception as e:
        _pc_err(e)


@app.post("/api/pc/pull", dependencies=[Depends(require_key)])
async def pc_pull(body: PcPullIn, tenant: str = Depends(current_tenant)):
    """Phone asks for one PC file; returns a download link."""
    from .pc import service as pcs
    from .pc.hub import hub
    try:
        out = await hub.call(tenant, "send_file", {"path": body.path})
    except Exception as e:
        _pc_err(e)
    f = pcs.get_file(out.get("file_id", ""))
    if f is None or f.tenant_id != tenant:
        raise HTTPException(502, "The file did not arrive from the PC")
    return pcs.public_file(f)


@app.post("/api/pc/send", dependencies=[Depends(require_key)])
async def pc_send(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """Phone sends a file to the PC's Santosh Inbox folder."""
    from .pc import service as pcs
    from .pc.hub import hub
    if not hub.is_online(tenant):
        raise HTTPException(409, "PC offline hai. PC on karke Santosh Desktop kholiye.")
    try:
        row = await pcs.store_upload(file, tenant, "", "to_pc")
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    try:
        return await hub.call(tenant, "save_file", {"file_id": row.id, "name": row.name, "url": f"/api/pc/fetch/{row.id}"})
    except Exception as e:
        _pc_err(e)


@app.get("/api/voice/stats", dependencies=[Depends(require_key)])
def voice_stats(tenant: str = Depends(current_tenant)):
    """How human the calls sound, in numbers: how fast he starts answering, reply length, questions, interruptions,
    silent tool runs. Recent calls since the server started."""
    from . import voice as v
    return v.stats_summary(tenant)


@app.websocket("/api/voice/ws")
async def voice_ws(ws: WebSocket, conv: str = "", voice: str = "", lang: str = "hi-IN", resume: str = ""):
    """Realtime voice call (Baat tab). See app/voice.py for the protocol. `resume` re-joins a call whose phone
    connection dropped (network change) instead of starting a new one."""
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
    if resume:
        call = v.CALLS.get(resume)
        if call is None or call.tenant != tenant or call.conv != conv or call.closed.is_set():
            await ws.send_text(json.dumps({"type": "error", "code": "gone", "message": "Pichli call ab chalu nahi hai."}))
            await ws.close(code=4410)
            return
        reader = await call.attach(ws)
        try:
            await reader   # until this connection drops again or the user hangs up
        except Exception:
            pass
        return
    if not st.gemini_api_key:
        await ws.send_text(json.dumps({"type": "error", "message": "Server par GEMINI_API_KEY set nahi hai."}))
        await ws.close()
        return
    await v.serve(v.Call(ws, conv, voice, lang, tenant))


@app.get("/api/emails/pending", dependencies=[Depends(require_key)])
def pending_emails(tenant: str = Depends(current_tenant)):
    from .db import EmailDraft
    from .mailbox import service as ms
    with session() as s:
        rows = s.scalars(select(EmailDraft).where(EmailDraft.tenant_id == tenant, EmailDraft.status.in_(("pending", "scheduled")))
                         .order_by(EmailDraft.created_at)).all()
        return {"emails": [ms.draft_view(d) for d in rows]}


class EmailEdit(BaseModel):
    to: str | None = None
    cc: str | None = None
    bcc: str | None = None
    subject: str | None = None
    body: str | None = None
    send_now: bool = False          # ignore the scheduled time and send at once


@app.post("/api/emails/{draft_id}/send", dependencies=[Depends(require_key)])
async def send_email_draft(draft_id: str, body: EmailEdit | None = None, tenant: str = Depends(current_tenant)):
    """The user approved (optionally after editing). Sends now, or schedules when the draft has a send time."""
    from .mailbox import service as ms
    from .mailbox.base import MailError
    edits = body.model_dump(exclude_none=True) if body else {}
    if edits.pop("send_now", False):
        edits["send_at"] = None
    try:
        return await asyncio.to_thread(ms.send_draft, tenant, draft_id, edits)
    except LookupError:
        raise HTTPException(404, "Draft not found")
    except MailError as e:
        raise HTTPException(502, str(e))


@app.post("/api/emails/{draft_id}/cancel", dependencies=[Depends(require_key)])
def cancel_email_draft(draft_id: str, tenant: str = Depends(current_tenant)):
    from .db import EmailDraft
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if not d or d.tenant_id != tenant:
            raise HTTPException(404, "Draft not found")
        if d.status in ("pending", "scheduled", "failed"):
            d.status = "cancelled"
        conv = d.conversation_id
    bus.publish(conv, "email_sent", {"id": draft_id, "status": "cancelled"})
    return {"status": "cancelled"}


@app.post("/api/emails/{draft_id}/attachments", dependencies=[Depends(require_key)])
async def add_email_attachment(draft_id: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """The user adds a file from the phone to a draft before sending."""
    from .db import EmailDraft
    from .mailbox import service as ms
    from .mailbox.base import MailError
    from .pc import service as pcs
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if not d or d.tenant_id != tenant:
            raise HTTPException(404, "Draft not found")
        if d.status not in ("pending", "failed"):
            raise HTTPException(409, "Yeh email ab badla nahi ja sakta")
    try:
        row = await pcs.store_upload(file, tenant, "", "mail")
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        current = [{"file_id": a["file_id"]} if a.get("type") == "file" else
                   {"email_id": a["email_id"], "attachment_id": a["attachment_id"]} if a.get("type") == "email" else
                   {"artifact_id": a["artifact_id"]} for a in (d.attachments or [])]
    try:
        atts = await asyncio.to_thread(ms.describe_attachments, tenant, current + [{"file_id": row.id}])
    except MailError as e:
        raise HTTPException(413, str(e))
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        d.attachments = atts
        view, conv = ms.draft_view(d), d.conversation_id
    bus.publish(conv, "email_draft", view)
    return view


@app.delete("/api/emails/{draft_id}/attachments/{index}", dependencies=[Depends(require_key)])
def remove_email_attachment(draft_id: str, index: int, tenant: str = Depends(current_tenant)):
    from .db import EmailDraft
    from .mailbox import service as ms
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if not d or d.tenant_id != tenant:
            raise HTTPException(404, "Draft not found")
        atts = list(d.attachments or [])
        if 0 <= index < len(atts) and d.status in ("pending", "failed"):
            atts.pop(index)
            d.attachments = atts or None
        view, conv = ms.draft_view(d), d.conversation_id
    bus.publish(conv, "email_draft", view)
    return view


# ---------------- mailboxes (Gmail / Outlook by sign-in, any email by app password) ----------------
@app.get("/api/mail/accounts", dependencies=[Depends(require_key)])
def mail_accounts(tenant: str = Depends(current_tenant)):
    from .mailbox import accounts as ma
    return {"accounts": ma.views(tenant),
            "can_link": {"google": ma.oauth_ready("google"), "microsoft": ma.oauth_ready("microsoft")}}


class ImapIn(BaseModel):
    address: str
    password: str
    name: str = ""
    imap_host: str = ""
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 0


@app.post("/api/mail/accounts/imap", dependencies=[Depends(require_key)])
async def mail_connect_imap(body: ImapIn, tenant: str = Depends(current_tenant)):
    from .mailbox import accounts as ma
    from .mailbox.base import MailError
    try:
        await asyncio.to_thread(ma.connect_imap, tenant, body.address, body.password, body.name, body.imap_host,
                                body.imap_port, body.smtp_host, body.smtp_port)
    except MailError as e:
        raise HTTPException(400, str(e))
    return {"accounts": ma.views(tenant)}


@app.get("/api/mail/accounts/link", dependencies=[Depends(require_key)])
def mail_link(provider: str, login_hint: str = "", tenant: str = Depends(current_tenant)):
    """The app opens the returned URL in the browser; the provider sends the user back to our callback."""
    from .mailbox import accounts as ma
    from .mailbox.base import MailError
    try:
        return {"url": ma.start_link(tenant, provider, login_hint)}
    except MailError as e:
        raise HTTPException(503, str(e))


class MailAccountEdit(BaseModel):
    signature: str | None = None
    default: bool | None = None


@app.patch("/api/mail/accounts/{key}", dependencies=[Depends(require_key)])
def mail_account_edit(key: str, body: MailAccountEdit, tenant: str = Depends(current_tenant)):
    from .mailbox import accounts as ma
    from .mailbox.base import MailError
    try:
        if body.signature is not None:
            ma.set_signature(tenant, key, body.signature)
        if body.default:
            ma.set_default(tenant, key)
    except MailError as e:
        raise HTTPException(400, str(e))
    return {"accounts": ma.views(tenant)}


@app.delete("/api/mail/accounts/{key}", dependencies=[Depends(require_key)])
def mail_account_remove(key: str, tenant: str = Depends(current_tenant)):
    from .mailbox import accounts as ma
    if not ma.remove(tenant, key):
        raise HTTPException(404, "Mailbox not found")
    return {"accounts": ma.views(tenant)}


def _mail_linked_page(view: dict | None, error: str = "") -> HTMLResponse:
    scheme = get_settings().app_redirect_scheme
    deep = f"{scheme}://mail?ok={0 if error else 1}"
    import html as _h
    msg = (f"<h2>Email Santosh se juda! ✅</h2><p>{_h.escape(view['address'])}</p>" if view else
           f"<h3>Email nahi juda</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def _finish_mail_link(request: Request) -> HTMLResponse:
    from .mailbox import accounts as ma
    from .mailbox.base import MailError
    if request.query_params.get("error"):
        return _mail_linked_page(None, request.query_params.get("error_description") or request.query_params["error"])
    try:
        view = await asyncio.to_thread(ma.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except MailError as e:
        return _mail_linked_page(None, str(e))
    return _mail_linked_page(view)


# ---------------- Google Calendar ----------------
def _cal_page(address: str | None, error: str = "") -> HTMLResponse:
    import html as _h
    scheme = get_settings().app_redirect_scheme
    deep = f"{scheme}://calendar?ok={0 if error else 1}"
    msg = (f"<h2>Google Calendar Santosh se juda! ✅</h2><p>{_h.escape(address or '')}</p>" if not error else
           f"<h3>Calendar nahi juda</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def _finish_cal_link(request: Request) -> HTMLResponse:
    from .cal import accounts as ca
    from .cal.google import CalError
    if request.query_params.get("error"):
        return _cal_page(None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(ca.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except CalError as e:
        return _cal_page(None, str(e))
    return _cal_page(view["address"])


def _cal_state(tenant: str) -> dict:
    from .cal import accounts as ca
    from .cal import service as cs
    out = {"accounts": ca.views(tenant), "can_link": ca.oauth_ready(), "prefs": cs.prefs(tenant), "calendars": []}
    try:
        out["calendars"] = [{k: c[k] for k in ("ref", "name", "account", "primary", "reading", "default", "role", "color")}
                            for c in cs.all_calendars(tenant)]
    except Exception as e:
        out["error"] = str(e)
    return out


@app.get("/api/calendar/accounts", dependencies=[Depends(require_key)])
def calendar_accounts(tenant: str = Depends(current_tenant)):
    return _cal_state(tenant)


@app.get("/api/calendar/link", dependencies=[Depends(require_key)])
def calendar_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
    from .cal import accounts as ca
    from .cal.google import CalError
    try:
        return {"url": ca.start_link(tenant, login_hint)}
    except CalError as e:
        raise HTTPException(503, str(e))


class CalPrefsIn(BaseModel):
    read_calendars: list[str] | None = None
    default_calendar: str | None = None
    alert_minutes: int | None = None
    default_account: str | None = None


@app.patch("/api/calendar/prefs", dependencies=[Depends(require_key)])
def calendar_prefs(body: CalPrefsIn, tenant: str = Depends(current_tenant)):
    from .cal import accounts as ca
    from .cal import service as cs
    from .cal.google import CalError
    try:
        if body.default_account:
            ca.set_default(tenant, body.default_account)
        kw = {}
        if body.read_calendars is not None:
            kw["read_calendars"] = body.read_calendars or None
        if body.default_calendar is not None:
            kw["default_calendar"] = body.default_calendar
        if body.alert_minutes is not None:
            kw["alert_minutes"] = max(0, min(body.alert_minutes, 120))
        if kw:
            cs.set_prefs(tenant, **kw)
    except CalError as e:
        raise HTTPException(400, str(e))
    return _cal_state(tenant)


@app.delete("/api/calendar/accounts/{key}", dependencies=[Depends(require_key)])
def calendar_remove(key: str, tenant: str = Depends(current_tenant)):
    from .cal import accounts as ca
    if not ca.remove(tenant, key):
        raise HTTPException(404, "Calendar not found")
    return _cal_state(tenant)


# ---------------- Google Sheets ----------------
def _linked_page(what: str, host: str, address: str | None, error: str = "") -> HTMLResponse:
    import html as _h
    deep = f"{get_settings().app_redirect_scheme}://{host}?ok={0 if error else 1}"
    msg = (f"<h2>{what} Santosh se juda! ✅</h2><p>{_h.escape(address or '')}</p>" if not error else
           f"<h3>{what} nahi juda</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def _finish_sheets_link(request: Request) -> HTMLResponse:
    from .sheets import accounts as sa
    from .sheets.client import SheetError
    if request.query_params.get("error"):
        return _linked_page("Google Sheets", "sheets", None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(sa.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except SheetError as e:
        return _linked_page("Google Sheets", "sheets", None, str(e))
    return _linked_page("Google Sheets", "sheets", view["address"])


def _sheets_state(tenant: str) -> dict:
    from .sheets import accounts as sa
    from .sheets import service as ss
    return {"accounts": sa.views(tenant), "can_link": sa.oauth_ready(), "recent": ss.recent(tenant)}


@app.get("/api/sheets/accounts", dependencies=[Depends(require_key)])
def sheets_accounts(tenant: str = Depends(current_tenant)):
    return _sheets_state(tenant)


@app.get("/api/sheets/link", dependencies=[Depends(require_key)])
def sheets_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
    from .sheets import accounts as sa
    from .sheets.client import SheetError
    try:
        return {"url": sa.start_link(tenant, login_hint)}
    except SheetError as e:
        raise HTTPException(503, str(e))


@app.delete("/api/sheets/accounts/{key}", dependencies=[Depends(require_key)])
def sheets_remove(key: str, tenant: str = Depends(current_tenant)):
    from .sheets import accounts as sa
    if not sa.remove(tenant, key):
        raise HTTPException(404, "Account not found")
    return _sheets_state(tenant)


# ---------------- YouTube ----------------
async def _finish_youtube_link(request: Request) -> HTMLResponse:
    from .youtube import accounts as ya
    from .youtube.client import YTError
    if request.query_params.get("error"):
        return _linked_page("YouTube", "youtube", None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(ya.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except YTError as e:
        return _linked_page("YouTube", "youtube", None, str(e))
    return _linked_page("YouTube", "youtube", (view.get("channel") or "") + " · " + view["address"])


def _youtube_state(tenant: str) -> dict:
    from .youtube import accounts as ya
    st = get_settings()
    return {"accounts": ya.views(tenant), "can_link": ya.oauth_ready(), "public_search": bool(st.youtube_api_key),
            "can_watch": bool(st.gemini_api_key)}


@app.get("/api/youtube/accounts", dependencies=[Depends(require_key)])
def youtube_accounts(tenant: str = Depends(current_tenant)):
    return _youtube_state(tenant)


@app.get("/api/youtube/link", dependencies=[Depends(require_key)])
def youtube_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
    from .youtube import accounts as ya
    from .youtube.client import YTError
    try:
        return {"url": ya.start_link(tenant, login_hint)}
    except YTError as e:
        raise HTTPException(503, str(e))


@app.delete("/api/youtube/accounts/{key}", dependencies=[Depends(require_key)])
def youtube_remove(key: str, tenant: str = Depends(current_tenant)):
    from .youtube import accounts as ya
    if not ya.remove(tenant, key):
        raise HTTPException(404, "Account not found")
    return _youtube_state(tenant)


# ---------------- Google Slides ----------------
async def _finish_slides_link(request: Request) -> HTMLResponse:
    from .slides import accounts as sla
    from .slides.client import SlidesError
    if request.query_params.get("error"):
        return _linked_page("Google Slides", "slides", None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(sla.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except SlidesError as e:
        return _linked_page("Google Slides", "slides", None, str(e))
    return _linked_page("Google Slides", "slides", view["address"])


def _slides_state(tenant: str) -> dict:
    from .slides import accounts as sla
    from .slides import service as slv
    return {"accounts": sla.views(tenant), "can_link": sla.oauth_ready(), "recent": slv.recent(tenant)}


@app.get("/api/slides/accounts", dependencies=[Depends(require_key)])
def slides_accounts(tenant: str = Depends(current_tenant)):
    return _slides_state(tenant)


@app.get("/api/slides/link", dependencies=[Depends(require_key)])
def slides_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
    from .slides import accounts as sla
    from .slides.client import SlidesError
    try:
        return {"url": sla.start_link(tenant, login_hint)}
    except SlidesError as e:
        raise HTTPException(503, str(e))


@app.delete("/api/slides/accounts/{key}", dependencies=[Depends(require_key)])
def slides_remove(key: str, tenant: str = Depends(current_tenant)):
    from .slides import accounts as sla
    if not sla.remove(tenant, key):
        raise HTTPException(404, "Account not found")
    return _slides_state(tenant)


# ---------------- Santosh Notebook (NotebookLM-style) ----------------
def _nb_err(fn, *a, **kw):
    from .notebook import service as ns
    try:
        return fn(*a, **kw)
    except ns.NotebookError as e:
        raise HTTPException(400, str(e))


class NotebookIn(BaseModel):
    title: str
    emoji: str = ""


class NotebookSourceIn(BaseModel):
    url: str | None = None
    text: str | None = None
    title: str | None = None
    drive: str | None = None
    sheet: str | None = None


class NotebookAskIn(BaseModel):
    question: str
    save: bool = False


class NotebookMakeIn(BaseModel):
    kind: str
    language: str = ""
    focus: str = ""


class NotebookAudioIn(BaseModel):
    style: str = "deep_dive"
    language: str = "hinglish"
    focus: str = ""
    conversation_id: str = ""


# ---------------- Hoola Network: avatars talk to avatars ----------------
class NetMeIn(BaseModel):
    handle: str | None = None
    discoverable: bool | None = None
    phone: str | None = None


class NetConnectIn(BaseModel):
    to: str = ""
    invite: str = ""
    relation: str = "friend"
    note: str = ""


class NetAnswerIn(BaseModel):
    action: str
    relation: str = ""


class NetLinkIn(BaseModel):
    vip: bool | None = None
    nick: str | None = None
    relation: str | None = None
    verified: bool | None = None


class NetDecideIn(BaseModel):
    action: str
    slot: int | None = None
    minutes: int | None = None
    note: str = ""


class NetSendIn(BaseModel):
    to: str
    kind: str = "message"
    body: dict = Field(default_factory=dict)
    thread_id: str = ""
    handle: bool = False
    goal: str = ""


class NetReplyIn(BaseModel):
    text: str


def _net(fn, *a, **kw):
    from .net import identity as idn
    from .net import service as net
    try:
        return fn(*a, **kw)
    except (net.NetError, idn.IdError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/net/me", dependencies=[Depends(require_key)])
def net_me(tenant: str = Depends(current_tenant)):
    from .net import service as net
    out = _net(net.me, tenant)
    return {k: v for k, v in out.items() if k != "public_key"}


@app.put("/api/net/me", dependencies=[Depends(require_key)])
def net_me_put(body: NetMeIn, tenant: str = Depends(current_tenant)):
    from .net import identity as idn
    if body.handle:
        _net(idn.set_handle, tenant, body.handle)
    if body.discoverable is not None:
        _net(idn.set_discovery, tenant, body.phone, body.discoverable)
    return net_me(tenant)


@app.post("/api/net/invite", dependencies=[Depends(require_key)])
def net_invite(tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.invite, tenant)


@app.get("/api/net/find", dependencies=[Depends(require_key)])
def net_find(q: str, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return {"results": _net(net.find, tenant, q)}


@app.post("/api/net/connect", dependencies=[Depends(require_key)])
def net_connect(body: NetConnectIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.connect, tenant, body.to, body.invite, body.relation, body.note)


@app.get("/api/net/connections", dependencies=[Depends(require_key)])
def net_connections(status: str = "", tenant: str = Depends(current_tenant)):
    from .net import service as net
    return {"connections": _net(net.connections, tenant, status)}


@app.post("/api/net/connections/{lid}", dependencies=[Depends(require_key)])
def net_answer(lid: str, body: NetAnswerIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.answer_connect, tenant, lid, body.action, body.relation)


@app.patch("/api/net/connections/{lid}", dependencies=[Depends(require_key)])
def net_link_patch(lid: str, body: NetLinkIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.update_link, tenant, lid, vip=body.vip, nick=body.nick, relation=body.relation, verified=body.verified)


@app.get("/api/net/inbox", dependencies=[Depends(require_key)])
def net_inbox(tenant: str = Depends(current_tenant)):
    from .net import service as net
    return {"waiting": _net(net.inbox, tenant), "counts": net.counts(tenant)}


@app.post("/api/net/inbox/{mid}", dependencies=[Depends(require_key)])
def net_decide(mid: str, body: NetDecideIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.decide, tenant, mid, body.action, body.slot, body.minutes, body.note)


@app.post("/api/net/send", dependencies=[Depends(require_key)])
def net_send(body: NetSendIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.send, tenant, body.to, body.kind, body.body, "", body.thread_id, body.handle, body.goal)


@app.post("/api/net/upload", dependencies=[Depends(require_key)])
async def net_upload(file: UploadFile = File(...), to: str = Form(""), thread_id: str = Form(""), text: str = Form(""),
                     tenant: str = Depends(current_tenant)):
    """v0.43 The owner attaches a real photo / video / PDF / any file in a Hoola chat. Their own tap = consent."""
    from .mailbox import service as ms
    from .net import service as net
    from .net.share import MAX_MB
    data = await file.read(MAX_MB * 1024 * 1024 + 1)
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"File {MAX_MB} MB se badi hai; Drive link bhejiye.")
    if not data:
        raise HTTPException(400, "File khaali hai.")
    if thread_id and not to:
        to = _net(net.thread, tenant, thread_id)["peer"]
    if not to:
        raise HTTPException(400, "Kise bhejna hai (to / thread_id)?")
    row = await asyncio.to_thread(ms.store_bytes, tenant, file.filename or "file", data)
    return await asyncio.to_thread(_net, net.send, tenant, to, "file", {"file_id": row.id, "text": text[:2000]},
                                   (text or row.name)[:80], thread_id, False, "")


class NetMakeIn(BaseModel):
    kind: str = "pdf"           # pdf | image
    title: str = ""
    content: str = ""


@app.post("/api/net/make", dependencies=[Depends(require_key)])
async def net_make(body: NetMakeIn, tenant: str = Depends(current_tenant)):
    """The avatar makes a document / picture; the app shows it and the owner decides to send it (nothing goes out)."""
    from .net import handle
    from .net.share import local_view
    f = await asyncio.to_thread(_net, handle.make_file, tenant, "image" if body.kind == "image" else "pdf", body.title,
                                body.content)
    return f | (await asyncio.to_thread(local_view, tenant, f["file_id"]))


@app.post("/api/net/messages/{mid}/think", dependencies=[Depends(require_key)])
async def net_think(mid: str, tenant: str = Depends(current_tenant)):
    """'Hoola, isse dekh ke batao': look at the attachment again and suggest replies, right now."""
    from .net import enrich
    return await asyncio.to_thread(enrich.run, tenant, mid)


# ---------------- v0.65 Hoola Video Editor ----------------
class VideoStart(BaseModel):
    file_ids: list[str] = Field(default_factory=list, max_length=8)
    brief: str = Field(default="", max_length=3000)
    platform: str = "reel"
    length_s: int | None = None
    captions: bool = True
    logo_file_id: str = ""
    music_file_id: str = ""
    title: str = ""
    conversation_id: str = ""


class VideoChange(BaseModel):
    instruction: str = Field(min_length=1, max_length=1500)


def _video_call(fn, *a, **k):
    from .videoedit.service import VideoError
    try:
        return fn(*a, **k)
    except VideoError as e:
        raise HTTPException(400, str(e))


@app.get("/api/video/jobs", dependencies=[Depends(require_key)])
def video_jobs(tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return {"jobs": vs.listing(tenant), "platforms": [{"id": k, **v} for k, v in vs.PLATFORMS.items()]}


@app.post("/api/video/jobs", dependencies=[Depends(require_key)])
def video_start(body: VideoStart, tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return _video_call(vs.start, tenant, body.file_ids, body.brief, body.platform, body.length_s, body.captions,
                       body.logo_file_id, body.music_file_id, body.title, body.conversation_id)


@app.get("/api/video/jobs/{job_id}", dependencies=[Depends(require_key)])
def video_job(job_id: str, tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return _video_call(vs.get, tenant, job_id)


@app.post("/api/video/jobs/{job_id}/revise", dependencies=[Depends(require_key)])
def video_revise(job_id: str, body: VideoChange, tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return _video_call(vs.revise, tenant, job_id, body.instruction)


@app.post("/api/video/jobs/{job_id}/cancel", dependencies=[Depends(require_key)])
def video_cancel(job_id: str, tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return _video_call(vs.cancel, tenant, job_id)


@app.get("/api/video/files/{job_id}/{name}")
def video_file(job_id: str, name: str, exp: int = 0, sig: str = ""):
    """Signed, expiring link to a finished video / its frames (opened by the phone's player or browser)."""
    from .videoedit import service as vs
    p = vs.file_for(job_id, name, exp, sig)
    if p is None:
        raise HTTPException(404, "Yeh video link purana ho gaya ya galat hai.")
    media = "video/mp4" if p.suffix == ".mp4" else "image/png" if p.suffix == ".png" else None
    return FileResponse(str(p), media_type=media, filename=p.name)


@app.get("/api/google/status", dependencies=[Depends(require_key)])
def google_status(live: bool = True, tenant: str = Depends(current_tenant)):
    """v0.70 Why her Google Drive / Gmail / Calendar do (not) work, with the fix (no tokens shown)."""
    from . import google_check
    return google_check.diagnose(tenant, live)


# ---------------- v0.68 Hoola Video Studio ----------------
class StudioDecide(BaseModel):
    yes: bool
    proof: dict | None = None      # v0.97 fingerprint signature from her phone (approvekey)


@app.get("/api/studio", dependencies=[Depends(require_key)])
def studio_home(tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    projects = []
    for x in ss.listing(tenant)[:30]:
        try:
            projects.append(ss.view(tenant, ss._load(tenant, x["project"])))
        except Exception:
            pass
    st = get_settings()
    return {"available": ss.available(), "ready": ss.ready_providers(tenant), "projects": projects,
            "month_spent_usd": ss.month_spent(tenant), "month_limit_usd": st.studio_month_usd, "usd_inr": st.studio_usd_inr}


@app.get("/api/studio/projects/{name}", dependencies=[Depends(require_key)])
def studio_project(name: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    try:
        return ss.view(tenant, ss._load(tenant, name))
    except ss.StudioJobError as e:
        raise HTTPException(404, str(e))


@app.post("/api/studio/approvals/{approval_id}", dependencies=[Depends(require_key)])
async def studio_decide(approval_id: str, body: StudioDecide, tenant: str = Depends(current_tenant)):
    """Her tap on a price card: only now does a paid generation start (capped at the shown price)."""
    from .studio import service as ss
    if body.yes:
        _fingerprint(tenant, "studio", approval_id, body.proof)
    try:
        return await ss.decide(tenant, approval_id, body.yes)
    except ss.StudioJobError as e:
        raise HTTPException(400, str(e))


@app.post("/api/studio/projects/{name}/assemble", dependencies=[Depends(require_key)])
async def studio_assemble(name: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    try:
        return await ss.assemble(tenant, name)
    except ss.StudioJobError as e:
        raise HTTPException(400, str(e))


@app.get("/api/studio/files/{tenant_key}/{exp}/{sig}/{name}")
def studio_file(tenant_key: str, exp: str, sig: str, name: str):
    """Signed links to her finished videos / sheets (the app's player and download need no header)."""
    from .studio import service as ss
    f = ss.file_for(tenant_key, exp, sig, name)
    if f is None:
        raise HTTPException(404, "link expired or wrong")
    return FileResponse(f)


@app.get("/api/studio/media/{tenant_key}/media/{sig}/{exp}/{name}")
def studio_media(tenant_key: str, sig: str, exp: str, name: str):
    """Short-lived signed links to character photos, only for a video provider that needs a URL (STUDIO_IMAGE_MODE=public)."""
    from .studio import service as ss
    f = ss.studio_sync(tenant_key).verify_media(sig, exp, name)
    if f is None:
        raise HTTPException(404, "no")
    return FileResponse(f)


# ---------------- v0.67 Hoola Computer Operator ----------------
class OperatorStart(BaseModel):
    task: str = Field(min_length=6, max_length=3000)
    start_url: str = Field(default="", max_length=1000)
    file_ids: list[str] = Field(default_factory=list, max_length=8)
    conversation_id: str = ""


class OperatorAnswer(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    answer: str = Field(default="", max_length=500)   # OTP / CAPTCHA / her secret: typed into the page, never stored


class OperatorInput(BaseModel):
    kind: str = Field(pattern="^(click|type|key)$")
    x: float = 0
    y: float = 0
    text: str = Field(default="", max_length=500)
    key: str = Field(default="", max_length=20)


def _op_call(fn, *a, **k):
    from .operator.service import OperatorJobError
    try:
        return fn(*a, **k)
    except OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.get("/api/operator", dependencies=[Depends(require_key)])
def operator_home(tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    return {"available": ops.available(), "active": ops.active(tenant), "tasks": ops.listing(tenant, 20),
            "recipes": [{k: r.get(k) for k in ("name", "task", "site", "variables", "runs", "updated", "version")}
                        for r in ops.recipes(tenant)]}


@app.post("/api/operator/tasks", dependencies=[Depends(require_key)])
def operator_start(body: OperatorStart, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    return _op_call(ops.start, tenant, body.task, body.start_url, body.file_ids, body.conversation_id)


@app.get("/api/operator/tasks/{task_id}", dependencies=[Depends(require_key)])
def operator_task(task_id: str, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    return _op_call(ops.get, tenant, task_id)


@app.post("/api/operator/tasks/{task_id}/cancel", dependencies=[Depends(require_key)])
def operator_cancel(task_id: str, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    return _op_call(ops.cancel, tenant, task_id)


@app.get("/api/operator/frame", dependencies=[Depends(require_key)])
async def operator_frame(tenant: str = Depends(current_tenant)):
    """The live view: a picture of the job's browser right now (the phone polls it while the job runs)."""
    from .operator import service as ops
    try:
        b = await ops.frame(tenant)
    except ops.OperatorJobError as e:
        raise HTTPException(404, str(e))
    return Response(b, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.post("/api/operator/input", dependencies=[Depends(require_key)])
async def operator_input(body: OperatorInput, tenant: str = Depends(current_tenant)):
    """Her own hands in the live view (tap / type / key): never logged as text, never shown to the model."""
    from .operator import service as ops
    try:
        return await ops.owner_input(tenant, body.kind, body.x, body.y, body.text, body.key)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.post("/api/operator/requests/{request_id}", dependencies=[Depends(require_key)])
async def operator_answer(request_id: str, body: OperatorAnswer, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    try:
        return await ops.resolve(tenant, request_id, body.status, body.answer)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.get("/api/operator/requests/{request_id}/captcha", dependencies=[Depends(require_key)])
async def operator_captcha(request_id: str, tenant: str = Depends(current_tenant)):
    """v0.76 the CAPTCHA picture for her phone (she may be far from the computer)."""
    from .operator import service as ops
    try:
        b = await ops.captcha_image(tenant, request_id)
    except ops.OperatorJobError as e:
        raise HTTPException(404, str(e))
    return Response(b, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.post("/api/operator/requests/{request_id}/captcha/refresh", dependencies=[Depends(require_key)])
async def operator_captcha_refresh(request_id: str, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    try:
        return await ops.captcha_refresh(tenant, request_id)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.get("/api/operator/requests/{request_id}/captcha/solve", dependencies=[Depends(require_key)])
async def operator_captcha_solve(request_id: str, tenant: str = Depends(current_tenant)):
    """v0.78 Hoola reads the CAPTCHA (OCR) and returns the solved text for owner confirmation."""
    from .operator import service as ops
    try:
        return await ops.captcha_solve(tenant, request_id)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.post("/api/operator/requests/{request_id}/captcha/fill", dependencies=[Depends(require_key)])
async def operator_captcha_fill(request_id: str, body: OperatorAnswer, tenant: str = Depends(current_tenant)):
    """v0.78 After the owner confirms / corrects the CAPTCHA answer, type it into the box."""
    from .operator import service as ops
    try:
        return await ops.captcha_fill(tenant, request_id, body.answer)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/operator/recipes/{name}", dependencies=[Depends(require_key)])
def operator_forget(name: str, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    if not ops.forget_recipe(tenant, name):
        raise HTTPException(404, "no such recipe")
    return {"ok": True}


@app.get("/api/app/latest", dependencies=[Depends(require_key)])
async def app_latest(current: str = "", force: bool = False):
    """v0.62 Newest phone-app release (GitHub APK build): version, apk_url, size, sha256, notes, available."""
    from . import appupdate
    if force:
        await asyncio.to_thread(appupdate.latest, True)
    return await asyncio.to_thread(appupdate.check, current)


@app.get("/api/device/keepalive", dependencies=[Depends(require_key)])
async def device_keepalive(brand: str = ""):
    """v0.49 Steps for this phone maker so Hoola keeps running in the background (dontkillmyapp.com, CC BY 4.0)."""
    from . import keepalive
    out = await asyncio.to_thread(keepalive.steps, brand)
    return out | {"checklist": keepalive.checklist(brand), "family": keepalive.family(brand)}


class BgHealth(BaseModel):
    brand: str = ""
    model: str = ""
    sdk: int = 0
    battery_optimized: bool = False
    background_restricted: bool = False
    standby_bucket: int = 0
    notifications: bool = True
    exits: list[dict] = []


@app.post("/api/device/bg_health", dependencies=[Depends(require_key)])
def device_bg_health(body: BgHealth, tenant: str = Depends(current_tenant)):
    """v0.56 The phone says what Android knows (battery saver, restricted, standby bucket, how the app was last stopped);
    the answer is plain-word problems + this phone family's checklist."""
    from . import keepalive
    return keepalive.save_health(tenant, body.model_dump())


@app.get("/api/device/bg_health", dependencies=[Depends(require_key)])
def device_bg_health_last(tenant: str = Depends(current_tenant)):
    from . import keepalive
    return keepalive.last_health(tenant)


# ---------------- v0.47 Public APIs (github.com/public-apis/public-apis) ----------------
@app.get("/api/publicapis", dependencies=[Depends(require_key)])
def publicapis_find(q: str = "", cat: str = "", auth: str = "any", limit: int = 30, tenant: str = Depends(current_tenant)):
    from .publicapis import service as pa
    out = pa.find(q, cat, auth if auth in ("any", "none", "key") else "any", max(1, min(limit, 60)), tenant)
    return out | {"total": len(pa.catalog()), "categories": pa.categories() if not q and not cat else []}


class PublicApiKeyIn(BaseModel):
    key: str = Field(min_length=4, max_length=500)
    place: str = "query"
    field: str = ""


@app.put("/api/publicapis/{api_id}/key", dependencies=[Depends(require_key)])
def publicapis_key(api_id: str, body: PublicApiKeyIn, tenant: str = Depends(current_tenant)):
    """The owner types an API's key in the app (sealed on the server; the avatar never sees it)."""
    from .publicapis import service as pa
    try:
        return pa.save_key(tenant, api_id, body.key, body.place, body.field)
    except pa.ApiError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/publicapis/{api_id}/key", dependencies=[Depends(require_key)])
def publicapis_key_delete(api_id: str, tenant: str = Depends(current_tenant)):
    from .publicapis import service as pa
    return pa.delete_key(tenant, api_id)


@app.get("/api/publicapis/keys", dependencies=[Depends(require_key)])
def publicapis_keys(tenant: str = Depends(current_tenant)):
    from .publicapis import service as pa
    return {"keys": pa.list_keys(tenant)}


@app.post("/api/net/outbox/{oid}", dependencies=[Depends(require_key)])
def net_outbox(oid: str, body: NetAnswerIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.outbox_decide, tenant, oid, body.action)


@app.get("/api/net/threads", dependencies=[Depends(require_key)])
def net_threads(tenant: str = Depends(current_tenant)):
    from .net import service as net
    return {"threads": _net(net.threads, tenant)}


@app.get("/api/net/threads/{tid}", dependencies=[Depends(require_key)])
def net_thread(tid: str, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.thread, tenant, tid)


class NetHandleIn(BaseModel):
    action: str = "start"       # start | stop
    goal: str = ""


@app.post("/api/net/threads/{tid}/handle", dependencies=[Depends(require_key)])
def net_handle(tid: str, body: NetHandleIn, tenant: str = Depends(current_tenant)):
    """'Tum sambhalo' on a whole conversation from the thread screen (or take it back)."""
    from .net import handle
    from .net import service as net
    t = _net(net.thread, tenant, tid)
    if body.action == "start":
        handle.start(tenant, t["id"], body.goal.strip()[:500] or t.get("goal") or "Baat ko aage badhao, mere niyam ke andar.")
    else:
        handle._set_mode(tenant, t["id"], "relay")
    return _net(net.thread, tenant, tid)


@app.post("/api/net/threads/{tid}/reply", dependencies=[Depends(require_key)])
def net_reply(tid: str, body: NetReplyIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.reply, tenant, tid, body.text)


class GroupIn(BaseModel):
    name: str
    emoji: str = ""
    members: list[str] = Field(default_factory=list)


class GroupPostIn(BaseModel):
    kind: str = "message"
    text: str = ""
    title: str = ""
    assign_to: str = ""
    due: str = ""
    file_id: str = ""


class GroupActIn(BaseModel):
    action: str
    who: str = ""
    mute: str = ""
    answer: str = ""


@app.get("/api/net/groups", dependencies=[Depends(require_key)])
def net_groups(tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return {"groups": _net(grp.groups, tenant)}


@app.post("/api/net/groups", dependencies=[Depends(require_key)])
def net_group_create(body: GroupIn, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.create, tenant, body.name, body.emoji, body.members)


@app.get("/api/net/groups/{gid}", dependencies=[Depends(require_key)])
def net_group(gid: str, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.detail, tenant, gid)


@app.post("/api/net/groups/{gid}/post", dependencies=[Depends(require_key)])
def net_group_post(gid: str, body: GroupPostIn, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.post, tenant, gid, body.kind, body.text, body.title, body.assign_to, body.file_id, body.due)


@app.post("/api/net/groups/{gid}/act", dependencies=[Depends(require_key)])
def net_group_act(gid: str, body: GroupActIn, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    a = body.action
    if a == "invite":
        return _net(grp.invite, tenant, gid, body.who)
    if a == "remove":
        return _net(grp.remove, tenant, gid, body.who)
    if a == "leave":
        return _net(grp.leave, tenant, gid)
    if a == "mute":
        return _net(grp.set_mute, tenant, gid, body.mute)
    if a == "answer_invite":
        return _net(grp.answer_invite, tenant, gid, body.answer or "accept")
    if a == "digest":
        return _net(grp.digest, tenant, gid, 24)
    raise HTTPException(400, "action?")


@app.post("/api/net/group-posts/{pid}/task", dependencies=[Depends(require_key)])
def net_group_task(pid: str, body: NetAnswerIn, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.task_answer, tenant, pid, body.action)


@app.post("/api/net/group-posts/{pid}/file", dependencies=[Depends(require_key)])
def net_group_file(pid: str, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.take_file, tenant, pid)


class SamajIn(BaseModel):
    name: str
    topic: str = ""
    description: str = ""
    visibility: str = "open"
    emoji: str = ""


class SamajPostIn(BaseModel):
    kind: str
    data: dict = Field(default_factory=dict)


class SamajActIn(BaseModel):
    action: str
    helpful: bool = True
    mod_action: str = ""
    who: str = ""
    reason: str = ""
    mute: str = ""


class LessonActIn(BaseModel):
    action: str
    communities: list[str] = Field(default_factory=list)
    text: str = ""


@app.get("/api/net/learned", dependencies=[Depends(require_key)])
def net_learned(tenant: str = Depends(current_tenant)):
    from .net import learning as lrn
    return {"lessons": lrn.lessons(tenant), "skills": lrn.skills(tenant)}


@app.post("/api/net/learned/{lid}", dependencies=[Depends(require_key)])
def net_lesson_act(lid: str, body: LessonActIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    from .net import learning as lrn
    if body.action == "forget":
        return _net(lrn.forget, tenant, lid)
    if body.action == "share":
        cids = body.communities or [c["cid"] for c in sam.my_communities(tenant) if c["status"] == "active"]
        return _net(lrn.share, tenant, lid, cids, body.text)
    if body.action == "dont_share":
        return _net(lrn.decline_share, tenant, lid)
    raise HTTPException(400, "action?")


@app.post("/api/net/skills/{sid}", dependencies=[Depends(require_key)])
def net_skill_act(sid: str, body: NetAnswerIn, tenant: str = Depends(current_tenant)):
    from .net import learning as lrn
    return _net(lrn.set_skill, tenant, sid, body.action)


@app.get("/api/net/samaj", dependencies=[Depends(require_key)])
def net_samaj(q: str = "", tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return {"mine": sam.my_communities(tenant), "directory": sam.directory(tenant, q)}


@app.post("/api/net/samaj", dependencies=[Depends(require_key)])
def net_samaj_create(body: SamajIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return _net(sam.create, tenant, body.name, body.topic, body.description, body.visibility, body.emoji)


@app.get("/api/net/samaj/{cid}", dependencies=[Depends(require_key)])
def net_samaj_detail(cid: str, kind: str = "", tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return _net(sam.detail, tenant, cid, kind)


@app.post("/api/net/samaj/{cid}/join", dependencies=[Depends(require_key)])
def net_samaj_join(cid: str, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return _net(sam.join, tenant, cid)


@app.post("/api/net/samaj/{cid}/post", dependencies=[Depends(require_key)])
def net_samaj_post(cid: str, body: SamajPostIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return _net(sam.post, tenant, cid, body.kind, body.data)


@app.post("/api/net/samaj/{cid}/act", dependencies=[Depends(require_key)])
def net_samaj_act(cid: str, body: SamajActIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    if body.action == "leave":
        return _net(sam.leave, tenant, cid)
    if body.action == "mute":
        return _net(sam.set_mute, tenant, cid, body.mute)
    if body.action == "moderate_member":
        return _net(sam.moderate, tenant, cid, body.mod_action, "", body.who)
    raise HTTPException(400, "action?")


@app.post("/api/net/samaj-items/{iid}", dependencies=[Depends(require_key)])
def net_samaj_item(iid: str, body: SamajActIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    if body.action == "rate":
        return _net(sam.rate, tenant, iid, body.helpful)
    if body.action == "report":
        return _net(sam.report, tenant, iid, body.reason)
    if body.action == "install":
        return _net(sam.install_skill, tenant, iid)
    if body.action == "moderate":
        it, c = _net(sam._my_item, tenant, iid)
        return _net(sam.moderate, tenant, c.cid, body.mod_action, iid, "")
    raise HTTPException(400, "action?")


class BizIn(BaseModel):
    name: str | None = None
    category: str | None = None
    area: str | None = None
    about: str | None = None
    hours: str | None = None
    catalog: list | None = None
    public: bool | None = None
    ticket_prefix: str | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None
    auto_assign: bool | None = None
    team: list[str] | None = None


class TicketIn(BaseModel):
    status: str = ""
    note: str = ""
    to: str = ""


class ChainActIn(BaseModel):
    action: str
    to: str = ""
    note: str = ""


class ComplainIn(BaseModel):
    business: str
    text: str
    kind: str = "complain"


@app.get("/api/net/business", dependencies=[Depends(require_key)])
def net_business(tenant: str = Depends(current_tenant)):
    from .net import business as biz
    return {"business": biz.profile(tenant), "tickets": biz.tickets(tenant) if biz.profile(tenant) else [],
            "my_tickets": biz.my_tickets(tenant)}


@app.put("/api/net/business", dependencies=[Depends(require_key)])
def net_business_put(body: BizIn, tenant: str = Depends(current_tenant)):
    from .net import business as biz
    return _net(biz.setup, tenant, **{k: v for k, v in body.model_dump().items() if v is not None})


@app.post("/api/net/business/verify", dependencies=[Depends(require_key)])
def net_business_verify(body: TicketIn, tenant: str = Depends(current_tenant)):
    from .net import business as biz
    return _net(biz.request_verification, tenant, body.note)


@app.get("/api/net/businesses", dependencies=[Depends(require_key)])
def net_businesses(q: str = "", category: str = "", tenant: str = Depends(current_tenant)):
    from .net import business as biz
    return {"businesses": biz.directory(tenant, q, category)}


@app.post("/api/net/businesses/contact", dependencies=[Depends(require_key)])
def net_business_contact(body: ComplainIn, tenant: str = Depends(current_tenant)):
    from .net import business as biz
    from .net import service as net
    if body.kind == "complain":
        return _net(biz.complain, tenant, body.business, body.text)
    addr = _net(biz.contact, tenant, body.business)
    k = {"quote": "ask", "order": "order"}.get(body.kind, "ask")
    return _net(net.send, tenant, addr, k, {"text": ({"quote": "Quote chahiye: ", "order": "Order: "}.get(body.kind, "")) + body.text})


@app.post("/api/net/tickets/{number}", dependencies=[Depends(require_key)])
def net_ticket(number: str, body: TicketIn, tenant: str = Depends(current_tenant)):
    from .net import business as biz
    if body.to:
        return _net(biz.assign, tenant, number, body.to, body.note)
    return _net(biz.update_ticket, tenant, number, body.status, body.note)


@app.get("/api/net/chains", dependencies=[Depends(require_key)])
def net_chains(tenant: str = Depends(current_tenant)):
    from .net import chain as chn
    return {"chains": chn.chains(tenant)}


@app.post("/api/net/chains/{cid}", dependencies=[Depends(require_key)])
def net_chain_act(cid: str, body: ChainActIn, tenant: str = Depends(current_tenant)):
    from .net import chain as chn
    return _net(chn.act, tenant, cid, body.action, body.to, body.note)


@app.get("/api/net/operator/verifications", dependencies=[Depends(require_key)])
def net_operator_queue(tenant: str = Depends(current_tenant)):
    from .net import business as biz
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "Sirf server operator")
    return {"requests": biz.verification_queue()}


@app.post("/api/net/operator/verifications/{biz_tenant}", dependencies=[Depends(require_key)])
def net_operator_verify(biz_tenant: str, body: NetAnswerIn, tenant: str = Depends(current_tenant)):
    from .net import business as biz
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "Sirf server operator")
    return _net(biz.operator_verify, biz_tenant, body.action == "approve")


@app.post("/hooks/hoola/{handle}/ticket")
async def net_ticket_webhook(handle: str, request: Request):
    """The business's own system (FNW Flow, a CRM...) updates a Hoola ticket. Body {ticket, status, note}, signed:
    X-Hoola-Signature: sha256=<HMAC-SHA256(secret, body)>."""
    from .net import business as biz
    from .net import identity as idn
    row = idn.by_handle(handle)
    if row is None:
        raise HTTPException(404, "not found")
    raw = await request.body()
    try:
        return biz.webhook_in(row.tenant_id, raw, request.headers.get("x-hoola-signature", ""))
    except Exception as e:
        raise HTTPException(400, str(e)[:120])


# ---------------- Hoola federation (other Hoola servers) and A2A discovery ----------------
@app.get("/.well-known/hoola.json")
def hoola_server_card():
    from .net import federation as fed
    return fed.server_card()


@app.get("/.well-known/agent-card.json")
@app.get("/.well-known/agent.json")
def hoola_agent_card():
    from .net import federation as fed
    return fed.agent_card()


@app.post("/hoola/inbox")
async def hoola_inbox(request: Request):
    from .net import federation as fed
    raw = await request.body()
    if len(raw) > 512 * 1024:
        raise HTTPException(413, "too big")
    try:
        return await asyncio.to_thread(fed.inbox, dict(request.headers), raw)
    except fed.FedError as e:
        raise HTTPException(401, str(e))


@app.get("/hoola/lookup")
def hoola_lookup(handle: str):
    from .net import federation as fed
    c = fed.public_lookup(handle)
    if c is None:
        raise HTTPException(404, "not found")
    return c


@app.get("/hoola/share/{sid}")
def hoola_share(sid: str, request: Request):
    from urllib.parse import quote
    from .net import federation as fed
    from .net.service import NetError
    try:
        name, mime, data, sha = fed.serve_share(dict(request.headers), sid, request.query_params.get("for", ""))
    except (fed.FedError, NetError) as e:
        raise HTTPException(403, str(e))
    return Response(content=data, media_type=mime or "application/octet-stream",
                    headers={"X-Hoola-Name": quote(name), "X-Hoola-SHA256": sha})


@app.post("/a2a")
async def hoola_a2a(request: Request):
    from .net import federation as fed
    try:
        body = await request.json()
    except Exception:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
    return await asyncio.to_thread(fed.a2a, body if isinstance(body, dict) else {})


@app.get("/c/{code}", response_class=HTMLResponse)
def net_invite_page(code: str):
    """What a phone camera opens from a Hoola QR: who is inviting, and a button into the Hoola app."""
    import html as _h
    from .net import identity as idn
    from .net.models import Invite
    from .db import session as _s
    with _s() as s:
        inv = s.get(Invite, code)
        owner = inv.tenant_id if inv else None
    if not owner:
        body = "<h2>Yeh invite purana ho gaya</h2><p>Naya QR ya link maangiye.</p>"
    else:
        c = idn.my_card(owner)
        who = _h.escape(idn.label(c))
        deep = f"santosh://connect?c={_h.escape(code)}"
        body = (f"<h2>{who}</h2><p>@{_h.escape(c['handle'])} aapke Hoola se judna chahte hain.</p>"
                f"<p><a class=b href='{deep}'>Hoola app mein kholiye</a></p>"
                "<p class=s>Hoola nahi hai? <a href='https://github.com/fibernetworkworks-droid/santosh-app/releases/latest'>"
                "Yahan se download kijiye</a>, phir yeh link dobara kholiye.</p>")
    return HTMLResponse("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                        "<title>Hoola</title><style>body{font-family:system-ui,sans-serif;background:#0B0A1A;color:#F4F2FF;"
                        "max-width:520px;margin:auto;padding:32px 20px}a{color:#FFB15C}.b{display:inline-block;padding:14px 22px;"
                        "background:#FFB15C;color:#1B1030;border-radius:14px;text-decoration:none;font-weight:700}.s{color:#B9B3DA}"
                        f"</style><h1>Hoola</h1>{body}")


# ---------------- Awaaz Pehchaan: who is talking (owner / family), voice lock ----------------
class VoiceIdModeIn(BaseModel):
    mode: str


class VoiceIdEnrolIn(BaseModel):
    name: str
    relation: str
    gender: str | None = None
    level: str | None = None


class VoiceIdMemberIn(BaseModel):
    level: str | None = None
    name: str | None = None


def _vid(fn, *a, **kw):
    from .voiceid import service as vs
    try:
        return fn(*a, **kw)
    except vs.VoiceIdError as e:
        raise HTTPException(400, str(e))


@app.get("/api/voiceid", dependencies=[Depends(require_key)])
def voiceid_get(tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    return vs.overview(tenant)


@app.put("/api/voiceid/mode", dependencies=[Depends(require_key)])
def voiceid_mode(body: VoiceIdModeIn, tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    return {"mode": _vid(vs.set_mode, tenant, body.mode)}


@app.post("/api/voiceid/enrol", dependencies=[Depends(require_key)])
def voiceid_enrol_start(body: VoiceIdEnrolIn, tenant: str = Depends(current_tenant)):
    """A one-time script with a code; the person reads it aloud themselves in the app."""
    from .voiceid import service as vs
    return _vid(vs.start_enrol, tenant, body.name, body.relation, body.gender, body.level)


@app.post("/api/voiceid/enrol/{enrol_id}", dependencies=[Depends(require_key)])
async def voiceid_enrol_finish(enrol_id: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    data = await file.read(12 * 1024 * 1024 + 1)
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "Recording bahut badi hai.")
    return await asyncio.to_thread(_vid, vs.finish_enrol, tenant, enrol_id, data)


@app.patch("/api/voiceid/members/{member_id}", dependencies=[Depends(require_key)])
def voiceid_member_update(member_id: str, body: VoiceIdMemberIn, tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    return _vid(vs.update, tenant, member_id, body.level, body.name)


@app.delete("/api/voiceid/members/{member_id}", dependencies=[Depends(require_key)])
def voiceid_member_delete(member_id: str, tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    if not vs.delete(tenant, member_id):
        raise HTTPException(404, "Yeh vyakti nahi mila.")
    return {"deleted": True}


# ---------------- Hoola avatar: name, gender, voice, Mere Niyam ----------------
class AvatarIn(BaseModel):
    name: str | None = None
    gender: str | None = None
    voice: str | None = None
    setup_done: bool | None = None
    rules: dict | None = None
    look: str | None = None


class RulesTextIn(BaseModel):
    text: str


@app.get("/api/avatar", dependencies=[Depends(require_key)])
def avatar_get(tenant: str = Depends(current_tenant)):
    from .avatar import service as av
    return av.get(tenant)


@app.put("/api/avatar", dependencies=[Depends(require_key)])
def avatar_put(body: AvatarIn, tenant: str = Depends(current_tenant)):
    from .avatar import service as av
    try:
        return av.save(tenant, body.name, body.gender, body.voice, body.setup_done, body.rules, body.look)
    except av.AvatarError as e:
        raise HTTPException(400, str(e))


@app.get("/api/avatar/looks", dependencies=[Depends(require_key)])
def avatar_looks(gender: str = "f"):
    """The 3D looks an avatar can wear: 100 female (f001..) or 100 male (m001..) looks from around the world.
    For a male avatar "" (the original Santosh) is the default and always allowed."""
    from .avatar import service as av
    g = gender if gender in ("m", "f") else "f"
    return {"gender": g, "default": av.DEFAULT_LOOK[g], "looks": [x for x in av.looks() if x["id"][0] == g]}


@app.post("/api/avatar/rules/parse", dependencies=[Depends(require_key)])
async def avatar_rules_parse(body: RulesTextIn, tenant: str = Depends(current_tenant)):
    """Owner's own words -> proposed rules (not saved until PUT /api/avatar with rules)."""
    from .avatar import service as av
    try:
        cur = av.get(tenant)
        rules = await av.parse_rules(body.text, cur["rules"])
    except av.AvatarError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(503, "Abhi niyam samajh nahi paaye; neeche se khud chuniye.")
    return {"rules": rules, "rules_summary": av.rules_summary(rules, cur["name"])}


# ---------------- App Jaanch (REA static checks of APK / EXE files; nothing is run) ----------------
@app.get("/api/appcheck", dependencies=[Depends(require_key)])
def appcheck_state(tenant: str = Depends(current_tenant)):
    from .appcheck import service as acs
    return acs.status() | {"history": acs.history(tenant)}


@app.post("/api/appcheck/upload", dependencies=[Depends(require_key)])
async def appcheck_upload(file: UploadFile = File(...), conversation_id: str = Form(""), tenant: str = Depends(current_tenant)):
    import asyncio
    from .appcheck import service as acs
    from .appcheck.runner import ReaError
    from .pc import service as pcs
    if not acs.status()["enabled"]:
        raise HTTPException(503, "App Jaanch abhi server par chalu nahi hai.")
    try:
        row = await pcs.store_upload(file, tenant, "", "to_phone", limit_mb=get_settings().appcheck_max_mb)
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    try:
        return await asyncio.to_thread(acs.check, tenant, conversation_id, {"file_id": row.id})
    except (acs.CheckError, ReaError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/appcheck/{cid}", dependencies=[Depends(require_key)])
def appcheck_get(cid: str, tenant: str = Depends(current_tenant)):
    from .appcheck import service as acs
    try:
        return acs.get(tenant, cid)
    except acs.CheckError as e:
        raise HTTPException(404, str(e))


@app.get("/api/notebooks", dependencies=[Depends(require_key)])
def notebooks_list(tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    return {"notebooks": ns.list_notebooks(tenant)}


@app.post("/api/notebooks", dependencies=[Depends(require_key)])
def notebooks_create(body: NotebookIn, tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    nb = ns.create(tenant, "", body.title, body.emoji)
    return ns.detail(tenant, nb["id"])


@app.get("/api/notebooks/{nid}", dependencies=[Depends(require_key)])
def notebooks_detail(nid: str, tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    return _nb_err(ns.detail, tenant, nid)


@app.delete("/api/notebooks/{nid}", dependencies=[Depends(require_key)])
def notebooks_delete(nid: str, tenant: str = Depends(current_tenant)):
    """The user deletes from the app (the app asks 'sure?' first)."""
    from .notebook import service as ns
    return {"deleted": _nb_err(ns.delete, tenant, nid)}


@app.post("/api/notebooks/{nid}/sources", dependencies=[Depends(require_key)])
async def notebooks_add_source(nid: str, body: NotebookSourceIn, tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    src = {k: v for k, v in body.model_dump().items() if v}
    await asyncio.to_thread(_nb_err, ns.add_source, tenant, nid, src)
    return ns.detail(tenant, nid)


@app.post("/api/notebooks/{nid}/upload", dependencies=[Depends(require_key)])
async def notebooks_upload(nid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    from .pc import service as pcs
    try:
        row = await pcs.store_upload(file, tenant, "", "mail")
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    await asyncio.to_thread(_nb_err, ns.add_source, tenant, nid, {"file_id": row.id})
    return ns.detail(tenant, nid)


@app.delete("/api/notebooks/{nid}/sources/{sid}", dependencies=[Depends(require_key)])
def notebooks_remove_source(nid: str, sid: str, tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    _nb_err(ns.remove_source, tenant, nid, sid)
    return ns.detail(tenant, nid)


@app.post("/api/notebooks/{nid}/ask", dependencies=[Depends(require_key)])
async def notebooks_ask(nid: str, body: NotebookAskIn, tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    try:
        return await ns.ask(tenant, nid, body.question, body.save)
    except ns.NotebookError as e:
        raise HTTPException(400, str(e))


@app.post("/api/notebooks/{nid}/make", dependencies=[Depends(require_key)])
async def notebooks_make(nid: str, body: NotebookMakeIn, tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    try:
        return await ns.make(tenant, nid, body.kind, body.language, body.focus)
    except ns.NotebookError as e:
        raise HTTPException(400, str(e))


@app.get("/api/notebooks/{nid}/notes/{note_id}", dependencies=[Depends(require_key)])
def notebooks_note(nid: str, note_id: str, tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    return _nb_err(ns.get_note, tenant, nid, note_id)


@app.post("/api/notebooks/{nid}/audio", dependencies=[Depends(require_key)])
def notebooks_audio(nid: str, body: NotebookAudioIn, tenant: str = Depends(current_tenant)):
    from .notebook import service as ns
    conv = body.conversation_id
    if conv:
        with session() as s:
            c = s.get(Conversation, conv)
            if not c or c.tenant_id != tenant:
                conv = ""
    out = _nb_err(ns.start_audio, tenant, conv, nid, body.language, body.style, body.focus)
    ns.launch_audio(out["audio_id"])
    return out


@app.get("/api/notebooks/{nid}/audio/{aid}/file", dependencies=[Depends(require_key)])
def notebooks_audio_file(nid: str, aid: str, tenant: str = Depends(current_tenant)):
    """A fresh download link for a finished audio overview."""
    from .notebook.models import NotebookAudio
    from .pc import service as pcs
    with session() as s:
        a = s.get(NotebookAudio, aid)
        if not a or a.tenant_id != tenant or a.notebook_id != nid or not a.file_id:
            raise HTTPException(404, "Audio not ready")
        fid = a.file_id
    f = pcs.get_file(fid)
    if f is None:
        raise HTTPException(410, "Audio file expired; make it again")
    return pcs.public_file(f)


from .drive.api import make_router as _drive_router  # noqa: E402
from .forms.api import make_router as _forms_router  # noqa: E402

app.include_router(_drive_router(require_key, current_tenant))
app.include_router(_forms_router(require_key, current_tenant))
from .photos.api import make_router as _photos_router  # noqa: E402

app.include_router(_photos_router(require_key, current_tenant))


@app.get("/auth/microsoft/callback")
async def microsoft_callback(request: Request):
    return await _finish_mail_link(request)


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
    facts = life.memory_facts(tenant, 500)
    used = sum(len(f.text) for f in facts if f.pinned)
    return {"facts": [{"id": f.id, "text": f.text, "pinned": bool(f.pinned)} for f in facts],
            "pinned_chars": used, "pinned_max": life.PINNED_CHARS, "in_prompt": life.RECENT_FACTS}


class PinIn(BaseModel):
    pinned: bool


@app.patch("/api/memory/{fact_id}", dependencies=[Depends(require_key)])
def pin_memory(fact_id: int, body: PinIn, tenant: str = Depends(current_tenant)):
    """'Hamesha yaad': a pinned fact is always in Hoola's mind (short; the rest is searched when needed)."""
    try:
        life.pin_fact(tenant, fact_id, body.pinned)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return get_memory(tenant)


# ---------------- v0.63 seekhe hue kaam + circuit breaker numbers ----------------
class ProcedureIn(BaseModel):
    active: bool | None = None
    title: str | None = None
    steps: list[str] | None = None


@app.get("/api/procedures", dependencies=[Depends(require_key)])
def procedures_list(tenant: str = Depends(current_tenant)):
    from . import procedures
    return {"procedures": procedures.listing(tenant)}


@app.patch("/api/procedures/{pid}", dependencies=[Depends(require_key)])
def procedures_edit(pid: str, body: ProcedureIn, tenant: str = Depends(current_tenant)):
    from . import procedures
    try:
        return procedures.update(tenant, pid, body.active, body.title, body.steps)
    except procedures.ProcedureError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/procedures/{pid}", dependencies=[Depends(require_key)])
def procedures_delete(pid: str, tenant: str = Depends(current_tenant)):
    from . import procedures
    try:
        procedures.delete(tenant, pid)
    except procedures.ProcedureError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.get("/api/jaanch", dependencies=[Depends(require_key)])
async def hoola_jaanch(tenant: str = Depends(current_tenant)):
    """v0.92 Hoola Jaanch: every part checked live (about 10 s) + the last 14 days of real work."""
    from . import jaanch
    return await jaanch.run(tenant)


@app.get("/api/jaanch/report", dependencies=[Depends(require_key)])
def hoola_jaanch_report(days: int = 14, tenant: str = Depends(current_tenant)):
    from . import jaanch
    return jaanch.report(tenant, max(1, min(days, 60)))


@app.get("/api/agent/stats", dependencies=[Depends(require_key)])
def agent_stats():
    from . import procedures
    from .agent.breaker import STATS
    from .agent import pakka
    from . import callreceipt, scrub, web
    from .agent import santosh as _s
    return {"breaker": {k: STATS.get(k, 0) for k in ("steer", "constrain", "stop")}, "procedures": dict(procedures.STATS),
            "pakka": dict(pakka.STATS), "halts": dict(_s.HALTS), "scrubbed": scrub.STATS["scrubbed"],
            "parallel": dict(web.PARALLEL_STATS), "call_receipts": dict(callreceipt.STATS)}


class ShopOrderIn(BaseModel):
    what: str
    site: str = ""
    budget: str = ""
    when: str = ""
    address: str = ""
    notes: str = ""
    compare: list[str] = []
    conversation_id: str = ""


@app.get("/api/shop/sites", dependencies=[Depends(require_key)])
def shop_sites():
    """v0.80 Order karo: sites Hoola can order / book from."""
    from .shop import sites
    return {"sites": sites.listing()}


@app.get("/api/shop/orders", dependencies=[Depends(require_key)])
def shop_orders(tenant: str = Depends(current_tenant)):
    from .shop import service as shop
    return {"orders": shop.orders(tenant)}


@app.post("/api/shop/orders", dependencies=[Depends(require_key)])
def shop_order_new(body: ShopOrderIn, tenant: str = Depends(current_tenant)):
    from .shop import service as shop
    try:
        return shop.order(tenant, body.what, body.conversation_id, body.site, body.budget, body.when, body.address,
                          body.notes, [c.lower() for c in body.compare])
    except shop.ShopError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------- v0.82 Darzi Sahayak (tailor / boutique coworker)
class DarziOrderIn(BaseModel):
    customer: str = ""
    name: str = ""
    phone: str = ""
    items: list[dict] = []
    deliver_on: str = ""
    trial_on: str = ""
    advance: float | None = None
    notes: str = ""
    photos: list[str] = []
    force: bool = False
    conversation_id: str = ""


class DarziOrderPatch(BaseModel):
    deliver_on: str = ""
    trial_on: str = ""
    notes: str = ""
    items: list[dict] | None = None
    force: bool = False


class DarziStatusIn(BaseModel):
    status: str
    note: str = ""
    conversation_id: str = ""


class DarziMoneyIn(BaseModel):
    amount: float | None = None
    how: str = ""
    note: str = ""
    reason: str = ""
    text: str = ""
    conversation_id: str = ""


class DarziMeasureIn(BaseModel):
    customer: str = ""
    name: str = ""
    phone: str = ""
    garment: str
    values: dict | str = {}
    person: str = ""
    note: str = ""
    unit: str = ""


class DarziCustomerIn(BaseModel):
    name: str
    phone: str = ""
    notes: str = ""


class DarziQuoteIn(BaseModel):
    approve: bool
    price: float | None = None
    to_list: bool | None = None


class DarziCheckIn(BaseModel):
    items: list[dict] = []
    deliver_on: str = ""
    trial_on: str = ""
    customer: str = ""


def _darzi(fn, *a, **k):
    from .darzi import service as darzi
    try:
        return fn(*a, **k)
    except darzi.DarziError as e:
        raise HTTPException(400, str(e))


@app.get("/api/darzi/today", dependencies=[Depends(require_key)])
def darzi_today(date: str = "", tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.day, tenant, date)


@app.get("/api/darzi/orders", dependencies=[Depends(require_key)])
def darzi_orders(status: str = "open", customer: str = "", tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return {"orders": _darzi(darzi.orders, tenant, status, customer, 150)}


@app.post("/api/darzi/orders", dependencies=[Depends(require_key)])
def darzi_order_new(body: DarziOrderIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.new_order, tenant, body.items, body.customer, body.name, body.phone, body.deliver_on, body.trial_on,
                  body.advance, body.notes, body.photos, body.force, by="owner", conv=body.conversation_id)


@app.get("/api/darzi/orders/{order_id}", dependencies=[Depends(require_key)])
def darzi_order_get(order_id: str, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.get_order, tenant, order_id)


@app.patch("/api/darzi/orders/{order_id}", dependencies=[Depends(require_key)])
def darzi_order_patch(order_id: str, body: DarziOrderPatch, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.update_order, tenant, order_id, body.deliver_on, body.trial_on, body.notes, body.items, body.force)


@app.post("/api/darzi/orders/{order_id}/status", dependencies=[Depends(require_key)])
def darzi_order_status(order_id: str, body: DarziStatusIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.set_status, tenant, order_id, body.status, body.note, conv=body.conversation_id)


@app.post("/api/darzi/orders/{order_id}/pay", dependencies=[Depends(require_key)])
def darzi_order_pay(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.pay, tenant, order_id, body.amount, body.how)


@app.post("/api/darzi/orders/{order_id}/deliver", dependencies=[Depends(require_key)])
def darzi_order_deliver(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.deliver, tenant, order_id, body.amount, body.note, conv=body.conversation_id)


@app.post("/api/darzi/orders/{order_id}/cancel", dependencies=[Depends(require_key)])
def darzi_order_cancel(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.cancel, tenant, order_id, body.reason)


@app.get("/api/darzi/orders/{order_id}/slip", dependencies=[Depends(require_key)])
def darzi_order_slip(order_id: str, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    data = _darzi(darzi.slip_pdf, tenant, order_id)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="order-{order_id}.pdf"'})


@app.post("/api/darzi/orders/{order_id}/slip", dependencies=[Depends(require_key)])
def darzi_order_slip_file(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.slip_file, tenant, order_id, body.conversation_id)


@app.post("/api/darzi/orders/{order_id}/ready", dependencies=[Depends(require_key)])
def darzi_order_ready(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.ready_card, tenant, order_id, body.conversation_id)


@app.post("/api/darzi/orders/{order_id}/send_business", dependencies=[Depends(require_key)])
async def darzi_order_send_business(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    """Her tap: the 'ready' message through the official business WhatsApp (24 h window)."""
    from .darzi import service as darzi
    try:
        return await darzi.send_ready_business(tenant, order_id, body.text)
    except darzi.DarziError as e:
        raise HTTPException(400, str(e))


@app.post("/api/darzi/orders/{order_id}/told", dependencies=[Depends(require_key)])
def darzi_order_told(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.mark_told, tenant, order_id, body.how or "whatsapp")


@app.get("/api/darzi/customers", dependencies=[Depends(require_key)])
def darzi_customers(q: str = "", tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return {"customers": darzi.customers(tenant, q, 300)}


@app.post("/api/darzi/customers", dependencies=[Depends(require_key)])
def darzi_customer_new(body: DarziCustomerIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.customer_upsert, tenant, body.name, body.phone, body.notes)


@app.get("/api/darzi/customers/{customer_id}", dependencies=[Depends(require_key)])
def darzi_customer_get(customer_id: str, history: bool = False, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    out = _darzi(darzi.measures, tenant, customer_id, "", "", "", history)
    out["orders"] = darzi.orders(tenant, "all", customer_id, 30)
    return out


@app.post("/api/darzi/measures", dependencies=[Depends(require_key)])
def darzi_measure_new(body: DarziMeasureIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.save_measure, tenant, body.customer, body.garment, body.values, body.person, body.note, body.unit,
                  "app", body.name, body.phone)


@app.get("/api/darzi/quotes", dependencies=[Depends(require_key)])
def darzi_quotes(status: str = "pending", tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return {"quotes": darzi.quotes(tenant, status)}


@app.post("/api/darzi/quotes/{quote_id}", dependencies=[Depends(require_key)])
def darzi_quote_decide(quote_id: str, body: DarziQuoteIn, tenant: str = Depends(current_tenant)):
    """Her Haan / Mana on a price Hoola prepared (only from her tap)."""
    from .darzi import service as darzi
    return _darzi(darzi.decide_quote, tenant, quote_id, body.approve, body.price, body.to_list)


@app.get("/api/darzi/settings", dependencies=[Depends(require_key)])
def darzi_settings_get(tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return darzi.settings(tenant)


@app.put("/api/darzi/settings", dependencies=[Depends(require_key)])
def darzi_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    keys = ("enabled", "shop_name", "unit", "pieces_per_day", "closed_days", "rush_percent", "min_days", "prices", "rules",
            "remeasure_months", "ready_template", "morning_time")
    return _darzi(darzi.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.get("/api/darzi/garments", dependencies=[Depends(require_key)])
def darzi_garments():
    from .darzi import garments
    return {"garments": garments.listing()}


@app.post("/api/darzi/check", dependencies=[Depends(require_key)])
def darzi_check(body: DarziCheckIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.check, tenant, body.items, body.deliver_on, body.trial_on, body.customer)


# ---------------------------------------------------------------- v0.84 Galla + Chai Sahayak (chai stall coworker)
class GallaAlertsIn(BaseModel):
    items: list[dict] = []


class GallaCashIn(BaseModel):
    amount: float
    date: str = ""
    hour: int | None = None
    note: str = ""


class ChaiPlanIn(BaseModel):
    for_date: str = ""
    conversation_id: str = ""


class ChaiDecideIn(BaseModel):
    approve: bool
    conversation_id: str = ""


class ChaiStockIn(BaseModel):
    milk_l: float | None = None
    sugar_kg: float | None = None
    tea_kg: float | None = None


class ChaiFeedbackIn(BaseModel):
    for_date: str = ""
    milk_left_l: float | None = None
    ran_out_at: str = ""
    sugar_left_kg: float | None = None
    tea_left_kg: float | None = None
    cash: float | None = None
    bought_milk_l: float | None = None


def _galla(fn, *a, **k):
    from .chai import service as chai
    from .galla import service as galla
    try:
        return fn(*a, **k)
    except (galla.GallaError, chai.ChaiError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/galla/alerts", dependencies=[Depends(require_key)])
def galla_alerts(body: GallaAlertsIn, tenant: str = Depends(current_tenant)):
    """From her phone: 'money received' alerts of the payment apps she picked, already reduced to amount / time / app /
    payer's first name / last 4 of the reference (the full notification never leaves the phone)."""
    from .galla import service as galla
    return galla.ingest_alerts(tenant, body.items)


@app.get("/api/galla/today", dependencies=[Depends(require_key)])
def galla_today(date: str = "", tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return _galla(galla.day_summary, tenant, date)


@app.get("/api/galla/hours", dependencies=[Depends(require_key)])
def galla_hours(days: int = 28, tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return galla.best_hours(tenant, max(1, min(120, days)))


@app.get("/api/galla/recent", dependencies=[Depends(require_key)])
def galla_recent(tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return {"payments": galla.recent(tenant, 80)}


@app.post("/api/galla/cash", dependencies=[Depends(require_key)])
def galla_cash(body: GallaCashIn, tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return _galla(galla.add_cash, tenant, body.amount, body.date, body.hour, body.note)


@app.post("/api/galla/entries/{entry_id}/void", dependencies=[Depends(require_key)])
def galla_void(entry_id: str, tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return _galla(galla.void, tenant, entry_id)


@app.post("/api/galla/statement", dependencies=[Depends(require_key)])
async def galla_statement(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "Statement 10 MB se bada hai.")
    return _galla(galla.import_statement, tenant, file.filename or "statement.csv", data)


@app.get("/api/galla/settings", dependencies=[Depends(require_key)])
def galla_settings_get(tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return galla.settings(tenant)


@app.put("/api/galla/settings", dependencies=[Depends(require_key)])
def galla_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return _galla(galla.save_settings, tenant, body.get("apps"), body.get("open_hour"), body.get("close_hour"))


@app.get("/api/chai/settings", dependencies=[Depends(require_key)])
def chai_settings_get(tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    return chai.settings(tenant)


@app.put("/api/chai/settings", dependencies=[Depends(require_key)])
def chai_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    keys = ("enabled", "stall_name", "menu", "other_pct", "cash_pct", "safety_pct", "milk_packet_ml", "typical_cups",
            "suppliers", "rules", "plan_time", "milk_factor")
    return _galla(chai.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/chai/stock", dependencies=[Depends(require_key)])
def chai_stock(body: ChaiStockIn, tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    return _galla(chai.set_stock, tenant, body.milk_l, body.sugar_kg, body.tea_kg)


@app.post("/api/chai/plan", dependencies=[Depends(require_key)])
async def chai_plan_make(body: ChaiPlanIn, tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    weather = None
    try:
        from .life import weather_for
        weather = await weather_for(tenant)
    except Exception:
        weather = None
    return await asyncio.to_thread(_galla, chai.plan_tomorrow, tenant, body.for_date, weather, body.conversation_id)


@app.get("/api/chai/plan", dependencies=[Depends(require_key)])
def chai_plan_get(date: str = "", tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    return {"plan": _galla(chai.get_plan, tenant, date)}


@app.post("/api/chai/orders/{order_id}", dependencies=[Depends(require_key)])
def chai_order_decide(order_id: str, body: ChaiDecideIn, tenant: str = Depends(current_tenant)):
    """Her Haan / Mana on a stock order Hoola prepared (only from her tap)."""
    from .chai import service as chai
    return _galla(chai.decide_order, tenant, order_id, body.approve, body.conversation_id)


@app.post("/api/chai/feedback", dependencies=[Depends(require_key)])
def chai_feedback(body: ChaiFeedbackIn, tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    return _galla(chai.feedback, tenant, body.for_date, body.milk_left_l, body.ran_out_at, body.sugar_left_kg,
                  body.tea_left_kg, body.cash, body.bought_milk_l)
# ---------------------------------------------------------------- v0.85 Daftar Sahayak (office manager)
def _office(fn, *a, **k):
    from .office import service as office
    try:
        return fn(*a, **k)
    except office.OfficeError as e:
        raise HTTPException(400, str(e))


@app.get("/api/office", dependencies=[Depends(require_key)])
def office_all(tenant: str = Depends(current_tenant)):
    """Everything for the Daftar screen in one call."""
    from .office import service as office
    return {"today": office.day(tenant), "settings": office.settings(tenant), "items": office.items(tenant),
            "tickets": office.tickets(tenant, "all")[:60], "renewals": office.renewals(tenant, status="all"),
            "deadlines": office.deadlines(tenant, "all")[:80], "petty": office.petty(tenant), "bills": office.bills(tenant, False)[:60],
            "spends": office.spends(tenant, "all")[:40], "vendors": office.vendors(tenant), "starters": office.starters(tenant)}


@app.get("/api/office/today", dependencies=[Depends(require_key)])
def office_today(tenant: str = Depends(current_tenant)):
    from .office import service as office
    return office.day(tenant)


@app.put("/api/office/settings", dependencies=[Depends(require_key)])
def office_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    keys = ("enabled", "office_name", "morning_time", "note_day", "note_time", "windows", "lead_days", "safety_days",
            "month_budget", "team", "rules")
    return _office(office.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/office/items", dependencies=[Depends(require_key)])
def office_item(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.item_upsert, tenant, str(body.get("name") or ""), body.get("qty"), str(body.get("unit") or ""),
                   body.get("min_qty"), body.get("lead_days"), str(body.get("vendor") or ""), body.get("price"),
                   str(body.get("location") or ""), "owner")


@app.post("/api/office/items/{item_id}/use", dependencies=[Depends(require_key)])
def office_item_use(item_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.use, tenant, item_id, body.get("qty"), str(body.get("note") or ""), "owner")


@app.post("/api/office/items/{item_id}/restock", dependencies=[Depends(require_key)])
def office_item_restock(item_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.restock, tenant, item_id, body.get("qty"), body.get("price"), str(body.get("vendor") or ""), "owner")


@app.post("/api/office/reorder", dependencies=[Depends(require_key)])
def office_reorder(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.reorder, tenant, body.get("names") or None, str(body.get("conversation_id") or ""))


@app.post("/api/office/tickets", dependencies=[Depends(require_key)])
def office_ticket_new(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.ticket_new, tenant, str(body.get("title") or ""), str(body.get("asset") or ""),
                   str(body.get("category") or ""), str(body.get("priority") or ""), str(body.get("vendor") or ""),
                   str(body.get("assigned_to") or ""), body.get("photos") or [], "owner", str(body.get("conversation_id") or ""))


@app.patch("/api/office/tickets/{ticket_id}", dependencies=[Depends(require_key)])
def office_ticket_patch(ticket_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.ticket_update, tenant, ticket_id, str(body.get("status") or ""), str(body.get("note") or ""),
                   str(body.get("vendor") or ""), str(body.get("assigned_to") or ""), body.get("cost"), "owner",
                   str(body.get("conversation_id") or ""))


@app.post("/api/office/renewals", dependencies=[Depends(require_key)])
def office_renewal_new(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.renewal_add, tenant, str(body.get("name") or ""), str(body.get("due_on") or ""),
                   str(body.get("kind") or ""), body.get("every_months"), body.get("amount"), str(body.get("vendor") or ""),
                   str(body.get("notes") or ""), body.get("files") or [], str(body.get("notice_by") or ""))


@app.post("/api/office/renewals/{renewal_id}/done", dependencies=[Depends(require_key)])
def office_renewal_done(renewal_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.renewal_done, tenant, renewal_id, body.get("paid"), str(body.get("next_due") or ""),
                   str(body.get("note") or ""))


@app.post("/api/office/renewals/{renewal_id}/pay", dependencies=[Depends(require_key)])
def office_renewal_pay(renewal_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.renewal_pay, tenant, renewal_id, body.get("amount"), str(body.get("conversation_id") or ""))


@app.post("/api/office/deadlines", dependencies=[Depends(require_key)])
def office_deadline_new(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.deadline_add, tenant, str(body.get("title") or ""), str(body.get("due_on") or ""),
                   str(body.get("owner") or ""), str(body.get("note") or ""))


@app.post("/api/office/deadlines/{deadline_id}/done", dependencies=[Depends(require_key)])
def office_deadline_done(deadline_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.deadline_done, tenant, deadline_id, bool(body.get("dropped")))


@app.post("/api/office/nudge", dependencies=[Depends(require_key)])
def office_nudge(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.nudge, tenant, str(body.get("deadline") or ""), str(body.get("owner") or ""),
                   str(body.get("conversation_id") or ""))


@app.post("/api/office/petty", dependencies=[Depends(require_key)])
def office_petty(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.petty_add, tenant, body.get("amount"), str(body.get("what") or ""), str(body.get("kind") or "out"),
                   str(body.get("by") or ""), str(body.get("on") or ""), str(body.get("bill") or ""))


@app.post("/api/office/bills", dependencies=[Depends(require_key)])
def office_bill(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.bill_add, tenant, str(body.get("vendor") or ""), body.get("amount"), str(body.get("number") or ""),
                   str(body.get("bill_date") or ""), str(body.get("due_on") or ""), body.get("gst"), str(body.get("what") or ""),
                   str(body.get("file_id") or ""))


@app.post("/api/office/bills/{bill_id}/paid", dependencies=[Depends(require_key)])
def office_bill_paid(bill_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.bill_paid, tenant, bill_id, str(body.get("on") or ""))


@app.post("/api/office/vendors", dependencies=[Depends(require_key)])
def office_vendor(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.vendor_upsert, tenant, str(body.get("name") or ""), str(body.get("phone") or ""),
                   str(body.get("email") or ""), str(body.get("category") or ""), str(body.get("gstin") or ""),
                   str(body.get("notes") or ""), str(body.get("id") or ""), body.get("udyam"))


@app.post("/api/office/spends", dependencies=[Depends(require_key)])
def office_spend_new(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.spend_request, tenant, str(body.get("title") or ""), body.get("amount"), str(body.get("kind") or "other"),
                   str(body.get("vendor") or ""), str(body.get("why") or ""), str(body.get("conversation_id") or ""))


@app.post("/api/office/spends/{spend_id}", dependencies=[Depends(require_key)])
def office_spend_decide(spend_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her Haan / Mana on a spend card (only from her tap). Approve never pays: she pays in her own app."""
    from .office import service as office
    return _office(office.decide_spend, tenant, spend_id, bool(body.get("approve")), body.get("amount"), str(body.get("note") or ""))


@app.post("/api/office/note", dependencies=[Depends(require_key)])
def office_note(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.weekly_note, tenant, bool(body.get("file", True)), str(body.get("conversation_id") or ""))


# ---------------------------------------------------------------- v0.87 Lekhak Sahayak (typist + translator)
def _lekhak(fn, *a, **k):
    from .lekhak import service as lekhak
    try:
        return fn(*a, **k)
    except lekhak.LekhakError as e:
        raise HTTPException(400, str(e))


@app.get("/api/lekhak", dependencies=[Depends(require_key)])
def lekhak_all(q: str = "", tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return {"docs": lekhak.docs(tenant, q, 80), "contacts": lekhak.contacts(tenant), "settings": lekhak.settings(tenant),
            "kinds": lekhak.KINDS, "langs": lekhak.LANGS}


@app.get("/api/lekhak/docs/{doc_id}", dependencies=[Depends(require_key)])
def lekhak_doc(doc_id: str, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.get_doc, tenant, doc_id)


@app.post("/api/lekhak/write", dependencies=[Depends(require_key)])
async def lekhak_write(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.write_letter, tenant, str(body.get("dictation") or ""), str(body.get("kind") or ""),
                                   str(body.get("lang") or ""), str(body.get("to") or ""), body.get("to_lines"),
                                   str(body.get("subject") or ""), str(body.get("reference") or ""), body.get("enclosures"),
                                   str(body.get("file_id") or ""), "app", str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/translate", dependencies=[Depends(require_key)])
async def lekhak_translate(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.translate, tenant, str(body.get("text") or ""), str(body.get("to") or ""),
                                   str(body.get("src") or ""), str(body.get("file_id") or ""), str(body.get("doc") or ""),
                                   str(body.get("register") or "formal"), True, str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/grammar", dependencies=[Depends(require_key)])
async def lekhak_grammar(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.fix_grammar, tenant, str(body.get("text") or ""), str(body.get("lang") or ""),
                                   str(body.get("doc") or ""), str(body.get("file_id") or ""), str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/type", dependencies=[Depends(require_key)])
async def lekhak_type(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.type_text, tenant, str(body.get("text") or ""), str(body.get("file_id") or ""),
                                   str(body.get("lang") or ""), str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/krutidev", dependencies=[Depends(require_key)])
def lekhak_krutidev(body: dict):
    from .lekhak import service as lekhak
    return lekhak.krutidev(str(body.get("text") or ""), str(body.get("to") or "unicode"))


@app.post("/api/lekhak/docs/{doc_id}/revise", dependencies=[Depends(require_key)])
async def lekhak_revise(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.revise, tenant, doc_id, str(body.get("instruction") or ""),
                                   str(body.get("conversation_id") or ""))


@app.put("/api/lekhak/docs/{doc_id}", dependencies=[Depends(require_key)])
def lekhak_edit(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """She edited the text herself in the app."""
    from .lekhak import service as lekhak
    return _lekhak(lekhak.edit, tenant, doc_id, str(body.get("text") or ""), body.get("parts"), str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/docs/{doc_id}/files", dependencies=[Depends(require_key)])
async def lekhak_files(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.make_files, tenant, doc_id, str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/docs/{doc_id}/sign_request", dependencies=[Depends(require_key)])
def lekhak_sign_request(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.sign_request, tenant, doc_id, str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/docs/{doc_id}/sign", dependencies=[Depends(require_key)])
async def lekhak_sign(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on the sign card (only from the app): approve + mode paper | image, the card's hash."""
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.decide_sign, tenant, doc_id, bool(body.get("approve")),
                                   str(body.get("mode") or "paper"), str(body.get("conversation_id") or ""), str(body.get("hash") or ""))


@app.post("/api/lekhak/docs/{doc_id}/copy", dependencies=[Depends(require_key)])
def lekhak_copy(doc_id: str, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.copy_doc, tenant, doc_id)


@app.post("/api/lekhak/docs/{doc_id}/share", dependencies=[Depends(require_key)])
def lekhak_share(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.share_draft, tenant, doc_id, str(body.get("phone") or ""), str(body.get("email") or ""))


@app.post("/api/lekhak/contacts", dependencies=[Depends(require_key)])
def lekhak_contact(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.contact_save, tenant, str(body.get("name") or ""), body.get("lines"), str(body.get("lang") or ""),
                   str(body.get("email") or ""), str(body.get("phone") or ""))


@app.put("/api/lekhak/settings", dependencies=[Depends(require_key)])
def lekhak_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    keys = ("my_name", "my_lines", "my_phone", "place", "gender", "lang", "letterhead", "keep", "rules", "glossary", "digits", "sign_file")
    return _lekhak(lekhak.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.88 Mobile Dukaan Sahayak (recharge + repair shop)
class MShopJobIn(BaseModel):
    name: str = ""
    phone: str = ""
    brand: str = ""
    model: str = ""
    imei: str = ""
    problem: str = ""
    faults: list[str] = []
    accessories: list[str] = []
    condition: str = ""
    promised_on: str = ""
    estimate: float | None = None
    advance: float | None = None
    proof: str = ""
    technician: str = ""
    force: bool = False
    conversation_id: str = ""


class MShopActIn(BaseModel):
    status: str = ""
    note: str = ""
    name: str = ""
    price: float | None = None
    cost: float | None = None
    warranty_days: int | None = None
    labour: float | None = None
    approve: bool = False
    total: float | None = None
    amount: float | None = None
    how: str = ""
    promised_on: str = ""
    technician: str = ""
    imei: str = ""
    proof: str = ""
    estimate: float | None = None
    force: bool = False
    conversation_id: str = ""


class MShopRechargeIn(BaseModel):
    number: str
    amount: float
    operator: str = ""
    validity_days: int | None = None
    name: str = ""
    plan: str = ""
    via: str = ""
    date: str = ""


def _mshop(fn, *a, **k):
    from .mshop import service as mshop
    try:
        return fn(*a, **k)
    except mshop.MShopError as e:
        raise HTTPException(400, str(e))


@app.get("/api/mshop/today", dependencies=[Depends(require_key)])
def mshop_today(tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return mshop.day(tenant)


@app.get("/api/mshop/jobs", dependencies=[Depends(require_key)])
def mshop_jobs(status: str = "open", q: str = "", tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return {"jobs": mshop.jobs(tenant, status, q, 200)}


@app.post("/api/mshop/jobs", dependencies=[Depends(require_key)])
def mshop_job_new(body: MShopJobIn, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return _mshop(mshop.new_job, tenant, body.name, body.phone, body.brand, body.model, body.imei, body.problem, body.faults,
                  body.accessories, body.condition, body.promised_on, body.estimate, body.advance, body.proof, [],
                  body.technician, body.force, "owner", body.conversation_id)


@app.post("/api/mshop/check", dependencies=[Depends(require_key)])
def mshop_check(body: MShopJobIn, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return _mshop(mshop.check_job, tenant, body.problem, body.faults, body.brand, body.model, body.imei, body.phone,
                  body.promised_on, body.proof)


@app.get("/api/mshop/jobs/{job_id}", dependencies=[Depends(require_key)])
def mshop_job_get(job_id: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return _mshop(mshop.get_job, tenant, job_id)


@app.post("/api/mshop/jobs/{job_id}/photos", dependencies=[Depends(require_key)])
async def mshop_photo_add(job_id: str, file: UploadFile = File(...), kind: str = Form("in"), note: str = Form(""),
                          tenant: str = Depends(current_tenant)):
    """A photo of the phone (camera in the app): kept in the shop's own store as warranty proof."""
    from .mshop import service as mshop
    data = await file.read()
    return _mshop(mshop.add_photo, tenant, job_id, data, file.filename or "photo.jpg", kind, note)


@app.post("/api/mshop/jobs/{job_id}/{action}", dependencies=[Depends(require_key)])
def mshop_job_act(job_id: str, action: str, body: MShopActIn, tenant: str = Depends(current_tenant)):
    """status | part | bill | decide (her Haan on the bill, only from her tap) | customer_ok | pay | deliver | update | ready | slip"""
    from .mshop import service as mshop
    conv = body.conversation_id
    if action == "status":
        return _mshop(mshop.set_status, tenant, job_id, body.status, body.note, conv=conv)
    if action == "part":
        return _mshop(mshop.add_part, tenant, job_id, body.name, body.price, body.cost, body.warranty_days, body.labour)
    if action == "bill":
        return _mshop(mshop.prepare_bill, tenant, job_id, conv)
    if action == "decide":
        return _mshop(mshop.decide_bill, tenant, job_id, body.approve, body.total, conv)
    if action == "customer_ok":
        return _mshop(mshop.customer_agreed, tenant, job_id, body.estimate)
    if action == "pay":
        return _mshop(mshop.pay, tenant, job_id, body.amount, body.how)
    if action == "deliver":
        return _mshop(mshop.deliver, tenant, job_id, body.amount, body.note, conv=conv)
    if action == "update":
        return _mshop(mshop.update_job, tenant, job_id, body.promised_on, body.note, body.technician, body.imei, body.proof,
                      body.estimate, body.force)
    if action == "ready":
        return _mshop(mshop.ready_card, tenant, job_id, conv)
    if action == "estimate_message":
        return _mshop(mshop.estimate_message, tenant, job_id)
    if action == "slip":
        return _mshop(mshop.slip_file, tenant, job_id, conv)
    raise HTTPException(404, "Unknown action")


@app.get("/api/mshop/jobs/{job_id}/slip.pdf", dependencies=[Depends(require_key)])
def mshop_job_slip(job_id: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return Response(_mshop(mshop.slip_pdf, tenant, job_id), media_type="application/pdf")


@app.get("/api/mshop/photos/{photo_id}", dependencies=[Depends(require_key)])
def mshop_photo_get(photo_id: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    path, mime = _mshop(mshop.photo_file, tenant, photo_id)
    return FileResponse(path, media_type=mime)


@app.get("/api/mshop/warranty", dependencies=[Depends(require_key)])
def mshop_warranty(q: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return mshop.warranty(tenant, q)


@app.post("/api/mshop/recharges", dependencies=[Depends(require_key)])
def mshop_recharge_new(body: MShopRechargeIn, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return _mshop(mshop.add_recharge, tenant, body.number, body.amount, body.operator, body.validity_days, body.name,
                  body.plan, body.via, body.date)


@app.get("/api/mshop/recharges", dependencies=[Depends(require_key)])
def mshop_recharges(date: str = "", tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return {"day": _mshop(mshop.recharges_day, tenant, date), "recent": mshop.recent_recharges(tenant, 80),
            "due": mshop.due_recharges(tenant)}


@app.post("/api/mshop/recharges/{recharge_id}/{action}", dependencies=[Depends(require_key)])
def mshop_recharge_act(recharge_id: str, action: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    if action == "reminded":
        return _mshop(mshop.mark_reminded, tenant, recharge_id)
    if action == "void":
        return _mshop(mshop.void_recharge, tenant, recharge_id)
    raise HTTPException(404, "Unknown action")


@app.get("/api/mshop/settings", dependencies=[Depends(require_key)])
def mshop_settings_get(tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return mshop.settings(tenant)


@app.put("/api/mshop/settings", dependencies=[Depends(require_key)])
def mshop_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    keys = ("enabled", "shop_name", "gstin", "gst_on", "prices", "warranty", "fix_days", "jobs_per_day", "unclaimed_days",
            "commission", "remind_days", "terms", "ready_template", "rules", "morning_time")
    return _mshop(mshop.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.90 Phone Doctor
def _pdoc(fn, *a, **k):
    from .phonedoc import service as pdoc
    try:
        return fn(*a, **k)
    except pdoc.PhoneDocError as e:
        raise HTTPException(400, str(e))


@app.get("/api/phonedoc/issues", dependencies=[Depends(require_key)])
def phonedoc_issues():
    from .phonedoc import service as pdoc
    return {"issues": pdoc.issues()}


@app.post("/api/phonedoc/check", dependencies=[Depends(require_key)])
def phonedoc_check(body: dict, tenant: str = Depends(current_tenant)):
    """The Hoola app posts the phone's own state (settings, battery, storage, network; no personal content)."""
    from .phonedoc import service as pdoc
    return _pdoc(pdoc.save_snapshot, tenant, body.get("snapshot") if isinstance(body.get("snapshot"), dict) else body)


@app.get("/api/phonedoc/cases", dependencies=[Depends(require_key)])
def phonedoc_cases(status: str = "", tenant: str = Depends(current_tenant)):
    from .phonedoc import service as pdoc
    return {"cases": pdoc.cases(tenant, status, 40)}


@app.post("/api/phonedoc/cases", dependencies=[Depends(require_key)])
def phonedoc_start(body: dict, tenant: str = Depends(current_tenant)):
    from .phonedoc import service as pdoc
    snap = body.get("snapshot") if isinstance(body.get("snapshot"), dict) else None
    if snap and not str(body.get("for_whom") or "").strip():
        _pdoc(pdoc.save_snapshot, tenant, snap)
    return _pdoc(pdoc.start, tenant, str(body.get("text") or ""), str(body.get("issue") or ""), str(body.get("for_whom") or ""),
                 str(body.get("device") or ""), str(body.get("app_package") or ""), snap)


@app.get("/api/phonedoc/cases/{case_id}", dependencies=[Depends(require_key)])
def phonedoc_case(case_id: str, tenant: str = Depends(current_tenant)):
    from .phonedoc import service as pdoc
    return _pdoc(pdoc.get_case, tenant, case_id)


@app.post("/api/phonedoc/cases/{case_id}/{action}", dependencies=[Depends(require_key)])
def phonedoc_case_action(case_id: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    from .phonedoc import service as pdoc
    if action == "step":
        return _pdoc(pdoc.step, tenant, case_id, str(body.get("step_id") or ""), str(body.get("result") or ""), str(body.get("note") or ""))
    if action == "recheck":
        snap = body.get("snapshot") if isinstance(body.get("snapshot"), dict) else None
        if snap:
            _pdoc(pdoc.save_snapshot, tenant, snap)
        return _pdoc(pdoc.recheck, tenant, case_id, snap)
    if action == "escalate":
        return _pdoc(pdoc.escalate, tenant, case_id, str(body.get("kind") or ""), bool(body.get("make_job")), str(body.get("phone") or ""))
    if action == "close":
        return _pdoc(pdoc.close, tenant, case_id)
    raise HTTPException(404, "step | recheck | escalate | close")


# ---------------------------------------------------------------- v0.98 Bima Sahayak (insurance agent)
def _ins(fn, *a, **k):
    from .insure import service as ins
    try:
        return fn(*a, **k)
    except (ins.InsError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/insurance/summary", dependencies=[Depends(require_key)])
def insurance_summary(days: int = 15, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return {"book": ins.book(tenant), "renewals": ins.renewals(tenant, days), "claims": ins.claims(tenant),
            "birthdays": ins.birthdays(tenant, 7)["birthdays"], "settings": ins.settings(tenant)}


@app.get("/api/insurance/clients", dependencies=[Depends(require_key)])
def insurance_clients(tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return {"clients": ins.clients(tenant)}


@app.post("/api/insurance/clients", dependencies=[Depends(require_key)])
def insurance_client_save(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _ins(ins.save_client, tenant, g("name"), g("client"), g("phone"), g("dob"), g("gender"), g("city"), body.get("metro"),
                body.get("income"), body.get("family"), body.get("liabilities"), body.get("goals"), body.get("savings"),
                body.get("whatsapp_ok"), g("notes"))


@app.get("/api/insurance/clients/{cid}/needs", dependencies=[Depends(require_key)])
def insurance_needs(cid: str, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.needs, tenant, cid)


@app.get("/api/insurance/policies", dependencies=[Depends(require_key)])
def insurance_policies(client: str = "", state: str = "", tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return {"policies": _ins(ins.policies, tenant, client, state)}


@app.post("/api/insurance/policies", dependencies=[Depends(require_key)])
def insurance_policy_save(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _ins(ins.save_policy, tenant, g("client"), g("insurer"), g("plan"), g("type"), g("number"), g("start"), g("mode"),
                body.get("premium"), body.get("cover"), g("next_due"), nominee=g("nominee"), commission_pct=body.get("commission_pct"),
                group=body.get("group"), members=body.get("members"), pay_link=g("pay_link"), policy=g("policy"), status=g("status"))


@app.post("/api/insurance/policies/{pid}/paid", dependencies=[Depends(require_key)])
def insurance_paid(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.premium_paid, tenant, pid, str(body.get("paid_on") or ""))


@app.post("/api/insurance/policies/{pid}/reminded", dependencies=[Depends(require_key)])
def insurance_reminded(pid: str, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.mark_reminded, tenant, pid)


@app.post("/api/insurance/import", dependencies=[Depends(require_key)])
async def insurance_import(file: UploadFile = File(...), insurer: str = Form(""), tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    data = await file.read()
    return _ins(ins.import_policies, tenant, "", data, file.filename or "renewals.csv", insurer)


@app.get("/api/insurance/reminders", dependencies=[Depends(require_key)])
def insurance_reminders(days: int = 15, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.reminder_drafts, tenant, days)


@app.post("/api/insurance/advice/{aid}", dependencies=[Depends(require_key)])
def insurance_advice(aid: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her Haan (only from her tap) turns the recommendation into a client message draft she sends."""
    from .insure import service as ins
    return _ins(ins.approve_advice, tenant, aid, bool(body.get("approve", True)))


@app.post("/api/insurance/claims", dependencies=[Depends(require_key)])
def insurance_claim_new(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.start_claim, tenant, str(body.get("policy") or ""), str(body.get("kind") or "other"), str(body.get("event_on") or ""),
                body.get("amount"))


@app.post("/api/insurance/claims/{cid}", dependencies=[Depends(require_key)])
def insurance_claim_update(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.update_claim, tenant, cid, body.get("have"), str(body.get("status") or ""), str(body.get("insurer_ref") or ""),
                str(body.get("filed_on") or ""), body.get("settled_amount"), str(body.get("note") or ""))


@app.post("/api/insurance/book_file", dependencies=[Depends(require_key)])
def insurance_book_file(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.book_file, tenant, str(body.get("conversation_id") or ""))


@app.post("/api/insurance/settings", dependencies=[Depends(require_key)])
def insurance_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    keys = ("agent_name", "agent_code", "remind_days", "morning_time", "enabled")
    return _ins(ins.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.96 Auditor's Assistant
def _aud(fn, *a, **k):
    from .audit import service as aud
    try:
        return fn(*a, **k)
    except (aud.AuditError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/audit/engagements", dependencies=[Depends(require_key)])
def audit_engagements(tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return {"engagements": aud.engagements(tenant)}


@app.post("/api/audit/engagements", dependencies=[Depends(require_key)])
def audit_engagement_new(body: dict, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.new_engagement, tenant, str(body.get("client") or ""), str(body.get("kind") or "statutory"), str(body.get("fy") or ""),
                str(body.get("entity") or "firm"), body.get("approval_limit"))


@app.get("/api/audit/engagements/{eid}", dependencies=[Depends(require_key)])
def audit_engagement_get(eid: str, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.get, tenant, eid)


@app.post("/api/audit/engagements/{eid}/upload/{what}", dependencies=[Depends(require_key)])
async def audit_upload(eid: str, what: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """what = tb | tb_prev | daybook"""
    from .audit import service as aud
    data = await file.read()
    if what in ("tb", "tb_prev"):
        return _aud(aud.import_tb, tenant, eid, "", data, file.filename or "tb.xlsx", what == "tb_prev")
    if what == "daybook":
        return _aud(aud.import_daybook, tenant, eid, "", data, file.filename or "daybook.xlsx")
    raise HTTPException(404, "tb | tb_prev | daybook")


@app.get("/api/audit/engagements/{eid}/findings", dependencies=[Depends(require_key)])
def audit_findings(eid: str, status: str = "", tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return {"findings": _aud(aud.findings, tenant, eid, status)}


@app.post("/api/audit/engagements/{eid}/{action}", dependencies=[Depends(require_key)])
def audit_act(eid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """run | materiality | facts | sample | confirmations | approve_confirmations (her Haan, only from her tap) | queries |
    asked | rep_letter | workpapers | letters | samples"""
    from .audit import service as aud
    conv = str(body.get("conversation_id") or "")
    if action == "run":
        return _aud(aud.run_tests, tenant, eid, conv)
    if action == "materiality":
        return _aud(aud.plan_materiality, tenant, eid, str(body.get("benchmark") or ""), body.get("pct"), str(body.get("risk") or "normal"))
    if action == "facts":
        keys = ("turnover", "cash_receipts_pct", "cash_payments_pct", "profession", "paid_up", "holding_or_sub", "status", "approval_limit")
        return _aud(aud.set_facts, tenant, eid, **{k: body[k] for k in keys if k in body})
    if action == "sample":
        return _aud(aud.make_sample, tenant, eid, str(body.get("population") or ""), str(body.get("method") or "mus"),
                    int(body.get("size") or 25), int(body.get("confidence") or 95))
    if action == "samples":
        return {"samples": _aud(aud.samples, tenant, eid)}
    if action == "confirmations":
        return _aud(aud.make_confirmations, tenant, eid, int(body.get("top") or 10), body.get("min_amount"))
    if action == "letters":
        return _aud(aud.confirmation_letters, tenant, eid)
    if action == "approve_confirmations":
        return _aud(aud.approve_confirmations, tenant, eid, bool(body.get("approve", True)))
    if action == "queries":
        return _aud(aud.query_list, tenant, eid)
    if action == "asked":
        return _aud(aud.mark_asked, tenant, eid)
    if action == "rep_letter":
        return _aud(aud.rep_letter, tenant, eid)
    if action == "workpapers":
        return _aud(aud.workpapers, tenant, eid, conv)
    raise HTTPException(404, "unknown action")


@app.post("/api/audit/findings/{fid}", dependencies=[Depends(require_key)])
def audit_finding_close(fid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.close_finding, tenant, fid, str(body.get("status") or ""), str(body.get("note") or ""), bool(body.get("remember")))


@app.post("/api/audit/samples/{sid}", dependencies=[Depends(require_key)])
def audit_sample_result(sid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.sample_result, tenant, sid, str(body.get("status") or ""), str(body.get("note") or ""))


@app.post("/api/audit/confirms/{cid}", dependencies=[Depends(require_key)])
def audit_confirm_reply(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.confirmation_reply, tenant, cid, body.get("amount"), str(body.get("note") or ""))


# ---------------------------------------------------------------- v0.95 Financial Analyst
def _fin(fn, *a, **k):
    from .analyst import service as fin
    try:
        return fn(*a, **k)
    except (fin.FinError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/finance/books", dependencies=[Depends(require_key)])
async def finance_books(file: UploadFile = File(...), label: str = Form(""), start: str = Form(...), end: str = Form(...),
                        tenant: str = Depends(current_tenant)):
    """Tally trial balance / P&L / balance sheet export -> statements, ratios, insights."""
    from .analyst import service as fin
    data = await file.read()
    return _fin(fin.import_books, tenant, label, start, end, "", data, file.filename or "tb.xlsx")


@app.post("/api/finance/bank", dependencies=[Depends(require_key)])
async def finance_bank(file: UploadFile = File(...), account: str = Form(""), tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    data = await file.read()
    return _fin(fin.import_bank, tenant, "", data, file.filename or "statement.csv", account)


@app.get("/api/finance/analysis", dependencies=[Depends(require_key)])
def finance_analysis(snapshot: str = "", tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.analyse, tenant, snapshot)


@app.get("/api/finance/periods", dependencies=[Depends(require_key)])
def finance_periods(tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return {"periods": fin.snapshots(tenant)}


@app.get("/api/finance/cash", dependencies=[Depends(require_key)])
def finance_cash(tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.cash, tenant)


@app.get("/api/finance/aging", dependencies=[Depends(require_key)])
def finance_aging(kind: str = "receivable", tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.aging, tenant, "payable" if kind == "payable" else "receivable")


@app.post("/api/finance/items", dependencies=[Depends(require_key)])
def finance_item_add(body: dict, tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.add_item, tenant, str(body.get("kind") or "receivable"), str(body.get("party") or ""), body.get("amount"),
                str(body.get("bill") or ""), str(body.get("bill_date") or ""), body.get("credit_days"), str(body.get("phone") or ""),
                bool(body.get("msme")), body.get("agreed_days"))


@app.post("/api/finance/loan_check", dependencies=[Depends(require_key)])
def finance_loan_check(body: dict, tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.loan_check, tenant, body.get("amount"), body.get("rate") or 10, float(body.get("years") or 5),
                body.get("projected_turnover"), str(body.get("snapshot") or ""))


@app.post("/api/finance/act/{action}", dependencies=[Depends(require_key)])
def finance_act(action: str, body: dict, tenant: str = Depends(current_tenant)):
    """report | share (her Haan, only from her tap) | reminders | advance_tax"""
    from .analyst import service as fin
    if action == "report":
        return _fin(fin.report, tenant, str(body.get("snapshot") or ""), str(body.get("conversation_id") or ""))
    if action == "share":
        return _fin(fin.approve_share, tenant, str(body.get("snapshot") or ""), bool(body.get("approve")), str(body.get("to") or ""))
    if action == "reminders":
        return _fin(fin.reminder_drafts, tenant)
    if action == "advance_tax":
        return _fin(fin.advance_tax, tenant, body.get("profit"), str(body.get("snapshot") or ""))
    raise HTTPException(404, "report | share | reminders | advance_tax")


@app.get("/api/finance/settings", dependencies=[Depends(require_key)])
def finance_settings_get(tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return fin.settings(tenant)


@app.put("/api/finance/settings", dependencies=[Depends(require_key)])
def finance_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    keys = ("business", "entity", "budget", "tax_paid", "morning_time", "enabled")
    return _fin(fin.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.94 Payroll Officer
def _pay(fn, *a, **k):
    from .payroll import service as pay
    try:
        return fn(*a, **k)
    except (pay.PayError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/payroll/today", dependencies=[Depends(require_key)])
def payroll_today(tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return pay.calendar(tenant)


@app.get("/api/payroll/employees", dependencies=[Depends(require_key)])
def payroll_employees(all: bool = False, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return {"employees": pay.employees(tenant, not all)}


@app.post("/api/payroll/employees", dependencies=[Depends(require_key)])
def payroll_employee_save(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    keys = ("phone", "gender", "dob", "doj", "designation", "pay", "gross", "uan", "esic_ip", "pan", "account", "ifsc", "regime",
            "declared", "prev_income", "prev_tds", "pf_member", "eps_member", "pf_on_full", "fixed_term", "alias")
    return _pay(pay.save_employee, tenant, str(body.get("name") or ""), str(body.get("employee") or ""), **{k: body[k] for k in keys if k in body})


@app.post("/api/payroll/attendance", dependencies=[Depends(require_key)])
def payroll_attendance(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.set_attendance, tenant, str(body.get("period") or ""), body.get("entries") or [])


@app.post("/api/payroll/attendance/import", dependencies=[Depends(require_key)])
async def payroll_attendance_import(file: UploadFile = File(...), period: str = Form(...), tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    data = await file.read()
    return _pay(pay.import_attendance, tenant, period, data, file.filename or "attendance.csv")


@app.post("/api/payroll/advances", dependencies=[Depends(require_key)])
def payroll_advance(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.add_advance, tenant, str(body.get("employee") or ""), body.get("amount"), body.get("emi"), str(body.get("given_on") or ""),
                str(body.get("note") or ""))


@app.get("/api/payroll/runs", dependencies=[Depends(require_key)])
def payroll_runs(tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return {"runs": pay.runs(tenant)}


@app.post("/api/payroll/runs", dependencies=[Depends(require_key)])
def payroll_run_make(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.prepare_run, tenant, str(body.get("period") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/payroll/runs/{run_id}", dependencies=[Depends(require_key)])
def payroll_run_get(run_id: str, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.get_run, tenant, run_id)


@app.post("/api/payroll/runs/{run_id}/{action}", dependencies=[Depends(require_key)])
def payroll_run_act(run_id: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """decide (her Haan, only from her tap) | files | paid (after she paid) | drafts"""
    from .payroll import service as pay
    conv = str(body.get("conversation_id") or "")
    if action == "decide":
        return _pay(pay.decide, tenant, run_id, bool(body.get("approve")), str(body.get("note") or ""), conv)
    if action == "files":
        return _pay(pay.files, tenant, run_id, conv)
    if action == "paid":
        return _pay(pay.mark_paid, tenant, run_id, str(body.get("paid_on") or ""), "owner", conv)
    if action == "drafts":
        return _pay(pay.payslip_drafts, tenant, run_id)
    raise HTTPException(404, "decide | files | paid | drafts")


@app.post("/api/payroll/leaving", dependencies=[Depends(require_key)])
def payroll_leaving(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.full_and_final, tenant, str(body.get("employee") or ""), str(body.get("last_day") or ""), body.get("leave_days") or 0,
                body.get("notice_recovery") or 0, body.get("other") or 0, bool(body.get("death_or_disability")),
                str(body.get("conversation_id") or ""))


@app.get("/api/payroll/settings", dependencies=[Depends(require_key)])
def payroll_settings_get(tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return pay.settings(tenant)


@app.put("/api/payroll/settings", dependencies=[Depends(require_key)])
def payroll_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    keys = ("enabled", "company", "state", "pf_on", "pf_code", "esi_on", "esi_code", "tan", "min_wage", "days_basis", "pay_account",
            "pay_ifsc", "morning_time")
    return _pay(pay.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.93 GST Sahayak
def _gst(fn, *a, **k):
    from .gstp import service as gstp
    try:
        return fn(*a, **k)
    except (gstp.GstError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/gst/today", dependencies=[Depends(require_key)])
def gst_today(tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return gstp.calendar(tenant)


@app.get("/api/gst/clients", dependencies=[Depends(require_key)])
def gst_clients(tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return {"clients": gstp.clients(tenant)}


@app.post("/api/gst/clients", dependencies=[Depends(require_key)])
def gst_client_save(body: dict, tenant: str = Depends(current_tenant)):
    """Add / update a client. A portal password is never accepted or stored."""
    from .gstp import service as gstp
    if any(k in body for k in ("password", "portal_password", "otp")):
        raise HTTPException(400, "Portal ka password / OTP Hoola nahi rakhta.")
    return _gst(gstp.add_client, tenant, str(body.get("name") or ""), str(body.get("gstin") or ""), str(body.get("scheme") or ""),
                body.get("aato"), str(body.get("portal_user") or ""), str(body.get("login_as") or ""), str(body.get("contact_name") or ""),
                str(body.get("contact_phone") or ""), body.get("fee"), str(body.get("notes") or ""), body.get("einvoice"),
                str(body.get("client") or ""))


@app.get("/api/gst/bills", dependencies=[Depends(require_key)])
def gst_bills(client: str, period: str = "", direction: str = "", tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return {"bills": _gst(gstp.docs, tenant, client, period, direction)}


@app.post("/api/gst/bills", dependencies=[Depends(require_key)])
def gst_bill_add(body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    line = {k: body.get(k) for k in ("txval", "rate", "hsn", "desc", "qty", "uqc", "igst", "cgst", "sgst", "cess")}
    return _gst(gstp.add_doc, tenant, str(body.get("client") or ""), str(body.get("direction") or "out"), str(body.get("number") or ""),
                body.get("date"), str(body.get("party_gstin") or ""), str(body.get("party_name") or ""), str(body.get("pos") or ""),
                body.get("items"), str(body.get("kind") or "inv"), bool(body.get("rcm")), str(body.get("irn") or ""),
                str(body.get("category") or ""), str(body.get("paid_on") or ""), body.get("value"), "app", bool(body.get("replace")), **line)


@app.delete("/api/gst/bills/{bill_id}", dependencies=[Depends(require_key)])
def gst_bill_delete(bill_id: str, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return _gst(gstp.delete_doc, tenant, bill_id)


@app.post("/api/gst/import", dependencies=[Depends(require_key)])
async def gst_import(file: UploadFile = File(...), client: str = Form(...), direction: str = Form("out"), period: str = Form(""),
                     tenant: str = Depends(current_tenant)):
    """A sales / purchase register (Tally / Vyapar / Excel / CSV)."""
    from .gstp import service as gstp
    data = await file.read()
    return _gst(gstp.import_register, tenant, client, direction, "", data, file.filename or "register.csv", period)


@app.post("/api/gst/2b", dependencies=[Depends(require_key)])
async def gst_2b(file: UploadFile = File(...), client: str = Form(...), period: str = Form(...), tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    data = await file.read()
    return _gst(gstp.import_2b, tenant, client, period, "", data, file.filename or "gstr2b.json")


@app.get("/api/gst/reconcile", dependencies=[Depends(require_key)])
def gst_reconcile(client: str, period: str, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return _gst(gstp.reconcile, tenant, client, period)


@app.post("/api/gst/ims", dependencies=[Depends(require_key)])
def gst_ims(body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    if body.get("apply"):
        return _gst(gstp.ims_apply, tenant, str(body.get("client") or ""), str(body.get("period") or ""), str(body.get("conversation_id") or ""))
    return _gst(gstp.ims_decide, tenant, str(body.get("client") or ""), str(body.get("period") or ""), body.get("decisions") or {})


@app.get("/api/gst/returns", dependencies=[Depends(require_key)])
def gst_returns(client: str = "", period: str = "", status: str = "", tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return {"returns": _gst(gstp.returns, tenant, client, period, status)}


@app.post("/api/gst/returns", dependencies=[Depends(require_key)])
def gst_prepare(body: dict, tenant: str = Depends(current_tenant)):
    """Prepare gstr1 | gstr3b | cmp08 for a client + period."""
    from .gstp import service as gstp
    kind, c, p, conv = str(body.get("kind") or "gstr1"), str(body.get("client") or ""), str(body.get("period") or ""), str(body.get("conversation_id") or "")
    if kind == "gstr1":
        return _gst(gstp.prepare_gstr1, tenant, c, p, conv)
    if kind == "gstr3b":
        return _gst(gstp.prepare_gstr3b, tenant, c, p, body.get("other_reversal"), conv)
    if kind == "cmp08":
        return _gst(gstp.prepare_cmp08, tenant, c, p, body.get("turnover"), conv)
    raise HTTPException(400, "kind: gstr1 | gstr3b | cmp08")


@app.get("/api/gst/returns/{return_id}", dependencies=[Depends(require_key)])
def gst_return(return_id: str, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return _gst(gstp.get_return, tenant, return_id)


@app.get("/api/gst/returns/{return_id}/gstr1.json", dependencies=[Depends(require_key)])
def gst_return_json(return_id: str, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    from .db import session as _sess
    with _sess() as s:
        r = s.get(gstp.GstReturn, return_id)
        if not r or r.tenant_id != tenant or not r.portal_json:
            raise HTTPException(404, "JSON nahi hai")
        return Response(r.portal_json, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="GSTR1_{r.period}.json"'})


@app.post("/api/gst/returns/{return_id}/{action}", dependencies=[Depends(require_key)])
def gst_return_act(return_id: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """decide (her Haan, only from her tap) | file | filed | json | tax_message"""
    from .gstp import service as gstp
    conv = str(body.get("conversation_id") or "")
    if action == "decide":
        return _gst(gstp.decide, tenant, return_id, bool(body.get("approve")), str(body.get("note") or ""), conv)
    if action == "file":
        return _gst(gstp.file_return, tenant, return_id, conv)
    if action == "filed":
        return _gst(gstp.mark_filed, tenant, return_id, str(body.get("arn") or ""), str(body.get("filed_on") or ""), "owner", conv)
    if action == "json":
        return _gst(gstp.return_file, tenant, return_id, conv)
    if action == "tax_message":
        return _gst(gstp.tax_message_draft, tenant, return_id)
    raise HTTPException(404, "decide | file | filed | json | tax_message")


@app.post("/api/gst/drafts", dependencies=[Depends(require_key)])
def gst_drafts(body: dict, tenant: str = Depends(current_tenant)):
    """ask_bills (to the client) | suppliers (missing in 2B)"""
    from .gstp import service as gstp
    if str(body.get("kind")) == "suppliers":
        return _gst(gstp.supplier_drafts, tenant, str(body.get("client") or ""), str(body.get("period") or ""))
    return _gst(gstp.client_request_draft, tenant, str(body.get("client") or ""), str(body.get("period") or ""))


@app.get("/api/gst/notices", dependencies=[Depends(require_key)])
def gst_notices(status: str = "open", tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return {"notices": gstp.notices(tenant, status)}


@app.post("/api/gst/notices", dependencies=[Depends(require_key)])
def gst_notice_add(body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return _gst(gstp.add_notice, tenant, str(body.get("client") or ""), str(body.get("form") or ""), str(body.get("issued_on") or ""),
                str(body.get("ref") or ""), str(body.get("text") or ""), body.get("amount"), str(body.get("due_on") or ""))


@app.post("/api/gst/notices/{notice_id}/{action}", dependencies=[Depends(require_key)])
def gst_notice_act(notice_id: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    if action == "draft":
        return _gst(gstp.notice_draft, tenant, notice_id)
    if action == "status":
        return _gst(gstp.notice_status, tenant, notice_id, str(body.get("status") or ""))
    raise HTTPException(404, "draft | status")


@app.get("/api/gst/settings", dependencies=[Depends(require_key)])
def gst_settings_get(tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return gstp.settings(tenant)


@app.put("/api/gst/settings", dependencies=[Depends(require_key)])
def gst_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    keys = ("enabled", "practitioner", "enrolment", "morning_time", "remind_days")
    return _gst(gstp.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.get("/api/agent/tasks", dependencies=[Depends(require_key)])
def agent_tasks(limit: int = 50, tenant: str = Depends(current_tenant)):
    """v0.78 Kaam ka hisaab: every task with its outcome, steps, failures, fixes used, and what was left."""
    from .agent import pakka
    return pakka.runs(tenant, limit)


@app.get("/api/agent/lessons", dependencies=[Depends(require_key)])
def agent_lessons(tenant: str = Depends(current_tenant)):
    """v0.78 Seekhe hue hal: failure -> what worked, learned from her own tasks."""
    from .agent import pakka
    return {"lessons": pakka.listing(tenant)}


@app.delete("/api/agent/lessons/{lid}", dependencies=[Depends(require_key)])
def agent_lesson_delete(lid: str, tenant: str = Depends(current_tenant)):
    from .agent import pakka
    if not pakka.forget(tenant, lid):
        raise HTTPException(404, "Not found")
    return {"ok": True}


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


class BtResultIn(BaseModel):
    ok: bool
    result: dict = Field(default_factory=dict)
    error: str = ""


@app.post("/api/bt/requests/{rid}/result", dependencies=[Depends(require_key)])
def bt_result(rid: str, body: BtResultIn, tenant: str = Depends(current_tenant)):
    from .bt import service as bt
    try:
        return bt.report(tenant, rid, body.ok, body.result, body.error)
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.get("/api/bt/requests/{rid}", dependencies=[Depends(require_key)])
def bt_get(rid: str, tenant: str = Depends(current_tenant)):
    from .bt import service as bt
    try:
        return bt.get(tenant, rid)
    except LookupError as e:
        raise HTTPException(404, str(e))


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


# Home devices ("Ghar"): speaker / TV / AC on the phone + SmartThings, LG ThinQ, Home Connect
from .bazar.api import devices as bz_devices  # noqa: E402
app.include_router(bz_devices.router, dependencies=[Depends(require_key)])
app.include_router(bz_devices.public)


@app.get("/api/bazar/catalog", dependencies=[Depends(require_key)])
def bazar_catalog(tenant: str = Depends(current_tenant)):
    return _bz(bazar.catalog, tenant)


@app.get("/api/bazar/find", dependencies=[Depends(require_key)])
def bazar_find_api(q: str = "", category: str = "", tenant: str = Depends(current_tenant)):
    return _bz(bazar.find, tenant, q, category)


class BazarDecision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    proof: dict | None = None      # v0.97 fingerprint signature from her phone (approvekey)


def _fingerprint(tenant: str, kind: str, target: str, proof: dict | None) -> None:
    """v0.97 A money card needs HER phone's fingerprint signature once a phone is set up (428 = ask the phone)."""
    from . import approvekey as ak
    try:
        if ak.needed(tenant, kind, target):
            ak.verify(tenant, kind, target, proof)
    except ak.ApproveError as e:
        code = str(e)
        if code in ("fingerprint_needed", "fingerprint_invalid"):
            raise HTTPException(428, code)
        raise HTTPException(400, code)


class FormAnswer(BaseModel):
    values: dict = Field(default_factory=dict)


@app.get("/api/forms/{form_id}", dependencies=[Depends(require_key)])
def form_get(form_id: str, tenant: str = Depends(current_tenant)):
    from . import askform
    try:
        return askform.get(tenant, form_id)
    except askform.FormError as e:
        raise HTTPException(404, str(e))


def _form_reply(tenant: str, conv: str, agent_text: str, shown: str, background: BackgroundTasks) -> str:
    """Her answers continue the job: inside a live call they go to the call; otherwise as her next chat message."""
    if not conv:
        return "none"
    try:
        from .voice import inject
        if inject(conv, agent_text):
            bus.publish(conv, "message", {"role": "user", "text": shown, "source": "form"})
            return "call"
    except Exception:
        log.exception("form -> call failed")
    bus.publish(conv, "message", {"role": "user", "text": shown, "source": "form"})
    background.add_task(run_turn, conv, shown, tenant, False, context=agent_text)
    return "chat"


@app.post("/api/forms/{form_id}/answer", dependencies=[Depends(require_key)])
def form_answer(form_id: str, body: FormAnswer, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    from . import askform
    try:
        v, agent_text, shown = askform.answer(tenant, form_id, body.values)
    except askform.FormError as e:
        raise HTTPException(400, str(e))
    with session() as s:
        from .askform import AskForm
        conv = s.get(AskForm, form_id).conversation_id
    return {**v, "went_to": _form_reply(tenant, conv, agent_text, shown, background)}


@app.post("/api/forms/{form_id}/cancel", dependencies=[Depends(require_key)])
def form_cancel(form_id: str, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    from . import askform
    try:
        v, agent_text = askform.cancel(tenant, form_id)
    except askform.FormError as e:
        raise HTTPException(404, str(e))
    if agent_text:
        with session() as s:
            from .askform import AskForm
            conv = s.get(AskForm, form_id).conversation_id
        _form_reply(tenant, conv, agent_text, "Form band kiya", background)
    return v


class ApproveKeyAdd(BaseModel):
    device_id: str = Field(min_length=4, max_length=80)
    public_key: str = Field(min_length=40, max_length=2000)
    label: str = Field(default="", max_length=120)
    strongbox: bool = False
    proof: dict | None = None


class ApproveProof(BaseModel):
    proof: dict | None = None


class ApproveChallengeReq(BaseModel):
    kind: str = Field(pattern="^(bazar|studio|remove|endorse)$")
    target: str = Field(min_length=1, max_length=2200)


@app.get("/api/approvekey", dependencies=[Depends(require_key)])
def approvekey_get(tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    return ak.devices(tenant)


@app.post("/api/approvekey/devices", dependencies=[Depends(require_key)])
def approvekey_add(body: ApproveKeyAdd, tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    try:
        return ak.register(tenant, body.device_id, body.public_key, body.label, body.strongbox, body.proof)
    except ak.ApproveError as e:
        raise HTTPException(400, str(e))


@app.post("/api/approvekey/devices/{device_id}/remove", dependencies=[Depends(require_key)])
def approvekey_remove(device_id: str, body: ApproveProof, tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    try:
        return ak.remove(tenant, device_id, body.proof)
    except ak.ApproveError as e:
        raise HTTPException(400, str(e))


@app.post("/api/approvekey/devices/{device_id}/cancel", dependencies=[Depends(require_key)])
def approvekey_cancel(device_id: str, tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    try:
        return ak.cancel(tenant, device_id)
    except ak.ApproveError as e:
        raise HTTPException(400, str(e))


@app.post("/api/approvekey/challenge", dependencies=[Depends(require_key)])
def approvekey_challenge(body: ApproveChallengeReq, tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    try:
        return ak.challenge(tenant, body.kind, body.target)
    except ak.ApproveError as e:
        raise HTTPException(400, str(e))


@app.get("/api/bazar/approvals/pending", dependencies=[Depends(require_key)])
def bazar_pending(tenant: str = Depends(current_tenant)):
    return {"approvals": bazar.pending_approvals(tenant)}


@app.post("/api/bazar/approvals/{approval_id}", dependencies=[Depends(require_key)])
async def bazar_decide(approval_id: str, body: BazarDecision, tenant: str = Depends(current_tenant)):
    if body.decision == "approve":
        await asyncio.to_thread(_fingerprint, tenant, "bazar", approval_id, body.proof)
    try:
        return await asyncio.to_thread(bazar.decide, tenant, approval_id, body.decision)
    except BazarError as e:
        raise HTTPException(400, str(e))


@app.get("/api/bazar/activity", dependencies=[Depends(require_key)])
def bazar_activity_api(tenant: str = Depends(current_tenant)):
    return bazar.activity(tenant)


@app.get("/api/bazar/files", dependencies=[Depends(require_key)])
def bazar_files(tenant: str = Depends(current_tenant)):
    """PDFs Santosh made for this user (GST invoices, quotations, salary slips, rent receipts, resumes)."""
    return {"files": bazar.list_docs(tenant)}


@app.get("/api/bazar/files/{doc_id}", dependencies=[Depends(require_key)])
def bazar_file(doc_id: str, tenant: str = Depends(current_tenant)):
    hit = bazar.get_doc(tenant, doc_id)
    if hit is None:
        raise HTTPException(404, "Not found")
    return FileResponse(hit[0], media_type="application/pdf", filename=hit[1])


@app.get("/api/bazar/files/{doc_id}/link", dependencies=[Depends(require_key)])
def bazar_file_fresh_link(doc_id: str, tenant: str = Depends(current_tenant)):
    """A fresh signed link for the chat card (the one in the card expires after a day)."""
    if bazar.get_doc(tenant, doc_id) is None:
        raise HTTPException(404, "Not found")
    return {"url": bazar.file_link(doc_id)}


@app.get("/api/bazar/files/{doc_id}/dl")
def bazar_file_link(doc_id: str, exp: int = 0, sig: str = ""):
    """Signed, expiring link from the chat card (opened in the phone's PDF viewer, which sends no auth header)."""
    if not bazar.check_file_sig(doc_id, exp, sig):
        raise HTTPException(403, "This link expired. Open the file from the Santosh app.")
    hit = bazar.get_doc(None, doc_id)
    if hit is None:
        raise HTTPException(404, "File no longer available")
    return FileResponse(hit[0], media_type="application/pdf", filename=hit[1])


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


# ---------------- Hoola Reels: share a reel to Hoola, turn it into something useful ----------------
class ReelLookIn(BaseModel):
    text: str


class ReelNoteIn(BaseModel):
    note: str = ""


class ReelRemindIn(BaseModel):
    when: str                      # local time, e.g. 2026-10-21T19:00
    text: str = ""


class ReelShopIn(BaseModel):
    items: list[str] = []


def _reel(fn, *a):
    from .reels import service as rs
    try:
        return fn(*a)
    except rs.ReelError as e:
        raise HTTPException(400, str(e))


@app.post("/api/reels/look", dependencies=[Depends(require_key)])
async def reel_look(body: ReelLookIn, tenant: str = Depends(current_tenant)):
    """A reel link shared from Instagram / YouTube / Facebook / Snapchat / Moj / Josh / ShareChat."""
    from .reels import service as rs
    return await asyncio.to_thread(_reel, rs.look_link, tenant, body.text[:4000])


@app.post("/api/reels/look_file", dependencies=[Depends(require_key)])
async def reel_look_file(file: UploadFile = File(...), text: str = Form(""), tenant: str = Depends(current_tenant)):
    """The owner's own screen recording / screenshot of a reel (for apps that don't share the video)."""
    from .reels import service as rs
    data = await file.read(rs.MAX_FILE + 1)
    return await asyncio.to_thread(_reel, rs.look_file, tenant, file.filename or "reel.mp4", file.content_type or "",
                                   data, text[:4000])


@app.get("/api/reels", dependencies=[Depends(require_key)])
def reels_saved(q: str = "", tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    return {"reels": rs.saved(tenant, q)}


# ---------------- Hoola Employee (v0.58): role, team, trust per duty, audit, pause, daily report ----------------
class EmployeeIn(BaseModel):
    enabled: bool | None = None
    preset: str | None = None
    upi_id: str | None = None
    upi_name: str | None = None
    slot_minutes: int | None = None
    inbox_on: bool | None = None
    role: str | None = None
    duties: list[str] | None = None
    business_name: str | None = None
    business_kind: str | None = None
    about: str | None = None
    hours: dict | None = None
    after_hours: str | None = None
    report_time: str | None = None
    rules: str | None = None
    reply_to_staff: bool | None = None


class EmployeePauseIn(BaseModel):
    paused: bool = True


class MemberIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    role: str | None = None
    duties: list[str] | None = None
    active: bool | None = None


class TrustIn(BaseModel):
    level: str | None = None
    per_day: int | None = None


class AskDecisionIn(BaseModel):
    approve: bool


class WrongIn(BaseModel):
    note: str = ""


class JobSheetIn(BaseModel):
    text: str = ""


def _emp(fn, *a, **kw):
    from .employee import service as emp
    try:
        return fn(*a, **kw)
    except emp.EmployeeError as e:
        raise HTTPException(400, str(e))


@app.get("/api/employee", dependencies=[Depends(require_key)])
def employee_get(tenant: str = Depends(current_tenant)):
    """Everything the Employee screen needs in one call."""
    from .employee import service as emp
    from .employee import inbox as biz_inbox
    from .employee.roles import DUTIES, LEVEL_LABEL, LEVELS, PRESETS, ROLES
    p = emp.profile(tenant)
    return {"profile": p, "status": emp.status(tenant), "trust": emp.trust(tenant) if p else [], "team": emp.team(tenant),
            "asks": emp.asks(tenant) if p else [],
            "roles": [{"id": k, "label": v["label"], "say": v["say"], "duties": v["duties"]} for k, v in ROLES.items()],
            "duties": [{"id": k, "label": v["label"], "say": v["say"]} for k, v in DUTIES.items()],
            "levels": [{"id": x, "label": LEVEL_LABEL[x]} for x in LEVELS],
            "presets": [{"id": k, "label": v["label"], "role": v["role"], "about_hint": v["about_hint"]} for k, v in PRESETS.items()],
            "inbox": biz_inbox.summary(tenant) if p else None}


@app.put("/api/employee", dependencies=[Depends(require_key)])
def employee_put(body: EmployeeIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.setup, tenant, **body.model_dump())


@app.post("/api/employee/pause", dependencies=[Depends(require_key)])
def employee_pause(body: EmployeePauseIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.set_pause, tenant, body.paused, "owner")


@app.get("/api/employee/team", dependencies=[Depends(require_key)])
def employee_team(tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return {"team": emp.team(tenant)}


@app.post("/api/employee/team", dependencies=[Depends(require_key)])
def employee_team_add(body: MemberIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.add_member, tenant, body.name or "", body.phone or "", body.address or "", body.role or "staff",
                body.duties or [])


@app.patch("/api/employee/team/{member_id}", dependencies=[Depends(require_key)])
def employee_team_edit(member_id: str, body: MemberIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.update_member, tenant, member_id, **body.model_dump())


@app.delete("/api/employee/team/{member_id}", dependencies=[Depends(require_key)])
def employee_team_remove(member_id: str, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    _emp(emp.remove_member, tenant, member_id)
    return {"ok": True}


@app.put("/api/employee/trust/{duty}", dependencies=[Depends(require_key)])
def employee_trust(duty: str, body: TrustIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.set_trust, tenant, duty, body.level, body.per_day)


@app.get("/api/employee/asks", dependencies=[Depends(require_key)])
def employee_asks(status: str = "pending", tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return {"asks": emp.asks(tenant, status)}


@app.post("/api/employee/asks/{ask_id}", dependencies=[Depends(require_key)])
async def employee_decide(ask_id: str, body: AskDecisionIn, tenant: str = Depends(current_tenant)):
    """The owner's Haan / Mana on something Hoola wanted to do on its own."""
    from .employee import service as emp
    try:
        return await emp.decide(tenant, ask_id, body.approve)
    except emp.EmployeeError as e:
        raise HTTPException(400, str(e))


@app.get("/api/employee/audit", dependencies=[Depends(require_key)])
def employee_audit(limit: int = 100, duty: str = "", day: str = "", tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return {"entries": _emp(emp.audit, tenant, limit, duty, day)}


@app.post("/api/employee/audit/{entry_id}/wrong", dependencies=[Depends(require_key)])
def employee_wrong(entry_id: str, body: WrongIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.mark_wrong, tenant, entry_id, body.note)


@app.get("/api/employee/report", dependencies=[Depends(require_key)])
def employee_report(day: str = "", tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    try:
        return emp.report(tenant, day)
    except ValueError:
        raise HTTPException(400, "day: YYYY-MM-DD")


@app.get("/api/employee/job_sheet", dependencies=[Depends(require_key)])
def employee_sheet(tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return emp.job_sheet(tenant)


@app.put("/api/employee/job_sheet", dependencies=[Depends(require_key)])
def employee_sheet_put(body: JobSheetIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.set_job_sheet, tenant, body.text)


@app.get("/api/employee/tasks", dependencies=[Depends(require_key)])
def employee_tasks(tenant: str = Depends(current_tenant)):
    from .employee import network
    return {"tasks": network.tasks(tenant)}


# ---------------- Hoola Employee v0.59: business WhatsApp inbox, appointments, dues, presets ----------------
class EmployeeSendIn(BaseModel):
    text: str = ""


class EmployeeHumanIn(BaseModel):
    human: bool = True
    note: str | None = None


class ChannelIn(BaseModel):
    phone_number_id: str
    display_number: str = ""
    token: str = ""


class ApptIn(BaseModel):
    start: str
    name: str = ""
    phone: str = ""
    note: str = ""


class ApptStatusIn(BaseModel):
    status: str


class DueIn(BaseModel):
    name: str = ""
    phone: str
    amount: float
    due_date: str = ""
    note: str = ""


class DueEditIn(BaseModel):
    status: str | None = None
    promised_on: str | None = None


def _inb(fn, *a, **kw):
    from .employee import inbox
    try:
        return fn(*a, **kw)
    except inbox.InboxError as e:
        raise HTTPException(400, str(e))


@app.get("/api/employee/presets", dependencies=[Depends(require_key)])
def employee_presets():
    from .employee.roles import PRESETS
    return {"presets": [{"id": k, "label": v["label"], "role": v["role"], "about_hint": v["about_hint"], "rules": v["rules"]}
                        for k, v in PRESETS.items()]}


@app.get("/api/employee/inbox", dependencies=[Depends(require_key)])
def employee_inbox(q: str = "", tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return {"contacts": inbox.contacts(tenant, q), "summary": inbox.summary(tenant)}


@app.get("/api/employee/inbox/{contact_id}", dependencies=[Depends(require_key)])
def employee_inbox_thread(contact_id: str, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.thread, tenant, contact_id)


@app.post("/api/employee/inbox/{contact_id}/send", dependencies=[Depends(require_key)])
async def employee_inbox_send(contact_id: str, body: EmployeeSendIn, tenant: str = Depends(current_tenant)):
    """The owner's own reply to a customer (she typed and tapped send: that is the confirmation)."""
    from .employee import inbox
    try:
        return await inbox.send(tenant, contact_id, body.text, by="owner")
    except inbox.InboxError as e:
        raise HTTPException(400, str(e))


@app.post("/api/employee/inbox/{contact_id}/human", dependencies=[Depends(require_key)])
def employee_inbox_human(contact_id: str, body: EmployeeHumanIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.set_human, tenant, contact_id, body.human, body.note)


@app.post("/api/employee/inbox/{contact_id}/answer", dependencies=[Depends(require_key)])
async def employee_inbox_answer(contact_id: str, tenant: str = Depends(current_tenant)):
    """Ask Hoola to answer this customer now (after the owner gave the chat back)."""
    from .employee import inbox
    _inb(inbox.thread, tenant, contact_id, 1, mark_read=False)      # 400 when it is not this owner's customer
    sent = await inbox.answer(tenant, contact_id)
    return {"sent": sent}


@app.get("/api/employee/channels", dependencies=[Depends(require_key)])
def employee_channels(tenant: str = Depends(current_tenant)):
    from .employee import inbox
    st = get_settings()
    return {"channels": inbox.channels(tenant), "webhook": "/webhooks/whatsapp", "server_number_owner": st.wa_inbox_tenant == tenant}


@app.put("/api/employee/channels", dependencies=[Depends(require_key)])
def employee_channel_set(body: ChannelIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.set_channel, tenant, body.phone_number_id, body.display_number, body.token)


@app.delete("/api/employee/channels/{phone_number_id}", dependencies=[Depends(require_key)])
def employee_channel_remove(phone_number_id: str, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    _inb(inbox.remove_channel, tenant, phone_number_id)
    return {"ok": True}


@app.get("/api/employee/slots", dependencies=[Depends(require_key)])
def employee_slots(date: str = "", days: int = 3, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    try:
        return {"free": inbox.free_slots(tenant, date, days)}
    except ValueError:
        raise HTTPException(400, "date: YYYY-MM-DD")


@app.get("/api/employee/appointments", dependencies=[Depends(require_key)])
def employee_appts(day: str = "", tenant: str = Depends(current_tenant)):
    from .employee import inbox
    try:
        return {"appointments": inbox.appointments(tenant, day)}
    except ValueError:
        raise HTTPException(400, "day: YYYY-MM-DD")


@app.post("/api/employee/appointments", dependencies=[Depends(require_key)])
def employee_appt_add(body: ApptIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.book, tenant, body.start, body.name, body.phone, "", body.note, "owner")


@app.patch("/api/employee/appointments/{appt_id}", dependencies=[Depends(require_key)])
def employee_appt_edit(appt_id: str, body: ApptStatusIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.set_appointment, tenant, appt_id, body.status)


@app.get("/api/employee/dues", dependencies=[Depends(require_key)])
def employee_dues(status: str = "", tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return {"dues": inbox.dues(tenant, status), "summary": inbox.dues_summary(tenant)}


@app.post("/api/employee/dues", dependencies=[Depends(require_key)])
def employee_due_add(body: DueIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.add_due, tenant, body.name, body.phone, body.amount, body.due_date, body.note)


@app.patch("/api/employee/dues/{due_id}", dependencies=[Depends(require_key)])
def employee_due_edit(due_id: str, body: DueEditIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.set_due, tenant, due_id, body.status, body.promised_on)


@app.post("/api/employee/dues/import", dependencies=[Depends(require_key)])
async def employee_dues_import(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .employee import inbox
    data = await file.read(2_000_001)
    if len(data) > 2_000_000:
        raise HTTPException(413, "CSV 2 MB tak.")
    return _inb(inbox.import_dues, tenant, data)


# reel scroll analysis (Usage Access numbers + the owner's own history download)
class ScrollSyncIn(BaseModel):
    days: list[dict] = []


class ScrollBudgetIn(BaseModel):
    minutes: int = 0


@app.post("/api/reels/scroll/sync", dependencies=[Depends(require_key)])
def scroll_sync(body: ScrollSyncIn, tenant: str = Depends(current_tenant)):
    from .reels import scroll
    return scroll.sync(tenant, body.days)


@app.get("/api/reels/scroll/report", dependencies=[Depends(require_key)])
def scroll_report(days: int = 7, tenant: str = Depends(current_tenant)):
    from .reels import scroll
    return scroll.report(tenant, days)


@app.post("/api/reels/scroll/budget", dependencies=[Depends(require_key)])
def scroll_budget(body: ScrollBudgetIn, tenant: str = Depends(current_tenant)):
    from .reels import scroll
    return scroll.set_budget(tenant, body.minutes)


@app.post("/api/reels/scroll/import", dependencies=[Depends(require_key)])
async def scroll_import(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """The owner's own Instagram 'Download your information' / Google Takeout YouTube history (zip, json or html)."""
    from .reels import scroll
    data = await file.read(scroll.MAX_IMPORT + 1)
    try:
        return await asyncio.to_thread(scroll.import_history, tenant, file.filename or "history", data)
    except scroll.ScrollError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/reels/scroll", dependencies=[Depends(require_key)])
def scroll_forget(tenant: str = Depends(current_tenant)):
    from .reels import scroll
    return scroll.forget(tenant)


@app.get("/api/reels/{reel_id}", dependencies=[Depends(require_key)])
def reel_get(reel_id: str, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    try:
        return rs.get(tenant, reel_id)
    except rs.ReelError as e:
        raise HTTPException(404, str(e))


@app.post("/api/reels/{reel_id}/save", dependencies=[Depends(require_key)])
def reel_save(reel_id: str, body: ReelNoteIn, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    return _reel(rs.save, tenant, reel_id, body.note)


@app.delete("/api/reels/{reel_id}/save", dependencies=[Depends(require_key)])
def reel_unsave(reel_id: str, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    return rs.unsave(tenant, reel_id)


@app.post("/api/reels/{reel_id}/remind", dependencies=[Depends(require_key)])
async def reel_remind(reel_id: str, body: ReelRemindIn, tenant: str = Depends(current_tenant)):
    from .agent.life_tools import create_reminder
    from .agent.tools import Ctx, ToolError
    from .reels import service as rs
    v = await asyncio.to_thread(_reel, rs.get, tenant, reel_id)
    text = (body.text.strip() or f"Reel: {v['title'] or 'jo save ki thi'}")[:400]
    if v["url"] and v["url"] not in text:
        text = f"{text} ({v['url']})"
    try:
        r = await create_reminder(Ctx(tenant, await asyncio.to_thread(_tv_conv, tenant)), text, body.when)
    except ToolError as e:
        raise HTTPException(400, str(e))
    return {"reminder": r, "say": f"Theek hai, {r.get('when') or body.when} ko yaad dila dunga."}


@app.post("/api/reels/{reel_id}/shop", dependencies=[Depends(require_key)])
async def reel_shop(reel_id: str, body: ReelShopIn, tenant: str = Depends(current_tenant)):
    """Products / ingredients of the reel -> the shopping list (+ plain search links to compare and buy)."""
    from .agent.life_tools import list_add
    from .agent.tools import Ctx
    from .reels import service as rs
    items = await asyncio.to_thread(_reel, rs.shop_items, tenant, reel_id, body.items or None)
    if not items:
        raise HTTPException(400, "Is reel mein khareedne layak cheez nahi mili.")
    r = await list_add(Ctx(tenant, await asyncio.to_thread(_tv_conv, tenant)), "shopping", items)
    return {"list": r["list"], "added": r["added"], "items": r["items"],
            "say": f"{len(r['added'])} cheezein shopping list mein daal di." if r["added"] else "Yeh sab pehle se list mein hai."}


@app.get("/api/reels/{reel_id}/share", dependencies=[Depends(require_key)])
def reel_share(reel_id: str, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    return _reel(rs.share_text, tenant, reel_id)


@app.post("/api/reels/{reel_id}/check", dependencies=[Depends(require_key)])
async def reel_check(reel_id: str, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    try:
        return await rs.fact_check(tenant, reel_id)
    except rs.ReelError as e:
        raise HTTPException(400, str(e))


# ---------------- v0.75 Pehchaan Locker: ID numbers (encrypted; masked unless she taps "dikhao") ----------------
class IdIn(BaseModel):
    kind: str
    number: str
    person: str = "self"
    note: str = ""


def _idv(fn, *a):
    from . import idvault
    try:
        return fn(*a)
    except idvault.VaultError as e:
        raise HTTPException(400, str(e))


@app.get("/api/ids", dependencies=[Depends(require_key)])
def ids_list(tenant: str = Depends(current_tenant)):
    from . import idvault
    return {"ids": idvault.list_(tenant), "kinds": idvault.KINDS, "people": idvault.PERSON_LABEL}


@app.post("/api/ids", dependencies=[Depends(require_key)])
def ids_save(body: IdIn, tenant: str = Depends(current_tenant)):
    from . import idvault
    return _idv(idvault.save, tenant, body.kind, body.number, body.person, body.note)


@app.post("/api/ids/{rid}/reveal", dependencies=[Depends(require_key)])
def ids_reveal(rid: str, tenant: str = Depends(current_tenant)):
    from . import idvault
    return _idv(idvault.reveal, tenant, rid)


@app.delete("/api/ids/{rid}", dependencies=[Depends(require_key)])
def ids_delete(rid: str, tenant: str = Depends(current_tenant)):
    from . import idvault
    return _idv(idvault.delete, tenant, rid)


# ---------------- v0.69 crash reports from the phone ----------------
class CrashIn(BaseModel):
    kind: str = ""
    text: str = ""
    during_call: bool = False


def _crash_file(tenant: str):
    from pathlib import Path
    p = Path("data") / "crashes"
    p.mkdir(parents=True, exist_ok=True)
    return p / (re.sub(r"[^A-Za-z0-9_-]", "_", tenant)[:60] + ".jsonl")


@app.post("/api/app/crash", dependencies=[Depends(require_key)])
def app_crash(body: CrashIn, tenant: str = Depends(current_tenant)):
    """Why the app closed by itself (stack trace or Android's exit record). Kept: the newest 50 per owner."""
    rec = {"at": time.time(), "kind": body.kind[:20], "during_call": body.during_call, "text": body.text[:20000]}
    f = _crash_file(tenant)
    lines = f.read_text(encoding="utf-8").splitlines()[-49:] if f.exists() else []
    lines.append(json.dumps(rec, ensure_ascii=False))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logging.getLogger("santosh.crash").warning("app crash (%s, call=%s): %s", rec["kind"], body.during_call,
                                               body.text[:400].replace("\n", " | "))
    return {"ok": True}


@app.get("/api/app/crashes", dependencies=[Depends(require_key)])
def app_crashes(tenant: str = Depends(current_tenant)):
    f = _crash_file(tenant)
    rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()] if f.exists() else []
    return {"crashes": rows[::-1]}


# ---------------- Hoola Motion: animated reels written as code, rendered to MP4 ----------------
class MotionPlanIn(BaseModel):
    kind: str
    brief: str


class MotionMakeIn(BaseModel):
    kind: str
    data: dict = {}
    brief: str = ""
    aspect: str = "9:16"
    music: str = "upbeat"


class MotionYoutubeIn(BaseModel):
    title: str = ""
    privacy: str = "private"


def _mo(fn, *a):
    from .motion import service as mo
    try:
        return fn(*a)
    except mo.MotionError as e:
        raise HTTPException(400, str(e))


@app.get("/api/motion/kinds", dependencies=[Depends(require_key)])
def motion_kinds(tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return mo.kinds()


@app.post("/api/motion/plan", dependencies=[Depends(require_key)])
async def motion_plan(body: MotionPlanIn, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return await asyncio.to_thread(_mo, mo.plan, body.kind, body.brief)


@app.post("/api/motion/videos", dependencies=[Depends(require_key)])
async def motion_make(body: MotionMakeIn, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return await asyncio.to_thread(_mo, mo.create, tenant, body.kind, body.data, body.aspect, body.music, body.brief)


@app.get("/api/motion/videos", dependencies=[Depends(require_key)])
def motion_list(tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return {"videos": mo.list_(tenant)}


@app.get("/api/motion/videos/{vid}", dependencies=[Depends(require_key)])
def motion_get(vid: str, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    try:
        return mo.get(tenant, vid)
    except mo.MotionError as e:
        raise HTTPException(404, str(e))


@app.delete("/api/motion/videos/{vid}", dependencies=[Depends(require_key)])
def motion_delete(vid: str, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return _mo(mo.delete, tenant, vid)


@app.post("/api/motion/videos/{vid}/youtube", dependencies=[Depends(require_key)])
async def motion_youtube(vid: str, body: MotionYoutubeIn, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    conv = await asyncio.to_thread(_tv_conv, tenant)
    return await asyncio.to_thread(_mo, mo.to_youtube, tenant, conv, vid, body.title, body.privacy)


@app.get("/api/motion/files/{name}")
def motion_file(name: str, exp: int = 0, sig: str = ""):
    """Signed link (no login header needed, so the phone's video player and share can use it)."""
    from fastapi.responses import FileResponse
    from .motion import service as mo
    m = re.fullmatch(r"(mv_[A-Za-z0-9]+)\.(mp4|jpg)", name)
    if not m or not mo.check_sig(m.group(1), m.group(2), exp, sig):
        raise HTTPException(403, "Link purana ho gaya.")
    p = mo.file_path(m.group(1), m.group(2))
    if p is None:
        raise HTTPException(404, "Video nahi mili.")
    return FileResponse(p, media_type="video/mp4" if m.group(2) == "mp4" else "image/jpeg",
                        filename=f"hoola-{m.group(1)}.{m.group(2)}" if m.group(2) == "mp4" else None)


# ---------------- Hoola TV: free official live channels, on the phone or the TV ----------------
class TvCastIn(BaseModel):
    channel: str
    tv: str = ""


def _tv_conv(tenant: str) -> str:
    from .bazar.service import latest_conversation
    with session() as s:
        return latest_conversation(s, tenant) or ""


@app.get("/api/tv/channels", dependencies=[Depends(require_key)])
def tv_channels(q: str = "", category: str = "", country: str = "", offset: int = 0, limit: int = 90,
                tenant: str = Depends(current_tenant)):
    """Channels worldwide. country = 'IN' / 'US'... ('' = whole world, India first); paged with offset/limit."""
    from .tv import catalog
    data = catalog.load()
    page = catalog.search(q, category, country, limit=max(1, min(limit, 200)), offset=max(0, offset))
    out = {**page, "offset": offset, "updated": data.get("updated", 0)}
    if offset == 0:
        out["categories"] = catalog.categories(country)
        out["countries"] = catalog.countries()
    return out


@app.get("/api/tv/channels/{cid}", dependencies=[Depends(require_key)])
def tv_channel_detail(cid: str, tenant: str = Depends(current_tenant)):
    from .tv import service as tvs
    try:
        return tvs.detail(cid)
    except tvs.TvError as e:
        raise HTTPException(404, str(e))


@app.post("/api/tv/cast", dependencies=[Depends(require_key)])
async def tv_cast(body: TvCastIn, tenant: str = Depends(current_tenant)):
    """Play a channel on the Chromecast / Android TV on the phone's Wi-Fi (the phone does it and reports back)."""
    from .tv import service as tvs
    try:
        return await tvs.play_on_tv(tenant, await asyncio.to_thread(_tv_conv, tenant), body.channel, body.tv)
    except tvs.TvError as e:
        raise HTTPException(404, str(e))


@app.post("/api/tv/stop", dependencies=[Depends(require_key)])
async def tv_stop(tenant: str = Depends(current_tenant)):
    from .tv import service as tvs
    return await tvs.stop_on_tv(tenant, await asyncio.to_thread(_tv_conv, tenant))


@app.get("/api/logo/{kind}/{key}")
async def plugin_logo(kind: str, key: str):
    """A plugin's / MCP server's real logo (from the brand's own site, cached as a 256 px PNG). Public: logos are
    public and phones load them as plain images; only things in Hoola's own lists are ever looked up."""
    from .bazar import logos
    if kind not in ("pack", "feat", "gh", "mcp", "tv") or len(key) > 120:
        raise HTTPException(404, "no logo")
    png = await asyncio.to_thread(logos.logo, kind, key)
    if not png:
        raise HTTPException(404, "no logo")
    return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=2592000"})


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


@app.get("/api/bazar/mcp/avatar", dependencies=[Depends(require_key)])
async def bazar_mcp_avatar(tenant: str = Depends(current_tenant)):
    """What the avatar knows about the owner's MCP servers right now: status and the tools it can call."""
    from .agent import mcp_live
    snap = await asyncio.to_thread(mcp_live.snapshot, tenant)
    return {"servers": [{"pack_id": x["pack_id"], "name": x["name"], "status": x["status"], "error": x["error"],
                         "tools": [t["name"] for t in x["tools"]]} for x in snap]}


class FeaturedIn(BaseModel):
    url: str = ""
    key: str = ""
    key_header: str = ""


@app.get("/api/bazar/mcp/featured", dependencies=[Depends(require_key)])
def bazar_mcp_featured(tenant: str = Depends(current_tenant)):
    return {"connectors": _bz(bazar.mcp_featured, tenant)}


@app.post("/api/bazar/mcp/featured/{fid}", dependencies=[Depends(require_key)])
async def bazar_mcp_connect(fid: str, body: FeaturedIn, tenant: str = Depends(current_tenant)):
    try:
        return await asyncio.to_thread(bazar.mcp_connect_featured, tenant, fid, body.url, body.key, body.key_header)
    except BazarError as e:
        raise HTTPException(400, str(e))


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


class McpToolIn(BaseModel):
    enabled: bool | None = None
    ask: bool | None = None


@app.get("/api/bazar/mcp/{pack_id}/tools", dependencies=[Depends(require_key)])
async def bazar_mcp_tools(pack_id: str, tenant: str = Depends(current_tenant)):
    """v0.91 Every tool of a server she added, with her on / off and "pehle poochho" switches."""
    return await asyncio.to_thread(_bz, bazar.mcp_tools, tenant, pack_id)


@app.patch("/api/bazar/mcp/{pack_id}/tools/{tool}", dependencies=[Depends(require_key)])
async def bazar_mcp_tool_set(pack_id: str, tool: str, body: McpToolIn, tenant: str = Depends(current_tenant)):
    return await asyncio.to_thread(_bz, bazar.mcp_tool_set, tenant, pack_id, tool, body.enabled, body.ask)


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


# ---------------- Santosh Shopping: orders, MCP tokens, ONDC callbacks, Commerce MCP at /mcp/commerce ----------------
from .bazar.api import commerce as bazar_commerce  # noqa: E402

bazar_commerce.mount(app, require_key, current_tenant)


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
    """Santosh Wake (our own on-device model). The app has the model built in; the server can push a newer one
    (WAKE_KEYWORD_FILE = path to a hey_santosh.onnx from wakeword/train.py) and tune the threshold."""
    import os
    st = get_settings()
    f = _wake_file()
    custom = bool(f) and f.endswith(".onnx")
    sens = min(max(st.wake_sensitivity, 0.0), 1.0)
    return {"available": True, "engine": "santosh-wake", "threshold": round(min(0.9, max(0.25, 1.1 - sens)), 3),
            "sensitivity": sens, "custom_model": custom, "version": str(int(os.path.getmtime(f))) if custom else "builtin"}


@app.get("/api/wake/keyword", dependencies=[Depends(require_key)])
def wake_keyword(tenant: str = Depends(current_tenant)):
    f = _wake_file()
    if not f:
        raise HTTPException(404, "No keyword file")
    if not f.endswith(".onnx"):
        raise HTTPException(404, "WAKE_KEYWORD_FILE must be a hey_santosh.onnx (Santosh Wake)")
    return FileResponse(f, media_type="application/octet-stream", filename="hey_santosh.onnx")


# ------------------------------------------------------------------ Santosh Artifacts
class ArtShareIn(BaseModel):
    on: bool = True


class ArtStateIn(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: object = None


class ArtAskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ArtReviseIn(BaseModel):
    request: str = Field(min_length=2, max_length=4000)


@app.get("/api/artifacts", dependencies=[Depends(require_key)])
def artifacts_list(tenant: str = Depends(current_tenant)):
    from . import artifacts
    return {"artifacts": artifacts.list_for(tenant)}


@app.get("/api/artifacts/{aid}", dependencies=[Depends(require_key)])
def artifact_detail(aid: str, tenant: str = Depends(current_tenant)):
    from . import artifacts
    d = artifacts.detail(tenant, aid)
    if d is None:
        raise HTTPException(404, "Not found")
    return d


@app.get("/api/artifacts/{aid}/view", dependencies=[Depends(require_key)])
def artifact_view_link(aid: str, version: int = 0, tenant: str = Depends(current_tenant)):
    from . import artifacts
    a = artifacts.get(tenant, aid)
    if a is None or not a.version:
        raise HTTPException(404, "Page not ready yet")
    v = version if 0 < version <= a.version else a.version
    return {"url": artifacts.view_url(aid, v), "version": v}


@app.post("/api/artifacts/{aid}/share", dependencies=[Depends(require_key)])
def artifact_share(aid: str, body: ArtShareIn, tenant: str = Depends(current_tenant)):
    from . import artifacts
    r = artifacts.set_share(tenant, aid, body.on)
    if r is None:
        raise HTTPException(404, "Not found")
    return r


@app.delete("/api/artifacts/{aid}", dependencies=[Depends(require_key)])
def artifact_delete(aid: str, tenant: str = Depends(current_tenant)):
    from . import artifacts
    if not artifacts.delete(tenant, aid):
        raise HTTPException(404, "Not found")
    return {"ok": True}


@app.get("/api/artifacts/{aid}/state", dependencies=[Depends(require_key)])
def artifact_state(aid: str, tenant: str = Depends(current_tenant)):
    from . import artifacts
    st = artifacts.state_all(tenant, aid)
    if st is None:
        raise HTTPException(404, "Not found")
    return {"state": st}


@app.put("/api/artifacts/{aid}/state", dependencies=[Depends(require_key)])
def artifact_state_set(aid: str, body: ArtStateIn, tenant: str = Depends(current_tenant)):
    from . import artifacts
    try:
        artifacts.state_set(tenant, aid, body.key, body.value)
    except KeyError:
        raise HTTPException(404, "Not found")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/artifacts/{aid}/ask", dependencies=[Depends(require_key)])
async def artifact_ask(aid: str, body: ArtAskIn, tenant: str = Depends(current_tenant)):
    from . import artifacts
    try:
        return {"answer": await artifacts.ask(tenant, aid, body.question)}
    except KeyError:
        raise HTTPException(404, "Not found")
    except ValueError as e:
        raise HTTPException(429 if "sawaal" in str(e) else 400, str(e))
    except Exception as e:
        raise HTTPException(503, f"Santosh abhi jawab nahi de pa raha ({type(e).__name__})")


@app.post("/api/artifacts/{aid}/revise", dependencies=[Depends(require_key)])
async def artifact_revise(aid: str, body: ArtReviseIn, tenant: str = Depends(current_tenant)):
    from . import artifacts
    a = artifacts.get(tenant, aid)
    if a is None:
        raise HTTPException(404, "Not found")
    try:
        await artifacts.make(tenant, a.conversation_id, body.request, artifact_id=aid, wait=0)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(409, str(e))
    return {"status": "building"}


@app.get("/a/{aid}/{version}")
def artifact_page(aid: str, version: int, exp: int = 0, sig: str = ""):
    """The owner's signed, expiring link (opened inside the app). Sandboxed: the page can't reach Santosh's API."""
    from . import artifacts
    from .db import Artifact, session as dbs
    if not artifacts.check(aid, version, exp, sig):
        raise HTTPException(403, "Link expired. Santosh app se dobara kholiye.")
    with dbs() as s:
        a = s.get(Artifact, aid)
        if a is None or a.deleted:
            raise HTTPException(404, "Not found")
        tenant = a.tenant_id
    page = artifacts.latest_html(aid, version)
    if page is None:
        raise HTTPException(404, "Not found")
    state = artifacts.state_all(tenant, aid) or {}
    return HTMLResponse(artifacts.render(aid, version, page, state), headers=artifacts.headers())


@app.get("/s/{token}")
def artifact_shared(token: str):
    """Public share link (latest version). Saved data is never included; it stays private to the owner."""
    from . import artifacts
    a = artifacts.by_share(token)
    if a is None or not a.version:
        raise HTTPException(404, "This link is off or doesn't exist")
    page = artifacts.latest_html(a.id, a.version) or ""
    return HTMLResponse(artifacts.render(a.id, a.version, page, None), headers=artifacts.headers())


# ------------------------------------------------------------------ push notifications (Firebase Cloud Messaging)
class PushTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=300)
    platform: str = "android"


@app.post("/api/push/token", dependencies=[Depends(require_key)])
def push_token(body: PushTokenIn, tenant: str = Depends(current_tenant)):
    from . import push
    push.register(tenant, body.token, body.platform)
    return {"ok": True, "push": push.configured()}


@app.delete("/api/push/token", dependencies=[Depends(require_key)])
def push_token_delete(body: PushTokenIn, tenant: str = Depends(current_tenant)):
    from . import push
    push.unregister(tenant, body.token)
    return {"ok": True}


# ------------------------------------------------------------------ Santosh Browser live view
@app.get("/api/browser/{sid}/live", dependencies=[Depends(require_key)])
def browser_live(sid: str, tenant: str = Depends(current_tenant)):
    from . import browser
    if sid.startswith("pcop_"):
        from .pc import operator
        op = operator.get(tenant, sid)
        if op is None:
            raise HTTPException(404, "not found")
        return op.live()
    try:
        return browser.live(tenant, sid)
    except browser.BrowserError as e:
        raise HTTPException(404, str(e))


@app.get("/api/browser/{sid}/frame", dependencies=[Depends(require_key)])
def browser_frame(sid: str, tenant: str = Depends(current_tenant)):
    from fastapi.responses import Response
    from . import browser
    if sid.startswith("pcop_"):
        from .pc import operator
        op = operator.get(tenant, sid)
        if op is None or not op.frame:
            raise HTTPException(404, "no frame yet")
        return Response(op.frame, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
    try:
        img = browser.frame(tenant, sid)
    except browser.BrowserError as e:
        raise HTTPException(404, str(e))
    return Response(img, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.post("/api/browser/{sid}/stop", dependencies=[Depends(require_key)])
def browser_stop(sid: str, tenant: str = Depends(current_tenant)):
    from . import browser
    if sid.startswith("pcop_"):
        from .pc import operator
        if not operator.stop(tenant, sid):
            raise HTTPException(404, "not found")
        return {"session_id": sid, "status": "cancelled"}
    try:
        return browser.cancel(tenant, sid)
    except browser.BrowserError as e:
        raise HTTPException(404, str(e))


# ------------------------------------------------------------------ Santosh Agent Army (open-source agents catalogue)
@app.get("/api/agents/directory", dependencies=[Depends(require_key)])
def agents_directory(q: str = "", field: str = "", kind: str = "", tier: str = "", limit: int = 30):
    from .bazar import agents
    return {"agents": agents.search(q, field, kind, tier, limit), "total": len(agents.agents())}


@app.get("/api/agents/fields", dependencies=[Depends(require_key)])
def agents_fields():
    from .bazar import agents
    return agents.stats()


@app.get("/api/agents/item/{ref}", dependencies=[Depends(require_key)])
def agents_item(ref: str):
    from .bazar import agents
    a = agents.get(ref)
    if a is None:
        raise HTTPException(404, "Not found")
    return a
