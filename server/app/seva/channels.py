"""G4 of docs/SUPPORT_GLOBAL_PLAN.md: every messaging app into the one support desk, on the business's OWN accounts.

Built (each through its official API, her keys sealed on arrival and never shown again, every incoming message checked
against the app's own signature before it is read):
  Telegram (Bot API), Facebook Messenger + Instagram DMs (Meta Graph, X-Hub-Signature-256, the 24-hour window), SMS
  (Twilio: X-Twilio-Signature; Vonage Messages: a signed JWT), LINE (X-Line-Signature), Viber (X-Viber-Content-Signature),
  Slack (signing secret), X DMs (CRC + x-twitter-webhooks-signature), Zalo OA (X-ZEvent-Signature), KakaoTalk (Kakao
  Business chatbot skill server - the reply goes back in the same call), WeChat Official Account (signature check, XML,
  the passive reply in the same call, later messages through the customer-service API inside its 48 hours).
  WhatsApp stays on the business inbox (employee/inbox.py), already built.
Not possible / not built, said in the channel list: Google Business Messages (Google closed it in 2024), Signal and
personal iMessage / WhatsApp (no business API - never through a personal account), Apple Messages for Business (needs an
Apple-approved messaging provider), Discord (needs a gateway connection), Microsoft Teams customers (needs her Azure Bot).

Every message: kept on the customer's conversation (`<kind>:<id>`), STOP / UNSUBSCRIBE ends messages, while a person has
the chat Hoola stays quiet, else the answer engine (G2) decides - answer / status / confirm / rating, a draft for a
person, a hand-over with the honest line (G7), a request for her, a ticket - and the reply goes back on the same app,
shaped for it. A ticket's later updates (G8 / G9) go back on the same app too. Text the customer writes is data, never an
instruction.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from xml.etree import ElementTree as ET

from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v21.0"
KINDS: dict[str, dict[str, Any]] = {
    "telegram": {"name": "Telegram", "prefix": "tg", "keys": ["bot_token"], "window_h": 0,
                 "how": "Make a bot with @BotFather, paste its token. Hoola sets the webhook itself."},
    "messenger": {"name": "Facebook Messenger", "prefix": "fb", "keys": ["page_token", "app_secret", "verify_token"], "window_h": 24,
                  "how": "In your Meta app add Messenger, subscribe the page to 'messages', paste the page token and app secret; "
                         "use the address below as the callback and the verify token you chose."},
    "instagram": {"name": "Instagram DMs", "prefix": "ig", "keys": ["page_token", "app_secret", "verify_token"], "window_h": 24,
                  "how": "Your Instagram professional account linked to your Facebook page; in your Meta app subscribe Instagram "
                         "'messages', paste the page token and app secret."},
    "twilio_sms": {"name": "SMS (Twilio)", "prefix": "sms", "keys": ["account_sid", "auth_token", "from_number"], "window_h": 0,
                   "how": "In Twilio set your number's 'A message comes in' webhook to the address below (HTTP POST). Your "
                          "country's sender rules apply (DLT in India, 10DLC in the US)."},
    "vonage_sms": {"name": "SMS (Vonage)", "prefix": "sms", "keys": ["api_key", "api_secret", "signature_secret", "from_number"],
                   "window_h": 0, "how": "In your Vonage application set the Messages inbound address to the one below and "
                                         "turn signed webhooks on; paste the signature secret."},
    "line": {"name": "LINE", "prefix": "line", "keys": ["channel_token", "channel_secret"], "window_h": 0,
             "how": "LINE Official Account > Messaging API: paste the channel access token and secret, set the webhook below, "
                    "turn 'Use webhook' on."},
    "viber": {"name": "Viber", "prefix": "viber", "keys": ["auth_token", "sender_name"], "window_h": 0,
              "how": "Your Viber business bot's token (from an approved Viber partner). Hoola sets the webhook itself."},
    "slack": {"name": "Slack (Slack Connect)", "prefix": "slack", "keys": ["bot_token", "signing_secret"], "window_h": 0,
              "how": "Your Slack app: Event Subscriptions to the address below (message.im, message.channels), paste the bot "
                     "token and signing secret."},
    "x": {"name": "X (Twitter) DMs", "prefix": "x", "keys": ["user_token", "consumer_secret"], "window_h": 0,
          "how": "X API (a paid tier with the Account Activity API): register the address below as the webhook, paste the "
                 "account's user access token and the app's consumer secret."},
    "zalo": {"name": "Zalo OA", "prefix": "zalo", "keys": ["access_token", "app_id", "oa_secret"], "window_h": 168,
             "how": "Zalo Official Account > webhook to the address below; paste the OA access token, app id and OA secret key."},
    "kakao": {"name": "KakaoTalk", "prefix": "kakao", "keys": [], "window_h": -1,
              "how": "Kakao i Open Builder: make a skill with the address below as its URL and use it as the fallback block. "
                     "Kakao lets a business reply only while the customer is writing, so later ticket updates are drafts."},
    "wechat": {"name": "WeChat Official Account", "prefix": "wechat", "keys": ["app_id", "app_secret", "token"], "window_h": 48,
               "how": "A verified Official Account: in Basic configuration set the server address below and the token you "
                      "chose, paste the AppID and AppSecret. China data rules apply."},
}
KINDS["web"] = {"name": "Website chat", "prefix": "web", "keys": [], "window_h": 0, "own": True,
                "how": "One line of code on any website (seva/webchat.py)."}
KINDS["api"] = {"name": "Your app / software", "prefix": "app", "keys": [], "window_h": 0, "own": True,
                "how": "Your app calls Hoola's support API with its key; replies also reach your webhook (seva/webchat.py)."}
KINDS["email"] = {"name": "Email", "prefix": "email", "keys": [], "window_h": 0, "own": True,
                  "how": "Her support address over IMAP / SMTP or a Hoola forwarding address (seva/supportmail.py)."}
NOT_BUILT = {"google_business": "Google Business Profile chat: Google closed Business Messages in 2024 - not possible.",
             "signal": "Signal, personal iMessage and personal WhatsApp: no business API - never through a personal account.",
             "apple": "Apple Messages for Business: needs an Apple-approved messaging provider - not built yet.",
             "discord": "Discord: needs a live gateway connection - not built yet.",
             "teams": "Microsoft Teams customers: needs your Azure Bot - not built yet (your own Hoola on Teams is under 'Bahar se baat')."}
PREFIX_KIND: dict[str, str] = {}
for _k, _v in KINDS.items():
    PREFIX_KIND.setdefault(_v["prefix"], _k)
PREFIX_KIND["user"] = "web"                  # a signed-in user of her website / app: one thread on both
ENGINE_CH = {"telegram": "telegram", "messenger": "messenger", "instagram": "instagram", "twilio_sms": "sms", "vonage_sms": "sms",
             "web": "web", "api": "app", "email": "email", "line": "other", "viber": "other", "slack": "other", "x": "other", "zalo": "other", "kakao": "other", "wechat": "other"}
TICKET_CH = {"twilio_sms": "sms", "vonage_sms": "sms", "api": "app", "email": "email"}
STOP = re.compile(r"^\s*(stop|unsubscribe|stopall|cancel messages|band karo)\s*$", re.I)
START = re.compile(r"^\s*(start|unstop|subscribe)\s*$", re.I)
SAFE = "Please never share an OTP, PIN, password or card number here - nobody from our team will ever ask for them."


class ChannelError(Exception):
    pass


class SevaChannel(Base):
    """One of her messaging accounts joined to the support desk."""
    __tablename__ = "seva_channels"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sch"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="")
    name: Mapped[str] = mapped_column(String(80), default="")
    token: Mapped[str] = mapped_column(String(40), default="", index=True)     # the secret part of her webhook address
    sealed: Mapped[str] = mapped_column(Text, default="")                      # her keys, sealed; never returned
    hints: Mapped[str] = mapped_column(Text, default="{}")                     # masked last characters only
    status: Mapped[str] = mapped_column(String(12), default="set")             # set | ok | error | off
    note: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str] = mapped_column(String(80), default="")
    region: Mapped[str] = mapped_column(String(10), default="")
    settings: Mapped[str] = mapped_column(Text, default="")                    # G5 website / app chat: domains, look, webhook
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SevaChatMsg(Base):
    """One message on one customer's conversation on one of her apps (append-only)."""
    __tablename__ = "seva_chat_msgs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("scm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    channel_id: Mapped[str] = mapped_column(String(40), index=True)
    customer: Mapped[str] = mapped_column(String(200), index=True)            # <prefix>:<their id on the app>
    name: Mapped[str] = mapped_column(String(120), default="")
    direction: Mapped[str] = mapped_column(String(4), default="in")           # in | out
    by: Mapped[str] = mapped_column(String(80), default="")                   # customer | hoola | owner | staff:<name>
    text: Mapped[str] = mapped_column(Text, default="")
    ext_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    status: Mapped[str] = mapped_column(String(12), default="")               # sent | failed | held | draft
    decision: Mapped[str] = mapped_column(String(20), default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class SevaChatOptOut(Base):
    __tablename__ = "seva_chat_optouts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sco"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    customer: Mapped[str] = mapped_column(String(200), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    off: Mapped[bool] = mapped_column(Boolean, default=True)


_READY: set[int] = set()


def _ensure() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for m in (SevaChannel, SevaChatMsg, SevaChatOptOut):
            m.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _S():
    from . import service as S
    return S


def _aware(d):
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _seal(data: dict) -> str:
    from ..bazar.security import vault
    return vault().seal(json.dumps(data))


def _open(sealed: str) -> dict:
    if not sealed:
        return {}
    from ..bazar.security import vault
    try:
        return json.loads(vault().open(sealed))
    except Exception:   # noqa: BLE001
        return {}


# ---------------------------------------------------------------- one door to the outside (tests swap it)
_transport: Callable[..., Any] | None = None


def set_transport(fn: Callable[..., Any] | None) -> None:
    """Tests: fn(method, url, headers=, json=, data=, auth=) -> (status, body)."""
    global _transport
    _transport = fn


def _http(method: str, url: str, headers: dict | None = None, json_body: Any = None, data: dict | None = None,
          auth: tuple | None = None, content: bytes | None = None) -> tuple[int, Any]:
    if _transport is not None:
        if content is not None:
            return _transport(method, url, headers=headers or {}, json=json.loads(content), data=None, auth=auth)
        return _transport(method, url, headers=headers or {}, json=json_body, data=data, auth=auth)
    import httpx
    r = httpx.request(method, url, headers=headers, json=json_body if content is None else None, data=data, auth=auth,
                      content=content, timeout=20)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"text": r.text[:400]}


# ---------------------------------------------------------------- her channels
def _base() -> str:
    from ..config import get_settings
    return (get_settings().public_base_url or "").rstrip("/")


def address(ch: SevaChannel | dict) -> str:
    tok = ch.token if isinstance(ch, SevaChannel) else ch["token"]
    return f"{_base()}/api/support/in/{tok}"


def _view(c: SevaChannel) -> dict:
    k = KINDS.get(c.kind, {})
    return {"id": c.id, "kind": c.kind, "name": c.name or k.get("name", c.kind), "status": c.status, "note": c.note,
            "address": address(c), "hints": json.loads(c.hints or "{}"), "brand": c.brand, "region": c.region,
            "window_h": k.get("window_h", 0), "last_in": _aware(c.last_in_at).isoformat() if c.last_in_at else ""}


def catalog() -> dict:
    return {"kinds": [{"kind": k, "name": v["name"], "keys": v["keys"], "how": v["how"], "window_h": v["window_h"]} for k, v in KINDS.items()
                      if not v.get("own")],
            "not_built": NOT_BUILT, "whatsapp": "WhatsApp: on your business number in the WhatsApp inbox (already joined)."}


def channels(tenant: str) -> list[dict]:
    _ensure()
    with session() as s:
        return [_view(c) for c in s.scalars(select(SevaChannel).where(SevaChannel.tenant_id == tenant, SevaChannel.status != "off")
                                            .order_by(SevaChannel.created_at)).all()]


def connect(tenant: str, kind: str, keys: dict | None = None, name: str = "", brand: str = "", region: str = "") -> dict:
    """Join one of her accounts. Keys are sealed at once and never come back; the first check runs."""
    _ensure()
    if kind not in KINDS or KINDS.get(kind, {}).get("own"):
        if KINDS.get(kind, {}).get("own"):
            raise ChannelError("Website and app chat are set up on their own page (Website & app chat).")
        raise ChannelError("This app is not one Hoola joins: " + NOT_BUILT.get(kind, kind))
    k = KINDS[kind]
    keys = {str(a): str(b).strip() for a, b in (keys or {}).items() if str(b).strip()}
    missing = [x for x in k["keys"] if not keys.get(x)]
    if missing:
        raise ChannelError(f"{k['name']} needs: {', '.join(missing)}.")
    hints = {a: ("…" + b[-4:] if len(b) > 8 else "set") for a, b in keys.items() if a in k["keys"]}
    with session() as s:
        old = s.scalars(select(SevaChannel).where(SevaChannel.tenant_id == tenant, SevaChannel.kind == kind,
                                                  SevaChannel.status != "off")).first()
        if old is not None:
            old.sealed, old.hints, old.status, old.note = _seal({x: keys[x] for x in keys}), json.dumps(hints), "set", ""
            old.name, old.brand, old.region = name[:80] or old.name, brand[:80], region[:10]
            cid = old.id
        else:
            c = SevaChannel(tenant_id=tenant, kind=kind, name=name[:80] or k["name"], token=secrets.token_urlsafe(18),
                            sealed=_seal(keys), hints=json.dumps(hints), brand=brand[:80], region=region[:10])
            s.add(c)
            s.flush()
            cid = c.id
    return check(tenant, cid) | {"say": f"{k['name']} joined. Your keys are sealed and are never shown again."}


def remove(tenant: str, cid: str) -> dict:
    with session() as s:
        c = s.get(SevaChannel, cid)
        if c is None or c.tenant_id != tenant:
            raise ChannelError("This channel was not found.")
        c.status, c.sealed = "off", ""
    return {"removed": cid, "say": "Removed; its keys are forgotten."}


def _ch(tenant: str, cid: str) -> tuple[SevaChannel, dict]:
    _ensure()
    with session() as s:
        c = s.get(SevaChannel, cid)
        if c is None or c.tenant_id != tenant or c.status == "off":
            raise ChannelError("This channel was not found.")
        s.expunge(c)
    return c, _open(c.sealed)


def check(tenant: str, cid: str) -> dict:
    """Ask the app whether her keys work (read-only where it can), and set the webhook where the app lets us."""
    c, k = _ch(tenant, cid)
    url = address(c)
    ok, note = True, "Paste the address into the app as its webhook."
    try:
        if c.kind == "telegram":
            st, b = _http("GET", f"https://api.telegram.org/bot{k['bot_token']}/getMe")
            ok = st == 200 and (b or {}).get("ok")
            if ok and _base():
                secret = hashlib.sha256((c.token + k["bot_token"]).encode()).hexdigest()[:48]
                st2, b2 = _http("POST", f"https://api.telegram.org/bot{k['bot_token']}/setWebhook",
                                json_body={"url": url, "secret_token": secret, "allowed_updates": ["message"]})
                note = "The bot answers and its webhook is set." if st2 == 200 and (b2 or {}).get("ok") else "The bot answers; set the webhook failed."
            elif ok:
                note = "The bot answers. Set PUBLIC_BASE_URL on the server so Hoola can set the webhook."
            else:
                note = "Telegram did not accept the bot token."
        elif c.kind == "viber":
            if _base():
                st, b = _http("POST", "https://chatapi.viber.com/pa/set_webhook", headers={"X-Viber-Auth-Token": k["auth_token"]},
                              json_body={"url": url, "event_types": ["delivered", "seen", "failed"], "send_name": True})
                ok = st == 200 and (b or {}).get("status") == 0
                note = "The webhook is set." if ok else f"Viber said: {(b or {}).get('status_message', st)}"
        elif c.kind in ("messenger", "instagram"):
            st, b = _http("GET", f"{GRAPH}/me?fields=id,name&access_token={k['page_token']}")
            ok = st == 200 and bool((b or {}).get("id"))
            note = (f"The page token works ({(b or {}).get('name', '')})." if ok else "Meta did not accept the page token.")
        elif c.kind == "slack":
            st, b = _http("POST", "https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {k['bot_token']}"})
            ok = st == 200 and (b or {}).get("ok")
            note = "The bot token works." if ok else "Slack did not accept the bot token."
        elif c.kind == "line":
            st, b = _http("GET", "https://api.line.me/v2/bot/info", headers={"Authorization": f"Bearer {k['channel_token']}"})
            ok = st == 200
            note = "The channel token works." if ok else "LINE did not accept the channel token."
        elif c.kind == "twilio_sms":
            st, b = _http("GET", f"https://api.twilio.com/2010-04-01/Accounts/{k['account_sid']}.json", auth=(k["account_sid"], k["auth_token"]))
            ok = st == 200
            note = "The Twilio account answers." if ok else "Twilio did not accept the account SID / auth token."
        elif c.kind == "wechat":
            tok = _wechat_token(c, k, fresh=True)
            ok = bool(tok)
            note = "The AppID and AppSecret work." if ok else "WeChat did not give an access token (AppID / AppSecret / IP allow-list)."
    except Exception as e:   # noqa: BLE001 - a network failure is a note, not a crash
        ok, note = False, f"Could not reach the app: {str(e)[:120]}"
    with session() as s:
        row = s.get(SevaChannel, cid)
        row.status, row.note = ("ok" if ok else "error"), note[:400]
        v = _view(row)
    return v


# ---------------------------------------------------------------- reading what the apps send (signature first)
def _hmac(key: str, raw: bytes, algo=hashlib.sha256) -> bytes:
    return hmac.new(key.encode(), raw, algo).digest()


def verify_get(c: SevaChannel, k: dict, q: dict) -> str | None:
    """The app's own address check (GET). Returns the body to answer with, None = refuse."""
    if c.kind in ("messenger", "instagram"):
        if q.get("hub.mode") == "subscribe" and hmac.compare_digest(str(q.get("hub.verify_token", "")), k.get("verify_token", "")):
            return str(q.get("hub.challenge", ""))
        return None
    if c.kind == "x" and q.get("crc_token"):
        d = base64.b64encode(_hmac(k["consumer_secret"], str(q["crc_token"]).encode())).decode()
        return json.dumps({"response_token": "sha256=" + d})
    if c.kind == "wechat":
        return str(q.get("echostr", "")) if _wechat_sig_ok(k, q) else None
    return None


def _wechat_sig_ok(k: dict, q: dict) -> bool:
    parts = sorted([k.get("token", ""), str(q.get("timestamp", "")), str(q.get("nonce", ""))])
    return hmac.compare_digest(hashlib.sha1("".join(parts).encode()).hexdigest(), str(q.get("signature", "")))


def _jwt_ok(token: str, secret: str, raw: bytes) -> bool:
    """Vonage signed webhook: HS256 JWT with payload_hash = sha256(body)."""
    try:
        h, p, sig = token.split(".")
        want = base64.urlsafe_b64encode(_hmac(secret, f"{h}.{p}".encode())).rstrip(b"=").decode()
        if not hmac.compare_digest(want, sig):
            return False
        claims = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
        if claims.get("payload_hash") and claims["payload_hash"] != hashlib.sha256(raw).hexdigest():
            return False
        return not (claims.get("exp") and claims["exp"] < time.time())
    except Exception:   # noqa: BLE001
        return False


def verify_post(c: SevaChannel, k: dict, headers: dict, raw: bytes, url: str, form: dict, q: dict) -> bool:
    h = {a.lower(): b for a, b in headers.items()}
    if c.kind == "telegram":
        want = hashlib.sha256((c.token + k["bot_token"]).encode()).hexdigest()[:48]
        return hmac.compare_digest(h.get("x-telegram-bot-api-secret-token", ""), want)
    if c.kind in ("messenger", "instagram"):
        sig = h.get("x-hub-signature-256", "")
        return sig.startswith("sha256=") and hmac.compare_digest(sig[7:], _hmac(k["app_secret"], raw).hex())
    if c.kind == "twilio_sms":
        base = url + "".join(f"{a}{form[a]}" for a in sorted(form))
        want = base64.b64encode(_hmac(k["auth_token"], base.encode(), hashlib.sha1)).decode()
        return hmac.compare_digest(h.get("x-twilio-signature", ""), want)
    if c.kind == "vonage_sms":
        auth = h.get("authorization", "")
        return auth.startswith("Bearer ") and _jwt_ok(auth[7:], k["signature_secret"], raw)
    if c.kind == "line":
        return hmac.compare_digest(h.get("x-line-signature", ""), base64.b64encode(_hmac(k["channel_secret"], raw)).decode())
    if c.kind == "viber":
        return hmac.compare_digest(h.get("x-viber-content-signature", ""), _hmac(k["auth_token"], raw).hex())
    if c.kind == "slack":
        from ..bahar import slack_sig_ok
        return slack_sig_ok(k["signing_secret"], h.get("x-slack-request-timestamp", ""), raw, h.get("x-slack-signature", ""))
    if c.kind == "x":
        sig = h.get("x-twitter-webhooks-signature", "")
        return sig.startswith("sha256=") and hmac.compare_digest(sig[7:], base64.b64encode(_hmac(k["consumer_secret"], raw)).decode())
    if c.kind == "zalo":
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            return False
        want = hashlib.sha256((k["app_id"] + raw.decode() + str(body.get("timestamp", "")) + k["oa_secret"]).encode()).hexdigest()
        return hmac.compare_digest(h.get("x-zevent-signature", ""), "mac=" + want)
    if c.kind == "kakao":
        return True                         # the address holds her secret token; Kakao skill calls carry no signature
    if c.kind == "wechat":
        return _wechat_sig_ok(k, q)
    return False


def parse(c: SevaChannel, k: dict, raw: bytes, form: dict) -> list[dict]:
    """The customer messages in one webhook call: [{from, name, text, ext_id, meta}]. Echoes / bots / other events dropped."""
    out: list[dict] = []
    try:
        if c.kind == "wechat":
            x = ET.fromstring(raw)
            if (x.findtext("MsgType") or "") == "text":
                out.append({"from": x.findtext("FromUserName") or "", "name": "", "text": x.findtext("Content") or "",
                            "ext_id": x.findtext("MsgId") or "", "meta": {"to": x.findtext("ToUserName") or ""}})
            return out
        if c.kind == "twilio_sms":
            if form.get("From") and form.get("Body") is not None:
                out.append({"from": form["From"], "name": "", "text": form.get("Body", ""), "ext_id": form.get("MessageSid", ""), "meta": {}})
            return out
        b = json.loads(raw or b"{}")
    except (ValueError, ET.ParseError):
        return []
    if c.kind == "telegram":
        m = b.get("message") or {}
        frm = m.get("from") or {}
        if m and not frm.get("is_bot") and (m.get("chat") or {}).get("type") == "private":
            out.append({"from": str(frm.get("id", "")), "name": " ".join(x for x in (frm.get("first_name"), frm.get("last_name")) if x),
                        "text": m.get("text") or m.get("caption") or "", "ext_id": str(b.get("update_id", "")),
                        "meta": {"chat_id": (m.get("chat") or {}).get("id")}})
    elif c.kind in ("messenger", "instagram"):
        if b.get("object") not in ("page", "instagram"):
            return []
        for e in b.get("entry") or []:
            for ev in e.get("messaging") or []:
                msg = ev.get("message") or {}
                if msg and not msg.get("is_echo") and (msg.get("text") or msg.get("attachments")):
                    out.append({"from": str((ev.get("sender") or {}).get("id", "")), "name": "", "text": msg.get("text") or "(a file)",
                                "ext_id": str(msg.get("mid", "")), "meta": {}})
    elif c.kind == "vonage_sms":
        if b.get("from") and b.get("text") is not None:
            out.append({"from": str(b["from"]), "name": "", "text": b.get("text", ""), "ext_id": str(b.get("message_uuid", "")), "meta": {}})
    elif c.kind == "line":
        for ev in b.get("events") or []:
            if ev.get("type") == "message" and (ev.get("message") or {}).get("type") == "text":
                out.append({"from": str((ev.get("source") or {}).get("userId", "")), "name": "", "text": ev["message"].get("text", ""),
                            "ext_id": str(ev["message"].get("id", "")), "meta": {"reply_token": ev.get("replyToken", "")}})
    elif c.kind == "viber":
        if b.get("event") == "message" and (b.get("message") or {}).get("type") == "text":
            snd = b.get("sender") or {}
            out.append({"from": str(snd.get("id", "")), "name": snd.get("name", ""), "text": b["message"].get("text", ""),
                        "ext_id": str(b.get("message_token", "")), "meta": {}})
    elif c.kind == "slack":
        ev = b.get("event") or {}
        if b.get("type") == "event_callback" and ev.get("type") == "message" and not ev.get("bot_id") and not ev.get("subtype"):
            out.append({"from": f"{ev.get('channel', '')}/{ev.get('user', '')}", "name": "", "text": ev.get("text", ""),
                        "ext_id": str(ev.get("client_msg_id") or ev.get("ts", "")), "meta": {"channel": ev.get("channel", "")}})
    elif c.kind == "x":
        me = str(b.get("for_user_id", ""))
        for ev in b.get("direct_message_events") or []:
            mc = ev.get("message_create") or {}
            if ev.get("type") == "message_create" and str(mc.get("sender_id", "")) != me:
                out.append({"from": str(mc.get("sender_id", "")), "name": "", "text": (mc.get("message_data") or {}).get("text", ""),
                            "ext_id": str(ev.get("id", "")), "meta": {}})
    elif c.kind == "zalo":
        if b.get("event_name") == "user_send_text":
            out.append({"from": str((b.get("sender") or {}).get("id", "")), "name": "", "text": (b.get("message") or {}).get("text", ""),
                        "ext_id": str((b.get("message") or {}).get("msg_id", "")), "meta": {}})
    elif c.kind == "kakao":
        ur = b.get("userRequest") or {}
        if ur.get("utterance"):
            out.append({"from": str((ur.get("user") or {}).get("id", "")), "name": "", "text": ur["utterance"],
                        "ext_id": hashlib.sha256(raw).hexdigest()[:40], "meta": {}})
    return [m for m in out if m["from"]]


# ---------------------------------------------------------------- sending back
def _wechat_token(c: SevaChannel, k: dict, fresh: bool = False) -> str:
    st, b = _http("GET", f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={k['app_id']}&secret={k['app_secret']}")
    return str((b or {}).get("access_token") or "") if st == 200 else ""


def _send_raw(c: SevaChannel, k: dict, to: str, text: str, meta: dict | None = None) -> bool:
    meta = meta or {}
    if c.kind == "telegram":
        st, b = _http("POST", f"https://api.telegram.org/bot{k['bot_token']}/sendMessage", json_body={"chat_id": meta.get("chat_id") or to, "text": text})
        return st == 200 and bool((b or {}).get("ok"))
    if c.kind in ("messenger", "instagram"):
        st, _ = _http("POST", f"{GRAPH}/me/messages?access_token={k['page_token']}",
                      json_body={"recipient": {"id": to}, "messaging_type": "RESPONSE", "message": {"text": text}})
        return st == 200
    if c.kind == "twilio_sms":
        st, _ = _http("POST", f"https://api.twilio.com/2010-04-01/Accounts/{k['account_sid']}/Messages.json",
                      data={"From": k["from_number"], "To": to, "Body": text}, auth=(k["account_sid"], k["auth_token"]))
        return st in (200, 201)
    if c.kind == "vonage_sms":
        st, _ = _http("POST", "https://api.nexmo.com/v1/messages", auth=(k["api_key"], k["api_secret"]),
                      json_body={"message_type": "text", "channel": "sms", "to": to.lstrip("+"), "from": k["from_number"], "text": text})
        return st in (200, 202)
    if c.kind == "line":
        st, _ = _http("POST", "https://api.line.me/v2/bot/message/push", headers={"Authorization": f"Bearer {k['channel_token']}"},
                      json_body={"to": to, "messages": [{"type": "text", "text": text}]})
        return st == 200
    if c.kind == "viber":
        st, b = _http("POST", "https://chatapi.viber.com/pa/send_message", headers={"X-Viber-Auth-Token": k["auth_token"]},
                      json_body={"receiver": to, "type": "text", "text": text, "sender": {"name": k.get("sender_name", "Support")[:28]}})
        return st == 200 and (b or {}).get("status") == 0
    if c.kind == "slack":
        st, b = _http("POST", "https://slack.com/api/chat.postMessage", headers={"Authorization": f"Bearer {k['bot_token']}"},
                      json_body={"channel": meta.get("channel") or to.split("/", 1)[0], "text": text})
        return st == 200 and bool((b or {}).get("ok"))
    if c.kind == "x":
        st, _ = _http("POST", f"https://api.x.com/2/dm_conversations/with/{to}/messages", headers={"Authorization": f"Bearer {k['user_token']}"},
                      json_body={"text": text})
        return st in (200, 201)
    if c.kind == "zalo":
        st, b = _http("POST", "https://openapi.zalo.me/v3.0/oa/message/cs", headers={"access_token": k["access_token"]},
                      json_body={"recipient": {"user_id": to}, "message": {"text": text}})
        return st == 200 and (b or {}).get("error", 0) == 0
    if c.kind == "wechat":
        tok = _wechat_token(c, k)
        if not tok:
            return False
        st, b = _http("POST", f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={tok}",
                      json_body={"touser": to, "msgtype": "text", "text": {"content": text}})
        return st == 200 and (b or {}).get("errcode", 0) == 0
    if c.kind == "email":
        from . import supportmail as SM
        return SM.send(c, k, to, text, meta)
    if c.kind == "web":
        return True                           # the visitor's page reads it (stored by send_to)
    if c.kind == "api":
        from . import webchat as WC
        return WC.to_webhook(c, k, to, text)
    return False                              # kakao: only inside the customer's own call


def _shape(kind: str, text: str) -> str:
    from . import engine as E
    t = E.shape(text, ENGINE_CH.get(kind, "other"))
    return t[:2000] if kind != "line" else t[:5000]


def _last_in(tenant: str, customer: str):
    with session() as s:
        m = s.scalars(select(SevaChatMsg).where(SevaChatMsg.tenant_id == tenant, SevaChatMsg.customer == customer,
                                                SevaChatMsg.direction == "in", SevaChatMsg.channel_id != "phone")
                      .order_by(SevaChatMsg.at.desc())).first()
        return (m.channel_id, _aware(m.at), json.loads(m.meta or "{}")) if m else (None, None, {})


def opted_out(tenant: str, customer: str) -> bool:
    _ensure()
    with session() as s:
        r = s.scalars(select(SevaChatOptOut).where(SevaChatOptOut.tenant_id == tenant, SevaChatOptOut.customer == customer)
                      .order_by(SevaChatOptOut.at.desc())).first()
        return bool(r and r.off)


def send_to(tenant: str, customer: str, text: str, by: str = "hoola", decision: str = "") -> dict:
    """A message to a customer on the app they wrote from - inside the app's window, never to someone who wrote STOP."""
    _ensure()
    S = _S()
    text = S._clean(text, 3000)
    if not text:
        raise ChannelError("An empty message cannot be sent.")
    if S._secret(text):
        raise ChannelError("This holds details like an OTP / PIN / card; that is never sent.")
    if opted_out(tenant, customer):
        raise ChannelError("This customer wrote STOP; we do not send them messages.")
    cid, last, meta = _last_in(tenant, customer)
    if cid is None and customer.startswith("email:"):
        with session() as s:          # e.g. her contact form (G5): the answer goes from her support address
            r = s.scalars(select(SevaChannel).where(SevaChannel.tenant_id == tenant, SevaChannel.kind == "email",
                                                    SevaChannel.status != "off")).first()
            cid = r.id if r is not None else None
    if cid is None and customer.startswith(("phone:", "wa:")):
        try:          # G3: a caller - WhatsApp if they ever wrote there (inside Meta's window), else a call-back by her
            from ..employee import inbox
            if inbox.notice_by_phone(tenant, customer.split(":", 1)[1], text):
                _store(tenant, "phone", customer, "", "out", by, text, "", "sent", decision)
                return {"sent": "whatsapp", "text": text}
        except Exception:   # noqa: BLE001
            log.exception("support phone customer notice")
        raise ChannelError("This customer only called: call them back (they have not written on WhatsApp or another app).")
    if cid is None:
        raise ChannelError("This customer has not written on any of your apps.")
    c, k = _ch(tenant, cid)
    w = KINDS[c.kind]["window_h"]
    if w < 0:
        raise ChannelError(f"{KINDS[c.kind]['name']} lets a business reply only while the customer is writing.")
    if w and last and S.clock() - last > timedelta(hours=w):
        raise ChannelError(f"{KINDS[c.kind]['name']} allows replies only within {w} hours of the customer's last message.")
    body = _shape(c.kind, text)
    ok = False
    try:
        ok = _send_raw(c, k, customer.split(":", 1)[1], body, meta)
    except Exception:   # noqa: BLE001
        log.exception("support channel send")
    _store(tenant, cid, customer, "", "out", by, body, "", "sent" if ok else "failed", decision)
    if not ok:
        raise ChannelError(f"{KINDS[c.kind]['name']} did not take the message.")
    return {"sent": c.kind, "text": body}


def _store(tenant: str, cid: str, customer: str, name: str, direction: str, by: str, text: str, ext_id: str, status: str,
           decision: str = "", meta: dict | None = None) -> None:
    S = _S()
    with session() as s:
        s.add(SevaChatMsg(tenant_id=tenant, channel_id=cid, customer=customer, name=name[:120], direction=direction, by=by[:80],
                          text=S.mask(text)[:3000], ext_id=ext_id[:120], status=status, decision=decision[:20],
                          meta=json.dumps(meta or {}), at=S.clock()))


def _seen(tenant: str, cid: str, ext_id: str) -> bool:
    if not ext_id:
        return False
    with session() as s:
        return s.scalars(select(SevaChatMsg.id).where(SevaChatMsg.tenant_id == tenant, SevaChatMsg.channel_id == cid,
                                                      SevaChatMsg.ext_id == ext_id)).first() is not None


def _held(tenant: str, customer: str) -> bool:
    """A person has (or is about to take) this customer: Hoola stays quiet."""
    from . import handover as H
    H._ensure()
    with session() as s:
        return s.scalars(select(H.SevaHandover.id).where(H.SevaHandover.tenant_id == tenant, H.SevaHandover.customer == customer,
                                                         H.SevaHandover.status.in_(("waiting", "taken")))).first() is not None


# ---------------------------------------------------------------- one message in -> one reply out
def answer(tenant: str, kind: str, customer: str, name: str, text: str) -> tuple[str, str]:
    """(reply, decision) for one customer message - every choice made by the answer engine and the hand-over rules."""
    from . import engine as E
    from . import handover as H
    S = _S()
    ch = ENGINE_CH.get(kind, "other")
    tch = TICKET_CH.get(kind, kind)
    d = E.reply(tenant, text, ch, customer, f"customer:{customer}")
    dec = d.get("decision", "")
    if dec in ("answer", "status", "confirmed", "not_fixed", "rated") and d.get("reply"):
        return d["reply"], dec
    if dec == "answer":
        return "You're welcome!", dec
    if dec == "refuse":
        return SAFE, dec
    if dec == "clarify":
        qs = [c["question"] for c in (d.get("candidates") or [])][:3]
        return ("Did you mean: " + " / ".join(qs) + "?") if qs else "Could you tell me a little more?", dec
    if dec == "draft":
        return "Thanks - a person from our team will reply here shortly.", dec
    if dec == "no_answer":
        t = S.new_ticket(tenant, text, tch, customer, name, by=f"customer:{customer}")
        return f"I don't have that answer, so I have passed your question to the team. Your request number is {t['number']}.", dec
    rule = d.get("rule") or ("money" if dec == "request" else "unknown")
    h = H.start(tenant, customer, tch, "; ".join(d.get("why") or [])[:300], rule, text, "", name)
    return h["customer_line"], "handover"


def handle(tenant: str, cid: str, msgs: list[dict]) -> list[str]:
    """Every message of one webhook call. Returns the replies (KakaoTalk / WeChat send them back in the same call)."""
    S = _S()
    c, _k = _ch(tenant, cid)
    pre = KINDS[c.kind]["prefix"]
    replies: list[str] = []
    for m in msgs:
        if _seen(tenant, cid, m["ext_id"]):
            continue
        who = m["from"]
        if pre == "sms":
            who = "+" + S._digits(who)
        customer = m.get("customer") or f"{pre}:{who}"
        text = S._clean(m["text"], 3000)
        _store(tenant, cid, customer, m.get("name", ""), "in", "customer", text, m["ext_id"], "", "", m.get("meta"))
        with session() as s:
            row = s.get(SevaChannel, cid)
            row.last_in_at = S.clock()
        if STOP.match(text):
            with session() as s:
                s.add(SevaChatOptOut(tenant_id=tenant, customer=customer, off=True, at=S.clock()))
            replies.append(_reply(tenant, c, customer, "You will get no more messages from us. Write START to undo.", "stop", force=True))
            continue
        if START.match(text) and opted_out(tenant, customer):
            with session() as s:
                s.add(SevaChatOptOut(tenant_id=tenant, customer=customer, off=False, at=S.clock()))
            replies.append(_reply(tenant, c, customer, "You will get our messages again.", "start"))
            continue
        if _held(tenant, customer):
            S._publish(tenant, "seva_chat", {"customer": customer, "kind": c.kind, "text": S.mask(text)[:300], "held": True})
            continue
        try:
            words, dec = answer(tenant, c.kind, customer, m.get("name", ""), text)
        except Exception:   # noqa: BLE001 - never silent: hand the customer to a person
            log.exception("support channel answer")
            from . import handover as H
            words, dec = H.start(tenant, customer, TICKET_CH.get(c.kind, c.kind), "Hoola could not answer (an error)", "unknown",
                                 text, "", m.get("name", ""))["customer_line"], "handover"
        replies.append(_reply(tenant, c, customer, words, dec))
        S._publish(tenant, "seva_chat", {"customer": customer, "kind": c.kind, "text": S.mask(text)[:300], "decision": dec})
    return [r for r in replies if r]


def _reply(tenant: str, c: SevaChannel, customer: str, words: str, dec: str, force: bool = False) -> str:
    """Sends now (or, for the apps that answer inside the same call, returns it to be answered)."""
    if c.kind in ("kakao", "wechat", "web", "api"):
        if c.kind in ("web", "api") and opted_out(tenant, customer) and not force:
            return ""
        _store(tenant, c.id, customer, "", "out", "hoola", _shape(c.kind, words), "", "sent", dec)
        return _shape(c.kind, words)
    try:
        if force:
            _c, k = _ch(tenant, c.id)
            _send_raw(_c, k, customer.split(":", 1)[1], _shape(c.kind, words), _last_in(tenant, customer)[2])
            _store(tenant, c.id, customer, "", "out", "hoola", words, "", "sent", dec)
        else:
            send_to(tenant, customer, words, "hoola", dec)
    except ChannelError as e:
        log.info("support channel reply not sent: %s", e)
    return ""


def inbound(token: str, method: str, headers: dict, raw: bytes, url: str, form: dict, q: dict) -> tuple[int, str, str]:
    """The public webhook door: (status, body, media type). Signature first; nothing is read from a call that fails it."""
    _ensure()
    with session() as s:
        c = s.scalars(select(SevaChannel).where(SevaChannel.token == token, SevaChannel.status != "off")).first()
        if c is None:
            return 404, "", "text/plain"
        s.expunge(c)
    k = _open(c.sealed)
    if method == "GET":
        out = verify_get(c, k, q)
        return (200, out, "application/json" if c.kind == "x" else "text/plain") if out is not None else (403, "", "text/plain")
    if not verify_post(c, k, headers, raw, url, form, q):
        log.warning("support channel %s: a call with a wrong signature was refused", c.kind)
        return 403, "", "text/plain"
    if c.kind == "slack":
        try:
            b = json.loads(raw or b"{}")
        except ValueError:
            b = {}
        if b.get("type") == "url_verification":
            return 200, json.dumps({"challenge": b.get("challenge", "")}), "application/json"
    msgs = parse(c, k, raw, form)
    replies = handle(c.tenant_id, c.id, msgs) if msgs else []
    if c.kind == "kakao":
        txt = replies[0] if replies else "Thanks - we got your message."
        return 200, json.dumps({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": txt[:1000]}}]}}), "application/json"
    if c.kind == "wechat":
        if not replies or not msgs:
            return 200, "success", "text/plain"
        m = msgs[0]
        xml = (f"<xml><ToUserName><![CDATA[{m['from']}]]></ToUserName><FromUserName><![CDATA[{m['meta'].get('to', '')}]]></FromUserName>"
               f"<CreateTime>{int(time.time())}</CreateTime><MsgType><![CDATA[text]]></MsgType>"
               f"<Content><![CDATA[{replies[0].replace(']]>', '] ]>')}]]></Content></xml>")
        return 200, xml, "application/xml"
    if c.kind == "twilio_sms":
        return 200, "<Response></Response>", "application/xml"
    return 200, "ok", "text/plain"


# ---------------------------------------------------------------- her side: the conversations
def conversations(tenant: str, limit: int = 60) -> list[dict]:
    _ensure()
    out: dict[str, dict] = {}
    with session() as s:
        kinds = {c.id: c.kind for c in s.scalars(select(SevaChannel).where(SevaChannel.tenant_id == tenant)).all()}
        for m in s.scalars(select(SevaChatMsg).where(SevaChatMsg.tenant_id == tenant).order_by(SevaChatMsg.at.desc()).limit(2000)).all():
            if m.customer in out:
                continue
            kd = kinds.get(m.channel_id, "phone" if m.channel_id == "phone" else "")
            out[m.customer] = {"customer": m.customer, "kind": kd, "app": "Phone" if kd == "phone" else KINDS.get(kd, {}).get("name", ""),
                               "name": m.name, "last": m.text[:160], "last_by": m.by, "at": _aware(m.at).isoformat()}
            if len(out) >= limit:
                break
    for v in out.values():
        v["held"] = _held(tenant, v["customer"])
        if not v["name"]:
            with session() as s:
                n = s.scalars(select(SevaChatMsg.name).where(SevaChatMsg.tenant_id == tenant, SevaChatMsg.customer == v["customer"],
                                                             SevaChatMsg.name != "")).first()
            v["name"] = n or ""
    return list(out.values())


def thread(tenant: str, customer: str) -> dict:
    _ensure()
    with session() as s:
        rows = s.scalars(select(SevaChatMsg).where(SevaChatMsg.tenant_id == tenant, SevaChatMsg.customer == customer)
                         .order_by(SevaChatMsg.at).limit(300)).all()
        msgs = [{"direction": m.direction, "by": m.by, "text": m.text, "status": m.status, "decision": m.decision,
                 "at": _aware(m.at).isoformat(), "file": json.loads(m.meta or "{}").get("file", "")} for m in rows]
    return {"customer": customer, "messages": msgs, "held": _held(tenant, customer), "stopped": opted_out(tenant, customer)}


def reply_as_person(tenant: str, customer: str, text: str, by: str = "owner") -> dict:
    """A person of her team writes to the customer from the desk; it counts as taking any waiting hand-over."""
    out = send_to(tenant, customer, text, by)
    from . import handover as H
    H.replied_key(tenant, customer, by)
    return out | {"say": "Sent."}


def overview(tenant: str) -> dict:
    return {"channels": channels(tenant), "catalog": catalog(), "conversations": conversations(tenant, 30)}
