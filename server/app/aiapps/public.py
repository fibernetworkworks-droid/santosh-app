"""v0.785 HOOLA AI APPS - D2: the PUBLIC surface (hosted chat page, embed bubble, JSON routes).

None of these routes takes her key: they answer her customers. So every one of them checks, every time:
  - the app exists, is LIVE (a draft or a paused app is a plain 404 - a draft is never revealed), and the channel it is
    reached through is on (`page` for the page and its JSON, `embed` for ?embed=1 and embed.js);
  - the visitor agreed to the notice first (DPDP): consent creates the session, the token is the visitor's only key to
    their own conversation (history and feedback are fenced to it);
  - limits per IP (30 chats / 10 minutes) and per session (60 / hour), text <= 2000 characters.
Only PUBLIC soul fields ever leave: name, kind, opening, suggested questions, notice, form, show_sources, feedback.
Her facts, about, persona, refused topics and limits never do. The page builds every server string with textContent.
"""
from __future__ import annotations

import asyncio
import html
import json
import re
import threading
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from . import runtime as RT
from . import store as ST
from .models import AiApp

CODE = re.compile(r"^[A-Za-z0-9_-]{1,24}$")
IP_LIMIT = (30, 600)          # chats per IP per 10 minutes
SESSION_LIMIT = (60, 3600)    # chats per session per hour
PUBLIC_FIELDS = ("name", "kind", "opening", "suggested", "notice", "form", "show_sources", "feedback")


class _Window:
    """Sliding-window counter per key (an IP, a session). In memory; a restart forgets."""

    def __init__(self, n: int, secs: int):
        self.n, self.secs = n, secs
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> int:
        """0 = allowed (and counted); else seconds until the next one may go."""
        t = time.monotonic()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and t - q[0] >= self.secs:
                q.popleft()
            if len(q) >= self.n:
                return max(1, int(self.secs - (t - q[0])) + 1)
            q.append(t)
            if len(self._hits) > 20000:                 # never grow without end
                for k in [k for k, v in self._hits.items() if not v][:5000]:
                    self._hits.pop(k, None)
            return 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


IP_WINDOW = _Window(*IP_LIMIT)
SESSION_WINDOW = _Window(*SESSION_LIMIT)


def live_app(code: str, channel: str = "page") -> AiApp | None:
    """The app answering at this code through this channel, or None (unknown / draft / paused / channel off)."""
    if not CODE.match(str(code or "")):
        return None
    a = ST.by_code(code)
    if a is None or a.status != "live" or not a.live_version:
        return None
    if not ST._j(a.channels, {}).get(channel):
        return None
    return a


def public_info(a: AiApp) -> dict[str, Any]:
    soul, _v = ST.live_soul(a)
    out = {k: soul.get(k) for k in PUBLIC_FIELDS}
    out["name"] = out.get("name") or a.name
    out["code"] = a.code
    out["label"] = "AI assistant"
    return out


def client_ip(request) -> str:
    """The visitor's address: the last X-Forwarded-For hop (the one the front door added), else the socket."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        last = xff.split(",")[-1].strip()
        if last:
            return last[:64]
    return (request.client.host if request.client else "") or "unknown"


# ---------------------------------------------------------------- the page
PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<title>__TITLE__</title>
<style>
:root{--bg:#0B0A1A;--panel:#151229;--line:#FFFFFF14;--ink:#F4F2FF;--mut:#B9B3DA;--acc:#FFB15C;--onacc:#1B1030;--vio:#7C5CFF;--bad:#F87171}
@media (prefers-color-scheme: light){:root{--bg:#FFFFFF;--panel:#F5F4FA;--line:#0000001A;--ink:#17142B;--mut:#5B5778;--acc:#C45A00;--onacc:#FFFFFF;--vio:#5B3FE0}}
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;display:flex;flex-direction:column}
header{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--line)}
header h1{font-size:17px;font-weight:600;margin:0;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tag{font-size:12px;padding:2px 8px;border-radius:999px;border:1px solid var(--vio);color:var(--ink)}
main{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;max-width:720px;width:100%;margin:0 auto}
.msg{max-width:85%;padding:10px 14px;border-radius:16px;white-space:pre-wrap;word-wrap:break-word}
.me{align-self:flex-end;background:var(--acc);color:var(--onacc);border-bottom-right-radius:4px}
.ai{align-self:flex-start;background:var(--panel);border:1px solid var(--line);border-bottom-left-radius:4px}
.src{font-size:12px;color:var(--mut);margin-top:6px}
.fb{display:flex;gap:6px;margin-top:6px}.fb button{font-size:13px;padding:2px 10px;border-radius:999px;border:1px solid var(--line);background:transparent;color:var(--mut);cursor:pointer}
.fb button.on{border-color:var(--acc);color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chips button{font:inherit;font-size:14px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:12px}
.card p{margin:0;color:var(--mut);font-size:14px}
.primary{font:inherit;font-weight:600;padding:10px 16px;border:0;border-radius:12px;background:var(--acc);color:var(--onacc);cursor:pointer}
.err{color:var(--bad);font-size:14px}
form#ask{display:flex;gap:8px;padding:12px 16px calc(12px + env(safe-area-inset-bottom));border-top:1px solid var(--line);max-width:720px;width:100%;margin:0 auto}
textarea{flex:1;font:inherit;resize:none;min-height:44px;max-height:140px;padding:10px 12px;border-radius:12px;border:1px solid var(--line);background:var(--panel);color:var(--ink)}
label{font-size:14px;color:var(--mut);display:flex;flex-direction:column;gap:4px}
label input,label select{font:inherit;padding:8px 10px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.hidden{display:none!important}.dots{color:var(--mut);font-size:14px}
</style></head>
<body>
<header><h1 id="name">__TITLE__</h1><span class="tag" id="label">AI assistant</span></header>
<main id="log" aria-live="polite"></main>
<form id="ask" class="hidden"><textarea id="q" maxlength="2000" rows="1" placeholder="Type your question" aria-label="Your question"></textarea><button class="primary" type="submit">Send</button></form>
<script>
(function(){
"use strict";
var CODE=__CODE__, EMBED=__EMBED__;
var BASE="/api/aiapp-pub/"+encodeURIComponent(CODE), Q=EMBED?"?embed=1":"";
var KEY="hoola_aiapp_"+CODE+(EMBED?"_e":""), INFO=null, busy=false;
var log=document.getElementById("log"), form=document.getElementById("ask"), q=document.getElementById("q");
function el(tag,cls,text){var e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=String(text);return e;}
function tok(){try{return localStorage.getItem(KEY)||"";}catch(e){return "";}}
function setTok(t){try{if(t)localStorage.setItem(KEY,t);else localStorage.removeItem(KEY);}catch(e){}}
function api(path,opts){opts=opts||{};var h={"Content-Type":"application/json"};var t=tok();if(t)h["X-Visitor-Token"]=t;
 return fetch(BASE+path+Q,{method:opts.method||"GET",headers:h,body:opts.body?JSON.stringify(opts.body):undefined,credentials:"omit"})
 .then(function(r){return r.json().catch(function(){return {};}).then(function(j){j=j||{};j._status=r.status;return j;});});}
function scroll(){log.scrollTop=log.scrollHeight;}
function aiMsg(text,sources,mid){var b=el("div","msg ai",text);
 if(INFO&&INFO.show_sources&&sources&&sources.length){var t=[];sources.forEach(function(s){if(s&&s.title)t.push(String(s.title));});if(t.length)b.appendChild(el("div","src","Source: "+t.join(", ")));}
 if(INFO&&INFO.feedback&&mid){var f=el("div","fb"),up=el("button",null,"Helpful"),dn=el("button",null,"Not right");
  up.type=dn.type="button";up.setAttribute("aria-label","This answer helped");dn.setAttribute("aria-label","This answer was not right");
  function rate(good,btn){api("/feedback",{method:"POST",body:{message_id:mid,good:good}}).then(function(j){if(j._status===200){up.classList.remove("on");dn.classList.remove("on");btn.classList.add("on");}});}
  up.onclick=function(){rate(true,up);};dn.onclick=function(){rate(false,dn);};f.appendChild(up);f.appendChild(dn);b.appendChild(f);}
 log.appendChild(b);scroll();}
function meMsg(text){log.appendChild(el("div","msg me",text));scroll();}
function chips(){if(!INFO.suggested||!INFO.suggested.length)return;var c=el("div","chips");c.id="chips";
 INFO.suggested.forEach(function(s){var b=el("button",null,s);b.type="button";b.onclick=function(){send(String(s));};c.appendChild(b);});log.appendChild(c);}
var formBox=null;
function buildForm(){if(INFO.kind!=="form"||!INFO.form||!INFO.form.length)return;formBox=el("div","card");
 INFO.form.forEach(function(f){var l=el("label",null,f.label+(f.required?" *":""));var i;
  if(f.type==="choice"){i=document.createElement("select");(f.options||[]).forEach(function(o){var op=el("option",null,o);op.value=o;i.appendChild(op);});}
  else if(f.type==="long_text"){i=document.createElement("textarea");}
  else{i=document.createElement("input");i.type={number:"number",phone:"tel",email:"email",date:"date"}[f.type]||"text";}
  i.name=f.key;i.setAttribute("data-key",f.key);if(f.required)i.required=true;l.appendChild(i);formBox.appendChild(l);});
 log.appendChild(formBox);}
function inputs(){var o={};if(!formBox)return o;formBox.querySelectorAll("[data-key]").forEach(function(i){o[i.getAttribute("data-key")]=i.value;});return o;}
function send(text){if(busy)return;text=String(text||"").trim();if(!text&&!formBox)return;busy=true;
 var ch=document.getElementById("chips");if(ch)ch.remove();if(text)meMsg(text);var d=el("div","dots","Thinking...");log.appendChild(d);scroll();
 api("/chat",{method:"POST",body:{text:text,inputs:inputs()}}).then(function(j){d.remove();busy=false;
  if(j._status===401){setTok("");consent();return;}
  if(j._status!==200){log.appendChild(el("div","err",j.detail||j.error||"Something went wrong. Please try again."));scroll();return;}
  aiMsg(j.reply,j.sources,j.message_id);}).catch(function(){d.remove();busy=false;log.appendChild(el("div","err","No connection. Please try again."));});}
form.addEventListener("submit",function(e){e.preventDefault();var v=q.value;q.value="";send(v);});
q.addEventListener("keydown",function(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();form.requestSubmit();}});
function start(hist){log.textContent="";if(INFO.opening)aiMsg(INFO.opening,null,null);
 (hist||[]).forEach(function(m){if(m.q)meMsg(m.q);aiMsg(m.a,m.sources,m.id);});buildForm();if(!hist||!hist.length)chips();form.classList.remove("hidden");q.focus();}
function consent(){log.textContent="";form.classList.add("hidden");var c=el("div","card");c.appendChild(el("strong",null,"Before you start"));
 c.appendChild(el("p",null,INFO.notice));var b=el("button","primary","I agree");b.type="button";var e=el("div","err");
 b.onclick=function(){b.disabled=true;api("/session",{method:"POST",body:{consent:true}}).then(function(j){if(j.token){setTok(j.token);start([]);}else{b.disabled=false;e.textContent=j.detail||"Please try again.";}});};
 c.appendChild(b);c.appendChild(e);log.appendChild(c);}
api("").then(function(j){if(j._status!==200){log.appendChild(el("p","err","This assistant is not available right now."));return;}INFO=j;
 document.getElementById("name").textContent=j.name;document.title=j.name;document.getElementById("label").textContent=j.label||"AI assistant";
 if(!tok()){consent();return;}api("/history").then(function(h){if(h._status===200)start(h.messages||[]);else{setTok("");consent();}});});
})();
</script></body></html>"""

EMBED_JS = r"""(function(){
"use strict";
if(window.__hoolaAiApp&&window.__hoolaAiApp[__CODE__])return;window.__hoolaAiApp=window.__hoolaAiApp||{};window.__hoolaAiApp[__CODE__]=1;
var SRC=__SRC__, open=false, frame=null;
var b=document.createElement("button");b.type="button";b.setAttribute("aria-label","Chat with our AI assistant");b.textContent="Chat";
b.style.cssText="position:fixed;right:20px;bottom:20px;z-index:2147483646;width:60px;height:60px;border-radius:30px;border:0;"+
 "background:#FFB15C;color:#1B1030;font:600 14px system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.25);cursor:pointer";
b.onclick=function(){open=!open;if(!frame){frame=document.createElement("iframe");frame.src=SRC;frame.title="AI assistant";
 frame.setAttribute("sandbox","allow-scripts allow-same-origin allow-forms");frame.setAttribute("referrerpolicy","no-referrer");
 frame.setAttribute("allow","");frame.style.cssText="position:fixed;right:20px;bottom:90px;z-index:2147483647;width:min(380px,calc(100vw - 40px));"+
 "height:min(600px,calc(100vh - 120px));border:1px solid rgba(0,0,0,.12);border-radius:16px;background:#fff;box-shadow:0 12px 40px rgba(0,0,0,.3)";
 document.body.appendChild(frame);}frame.style.display=open?"block":"none";b.textContent=open?"Close":"Chat";};
(document.body?Promise.resolve():new Promise(function(r){document.addEventListener("DOMContentLoaded",r);})).then(function(){document.body.appendChild(b);});
})();
"""


def _js(v: str) -> str:
    """A JSON string literal that is safe inside a <script> block."""
    return json.dumps(str(v)).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def page_html(a: AiApp, embed: bool) -> str:
    title = html.escape(public_info(a).get("name") or "AI assistant")
    return (PAGE.replace("__TITLE__", title).replace("__CODE__", _js(a.code))
            .replace("__EMBED__", "true" if embed else "false"))


def page_headers(embed: bool) -> dict[str, str]:
    csp = ("default-src 'self' 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'none'; "
           "object-src 'none'; frame-ancestors " + ("*" if embed else "'none'"))
    h = {"Content-Security-Policy": csp, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
         "Cache-Control": "no-store"}
    if not embed:
        h["X-Frame-Options"] = "DENY"
    return h


# ---------------------------------------------------------------- routes
def make_router(require_key, current_tenant):  # noqa: ARG001 - the house signature; none of these routes takes her key
    r = APIRouter()
    NOT_FOUND = "This assistant was not found."

    def _channel(request: Request) -> str:
        return "embed" if request.query_params.get("embed") in ("1", "true") else "page"

    async def _app(code: str, request: Request) -> tuple[AiApp, str]:
        ch = _channel(request)
        a = await asyncio.to_thread(live_app, code, ch)
        if a is None:
            raise HTTPException(404, NOT_FOUND)
        return a, ch

    async def _session(a: AiApp, request: Request) -> str:
        tok = request.headers.get("x-visitor-token", "").strip()
        sid = await asyncio.to_thread(RT.session_for, a, tok) if tok.startswith("avs_") and len(tok) < 120 else ""
        if not sid:
            raise HTTPException(401, "Please agree to the notice first.")
        return sid

    @r.get("/ai/{code}", response_class=HTMLResponse)
    async def page(code: str, request: Request):
        a, ch = await _app(code, request)
        embed = ch == "embed"
        return HTMLResponse(page_html(a, embed), headers=page_headers(embed))

    @r.get("/ai/{code}/embed.js")
    async def embed_js(code: str, request: Request):
        a = await asyncio.to_thread(live_app, code, "embed")
        if a is None:
            raise HTTPException(404, NOT_FOUND)
        src = str(request.base_url).rstrip("/") + f"/ai/{a.code}?embed=1"
        body = EMBED_JS.replace("__CODE__", _js(a.code)).replace("__SRC__", _js(src))
        return Response(body, media_type="application/javascript",
                        headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"})

    @r.get("/api/aiapp-pub/{code}")
    async def info(code: str, request: Request):
        a, _ch = await _app(code, request)
        return await asyncio.to_thread(public_info, a)

    @r.post("/api/aiapp-pub/{code}/session")
    async def new_session(code: str, request: Request, body: dict = Body(default={})):
        a, ch = await _app(code, request)
        if (body or {}).get("consent") is not True:
            raise HTTPException(400, "Please read the notice and tap I agree first.")
        wait = IP_WINDOW.hit("s:" + client_ip(request))
        if wait:
            return JSONResponse({"detail": "Too many requests. Please wait a little."}, status_code=429,
                                headers={"Retry-After": str(wait)})
        _sid, tok = await asyncio.to_thread(RT.open_session, a, ch, "", True)
        return {"token": tok}

    @r.post("/api/aiapp-pub/{code}/chat")
    async def chat(code: str, request: Request, body: dict = Body(default={})):
        a, ch = await _app(code, request)
        sid = await _session(a, request)
        b = dict(body or {})
        text = str(b.get("text") or "")
        if len(text) > RT.MAX_Q:
            raise HTTPException(413, f"Please keep it under {RT.MAX_Q} characters.")
        wait = IP_WINDOW.hit("c:" + client_ip(request)) or SESSION_WINDOW.hit(sid)
        if wait:
            return JSONResponse({"detail": "Too many messages. Please wait a little."}, status_code=429,
                                headers={"Retry-After": str(wait)})
        inputs = b.get("inputs") if isinstance(b.get("inputs"), dict) else None
        try:
            out = await asyncio.to_thread(RT.answer, a, text, ch, sid, inputs)
        except ST.AppError as e:
            raise HTTPException(e.code, str(e))
        return {"reply": out.get("reply", ""), "outcome": out.get("outcome", ""), "sources": out.get("sources") or [],
                "message_id": out.get("message_id", "")}

    @r.get("/api/aiapp-pub/{code}/history")
    async def hist(code: str, request: Request):
        a, _ch = await _app(code, request)
        sid = await _session(a, request)
        rows = await asyncio.to_thread(RT.history, a, sid)
        return {"messages": [{"id": m["id"], "q": m["q"], "a": m["a"], "sources": m["sources"], "at": m["at"]} for m in rows]}

    @r.post("/api/aiapp-pub/{code}/feedback")
    async def fb(code: str, request: Request, body: dict = Body(default={})):
        a, _ch = await _app(code, request)
        sid = await _session(a, request)
        b = dict(body or {})
        mid = str(b.get("message_id") or "")
        if not mid:
            raise HTTPException(400, "message_id is needed.")
        try:
            return await asyncio.to_thread(RT.feedback, a, sid, mid, 1 if b.get("good") else -1)
        except ST.AppError as e:
            raise HTTPException(e.code, str(e))

    return r
