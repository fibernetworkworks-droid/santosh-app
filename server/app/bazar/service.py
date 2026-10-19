"""Bazar service: connects the 159 MVP packs to Santosh core (tenants, conversations, live events, worker).

Every Santosh tenant (signed-in user) is a Bazar user with the same id. Money and messages to other people never move
without a confirm card the user taps in the app; the card shows amounts and payees computed by server code.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import logging
import re
import secrets
from typing import Any

from sqlalchemy import select

from ..config import get_settings as core_settings
from ..db import Conversation as CoreConversation
from ..db import Profile as CoreProfile
from ..db import session
from ..events import bus, notify
from .agent.runner import PausedForApproval, Runner
from .agent.toolbox import default_executors
from .config import get_settings
from .connectors.base import Ctx, ToolError, rupees, to_paise
from .connectors.upi import valid_vpa
from .db import (Approval, Connection, Contact, InstalledPack, Reminder, Shop, ShopDue, ShopItem, ShopOrder, Task,
                 Transaction, User)
from . import custom_mcp, directory
from .db import CustomMcp
from .packs.registry import Pack, Registry, registry

log = logging.getLogger("santosh.bazar")

# Native packs whose job Santosh core already does (and does better: real alarms, Google Calendar, routines).
CORE_EQUIVALENT = {
    "reminders": "create_reminder, list_reminders, cancel_reminder, set_phone_alarm",
    "calendar": "calendar_add_event / calendar_agenda (Google Calendar) or add_calendar_event (phone)",
    "notes": "remember, forget",
    "lists": "list_add, list_show, list_done",
    "briefing": "set_profile(briefing_time) for the daily briefing, or create_routine",
    "wa_marketing": "check_template, submit_template, create_campaign (WhatsApp campaigns)",
}

STATUS_TEXT = {
    "ready": "ready",
    "demo": "demo mode: test bills only until the BBPS partner is live",
    "no_shop_yet": "no shop of this kind has joined Santosh Bazar yet",
    "needs_link": "user must link this account once (Connect tab)",
    "not_configured": "provider access not configured on the server yet",
    "core": "built into Santosh",
    "pc_offline": "the PC is offline: switch it on and open Santosh Desktop",
    "pc_not_paired": "no PC paired yet: Santosh app > Main > Mera PC",
    "needs_key": "add this server's API key once in the Santosh app (Connect > MCP servers); never in chat",
}

_executors = None


def executors():
    global _executors
    if _executors is None:
        _executors = default_executors()
    return _executors


def set_executors(ex) -> None:  # tests
    global _executors
    _executors = ex


# ---------------------------------------------------------------- users / tasks
def ensure_user(s, tenant_id: str) -> User:
    st = get_settings()
    u = s.get(User, tenant_id)
    prof = s.get(CoreProfile, tenant_id)
    if u is None:
        u = User(id=tenant_id, language="hi", cap_per_order_paise=st.default_cap_per_order_paise,
                 cap_per_day_paise=st.default_cap_per_day_paise, profile={})
        s.add(u)
    if prof is not None:
        if prof.name and not u.name:
            u.name = prof.name
        if prof.city and not u.city:
            u.city = prof.city
        if prof.lat is not None and prof.lon is not None and not (u.profile or {}).get("home_location"):
            u.profile = {**(u.profile or {}), "home_location": {"lat": prof.lat, "lng": prof.lon, "name": prof.city or "Home"}}
    s.flush()
    return u


def _task(s, user: User, conversation_id: str) -> Task:
    """One Bazar task per conversation (within 6 h), so a cart built earlier can be ordered later."""
    since = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(hours=6)
    t = s.scalars(select(Task).where(Task.user_id == user.id, Task.conversation_id == conversation_id, Task.created_at >= since)
                  .order_by(Task.created_at.desc())).first()
    if t is None:
        t = Task(user_id=user.id, conversation_id=conversation_id, text="santosh", engine="claude", status="running", result={})
        s.add(t)
        s.flush()
    return t


def _ctx(s, user: User, task: Task | None) -> Ctx:
    return Ctx(s, user, task, get_settings())


# ---------------------------------------------------------------- catalogue
def pack_status(s, user: User, pack: Pack) -> str:
    st = get_settings()
    if pack.executor == "native" and pack.config.get("skill") in CORE_EQUIVALENT:
        return "core"
    if pack.executor == "bbps":
        return "ready" if st.bills_live else "demo"
    if pack.executor == "shop":
        n = s.scalars(select(Shop.id).where(Shop.template_id == pack.config["template"], Shop.active.is_(True))).first()
        return "ready" if n else "no_shop_yet"
    if pack.executor == "pc":
        from ..pc.hub import hub
        if hub.is_online(user.id):
            return "ready"
        from ..db import PcDevice
        paired = s.scalars(select(PcDevice.id).where(PcDevice.tenant_id == user.id, PcDevice.revoked.is_(False))).first()
        return "pc_offline" if paired else "pc_not_paired"
    if pack.executor == "mcp" and pack.config.get("custom"):
        try:
            h = custom_mcp.headers_for(s, pack, user.id)
        except Exception:
            h = None
        if h is not None:
            return "ready"
        return "needs_key" if pack.config.get("auth") == "key" else "needs_link"
    if pack.executor == "mcp":
        if not getattr(st, pack.config["endpoint_setting"], ""):
            return "not_configured"
        c = s.scalars(select(Connection).where(Connection.user_id == user.id, Connection.provider == pack.config["provider"],
                                               Connection.status == "active")).first()
        return "ready" if c else "needs_link"
    return "ready"


def _spec_out(sp) -> dict[str, Any]:
    note = {2: " [needs the user's tap on a confirm card]", 3: " [needs a confirm tap + the user's UPI PIN]"}.get(sp.tier, "")
    return {"tool": sp.name, "description": sp.description + note, "tier": sp.tier,
            "input_schema": sp.input_schema or {"type": "object", "properties": {}}}


def _pack_out(s, user: User, p: Pack, with_tools: bool) -> dict[str, Any]:
    status = pack_status(s, user, p)
    out: dict[str, Any] = {"pack_id": p.id, "name": p.name, "category": p.category, "kind": p.sub_category,
                           "does": p.description, "status": status, "status_note": STATUS_TEXT[status]}
    if status == "core":
        out["use_core_tools"] = CORE_EQUIVALENT[p.config["skill"]]
        return out
    if p.executor == "upi" and not p.config.get("package_verified"):
        out["note"] = "App package not verified on a phone yet; the generic UPI chooser opens if it is missing."
    if p.executor == "ride" and not p.config.get("verified"):
        out["note"] = "Opens the app; pickup/drop may need to be set in the app."
    if with_tools and status in ("ready", "demo"):
        try:
            specs = executors()[p.executor].tool_specs(p, _ctx(s, user, None))
            out["tools"] = [_spec_out(sp) for sp in specs]
        except ToolError as e:
            out["status"], out["status_note"] = "unavailable", str(e).replace("NOT_LINKED: ", "")
        except Exception as e:  # provider down
            out["status"], out["status_note"] = "unavailable", f"{p.name} is not responding right now ({type(e).__name__})"
    return out


def _fallback_match(text: str, limit: int) -> list[Pack]:
    words = [w for w in re.findall(r"[\wऀ-ॿ]+", text.lower()) if len(w) > 2]
    scored = []
    for p in registry().packs.values():
        hay = f"{p.name} {p.category} {p.sub_category} {p.description} {' '.join(p.keywords)}".lower()
        sc = sum(1 for w in words if w in hay)
        if sc:
            scored.append((sc, p))
    scored.sort(key=lambda x: (-x[0], x[1].priority, x[1].name))
    return [p for _, p in scored[:limit]]


def find(tenant_id: str, query: str = "", category: str = "", limit: int = 6) -> dict[str, Any]:
    reg = registry()
    limit = max(1, min(int(limit or 6), 12))
    with session() as s:
        user = ensure_user(s, tenant_id)
        if category and not query:
            packs = [p for p in reg.all(phase="MVP") if category.lower() in p.category.lower()][:40]
            return {"packs": [_pack_out(s, user, p, with_tools=False) for p in packs],
                    "hint": "Call bazar_find again with a specific query to get the tools of a pack."}
        if not query:
            cats: dict[str, int] = {}
            for p in reg.all(phase="MVP"):
                cats[p.category] = cats.get(p.category, 0) + 1
            return {"total_packs": len(reg.packs), "categories": cats,
                    "hint": "Ask with a query like 'bijli bill', 'kirana', 'phonepe', 'uber', 'swiggy'."}
        mine = [custom_mcp.to_pack(r) for r in custom_mcp.user_rows(s, user.id)]
        if mine:
            wants_mine = bool(re.search(r"\b(mcp|my servers?|mere server)\b", query.lower()))
            mine_hits = [p for p, _ in Registry(mine).match(query, limit=limit)] if not wants_mine else mine[:limit]
            if not mine_hits:
                mine_hits = [p for p in mine if any(w in f"{p.name} {p.description}".lower()
                                                    for w in re.findall(r"[a-z0-9]{4,}", query.lower()))][:3]
        else:
            mine_hits = []
        hits = mine_hits + [p for p, _ in reg.match(query, limit=limit)]
        if len(hits) < 2:
            for p in _fallback_match(query, limit):
                if p not in hits:
                    hits.append(p)
        hits = hits[:limit]
        out = [_pack_out(s, user, p, with_tools=i < 4) for i, p in enumerate(hits)]
        res: dict[str, Any] = {"packs": out}
        if len(out) < 3 or re.search(r"\bmcp\b", query.lower()):
            dir_hits = directory.search(query, limit=5)
            if dir_hits:
                res["mcp_directory"] = dir_hits
                res["directory_hint"] = ("These MCP servers exist but are not connected yet. To use one, the user gives its "
                                         "https MCP address (or you call bazar_mcp action=add with url and ref); local "
                                         "servers must run on a computer first. Never guess an address.")
        if not out and not res.get("mcp_directory"):
            res["message"] = "No Santosh connector does this yet."
        return res


# ---------------------------------------------------------------- running tools
def _open_action(out: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(out, dict):
        return None
    if out.get("intent_url"):
        return {"kind": "upi", "url": out["intent_url"], "package": out.get("android_package") or "",
                "label": "UPI app kholiye"}
    if out.get("deep_link") or out.get("android_package"):
        return {"kind": "app", "url": out.get("deep_link") or "", "package": out.get("android_package") or "",
                "label": f"{out.get('app', 'App')} kholiye"}
    if out.get("share_links"):
        return {"kind": "links", "links": out["share_links"], "label": "WhatsApp par bhejiye"}
    if out.get("payment_link"):
        return {"kind": "share", "text": out.get("share_text") or out["payment_link"], "label": "Link share kijiye"}
    return None


def card_of(ap: Approval, pack: Pack | None) -> dict[str, Any]:
    items = []
    for it in ap.items or []:
        price = it.get("price_paise")
        items.append({"name": it.get("name", ""), "price": rupees(price) if isinstance(price, int) else ""})
    return {"id": ap.id, "title": ap.title, "payee": ap.payee, "amount": rupees(ap.amount_paise) if ap.amount_paise else "",
            "amount_paise": ap.amount_paise, "items": items, "pay_method": ap.pay_method, "tier": ap.tier,
            "pack": pack.name if pack else "", "demo": ap.title.startswith("[DEMO]"), "status": ap.decision,
            "needs_pin": ap.tier >= 3 or "UPI" in (ap.pay_method or "")}


def run(tenant_id: str, conversation_id: str, pack_id: str, tool: str, args: dict[str, Any] | None) -> dict[str, Any]:
    events: list[tuple[str, dict[str, Any]]] = []
    try:
        return _run(tenant_id, conversation_id, pack_id, tool, args, events)
    finally:
        for kind, payload in events:  # publish after the DB transaction closed (SQLite allows one writer)
            try:
                bus.publish(conversation_id, kind, payload)
            except Exception:
                log.exception("bazar event publish failed")


def _run(tenant_id: str, conversation_id: str, pack_id: str, tool: str, args: dict[str, Any] | None,
         events: list) -> dict[str, Any]:
    reg = registry()
    pack = reg.lookup(pack_id)
    if pack is None or (pack.config.get("custom") and pack.config.get("owner") != tenant_id):
        raise ToolError(f"Unknown pack '{pack_id}'. Use bazar_find first.")
    args = args if isinstance(args, dict) else {}
    if pack.executor == "pc" and tool in {t.name for t in pack.tools} and pack.tier_of(tool) < 2:
        return _run_pc_read(tenant_id, pack, tool, args, events)
    with session() as s:
        user = ensure_user(s, tenant_id)
        status = pack_status(s, user, pack)
        if status == "core":
            raise ToolError(f"Use Santosh's own tools for this: {CORE_EQUIVALENT[pack.config['skill']]}.")
        if status == "not_configured":
            raise ToolError(f"{pack.name}: {STATUS_TEXT[status]}.")
        if pack.executor != "mcp" and tool not in {t.name for t in pack.tools}:
            raise ToolError(f"{pack.name} has no tool '{tool}'. Its tools: {', '.join(t.name for t in pack.tools)}")
        task = _task(s, user, conversation_id)
        runner = Runner(s, get_settings(), reg, executors())
        try:
            out = runner.call_tool(_ctx(s, user, task), pack, tool, args)
        except PausedForApproval as p:
            ap = p.approval
            ap.conversation_id = conversation_id
            card = card_of(ap, pack)
            s.flush()
            events.append(("bazar_approval", card))
            return {"needs_approval": True, "approval_id": ap.id, "card": {k: card[k] for k in ("title", "payee", "amount", "items")},
                    "say": "A confirm card is on the user's screen. Tell them the total and to tap Approve (or Cancel). "
                           "Nothing is ordered or paid until they tap."}
        except ToolError as e:
            msg = str(e)
            if msg.startswith("PC_OFFLINE: "):
                raise ToolError(msg.removeprefix("PC_OFFLINE: "))
            if msg.startswith("NOT_LINKED: "):
                events.append(("bazar_link", {"pack_id": pack.id, "name": pack.name}))
                raise ToolError(msg.removeprefix("NOT_LINKED: "))
            raise
        if isinstance(out, dict) and out.get("pc_file"):
            events.append(("pc_file", out["pc_file"]))
            out = {**out, "phone": "A download card for this file is shown in the chat."}
        act = _open_action(out)
        if act:
            events.append(("bazar_open", {**act, "pack": pack.name, "message": out.get("message", "")}))
            out = {**out, "phone": "An Open button is shown in the chat; the user taps it to continue."}
        return out


def _run_pc_read(tenant_id: str, pack: Pack, tool: str, args: dict[str, Any], events: list) -> dict[str, Any]:
    """PC reads run with no database transaction open: the PC's answer (and its file upload) may need to write."""
    from types import SimpleNamespace
    ctx = SimpleNamespace(user=SimpleNamespace(id=tenant_id), session=None, task=None, settings=get_settings())
    try:
        out = executors()["pc"].call(pack, tool, args, ctx)
    except ToolError as e:
        raise ToolError(str(e).removeprefix("PC_OFFLINE: "))
    if isinstance(out, dict) and out.get("pc_file"):
        events.append(("pc_file", out["pc_file"]))
        out = {**out, "phone": "A download card for this file is shown in the chat."}
    return out


def decide(tenant_id: str, approval_id: str, decision: str) -> dict[str, Any]:
    if decision not in ("approve", "reject"):
        raise ToolError("decision must be approve or reject")
    reg = registry()
    with session() as s:
        user = ensure_user(s, tenant_id)
        ap = s.get(Approval, approval_id)
        if ap is None or ap.user_id != user.id:
            raise ToolError("Approval not found")
        conv = ap.conversation_id
        pack = reg.lookup((ap.action or {}).get("pack_id", ""))
        outcome = Runner(s, get_settings(), reg, executors()).decide(approval_id, user, decision)
        card = card_of(ap, pack)
    act = _open_action(outcome)
    card["result"] = {"message": outcome.get("message") or outcome.get("error") or "", "open": act}
    if conv:
        bus.publish(conv, "bazar_approval", card)
        if outcome.get("error"):
            notify(conv, f"{card['title']}: nahi ho paya. {outcome['error']}")
        elif decision == "reject":
            notify(conv, f"Theek hai, '{card['title']}' cancel kar diya. Kuch order ya payment nahi hua.")
        else:
            notify(conv, outcome.get("message") or f"'{card['title']}' ho gaya.")
    return {"status": ap.decision, "outcome": outcome, "open": act}


def pending_approvals(tenant_id: str) -> list[dict[str, Any]]:
    reg = registry()
    with session() as s:
        rows = s.scalars(select(Approval).where(Approval.user_id == tenant_id, Approval.decision == "pending")
                         .order_by(Approval.created_at.desc()).limit(20)).all()
        return [card_of(a, reg.lookup((a.action or {}).get("pack_id", ""))) for a in rows]


def _what(s, reg, provider: str) -> str:
    p = reg.lookup(provider)
    if p:
        return p.name
    shop = s.get(Shop, provider)
    return shop.name if shop else provider


def activity(tenant_id: str, limit: int = 20) -> dict[str, Any]:
    reg = registry()
    with session() as s:
        txns = s.scalars(select(Transaction).where(Transaction.user_id == tenant_id, Transaction.status != "fetched")
                         .order_by(Transaction.created_at.desc()).limit(limit)).all()
        orders = s.scalars(select(ShopOrder).where(ShopOrder.user_id == tenant_id, ShopOrder.status != "cart")
                           .order_by(ShopOrder.created_at.desc()).limit(limit)).all()
        shops = {o.shop_id: s.get(Shop, o.shop_id) for o in orders}
        return {
            "payments": [{"ref": t.txn_ref, "kind": t.kind, "what": _what(s, reg, t.provider),
                          "amount": rupees(t.amount_paise), "status": t.status, "at": t.created_at.isoformat(),
                          "demo": bool((t.meta or {}).get("bill", {}).get("sandbox"))} for t in txns],
            "orders": [{"id": o.id, "shop": shops[o.shop_id].name if shops.get(o.shop_id) else "", "status": o.status,
                        "payment": o.payment_status, "total": rupees(o.total_paise), "slot": o.slot,
                        "items": [l.get("label", "") for l in o.lines]} for o in orders],
        }


# ---------------------------------------------------------------- user settings / contacts
def get_user_settings(tenant_id: str) -> dict[str, Any]:
    with session() as s:
        u = ensure_user(s, tenant_id)
        return {"cap_per_order_rupees": u.cap_per_order_paise / 100, "cap_per_day_rupees": u.cap_per_day_paise / 100,
                "pincode": u.pincode, "address": (u.profile or {}).get("address", ""), "language": u.language, "phone": u.phone}


def set_user_settings(tenant_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Only from the app (never the model): spend caps, address, pincode, phone."""
    with session() as s:
        u = ensure_user(s, tenant_id)
        if data.get("cap_per_order_rupees") is not None:
            u.cap_per_order_paise = max(0, min(to_paise(data["cap_per_order_rupees"]), 500_000))  # ≤ ₹5,000 auto
        if data.get("cap_per_day_rupees") is not None:
            u.cap_per_day_paise = max(0, min(to_paise(data["cap_per_day_rupees"]), 2_000_000))
        if data.get("pincode") is not None:
            pin = re.sub(r"\D", "", str(data["pincode"]))[:6]
            u.pincode = pin
        if data.get("address") is not None:
            u.profile = {**(u.profile or {}), "address": str(data["address"])[:400]}
        if data.get("language") in ("hi", "mr", "en"):
            u.language = data["language"]
        if data.get("phone") is not None:
            u.phone = re.sub(r"\D", "", str(data["phone"]))[-12:]
    return get_user_settings(tenant_id)


def add_contact(tenant_id: str, name: str, upi_id: str = "", phone: str = "", relation: str = "") -> dict[str, Any]:
    name = (name or "").strip()[:120]
    if not name:
        raise ToolError("Contact name is missing")
    upi_id = (upi_id or "").strip()
    if upi_id and not valid_vpa(upi_id):
        raise ToolError(f"'{upi_id}' is not a valid UPI ID")
    phone = re.sub(r"\D", "", phone or "")
    if len(phone) == 10:
        phone = "91" + phone
    with session() as s:
        ensure_user(s, tenant_id)
        c = s.scalars(select(Contact).where(Contact.user_id == tenant_id, Contact.name == name)).first()
        if c is None:
            c = Contact(user_id=tenant_id, name=name)
            s.add(c)
        if upi_id:
            c.upi_id = upi_id
        if phone:
            c.phone = phone
        if relation:
            c.relation = relation[:40]
        s.flush()
        return {"saved": name, "upi_id": c.upi_id, "phone": c.phone}


def list_contacts(tenant_id: str) -> list[dict[str, Any]]:
    with session() as s:
        return [{"name": c.name, "upi_id": c.upi_id, "phone": c.phone, "relation": c.relation}
                for c in s.scalars(select(Contact).where(Contact.user_id == tenant_id).order_by(Contact.name)).all()]


# ---------------------------------------------------------------- linked app accounts (MCP)
def mcp_packs() -> list[Pack]:
    return registry().by_executor("mcp")


def connections(tenant_id: str) -> list[dict[str, Any]]:
    st = get_settings()
    with session() as s:
        user = ensure_user(s, tenant_id)
        out = []
        for p in mcp_packs():
            out.append({"pack_id": p.id, "name": p.name, "provider": p.config["provider"], "status": pack_status(s, user, p),
                        "configured": bool(getattr(st, p.config["endpoint_setting"], ""))})
        for r in custom_mcp.user_rows(s, user.id):
            p = custom_mcp.to_pack(r)
            out.append({"pack_id": p.id, "name": p.name, "provider": p.config["provider"], "status": pack_status(s, user, p),
                        "configured": True, "custom": True})
        return out


def _link_target(s, tenant_id: str, pack_id: str) -> tuple[Pack, str]:
    p = registry().lookup(pack_id)
    if not p or p.executor != "mcp" or (p.config.get("custom") and p.config.get("owner") != tenant_id):
        raise ToolError("Unknown app")
    url = p.config.get("endpoint") or getattr(get_settings(), p.config["endpoint_setting"], "")
    if not url:
        raise ToolError(f"{p.name} is not available on this server yet.")
    return p, url


def link_start(tenant_id: str, pack_id: str) -> str:
    from . import mcp_auth
    with session() as s:
        ensure_user(s, tenant_id)
        p, url = _link_target(s, tenant_id, pack_id)
        try:
            return mcp_auth.start(s, tenant_id, p.config["provider"], url)
        except (mcp_auth.LinkError, custom_mcp.UrlError) as e:
            raise ToolError(str(e))


def link_finish(state: str, code: str) -> tuple[str, str]:
    from . import mcp_auth
    with session() as s:
        try:
            uid, provider = mcp_auth.finish(s, state, code)
        except (mcp_auth.LinkError, custom_mcp.UrlError) as e:
            raise ToolError(str(e))
        name = next((p.name for p in mcp_packs() if p.config["provider"] == provider), provider)
        if provider.startswith("custom:"):
            row = s.get(CustomMcp, provider.removeprefix("custom:"))
            if row:
                name = row.name
                row.auth = "oauth"
    for p in mcp_packs():  # tool lists are cached per user; drop them
        executors()["mcp"]._cache.pop(p.id + ":" + uid, None)
    if provider.startswith("custom:"):
        executors()["mcp"]._cache.pop(provider.removeprefix("custom:") + ":" + uid, None)
    return uid, name


def link_token(tenant_id: str, provider: str, token: str, expires_in: int | None = None) -> None:
    """Operator/dev path: store a token obtained elsewhere."""
    from .security import vault
    if provider not in {p.config["provider"] for p in mcp_packs()}:
        raise ToolError("Unknown provider")
    with session() as s:
        ensure_user(s, tenant_id)
        for c in s.scalars(select(Connection).where(Connection.user_id == tenant_id, Connection.provider == provider)).all():
            c.status = "replaced"
        exp = (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(seconds=expires_in)) if expires_in else None
        s.add(Connection(user_id=tenant_id, provider=provider, token_enc=vault().seal(token), status="active", expires_at=exp))


def unlink(tenant_id: str, pack_id: str) -> bool:
    with session() as s:
        p, _ = _link_target(s, tenant_id, pack_id)
        rows = s.scalars(select(Connection).where(Connection.user_id == tenant_id, Connection.provider == p.config["provider"],
                                                  Connection.status == "active")).all()
        for c in rows:
            c.status, c.token_enc = "revoked", ""
    executors()["mcp"]._cache.pop(p.id + ":" + tenant_id, None)
    return bool(rows)


# ---------------------------------------------------------------- MCP servers the user adds
def mcp_directory(query: str = "", field: str = "", limit: int = 8) -> dict[str, Any]:
    if not query and not field:
        return directory.stats()
    return {"servers": directory.search(query, limit=limit, field=field)}


def mcp_list(tenant_id: str) -> list[dict[str, Any]]:
    with session() as s:
        user = ensure_user(s, tenant_id)
        return [custom_mcp.public(r, pack_status(s, user, custom_mcp.to_pack(r))) for r in custom_mcp.user_rows(s, user.id)]


def mcp_add(tenant_id: str, url: str, name: str = "", ref: str = "", key: str = "", key_header: str = "",
            probe_client=None, conversation_id: str = "") -> dict[str, Any]:
    """Add a remote MCP server. Tries it right away; works out whether it needs a sign-in or a key."""
    url = (url or "").strip()
    if not url:
        entry = directory.get(ref) if ref else None
        if entry:
            raise ToolError(f"{entry['r']} has no address in the directory. Ask the user for its https MCP address "
                            f"(see {entry['l']}); never guess one.")
        raise ToolError("Give the server's https MCP address.")
    try:
        url = custom_mcp.check_url(url)
    except custom_mcp.UrlError as e:
        raise ToolError(str(e))
    with session() as s:
        user = ensure_user(s, tenant_id)
        try:
            row = custom_mcp.create(s, user.id, url, name, ref)
            if key:
                custom_mcp.save_key(s, row, key, key_header)
        except custom_mcp.UrlError as e:
            raise ToolError(str(e))
        pack = custom_mcp.to_pack(row)
        headers = custom_mcp.headers_for(s, pack, user.id) if row.auth == "key" else {}
        result, note = custom_mcp.probe(url, headers, probe_client)
        out: dict[str, Any] = {"pack_id": row.id, "name": row.name, "url": row.url}
        if result == "ok":
            out.update(status="ready", say=f"{row.name} is connected. Use bazar_find or bazar_run with pack_id {row.id}.")
        elif result == "auth" and row.auth != "key":
            row.auth = "oauth"
            out.update(status="needs_link", say="This server needs a sign-in. A Link button is shown; after the user signs "
                                                "in, it works. If it uses an API key instead, they add it in Connect > MCP servers.")
        elif result == "auth":
            out.update(status="key_rejected", say="The server refused that key. Ask the user to check it in Connect > MCP servers.")
        else:
            row.status = "removed"
            raise ToolError(note)
        if row.caution:
            out["caution"] = "This server can act on money, crypto, code or the computer; every action needs the user's tap."
        status = out["status"]
        conv = conversation_id or latest_conversation(s, tenant_id)
    executors()["mcp"]._cache.pop(out["pack_id"] + ":" + tenant_id, None)
    if status == "needs_link" and conv:
        bus.publish(conv, "bazar_link", {"pack_id": out["pack_id"], "name": out["name"]})
    return out


def mcp_set_key(tenant_id: str, pack_id: str, key: str, header: str = "") -> dict[str, Any]:
    with session() as s:
        row = s.get(CustomMcp, pack_id)
        if not row or row.user_id != tenant_id or row.status != "active":
            raise ToolError("Unknown MCP server")
        try:
            custom_mcp.save_key(s, row, key, header)
        except custom_mcp.UrlError as e:
            raise ToolError(str(e))
        user = ensure_user(s, tenant_id)
        st = pack_status(s, user, custom_mcp.to_pack(row))
    executors()["mcp"]._cache.pop(pack_id + ":" + tenant_id, None)
    return {"pack_id": pack_id, "status": st}


def mcp_remove(tenant_id: str, pack_id: str) -> bool:
    with session() as s:
        row = s.get(CustomMcp, pack_id)
        if not row or row.user_id != tenant_id or row.status != "active":
            return False
        row.status = "removed"
        for c in s.scalars(select(Connection).where(Connection.user_id == tenant_id,
                                                    Connection.provider == custom_mcp.provider_of(pack_id))).all():
            c.status, c.token_enc = "revoked", ""
    executors()["mcp"]._cache.pop(pack_id + ":" + tenant_id, None)
    return True


# ---------------------------------------------------------------- payments
def _conv_of_txn(s, txn: Transaction) -> str:
    if txn.task_id:
        t = s.get(Task, txn.task_id)
        if t and t.conversation_id:
            return t.conversation_id
    return latest_conversation(s, txn.user_id)


def latest_conversation(s, tenant_id: str) -> str:
    c = s.scalars(select(CoreConversation).where(CoreConversation.tenant_id == tenant_id)
                  .order_by(CoreConversation.created_at.desc())).first()
    return c.id if c else ""


def payment_confirmed(txn_ref: str, ok: bool, provider_ref: str = "") -> dict[str, Any]:
    with session() as s:
        txn = Runner(s, get_settings(), registry(), executors()).payment_confirmed(txn_ref, ok, provider_ref)
        conv = _conv_of_txn(s, txn)
        reply = (txn.meta or {}).get("reply") or ("Payment nahi hua. Kuch kata nahi; dobara try karein?" if not ok else "")
        out = {"txn_ref": txn.txn_ref, "status": txn.status}
    if conv and reply:
        notify(conv, reply)
    return out


def verify_webhook(raw: bytes, signature: str) -> bool:
    secret = get_settings().webhook_secret
    if not secret:
        return False
    good = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(good, signature or "")


# ---------------------------------------------------------------- merchants (shops)
def _hash(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


def create_shop(tenant_id: str, data: dict[str, Any]) -> dict[str, Any]:
    reg = registry()
    tpl = data.get("template_id", "")
    if tpl not in reg.packs or reg.get(tpl).executor != "shop":
        raise ToolError("Unknown shop template. Templates: " + ", ".join(p.id for p in reg.by_executor("shop")))
    if not valid_vpa(data.get("upi_id", "")):
        raise ToolError("Invalid UPI ID")
    phone = re.sub(r"\D", "", data.get("owner_phone", ""))
    if len(phone) == 10:
        phone = "91" + phone
    if len(phone) < 12:
        raise ToolError("Owner phone must be a 10-digit Indian mobile number")
    token = "shop_" + secrets.token_urlsafe(24)
    with session() as s:
        shop = Shop(template_id=tpl, name=str(data["name"])[:160], owner_phone=phone, upi_id=data["upi_id"].strip(),
                    city=str(data.get("city", ""))[:80], pincodes=[re.sub(r"\D", "", str(p))[:6] for p in data.get("pincodes") or []],
                    aliases=[str(a)[:60] for a in data.get("aliases") or []], languages=data.get("languages") or ["mr", "hi", "en"],
                    min_order_paise=to_paise(data.get("min_order_rupees") or 0), delivery_fee_paise=to_paise(data.get("delivery_fee_rupees") or 0),
                    slots=[str(x)[:60] for x in data.get("slots") or []], owner_tenant=tenant_id, merchant_token_hash=_hash(token))
        s.add(shop)
        s.flush()
        return {"id": shop.id, "name": shop.name, "template": tpl, "merchant_token": token,
                "note": "Save the merchant token now; it is shown only once. The shop uses it to see and update orders."}


def shop_for(s, shop_id: str, tenant_id: str | None, merchant_token: str | None) -> Shop:
    shop = s.get(Shop, shop_id)
    if not shop:
        raise ToolError("Shop not found")
    if merchant_token and shop.merchant_token_hash and hmac.compare_digest(_hash(merchant_token), shop.merchant_token_hash):
        return shop
    if tenant_id and shop.owner_tenant and tenant_id == shop.owner_tenant:
        return shop
    raise PermissionError("Not your shop")


def add_items(shop_id: str, items: list[dict[str, Any]], tenant_id: str | None, merchant_token: str | None) -> dict[str, Any]:
    with session() as s:
        shop = shop_for(s, shop_id, tenant_id, merchant_token)
        for it in items:
            s.add(ShopItem(shop_id=shop.id, name=str(it["name"])[:160], price_paise=to_paise(it["price_rupees"]),
                           unit=str(it.get("unit") or "pc")[:20], unit_qty=float(it.get("unit_qty") or 1),
                           aliases=[str(a)[:60] for a in it.get("aliases") or []], in_stock=bool(it.get("in_stock", True)),
                           kind=str(it.get("kind") or "product")[:20]))
        s.flush()
        return {"shop": shop.name, "items": len(shop.items)}


def shop_orders(shop_id: str, tenant_id: str | None, merchant_token: str | None, status: str | None = None) -> list[dict[str, Any]]:
    with session() as s:
        shop = shop_for(s, shop_id, tenant_id, merchant_token)
        q = select(ShopOrder).where(ShopOrder.shop_id == shop.id, ShopOrder.status != "cart")
        if status:
            q = q.where(ShopOrder.status == status)
        return [{"id": o.id, "status": o.status, "payment": o.payment_status, "total": rupees(o.total_paise), "slot": o.slot,
                 "address": o.address, "lines": [l["label"] for l in o.lines], "at": o.created_at.isoformat(),
                 "whatsapp_alert": o.notify_status} for o in s.scalars(q.order_by(ShopOrder.created_at.desc()).limit(100)).all()]


ORDER_STATUS = {"accepted", "ready", "delivered", "cancelled"}
STATUS_HI = {"accepted": "order accept kar liya", "ready": "order taiyaar hai", "delivered": "order deliver ho gaya",
             "cancelled": "order cancel kar diya"}


def update_order(shop_id: str, order_id: str, status: str | None, paid: bool, tenant_id: str | None,
                 merchant_token: str | None) -> dict[str, Any]:
    msgs, conv = [], ""
    with session() as s:
        shop = shop_for(s, shop_id, tenant_id, merchant_token)
        o = s.get(ShopOrder, order_id)
        if not o or o.shop_id != shop.id:
            raise ToolError("Order not found")
        if status:
            if status not in ORDER_STATUS:
                raise ToolError("status must be accepted, ready, delivered or cancelled")
            o.status = status
            msgs.append(f"{shop.name} ne aapka {STATUS_HI[status]}.")
        txn = s.scalars(select(Transaction).where(Transaction.txn_ref == o.txn_ref)).first() if o.txn_ref else None
        conv = _conv_of_txn(s, txn) if txn else latest_conversation(s, o.user_id)
        ref, already = o.txn_ref, o.payment_status == "paid"
        out = {"id": o.id, "status": o.status}
    if paid and ref and not already:
        payment_confirmed(ref, True, "MERCHANT_CONFIRMED")  # notifies the user itself
    if conv and msgs:
        notify(conv, " ".join(msgs))
    with session() as s:
        o = s.get(ShopOrder, order_id)
        out["payment"] = o.payment_status
    return out


def upload_dues(shop_id: str, dues: list[dict[str, Any]], tenant_id: str | None, merchant_token: str | None) -> dict[str, Any]:
    with session() as s:
        shop = shop_for(s, shop_id, tenant_id, merchant_token)
        for d in dues:
            ph = re.sub(r"\D", "", str(d.get("customer_phone") or ""))
            s.add(ShopDue(shop_id=shop.id, customer_ref=str(d["customer_ref"])[:60], customer_phone=ph[-12:],
                          description=str(d.get("description") or "")[:200], amount_paise=to_paise(d["amount_rupees"]),
                          due_on=dt.date.fromisoformat(d["due_on"]) if d.get("due_on") else None))
        return {"uploaded": len(dues)}


def list_shops(template: str | None = None, pincode: str | None = None) -> list[dict[str, Any]]:
    with session() as s:
        q = select(Shop).where(Shop.active.is_(True))
        if template:
            q = q.where(Shop.template_id == template)
        shops = s.scalars(q).all()
        if pincode:
            shops = [x for x in shops if not x.pincodes or pincode in x.pincodes]
        return [{"id": x.id, "name": x.name, "template": x.template_id, "city": x.city, "items": len(x.items)} for x in shops]


# ---------------------------------------------------------------- reminders (bill, birthday, medicine packs)
def _advance(r: Reminder) -> None:
    step = {"daily": dt.timedelta(days=1), "weekly": dt.timedelta(days=7)}.get(r.repeat)
    if step:
        r.due_at += step
    elif r.repeat == "monthly":
        m = r.due_at.month % 12 + 1
        y = r.due_at.year + (r.due_at.month == 12)
        r.due_at = r.due_at.replace(year=y, month=m, day=min(r.due_at.day, 28))
    elif r.repeat == "yearly":
        try:
            r.due_at = r.due_at.replace(year=r.due_at.year + 1)
        except ValueError:
            r.due_at = r.due_at.replace(year=r.due_at.year + 1, day=28)
    else:
        r.done = True
    # never fire a backlog after downtime: jump daily/weekly repeats past "now"
    nowu = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    if not r.done and step:
        while r.due_at <= nowu:
            r.due_at += step


ICON = {"bill": "Bill yaad dilana", "medicine": "Dawai ka samay", "birthday": "Aaj khaas din", "event": "Event", "reminder": "Yaad dilana"}


def fire_due_reminders() -> int:
    nowu = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    fired = []
    with session() as s:
        rows = s.scalars(select(Reminder).where(Reminder.done.is_(False), Reminder.due_at <= nowu).limit(50)).all()
        for r in rows:
            conv = latest_conversation(s, r.user_id)
            fired.append((conv, f"{ICON.get(r.kind, 'Yaad dilana')}: {r.text}"))
            _advance(r)
    for conv, text in fired:
        if conv:
            notify(conv, text)
    return len(fired)


def catalog(tenant_id: str) -> dict[str, Any]:
    """Every pack with its live status, for the app's Apps screen."""
    reg = registry()
    with session() as s:
        user = ensure_user(s, tenant_id)
        packs = [{"pack_id": p.id, "name": p.name, "category": p.category, "kind": p.sub_category, "executor": p.executor,
                  "status": pack_status(s, user, p)} for p in reg.all()]
        packs += [{"pack_id": r.id, "name": r.name, "category": "My MCP servers", "kind": "MCP server", "executor": "mcp",
                   "status": pack_status(s, user, custom_mcp.to_pack(r))} for r in custom_mcp.user_rows(s, user.id)]
    counts: dict[str, int] = {}
    for p in packs:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    return {"total": len(packs), "by_status": counts, "packs": packs}
