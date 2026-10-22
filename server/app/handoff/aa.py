"""v0.116 Account Aggregator hand-off: Hoola reads an AA consent request WITH her and hands her to her AA app.

Hoola is not an FIU (only RBI / SEBI / IRDAI / PFRDA regulated entities are) and not an AA, so no financial data ever
comes to Hoola through AA. What it does:
  review   the consent request she sees (from her words / a screenshot read by file_read): who asks (FIU), why, which
           accounts (FI types), how far back, one-time or repeated, view or store, how long they keep it, until when.
           Compared with what that purpose usually needs -> plain-words flags + verdict ok | check | avoid. Fields
           follow the ReBIT consent artefact (purpose code, fiTypes, FIDataRange, fetchType, Frequency, consentMode,
           DataLife, consentExpiry). The usual needs are Hoola's rules of thumb, said as such.
  hand-off the steps in her own AA app (approve / reject there; revoke any time there) + Play Store links.
  remember a small record (who, why, dates, her decision; no account numbers, no data) and remind her to revoke once
           the purpose is over, and before expiry.
A loan "agent" / DSA must never be the one holding her AA consent: consent goes to the lender itself (RBI digital
lending: a lending service provider never handles the money, and her data goes to the regulated lender).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from ..net import policy

PURPOSES = {
    "101": "Wealth management service",
    "102": "Customer spending patterns, budget or other reportings",
    "103": "Aggregated statement",
    "104": "Explicit consent to monitor the account (e.g. a running loan)",
    "105": "Explicit one-time consent for accessing data from the accounts",
}
FI_TYPES = {
    "DEPOSIT": "bank account (savings / current)", "TERM_DEPOSIT": "FD", "RECURRING_DEPOSIT": "RD",
    "SIP": "SIP", "CP": "commercial paper", "GOVT_SECURITIES": "sarkari bond", "EQUITIES": "shares",
    "BONDS": "bonds", "DEBENTURES": "debentures", "MUTUAL_FUNDS": "mutual funds", "ETF": "ETF", "IDR": "IDR",
    "CIS": "CIS", "AIF": "AIF", "INSURANCE_POLICIES": "insurance policies", "LIFE_INSURANCE": "life insurance",
    "GENERAL_INSURANCE": "general insurance", "NPS": "NPS", "INVIT": "InvIT", "REIT": "REIT",
    "GSTR1_3B": "GST returns (GSTR-1 / 3B)", "OTHER": "doosre accounts",
}
INVEST = {"SIP", "EQUITIES", "BONDS", "DEBENTURES", "MUTUAL_FUNDS", "ETF", "GOVT_SECURITIES", "CP", "IDR", "CIS", "AIF",
          "NPS", "INVIT", "REIT"}
BANK = {"DEPOSIT", "TERM_DEPOSIT", "RECURRING_DEPOSIT"}
# what each purpose usually needs (Hoola's rule of thumb, told to her as such)
NEEDS = {
    "loan": {"say": "loan", "fi": BANK | {"GSTR1_3B"}, "months": 12, "fetch": "ONETIME", "life_days": 365, "expiry_days": 90},
    "loan_running": {"say": "chalte loan ki nigrani", "fi": BANK, "months": 12, "fetch": "PERIODIC", "life_days": 365,
                     "expiry_days": 366 * 5},
    "credit_card": {"say": "credit card", "fi": BANK, "months": 6, "fetch": "ONETIME", "life_days": 180, "expiry_days": 60},
    "insurance": {"say": "insurance", "fi": BANK | {"INSURANCE_POLICIES", "LIFE_INSURANCE", "GENERAL_INSURANCE"},
                  "months": 12, "fetch": "ONETIME", "life_days": 365, "expiry_days": 90},
    "wealth": {"say": "investment salah", "fi": BANK | INVEST | {"INSURANCE_POLICIES", "LIFE_INSURANCE"}, "months": 24,
               "fetch": "PERIODIC", "life_days": 365, "expiry_days": 366},
    "budget": {"say": "kharcha / budget app", "fi": BANK, "months": 12, "fetch": "PERIODIC", "life_days": 365, "expiry_days": 366},
    "tax": {"say": "tax filing", "fi": BANK | INVEST | {"GSTR1_3B"}, "months": 15, "fetch": "ONETIME", "life_days": 180,
            "expiry_days": 60},
    "rent": {"say": "kiraya / job / verification", "fi": {"DEPOSIT"}, "months": 6, "fetch": "ONETIME", "life_days": 30,
             "expiry_days": 30},
    "other": {"say": "doosra kaam", "fi": BANK, "months": 12, "fetch": "ONETIME", "life_days": 365, "expiry_days": 90},
}
MODES = {"VIEW": "sirf dekhenge", "STORE": "apne paas rakhenge", "QUERY": "sawaal poochh kar dekhenge",
         "STREAM": "lagaatar lete rahenge"}
AA_APPS = [("OneMoney", "FinSec AA Solutions"), ("Finvu", "Cookiejar Technologies"), ("Anumati", "Perfios"),
           ("Saafe", "Dashboard Account Aggregation"), ("Setu AA", "Agya Technologies"), ("SurakshAA", "Protean"),
           ("INK", "Unacores"), ("CAMSfinserv", "CAMSFinServ"), ("NADL", "NESL Asset Data")]
STATUSES = ("reviewed", "approved", "rejected", "revoked", "expired")
STATS = {"reviews": 0, "avoid": 0, "reminders": 0}


class HandoffError(ValueError):
    pass


class AaConsent(Base):
    """Her note of one AA consent (no account numbers, no data): who asked, why, the terms, her decision, reminders."""
    __tablename__ = "handoff_aa_consents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aac"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    requester: Mapped[str] = mapped_column(String(160), default="")
    for_what: Mapped[str] = mapped_column(String(20), default="other")
    terms: Mapped[dict] = mapped_column(JSON, default=dict)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    verdict: Mapped[str] = mapped_column(String(8), default="check")
    aa_app: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(10), default="reviewed")
    remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminded: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _date(x: Any) -> date | None:
    if not x:
        return None
    if isinstance(x, date):
        return x
    s = str(x).strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


_UNIT_DAYS = {"HOUR": 1 / 24, "DAY": 1, "DAYS": 1, "MONTH": 30, "MONTHS": 30, "YEAR": 365, "YEARS": 365, "INF": 99999,
              "DIN": 1, "MAHINA": 30, "MAHINE": 30, "SAAL": 365, "VARSH": 365, "WEEK": 7, "HAFTA": 7}


def _span_days(x: Any) -> float | None:
    """'1 YEAR', '6 months', {'unit': 'MONTH', 'value': 6}, 'INF', 180 -> days."""
    if x in (None, ""):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, dict):
        u, v = str(x.get("unit") or "").upper(), x.get("value")
        if u == "INF":
            return 99999.0
        try:
            return float(v) * _UNIT_DAYS.get(u, 1)
        except (TypeError, ValueError):
            return None
    s = str(x).strip().upper()
    if s in ("INF", "INFINITE", "HAMESHA", "FOREVER"):
        return 99999.0
    m = re.match(r"(\d+(?:\.\d+)?)\s*([A-Z]+)?", s)
    if not m:
        return None
    u = m.group(2) or "DAY"
    return float(m.group(1)) * _UNIT_DAYS.get(u, _UNIT_DAYS.get(u.rstrip("S"), 1))


def _per_day(freq: Any) -> float | None:
    """'1/MONTH', {'unit': 'DAY', 'value': 4}, 'daily' -> fetches per day."""
    if freq in (None, ""):
        return None
    if isinstance(freq, dict):
        try:
            return float(freq.get("value") or 1) / max(_UNIT_DAYS.get(str(freq.get("unit") or "DAY").upper(), 1), 1 / 24)
        except (TypeError, ValueError):
            return None
    s = str(freq).strip().upper()
    words = {"DAILY": 1, "ROZ": 1, "WEEKLY": 1 / 7, "MONTHLY": 1 / 30, "MAHINE": 1 / 30, "YEARLY": 1 / 365, "HOURLY": 24}
    if s in words:
        return words[s]
    m = re.match(r"(\d+)\s*/?\s*(?:PER\s+)?([A-Z]+)", s)
    if not m:
        return None
    return float(m.group(1)) / max(_UNIT_DAYS.get(m.group(2), 1), 1 / 24)


def _fi(raw: Any) -> list[str]:
    if isinstance(raw, str):
        raw = re.split(r"[,\s/]+", raw)
    out = []
    for x in raw or []:
        k = str(x or "").strip().upper().replace(" ", "_").replace("-", "_")
        k = {"BANK": "DEPOSIT", "SAVINGS": "DEPOSIT", "FD": "TERM_DEPOSIT", "RD": "RECURRING_DEPOSIT", "MF": "MUTUAL_FUNDS",
             "SHARES": "EQUITIES", "STOCKS": "EQUITIES", "INSURANCE": "INSURANCE_POLICIES", "GST": "GSTR1_3B"}.get(k, k)
        if k in FI_TYPES and k not in out:
            out.append(k)
    return out


def review(tenant: str, requester: str = "", for_what: str = "other", purpose_code: str = "", fi_types: Any = None,
           data_from: Any = None, data_to: Any = None, months: Any = None, fetch_type: str = "", frequency: Any = None,
           consent_mode: str = "", data_life: Any = None, expiry: Any = None, aa_app: str = "", text: str = "") -> dict[str, Any]:
    """Check one AA consent request against what its purpose usually needs. Saves her note; never approves anything."""
    fw = for_what if for_what in NEEDS else "other"
    need = NEEDS[fw]
    fis = _fi(fi_types)
    code = re.sub(r"\D", "", str(purpose_code or ""))[:3]
    df, dt = _date(data_from), _date(data_to)
    rng = None
    if df and dt:
        rng = max(0.0, (dt - df).days / 30.4)
    elif months not in (None, ""):
        try:
            rng = float(months)
        except (TypeError, ValueError):
            rng = None
    ft = str(fetch_type or "").upper().replace("-", "_")
    ft = "PERIODIC" if ft in ("PERIODIC", "REPEAT", "RECURRING", "BAAR_BAAR") else ("ONETIME" if ft in ("ONETIME", "ONE_TIME", "ONCE", "EK_BAAR") else "")
    cm = str(consent_mode or "").upper()
    cm = cm if cm in MODES else ""
    life = _span_days(data_life)
    exp = _date(expiry)
    exp_days = (exp - date.today()).days if exp else None
    perday = _per_day(frequency)
    req = policy.clean_name(requester, 120)
    flags: list[dict[str, str]] = []

    def flag(level: str, say: str) -> None:
        flags.append({"level": level, "say": say})

    if not req:
        flag("warn", "Kaun maang raha hai, yeh nahi pata. AA app mein FIU (bank / NBFC / company) ka naam aur uska regulator dekhiye.")
    elif re.search(r"\b(agent|dsa|broker|consultant|loan\s*wala|app\s*wala)\b", req, re.I):
        flag("avoid", "Consent kisi agent / DSA ke naam par nahi, seedha lender (bank / NBFC) ke naam hona chahiye.")
    if code and code not in PURPOSES:
        flag("warn", f"Purpose code {code} jaana-pehchaana nahi. AA app mein likha kaaran dhyaan se padhiye.")
    extra = [f for f in fis if f not in need["fi"]]
    if extra:
        lvl = "avoid" if fw in ("rent", "credit_card") and any(f in INVEST for f in extra) else "warn"
        flag(lvl, f"{need['say'].capitalize()} ke liye yeh zaroori nahi lagte: {', '.join(FI_TYPES[f] for f in extra)}. "
                  "AA app mein inka tick hata sakti hain, ya poochhiye kyun chahiye.")
    if rng is not None and rng > need["months"] + 0.5:
        flag("warn", f"{rng:.0f} mahine purana data maang rahe hain; {need['say']} ke liye aam taur par {need['months']} mahine kaafi hai.")
    if ft == "PERIODIC" and need["fetch"] == "ONETIME":
        flag("warn", f"Baar-baar (PERIODIC) data lenge, jabki {need['say']} ke liye ek baar (ONETIME) kaafi hai.")
    if perday is not None and perday > 1.01:
        flag("warn", f"Din mein {perday:.0f} baar data lenge; itna aam taur par nahi chahiye.")
    if cm in ("STORE", "STREAM") and life is not None and life > need["life_days"]:
        flag("avoid" if life > 730 else "warn", f"Data apne paas {('hamesha' if life >= 99999 else f'{life / 30.4:.0f} mahine')} rakhenge; "
                                                f"{need['say']} ke liye {need['life_days'] // 30} mahine se zyada ki zaroorat nahi lagti.")
    if exp_days is not None:
        if exp_days < 0:
            flag("warn", "Is consent ki aakhri tareekh beet chuki hai.")
        elif exp_days > need["expiry_days"] + 5:
            flag("warn", f"Consent {exp_days} din tak chalega; {need['say']} ke liye aam taur par {need['expiry_days']} din kaafi.")
    if text and policy.secret_found(text):
        flag("avoid", "Is message mein OTP / PIN jaisa kuch hai. AA consent ke liye OTP sirf AA app mein daaliye, kisi ko mat bataiye.")
    verdict = "avoid" if any(f["level"] == "avoid" for f in flags) else ("check" if flags else "ok")
    see = [FI_TYPES[f] for f in fis] or ["jo accounts aap chunengi"]
    plain = (f"{req or 'Maangne wala'} aapke {', '.join(see)} ka " +
             (f"pichhle {rng:.0f} mahine ka " if rng else "") + "data " +
             ("ek baar " if ft == "ONETIME" else ("baar-baar " if ft == "PERIODIC" else "")) +
             (MODES.get(cm, "") + " " if cm else "") + "chahte hain" +
             (f" ({PURPOSES[code]})" if code in PURPOSES else "") + ".")
    terms = {"purpose_code": code, "purpose": PURPOSES.get(code, ""), "fi_types": fis, "months": rng,
             "data_from": df.isoformat() if df else "", "data_to": dt.isoformat() if dt else "", "fetch_type": ft,
             "per_day": perday, "consent_mode": cm, "data_life_days": life, "expiry": exp.isoformat() if exp else ""}
    with session() as s:
        row = AaConsent(id=new_id("aac"), tenant_id=tenant, requester=req, for_what=fw, terms=terms, flags=flags,
                        verdict=verdict, aa_app=policy.clean_name(aa_app, 40), status="reviewed",
                        note=policy.quote(text, 600), created_at=now(), updated_at=now())
        s.add(row)
        s.flush()
        v = view(row)
    STATS["reviews"] += 1
    if verdict == "avoid":
        STATS["avoid"] += 1
    say = {"ok": "Yeh consent apne kaam ke hisaab se theek lagta hai.",
           "check": "Kuch baatein zyada maangi gayi hain; dekh kar hi haan kariye.",
           "avoid": "Is consent mein khatre ki baat hai; mana karna behtar."}[verdict]
    return {"consent": v, "plain": plain, "say": say + " Faisla aap apne AA app mein karengi; Hoola kuch approve nahi karta.",
            "steps": steps(aa_app), "rule_of_thumb": "Yeh Hoola ka aam andaaza hai, kanooni seema nahi."}


def steps(aa_app: str = "") -> list[str]:
    app = policy.clean_name(aa_app, 40) or "apne Account Aggregator app"
    return [f"{app} kholiye (jis AA se SMS / link aaya).",
            "Consent request mein 'kaun', 'kyun', 'kaunse account', 'kitne din ka data' aur 'kab tak' dekhiye.",
            "Jo account zaroori nahi, unka tick hataiye (agar app deta hai).",
            "Theek ho to Approve, nahi to Reject. OTP / PIN sirf AA app mein, kisi ko mat bataiye.",
            "Kaam ho jaaye (loan ka faisla, report mil gayi) to AA app mein Consent > Revoke kar dijiye.",
            "Hoola ko batayiye kya kiya ('approve kar diya' / 'mana kiya'); woh revoke yaad dila dega."]


def apps() -> list[dict[str, str]]:
    from urllib.parse import quote
    return [{"name": n, "company": c, "play": f"https://play.google.com/store/search?q={quote(n + ' account aggregator')}&c=apps"}
            for n, c in AA_APPS]


def view(r: AaConsent) -> dict[str, Any]:
    return {"id": r.id, "requester": r.requester, "for_what": r.for_what, "for_say": NEEDS.get(r.for_what, NEEDS["other"])["say"],
            "terms": r.terms or {}, "flags": r.flags or [], "verdict": r.verdict, "aa_app": r.aa_app, "status": r.status,
            "remind_at": _utc(r.remind_at).isoformat() if r.remind_at else "", "created_at": _utc(r.created_at).isoformat()}


def mark(tenant: str, cid: str, status: str, revoke_after_days: Any = None) -> dict[str, Any]:
    """She tells Hoola what she did in her AA app (approved / rejected / revoked). Approved -> a revoke reminder."""
    if status not in ("approved", "rejected", "revoked"):
        raise HandoffError("status: approved | rejected | revoked")
    with session() as s:
        r = s.get(AaConsent, cid)
        if r is None or r.tenant_id != tenant:
            raise HandoffError("Yeh consent nahi mila.")
        r.status, r.updated_at = status, now()
        if status == "approved":
            try:
                days = int(revoke_after_days) if revoke_after_days not in (None, "") else (30 if NEEDS.get(r.for_what, NEEDS["other"])["fetch"] == "ONETIME" else 0)
            except (TypeError, ValueError):
                days = 30
            exp = _date((r.terms or {}).get("expiry"))
            due = now() + timedelta(days=days) if days else None
            if exp:
                before = datetime.combine(exp, datetime.min.time(), tzinfo=timezone.utc) - timedelta(days=3)
                due = min(due, before) if due else before
            r.remind_at = due
        else:
            r.remind_at = None
        s.flush()
        v = view(r)
    say = {"approved": "Theek hai. " + (f"{v['remind_at'][:10]} ko revoke yaad dila dunga." if v["remind_at"] else ""),
           "rejected": "Theek, mana kar diya. Data nahi jaayega.", "revoked": "Badhiya, consent band. Aage data nahi jaayega."}[status]
    return {"consent": v, "say": say.strip()}


def consents(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [view(r) for r in s.scalars(select(AaConsent).where(AaConsent.tenant_id == tenant)
                                           .order_by(AaConsent.updated_at.desc()).limit(60)).all()]


def forget(tenant: str, cid: str) -> dict[str, Any]:
    with session() as s:
        r = s.get(AaConsent, cid)
        if r is None or r.tenant_id != tenant:
            raise HandoffError("Yeh consent nahi mila.")
        s.delete(r)
    return {"status": "deleted"}


def tick() -> int:
    """Revoke reminders (once) and expired consents."""
    n = 0
    out: list[tuple[str, dict[str, Any]]] = []
    with session() as s:
        for r in s.scalars(select(AaConsent).where(AaConsent.status == "approved")).all():
            exp = _date((r.terms or {}).get("expiry"))
            if exp and exp < date.today():
                r.status, r.remind_at, r.updated_at = "expired", None, now()
                continue
            if r.remind_at is not None and _utc(r.remind_at) <= now() and "revoke" not in (r.reminded or []):
                r.reminded = list(r.reminded or []) + ["revoke"]
                r.remind_at = None
                out.append((r.tenant_id, view(r)))
    for tenant, v in out:
        n += 1
        STATS["reminders"] += 1
        from ..net.service import NetError, tell
        try:
            tell(tenant, "handoff_reminder", {"rail": "aa", "consent": v,
                                              "say": f"{v['requester'] or 'AA'} ka consent ({v['for_say']}) ab bhi chalu hai. "
                                                     "Kaam ho gaya ho to AA app mein Revoke kar dijiye."})
        except NetError:
            pass
    return n
