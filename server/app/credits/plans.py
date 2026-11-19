"""v0.999.25 HOOLA CREDITS - the price list (docs/research/credits/01_credit_plans.md).

One credit = $0.001 of AI cost at the maker's price, the same everywhere. Three price levels:
  in       India, rupees, GST included, paid through Razorpay or Cashfree (Newtika files the GST)
  world    every other country, US dollars before the buyer's tax, paid through Dodo Payments or Paddle (the merchant
           of record adds and pays each country's VAT / GST / sales tax)
  regional lower-income countries (the owner's list, CREDITS_REGIONAL), dollars, same payment route as world
Every plan keeps 40% even if all its credits are used (fees, tax and servers already taken off)."""
from __future__ import annotations

from typing import Any

USD_PER_CREDIT = 0.001
REGIONS = ("in", "world", "regional")
CURRENCY = {"in": "INR", "world": "USD", "regional": "USD"}

# monthly plans: price + credits per price level; days = how long one purchase lasts
PLANS: dict[str, dict[str, Any]] = {
    "lite": {"name": "Lite", "price": {"in": 399, "world": 8, "regional": 4.5},
             "credits": {"in": 2000, "world": 3900, "regional": 1900}, "carry": False},
    "plus": {"name": "Plus", "price": {"in": 999, "world": 20, "regional": 11},
             "credits": {"in": 5400, "world": 10600, "regional": 5500}, "carry": False},
    "pro": {"name": "Pro", "price": {"in": 1999, "world": 100, "regional": 23},
            "credits": {"in": 11100, "world": 55200, "regional": 12200}, "carry": True},
    "max": {"name": "Max", "price": {"in": 7999, "world": 200, "regional": 90},
            "credits": {"in": 44900, "world": 111000, "regional": 49600}, "carry": True},
}
PLAN_DAYS = 30

# extra credits, bought when needed; they last 12 months
TOPUPS: dict[str, dict[str, Any]] = {
    "t1k": {"credits": 1000, "price": {"in": 219, "world": 2.49, "regional": 2.49}},
    "t5k": {"credits": 5000, "price": {"in": 999, "world": 11.99, "regional": 11.99}},
    "t20k": {"credits": 20000, "price": {"in": 3899, "world": 45.99, "regional": 45.99}},
}
TOPUP_DAYS = 365

# AI employees: one package per employee, a number of jobs a month on a set tier (not paid from chat credits)
PACKS: dict[str, dict[str, Any]] = {
    "starter": {"name": "Starter", "jobs": 60, "tier": "medium", "price": {"in": 1499, "world": 16, "regional": 16}},
    "standard": {"name": "Standard", "jobs": 150, "tier": "medium", "price": {"in": 3699, "world": 39, "regional": 39}},
    "pro": {"name": "Pro", "jobs": 60, "tier": "high", "price": {"in": 9499, "world": 99, "regional": 99}},
    "ultra": {"name": "Ultra", "jobs": 30, "tier": "ultra", "price": {"in": 29999, "world": 309, "regional": 309}},
}


def region_of(country: str) -> str:
    from ..config import get_settings
    c = (country or "").strip().upper()[:2]
    if c == "IN":
        return "in"
    reg = {x.strip().upper() for x in str(getattr(get_settings(), "credits_regional", "") or "").split(",") if x.strip()}
    return "regional" if c in reg else "world"


def minor(amount: float, currency: str) -> int:
    """Paise / cents."""
    return int(round(float(amount) * 100))


def sku(kind: str, item: str, region: str) -> str:
    return f"{kind}_{item}_{region}"


def parse_sku(s: str) -> tuple[str, str, str]:
    """'plan_pro_world' -> ('plan', 'pro', 'world'); ValueError for anything not on the list."""
    try:
        kind, item, region = str(s or "").split("_", 2)
    except ValueError:
        raise ValueError("Not on the price list.")
    table = {"plan": PLANS, "topup": TOPUPS, "pack": PACKS}.get(kind)
    if table is None or item not in table or region not in REGIONS:
        raise ValueError("Not on the price list.")
    return kind, item, region


def item_of(kind: str, item: str) -> dict[str, Any]:
    return {"plan": PLANS, "topup": TOPUPS, "pack": PACKS}[kind][item]


def price(kind: str, item: str, region: str) -> tuple[float, str]:
    return float(item_of(kind, item)["price"][region]), CURRENCY[region]


def catalogue(region: str) -> dict[str, Any]:
    cur = CURRENCY[region]
    return {
        "region": region, "currency": cur,
        "plans": [{"id": k, "sku": sku("plan", k, region), "name": v["name"], "price": v["price"][region],
                   "credits": v["credits"][region], "days": PLAN_DAYS} for k, v in PLANS.items()],
        "topups": [{"id": k, "sku": sku("topup", k, region), "credits": v["credits"], "price": v["price"][region]}
                   for k, v in TOPUPS.items()],
        "packs": [{"id": k, "sku": sku("pack", k, region), "name": v["name"], "jobs": v["jobs"], "tier": v["tier"],
                   "price": v["price"][region]} for k, v in PACKS.items()],
    }
