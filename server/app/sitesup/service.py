"""Site Sahayak: Hoola as a construction site supervisor, end to end.

  1. Gets the job: "aaj slab ka 18 cum dala", "Ramesh thekedar ke 12 mazdoor, 2 mistri 10 ghante", "cement 200 bag aaya challan 554",
     "50 bag aur chahiye parso tak", "toolbox talk helmet par 23 log", "scaffold checklist", "beldar gir gaya", "cube 7 din 18.2 17.9 18.6",
     "2nd floor flat 203 mein crack - photo", "aaj ki DPR client ko".
  2. Does the work: activity plan + daily progress vs plan (look-ahead, delays with reasons), labour attendance per contractor / trade
     with normal + overtime hours (OSH Code rounding) and the register numbers, material received / used / balance with challans,
     indents, toolbox talks, safety checklists, near-miss / accident register with the Form XI clock, pour cards with cube sets at
     7 / 28 (/ 56) days and curing dates, snags with photos (EXIF stripped), the daily progress report (DPR).
  3. Checked against the rules and earlier work: planned % vs done %, material a coming activity needs vs balance, 8 h / 48 h,
     IS 456 sampling frequency and acceptance (her QA plan wins), curing days by cement, critical checklist failures, report deadlines.
  4. Ready as a card / file / draft: DPR PDF + WhatsApp text, indent card, stop-work card, Form XI notice text, wage-register Excel.
  5. Waits for HER tap (in code, only the app API can decide): any material indent / purchase (fingerprint once a phone key is set
     up and the amount is known), any report or message going to the client, any stop-work order and lifting it.
  6. Delivers and learns: the DPR goes out only after her tap (her WhatsApp via wa.me, or the business WhatsApp inside Meta's window),
     progress / delays feed the Theka hindrance diary (EOT), material mirrors into the Theka project stock.

When a site sits ON a Theka project (v0.117), BOQ / measurement book / RA bills / EOT stay in theka: this module links to them.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import secrets
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from sqlalchemy import select

from ..db import new_id, now, session
from . import rules as R
from .models import (SsActivity, SsCube, SsIndent, SsLabour, SsMaterial, SsPhoto, SsPour, SsProgress, SsReport, SsSafety, SsSettings,
                     SsSite, SsSnag, SsStop)

log = logging.getLogger("santosh.sitesup")
_LOCK = threading.RLock()


class SiteError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)


def _num(v) -> float:
    if v in (None, ""):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("₹", "")
    m = re.search(r"-?\d+(\.\d+)?", s)
    n = float(m.group(0)) if m else 0.0
    low = s.lower()
    if "crore" in low:
        n *= 1e7
    elif "lakh" in low or "lac" in low:
        n *= 1e5
    return n


def _rs(v) -> str:
    v = round(float(v or 0))
    s = str(abs(v))
    if len(s) > 3:
        s = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", s[:-3]) + "," + s[-3:]
    return ("-" if v < 0 else "") + "₹" + s


def _g(v) -> str:
    return f"{float(v):g}"


_SECRET = re.compile(r"\b\d{12,19}\b|\b[A-Z]{5}\d{4}[A-Z]\b")


def _clean(v, n: int = 300) -> str:
    """Her / staff words: long numbers (Aadhaar / card / account) and PANs never kept in the registers."""
    t = re.sub(r"\s+", " ", str(v or "")).strip()
    t = _SECRET.sub("[number hataya]", t)
    return t[:n]


def _phone(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    return d if len(d) == 10 and d[0] in "6789" else ""


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return datetime.now(_tz(tenant)).date()


def _local_now(tenant: str) -> datetime:
    return datetime.now(_tz(tenant))


def _date(v, default: date | None = None) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if v in (None, ""):
        return default
    s = str(v).strip().lower()
    if s in ("aaj", "today"):
        return default
    from ..analyst.service import _date as d
    return d(str(v).strip()[:11]) or default


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def actor_name(tenant: str, actor: str) -> str:
    if actor in ("", "owner") or str(actor).startswith("approved:"):
        return "Owner"
    try:
        from ..employee.service import actor_label
        return actor_label(tenant, actor)
    except Exception:
        return str(actor)[:40]


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("sitesup publish failed")


def _st(s, tenant: str) -> SsSettings:
    r = s.get(SsSettings, tenant)
    if r is None:
        r = SsSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _next(s, tenant: str, kind: str, prefix: str, width: int = 4) -> str:
    st = _st(s, tenant)
    seq = _j(st.seq, {})
    seq[kind] = int(seq.get(kind, 0)) + 1
    st.seq = _dump(seq)
    return f"{prefix}-{seq[kind]:0{width}d}"


def _once(s, tenant: str, key: str) -> bool:
    st = _st(s, tenant)
    told = _j(st.told, [])
    if key in told:
        return False
    told.append(key)
    st.told = _dump(told[-400:])
    return True


def _sha(*parts) -> str:
    return hashlib.sha256(_dump(list(parts)).encode()).hexdigest()


# ---------------------------------------------------------------- settings
_SET_KEYS = ("firm", "supervisor", "morning_time", "dpr_time", "day_hours", "week_hours", "lookahead_days", "behind_pct", "rates",
             "cube_limits", "rules")


def settings(tenant: str) -> dict:
    with session() as s:
        r = _st(s, tenant)
        return {"firm": r.firm, "supervisor": r.supervisor, "morning_time": r.morning_time, "dpr_time": r.dpr_time, "day_hours": r.day_hours,
                "week_hours": r.week_hours, "lookahead_days": r.lookahead_days, "behind_pct": r.behind_pct, "rates": _j(r.rates, {}),
                "cube_limits": _j(r.cube_limits, {}), "rules": _j(r.rules, [])}


def _hhmm(v: str) -> str:
    m = re.fullmatch(r"(\d{1,2})[:.](\d{2})", str(v).strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise SiteError(f"Samay HH:MM mein: {v}")
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def save_settings(tenant: str, **kw: Any) -> dict:
    with session() as s:
        r = _st(s, tenant)
        for k in ("firm", "supervisor"):
            if kw.get(k) is not None:
                setattr(r, k, _clean(kw[k], 160))
        for k in ("morning_time", "dpr_time"):
            if kw.get(k):
                setattr(r, k, _hhmm(kw[k]))
        if kw.get("day_hours") not in (None, ""):
            v = _num(kw["day_hours"])
            if not 4 <= v <= 9:
                raise SiteError("Din ke ghante 4-9 ke beech (kanoon 8 ke baad overtime).")
            r.day_hours = v
        if kw.get("week_hours") not in (None, ""):
            v = _num(kw["week_hours"])
            if not 24 <= v <= 48:
                raise SiteError("Hafte ke ghante 48 se zyada nahi rakh sakte (OSH Code).")
            r.week_hours = v
        if kw.get("lookahead_days") not in (None, ""):
            r.lookahead_days = max(3, min(60, int(_num(kw["lookahead_days"]))))
        if kw.get("behind_pct") not in (None, ""):
            r.behind_pct = max(1.0, min(50.0, _num(kw["behind_pct"])))
        if isinstance(kw.get("rates"), dict):
            rates = _j(r.rates, {})
            for t, v in kw["rates"].items():
                k = R.trade_of(t)
                if _num(v) > 0:
                    rates[k] = _num(v)
                else:
                    rates.pop(k, None)
            r.rates = _dump(rates)
        if isinstance(kw.get("cube_limits"), dict):
            cl = {k: _num(v) for k, v in kw["cube_limits"].items() if k in ("individual_minus", "mean_plus", "sd") and _num(v) > 0}
            r.cube_limits = _dump(cl)
        if kw.get("rules") is not None:
            rl = kw["rules"] if isinstance(kw["rules"], list) else [kw["rules"]]
            r.rules = _dump([_clean(x, 200) for x in rl if str(x).strip()][:30])
    return {**settings(tenant), "say": "Site ke niyam save."}


# ---------------------------------------------------------------- sites
def _site(s, tenant: str, ref: str = "") -> SsSite:
    rows = s.scalars(select(SsSite).where(SsSite.tenant_id == tenant)).all()
    if not rows:
        raise SiteError("Pehle site jodiye (naam, client).")
    ref = str(ref or "").strip()
    if not ref:
        run = [r for r in rows if r.status in ("running", "stopped")]
        if len(run) == 1:
            return run[0]
        raise SiteError("Kaun si site? " + ", ".join(r.name for r in rows[:8]))
    for r in rows:
        if r.id == ref or r.name.lower() == ref.lower() or (r.theka_project_id and r.theka_project_id == ref):
            return r
    hits = [r for r in rows if ref.lower() in r.name.lower()]
    if len(hits) == 1:
        return hits[0]
    raise SiteError(f"Site '{ref}' nahi mili." if not hits else "Kai sites: " + ", ".join(h.name for h in hits))


def _theka_project(tenant: str, ref: str) -> dict | None:
    if not ref:
        return None
    try:
        from ..theka import service as T
        return T.project_view(tenant, ref)
    except Exception:
        return None


def save_site(tenant: str, name: str = "", site: str = "", **kw: Any) -> dict:
    with _LOCK, session() as s:
        r = _site(s, tenant, site) if site else None
        new = r is None
        if new:
            if not str(name).strip():
                raise SiteError("Site ka naam chahiye.")
            r = SsSite(tenant_id=tenant)
            s.add(r)
        if name:
            r.name = _clean(name, 200)
        for k in ("address", "client", "client_email", "engineer"):
            if kw.get(k) is not None:
                setattr(r, k, _clean(kw[k], 300))
        if kw.get("client_phone") is not None:
            p = _phone(kw["client_phone"])
            if kw["client_phone"] and not p:
                raise SiteError("Client ka phone 10 ankon ka mobile hona chahiye.")
            r.client_phone = p
        for k in ("start", "finish"):
            if kw.get(k):
                d = _date(kw[k])
                if not d:
                    raise SiteError(f"Tareekh samajh nahi aayi: {kw[k]}")
                setattr(r, k, d.isoformat())
        if kw.get("status") in ("running", "done", "closed"):
            r.status = kw["status"]
        tp = kw.get("theka_project")
        s.flush()
        sid = r.id
    linked = None
    if tp:
        linked = _theka_project(tenant, str(tp))
        if not linked:
            raise SiteError(f"Theka mein kaam '{tp}' nahi mila.")
        with session() as s:
            r = s.get(SsSite, sid)
            r.theka_project_id = linked["id"]
            if not r.client and linked.get("client"):
                r.client = linked["client"]
            if not r.start and linked.get("start"):
                r.start, r.finish = linked["start"], linked.get("end", "")
    v = site_view(tenant, sid)
    say = f"{'Nayi site' if new else 'Site update'}: {v['name']}" + (f" ({v['client']})" if v["client"] else "") + "."
    if linked:
        say += f" Theka kaam '{linked['name']}' se judi: BOQ / naap / RA bill wahin rahenge, rukawat wahan ke hindrance register mein jayegi."
    return {"site": v, "say": say}


def site_view(tenant: str, ref: str = "") -> dict:
    with session() as s:
        r = _site(s, tenant, ref)
        stop = s.get(SsStop, r.stop_id) if r.stop_id else None
        v = {"id": r.id, "name": r.name, "address": r.address, "client": r.client, "client_phone": r.client_phone,
             "client_email": r.client_email, "engineer": r.engineer, "theka_project_id": r.theka_project_id, "start": r.start,
             "finish": r.finish, "status": r.status, "stop": _stop_view(stop) if stop else None}
    if v["theka_project_id"]:
        tp = _theka_project(tenant, v["theka_project_id"])
        v["theka"] = {"name": tp["name"], "progress_pct": tp["progress_pct"], "delay": tp.get("delay")} if tp else None
    return v


def sites(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(SsSite.id).where(SsSite.tenant_id == tenant)
        if status:
            q = q.where(SsSite.status == status)
        ids = s.scalars(q.order_by(SsSite.created_at)).all()
    return [site_view(tenant, i) for i in ids]


# ---------------------------------------------------------------- activities + progress
def _act(s, site: SsSite, ref: str) -> SsActivity:
    rows = s.scalars(select(SsActivity).where(SsActivity.site_id == site.id)).all()
    ref = str(ref or "").strip()
    if not ref:
        raise SiteError("Kaun sa kaam (activity)?")
    for a in rows:
        if a.id == ref or a.code == ref or a.name.lower() == ref.lower() or (a.boq_item and a.boq_item == ref):
            return a
    words = [w for w in R.low(ref).split() if len(w) > 2]
    hits = [a for a in rows if words and all(w in R.low(a.name + " " + a.location) for w in words)] or \
           [a for a in rows if R.low(ref) in R.low(a.name)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SiteError(f"Activity '{ref}' plan mein nahi; pehle 'plan' se jodiye.")
    raise SiteError("Kai activity: " + ", ".join(f"{h.code} {h.name}" for h in hits[:6]))


def plan(tenant: str, site: str = "", items: list | None = None, from_boq: bool = False) -> dict:
    """Activities with planned quantity and dates. from_boq: one activity per Theka BOQ item (dates she gives later)."""
    rows: list[dict] = []
    with session() as s:
        st = _site(s, tenant, site)
        sid, tp = st.id, st.theka_project_id
    if from_boq:
        if not tp:
            raise SiteError("Yeh site kisi Theka kaam se judi nahi: pehle `site theka_project=...`.")
        from ..theka import service as T
        for b in T.boq_items(tenant, tp):
            rows.append({"code": b["code"], "name": b["description"][:200], "unit": b["unit"], "qty": b["qty"], "boq_item": b["code"]})
    for it in items or []:
        if isinstance(it, dict) and str(it.get("name") or "").strip():
            rows.append(it)
    if not rows:
        raise SiteError("Activity ke naam / maatra / tareekh dijiye (ya from_boq).")
    added, updated, problems = 0, 0, []
    with _LOCK, session() as s:
        st = s.get(SsSite, sid)
        have = {a.code: a for a in s.scalars(select(SsActivity).where(SsActivity.site_id == sid)).all()}
        n = len(have)
        for it in rows:
            code = str(it.get("code") or "").strip()[:20]
            a = have.get(code) if code else None
            if a is None:
                n += 1
                a = SsActivity(tenant_id=tenant, site_id=sid, code=code or f"A{n:02d}")
                s.add(a)
                have[a.code] = a
                added += 1
            else:
                updated += 1
            a.name = _clean(it.get("name") or a.name, 200)
            if it.get("location") is not None:
                a.location = _clean(it["location"], 160)
            if it.get("unit"):
                a.unit = R.unit_of(it["unit"])
            if it.get("qty") not in (None, ""):
                a.qty = max(0.0, _num(it["qty"]))
            for k in ("start", "finish"):
                if it.get(k):
                    d = _date(it[k])
                    if d:
                        setattr(a, k, d.isoformat())
                    else:
                        problems.append(f"{a.name}: tareekh '{it[k]}' samajh nahi aayi")
            if a.start and a.finish and a.finish < a.start:
                problems.append(f"{a.name}: khatam hone ki tareekh shuru se pehle")
                a.finish = a.start
            if it.get("boq_item"):
                a.boq_item = str(it["boq_item"])[:40]
            if it.get("contractor") is not None:
                a.contractor = _clean(it["contractor"], 120)
            if isinstance(it.get("needs"), list):
                a.needs = _dump([{"item": R.low(x.get("item"))[:80], "qty": _num(x.get("qty")), "unit": R.unit_of(x.get("unit") or "")}
                                 for x in it["needs"] if isinstance(x, dict) and x.get("item") and _num(x.get("qty")) > 0])
        nm = st.name
    say = f"{nm}: {added} nayi activity" + (f", {updated} update" if updated else "") + "."
    if problems:
        say += " Dhyaan: " + "; ".join(problems[:5])
    return {"added": added, "updated": updated, "problems": problems, "activities": activities(tenant, sid), "say": say}


def progress(tenant: str, site: str = "", activity: str = "", qty=None, day: str = "", note: str = "", delay: str = "",
             lost_hours=None, by_client: bool | None = None, actor: str = "owner") -> dict:
    """Work done today on one activity (as reported: never rounded up). A delay reason goes to the Theka hindrance diary too."""
    d = _date(day, today(tenant))
    if d > today(tenant):
        raise SiteError("Aage ki tareekh ka kaam nahi likh sakte.")
    q = _num(qty)
    if q < 0:
        raise SiteError("Maatra ulti (minus) nahi ho sakti.")
    if not q and not delay and not note:
        raise SiteError("Kitna kaam hua, ya kyun nahi hua (rukawat) bataiye.")
    dk, client_side = R.delay_kind(delay)
    if by_client is not None:
        client_side = bool(by_client)
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        a = _act(s, st, activity)
        before = sum(p.qty for p in s.scalars(select(SsProgress).where(SsProgress.activity_id == a.id)).all())
        s.add(SsProgress(tenant_id=tenant, site_id=st.id, activity_id=a.id, day=d.isoformat(), qty=q, note=_clean(note, 500),
                         delay=_clean(delay, 500), delay_kind=dk, by_client=client_side,
                         lost_hours=_num(lost_hours) if lost_hours not in (None, "") else (8.0 if delay and not q else 0.0),
                         by=actor_name(tenant, actor)))
        cum = before + q
        aname, aunit, aqty, tp, sname, sid = a.name, a.unit, a.qty, st.theka_project_id, st.name, st.id
    if tp and (delay or q):
        try:
            from ..theka import service as T
            T.diary(tenant, tp, 0, f"{aname}: {_g(q)} {aunit}" if q else "", (f"{aname}: {_clean(delay, 200)}" if delay else ""),
                    lost_hours if lost_hours not in (None, "") else None, client_side, d.isoformat())
        except Exception:
            log.exception("theka diary mirror failed")
    say = f"{sname} {d.strftime('%d %b')}: {aname} {_g(q)} {aunit}" + (f" (kul {_g(cum)} / {_g(aqty)})" if aqty else "") + "."
    if aqty and cum > aqty:
        say += f" Plan se {_g(cum - aqty)} {aunit} zyada: drawing / BOQ badla to plan update kariye" + (" (Theka mein deviation dekhiye)." if tp else ".")
    if delay:
        say += f" Rukawat likhi ({'client / department ki taraf - EOT mein ginegi' if client_side else 'site ki taraf'})."
    return {"cumulative": round(cum, 3), "activity": next((x for x in activities(tenant, sid) if x["name"] == aname), None), "say": say}


def activities(tenant: str, site: str = "", on: date | None = None) -> list[dict]:
    on = on or today(tenant)
    with session() as s:
        st = _site(s, tenant, site)
        cfg = _st(s, tenant)
        acts = s.scalars(select(SsActivity).where(SsActivity.site_id == st.id)).all()
        prog = s.scalars(select(SsProgress).where(SsProgress.site_id == st.id)).all()
        tp = st.theka_project_id
        limit = cfg.behind_pct
        rows = []
        for a in acts:
            ps = [p for p in prog if p.activity_id == a.id]
            done = sum(p.qty for p in ps)
            pct = round(min(100.0, done * 100 / a.qty), 1) if a.qty else (100.0 if done else 0.0)
            reasons = [p.delay for p in sorted(ps, key=lambda p: p.day, reverse=True) if p.delay][:3]
            stt = R.activity_state(_date(a.start), _date(a.finish), on, pct, limit)
            rows.append({"id": a.id, "code": a.code, "name": a.name, "location": a.location, "unit": a.unit, "qty": a.qty, "start": a.start,
                         "finish": a.finish, "done": round(done, 3), "done_pct": pct, **stt, "reasons": reasons, "boq_item": a.boq_item,
                         "contractor": a.contractor, "needs": _j(a.needs, []),
                         "today": round(sum(p.qty for p in ps if p.day == on.isoformat()), 3)})
    if tp:
        try:
            from ..theka import service as T
            mb = {b["code"]: b for b in T.boq_items(tenant, tp)}
            for r in rows:
                b = mb.get(r["boq_item"])
                if b:
                    r["mb_done"] = b["done"]
                    r["mb_note"] = "Measurement book (Theka) mein naapa gaya: " + _g(b["done"]) + f" {b['unit']}"
        except Exception:
            pass
    return sorted(rows, key=lambda x: (x["start"] or "9999", x["code"]))


def lookahead(tenant: str, site: str = "", days: int | None = None) -> dict:
    """Coming work (next N days) + what each still needs: material balance short, behind-plan activities with reasons."""
    on = today(tenant)
    with session() as s:
        n = days or _st(s, tenant).lookahead_days
    end = on + timedelta(days=int(n))
    acts = activities(tenant, site, on)
    bal = {b["item"]: b["balance"] for b in material_balance(tenant, site)}
    coming, behind = [], []
    for a in acts:
        st, fi = _date(a["start"]), _date(a["finish"])
        if a["state"] in ("behind", "late"):
            behind.append(a)
        if st and st <= end and (not fi or fi >= on) and a["state"] != "done":
            short = []
            for nd in a["needs"]:
                have = bal.get(nd["item"], 0.0)
                left = nd["qty"] * (1 - a["done_pct"] / 100)
                if have < left:
                    short.append({"item": nd["item"], "need": round(left, 2), "have": round(have, 2), "unit": nd["unit"]})
            coming.append({**a, "short": short})
    parts = []
    for a in behind[:6]:
        parts.append(f"{a['name']}: plan {a['planned_pct']:g}%, hua {a['done_pct']:g}%" + (f" ({a['late_days']} din late)" if a["late_days"] else "")
                     + (f" - wajah: {a['reasons'][0][:60]}" if a["reasons"] else " - wajah likhi nahi"))
    for a in coming:
        for sh in a["short"]:
            parts.append(f"{a['name']} ke liye {sh['item']} {_g(sh['need'])} {sh['unit']} chahiye, site par {_g(sh['have'])}: indent ka card banayein?")
    return {"from": on.isoformat(), "to": end.isoformat(), "coming": coming, "behind": behind,
            "say": ("; ".join(parts) + ".") if parts else f"Agle {n} din: plan ke hisaab se, koi kami nahi dikhi."}


# ---------------------------------------------------------------- labour
def attendance(tenant: str, site: str = "", rows: list | None = None, day: str = "", actor: str = "owner", **one: Any) -> dict:
    """Rows: {contractor, trade, count, hours} for a gang or {worker, trade, contractor, hours, gender} for a named worker.
    Same day + contractor + trade (+ worker) = replaced, not doubled. Hours > her day limit = overtime (rounded per the rule)."""
    d = _date(day, today(tenant))
    if d > today(tenant):
        raise SiteError("Aage ki hazri nahi lag sakti.")
    items = list(rows or [])
    if one.get("trade") or one.get("worker") or one.get("count"):
        items.append(one)
    if not items:
        raise SiteError("Kis thekedar ke kitne log, kaun sa kaam, kitne ghante?")
    warn: list[str] = []
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        cfg = _st(s, tenant)
        limit = cfg.day_hours
        for it in items:
            trade = R.trade_of(it.get("trade") or it.get("worker") or "")
            contractor = _clean(it.get("contractor") or "Apne", 120)
            worker = _clean(it.get("worker") or "", 120)
            count = 1 if worker else int(_num(it.get("count")) or 0)
            if count <= 0:
                raise SiteError(f"{R.TRADE_LABEL[trade]}: kitne log?")
            if count > 2000:
                raise SiteError("Itne log? Dobara dekhiye.")
            h = _num(it.get("hours")) if it.get("hours") not in (None, "") else limit
            if not 0 < h <= 16:
                raise SiteError("Ghante 0-16 ke beech.")
            sp = R.split_hours(h, limit)
            old = s.scalars(select(SsLabour).where(SsLabour.site_id == st.id, SsLabour.day == d.isoformat(), SsLabour.contractor == contractor,
                                                   SsLabour.trade == trade, SsLabour.worker == worker)).first()
            row = old or SsLabour(tenant_id=tenant, site_id=st.id, day=d.isoformat(), contractor=contractor, trade=trade, worker=worker)
            row.count, row.hours, row.normal, row.ot = count, sp["hours"], sp["normal"], sp["ot"]
            row.gender = str(it.get("gender") or "")[:1].lower() if str(it.get("gender") or "")[:1].lower() in ("m", "f") else ""
            ref = str(it.get("id_ref") or "")
            row.id_ref = ref if re.fullmatch(r"\{id:[A-Za-z0-9_-]{4,40}\}", ref) else ""
            row.by = actor_name(tenant, actor)
            s.add(row)
            if sp["ot"]:
                warn.append(f"{worker or R.TRADE_LABEL[trade]} ({contractor}): {sp['ot']:g} ghante overtime - dugni dar (OSH Code)")
            if h > 12:
                warn.append(f"{worker or R.TRADE_LABEL[trade]}: {h:g} ghante - spread-over / aaram ke niyam aapke rajya ke dekhiye")
        s.flush()
        ws = R.week_start(d)
        named = s.scalars(select(SsLabour).where(SsLabour.tenant_id == tenant, SsLabour.worker != "", SsLabour.day >= ws.isoformat(),
                                                 SsLabour.day <= (ws + timedelta(days=6)).isoformat())).all()
        wk: dict[str, float] = {}
        for r in named:
            wk[r.worker] = wk.get(r.worker, 0.0) + r.hours
        for w, h in wk.items():
            if h > cfg.week_hours:
                warn.append(f"{w}: is hafte {h:g} ghante (> {cfg.week_hours:g}) - OSH Code 48 ghante / hafta")
        day_rows = s.scalars(select(SsLabour).where(SsLabour.site_id == st.id, SsLabour.day == d.isoformat())).all()
        total = sum(r.count for r in day_rows)
        tp, sname = st.theka_project_id, st.name
    if tp:
        try:
            from ..theka import service as T
            T.diary(tenant, tp, total, "", "", None, False, d.isoformat())
        except Exception:
            log.exception("theka diary labour mirror failed")
    say = f"{sname} {d.strftime('%d %b')}: aaj kul {total} log hazir." + (" " + "; ".join(warn[:5]) + "." if warn else "")
    return {"total": total, "warnings": warn, "say": say}


def labour_day(tenant: str, site: str = "", day: str = "") -> dict:
    d = _date(day, today(tenant))
    with session() as s:
        st = _site(s, tenant, site)
        rows = s.scalars(select(SsLabour).where(SsLabour.site_id == st.id, SsLabour.day == d.isoformat())).all()
        out: dict[str, dict] = {}
        for r in rows:
            c = out.setdefault(r.contractor, {"contractor": r.contractor, "trades": {}, "people": 0, "ot_hours": 0.0})
            t = c["trades"].setdefault(r.trade, {"trade": r.trade, "label": R.TRADE_LABEL.get(r.trade, r.trade), "people": 0})
            t["people"] += r.count
            c["people"] += r.count
            c["ot_hours"] += r.ot * r.count
    return {"day": d.isoformat(), "contractors": [{**c, "trades": list(c["trades"].values())} for c in out.values()],
            "total": sum(c["people"] for c in out.values())}


def register(tenant: str, site: str = "", start: str = "", end: str = "") -> dict:
    """Wage-register NUMBERS per contractor / trade for the period: man-days, normal hours, OT hours. Rupees only from her own
    daily rate per trade (an estimate to check the contractor's labour bill); salaries stay with payroll."""
    on = today(tenant)
    a = _date(start, on.replace(day=1))
    b = _date(end, on)
    with session() as s:
        st = _site(s, tenant, site)
        rates = _j(_st(s, tenant).rates, {})
        day_h = _st(s, tenant).day_hours
        rows = s.scalars(select(SsLabour).where(SsLabour.site_id == st.id, SsLabour.day >= a.isoformat(), SsLabour.day <= b.isoformat())).all()
        sname = st.name
    by: dict[tuple, dict] = {}
    workers: dict[str, dict] = {}
    for r in rows:
        k = (r.contractor, r.trade)
        x = by.setdefault(k, {"contractor": r.contractor, "trade": r.trade, "label": R.TRADE_LABEL.get(r.trade, r.trade), "man_days": 0,
                              "normal_hours": 0.0, "ot_hours": 0.0, "days": set()})
        x["man_days"] += r.count
        x["normal_hours"] += r.normal * r.count
        x["ot_hours"] += r.ot * r.count
        x["days"].add(r.day)
        if r.worker:
            w = workers.setdefault(r.worker, {"worker": r.worker, "contractor": r.contractor, "trade": r.trade, "days": 0, "hours": 0.0, "ot": 0.0})
            w["days"] += 1
            w["hours"] += r.hours
            w["ot"] += r.ot
    lines = []
    for x in by.values():
        rate = rates.get(x["trade"])
        est = round(rate * x["man_days"] + rate / day_h * R.OT_RATE * x["ot_hours"], 2) if rate else None
        lines.append({**{k: v for k, v in x.items() if k != "days"}, "days_worked": len(x["days"]), "normal_hours": round(x["normal_hours"], 2),
                      "ot_hours": round(x["ot_hours"], 2), "rate": rate, "estimate": est})
    lines.sort(key=lambda x: (x["contractor"], x["trade"]))
    tot = {"man_days": sum(x["man_days"] for x in lines), "ot_hours": round(sum(x["ot_hours"] for x in lines), 2)}
    say = (f"{sname} {a.strftime('%d %b')} - {b.strftime('%d %b')}: {tot['man_days']} man-days, {tot['ot_hours']:g} ghante overtime"
           f" ({len({x['contractor'] for x in lines})} thekedar). Salary / mazdoori payroll mein; yeh numbers thekedar ke bill se milaiye.")
    return {"site": sname, "from": a.isoformat(), "to": b.isoformat(), "lines": lines, "workers": list(workers.values()), "total": tot, "say": say}



# ---------------------------------------------------------------- material
def material(tenant: str, site: str = "", item: str = "", qty=None, kind: str = "in", unit: str = "", supplier: str = "", challan: str = "",
             vehicle: str = "", ok: bool = True, note: str = "", day: str = "", indent: str = "", actor: str = "owner") -> dict:
    """Received (with challan) / used / returned / wasted at site. Received goods marked not-ok stay out of the balance note."""
    q = abs(_num(qty))
    if q <= 0:
        raise SiteError("Maatra bataiye.")
    if kind not in ("in", "used", "return", "waste"):
        raise SiteError("kind: in | used | return | waste")
    it = R.low(item)[:80]
    if not it:
        raise SiteError("Kaun sa maal?")
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        if kind == "in" and challan:
            dup = s.scalars(select(SsMaterial).where(SsMaterial.site_id == st.id, SsMaterial.challan == str(challan)[:60], SsMaterial.item == it)).first()
            if dup:
                raise SiteError(f"Challan {challan} ka {item} pehle se darj ({dup.day}).")
        bal = sum(m.qty for m in s.scalars(select(SsMaterial).where(SsMaterial.site_id == st.id, SsMaterial.item == it)).all())
        if kind != "in" and q > bal + 1e-9:
            raise SiteError(f"Site par {item} sirf {_g(bal)} hai; {_g(q)} kharch kaise? Pehle aamad (receipt) likhiye.")
        un = R.unit_of(unit) if unit else (s.scalars(select(SsMaterial.unit).where(SsMaterial.site_id == st.id, SsMaterial.item == it)).first() or "")
        row = SsMaterial(tenant_id=tenant, site_id=st.id, day=d.isoformat(), item=it, unit=un, qty=q if kind == "in" else -q, kind=kind,
                         supplier=_clean(supplier, 160), challan=_clean(challan, 60), vehicle=_clean(vehicle, 20).upper(), ok=bool(ok),
                         note=_clean(note, 300), by=actor_name(tenant, actor))
        if indent:
            ind = _indent(s, tenant, indent)
            row.indent_id = ind.id
            if ind.status in ("approved", "ordered"):
                ind.status = "received"
        s.add(row)
        new_bal = bal + row.qty
        tp, sname = st.theka_project_id, st.name
    if tp and kind in ("in", "used"):
        try:
            from ..theka import service as T
            T.material(tenant, tp, it, q, None, kind == "used", d.isoformat(), f"site: {challan}" if challan else "site")
        except Exception:
            log.exception("theka material mirror failed")
    word = {"in": "aaya", "used": "lagaya", "return": "wapas gaya", "waste": "kharab / wastage"}[kind]
    say = f"{sname}: {item} {_g(q)} {un} {word}" + (f" (challan {challan})" if challan else "") + f"; site par ab {_g(new_bal)} {un}."
    if kind == "in" and not ok:
        say += " Maal theek nahi (quality) likha: supplier ko wapas / replace ki baat kijiye, photo jodiye."
    if new_bal <= 0:
        say += " Khatam! Indent ka card banayein?"
    return {"balance": round(new_bal, 3), "say": say}


def material_balance(tenant: str, site: str = "") -> list[dict]:
    with session() as s:
        st = _site(s, tenant, site)
        agg: dict[str, dict] = {}
        for m in s.scalars(select(SsMaterial).where(SsMaterial.site_id == st.id).order_by(SsMaterial.day)).all():
            a = agg.setdefault(m.item, {"item": m.item, "unit": m.unit, "received": 0.0, "used": 0.0, "returned": 0.0, "waste": 0.0, "last_in": ""})
            if m.kind == "in":
                a["received"] += m.qty
                a["last_in"] = m.day
            else:
                a[{"used": "used", "return": "returned", "waste": "waste"}[m.kind]] += -m.qty
            a["unit"] = a["unit"] or m.unit
    return [{**a, "balance": round(a["received"] - a["used"] - a["returned"] - a["waste"], 3)} for a in agg.values()]


# ---------------------------------------------------------------- indents (HER tap)
def _indent(s, tenant: str, ref: str) -> SsIndent:
    x = s.get(SsIndent, ref)
    if x is None:
        x = s.scalars(select(SsIndent).where(SsIndent.tenant_id == tenant, SsIndent.number == str(ref).upper())).first()
    if x is None or x.tenant_id != tenant:
        raise SiteError("Indent nahi mila.")
    return x


def _indent_show(x: SsIndent, site_name: str) -> dict:
    return {"number": x.number, "site": site_name, "items": _j(x.items, []), "need_by": x.need_by, "reason": x.reason, "supplier": x.supplier,
            "supplier_phone": x.supplier_phone, "amount": round(x.amount, 2)}


def _indent_view(s, x: SsIndent) -> dict:
    st = s.get(SsSite, x.site_id)
    show = _indent_show(x, st.name if st else "")
    v = {"id": x.id, **show, "amount_text": _rs(x.amount) if x.amount else "daam pata nahi", "checks": _j(x.checks, []), "status": x.status,
         "hash": x.hash, "asked_by": x.asked_by, "reason_no": x.reason_no}
    if x.status in ("approved", "ordered") and x.supplier_phone:
        v["wa"] = f"https://wa.me/91{x.supplier_phone}?text={quote(indent_message(show))}"
    return v


def indent_message(show: dict) -> str:
    lines = "\n".join(f"- {i['item']}: {_g(i['qty'])} {i.get('unit', '')}".rstrip() for i in show["items"])
    return (f"Namaste{(' ' + show['supplier']) if show['supplier'] else ''}, site '{show['site']}' ke liye order ({show['number']}):\n{lines}\n"
            + (f"Chahiye: {show['need_by']} tak.\n" if show["need_by"] else "") + "Rate aur delivery confirm kijiye. Dhanyavaad.")


def indent_request(tenant: str, site: str = "", items: list | None = None, need_by: str = "", reason: str = "", supplier: str = "",
                   supplier_phone: str = "", amount=None, actor: str = "owner", conv: str = "") -> dict:
    """Make the card. Nothing is ordered here: only her tap in the app (decide_indent by_tap=True)."""
    its = []
    for i in items or []:
        if isinstance(i, dict) and str(i.get("item") or "").strip() and _num(i.get("qty")) > 0:
            its.append({"item": R.low(i["item"])[:80], "qty": _num(i["qty"]), "unit": R.unit_of(i.get("unit") or "")})
    if not its:
        raise SiteError("Kya maal, kitna? (items [{item, qty, unit}])")
    a = _num(amount)
    if a < 0 or a > 50_000_000:
        raise SiteError("Rakam galat lagti hai.")
    nb = _date(need_by) if need_by else None
    if need_by and not nb:
        raise SiteError(f"Tareekh samajh nahi aayi: {need_by}")
    on = today(tenant)
    ph = _phone(supplier_phone)
    if supplier_phone and not ph:
        raise SiteError("Supplier ka phone 10 ankon ka mobile.")
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        key = _sha(sorted((i["item"], i["qty"]) for i in its))
        for x in s.scalars(select(SsIndent).where(SsIndent.site_id == st.id, SsIndent.status == "waiting")).all():
            if _sha(sorted((i["item"], i["qty"]) for i in _j(x.items, []))) == key:
                return {"indent": _indent_view(s, x), "existing": True, "status": "needs_tap",
                        "say": f"{x.number} ka card pehle se aapki haan ka intezaar kar raha hai."}
        bal: dict[str, float] = {}
        for m in s.scalars(select(SsMaterial).where(SsMaterial.site_id == st.id)).all():
            bal[m.item] = bal.get(m.item, 0.0) + m.qty
        checks = []
        for i in its:
            have = bal.get(i["item"], 0.0)
            if have > 0:
                checks.append(f"{i['item']}: site par abhi {_g(have)} {i['unit']} pada hai.")
            used = [-m.qty for m in s.scalars(select(SsMaterial).where(SsMaterial.site_id == st.id, SsMaterial.item == i["item"],
                                                                        SsMaterial.kind == "used", SsMaterial.day >= (on - timedelta(days=14)).isoformat())).all()]
            if used:
                per_day = sum(used) / 14
                if per_day > 0 and i["qty"] > per_day * 60:
                    checks.append(f"{i['item']}: pichhle 14 din mein roz ~{per_day:.1f} laga; yeh {i['qty'] / per_day:.0f} din ka maal hai.")
        if nb and nb < on:
            checks.append("Chahiye-tak ki tareekh nikal chuki hai.")
        if not a:
            checks.append("Daam pata nahi: supplier ka quote aane par rakam ke saath naya card banaiye (Hoola daam nahi gadhta).")
        x = SsIndent(tenant_id=tenant, site_id=st.id, number=_next(s, tenant, "indent", "IND"), items=_dump(its), need_by=nb.isoformat() if nb else "",
                     reason=_clean(reason, 300), supplier=_clean(supplier, 160), supplier_phone=ph, amount=a, checks=_dump(checks),
                     asked_by=actor_name(tenant, actor), conv=conv)
        s.add(x)
        s.flush()
        x.hash = _sha(_indent_show(x, st.name))
        view = _indent_view(s, x)
    say = (f"{view['number']}: " + ", ".join(f"{i['item']} {_g(i['qty'])} {i['unit']}" for i in its) + f" ({view['amount_text']})"
           + " - indent ka card aapki haan ke liye bheja hai. Hoola khud order nahi karta, paise nahi deta.")
    if checks:
        say += " Dhyaan: " + " ".join(checks)
    _publish(tenant, "sitesup_indent", {"indent": view, "say": say}, conv)
    return {"indent": view, "status": "needs_tap", "say": say}


def indent_card(tenant: str, indent_id: str) -> dict | None:
    with session() as s:
        x = s.get(SsIndent, indent_id)
        if x is None or x.tenant_id != tenant:
            return None
        return _indent_view(s, x)


def indent_challenge(tenant: str, indent_id: str) -> dict:
    """approvekey's message format (kind 'sitesup'): the phone signs this card as it is NOW."""
    from .. import approvekey as ak
    c = indent_card(tenant, indent_id)
    if not c or c["status"] != "waiting":
        raise SiteError("Yeh card ab baaki nahi hai.")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|sitesup|{indent_id}|{c['hash']}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="sitesup", target=indent_id, digest=c["hash"], message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    return {"challenge_id": chid, "message": msg, "expires_at": exp.isoformat(),
            "show": {"title": f"Indent {c['number']}: {c['site'][:40]}", "amount": c["amount_text"], "payee": c["supplier"]}}


def _verify_fingerprint(tenant: str, indent_id: str, digest: str, proof: dict | None) -> None:
    from .. import approvekey as ak
    if not proof:
        raise SiteError("fingerprint_needed")
    with session() as s:
        ak._settle(s, tenant)
        ok = ak._check(s, tenant, "sitesup", indent_id, proof, digest)
    if not ok:
        raise SiteError("fingerprint_invalid")


def decide_indent(tenant: str, indent_id: str, yes: bool, card_hash: str = "", reason: str = "", proof: dict | None = None,
                  by_tap: bool = False) -> dict:
    """ONLY her tap in the app (API). The tool can never reach this with by_tap."""
    if not by_tap:
        raise SiteError("Indent / kharid ki haan sirf aapke tap se (app ka card).")
    with session() as s:
        x = _indent(s, tenant, indent_id)
        if x.status != "waiting":
            return {"indent": _indent_view(s, x), "say": f"{x.number} pehle hi '{x.status}' hai."}
        st = s.get(SsSite, x.site_id)
        if not card_hash or card_hash != x.hash or _sha(_indent_show(x, st.name if st else "")) != x.hash:
            raise SiteError("Card badal gaya hai; naya card dekhiye.")
        amount, xid = x.amount, x.id
    if yes and amount > 0:
        from .. import approvekey as ak
        if ak.active_on(tenant):
            _verify_fingerprint(tenant, xid, card_hash, proof)
    with _LOCK, session() as s:
        x = s.get(SsIndent, xid)
        x.status = "approved" if yes else "rejected"
        x.reason_no = _clean(reason, 300)
        x.decided_at = now()
        view = _indent_view(s, x)
    if yes:
        say = f"{view['number']} maana. Supplier ko order aap bhejiye" + (" (WhatsApp draft taiyaar)" if view.get("wa") else "") + \
            "; maal aaye to challan ke saath 'material' mein likhiye. Paise aap khud dengi."
    else:
        say = f"{view['number']}: nahi mangwana" + (f" ({view['reason_no']})" if view["reason_no"] else "") + "."
    return {"indent": view, "say": say}


def indent_ordered(tenant: str, indent_id: str) -> dict:
    with session() as s:
        x = _indent(s, tenant, indent_id)
        if x.status != "approved":
            raise SiteError(f"{x.number} abhi '{x.status}' hai: pehle aapki haan (card par tap).")
        x.status = "ordered"
        return {"indent": _indent_view(s, x), "say": f"{x.number}: order bhej diya likha. Maal aane par challan ke saath material mein."}


def indents(tenant: str, status: str = "", site: str = "") -> list[dict]:
    with session() as s:
        q = select(SsIndent).where(SsIndent.tenant_id == tenant)
        if site:
            q = q.where(SsIndent.site_id == _site(s, tenant, site).id)
        if status:
            q = q.where(SsIndent.status == status)
        return [_indent_view(s, x) for x in s.scalars(q.order_by(SsIndent.created_at.desc())).all()[:80]]


# ---------------------------------------------------------------- safety
def toolbox(tenant: str, site: str = "", topic: str = "", people=None, by: str = "", note: str = "", day: str = "", actor: str = "owner") -> dict:
    n = int(_num(people))
    if n <= 0:
        raise SiteError("Kitne log the talk mein?")
    t = _clean(topic, 160) or R.TOOLBOX_TOPICS[today(tenant).toordinal() % len(R.TOOLBOX_TOPICS)]
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        s.add(SsSafety(tenant_id=tenant, site_id=st.id, kind="talk", day=d.isoformat(), sub="talk", text=t, people=n,
                       data=_dump({"by": _clean(by, 80), "note": _clean(note, 300)}), by=actor_name(tenant, actor)))
        present = sum(r.count for r in s.scalars(select(SsLabour).where(SsLabour.site_id == st.id, SsLabour.day == d.isoformat())).all())
        sname = st.name
    say = f"{sname}: toolbox talk '{t}' - {n} log."
    if present and n < present:
        say += f" Aaj {present} hazir the; baaki {present - n} ko bhi bataiye."
    return {"say": say, "topic": t}


def checklist(tenant: str, site: str = "", kind: str = "", answers: dict | None = None, area: str = "", day: str = "",
              actor: str = "owner", conv: str = "") -> dict:
    """A checklist as answered at site. A critical 'no' = unsafe: a stop-work card for HER tap is prepared (not ordered)."""
    try:
        res = R.checklist_result(str(kind), dict(answers or {}))
    except ValueError as e:
        raise SiteError(str(e))
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        row = SsSafety(tenant_id=tenant, site_id=st.id, kind="check", day=d.isoformat(), sub=res["kind"], text=_clean(area, 200),
                       data=_dump(res), by=actor_name(tenant, actor))
        s.add(row)
        s.flush()
        rid, sname, sid = row.id, st.name, st.id
    say = f"{sname}: {res['label']} checklist {res['score']}%."
    out = {"result": res, "id": rid}
    if res["failed"]:
        say += " Kami: " + "; ".join(i["q"] for i in res["items"] if i["id"] in res["failed"])[:400]
    if res["unanswered"]:
        say += f" {len(res['unanswered'])} sawaal ka jawab baaki."
    if res["unsafe"]:
        reason = f"{res['label']}: " + "; ".join(i["q"] for i in res["items"] if i["id"] in res["unsafe"])
        stop = stop_request(tenant, sid, area or res["label"], reason, rid, actor=actor, conv=conv)
        out["stop"] = stop["stop"]
        say += (" JAAN KA KHATRA ho to abhi logon ko us jagah se door hataiye. Kaam rokne (stop-work) ka card aapki haan ke liye bheja hai.")
    out["say"] = say
    return out


def incident(tenant: str, site: str = "", text: str = "", kind: str = "", at: str = "", people=None, names: str = "", action: str = "",
             injury_off_since: str = "", actor: str = "owner", conv: str = "") -> dict:
    """Near-miss / first aid / injury / death / dangerous occurrence in the register. Form XI clock (OSH Central Rules 2026 r.7)."""
    t = _clean(text, 1000)
    if not t:
        raise SiteError("Kya hua, kahan, kab?")
    k = R.incident_kind(kind, t)
    tz = _tz(tenant)
    when = None
    if at:
        try:
            when = datetime.fromisoformat(str(at)).replace(tzinfo=tz) if "T" in str(at) or ":" in str(at) else None
        except ValueError:
            when = None
    when = (when or _local_now(tenant)).astimezone(timezone.utc)
    off = None
    if injury_off_since:
        try:
            off = datetime.fromisoformat(str(injury_off_since)).replace(tzinfo=tz).astimezone(timezone.utc)
        except ValueError:
            off = None
    due, rule = R.report_due(k, when, off)
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        row = SsSafety(tenant_id=tenant, site_id=st.id, kind="incident", number=_next(s, tenant, "incident", "INC", 3),
                       day=when.astimezone(tz).date().isoformat(), at=when, sub=k, text=t, people=int(_num(people)),
                       data=_dump({"names": _clean(names, 300), "action": _clean(action, 500), "rule": rule}), due_at=due,
                       by=actor_name(tenant, actor))
        s.add(row)
        s.flush()
        v = _incident_view(row, st.name)
        sname, sid, tp = st.name, st.id, st.theka_project_id
    first = {"death": "112 / ambulance, police - pehle jaan aur jagah. ", "injury": "Pehle ilaaj (first aid / hospital). ",
             "dangerous": "Us jagah se sabko door kijiye, jagah ko waisa hi rehne dijiye (inquiry). "}.get(k, "")
    say = f"{sname}: {v['number']} {R.INCIDENT_KINDS[k]} register mein. {first}{rule}"
    if due:
        say += f" Notice ki aakhri ghadi: {v['due_local']}. Form XI ka draft taiyaar; aap / aapka safety officer bhariye, phir 'reported' likhiye."
    if k == "near_miss":
        say += " Near-miss batana achha hai: aisi jagah theek kariye taaki chot na ho."
    out = {"incident": v, "say": say}
    if k in ("death", "dangerous", "injury"):
        out["form_xi"] = form_xi_text(tenant, v["id"])
        _publish(tenant, "sitesup_alert", {"kind": "incident", "site": sname, "say": say, "incident": v}, conv)
        if k in ("death", "dangerous"):
            st_ = stop_request(tenant, sid, "Ghatna ki jagah", f"{v['number']}: {t[:200]}", v["id"], actor=actor, conv=conv)
            out["stop"] = st_["stop"]
    if tp and k in ("death", "dangerous", "injury"):
        try:
            from ..theka import service as T
            T.diary(tenant, tp, 0, "", f"{v['number']}: {R.INCIDENT_KINDS[k]}", None, False, v["day"])
        except Exception:
            pass
    return out


def _incident_view(r: SsSafety, site_name: str = "") -> dict:
    d = _j(r.data, {})
    due = _aware(r.due_at)
    return {"id": r.id, "number": r.number, "site": site_name, "kind": r.sub, "label": R.INCIDENT_KINDS.get(r.sub, r.sub), "text": r.text,
            "day": r.day, "at": _aware(r.at).isoformat() if r.at else "", "people": r.people, "names": d.get("names", ""), "action": d.get("action", ""),
            "rule": d.get("rule", ""), "due_at": due.isoformat() if due else "", "due_local": due.strftime("%d %b %H:%M UTC") if due else "",
            "reported": r.reported, "overdue": bool(due and not r.reported and due < datetime.now(timezone.utc))}


def form_xi_text(tenant: str, incident_id: str) -> str:
    """Plain draft of what Form XI asks (her state's form / portal decides the exact format)."""
    with session() as s:
        r = s.get(SsSafety, incident_id)
        if r is None or r.tenant_id != tenant or r.kind != "incident":
            raise SiteError("Ghatna nahi mili.")
        st = s.get(SsSite, r.site_id)
        cfg = _st(s, tenant)
        v = _incident_view(r, st.name if st else "")
        addr = st.address if st else ""
        firm = cfg.firm
    return (f"NOTICE OF ACCIDENT / DANGEROUS OCCURRENCE (Form XI - OSH Code 2020 s.10; check your State's form)\n"
            f"1. Establishment / employer: {firm or '__________'}\n2. Site address: {addr or '__________'}\n"
            f"3. Date and time: {v['at'][:16].replace('T', ' ')} UTC\n4. Kind: {v['label']}\n5. What happened: {v['text']}\n"
            f"6. Persons affected (names / age / trade / contractor): {v['names'] or '__________'}\n"
            f"7. First aid / hospital / action taken: {v['action'] or '__________'}\n8. Reported by: __________ (signature, designation)\n"
            f"To: Inspector-cum-Facilitator; copy DM / SDO" + (", police station, family of the worker" if v["kind"] == "death" else "") + ".")


def incident_reported(tenant: str, incident_id: str, ref: str) -> dict:
    with session() as s:
        r = s.get(SsSafety, incident_id)
        if r is None or r.tenant_id != tenant or r.kind != "incident":
            raise SiteError("Ghatna nahi mili.")
        if not str(ref).strip():
            raise SiteError("Kisko / kaise bheja (portal ref / email / acknowledgement) likhiye.")
        r.reported = _clean(ref, 160)
        return {"incident": _incident_view(r), "say": f"{r.number}: notice bheja likha ({r.reported})."}


def safety_log(tenant: str, site: str = "", kind: str = "", days: int = 30) -> list[dict]:
    on = today(tenant)
    with session() as s:
        st = _site(s, tenant, site)
        q = select(SsSafety).where(SsSafety.site_id == st.id, SsSafety.day >= (on - timedelta(days=days)).isoformat())
        if kind:
            q = q.where(SsSafety.kind == kind)
        out = []
        for r in s.scalars(q.order_by(SsSafety.day.desc())).all():
            if r.kind == "incident":
                out.append({"type": "incident", **_incident_view(r, st.name)})
            elif r.kind == "check":
                d = _j(r.data, {})
                out.append({"type": "check", "id": r.id, "day": r.day, "kind": r.sub, "label": d.get("label", r.sub), "area": r.text,
                            "score": d.get("score"), "failed": d.get("failed", []), "unsafe": d.get("unsafe", [])})
            else:
                out.append({"type": "talk", "id": r.id, "day": r.day, "topic": r.text, "people": r.people})
    return out


# ---------------------------------------------------------------- stop work (HER tap)
def _stop_show(x: SsStop, site_name: str) -> dict:
    return {"number": x.number, "site": site_name, "area": x.area, "reason": x.reason, "contractor": x.contractor}


def _stop_view(x: SsStop, site_name: str = "") -> dict:
    return {"id": x.id, **_stop_show(x, site_name), "status": x.status, "hash": x.hash, "lift_note": x.lift_note, "asked_by": x.asked_by}


def stop_request(tenant: str, site: str, area: str, reason: str, source: str = "", contractor: str = "", actor: str = "owner", conv: str = "") -> dict:
    """Card only. The stop-work order is given only by her tap (decide_stop by_tap=True)."""
    if not str(reason).strip():
        raise SiteError("Kaam kyon rokna hai?")
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        for x in s.scalars(select(SsStop).where(SsStop.site_id == st.id, SsStop.status == "waiting")).all():
            if x.area.lower() == _clean(area, 200).lower():
                x.reason = _clean(x.reason + " | " + reason, 1000) if reason not in x.reason else x.reason
                x.hash = _sha(_stop_show(x, st.name))
                v = _stop_view(x, st.name)
                break
        else:
            x = SsStop(tenant_id=tenant, site_id=st.id, number=_next(s, tenant, "stop", "SW", 3), area=_clean(area, 200) or "Poori site",
                       reason=_clean(reason, 1000), source=str(source or "")[:40], contractor=_clean(contractor, 120),
                       asked_by=actor_name(tenant, actor), conv=conv)
            s.add(x)
            s.flush()
            x.hash = _sha(_stop_show(x, st.name))
            v = _stop_view(x, st.name)
    say = f"{v['number']}: '{v['area']}' par kaam rokne ka card aapki haan ke liye. Wajah: {v['reason'][:200]}"
    _publish(tenant, "sitesup_stop", {"stop": v, "say": say}, conv)
    return {"stop": v, "status": "needs_tap", "say": say}


def decide_stop(tenant: str, stop_id: str, yes: bool, card_hash: str = "", by_tap: bool = False) -> dict:
    if not by_tap:
        raise SiteError("Kaam rokne ka order sirf aapke tap se.")
    with _LOCK, session() as s:
        x = s.get(SsStop, stop_id)
        if x is None or x.tenant_id != tenant:
            raise SiteError("Card nahi mila.")
        st = s.get(SsSite, x.site_id)
        if x.status != "waiting":
            return {"stop": _stop_view(x, st.name), "say": f"{x.number} pehle hi '{x.status}' hai."}
        if not card_hash or card_hash != x.hash or _sha(_stop_show(x, st.name)) != x.hash:
            raise SiteError("Card badal gaya hai; naya card dekhiye.")
        x.status = "active" if yes else "rejected"
        if yes and x.area.lower() in ("poori site", "site", "puri site"):
            st.status, st.stop_id = "stopped", x.id
        v = _stop_view(x, st.name)
        sname, tp, day_ = st.name, st.theka_project_id, today(tenant).isoformat()
    if yes:
        notice = f"{sname}: {v['area']} par kaam abhi se BAND (stop-work {v['number']}). Wajah: {v['reason'][:300]}. Jab tak theek karke dobara jaancha na jaye, koi kaam nahi."
        if tp:
            try:
                from ..theka import service as T
                T.diary(tenant, tp, 0, "", f"Stop-work {v['number']}: {v['area']}", None, False, day_)
            except Exception:
                pass
        return {"stop": v, "notice": notice, "say": f"{v['number']} laagu. Thekedar / foreman ko yeh notice bataiye (WhatsApp draft taiyaar)."}
    return {"stop": v, "say": f"{v['number']}: kaam nahi roka (aapka faisla)."}


def lift_stop(tenant: str, stop_id: str, note: str, by_tap: bool = False) -> dict:
    if not by_tap:
        raise SiteError("Kaam dobara shuru karne ki haan bhi sirf aapke tap se.")
    if not str(note).strip():
        raise SiteError("Kya theek kiya gaya? (jaise: guard rail lag gayi, dobara checklist 100%)")
    with _LOCK, session() as s:
        x = s.get(SsStop, stop_id)
        if x is None or x.tenant_id != tenant or x.status != "active":
            raise SiteError("Chalu stop-work nahi mila.")
        x.status, x.lift_note = "lifted", _clean(note, 300)
        st = s.get(SsSite, x.site_id)
        if st.stop_id == x.id:
            st.status, st.stop_id = "running", ""
        return {"stop": _stop_view(x, st.name), "say": f"{x.number} hataya: kaam shuru ({x.lift_note})."}


def stops(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(SsStop).where(SsStop.tenant_id == tenant)
        if status:
            q = q.where(SsStop.status == status)
        out = []
        for x in s.scalars(q.order_by(SsStop.created_at.desc())).all()[:60]:
            st = s.get(SsSite, x.site_id)
            out.append(_stop_view(x, st.name if st else ""))
        return out


# ---------------------------------------------------------------- quality: pour cards, cubes, snags
def pour(tenant: str, site: str = "", element: str = "", grade: str = "", volume=None, cement: str = "", day: str = "", source: str = "",
         slump: str = "", checks: dict | None = None, hot_dry: bool = False, ages: list | None = None, actor: str = "owner") -> dict:
    v = _num(volume)
    if v <= 0:
        raise SiteError("Kitna concrete (cum)?")
    if not str(element).strip():
        raise SiteError("Kaun sa hissa (slab / column / beam ... kahan)?")
    if R.grade_fck(grade) is None:
        raise SiteError("Grade (M20 / M25 ...) bataiye.")
    d = _date(day, today(tenant))
    n = R.samples_for(v)
    cure = R.curing_days(cement, hot_dry)
    ag = R.cube_ages(cement, [int(_num(a)) for a in (ages or []) if _num(a)])
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        p = SsPour(tenant_id=tenant, site_id=st.id, number=_next(s, tenant, "pour", "PC", 3), element=_clean(element, 200), grade=str(grade).upper()[:12],
                   cement=_clean(cement, 40), volume=v, day=d.isoformat(), source=_clean(source, 120), slump=_clean(slump, 20),
                   checks=_dump(dict(checks or {})), samples=n, curing_until=(d + timedelta(days=cure)).isoformat(), by=actor_name(tenant, actor))
        s.add(p)
        s.flush()
        for smp in range(1, n + 1):
            for a in ag:
                s.add(SsCube(tenant_id=tenant, pour_id=p.id, sample=smp, age=a, due=(d + timedelta(days=a)).isoformat()))
        pv = _pour_view(s, p)
        sname = st.name
    say = (f"{sname}: {pv['number']} {pv['element']} {pv['grade']} {_g(v)} cum. IS 456 ke hisaab se kam se kam {n} sample (har sample 3 cube) = {n * 3} cube "
           f"bhariye; test {', '.join(str(a) for a in ag)} din par (tareekh yaad dilaunga). Curing {cure} din, {pv['curing_until']} tak.")
    open_chk = [k for k, ok in (checks or {}).items() if ok in (False, "no", "nahi")]
    if open_chk:
        say += " Pour se pehle baaki: " + ", ".join(open_chk) + "."
    return {"pour": pv, "say": say}


def _pour_view(s, p: SsPour) -> dict:
    cubes = s.scalars(select(SsCube).where(SsCube.pour_id == p.id).order_by(SsCube.age, SsCube.sample)).all()
    return {"id": p.id, "number": p.number, "element": p.element, "grade": p.grade, "cement": p.cement, "volume": p.volume, "day": p.day,
            "source": p.source, "slump": p.slump, "checks": _j(p.checks, {}), "samples": p.samples, "curing_until": p.curing_until,
            "cubes": [{"id": c.id, "sample": c.sample, "age": c.age, "due": c.due, "results": _j(c.results, []), "verdict": c.verdict,
                       "lab": c.lab} for c in cubes]}


def _pour(s, tenant: str, ref: str) -> SsPour:
    p = s.get(SsPour, ref) or s.scalars(select(SsPour).where(SsPour.tenant_id == tenant, SsPour.number == str(ref).upper())).first()
    if p is None or p.tenant_id != tenant:
        raise SiteError("Pour card nahi mila (PC-001 jaisa number).")
    return p


def cube_result(tenant: str, pour_ref: str, age=None, results: list | None = None, sample: int = 1, lab: str = "", tested_on: str = "",
                conv: str = "") -> dict:
    vals = [_num(x) for x in (results or []) if _num(x) > 0]
    if not vals:
        raise SiteError("Cube ke result N/mm2 mein (jaise 18.2, 17.9, 18.6).")
    if any(x > 150 for x in vals):
        raise SiteError("N/mm2 mein dijiye (kN load nahi): 150 mm cube par load / 22.5 = N/mm2.")
    a = int(_num(age)) or 28
    with _LOCK, session() as s:
        p = _pour(s, tenant, pour_ref)
        c = s.scalars(select(SsCube).where(SsCube.pour_id == p.id, SsCube.age == a, SsCube.sample == int(sample or 1))).first()
        if c is None:
            c = SsCube(tenant_id=tenant, pour_id=p.id, sample=int(sample or 1), age=a, due=(_date(p.day) + timedelta(days=a)).isoformat())
            s.add(c)
        earlier = []
        if a >= 28:
            same = s.scalars(select(SsPour).where(SsPour.site_id == p.site_id, SsPour.grade == p.grade)).all()
            ids = [x.id for x in same]
            for e in s.scalars(select(SsCube).where(SsCube.pour_id.in_(ids), SsCube.age == a, SsCube.verdict.in_(("pass", "fail")))
                               .order_by(SsCube.tested_on, SsCube.due)).all():
                if e.id != c.id and _j(e.results, []):
                    rr = _j(e.results, [])
                    earlier.append(sum(rr) / len(rr))
        lim = _j(_st(s, tenant).cube_limits, {})
        j = R.judge_cubes(p.grade, a, vals, earlier, lim)
        c.results = _dump(vals)
        c.verdict = j["verdict"]
        c.lab = _clean(lab, 120)
        c.tested_on = (_date(tested_on, today(tenant))).isoformat()
        st = s.get(SsSite, p.site_id)
        pv, sname, pnum, el = _pour_view(s, p), st.name, p.number, p.element
    say = f"{sname} {pnum} ({el}) sample {sample}: {j['say']}"
    if j["verdict"] in ("fail", "indicative_low"):
        _publish(tenant, "sitesup_alert", {"kind": "cube", "site": sname, "say": say, "pour": pnum}, conv)
    return {"pour": pv, "judge": j, "say": say}


def pours(tenant: str, site: str = "") -> list[dict]:
    with session() as s:
        st = _site(s, tenant, site)
        return [_pour_view(s, p) for p in s.scalars(select(SsPour).where(SsPour.site_id == st.id).order_by(SsPour.day.desc())).all()[:60]]


def cubes_due(tenant: str, within: int = 2) -> list[dict]:
    on = today(tenant)
    with session() as s:
        out = []
        for c in s.scalars(select(SsCube).where(SsCube.tenant_id == tenant, SsCube.verdict == "", SsCube.due <= (on + timedelta(days=within)).isoformat())
                           .order_by(SsCube.due)).all():
            p = s.get(SsPour, c.pour_id)
            st = s.get(SsSite, p.site_id) if p else None
            if not p or not st:
                continue
            out.append({"cube": c.id, "pour": p.number, "element": p.element, "grade": p.grade, "site": st.name, "age": c.age, "sample": c.sample,
                        "due": c.due, "late_days": max(0, (on - date.fromisoformat(c.due)).days)})
    return out


def snag(tenant: str, site: str = "", text: str = "", location: str = "", trade: str = "", contractor: str = "", due: str = "",
         actor: str = "owner") -> dict:
    t = _clean(text, 600)
    if not t:
        raise SiteError("Kya kami hai, kahan?")
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        x = SsSnag(tenant_id=tenant, site_id=st.id, number=_next(s, tenant, "snag", "SN", 3), location=_clean(location, 160), text=t,
                   trade=R.trade_of(trade or t) if (trade or t) else "", contractor=_clean(contractor, 120),
                   due=(_date(due).isoformat() if _date(due) else ""), day=today(tenant).isoformat(), by=actor_name(tenant, actor))
        s.add(x)
        s.flush()
        v = _snag_view(s, x)
    return {"snag": v, "say": f"{v['number']}: {v['location'] or 'site'} - {t[:80]}. Photo jodiye; thekedar theek kare to 'fixed', aap / engineer dekh lein to 'verified'."}


def _snag_view(s, x: SsSnag) -> dict:
    photos = s.scalars(select(SsPhoto.id).where(SsPhoto.ref == x.id)).all()
    return {"id": x.id, "number": x.number, "location": x.location, "text": x.text, "trade": x.trade, "contractor": x.contractor, "due": x.due,
            "status": x.status, "day": x.day, "photos": list(photos)}


def snag_status(tenant: str, ref: str, status: str, actor: str = "owner") -> dict:
    if status not in ("open", "fixed", "verified"):
        raise SiteError("status: open | fixed | verified")
    with session() as s:
        x = s.get(SsSnag, ref) or s.scalars(select(SsSnag).where(SsSnag.tenant_id == tenant, SsSnag.number == str(ref).upper())).first()
        if x is None or x.tenant_id != tenant:
            raise SiteError("Snag nahi mila.")
        if status == "verified" and x.status != "fixed":
            raise SiteError("Pehle 'fixed' (theek kiya), phir dekh kar 'verified'.")
        x.status = status
        return {"snag": _snag_view(s, x), "say": f"{x.number}: {status}."}


def snags(tenant: str, site: str = "", status: str = "") -> list[dict]:
    with session() as s:
        st = _site(s, tenant, site)
        q = select(SsSnag).where(SsSnag.site_id == st.id)
        if status:
            q = q.where(SsSnag.status == status)
        return [_snag_view(s, x) for x in s.scalars(q.order_by(SsSnag.day.desc())).all()]


# ---------------------------------------------------------------- photos (EXIF / GPS stripped)
def _dir(tenant: str, site_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", tenant)[:64]
    p = Path(os.environ.get("SITESUP_DIR") or "data/sitesup") / safe / site_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def clean_image(data: bytes) -> bytes:
    """Re-encode from pixels (JPEG <= 1600 px): EXIF, GPS, camera details gone."""
    from PIL import Image, ImageOps
    if not data or len(data) > 20 * 1024 * 1024:
        raise SiteError("Photo khaali ya 20 MB se badi.")
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise SiteError("Yeh photo khul nahi rahi (JPG / PNG / WEBP).")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1600, 1600))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85, optimize=True)
    return out.getvalue()


def add_photo(tenant: str, data: bytes, site: str = "", ref: str = "", stage: str = "site", note: str = "", file_id: str = "") -> dict:
    if file_id and not data:
        from ..mailbox import service as ms
        try:
            data = Path(ms._file_row(tenant, str(file_id)).stored_path).read_bytes()
        except Exception:
            data = b""
        if not data:
            raise SiteError("File nahi mili (chat file 24 ghante tak rehti hai).")
    if stage not in ("site", "snag", "fixed", "incident", "pour", "material", "progress"):
        raise SiteError("stage: site | snag | fixed | incident | pour | material | progress")
    clean = clean_image(data)
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        if ref:
            ok = any(s.get(m, ref) is not None for m in (SsSnag, SsSafety, SsPour, SsProgress, SsMaterial))
            if not ok:
                sn = s.scalars(select(SsSnag).where(SsSnag.tenant_id == tenant, SsSnag.number == str(ref).upper())).first()
                if sn is None:
                    raise SiteError("Photo kis cheez ki? (snag / ghatna / pour ka number)")
                ref = sn.id
            if stage == "fixed":
                sn = s.get(SsSnag, ref)
                if sn is not None and sn.status == "open":
                    sn.status = "fixed"
        n = len(s.scalars(select(SsPhoto.id).where(SsPhoto.site_id == st.id)).all())
        if n >= 2000:
            raise SiteError("Is site par 2000 photo ho gayi.")
        pid = new_id("ph")
        path = _dir(tenant, st.id) / f"{pid}.jpg"
        path.write_bytes(clean)
        s.add(SsPhoto(id=pid, tenant_id=tenant, site_id=st.id, ref=ref, stage=stage, day=today(tenant).isoformat(), path=str(path), note=_clean(note, 200)))
    return {"photo": pid, "bytes": len(clean), "say": "Photo jodi (location / camera ki jaankari hata di)."}


def photo_bytes(tenant: str, photo_id: str) -> bytes:
    with session() as s:
        p = s.get(SsPhoto, photo_id)
        if p is None or p.tenant_id != tenant:
            raise SiteError("Photo nahi mili.")
        path = p.path
    try:
        return Path(path).read_bytes()
    except OSError:
        raise SiteError("Photo file nahi mili.")


# ---------------------------------------------------------------- DPR + client messages (HER tap)
def dpr_data(tenant: str, site: str = "", day: str = "", weather: str = "", tomorrow: str = "", remarks: str = "") -> dict:
    d = _date(day, today(tenant))
    sv = site_view(tenant, site)
    acts = activities(tenant, sv["id"], d)
    with session() as s:
        prog = s.scalars(select(SsProgress).where(SsProgress.site_id == sv["id"], SsProgress.day == d.isoformat())).all()
        name_of = {a["id"]: a for a in acts}
        work = [{"activity": name_of.get(p.activity_id, {}).get("name", ""), "qty": p.qty, "unit": name_of.get(p.activity_id, {}).get("unit", ""),
                 "note": p.note} for p in prog if p.qty or p.note]
        hind = [{"activity": name_of.get(p.activity_id, {}).get("name", ""), "reason": p.delay, "client_side": p.by_client, "hours": p.lost_hours}
                for p in prog if p.delay]
        mat_today = [{"item": m.item, "qty": abs(m.qty), "unit": m.unit, "kind": m.kind, "challan": m.challan, "supplier": m.supplier, "ok": m.ok}
                     for m in s.scalars(select(SsMaterial).where(SsMaterial.site_id == sv["id"], SsMaterial.day == d.isoformat())).all()]
        safety = [r for r in s.scalars(select(SsSafety).where(SsSafety.site_id == sv["id"], SsSafety.day == d.isoformat())).all()]
        talks = [{"topic": r.text, "people": r.people} for r in safety if r.kind == "talk"]
        checks = [{"label": _j(r.data, {}).get("label", r.sub), "score": _j(r.data, {}).get("score")} for r in safety if r.kind == "check"]
        incs = [_incident_view(r) for r in safety if r.kind == "incident"]
        pours_ = [{"number": p.number, "element": p.element, "grade": p.grade, "volume": p.volume, "cubes": p.samples * 3}
                  for p in s.scalars(select(SsPour).where(SsPour.site_id == sv["id"], SsPour.day == d.isoformat())).all()]
        cube_res = []
        for c in s.scalars(select(SsCube).where(SsCube.tenant_id == tenant, SsCube.tested_on == d.isoformat(), SsCube.verdict != "")).all():
            p = s.get(SsPour, c.pour_id)
            if p and p.site_id == sv["id"]:
                rr = _j(c.results, [])
                cube_res.append({"pour": p.number, "element": p.element, "age": c.age, "mean": round(sum(rr) / len(rr), 2) if rr else None,
                                 "verdict": c.verdict})
        snag_open = len(s.scalars(select(SsSnag.id).where(SsSnag.site_id == sv["id"], SsSnag.status != "verified")).all())
        snag_new = len(s.scalars(select(SsSnag.id).where(SsSnag.site_id == sv["id"], SsSnag.day == d.isoformat())).all())
        photos = [p.path for p in s.scalars(select(SsPhoto).where(SsPhoto.site_id == sv["id"], SsPhoto.day == d.isoformat())).all()][:4]
        cfg = _st(s, tenant)
        firm = cfg.firm
    lab = labour_day(tenant, sv["id"], d.isoformat())
    bal = material_balance(tenant, sv["id"])
    behind = [a for a in acts if a["state"] in ("behind", "late")]
    return {"site": sv["name"], "client": sv["client"], "day": d.isoformat(), "firm": firm, "weather": _clean(weather, 120),
            "tomorrow": _clean(tomorrow, 500), "remarks": _clean(remarks, 500), "work": work, "hindrances": hind, "labour": lab,
            "material_today": mat_today, "balance": bal, "talks": talks, "checks": checks, "incidents": incs, "pours": pours_, "cubes": cube_res,
            "snags": {"open": snag_open, "new": snag_new}, "behind": [{"name": a["name"], "planned_pct": a["planned_pct"], "done_pct": a["done_pct"],
                                                                     "late_days": a["late_days"]} for a in behind],
            "progress": [{"name": a["name"], "done_pct": a["done_pct"], "planned_pct": a["planned_pct"]} for a in acts if a["qty"]],
            "stopped": sv["status"] == "stopped", "photos": photos}


def dpr_text(d: dict) -> str:
    dt = date.fromisoformat(d["day"]).strftime("%d %b %Y")
    L = [f"*Daily Progress Report - {d['site']}*", f"{dt}" + (f" | Mausam: {d['weather']}" if d["weather"] else "")]
    if d["stopped"]:
        L.append("Site par stop-work laagu hai.")
    L.append(f"Manpower: {d['labour']['total']}" + (" (" + ", ".join(f"{c['contractor']} {c['people']}" for c in d["labour"]["contractors"]) + ")"
                                                    if d["labour"]["contractors"] else ""))
    if d["work"]:
        L.append("Aaj ka kaam:")
        L += [f"- {w['activity']}: {_g(w['qty'])} {w['unit']}".rstrip() + (f" ({w['note']})" if w["note"] else "") for w in d["work"]]
    else:
        L.append("Aaj ka kaam: likha nahi gaya.")
    if d["pours"]:
        L += [f"- Concrete {p['element']} {p['grade']} {_g(p['volume'])} cum, {p['cubes']} cube liye" for p in d["pours"]]
    if d["material_today"]:
        L.append("Material: " + "; ".join(f"{m['item']} {_g(m['qty'])} {m['unit']} {'aaya' if m['kind'] == 'in' else 'laga'}" for m in d["material_today"]))
    if d["hindrances"]:
        L.append("Rukawat: " + "; ".join(f"{h['activity']}: {h['reason']}" for h in d["hindrances"]))
    if d["behind"]:
        L.append("Plan se peeche: " + "; ".join(f"{b['name']} ({b['done_pct']:g}% / plan {b['planned_pct']:g}%)" for b in d["behind"][:5]))
    if d["talks"] or d["checks"] or d["incidents"]:
        L.append("Safety: " + "; ".join([f"toolbox '{t['topic']}' {t['people']} log" for t in d["talks"]]
                                         + [f"{c['label']} {c['score']}%" for c in d["checks"]]
                                         + [f"{i['label']}" for i in d["incidents"]]))
    if d["cubes"]:
        L.append("Cube test: " + "; ".join(f"{c['pour']} {c['age']} din {c['mean']} N/mm2 ({c['verdict']})" for c in d["cubes"]))
    if d["snags"]["new"] or d["snags"]["open"]:
        L.append(f"Snag: {d['snags']['new']} naye, {d['snags']['open']} khule")
    if d["tomorrow"]:
        L.append(f"Kal: {d['tomorrow']}")
    if d["remarks"]:
        L.append(d["remarks"])
    if d["firm"]:
        L.append(f"- {d['firm']}")
    return "\n".join(L)


def _pdf_safe(t: str) -> str:
    return str(t).replace("₹", "Rs ").replace("*", "").encode("latin-1", "replace").decode("latin-1")


def dpr_pdf(d: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    bio = io.BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    w, h = A4
    y = h - 50

    def line(t: str, size: int = 10, bold: bool = False, gap: int = 14):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        for part in [t[i:i + 100] for i in range(0, max(1, len(t)), 100)]:
            if y < 60:
                c.showPage()
                y = h - 50
                c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
            c.drawString(40, y, _pdf_safe(part))
            y -= gap

    line(f"DAILY PROGRESS REPORT - {d['site']}", 14, True, 20)
    line(f"Date: {d['day']}   Client: {d['client'] or '-'}   Weather: {d['weather'] or '-'}")
    if d["firm"]:
        line(f"By: {d['firm']}")
    y -= 6
    for row in dpr_text(d).split("\n")[2:]:
        line(row, 10, row.endswith(":"))
    if d["progress"]:
        y -= 6
        line("Overall progress (activity: done % / planned %)", 11, True)
        for p in d["progress"][:30]:
            line(f"  {p['name'][:60]}: {p['done_pct']:g}% / {p['planned_pct'] if p['planned_pct'] is not None else '-'}%")
    if d["balance"]:
        y -= 6
        line("Material balance at site", 11, True)
        for b in d["balance"][:30]:
            line(f"  {b['item']}: {_g(b['balance'])} {b['unit']} (aaya {_g(b['received'])}, laga {_g(b['used'])})")
    x = 40
    for pth in d.get("photos", [])[:4]:
        try:
            if y < 200:
                c.showPage()
                y = h - 50
            c.drawImage(ImageReader(pth), x, y - 140, width=120, height=130, preserveAspectRatio=True)
            x += 130
        except Exception:
            continue
    c.setFont("Helvetica", 7)
    c.drawString(40, 30, "Prepared by Hoola from site entries. Quantities as recorded at site; certified measurement as per the measurement book.")
    c.save()
    return bio.getvalue()


def _report_show(r: SsReport) -> dict:
    return {"number": r.number, "kind": r.kind, "day": r.day, "text": r.text, "file_id": r.file_id, "to_phone": r.to_phone}


def _report_view(r: SsReport, site_name: str = "") -> dict:
    v = {"id": r.id, **_report_show(r), "site": site_name, "status": r.status, "hash": r.hash, "via": r.via}
    if r.status == "approved" and r.to_phone:
        v["wa"] = f"https://wa.me/91{r.to_phone}?text={quote(r.text)}"
    return v


def dpr_request(tenant: str, site: str = "", day: str = "", weather: str = "", tomorrow: str = "", remarks: str = "", to_phone: str = "",
                actor: str = "owner", conv: str = "") -> dict:
    """Build the DPR (text + PDF) and send her the card. Nothing reaches the client until her tap (decide_report by_tap=True)."""
    from .. import chatfiles
    d = dpr_data(tenant, site, day, weather, tomorrow, remarks)
    if not d["work"] and not d["labour"]["total"] and not d["hindrances"] and not d["material_today"]:
        raise SiteError("Aaj ki site entry (kaam / hazri / material / rukawat) kuch nahi: DPR khaali hogi.")
    text = dpr_text(d)
    pdf = dpr_pdf(d)
    f = chatfiles.store(tenant, f"DPR_{re.sub(r'[^A-Za-z0-9]+', '_', d['site'])[:40]}_{d['day']}.pdf", pdf, "application/pdf")
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        ph = _phone(to_phone) or st.client_phone
        for old in s.scalars(select(SsReport).where(SsReport.site_id == st.id, SsReport.kind == "dpr", SsReport.day == d["day"],
                                                    SsReport.status == "waiting")).all():
            old.status = "stale"
        r = SsReport(tenant_id=tenant, site_id=st.id, kind="dpr", number=_next(s, tenant, "dpr", "DPR"), day=d["day"], data=_dump(d), text=text,
                     file_id=str(f.get("file_id") or f.get("id") or ""), to_phone=ph, status="waiting", conv=conv)
        s.add(r)
        s.flush()
        r.hash = _sha(_report_show(r), hashlib.sha256(pdf).hexdigest())
        v = _report_view(r, st.name)
    say = f"{v['number']} ({d['site']}, {d['day']}) taiyaar - client ko bhejne ke liye aapki haan ka card bheja hai." + \
        ("" if v["to_phone"] else " Client ka phone nahi: site mein jodiye ya PDF khud bhejiye.")
    _publish(tenant, "sitesup_report", {"report": v, "file": f, "say": say}, conv)
    return {"report": v, "file": f, "status": "needs_tap", "say": say}


def message_request(tenant: str, site: str = "", text: str = "", to_phone: str = "", conv: str = "") -> dict:
    """Any other message to the client (delay, drawing needed, visit): a draft card; only her tap lets it go."""
    t = str(text or "").strip()
    if not t:
        raise SiteError("Client ko kya likhna hai?")
    from ..net import policy
    if policy.secret_found(t):
        raise SiteError("Isme OTP / PIN / card jaisi baat hai.")
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        r = SsReport(tenant_id=tenant, site_id=st.id, kind="message", number=_next(s, tenant, "msg", "MSG"), day=today(tenant).isoformat(),
                     text=t[:1500], to_phone=_phone(to_phone) or st.client_phone, status="waiting", conv=conv)
        s.add(r)
        s.flush()
        r.hash = _sha(_report_show(r))
        v = _report_view(r, st.name)
    say = f"{v['number']}: client ke liye message ka draft - aapki haan ke card par."
    _publish(tenant, "sitesup_report", {"report": v, "say": say}, conv)
    return {"report": v, "status": "needs_tap", "say": say}


async def decide_report(tenant: str, report_id: str, yes: bool, card_hash: str = "", via: str = "self", by_tap: bool = False) -> dict:
    """ONLY her tap. yes + via=self -> approved: wa.me link she sends from her own WhatsApp (then 'Maine bhej diya').
    via=business -> the business WhatsApp (official Cloud API), only to a client who has written to that number (Meta 24 h window)."""
    if not by_tap:
        raise SiteError("Client ko report / message sirf aapke tap se jaata hai.")
    with session() as s:
        r = s.get(SsReport, report_id)
        if r is None or r.tenant_id != tenant:
            raise SiteError("Report nahi mili.")
        st = s.get(SsSite, r.site_id)
        if r.status != "waiting":
            return {"report": _report_view(r, st.name), "say": f"{r.number} pehle hi '{r.status}' hai."}
        if not card_hash or card_hash != r.hash:
            raise SiteError("Card badal gaya / purana hai; naya card dekhiye.")
        text, phone, sname = r.text, r.to_phone, st.name
    if re.search(r"\[[^\]]*\]|__________", text):
        raise SiteError("Report mein khaali jagah baaki hai: pehle bhariye.")
    if not yes:
        with session() as s:
            r = s.get(SsReport, report_id)
            r.status = "rejected"
            return {"report": _report_view(r, sname), "say": f"{r.number}: nahi bheja (aapka faisla)."}
    if via == "business":
        from ..employee import inbox
        from ..employee.models import BizContact
        if not phone:
            raise SiteError("Client ka phone nahi.")
        with session() as s:
            c = s.scalars(select(BizContact).where(BizContact.tenant_id == tenant, BizContact.wa_id.in_((phone, "91" + phone)))).first()
            cid = c.id if c else ""
        if not cid:
            raise SiteError("Client ne business WhatsApp par kabhi message nahi kiya: apne WhatsApp se (wa.me) bhejiye.")
        try:
            await inbox.send(tenant, cid, text, by="owner")
        except inbox.InboxError as e:
            raise SiteError(str(e))
        with session() as s:
            r = s.get(SsReport, report_id)
            r.status, r.via = "sent", "business"
            return {"report": _report_view(r, sname), "say": f"{r.number} business WhatsApp se client ko bheja. PDF bhi chahiye to file share kijiye."}
    with session() as s:
        r = s.get(SsReport, report_id)
        r.status = "approved"
        v = _report_view(r, sname)
    return {"report": v, "say": f"{v['number']} maana. 'WhatsApp kholo' se apne phone se bhejiye (PDF bhi share kar sakti hain), phir 'Maine bhej diya'."}


def report_sent(tenant: str, report_id: str) -> dict:
    with session() as s:
        r = s.get(SsReport, report_id)
        if r is None or r.tenant_id != tenant:
            raise SiteError("Report nahi mili.")
        if r.status != "approved":
            raise SiteError(f"{r.number} abhi '{r.status}' hai: pehle aapki haan.")
        r.status, r.via = "sent", "self"
        st = s.get(SsSite, r.site_id)
        return {"report": _report_view(r, st.name if st else ""), "say": "Bheja likha."}


def reports(tenant: str, site: str = "", status: str = "") -> list[dict]:
    with session() as s:
        q = select(SsReport).where(SsReport.tenant_id == tenant)
        if site:
            q = q.where(SsReport.site_id == _site(s, tenant, site).id)
        if status:
            q = q.where(SsReport.status == status)
        out = []
        for r in s.scalars(q.order_by(SsReport.created_at.desc())).all()[:60]:
            st = s.get(SsSite, r.site_id)
            out.append(_report_view(r, st.name if st else ""))
        return out


# ---------------------------------------------------------------- day, register file, forget, tick
def day(tenant: str) -> dict:
    on = today(tenant)
    parts = []
    with session() as s:
        run = s.scalars(select(SsSite).where(SsSite.tenant_id == tenant, SsSite.status.in_(("running", "stopped")))).all()
        site_ids = [(x.id, x.name, x.status) for x in run]
        inc = s.scalars(select(SsSafety).where(SsSafety.tenant_id == tenant, SsSafety.kind == "incident", SsSafety.reported == "",
                                               SsSafety.due_at.is_not(None))).all()
        inc_v = [_incident_view(r) for r in inc]
        waiting = len(s.scalars(select(SsIndent.id).where(SsIndent.tenant_id == tenant, SsIndent.status == "waiting")).all())
        stops_w = len(s.scalars(select(SsStop.id).where(SsStop.tenant_id == tenant, SsStop.status == "waiting")).all())
        reps_w = len(s.scalars(select(SsReport.id).where(SsReport.tenant_id == tenant, SsReport.status == "waiting")).all())
        cure = s.scalars(select(SsPour).where(SsPour.tenant_id == tenant, SsPour.curing_until >= on.isoformat())).all()
        curing = [f"{p.number} {p.element}" for p in cure]
    for i in inc_v:
        parts.append(f"{i['number']} ka notice abhi tak nahi bheja" + (" - DER HO GAYI" if i["overdue"] else f" (aakhri ghadi {i['due_local']})"))
    for sid, nm, stt in site_ids:
        if stt == "stopped":
            parts.append(f"{nm}: stop-work laagu")
        la = lookahead(tenant, sid, 7)
        if la["behind"] or any(a["short"] for a in la["coming"]):
            parts.append(f"{nm}: {la['say']}")
    cd = cubes_due(tenant, 0)
    if cd:
        parts.append("Aaj cube test: " + ", ".join(f"{c['pour']} {c['age']} din" + (f" ({c['late_days']} din late)" if c["late_days"] else "") for c in cd[:6]))
    if curing:
        parts.append("Curing chalu: " + ", ".join(curing[:6]))
    if waiting:
        parts.append(f"{waiting} indent aapki haan ke intezaar mein")
    if stops_w:
        parts.append(f"{stops_w} stop-work card aapki haan ke intezaar mein")
    if reps_w:
        parts.append(f"{reps_w} report / message client ke liye aapki haan ke intezaar mein")
    parts.append(f"Aaj ka toolbox talk vishay: {R.TOOLBOX_TOPICS[on.toordinal() % len(R.TOOLBOX_TOPICS)]}")
    return {"parts": parts, "say": "; ".join(parts) + "."}


def overview(tenant: str) -> dict:
    out = {"settings": settings(tenant), "sites": sites(tenant), "indents": indents(tenant, "waiting"), "stops": stops(tenant),
           "reports": reports(tenant)[:20], "cubes_due": cubes_due(tenant, 3), "rules": list(R.NEVER),
           "checklists": {k: {"label": v["label"], "items": [{"id": i, "q": q, "critical": c} for i, q, c in v["items"]]} for k, v in R.CHECKLISTS.items()},
           "topics": list(R.TOOLBOX_TOPICS), "incident_kinds": R.INCIDENT_KINDS}
    try:
        out["day"] = day(tenant)
    except Exception:
        out["day"] = {"parts": [], "say": ""}
    return out


def register_file(tenant: str, site: str = "", start: str = "", end: str = "", conv: str = "") -> dict:
    import openpyxl
    from .. import chatfiles
    reg = register(tenant, site, start, end)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Labour register"
    ws.append(["Contractor", "Trade", "Days worked", "Man-days", "Normal hours", "OT hours (2x)", "Her rate / day", "Estimate (check only)"])
    for x in reg["lines"]:
        ws.append([x["contractor"], x["label"], x["days_worked"], x["man_days"], x["normal_hours"], x["ot_hours"], x["rate"], x["estimate"]])
    ws2 = wb.create_sheet("Workers")
    ws2.append(["Worker", "Contractor", "Trade", "Days", "Hours", "OT hours"])
    for w in reg["workers"]:
        ws2.append([w["worker"], w["contractor"], R.TRADE_LABEL.get(w["trade"], w["trade"]), w["days"], w["hours"], w["ot"]])
    ws3 = wb.create_sheet("Material")
    ws3.append(["Item", "Unit", "Received", "Used", "Returned", "Waste", "Balance"])
    for b in material_balance(tenant, site):
        ws3.append([b["item"], b["unit"], b["received"], b["used"], b["returned"], b["waste"], b["balance"]])
    ws4 = wb.create_sheet("Safety")
    ws4.append(["Day", "Type", "What", "People / score", "Report due", "Reported"])
    for r in safety_log(tenant, site, "", 120):
        if r["type"] == "incident":
            ws4.append([r["day"], r["label"], r["text"], r["people"], r["due_at"], r["reported"]])
        elif r["type"] == "check":
            ws4.append([r["day"], "Checklist " + r["label"], r["area"], r["score"], "", ""])
        else:
            ws4.append([r["day"], "Toolbox talk", r["topic"], r["people"], "", ""])
    bio = io.BytesIO()
    wb.save(bio)
    f = chatfiles.store(tenant, f"Site_register_{reg['from']}_{reg['to']}.xlsx", bio.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "sitesup", "title": "Site register"}, conv)
    return {"file": f, "say": f"{reg['site']}: hazri / overtime / material / safety register Excel mein."}


def forget(tenant: str, site: str) -> dict:
    """DPDP: after a site is done, workers' names and ID references and incident names are blanked; counts stay."""
    with _LOCK, session() as s:
        st = _site(s, tenant, site)
        if st.status not in ("done", "closed"):
            raise SiteError("Site abhi chalu hai: kaam khatam (done) hone ke baad hi bhoolna.")
        n = 0
        for r in s.scalars(select(SsLabour).where(SsLabour.site_id == st.id, SsLabour.worker != "")).all():
            r.worker, r.id_ref = f"worker-{r.id[-4:]}", ""
            n += 1
        for r in s.scalars(select(SsSafety).where(SsSafety.site_id == st.id, SsSafety.kind == "incident")).all():
            d = _j(r.data, {})
            d["names"] = ""
            r.data = _dump(d)
        st.client_phone, st.client_email = "", ""
        sname = st.name
    return {"forgot": n, "say": f"{sname}: mazdooron ke naam / ID reference aur client ka contact hata diye; ginti aur register bache hain."}


def _tenants() -> list[str]:
    with session() as s:
        return sorted(set(s.scalars(select(SsSite.tenant_id).where(SsSite.status.in_(("running", "stopped")))).all()))


def _due_time(loc: datetime, hhmm: str) -> bool:
    try:
        hh, mm = (int(x) for x in (hhmm or "08:00").split(":"))
    except ValueError:
        hh, mm = 8, 0
    return (loc.hour, loc.minute) >= (hh, mm)


def tick(now_: datetime | None = None) -> dict:
    """Worker, every minute: cube tests due (tomorrow + today, once each), overdue results, Form XI deadlines (2 h before and when
    passed), curing ends, the morning note at her time, an evening DPR nudge at her dpr_time when the site has entries but no DPR."""
    n = _aware(now_) or datetime.now(timezone.utc)
    out = {"alerts": 0, "morning": 0, "dpr": 0}
    for tenant in _tenants():
        try:
            loc = n.astimezone(_tz(tenant))
            on = loc.date()
            alerts = []
            with _LOCK, session() as s:
                for c in s.scalars(select(SsCube).where(SsCube.tenant_id == tenant, SsCube.verdict == "",
                                                        SsCube.due <= (on + timedelta(days=1)).isoformat())).all():
                    p = s.get(SsPour, c.pour_id)
                    st = s.get(SsSite, p.site_id) if p else None
                    if not p or not st:
                        continue
                    due = date.fromisoformat(c.due)
                    stage = "tomorrow" if due > on else ("today" if due == on else ("late" if (on - due).days >= 1 else ""))
                    if stage and c.sample == 1 and _once(s, tenant, f"cube:{p.id}:{c.age}:{stage}"):
                        say = {"tomorrow": f"Kal {p.number} ({p.element}, {p.grade}) ke {c.age} din wale cube test hain: lab / CTM tayyar rakhiye.",
                               "today": f"Aaj {p.number} ({p.element}) ke {c.age} din wale cube test: result aane par 'cube' mein likhiye.",
                               "late": f"{p.number} ({p.element}) ke {c.age} din wale cube ka result abhi tak nahi aaya."}[stage]
                        alerts.append({"kind": "cube", "site": st.name, "say": say})
                    if p.curing_until == on.isoformat() and _once(s, tenant, f"cure:{p.id}"):
                        alerts.append({"kind": "curing", "site": st.name, "say": f"{p.number} ({p.element}) ki curing aaj poori: {p.cement or 'cement'} ke hisaab se."})
                for r in s.scalars(select(SsSafety).where(SsSafety.tenant_id == tenant, SsSafety.kind == "incident", SsSafety.reported == "",
                                                          SsSafety.due_at.is_not(None))).all():
                    due = _aware(r.due_at)
                    if due - timedelta(hours=2) <= n < due and _once(s, tenant, f"inc:{r.id}:soon"):
                        alerts.append({"kind": "incident", "say": f"{r.number}: Form XI notice ki aakhri ghadi 2 ghante se kam mein. Bhej diya to 'reported' likhiye."})
                    elif n >= due and _once(s, tenant, f"inc:{r.id}:late"):
                        alerts.append({"kind": "incident", "say": f"{r.number}: notice ka samay nikal gaya - abhi bhejiye aur der ki wajah likhiye."})
                cfg = _st(s, tenant)
                morning = cfg.last_morning != on.isoformat() and _due_time(loc, cfg.morning_time)
                if morning:
                    cfg.last_morning = on.isoformat()
                nudge = cfg.last_dpr_nudge != on.isoformat() and _due_time(loc, cfg.dpr_time)
                if nudge:
                    cfg.last_dpr_nudge = on.isoformat()
                todo_dpr = []
                if nudge:
                    for st in s.scalars(select(SsSite).where(SsSite.tenant_id == tenant, SsSite.status.in_(("running", "stopped")))).all():
                        has = s.scalars(select(SsProgress.id).where(SsProgress.site_id == st.id, SsProgress.day == on.isoformat())).first() or \
                            s.scalars(select(SsLabour.id).where(SsLabour.site_id == st.id, SsLabour.day == on.isoformat())).first()
                        done = s.scalars(select(SsReport.id).where(SsReport.site_id == st.id, SsReport.kind == "dpr", SsReport.day == on.isoformat())).first()
                        if has and not done:
                            todo_dpr.append(st.name)
            for a in alerts:
                out["alerts"] += 1
                _publish(tenant, "sitesup_alert", a)
            if morning:
                d = day(tenant)
                _publish(tenant, "sitesup_day", {"say": d["say"], "parts": d["parts"]})
                out["morning"] += 1
            if todo_dpr:
                _publish(tenant, "sitesup_alert", {"kind": "dpr", "say": "Aaj ki DPR baaki: " + ", ".join(todo_dpr) + ". 'DPR banao' boliye; client ko aapki haan se hi jayegi."})
                out["dpr"] += 1
        except Exception:
            log.exception("sitesup tick failed for %s", tenant)
    return out
