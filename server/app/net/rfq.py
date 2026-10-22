"""v0.107 Compare quotes: the same list to 2-5 sellers, a fixed wait, one table sorted by cost in code (research Diagram 1.3).

AI buyers grab the first reply and do worse with too many options, so her Hoola does NOT show quotes as they arrive:
each seller gets an ordinary deal_ask (tag {rfq: id} stays on her side only - no seller learns who else was asked or what
they quoted), the quotes are held, and when every seller has answered or the window ends (default 30 minutes) one
"compare" card shows at most 5 rows: complete quotes first, then by total (GST included), with what is short / missing,
credit (khata days), pay options, the checked verified-business credential, the trust tier and the past fill rate (how
much of earlier lists this seller actually gave). She taps one row (the normal fingerprinted deal confirm); the others get
"Is baar nahi, dhanyavaad" unless she chose a split order.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import identity as idn
from .service import NetError, resolve, tell

MIN_SELLERS, MAX_SELLERS, MAX_ROWS = 2, 5, 5
WINDOW_DEFAULT, WINDOW_MIN, WINDOW_MAX = 30, 5, 240
THANKS = "Is baar nahi, dhanyavaad."
STATS = {"started": 0, "shown": 0, "chosen": 0}


class RfqError(NetError):
    pass


class Rfq(Base):
    __tablename__ = "hoola_rfqs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    items: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(Text, default="")
    deals: Mapped[list] = mapped_column(JSON, default=list)                 # [{deal_id, peer}]
    failed: Mapped[list] = mapped_column(JSON, default=list)                # [{to, reason}]
    window_minutes: Mapped[int] = mapped_column(Integer, default=WINDOW_DEFAULT)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    state: Mapped[str] = mapped_column(String(10), default="open")         # open | ready | chosen | closed
    split: Mapped[bool] = mapped_column(Boolean, default=False)
    chosen: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _dl():
    from . import deal as dl
    return dl


def _get(tenant: str, rfq_id: str) -> Rfq:
    with session() as s:
        r = s.get(Rfq, rfq_id)
        if r is None or r.tenant_id != tenant:
            raise RfqError("Yeh tulna (compare) nahi mili.")
        s.expunge(r)
        return r


def _set(rfq_id: str, **kw) -> None:
    with session() as s:
        r = s.get(Rfq, rfq_id)
        if r is not None:
            for k, v in kw.items():
                setattr(r, k, v)


def start(tenant: str, to: Any, items: Any, mode: str = "pickup", need_by: str = "", note: str = "", title: str = "",
          window_minutes: Any = None) -> dict[str, Any]:
    """The same list to 2-5 sellers; the table comes when all answered or the window ends."""
    dl = _dl()
    names = [str(x).strip() for x in (to if isinstance(to, list) else str(to or "").split(",")) if str(x).strip()]
    peers: list[tuple[str, str]] = []
    for n in names:
        try:
            p = resolve(tenant, n)
        except NetError:
            p = n
        if p not in [x[1] for x in peers]:
            peers.append((n, p))
    if not (MIN_SELLERS <= len(peers) <= MAX_SELLERS):
        raise RfqError(f"Tulna ke liye {MIN_SELLERS} se {MAX_SELLERS} dukaan / wholesaler bataiye.")
    dl.check_ask({"items": items, "mode": mode, "need_by": need_by, "note": note, "title": title})      # fail early, once
    try:
        win = int(window_minutes) if window_minutes not in (None, "") else WINDOW_DEFAULT
    except (TypeError, ValueError):
        win = WINDOW_DEFAULT
    win = max(WINDOW_MIN, min(win, WINDOW_MAX))
    rid = new_id("rq")
    with session() as s:
        s.add(Rfq(id=rid, tenant_id=tenant, title=str(title or "")[:200], items=list(items or []), note=str(note or "")[:600],
                  deals=[], failed=[], window_minutes=win, closes_at=now() + timedelta(minutes=win), state="open",
                  created_at=now()))
    deals, failed = [], []
    for name, _p in peers:
        try:
            out = dl.ask(tenant, name, items, mode, need_by, note, title, tag={"rfq": rid})
            deals.append({"deal_id": out["deal"]["id"], "peer": out["deal"]["peer"]})
            _set(rid, deals=list(deals))                # quotes may come back while the next seller is asked
        except NetError as e:
            failed.append({"to": name, "reason": str(e)[:200]})
    if not deals:
        _set(rid, state="closed", failed=failed)
        raise RfqError("Kisi tak list nahi pahunchi: " + "; ".join(f"{f['to']}: {f['reason']}" for f in failed))
    _set(rid, deals=deals, failed=failed)
    STATS["started"] += 1
    _maybe_ready(tenant, rid)
    r = _get(tenant, rid)
    return {"status": r.state, "rfq": view(r),
            "say": f"List {len(deals)} jagah gayi. Sabke quote aane par (ya {win} minute baad) ek saath tulna dikhaunga; "
                   "pehla jawab dekh kar jaldi nahi karunga." + (f" Nahi pahunchi: {', '.join(f['to'] for f in failed)}."
                                                                  if failed else "")}


# ---------------------------------------------------------------- hooks from deal.py
def _rfq_of(tenant: str, d) -> Rfq | None:
    rid = str((d.tag or {}).get("rfq") or "")
    if not rid:
        return None
    try:
        return _get(tenant, rid)
    except RfqError:
        return None


def on_quote(tenant: str, d) -> bool:
    """A quote for a compare: held (no card of its own). True = held."""
    r = _rfq_of(tenant, d)
    if r is None or r.state not in ("open", "ready"):
        return False
    dl = _dl()
    d.waiting = "compare"
    dl._save(d)
    if r.state == "ready":                              # a late quote: the table is shown again with it
        _show(tenant, r.id, late=True)
    else:
        _maybe_ready(tenant, r.id)
    return True


def on_reject(tenant: str, d) -> bool:
    """A seller in a compare said no: no card of its own; the table may now be complete."""
    r = _rfq_of(tenant, d)
    if r is None or r.state not in ("open", "ready"):
        return False
    if r.state == "open":
        _maybe_ready(tenant, r.id)
    return True


def after_confirm(tenant: str, d) -> None:
    r = _rfq_of(tenant, d)
    if r is None or r.state == "closed":
        return
    dl = _dl()
    chosen = list(dict.fromkeys(list(r.chosen or []) + [d.id]))
    _set(r.id, state="chosen", chosen=chosen)
    STATS["chosen"] += 1
    if r.split:
        return
    for x in r.deals or []:
        if x["deal_id"] in chosen:
            continue
        try:
            o = dl._get(tenant, x["deal_id"])
            if o.state in ("asked", "quoted"):
                dl.cancel(tenant, o.id, THANKS)
        except NetError:
            continue


def _maybe_ready(tenant: str, rfq_id: str) -> None:
    r = _get(tenant, rfq_id)
    if r.state != "open":
        return
    dl = _dl()
    states = []
    for x in r.deals or []:
        try:
            states.append(dl._get(tenant, x["deal_id"]).state)
        except NetError:
            states.append("gone")
    if states and all(s not in ("asked", "") for s in states):
        _show(tenant, rfq_id)


# ---------------------------------------------------------------- the table
def fill_rate(tenant: str, peer: str) -> float | None:
    """Of what she asked this seller for before, how much did his quotes actually give (0-1)? None = no history."""
    dl = _dl()
    with session() as s:
        rows = s.scalars(select(dl.Deal).where(dl.Deal.tenant_id == tenant, dl.Deal.peer == peer, dl.Deal.role == "buyer",
                                              dl.Deal.state.in_(("accepted", "packing", "ready", "handed_over", "closed",
                                                                 "disputed"))).order_by(dl.Deal.updated_at.desc()).limit(20)).all()
        asked = got = 0.0
        for d in rows:
            for ln in (d.quote or {}).get("lines") or []:
                a = float(ln.get("asked") or 0)
                if a <= 0:
                    continue
                asked += a
                got += min(a, float(ln.get("qty") or 0)) if ln.get("status") != "substitute" else 0
    return round(got / asked, 2) if asked else None


def rows(tenant: str, r: Rfq) -> list[dict[str, Any]]:
    dl = _dl()
    from . import trust
    out = []
    for x in r.deals or []:
        try:
            d = dl._get(tenant, x["deal_id"])
        except NetError:
            continue
        q = d.quote or {}
        terms = q.get("terms") or {}
        row = {"deal_id": d.id, "with": dl._say_who(d.peer), "state": d.state, "quoted": bool(q.get("lines")),
               "v": q.get("v"), "total": q.get("total"), "gst": q.get("gst"), "short": q.get("short") or [],
               "missing": q.get("missing") or [], "subs": [l["item"] for l in q.get("lines") or [] if l.get("status") == "substitute"],
               "complete": bool(q.get("lines")) and not (q.get("short") or q.get("missing")),
               "pay_options": terms.get("pay_options") or [], "credit_days": (terms.get("khata") or {}).get("days"),
               "valid_until": q.get("valid_until", ""), "verified": bool((q.get("vbc") or {}).get("ok")),
               "verified_name": (q.get("vbc") or {}).get("name", ""), "tier": trust.tier(tenant, d.peer)["tier"],
               "fill_rate": fill_rate(tenant, d.peer), "note": q.get("note", ""), "reason": d.reason}
        if not row["quoted"]:
            row["say"] = {"rejected": "mana kar diya", "asked": "abhi jawab nahi", "cancelled": "cancel",
                          "expired": "samay khatam"}.get(d.state, d.state)
        out.append(row)
    quoted = sorted([x for x in out if x["quoted"] and x["state"] == "quoted"],
                    key=lambda x: (not x["complete"], float(x["total"] or 0)))
    rest = [x for x in out if x not in quoted]
    quoted = quoted[:MAX_ROWS]
    if quoted:
        quoted[0]["best"] = True
        best = float(quoted[0]["total"] or 0)
        for x in quoted[1:]:
            x["more_by"] = round(float(x["total"] or 0) - best, 2)
    return quoted + rest


def view(r: Rfq) -> dict[str, Any]:
    return {"id": r.id, "rfq_id": r.id, "title": r.title, "state": r.state, "items": r.items or [], "split": r.split,
            "window_minutes": r.window_minutes, "closes_at": r.closes_at.isoformat() if r.closes_at else "",
            "chosen": r.chosen or [], "failed": r.failed or [], "rows": rows(r.tenant_id, r),
            "created": r.created_at.isoformat() if r.created_at else ""}


def _show(tenant: str, rfq_id: str, late: bool = False) -> None:
    _set(rfq_id, state="ready")
    r = _get(tenant, rfq_id)
    v = view(r)
    q = [x for x in v["rows"] if x["quoted"] and x["state"] == "quoted"]
    dl = _dl()
    if q:
        b = q[0]
        say = (f"{len(q)} quote aaye. Sabse achha: {b['with']} {dl.inr(b['total'])}" +
               ("" if b["complete"] else " (kuch cheez kam)") + ". Ek chuniye (Haan aapke tap se hi)." +
               (" Ek naya quote baad mein aaya." if late else ""))
    else:
        say = "Kisi ne quote nahi bheja."
    STATS["shown"] += 1
    tell(tenant, "hoola_rfq", v | {"card": "compare", "say": say},
         f"[Compare] {say} Kisi ek ko chun-na owner ka tap hai; tum confirm nahi kar sakte. rfq_id={rfq_id}.")


def show(tenant: str, rfq_id: str) -> dict[str, Any]:
    return view(_get(tenant, rfq_id))


def rfqs(tenant: str, open_only: bool = True) -> list[dict[str, Any]]:
    with session() as s:
        q = select(Rfq).where(Rfq.tenant_id == tenant)
        if open_only:
            q = q.where(Rfq.state.in_(("open", "ready")))
        rs = s.scalars(q.order_by(Rfq.created_at.desc()).limit(30)).all()
        for r in rs:
            s.expunge(r)
    return [view(r) for r in rs]


def set_split(tenant: str, rfq_id: str, on: bool) -> dict[str, Any]:
    r = _get(tenant, rfq_id)
    if r.state == "closed":
        raise RfqError("Yeh tulna band ho chuki hai.")
    _set(rfq_id, split=bool(on))
    return show(tenant, rfq_id)


def close(tenant: str, rfq_id: str) -> dict[str, Any]:
    """Done: every quote not chosen gets the polite no."""
    dl = _dl()
    r = _get(tenant, rfq_id)
    for x in r.deals or []:
        if x["deal_id"] in (r.chosen or []):
            continue
        try:
            o = dl._get(tenant, x["deal_id"])
            if o.state in ("asked", "quoted"):
                dl.cancel(tenant, o.id, THANKS)
        except NetError:
            continue
    _set(rfq_id, state="closed")
    return show(tenant, rfq_id)


def tick() -> int:
    n = 0
    with session() as s:
        due = [(r.tenant_id, r.id) for r in s.scalars(select(Rfq).where(Rfq.state == "open", Rfq.closes_at <= now())).all()]
    for t, rid in due:
        try:
            _show(t, rid)
            n += 1
        except Exception:
            continue
    return n


_ = (idn, datetime)
