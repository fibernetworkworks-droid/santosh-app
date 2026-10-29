"""HTTP API for the Santosh app, the Meta webhook, and the demo chat page."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
from urllib.parse import quote
import json
import re
import logging
import threading
import time
import shutil
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select

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
APP_VERSION = "0.224.0"   # v0.224.0 VOICE PHASE 1 - stop the breakage (owner: START PHASE 1 after the voice-to-voice report; numbered past the dev's v0.221/v0.222 and the reserved v0.223 CONSOLE R1): (1) affective dialog never goes to a 3.x live model (Google removed it from gemini-3.8-live; every process lost its first connect to the heal), (2) every call tool says how it runs - slow work NON_BLOCKING with WHEN_IDLE results (he keeps talking), quick tools BLOCKING (exact answer, no guessing), (3) the passive voice approval answers only a card newer than her last turn and never carries words across turns, (4) voice-turn saves and the facts block run off the audio loop. Previous: v0.222.0 GOAL HERS - a long job SHE asked for keeps her authority in its background rounds (owner: "FIX 1 AND 2 THEN DEPLOY V0.222"): every round ran as actor "routine", so (1) with Employee mode on the gate held her own job's steps for approval at trust 'seekh' and (2) the monthly AI limit refused the rounds as background work. The goal now remembers who asked (origin); rounds of her job run as actor "goal" = her own authority at the gate and her own chat lane in the budget; a routine's job stays routine. Previous: v0.221.0 KAAM KHAATA - long jobs keep their progress and keep going (owner: "NOT ABLE TO PERFORM COMPLEX LONG TASK AND FORGOT THE WORK IN BETWEEN"). Root causes found on v0.220 and reproduced: (1) one message after a long job yaad squeezed it to its FIRST 13 steps, values cut at 60 chars, truncated results unreadable - the newest progress vanished; (2) the GLM / OmniRoute brain's finish_reason was never read: cut answers counted as finished and half-written tool calls ran with empty inputs; (3) without a kaam_plan the turn died at step 24 and that line was never saved; (4) a goal paused on her tap never restarted; (5) a finished job's result was never saved into history. Fixes: rich compress (every step of the newest 3 work exchanges + an open goal's turns, newest kept first, ids / links whole, truncated JSON salvaged), cut answers = max_tokens with more room, one-time move to long-job caps + deadline, the step-cap line saved, goal resume sweep (waiting time and resumes never count against it; rounds 3->6, working minutes 60->180), wake results saved (display None). Tests: test_v0221_kaam_khaata.py.


def _quiet_http_logs() -> None:
    """v0.190.1 P0: every TV-catalog health probe logged an INFO line to stderr - thousands per refresh,
    the error log and the disk drowned while the box crawled. Warnings and above still come through.
    Tool traffic is unaffected: inbound access is uvicorn.access, a different logger, untouched."""
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _quiet_http_logs()
    from . import usage as _usage
    _usage.install()          # v0.98 every Claude / Gemini call is counted (owner, feature, cost)
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
    try:                                       # v0.137 Tech suite modules read these from the environment
        import os as _os
        from .cyber import service as _cyber_svc
        _st = get_settings()
        _cyber_svc.SLEEP_BETWEEN_S = float(_st.cyber_sleep_between_s or 0)
        if _st.cyber_certin_feed:
            _os.environ.setdefault("CYBER_CERTIN_FEED", _st.cyber_certin_feed)
        if not _st.devops_llm:
            _os.environ.setdefault("DEVOPS_LLM", "false")
        if not _st.customs_llm:                 # v0.139 Safar suite
            _os.environ.setdefault("CUSTOMS_LLM", "false")
        if not _st.contracts_llm:               # v0.150 Kanoon suite
            _os.environ.setdefault("CONTRACTS_LLM", "false")
        for _k, _v in (("COURIER_DIR", _st.courier_dir), ("COURIER_BLUEDART_BASE", _st.courier_bluedart_base),
                       ("LOGISTICS_DIR", _st.logistics_dir), ("SITESUP_DIR", _st.sitesup_dir),
                       ("MOTIONDESK_DIR", _st.motiondesk_dir), ("PHOTOASSIST_DIR", _st.photoassist_dir), ("GRAPHIC_DIR", _st.graphic_dir)):
            if _v:
                _os.environ.setdefault(_k, _v)
        if _st.courier_poll_min:
            from .courier import service as _courier_svc
            _courier_svc.POLL_MIN = int(_st.courier_poll_min)
    except Exception:
        log.exception("tech suite settings")
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
    _usage.flush()               # v0.98 counted calls are not lost on a restart
    try:
        await operator_service.shutdown()
    except Exception:
        pass


app = FastAPI(title="Santosh Core", version=APP_VERSION, lifespan=lifespan)


@app.middleware("http")
async def _hosted_sites(request: Request, call_next):
    """v0.122 Websites Hoola launched are served from this server by their hostname (free Hoola address or her domain)."""
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if host and "." in host and not host.startswith(("127.", "localhost")) and request.method in ("GET", "HEAD"):
        from .site import hosting as _hosting
        hm = _hosting.host_map()
        if host in hm:
            res = await asyncio.to_thread(_hosting.serve, host, request.url.path)
            if res is not None:
                code, body, ctype, headers = res
                return Response(content=b"" if request.method == "HEAD" else body, status_code=code, media_type=ctype,
                                headers=headers)
    return await call_next(request)


@app.middleware("http")
async def _usage_scope(request: Request, call_next):
    """v0.98 Model calls made while serving this request are counted for its owner (resolved only if a model is called)
    and for a feature named by the path."""
    from . import usage

    def who() -> str:
        try:
            return _resolve_tenant(request)
        except Exception:
            return ""
    usage.bind(feature=usage.feature_for_path(request.url.path), resolver=who)
    return await call_next(request)


def _operator_ok() -> bool:
    try:
        from .operator.service import available
        return available()
    except Exception:
        return False


def _pg_ok() -> bool:
    try:
        import psycopg  # noqa: F401
        return True
    except ImportError:
        return False


def _blender_ok() -> bool:
    try:
        from .blender3d.sandbox import find
        return bool(find())
    except Exception:
        return False


def _qa_ok() -> bool:
    try:
        from .qa.runner import available
        return available() == ""
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
        if not c or c.tenant_id != tenant or c.deleted:     # v0.162 a deleted chat is gone from links too
            raise HTTPException(404, "Conversation not found")
        return c


# ---------------- health + demo page ----------------
@app.get("/healthz")
def healthz():
    st = get_settings()
    from .voice import MALE_VOICES
    from . import mail
    from .voiceid import engine as _vid_engine
    features = ["routines", "voice", "web", "bazar", "avatar", "bluetooth", "chat_files", "public_apis", "reels", "employee", "procedures", "darzi", "chai", "office", "lekhak", "mobile_shop", "phone_doctor", "gst", "payroll", "finance", "audit", "telecall", "insurance", "seo", "kalam", "thok", "niryat", "ads", "franchise", "theka", "brand", "website", "hoola_screen", "app_design", "app_android", "seva", "helpdesk", "shikayat", "aftersales", "feedback", "wapsi", "samudaay", "gyaan", "kaam_watch", "app_ideas", "devsahayak", "itadmin", "isp_noc", "cyber", "devops", "docwriter", "app_review", "product", "customs", "travel", "warehouse", "fleet", "courier", "drivers", "logistics", "propagent", "rentdesk", "site_supervisor", "interior", "archassist", "society", "vakil", "legal_research", "compliance", "contracts", "cosec", "notary", "pidesk", "dpo", "front_office", "eventplan", "shaadi", "tourguide", "homestay", "banquet", "edit_desk", "motiondesk", "patrakar", "photoassist", "artistmgr", "kitab", "podcast", "influencer", "graphic"] + (["film_desk"] if shutil.which("ffmpeg") else []) + (["qa"] if _qa_ok() else []) + (["callcentre"] if st.public_base_url and st.gemini_api_key else []) + (["video_editor"] if shutil.which("ffmpeg") else []) + (["blender_3d"] if _blender_ok() else []) + (["postgres"] if _pg_ok() else []) + (["computer_operator"] if _operator_ok() else []) + (["video_studio"] if shutil.which("ffmpeg") and get_settings().studio_on else []) + (["voiceid"] if _vid_engine.available() else []) + (["realtime_voice", "google_search"] if st.gemini_api_key else []) + (["side_talk"] if st.gemini_api_key and st.voice_side_talk else []) \
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


# ----------------------------------------------------------------------------- Hoola website on the Hoola server
_SITE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
             "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; "
             "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
_SITE_HEADERS = {"Content-Security-Policy": _SITE_CSP, "X-Content-Type-Options": "nosniff",
                 "Referrer-Policy": "strict-origin-when-cross-origin", "X-Frame-Options": "DENY",
                 "Cache-Control": "public, max-age=300"}


def _site_page(slug: str):
    return FileResponse(STATIC / "site" / f"{slug}.html", media_type="text/html", headers=_SITE_HEADERS)


@app.get("/")
def index():
    """The Hoola website (home). Every page has a Console button -> /console/. Websites Hoola launched for owners are
    served before this by their own hostnames (_hosted_sites)."""
    return _site_page("home")


@app.get("/employee")
def site_employee():
    return _site_page("employee")


@app.get("/network")
def site_network():
    return _site_page("network")


@app.get("/chat")
def old_web_chat():
    """The old one-page web chat (API key in the browser) that used to be at /. The Hoola Console replaces it."""
    return FileResponse(STATIC / "index.html")


@app.get("/download")
async def download_app():
    """Website download buttons: always the newest Android APK from the GitHub releases (cached 10 min); if GitHub
    can't be reached, the releases page."""
    from . import appupdate
    try:
        latest = await asyncio.to_thread(appupdate.latest)
    except Exception:
        latest = None
    url = (latest or {}).get("apk_url") or f"https://github.com/{appupdate._repo()}/releases"
    if not str(url).startswith("https://github.com/"):
        url = "https://github.com/fibernetworkworks-droid/santosh-app/releases"
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "no-store"})


# ----------------------------------------------------------------------------- v0.127 Hoola Screen (view-only second screen)
@app.get("/api/screen/link")
def screen_link(request: Request, days: int = 30, tenant: str = Depends(current_tenant)):
    from . import screen
    base = get_settings().public_base_url or str(request.base_url).rstrip("/")
    return screen.link(tenant, base, days)


@app.post("/api/screen/revoke")
def screen_revoke(tenant: str = Depends(current_tenant)):
    from . import screen
    return screen.revoke(tenant)


@app.get("/api/screen/preview")
def screen_preview(tenant: str = Depends(current_tenant)):
    from . import screen
    return screen.board(tenant)


@app.get("/api/screen/{token}/board")
def screen_board(token: str):
    """Public but read-only: the signed link is the only key; nothing can be changed from here."""
    from . import screen
    try:
        t = screen.tenant_of(token)
    except screen.ScreenError as e:
        raise HTTPException(403, str(e))
    return JSONResponse(screen.board(t), headers={"Cache-Control": "no-store"})


@app.get("/screen/{token}")
def screen_page(token: str):
    from . import screen
    try:
        screen.tenant_of(token)
    except screen.ScreenError as e:
        return HTMLResponse(f"<meta name=viewport content='width=device-width'><body style='font:20px system-ui;"
                            f"background:#0d1017;color:#eee;padding:40px'>{e}</body>", status_code=403)
    return HTMLResponse(screen.page(), headers={
        "Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                   "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'"})


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
def create_conversation(tenant: str = Depends(current_tenant), project_id: str = ""):
    # (tenant stays the FIRST argument: /api/bootstrap calls create_conversation(tenant) directly)
    if project_id:   # v0.164 "Naya chat" inside one of her projects
        from . import projects
        if not projects.enabled():
            raise HTTPException(404, "Projects are off (CHAT_PROJECTS)")
        try:
            projects.get(tenant, project_id)
        except projects.ProjectError as e:
            raise HTTPException(e.status, str(e))
    with session() as s:
        c = Conversation(tenant_id=tenant, project_id=project_id or None)
        s.add(c)
        s.flush()
        cid = c.id
    greeting = "Namaskar! Main Santosh hoon, aapka AI coworker. Aaj kya kaam poora karna hai?"
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=greeting, display=greeting,
                      in_history=False, delivered_to_agent=True))
    bus.publish(cid, "message", {"role": "assistant", "text": greeting, "source": "greeting"})
    from . import convs
    convs.mark(tenant, cid, "new")
    return {"id": cid}



@app.post("/api/conversations/{conversation_id}/stop", dependencies=[Depends(require_key)])
def stop_turn(conversation_id: str, tenant: str = Depends(current_tenant)):
    """Rokiye: Hoola stops the task after the step it is on (nothing new starts).
    v0.186: an open goal of this chat stops with it (the goal card shows stopped)."""
    _conv_or_404(conversation_id, tenant)
    from .agent.santosh import stop
    stop(conversation_id)
    return {"stopped": True}

@app.get("/api/conversations/{conversation_id}/goal", dependencies=[Depends(require_key)])
def get_goal(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.186 the working (or newest) goal of this chat, for the phone's goal card."""
    _conv_or_404(conversation_id, tenant)
    from .agent import goal
    v = goal.active_for(conversation_id)
    if v is None:
        with goal.session() as s:
            r = s.scalars(select(goal.GoalRun).where(goal.GoalRun.conversation_id == conversation_id)
                          .order_by(goal.GoalRun.updated_at.desc())).first()
            v = goal._row_view(r) if r is not None else None
    return {"goal": v}

@app.post("/api/conversations/{conversation_id}/goal/stop", dependencies=[Depends(require_key)])
def stop_goal(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.186 Rokiye for the goal only: the plan stops, the chat itself stays free."""
    _conv_or_404(conversation_id, tenant)
    from .agent import goal
    goal.mark_stopped(conversation_id)
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


@app.get("/api/conversations/{conversation_id}/harness-events", dependencies=[Depends(require_key)])
def harness_events(conversation_id: str, after: int = 0, limit: int = 100, tenant: str = Depends(current_tenant)):
    """v0.193 the harness session log of this chat (agent/eventlog.py): the machine-readable story of its turns -
    tools run, results, agents deployed, wakes. Read-only, for the console and debugging; the brain reads the same
    rows through the session_log tool."""
    _conv_or_404(conversation_id, tenant)
    from .agent import eventlog
    rows = eventlog.recent(conversation_id, limit=min(max(int(limit or 100), 1), 400))
    rows = [r for r in rows if r["id"] > after]
    return {"events": rows, "last_id": rows[-1]["id"] if rows else after}


@app.post("/api/conversations/{conversation_id}/messages", status_code=202, dependencies=[Depends(require_key)])
async def post_message(conversation_id: str, body: NewMessage, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    _conv_or_404(conversation_id, tenant)
    if _already_sent(tenant, conversation_id, body.client_id):
        return {"accepted": True, "duplicate": True}
    from . import chatfiles, convs, turn_inbox
    convs.mark(tenant, conversation_id, "message")   # v0.158 this is the chat she is in: notes and cards come here
    context = chatfiles.context(tenant, body.files) if body.files else ""
    shown = chatfiles.shown(tenant, body.files) if body.files else []
    bus.publish(conversation_id, "message", {"role": "user", "text": body.text, "source": "user",
                                             **({"client_id": body.client_id} if body.client_id else {}),
                                             **({"files": shown} if shown else {})})
    ti_id = turn_inbox.accept(tenant, conversation_id, body.text, bool(body.voice), context, body.client_id or "")
    if context:
        background.add_task(turn_inbox.run_owned, ti_id, conversation_id, body.text, tenant, bool(body.voice),
                            context=context, client_id=body.client_id or "")   # v0.173 steering: take-back while queued
    else:
        background.add_task(turn_inbox.run_owned, ti_id, conversation_id, body.text, tenant, bool(body.voice),
                            client_id=body.client_id or "")
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


REPLAY_MAX = 3000   # v0.158 more events than this to catch up = the app reloads the chat in order instead


@app.get("/api/conversations/{conversation_id}/events", dependencies=[Depends(require_key)])
async def events(conversation_id: str, request: Request, after: int = 0, live: int = 0,
                 tenant: str = Depends(current_tenant)):
    """Server-sent events: everything after `after` (this chat + cards from her other chats), then live.

    v0.158: the catch-up is paged until it reaches now (it used to send the oldest 500 and then skip the rest), a
    `replay_end` marker tells the app when catching up is over (no more guessing with a timer), and a gap too big to
    catch up sends `resync` so the app reloads the chat in order instead of showing a broken one.

    v0.161 `live=1`: also the reply being written (reply_start / delta / delta_reset / reply_end, never stored, sent
    without an SSE id). Without it (older apps) the stream is exactly as before."""
    _conv_or_404(conversation_id, tenant)
    from . import convs
    last = int(request.headers.get("last-event-id") or after or 0)
    q = bus.subscribe(conversation_id, tenant)
    convs.mark(tenant, conversation_id, "stream")

    async def gen():
        try:
            sent = last
            if last > 0:
                total = 0
                while True:
                    page = await asyncio.to_thread(bus.backlog, conversation_id, sent, 500, tenant)
                    for ev in page:
                        sent = ev["id"]
                        yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    total += len(page)
                    if len(page) < 500:
                        break
                    if total >= REPLAY_MAX:   # away too long: reload the chat in order
                        sent = await asyncio.to_thread(bus.last_id, conversation_id, tenant)
                        yield f"data: {json.dumps({'id': 0, 'kind': 'resync', 'payload': {'why': 'gap'}})}\n\n"
                        break
            else:
                sent = await asyncio.to_thread(bus.last_id, conversation_id, tenant)   # the app loads /timeline first
            yield f"data: {json.dumps({'id': 0, 'kind': 'replay_end', 'payload': {'last': sent}})}\n\n"
            ticks = 0
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    from . import offline
                    offline.touch(tenant)   # the stream is still open: the phone is online
                    ticks += 1
                    if live and ticks % 4 == 0:   # v0.178 every ~60 s: while a turn really runs, refresh its typing
                        try:                      # dots on the phone (a crashed turn stops refreshing -> they clear)
                            from .agent.santosh import turn_running
                            if turn_running(conversation_id):
                                yield f"data: {json.dumps({'id': 0, 'kind': 'typing', 'payload': {'on': True}, 'live': True})}\n\n"
                        except Exception:
                            pass
                    yield ": ping\n\n"
                    continue
                if ev.get("live"):
                    if live:
                        yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    continue
                if ev["id"] <= sent:
                    continue
                sent = ev["id"]
                yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            bus.unsubscribe(conversation_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/conversations/{conversation_id}/live", dependencies=[Depends(require_key)])
def chat_live(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.161 the reply being written right now ({turn, seg, seq, text}) so a reload continues it; 204 when none."""
    _conv_or_404(conversation_id, tenant)
    from . import livereply
    snap = livereply.snapshot(conversation_id)
    return snap if snap else Response(status_code=204)


@app.post("/api/conversations/{conversation_id}/retry", status_code=202, dependencies=[Depends(require_key)])
async def chat_retry(conversation_id: str, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    """v0.161 Dobara: her last message runs again and the new answer replaces the last reply (the old one is kept in
    the database as a branch). Nothing already sent / paid is repeated without a new card (see livereply.RETRY_NOTE)."""
    _conv_or_404(conversation_id, tenant)
    from . import chats, convs, livereply
    try:   # v0.162 CHAT_SESSIONS: the old reply stays as version 1 of 2 (‹ › arrows) instead of being replaced
        text, context = chats.retry(conversation_id) if chats.enabled() else livereply.prepare_retry(conversation_id)
    except (livereply.RetryError, chats.ChatError) as e:
        raise HTTPException(e.status, str(e))
    convs.mark(tenant, conversation_id, "message")
    background.add_task(run_turn, conversation_id, text, tenant, False, context=context)
    return {"accepted": True, "text": text}


class FeedbackIn(BaseModel):
    turn: str = Field(min_length=1, max_length=40)
    value: str = Field(max_length=8)
    note: str = Field(default="", max_length=500)


@app.post("/api/conversations/{conversation_id}/feedback", dependencies=[Depends(require_key)])
def chat_feedback(conversation_id: str, body: FeedbackIn, tenant: str = Depends(current_tenant)):
    """v0.161 thumbs up / down on one reply (counted in the usage report)."""
    _conv_or_404(conversation_id, tenant)
    from . import livereply
    try:
        return livereply.feedback(tenant, conversation_id, body.turn, body.value, body.note)
    except livereply.RetryError as e:
        raise HTTPException(e.status, str(e))


@app.get("/api/conversations/{conversation_id}/timeline", dependencies=[Depends(require_key)])
def chat_timeline(conversation_id: str, limit: int = 60, before: int = 0, steps: bool = False,
                  tenant: str = Depends(current_tenant)):
    """v0.158 the chat in order: messages and each card once where it first appeared, in its latest state (cards from
    her other chats too), newest page last; `before` = the page before that event id.
    v0.171 `steps=1` (the console): tool-call step events ride along so the transcript keeps what each turn did."""
    _conv_or_404(conversation_id, tenant)
    from .events import timeline
    return timeline(conversation_id, tenant, limit, before, steps=steps)


@app.get("/api/conversations/{conversation_id}/timeline/head", dependencies=[Depends(require_key)])
def chat_timeline_head(conversation_id: str, n: int = 40, tenant: str = Depends(current_tenant)):
    """v0.158 the app's self-check: the newest story ids in order (missing / out of order on the phone = reload)."""
    _conv_or_404(conversation_id, tenant)
    from .events import head
    return head(conversation_id, tenant, n)


def _export_name(conv: Conversation, ext: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (conv.title or "hoola-chat")).strip("-").lower()[:40] or "hoola-chat"
    return f"{slug}-{time.strftime('%Y%m%d-%H%M')}.{ext}"


@app.get("/api/conversations/{conversation_id}/export", dependencies=[Depends(require_key)])
def chat_export(conversation_id: str, fmt: str = "md", tenant: str = Depends(current_tenant)):
    """v0.171 the whole chat as one file (console: Export). `fmt=md` reads like the chat itself — her messages,
    Hoola's replies and the steps of each turn in order; `fmt=json` keeps every stored event for keeping/backup.
    Live-only noise (typing, deltas, think) was never stored, so it is simply absent; cards from her other chats
    and old retry branches are marked as what they are, never shown as reply text."""
    if not (get_settings().console_v2 or get_settings().console_stream):
        raise HTTPException(404, "Export is off (CONSOLE_V2)")
    conv = _conv_or_404(conversation_id, tenant)
    from .db import Event
    from .events import LIVE_ONLY
    from .avatar.service import persona
    with session() as s:
        rows = s.scalars(select(Event).where(Event.conversation_id == conversation_id).order_by(Event.id)).all()
        rows = [e for e in rows if e.kind not in ("typing", "log")]      # pure noise never belongs in a file
    avatar = persona(tenant)[0] or "Hoola"
    when = lambda iso: (iso or "")[:16].replace("T", " ")                # noqa: E731  2026-10-25 16:20
    if fmt == "json":
        import json as _json
        body = _json.dumps({
            "conversation": conversation_id, "title": conv.title or "", "tenant": tenant,
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "version": APP_VERSION,
            "events": [{"id": e.id, "kind": e.kind, "at": e.created_at.isoformat() if e.created_at else None,
                        "payload": e.payload} for e in rows],
        }, ensure_ascii=False, default=str, indent=1)
        return Response(body, media_type="application/json; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{_export_name(conv, "json")}"'})
    out = [f"# {conv.title or 'Hoola chat'}", "", f"> {avatar} ki chat · export {time.strftime('%d %b %Y, %H:%M')} · Hoola Console", ""]
    n_steps = 0
    for e in rows:
        p = e.payload if isinstance(e.payload, dict) else {}
        at = when(e.created_at.isoformat() if e.created_at else None)
        if e.kind == "message":
            text = str(p.get("text") or "").strip()
            if not text or p.get("replaced_by") or p.get("taken_back"):
                continue                  # empty shell, the old retry branch, or a message she took back
            who = "Aap" if p.get("role") == "user" else avatar
            files = p.get("files") or []
            head = f"## {who} · {at}"
            if p.get("edited"):
                head += " · (badla hua)"
            out += [head, "", text, ""]
            for f in files:
                name = f.get("name") if isinstance(f, dict) else str(f)
                if name:
                    out += [f"- 📎 {name}", ""]
            n_steps = 0
        elif e.kind == "step":
            if p.get("state") == "running":
                continue                                  # the done / error step of the same call follows it
            mark = "✓" if p.get("state") == "done" else "✕"
            line = f"- {mark} {p.get('label') or p.get('tool') or 'kadam'} `{p.get('tool') or ''}`"
            brief = p.get("args") or []
            if brief:                                     # v0.171 what was asked (already masked server-side)
                line += " — " + ", ".join(f"{k} {v}" for k, v in brief[:4])
            elif p.get("detail"):
                line += f" — {p['detail']}"
            if not n_steps:
                out += ["**Kadam**", ""]
            out += [line]
            n_steps += 1
        elif e.kind not in LIVE_ONLY and e.kind != "message":
            out += [f"_(card: {e.kind})_"] if out and out[-1] == "" else []
    md = "\n".join(out).rstrip() + "\n"
    return Response(md, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{_export_name(conv, "md")}"'})


@app.get("/api/conversations", dependencies=[Depends(require_key)])
def chat_list(limit: int = 40, archived: bool = False, tenant: str = Depends(current_tenant)):
    """v0.158 her old chats (newest activity first): nothing is lost when she starts a new one.
    v0.162 CHAT_SESSIONS: one query, pinned first, titles, archive list (`archived=true`), busy flags."""
    from . import chats, convs
    if chats.enabled():
        return {"conversations": chats.chat_list(tenant, archived, limit), "current": convs.current(tenant)}
    return {"conversations": convs.chats(tenant, limit), "current": convs.current(tenant)}


@app.get("/api/conversations/search", dependencies=[Depends(require_key)])
def chat_search(q: str = "", tenant: str = Depends(current_tenant)):
    """v0.162 titles and message text of her chats; each hit has the event id to jump to.
    v0.178 backed by the FTS5 index (chatsearch): prefix words, Hinglish / Devanagari, bm25 rank, real snippets."""
    from . import chats
    if not chats.enabled():
        raise HTTPException(404, "Chat search is off (CHAT_SESSIONS)")
    return {"results": chats.search(tenant, q[:200])}


@app.get("/api/conversations/{conversation_id}/find", dependencies=[Depends(require_key)])
def chat_find(conversation_id: str, q: str = "", tenant: str = Depends(current_tenant)):
    """v0.178 in-chat find (console Ctrl+F): every live match of this chat in document order + a total count, so the
    find bar can walk 3/17 with the arrows and jumpTo can load older pages on the way."""
    _conv_or_404(conversation_id, tenant)
    from . import chatsearch, chats
    if not chats.enabled():
        raise HTTPException(404, "Chat search is off (CHAT_SESSIONS)")
    return chatsearch.find_in_chat(tenant, conversation_id, q[:200])


class ChatPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    pinned: bool | None = None
    archived: bool | None = None
    project_id: str | None = Field(default=None, max_length=40)    # v0.164 "" / null = out of the project


def _chats_on():
    from . import chats
    if not chats.enabled():
        raise HTTPException(404, "Many chats is off (CHAT_SESSIONS)")
    return chats


@app.patch("/api/conversations/{conversation_id}", dependencies=[Depends(require_key)])
def chat_patch(conversation_id: str, body: ChatPatchIn, tenant: str = Depends(current_tenant)):
    """v0.162 rename / pin / archive. v0.164 project_id: into / out of one of her projects."""
    out: dict = {}
    if "project_id" in body.model_fields_set:
        from . import projects
        if not projects.enabled():
            raise HTTPException(404, "Projects are off (CHAT_PROJECTS)")
        try:
            out = projects.set_chat(tenant, conversation_id, body.project_id or None)
        except projects.ProjectError as e:
            raise HTTPException(e.status, str(e))
        if not ({"title", "pinned", "archived"} & body.model_fields_set):
            return out
    chats = _chats_on()
    try:
        return {**out, **chats.patch(tenant, conversation_id, body.title, body.pinned, body.archived)}
    except chats.ChatError as e:
        raise HTTPException(e.status, str(e))


@app.delete("/api/conversations/{conversation_id}", dependencies=[Depends(require_key)])
def chat_delete(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.162 soft delete (the console asks first): gone from the list, search and links; rows kept."""
    chats = _chats_on()
    _conv_or_404(conversation_id, tenant)
    try:
        return chats.delete(tenant, conversation_id)
    except chats.ChatError as e:
        raise HTTPException(e.status, str(e))


class ChatEditIn(BaseModel):
    event_id: int
    text: str = Field(min_length=1, max_length=4000)


async def _edited_turn(conversation_id: str, text: str, tenant: str, parent: int | None) -> None:
    await run_turn(conversation_id, text, tenant, False)
    if parent:
        from .db import Message
        with session() as s:   # the new version of her message points to the one she edited
            row = s.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.role == "user",
                                                  Message.in_history.is_(True), Message.parent_id.is_(None),
                                                  Message.id > parent).order_by(Message.id)).first()
            if row is not None:
                row.parent_id = parent


@app.post("/api/conversations/{conversation_id}/edit", status_code=202, dependencies=[Depends(require_key)])
def chat_edit(conversation_id: str, body: ChatEditIn, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    """v0.162 her message edited: a new version from there (the old one stays, ‹ 1/2 ›); the new text runs as a turn."""
    chats = _chats_on()
    _conv_or_404(conversation_id, tenant)
    try:
        b = chats.edit(conversation_id, body.event_id, body.text)
    except chats.ChatError as e:
        raise HTTPException(e.status, str(e))
    from . import convs
    convs.mark(tenant, conversation_id, "message")
    ev = bus.publish(conversation_id, "message", {"role": "user", "text": body.text.strip(), "source": "user",
                                                  "edited": True, "branch": b["group"]})
    chats.started(conversation_id, b["group"], ev["id"])
    background.add_task(_edited_turn, conversation_id, body.text.strip(), tenant, b.get("parent"))
    return {"accepted": True, **b, "event_id": ev["id"]}


class ChatBranchIn(BaseModel):
    group: int
    index: int


class TakebackIn(BaseModel):
    client_id: str = Field(min_length=8, max_length=64)


@app.post("/api/conversations/{conversation_id}/takeback", dependencies=[Depends(require_key)])
def chat_takeback(conversation_id: str, body: TakebackIn, tenant: str = Depends(current_tenant)):
    """v0.173 she takes back a message that is still only queued (Hoola busy with the previous kaam): it never
    reaches the model and its bubble leaves the chat. The turn already running with it cannot be taken back
    (Rokiye is for that)."""
    _conv_or_404(conversation_id, tenant)
    from .agent import santosh
    if santosh.message_running(conversation_id, body.client_id):
        raise HTTPException(409, "Yeh message chal padi hai. Rokne ke liye 'Rokiye' dabaiye.")
    from .db import Event
    with session() as s:
        rows = s.scalars(select(Event).where(Event.conversation_id == conversation_id, Event.kind == "message")
                         .order_by(Event.id.desc()).limit(80)).all()
        hit = next((e for e in rows if isinstance(e.payload, dict) and e.payload.get("client_id") == body.client_id
                    and e.payload.get("role") == "user" and not e.payload.get("taken_back")), None)
        if hit is None:
            raise HTTPException(404, "Woh message nahi mili (shayad pehle hi le li gayi).")
        hit.payload = {**hit.payload, "taken_back": True}
        eid = hit.id
    santosh.hold_message(conversation_id, body.client_id)
    return {"taken": True, "event_id": eid}


@app.post("/api/conversations/{conversation_id}/branch", dependencies=[Depends(require_key)])
def chat_branch(conversation_id: str, body: ChatBranchIn, tenant: str = Depends(current_tenant)):
    """v0.162 ‹ / ›: show another version of an edited message or a re-asked reply (nothing is lost)."""
    chats = _chats_on()
    _conv_or_404(conversation_id, tenant)
    try:
        return chats.switch(conversation_id, body.group, body.index)
    except chats.ChatError as e:
        raise HTTPException(e.status, str(e))


@app.post("/api/conversations/{conversation_id}/open", dependencies=[Depends(require_key)])
def chat_open(conversation_id: str, tenant: str = Depends(current_tenant)):
    _conv_or_404(conversation_id, tenant)
    from . import convs
    convs.mark(tenant, conversation_id, "open")
    return {"ok": True}


class ChatHealIn(BaseModel):
    kind: str = Field(default="resync", max_length=16)
    reason: str = Field(default="", max_length=300)
    data: dict = Field(default_factory=dict)


@app.post("/api/chat/heal", dependencies=[Depends(require_key)])
def chat_heal(body: ChatHealIn, tenant: str = Depends(current_tenant)):
    """The app found its chat different from the server's and reloaded it: kept for Hoola Jaanch."""
    from . import convs
    data = {k: v for k, v in (body.data or {}).items() if isinstance(v, (int, float, str, bool))}
    return convs.heal_report(tenant, "resync", body.reason, data)


@app.get("/api/chat/health", dependencies=[Depends(require_key)])
def chat_health(tenant: str = Depends(current_tenant)):
    from . import convs
    return convs.health(tenant)


@app.get("/api/chat/waiting", dependencies=[Depends(require_key)])
def chat_waiting(tenant: str = Depends(current_tenant)):
    """Cards in any of her chats that wait for her now."""
    from .events import waiting_cards
    return {"waiting": waiting_cards(tenant, 40)}


class CallCardsIn(BaseModel):
    conversation_id: str = Field(default="", max_length=40)
    cards: list[dict] = Field(default_factory=list, max_length=30)


@app.get("/api/voice/card_rules", dependencies=[Depends(require_key)])
def voice_card_rules(tenant: str = Depends(current_tenant)):
    """v0.158 card kinds that stay out of her calls (learned from what she closed unused before)."""
    from . import convs
    return convs.call_rules(tenant)


@app.post("/api/voice/calls/{call_id}/cards", dependencies=[Depends(require_key)])
async def voice_call_cards(call_id: str, body: CallCardsIn, tenant: str = Depends(current_tenant)):
    """The app reports which cards a call showed and what she did with them; Hoola learns what to keep out."""
    from . import convs
    conv = body.conversation_id if body.conversation_id and convs.tenant_of(body.conversation_id) == tenant else ""
    return await asyncio.to_thread(convs.call_report, tenant, call_id[:40], body.cards, conv)


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
from .db import DeviceAction, ListItem, MemoryFact, Profile, Reminder, as_utc, now  # noqa: E402


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
def google_start(app_session: bool = True, web: bool = False, apps: bool = False):
    """The app opens this; we redirect to Google's consent screen. web=1 = the Hoola Console (v0.142): sign-in with
    name + email only; web=1&apps=1 = the console's "Google apps jodiye" (Gmail, Drive, Calendar, Docs, Sheets)."""
    from . import accounts
    try:
        return RedirectResponse(accounts.start_google(web=web, apps=apps))
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
    from .seo.service import is_link_state as is_seo_state
    if is_seo_state(request.query_params.get("state", "")):     # "connect my Search Console" (read-only)
        return await _finish_seo_link(request)
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
    from .feedback.gbp import is_link_state as is_fb_state
    if is_fb_state(request.query_params.get("state", "")):      # v0.133 "connect my Business Profile reviews" (Feedback Sahayak)
        from .feedback.api import finish_page as fb_finish
        return await fb_finish(request)
    from .itadmin.connectors import is_link_state as is_ita_state
    if is_ita_state(request.query_params.get("state", "")):     # v0.137 "connect my Google Workspace admin" (IT Admin Sahayak)
        from .itadmin.api import finish_page as ita_finish
        return await ita_finish(request)
    from .forms.accounts import is_link_state as is_form_state
    if is_form_state(request.query_params.get("state", "")):    # "connect my Google Forms"
        from .forms.api import finish_page as forms_finish
        return await forms_finish(request)
    code = request.query_params.get("code")
    state = request.query_params.get("state", "")
    err = request.query_params.get("error")
    from .console import service as console
    web = console.is_web_state(state)
    if err:
        if web:   # she pressed Cancel on Google's screen: back to the console, not a bare error page
            msg = "Google sign-in band kiya gaya." if err == "access_denied" else f"Google sign-in nahi hua ({err[:40]})."
            return RedirectResponse("/console/?error=" + quote(msg), headers=_CONSOLE_NOREF)
        return HTMLResponse(f"<h3>Sign-in cancelled</h3><p>{err}</p>", status_code=400)
    if not code:
        raise HTTPException(400, "Missing code")
    try:
        res = await accounts.finish_google(code, state)
    except accounts.AuthError as e:
        if web:
            return RedirectResponse("/console/?error=" + quote(str(e)[:160]), headers=_CONSOLE_NOREF)
        return HTMLResponse(f"<h3>Sign-in nahi hua</h3><p>{e}</p>", status_code=400)
    if web:   # v0.142 Hoola Console: a one-time code, never the session token, goes into the URL
        apps = "&google=apps" if state.startswith(console.WEB_STATE + "g.") else ""
        return RedirectResponse("/console/?code=" + console.issue_code(res["session_token"]) + apps, headers=_CONSOLE_NOREF)
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


# ---------------------------------------------------------------- v0.142 Hoola Console (web app at /console)
_CONSOLE_NOREF = {"Referrer-Policy": "no-referrer", "Cache-Control": "no-store"}
_CONSOLE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
                "worker-src 'self' blob:; frame-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


@app.get("/console")
@app.get("/console/")
@app.get("/console/c/{conversation_id}")
def console_page(conversation_id: str = "", legacy: bool = False):
    """The Hoola Console: chat-first web app on the same APIs as the phone (login: Google or Hoola ID + password).
    v0.162 /console/c/<id> = a link to one chat (same page; the page opens that chat).
    v0.170 Console v2 (CONSOLE_V2, default on): the Night-Glass v2 shell serves the same address and the same APIs;
    ?legacy=1 (or CONSOLE_V2=false) serves the previous console page unchanged."""
    st = get_settings()
    page = "index.html" if (legacy or not st.console_v2) else "v2.html"
    return FileResponse(STATIC / "console" / page, headers={
        **_CONSOLE_NOREF, "Content-Security-Policy": _CONSOLE_CSP, "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff", "Permissions-Policy": "microphone=(self), camera=(), geolocation=()"})


@app.get("/api/console/config")
def console_config():
    from . import accounts
    st = get_settings()
    return {"app": "Hoola", "version": app.version, "google": accounts.oauth_configured(), "password": True,
            "v2": bool(st.console_v2),
            "stream": bool(st.console_v2 or st.console_stream), "sessions": bool(st.console_v2 or st.chat_sessions),
            "panel": bool(st.console_v2 or st.side_panel), "projects": bool(st.console_v2 or st.chat_projects)}


@app.get("/api/console/stream", dependencies=[Depends(require_key)])
async def console_stream(request: Request, after: int = 0, tenant: str = Depends(current_tenant)):
    """v0.162 ONE stream for all her chats (CHAT_SESSIONS): every event of every chat, tagged `conv`, including the
    reply being written (live-only, no SSE id). The console switches chats without reconnecting, so work in one chat
    never stops when she opens another, and every chat that works gets a busy badge."""
    _chats_on()
    last = int(request.headers.get("last-event-id") or after or 0)
    q = bus.subscribe_account(tenant)

    async def gen():
        try:
            sent = last
            if last > 0:
                total = 0
                while True:
                    page = await asyncio.to_thread(bus.backlog_account, tenant, sent, 500)
                    for ev in page:
                        sent = ev["id"]
                        yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    total += len(page)
                    if len(page) < 500:
                        break
                    if total >= REPLAY_MAX:
                        sent = await asyncio.to_thread(bus.last_account_id, tenant)
                        yield f"data: {json.dumps({'id': 0, 'kind': 'resync', 'payload': {'why': 'gap'}})}\n\n"
                        break
            else:
                sent = await asyncio.to_thread(bus.last_account_id, tenant)
            yield f"data: {json.dumps({'id': 0, 'kind': 'replay_end', 'payload': {'last': sent}})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    from . import offline
                    offline.touch(tenant)
                    yield ": ping\n\n"
                    continue
                if ev.get("live"):
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    continue
                if ev["id"] <= sent:
                    continue
                sent = ev["id"]
                yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            bus.unsubscribe_account(tenant, q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class ConsoleLoginIn(BaseModel):
    handle: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


def _client_ip(request: Request) -> str:
    """nginx's X-Real-IP ($remote_addr) only; a client-sent X-Forwarded-For is not trusted."""
    return (request.headers.get("x-real-ip", "").strip() or (request.client.host if request.client else "") or "?")[:64]


@app.post("/api/console/login")
def console_login(body: ConsoleLoginIn, request: Request):
    from .console import service as console
    try:
        return console.login(body.handle, body.password, _client_ip(request))
    except console.ConsoleError as e:
        raise HTTPException(e.status, str(e))


class ConsoleCodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)


@app.post("/api/console/exchange")
def console_exchange(body: ConsoleCodeIn):
    from .console import service as console
    try:
        return {"session_token": console.exchange(body.code)}
    except console.ConsoleError as e:
        raise HTTPException(e.status, str(e))


class ConsolePasswordIn(BaseModel):
    password: str = Field(default="", max_length=200)
    current: str = Field(default="", max_length=200)
    remove: bool = False


@app.put("/api/console/password", dependencies=[Depends(require_key)])
def console_password(body: ConsolePasswordIn, tenant: str = Depends(current_tenant)):
    from .console import service as console
    try:
        if body.remove:
            return {"removed": console.remove_password(tenant, body.current)}
        return console.set_password(tenant, body.password, body.current)
    except console.ConsoleError as e:
        raise HTTPException(e.status, str(e))


@app.get("/api/console/me", dependencies=[Depends(require_key)])
def console_me(tenant: str = Depends(current_tenant)):
    from .console import service as console
    return console.me(tenant)


@app.get("/api/console/conversations", dependencies=[Depends(require_key)])
def console_conversations(limit: int = 40, archived: bool = False, project: str = "", tenant: str = Depends(current_tenant)):
    from . import chats
    if chats.enabled():   # v0.162 one query instead of 2 per chat; pinned first, titles, busy (v0.164 + project filter)
        return {"conversations": chats.chat_list(tenant, archived, max(limit, 200), project[:40])}
    from .console import service as console
    return {"conversations": console.conversations(tenant, limit)}


@app.get("/api/console/pending", dependencies=[Depends(require_key)])
def console_pending(tenant: str = Depends(current_tenant)):
    from .console import service as console
    return {"pending": console.pending(tenant)}


_CARD_SKIP = {"message", "typing", "step", "work"}


@app.get("/api/console/conversations/{conversation_id}/recent", dependencies=[Depends(require_key)])
def console_recent(conversation_id: str, n: int = 60, tenant: str = Depends(current_tenant)):
    """Opening an old chat: the cursor to stream from, and the latest state of its last cards (newest per card id)."""
    _conv_or_404(conversation_id, tenant)
    from .db import Event
    with session() as s:
        last = s.scalar(select(func.max(Event.id)).where(Event.conversation_id == conversation_id)) or 0
        rows = s.scalars(select(Event).where(Event.conversation_id == conversation_id, Event.kind.not_in(_CARD_SKIP))
                         .order_by(Event.id.desc()).limit(max(1, min(n, 200)) * 3)).all()
        seen, cards = set(), []
        for e in rows:
            p = e.payload if isinstance(e.payload, dict) else {}
            key = (e.kind, str(p.get("id") or p.get("task_id") or e.id))
            if key in seen:
                continue
            seen.add(key)
            cards.append({"id": e.id, "kind": e.kind, "payload": p, "at": e.created_at.isoformat()})
            if len(cards) >= n:
                break
    return {"last_event_id": last, "cards": list(reversed(cards))}


@app.get("/api/console/today", dependencies=[Depends(require_key)])
def console_today(tenant: str = Depends(current_tenant)):
    from .console import service as console
    return console.today(tenant)


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
async def pc_upload(request: Request, file: UploadFile = File(...), path: str = Form(""),
                    direction: str = Form("to_phone")):
    """The PC uploads a file the phone asked for. v0.202 PC-to-PC bridge: the Hoola PC uploads with
    direction "to_pc" so the USER'S personal PC can fetch it into her Santosh Inbox; every old desktop
    sends no direction and keeps "to_phone" (a phone download card) exactly as before."""
    from .pc import service as pcs
    dev = _pc_device(request)
    if direction not in ("to_phone", "to_pc"):   # unknown value = the safe old behaviour
        direction = "to_phone"
    try:
        row = await pcs.store_upload(file, dev.tenant_id, dev.id, direction, path)
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


@app.get("/api/pc/hoola", dependencies=[Depends(require_key)])
def pc_hoola_devices(tenant: str = Depends(current_tenant)):
    """v0.205 HOOLA PC AND MERA PC ARE DIFFERENT SECTIONS: the phone's own "Hoola ka PC" section
    feeds from here — ONLY the Hoola PC (Hoola's own cloud container), never the user's personal
    PCs; /api/pc/devices stays personal-only (the v0.201 rule untouched), this is its mirror."""
    from .pc import service as pcs
    return {"devices": pcs.hoola_devices(tenant)}


@app.get("/api/pc/hoola/jobs", dependencies=[Depends(require_key)])
def pc_hoola_jobs(limit: int = 50, tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    return {"jobs": pcs.hoola_jobs(tenant, limit)}


@app.post("/api/pc/search", dependencies=[Depends(require_key)])
async def pc_search(body: PcSearchIn, tenant: str = Depends(current_tenant)):
    from .pc.hub import hub
    try:   # v0.200 Mera PC = user personal PC: search is HER PC's job, never the Hoola PC's
        return await hub.call_personal(tenant, "search", {"query": body.query, "kind": body.kind, "limit": 30})
    except Exception as e:
        _pc_err(e)


@app.post("/api/pc/pull", dependencies=[Depends(require_key)])
async def pc_pull(body: PcPullIn, tenant: str = Depends(current_tenant)):
    """Phone asks for one PC file; returns a download link."""
    from .pc import service as pcs
    from .pc.hub import hub
    try:   # v0.200 Mera PC = user personal PC: pull is HER PC's job, never the Hoola PC's
        out = await hub.call_personal(tenant, "send_file", {"path": body.path})
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
    if not hub.has_personal(tenant):   # v0.200 Mera PC = user personal PC: send targets HER PC only
        raise HTTPException(409, "PC offline hai. PC on karke Santosh Desktop kholiye.")
    try:
        row = await pcs.store_upload(file, tenant, "", "to_pc")
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    try:
        return await hub.call_personal(tenant, "save_file", {"file_id": row.id, "name": row.name, "url": f"/api/pc/fetch/{row.id}"})
    except Exception as e:
        _pc_err(e)


@app.get("/api/voice/check", dependencies=[Depends(require_key)])
async def voice_check(tenant: str = Depends(current_tenant)):
    """v0.150 Connect to Gemini Live the way her calls do and say which part it refuses (and heal it)."""
    from . import voicecheck
    return await voicecheck.run(tenant)


@app.get("/api/voice/stats", dependencies=[Depends(require_key)])
def voice_stats(tenant: str = Depends(current_tenant)):
    """How human the calls sound, in numbers: how fast he starts answering, reply length, questions, interruptions,
    silent tool runs. Recent calls since the server started."""
    from . import callrating
    from . import voice as v
    return {**v.stats_summary(tenant), "ratings": callrating.summary(tenant)}   # v0.98 her own 👍 / 👎 too


class CallRate(BaseModel):
    good: bool
    reasons: list[str] = Field(default_factory=list)
    seconds: int = 0


@app.post("/api/voice/calls/{call_id}/rating", dependencies=[Depends(require_key)])
def voice_rate(call_id: str, body: CallRate, tenant: str = Depends(current_tenant)):
    """v0.98 her one tap after a call: good / not good + what went wrong."""
    from . import callrating
    return callrating.rate(tenant, call_id, body.good, body.reasons, body.seconds)


# ---- v0.119 "<name> ne kya seekha": how she speaks, words misheard before, her words (numbers and words only) ----
class VoiceLearnBody(BaseModel):
    learn: bool


class VoiceWordBody(BaseModel):
    term: str = Field(min_length=2, max_length=60)


class VoiceFixBody(BaseModel):
    heard: str = Field(min_length=1, max_length=80)
    meant: str = Field(min_length=1, max_length=80)


def _vs_call(fn, *a):
    from . import voicestyle
    try:
        return fn(*a)
    except voicestyle.StyleError as e:
        raise HTTPException(400, str(e))


@app.get("/api/voice/learned", dependencies=[Depends(require_key)])
def voice_learned(tenant: str = Depends(current_tenant)):
    from . import voicestyle
    v = voicestyle.view(tenant)
    v["say"] = voicestyle.say(tenant)
    return v


@app.put("/api/voice/learned", dependencies=[Depends(require_key)])
def voice_learned_set(body: VoiceLearnBody, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return voicestyle.set_learn(tenant, body.learn)


@app.delete("/api/voice/learned", dependencies=[Depends(require_key)])
def voice_learned_forget(part: str = "all", tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return _vs_call(voicestyle.forget, tenant, part)


@app.post("/api/voice/learned/words", dependencies=[Depends(require_key)])
def voice_word_add(body: VoiceWordBody, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return _vs_call(voicestyle.add_word, tenant, body.term, "her")


@app.delete("/api/voice/learned/words/{word_id}", dependencies=[Depends(require_key)])
def voice_word_remove(word_id: int, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    if not voicestyle.remove_word(tenant, word_id):
        raise HTTPException(404, "Shabd nahi mila")
    return {"ok": True}


@app.post("/api/voice/learned/fixes", dependencies=[Depends(require_key)])
def voice_fix_add(body: VoiceFixBody, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return _vs_call(voicestyle.note_fix, tenant, body.heard, body.meant, True)


@app.post("/api/voice/learned/fixes/{fix_id}/confirm", dependencies=[Depends(require_key)])
def voice_fix_confirm(fix_id: int, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return _vs_call(voicestyle.confirm_fix, tenant, fix_id)


@app.delete("/api/voice/learned/fixes/{fix_id}", dependencies=[Depends(require_key)])
def voice_fix_remove(fix_id: int, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    if not voicestyle.remove_fix(tenant, fix_id):
        raise HTTPException(404, "Sudhaar nahi mila")
    return {"ok": True}


class UsageLimit(BaseModel):
    month_inr: float | None = Field(default=None, ge=0, le=10_000_000)
    month_usd: float | None = Field(default=None, ge=0, le=100_000)


@app.get("/api/usage", dependencies=[Depends(require_key)])
def usage_get(days: int = 30, tenant: str = Depends(current_tenant)):
    """v0.98 Kharcha: what Hoola's AI cost this owner (per day, per feature, per model), the month vs her limit."""
    from . import usage
    return usage.report(tenant, days)


@app.put("/api/usage/limit", dependencies=[Depends(require_key)])
def usage_limit(body: UsageLimit, tenant: str = Depends(current_tenant)):
    from . import usage
    if body.month_inr is None and body.month_usd is None:
        raise HTTPException(400, "month_inr ya month_usd dijiye (0 = koi seema nahi)")
    return usage.set_limit(tenant, month_usd=body.month_usd, month_inr=body.month_inr)


@app.get("/api/usage/all", dependencies=[Depends(require_key)])
def usage_all(days: int = 30, tenant: str = Depends(current_tenant)):
    """The server owner's view: spend per owner (counts only). Only for the main account."""
    from . import usage
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "Sirf server ke maalik ke liye")
    return {"tenants": usage.all_tenants(days), "usd_inr": usage.usd_inr()}


@app.websocket("/api/voice/ws")
async def voice_ws(ws: WebSocket, conv: str = "", voice: str = "", lang: str = "hi-IN", resume: str = ""):
    """Realtime voice call (Baat tab). See app/voice.py for the protocol. `resume` re-joins a call whose phone
    connection dropped (network change) instead of starting a new one."""
    from . import voice as v
    st = get_settings()
    got = ws.headers.get("authorization", "").removeprefix("Bearer ").strip() or ws.query_params.get("key", "")
    # v0.142 browsers can't set headers on a WebSocket: the console sends "hoola, hoola-key.<token>" as subprotocols
    protos = [p.strip() for p in ws.headers.get("sec-websocket-protocol", "").split(",") if p.strip()]
    sub = "hoola" if "hoola" in protos else None
    if not got:
        got = next((p[len("hoola-key."):] for p in protos if p.startswith("hoola-key.")), "")
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
    await ws.accept(subprotocol=sub)
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


# ---------------- v0.183.0 Gmail's own settings (vacation / aliases / auto-forward) for the Email screen ----------------
@app.get("/api/mail/settings", dependencies=[Depends(require_key)])
async def mail_settings(account: str = "", tenant: str = Depends(current_tenant)):
    """Read-only view: vacation reply, send-as aliases and auto-forwarding of the (first) Gmail mailbox,
    plus scope_ok = whether this mailbox granted gmail.settings.basic (else a reconnect is needed for settings)."""
    from .mailbox import service as ms
    from .mailbox.base import MailError
    try:
        return await asyncio.to_thread(ms.settings_status, tenant, account or None)
    except MailError as e:
        raise HTTPException(400, str(e))


# ---------------- v0.182.0 rules / watch / mute / snooze (the app's Email screen) ----------------
@app.get("/api/mail/rules", dependencies=[Depends(require_key)])
def mail_rules(tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    return {"rules": sync.rules_list(tenant), "watch": sync.watch_views(tenant), "muted": sync.muted(tenant),
            "snoozed": sync.snooze_list(tenant), "searches": sync.searches_list(tenant)}


class MailRuleIn(BaseModel):
    name: str = ""
    match: dict = {}
    actions: dict = {}


@app.post("/api/mail/rules", dependencies=[Depends(require_key)])
def mail_rule_create(body: MailRuleIn, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    from .mailbox.base import MailError
    try:
        return sync.rule_create(tenant, body.name, body.match, body.actions)
    except MailError as e:
        raise HTTPException(400, str(e))


class MailRuleEdit(BaseModel):
    enabled: bool


@app.patch("/api/mail/rules/{rid}", dependencies=[Depends(require_key)])
def mail_rule_edit(rid: str, body: MailRuleEdit, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    from .mailbox.base import MailError
    try:
        return sync.rule_edit(tenant, rid, body.enabled)
    except MailError as e:
        raise HTTPException(404, str(e))


@app.delete("/api/mail/rules/{rid}", dependencies=[Depends(require_key)])
def mail_rule_remove(rid: str, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    if not sync.rule_delete(tenant, rid):
        raise HTTPException(404, "Rule not found")
    return {"rules": sync.rules_list(tenant)}


class MailWatchIn(BaseModel):
    mode: str
    account: str | None = None


@app.post("/api/mail/watch", dependencies=[Depends(require_key)])
def mail_watch(body: MailWatchIn, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    from .mailbox.base import MailError
    try:
        return {"watch": sync.set_watch_mode(tenant, body.mode, body.account)}
    except MailError as e:
        raise HTTPException(400, str(e))


class MailMuteIn(BaseModel):
    add: str = ""
    clear: bool = False


@app.post("/api/mail/mute", dependencies=[Depends(require_key)])
def mail_mute(body: MailMuteIn, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    return {"muted": sync.mute_edit(tenant, add=[x for x in body.add.split(",") if x.strip()], clear=body.clear)}


@app.delete("/api/mail/snoozes/{sid}", dependencies=[Depends(require_key)])
def mail_snooze_cancel(sid: str, tenant: str = Depends(current_tenant)):
    """Cancel = the mail comes back to the inbox right now (unread)."""
    from .mailbox import sync
    if not sync.snooze_cancel(tenant, sid):
        raise HTTPException(404, "Snooze not found")
    return {"snoozed": sync.snooze_list(tenant)}


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
            "month_spent_usd": ss.month_spent(tenant), "month_limit_usd": st.studio_month_usd, "usd_inr": st.studio_usd_inr,
            "can_paint": bool(st.gemini_api_key), "lyria": ss.lyria_ready(), "voices": list(ss.VOICES),
            "styles": list(ss.catalog.STYLES), "moods": list(ss.MOODS)}


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


class StudioNew(BaseModel):          # v0.157 the app's "Naya video" form
    name: str = Field(min_length=2, max_length=60)
    brief: str = Field(default="", max_length=2000)
    aspect: str = "9:16"
    style: str = "reel"
    language: str = "Hindi"
    seconds: int = Field(default=30, ge=6, le=600)
    voice: str = ""                  # v0.159 male | female
    captions: bool = True
    caption_style: str = "bold"
    music: str = ""                  # a mood (Lyria, paid in the same card) or "" = none
    quality: str = "final"


class StudioPlan(BaseModel):
    brief: str = Field(default="", max_length=2000)
    seconds: int = Field(default=30, ge=6, le=600)


class StudioRun(BaseModel):
    quality: str = "preview"
    shot_ids: list[str] | None = None
    variants: int = Field(default=1, ge=1, le=4)


class StudioPick(BaseModel):
    shot_id: str
    take: int


class StudioShot(BaseModel):
    prompt: str | None = Field(default=None, max_length=1500)
    dialogue: str | None = Field(default=None, max_length=600)
    caption: str | None = Field(default=None, max_length=120)
    duration: int | None = Field(default=None, ge=2, le=30)
    kind: str | None = None
    camera: str | None = None
    characters: list[str] | None = Field(default=None, max_length=6)
    transition: str | None = None
    speaker: str | None = None


class StudioMusic(BaseModel):
    mood: str = "upbeat"
    volume: float = 0.25
    file_id: str = ""                # v0.159 her own licensed song


class StudioVoiceover(BaseModel):
    shot_id: str
    text: str = Field(default="", max_length=600)
    file_id: str = ""


class StudioCharacter(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=400)
    file_ids: list[str] = Field(default_factory=list, max_length=4)
    consent: bool = False
    voice: str = ""
    kind: str = "person"             # v0.159 person | place | product


class StudioSettings(BaseModel):
    voice: str | None = None
    captions: bool | None = None
    caption_style: str | None = None
    music: str | None = None
    quality: str | None = None
    logo_position: str | None = None
    style: str | None = None
    music_volume: float | None = Field(default=None, ge=0, le=1)


class StudioAddShot(BaseModel):
    prompt: str = Field(default="", max_length=1500)
    duration: int = Field(default=5, ge=2, le=30)
    kind: str = "scene"
    camera: str | None = None
    dialogue: str | None = Field(default=None, max_length=600)
    caption: str | None = Field(default=None, max_length=120)
    characters: list[str] = Field(default_factory=list, max_length=6)
    after: str = ""


class StudioRedo(BaseModel):
    change: str = Field(default="", max_length=300)
    quality: str = ""


class StudioImprove(BaseModel):
    brief: str = Field(min_length=1, max_length=2000)
    language: str = "Hindi"
    seconds: int = Field(default=30, ge=6, le=600)


class StudioLogo(BaseModel):
    file_id: str
    position: str = "top-right"


def _studio_call(fn):
    async def run(*a, **k):
        from .studio import service as ss
        try:
            return await fn(*a, **k)
        except (ss.StudioJobError, ss.StudioError) as e:
            raise HTTPException(400, str(e))
    return run


@app.post("/api/studio/projects", dependencies=[Depends(require_key)])
async def studio_new(body: StudioNew, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    v = await _studio_call(ss.create)(tenant, body.name, body.aspect, body.style, body.language, body.brief, "",
                                      {"voice": body.voice, "captions": body.captions, "caption_style": body.caption_style,
                                       "music": body.music, "quality": body.quality})
    if body.brief.strip():
        await _studio_call(ss.plan)(tenant, v["project"], body.brief, body.seconds, "")
    return ss.view(tenant, ss._load(tenant, v["project"]))


@app.post("/api/studio/projects/{name}/plan", dependencies=[Depends(require_key)])
async def studio_plan(name: str, body: StudioPlan, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.plan)(tenant, name, body.brief, body.seconds, "")


@app.post("/api/studio/projects/{name}/keyframes", dependencies=[Depends(require_key)])
async def studio_keyframes(name: str, body: StudioRun, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.keyframes)(tenant, name, body.shot_ids)


@app.post("/api/studio/projects/{name}/generate", dependencies=[Depends(require_key)])
async def studio_generate(name: str, body: StudioRun, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.generate)(tenant, name, body.quality, body.shot_ids, body.variants, None, "")


@app.post("/api/studio/projects/{name}/pick", dependencies=[Depends(require_key)])
async def studio_pick(name: str, body: StudioPick, tenant: str = Depends(current_tenant)):
    from .studio import service as ss

    async def go():
        st = await ss.studio(tenant)
        r = st.pick(name, body.shot_id, body.take)
        ss._changed(tenant, name)
        return r
    return await _studio_call(go)()


@app.patch("/api/studio/projects/{name}/shots/{shot_id}", dependencies=[Depends(require_key)])
async def studio_shot(name: str, shot_id: str, body: StudioShot, tenant: str = Depends(current_tenant)):
    from .studio import service as ss

    async def go():
        st = await ss.studio(tenant)
        st.shot_update(name, shot_id, body.model_dump(exclude_none=True))
        ss._changed(tenant, name)
        return ss.view(tenant, ss._load(tenant, name))
    return await _studio_call(go)()


@app.post("/api/studio/projects/{name}/music", dependencies=[Depends(require_key)])
async def studio_music(name: str, body: StudioMusic, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.music)(tenant, name, body.mood, body.file_id, body.volume)


@app.post("/api/studio/projects/{name}/voiceover", dependencies=[Depends(require_key)])
async def studio_voiceover(name: str, body: StudioVoiceover, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    await _studio_call(ss.voiceover)(tenant, name, body.shot_id, body.text, body.file_id)
    return ss.view(tenant, ss._load(tenant, name))


@app.post("/api/studio/projects/{name}/characters", dependencies=[Depends(require_key)])
async def studio_character(name: str, body: StudioCharacter, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    if body.file_ids:
        return await _studio_call(ss.character)(tenant, name, body.name, body.description, body.file_ids, body.consent, body.voice,
                                                body.kind)
    return await _studio_call(ss.character_generate)(tenant, name, body.name, body.description, body.kind, body.voice)


@app.post("/api/studio/projects/{name}/settings", dependencies=[Depends(require_key)])
async def studio_settings(name: str, body: StudioSettings, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.settings)(tenant, name, body.model_dump(exclude_none=True))


@app.post("/api/studio/projects/{name}/shots", dependencies=[Depends(require_key)])
async def studio_add_shot(name: str, body: StudioAddShot, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    d = body.model_dump(exclude_none=True)
    after = d.pop("after", "")
    return await _studio_call(ss.add_shot)(tenant, name, d, after)


@app.delete("/api/studio/projects/{name}/shots/{shot_id}", dependencies=[Depends(require_key)])
async def studio_delete_shot(name: str, shot_id: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.delete_shot)(tenant, name, shot_id)


@app.post("/api/studio/projects/{name}/shots/{shot_id}/redo", dependencies=[Depends(require_key)])
async def studio_redo_shot(name: str, shot_id: str, body: StudioRedo, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.redo_shot)(tenant, name, shot_id, body.change, body.quality)


@app.post("/api/studio/projects/{name}/shots/{shot_id}/line", dependencies=[Depends(require_key)])
async def studio_line(name: str, shot_id: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.speak_line)(tenant, name, shot_id)


@app.post("/api/studio/projects/{name}/cancel", dependencies=[Depends(require_key)])
async def studio_cancel(name: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.cancel)(tenant, name)


@app.post("/api/studio/projects/{name}/logo", dependencies=[Depends(require_key)])
async def studio_logo(name: str, body: StudioLogo, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    await _studio_call(ss.logo)(tenant, name, body.file_id, body.position)
    return ss.view(tenant, ss._load(tenant, name))


@app.delete("/api/studio/projects/{name}", dependencies=[Depends(require_key)])
async def studio_hide(name: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.hide)(tenant, name)


@app.post("/api/studio/improve", dependencies=[Depends(require_key)])
async def studio_improve(body: StudioImprove):
    from .studio import service as ss
    return await _studio_call(ss.improve_brief)(body.brief, body.language, body.seconds)


@app.get("/api/studio/voice_sample", dependencies=[Depends(require_key)])
async def studio_voice_sample(voice: str = "male", language: str = "Hindi", tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.voice_sample)(tenant, voice, language)


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
def net_business_verify(body: TicketIn, udyam: str = "", tenant: str = Depends(current_tenant)):
    from .net import business as biz
    return _net(biz.request_verification, tenant, body.note, udyam)


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
def net_operator_verify(biz_tenant: str, body: NetAnswerIn, bank_name_ok: bool = False,
                        tenant: str = Depends(current_tenant)):
    from .net import business as biz
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "Sirf server operator")
    return _net(biz.operator_verify, biz_tenant, body.action == "approve", bank_name_ok)


# ---------------------------------------------------------------- v0.102 Hoola Deals (buy / sell between avatars)
class DealAskIn(BaseModel):
    to: str
    items: list = Field(default_factory=list)
    mode: str = "pickup"
    need_by: str = ""
    note: str = ""
    title: str = ""
    area: str = ""


class DealActIn(BaseModel):
    lines: list | None = None
    note: str = ""
    reason: str = ""
    valid_minutes: int | None = None
    ready_by: str = ""
    place: str = ""
    minutes: int | None = None
    code: str = ""
    v: int | None = None
    mode: str = ""
    proof: dict | None = None
    # v0.106 money / dispute
    amount: float | None = None
    utr: str = ""
    collect: dict | None = None
    pay: str = ""
    resolution: str = ""
    accept: bool = True
    yes: bool = False
    items: list | None = None
    # v0.113 bookings / job card
    slot: str = ""
    address: str = ""
    slots: list | None = None
    estimate: dict | None = None
    eta_minutes: int | None = None
    summary: str = ""
    warranty_days: int | None = None
    covers: str = ""
    purpose: str = "resched"
    ids_yes: list | None = None
    ids_no: list | None = None


class StockIn(BaseModel):
    items: list = Field(default_factory=list)


@app.get("/api/net/deals", dependencies=[Depends(require_key)])
def net_deals(state: str = "", role: str = "", tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return {"deals": dl.deals(tenant, state, role)}


@app.post("/api/net/deals", dependencies=[Depends(require_key)])
def net_deal_ask(body: DealAskIn, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return _net(dl.ask, tenant, body.to, body.items, body.mode, body.need_by, body.note, body.title, body.area)


@app.get("/api/net/deals/catalog", dependencies=[Depends(require_key)])
def net_deal_catalog(to: str, tenant: str = Depends(current_tenant)):
    """v0.105 a seller's price list, asked through her avatar (only what that seller shares)."""
    from .net import deal as dl
    return _net(dl.catalog_of, tenant, to)


@app.get("/api/net/deals/{deal_id}", dependencies=[Depends(require_key)])
def net_deal_get(deal_id: str, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return _net(dl.show, tenant, deal_id)


@app.post("/api/net/deals/{deal_id}/{action}", dependencies=[Depends(require_key)])
def net_deal_act(deal_id: str, action: str, body: DealActIn, tenant: str = Depends(current_tenant)):
    """Her taps on a deal card. `confirm` is the only way an order is placed (fingerprint-signed once a phone is set up)."""
    from .net import deal as dl
    if action == "confirm":
        _fingerprint(tenant, "deal", deal_id, body.proof)
        return _net(dl.confirm, tenant, deal_id, body.v, body.mode, by_tap=True, pay=body.pay, slot=body.slot,
                    address=body.address)
    if action == "send_quote":
        return _net(dl.send_quote, tenant, deal_id, body.lines, body.note, body.valid_minutes, slots=body.slots,
                    estimate=body.estimate)
    if action == "accept":
        return _net(dl.accept, tenant, deal_id, body.ready_by, body.note)
    if action == "reject":
        return _net(dl.reject, tenant, deal_id, body.reason or body.note)
    if action == "packing":
        return _net(dl.packing, tenant, deal_id, body.note)
    if action == "ready":
        return _net(dl.mark_ready, tenant, deal_id, body.place, body.minutes, body.note)
    if action == "handed_over":
        return _net(dl.handed_over, tenant, deal_id, body.code, body.note, body.collect)
    if action == "cancel":
        return _net(dl.cancel, tenant, deal_id, body.reason or body.note)
    from .net import dealpay as dp                       # v0.106 money, cancel requests, the check, disputes
    from .net import mandate as md                       # v0.112 "is baar rok do" on a standing-order run
    from .net import job as jb                           # v0.113 the service job card
    acts = {
        "pay_link": lambda: dp.pay_link(tenant, deal_id),
        "trust_payee": lambda: dp.trust_payee(tenant, deal_id),
        "paid": lambda: dp.claim_paid(tenant, deal_id, body.utr),
        "pay_request": lambda: dp.request_payment(tenant, deal_id, body.amount),
        "received": lambda: dp.received(tenant, deal_id, body.amount, body.mode or "upi", body.utr),
        "refund": lambda: dp.refund(tenant, deal_id, body.amount, body.utr),
        "ok": lambda: dp.all_ok(tenant, deal_id),
        "dispute": lambda: dp.dispute(tenant, deal_id, body.reason or "other", body.items, body.note),
        "resolve": lambda: dp.resolve(tenant, deal_id, body.resolution, body.amount, body.note),
        "dispute_close": lambda: dp.dispute_close(tenant, deal_id, body.accept, body.note),
        "cancel_answer": lambda: dp.cancel_answer(tenant, deal_id, body.yes, body.note),
        "standing_hold": lambda: md.hold_once(tenant, deal_id),
        # v0.113 job card (approve / pick_slot = her tap here)
        "on_the_way": lambda: jb.on_the_way(tenant, deal_id, body.eta_minutes, body.note),
        "arrived": lambda: jb.arrived(tenant, deal_id, body.note),
        "estimate": lambda: jb.estimate(tenant, deal_id, body.lines or body.items),
        "approve": lambda: jb.approve(tenant, deal_id, body.ids_yes, body.ids_no, by_tap=True),
        "done": lambda: jb.done(tenant, deal_id, body.summary or body.note, body.warranty_days, body.covers),
        "offer_slots": lambda: jb.offer_slots(tenant, deal_id, body.purpose, body.slots),
        "pick_slot": lambda: jb.pick_slot(tenant, deal_id, body.slot, by_tap=True),
        "resched": lambda: jb.ask_resched(tenant, deal_id, body.note),
        "warranty": lambda: jb.claim(tenant, deal_id, body.note),
        "warranty_done": lambda: jb.warranty_done(tenant, deal_id, body.summary or body.note),
    }
    if action in acts:
        return _net(acts[action])
    raise HTTPException(400, "action: confirm, send_quote, accept, reject, packing, ready, handed_over, cancel, "
                             + ", ".join(acts))


@app.post("/api/net/deals/{deal_id}/photo", dependencies=[Depends(require_key)])
async def net_deal_photo(deal_id: str, file: UploadFile = File(...), stage: str = Form("after"),
                         tenant: str = Depends(current_tenant)):
    """v0.113 a proof photo of the work (camera / gallery) -> kept for the job + sent to the customer's Hoola."""
    from .net import job as jb
    data = await file.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "Photo 12 MB se badi hai.")
    return _net(jb.add_photo, tenant, deal_id, data, file.filename or "photo.jpg", stage)


@app.get("/api/net/deals/{deal_id}/photos/{pid}", dependencies=[Depends(require_key)])
def net_deal_photo_get(deal_id: str, pid: str, tenant: str = Depends(current_tenant)):
    from .net import job as jb
    return FileResponse(_net(jb.photo_file, tenant, deal_id, pid), media_type="image/jpeg")


class BookIn(BaseModel):
    to: str
    what: str
    items: list = Field(default_factory=list)
    when: str = ""
    area: str = ""
    note: str = ""
    at: str = ""


@app.post("/api/net/bookings", dependencies=[Depends(require_key)])
def net_book(body: BookIn, tenant: str = Depends(current_tenant)):
    """v0.113 ask a service / appointment (only the work, area and preferred time go; the address only at booking)."""
    from .net import deal as dl
    return _net(dl.ask, tenant, body.to, body.items, "pickup", "", body.note, "", body.area,
                service={"what": body.what, "when": body.when, "area": body.area, "at": body.at})


@app.get("/api/net/bookings", dependencies=[Depends(require_key)])
def net_bookings(role: str = "", tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return {"bookings": [d for d in dl.deals(tenant, "", role, 120) if d.get("service")]}


@app.get("/api/net/service_rules", dependencies=[Depends(require_key)])
def net_service_rules(tenant: str = Depends(current_tenant)):
    from .net import booking as bk
    return bk.rules_view(tenant) | {"free_slots": bk.free_slots(tenant)}


@app.put("/api/net/service_rules", dependencies=[Depends(require_key)])
def net_service_rules_put(body: dict, tenant: str = Depends(current_tenant)):
    from .net import booking as bk
    allowed = ("days", "open_at", "close_at", "slot_minutes", "capacity", "lead_minutes", "horizon_days", "visit_fee",
               "visit_gst", "visit_adjust", "at", "warranty_days", "prefix", "closed_on")
    return _net(bk.set_rules, tenant, **{k: body[k] for k in allowed if k in body})


@app.get("/api/net/deals/{deal_id}/receipt.pdf", dependencies=[Depends(require_key)])
def net_deal_receipt(deal_id: str, tenant: str = Depends(current_tenant)):
    """v0.106 the bill + receipts of one deal, made from this side's own record."""
    from .net import dealpay as dp
    pdf = _net(dp.receipt_pdf, tenant, deal_id)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="hoola-{deal_id}.pdf"'})


class KhataIn(BaseModel):
    to: str
    limit: float | None = None
    days: int | None = None
    status: str = "active"
    amount: float | None = None
    mode: str = "upi"
    utr: str = ""


# ---------------------------------------------------------------- v0.112 compare, trust, standing orders, offers
class RfqIn(BaseModel):
    to: list = Field(default_factory=list)
    items: list = Field(default_factory=list)
    mode: str = "pickup"
    need_by: str = ""
    note: str = ""
    title: str = ""
    window_minutes: int | None = None
    on: bool = True


@app.post("/api/net/rfqs", dependencies=[Depends(require_key)])
def net_rfq_start(body: RfqIn, tenant: str = Depends(current_tenant)):
    from .net import rfq as rq
    return _net(rq.start, tenant, body.to, body.items, body.mode, body.need_by, body.note, body.title, body.window_minutes)


@app.get("/api/net/rfqs", dependencies=[Depends(require_key)])
def net_rfqs(all: bool = False, tenant: str = Depends(current_tenant)):
    from .net import rfq as rq
    return {"compares": rq.rfqs(tenant, not all)}


@app.get("/api/net/rfqs/{rfq_id}", dependencies=[Depends(require_key)])
def net_rfq(rfq_id: str, tenant: str = Depends(current_tenant)):
    from .net import rfq as rq
    return _net(rq.show, tenant, rfq_id)


@app.post("/api/net/rfqs/{rfq_id}/{action}", dependencies=[Depends(require_key)])
def net_rfq_act(rfq_id: str, action: str, body: RfqIn, tenant: str = Depends(current_tenant)):
    from .net import rfq as rq
    if action == "split":
        return _net(rq.set_split, tenant, rfq_id, body.on)
    if action == "close":
        return _net(rq.close, tenant, rfq_id)
    raise HTTPException(400, "action: split, close")


class TrustIn(BaseModel):
    to: str
    level: str = "trusted"
    reason: str = "spam"
    kind: str = ""


@app.get("/api/net/trust", dependencies=[Depends(require_key)])
def net_trust(to: str, tenant: str = Depends(current_tenant)):
    from .net import service as net
    from .net import trust as tr
    peer = _net(net.resolve, tenant, to) if not to.startswith("hl_") else to
    return tr.tier(tenant, peer)


@app.put("/api/net/trust", dependencies=[Depends(require_key)])
def net_trust_put(body: TrustIn, tenant: str = Depends(current_tenant)):
    from .net import trust as tr
    return _net(tr.set_trust, tenant, body.to, body.level)


@app.post("/api/net/trust/report", dependencies=[Depends(require_key)])
def net_trust_report(body: TrustIn, tenant: str = Depends(current_tenant)):
    from .net import trust as tr
    return _net(tr.report, tenant, body.to, body.reason, body.kind)


class MandateIn(BaseModel):
    to: str = ""
    items: list = Field(default_factory=list)
    days: list | str = Field(default_factory=list)
    at: str = "09:00"
    max_total: float | None = None
    until: str = ""
    tolerance_pct: float | None = None
    pay: str = ""
    hold_minutes: int | None = None
    title: str = ""
    mode: str = "pickup"
    proof: dict | None = None


@app.get("/api/net/mandates", dependencies=[Depends(require_key)])
def net_mandates(tenant: str = Depends(current_tenant)):
    from .net import mandate as md
    return {"standing_orders": md.mandates(tenant)}


@app.post("/api/net/mandates", dependencies=[Depends(require_key)])
def net_mandate_create(body: MandateIn, tenant: str = Depends(current_tenant)):
    from .net import mandate as md
    return _net(md.create, tenant, body.to, body.items, body.days, body.at, body.max_total, body.until, body.tolerance_pct,
                body.pay, body.hold_minutes, body.title, body.mode)


@app.post("/api/net/mandates/{mid}/{action}", dependencies=[Depends(require_key)])
def net_mandate_act(mid: str, action: str, body: MandateIn, tenant: str = Depends(current_tenant)):
    """`sign` / `resume` = HER tap that turns the rule on (fingerprint-signed once a phone is set up)."""
    from .net import mandate as md
    if action in ("sign", "resume"):
        _fingerprint(tenant, "mandate", mid, body.proof)
        return _net(md.sign, tenant, mid, by_tap=True)
    if action in ("pause", "stop"):
        return _net(md.set_state, tenant, mid, action)
    if action == "run":
        return _net(md.run_now, tenant, mid)
    raise HTTPException(400, "action: sign, pause, resume, stop, run")


class PromoIn(BaseModel):
    to: str = ""
    title: str = ""
    text: str = ""
    items: list | None = None
    valid_days: int = 7


@app.get("/api/net/promos", dependencies=[Depends(require_key)])
def net_promos(tenant: str = Depends(current_tenant)):
    from .net import promo as pr
    return {"offers": pr.inbox(tenant), "opted_in": pr.my_optins(tenant)}


@app.get("/api/net/promos/audience", dependencies=[Depends(require_key)])
def net_promo_audience(tenant: str = Depends(current_tenant)):
    from .net import promo as pr
    return pr.audience(tenant)


@app.post("/api/net/promos/{action}", dependencies=[Depends(require_key)])
def net_promo_act(action: str, body: PromoIn, tenant: str = Depends(current_tenant)):
    """optin / optout (the buyer), preview / send (the seller; send = her tap)."""
    from .net import promo as pr
    if action == "optin":
        return _net(pr.opt_in, tenant, body.to)
    if action == "optout":
        return _net(pr.opt_out, tenant, body.to)
    if action == "preview":
        return _net(pr.preview, tenant, body.title, body.text, body.items, body.valid_days)
    if action == "send":
        return _net(pr.send_offer, tenant, body.title, body.text, body.items, body.valid_days, by_tap=True)
    raise HTTPException(400, "action: optin, optout, preview, send")


@app.post("/api/net/promos/{promo_id}/{action}", dependencies=[Depends(require_key)])
def net_promo_item(promo_id: str, action: str, body: PromoIn, tenant: str = Depends(current_tenant)):
    from .net import promo as pr
    if action == "order":
        return _net(pr.order_from, tenant, promo_id, body.items)
    if action == "dismiss":
        return _net(pr.dismiss, tenant, promo_id)
    raise HTTPException(400, "action: order, dismiss")


class DostiIn(BaseModel):
    on: bool | None = None
    who: str | None = None
    chosen: list[str] | None = None
    share_work: bool | None = None
    share_skills: bool | None = None
    share_videos: str | None = None
    daily_max: int | None = None
    to: str = ""
    text: str = ""
    thread_id: str = ""
    share: bool = False
    what: str = ""
    why: str = ""
    action: str = ""
    file_id: str = ""
    status: str | None = None
    shared: bool | None = None
    title: str | None = None
    summary: str | None = None
    learned: str | None = None
    category: str = "other"


@app.get("/api/net/dosti", dependencies=[Depends(require_key)])
def net_dosti(tenant: str = Depends(current_tenant)):
    """v0.160 Dosti: her setting, the work diary, friends' chats, what friends shared, doc requests."""
    from .net import dosti as ds
    _net(ds.sync, tenant)
    return ds.overview(tenant)


@app.put("/api/net/dosti", dependencies=[Depends(require_key)])
def net_dosti_set(body: DostiIn, tenant: str = Depends(current_tenant)):
    from .net import dosti as ds
    return _net(ds.set_settings, tenant, on=body.on, who=body.who, chosen=body.chosen, share_work=body.share_work,
                share_skills=body.share_skills, share_videos=body.share_videos, daily_max=body.daily_max)


@app.post("/api/net/dosti/{action}", dependencies=[Depends(require_key)])
def net_dosti_act(action: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    """talk (to | thread_id, text, share) / doc_ask (to, what, why) / diary (add: title, summary, learned, category) /
    share_now / sync."""
    from .net import dosti as ds
    if action == "talk":
        return _net(ds.talk, tenant, body.to, body.text, body.thread_id, body.share)
    if action == "doc_ask":
        return _net(ds.ask_doc, tenant, body.to, body.what, body.why)
    if action == "diary":
        return _net(ds.add_experience, tenant, body.title or "", body.summary or "", body.learned or "", body.category)
    if action == "share_now":
        return {"friends_told": _net(ds.share_learnings, tenant, True)}
    if action == "sync":
        return {"new": _net(ds.sync, tenant, 10)}
    raise HTTPException(400, "action: talk, doc_ask, diary, share_now, sync")


@app.post("/api/net/dosti/threads/{thread_id}/{action}", dependencies=[Depends(require_key)])
def net_dosti_thread(thread_id: str, action: str, tenant: str = Depends(current_tenant)):
    from .net import dosti as ds
    if action not in ("pause", "resume"):
        raise HTTPException(400, "action: pause, resume")
    return _net(ds.pause, tenant, thread_id, action == "pause")


@app.patch("/api/net/dosti/diary/{exp_id}", dependencies=[Depends(require_key)])
def net_dosti_diary(exp_id: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    from .net import dosti as ds
    return _net(ds.update_experience, tenant, exp_id, status=body.status, shared=body.shared, title=body.title,
                summary=body.summary, learned=body.learned)


@app.post("/api/net/dosti/diary/{exp_id}/{action}", dependencies=[Depends(require_key)])
def net_dosti_video(exp_id: str, action: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    """video = make the explainer video of this skill; send_video = to a friend (this tap is her consent)."""
    from .net import dosti as ds
    if action == "video":
        return _net(ds.make_video, tenant, exp_id)
    if action == "send_video":
        return _net(ds.send_video, tenant, exp_id, body.to, by_tap=True)
    raise HTTPException(400, "action: video, send_video")


@app.post("/api/net/dosti/docs/{ask_id}", dependencies=[Depends(require_key)])
def net_dosti_doc(ask_id: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    """Her tap on a document request: send (file_id) or decline. The only way a requested document goes out."""
    from .net import dosti as ds
    return _net(ds.doc_answer, tenant, ask_id, body.action, body.file_id, by_tap=True)


@app.post("/api/net/dosti/items/{item_id}", dependencies=[Depends(require_key)])
def net_dosti_item(item_id: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    """Her yes / no on a skill a friend's avatar shared (learn | decline)."""
    from .net import dosti as ds
    return _net(ds.item_answer, tenant, item_id, body.action, by_tap=True)


@app.get("/api/net/khata", dependencies=[Depends(require_key)])
def net_khata(tenant: str = Depends(current_tenant)):
    from .net import khata as kh
    return kh.book(tenant)


@app.post("/api/net/khata/{action}", dependencies=[Depends(require_key)])
def net_khata_act(action: str, body: KhataIn, tenant: str = Depends(current_tenant)):
    from .net import khata as kh
    acts = {
        "open": lambda: kh.open_account(tenant, body.to, body.limit if body.limit is not None else 0, body.days or 15,
                                        body.status),
        "request": lambda: kh.request(tenant, body.to, body.amount),
        "received": lambda: kh.received(tenant, body.to, body.amount, body.mode, body.utr),
        "pay_link": lambda: kh.pay_link(tenant, body.to),
        "trust_payee": lambda: kh.trust_payee(tenant, body.to),
        "paid": lambda: kh.claim_paid(tenant, body.to, body.utr),
    }
    if action not in acts:
        raise HTTPException(400, "action: " + ", ".join(acts))
    return _net(acts[action])


@app.get("/api/net/stock", dependencies=[Depends(require_key)])
def net_stock(q: str = "", tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return {"stock": dl.stock(tenant, q), "rules": dl.rules_view(tenant)}


@app.put("/api/net/stock", dependencies=[Depends(require_key)])
def net_stock_put(body: StockIn, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return _net(dl.set_stock, tenant, body.items)


@app.delete("/api/net/stock/{item}", dependencies=[Depends(require_key)])
def net_stock_delete(item: str, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return _net(dl.remove_stock, tenant, item)


@app.post("/api/net/stock/import", dependencies=[Depends(require_key)])
async def net_stock_import(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "File 10 MB se badi hai.")
    return _net(dl.import_stock, tenant, file.filename or "stock.csv", data)


class PickActIn(BaseModel):
    short: list | None = None
    code: str = ""
    note: str = ""
    collect: dict | None = None


@app.get("/api/net/picks", dependencies=[Depends(require_key)])
def net_picks(all: bool = False, tenant: str = Depends(current_tenant)):
    from .net import pick as pk
    return {"picks": pk.picks(tenant, not all)}


@app.post("/api/net/picks/{pick_id}/{action}", dependencies=[Depends(require_key)])
def net_pick_act(pick_id: str, action: str, body: PickActIn, tenant: str = Depends(current_tenant)):
    from .net import pick as pk
    if action in ("packing", "packed", "short"):
        return _net(pk.mark, tenant, pick_id, action, body.short, body.note)
    if action == "handover":
        return _net(pk.handover, tenant, pick_id, body.code, body.collect)
    raise HTTPException(400, "action: packing, packed, short, handover")


@app.get("/api/net/deal_rules", dependencies=[Depends(require_key)])
def net_deal_rules(tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return dl.rules_view(tenant)


@app.put("/api/net/deal_rules", dependencies=[Depends(require_key)])
def net_deal_rules_put(body: dict, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    allowed = ("auto_quote", "auto_quote_max", "auto_accept", "auto_accept_max", "valid_minutes", "place", "pickup_minutes",
               "prefix", "trusted", "catalog", "show_stock", "auto_ready", "packers", "pay_before", "counter_ok", "khata",
               "cancel_minutes", "dispute_hours", "upi_id", "payee_name", "auto_accept_who")
    return _net(dl.set_rules, tenant, **{k: body[k] for k in allowed if k in body})


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
    from .net import a2a
    return a2a.agent_card()


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


async def _a2a_call(request: Request, v1: bool):
    from .net import a2a
    if not get_settings().a2a_inbound:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32004, "message": "A2A is off on this server"}})
    raw = await request.body()
    if len(raw) > 256 * 1024:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Request too large"}})
    try:
        body = json.loads(raw.decode() or "null")
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
    ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "")
    out = await asyncio.to_thread(a2a.rpc, body, dict(request.headers), ip, v1,
                                  request.query_params.get("A2A-Version", ""))
    return JSONResponse(out, headers={"A2A-Version": "1.0" if v1 else "0.3"})


@app.post("/a2a")
async def hoola_a2a(request: Request):
    """A2A 0.3 names (message/send, tasks/get, tasks/cancel) and 1.0 names both work here (v0.116)."""
    return await _a2a_call(request, False)


@app.post("/a2a/v1")
async def hoola_a2a_v1(request: Request):
    """v0.116 A2A 1.0 JSON-RPC (SendMessage, GetTask, ListTasks, CancelTask)."""
    return await _a2a_call(request, True)


@app.get("/a2a/help", response_class=PlainTextResponse)
def hoola_a2a_help():
    from .net import a2a
    return a2a.help_text()


# ---------------- v0.116 A2A 1.0 (her side), hand-offs (AA, ABDM, DigiLocker), ONDC listing ----------------
def _ho(fn, *a, **kw):
    from .handoff.aa import HandoffError
    from .net import service as net
    try:
        return fn(*a, **kw)
    except (net.NetError, HandoffError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/a2a", dependencies=[Depends(require_key)])
def a2a_home(tenant: str = Depends(current_tenant)):
    from .net import a2a
    from .net import federation as fed
    return {"mode": a2a.mode(tenant), "tasks": a2a.tasks(tenant), "outs": a2a.outs(tenant),
            "card": fed.my_base() + "/.well-known/agent-card.json", "endpoint": fed.my_base() + "/a2a/v1"}


@app.put("/api/a2a/mode", dependencies=[Depends(require_key)])
def a2a_mode(body: dict, tenant: str = Depends(current_tenant)):
    from .net import a2a
    return _ho(a2a.set_mode, tenant, str(body.get("mode") or ""))


@app.get("/api/a2a/tasks/{tid}", dependencies=[Depends(require_key)])
def a2a_task(tid: str, tenant: str = Depends(current_tenant)):
    from .net import a2a
    return _ho(a2a.show, tenant, tid)


@app.post("/api/a2a/tasks/{tid}/{action}", dependencies=[Depends(require_key)])
def a2a_task_act(tid: str, action: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """Her taps on an outside agent's request: reply / quote / accept / reject / ready / handed_over / cancel."""
    from .net import a2a
    b = body or {}
    acts = {"reply": lambda: a2a.reply(tenant, tid, str(b.get("text") or ""), by_tap=True),
            "draft_reply": lambda: a2a.prepare_reply(tenant, tid, str(b.get("text") or "")),
            "quote": lambda: a2a.send_quote(tenant, tid, b.get("lines"), str(b.get("note") or ""), b.get("valid_minutes")),
            "accept": lambda: a2a.accept(tenant, tid, str(b.get("note") or "")),
            "reject": lambda: a2a.reject(tenant, tid, str(b.get("reason") or "")),
            "ready": lambda: a2a.mark_ready(tenant, tid, str(b.get("place") or "")),
            "handed_over": lambda: a2a.handed_over(tenant, tid, str(b.get("code") or "")),
            "cancel": lambda: a2a.cancel_order(tenant, tid, str(b.get("reason") or ""))}
    if action not in acts:
        raise HTTPException(404, "action")
    return _ho(acts[action])


@app.post("/api/a2a/discover", dependencies=[Depends(require_key)])
def a2a_discover(body: dict, tenant: str = Depends(current_tenant)):
    from .net import a2a
    return _ho(a2a.discover, str(body.get("url") or ""))


@app.post("/api/a2a/out", dependencies=[Depends(require_key)])
def a2a_out_new(body: dict, tenant: str = Depends(current_tenant)):
    from .net import a2a
    return _ho(a2a.draft, tenant, str(body.get("url") or ""), str(body.get("text") or ""), body.get("data"),
               str(body.get("task_of") or ""))


@app.post("/api/a2a/out/{oid}/{action}", dependencies=[Depends(require_key)])
def a2a_out_act(oid: str, action: str, tenant: str = Depends(current_tenant)):
    """'Bhejo' (her tap) / drop / poll a message to an outside agent."""
    from .net import a2a
    if action == "send":
        return _ho(a2a.send, tenant, oid, by_tap=True)
    if action == "drop":
        return _ho(a2a.drop, tenant, oid)
    if action == "poll":
        return _ho(a2a.poll, tenant, oid)
    raise HTTPException(404, "action")


@app.get("/api/handoff", dependencies=[Depends(require_key)])
def handoff_home(tenant: str = Depends(current_tenant)):
    from .handoff import aa, abdm, digilocker, ondc
    return {"aa": aa.consents(tenant), "aa_apps": aa.apps(), "abdm": abdm.consents(tenant), "abdm_topics": list(abdm.HELP),
            "digilocker": digilocker.status(tenant), "ondc": ondc.readiness(tenant)}


@app.post("/api/handoff/aa/review", dependencies=[Depends(require_key)])
def handoff_aa_review(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import aa
    keys = ("requester", "for_what", "purpose_code", "fi_types", "data_from", "data_to", "months", "fetch_type", "frequency",
            "consent_mode", "data_life", "expiry", "aa_app", "text")
    return _ho(aa.review, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/handoff/aa/{cid}/mark", dependencies=[Depends(require_key)])
def handoff_aa_mark(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import aa
    return _ho(aa.mark, tenant, cid, str(body.get("status") or ""), body.get("revoke_after_days"))


@app.delete("/api/handoff/aa/{cid}", dependencies=[Depends(require_key)])
def handoff_aa_forget(cid: str, tenant: str = Depends(current_tenant)):
    from .handoff import aa
    return _ho(aa.forget, tenant, cid)


@app.post("/api/handoff/abdm/review", dependencies=[Depends(require_key)])
def handoff_abdm_review(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import abdm
    keys = ("requester", "purpose", "hi_types", "data_from", "data_to", "expiry", "for_whom", "visit")
    return _ho(abdm.review, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/handoff/abdm/{cid}/mark", dependencies=[Depends(require_key)])
def handoff_abdm_mark(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import abdm
    return _ho(abdm.mark, tenant, cid, str(body.get("status") or ""), body.get("revoke_after_days"))


@app.delete("/api/handoff/abdm/{cid}", dependencies=[Depends(require_key)])
def handoff_abdm_forget(cid: str, tenant: str = Depends(current_tenant)):
    from .handoff import abdm
    return _ho(abdm.forget, tenant, cid)


@app.get("/api/handoff/abdm/help", dependencies=[Depends(require_key)])
def handoff_abdm_help(topic: str = "", tenant: str = Depends(current_tenant)):
    from .handoff import abdm
    return abdm.explain(topic)


@app.get("/api/digilocker", dependencies=[Depends(require_key)])
def digilocker_status(tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return digilocker.status(tenant)


@app.post("/api/digilocker/start", dependencies=[Depends(require_key)])
def digilocker_start(body: dict | None = None, tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return _ho(digilocker.start, tenant, str((body or {}).get("doctype") or ""))


@app.get("/api/digilocker/callback", response_class=HTMLResponse)
def digilocker_callback(code: str = "", state: str = "", error: str = ""):
    """DigiLocker sends her back here after she signed in on its own page (public: the random state is the key)."""
    import html as _h
    from .handoff import digilocker
    from .handoff.aa import HandoffError
    try:
        res = digilocker.callback(code, state, error)
        msg = res["say"]
    except HandoffError as e:
        msg = str(e)
    return HTMLResponse("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                        "<title>Hoola · DigiLocker</title><body style='font-family:sans-serif;padding:24px'>"
                        f"<h3>Hoola</h3><p>{_h.escape(msg)}</p><p><a href='santosh://home'>Hoola kholiye</a></p>",
                        headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"})


@app.get("/api/digilocker/issued", dependencies=[Depends(require_key)])
def digilocker_issued(tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return {"issued": _ho(digilocker.issued, tenant)}


@app.post("/api/digilocker/fetch", dependencies=[Depends(require_key)])
def digilocker_fetch(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return _ho(digilocker.fetch, tenant, str(body.get("uri") or ""))


@app.delete("/api/digilocker", dependencies=[Depends(require_key)])
def digilocker_disconnect(tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return _ho(digilocker.disconnect, tenant)


@app.get("/api/ondc", dependencies=[Depends(require_key)])
def ondc_home(tenant: str = Depends(current_tenant)):
    from .handoff import ondc
    return ondc.readiness(tenant) | {"domains": ondc.DOMAINS}


@app.put("/api/ondc", dependencies=[Depends(require_key)])
def ondc_setup(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import ondc
    keys = ("on", "domain", "seller_app", "store_name", "gstin", "fssai", "care", "pincodes", "radius_km", "ship_minutes",
            "returnable", "return_days", "cancellable", "cod", "fulfilment")
    return _ho(ondc.setup, tenant, **{k: body[k] for k in keys if k in body})


@app.put("/api/ondc/items", dependencies=[Depends(require_key)])
def ondc_item(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import ondc
    return _ho(ondc.set_item, tenant, str(body.get("item") or ""), **{k: body[k] for k in ondc.ITEM_KEYS if k in body})


@app.post("/api/ondc/export", dependencies=[Depends(require_key)])
def ondc_export(tenant: str = Depends(current_tenant)):
    from .events import bus
    from .handoff import ondc
    from .net.service import home_conv
    res = _ho(ondc.export, tenant)
    bus.publish(home_conv(tenant), "pc_file", {**res["file"], "source": "ondc"})
    return res


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


from .notebook.api import make_router as _notebook_router  # noqa: E402

app.include_router(_notebook_router(require_key, current_tenant))

from .drive.api import make_router as _drive_router  # noqa: E402
from .forms.api import make_router as _forms_router  # noqa: E402

app.include_router(_drive_router(require_key, current_tenant))
app.include_router(_forms_router(require_key, current_tenant))
from .photos.api import make_router as _photos_router  # noqa: E402

app.include_router(_photos_router(require_key, current_tenant))

# v0.133 Seva suite: 7 customer-support Sahayaks (each module owns its /api/<mod>/* routes)
from .seva.api import make_router as _seva_router  # noqa: E402
from .helpdesk.api import make_router as _helpdesk_router  # noqa: E402
from .shikayat.api import make_router as _shikayat_router  # noqa: E402
from .aftersales.api import make_router as _aftersales_router  # noqa: E402
from .feedback.api import make_router as _feedback_router  # noqa: E402
from .wapsi.api import make_router as _wapsi_router  # noqa: E402
from .samudaay.api import make_router as _samudaay_router  # noqa: E402
from .callcentre.api import make_router as _callcentre_router  # noqa: E402

for _mk in (_seva_router, _helpdesk_router, _shikayat_router, _aftersales_router, _feedback_router, _wapsi_router,
            _samudaay_router, _callcentre_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.137 Tech suite: 9 Technology & software Sahayaks (each module owns its /api/<mod>/* routes; the few public ones
# - ispnoc / devops collectors, docwriter / product published pages - verify their own signature / token in code)
from .devsahayak.api import make_router as _devsahayak_router  # noqa: E402
from .qa.api import make_router as _qa_router  # noqa: E402
from .itadmin.api import make_router as _itadmin_router  # noqa: E402
from .ispnoc.api import make_router as _ispnoc_router  # noqa: E402
from .cyber.api import make_router as _cyber_router  # noqa: E402
from .devops.api import make_router as _devops_router  # noqa: E402
from .docwriter.api import make_router as _docwriter_router  # noqa: E402
from .appreview.api import make_router as _appreview_router  # noqa: E402
from .product.api import make_router as _product_router  # noqa: E402

for _mk in (_devsahayak_router, _qa_router, _itadmin_router, _ispnoc_router, _cyber_router, _devops_router,
            _docwriter_router, _appreview_router, _product_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.139 Safar suite: 7 Logistics, transport & travel Sahayaks (all routes key-protected under /api/<mod>/*; no public routes)
from .customs.api import make_router as _customs_router  # noqa: E402
from .travel.api import make_router as _travel_router  # noqa: E402
from .warehouse.api import make_router as _warehouse_router  # noqa: E402
from .fleet.api import make_router as _fleet_router  # noqa: E402
from .courier.api import make_router as _courier_router  # noqa: E402
from .drivers.api import make_router as _drivers_router  # noqa: E402
from .logistics.api import make_router as _logistics_router  # noqa: E402

for _mk in (_customs_router, _travel_router, _warehouse_router, _fleet_router, _courier_router, _drivers_router, _logistics_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.144 Makaan suite: 6 Real estate & construction Sahayaks (all under /api/<mod>/*, key-protected; the ONLY public routes are
# propagent's listing page /api/propagent/page/{token}[/photo/{n}], which check their own random token)
from .propagent.api import make_router as _propagent_router  # noqa: E402
from .rentdesk.api import make_router as _rentdesk_router  # noqa: E402
from .sitesup.api import make_router as _sitesup_router  # noqa: E402
from .interior.api import make_router as _interior_router  # noqa: E402
from .archassist.api import make_router as _archassist_router  # noqa: E402
from .society.api import make_router as _society_router  # noqa: E402

for _mk in (_propagent_router, _rentdesk_router, _sitesup_router, _interior_router, _archassist_router, _society_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.150 Kanoon suite: 8 Law, compliance & safety Sahayaks (all under /api/<mod>/*, key-protected; no public routes)
from .vakil.api import make_router as _vakil_router  # noqa: E402
from .legalres.api import make_router as _legalres_router  # noqa: E402
from .compliance.api import make_router as _compliance_router  # noqa: E402
from .contracts.api import make_router as _contracts_router  # noqa: E402
from .cosec.api import make_router as _cosec_router  # noqa: E402
from .notary.api import make_router as _notary_router  # noqa: E402
from .pidesk.api import make_router as _pidesk_router  # noqa: E402
from .dpo.api import make_router as _dpo_router  # noqa: E402

for _mk in (_vakil_router, _legalres_router, _compliance_router, _contracts_router, _cosec_router, _notary_router, _pidesk_router, _dpo_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.152 Mehmaan suite: 6 Hospitality, events & tourism Sahayaks (under /api/<mod>/*, key-protected; homestay's router also holds
# the public calendar feed /api/homestay-ical/{tenant}/{token}.ics, which checks its own random token)
from .frontoffice.api import make_router as _frontoffice_router  # noqa: E402
from .eventplan.api import make_router as _eventplan_router  # noqa: E402
from .shaadi.api import make_router as _shaadi_router  # noqa: E402
from .tourguide.api import make_router as _tourguide_router  # noqa: E402
from .homestay.api import make_router as _homestay_router  # noqa: E402
from .banquet.api import make_router as _banquet_router  # noqa: E402

for _mk in (_frontoffice_router, _eventplan_router, _shaadi_router, _tourguide_router, _homestay_router, _banquet_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.156 Kala suite: 10 Media, design & creative Sahayaks (under /api/<mod>/*, key-protected; podcast's router also holds two
# PUBLIC routes that check their own random feed token: GET /api/podcast/feed/{token}.xml and /api/podcast/pub/{token}/{ep}/{name})
from .editdesk.api import make_router as _editdesk_router  # noqa: E402
from .motiondesk.api import make_router as _motiondesk_router  # noqa: E402
from .filmdesk.api import make_router as _filmdesk_router  # noqa: E402
from .patrakar.api import make_router as _patrakar_router  # noqa: E402
from .photoassist.api import make_router as _photoassist_router  # noqa: E402
from .graphic.api import make_router as _graphic_router  # noqa: E402
from .artistmgr.api import make_router as _artistmgr_router  # noqa: E402
from .kitab.api import make_router as _kitab_router  # noqa: E402
from .podcast.api import make_router as _podcast_router  # noqa: E402
from .influencer.api import make_router as _influencer_router  # noqa: E402

for _mk in (_editdesk_router, _motiondesk_router, _filmdesk_router, _patrakar_router, _photoassist_router, _graphic_router,
            _artistmgr_router, _kitab_router, _podcast_router, _influencer_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.141 3D Studio (Blender in a locked box): /api/blender3d/*; the signed file route checks its own signature
from .blender3d.api import make_router as _blender3d_router  # noqa: E402

app.include_router(_blender3d_router(require_key, current_tenant))

# v0.147 Hoola Postgres (her own database: reads READ ONLY, changes only on her tap): /api/pgdb/*
from .pgdb.api import make_router as _pgdb_router  # noqa: E402

app.include_router(_pgdb_router(require_key, current_tenant))

# v0.134 Gyaan (knowledge base / agentic RAG): /api/gyaan/*
from .gyaan.api import make_router as _gyaan_router  # noqa: E402

app.include_router(_gyaan_router(require_key, current_tenant))


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
    from datetime import datetime
    tz = life.tz_of(tenant)
    day_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    with session() as s:
        rows = s.scalars(select(ListItem).where(ListItem.tenant_id == tenant, ListItem.done.is_(False))
                         .order_by(ListItem.list_name, ListItem.id)).all()
        out: dict[str, list[dict]] = {}
        for r in rows:
            out.setdefault(r.list_name, []).append({"id": r.id, "text": r.text})
        # v0.177: what she finished TODAY stays visible — the daily completed feed (tenant-local day)
        done_rows = s.scalars(select(ListItem).where(ListItem.tenant_id == tenant, ListItem.done.is_(True),
                                                     ListItem.done_at >= day_start)
                              .order_by(ListItem.done_at.desc())).all()
        done_today = [{"id": r.id, "text": r.text, "list_name": r.list_name,
                       "done_at": as_utc(r.done_at).isoformat() if r.done_at else None} for r in done_rows]
        return {"lists": out, "done_today": done_today}


@app.post("/api/lists/items/{item_id}/done", dependencies=[Depends(require_key)])
def tick_item(item_id: int, tenant: str = Depends(current_tenant)):
    with session() as s:
        it = s.get(ListItem, item_id)
        if not it or it.tenant_id != tenant:
            raise HTTPException(404, "Item not found")
        it.done = True
        it.done_at = now()          # v0.177: stamped so the daily completed feed can show it
    return get_lists()


@app.post("/api/lists/items/{item_id}/undo", dependencies=[Depends(require_key)])
def undo_item(item_id: int, tenant: str = Depends(current_tenant)):
    """v0.177: ticked the wrong thing? One tap puts it back on the list (and out of done-today)."""
    with session() as s:
        it = s.get(ListItem, item_id)
        if not it or it.tenant_id != tenant:
            raise HTTPException(404, "Item not found")
        it.done = False
        it.done_at = None
    return get_lists()


@app.get("/api/memory", dependencies=[Depends(require_key)])
def get_memory(tenant: str = Depends(current_tenant)):
    facts = life.memory_facts(tenant, 500)
    used = sum(len(f.text) for f in facts if f.pinned)
    return {"facts": [{"id": f.id, "text": f.text, "pinned": bool(f.pinned), "auto": getattr(f, "source", None) == "auto",
                       "created_at": f.created_at.isoformat()}   # v0.165 home "aaj kya seekha" filters today's facts
                      for f in facts],
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


# ---------------- v0.108 Hoola ki yaad (search everything) + Document desk / Sheet Milaan ----------------
@app.get("/api/yaad", dependencies=[Depends(require_key)])
def yaad_search(q: str = "", days: int = 0, kind: str = "", tenant: str = Depends(current_tenant)):
    from . import yaad
    if not q.strip():
        return {"health": yaad.health(tenant), "hits": []}
    return {"hits": yaad.search(tenant, q, 20, days or None, [kind] if kind else None)}


@app.get("/api/docdesk", dependencies=[Depends(require_key)])
def docdesk_all(conv: str = "", tenant: str = Depends(current_tenant)):
    from . import docdesk as dd
    files = dd.job_files(tenant, conv) if conv else dd.job_files(tenant)
    return {"files": [dd._view(f, i) for i, f in enumerate(files, start=1)], "edits": dd.edits(tenant)}


@app.get("/api/docdesk/edits/{edit_id}", dependencies=[Depends(require_key)])
def docdesk_edit(edit_id: str, tenant: str = Depends(current_tenant)):
    from . import docdesk as dd
    try:
        return dd.full_result(tenant, edit_id)
    except dd.DeskError as e:
        raise HTTPException(404, str(e))


class DeskDecideIn(BaseModel):
    yes: bool
    options: dict | None = None


@app.post("/api/docdesk/edits/{edit_id}/decide", dependencies=[Depends(require_key)])
async def docdesk_decide(edit_id: str, body: DeskDecideIn, tenant: str = Depends(current_tenant)):
    """Her tap on a Sheet Milaan / document-edit card: Haan = the new copy goes to her PC's Santosh Inbox (and opens)."""
    from . import docdesk as dd
    try:
        return await dd.decide(tenant, edit_id, body.yes, body.options)
    except dd.DeskError as e:
        raise HTTPException(400, str(e))


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


@app.get("/api/kaam", dependencies=[Depends(require_key)])
async def kaam_get(q: str = "", tenant: str = Depends(current_tenant)):
    """v0.136 the live state of her long jobs (working / waiting for her / done / failed), as Hoola sees it."""
    from . import kaamwatch
    out = await asyncio.to_thread(kaamwatch.status, tenant, q[:80])
    out["stats"] = dict(kaamwatch.STATS)
    return out


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


# ---------------------------------------------------------------- v0.117 Theka Sahayak (contractor)
def _tk(fn, *a, **k):
    from .theka import service as tk
    try:
        return fn(*a, **k)
    except (tk.ThekaError, ValueError) as e:
        raise HTTPException(400, str(e))


_TK_TENDER = ("dept", "portal", "ref", "value", "emd", "emd_mode", "prebid", "last_date", "opening", "status", "have", "our_quote", "l1", "emd_back", "notes")
_TK_PROJECT = ("client", "govt", "agreement_no", "value", "start", "end", "dlp_months", "gst_rate", "retention_pct", "sd_pct", "it_tds_pct", "gst_tds",
               "cess_pct", "mob_advance", "mob_pct", "deviation_pct", "bg_no", "bg_amount", "bg_valid_to", "insurance_valid_to", "completed_on", "status")


@app.get("/api/theka/day", dependencies=[Depends(require_key)])
def theka_day(tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return {**_tk(tk.day, tenant), "settings": tk.settings(tenant), "tenders": tk.tenders(tenant), "projects": tk.projects(tenant),
            "receivables": tk.receivables(tenant)}


@app.post("/api/theka/settings", dependencies=[Depends(require_key)])
def theka_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    keys = ("firm", "gstin", "individual", "udyam", "registration", "registration_valid_to", "address", "morning_time")
    return _tk(tk.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/theka/tenders", dependencies=[Depends(require_key)])
def theka_tender(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.save_tender, tenant, str(body.get("name") or ""), str(body.get("tender") or ""), **{k: body[k] for k in _TK_TENDER if k in body})


@app.post("/api/theka/projects", dependencies=[Depends(require_key)])
def theka_project(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.save_project, tenant, str(body.get("name") or ""), str(body.get("project") or ""), **{k: body[k] for k in _TK_PROJECT if k in body})


@app.get("/api/theka/projects/{pid}", dependencies=[Depends(require_key)])
def theka_project_get(pid: str, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return {**_tk(tk.project_view, tenant, pid), "boq": _tk(tk.boq_items, tenant, pid), "stock": _tk(tk.stock, tenant, pid)}


@app.post("/api/theka/projects/{pid}/boq", dependencies=[Depends(require_key)])
async def theka_boq_upload(pid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    data = await file.read()
    return _tk(tk.boq, tenant, pid, None, data, file.filename or "boq.csv")


@app.post("/api/theka/projects/{pid}/{action}", dependencies=[Depends(require_key)])
def theka_project_act(pid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """measure | ra_bill | material | diary | eot"""
    from .theka import service as tk
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    conv = g("conversation_id")
    if action == "measure":
        return _tk(tk.measure, tenant, pid, g("item"), body.get("qty"), g("detail"), g("day"), g("by"))
    if action == "ra_bill":
        return _tk(tk.ra_bill, tenant, pid, g("upto"), bool(body.get("final")), conv)
    if action == "material":
        return _tk(tk.material, tenant, pid, g("item"), body.get("qty"), body.get("rate"), bool(body.get("used")), g("day"), g("note"))
    if action == "diary":
        return _tk(tk.diary, tenant, pid, body.get("labour") or 0, g("work"), g("hindrance"), body.get("lost_hours"), bool(body.get("by_client")), g("day"))
    if action == "eot":
        return _tk(tk.eot_letter, tenant, pid, conv)
    raise HTTPException(404, "measure | ra_bill | material | diary | eot")


@app.post("/api/theka/bills/{bid}", dependencies=[Depends(require_key)])
def theka_bill_status(bid: str, body: dict, tenant: str = Depends(current_tenant)):
    """status submitted (her Haan, only from her tap) | passed | paid"""
    from .theka import service as tk
    return _tk(tk.bill_status, tenant, bid, str(body.get("status") or ""), body.get("amount"), str(body.get("on") or ""))


@app.post("/api/theka/subs", dependencies=[Depends(require_key)])
def theka_sub(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.save_sub, tenant, str(body.get("name") or ""), str(body.get("phone") or ""), body.get("individual"), body.get("pan_ok"),
               str(body.get("work") or ""), body.get("retention_pct"))


@app.post("/api/theka/sub_bills", dependencies=[Depends(require_key)])
def theka_sub_bill(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.sub_bill, tenant, str(body.get("sub") or ""), body.get("amount"), str(body.get("project") or ""), str(body.get("day") or ""),
               str(body.get("note") or ""))


@app.post("/api/theka/register", dependencies=[Depends(require_key)])
def theka_register(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.register_file, tenant, str(body.get("conversation_id") or ""))


# ---------------------------------------------------------------- v0.115 Franchise Sahayak (franchise owner)
def _fr(fn, *a, **k):
    from .franchise import service as fr
    try:
        return fn(*a, **k)
    except (fr.FrError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/franchise/day", dependencies=[Depends(require_key)])
def franchise_day(tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return {**_fr(fr.day, tenant), "outlets": fr.outlets(tenant), "agreements": fr.agreements(tenant), "settings": fr.settings(tenant),
            "statements": fr.statements(tenant)}


@app.post("/api/franchise/settings", dependencies=[Depends(require_key)])
def franchise_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.save_settings, tenant, **{k: body[k] for k in ("company", "state", "tds_applies", "morning_time") if k in body})


@app.post("/api/franchise/agreements", dependencies=[Depends(require_key)])
def franchise_agreement(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    keys = ("franchisor", "contact", "royalty_pct", "marketing_pct", "tech_fee", "min_guarantee", "base", "foreign", "franchisor_state",
            "due_day", "start", "term_years", "lock_in_years", "notice_months", "checklist", "notes")
    return _fr(fr.save_agreement, tenant, str(body.get("brand") or ""), **{k: body[k] for k in keys if k in body})


@app.post("/api/franchise/outlets", dependencies=[Depends(require_key)])
def franchise_outlet(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _fr(fr.save_outlet, tenant, g("name"), g("brand"), g("city"), g("opened_on"), body.get("rent"), g("lease_end"),
               body.get("escalation_pct"), g("escalation_on"), body.get("targets"), g("manager_phone"))


@app.post("/api/franchise/sales", dependencies=[Depends(require_key)])
def franchise_sale(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.add_sale, tenant, str(body.get("outlet") or ""), body.get("net"), str(body.get("day") or ""), body.get("gross"),
               body.get("discount"), body.get("gst"), body.get("orders"), body.get("channels"))


@app.post("/api/franchise/sales/import", dependencies=[Depends(require_key)])
async def franchise_import(file: UploadFile = File(...), outlet: str = Form(""), tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    data = await file.read()
    return _fr(fr.import_sales, tenant, outlet, data, file.filename or "sales.csv")


@app.post("/api/franchise/costs", dependencies=[Depends(require_key)])
def franchise_cost(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.add_cost, tenant, str(body.get("outlet") or ""), str(body.get("kind") or "other"), body.get("amount"),
               str(body.get("month") or ""), str(body.get("note") or ""))


@app.post("/api/franchise/statements", dependencies=[Depends(require_key)])
def franchise_statement(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.statement, tenant, str(body.get("brand") or ""), str(body.get("month") or ""), str(body.get("conversation_id") or ""))


@app.post("/api/franchise/statements/{sid}/{action}", dependencies=[Depends(require_key)])
def franchise_statement_act(sid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """approve (her Haan, only from her tap) | paid"""
    from .franchise import service as fr
    if action == "approve":
        return _fr(fr.approve_statement, tenant, sid)
    if action == "paid":
        return _fr(fr.mark_paid, tenant, sid, str(body.get("on") or ""))
    raise HTTPException(404, "approve | paid")


@app.post("/api/franchise/licences", dependencies=[Depends(require_key)])
def franchise_licence(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.save_licence, tenant, str(body.get("outlet") or ""), str(body.get("kind") or "other"), str(body.get("valid_to") or ""),
               str(body.get("number") or ""), str(body.get("note") or ""))


@app.post("/api/franchise/audits", dependencies=[Depends(require_key)])
def franchise_audit(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.audit, tenant, str(body.get("outlet") or ""), body.get("failed"), body.get("items"), str(body.get("kind") or "daily"),
               str(body.get("day") or ""), str(body.get("note") or ""))


@app.post("/api/franchise/pnl_file", dependencies=[Depends(require_key)])
def franchise_pnl_file(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.pnl_file, tenant, str(body.get("month") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/franchise/{what}", dependencies=[Depends(require_key)])
def franchise_read(what: str, outlet: str = "", month: str = "", tenant: str = Depends(current_tenant)):
    """pnl | compare | licences | dates"""
    from .franchise import service as fr
    fns = {"pnl": lambda: fr.pnl(tenant, outlet, month), "compare": lambda: fr.compare(tenant, month), "licences": lambda: fr.licences(tenant),
           "dates": lambda: {"dates": fr.dates_watch(tenant)}}
    if what not in fns:
        raise HTTPException(404, "pnl | compare | licences | dates")
    return _fr(fns[what])


# ---------------------------------------------------------------- v0.110 Niryat Sahayak (exporter)
def _nir(fn, *a, **k):
    from .niryat import service as nr
    try:
        return fn(*a, **k)
    except (nr.NiryatError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/niryat/day", dependencies=[Depends(require_key)])
def niryat_day(tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return {**_nir(nr.day, tenant), "settings": nr.settings(tenant)}


@app.post("/api/niryat/settings", dependencies=[Depends(require_key)])
def niryat_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    keys = ("firm", "address", "iec", "gstin", "phone", "email", "ad_bank", "lut_no", "rcmc", "rcmc_valid_to", "prefix", "morning_time")
    return _nir(nr.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.get("/api/niryat/buyers", dependencies=[Depends(require_key)])
def niryat_buyers(tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return {"buyers": nr.buyers(tenant)}


@app.post("/api/niryat/buyers", dependencies=[Depends(require_key)])
def niryat_buyer_save(body: dict, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _nir(nr.save_buyer, tenant, g("name"), g("buyer"), g("country"), g("address"), g("email"), g("phone"), g("currency"),
                g("pay_terms"), body.get("credit_days"), g("notes"))


@app.get("/api/niryat/shipments", dependencies=[Depends(require_key)])
def niryat_shipments(status: str = "", buyer: str = "", tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return {"shipments": _nir(nr.shipments, tenant, status, buyer)}


@app.post("/api/niryat/shipments", dependencies=[Depends(require_key)])
def niryat_pi(body: dict, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _nir(nr.proforma, tenant, g("buyer"), body.get("lines"), g("text"), g("incoterm") or "FOB", g("place"), body.get("fx"),
                body.get("freight"), body.get("insurance"), g("gst_mode") or "lut", g("port_loading"), g("port_discharge"), g("mode") or "sea",
                g("currency"), g("conversation_id"))


@app.get("/api/niryat/shipments/{sid}", dependencies=[Depends(require_key)])
def niryat_shipment(sid: str, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return _nir(nr.get_shipment, tenant, sid)


@app.post("/api/niryat/shipments/{sid}/{action}", dependencies=[Depends(require_key)])
def niryat_act(sid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """send_pi / confirm (her Haan, only from her tap) | shipped | receive | cancel"""
    from .niryat import service as nr
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    if action == "send_pi":
        return _nir(nr.pi_draft, tenant, sid)
    if action == "confirm":
        return _nir(nr.confirm, tenant, sid, g("inv_date"), body.get("fx"), g("conversation_id"))
    if action == "shipped":
        return _nir(nr.shipped, tenant, sid, g("sb_no"), g("sb_date"), g("bl_no"), g("ship_date"), body.get("fx"))
    if action == "receive":
        return _nir(nr.receive, tenant, sid, body.get("amount"), body.get("inr"), g("on"), g("ref"))
    if action == "cancel":
        return _nir(nr.cancel, tenant, sid, g("reason"))
    raise HTTPException(404, "send_pi | confirm | shipped | receive | cancel")


@app.get("/api/niryat/realisation", dependencies=[Depends(require_key)])
def niryat_realisation(tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return nr.realisation(tenant)


@app.post("/api/niryat/register", dependencies=[Depends(require_key)])
def niryat_register(body: dict, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return _nir(nr.register_file, tenant, str(body.get("conversation_id") or ""))


# ---------------------------------------------------------------- v0.107 Thok Sahayak (wholesale trader)
def _thok(fn, *a, **k):
    from .thok import service as th
    try:
        return fn(*a, **k)
    except (th.ThokError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/thok/day", dependencies=[Depends(require_key)])
def thok_day(tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {**_thok(th.day, tenant), "settings": th.settings(tenant), "route": _thok(th.route_plan, tenant)}


@app.post("/api/thok/settings", dependencies=[Depends(require_key)])
def thok_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    keys = ("firm", "gstin", "address", "phone", "bank", "terms", "aato", "last_fy_turnover", "prefix", "credit_days", "morning_time")
    return _thok(th.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.get("/api/thok/parties", dependencies=[Depends(require_key)])
def thok_parties(kind: str = "", route: str = "", tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {"parties": _thok(th.parties, tenant, kind, route)}


@app.post("/api/thok/parties", dependencies=[Depends(require_key)])
def thok_party_save(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _thok(th.save_party, tenant, g("name"), g("party"), g("kind"), g("phone"), g("gstin"), g("address"), body.get("credit_limit"),
                 body.get("credit_days"), g("route"), body.get("msme"), body.get("pan_ok"), body.get("opening"), body.get("whatsapp_ok"),
                 g("notes"), g("state"))


@app.get("/api/thok/parties/{pid}", dependencies=[Depends(require_key)])
def thok_party(pid: str, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.party_view, tenant, pid)


@app.post("/api/thok/parties/{pid}/statement", dependencies=[Depends(require_key)])
def thok_statement(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.statement_file, tenant, pid, str(body.get("conversation_id") or ""))


@app.get("/api/thok/items", dependencies=[Depends(require_key)])
def thok_items(q: str = "", tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {"items": _thok(th.items, tenant, q)}


@app.post("/api/thok/items", dependencies=[Depends(require_key)])
def thok_item_save(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.save_item, tenant, str(body.get("name") or ""), body.get("price"), body.get("gst_pct"), str(body.get("unit") or ""),
                 body.get("qty"), str(body.get("hsn") or ""), body.get("cost"), str(body.get("supplier") or ""), body.get("lead_days"),
                 body.get("low_at"), body.get("tiers"))


@app.get("/api/thok/orders", dependencies=[Depends(require_key)])
def thok_orders(status: str = "", party: str = "", tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {"orders": _thok(th.orders, tenant, status, party)}


@app.post("/api/thok/orders", dependencies=[Depends(require_key)])
def thok_order_new(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.take_order, tenant, str(body.get("party") or ""), str(body.get("text") or ""), body.get("lines"),
                 str(body.get("note") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/thok/orders/{oid}", dependencies=[Depends(require_key)])
def thok_order_get(oid: str, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.get_order, tenant, oid)


@app.post("/api/thok/orders/{oid}/{action}", dependencies=[Depends(require_key)])
def thok_order_act(oid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """bill (her Haan, only from her tap) | cancel | invoice"""
    from .thok import service as th
    conv = str(body.get("conversation_id") or "")
    if action == "bill":
        return _thok(th.bill, tenant, oid, str(body.get("bill_date") or ""), body.get("lines"), conv)
    if action == "cancel":
        return _thok(th.cancel_order, tenant, oid, str(body.get("reason") or ""))
    if action == "invoice":
        return _thok(th.invoice_file, tenant, oid, conv)
    raise HTTPException(404, "bill | cancel | invoice")


@app.post("/api/thok/receive", dependencies=[Depends(require_key)])
def thok_receive(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _thok(th.receive, tenant, g("party"), body.get("amount"), g("mode") or "cash", g("on"), g("cheque_no"), g("cheque_date"),
                 g("bank"), g("note"))


@app.post("/api/thok/cheques/{pid}", dependencies=[Depends(require_key)])
def thok_cheque(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.cheque, tenant, pid, str(body.get("status") or ""), str(body.get("memo_date") or ""), str(body.get("reason") or ""))


@app.get("/api/thok/payments", dependencies=[Depends(require_key)])
def thok_payments(party: str = "", status: str = "", tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {"payments": _thok(th.payments, tenant, party, status)}


@app.post("/api/thok/purchases", dependencies=[Depends(require_key)])
def thok_purchase(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.purchase, tenant, str(body.get("supplier") or ""), str(body.get("text") or ""), body.get("lines"),
                 str(body.get("bill_no") or ""), str(body.get("bill_date") or ""), body.get("agreed_days"), body.get("paid"))


@app.post("/api/thok/pay_supplier", dependencies=[Depends(require_key)])
def thok_pay_supplier(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.pay_supplier, tenant, str(body.get("supplier") or ""), body.get("amount"), str(body.get("mode") or "neft"),
                 str(body.get("on") or ""), str(body.get("note") or ""))


@app.get("/api/thok/{what}", dependencies=[Depends(require_key)])
def thok_read(what: str, route: str = "", days: int = 30, tenant: str = Depends(current_tenant)):
    """outstanding | reminders | payables | reorder | margins | route"""
    from .thok import service as th
    fns = {"outstanding": lambda: th.outstanding(tenant, route), "reminders": lambda: th.reminder_drafts(tenant, route),
           "payables": lambda: th.payables(tenant), "reorder": lambda: th.reorder(tenant), "margins": lambda: th.margins(tenant, days),
           "route": lambda: th.route_plan(tenant, route)}
    if what not in fns:
        raise HTTPException(404, "outstanding | reminders | payables | reorder | margins | route")
    return _thok(fns[what])


# ---------------------------------------------------------------- v0.103 SEO Sahayak
def _seo(fn, *a, **k):
    from .seo import service as seo
    try:
        return fn(*a, **k)
    except (seo.SeoError, ValueError) as e:
        raise HTTPException(400, str(e))


async def _finish_seo_link(request: Request) -> HTMLResponse:
    from .seo import service as seo
    if request.query_params.get("error"):
        return _linked_page("Search Console", "seo", None, request.query_params["error"])
    try:
        v = await asyncio.to_thread(seo.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except seo.SeoError as e:
        return _linked_page("Search Console", "seo", None, str(e))
    return _linked_page("Search Console", "seo", v["address"])


@app.get("/api/seo/summary", dependencies=[Depends(require_key)])
def seo_summary(site: str = "", tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    if not seo.sites(tenant):
        return {"site": None, "gsc": seo.gsc_status(tenant)}
    return _seo(seo.summary, tenant, site)


@app.post("/api/seo/site", dependencies=[Depends(require_key)])
def seo_site(body: dict, tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    biz = {k: body.get(k) for k in ("city", "state", "street", "pin", "phone", "schema_type", "hours", "price_range")}
    return _seo(seo.save_site, tenant, str(body.get("url") or ""), str(body.get("name") or ""), str(body.get("site") or ""),
                body.get("services"), **biz)


@app.get("/api/seo/tasks", dependencies=[Depends(require_key)])
def seo_tasks(site: str = "", status: str = "open", tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    return {"tasks": _seo(seo.tasks, tenant, site, status)}


@app.post("/api/seo/tasks/{tid}", dependencies=[Depends(require_key)])
def seo_task(tid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    return _seo(seo.close_task, tenant, tid, str(body.get("status") or "done"))


@app.get("/api/seo/drafts", dependencies=[Depends(require_key)])
def seo_drafts(site: str = "", tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    return {"drafts": _seo(seo.drafts, tenant, site)}


@app.post("/api/seo/drafts/{did}", dependencies=[Depends(require_key)])
def seo_draft_ok(did: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her Haan (only from her tap): the draft is final; she puts it on her site / profile."""
    from .seo import service as seo
    return _seo(seo.approve_draft, tenant, did, str(body.get("text") or ""))


@app.post("/api/seo/{action}", dependencies=[Depends(require_key)])
def seo_act(action: str, body: dict, tenant: str = Depends(current_tenant)):
    """audit | speed | performance | brief | schema | gbp_post | review_reply | report | keywords"""
    from .seo import service as seo
    site, conv = str(body.get("site") or ""), str(body.get("conversation_id") or "")
    if action == "audit":
        return _seo(seo.crawl, tenant, site, int(body.get("max_pages") or 25), conv)
    if action == "speed":
        return _seo(seo.pagespeed, tenant, site, str(body.get("url") or ""), str(body.get("strategy") or "mobile"))
    if action == "performance":
        return _seo(seo.performance, tenant, site, int(body.get("days") or 28), conv)
    if action == "brief":
        return _seo(seo.content_brief, tenant, str(body.get("keyword") or ""), site, conv)
    if action == "schema":
        return _seo(seo.schema_draft, tenant, site, conv)
    if action == "gbp_post":
        return _seo(seo.gbp_post, tenant, str(body.get("topic") or ""), str(body.get("offer") or ""), site, conv)
    if action == "review_reply":
        return _seo(seo.review_reply, tenant, str(body.get("review") or ""), int(body.get("stars") or 0), str(body.get("reviewer") or ""), site, conv)
    if action == "report":
        return _seo(seo.report_file, tenant, site, conv)
    if action == "keywords":
        return _seo(seo.keyword_plan, tenant, site)
    raise HTTPException(404, "unknown action")


@app.get("/api/seo/gsc/link", dependencies=[Depends(require_key)])
def seo_gsc_link(tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    try:
        return {"url": seo.start_link(tenant)}
    except seo.SeoError as e:
        raise HTTPException(503, str(e))


@app.delete("/api/seo/gsc", dependencies=[Depends(require_key)])
def seo_gsc_remove(tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    from .db import session as _ses
    with _ses() as s:
        g = s.get(seo.SeoGoogle, tenant)
        if g:
            s.delete(g)
    return seo.gsc_status(tenant)


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


# ---------------------------------------------------------------- v0.99 Telecaller Sahayak (a person makes every call)
def _tele(fn, *a, **k):
    from .telecall import service as tele
    try:
        return fn(*a, **k)
    except tele.TeleError as e:
        raise HTTPException(400, str(e))


@app.get("/api/telecall", dependencies=[Depends(require_key)])
def tele_all(assigned: str = "", tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return {"list": tele.call_list(tenant, 0, assigned), "report": tele.report(tenant, 1), "settings": tele.settings(tenant),
            "outcomes": {k: v[0] for k, v in tele.OUTCOMES.items()}, "purposes": tele.PURPOSES}


@app.get("/api/telecall/leads", dependencies=[Depends(require_key)])
def tele_leads(q: str = "", stage: str = "", tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return {"leads": tele.leads(tenant, q, stage, 300)}


@app.post("/api/telecall/leads", dependencies=[Depends(require_key)])
def tele_add(body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.add_lead, tenant, str(body.get("name") or ""), str(body.get("phone") or ""),
                 str(body.get("source") or "enquiry"), str(body.get("purpose") or "sales"), str(body.get("need") or ""),
                 str(body.get("notes") or ""), str(body.get("city") or ""), str(body.get("language") or ""), body.get("amount"),
                 body.get("consent"), str(body.get("assigned") or ""), str(body.get("next_when") or ""))


@app.post("/api/telecall/import", dependencies=[Depends(require_key)])
def tele_import(body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.import_list, tenant, str(body.get("list_id") or ""), str(body.get("file_id") or ""),
                 str(body.get("source") or ""), str(body.get("purpose") or "sales"), str(body.get("assigned") or ""))


@app.get("/api/telecall/leads/{lead_id}", dependencies=[Depends(require_key)])
def tele_lead(lead_id: str, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.get_lead, tenant, lead_id)


@app.patch("/api/telecall/leads/{lead_id}", dependencies=[Depends(require_key)])
def tele_update(lead_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    keys = ("name", "need", "city", "language", "assigned", "notes", "purpose", "interest", "stage", "amount", "consent",
            "next_when", "reason")
    return _tele(tele.update_lead, tenant, lead_id, **{k: body[k] for k in keys if k in body})


@app.post("/api/telecall/leads/{lead_id}/script", dependencies=[Depends(require_key)])
async def tele_script(lead_id: str, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return await asyncio.to_thread(_tele, tele.make_script, tenant, lead_id)


@app.post("/api/telecall/leads/{lead_id}/call", dependencies=[Depends(require_key)])
def tele_start(lead_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """She tapped Call: note the time; the APP opens the phone's own dialer. The server never dials."""
    from .telecall import service as tele
    return _tele(tele.start_call, tenant, lead_id, str(body.get("by") or "owner"))


@app.post("/api/telecall/calls/{call_id}/log", dependencies=[Depends(require_key)])
async def tele_log_call(call_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return await asyncio.to_thread(_tele, tele.log_call, tenant, "", call_id, str(body.get("outcome") or ""),
                                   str(body.get("notes") or ""), str(body.get("next_when") or ""), body.get("seconds"),
                                   str(body.get("interest") or ""), body.get("amount"), str(body.get("file_id") or ""),
                                   str(body.get("by") or "owner"), "app", str(body.get("conversation_id") or ""))


@app.post("/api/telecall/leads/{lead_id}/log", dependencies=[Depends(require_key)])
async def tele_log_lead(lead_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return await asyncio.to_thread(_tele, tele.log_call, tenant, lead_id, "", str(body.get("outcome") or ""),
                                   str(body.get("notes") or ""), str(body.get("next_when") or ""), body.get("seconds"),
                                   str(body.get("interest") or ""), body.get("amount"), str(body.get("file_id") or ""),
                                   str(body.get("by") or "owner"), "app", str(body.get("conversation_id") or ""))


@app.post("/api/telecall/leads/{lead_id}/dnd", dependencies=[Depends(require_key)])
def tele_dnd(lead_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.mark_dnd, tenant, lead_id, bool(body.get("wrong")))


@app.delete("/api/telecall/leads/{lead_id}", dependencies=[Depends(require_key)])
def tele_forget(lead_id: str, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.forget, tenant, lead_id)


@app.get("/api/telecall/report", dependencies=[Depends(require_key)])
def tele_report(days: int = 1, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return tele.report(tenant, max(1, min(90, days)))


@app.put("/api/telecall/settings", dependencies=[Depends(require_key)])
def tele_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    keys = ("enabled", "business", "caller_name", "pitch", "segment", "start_hour", "end_hour", "daily_goal", "max_attempts",
            "record_calls", "registered", "language", "rules", "dont_say", "team", "morning_time")
    return _tele(tele.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.111 Ads Sahayak (performance marketer; ad money on her tap)
def _ads(fn, *a, **k):
    from .ads import service as ads
    try:
        return fn(*a, **k)
    except ads.AdsError as e:
        raise HTTPException(400, str(e))


@app.get("/api/ads", dependencies=[Depends(require_key)])
async def ads_all(tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(ads.everything, tenant)


@app.get("/api/ads/report", dependencies=[Depends(require_key)])
async def ads_report(days: int = 30, platform: str = "", tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(ads.analyse, tenant, max(1, min(365, days)), platform)


@app.post("/api/ads/import", dependencies=[Depends(require_key)])
async def ads_import(file: UploadFile | None = File(None), file_id: str = Form(""), platform: str = Form(""),
                     start: str = Form(""), end: str = Form(""), conversation_id: str = Form(""),
                     tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    data = await file.read() if file is not None else None
    if data is not None and len(data) > 30 * 1024 * 1024:
        raise HTTPException(413, "Report 30 MB se badi hai.")
    return await asyncio.to_thread(_ads, ads.import_report, tenant, file_id, data, (file.filename if file else "report.csv"),
                                   platform, start, end, conversation_id)


@app.post("/api/ads/plan", dependencies=[Depends(require_key)])
async def ads_plan(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(_ads, ads.make_plan, tenant, int(body.get("days") or 14), str(body.get("conversation_id") or ""),
                                   float(body.get("extra") or 0))


@app.get("/api/ads/changes", dependencies=[Depends(require_key)])
def ads_changes(status: str = "", tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return {"changes": ads.changes(tenant, status, 100)}


@app.post("/api/ads/changes/{cid}/decide", dependencies=[Depends(require_key)])
async def ads_decide(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on a change card. A change that spends more needs her phone's fingerprint once one is set up."""
    from .ads import service as ads
    yes = bool(body.get("yes"))
    if yes:
        _fingerprint(tenant, "ads", cid, body.get("proof"))
    after = body.get("after")
    return await asyncio.to_thread(_ads, ads.decide_change, tenant, cid, yes, float(after) if after not in (None, "") else None,
                                   str(body.get("conversation_id") or ""))


@app.post("/api/ads/changes/{cid}/done", dependencies=[Depends(require_key)])
def ads_done(cid: str, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return _ads(ads.mark_done, tenant, cid)


@app.post("/api/ads/copies", dependencies=[Depends(require_key)])
async def ads_copies(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(_ads, ads.write_copies, tenant, str(body.get("brief") or ""), str(body.get("platform") or "meta"),
                                   str(body.get("campaign") or ""), int(body.get("n") or 4), str(body.get("lang") or ""),
                                   str(body.get("landing") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/ads/tests", dependencies=[Depends(require_key)])
def ads_tests(tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return {"tests": ads.tests(tenant, 60)}


@app.post("/api/ads/tests/{tid}/{action}", dependencies=[Depends(require_key)])
def ads_test_act(tid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    if action == "live":
        return _ads(ads.test_live, tenant, tid, body.get("labels"))
    if action == "result":
        return _ads(ads.test_result, tenant, tid, body.get("results") if isinstance(body.get("results"), dict) else None)
    raise HTTPException(404, "unknown action")


@app.post("/api/ads/sales", dependencies=[Depends(require_key)])
def ads_sale(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return _ads(ads.add_sale, tenant, str(body.get("campaign") or ""), int(body.get("count") or 0), float(body.get("value") or 0),
                str(body.get("day") or ""), str(body.get("platform") or ""), str(body.get("note") or ""))


@app.put("/api/ads/settings", dependencies=[Depends(require_key)])
def ads_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    keys = ("enabled", "business", "segment", "offer", "target_cpl", "target_roas", "avg_order", "margin_pct", "close_pct",
            "month_budget", "max_step_pct", "report_day", "report_time", "rules")
    return _ads(ads.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.put("/api/ads/meta", dependencies=[Depends(require_key)])
async def ads_meta(body: dict, tenant: str = Depends(current_tenant)):
    """Her own Meta ad account: account id + a system-user token (typed in the app only; sealed, never shown again)."""
    from .ads import service as ads
    return await asyncio.to_thread(_ads, ads.set_meta, tenant, str(body.get("account") or ""), str(body.get("token") or ""))


@app.delete("/api/ads/meta", dependencies=[Depends(require_key)])
def ads_meta_off(tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return ads.forget_meta(tenant)


@app.post("/api/ads/meta/fetch", dependencies=[Depends(require_key)])
async def ads_meta_fetch(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(_ads, ads.fetch_meta, tenant, int(body.get("days") or 14), str(body.get("conversation_id") or ""))


# ---------------------------------------------------------------- v0.121 Website Sahayak (plan, looks, live build, checks, preview)
def _site(fn, *a, **k):
    from .site import service as S
    try:
        return fn(*a, **k)
    except S.SiteError as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, f"not found: {e}")


@app.get("/api/sites", dependencies=[Depends(require_key)])
async def sites_all(tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(S.everything, tenant)


@app.post("/api/sites", dependencies=[Depends(require_key)])
async def sites_new(body: dict, tenant: str = Depends(current_tenant)):
    """{brief, name, goal, style, answers {name, phone, ...}, client, conversation_id}"""
    from .site import service as S
    ans = body.get("answers") if isinstance(body.get("answers"), dict) else None
    return await asyncio.to_thread(_site, S.new, tenant, str(body.get("brief") or ""), str(body.get("conversation_id") or ""),
                                   str(body.get("name") or ""), str(body.get("field") or ""), str(body.get("goal") or ""),
                                   str(body.get("style") or ""), ans, str(body.get("client") or ""))


@app.get("/api/sites-library", dependencies=[Depends(require_key)])
async def sites_library(industry: str = "", q: str = "", offset: int = 0, limit: int = 60):
    from .site import library as L
    return await asyncio.to_thread(L.browse, industry, q, max(1, min(limit, 200)), max(0, offset))


@app.get("/api/sites-library/brief", dependencies=[Depends(require_key)])
async def sites_library_brief(field: str, goal: str = "", style: str = ""):
    from .site import library as L
    try:
        return await asyncio.to_thread(L.brief, field, goal, style)
    except KeyError:
        raise HTTPException(404, "field not found")


@app.get("/api/sites-library/understand", dependencies=[Depends(require_key)])
async def sites_library_understand(q: str):
    from .site import library as L
    return await asyncio.to_thread(L.understand, q)


@app.get("/api/sites/{ref}", dependencies=[Depends(require_key)])
async def sites_get(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.get, tenant, ref)


@app.delete("/api/sites/{ref}", dependencies=[Depends(require_key)])
async def sites_delete(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.delete, tenant, ref)


@app.post("/api/sites/{ref}/answers", dependencies=[Depends(require_key)])
async def sites_answers(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import service as S
    ans = body.get("answers") if isinstance(body.get("answers"), dict) else {}
    return await asyncio.to_thread(_site, S.answer, tenant, ref, ans)


@app.post("/api/sites/{ref}/plan", dependencies=[Depends(require_key)])
async def sites_plan_ok(ref: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """Her tap: 'Haan, aage badho' on the plan card -> 3 looks."""
    from .site import service as S
    body = body or {}
    pages = body.get("pages") if isinstance(body.get("pages"), list) else None
    return await asyncio.to_thread(_site, S.approve_plan, tenant, ref, str(body.get("conversation_id") or ""), pages)


@app.post("/api/sites/{ref}/look", dependencies=[Depends(require_key)])
async def sites_look(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on one of the 3 looks {index, colors_from?} -> the build starts."""
    from .site import service as S
    cf = body.get("colors_from")
    return await asyncio.to_thread(_site, S.choose_look, tenant, ref, int(body.get("index") or 0),
                                   int(cf) if cf is not None and str(cf).lstrip("-").isdigit() else None,
                                   str(body.get("conversation_id") or ""))


@app.post("/api/sites/{ref}/change", dependencies=[Depends(require_key)])
async def sites_change(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.change, tenant, ref, str(body.get("instruction") or ""),
                                   str(body.get("conversation_id") or ""))


@app.post("/api/sites/{ref}/stop", dependencies=[Depends(require_key)])
async def sites_stop(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.stop, tenant, ref)


@app.post("/api/sites/{ref}/resume", dependencies=[Depends(require_key)])
async def sites_resume(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.resume, tenant, ref)


@app.post("/api/sites/{ref}/photo", dependencies=[Depends(require_key)])
async def sites_photo(ref: str, file: UploadFile = File(...), about: str = Form(""), tenant: str = Depends(current_tenant)):
    from .site import service as S
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "Photo 25 MB se badi hai")
    return await asyncio.to_thread(_site, S.add_photo, tenant, ref, data, "", about, "")


@app.post("/api/sites/{ref}/export", dependencies=[Depends(require_key)])
async def sites_export(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.export, tenant, ref)


@app.get("/api/sites/{ref}/leads", dependencies=[Depends(require_key)])
async def sites_leads(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return {"leads": await asyncio.to_thread(_site, S.leads, tenant, ref)}


@app.get("/api/sites/{ref}/shots/{name:path}", dependencies=[Depends(require_key)])
async def sites_shot(ref: str, name: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    try:
        f = await asyncio.to_thread(S.shot_file, tenant, ref, name)
    except (S.SiteError, ValueError):
        raise HTTPException(404, "not found")
    return FileResponse(f, headers={"Cache-Control": "private, max-age=300"})


@app.get("/api/site-preview/{token}")
async def site_preview_root(token: str):
    return RedirectResponse(f"/api/site-preview/{token}/", status_code=307)


@app.get("/api/site-preview/{token}/{path:path}")
async def site_preview(token: str, path: str = ""):
    """Public, by its random token: the live preview of a site being built (noindex, strict CSP)."""
    from .site import service as S
    try:
        data, ctype, headers = await asyncio.to_thread(S.preview_file, token, path)
    except S.SiteError:
        raise HTTPException(404, "not found")
    # v0.160 the console shows it in a sandboxed frame (opaque origin): its own fonts / files must load from there
    return Response(content=data, media_type=ctype, headers={**headers, "Access-Control-Allow-Origin": "*"})


_SITE_FORM_CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS",
                   "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400"}


@app.options("/api/site-forms/{site_id}")
async def site_form_cors(site_id: str):
    return Response(status_code=204, headers=_SITE_FORM_CORS)


@app.post("/api/site-forms/{site_id}")
async def site_form(site_id: str, request: Request):
    """Public: a visitor's enquiry from a Hoola-built site -> her lead (honeypot, rate limits, no cookies)."""
    from .site import service as S
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "bad form")
    ip = (request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip") or
          (request.client.host if request.client else ""))
    try:
        out = await asyncio.to_thread(S.form_post, site_id, body, ip)
    except S.SiteError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400, headers=_SITE_FORM_CORS)
    return JSONResponse(out, headers=_SITE_FORM_CORS)


# ---------------------------------------------------------------- v0.122 Website hosting: launch, rollback, her domain, DNS
def _host(fn, *a, **k):
    from .site import dns as D
    from .site import hosting as H
    from .site import service as S
    try:
        return fn(*a, **k)
    except (H.HostError, D.DnsError, S.SiteError) as e:
        raise HTTPException(400, str(e))
    except Exception as e:                       # v0.123 domain errors carry plain words too
        from .site import domains as DM
        if isinstance(e, DM.DomainError):
            raise HTTPException(400, str(e))
        raise


@app.get("/api/sites/{ref}/hosting", dependencies=[Depends(require_key)])
async def sites_hosting(ref: str, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.status, tenant, ref)


@app.post("/api/sites/{ref}/launch-request", dependencies=[Depends(require_key)])
async def sites_launch_request(ref: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    body = body or {}
    return await asyncio.to_thread(_host, H.launch_request, tenant, ref, body.get("free", True) is not False,
                                   str(body.get("conversation_id") or ""))


@app.post("/api/sites/{ref}/launch", dependencies=[Depends(require_key)])
async def sites_launch(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on 'Haan, live karo' (the card's hash must match the checked version and addresses)."""
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.launch, tenant, ref, str(body.get("hash") or ""), body.get("free", True) is not False)


@app.post("/api/sites/{ref}/rollback-request", dependencies=[Depends(require_key)])
async def sites_rollback_request(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.rollback_request, tenant, ref, int(body.get("version") or 0))


@app.post("/api/sites/{ref}/rollback", dependencies=[Depends(require_key)])
async def sites_rollback(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.rollback, tenant, ref, int(body.get("version") or 0), str(body.get("hash") or ""))


@app.post("/api/sites/{ref}/takedown", dependencies=[Depends(require_key)])
async def sites_takedown(ref: str, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.take_down, tenant, ref)


@app.post("/api/sites/{ref}/domain", dependencies=[Depends(require_key)])
async def sites_domain(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.connect_domain, tenant, ref, str(body.get("domain") or ""),
                                   str(body.get("conversation_id") or ""))


@app.post("/api/sites-dns/{plan_id}/apply", dependencies=[Depends(require_key)])
async def sites_dns_apply(plan_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on the DNS card."""
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.dns_apply, tenant, plan_id, str(body.get("hash") or ""))


@app.post("/api/sites-dns/{plan_id}/undo", dependencies=[Depends(require_key)])
async def sites_dns_undo(plan_id: str, tenant: str = Depends(current_tenant)):
    from .site import dns as D
    return await asyncio.to_thread(_host, D.undo, tenant, plan_id)


@app.get("/api/sites-dns/{plan_id}/check", dependencies=[Depends(require_key)])
async def sites_dns_check(plan_id: str, tenant: str = Depends(current_tenant)):
    from .site import dns as D
    return await asyncio.to_thread(_host, D.check, tenant, plan_id)


@app.post("/api/sites/{ref}/email-dns", dependencies=[Depends(require_key)])
async def sites_email_dns(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{domain, provider google|zoho, report_to} -> a DNS plan card for email at her domain (applied on her tap)."""
    from .site import dns as D
    from .site import service as S

    def go():
        with __import__("app.db", fromlist=["session"]).session() as s:
            r = S._find(s, tenant, ref)
            sid = r.id
        d = D.norm_domain(str(body.get("domain") or ""))
        return D.make_plan(tenant, sid, d, D.email_records(d, str(body.get("provider") or ""), str(body.get("report_to") or "")),
                           "email")
    return await asyncio.to_thread(_host, go)


@app.get("/api/sites-keys", dependencies=[Depends(require_key)])
async def sites_keys(tenant: str = Depends(current_tenant)):
    from .site import dns as D
    return {"keys": await asyncio.to_thread(D.keys, tenant)}


@app.put("/api/sites-keys/{provider}", dependencies=[Depends(require_key)])
async def sites_key_set(provider: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her own Cloudflare / Porkbun key, typed in the app only (never in chat); verified, then sealed."""
    from .site import dns as D
    return await asyncio.to_thread(_host, D.set_key, tenant, provider, str(body.get("token") or ""), str(body.get("secret") or ""))


@app.delete("/api/sites-keys/{provider}", dependencies=[Depends(require_key)])
async def sites_key_forget(provider: str, tenant: str = Depends(current_tenant)):
    from .site import dns as D
    return await asyncio.to_thread(_host, D.forget_key, tenant, provider)


@app.get("/api/hosting/ask")
async def hosting_ask(domain: str = ""):
    """For an optional Caddy in front (on-demand TLS): 200 only for hostnames of launched Hoola sites."""
    from .site import hosting as H
    return Response(status_code=200 if domain.lower() in await asyncio.to_thread(H.host_map, True) else 404)


# ---------------------------------------------------------------- v0.123 Domains (ideas, live price, buy on her fingerprint tap)
@app.get("/api/sites-domains", dependencies=[Depends(require_key)])
async def sites_domains(tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    from .site import dns as D
    return {"domains": await asyncio.to_thread(DM.domains, tenant), "keys": await asyncio.to_thread(D.keys, tenant),
            "month_spent_inr": await asyncio.to_thread(DM._month_spent, tenant), "month_limit_inr": DM._ceiling()}


@app.post("/api/sites-domains/ideas", dependencies=[Depends(require_key)])
async def sites_domain_ideas(body: dict, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    return await asyncio.to_thread(_host, DM.suggest, tenant, str(body.get("site") or ""), str(body.get("name") or ""),
                                   str(body.get("city") or ""))


@app.post("/api/sites-domains/check", dependencies=[Depends(require_key)])
async def sites_domain_check(body: dict, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    doms = [str(d) for d in (body.get("domains") or [])][:20]
    return {"results": await asyncio.to_thread(_host, DM.check, tenant, doms)}


@app.post("/api/sites-domains/request", dependencies=[Depends(require_key)])
async def sites_domain_request(body: dict, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    return await asyncio.to_thread(_host, DM.buy_request, tenant, str(body.get("site") or ""), str(body.get("domain") or ""),
                                   bool(body.get("auto_renew")), "",
                                   body.get("registrant") if isinstance(body.get("registrant"), dict) else None)


@app.post("/api/sites-domains/{oid}/buy", dependencies=[Depends(require_key)])
async def sites_domain_buy(oid: str, body: dict, tenant: str = Depends(current_tenant)):
    """ONLY her tap on the domain card; fingerprint-signed once a phone key is set up (money, no refunds)."""
    from .site import domains as DM
    _fingerprint(tenant, "domain", oid, body.get("proof"))
    return await asyncio.to_thread(_host, DM.buy, tenant, oid, str(body.get("hash") or ""))


@app.post("/api/sites-domains/{oid}/cancel", dependencies=[Depends(require_key)])
async def sites_domain_cancel(oid: str, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    return await asyncio.to_thread(_host, DM.cancel, tenant, oid)


@app.post("/api/sites-domains/kyc", dependencies=[Depends(require_key)])
async def sites_domain_kyc(body: dict, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    return await asyncio.to_thread(_host, DM.kyc_done, tenant, str(body.get("domain") or ""))


# ---------------------------------------------------------------- v0.124 Website care + agency + GitHub export
def _care(fn, *a, **k):
    from .site import github as GH
    try:
        return _host(fn, *a, **k)
    except GH.GithubError as e:
        raise HTTPException(400, str(e))


@app.get("/api/sites/{ref}/care", dependencies=[Depends(require_key)])
async def sites_care(ref: str, days: int = 30, tenant: str = Depends(current_tenant)):
    from .site import care as SC
    return await asyncio.to_thread(_care, SC.report, tenant, ref, max(1, min(days, 365)))


@app.get("/api/sites-clients", dependencies=[Depends(require_key)])
async def sites_clients(tenant: str = Depends(current_tenant)):
    from .site import care as SC
    return {"clients": await asyncio.to_thread(SC.clients, tenant)}


@app.post("/api/sites/{ref}/assign", dependencies=[Depends(require_key)])
async def sites_assign(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import care as SC
    return await asyncio.to_thread(_care, SC.assign, tenant, ref,
                                   body.get("client") if "client" in body else None, body.get("staff") if "staff" in body else None)


@app.get("/api/sites/{ref}/github", dependencies=[Depends(require_key)])
async def sites_github_list(ref: str, tenant: str = Depends(current_tenant)):
    from .site import github as GH
    from .site import service as S

    def run():
        with session() as s:
            sid = S._find(s, tenant, ref).id
        return {"exports": GH.exports(tenant, sid)}
    return await asyncio.to_thread(_care, run)


@app.post("/api/sites/{ref}/github-request", dependencies=[Depends(require_key)])
async def sites_github_request(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import github as GH
    return await asyncio.to_thread(_care, GH.request, tenant, ref, str(body.get("repo") or ""), body.get("private", True) is not False)


@app.post("/api/sites-github/{eid}/push", dependencies=[Depends(require_key)])
async def sites_github_push(eid: str, body: dict, tenant: str = Depends(current_tenant)):
    """ONLY her tap on the GitHub card."""
    from .site import github as GH
    return await asyncio.to_thread(_care, GH.push, tenant, eid, str(body.get("hash") or ""))


@app.post("/api/sites-github/{eid}/cancel", dependencies=[Depends(require_key)])
async def sites_github_cancel(eid: str, tenant: str = Depends(current_tenant)):
    from .site import github as GH
    return await asyncio.to_thread(_care, GH.cancel, tenant, eid)


# ---------------------------------------------------------------- v0.128 App Sahayak (every screen designed + prototype first)
def _appd(fn, *a, **k):
    from .appmaker import service as A
    try:
        return fn(*a, **k)
    except A.AppError as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, f"not found: {e}")


@app.get("/api/apps", dependencies=[Depends(require_key)])
async def apps_all(tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.everything, tenant)


@app.post("/api/apps", dependencies=[Depends(require_key)])
async def apps_new(body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    ans = body.get("answers") if isinstance(body.get("answers"), dict) else None
    return await asyncio.to_thread(_appd, A.new, tenant, str(body.get("brief") or ""), str(body.get("conversation_id") or ""),
                                   str(body.get("name") or ""), str(body.get("field") or ""), str(body.get("goal") or ""),
                                   str(body.get("style") or ""), ans, str(body.get("idea") or ""))


@app.get("/api/apps-ideas", dependencies=[Depends(require_key)])
async def apps_ideas(q: str = "", field: str = "", goal: str = "", aud: str = "", offset: int = 0, limit: int = 30):
    """v0.136 the 1 crore app idea list: her words -> the best precise idea + near ones; or walk the list page by page."""
    from .appmaker import ideas as I

    def go():
        out = I.browse(q, field, goal, aud, offset, limit)
        if q and not offset:
            u = I.understand(q, field, goal)
            out["best"] = u.get("idea")
            out["near"] = u.get("alternatives", [])
            out["ask"] = u.get("ask", "")
        out["all_ideas"] = I.total()
        return out
    return await asyncio.to_thread(go)


@app.get("/api/apps-ideas/{idea_id}", dependencies=[Depends(require_key)])
async def apps_idea(idea_id: str):
    from .appmaker import ideas as I
    try:
        return await asyncio.to_thread(I.idea, idea_id)
    except KeyError:
        raise HTTPException(404, "idea not found")


@app.get("/api/apps-library", dependencies=[Depends(require_key)])
async def apps_library(industry: str = "", q: str = "", offset: int = 0, limit: int = 60):
    from .appmaker import library as AL
    return await asyncio.to_thread(AL.browse, industry, q, max(1, min(limit, 200)), max(0, offset))


@app.get("/api/apps-library/brief", dependencies=[Depends(require_key)])
async def apps_library_brief(field: str, goal: str = "", style: str = ""):
    from .appmaker import library as AL
    try:
        return await asyncio.to_thread(AL.brief, field, goal, style)
    except KeyError:
        raise HTTPException(404, "field not found")


@app.get("/api/apps-library/understand", dependencies=[Depends(require_key)])
async def apps_library_understand(q: str):
    from .appmaker import library as AL
    return await asyncio.to_thread(AL.understand, q)


@app.get("/api/apps/{ref}", dependencies=[Depends(require_key)])
async def apps_get(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.get, tenant, ref)


@app.delete("/api/apps/{ref}", dependencies=[Depends(require_key)])
async def apps_delete(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.delete, tenant, ref)


@app.get("/api/apps/{ref}/spec", dependencies=[Depends(require_key)])
async def apps_spec(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.spec, tenant, ref)


@app.get("/api/apps/{ref}/blueprint", dependencies=[Depends(require_key)])
async def apps_blueprint(ref: str, tenant: str = Depends(current_tenant)):
    """v0.131: data tables, org levels, roles matrix, approval chain, login plan, phone features with store status, files."""
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.blueprint, tenant, ref)


@app.get("/api/apps/{ref}/blueprint/{name}", dependencies=[Depends(require_key)])
async def apps_blueprint_file(ref: str, name: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    try:
        data, ctype = await asyncio.to_thread(A.blueprint_file, tenant, ref, name)
    except A.AppError:
        raise HTTPException(404, "not found")
    headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
    if name.endswith(".html"):
        headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; frame-ancestors *"
    return Response(content=data, media_type=ctype, headers=headers)


@app.get("/api/apps-catalog/{kind}", dependencies=[Depends(require_key)])
async def apps_catalog(kind: str, q: str = ""):
    """archetypes | capabilities | login | screens | roles (v0.131 complex apps)."""
    def go():
        from .appmaker import auth as AU
        from .appmaker import capabilities as CP
        from .appmaker import datamodel as DM
        from .appmaker import library as AL
        from .appmaker import orgmodel as OM
        from .appmaker import taxonomy as TX
        if kind == "archetypes":
            return {"archetypes": [{"id": k, "label": g["label"], "hi": g["hi"], "brief": g["brief"], "modules": g["modules"],
                                    "roles": [OM.ROLES[r]["label"] for r in g["roles"]], "screens": len(g["screens"]),
                                    "levels": OM.LEVELS[g["levels"]], "money": g["money"], "fields": len(AL.pro_fields(k))}
                                   for k, g in TX.GOALS.items() if g.get("complex")], "counts": AL.counts()}
        if kind == "capabilities":
            ql = q.lower()
            return {"capabilities": [c for c in CP.catalog() if not ql or ql in (c["label"] + " " + c["hi"] + " " + c["id"]).lower()],
                    "legend": {"play": CP.PLAY_LABEL, "ios": CP.IOS_LABEL}, "counts": CP.counts()}
        if kind == "login":
            return {"methods": AU.METHODS, "policy": AU.POLICY}
        if kind == "screens":
            return {"screens": [{"id": k, "label": v["label"], "hi": v["hi"], "why": v["why"], "pro": bool(v.get("pro")),
                                 "designs": len(v["variants"])} for k, v in TX.SCREENS.items()], "code": TX.CODE_SCREENS}
        if kind == "roles":
            return {"roles": OM.ROLES, "templates": OM.BASE, "levels": OM.LEVELS, "scopes": OM.SCOPE_LABEL, "rules": OM.RULES,
                    "modules": DM.MODULES}
        raise HTTPException(404, "unknown catalogue")
    return await asyncio.to_thread(go)


@app.post("/api/apps/{ref}/{action}", dependencies=[Depends(require_key)])
async def apps_act(ref: str, action: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """answers | plan (her Haan) | look (her choice) | change | approve (her 'Design pakka' tap, with the card's hash) | stop | resume."""
    from .appmaker import service as A
    body = body or {}
    conv = str(body.get("conversation_id") or "")
    if action == "answers":
        ans = body.get("answers") if isinstance(body.get("answers"), dict) else {}
        return await asyncio.to_thread(_appd, A.answer, tenant, ref, ans)
    if action == "plan":
        drop = body.get("drop") if isinstance(body.get("drop"), list) else None
        return await asyncio.to_thread(_appd, A.approve_plan, tenant, ref, conv, drop)
    if action == "look":
        cf = body.get("colors_from")
        return await asyncio.to_thread(_appd, A.choose_look, tenant, ref, int(body.get("index") or 0),
                                       int(cf) if cf is not None else None, conv)
    if action == "change":
        return await asyncio.to_thread(_appd, A.change, tenant, ref, str(body.get("instruction") or ""), conv)
    if action == "approve":
        return await asyncio.to_thread(_appd, A.approve, tenant, ref, str(body.get("hash") or ""))
    if action == "stop":
        return await asyncio.to_thread(_appd, A.stop, tenant, ref)
    if action == "resume":
        return await asyncio.to_thread(_appd, A.resume, tenant, ref)
    if action == "android":
        from .appmaker.android import service as AN
        only = [str(x) for x in body.get("redo") or [] if isinstance(x, str)][:60] if isinstance(body.get("redo"), list) else None
        return await asyncio.to_thread(_appd, AN.build, tenant, ref, conv, only)
    raise HTTPException(404, "unknown action")


@app.get("/api/apps/{ref}/android", dependencies=[Depends(require_key)])
async def apps_android(ref: str, tenant: str = Depends(current_tenant)):
    """v0.132: the native Android build of an approved design (screens in Kotlin, compile rounds, APK / project ZIP)."""
    from .appmaker.android import service as AN
    return await asyncio.to_thread(_appd, AN.get, tenant, ref)


@app.get("/api/apps/{ref}/android/{what}", dependencies=[Depends(require_key)])
async def apps_android_file(ref: str, what: str, tenant: str = Depends(current_tenant)):
    from .appmaker.android import service as AN
    try:
        if what == "zip":
            f, name = await asyncio.to_thread(AN.zip_file, tenant, ref)
            return FileResponse(f, media_type="application/zip", filename=name, headers={"Cache-Control": "private, no-store"})
        if what == "apk":
            f, name = await asyncio.to_thread(AN.apk_file, tenant, ref)
            return FileResponse(f, media_type="application/vnd.android.package-archive", filename=name,
                                headers={"Cache-Control": "private, no-store"})
    except AN.AS.AppError as e:
        raise HTTPException(404, str(e))
    raise HTTPException(404, "not found")


@app.get("/api/app-apk/{token}/{name}")
async def app_apk(token: str, name: str):
    """Public by its random token (7 days): the preview APK her phone's installer downloads (sha256 checked on the phone)."""
    from .appmaker.android import service as AN
    try:
        f = await asyncio.to_thread(AN.apk_by_token, token, name)
    except AN.AndroidError:
        raise HTTPException(404, "not found")
    return FileResponse(f, media_type="application/vnd.android.package-archive", filename=name,
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@app.get("/api/app-zip/{token}/{name}")
async def app_zip(token: str, name: str):
    """Public by its random token (7 days): the Android Studio project of her app (open on a laptop)."""
    from .appmaker.android import service as AN
    try:
        f = await asyncio.to_thread(AN.file_by_token, token, name, "zip")
    except AN.AndroidError:
        raise HTTPException(404, "not found")
    return FileResponse(f, media_type="application/zip", filename=name, headers={"Cache-Control": "private, no-store"})


@app.get("/api/app-content/{app_key}")
async def app_content(app_key: str):
    """Public, read only: what an installed Hoola-made app shows (her public facts + public products; samples marked)."""
    from .appmaker.android import service as AN
    try:
        data = await asyncio.to_thread(AN.content, app_key)
    except AN.AndroidError:
        raise HTTPException(404, "not found")
    return JSONResponse(data, headers={"Cache-Control": "public, max-age=60"})


@app.get("/api/apps/{ref}/shots/{name:path}", dependencies=[Depends(require_key)])
async def apps_shot(ref: str, name: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    try:
        f = await asyncio.to_thread(A.shot_file, tenant, ref, name)
    except (A.AppError, ValueError):
        raise HTTPException(404, "not found")
    return FileResponse(f, headers={"Cache-Control": "private, max-age=300"})


@app.get("/api/app-preview/{token}")
async def app_preview_root(token: str):
    return RedirectResponse(f"/api/app-preview/{token}/", status_code=307)


@app.get("/api/app-preview/{token}/{path:path}")
async def app_preview(token: str, path: str = ""):
    """Public, by its random token: the tap-through prototype of an app design (noindex, strict CSP, no network)."""
    from .appmaker import service as A
    try:
        data, ctype, headers = await asyncio.to_thread(A.preview_file, token, path)
    except A.AppError:
        raise HTTPException(404, "not found")
    return Response(content=data, media_type=ctype, headers={**headers, "Access-Control-Allow-Origin": "*"})


# ---------------------------------------------------------------- v0.118 Brand Sahayak (brand designer; final artwork on her tap)
def _brand(fn, *a, **k):
    from .brand import service as brand
    try:
        return fn(*a, **k)
    except brand.BrandError as e:
        raise HTTPException(400, str(e))


@app.get("/api/brand", dependencies=[Depends(require_key)])
async def brand_all(tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return await asyncio.to_thread(brand.everything, tenant)


@app.get("/api/brand/designs", dependencies=[Depends(require_key)])
async def brand_designs(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return {"designs": await asyncio.to_thread(brand.designs, tenant, status, q)}


@app.post("/api/brand/designs", dependencies=[Depends(require_key)])
async def brand_make(body: dict, tenant: str = Depends(current_tenant)):
    """{brief, kind, sizes, festival, photo (file_id), layout, words {headline, sub, offer, cta, date, body}, ai_background, template}"""
    from .brand import service as brand
    words = body.get("words") if isinstance(body.get("words"), dict) else None
    return await asyncio.to_thread(_brand, brand.make, tenant, str(body.get("brief") or ""), str(body.get("kind") or ""),
                                   body.get("sizes"), str(body.get("festival") or ""), str(body.get("photo") or ""),
                                   str(body.get("layout") or ""), words, bool(body.get("ai_background")),
                                   str(body.get("template") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/brand/designs/{ref}", dependencies=[Depends(require_key)])
async def brand_design(ref: str, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return await asyncio.to_thread(_brand, brand.get, tenant, ref)


@app.delete("/api/brand/designs/{ref}", dependencies=[Depends(require_key)])
async def brand_delete(ref: str, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return await asyncio.to_thread(_brand, brand.delete, tenant, ref)


@app.post("/api/brand/designs/{ref}/photo", dependencies=[Depends(require_key)])
async def brand_photo(ref: str, file: UploadFile = File(...), conversation_id: str = Form(""),
                      tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "Photo 25 MB se badi hai.")
    return await asyncio.to_thread(_brand, brand.set_photo, tenant, ref, "", data, conversation_id)


@app.post("/api/brand/designs/{ref}/{action}", dependencies=[Depends(require_key)])
async def brand_act(ref: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """revise {instruction} | edit {fields, layout} | resize {sizes, add} | approve {force} (sends the card) |
    decide {yes, hash, reason} (ONLY her tap on the card) | copy | template {on}"""
    from .brand import service as brand
    conv = str(body.get("conversation_id") or "")
    if action == "revise":
        return await asyncio.to_thread(_brand, brand.revise, tenant, ref, str(body.get("instruction") or ""), conv)
    if action == "edit":
        fields = body.get("fields") if isinstance(body.get("fields"), dict) else {}
        return await asyncio.to_thread(_brand, brand.edit, tenant, ref, fields, str(body.get("layout") or ""), conv)
    if action == "resize":
        return await asyncio.to_thread(_brand, brand.resize, tenant, ref, body.get("sizes"), body.get("add", True) is not False, conv)
    if action == "approve":
        return await asyncio.to_thread(_brand, brand.request_approval, tenant, ref, bool(body.get("force")), conv)
    if action == "decide":
        return await asyncio.to_thread(_brand, brand.decide, tenant, ref, bool(body.get("yes")), str(body.get("hash") or ""),
                                       str(body.get("reason") or ""), conv)
    if action == "copy":
        return await asyncio.to_thread(_brand, brand.copy_design, tenant, ref)
    if action == "template":
        return await asyncio.to_thread(_brand, brand.copy_design, tenant, ref, body.get("on", True) is not False)
    raise HTTPException(400, "action = revise | edit | resize | approve | decide | copy | template")


@app.get("/api/brand/files/{design_id}/{name}", dependencies=[Depends(require_key)])
def brand_file(design_id: str, name: str, download: bool = False, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    path, mime = _brand(brand.file_path, tenant, design_id, name)
    return FileResponse(path, media_type=mime, filename=name if download else None)


@app.get("/api/brand/kit", dependencies=[Depends(require_key)])
async def brand_kit(tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return await asyncio.to_thread(brand.kit, tenant)


@app.put("/api/brand/kit", dependencies=[Depends(require_key)])
async def brand_kit_save(body: dict, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    keys = ("name", "tagline", "colors", "contact", "font", "tone", "rule", "rules", "state", "language", "nudge", "nudge_days")
    return await asyncio.to_thread(_brand, brand.save_kit, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/brand/logo", dependencies=[Depends(require_key)])
async def brand_logo(file: UploadFile | None = File(None), file_id: str = Form(""), clean_bg: bool = Form(False),
                     tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    data = await file.read() if file is not None else None
    if data is not None and len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Logo 15 MB se bada hai.")
    return await asyncio.to_thread(_brand, brand.set_logo, tenant, data, file_id, (file.filename if file else "logo.png"), clean_bg)


@app.get("/api/brand/logo", dependencies=[Depends(require_key)])
def brand_logo_get(tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    path, mime = _brand(brand.logo_file, tenant)
    return FileResponse(path, media_type=mime)


@app.get("/api/brand/festivals", dependencies=[Depends(require_key)])
async def brand_festivals(days: int = 60, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return {"festivals": await asyncio.to_thread(brand.upcoming, tenant, max(1, min(370, days)))}


# ---------------------------------------------------------------- v0.101 Kalam Sahayak (content writer; publishing on her tap)
def _kalam(fn, *a, **k):
    from .kalam import service as kalam
    try:
        return fn(*a, **k)
    except kalam.KalamError as e:
        raise HTTPException(400, str(e))


@app.get("/api/kalam", dependencies=[Depends(require_key)])
def kalam_all(tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return kalam.everything(tenant)


@app.get("/api/kalam/pieces", dependencies=[Depends(require_key)])
def kalam_pieces(kind: str = "", status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return {"pieces": kalam.pieces(tenant, kind, status, q, 120)}


@app.post("/api/kalam/write", dependencies=[Depends(require_key)])
async def kalam_write(body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return await asyncio.to_thread(_kalam, kalam.write, tenant, str(body.get("brief") or ""), str(body.get("kind") or ""),
                                   str(body.get("title") or ""), str(body.get("keyword") or ""), body.get("words"),
                                   str(body.get("lang") or ""), str(body.get("audience") or ""), body.get("file_ids"),
                                   body.get("urls"), body.get("product") if isinstance(body.get("product"), dict) else None,
                                   str(body.get("experience") or ""), bool(body.get("paid")), str(body.get("conversation_id") or ""))


@app.get("/api/kalam/pieces/{pid}", dependencies=[Depends(require_key)])
def kalam_get(pid: str, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return _kalam(kalam.get, tenant, pid)


@app.put("/api/kalam/pieces/{pid}", dependencies=[Depends(require_key)])
async def kalam_edit(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return await asyncio.to_thread(_kalam, kalam.edit, tenant, pid, body.get("body"), body.get("title"),
                                   body.get("meta") if isinstance(body.get("meta"), dict) else None)


@app.delete("/api/kalam/pieces/{pid}", dependencies=[Depends(require_key)])
def kalam_delete(pid: str, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return _kalam(kalam.delete, tenant, pid)


@app.post("/api/kalam/pieces/{pid}/{action}", dependencies=[Depends(require_key)])
async def kalam_action(pid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """revise | check | publish | decide (her tap on the publish card) | repurpose | files | result | copy | unpage"""
    from .kalam import service as kalam
    conv = str(body.get("conversation_id") or "")
    if action == "revise":
        return await asyncio.to_thread(_kalam, kalam.revise, tenant, pid, str(body.get("instruction") or ""), conv)
    if action == "check":
        return await asyncio.to_thread(_kalam, kalam.check, tenant, pid, body.get("web", True) is not False, conv)
    if action == "publish":
        return await asyncio.to_thread(_kalam, kalam.publish_request, tenant, pid, str(body.get("dest") or ""),
                                       str(body.get("where") or ""), body.get("to"), str(body.get("status") or "publish"),
                                       str(body.get("when") or ""), bool(body.get("force")), conv)
    if action == "decide":
        return await asyncio.to_thread(_kalam, kalam.decide_publish, tenant, pid, bool(body.get("yes")),
                                       str(body.get("note") or ""), str(body.get("url") or ""), conv, str(body.get("hash") or ""))
    if action == "repurpose":
        return await asyncio.to_thread(_kalam, kalam.repurpose, tenant, pid, body.get("kinds"), conv)
    if action == "files":
        return await asyncio.to_thread(_kalam, kalam.make_files, tenant, pid, conv)
    if action == "result":
        return _kalam(kalam.result, tenant, pid, body.get("views"), body.get("clicks"), body.get("orders"),
                      str(body.get("url") or ""), str(body.get("note") or ""))
    if action == "copy":
        return _kalam(kalam.copy_piece, tenant, pid)
    if action == "unpage":
        return _kalam(kalam.unpublish_page, tenant, pid)
    raise HTTPException(404, "unknown action")


@app.get("/api/kalam/ideas", dependencies=[Depends(require_key)])
async def kalam_ideas(days: int = 45, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return await asyncio.to_thread(kalam.ideas, tenant, max(7, min(120, days)))


@app.put("/api/kalam/settings", dependencies=[Depends(require_key)])
def kalam_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    keys = ("enabled", "business", "about", "audience", "language", "address", "contact", "website", "cta", "tone", "do_words",
            "dont_words", "rules", "ai_note", "facts")
    return _kalam(kalam.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/kalam/facts", dependencies=[Depends(require_key)])
def kalam_fact(body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return _kalam(kalam.add_fact, tenant, str(body.get("fact") or ""), str(body.get("source") or ""))


@app.post("/api/kalam/voice", dependencies=[Depends(require_key)])
async def kalam_voice(body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return await asyncio.to_thread(_kalam, kalam.learn_voice, tenant, str(body.get("text") or ""), body.get("file_ids"),
                                   body.get("urls"))


@app.put("/api/kalam/wordpress", dependencies=[Depends(require_key)])
async def kalam_wordpress(body: dict, tenant: str = Depends(current_tenant)):
    """Her own site: url + username + an Application Password (typed in the app only; sealed, never shown again)."""
    from .kalam import service as kalam
    return await asyncio.to_thread(_kalam, kalam.set_wordpress, tenant, str(body.get("url") or ""), str(body.get("user") or ""),
                                   str(body.get("app_password") or ""))


@app.delete("/api/kalam/wordpress", dependencies=[Depends(require_key)])
def kalam_wordpress_off(tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return kalam.forget_wordpress(tenant)


@app.get("/api/kalam/page/{token}")
def kalam_page(token: str):
    """A page she published with her Haan (public link)."""
    from .kalam import service as kalam
    html_text = kalam.page_by_token(token)
    if not html_text:
        raise HTTPException(404, "Page nahi mila")
    return HTMLResponse(html_text, headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:",
                                            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})


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
    return get_memory(tenant)


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


class UpiResultBody(BaseModel):
    txn_ref: str = Field(max_length=40)
    response: str = Field(default="", max_length=2000)   # the UPI app's own answer (NPCI response string)
    result: str = Field(default="", max_length=20)       # ok | cancelled | none (what Android reported)
    package: str = Field(default="", max_length=120)
    answer: str = Field(default="", max_length=8)        # her word on the card: done | not


@app.post("/api/bazar/upi/result", dependencies=[Depends(require_key)])
async def bazar_upi_result(body: UpiResultBody, tenant: str = Depends(current_tenant)):
    """v0.109 After 'Paisa bhejo': the phone reports what the UPI app said, or she taps Ho gaya / Nahi hua."""
    from .bazar import upiresult
    return await asyncio.to_thread(_bz, upiresult.record, tenant, body.txn_ref, body.response, body.result,
                                   body.package, body.answer)


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
    if kind not in ("pack", "feat", "gh", "mcp", "tv", "dir") or len(key) > 120:
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
    readonly: bool | None = None          # v0.143 GitHub MCP: only read tools
    toolsets: list[str] | None = None     # v0.143 GitHub MCP toolsets / v0.145 Supabase feature groups
    project: str | None = None            # v0.145 Supabase project ref


@app.get("/api/bazar/mcp/featured", dependencies=[Depends(require_key)])
def bazar_mcp_featured(tenant: str = Depends(current_tenant)):
    return {"connectors": _bz(bazar.mcp_featured, tenant)}


@app.post("/api/bazar/mcp/featured/{fid}", dependencies=[Depends(require_key)])
async def bazar_mcp_connect(fid: str, body: FeaturedIn, tenant: str = Depends(current_tenant)):
    try:
        return await asyncio.to_thread(bazar.mcp_connect_featured, tenant, fid, body.url, body.key, body.key_header,
                                       readonly=body.readonly, toolsets=body.toolsets, project=body.project)
    except BazarError as e:
        raise HTTPException(400, str(e))


class OneTapIn(BaseModel):
    ref: str
    keys: dict[str, str] = {}
    accept_caution: bool = False


@app.post("/api/bazar/mcp/one_tap", dependencies=[Depends(require_key)])
async def bazar_mcp_one_tap(body: OneTapIn, tenant: str = Depends(current_tenant)):
    """v0.154 'Ek tap mein jodo': hosted servers join directly, npm / PyPI ones run on the MCP runner box. Keys only
    from the app (never chat)."""
    try:
        return await asyncio.to_thread(bazar.mcp_one_tap, tenant, body.ref, body.keys, body.accept_caution)
    except BazarError as e:
        raise HTTPException(400, str(e))


@app.get("/api/bazar/mcp/runner", dependencies=[Depends(require_key)])
async def bazar_mcp_runner():
    from .bazar import runner as mcp_runner
    return await asyncio.to_thread(mcp_runner.health)


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


# ---------------- Aaj ka Din: one call for the home card — weather + today's meetings + next reminder ----------------
_day_weather: dict[str, tuple[float, dict]] = {}   # tenant → (fetched_at, weather; {} = last fetch failed)


@app.get("/api/day", dependencies=[Depends(require_key)])
async def day(tenant: str = Depends(current_tenant)):
    """v0.166 premium Aaj ka Din card: mausam (cached 15 min), aaj ki baaki meetings, agla reminder — one round trip."""
    from datetime import datetime, timedelta
    from . import gcal
    tz = life.tz_of(tenant)
    now = datetime.now(tz)
    out: dict = {"weather": None, "events": [], "next_reminder": None}

    hit = _day_weather.get(tenant)
    if hit and now.timestamp() - hit[0] < 900:
        out["weather"] = hit[1] or None
    else:
        try:
            w = await life.weather_for(tenant)
            _day_weather[tenant] = (now.timestamp(), w)
            out["weather"] = w
        except Exception:
            _day_weather[tenant] = (now.timestamp(), {})   # short-circuit failures too — never hammer open-meteo

    if gcal.configured():   # aaj ki meetings jo abhi baaqi hain (ya abhi chal rahi hain)
        try:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            views = await gcal.agenda(start, start + timedelta(days=1), keep_raw=True)
            evs: list[dict] = []
            for v in views:
                if v.get("all_day"):
                    continue
                try:
                    st = datetime.fromisoformat(v["_start_raw"])
                    en = datetime.fromisoformat(v["_end_raw"]) if v.get("_end_raw") else None
                    running = st <= now and (en is None or en > now)
                    if en is not None and en <= now:
                        continue   # khatam ho chuki
                    evs.append({"title": v.get("title") or "(no title)", "start": v.get("start") or "",
                                "location": (v.get("location") or "").strip(),
                                "attendees": len(v.get("attendees") or []),
                                "starts_in_mins": None if running else max(0, int((st - now).total_seconds() // 60)),
                                "running": running})
                except Exception:
                    continue
                if len(evs) >= 3:
                    break
            out["events"] = evs
        except Exception:
            pass

    try:
        rem = life.upcoming_reminders(tenant, limit=1)
        out["next_reminder"] = rem[0] if rem else None
    except Exception:
        pass
    return out


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


# ------------------------------------------------------------------ v0.164 projects, "Kaam ke folder" (CHAT_PROJECTS)
def _projects_on():
    from . import projects
    if not projects.enabled():
        raise HTTPException(404, "Projects are off (CHAT_PROJECTS)")
    return projects


def _proj_call(fn, *a):
    from . import projects
    try:
        return fn(*a)
    except projects.ProjectError as e:
        raise HTTPException(e.status, str(e))


class ProjectIn(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    instructions: str | None = Field(default=None, max_length=8000)
    memory: str | None = Field(default=None, max_length=8000)
    emoji: str | None = Field(default=None, max_length=8)


@app.get("/api/projects", dependencies=[Depends(require_key)])
def projects_list(tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return {"projects": p.list_for(tenant)}


@app.post("/api/projects", status_code=201, dependencies=[Depends(require_key)])
def projects_create(body: ProjectIn, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.create, tenant, body.name or "", body.instructions or "", body.emoji or "")


@app.get("/api/projects/{pid}", dependencies=[Depends(require_key)])
def projects_get(pid: str, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.get, tenant, pid)


@app.patch("/api/projects/{pid}", dependencies=[Depends(require_key)])
def projects_patch(pid: str, body: ProjectIn, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.patch, tenant, pid, body.name, body.instructions, body.memory, body.emoji)


@app.delete("/api/projects/{pid}", dependencies=[Depends(require_key)])
def projects_delete(pid: str, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.delete, tenant, pid)


@app.post("/api/projects/{pid}/files", status_code=201, dependencies=[Depends(require_key)])
async def projects_file(pid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """A file for the project (kept until she removes it; big ones are searched through her Gyaan)."""
    p = _projects_on()
    data = await file.read(p.MAX_FILE + 1)
    return await asyncio.to_thread(_proj_call, p.add_file, tenant, pid, file.filename or "file", data)


@app.delete("/api/projects/{pid}/files/{fid}", dependencies=[Depends(require_key)])
def projects_file_delete(pid: str, fid: str, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.remove_file, tenant, pid, fid)


# ------------------------------------------------------------------ v0.163 side panel (SIDE_PANEL)
def _panel_on():
    from . import panel
    if not panel.enabled():
        raise HTTPException(404, "Side panel is off (SIDE_PANEL)")
    return panel


def _panel_call(fn, *a):
    from . import panel
    try:
        return fn(*a)
    except panel.PanelError as e:
        raise HTTPException(e.status, str(e))


@app.get("/api/panel/library", dependencies=[Depends(require_key)])
def panel_library(kind: str = "", q: str = "", tenant: str = Depends(current_tenant)):
    """Banaya hua: every page, file, picture, video, website and app Hoola made for her (newest first)."""
    panel = _panel_on()
    return {"items": panel.library(tenant, kind[:10], q[:100])}


@app.get("/api/panel/files/{file_id}/info", dependencies=[Depends(require_key)])
def panel_file_info(file_id: str, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.file_info, tenant, file_id)


@app.get("/api/panel/files/{file_id}", dependencies=[Depends(require_key)])
def panel_file(file_id: str, download: int = 0, tenant: str = Depends(current_tenant)):
    """Her file with her login. Only images / video / audio / PDF are viewable; everything else is a download."""
    panel = _panel_on()
    data, mt, name, viewable = _panel_call(panel.file_bytes, tenant, file_id)
    from urllib.parse import quote
    disp = "inline" if viewable and not download else "attachment"
    return Response(content=data, media_type=mt, headers={
        "Content-Disposition": f"{disp}; filename*=UTF-8''{quote(name)}", "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store", "Content-Security-Policy": "default-src 'none'; img-src 'self'; media-src 'self'"
        if disp == "inline" and not mt.endswith("pdf") else "default-src 'none'; sandbox"})


@app.get("/api/panel/files/{file_id}/text", dependencies=[Depends(require_key)])
def panel_file_text(file_id: str, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.file_text, tenant, file_id)


@app.get("/api/panel/files/{file_id}/pdf", dependencies=[Depends(require_key)])
def panel_file_pdf(file_id: str, tenant: str = Depends(current_tenant)):
    """Word / Excel / PowerPoint as a PDF to look at (Gotenberg on the server)."""
    panel = _panel_on()
    pdf = _panel_call(panel.file_pdf, tenant, file_id)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": "inline", "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@app.get("/api/panel/pages/{aid}/source", dependencies=[Depends(require_key)])
def panel_page_source(aid: str, version: int = 0, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.page_source, tenant, aid, version)


@app.get("/api/panel/pages/{aid}/view", dependencies=[Depends(require_key)])
def panel_page_view(aid: str, version: int = 0, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.page_view, tenant, aid, version)


class PanelShareIn(BaseModel):
    kind: str = Field(max_length=8)
    id: str = Field(min_length=1, max_length=64)
    conversation_id: str = Field(default="", max_length=40)


@app.post("/api/panel/share", dependencies=[Depends(require_key)])
def panel_share(body: PanelShareIn, tenant: str = Depends(current_tenant)):
    """Share = a Haan card first (nothing is public until she taps it)."""
    panel = _panel_on()
    if body.conversation_id:
        _conv_or_404(body.conversation_id, tenant)
    return _panel_call(panel.ask_share, tenant, body.conversation_id, body.kind, body.id)


class PanelDecideIn(BaseModel):
    approve: bool


@app.post("/api/panel/share/{sid}", dependencies=[Depends(require_key)])
def panel_share_decide(sid: str, body: PanelDecideIn, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.decide_share, tenant, sid, body.approve)


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
def artifact_page(aid: str, version: int, exp: int = 0, sig: str = "", panel: int = 0):
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
    return HTMLResponse(artifacts.render(aid, version, page, state, panel=bool(panel)), headers=artifacts.headers())


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
_browser_memo: OrderedDict = OrderedDict()      # v0.190.1 P0: (kind, tenant, sid) -> (at, value), TTL 1 s
_BROWSER_MEMO_S = 1.0
_BROWSER_MEMO_MAX = 512
_browser_memo_lock = threading.Lock()


def _browser_memo_get(key: tuple):
    hit = None
    with _browser_memo_lock:
        pair = _browser_memo.get(key)
        if pair:
            at, val = pair
            if time.time() - at <= _BROWSER_MEMO_S:
                hit = val
            else:
                _browser_memo.pop(key, None)
    return hit


def _browser_memo_put(key: tuple, val) -> None:
    with _browser_memo_lock:
        _browser_memo[key] = (time.time(), val)
        _browser_memo.move_to_end(key)
        while len(_browser_memo) > _BROWSER_MEMO_MAX:
            _browser_memo.popitem(last=False)


@app.get("/api/browser/{sid}/live", dependencies=[Depends(require_key)])
def browser_live(sid: str, tenant: str = Depends(current_tenant)):
    hit = _browser_memo_get(("live", tenant, sid))   # v0.190.1 P0: the live page was polled ~90 rps during the
    if hit is not None:                              # load spiral - every hit is a fresh thread + dict read; a
        return hit                                   # 1 s memo caps the pile-up without changing what she sees
    from . import browser
    if sid.startswith("pcop_"):
        from .pc import operator
        op = operator.get(tenant, sid)
        if op is None:
            raise HTTPException(404, "not found")
        out = op.live()
    else:
        try:
            out = browser.live(tenant, sid)
        except browser.BrowserError as e:
            raise HTTPException(404, str(e))
    _browser_memo_put(("live", tenant, sid), out)
    return out


@app.get("/api/browser/{sid}/frame", dependencies=[Depends(require_key)])
def browser_frame(sid: str, tenant: str = Depends(current_tenant)):
    hit = _browser_memo_get(("frame", tenant, sid))  # same 1 s memo - the JPEG bytes are immutable
    if hit is not None:
        return Response(hit, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
    from . import browser
    if sid.startswith("pcop_"):
        from .pc import operator
        op = operator.get(tenant, sid)
        if op is None or not op.frame:
            raise HTTPException(404, "no frame yet")
        img = op.frame
    else:
        try:
            img = browser.frame(tenant, sid)
        except browser.BrowserError as e:
            raise HTTPException(404, str(e))
    _browser_memo_put(("frame", tenant, sid), img)
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


# ------------------------------------------------------------------ v0.98 one call at app open
@app.get("/api/bootstrap", dependencies=[Depends(require_key)])
def bootstrap(request: Request, conv: str = "", new: bool = False, tenant: str = Depends(current_tenant)):
    """Everything the app needs to open, in one round trip (it used to wait for 8 calls one after another): server
    health, the chat to use (hers if still valid, else a new one), account, lists, routines, avatar, actions the phone
    still has to run, and this month's AI spend vs her limit."""
    out: dict = {"health": healthz()}
    cid = ""
    if conv:
        with session() as s:
            c = s.get(Conversation, conv)
            if c is not None and c.tenant_id == tenant:
                cid = c.id
    from . import convs
    if not cid and not new:
        cid = convs.current(tenant)    # v0.158 sign-in / re-install / cleared app: her last chat, not an empty new one
    out["conversation_id"] = cid or create_conversation(tenant)["id"]
    out["conversation_new"] = not cid
    convs.mark(tenant, out["conversation_id"], "app")
    for key, fn in (("me", lambda: api_me(request)), ("lists", lambda: get_lists(tenant)),
                    ("routines", lambda: get_routines(tenant)["routines"]), ("avatar", lambda: avatar_get(tenant)),
                    ("pending_actions", lambda: pending_actions(tenant)["actions"])):
        try:
            out[key] = fn()
        except Exception as e:      # one part failing must not stop the app from opening
            log.warning("bootstrap %s failed: %s", key, e)
            out[key] = None
    try:
        from . import usage
        st = usage.state(tenant)
        inr = usage.usd_inr()
        out["usage"] = {"spent_inr": round(st["spent_usd"] * inr, 2), "limit_inr": round(st["limit_usd"] * inr, 2),
                        "pct": st["pct"], "warn": st["warn"], "over": st["over"]}
    except Exception:
        out["usage"] = None
    return out

