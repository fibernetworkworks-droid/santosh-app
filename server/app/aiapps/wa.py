"""v0.772 HOOLA AI APPS - D2: an AI app answering on HER business WhatsApp number.

When one of her LIVE apps names a business phone_number_id in `channels.whatsapp`, that number's customer messages are
answered by the app (runtime channel 'whatsapp', one session per customer wa_id) instead of the Employee brain. The
reply still goes out through `employee.inbox.send`, so the 24 h window, STOP, secrets and her takeover are unchanged;
the inbox checks human mode / STOP / window BEFORE it asks the app. No app bound = the inbox is exactly as before.
"""
from __future__ import annotations

import logging

from ..db import session
from . import runtime as RT
from . import store as ST
from .models import AiApp, ensure_tables

log = logging.getLogger("santosh.aiapps.wa")


def app_for_number(tenant: str, pnid: str) -> AiApp | None:
    """Her live app bound to this business number, or None."""
    pnid = str(pnid or "").strip()
    if not tenant or not pnid:
        return None
    try:
        ensure_tables()
        with session() as s:
            rows = (s.query(AiApp).filter(AiApp.tenant_id == tenant, AiApp.status == "live")
                    .order_by(AiApp.updated_at.desc()).all())
            for a in rows:
                if a.live_version and str(ST._j(a.channels, {}).get("whatsapp") or "").strip() == pnid:
                    s.expunge(a)
                    return a
    except Exception:                                   # noqa: BLE001 - a broken app table never breaks the inbox
        log.warning("ai app lookup for %s failed", pnid, exc_info=True)
    return None


def answer_whatsapp(tenant: str, pnid: str, wa_id: str, text: str, name: str = "") -> str | None:
    """The app's reply to one customer's message, or None (no app bound / nothing to say). Never sends anything."""
    a = app_for_number(tenant, pnid)
    if a is None or not str(text or "").strip():
        return None
    visitor = str(wa_id or "")[:120]
    sid = RT.session_for(a, visitor=visitor, channel="whatsapp")
    first = not sid
    if first:
        # the customer wrote to the business first; the notice goes with the first reply (DPDP)
        sid, _tok = RT.open_session(a, "whatsapp", visitor=visitor, consent=True)
    try:
        out = RT.answer(a, text=str(text)[:RT.MAX_Q], channel="whatsapp", session_id=sid, visitor_name=name)
    except ST.AppError:
        return None
    reply = str(out.get("reply") or "").strip()
    if not reply:
        return None
    if first:
        notice = (ST.live_soul(a)[0] or {}).get("notice") or ""
        if notice:
            reply = f"{notice}\n\n{reply}"
    return reply
