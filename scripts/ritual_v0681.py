#!/usr/bin/env python3
"""v0.681.0 KALA MANCH version ritual.

KALA (the T5 knowledge-skill catalog family, owner "GO" on the google/skills deploy plan) was
PLANNED at 0.669.0 while the dev chain shipped 0.669.0 (HOOLA AURA) through 0.680.0 (HOOLA ADOPT)
- the plan's slot was taken, so KALA re-slotted per the REBASE PROTOCOL: rebuilt on their
00aa1dac9 v0.680.0 tip, their base kept whole, the version layer re-applied coherently
0.680.0/+679 -> 0.681.0/+680 and the registry layer 608 -> 609 (v0.680 added no tools).

This sweep re-applies that layer across ALL test files (version tokens, the pubspec-string pins,
the registry pins + their arithmetic messages, the aep1 pin-on-the-pin - all healed by the same
replacement), pubspec, the console cache-buster stamps (the test_v0179 law: stamps == APP_VERSION),
the APP_VERSION story (my KALA head, their ADOPT chain verbatim in Previous), and the three
mirrors (HISTORY / WORKLOG / CLAUDE.md). Zero residual expected on exit.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_BUILD = "0.681.0", "+680"
OLD_V, OLD_BUILD = "0.680.0", "+679"

KALA_LINK = ('"608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, '
             "owner 'GO' on the google/skills deploy plan). \" \"607 + 1 duniya (")

# ---------------------------------------------------------------- 1. the test-file sweep
changed, tokens = [], 0
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    tokens += len(re.findall(rf"\b{re.escape(OLD_V)}\b", text))
    text = text.replace(OLD_V, NEW)
    text = re.sub(r"\+679\b", NEW_BUILD, text)
    text = re.sub(r"== 608\b", "== 609", text)
    text = text.replace('"607 + 1 duniya (', KALA_LINK, 1) if '"607 + 1 duniya (' in text else text
    # the one comment-shaped pin (kaan_w5: "# W5 adds doors, not tools (608 = 607 + 1 duniya ...)")
    text = text.replace("(608 = 607 + 1 duniya", "(609 = 608 + 1 kala + 607 + 1 duniya")
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)
print(f"tests swept: {len(changed)} files ({tokens} version tokens)")

# ---------------------------------------------------------------- 2. pubspec
pub = ROOT / "pubspec.yaml"
text = pub.read_text(encoding="utf-8")
text, n = re.subn(r"version: 0\.\d+\.\d+\+\d+", f"version: {NEW}{NEW_BUILD}", text, count=1)
pub.write_text(text, encoding="utf-8")
print("pubspec ->", f"{NEW}{NEW_BUILD}" if n else "!! PATTERN MISS")

# ---------------------------------------------------------------- 3. the console cache-busters (the v0179 law)
stamped = 0
for f in sorted((ROOT / "server" / "app" / "static" / "console").glob("*")):
    if f.suffix not in (".html", ".htm"):
        continue
    text = f.read_text(encoding="utf-8")
    new_text, n = re.subn(rf"\?v={re.escape(OLD_V)}", f"?v={NEW}", text)
    if n:
        f.write_text(new_text, encoding="utf-8")
        stamped += n
print(f"console cache-busters: {stamped} stamps -> {NEW}")

# ---------------------------------------------------------------- 4. the APP_VERSION story splice
main = ROOT / "server" / "app" / "main.py"
lines = main.read_text(encoding="utf-8").split("\n")
their = lines[35]
assert their.startswith(f'APP_VERSION = "{OLD_V}"'), "line 36 is not the ADOPT story"
t_marker = their.index(f"# v{OLD_V}") + len("# ")
their_story = their[t_marker:]

REBASE_NOTE = ("planned at 0.669.0; the dev chain took 0.669.0 (HOOLA AURA) through 0.680.0 (HOOLA ADOPT) "
               "while KALA sat planned - REBASE PROTOCOL, re-slotted on their 00aa1dac9 v0.680.0 tip, "
               "their base kept whole, the version layer re-applied coherently 0.680.0/+679 -> 0.681.0/+680, "
               "ritual_v0681.py")

MY_HEAD = (
    f'APP_VERSION = "{NEW}"   # v0.681.0: KALA MANCH - the T5 knowledge-skill catalog family ({REBASE_NOTE}) '
    '(owner: "GO" on the google/skills deploy plan, after the READ of github.com/google/skills - Apache-2.0, '
    'fork-and-remix sanctioned): the T5 tier beside the four brothers - the knowledge tier. ONE tool `kala` '
    '(registry 608 -> 609, v0.680 added no tools), IDEA-ONLY: zero upstream code, zero new pip, zero new keys. '
    'FIVE ACTIONS, every answer ONE envelope {schema_version, ok, tool, action, ..., meta{elapsed_ms, backend}, '
    'error{code, message, hint}}: catalog (index.json fetched BYTE-EXACT behind a 5-min in-process TTL cache '
    '(kala_catalog_ttl_seconds=300), narrowed by a case-insensitive regex over name+description, 25-cap with '
    'the honest total_matches, the no-query alphabetical-bias note - the upstream README\'s own warning; a '
    'broken regex degrades to a literal find, never a crash) | read (one SKILL.md by its EXACT catalog name, '
    'fetched fresh on every read, 12k cap with the honest truncation note, an unknown name NOT_FOUND naming '
    'the catalog - never inferred from the name, the routing rule\'s law) | references (a skill\'s '
    'references/<file>.md deep-dive derived from its entrypoint and re-allowlisted, 8k cap, a 404 = honest '
    'NOT_FOUND, a ../ traversal refused before ANY fetch) | list (the predictable family prefixes - gke-, '
    'agent-platform-, google-cloud-solution-, google-cloud-waf-, secops- ... - with the family table, an '
    'unknown prefix empty + the table, never invented) | status (zero network: upstream, cache state '
    'including the last fetch error, caps, laws). THE LAWS: GET only, forever; EVERY url crosses TWO walls - '
    'the house scrape-lane SSRF guard AND this lane\'s own one-host allowlist (https://raw.githubusercontent.com '
    'only, one path shape: index.json | skills/<domain>/<skill>/SKILL.md | .../references/<file>.md - refused '
    'by name NOT_ALLOWED; a poisoned catalog entry pointing elsewhere is refused too, cached text is never '
    'trusted); the catalog is cached, the documents are NEVER cached (fetching is the normal path, the '
    'upstream\'s own law); NO SKILL.MD SCRIPT EVER EXECUTES server-side - documents are read, never run; text '
    'passes operator.browser mask_ids like every scraping surface; ONE network seam (_http_get) every public '
    'byte rides - tests monkeypatch exactly that and the suite stays offline; the attribution UA '
    'hoola-kala/0.681 (+google-skills catalog; Apache-2.0 remixed; idea-only); kill switch kala_enabled (off '
    '= every action NEED_SETUP, honest), default on. prompts.py Kala bullet beside the four brothers. Tests: '
    'NEW test_v0681_kala_manch.py (34, zero network, the fake seam pops scripted answers, an autouse fixture '
    'keeps the cache cold): envelope shape, status zero-network + cold-cache honesty, kill switch, catalog '
    '(regex narrow, case-insensitive, cap+note, no-query bias note, broken regex literal, the cache really '
    'caching - second call no seam, TTL expiry refetches, bad JSON = UPSTREAM and told in status), read '
    '(byte-exact body + description, unknown name NOT_FOUND never-guess, honest truncation, TOO_BIG, the PAN '
    'mask, empty name), references (entrypoint-derived url, 404 = NOT_FOUND, traversal refused pre-network, '
    'non-SKILL.md entrypoint refused), list (known prefix, unknown prefix + families, empty prefix), the '
    'allowlist (six refusals by name + the house paths accepted + a poisoned catalog entry refused), the SSRF '
    'guard wired (loopback + file:// through the real house guard, zero DNS), timeout mapping, unknown action, '
    'the attribution tag, purity (no top-level httpx), registry 609 pin, enum pin, APP_VERSION pin. '
    'RE-SHIP VERIFICATION in the sandbox: kala 34 + duniya 39 + sandarbh/bhandar 78 + jharokha 27 = 178 in one '
    'battery on the swept tree. Version ritual: ritual_v0681.py swept 0.680.0 -> 0.681.0 (+680) across the '
    'test files (version tokens + the pubspec-string pins), pubspec, the console cache-buster stamps (the '
    'v0179 law: stamps == APP_VERSION), the registry pins 608 -> 609 with the arithmetic note (the kaan_w5 '
    'comment-shaped pin healed), the aep1 pin-on-the-pin riding the same replacement, ZERO residual; '
    'CLAUDE.md current-version line + the Current state bullet, docs/HISTORY.md section, docs/WORKLOG.md '
    'task. Server-only deploy = owner\'s vps-ops dispatch; desktop untouched - old APKs keep working; no new '
    'pip; one new kill switch, default on. NOT VERIFIED live: the first real catalog fetch + SKILL.md read on '
    'the VPS - the public upstream is coded to its documented shape and the suite is fully scripted; her first '
    '"google ka GKE skill laao" is the live test. Previous: '
)
lines[35] = MY_HEAD + their_story
main.write_text("\n".join(lines), encoding="utf-8")
print("APP_VERSION story: KALA 0.681.0 head + their HOOLA ADOPT chain verbatim")

# ---------------------------------------------------------------- 5. the mirrors
h = ROOT / "docs" / "HISTORY.md"
t = h.read_text(encoding="utf-8")
sec = ("## v0.681.0 KALA MANCH — the T5 knowledge-skill catalog family (8 Nov 2026, planned at 0.669.0; "
       "the dev chain took 0.669.0-0.680.0 while KALA sat planned - REBASE PROTOCOL, re-slotted on their "
       "v0.680.0 tip, all kept)\n\n"
       "The knowledge tier beside the four capability brothers: Google's public skill catalog "
       "(github.com/google/skills, Apache-2.0, fork-and-remix sanctioned) read on demand — IDEA-ONLY.\n\n"
       "- **ONE tool `kala`** (registry 608 -> 609), FIVE ACTIONS, one envelope: **catalog** (index.json "
       "byte-exact behind a 5-min in-process TTL cache `kala_catalog_ttl_seconds=300`, case-insensitive regex "
       "narrowing over name+description, 25-cap with honest totals, the alphabetical-bias note; a broken regex "
       "degrades to a literal find) · **read** (one SKILL.md by its EXACT catalog name, fetched fresh every "
       "read, 12k cap + honest truncation, unknown name = NOT_FOUND — never inferred from the name) · "
       "**references** (the skill's references/<file>.md deep-dive, derived from the entrypoint and "
       "re-allowlisted, 8k cap, 404 = NOT_FOUND, ../ traversal refused before any fetch) · **list** (the "
       "predictable family prefixes — gke-, agent-platform-, google-cloud-solution-, google-cloud-waf- ... — "
       "with the family table, unknown prefixes answered with the table, never invented answers) · **status** "
       "(zero network: upstream, cache state incl. the last error, caps, laws).\n"
       "- **THE LAWS** — GET only forever; every url crosses TWO walls (the house scrape-lane SSRF guard AND "
       "the lane's one-host allowlist: https://raw.githubusercontent.com only, one path shape — index.json | "
       "skills/<domain>/<skill>/SKILL.md | .../references/<file>.md — refused by name NOT_ALLOWED; a poisoned "
       "catalog entry is refused too); the catalog is cached, the documents are never cached (fetching is the "
       "normal path); **NO SKILL.MD SCRIPT EVER EXECUTES** server-side; text passes the id-mask; ONE network "
       "seam (`_http_get`) the tests monkeypatch — the suite stays offline; attribution UA "
       "`hoola-kala/0.681 (+google-skills catalog; Apache-2.0 remixed; idea-only)`; kill switch "
       "`kala_enabled` default on.\n"
       "- **Idea provenance (not code)** — the finding-google-skills meta-skill (byte-exact catalog fetch, "
       "truncation-bias honesty), the routing rule (predictable families, never infer contents from a name), "
       "the SKILL.md anatomy (progressive disclosure), the attribution tag law (append, never overwrite).\n"
       "- Tests: **test_v0681_kala_manch.py (34, zero network, autouse cold cache)** — the battery on the "
       "swept tree: kala 34 + duniya 39 + sandarbh/bhandar 78 + jharokha 27 = 178.\n\n")
h.write_text(sec + t, encoding="utf-8")
print("HISTORY: KALA section prepended")

w = ROOT / "docs" / "WORKLOG.md"
t = w.read_text(encoding="utf-8")
lines_w = t.split("\n")
idx = next(i for i, l in enumerate(lines_w) if l.startswith("Task ID:"))
lines_w.insert(idx, "Task ID: v0.681.0 KALA MANCH - the T5 knowledge-skill catalog family (planned at 0.669.0, "
                    "the dev chain took 0.669-0.680 while KALA sat planned - REBASE PROTOCOL, re-slotted on "
                    "their v0.680.0 tip, all kept; owner: \"GO\" on the google/skills deploy plan)\n")
w.write_text("\n".join(lines_w), encoding="utf-8")
print("WORKLOG: task inserted")

c = ROOT / "CLAUDE.md"
t = c.read_text(encoding="utf-8")
old_head = "- Current version: v0.680.0 (pubspec 0.680.0+679; "
new_head = ("- Current version: v0.681.0 (pubspec 0.681.0+680; KALA MANCH v0.681.0 = the T5 knowledge-skill "
            "catalog family: ONE tool `kala` (catalog | read | references | list | status) over "
            "github.com/google/skills (Apache-2.0) - index.json byte-exact behind a 5-min TTL cache, SKILL.md "
            "documents fetched fresh and NEVER executed, one-host allowlist over the house SSRF guard, no "
            "login no key, registry 608 -> 609, owner 'GO' on the google/skills deploy plan; previous head: "
            "v0.680.0 (pubspec 0.680.0+679; ")
assert old_head in t, "the Current version line head moved"
t = t.replace(old_head, new_head, 1)
anchor = "## Current state (latest first, one line each)\n"
i = t.index(anchor) + len(anchor)
bullet = ("- v0.681 KALA MANCH (planned at 0.669.0, re-slotted on their v0.680.0 tip; owner: \"GO\" on the "
          "google/skills deploy plan): the T5 knowledge tier — ONE tool `kala` over Google's public skill "
          "catalog (github.com/google/skills, Apache-2.0): action=catalog fetches index.json byte-exact "
          "(5-min TTL cache) and narrows it by a query; action=read fetches one SKILL.md by its EXACT name "
          "(never inferred); action=references fetches a skill's references/<file>.md; action=list walks the "
          "predictable family prefixes (gke-, agent-platform-...) with the family table; action=status shows "
          "the cache, caps and laws. GET only; the house SSRF guard AND a one-host allowlist ("
          "raw.githubusercontent.com) on every url; documents fetched fresh, never cached, and NEVER executed "
          "— a skill's scripts/ are text; the id-mask on everything; one network seam; kala_enabled default "
          "on; registry 608 -> 609; 34 tests; IDEA-ONLY (zero upstream code).\n")
t = t[:i] + bullet + t[i:]
c.write_text(t, encoding="utf-8")
print("CLAUDE.md: current-version line + Current state bullet")

# ---------------------------------------------------------------- 6. residual check
residual_v, residual_r = [], []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    if re.search(rf"\b{re.escape(OLD_V)}\b", text):
        residual_v.append(f.name)
    if re.search(r"== 608\b", text):
        residual_r.append(f.name)
print("residual 0.680.0 in tests:", residual_v or "ZERO")
print("residual == 608 in tests:", residual_r or "ZERO")
pub_now = pub.read_text(encoding="utf-8")
assert f"version: {NEW}{NEW_BUILD}" in pub_now
main_now = main.read_text(encoding="utf-8")
assert f'APP_VERSION = "{NEW}"' in main_now
print("ritual_v0681: DONE")
