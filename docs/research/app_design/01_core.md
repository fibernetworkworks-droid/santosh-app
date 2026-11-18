# Hoola phone app: core design audit (read-only, judged from source)

Scope: lib/main.dart plus 31 lib/ui files. Flutter cannot run here, so every finding comes from the code. Line numbers refer to the files as they are on main today.

## App-wide measurements (scripted over the files in scope)

| file | lines | raw `Color(0x..)` | text under 12 px | Semantics |
|---|---|---|---|---|
| home_sections.dart | 1641 | **115** | **59** (smallest 8.5) | 0 |
| today_screen.dart | 890 | 53 | 21 (smallest 9.5) | 0 |
| chat_screen.dart | 2791 | 37 | 5 | 2 |
| glass.dart | 366 | 36 | 1 | 0 |
| chat_attach.dart | 492 | 21 | 0 | 3 |
| live_voice_screen.dart | 601 | 12 | 3 | 2 |
| plugin_widgets.dart | 393 | 10 | 4 | 0 |
| any_card.dart / approve_sheet.dart | 309 / 249 | 9 / 9 | 3 / 0 | 0 / 1 |
| hoola_cards.dart | 946 | 0 | 7 | 0 |
| hoola_net_screen.dart | 1212 | 2 | 6 | 0 |
| employees_screen.dart | 2367 | 0 | 5 | 0 |
| profile_screen.dart | 1647 | 4 | 2 | 0 |

- **Font weights across all lib/ui plus main.dart:** w800 722, w700 700, w600 153, w900 13, w500 8, w400 3. Bold is the default rather than an accent, so nothing stands out. The console pass already capped weights at 600 (v0.255); the phone never got that pass.
- **Font sizes:** home_sections alone uses 16 distinct sizes (8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13.5, 14, 14.5, 15, 16, 19, 23). chat_screen uses 11. glass.dart defines colours (class C) and `display()` / `replyText()`, but **no type scale**: there are no `body`, `label`, `caption` or `title` tokens. Every file therefore invents its own `TextStyle(fontSize: x)`. This is the root cause of most findings below.
- **Semantics:** 16 wrappers in the whole core, 0 in the Today, Home, Profile, Connect, Employees and Network screens. Custom `Press` + `Container` tap targets (chips, tiles, pills) carry no label and no button role.
- **Language:** strings go through `app.g()`, and `tr()` falls back to the Hinglish *key* when the English map lacks it (i18n.dart:304). The g() keys I sampled are covered. The leftovers are **literal strings that bypass g()**:
  - today_screen.dart:44 greeting `Shubh ratri / Suprabhat / Namaste / Shubh sandhya` (the first line she reads)
  - profile_screen.dart:223 `Naam, mahila/purush, roop, awaaz`
  - profile_screen.dart:230-231 `${name} ka roop`, `100 roop, duniya bhar se`
  - profile_screen.dart many `... sahayak` titles (Theka / Franchise / Niryat / Thok / SEO / Bima / Feedback / Community / Shikayat)
  - profile_screen.dart: `Feedback se roadmap` (581), `AI ka kharcha` (956), `phone se` (1276), `Pin hatao` (1395), `'Band'` briefing subtitle (~1430)
  - avatar_setup_screen.dart: `Seedha mana` (441), `Se ${from}` (496), `Seekhna` (511), `Namaste! Main $_n.` (535)
  - hoola_net_screen.dart: `QR banaiye` (204), `} se baat` (392), `Aapka …` (448), `aap admin` (507), `se banwaiye` (672), `Kaam do` (1172)
  - live_voice_screen.dart:513 `mic band`
  - employee_screen.dart:268 `(band)`
- **Internal name shown to users:** voice_screen.dart:390 hard-codes `'SANTOSH'` as the speaker label. live_voice_screen uses `app.aName`.
- **Emoji as UI chrome:** hoola_cards 25 lines (`✅ verified`, `🏢 business`, `⭐ VIP`, `⚠️ identity changed` at 22-26), hoola_net 18, home_sections 17 (weather glyphs 228-235 instead of icons), goal_card 4 (`✅ WHAT HAPPENED`, `📎 WHAT WAS MADE`, `👉 WHAT YOU NEED TO DO` at 184-187; `⏳` step marks at 14), chat_screen 4 (`🕶 Incognito` at 596 and 739, `Sab ho gaya ✓` at 674 is also Hinglish), kaam_sheet:103 `📞 call`, calls_sheet:101 `📞 Call`, bazar_screen:173 `linked ✓`.

---

## Per-file entries

### main.dart (app shell)
- **What it is:** a 5-slot glass bottom bar (Today / Chat / raised Talk orb / Connect / Main), CallBar above it, Aurora background, a lock-screen "Talk only" mode, and first-run AvatarSetup.
- **Problems:**
  - The tab is labelled **"Main"** (466) but its page title is **"Profile"** (profile_screen:213). The word "Main" means nothing in English and reads as Hindi "I".
  - The Talk orb (472-488) has no visible label, only a Semantics label. New users don't know it means "voice call".
  - The orb gradient uses raw colours (481-482) rather than `C.gradient`.
  - Nav labels are 11 px (441). This is acceptable only for nav; everywhere else it isn't.
  - Bottom padding is magic numbers: 92 / 152 (401).
  - Nav items are 62 px tall, which is good.

### glass.dart (design system)
- **What it is:** C tokens, `display()` (Sora), `replyText()` (Literata), the Manrope theme, Glass / Aurora / Press / GradientButton / GlassButton / Pill / Avatar / Caption / Stagger.
- **Problems:**
  - No text-style tokens beyond those two functions.
  - The widgets themselves use raw colours: GlassButton 158-159 `0x17FFFFFF` / `0x29FFFFFF`, Pill 169 `0x1FFFFFFF`, Avatar 195 sweep, snackbar 72, Aurora blobs 24-26. There are no surface or border tokens, so other files copy these alphas by hand. I counted 0x12 / 0x14 / 0x17 / 0x1F / 0x21 / 0x26 / 0x29 white all in use.
  - Pill is 11 px w800 with letter-spacing (177). Caption is 12 px w800 all caps (220).
  - Press has no Semantics or button role built in, which is why the whole app lacks them.
- **Fix:** add `T.title / T.body / T.label / T.caption`, `C.surface1/2`, `C.border`, `C.borderStrong`, and give Press `semanticLabel`.

### today_screen.dart (Today tab)
- **What it is:** the default tab. Section order (157-238):
  1. date + weather chip
  2. greeting
  3. hero (avatar, mood line, Talk / Type buttons, status)
  4. approvals
  5. WORK STATUS
  6. TODAY tiles
  7. DO SOON (4 tiles + a scroll of 4 chips)
  8. Employee
  9. Network
  10. Notebook
  11. Learned
  12. Reminders
  13. Routines
  14. Lists
  15. Recap (24 h)
  16. PartnerFooter
- **Problems:**
  - That is **16 stacked sections**. Approvals (the only thing that truly needs her) sit 4th, and are styled like any other card (`border 0x66FFB15C`, 180).
  - The greeting is Hinglish (44).
  - The hero says "Talk" and "Type it" (121-123), duplicating the nav orb and the Chat tab. The status text always says "Online" even when disconnected (132). Plural bug: `'$pend tasks are waiting'` gives "1 tasks" (100).
  - The DO SOON tiles and chips use 8 hard-coded gradient pairs (204-225). The chips are about 32 px tall (padding 6 plus a 20 px badge, 246-260), so the tap target is under 44.
  - The weather chip text is 11.5 px (92) and the icon is an emoji.
  - The Reminder / Routines / Lists empty states repeat the same "invite card + Start a chat CTA + italic promise" pattern three times, each with its own raw accent: 0xFFFCD34D (418), 0xFFC4B5FD (639), 0xFF5EEAD4 (795). Tagline colours like `0x99C4B5FD` at 11.5 italic (644) are low contrast.
  - Count badges are 9.5 px (745).
  - The hero avatar takes 132 px of a 328 px content width (112). On a 360 px phone the mood line, 3-line text and two buttons get about 180 px.
- **Fix:**
  - Put "Needs you" at the very top.
  - Merge Reminders / Routines / Lists into one "Scheduled" card.
  - Move Employee / Network / Notebook / Learned off Today, or collapse them to one "Your Hoola" row.

### home_sections.dart (Today's sections)
- **What it is:** HomeLabel / HomeBar plus LiveWorkSection, DayTilesSection, EmployeeSection, NetworkSection, NotebookSection, LearnedSection, RecapSection, PartnerFooter.
- **Problems:**
  - This is the worst file for tokens: 115 raw colours, 59 sub-12 px texts.
  - Badges are 8.5 px all caps (733, 844, 893), with 9 px texts at 129, 1111, 1163, 1386 and 1467.
  - `app.g('khud seekha')` at 9 px with raw violet (1386).
  - Weather emoji at 228-235.
  - Labels are all-caps marketing names ("HOOLA EMPLOYEE", "HOOLA NETWORK", "HOOLA NOTEBOOK", "WHAT HOOLA DID · LAST 24 HOURS" at 539/929/1195/1595). "HOOLA EMPLOYEE" (539/623) is the old naming; the product now says AI Employees.
  - Each section builds its own empty and full card with a bespoke layout. There is no shared `HomeCard(title, count, items, cta)`.

### chat_screen.dart (Chat tab)
- **What it is:**
  - header (586): LiveAvatar, name, status line, plus 3 icon buttons: Voice, Old chats, New chat
  - the feed (`_item` with 5 kinds, plus about 10 inline card classes at 2283-2791: Campaign, Email, EmailNew, EmailSnooze, Bazar, Open, Link)
  - waiting strip, reply bar, quick replies, composer (1278: attach, text field, 50 px send / mic)
- **Problems:**
  - The empty hero (837-876) shows a 170 px avatar plus three starters, and an italic 12 px privacy line in C.faint.
  - The status line mixes `🕶 Incognito · will not be remembered` (596) with `Online · <language>`.
  - The voice IconButton duplicates the nav orb (601).
  - The card classes inside this 2.8k-line file duplicate any_card / hoola_cards. There is no single card shell, so each email or campaign card sets its own paddings and sizes (12-13.5 px).
  - Many fresh English keys (Retry, Summary of this chat, Your work, Calls) are fine; `Sab ho gaya ✓` (674) is Hinglish plus a glyph.
  - Sizes 10.5 to 11.5 appear on step and meta text.
  - Only 2 Semantics wrappers in the whole chat. Message bubbles and step dots have none.

### chat_attach.dart
- **What it is:** attachment tray, tiles above her bubble, and a full-screen viewer.
- **Problems:**
  - 21 raw colours: file-type tints 61-64, tile surfaces 94/114/123/139 (0xFF1E1A38 / 1B1830 / 15122B / 1A1733) that are four near-identical surfaces, and overlay 0xB8 / 0xC7110F20.
  - Semantics are present (3), which is good. Text is 12 px throughout.
  - Needs `C.surface` tokens.

### md_text.dart
- **What it is:** the markdown renderer for replies.
- **Problems:** 7 raw colours (code / quote backgrounds) and a fixed 14 px for code and tables. It is otherwise consistent with `replyText()`. It is fine apart from tokenising.

### think_card.dart
- **What it is:** the folded "Thinking" card.
- **Problems:** clean; 12.5 px meta and 1 Semantics wrapper. None.

### goal_card.dart
- **What it is:** the long-job plan and report card in chat.
- **Problems:**
  - Emoji headings `✅ / 📎 / 👉` (184-187) and the step glyph map including `⏳` (14).
  - Headers are 10.5 px w800 caps (49, 167), sub-text 10.5 px (85).
  - Uses 7 different sizes in 191 lines.
- **Fix:** icons plus T.label.

### work_strip.dart, kaam_sheet.dart, calls_sheet.dart
- **What they are:** the live-work strip above chat, and the "Your work" and "Your calls" bottom sheets.
- **Problems:**
  - These are small and fairly consistent, with 12 / 13 px text.
  - The emoji `📞` in list rows (kaam_sheet 103, calls_sheet 101) should be leading icons.
  - The two sheets are near-identical layouts written twice. One `HoolaListSheet` would cover both.

### hoola_cards.dart
- **What it is:** the premium default card plus network and contact cards.
- **Problems:**
  - 25 emoji lines: `✅ verified` / `🏢 business` / `⭐ VIP` / `⚠️ identity changed` at 22-26, all 11.5 px coloured text (each a "badge" with no badge shape).
  - 7 sizes. 0 raw colours, which is good.

### any_card.dart
- **What it is:** the fallback for every unknown card kind (the default card).
- **Problems:**
  - It defines a **private palette** at 29-32 (`_surf1 0xFF1C1838`, `_surf2`, `_hair`, `_vio 0xFFA28DFF`). That is a second design system living beside C.
  - Eyebrow 10.5 px caps (153); meta 11 px (158, 161).
  - The docked CTA gradient is raw (296).
- **Fix:** promote `_surf*` into C and use them everywhere (chat_attach, approve_sheet).

### approve_sheet.dart
- **What it is:** the approval bottom sheet, money cards included.
- **Problems:**
  - Its own tint 0xFF1A143A (41), handle colour, dividers 0x14FFFFFF (158/164), and a raw CTA gradient (204-206). That is a third copy of the CTA gradient.
  - The demo pill is all-caps "DEMO · NO REAL MONEY WILL BE CUT" (79).
  - Hierarchy is good (amount big, 15.5).
  - Semantics: 1 wrapper. The slide/approve control needs an explicit label.

### catchup_screen.dart
- **What it is:** "Welcome back" after time offline: what waited, what happened.
- **Problems:** fine structure (2 Captions). Count numbers are display(24) in raw-ish colours, and one 11.5 px text. Minor.

### live_voice_screen.dart (Talk tab, realtime)
- **What it is:** the live call screen: avatar, captions (YOU / NAME), cards that arrived during the call, controls, and a green CallBar.
- **Problems:**
  - Hinglish `mic band` in the CallBar state (513).
  - The CallBar is raw green 0xFF15803D (518), not C.ok.
  - Speaker labels are 10.5 px caps (430, 435).
  - 12 raw colours.
  - The state strings at 80-89 are English keys missing from the en map, so they fall back correctly.

### voice_screen.dart (Talk, fallback phone-speech)
- **What it is:** the older voice screen used when realtime is off (main.dart:503).
- **Problems:**
  - Hard-coded `'SANTOSH'` label (390). This is the internal name reaching the user; it must be `app.aName`.
  - It duplicates live_voice_screen's caption layout (385 vs 430). Two screens drift apart.

### live_santosh.dart, santosh3d.dart, hoola_mark.dart, avatar_look.dart
- **What they are:** the avatar renderers (2D LiveSantosh, a 3D wrapper, the T1-T3 thinking mark) and the look picker.
- **Problems:**
  - `Santosh3D` is not instantiated anywhere in lib (only its class definition). It looks like dead code.
  - LiveSantosh is drawn at 6 different sizes (140, 150, 170, 190 default, 260 in setup / santosh3d): today:112 150, chat:840 170, catchup:48 140, setup:73 260. An avatar scale (S / M / L) would unify them.
  - avatar_look: 1 tiny text (10.5).

### setup_screen.dart (first launch: server / sign-in)
- **What it is:** "Hello, I am Hoola" (79), a 260 px avatar, and connect fields.
- **Problems:** 6 different sizes in 137 lines and 11 / 11.5 px helper text. Otherwise simple.

### avatar_setup_screen.dart (first run: name, gender, rules; also Profile > My Rules)
- **What it is:** a multi-step wizard: name, male / female, selling rules, then My Rules (who can reach, VIPs, refuse, what can come in, quiet hours, language, learning), then "Namaste! Main $_n."
- **Problems:**
  - Hinglish section titles `Seedha mana` (441) and `Seekhna` (511).
  - `Se ${from}` paired with "Until" (496): half Hindi, half English in one row.
  - Closing line `Namaste! Main $_n.` (535).
  - The rules page asks about 8 decisions on the first run, before she has used the app. Too many options too early. Defaults should be silent, editable later.
  - The quiet-hours time is a plain TextButton (small target).

### profile_screen.dart ("Main" tab)
- **What it is:** a title "Profile" (213), then:
  - **one Glass card holding about 100 ListTiles** (starting at 219)
  - about 20 more single-entry Glass cards (878-1075)
  - Account, connectors, briefing, language and voice, voice-reply switch, "Talk from outside", memory page, inline fact list, Account / Logout
- **Problems:**
  - **130 ListTiles in total**, no grouping headers inside the big card, no search, and Logout at the very bottom.
  - Each subtitle is 1-2 lines of dense jargon (BOQ, RA bills, RoDTEP, OLT alarms, EOT, PI).
  - The `${name} · <Role>` prefix is repeated on about 60 rows, which wastes the first 8-10 characters of every title on a 360 px screen.
  - Hinglish titles as listed above.
  - **Duplicates:** "Employees · hire AI staff" (266) and "${name} · Employee" (274) sit next to dozens of individual desk rows that belong inside Employees. Connectors (1288) duplicates the Connect tab. Hoola Network duplicates Today's Network section. "What Hoola has learned" duplicates Today's Learned. Memory appears twice: the memory page row (~1376) plus the inline "What Hoola remembers" fact list (~1385).
  - Every row has the same accent icon colour (C.accent), so no visual grouping. There are no Semantics.

### bazar_screen.dart (Connect tab)
- **What it is:**
  1. Title "Connectors" plus "$total plugins…" (331-333)
  2. search
  3. 5 filter chips
  4. TopPlugins rails
  5. CONNECT YOUR ACCOUNTS grid
  6. a Glass card of 8 rows: Hoola TV, Hoola Reels, Scroll report, Hoola Motion, Apps 1,600+, Public APIs 2,100+, Hoola Shopping, Spending limit, Add a shop (365-475)
  7. ALL PLUGINS · N as ExpansionTiles per category (481-508)
  8. a footer hint
- **Problems:**
  - The Connect tab mixes **entertainment and creation features** (TV, Reels, Scroll report, Motion) with connectors and with a money setting (Spending limit, 452).
  - The count line "$total plugins" sells volume, not help.
  - The filter chip names ("Hoola will do it", "Will read SMS") are unclear.
  - Category subtitles are 11.5 px faint (503).
  - The AppBar duplicates the count (517).
  - `linked ✓` (173).
  - The ExpansionTile icons use raw 0x1FFFB15C (498).

### top_plugins.dart, plugin_widgets.dart
- **What they are:** the curated rails on Connect, PluginGrid / PluginRow, and the badge widgets.
- **Problems:** 11.5 px subtitles (top_plugins ×3), 10.5 px badges (plugin_widgets 246, 309), 10 raw colours for badge states. They need a shared `StatusBadge(tone)`.

### employees_screen.dart (Profile > Employees, plus the SEO Desk)
- **What it is:** a hub grouped by department (206), then cards (`_card`, 168), then hire; this file also contains the SEO desk (574+) and other desks.
- **Problems:**
  - 2,367 lines mixing the hub with a full desk.
  - Inconsistent heading sizes display(14 / 15 / 16 / 17 / 20) for peer headings (298, 347, 436, 448, 478, 486).
  - Only 11.5 px tiny cases. 0 raw colours, which is good.
  - The department group header is display(15) with no count.

### employee_screen.dart (Profile > "Name · Employee")
- **What it is:** a 6-tab desk: Work / Inbox / Trusted / Team / Accounts / Job (89-96), scrollable tabs.
- **Problems:** six tabs on a phone, scrollable, so "Accounts" and "Job" are hidden off-screen at 360 px. `(band)` is Hinglish (268). Heading sizes 16 / 17 / 20 mixed.

### hoola_net_screen.dart (Profile > Hoola Network)
- **What it is:** 6 scrollable tabs: My ID / Connected people (n) / Inbox (n) / Conversations / Groups / Community (543-549).
- **Problems:**
  - Six tabs with counts in labels, which overflows on 360 px.
  - Hinglish CTAs: QR banaiye (204), Kaam do (1172), se banwaiye (672), Aapka (448).
  - Emoji: group emoji as leading at 26 px (505), `📄` / `🖼️` options (705), `📎` in previews (449), `Connected ✓` snack (258).
  - Message meta is 10.5 px (1012, 1031-1032).

### memory_page_screen.dart (Profile > Hoola's memory)
- **What it is:** an "About me" page plus switches.
- **Problems:** clean and consistent (12 / 13.5 / 16). Emoji `🕶` inside the help sentence (207). Duplicates the inline fact list on Profile.

---

## Information architecture

**Main (Profile) tab: about 130 entries.**
- One card of about 100 ListTiles: avatar, look, network, learned, rules, Employees hub, the Employee desk, ID Locker, then about 85 individual desks / sahayaks / Google apps / PC / Notebook / YouTube / App Check / Artifacts / Home / Connectors.
- About 20 more single-row cards.
- Briefing, language and voice, voice switch, Talk from outside, memory page, inline facts, Account / Logout.

Problems:
- No hierarchy.
- AI-employee desks are listed BOTH here and in Employees.
- Connectors are listed both here and on the Connect tab.
- The tab name "Main" means nothing, while the page says "Profile".

**Proposed structure:**
- Header: avatar card (name, look, voice)
- 6 group rows: **AI Employees** (the hub; desks live only there), **My Hoola** (look, rules, network, learned, memory), **Apps & accounts** (Google, email, PC, home: or move these to Connect), **Settings** (language, voice, briefing, outside channels, spending limit), **Privacy** (ID Locker, memory), **Account**
- Rename the tab to "You" or "Profile"

**Today tab: 16 sections.** Approvals come 4th. Employee / Network / Notebook / Learned are feature promotions, not today's state. Reminders, routines and lists are 3 near-identical cards.

Proposed order:
1. Greeting plus one-line status
2. **Needs you** (approvals and questions)
3. **Working now**
4. **Today** (calendar, reminders, routines)
5. Quick actions (one row)
6. Recap

Everything else goes to Profile or Connect.

**Connect tab:** mixes 4 kinds of thing:
- connectors (Apps 1,600+, Public APIs, plugins)
- Hoola features (TV, Reels, Scroll report, Motion, Shopping)
- a money setting (spending limit)
- shop onboarding

Proposed:
- Connect = "Connected" (her linked accounts first, with status), "Add a connection" (search, plus the top category rails)
- Move TV / Reels / Motion / Scroll report to Today quick actions or a Create area
- Move the spending limit to Settings > Money

---

## Top 10 design fixes for the core app, ranked by impact

1. **Collapse Profile's 130 rows into about 6 grouped rows; desks only inside Employees.** profile_screen.dart:219-1075, worst at 266-1288. Rename the tab "Main" to "Profile" or "You" (main.dart:466).
2. **Add a type scale to glass.dart** (T.title / T.body / T.label / T.caption, 12 px floor, max w700) and replace the 1,400+ ad-hoc sizes and w800 weights. Biggest offenders: home_sections.dart (16 sizes, 8.5 px at 733 / 844 / 893), today_screen.dart:745.
3. **Reorder and trim Today** to Needs you, Working, Today, Quick actions, Recap; move approvals to the top (today_screen.dart:157-238) and merge Reminder / Routines / Lists (today_screen.dart:386 / 607 / 779).
4. **Add surface and border tokens; kill the private palettes.** any_card.dart:29-32, chat_attach.dart:94-140, approve_sheet.dart:41 / 158, the three copied CTA gradients (main.dart:481, approve_sheet.dart:204, any_card.dart:296), home_sections.dart (115 raw colours).
5. **Finish the English pass on literal strings:** today_screen.dart:44 greeting, profile_screen.dart:223 / 230-231 / 956 / 1395 and the "sahayak" titles, avatar_setup_screen.dart:441 / 496 / 511 / 535, hoola_net_screen.dart:204 / 448 / 672 / 1172, live_voice_screen.dart:513, employee_screen.dart:268, chat_screen.dart:674; and voice_screen.dart:390 `'SANTOSH'` becomes `app.aName`.
6. **Split Connect into "Connected" and "Add"**, and move TV / Reels / Motion / Scroll report and the spending limit out (bazar_screen.dart:365-475).
7. **Accessibility:**
   - give Press a semantic label and button role (glass.dart Press)
   - make chip and tile targets at least 44 px (today_screen.dart:243-260, hoola_net tabs)
   - add a visible "Talk" label under the orb (main.dart:472)
8. **Replace emoji chrome with icons and badges:** hoola_cards.dart:22-26, goal_card.dart:14 / 184-187, home_sections.dart:228-235, chat_screen.dart:596 / 739, kaam_sheet.dart:103, calls_sheet.dart:101, hoola_net_screen.dart:449 / 505 / 705.
9. **One card shell for chat:** move the inline cards (chat_screen.dart:2283-2791) onto any_card / hoola_cards, and make one `HomeCard` for the home_sections sections.
10. **Cut 6-tab screens to at most 4 visible:** employee_screen.dart:89-96, hoola_net_screen.dart:543-549. Merge the two voice screens' caption UI (voice_screen.dart:385 vs live_voice_screen.dart:430). Delete the unused Santosh3D (santosh3d.dart:52).

## 5 worst screens

1. **profile_screen.dart:219-1475**: about 130 flat rows, Hinglish, duplicates, Logout last.
2. **home_sections.dart** (Today's sections): 115 raw colours, 59 tiny texts down to 8.5 px (733 / 844 / 893), 16 font sizes.
3. **today_screen.dart:157-238**: 16 sections, approvals buried, Hinglish greeting (44), hard-coded gradients (204-225).
4. **bazar_screen.dart:331-510** (Connect): mixed purposes, volume-first copy.
5. **hoola_net_screen.dart:543-549**: 6 tabs, Hinglish CTAs, emoji, 10.5 px meta (1012-1032).

Runners-up:
- **chat_screen.dart**: 2.8k lines, about 10 inline card styles.
- **avatar_setup_screen.dart**: about 8 decisions on first run.
