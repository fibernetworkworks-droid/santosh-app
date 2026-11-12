#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.848.0", "+847", "0.847.0", "+846"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.847\.0", NEW, t)
    t = re.sub(r"\+846\b", NEW_B, t)
    if t != o:
        f.write_text(t, encoding="utf-8")
        n += 1
print("tests swept:", n)
p = ROOT / "pubspec.yaml"
t, k = re.subn(r"version: 0\.\d+\.\d+\+\d+", f"version: {NEW}{NEW_B}", p.read_text(), count=1)
p.write_text(t)
print("pubspec:", k)
for f in sorted((ROOT / "server/app/static/console").glob("*.html")):
    t = f.read_text()
    if f"v={OLD}" in t:
        print("stamps:", f.name, t.count(f"v={OLD}"))
        f.write_text(t.replace(f"v={OLD}", f"v={NEW}"))
m = ROOT / "server/app/main.py"
t = m.read_text()
ol = re.search(r'^APP_VERSION = "0\.847\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.848.0 BAHI A9 - her book and the CA hand-off (owner: "GO A9"): NEW bahi/book.py - the register becomes Tally voucher XML (Sales, Credit Note, Purchase, Debit Note, Receipt, '
         'Payment from the bank lines she confirmed) that balances to the paisa, with GST tax ledgers (a lump tax figure becomes IGST or CGST + SGST by the party state, never "round '
         'off"), party ledgers created in the same file and ledger names that are HERS (acc_book_cfg); a JSON copy of the vouchers; ONE monthly CA pack ZIP (vouchers, register, parties, '
         'the 2B worksheet with her decisions, the GSTR-1 / 3B worksheets Hoola prepared, the bank reconciliation, the TDS register, the bills she sent, and OPEN-QUESTIONS.txt = '
         'everything Hoola was not sure of; a fixed zip stamp so the same books give the same hash); she closes the month on the pack\'s hash and it locks in the register; '
         '/api/bahi/book/* and /pack/*; console CA pack tab + a party form on Pay + TDS; 5 tests. NOT BUILT: Zoho Books over OAuth, live Tally (frozen PC code), a CA login that closes '
         'a month (A11). NOT VERIFIED in a real Tally import. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
