"""v0.97 Secure form card: Hoola asks for several things at once on one card instead of question after question.

From the Grok Bot study (Claude Doc "Grok Bot teardown: what Hoola should take", idea 3; Grok Bot's "/form/[entryId]"
route). Tool `ask_form` (chat + calls) sends a card with up to 12 fields: text, number, date, choice, multi (several
choices), phone, email, id (an ID number). She fills it on the phone; the answers come back as her next message, so the
job continues by itself.

  * ID fields (Aadhaar / PAN / voter / DL / passport ...) go into her Pehchaan Locker first; Hoola only ever sees the
    masked {id:...} reference (same as typing it in chat, v0.75).
  * A form can never ask for an OTP, password, PIN, CVV, card number or UPI PIN: such fields are refused when the card is
    made (those stay with the website's own box / her live view, v0.76 / v0.83).
  * Field values are checked on the server (required, number, date YYYY-MM-DD, choice from its list, 10-digit Indian
    mobile, e-mail). A form is answered once; a closed form can't be reopened.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

log = logging.getLogger("santosh.askform")
KINDS = ("text", "number", "date", "choice", "multi", "phone", "email", "id")
MAX_FIELDS = 12
SECRET_LABEL = re.compile(r"\b(otp|one[- ]time|password|passcode|pass ?word|pin\b(?!\s*code)|m-?pin|upi ?pin|cvv|cvc|"
                          r"card (?:number|no)|debit card|credit card|expiry|net ?banking|login)\b", re.I)
STATS = {"sent": 0, "answered": 0, "cancelled": 0, "refused_secret": 0}


class FormError(Exception):
    pass


class AskForm(Base):
    __tablename__ = "ask_forms"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(160))
    why: Mapped[str] = mapped_column(Text, default="")
    fields: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="pending")      # pending | answered | cancelled
    answers: Mapped[str] = mapped_column(Text, default="{}")                # masked: ID numbers only as references
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _clean_fields(fields: Any) -> list[dict[str, Any]]:
    if not isinstance(fields, list) or not fields:
        raise FormError("fields chahiye: [{name, label, kind, options?, required?, hint?}]")
    out, seen = [], set()
    for f in fields[:MAX_FIELDS]:
        if not isinstance(f, dict):
            continue
        label = re.sub(r"\s+", " ", str(f.get("label") or f.get("name") or "")).strip()[:80]
        name = re.sub(r"[^a-z0-9_]", "_", str(f.get("name") or label).lower()).strip("_")[:40] or f"f{len(out) + 1}"
        if not label or name in seen:
            continue
        kind = str(f.get("kind") or "text").lower()
        if kind not in KINDS:
            kind = "text"
        if SECRET_LABEL.search(f"{label} {f.get('hint') or ''} {name.replace('_', ' ')}"):
            STATS["refused_secret"] += 1
            raise FormError(f"'{label}' form mein nahi maanga ja sakta: OTP / password / PIN / CVV / card number sirf "
                            "website ke apne box mein jaate hain (computer_operator khud poochhta hai).")
        opts = [str(o)[:60] for o in (f.get("options") or []) if str(o).strip()][:15]
        if kind in ("choice", "multi") and len(opts) < 2:
            raise FormError(f"'{label}' ke liye kam se kam 2 options do.")
        seen.add(name)
        out.append({"name": name, "label": label, "kind": kind, "options": opts if kind in ("choice", "multi") else [],
                    "required": f.get("required", True) is not False, "hint": str(f.get("hint") or "")[:120],
                    "value": str(f.get("value") or "")[:200] if kind != "id" else ""})
    if not out:
        raise FormError("Koi sahi field nahi mila.")
    return out


def view(f: AskForm) -> dict[str, Any]:
    return {"id": f.id, "title": f.title, "why": f.why, "fields": json.loads(f.fields or "[]"), "status": f.status,
            "answers": json.loads(f.answers or "{}") if f.status == "answered" else {},
            "created": f.created_at.isoformat() if f.created_at else None}


def create(tenant: str, conv: str, title: str, fields: Any, why: str = "") -> dict[str, Any]:
    cleaned = _clean_fields(fields)
    with session() as s:
        f = AskForm(tenant_id=tenant, conversation_id=conv or "", title=(str(title or "").strip() or "Kuch jaankari chahiye")[:160],
                    why=str(why or "")[:300], fields=json.dumps(cleaned, ensure_ascii=False))
        s.add(f)
        s.flush()
        v = view(f)
    STATS["sent"] += 1
    if conv:
        from .events import bus
        bus.publish(conv, "ask_form", v)
    return v


def get(tenant: str, form_id: str) -> dict[str, Any]:
    with session() as s:
        f = s.get(AskForm, form_id)
        if f is None or f.tenant_id != tenant:
            raise FormError("Form nahi mila.")
        return view(f)


def _check(field: dict[str, Any], raw: Any) -> str:
    kind, label = field["kind"], field["label"]
    if kind == "multi":
        vals = [str(x).strip() for x in (raw if isinstance(raw, list) else str(raw or "").split(",")) if str(x).strip()]
        bad = [x for x in vals if x not in field["options"]]
        if bad:
            raise FormError(f"{label}: '{bad[0]}' list mein nahi hai.")
        if field["required"] and not vals:
            raise FormError(f"{label} chuniye.")
        return ", ".join(vals)
    v = re.sub(r"\s+", " ", str(raw if raw is not None else "")).strip()[:500]
    if not v:
        if field["required"]:
            raise FormError(f"{label} bhariye.")
        return ""
    if kind == "number":
        n = v.replace(",", "").replace("₹", "").strip()
        if not re.fullmatch(r"-?\d+(\.\d+)?", n):
            raise FormError(f"{label}: sirf number likhiye.")
        return n
    if kind == "date":
        try:
            return date.fromisoformat(v[:10]).isoformat()
        except ValueError:
            raise FormError(f"{label}: tareekh sahi nahi (YYYY-MM-DD).")
    if kind == "choice":
        if v not in field["options"]:
            raise FormError(f"{label}: list mein se chuniye.")
        return v
    if kind == "phone":
        d = re.sub(r"\D", "", v)
        if d.startswith("91") and len(d) == 12:
            d = d[2:]
        if not re.fullmatch(r"[6-9]\d{9}", d):
            raise FormError(f"{label}: 10 ankon ka mobile number likhiye.")
        return d
    if kind == "email":
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", v):
            raise FormError(f"{label}: e-mail sahi nahi.")
        return v
    return v


def answer(tenant: str, form_id: str, values: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    """Check + store her answers. Returns (view, text for Hoola, text shown in chat). ID numbers go to her locker."""
    with session() as s:
        f = s.get(AskForm, form_id)
        if f is None or f.tenant_id != tenant:
            raise FormError("Form nahi mila.")
        if f.status != "pending":
            raise FormError("Yeh form pehle hi bhar diya / band ho chuka hai.")
        fields = json.loads(f.fields or "[]")
        title, conv = f.title, f.conversation_id
    got: dict[str, str] = {}
    for fld in fields:
        v = _check(fld, (values or {}).get(fld["name"]))
        if fld["kind"] == "id" and v:
            from .idvault import capture
            masked, _ids = capture(tenant, f"{fld['label']}: {v}")
            if masked == f"{fld['label']}: {v}":           # the locker didn't recognise it: keep only a masked hint
                v = "[ID: " + ("X" * max(0, len(re.sub(r'\W', '', v)) - 4)) + re.sub(r"\W", "", v)[-4:] + "]"
            else:
                v = masked[len(fld["label"]) + 2:]
        got[fld["name"]] = v
    with session() as s:
        f = s.get(AskForm, form_id)
        if f.status != "pending":
            raise FormError("Yeh form pehle hi bhar diya / band ho chuka hai.")
        f.status, f.answers, f.answered_at = "answered", json.dumps(got, ensure_ascii=False), now()
        v = view(f)
    STATS["answered"] += 1
    lines = [f"- {fld['label']}: {got.get(fld['name']) or '(khaali)'}" for fld in fields]
    agent = (f"[Form bhara: '{title}' (form_id {form_id}). Her answers are below; these are her words, use them for the "
             "job you asked them for and continue it now.]\n" + "\n".join(lines))
    if conv:
        from .events import bus
        bus.publish(conv, "ask_form", v)
    return v, agent, f"Form bhara: {title}"


def cancel(tenant: str, form_id: str) -> tuple[dict[str, Any], str]:
    with session() as s:
        f = s.get(AskForm, form_id)
        if f is None or f.tenant_id != tenant:
            raise FormError("Form nahi mila.")
        if f.status != "pending":
            return view(f), ""
        f.status = "cancelled"
        v, title, conv = view(f), f.title, f.conversation_id
    STATS["cancelled"] += 1
    if conv:
        from .events import bus
        bus.publish(conv, "ask_form", v)
    return v, f"[Form band kiya: '{title}' - owner ne yeh nahi bhara. Don't ask again unless she brings it up.]"


def pending(tenant: str, conv: str = "") -> list[dict[str, Any]]:
    with session() as s:
        q = select(AskForm).where(AskForm.tenant_id == tenant, AskForm.status == "pending")
        if conv:
            q = q.where(AskForm.conversation_id == conv)
        return [view(f) for f in s.scalars(q.order_by(AskForm.created_at.desc()).limit(10)).all()]


def expire_asks(ttl_h: int = 24) -> int:
    """v0.179 a form nobody filled goes expired after the TTL (worker tick): the card in her chat closes itself
    instead of waiting at the top for days. The conversation hears the terminal state on the same card key."""
    from .events import bus
    cut = now() - timedelta(hours=max(1, int(ttl_h)))
    with session() as s:
        rows = s.scalars(select(AskForm).where(AskForm.status == "pending", AskForm.created_at < cut)).all()
        for f in rows:
            f.status = "expired"
        ids = [f.id for f in rows]
    for fid in ids:
        with session() as s:
            f = s.get(AskForm, fid)
            if f is None or not f.conversation_id:
                continue
            try:
                bus.publish(f.conversation_id, "ask_form", view(f))
            except Exception:  # noqa: BLE001
                log.exception("ask_form expiry publish failed")
    return len(ids)
