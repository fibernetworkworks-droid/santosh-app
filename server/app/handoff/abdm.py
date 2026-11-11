"""v0.116 ABDM hand-off: Hoola explains health-record consents and reminds; she decides in her PHR app.

Hoola is NOT an ABDM consent manager, HIP or HIU (those need NHA certification), so it never receives, stores or reads a
health record, never approves a consent and never asks for an ABHA OTP. What it does:
  explain  ABHA number / ABHA address, Scan & Share at the hospital counter, linking records, consents, family members
           (topics in HELP), with the official places to do it (ABHA app / abha.abdm.gov.in).
  review   a consent request she sees in her PHR app (a hospital / doctor / lab / insurer asking for records): purpose
           (CAREMGT, BTG, PUBHLTH, HPAYMT, DSRCH, PATRQT), record types (OPConsultation, Prescription, DischargeSummary,
           DiagnosticReport, ImmunizationRecord, HealthDocumentRecord, WellnessRecord, Invoice), date range, expiry ->
           plain words + flags (research / public health = she may say no; very old records; long expiry).
  remember a tiny note (who asked, why, which record TYPES, dates, her decision) for whom (self / maa / papa ...), and
           reminds her to revoke in the PHR app once the visit / claim is over and before expiry.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from ..net import policy
from .aa import HandoffError, _date, _utc

PURPOSES = {
    "CAREMGT": "treatment (care management)",
    "BTG": "emergency (break the glass)",
    "PUBHLTH": "public health",
    "HPAYMT": "treatment bill / insurance claim (healthcare payment)",
    "DSRCH": "disease research",
    "PATRQT": "requested by you (self requested)",
}
HI_TYPES = {
    "OPConsultation": "OPD consultation note", "Prescription": "prescription", "DischargeSummary": "discharge summary",
    "DiagnosticReport": "lab / scan report", "ImmunizationRecord": "immunization record", "HealthDocumentRecord": "other health documents",
    "WellnessRecord": "wellness record (BP, sugar, weight...)", "Invoice": "hospital bill",
}
WHO = ("self", "maa", "papa", "pati", "patni", "beta", "beti", "bhai", "behen", "dada", "dadi", "nana", "nani", "other")
WHO_SAY = {"maa": "mother", "papa": "father", "pati": "husband", "patni": "wife", "beta": "son", "beti": "daughter",
           "bhai": "brother", "behen": "sister", "dada": "grandfather", "dadi": "grandmother", "nana": "grandfather",
           "nani": "grandmother", "other": "family member"}
STATS = {"reviews": 0, "reminders": 0}

HELP = {
    "abha": ["The ABHA number is a 14-digit health ID; the ABHA address (like name@abdm) is the identity linked to it.",
             "To create one: in the ABHA app or on abha.abdm.gov.in, with Aadhaar or a Driving Licence. The OTP comes to your phone; "
             "enter it only in that app / site, never give it to Hoola.",
             "Once you have it, you can keep the ABHA number in Hoola's ID Locker (it is shown masked)."],
    "scan_share": ["The hospital's registration counter has an ABDM QR code.",
                   "Scan the QR with 'Scan & Share' in the ABHA app (or any ABDM PHR app): your profile (name, age, "
                   "ABHA) goes to the counter and you get a token number.",
                   "You spend less time in the queue; reports can be linked to your ABHA."],
    "link": ["The hospital / lab 'links' your report to your ABHA; it shows under 'My Records' in the ABHA app.",
             "Old records: use 'Link records' in the app / search the hospital's name, with a mobile OTP (in the app)."],
    "consent": ["When a doctor / hospital wants to see your records, a consent request arrives in the ABHA app.",
                "Check in it: who, why (purpose), which records, how old, until when.",
                "Approve / Deny there. Later you can Revoke any time under 'Consents'.",
                "Hoola will explain the request and remind you to revoke; the decision is yours."],
    "family": ["You can create an ABHA for children / elders too ('family' / linked profiles in the ABHA app).",
               "You can also see their consents in the app on their behalf."],
    "privacy": ["Creating an ABHA is not mandatory; you get treatment without one too.",
                "Without consent, records are not shared. Even in an emergency (BTG) you can see later who looked."],
}


class HealthConsent(Base):
    """Her note of one ABDM consent request: who, why, record TYPES, dates, decision. Never a record's content."""
    __tablename__ = "handoff_health_consents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    for_whom: Mapped[str] = mapped_column(String(10), default="self")
    requester: Mapped[str] = mapped_column(String(160), default="")
    purpose: Mapped[str] = mapped_column(String(10), default="")
    hi_types: Mapped[list] = mapped_column(JSON, default=list)
    terms: Mapped[dict] = mapped_column(JSON, default=dict)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10), default="reviewed")       # reviewed | approved | denied | revoked | expired
    remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminded: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _purpose(x: Any) -> str:
    k = str(x or "").upper().replace(" ", "")
    words = {"CARE": "CAREMGT", "TREATMENT": "CAREMGT", "ILAAJ": "CAREMGT", "EMERGENCY": "BTG", "BREAKTHEGLASS": "BTG",
             "PUBLICHEALTH": "PUBHLTH", "PAYMENT": "HPAYMT", "INSURANCE": "HPAYMT", "CLAIM": "HPAYMT", "RESEARCH": "DSRCH",
             "SELF": "PATRQT"}
    return k if k in PURPOSES else words.get(k, "")


def _types(raw: Any) -> list[str]:
    if isinstance(raw, str):
        raw = [x.strip() for x in raw.replace("/", ",").split(",")]
    low = {k.lower(): k for k in HI_TYPES}
    alias = {"prescription": "Prescription", "parchi": "Prescription", "lab": "DiagnosticReport", "report": "DiagnosticReport",
             "discharge": "DischargeSummary", "opd": "OPConsultation", "vaccine": "ImmunizationRecord",
             "teeka": "ImmunizationRecord", "bill": "Invoice", "all": "*", "sab": "*"}
    out: list[str] = []
    for x in raw or []:
        k = str(x or "").strip()
        v = low.get(k.lower()) or alias.get(k.lower())
        if v == "*":
            return list(HI_TYPES)
        if v and v not in out:
            out.append(v)
    return out


def review(tenant: str, requester: str = "", purpose: str = "", hi_types: Any = None, data_from: Any = None,
           data_to: Any = None, expiry: Any = None, for_whom: str = "self", visit: str = "") -> dict[str, Any]:
    p = _purpose(purpose)
    types = _types(hi_types)
    df, dt, exp = _date(data_from), _date(data_to), _date(expiry)
    req = policy.clean_name(requester, 120)
    who = for_whom if for_whom in WHO else "self"
    flags: list[dict[str, str]] = []

    def flag(level: str, say: str) -> None:
        flags.append({"level": level, "say": say})

    if not req:
        flag("warn", "It is not clear who is asking. Check the hospital / doctor's name in the PHR app.")
    if not p:
        flag("warn", "The reason (purpose) is not clear; read the purpose written in the app.")
    elif p in ("DSRCH", "PUBHLTH"):
        flag("warn", f"This is for {PURPOSES[p]}, not for your treatment. You have the right to refuse.")
    elif p == "BTG":
        flag("info", "Emergency access: you can see later in the app who looked at what.")
    if len(types) >= 6:
        flag("warn", "They are asking for almost all records; give only what this visit needs (such as a report / prescription).")
    if df and (date.today() - df).days > 3 * 365:
        flag("warn", f"They are asking for records going back to {df.year}; recent records are usually enough for treatment.")
    if exp:
        left = (exp - date.today()).days
        if left < 0:
            flag("warn", "The expiry date of this request has passed.")
        elif left > 30:
            flag("warn", f"They will be able to look for {left} days; 7-30 days is usually enough for one visit / claim.")
    verdict = "check" if any(f["level"] == "warn" for f in flags) else "ok"
    terms = {"data_from": df.isoformat() if df else "", "data_to": dt.isoformat() if dt else "",
             "expiry": exp.isoformat() if exp else "", "visit": policy.quote(visit, 160)}
    with session() as s:
        r = HealthConsent(id=new_id("hc"), tenant_id=tenant, for_whom=who, requester=req, purpose=p, hi_types=types,
                          terms=terms, flags=flags, status="reviewed", created_at=now(), updated_at=now())
        s.add(r)
        s.flush()
        v = view(r)
    STATS["reviews"] += 1
    plain = (f"{req or 'Someone'} wants to see {('your' if who == 'self' else 'your ' + WHO_SAY.get(who, who) + chr(39) + 's')} " +
             (", ".join(HI_TYPES[t] for t in types) if types else "health records") +
             (f", reason: {PURPOSES[p]}" if p else "") + (f", until {exp.strftime('%d %b %Y')}" if exp else "") + ".")
    return {"consent": v, "plain": plain, "verdict": verdict,
            "say": ("This looks fine. " if verdict == "ok" else "Look at this carefully. ") +
                   "You Approve / Deny in the ABHA app; Hoola does not see any record.",
            "steps": HELP["consent"]}


def view(r: HealthConsent) -> dict[str, Any]:
    return {"id": r.id, "for_whom": r.for_whom, "requester": r.requester, "purpose": r.purpose,
            "purpose_say": PURPOSES.get(r.purpose, ""), "hi_types": r.hi_types or [],
            "hi_say": [HI_TYPES.get(t, t) for t in r.hi_types or []], "terms": r.terms or {}, "flags": r.flags or [],
            "status": r.status, "remind_at": _utc(r.remind_at).isoformat() if r.remind_at else "",
            "created_at": _utc(r.created_at).isoformat()}


def mark(tenant: str, cid: str, status: str, revoke_after_days: Any = None) -> dict[str, Any]:
    if status not in ("approved", "denied", "revoked"):
        raise HandoffError("status: approved | denied | revoked")
    with session() as s:
        r = s.get(HealthConsent, cid)
        if r is None or r.tenant_id != tenant:
            raise HandoffError("This consent was not found.")
        r.status, r.updated_at = status, now()
        r.remind_at = None
        if status == "approved":
            try:
                days = int(revoke_after_days) if revoke_after_days not in (None, "") else 7
            except (TypeError, ValueError):
                days = 7
            due = now() + timedelta(days=max(1, days))
            exp = _date((r.terms or {}).get("expiry"))
            if exp:
                due = min(due, datetime.combine(exp, datetime.min.time(), tzinfo=timezone.utc) - timedelta(days=1))
            r.remind_at = due
        s.flush()
        v = view(r)
    return {"consent": v, "say": {"approved": "OK. I will remind you to revoke after the visit.", "denied": "OK, no records went.",
                                  "revoked": "Good, they can no longer see the records."}[status]}


def consents(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [view(r) for r in s.scalars(select(HealthConsent).where(HealthConsent.tenant_id == tenant)
                                           .order_by(HealthConsent.updated_at.desc()).limit(60)).all()]


def forget(tenant: str, cid: str) -> dict[str, Any]:
    with session() as s:
        r = s.get(HealthConsent, cid)
        if r is None or r.tenant_id != tenant:
            raise HandoffError("This consent was not found.")
        s.delete(r)
    return {"status": "deleted"}


def explain(topic: str = "") -> dict[str, Any]:
    t = (topic or "").lower()
    key = next((k for k in HELP if k in t), "") or {"scan": "scan_share", "qr": "scan_share", "token": "scan_share",
                                                   "record": "link", "report": "link", "parivaar": "family",
                                                   "bachch": "family", "id": "abha", "number": "abha"}.get(
        next((w for w in ("scan", "qr", "token", "record", "report", "parivaar", "bachch", "id", "number") if w in t), ""), "")
    if not key:
        return {"topics": list(HELP), "say": "ABHA, Scan & Share, linking records, consent, family, privacy: which one?"}
    return {"topic": key, "steps": HELP[key], "official": ["ABHA app (NHA)", "https://abha.abdm.gov.in"],
            "say": "You do this in the official ABHA app / site; the OTP goes only there."}


def tick() -> int:
    n = 0
    out = []
    with session() as s:
        for r in s.scalars(select(HealthConsent).where(HealthConsent.status == "approved")).all():
            exp = _date((r.terms or {}).get("expiry"))
            if exp and exp < date.today():
                r.status, r.remind_at, r.updated_at = "expired", None, now()
                continue
            if r.remind_at is not None and _utc(r.remind_at) <= now() and "revoke" not in (r.reminded or []):
                r.reminded, r.remind_at = list(r.reminded or []) + ["revoke"], None
                out.append((r.tenant_id, view(r)))
    for tenant, v in out:
        n += 1
        STATS["reminders"] += 1
        from ..net.service import tell
        tell(tenant, "handoff_reminder", {"rail": "abdm", "consent": v,
                                          "say": f"{v['requester'] or 'Hospital'} can still see the health records. "
                                                 "When it is no longer needed, revoke the consent in the ABHA app."})
    return n
