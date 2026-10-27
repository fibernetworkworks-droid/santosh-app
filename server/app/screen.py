"""v0.127 Hoola Screen: a VIEW-ONLY live board of Hoola's work for a second screen.

A mini screen / TV / monitor connected to the phone (HDMI or wireless display) shows it through the phone app's
Android Presentation; any other browser (tablet, laptop, smart-TV browser) can open the same page by its link.

Safety:
- The link is a signed, read-only token (tenant + expiry + her revoke version). It can only READ this board.
  Nothing can be approved, paid, typed or sent from it; every Haan / payment / OTP stays on her phone.
- The board shows only what a lock-screen notification already shows (push.render) and short live-step labels,
  with long digit runs masked; never tool inputs or outputs, never OTP / password asks' content.
- "Saare link band karo" bumps her version so every old link stops at once.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from .config import get_settings
from .db import Base, Conversation, Event, session

LINK_DAYS = 30
MAX_DAYS = 90
CARD_HOURS = 24          # cards from the last day
ACTIVE_S = 600           # a step not finished within 10 min is no longer shown as "now"
SKIP_CARD = {"message", "device_action", "home_device", "bt_request"}
MASK_RE = re.compile(r"\d[\d \-]{4,}\d")
FALLBACK = {"operator_ask": "Website job ko aapka jawab chahiye", "bazar_approval": "Approve karein",
            "employee_ask": "Aapki haan chahiye", "ask_form": "Form bharna hai", "pc_file": "Nayi file",
            "email_draft": "Email draft taiyaar", "studio_approval": "Video ka kharcha: aapki haan"}
SECRET_ASK = re.compile(r"\b(otp|password|pin|cvv|passcode)\b", re.I)


class ScreenKey(Base):
    """Her revoke version: links carry it; bumping it ends every link given before."""
    __tablename__ = "screen_keys"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ver: Mapped[int] = mapped_column(Integer, default=1)


class ScreenError(Exception):
    pass


# ----------------------------------------------------------------------------- link
def _key() -> bytes:
    st = get_settings()
    return f"screen:{st.secret_key or st.api_key or 'hoola-screen'}".encode()


def _ver(tenant: str) -> int:
    with session() as s:
        row = s.get(ScreenKey, tenant)
        return row.ver if row else 1


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(tenant: str, days: int = LINK_DAYS) -> tuple[str, int]:
    days = max(1, min(MAX_DAYS, int(days or LINK_DAYS)))
    exp = int(time.time()) + days * 86400
    body = _b64(json.dumps({"t": tenant, "e": exp, "v": _ver(tenant)}, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest()[:18])
    return f"{body}.{sig}", exp


def tenant_of(token: str) -> str:
    """The tenant this view-only link belongs to, or ScreenError."""
    try:
        body, sig = (token or "").split(".", 1)
        good = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest()[:18])
        if not hmac.compare_digest(good, sig):
            raise ValueError
        d = json.loads(_unb64(body))
    except Exception:
        raise ScreenError("Yeh link sahi nahi hai.")
    if int(d.get("e") or 0) < time.time():
        raise ScreenError("Yeh link purana ho gaya. Phone par naya link banaiye.")
    if int(d.get("v") or 0) != _ver(str(d.get("t"))):
        raise ScreenError("Yeh link band kar diya gaya hai.")
    return str(d["t"])


def link(tenant: str, base: str = "", days: int = LINK_DAYS) -> dict[str, Any]:
    tok, exp = make_token(tenant, days)
    base = (base or get_settings().public_base_url or "").rstrip("/")
    path = f"/screen/{tok}"
    return {"path": path, "url": f"{base}{path}" if base else path, "expires": exp,
            "expires_on": datetime.fromtimestamp(exp, timezone.utc).date().isoformat(),
            "say": "Yeh link sirf dekhne ke liye hai: is par koi haan / payment nahi ho sakta."}


def revoke(tenant: str) -> dict[str, Any]:
    with session() as s:
        row = s.get(ScreenKey, tenant)
        if row is None:
            s.add(ScreenKey(tenant_id=tenant, ver=2))
        else:
            row.ver = (row.ver or 1) + 1
    return {"ok": True, "say": "Saare purane screen link band. Phone par naya link ban jayega."}


# ----------------------------------------------------------------------------- board
def _mask(text: Any, n: int = 160) -> str:
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    t = MASK_RE.sub(lambda m: "•" * 4 + re.sub(r"\D", "", m.group(0))[-2:], t)
    return t[:n]


def _name(tenant: str) -> str:
    try:
        from .avatar.service import persona
        return persona(tenant)[0] or "Hoola"
    except Exception:
        return "Hoola"


def _card(kind: str, p: dict, name: str) -> tuple[str, str] | None:
    if kind in SKIP_CARD:
        return None
    try:
        from . import push
        shown = push.render(kind, p, name)
    except Exception:
        shown = None
    if not shown:
        try:
            from . import push
            if kind not in push.PUSH_KINDS:
                return None
        except Exception:
            return None
        shown = (FALLBACK.get(kind, "Naya card"), "Aapke phone par dekhiye.")
    title, body = shown
    if SECRET_ASK.search(f"{title} {body}") or kind == "operator_ask":
        body = "Aapke phone par jawab chahiye."
    return _mask(title, 80), _mask(body, 220)


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def board(tenant: str) -> dict[str, Any]:
    """Everything the screen shows, already safe to show."""
    name = _name(tenant)
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=CARD_HOURS)
    with session() as s:
        convs = s.scalars(select(Conversation.id).where(Conversation.tenant_id == tenant)
                          .order_by(Conversation.created_at.desc()).limit(5)).all()
        evs = s.scalars(select(Event).where(Event.conversation_id.in_(convs or ["-"]), Event.created_at >= since)
                        .order_by(Event.id.desc()).limit(600)).all() if convs else []
        rows = [(e.id, e.kind, dict(e.payload or {}), _aware(e.created_at)) for e in evs]
    steps: dict[str, dict] = {}
    cards: list[dict] = []
    said = ""
    seen_cards: set[str] = set()
    for eid, kind, p, at in rows:   # newest first
        if kind == "work":
            sid = str(p.get("id") or eid)
            if sid in steps:
                continue
            steps[sid] = {"label": _mask(p.get("label") or p.get("tool") or "Kaam", 90),
                          "scene": str(p.get("scene") or "work")[:16], "phase": str(p.get("phase") or "")[:10],
                          "at": at.isoformat(), "age": int((now - at).total_seconds())}
        elif kind == "message":
            if not said and p.get("role") == "assistant" and p.get("text"):
                said = _mask(p.get("text"), 220)
        else:
            shown = _card(kind, p, name)
            if not shown:
                continue
            inner = p.get("card") if isinstance(p.get("card"), dict) else {}
            cid = p.get("id") or inner.get("id")
            if cid:
                key = f"{kind}:{cid}"
                if key in seen_cards:
                    continue   # cards updated in place: show the newest state only
                seen_cards.add(key)
            if len(cards) < 8:
                cards.append({"kind": kind, "title": shown[0], "body": shown[1], "at": at.isoformat(),
                              "age": int((now - at).total_seconds())})
    ordered = sorted(steps.values(), key=lambda x: x["age"])
    now_steps = [x for x in ordered if x["phase"] in ("start", "waiting") and x["age"] <= ACTIVE_S][:4]
    done_steps = [x for x in ordered if x["phase"] in ("done", "error", "stopped")][:8]
    return {"name": name, "now": now_steps, "recent": done_steps, "cards": cards, "said": said,
            "today": _today(tenant), "call": _call(tenant), "at": now.isoformat()}


def _today(tenant: str) -> dict[str, Any]:
    try:
        from .agent.pakka import TaskRun
    except Exception:
        return {"done": 0, "total": 0, "tasks": []}
    start = datetime.now(timezone.utc) - timedelta(hours=18)
    with session() as s:
        runs = s.scalars(select(TaskRun).where(TaskRun.tenant_id == tenant, TaskRun.created_at >= start,
                                               TaskRun.outcome != "talk")
                         .order_by(TaskRun.created_at.desc()).limit(40)).all()
        tasks = [{"what": _mask(r.request, 90), "outcome": r.outcome} for r in runs]
    return {"done": sum(1 for t in tasks if t["outcome"] == "done"), "total": len(tasks), "tasks": tasks[:6]}


def _call(tenant: str) -> dict[str, Any] | None:
    try:
        from . import voice
        for c in list(voice.CALLS.values()):
            if getattr(c, "tenant", "") == tenant:
                return {"live": True}
    except Exception:
        pass
    return None


# ----------------------------------------------------------------------------- page
PAGE = """<!doctype html><html lang="hi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Hoola Screen</title><style>
:root{--bg:#0d1017;--card:#171c26;--line:#262d3a;--ink:#eef1f6;--mute:#93a0b4;--go:#2fbf71;--wait:#f2a33a;--bad:#e5534b;--acc:#ff8a3d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.4 system-ui,'Segoe UI',Roboto,'Noto Sans Devanagari',sans-serif}
header{display:flex;align-items:center;gap:14px;padding:18px 28px;border-bottom:1px solid var(--line)}
.dot{width:14px;height:14px;border-radius:50%;background:var(--go);box-shadow:0 0 0 0 rgba(47,191,113,.6);animation:p 2s infinite}
.dot.off{background:var(--mute);animation:none}@keyframes p{70%{box-shadow:0 0 0 12px rgba(47,191,113,0)}}
h1{font-size:28px;margin:0;font-weight:700}#clock{margin-left:auto;font-size:26px;font-variant-numeric:tabular-nums;color:var(--mute)}
#call{display:none;background:var(--go);color:#04210f;font-weight:700;border-radius:99px;padding:6px 14px}
main{display:grid;grid-template-columns:1.25fr 1fr;gap:20px;padding:20px 28px}
section{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;min-width:0}
h2{margin:0 0 12px;font-size:15px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
.step{display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line)}.step:last-child{border:0}
.big .step{font-size:24px}.ic{width:30px;text-align:center;flex:none}
.spin{width:22px;height:22px;border:3px solid var(--line);border-top-color:var(--acc);border-radius:50%;animation:s 1s linear infinite;display:inline-block}
@keyframes s{to{transform:rotate(360deg)}}.age{margin-left:auto;color:var(--mute);font-size:14px;white-space:nowrap}
.card{border-left:4px solid var(--wait);padding:10px 12px;margin:0 0 10px;background:#1d2330;border-radius:8px}
.card b{display:block;font-size:18px}.card span{color:var(--mute)}.empty{color:var(--mute);padding:8px 0}
#said{font-size:20px}.col{display:flex;flex-direction:column;gap:20px;min-width:0}
footer{padding:0 28px 18px;color:var(--mute);font-size:13px}.ok{color:var(--go)}.bad{color:var(--bad)}.w{color:var(--wait)}
@media(max-width:820px){main{grid-template-columns:1fr;padding:16px}header{padding:14px 16px}h1{font-size:22px}.big .step{font-size:19px}}
</style></head><body>
<header><span class="dot" id="dot"></span><h1 id="nm">Hoola</h1><span id="call">📞 Call chal rahi hai</span><span id="clock"></span></header>
<main><div class="col"><section class="big"><h2>Abhi kar raha hai</h2><div id="now"></div></section>
<section><h2>Abhi abhi hua</h2><div id="recent"></div></section></div>
<div class="col"><section><h2>Aapke phone par dekhiye</h2><div id="cards"></div></section>
<section><h2>Aaj ka kaam</h2><div id="today"></div></section><section><h2>Aakhri baat</h2><div id="said" class="empty">—</div></section></div></main>
<footer>Sirf dekhne ke liye. Haan, payment aur OTP sirf aapke phone par. <span id="st"></span></footer>
<script>
const FEED=location.pathname.replace(/^\\/screen\\//,'/api/screen/')+'/board';
const IC={email:'✉️',browser:'🌐',payment:'💳',bluetooth:'📶',network:'🔗',pc:'💻',work:'⚙️'};
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function ago(s){return s<60?'abhi':s<3600?Math.floor(s/60)+' min':Math.floor(s/3600)+' ghante'}
function mark(p){return p==='done'?'<span class="ok">✓</span>':p==='error'?'<span class="bad">✕</span>':p==='stopped'?'<span class="w">■</span>':p==='waiting'?'<span class="w">⏳</span>':'<span class="spin"></span>'}
function list(el,items,f,none){document.getElementById(el).innerHTML=items.length?items.map(f).join(''):'<div class="empty">'+none+'</div>'}
let fails=0;
async function tick(){try{const r=await fetch(FEED,{cache:'no-store'});const d=await r.json();
if(!r.ok){document.getElementById('st').textContent=d.detail||'Link band';document.getElementById('dot').className='dot off';return setTimeout(tick,30000)}
fails=0;document.getElementById('dot').className='dot';document.getElementById('nm').textContent=d.name;
document.getElementById('call').style.display=d.call?'inline-block':'none';
list('now',d.now,x=>'<div class="step"><span class="ic">'+mark(x.phase)+'</span>'+(IC[x.scene]||'⚙️')+' '+esc(x.label)+'</div>','Khaali hai. Kuch kehiye, kaam yahan dikhega.');
list('recent',d.recent,x=>'<div class="step"><span class="ic">'+mark(x.phase)+'</span>'+esc(x.label)+'<span class="age">'+ago(x.age)+'</span></div>','Abhi kuch nahi.');
list('cards',d.cards,x=>'<div class="card"><b>'+esc(x.title)+'</b><span>'+esc(x.body)+'</span><div class="age">'+ago(x.age)+'</div></div>','Koi naya card nahi.');
const t=d.today;document.getElementById('today').innerHTML='<div style="font-size:30px;font-weight:700">'+t.done+' / '+t.total+' <span style="font-size:16px;color:var(--mute)">kaam poore</span></div>'+t.tasks.map(x=>'<div class="step"><span class="ic">'+(x.outcome==='done'?'<span class="ok">✓</span>':'<span class="w">…</span>')+'</span>'+esc(x.what)+'</div>').join('');
const s=document.getElementById('said');s.textContent=d.said||'—';s.className=d.said?'':'empty';
document.getElementById('st').textContent='';}catch(e){fails++;document.getElementById('dot').className='dot off';document.getElementById('st').textContent='Internet ka intezaar...'}
setTimeout(tick,fails?5000:2500)}
function clock(){document.getElementById('clock').textContent=new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}
setInterval(clock,10000);clock();tick();
</script></body></html>"""


def page() -> str:
    return PAGE
