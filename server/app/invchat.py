"""INVESTMENTS DESK - the Investments & Wealth employee's own section, like Payments, Firm Practice and Institution (owner: "NOW LETS WORK
ON NEXT EMPLOYEE INVESTMENTS DESK").

- The Investments chat = a Conversation with kind 'investments', kept out of every Hoola chat list (callconv.not_call); facts she tells it
  still reach her one memory. A turn in it (or a voice call started from it) gets the desk's state as a block and the investments tool
  (`investments_desk`, family investdesk) in view.
- The desk runs the F10 engine (fin/desks/investments.py) on any of her finance workspaces (a person, her own work, a business, a firm or a
  fund - the engine serves all of them). A team member someone put on a business reads (auditor / viewer) or changes (owner / accountant /
  approver) it, the same as Books & Accounts.
- The engine is stateless; the desk keeps her data in the workspace's settings under `investments_desk`:
    trades     her buys and sells (form or her broker's CSV) -> the capital gains by tax lot in her country's method, by tax year
    holdings   what she holds at the price SHE gives (form, CSV, or built from her trades) -> value, weights, allocation, over her limit,
               and the losses she could realise with the wash / superficial window from her own recent buys
    positions  options and futures -> the most she can lose, the break-even, a 1% move; her past results
    plans      the fee-cost and retirement-drawdown plans, at the return and inflation SHE assumes (Hoola never assumes one)
    scams      offers she checked (signs + the firm against the register entries she pasted)
    funds      NAV checks for a fund she administers, kept as a history
- Hoola never places, changes or cancels an order and never says what to buy or sell. Not investment advice.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.invchat")

KIND = "investments"
KEY = "investments_desk"       # the Hub employee
TOOL = "investments_desk"      # its tool
FAMILIES = ["investdesk"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FOOT = ("Hoola works out the numbers on your investments. It never places, changes or cancels an order and never says what to buy or sell - "
        "you do, with your broker. Matching methods and tax years are Hoola's table until you check them. Not investment advice.")
WRITE = {"owner", "accountant", "approver"}
ROLE_SAY = {"owner": "Owner", "accountant": "Accountant", "approver": "Approver", "auditor": "Auditor", "viewer": "Viewer"}
SIZE_SAY = {"personal": "Me or my household", "solo": "My own work", "business": "My business", "firm": "My firm", "institution": "My fund / institution"}
CLASSES = ("shares", "funds", "bonds", "cash", "property", "crypto", "commodities", "other")
MAX_ROWS = 20000
NOT_CONFIRMED = " (Hoola's table - check this)"
TAX_YEAR = {"GB": (4, 6, "6 April to 5 April"), "IN": (4, 1, "1 April to 31 March"), "AU": (7, 1, "1 July to 30 June"),
            "NZ": (4, 1, "1 April to 31 March"), "ZA": (3, 1, "1 March to the end of February")}


class InvDeskError(ValueError):
    pass


def is_investments(conv: str) -> bool:
    if not conv:
        return False
    if conv in _OF:
        return _OF[conv]
    hit = False
    try:
        with session() as s:
            c = s.get(Conversation, conv)
            if c is not None:
                if (c.kind or "") == KIND:
                    hit = True
                elif (c.kind or "") == "call" and c.origin_conv:
                    o = s.get(Conversation, c.origin_conv)
                    hit = bool(o is not None and (o.kind or "") == KIND)
    except Exception:   # noqa: BLE001
        log.exception("investments chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _hire():
    from .employee import hire
    return hire


def portfolios(tenant: str) -> list[dict[str, Any]]:
    """Every finance workspace of hers (any size: the engine serves a person up to a fund) and the ones other people put her on."""
    from .fin import profile as PR
    from .fin.desks import books_ent as E
    own = [{"id": w["id"], "name": w["name"] or "My investments", "size": w["size"], "currency": w["currency"],
            "countries": w["countries"], "role": "owner"} for w in PR.workspaces(tenant)]
    try:
        return own + E.shared_with(tenant)
    except Exception:   # noqa: BLE001
        log.exception("shared workspaces read failed")
        return own


def workspace(tenant: str, want: str = "") -> dict[str, Any] | None:
    bs = portfolios(tenant)
    if not want:
        try:
            want = str(_hire().settings(tenant, KEY).get("workspace") or "")
        except Exception:   # noqa: BLE001
            want = ""
    for b in bs:
        if b["id"] == want:
            return b
    return bs[0] if bs else None


def pick(tenant: str, ws: str) -> dict[str, Any]:
    if not any(b["id"] == ws for b in portfolios(tenant)):
        raise InvDeskError("No such portfolio.")
    try:
        _hire().save_settings(tenant, KEY, workspace=ws)
    except Exception:   # noqa: BLE001
        pass
    forget(tenant)
    return {"workspace": ws}


def setup(tenant: str, a: dict[str, Any]) -> dict[str, Any]:
    """A first portfolio when she has no finance workspace yet: a name, her country and currency, and who it is for."""
    from .fin import profile as PR
    name = str(a.get("name") or "").strip()[:80] or "My investments"
    cc = str(a.get("country") or "").strip().upper()
    cur = str(a.get("currency") or "").strip().upper()
    size = str(a.get("size") or "personal")
    if size not in PR.SIZES:
        raise InvDeskError("size: " + ", ".join(PR.SIZE_ORDER))
    if len(cc) != 2 or len(cur) != 3:
        raise InvDeskError("country (two letters, like GB) and currency (three letters, like GBP).")
    pv = PR.preview({"size": size, "countries": [cc], "currency": cur, "name": name, "wants": []})
    w = PR.apply(tenant, pv["answers"], pv["hash"])
    pick(tenant, w["id"])
    _regreet(tenant)
    return {"portfolio": {"id": w["id"], "name": w["name"]}}


def _regreet(tenant: str) -> None:
    try:
        hi = greeting(tenant)
        with session() as s:
            for c in s.scalars(_q(tenant)).all():
                if s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user")):
                    continue
                for m in s.scalars(select(Message).where(Message.conversation_id == c.id, Message.role == "assistant")).all():
                    m.content = m.display = hi
            s.commit()
    except Exception:   # noqa: BLE001
        log.exception("investments chat greeting refresh failed")


# ---------------------------------------------------------------- desk state
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _wsrow(owner: str, ws: str) -> dict[str, Any]:
    from .fin import profile as PR
    return PR.get(owner, ws)


def _state(owner: str, ws: str) -> dict[str, Any]:
    st = dict((_wsrow(owner, ws).get("settings") or {}).get("investments_desk") or {})
    for k, v in (("trades", []), ("holdings", []), ("positions", []), ("results", []), ("scams", []), ("funds", []), ("files", []),
                 ("country", ""), ("method", ""), ("rule_days", None), ("max_pct", None), ("prices_on", ""),
                 ("assume", {}), ("fee_plan", {}), ("retire_plan", {}), ("targets", {})):
        st.setdefault(k, v)
    return st


def _put(owner: str, ws: str, st: dict[str, Any]) -> None:
    from . import db
    from .fin.models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != owner:
            raise InvDeskError("No such portfolio.")
        cur = json.loads(row.settings or "{}")
        cur["investments_desk"] = st
        row.settings = json.dumps(cur)
        s.commit()


def _num(v: Any, what: str, lo: float | None = None) -> float:
    try:
        x = float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        raise InvDeskError(f"{what}: a number.")
    if x != x or x in (float("inf"), float("-inf")):
        raise InvDeskError(f"{what}: a number.")
    if lo is not None and x < lo:
        raise InvDeskError(f"{what}: not below {lo:g}.")
    return x


def _opt(v: Any, what: str, lo: float | None = None) -> float | None:
    return None if v in (None, "") else _num(v, what, lo)


def _day(v: Any, what: str) -> str:
    try:
        return date.fromisoformat(str(v).strip()[:10]).isoformat()
    except ValueError:
        raise InvDeskError(f"{what}: a date as YYYY-MM-DD.")


def _text(v: Any, n: int = 80) -> str:
    return str(v or "").strip()[:n]


def _next_n(rows: list[dict[str, Any]]) -> int:
    return 1 + max([int(x.get("n") or 0) for x in rows] or [0])


def _find(rows: list[dict[str, Any]], n: Any, what: str) -> dict[str, Any]:
    for x in rows:
        if int(x.get("n") or 0) == int(_num(n, "n")):
            return x
    raise InvDeskError(f"No such {what}.")


def _country(owner: str, ws: str, st: dict[str, Any]) -> str:
    return (st.get("country") or ((_wsrow(owner, ws).get("countries") or [""])[0]) or "").upper()


def _engine(owner: str, me: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin import core
    from .fin.desks import investments as IV
    try:
        return core.run_tool(owner, me, TOOL, action, dict(a), lambda: IV.run(owner, action, a, me))
    except IV.InvestError as e:
        raise InvDeskError(str(e))


def tax_year(country: str, d: str) -> str:
    """The tax year a date falls in, by Hoola's table (the calendar year where her country is not in it)."""
    dd = date.fromisoformat(d[:10])
    m = TAX_YEAR.get(country)
    if not m:
        return str(dd.year)
    start = date(dd.year, m[0], m[1])
    y = dd.year if dd >= start else dd.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def tax_year_says(country: str) -> str:
    m = TAX_YEAR.get(country)
    return (m[2] if m else "the calendar year") + NOT_CONFIRMED


# ---------------------------------------------------------------- CSV files she uploads (her broker's export)
_ALIAS = {
    "date": ("date", "trade date", "settlement date", "transaction date", "deal date", "time", "executed"),
    "side": ("side", "type", "action", "buy/sell", "transaction type", "direction", "b/s"),
    "symbol": ("symbol", "ticker", "instrument", "security", "stock", "code", "isin", "name", "scrip"),
    "qty": ("qty", "quantity", "shares", "units", "amount of shares", "no. of shares", "volume"),
    "price": ("price", "trade price", "unit price", "price per share", "rate", "avg price", "last price", "market price", "ltp"),
    "fees": ("fees", "fee", "commission", "charges", "brokerage", "costs"),
    "cost": ("cost", "book cost", "total cost", "cost basis", "invested", "buy value", "purchase value"),
    "asset_class": ("asset_class", "class", "asset class", "type", "category", "asset type"),
}
_SIDE = {"buy": "buy", "b": "buy", "bought": "buy", "purchase": "buy", "sell": "sell", "s": "sell", "sold": "sell", "sale": "sell"}


def _read_csv(text: str, want: list[str], need: list[str]) -> list[dict[str, Any]]:
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        raise InvDeskError("The file is empty.")
    head = [c.strip().lower() for c in rows[0]]
    col: dict[str, int] = {}
    for k in want:
        for alias in _ALIAS.get(k, (k,)):
            if alias in head and head.index(alias) not in col.values():
                col[k] = head.index(alias)
                break
    miss = [k for k in need if k not in col]
    if miss:
        raise InvDeskError("These columns were not found: " + ", ".join(miss) + ". The first line should name the columns.")
    out = []
    for r in rows[1:MAX_ROWS + 1]:
        out.append({k: (r[i].strip() if i < len(r) else "") for k, i in col.items()})
    return out


def _clean_trade(t: dict[str, Any], i: str) -> dict[str, Any]:
    side = _SIDE.get(str(t.get("side") or "").strip().lower())
    if not side:
        raise InvDeskError(f"{i}: side buy or sell.")
    q = abs(_num(t.get("qty"), f"{i} quantity"))
    if q <= 0:
        raise InvDeskError(f"{i}: a quantity above 0.")
    sym = _text(t.get("symbol"), 40).upper()
    if not sym:
        raise InvDeskError(f"{i}: the symbol.")
    return {"date": _day(t.get("date"), f"{i} date"), "side": side, "symbol": sym, "qty": q, "price": abs(_num(t.get("price"), f"{i} price")),
            "fees": abs(_num(t.get("fees") or 0, f"{i} fees"))}


def _clean_hold(h: dict[str, Any], i: str) -> dict[str, Any]:
    sym = _text(h.get("symbol"), 40).upper()
    if not sym:
        raise InvDeskError(f"{i}: the symbol.")
    cls = _text(h.get("asset_class"), 20).lower()
    cls = {"equity": "shares", "stock": "shares", "stocks": "shares", "share": "shares", "etf": "funds", "fund": "funds", "mutual fund": "funds",
           "bond": "bonds", "gilt": "bonds", "fixed income": "bonds", "debt": "bonds", "gold": "commodities", "cash": "cash"}.get(cls, cls)
    return {"symbol": sym, "qty": _num(h.get("qty"), f"{i} quantity", 0), "price": _num(h.get("price"), f"{i} price", 0),
            "cost": _opt(h.get("cost"), f"{i} cost", 0), "asset_class": cls if cls in CLASSES else "other"}


def upload(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    kind = str(a.get("kind") or "")
    text = str(a.get("text") or "")
    if len(text) > 8_000_000:
        raise InvDeskError("Up to 8 MB.")
    st = _state(owner, ws)
    if kind == "trades":
        raw = _read_csv(text, ["date", "side", "symbol", "qty", "price", "fees"], ["date", "side", "symbol", "qty", "price"])
        rows, skipped = [], 0
        for j, r in enumerate(raw):
            try:
                rows.append(_clean_trade(r, f"line {j + 2}"))
            except InvDeskError:
                skipped += 1
        if not rows:
            raise InvDeskError("No buy or sell line could be read: each line needs a date, buy or sell, a symbol, a quantity and a price.")
        n = _next_n(st["trades"])
        seen = {(t["date"], t["side"], t["symbol"], t["qty"], t["price"]) for t in st["trades"]}
        added = 0
        for r in rows:
            k = (r["date"], r["side"], r["symbol"], r["qty"], r["price"])
            if k in seen:
                continue
            seen.add(k)
            st["trades"].append({"n": n, **r, "src": "file"})
            n += 1
            added += 1
        say = f"{added} trades added" + (f", {len(rows) - added} already on the desk" if len(rows) > added else "") + (
            f", {skipped} lines could not be read" if skipped else "")
    elif kind == "holdings":
        raw = _read_csv(text, ["symbol", "qty", "price", "cost", "asset_class"], ["symbol", "qty", "price"])
        rows, skipped = [], 0
        for j, r in enumerate(raw):
            try:
                rows.append(_clean_hold(r, f"line {j + 2}"))
            except InvDeskError:
                skipped += 1
        if not rows:
            raise InvDeskError("No holding could be read: each line needs a symbol, a quantity and a price.")
        n = 1
        st["holdings"] = [{"n": n + i, **r, "src": "file"} for i, r in enumerate(rows)]
        st["prices_on"] = _day(a.get("prices_on") or date.today().isoformat(), "prices_on")
        say = f"{len(rows)} holdings read" + (f", {skipped} lines could not be read" if skipped else "")
    else:
        raise InvDeskError("kind: trades | holdings")
    st["files"] = (st["files"] + [{"kind": kind, "name": _text(a.get("name"), 80) or "file.csv", "rows": len(rows), "by": me, "on": _now()}])[-30:]
    _put(owner, ws, st)
    return {"rows": len(rows), "says": say}


# ---------------------------------------------------------------- her registers
def trade_add(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    t = _clean_trade(a, "the trade")
    st["trades"].append({"n": _next_n(st["trades"]), **t, "src": "form", "by": me})
    _put(owner, ws, st)
    return {"trade": st["trades"][-1]}


def hold_add(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    h = _clean_hold(a, "the holding")
    old = next((x for x in st["holdings"] if x["symbol"] == h["symbol"]), None)
    if old:
        old.update(h)
    else:
        st["holdings"].append({"n": _next_n(st["holdings"]), **h, "src": "form"})
    if a.get("prices_on"):
        st["prices_on"] = _day(a["prices_on"], "prices_on")
    _put(owner, ws, st)
    return {"holdings": len(st["holdings"])}


def price_set(owner: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    """New prices for what she holds (she gives them; Hoola fetches no price)."""
    st = _state(owner, ws)
    prices = a.get("prices") or {}
    if not isinstance(prices, dict) or not prices:
        raise InvDeskError("prices: {symbol: price}.")
    hit = 0
    for h in st["holdings"]:
        v = prices.get(h["symbol"])
        if v not in (None, ""):
            h["price"] = _num(v, f"{h['symbol']} price", 0)
            hit += 1
    st["prices_on"] = _day(a.get("prices_on") or date.today().isoformat(), "prices_on")
    _put(owner, ws, st)
    return {"updated": hit, "prices_on": st["prices_on"]}


def from_trades(owner: str, ws: str, me: str) -> dict[str, Any]:
    """Holdings built from what her trades leave: the quantity and the cost from the matching; the price stays hers (kept if she gave one)."""
    st = _state(owner, ws)
    g = gains(owner, ws, me)
    if g.get("error"):
        raise InvDeskError(g["error"])
    old = {h["symbol"]: h for h in st["holdings"]}
    out = []
    for h in g.get("holdings") or []:
        if h["qty"] <= 0:
            continue
        o = old.get(h["symbol"]) or {}
        out.append({"n": len(out) + 1, "symbol": h["symbol"], "qty": h["qty"], "price": o.get("price"), "cost": h["cost"],
                    "asset_class": o.get("asset_class") or "shares", "src": "trades"})
    st["holdings"] = out
    _put(owner, ws, st)
    return {"holdings": len(out), "no_price": [h["symbol"] for h in out if h["price"] is None]}


def position_add(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    kind = str(a.get("type") or "").lower()
    if kind not in ("call", "put", "future"):
        raise InvDeskError("type: call | put | future.")
    side = str(a.get("side") or "long").lower()
    if side not in ("long", "short"):
        raise InvDeskError("side: long | short.")
    p = {"type": kind, "side": side, "symbol": _text(a.get("symbol"), 40).upper(), "expiry": _day(a["expiry"], "expiry") if a.get("expiry") else "",
         "qty": _num(a.get("qty") or 1, "qty", 0), "multiplier": _num(a.get("multiplier") or 1, "multiplier", 0)}
    if kind == "future":
        p["price"] = _num(a.get("price"), "price", 0)
        p["margin"] = _opt(a.get("margin"), "margin", 0)
    else:
        p["strike"] = _num(a.get("strike"), "strike", 0)
        p["premium"] = _num(a.get("premium"), "premium", 0)
    _engine(owner, me, "derivatives", {"positions": [p]})        # refused here if the engine cannot read it
    st["positions"].append({"n": _next_n(st["positions"]), **p, "by": me, "on": _now()})
    _put(owner, ws, st)
    return {"position": st["positions"][-1]}


def remove(owner: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    reg = str(a.get("register") or "")
    if reg not in ("trades", "holdings", "positions", "scams", "funds"):
        raise InvDeskError("register: trades | holdings | positions | scams | funds")
    st = _state(owner, ws)
    if a.get("all"):
        st[reg] = []
    else:
        row = _find(st[reg], a.get("n"), reg[:-1])
        st[reg] = [x for x in st[reg] if x is not row]
    _put(owner, ws, st)
    return {"left": len(st[reg])}


def save_settings(owner: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin.desks import investments as IV
    st = _state(owner, ws)
    if "country" in a:
        cc = _text(a["country"], 2).upper()
        if cc and len(cc) != 2:
            raise InvDeskError("country: two letters, like GB.")
        st["country"] = cc
    if "method" in a:
        m = _text(a["method"], 20)
        if m and m not in ("fifo", "average", "uk_share_id"):
            raise InvDeskError("method: fifo | average | uk_share_id - or leave it empty for your country's.")
        st["method"] = m
    if "rule_days" in a:
        st["rule_days"] = int(_num(a["rule_days"], "rule_days", 0)) if a["rule_days"] not in (None, "") else None
    if "max_pct" in a:
        st["max_pct"] = _opt(a["max_pct"], "max_pct", 0)
    if "assume" in a:
        for k in ("return_pct", "inflation_pct"):
            if k in (a["assume"] or {}):
                v = (a["assume"] or {})[k]
                if v in (None, ""):
                    st["assume"].pop(k, None)
                else:
                    st["assume"][k] = _num(v, k, -50)
    if "targets" in a:
        tg = {}
        for k, v in (a["targets"] or {}).items():
            if k in CLASSES and v not in (None, ""):
                tg[k] = _num(v, f"target {k}", 0)
        if tg and abs(sum(tg.values()) - 100) > 0.5:
            raise InvDeskError(f"Your target mix adds up to {sum(tg.values()):g}% - it should add up to 100%.")
        st["targets"] = tg
    if "results" in a:
        rs = a["results"]
        rs = [x for x in rs.replace("\n", ",").split(",")] if isinstance(rs, str) else (rs or [])
        st["results"] = [_num(x, "results") for x in rs if str(x).strip()][:2000]
    if st.get("country") and st["country"] not in IV.METHODS and not st.get("method"):
        st["method_note"] = f"Hoola has no matching method for {st['country']}: choose one (first in first out, average cost or UK share matching)."
    else:
        st.pop("method_note", None)
    _put(owner, ws, st)
    return {k: st.get(k) for k in ("country", "method", "rule_days", "max_pct", "assume", "targets", "method_note")} | {"results": len(st["results"])}


# ---------------------------------------------------------------- the work
def gains(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["trades"]:
        return {"empty": True}
    country = _country(owner, ws, st)
    a: dict[str, Any] = {"country": country, "trades": st["trades"]}
    if st.get("method"):
        a["method"] = st["method"]
    if st.get("rule_days") is not None:
        a["rule_days"] = st["rule_days"]
    try:
        r = _engine(owner, me, "lots", a)
    except InvDeskError as e:
        return {"error": str(e), "country": country}
    by_year: dict[str, dict[str, float]] = defaultdict(lambda: {"gains": 0.0, "losses": 0.0, "disallowed": 0.0, "sales": 0, "proceeds": 0.0})
    for d in r.get("disposals") or []:
        y = by_year[tax_year(country, d["date"])]
        y["sales"] += 1
        y["proceeds"] += d["proceeds"]
        y["disallowed"] += d.get("disallowed") or 0
        if d["gain"] >= 0:
            y["gains"] += d["gain"]
        else:
            y["losses"] += d["gain"]
        d["tax_year"] = tax_year(country, d["date"])
    years = [{"year": k, "gains": round(v["gains"], 2), "losses": round(v["losses"], 2), "net": round(v["gains"] + v["losses"], 2),
              "disallowed": round(v["disallowed"], 2), "sales": v["sales"], "proceeds": round(v["proceeds"], 2)} for k, v in sorted(by_year.items())]
    r["years"] = years
    r["this_year"] = tax_year(country, date.today().isoformat())
    r["tax_year_is"] = tax_year_says(country)
    r["trades"] = len(st["trades"])
    return r


def gains_csv(r: dict[str, Any]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["tax year", "date", "symbol", "quantity", "proceeds", "cost", "gain", "loss not allowed now", "how matched", "held days", "term"])
    for d in r.get("disposals") or []:
        parts = d.get("parts") or [{}]
        rule = "; ".join(sorted({p.get("rule") or "" for p in parts if p.get("rule")})) or r.get("method", "")
        held = "; ".join(str(p["days_held"]) for p in parts if p.get("days_held") is not None)
        term = "; ".join(sorted({p["term"] for p in parts if p.get("term")}))
        w.writerow([d.get("tax_year", ""), d["date"], d["symbol"], d["qty"], d["proceeds"], d["cost"], d["gain"], d.get("disallowed") or 0, rule, held, term])
    w.writerow([])
    w.writerow(["Worked out by Hoola from your trades by " + str(r.get("method_from") or "") + ". The tax on these gains is not worked out."])
    return buf.getvalue().encode()


def portfolio(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    hs = [h for h in st["holdings"] if h.get("qty")]
    if not hs:
        return {"empty": True}
    priced = [h for h in hs if h.get("price") is not None]
    if not priced:
        return {"error": "Give a price for what you hold: Hoola fetches no prices.", "no_price": [h["symbol"] for h in hs]}
    a: dict[str, Any] = {"holdings": [{k: h.get(k) for k in ("symbol", "qty", "price", "cost", "asset_class")} for h in priced]}
    if st.get("max_pct") is not None:
        a["max_pct"] = st["max_pct"]
    try:
        r = _engine(owner, me, "statement", a)
    except InvDeskError as e:
        return {"error": str(e)}
    r["no_price"] = [h["symbol"] for h in hs if h.get("price") is None]
    r["prices_on"] = st.get("prices_on") or ""
    cost = sum((h.get("cost") or 0) for h in priced if h.get("cost") is not None)
    r["cost"] = round(cost, 2)
    r["unrealised_pct"] = round(r["unrealised"] / cost * 100, 2) if cost else None
    tg = st.get("targets") or {}
    if tg:
        al = r.get("allocation") or {}
        r["drift"] = [{"class": k, "target": tg.get(k, 0.0), "now": al.get(k, 0.0), "off": round(al.get(k, 0.0) - tg.get(k, 0.0), 2)}
                      for k in sorted(set(tg) | set(al))]
    return r


def harvest(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    hs = [h for h in st["holdings"] if h.get("qty") and h.get("price") is not None and h.get("cost") is not None]
    if not hs:
        return {"empty": True}
    country = _country(owner, ws, st)
    a = {"country": country, "today": date.today().isoformat(),
         "holdings": [{k: h[k] for k in ("symbol", "qty", "price", "cost")} for h in hs],
         "recent_buys": [{"symbol": t["symbol"], "date": t["date"]} for t in st["trades"] if t["side"] == "buy"]}
    if st.get("rule_days") is not None:
        a["rule_days"] = st["rule_days"]
    try:
        return _engine(owner, me, "harvest", a)
    except InvDeskError as e:
        return {"error": str(e)}


def risk(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["positions"] and not st["results"]:
        return {"empty": True}
    ps = [{k: v for k, v in p.items() if k not in ("n", "by", "on", "symbol", "expiry")} for p in st["positions"]]
    try:
        r = _engine(owner, me, "derivatives", {"positions": ps, "results": st["results"]}) if ps or st["results"] else {"positions": []}
    except InvDeskError as e:
        return {"error": str(e)}
    for out, p in zip(r.get("positions") or [], st["positions"]):
        out.update({"n": p["n"], "symbol": p.get("symbol") or "", "expiry": p.get("expiry") or "", "qty": p["qty"], "multiplier": p["multiplier"],
                    "strike": p.get("strike"), "premium": p.get("premium"), "price": p.get("price"), "margin": p.get("margin")})
        if p.get("expiry"):
            out["days_left"] = (date.fromisoformat(p["expiry"]) - date.today()).days
    r["unlimited"] = [x["n"] for x in r.get("positions") or [] if x.get("most_you_can_lose") in ("unlimited", "more than your margin", "the whole notional")]
    return r


def plan(owner: str, ws: str, me: str, a: dict[str, Any]) -> dict[str, Any]:
    """The fee-cost or the retirement-drawdown plan at HER assumptions; what she typed is kept for next time."""
    st = _state(owner, ws)
    which = str(a.get("which") or "")
    asm = dict(st.get("assume") or {})
    for k in ("return_pct", "inflation_pct"):
        if a.get(k) not in (None, ""):
            asm[k] = _num(a[k], k, -50)
    if which == "fees":
        keep = {k: a[k] for k in ("amount", "years", "fee_pct", "platform_pct", "entry_pct") if a.get(k) not in (None, "")}
        if "amount" not in keep and st.get("holdings"):
            p = portfolio(owner, ws, me)
            if p.get("total"):
                keep["amount"] = p["total"]
        st["fee_plan"] = keep
        if asm.get("return_pct") is None:
            raise InvDeskError("Your yearly return assumption first: Hoola never assumes one.")
        args = {"return_pct": asm["return_pct"], **{k: v for k, v in keep.items()}}
        args.setdefault("years", 20)
        r = _engine(owner, me, "fees", args)
    elif which == "retire":
        keep = {k: a[k] for k in ("pot", "withdraw", "years") if a.get(k) not in (None, "")}
        if "pot" not in keep and st.get("holdings"):
            p = portfolio(owner, ws, me)
            if p.get("total"):
                keep["pot"] = p["total"]
        st["retire_plan"] = keep
        for k in ("return_pct", "inflation_pct"):
            if asm.get(k) is None:
                raise InvDeskError(f"Your {'return' if k == 'return_pct' else 'inflation'} assumption first: Hoola never assumes one.")
        r = _engine(owner, me, "retirement", {"return_pct": asm["return_pct"], "inflation_pct": asm["inflation_pct"], **keep})
    else:
        raise InvDeskError("which: fees | retire")
    st["assume"] = asm
    _put(owner, ws, st)
    r["kept"] = keep
    return r


def scam_check(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    text, firm = str(a.get("text") or "")[:20000], _text(a.get("firm"), 120)
    reg = a.get("register")
    if isinstance(reg, str):
        reg = [{"name": x.strip()} for x in reg.splitlines() if x.strip()]
    args: dict[str, Any] = {"text": text, "firm": firm, "country": _country(owner, ws, st)}
    if reg:
        args["register"] = reg[:500]
    r = _engine(owner, me, "scam", args)
    st["scams"] = (st["scams"] + [{"n": _next_n(st["scams"]), "on": _now(), "firm": firm, "excerpt": text[:240], "flags": r["flags"],
                                   "level": r["level"], "on_register": r.get("on_your_register"), "by": me}])[-60:]
    _put(owner, ws, st)
    r["n"] = st["scams"][-1]["n"]
    return r


def _lines(v: Any, what: str) -> list[dict[str, Any]]:
    if isinstance(v, list):
        return [{"name": _text(x.get("name"), 60), "value": _num(x.get("value"), what)} for x in v if isinstance(x, dict)]
    out = []
    for ln in str(v or "").splitlines():
        if not ln.strip():
            continue
        name, _, val = ln.rpartition(",")
        out.append({"name": name.strip()[:60] or "item", "value": _num(val, what)})
    return out


def nav(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    assets, liab = _lines(a.get("assets"), "assets"), _lines(a.get("liabilities"), "liabilities")
    if not assets:
        raise InvDeskError("assets: one line each, name, value.")
    args: dict[str, Any] = {"assets": assets, "liabilities": liab, "units": _num(a.get("units"), "units", 0)}
    for k in ("reported_nav", "tolerance_bp"):
        if a.get(k) not in (None, ""):
            args[k] = _num(a[k], k, 0)
    r = _engine(owner, me, "nav_check", args)
    fund = _text(a.get("fund"), 80) or "Fund"
    st["funds"] = (st["funds"] + [{"n": _next_n(st["funds"]), "fund": fund, "on": _now(), "as_of": _day(a.get("as_of") or date.today().isoformat(), "as_of"),
                                   "units": args["units"], "assets": assets, "liabilities": liab, "by": me,
                                   **{k: r.get(k) for k in ("net_assets", "nav_per_unit", "reported", "difference_bp", "break", "tolerance_bp")}}])[-200:]
    _put(owner, ws, st)
    r["n"] = st["funds"][-1]["n"]
    return r


# ---------------------------------------------------------------- today
def today_view(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    country = _country(owner, ws, st)
    cur = str(_wsrow(owner, ws).get("currency") or "").upper()
    from .fin.desks import investments as IV
    m = IV.METHODS.get(country) or {}
    out: dict[str, Any] = {
        "country": country, "method": st.get("method") or "", "method_name": ("your own: " + st["method"]) if st.get("method") else (
            (m.get("name", "") + NOT_CONFIRMED) if m else ""), "method_note": st.get("method_note") or "",
        "rule_days": st.get("rule_days"), "max_pct": st.get("max_pct"), "assume": st.get("assume") or {}, "targets": st.get("targets") or {},
        "fee_plan": st.get("fee_plan") or {}, "retire_plan": st.get("retire_plan") or {}, "prices_on": st.get("prices_on") or "",
        "trades": sorted(st["trades"], key=lambda t: (t["date"], t["n"]), reverse=True)[:400], "trades_count": len(st["trades"]),
        "holdings": st["holdings"], "positions_count": len(st["positions"]), "results_count": len(st["results"]),
        "results": st["results"][-200:],
        "scams": list(reversed(st["scams"]))[:20], "funds": list(reversed(st["funds"]))[:40], "files": list(reversed(st["files"]))[:12],
        "classes": list(CLASSES), "methods": {k: v["name"] for k, v in IV.METHODS.items()}, "tax_year_is": tax_year_says(country),
    }
    g = gains(owner, ws, me)
    out["gains"] = {k: g.get(k) for k in ("empty", "error", "gains", "losses", "net", "disallowed_losses", "years", "this_year", "method_from", "by_term")}
    p = portfolio(owner, ws, me)
    out["portfolio"] = p
    h = harvest(owner, ws, me)
    out["harvest"] = {k: h.get(k) for k in ("empty", "error", "total")} | {"losses": (h.get("losses") or [])[:20]}
    rk = risk(owner, ws, me)
    out["risk"] = {"empty": rk.get("empty"), "error": rk.get("error"), "unlimited": rk.get("unlimited") or [],
                   "soon": [x for x in rk.get("positions") or [] if x.get("days_left") is not None and 0 <= x["days_left"] <= 14],
                   "results": rk.get("your_results")}
    needs = []
    if not country:
        needs.append({"say": "Choose your country so Hoola matches your sales the way your tax rules do", "go": "settings", "bad": True})
    elif not m and not st.get("method"):
        needs.append({"say": f"Hoola has no matching method for {country}: choose one in Settings", "go": "settings", "bad": True})
    if g.get("error"):
        needs.append({"say": "Your trades could not be matched: " + g["error"], "go": "gains", "bad": True})
    this = next((y for y in g.get("years") or [] if y["year"] == g.get("this_year")), None)
    if this and this["sales"]:
        needs.append({"say": f"This tax year ({this['year']}): {this['sales']} sale{'' if this['sales'] == 1 else 's'}, net {'gain' if this['net'] >= 0 else 'loss'} {cur} {abs(this['net']):,.2f}",
                      "go": "gains"})
    if g.get("disallowed_losses"):
        needs.append({"say": f"{cur} {g['disallowed_losses']:,.2f} of losses do not count yet - the buy-back rule moved them into your new shares", "go": "gains"})
    if p.get("no_price"):
        needs.append({"say": f"{len(p['no_price'])} holding{' has' if len(p['no_price']) == 1 else 's have'} no price: {', '.join(p['no_price'][:5])}", "go": "portfolio", "bad": True})
    if p.get("prices_on"):
        age = (date.today() - date.fromisoformat(p["prices_on"])).days
        if age > 7:
            needs.append({"say": f"Your prices are from {p['prices_on']} ({age} days ago) - update them for a true value", "go": "portfolio"})
    for s in (p.get("over_your_limit") or [])[:4]:
        w = next((x["weight_pct"] for x in p.get("holdings") or [] if x["symbol"] == s), None)
        needs.append({"say": f"{s} is {w}% of the portfolio - over your {st.get('max_pct'):g}% limit", "go": "portfolio", "bad": True})
    for d in (p.get("drift") or []):
        if abs(d["off"]) >= 5:
            needs.append({"say": f"{d['class'].title()}: {d['now']:g}% now, your target {d['target']:g}%", "go": "portfolio"})
    if not p.get("empty") and st.get("max_pct") is None:
        needs.append({"say": "Set your concentration limit to see positions that are too big", "go": "settings"})
    for x in out["risk"]["soon"][:4]:
        needs.append({"say": f"{x['type'].title()} #{x['n']} {x['symbol']} expires in {x['days_left']} day{'' if x['days_left'] == 1 else 's'}", "go": "derivatives"})
    if out["risk"]["unlimited"]:
        n_ = len(out["risk"]["unlimited"])
        needs.append({"say": f"{n_} position{'s' if n_ > 1 else ''} can lose more than you put in", "go": "derivatives", "bad": True})
    br = [f for f in st["funds"][-20:] if f.get("break")]
    if br:
        needs.append({"say": f"NAV break on {br[-1]['fund']} ({br[-1]['as_of']}): {br[-1]['difference_bp']} bp from the reported NAV", "go": "funds", "bad": True})
    out["needs"] = needs
    return out


def summary(tenant: str, want: str = "") -> dict[str, Any]:
    from .fin.desks import books_ent as E
    h = _hire()
    st = h.status(tenant, KEY)
    trust = ""
    if st not in ("hired", "paused"):
        try:
            shared = E.shared_with(tenant)
        except Exception:   # noqa: BLE001
            shared = []
        if not shared:
            return {"hired": False, "status": st, "say": "Investments & Wealth is not hired. Hire it from AI Employees."}
    else:
        with session() as s:
            trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    out: dict[str, Any] = {"hired": True, "status": st if st in ("hired", "paused") else "member",
                           "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
                           "portfolios": portfolios(tenant), "workspace": workspace(tenant, want), "roles": ROLE_SAY, "sizes": SIZE_SAY,
                           "foot": FOOT}
    w = out["workspace"]
    if w:
        try:
            acc = E.access(tenant, w["id"])
            out["role"] = acc["role"]
            out["can_write"] = acc["role"] in WRITE
            out["desk"] = today_view(acc["owner"], w["id"], f"{acc['name']} <{tenant}>")
        except Exception as e:   # noqa: BLE001
            log.exception("investments desk read failed")
            out["desk_error"] = str(e)[:200]
    return out


READS = {"gains", "portfolio", "harvest", "risk", "methods"}


def do(caller: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin.desks import books_ent as E
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    ws = str(a.get("workspace") or "")
    acc = E.access(caller, ws)
    role, owner = acc["role"], acc["owner"]
    me = f"{acc['name']} <{caller}>"
    if part not in READS and role not in WRITE:
        raise InvDeskError(f"Your role ({ROLE_SAY.get(role, role)}) can read this desk but not change it.")
    f = {
        "gains": lambda: gains(owner, ws, me), "portfolio": lambda: portfolio(owner, ws, me), "harvest": lambda: harvest(owner, ws, me),
        "risk": lambda: risk(owner, ws, me), "methods": lambda: _engine(owner, me, "methods", {}),
        "upload": lambda: upload(owner, ws, a, me), "trade": lambda: trade_add(owner, ws, a, me), "hold": lambda: hold_add(owner, ws, a, me),
        "prices": lambda: price_set(owner, ws, a), "from_trades": lambda: from_trades(owner, ws, me),
        "position": lambda: position_add(owner, ws, a, me), "remove": lambda: remove(owner, ws, a),
        "settings": lambda: save_settings(owner, ws, a), "plan": lambda: plan(owner, ws, me, a),
        "scam": lambda: scam_check(owner, ws, a, me), "nav": lambda: nav(owner, ws, a, me),
    }.get(part)
    if f is None:
        raise InvDeskError("Not an Investments desk action.")
    out = f()
    if part not in READS:
        forget(owner)
        forget(caller)
    return out


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- the chat
def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def greeting(tenant: str) -> str:
    d = summary(tenant)
    if not d.get("hired"):
        return ("I work out the numbers on your investments: capital gains by tax lot, what your fees cost, how long a pot lasts. Hire me from "
                "AI Employees to start.")
    if not d.get("workspace"):
        return "Hello. Set up your portfolio on the desk (a name, your country and currency), then drop your broker's file here."
    k = d.get("desk") or {}
    bits = []
    if (k.get("portfolio") or {}).get("total"):
        bits.append(f"{len(k['portfolio']['holdings'])} holdings")
    if k.get("trades_count"):
        bits.append(f"{k['trades_count']} trades")
    if k.get("positions_count"):
        bits.append(f"{k['positions_count']} option / future position(s)")
    return ("Hello. " + ("On this desk: " + ", ".join(bits) + ". " if bits else "")
            + "Drop your broker's trades or holdings file here, ask what a sale means for your gains this tax year, or paste an offer to check "
              "it for scam signs. I never place orders or say what to buy or sell.")


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Investments chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


RULES = ("You are her Investments & Wealth employee, talking in the desk's own chat (or a voice call started from it). Use the " + TOOL +
         " tool: lots (capital gains by tax lot from her trades in her country's method, or the method she names), statement (value, weights, "
         "allocation, over her concentration limit), fees (what yearly charges cost at the return SHE assumes), harvest (unrealised losses + the "
         "wash / superficial window from her recent buys), derivatives (the most she can lose, the break-even, a 1% move), scam (signs in an offer + "
         "the firm against register entries she pasted), retirement (how long a pot lasts at her withdrawal, return and inflation), nav_check (a "
         "fund's NAV per unit). Every figure you say comes from the tool or the desk below - never estimate one, never fetch or guess a price, "
         "never assume a return. Matching methods, holding periods and tax years are Hoola's from memory: say 'check this with your tax rules'. "
         "The tax on a gain is not worked out (it needs her rate and allowances). Hoola never places, changes or cancels an order and never says "
         "what to buy, sell or hold - say so plainly if she asks. Never ask for or keep a password, a PIN or a broker login. Plain English, short. "
         "Not investment or tax advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<investments_desk>{RULES}Investments & Wealth is not hired yet: tell her to hire it from AI Employees.</investments_desk>"
        elif not d.get("workspace"):
            txt = f"\n\n<investments_desk>{RULES}\nNo portfolio set up yet: ask her to set it up on the desk.</investments_desk>"
        else:
            w, k = d["workspace"], d.get("desk") or {}
            p, g = k.get("portfolio") or {}, k.get("gains") or {}
            hs = "; ".join(f"{x['symbol']} {x['value']:,.2f} ({x['weight_pct']}%)" for x in (p.get("holdings") or [])[:15]) or "none"
            ys = "; ".join(f"{y['year']}: net {y['net']:,.2f} from {y['sales']} sale(s)" for y in (g.get("years") or [])[-4:]) or "no sales"
            txt = (f"\n\n<investments_desk>{RULES}\nPortfolio: {w['name']} (workspace {w['id']}), country {k.get('country') or 'not set'}, "
                   f"currency {w['currency']}. Matching: {k.get('method_name') or 'not set'}. Tax year: {k.get('tax_year_is')}."
                   f"\nValue: {p.get('total', 'no priced holdings')} (prices from {k.get('prices_on') or 'unknown'}); unrealised {p.get('unrealised', '-')}."
                   f"\nHoldings: {hs}.\nAllocation: {json.dumps(p.get('allocation') or {})}. Over her limit: {', '.join(p.get('over_your_limit') or []) or 'none'}."
                   f"\nTrades on the desk: {k.get('trades_count', 0)}. Gains by tax year: {ys}. Losses not allowed now: {g.get('disallowed_losses') or 0}."
                   f"\nUnrealised losses she could look at: {(k.get('harvest') or {}).get('total') or 0}."
                   f"\nOption / future positions: {k.get('positions_count', 0)}. Her assumptions: {json.dumps(k.get('assume') or {})}."
                   + (f"\nShe is the {d.get('role')} on this portfolio (someone else owns it): explain from these figures and send her "
                      "to the desk for changes." if d.get("role") not in (None, "owner") else "")
                   + "</investments_desk>")
    except Exception:   # noqa: BLE001
        log.exception("investments block failed")
        txt = f"\n\n<investments_desk>{RULES}The desk could not be read just now.</investments_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/investments/chat", dependencies=dep)
    def inv_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/investments/chat/new", dependencies=dep)
    def inv_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/investments/chat/{conv}/ok", dependencies=dep)
    def inv_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Investments chat")
        return {"ok": True}

    @router.get("/api/investments/desk", dependencies=dep)
    def inv_desk(workspace: str = "", tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant, workspace)

    @router.post("/api/investments/setup", dependencies=dep)
    def inv_setup(body: dict | None = None, tenant: str = Depends(current_tenant)):
        try:
            return setup(tenant, body or {})
        except ValueError as e:
            raise HTTPException(400, str(e))

    @router.post("/api/investments/do/{part}", dependencies=dep)
    def inv_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin import laws as L
        try:
            return do(tenant, part, body or {})
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except PermissionError as e:
            raise HTTPException(403, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    @router.get("/api/investments/download", dependencies=dep)
    def inv_download(workspace: str, what: str = "gains", tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        from .fin.desks import books_ent as E
        try:
            acc = E.access(tenant, workspace)
            me = f"{acc['name']} <{tenant}>"
            if what == "gains":
                r = gains(acc["owner"], workspace, me)
                if r.get("empty") or r.get("error"):
                    raise InvDeskError(r.get("error") or "No trades on the desk yet.")
                return Response(gains_csv(r), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="capital-gains.csv"'})
            if what == "holdings":
                st = _state(acc["owner"], workspace)
                buf = io.StringIO()
                wr = csv.writer(buf)
                wr.writerow(["symbol", "qty", "price", "cost", "asset_class"])
                for h in st["holdings"]:
                    wr.writerow([h["symbol"], h["qty"], h.get("price") if h.get("price") is not None else "", h.get("cost") if h.get("cost") is not None else "",
                                 h.get("asset_class") or ""])
                return Response(buf.getvalue().encode(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="holdings.csv"'})
        except ValueError as e:
            raise HTTPException(400, str(e))
        raise HTTPException(400, "what: gains | holdings")

    @router.put("/api/investments/workspace", dependencies=dep)
    def inv_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except InvDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
