"""v0.112 Standing order mandate: she signs ONE rule ("every Monday, the usual list, max Rs 20,000, till 31 Dec") and that
signature is the tap for each run that stays inside it (research Diagram 1.7, AP2 "intent mandate": limits + expiry,
signed once).

Each run (`tick`) sends an ordinary deal_ask (tag {mandate: id}, this side only). When the quote comes back, code checks it
(`_check`): every line in full (no short / missing / substitute), total <= max_total, each price within tolerance_pct
(default 5%) of the BASE price (the prices of the first order she confirmed by her own tap - so the first run always
asks her), quote not expired, her pay choice offered. Inside the rule -> one card "placing at HH:MM unless you stop it"
and after hold_minutes (default 30) `confirm(by_mandate=)` places it; `deal.confirm` re-checks with `allows()` and the
rule's signature digest (an edited rule = a new signature). Outside the rule (price jump, shortage, over cap) -> her normal
confirm card with the reason. She can stop one run ("Rok do"), pause, resume or end the rule with one tap. The model can
draft a rule but never sign it (signing is an API tap, fingerprint once a phone is set up).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from .service import NetError, resolve, tell

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_WORDS = {"mon": "Somvar", "tue": "Mangalvar", "wed": "Budhvar", "thu": "Guruvar", "fri": "Shukravar", "sat": "Shanivar",
             "sun": "Ravivar"}
MAX_RUNS = 400
MAX_ACTIVE = 20
TOL_DEFAULT, TOL_MAX = 5.0, 25.0
STATS = {"runs": 0, "auto_placed": 0, "needs_tap": 0}


class MandateError(NetError):
    pass


class Mandate(Base):
    __tablename__ = "hoola_mandates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("md"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # S-1, S-2 ...
    peer: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200), default="")
    items: Mapped[list] = mapped_column(JSON, default=list)
    days: Mapped[list] = mapped_column(JSON, default=list)                 # ["mon", ...]
    at: Mapped[str] = mapped_column(String(5), default="09:00")            # her local time
    max_total: Mapped[float] = mapped_column(Float, default=0.0)
    tolerance_pct: Mapped[float] = mapped_column(Float, default=TOL_DEFAULT)
    until: Mapped[str] = mapped_column(String(10), default="")
    pay: Mapped[str] = mapped_column(String(8), default="")
    mode: Mapped[str] = mapped_column(String(10), default="pickup")
    hold_minutes: Mapped[int] = mapped_column(Integer, default=30)
    state: Mapped[str] = mapped_column(String(8), default="draft")         # draft | active | paused | ended
    base: Mapped[dict] = mapped_column(JSON, default=dict)                 # {norm item: price} from her first tapped order
    signed_digest: Mapped[str] = mapped_column(String(64), default="")
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    runs: Mapped[list] = mapped_column(JSON, default=list)                 # [{deal_id, at, status, total, why, hold_until}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _dl():
    from . import deal as dl
    return dl


def _tz(tenant: str):
    try:
        from ..galla.service import _tz as gtz
        return gtz(tenant)
    except Exception:
        from datetime import timezone
        return timezone(timedelta(hours=5, minutes=30))


def _utc(d: datetime | None) -> datetime | None:
    from datetime import timezone
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _get(tenant: str, mid: str) -> Mandate:
    with session() as s:
        m = s.get(Mandate, mid)
        if m is None or m.tenant_id != tenant:
            raise MandateError("Yeh standing order nahi mila.")
        s.expunge(m)
        return m


def _set(mid: str, **kw) -> None:
    with session() as s:
        m = s.get(Mandate, mid)
        if m is not None:
            for k, v in kw.items():
                setattr(m, k, v)


def next_after(m: Mandate, after: datetime) -> datetime | None:
    """The next run time after `after` (her local day + time), or None once `until` has passed."""
    tz = _tz(m.tenant_id)
    hh, mm = (int(x) for x in (m.at or "09:00").split(":"))
    local = _utc(after).astimezone(tz)
    for k in range(0, 15):
        day = (local + timedelta(days=k)).date()
        if DAYS[day.weekday()] not in (m.days or []):
            continue
        t = datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)
        if t <= local:
            continue
        if m.until and day.isoformat() > m.until:
            return None
        return t.astimezone(_utc(after).tzinfo)
    return None


def _clean(dl, items: Any, days: Any, at: str, max_total: Any, until: str, tolerance: Any, hold_minutes: Any):
    body = dl.check_ask({"items": items, "mode": "pickup"})
    ds = [str(x).lower()[:3] for x in (days if isinstance(days, list) else str(days or "").replace(" ", "").split(","))]
    if "dai" in ds or "eve" in ds or "roz" in ds:                  # daily / everyday / roz
        ds = list(DAYS)
    ds = [x for x in DAYS if x in ds]
    if not ds:
        raise MandateError("Kaunse din? (mon..sun, ya daily)")
    try:
        hh, mm = (int(x) for x in str(at or "09:00").split(":"))
        assert 0 <= hh < 24 and 0 <= mm < 60
    except Exception:
        raise MandateError("Samay HH:MM mein (jaise 09:30).")
    cap = dl._num(max_total, 1, dl.MAX_TOTAL)
    if cap is None:
        raise MandateError("Har order ki zyada se zyada rakam (₹) bataiye.")
    try:
        u = date.fromisoformat(str(until or ""))
    except ValueError:
        raise MandateError("Kab tak? (taareekh YYYY-MM-DD)")
    if u <= date.today() or u > date.today() + timedelta(days=366):
        raise MandateError("Aakhri taareekh aaj ke baad aur ek saal ke andar ho.")
    tol = dl._num(tolerance if tolerance not in (None, "") else TOL_DEFAULT, 0, TOL_MAX)
    if tol is None:
        raise MandateError(f"Daam badhne ki chhoot 0 se {TOL_MAX:g}% tak.")
    hold = dl._num(hold_minutes if hold_minutes not in (None, "") else 30, 0, 720)
    if hold is None:
        raise MandateError("Rokne ka samay 0 se 720 minute.")
    return body["items"], ds, f"{hh:02d}:{mm:02d}", round(cap, 2), u.isoformat(), round(tol, 2), int(hold)


def create(tenant: str, to: str, items: Any, days: Any, at: str, max_total: Any, until: str, tolerance: Any = None,
           pay: str = "", hold_minutes: Any = None, title: str = "", mode: str = "pickup") -> dict[str, Any]:
    """A DRAFT rule. Nothing runs until she signs it (her tap)."""
    dl = _dl()
    peer = resolve(tenant, to)
    from .service import _link
    l = _link(tenant, peer)
    if l is None or l.status != "active":
        raise MandateError(f"{to} se Hoola connection nahi hai.")
    its, ds, hm, cap, u, tol, hold = _clean(dl, items, days, at, max_total, until, tolerance, hold_minutes)
    with session() as s:
        n_active = len(s.scalars(select(Mandate.id).where(Mandate.tenant_id == tenant,
                                                          Mandate.state.in_(("active", "paused", "draft")))).all())
        n_all = len(s.scalars(select(Mandate.id).where(Mandate.tenant_id == tenant)).all())
        if n_active >= MAX_ACTIVE:
            raise MandateError(f"{MAX_ACTIVE} se zyada standing order nahi.")
        m = Mandate(id=new_id("md"), tenant_id=tenant, number=f"S-{n_all + 1}", peer=peer, items=its, days=ds, at=hm,
                    max_total=cap, tolerance_pct=tol, until=u, pay=pay if pay in ("upi", "counter", "khata") else "",
                    mode=mode if mode in ("pickup", "delivery") else "pickup", hold_minutes=hold, state="draft",
                    title=str(title or "")[:200] or ", ".join(f"{i['item']} {i['qty']:g}" for i in its[:3]), base={},
                    runs=[], created_at=now())
        s.add(m)
        s.flush()
        mid = m.id
    m = _get(tenant, mid)
    return {"status": "needs_tap", "mandate": view(m), "card": sign_card(tenant, mid),
            "say": f"Standing order {m.number} taiyaar: {_when_say(m)}, har baar zyada se zyada {dl.inr(cap)}, {u} tak. "
                   "Chalu karne ke liye card par 'Haan, chalu karo' dabaiye."}


def _when_say(m: Mandate) -> str:
    ds = m.days or []
    d = "roz" if len(ds) == 7 else ", ".join(DAY_WORDS[x] for x in ds)
    return f"{d} {m.at} baje"


def sign_card(tenant: str, mid: str) -> dict[str, Any]:
    """Exactly what she signs (also the fingerprint digest). Any edit = a different card = a new signature."""
    dl = _dl()
    m = _get(tenant, mid)
    return {"title": f"Standing order {m.number}: {dl._say_who(m.peer)}", "payee": dl._say_who(m.peer),
            "amount": f"har baar max {dl.inr(m.max_total)}",
            "items": [{"name": f"{i['item']} x {i['qty']:g} {i.get('unit') or ''}".strip(), "price": ""} for i in m.items or []],
            "when": _when_say(m), "until": m.until, "tolerance": f"{m.tolerance_pct:g}%", "hold": m.hold_minutes,
            "pay": m.pay, "peer": m.peer}


def digest(card: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(card, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sign(tenant: str, mid: str, by_tap: bool = False) -> dict[str, Any]:
    if not by_tap:
        raise MandateError("Standing order sirf aapke tap se chalu hota hai.")
    m = _get(tenant, mid)
    if m.state not in ("draft", "paused"):
        raise MandateError(f"Yeh standing order '{m.state}' hai.")
    nxt = next_after(m, now())
    if nxt is None:
        raise MandateError("Aakhri taareekh tak koi din nahi bachta.")
    _set(mid, state="active", signed_digest=digest(sign_card(tenant, mid)), signed_at=now(), next_run=nxt)
    m = _get(tenant, mid)
    return {"status": "active", "mandate": view(m),
            "say": f"{m.number} chalu. Agla order {_local(m, nxt)} ko. Daam {m.tolerance_pct:g}% se zyada badhe, kuch kam ho, ya "
                   "rakam seema se upar jaaye to aapse poochhunga."}


def _local(m: Mandate, t: datetime | None) -> str:
    if t is None:
        return ""
    return _utc(t).astimezone(_tz(m.tenant_id)).strftime("%d/%m %H:%M")


def set_state(tenant: str, mid: str, action: str) -> dict[str, Any]:
    m = _get(tenant, mid)
    if action == "pause" and m.state == "active":
        _set(mid, state="paused", next_run=None)
    elif action == "resume" and m.state == "paused":
        return sign(tenant, mid, by_tap=True)           # her tap on Resume = the same signed rule again
    elif action in ("stop", "end"):
        _set(mid, state="ended", next_run=None)
    else:
        raise MandateError("action: pause, resume, stop")
    return {"status": _get(tenant, mid).state, "mandate": view(_get(tenant, mid))}


def view(m: Mandate) -> dict[str, Any]:
    dl = _dl()
    return {"id": m.id, "mandate_id": m.id, "number": m.number, "with": dl._say_who(m.peer), "peer": m.peer, "title": m.title,
            "items": m.items or [], "days": m.days or [], "at": m.at, "when": _when_say(m), "max_total": m.max_total,
            "tolerance_pct": m.tolerance_pct, "until": m.until, "pay": m.pay, "hold_minutes": m.hold_minutes,
            "state": m.state, "base_set": bool(m.base), "next_run": m.next_run.isoformat() if m.next_run else "",
            "next_say": _local(m, m.next_run), "runs": (m.runs or [])[-10:]}


def mandates(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(Mandate).where(Mandate.tenant_id == tenant).order_by(Mandate.created_at.desc()).limit(50)).all()
        for r in rows:
            s.expunge(r)
    return [view(r) for r in rows]


def number(tenant: str, mid: str) -> str:
    try:
        return _get(tenant, mid).number
    except MandateError:
        return ""


# ---------------------------------------------------------------- the code check
def _check(m: Mandate, d) -> list[str]:
    """Why this quote is NOT inside the rule ([] = inside)."""
    dl = _dl()
    q = d.quote or {}
    why = []
    if d.state != "quoted" or dl._expired(d):
        why.append("quote lagoo nahi")
    if not q.get("lines") or q.get("short") or q.get("missing"):
        why.append("kuch cheez kam / nahi hai: " + ", ".join((q.get("short") or []) + (q.get("missing") or [])))
    if any(l.get("status") == "substitute" for l in q.get("lines") or []):
        why.append("badle mein doosri cheez")
    if float(q.get("total") or 0) > m.max_total + 0.01:
        why.append(f"rakam {dl.inr(q.get('total'))} seema {dl.inr(m.max_total)} se zyada")
    if not m.base:
        why.append("pehla order: aapke tap se (iske daam aage ke liye aadhaar banenge)")
    else:
        for ln in q.get("lines") or []:
            if not ln.get("qty"):
                continue
            b = m.base.get(dl.norm(ln["item"]))
            p = float(ln.get("price") or 0)
            if b is None:
                why.append(f"{ln['item']}: naya item")
            elif p > float(b) * (1 + m.tolerance_pct / 100) + 0.001:
                why.append(f"{ln['item']} ka daam {dl.inr(b)} se {dl.inr(p)} ({(p / float(b) - 1) * 100:.0f}% zyada)")
    opts = ((q.get("terms") or {}).get("pay_options")) or []
    if m.pay and m.pay not in opts:
        why.append(f"'{m.pay}' se paisa is baar nahi")
    return why


def _run_of(m: Mandate, deal_id: str) -> dict[str, Any] | None:
    return next((r for r in m.runs or [] if r.get("deal_id") == deal_id), None)


def _update_run(mid: str, deal_id: str, **kw) -> None:
    with session() as s:
        m = s.get(Mandate, mid)
        if m is None:
            return
        runs = [dict(r) for r in m.runs or []]
        hit = False
        for r in runs:
            if r.get("deal_id") == deal_id:
                r.update(kw)
                hit = True
        if not hit:                                     # the quote came back while the list was still going out
            runs.append({"deal_id": deal_id, "at": now().isoformat()} | kw)
        m.runs = runs[-MAX_RUNS:]


def _mandate_of(tenant: str, d) -> Mandate | None:
    mid = str((d.tag or {}).get("mandate") or "")
    if not mid:
        return None
    try:
        return _get(tenant, mid)
    except MandateError:
        return None


def on_quote(tenant: str, d) -> bool:
    """A quote for a standing-order run: inside the rule -> 'placing at ...' card; else her confirm card with why."""
    m = _mandate_of(tenant, d)
    if m is None:
        return False
    dl = _dl()
    q = d.quote or {}
    why = _check(m, d) if m.state == "active" else ["standing order chalu nahi"]
    if why:
        STATS["needs_tap"] += 1
        _update_run(m.id, d.id, status="needs_tap", why=why[:4], total=q.get("total"))
        dl._publish(tenant, d, "confirm", f"Standing order {m.number}: {dl._say_who(d.peer)} ka quote {dl.inr(q.get('total'))}. "
                    "Niyam ke bahar: " + "; ".join(why[:4]) + ". Haan aapke tap se hi.",
                    f"Standing order {m.number} ka quote niyam ke bahar ({'; '.join(why[:3])}). Owner tap kare tabhi order jaayega. "
                    f"deal_id={d.id}.")
        return True
    hold_until = now() + timedelta(minutes=m.hold_minutes)
    _update_run(m.id, d.id, status="holding", hold_until=hold_until.isoformat(), total=q.get("total"), why=[])
    d.waiting = "mandate"
    dl._save(d)
    dl._publish(tenant, d, "mandate", f"Standing order {m.number}: {dl._say_who(d.peer)} ka quote {dl.inr(q.get('total'))}, sab "
                f"niyam ke andar. {_local(m, hold_until)} par khud pakka karunga; rokna ho to 'Is baar rok do'.",
                f"Standing order {m.number}: quote niyam ke andar, {m.hold_minutes} min baad code khud confirm karega. deal_id={d.id}.")
    if m.hold_minutes == 0:
        _place(tenant, m.id, d.id)
    return True


def on_reject(tenant: str, d) -> bool:
    m = _mandate_of(tenant, d)
    if m is None:
        return False
    _update_run(m.id, d.id, status="rejected", why=[d.reason or "mana"])
    _dl()._publish(tenant, d, "info", f"Standing order {m.number}: {_dl()._say_who(d.peer)} ne is baar mana kiya ({d.reason}).")
    return True


def allows(tenant: str, mid: str, d) -> bool:
    """deal.confirm asks: may this rule place THIS order right now? Everything checked again in code."""
    try:
        m = _get(tenant, mid)
    except MandateError:
        return False
    if m.state != "active" or d.role != "buyer" or d.peer != m.peer or str((d.tag or {}).get("mandate") or "") != mid:
        return False
    if m.signed_digest != digest(sign_card(tenant, mid)):
        return False
    if m.until and date.today().isoformat() > m.until:
        return False
    r = _run_of(m, d.id)
    if r is None or r.get("status") != "holding":
        return False
    hu = _dl()._when(r.get("hold_until"))
    if hu is None or hu > now():
        return False
    return not _check(m, d)


def after_confirm(tenant: str, d, by_tap: bool) -> None:
    """Her own tap on a standing-order quote: the first one sets the base prices."""
    m = _mandate_of(tenant, d)
    if m is None:
        return
    dl = _dl()
    if by_tap:
        _update_run(m.id, d.id, status="placed_by_tap")
        if not m.base:
            _set(m.id, base={dl.norm(l["item"]): float(l.get("price") or 0) for l in (d.quote or {}).get("lines") or []
                             if l.get("qty")})
    else:
        _update_run(m.id, d.id, status="placed")


def hold_once(tenant: str, deal_id: str) -> dict[str, Any]:
    """'Is baar rok do': this run waits for her normal tap."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    m = _mandate_of(tenant, d)
    if m is None:
        raise MandateError("Yeh standing order ka order nahi hai.")
    r = _run_of(m, d.id)
    if r is None or r.get("status") != "holding":
        raise MandateError("Is order ko rokne ka samay nahi raha.")
    _update_run(m.id, d.id, status="stopped_once")
    d.waiting = "confirm"
    dl._save(d)
    dl._publish(tenant, d, "confirm", f"Theek hai, {m.number} ka yeh order roka. Chahein to khud 'Haan, confirm' kar sakti hain.")
    return {"status": "held", "deal": dl.view(dl._get(tenant, deal_id))}


def _place(tenant: str, mid: str, deal_id: str) -> None:
    dl = _dl()
    m = _get(tenant, mid)
    try:
        dl.confirm(tenant, deal_id, by_mandate=mid, pay=m.pay)
        STATS["auto_placed"] += 1
        d = dl._get(tenant, deal_id)
        dl._publish(tenant, d, "info", f"Standing order {m.number}: order pakka kiya ({dl.inr((d.quote or {}).get('total'))}).")
    except NetError as e:
        _update_run(mid, deal_id, status="failed", why=[str(e)[:200]])
        try:
            dl._publish(tenant, dl._get(tenant, deal_id), "confirm", f"Standing order {m.number}: khud pakka nahi hua ({e}). "
                        "Aap dekh kar 'Haan, confirm' kar sakti hain.")
        except Exception:
            pass


def run_now(tenant: str, mid: str) -> dict[str, Any]:
    """One run: the list goes out (used by the timer; also 'abhi bhejo')."""
    dl = _dl()
    m = _get(tenant, mid)
    if m.state != "active":
        raise MandateError("Standing order chalu nahi hai.")
    if len(m.runs or []) >= MAX_RUNS:
        _set(mid, state="ended", next_run=None)
        raise MandateError("Is standing order ke sab order ho chuke.")
    out = dl.ask(tenant, m.peer, m.items, m.mode, "", f"Standing order {m.number}", m.title, tag={"mandate": mid})
    with session() as s:
        row = s.get(Mandate, mid)
        runs = list(row.runs or [])
        if not any(r.get("deal_id") == out["deal"]["id"] for r in runs):
            runs.append({"deal_id": out["deal"]["id"], "at": now().isoformat(), "status": "asked"})
        row.runs = runs[-MAX_RUNS:]
    STATS["runs"] += 1
    return {"status": "asked", "deal": dl.view(dl._get(tenant, out["deal"]["id"]))}


def tick() -> int:
    n = 0
    with session() as s:
        rows = s.scalars(select(Mandate).where(Mandate.state == "active")).all()
        for r in rows:
            s.expunge(r)
    for m in rows:
        try:
            if m.until and date.today().isoformat() > m.until:
                _set(m.id, state="ended", next_run=None)
                tell(m.tenant_id, "hoola_mandate", view(_get(m.tenant_id, m.id)) |
                     {"card": "info", "say": f"Standing order {m.number} ki aakhri taareekh nikal gayi; band kiya."})
                continue
            for r in m.runs or []:                      # holds that are over -> place
                if r.get("status") == "holding":
                    hu = _dl()._when(r.get("hold_until"))
                    if hu is not None and hu <= now():
                        _place(m.tenant_id, m.id, r["deal_id"])
                        n += 1
            nr = _utc(m.next_run)
            if nr is not None and nr <= now():
                _set(m.id, next_run=next_after(m, now()))
                try:
                    run_now(m.tenant_id, m.id)
                except NetError as e:
                    tell(m.tenant_id, "hoola_mandate", view(_get(m.tenant_id, m.id)) |
                         {"card": "info", "say": f"Standing order {m.number}: list nahi gayi ({e})."})
                n += 1
        except Exception:
            continue
    return n
