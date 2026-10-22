"""v0.107 Trust tiers and the verified-business credential (Hoola Deals phase 4).

Trust tiers (TRAI TCCCPR 2025 / WhatsApp Business opt-in rules copied as code, research Diagram 0.3):
  blocked   her own block, or a sender reported by 5+ different owners in 10 days ("limited": deal lists cut to 3 a day,
            offers refused) - `limited()`.
  stranger  no active connection: only a connect request (the network already enforces this).
  known     an active connection: structured asks; her Hoola answers inside her rules; orders / money need her tap.
  trusted   she marked them trusted (`set_trust`), or VIP / family / team, or named in Mere Niyam selling.trusted:
            auto quotes and auto accepts up to her caps (selling.auto_accept_who = trusted, the default).
  An explicit "known" from her wins over relation / VIP.

Verified-business credential: when the server operator verifies a business (GSTIN, optional Udyam, and that the UPI
payee name matches the bank account) this server SIGNS a credential with its server key (the same Ed25519 key that signs
federation requests): {v, type, sub = the business's Hoola address, name, gstin masked, udyam masked, upi (only when the
operator checked the bank name), iss = this server's domain, iat, exp (90 days; reissued while still verified)}. It rides
in every quote (`deal_quote.vbc`) and offer. The buyer's Hoola checks it in code (`check`): signature by the issuer's
server key, issuer is THIS server or one listed in HOOLA_TRUSTED_ISSUERS, not expired, subject == the sender, and for a
local issuer still verified right now. A business's own "I am verified" flag is never believed.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import identity as idn

TIERS = ("blocked", "stranger", "known", "trusted")
TIER_WORDS = {"blocked": "roka hua", "stranger": "anjaan", "known": "jaan-pehchaan", "trusted": "bharosemand"}
REPORT_LIMIT, REPORT_DAYS = 5, 10
LIMITED_ASKS_PER_DAY = 3
CRED_DAYS, CRED_REISSUE_DAYS = 90, 30
UDYAM_RE = re.compile(r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$")
REPORT_REASONS = ("spam", "fraud", "abuse", "fake", "other")
STATS = {"issued": 0, "checked_ok": 0, "checked_bad": 0, "reports": 0}


class TrustError(Exception):
    pass


class TrustReport(Base):
    """One owner reported one sender (kept per reporter; 5 different reporters in 10 days = limited)."""
    __tablename__ = "hoola_trust_reports"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)          # who reported
    peer: Mapped[str] = mapped_column(String(200), index=True)              # who was reported
    reason: Mapped[str] = mapped_column(String(12), default="spam")
    kind: Mapped[str] = mapped_column(String(30), default="")               # what it was about (promo_offer, deal_ask...)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- tiers
def limited(peer: str) -> bool:
    since = now() - timedelta(days=REPORT_DAYS)
    with session() as s:
        who = s.scalars(select(TrustReport.tenant_id).where(TrustReport.peer == peer, TrustReport.at >= since)).all()
    return len(set(who)) >= REPORT_LIMIT


def tier(tenant: str, peer: str) -> dict[str, Any]:
    from .service import _link
    l = _link(tenant, peer) if peer else None
    out = {"tier": "stranger", "limited": limited(peer) if peer else False, "why": ""}
    if l is not None and l.status == "blocked":
        out |= {"tier": "blocked", "why": "aapne roka hai"}
    elif out["limited"]:
        out |= {"tier": "blocked", "why": f"{REPORT_LIMIT}+ logon ne {REPORT_DAYS} din mein shikayat ki"}
    elif l is not None and l.status == "active":
        explicit = (getattr(l, "trust", "") or "")
        if explicit == "trusted":
            out |= {"tier": "trusted", "why": "aapne bharosemand chuna"}
        elif explicit == "known":
            out |= {"tier": "known", "why": "aapne jaan-pehchaan rakha"}
        elif l.vip or l.relation in ("family", "team"):
            out |= {"tier": "trusted", "why": "VIP / parivaar / team"}
        elif _named_trusted(tenant, l, peer):
            out |= {"tier": "trusted", "why": "Mere Niyam mein bharose wale"}
        else:
            out |= {"tier": "known", "why": "jude hue"}
    out["word"] = TIER_WORDS[out["tier"]]
    return out


def _named_trusted(tenant: str, l, peer: str) -> bool:
    try:
        from . import deal as dl
        return dl._named(dl.selling(tenant).get("trusted") or [], l, idn.peer_card(peer), peer)
    except Exception:
        return False


def is_trusted(tenant: str, peer: str) -> bool:
    return tier(tenant, peer)["tier"] == "trusted"


def set_trust(tenant: str, who: str, level: str) -> dict[str, Any]:
    """Owner only: mark a connection trusted / known (blocking stays the network's own block)."""
    from .service import NetError, _link, resolve
    if level not in ("trusted", "known", "auto"):
        raise NetError("level: trusted, known, auto")
    peer = resolve(tenant, who)
    with session() as s:
        from .models import Link
        l = s.scalars(select(Link).where(Link.tenant_id == tenant, Link.peer == peer)).first()
        if l is None or l.status != "active":
            raise NetError(f"{who} se Hoola connection nahi hai.")
        l.trust, l.updated_at = ("" if level == "auto" else level), now()
    _ = _link
    return {"peer": peer, "with": idn.label(idn.peer_card(peer))} | tier(tenant, peer)


def report(tenant: str, who: str, reason: str = "spam", kind: str = "") -> dict[str, Any]:
    """She reports a sender (spam / fraud ...). Once per reporter per 10 days; offers from them stop for her at once."""
    from .service import NetError, resolve
    if reason not in REPORT_REASONS:
        raise NetError("reason: " + ", ".join(REPORT_REASONS))
    peer = who if who.startswith("hl_") else resolve(tenant, who)
    since = now() - timedelta(days=REPORT_DAYS)
    with session() as s:
        dup = s.scalars(select(TrustReport).where(TrustReport.tenant_id == tenant, TrustReport.peer == peer,
                                                  TrustReport.at >= since)).first()
        if dup is None:
            s.add(TrustReport(id=new_id("tr"), tenant_id=tenant, peer=peer, reason=reason, kind=kind[:30], at=now()))
            STATS["reports"] += 1
    from . import promo
    promo.opt_out(tenant, peer, quiet=True)
    return {"status": "reported", "limited": limited(peer),
            "say": "Shikayat darj. Inke offers ab aapko nahi aayenge."}


# ---------------------------------------------------------------- the verified-business credential
def _canon(body: dict[str, Any]) -> bytes:
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def _mask(x: str, head: int = 2, tail: int = 3) -> str:
    x = x or ""
    return x[:head] + "•••" + x[-tail:] if len(x) > head + tail else ""


def issue(tenant: str) -> dict[str, Any] | None:
    """Sign a fresh credential for a business this server verified (None when it isn't verified)."""
    from . import federation as fed
    from .business import Business
    with session() as s:
        b = s.get(Business, tenant)
        if b is None or b.verification != "verified":
            if b is not None and getattr(b, "credential", None):
                b.credential = {}
            return None
        body = {"v": 1, "type": "hoola.verified_business", "sub": idn.my_card(tenant)["address"], "name": b.name,
                "gstin": _mask(b.gstin), "state": (b.gstin or "")[:2], "udyam": _mask(getattr(b, "udyam", "") or "", 8, 3),
                "upi": getattr(b, "verified_upi", "") or "", "iss": idn.domain(),
                "iat": now().isoformat(), "exp": (now() + timedelta(days=CRED_DAYS)).isoformat()}
        sig = base64.b64encode(fed._server_key().sign(_canon(body))).decode()
        cred = body | {"sig": sig}
        b.credential = cred
    STATS["issued"] += 1
    return cred


def credential(tenant: str) -> dict[str, Any] | None:
    """The credential to attach (reissued when older than 30 days; dropped when no longer verified)."""
    from .business import Business
    with session() as s:
        b = s.get(Business, tenant)
        if b is None or b.verification != "verified":
            return None
        cred = dict(getattr(b, "credential", None) or {})
    iat = _when(cred.get("iat"))
    if not cred or iat is None or now() - iat > timedelta(days=CRED_REISSUE_DAYS):
        return issue(tenant)
    return cred


def _when(x: Any) -> datetime | None:
    try:
        return _utc(datetime.fromisoformat(str(x)))
    except (TypeError, ValueError):
        return None


def trusted_issuers() -> set[str]:
    from ..config import get_settings
    raw = getattr(get_settings(), "hoola_trusted_issuers", "") or ""
    return {idn.domain().lower()} | {d.strip().lower() for d in raw.split(",") if d.strip()}


def check(cred: Any, subject: str) -> dict[str, Any]:
    """Is this a real, current credential for `subject`? Never raises; {'ok': False, 'why': ...} when not."""
    bad = {"ok": False, "name": "", "upi": "", "issuer": ""}
    if not isinstance(cred, dict) or cred.get("type") != "hoola.verified_business" or not cred.get("sig"):
        return bad | {"why": "credential nahi"}
    iss = str(cred.get("iss") or "").lower()
    out = bad | {"issuer": iss}
    if iss not in trusted_issuers():
        STATS["checked_bad"] += 1
        return out | {"why": f"{iss} hamara bharosemand verifier nahi"}
    if str(cred.get("sub") or "") != subject:
        STATS["checked_bad"] += 1
        return out | {"why": "credential kisi aur ka hai"}
    exp = _when(cred.get("exp"))
    if exp is None or exp < now():
        return out | {"why": "credential purana (expire)"}
    body = {k: v for k, v in cred.items() if k != "sig"}
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from . import federation as fed
        key = fed.server_public_key() if iss == idn.domain().lower() else fed._remote_card(iss)["server_key"]
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key)).verify(base64.b64decode(str(cred["sig"])), _canon(body))
    except Exception:
        STATS["checked_bad"] += 1
        return out | {"why": "signature nahi mila"}
    if iss == idn.domain().lower():                     # our own server: still verified right now?
        t = idn.tenant_of(subject)
        from .business import Business
        with session() as s:
            b = s.get(Business, t) if t else None
            if b is None or b.verification != "verified":
                STATS["checked_bad"] += 1
                return out | {"why": "verification wapas li gayi"}
    STATS["checked_ok"] += 1
    return {"ok": True, "name": str(cred.get("name") or "")[:120], "upi": str(cred.get("upi") or ""), "issuer": iss,
            "gstin": str(cred.get("gstin") or ""), "udyam": str(cred.get("udyam") or ""), "exp": str(cred.get("exp") or ""),
            "why": ""}


def payee_ok(vbc: dict[str, Any] | None, upi_id: str) -> bool:
    """The payee is the one the verifier matched to the bank account (credential checked, same UPI ID)."""
    return bool(vbc and vbc.get("ok") and vbc.get("upi") and str(vbc["upi"]).lower() == str(upi_id or "").lower())


def digest(cred: dict[str, Any] | None) -> str:
    return hashlib.sha256(_canon(cred or {})).hexdigest()[:16]
