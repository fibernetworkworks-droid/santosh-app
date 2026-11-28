# Third-party notices

## claude-seo (ideas and thresholds for Hoola SEO PRO, v0.319)

Hoola's SEO checks in `server/app/seo/pro.py` (and the SEO PRO parts of `seo/service.py`, `seo/desk.py` and
`site/sitemap.py`) were designed after studying the open-source project **claude-seo** by AgriciDaniel
(https://github.com/AgriciDaniel/claude-seo, v2.5.0, commit 6be93f4). No code was copied: the checks, texts and lists are
Hoola's own, re-written for Indian small businesses. These ideas and numbers came from that project:

- the 7-part health score weights (technical 22, content 23, on-page 20, schema 10, performance 10, AI readiness 10,
  images 5) and the critical / high / medium / low buckets
- the 17 page-drift comparison rules
- the AI crawler split (search bots vs training bots vs user-triggered fetchers)
- page-type word-count floors, image weight bands, scaled-content gates (30-40% unique; 100 / 500 pages; location
  pages 30 / 50), templated-metadata detection
- the E-E-A-T (20 / 25 / 25 / 30) and local search (25 / 20 / 20 / 15 / 10 / 10) scorecard weights
- the retired / no-rich-result structured data types and the Google updates ledger (dates from Google's own Search
  Status Dashboard and Search Central)
- the report envelope: first principle, how we would know it failed, leading indicator

Not used on purpose (Hoola works through official routes only): Google results scraping (site: lookups, SERP / competitor
scoring, briefs from results), paid third-party SEO data providers, crawler impersonation, AI-text "humanising", the
Indexing API for ordinary pages, and the project's CC BY-SA phrase lists and CC BY prompts.

claude-seo is licensed under the MIT License:

```
MIT License

Copyright (c) 2026 agricidaniel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## ECC (agent instructions adapted for Developer Sahayak, v0.402)

The specialist instructions in `server/app/devsahayak/specialists.py` (PR reviewer discipline, the per-language reviewer
and CI-fixer notes, the focused security / silent-failure / test-coverage passes) were adapted from the agent files of the
open-source project **ECC** by Affaan Mustafa (https://github.com/affaan-m/ECC, v2.2.3, commit b38be6a): `code-reviewer`,
`security-reviewer`, `silent-failure-hunter`, `pr-test-analyzer`, the `*-reviewer` and `*-build-resolver` agents for
Python, TypeScript / JavaScript, Flutter / Dart, Kotlin, Go, Java, Swift and Rust, and `database-reviewer`. The text was
condensed and re-written for Hoola's read-only tools, CI logs and safety rules; no code was copied and nothing from ECC
runs inside Hoola. v0.794 (owner: "ADD ALL MISSING ECC AGENTS TO HOOLA CODE") widened this to ECC's whole agent roster that fits a
coding session: 63 of ECC's 71 agent files (ECC v2.2.3, commit d2ef268) and its `rules/` (common + 21 languages) were
condensed and rewritten as text in `server/app/devsahayak/ecc/` (the 8 left out are listed with reasons in
`ecc.NOT_ADDED`), and ECC's pre-commit quality hook was re-implemented as Hoola's own Python (`ecc.gate`). Hoola Code
hands work to these agents with its own `agent` tool (`devsahayak/subagent.py`). Still no ECC code runs inside Hoola.

ECC is distributed under the MIT License:

```
MIT License

Copyright (c) 2026 Affaan Mustafa

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Claude Code Game Studios (ideas for the Hoola Game Crew and the game-desk fixes, v0.406; the read guard, v0.455)

Hoola's Game Crew (`server/app/gamedesk/crew.py`), the task acceptance criteria and evidence, the "not assessed" results
and the Godot 4.5-4.7 notes in `server/app/gamedesk/ai.py` were designed after studying the open-source project
**Claude Code Game Studios** by Donchitos (https://github.com/Donchitos/Claude-Code-Game-Studios, release 1.2.0, commit
05ad7c8). No code or prompt text was copied: the role descriptions, checklists, team flows and code are Hoola's own,
written for Hoola's hosted Game Desk. These ideas came from that project:

v0.455 took one more idea from the same repo's release 1.2.0: its `validate-read.sh` hook, which refuses a
whole-file read of a large design doc and answers with the doc's headings so the retry reads one section.
`.claude/hooks/read-guard.sh` is Hoola's own implementation of that idea (different watched paths, different
size bar, and a headings reply that caps the list because docs/HISTORY.md has 639 headings - printing them all
would be the waste the guard exists to prevent). No code was copied.

- the studio roster (3 directors, 8 department leads, specialists, plus Godot / Unity / Unreal engine specialists) and
  the team flows (combat, narrative, UI, release, polish, audio, level, live ops, QA)
- acceptance criteria covered by a test, a retained screenshot or the owner's answer; evidence stamped with the code it
  proves, so evidence older than the code shows
- "NOT ASSESSED" as a real verdict: a check with no data says so instead of passing
- phase gates with PASS / CONCERNS / FAIL / NOT ASSESSED verdicts that advise and never block her decision
- importing a Godot project first (class cache) before checking scripts, and the list of Godot 4.5-4.7 changes (taken
  from Godot's own migration guides, which that project cites)

Not used on purpose: the Claude Code slash commands, hooks, local file layout and agent prompt files (Hoola is a hosted
service, not a terminal template), and its per-agent model choices.

Claude Code Game Studios is licensed under the MIT License:

```
MIT License

Copyright (c) 2026 Donchitos

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## MapLibre GL JS 4.7.1 (v0.412 NAKSHA LIVE)

Vendored unchanged at `server/app/static/vendor/maplibre/` (maplibre-gl.js, maplibre-gl.css). It draws the maps in the
native apps' tracking screens (Android WebView) and the console's riders map. BSD-3-Clause, full text in
`server/app/static/vendor/maplibre/LICENSE.txt`. Map tiles come from OpenFreeMap (https://openfreemap.org, free, no key);
the map shows their attribution: © OpenFreeMap, © OpenMapTiles, data © OpenStreetMap contributors (ODbL).

## Anthropic example skills (Apache License 2.0)

Shipped (v0.494, `server/app/coder/skillpack/claude/`): **internal-comms**, **theme-factory**, **frontend-design**,
**canvas-design** (without its canvas-fonts folder, which is not shipped), **webapp-testing**, **mcp-builder**,
from https://github.com/anthropics/skills (commit ca45fc49), Copyright Anthropic, PBC, licensed under the Apache
License, Version 2.0. Each folder keeps its own LICENSE.txt. Changes by Newtika for Hoola (marked in each SKILL.md
under "Hoola note"): one added `when_to_use` frontmatter line and an appended Hoola section; the original text is
otherwise unchanged and pinned by a hash test. No Anthropic trademarks are used beyond naming the origin.

Also in that folder: **coauthor-docs** and **skill-maker**, Hoola originals (the upstream doc-coauthoring has no
licence file, and the upstream skill-creator needs the Claude command line tool and sub-agents, so none of their
text is used).
Licence verdicts: `docs/research/skills/licences.md`.

## Mermaid (diagram drawing for the Architecture Desk, v0.413)

`server/app/archdesk/vendor/mermaid.min.js` is Mermaid 11.4.1 (https://github.com/mermaid-js/mermaid), unmodified,
used to draw architecture diagrams inside the server's headless Chromium. It is never served to users.
MIT License - Copyright (c) 2014-2024 Knut Sveidqvist and contributors. Permission is hereby granted, free of charge,
to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the
Software without restriction, including without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to
do so, subject to the following conditions: The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

## crawl4ai (ideas only, no code) — v0.537 CRAWL BRAIN

Source read: https://github.com/unclecode/crawl4ai @ v0.9.5 (commit cae74b2), Apache-2.0.

**No crawl4ai code is in this tree.** `server/app/crawl/` re-implements published algorithms from their
formulas: a confidence-weighted stopping rule, a boilerplate-pruning content filter, best-first frontier
scoring, sitemap/Common-Crawl URL seeding, data-vs-layout table scoring, chunking strategies, anti-bot
block fingerprinting, proxy rotation, and a step script compiled to JavaScript.

That is not only house style (the "port law" that built `app/aep`, `app/crew`, `app/dhara`). crawl4ai
vendors a fork of **html2text** at `crawl4ai/html2text/` declaring upstream's own release `2024.2.26`,
carrying no copyright line and no licence header — and **upstream html2text is distributed under the
GPLv3** ("Originally written by Aaron Swartz. This code is distributed under the GPLv3", plus a GNU GPL v3
`COPYING`). Both `markdown_generation_strategy.py` and `utils.py` import that fork, so every
page-to-markdown conversion in the library runs through GPL'd code inside an Apache-2.0 repository.
`server/app/agent/crawl_jobs.py` already keeps Firecrawl's AGPL engine out of this tree for the same
reason.

Two of crawl4ai's capabilities were deliberately **not** reproduced, and `server/app/crawl/__init__.py`
records why: mining robots.txt `Disallow:` entries as a URL-discovery source, and minting rotating
residential proxies from a commercial provider's API.

## lottie-web 5.13.0 (light player) - MIT
Copyright (c) 2015 Airbnb, Inc. Vendored as `server/app/site/assets/vendor/lottie_light.min.js` (licence beside it:
`lottie-web.LICENSE.md`), served from her own website only on pages that show an animation (v0.568).

## three.js r187 - MIT
Copyright (c) 2010-2026 three.js authors. The parts Hoola's 3D hero scenes use, bundled into
`server/app/site/assets/vendor/three-hero.js` (licence: `three.LICENSE.txt`; rebuild steps: `vendor/REBUILD.md`) (v0.568).

## Impeccable (pbakaus/impeccable) - Apache-2.0
Copyright (c) Paul Bakaus and contributors. Read at commit c8891a9a (5 Nov 2026); notes in
`docs/research/impeccable/00_READ.md`. **No upstream code is included.** The website "AI look" check
(`server/app/site/look.py`, v0.606) and the section writer's CRAFT FLOOR (`server/app/site/ai.py`) are Hoola's own
Python and wording built from Impeccable's ideas: its anti-pattern catalogue (the reflex tells of AI-generated pages),
its craft-floor checks, its surface modes (persuade / operate / read / experience) and its rule that the user's own
brief wins over every warning. Impeccable itself credits ehmo/platform-design-skills (MIT) for its iOS / Android
references, which Hoola did not use.

## AI Website Cloner Template (JCodesMore/ai-website-cloner-template) - MIT
Read at commit ee3f5a2f (5 Oct 2026); notes in `docs/research/website_cloner/00_READ.md`. **No upstream code is included.**
`server/app/site/moved.py` (v0.622) is Hoola's own Python built from two of its ideas - keep a source-URL -> new-route map
when a site moves, and compare the old page and the new one at the same width - applied ONLY to the user's own old site
(ownership proved first, v0.567). Hoola does not clone sites the user does not own.

## The Agency (msitarzewski/agency-agents) - MIT
Copyright (c) 2025 AgentLand Contributors. Read at commit 8ae6164 (8 Nov 2026). **No upstream code is included and
nothing from it runs inside Hoola.** v0.814 (owner: "GO 1 2 3") condensed and rewrote, as text: 35 of its engineering /
testing / security / specialist agent files for Hoola Code (`server/app/devsahayak/ecc/agency_eng.py`,
`agency_qa.py` - the persona, emoji and internet-only parts dropped; the reality checker is used as the last look
before a coding round finishes), and its 21 game-development agent files as expert notes + 8 new engine roles for the
Game Developer's crew (`server/app/gamedesk/agency.py`). The Agency is distributed under the MIT License:

```
MIT License

Copyright (c) 2025 AgentLand Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## claude-mem (thedotmack/claude-mem) - Apache-2.0
Read at commit 6b779c0 (10 Nov 2026). **No upstream code is included.** v0.828.0 HOOLA CODE MEMORY
(`server/app/devsahayak/memory.py`) is Hoola's own Python built from its design: an observer that turns a session's work
into typed observations + a summary, a budget-fitted index at the start of the next session, and the three-step
search -> timeline -> details retrieval. (Hoola's chat memory, `server/app/coder/`, v0.485, followed the same design.)

## Bundled fonts (phone app, v0.859 R0) - SIL Open Font License 1.1

`assets/fonts/` holds static TTF files of Manrope, Sora, Literata, Schibsted Grotesk and JetBrains Mono, downloaded
unchanged from Google Fonts by `tool/fetch_fonts.py`. All five are licensed under the SIL Open Font License 1.1
(https://openfontlicense.org): free to bundle and redistribute inside an app; the fonts themselves are not sold alone
and their reserved names are not used for changed versions. Copyright stays with their authors (Manrope: Mikhail
Sharanda; Sora: Barbara Ugalde / Sora Project; Literata: TypeTogether; Schibsted Grotesk: Schibsted / Bakken & Baeck;
JetBrains Mono: JetBrains).

## vercel-labs/agent-browser and microsoft/playwright-mcp (Apache License 2.0)
`desktop-linux/pagekit.py` (Hoola PC page engine 2, v0.999.93) follows ideas from these projects: element refs taken
from a page snapshot, a hit-target check before a click, and the before / after snapshot diff. The code is Hoola's own;
no source file was copied. Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0

## andrej-karpathy-skills (forrestchang / multica-ai) - MIT
Read at commit 2c60614 (28 Nov 2026). The repo is text only (a CLAUDE.md, a skill, a Cursor rule and examples) with
four coding rules written from Andrej Karpathy's notes on how coding models go wrong. The repo ships no LICENSE file;
its skill, plugin manifest and README state MIT. **No upstream file is included.** Hoola Code (`server/app/devsahayak/
karpathy.py`) carries the four rules rewritten in Hoola's own words, credited where they appear, and adds its own
in-code check for rule 3 (changes that only touch layout or delete an existing comment).

## Ponytail (DietrichGebert/ponytail) - MIT
Copyright (c) 2026 DietrichGebert. Read at commit ebd8654 (v5.3.3, 28 Nov 2026). **No upstream file is included.**
Hoola Code (`server/app/devsahayak/ponytail.py`) carries Ponytail's rules for the smallest complete change, its levels
(lite / full / ultra / off), and its review, audit and `shortcut:` debt reports, rewritten in Hoola's own words and
credited where they appear. Ponytail is distributed under the MIT License.

## Superpowers (obra/superpowers) - MIT
Copyright (c) 2025 Jesse Vincent. Read at commit 22f0b46 (v7.0.2, 28 Nov 2026). **No upstream file is included.**
Hoola Code (`server/app/devsahayak/superpowers.py` + `superpowers/*.md`) carries 13 of its skills rewritten in Hoola's
own words for Hoola Code's tools, its rule for using skills, and two of its rules (verification before completion, the
three-fix rule of systematic debugging) checked in code. The older condensed copy for Hoola's chat skill desk
(`server/app/coder/skillpack/sp-*.md`, v0.499) is unchanged. Superpowers is distributed under the MIT License.

## ECC skills (affaan-m/ECC) - MIT
Copyright (c) 2026 Affaan Mustafa. Read at commit 4adeee67 (28 Nov 2026). **132 of ECC's skill files are included
unchanged** in `server/app/devsahayak/ecc_skills/` (its language / framework / database / infrastructure skills and its
general coding skills; the skills that set up Claude Code or ECC itself, need outside services, or are not about coding
were left out). Hoola Code reads them through `server/app/devsahayak/eccskills.py`. The `gdscript-reviewer` agent
(`server/app/devsahayak/ecc/reviewers_lang.py`), the config protection (`configguard.py`) and the MCP health check
(`mcphealth.py`) are Hoola's own text and code, adapted from ECC's agent and hooks. So are the repo rule files (`hookify.py`, ECC's Hookify rule-file format), the two-reviewer check (`santa.py`, ECC's Santa method skill by Ronald Skelton), `/test-coverage` (`testcover.py`), the epic commands (`epic.py`) and the learnings export / import (`learnshare.py`, ECC's instinct-export / instinct-import). ECC is distributed under the MIT
License:

```
MIT License

Copyright (c) 2026 Affaan Mustafa

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## Hermes Agent (NousResearch/hermes-agent) - MIT
Copyright (c) 2025 Nous Research. Read at commit d71a6574 (28 Nov 2026). Idea only, no code copied: its scan of
every memory and skill write (`tools/threat_patterns.py`) is the model for Hoola's own `server/app/coder/guard.py`
(Hoola's patterns, rules and code). Hoola's nudge / curator / dreams were already Hoola's own ports of the same ideas.
