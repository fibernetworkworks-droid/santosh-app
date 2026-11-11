#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.807.0", "+806", "0.806.0", "+805"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.806\.0", NEW, t)
    t = re.sub(r"\+805\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.806\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.807.0 BAHI A0 - the GST & Accounts employee, foundation (built as 0.806; their HOOLA CODE PHASE 6 took 0.806.0 - '
         'REBASE PROTOCOL, both kept; owner: "FULL GST AND ACCOUNT EMPLOYEE --- I HAVE WHITEBOOK APIS" -> "GO A0"; docs/ACCOUNTS_EMPLOYEE_PLAN.md): '
         'NEW server/app/bahi/ - ONE register of every document (acc_docs, keyed by source + source_ref) read from the engines Hoola already '
         'has (GST Sahayak, wholesale Thok, office bills, her app + website invoices), the same bill entered in two engines flagged on both, a '
         'change to a LOCKED month held as an amendment (acc_periods), a document its source dropped marked never deleted, an append-only '
         'trail (acc_events); rules as DATA (bahi/rules/*.json: GST slabs before / after 22 Sep 2025, due dates, limits, the Income-tax Rules '
         '2026 form map) each with source + basis + checked_on + review_by, unverified rows shown never computed with; the WhiteBooks GSP '
         'client (bahi/wb.py) built to their OpenAPI specs - client_id / client_secret headers + email query, success only on status_cd 1, '
         'WB_ERR codes in plain English, no password / OTP in a log line, per-tenant daily cap + per-minute guard, every call metered '
         '(acc_wb_calls) - and the sandbox contract check `python -m app.bahi.wbcheck` / vps-ops wb_check that records each reply SHAPE '
         '(never a value; production = ping only); the Hub row Accounts Assistant goes live as "GST & Accounts" (gates no tool) with its '
         'console desk (bahi.js: Overview / Register / Rules / Connection / Plan); /api/bahi/*; no chat tool yet (A1); 14 tests incl. a '
         'browser walk. NOT VERIFIED against the real WhiteBooks sandbox (keys not on the server yet). Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
