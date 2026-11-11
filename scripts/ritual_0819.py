#!/usr/bin/env python3
"""v0.819.0 WHITEBOOKS PASTE CHECK version ritual (built as 0.814). 0.818.0/+817 -> 0.819.0/+818 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.819.0", "+818", "0.818.0", "+817"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.818\.0", NEW, t)
    t = re.sub(r"\+817\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.818\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.819.0 WHITEBOOKS PASTE CHECK (built as 0.814; their HOOLA CINEMA took 0.814.0, 0.815-0.818 followed - REBASE PROTOCOL, all kept) - her first live wb_check (sandbox, every key set) was refused on GST, e-Invoice and e-Way '
         'Bill alike (WB_ERR_9001 = keys not accepted or the account not active); the requests match the specs, so two causes are left: a '
         'bad paste or an account WhiteBooks has not activated (her Hub dashboard shows every product "not subscribed"). Now every WhiteBooks '
         'value is cleaned before use (stray spaces / quotes / Windows line ends: wb.clean, wb.email), wb_check first prints how each pasted '
         'value LOOKS without the value (hidden dots copied from the Hub, a space inside, not an email, not a GSTIN, the GST key pasted into '
         'the e-invoice line; ids by their leading letters + length, secrets by length only) and, when every paste looks right and WhiteBooks '
         'still refuses, says to ask WhiteBooks to activate sandbox access; the e-way bill refusal that carries no code is named WB_ERR_9001; '
         '2 tests. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
