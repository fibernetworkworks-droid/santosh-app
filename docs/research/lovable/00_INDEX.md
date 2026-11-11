# Lovable, read end to end (11 Nov 2026) - what it does, how, and why

Owner ask (11 Nov 2026): "DO DEEP RESEARCH ON DESIGN, LOGIC, STEPS, STRATEGY ETC USE BY LOVABLE ... EXTRACT ALL FEATURES
FROM DESIGN ANIMATION, GRAPHICS TO SMOOTH TRANSITION IN CHAT ... WE WANT SAME CLONE FOR HOOLA WEB DEVELOPMENT".

Four research passes ran in parallel (engine + tools, chat / preview design + motion, strategy + workflow, Hoola's own
Studio today). This file is the captured evidence. The plan built on it is `docs/LOVABLE_STUDIO_PLAN.md`.

How sure each line is:
- **[docs]** docs.lovable.dev pages (fetched as `.md`), the changelog, lovable.dev/blog - Lovable's own words.
- **[npm]** Lovable's published MIT packages, downloaded and READ (not run): `lovable-tagger` 1.0-1.3.5,
  `@lovable.dev/vite-tanstack-config` 2.27, `@lovable.dev/lovite`, `@lovable.dev/vite-plugin-hmr-gate`,
  `@lovable.dev/vite-plugin-dev-server-bridge`.
- **[CSS] / [i18n]** Lovable's live app bundles (globals / app-shared / app-lazy-shared CSS, the i18n string chunks) and the
  preview script `cdn.gpteng.co/lovable.js`, fetched 11 Nov 2026. Content-hashed - they rotate.
- **[leak]** the leaked agent prompt + tool list (github.com/x1xhlol/system-prompts-and-models-of-ai-tools, Lovable/,
  dated 2025-09-16). Not official, may be outdated.
- **[3rd]** reviews, teardowns, aggregators - directional only. **[inferred]** = reasoning, no source.
- The lovable.dev home page itself sits behind a Cloudflare challenge; it was NOT fetched (and not worked around).

---

## 1. The stack and the template

- Until 12 May 2026 every project was the `vite_react_shadcn_ts` template **[docs + a real synced repo]**: React 18,
  Vite 5, TypeScript, Tailwind 3 + tailwindcss-animate + typography, the whole shadcn/ui Radix set pre-installed,
  react-router 6, TanStack Query 5, react-hook-form + zod, lucide-react, sonner, recharts, date-fns, `@/` alias.
  `App.tsx` = QueryClient > Tooltip > Toaster > BrowserRouter with the comment "ADD ALL CUSTOM ROUTES ABOVE THE
  CATCH-ALL". `index.css` opens with "Definition of the design system. All colors, gradients, fonts, etc should be
  defined here. All colors MUST be HSL." `--radius: 0.5rem`, accordion keyframes 0.2 s ease-out.
- From 13 May 2026 (Enterprise 22 Jun) new projects are **TanStack Start, server-rendered, on Cloudflare Workers**
  **[docs]**: `createServerFn` server functions inside the app (were Supabase edge functions), SSR / SSG / CSR per
  route, static routes prerendered, Tailwind v4, secrets as Worker bindings (`VITE_*` public), migrations as Drizzle
  files (`drizzle/migrations/` + `_journal.json`), Vitest tests in `src/test`. A curated TanStack rule set is injected
  into every request on the new stack (stops Next.js habits). Old apps upgrade in place (10-35 credits).
- Why it matters: Lovable's quality lever is ONE opinionated template + "design system first". The model never
  chooses a stack.

## 2. How the agent edits (three generations)

1. **Late 2024** - one response, XML tags (`<lov-write>`), parsed after generation; small fine-tuned models picked the
   files a change depends on; hand-written "knowledge files" from broken-app logs ("only use icons that exist in
   lucide-react"); a "Lovable Stack Overflow" of known problem -> fix cut users getting stuck by 5% **[docs: Osika,
   "How we built Lovable", 4 Nov 2026]**.
2. **Aug 2025** - Agent mode, native tool calls, "errors down 91%" **[docs changelog]**.
3. **2026** - Build / Plan / Chat, subagents, `/goal` (up to 10 h), browser tests, self-written tests, drafts, memory,
   on an event-sourced "Trajectory" log **[docs: "Inside Chats", 24 Sep 2026]**.

**The tool list [leak, 2025-09]:**

| Tool | Job |
|---|---|
| `lov-view(file, lines?)` | read a file (500 lines default), never one already in context |
| `lov-search-files(query, include, exclude, case)` | regex search with globs |
| `lov-line-replace(file, search, first_line, last_line, replace)` | **the default edit**: search text checked against a 1-based line range; `...` skips the middle of a long block; parallel edits use ORIGINAL line numbers |
| `lov-write(file, content)` | new file / fallback; unchanged blocks > 5 lines written as `// ... keep existing code` (platform merges) |
| `lov-rename`, `lov-delete`, `lov-copy`, `lov-download-to-repo` | file ops (uploads -> `src/assets`, ES6 import) |
| `lov-add-dependency`, `lov-remove-dependency` | npm |
| `lov-read-console-logs`, `lov-read-network-requests` | the preview's logs AT the time of her message |
| `lov-fetch-website`, `websearch--web_search`, `document--parse_document` | context (page as md/html/screenshot; PDF/Office OCR) |
| `imagegen--generate_image / edit_image` | flux.schnell small, flux.dev hero; imported as modules |
| `secrets--add_secret` | a secure input box - "the only way to collect secrets" |
| `stripe--enable_stripe`, `analytics--read_project_analytics`, `security--run_security_scan / get_table_schema`, `supabase--docs-search / docs-get` | platform |

2026 additions **[docs, inferred as tools]**: browser testing (click, fill, screenshot, read console/network, sign in
as her), run tests, call an edge function, SQL migrations, read DB, spawn subagents (generic + "Explore"), connector
actions with approval, video, deep scan, run JS inside her open preview.

**System prompt rules [leak]:** discuss by default, code on action words ("implement, add, create") - except the FIRST
message ("likely wants code"); never re-read files in `useful-context`; parallel tool calls; minimal correct change, no
unasked features; small focused components, never one long file; debug tools first (console -> network -> code), never
ask a non-technical user for logs; reply < 2 lines; SEO on every page (title < 60, description <= 160, one H1, JSON-LD,
alt, lazy images, canonical); **design system first**: no `text-white` / `bg-white` in components, every colour /
gradient / shadow / transition a semantic HSL token in `index.css` + `tailwind.config.ts` (`--primary-glow`,
`--gradient-primary`, `--shadow-elegant`, `--transition-smooth`), shadcn customised through `cva` variants (`hero`,
`premium`); no dark-mode toggle unless asked. **First message "wow them":** what does it evoke -> v1 feature list (small)
-> colours / gradients / animations / fonts -> edit tokens FIRST -> component variants -> generate real images -> no
build errors -> update Index.

## 3. The agent runtime (2026) [docs: "Inside Chats"]

- Every conversation is an **append-only event log** (UserMessage, AgentStart/Done, IterationStart/End,
  ToolExecutionStart/End, ToolApprovalRequired...). One parent pointer per event, named heads like git branches.
  Revert = a Revert event; fork = a pointer (nothing copied). Bigtable + a content-addressed blob store; git holds code.
- The prompt is a **projection** built backward from the head at each iteration; compaction runs on a side branch and
  is admitted at an iteration boundary (the agent never pauses); streaming deltas are never persisted.
- **Inboxes**: a follow-up "mid-build" lands in the agent's inbox and is copied onto its log at the next iteration
  boundary. Runs suspend at a boundary and resume on any node (deploys, sandbox loss). ~0.5 B events / ~2.6 M user turns
  a weekday.
- Subagents are read-only, fresh context; routine lookups go to lighter models. An earlier async multi-agent design was
  REMOVED because agents "got stuck in technical rabbit holes".

## 4. The preview machine [docs + npm + podcast]

- 2025: an isolated Node container per project, 4,000+ on fly.io, persistent Vite + HMR. 2026: Kubernetes on GCP,
  **gVisor** sandboxes (memory can be reclaimed), one pod per session (5 min - 24 h), **warm pools**, a git-folder disk
  snapshot mounted on claim, pre-pulled image disk (skips 85-90% of image streaming); builds spike 15-16 cores then idle
  < 0.5 vCPU; ~1 M sandboxes / day.
- **OJ**, their own Rust dev server (Rolldown + Oxc, runs real Vite plugins through a bridge): time to a usable preview
  17.4 s -> 8.0 s median, sandbox claim 14.5 s -> 3.0 s, 6.5x less memory.
- **HMR gate** (`vite-plugin-hmr-gate`) [npm]: watcher events are HELD while the agent writes and released by
  `POST /__hmr_flush` (drain 1.5 s, fail-open after 240 s) - the preview never shows a half-written state. Boot /
  update progress events (`lovable:boot-progress` with module counts + first build error `{message, file, line}`)
  throttled to 500 ms; an update shows progress only past 10 modules or 1.5 s.
- **Error collector** [npm]: injected client listens to `window.error` + `unhandledrejection`, POSTs JSON (<= 64 KB)
  to `/__lovable/error-collector`, server appends JSON lines to `/tmp/runtime-errors.log` (the agent's log tool and
  "Try to fix" read it [inferred]). SSR / server-function error loggers separate build / server / app errors.
- **Run JS inside HER open preview**: `/_sandbox/preview/execute` (<= 50 KB, 1.5-5 s) over the HMR socket; `viewers`.
- **Click -> source** [npm]: `lovable-tagger` v1 added `data-lov-id="src/x.tsx:line:col"` to every JSX element; v1.1.12+
  wraps `jsxDEV` instead - each DOM node carries a hidden `Symbol.for("__jsxSource__")` {file, line, col, component} and
  `window.sourceElementMap` maps `file:line:col` -> WeakRefs of nodes (both directions), dev only, nothing in SSR HTML.
  It also writes the **resolved Tailwind theme** to `src/tailwind.config.lov.json` so the editor can apply token-based
  style edits optimistically with NO model call; on save, clean TSX from the AST with line-precise diffs, then HMR.
- Selection overlay [preview-js]: `1px solid rgb(37,99,235)` + 4% fill for selected, dotted for inline text, dashed for
  text mode, green dotted marquee for multi-select, crosshair cursor, a pill tooltip (white 600 12px on 93% blue). Bridge
  messages: ELEMENTS_SELECTED, ELEMENT_TEXT_UPDATED, DRAWING_UPDATED, HMR_UPDATE_APPLIED, RUNTIME_ERROR,
  BLANK_DOM_DETECTED, URL_CHANGED, APP_LCP / APP_INP.

## 5. Modes and features [docs]

- **Build** (was Agent): runs to the end, Details view (Timeline of every tool call + Changes diff), follow-ups picked
  up at the next stopping point, up to 10 h, usage-priced ("many requests < 1 credit"), credit check-in at 20 credits
  (Continue / Finish up), Stop keeps work done, "Undo latest edit".
- **Plan** (Feb 2026): investigates across steps (files, logs; subagents for big asks), asks questions, writes a plan
  (overview, decisions / assumptions, components / data models / APIs, ordered steps, optional diagrams) in a **Plan
  view** - editable, highlight a passage to comment (only that part is rewritten), versions ("2 of 3"). Plans are files:
  `.lovable/plan.md`, archived dated in `.lovable/plan/` on approval. **Approve** -> Build implements it; **Skip**. 1 credit.
- **Chat**: read-only (code, files, app data, other projects via `@`, connectors); never edits / migrates / publishes;
  a "Start building (uses credits)" card with Build / Skip; cheap, daily allowance. Alt/Option+P cycles modes; Plan is
  moving to a `/plan` command ("Send and plan").
- **`/goal`**: runs until the goal is met, asks only for access she alone can give.
- **Design guidance** (May 2026): when a visual ask leaves the look open, a question card asks <= 4 questions with VISUAL
  options - palette swatches, font pairs shown in their own fonts ("The quick brown fox jumps over"), 15 layout
  wireframes (hero grid, bento, zigzag, masonry, magazine, split, sidebar, dashboard...), one content question; first
  option preselected, Skip all; spacing / radius / animation intensity derived from the answers; skipped when the prompt
  already names a style or the ask is functional.
- **Preview toolbar** (Jun 2026, replaced Visual Edits): floating, docked bottom-centre, drag + snap to corners,
  minimise to an edge tab; single-key modes **S** select (Cmd-click multi-select, each becomes a chat reference),
  **T** inline text (100 free edits / 24 h / account), **D** draw annotation (shapes auto-cleaned, annotated screenshot
  sent with the message), **C** pinned comments. History: Visual Edits (Mar 2025) were deterministic, model-free, free;
  Nov 2025 added a margin / padding / border / shadow / colour panel; Apr 2026 they became AI-powered.
- **Instructions** (was Knowledge): workspace / project / personal, 10,000 chars each, always in context; **Skills**
  load on demand (`/`); **Memory** saved automatically (secrets stripped); technical decisions in `AGENTS.md`.
- **Code mode**: file tree, search, line pills (`Button.tsx:42`), every save a version, manual edits free.
- **History**: every change a version, bookmarks, Published badge, per-version diff, "Revert and resend" branches;
  **revert restores code, never database data**. **Drafts** (Sep 2026): branch copies with own chat + preview, accepted
  back; they share the real database and accepting never drops or renames.
- **"Try to fix"**: on build / runtime errors; 10 free fixes, each back 24 h after use; publish is blocked while the
  latest build fails.
- **Testing**: a small Vitest test added WITHOUT being asked when a rule changes (price, limit, permission, date) and
  run before "done"; never for copy / styling. **Browser testing**: a real browser, clicks, forms, screenshots, sizes,
  logged in as her; used selectively ("verify it works").
- **Imports**: Figma (plugin / MCP / `.fig`), a website from a URL (visible text, images, fonts, colours, spacing,
  desktop + phone; a screenshot kept to compare), a project ZIP <= 250 MB or exports from Bolt / v0 / Replit / Base44.
- **Publishing**: snapshot to `*.lovable.app`, custom domains (buy in-app), quick scan when the dialog opens, SSR for SEO
  (older apps get prerendering for verified crawlers: +2.9% organic, +98.5% AI-tool traffic).
- **Templates / remix / design systems**: remix = an independent copy (new keys, no data); a design-system project
  pushes components + a machine-readable schema into connected projects, with "Update available" and drift checks.

## 6. The backend ladder [docs]

1. Static UI with sample data. 2. Enable Cloud = database + auth + storage provisioned TOGETHER (Supabase underneath),
region fixed for good. 3. Tables from plain words -> migrations + generated types; form tables let visitors insert, not
read. 4. Auth: email + password and Google by default; phone, Apple, Microsoft, SAML / OIDC; redirect URLs kept updated on
publish. 5. Server code: server functions (new) / edge functions (old), secrets only through the secure prompt, `pg_cron`
jobs. 6. Payments: built-in Paddle / Stripe (managed keys, webhooks, test/live) or her own Stripe key. 7. Storage +
realtime under RLS. 8. AI features through the built-in gateway (`LOVABLE_API_KEY` per project, called from server code,
SSE, 429 / 402 told apart).

- **Migrations**: breaking changes (drop / rename / type change / required column without default) are REFUSED and done
  by adding a column and copying; "execute backward-incompatible migrations" defaults to **Never**; all pending
  migrations apply as ONE run (one failure = nothing applied); runs never overlap.
- **Agent permissions**, each Always / Ask / Never: enable Cloud, read DB, read analytics, run security checks, modify
  DB, breaking migrations, change data, configure auth, read logs.
- **Security**: quick scan (~10-15 s) on every publish (tables without RLS, permissive policies, leaked-password check off,
  critical reachable npm advisories, exposed MCP servers); deep scan = an LLM review of all code (2-4 min); auto-fix of
  low-risk findings; "block publishing with critical issues"; Wiz + Aikido partners; pasted API keys detected and moved
  to Secrets.
- **The incidents that shaped it**: CVE-2025-48757 (170 of 1,645 showcase apps / 303 endpoints with wrong or missing RLS;
  the scanner only checked a policy EXISTED); Apr 2026 broken object-level auth (5 API calls from a free account read
  other users' public-project code, chats and the DB credentials in that code; HackerOne sat on it 48 days). Lesson:
  RLS that exists but is wrong, client-only role checks, public-by-default sharing, one DB for preview and production.

## 7. Workflow and strategy [docs + 3rd]

- The sequence Lovable teaches: answer the basics (what / who / why / the one key action) -> **Plan mode** for anything
  bigger than a tweak ("ask me any questions you need") -> **v1 = one user, one action, one outcome** -> choose a design
  direction early and SAVE it to instructions -> **front end first, component by component, real copy** -> **sample data
  until the flows feel right** -> backend -> auth + roles -> **security scan when accounts are added and again before
  publish** -> payments (test mode) -> **test like a user** (empty states, bad input, refresh, second user, phone) -> publish.
- Scope: one change per prompt, verify, move on; a change prompt names what to build, where, and **what must stay
  untouched**; bookmark after every working feature; queue prompts.
- The debugging ladder: Try to fix once or twice -> describe precisely -> **switch to Plan for the root cause** ("what
  have we already tried?") -> review recent changes for a regression -> rebuild the component minimal -> revert ->
  remix to a clean copy; Plan-mode codebase / performance audits every few weeks. "Repeated blind fixes pile up code
  that hides the real problem."
- Cost examples [docs]: make a button grey 0.50 credit, remove footer 0.90, add auth 1.20, landing page with images
  1.7-2.0, Plan 1 / message. Pro $25 = 100 credits + 5 a day; no per-seat price.
- Scale [docs/3rd]: ~$500 M ARR (Jun 2026), $13.3 B valuation (Aug 2026), ~1 M new projects a week, 70 M+ built.
- Weaknesses reviewers repeat: credits burned in debugging loops (10-20 a session), fragility past the "70%", role
  security, one-branch git sync, Test/Live separation withdrawn for new projects (Mar 2026), Supabase + TanStack +
  Cloudflare lock-in.
- Rivals (Nov 2026): Bolt (WebContainers in the browser, Bolt Cloud), v0 (Next.js + shadcn, Vercel), Replit Agent (any
  language, real VM, DB rollback 28 days), Emergent (React + FastAPI + MongoDB, multi-agent, Expo for mobile), Base44 (Wix).

## 8. The interface, part by part [CSS + i18n + preview-js + docs]

Their design system is "Pulse": OKLCH tokens on one warm neutral hue (107), surface ladder `--bg-depth / base / primary /
secondary / tertiary / quaternary` (light stacks toward white, dark lifts lighter as it stacks), fg ladder primary /
secondary / tertiary / quaternary, semantic hues (accent blue 264, destructive, special purple, positive, attention,
highlight) each with bg / fg / border / glow / translucent; **0.5 px hairlines on retina**; buttons = stacked effect
layers (drop shadow, interaction fill 0 / .08 / .10-.12, top + bottom inset spotlights, dome gradient, rim) - shadows
hide on press, hover glow on instantly and fades out (0.15 s ease-out-cubic); type weight 480 (non-standard), display
3.75 rem / 700 / -0.05 em; easing tokens (Penner set, `--ease-overshoot`, a `linear()` spring for sheets), default 0.15 s.

- **Home**: a static soft-glow raster behind the hero (blurred 12 px, not an animated gradient, no grain); time-of-day
  style greetings ("What should we build?", "Got an idea?"); placeholder typewriter "Ask Lovable to create " + rotating
  ends ("a landing page for my...", "a dashboard to..."); composer with `+` (import, attach, design, connectors,
  databases), mic dictation (Alt+V), mode picker with one-line descriptions, send turns into a spinner at once; quick
  chips (Website, Dashboard, Internal tool, Store, Portal...); a floating prompt bar while scrolling; pasted secrets
  blocked with a toast.
- **Home -> editor**: a route change; her prompt becomes the first message; the PREVIEW pane shows a first-build screen
  "Setting the stage" with rotating plain status lines ("Writing the first version.", "Laying out your pages.", "Wiring up
  the backend.", "Polishing the details.", "First builds take a moment."); design questions may come first; optional
  sound on completion.
- **Editor**: chat left / preview right, resizable divider ("Drag to resize, click to collapse"), Cmd+B hides chat; top
  bar = project name doubling as draft switcher, History, tabs Preview | Files | Code | More (Database, Users, Storage,
  AI, Payments, Emails, Connectors, Security, Usage...), device toggle, page path box, refresh (Shift = restart), open in
  tab, comments badge, collaborator avatars, Share, Publish (dialog with deploy progress -> live URL + next steps).
- **Chat**: Tiptap composer "Ask Lovable..." / "Queue follow-up..." / "Tell Lovable what to do instead..."; `@` mentions
  as animated pills (enter = blur 4 px + scale .96 -> 1, 0.15 s); long pastes become typed attachment chips (Code / CSV /
  JSON / Logs / SQL) with stats; up to 10 files, image zoom + draw. **Streaming = per-character spans fading in over
  0.3 s ease-out-quad with a stagger**; list bullets / code / tables appear with their first character; instant under
  reduced motion. **"Thinking..." = a shimmer band sweeping across the text, 1.8 s linear, 70% band**, "Thought" when done.
  **Tool rows** present -> past verbs (Reading -> Read, Editing -> Edited, Ran command, Read preview logs, Generated image,
  Queried database, Configured auth) in **condensed groups**, "Used N tools", a **Details** view where the preview sits
  (Timeline + Changes, Input / Output per call); run states (Working..., Done, Stopped, Build unsuccessful + Rerun build,
  Preview is out of date); footer **"Worked for 42s · credits used"**; task list checkboxes draw their tick (0.15 s);
  error cards (Build / Runtime / CORS / edge function) with **Try to fix** (mod+Enter), Show logs, "Fix build (free)";
  suggestion chips; question cards (<= 4, Recommended badge, Something else, Skip all); plan card (Open plan, Approve /
  Skip); follow-ups sent mid-run sit greyed until picked up ("Send now" / "Interrupt"); Undo latest edit / Revert to this
  version / Bookmark on replies; **a new user message scrolls to the top of the viewport** (not stuck to the stream);
  jump-to-message flash (muted wash fading 1.6 s after 0.8 s); credit check-in and out-of-credits cards.
- **Preview**: boot lines ("Preparing your preview...", "Starting the dev server...", "Compiling your app... (n modules)",
  "Taking longer than usual..."), update states ("Applying changes...", "Preview is out of date"), "Still building? / Keep
  building" after idle, error overlay "The app encountered an error" + Try to fix + Show logs, device frames (phone corner
  radius 32 px), the floating toolbar (S / T / D / C), drawing with auto-cleaned shapes and marching-ants selection.
- **Motion inventory**: shimmer 1 s, sheen 4 s, loader sweep 2 s, status-dot ping 1.4 s x3, caret blink 1 s, collapsible
  height 0.2 s + opacity 0.12 s, gradient text "develop-in", a conic "shine" ring for live surfaces, heartbeat on the logo;
  every animation has a reduced-motion and forced-colours fallback; focus = 2 px accent outline, offset 2 px.

**Brand line we keep**: their identity (the heart-shaped glow image, the 22-stop blue -> pink -> orange spectrum, the
commercial Camera Plain typeface, the "Pulse" name, "Ask Lovable", their copy) is NOT copied. The patterns (token
ladders, layered buttons, shimmer thinking text, per-character fade, present -> past tool verbs, HMR gate, source-tagged
runtime, selection overlay, first-build narrative, floating toolbar) are generic techniques and are rebuilt in Hoola's
own identity (v0.716 mark, Hoola tokens, Literata / Schibsted, Hoola words).

## 9. Hoola Web Studio today (mapped 11 Nov 2026, read-only)

- `/console/web` (`static/console/webstudio.*`, ~2,000 lines): home with aura, Build | Plan, templates (1,00,000
  generated prompts), plans waiting, sites grid; plan document + revise chat; workspace with per-site chat, Preview /
  Code / Cloud / Integrations / Health / Settings / History / Publish; three looks; live build canvas over SSE slots
  (`site/stream.py` + `hoola-build.js`); visual edit (text / link / image / media / remove, no AI, undo 50); publish with
  DNS cards + launch hash + her tap.
- Engine: architect plan on Opus -> design kit -> sections written in parallel as `{html, css, js}` JSON -> sanitised ->
  assembled static pages (`site/build.py`) -> Chromium checks at 4 widths (console errors included) -> up to 3 whole-section
  fix rounds -> screenshot critique -> visitor journeys -> nine gates -> version (20 kept). Backend = `site/webapp.py`
  lists + rules + members, `applink` to App Sahayak's DIMAAG logic engine, shop / pay / GST / CMS / blog / languages.
- **Gaps against Lovable**:
  1. no real component codebase (React export = `dangerouslySetInnerHTML` wrapper, nothing comes back);
  2. every change rewrites WHOLE sections and re-runs the whole pipeline (slow, costly for "make the button grey");
  3. `data-k` / `data-e` exist in the edit preview but the selected element never reaches the model;
  4. no live-preview error loop (console errors only at build time; no Try to fix);
  5. visual edit is content-only (no style / spacing / token panel, though `/theme` exists);
  6. looks share body sections; 7. restore only after a site is live, no revert of an AI change, no drafts;
  8. Studio chat POLLS every 1.5 s (no token streaming), the pending steps are client-timed labels, no attachments,
     Plan in chat is a hint not a card, several buttons send canned Hinglish;
  9. live slots in process memory; 10. Cloud tab read-only (no schema / row editor, no storage browser);
  11. GitHub one-way; 12. no secrets / third-party API calls from a site; 13. one model writes everything;
  14. no collaborators / remix; 15. templates are prompts, not starter projects with previews.
