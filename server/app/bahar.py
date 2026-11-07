"""v0.616 BAHAR SE BAAT - talk to your own Hoola from WhatsApp, Telegram, Slack and Microsoft Teams
(owner: "More places to talk to Hoola" -> all four channels, "Only me").

Dots answers in Slack and Teams; Hoola now answers its OWNER wherever she already is. One core, four doors:

  whatsapp - her OWN WhatsApp Business number through Meta's official Cloud API (the number she already joined
             for the business inbox). A message from HER paired phone goes to Hoola; everyone else stays a
             customer on the business inbox, exactly as before. Never personal WhatsApp.
  telegram - her own bot (BotFather token, sealed); webhook with Telegram's secret-token header.
  slack    - her own Slack app (bot token + signing secret, sealed); Events API, signed requests only.
  teams    - her own Azure Bot (app id + password, sealed); Bot Framework JWT checked on every activity.

ONLY HER: a channel is useless until she PAIRS it - the app shows a 6-digit code (15 minutes, 5 tries) and she
sends that code from the app she wants to use. From then on only that one sender (her WhatsApp number / her
Telegram user / her Slack user / her Teams user) reaches Hoola; anyone else gets nothing from Hoola.

THE TURN: her message rides the SAME pipeline as the phone (convs.mark + bus.publish + turn_inbox.accept +
run_owned) into one chat per channel ("WhatsApp se baat"), so memory, tools and cards are the same Hoola. The
answer goes back on the channel; a job that finishes later is forwarded by the worker. Cards that need her tap
stay in the app (the reply says so) - a tap never travels over a chat app. OTP / PIN / card text is never sent
out on a channel.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, Conversation, Message, new_id, now, session

log = logging.getLogger("santosh.bahar")

CHANNELS = ("whatsapp", "telegram", "slack", "teams")
LABEL = {"whatsapp": "WhatsApp", "telegram": "Telegram", "slack": "Slack", "teams": "Microsoft Teams"}
CODE_TTL = timedelta(minutes=15)
CODE_TRIES = 5
WA_WINDOW = timedelta(hours=24)
MAX_OUT = {"whatsapp": 4000, "telegram": 4000, "slack": 3500, "teams": 4000}
CONTEXT = ("Yeh message maalkin ne {label} se bheja hai (bahar ka app). Jawab chhota aur saaf rakhiye - wahan "
           "lambi tables theek nahi dikhti. Jo card tap karna ho (bhejna, paisa, delete) woh Hoola app mein hi hoga; "
           "yeh bata dijiye.")


class BaharError(ValueError):
    pass


class BaharLink(Base):
    """One outside channel of one owner. `secret` is sealed JSON (bot tokens etc.); nothing in it is ever returned."""
    __tablename__ = "bahar_links"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bhr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    hook: Mapped[str] = mapped_column(String(48), index=True)          # the webhook path part (random)
    status: Mapped[str] = mapped_column(String(16), default="pairing")  # pairing | linked
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    code_tries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_sent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_TABLE_OK: set[int] = set()


def ensure_table() -> None:
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _TABLE_OK:
        return
    BaharLink.__table__.create(bind=eng, checkfirst=True)
    _TABLE_OK.add(id(eng))


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _h(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _seal(data: dict) -> str:
    from .bazar.security import vault
    return vault().seal(json.dumps(data))


def _open(sealed: str | None) -> dict:
    if not sealed:
        return {}
    from .bazar.security import vault
    try:
        return json.loads(vault().open(sealed))
    except Exception:
        return {}


# ---------------------------------------------------------------- outside HTTP (one door, swappable in tests)
_transport: Callable[..., Any] | None = None


def set_transport(fn: Callable[..., Any] | None) -> None:
    """Tests: fn(method, url, headers=..., json=..., data=...) -> (status, json)."""
    global _transport
    _transport = fn


async def _http(method: str, url: str, headers: dict | None = None, json_body: Any = None,
                data: dict | None = None) -> tuple[int, Any]:
    if _transport is not None:
        out = _transport(method, url, headers=headers or {}, json=json_body, data=data)
        if asyncio.iscoroutine(out):
            out = await out
        return out
    import httpx
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.request(method, url, headers=headers, json=json_body, data=data)
    try:
        body = r.json()
    except ValueError:
        body = {"text": r.text[:400]}
    return r.status_code, body


# ---------------------------------------------------------------- setup (owner, from the app)
def _view(l: BaharLink, base: str = "") -> dict[str, Any]:
    m = l.meta or {}
    out = {"channel": l.channel, "label": LABEL[l.channel], "status": l.status,
           "paired_with": _mask(l.external_id or ""), "conversation_id": l.conversation_id,
           "last_in_at": _utc(l.last_in_at).isoformat() if l.last_in_at else None}
    if l.channel in ("slack", "teams", "telegram"):
        out["webhook"] = f"{base}/webhooks/bahar/{l.channel}/{l.hook}"
    if m.get("bot_name"):
        out["bot_name"] = m["bot_name"]
    if m.get("number"):
        out["number"] = m["number"]
    return out


def _mask(v: str) -> str:
    v = str(v or "")
    if not v:
        return ""
    return ("•" * max(len(v) - 4, 0) + v[-4:]) if len(v) > 4 else "••" + v[-2:]


def links(tenant: str, base: str = "") -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(BaharLink).where(BaharLink.tenant_id == tenant)).all()
        have = {r.channel: _view(r, base) for r in rows}
    return [have.get(c) or {"channel": c, "label": LABEL[c], "status": "off"} for c in CHANNELS]


def _wa_number(tenant: str) -> tuple[str, str]:
    """Her joined business number (phone_number_id, display) - the same one the business inbox uses."""
    from .config import get_settings
    from .employee import inbox
    ch = inbox.channels(tenant)
    if ch:
        return ch[0]["phone_number_id"], ch[0].get("display_number") or ""
    st = get_settings()
    if st.wa_inbox_tenant == tenant and st.wa_phone_number_id:
        return st.wa_phone_number_id, ""
    return "", ""


async def setup(tenant: str, channel: str, creds: dict[str, str] | None = None, base: str = "") -> dict[str, Any]:
    """Create / refresh a channel and hand out a fresh pairing code. Credentials are sealed on arrival."""
    if channel not in CHANNELS:
        raise BaharError("Yeh channel nahi hai (whatsapp / telegram / slack / teams).")
    ensure_table()
    creds = {k: str(v).strip() for k, v in (creds or {}).items() if v and str(v).strip()}
    with session() as s:
        l = s.scalars(select(BaharLink).where(BaharLink.tenant_id == tenant, BaharLink.channel == channel)).first()
        old = _open(l.secret) if l else {}
        meta = dict(l.meta or {}) if l else {}
    sec = {**old, **creds}
    if channel == "whatsapp":
        pnid, disp = _wa_number(tenant)
        if not pnid:
            raise BaharError("Pehle apna WhatsApp Business number jodiye (Profile > WhatsApp Business). Hoola usi "
                             "number se aapse baat karega - personal WhatsApp kabhi nahi.")
        meta.update(pnid=pnid, number=disp)
    elif channel == "telegram":
        if not sec.get("token"):
            raise BaharError("Telegram mein @BotFather se naya bot banaiye aur uska token yahan daaliye.")
        from .samudaay.adapters import AdapterError, tg_call
        sec.setdefault("header", secrets.token_urlsafe(24))
        try:
            me = await asyncio.to_thread(tg_call, sec["token"], "getMe", {})
        except AdapterError as e:
            raise BaharError(f"Bot token kaam nahi kar raha: {e}") from None
        meta.update(bot_name="@" + str((me or {}).get("username") or ""))
    elif channel == "slack":
        if not sec.get("bot_token", "").startswith("xoxb-") or not sec.get("signing_secret"):
            raise BaharError("Slack app ka Bot token (xoxb-...) aur Signing secret dono chahiye.")
        st, body = await _http("POST", "https://slack.com/api/auth.test",
                               headers={"Authorization": f"Bearer {sec['bot_token']}"})
        if st >= 400 or not (body or {}).get("ok"):
            raise BaharError(f"Slack ne token nahi maana: {(body or {}).get('error') or st}")
        meta.update(bot_name=str(body.get("user") or "Hoola"), team=str(body.get("team") or ""),
                    bot_user=str(body.get("user_id") or ""))
    elif channel == "teams":
        if not sec.get("app_id") or not sec.get("app_password"):
            raise BaharError("Azure Bot ka Microsoft App ID aur client secret (password) dono chahiye.")
        await _teams_token(sec, fresh=True)          # proves the pair works before she pairs
    code = f"{secrets.randbelow(10 ** 6):06d}"
    with session() as s:
        l = s.scalars(select(BaharLink).where(BaharLink.tenant_id == tenant, BaharLink.channel == channel)).first()
        if l is None:
            l = BaharLink(tenant_id=tenant, channel=channel, hook=secrets.token_urlsafe(18))
            s.add(l)
        l.secret = _seal(sec) if sec else None
        l.meta = meta
        l.code_hash, l.code_until, l.code_tries = _h(code), now() + CODE_TTL, 0
        if l.status != "linked":
            l.status = "pairing"
        s.flush()
        view, hook = _view(l, base), l.hook
    if channel == "telegram" and base:
        from .samudaay.adapters import AdapterError, tg_call
        try:
            await asyncio.to_thread(tg_call, sec["token"], "setWebhook",
                                    {"url": f"{base}/webhooks/bahar/telegram/{hook}", "secret_token": sec["header"],
                                     "allowed_updates": ["message"]})
        except AdapterError as e:
            raise BaharError(f"Telegram webhook nahi laga: {e}") from None
    return {**view, "code": code, "code_minutes": int(CODE_TTL.total_seconds() // 60), "how": how(channel, view)}


def how(channel: str, view: dict) -> str:
    code_line = "Ab {where} se sirf yeh code bhejiye: HOOLA <code>. Uske baad sirf aap hi Hoola se baat kar sakengi."
    if channel == "whatsapp":
        return code_line.format(where=f"apne phone ke WhatsApp se apne business number {view.get('number') or ''}".strip())
    if channel == "telegram":
        return code_line.format(where=f"Telegram mein apne bot {view.get('bot_name') or ''} ko".strip())
    if channel == "slack":
        return ("Slack app settings > Event Subscriptions > Request URL mein yeh daaliye: " + view.get("webhook", "")
                + " ; 'message.im' event jodiye, phir App Home > Messages tab on kijiye. " + code_line.format(where="bot ko DM mein"))
    return ("Azure Bot > Configuration > Messaging endpoint mein yeh daaliye: " + view.get("webhook", "")
            + " ; Channels mein Microsoft Teams on kijiye. " + code_line.format(where="Teams mein bot ko"))


def remove(tenant: str, channel: str) -> bool:
    ensure_table()
    with session() as s:
        l = s.scalars(select(BaharLink).where(BaharLink.tenant_id == tenant, BaharLink.channel == channel)).first()
        if l is None:
            return False
        sec, ch = _open(l.secret), l.channel
        s.delete(l)
    if ch == "telegram" and sec.get("token"):
        try:
            from .samudaay.adapters import tg_call
            tg_call(sec["token"], "deleteWebhook", {})
        except Exception:
            pass
    return True


def _link_by_hook(channel: str, hook: str) -> BaharLink | None:
    ensure_table()
    with session() as s:
        l = s.scalars(select(BaharLink).where(BaharLink.channel == channel, BaharLink.hook == hook)).first()
        if l is not None:
            s.expunge(l)
        return l


# ---------------------------------------------------------------- incoming (one core)
_SEEN: "OrderedDict[str, float]" = OrderedDict()
_TASKS: set[asyncio.Task] = set()
_LOCKS: dict[str, asyncio.Lock] = {}
_CODE_RE = re.compile(r"^\s*(?:hoola\s*[:\-]?\s*)?(\d{6})\s*$", re.I)


def _seen(key: str) -> bool:
    if not key:
        return False
    nowm = time.monotonic()
    while _SEEN and (len(_SEEN) > 5000 or nowm - next(iter(_SEEN.values())) > 3600):
        _SEEN.popitem(last=False)
    if key in _SEEN:
        return True
    _SEEN[key] = nowm
    return False


def spawn(coro) -> None:
    """Run in the background with a strong reference (a webhook must answer fast; Meta / Slack retry slow ones)."""
    t = asyncio.get_running_loop().create_task(coro)
    _TASKS.add(t)
    t.add_done_callback(_TASKS.discard)


async def incoming(link_id: str, sender: str, text: str, msg_id: str = "", meta: dict | None = None) -> str:
    """One message from outside. Returns what happened: paired | wrong_code | turn | ignored | duplicate."""
    if _seen(f"{link_id}:{msg_id}"):
        return "duplicate"
    sender, text = str(sender or ""), str(text or "").strip()[:8000]
    with session() as s:
        l = s.get(BaharLink, link_id)
        if l is None:
            return "ignored"
        linked_to = l.external_id if l.status == "linked" else ""
        if linked_to and linked_to == sender:
            l.last_in_at = now()
            if meta:
                l.meta = {**(l.meta or {}), **meta}
            tenant, channel = l.tenant_id, l.channel
        elif not linked_to:
            m = _CODE_RE.match(text)
            until = _utc(l.code_until)
            if not m or not l.code_hash or until is None or until < now() or (l.code_tries or 0) >= CODE_TRIES:
                return "ignored"
            if not hmac.compare_digest(_h(m.group(1)), l.code_hash):
                l.code_tries = (l.code_tries or 0) + 1
                return "wrong_code"
            l.status, l.external_id, l.code_hash, l.code_until = "linked", sender, None, None
            l.last_in_at = now()
            l.meta = {**(l.meta or {}), **(meta or {})}
            if not l.conversation_id:
                c = Conversation(tenant_id=l.tenant_id, title=f"{LABEL[l.channel]} se baat")
                s.add(c)
                s.flush()
                l.conversation_id = c.id
            top = s.scalars(select(Message.id).where(Message.conversation_id == l.conversation_id)
                            .order_by(Message.id.desc()).limit(1)).first()
            l.last_sent_id = int(top or 0)
            tenant, channel, lid = l.tenant_id, l.channel, l.id
        else:
            return "ignored"                                  # not her: Hoola talks only to its owner
    if not linked_to:
        await _send(lid, f"Jud gaya ✓ Ab {LABEL[channel]} se aap seedhe Hoola se baat kar sakti hain. "
                         "Paisa / bhejna / delete jaise card Hoola app mein hi tap honge.")
        return "paired"
    if not text:
        await _send(link_id, "Abhi main yahan sirf likha hua message samajhta hoon. Photo / voice ke liye Hoola app kholiye.")
        return "turn"
    await _turn(link_id, tenant, channel, text, msg_id)
    return "turn"


async def _turn(link_id: str, tenant: str, channel: str, text: str, msg_id: str) -> None:
    from . import convs, turn_inbox
    from .events import bus
    with session() as s:
        l = s.get(BaharLink, link_id)
        conv = l.conversation_id if l else None
        if conv:
            c = s.get(Conversation, conv)
            if c is None or c.deleted:
                conv = None
        if not conv:
            c = Conversation(tenant_id=tenant, title=f"{LABEL[channel]} se baat")
            s.add(c)
            s.flush()
            conv = c.id
            l.conversation_id = conv
    cid = f"{channel}:{msg_id}"[:64] if msg_id else ""
    # v0.666 a channel chat is NEVER "the chat she is in": marking it sent every mail alert, calendar nudge and browser
    # answer out on Telegram / WhatsApp (forward_all forwards every new reply of this chat) and opened her app on it
    bus.publish(conv, "message", {"role": "user", "text": text, "source": channel, **({"client_id": cid} if cid else {})})
    ti = turn_inbox.accept(tenant, conv, text, False, CONTEXT.format(label=LABEL[channel]), cid)
    await _typing(link_id)
    try:
        await turn_inbox.run_owned(ti, conv, text, tenant, False, context=CONTEXT.format(label=LABEL[channel]),
                                   client_id=cid)
    except Exception:
        log.exception("bahar turn failed (%s)", channel)
        await _send(link_id, "Maaf kijiye, abhi jawab nahi ban paaya. Hoola app mein dekhiye ya thodi der baad likhiye.")
    await forward(link_id)


# ---------------------------------------------------------------- outgoing
def _clean(text: str, channel: str) -> str:
    t = str(text or "").strip()
    if channel in ("whatsapp", "slack"):
        t = re.sub(r"\*\*(.+?)\*\*", r"*\1*", t)               # markdown bold -> their bold
        t = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", t, flags=re.M)
    elif channel == "telegram":
        t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
        t = re.sub(r"^#{1,6}\s*", "", t, flags=re.M)
    return t


def _chunks(text: str, size: int) -> list[str]:
    out, buf = [], ""
    for para in text.split("\n\n"):
        while len(para) > size:
            out.append(para[:size])
            para = para[size:]
        if len(buf) + len(para) + 2 > size and buf:
            out.append(buf)
            buf = ""
        buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        out.append(buf)
    return out[:6]


SEND_TRIES = 3
_FAILS: dict = {}


def _advance(link_id: str, mid: int) -> None:
    with session() as s:
        l = s.get(BaharLink, link_id)
        if l is not None and int(mid) > int(l.last_sent_id or 0):
            l.last_sent_id = int(mid)


async def forward(link_id: str) -> int:
    """Send her new Hoola replies (this turn's, or a job that finished later) back on the channel, once each."""
    lock = _LOCKS.setdefault(link_id, asyncio.Lock())
    async with lock:
        with session() as s:
            l = s.get(BaharLink, link_id)
            if l is None or l.status != "linked" or not l.conversation_id:
                return 0
            rows = s.scalars(select(Message).where(Message.conversation_id == l.conversation_id,
                                                   Message.role == "assistant", Message.display.is_not(None),
                                                   Message.branch.is_(None), Message.id > int(l.last_sent_id or 0))
                             .order_by(Message.id).limit(10)).all()
            todo = [(m.id, m.display) for m in rows if (m.display or "").strip()]
            channel, last_in = l.channel, _utc(l.last_in_at)
        if not todo:
            return 0
        if channel == "whatsapp" and (last_in is None or now() - last_in > WA_WINDOW):
            _advance(link_id, todo[-1][0])
            return 0                                       # Meta's 24 h window: the reply stays in the app
        # v0.665 a reply is marked sent only AFTER it really went (a Telegram 5xx / a WhatsApp token blip used to lose
        # it for good: last_sent_id moved before the send). A failing one is tried again on the next forward, at most
        # SEND_TRIES times, then skipped so one bad message never blocks the rest.
        sent = 0
        for mid, text in todo:
            if await _send(link_id, text):
                sent += 1
                _FAILS.pop((link_id, mid), None)
            else:
                k = (link_id, mid)
                _FAILS[k] = _FAILS.get(k, 0) + 1
                if _FAILS[k] < SEND_TRIES:
                    break                                  # keep this one (and the ones after it) for the next try
                _FAILS.pop(k, None)
                log.warning("bahar: reply %s on %s skipped after %s failed sends", mid, link_id, SEND_TRIES)
            _advance(link_id, mid)
        return sent


async def _send(link_id: str, text: str) -> bool:
    from .net import policy
    with session() as s:
        l = s.get(BaharLink, link_id)
        if l is None or not l.external_id:
            return False
        channel, to, meta, sec, tenant = l.channel, l.external_id, dict(l.meta or {}), _open(l.secret), l.tenant_id
    text = _clean(text, channel)
    if policy.secret_found(text):
        text = "Is jawab mein OTP / PIN / card jaisi jaankari hai - woh bahar ke app par nahi bhejta. Hoola app mein dekhiye."
    ok = True
    for part in _chunks(text, MAX_OUT[channel]):
        try:
            if channel == "whatsapp":
                from .employee import inbox
                from .whatsapp import get_whatsapp
                pnid, token = inbox._channel_auth(tenant, meta.get("pnid", ""))
                await get_whatsapp().send_text(to, part, pnid, token)
            elif channel == "telegram":
                from .samudaay.adapters import tg_call
                await asyncio.to_thread(tg_call, sec.get("token", ""), "sendMessage",
                                        {"chat_id": meta.get("chat_id") or to, "text": part,
                                         "disable_web_page_preview": True})
            elif channel == "slack":
                st, body = await _http("POST", "https://slack.com/api/chat.postMessage",
                                       headers={"Authorization": f"Bearer {sec.get('bot_token', '')}"},
                                       json_body={"channel": meta.get("dm") or to, "text": part})
                if st >= 400 or not (body or {}).get("ok"):
                    raise BaharError(str((body or {}).get("error") or st))
            elif channel == "teams":
                tok = await _teams_token(sec)
                url = str(meta.get("service_url") or "").rstrip("/")
                if not url.startswith("https://") or not meta.get("conv"):
                    raise BaharError("Teams conversation pata nahi")
                st, body = await _http("POST", f"{url}/v3/conversations/{meta['conv']}/activities",
                                       headers={"Authorization": f"Bearer {tok}"},
                                       json_body={"type": "message", "text": part, "textFormat": "markdown"})
                if st >= 400:
                    raise BaharError(f"Teams {st}")
        except Exception as e:
            ok = False
            log.warning("bahar send failed (%s): %s", channel, str(e)[:200])
            break
    return ok


async def _typing(link_id: str) -> None:
    with session() as s:
        l = s.get(BaharLink, link_id)
        if l is None or l.channel != "telegram":
            return
        chat, sec = (l.meta or {}).get("chat_id") or l.external_id, _open(l.secret)
    try:
        from .samudaay.adapters import tg_call
        await asyncio.to_thread(tg_call, sec.get("token", ""), "sendChatAction", {"chat_id": chat, "action": "typing"})
    except Exception:
        pass


async def forward_all() -> int:
    """Worker: a long job that finished after the turn still reaches her on the channel."""
    ensure_table()
    with session() as s:
        ids = list(s.scalars(select(BaharLink.id).where(BaharLink.status == "linked")).all())
    n = 0
    for i in ids:
        try:
            n += await forward(i)
        except Exception:
            log.exception("bahar forward")
    return n


# ---------------------------------------------------------------- per-channel webhook readers
def whatsapp_take(value: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    """From one Meta `messages` change, take out the messages that are HER talking to Hoola (paired number,
    or a pairing code). Returns [(link_id, sender, text, wamid)] and REMOVES them from `value`, so the business
    inbox never sees them. Everyone else is left in place for the customer inbox."""
    ensure_table()
    pnid = str((value.get("metadata") or {}).get("phone_number_id") or "")
    if not pnid or not value.get("messages"):
        return []
    with session() as s:
        rows = s.scalars(select(BaharLink).where(BaharLink.channel == "whatsapp")).all()
        mine = [(r.id, r.status, r.external_id or "", r.code_hash, _utc(r.code_until), r.code_tries or 0)
                for r in rows if (r.meta or {}).get("pnid") == pnid]
    if not mine:
        return []
    from .employee.inbox import _text_of
    lid, status, ext, code_hash, until, tries = mine[0]
    took, keep = [], []
    for m in value.get("messages") or []:
        wa = re.sub(r"\D", "", str(m.get("from") or ""))
        _kind, text = _text_of(m)
        cm = _CODE_RE.match(text or "")
        ours = (status == "linked" and wa and wa == ext) or (
            status != "linked" and cm and code_hash and until and until > now() and tries < CODE_TRIES)
        if ours:
            took.append((lid, wa, text if _kind == "text" else "", str(m.get("id") or "")))
        else:
            keep.append(m)
    value["messages"] = keep
    return took


def telegram_read(update: dict[str, Any]) -> tuple[str, str, str, dict] | None:
    m = update.get("message") or {}
    chat, frm = m.get("chat") or {}, m.get("from") or {}
    if chat.get("type") != "private" or frm.get("is_bot"):
        return None                                      # only her own 1:1 chat with her bot
    return (str(frm.get("id") or ""), str(m.get("text") or m.get("caption") or ""),
            str(update.get("update_id") or m.get("message_id") or ""), {"chat_id": chat.get("id")})


def slack_sig_ok(signing_secret: str, ts: str, raw: bytes, sig: str) -> bool:
    try:
        if abs(time.time() - int(ts)) > 300:
            return False
    except (TypeError, ValueError):
        return False
    base = b"v0:" + str(ts).encode() + b":" + raw
    want = "v0=" + hmac.new(signing_secret.encode(), base, hashlib.sha256).hexdigest()
    return bool(sig) and hmac.compare_digest(want, sig)


def slack_read(body: dict[str, Any], bot_user: str = "") -> tuple[str, str, str, dict] | None:
    ev = body.get("event") or {}
    if body.get("type") != "event_callback" or ev.get("type") != "message" or ev.get("channel_type") != "im":
        return None
    if ev.get("bot_id") or ev.get("subtype") or (bot_user and ev.get("user") == bot_user):
        return None                                      # our own replies and edits never become turns
    return (str(ev.get("user") or ""), str(ev.get("text") or ""), str(body.get("event_id") or ev.get("ts") or ""),
            {"dm": ev.get("channel")})


def teams_read(act: dict[str, Any]) -> tuple[str, str, str, dict] | None:
    if act.get("type") != "message":
        return None
    conv = act.get("conversation") or {}
    if conv.get("conversationType") not in (None, "personal"):
        return None                                      # 1:1 chat with the bot only, never a team channel
    frm = act.get("from") or {}
    text = re.sub(r"<at>.*?</at>", "", str(act.get("text") or "")).strip()
    return (str(frm.get("aadObjectId") or frm.get("id") or ""), text, str(act.get("id") or ""),
            {"service_url": act.get("serviceUrl"), "conv": conv.get("id")})


# ---------------------------------------------------------------- Teams auth (Bot Framework)
_TEAMS_TOK: dict[str, tuple[str, float]] = {}
_JWKS: dict[str, Any] = {}
BF_OPENID = "https://login.botframework.com/v1/.well-known/openidconfiguration"
BF_ISSUER = "https://api.botframework.com"


async def _teams_token(sec: dict, fresh: bool = False) -> str:
    app_id = sec.get("app_id", "")
    hit = _TEAMS_TOK.get(app_id)
    if hit and not fresh and hit[1] > time.time() + 60:
        return hit[0]
    tenant = sec.get("app_tenant") or "botframework.com"     # single-tenant bots name their own directory
    st, body = await _http("POST", f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                           data={"grant_type": "client_credentials", "client_id": app_id,
                                 "client_secret": sec.get("app_password", ""),
                                 "scope": "https://api.botframework.com/.default"})
    tok = (body or {}).get("access_token")
    if st >= 400 or not tok:
        raise BaharError(f"Microsoft ne bot ka login nahi maana: {(body or {}).get('error_description') or (body or {}).get('error') or st}"[:240])
    _TEAMS_TOK[app_id] = (tok, time.time() + int((body or {}).get("expires_in") or 3000))
    return tok


def teams_verify(auth_header: str, app_id: str, service_url: str) -> bool:
    """Bot Framework's channel token: RS256 by its published keys, issuer api.botframework.com, audience = her
    app id, and the serviceurl claim matching the activity. Anything else is refused."""
    tok = (auth_header or "").removeprefix("Bearer ").strip()
    if not tok or not app_id:
        return False
    try:
        import httpx
        import jwt
        if "client" not in _JWKS or _JWKS.get("at", 0) < time.time() - 86400:
            cfg = httpx.get(BF_OPENID, timeout=10).json()
            _JWKS["client"], _JWKS["at"] = jwt.PyJWKClient(cfg["jwks_uri"]), time.time()
        key = _JWKS["client"].get_signing_key_from_jwt(tok)
        claims = jwt.decode(tok, key.key, algorithms=["RS256"], audience=app_id, issuer=BF_ISSUER, leeway=300)
    except Exception as e:
        log.warning("teams token refused: %s", type(e).__name__)
        return False
    su = str(claims.get("serviceurl") or claims.get("serviceUrl") or "")
    return not su or su.rstrip("/") == str(service_url or "").rstrip("/")


def chat_ids(tenant: str) -> set:
    """v0.666 the conversations that belong to her outside channels (never her 'current' chat)."""
    try:
        ensure_table()
        with session() as s:
            return {c for c in s.scalars(select(BaharLink.conversation_id).where(BaharLink.tenant_id == tenant)).all() if c}
    except Exception:   # noqa: BLE001
        log.debug("bahar chat ids failed", exc_info=True)
        return set()
