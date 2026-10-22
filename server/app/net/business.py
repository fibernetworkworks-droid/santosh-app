"""v0.33 business avatars: a business's Hoola is a public counter any customer's avatar can reach (no personal
connection needed; the business chose to be public). Complaints become numbered tickets (optionally sent on to the
business's own system such as FNW Flow, by a signed webhook), quotes come from the business's own price list,
orders wait for the owner's tap, and tickets can be passed along a chain to a technician's avatar. A verified-business
badge is given only by the server operator after checking documents."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import identity as idn
from . import policy
from .models import HoolaId, Link
from .service import EXTRA_KINDS, NetError, _link, _post, tell

CATEGORIES = ("isp", "shop", "pharmacy", "clinic", "services", "restaurant", "education", "other")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$")


class Business(Base):
    __tablename__ = "hoola_businesses"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(20), default="other")
    area: Mapped[str] = mapped_column(String(160), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    hours: Mapped[str] = mapped_column(String(200), default="")
    catalog: Mapped[list] = mapped_column(JSON, default=list)               # [{item, price, unit}]
    public: Mapped[bool] = mapped_column(Boolean, default=True)
    ticket_prefix: Mapped[str] = mapped_column(String(8), default="T")
    next_ticket: Mapped[int] = mapped_column(Integer, default=1001)
    webhook_url: Mapped[str] = mapped_column(Text, default="")
    webhook_secret: Mapped[str] = mapped_column(Text, default="")          # encrypted
    team: Mapped[list] = mapped_column(JSON, default=list)                  # addresses a ticket can go to (chain)
    auto_assign: Mapped[bool] = mapped_column(Boolean, default=False)
    gstin: Mapped[str] = mapped_column(String(20), default="")
    verification: Mapped[str] = mapped_column(String(12), default="none")  # none | requested | verified | rejected
    udyam: Mapped[str] = mapped_column(String(24), default="")             # v0.112 optional Udyam registration
    verified_upi: Mapped[str] = mapped_column(String(80), default="")      # v0.112 UPI ID the operator matched to the bank name
    credential: Mapped[dict] = mapped_column(JSON, default=dict)           # v0.112 server-signed verified-business credential
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=now)


class Ticket(Base):
    __tablename__ = "hoola_tickets"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_hoola_ticket"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tkt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)          # the business
    number: Mapped[str] = mapped_column(String(30))
    customer: Mapped[str] = mapped_column(String(200))
    customer_label: Mapped[str] = mapped_column(String(160), default="")
    thread: Mapped[str] = mapped_column(String(60), default="")
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(12), default="open")         # open | assigned | in_progress | resolved | closed
    note: Mapped[str] = mapped_column(Text, default="")
    chain_id: Mapped[str] = mapped_column(String(60), default="")
    webhook_status: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=now)


class CustomerTicket(Base):
    """Customer side: the tickets this owner's avatar raised with businesses."""
    __tablename__ = "hoola_my_tickets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("myt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    business: Mapped[str] = mapped_column(String(200))
    number: Mapped[str] = mapped_column(String(30), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=now)


BIZ_KINDS = {"biz_complaint", "biz_ticket", "biz_update"}


# ---------------------------------------------------------------- business profile
def _biz(tenant: str) -> Business | None:
    with session() as s:
        b = s.get(Business, tenant)
        if b is not None:
            s.expunge(b)
        return b


def profile(tenant: str) -> dict[str, Any] | None:
    b = _biz(tenant)
    if b is None:
        return None
    cat = b.catalog
    try:                                              # v0.105 once she keeps a stock list, that IS the price list
        from . import deal as dl
        st = dl.stock(tenant)
        if st:
            cat = [{"item": x["name"], "price": x["price"], "unit": x["unit"], "free": x["free"]} for x in st if x["public"]]
    except Exception:
        pass
    return {"name": b.name, "category": b.category, "area": b.area, "about": b.about, "hours": b.hours, "catalog": cat,
            "catalog_raw": b.catalog,
            "public": b.public, "ticket_prefix": b.ticket_prefix, "webhook": bool(b.webhook_url),
            "team": [{"address": a, "label": idn.label(idn.peer_card(a))} for a in b.team or []], "auto_assign": b.auto_assign,
            "verification": b.verification, "gstin": b.gstin[:2] + "•••" + b.gstin[-3:] if b.gstin else "",
            "handle": idn.ensure(tenant).handle}


def setup(tenant: str, **kw) -> dict[str, Any]:
    name = str(kw.get("name") or "").strip()[:120]
    with session() as s:
        b = s.get(Business, tenant)
        if b is None:
            if not name:
                raise NetError("Business ka naam bataiye.")
            b = Business(tenant_id=tenant, name=name)
            s.add(b)
        if name:
            b.name = name
        if kw.get("category") in CATEGORIES:
            b.category = kw["category"]
        for k, n in (("area", 160), ("about", 3000), ("hours", 200)):
            if isinstance(kw.get(k), str):
                b_val = kw[k].strip()[:n]
                if policy.secret_found(b_val):
                    raise NetError("Isme mana ki gayi jaankari hai.")
                setattr(b, k, b_val)
        if isinstance(kw.get("catalog"), list):
            items = []
            for it in kw["catalog"][:200]:
                if isinstance(it, dict) and str(it.get("item") or "").strip():
                    try:
                        price = round(float(it.get("price")), 2)
                    except (TypeError, ValueError):
                        price = None
                    items.append({"item": str(it["item"]).strip()[:120], "price": price, "unit": str(it.get("unit") or "")[:30]})
            b.catalog = items
        if isinstance(kw.get("public"), bool):
            b.public = kw["public"]
        if isinstance(kw.get("ticket_prefix"), str) and re.fullmatch(r"[A-Z]{1,6}", kw["ticket_prefix"].upper()):
            b.ticket_prefix = kw["ticket_prefix"].upper()
        if isinstance(kw.get("webhook_url"), str):
            url = kw["webhook_url"].strip()
            if url and not url.startswith("https://"):
                raise NetError("Webhook https:// se shuru hona chahiye.")
            if url:
                from ..bazar.custom_mcp import UrlError, check_url
                try:
                    check_url(url)
                except UrlError as e:
                    raise NetError(str(e))
            b.webhook_url = url
        if isinstance(kw.get("webhook_secret"), str) and kw["webhook_secret"]:
            b.webhook_secret = idn._fernet().encrypt(kw["webhook_secret"].encode()).decode()
        if isinstance(kw.get("auto_assign"), bool):
            b.auto_assign = kw["auto_assign"]
    with session() as s:
        h = s.get(HoolaId, tenant)
        if h is not None:
            h.business = True
    if isinstance(kw.get("catalog"), list):          # v0.105 the price list lives in the stock list too (one source)
        from . import deal as dl
        dl.sync_catalog(tenant, list((profile(tenant) or {}).get("catalog_raw") or []))
    if kw.get("team") is not None:
        set_team(tenant, list(kw["team"]))
    return profile(tenant) or {}


def set_team(tenant: str, who: list[str]) -> list[str]:
    from .service import resolve
    addrs = []
    for w in who[:30]:
        a = resolve(tenant, str(w))
        l = _link(tenant, a)
        if l is None or l.status != "active":
            raise NetError(f"{w} aapse juda nahi hai (team ke liye judna zaroori).")
        addrs.append(a)
    with session() as s:
        s.get(Business, tenant).team = addrs
    return addrs


def request_verification(tenant: str, gstin: str, udyam: str = "") -> dict[str, Any]:
    g = (gstin or "").strip().upper()
    if not GSTIN_RE.match(g):
        raise NetError("GSTIN sahi nahi lagta (15 akshar, jaise 27ABCDE1234F1Z5).")
    u = (udyam or "").strip().upper()
    from .trust import UDYAM_RE
    if u and not UDYAM_RE.match(u):
        raise NetError("Udyam number aisa hota hai: UDYAM-MH-01-0000000")
    with session() as s:
        b = s.get(Business, tenant)
        if b is None:
            raise NetError("Pehle business profile banaiye.")
        b.gstin, b.verification, b.udyam = g, "requested", u
    return {"status": "requested", "note": "Server chalane wale documents (GSTIN, Udyam, bank mein naam) dekh kar verified "
            "badge denge."}


def operator_verify(tenant: str, approve: bool, bank_name_ok: bool = False) -> dict[str, Any]:
    """Only the server owner (operator) calls this, after checking the documents. `bank_name_ok` = she checked that the
    business's UPI ID (Khareed aur bikri > Niyam) belongs to a bank account in the business's name: only then the
    credential names that UPI ID, and buyers' Hoolas show the payee as verified (v0.112)."""
    upi = ""
    if approve and bank_name_ok:
        from .deal import rules as deal_rules
        upi = deal_rules(tenant).upi_id or ""
        if not upi:
            raise NetError("Is business ka UPI ID abhi nahi hai; bank naam milane ke liye pehle UPI ID chahiye.")
    with session() as s:
        b = s.get(Business, tenant)
        if b is None:
            raise NetError("Business nahi mila.")
        b.verification = "verified" if approve else "rejected"
        b.verified_upi = upi if approve else ""
        if not approve:
            b.credential = {}
        h = s.get(HoolaId, tenant)
        if h is not None:
            h.business, h.business_verified = True, bool(approve)
    if approve:
        from . import trust
        trust.issue(tenant)
    if approve:
        tell(tenant, "hoola_msg", {"kind": "biz_verified", "fyi": True, "from": "Hoola", "text": "Aapka business verified ho gaya 🏢✓"})
    return {"status": "verified" if approve else "rejected"}


def verification_queue() -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(Business).where(Business.verification == "requested")).all()
        out = [{"tenant": b.tenant_id, "name": b.name, "gstin": b.gstin, "area": b.area, "category": b.category,
                "udyam": b.udyam or ""} for b in rows]
    from .deal import rules as deal_rules
    for x in out:                                # v0.112 the UPI ID to match against the bank account name
        x["upi_id"] = deal_rules(x["tenant"]).upi_id or ""
        x["payee_name"] = deal_rules(x["tenant"]).payee_name or ""
    return out


def directory(tenant: str, q: str = "", category: str = "") -> list[dict[str, Any]]:
    w = (q or "").lower().strip()
    out = []
    with session() as s:
        for b in s.scalars(select(Business).where(Business.public.is_(True))).all():
            if b.tenant_id == tenant:
                continue
            if category and b.category != category:
                continue
            if w and w not in f"{b.name} {b.area} {b.about} {b.category}".lower():
                continue
            h = s.get(HoolaId, b.tenant_id)
            if h is None:
                continue
            out.append({"address": idn.address(h.uid), "handle": h.handle, "name": b.name, "category": b.category,
                        "area": b.area, "hours": b.hours, "verified": b.verification == "verified"})
    return sorted(out, key=lambda x: (not x["verified"], x["name"]))[:50]


# ---------------------------------------------------------------- customer side
def contact(tenant: str, business: str) -> str:
    """Opens the counter: both sides get an active 'business' link (the business chose to be public)."""
    from .service import resolve
    addr = resolve(tenant, business)
    btenant = idn.tenant_of(addr)
    b = _biz(btenant) if btenant else None
    if btenant and (b is None or not b.public):
        raise NetError("Yeh Hoola business nahi hai (ya abhi public nahi).")
    me = idn.my_card(tenant)["address"]
    if addr == me:
        raise NetError("Yeh aapka apna business hai.")
    with session() as s:
        mine = s.scalars(select(Link).where(Link.tenant_id == tenant, Link.peer == addr)).first()
        if mine is not None and mine.status == "blocked":
            raise NetError("Aapne is business ko block kiya hai.")
        if mine is None:
            s.add(Link(tenant_id=tenant, peer=addr, status="active", relation="business", via="business"))
        elif mine.status != "active":
            mine.status, mine.relation = "active", "business"
        if btenant:
            theirs = s.scalars(select(Link).where(Link.tenant_id == btenant, Link.peer == me)).first()
            if theirs is not None and theirs.status in ("blocked", "declined"):
                raise NetError("Yeh business abhi aapse baat nahi le raha.")
            if theirs is None:
                s.add(Link(tenant_id=btenant, peer=me, status="active", relation="business", via="customer"))
            elif theirs.status in ("requested", "incoming"):
                theirs.status = "active"         # a pending personal request becomes a customer connection
    return addr


def complain(tenant: str, business: str, text: str, category: str = "") -> dict[str, Any]:
    text = (text or "").strip()
    if len(text) < 5:
        raise NetError("Shikayat kya hai? Thoda bataiye.")
    if policy.secret_found(text):
        raise NetError("Shikayat mein PIN / OTP / password jaisi cheez mat daaliye.")
    addr = contact(tenant, business)
    with session() as s:
        mt = CustomerTicket(tenant_id=tenant, business=addr, text=text[:3000])
        s.add(mt)
        s.flush()
        mid = mt.id
    r = _post(tenant, addr, "biz_complaint", {"text": text[:3000], "category": category[:40], "ref": mid}, new_id("tk"))
    if not r.get("ok"):
        raise NetError(r.get("reason") or "Shikayat nahi pahunchi.")
    with session() as s:
        mt = s.get(CustomerTicket, mid)
        mt.number = str(r.get("ticket") or "")
    return {"status": "registered", "ticket": r.get("ticket"), "eta": r.get("eta", ""),
            "business": idn.label(idn.peer_card(addr))}


def my_tickets(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(CustomerTicket).where(CustomerTicket.tenant_id == tenant)
                         .order_by(CustomerTicket.updated_at.desc()).limit(50)).all()
        return [{"id": t.id, "business": idn.label(idn.peer_card(t.business)), "number": t.number, "text": t.text,
                 "status": t.status, "note": t.note, "updated": t.updated_at.isoformat()} for t in rows]


# ---------------------------------------------------------------- business side
def _webhook(b: Business, payload: dict[str, Any]) -> str:
    if not b.webhook_url:
        return ""
    import httpx
    from ..bazar.custom_mcp import UrlError, check_url
    try:
        check_url(b.webhook_url)                 # re-checked every time (the name could now point inside)
    except UrlError:
        return "blocked"
    body = json.dumps(payload, ensure_ascii=False).encode()
    secret = idn._fernet().decrypt(b.webhook_secret.encode()).decode() if b.webhook_secret else ""
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest() if secret else ""
    try:
        r = httpx.post(b.webhook_url, content=body, timeout=10, follow_redirects=False,
                       headers={"Content-Type": "application/json", "X-Hoola-Event": payload.get("event", "ticket"),
                                "X-Hoola-Signature": f"sha256={sig}"})
        return f"{r.status_code}"
    except Exception as e:
        return f"failed: {type(e).__name__}"


def tickets(tenant: str, status: str = "") -> list[dict[str, Any]]:
    with session() as s:
        q = select(Ticket).where(Ticket.tenant_id == tenant)
        if status:
            q = q.where(Ticket.status == status)
        rows = s.scalars(q.order_by(Ticket.updated_at.desc()).limit(100)).all()
        return [ticket_view(t) for t in rows]


def ticket_view(t: Ticket) -> dict[str, Any]:
    return {"id": t.id, "number": t.number, "customer": t.customer_label, "text": t.text, "category": t.category,
            "status": t.status, "note": t.note, "chain_id": t.chain_id, "webhook": t.webhook_status,
            "created": t.created_at.isoformat(), "updated": t.updated_at.isoformat()}


def update_ticket(tenant: str, number: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "assigned", "in_progress", "resolved", "closed"):
        raise NetError("status: open, assigned, in_progress, resolved, closed")
    if policy.secret_found(note):
        raise NetError("Note mein mana ki gayi jaankari hai.")
    with session() as s:
        t = s.scalars(select(Ticket).where(Ticket.tenant_id == tenant, (Ticket.number == number) | (Ticket.id == number))).first()
        if t is None:
            raise NetError("Yeh ticket nahi mila.")
        t.status, t.note, t.updated_at = status, note[:1000] or t.note, now()
        s.flush()
        s.expunge(t)
    b = _biz(tenant)
    if b is not None:
        _webhook(b, {"event": "ticket.updated", "ticket": t.number, "status": status, "note": note[:1000]})
    if t.customer.startswith("wa:"):           # a WhatsApp customer (Hoola Employee inbox): tell them there
        from ..employee import inbox as biz_inbox
        words = {"assigned": "kisi ko di gayi", "in_progress": "par kaam chal raha hai", "resolved": "theek ho gayi",
                 "closed": "band ki gayi", "open": "khuli hai"}.get(status, status)
        biz_inbox.notice_by_phone(tenant, t.customer[3:], f"Aapki shikayat {t.number} {words}." + (f" {note[:300]}" if note else ""))
        return ticket_view(t)
    _post(tenant, t.customer, "biz_update", {"ticket": t.number, "status": status, "note": note[:1000]}, t.thread or new_id("tk"))
    return ticket_view(t)


def assign(tenant: str, number: str, to: str, note: str = "") -> dict[str, Any]:
    from . import chain
    with session() as s:
        t = s.scalars(select(Ticket).where(Ticket.tenant_id == tenant, (Ticket.number == number) | (Ticket.id == number))).first()
        if t is None:
            raise NetError("Yeh ticket nahi mila.")
        s.expunge(t)
    c = chain.start(tenant, to, f"Ticket {t.number}: {t.text[:500]}", note or "Customer ki shikayat dekhiye", 72, t.number)
    with session() as s:
        row = s.get(Ticket, t.id)
        row.chain_id, row.status, row.updated_at = c["chain_id"], "assigned", now()
    update_ticket(tenant, t.number, "assigned", note or f"{c['holder'] or 'Technician'} ko diya gaya")
    return {"status": "assigned", "chain_id": c["chain_id"]}


def chain_done(tenant: str, ref: str, note: str, who: str) -> None:
    """A ticket's chain finished: mark it resolved and tell the customer."""
    try:
        update_ticket(tenant, ref, "resolved", note or f"{who} ne kaam poora kiya")
    except NetError:
        pass


def webhook_in(tenant: str, body: bytes, signature: str) -> dict[str, Any]:
    """The business's own system (e.g. FNW Flow) updates a ticket: POST signed with the shared secret."""
    b = _biz(tenant)
    if b is None or not b.webhook_secret:
        raise NetError("not configured")
    secret = idn._fernet().decrypt(b.webhook_secret.encode()).decode()
    want = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, signature or ""):
        raise NetError("bad signature")
    data = json.loads(body.decode() or "{}")
    import time
    ts = data.get("ts")
    if not isinstance(ts, (int, float)) or abs(time.time() - float(ts)) > 300:
        raise NetError("ts (unix seconds) chahiye, 5 minute ke andar")
    nonce = str(data.get("nonce") or "")
    if not 8 <= len(nonce) <= 80:
        raise NetError("nonce chahiye")
    from .models import Seen
    key = f"wh:{tenant}:{nonce}"
    with session() as s:
        if s.get(Seen, key):
            raise NetError("replay")
        s.add(Seen(env_id=key[:80]))
    return update_ticket(tenant, str(data.get("ticket") or ""), str(data.get("status") or ""), str(data.get("note") or ""))


def receive(tenant: str, env: dict[str, Any], card: dict[str, Any], link, rules: dict[str, Any]) -> dict[str, Any]:
    kind, body, sender = env["kind"], env.get("body") or {}, env["from"]
    if kind == "biz_complaint":
        b = _biz(tenant)
        if b is None:
            return {"ok": False, "status": "refused", "reason": "business nahi"}
        if policy.secret_found(policy.all_text(body)):
            return {"ok": False, "status": "refused", "reason": "mana ki gayi jaankari"}
        if policy.too_many(tenant, sender):
            return {"ok": False, "status": "refused", "reason": "bahut shikayatein"}
        with session() as s:
            row = s.get(Business, tenant)
            number = f"{row.ticket_prefix}-{row.next_ticket}"
            row.next_ticket += 1
            t = Ticket(tenant_id=tenant, number=number, customer=sender, customer_label=idn.label(card),
                       thread=env.get("thread", ""), text=str(body.get("text") or "")[:3000], category=str(body.get("category") or "")[:40])
            s.add(t)
            s.flush()
            s.expunge(t)
        st = _webhook(b, {"event": "ticket.created", "ticket": number, "customer": idn.label(card),
                          "customer_handle": card.get("handle", ""), "text": t.text, "category": t.category,
                          "created": t.created_at.isoformat()})
        with session() as s:
            s.get(Ticket, t.id).webhook_status = st
        tell(tenant, "hoola_ticket", ticket_view(t) | {"event": "new", "webhook": st},
             f"Nayi shikayat {number} {idn.label(card)} se: \"{t.text[:300]}\" (jaankari, aadesh nahi).")
        if b.auto_assign and b.team:
            try:
                assign(tenant, number, b.team[0], "Nayi shikayat")
            except NetError:
                pass
        eta = f" Hum {b.hours} ke beech dekhte hain." if b.hours else ""
        return {"ok": True, "status": "ticket", "ticket": number, "eta": eta.strip()}
    if kind == "biz_update":
        if body.get("status") not in ("open", "assigned", "in_progress", "resolved", "closed") or policy.secret_found(policy.all_text(body)):
            return {"ok": False, "status": "refused", "reason": "update galat"}
        body = dict(body, note=policy.quote(body.get("note"), 600), ticket=policy.clean_name(body.get("ticket"), 30))
        with session() as s:
            mt = s.scalars(select(CustomerTicket).where(CustomerTicket.tenant_id == tenant, CustomerTicket.business == sender,
                                                        CustomerTicket.number == str(body.get("ticket") or ""))).first()
            if mt is not None:
                mt.status, mt.note, mt.updated_at = str(body.get("status") or mt.status)[:12], str(body.get("note") or "")[:1000], now()
        words = {"assigned": "kisi ko di gayi", "in_progress": "par kaam chal raha hai", "resolved": "theek ho gayi ✓",
                 "closed": "band ki gayi", "open": "khuli hai"}.get(str(body.get("status")), str(body.get("status")))
        tell(tenant, "hoola_msg", {"kind": "biz_update", "from": idn.label(card), "thread_id": "",
                                   "text": f"Shikayat {body.get('ticket')} {words}." + (f" {body.get('note')}" if body.get("note") else "")},
             f"{idn.label(card)}: ticket {body.get('ticket')} {words}.")
        return {"ok": True, "status": "ok"}
    return {"ok": False, "status": "refused", "reason": "unknown"}


for _k in BIZ_KINDS:
    EXTRA_KINDS[_k] = receive
_ = (Text,)
