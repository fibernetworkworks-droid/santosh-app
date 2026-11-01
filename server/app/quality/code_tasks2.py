"""v0.365 HARD CARD - set 2 of the coding card (owner: "GO HARD CARD"). Set 1 was 12/12: tiny repos, one file each.

Set 2 works on the two bigger projects in code_repos (DUKAAN Python 30 files, HISAAB JavaScript 13 files) and asks for what
real work needs: a feature across 4-5 files, a rename with every caller + an alias, bugs whose cause is far from the symptom
(a shared default list, a reservation leak seen only in a failing test run, Sundays counted in a date sum), an access-control
hole, a refactor that must not change behaviour, a setting hard-coded in three places, a folder rules file, two JavaScript
jobs, and a vague ask that must be answered with ONE question instead of a guess. Same marking as set 1 (codecard.score)."""
from __future__ import annotations

import re

from . import code_repos as R

SET = 2
STEPS, MINUTES = 40, 8.0

# ---------------------------------------------------------------- files that differ per job
CART_SHARED = R.CART.replace('''    def __init__(self, customer_id: str, items=None):
        self.customer_id = customer_id
        self.items = items if items is not None else []''', '''    def __init__(self, customer_id: str, items=[]):
        self.customer_id = customer_id
        self.items = items''')
DATES_BUG = '''from datetime import date, timedelta


def delivery_date(placed: date, days: int) -> date:
    """placed + `days` delivery days; there is no delivery on Sunday, so Sundays are not counted."""
    d = placed + timedelta(days=days)
    if d.weekday() == 6:
        d += timedelta(days=1)
    return d
'''
ORDERS_LEAK = R.ORDERS.replace('''    reserved = []
    try:
        for it in cart.items:
            inventory.reserve(it.sku, it.qty)
            reserved.append(it)
    except inventory.OutOfStock:
        inventory.release(reserved)
        raise
''', '''    for it in cart.items:
        inventory.reserve(it.sku, it.qty)
''')
TEST_ORDERS_LEAK = R.TEST_ORDERS.replace("from app import inventory\n", "import pytest\n\nfrom app import inventory\n") + '''

def test_failed_order_keeps_stock():
    c = Cart("c1")
    c.add("TEA-250", 2)
    c.add("KETTLE", 9)                        # only 5 kettles
    with pytest.raises(inventory.OutOfStock):
        place_order(c)
    assert inventory.STOCK["TEA-250"] == 50
'''
LEAK_RUN = '''$ python -m pytest -q
..F.
=================================== FAILURES ===================================
________________________ test_failed_order_keeps_stock _________________________

    def test_failed_order_keeps_stock():
        c = Cart("c1")
        c.add("TEA-250", 2)
        c.add("KETTLE", 9)                        # only 5 kettles
        with pytest.raises(inventory.OutOfStock):
            place_order(c)
>       assert inventory.STOCK["TEA-250"] == 50
E       assert 48 == 50

tests/test_orders.py:21: AssertionError
1 failed, 4 passed in 0.03s'''
HANDLERS_IDOR = R.HANDLERS.replace('''def get_order(req) -> dict:
    """{'order_id', 'customer_id'} -> the order."""
    if require(req, "order_id", "customer_id"):
        return {"status": 400, "body": {"error": "order_id and customer_id required"}}
    o = orders.get_order(req["order_id"])
    if o is None or o.customer_id != req["customer_id"]:''', '''def get_order(req) -> dict:
    """{'order_id'} -> the order."""
    if require(req, "order_id"):
        return {"status": 400, "body": {"error": "order_id required"}}
    o = orders.get_order(req["order_id"])
    if o is None:''')
ORDERS_LONG = '''import logging

from app import config, inventory
from app.catalog import find_product
from app.discounts import COUPONS
from app.models import Order
from app.utils.ids import next_id

log = logging.getLogger(__name__)
ORDERS: dict = {}


def place_order(cart, coupon: str = "", payment: str = "prepaid") -> Order:
    """Reserve stock and record the order. Raises ValueError / OutOfStock."""
    # check the cart
    if not cart.items:
        raise ValueError("empty cart")
    if payment not in ("prepaid", "cod"):
        raise ValueError("payment")
    # subtotal
    subtotal = 0
    for it in cart.items:
        subtotal += it.qty * it.price
    # coupon
    discount = 0
    if coupon:
        off = COUPONS.get(coupon.upper())
        if off is None:
            raise ValueError("unknown coupon")
        discount = (subtotal * off + 50) // 100
        if discount > config.COUPON_CAP:
            discount = config.COUPON_CAP
    # stock
    reserved = []
    for it in cart.items:
        if inventory.STOCK.get(it.sku, 0) < it.qty:
            for r in reserved:
                inventory.STOCK[r.sku] = inventory.STOCK.get(r.sku, 0) + r.qty
            raise inventory.OutOfStock(it.sku)
        inventory.STOCK[it.sku] -= it.qty
        reserved.append(it)
    # gst
    taxable = subtotal - discount
    gst = (taxable * config.GST_RATE + 50) // 100
    # shipping
    weight = 0
    for it in cart.items:
        weight += find_product(it.sku).weight_g * it.qty
    if subtotal >= config.FREE_SHIPPING_ABOVE:
        ship = 0
    else:
        extra_kg = (weight - 2000 + 999) // 1000
        if extra_kg < 0:
            extra_kg = 0
        ship = config.SHIPPING_FLAT + config.SHIPPING_PER_KG * extra_kg
    # total
    total = taxable + gst + ship
    o = Order(next_id("O"), cart.customer_id, list(cart.items), subtotal, discount, gst, ship, total, payment)
    ORDERS[o.id] = o
    log.info("order %s placed, total %d", o.id, total)
    return o
''' + R.ORDERS[R.ORDERS.index("\n\ndef cancel_order"):]
JS_GST_FIXED = R.JS_GST.replace("  return { cgst: Math.floor(gst / 2), sgst: Math.floor(gst / 2) };",
                                "  const cgst = Math.floor(gst / 2);\n  return { cgst, sgst: gst - cgst };")
JS_FORMAT_INR = R.JS_FORMAT + '''
/** paise -> "Rs 12,34,567.50" (Indian grouping: last 3 digits, then pairs) */
export function formatINR(paise) {
  const sign = paise < 0 ? "-" : "";
  const [r, p] = plain(Math.abs(paise)).split(".");
  const last3 = r.slice(-3);
  const rest = r.slice(0, -3);
  const grouped = rest ? rest.replace(/\\B(?=(\\d{2})+(?!\\d))/g, ",") + "," + last3 : last3;
  return `${sign}Rs ${grouped}.${p}`;
}
'''
PY_RUN_ORDERS = '''from app import inventory, orders
from app.cart import Cart


def run(items, coupon="", pay="prepaid"):
    c = Cart("c9")
    for s, q in items:
        c.add(s, q)
    o = orders.place_order(c, coupon, pay)
    return (o.subtotal, o.discount, o.gst, o.shipping, o.total)


'''

TASKS: list[dict] = [
    {"id": "feature_cod_fee", "kind": "write", "repo": "dukaan",
     "request": ("Cash on delivery (payment='cod') par Rs 40 ka COD fee lagao. Order total mein jude (COD fee par GST nahi), "
                 "Order mein alag cod_fee field ho, aur create_order aur quote dono ke jawab mein 'cod_fee' dikhe "
                 "(quote ko bhi payment de sakte hain). Prepaid par cod_fee 0."),
     "files": {}, "must_test": True,
     "allow": r"^(app/(config|models|orders|notify)\.py|app/api/handlers\.py|tests/.+\.py)$",
     "want": [[r"^app/config\.py$", r"COD_FEE\s*=\s*4000"]],
     "check": ("from app import config, orders\nfrom app.api import handlers as h\n"
               "b = h.create_order({'customer_id': 'c1', 'items': [['TEA-250', 1]]})\nassert b['status'] == 201, b\n"
               "assert b['body'].get('cod_fee') == 0 and b['body']['total'] == 26140, b\n"
               "r = h.create_order({'customer_id': 'c1', 'items': [['TEA-250', 1]], 'payment': 'cod'})\n"
               "assert r['status'] == 201 and r['body']['cod_fee'] == 4000 and r['body']['total'] == 30140, r\n"
               "o = orders.get_order(r['body']['id'])\nassert o.cod_fee == 4000 and o.total == 30140 and o.gst == 3240\n"
               "q = h.quote({'items': [['TEA-250', 1]], 'payment': 'cod'})['body']\n"
               "assert q['cod_fee'] == 4000 and q['total'] == 30140, q\n"
               "q = h.quote({'items': [['TEA-250', 1]]})['body']\nassert q['cod_fee'] == 0 and q['total'] == 26140, q\n"),
     "solution": {
         "app/config.py": R.CONFIG + "COD_FEE = 4000               # cash on delivery, no GST on it\n",
         "app/models.py": R.MODELS.replace('    status: str = "placed"\n', '    status: str = "placed"\n    cod_fee: int = 0\n'),
         "app/orders.py": R.ORDERS.replace("from app import inventory, tax", "from app import config, inventory, tax")
                                  .replace("    total = taxable + g + ship\n    o = Order(next_id(\"O\"), cart.customer_id, "
                                           "list(cart.items), subtotal, discount, g, ship, total, payment)",
                                           "    cod = config.COD_FEE if payment == \"cod\" else 0\n"
                                           "    total = taxable + g + ship + cod\n    o = Order(next_id(\"O\"), cart.customer_id, "
                                           "list(cart.items), subtotal, discount, g, ship, total, payment, cod_fee=cod)"),
         "app/api/handlers.py": R.HANDLERS.replace("from app import inventory, orders, tax",
                                                   "from app import config, inventory, orders, tax")
                                          .replace('"payment": o.payment, "status": o.status}',
                                                   '"payment": o.payment, "status": o.status, "cod_fee": o.cod_fee}')
                                          .replace("    ship = shipping_fee(subtotal, cart.weight_g())\n    return {",
                                                   "    ship = shipping_fee(subtotal, cart.weight_g())\n"
                                                   "    cod = config.COD_FEE if req.get(\"payment\") == \"cod\" else 0\n    return {")
                                          .replace('"total": subtotal - discount + g + ship, "free_above": 49900}}',
                                                   '"total": subtotal - discount + g + ship + cod, "cod_fee": cod, '
                                                   '"free_above": 49900}}'),
         "tests/test_cod.py": "from app.api import handlers as h\n\n\ndef test_cod_fee():\n"
                              "    r = h.create_order({'customer_id': 'c1', 'items': [['TEA-250', 1]], 'payment': 'cod'})\n"
                              "    assert r['body']['cod_fee'] == 4000\n"}},
    {"id": "rename_with_alias", "kind": "write", "repo": "dukaan",
     "request": ("discounts.apply_coupon ka naam redeem_coupon karo aur har jagah (orders, API) naya naam use karo. "
                 "Purana naam ek release ke liye kaam karta rahe (AGENTS.md)."),
     "files": {},
     "allow": r"^(app/(discounts|orders)\.py|app/api/handlers\.py|tests/.+\.py|docs/.+|README\.md)$",
     "check": ("import pathlib\nfrom app import discounts\nfrom app.api import handlers as h\n"
               "assert discounts.redeem_coupon('DIWALI10', 10000) == 1000\n"
               "assert discounts.apply_coupon('DIWALI10', 10000) == 1000, 'old name must stay as an alias'\n"
               "for p in pathlib.Path('app').rglob('*.py'):\n"
               "    if p.name != 'discounts.py':\n        assert 'apply_coupon' not in p.read_text(), f'old name still used in {p}'\n"
               "assert h.quote({'items': [['TEA-250', 1]], 'coupon': 'DIWALI10'})['body']['discount'] == 1800\n"
               "assert h.create_order({'customer_id': 'c', 'items': [['TEA-250', 1]], 'coupon': 'diwali10'})['body']['discount'] == 1800\n"),
     "solution": {
         "app/discounts.py": R.DISCOUNTS.replace("def apply_coupon(", "def redeem_coupon(")
                             + "\n\napply_coupon = redeem_coupon   # old name, kept for one release\n",
         "app/orders.py": R.ORDERS.replace("apply_coupon", "redeem_coupon"),
         "app/api/handlers.py": R.HANDLERS.replace("apply_coupon", "redeem_coupon")}},
    {"id": "fix_shared_default", "kind": "fix", "repo": "dukaan",
     "request": ("Production mein ek customer ke cart mein doosre customer ke items dikh rahe hain. Repro: "
                 "Cart('a').add('TEA-250') ke baad Cart('b').items mein bhi TEA-250 hai."),
     "files": {"app/cart.py": CART_SHARED}, "must_test": True,
     "allow": r"^(app/cart\.py|tests/.+\.py)$",
     "check": ("from app.cart import Cart\na = Cart('a')\na.add('TEA-250')\nb = Cart('b')\nassert b.items == [], b.items\n"
               "b.add('MUG')\nassert [i.sku for i in a.items] == ['TEA-250'] and [i.sku for i in b.items] == ['MUG']\n"
               "from app.models import LineItem\nc = Cart('c', [LineItem('MUG', 1, 24900)])\nc.add('TEA-250')\n"
               "assert [i.sku for i in c.items] == ['MUG', 'TEA-250'], 'items passed in must be kept'\n"
               "assert Cart('d').items == [] and Cart('e', None).items == []\n"),
     "solution": {"app/cart.py": R.CART,
                  "tests/test_cart.py": R.TEST_CART + "\n\ndef test_carts_do_not_share_items():\n    Cart('a').add('TEA-250')\n"
                                                      "    assert Cart('b').items == []\n"}},
    {"id": "fix_sunday_count", "kind": "fix", "repo": "dukaan",
     "request": ("Wednesday 4 Nov 2026 ko order hua, 5 din ki delivery: system Monday 9 Nov dikhata hai. Beech ka Sunday "
                 "delivery din nahi hai, isliye Tuesday 10 Nov aana chahiye."),
     "files": {"app/utils/dates.py": DATES_BUG}, "must_test": True,
     "allow": r"^(app/utils/dates\.py|tests/.+\.py)$",
     "check": ("from datetime import date\nfrom app.utils.dates import delivery_date as f\n"
               "assert f(date(2026, 11, 4), 5) == date(2026, 11, 10)\nassert f(date(2026, 11, 7), 1) == date(2026, 11, 9)\n"
               "assert f(date(2026, 11, 7), 2) == date(2026, 11, 10)\nassert f(date(2026, 11, 1), 6) == date(2026, 11, 7)\n"
               "assert f(date(2026, 11, 4), 0) == date(2026, 11, 4)\nassert f(date(2026, 11, 2), 13) == date(2026, 11, 17)\n"),
     "solution": {"app/utils/dates.py": R.DATES,
                  "tests/test_dates.py": "from datetime import date\n\nfrom app.utils.dates import delivery_date\n\n\n"
                                         "def test_sunday_not_counted():\n"
                                         "    assert delivery_date(date(2026, 11, 4), 5) == date(2026, 11, 10)\n"}},
    {"id": "fix_from_test_run", "kind": "fix", "repo": "dukaan",
     "request": "CI laal hai. Yeh run dekho aur asli wajah theek karo (test galat nahi hai):\n" + LEAK_RUN,
     "files": {"app/orders.py": ORDERS_LEAK, "tests/test_orders.py": TEST_ORDERS_LEAK},
     "allow": r"^(app/(orders|inventory)\.py|tests/.+\.py)$",
     # the red test must stay exactly as it is (adding tests next to it is fine)
     "want": [[r"^tests/test_orders\.py$", re.escape(TEST_ORDERS_LEAK[TEST_ORDERS_LEAK.index("def test_failed_order_keeps_stock"):].rstrip())]],
     "check": ("from app import inventory, orders\nfrom app.cart import Cart\n"
               "c = Cart('c1')\nc.add('TEA-250', 2)\nc.add('MUG', 1)\nc.add('KETTLE', 9)\n"
               "try:\n    orders.place_order(c)\n    raise SystemExit('expected OutOfStock')\nexcept inventory.OutOfStock:\n    pass\n"
               "assert inventory.STOCK == {'TEA-250': 50, 'SUGAR-1K': 100, 'MUG': 20, 'KETTLE': 5}, inventory.STOCK\n"
               "c = Cart('c1')\nc.add('TEA-250', 2)\norders.place_order(c)\nassert inventory.STOCK['TEA-250'] == 48\n"
               "c = Cart('c1')\nc.add('TEA-250', 1)\ntry:\n    orders.place_order(c, 'NOPE')\nexcept ValueError:\n    pass\n"
               "assert inventory.STOCK['TEA-250'] == 48, 'a bad coupon must not take stock'\n"),
     "solution": {"app/orders.py": R.ORDERS}},
    {"id": "fix_access_control", "kind": "fix", "repo": "dukaan",
     "request": ("API ka get_order: koi bhi order_id bhej ke kisi ka bhi order dekh sakta hai. Sirf usi customer ko apna order "
                 "mile (request mein customer_id); kisi aur ko bilkul wahi jawab mile jo galat order_id par milta hai."),
     "files": {"app/api/handlers.py": HANDLERS_IDOR}, "must_test": True,
     "allow": r"^(app/api/handlers\.py|tests/.+\.py)$",
     "check": ("from app.api import handlers as h\n"
               "o = h.create_order({'customer_id': 'c1', 'items': [['MUG', 1]]})['body']\n"
               "own = h.get_order({'order_id': o['id'], 'customer_id': 'c1'})\nassert own['status'] == 200 and own['body']['id'] == o['id']\n"
               "other = h.get_order({'order_id': o['id'], 'customer_id': 'c2'})\n"
               "unknown = h.get_order({'order_id': 'O99999', 'customer_id': 'c2'})\n"
               "assert other['status'] == 404 and other == unknown, (other, unknown)\n"
               "assert h.get_order({'order_id': o['id']})['status'] in (400, 404)\n"
               "assert h.get_order(None)['status'] == 400\n"),
     "solution": {"app/api/handlers.py": R.HANDLERS,
                  "tests/test_api.py": "from app.api import handlers as h\n\n\ndef test_other_customer_gets_404():\n"
                                       "    o = h.create_order({'customer_id': 'c1', 'items': [['MUG', 1]]})['body']\n"
                                       "    assert h.get_order({'order_id': o['id'], 'customer_id': 'c2'})['status'] == 404\n"}},
    {"id": "js_fix_gst_split", "kind": "fix", "repo": "hisaab", "lang": "js",
     "request": ("Same-state invoice mein CGST + SGST jodne par total GST se 1 paisa kam aata hai (jaise 10005 paise ke bill "
                 "par). Theek karo."),
     "files": {}, "must_test": True,
     "allow": r"^(src/gst\.js|test/.+\.js)$",
     "check": ('import assert from "node:assert/strict";\nimport { splitGst } from "./src/gst.js";\n'
               'import { buildInvoice } from "./src/invoice.js";\n'
               'for (const g of [0, 1, 2, 3, 1799, 1801, 3601]) {\n  const s = splitGst(g, false);\n'
               '  assert.equal(s.cgst + s.sgst, g);\n  assert.ok(Math.abs(s.cgst - s.sgst) <= 1);\n}\n'
               'assert.deepEqual(splitGst(3601, true), { igst: 3601 });\n'
               'const inv = buildInvoice([{ name: "x", qty: 1, price: 10005 }]);\n'
               'assert.equal(inv.gst, 1801);\nassert.equal(inv.cgst + inv.sgst, inv.gst);\n'),
     "solution": {"src/gst.js": JS_GST_FIXED,
                  "test/gst.test.js": 'import { test } from "node:test";\nimport assert from "node:assert/strict";\n'
                                      'import { splitGst } from "../src/gst.js";\n\ntest("halves add up", () => {\n'
                                      '  const s = splitGst(1801, false);\n  assert.equal(s.cgst + s.sgst, 1801);\n});\n'}},
    {"id": "js_write_inr", "kind": "write", "repo": "hisaab", "lang": "js",
     "request": ("src/format.js mein formatINR(paise) jodo, Indian grouping ke saath: 123456750 -> 'Rs 12,34,567.50', "
                 "5 -> 'Rs 0.05', -150000 -> '-Rs 1,500.00'."),
     "files": {}, "must_test": True,
     "allow": r"^(src/(format|index)\.js|test/.+\.js|README\.md)$",
     "check": ('import assert from "node:assert/strict";\nimport { formatINR } from "./src/format.js";\n'
               'import * as idx from "./src/index.js";\n'
               'const want = [[123456750, "Rs 12,34,567.50"], [5, "Rs 0.05"], [-150000, "-Rs 1,500.00"], '
               '[99900, "Rs 999.00"], [10000000, "Rs 1,00,000.00"], [0, "Rs 0.00"], [100000000000, "Rs 1,00,00,00,000.00"]];\n'
               'for (const [p, s] of want) assert.equal(formatINR(p), s);\n'
               'assert.equal(typeof idx.formatINR, "function", "AGENTS.md: export it from src/index.js");\n'),
     "solution": {"src/format.js": JS_FORMAT_INR,
                  "src/index.js": R.JS_INDEX.replace('export { formatPlain } from "./format.js";',
                                                     'export { formatPlain, formatINR } from "./format.js";'),
                  "test/format.test.js": 'import { test } from "node:test";\nimport assert from "node:assert/strict";\n'
                                         'import { formatINR } from "../src/format.js";\n\ntest("indian grouping", () => {\n'
                                         '  assert.equal(formatINR(123456750), "Rs 12,34,567.50");\n});\n'}},
    {"id": "vague_ask", "kind": "fix", "repo": "dukaan", "ask": True,
     "request": "Checkout mein kuch gadbad hai, theek kar do.",
     "files": {}, "allow": r"^$", "check": "", "solution": {}},
    {"id": "refactor_same_behaviour", "kind": "write", "repo": "dukaan",
     "request": ("orders.place_order bahut lamba hai aur jo kaam cart, discounts, inventory, tax aur shipping ke helpers "
                 "pehle se karte hain wahi khud dobara karta hai. Ise chhota karo aur un helpers ko use karo. Behaviour "
                 "bilkul same rahe."),
     "files": {"app/orders.py": ORDERS_LONG},
     "allow": r"^(app/orders\.py|tests/.+\.py)$",
     "check": (PY_RUN_ORDERS + "import inspect\nsrc = inspect.getsource(orders.place_order)\n"
               "assert len(src.splitlines()) <= 32, f'still {len(src.splitlines())} lines'\n"
               "assert 'STOCK' not in src and 'COUPONS' not in src, 'helpers not used'\n"
               "assert run([('TEA-250', 1)]) == (18000, 0, 3240, 4900, 26140)\n"
               "assert run([('SUGAR-1K', 3)]) == (15600, 0, 2808, 6900, 25308)\n"
               "assert run([('KETTLE', 1), ('MUG', 1)], 'diwali10') == (154800, 15480, 25078, 0, 164398)\n"
               "assert run([('SUGAR-1K', 4)], 'WELCOME50', 'cod') == (20800, 10400, 1872, 8900, 21172)\n"
               "before = dict(inventory.STOCK)\nfor bad in ([('TEA-250', 1), ('KETTLE', 99)],):\n"
               "    try:\n        run(bad)\n        raise SystemExit('expected OutOfStock')\n"
               "    except inventory.OutOfStock:\n        pass\nassert inventory.STOCK == before\n"
               "for args in (([('TEA-250', 1)], 'NOPE'), ([('TEA-250', 1)], '', 'card')):\n"
               "    try:\n        run(*args)\n        raise SystemExit('expected ValueError')\n    except ValueError:\n        pass\n"
               "try:\n    orders.place_order(Cart('x'))\n    raise SystemExit('expected ValueError')\nexcept ValueError:\n    pass\n"
               "assert inventory.STOCK == before\n"),
     "solution": {"app/orders.py": R.ORDERS}},
    {"id": "setting_everywhere", "kind": "write", "repo": "dukaan",
     "request": "Free shipping ki limit Rs 499 se badha kar Rs 999 karo.",
     "files": {},
     "allow": r"^(app/(config|shipping|notify)\.py|app/api/handlers\.py|tests/.+\.py|docs/.+|README\.md)$",
     "check": ("import pathlib\nfrom app import config, notify\nfrom app.api import handlers as h\n"
               "from app.shipping import shipping_fee\nassert config.FREE_SHIPPING_ABOVE == 99900\n"
               "assert shipping_fee(60000, 500) == 4900 and shipping_fee(99900, 500) == 0\n"
               "assert h.quote({'items': [['MUG', 3]]})['body']['shipping'] == 4900\n"
               "assert h.quote({'items': [['MUG', 3]]})['body']['free_above'] == 99900, 'quote still says 499'\n"
               "n = notify.shipping_note()\nassert '999' in n and '499' not in n, n\n"
               "for p in pathlib.Path('app').rglob('*.py'):\n    assert '49900' not in p.read_text(), f'old limit left in {p}'\n"),
     "solution": {"app/config.py": R.CONFIG.replace("FREE_SHIPPING_ABOVE = 49900   # orders from Rs 499 ship free",
                                                    "FREE_SHIPPING_ABOVE = 99900   # orders from Rs 999 ship free"),
                  "app/api/handlers.py": R.HANDLERS.replace("from app import inventory, orders, tax",
                                                            "from app import config, inventory, orders, tax")
                                                   .replace('"free_above": 49900', '"free_above": config.FREE_SHIPPING_ABOVE'),
                  "app/notify.py": R.NOTIFY.replace("from app.money import fmt", "from app import config\nfrom app.money import fmt")
                                          .replace('return "Free shipping on orders from Rs 499!"',
                                                   'return f"Free shipping on orders from Rs {config.FREE_SHIPPING_ABOVE // 100}!"')}},
    {"id": "folder_rules_handler", "kind": "write", "repo": "dukaan",
     "request": ("API mein cancel_order handler jodo: order_id aur customer_id aayenge; sirf apna order cancel ho, stock wapas "
                 "aaye, jawab mein cancelled order."),
     "files": {}, "must_test": True,
     "allow": r"^(app/api/handlers\.py|app/orders\.py|tests/.+\.py)$",
     "check": ("import inspect\nfrom app import inventory\nfrom app.api import handlers as h\n"
               "assert 'require(' in inspect.getsource(h.cancel_order), 'app/api/AGENTS.md: check keys with require()'\n"
               "o = h.create_order({'customer_id': 'c1', 'items': [['MUG', 2]]})['body']\nassert inventory.STOCK['MUG'] == 18\n"
               "r = h.cancel_order({'order_id': o['id'], 'customer_id': 'c2'})\nassert r['status'] == 404, r\n"
               "assert inventory.STOCK['MUG'] == 18\n"
               "r = h.cancel_order({'order_id': o['id'], 'customer_id': 'c1'})\n"
               "assert r['status'] == 200 and r['body']['status'] == 'cancelled' and r['body']['id'] == o['id'], r\n"
               "assert inventory.STOCK['MUG'] == 20\n"
               "assert h.cancel_order({'order_id': o['id'], 'customer_id': 'c1'})['status'] == 200 and inventory.STOCK['MUG'] == 20\n"
               "assert h.cancel_order({'order_id': 'O99999', 'customer_id': 'c1'})['status'] == 404\n"
               "for bad in (None, {}, {'order_id': o['id']}, 'x', 5, []):\n    assert h.cancel_order(bad)['status'] == 400, bad\n"),
     "solution": {"app/api/handlers.py": R.HANDLERS + '''

def cancel_order(req) -> dict:
    """{'order_id', 'customer_id'} -> the cancelled order (stock returned)."""
    if require(req, "order_id", "customer_id"):
        return {"status": 400, "body": {"error": "order_id and customer_id required"}}
    o = orders.get_order(req["order_id"])
    if o is None or o.customer_id != req["customer_id"]:
        return {"status": 404, "body": {"error": "not found"}}
    return {"status": 200, "body": _order_body(orders.cancel_order(o.id))}
''',
                  "tests/test_api.py": "from app.api import handlers as h\n\n\ndef test_cancel_own_order():\n"
                                       "    o = h.create_order({'customer_id': 'c1', 'items': [['MUG', 1]]})['body']\n"
                                       "    r = h.cancel_order({'order_id': o['id'], 'customer_id': 'c1'})\n"
                                       "    assert r['body']['status'] == 'cancelled'\n"}},
]

for _t in TASKS:
    _t["base"] = R.HISAAB if _t["repo"] == "hisaab" else R.DUKAAN
