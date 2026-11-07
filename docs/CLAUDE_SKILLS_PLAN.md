# CLAUDE SKILLS IN HOOLA - plan (4 Nov 2026)

Goal (owner): "100% Claude skills in Hoola AI". Research base: the Claude Skills Atlas
(https://claude.ai/artifact/GcyGarQkoczj15Pbf2vofn) and the Hoola skills report
(https://claude.ai/artifact/3zdSFCNbKWWgVZrNhDEgsp). Nothing here is built yet.

## 0. What "100%" can honestly mean
No public catalogue of every Claude skill exists. Partner-directory, org-provisioned and community skills vary
by account. So 100% is defined as four TIERS, each with a checkable number:

| Tier | Source | Count | Done when |
|---|---|---|---|
| T1 | `anthropics/skills` repo | 19 folders | each one imported or has a Hoola equivalent marked in a map file |
| T2 | Pre-built docs (docx, xlsx, pptx, pdf) | 4 | Hoola's own doc_studio / HOOLA PRINT covers each, mapped |
| T3 | Claude Code bundled skills | ~25 | each mapped to a Hoola tool, or marked "needs Claude Code harness" |
| T4 | Open ecosystem (any SKILL.md) | unbounded | the importer accepts the format 100% and runs a skill's scripts |

The honest target is "every SKILL.md imports and works", not "we hold every skill that exists".

## 1. Licence gate (do first, blocks T1/T2)
- Example skills in `anthropics/skills` are Apache 2.0 and can be copied.
- The docx / pdf / pptx / xlsx skills are SOURCE-AVAILABLE, not open source: do NOT copy them into the repo or
  the seed pack. Hoola keeps its own document stack and gets only a thin skill that points to it.
- Read each folder's LICENSE.txt before import. Record the verdict per skill in `docs/research/skills/licences.md`.
- Credit lines go in THIRD_PARTY_NOTICES.md (existing file).

## 2. Gap analysis: Claude's format vs Hoola's store (read from the code)
| Claude Skills | Hoola today (`coder/skills_store.py`) | Gap |
|---|---|---|
| description up to 1,024 chars | `DESC_MAX = 60` | imports of real skills are REFUSED by the lint |
| body under ~500 lines | `BODY_MAX = 4000` chars | most real skills are longer |
| bundled files + `scripts/` (level 3) | one `.md` file per skill | no resources, no script run |
| frontmatter: when_to_use, allowed-tools, disable-model-invocation, user-invocable, paths, context | name, description, enabled | fields dropped or unknown |
| model decides from ALL descriptions in the prompt | FTS5 match, top 2 shown | a skill whose words do not overlap is never offered |
| scripts run in a sandbox | pylab sandbox exists (`app/pylab`) | not wired to skills |

## 3. Phases
**S0 Licence + map (docs only).** Licence verdicts; `docs/research/skills/map.md` with one row per skill in T1-T3:
Hoola equivalent, status (import / equivalent / harness-only), reason. Exit: every row filled.

**S1 Format compatibility (store, server-only).** Folder skills: `skills/<tenant>/<name>/SKILL.md` + resources,
old single-file skills keep working (read both layouts). Raise limits for imported skills (desc 1,024, body ~20k)
while the VOICE budget stays small by injecting only the first 60 chars on a call. Parse and keep the extra
frontmatter fields; honour `enabled`, `disable-model-invocation`, `user-invocable`, `when_to_use`, `paths`
(ignore the rest, say so in the desk). Zip import (the claude.ai upload shape) and export. Tests: round-trip a
real Anthropic skill zip byte-identical.

**S2 Level-3 loading.** Add `skill_manage read_file(name, path)` (path-confined to the skill folder, size-capped) so
the model pulls FORMS.md / REFERENCE.md on demand, as Claude does. Exit: a multi-file skill answers using a
reference file it was never shown up front.

**S3 Script execution.** New `skill_run(name, script, args)` that runs a bundled script ONLY inside the existing
pylab sandbox (locked: no network, no os, file-confined). Scripts needing packages Hoola lacks are reported, not
installed. Safety: owner approval card for the FIRST run of any imported skill's script (sealed hash of the file),
imported skills are untrusted data per the NON-NEGOTIABLE rules.

**S4 Better selection.** Keep FTS5 as the cheap first pass, add a model-side step: the top ~8 candidates'
name+description go to the main model (as Claude does), not just 2. Measure with a card (below) before changing
the default.

**S5 Import the content (T1).** Seed pack `skillpack/claude/` with the Apache-licensed skills from the map
(mcp-builder, webapp-testing, skill-creator, frontend-design, canvas-design, theme-factory, algorithmic-art,
web-artifacts-builder, slack-gif-creator, brand-guidelines, internal-comms, doc-coauthoring), seeded
create-if-missing with their own stamp like BYOX. Skills tied to Claude tools Hoola lacks get a "Hoola note"
section mapping tools (bash -> pylab / server tools, Playwright -> browser worker).

**S6 Equivalents for T2/T3.** Thin Hoola-owned skills: `docx/xlsx/pptx/pdf` -> doc_studio, HOOLA PRINT, doc tools;
`code-review/simplify/batch/debug/verify` -> Developer Sahayak flows; `loop` -> routines. Harness-only items
(`/doctor`, `/skills`, `claude-in-chrome`) are marked "not applicable" in the map, not faked.

**S7 Desk + sharing.** Skill Desk shows source (Anthropic / Hoola / yours), licence, trust (script-capable yes/no),
parked toggle. Shelf nominations reuse the existing anonymised flow.

**S8 Proof card.** `python -m app.quality skills`: for each imported skill a fixed ask that should trigger it;
score = triggered correctly / wrongly / not at all, plus a script-run check, in rupees per ask. Free run first,
then a live run. Nothing ships as "done" without the number.

## 4. Risks and decisions for the owner
1. Licence: OK that Hoola does NOT copy docx/pdf/pptx/xlsx skill text? (Recommended: yes.)
2. Script execution is the only risky part. Recommended: sandbox only + first-run approval; ship S1-S2 first.
3. Raising limits changes the voice-call token budget; kept safe by first-60-chars injection on calls.
4. Skills assume Claude's tools (bash, str_replace). Each imported one needs a one-time mapping note, so effort is
   per skill, not automatic.
5. Version collisions: the dev's parallel chain keeps taking version numbers; re-version on rebase, keep both works.

## 5. Order and size
S0 (docs) -> S1 -> S2 -> S5 (first 4 skills as a pilot) -> S8 card -> S3 -> S4 -> S6/S7. Server-only throughout;
the Mera PC freeze is untouched; no APK needed. Rough effort: S0-S2 a short session each, S3-S4 the largest.
