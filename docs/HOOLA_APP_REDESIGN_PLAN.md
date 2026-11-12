# Hoola phone app - the Claude-style redesign (plan)

Owner, 12 Nov 2026: "CHANGE ENTIRE EXISTING DESIGN OF HOOLA APP AND SWITCH TO CLAUDE APP DESIGN, UI / UX, ANIMATION,
SMOOTHNESS - EVERYTHING ... 100 % CLAUDE APP NATIVE HUMAN MADE APP ... FROM STREAMING SMOOTH CHAT TO SMALL DETAILS".

Inputs: the screen audit (`docs/research/app_design/00_INDEX.md` + 01-04), the owner's Claude APK report and 7 HTML pages
(`05_claude_android_reference.md`), 24 Claude app screenshots she sent (light + dark).
Mock-ups of the 10 basic screens, light + dark: the "Hoola App - Claude-style redesign" design canvas (link in chat).

## 0. What "Claude-style" means here (and what stays Hoola)

Taken from Claude, as LAYOUT, BEHAVIOUR and NUMBERS: the warm paper / warm charcoal neutrals, one quiet surface per
card, serif replies + sans interface, the floating pill tab bar, the pill composer with a voice button, the drawer of
recent chats, steps folded into one grey line that opens a sheet, cards with one question and two buttons, pop-over menus,
bottom sheets for detail, empty states in two lines, springs and fades, streaming with a soft tail, reduce motion.

Kept Hoola's own, on purpose (it must not look like a copy of someone else's product, and Anthropic's fonts, logo,
animations, sounds and icons are theirs): the Hoola mark (blue / violet orbit) in place of Claude's spark, Hoola violet
(#5B45E0 light / #9C88FF dark) as the one accent, free fonts (Schibsted Grotesk interface, Literata replies + headings,
JetBrains Mono code - the same three the web console already uses), Material Symbols Rounded icons, Hoola's own working
mark animation. Hoola's rules do not change: money / sending / deleting only on her tap.

## 1. The new design system (one file: `lib/ui/hoola_theme.dart`, replaces Night Glass in `glass.dart`)

Colour roles (light / dark):

| role | light | dark |
|---|---|---|
| bg (page) | #FAF9F6 | #1D1C1A |
| surface (cards, composer, nav) | #FFFFFF | #262523 |
| sunk (user bubble, tiles, chips) | #F1F0EC | #2F2E2B |
| line / line strong | #E5E3DD / #D3D1CA | #3A3936 / #4A4945 |
| ink / ink2 / ink3 | #1B1A17 / #57554F / #6F6C65 | #F3F1EC / #BBB8B0 / #9C9890 |
| accent / accent soft | #5B45E0 / #EEEBFD | #9C88FF / #2B2547 |
| primary pill (buttons) / text on it | #1B1A17 / #FFFFFF | #F3F1EC / #1B1A17 |
| ok / warn / bad (+ soft backgrounds) | #1F7A52 / #8F5409 / #B8361F | #4CC38A / #E8B062 / #F07A6A |
| code chip / code ink | #F1F0EC / #2B5DB8 | #2F2E2B / #8AB4F8 |

Every text pair passes 4.5:1. No raw `Color(0x..)` outside this file (a test enforces it).

Type (sp; one scale for the whole app): display 22/700 · heading 18/600 · title 15-16/600 · body 15-16/400 ·
reply 17 Literata 1.6 · small 13/400 · label 12/500 · code 12-14 mono. Weights 400/500/600/700 only. 12 is the floor.
Markdown: H1 22 Literata, H2 18, H3 16; paragraph gap 8 + line height 1.6; list indent 16; code block corner 12,
padding 12, header row with Copy + Expand; tables scroll sideways in a box.

Shape + space: corners 8 (chips) / 12 (tiles, code) / 16-18 (cards) / 28 (sheets) / pill; spacing 4-8-12-16-20-24;
touch targets 44 minimum (48 for the main buttons). Shadows only on floating things (composer, nav, menus, sheets).

Motion (all through one `HoolaMotion` helper that obeys the phone's reduce-motion setting):
push = slide from right 280 ms; sheet = slide up with a spring, scrim 0 -> 40 %; menu = scale 0.96 -> 1 + fade 160 ms;
loading -> loaded -> error = crossfade 200 ms; title change = headline crossfade; tab change = icon crossfade + pill
slide; card enter = small spring up. Reduce motion: every transition becomes a 120 ms fade, springs 0 ms, orb still.

## 2. The new app map (the user's question: what are the tabs)

Floating pill tab bar, 4 tabs (Claude has 4):
- **Hoola** - home greeting + the chat. The drawer (top-left) lists recent chats + calls, All chats, "What Santosh
  remembers", and her avatar (-> Settings) + New chat.
- **Work** - replaces Today: Needs you (approvals, questions) -> Working now (live steps) -> Done today -> Your AI team.
- **Connect** - Connected + Add a connection (search on top). TV, Reels, Motion, Scroll report and the spend limit move
  out to Settings / Work.
- **Made** - everything Hoola made: documents, pictures, websites, sheets, apps; search + type filter.

Talk is no longer a tab: the black voice button in the composer opens the call (as in Claude). Main/Profile becomes
**Settings** (avatar, memory, rules, AI team, appearance, notifications, language, privacy + ID Locker, billing, help,
log out) reached from the drawer. The ~100 desk rows that sat on Main move into Work -> Your AI team.

## 3. Phases (each = one version, the normal ritual: main.py + pubspec + test_routines + HISTORY + CI green + APK)

| phase | what ships | main files |
|---|---|---|
| R0 Eyes first (v0.859, built) | Golden screenshot tests (flutter_test, light + dark, 360 + 412 px) for every screen this plan touches, run in build-apk CI and uploaded as an artifact zip, so every later phase is SEEN. Fonts bundled as assets (no runtime font download = no text flicker, works offline). | `test/goldens/`, `.github/workflows/build-apk.yml`, `pubspec.yaml` |
| R1 Design system (v0.860, built) | `hoola_theme.dart` (tokens, type, shape, motion, icons), Light / Dark / System setting, a test that fails on new raw colours / sizes below 12 / weights above 700. Old Night Glass kept only until R8 moves the last screen. | `lib/ui/hoola_theme.dart`, `glass.dart`, `main.dart` |
| R2 Shell (v0.861, built, preview switch) | 4-tab pill nav, drawer, the pill composer (+ / field / mic / voice), named transitions, haptics, the on-call bar redone as a slim pill above the composer. | `main.dart`, NEW `lib/ui/shell/` |
| R3 Chat (v0.862, built, preview switch; cards still old until R4) | The heart. Serif replies, user bubble, markdown spacing, code block + inline code, tables, streaming at reading speed with the soft tail fade and capped catch-up, the "used N tools ›" line + Steps sheet (icon per step kind, internal steps hidden, helper agents folded), working mark (idle / thinking / writing), Stop, action row (copy / share / read aloud / good / not right / ask again), long-press sheet, scroll-to-latest button, attachments tray, "Reconnecting…" + clear error with Retry. | `chat_screen.dart` split into `lib/ui/chat/`, `md_text.dart`, `think_card.dart`, `chat_attach.dart` |
| R3s Server (v0.863, built) | Each step event carries `kind` (search / read / write / edit / web / run / agent / skill / question / card / other) and `housekeeping`; one "turn result" record (status of 8, needs-you flag, one-line description, what was made) used by the chat list, Work, the notification and the chat card, so all four always agree. | `server/app/agent/labels_en.py`, `kaamlist.py`, `events.py`, `push.py` |
| R4 Cards (v0.864, built: shell + approval / file / page / default; desk cards move in R8) | One card shell (`HoolaCard`): approval (Yes / Not now), question (choices), file / made-thing card, next-step offer, payment (still only in the unlocked app). Push notifications get Yes / Not now on approvals (never for money). | `any_card.dart`, `hoola_cards.dart`, `approve_sheet.dart`, `tool/android/kotlin/Notify.kt` |
| R5 Talk (v0.865, built: live call; the turn-by-turn voice screen stays old) | The call screen: what she said / what Santosh said, orb driven by her live voice level, controls row (show something / voice / mute / end), reduce motion. Call engine unchanged. | `live_voice_screen.dart`, `voice_screen.dart` |
| R6 Work + Made + Connect (v0.866, built, preview switch) | The three tabs from the mock-ups, on the existing APIs (`/api/kaam/list`, artifacts / files / creations, bazar connectors). | `today_screen.dart` -> `work_screen.dart`, NEW `made_screen.dart`, `bazar_screen.dart` |
| R7 Settings (v0.867, built, preview switch) | Settings screen (6 groups) + Your AI team list; every old Main row lands in exactly one place (a test lists the old rows and checks each still has a way in). | `profile_screen.dart`, `employees_screen.dart` |
| R8 Desks (v0.868 wave 1 + v0.869 wave 2 built: kit + flat desk frame for all + 57 desks + 4 inner pages; next waves per GO) | `DeskScaffold` (header, tabs, loading, error + Retry, empty state, warning row, confirm sheet, detail as a sheet) and all ~150 desk screens moved onto it in waves of ~20, worst first (app_design, notebook, motion, hoola_media, deal, rentdesk, tourguide, homestay, notary, courier, devops ...). English and icons fixed in the same pass. | every `*_screen.dart` |
| R9 Proof + polish | Goldens for every screen in both themes, TalkBack labels, text at 200 %, 60 fps scroll on a budget phone (the blur and Aurora go, which helps), sounds only if she decides, the old glass.dart deleted. | all |

Rough size: R0-R3 are the big ones (the chat is 2,791 lines today); R8 is the longest by volume. Nothing on the server
changes except R3s.

## 3a. The text pipeline (owner's "How Claude Formats Text" page, layer by layer)

What the phone app (`lib/ui/md_text.dart`, 452 lines) has today, and what R3 / R3s add:

| Claude layer | Hoola phone today | R3 / R3s adds |
|---|---|---|
| 1 model sends plain Markdown | same (the server streams Markdown text) | nothing |
| 2 Markdown -> blocks + inline marks | own parser: paragraphs (soft breaks reflow, v0.284), headings, bullet / numbered lists with nesting, quotes, code fences, tables, rules, bold / italic / strike / inline code / links | links to chats / files open in-app (kept); images inside replies |
| 3 styles per mark | bold, italic, strike, link colour, inline code = generic `monospace` on a white overlay; headings 22 / 20 / 17 | JetBrains Mono everywhere; inline code = tinted chip in the code colour role; bold 600; link = accent + underline; headings 22 / 18 / 16 (Literata); list indent 16 per level; table cell padding 8, header semibold, full-width box that scrolls |
| 3 code blocks | dark box, monospace, scrolls sideways; no header, no copy | header row with the language + Copy + Expand (full-screen sheet), light syntax colours from theme roles, corner 12, padding 12 |
| 4 one theme every text inherits | sizes / colours set by hand per screen (29 sizes) | `hoola_theme.dart` TextTheme: display 22/700, heading 18/600, H2 16/600, H3 14/600, body 15/400, small 13/400, code 12-14 mono, reply 17 Literata |
| 5 rich system strings (code / colour / link inside a sentence) | plain strings | `HoolaRich` helper: a string with `{code:..}`, `{link:settings|..}`, `{accent:..}` parts, for help lines, setup steps, notices |
| 6 same tokens inside web views (artifacts) | artifacts / pages keep their own CSS | the app passes its colour + font roles (light / dark) into every Hoola artifact / page WebView as CSS variables (`--hoola-*`), so a page made in chat matches the app |
| 7 server-formatted lines (errors, model name, counts, limits) | server lines arrive as plain text inside the reply | R3s: a `notice` event `{text, role: info|warn|danger|code, link}` drawn by the app in that role - never mixed into the model's Markdown |
| streaming: half-written marks | an open `**` / `` ` `` / `~~` already styles what follows (no stray stars); a table header waits for its separator | kept; plus the soft tail fade on the newest words and capped catch-up; an unclosed mark at the very end shows as text (no crash) |
| speed | re-parses the whole reply on every update | parse only the last (growing) block while streaming; finished blocks cached |

Paragraph gap: 16 today (measured on Claude web, v0.274). The Android page says 8; the screenshots look nearer 12 -
R0's golden screenshots decide, side by side with the owner's Claude screenshots.

## 3b. Chat timing + connection (owner's "Chat Timing & Text Pipeline" page)

| Claude (owner's page) | Hoola phone today | R3 adds |
|---|---|---|
| live stream of tokens (SSE) | Android `SantoshService` keeps the live event stream (`Native.start`), events numbered, resume from the last number after a drop (`lastEventId`) | kept |
| stall -> reconnect after 15 s | reconnect with backoff 3 -> 6 -> 12 -> 30 s when the stream drops; a "typing" guard ends a dead turn after 75 s; self-check every 90 s | stall watch: no event for 15 s while a reply is streaming -> quiet reconnect + resume; "Reconnecting…" shown under the reply (not a banner) and gone when words flow again |
| retry budget, then a clear failure | "Ask again" exists (`retryLastReply`) | after 3 failed reconnects: one plain line "Lost the connection - Retry" with the reply kept so far |
| thinking mark between send and first word | typing dots / mood | the Hoola working mark (thinking state) under her message from the tap until the first word |
| ~55 tokens / s, no flicker | `_Reveal` paces words (v0.283: 60-79 words / s, catch-up capped) | same pacing + soft tail fade; parse only the growing block (3a) |
| message shown at once on tap | yes (local echo) | kept, with a "sending" tick that turns solid when the server has it |
| connection reused (keep-alive) | already one shared HTTP client (`api.dart:52`) | kept; one upload path (`api.dart:2121`) opens its own client - moved onto the shared one |
| artifact WebView pre-warmed | opens cold | keep one WebView warm while a chat is open |
| first word in 0.25-0.6 s | NOT comparable: a Hoola turn picks tools, reads memory and runs a model through the server (Claude's figure is only their network + first token) | the app MEASURES it: tap -> first word, logged per turn and shown in Settings > Usage; the server work to make it faster is separate (not a design job) |

## 3c. Artifacts (owner's "Claude Artifact System" page)

Hoola already has the core of it (`server/app/artifacts.py`, `lib/ui/artifact_screen.dart`, `artifacts_screen.dart`):

| Claude stage | Hoola today | R3 / R4 / R6 adds |
|---|---|---|
| 1 page made while the reply streams | the page is written by the model, one row per version (`ArtifactVersion`), progress events on the bus; console card shows the step, a live clock and Stop (v0.725) | the phone card gets the same: step, clock, Stop, then ready / not made with a reason and Try again |
| 2 card in the chat -> full-screen page | `artifact` card in chat opens `ArtifactScreen` full screen | the new card (tile + title + "Page · v3"), same as the mock-up |
| 3 web view kept warm (300-800 ms -> < 50 ms) | opens cold every time; the screen polls every 5 s | one warm WebView while a chat is open; live `artifact` events instead of the 5 s poll |
| 4 handshake, size + safe area + theme sent in | page loads by signed URL (`/a/<id>/<v>?exp&sig`, HMAC, short expiry) | the app passes its size, safe area and LIGHT / DARK colour + font roles (`--hoola-*`, 3a layer 6) |
| 5 sandbox: own domain, scripts only from 2 CDNs, no file access | CSP `sandbox` (opaque origin: no cookies, no Hoola API), scripts only from pinned CDNs, `connect-src 'none'`, no forms, no frames | kept. Owner decision: serve pages from a SEPARATE domain (e.g. a `hoolapages` domain) like Claude does - needs her DNS |
| 5 runtime API in the page | `window.santosh.storage.get/set/all` (saved per page on the server) + `ask` (short answer from the brain); off on a shared link | kept, renamed `window.hoola` (old name kept as an alias) |
| 6 page tells the app which edge is visible -> composer / nav hide while reading | not done | yes: hide the composer + tab bar while she scrolls down a page, show again at the top / bottom |
| 7 page can send a message into the chat ("Ask Claude" button) | `ask` returns an answer inside the page only | `window.hoola.send(text)` posts it as HER message in the chat that made the page, only after a small confirm sheet (the page is data, never instructions) |
| 8 comments on a page | console only (design canvas), not artifacts | later (not in this redesign) |
| 9 sharing: public link / team / look when shared | public link (`/s/<token>`), unshare, versions menu, open in browser, delete | menu redone as a pop-over (Open in browser / Copy link / Versions / Share / Delete in red); team-only sharing = later |
| gallery | artifacts list screen | the **Made** tab (pages + files + pictures + sites), filter by type, search; the chat header's file button = what this chat made, with "Download all" |
| 110 typed blocks in chat | ~10 card kinds drawn on the phone (`any_card`, maps, file, approval, ask form, goal / plan, think, UPI, call receipt, photo) | R4: one card shell + typed bodies; first: question (choices), next-step offer, file / page, plan (to-do list), map, chart, image gallery |

## 4. Decisions only the owner can make (the plan assumes the first option)

1. **Tabs:** Hoola / Work / Connect / Made, with Talk in the composer and Profile behind the drawer avatar - or keep 5
   tabs (Today / Chat / Talk / Connect / Settings) in the new look.
2. **Accent:** Hoola violet - or another single colour. (Claude's terracotta + spark would make Hoola look like a copy.)
3. **Night Glass goes completely** (dark aurora, glass panels, mood colours on the call) - or keep the aurora only on
   the call screen.
4. **Mera PC screens** (`pc_screen.dart`, `hoola_pc_screen.dart`) are FROZEN: they keep the old look until she lifts the
   freeze for a style-only change.
5. **Pages on their own domain:** serve made pages from a separate domain (safer, like Claude) - needs a DNS record from her; until then the current sandbox stays.
6. **Sound cues** on calls / approvals: none (default), or short Hoola-made tones.

## 5. Not verified / risks

- Flutter cannot run in this sandbox: every phase compiles first on CI; R0's screenshots are how the result is seen.
- Material Symbols / any new package must support Dart 3.5.4 (the CI pin) - checked when R1 adds it.
- The Claude numbers come from the owner's research files and screenshots, not from Anthropic.
- Old APKs keep working: the server change (R3s) only adds fields.
