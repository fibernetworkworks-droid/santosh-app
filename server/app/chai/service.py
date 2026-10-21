"""v0.84 Chai Sahayak: a chai stall's coworker.

  1. Gets the job: she tells Hoola (chat / call) or forwards a statement / a payment alert / a supplier's bill.
  2. Counts the day's sales from UPI alerts (Galla: her phone reads only payment apps' 'money received' alerts) plus the
     cash she tells.
  3. Shows the best-selling hour, checked against earlier work (same weekday in the last weeks, yesterday).
  4. Plans milk, sugar and tea patti for tomorrow from her menu (what one cup takes), the same weekday's sales,
     tomorrow's holiday / rain / heat, what is left, and her own rules; milk rounded to her packet size.
  5. Waits for her Haan on ordering stock: a card per supplier (WhatsApp draft to her doodhwala, or Order karo on a
     site for sugar / patti that stops at payment). Hoola prepares, she decides; money is always hers.
  6. Delivers and learns: next morning "kitna doodh bacha / kab khatam hua" teaches how much milk a cup really takes
     (milk factor) and how much of her sales is cash; the chat turn itself is learned as a procedure (v0.64).
"""
from __future__ import annotations

import json
import logging
import math
import re
import statistics
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from ..galla import service as galla

log = logging.getLogger("santosh.chai")

DEFAULT_MENU = [
    {"name": "Chai", "price": 10, "milk_ml": 50, "sugar_g": 8, "tea_g": 2.5, "share": 70},
    {"name": "Special / adrak chai", "price": 15, "milk_ml": 80, "sugar_g": 10, "tea_g": 3, "share": 20},
    {"name": "Coffee", "price": 20, "milk_ml": 110, "sugar_g": 10, "tea_g": 0, "share": 10},
]


class ChaiError(Exception):
    pass


class ChaiSettings(Base):
    __tablename__ = "chai_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    stall_name: Mapped[str] = mapped_column(String(120), default="")
    menu: Mapped[str] = mapped_column(Text, default="")
    other_pct: Mapped[int] = mapped_column(Integer, default=20)         # % of sales that is not chai (biscuit, snacks...)
    cash_pct: Mapped[float] = mapped_column(Float, default=40.0)       # % of sales paid in cash (learned)
    cash_learned: Mapped[int] = mapped_column(Integer, default=0)
    milk_factor: Mapped[float] = mapped_column(Float, default=1.0)     # real milk per cup / menu milk per cup (learned)
    factor_learned: Mapped[int] = mapped_column(Integer, default=0)
    safety_pct: Mapped[int] = mapped_column(Integer, default=10)
    milk_packet_ml: Mapped[int] = mapped_column(Integer, default=500)
    typical_cups: Mapped[int] = mapped_column(Integer, default=0)      # her own guess until sales history exists
    stock: Mapped[str] = mapped_column(Text, default="{}")             # {milk_l, sugar_kg, tea_kg, at}
    suppliers: Mapped[str] = mapped_column(Text, default="[]")         # [{name, phone, items: [milk|sugar|tea], site}]
    rules: Mapped[str] = mapped_column(Text, default="[]")
    plan_time: Mapped[str] = mapped_column(String(5), default="20:00")
    last_plan: Mapped[str] = mapped_column(String(10), default="")


class ChaiPlan(Base):
    __tablename__ = "chai_plans"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    for_date: Mapped[str] = mapped_column(String(10), index=True)
    cups: Mapped[int] = mapped_column(Integer, default=0)
    sales_paise: Mapped[int] = mapped_column(Integer, default=0)
    need: Mapped[str] = mapped_column(Text, default="{}")              # {milk_l, sugar_kg, tea_kg} for the day
    buy: Mapped[str] = mapped_column(Text, default="{}")               # what to buy
    reasons: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="draft")   # draft | done
    feedback: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class StockOrder(Base):
    __tablename__ = "chai_stock_orders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cso"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    plan_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    supplier: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    site: Mapped[str] = mapped_column(String(40), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")             # [{item, qty, unit}]
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="pending") # pending | approved | rejected
    shop_order_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _digits(p: str) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    return d[-10:] if len(d) >= 10 else d


def _row(s, tenant: str) -> ChaiSettings:
    r = s.get(ChaiSettings, tenant)
    if r is None:
        r = ChaiSettings(tenant_id=tenant, menu=json.dumps(DEFAULT_MENU))
        s.add(r)
        s.flush()
    return r


def _menu(r: ChaiSettings) -> list[dict]:
    m = _j(r.menu, [])
    return m or [dict(x) for x in DEFAULT_MENU]


def _per_cup(menu: list[dict]) -> dict[str, float]:
    share = sum(max(0.0, float(x.get("share") or 0)) for x in menu) or float(len(menu)) or 1.0
    w = lambda x: (max(0.0, float(x.get("share") or 0)) or (share / max(1, len(menu)))) / share   # noqa: E731
    return {"price": sum(float(x.get("price") or 0) * w(x) for x in menu),
            "milk_ml": sum(float(x.get("milk_ml") or 0) * w(x) for x in menu),
            "sugar_g": sum(float(x.get("sugar_g") or 0) * w(x) for x in menu),
            "tea_g": sum(float(x.get("tea_g") or 0) * w(x) for x in menu)}


def _view(r: ChaiSettings) -> dict[str, Any]:
    menu = _menu(r)
    pc = _per_cup(menu)
    return {"enabled": bool(r.enabled), "stall_name": r.stall_name, "menu": menu, "other_pct": r.other_pct,
            "cash_pct": round(r.cash_pct, 1), "cash_learned": r.cash_learned, "milk_factor": round(r.milk_factor, 3),
            "factor_learned": r.factor_learned, "safety_pct": r.safety_pct, "milk_packet_ml": r.milk_packet_ml,
            "typical_cups": r.typical_cups, "stock": _j(r.stock, {}), "suppliers": _j(r.suppliers, []),
            "rules": _j(r.rules, []), "plan_time": r.plan_time,
            "per_cup": {k: round(v, 2) for k, v in pc.items()},
            "real_milk_per_cup_ml": round(pc["milk_ml"] * r.milk_factor, 1)}


def settings(tenant: str) -> dict[str, Any]:
    with session() as s:
        return _view(_row(s, tenant))


def _num(v, name: str, lo: float = 0, hi: float = 1e6) -> float:
    try:
        x = float(str(v).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        raise ChaiError(f"{name} ek number hona chahiye.")
    if not lo <= x <= hi:
        raise ChaiError(f"{name} {lo:g} se {hi:g} ke beech.")
    return x


def save_settings(tenant: str, **kw: Any) -> dict[str, Any]:
    with session() as s:
        r = _row(s, tenant)
        if kw.get("stall_name") is not None:
            r.stall_name = str(kw["stall_name"]).strip()[:120]
        if kw.get("enabled") is not None:
            r.enabled = bool(kw["enabled"])
        if kw.get("menu") is not None:
            menu = []
            for x in kw["menu"] or []:
                if not isinstance(x, dict) or not str(x.get("name") or "").strip():
                    continue
                menu.append({"name": str(x["name"]).strip()[:60], "price": _num(x.get("price", 0), "Daam", 0, 10000),
                             "milk_ml": _num(x.get("milk_ml", 0), "Doodh (ml)", 0, 1000),
                             "sugar_g": _num(x.get("sugar_g", 0), "Chini (g)", 0, 200),
                             "tea_g": _num(x.get("tea_g", 0), "Patti (g)", 0, 100),
                             "share": _num(x.get("share", 0), "Hissa %", 0, 100)})
            if not menu:
                raise ChaiError("Menu mein kam se kam ek cheez (naam + daam) chahiye.")
            r.menu = json.dumps(menu, ensure_ascii=False)
        for k, name, lo, hi in (("other_pct", "Doosri cheezon ka hissa %", 0, 95), ("safety_pct", "Extra %", 0, 100),
                                ("milk_packet_ml", "Packet (ml)", 0, 5000), ("typical_cups", "Roz ke cup", 0, 20000)):
            if kw.get(k) is not None:
                setattr(r, k, int(_num(kw[k], name, lo, hi)))
        if kw.get("cash_pct") is not None:
            r.cash_pct = _num(kw["cash_pct"], "Cash %", 0, 100)
        if kw.get("milk_factor") is not None:
            r.milk_factor = _num(kw["milk_factor"], "Doodh factor", 0.5, 2)
        if kw.get("plan_time") is not None:
            v = str(kw["plan_time"]).strip()
            if not re.fullmatch(r"\d{1,2}:\d{2}", v):
                raise ChaiError("Plan ka samay HH:MM mein (jaise 20:00).")
            r.plan_time = v
        if kw.get("rules") is not None:
            r.rules = json.dumps([str(x).strip()[:300] for x in kw["rules"] or [] if str(x).strip()][:30], ensure_ascii=False)
        if kw.get("suppliers") is not None:
            out = []
            for x in kw["suppliers"] or []:
                if not isinstance(x, dict) or not str(x.get("name") or "").strip():
                    continue
                items = [i for i in (str(t).lower().strip() for t in (x.get("items") or [])) if i in ("milk", "sugar", "tea")]
                out.append({"name": str(x["name"]).strip()[:80], "phone": _digits(x.get("phone") or ""),
                            "items": items or ["milk"], "site": str(x.get("site") or "").lower().strip()[:40]})
            r.suppliers = json.dumps(out, ensure_ascii=False)
        return _view(r)


def set_stock(tenant: str, milk_l=None, sugar_kg=None, tea_kg=None) -> dict[str, Any]:
    with session() as s:
        r = _row(s, tenant)
        st = _j(r.stock, {})
        for k, v, hi in (("milk_l", milk_l, 500), ("sugar_kg", sugar_kg, 500), ("tea_kg", tea_kg, 100)):
            if v is not None and v != "":
                st[k] = round(_num(v, k, 0, hi), 3)
        st["at"] = galla.today(tenant).isoformat()
        r.stock = json.dumps(st)
        return {"stock": st, "say": "Stock likh liya: " + ", ".join(f"{k.split('_')[0]} {v:g}{k.split('_')[1]}"
                                                                  for k, v in st.items() if k != "at") + "."}


# ---------------------------------------------------------------- the plan for tomorrow
def _estimate_sales(tenant: str, target: date, r: ChaiSettings, reasons: list[str]) -> int:
    """Expected total sales (paise) on `target` from earlier days; UPI-only days are completed with her cash share."""
    tot = galla.totals(tenant, 35, target - timedelta(days=1))
    cash_share = min(0.95, max(0.0, r.cash_pct / 100))

    def full(v: dict) -> int:
        if v["cash"] > 0:
            return v["total"]
        return int(v["upi"] / (1 - cash_share)) if cash_share < 1 else v["upi"]
    same = [(k, full(v)) for k, v in sorted(tot.items()) if date.fromisoformat(k).weekday() == target.weekday()][-4:]
    if len(same) >= 2:
        val = int(statistics.mean(x for _, x in same))
        reasons.append(f"Pichhle {len(same)} {galla.DAYS[target.weekday()]} ki bikri ka ausat {galla._rs(val)}.")
        return val
    last7 = [full(v) for k, v in sorted(tot.items()) if date.fromisoformat(k) >= target - timedelta(days=8)]
    if len(last7) >= 2:
        val = int(statistics.mean(last7))
        reasons.append(f"Pichhle {len(last7)} din ki bikri ka ausat {galla._rs(val)} (har din ka hisaab abhi kam hai).")
        return val
    return 0


def plan_tomorrow(tenant: str, for_date: str = "", weather: dict | None = None, conv: str = "") -> dict[str, Any]:
    """How many cups tomorrow, how much milk / sugar / patti to have, what to buy; one order card per supplier."""
    target = galla._day(tenant, for_date) if for_date else galla.today(tenant) + timedelta(days=1)
    reasons: list[str] = []
    with session() as s:
        r = _row(s, tenant)
        sv = _view(r)
        sales = _estimate_sales(tenant, target, r, reasons)
        pc = _per_cup(sv["menu"])
        if sales:
            chai_sales = sales * (100 - r.other_pct) / 100
            cups = chai_sales / 100 / max(1.0, pc["price"])
            reasons.append(f"Bikri ka {100 - r.other_pct}% chai / coffee, ek cup ka ausat daam ₹{pc['price']:.1f} = ~{round(cups)} cup.")
            if not r.cash_learned:
                reasons.append(f"Cash ka hissa {r.cash_pct:.0f}% maana hai (shaam ko cash bata dengi to sahi hota jayega).")
        elif r.typical_cups:
            cups = float(r.typical_cups)
            sales = int(cups * pc["price"] * 100 / max(0.05, (100 - r.other_pct) / 100))
            reasons.append(f"Abhi bikri ka hisaab nahi; aapke bataye roz ~{r.typical_cups} cup se.")
        else:
            return {"needs": "typical_cups", "say": "Abhi bikri ka koi hisaab nahi hai. Roz lagbhag kitne cup chai bikti hai? "
                                                   "(Ya UPI alerts chalu kar dijiye, 2-3 din mein Hoola khud seekh lega.)"}
        factor = 1.0
        try:
            from ..india.days import day_info
            hs = day_info(target).get("holidays") or []
            if hs:
                reasons.append(f"{galla._nice(target)} ko {hs[0].get('name', 'chhutti')}: chhutti ke din bikri badal sakti hai, "
                               "pichhli chhutti ka hisaab dekhkar badliye.")
        except Exception:
            pass
        w = weather or {}
        rain = w.get("tomorrow_rain_chance_pct")
        tmax = w.get("tomorrow_max_c")
        if isinstance(rain, (int, float)) and rain >= 60:
            factor *= 1.10
            reasons.append(f"Kal baarish ka chance {rain:.0f}%: chai zyada bikti hai, +10%.")
        if isinstance(tmax, (int, float)) and tmax >= 38:
            factor *= 0.90
            reasons.append(f"Kal {tmax:.0f}°C garmi: chai kam, -10%.")
        cups = cups * factor
        safety = 1 + r.safety_pct / 100
        milk_l = cups * pc["milk_ml"] * r.milk_factor / 1000 * safety
        sugar_kg = cups * pc["sugar_g"] / 1000 * safety
        tea_kg = cups * pc["tea_g"] / 1000 * safety
        if r.factor_learned:
            reasons.append(f"Ek cup mein asal mein ~{pc['milk_ml'] * r.milk_factor:.0f} ml doodh lagta hai "
                           f"({r.factor_learned} din ke hisaab se seekha).")
        reasons.append(f"{r.safety_pct}% extra rakha (kam na pade).")
        st = _j(r.stock, {})
        fresh = st.get("at") in (galla.today(tenant).isoformat(), target.isoformat())
        buy: dict[str, float] = {}
        left_milk = float(st.get("milk_l") or 0) if fresh else 0.0
        need_milk = max(0.0, milk_l - left_milk)
        if left_milk:
            reasons.append(f"{left_milk:g} litre doodh bacha hai, utna kam.")
        pk = r.milk_packet_ml or 0
        buy["milk_l"] = (math.ceil(need_milk * 1000 / pk) * pk / 1000) if pk else math.ceil(need_milk * 2) / 2
        notes = []
        for k, daily, step, label in (("sugar_kg", sugar_kg, 0.5, "chini"), ("tea_kg", tea_kg, 0.25, "patti")):
            if daily <= 0:
                continue
            have = st.get(k)
            if have is None:
                notes.append(f"{label.title()} kitni bachi hai bata dijiye (abhi andaza nahi).")
                continue
            days_left = float(have) / daily if daily else 99
            if days_left < 3:
                want = max(0.0, daily * 7 - float(have))
                buy[k] = math.ceil(want / step) * step
                reasons.append(f"{label.title()} {float(have):g} kg bachi, ~{days_left:.1f} din ki: 7 din ki le lijiye.")
        need = {"milk_l": round(milk_l, 2), "sugar_kg": round(sugar_kg, 3), "tea_kg": round(tea_kg, 3),
                "start_milk_l": round(left_milk, 2)}
        plan = s.scalars(select(ChaiPlan).where(ChaiPlan.tenant_id == tenant, ChaiPlan.for_date == target.isoformat())).first()
        if plan is None:
            plan = ChaiPlan(tenant_id=tenant, for_date=target.isoformat())
            s.add(plan)
        plan.cups, plan.sales_paise = int(round(cups)), int(sales * factor)
        plan.status = "draft"
        plan.need, plan.buy = json.dumps(need), json.dumps(buy)
        plan.reasons = json.dumps(reasons + notes, ensure_ascii=False)
        s.flush()
        for old in s.scalars(select(StockOrder).where(StockOrder.plan_id == plan.id, StockOrder.status == "pending")).all():
            s.delete(old)                                   # a new plan replaces cards she has not answered yet
        orders = _make_orders(s, tenant, r, plan, target, buy)
        out = _plan_view(s, plan)
        out["orders"] = [_order_view(o) for o in orders]
        out["rules"] = sv["rules"]
    say = (f"Kal ({galla._nice(target)}) ~{out['cups']} cup: doodh {need['milk_l']:g} L chahiye"
           + (f", {buy['milk_l']:g} L lena hai" if buy.get("milk_l") else ", naya lene ki zaroorat nahi")
           + "".join(f", {('chini' if k == 'sugar_kg' else 'patti')} {v:g} kg lena hai" for k, v in buy.items() if k != "milk_l" and v)
           + ". Order card par aapki haan ka intezaar.")
    out["say"] = say
    _publish(tenant, "chai_plan", out, conv)
    return out


def _make_orders(s, tenant: str, r: ChaiSettings, plan: ChaiPlan, target: date, buy: dict) -> list[StockOrder]:
    sups = _j(r.suppliers, [])
    name = r.stall_name or "chai stall"
    lines = {"milk": ("milk_l", "litre doodh"), "sugar": ("sugar_kg", "kg chini"), "tea": ("tea_kg", "kg chai patti")}
    out: list[StockOrder] = []
    left = {k: v for k, v in buy.items() if v}
    for sp in sups:
        items = [{"item": it, "qty": left.pop(lines[it][0]), "unit": lines[it][1]} for it in sp.get("items", []) if lines[it][0] in left]
        if not items:
            continue
        what = ", ".join(f"{x['qty']:g} {x['unit']}" for x in items)
        text = (f"Namaste {sp['name']} ji, {galla._nice(target)} subah ke liye {what} chahiye. Dhanyavaad, {name}."
                if not sp.get("site") else what)
        o = StockOrder(tenant_id=tenant, plan_id=plan.id, supplier=sp["name"], phone=sp.get("phone", ""), site=sp.get("site", ""),
                       items=json.dumps(items), text=text)
        s.add(o)
        out.append(o)
    if left:                                              # nobody set up for these: she buys herself, the card is the list
        items = [{"item": it, "qty": left[k], "unit": u} for it, (k, u) in lines.items() if k in left]
        o = StockOrder(tenant_id=tenant, plan_id=plan.id, supplier="Khud lena hai", items=json.dumps(items),
                       text="Kharidna hai: " + ", ".join(f"{x['qty']:g} {x['unit']}" for x in items))
        s.add(o)
        out.append(o)
    s.flush()
    return out


def _order_view(o: StockOrder) -> dict[str, Any]:
    items = _j(o.items, [])
    return {"id": o.id, "plan_id": o.plan_id, "supplier": o.supplier, "phone": o.phone, "site": o.site, "items": items,
            "what": ", ".join(f"{x['qty']:g} {x['unit']}" for x in items), "text": o.text, "status": o.status,
            "wa_link": f"https://wa.me/91{o.phone}?text={quote(o.text)}" if len(o.phone or "") == 10 else "",
            "shop_order_id": o.shop_order_id}


def _plan_view(s, p: ChaiPlan) -> dict[str, Any]:
    d = date.fromisoformat(p.for_date)
    orders = s.scalars(select(StockOrder).where(StockOrder.plan_id == p.id)).all()
    return {"id": p.id, "for_date": p.for_date, "nice": galla._nice(d), "cups": p.cups, "sales": galla._rs(p.sales_paise),
            "need": _j(p.need, {}), "buy": _j(p.buy, {}), "reasons": _j(p.reasons, []), "status": p.status,
            "feedback": _j(p.feedback, {}), "orders": [_order_view(o) for o in orders]}


def get_plan(tenant: str, for_date: str = "") -> dict[str, Any] | None:
    with session() as s:
        q = select(ChaiPlan).where(ChaiPlan.tenant_id == tenant)
        q = q.where(ChaiPlan.for_date == galla._day(tenant, for_date).isoformat()) if for_date else q
        p = s.scalars(q.order_by(ChaiPlan.for_date.desc())).first()
        return _plan_view(s, p) if p else None


def decide_order(tenant: str, order_id: str, approve: bool, conv: str = "") -> dict[str, Any]:
    """Her Haan / Mana on a stock order (only from her tap or her own words to Hoola)."""
    with session() as s:
        o = s.get(StockOrder, order_id)
        if o is None or o.tenant_id != tenant:
            raise ChaiError("Yeh order card nahi mila.")
        if o.status != "pending":
            raise ChaiError("Is card par faisla ho chuka.")
        o.status = "approved" if approve else "rejected"
        s.flush()
        v = _order_view(o)
        site, text = o.site, o.text
    say = "Theek hai, yeh order nahi." if not approve else ""
    if approve:
        if site:
            from ..shop import service as shop
            try:
                r = shop.order(tenant, text, conv, site, "", "kal subah", "", "chai stall ka stock", created_by="owner")
                with session() as s:
                    s.get(StockOrder, order_id).shop_order_id = str(r.get("id") or (r.get("order") or {}).get("id") or "")
                v["shop_order_id"] = str(r.get("id") or "")
                say = f"{site.title()} par order taiyaar ho raha hai; payment aap karengi (card aayega)."
            except Exception as e:                     # site not supported etc.: she buys herself
                say = f"Site se order nahi ho paya ({e}); list card par hai."
        elif v["wa_link"]:
            say = f"WhatsApp par {v['supplier']} ka message taiyaar: card par 'Bhejo' dabaiye."
        else:
            say = "Pakka. Yeh list card par hai."
    _publish(tenant, "chai_order", v, conv)
    return {"order": v, "say": say}


# ---------------------------------------------------------------- learning: what really happened
def feedback(tenant: str, for_date: str = "", milk_left_l=None, ran_out_at: str = "", sugar_left_kg=None, tea_left_kg=None,
             cash=None, bought_milk_l=None) -> dict[str, Any]:
    """Her report of a finished day: milk left (or when it ran out), cash taken. Teaches the milk per cup and the cash share."""
    d = galla._day(tenant, for_date)
    learned: list[str] = []
    if cash not in (None, ""):
        galla.add_cash(tenant, cash, d.isoformat(), note="shaam ka cash")
    day = galla.totals(tenant, 1, d).get(d.isoformat(), {"upi": 0, "cash": 0, "total": 0})
    with session() as s:
        r = _row(s, tenant)
        if day["cash"] > 0 and day["upi"] > 0:
            pct = day["cash"] * 100 / day["total"]
            r.cash_pct = pct if not r.cash_learned else 0.7 * r.cash_pct + 0.3 * pct
            r.cash_learned += 1
            learned.append(f"Cash ka hissa ab ~{r.cash_pct:.0f}% maana.")
        p = s.scalars(select(ChaiPlan).where(ChaiPlan.tenant_id == tenant, ChaiPlan.for_date == d.isoformat())).first()
        pc = _per_cup(_menu(r))
        if p is not None and (milk_left_l not in (None, "") or ran_out_at):
            buy = _j(p.buy, {})
            had = float(bought_milk_l) if bought_milk_l not in (None, "") else float(buy.get("milk_l") or 0)
            had += float(_j(p.need, {}).get("start_milk_l") or 0)
            left = float(milk_left_l or 0)
            used = max(0.0, had - left)
            sales = day["total"] if day["cash"] else int(day["upi"] / max(0.05, 1 - r.cash_pct / 100))
            cups = sales / 100 * (100 - r.other_pct) / 100 / max(1.0, pc["price"])
            expect = cups * pc["milk_ml"] / 1000
            if used > 0 and expect > 0.5:
                ratio = used / expect
                if ran_out_at:
                    ratio *= 1.10                          # it ran out: the real need was more than what was there
                ratio = max(0.6, min(1.6, ratio))
                r.milk_factor = round(ratio if not r.factor_learned else 0.7 * r.milk_factor + 0.3 * ratio, 3)
                r.factor_learned += 1
                learned.append(f"Ek cup mein ~{pc['milk_ml'] * r.milk_factor:.0f} ml doodh lagta hai (seekha).")
            fb = _j(p.feedback, {})
            fb.update({"milk_left_l": left, "ran_out_at": ran_out_at, "used_l": round(used, 2), "cups_est": round(cups)})
            p.feedback, p.status = json.dumps(fb), "done"
        st = _j(r.stock, {})
        for k, v in (("milk_l", milk_left_l), ("sugar_kg", sugar_left_kg), ("tea_kg", tea_left_kg)):
            if v not in (None, ""):
                st[k] = round(_num(v, k, 0, 500), 3)
        st["at"] = galla.today(tenant).isoformat()
        r.stock = json.dumps(st)
    if ran_out_at:
        learned.append(f"Doodh {ran_out_at} baje khatam hua: agle plan mein zyada rakhenge.")
    return {"learned": learned, "say": "Shukriya, likh liya. " + " ".join(learned)}


# ---------------------------------------------------------------- the evening card (worker)
def due_plans() -> list[str]:
    from ..life import tz_of
    out = []
    with session() as s:
        for r in s.scalars(select(ChaiSettings).where(ChaiSettings.enabled.is_(True))).all():
            local = datetime.now(tz_of(r.tenant_id))
            d = local.date().isoformat()
            try:
                hh, mm = [int(x) for x in (r.plan_time or "20:00").split(":")]
            except ValueError:
                hh, mm = 20, 0
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            if r.last_plan != d and 0 <= late <= 180:
                r.last_plan = d
                out.append(r.tenant_id)
    return out


async def evening(tenant: str) -> dict[str, Any]:
    weather = None
    try:
        from ..life import weather_for
        weather = await weather_for(tenant)
    except Exception:
        weather = None
    today_sum = galla.day_summary(tenant)
    plan = plan_tomorrow(tenant, weather=weather)
    try:
        from ..events import notify
        from ..net.service import home_conv
        notify(home_conv(tenant), today_sum["text"] + "\n" + plan.get("say", ""))
    except Exception:
        pass
    return {"today": today_sum, "plan": plan}


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("chai publish failed")


def prompt_block(tenant: str) -> str:
    with session() as s:
        r = s.get(ChaiSettings, tenant)
        if r is None or not r.enabled:
            return ""
    return "CHAI STALL: she runs a chai stall; use chai / chai_dekho for sales (UPI alerts + cash), best hours, tomorrow's milk / sugar plan and stock orders."
