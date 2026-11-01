"""v0.402 REVIEW CARD - fixed practice pull requests for Developer Sahayak's PR review (owner: "GO ECC PHASE 1").

Every PR changes the DUKAAN shop (code_repos, 30 files). 8 carry ONE planted problem at a known line (`spot` = a piece of
text on the bad added line, `path` its file); 4 are CLEAN and the right review has ZERO real comments. Marked by
reviewcard.score: caught (a medium / high comment within 3 lines of the planted line), quiet on clean PRs (no medium /
high comment), false alarms (medium / high comments that match no planted problem), verdict. SET stays fixed so cards
from different versions compare."""
from __future__ import annotations

from . import code_repos as R

SET = 1

SHIPPING_PIN = R.SHIPPING.replace('''def shipping_fee(subtotal: int, weight_g: int) -> int:
    """Flat fee + per started kg above 2 kg; free from the free-shipping limit."""
    if subtotal >= config.FREE_SHIPPING_ABOVE:''', '''def shipping_fee(subtotal: int, weight_g: int, pincode: str) -> int:
    """Flat fee + per started kg above 2 kg; free from the free-shipping limit; Rs 30 more outside Maharashtra."""
    if subtotal >= config.FREE_SHIPPING_ABOVE:''').replace(
    "    return config.SHIPPING_FLAT + config.SHIPPING_PER_KG * extra_kg",
    "    far = 0 if str(pincode).startswith(('40', '41', '42', '43', '44')) else 3000\n"
    "    return config.SHIPPING_FLAT + config.SHIPPING_PER_KG * extra_kg + far")

SEARCH = '''import sqlite3


def find_customers(db: sqlite3.Connection, name: str) -> list:
    """Customers whose name starts with the text she typed in the search box."""
    rows = db.execute(f"SELECT id, name, phone FROM customers WHERE name LIKE '{name}%'").fetchall()
    return [{"id": r[0], "name": r[1], "phone": r[2]} for r in rows]
'''
SEARCH_OK = SEARCH.replace('''db.execute(f"SELECT id, name, phone FROM customers WHERE name LIKE '{name}%'")''',
                           '''db.execute("SELECT id, name, phone FROM customers WHERE name LIKE ?", (name + "%",))''')

NOTIFY_OTP = R.NOTIFY + '''

def otp_message(phone: str, otp: str) -> str:
    """The SMS that carries a login OTP."""
    log.info("sending login otp %s to %s", otp, phone)
    return f"Your Hoola shop login code is {otp}. Do not share it."
'''

ORDERS_SWALLOW = R.ORDERS.replace('''    reserved = []
    try:
        for it in cart.items:
            inventory.reserve(it.sku, it.qty)
            reserved.append(it)
    except inventory.OutOfStock:
        inventory.release(reserved)
        raise
''', '''    for it in cart.items:
        try:
            inventory.reserve(it.sku, it.qty)
        except Exception:
            log.debug("reserve skipped for %s", it.sku)
''')

MONEY_TRUNC = R.MONEY.replace('''def pct(amount: int, rate: int) -> int:
    """rate percent of a paise amount, rounded half up."""
    return (amount * rate + 50) // 100''', '''def pct(amount: int, rate: int) -> int:
    """rate percent of a paise amount, rounded half up."""
    return amount * rate // 100''')

HANDLERS_INVOICE = R.HANDLERS + '''

def get_invoice(req) -> dict:
    """{'order_id', 'customer_id'} -> the order's invoice lines."""
    if require(req, "order_id", "customer_id"):
        return {"status": 400, "body": {"error": "order_id and customer_id required"}}
    o = orders.get_order(req["order_id"])
    if o is None:
        return {"status": 404, "body": {"error": "not found"}}
    return {"status": 200, "body": {"invoice": _order_body(o)}}
'''
HANDLERS_INVOICE_OK = HANDLERS_INVOICE.replace('''    o = orders.get_order(req["order_id"])
    if o is None:
        return {"status": 404, "body": {"error": "not found"}}
    return {"status": 200, "body": {"invoice": _order_body(o)}}''', '''    o = orders.get_order(req["order_id"])
    if o is None or o.customer_id != req["customer_id"]:
        return {"status": 404, "body": {"error": "not found"}}
    return {"status": 200, "body": {"invoice": _order_body(o)}}''')

DATES_OFF = R.DATES.replace("    while left > 0:", "    while left >= 0:")

CART_BULK = R.CART + '''

def cart_from_skus(customer_id: str, skus=[]) -> Cart:
    """A cart with one of each SKU (the 'reorder' button)."""
    skus.append("TEA-250")
    cart = Cart(customer_id)
    for sku in skus:
        cart.add(sku)
    return cart
'''

REPORTS_TIDY = R.REPORTS.replace('''def daily_sales(orders) -> dict:
    """Totals of the placed (not cancelled) orders."""
    live = [o for o in orders if o.status != "cancelled"]
    units = Counter()
    for o in live:
        for it in o.items:
            units[it.sku] += it.qty
    return {"orders": len(live), "revenue": sum(o.total for o in live), "units": dict(units)}''', '''def _live(orders) -> list:
    """The orders that count (not cancelled)."""
    return [o for o in orders if o.status != "cancelled"]


def daily_sales(orders) -> dict:
    """Totals of the placed (not cancelled) orders."""
    live = _live(orders)
    units = Counter(it.sku for o in live for it in o.items for _ in range(it.qty))
    return {"orders": len(live), "revenue": sum(o.total for o in live), "units": dict(units)}''')

VALIDATORS_GSTIN = R.VALIDATORS + '''

def is_valid_gstin(gstin: str) -> bool:
    """15-character GSTIN shape: 2-digit state, PAN, entity digit, Z, check character."""
    return isinstance(gstin, str) and bool(re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", gstin))
'''
TEST_GSTIN = '''from app.validators import is_valid_gstin


def test_gstin_shape():
    assert is_valid_gstin("27AAPFU0939F1ZV")
    assert not is_valid_gstin("27AAPFU0939F1Z")
    assert not is_valid_gstin(None)
'''

PRS: list[dict] = [
    # ------------------------------------------------------------ planted problems
    {"id": "caller_not_updated", "title": "Shipping: Rs 30 extra outside Maharashtra",
     "body": "shipping_fee now takes the delivery pincode.",
     "files": {"app/shipping.py": SHIPPING_PIN},
     "bug": {"path": "app/shipping.py", "spot": "def shipping_fee(subtotal: int, weight_g: int, pincode: str)",
             "what": "orders.py and api/handlers.py still call shipping_fee(subtotal, weight) -> TypeError on every order"}},
    {"id": "sql_injection", "title": "Customer search box",
     "body": "Search customers by the start of their name.",
     "files": {"app/search.py": SEARCH},
     "bug": {"path": "app/search.py", "spot": "WHERE name LIKE '{name}%'", "what": "f-string SQL from the search box"}},
    {"id": "otp_in_logs", "title": "Login OTP SMS text", "body": "Adds the OTP SMS message.",
     "files": {"app/notify.py": NOTIFY_OTP},
     "bug": {"path": "app/notify.py", "spot": 'log.info("sending login otp', "what": "the OTP and phone number written to logs"}},
    {"id": "swallowed_stock_error", "title": "Orders: simpler stock reservation",
     "body": "Simplify the reservation loop.", "files": {"app/orders.py": ORDERS_SWALLOW},
     "bug": {"path": "app/orders.py", "spot": "except Exception:",
             "what": "out-of-stock is swallowed, the order is placed anyway (oversell) and nothing is released"}},
    {"id": "rounding_down", "title": "Money: simpler pct()", "body": "Integer maths only.",
     "files": {"app/money.py": MONEY_TRUNC},
     "bug": {"path": "app/money.py", "spot": "return amount * rate // 100",
             "what": "rounds down although the docstring promises half up (999 paise at 5% gives 49, should be 50)"}},
    {"id": "invoice_any_customer", "title": "API: invoice endpoint", "body": "Customers can fetch their invoice.",
     "files": {"app/api/handlers.py": HANDLERS_INVOICE},
     "bug": {"path": "app/api/handlers.py", "spot": 'return {"status": 200, "body": {"invoice": _order_body(o)}}',
             "what": "never checks the order belongs to customer_id: anyone reads anyone's invoice", "near": 4}},
    {"id": "delivery_off_by_one", "title": "Dates: tidy the delivery loop", "body": "Small loop change.",
     "files": {"app/utils/dates.py": DATES_OFF},
     "bug": {"path": "app/utils/dates.py", "spot": "while left >= 0:", "what": "counts one delivery day too many"}},
    {"id": "mutable_default", "title": "Cart: reorder button helper", "body": "Build a cart from a list of SKUs.",
     "files": {"app/cart.py": CART_BULK},
     "bug": {"path": "app/cart.py", "spot": "def cart_from_skus(customer_id: str, skus=[])",
             "what": "mutable default list + append: every reorder keeps adding TEA-250 to the shared default"}},
    # ------------------------------------------------------------ clean (the right review = zero real comments)
    {"id": "clean_search_parameterised", "title": "Customer search box (parameterised)",
     "body": "Search customers by the start of their name.", "files": {"app/search.py": SEARCH_OK}, "bug": None},
    {"id": "clean_invoice_checked", "title": "API: invoice endpoint (owner checked)",
     "body": "Customers can fetch their own invoice; anyone else gets 404.",
     "files": {"app/api/handlers.py": HANDLERS_INVOICE_OK}, "bug": None},
    {"id": "clean_refactor", "title": "Reports: small tidy", "body": "Extract _live(); same numbers.",
     "files": {"app/reports.py": REPORTS_TIDY}, "bug": None},
    {"id": "clean_feature_with_test", "title": "Validators: GSTIN shape check", "body": "Adds is_valid_gstin + a test.",
     "files": {"app/validators.py": VALIDATORS_GSTIN, "tests/test_validators.py": TEST_GSTIN}, "bug": None},
]
