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
| R0 Eyes first | Golden screenshot tests (flutter_test, light + dark, 360 + 412 px) for every screen this plan touches, run in build-apk CI and uploaded as an artifact zip, so every later phase is SEEN. Fonts bundled as assets (no runtime font download = no text flicker, works offline). | `test/goldens/`, `.github/workflows/build-apk.yml`, `pubspec.yaml` |
| R1 Design system | `hoola_theme.dart` (tokens, type, shape, motion, icons), Light / Dark / System setting, a test that fails on new raw colours / sizes below 12 / weights above 700. Old Night Glass kept only until R8 moves the last screen. | `lib/ui/hoola_theme.dart`, `glass.dart`, `main.dart` |
| R2 Shell | 4-tab pill nav, drawer, the pill composer (+ / field / mic / voice), named transitions, haptics, the on-call bar redone as a slim pill above the composer. | `main.dart`, NEW `lib/ui/shell/` |
| R3 Chat | The heart. Serif replies, user bubble, markdown spacing, code block + inline code, tables, streaming at reading speed with the soft tail fade and capped catch-up, the "used N tools ›" line + Steps sheet (icon per step kind, internal steps hidden, helper agents folded), working mark (idle / thinking / writing), Stop, action row (copy / share / read aloud / good / not right / ask again), long-press sheet, scroll-to-latest button, attachments tray, "Reconnecting…" + clear error with Retry. | `chat_screen.dart` split into `lib/ui/chat/`, `md_text.dart`, `think_card.dart`, `chat_attach.dart` |
| R3s Server | Each step event carries `kind` (search / read / write / edit / web / run / agent / skill / question / card / other) and `housekeeping`; one "turn result" record (status of 8, needs-you flag, one-line description, what was made) used by the chat list, Work, the notification and the chat card, so all four always agree. | `server/app/agent/labels_en.py`, `kaamlist.py`, `events.py`, `push.py` |
| R4 Cards | One card shell (`HoolaCard`): approval (Yes / Not now), question (choices), file / made-thing card, next-step offer, payment (still only in the unlocked app). Push notifications get Yes / Not now on approvals (never for money). | `any_card.dart`, `hoola_cards.dart`, `approve_sheet.dart`, `tool/android/kotlin/Notify.kt` |
| R5 Talk | The call screen: what she said / what Santosh said, orb driven by her live voice level, controls row (show something / voice / mute / end), reduce motion. Call engine unchanged. | `live_voice_screen.dart`, `voice_screen.dart` |
| R6 Work + Made + Connect | The three tabs from the mock-ups, on the existing APIs (`/api/kaam/list`, artifacts / files / creations, bazar connectors). | `today_screen.dart` -> `work_screen.dart`, NEW `made_screen.dart`, `bazar_screen.dart` |
| R7 Settings | Settings screen (6 groups) + Your AI team list; every old Main row lands in exactly one place (a test lists the old rows and checks each still has a way in). | `profile_screen.dart`, `employees_screen.dart` |
| R8 Desks | `DeskScaffold` (header, tabs, loading, error + Retry, empty state, warning row, confirm sheet, detail as a sheet) and all ~150 desk screens moved onto it in waves of ~20, worst first (app_design, notebook, motion, hoola_media, deal, rentdesk, tourguide, homestay, notary, courier, devops ...). English and icons fixed in the same pass. | every `*_screen.dart` |
| R9 Proof + polish | Goldens for every screen in both themes, TalkBack labels, text at 200 %, 60 fps scroll on a budget phone (the blur and Aurora go, which helps), sounds only if she decides, the old glass.dart deleted. | all |

Rough size: R0-R3 are the big ones (the chat is 2,791 lines today); R8 is the longest by volume. Nothing on the server
changes except R3s.

## 4. Decisions only the owner can make (the plan assumes the first option)

1. **Tabs:** Hoola / Work / Connect / Made, with Talk in the composer and Profile behind the drawer avatar - or keep 5
   tabs (Today / Chat / Talk / Connect / Settings) in the new look.
2. **Accent:** Hoola violet - or another single colour. (Claude's terracotta + spark would make Hoola look like a copy.)
3. **Night Glass goes completely** (dark aurora, glass panels, mood colours on the call) - or keep the aurora only on
   the call screen.
4. **Mera PC screens** (`pc_screen.dart`, `hoola_pc_screen.dart`) are FROZEN: they keep the old look until she lifts the
   freeze for a style-only change.
5. **Sound cues** on calls / approvals: none (default), or short Hoola-made tones.

## 5. Not verified / risks

- Flutter cannot run in this sandbox: every phase compiles first on CI; R0's screenshots are how the result is seen.
- Material Symbols / any new package must support Dart 3.5.4 (the CI pin) - checked when R1 adds it.
- The Claude numbers come from the owner's research files and screenshots, not from Anthropic.
- Old APKs keep working: the server change (R3s) only adds fields.
