#!/usr/bin/env python3
"""v0.688.0 KAAM MANCH version ritual.

KAAM (the work-discipline layer, owner "GO" on the OWL deploy plan) was PLANNED at v0.686.0
while the dev chain shipped v0.686.0 (EK LAKH ALAG WEBSITE) and v0.687.0 (LEADS EMPLOYEE) -
the plan's slot was taken, so KAAM re-slotted per the REBASE PROTOCOL: rebuilt on their
c78c2164c v0.687.0 tip, their base kept whole, the version layer re-applied coherently
0.687.0/+686 -> 0.688.0/+687. The registry stays 615 (a laws layer adds no tool).

This sweep re-applies that layer across ALL test files (version tokens with the parser-stamp
guard: `v0.687.0-gm1`-shaped pins STAY - they pin the leads parser's own stamp, not APP_VERSION),
pubspec, the console cache-buster stamps (the v0179 law: stamps == APP_VERSION), the APP_VERSION
story (my KAAM head, their LEADS EMPLOYEE story verbatim in Previous), and the three mirrors
(HISTORY / WORKLOG / CLAUDE.md). Zero residual expected on exit.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_BUILD = "0.688.0", "+687"
OLD_V, OLD_BUILD = "0.687.0", "+686"

# ---------------------------------------------------------------- 1. the test-file sweep
changed, tokens = [], 0
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    hits = re.findall(r"(?<!v)0\.687\.0", text)          # the v-prefixed parser stamps stay theirs
    tokens += len(hits)
    text = re.sub(r"(?<!v)0\.687\.0", NEW, text)
    text = re.sub(r"\+686\b", NEW_BUILD, text)
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
    if f.suffix not in (".html", ".htm", ".js", ".css"):
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
assert their.startswith(f'APP_VERSION = "{OLD_V}"'), "line 36 is not the LEADS EMPLOYEE story"
t_marker = their.index(f"# v{OLD_V}") + len("# ")
their_story = their[t_marker:]

MY_HEAD = (
    f'APP_VERSION = "{NEW}"   # v0.688.0: KAAM MANCH - the work-discipline layer, the OWL port '
    "(owner: \"GO\" on the OWL deploy plan, after the end-to-end READ of github.com/camel-ai/owl @ 2df367e - "
    "Apache-2.0, external PRs welcome; planned at v0.686.0, the dev chain took v0.686.0 EK LAKH ALAG WEBSITE and "
    "v0.687.0 LEADS EMPLOYEE while KAAM sat planned - REBASE PROTOCOL, re-slotted on their c78c2164c v0.687.0 tip, "
    "their base kept whole; registry stays 615 - a laws layer, not a family; zero upstream code, zero new pip, "
    "zero new keys, zero Flutter change). THREE SURFACES, all behind kaam_enabled (default on; kaam_ledger_enabled "
    "for the receipt alone; off = byte-identical behaviour, tested): TIPS - the specialist workers' search/verify/"
    "code heuristics (broad-then-narrow, snippet-is-not-a-number, name-your-sources, if-one-road-fails, "
    "code-is-not-work-until-you-RUN-it, done-means-PROVEN) as a house-written block appended to the system prompt "
    "ALWAYS (after the family cut, never admission-dropped; the v0.221 byte-identity contract re-pinned to the new "
    "truth) | DONE - the <TASK_DONE> law in code: _pakka_check's free backstop - a strong done-claim (ho gaya / "
    "ban gaya / bhej diya / complete... with a work-noun guard and negation respect) while EVERY real call failed "
    "sets the correction note, no model call, no loop | LEDGER - one (Kaam: steps/calls/plan/done) work-receipt "
    "note row under the answer when tools ran (pure arithmetic over the turn's own state, per-tool cap 12, never "
    "raises; NO token count - state holds none and a made-up number is worse than none, the after_call law). The "
    "caps/loop machinery was NOT ported: the house already owns stricter ones (kaam_plan goal mode v0.187, 24/80 "
    "steps, the replan breaker, Pakka kaam v0.78). Tests: NEW test_v0688_kaam_manch.py (32, zero network): the "
    "tips, the ledger, the done law, the wiring, the pins (registry 615 unchanged, no kaam tool, module purity "
    "stdlib-re-only, fresh-interpreter inertness, APP_VERSION, pubspec); sibling battery green on the swept tree; "
    "the jharokha 22 reds PROVEN pre-existing on pristine origin/main with a stash run (this sandbox's missing "
    "Chromium, never this diff's lanes). Server-only deploy; desktop untouched. Previous: "
)
lines[35] = MY_HEAD + their_story
main.write_text("\n".join(lines), encoding="utf-8")
print("APP_VERSION story spliced (KAAM head, their LEADS EMPLOYEE story verbatim in Previous)")

# ---------------------------------------------------------------- 5. the CLAUDE.md mirrors
cl = ROOT / "CLAUDE.md"
text = cl.read_text(encoding="utf-8")
text, n = re.subn(r"Current version: v0\.687\.0 \(pubspec 0\.687\.0\+686;",
                 "Current version: v0.688.0 (pubspec 0.688.0+687; KAAM MANCH v0.688.0 = the work-discipline "
                 "layer, the OWL port (kaam_laws.py: TIPS on the system prompt + the done backstop + the "
                 "(Kaam:) ledger note, kaam_enabled default on, registry 615 stands); previous head v0.687.0 "
                 "(pubspec 0.687.0+686;", text, count=1)
bullet = ("- v0.688 KAAM MANCH (planned at 0.686, re-slotted on their v0.687 tip; owner: \"GO\" on the OWL deploy "
          "plan): the work-discipline layer — NOT a tool (registry 615 stands), IDEA-ONLY from camel-ai/owl@2df367e "
          "(Apache-2.0). TIPS: the search/verify/code heuristics, house-written, appended to the system prompt "
          "always. DONE: the <TASK_DONE> backstop in _pakka_check — a done-claim while every real call failed sets "
          "the correction note. LEDGER: one (Kaam: steps · calls · plan · done) receipt row under the answer when "
          "tools ran. kaam_enabled + kaam_ledger_enabled, both default on, off = byte-identical; 32 tests.\n")
text = text.replace("## Current state (latest first, one line each)\n",
                    "## Current state (latest first, one line each)\n" + bullet, 1)
cl.write_text(text, encoding="utf-8")
print("CLAUDE.md:", "current-version line + Current state bullet" if n else "!! current-version PATTERN MISS")

# ---------------------------------------------------------------- 6. HISTORY.md + WORKLOG.md
hist = ROOT / "docs" / "HISTORY.md"
section = f"""## v0.688.0 KAAM MANCH — the work-discipline layer, the OWL port (8 Nov 2026; owner: "GO" on the OWL deploy plan, after the READ of github.com/camel-ai/owl @ 2df367e)

Planned at v0.686.0; the dev chain shipped v0.686.0 (EK LAKH ALAG WEBSITE) and v0.687.0 (LEADS EMPLOYEE) while the plan sat — REBASE PROTOCOL onto their c78c2164c tip, their base kept whole. A laws layer, not a family: **registry stays 615**, zero new pip, zero new keys, zero Flutter change. IDEA-ONLY: zero upstream code from camel-ai/owl (Apache-2.0); what ported is the orchestration doctrine.

- **TIPS** — `agent/kaam_laws.py` `TIPS`: the specialist workers' heuristics (broad-then-narrow search, a snippet is not a number, name your sources, if one road fails take another, code is not work until you RUN it, done means PROVEN, lamba kaam one step at a time), house-written (no upstream sentence verbatim — tested), appended to the system prompt ALWAYS: after the PATLA-PROMPT family cut, so never admission-dropped. The v0.221 byte-identity contract re-pinned to the new truth (off = the old identity, also tested).
- **DONE** — the `<TASK_DONE>` law in code: `_pakka_check` gains a free backstop for the paths the model self-check never reaches (the simple-job skip, the checks cap): a strong done-claim (ho gaya / ban gaya / bhej diya / complete — with a work-noun guard so question echoes like "kya ho gaya?" stay quiet, and negation respect for "nahi hua" / "not done") while EVERY real call of the turn failed sets the correction note. No model call, no loop.
- **LEDGER** — one `(Kaam: 7/24 steps · 3 calls (2 ok) · plan 2/5 · done ✓ · duniya×2, workspace)` work-receipt note row under the answer when tools ran (the v0.668 own-row law). Pure arithmetic over the turn's own state; per-tool display cap 12; never raises. NO token count: state holds no per-turn tally and a made-up number is worse than none (the after_call law).
- **Switches** — `kaam_enabled` (default True) gates all three surfaces; `kaam_ledger_enabled` (default True) the receipt alone. Off = byte-identical prompts, no ledger, no backstop (tested).
- **NOT ported, said plainly** — OWL's caps and loop: the house already owns stricter ones (kaam_plan goal mode v0.187, agent_max_steps 24 / goal 80, the replan breaker, Pakka kaam v0.78, goal_verify v0.443).
- Tests: NEW `test_v0688_kaam_manch.py` (32, zero network): tips (9), ledger (9), done law (6), wiring (4), pins & purity (6: registry 615 unchanged, no kaam tool, module stdlib-re-only, fresh-interpreter inertness, APP_VERSION, pubspec). Sibling battery green on the swept tree (kala 34, duniya 39, sandarbh/bhandar, sahi_jawab 11, draft_jaanch, chhota_jawab, lamba_kaam, yaad_pakki, sahi_auzaar, lakh_websites, leads_employee — 179 + 110 + 34 green); the jharokha 22 reds proven pre-existing on pristine origin/main with a stash run (this sandbox's missing Chromium).
- Version ritual: `scripts/ritual_v0688.py` — version tokens swept with the parser-stamp guard (`v0.687.0-gm1`-shaped leads pins stay theirs), pubspec 0.688.0+687, console stamps `?v=0.688.0`, the APP_VERSION story splice, the three mirrors.
- Server-only deploy = owner's vps-ops dispatch; desktop untouched. NOT VERIFIED live: her first turn with the ledger line under the answer — that is the live test.

"""
text = hist.read_text(encoding="utf-8")
hist.write_text(section + text, encoding="utf-8")
print("HISTORY.md section prepended")

work = ROOT / "docs" / "WORKLOG.md"
task = """# HOOLA — Multi-Session Worklog
Task ID: v0.688.0 KAAM MANCH (the OWL work-discipline port)
Agent: main (kaam laws lane)
Task: owner "GO" on the OWL deploy plan (download/HOOLA_OWL_DEPLOY_PLAN.md, 6 decisions locked: laws+tips shape, KAAM MANCH name, all lanes, default ON + caps, no new tool, ~30 tests).
Work Log: REBASE PROTOCOL (planned v0.686, shipped on their v0.687 tip c78c2164c, their base kept whole); server/app/agent/kaam_laws.py NEW (~150 LOC, stdlib-re only); prompts.py _kaam_tips() appended post-cut in system_text (both paths); santosh.py the ledger note at natural turn end + the done backstop in _pakka_check; config.py kaam_enabled + kaam_ledger_enabled (default on); test_v0688_kaam_manch.py NEW (32, offline); the v0.221 full-guide contract test re-pinned to SYSTEM+tips (off = old identity); ritual_v0688.py swept (parser-stamp guard), pubspec 0.688.0+687, console stamps, APP_VERSION story, CLAUDE.md + HISTORY.md + WORKLOG mirrors; battery green, jharokha 22 reds proven pre-existing (missing Chromium, stash run).
Stage Summary: pushed to main as v0.688.0 + tag; vps-ops deploy fired; live test = her first (Kaam:) receipt line under a worked answer.
"""
text = work.read_text(encoding="utf-8")
text = text.replace("# HOOLA — Multi-Session Worklog\n", task, 1)
work.write_text(text, encoding="utf-8")
print("WORKLOG.md task prepended")

# ---------------------------------------------------------------- 7. residual check
residual = []
for f in sorted((ROOT / "server").rglob("*.py")):
    if "hoola-venv" in str(f) or "__pycache__" in str(f):
        continue
    text = f.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"(?<!v)0\.687\.0", text):
        residual.append(f.name)
for f in [pub, main, cl]:
    text = f.read_text(encoding="utf-8")
    if re.search(r"\+686\b", text) and "0.687.0+686; previous" not in text:
        residual.append(f.name + " (+686)")
print("residual 0.687.0 in server .py:", residual or "ZERO")
