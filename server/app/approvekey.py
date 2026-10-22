"""v0.97 Fingerprint-signed approvals: a money card is approved only by HER phone's fingerprint, not by the app key alone.

From the Grok Bot study (Claude Doc "Grok Bot teardown: what Hoola should take", idea 2). Until now an approval was an
ordinary API call: anyone holding the app's key (a stolen phone backup, a leaked key) could approve a payment card.

  * The phone makes an EC P-256 key inside Android Keystore (StrongBox when the phone has it). The key can sign only
    right after a fingerprint / face check (BIOMETRIC_STRONG) and is voided when a new fingerprint is added. Only the
    public key comes here (`ApproveDevice`).
  * A money card (Bazar approval with money, Video Studio price card) asks for a challenge: the server writes a message
    that names the exact card (kind, id, a hash of title / payee / amount / items, a nonce, 2-minute expiry). The phone
    shows BiometricPrompt and signs it; the server checks the signature, the hash against the card as it is NOW, the
    expiry and that the challenge is used once. Then the old approval path runs.
  * Once any key is active, money cards REQUIRE the signature (HTTP 428 `fingerprint_needed` without it). Rejecting a
    card never needs one. Phones without a strong fingerprint sensor (or Android < 9) keep the slide as before.
  * A stolen app key must not be able to undo this: adding a second phone while one is active is PENDING for 24 hours
    (push + chat line, she can cancel) unless an active phone signs it; removing a phone is immediate only when signed
    by an active phone, else it also waits 24 hours (and can be cancelled).
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

log = logging.getLogger("santosh.approvekey")
WAIT = timedelta(hours=24)
CHALLENGE_TTL = timedelta(minutes=2)
STATS = {"challenges": 0, "verified": 0, "refused": 0, "required": 0}


class ApproveError(Exception):
    pass


class ApproveDevice(Base):
    __tablename__ = "approve_devices"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ad"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    device_id: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120), default="")
    public_key: Mapped[str] = mapped_column(Text)                 # base64 DER SubjectPublicKeyInfo (EC P-256)
    status: Mapped[str] = mapped_column(String(12), default="active")   # active | pending | removed
    active_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remove_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    strongbox: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApproveChallenge(Base):
    __tablename__ = "approve_challenges"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ac"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(20))            # bazar | studio | endorse | remove
    target: Mapped[str] = mapped_column(String(120))
    digest: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _load_key(b64: str):
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import load_der_public_key
    try:
        key = load_der_public_key(base64.b64decode(b64, validate=False))
    except Exception:
        raise ApproveError("Phone ki chaabi padhi nahi ja saki (galat public key).")
    if not isinstance(key, ec.EllipticCurvePublicKey) or key.curve.name != "secp256r1":
        raise ApproveError("Sirf EC P-256 chaabi chalti hai.")
    return key


def _settle(s, tenant: str) -> None:
    """Pending adds / removals whose 24 hours are over take effect."""
    t = datetime.now(timezone.utc)
    for d in s.scalars(select(ApproveDevice).where(ApproveDevice.tenant_id == tenant, ApproveDevice.status != "removed")).all():
        if d.status == "pending" and d.active_after and _utc(d.active_after) <= t:
            d.status, d.active_after = "active", None
        if d.status == "active" and d.remove_after and _utc(d.remove_after) <= t:
            d.status, d.remove_after = "removed", None


def _view(d: ApproveDevice) -> dict[str, Any]:
    return {"device_id": d.device_id, "label": d.label, "status": d.status, "strongbox": bool(d.strongbox),
            "active_after": _utc(d.active_after).isoformat() if d.active_after else None,
            "remove_after": _utc(d.remove_after).isoformat() if d.remove_after else None,
            "added": _utc(d.created_at).isoformat() if d.created_at else None,
            "last_used": _utc(d.last_used).isoformat() if d.last_used else None}


def devices(tenant: str) -> dict[str, Any]:
    with session() as s:
        _settle(s, tenant)
        rows = s.scalars(select(ApproveDevice).where(ApproveDevice.tenant_id == tenant, ApproveDevice.status != "removed")
                         .order_by(ApproveDevice.created_at)).all()
        out = [_view(d) for d in rows]
    return {"devices": out, "on": any(d["status"] == "active" for d in out),
            "say": ("Paise wale card sirf aapke fingerprint se haan honge." if any(d["status"] == "active" for d in out)
                    else "Abhi fingerprint wali haan band hai: paise wale card slide se haan hote hain.")}


def active_on(tenant: str) -> bool:
    with session() as s:
        _settle(s, tenant)
        return s.scalars(select(ApproveDevice.id).where(ApproveDevice.tenant_id == tenant,
                                                         ApproveDevice.status == "active")).first() is not None


def _tell(tenant: str, text: str) -> None:
    """A chat line in her home chat (pushed to the phone like any message): someone is adding / removing a phone."""
    try:
        from .events import notify
        from .net.service import home_conv
        conv = home_conv(tenant)
        if conv:
            notify(conv, text)
    except Exception:
        log.exception("approve key notice failed")


def register(tenant: str, device_id: str, public_key: str, label: str = "", strongbox: bool = False,
             proof: dict[str, Any] | None = None) -> dict[str, Any]:
    device_id = str(device_id or "").strip()[:80]
    if not device_id:
        raise ApproveError("device_id chahiye")
    _load_key(public_key)
    with session() as s:
        _settle(s, tenant)
        others = s.scalars(select(ApproveDevice).where(ApproveDevice.tenant_id == tenant,
                                                       ApproveDevice.status != "removed")).all()
        mine = next((d for d in others if d.device_id == device_id), None)
        any_active = any(d.status == "active" and d.device_id != device_id for d in others)
        if mine is not None:          # the same phone made a new key (new fingerprint added, app reinstalled)
            mine.status = "removed"
        endorsed = False
        if any_active and proof:
            endorsed = _check(s, tenant, "endorse", device_id, proof, _endorse_digest(device_id, public_key))
        pending = any_active and not endorsed
        d = ApproveDevice(tenant_id=tenant, device_id=device_id, label=str(label or "")[:120], public_key=public_key,
                          strongbox=bool(strongbox), status="pending" if pending else "active",
                          active_after=datetime.now(timezone.utc) + WAIT if pending else None)
        s.add(d)
        s.flush()
        v = _view(d)
    if pending:
        _tell(tenant, f"Ek naya phone ('{v['label'] or 'phone'}') paise ki haan ke liye jud raha hai. 24 ghante baad chalu "
                      "hoga. Agar yeh aap nahi hain to Profile > Fingerprint se haan mein 'Rok do' dabaiye.")
    return {**v, "say": ("Yeh phone 24 ghante baad chalu hoga (pehle wale phone se haan karke abhi chalu kar sakte hain)."
                         if pending else "Ho gaya: ab paise wale card sirf is phone ke fingerprint se haan honge.")}


def _endorse_digest(device_id: str, public_key: str) -> str:
    return hashlib.sha256(f"endorse|{device_id}|{public_key}".encode()).hexdigest()


def remove(tenant: str, device_id: str, proof: dict[str, Any] | None = None) -> dict[str, Any]:
    with session() as s:
        _settle(s, tenant)
        d = s.scalars(select(ApproveDevice).where(ApproveDevice.tenant_id == tenant, ApproveDevice.device_id == device_id,
                                                  ApproveDevice.status != "removed")).first()
        if d is None:
            raise ApproveError("Yeh phone jude hue phones mein nahi hai.")
        if d.status == "pending":
            d.status = "removed"
            return {"status": "removed", "say": "Naya phone roka gaya."}
        signed = bool(proof) and _check(s, tenant, "remove", device_id, proof, hashlib.sha256(
            f"remove|{device_id}".encode()).hexdigest())
        if signed:
            d.status = "removed"
            return {"status": "removed", "say": "Phone hata diya."}
        d.remove_after = datetime.now(timezone.utc) + WAIT
        label = d.label
    _tell(tenant, f"'{label or 'phone'}' ko fingerprint wali haan se hataya ja raha hai: 24 ghante baad hatega. Agar yeh aap "
                  "nahi hain to Profile > Fingerprint se haan mein 'Rok do' dabaiye.")
    return {"status": "remove_pending", "say": "24 ghante baad hatega (jude hue phone se fingerprint dekar abhi hata sakte hain)."}


def cancel(tenant: str, device_id: str) -> dict[str, Any]:
    """Stop a pending add or a pending removal (no fingerprint needed: it only keeps things as they were)."""
    with session() as s:
        d = s.scalars(select(ApproveDevice).where(ApproveDevice.tenant_id == tenant, ApproveDevice.device_id == device_id,
                                                  ApproveDevice.status != "removed")).first()
        if d is None:
            raise ApproveError("Yeh phone nahi mila.")
        if d.status == "pending":
            d.status = "removed"
            return {"status": "removed", "say": "Naya phone roka gaya."}
        d.remove_after = None
        return {"status": d.status, "say": "Hatana roka gaya, phone juda rahega."}


# ---------------------------------------------------------------- what a card says, hashed
def card_digest(kind: str, target: str, tenant: str) -> tuple[str, dict[str, Any]]:
    """(hash, what to show) of the card as it is NOW. A card changed after the challenge = the signature fails."""
    if kind == "bazar":
        from .bazar import service as bz
        card = bz.approval_card(tenant, target)
        if card is None:
            raise ApproveError("Yeh card ab baaki nahi hai.")
        show = {"title": card.get("title", ""), "payee": card.get("payee", ""), "amount": card.get("amount", ""),
                "items": [i.get("name", "") + " " + i.get("price", "") for i in card.get("items") or []]}
    elif kind == "studio":
        from .studio import service as ss
        card = ss.approval_card(tenant, target)
        if card is None:
            raise ApproveError("Yeh card ab baaki nahi hai.")
        show = {"title": card.get("title", ""), "amount": card.get("inr") or card.get("amount", ""),
                "usd": card.get("usd", "")}
    elif kind == "deal":                          # v0.102 the buyer's order confirm on the Hoola Network
        from .net import deal as dl
        card = dl.confirm_card(tenant, target)
        if card is None:
            raise ApproveError("Yeh card ab baaki nahi hai.")
        show = {"title": card.get("title", ""), "payee": card.get("payee", ""), "amount": card.get("amount", ""),
                "items": [i.get("name", "") + " " + i.get("price", "") for i in card.get("items") or []],
                "quote": card.get("hash", "")}
    elif kind == "ads":                           # v0.108 an ad budget raise / resume
        from .ads import service as ads
        card = ads.approval_card(tenant, target)
        if card is None:
            raise ApproveError("Yeh card ab baaki nahi hai.")
        show = {"title": card.get("title", ""), "amount": card.get("amount", ""), "payee": card.get("payee", "")}
    else:
        raise ApproveError("kind = bazar | studio | deal | ads")
    return hashlib.sha256(json.dumps(show, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), show


def needed(tenant: str, kind: str, target: str) -> bool:
    """A fingerprint is needed for this approval: an active phone exists and the card moves / spends money."""
    if not active_on(tenant):
        return False
    if kind in ("studio", "deal"):
        return True
    if kind == "ads":                             # v0.108 only a change that spends more ad money
        from .ads import service as ads
        return ads.change_spends(tenant, target)
    if kind == "bazar":
        from .bazar import service as bz
        card = bz.approval_card(tenant, target)
        return bool(card and card.get("money"))
    return False


def challenge(tenant: str, kind: str, target: str) -> dict[str, Any]:
    if kind in ("bazar", "studio", "deal", "ads"):
        digest, show = card_digest(kind, target, tenant)
    elif kind == "remove":
        digest, show = hashlib.sha256(f"remove|{target}".encode()).hexdigest(), {"title": "Phone hatana"}
    elif kind == "endorse":
        pub = str(target).split("|", 1)
        if len(pub) != 2:
            raise ApproveError("endorse target = <device_id>|<public_key>")
        digest, show, target = _endorse_digest(pub[0], pub[1]), {"title": "Naya phone jodna"}, pub[0]
    else:
        raise ApproveError("kind = bazar | studio | deal | ads | remove | endorse")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|{kind}|{target}|{digest}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        c = ApproveChallenge(tenant_id=tenant, kind=kind, target=target, digest=digest, message=msg, expires_at=exp)
        s.add(c)
        s.flush()
        cid = c.id
    STATS["challenges"] += 1
    return {"challenge_id": cid, "message": msg, "show": show, "expires_at": exp.isoformat()}


def _check(s, tenant: str, kind: str, target: str, proof: dict[str, Any], digest: str) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    c = s.get(ApproveChallenge, str(proof.get("challenge_id") or ""))
    if c is None or c.tenant_id != tenant or c.used or c.kind != kind or c.target != target:
        return False
    if _utc(c.expires_at) < datetime.now(timezone.utc) or c.digest != digest:
        return False
    d = s.scalars(select(ApproveDevice).where(ApproveDevice.tenant_id == tenant,
                                              ApproveDevice.device_id == str(proof.get("device_id") or ""),
                                              ApproveDevice.status == "active")).first()
    if d is None:
        return False
    try:
        sig = base64.b64decode(str(proof.get("signature") or ""))
        _load_key(d.public_key).verify(sig, c.message.encode(), ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError, ApproveError):
        return False
    c.used = True
    d.last_used = datetime.now(timezone.utc)
    return True


def verify(tenant: str, kind: str, target: str, proof: dict[str, Any] | None) -> None:
    """Raise ApproveError unless the proof is a fresh, unused signature by an active phone over this card as it is now."""
    if not proof:
        STATS["required"] += 1
        raise ApproveError("fingerprint_needed")
    digest, _ = card_digest(kind, target, tenant)
    with session() as s:
        _settle(s, tenant)
        ok = _check(s, tenant, kind, target, proof, digest)
    if not ok:
        STATS["refused"] += 1
        raise ApproveError("fingerprint_invalid")
    STATS["verified"] += 1
