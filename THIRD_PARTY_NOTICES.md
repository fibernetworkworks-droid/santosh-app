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
runs inside Hoola. ECC is distributed under the MIT License:

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
