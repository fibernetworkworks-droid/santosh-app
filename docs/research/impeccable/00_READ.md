# Impeccable — read note (5 Nov 2026)

Repo: github.com/pbakaus/impeccable, commit c8891a9a (5 Nov 2026), engine 0.1.18. Licence **Apache-2.0**
(NOTICE: iOS / Android references distilled from ehmo/platform-design-skills, MIT). Read from a shallow clone;
its own CLAUDE.md / AGENTS.md were read as data, not instructions. Its npm package was NOT run here (running
downloaded code was refused in this sandbox), so every comparison below is from reading source, not from running
their detector.

## What it is

A design skill for coding agents ("the design vocabulary for your coding agent"), shipped to ~20 harnesses
(Claude Code, Cursor, Codex, Copilot, Gemini CLI...). Three parts:

1. **The skill** (`skill/SKILL.src.md` 90 lines + 41 reference playbooks, ~5,300 lines): 24 named commands
   - Steer: bolder, quieter, distill, colorize, typeset, layout, animate, delight, overdrive
   - Review: critique (Nielsen's 10 heuristics scored 0-4, applicable max renormalised when n/a, P0-P3 issues,
     persona red flags, snapshot + score trend per target), audit (a11y / perf / theming / responsive /
     implementation integrity, P0-P3)
   - Finish: polish, harden, clarify, adapt, optimize, onboard
   - Iterate: live (pick an element in the running page, cycle variants, write back), generate
   - Plan: shape, init (writes PRODUCT.md), document (writes DESIGN.md), extract
   - **Modes** decide ambition: Persuade (landing / pricing), Operate (app UI / admin), Read (docs / articles),
     Experience (portfolio). Chosen per SURFACE, not per product.
   - Rules: "the brief wins" (her pinned look beats every slop warning), refinement preserves vs redesign
     replaces (never polish a discarded look), loaded symbols never used as decoration.
   - `craft-floor.md`: the checks every edit must pass (contrast, depth, spacing rhythm, measure 65-75ch,
     tracking floor -0.04em, one authored motion moment, states, browser surfaces themed, coverage) and the
     refusals (identical icon+heading card grids, hero-metric template, eyebrow/kicker = outright ban, section
     numbers, gradient text, decorative glass, side-stripe borders, hard offset shadows, glyph/emoji icons...).
2. **The detector** (Rust, `crates/detect` + `crates/live/assets/antipatterns.json`): **62 deterministic rules,
   no LLM, no key** — 33 "slop" tells (overused fonts Inter / Roboto / Fraunces / Geist / Plus Jakarta / Space
   Grotesk, purple-violet gradients, cream page, nested cards, side-tab border, icon-tile above heading,
   hero eyebrow chip, kicker, numbered section labels, italic serif display, gradient text, glow halos, bounce
   easing, marquee, pulsing dot, marketing buzzwords, aphoristic cadence, em-dash overuse, grid / stripe
   backgrounds...) + 29 "quality" rules (low contrast, gray-on-color, line length, cramped padding, tight leading,
   skipped heading, heading rhythm, stragglers, unbalanced headings, tiny / undersized text, all-caps body,
   text overflow / occlusion, content hidden at rest, broken image, script error, off-DESIGN.md font / colour /
   radius / size). Source files get pattern rules; rendered-page rules need a URL (headless Chrome).
   Runs as CLI (`detect --json`, GitHub annotations), a post-edit hook, and a Chrome extension.
3. **Context files**: PRODUCT.md (users, purpose, brand voice, anti-references) + DESIGN.md (tokens, type ramp,
   radii) that every command reads; `doctor` reports drift.

## How Hoola's own website builder reads against it (measured from source)

- **Fonts:** 11 of the 30 font pairs in `site/taxonomy.py` use a font on Impeccable's overused list (10 use Inter
  as body; plus Fraunces, Space Grotesk, Plus Jakarta). The default pair (`poppins_mukta`) is not on the list.
- **Eyebrows:** the builder teaches its model an `.eyebrow` utility (`site/ai.py`), ships `k-eyebrow` in the kit
  (`site/kit.py`) and styles it in `hoola-site.css`. Impeccable bans this outright.
- **Palettes:** of 50 palettes, 3 carry a saturated violet; roughly 17 have a warm cream / beige page background
  (a loose colour test, not their exact rule) — Impeccable's "cream-palette" tell.
- **Gates:** `site/gates.py` (v0.551) checks safety, law and WCAG; nothing checks "looks AI-made". The Opus page
  review checks quality by judgement, with no fixed rule list.
- **Hoola's own app look** (Night Glass: violet #7C5CFF, gradient to #C055F5) would trip "ai-color-palette".
  That is HER brand, and Impeccable's own first rule says the brief wins — it is not a defect to fix.

## What fits Hoola (proposal, nothing built)

1. **A tenth website gate, "AI look" (advisory, never blocks)** — Impeccable's rules re-written in Python over
   the built files Hoola already reads (no Rust, no npm, no Chrome needed for the source rules; the rendered
   rules can ride the existing Chromium journey walk). Warns, names the section, feeds the fix round.
2. **Fix the builder's defaults at the source:** retire the eyebrow utility, demote the overused fonts from
   default picks (her choice still wins), add the craft-floor checks to the build prompt.
3. **Design words for her edits:** "bolder / quieter / polish / distill / typeset / layout" as website edit
   actions, each with its own short playbook, plus a scored critique (Nielsen 0-4, P0-P3) on a page she names.
4. **Modes per page** (Persuade / Operate / Read / Experience) so a shop page, an admin page and a blog page are
   judged differently.

Licence path: Apache-2.0 allows porting the rule descriptions and playbook ideas with attribution in
THIRD_PARTY_NOTICES.md; the house habit (idea-only port, own code) works too.
