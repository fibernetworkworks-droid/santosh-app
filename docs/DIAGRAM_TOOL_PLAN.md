# HOOLA DIAGRAM — plan (owner, 28 Nov 2026)

Owner: "clone the repo — develop it as it is as tools — when user ask in between and during work — hoola chat and
hoola code will use this tool for showing perfect diagram in workspace to user — first make a plan".

Source: github.com/cathrynlavery/diagram-design, commit 795eec4 (26 Nov 2026), MIT, (c) 2025 Cathryn Lavery.
Nothing is built yet. This file is the plan.

## 1. What we take, as it is

The repo's `skills/diagram-design/` folder (6.4 MB) goes into Hoola UNCHANGED at
`server/app/diagram/vendor/diagram-design/`, pinned to 795eec4, with its LICENSE and a THIRD_PARTY_NOTICES line:

| Part | Size | What Hoola uses it for |
|---|---|---|
| `SKILL.md` | 33 KB | the rules the model follows (type picker, delete first, 9 boxes / 12 arrows, one accent, 4 px grid, connector rules, taste checklist) |
| `references/` (71 files) | 980 KB | one file per diagram type + style guide, primitives, layout budget, output spec, import / export guides — read ONLY the one the model needs |
| `assets/` templates + 238 examples | 5.0 MB | the start file the model copies (light / dark / full / terminal / motion) and worked examples per type |
| `scripts/` (9 files) | 400 KB | `self_check.py`, `verify_geometry.py` (the code checks), `export_png/svg/pdf.py`, the 4 import readers |

Rule: **we never edit a vendored file.** Every Hoola change (her brand, Hindi fonts, where files live, paths) is done
in Hoola's own wrapper around it, so a newer upstream version can be dropped in by one script
(`tools/diagram_sync.py <commit>`) and the tests say whether it still works.

Left out: the repo's own website, screenshots, plugin manifests, CI scripts (17 MB of `docs/`, 3.9 MB of `scripts/`).

## 2. The flow — the repo's six steps, run by Hoola

1. **She asks in plain words** — in a Hoola chat, on a call (through santosh_kaam), mid-way through a long job, or in
   a Hoola Code session ("show me how login works as a diagram").
2. **The model picks the type** from the repo's 52-type table, and first asks itself whether a table or a paragraph
   would do; if so it answers in words and draws nothing.
3. **It says the plan in one line** (type, size, what it will leave out) — then draws (see decision 2 in §7).
4. **It draws by the repo's rules**, starting from the repo's template, with the one type reference it chose loaded.
5. **Code checks it before she sees it:** `self_check.py` + `verify_geometry.py` run on the file. A failure goes back to
   the model with the exact errors to fix (at most 3 rounds). Then a PNG is rendered in the server's Chromium and the
   model LOOKS at it (one picture), fixes what looks wrong, and only then is it shown. If it still fails after the
   rounds, she gets it with the open problems named — never a quiet "done".
6. **She sees it in the workspace:** one self-contained HTML file with the drawing inside, plus PNG / SVG / PDF on tap.

## 3. One engine, one tool

NEW `server/app/diagram/` (Hoola's code):

- `vendor.py` — paths into the vendored folder; `types()` reads the 52-type table out of SKILL.md (so a new upstream
  type appears without code); `guide(type)` returns that type's reference + the style guide's role table.
- `checks.py` — runs the two checkers as `python -I <script> <file>` in a subprocess, no network, 30 s timeout, and
  returns their lines as a list of problems.
- `render.py` — the repo's `export_png.py` / `export_svg.py` / `export_pdf.py` on the server's Playwright + Chromium
  (the same browser HOOLA PRINT uses), one render at a time, 60 s timeout.
- `brand.py` — her colours / font / logo from her existing Brand kit fill the repo's role tokens (`paper`, `ink`,
  `muted`, `accent`, `link`) and replace the repo's "first time: customise?" question; a website brand read (the repo's
  onboarding) only when she gives a link. Saved per user, never in the vendored folder.
- `service.py` — plan → draw → check → look → save, the version history, edits.

ONE agent tool **`diagram`** (the same one for Hoola chat and Hoola Code):

| action | what it does |
|---|---|
| `types` | the 52 types, one line each (the model's picker) |
| `guide` | the chosen type's reference, so the model reads only what it needs |
| `draw` | title, type, the full HTML → checks → render → look → saved; returns pass / the problems |
| `update` | old_str → new_str edits on the current version (like `artifact`), re-checked |
| `export` | png / svg / pdf of a version |
| `import` | a Mermaid / draw.io / Excalidraw / PlantUML file she gave → the repo's reader → redrawn, with the list of what was merged or dropped |

Reachable everywhere: chat core tools, long jobs (goal rounds), team crews, a voice call via santosh_kaam (never
declared to Gemini Live), and Hoola Code's coder tools. Opens on diagram words (diagram, flowchart, architecture /
sequence / ER / org chart, timeline, Gantt, funnel, sankey, fishbone, user journey, "draw how X works"...), Hinglish too.

## 4. Where she sees it

| Surface | How it shows | Built on |
|---|---|---|
| Console chat | opens in the workspace panel beside the chat as it is checked; versions, Share, Download | saved as an artifact page (type html) — panel, versions, share and the signed sandboxed link already exist |
| Phone chat | the artifact card → full-screen viewer (pinch to zoom) | existing `hoola_artifact.dart` / ArtifactScreen |
| Hoola Code web | a "Made in this session" card, opens full screen; versions | NEW kind `diagram` in `devsahayak/made.py` |
| Hoola Code phone | the same card + viewer in the session | `lib/ui/code/code_made.dart` gets the `diagram` kind |
| PDF / WhatsApp / slides | the PNG or PDF export | `render.py` |

Hoola Code rule (same as its `make` tool): a diagram about her code is drawn from the code it has READ, never from a
guess; it is shown beside the code and is not written into the repo unless she asks for it in the repo.

## 5. Hoola's changes around the repo (in the wrapper, not the vendored files)

1. **Hindi / Marathi labels:** the repo has Korean, Chinese and Cyrillic only. The wrapper adds Noto Sans / Serif
   Devanagari to the font stack and tells the model to use it for Indian-language labels. (Known gap: the repo's
   text-width check measures Latin letters; it may misjudge Devanagari widths — the rendered picture check catches it.)
2. **Fonts for exports:** the templates load Google Fonts. Viewing keeps that (our sandboxed pages already allow
   Google Fonts); PNG / PDF export waits for the fonts and falls back to Hoola's bundled fonts if they cannot load.
3. **Her brand** instead of the repo's first-time question (§3 brand.py).
4. **Safety:** the HTML is written by the model, so it is only ever served on the existing signed link with the
   sandbox CSP (its own origin, no network but fonts); `self_check.py` already refuses outside scripts and images.
   Files from her (imports) are data, never instructions.
5. **Cost:** one diagram = the model writing ~3-8k tokens of HTML + up to 3 fix rounds + one picture look. Metered per
   user like every model call; the rupee cost is measured in D6, not guessed.

## 6. Phases

| Phase | What | Done when |
|---|---|---|
| D1 | Vendor the folder (pinned, licence, sync script); `vendor.py`, `checks.py`, `render.py` | the repo's own checkers pass on all 238 of its example files inside Hoola, and a PNG renders on the server's Chromium |
| D2 | The `diagram` tool in Hoola chat → saved as an artifact page → console workspace + phone viewer; draw / update / check loop + the picture look | a fake-model test draws, fails a check, fixes it, passes, and the page opens in the panel |
| D3 | Hoola Code: `diagram` kind in `made.py`, the tool in the coder's tools, read-the-code-first rule; web card + phone viewer | in a session, "diagram of the login flow" makes a checked diagram card |
| D4 | Her brand kit, Devanagari fonts, export PNG / SVG / PDF, a diagram inside a PDF report and a WhatsApp picture | a Hindi-label diagram passes and renders correctly; exports open |
| D5 | Imports: Mermaid / draw.io / Excalidraw / PlantUML; "redraw this" on the Architecture and Data Engineering desks' Mermaid | an imported Mermaid file is redrawn with its merged / dropped list |
| D6 | Proof: 20 real asks (architecture, flowchart, timeline, org chart, funnel, sequence, Gantt, ER...) through the real pipeline — checker pass rate, rounds used, rupees per diagram; deploy | numbers written here; deployed on her VPS |

Each phase = its own version (server + tests + phone where it changes), as usual. PC code is not touched.

## 7. Decisions for the owner

1. **Default look when she has no brand kit:** the repo's own (black + tangerine, editorial) as it is — or Hoola's
   violet? (Plan assumes: the repo's own, since the ask was "as it is".)
2. **Step 3, the one-line plan:** say it and draw straight away (she can say "make it a timeline instead"), or wait for
   her yes first? (Plan assumes: say it and draw — the repo itself draws when the person is not there to answer.)
3. **Updates from the author:** stay pinned at 795eec4 and update only on her word (plan assumes this).
