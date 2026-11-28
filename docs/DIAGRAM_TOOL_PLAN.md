# HOOLA DIAGRAM — plan v2 (owner, 28 Nov 2026)

Owner: "clone the repo — develop it as it is as tools — when user ask in between and during work — hoola chat and
hoola code will use this tool for showing perfect diagram in workspace to user — first make a plan", then four repos
read one by one, then "rewrite the plan", then "MAKE IT GLOBAL NOT INDIA NATIVE" (§7a). Nothing is built yet; this file is the plan. v1 (diagram-design only) is
replaced by this one.

## 1. The four repos and what each one gives

| Repo (commit read) | Licence | What it is | Role in Hoola |
|---|---|---|---|
| tt-a1i/archify (b42e7d7, v3.3.2) | Apache-2.0 / MIT | The AI writes a small JSON description; archify's OWN CODE places every box, routes every line, then checks it in four gates (schema, build, strict check, real-browser check) before it is delivered. Interactive HTML: click a part, trace a path, upstream / downstream. Also one-page answers ("explainer"), story video, Code Analysis of a repo, PR walkthroughs | **Engine A — the main engine** |
| cathrynlavery/diagram-design (795eec4) | MIT | A skill: 52 diagram types with a strict designer look (one accent, 4 px grid, 9-box budget, connector rules); the AI writes the SVG from templates; two Python checkers + a rendered picture check it | **Engine B — every other type** |
| DayuanJiang/next-ai-draw-io (75f0df3) | Apache-2.0 | The AI draws on a REAL draw.io editor canvas: she drags, renames, restyles by hand; selects shapes and asks "change only these"; AI changes are outlined, one Ctrl+Z undoes them; versions with thumbnails; AWS / Azure / GCP / K8s icons; draw.io editor self-hosted (v32.0.2, sha-pinned) | **Engine C — when she wants to edit it herself** |
| eraserlabs/eraser-diagrams (75db422) | MIT | JSON diagram + a look defined once (components, palette, fonts) + real browser measuring + an obstacle-aware line router; output = PNG + HTML + the measured JSON | **Two ideas, not a fourth engine** (§5) |

Why three engines and not four: every engine is code we must keep working on her server, update and test. Three cover
every need; Eraser's two best ideas fit inside them.

## 2. Which engine draws what (code decides, never a guess)

`diagram` picks the engine from the type and her words; the model may name one, code checks it fits.

| Her need | Engine | Why |
|---|---|---|
| Architecture, workflow / process, sequence, data flow, status / lifecycle, database tables (ERD), class, tree, timeline, time waterfall — and every diagram about CODE | **A archify** | code places boxes and lines = the same request gives the same clean layout; click to explore |
| Charts (bar, line, scatter, heatmap, treemap, sankey, waterfall money bridge, radar, polar), org chart, funnel / pyramid, quadrant, venn, user journey, service blueprint, fishbone, Wardley, kanban, story map, Gantt, swimlane, steps, loop, layers, exploded / axonometric, and the rest of the 52 | **B diagram-design** | archify has no such type; diagram-design's look and checks |
| "editable", "draw.io", "I will change it myself", or Edit on any A / B diagram | **C draw.io** | real hand editing |
| A question best answered as a page (a comparison, a diagnosis, a "how does X work") | **A explainer** | conclusion first, panels, charts, numbered sources |
| "What is wrong with this repo's structure", cycles, coupling, hotspots | **A Code Analysis** (Hoola Code) | reads the repo, never runs its code |
| "Show what this PR changed" | **A PR walkthrough** (Hoola Code) | marks the change on the diagram |

Before any engine: "would a table or a paragraph do?" — if yes, answer in words and draw nothing (diagram-design's
rule, kept for all three).

## 3. Taking the repos "as it is"

Each upstream folder is copied UNCHANGED into `server/app/diagram/vendor/<name>/`, pinned to the commit above, with
its LICENSE / NOTICE and a THIRD_PARTY_NOTICES line. **We never edit a vendored file**; every Hoola change lives in
Hoola's wrapper. `tools/diagram_sync.py <engine> <commit>` drops in a newer version on her word; the tests say whether
it still works.

| Vendored | Size | Left out |
|---|---|---|
| `archify/archify/` (renderers, schemas, references, examples, explainer, story, Code Analysis module, bin) | ~25 MB | website, docs, journal, benchmarks, experiments, sponsor material |
| `diagram-design/skills/diagram-design/` (SKILL.md, references, templates + examples, 9 scripts) | 6.4 MB | website, screenshots, plugin manifests, CI |
| next-ai-draw-io: the MCP-server source parts we port (XML checks, edit gate, selection, pages, diff, drawing guides, shape libraries) | ~1 MB | the Next.js web app, Electron, 25 model providers |
| draw.io editor (jgraph/drawio `draw.war` v32.0.2, Apache-2.0) | downloaded at setup, sha-256 checked, not in git | — |

Runtimes: archify and the draw.io parts are Node (>= 18) with no runtime packages (archify) or one small set
(draw.io parts); Hoola's server already runs Node (HyperFrames) and Chromium + Playwright (HOOLA PRINT). diagram-design's
scripts are plain Python. New vps-ops job `diagram_setup` fetches the draw.io editor and checks all three engines.

## 4. One tool, used everywhere

ONE agent tool **`diagram`**, the same for Hoola chat and Hoola Code:

| action | what it does |
|---|---|
| `types` | every type of the three engines, one line each, with the engine that draws it |
| `guide` | the chosen type's reference / schema / example (the model reads only what it needs) |
| `draw` | type + title + the description (A: JSON, B: HTML from the template, C: draw.io cells) → that engine's checks → rendered picture the model looks at → saved and shown |
| `update` | change the current version (A: JSON edits; B: old_str → new_str; C: id-based cell edits, only after re-reading the canvas) |
| `edit` | open an A or B diagram in the draw.io editor (C) so she can change it by hand |
| `selection` | (C) the shapes she has selected, so "change only these" works |
| `export` | PNG / SVG / PDF (all), .drawio (C), video (A story) |
| `import` | her Mermaid / draw.io / Excalidraw / PlantUML file → redrawn, with the list of what was merged or dropped |
| `explain` | (A) a one-page answer |
| `analyze` / `pr` | (A, Hoola Code) Code Analysis of the repo; a PR walkthrough |

Reachable: chat core tools, long jobs (goal rounds), team crews, a voice call via santosh_kaam (never declared to
Gemini Live; the diagram lands in the chat), and Hoola Code's coder tools. Opens on diagram asks in ANY language
(§7a): the model already understands "draw how X works" in every language it speaks, so the tool is offered to it by
meaning, not by a word list in one language; a short keyword list per supported language only helps the tool show
up sooner (diagram, flowchart, architecture, sequence, ER, org chart, timeline, Gantt, funnel, journey, and their
translations), and never decides alone.

**The flow, for every engine (her six steps):**
1. She asks — any time, also in the middle of a job or a coding round.
2. Code picks the engine for the type (§2); the model picks the type, or answers in words.
3. One-line plan in her chat ("Architecture diagram, 7 parts, leaving out the cache detail"), then it draws at once —
   she can redirect with her next message (owner decision 2 below).
4. The model writes only the DESCRIPTION; the engine does the drawing rules.
5. The engine's own checks run (A: four gates; B: self_check + verify_geometry; C: XML checks + repair). A failure goes
   back to the model with the exact errors, at most 3 rounds. Then one rendered picture is looked at by the model and
   fixed if wrong. Still failing = shown with the open problems named, never a quiet "done".
6. She sees it in the workspace (§6).

## 5. Eraser's two ideas, built into Hoola

1. **Her look, set once.** One `diagram_look` per user, from her existing Brand kit (colours, font, logo): paper / ink
   / muted / accent / link roles. Every engine reads it — A as its theme, B as its style-guide tokens (in the wrapper,
   not the vendored file), C as draw.io's default style. No brand kit = the engine's own default look (decision 1).
2. **Description in, measured result back.** Every saved diagram keeps the description AND the measured result
   (real box sizes, real line routes). An edit changes the description and redraws — never patches pixels; a diagram
   opened in draw.io (C) and saved by her comes back as her new version, and the AI reads it before its next change.
   If C's AI-drawn arrows turn out messy in D6, Eraser's line router (MIT) is ported for C — measured first, not assumed.

## 6. Where she sees it

| Surface | How | Built on |
|---|---|---|
| Console chat | opens in the workspace panel beside the chat; versions, Share, Download; A: click to explore; C: the live editor in the panel | an artifact page (versions, share, signed sandboxed link exist) + a new editor view for C |
| Phone chat | the card → full-screen viewer (pinch to zoom, A's click-to-explore works by touch); C on the phone = the picture + a "change it" box, full hand editing on the web console | `hoola_artifact.dart` / ArtifactScreen |
| Hoola Code web + phone | a "Made in this session" card that opens full screen; Code Analysis + PR walkthrough as their own cards | NEW kind `diagram` in `devsahayak/made.py`, `code_made.dart` |
| PDF reports, email, chat apps (WhatsApp, Slack, Teams, Telegram...), slides | the PNG / PDF export, sent through the channels she has connected | HOOLA PRINT's Chromium |

Hoola Code rule: a diagram about her code is drawn from the code Hoola has READ (archify's repository evidence links
each part to its file); it is not written into the repo unless she asks for it in the repo.

## 7. Safety, privacy, cost

- **The editor page (C) must share its origin with the draw.io copy** to highlight changes, read her selection and
  undo (the repo's own reason). So C runs on Hoola's separate sandboxed page origin (the one artifact pages use), never
  the console's — it cannot read her sign-in; it talks to the server only through a short-lived signed token for that
  one diagram.
- **Nothing phones home:** archify's daily update check is switched off (`ARCHIFY_UPDATE_CHECK_DISABLED=1`, its own
  documented switch); icons come from the vendored libraries, never Eraser's or anyone's online catalogue; fonts are
  Hoola's bundled ones (Google Fonts only as the viewer's fallback, as artifact pages already allow).
- **Model-written diagram text is data:** B's HTML and A's JSON are checked by the engines (no outside scripts); C's
  XML is checked and repaired before the canvas loads it; her imported files are data, never instructions.
- **Code Analysis never runs her repo's code** (archify's own rule) and runs only on a copy Hoola already holds.
- **Every language and script** — see §7a.
- **Cost:** A and C need fewer tokens than B (a description instead of a whole SVG). Every call is metered per user;
  the cost per diagram is MEASURED in D6 (in USD, shown to each user in her own currency), not guessed.

## 7a. Global from day one — every language, every script, every market

Hoola Diagram is built for users anywhere in the world, not one country:

- **The diagram speaks her language.** Labels, titles, notes, the one-line plan and every message around the diagram
  are in the language she writes in (or her chosen app language), for any language the model speaks. No language is
  the "default" one in code.
- **Every writing system renders.** The wrapper gives each engine one font stack covering the world's scripts: Latin,
  Cyrillic, Greek, Arabic, Hebrew, Devanagari and the other Indic scripts, Thai, Chinese (Simplified + Traditional),
  Japanese, Korean, Ethiopic and more (the Noto family, bundled on the server, so nothing is fetched at render time).
  Mixed scripts in one label work.
- **Right-to-left works.** Arabic, Hebrew, Persian and Urdu labels read right to left inside their boxes, and an RTL
  diagram can mirror its reading direction (left ← right) when she asks; numbers and code stay left to right.
- **Text fits in every script.** CJK, Arabic and Indic text has different widths than Latin; archify and Eraser-style
  measuring use the real rendered size, and diagram-design's Latin-based width check is backed by the rendered-picture
  check, so no label overflows in any language.
- **Dates, numbers and units follow her locale** (1,234.5 vs 1.234,5; 28/11 vs 11/28; her time zone), wherever an
  engine prints them (timelines, Gantt, waterfalls, charts).
- **Viewer and editor in her language.** archify's viewer already ships English, Chinese, Arabic, Spanish, Korean and
  Russian; draw.io's editor ships ~40 languages; Hoola's own buttons around them use the app's language. Missing
  languages are added as plain translation files in the wrapper, never by editing a vendored file.
- **Icons are global.** Cloud (AWS / Azure / Google Cloud / Kubernetes), tech and generic icons; no country-specific
  assumptions in the type router or the examples.
- **Money and limits are per user, in her currency.** Cost is measured in USD and shown in her own currency; quotas
  are per user, not per country.
- **Language test set (D5):** one diagram per engine with labels in English, Spanish, Arabic, Hebrew, Hindi, Chinese,
  Japanese, Korean, Russian, Thai and Amharic, plus one mixed-script label — each must pass the engine's checks and
  the picture check, and RTL must read right to left.

## 8. Phases

| Phase | What | Done when |
|---|---|---|
| D1 | Vendor the three engines (pinned, licences, sync script), `diagram_setup` (draw.io editor fetch + sha check); Hoola's runners for each engine's checks + render | archify's examples pass its four gates inside Hoola; diagram-design's checkers pass on its 238 examples; the draw.io editor loads; one PNG from each engine |
| D2 | The `diagram` tool in Hoola chat with engines A + B: the type router, draw / update / check loop, the picture look, saved as an artifact page → console workspace + phone viewer | fake-model tests: an architecture ask goes to A, a funnel to B; a failing check is fixed; the page opens in the panel |
| D3 | Engine C: the editor view in the workspace (her hand edits saved as versions, selection → "change only these", AI changes outlined, undo), `edit` from any A / B diagram, .drawio export | a browser walk: draw, she moves a box, the AI's next change keeps her move, Ctrl+Z undoes the AI |
| D4 | Hoola Code: `diagram` in the coder's tools + `diagram` made-kind cards (web + phone); A's Code Analysis and PR walkthrough as session cards; read-the-code-first rule | in a session "diagram of the login flow" gives a checked card linked to the files; Code Analysis runs on a fixture repo |
| D5 | Her look set once (§5.1), every language and script (§7a), export PNG / SVG / PDF (+ A's story video), diagrams inside PDF reports, email and her connected chat apps, A's one-page answers in chat, imports (Mermaid / draw.io / Excalidraw / PlantUML) incl. "redraw" on the Architecture and Data Engineering desks' Mermaid | the language test set (§7a) renders right in all three engines, Arabic / Hebrew right to left; an imported Mermaid file is redrawn with its merged / dropped list |
| D6 | Proof: 30 real asks (10 per engine, in at least 6 languages) through the real pipeline: first-try pass rate, rounds used, seconds and cost (USD) per diagram, which engine the router chose and whether right; decide on Eraser's router for C; deploy | numbers written here; deployed on her VPS |

Each phase = its own version (server + tests + phone where it changes). PC code is not touched.

Built so far: **D1** (v0.999.323), **D2** (v0.999.329), **D3** (v0.999.331), **D4** (v0.999.333). D3 as built:
the editor runs from Hoola's own server in a sandbox with no access to her sign-in; the link is signed for one diagram and
expires in 12 h; Hoola must `read` before `change` (a change on an older copy is refused); her editor gets Hoola's change id by
id as ONE undo step, outlined for 4 s; her own shapes, even unsaved, are never overwritten. The phone does not have the editor
yet (it still opens the picture page) - that rides D5 with the other phone work.

**D4** (v0.999.333) as built: Hoola Code has its own `diagram` tool (devsahayak/diagrams.py) on the same engines. A
diagram of her code names the files it is drawn from; each must be a file of the working copy READ in this session or the
draw is refused before any engine runs. archify's `sources` on each part are checked by archify itself (`--repo-root`)
against a snapshot commit of the working copy (made with a private index - her branch, HEAD and index never move) in a
throwaway evidence repo, so a cited line that is not in the file is sent back. Results are cards in "Made in this
session" (made.py kinds diagram / analysis / review), never in her chat and never written into the repo. Code Analysis =
archify's own static analyser on the working copy (ts / py / java; go / rust only where their toolchain is installed);
the PR walkthrough = the same analyser between where the session started and the working copy now. The server's own
folder paths are masked out of the report pages. Web: rail card + full-screen viewer with Edit by hand for an editable
diagram; phone: the cards, a Diagrams filter, "Drawn from" files.

## 9. Risks

- **Running the vendored programs.** In the session that read the repos, the sandbox refused to run archify's
  downloaded program; the build runs every engine's own checks in tests and on the server, so this needs to be allowed
  for the vendored folders (an `allow` rule for `node server/app/diagram/vendor/...` and `python3 -I .../scripts/...`).
- **Two Node engines + a 30 MB editor** add to deploy size and to what can break on update — pinned commits and the
  sync script's tests are the guard.
- **Some scripts are weaker in one engine** (for example a script none of its examples use); the language test set
  finds it in D5, and the fix lives in the wrapper's fonts or measuring, never in the vendored code.
- **Engine C on a phone** is cramped by nature; the phone gets the picture + "change it" box (§6).
- **The router's choice** can be wrong for a mixed ask; D6 measures it and the model can name an engine (code checks
  it fits).

## 10. Decisions for the owner

1. **Default look when she has no brand kit:** each engine's own default (archify's theme, diagram-design's black +
   tangerine, draw.io's default) — or one Hoola look for all three? (Plan assumes: one Hoola look for all three, so
   her diagrams match each other.)
2. **Step 3, the one-line plan:** say it and draw at once, or wait for her yes? (Plan assumes: say it and draw.)
3. **Updates from the authors:** stay pinned and update only on her word? (Plan assumes: yes.)
