#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.849.0", "+848", "0.848.0", "+847"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.848\.0", NEW, t)
    t = re.sub(r"\+847\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.848\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.849.0 BAHI A10 - month-end and year-end (owner: "GO A10"): NEW bahi/closing.py - the month-end CHECKLIST ticked only from records (bills drafts, bank lines and the stored '
         'reconciliation, 2B decisions and what reached the portal, IRNs, GSTR-1 / 3B filed or saved, TDS deposited, month closed on a pack; payroll and accruals shown as "not tracked here", '
         'never ticked), each line with its due date and a button to the tab that fixes it; the MIS (sales, purchases, a margin on purchases labelled as not a true gross profit, bank '
         'cash in / out, receivables and payables with what is overdue) and the DAILY CASH LINE as text (money in and out today, who is due tomorrow); ONE calendar = the monthly dates '
         '(due_dates.json) + the yearly ones (new rules file annual.json: the 30 Nov credit cliff with the bills and credit at stake, advance tax, MSME-1, and GSTR-9 / DIR-3 marked '
         'date-unconfirmed = a warning only); the accuracy SWEEP (one GSTIN under several names, one name under several GSTINs, round cash, one narration matched to several parties, a '
         'changed bank account) each with a fix button; the GSTR-9 comparison with the portal\'s getautocal / get8adetails (reads only). /api/bahi/close/*; console Month-end tab; 6 '
         'tests. NOT BUILT: sending the line to WhatsApp / voice, HSN-vs-rate, the cash-payment limit, Rule 37A. NOT VERIFIED: the GSTR-9 reads and their layout. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
