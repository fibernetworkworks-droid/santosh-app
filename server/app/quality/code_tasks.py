"""v0.360 CODE CARD - the fixed set of practice coding jobs Developer Sahayak is scored on.

Each task = a tiny Python repo (files), what she asks (request, kind), and how it is marked:
- check: a hidden Python script that must exit 0 on the repo AFTER Hoola's change (the code really works);
- allow: the files Hoola may change (scope - a fix does not wander into other files);
- forbid / want: project-rule checks on the final text of changed files (e.g. no print(), no f-string SQL);
- must_test: a fix / feature must come with a test that passes (and, for a fix, FAILS on the old code = proves the bug);
- mutant (tests kind): her tests must catch this broken version;
- explain_re (explain kind): the explanation must name the cause, and nothing may change;
- solution: a reference answer, used ONLY by the offline test to prove every check is right (never shown to the model).
The set is fixed (SET) so cards from different versions compare. Requests are in Hinglish, like hers."""
from __future__ import annotations

SET = 1

AGENTS = """# Rules for contributors and coding agents
- Python 3.11. Tests live in tests/ as test_<module>.py, plain pytest functions (no classes).
- Money is integer paise, never float.
- Never use print(); use logging (log = logging.getLogger(__name__)).
- Keep changes small; do not touch unrelated functions.
"""
BASE = {"AGENTS.md": AGENTS, "README.md": "# Shop utils\n\nSmall helpers for the shop app.\n",
        "pyproject.toml": "[project]\nname = \"shop-utils\"\nrequires-python = \">=3.11\"\n\n[tool.pytest.ini_options]\n"
                          "testpaths = [\"tests\"]\n",
        "app/__init__.py": "", "tests/__init__.py": ""}

STATS = '''def average(nums):
    """Mean of a list of numbers."""
    return sum(nums) / len(nums)
'''
STATS_TEST = '''from app.stats import average


def test_average():
    assert average([2, 4]) == 3
'''
PAGING = '''def page(items, n, size=10):
    """Return page n (1-based) of items."""
    start = n * size
    return items[start:start + size]
'''
MONEY = '''def to_paise(rupees: str) -> int:
    """'12.5' -> 1250, '7' -> 700."""
    whole, _, frac = rupees.partition(".")
    return int(whole) * 100 + int(frac or 0)
'''
INVOICE = '''from app.money import to_paise


def invoice_total(lines):
    """lines = [(price_in_rupees_text, qty)] -> total in paise."""
    return sum(to_paise(p) * q for p, q in lines)
'''
TAX = '''"""Tax helpers. Money is integer paise."""


def round_paise(x: float) -> int:
    """Round half up to whole paise."""
    return int(x + 0.5)
'''
VALIDATORS = '''import re


def is_valid_phone(phone: str) -> bool:
    """10-digit Indian mobile starting 6-9."""
    return bool(re.fullmatch(r"[6-9][0-9]{9}", phone))
'''
APP_RULES = "# app/ rules\n- Every function in app/ has type hints on every parameter and the return, and a one-line docstring.\n"
DISCOUNT = '''def apply_discount(price: int, percent: int) -> int:
    """Price in paise after a percent discount; percent is capped to 0..100, so the result is never below 0."""
    percent = max(0, min(100, percent))
    return price - price * percent // 100
'''
TEXT = '''def slug(s: str) -> str:
    """'Hello World!' -> 'hello-world'"""
    out = "".join(c.lower() if c.isalnum() else "-" for c in s)
    while "--" in out:
        out = out.replace("--", "-")
    return out


def slug_keep_case(s: str) -> str:
    """Like slug but keeps case and every hyphen (the old export reads it exactly: do not change)."""
    return "".join(c if c.isalnum() else "-" for c in s)
'''
FMT = '''def format_price(paise: int) -> str:
    """1250 -> '₹12.50'"""
    return f"₹{paise // 100}.{paise % 100:02d}"
'''
CART = '''from app.fmt import format_price


def cart_label(items):
    """items = [(name, paise)] -> 'Total: ₹x.yy'"""
    return "Total: " + format_price(sum(p for _, p in items))
'''
USERS = '''import sqlite3


def find_user(db: sqlite3.Connection, name: str):
    """Return (id, name) or None."""
    return db.execute(f"SELECT id, name FROM users WHERE name = '{name}'").fetchone()
'''
REPORT = '''import logging

log = logging.getLogger(__name__)


def header(title):
    """Report title line."""
    return f"== {title} =="
'''

TASKS: list[dict] = [
    {"id": "fix_empty_average", "kind": "fix",
     "request": "average([]) ZeroDivisionError se crash karta hai. Khaali list par 0 aana chahiye.",
     "files": {"app/stats.py": STATS, "tests/test_stats.py": STATS_TEST},
     "allow": r"^(app/stats\.py|tests/.+\.py)$", "must_test": True,
     "check": "from app.stats import average\nassert average([]) == 0\nassert average([2, 4]) == 3\n",
     "solution": {"app/stats.py": STATS.replace("    return sum(nums) / len(nums)",
                                                "    if not nums:\n        return 0\n    return sum(nums) / len(nums)"),
                  "tests/test_stats.py": STATS_TEST + "\n\ndef test_empty():\n    assert average([]) == 0\n"}},
    {"id": "fix_page_offset", "kind": "fix",
     "request": "page(items, 1) pehle 10 items nahi deta, 11-20 deta hai. Page 1 = pehle 10 items hone chahiye.",
     "files": {"app/paging.py": PAGING},
     "allow": r"^(app/paging\.py|tests/.+\.py)$", "must_test": True,
     "check": ("from app.paging import page\nx = list(range(25))\nassert page(x, 1) == list(range(10))\n"
               "assert page(x, 3) == [20, 21, 22, 23, 24]\nassert page(x, 2, size=5) == [5, 6, 7, 8, 9]\n"),
     "solution": {"app/paging.py": PAGING.replace("start = n * size", "start = (n - 1) * size"),
                  "tests/test_paging.py": "from app.paging import page\n\n\ndef test_first_page():\n"
                                          "    assert page(list(range(25)), 1) == list(range(10))\n"}},
    {"id": "fix_root_cause_elsewhere", "kind": "fix",
     "request": ("Invoice total galat aa raha hai: invoice_total([('12.5', 2)]) 2410 paise deta hai, 2500 hona chahiye.\n"
                 "File \"app/invoice.py\", line 6, in invoice_total"),
     "files": {"app/money.py": MONEY, "app/invoice.py": INVOICE},
     "allow": r"^(app/money\.py|tests/.+\.py)$", "must_test": True,
     "check": ("from app.money import to_paise\nfrom app.invoice import invoice_total\n"
               "assert to_paise('12.5') == 1250\nassert to_paise('12.05') == 1205\nassert to_paise('7') == 700\n"
               "assert to_paise('0.99') == 99\nassert invoice_total([('12.5', 2)]) == 2500\n"),
     "solution": {"app/money.py": MONEY.replace("int(frac or 0)", "int((frac + \"00\")[:2])"),
                  "tests/test_money.py": "from app.money import to_paise\n\n\ndef test_one_decimal():\n"
                                         "    assert to_paise('12.5') == 1250\n"}},
    {"id": "write_gst", "kind": "write",
     "request": ("app/tax.py mein gst_amount(price_paise, rate_percent) jodo jo GST paise mein de, round half up. "
                 "Jaise 10000 paise par 18% = 1800."),
     "files": {"app/tax.py": TAX},
     "allow": r"^(app/tax\.py|tests/.+\.py)$", "must_test": True,
     "check": ("from app.tax import gst_amount\nassert gst_amount(10000, 18) == 1800\nassert gst_amount(999, 5) == 50\n"
               "assert gst_amount(1, 18) == 0\nassert isinstance(gst_amount(333, 18), int)\n"),
     "solution": {"app/tax.py": TAX + '\n\ndef gst_amount(price_paise: int, rate_percent: int) -> int:\n'
                                      '    """GST in paise, round half up."""\n'
                                      '    return (price_paise * rate_percent + 50) // 100\n',
                  "tests/test_tax.py": "from app.tax import gst_amount\n\n\ndef test_gst():\n"
                                       "    assert gst_amount(10000, 18) == 1800\n"}},
    {"id": "write_folder_rules", "kind": "write",
     "request": "app/validators.py mein is_valid_pincode(code) jodo: 6 digit ka Indian PIN code, pehla digit 0 nahi ho sakta.",
     "files": {"app/validators.py": VALIDATORS, "app/AGENTS.md": APP_RULES},
     "allow": r"^(app/validators\.py|tests/.+\.py)$", "must_test": True,
     "check": ("from app.validators import is_valid_pincode as f\nassert f('444001') and f('110011')\n"
               "assert not f('044001') and not f('12345') and not f('44400a') and not f('4440011')\n"
               "assert (f.__doc__ or '').strip(), 'folder rule: docstring'\n"
               "assert 'return' in f.__annotations__ and len(f.__annotations__) >= 2, 'folder rule: type hints'\n"),
     "solution": {"app/validators.py": VALIDATORS + '\n\ndef is_valid_pincode(code: str) -> bool:\n'
                                                    '    """6-digit Indian PIN, first digit 1-9."""\n'
                                                    '    return bool(re.fullmatch(r"[1-9][0-9]{5}", code))\n',
                  "tests/test_validators.py": "from app.validators import is_valid_pincode\n\n\ndef test_pin():\n"
                                              "    assert is_valid_pincode('444001')\n    assert not is_valid_pincode('044001')\n"}},
    {"id": "tests_for_discount", "kind": "tests",
     "request": "app/discount.py ke apply_discount ke liye achhe tests likho (edge cases bhi).",
     "files": {"app/discount.py": DISCOUNT},
     "allow": r"^tests/.+\.py$", "min_tests": 3,
     "mutant": {"app/discount.py": DISCOUNT.replace("    percent = max(0, min(100, percent))\n", "")},
     "check": "",
     "solution": {"tests/test_discount.py": "from app.discount import apply_discount\n\n\ndef test_basic():\n"
                                            "    assert apply_discount(1000, 10) == 900\n\n\ndef test_cap():\n"
                                            "    assert apply_discount(1000, 150) == 0\n\n\ndef test_negative():\n"
                                            "    assert apply_discount(1000, -5) == 1000\n"}},
    {"id": "fix_with_distractor", "kind": "fix",
     "request": "slug('Hello World!') 'hello-world-' deta hai; aakhir (ya shuru) mein hyphen nahi hona chahiye.",
     "files": {"app/text.py": TEXT},
     "allow": r"^(app/text\.py|tests/.+\.py)$", "must_test": True,
     "check": ("from app.text import slug, slug_keep_case\nassert slug('Hello World!') == 'hello-world'\n"
               "assert slug('  A  b ') == 'a-b'\nassert slug_keep_case('Hello World!') == 'Hello-World-', 'distractor changed'\n"),
     "solution": {"app/text.py": TEXT.replace("        out = out.replace(\"--\", \"-\")\n    return out\n",
                                              "        out = out.replace(\"--\", \"-\")\n    return out.strip(\"-\")\n", 1),
                  "tests/test_text.py": "from app.text import slug\n\n\ndef test_no_edge_hyphen():\n"
                                        "    assert slug('Hello World!') == 'hello-world'\n"}},
    {"id": "write_keep_old_calls", "kind": "write",
     "request": ("format_price mein optional currency jodo (default INR = '₹'); currency='USD' par '$12.50' aaye. "
                 "Purane saare calls waise hi chalne chahiye."),
     "files": {"app/fmt.py": FMT, "app/cart.py": CART},
     "allow": r"^(app/fmt\.py|tests/.+\.py)$", "must_test": True,
     "check": ("from app.fmt import format_price\nfrom app.cart import cart_label\nassert format_price(1250) == '₹12.50'\n"
               "assert format_price(1250, 'USD') == '$12.50'\nassert format_price(1250, currency='INR') == '₹12.50'\n"
               "assert format_price(5) == '₹0.05'\nassert cart_label([('a', 1000), ('b', 250)]) == 'Total: ₹12.50'\n"),
     "solution": {"app/fmt.py": 'SYMBOLS = {"INR": "₹", "USD": "$"}\n\n\ndef format_price(paise: int, currency: str = "INR") -> str:\n'
                                '    """1250 -> \'₹12.50\'"""\n'
                                '    return f"{SYMBOLS[currency]}{paise // 100}.{paise % 100:02d}"\n',
                  "tests/test_fmt.py": "from app.fmt import format_price\n\n\ndef test_usd():\n"
                                       "    assert format_price(1250, 'USD') == '$12.50'\n"}},
    {"id": "docs_readme", "kind": "docs",
     "request": "README mein format_price ka 'Usage' section likho, ek chhote example ke saath (input aur output dono).",
     "files": {"app/fmt.py": FMT},
     "allow": r"^(README\.md|docs/.+)$",
     "check": ("t = open('README.md', encoding='utf-8').read()\nassert 'format_price' in t\n"
               "assert '12.50' in t or '1250' in t, 'example'\nassert 'usage' in t.lower()\n"),
     "solution": {"README.md": BASE["README.md"] + "\n## Usage\n\n```python\nfrom app.fmt import format_price\n"
                                                   "format_price(1250)  # '₹12.50'\n```\n"}},
    {"id": "explain_only", "kind": "explain",
     "request": "average([]) kyon crash hota hai? Sirf samjhao, kuch badlo mat.",
     "files": {"app/stats.py": STATS},
     "allow": r"^$", "explain_re": r"len|zero|0 se|khaali|empty",
     "check": "", "solution": {}},
    {"id": "fix_sql_injection", "kind": "fix",
     "request": "find_user(db, \"O'Brien\") sqlite3.OperationalError deta hai. Har naam par sahi chalna chahiye.",
     "files": {"app/users.py": USERS},
     "allow": r"^(app/users\.py|tests/.+\.py)$", "must_test": True,
     "forbid": [[r"^app/users\.py$", r"f[\"'][^\"']*SELECT|SELECT[^\n]*%\s*\(|SELECT[^\n]*\.format\(|SELECT[^\n]*\+\s*name"]],
     "check": ("import sqlite3\nfrom app.users import find_user\ndb = sqlite3.connect(':memory:')\n"
               "db.execute('CREATE TABLE users (id INTEGER, name TEXT)')\n"
               "db.executemany('INSERT INTO users VALUES (?, ?)', [(1, \"O'Brien\"), (2, 'alice')])\n"
               "assert find_user(db, \"O'Brien\") == (1, \"O'Brien\")\nassert find_user(db, 'alice') == (2, 'alice')\n"
               "assert find_user(db, \"x' OR '1'='1\") is None, 'injection'\n"),
     "solution": {"app/users.py": USERS.replace("f\"SELECT id, name FROM users WHERE name = '{name}'\")",
                                                "\"SELECT id, name FROM users WHERE name = ?\", (name,))"),
                  "tests/test_users.py": "import sqlite3\n\nfrom app.users import find_user\n\n\ndef test_quote():\n"
                                         "    db = sqlite3.connect(':memory:')\n"
                                         "    db.execute('CREATE TABLE users (id INTEGER, name TEXT)')\n"
                                         "    db.execute('INSERT INTO users VALUES (1, ?)', (\"O'Brien\",))\n"
                                         "    assert find_user(db, \"O'Brien\") == (1, \"O'Brien\")\n"}},
    {"id": "write_root_rules", "kind": "write",
     "request": ("app/report.py mein summarize(rows) jodo: rows = [{'amt': paise}], jawab {'count': kitni rows, "
                 "'total': amt ka jod}; aur ek info log line likho jisme count ho."),
     "files": {"app/report.py": REPORT},
     "allow": r"^(app/report\.py|tests/.+\.py)$", "must_test": True,
     "forbid": [[r"^app/", r"(?<![\w.])print\("]],
     "want": [[r"^app/report\.py$", r"log\.(info|debug)\("]],
     "check": ("from app.report import summarize\nassert summarize([{'amt': 5}, {'amt': 7}]) == {'count': 2, 'total': 12}\n"
               "assert summarize([]) == {'count': 0, 'total': 0}\n"),
     "solution": {"app/report.py": REPORT + '\n\ndef summarize(rows):\n    """Count and total of amt."""\n'
                                            '    total = sum(r["amt"] for r in rows)\n'
                                            '    log.info("summarized %d rows", len(rows))\n'
                                            '    return {"count": len(rows), "total": total}\n',
                  "tests/test_report.py": "from app.report import summarize\n\n\ndef test_sum():\n"
                                          "    assert summarize([{'amt': 5}]) == {'count': 1, 'total': 5}\n"}},
]


def repo(task: dict) -> dict[str, str]:
    """The task's whole starting repo (the shared base + its own files)."""
    return {**BASE, **task["files"]}
