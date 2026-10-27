"""Influencer Sahayak: Hoola as an influencer / talent manager's coworker (talent managers and small agencies managing creators).

  1. Creator roster: handles, follower counts AS SHE TYPED them (dated), niche, language, health / nutrition qualification,
     SEBI registration (finfluencers), virtual / AI influencer flag, PAN in her Pehchaan Locker, UPI ID for payouts.
  2. Rate card per creator x platform x format from HER numbers only (Hoola never prices a creator); rate card PDF.
  3. Brand deal pipeline D-0001 (lead -> pitched -> negotiating -> contracted -> live -> done / lost): deliverables priced from
     the rate card, barter value, usage rights, category exclusivity (a clash with another live deal's exclusivity is refused in
     code), payment terms, her commission. Category gates in code: real-money games / betting and tobacco / alcohol refused,
     a SEBI-regulated brand with a creator who is not SEBI-registered refused (SEBI, Aug 2024), bought followers never.
  4. Content calendar P-0001 from the deliverables; every caption checked for ASCI disclosure (#ad on the FIRST line, video
     overlay + spoken in 10 s, story frames, podcast start + end, virtual / AI labels, health qualification, SEBI number,
     crypto disclaimer, disease-cure words, guarantee words, claims the brand must prove).
  5. Money she records: invoice (GST 18% SAC 998361 when she is registered, export with LUT), receipts with the brand's TDS,
     overdue list, creator payout statement; performance reports from HER pasted exports only.

Waits for HER tap (only the app API passes by_tap=True; tools only make the card): pitch to a brand, contract draft to a brand,
content draft to a brand, go-live note to the creator, invoice, creator payout (fingerprint once a phone key is active, approvekey
kind "influencer"), campaign report to a brand, any other message. Hoola never posts, never sends, never takes or pays money."""
from __future__ import annotations

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
    InfluencerAlert,
    InfluencerCard,
    InfluencerCreator,
    InfluencerDeal,
    InfluencerPost,
    InfluencerRate,
    InfluencerSettings,
)

log = logging.getLogger("santosh.influencer")
_LOCK = threading.RLock()
CARD_KINDS = ("pitch", "contract", "content", "golive", "invoice", "payout", "report", "message")
MONEY_CARDS = ("payout",)
CARD_TITLE = {"pitch": "Brand ko pitch", "contract": "Contract draft brand ko", "content": "Content draft brand ko",
              "golive": "Creator ko 'post kar do'", "invoice": "Invoice brand ko", "payout": "Creator ka hissa",
              "report": "Campaign report brand ko", "message": "Message"}
OWNER_STAGES = {"contracted", "done"}


class InfluencerError(Exception):
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
        log.exception("influencer publish failed")


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


def _st(s, tenant: str) -> InfluencerSettings:
    r = s.get(InfluencerSettings, tenant)
    if r is None:
        r = InfluencerSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _wa(phone: str, text: str) -> str:
    d = R.phone(phone)
    return f"https://wa.me/91{d}?text={urlq(text)}" if d else ""


def _sms(phone: str, text: str) -> str:
    d = R.phone(phone)
    return f"sms:+91{d}?body={urlq(text)}" if d else ""


def _mail(email: str, subject: str, text: str) -> str:
    return f"mailto:{email}?subject={urlq(subject)}&body={urlq(text)}" if email and "@" in email else ""


def _draft(phone: str, text: str, email: str = "", subject: str = "", **extra) -> dict:
    return {"text": text, "wa": _wa(phone, text), "sms": _sms(phone, text), "mail": _mail(email, subject, text), **extra}


def _upi_link(upi: str, name: str, amount: float, note: str) -> str:
    if not upi or not amount or amount <= 0:
        return ""
    return f"upi://pay?pa={urlq(upi)}&pn={urlq(name)}&am={amount:.2f}&cu=INR&tn={urlq(note[:40])}"


def _her_upi(tenant: str) -> tuple[str, str]:
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


def _store(tenant: str, name: str, data: bytes, mime: str, conv: str = "", title: str = "") -> dict:
    from .. import chatfiles
    f = chatfiles.store(tenant, name, data, mime)
    _publish(tenant, "pc_file", {**f, "source": "influencer", "title": title or name}, conv)
    return f


def _log(d: InfluencerDeal, text: str, by: str = "") -> None:
    lg = _j(d.log, [])
    lg.append({"at": now().isoformat(), "what": R.clean(text, 300), "by": by})
    d.log = _dump(lg[-80:])


def _bool(v) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "haan", "ha", "on")
    return bool(v)


def _num(v) -> float | None:
    return R.money(v)


# ---------------------------------------------------------------- settings
_SET_KEYS = ("agency", "gstin", "gst_registered", "lut", "state", "address", "phone", "email", "upi_id", "commission_pct",
             "pay_days", "morning_time", "terms", "rules")


def _settings_view(st: InfluencerSettings) -> dict:
    return {"agency": st.agency, "gstin": st.gstin, "gst_registered": bool(st.gst_registered), "lut": bool(st.lut),
            "state": st.state, "address": st.address, "phone": st.phone, "email": st.email, "upi_id": st.upi_id,
            "commission_pct": st.commission_pct, "pay_days": st.pay_days, "morning_time": st.morning_time, "terms": st.terms,
            "rules": st.rules,
            "notes": ["GST: influencer promotion = advertising service, 18% (SAC 998361). Saal mein Rs 20 lakh se upar (special "
                      "states Rs 10 lakh) registration zaroori; barter bhi turnover mein ginta hai. CA se pakka karein.",
                      "TDS: brand fee par 10% (Income-tax Act 2025 s.393(1), purana 194J) kaat sakta hai; free saamaan Rs 20,000 "
                      "se upar par 10% (purana 194R) brand deta hai."]}


def settings(tenant: str) -> dict:
    with session() as s:
        return _settings_view(_st(s, tenant))


def save_settings(tenant: str, **kw: Any) -> dict:
    with _LOCK, session() as s:
        st = _st(s, tenant)
        for k in ("agency", "address", "phone", "email", "upi_id", "terms", "rules", "morning_time"):
            if k in kw and kw[k] is not None:
                v = R.clean(kw[k], 1500 if k in ("terms", "rules", "address") else 160)
                if k == "phone" and v and not R.phone(v):
                    raise InfluencerError("Phone 10 ank ka chahiye.")
                if k == "upi_id" and v and not re.fullmatch(r"[\w.\-]{2,}@[a-zA-Z]{2,}", v):
                    raise InfluencerError("UPI ID sahi nahi lagta (jaise naam@okicici).")
                if k == "morning_time" and v and not re.fullmatch(r"\d{2}:\d{2}", v):
                    raise InfluencerError("Samay HH:MM mein.")
                setattr(st, k, v)
        if "gstin" in kw and kw["gstin"] is not None:
            g = str(kw["gstin"]).strip().upper()
            if g:
                from ..india.money import gstin_ok
                if not gstin_ok(g):
                    raise InfluencerError("GSTIN ka check digit galat hai.")
                st.state = g[:2]
                st.gst_registered = True
            st.gstin = g
        for k in ("gst_registered", "lut"):
            if k in kw and kw[k] is not None:
                setattr(st, k, _bool(kw[k]))
        if "state" in kw and kw["state"]:
            st.state = re.sub(r"\D", "", str(kw["state"]))[:2]
        if "commission_pct" in kw:
            p = _num(kw["commission_pct"])
            if p is not None and not 0 <= p <= 90:
                raise InfluencerError("Commission 0-90% ke beech.")
            st.commission_pct = p
        if "pay_days" in kw and kw["pay_days"] is not None:
            n = _num(kw["pay_days"])
            if n is None or not 0 <= n <= 180:
                raise InfluencerError("Payment din 0-180.")
            st.pay_days = int(n)
        return {**_settings_view(st), "say": "Niyam save ho gaye."}


# ---------------------------------------------------------------- creators
def _creator_view(c: InfluencerCreator, full: bool = False) -> dict:
    hs = _j(c.handles, [])
    v = {"id": c.id, "number": c.number, "name": c.name, "city": c.city, "language": c.language, "niche": c.niche,
         "handles": hs, "qualification": c.qualification, "sebi_reg": c.sebi_reg, "virtual": bool(c.virtual),
         "gst_registered": bool(c.gst_registered), "pan": c.pan_masked, "upi_id": c.upi_id, "share_pct": c.share_pct,
         "no_messages": bool(c.no_messages), "status": c.status, "phone": c.phone, "email": c.email,
         "followers_total": sum(int(h.get("followers") or 0) for h in hs)}
    if full:
        v["notes"] = c.notes
        v["follower_log"] = _j(c.follower_log, [])[-30:]
        v["signals"] = _signals(c)
    return v


def _signals(c: InfluencerCreator) -> list[str]:
    out = []
    log_ = _j(c.follower_log, [])
    for h in _j(c.handles, []):
        hist = [x for x in log_ if x.get("platform") == h.get("platform")]
        out += [f"{R.PLATFORMS.get(h.get('platform'), h.get('platform'))}: {x}" for x in
                R.fake_signals(h.get("followers"), h.get("avg_likes"), h.get("avg_comments"), hist)]
    return out


def _creator(s, tenant: str, ref: str) -> InfluencerCreator:
    ref = str(ref or "").strip()
    if not ref:
        raise InfluencerError("Kaunsa creator? (naam ya C-001)")
    c = s.get(InfluencerCreator, ref)
    if c is not None and c.tenant_id == tenant:
        return c
    rows = s.scalars(select(InfluencerCreator).where(InfluencerCreator.tenant_id == tenant)).all()
    low = ref.lower().lstrip("@")
    for c in rows:
        if c.number.lower() == low or c.name.lower() == low:
            return c
    for c in rows:
        if any(str(h.get("handle", "")).lower().lstrip("@") == low for h in _j(c.handles, [])):
            return c
    hits = [c for c in rows if low in c.name.lower()]
    if len(hits) == 1:
        return hits[0]
    raise InfluencerError(f"Creator '{ref}' nahi mila.")


def creator_save(tenant: str, ref: str = "", actor: str = "owner", **kw: Any) -> dict:
    """New or update. Follower counts / averages only as she typed (dated); never fetched or guessed."""
    if R.fake_engagement(" ".join(str(v) for v in kw.values() if isinstance(v, str))):
        raise InfluencerError(R.FAKE_REFUSAL)
    pan_raw = str(kw.pop("pan", "") or "").strip()
    pan_ref_given = pan_raw if re.fullmatch(r"\{id:[a-z0-9]+\}", pan_raw) else ""
    pan_val = "" if pan_ref_given else R.clean(pan_raw, 20).upper()
    with _LOCK, session() as s:
        st = _st(s, tenant)
        if ref:
            c = _creator(s, tenant, ref)
        else:
            nm = R.clean(kw.get("name"), 120)
            if not nm:
                raise InfluencerError("Creator ka naam chahiye.")
            st.cr_seq += 1
            c = InfluencerCreator(tenant_id=tenant, number=f"C-{st.cr_seq:03d}", name=nm)
            s.add(c)
        if c.status == "forgotten":
            raise InfluencerError("Is creator ki details mita di gayi thi.")
        for k, n in (("name", 120), ("city", 80), ("language", 60), ("niche", 160), ("qualification", 200), ("notes", 2000),
                     ("email", 120)):
            if k in kw and kw[k] is not None:
                setattr(c, k, R.clean(kw[k], n))
        if "phone" in kw and kw["phone"] is not None:
            p = R.phone(kw["phone"])
            if kw["phone"] and not p:
                raise InfluencerError("Phone 10 ank ka chahiye.")
            c.phone = p
        if "sebi_reg" in kw and kw["sebi_reg"] is not None:
            v = re.sub(r"\s", "", str(kw["sebi_reg"]).upper())[:40]
            if v and not re.fullmatch(r"IN[AH]\d{9}", v):
                raise InfluencerError("SEBI number aisa hota hai: INH000012345 (RA) ya INA000012345 (IA).")
            c.sebi_reg = v
        if "upi_id" in kw and kw["upi_id"] is not None:
            v = str(kw["upi_id"]).strip()
            if v and not re.fullmatch(r"[\w.\-]{2,}@[a-zA-Z]{2,}", v):
                raise InfluencerError("UPI ID sahi nahi lagta.")
            c.upi_id = v
        for k in ("virtual", "gst_registered", "no_messages"):
            if k in kw and kw[k] is not None:
                setattr(c, k, _bool(kw[k]))
        if "share_pct" in kw:
            p = _num(kw["share_pct"])
            if p is not None and not 0 <= p <= 90:
                raise InfluencerError("Commission 0-90%.")
            c.share_pct = p
        if "status" in kw and kw["status"] in ("active", "left"):
            c.status = kw["status"]
        hs = _j(c.handles, [])
        new_h = list(kw.get("handles") or [])
        if kw.get("platform") or kw.get("handle"):
            new_h.append({"platform": kw.get("platform"), "handle": kw.get("handle"), "followers": kw.get("followers"),
                          "avg_likes": kw.get("avg_likes"), "avg_comments": kw.get("avg_comments"),
                          "avg_views": kw.get("avg_views")})
        flog = _j(c.follower_log, [])
        on = today(tenant).isoformat()
        for h in new_h:
            if not isinstance(h, dict):
                continue
            pf = R.platform_of(h.get("platform"))
            if not pf:
                raise InfluencerError("Platform batayiye (instagram / youtube ...).")
            cur = next((x for x in hs if x.get("platform") == pf), None)
            if cur is None:
                cur = {"platform": pf}
                hs.append(cur)
            if h.get("handle"):
                cur["handle"] = R.clean(h["handle"], 80)
            for k in ("followers", "avg_likes", "avg_comments", "avg_views"):
                n = R.count(h.get(k))
                if n is not None:
                    cur[k] = n
                    if k == "followers":
                        cur["on"] = on
                        flog.append({"platform": pf, "followers": n, "on": on})
        c.handles = _dump(hs)
        c.follower_log = _dump(flog[-200:])
        s.flush()
        cid, number, cname = c.id, c.number, c.name
    if pan_ref_given:
        from .. import idvault
        hit = next((r for r in idvault.list_(tenant) if r["ref"] == pan_ref_given and r["kind"] == "pan"), None)
        if hit is None:
            raise InfluencerError("Yeh PAN locker mein nahi mila.")
        with _LOCK, session() as s:
            c = s.get(InfluencerCreator, cid)
            c.pan_ref, c.pan_masked = hit["ref"], hit["masked"]
    if pan_val:
        from .. import idvault
        try:
            r = idvault.save(tenant, "pan", pan_val, f"creator {number}", f"{cname} (influencer)")
        except Exception as e:
            raise InfluencerError(f"PAN: {e}")
        with _LOCK, session() as s:
            c = s.get(InfluencerCreator, cid)
            c.pan_ref, c.pan_masked = r["ref"], r["masked"]
    with session() as s:
        c = s.get(InfluencerCreator, cid)
        v = _creator_view(c, True)
    sig = v["signals"]
    say = f"{number} {cname} save." + (f" Dhyaan: {sig[0]}" if sig else "")
    return {"creator": v, "say": say}


def creators(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(InfluencerCreator).where(InfluencerCreator.tenant_id == tenant)
        rows = s.scalars(q.order_by(InfluencerCreator.number)).all()
        return [_creator_view(c) for c in rows if not status or c.status == status]


def creator_view(tenant: str, ref: str) -> dict:
    with session() as s:
        c = _creator(s, tenant, ref)
        v = _creator_view(c, True)
        v["rates"] = [_rate_view(r) for r in s.scalars(select(InfluencerRate).where(InfluencerRate.tenant_id == tenant,
                                                                                    InfluencerRate.creator_id == c.id)).all()]
        v["deals"] = [_deal_brief(s, d) for d in s.scalars(select(InfluencerDeal).where(InfluencerDeal.tenant_id == tenant,
                                                                                        InfluencerDeal.creator_id == c.id)).all()]
        return v


# ---------------------------------------------------------------- rate card (HER numbers)
def _rate_view(r: InfluencerRate) -> dict:
    return {"id": r.id, "platform": r.platform, "platform_label": R.PLATFORMS.get(r.platform, r.platform), "fmt": r.fmt,
            "fmt_label": R.FORMATS.get(r.fmt, r.fmt), "price": r.price, "price_text": _rs(r.price), "usage_days": r.usage_days,
            "usage_price": r.usage_price, "notes": r.notes}


def rate_save(tenant: str, creator: str, platform: str, fmt: str, price=None, usage_days=None, usage_price=None,
              notes: str = "") -> dict:
    p = _num(price)
    if p is None or p <= 0:
        raise InfluencerError("Daam aapka number chahiye (Hoola khud daam nahi lagata).")
    pf, ft = R.platform_of(platform), R.format_of(fmt)
    if not pf or not ft:
        raise InfluencerError("Platform aur format dono batayiye (jaise instagram reel).")
    with _LOCK, session() as s:
        c = _creator(s, tenant, creator)
        r = s.scalars(select(InfluencerRate).where(InfluencerRate.tenant_id == tenant, InfluencerRate.creator_id == c.id,
                                                   InfluencerRate.platform == pf, InfluencerRate.fmt == ft)).first()
        if r is None:
            r = InfluencerRate(tenant_id=tenant, creator_id=c.id, platform=pf, fmt=ft)
            s.add(r)
        r.price = p
        if usage_days is not None:
            r.usage_days = int(_num(usage_days) or 0)
        if usage_price is not None:
            r.usage_price = _num(usage_price)
        if notes:
            r.notes = R.clean(notes, 300)
        s.flush()
        return {"rate": _rate_view(r), "say": f"{c.name}: {R.PLATFORMS[pf]} {R.FORMATS[ft]} {_rs(p)}."}


def rate_card(tenant: str, creator: str) -> dict:
    with session() as s:
        c = _creator(s, tenant, creator)
        rows = s.scalars(select(InfluencerRate).where(InfluencerRate.tenant_id == tenant, InfluencerRate.creator_id == c.id)).all()
        hist = _history_prices(s, tenant, c.id)
        return {"creator": _creator_view(c), "rates": [_rate_view(r) for r in rows], "history": hist,
                "note": "Daam sirf aapke. 'Pichhli deals' aapki apni poori hui deals ka median hai, sujhav nahi."}


def _history_prices(s, tenant: str, creator_id: str) -> list[dict]:
    from statistics import median
    got: dict[tuple, list[float]] = {}
    for d in s.scalars(select(InfluencerDeal).where(InfluencerDeal.tenant_id == tenant, InfluencerDeal.creator_id == creator_id,
                                                   InfluencerDeal.stage.in_(("contracted", "live", "done")))).all():
        for x in _j(d.deliverables, []):
            if x.get("price"):
                got.setdefault((x.get("platform"), x.get("fmt")), []).append(float(x["price"]))
    return [{"platform": k[0], "fmt": k[1], "median": median(v), "deals": len(v)} for k, v in got.items()]


def _rate_for(s, tenant: str, creator_id: str, pf: str, ft: str) -> InfluencerRate | None:
    return s.scalars(select(InfluencerRate).where(InfluencerRate.tenant_id == tenant, InfluencerRate.creator_id == creator_id,
                                                  InfluencerRate.platform == pf, InfluencerRate.fmt == ft)).first()


# ---------------------------------------------------------------- deals
def _deal(s, tenant: str, ref: str) -> InfluencerDeal:
    ref = str(ref or "").strip()
    if not ref:
        raise InfluencerError("Kaunsi deal? (D-0001)")
    d = s.get(InfluencerDeal, ref)
    if d is not None and d.tenant_id == tenant:
        return d
    d = s.scalars(select(InfluencerDeal).where(InfluencerDeal.tenant_id == tenant, InfluencerDeal.number == ref.upper())).first()
    if d is None:
        raise InfluencerError(f"Deal '{ref}' nahi mili.")
    return d


def _deal_brief(s, d: InfluencerDeal) -> dict:
    c = s.get(InfluencerCreator, d.creator_id)
    return {"id": d.id, "number": d.number, "brand": d.brand, "creator": c.name if c else "", "creator_number": c.number if c else "",
            "stage": d.stage, "stage_label": R.STAGE_LABEL.get(d.stage, d.stage), "fee": d.fee, "fee_text": _rs(d.fee) if d.fee else "",
            "kind": d.kind, "product": d.product, "due_on": d.due_on, "invoice_no": d.invoice_no,
            "received": round(sum(float(x.get("amount") or 0) for x in _j(d.receipts, [])), 2)}


def _clean_deliverables(s, tenant: str, creator_id: str, items: Any) -> list[dict]:
    out = []
    for x in items or []:
        if isinstance(x, str):
            x = {"fmt": x}
        if not isinstance(x, dict):
            continue
        pf, ft = R.platform_of(x.get("platform") or "instagram"), R.format_of(x.get("fmt") or x.get("format") or "")
        if not ft:
            raise InfluencerError("Har deliverable ka format chahiye (reel / story / video ...).")
        qty = int(R.count(x.get("qty")) or 1)
        price = _num(x.get("price"))
        src = "aapka"
        if price is None:
            r = _rate_for(s, tenant, creator_id, pf, ft)
            price, src = (r.price, "rate card") if r else (None, "")
        due = R.as_date(x.get("due"))
        out.append({"platform": pf, "fmt": ft, "qty": max(1, min(qty, 50)), "price": price, "price_from": src,
                    "due": due.isoformat() if due else ""})
    return out


def _cats_of(d: InfluencerDeal) -> list[str]:
    return R.categories(" ".join([d.brand, d.product, d.brief, d.excl_category]))


def _gate(s, tenant: str, d: InfluencerDeal, c: InfluencerCreator) -> list[str]:
    """Hard refusals in code (not her choice): banned categories, SEBI-regulated brand + unregistered creator, fake engagement."""
    cats = _cats_of(d)
    out = [R.BLOCK_CATEGORIES[k] for k in cats if k in R.BLOCK_CATEGORIES]
    if R.fake_engagement(" ".join([d.brief, d.product, d.barter_items])):
        out.append(R.FAKE_REFUSAL)
    if d.sebi_regulated and not c.sebi_reg:
        out.append("SEBI-registered brand (broker / AMC / adviser) kisi aise creator ke saath kaam nahi kar sakta jo SEBI-registered "
                   "nahi aur share / fund par salah ya returns ki baat karta ho (SEBI, Aug 2024 circular). Creator ka SEBI number "
                   "nahi hai: yeh deal nahi chalegi (sirf investor education, bina salah ke, brand ke apne niyam se).")
    return out


def _clash(s, tenant: str, d: InfluencerDeal) -> list[str]:
    """Another live deal of the same creator holds exclusivity for this category in these dates (or this deal's own exclusivity
    is broken by one that is already running)."""
    mine = [R.as_date(x.get("due")) for x in _j(d.deliverables, []) if x.get("due")]
    m1 = min([x for x in mine if x], default=None) or R.as_date(d.excl_from)
    m2 = max([x for x in mine if x], default=None) or R.as_date(d.excl_to)
    my_text = " ".join([d.brand, d.product, d.brief, d.excl_category]).lower()
    out = []
    for o in s.scalars(select(InfluencerDeal).where(InfluencerDeal.tenant_id == tenant, InfluencerDeal.creator_id == d.creator_id,
                                                   InfluencerDeal.id != d.id,
                                                   InfluencerDeal.stage.in_(("contracted", "live", "done")))).all():
        if o.brand.strip().lower() == d.brand.strip().lower():
            continue
        cat = o.excl_category.strip().lower()
        if cat and R.overlap(R.as_date(o.excl_from), R.as_date(o.excl_to), m1, m2) and \
                any(w in my_text for w in re.split(r"[\s,/]+", cat) if len(w) > 2):
            out.append(f"{o.number} ({o.brand}) ki exclusivity '{o.excl_category}' {o.excl_from} se {o.excl_to} tak hai: "
                       "isi category ki doosri brand ka kaam usi samay mana.")
        mycat = d.excl_category.strip().lower()
        if mycat and d.excl_from and o.stage in ("contracted", "live"):
            o_text = " ".join([o.brand, o.product, o.brief, o.excl_category]).lower()
            od = [R.as_date(x.get("due")) for x in _j(o.deliverables, []) if x.get("due")]
            if any(w in o_text for w in re.split(r"[\s,/]+", mycat) if len(w) > 2) and \
                    R.overlap(R.as_date(d.excl_from), R.as_date(d.excl_to), min([x for x in od if x], default=None),
                              max([x for x in od if x], default=None)):
                out.append(f"Is deal ki exclusivity '{d.excl_category}' {o.number} ({o.brand}) ke chalte kaam se takrati hai.")
    return out


_DEAL_KEYS = ("creator", "brand", "brand_contact", "brand_phone", "brand_email", "brand_gstin", "brand_foreign", "sebi_regulated",
              "product", "brief", "kind", "deliverables", "fee", "barter_value", "barter_items", "usage_days", "excl_category",
              "excl_from", "excl_to", "pay_days", "share_pct")


def deal_save(tenant: str, ref: str = "", actor: str = "owner", conv: str = "", force: bool = False, reason: str = "",
              **kw: Any) -> dict:
    """New deal or update. Nothing priced by Hoola: a deliverable without HER price and no rate card line stays [daam?]."""
    with _LOCK, session() as s:
        st = _st(s, tenant)
        if ref:
            d = _deal(s, tenant, ref)
            if d.invoice_no and any(k in kw for k in ("fee", "deliverables", "kind", "barter_value")):
                raise InfluencerError(f"{d.number} ka invoice ban chuka: paise / deliverables ab nahi badlenge (naya credit note CA se).")
        else:
            if not kw.get("creator") or not kw.get("brand"):
                raise InfluencerError("Creator aur brand dono chahiye.")
            d = None
        c = None
        if kw.get("creator"):
            c = _creator(s, tenant, kw["creator"])
            if c.status != "active":
                raise InfluencerError(f"{c.name} ab roster mein nahi.")
        if d is None:
            st.deal_seq += 1
            d = InfluencerDeal(tenant_id=tenant, number=f"D-{st.deal_seq:04d}", conv=conv, creator_id=c.id)
            s.add(d)
            s.flush()
        if c is not None:
            d.creator_id = c.id
        c = s.get(InfluencerCreator, d.creator_id)
        for k, n in (("brand", 160), ("brand_contact", 120), ("brand_email", 120), ("product", 200), ("brief", 4000),
                     ("barter_items", 500), ("excl_category", 80)):
            if k in kw and kw[k] is not None:
                setattr(d, k, R.clean(kw[k], n))
        if "brand_phone" in kw and kw["brand_phone"] is not None:
            p = R.phone(kw["brand_phone"])
            if kw["brand_phone"] and not p:
                raise InfluencerError("Brand ka phone 10 ank ka chahiye.")
            d.brand_phone = p
        if "brand_gstin" in kw and kw["brand_gstin"]:
            g = str(kw["brand_gstin"]).strip().upper()
            from ..india.money import gstin_ok
            if not gstin_ok(g):
                raise InfluencerError("Brand ka GSTIN check digit galat.")
            d.brand_gstin, d.brand_state = g, g[:2]
        for k in ("brand_foreign", "sebi_regulated"):
            if k in kw and kw[k] is not None:
                setattr(d, k, _bool(kw[k]))
        if "kind" in kw and kw["kind"]:
            if kw["kind"] not in R.DEAL_KINDS:
                raise InfluencerError("Deal kind: paid / barter / affiliate / employee / mixed.")
            d.kind = kw["kind"]
        if "deliverables" in kw and kw["deliverables"] is not None:
            d.deliverables = _dump(_clean_deliverables(s, tenant, d.creator_id, kw["deliverables"]))
        if "fee" in kw:
            d.fee = _num(kw["fee"])
        if "barter_value" in kw:
            d.barter_value = _num(kw["barter_value"]) or 0.0
        for k in ("usage_days", "pay_days"):
            if k in kw and kw[k] is not None:
                setattr(d, k, int(_num(kw[k]) or 0))
        if "share_pct" in kw:
            p = _num(kw["share_pct"])
            if p is not None and not 0 <= p <= 90:
                raise InfluencerError("Commission 0-90%.")
            d.share_pct = p
        for k in ("excl_from", "excl_to"):
            if k in kw and kw[k] is not None:
                dd = R.as_date(kw[k])
                d.__setattr__(k, dd.isoformat() if dd else "")
        dl = _j(d.deliverables, [])
        if d.fee is None and dl and all(x.get("price") for x in dl):
            d.fee = round(sum(float(x["price"]) * int(x.get("qty") or 1) for x in dl), 2)
        d.categories = _dump(_cats_of(d))
        bad = _gate(s, tenant, d, c)
        if bad:
            raise InfluencerError(" ".join(bad))
        cl = _clash(s, tenant, d)
        if cl and not (force and is_owner(actor) and reason.strip()):
            raise InfluencerError(" ".join(cl) + " (Sirf aap, wajah likh kar, 'phir bhi' kar sakti hain.)")
        if cl:
            _log(d, f"Exclusivity takrav phir bhi: {reason}", "Owner")
        _log(d, "Deal save", actor_name(tenant, actor))
        s.flush()
        did = d.id
        _sync_posts(s, tenant, d)
        v = _deal_view(s, d)
    notes = []
    if any(not x.get("price") for x in v["deliverables"]):
        notes.append("Kuch deliverables ka daam nahi: rate card mein daam daaliye ya deal mein likhiye.")
    if cl:
        notes.append("Exclusivity takrav aapki wajah ke saath save hua.")
    return {"deal": v, "say": f"{v['number']} {v['brand']} · {v['creator']} save." + (" " + " ".join(notes) if notes else ""),
            "id": did}


def _sync_posts(s, tenant: str, d: InfluencerDeal) -> None:
    """One post row per deliverable unit; extra planned rows (deliverables reduced) are removed; done work stays."""
    st = _st(s, tenant)
    want = []
    for x in _j(d.deliverables, []):
        for _ in range(int(x.get("qty") or 1)):
            want.append(x)
    have = s.scalars(select(InfluencerPost).where(InfluencerPost.tenant_id == tenant, InfluencerPost.deal_id == d.id)
                     .order_by(InfluencerPost.number)).all()
    pool = list(have)
    for x in want:
        p = next((p for p in pool if p.platform == x["platform"] and p.fmt == x["fmt"]), None)
        if p is not None:
            pool.remove(p)
            if p.status in ("planned", "draft") and x.get("due"):
                p.due = x["due"]
            continue
        st.post_seq += 1
        s.add(InfluencerPost(tenant_id=tenant, number=f"P-{st.post_seq:04d}", deal_id=d.id, creator_id=d.creator_id,
                             platform=x["platform"], fmt=x["fmt"], due=x.get("due") or ""))
    for p in pool:
        if p.status in ("planned",) and not p.caption:
            s.delete(p)


def _post_view(p: InfluencerPost) -> dict:
    return {"id": p.id, "number": p.number, "deal_id": p.deal_id, "platform": p.platform,
            "platform_label": R.PLATFORMS.get(p.platform, p.platform), "fmt": p.fmt, "fmt_label": R.FORMATS.get(p.fmt, p.fmt),
            "due": p.due, "status": p.status, "status_label": R.POST_STATUS.get(p.status, p.status), "caption": p.caption,
            "script": p.script, "duration_s": p.duration_s, "ai_media": bool(p.ai_media), "ticks": _j(p.ticks, {}),
            "check": _j(p.check, {}), "brand_notes": p.brand_notes, "brand_ok": bool(p.approved_hash) and
            p.approved_hash == _content_hash(p), "live_url": p.live_url, "posted_on": p.posted_on, "metrics": _j(p.metrics, {}),
            "engagement": R.engagement(_j(p.metrics, {})) if _j(p.metrics, {}) else {}}


def _deal_view(s, d: InfluencerDeal) -> dict:
    c = s.get(InfluencerCreator, d.creator_id)
    posts = s.scalars(select(InfluencerPost).where(InfluencerPost.tenant_id == d.tenant_id, InfluencerPost.deal_id == d.id)
                      .order_by(InfluencerPost.number)).all()
    rec = _j(d.receipts, [])
    return {**_deal_brief(s, d), "brand_contact": d.brand_contact, "brand_phone": d.brand_phone, "brand_email": d.brand_email,
            "brand_gstin": d.brand_gstin, "brand_foreign": bool(d.brand_foreign), "sebi_regulated": bool(d.sebi_regulated),
            "brief": d.brief, "categories": _j(d.categories, []), "kind_label": R.DEAL_KINDS.get(d.kind, d.kind),
            "deliverables": _j(d.deliverables, []), "barter_value": d.barter_value, "barter_items": d.barter_items,
            "usage_days": d.usage_days, "excl_category": d.excl_category, "excl_from": d.excl_from, "excl_to": d.excl_to,
            "pay_days": d.pay_days, "share_pct": d.share_pct, "lost_reason": d.lost_reason, "invoice": _j(d.invoice, {}),
            "receipts": rec, "tds_total": round(sum(float(x.get("tds") or 0) for x in rec), 2), "payout": _j(d.payout, {}),
            "report": _j(d.report, {}), "posts": [_post_view(p) for p in posts], "creator_view": _creator_view(c) if c else {},
            "log": _j(d.log, [])[-20:], "money": _money(s, d)}


def deals(tenant: str, stage: str = "", creator: str = "") -> list[dict]:
    with session() as s:
        q = select(InfluencerDeal).where(InfluencerDeal.tenant_id == tenant)
        if stage:
            q = q.where(InfluencerDeal.stage == stage)
        if creator:
            q = q.where(InfluencerDeal.creator_id == _creator(s, tenant, creator).id)
        return [_deal_brief(s, d) for d in s.scalars(q.order_by(InfluencerDeal.created_at.desc())).all()][:200]


def deal_view(tenant: str, ref: str) -> dict:
    with session() as s:
        return _deal_view(s, _deal(s, tenant, ref))


def stage(tenant: str, ref: str, to: str, reason: str = "", actor: str = "owner") -> dict:
    if to not in R.STAGES:
        raise InfluencerError("Stage: " + " / ".join(R.STAGES))
    if to in OWNER_STAGES and not is_owner(actor):
        raise InfluencerError("Deal pakki / poori sirf owner karti hain.")
    with _LOCK, session() as s:
        d = _deal(s, tenant, ref)
        if to == "lost" and not reason.strip():
            raise InfluencerError("Deal kyun nahi hui? Wajah likhiye (seekhne ke liye).")
        if to == "contracted":
            c = s.get(InfluencerCreator, d.creator_id)
            bad = _gate(s, tenant, d, c) + _clash(s, tenant, d)
            if bad:
                raise InfluencerError(" ".join(bad))
        d.stage = to
        if to == "lost":
            d.lost_reason = R.clean(reason, 300)
        _log(d, f"Stage: {R.STAGE_LABEL[to]}" + (f" ({reason})" if reason else ""), actor_name(tenant, actor))
        return {"deal": _deal_brief(s, d), "say": f"{d.number}: {R.STAGE_LABEL[to]}."}


# ---------------------------------------------------------------- posts + disclosure check
def _post(s, tenant: str, ref: str) -> InfluencerPost:
    ref = str(ref or "").strip()
    p = s.get(InfluencerPost, ref)
    if p is not None and p.tenant_id == tenant:
        return p
    p = s.scalars(select(InfluencerPost).where(InfluencerPost.tenant_id == tenant, InfluencerPost.number == ref.upper())).first()
    if p is None:
        raise InfluencerError(f"Post '{ref}' nahi mila (P-0001).")
    return p


def _content_hash(p: InfluencerPost) -> str:
    return R.digest({"caption": p.caption, "script": p.script, "ai": bool(p.ai_media), "dur": p.duration_s})


def _run_check(s, p: InfluencerPost) -> dict:
    d = s.get(InfluencerDeal, p.deal_id)
    c = s.get(InfluencerCreator, p.creator_id)
    text_cats = R.categories(" ".join([p.caption, p.script]))
    cats = sorted(set(_j(d.categories, []) if d else []) | set(text_cats))
    res = R.disclosure_check("\n".join(x for x in (p.caption, p.script) if x) if p.fmt in R.AUDIO_FORMATS else p.caption,
                             p.platform, p.fmt, d.kind if d else "paid", virtual=bool(c and c.virtual), ai_media=bool(p.ai_media),
                             cats=cats, health_qual=c.qualification if c else "", sebi_reg=c.sebi_reg if c else "",
                             ticks=_j(p.ticks, {}), duration_s=p.duration_s)
    if p.script and p.fmt not in R.AUDIO_FORMATS:
        sc = R.disclosure_check("#ad\n" + p.script, p.platform, "post", "paid", cats=cats,
                                health_qual=c.qualification if c else "", sebi_reg=c.sebi_reg if c else "")
        res["block"] += [f"Script: {x}" for x in sc["block"] if "label" not in x.lower()]
        res["ok"] = not res["block"]
    p.check = _dump(res)
    return res


def post_save(tenant: str, ref: str, actor: str = "owner", **kw: Any) -> dict:
    with _LOCK, session() as s:
        p = _post(s, tenant, ref)
        if p.status == "live" and any(k in kw for k in ("caption", "script")):
            raise InfluencerError("Post live ho chuka: caption ab yahan nahi badlega (platform par khud badliye, phir yahan likhiye).")
        before = _content_hash(p)
        for k, n in (("caption", 2200), ("script", 6000), ("brand_notes", 2000)):
            if k in kw and kw[k] is not None:
                setattr(p, k, R.clean(kw[k], n))
        if "duration_s" in kw:
            p.duration_s = _num(kw["duration_s"])
        if "ai_media" in kw and kw["ai_media"] is not None:
            p.ai_media = _bool(kw["ai_media"])
        if "due" in kw and kw["due"]:
            dd = R.as_date(kw["due"])
            if not dd:
                raise InfluencerError("Tareekh DD-MM-YYYY mein.")
            p.due = dd.isoformat()
        if isinstance(kw.get("ticks"), dict):
            t = _j(p.ticks, {})
            t.update({str(k): bool(v) for k, v in kw["ticks"].items()})
            p.ticks = _dump(t)
        if p.caption and p.status == "planned":
            p.status = "draft"
        if before != _content_hash(p) and p.status in ("with_brand", "approved"):
            p.status = "draft"
        if kw.get("brand_ok") is not None:
            if _bool(kw["brand_ok"]):
                if not p.caption:
                    raise InfluencerError("Pehle caption / draft chahiye.")
                p.approved_hash = _content_hash(p)
                p.status = "approved"
            else:
                p.approved_hash = ""
        if kw.get("live_url"):
            u = str(kw["live_url"]).strip()
            if not re.match(r"https://", u):
                raise InfluencerError("Live post ka https link chahiye.")
            p.live_url, p.status = u[:400], "live"
            p.posted_on = R.as_date(kw.get("posted_on")).isoformat() if R.as_date(kw.get("posted_on")) else today(tenant).isoformat()
            d = s.get(InfluencerDeal, p.deal_id)
            if d and d.stage == "contracted":
                d.stage = "live"
        if kw.get("status") in ("missed", "planned"):
            p.status = kw["status"]
        res = _run_check(s, p)
        v = _post_view(p)
    say = f"{v['number']}: " + ("disclosure theek." if res["ok"] else "rukawat: " + res["block"][0])
    if res["ok"] and res["warn"]:
        say += f" ({len(res['warn'])} baatein dekhiye)"
    if kw.get("live_url") and not res["ok"]:
        say += " Post live hai par disclosure poora nahi: creator se turant theek karwaiye (ASCI notice aa sakta hai)."
    return {"post": v, "say": say}


def check_text(tenant: str, caption: str, platform: str = "instagram", fmt: str = "reel", kind: str = "paid",
               creator: str = "", ai_media: bool = False, duration_s=None) -> dict:
    """Quick check of any caption she pastes (no deal needed)."""
    virtual, qual, sebi = False, "", ""
    if creator:
        with session() as s:
            c = _creator(s, tenant, creator)
            virtual, qual, sebi = bool(c.virtual), c.qualification, c.sebi_reg
    res = R.disclosure_check(caption, R.platform_of(platform) or "instagram", R.format_of(fmt) or "post", kind, virtual=virtual,
                             ai_media=ai_media, cats=R.categories(caption), health_qual=qual, sebi_reg=sebi,
                             duration_s=_num(duration_s))
    res["say"] = "Disclosure theek." if res["ok"] else "Rukawat: " + res["block"][0]
    return res


def posts(tenant: str, deal: str = "", day_from: str = "", status: str = "") -> list[dict]:
    with session() as s:
        q = select(InfluencerPost).where(InfluencerPost.tenant_id == tenant)
        if deal:
            q = q.where(InfluencerPost.deal_id == _deal(s, tenant, deal).id)
        rows = s.scalars(q.order_by(InfluencerPost.due, InfluencerPost.number)).all()
        out = []
        for p in rows:
            if status and p.status != status:
                continue
            if day_from and p.due and p.due < day_from:
                continue
            v = _post_view(p)
            d = s.get(InfluencerDeal, p.deal_id)
            c = s.get(InfluencerCreator, p.creator_id)
            v.update({"deal": d.number if d else "", "brand": d.brand if d else "", "creator": c.name if c else ""})
            out.append(v)
        return out


def calendar(tenant: str, month: str = "") -> dict:
    m = month or today(tenant).isoformat()[:7]
    items = [p for p in posts(tenant) if p["due"].startswith(m)]
    by_day: dict[str, list] = {}
    for p in items:
        by_day.setdefault(p["due"], []).append(p)
    crowd = [f"{k}: {len(v)} post ek hi creator ke" for k, v in by_day.items()
             if max([sum(1 for x in v if x["creator"] == c) for c in {x["creator"] for x in v}] or [0]) >= 3]
    return {"month": m, "days": by_day, "undated": [p for p in posts(tenant) if not p["due"] and p["status"] != "live"],
            "notes": crowd}


# ---------------------------------------------------------------- money
def _fy_sums(s, tenant: str, d: InfluencerDeal) -> tuple[float, float]:
    """Fees already invoiced and barter already taken from the same brand in this FY (for TDS thresholds)."""
    fy0 = R.fy_start(today(tenant))
    fees = ben = 0.0
    for o in s.scalars(select(InfluencerDeal).where(InfluencerDeal.tenant_id == tenant, InfluencerDeal.id != d.id,
                                                   InfluencerDeal.stage.in_(("contracted", "live", "done")))).all():
        if o.brand.strip().lower() != d.brand.strip().lower():
            continue
        ca = _aware(o.created_at)
        if ca and ca.date() < fy0:
            continue
        if o.invoice_no:
            fees += float(_j(o.invoice, {}).get("taxable") or 0)
        ben += float(o.barter_value or 0)
    return fees, ben


def _money(s, d: InfluencerDeal) -> dict:
    st = _st(s, d.tenant_id)
    c = s.get(InfluencerCreator, d.creator_id)
    fee = d.fee
    lines = []
    for x in _j(d.deliverables, []):
        lines.append({"what": f"{R.PLATFORMS.get(x['platform'], x['platform'])} {R.FORMATS.get(x['fmt'], x['fmt'])} x {x.get('qty', 1)}",
                      "amount": round(float(x["price"]) * int(x.get("qty") or 1), 2) if x.get("price") else None})
    taxable = fee
    gst = R.gst_of(taxable or 0.0, bool(st.gst_registered), st.state, d.brand_state, bool(d.brand_foreign), bool(st.lut)) \
        if taxable else None
    total = round(taxable + gst["total_tax"], 2) if taxable is not None and gst else None
    fees_fy, ben_fy = _fy_sums(s, d.tenant_id, d)
    tds = R.tds_note(taxable or 0.0, float(d.barter_value or 0), fees_fy, ben_fy)
    pct = d.share_pct if d.share_pct is not None else (c.share_pct if c and c.share_pct is not None else st.commission_pct)
    comm = round(taxable * pct / 100, 2) if taxable is not None and pct is not None else None
    creator_due = round(taxable - comm, 2) if comm is not None else None
    rec = _j(d.receipts, [])
    got = round(sum(float(x.get("amount") or 0) for x in rec), 2)
    tds_got = round(sum(float(x.get("tds") or 0) for x in rec), 2)
    owed = round(total - got - tds_got, 2) if total is not None else None
    return {"lines": lines, "taxable": taxable, "gst": gst, "total": total, "total_text": _rs(total) if total else "[daam?]",
            "tds": tds, "commission_pct": pct, "commission": comm, "creator_due": creator_due, "received": got,
            "tds_deducted": tds_got, "outstanding": owed, "barter_value": d.barter_value}


# ---------------------------------------------------------------- cards (HER tap only)
def _card_view(c: InfluencerCard) -> dict:
    sh = _j(c.show, {})
    return {"id": c.id, "kind": c.kind, "title": CARD_TITLE.get(c.kind, c.kind), "status": c.status, "hash": c.hash,
            "show": {k: v for k, v in sh.items() if not k.startswith("_")}, "deal_id": c.deal_id, "post_id": c.post_id,
            "money": c.kind in MONEY_CARDS, "asked_by": c.asked_by, "reason": c.reason, "result": _j(c.result, {}),
            "created_at": _aware(c.created_at).isoformat() if c.created_at else ""}


def _base(s, d: InfluencerDeal) -> dict:
    c = s.get(InfluencerCreator, d.creator_id)
    return {"deal": d.number, "brand": d.brand, "creator": c.name if c else "", "creator_number": c.number if c else ""}


def _pitch_text(s, d: InfluencerDeal, st: InfluencerSettings) -> str:
    c = s.get(InfluencerCreator, d.creator_id)
    hs = ", ".join(f"{R.PLATFORMS.get(h['platform'], h['platform'])} {h.get('handle', '')}"
                   + (f" ({h['followers']:,} followers, {h.get('on', '')})" if h.get("followers") else "")
                   for h in _j(c.handles, [])) if c else ""
    dl = "\n".join(f"- {R.PLATFORMS.get(x['platform'], x['platform'])} {R.FORMATS.get(x['fmt'], x['fmt'])} x{x.get('qty', 1)}: "
                   f"{_rs(x['price']) if x.get('price') else '[daam?]'}" for x in _j(d.deliverables, []))
    lines = [f"Namaste {d.brand_contact or d.brand} ji,", "",
             f"{c.name if c else ''} ({c.niche if c and c.niche else 'creator'}) ke saath {d.product or d.brand} ke liye prastaav:",
             hs, "", dl or "- [deliverables?]", "",
             f"Kul: {_rs(d.fee) if d.fee else '[daam?]'} + GST (agar lage)." if d.kind != "barter" else
             f"Barter: {d.barter_items or '[saamaan?]'} (mool {_rs(d.barter_value) if d.barter_value else '[?]'}).",
             (f"Usage rights: {d.usage_days} din." if d.usage_days else "Usage: sirf creator ke apne account par (organic)."),
             (f"Exclusivity: {d.excl_category} {d.excl_from} se {d.excl_to}." if d.excl_category else ""),
             "Har post par saaf '#ad' disclosure hoga (ASCI).", "", f"- {st.agency or 'Aapki team'}"]
    return "\n".join(x for x in lines if x is not None)


def _show(s, tenant: str, kind: str, d: InfluencerDeal | None, p: InfluencerPost | None, inp: dict) -> dict:
    """What the card shows, REBUILT from the state now (the hash covers it: any change after the card = stale)."""
    st = _st(s, tenant)
    if d is None:
        return {"kind": kind, **inp}
    base = _base(s, d)
    m = _money(s, d)
    if kind == "pitch":
        return {**base, "text": _pitch_text(s, d, st), "fee": d.fee, "amount_text": _rs(d.fee) if d.fee else "",
                "deliverables": _j(d.deliverables, []), "to_phone": d.brand_phone, "to_email": d.brand_email, "_in": inp}
    if kind == "contract":
        return {**base, "deliverables": _j(d.deliverables, []), "fee": d.fee, "total_text": m["total_text"], "kind": d.kind,
                "barter": d.barter_items, "barter_value": d.barter_value, "usage_days": d.usage_days,
                "excl": f"{d.excl_category} {d.excl_from}..{d.excl_to}" if d.excl_category else "", "pay_days": d.pay_days or st.pay_days,
                "terms": st.terms, "tds_lines": m["tds"]["lines"], "gst_note": (m["gst"] or {}).get("note", ""), "_in": inp}
    if kind in ("content", "golive"):
        if p is None:
            raise InfluencerError("Post chahiye.")
        chk = _j(p.check, {})
        return {**base, "post": p.number, "platform": R.PLATFORMS.get(p.platform, p.platform), "fmt": R.FORMATS.get(p.fmt, p.fmt),
                "due": p.due, "caption": p.caption, "script": p.script[:1500], "content_hash": _content_hash(p),
                "warn": chk.get("warn", []), "checklist": [x["text"] for x in chk.get("checklist", [])],
                "brand_ok": bool(p.approved_hash) and p.approved_hash == _content_hash(p), "_in": inp}
    if kind == "invoice":
        return {**base, "lines": m["lines"], "taxable": m["taxable"], "gst": m["gst"], "total": m["total"], "total_text": m["total_text"],
                "amount_text": m["total_text"], "tds_lines": m["tds"]["lines"], "expected_tds": m["tds"]["fee_tds"],
                "pay_days": d.pay_days or st.pay_days, "brand_gstin": d.brand_gstin, "_in": inp}
    if kind == "payout":
        c = s.get(InfluencerCreator, d.creator_id)
        return {**base, "fee": m["taxable"], "commission_pct": m["commission_pct"], "commission": m["commission"],
                "amount": m["creator_due"], "amount_text": _rs(m["creator_due"]), "received": m["received"],
                "tds_deducted": m["tds_deducted"], "upi": c.upi_id if c else "", "payee": c.name if c else "", "_in": inp}
    if kind == "report":
        posts_ = s.scalars(select(InfluencerPost).where(InfluencerPost.tenant_id == tenant, InfluencerPost.deal_id == d.id)).all()
        nums = R.campaign_numbers([{"metrics": _j(x.metrics, {})} for x in posts_], d.fee)
        return {**base, "numbers": nums, "live": [x.live_url for x in posts_ if x.live_url], "note": inp.get("note", ""), "_in": inp}
    if kind == "message":
        return {**base, "to": inp.get("to", "brand"), "text": inp.get("text", ""), "_in": inp}
    raise InfluencerError(f"card '{kind}' nahi pehchana.")


def _make_card(tenant: str, kind: str, deal_ref: str, post_ref: str, inp: dict, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        p = _post(s, tenant, post_ref) if post_ref else None
        d = s.get(InfluencerDeal, p.deal_id) if p else (_deal(s, tenant, deal_ref) if deal_ref else None)
        show = _show(s, tenant, kind, d, p, inp)
        h = R.digest(show)
        old = s.scalars(select(InfluencerCard).where(InfluencerCard.tenant_id == tenant, InfluencerCard.kind == kind,
                                                     InfluencerCard.deal_id == (d.id if d else ""),
                                                     InfluencerCard.post_id == (p.id if p else ""),
                                                     InfluencerCard.status == "waiting")).all()
        for o in old:
            if o.hash == h:
                return {"card": _card_view(o), "status": "needs_tap", "existing": True,
                        "say": "Yahi card pehle se aapki haan ka intezaar kar raha hai."}
            o.status = "stale"
        c = InfluencerCard(tenant_id=tenant, kind=kind, deal_id=d.id if d else "", post_id=p.id if p else "", show=_dump(show),
                           hash=h, asked_by=actor_name(tenant, actor), conv=conv or (d.conv if d else ""))
        s.add(c)
        s.flush()
        v = _card_view(c)
        cv = c.conv
    say = f"{CARD_TITLE[kind]}: {v['show'].get('deal', '')} {v['show'].get('post', '')} aapki haan ka card bheja hai.".replace("  ", " ")
    _publish(tenant, "influencer_card", {"card": v, "say": say}, cv)
    return {"card": v, "status": "needs_tap", "say": say}


def card_view(tenant: str, card_id: str) -> dict:
    with session() as s:
        c = s.get(InfluencerCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise InfluencerError("Card nahi mila.")
        return _card_view(c)


def cards(tenant: str, status: str = "waiting") -> list[dict]:
    with session() as s:
        q = select(InfluencerCard).where(InfluencerCard.tenant_id == tenant)
        if status:
            q = q.where(InfluencerCard.status == status)
        return [_card_view(c) for c in s.scalars(q.order_by(InfluencerCard.created_at.desc())).all()][:100]


def card_challenge(tenant: str, card_id: str) -> dict:
    """approvekey's message format (kind 'influencer'): her phone signs this money card (creator payout) as it is NOW."""
    from .. import approvekey as ak
    c = card_view(tenant, card_id)
    if c["status"] != "waiting" or c["kind"] not in MONEY_CARDS:
        raise InfluencerError("Yeh card ab baaki nahi hai.")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|influencer|{card_id}|{c['hash']}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="influencer", target=card_id, digest=c["hash"], message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    sh = c["show"]
    return {"challenge_id": chid, "message": msg, "show": {"title": f"{c['title']} {sh.get('deal', '')}",
                                                           "amount": sh.get("amount_text", ""), "payee": sh.get("payee", "")},
            "expires_at": exp.isoformat()}


def _verify_fingerprint(tenant: str, card_id: str, digest: str, proof: dict | None) -> None:
    from .. import approvekey as ak
    if not proof:
        raise InfluencerError("fingerprint_needed")
    with session() as s:
        ak._settle(s, tenant)
        ok = ak._check(s, tenant, "influencer", card_id, proof, digest)
    if not ok:
        raise InfluencerError("fingerprint_invalid")


def _blockers(kind: str, sh: dict, inp: dict, s, tenant: str, card: InfluencerCard) -> list[str]:
    out = []
    txt = json.dumps({k: v for k, v in sh.items() if k != "_in"}, ensure_ascii=False)
    if kind in ("pitch", "contract", "invoice", "payout") and "[daam?]" in txt:
        out.append("Kuch daam khaali hain ([daam?]): pehle bhariye.")
    if kind in ("content", "golive") and card.post_id:
        p = s.get(InfluencerPost, card.post_id)
        res = _run_check(s, p)
        out += res["block"]
        if kind == "golive" and not (p.approved_hash and p.approved_hash == _content_hash(p)):
            out.append("Brand ki haan is draft par darj nahi ('Brand ne haan kaha' tick kariye).")
    if kind == "invoice" and sh.get("total") is None:
        out.append("Fee tay nahi: invoice nahi ban sakta.")
    if kind == "payout":
        if sh.get("amount") is None:
            out.append("Commission % tay nahi (Niyam ya creator / deal mein likhiye).")
        if not sh.get("received"):
            out.append("Brand se abhi paise darj nahi: pehle 'paise mile' likhiye.")
    if kind in ("pitch", "contract", "content", "golive", "invoice", "report", "message"):
        with_d = s.get(InfluencerDeal, card.deal_id) if card.deal_id else None
        if with_d is not None:
            cr = s.get(InfluencerCreator, with_d.creator_id)
            out += _gate(s, tenant, with_d, cr)
    return out


def decide(tenant: str, card_id: str, yes: bool, card_hash: str = "", reason: str = "", proof: dict | None = None,
           by_tap: bool = False, conv: str = "") -> dict:
    """ONLY from the app's API (her tap). The card's hash must still match the state NOW; the payout card needs her fingerprint
    once a phone key is active; blockers (blank prices, disclosure rukawat, banned category) refuse a Haan."""
    if not by_tap:
        raise InfluencerError("Yeh sirf aapke tap se (app ka card).")
    with _LOCK, session() as s:
        c = s.get(InfluencerCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise InfluencerError("Card nahi mila.")
        if c.status != "waiting":
            return {"card": _card_view(c), "say": f"Yeh card pehle hi '{c.status}' hai."}
        d = s.get(InfluencerDeal, c.deal_id) if c.deal_id else None
        p = s.get(InfluencerPost, c.post_id) if c.post_id else None
        inp = _j(c.show, {}).get("_in", {})
        try:
            now_hash = R.digest(_show(s, tenant, c.kind, d, p, inp))
        except InfluencerError:
            now_hash = ""
        ch, kind = c.hash, c.kind
        bad = not card_hash or card_hash != ch or now_hash != ch
        stale = now_hash != ch
        if not bad and not yes:
            c.status, c.reason, c.decided_at = "rejected", R.clean(reason, 300), now()
            return {"card": _card_view(c), "say": f"{CARD_TITLE[kind]}: nahi."}
        bl = [] if bad else _blockers(kind, _j(c.show, {}), inp, s, tenant, c)
        if stale:
            c.status = "stale"
    if bad:
        raise InfluencerError("Card ke baad kuch badal gaya; naya card dekhiye.")
    if bl:
        raise InfluencerError("Haan nahi ho sakti: " + " ".join(bl))
    if kind in MONEY_CARDS:
        from .. import approvekey as ak
        if ak.active_on(tenant):
            _verify_fingerprint(tenant, card_id, card_hash, proof)
    fn = {"pitch": _do_pitch, "contract": _do_contract, "content": _do_content, "golive": _do_golive, "invoice": _do_invoice,
          "payout": _do_payout, "report": _do_report, "message": _do_message}[kind]
    out = fn(tenant, card_id, conv)
    with _LOCK, session() as s:
        c = s.get(InfluencerCard, card_id)
        c.status, c.decided_at = "approved", now()
        c.result = _dump({k: v for k, v in out.items() if k in ("draft", "file_id", "say", "invoice_no")})
        out["card"] = _card_view(c)
    return out


def _ctx(card_id: str) -> tuple[dict, str, str, str]:
    with session() as s:
        c = s.get(InfluencerCard, card_id)
        return _j(c.show, {}), c.deal_id, c.post_id, c.conv


def _do_pitch(tenant: str, card_id: str, conv: str) -> dict:
    sh, did, _, cv = _ctx(card_id)
    with _LOCK, session() as s:
        d = s.get(InfluencerDeal, did)
        if d.stage == "lead":
            d.stage = "pitched"
        _log(d, "Pitch aapki haan se taiyaar", "Owner")
        phone, email, number = d.brand_phone, d.brand_email, d.number
        cid = d.creator_id
    f = None
    try:
        with session() as s:
            c = s.get(InfluencerCreator, cid)
            ref = c.number
        pdf = rate_card_pdf(tenant, ref)
        f = _store(tenant, f"ratecard_{ref}.pdf", pdf, "application/pdf", conv or cv, "Rate card")
    except Exception:
        log.exception("rate card pdf failed")
    return {"draft": _draft(phone, sh["text"], email, f"Collaboration proposal {number}"), "file_id": (f or {}).get("file_id", ""),
            "say": f"{number}: pitch ka draft taiyaar. Aap khud bhejiye (WhatsApp / email)."}


def _do_contract(tenant: str, card_id: str, conv: str) -> dict:
    sh, did, _, cv = _ctx(card_id)
    pdf = contract_pdf(tenant, did, final=True)
    with _LOCK, session() as s:
        d = s.get(InfluencerDeal, did)
        d.contract_hash = R.digest(sh)
        if d.stage in ("lead", "pitched"):
            d.stage = "negotiating"
        _log(d, "Contract draft aapki haan se", "Owner")
        phone, email, number = d.brand_phone, d.brand_email, d.number
    f = _store(tenant, f"contract_{number}.pdf", pdf, "application/pdf", conv or cv, f"Contract {number}")
    text = f"Namaste, {number} ka collaboration agreement draft saath mein hai. Dekh kar bataiye; dono taraf sign ke baad kaam shuru."
    return {"draft": _draft(phone, text, email, f"Agreement draft {number}"), "file_id": f.get("file_id", ""),
            "say": f"{number}: contract PDF taiyaar (vakil se ek baar dekhwa lijiye). Sign hone par 'deal pakki' kariye."}


def _do_content(tenant: str, card_id: str, conv: str) -> dict:
    sh, did, pid, _ = _ctx(card_id)
    with _LOCK, session() as s:
        p = s.get(InfluencerPost, pid)
        d = s.get(InfluencerDeal, did)
        p.status = "with_brand"
        phone, email = d.brand_phone, d.brand_email
    text = (f"{sh['deal']} · {sh['post']} ({sh['platform']} {sh['fmt']}, {sh['due'] or 'tareekh?'}) ka draft:\n\n{sh['caption']}"
            + (f"\n\nScript:\n{sh['script']}" if sh.get("script") else "") + "\n\nApproval / badlav bataiye.")
    return {"draft": _draft(phone, text, email, f"Content for approval {sh['post']}"),
            "say": f"{sh['post']}: draft brand ko bhejne ke liye taiyaar (aap bhejiye). Unka jawab aaye to 'brand ne haan kaha' likhiye."}


def _do_golive(tenant: str, card_id: str, conv: str) -> dict:
    sh, did, pid, _ = _ctx(card_id)
    with session() as s:
        d = s.get(InfluencerDeal, did)
        c = s.get(InfluencerCreator, d.creator_id)
        phone, no = c.phone, c.no_messages
    checklist = "\n".join(f"[ ] {x}" for x in sh.get("checklist", []))
    text = (f"{sh['post']} ({sh['brand']}) approve ho gaya. {sh['due'] or ''} ko post kariye, caption bilkul yahi (pehli line "
            f"mein #ad):\n\n{sh['caption']}\n\n{checklist}\nPost karne ke baad link bhejiye.")
    return {"draft": _draft("" if no else phone, text), "say": f"{sh['post']}: creator ke liye note taiyaar (aap bhejiye)."}


def _do_invoice(tenant: str, card_id: str, conv: str) -> dict:
    sh, did, _, cv = _ctx(card_id)
    with _LOCK, session() as s:
        d = s.get(InfluencerDeal, did)
        st = _st(s, tenant)
        t = today(tenant)
        st.inv_seq += 1
        d.invoice_no = f"INF/{R.fy_of(t)}/{st.inv_seq:04d}"
        d.invoice = _dump({k: sh.get(k) for k in ("lines", "taxable", "gst", "total", "tds_lines", "expected_tds")} |
                          {"date": t.isoformat()})
        d.due_on = (t + timedelta(days=int(sh.get("pay_days") or 30))).isoformat()
        _log(d, f"Invoice {d.invoice_no} aapki haan se", "Owner")
        number, inv, phone, email, total = d.number, d.invoice_no, d.brand_phone, d.brand_email, sh.get("total")
    pdf = invoice_pdf(tenant, did)
    f = _store(tenant, f"invoice_{inv.replace('/', '-')}.pdf", pdf, "application/pdf", conv or cv, f"Invoice {inv}")
    upi, nm = _her_upi(tenant)
    link = _upi_link(upi, nm, float(total or 0), inv) if not sh.get("brand_gstin") else ""
    text = (f"Namaste, {number} ka invoice {inv} ({_rs(total)}) saath mein hai. Bhugtan {sh.get('pay_days')} din mein. "
            "TDS kaatein to Form 16A bhejiye." + (f"\nUPI: {upi}" if link else ""))
    return {"draft": _draft(phone, text, email, f"Invoice {inv}", upi=link), "file_id": f.get("file_id", ""), "invoice_no": inv,
            "say": f"Invoice {inv} bana ({_rs(total)}). Aap brand ko bhejiye; paise aane par 'paise mile' likhiye."}


def _do_payout(tenant: str, card_id: str, conv: str) -> dict:
    sh, did, _, _ = _ctx(card_id)
    with _LOCK, session() as s:
        d = s.get(InfluencerDeal, did)
        c = s.get(InfluencerCreator, d.creator_id)
        d.payout = _dump({"amount": sh.get("amount"), "commission": sh.get("commission"), "pct": sh.get("commission_pct"),
                          "approved_on": today(tenant).isoformat(), "sent": False})
        _log(d, f"Creator ka hissa {_rs(sh.get('amount'))} aapki haan (fingerprint) se", "Owner")
        upi, name, phone, number = c.upi_id, c.name, c.phone, d.number
    link = _upi_link(upi, name, float(sh.get("amount") or 0), f"{number} share")
    text = (f"{name} ji, {number} ({sh['brand']}) ka hisaab: fee {_rs(sh.get('fee'))}, commission {sh.get('commission_pct')}% = "
            f"{_rs(sh.get('commission'))}, aapka hissa {_rs(sh.get('amount'))}. Bhej rahi hoon.")
    return {"draft": _draft(phone, text, upi=link),
            "say": f"{number}: {_rs(sh.get('amount'))} {name} ko dene ka UPI link taiyaar; aap apne UPI app se bhejiye, phir 'bhej diya'."}


def _do_report(tenant: str, card_id: str, conv: str) -> dict:
    sh, did, _, cv = _ctx(card_id)
    pdf = report_pdf(tenant, did)
    with _LOCK, session() as s:
        d = s.get(InfluencerDeal, did)
        d.report = _dump({"numbers": sh.get("numbers"), "on": today(tenant).isoformat()})
        phone, email, number = d.brand_phone, d.brand_email, d.number
    f = _store(tenant, f"report_{number}.pdf", pdf, "application/pdf", conv or cv, f"Report {number}")
    n = sh.get("numbers") or {}
    text = (f"{number} campaign report: views {n.get('views', 0):,}, reach {n.get('reach', 0):,}, engagement "
            f"{n.get('er_pct') if n.get('er_pct') is not None else '?'}%. PDF saath mein (numbers creator ke platform export se).")
    return {"draft": _draft(phone, text, email, f"Campaign report {number}"), "file_id": f.get("file_id", ""),
            "say": f"{number}: report taiyaar (aap bhejiye)."}


def _do_message(tenant: str, card_id: str, conv: str) -> dict:
    sh, did, _, _ = _ctx(card_id)
    with session() as s:
        d = s.get(InfluencerDeal, did)
        c = s.get(InfluencerCreator, d.creator_id)
        if sh.get("to") == "creator":
            phone, email = ("" if c.no_messages else c.phone), c.email
        else:
            phone, email = d.brand_phone, d.brand_email
    return {"draft": _draft(phone, sh.get("text", ""), email, sh.get("deal", "")), "say": "Message ka draft taiyaar (aap bhejiye)."}


# ---- card requests (never decide)
def pitch_request(tenant: str, deal: str, actor: str = "owner", conv: str = "") -> dict:
    return _make_card(tenant, "pitch", deal, "", {}, actor, conv)


def contract_request(tenant: str, deal: str, actor: str = "owner", conv: str = "") -> dict:
    return _make_card(tenant, "contract", deal, "", {}, actor, conv)


def content_request(tenant: str, post: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        p = _post(s, tenant, post)
        if not p.caption:
            raise InfluencerError("Pehle caption / draft likhiye.")
    return _make_card(tenant, "content", "", post, {}, actor, conv)


def golive_request(tenant: str, post: str, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        p = _post(s, tenant, post)
        res = _run_check(s, p)
        if not res["ok"]:
            raise InfluencerError("Disclosure mein rukawat: " + " ".join(res["block"]))
    return _make_card(tenant, "golive", "", post, {}, actor, conv)


def invoice_request(tenant: str, deal: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        d = _deal(s, tenant, deal)
        if d.invoice_no:
            raise InfluencerError(f"{d.number} ka invoice {d.invoice_no} pehle hi ban chuka.")
        if d.stage not in ("contracted", "live", "done"):
            raise InfluencerError("Invoice deal pakki hone ke baad.")
    return _make_card(tenant, "invoice", deal, "", {}, actor, conv)


def payout_request(tenant: str, deal: str, actor: str = "owner", conv: str = "") -> dict:
    return _make_card(tenant, "payout", deal, "", {}, actor, conv)


def report_request(tenant: str, deal: str, note: str = "", actor: str = "owner", conv: str = "") -> dict:
    return _make_card(tenant, "report", deal, "", {"note": R.clean(note, 500)}, actor, conv)


def message_request(tenant: str, deal: str, text: str, to: str = "brand", actor: str = "owner", conv: str = "") -> dict:
    t = R.clean(text, 1500)
    if not t:
        raise InfluencerError("Message khaali hai.")
    if R.fake_engagement(t):
        raise InfluencerError(R.FAKE_REFUSAL)
    return _make_card(tenant, "message", deal, "", {"text": t, "to": "creator" if to == "creator" else "brand"}, actor, conv)


# ---------------------------------------------------------------- money she records (owner only)
def received(tenant: str, deal: str, amount, tds=None, ref: str = "", on: str = "", actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise InfluencerError("Paise ka hisaab sirf owner.")
    a = _num(amount)
    if a is None or a <= 0:
        raise InfluencerError("Kitne paise aaye?")
    t = _num(tds) or 0.0
    with _LOCK, session() as s:
        d = _deal(s, tenant, deal)
        rec = _j(d.receipts, [])
        dd = R.as_date(on) or today(tenant)
        rec.append({"amount": a, "tds": t, "ref": R.clean(ref, 60)[-4:] if ref else "", "on": dd.isoformat()})
        d.receipts = _dump(rec)
        _log(d, f"Paise mile {_rs(a)}" + (f" + TDS {_rs(t)}" if t else ""), "Owner")
        m = _money(s, d)
        number = d.number
    say = f"{number}: {_rs(a)} darj." + (f" TDS {_rs(t)}: Form 16A / 26AS mein milaiye." if t else "")
    if m["outstanding"] is not None:
        say += f" Baaki {_rs(max(0, m['outstanding']))}."
    return {"money": m, "say": say}


def payout_sent(tenant: str, deal: str, ref: str = "", actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise InfluencerError("Sirf owner.")
    with _LOCK, session() as s:
        d = _deal(s, tenant, deal)
        po = _j(d.payout, {})
        if not po.get("approved_on"):
            raise InfluencerError("Pehle creator ke hisse ka card (aapki fingerprint haan) chahiye.")
        po.update({"sent": True, "ref": R.clean(ref, 60)[-4:], "sent_on": today(tenant).isoformat()})
        d.payout = _dump(po)
        _log(d, "Creator ko hissa bhej diya", "Owner")
        return {"payout": po, "say": f"{d.number}: creator ka hissa bheja darj."}


# ---------------------------------------------------------------- performance (her pasted exports)
def metrics(tenant: str, post: str, actor: str = "owner", **nums: Any) -> dict:
    with _LOCK, session() as s:
        p = _post(s, tenant, post)
        m = _j(p.metrics, {})
        for k in ("views", "reach", "likes", "comments", "shares", "saves", "clicks", "watch_min", "followers_gained"):
            if k in nums and nums[k] is not None:
                n = R.count(nums[k])
                if n is None:
                    raise InfluencerError(f"{k}: number samajh nahi aaya.")
                m[k] = n
        m["source"] = "aapke diye number"
        m["on"] = today(tenant).isoformat()
        p.metrics = _dump(m)
        v = _post_view(p)
    e = v["engagement"]
    return {"post": v, "say": f"{v['number']}: engagement {e.get('er_pct') if e.get('er_pct') is not None else '?'}% ({e.get('base')})."}


def import_metrics(tenant: str, deal: str, raw: bytes | str, actor: str = "owner") -> dict:
    rows = R.parse_metrics(raw)
    if not rows:
        raise InfluencerError("Sheet mein views / reach / likes ke column nahi mile (Instagram / YouTube Studio ka export daaliye).")
    matched, unmatched = [], []
    with _LOCK, session() as s:
        d = _deal(s, tenant, deal)
        ps = s.scalars(select(InfluencerPost).where(InfluencerPost.tenant_id == tenant, InfluencerPost.deal_id == d.id)).all()
        for r in rows:
            key = (r.get("url") or r.get("post_id") or "").strip()
            hit = next((p for p in ps if p.live_url and key and (key in p.live_url or p.live_url.rstrip("/") in key)), None)
            if hit is None:
                unmatched.append(key or "(bina link)")
                continue
            m = {k: r[k] for k in ("views", "reach", "likes", "comments", "shares", "saves", "clicks", "watch_min",
                                   "followers_gained") if r.get(k) is not None}
            m.update({"source": "aapka export", "on": today(tenant).isoformat()})
            hit.metrics = _dump(m)
            matched.append(hit.number)
    return {"matched": matched, "unmatched": unmatched[:20],
            "say": f"{len(matched)} post ke number jude." + (f" {len(unmatched)} line kisi live post se nahi mili." if unmatched else "")}


def report(tenant: str, deal: str) -> dict:
    with session() as s:
        d = _deal(s, tenant, deal)
        ps = s.scalars(select(InfluencerPost).where(InfluencerPost.tenant_id == tenant, InfluencerPost.deal_id == d.id)).all()
        nums = R.campaign_numbers([{"metrics": _j(p.metrics, {})} for p in ps], d.fee)
        return {"deal": d.number, "brand": d.brand, "numbers": nums,
                "posts": [{**_post_view(p)} for p in ps],
                "note": "Sab number aapke / creator ke platform export se; Hoola khud kuch nahi nikalta."}


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


def _head(st: InfluencerSettings, title: str) -> list[tuple]:
    who = " · ".join(x for x in (st.agency, f"GSTIN {st.gstin}" if st.gstin else "") if x)
    contact = " · ".join(x for x in (st.address, st.phone, st.email) if x)
    out = [("h1", title)]
    if who:
        out.append(("p", who))
    if contact:
        out.append(("p", contact))
    return out


def rate_card_pdf(tenant: str, creator: str) -> bytes:
    rc = rate_card(tenant, creator)
    with session() as s:
        st = _st(s, tenant)
        blocks = _head(st, f"Rate card: {rc['creator']['name']}")
    c = rc["creator"]
    blocks.append(("p", " · ".join(x for x in (c["niche"], c["city"], c["language"]) if x)))
    blocks.append(("table", [["Platform", "Handle", "Followers (date)"]] +
                   [[R.PLATFORMS.get(h["platform"], h["platform"]), h.get("handle", ""),
                     f"{h['followers']:,} ({h.get('on', '')})" if h.get("followers") else "-"] for h in c["handles"]]))
    blocks.append(("table", [["Platform", "Format", "Daam (GST alag)", "Usage"]] +
                   [[r["platform_label"], r["fmt_label"], _pdf_rs(r["price"]),
                     f"{r['usage_days']} din: {_pdf_rs(r['usage_price'])}" if r["usage_days"] else "organic"] for r in rc["rates"]]))
    blocks.append(("p", "Har paid post par saaf '#ad' disclosure (ASCI). Follower numbers upar likhi tareekh ke."))
    return _pdf("Rate card", blocks)


def contract_pdf(tenant: str, deal: str, final: bool = False) -> bytes:
    with session() as s:
        d = _deal(s, tenant, deal)
        st = _st(s, tenant)
        c = s.get(InfluencerCreator, d.creator_id)
        m = _money(s, d)
        blocks = _head(st, f"Influencer collaboration agreement {d.number}")
        blocks.append(("p", f"Brand: {d.brand}{(' · GSTIN ' + d.brand_gstin) if d.brand_gstin else ''} · Creator: {c.name if c else ''} "
                            f"(managed by {st.agency or '[agency?]'}) · Product: {d.product or '[?]'}"))
        blocks.append(("h", "1. Deliverables"))
        blocks.append(("table", [["Platform", "Format", "Qty", "Due", "Daam"]] +
                       [[R.PLATFORMS.get(x["platform"], x["platform"]), R.FORMATS.get(x["fmt"], x["fmt"]), str(x.get("qty", 1)),
                         x.get("due") or "[ ? ]", _pdf_rs(x.get("price"))] for x in _j(d.deliverables, [])]))
        blocks.append(("h", "2. Fee and payment"))
        if d.kind == "barter":
            blocks.append(("p", f"Barter: {d.barter_items or '[ ? ]'} (value {_pdf_rs(d.barter_value or None)}). Barter value is income "
                                "of the creator; if the brand's benefits to the creator exceed Rs 20,000 in a financial year the brand "
                                "deducts / pays 10% TDS before giving them (Income-tax Act 2025 s.393(1), old 194R)."))
        else:
            blocks.append(("p", f"Fee {_pdf_rs(d.fee)} plus GST if applicable. Payment within {d.pay_days or st.pay_days} days of "
                                "invoice. " + " ".join(m["tds"]["lines"])))
        blocks.append(("h", "3. Disclosure (ASCI / CCPA)"))
        blocks.append(("p", "Every post will carry a clear '#ad' / 'Sponsored' label on the FIRST line of the caption, an on-screen "
                            "label and a spoken disclosure in the first seconds of videos, a label on every story frame, and the "
                            "platform's paid-partnership tool. The brand will not ask for the label to be removed or hidden. "
                            "AI-generated or virtual content will be labelled as such."))
        blocks.append(("h", "4. Claims and approvals"))
        blocks.append(("p", "The brand gives proof for every product claim it asks the creator to make and is responsible for it. "
                            "Up to [ ? ] revision rounds on drafts; approval in writing before posting. The creator speaks from "
                            "genuine use; no claim of cure for diseases, no guaranteed returns."))
        blocks.append(("h", "5. Content rights"))
        blocks.append(("p", (f"The brand may reuse the content on its own channels / ads for {d.usage_days} days from posting. "
                             if d.usage_days else "Organic only: the brand may share / repost with credit, no paid ads use. ")
                            + "Copyright stays with the creator unless assigned in writing (Copyright Act 1957 s.19). Music / stock "
                              "used must be licensed for commercial use."))
        if d.excl_category:
            blocks.append(("h", "6. Exclusivity"))
            blocks.append(("p", f"No paid work for a competing brand in '{d.excl_category}' from {d.excl_from or '[ ? ]'} to "
                                f"{d.excl_to or '[ ? ]'}."))
        blocks.append(("h", "7. Cancellation, data, law"))
        blocks.append(("p", (st.terms or "Cancellation after the creator has started work: [ ? ]% of the fee is payable. ")
                            + " Both sides keep the other's personal data only for this work (DPDP Act 2023). Indian law."))
        blocks.append(("p", "Signatures: Brand ______________   Creator / agency ______________   Date ________"))
        blocks.append(("p", "Draft by Hoola from your facts: please get it checked by your lawyer before signing."))
    return _pdf(f"Agreement {deal}", blocks, "" if final else "DRAFT")


def invoice_pdf(tenant: str, deal: str) -> bytes:
    with session() as s:
        d = _deal(s, tenant, deal)
        st = _st(s, tenant)
        inv = _j(d.invoice, {})
        if not d.invoice_no:
            raise InfluencerError("Invoice abhi bana nahi.")
        blocks = _head(st, ("Tax invoice " if st.gst_registered else "Invoice ") + d.invoice_no)
        blocks.append(("p", f"Date {inv.get('date', '')} · Bill to: {d.brand}{(' · GSTIN ' + d.brand_gstin) if d.brand_gstin else ''}"
                            f" · Deal {d.number} · Due {d.due_on}"))
        rows = [["Service", "Amount"]] + [[x["what"], _pdf_rs(x.get("amount"))] for x in inv.get("lines") or []]
        g = inv.get("gst") or {}
        rows.append([f"Taxable value (SAC {R.GST_SAC})", _pdf_rs(inv.get("taxable"))])
        for k in ("cgst", "sgst", "igst"):
            if g.get(k):
                rows.append([k.upper(), _pdf_rs(g[k])])
        rows.append(["Total", _pdf_rs(inv.get("total"))])
        blocks.append(("table", rows))
        if g.get("note"):
            blocks.append(("p", g["note"]))
        try:
            from ..india.money import rupees_words
            blocks.append(("p", "In words: " + rupees_words(float(inv.get("total") or 0), "en")))
        except Exception:
            pass
        for x in inv.get("tds_lines") or []:
            blocks.append(("p", x))
        if st.upi_id:
            blocks.append(("p", f"UPI: {st.upi_id}"))
    return _pdf(d.invoice_no, blocks)


def report_pdf(tenant: str, deal: str) -> bytes:
    rp = report(tenant, deal)
    with session() as s:
        st = _st(s, tenant)
        blocks = _head(st, f"Campaign report {rp['deal']} · {rp['brand']}")
    n = rp["numbers"]
    blocks.append(("table", [["Views", "Reach", "Likes", "Comments", "Shares", "Saves", "Clicks", "Engagement"],
                             [f"{n['views']:,}", f"{n['reach']:,}", f"{n['likes']:,}", f"{n['comments']:,}", f"{n['shares']:,}",
                              f"{n['saves']:,}", f"{n['clicks']:,}", f"{n['er_pct']}%" if n.get("er_pct") is not None else "-"]]))
    if n.get("cpm") is not None or n.get("cpe") is not None:
        blocks.append(("p", f"Cost per 1,000 views {_pdf_rs(n.get('cpm'))} · cost per engagement {_pdf_rs(n.get('cpe'))}"))
    blocks.append(("table", [["Post", "Link", "Views", "Engagement"]] +
                   [[p["number"], p["live_url"] or "-", f"{int(p['metrics'].get('views') or 0):,}",
                     f"{p['engagement'].get('er_pct')}%" if p["engagement"].get("er_pct") is not None else "-"] for p in rp["posts"]]))
    blocks.append(("p", "Numbers are from the creator's own platform analytics export (" + str(n["posts_with_numbers"]) + " of "
                        + str(n["posts"]) + " posts)."))
    return _pdf(f"Report {deal}", blocks)


# ---------------------------------------------------------------- DPDP
def forget(tenant: str, creator: str = "", deal: str = "", actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise InfluencerError("Sirf owner.")
    with _LOCK, session() as s:
        if creator:
            c = _creator(s, tenant, creator)
            open_ = s.scalars(select(InfluencerDeal).where(InfluencerDeal.tenant_id == tenant, InfluencerDeal.creator_id == c.id,
                                                          InfluencerDeal.stage.in_(("negotiating", "contracted", "live")))).all()
            if open_:
                raise InfluencerError("Is creator ki deals abhi chal rahi hain: pehle poori / band kariye.")
            ref = c.pan_ref
            c.name, c.phone, c.email, c.city, c.notes, c.upi_id = f"Purana creator {c.number}", "", "", "", "", ""
            c.handles, c.follower_log, c.qualification, c.pan_ref, c.pan_masked = "[]", "[]", "", "", ""
            c.status = "forgotten"
            out = c.number
        elif deal:
            d = _deal(s, tenant, deal)
            if d.stage not in ("done", "lost"):
                raise InfluencerError("Deal poori ya band hone ke baad hi.")
            d.brand_contact, d.brand_phone, d.brand_email = "", "", ""
            ref, out = "", d.number
        else:
            raise InfluencerError("Kise bhoolna hai? creator ya deal.")
    if ref:
        try:
            from .. import idvault
            for r in idvault.list_(tenant):
                if r["ref"] == ref:
                    idvault.delete(tenant, r["id"])
        except Exception:
            log.exception("idvault delete failed")
    return {"say": f"{out}: personal details mita di (DPDP); hisaab ke number rahe."}


# ---------------------------------------------------------------- day / overview / worker
def day(tenant: str) -> dict:
    t = today(tenant)
    tm = t + timedelta(days=1)
    with session() as s:
        ps = s.scalars(select(InfluencerPost).where(InfluencerPost.tenant_id == tenant, InfluencerPost.status != "live")).all()
        ds = s.scalars(select(InfluencerDeal).where(InfluencerDeal.tenant_id == tenant)).all()
        dmap = {d.id: d for d in ds}
        due_today = [p.number for p in ps if p.due == t.isoformat()]
        due_tm = [p.number for p in ps if p.due == tm.isoformat()]
        late = [p.number for p in ps if p.due and p.due < t.isoformat() and p.status != "missed"]
        blocked = [p.number for p in ps if p.caption and not _j(p.check, {}).get("ok", True)]
        unpaid = []
        for d in ds:
            if d.invoice_no and d.due_on and d.due_on < t.isoformat():
                m = _money(s, d)
                if (m["outstanding"] or 0) > 1:
                    unpaid.append(f"{d.number} {d.brand} {_rs(m['outstanding'])} ({d.due_on} se)")
        excl = [f"{d.number} {d.brand}: {d.excl_category} {d.excl_to} ko khatam" for d in ds
                if d.excl_to and t.isoformat() <= d.excl_to <= (t + timedelta(days=7)).isoformat()]
        waiting = len(s.scalars(select(InfluencerCard).where(InfluencerCard.tenant_id == tenant,
                                                             InfluencerCard.status == "waiting")).all())
        _ = dmap
    parts = []
    if due_today:
        parts.append(f"Aaj post: {', '.join(due_today)}")
    if due_tm:
        parts.append(f"Kal: {', '.join(due_tm)}")
    if late:
        parts.append(f"Der ho gayi: {', '.join(late)}")
    if blocked:
        parts.append(f"Disclosure rukawat: {', '.join(blocked)}")
    if unpaid:
        parts.append("Paise baaki: " + "; ".join(unpaid[:5]))
    if excl:
        parts.append("Exclusivity: " + "; ".join(excl))
    if waiting:
        parts.append(f"{waiting} card aapki haan ka intezaar")
    return {"today": due_today, "tomorrow": due_tm, "late": late, "blocked": blocked, "unpaid": unpaid, "exclusivity": excl,
            "waiting": waiting, "say": ". ".join(parts) + "." if parts else "Influencer kaam: aaj sab theek."}


def overview(tenant: str) -> dict:
    return {"settings": settings(tenant), "day": day(tenant), "creators": creators(tenant), "deals": deals(tenant),
            "cards": cards(tenant), "posts": posts(tenant, day_from=(today(tenant) - timedelta(days=7)).isoformat())}


def _once(s, tenant: str, key: str) -> bool:
    k = f"{tenant}:{key}"[:200]
    if s.get(InfluencerAlert, k) is not None:
        return False
    s.add(InfluencerAlert(key=k, tenant_id=tenant))
    return True


def _tenants() -> list[str]:
    with session() as s:
        return sorted(set(s.scalars(select(InfluencerDeal.tenant_id)).all()) | set(s.scalars(select(InfluencerSettings.tenant_id)).all()))


def tick(when: datetime | None = None) -> dict:
    """Worker, every few minutes: post due tomorrow, post past its date and not live, live post with disclosure problems,
    content with the brand 3+ days, invoice overdue, exclusivity ending in 7 days (each once); morning note at her time."""
    n = _aware(when) or now()
    out = {"alerts": 0, "morning": 0}
    for tenant in _tenants():
        try:
            loc = n.astimezone(_tz(tenant))
            on = loc.date()
            alerts = []
            with _LOCK, session() as s:
                for p in s.scalars(select(InfluencerPost).where(InfluencerPost.tenant_id == tenant)).all():
                    d = s.get(InfluencerDeal, p.deal_id)
                    if d is None or d.stage in ("lost",):
                        continue
                    if p.status != "live" and p.due == (on + timedelta(days=1)).isoformat() and _once(s, tenant, f"tm:{p.id}:{p.due}"):
                        alerts.append({"kind": "due_tomorrow", "deal": d.number, "post": p.number,
                                       "say": f"Kal {p.number} ({d.brand}) post hona hai" +
                                              ("" if p.status == "approved" else f": abhi '{R.POST_STATUS.get(p.status, p.status)}'") + "."})
                    if p.status not in ("live", "missed") and p.due and p.due < on.isoformat() and _once(s, tenant, f"late:{p.id}:{p.due}"):
                        alerts.append({"kind": "late", "deal": d.number, "post": p.number,
                                       "say": f"{p.number} ({d.brand}) {p.due} ko hona tha, abhi live nahi. Creator / brand se baat?"})
                    if p.status == "live" and p.caption and not _j(p.check, {}).get("ok", True) and _once(s, tenant, f"livebad:{p.id}"):
                        alerts.append({"kind": "live_disclosure", "deal": d.number, "post": p.number,
                                       "say": f"{p.number} live hai par disclosure poora nahi: creator se turant theek karwaiye."})
                    if p.status == "with_brand" and _once(s, tenant, f"brand3:{p.id}:{on.isoformat()}") and \
                            p.due and (R.as_date(p.due) or on) <= on + timedelta(days=2):
                        alerts.append({"kind": "brand_waiting", "deal": d.number, "post": p.number,
                                       "say": f"{p.number} brand ki approval ka intezaar, aur tareekh {p.due} paas hai. Yaad dilane ka message card banau?"})
                for d in s.scalars(select(InfluencerDeal).where(InfluencerDeal.tenant_id == tenant)).all():
                    if d.invoice_no and d.due_on and d.due_on < on.isoformat():
                        m = _money(s, d)
                        if (m["outstanding"] or 0) > 1 and _once(s, tenant, f"due:{d.id}:{d.due_on}"):
                            alerts.append({"kind": "overdue", "deal": d.number,
                                           "say": f"{d.number} ({d.brand}) ka invoice {d.invoice_no} {d.due_on} se baaki: {_rs(m['outstanding'])}. "
                                                  "Yaad dilane ka card banau?"})
                    if d.excl_to and on.isoformat() <= d.excl_to <= (on + timedelta(days=7)).isoformat() and \
                            _once(s, tenant, f"excl:{d.id}:{d.excl_to}"):
                        alerts.append({"kind": "exclusivity", "deal": d.number,
                                       "say": f"{d.number} ki exclusivity '{d.excl_category}' {d.excl_to} ko khatam: nayi brands se baat ho sakti hai."})
            for a in alerts:
                _publish(tenant, "influencer_alert", a)
                out["alerts"] += 1
            with session() as s:
                r = s.get(InfluencerSettings, tenant)
                due_m = False
                if r is not None and r.last_morning != on.isoformat():
                    try:
                        hh, mm = (int(z) for z in (r.morning_time or "09:30").split(":"))
                    except ValueError:
                        hh, mm = 9, 30
                    due_m = (loc.hour, loc.minute) >= (hh, mm)
                    if due_m:
                        r.last_morning = on.isoformat()
            if due_m:
                dd = day(tenant)
                if dd["say"] != "Influencer kaam: aaj sab theek.":
                    _publish(tenant, "influencer_day", {"say": dd["say"], "waiting": dd["waiting"]})
                    out["morning"] += 1
        except Exception:
            log.exception("influencer tick failed for %s", tenant)
    return out
