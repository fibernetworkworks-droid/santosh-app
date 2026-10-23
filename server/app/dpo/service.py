"""DPO Sahayak: Hoola as the business's data protection officer under the DPDP Act 2023 + DPDP Rules 2025.

Records of processing (pre-filled from the Hoola modules she really uses) -> privacy notice (Rule 3) in hi / mr / en -> consent
records + withdrawal -> rights requests with the 90-day clock (Rule 14(3)), identity checked by METHOD + reference only, reply
drafts, erasure through the modules' own forget functions -> breach register: Board intimation (Rule 7(2)(a)), 72-hour report
(Rule 7(2)(b)), intimation to people (Rule 7(1)), CERT-In 6-hour clock through the IT Helpdesk incident -> DPIA + processor (DPA)
checklist -> children (verifiable parental consent) flags -> retention review.

Publishing a notice, replying to a person, erasing data and every breach notice are CARDS: only her app tap
(POST /api/dpo/cards/{id}/decide {yes, hash}) decides them; erasure also needs her phone's fingerprint once a phone key is active.
Hoola files nothing on any portal and is not a lawyer: everything is a draft for her lawyer / CA / CS."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
import threading
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import func, inspect, select, text

from ..db import now, session
from . import rules as R
from .models import (DpoActivity, DpoAlert, DpoBreach, DpoCard, DpoConsent, DpoNotice, DpoRequest, DpoSettings,
                     DpoVendor)

log = logging.getLogger("santosh.dpo")
_LOCK = threading.RLock()

CARD_KINDS = {"notice": "Privacy notice publish", "reply": "Jawab bhejna", "erase": "Data mitaana",
              "breach_initial": "Board ko pehli soochna", "breach_report": "Board ko 72 ghante ki report",
              "breach_people": "Prabhavit logon ko soochna"}


class DpoError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str, sort_keys=True)


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def clock() -> datetime:
    return now()


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return clock().astimezone(_tz(tenant)).date()


def _local(tenant: str, d: datetime | None) -> str:
    d = _aware(d)
    return R.fmt_dt(d.astimezone(_tz(tenant))) if d else ""


def _date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s[:10], f).date()
        except ValueError:
            pass
    return None


def _when(tenant: str, v) -> datetime | None:
    """Her local date-time words -> aware UTC ('2026-10-23 14:30', '23-10-2026 2:30 pm', 'abhi' / '' = now)."""
    s = str(v or "").strip().lower()
    if not s or s in ("abhi", "now", "aaj", "today"):
        return clock()
    if isinstance(v, datetime):
        return _aware(v)
    m = re.match(r"(\d{1,4}[-/.]\d{1,2}[-/.]\d{2,4})(?:[ t,]+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?", s)
    if not m:
        return None
    d = _date(m.group(1))
    if d is None:
        return None
    hh, mm = int(m.group(2) or 0), int(m.group(3) or 0)
    if m.group(4) == "pm" and hh < 12:
        hh += 12
    if m.group(4) == "am" and hh == 12:
        hh = 0
    try:
        loc = datetime.combine(d, time(hh, mm), tzinfo=_tz(tenant))
    except ValueError:
        return None
    return loc.astimezone(timezone.utc)


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("dpo publish failed")


def is_owner(actor: str) -> bool:
    a = actor or "owner"
    return a == "owner" or a.startswith("approved:")


def actor_name(tenant: str, actor: str) -> str:
    if is_owner(actor):
        return "Owner"
    try:
        from ..employee.service import actor_label
        return actor_label(tenant, actor)
    except Exception:
        return (actor or "")[:40]


def _need_owner(actor: str) -> None:
    if not is_owner(actor):
        raise DpoError("Yeh sirf owner kar sakti hain.")


def _st(s, tenant: str) -> DpoSettings:
    r = s.get(DpoSettings, tenant)
    if r is None:
        r = DpoSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _next(st: DpoSettings, kind: str) -> int:
    seq = _j(st.seq, {})
    seq[kind] = int(seq.get(kind, 0)) + 1
    st.seq = _dump(seq)
    return seq[kind]


def _hash(v) -> str:
    return hashlib.sha256(_dump(v).encode()).hexdigest()


def _list(v) -> list[str]:
    if isinstance(v, str):
        v = [x for x in re.split(r"[,\n;]", v)]
    return [R.scrub(x, 120) for x in (v or []) if str(x).strip()][:40]


def _contact(st: DpoSettings) -> str:
    bits = [st.contact_name, st.contact_email, st.contact_phone]
    return ", ".join(b for b in bits if b)


def _wa(phone: str, msg: str) -> str:
    from urllib.parse import quote
    p = R.phone10(phone)
    return f"https://wa.me/91{p}?text={quote(msg)}" if p else ""


def _mailto(email: str, subject: str, body: str) -> str:
    from urllib.parse import quote
    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}" if email and "@" in email else ""


# ---------------------------------------------------------------- settings
_SET_KEYS = ("org", "contact_name", "contact_email", "contact_phone", "link", "identifiers", "reply_days", "languages", "sdf",
             "third_schedule", "morning_time", "rules")


def _settings_view(r: DpoSettings) -> dict:
    return {"org": r.org, "contact_name": r.contact_name, "contact_email": r.contact_email, "contact_phone": r.contact_phone,
            "link": r.link, "identifiers": r.identifiers, "reply_days": r.reply_days, "languages": r.languages, "sdf": r.sdf,
            "third_schedule": r.third_schedule, "morning_time": r.morning_time, "rules": r.rules}


def settings(tenant: str) -> dict:
    with session() as s:
        r = _st(s, tenant)
        v = _settings_view(r)
    v["missing"] = [k for k, lbl in (("org", "business ka naam"), ("contact_email", "jawab dene wale ka email"),
                                     ("link", "consent wapas / maang ka link")) if not v[k]]
    v["phases"] = R.phase_notes(today(tenant))
    v["sdf_note"] = ("Significant Data Fiduciary: India mein DPO, saalana DPIA aur audit (s.10, Rule 13)." if v["sdf"] else
                     "Significant Data Fiduciary sirf sarkar notify karti hai; aam dukaan / business par woh extra niyam nahi.")
    return v


def save_settings(tenant: str, actor: str = "owner", **kw: Any) -> dict:
    _need_owner(actor)
    with session() as s:
        r = _st(s, tenant)
        for k in _SET_KEYS:
            if k not in kw or kw[k] is None:
                continue
            v = kw[k]
            if k == "reply_days":
                n = int(float(v or 0))
                if n < 1 or n > R.RIGHTS_DAYS:
                    raise DpoError(f"Jawab ke din 1 se {R.RIGHTS_DAYS} tak (kanoon mein zyada se zyada {R.RIGHTS_DAYS}).")
                r.reply_days = n
            elif k == "sdf":
                r.sdf = bool(v)
            elif k == "contact_phone":
                p = R.phone10(v)
                if v and not p:
                    raise DpoError("10 ank ka mobile.")
                r.contact_phone = p
            elif k == "contact_email":
                e = str(v).strip()
                if e and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e):
                    raise DpoError("Email sahi nahi.")
                r.contact_email = e[:120]
            elif k == "link":
                l = str(v).strip()
                if l and not l.startswith("https://"):
                    raise DpoError("Link https:// se shuru ho.")
                r.link = l[:300]
            elif k == "third_schedule":
                r.third_schedule = v if v in ("ecommerce", "gaming", "social", "") else ""
            elif k == "morning_time":
                r.morning_time = v if re.match(r"^\d{2}:\d{2}$", str(v)) else r.morning_time
            else:
                setattr(r, k, R.scrub(v, 400))
    return {"settings": settings(tenant), "say": "DPO niyam save."}


# ---------------------------------------------------------------- records of processing
def _tables(s) -> dict[str, set[str]]:
    ins = inspect(s.get_bind())
    out = {}
    for t in ins.get_table_names():
        try:
            out[t] = {c["name"] for c in ins.get_columns(t)}
        except Exception:
            out[t] = set()
    return out


def _count(s, tables: dict, table: str, tenant: str, older: datetime | None = None) -> int:
    cols = tables.get(table)
    if not cols or "tenant_id" not in cols:
        return 0
    q = f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :t"
    args: dict[str, Any] = {"t": tenant}
    if older is not None:
        if "created_at" not in cols:
            return 0
        q += " AND created_at < :o"
        args["o"] = older.replace(tzinfo=None)
    try:
        return int(s.execute(text(q), args).scalar() or 0)
    except Exception:
        return 0


def _act_view(a: DpoActivity, vendors: list[str] | None = None) -> dict:
    d = {"id": a.id, "number": a.number, "source": a.source, "name": a.name, "people": a.people, "items": _j(a.items, []),
         "purpose": a.purpose, "basis": a.basis, "basis_label": R.BASES.get(a.basis, a.basis), "retention": a.retention,
         "retention_days": a.retention_days, "processors": _j(a.processors, []), "children": a.children, "abroad": a.abroad,
         "law_hold": a.law_hold, "records": a.records, "status": a.status, "confirmed": a.confirmed, "dpia": _j(a.dpia, {}),
         "notes": a.notes}
    checks = []
    if not a.confirmed:
        checks.append("Hoola ne module se bhara hai: ek baar dekh kar 'sahi hai' kijiye.")
    if not a.purpose:
        checks.append("Kaam (purpose) likhiye.")
    if not a.retention:
        checks.append("Kitne samay rakhna hai, likhiye.")
    checks += R.child_flags(d)
    if a.abroad:
        checks.append("Data India ke bahar: sarkar ki rok wali desh list (s.16) dekhiye aur vendor ke contract mein desh likhwaiye.")
    if vendors is not None:
        for p in d["processors"]:
            if p and "hoola" not in p.lower() and not any(v.lower() in p.lower() or p.lower() in v.lower() for v in vendors):
                checks.append(f"Processor '{p}' ka contract (DPA) register mein nahi.")
    risky = a.children or a.abroad or any(w in " ".join(d["items"]).lower() for w in ("health", "bank", "pan", "aadhaar", "awaaz", "id "))
    if risky and not d["dpia"].get("level"):
        checks.append("Jokhim wala data: DPIA checklist bhariye.")
    d["checks"] = checks
    return d


def _vendor_names(s, tenant: str) -> list[str]:
    return [v.name for v in s.scalars(select(DpoVendor).where(DpoVendor.tenant_id == tenant)).all() if v.dpa_signed]


def scan(tenant: str, actor: str = "owner") -> dict:
    """Pre-fill the register from the Hoola modules she really uses (records counted, nothing read)."""
    added, seen = [], []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        tables = _tables(s)
        have = {a.source: a for a in s.scalars(select(DpoActivity).where(DpoActivity.tenant_id == tenant)).all()}
        for c in R.ROPA_CATALOG:
            n = sum(_count(s, tables, t, tenant) for t in c["tables"])
            if n <= 0:
                continue
            seen.append({"key": c["key"], "label": c["label"], "records": n})
            a = have.get(c["key"])
            if a is None:
                a = DpoActivity(tenant_id=tenant, number=f"PA-{_next(st, 'pa'):02d}", source=c["key"], name=c["label"], people=c["people"],
                                items=_dump(c["items"]), purpose=c["purpose"], basis=c["basis"], retention=c["retention"],
                                retention_days=c.get("days"), processors=_dump(c["processors"]), law_hold=bool(c.get("law_hold")))
                s.add(a)
                added.append(c["label"])
            a.records = n
            a.updated_at = now()
    say = (f"{len(seen)} module mein logon ka data mila; {len(added)} naye record bane (Hoola ka andaaza: har ek dekh kar 'sahi hai' kijiye)."
           if seen else "Abhi kisi module mein logon ka data nahi mila. Apna kaam khud jodiye.")
    return {"found": seen, "added": added, "say": say}


_ACT_KEYS = ("name", "people", "items", "purpose", "basis", "retention", "retention_days", "processors", "children", "abroad",
             "law_hold", "status", "notes", "confirmed")


def activity_save(tenant: str, ref: str = "", actor: str = "owner", **kw: Any) -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        if ref:
            a = _activity(s, tenant, ref)
        else:
            if not str(kw.get("name") or "").strip():
                raise DpoError("Kaam ka naam chahiye.")
            a = DpoActivity(tenant_id=tenant, number=f"PA-{_next(_st(s, tenant), 'pa'):02d}", source="own", confirmed=True)
            s.add(a)
        for k in _ACT_KEYS:
            if k not in kw or kw[k] is None:
                continue
            v = kw[k]
            if k in ("items", "processors"):
                setattr(a, k, _dump(_list(v)))
            elif k == "basis":
                if v not in R.BASES:
                    raise DpoError("Aadhaar: " + " / ".join(R.BASES))
                a.basis = v
            elif k == "retention_days":
                a.retention_days = int(float(v)) if v not in ("", None) else None
            elif k in ("children", "abroad", "law_hold", "confirmed"):
                setattr(a, k, bool(v))
            elif k == "status":
                a.status = "stopped" if v == "stopped" else "active"
            else:
                setattr(a, k, R.scrub(v, 600))
        a.updated_at = now()
        s.flush()
        return {"activity": _act_view(a, _vendor_names(s, tenant)), "say": f"{a.number} save."}


def _activity(s, tenant: str, ref: str) -> DpoActivity:
    a = s.get(DpoActivity, ref)
    if a is None or a.tenant_id != tenant:
        a = s.scalars(select(DpoActivity).where(DpoActivity.tenant_id == tenant, DpoActivity.number == str(ref).upper())).first()
    if a is None:
        raise DpoError("Record (PA-..) nahi mila.")
    return a


def activities(tenant: str) -> list[dict]:
    with session() as s:
        vn = _vendor_names(s, tenant)
        return [_act_view(a, vn) for a in s.scalars(select(DpoActivity).where(DpoActivity.tenant_id == tenant)
                                                    .order_by(DpoActivity.number)).all()]


def dpia(tenant: str, ref: str, answers: dict, actor: str = "owner") -> dict:
    _need_owner(actor)
    ans = {k: answers[k] for k, _, _ in R.DPIA_QUESTIONS if k in (answers or {})}
    score, level, notes = R.dpia_score(ans)
    with session() as s:
        a = _activity(s, tenant, ref)
        a.dpia = _dump({"answers": ans, "score": score, "level": level, "notes": notes, "on": today(tenant).isoformat()})
        if ans.get("children"):
            a.children = True
        if ans.get("abroad"):
            a.abroad = True
        v = _act_view(a, _vendor_names(s, tenant))
    lvl = {"low": "kam", "medium": "beech ka", "high": "zyada"}[level]
    return {"activity": v, "say": f"{v['number']} DPIA: jokhim {lvl} ({score}). " + ("; ".join(notes[:3]) if notes else "")}


# ---------------------------------------------------------------- vendors (processors) + DPA checklist
def _vendor_view(v: DpoVendor, on: date) -> dict:
    cl = _j(v.clauses, {})
    missing = [lbl for k, lbl in R.DPA_CLAUSES if not cl.get(k)]
    rv = _date(v.review_on)
    return {"id": v.id, "name": v.name, "service": v.service, "items": _j(v.items, []), "country": v.country, "dpa_signed": v.dpa_signed,
            "dpa_on": v.dpa_on, "review_on": v.review_on, "review_days": (rv - on).days if rv else None, "clauses": cl,
            "missing": missing, "file_id": v.file_id, "notes": v.notes,
            "abroad": bool(v.country) and v.country.strip().lower() not in ("india", "in", "bharat")}


def vendor_save(tenant: str, ref: str = "", actor: str = "owner", **kw: Any) -> dict:
    _need_owner(actor)
    with session() as s:
        v = s.get(DpoVendor, ref) if ref else None
        if ref and (v is None or v.tenant_id != tenant):
            v = s.scalars(select(DpoVendor).where(DpoVendor.tenant_id == tenant, DpoVendor.name == ref)).first()
        if v is None:
            if not str(kw.get("name") or "").strip():
                raise DpoError("Vendor ka naam chahiye.")
            v = DpoVendor(tenant_id=tenant)
            s.add(v)
        for k in ("name", "service", "country", "notes", "file_id"):
            if kw.get(k) is not None:
                setattr(v, k, R.scrub(kw[k], 200))
        if kw.get("items") is not None:
            v.items = _dump(_list(kw["items"]))
        if kw.get("dpa_signed") is not None:
            v.dpa_signed = bool(kw["dpa_signed"])
        for k in ("dpa_on", "review_on"):
            if kw.get(k):
                d = _date(kw[k])
                if not d:
                    raise DpoError(f"{k}: taarikh YYYY-MM-DD.")
                setattr(v, k, d.isoformat())
        if isinstance(kw.get("clauses"), dict):
            cl = _j(v.clauses, {})
            for k, _ in R.DPA_CLAUSES:
                if k in kw["clauses"]:
                    cl[k] = bool(kw["clauses"][k])
            v.clauses = _dump(cl)
        s.flush()
        out = _vendor_view(v, today(tenant))
    say = f"{out['name']} save." + (f" Contract mein {len(out['missing'])} baatein baaki." if out["missing"] else " Saare clause hain.")
    return {"vendor": out, "say": say}


def vendors(tenant: str) -> list[dict]:
    on = today(tenant)
    with session() as s:
        return [_vendor_view(v, on) for v in s.scalars(select(DpoVendor).where(DpoVendor.tenant_id == tenant).order_by(DpoVendor.name)).all()]


# ---------------------------------------------------------------- notice (Rule 3)
def _notice_view(n: DpoNotice) -> dict:
    return {"id": n.id, "version": n.version, "lang": n.lang, "lang_label": R.LANGS.get(n.lang, n.lang), "text": n.text,
            "status": n.status, "blanks": R.has_blank(n.text), "files": _j(n.files, []),
            "published_at": _aware(n.published_at).isoformat(timespec="minutes") if n.published_at else "",
            "activity_ids": _j(n.activity_ids, [])}


def notice_draft(tenant: str, lang: str = "hi", activity_ids: list | None = None, actor: str = "owner") -> dict:
    lang = lang if lang in R.LANGS else "hi"
    with _LOCK, session() as s:
        st = _st(s, tenant)
        q = select(DpoActivity).where(DpoActivity.tenant_id == tenant, DpoActivity.status == "active")
        acts = s.scalars(q.order_by(DpoActivity.number)).all()
        if activity_ids:
            acts = [a for a in acts if a.id in activity_ids or a.number in activity_ids]
        if not acts:
            raise DpoError("Pehle records of processing banaiye (scan / naya kaam).")
        ver = (s.scalar(select(func.max(DpoNotice.version)).where(DpoNotice.tenant_id == tenant, DpoNotice.lang == lang)) or 0) + 1
        views = [_act_view(a) for a in acts]
        txt = R.notice_text(lang, st.org, views, st.link, _contact(st), st.reply_days or R.RIGHTS_DAYS, ver, today(tenant))
        n = DpoNotice(tenant_id=tenant, version=ver, lang=lang, activity_ids=_dump([a.id for a in acts]), text=txt)
        s.add(n)
        s.flush()
        v = _notice_view(n)
        unconf = [a.number for a in acts if not a.confirmed]
    say = f"Notice v{ver} ({R.LANGS[lang]}) ka draft." + (" [____] bharne baaki (settings: naam / link / contact)." if v["blanks"] else "")
    if unconf:
        say += f" Records {', '.join(unconf)} abhi 'sahi hai' nahi kiye."
    return {"notice": v, "say": say + " " + R.DISCLAIMER}


def notice_edit(tenant: str, ref: str, text_: str, actor: str = "owner") -> dict:
    _need_owner(actor)
    with session() as s:
        n = s.get(DpoNotice, ref)
        if n is None or n.tenant_id != tenant:
            raise DpoError("Notice nahi mila.")
        if n.status not in ("draft", "rejected"):
            raise DpoError("Sirf draft badal sakte hain; naya draft banaiye.")
        n.text = str(text_ or "")[:20000]
        n.status = "draft"
        return {"notice": _notice_view(n), "say": "Notice badla."}


def notices(tenant: str) -> list[dict]:
    with session() as s:
        return [_notice_view(n) for n in s.scalars(select(DpoNotice).where(DpoNotice.tenant_id == tenant)
                                                   .order_by(DpoNotice.created_at.desc())).all()[:40]]


def notice_request(tenant: str, ref: str, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        n = s.get(DpoNotice, ref)
        if n is None or n.tenant_id != tenant:
            raise DpoError("Notice nahi mila.")
        if n.status not in ("draft", "rejected"):
            raise DpoError(f"Notice abhi '{n.status}' hai.")
        if R.has_blank(n.text):
            raise DpoError("Notice mein [____] baaki hain: pehle bhariye.")
        n.status = "waiting"
        data = {"lang": n.lang, "lang_label": R.LANGS.get(n.lang), "version": n.version, "text": n.text, "disclaimer": R.DISCLAIMER}
        c = _new_card(s, tenant, "notice", n.id, f"Privacy notice v{n.version} ({R.LANGS.get(n.lang)}) publish karein?", data,
                      _hash(_snapshot(s, "notice", n.id)), actor, conv)
        cv = _card_view(c)
    _publish(tenant, "dpo_card", {"card": cv, "say": cv["title"]}, conv)
    return {"card": cv, "say": "Notice ka card bheja: aapke tap ke baad hi publish (file banegi, aap website / app par lagaiye)."}


# ---------------------------------------------------------------- consents
def _consent_view(c: DpoConsent) -> dict:
    return {"id": c.id, "name": c.name, "phone": R.mask_phone(c.phone), "activities": _j(c.activity_ids, []),
            "notice_version": c.notice_version, "how": c.how, "proof": c.proof, "child": c.child, "parent_name": c.parent_name,
            "parent_check": c.parent_check, "given_at": _aware(c.given_at).isoformat(timespec="minutes") if c.given_at else "",
            "withdrawn_at": _aware(c.withdrawn_at).isoformat(timespec="minutes") if c.withdrawn_at else "",
            "withdraw_how": c.withdraw_how, "status": c.status}


def _id_free(txt: str, what: str) -> str:
    from .. import pii
    t = txt or ""
    hit = [x for x in pii.find(t) if x in ("aadhaar", "pan", "card", "bank_account", "otp_pin", "password")]
    if re.search(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b", t) or re.search(r"\b(?:\d[ -]?){11}\d\b", t):
        hit.append("id")
    if hit:
        raise DpoError(f"{what}: ID / bank number yahan mat likhiye, sirf tareeka aur reference (jaise 'DigiLocker se umar dekhi, "
                       f"ref 12-10'). ID number chahiye to Pehchaan Locker mein.")
    return R.scrub(txt, 200)


def consent_add(tenant: str, name: str = "", phone: str = "", activities_: list | None = None, how: str = "", proof: str = "",
                child: bool = False, parent_name: str = "", parent_check: str = "", notice_version: int | None = None,
                actor: str = "owner") -> dict:
    p = R.phone10(phone)
    if not (name or p):
        raise DpoError("Naam ya mobile chahiye.")
    if child and not (parent_name and parent_check):
        raise DpoError("Bachche (18 se kam) ka consent: maa-baap ka naam aur verify kaise kiya (Rule 10) pehle likhiye.")
    pc = _id_free(parent_check, "Parent verification")
    pr = _id_free(proof, "Proof")
    with session() as s:
        ids = []
        for r in (activities_ or []):
            try:
                ids.append(_activity(s, tenant, str(r)).id)
            except DpoError:
                pass
        c = DpoConsent(tenant_id=tenant, name=R.scrub(name, 120), phone=p, activity_ids=_dump(ids), how=R.scrub(how, 40), proof=pr,
                       child=bool(child), parent_name=R.scrub(parent_name, 120), parent_check=pc, notice_version=notice_version)
        s.add(c)
        s.flush()
        return {"consent": _consent_view(c), "say": "Consent darj." + (" (Bachcha: parent verification ke saath.)" if child else "")}


def consent_withdraw(tenant: str, ref: str = "", phone: str = "", how: str = "", conv: str = "") -> dict:
    """The person's right: recorded at once (no tap). Processing on consent must stop; erasure is a separate card."""
    p = R.phone10(phone)
    with session() as s:
        rows = []
        if ref:
            c = s.get(DpoConsent, ref)
            if c and c.tenant_id == tenant:
                rows = [c]
        elif p:
            rows = s.scalars(select(DpoConsent).where(DpoConsent.tenant_id == tenant, DpoConsent.phone == p, DpoConsent.status == "active")).all()
        if not rows:
            raise DpoError("Consent record nahi mila.")
        for c in rows:
            c.status, c.withdrawn_at, c.withdraw_how = "withdrawn", clock(), R.scrub(how, 60)
        acts = sorted({a for c in rows for a in _j(c.activity_ids, [])})
        names = [x.number for x in s.scalars(select(DpoActivity).where(DpoActivity.id.in_(acts))).all()] if acts else []
        phone_ = rows[0].phone
    hits = find(tenant, phone_) if phone_ else []
    say = (f"Consent wapas darj ({len(rows)}). In kaamon mein ab unka data consent par use mat kijiye: {', '.join(names) or 'sab'}. "
           "Pehle ka kaam valid rehta hai.")
    if hits:
        say += f" Unka data {len(hits)} jagah hai; mitaana ho to maang (erasure) banaiye."
    return {"withdrawn": len(rows), "found": hits, "say": say}


def consents(tenant: str, q: str = "") -> list[dict]:
    with session() as s:
        rows = s.scalars(select(DpoConsent).where(DpoConsent.tenant_id == tenant).order_by(DpoConsent.given_at.desc())).all()[:300]
        out = [_consent_view(c) for c in rows]
    if q:
        ql, p = q.lower(), R.phone10(q)
        out = [c for c in out if ql in c["name"].lower() or (p and c["phone"].endswith(p[-4:]))]
    return out


# ---------------------------------------------------------------- find a person across modules (phone)
def find(tenant: str, phone: str) -> list[dict]:
    p = R.phone10(phone)
    if not p:
        return []
    out = []
    with session() as s:
        tables = _tables(s)
        for key, label, table, col, idcol, eraser in R.FINDERS:
            cols = tables.get(table)
            if not cols or col not in cols or "tenant_id" not in cols:
                continue
            try:
                rows = s.execute(text(f"SELECT {idcol} FROM {table} WHERE tenant_id = :t AND {col} LIKE :p LIMIT 20"),
                                 {"t": tenant, "p": f"%{p}"}).all()
            except Exception:
                continue
            for (rid,) in rows:
                c = R.CATALOG.get(key, {})
                out.append({"module": key, "label": label, "ref": str(rid), "can_erase": bool(eraser), "items": c.get("items", []),
                            "purpose": c.get("purpose", ""), "law_hold": bool(c.get("law_hold"))})
        n = s.scalar(select(func.count()).select_from(DpoConsent).where(DpoConsent.tenant_id == tenant, DpoConsent.phone == p)) or 0
        if n:
            out.append({"module": "dpo", "label": "Consent record", "ref": p, "can_erase": True, "items": ["naam", "mobile", "consent"],
                        "purpose": "consent ka saboot", "law_hold": False})
    return out


def _erase_one(tenant: str, hit: dict, phone: str) -> dict:
    m, ref = hit["module"], hit["ref"]
    try:
        if m == "telecall":
            from ..telecall import service as X
            r = X.forget(tenant, ref)
        elif m == "shikayat":
            from ..shikayat import service as X
            r = X.forget_customer(tenant, phone)
        elif m == "callcentre":
            from ..callcentre import service as X
            r = X.forget_caller(tenant, phone)
        elif m == "wapsi":
            from ..wapsi import service as X
            r = X.forget_customer(tenant, ref)
        elif m == "courier":
            from ..courier import service as X
            r = X.forget(tenant, ref)
        elif m == "propagent":
            from ..propagent import service as X
            r = X.forget_lead(tenant, ref)
        elif m == "dpo":
            with session() as s:
                for c in s.scalars(select(DpoConsent).where(DpoConsent.tenant_id == tenant, DpoConsent.phone == phone)).all():
                    c.name, c.phone, c.parent_name, c.status = "(hataya)", "", "", "forgotten"
            r = {"say": "Consent record se naam / number hataya."}
        else:
            return {"module": m, "ref": ref, "ok": False, "say": "Is module mein mitaane ka seedha raasta nahi: uski screen se hataiye."}
        return {"module": m, "ref": ref, "ok": True, "say": str((r or {}).get("say", "Mita diya."))[:200]}
    except Exception as e:  # each module refuses in its own words (e.g. open case)
        return {"module": m, "ref": ref, "ok": False, "say": str(e)[:200]}


# ---------------------------------------------------------------- rights requests (Rule 14)
def _req_view(r: DpoRequest, on: date) -> dict:
    due = _date(r.due_on)
    return {"id": r.id, "number": r.number, "kind": r.kind, "kind_label": R.KINDS.get(r.kind, ("", ""))[0], "name": r.name,
            "phone": R.mask_phone(r.phone), "email": R.mask_email(r.email), "via": r.via, "text": r.text, "received_on": r.received_on,
            "due_on": r.due_on, "days_left": (due - on).days if due else None, "id_check": r.id_check, "id_how": r.id_how,
            "found": _j(r.found, []), "reply": r.reply, "status": r.status, "result": _j(r.result, {}), "log": _j(r.log, [])[-20:]}


def _req(s, tenant: str, ref: str) -> DpoRequest:
    r = s.get(DpoRequest, ref)
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(DpoRequest).where(DpoRequest.tenant_id == tenant, DpoRequest.number == str(ref).upper())).first()
    if r is None:
        raise DpoError("Maang (R-....) nahi mili.")
    return r


def _rlog(r: DpoRequest, what: str, by: str = "") -> None:
    lg = _j(r.log, [])
    lg.append({"at": now().isoformat(timespec="minutes"), "what": what[:200], "by": by})
    r.log = _dump(lg[-60:])


def request_new(tenant: str, text_: str = "", name: str = "", phone: str = "", email: str = "", via: str = "", kind: str = "",
                received: str = "", actor: str = "owner", conv: str = "") -> dict:
    body = R.scrub(text_, 3000)
    if not (body or kind):
        raise DpoError("Unki maang ke shabd (ya kind) chahiye.")
    kind = kind if kind in R.KINDS else R.kind_of(body)
    p = R.phone10(phone)
    rec = _date(received) or today(tenant)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        due = R.due_rights(rec, st.reply_days)
        r = DpoRequest(tenant_id=tenant, number=f"R-{_next(st, 'r'):04d}", kind=kind, name=R.scrub(name, 120), phone=p,
                       email=str(email or "").strip()[:120], via=R.scrub(via, 20), text=body, received_on=rec.isoformat(), due_on=due.isoformat())
        _rlog(r, f"Maang mili ({R.KINDS[kind][0]})", actor_name(tenant, actor))
        s.add(r)
        s.flush()
        rid = r.id
    hits = find(tenant, p) if p else []
    with session() as s:
        r = s.get(DpoRequest, rid)
        r.found = _dump(hits)
        v = _req_view(r, today(tenant))
    if kind == "withdraw" and p:
        try:
            consent_withdraw(tenant, phone=p, how=f"maang {v['number']}")
        except DpoError:
            pass
    say = (f"{v['number']} ({v['kind_label']}) darj: jawab {v['due_on']} tak (kanoon: {R.RIGHTS_DAYS} din se zyada nahi). "
           f"Pehle pehchaan pakki kijiye ({'registered mobile / email se' if not st.identifiers else st.identifiers}): sirf tareeka likhiye, "
           "ID number nahi.")
    if hits:
        say += f" Unka data {len(hits)} jagah mila."
    _publish(tenant, "dpo_request", {"request": v, "say": say}, conv)
    return {"request": v, "say": say}


def request_verify(tenant: str, ref: str, ok: bool = True, how: str = "", actor: str = "owner") -> dict:
    hw = _id_free(how, "Pehchaan")
    if not hw:
        raise DpoError("Pehchaan kaise ki, likhiye (jaise 'registered mobile par call karke pucha').")
    with session() as s:
        r = _req(s, tenant, ref)
        r.id_check, r.id_how = ("done" if ok else "failed"), hw
        if r.status == "new":
            r.status = "working"
        _rlog(r, f"Pehchaan {'pakki' if ok else 'nahi hui'}: {hw}", actor_name(tenant, actor))
        v = _req_view(r, today(tenant))
    return {"request": v, "say": f"{v['number']}: pehchaan {'pakki' if ok else 'nahi hui (jawab mein yahi likhenge)'}."}


def _access_body(tenant: str, r: DpoRequest) -> str:
    hits = _j(r.found, [])
    if not hits:
        return "Hamare records mein aapke is number se koi data nahi mila. " + R.BLANK
    lines = ["Hamare paas aapka yeh data hai:"]
    for h in hits:
        lines.append(f"- {h['label']}: {', '.join(h.get('items') or [])} (kaam: {h.get('purpose') or R.BLANK})")
    with session() as s:
        procs = sorted({p for a in s.scalars(select(DpoActivity).where(DpoActivity.tenant_id == tenant,
                                                                      DpoActivity.source.in_([h['module'] for h in hits]))).all()
                        for p in _j(a.processors, [])})
    if procs:
        lines.append("Jinke saath share hota hai (processors): " + ", ".join(procs))
    return "\n".join(lines)


def request_reply(tenant: str, ref: str, body: str = "", actor: str = "owner", conv: str = "") -> dict:
    """Draft the reply and make a card; only her tap sends (she sends from her own WhatsApp / email)."""
    with _LOCK, session() as s:
        st = _st(s, tenant)
        r = _req(s, tenant, ref)
        if r.status in ("replied", "closed"):
            raise DpoError(f"{r.number} ka jawab ja chuka.")
        if r.kind != "grievance" and r.id_check == "pending":
            raise DpoError("Pehle pehchaan pakki kijiye (request_verify): bina pehchaan ke kisi ka data / jawab nahi.")
        if not body:
            if r.id_check == "failed":
                body = "Hum aapki pehchaan pakki nahi kar paye, isliye abhi yeh maang poori nahi kar sakte. Registered mobile / email se dobara likhiye."
            elif r.kind == "access":
                body = _access_body(tenant, r)
            elif r.kind == "erasure":
                res = _j(r.result, {}).get("erased")
                body = ("Aapka data in jagahon se hata diya gaya: " + ", ".join(f"{x['module']}" for x in res if x.get("ok"))
                        if res else R.BLANK)
            elif r.kind == "withdraw":
                body = "Aapka consent wapas darj ho gaya; aage se is kaam ke liye aapka data use nahi hoga."
            else:
                body = R.BLANK
        txt = R.reply_text(r.kind, r.name, st.org, r.number, R.scrub(body, 3000), _contact(st))
        if R.has_blank(txt):
            r.reply = txt
            return {"request": _req_view(r, today(tenant)), "say": "Jawab mein [____] baaki: apne shabd bhejiye (body) ya settings bhariye."}
        r.reply = txt
        r.status = "waiting"
        old = s.scalars(select(DpoCard).where(DpoCard.tenant_id == tenant, DpoCard.kind == "reply", DpoCard.target == r.id,
                                              DpoCard.status == "waiting")).all()
        for o in old:
            o.status = "stale"
        data = {"number": r.number, "kind_label": R.KINDS[r.kind][0], "to": r.name, "phone": R.mask_phone(r.phone),
                "email": R.mask_email(r.email), "text": txt, "due_on": r.due_on, "disclaimer": R.DISCLAIMER}
        c = _new_card(s, tenant, "reply", r.id, f"{r.number}: jawab bhejein?", data, _hash(_snapshot(s, "reply", r.id)), actor, conv)
        _rlog(r, "Jawab ka card bana", actor_name(tenant, actor))
        cv = _card_view(c)
    _publish(tenant, "dpo_card", {"card": cv, "say": cv["title"]}, conv)
    return {"card": cv, "say": "Jawab ka card bheja: aapke tap ke baad WhatsApp / email ka draft khulega, aap bhejiye."}


def erase_request(tenant: str, ref: str, modules: list | None = None, actor: str = "owner", conv: str = "") -> dict:
    """Erasure card: which module records go. Runs the modules' own forget functions only on her tap."""
    with _LOCK, session() as s:
        r = _req(s, tenant, ref)
        if r.kind not in ("erasure", "withdraw"):
            raise DpoError("Mitaana sirf erasure / consent wapas ki maang par.")
        if r.id_check != "done":
            raise DpoError("Pehle pehchaan pakki kijiye: galat aadmi ke kehne par data mitana nuksaan hai.")
        if not r.phone:
            raise DpoError("Unka registered mobile chahiye (record dhoondne ke liye).")
        rid, phone = r.id, r.phone
    hits = find(tenant, phone)
    with session() as s:
        r = s.get(DpoRequest, rid)
        r.found = _dump(hits)
    targets = [h for h in hits if h["can_erase"] and (not modules or h["module"] in modules)]
    manual = [h for h in hits if not h["can_erase"]]
    if not targets:
        raise DpoError("Mitaane layak record nahi mila" + (f" (in modules mein khud hataiye: {', '.join(sorted({h['label'] for h in manual}))})"
                                                           if manual else "."))
    warn = [f"{h['label']}: kanoon ke liye kuch record rakhna pad sakta hai (CA se poochhiye)." for h in targets if h["law_hold"]]
    with _LOCK, session() as s:
        r = s.get(DpoRequest, rid)
        data = {"number": r.number, "phone": R.mask_phone(phone), "targets": [{"module": h["module"], "label": h["label"], "ref": h["ref"]}
                                                                             for h in targets],
                "manual": [h["label"] for h in manual], "warnings": warn,
                "note": "Yeh wapas nahi aata. Module apne niyam se mana kar sakta hai (jaise khula case)."}
        c = _new_card(s, tenant, "erase", r.id, f"{r.number}: {len(targets)} record mitaayein?", data,
                      _hash(_snapshot(s, "erase", r.id, data)), actor, conv)
        _rlog(r, "Mitaane ka card bana", actor_name(tenant, actor))
        cv = _card_view(c)
    _publish(tenant, "dpo_card", {"card": cv, "say": cv["title"]}, conv)
    return {"card": cv, "say": "Mitaane ka card bheja: aapke tap (aur fingerprint, agar phone juda hai) ke baad hi."}


def request_close(tenant: str, ref: str, status: str = "closed", note: str = "", actor: str = "owner") -> dict:
    _need_owner(actor)
    with session() as s:
        r = _req(s, tenant, ref)
        r.status = status if status in ("closed", "rejected", "replied") else "closed"
        _rlog(r, f"{r.status}: {R.scrub(note, 200)}", "Owner")
        v = _req_view(r, today(tenant))
    return {"request": v, "say": f"{v['number']} {v['status']}."}


def request_sent(tenant: str, ref: str, how: str = "", actor: str = "owner") -> dict:
    _need_owner(actor)
    with session() as s:
        r = _req(s, tenant, ref)
        r.status = "replied"
        late = today(tenant) > (_date(r.due_on) or today(tenant))
        _rlog(r, "Jawab bheja" + (f" ({R.scrub(how, 60)})" if how else "") + (" - samay ke baad" if late else ""), "Owner")
        v = _req_view(r, today(tenant))
    return {"request": v, "say": f"{v['number']} jawab bheja darj." + (" (Due date nikal chuki thi.)" if late else "")}


def requests(tenant: str, status: str = "") -> list[dict]:
    on = today(tenant)
    with session() as s:
        q = select(DpoRequest).where(DpoRequest.tenant_id == tenant)
        if status == "open":
            q = q.where(DpoRequest.status.in_(("new", "working", "waiting")))
        elif status:
            q = q.where(DpoRequest.status == status)
        return [_req_view(r, on) for r in s.scalars(q.order_by(DpoRequest.created_at.desc())).all()[:200]]


def request_view(tenant: str, ref: str) -> dict:
    with session() as s:
        return _req_view(_req(s, tenant, ref), today(tenant))


# ---------------------------------------------------------------- breaches (Rule 7 + CERT-In via IT Helpdesk)
def _breach_view(tenant: str, b: DpoBreach) -> dict:
    f = _j(b.facts, {})
    due = _aware(b.report_due)
    left = (due - clock()).total_seconds() / 3600 if due else None
    ci = _j(b.cert_in, {})
    st_org, contact = "", ""
    with session() as s:
        st = s.get(DpoSettings, tenant)
        if st:
            st_org, contact = st.org, _contact(st)
    f2 = {**f, "aware_text": _local(tenant, b.aware_at)}
    return {"id": b.id, "number": b.number, "title": b.title, "aware_at": _local(tenant, b.aware_at), "report_due": _local(tenant, due),
            "hours_left": round(left, 1) if left is not None else None, "facts": f, "affected": len(_j(b.affected, [])),
            "activities": _j(b.activity_ids, []), "cert_in": ci, "status": b.status,
            "initial_at": _local(tenant, b.initial_at), "report_at": _local(tenant, b.report_at), "people_at": _local(tenant, b.people_at),
            "refs": _j(b.refs, {}),
            "drafts": {"initial": R.breach_initial_text(f2, st_org), "report": R.breach_report_text(f2, st_org),
                       "people": R.breach_people_text(f2, st_org, contact)}}


def _breach(s, tenant: str, ref: str) -> DpoBreach:
    b = s.get(DpoBreach, ref)
    if b is None or b.tenant_id != tenant:
        b = s.scalars(select(DpoBreach).where(DpoBreach.tenant_id == tenant, DpoBreach.number == str(ref).upper())).first()
    if b is None:
        raise DpoError("Breach (B-..) nahi mila.")
    return b


def _clean_affected(v) -> list[dict]:
    out = []
    for x in (v or [])[:5000]:
        if isinstance(x, str):
            x = {"phone": x} if R.phone10(x) else ({"email": x} if "@" in x else {"name": x})
        if not isinstance(x, dict):
            continue
        p, e = R.phone10(x.get("phone")), str(x.get("email") or "").strip()[:120]
        if p or "@" in e:
            out.append({"name": R.scrub(x.get("name"), 80), "phone": p, "email": e if "@" in e else ""})
    return out


def breach_new(tenant: str, title: str, aware: str = "", link_cert_in: bool = True, activities_: list | None = None,
               affected: list | None = None, actor: str = "owner", conv: str = "", **facts: Any) -> dict:
    if not str(title or "").strip():
        raise DpoError("Kya hua, ek line mein likhiye.")
    aware_at = _when(tenant, aware)
    if aware_at is None:
        raise DpoError("Kab pata chala: 'YYYY-MM-DD HH:MM' (ya 'abhi').")
    f = {k: R.scrub(v, 1500) for k, v in facts.items() if k in R.BREACH_FIELDS and v}
    with _LOCK, session() as s:
        st = _st(s, tenant)
        ids = []
        for r in (activities_ or []):
            try:
                ids.append(_activity(s, tenant, str(r)).id)
            except DpoError:
                pass
        b = DpoBreach(tenant_id=tenant, number=f"B-{_next(st, 'b'):02d}", title=R.scrub(title, 200), aware_at=aware_at,
                      report_due=aware_at + timedelta(hours=R.BREACH_REPORT_HOURS), facts=_dump(f), activity_ids=_dump(ids),
                      affected=_dump(_clean_affected(affected)))
        s.add(b)
        s.flush()
        bid = b.id
    ci: dict = {}
    if link_cert_in:
        try:
            from ..helpdesk import service as H
            out = H.report_phish(tenant, f"Personal data breach: {title}. {f.get('nature', '')}", kind="data_leak", personal_data=True,
                                 actor=actor, conv=conv)
            inc = out.get("incident") or {}
            ci = {"incident": inc.get("id", ""), "due": inc.get("report_due_local") or inc.get("report_due") or "",
                  "applies": (out.get("cert_in") or {}).get("applies"), "why": (out.get("cert_in") or {}).get("why", "")}
        except Exception as e:
            log.info("dpo: cert-in link skipped: %s", e)
            ci = {"error": "IT Helpdesk incident nahi bana; CERT-In 6 ghante wala niyam khud dekhiye (IT Helpdesk > Suraksha)."}
    with session() as s:
        b = s.get(DpoBreach, bid)
        b.cert_in = _dump(ci)
        v = _breach_view(tenant, b)
    say = (f"{v['number']} darj. Board ko pehli soochna 'bina der' (Rule 7(2)(a)); poori report {v['report_due']} tak (72 ghante). "
           "Prabhavit logon ko bhi bina der batana hai (Rule 7(1)). Teeno ke draft taiyaar: har ek aapke tap se.")
    if ci.get("incident"):
        say += f" CERT-In: IT Helpdesk incident bana ({ci.get('why') or '6 ghante wala niyam'})."
    _publish(tenant, "dpo_breach", {"breach": v, "say": say}, conv)
    return {"breach": v, "say": say + " " + R.DISCLAIMER}


def breach_update(tenant: str, ref: str, affected: list | None = None, actor: str = "owner", **facts: Any) -> dict:
    with _LOCK, session() as s:
        b = _breach(s, tenant, ref)
        f = _j(b.facts, {})
        for k, v in facts.items():
            if k in R.BREACH_FIELDS and v is not None:
                f[k] = R.scrub(v, 1500)
        b.facts = _dump(f)
        if affected is not None:
            b.affected = _dump(_clean_affected(affected))
        for c in s.scalars(select(DpoCard).where(DpoCard.tenant_id == tenant, DpoCard.target == b.id, DpoCard.status == "waiting")).all():
            c.status = "stale"
        v = _breach_view(tenant, b)
    return {"breach": v, "say": f"{v['number']} update (purane card radd: naya card banaiye)."}


def breach_send(tenant: str, ref: str, which: str, actor: str = "owner", conv: str = "") -> dict:
    which = which if which in ("initial", "report", "people") else "initial"
    kind = f"breach_{which}"
    with _LOCK, session() as s:
        b = _breach(s, tenant, ref)
        v = _breach_view(tenant, b)
        txt = v["drafts"][which]
        if which in ("report", "people") and R.has_blank(txt):
            miss = [ln.split(":")[0] for ln in txt.splitlines() if R.BLANK in ln]
            raise DpoError("Draft mein [____] baaki: " + "; ".join(miss[:6]) + ". Jo pata nahi, woh saaf likhiye ('abhi jaanch chal rahi').")
        aff = _j(b.affected, [])
        data = {"number": b.number, "which": which, "text": txt, "report_due": v["report_due"], "hours_left": v["hours_left"],
                "affected": len(aff), "disclaimer": R.DISCLAIMER,
                "where": ("Prabhavit logon ko unke registered tareeke se (WhatsApp / SMS / email)." if which == "people" else
                          "Data Protection Board of India ko: Board ka official channel (Board ne portal / email jaari kiya ho to wahi). "
                          "Hoola khud file nahi karta.")}
        for o in s.scalars(select(DpoCard).where(DpoCard.tenant_id == tenant, DpoCard.kind == kind, DpoCard.target == b.id,
                                                 DpoCard.status == "waiting")).all():
            o.status = "stale"
        c = _new_card(s, tenant, kind, b.id, f"{b.number}: {CARD_KINDS[kind]}?", data, _hash(_snapshot(s, kind, b.id)), actor, conv)
        cv = _card_view(c)
    _publish(tenant, "dpo_card", {"card": cv, "say": cv["title"]}, conv)
    return {"card": cv, "say": f"{CARD_KINDS[kind]} ka card bheja: aapke tap ke baad hi."}


def breach_sent(tenant: str, ref: str, which: str, ref_no: str = "", actor: str = "owner") -> dict:
    """Her word that she really sent it (to the Board / to people). Late against 72 h is said."""
    _need_owner(actor)
    with session() as s:
        b = _breach(s, tenant, ref)
        approved = s.scalars(select(DpoCard).where(DpoCard.tenant_id == tenant, DpoCard.target == b.id,
                                                   DpoCard.kind == f"breach_{which}", DpoCard.status == "approved")).first()
        if approved is None:
            raise DpoError("Pehle uska card aapke tap se 'haan' hona chahiye.")
        t = clock()
        if which == "initial":
            b.initial_at = t
        elif which == "report":
            b.report_at = t
        else:
            b.people_at = t
        refs = _j(b.refs, {})
        refs[which] = R.scrub(ref_no, 120)
        b.refs = _dump(refs)
        late = which == "report" and _aware(b.report_due) and t > _aware(b.report_due)
        v = _breach_view(tenant, b)
    return {"breach": v, "say": f"{v['number']}: {which} bheja darj." + (" 72 ghante nikal chuke the: der ki wajah report mein likhiye." if late else "")}


def breach_close(tenant: str, ref: str, actor: str = "owner") -> dict:
    _need_owner(actor)
    with session() as s:
        b = _breach(s, tenant, ref)
        miss = [w for w, at in (("Board pehli soochna", b.initial_at), ("72 ghante report", b.report_at), ("logon ko soochna", b.people_at))
                if at is None]
        if miss:
            raise DpoError("Band karne se pehle: " + ", ".join(miss) + " baaki.")
        b.status = "closed"
        v = _breach_view(tenant, b)
    return {"breach": v, "say": f"{v['number']} band."}


def breaches(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(DpoBreach).where(DpoBreach.tenant_id == tenant)
        if status:
            q = q.where(DpoBreach.status == status)
        return [_breach_view(tenant, b) for b in s.scalars(q.order_by(DpoBreach.created_at.desc())).all()[:100]]


def breach_view(tenant: str, ref: str) -> dict:
    with session() as s:
        return _breach_view(tenant, _breach(s, tenant, ref))


# ---------------------------------------------------------------- cards (HER tap only)
def _new_card(s, tenant: str, kind: str, target: str, title: str, data: dict, h: str, actor: str, conv: str) -> DpoCard:
    c = DpoCard(tenant_id=tenant, kind=kind, target=target, title=title[:200], hash=h, data=_dump(data),
                asked_by=actor_name(tenant, actor), conv=conv)
    s.add(c)
    s.flush()
    return c


def _card_view(c: DpoCard) -> dict:
    return {"id": c.id, "kind": c.kind, "kind_label": CARD_KINDS.get(c.kind, c.kind), "target": c.target, "title": c.title,
            "hash": c.hash, "data": _j(c.data, {}), "status": c.status, "reason": c.reason, "result": _j(c.result, {}),
            "asked_by": c.asked_by, "fingerprint": c.kind == "erase",
            "created_at": _aware(c.created_at).isoformat(timespec="minutes") if c.created_at else ""}


def _snapshot(s, kind: str, target: str, data: dict | None = None):
    """What the card shows, read again from the tables; any change after the card = stale."""
    if kind == "notice":
        n = s.get(DpoNotice, target)
        return [n.text, n.lang, n.version] if n else None
    if kind == "reply":
        r = s.get(DpoRequest, target)
        return [r.reply, r.phone, r.email, r.id_check] if r else None
    if kind == "erase":
        r = s.get(DpoRequest, target)
        if r is None:
            return None
        tg = (data or {}).get("targets")
        if tg is None:
            c = s.scalars(select(DpoCard).where(DpoCard.kind == "erase", DpoCard.target == target, DpoCard.status == "waiting")
                          .order_by(DpoCard.created_at.desc())).first()
            tg = _j(c.data, {}).get("targets") if c else []
        return [r.phone, r.id_check, tg]
    if kind.startswith("breach_"):
        b = s.get(DpoBreach, target)
        if b is None:
            return None
        return [kind, b.facts, b.affected, _aware(b.aware_at).isoformat() if b.aware_at else ""]
    return None


def cards(tenant: str, status: str = "waiting") -> list[dict]:
    with session() as s:
        q = select(DpoCard).where(DpoCard.tenant_id == tenant)
        if status:
            q = q.where(DpoCard.status == status)
        return [_card_view(c) for c in s.scalars(q.order_by(DpoCard.created_at.desc())).all()[:100]]


def card(tenant: str, card_id: str) -> dict | None:
    with session() as s:
        c = s.get(DpoCard, card_id)
        return _card_view(c) if c and c.tenant_id == tenant else None


def challenge(tenant: str, card_id: str) -> dict:
    """approvekey's message format (kind 'dpo'): the phone signs this erasure card as it is NOW."""
    from .. import approvekey as ak
    c = card(tenant, card_id)
    if not c or c["status"] != "waiting":
        raise DpoError("Yeh card ab baaki nahi hai.")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|dpo|{card_id}|{c['hash']}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="dpo", target=card_id, digest=c["hash"], message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    return {"challenge_id": chid, "message": msg, "show": {"title": c["title"][:80], "amount": "", "payee": ""},
            "expires_at": exp.isoformat()}


def _verify_fingerprint(tenant: str, card_id: str, digest: str, proof: dict | None) -> None:
    from .. import approvekey as ak
    if not proof:
        raise DpoError("fingerprint_needed")
    with session() as s:
        ak._settle(s, tenant)
        ok = ak._check(s, tenant, "dpo", card_id, proof, digest)
    if not ok:
        raise DpoError("fingerprint_invalid")


def decide_card(tenant: str, card_id: str, yes: bool, card_hash: str = "", reason: str = "", proof: dict | None = None,
                by_tap: bool = False) -> dict:
    """ONLY her tap in the app (API). The tool can never reach this with by_tap."""
    if not by_tap:
        raise DpoError("Yeh faisla sirf aapke tap se (app ka card).")
    with _LOCK, session() as s:
        c = s.get(DpoCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise DpoError("Card nahi mila.")
        if c.status != "waiting":
            return {"card": _card_view(c), "say": f"Yeh card pehle hi '{c.status}' hai."}
        snap = _snapshot(s, c.kind, c.target, _j(c.data, {}))
        if snap is None or _hash(snap) != c.hash:
            c.status = "stale"
            raise DpoError("Card ke baad cheezein badal gayi: naya card banwaiye.")
        if not card_hash or card_hash != c.hash:
            raise DpoError("Card badal gaya hai; naya card dekhiye.")
        kind, target, data = c.kind, c.target, _j(c.data, {})
    if yes and kind == "erase":
        from .. import approvekey as ak
        if ak.active_on(tenant):
            _verify_fingerprint(tenant, card_id, card_hash, proof)
    out: dict[str, Any] = {}
    erased: list[dict] = []
    if yes and kind == "erase":
        with session() as s:
            phone = s.get(DpoRequest, target).phone
        erased = [_erase_one(tenant, h, phone) for h in data.get("targets", [])]
    with _LOCK, session() as s:
        c = s.get(DpoCard, card_id)
        c.status = "approved" if yes else "rejected"
        c.reason = R.scrub(reason, 300)
        c.decided_at = now()
        if kind == "notice":
            n = s.get(DpoNotice, target)
            if yes:
                for o in s.scalars(select(DpoNotice).where(DpoNotice.tenant_id == tenant, DpoNotice.lang == n.lang,
                                                           DpoNotice.status == "published")).all():
                    o.status = "old"
                n.status, n.published_at = "published", now()
                out["say"] = f"Notice v{n.version} publish (approved). Isse apni website / app / dukaan par lagaiye; file aa rahi hai."
                out["_file"] = (n.id, n.lang, n.version, n.text)
            else:
                n.status = "rejected"
                out["say"] = "Notice publish nahi hua."
        elif kind == "reply":
            r = s.get(DpoRequest, target)
            if yes:
                out["send"] = {"wa": _wa(r.phone, r.reply), "mail": _mailto(r.email, f"{r.number}", r.reply), "text": r.reply}
                out["say"] = f"{r.number}: jawab taiyaar. WhatsApp / email khol kar aap bhejiye, phir 'Bhej diya'."
                _rlog(r, "Jawab approved (aapka tap)", "Owner")
            else:
                r.status = "working"
                out["say"] = f"{r.number}: jawab nahi gaya."
        elif kind == "erase":
            r = s.get(DpoRequest, target)
            if yes:
                res = _j(r.result, {})
                res["erased"] = erased
                r.result = _dump(res)
                ok = [e for e in erased if e["ok"]]
                _rlog(r, f"Mitaya: {len(ok)} / {len(erased)} (aapka tap)", "Owner")
                out["erased"] = erased
                out["say"] = (f"{r.number}: {len(ok)} record mita diye." +
                              (f" {len(erased) - len(ok)} nahi mite: " + "; ".join(e['say'] for e in erased if not e['ok'])[:300]
                               if len(ok) < len(erased) else "") + " Ab unhe jawab bhejiye.")
                c.result = _dump({"erased": erased})
            else:
                out["say"] = f"{r.number}: kuch nahi mitaya."
        elif kind.startswith("breach_"):
            b = s.get(DpoBreach, target)
            which = kind.split("_", 1)[1]
            if yes:
                txt = data.get("text", "")
                if which == "people":
                    aff = _j(b.affected, [])
                    out["send"] = [{"name": a.get("name", ""), "phone": R.mask_phone(a.get("phone", "")),
                                    "wa": _wa(a.get("phone", ""), txt), "mail": _mailto(a.get("email", ""), f"{b.number}: data breach", txt)}
                                   for a in aff[:500]]
                out["text"] = txt
                out["say"] = (f"{b.number}: {CARD_KINDS[kind]} approved. Aap bhejiye (Hoola khud nahi bhejta), phir 'Bhej diya' "
                              "ke saath reference.")
            else:
                out["say"] = f"{b.number}: {CARD_KINDS[kind]} nahi."
        out["card"] = _card_view(c)
    f = out.pop("_file", None)
    if f:
        try:
            out["file"] = _notice_file(tenant, *f)
        except Exception:
            log.exception("dpo notice file failed")
    return out


def _notice_file(tenant: str, nid: str, lang: str, ver: int, txt: str) -> dict | None:
    from .. import chatfiles
    from ..officegen import make_docx
    data = make_docx(f"Privacy notice v{ver}", txt)
    f = chatfiles.store(tenant, f"Privacy_notice_v{ver}_{lang}.docx", data,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with session() as s:
        n = s.get(DpoNotice, nid)
        n.files = _dump([f.get("file_id") or f.get("id")])
    _publish(tenant, "pc_file", {**f, "source": "dpo", "title": f"Privacy notice v{ver}"})
    return f


# ---------------------------------------------------------------- retention
def retention(tenant: str) -> list[dict]:
    out = []
    n = clock()
    with session() as s:
        tables = _tables(s)
        for a in s.scalars(select(DpoActivity).where(DpoActivity.tenant_id == tenant, DpoActivity.status == "active")).all():
            c = R.CATALOG.get(a.source)
            old = 0
            if c and a.retention_days:
                cut = n - timedelta(days=int(a.retention_days))
                old = sum(_count(s, tables, t, tenant, older=cut) for t in c["tables"])
            out.append({"activity": a.number, "name": a.name, "retention": a.retention, "days": a.retention_days, "older": old,
                        "law_hold": a.law_hold,
                        "say": (f"{old} record {a.retention_days} din se purane: review karke mitaiye (har ek ke liye maang / module se)."
                                if old else "")})
    return out


# ---------------------------------------------------------------- register (Excel)
def register_file(tenant: str, conv: str = "") -> dict:
    from .. import chatfiles
    from ..officegen import make_xlsx
    acts = activities(tenant)
    sheets = {
        "Records of processing": [["No", "Kaam", "Kiska data", "Data", "Purpose", "Aadhaar", "Retention", "Processors", "Bachche",
                                   "Bahar", "Records", "DPIA"]] +
        [[a["number"], a["name"], a["people"], ", ".join(a["items"]), a["purpose"], a["basis_label"], a["retention"],
          ", ".join(a["processors"]), "haan" if a["children"] else "", "haan" if a["abroad"] else "", a["records"],
          a["dpia"].get("level", "")] for a in acts],
        "Requests": [["No", "Kind", "Received", "Due", "Status", "Pehchaan"]] +
        [[r["number"], r["kind_label"], r["received_on"], r["due_on"], r["status"], r["id_check"]] for r in requests(tenant)],
        "Breaches": [["No", "Kya", "Pata chala", "72h due", "Board pehli", "Board report", "Logon ko"]] +
        [[b["number"], b["title"], b["aware_at"], b["report_due"], b["initial_at"], b["report_at"], b["people_at"]] for b in breaches(tenant)],
        "Processors": [["Vendor", "Service", "Desh", "DPA", "Review", "Baaki clause"]] +
        [[v["name"], v["service"], v["country"], "haan" if v["dpa_signed"] else "nahi", v["review_on"], len(v["missing"])] for v in vendors(tenant)],
        "Consents": [["Naam", "Mobile", "Kaise", "Kab", "Wapas", "Bachcha"]] +
        [[c["name"], c["phone"], c["how"], c["given_at"], c["withdrawn_at"], "haan" if c["child"] else ""] for c in consents(tenant)],
    }
    data = make_xlsx("DPDP register", sheets)
    f = chatfiles.store(tenant, "DPDP_register.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "dpo", "title": "DPDP register"}, conv)
    return {"file": f, "say": "Records of processing, maangein, breach, vendors aur consent ka Excel (aapke vakil / auditor ke liye)."}


# ---------------------------------------------------------------- day / overview
def day(tenant: str) -> dict:
    reqs = requests(tenant, "open")
    brs = breaches(tenant, "open")
    cs = cards(tenant)
    acts = activities(tenant)
    vs = vendors(tenant)
    unconf = [a["number"] for a in acts if not a["confirmed"]]
    child_issue = [a["number"] for a in acts if a["children"] and R.child_flags(a)]
    no_dpa = [v["name"] for v in vs if not v["dpa_signed"]]
    bits = []
    for b in brs:
        if not b["report_at"]:
            bits.append(f"Breach {b['number']}: 72 ghante ki report {b['report_due']} tak ({b['hours_left']} ghante).")
    late = [r for r in reqs if (r["days_left"] or 0) < 0]
    soon = [r for r in reqs if r["days_left"] is not None and 0 <= r["days_left"] <= 7]
    if late:
        bits.append(f"{len(late)} maang ki taarikh nikal gayi: " + ", ".join(r["number"] for r in late[:5]) + ".")
    if soon:
        bits.append(f"{len(soon)} maang 7 din mein due.")
    if cs:
        bits.append(f"{len(cs)} card aapki haan ke liye.")
    if unconf:
        bits.append(f"{len(unconf)} record 'sahi hai' karne baaki.")
    if no_dpa:
        bits.append(f"{len(no_dpa)} vendor ka DPA nahi.")
    return {"say": " ".join(bits) or "Data suraksha: aaj sab theek.", "requests": reqs, "breaches": brs, "cards": cs,
            "unconfirmed": unconf, "children": child_issue, "no_dpa": no_dpa, "phases": R.phase_notes(today(tenant))}


def overview(tenant: str) -> dict:
    return {"settings": settings(tenant), "day": day(tenant), "activities": activities(tenant), "notices": notices(tenant),
            "vendors": vendors(tenant), "requests": requests(tenant), "breaches": breaches(tenant)}


def law() -> dict:
    return {"never": R.NEVER, "penalties": R.PENALTIES, "kinds": {k: v[0] for k, v in R.KINDS.items()}, "bases": R.BASES,
            "dpia": [{"key": k, "q": q} for k, q, _ in R.DPIA_QUESTIONS], "dpa": [{"key": k, "text": t} for k, t in R.DPA_CLAUSES],
            "third_schedule": [t for t, _, _ in R.THIRD_SCHEDULE], "phases": {"rules": R.RULES_NOTIFIED.isoformat(),
                                                                              "consent_manager": R.CONSENT_MANAGER_FROM.isoformat(),
                                                                              "main_duties": R.MAIN_DUTIES_FROM.isoformat()},
            "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES], "disclaimer": R.DISCLAIMER}


# ---------------------------------------------------------------- worker
def _once(s, tenant: str, key: str) -> bool:
    k = f"{tenant}:{key}"[:200]
    if s.get(DpoAlert, k) is not None:
        return False
    s.add(DpoAlert(key=k, tenant_id=tenant))
    return True


def _tenants() -> list[str]:
    with session() as s:
        t = set(s.scalars(select(DpoSettings.tenant_id)).all())
        t |= set(s.scalars(select(DpoRequest.tenant_id)).all())
        t |= set(s.scalars(select(DpoBreach.tenant_id)).all())
        t |= set(s.scalars(select(DpoActivity.tenant_id)).all())
        return sorted(t)


def tick(when: datetime | None = None) -> dict:
    """Worker, every minute: breach clocks (24 h / 6 h left, overdue), request due windows (15 / 7 / 1 / 0 days, late), vendor
    DPA review dates, law phase dates (30 days before), retention review once a month, morning note at her time."""
    n = _aware(when) or now()
    out = {"alerts": 0, "morning": 0}
    for tenant in _tenants():
        try:
            loc = n.astimezone(_tz(tenant))
            on = loc.date()
            alerts = []
            with session() as s:
                for b in s.scalars(select(DpoBreach).where(DpoBreach.tenant_id == tenant, DpoBreach.status == "open")).all():
                    if b.report_at or not b.report_due:
                        continue
                    left = (_aware(b.report_due) - n).total_seconds() / 3600
                    win = "late" if left < 0 else ("6h" if left <= 6 else ("24h" if left <= 24 else None))
                    if win and _once(s, tenant, f"breach:{b.id}:{win}"):
                        alerts.append({"kind": "breach", "ref": b.number,
                                       "say": f"Breach {b.number}: Board ki 72 ghante wali report " +
                                              ("ka samay nikal gaya: turant bhejiye aur der ki wajah likhiye." if win == "late" else
                                               f"ke {round(left)} ghante baaki.")})
                for r in s.scalars(select(DpoRequest).where(DpoRequest.tenant_id == tenant,
                                                            DpoRequest.status.in_(("new", "working", "waiting")))).all():
                    due = _date(r.due_on)
                    if not due:
                        continue
                    dl = (due - on).days
                    win = "late" if dl < 0 else next((w for w in (0, 1, 7, 15) if dl <= w), None)
                    if win is not None and _once(s, tenant, f"req:{r.id}:{win}"):
                        alerts.append({"kind": "request", "ref": r.number,
                                       "say": f"Maang {r.number} ({R.KINDS.get(r.kind, ('', ''))[0]}): " +
                                              ("jawab ki taarikh nikal gayi." if win == "late" else f"jawab {r.due_on} tak ({dl} din).")})
                for v in s.scalars(select(DpoVendor).where(DpoVendor.tenant_id == tenant)).all():
                    rv = _date(v.review_on)
                    if rv and (rv - on).days <= 30 and _once(s, tenant, f"vendor:{v.id}:{v.review_on}"):
                        alerts.append({"kind": "vendor", "ref": v.name, "say": f"{v.name} ka data contract (DPA) review {v.review_on} ko."})
                for what, d in (("Consent manager niyam (Rule 4)", R.CONSENT_MANAGER_FROM),
                                ("Notice / consent / rights / breach ke niyam (Rules 3, 5-16)", R.MAIN_DUTIES_FROM)):
                    if 0 <= (d - on).days <= 30 and _once(s, tenant, f"phase:{d.isoformat()}"):
                        alerts.append({"kind": "phase", "ref": d.isoformat(), "say": f"{what} {d.strftime('%d-%m-%Y')} se lagu: taiyaari dekh lijiye."})
            month = on.strftime("%Y-%m")
            for rt in retention(tenant):
                if rt["older"]:
                    with session() as s:
                        if _once(s, tenant, f"ret:{rt['activity']}:{month}"):
                            alerts.append({"kind": "retention", "ref": rt["activity"], "say": f"{rt['activity']} {rt['name']}: {rt['say']}"})
            for a in alerts:
                out["alerts"] += 1
                _publish(tenant, "dpo_alert", a)
            if _morning_due(tenant, loc):
                d = day(tenant)
                with session() as s:
                    _st(s, tenant).last_morning = on.isoformat()
                if d["say"] != "Data suraksha: aaj sab theek.":
                    _publish(tenant, "dpo_day", {"say": d["say"], "requests": len(d["requests"]), "breaches": len(d["breaches"]),
                                                 "cards": len(d["cards"])})
                    out["morning"] += 1
        except Exception:
            log.exception("dpo tick failed for %s", tenant)
    return out


def _morning_due(tenant: str, loc: datetime) -> bool:
    with session() as s:
        r = s.get(DpoSettings, tenant)
        if r is None or r.last_morning == loc.date().isoformat():
            return False
        try:
            hh, mm = (int(x) for x in (r.morning_time or "09:30").split(":"))
        except ValueError:
            hh, mm = 9, 30
        return (loc.hour, loc.minute) >= (hh, mm)
