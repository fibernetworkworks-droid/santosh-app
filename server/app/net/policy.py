"""The receiving avatar's checks, from its owner's Mere Niyam: is this peer connected, is it a VIP, a blocked topic,
too many messages, quiet hours, and does this kind come in on its own, after asking, or never. Also the hard rule
that no PIN / OTP / password / card / Aadhaar number ever travels between avatars."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from ..db import session
from .models import NetMsg

KIND_RULE = {"message": "message", "ask": "message", "task": "message", "reminder": "message", "voice_note": "voice_note",
             "meeting": "meeting", "file": "file", "email": "email", "link": "link", "presentation": "presentation",
             "payment_request": "payment_request", "contact_card": "contact_card", "location": "location"}
APP_EXT = (".apk", ".xapk", ".apks", ".exe", ".msi", ".scr", ".bat", ".cmd", ".vbs", ".js", ".ps1", ".hta", ".jar", ".lnk")
DAILY_LIMIT = 40          # messages from one peer per day
BURST_LIMIT = 8           # in 5 minutes

_SECRET_WORDS = r"(otp|one[ -]?time|pin|mpin|upi ?pin|cvv|password|passcode|pass ?word|net ?banking)"
_OTP = re.compile(_SECRET_WORDS + r"\W{0,12}(is|hai|:|=|-)?\W{0,6}\d{4,8}\b|\b\d{4,8}\b\W{0,12}(is|hai)?\W{0,6}(your|aapka|tumhara)?\W{0,6}" + _SECRET_WORDS, re.I)
_PASSWORD = re.compile(r"\b(password|passcode|pass ?word)\b\W{0,6}(is|hai|:|=)\W{0,4}\S{4,}", re.I)
_AADHAAR = re.compile(r"\b[2-9]\d{3}[ -]\d{4}[ -]\d{4}\b|\b(aadhaar|aadhar|uidai|aadhaar no)\W{0,12}[2-9]\d{11}\b", re.I)
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _luhn(num: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", num)][::-1]
    if not 13 <= len(d) <= 19:
        return False
    return sum(x if i % 2 == 0 else (x * 2 - 9 if x * 2 > 9 else x * 2) for i, x in enumerate(d)) % 10 == 0


def secret_found(text: str) -> str:
    """Which forbidden detail is in the text ('' if none)."""
    t = text or ""
    if _OTP.search(t):
        return "OTP / PIN"
    if _PASSWORD.search(t):
        return "password"
    for m in _CARD.finditer(t):
        if _luhn(m.group(0)):
            return "card number"
    if _AADHAAR.search(t):
        return "Aadhaar number"
    return ""


def body_text(body: dict[str, Any]) -> str:
    parts = []
    for k in ("text", "subject", "title", "note", "question", "summary", "url", "name"):
        v = body.get(k)
        if isinstance(v, str):
            parts.append(v)
    return "\n".join(parts)


def rule_key(kind: str, body: dict[str, Any]) -> str:
    if kind == "file" and str(body.get("name", "")).lower().endswith(APP_EXT):
        return "app_file"
    return KIND_RULE.get(kind, "message")


def is_vip(rules: dict[str, Any], link, card: dict[str, Any] | None) -> bool:
    if link is not None and link.vip:
        return True
    names = {str(x).lower().lstrip("@") for x in rules.get("vip") or []}
    if not names:
        return False
    rel = (link.relation if link is not None else "").lower()
    cand = {rel, {"family": "family", "team": "team"}.get(rel, ""), (link.nick if link is not None else "").lower()}
    if card:
        cand |= {str(card.get("owner_name", "")).lower(), str(card.get("handle", "")).lower(),
                 str(card.get("owner_name", "")).lower().split(" ")[0]}
    if rel == "family":
        cand |= {"family", "parivar", "ghar"}
    if rel == "team":
        cand |= {"team", "office", "staff"}
    return bool(names & {c for c in cand if c})


def blocked_topic(rules: dict[str, Any], text: str) -> str:
    t = (text or "").lower()
    for topic in rules.get("blocked_topics") or []:
        w = str(topic).lower().strip()
        if w and re.search(r"\b" + re.escape(w) + r"\b", t):
            return w
    return ""


def in_quiet(rules: dict[str, Any], tenant: str, at: datetime | None = None) -> bool:
    q = rules.get("quiet") or {}
    if not q.get("on"):
        return False
    try:
        from ..life import tz_of
        local = (at or datetime.now(timezone.utc)).astimezone(tz_of(tenant))
    except Exception:
        local = at or datetime.now(timezone.utc)
    hm = local.hour * 60 + local.minute
    f = int(q.get("from", "22:00")[:2]) * 60 + int(q.get("from", "22:00")[3:5])
    t = int(q.get("to", "08:00")[:2]) * 60 + int(q.get("to", "08:00")[3:5])
    return (f <= hm < t) if f < t else (hm >= f or hm < t)


def quiet_ends(rules: dict[str, Any], tenant: str) -> datetime:
    from ..life import tz_of
    tz = tz_of(tenant)
    local = datetime.now(timezone.utc).astimezone(tz)
    to = rules.get("quiet", {}).get("to", "08:00")
    end = local.replace(hour=int(to[:2]), minute=int(to[3:5]), second=0, microsecond=0)
    if end <= local:
        end += timedelta(days=1)
    return end.astimezone(timezone.utc)


def too_many(tenant: str, peer: str) -> bool:
    now = datetime.now(timezone.utc)
    with session() as s:
        day = s.scalar(select(func.count()).select_from(NetMsg).where(
            NetMsg.tenant_id == tenant, NetMsg.peer == peer, NetMsg.direction == "in",
            NetMsg.created_at >= now - timedelta(days=1))) or 0
        burst = s.scalar(select(func.count()).select_from(NetMsg).where(
            NetMsg.tenant_id == tenant, NetMsg.peer == peer, NetMsg.direction == "in",
            NetMsg.created_at >= now - timedelta(minutes=5))) or 0
    return day >= DAILY_LIMIT or burst >= BURST_LIMIT


def decide(tenant: str, rules: dict[str, Any], link, card: dict[str, Any] | None, kind: str, body: dict[str, Any],
           in_my_thread: bool = False) -> dict[str, Any]:
    """-> {'action': block|decline|auto|ask, 'reason': str, 'vip': bool, 'quiet': bool}"""
    text = body_text(body)
    secret = secret_found(text)
    if secret:
        return {"action": "block", "reason": f"is mein {secret} jaisi jaankari thi (Hoola yeh kabhi aage nahi bhejta)",
                "vip": False, "quiet": False}
    vip = is_vip(rules, link, card)
    quiet = in_quiet(rules, tenant) and not (vip and rules.get("quiet", {}).get("vip_can_ring"))
    if in_my_thread and kind in ("reply", "meeting_ok", "meeting_no", "accepted", "declined", "receipt", "handled"):
        return {"action": "auto", "reason": "aapki shuru ki baat ka jawab", "vip": vip, "quiet": quiet}
    topic = blocked_topic(rules, text)
    if topic and not vip:
        return {"action": "decline", "reason": f"'{topic}' wali baatein aapne mana ki hain", "vip": vip, "quiet": quiet}
    key = rule_key(kind, body)
    setting = (rules.get("accept") or {}).get(key, "ask")
    if setting == "never" and not (vip and key in ("message", "voice_note")):
        return {"action": "decline", "reason": "aapke niyam mein yeh mana hai", "vip": vip, "quiet": quiet}
    if key in ("payment_request", "app_file"):
        return {"action": "ask", "reason": "paise / app file hamesha aapse poochh kar", "vip": vip, "quiet": quiet}
    if key == "file" and vip and (rules.get("decide_alone") or {}).get("accept_files_from_vip"):
        return {"action": "auto", "reason": "VIP ki file", "vip": vip, "quiet": quiet}
    if setting == "auto":
        return {"action": "auto", "reason": "aapke niyam: seedha le lo", "vip": vip, "quiet": quiet}
    return {"action": "ask", "reason": "aapse poochhna hai", "vip": vip, "quiet": quiet}
