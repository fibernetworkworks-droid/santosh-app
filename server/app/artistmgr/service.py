"""Artist Sahayak: Hoola as a musician's manager (artist roster, gig calendar, offers / riders / contracts, travel, royalty
registrations, release plans, settlements and splits), end to end.

  1. Roster: artists / bands with members (and their split %), rider (tech / hospitality / travel), fee notes in HER words,
     royalty-registration checklist (IPRS / ISAMRA / PPL / ISRC / IPI / distributor / Content ID / copyright / PAN-GST).
  2. Gig calendar: an offer pasted from WhatsApp / email / call = an enquiry G-0001 with only the facts that are written.
     HOLD (expires by itself) and CONFIRMED gigs block the artist's time. A second gig that overlaps - or leaves less than HER
     gap (same city / travel) - is REFUSED IN CODE, even for her, and so is a gig on a day she blocked or one that needs a
     band member who is already booked with another artist.
  3. Money in plain numbers: fee (the promoter's / her number, never guessed), advance + balance, payments she records,
     promoter's TDS (her word, a tax credit), expenses, HER commission %, net to the artist and member splits.
  4. Releases: tracks with ISRC (shape checked), writers with splits that must total 100 and IPI, UPC check digit,
     the distributor's lead time from HER terms, Spotify pitch 7 days before, IPRS work registration.

Waits for HER tap (only the app API passes by_tap=True; tools only make the card):
  * any reply / message to a promoter, artist or member, the contract + rider, the invoice, any payment request,
  * a hold becoming a confirmed gig (the clash test runs again at the tap),
  * the release metadata going final (what she then delivers on her distributor),
  * a payout statement to the artist / members (money: her phone's fingerprint once a phone key is active).
Hoola never takes or sends money (UPI links go to HER UPI ID), never logs in to IPRS / PPL / ISAMRA / a distributor, never
invents a fee, date, royalty or code."""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import secrets
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote as urlq

from sqlalchemy import select

from ..db import now, session
from . import rules as R
from .models import (
    ArtistmgrAlert,
    ArtistmgrArtist,
    ArtistmgrBlock,
    ArtistmgrCard,
    ArtistmgrGig,
    ArtistmgrPayout,
    ArtistmgrRelease,
    ArtistmgrRoyalty,
    ArtistmgrSettings,
)

log = logging.getLogger("santosh.artistmgr")
_LOCK = threading.RLock()
MONEY_CARDS = ("payout",)
CARD_KINDS = ("reply", "contract", "confirm", "invoice", "pay", "payout", "message", "release")
CARD_TITLE = {"reply": "Promoter ko jawab", "contract": "Contract + rider promoter ko", "confirm": "Hold ko pakka gig",
              "invoice": "Invoice promoter ko", "pay": "Paise maangna", "payout": "Artist ko payout statement",
              "message": "Message", "release": "Release metadata final"}
STATUS = {"enquiry": "Enquiry", "hold": "Hold (kachcha)", "confirmed": "Pakka", "done": "Ho gaya", "cancelled": "Radd"}
ROYALTY_SOURCES = ("iprs", "isamra", "ppl", "distributor", "youtube", "sync", "other")


class ArtistError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


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


def _date(v, tenant: str = "") -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if not v:
        return None
    s = str(v).strip()
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s[:10], f).date()
        except ValueError:
            pass
    return R.date_of(s, today(tenant) if tenant else date.today())


def _num(v) -> float | None:
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = R.money_of(f"rs {v}") if re.search(r"lakh|lac|k\b|hazaar|crore|cr\b", str(v).lower()) else None
    if m is not None:
        return m
    s = re.sub(r"[^\d.\-]", "", str(v).replace(",", ""))
    try:
        return float(s) if s not in ("", "-", ".") else None
    except ValueError:
        return None


def _pct(v, name: str, hi: float = 100) -> float | None:
    n = _num(v)
    if n is None:
        return None
    if not 0 <= n <= hi:
        raise ArtistError(f"{name} 0 se {hi:g}% ke beech.")
    return n


def _rs(v: float | None) -> str:
    if v is None:
        return "[daam?]"
    try:
        from ..india.money import inr
        return inr(v)
    except Exception:
        return f"₹{v:,.0f}"


def _pdf_rs(v: float | None) -> str:
    return "[ ? ]" if v is None else "Rs. " + f"{v:,.2f}"


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("artistmgr publish failed")


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
        return str(actor)[:40]


def _need_owner(actor: str) -> None:
    if not is_owner(actor):
        raise ArtistError("Sirf owner.")


def _st(s, tenant: str) -> ArtistmgrSettings:
    r = s.get(ArtistmgrSettings, tenant)
    if r is None:
        r = ArtistmgrSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _wa(phone: str, text: str) -> str:
    d = R.phone(phone)
    return f"https://wa.me/91{d}?text={urlq(text)}" if d else ""


def _sms(phone: str, text: str) -> str:
    d = R.phone(phone)
    return f"sms:+91{d}?body={urlq(text)}" if d else ""


def _draft(phone: str, text: str, **extra) -> dict:
    return {"text": text, "wa": _wa(phone, text), "sms": _sms(phone, text), **extra}


def _upi_of(tenant: str) -> tuple[str, str]:
    with session() as s:
        st = _st(s, tenant)
        upi, nm = st.upi_id, st.agency
    if not upi:
        try:
            from ..employee import service as emp
            p = emp.profile(tenant) or {}
            upi = p.get("upi_id") or ""
            nm = nm or p.get("upi_name") or p.get("business_name") or ""
        except Exception:
            upi = ""
    return upi, nm


def _upi(tenant: str, amount: float | None, note: str) -> str:
    upi, nm = _upi_of(tenant)
    if not upi or not amount or amount <= 0:
        return ""
    return f"upi://pay?pa={urlq(upi)}&pn={urlq(nm)}&am={amount:.2f}&cu=INR&tn={urlq(note[:40])}"


def _store(tenant: str, name: str, data: bytes, mime: str, conv: str = "", title: str = "") -> dict:
    from .. import chatfiles
    f = chatfiles.store(tenant, name, data, mime)
    _publish(tenant, "pc_file", {**f, "source": "artistmgr", "title": title or name}, conv)
    return f


def _fy(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def _log(g: ArtistmgrGig, text: str, by: str = "") -> None:
    lg = _j(g.log, [])
    lg.append({"at": now().isoformat(), "what": R.clean(text, 300), "by": by})
    g.log = _dump(lg[-80:])


def _hhmm_or_err(v, what: str) -> str:
    if v in (None, ""):
        return ""
    t = R.hhmm(v)
    if not t:
        raise ArtistError(f"{what} '{v}' samajh nahi aaya (jaise 20:30 ya 8:30 pm).")
    return t


# ---------------------------------------------------------------- settings
_SET_KEYS = ("agency", "gstin", "address", "phone", "email", "upi_id", "commission_pct", "royalty_pct", "same_city_gap", "travel_gap",
             "hold_hours", "advance_pct", "balance_days", "distributors", "terms", "rules", "morning_time")


def _distributors(st: ArtistmgrSettings) -> list[dict]:
    return _j(st.distributors, [])


def _settings_view(st: ArtistmgrSettings) -> dict:
    return {"agency": st.agency, "gstin": st.gstin, "address": st.address, "phone": st.phone, "email": st.email, "upi_id": st.upi_id,
            "commission_pct": st.commission_pct, "royalty_pct": st.royalty_pct, "same_city_gap": st.same_city_gap,
            "travel_gap": st.travel_gap, "hold_hours": st.hold_hours, "advance_pct": st.advance_pct, "balance_days": st.balance_days,
            "distributors": _distributors(st), "terms": st.terms, "rules": st.rules, "morning_time": st.morning_time,
            "organiser_duties": R.ORGANISER_DUTIES, "performer_clause": R.PERFORMER_CLAUSE}


def settings(tenant: str) -> dict:
    with session() as s:
        return _settings_view(_st(s, tenant))


def save_settings(tenant: str, actor: str = "owner", **kw: Any) -> dict:
    _need_owner(actor)
    notes = []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        if "gstin" in kw:
            g = str(kw["gstin"] or "").strip().upper()
            if g and not R.gstin_ok(g):
                raise ArtistError(f"GSTIN '{g}' sahi nahi lagta.")
            st.gstin = g
        for k in ("agency", "address", "email", "terms", "rules"):
            if k in kw:
                setattr(st, k, R.clean(kw[k], 3000 if k in ("terms", "rules") else 300))
        if "phone" in kw:
            p = R.phone(kw["phone"])
            if kw["phone"] and not p:
                raise ArtistError("10 ank ka mobile number.")
            st.phone = p
        if "upi_id" in kw:
            u = str(kw["upi_id"] or "").strip()
            if u and not re.fullmatch(r"[\w.\-]{2,64}@[A-Za-z][\w]{1,40}", u):
                raise ArtistError(f"UPI ID '{u}' sahi nahi lagta (naam@bank).")
            st.upi_id = u
        if "commission_pct" in kw:
            st.commission_pct = _pct(kw["commission_pct"], "Commission", 50)
        if "royalty_pct" in kw:
            st.royalty_pct = _pct(kw["royalty_pct"], "Royalty commission", 50)
        if "advance_pct" in kw:
            v = _pct(kw["advance_pct"], "Advance")
            st.advance_pct = 50.0 if v is None else v
        for k, lo, hi, dflt in (("same_city_gap", 0, 1440, 120), ("travel_gap", 0, 2880, 480), ("hold_hours", 1, 720, 72),
                                ("balance_days", 0, 60, 0)):
            if k in kw:
                n = _num(kw[k])
                if n is None:
                    n = dflt
                if not lo <= n <= hi:
                    raise ArtistError(f"{k} {lo} se {hi} ke beech.")
                setattr(st, k, int(n))
        if "morning_time" in kw:
            st.morning_time = R.hhmm(kw["morning_time"]) or "09:00"
        if "distributors" in kw:
            out = []
            for d in kw["distributors"] or []:
                if not isinstance(d, dict) or not str(d.get("name") or "").strip():
                    continue
                ld = _num(d.get("lead_days"))
                out.append({"name": R.clean(d["name"], 80), "share_pct": _pct(d.get("share_pct"), "Distributor share"),
                            "lead_days": int(ld) if ld is not None and 0 <= ld <= 120 else None,
                            "payout": R.clean(d.get("payout"), 120), "notes": R.clean(d.get("notes"), 300)})
                if ld is None:
                    notes.append(f"{out[-1]['name']}: lead time (kitne din pehle delivery) nahi bataya; release plan mein 'pata nahi' rahega.")
            st.distributors = _dump(out[:12])
        v = _settings_view(st)
    say = "Niyam save." + (" " + " ".join(notes) if notes else "")
    if v["commission_pct"] is None:
        say += " Aapka commission % abhi nahi likha: settlement mein commission ki line khaali rahegi."
    return {"settings": v, "say": say}


# ---------------------------------------------------------------- artists
def _artist_view(a: ArtistmgrArtist, full: bool = False) -> dict:
    v = {"id": a.id, "name": a.name, "kind": a.kind, "kind_label": R.KIND_LABEL.get(a.kind, a.kind), "genre": a.genre,
         "art_form": a.art_form, "phone": a.phone, "email": a.email, "city": a.city, "gstin": a.gstin, "upi_id": a.upi_id,
         "members": _j(a.members, []), "min_fee": a.min_fee, "fee_note": a.fee_note, "commission_pct": a.commission_pct,
         "active": a.active, "forgotten": a.forgotten}
    if full:
        v["rider"] = _j(a.rider, {})
        v["notes"] = a.notes
        v["regs"] = _regs_view(a)
    return v


def _regs_view(a: ArtistmgrArtist) -> list[dict]:
    have = _j(a.regs, {})
    out = []
    for k, d in R.REGS.items():
        h = have.get(k) or {}
        out.append({"key": k, **d, "status": h.get("status", "none"), "ref": h.get("ref", ""), "note": h.get("note", ""),
                    "at": h.get("at", "")})
    return out


def _artist(s, tenant: str, ref: str) -> ArtistmgrArtist:
    ref = str(ref or "").strip()
    if not ref:
        rows = s.scalars(select(ArtistmgrArtist).where(ArtistmgrArtist.tenant_id == tenant, ArtistmgrArtist.active.is_(True))).all()
        if len(rows) == 1:
            return rows[0]
        raise ArtistError("Kaunsa artist? (naam bataiye)")
    a = s.get(ArtistmgrArtist, ref)
    if a is not None and a.tenant_id == tenant:
        return a
    k = R.key_of(ref)
    rows = s.scalars(select(ArtistmgrArtist).where(ArtistmgrArtist.tenant_id == tenant)).all()
    for a in rows:
        if R.key_of(a.name) == k:
            return a
    hits = [a for a in rows if k and k in R.key_of(a.name)]
    if len(hits) == 1:
        return hits[0]
    raise ArtistError(f"Artist '{ref}' nahi mila.")


def _clean_members(members: Any) -> list[dict]:
    out = []
    for m in members or []:
        if isinstance(m, str):
            m = {"name": m}
        if not isinstance(m, dict) or not str(m.get("name") or "").strip():
            continue
        sp = _num(m.get("split_pct"))
        out.append({"name": R.clean(m["name"], 80), "role": R.clean(m.get("role"), 40), "phone": R.phone(m.get("phone")),
                    "split_pct": sp})
    probs = R.split_problems(out)
    if probs:
        raise ArtistError(" ".join(probs))
    return out[:20]


def artist_save(tenant: str, name: str = "", kind: str = "", genre: str = "", phone: str = "", email: str = "", city: str = "",
                members: Any = None, min_fee=None, fee_note: str = "", commission_pct=None, rider: Any = None, gstin: str = "",
                upi_id: str = "", art_form: str = "", notes: str = "", artist_id: str = "", active: Any = None,
                actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        a = None
        if artist_id:
            a = _artist(s, tenant, artist_id)
        elif name:
            try:
                a = _artist(s, tenant, name)
            except ArtistError:
                a = None
        if a is None:
            if not str(name or "").strip():
                raise ArtistError("Artist / band ka naam.")
            a = ArtistmgrArtist(tenant_id=tenant, name=R.clean(name, 120))
            s.add(a)
        if name:
            a.name = R.clean(name, 120)
        if kind:
            k = kind.lower().strip()
            a.kind = k if k in R.KINDS else "other"
        if art_form:
            a.art_form = art_form.lower() if art_form.lower() in ("folk", "classical") else ""
        elif kind and kind.lower() in ("folk", "classical"):
            a.art_form = kind.lower()
        for k, v, n in (("genre", genre, 80), ("city", city, 60), ("fee_note", fee_note, 500), ("notes", notes, 2000), ("email", email, 120)):
            if v:
                setattr(a, k, R.clean(v, n))
        if phone:
            p = R.phone(phone)
            if not p:
                raise ArtistError("10 ank ka mobile number.")
            a.phone = p
        if gstin:
            g = gstin.strip().upper()
            if not R.gstin_ok(g):
                raise ArtistError(f"GSTIN '{g}' sahi nahi lagta.")
            a.gstin = g
        if upi_id:
            a.upi_id = upi_id.strip()[:80]
        if members is not None:
            a.members = _dump(_clean_members(members))
        if min_fee is not None:
            a.min_fee = _num(min_fee)
        if commission_pct is not None:
            a.commission_pct = _pct(commission_pct, "Commission", 50)
        if rider is not None:
            r0 = _j(a.rider, {})
            if isinstance(rider, dict):
                for k in ("tech", "hospitality"):
                    if k in rider:
                        r0[k] = [R.clean(x, 160) for x in (rider[k] or []) if str(x).strip()][:40]
                for k in ("travel", "stay", "notes"):
                    if k in rider:
                        r0[k] = R.clean(rider[k], 600)
            elif isinstance(rider, str):
                r0["notes"] = R.clean(rider, 1500)
            a.rider = _dump(r0)
        if active is not None:
            a.active = bool(active)
        s.flush()
        v = _artist_view(a, True)
    return {"artist": v, "say": f"{v['name']} roster mein save."}


def artists(tenant: str, all_: bool = False) -> list[dict]:
    with session() as s:
        q = select(ArtistmgrArtist).where(ArtistmgrArtist.tenant_id == tenant)
        if not all_:
            q = q.where(ArtistmgrArtist.active.is_(True))
        return [_artist_view(a) for a in s.scalars(q.order_by(ArtistmgrArtist.name)).all()]


def artist_view(tenant: str, ref: str) -> dict:
    with session() as s:
        a = _artist(s, tenant, ref)
        v = _artist_view(a, True)
        gigs = s.scalars(select(ArtistmgrGig).where(ArtistmgrGig.artist_id == a.id).order_by(ArtistmgrGig.day)).all()
        v["gigs"] = [_gig_brief(s, g) for g in gigs if g.status in ("enquiry", "hold", "confirmed")]
        v["releases"] = [_rel_brief(r) for r in s.scalars(select(ArtistmgrRelease).where(ArtistmgrRelease.artist_id == a.id)).all()]
        v["blocks"] = [{"id": b.id, "from": b.day_from, "to": b.day_to, "note": b.note}
                       for b in s.scalars(select(ArtistmgrBlock).where(ArtistmgrBlock.artist_id == a.id, ArtistmgrBlock.active.is_(True))).all()]
        v["ledger"] = _ledger(s, a)
    return v


def reg_set(tenant: str, artist: str, key: str, status: str, ref: str = "", note: str = "", actor: str = "owner") -> dict:
    """Her word that a registration was applied / done (Hoola never logs in to IPRS / PPL / ISAMRA / IMI)."""
    _need_owner(actor)
    key = (key or "").lower().strip()
    if key not in R.REGS:
        raise ArtistError(f"'{key}' nahi pehchana: {', '.join(R.REGS)}.")
    status = (status or "").lower().strip()
    if status not in R.REG_STATUS:
        raise ArtistError("status none | applied | done | na.")
    if key == "ipi" and ref and not R.ipi_ok(ref):
        raise ArtistError("IPI number 9-11 ank ka hota hai.")
    if key == "isrc" and ref and not re.fullmatch(r"[A-Z0-9]{3}", ref.strip().upper()):
        raise ArtistError("ISRC registrant code 3 akshar / ank ka hota hai (jaise K40).")
    with _LOCK, session() as s:
        a = _artist(s, tenant, artist)
        regs = _j(a.regs, {})
        regs[key] = {"status": status, "ref": R.clean(ref, 60).upper() if key == "isrc" else R.clean(ref, 60),
                     "note": R.clean(note, 300), "at": today(tenant).isoformat()}
        a.regs = _dump(regs)
        v = _regs_view(a)
        nm = a.name
    return {"regs": v, "say": f"{nm}: {R.REGS[key]['label']} = {status}."}


def block_days(tenant: str, artist: str, day_from: str, day_to: str = "", note: str = "", actor: str = "owner") -> dict:
    _need_owner(actor)
    a0, b0 = _date(day_from, tenant), _date(day_to or day_from, tenant)
    if not a0 or not b0 or b0 < a0:
        raise ArtistError("Kis din se kis din tak?")
    with _LOCK, session() as s:
        a = _artist(s, tenant, artist)
        hits = [g for g in _active_gigs(s, tenant, a.id) if a0.isoformat() <= g.day <= b0.isoformat()]
        if hits:
            raise ArtistError("In dinon par pehle se gig hai: " + ", ".join(f"{g.number} ({g.day})" for g in hits))
        b = ArtistmgrBlock(tenant_id=tenant, artist_id=a.id, day_from=a0.isoformat(), day_to=b0.isoformat(), note=R.clean(note, 200))
        s.add(b)
        s.flush()
        bid, nm = b.id, a.name
    return {"block": bid, "say": f"{nm}: {a0} se {b0} tak koi gig nahi lagega."}


def unblock(tenant: str, block_id: str, actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        b = s.get(ArtistmgrBlock, block_id)
        if b is None or b.tenant_id != tenant:
            raise ArtistError("Block nahi mila.")
        b.active = False
    return {"say": "Woh din khul gaye."}


# ---------------------------------------------------------------- gigs: the double-booking test
def _expire_holds(s, tenant: str) -> list[ArtistmgrGig]:
    n = clock()
    out = []
    for g in s.scalars(select(ArtistmgrGig).where(ArtistmgrGig.tenant_id == tenant, ArtistmgrGig.status == "hold")).all():
        hu = _aware(g.hold_until)
        if hu and hu <= n:
            g.status, g.hold_until = "enquiry", None
            _log(g, "Hold ka samay khatam: date chhoot gayi")
            out.append(g)
    return out


def _active_gigs(s, tenant: str, artist_id: str) -> list[ArtistmgrGig]:
    return list(s.scalars(select(ArtistmgrGig).where(ArtistmgrGig.tenant_id == tenant, ArtistmgrGig.artist_id == artist_id,
                                                     ArtistmgrGig.status.in_(R.BLOCKING))).all())


def _win(g) -> tuple[datetime, datetime] | None:
    d = _date(g.day)
    if d is None:
        return None
    return R.window(d, g.start or "", g.end or "", g.set_minutes)


def _member_keys(a: ArtistmgrArtist | None) -> dict[str, str]:
    out = {}
    for m in _j(a.members, []) if a else []:
        k = m.get("phone") or R.key_of(m.get("name"))
        if k:
            out[k] = m.get("name") or k
    return out


def _clashes(s, tenant: str, artist_id: str, day: str, start: str, end: str, set_minutes, city: str, gig_id: str = "") -> list[dict]:
    """Everything that stops this time for this artist: her blocked days, any held / confirmed gig of the artist within HER gap,
    and gigs of OTHER artists that share a member (same phone, else same name)."""
    _expire_holds(s, tenant)
    d = _date(day)
    if d is None:
        return []
    st = _st(s, tenant)
    me = R.window(d, start or "", end or "", set_minutes)
    out = []
    for b in s.scalars(select(ArtistmgrBlock).where(ArtistmgrBlock.artist_id == artist_id, ArtistmgrBlock.active.is_(True))).all():
        if b.day_from <= d.isoformat() <= b.day_to:
            out.append({"kind": "block", "say": f"Aapne {b.day_from} se {b.day_to} tak band rakha hai" + (f" ({b.note})" if b.note else "")})
    a = s.get(ArtistmgrArtist, artist_id)
    mine = _member_keys(a)
    others = []
    if mine:
        for o in s.scalars(select(ArtistmgrArtist).where(ArtistmgrArtist.tenant_id == tenant, ArtistmgrArtist.id != artist_id)).all():
            shared = [nm for k, nm in _member_keys(o).items() if k in mine]
            if shared:
                others.append((o, shared))
    pairs = [(g, None) for g in _active_gigs(s, tenant, artist_id)]
    for o, shared in others:
        pairs += [(g, (o, shared)) for g in _active_gigs(s, tenant, o.id)]
    for g, via in pairs:
        if g.id == gig_id:
            continue
        w = _win(g)
        if w is None:
            continue
        gap = R.gap_needed(city, g.city, st.same_city_gap, st.travel_gap)
        if R.clashes(me, w, gap):
            when = f"{g.day} {g.start or 'pura din'}" + (f"-{g.end}" if g.end else "") + (f" {g.city}" if g.city else "")
            if via:
                say = f"{', '.join(via[1])} ({via[0].name} ke saath) {g.number} mein busy: {when}"
            else:
                say = f"{STATUS[g.status]} gig {g.number} ({g.event or g.promoter or 'show'}): {when}"
            out.append({"kind": "gig", "gig": g.number, "status": g.status, "via_member": bool(via), "gap_min": gap, "say": say})
    return out


def _clash_text(c: list[dict]) -> str:
    return "Yeh time khaali nahi (double booking nahi hogi): " + "; ".join(x["say"] for x in c) + "."


# ---------------------------------------------------------------- gigs
def _gig_brief(s, g: ArtistmgrGig) -> dict:
    a = s.get(ArtistmgrArtist, g.artist_id) if g.artist_id else None
    return {"id": g.id, "number": g.number, "artist": a.name if a else "", "status": g.status, "status_label": STATUS.get(g.status, g.status),
            "event": g.event, "event_type": g.event_type, "promoter": g.promoter, "city": g.city, "venue": g.venue, "day": g.day,
            "start": g.start, "end": g.end, "fee": g.fee, "fee_text": _rs(g.fee),
            "hold_until": _aware(g.hold_until).isoformat() if g.hold_until else ""}


def _paid(g: ArtistmgrGig) -> float:
    return round(sum(float(p.get("amount") or 0) for p in _j(g.payments, [])), 2)


def _comm_pct(s, g: ArtistmgrGig) -> float | None:
    a = s.get(ArtistmgrArtist, g.artist_id) if g.artist_id else None
    if a is not None and a.commission_pct is not None:
        return a.commission_pct
    return _st(s, g.tenant_id).commission_pct


def _money(s, g: ArtistmgrGig) -> dict:
    st = _st(s, g.tenant_id)
    m = R.settlement(g.fee, _paid(g), g.tds or 0.0, _comm_pct(s, g), _j(g.expenses, []))
    adv_pct = g.advance_pct if g.advance_pct is not None else st.advance_pct
    if g.fee is not None:
        m["advance"] = round(g.fee * adv_pct / 100, 2)
        m["balance"] = round(g.fee - m["advance"], 2)
        d = _date(g.day)
        m["balance_due"] = (d - timedelta(days=st.balance_days)).isoformat() if d else ""
    else:
        m["advance"] = m["balance"] = None
        m["balance_due"] = ""
    m["advance_pct"] = adv_pct
    return m


def _gig_view(s, g: ArtistmgrGig) -> dict:
    v = _gig_brief(s, g)
    a = s.get(ArtistmgrArtist, g.artist_id) if g.artist_id else None
    v.update({"phone": g.phone, "email": g.email, "promoter_gstin": g.promoter_gstin, "set_minutes": g.set_minutes,
              "ticketed": g.ticketed, "travel_by": g.travel_by, "travel_trip": g.travel_trip, "notes": g.notes,
              "offer_text": g.offer_text, "payments": _j(g.payments, []), "expenses": _j(g.expenses, []), "tds": g.tds,
              "invoice_no": g.invoice_no, "contract_ok": bool(g.contract_ok), "log": _j(g.log, [])[-20:],
              "money": _money(s, g), "tds_note": R.tds_note(g.event_type, g.fee), "cancel": _j(g.cancel, {}),
              "rider": _j(a.rider, {}) if a else {}, "organiser_duties": R.ORGANISER_DUTIES, "forgotten": g.forgotten})
    v["cards"] = [_card_view(c) for c in s.scalars(select(ArtistmgrCard).where(ArtistmgrCard.ref_id == g.id)
                                                   .order_by(ArtistmgrCard.created_at.desc())).all()][:12]
    v["blanks"] = _gig_blanks(g)
    return v


def _gig_blanks(g: ArtistmgrGig) -> list[str]:
    out = []
    if not g.day:
        out.append("tareekh")
    if not g.start:
        out.append("set ka time")
    if g.fee is None:
        out.append("fee")
    if not g.city:
        out.append("shehar")
    if not g.promoter:
        out.append("promoter ka naam")
    if not g.phone:
        out.append("promoter ka phone")
    return out


def _gig(s, tenant: str, ref: str) -> ArtistmgrGig:
    ref = str(ref or "").strip()
    g = s.get(ArtistmgrGig, ref) if ref else None
    if g is None and ref:
        g = s.scalars(select(ArtistmgrGig).where(ArtistmgrGig.tenant_id == tenant, ArtistmgrGig.number == ref.upper())).first()
    if g is None or g.tenant_id != tenant:
        raise ArtistError(f"Gig '{ref}' nahi mila.")
    return g


_GIG_KEYS = ("artist", "event", "event_type", "promoter", "phone", "email", "promoter_gstin", "city", "venue", "day", "start", "end",
             "set_minutes", "fee", "advance_pct", "ticketed", "travel_by", "notes")


def offer(tenant: str, text: str = "", artist: str = "", actor: str = "owner", conv: str = "", **kw: Any) -> dict:
    """A show offer (pasted WhatsApp / email / call note = data) -> enquiry G-0001 with the written facts only."""
    t = today(tenant)
    with session() as s:
        cities = sorted({a.city for a in s.scalars(select(ArtistmgrArtist).where(ArtistmgrArtist.tenant_id == tenant)).all() if a.city})
    facts = R.parse_offer(text, t, cities) if text else {}
    for k in _GIG_KEYS:
        if kw.get(k) not in (None, ""):
            facts[k] = kw[k]
    return gig_save(tenant, "", artist=artist, offer_text=text, actor=actor, conv=conv, **{k: facts[k] for k in facts if k in _GIG_KEYS})


def gig_save(tenant: str, gig: str = "", artist: str = "", offer_text: str = "", actor: str = "owner", conv: str = "", **kw: Any) -> dict:
    notes = []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        if gig:
            g = _gig(s, tenant, gig)
            if g.status in ("done", "cancelled"):
                raise ArtistError(f"{g.number} {STATUS[g.status]}: ab badla nahi ja sakta.")
        else:
            a = _artist(s, tenant, artist or kw.get("artist") or "")
            st.gig_seq += 1
            g = ArtistmgrGig(tenant_id=tenant, number=f"G-{st.gig_seq:04d}", artist_id=a.id, conv=conv,
                             offer_text=R.clean(offer_text, 3000))
            s.add(g)
            _log(g, "Offer aaya" if offer_text else "Gig bana", actor_name(tenant, actor))
        if gig and (artist or kw.get("artist")):
            a = _artist(s, tenant, artist or kw.get("artist"))
            if a.id != g.artist_id and g.status == "confirmed" and not is_owner(actor):
                raise ArtistError("Pakke gig ka artist sirf owner badal sakti hain.")
            g.artist_id = a.id
        old = (g.artist_id, g.day, g.start, g.end, g.set_minutes, g.city)
        if "day" in kw and kw["day"] not in (None, ""):
            d = _date(kw["day"], tenant)
            if d is None:
                raise ArtistError(f"Tareekh '{kw['day']}' samajh nahi aayi.")
            if d < today(tenant):
                raise ArtistError("Yeh tareekh beet chuki hai.")
            g.day = d.isoformat()
        if "start" in kw:
            g.start = _hhmm_or_err(kw["start"], "Start time")
        if "end" in kw:
            g.end = _hhmm_or_err(kw["end"], "End time")
        if "set_minutes" in kw and kw["set_minutes"] not in (None, ""):
            n = _num(kw["set_minutes"])
            if n is None or not 10 <= n <= 720:
                raise ArtistError("Set 10 se 720 minute ka.")
            g.set_minutes = int(n)
        if "fee" in kw and kw["fee"] not in (None, ""):
            f = _num(kw["fee"])
            if f is None or f <= 0:
                raise ArtistError("Fee ek sahi rakam honi chahiye.")
            if g.status == "confirmed" and g.fee is not None and abs(f - g.fee) > 0.5 and not is_owner(actor):
                raise ArtistError("Pakke gig ki fee sirf owner badal sakti hain.")
            g.fee = f
        if "advance_pct" in kw and kw["advance_pct"] not in (None, ""):
            g.advance_pct = _pct(kw["advance_pct"], "Advance")
        if "phone" in kw and kw["phone"]:
            p = R.phone(kw["phone"])
            if not p:
                raise ArtistError("Promoter ka 10 ank ka mobile number.")
            g.phone = p
        if "promoter_gstin" in kw and kw["promoter_gstin"]:
            pg = str(kw["promoter_gstin"]).strip().upper()
            if not R.gstin_ok(pg):
                raise ArtistError(f"Promoter GSTIN '{pg}' sahi nahi lagta.")
            g.promoter_gstin = pg
        if "event_type" in kw and kw["event_type"]:
            et = str(kw["event_type"]).lower()
            g.event_type = et if et in R.EVENT_LABEL else (R.event_of(et) or "other")
        for k, n in (("event", 160), ("promoter", 120), ("email", 120), ("city", 60), ("venue", 160), ("notes", 2000), ("travel_by", 20)):
            if k in kw and kw[k] not in (None, ""):
                setattr(g, k, R.clean(kw[k], n))
        if "ticketed" in kw and kw["ticketed"] is not None:
            g.ticketed = bool(kw["ticketed"])
        if not g.event_type and offer_text:
            g.event_type = R.event_of(offer_text)
        s.flush()
        if g.status in R.BLOCKING and (g.artist_id, g.day, g.start, g.end, g.set_minutes, g.city) != old:
            c = _clashes(s, tenant, g.artist_id, g.day, g.start, g.end, g.set_minutes, g.city, g.id)
            if c:
                raise ArtistError(_clash_text(c))
            _log(g, f"Time / jagah badli: {g.day} {g.start}", actor_name(tenant, actor))
        a = s.get(ArtistmgrArtist, g.artist_id)
        if a and a.min_fee and g.fee is not None and g.fee < a.min_fee:
            notes.append(f"Fee {_rs(g.fee)} {a.name} ki aapki minimum fee {_rs(a.min_fee)} se kam hai.")
        c = _clashes(s, tenant, g.artist_id, g.day, g.start, g.end, g.set_minutes, g.city, g.id) if g.day else []
        v = _gig_view(s, g)
        cv = g.conv
    if c and v["status"] not in R.BLOCKING:
        notes.append(_clash_text(c) + " Hold / pakka nahi ho payega.")
    if v["blanks"]:
        notes.append("Abhi nahi pata: " + ", ".join(v["blanks"]) + " (main andaaza nahi lagaunga).")
    say = f"{v['number']} ({v['artist']}): {v['day'] or 'tareekh?'} {v['start']} {v['city']}, fee {v['fee_text']}. " + " ".join(notes)
    if not gig:
        _publish(tenant, "artistmgr_gig", {"gig": v, "say": say}, cv or conv)
    return {"gig": v, "clashes": c, "say": say.strip()}


def hold(tenant: str, gig: str, hours=None, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        g = _gig(s, tenant, gig)
        st = _st(s, tenant)
        if g.status not in ("enquiry", "hold"):
            raise ArtistError(f"{g.number} {STATUS[g.status]} hai.")
        if not g.day:
            raise ArtistError("Pehle tareekh.")
        c = _clashes(s, tenant, g.artist_id, g.day, g.start, g.end, g.set_minutes, g.city, g.id)
        if c:
            raise ArtistError(_clash_text(c))
        h = int(_num(hours) or st.hold_hours)
        if h <= 0:
            raise ArtistError("Hold ke ghante.")
        if not is_owner(actor):
            h = min(h, st.hold_hours)
        g.status, g.hold_until = "hold", clock() + timedelta(hours=h)
        _log(g, f"Hold {h} ghante", actor_name(tenant, actor))
        v = _gig_view(s, g)
    return {"gig": v, "say": f"{v['number']} {h} ghante ke liye hold (is beech koi aur gig is time nahi lagega)."}


def release(tenant: str, gig: str, actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        g = _gig(s, tenant, gig)
        if g.status == "confirmed":
            raise ArtistError("Pakka gig chhodna = cancel (sirf owner, wajah ke saath).")
        if g.status == "hold":
            g.status, g.hold_until = "enquiry", None
            _log(g, "Hold chhoda", actor_name(tenant, actor))
        v = _gig_view(s, g)
    return {"gig": v, "say": f"{v['number']} ka hold chhoda."}


def paid(tenant: str, gig: str, amount, mode: str = "upi", ref: str = "", day: str = "", actor: str = "owner") -> dict:
    """Her word that money came (into her / the artist's account). Hoola never takes money."""
    _need_owner(actor)
    n = _num(amount)
    if n is None or n <= 0:
        raise ArtistError("Kitne paise aaye?")
    mode = (mode or "upi").lower()
    if mode not in ("upi", "cash", "bank", "cheque"):
        raise ArtistError("mode upi | cash | bank | cheque.")
    with _LOCK, session() as s:
        g = _gig(s, tenant, gig)
        rows = _j(g.payments, [])
        d = _date(day, tenant) or today(tenant)
        rows.append({"id": secrets.token_hex(4), "amount": round(n, 2), "mode": mode, "ref": R.clean(ref, 40)[-6:], "day": d.isoformat()})
        g.payments = _dump(rows)
        _log(g, f"Paise mile {_rs(n)} ({mode})", "Owner")
        m = _money(s, g)
        num = g.number
    warn = " Ek din mein ek vyakti se Rs 2 lakh ya zyada cash: Income-tax Act 2025 s.221 (purana 269ST) dekhiye." if mode == "cash" and n >= 200000 else ""
    left = m["due_from_promoter"]
    return {"money": m, "say": f"{num}: {_rs(n)} mile. " + (f"Baaki {_rs(left)}." if left and left > 0.5 else "Poori fee aa gayi.") + warn}


def set_tds(tenant: str, gig: str, amount, actor: str = "owner") -> dict:
    _need_owner(actor)
    n = _num(amount)
    if n is None or n < 0:
        raise ArtistError("TDS kitna kata?")
    with _LOCK, session() as s:
        g = _gig(s, tenant, gig)
        if g.fee is not None and n > g.fee:
            raise ArtistError("TDS fee se zyada nahi ho sakta.")
        g.tds = round(n, 2)
        _log(g, f"Promoter ne TDS kata {_rs(n)}", "Owner")
        m = _money(s, g)
        num = g.number
    return {"money": m, "say": f"{num}: TDS {_rs(n)} likha. Promoter se Form 16A maangiye (artist ke PAN par 26AS mein dikhega)."}


def expense(tenant: str, gig: str, what: str, amount, paid_by: str = "manager", actor: str = "owner") -> dict:
    _need_owner(actor)
    n = _num(amount)
    if n is None or n <= 0 or not str(what or "").strip():
        raise ArtistError("Kya kharcha aur kitna?")
    pb = (paid_by or "manager").lower()
    if pb not in ("manager", "artist", "promoter"):
        raise ArtistError("paid_by manager | artist | promoter.")
    with _LOCK, session() as s:
        g = _gig(s, tenant, gig)
        ex = _j(g.expenses, [])
        ex.append({"what": R.clean(what, 120), "amount": round(n, 2), "paid_by": pb})
        g.expenses = _dump(ex[:60])
        m = _money(s, g)
        num = g.number
    return {"money": m, "say": f"{num}: kharcha {what} {_rs(n)} ({pb})."}


def done(tenant: str, gig: str, actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        g = _gig(s, tenant, gig)
        if g.status != "confirmed":
            raise ArtistError("Sirf pakka gig 'ho gaya' ho sakta hai.")
        g.status = "done"
        _log(g, "Show ho gaya", "Owner")
        m = _money(s, g)
        num = g.number
    say = f"{num} ho gaya."
    if not m["fully_paid"]:
        say += f" Promoter se abhi {_rs(m['due_from_promoter'])} baaki (TDS ke baad)."
    return {"money": m, "say": say}


def cancel(tenant: str, gig: str, reason: str = "", by: str = "promoter", actor: str = "owner") -> dict:
    _need_owner(actor)
    if not str(reason or "").strip():
        raise ArtistError("Cancel ki wajah likhiye.")
    with _LOCK, session() as s:
        g = _gig(s, tenant, gig)
        if g.status in ("done", "cancelled"):
            raise ArtistError(f"{g.number} pehle hi {STATUS[g.status]}.")
        was = g.status
        g.status, g.hold_until = "cancelled", None
        g.cancel = _dump({"by": by, "reason": R.clean(reason, 300), "was": was, "paid": _paid(g), "on": today(tenant).isoformat()})
        _log(g, f"Cancel ({by}): {reason}", "Owner")
        for c in s.scalars(select(ArtistmgrCard).where(ArtistmgrCard.ref_id == g.id, ArtistmgrCard.status == "waiting")).all():
            c.status = "stale"
        num, pd = g.number, _paid(g)
    say = f"{num} radd; artist ka woh time ab khaali."
    if pd:
        say += f" {_rs(pd)} aaya tha: contract ki cancellation shart ke hisaab se kitna lautana / rakhna hai, aap tay kijiye."
    return {"say": say}


def travel_link(tenant: str, gig: str, origin: str = "", actor: str = "owner", conv: str = "") -> dict:
    """Make a Travel Sahayak trip for the gig (only facts of the gig; booking there waits for her tap as always)."""
    with session() as s:
        g = _gig(s, tenant, gig)
        if g.travel_trip:
            return {"say": f"{g.number} ki trip pehle se: {g.travel_trip}.", "trip": g.travel_trip}
        a = s.get(ArtistmgrArtist, g.artist_id)
        if not g.city or not g.day:
            raise ArtistError("Pehle gig ka shehar aur tareekh.")
        names = [{"name": m["name"]} for m in _j(a.members, [])] if a else []
        if a and not names:
            names = [{"name": a.name}]
        d = _date(g.day)
        args = dict(destination=g.city, start_date=(d - timedelta(days=1)).isoformat(), end_date=(d + timedelta(days=1)).isoformat(),
                    title=f"{a.name if a else ''} · {g.number} {g.city}", origin=origin or (a.city if a else ""), kind="business",
                    for_client=False, prefs=f"Gig {g.number} {g.day} {g.start} {g.venue}".strip())
    try:
        from ..travel import service as T
        out = T.new_trip(tenant, travellers=names, actor=actor, conv=conv, **args)
    except Exception as e:
        raise ArtistError(f"Travel Sahayak trip nahi bana paya: {e}")
    num = (out.get("trip") or {}).get("number", "")
    with _LOCK, session() as s:
        g = _gig(s, tenant, gig)
        g.travel_trip = num
        _log(g, f"Travel trip {num}", actor_name(tenant, actor))
    return {"trip": num, "say": f"{num} trip bani (gig se ek din pehle se ek din baad). Ticket booking Travel mein aapki haan se."}


def forget(tenant: str, gig: str, actor: str = "owner") -> dict:
    """DPDP Act 2023 / Rules 2025: a finished gig keeps its numbers; the promoter's personal contact is removed."""
    _need_owner(actor)
    with _LOCK, session() as s:
        g = _gig(s, tenant, gig)
        if g.status not in ("done", "cancelled"):
            raise ArtistError("Gig poora / radd hone ke baad hi.")
        g.phone, g.email, g.offer_text, g.notes = "", "", "", ""
        g.promoter = "Promoter (hataya)" if g.promoter else ""
        g.forgotten = True
        for c in s.scalars(select(ArtistmgrCard).where(ArtistmgrCard.ref_id == g.id)).all():
            c.show = _dump({"gig": g.number, "hataya": True})
            c.result = "{}"
        _log(g, "Promoter ki details hata di (DPDP)", "Owner")
        num = g.number
    return {"say": f"{num}: promoter ki personal details hata di; hisaab ke number rahe."}


def forget_artist(tenant: str, artist: str, actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        a = _artist(s, tenant, artist)
        if _active_gigs(s, tenant, a.id):
            raise ArtistError("Iske aage ke gig abhi baaki hain.")
        a.phone, a.email, a.upi_id, a.notes, a.gstin = "", "", "", "", ""
        a.members = _dump([{**m, "phone": ""} for m in _j(a.members, [])])
        a.active, a.forgotten = False, True
        nm = a.name
    return {"say": f"{nm}: contact details hata di (DPDP); purane gig / royalty ke number rahe."}


def gigs(tenant: str, status: str = "", artist: str = "", day_from: str = "") -> list[dict]:
    with _LOCK, session() as s:
        _expire_holds(s, tenant)
        q = select(ArtistmgrGig).where(ArtistmgrGig.tenant_id == tenant)
        if status:
            q = q.where(ArtistmgrGig.status == status)
        if artist:
            q = q.where(ArtistmgrGig.artist_id == _artist(s, tenant, artist).id)
        if day_from:
            q = q.where(ArtistmgrGig.day >= day_from)
        return [_gig_brief(s, g) for g in s.scalars(q.order_by(ArtistmgrGig.day, ArtistmgrGig.start)).all()][:200]


def gig_view(tenant: str, ref: str) -> dict:
    with _LOCK, session() as s:
        _expire_holds(s, tenant)
        return _gig_view(s, _gig(s, tenant, ref))


def check(tenant: str, artist: str, day: str, start: str = "", end: str = "", city: str = "", set_minutes=None) -> dict:
    """Is this artist free then? (read only)"""
    with _LOCK, session() as s:
        a = _artist(s, tenant, artist)
        d = _date(day, tenant)
        if d is None:
            raise ArtistError("Kaunsi tareekh?")
        c = _clashes(s, tenant, a.id, d.isoformat(), R.hhmm(start), R.hhmm(end), _num(set_minutes), city)
        nm = a.name
    return {"artist": nm, "day": d.isoformat(), "free": not c, "clashes": c,
            "say": f"{nm} {d} ko {'khaali hai' if not c else 'khaali nahi'}." + ("" if not c else " " + _clash_text(c))}


def calendar(tenant: str, month: str = "", artist: str = "") -> dict:
    m = month or today(tenant).strftime("%Y-%m")
    if not re.fullmatch(r"20\d\d-\d\d", m):
        raise ArtistError("Mahina YYYY-MM.")
    with _LOCK, session() as s:
        _expire_holds(s, tenant)
        q = select(ArtistmgrGig).where(ArtistmgrGig.tenant_id == tenant, ArtistmgrGig.day.like(f"{m}-%"),
                                       ArtistmgrGig.status.in_(("enquiry", "hold", "confirmed", "done")))
        if artist:
            q = q.where(ArtistmgrGig.artist_id == _artist(s, tenant, artist).id)
        days: dict[str, list] = {}
        for g in s.scalars(q.order_by(ArtistmgrGig.day, ArtistmgrGig.start)).all():
            days.setdefault(g.day, []).append(_gig_brief(s, g))
        blocks = []
        for b in s.scalars(select(ArtistmgrBlock).where(ArtistmgrBlock.tenant_id == tenant, ArtistmgrBlock.active.is_(True))).all():
            if b.day_from[:7] <= m <= b.day_to[:7]:
                a = s.get(ArtistmgrArtist, b.artist_id)
                blocks.append({"id": b.id, "artist": a.name if a else "", "from": b.day_from, "to": b.day_to, "note": b.note})
    return {"month": m, "days": days, "blocks": blocks}


# ---------------------------------------------------------------- invoice maths
def _invoice(s, tenant: str, g: ArtistmgrGig) -> dict:
    st = _st(s, tenant)
    a = s.get(ArtistmgrArtist, g.artist_id)
    issuer_gstin = (a.gstin if a and a.gstin else st.gstin) or ""
    pct, note = R.gst_note(issuer_gstin, a.art_form if a else "", g.fee)
    base = g.fee or 0.0
    same = bool(issuer_gstin and g.promoter_gstin and issuer_gstin[:2] == g.promoter_gstin[:2]) or not g.promoter_gstin
    t = R.gst_lines(base, pct, same)
    total = round(base + t["tax"], 2) if g.fee is not None else None
    words = ""
    if total:
        try:
            from ..india.money import rupees_words
            words = rupees_words(total, "en")
        except Exception:
            words = ""
    return {"issuer": a.name if a and a.gstin else (st.agency or (a.name if a else "")), "issuer_gstin": issuer_gstin,
            "fee": g.fee, "gst_pct": pct, **t, "total": total, "total_text": _rs(total), "words": words, "gst_note": note,
            "tds_note": R.tds_note(g.event_type, g.fee), "same_state": same}


# ---------------------------------------------------------------- releases
def _rel_brief(r: ArtistmgrRelease) -> dict:
    return {"id": r.id, "number": r.number, "title": r.title, "kind": r.kind, "day": r.day, "distributor": r.distributor,
            "status": r.status}


def _rel(s, tenant: str, ref: str) -> ArtistmgrRelease:
    ref = str(ref or "").strip()
    r = s.get(ArtistmgrRelease, ref) if ref else None
    if r is None and ref:
        r = s.scalars(select(ArtistmgrRelease).where(ArtistmgrRelease.tenant_id == tenant, ArtistmgrRelease.number == ref.upper())).first()
    if r is None or r.tenant_id != tenant:
        raise ArtistError(f"Release '{ref}' nahi mila.")
    return r


def _clean_tracks(tracks: Any) -> list[dict]:
    out = []
    seen = set()
    for t in tracks or []:
        if isinstance(t, str):
            t = {"title": t}
        if not isinstance(t, dict) or not str(t.get("title") or "").strip():
            continue
        code = R.isrc(t.get("isrc")) if t.get("isrc") else ""
        raw = str(t.get("isrc") or "").strip()
        if code and code in seen:
            raise ArtistError(f"ISRC {R.isrc_pretty(code)} do gaanon par: har recording ka apna code hota hai.")
        if code:
            seen.add(code)
        ws = []
        for w in t.get("writers") or []:
            if isinstance(w, str):
                w = {"name": w}
            if isinstance(w, dict) and str(w.get("name") or "").strip():
                ws.append({"name": R.clean(w["name"], 80), "role": R.clean(w.get("role"), 30) or "writer",
                           "share": _num(w.get("share")), "ipi": re.sub(r"\D", "", str(w.get("ipi") or ""))})
        out.append({"title": R.clean(t["title"], 160), "isrc": code or raw[:20], "writers": ws,
                    "performers": [R.clean(x, 80) for x in (t.get("performers") or []) if str(x).strip()][:20],
                    "explicit": bool(t.get("explicit")), "lyrics": bool(t.get("lyrics")), "language": R.clean(t.get("language"), 30)})
    return out[:40]


def release_save(tenant: str, artist: str = "", title: str = "", kind: str = "", day: str = "", distributor: str = "", upc: str = "",
                 tracks: Any = None, artwork: Any = None, label: str = "", notes: str = "", release: str = "",
                 actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        st = _st(s, tenant)
        if release:
            r = _rel(s, tenant, release)
        else:
            a = _artist(s, tenant, artist)
            if not str(title or "").strip():
                raise ArtistError("Release ka naam.")
            st.rel_seq += 1
            r = ArtistmgrRelease(tenant_id=tenant, number=f"R-{st.rel_seq:03d}", artist_id=a.id)
            s.add(r)
        before = r.final_hash
        if title:
            r.title = R.clean(title, 160)
        if kind:
            r.kind = kind.lower() if kind.lower() in ("single", "ep", "album") else "single"
        if day:
            d = _date(day, tenant)
            if d is None:
                raise ArtistError(f"Release date '{day}' samajh nahi aayi.")
            r.day = d.isoformat()
        if distributor:
            names = {R.key_of(x["name"]): x["name"] for x in _distributors(st)}
            r.distributor = names.get(R.key_of(distributor), R.clean(distributor, 80))
        if upc:
            if not R.upc_ok(upc):
                raise ArtistError(f"UPC / EAN '{upc}' ka check digit galat (12 ya 13 ank).")
            r.upc = re.sub(r"\D", "", upc)
        if tracks is not None:
            r.tracks = _dump(_clean_tracks(tracks))
        if artwork is not None:
            r.artwork = bool(artwork)
        if label:
            r.label = R.clean(label, 120)
        if notes:
            r.notes = R.clean(notes, 1000)
        changed = False
        if r.status in ("final", "delivered") and (tracks is not None or upc or day or title or distributor):
            r.status, r.final_hash = "plan", ""
            changed = True
        s.flush()
        v = _rel_view(s, r)
    say = f"{v['number']} {v['title']}: {len(v['problems'])} baatein baaki." if v["problems"] else f"{v['number']} {v['title']}: sab bhara hai."
    if changed and before:
        say += " Metadata badla: final dobara aapki haan se."
    return {"release": v, "say": say}


def _rel_view(s, r: ArtistmgrRelease) -> dict:
    st = _st(s, r.tenant_id)
    a = s.get(ArtistmgrArtist, r.artist_id)
    tracks = _j(r.tracks, [])
    d = _date(r.day)
    lead = next((x.get("lead_days") for x in _distributors(st) if R.key_of(x["name"]) == R.key_of(r.distributor)), None) if r.distributor else None
    t = today(r.tenant_id)
    plan = R.release_plan(d, lead, t) if d else []
    done_ = _j(r.done, {})
    for p in plan:
        p["done"] = done_.get(p["key"], "")
        if p["done"]:
            p["late"] = False
    probs = []
    if not tracks:
        probs.append("Koi gaana (track) nahi.")
    for tr in tracks:
        probs += R.track_problems(tr)
    if not r.day:
        probs.append("Release date nahi.")
    if not r.distributor:
        probs.append("Distributor nahi chuna.")
    elif lead is None:
        probs.append(f"{r.distributor} ka lead time aapke Niyam mein nahi.")
    if not r.artwork:
        probs.append("Artwork (cover) taiyaar nahi bataya.")
    if r.kind != "single" and not r.upc:
        probs.append("EP / album ka UPC nahi (distributor deta hai).")
    for p in plan:
        if p["late"] and not p["done"] and p["key"] != "release":
            probs.append(f"Der: {p['what']} ({p['by']}).")
    return {**_rel_brief(r), "artist": a.name if a else "", "upc": r.upc, "label": r.label, "tracks": tracks, "artwork": r.artwork,
            "notes": r.notes, "plan": plan, "problems": probs, "final": r.status in ("final", "delivered", "live"),
            "isrc_pretty": [R.isrc_pretty(R.isrc(x.get("isrc"))) for x in tracks if R.isrc(x.get("isrc"))]}


def release_view(tenant: str, ref: str) -> dict:
    with session() as s:
        return _rel_view(s, _rel(s, tenant, ref))


def releases(tenant: str, artist: str = "") -> list[dict]:
    with session() as s:
        q = select(ArtistmgrRelease).where(ArtistmgrRelease.tenant_id == tenant)
        if artist:
            q = q.where(ArtistmgrRelease.artist_id == _artist(s, tenant, artist).id)
        return [_rel_brief(r) for r in s.scalars(q.order_by(ArtistmgrRelease.day)).all()]


def release_step(tenant: str, release: str, step: str, actor: str = "owner") -> dict:
    """Her word that a plan step is done (delivered on her distributor, pitched, IPRS work registered, live)."""
    step = (step or "").lower()
    if step not in ("deliver", "pitch", "iprs", "release"):
        raise ArtistError("step deliver | pitch | iprs | release.")
    with _LOCK, session() as s:
        r = _rel(s, tenant, release)
        if step in ("deliver", "release") and r.status == "plan":
            raise ArtistError("Pehle metadata final (aapki haan ka card), phir delivery.")
        dn = _j(r.done, {})
        dn[step] = today(tenant).isoformat()
        r.done = _dump(dn)
        if step == "deliver":
            r.status = "delivered"
        if step == "release":
            r.status = "live"
        v = _rel_view(s, r)
    return {"release": v, "say": f"{v['number']}: '{step}' ho gaya likha."}


# ---------------------------------------------------------------- royalties + ledger
def royalty_add(tenant: str, artist: str, source: str, amount, period: str = "", release: str = "", ref: str = "",
                actor: str = "owner") -> dict:
    """A line exactly as in HER statement (IPRS / ISAMRA / PPL / distributor / YouTube). Never estimated."""
    _need_owner(actor)
    src = (source or "").lower().strip()
    if src not in ROYALTY_SOURCES:
        raise ArtistError(f"source: {', '.join(ROYALTY_SOURCES)}.")
    n = _num(amount)
    if n is None or n == 0:
        raise ArtistError("Statement mein kitni rakam hai?")
    with _LOCK, session() as s:
        a = _artist(s, tenant, artist)
        rid = _rel(s, tenant, release).id if release else ""
        dup = s.scalars(select(ArtistmgrRoyalty).where(ArtistmgrRoyalty.artist_id == a.id, ArtistmgrRoyalty.source == src,
                                                       ArtistmgrRoyalty.period == R.clean(period, 20),
                                                       ArtistmgrRoyalty.amount == round(n, 2))).first()
        if dup is not None and (ref == "" or dup.ref == R.clean(ref, 80)):
            raise ArtistError("Yahi line pehle se likhi hai (same source, period, rakam).")
        y = ArtistmgrRoyalty(tenant_id=tenant, artist_id=a.id, source=src, period=R.clean(period, 20), amount=round(n, 2),
                             release_id=rid, ref=R.clean(ref, 80))
        s.add(y)
        s.flush()
        nm = a.name
    return {"say": f"{nm}: {src.upper()} {period} {_rs(n)} likha (aapke statement se)."}


def _ledger(s, a: ArtistmgrArtist) -> dict:
    st = _st(s, a.tenant_id)
    gl, total = [], 0.0
    for g in s.scalars(select(ArtistmgrGig).where(ArtistmgrGig.artist_id == a.id, ArtistmgrGig.status == "done",
                                                  ArtistmgrGig.payout_id == "")).all():
        m = _money(s, g)
        gl.append({"kind": "gig", "id": g.id, "ref": g.number, "what": f"{g.number} {g.event or g.city} {g.day}", "fee": g.fee,
                   "received": m["received"], "tds": m["tds"], "commission": m["commission"], "expenses": m["expenses_recover"],
                   "net": m["net_to_artist"], "ready": m["fully_paid"]})
    for y in s.scalars(select(ArtistmgrRoyalty).where(ArtistmgrRoyalty.artist_id == a.id, ArtistmgrRoyalty.payout_id == "")).all():
        comm = round(y.amount * st.royalty_pct / 100, 2) if st.royalty_pct else 0.0
        gl.append({"kind": "royalty", "id": y.id, "ref": y.source.upper(), "what": f"{y.source.upper()} {y.period}", "fee": y.amount,
                   "received": y.amount, "tds": 0.0, "commission": comm, "expenses": 0.0, "net": round(y.amount - comm, 2), "ready": True})
    for x in gl:
        if x["ready"]:
            total += x["net"]
    return {"lines": gl, "ready_total": round(total, 2), "ready_total_text": _rs(round(total, 2)),
            "royalties_by_source": _by_source(s, a)}


def _by_source(s, a: ArtistmgrArtist) -> dict:
    out: dict[str, float] = {}
    for y in s.scalars(select(ArtistmgrRoyalty).where(ArtistmgrRoyalty.artist_id == a.id)).all():
        out[y.source] = round(out.get(y.source, 0) + y.amount, 2)
    return out


# ---------------------------------------------------------------- cards (HER tap)
def _card_view(c: ArtistmgrCard) -> dict:
    sh = _j(c.show, {})
    return {"id": c.id, "kind": c.kind, "title": CARD_TITLE.get(c.kind, c.kind), "status": c.status, "hash": c.hash,
            "show": {k: v for k, v in sh.items() if not k.startswith("_")}, "ref_id": c.ref_id, "money": c.kind in MONEY_CARDS,
            "asked_by": c.asked_by, "reason": c.reason, "result": _j(c.result, {}),
            "created_at": _aware(c.created_at).isoformat() if c.created_at else ""}


def _gig_base(s, g: ArtistmgrGig) -> dict:
    a = s.get(ArtistmgrArtist, g.artist_id)
    return {"gig": g.number, "artist": a.name if a else "", "promoter": g.promoter, "phone": g.phone, "event": g.event,
            "event_label": R.EVENT_LABEL.get(g.event_type or "other", "Event"), "day": g.day, "start": g.start, "end": g.end,
            "city": g.city, "venue": g.venue, "status": g.status}


def _show(s, tenant: str, kind: str, ref: str, inp: dict) -> dict:
    """What the card shows, rebuilt from the state NOW (the hash covers it: any change after the card = stale)."""
    st = _st(s, tenant)
    if kind in ("reply", "contract", "confirm", "invoice", "pay") or (kind == "message" and inp.get("gig")):
        g = s.get(ArtistmgrGig, ref)
        if g is None:
            raise ArtistError("Gig nahi mila.")
        base = _gig_base(s, g)
        m = _money(s, g)
        if kind == "reply":
            text = inp.get("text") or (f"Namaste {g.promoter or ''} ji, {base['artist']} {base['day']} {base['city']} ke liye available hain. "
                                       f"Fee {_rs(g.fee)}, advance {m['advance_pct']:g}% ({_rs(m['advance'])}) booking par, baaki "
                                       f"{m['balance_due'] or 'show se pehle'} tak. Travel / stay / rider alag se. Pakka karne ke liye bataiye.")
            return {**base, "fee": g.fee, "fee_text": _rs(g.fee), "text": R.clean(text, 1500), "_in": inp}
        if kind == "contract":
            a = s.get(ArtistmgrArtist, g.artist_id)
            return {**base, "fee": g.fee, "fee_text": _rs(g.fee), "advance": m["advance"], "advance_text": _rs(m["advance"]),
                    "balance": m["balance"], "balance_text": _rs(m["balance"]), "balance_due": m["balance_due"], "set_minutes": g.set_minutes,
                    "rider": _j(a.rider, {}) if a else {}, "travel_by": g.travel_by, "terms": st.terms,
                    "organiser_duties": R.ORGANISER_DUTIES, "performer_clause": R.PERFORMER_CLAUSE, "tds_note": R.tds_note(g.event_type, g.fee),
                    "_in": inp}
        if kind == "confirm":
            return {**base, "fee": g.fee, "fee_text": _rs(g.fee), "paid": _paid(g), "paid_text": _rs(_paid(g)),
                    "hold_until": _aware(g.hold_until).isoformat() if g.hold_until else "", "_in": inp}
        if kind == "invoice":
            return {**base, "fee": g.fee, "invoice": _invoice(s, tenant, g), "promoter_gstin": g.promoter_gstin, "paid": _paid(g), "_in": inp}
        if kind == "pay":
            upi, _ = _upi_of(tenant)
            return {**base, "label": inp.get("label", ""), "amount": inp.get("amount"), "amount_text": _rs(inp.get("amount")), "upi": upi,
                    "paid": _paid(g), "_in": inp}
        return {**base, "to": inp.get("to", "promoter"), "to_phone": inp.get("to_phone") or g.phone, "text": R.clean(inp.get("text"), 1500),
                "_in": inp}
    if kind == "payout":
        a = s.get(ArtistmgrArtist, ref)
        if a is None:
            raise ArtistError("Artist nahi mila.")
        led = _ledger(s, a)
        lines = [x for x in led["lines"] if x["ready"] and x["id"] in set(inp.get("ids") or [])]
        total = round(sum(x["net"] for x in lines), 2)
        mem = [m for m in _j(a.members, []) if m.get("split_pct") is not None]
        splits = R.share(total, mem) if mem else [{"name": a.name, "split_pct": 100, "amount": total}]
        return {"artist": a.name, "phone": a.phone, "lines": lines, "total": total, "total_text": _rs(total), "amount_text": _rs(total),
                "splits": [{"name": x["name"], "split_pct": x.get("split_pct"), "amount": x["amount"], "phone": x.get("phone", "")} for x in splits],
                "_in": inp}
    if kind == "message":
        a = s.get(ArtistmgrArtist, ref)
        if a is None:
            raise ArtistError("Artist nahi mila.")
        return {"artist": a.name, "to": inp.get("to", "artist"), "to_phone": inp.get("to_phone") or a.phone, "text": R.clean(inp.get("text"), 1500),
                "_in": inp}
    if kind == "release":
        r = s.get(ArtistmgrRelease, ref)
        if r is None:
            raise ArtistError("Release nahi mila.")
        v = _rel_view(s, r)
        return {"release": v["number"], "title": v["title"], "artist": v["artist"], "kind": v["kind"], "day": v["day"],
                "distributor": v["distributor"], "upc": v["upc"], "label": v["label"], "tracks": v["tracks"], "problems": v["problems"],
                "_in": inp}
    raise ArtistError(f"card '{kind}' nahi pehchana.")


def _blockers(kind: str, sh: dict) -> list[str]:
    b = []
    if kind in ("reply", "contract", "invoice", "confirm") and sh.get("fee") is None:
        b.append("fee")
    if kind in ("contract", "confirm", "invoice") and not sh.get("day"):
        b.append("tareekh")
    if kind == "contract" and not sh.get("start"):
        b.append("set ka time")
    if kind in ("reply", "contract", "invoice", "pay") and not sh.get("promoter"):
        b.append("promoter ka naam")
    if kind in ("message", "reply") and not str(sh.get("text") or "").strip():
        b.append("message ka text")
    if kind in ("message",) and not R.phone(sh.get("to_phone")):
        b.append("phone number")
    if kind == "pay" and not sh.get("amount"):
        b.append("rakam")
    if kind == "pay" and not sh.get("upi"):
        b.append("aapka UPI ID (Niyam)")
    if kind == "payout" and not sh.get("lines"):
        b.append("payout ke liye taiyaar line")
    if kind == "release" and sh.get("problems"):
        b += sh["problems"]
    if re.search(r"\[(?:daam|\s*\?\s*)\]", json.dumps(sh, ensure_ascii=False)):
        b.append("khaali jagah [?]")
    return b


def _make_card(tenant: str, kind: str, ref: str, inp: dict, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        _expire_holds(s, tenant)
        show = _show(s, tenant, kind, ref, inp)
        bl = _blockers(kind, show)
        if bl:
            raise ArtistError(f"{CARD_TITLE[kind]} abhi nahi: pehle " + "; ".join(bl) + ".")
        h = R.digest(show)
        old = s.scalars(select(ArtistmgrCard).where(ArtistmgrCard.tenant_id == tenant, ArtistmgrCard.kind == kind,
                                                    ArtistmgrCard.ref_id == ref, ArtistmgrCard.status == "waiting")).all()
        for o in old:
            if o.hash == h:
                return {"card": _card_view(o), "status": "needs_tap", "existing": True,
                        "say": "Yahi card pehle se aapki haan ka intezaar kar raha hai."}
            o.status = "stale"
        g = s.get(ArtistmgrGig, ref)
        c = ArtistmgrCard(tenant_id=tenant, ref_id=ref, kind=kind, show=_dump(show), hash=h, asked_by=actor_name(tenant, actor),
                          conv=conv or (g.conv if g else ""))
        s.add(c)
        s.flush()
        v = _card_view(c)
        cv = c.conv
    tag = v["show"].get("gig") or v["show"].get("release") or v["show"].get("artist") or ""
    say = f"{CARD_TITLE[kind]}: {tag} aapki haan ka card bheja hai."
    _publish(tenant, "artistmgr_card", {"card": v, "say": say}, cv)
    return {"card": v, "status": "needs_tap", "say": say}


def card_view(tenant: str, card_id: str) -> dict:
    with session() as s:
        c = s.get(ArtistmgrCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise ArtistError("Card nahi mila.")
        return _card_view(c)


def cards(tenant: str, status: str = "waiting") -> list[dict]:
    with session() as s:
        q = select(ArtistmgrCard).where(ArtistmgrCard.tenant_id == tenant)
        if status:
            q = q.where(ArtistmgrCard.status == status)
        return [_card_view(c) for c in s.scalars(q.order_by(ArtistmgrCard.created_at.desc())).all()][:100]


def card_challenge(tenant: str, card_id: str) -> dict:
    """approvekey's message format (kind 'artistmgr'): her phone signs this payout card as it is NOW."""
    from .. import approvekey as ak
    c = card_view(tenant, card_id)
    if c["status"] != "waiting" or c["kind"] not in MONEY_CARDS:
        raise ArtistError("Yeh card ab baaki nahi hai.")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|artistmgr|{card_id}|{c['hash']}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="artistmgr", target=card_id, digest=c["hash"], message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    sh = c["show"]
    return {"challenge_id": chid, "message": msg, "show": {"title": f"Payout {sh.get('artist', '')}", "amount": sh.get("total_text", ""),
                                                           "payee": sh.get("artist", "")}, "expires_at": exp.isoformat()}


def _verify_fingerprint(tenant: str, card_id: str, digest: str, proof: dict | None) -> None:
    from .. import approvekey as ak
    if not proof:
        raise ArtistError("fingerprint_needed")
    with session() as s:
        ak._settle(s, tenant)
        ok = ak._check(s, tenant, "artistmgr", card_id, proof, digest)
    if not ok:
        raise ArtistError("fingerprint_invalid")


def decide(tenant: str, card_id: str, yes: bool, card_hash: str = "", reason: str = "", proof: dict | None = None,
           by_tap: bool = False, conv: str = "") -> dict:
    """ONLY from the app's API (her tap). The card's hash must still match the state NOW; the payout card needs her fingerprint
    once a phone key is active."""
    if not by_tap:
        raise ArtistError("Yeh sirf aapke tap se (app ka card).")
    with _LOCK, session() as s:
        _expire_holds(s, tenant)
        c = s.get(ArtistmgrCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise ArtistError("Card nahi mila.")
        if c.status != "waiting":
            return {"card": _card_view(c), "say": f"Yeh card pehle hi '{c.status}' hai."}
        inp = _j(c.show, {}).get("_in", {})
        try:
            now_hash = R.digest(_show(s, tenant, c.kind, c.ref_id, inp))
        except ArtistError:
            now_hash = ""
        ch, kind = c.hash, c.kind
        if now_hash != ch:
            c.status = "stale"
    if not card_hash or card_hash != ch or now_hash != ch:
        raise ArtistError("Card ke baad kuch badal gaya; naya card dekhiye.")
    if yes and kind in MONEY_CARDS:
        from .. import approvekey as ak
        if ak.active_on(tenant):
            _verify_fingerprint(tenant, card_id, card_hash, proof)
    if not yes:
        with _LOCK, session() as s:
            c = s.get(ArtistmgrCard, card_id)
            c.status, c.reason, c.decided_at = "rejected", R.clean(reason, 300), now()
            v = _card_view(c)
        return {"card": v, "say": f"{CARD_TITLE[kind]}: nahi."}
    fn = {"reply": _do_reply, "contract": _do_contract, "confirm": _do_confirm, "invoice": _do_invoice, "pay": _do_pay,
          "payout": _do_payout, "message": _do_message, "release": _do_release}[kind]
    out = fn(tenant, card_id, conv)
    with _LOCK, session() as s:
        c = s.get(ArtistmgrCard, card_id)
        if c.status == "waiting":
            c.status, c.decided_at = "approved", now()
        c.result = _dump({k: v for k, v in out.items() if k in ("draft", "drafts", "file_id", "say")})
        out["card"] = _card_view(c)
    return out


def _card_ctx(card_id: str) -> tuple[dict, str]:
    with session() as s:
        c = s.get(ArtistmgrCard, card_id)
        return _j(c.show, {}), c.ref_id


def _do_reply(tenant: str, card_id: str, conv: str) -> dict:
    sh, gid = _card_ctx(card_id)
    with _LOCK, session() as s:
        g = s.get(ArtistmgrGig, gid)
        _log(g, "Promoter ko jawab aapki haan se", "Owner")
    return {"draft": _draft(sh.get("phone", ""), sh.get("text", "")), "say": f"{sh.get('gig')}: jawab ka draft taiyaar, aap bhejiye."}


def _do_contract(tenant: str, card_id: str, conv: str) -> dict:
    sh, gid = _card_ctx(card_id)
    pdf = contract_pdf(tenant, gid, final=True)
    with _LOCK, session() as s:
        g = s.get(ArtistmgrGig, gid)
        g.contract_ok = R.digest(sh)
        _log(g, "Contract + rider aapki haan se final", "Owner")
        num, phone, prom = g.number, g.phone, g.promoter
    f = _store(tenant, f"{num}_performance_agreement.pdf", pdf, "application/pdf", conv, f"{num} contract + rider")
    text = (f"Namaste {prom} ji, {sh.get('artist')} ke {sh.get('day')} {sh.get('city')} show ({num}) ka performance agreement aur rider "
            f"PDF mein bhej rahe hain: fee {sh.get('fee_text')}, advance {sh.get('advance_text')}. Padh kar sign karke bhej dijiye.")
    return {"draft": _draft(phone, text, file_id=f.get("file_id", "")), "file_id": f.get("file_id", ""),
            "say": f"{num} contract PDF final; draft taiyaar, aap bhejiye (PDF saath lagaiye)."}


def _do_confirm(tenant: str, card_id: str, conv: str) -> dict:
    problem = ""
    with _LOCK, session() as s:                                              # clash test + confirm under one lock
        c = s.get(ArtistmgrCard, card_id)
        g = s.get(ArtistmgrGig, c.ref_id)
        cl = _clashes(s, tenant, g.artist_id, g.day, g.start, g.end, g.set_minutes, g.city, g.id)
        if g.status not in ("enquiry", "hold"):
            problem = f"{g.number} ab {STATUS.get(g.status, g.status)} hai."
        elif cl:
            problem = _clash_text(cl)
        if problem:
            c.status = "stale"
        else:
            g.status, g.hold_until = "confirmed", None
            _log(g, "Pakka gig (aapki haan)", "Owner")
        num = g.number
    if problem:
        raise ArtistError(problem)
    return {"say": f"{num} pakka: artist ka yeh time ab band. Contract / advance ka card chahiye to bataiye."}


def _do_invoice(tenant: str, card_id: str, conv: str) -> dict:
    sh, gid = _card_ctx(card_id)
    with _LOCK, session() as s:
        g = s.get(ArtistmgrGig, gid)
        st = _st(s, tenant)
        if not g.invoice_no:
            st.inv_seq += 1
            g.invoice_no = f"INV/{_fy(today(tenant))}/{st.inv_seq:04d}"
        _log(g, f"Invoice {g.invoice_no}", "Owner")
        num, inv, phone, prom = g.number, g.invoice_no, g.phone, g.promoter
    pdf = invoice_pdf(tenant, gid)
    f = _store(tenant, f"{inv.replace('/', '-')}.pdf", pdf, "application/pdf", conv, f"Invoice {inv}")
    tot = (sh.get("invoice") or {}).get("total")
    due = round((tot or 0) - (sh.get("paid") or 0), 2)
    upi = _upi(tenant, due, f"{inv}")
    text = f"Namaste {prom} ji, {num} show ka invoice {inv}: kul {_rs(tot)}" + (f", baaki {_rs(due)}" if due > 0 else "") + ". PDF saath hai."
    if upi:
        text += f" UPI: {upi}"
    return {"draft": _draft(phone, text, file_id=f.get("file_id", ""), upi=upi), "file_id": f.get("file_id", ""),
            "say": f"Invoice {inv} bana; draft taiyaar, aap bhejiye."}


def _do_pay(tenant: str, card_id: str, conv: str) -> dict:
    sh, gid = _card_ctx(card_id)
    upi = _upi(tenant, sh.get("amount"), f"{sh.get('gig')} {sh.get('label', '')}")
    text = (f"Namaste {sh.get('promoter')} ji, {sh.get('artist')} {sh.get('day')} show ({sh.get('gig')}) ka {sh.get('label') or 'payment'}: "
            f"{sh.get('amount_text')}. UPI se: {upi}")
    with _LOCK, session() as s:
        g = s.get(ArtistmgrGig, gid)
        _log(g, f"Paise maange {sh.get('amount_text')}", "Owner")
    return {"draft": _draft(sh.get("phone", ""), text, upi=upi), "say": "Payment maangne ka draft taiyaar (UPI aapke ID ka), aap bhejiye."}


def _do_message(tenant: str, card_id: str, conv: str) -> dict:
    sh, _ = _card_ctx(card_id)
    return {"draft": _draft(sh.get("to_phone", ""), sh.get("text", "")), "say": "Message draft taiyaar, aap bhejiye."}


def _do_release(tenant: str, card_id: str, conv: str) -> dict:
    sh, rid = _card_ctx(card_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["release", "title", "kind", "release_date", "distributor", "upc", "label", "track_no", "track_title", "isrc",
                "writers (role share% ipi)", "performers", "explicit", "language"])
    for i, t in enumerate(sh.get("tracks") or [], 1):
        ws = "; ".join(f"{x['name']} ({x.get('role', '')} {x.get('share') if x.get('share') is not None else '?'}% {x.get('ipi', '')})"
                       for x in t.get("writers") or [])
        w.writerow([sh.get("release"), sh.get("title"), sh.get("kind"), sh.get("day"), sh.get("distributor"), sh.get("upc"),
                    sh.get("label"), i, t.get("title"), R.isrc_pretty(R.isrc(t.get("isrc"))), ws, ", ".join(t.get("performers") or []),
                    "yes" if t.get("explicit") else "no", t.get("language", "")])
    with _LOCK, session() as s:
        r = s.get(ArtistmgrRelease, rid)
        r.status, r.final_hash = "final", R.digest(sh)
        num = r.number
    f = _store(tenant, f"{num}_metadata.csv", buf.getvalue().encode("utf-8"), "text/csv", conv, f"{num} release metadata")
    return {"file_id": f.get("file_id", ""),
            "say": f"{num} metadata final. Ab aap {sh.get('distributor')} par khud upload kijiye; ho jaye to 'deliver ho gaya' bataiye."}


def _do_payout(tenant: str, card_id: str, conv: str) -> dict:
    sh, aid = _card_ctx(card_id)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        st.pay_seq += 1
        p = ArtistmgrPayout(tenant_id=tenant, number=f"P-{st.pay_seq:04d}", artist_id=aid, lines=_dump(sh.get("lines") or []),
                            total=sh.get("total") or 0.0, splits=_dump(sh.get("splits") or []))
        s.add(p)
        s.flush()
        for ln in sh.get("lines") or []:
            if ln["kind"] == "gig":
                g = s.get(ArtistmgrGig, ln["id"])
                if g:
                    g.payout_id = p.id
            else:
                y = s.get(ArtistmgrRoyalty, ln["id"])
                if y:
                    y.payout_id = p.id
        pid, pnum = p.id, p.number
    pdf = payout_pdf(tenant, pid)
    f = _store(tenant, f"{pnum}_statement.pdf", pdf, "application/pdf", conv, f"{pnum} payout statement")
    drafts = []
    for x in sh.get("splits") or []:
        ph = x.get("phone") or (sh.get("phone") if len(sh.get("splits") or []) == 1 else "")
        text = (f"Namaste {x['name']} ji, {sh.get('artist')} payout {pnum}: aapka hissa {_rs(x['amount'])}"
                + (f" ({x['split_pct']:g}%)" if x.get("split_pct") is not None else "") + ". Statement PDF saath hai.")
        drafts.append({"name": x["name"], **_draft(ph, text)})
    return {"drafts": drafts, "file_id": f.get("file_id", ""), "payout": pnum,
            "say": f"{pnum}: statement {sh.get('total_text')} final. Paise aap khud bhejiye; bhejne ke baad 'payout bhej diya' bataiye."}


def payout_paid(tenant: str, payout: str, ref: str = "", actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        p = s.get(ArtistmgrPayout, payout)
        if p is None:
            p = s.scalars(select(ArtistmgrPayout).where(ArtistmgrPayout.tenant_id == tenant, ArtistmgrPayout.number == str(payout).upper())).first()
        if p is None or p.tenant_id != tenant:
            raise ArtistError("Payout nahi mila.")
        p.status, p.paid_ref = "paid", R.clean(ref, 40)[-8:]
        num = p.number
    return {"say": f"{num}: aapne paise bhej diye, likha."}


def payouts(tenant: str, artist: str = "") -> list[dict]:
    with session() as s:
        q = select(ArtistmgrPayout).where(ArtistmgrPayout.tenant_id == tenant)
        if artist:
            q = q.where(ArtistmgrPayout.artist_id == _artist(s, tenant, artist).id)
        out = []
        for p in s.scalars(q.order_by(ArtistmgrPayout.created_at.desc())).all():
            a = s.get(ArtistmgrArtist, p.artist_id)
            out.append({"id": p.id, "number": p.number, "artist": a.name if a else "", "total": p.total, "total_text": _rs(p.total),
                        "splits": _j(p.splits, []), "status": p.status})
        return out


# ---------------------------------------------------------------- card requests (tools / API make cards; never decide)
def reply_request(tenant: str, gig: str, text: str = "", actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        gid = _gig(s, tenant, gig).id
    return _make_card(tenant, "reply", gid, {"text": R.clean(text, 1500)} if text else {}, actor, conv)


def contract_request(tenant: str, gig: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        g = _gig(s, tenant, gig)
        if g.status in ("done", "cancelled"):
            raise ArtistError(f"{g.number} {STATUS[g.status]}.")
        gid = g.id
    return _make_card(tenant, "contract", gid, {}, actor, conv)


def confirm_request(tenant: str, gig: str, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        _expire_holds(s, tenant)
        g = _gig(s, tenant, gig)
        if g.status not in ("enquiry", "hold"):
            raise ArtistError(f"{g.number} {STATUS[g.status]} hai.")
        c = _clashes(s, tenant, g.artist_id, g.day, g.start, g.end, g.set_minutes, g.city, g.id)
        if c:
            raise ArtistError(_clash_text(c))
        gid = g.id
    return _make_card(tenant, "confirm", gid, {}, actor, conv)


def invoice_request(tenant: str, gig: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        g = _gig(s, tenant, gig)
        if g.status not in ("confirmed", "done"):
            raise ArtistError("Invoice sirf pakke / ho chuke gig ka.")
        gid = g.id
    return _make_card(tenant, "invoice", gid, {}, actor, conv)


def pay_request(tenant: str, gig: str, stage: str = "", amount=None, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        g = _gig(s, tenant, gig)
        if g.status not in ("hold", "confirmed", "done"):
            raise ArtistError("Paise sirf hold / pakke gig ke liye maange jaate hain.")
        m = _money(s, g)
        st = (stage or "").lower()
        n = _num(amount)
        if n is None:
            if st in ("advance", "booking"):
                n, label = m["advance"], "advance"
            elif st in ("balance", "baaki", ""):
                n, label = m["due_from_promoter"], "baaki payment"
            else:
                raise ArtistError("stage advance | balance, ya rakam.")
        else:
            label = st or "payment"
        if n is None or n <= 0:
            raise ArtistError("Maangne ko kuch baaki nahi (ya fee nahi pata).")
        gid = g.id
    return _make_card(tenant, "pay", gid, {"amount": round(n, 2), "label": label}, actor, conv)


def message_request(tenant: str, text: str, gig: str = "", artist: str = "", to: str = "", actor: str = "owner", conv: str = "") -> dict:
    if not str(text or "").strip():
        raise ArtistError("Message mein kya likhna hai?")
    to = (to or "").strip()
    with session() as s:
        if gig:
            g = _gig(s, tenant, gig)
            phone = g.phone
            if to and to.lower() not in ("promoter", ""):
                a = s.get(ArtistmgrArtist, g.artist_id)
                phone = _to_phone(a, to)
            return _make_card(tenant, "message", g.id, {"gig": g.number, "to": to or "promoter", "to_phone": phone, "text": R.clean(text, 1500)},
                              actor, conv)
        a = _artist(s, tenant, artist)
        aid, phone = a.id, _to_phone(a, to)
    return _make_card(tenant, "message", aid, {"to": to or "artist", "to_phone": phone, "text": R.clean(text, 1500)}, actor, conv)


def _to_phone(a: ArtistmgrArtist | None, to: str) -> str:
    if a is None:
        return ""
    if not to or R.key_of(to) in ("artist", R.key_of(a.name)):
        return a.phone
    for m in _j(a.members, []):
        if R.key_of(m.get("name")) == R.key_of(to):
            return m.get("phone") or ""
    p = R.phone(to)
    return p


def release_final_request(tenant: str, release: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        rid = _rel(s, tenant, release).id
    return _make_card(tenant, "release", rid, {}, actor, conv)


def payout_request(tenant: str, artist: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        a = _artist(s, tenant, artist)
        led = _ledger(s, a)
        ids = sorted(x["id"] for x in led["lines"] if x["ready"])
        waiting = [x["what"] for x in led["lines"] if not x["ready"]]
        aid = a.id
    if not ids:
        raise ArtistError("Payout ke liye kuch taiyaar nahi (gig ki poori fee aani chahiye, ya royalty line likhi ho)."
                          + (f" Baaki: {', '.join(waiting)}." if waiting else ""))
    return _make_card(tenant, "payout", aid, {"ids": ids}, actor, conv)


# ---------------------------------------------------------------- PDFs
def _pdf(title: str, blocks: list[tuple], watermark: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    from .. import indicpdf
    pdf = indicpdf.blocks_pdf(title, blocks, watermark)
    if pdf:
        return pdf
    ss = getSampleStyleSheet()
    small = ss["BodyText"].clone("small", fontSize=8.5, leading=10.5)

    def txt(t: str) -> str:
        return indicpdf.rl_markup(escape(str(t or "").replace("₹", "Rs. ")))
    story: list = []
    for b in blocks:
        if b[0] == "h":
            story.append(Paragraph(txt(b[1]), ss["Heading2"]))
        elif b[0] == "h1":
            story.append(Paragraph(txt(b[1]), ss["Title"]))
        elif b[0] == "p":
            story.append(Paragraph(txt(b[1]), ss["BodyText"]))
        elif b[0] == "table":
            rows = [[Paragraph(txt(c), small) for c in r] for r in b[1]]
            t = Table(rows, colWidths=b[2] if len(b) > 2 else None, repeatRows=1)
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(t)
        story.append(Spacer(1, 6))
    bio = io.BytesIO()

    def mark(c, _d):
        if watermark:
            c.saveState()
            c.setFont("Helvetica-Bold", 46)
            c.setFillColor(colors.Color(0.85, 0.2, 0.2, alpha=0.18))
            c.translate(300, 420)
            c.rotate(35)
            c.drawCentredString(0, 0, watermark)
            c.restoreState()
    doc = SimpleDocTemplate(bio, pagesize=A4, title=title, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    doc.build(story, onFirstPage=mark, onLaterPages=mark)
    return bio.getvalue()


def _head(st: ArtistmgrSettings, title: str) -> list[tuple]:
    out = [("h1", title)]
    who = " · ".join(x for x in (st.agency, f"GSTIN {st.gstin}" if st.gstin else "") if x)
    contact = " · ".join(x for x in (st.address, st.phone, st.email) if x)
    if who:
        out.append(("p", who))
    if contact:
        out.append(("p", contact))
    return out


def contract_pdf(tenant: str, gig: str, final: bool = False) -> bytes:
    with session() as s:
        g = _gig(s, tenant, gig)
        st = _st(s, tenant)
        sh = _show(s, tenant, "contract", g.id, {})
        rider = sh.get("rider") or {}
        blocks = _head(st, f"Performance agreement {g.number}") + [
            ("p", f"Artist: {sh['artist']}  ·  Promoter / organiser: {g.promoter or '[____]'}"
                  + (f" (GSTIN {g.promoter_gstin})" if g.promoter_gstin else "")),
            ("p", f"Event: {g.event or sh['event_label']} · {g.venue or '[venue]'}, {g.city or '[city]'} · {g.day} · "
                  f"{g.start or '[time]'}" + (f"-{g.end}" if g.end else "") + (f" · set {g.set_minutes} min" if g.set_minutes else "")),
            ("h", "Fee and payment"),
            ("table", [["", "Amount"], ["Fee (before GST)", _pdf_rs(sh.get("fee"))],
                       [f"Advance on signing ({_money(s, g)['advance_pct']:g}%)", _pdf_rs(sh.get("advance"))],
                       [f"Balance by {sh.get('balance_due') or 'show day'}", _pdf_rs(sh.get("balance"))]], [330, 120]),
            ("p", "TDS, if deducted, against Form 16A. GST as per the invoice."),
            ("h", "Organiser's responsibilities"),
            *[("p", "• " + x) for x in R.ORGANISER_DUTIES],
            ("p", "Travel: " + ({"promoter": "by the promoter", "artist": "by the artist"}.get(g.travel_by, "[as agreed]"))),
            ("h", "Recording and broadcast"),
            ("p", R.PERFORMER_CLAUSE),
        ]
        if rider.get("tech") or rider.get("hospitality") or rider.get("notes"):
            blocks.append(("h", "Rider"))
            for x in rider.get("tech") or []:
                blocks.append(("p", "• Tech: " + x))
            for x in rider.get("hospitality") or []:
                blocks.append(("p", "• Hospitality: " + x))
            for k in ("travel", "stay", "notes"):
                if rider.get(k):
                    blocks.append(("p", f"• {k.title()}: {rider[k]}"))
        if st.terms:
            blocks += [("h", "Cancellation and other terms"), ("p", st.terms)]
        else:
            blocks += [("h", "Cancellation and other terms"), ("p", "[Cancellation terms: owner to fill]")]
        blocks += [("p", "Signed for the artist: ____________________     Signed for the organiser: ____________________"),
                   ("p", "Draft prepared with Hoola; please have it checked by your lawyer.")]
    return _pdf(f"Agreement {g.number}", blocks, "" if final else "DRAFT - NOT SENT")


def invoice_pdf(tenant: str, gig: str) -> bytes:
    with session() as s:
        g = _gig(s, tenant, gig)
        st = _st(s, tenant)
        q = _invoice(s, tenant, g)
        rows = [["", "Amount"], [f"Live performance: {g.event or R.EVENT_LABEL.get(g.event_type or 'other')} {g.day} {g.city}", _pdf_rs(g.fee)]]
        if q["cgst"]:
            rows += [[f"CGST {q['gst_pct'] / 2:g}%", _pdf_rs(q["cgst"])], [f"SGST {q['gst_pct'] / 2:g}%", _pdf_rs(q["sgst"])]]
        if q["igst"]:
            rows.append([f"IGST {q['gst_pct']:g}%", _pdf_rs(q["igst"])])
        rows.append(["TOTAL", _pdf_rs(q["total"])])
        blocks = _head(st, f"Tax invoice {g.invoice_no or '[number]'}") + [
            ("p", f"From: {q['issuer']}" + (f" (GSTIN {q['issuer_gstin']})" if q["issuer_gstin"] else "")),
            ("p", f"To: {g.promoter}" + (f" (GSTIN {g.promoter_gstin})" if g.promoter_gstin else "")),
            ("p", f"Date: {today(tenant).isoformat()} · Gig {g.number}"),
            ("table", rows, [330, 120]),
        ]
        if q["words"]:
            blocks.append(("p", f"In words: {q['words']}"))
        if _paid(g):
            blocks.append(("p", f"Received so far: {_pdf_rs(_paid(g))}"))
        blocks.append(("p", q["gst_note"]))
    return _pdf(f"Invoice {g.invoice_no}", blocks)


def payout_pdf(tenant: str, payout_id: str) -> bytes:
    with session() as s:
        p = s.get(ArtistmgrPayout, payout_id)
        if p is None or p.tenant_id != tenant:
            raise ArtistError("Payout nahi mila.")
        st = _st(s, tenant)
        a = s.get(ArtistmgrArtist, p.artist_id)
        rows = [["Item", "Gross", "TDS", "Commission", "Expenses", "Net"]]
        for x in _j(p.lines, []):
            rows.append([x["what"], _pdf_rs(x.get("received")), _pdf_rs(x.get("tds")), _pdf_rs(x.get("commission")) if x.get("commission") is not None else "-",
                         _pdf_rs(x.get("expenses")), _pdf_rs(x.get("net"))])
        rows.append(["TOTAL", "", "", "", "", _pdf_rs(p.total)])
        srows = [["Member", "Share", "Amount"]] + [[x["name"], f"{x['split_pct']:g}%" if x.get("split_pct") is not None else "", _pdf_rs(x["amount"])]
                                                  for x in _j(p.splits, [])]
        blocks = _head(st, f"Payout statement {p.number}") + [
            ("p", f"Artist: {a.name if a else ''} · Date {today(tenant).isoformat()}"),
            ("table", rows, [150, 60, 50, 65, 60, 65]), ("h", "Splits"), ("table", srows, [220, 80, 120]),
            ("p", "TDS deducted by promoters is credited to the artist's PAN (Form 16A / 26AS)."),
        ]
    return _pdf(f"Payout {p.number}", blocks)


# ---------------------------------------------------------------- day / overview / worker
def day(tenant: str) -> dict:
    t = today(tenant)
    tm = t + timedelta(days=1)
    with _LOCK, session() as s:
        expired = _expire_holds(s, tenant)
        st = _st(s, tenant)
        rows = s.scalars(select(ArtistmgrGig).where(ArtistmgrGig.tenant_id == tenant, ArtistmgrGig.status.in_(("hold", "confirmed", "done")))).all()
        today_g = [_gig_brief(s, g) for g in rows if g.day == t.isoformat() and g.status == "confirmed"]
        tom_g = [_gig_brief(s, g) for g in rows if g.day == tm.isoformat() and g.status == "confirmed"]
        n = clock()
        holds = [_gig_brief(s, g) for g in rows if g.status == "hold" and g.hold_until and _aware(g.hold_until) <= n + timedelta(hours=24)]
        bal, unsettled = [], []
        for g in rows:
            m = _money(s, g)
            if g.status == "confirmed" and m["balance_due"] and m["balance_due"] <= t.isoformat() and not m["fully_paid"]:
                bal.append(f"{g.number}: {_rs(m['due_from_promoter'])} baaki ({m['balance_due']} tak tha)")
            if g.status == "confirmed" and g.day and g.day < t.isoformat():
                unsettled.append(f"{g.number} ({g.day}) ho gaya? 'done' bataiye")
            if g.status == "done" and not m["fully_paid"]:
                unsettled.append(f"{g.number}: promoter se {_rs(m['due_from_promoter'])} baaki")
        rel = []
        for r in s.scalars(select(ArtistmgrRelease).where(ArtistmgrRelease.tenant_id == tenant, ArtistmgrRelease.status != "live")).all():
            for p in _rel_view(s, r)["plan"]:
                if p["by"] and not p["done"] and p["by"] <= (t + timedelta(days=7)).isoformat():
                    rel.append(f"{r.number} {r.title}: {p['what']} ({p['by']})")
        waiting = len(s.scalars(select(ArtistmgrCard).where(ArtistmgrCard.tenant_id == tenant, ArtistmgrCard.status == "waiting")).all())
        missing = []
        for a in s.scalars(select(ArtistmgrArtist).where(ArtistmgrArtist.tenant_id == tenant, ArtistmgrArtist.active.is_(True))).all():
            need = [x["label"] for x in _regs_view(a) if x["status"] == "none" and x["key"] in ("iprs", "isamra", "isrc")]
            if need:
                missing.append(f"{a.name}: {', '.join(need)}")
        no_comm = st.commission_pct is None
    parts = []
    if today_g:
        parts.append("Aaj: " + ", ".join(f"{g['number']} {g['artist']} {g['start']} {g['city']}" for g in today_g))
    if tom_g:
        parts.append("Kal: " + ", ".join(f"{g['number']} {g['artist']} {g['city']}" for g in tom_g) + " (rider / travel pakka?)")
    if holds:
        parts.append("Hold 24 ghante mein khatam: " + ", ".join(g["number"] for g in holds))
    if expired:
        parts.append("Hold khatam ho gaye: " + ", ".join(g.number for g in expired))
    if bal:
        parts.append("Baaki payment: " + "; ".join(bal))
    if unsettled:
        parts.append("; ".join(unsettled[:6]))
    if rel:
        parts.append("Release: " + "; ".join(rel[:6]))
    if waiting:
        parts.append(f"{waiting} card aapki haan ka intezaar")
    say = ". ".join(parts) + "." if parts else "Artist kaam aaj sab theek."
    return {"today": today_g, "tomorrow": tom_g, "holds": holds, "balances": bal, "unsettled": unsettled, "releases": rel,
            "waiting": waiting, "regs_missing": missing, "no_commission": no_comm, "say": say}


def overview(tenant: str) -> dict:
    return {"settings": settings(tenant), "artists": artists(tenant), "gigs": gigs(tenant, day_from=today(tenant).isoformat()),
            "releases": releases(tenant), "cards": cards(tenant, "waiting"), "payouts": payouts(tenant)[:20], "day": day(tenant),
            "regs": R.REGS}


def _once(s, tenant: str, key: str) -> bool:
    k = f"{tenant}:{key}"[:200]
    if s.get(ArtistmgrAlert, k) is not None:
        return False
    s.add(ArtistmgrAlert(key=k, tenant_id=tenant))
    return True


def _tenants() -> list[str]:
    with session() as s:
        return sorted(set(s.scalars(select(ArtistmgrGig.tenant_id)).all()) | set(s.scalars(select(ArtistmgrSettings.tenant_id)).all()))


def tick(now_: datetime | None = None) -> dict:
    """Worker, every minute: holds expire (told once), hold ending in 12 h, gig tomorrow (rider / travel), balance due,
    show over without 'done', release steps in 3 days; morning note at her time (only when there is something)."""
    n = _aware(now_) or now()
    out = {"alerts": 0, "expired": 0, "morning": 0}
    for tenant in _tenants():
        try:
            loc = n.astimezone(_tz(tenant))
            on = loc.date()
            alerts = []
            with _LOCK, session() as s:
                for g in s.scalars(select(ArtistmgrGig).where(ArtistmgrGig.tenant_id == tenant, ArtistmgrGig.status == "hold")).all():
                    hu = _aware(g.hold_until)
                    if hu and hu <= n:
                        g.status, g.hold_until = "enquiry", None
                        _log(g, "Hold ka samay khatam")
                        out["expired"] += 1
                        alerts.append({"kind": "hold_expired", "gig": g.number, "say": f"{g.number} ka hold khatam; {g.day} ka time ab khaali."})
                    elif hu and hu <= n + timedelta(hours=12) and _once(s, tenant, f"hold12:{g.id}:{hu.isoformat()}"):
                        alerts.append({"kind": "hold_soon", "gig": g.number,
                                       "say": f"{g.number} ka hold {hu.astimezone(_tz(tenant)).strftime('%d-%m %H:%M')} par khatam: pakka karne ka card banau?"})
                for g in s.scalars(select(ArtistmgrGig).where(ArtistmgrGig.tenant_id == tenant, ArtistmgrGig.status == "confirmed")).all():
                    d = _date(g.day)
                    if d is None:
                        continue
                    m = _money(s, g)
                    if d == on + timedelta(days=1) and _once(s, tenant, f"eve:{g.id}"):
                        alerts.append({"kind": "tomorrow", "gig": g.number,
                                       "say": f"Kal {g.number} {g.city} {g.start}: rider, sound check aur travel pakka?"
                                              + ("" if g.travel_trip or g.travel_by == "promoter" else " Travel abhi nahi juda.")})
                    if m["balance_due"] and m["balance_due"] <= on.isoformat() and not m["fully_paid"] and \
                            _once(s, tenant, f"bal:{g.id}:{m['balance_due']}"):
                        alerts.append({"kind": "balance", "gig": g.number,
                                       "say": f"{g.number}: {_rs(m['due_from_promoter'])} baaki ka samay; maangne ka card banau?"})
                    if d < on and _once(s, tenant, f"over:{g.id}"):
                        alerts.append({"kind": "over", "gig": g.number, "say": f"{g.number} ({g.day}) ho gaya? 'done' bataiye, phir settlement."})
                for r in s.scalars(select(ArtistmgrRelease).where(ArtistmgrRelease.tenant_id == tenant, ArtistmgrRelease.status != "live")).all():
                    for p in _rel_view(s, r)["plan"]:
                        if p["by"] and not p["done"] and p["by"] <= (on + timedelta(days=3)).isoformat() and \
                                _once(s, tenant, f"rel:{r.id}:{p['key']}:{p['by']}"):
                            alerts.append({"kind": "release", "release": r.number, "say": f"{r.number} {r.title}: {p['what']} ({p['by']})."})
            for a in alerts:
                _publish(tenant, "artistmgr_alert", a)
                out["alerts"] += 1
            due_m = False
            with session() as s:
                st = s.get(ArtistmgrSettings, tenant)
                if st is not None and st.last_morning != on.isoformat():
                    try:
                        hh, mm = (int(z) for z in (st.morning_time or "09:00").split(":"))
                    except ValueError:
                        hh, mm = 9, 0
                    due_m = (loc.hour, loc.minute) >= (hh, mm)
                    if due_m:
                        st.last_morning = on.isoformat()
            if due_m:
                d = day(tenant)
                if d["say"] != "Artist kaam aaj sab theek.":
                    _publish(tenant, "artistmgr_day", {"say": d["say"], "today": len(d["today"]), "tomorrow": len(d["tomorrow"]),
                                                       "waiting": d["waiting"]})
                    out["morning"] += 1
        except Exception:
            log.exception("artistmgr tick failed for %s", tenant)
    return out
