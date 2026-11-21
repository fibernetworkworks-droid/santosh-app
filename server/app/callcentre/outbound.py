"""v0.999.67 AI TELECALLER - Hoola makes and speaks every call (owner: "WE DONT WANT HUMAN TO CALL ANY MORE --- EVERY CALL
TO BE GENERATED AND TALK BY AI ONLY ON HUMAN PROVIDED DATA"; Dograh's outbound campaigns as the model, ideas only).

A CALL LIST (campaign) = HER people (her sheet, her Telecaller leads, her Lead Generation leads, her customers) + HER
approved script + hours + how many calls at once + tries + a money cap a day. Hoola calls ONLY the people in it.

Gates, in code, before every single call (`gate`):
- the list was started by HER tap on the start card, bound to its hash (people, script version, hours, cap);
- the country pack of the number (countries.py): the person's own local calling hours (their time zone), the consent the
  country needs - a person who never asked to be called (cold) is called only in India from her registered 140 / 1600
  line, and in a country whose pack Hoola has not verified only after she confirmed she checked the law there;
- anyone who said "don't call me" (on any list, on the Telecaller, or by the do-not-call tool on a call) never again;
- tries per person, the gap between tries, the calls-at-once limit, the money cap of the day.

On the call: the first sentence says it is an AI calling for her business and why; the line speaks only from her
approved script + her approved business knowledge (knowledge.py) and the live lookups she approved; an answering
machine (the provider's own check) gets her short voicemail and a later try; results go back into the person's row
(the fields she asked for), her Telecaller lead (stage, next call), and her chat when something needs HER.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from ..db import now, session
from . import countries as CO
from . import providers as P
from . import rules as R
from .models import CcCall, CcCampaign, CcTarget

log = logging.getLogger("santosh.callcentre")

PURPOSES = ("sales", "followup", "renewal", "dues", "appointment", "feedback", "reminder", "survey", "service")
BASES = ("asked", "customer", "cold", "unknown")
RETRYABLE = {"no_answer", "busy", "failed", "voicemail"}
MAX_PEOPLE = 20000
DIAL_PER_TICK = 6


class OutError(Exception):
    pass


def _j(v, default):
    try:
        return json.loads(v) if v else default
    except ValueError:
        return default


def _S():
    from . import service as S
    return S


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- the list
def _view(c: CcCampaign, counts: dict[str, int] | None = None) -> dict[str, Any]:
    return {"id": c.id, "name": c.name, "goal": c.goal, "purpose": c.purpose, "status": c.status, "country": c.country,
            "basis": c.basis, "hours": f"{c.start_hour}-{c.end_hour}", "at_once": c.at_once, "max_tries": c.max_tries,
            "retry_min": c.retry_min, "daily_cap": c.daily_cap, "voicemail": c.voicemail, "fields": _j(c.fields, []),
            "started_at": c.started_at.isoformat() if c.started_at else None, "people": counts or {}}


def _get(s, tenant: str, cid: str) -> CcCampaign:
    c = s.get(CcCampaign, cid)
    if c is None or c.tenant_id != tenant:
        raise OutError("No such call list.")
    return c


def _counts(s, cid: str) -> dict[str, int]:
    rows = s.execute(select(CcTarget.status, func.count()).where(CcTarget.campaign_id == cid).group_by(CcTarget.status)).all()
    out = {k: int(v) for k, v in rows}
    out["total"] = sum(out.values())
    return out


def create(tenant: str, name: str, goal: str = "", purpose: str = "sales", country: str = "", basis: str = "asked",
           start_hour: str = "", end_hour: str = "", at_once: int = 2, max_tries: int = 3, retry_min: int = 120,
           daily_cap: float = 0.0, voicemail: str = "", fields: list[Any] | None = None) -> dict[str, Any]:
    if not (name or "").strip():
        raise OutError("Give the call list a name.")
    if purpose not in PURPOSES:
        raise OutError("purpose = " + " | ".join(PURPOSES))
    if basis not in BASES[:3]:
        raise OutError("basis = asked (they asked to be called) | customer (your customers) | cold (they never asked)")
    S = _S()
    with session() as s:
        st = S._row(s, tenant)
        code = (country or st.country or "IN").upper()[:2]
        if code not in CO.PACKS:
            raise OutError("That country is not supported yet.")
        f = []
        for x in (fields or [])[:12]:
            if isinstance(x, str) and x.strip():
                f.append({"name": re.sub(r"\W+", "_", x.strip().lower())[:40], "ask": x.strip()[:200]})
            elif isinstance(x, dict) and x.get("name"):
                f.append({"name": re.sub(r"\W+", "_", str(x["name"]).strip().lower())[:40], "ask": str(x.get("ask") or x["name"])[:200]})
        c = CcCampaign(tenant_id=tenant, name=name.strip()[:120], goal=(goal or "").strip()[:500], purpose=purpose,
                       country=code, basis=basis, start_hour=S._hm(start_hour or "10:00"), end_hour=S._hm(end_hour or "19:00"),
                       at_once=max(1, min(10, int(at_once or 2))), max_tries=max(1, min(6, int(max_tries or 3))),
                       retry_min=max(15, min(10080, int(retry_min or 120))), daily_cap=max(0.0, float(daily_cap or 0)),
                       voicemail=(voicemail or "").strip()[:400], fields=json.dumps(f, ensure_ascii=False))
        s.add(c)
        s.flush()
        return _view(c, {"total": 0})


def update(tenant: str, cid: str, **kw) -> dict[str, Any]:
    """Change a list. A running list goes back to 'ready' (her tap again) when what she approved changes."""
    S = _S()
    with session() as s:
        c = _get(s, tenant, cid)
        for k in ("name", "goal", "voicemail"):
            if kw.get(k) is not None:
                setattr(c, k, str(kw[k]).strip()[:500])
        if kw.get("purpose") in PURPOSES:
            c.purpose = kw["purpose"]
        if kw.get("basis") in BASES[:3]:
            c.basis = kw["basis"]
        for k in ("start_hour", "end_hour"):
            if kw.get(k):
                setattr(c, k, S._hm(kw[k]))
        for k, lo, hi in (("at_once", 1, 10), ("max_tries", 1, 6), ("retry_min", 15, 10080)):
            if kw.get(k) is not None:
                setattr(c, k, max(lo, min(hi, int(kw[k]))))
        if kw.get("daily_cap") is not None:
            c.daily_cap = max(0.0, float(kw["daily_cap"]))
        if c.status == "running":
            c.status = "paused"
        return _view(c, _counts(s, cid)) | {"say": "Saved." + (" The list is paused until you start it again."
                                                               if c.status == "paused" else "")}


_COLS = {"name": ("name", "naam", "customer", "contact", "full name", "person"),
         "phone": ("phone", "mobile", "number", "contact no", "whatsapp", "tel", "cell"),
         "country": ("country", "country code"),
         "tz": ("timezone", "time zone", "tz"),
         "lang": ("language", "lang", "bhasha"),
         "basis": ("consent", "asked", "basis", "source")}


def _col(header: list[str], keys: tuple[str, ...]) -> str:
    low = {h.lower().strip(): h for h in header}
    for k in keys:
        if k in low:
            return low[k]
    for h in header:
        if any(k in h.lower() for k in keys):
            return h
    return ""


def _basis_of(v: Any, default: str) -> str:
    t = str(v or "").strip().lower()
    if not t:
        return default
    if t in ("yes", "y", "true", "1", "asked", "enquiry", "inquiry", "website", "form", "missed call", "opt-in", "opted in"):
        return "asked"
    if t in ("customer", "client", "existing", "member"):
        return "customer"
    if t in ("no", "n", "false", "0", "cold", "bought", "list", "scraped"):
        return "cold"
    return default


def _never(tenant: str) -> set[str]:
    """Every number she must never call: 'don't call' on any list, and her Telecaller DND list."""
    out: set[str] = set()
    with session() as s:
        for (ph,) in s.execute(select(CcTarget.phone).where(CcTarget.tenant_id == tenant, CcTarget.status == "dnd")).all():
            out.add(CO.digits(ph)[-10:])
        try:
            from ..telecall.service import TeleLead
            for (ph,) in s.execute(select(TeleLead.phone).where(TeleLead.tenant_id == tenant, TeleLead.stage == "dnd")).all():
                out.add(CO.digits(ph)[-10:])
        except Exception:      # noqa: BLE001 - the Telecaller tables may not exist on an old server
            pass
    return out


def add_people(tenant: str, cid: str, rows: list[dict[str, Any]] | None = None, file_id: str = "",
               lead_ids: list[str] | None = None, basis: str = "") -> dict[str, Any]:
    """People from HER data only: rows she gave, a sheet she sent (CSV / Excel), or her Telecaller leads."""
    from . import knowledge as K
    raw: list[dict[str, Any]] = []
    if file_id:
        from ..mailbox import service as ms
        try:
            fname, _m, data = ms.load_files(tenant, [{"type": "file", "file_id": file_id}])[0]
        except Exception as e:      # noqa: BLE001
            raise OutError(f"That file was not found ({e}).")
        raw = K._sheet_rows(fname, data)
    raw += [r for r in (rows or []) if isinstance(r, dict)]
    leads: dict[str, Any] = {}
    if lead_ids:
        from ..telecall.service import TeleLead
        with session() as s:
            for lead in s.scalars(select(TeleLead).where(TeleLead.tenant_id == tenant, TeleLead.id.in_(lead_ids[:MAX_PEOPLE]))).all():
                b = "asked" if lead.consent or lead.source in ("enquiry", "website", "missed_call", "whatsapp", "referral",
                                                               "ads_form", "walk_in") else (
                    "customer" if lead.source == "customer" else ("cold" if lead.consent is False or lead.source in
                                                                    ("bought", "cold", "list") else "unknown"))
                raw.append({"name": lead.name, "phone": lead.phone, "need": lead.need, "city": lead.city,
                            "language": lead.language, "_basis": b, "_lead": lead.id})
    if not raw:
        raise OutError("Give the people to call: a sheet (file_id), rows, or Telecaller lead ids.")
    header = list({k for r in raw for k in r.keys() if not str(k).startswith("_")})
    col = {f: _col(header, keys) for f, keys in _COLS.items()}
    if not col["phone"]:
        raise OutError("No phone column found. Columns seen: " + ", ".join(header[:12]) + ".")
    never = _never(tenant)
    added = skipped = dup = 0
    reasons: dict[str, int] = {}
    with session() as s:
        c = _get(s, tenant, cid)
        have = {CO.digits(p) for (p,) in s.execute(select(CcTarget.phone).where(CcTarget.campaign_id == cid)).all()}
        if len(have) + len(raw) > MAX_PEOPLE:
            raise OutError(f"A call list holds up to {MAX_PEOPLE} people.")
        for r in raw:
            country = str(r.get(col["country"]) or "").strip().upper()[:2] if col["country"] else ""
            ph = CO.e164(r.get(col["phone"]), country if country in CO.PACKS else c.country)
            why = ""
            if not ph:
                why = "not a phone number"
            elif CO.digits(ph) in have:      # the whole number: two countries can share the last 10 digits
                dup += 1
                continue
            elif CO.digits(ph)[-10:] in never:
                why = "said do not call"
            code = CO.country_of(ph) if ph else ""
            if code == "US" and (c.country == "CA" or country == "CA"):
                code = "CA"
            tz = CO.tz_of(code, str(r.get(col["tz"]) or "").strip() if col["tz"] else "", ph)
            b = r.get("_basis") or _basis_of(r.get(col["basis"]) if col["basis"] else "", basis or c.basis)
            data = {k: str(v)[:300] for k, v in r.items() if not str(k).startswith("_") and k not in (col["phone"],)
                    and v not in (None, "")}
            t = CcTarget(tenant_id=tenant, campaign_id=cid, name=str(r.get(col["name"]) or "")[:120] if col["name"] else "",
                         phone=ph[:20], country=code, tz=tz, lang=(str(r.get(col["lang"]) or "")[:8] if col["lang"] else "") or _lang_for(code, c.country),
                         basis=b, data=json.dumps(data, ensure_ascii=False)[:4000], lead_id=str(r.get("_lead") or ""))
            if why:
                t.status, t.why = ("dnd" if why == "said do not call" else "skipped"), why
                skipped += 1
                reasons[why] = reasons.get(why, 0) + 1
            else:
                added += 1
            if ph:
                have.add(CO.digits(ph))
            s.add(t)
        if c.status == "running":
            c.status = "paused"
        counts = _counts(s, cid)
    return {"added": added, "skipped": skipped, "duplicates": dup, "why_skipped": reasons, "people": counts,
            "say": f"{added} people added" + (f", {skipped} left out" if skipped else "") + (f", {dup} already on the list" if dup else "")
                   + ". Hoola calls only after you tap Start on the list."}


# ---------------------------------------------------------------- the checks before a call
def _ready_problems(tenant: str) -> list[str]:
    S = _S()
    out = []
    st = S.settings(tenant)
    prov = P.KINDS.get(st["provider"])
    if prov is None or not prov.outbound:
        out.append(f"{st['provider']} cannot place calls")
    if not st["creds_set"] and st["provider"] != "plivo":
        out.append("the phone provider's keys are not entered (Settings > Phone line)")
    if not st["number"]:
        out.append("no number to call from (Settings > Phone line)")
    if not st.get("urls"):
        out.append("PUBLIC_BASE_URL is not set on the server")
    if S.approved(tenant) is None:
        out.append("no approved call script yet")
    return out


def _lang_for(code: str, home: str) -> str:
    """v0.999.73 a person abroad is called in their country's language when the list names none; at home the script's
    own language decides ('' here)."""
    if not code or code == (home or "").upper():
        return ""
    return CO.lang_of(code)


def gate(tenant: str, t: CcTarget, c: CcCampaign, st: dict[str, Any], at: datetime | None = None) -> tuple[bool, str, bool]:
    """(may call now, why not, is it only 'not now' - a later time can work)."""
    if t.status in ("dnd", "done", "skipped"):
        return False, t.why or t.status, False
    if t.tries >= c.max_tries:
        return False, "no more tries", False
    ok, why = CO.basis_ok(t.country, t.basis, bool(st.get("registered_line")), t.country in (st.get("confirmed_countries") or []))
    if not ok:
        return False, why, False
    ok, why = CO.can_call_now(t.country, t.tz, c.start_hour, c.end_hour, at)
    if not ok:
        return False, why, "time zone" not in why
    return True, "", True


def start_card(tenant: str, cid: str) -> dict[str, Any]:
    """What she approves: who can be called, who is held and why, the hours, the script, the cost. -> a card + hash."""
    S = _S()
    st = S.settings(tenant)
    with session() as s:
        c = _get(s, tenant, cid)
        people = s.scalars(select(CcTarget).where(CcTarget.campaign_id == cid)).all()
        callable_, held = 0, {}
        countries: set[str] = set()
        for t in people:
            if t.status in ("dnd", "skipped", "done"):
                continue
            ok, why, later = gate(tenant, t, c, st, at=_probe_time(t))
            if ok or later:
                callable_ += 1
                countries.add(t.country)
            else:
                held[why] = held.get(why, 0) + 1
        sc = S.approved(tenant)
        view = _view(c, _counts(s, cid))
    problems = _ready_problems(tenant)
    if c.daily_cap <= 0:
        problems.append("set a money cap for each day")
    if not callable_:
        problems.append("nobody on this list can be called")
    est = cost_estimate(tenant, callable_)
    card = {"campaign_id": cid, "name": view["name"], "callable": callable_, "held": held, "hours": view["hours"],
            "countries": sorted(countries), "at_once": view["at_once"], "max_tries": view["max_tries"],
            "script_version": (sc or {}).get("version"), "script_hash": (sc or {}).get("hash", ""),
            "daily_cap": view["daily_cap"], "currency": st.get("currency"), "estimate": est, "problems": problems}
    card["hash"] = _hash(card)
    return card


def _probe_time(t: CcTarget) -> datetime:
    """A time inside the person's calling window (so 'held' means held for good, not 'it is night now')."""
    try:
        from zoneinfo import ZoneInfo
        if t.tz:
            local = datetime.now(ZoneInfo(t.tz)).replace(hour=12, minute=0, second=0, microsecond=0)
            while local.weekday() not in (CO.pack(t.country).get("days") or range(7)):
                local += timedelta(days=1)
            return local
    except Exception:      # noqa: BLE001
        pass
    return now()


def _hash(card: dict[str, Any]) -> str:
    keep = {k: card[k] for k in ("campaign_id", "callable", "hours", "at_once", "max_tries", "script_hash", "daily_cap", "countries")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:24]


def cost_estimate(tenant: str, people: int, minutes_each: float = 2.0) -> dict[str, Any]:
    from .. import usage
    from ..config import get_settings
    S = _S()
    st = S.settings(tenant)
    ai_min = usage.cost(get_settings().gemini_live_model, sec_in=60, sec_out=40)
    fx = _fx(st.get("currency") or "INR")
    phone = float(st.get("rate_per_min") or 0)
    per_min = phone + (ai_min * fx if fx else 0)
    return {"people": people, "minutes_each": minutes_each, "per_minute": round(per_min, 3), "ai_usd_per_minute": round(ai_min, 4),
            "total": round(per_min * minutes_each * people, 2), "currency": st.get("currency"),
            "note": ("" if fx else "The AI part is counted in US dollars and is not inside this number.")
                    + ("" if phone else " Your phone company's rate per minute is not entered yet (Settings), so it is not counted.")}


def _fx(cur: str) -> float | None:
    if cur == "USD":
        return 1.0
    if cur == "INR":
        from .. import usage
        return usage.usd_inr()
    return None


def start(tenant: str, cid: str, hash_: str, conv: str = "") -> dict[str, Any]:
    """HER tap on the start card. Nothing is dialled before this; a list that changed since she saw it is refused."""
    card = start_card(tenant, cid)
    if card["problems"]:
        raise OutError("Not ready: " + "; ".join(card["problems"]) + ".")
    if hash_ != card["hash"]:
        raise OutError("The list changed since you saw it; look at it again.")
    with session() as s:
        c = _get(s, tenant, cid)
        c.status, c.start_hash, c.started_at = "running", hash_, c.started_at or now()
        return _view(c, _counts(s, cid)) | {"say": f"Started. Hoola calls {card['callable']} people inside their calling hours."}


def set_status(tenant: str, cid: str, status: str) -> dict[str, Any]:
    if status not in ("paused", "stopped"):
        raise OutError("pause or stop (starting is your tap on the start card).")
    with session() as s:
        c = _get(s, tenant, cid)
        c.status = status
        return _view(c, _counts(s, cid))


def lists(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [_view(c, _counts(s, c.id)) for c in s.scalars(select(CcCampaign).where(CcCampaign.tenant_id == tenant)
                                                              .order_by(CcCampaign.created_at.desc())).all()]


def people(tenant: str, cid: str, status: str = "", limit: int = 200) -> list[dict[str, Any]]:
    with session() as s:
        _get(s, tenant, cid)
        q = select(CcTarget).where(CcTarget.campaign_id == cid)
        if status:
            q = q.where(CcTarget.status == status)
        return [_tview(t) for t in s.scalars(q.order_by(CcTarget.created_at).limit(limit)).all()]


def _tview(t: CcTarget) -> dict[str, Any]:
    return {"id": t.id, "name": t.name, "phone": R.mask_phone(t.phone), "country": t.country, "tz": t.tz, "basis": t.basis,
            "status": t.status, "tries": t.tries, "outcome": t.outcome, "result": _j(t.result, {}), "why": t.why,
            "next_at": _aware(t.next_at).isoformat() if t.next_at else None, "call_id": t.call_id}


# ---------------------------------------------------------------- dialling (worker)
def spent_today(tenant: str) -> float:
    S = _S()
    st = S.settings(tenant)
    fx = _fx(st.get("currency") or "INR")
    start_ = now() - timedelta(hours=24)
    with session() as s:
        rows = s.scalars(select(CcCall).where(CcCall.tenant_id == tenant, CcCall.direction == "out",
                                              CcCall.started_at >= start_)).all()
        return round(sum((c.phone_inr or 0) + ((c.ai_usd or 0) * fx if fx else 0) for c in rows), 2)


def _live_out(tenant: str, cid: str) -> int:
    with session() as s:
        return int(s.scalar(select(func.count()).select_from(CcCall).where(
            CcCall.campaign_id == cid, CcCall.status.in_(("ringing", "live")))) or 0)


def tick(limit: int = DIAL_PER_TICK) -> int:
    """Worker, every minute: call the next due people of every running list."""
    S = _S()
    placed = 0
    with session() as s:
        running = [(c.tenant_id, c.id) for c in s.scalars(select(CcCampaign).where(CcCampaign.status == "running")).all()]
    for tenant, cid in running:
        try:
            placed += _tick_one(S, tenant, cid, limit - placed)
        except Exception:      # noqa: BLE001 - one list failing never stops the others
            log.exception("outbound tick %s failed", cid)
        if placed >= limit:
            break
    return placed


def _tick_one(S, tenant: str, cid: str, room: int) -> int:
    st = S.settings(tenant)
    if _ready_problems(tenant):
        return 0
    with session() as s:
        c = _get(s, tenant, cid)
        cap, at_once = c.daily_cap, c.at_once
        left = s.scalar(select(func.count()).select_from(CcTarget).where(
            CcTarget.campaign_id == cid, CcTarget.status.in_(("queued", "retry", "calling")))) or 0
        if not left:
            c.status = "done"
            S.publish(tenant, "callcentre_campaign", _view(c, _counts(s, cid)) | {"say": f"{c.name}: every person was called."})
            return 0
    if spent_today(tenant) >= cap:
        return 0
    free = at_once - _live_out(tenant, cid)
    if free <= 0:
        return 0
    n = 0
    with session() as s:
        c = _get(s, tenant, cid)
        due = s.scalars(select(CcTarget).where(CcTarget.campaign_id == cid, CcTarget.status.in_(("queued", "retry")),
                                               (CcTarget.next_at.is_(None)) | (CcTarget.next_at <= now()))
                        .order_by(CcTarget.next_at.is_(None).desc(), CcTarget.next_at, CcTarget.created_at).limit(50)).all()
        picks = []
        for t in due:
            if len(picks) >= min(free, room):
                break
            ok, why, later = gate(tenant, t, c, st)
            if ok:
                picks.append(t.id)
            elif later:
                t.next_at, t.why = now() + timedelta(minutes=30), why
            elif why == "no more tries":
                t.status, t.why = "done", why
            else:      # held (consent / country / a time zone missing): it waits, and comes back when she fixes it
                t.next_at, t.why = now() + timedelta(hours=1), why
    for tid in picks:
        if _dial(S, tenant, cid, tid, st):
            n += 1
    return n


def _dial(S, tenant: str, cid: str, tid: str, st: dict[str, Any]) -> bool:
    sc = S.approved(tenant)
    with session() as s:
        t = s.get(CcTarget, tid)
        call = CcCall(tenant_id=tenant, provider=st["provider"], caller=t.phone, status="ringing", direction="out",
                      campaign_id=cid, target_id=tid, script_id=sc["id"], script_version=sc["version"], lang=t.lang or "")
        s.add(call)
        s.flush()
        call_id = call.id
        t.status, t.tries, t.call_id, t.why = "calling", t.tries + 1, call_id, ""
        to = t.phone
    urls = st["urls"]
    tk = S.ticket(call_id, minutes=10)
    q = f"?out={call_id}&ot={tk}"
    prov = P.get(st["provider"], S.creds(tenant))
    try:
        got = prov.dial(to, st["number"], urls["answer"] + q, urls["hangup"] + q,
                        (urls["answer"].rsplit("/", 1)[0] + "/machine" + q) if prov.machine_check else "")
    except P.ProviderError as e:
        with session() as s:
            c = s.get(CcCall, call_id)
            c.status, c.outcome, c.ended_at = "ended", "failed", now()
            c.summary = str(e)[:300]
        after_call(call_id, "failed")
        return False
    with session() as s:
        c = s.get(CcCall, call_id)
        c.provider_call = (got.get("call") or "")[:80]
    return True


# ---------------------------------------------------------------- provider events for a call Hoola made
def _out_call(tenant: str, call_id: str, ticket: str) -> CcCall | None:
    S = _S()
    if not S.ticket_ok(call_id, ticket):
        return None
    with session() as s:
        c = s.get(CcCall, call_id)
        if c is None or c.tenant_id != tenant or c.direction != "out":
            return None
        s.expunge(c)
        return c


def answered(tenant: str, call_id: str, ticket: str, info: dict[str, str], answered_by: str) -> dict[str, Any]:
    """The person picked up (or a machine did). -> stream to the AI, or the voicemail line, or end."""
    S = _S()
    c = _out_call(tenant, call_id, ticket)
    if c is None:
        return {"action": "say", "text": "", "call_id": call_id, "lang": "en-IN"}
    with session() as s:
        row = s.get(CcCall, call_id)
        if info.get("call"):
            row.provider_call = info["call"][:80]
        row.answered_by = answered_by or "unknown"
        camp = s.get(CcCampaign, row.campaign_id)
        vm = (camp.voicemail if camp else "") or ""
        lang = row.lang or "en-IN"
    if answered_by == "machine":
        return _voicemail(tenant, call_id, vm, lang)
    if not S.claim_slot(tenant, call_id):
        with session() as s:
            row = s.get(CcCall, call_id)
            row.status, row.outcome, row.ended_at = "ended", "busy", now()
        after_call(call_id, "busy")
        return {"action": "say", "text": "", "call_id": call_id, "lang": lang}
    with session() as s:
        s.get(CcCall, call_id).status = "live"
    return {"action": "stream", "ticket": S.ticket(call_id), "call_id": call_id, "lang": lang}


def _voicemail(tenant: str, call_id: str, text: str, lang: str) -> dict[str, Any]:
    with session() as s:
        row = s.get(CcCall, call_id)
        row.status, row.outcome, row.ended_at, row.answered_by = "ended", "voicemail", now(), "machine"
        row.summary = "An answering machine answered" + (": Hoola left your message." if text else ".")
    after_call(call_id, "voicemail")
    return {"action": "say", "text": text, "call_id": call_id, "lang": lang}


def machine(tenant: str, call_id: str, ticket: str, answered_by: str) -> dict[str, Any] | None:
    """Plivo's answering-machine check came after the pick-up: a machine -> move the call to the voicemail line."""
    c = _out_call(tenant, call_id, ticket)
    if c is None or answered_by != "machine":
        return None
    return {"call_id": call_id, "provider_call": c.provider_call}


def voicemail_line(tenant: str, call_id: str, ticket: str) -> dict[str, Any]:
    c = _out_call(tenant, call_id, ticket)
    if c is None:
        return {"action": "say", "text": "", "lang": "en-IN"}
    with session() as s:
        camp = s.get(CcCampaign, c.campaign_id)
        vm = (camp.voicemail if camp else "") or ""
    _S().release_slot(tenant, call_id)
    return _voicemail(tenant, call_id, vm, c.lang or "en-IN")


def dial_ended(tenant: str, call_id: str, ticket: str, status: str, seconds: float | None = None) -> None:
    """The provider says the call is over. Only a call that never reached the AI is settled here (no answer / busy /
    failed); a call the AI handled is settled by service.finish."""
    c = _out_call(tenant, call_id, ticket)
    if c is None:
        return
    st = (status or "").lower()
    outcome = ("busy" if "busy" in st else "no_answer" if any(x in st for x in ("no-answer", "no_answer", "noanswer", "timeout",
                                                                                    "cancel", "not_answer"))
               else "failed" if any(x in st for x in ("fail", "invalid", "unallocated", "rejected")) else "no_answer")
    with session() as s:
        row = s.get(CcCall, call_id)
        if row.status not in ("ringing",):
            if seconds is not None and not row.seconds:
                row.seconds = float(seconds)
            return
        row.status, row.outcome, row.ended_at = "ended", outcome, now()
    after_call(call_id, outcome)


# ---------------------------------------------------------------- the line's own tools on a call Hoola made
def save_result(cc, **fields) -> dict[str, Any]:
    """The answers she asked for on this list (need, budget, date ...). Only her field names are kept."""
    with session() as s:
        row = s.get(CcCall, cc.call_id)
        t = s.get(CcTarget, row.target_id) if row else None
        if t is None:
            return {"error": "Not a call from a call list."}
        camp = s.get(CcCampaign, t.campaign_id)
        names = {f["name"] for f in _j(camp.fields, [])} | {"outcome", "interest", "note"}
        res = _j(t.result, {})
        for k, v in fields.items():
            k2 = re.sub(r"\W+", "_", str(k).lower())[:40]
            if k2 in names and v not in (None, ""):
                res[k2] = R.mask_text(str(v))[:300]
        t.result = json.dumps(res, ensure_ascii=False)
    return {"saved": True, "say": "Saved. Carry on with the call."}


def do_not_call(cc, **_) -> dict[str, Any]:
    with session() as s:
        row = s.get(CcCall, cc.call_id)
        t = s.get(CcTarget, row.target_id) if row else None
        if t is not None:
            t.status, t.why, t.outcome = "dnd", "said do not call", "dnd"
            lead = t.lead_id
        else:
            lead = ""
    if lead:
        try:
            from ..telecall import service as TC
            TC.mark_dnd(cc.tenant, lead)
        except Exception:      # noqa: BLE001
            log.exception("telecall dnd failed")
    return {"saved": True, "say": "Apologise once, say they will not be called again, then end the call."}


def call_back(cc, when: str = "", **_) -> dict[str, Any]:
    from ..telecall import service as TC
    at = TC.when(cc.tenant, when)
    if at is None:
        return {"error": "Ask for a clear day and time."}
    with session() as s:
        row = s.get(CcCall, cc.call_id)
        t = s.get(CcTarget, row.target_id) if row else None
        if t is None:
            return {"error": "Not a call from a call list."}
        t.next_at = at
        res = _j(t.result, {})
        res["call_back"] = when[:40]
        t.result = json.dumps(res, ensure_ascii=False)
    return {"saved": True, "say": f"Confirm the time back to them ({when}) and close politely."}


# ---------------------------------------------------------------- after a call Hoola made
_TO_TELE = {"appointment": "converted", "answered": "interested", "message": "callback", "complaint": "complaint",
            "transferred": "interested", "no_answer": "no_answer", "busy": "busy", "failed": "not_reachable",
            "voicemail": "no_answer", "dnd": "dnd"}


def after_call(call_id: str, outcome: str = "") -> None:
    """Settle the person's row: done, try again later, or never again; and tell her Telecaller lead."""
    with session() as s:
        row = s.get(CcCall, call_id)
        if row is None or row.direction != "out":
            return
        t = s.get(CcTarget, row.target_id)
        camp = s.get(CcCampaign, row.campaign_id)
        if t is None or camp is None:
            return
        out = outcome or row.outcome or "answered"
        t.outcome = out if t.status != "dnd" else "dnd"
        res = _j(t.result, {})
        if t.status == "dnd":
            pass
        elif out in RETRYABLE:
            if t.tries < camp.max_tries:
                t.status, t.next_at = "retry", now() + timedelta(minutes=camp.retry_min)
            else:
                t.status, t.why = "done", "no more tries"
        elif res.get("call_back") and t.next_at and _aware(t.next_at) > now():
            t.status = "retry"          # she / they asked for a later time: one more call then
        else:
            t.status = "done"
        tenant, lead, summary = row.tenant_id, t.lead_id, row.summary or ""
        next_at, tout = t.next_at, t.outcome
        status = t.status
        needs = out in ("message", "transferred", "complaint")
        name = t.name or R.mask_phone(t.phone)
    if lead:
        try:
            from ..telecall import service as TC
            nxt = ""
            if status == "retry" and next_at:
                nxt = _aware(next_at).astimezone(TC._tz(tenant)).strftime("%Y-%m-%d %H:%M")
            TC.log_call(tenant, lead, outcome=_TO_TELE.get(tout, "interested"), notes=(summary or "")[:500],
                        next_when=nxt, by="hoola", source="ai_call")
        except Exception:      # noqa: BLE001 - the Telecaller row failing never loses the call
            log.exception("telecall log for an AI call failed")
    if needs:
        _S().publish(tenant, "callcentre_campaign_needs", {"call_id": call_id, "name": name, "outcome": out,
                                                            "say": f"{name}: {summary[:160] or out}"})


# ---------------------------------------------------------------- Test chat (nobody is called)
def test_chat(tenant: str, turns: list[dict[str, str]], cid: str = "", use_draft: bool = True) -> dict[str, Any]:
    """Talk to the AI caller by typing: the same script + business knowledge + rules, a text model, no phone call.
    turns = [{"who": "customer"|"hoola", "text"}]; returns Hoola's next line and what it used."""
    from . import knowledge as K
    S = _S()
    sc = (S.draft(tenant) if use_draft else None) or S.approved(tenant)
    if not sc:
        raise OutError("Write a call script first.")
    c = sc.get("content") or {}
    camp = None
    if cid:
        with session() as s:
            camp = _view(_get(s, tenant, cid))
    last = next((x.get("text", "") for x in reversed(turns or []) if x.get("who") == "customer"), "")
    facts = K.search(tenant, last) if last else []
    faq, _sc = R.best_faq(last, c.get("faqs") or []) if last else (None, 0)
    known = "\n".join(f"- {f['text']}" for f in facts) + (f"\n- {faq['q']} {faq['a']}" if faq else "")
    system = test_persona(tenant, sc, camp) + "\n\nFACTS FOUND FOR THE LAST QUESTION (the only facts you may use):\n" + (known or "(none: say you will find out and offer a call-back)")
    convo = "\n".join(f"{'Customer' if x.get('who') == 'customer' else 'You'}: {x.get('text', '')}" for x in (turns or [])[-20:])
    reply = S._llm(system, (convo or "(the call just connected)") + "\nYou:").strip()
    if not reply:
        reply = (c.get("greeting") or R.disclosure("en-IN", c.get("business") or "", "", False)) if not turns else \
            ("I'll check that and get back to you." if not known else (faq["a"] if faq else facts[0]["text"]))
    allowed = json.dumps(c, ensure_ascii=False) + " " + known
    return {"reply": reply, "facts_used": facts, "faq_used": faq["q"] if faq else "", "flags": R.unscripted(reply, allowed),
            "script_version": sc.get("version"), "status": sc.get("status")}


def test_persona(tenant: str, sc: dict[str, Any], camp: dict[str, Any] | None) -> str:
    c = sc.get("content") or {}
    biz = c.get("business") or "the business"
    steps = "\n".join(f"{i + 1}. {x.get('name', '')}: {x.get('say', '')}" for i, x in enumerate(c.get("steps") or []))
    why = (camp or {}).get("goal") or "the reason in the script"
    return (f"You are the AI phone assistant of {biz}, in a TEST conversation typed by the owner pretending to be a "
            f"customer. {'You called them about: ' + why if camp else 'The customer called the business.'}\n"
            "First line: say you are an AI assistant of the business. Answer ONLY from the facts given and the script; "
            "never invent a price, date, discount or promise; if you do not know, say you will find out and offer a "
            "call-back. Short, warm, natural spoken sentences.\n"
            + (f"CALL STEPS:\n{steps}\n" if steps else "")
            + "\n".join(f"Never: {x}" for x in c.get("never") or []))
