"""Santosh Artifacts: pages Santosh builds for the user, like Claude's artifacts.

From a text chat or a voice call, Santosh turns a request ("EMI calculator", "milk hisaab tracker", "Diwali sale
poster", "is data ka chart", "10th ka quiz") into one self-contained interactive HTML page. The app opens it full
screen, the user asks for changes (new versions), and can share a public link.

Security: pages are served with a CSP *sandbox* (opaque origin: no cookies, no Santosh API, no network calls except
listed CDNs for scripts/fonts, no form posts). The only way out is `window.santosh`, a tiny bridge the Santosh app
implements: storage.get/set/all (saved per page on the server) and ask (a short answer from Santosh's brain).
Outside the app (a shared link) storage stays in memory and ask is off.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import html as htmlmod
import json
import logging
import re
import secrets
import time
from typing import Any

from sqlalchemy import select

from .config import get_settings
from .db import Artifact, ArtifactState, ArtifactVersion, now, session
from .events import bus

log = logging.getLogger("santosh.artifacts")

MAX_HTML = 600_000
MAX_STATE_VALUE = 64_000
MAX_STATE_KEYS = 300
LINK_HOURS = 24
_building: dict[str, asyncio.Task] = {}
_ask_log: dict[str, list[float]] = {}

CDN_SCRIPT = "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com"
CSP = ("sandbox allow-scripts allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-downloads; "
       "default-src 'none'; "
       f"script-src 'unsafe-inline' 'unsafe-eval' blob: {CDN_SCRIPT}; "
       "style-src 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com; "
       "font-src data: https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
       "img-src data: blob: https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com; "
       "media-src data: blob:; worker-src blob:; connect-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'")

BUILDER = """You build "artifacts" for Santosh, an Indian AI coworker app: one self-contained, interactive HTML page that
the user opens full screen on an Android phone (WebView, 360-430 px wide) and may share as a link.

Make something genuinely useful and beautiful, not a template:
- Mobile first: single column, 16 px side padding, tap targets >= 44 px, no horizontal scroll, sticky header if useful.
- Polished: one clear visual idea, a restrained palette defined as CSS variables on :root, good type scale, real
  spacing, subtle shadows/radii, smooth but quick transitions. Support dark mode with @media (prefers-color-scheme: dark).
- India-ready: ₹ with Indian grouping (₹1,25,000 via toLocaleString('en-IN')), dates as 19 Oct 2026, km, °C.
  Write UI text in the user's language/script as asked (Hindi/Marathi in Devanagari with
  "Noto Sans Devanagari" from Google Fonts; Hinglish in Latin script). Default: simple English + Hinglish labels.
- Self-contained: inline CSS/JS. You MAY load libraries only from cdnjs.cloudflare.com, cdn.jsdelivr.net, unpkg.com
  (pin exact versions, e.g. https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js) and fonts from
  Google Fonts. The page has NO network access otherwise: never fetch() APIs; embed all data in the page. No external
  images: use inline SVG, CSS, emoji or canvas.
- Saving: localStorage is NOT available. To remember things (entries, progress, settings) use the async bridge
  window.santosh.storage: await santosh.storage.get(key) -> value|null, await santosh.storage.set(key, jsonValue),
  await santosh.storage.all() -> {key: value}. Load saved data on start; save after each change.
- AI help inside the page (optional, only when it adds real value): const answer = await santosh.ask("question");
  returns a short text answer from Santosh. Show a loading state; handle errors.
- Wrap every santosh.* call in try/catch so the page still works when opened from a shared link.
- Forms never submit anywhere (prevent default). No login screens, no payment collection, no fake data presented as real.
- Charts: Chart.js or inline SVG, labelled axes, ₹ formatting, readable in light and dark.
- Accessible: semantic HTML, labels for inputs, sufficient contrast.

Reply in exactly this format and nothing else:
TITLE: <2-5 word name>
SUMMARY: <one short line, what the page does>
<!doctype html>
...the complete HTML document...
"""

REVISE = """Below is the CURRENT version of the page. Apply the user's change request and return the COMPLETE updated
document in the same reply format (TITLE, SUMMARY, full HTML). Keep everything that wasn't asked to change, including
saved-data keys (so the user's saved entries keep working)."""


# ----------------------------------------------------------------------------- helpers
def _key() -> bytes:
    raw = get_settings().secret_key or "santosh-dev-secret"
    return hashlib.sha256(("artifact:" + raw).encode()).digest()


def sign(aid: str, version: int, exp: int) -> str:
    return hmac.new(_key(), f"{aid}:{version}:{exp}".encode(), hashlib.sha256).hexdigest()[:40]


def check(aid: str, version: int, exp: int, sig: str) -> bool:
    return exp >= time.time() and hmac.compare_digest(sign(aid, version, exp), sig or "")


def base_url() -> str:
    return (get_settings().public_base_url or "").rstrip("/")


def view_url(aid: str, version: int) -> str:
    exp = int(time.time()) + LINK_HOURS * 3600
    return f"{base_url()}/a/{aid}/{version}?exp={exp}&sig={sign(aid, version, exp)}"


def share_url(token: str) -> str:
    return f"{base_url()}/s/{token}" if token else ""


def public(a: Artifact) -> dict[str, Any]:
    return {"id": a.id, "title": a.title, "version": a.version, "status": a.status, "summary": a.summary,
            "error": a.error, "updated_at": (a.updated_at or a.created_at).isoformat(), "shared": bool(a.share_token)}


def _emit(a: Artifact) -> None:
    if a.conversation_id:
        try:
            bus.publish(a.conversation_id, "artifact", public(a))
        except Exception:
            log.exception("artifact event failed")


def parse(text: str) -> tuple[str, str, str]:
    """(title, summary, html) from the builder's reply."""
    t = (text or "").strip()
    t = re.sub(r"^```(?:html)?\s*", "", t)
    title = summary = ""
    m = re.search(r"^\s*TITLE:\s*(.+)$", t, re.M)
    if m:
        title = m.group(1).strip()[:120]
    m = re.search(r"^\s*SUMMARY:\s*(.+)$", t, re.M)
    if m:
        summary = m.group(1).strip()[:280]
    start = re.search(r"<!doctype html|<html", t, re.I)
    if not start:
        raise ValueError("no HTML in the reply")
    page = t[start.start():]
    end = page.lower().rfind("</html>")
    if end != -1:
        page = page[:end + 7]
    page = re.sub(r"\s*```\s*$", "", page)
    if len(page) < 200:
        raise ValueError("page too short")
    if not title:
        m = re.search(r"<title>(.*?)</title>", page, re.I | re.S)
        title = htmlmod.unescape(m.group(1).strip())[:120] if m else "Santosh page"
    return title, summary, page[:MAX_HTML]


async def _llm(system: str, prompt: str, max_tokens: int = 16000) -> str:
    """Claude when its key is set (best pages), else the low-cost brain (OmniRoute / GLM)."""
    st = get_settings()
    from .agent import llm
    if st.anthropic_api_key:
        from .agent.santosh import get_client
        msg = await get_client().messages.create(model=st.anthropic_model, max_tokens=max_tokens, system=system,
                                                 messages=[{"role": "user", "content": prompt}])
        return "".join(getattr(b, "text", "") for b in msg.content)
    brain = llm.cheap_brain()
    if not brain:
        raise RuntimeError("No AI model is configured")
    blocks, _, _ = await llm.openai_create(brain, system, [], [{"role": "user", "content": prompt}], min(max_tokens, 12000))
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


# ----------------------------------------------------------------------------- building
def create(tenant: str, conversation_id: str, request: str) -> Artifact:
    with session() as s:
        a = Artifact(tenant_id=tenant, conversation_id=conversation_id or "", title=_guess_title(request), status="building")
        s.add(a)
        s.flush()
        s.expunge(a)
    return a


def _guess_title(request: str) -> str:
    words = re.sub(r"\s+", " ", request or "").strip().split(" ")[:5]
    return (" ".join(words) or "Santosh page")[:60]


def get(tenant: str, aid: str) -> Artifact | None:
    with session() as s:
        a = s.get(Artifact, aid)
        if a is None or a.tenant_id != tenant or a.deleted:
            return None
        s.expunge(a)
        return a


def latest_html(aid: str, version: int | None = None) -> str | None:
    with session() as s:
        q = select(ArtifactVersion).where(ArtifactVersion.artifact_id == aid)
        q = q.where(ArtifactVersion.version == version) if version else q.order_by(ArtifactVersion.version.desc())
        v = s.scalars(q).first()
        return v.html if v else None


async def _build(aid: str, request: str, data: str = "") -> None:
    with session() as s:
        a = s.get(Artifact, aid)
        if a is None:
            return
        a.status, a.error, a.updated_at = "building", "", now()
        prev_version = a.version
        s.flush()
        snap = public(a)
        conv = a.conversation_id
    if conv:
        bus.publish(conv, "artifact", snap)
    current = latest_html(aid) if prev_version else None
    prompt = f"User request:\n{request.strip()}"
    if data:
        prompt += f"\n\nData to use (embed it in the page):\n{data[:60000]}"
    system = BUILDER + ("\n\n" + REVISE if current else "")
    if current:
        prompt = f"{prompt}\n\nCURRENT PAGE:\n{current}"
    try:
        reply = await _llm(system, prompt)
        try:
            title, summary, page = parse(reply)
        except ValueError:   # one retry with a nudge about the format
            reply = await _llm(system, prompt + "\n\nReturn TITLE, SUMMARY and the complete HTML document.")
            title, summary, page = parse(reply)
        with session() as s:
            a = s.get(Artifact, aid)
            if a is None:
                return
            n = a.version + 1
            s.add(ArtifactVersion(artifact_id=aid, version=n, html=page, note=request.strip()[:300]))
            a.version, a.title, a.summary, a.status, a.error, a.updated_at = n, title, summary, "ready", "", now()
            s.flush()
            s.expunge(a)
    except Exception as e:
        log.exception("artifact build failed")
        with session() as s:
            a = s.get(Artifact, aid)
            if a is None:
                return
            a.status = "ready" if a.version else "failed"
            a.error = f"Ye version nahi ban paya: {type(e).__name__}"[:300]
            a.updated_at = now()
            s.flush()
            s.expunge(a)
    _emit(a)


def start_build(aid: str, request: str, data: str = "") -> asyncio.Task:
    old = _building.get(aid)
    if old and not old.done():
        raise RuntimeError("Is page ka ek version abhi ban raha hai; thoda ruk kar boliye.")
    t = asyncio.get_running_loop().create_task(_build(aid, request, data))
    _building[aid] = t
    t.add_done_callback(lambda _t: _building.pop(aid, None) if _building.get(aid) is _t else None)
    return t


async def make(tenant: str, conversation_id: str, request: str, artifact_id: str = "", data: str = "",
               wait: float = 150) -> dict[str, Any]:
    """Create a new page or a new version of one. Waits up to `wait` seconds, then returns while it keeps building."""
    request = (request or "").strip()
    if len(request) < 3:
        raise ValueError("Batayiye kya banana hai")
    if artifact_id:
        a = get(tenant, artifact_id)
        if a is None:
            raise ValueError("That page wasn't found (use artifact_list for ids)")
        if conversation_id and a.conversation_id != conversation_id:
            with session() as s:
                row = s.get(Artifact, a.id)
                row.conversation_id = conversation_id
    else:
        a = create(tenant, conversation_id, request)
        _emit(a)
    task = start_build(a.id, request, data)
    if wait > 0:
        try:
            await asyncio.wait_for(asyncio.shield(task), wait)
        except asyncio.TimeoutError:
            pass
    a = get(tenant, a.id) or a
    return public(a)


# ----------------------------------------------------------------------------- serving
SHIM = """<script>(function(){var P={},n=0,M=%(state)s;
function B(){return window.SantoshBridge&&typeof window.SantoshBridge.postMessage==='function'?window.SantoshBridge:null}
function call(op,a){var b=B();if(!b){if(op==='storage.get')return Promise.resolve(M.hasOwnProperty(a.key)?M[a.key]:null);
if(op==='storage.set'){if(a.value===null||a.value===undefined)delete M[a.key];else M[a.key]=a.value;return Promise.resolve(true)}
if(op==='storage.all')return Promise.resolve(JSON.parse(JSON.stringify(M)));
return Promise.reject(new Error('Santosh app mein kholiye'))}
return new Promise(function(res,rej){var id='c'+(++n);P[id]=[res,rej];b.postMessage(JSON.stringify({id:id,op:op,args:a||{}}))})}
window.__santoshReply=function(id,ok,v){var p=P[id];if(!p)return;delete P[id];ok?p[0](v):p[1](new Error(String(v)))};
try{Object.defineProperty(window,'localStorage',{get:function(){var s={getItem:function(k){return M.hasOwnProperty(k)?String(M[k]):null},setItem:function(k,v){M[k]=String(v);call('storage.set',{key:k,value:String(v)})},removeItem:function(k){delete M[k];call('storage.set',{key:k,value:null})},clear:function(){M={}},key:function(i){return Object.keys(M)[i]||null}};Object.defineProperty(s,'length',{get:function(){return Object.keys(M).length}});return s}})}catch(e){}
window.santosh={artifactId:%(aid)s,version:%(ver)s,get inApp(){return !!B()},
storage:{get:function(k){return call('storage.get',{key:String(k)})},set:function(k,v){return call('storage.set',{key:String(k),value:v===undefined?null:v})},
remove:function(k){return call('storage.set',{key:String(k),value:null})},all:function(){return call('storage.all',{})}},
ask:function(q){return call('ask',{question:String(q)})}};})();</script>"""


def render(aid: str, version: int, page: str, state: dict[str, Any] | None = None) -> str:
    """The page plus the window.santosh bridge. `state` (only for the owner's own signed link) pre-fills saved data so
    pages that read storage synchronously at start see it."""
    st = json.dumps(state or {}, ensure_ascii=False).replace("</", "<\\/")
    shim = SHIM % {"aid": json.dumps(aid), "ver": int(version), "state": st}
    m = re.search(r"<head[^>]*>", page, re.I)
    if m:
        return page[:m.end()] + shim + page[m.end():]
    m = re.search(r"<html[^>]*>", page, re.I)
    if m:
        return page[:m.end()] + "<head>" + shim + "</head>" + page[m.end():]
    return shim + page


def headers() -> dict[str, str]:
    return {"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow", "Cache-Control": "private, max-age=60",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()"}


# ----------------------------------------------------------------------------- user actions
def list_for(tenant: str, limit: int = 50) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(Artifact).where(Artifact.tenant_id == tenant, Artifact.deleted.is_(False))
                         .order_by(Artifact.updated_at.desc()).limit(limit)).all()
        return [public(a) for a in rows]


def detail(tenant: str, aid: str) -> dict[str, Any] | None:
    a = get(tenant, aid)
    if a is None:
        return None
    with session() as s:
        vs = s.scalars(select(ArtifactVersion).where(ArtifactVersion.artifact_id == aid)
                       .order_by(ArtifactVersion.version.desc())).all()
        versions = [{"version": v.version, "created_at": v.created_at.isoformat(), "note": v.note} for v in vs]
    return {**public(a), "versions": versions, "share_url": share_url(a.share_token)}


def set_share(tenant: str, aid: str, on: bool) -> dict[str, Any] | None:
    with session() as s:
        a = s.get(Artifact, aid)
        if a is None or a.tenant_id != tenant or a.deleted:
            return None
        if on and not a.share_token:
            a.share_token = secrets.token_urlsafe(16)
        if not on:
            a.share_token = ""
        return {"shared": bool(a.share_token), "share_url": share_url(a.share_token)}


def delete(tenant: str, aid: str) -> bool:
    with session() as s:
        a = s.get(Artifact, aid)
        if a is None or a.tenant_id != tenant:
            return False
        a.deleted, a.share_token = True, ""
        for st in s.scalars(select(ArtifactState).where(ArtifactState.artifact_id == aid)).all():
            s.delete(st)
        return True


def by_share(token: str) -> Artifact | None:
    if not token or len(token) < 10:
        return None
    with session() as s:
        a = s.scalars(select(Artifact).where(Artifact.share_token == token, Artifact.deleted.is_(False))).first()
        if a:
            s.expunge(a)
        return a


def state_all(tenant: str, aid: str) -> dict[str, Any] | None:
    if get(tenant, aid) is None:
        return None
    with session() as s:
        return {r.key: (r.value or {}).get("v") for r in
                s.scalars(select(ArtifactState).where(ArtifactState.artifact_id == aid)).all()}


def state_set(tenant: str, aid: str, key: str, value: Any) -> None:
    if get(tenant, aid) is None:
        raise KeyError(aid)
    key = str(key)[:120]
    if not key:
        raise ValueError("empty key")
    if value is not None and len(json.dumps(value, ensure_ascii=False)) > MAX_STATE_VALUE:
        raise ValueError("value too large (64 KB max)")
    with session() as s:
        row = s.scalars(select(ArtifactState).where(ArtifactState.artifact_id == aid, ArtifactState.key == key)).first()
        if value is None:
            if row:
                s.delete(row)
            return
        if row is None:
            n = len(s.scalars(select(ArtifactState.id).where(ArtifactState.artifact_id == aid)).all())
            if n >= MAX_STATE_KEYS:
                raise ValueError("too many saved keys for this page")
            s.add(ArtifactState(artifact_id=aid, key=key, value={"v": value}))
        else:
            row.value, row.updated_at = {"v": value}, now()


async def ask(tenant: str, aid: str, question: str) -> str:
    a = get(tenant, aid)
    if a is None:
        raise KeyError(aid)
    q = (question or "").strip()[:2000]
    if not q:
        raise ValueError("empty question")
    hits = [t for t in _ask_log.get(tenant, []) if t > time.time() - 3600]
    if len(hits) >= 60:
        raise ValueError("Bahut saare sawaal; thodi der baad poochiye")
    _ask_log[tenant] = hits + [time.time()]
    system = (f"You are Santosh, answering a question asked from inside the user's page '{a.title}' ({a.summary}). "
              "Answer briefly and concretely (max 120 words), in the language of the question. Plain text only.")
    return (await _llm(system, q, max_tokens=600)).strip()[:4000]
