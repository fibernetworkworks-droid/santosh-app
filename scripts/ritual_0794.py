#!/usr/bin/env python3
"""v0.794.0 PROMPT NAAP version ritual (built as 0.785 on the v0.784 tip; their HOOLA AI APPS ... HOOLA CODE SAFETY + RESUME took
0.785.0-0.793.0 while it sat built - REBASE PROTOCOL, all kept). 0.793.0/+792 -> 0.794.0/+793 across the test pins, pubspec, the
console stamps and the APP_VERSION story (theirs kept verbatim as Previous). No console file added, so the stamp COUNT stays."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.794.0", "+793", "0.793.0", "+792"
src, dst = ROOT / "server/tests/test_v0785_prompt_card.py", ROOT / "server/tests/test_v0794_prompt_card.py"
if src.exists():
    t = src.read_text().replace('"""v0.785 PROMPT NAAP', '"""v0.794 PROMPT NAAP (built as 0.785)')
    dst.write_text(t.replace('"0.785.0"', f'"{OLD}"').replace("0.785.0+784", f"{OLD}{OLD_B}"))
    src.unlink()
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.793\.0", NEW, t)
    t = re.sub(r"\+792\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.793\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.794.0 PROMPT NAAP (built as 0.785; their 0.785.0-0.793.0 took the numbers - REBASE PROTOCOL, all kept; P0 of '
         'docs/HOOLA_PROMPTING_PLAN.md, the owner pasted the P0 step = GO): the PROMPT card quality/promptcard.py + prompt_asks.py - 60 '
         'rough asks (20 website / 20 picture / 20 script, half Hinglish half English), each as her raw line AND a brief filled in by '
         'hand, run through the real engine twice (website = the architect plan, one call, nothing built or saved; script = the Create '
         'script writer; picture = the Create picture engine + one reader call answering yes / no per statement) and scored the same '
         'way in code against what she wanted (must items, facts kept unchanged, invented prices / phones / percents, the engine own '
         'check; her brief echoed back earns nothing); section verdict by rule BUILD / RETHINK / DROP, her pick outranks the checks '
         '(prompt verdict <id> raw|brief|same); the free card checks the set, calibrates the scorer on 14 planted cases and asks the '
         'engines own guards; a live card needs --budget-inr and stops itself; GET /api/quality/prompt; vps-ops prompt_card_check / '
         'prompt_card_try; no user-facing change; NOT VERIFIED: no live card has run, so no numbers yet. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
