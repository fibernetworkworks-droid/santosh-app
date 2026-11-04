# CLAUDE SKILLS PILOT - the 8 chosen skills (plan first, 4 Nov 2026)

Owner asked: bring mcp-builder, skill-creator, webapp-testing, internal-comms, doc-coauthoring, frontend-design,
theme-factory and canvas-design into Hoola. This is the S5 pilot of `docs/CLAUDE_SKILLS_PLAN.md`. NOTHING BUILT YET.
Sizes below were read from the real files in github.com/anthropics/skills (estimates, not byte counts).

## 1. What each skill really is (measured, not guessed)
| Skill | Size | Bundled files | Assumes | Hoola fit |
|---|---|---|---|---|
| internal-comms | ~1.5k chars | examples/ x4 (3p-updates, newsletter, faq, general) | nothing | EASIEST. Pure writing guides. Needs Hinglish adaptation |
| webapp-testing | ~4.5k chars | scripts/with_server.py, examples/ x3 | Playwright (python), shell | Hoola has `server/browser_worker`; need a mapping note, script runs only after S3 |
| theme-factory | ~60 lines | themes/ (10 specs), theme-showcase.pdf | read files, show PDF | EASY. Data skill: palettes + font pairs. Feeds Create Studio / site kit |
| frontend-design | ~10k chars | none | HTML/CSS, optional screenshot | EASY content; overlaps `artifact-design` + site/kit.py, must not conflict |
| canvas-design | ~12k chars | canvas-fonts/ | code to render png/pdf, fonts | Needs fonts + a renderer; Hoola has HOOLA PRINT + Create Studio |
| doc-coauthoring | ~17k chars | none | create_file + str_replace, artifacts, optional MCP + subagent | Maps to doc_studio / artifacts; the "reader test" needs a subagent step |
| mcp-builder | ~11k chars | reference/ x5 (best practices, python, node v1/v2, evaluation) | network, npm, npx inspector | Maps to Developer Sahayak + Bazar MCP; needs the network + a build box |
| skill-creator | ~25k chars | agents/ x3, references/, assets/, scripts/ x4, eval-viewer | subagents, `claude -p` CLI, browser viewer | HARDEST. Core ideas portable; its machinery is Claude-CLI-bound |

## 2. Licence verdict (checked)
- `mcp-builder` and `canvas-design` LICENSE.txt = Apache 2.0, (c) Anthropic. Copy, modify, redistribute allowed IF we
  keep the licence text, mark changed files, keep notices. Same expected for internal-comms, webapp-testing,
  frontend-design, theme-factory (each says "Complete terms in LICENSE.txt").
- `skill-creator` and `doc-coauthoring` frontmatter has NO license field -> S0 must read their folder for a LICENSE.txt
  and the repo root. If none is found, do not copy their text: write a Hoola-original skill from the idea instead.
- Each imported skill keeps its LICENSE.txt beside it, plus a line in THIRD_PARTY_NOTICES.md and a
  "Modified by Newtika for Hoola" notice in the file. No Anthropic trademarks in the Hoola UI beyond origin credit.

## 3. Hard blockers found in Hoola's store (`coder/skills_store.py`)
- `BODY_MAX = 4000` chars: only internal-comms, theme-factory and (barely) webapp-testing fit. The other five are
  10-25k chars -> REFUSED today. `DESC_MAX = 60`: all eight Anthropic descriptions are longer -> REFUSED.
- One `.md` file per skill: no `reference/`, `examples/`, `themes/`, `scripts/`, fonts. Six of eight need these.
- So the order is forced: S1 (folder skills + higher limits) and S2 (read_file) come BEFORE any of the eight.

## 4. Phases for the pilot
**P0 - Licence + map (docs).** Read each folder's LICENSE.txt, record verdicts in
`docs/research/skills/licences.md`; write `map.md` rows for the 8 (tool mapping: bash->pylab/server tools,
Playwright->browser_worker, create_file/str_replace->doc_studio/artifacts, WebFetch->scrape tools).

**P1 - Store upgrade (S1+S2 of the main plan).** Folder layout `skills/<tenant>/<name>/SKILL.md` + resources, old
single files still read; imported skills may have a 1,024-char description and ~25k body; calls inject only the first
60 chars; `skill_manage read_file(name, path)` confined to the skill folder with a size cap; parse and honour
`enabled`, `when_to_use`, `disable-model-invocation`, `user-invocable`; zip import. Tests: round-trip a real
Anthropic skill zip.

**P2 - Wave 1: no-script, content skills.** internal-comms, theme-factory, frontend-design. Each gets a
"Hoola note" section: reply in the user's language, Hinglish examples added beside the English ones, outputs go
through doc_studio / site kit / artifact tools. frontend-design is reconciled with the existing design rules in
site/kit.py so the two never give conflicting advice (one wins by a written precedence line).

**P3 - Wave 2: tool-mapped skills.** doc-coauthoring (-> doc_studio + artifacts, reader-test step becomes a
fresh-context model call, not a subagent), canvas-design (-> Create Studio / HOOLA PRINT render path; fonts folder
vendored only if its licence allows, else Hoola's bundled Noto/Literata set), webapp-testing (-> browser_worker; its
`with_server.py` runs only via S3 sandbox rules, otherwise the skill is guidance-only and says so).

**P4 - Wave 3: builder skills.** mcp-builder (-> Developer Sahayak flow; needs the dev lab box `app/devlab` for
npm/npx, network-off by default, so the "install deps" step is honest about what it cannot do), skill-creator
(Hoola-original: keep the interview -> draft -> test-prompts -> improve loop, replace `claude -p` and subagents
with a Hoola eval run of N fixed asks scored by the new skills card; no browser viewer, results show in the Skill Desk).

**P5 - Proof card.** `python -m app.quality skills` with 3 fixed asks per skill (24 total) + 4 negative asks that
must NOT trigger. Score: triggered right / wrong / missed, reference file actually read, rupees per ask. Free run
first (is it in view and reachable), live run after. A skill is "shipped" only with its number.

**P6 - Desk + docs.** Skill Desk shows source "Anthropic (Apache 2.0)", the licence link, parked toggle.
HISTORY.md section, one CLAUDE.md line.

## 5. Order and exit criteria
P0 -> P1 -> P2 (3 skills live + card) -> P3 -> P4 -> P5/P6. Ship P2 first: it proves the whole pipe with the three
safest skills. Exit per wave: store tests green, card numbers printed, nothing in the frozen PC files touched.

## 6. Risks
1. Prompt-injection: imported skill text is treated as DATA from a third party, never a higher-authority instruction;
   it cannot grant tools, change approvals or touch money rules. Scripts: approval card on first run + sandbox only.
2. Token cost: a 25k-char skill read on every turn is expensive. Level-2 body is read only on a match, and the
   card reports tokens per ask.
3. Conflicts with existing Hoola rules (reply style, design kit, NON-NEGOTIABLE rules): the Hoola note states
   "house rules win", tested with a conflict ask.
4. Version collisions with the parallel dev chain: re-version on rebase, keep both works.
5. skill-creator is the weakest fit; if P4 shows it cannot run honestly without the Claude CLI, ship the
   Hoola-original smaller version and say so plainly.

## 7. Decisions needed from the owner
- GO for P0+P1 now (server-only, no APK, no PC files)?
- skill-creator: accept a Hoola-original version if its licence is unclear or its machinery cannot run?
- webapp-testing and mcp-builder scripts: sandbox-only with first-run approval (recommended)?

## 8. Status log
- 4 Nov 2026 P0 DONE (licences + tool map in docs/research/skills/). P1 DONE (folder skills, Claude limits for
  imported skills, read_file, zip import/export; commit eb67c647).
- 4 Nov 2026 P2 DONE: internal-comms, theme-factory, frontend-design seeded from `skillpack/claude/` via
  `skill_packs.seed_claude` (own once-ever stamp, switch `claude_skills_enabled`, rides the Skill Desk's first open
  like BYOX). Upstream text pinned unchanged by hash; Hoola note + Hinglish when_to_use added. Retrieval card in
  tests: 10/10 asks find the right skill in the injected top 2 (English + Hinglish) on a 44-skill tenant, 0/4
  unrelated asks pull a pack skill in. NOT measured: a live model actually following the skills (needs the P5 live card).
- 4 Nov 2026 P3 DONE: canvas-design (upstream, WITHOUT canvas-fonts: 5.5 MB of Latin-only binary fonts the model
  cannot read, one copy per tenant), webapp-testing (upstream; its scripts are stored for reading only, the Hoola note
  says plainly they are not run), and coauthor-docs (Hoola ORIGINAL: upstream doc-coauthoring has no licence file).
  Pack = 6 skills, desk = 47. Retrieval card 16/16 right skill in the injected top 2, 0/4 unrelated asks pull one in.
  Still open: font licences only matter if fonts are ever vendored; script execution (S3) not started.
- 4 Nov 2026 P4 DONE: mcp-builder (upstream, with its 5 reference guides and scripts/ stored for reading only; the
  Hoola note says "written, not run", points to Bazar before building, scrape_page instead of WebFetch) and
  skill-maker (Hoola ORIGINAL replacement for skill-creator: interview, draft inside the 60/4,000 limits, dry-run on
  sample asks, save only after her yes, tune from the desk numbers; it says plainly the dry-run is reasoning, not a
  test suite). Pack = 8 skills (5 upstream + mcp-builder = 6 upstream, 2 originals), desk = 49.
  Retrieval card 20/20 right skill in the injected top 2. The card caught a real false positive: skill-maker's own
  example words (gst, sharma, invoice) pulled it into GST asks; fixed by neutral examples. FTS is an OR of words, so
  common Hinglish verbs (banao, likho) in a when_to_use line widen matches: keep trigger lines to distinctive nouns.
  Still open: P5 live card (does a model really follow them), S3 script running, S4 wider candidate selection,
  seeding on first chat turn, version bump.
- 4 Nov 2026 P5 DONE (free card + live card built; LIVE CARD NOT RUN: no model key in the build sandbox).
  `python -m app.quality skills [--live]` (`quality/skills_asks.py` 10 positive + 4 unrelated asks, `quality/skillscard.py`).
  FREE card: right skill in the injected top 2 10/10, skill_manage callable 10/10, files open 10/10, unrelated asks
  leave the pack out 4/4. LIVE card (to run on the VPS with a key): opened the skill, opened the file it needed,
  markers in the reply, honest about limits (webapp-testing, mcp-builder asks invite a false "it passed" claim),
  does NOT save a skill before the user says yes (skill-maker), rupees per answer. Markers prove the guidance
  reached the reply, not that the writing is good.
  FOUND BY THE CARD (a real bug since v0.477): `skill_manage` is in the non-core `skill` family, so on an ordinary
  turn it was NOT in the model's tool list while the prompt said "skill_manage read the skill before you follow it":
  a matched skill could not be opened without a tool_search detour. Fixed: `coder.inject.admit_tool` admits that one
  tool when a skill matches the ask (no match / switch off = no extra tool); the agent loop calls it after admission.
  NOT FIXED: voice calls (skill_manage is not a declared call tool; a call hands work to santosh_kaam).
- 4 Nov 2026 FIX SEEDING DONE: `skill_packs.seed_all` (starters + BYOX + Claude pack, each its own once-ever stamp)
  now runs on a user's FIRST memory-block build (`inject.primer`: chat turn or call start), not only when the Skill
  Desk opens; remembered per process (keyed by coder dir + tenant) so later turns pay nothing; internal tenants
  ('_packs', '__quality__', ...) are never auto-seeded; a skill she deleted stays deleted (stamps); switches still
  work and re-arm without a restart; a failing pack is retried next turn. First turn pays a one-off file copy.
  Regression run: 280 tests pass; 2 failures are PRE-EXISTING on the committed code and unrelated
  (test_v0473 coder_routes_mounted: FastAPI `_IncludedRouter` has no `.path` in this sandbox; test_v108 voice memory:
  `_tone_tag` missing on a fake).
- 4 Nov 2026 MERGED WITH main (v0.499.0): main had moved 8 commits (PROG pack, Superpowers pack, UIUX, code graph...).
  Conflicts kept BOTH works: `seed_all` now runs five packs (starters, BYOX, PROG, superpowers, Claude) exactly-once
  each; desk = 11 + 31 + 2 + 15 + 8 = 67 skills; config keeps `claude_skills_enabled` + `progpack_enabled` + `sp_enabled`.
  Found while merging: skill search matched on ANY word, so a plain weather ask ("... mein ...") pulled the PROG skill
  in (and with it the skill_manage tool schema). `store.skills_search` now drops everyday English/Hinglish filler words.
  The three other-chain desk-route pins that grepped service.py for a literal seed call now check seed_all.
  Regression: 332 related tests; 12 failures are PRE-EXISTING (identical on a clean origin/main checkout):
  5 stale version pins, 5 UIUX vendored-engine tests, coder routes_mounted (FastAPI sandbox), voice memory `_tone_tag`.
