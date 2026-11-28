"""G5 of docs/SUPPORT_GLOBAL_PLAN.md: the chat on her website and inside her own app / software.

- WEBSITE CHAT: one line of code for any website (`<script src=".../static/support/widget.js" data-hoola-support="KEY">`):
  a chat button + panel, files (pictures / PDF), a "Call me" button. Only the website addresses she lists may use it
  (the browser's Origin is checked on every call); a visitor gets a signed visitor token; a logged-in user of her site can
  be named with `user_id` + `user_hash` (= HMAC-SHA256 of the user id with her identity secret, made on HER server) so
  they see only their own thread, the same one as in her app.
- HER APP / SOFTWARE: the same answer engine as a REST API with its own key and limits (POST /api/support/v1/messages,
  GET /api/support/v1/messages), replies a person or a ticket update sends later reach HER webhook (signed with
  X-Hoola-Signature); a hosted chat page (/support/chat/KEY) for any app's web view - iOS, Android, React Native, a kiosk.
- CONTACT FORM: POST /api/support/form/KEY -> a ticket (a hidden honeypot field drops bots).
Every message goes through the same path as the messaging apps (seva/channels.py): her knowledge, her trust levels, her
hand-over rules, her workflow, the ticket updates. Text a visitor writes is data, never an instruction.
Not built: native iOS / Android / React Native kits (the hosted page + the REST API cover an app today), reviews.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select

from ..db import new_id, session

log = logging.getLogger(__name__)

UPLOADS = Path("data") / "seva_uploads"
MAX_FILE = 5 * 1024 * 1024
FILE_KINDS = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg", b"GIF8": "image/gif", b"%PDF": "application/pdf"}
LIMITS = {"visitor": (20, 60), "key": (120, 60), "ip": (60, 60), "form": (5, 600)}     # (calls, seconds)
_HITS: dict[str, deque] = defaultdict(deque)
_LOCK = threading.Lock()


class WebError(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _CH():
    from . import channels as CH
    return CH


def _S():
    from . import service as S
    return S


def _limit(kind: str, who: str) -> None:
    n, win = LIMITS[kind]
    key, t = f"{kind}:{who}", time.monotonic()
    with _LOCK:
        q = _HITS[key]
        while q and q[0] < t - win:
            q.popleft()
        if len(q) >= n:
            raise WebError("Too many messages; wait a moment.", 429)
        q.append(t)


# ---------------------------------------------------------------- her setup
DEFAULT = {"domains": [], "title": "Chat with us", "greeting": "Hello! How can we help?", "colour": "#5B45E0", "files": True,
           "call_me": True, "webhook_url": ""}


def _settings(c) -> dict:
    try:
        return DEFAULT | json.loads(c.settings or "{}")
    except ValueError:
        return dict(DEFAULT)


def _host(u: str) -> str:
    u = str(u or "").strip().lower()
    if not u:
        return ""
    if "://" not in u:
        u = "https://" + u
    return (urlparse(u).hostname or "").lstrip(".")


def clean_settings(body: dict, old: dict | None = None) -> dict:
    out = dict(old or DEFAULT)
    b = body if isinstance(body, dict) else {}
    if "domains" in b:
        ds = []
        for d in (b["domains"] or [])[:30]:
            h = _host(d)
            if not h or not re.match(r"^[a-z0-9.*-]+$", h):
                raise WebError(f"{d}: give a website address like shop.example.com.")
            ds.append(h)
        out["domains"] = sorted(set(ds))
    for k, n in (("title", 60), ("greeting", 300)):
        if k in b:
            out[k] = str(b[k] or "").strip()[:n] or DEFAULT[k]
    if "colour" in b:
        c = str(b["colour"] or "").strip()
        if not re.match(r"^#[0-9a-fA-F]{6}$", c):
            raise WebError("The colour is like #5B45E0.")
        out["colour"] = c
    for k in ("files", "call_me"):
        if k in b:
            out[k] = bool(b[k])
    if "webhook_url" in b:
        w = str(b["webhook_url"] or "").strip()
        if w and not w.startswith("https://"):
            raise WebError("The webhook address must start with https://.")
        out["webhook_url"] = w[:300]
    return out


def setup(tenant: str, kind: str, body: dict | None = None) -> dict:
    """Make (or change) her website chat ('web') or her app's API ('api'). New secrets are shown ONCE."""
    CH = _CH()
    CH._ensure()
    if kind not in ("web", "api"):
        raise WebError("kind: web | api")
    shown: dict[str, str] = {}
    with session() as s:
        c = s.scalars(select(CH.SevaChannel).where(CH.SevaChannel.tenant_id == tenant, CH.SevaChannel.kind == kind,
                                                   CH.SevaChannel.status != "off")).first()
        if c is None:
            keys = {"identity_secret": "hid_" + secrets.token_urlsafe(24), "visitor_secret": secrets.token_urlsafe(32)}
            shown["identity_secret"] = keys["identity_secret"]
            if kind == "api":
                keys["api_key"] = "hsk_" + secrets.token_urlsafe(28)
                keys["webhook_secret"] = "whs_" + secrets.token_urlsafe(24)
                shown["api_key"], shown["webhook_secret"] = keys["api_key"], keys["webhook_secret"]
            c = CH.SevaChannel(tenant_id=tenant, kind=kind, name=CH.KINDS[kind]["name"], token=secrets.token_urlsafe(18),
                               sealed=CH._seal(keys), hints=json.dumps({k: "…" + v[-4:] for k, v in shown.items()}), status="ok",
                               settings=json.dumps(clean_settings(body or {})))
            s.add(c)
            s.flush()
        else:
            c.settings = json.dumps(clean_settings(body or {}, _settings(c)))
        cid = c.id
    return view(tenant, kind) | ({"secrets_once": shown, "say": "Copy these now: they are shown only this once."} if shown else
                                 {"say": "Saved."})


def rotate(tenant: str, kind: str, what: str) -> dict:
    """A new identity secret / API key / webhook secret, shown once; the old one stops working at once."""
    CH = _CH()
    prefix = {"identity_secret": "hid_", "api_key": "hsk_", "webhook_secret": "whs_"}.get(what)
    if not prefix or (what != "identity_secret" and kind != "api"):
        raise WebError("Nothing to renew with that name.")
    c, k = _row(tenant, kind)
    k[what] = prefix + secrets.token_urlsafe(28)
    with session() as s:
        r = s.get(CH.SevaChannel, c.id)
        r.sealed = CH._seal(k)
        h = json.loads(r.hints or "{}")
        h[what] = "…" + k[what][-4:]
        r.hints = json.dumps(h)
    return {"secrets_once": {what: k[what]}, "say": "The old one no longer works. Copy the new one now."}


def _row(tenant: str, kind: str):
    CH = _CH()
    CH._ensure()
    with session() as s:
        c = s.scalars(select(CH.SevaChannel).where(CH.SevaChannel.tenant_id == tenant, CH.SevaChannel.kind == kind,
                                                   CH.SevaChannel.status != "off")).first()
        if c is None:
            raise WebError("Not set up yet.", 404)
        s.expunge(c)
    return c, CH._open(c.sealed)


def view(tenant: str, kind: str = "") -> dict:
    CH = _CH()
    out = {}
    for kd in (("web", "api") if not kind else (kind,)):
        try:
            c, _k = _row(tenant, kd)
        except WebError:
            out[kd] = None
            continue
        base = CH._base()
        st = _settings(c)
        v = {"id": c.id, "key": c.token, "settings": st, "hints": json.loads(c.hints or "{}"), "last_in": CH._view(c)["last_in"]}
        if kd == "web":
            v["snippet"] = f'<script src="{base}/static/support/widget.js" data-hoola-support="{c.token}" async></script>'
            v["page"] = f"{base}/support/chat/{c.token}"
            v["form"] = f"{base}/api/support/form/{c.token}"
        else:
            v["api"] = f"{base}/api/support/v1/messages"
            v["page"] = f"{base}/support/chat/{c.token}"
        out[kd] = v
    return out if not kind else out[kind]


def user_hash(identity_secret: str, user_id: str) -> str:
    """What HER server puts beside a signed-in user's id (never made in the browser)."""
    return hmac.new(identity_secret.encode(), str(user_id).encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------- the visitor
def _origin_ok(st: dict, origin: str, own_page: bool) -> bool:
    if own_page:
        return True
    h = _host(origin)
    if not h:
        return False
    for d in st.get("domains", []):
        if h == d or (d.startswith("*.") and h.endswith(d[1:])) or h.endswith("." + d):
            return True
    return False


def _by_key(key: str):
    CH = _CH()
    CH._ensure()
    with session() as s:
        c = s.scalars(select(CH.SevaChannel).where(CH.SevaChannel.token == key, CH.SevaChannel.kind.in_(("web", "api")),
                                                   CH.SevaChannel.status != "off")).first()
        if c is None:
            raise WebError("Not found.", 404)
        s.expunge(c)
    return c, CH._open(c.sealed)


def _token(k: dict, customer: str, days: int = 30) -> str:
    exp = int(time.time()) + days * 86400
    body = base64.urlsafe_b64encode(json.dumps({"c": customer, "e": exp}).encode()).decode().rstrip("=")
    sig = hmac.new(k["visitor_secret"].encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def _read_token(k: dict, tok: str) -> str:
    try:
        body, sig = str(tok).split(".")
        want = hmac.new(k["visitor_secret"].encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(want, sig):
            raise ValueError
        d = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if d["e"] < time.time():
            raise ValueError
        return d["c"]
    except Exception:   # noqa: BLE001
        raise WebError("Start the chat again.", 401)


def session_start(key: str, origin: str, own_page: bool, user_id: str = "", hashv: str = "", name: str = "", ip: str = "") -> dict:
    """A visitor opens the chat: a signed visitor token (and their own earlier messages when they are signed in)."""
    c, k = _by_key(key)
    st = _settings(c)
    if c.kind == "web" and not _origin_ok(st, origin, own_page):
        raise WebError("This website is not on the list of addresses allowed to use this chat.", 403)
    _limit("ip", ip or "?")
    if user_id:
        if not hashv or not hmac.compare_digest(user_hash(k["identity_secret"], user_id), str(hashv)):
            raise WebError("The signed-in user could not be checked (user_hash).", 403)
        customer = "user:" + re.sub(r"[^A-Za-z0-9_.@:-]", "", str(user_id))[:120]
    else:
        customer = "web:" + secrets.token_urlsafe(12)
    return {"token": _token(k, customer), "title": st["title"], "greeting": st["greeting"], "colour": st["colour"],
            "files": st["files"], "call_me": st["call_me"], "messages": messages(c.tenant_id, customer)["messages"],
            "signed_in": bool(user_id)}


def messages(tenant: str, customer: str, after: str = "") -> dict:
    CH = _CH()
    with session() as s:
        sel = select(CH.SevaChatMsg).where(CH.SevaChatMsg.tenant_id == tenant, CH.SevaChatMsg.customer == customer)
        rows = s.scalars(sel.order_by(CH.SevaChatMsg.at).limit(200)).all()
        out = [{"id": m.id, "from": "you" if m.direction == "in" else ("team" if m.by not in ("hoola",) else "hoola"),
                "text": m.text, "at": CH._aware(m.at).isoformat()} for m in rows if m.status != "failed"]
    if after:
        i = next((n for n, m in enumerate(out) if m["id"] == after), None)
        out = out[i + 1:] if i is not None else out
    return {"messages": out}


def visitor_send(key: str, origin: str, own_page: bool, tok: str, text: str, name: str = "", ip: str = "") -> dict:
    CH = _CH()
    c, k = _by_key(key)
    if c.kind == "web" and not _origin_ok(_settings(c), origin, own_page):
        raise WebError("This website is not allowed to use this chat.", 403)
    customer = _read_token(k, tok)
    _limit("visitor", customer)
    _limit("ip", ip or "?")
    S = _S()
    text = S._clean(text, 2000)
    if not text:
        raise WebError("Write a message.")
    CH.handle(c.tenant_id, c.id, [{"from": customer.split(":", 1)[1], "customer": customer, "name": S._clean(name, 80),
                                   "text": text, "ext_id": new_id("wm"), "meta": {}}])
    return messages(c.tenant_id, customer)


def visitor_poll(key: str, origin: str, own_page: bool, tok: str, after: str = "") -> dict:
    c, k = _by_key(key)
    if c.kind == "web" and not _origin_ok(_settings(c), origin, own_page):
        raise WebError("This website is not allowed to use this chat.", 403)
    return messages(c.tenant_id, _read_token(k, tok), after)


def visitor_file(key: str, origin: str, own_page: bool, tok: str, name: str, data: bytes) -> dict:
    CH = _CH()
    c, k = _by_key(key)
    st = _settings(c)
    if c.kind == "web" and not _origin_ok(st, origin, own_page):
        raise WebError("This website is not allowed to use this chat.", 403)
    if not st["files"]:
        raise WebError("Files are not taken in this chat.")
    customer = _read_token(k, tok)
    _limit("visitor", customer)
    if len(data) > MAX_FILE:
        raise WebError("The file is bigger than 5 MB.")
    mime = next((m for sig, m in FILE_KINDS.items() if data.startswith(sig)), "")
    if not mime:
        raise WebError("Send a picture (PNG / JPG / GIF) or a PDF.")
    fid = new_id("wf")
    d = UPLOADS / re.sub(r"[^A-Za-z0-9_-]", "_", c.tenant_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / fid).write_bytes(data)
    (d / (fid + ".json")).write_text(json.dumps({"name": re.sub(r"[^\w. -]", "_", name)[:80] or "file", "mime": mime, "customer": customer}))
    safe = re.sub(r"[^\w. -]", "_", name)[:80] or "file"
    CH._store(c.tenant_id, c.id, customer, "", "in", "customer", f"Sent a file: {safe} ({len(data) // 1024} KB)", fid, "",
              "", {"file": fid, "mime": mime})
    _S()._publish(c.tenant_id, "seva_chat", {"customer": customer, "kind": c.kind, "text": f"a file: {safe}"})
    return messages(c.tenant_id, customer)


def file_for_owner(tenant: str, fid: str) -> tuple[bytes, str, str]:
    d = UPLOADS / re.sub(r"[^A-Za-z0-9_-]", "_", tenant)
    fid = re.sub(r"[^A-Za-z0-9_-]", "", fid)
    p, m = d / fid, d / (fid + ".json")
    if not p.exists() or not m.exists():
        raise WebError("Not found.", 404)
    meta = json.loads(m.read_text())
    return p.read_bytes(), meta["mime"], meta["name"]


def call_me(key: str, origin: str, own_page: bool, tok: str, phone: str, note: str = "", name: str = "", ip: str = "") -> dict:
    """The visitor asks to be called: a call-back ticket handed to a person, with the honest window."""
    from . import handover as H
    c, k = _by_key(key)
    st = _settings(c)
    if c.kind == "web" and not _origin_ok(st, origin, own_page):
        raise WebError("This website is not allowed to use this chat.", 403)
    if not st["call_me"]:
        raise WebError("Call-backs are not offered here.")
    customer = _read_token(k, tok)
    _limit("form", customer)
    S = _S()
    d = S._digits(phone)
    if len(d) < 8:
        raise WebError("Give the phone number to call, with the country code.")
    h = H.start(c.tenant_id, "", "phone", "the visitor asked to be called back", "asked",
                S._clean(note, 500) or "Please call me back.", "", S._clean(name, 80) or "Website visitor")
    with session() as s:
        t = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == c.tenant_id, S.SevaTicket.number == h["ticket"])).first()
        t.customer = "phone:" + d
        S._add_note(t, "hoola", f"Call back on +{d} (asked in the website chat).")
    _CH()._store(c.tenant_id, c.id, customer, "", "out", "hoola", h["customer_line"], "", "sent", "callback")
    return messages(c.tenant_id, customer) | {"line": h["customer_line"]}


def form(key: str, origin: str, own_page: bool, body: dict, ip: str = "") -> dict:
    """Her contact form: a ticket. The hidden field `website` must stay empty (bots fill it)."""
    c, k = _by_key(key)
    if c.kind == "web" and not _origin_ok(_settings(c), origin, own_page):
        raise WebError("This website is not allowed to use this form.", 403)
    _limit("form", ip or "?")
    if str(body.get("website") or "").strip():
        return {"ok": True}                    # a bot: answered like a person, nothing kept
    S = _S()
    msg = S._clean(body.get("message"), 3000)
    if not msg:
        raise WebError("Write your message.")
    email = str(body.get("email") or "").strip()[:160]
    phone = S._digits(body.get("phone"))
    if not email and len(phone) < 8:
        raise WebError("Give an email address or a phone number so we can answer.")
    cust = ("email:" + email.lower()) if email else ("phone:" + phone)
    t = S.new_ticket(c.tenant_id, msg, "web", cust, S._clean(body.get("name"), 80), by="form")
    return {"ok": True, "number": t["number"], "say": f"Thank you. Your request number is {t['number']}."}


# ---------------------------------------------------------------- her app's own API
def _api_key(c, k: dict, auth: str) -> None:
    got = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not got or not hmac.compare_digest(got, k.get("api_key", "")):
        raise WebError("Wrong API key.", 401)


def _api_row(auth: str):
    """The API key alone names her app (keys are unique)."""
    CH = _CH()
    CH._ensure()
    got = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not got.startswith("hsk_"):
        raise WebError("Wrong API key.", 401)
    with session() as s:
        rows = s.scalars(select(CH.SevaChannel).where(CH.SevaChannel.kind == "api", CH.SevaChannel.status != "off")).all()
        for r in rows:
            k = CH._open(r.sealed)
            if hmac.compare_digest(k.get("api_key", ""), got):
                s.expunge(r)
                return r, k
    raise WebError("Wrong API key.", 401)


def api_send(auth: str, body: dict) -> dict:
    CH = _CH()
    c, k = _api_row(auth)
    _limit("key", c.id)
    S = _S()
    uid = re.sub(r"[^A-Za-z0-9_.@:-]", "", str(body.get("user_id") or ""))[:120]
    if not uid:
        raise WebError("user_id is needed (your user's id in your app).")
    text = S._clean(body.get("text"), 2000)
    if not text:
        raise WebError("text is needed.")
    customer = "user:" + uid
    _limit("visitor", customer)
    before = messages(c.tenant_id, customer)["messages"]
    CH.handle(c.tenant_id, c.id, [{"from": uid, "customer": customer, "name": S._clean(body.get("name"), 80), "text": text,
                                   "ext_id": str(body.get("message_id") or new_id("am"))[:120], "meta": {}}])
    after = messages(c.tenant_id, customer)["messages"]
    new = after[len(before):]
    return {"user_id": uid, "replies": [m for m in new if m["from"] != "you"], "messages": after[-30:]}


def api_messages(auth: str, user_id: str, after: str = "") -> dict:
    c, k = _api_row(auth)
    _limit("key", c.id)
    uid = re.sub(r"[^A-Za-z0-9_.@:-]", "", str(user_id))[:120]
    return messages(c.tenant_id, "user:" + uid, after)


def to_webhook(c, k: dict, to: str, text: str) -> bool:
    """A later message for one of her app's users (a person replied, a ticket moved): POST to HER webhook, signed."""
    st = _settings(c)
    url = st.get("webhook_url") or ""
    if not url:
        return True                            # her app reads it with GET /api/support/v1/messages
    body = json.dumps({"user_id": to, "text": text, "at": datetime.now(timezone.utc).isoformat()}).encode()
    sig = hmac.new(k.get("webhook_secret", "").encode(), body, hashlib.sha256).hexdigest()
    try:
        st_, _ = _CH()._http("POST", url, headers={"Content-Type": "application/json", "X-Hoola-Signature": "sha256=" + sig},
                             content=body)
    except Exception:   # noqa: BLE001
        log.exception("support webhook")
        return False
    return 200 <= st_ < 300
