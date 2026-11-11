# HOOLA WEB STUDIO 2 - the Lovable-grade builder, end to end (plan, 11 Nov 2026)

Owner ask: "DO DEEP RESEARCH ON DESIGN, LOGIC, STEPS, STRATEGY ETC USE BY LOVABLE FOR DEVELOPMENT OF ANY WEB APP /
WEBSITE FROM LOW TO COMPLEX. ALSO EXTRACT ALL FEATURES FROM DESIGN ANIMATION, GRAPHICS TO SMOOTH TRANSITION IN CHAT
... WE WANT SAME CLONE FOR HOOLA WEB DEVELOPMENT ... DEVELOP A PLAN FOR HOOLA WEB DEVELOPMENT STUDIO END TO END".

Evidence: `docs/research/lovable/00_INDEX.md` (read it first - every claim below that is about Lovable is sourced
there). Nothing is built by this document. Each phase below is one shippable version with its own tests.

---

## 0. The verdict in five lines

1. Lovable's quality does not come from the model. It comes from **one fixed, opinionated codebase template + "design
   system first" + small line-level edits + a preview that reports its own errors + plan-before-build**. All five are
   copyable as techniques; none needs their code.
2. Hoola's Studio is already strong where Lovable is weak (plan quality on Opus, three looks, safety gates, Indian
   commerce / GST / OTP / UPI, her-tap publishing, visitor journeys, ops after launch). It is weak exactly where
   Lovable is strong: **it writes static HTML sections, rewrites a whole section for every change, cannot hear its own
   preview's errors, and its chat polls instead of streaming**.
3. So the plan is NOT "throw the Studio away". It is **two engines behind one Studio**: the existing Site Engine
   (static, fast, cheap - brochures, shops, catalogues, 100-page sites) upgraded with Lovable's edit / preview / chat
   machinery, and a NEW App Engine (a real React + TypeScript project in a sandbox, Lovable's way) for web apps.
   The architect's plan picks the engine; she can override.
4. The chat and preview get Lovable's interaction design (streaming, thinking shimmer, tool verbs, details timeline,
   question cards, plan card, Try to fix, preview toolbar) in **Hoola's own identity** - never their heart glow,
   spectrum, Camera Plain font or words.
5. Their published failures are written in as walls from day one: RLS / rules that exist but are wrong, client-only
   role checks, public-by-default sharing, one database for preview and live, credit burn in fix loops.

## 1. What we copy, what we do better, what we refuse

| Lovable does | Hoola does |
|---|---|
| One template (React + Vite / TanStack Start + Tailwind + shadcn) | Site Engine stays; App Engine = ONE template (section 5) - the model never picks a stack |
| Design system first (tokens file before any page) | Already have `site/kit.py` + taxonomy tokens; make it a hard rule in BOTH engines + a drift check |
| `line-replace` edits, `keep existing code` merges | `edit_lines` / `search_replace` tools on section files and code files; whole rewrite only as fallback |
| HMR gate (hold while writing, flush once) | Same idea: the preview version only advances when a change set is complete |
| Error collector -> log -> agent + Try to fix | Same: preview errors reach the chat; free fixes per day; ladder to root cause |
| Click -> source (`__jsxSource__` map) | Site Engine: `data-k` / `data-e` already exist - wire them to the model; App Engine: our own jsxDEV wrapper |
| Build / Plan / Chat modes | Already Build / Plan; add read-only Chat; plan becomes a file + card + editable view |
| Design guidance question cards | Add - with visual swatches, font pairs, layout wireframes from our own taxonomy |
| Instructions (3 levels) + AGENTS.md + memory | Per-site instructions + decisions file; reuse Hoola memory (yaad) for preferences |
| Version every change, revert code not data, drafts | Version every change (we do), restore BEFORE launch too, drafts on the Site Engine first |
| Quick scan on publish, deep scan on demand | We already have nine gates that BLOCK launch - keep; add deep scan for App Engine code |
| Credits | Rupees: every turn shows "Worked for 42 s · Rs 3.10"; a check-in at her own limit |
| Supabase as backend | **Refused**: our own backend (applink / DIMAAG / site-app) - her data on her server, Indian OTP / UPI / GST built in |
| Cloudflare Workers runtime | **Refused for now**: static hosting + Hoola's own API on her VPS (one box, no new vendor); revisit with SSR need |
| `/goal` 10-hour runs | Later; our long-job machinery (kaam_plan, crews) already exists |
| Their brand (glow image, spectrum, font, "Ask Lovable") | **Refused**: Hoola identity only |

**Where Hoola must beat them** (said to her as the reason this is worth building): plan on Opus with code-sized depth
(v0.709), three full looks before build, launch gates that block, Indian business stack (GST invoices, UPI, OTP via DLT,
Shiprocket, MSG91), her-tap money and publishing, ops after launch (errors, speed, restore test), rupee-honest costs.

## 2. The two engines and who picks

- **Site Engine** (exists): plan -> kit -> sections `{html, css, js}` -> static pages + `hoola-site.js` / `hoola-app.js`.
  Right for: landing, portfolio, business site, blog, shop, catalogue up to thousands of pages, booking, simple member
  areas. Cheap to host, fast, SEO-perfect, already gated.
- **App Engine** (new, phase L8+): a real project (section 5). Right for: dashboards, multi-role portals, SaaS, admin
  tools, anything with custom client logic the section sanitiser refuses today.
- **Who picks**: the architect's plan already sizes simple / standard / complex and names `main_screen` (v0.715).
  Rule in code: complex + any app screen beyond the 9 screen types, or custom client logic -> App Engine; everything
  else Site Engine. The plan card states the engine and why; her "use the other one" is honoured.
- One Studio, one chat, one history, one publish flow for both. She never sees two products.

## 3. The Studio experience, screen by screen (target)

### 3.1 Home
- Greeting by time of day + her name (rotating set, Hoola words). Composer centred over Hoola's own aura (v0.669 -
  keep; no raster glow). Placeholder typewriter: "Ask Hoola to build " + rotating ends ("a website for my clinic...",
  "a dashboard to track...", "an online store that..."), ~45 ms a character, 1.6 s pause, off under reduced motion.
- Composer: `+` menu (attach / screenshot / old site / Figma / product sheet), mic (Kaan dictation, v0.751), mode
  picker **Build / Plan / Chat** with one-line descriptions, Alt+P cycles, `/plan` command pill, send turns into a
  spinner the moment she presses it.
- Chips: Website, Online store, Dashboard, Booking site, Portal, Landing page, Blog, Internal tool.
- Templates become **real starter projects with a live thumbnail** (start with 24 hand-checked ones built by the
  engine itself; the 1,00,000 generated prompts stay as "ideas").
- A pasted secret is blocked with a toast and pointed to the secure box (existing rule, now on this composer).

### 3.2 Home -> workspace transition
- Her prompt becomes the first message in the chat column, the composer re-docks at the bottom (one 240 ms move),
  the right pane shows **"Setting the stage"** - a calm first-build narrative of REAL server steps (v0.656 activity
  steps, never client-timed labels - kills gap D8): "Reading your idea." "Planning the pages." "Choosing colours and
  fonts." "Writing the first version." "Checking it on a phone." "First builds take a minute or two."
- If the look is open, the **design question card** comes first (3.4).

### 3.3 Workspace layout
- Chat left / preview right, draggable divider (keep), Ctrl+B hides chat, mobile = swipe between the two.
- Top bar: site name (doubles as draft switcher later), status pill, History, Share, Publish.
- Right tabs: Preview | Code | Data | More (Integrations, Health, Settings, Security, Usage). Device toggle, page path
  box, refresh (Shift = full rebuild), open in new tab.

### 3.4 Chat - every element, with the motion spec
| Element | Spec |
|---|---|
| Streaming | real SSE token stream (replace 1.5 s polling); each new word fades in over 300 ms ease-out-quad, staggered; lists / code / tables appear with their first character; instant under reduced motion |
| Thinking | "Thinking..." with a shimmer band sweeping the text (1.8 s linear, 70% band, Hoola violet over ink); "Thought for 12 s" folded after |
| Tool rows | present -> past verbs, Hoola words: Reading page -> Read page; Planning -> Planned; Writing Home hero -> Wrote Home hero; Checking on phone -> Checked on phone; Fixing contrast -> Fixed contrast; grouped "Used 6 steps", tap opens the Details view |
| Details view | opens where the preview sits: Timeline (every step with server start / end) + Changes (per-file diff); "Back to preview" |
| Run footer | "Worked for 42 s · Rs 3.10" (rupees from the real usage meter), version chip "Version 7", Undo this change, Bookmark |
| Plan card | Open plan / Approve / Skip; Plan view = editable document, highlight a passage to comment, versions "2 of 3" |
| Chat-mode card | "Start building (uses money)" with Build / Skip |
| Question card | up to 4 questions, visual options (palette swatches, font pairs shown in their own fonts, layout wireframes drawn from `taxonomy`), first option preselected, Something else, Skip all |
| Error card | Build problem / Page error / Data error + **Try to fix** (Ctrl+Enter), Show details; "free fix" count when free |
| Suggestions | 2-4 next-step chips under a finished reply (from the plan's remaining steps, never invented) |
| Follow-ups | a message sent while working shows greyed "Runs after this step" with Send now / Interrupt |
| Scroll | a new message of hers scrolls to the TOP of the view (not glued to the stream); jump-to-message flash 1.6 s |
| Attachments | up to 10 files, image zoom + draw; long paste becomes a typed chip (Code / CSV / JSON / Logs) |
| Element pills | selected elements appear as pills in the composer ("Home · Hero · button 'Book now'") and ride to the model |
| Money check-in | at her own per-turn limit: Continue / Wrap up |

### 3.5 Preview
- Boot lines from the real build ("Preparing preview...", "Assembling 6 pages...", "Taking longer than usual...").
- Update states: "Applying changes...", "Preview is out of date" (when a version is newer than what she sees).
- The preview only advances when a change set is COMPLETE (the HMR-gate idea) - never a half-written page; the live
  build canvas (v0.664) stays for the first build and big rebuilds.
- Error overlay inside the frame: "This page hit a problem" + Try to fix + Show details.
- **Preview toolbar** (floating, bottom-centre, drag + snap, minimise): **S** select (Ctrl-click multi), **T** inline
  text (free, no model), **D** draw (shapes cleaned, annotated screenshot sent), **C** comment (pinned, for her team).
- **Style panel** (free, no model, Site Engine first): for a selected element - text, colour (from the site's tokens
  only), spacing, radius, font size step, alignment, image replace; writes through the same version path as visual
  edit; a raw colour outside the tokens is refused (design-system rule).
- Selection look: 1 px Hoola violet outline + 4% fill, dotted for text editing, a small pill tooltip with the element's
  name; crosshair in select mode.

## 4. Site Engine upgrades (what changes under the hood)

- **E1 Line edits**: new agent tools over the section store - `site_view(section)`, `site_search(query)`,
  `site_edit(section, search, replace)` (exact match, must be unique, sanitiser re-run on the result), `site_write`
  (whole section, fallback). A change that touches one string no longer re-asks Opus for the whole section.
- **E2 Tiered checks**: a small change runs the quick checks only on the touched pages (horizontal scroll, contrast,
  console errors, links on that page) in seconds; the full Chromium matrix + critique + journeys + gates run before
  publish and on big changes. Measured target: "make the button grey" under 20 s and under Rs 1 (today: a full section
  rewrite + full pipeline).
- **E3 Element -> model**: the selected `data-k` / `data-e` plus the element's HTML snippet + page + a screenshot crop
  go into the turn as `<selected_elements>` (fixes gap D3). "Change with AI" stops pasting quoted text.
- **E4 Preview errors**: `hoola-site.js` in preview mode posts `error` / `unhandledrejection` / failed fetches to
  `POST /api/sites/{id}/preview-errors` (64 KB cap, masked); the agent gets a `site_logs` tool; the chat shows the error
  card. Visitor errors after launch already flow (`site/ops.py`) - same card.
- **E5 Versions before launch**: every change already makes a version; add Restore for ANY version (not only live),
  Bookmark, "Undo this change" on each reply, per-version diff, "Revert and resend" from an edited message.
- **E6 Drafts**: a draft = a named branch of the section store with its own preview token; Accept merges by section
  (conflicts named, never silent); shared data, as Lovable does - and said plainly.
- **E7 Live slots durable**: `site/stream.py` slots move from process memory to a small on-disk ring (or the DB) so a
  restart or a second worker does not lose the live view (gap D9).
- **E8 Looks with their own bodies**: allow a look to differ in body sections for small sites (<= 12 sections), keep
  the shared-body rule above it (cost).

## 5. The App Engine (new) - the Lovable-grade lane

### 5.1 The one template
- React 18 + TypeScript + Vite + Tailwind v4 + a Hoola component kit (shadcn-style, MIT Radix primitives, our own
  tokens and names) + React Router + TanStack Query + react-hook-form + zod + lucide + sonner + recharts + date-fns.
- `src/styles/tokens.css` = THE design system (Hoola semantic tokens: surfaces, ink ladder, accent, states, radius,
  shadows, motion) generated from the plan's look; components customised only through `cva` variants; a drift check
  refuses raw colours / one-off values in components (the "design system first" law, enforced in code).
- `src/lib/hoola.ts` = the typed client for Hoola Cloud (5.4) - the ONLY way the app reaches data, auth, files,
  payments, AI. No other backend, no keys in the client.
- `AGENTS.md` at the root (technical decisions as one-line rules with reasons) + `.hoola/plan/` (approved plans, dated).
- Pinned, vendored dependency set (no `@latest`); `add_dependency` only from an allow-list grown by her tap
  (the v0.497 prog-library-registry law: never a guessed package name).

### 5.2 Where it runs (the infrastructure decision)
- Build and preview run in the **devlab Docker box** (v0.456 / v0.535 walls: uid 1000, cap-drop ALL, memory / cpu /
  pids caps, no secrets inside) with the network limited to the npm registry mirror during install only and OFF while
  the dev server runs.
- One container per ACTIVE editing session, warm pool of 1, idle-reaped after 10 min, hard cap of live previews per
  server (start at 2 on her VPS; the queue says "Your preview starts in about a minute").
- Dev server = Vite (Lovable moved to their own Rust server for speed; Vite first, measure, then decide).
- Preview served through Hoola's preview token proxy (as today), sandboxed iframe, same CSP family.
- **Published app = static build** (`vite build`) served by `hosting.serve` + Hoola Cloud API. No SSR in v1; crawlers
  get prerendered HTML of public routes (headless render at publish) for SEO.

### 5.3 The agent's tool set (App Engine)
`app_view`, `app_search`, `app_edit_lines` (search text verified against a line range, `...` to skip a long middle,
parallel edits on original line numbers), `app_write` (new file / fallback), `app_rename`, `app_delete`,
`app_add_dependency` (allow-list), `app_logs` (preview runtime + build errors from the collector), `app_network`,
`app_test` (Vitest), `app_browser_check` (our Playwright journey runner on the preview), `site_fetch` (her old site /
a reference page, existing scrape lane), `image_make` (photogen / Pexels, existing), `secret_ask` (opens the secure box
card - the ONLY way a key enters), `cloud_schema` / `cloud_migrate` (5.4). Every tool runs through `_run_tool`
(harness, ledger, masking) like every other Hoola tool.

### 5.4 Hoola Cloud (backend for App Engine apps)
- Built on what exists: `site/webapp.py` collections + rules, `applink` -> App Sahayak backend + DIMAAG logic engine,
  `site/security.py` OTP / TOTP / sessions, shop / pay / GST, uploads, live SSE.
- Exposed to the app as `hoola.ts`: `auth` (email + password, phone OTP via DLT, Google later), `db.collection(x)` typed
  CRUD, `files`, `fn(name)` (locked server functions = DIMAAG functions), `live`, `pay` (her gateway, paid only on the
  signed webhook), `ai` (Hoola's own models through a server function, metered, never a key in the client).
- **Rules are enforced on the server for every call** (the RLS lesson): a rule that lets everyone read is flagged at
  plan time, client-side role checks are never trusted, roles live in the backend's own member table (never a field
  the user can edit).
- **Migrations**: schema changes are additive only (add field / list, hide, label); drop / rename / type change are
  refused and done as add-copy-hide, unless she taps an explicit "I accept data loss" card; all pending changes apply
  as ONE run; code revert never touches data, and the revert card says so.
- **Preview data vs live data**: a separate preview dataset from day one (seeded sample rows, marked `data-sample` as
  v0.715 does); publish never copies preview rows to live. This is the wall Lovable removed in Mar 2026 - we keep it.

### 5.5 Click -> source and free style edits (App Engine)
- Our own Vite plugin in dev only: wraps `jsxDEV` so each host element carries a hidden source record
  {file, line, col, component}, and keeps a `file:line:col -> nodes` map for the reverse direction; nothing in the
  production build.
- Resolved theme JSON (`.hoola/theme.json`) written on every tokens change so the style panel can preview a change
  instantly and then write a precise line edit (a className or a token) - no model call, no money.

### 5.6 Proof the work is done
- A small Vitest test is added whenever a RULE changes (price, limit, permission, date) and run before "done"; never
  for copy or styling.
- The browser check (Playwright, existing `site/journeys.py` runner) walks sign-in, the main screen, one create /
  edit / delete, at phone and desktop sizes, before "done" on any data change.
- Nothing is called done that a check did not prove (house rule since v0.443).

## 6. Modes, plans and standing instructions (both engines)

- **Build** (default after the first message): does the work, shows the Details timeline, honours follow-ups at the
  next step boundary, money check-in at her limit, Stop keeps finished work.
- **Plan**: investigates (reads the site / code, logs, data), asks up to 4 questions, writes `plan.md` (overview,
  decisions + assumptions, pages / screens, data, rules, integrations, ordered steps, risks, the engine and why);
  editable Plan view; Approve -> Build implements it step by step; Skip. Reuses the v0.709 architect for new projects.
- **Chat**: read-only and cheap (small model), reads the project + its data, never changes anything; "Start building"
  card when code is needed.
- **First message rule**: a first message means build (no discussion) unless it is unclear - then ONE question
  (v0.371 / v0.734 rule).
- **Standing instructions per site**: her brief (product, users, journeys, roles, design direction, terms), 10k chars,
  drafted by Hoola from what is built, always in context; decisions in `AGENTS.md`; her preferences in Hoola memory.

## 7. The build sequence Hoola follows (taught to the model AND enforced by the plan)

1. Basics: what, who, why, the one key action (architect asks if missing).
2. Plan for anything bigger than a tweak.
3. v1 = one user, one action, one outcome.
4. Design direction chosen early (question card or her words) and saved to instructions.
5. Front end first, section by section / screen by screen, real copy, sample data marked as sample.
6. Data and rules only when the screens feel right.
7. Accounts + roles -> **security check** (gates on the Site Engine; quick scan + rule audit on the App Engine).
8. Payments (her gateway, test mode first).
9. Test like a visitor: empty states, bad input, refresh, second account, phone.
10. Publish (her tap, gates must pass) -> health + ops.

Scope rules in the system prompt: one change per message; say what changes, where, and what must stay untouched;
bookmark after each working feature.

## 8. Debugging ladder (built into the product, not just advice)

1. Error card -> **Try to fix** (5 free a day per site, then normal price; "free" said on the button).
2. Two failed fixes on the same error -> the next press switches to **Plan for root cause** automatically ("What
   have we already tried?" is in the prompt with the ledger of attempts) - never a third blind patch.
3. Regression check: review the last changes to the broken area before changing more.
4. Rebuild the one broken section / component minimal, then reintegrate.
5. Restore a working version (one tap, code only, data untouched - said).
6. Copy the project clean (remix) as the last resort.
The ledger of attempts is kept per error fingerprint so the model sees what failed before.

## 9. Security and money walls (non-negotiable, from their incidents)

- Every data rule enforced server-side; a permissive rule is a FAIL at plan time and at publish.
- Roles never in a user-editable record; admin checks never only in the client.
- Projects private by default; sharing a preview link is her tap; a public template copy never carries data,
  secrets or chat.
- Keys only through the secure box card; a pasted key in chat is blocked and she is told to rotate it.
- Publish blocked on any FAIL (nine gates + App Engine quick scan: rules, dependency advisories that are reachable,
  exposed secrets, open endpoints); deep scan (LLM review) on demand before a big launch.
- Money: every turn priced in rupees from the real meter; a per-turn and per-day limit she sets; no silent loops -
  the fix ladder caps blind retries at 2.

## 10. Phases (each = one version, tests + a measured card)

| # | Name | What ships | Proof |
|---|---|---|---|
| L0 | STUDIO NAAP | the Studio card: 30 asks low -> complex (10 brochure, 8 shop / booking, 8 portal / dashboard, 4 SaaS), scored in code (built, time, rupees, preview errors, gates, design checks, the 3 small-edit asks timed) + the baseline on today's Studio | card numbers in HISTORY |
| L1 | CHAT JAISA | SSE token streaming in the Studio chat, word fade, thinking shimmer, tool verbs, grouped steps, Details view (Timeline + Changes), run footer with rupees, scroll-to-top, follow-up queue, attachments + paste chips | browser walk, reduced-motion check |
| L2 | TEEN MODE | Build / Plan / Chat with Alt+P + `/plan`, plan as a file + Plan view (edit, comment, versions, Approve / Skip), Chat read-only on a small model + Start building card, per-site instructions | plan card test, chat never writes (test) |
| L3 | SAWAAL CARD | design question cards with visual options (palettes, font pairs, layout wireframes from taxonomy), skipped when her words name a style | card test |
| L4 | CHHOTA BADLAAV | E1 line-edit tools + E2 tiered checks | "make the button grey" < 20 s, < Rs 1 on the card |
| L5 | YEH WALA | preview toolbar (S / T / D / C), E3 element pills to the model, annotated screenshots, free style panel on tokens | browser walk; style edit costs Rs 0 |
| L6 | GALTI PAKDO | E4 preview error collector + error cards + Try to fix + the debugging ladder with the attempts ledger | planted-error test fixed in <= 2 tries |
| L7 | WAPAS | E5 restore any version, bookmarks, undo per reply, diffs, revert and resend; E7 durable live slots | restart test keeps the live view |
| L8 | APP ENGINE 1 | template + tokens + drift check, devlab container dev server, preview proxy, the tool set, build + static publish | 5 card asks built in the box |
| L9 | APP ENGINE 2 | click -> source plugin, theme JSON, free style edits, error collector in the template, HMR-gate equivalent | half-write never shown (test) |
| L10 | HOOLA CLOUD | `hoola.ts` over the existing backend, server-enforced rules, additive migrations, preview vs live data | rule audit + migration refusal tests |
| L11 | SABOOT | auto tests on rule changes + browser check before done (App Engine); quick scan + deep scan; publish block | planted bad-rule app refused at publish |
| L12 | GHAR + SHURUAAT | home redesign (greeting, typewriter, chips, real starter projects with thumbnails), the home -> workspace transition, "Setting the stage" with real steps | browser walk |
| L13 | DRAFT | E6 drafts on the Site Engine, then App Engine branches | conflict-named merge test |
| L14 | GITHUB DO TARAF | two-way sync for App Engine projects (one branch), import from ZIP / another builder's export | round-trip test |
| L15 | PROOF | the L0 card again + 3 proof apps (a clinic site, a coaching portal with roles + payments, a dispatch dashboard), owner walks them | numbers before vs after |

Order logic: L1-L7 improve the Studio she already uses, every week, with no new infrastructure; L8-L11 are the big
build and only start after L0 numbers say where the Site Engine stops; L12-L15 finish and prove.

## 11. Decisions only the owner can make (asked before L8)

1. **App Engine infrastructure**: run dev-server sandboxes on the current VPS (cap 2 live previews, slower, no new
   cost) or a separate build server (more previews at once, a monthly bill). Recommendation: start on the VPS with
   the cap, move when the queue shows real waits.
2. **Model per job**: plan + first build on Opus (today), small edits + Chat mode on a cheaper model (GLM / Haiku),
   fixes on the plan model. Recommendation as written; her call on the rupee ceiling per turn.
3. **Free allowances**: free fixes per day and free style / text edits - the numbers she wants to give users.
4. **Brand**: Hoola identity everywhere (recommended and assumed); no Lovable brand elements.

**At L8 (v0.824, owner "GO L8") these four were not answered, so the recommendations above were taken and are
switchable:** previews on her VPS in Docker, at most 2 builds at once (`app_engine_previews`); no extra model call (the
Studio turn's model writes through `app_engine`); no free allowance built or promised; "Hoola App Engine" as the name.
L8 measured the box here: ~6 s a build (template 4.6 s), image ~660 MB; her VPS numbers come from vps-ops `appengine_check`.

## 12. What is NOT in this plan (on purpose)

- Copying Lovable's code, assets, fonts, copy or name - patterns only.
- Supabase / Cloudflare Workers / TanStack Start SSR - our own backend and hosting first; SSR only if the L0 card and
  real SEO numbers ask for it.
- A Rust dev server - Vite first, measured.
- Native mobile from the App Engine - App Sahayak already builds native apps; a shared backend links them (applink).
- Any PC-frozen file - nothing here touches `server/app/pc/`, `agent/pc_tools.py`, `desktop/` or their tests.

## 13. Not verified, said plainly

- Every Lovable fact is from their docs, their published npm packages, their live CSS / string bundles and a leaked
  2025 prompt (see the research file's confidence tags). Their home page was not fetched (Cloudflare challenge).
- No phase is built. The App Engine's sandbox cost on her VPS is an estimate until L8 measures it.
