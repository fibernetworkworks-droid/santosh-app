# Hoola phone app - design audit (12 Nov 2026, v0.857.0)

Owner ask: "NOW LETS WORK ON APP SIDE DESIGN FIRST CHECK ALL EXISTING SCREENS IN EXISTING HOOLA APP".
Read from SOURCE only (Flutter cannot run in the sandbox) - nothing here was seen on a real screen.

Scope: 221 Dart files in lib/ui (+ studio/), 129k lines, 316 screen / page / sheet classes.
Files: 01_core.md (shell, Today, Chat, Talk, Connect, Main, Employees, Network), 02-04 = every desk screen.

## Numbers (scripted over lib/ui)
- Font sizes in use: 29 different values (8.5 - 64); 679 texts under 12px; 11.5 / 12 / 12.5 dominate.
- 778 w800/w900 weights; 680 raw Color(0x..) + 412 Colors.* beside 7,034 C.* tokens.
- 24 different corner radii (2 - 999).
- 375 emoji in UI code; ~35 files with visible Hinglish (English waves missed them); tabs split "Today / Rules" vs "Aaj / Niyam".
- Shared desk code: none. `_s` re-declared in ~116 files, `_snack` ~95, `_list` ~91, `_form` ~57.
- Tabs built 4 ways (ChoiceChip row, ChoiceChip Wrap, TabBar, NavigationBar).
- No desk has an error + Retry state: a failed first load = spinner forever + raw exception snackbar.
- ~36 desks never use Aurora (look flat next to the rest).
- No screenshot / golden pipeline for the Hoola app itself in CI.

## Root cause
glass.dart has colour tokens and two fonts but NO type scale, radius, spacing, surface or state tokens and NO shared desk
scaffold - so every one of ~150 screens invented its own.

## Biggest problems (impact order)
1. Main (Profile) tab = ~130 flat rows (one card ~100 rows), duplicates Employees / Connect / Today, Logout last
   (profile_screen.dart:219-1475); the tab says "Main", the page says "Profile".
2. No type scale: 8.5px labels (home_sections.dart:733/844/893), 16 sizes in one file.
3. Today = 16 sections, approvals 4th (today_screen.dart:157-238), Hinglish greeting (44), "1 tasks" (100).
4. Connect tab mixes connectors, Hoola features, a money setting and shop onboarding (bazar_screen.dart:331-510).
5. ~150 desks: same skeleton, zero shared code, no error state, mixed tabs / backgrounds / radii.
6. Hinglish leftovers + one mistranslation (rentdesk tab "Yes" for "Haan", rentdesk_screen.dart:340); "SANTOSH" shown
   to users (voice_screen.dart:390).
7. Emoji as status / chrome (~16 desk files + core cards).
8. Accessibility: Press has no Semantics role, ~32px chips, Talk orb has no visible label.
9. Studio has its own palette `SC` that drifts from C (studio/studio_kit.dart:17-19).
10. Worst desks: app_design_screen, notebook_screen, motion_screen, hoola_media, browser_live, deal_screen,
    rentdesk, tourguide, photoassist, homestay, notary, courier, devops, scroll_screen.

Dead: agents_screen.dart (no caller), santosh3d.dart likely unused. Frozen (do not change): pc_screen.dart,
hoola_pc_screen.dart.

## Proposed order of work (needs the owner's GO)
- D0 screenshot job in CI (golden tests / emulator walk) so every later step is SEEN, not guessed.
- D1 glass.dart tokens: type scale (12px floor, w700 max), radius 8/12/16/24/pill, spacing, surfaces, CTA gradient.
- D2 DeskScaffold + shared helpers (tabs, loading, error + Retry, empty, warning row, confirm dialog).
- D3 the 5 tabs redesigned: Today (Needs you -> Working -> Today -> Quick actions -> Recap), Chat cards on one shell,
  Connect (Connected / Add), Main -> Profile (~6 groups; desks only in Employees).
- D4 move every desk onto DeskScaffold, worst first; English + icons in the same pass.
