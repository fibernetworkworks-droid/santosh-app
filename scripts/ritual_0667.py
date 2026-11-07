#!/usr/bin/env python3
"""v0.667.0 DUNIYA MANCH version ritual - the T4 keyless-public-web family.

Sweeps the version layer coherently across the tree: 0.666.0/+672 -> 0.667.0/+673,
registry pins 607 -> 608 (one duniya), the APP_VERSION story grows the DUNIYA MANCH
paragraph with the v0.666.0 KAAN W5 story spliced verbatim into the Previous chain,
and the mirrors (CLAUDE.md / docs/WORKLOG.md Task 40 / docs/HISTORY.md) land.
ZERO residual is checked by the sweep's own report; the suites re-run after.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # .../hoola-project
NEW, NEW_BUILD = "0.667.0", "+673"
OLD_V, OLD_BUILD = "0.666.0", "+672"

DUNIYA_PIN = ('"607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, '
              'owner \'T4\'). " "606 + 1 jharokha')

# ---------------------------------------------------------------- 1. the test-file sweep
changed, pins = [], 0
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    text = text.replace(f"== 607, \"606 + 1 jharokha",
                        f"== 608, {DUNIYA_PIN}")
    text = text.replace(f"== 607, (\"606 + 1 jharokha",
                        f"== 608, ({DUNIYA_PIN}")
    n = len(re.findall(rf"\b{re.escape(OLD_V)}\b", text))
    pins += n
    text = text.replace(OLD_V, NEW).replace(OLD_BUILD, NEW_BUILD)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)
print(f"tests swept: {len(changed)} files (version tokens before sweep: {pins})")

# ---------------------------------------------------------------- 2. pubspec
pub = ROOT / "pubspec.yaml"
text = pub.read_text(encoding="utf-8")
text, n = re.subn(r"version: 0\.\d+\.\d+\+\d+", f"version: {NEW}{NEW_BUILD}", text, count=1)
pub.write_text(text, encoding="utf-8")
print("pubspec ->", f"{NEW}{NEW_BUILD}" if n else "!! PATTERN MISS")

# ---------------------------------------------------------------- 3. the APP_VERSION story
main = ROOT / "server" / "app" / "main.py"
lines = main.read_text(encoding="utf-8").split("\n")
line36 = lines[35]
assert line36.startswith(f'APP_VERSION = "{OLD_V}"'), "line 36 is not the v0.666.0 story head"

MY_STORY = (
    "v0.667.0 DUNIYA MANCH - the T4 keyless-public-web family (owner: 'T4' - the fourth and last tier "
    "of download/HOOLA_MCP_FEED.json; the ladder was three for three after JHAROKHA v0.665 - T1 "
    "SANDARBH, T2 BHANDAR, T3 JHAROKHA - and this closes it): the no-login / no-key public-web rows "
    "land backend-only as ONE GET-only tool `duniya` (registry 607 -> 608), IDEA-ONLY from the "
    "modelcontextprotocol/servers fetch reference ('Web content fetching capabilities for LLMs') + the "
    "no-key public-API rows the feed's T4 tier named (Wikipedia / Open-Meteo / Hacker News / Frankfurter "
    "/ Free Dictionary / arXiv), zero upstream code, zero new pip (httpx is the house's), zero new keys. "
    "EIGHT ACTIONS, every answer ONE envelope {schema_version, ok, tool, action, ..., meta{elapsed_ms, "
    "backend}, error{code, message, hint}}: fetch (one public http(s) url -> readable text, scripts and "
    "styles stripped by a stdlib parser, the final url after redirects told honestly, an honest "
    "truncation note at the 12k cap, TOO_BIG past the 500k download cap, non-text content-types refused "
    "naming jharokha) | wikipedia (search + the top hit's summary in any language edition; the courtesy "
    "summary is never fatal) | weather (Open-Meteo geocode + forecast, WMO codes named in words, days "
    "clamped 1-7) | hn (Algolia story search with the story_* fallbacks) | currency (Frankfurter latest "
    "or by date; the amount folded into the answer told both ways - rate AND result) | dictionary "
    "(meanings, definitions capped 2, the 404 = NOT_FOUND honesty) | arxiv (the Atom export parsed with "
    "the stdlib, no new pip) | status (zero network: the backends, caps and laws). THE LAWS: GET only, "
    "forever - never POST/PUT/DELETE, never an Authorization header, never a cookie; the named backends' "
    "urls are code constants and EVERY url - the free fetch one AND the constants - goes through the "
    "house's own scrape-lane SSRF guard (public hosts only; loopback / RFC1918 / link-local / metadata "
    "never fetched); ONE network seam (_http_get) every public byte rides - tests monkeypatch exactly "
    "that and the whole suite stays offline; text passes operator.browser mask_ids like every scraping "
    "surface; kill switch duniya_enabled (off = every action NEED_SETUP, honest). Config: "
    "duniya_enabled=True. prompts.py Duniya bullet beside the three brothers. Tests: NEW "
    "test_v0667_duniya_manch.py (39, zero network, the fake seam pops scripted answers): the envelope "
    "shape, status zero-network, the kill switch, fetch (strips scripts/styles, json pretty, redirect "
    "final url, honest truncation, TOO_BIG, non-text refused, the PAN mask riding the text, the guard "
    "REALLY wired between the ask and the web), the SSRF guard itself (loopback / metadata / file:// / "
    "ftp://), wikipedia (search+summary in order, no-results NOT_FOUND with no courtesy call, summary "
    "failure not fatal, input laws), weather (geocode+forecast, WMO words, the clamp, unknown place), "
    "hn (shape + fallbacks + the hn_url built), currency (rate/result both ways, the historical date in "
    "the path, input laws, missing pair), dictionary (capped definitions, 404 = NOT_FOUND), arxiv (Atom "
    "parse, empty feed, broken Atom), upstream timeout mapping, purity (no top-level httpx), registry "
    "608 pin, enum pin, APP_VERSION pin. Version ritual (scripts/ritual_0667.py): pubspec 0.667.0+673, "
    "pins ->0.667.0(+673) swept across the suites (zero residual), registry pins 607 -> 608 with the "
    "note, CLAUDE.md current-version line, docs/WORKLOG.md Task 40, docs/HISTORY.md section. "
    "Server-only deploy: old APKs keep working; no new pip; one new kill switch, default on. THE FEED'S "
    "TIER LADDER IS FOUR FOR FOUR: T1 SANDARBH (reference) v0.586/0.590, T2 BHANDAR (local core) "
    "v0.618/0.620, T3 JHAROKHA (local browser) v0.664/0.665, T4 DUNIYA (keyless public web) v0.667. "
)
rest = line36.split("# ", 1)[1]                        # their whole v0.666.0 story, verbatim
lines[35] = f'APP_VERSION = "{NEW}"   # {MY_STORY}Previous: {rest}'
main.write_text("\n".join(lines), encoding="utf-8")
print("APP_VERSION story: DUNIYA MANCH head + their v0.666.0 chain verbatim in Previous")

# ---------------------------------------------------------------- 4. CLAUDE.md
c = ROOT / "CLAUDE.md"
t = c.read_text(encoding="utf-8")
old_head = "Current version: v0.665.0"
idx = t.find(old_head)
assert idx > 0, "CLAUDE.md current-version line not found"
new_head = ("Current version: v0.667.0 (pubspec 0.667.0+673; DUNIYA MANCH v0.667.0 = the T4 "
            "keyless-public-web family: ONE GET-only tool `duniya` (fetch | wikipedia | weather | hn | "
            "currency | dictionary | arxiv | status) over the no-login / no-key public web - the "
            "mcp/servers fetch reference + the no-key public-API rows, IDEA-ONLY, SSRF-guarded, one "
            "network seam, owner 'T4'; previous head ")
t = t[:idx] + new_head + t[idx + len("Current version: "):]
list_anchor = "## Current state (latest first, one line each)\n"
t = t.replace(list_anchor,
              list_anchor + "- v0.667 DUNIYA MANCH (owner 'T4', the T4 tier - the feed ladder is four for "
              "four): the keyless public web as ONE GET-only tool `duniya` (fetch | wikipedia | weather | "
              "hn | currency | dictionary | arxiv | status); registry 608; 39 tests.\n", 1)
c.write_text(t, encoding="utf-8")
print("CLAUDE.md: current-version line + Current state row")

# ---------------------------------------------------------------- 5. docs/WORKLOG.md Task 40
w = ROOT / "docs" / "WORKLOG.md"
task = """
## Task 40 — v0.667.0 DUNIYA MANCH (owner: "T4" - the T4 tier of download/HOOLA_MCP_FEED.json)

The T4 tier of download/HOOLA_MCP_FEED.json - the no-login / no-key public-web rows - lands
backend-only for the hoola AI, the fourth and last idea-lane of the feed family (Sandarbh v0.586 =
T1 reference, Bhandar v0.620 = T2 local core, Jharokha v0.665 = T3 local browser, Duniya v0.667 =
T4 keyless public web). NOTE: the feed file itself was lost to a sandbox recycle; the T4 tier was
deployed from its recorded definition (the no-login / no-key public-web rows), the same standard
the first three tiers rode.

**The catalog (catalog-description-verified, ported IDEA-ONLY - zero upstream code, zero new pip,
zero new keys):** modelcontextprotocol/servers fetch (the official reference: "Web content fetching
capabilities for LLMs") + the no-key public-API rows (Wikipedia / Open-Meteo / Hacker News /
Frankfurter / Free Dictionary / arXiv).

**The lane:** ONE tool `duniya` (registry 607 -> 608), eight actions, every answer one envelope
{schema_version, ok, tool, action, ..., meta{elapsed_ms, backend}, error{code, message, hint}}:
fetch | wikipedia | weather | hn | currency | dictionary | arxiv | status.

**The laws:** GET only, forever (never POST/PUT/DELETE, never an auth header, never a cookie);
the named backends' urls are code constants and EVERY url rides the house scrape-lane SSRF guard;
ONE network seam (`_http_get`) every public byte rides - tests monkeypatch exactly that, the whole
suite offline; text passes mask_ids; kill switch `duniya_enabled` (off = honest NEED_SETUP).

- Wiring: agent/duniya_tools.py (new); tools.py registry 607 -> 608; config.py duniya_enabled=True;
  prompts.py Duniya bullet beside the three brothers.
- Tests: NEW server/tests/test_v0667_duniya_manch.py (39, zero network; the fake seam pops scripted
  answers): envelope shape, status zero-network, kill switch, fetch (strips scripts/styles, json
  pretty, redirect final url, honest truncation, TOO_BIG, non-text refused, PAN mask, guard REALLY
  wired), the SSRF guard itself (loopback / metadata / file:// / ftp://), wikipedia, weather, hn,
  currency, dictionary, arxiv, upstream mapping, purity (no top-level httpx), registry 608 pin,
  enum pin, APP_VERSION pin.
- Ritual: scripts/ritual_0667.py - 0.666.0/+672 -> 0.667.0/+673 across the suites (zero residual),
  registry pins 607 -> 608 with the note, pubspec, APP_VERSION story (their KAAN W5 chain verbatim
  in Previous), CLAUDE.md, WORKLOG Task 40, HISTORY section.

Stage Summary:
- v0.667.0, tests/test_v0667_duniya_manch.py green. Server-only deploy - old APKs keep working.
"""
w.write_text(w.read_text(encoding="utf-8") + task, encoding="utf-8")
print("WORKLOG Task 40 appended")

# ---------------------------------------------------------------- 6. docs/HISTORY.md (newest first)
h = ROOT / "docs" / "HISTORY.md"
section = """## v0.667.0 DUNIYA MANCH — the T4 keyless-public-web family: the world outside the walls (owner: "T4")

The fourth and last tier of download/HOOLA_MCP_FEED.json lands backend-only: ONE GET-only tool
`duniya` (registry 607 -> 608) over the parts of the web that answer anyone - no login, no API key.
Actions: fetch (the mcp/servers fetch reference idea - one public url, readable text, scripts
stripped, redirects honest, caps honest) | wikipedia | weather (Open-Meteo) | hn (Algolia) |
currency (Frankfurter) | dictionary (dictionaryapi.dev) | arxiv (Atom, stdlib-parsed) | status.
Laws: GET only forever; every url - free AND fixed-backends - through the house SSRF guard; ONE
network seam the tests monkeypatch (suite fully offline); mask_ids on the text; kill switch
duniya_enabled. Tests: test_v0667_duniya_manch.py (39, zero network). THE FEED'S TIER LADDER IS
FOUR FOR FOUR: SANDARBH v0.590 (T1 reference) + BHANDAR v0.620 (T2 local core) + JHAROKHA v0.665
(T3 local browser) + DUNIYA v0.667 (T4 keyless public web).

"""
t = h.read_text(encoding="utf-8")
h.write_text(section + t, encoding="utf-8")
print("HISTORY section prepended")

# ---------------------------------------------------------------- 7. the residual check
residual = []
for rel in ["pubspec.yaml", "server/app/main.py"]:
    body = (ROOT / rel).read_text(encoding="utf-8")
    if OLD_BUILD in body:
        residual.append(rel)
left_build = [f.name for f in (ROOT / "server" / "tests").glob("*.py") if OLD_BUILD in f.read_text(encoding="utf-8")]
print(f"residual {OLD_BUILD}: tests={left_build or 'NONE'} other={residual or 'NONE'}")
print("RITUAL DONE ->", f"{NEW}{NEW_BUILD}, registry 608")
