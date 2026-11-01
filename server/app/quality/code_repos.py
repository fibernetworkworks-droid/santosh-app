"""v0.365 HARD CARD - the two bigger practice projects the hard coding set (code_tasks2) is built on.

DUKAAN (Python, 29 files): a small shop backend - catalog, stock, cart, coupons, GST, shipping, orders, notifications,
reports, dates, JSON-style API handlers - with root AGENTS.md, a folder rules file in app/api/, docs, tests.
HISAAB (JavaScript, 12 files): ES-module billing helpers (paise, GST split, formats, invoices) tested with node:test.
Every job starts from one of these and changes a few files; the base itself is correct and its own tests pass."""
from __future__ import annotations

PY_AGENTS = """# Rules for contributors and coding agents (dukaan)
- Python 3.11, standard library only. Money is integer paise everywhere, never float.
- Settings (rates, limits, fees) live in app/config.py - never hard-code them elsewhere.
- Logging, never print(): log = logging.getLogger(__name__).
- Tests live in tests/ as test_<module>.py, plain pytest functions. tests/conftest.py resets stock and orders.
- Keep public function names stable; if one must change, keep the old name as an alias for one release.
- Small focused changes; do not reformat or touch unrelated code.
"""
API_AGENTS = """# app/api/ rules
- Every handler takes one dict and returns {"status": int, "body": dict}. A handler NEVER raises:
  bad / missing input = 400, unknown id or someone else's record = 404 (never reveal that it exists).
- Check required keys with app.validators.require(req, *keys) first.
- Bodies hold plain data only (ints in paise, str), built with _order_body for orders.
"""
CONFIG = '''"""Shop settings. Money is integer paise."""
GST_RATE = 18                 # percent
FREE_SHIPPING_ABOVE = 49900   # orders from Rs 499 ship free
SHIPPING_FLAT = 4900
SHIPPING_PER_KG = 2000        # each started kg above 2 kg
COUPON_CAP = 20000            # max Rs 200 off
'''
MODELS = '''from dataclasses import dataclass


@dataclass
class Product:
    sku: str
    name: str
    price: int          # paise
    weight_g: int = 500


@dataclass
class LineItem:
    sku: str
    qty: int
    price: int          # paise, each


@dataclass
class Order:
    id: str
    customer_id: str
    items: list
    subtotal: int
    discount: int
    gst: int
    shipping: int
    total: int
    payment: str = "prepaid"
    status: str = "placed"
'''
MONEY = '''def fmt(paise: int) -> str:
    """12345 -> 'Rs 123.45'"""
    sign = "-" if paise < 0 else ""
    paise = abs(paise)
    return f"{sign}Rs {paise // 100}.{paise % 100:02d}"


def pct(amount: int, rate: int) -> int:
    """rate percent of a paise amount, rounded half up."""
    return (amount * rate + 50) // 100
'''
TAX = '''from app import config
from app.money import pct


def gst(amount: int) -> int:
    """GST on a paise amount at the shop rate."""
    return pct(amount, config.GST_RATE)
'''
CATALOG = '''from app.models import Product

PRODUCTS = {
    "TEA-250": Product("TEA-250", "Assam tea 250 g", 18000, 250),
    "SUGAR-1K": Product("SUGAR-1K", "Sugar 1 kg", 5200, 1000),
    "MUG": Product("MUG", "Steel mug", 24900, 300),
    "KETTLE": Product("KETTLE", "Electric kettle", 129900, 1200),
}


def find_product(sku: str):
    """The Product for a SKU, or None."""
    return PRODUCTS.get(sku)
'''
INVENTORY = '''STOCK = {"TEA-250": 50, "SUGAR-1K": 100, "MUG": 20, "KETTLE": 5}


class OutOfStock(Exception):
    pass


def available(sku: str) -> int:
    """Units in stock."""
    return STOCK.get(sku, 0)


def reserve(sku: str, qty: int) -> None:
    """Take qty out of stock, or raise OutOfStock (nothing taken)."""
    if STOCK.get(sku, 0) < qty:
        raise OutOfStock(sku)
    STOCK[sku] -= qty


def release(items) -> None:
    """Put LineItems back in stock (a cancelled or failed order)."""
    for it in items:
        STOCK[it.sku] = STOCK.get(it.sku, 0) + it.qty
'''
CART = '''from app.catalog import find_product
from app.models import LineItem


class Cart:
    def __init__(self, customer_id: str, items=None):
        self.customer_id = customer_id
        self.items = items if items is not None else []

    def add(self, sku: str, qty: int = 1) -> None:
        p = find_product(sku)
        if p is None:
            raise KeyError(sku)
        if qty <= 0:
            raise ValueError("qty")
        for it in self.items:
            if it.sku == sku:
                it.qty += qty
                return
        self.items.append(LineItem(sku, qty, p.price))

    def remove(self, sku: str) -> None:
        self.items = [i for i in self.items if i.sku != sku]

    def subtotal(self) -> int:
        return sum(i.qty * i.price for i in self.items)

    def weight_g(self) -> int:
        return sum(find_product(i.sku).weight_g * i.qty for i in self.items)
'''
DISCOUNTS = '''from app import config
from app.money import pct

COUPONS = {"DIWALI10": 10, "WELCOME50": 50}   # percent off


def apply_coupon(code: str, subtotal: int) -> int:
    """Discount in paise for a coupon code ('' = none), capped at config.COUPON_CAP."""
    if not code:
        return 0
    off = COUPONS.get(code.upper())
    if off is None:
        raise ValueError("unknown coupon")
    return min(pct(subtotal, off), config.COUPON_CAP)
'''
SHIPPING = '''from app import config


def shipping_fee(subtotal: int, weight_g: int) -> int:
    """Flat fee + per started kg above 2 kg; free from the free-shipping limit."""
    if subtotal >= config.FREE_SHIPPING_ABOVE:
        return 0
    extra_kg = max(0, (weight_g - 2000 + 999) // 1000)
    return config.SHIPPING_FLAT + config.SHIPPING_PER_KG * extra_kg
'''
ORDERS = '''import logging

from app import inventory, tax
from app.discounts import apply_coupon
from app.models import Order
from app.shipping import shipping_fee
from app.utils.ids import next_id

log = logging.getLogger(__name__)
ORDERS: dict = {}


def place_order(cart, coupon: str = "", payment: str = "prepaid") -> Order:
    """Reserve stock and record the order. Raises ValueError / OutOfStock."""
    if not cart.items:
        raise ValueError("empty cart")
    if payment not in ("prepaid", "cod"):
        raise ValueError("payment")
    subtotal = cart.subtotal()
    discount = apply_coupon(coupon, subtotal)
    reserved = []
    try:
        for it in cart.items:
            inventory.reserve(it.sku, it.qty)
            reserved.append(it)
    except inventory.OutOfStock:
        inventory.release(reserved)
        raise
    taxable = subtotal - discount
    g = tax.gst(taxable)
    ship = shipping_fee(subtotal, cart.weight_g())
    total = taxable + g + ship
    o = Order(next_id("O"), cart.customer_id, list(cart.items), subtotal, discount, g, ship, total, payment)
    ORDERS[o.id] = o
    log.info("order %s placed, total %d", o.id, total)
    return o


def cancel_order(order_id: str) -> Order:
    """Cancel once and return the stock. KeyError for an unknown id."""
    o = ORDERS[order_id]
    if o.status != "cancelled":
        o.status = "cancelled"
        inventory.release(o.items)
        log.info("order %s cancelled", order_id)
    return o


def get_order(order_id: str):
    """The Order, or None."""
    return ORDERS.get(order_id)
'''
NOTIFY = '''import logging

from app.money import fmt

log = logging.getLogger(__name__)


def order_message(order) -> str:
    """The SMS text for a placed order."""
    return f"Order {order.id} placed: {len(order.items)} items, total {fmt(order.total)}. " + shipping_note()


def shipping_note() -> str:
    """The free-shipping line under every message."""
    return "Free shipping on orders from Rs 499!"
'''
REPORTS = '''from collections import Counter


def daily_sales(orders) -> dict:
    """Totals of the placed (not cancelled) orders."""
    live = [o for o in orders if o.status != "cancelled"]
    units = Counter()
    for o in live:
        for it in o.items:
            units[it.sku] += it.qty
    return {"orders": len(live), "revenue": sum(o.total for o in live), "units": dict(units)}
'''
VALIDATORS = '''import re


def is_valid_pincode(code: str) -> bool:
    """6-digit Indian PIN, first digit 1-9."""
    return isinstance(code, str) and bool(re.fullmatch(r"[1-9][0-9]{5}", code))


def is_valid_phone(phone: str) -> bool:
    """10-digit Indian mobile starting 6-9."""
    return isinstance(phone, str) and bool(re.fullmatch(r"[6-9][0-9]{9}", phone))


def require(req, *keys) -> list:
    """The keys missing (or empty) in req; every key when req is not a dict."""
    if not isinstance(req, dict):
        return list(keys)
    return [k for k in keys if req.get(k) in (None, "", [])]
'''
IDS = '''import itertools

_counter = itertools.count(1)


def next_id(prefix: str) -> str:
    """O00001, O00002 ..."""
    return f"{prefix}{next(_counter):05d}"
'''
DATES = '''from datetime import date, timedelta


def delivery_date(placed: date, days: int) -> date:
    """placed + `days` delivery days; there is no delivery on Sunday, so Sundays are not counted."""
    d = placed
    left = days
    while left > 0:
        d += timedelta(days=1)
        if d.weekday() != 6:
            left -= 1
    return d
'''
TEXT = '''def title_case(s: str) -> str:
    """'assam tea' -> 'Assam Tea'"""
    return " ".join(w[:1].upper() + w[1:] for w in s.split())


def truncate(s: str, n: int) -> str:
    """Cut to n characters with an ellipsis."""
    return s if len(s) <= n else s[: n - 1] + "…"
'''
HANDLERS = '''from app import inventory, orders, tax
from app.cart import Cart
from app.discounts import apply_coupon
from app.shipping import shipping_fee
from app.validators import require


def _cart(req) -> Cart:
    cart = Cart(str(req.get("customer_id") or "guest"))
    for sku, qty in req["items"]:
        cart.add(sku, int(qty))
    return cart


def _order_body(o) -> dict:
    return {"id": o.id, "customer_id": o.customer_id, "items": [[i.sku, i.qty, i.price] for i in o.items],
            "subtotal": o.subtotal, "discount": o.discount, "gst": o.gst, "shipping": o.shipping, "total": o.total,
            "payment": o.payment, "status": o.status}


def quote(req) -> dict:
    """{'items': [[sku, qty]], 'coupon': ''} -> the price breakdown; nothing is reserved."""
    if require(req, "items"):
        return {"status": 400, "body": {"error": "items required"}}
    try:
        cart = _cart(req)
        subtotal = cart.subtotal()
        discount = apply_coupon(req.get("coupon", ""), subtotal)
    except (KeyError, ValueError, TypeError) as e:
        return {"status": 400, "body": {"error": str(e)}}
    g = tax.gst(subtotal - discount)
    ship = shipping_fee(subtotal, cart.weight_g())
    return {"status": 200, "body": {"subtotal": subtotal, "discount": discount, "gst": g, "shipping": ship,
                                    "total": subtotal - discount + g + ship, "free_above": 49900}}


def create_order(req) -> dict:
    """{'customer_id', 'items', 'coupon'?, 'payment'?} -> 201 with the order."""
    if require(req, "customer_id", "items"):
        return {"status": 400, "body": {"error": "customer_id and items required"}}
    try:
        o = orders.place_order(_cart(req), req.get("coupon", ""), req.get("payment", "prepaid"))
    except inventory.OutOfStock as e:
        return {"status": 409, "body": {"error": f"out of stock: {e}"}}
    except (KeyError, ValueError, TypeError) as e:
        return {"status": 400, "body": {"error": str(e)}}
    return {"status": 201, "body": _order_body(o)}


def get_order(req) -> dict:
    """{'order_id', 'customer_id'} -> the order."""
    if require(req, "order_id", "customer_id"):
        return {"status": 400, "body": {"error": "order_id and customer_id required"}}
    o = orders.get_order(req["order_id"])
    if o is None or o.customer_id != req["customer_id"]:
        return {"status": 404, "body": {"error": "not found"}}
    return {"status": 200, "body": _order_body(o)}
'''
CONFTEST = '''import pytest

from app import inventory, orders

_BASE = dict(inventory.STOCK)


@pytest.fixture(autouse=True)
def fresh_shop():
    inventory.STOCK.clear()
    inventory.STOCK.update(_BASE)
    orders.ORDERS.clear()
    yield
'''
TEST_CART = '''from app.cart import Cart


def test_add_merges_same_sku():
    c = Cart("c1")
    c.add("TEA-250")
    c.add("TEA-250", 2)
    assert len(c.items) == 1 and c.items[0].qty == 3
    assert c.subtotal() == 54000
'''
TEST_ORDERS = '''from app import inventory
from app.cart import Cart
from app.orders import cancel_order, place_order


def test_place_and_cancel_returns_stock():
    c = Cart("c1")
    c.add("MUG", 3)
    o = place_order(c)
    assert inventory.STOCK["MUG"] == 17
    assert o.total == 74700 + 13446           # free shipping from Rs 499, GST 18%
    cancel_order(o.id)
    assert inventory.STOCK["MUG"] == 20
'''
TEST_MONEY = '''from app.money import fmt, pct


def test_fmt():
    assert fmt(12345) == "Rs 123.45"


def test_pct_half_up():
    assert pct(250, 18) == 45
'''
ARCH = """# Architecture

app/config.py      every rate / limit / fee
app/models.py      Product, LineItem, Order (dataclasses)
app/catalog.py     products by SKU
app/inventory.py   stock: reserve / release
app/cart.py        Cart (items, subtotal, weight)
app/discounts.py   coupons
app/tax.py         GST
app/shipping.py    shipping fee
app/orders.py      place / cancel / get orders (in memory)
app/notify.py      SMS texts
app/reports.py     daily sales
app/api/handlers.py  JSON-style handlers (see app/api/AGENTS.md)
app/utils/         ids, dates, text
"""

DUKAAN = {
    "AGENTS.md": PY_AGENTS, "README.md": "# dukaan\n\nA small shop backend. See docs/ARCHITECTURE.md.\n\n"
                                         "Run the tests: `python -m pytest -q`\n",
    "pyproject.toml": '[project]\nname = "dukaan"\nrequires-python = ">=3.11"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
    "docs/ARCHITECTURE.md": ARCH,
    "app/__init__.py": "", "app/config.py": CONFIG, "app/models.py": MODELS, "app/money.py": MONEY, "app/tax.py": TAX,
    "app/catalog.py": CATALOG, "app/inventory.py": INVENTORY, "app/cart.py": CART, "app/discounts.py": DISCOUNTS,
    "app/shipping.py": SHIPPING, "app/orders.py": ORDERS, "app/notify.py": NOTIFY, "app/reports.py": REPORTS,
    "app/validators.py": VALIDATORS, "app/utils/__init__.py": "", "app/utils/ids.py": IDS, "app/utils/dates.py": DATES,
    "app/utils/text.py": TEXT, "app/api/__init__.py": "", "app/api/AGENTS.md": API_AGENTS, "app/api/handlers.py": HANDLERS,
    "tests/__init__.py": "", "tests/conftest.py": CONFTEST, "tests/test_cart.py": TEST_CART,
    "tests/test_orders.py": TEST_ORDERS, "tests/test_money.py": TEST_MONEY,
}

# ---------------------------------------------------------------- HISAAB (JavaScript)
JS_AGENTS = """# Rules for contributors and coding agents (hisaab)
- Node 20+, ES modules (import / export), no dependencies.
- Money is integer paise; never floats for money.
- Tests live in test/<module>.test.js using node:test and node:assert/strict. Run: node --test
- Export new functions from src/index.js too.
"""
PKG = '{\n  "name": "hisaab",\n  "version": "1.4.0",\n  "type": "module",\n  "scripts": {"test": "node --test"}\n}\n'
JS_MONEY = '''/** Rupees text ("12.5") -> paise (1250). */
export function toPaise(rupees) {
  const [whole, frac = ""] = String(rupees).split(".");
  return Number(whole) * 100 + Number((frac + "00").slice(0, 2));
}

/** paise -> "12.50" */
export function plain(paise) {
  const sign = paise < 0 ? "-" : "";
  const p = Math.abs(paise);
  return `${sign}${Math.floor(p / 100)}.${String(p % 100).padStart(2, "0")}`;
}
'''
JS_GST = '''/** GST in paise on a paise amount at `rate` percent, half up. */
export function gstOn(amount, rate) {
  return Math.floor((amount * rate + 50) / 100);
}

/**
 * Split a GST amount: inter-state = all IGST; within the state = CGST + SGST halves.
 * The parts must always add up to the whole GST.
 */
export function splitGst(gst, interState) {
  if (interState) return { igst: gst };
  return { cgst: Math.floor(gst / 2), sgst: Math.floor(gst / 2) };
}
'''
JS_FORMAT = '''import { plain } from "./money.js";

/** paise -> "Rs 1234567.50" (no grouping) */
export function formatPlain(paise) {
  return `Rs ${plain(paise)}`;
}
'''
JS_INVOICE = '''import { gstOn, splitGst } from "./gst.js";

/** lines = [{name, qty, price}] (paise) -> invoice totals. */
export function buildInvoice(lines, { rate = 18, interState = false } = {}) {
  const subtotal = lines.reduce((s, l) => s + l.qty * l.price, 0);
  const gst = gstOn(subtotal, rate);
  return { subtotal, gst, ...splitGst(gst, interState), total: subtotal + gst };
}
'''
JS_LEDGER = '''/** Running balance of entries [{amount}] (paise, + in / - out). */
export function balance(entries) {
  return entries.reduce((s, e) => s + e.amount, 0);
}
'''
JS_DATES = '''/** "2026-11-01" -> "01/11/2026" */
export function dmy(iso) {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
'''
JS_VALIDATE = '''/** 15-character GSTIN shape check. */
export function looksLikeGstin(s) {
  return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(String(s));
}
'''
JS_INDEX = '''export { toPaise, plain } from "./money.js";
export { gstOn, splitGst } from "./gst.js";
export { formatPlain } from "./format.js";
export { buildInvoice } from "./invoice.js";
export { balance } from "./ledger.js";
export { dmy } from "./dates.js";
export { looksLikeGstin } from "./validate.js";
'''
JS_TEST_MONEY = '''import { test } from "node:test";
import assert from "node:assert/strict";
import { toPaise, plain } from "../src/money.js";

test("toPaise", () => {
  assert.equal(toPaise("12.5"), 1250);
});

test("plain", () => {
  assert.equal(plain(5), "0.05");
});
'''
JS_TEST_INVOICE = '''import { test } from "node:test";
import assert from "node:assert/strict";
import { buildInvoice } from "../src/invoice.js";

test("inter-state invoice is all IGST", () => {
  const inv = buildInvoice([{ name: "tea", qty: 2, price: 10000 }], { interState: true });
  assert.deepEqual(inv, { subtotal: 20000, gst: 3600, igst: 3600, total: 23600 });
});
'''

HISAAB = {
    "AGENTS.md": JS_AGENTS, "README.md": "# hisaab\n\nBilling helpers in paise. `node --test`\n", "package.json": PKG,
    "src/index.js": JS_INDEX, "src/money.js": JS_MONEY, "src/gst.js": JS_GST, "src/format.js": JS_FORMAT,
    "src/invoice.js": JS_INVOICE, "src/ledger.js": JS_LEDGER, "src/dates.js": JS_DATES, "src/validate.js": JS_VALIDATE,
    "test/money.test.js": JS_TEST_MONEY, "test/invoice.test.js": JS_TEST_INVOICE,
}
