# Hoola phone app design audit, batch B (63 files in lib/ui)

Read-only, judged from source (Flutter cannot run here). Design system: `lib/ui/glass.dart` (class `C` tokens, `display()` = Sora, Manrope body, `Glass` / `Aurora` / `Press` / `GradientButton` / `Pill` / `Caption`).
Numbers come from scripted greps plus spot reads. "w8" = lines using w800/w900. "small" = fontSize below 12. Line numbers are first hits, not every hit.
FROZEN (owner): `pc_screen.dart` and `hoola_pc_screen.dart`. They are audited here but must not be changed.

Severity: 1 = cosmetic, 2 = visible inconsistency, 3 = should be fixed first.

| file | what it is | layout | top issues (line) | sev |
|---|---|---|---|---|
| enterprise_screen | Connect your ERP / CRM systems (enterprise roles) | single ListView form + Glass | Hinglish labels: "Apne system jodiye", "API ka address", "Key kaisi hai" (251, 260). Radius 8 is a one-off. No Aurora (other desks have it). | 2 |
| eventplan_screen | Event Sahayak desk + event page + 3 chat cards | ChoiceChip row in horizontal ListView (280: Today/Events/Vendors/Rules) | fontSize 11 (573, 675, 751, 871). w800 x7 (201, 239, 497, 651). '⚠ $w' emoji warnings (510, 516, 518). Bare full-screen spinner Scaffold (481). Title mixes Hindi brand + English ("Event Sahayak"). | 2 |
| feedback_screen | Feedback / reviews desk + reply / survey / note cards | ChoiceChip Wrap inside the ListView (Today/Themes/Reviews/Survey) | fontSize 11.5 (197, 331, 369, 431). w800 (229, 287, 409, 604). ★ glyph strings (26, 213, 296). Title "Feedback sahayak" uses lowercase s (other desks write "Sahayak"). | 2 |
| filmdesk_producer | Producer page: Script/Shots/Schedule/Money/Sales/Delivery | ChoiceChip tabs (68) | Hinglish label "Contract ki shart" (285). Otherwise clean, fonts 12.5 and up. | 1 |
| filmdesk_screen | Film desk + project page + cards | ChoiceChip row (287) | Hinglish tab "Filmein" (287). fontSize 11 (124, 143, 494, 506). ✓/⚠/✗ glyphs inline (701). | 2 |
| finance_screen | Financial analyst desk | DefaultTabController + TabBar (39/45: Accounts/Cash/Dues/Loan / Tax) | fontSize 11.5 (216, 240, 473). Radius 4 is a one-off. No loading indicator found (0 spinners), so it relies on empty Glass. | 2 |
| fleet_screen | Fleet desk + vehicle page + spend / trip / alert cards | ChoiceChip row (399) | w800 x8 (211, 243, 344, 376). ⚠ / ⛔ emoji in warnings (773, 840, 841). fontSize 11 (784). | 2 |
| forms_screen | Google Forms list + FormCard | list | Clean. Error handling is present. Minor: uses a plain list with no empty-state art. | 1 |
| franchise_screen | Franchise desk + statement card | ChoiceChip Wrap (Today/Outlets/Royalty/Licence + audit) | "Franchise sahayak" lowercase (title). fontSize 11.5 (280). No error state (0 error lines). | 2 |
| frontoffice_screen | Hotel front office: availability, booking, folio, report | ChoiceChip tabs (419) | fontSize 10.5 / 11 cluster (235, 261-263). w800 x10 (78, 260, 279, 386). 1,139 lines in one file. ⚠ emoji (953, 1029). | 2 |
| game_assets_screen | Game asset approvals | list | Radii 8 and 10 mixed. fontSize 11.5 (158). | 1 |
| game_bible_screen | Game Bible (names / numbers) | list | Raw Color (30). Radii 5 and 7 are off-scale. | 1 |
| game_desk_screen | Game Desk home + game list | list + GameStudioList | Three radii (8, 12, 20). fontSize 11.5 (157). | 1 |
| game_qa_screen | QA bot runs + bugs | list | Clean. | 1 |
| game_release_screen | Release builds / stores | list | Clean. | 1 |
| game_roles_screen | 10 role screens in one file (Worlds, Physics, Audio, Haptics, Net, ...) | 10 ListView screens, 6 Aurora | 1,241 lines. ✓ / ✕ prefix glyph strings (36, 38, 322, 518). fontSize 11.5 (32, 324, 530, 881). The screens are near copies of each other and should share one role-screen scaffold. | 2 |
| game_studio_screen | One game's studio project (board, versions, report) | list | ✓ / ✕ / ○ status glyph text (272). Otherwise consistent. | 1 |
| graphic_screen | Graphic designer desk + job page + cards | ChoiceChip row (336) | Emoji chrome ⛔ ⚠️ ℹ️ 🖨 🔤 (442, 708, 713). fontSize 11 (150, 292, 493, 603). w800 (301, 425, 481, 693). | 3 |
| gst_screen | GST sahayak: clients, 2B recon, returns, notices | DefaultTabController + TabBar (Aaj/Clients/Returns/Notice) | Hinglish tab "Aaj" and dialog title "Client ko message". Lowercase "GST sahayak". w800 (167, 319, 598, 695). fontSize 11.5 (615, 899). | 2 |
| guru_screen | Personal tutor + learner page + report card | ChoiceChip Wrap (Study/Practice/Language/Progress) | No error state (0). w800 (76, 262, 419). fontSize 11.5 (86, 375). | 2 |
| gyaan_screen | Knowledge sources | list | Label "<name> ka gyaan" is Hinglish. fontSize 11.5 (345). | 1 |
| handoff_screen | Consents / AA / ABHA / DigiLocker / ONDC / outside agents | DefaultTabController + TabBar (366) | w800/w900 x16, the heaviest in the batch (108, 109, 125, 210). '✓' and '✗' strings (688, 734). No spinner beyond one. | 3 |
| helpdesk_screen | IT helpdesk desk + ticket page + cards | ChoiceChip Wrap (Aaj/Tickets/Devices/Suraksha/...) | Hinglish tabs "Aaj" and "Suraksha", plus "Mail / message ka text", "subah ka note", "Error ka text" (287, 352, 552). fontSize 11.5 (389, 585). | 3 |
| home_devices_screen | Ghar: IR / AC / TV devices | list | fontSize 11 (159, 430, 515). Fine otherwise. | 1 |
| homestay_screen | Homestay host desk + booking page + cards | ChoiceChip row (581) | Tabs "Aaj / Mehmaan / Hisaab / Niyam" (581). "⚠ Khaali: $b" (959). "Subah ka note (HH:MM)" (198). fontSize 11 cluster (399, 420, 437, 448). Radius 6 is a one-off. | 3 |
| hoola_business_screen | Hoola Network business directory | DefaultTabController + TabBar (188) | Tab "Dhoondhiye" sits next to "My business" (188). '🏢 verified' emoji badge (206, 242). | 2 |
| hoola_media | Shared media tile / seen / insight / from-to widgets | widgets (no screen) | 9 raw Color(0x..) (136, 162, 188, 234) and 8 Colors.white/black. fontSize 10.5 (143, 169, 192, 309). Three radii (8, 12, 14). Sample string "Kunal ka Raju → aapka Santosh". | 3 |
| hoola_pc_screen | Hoola's own cloud PC (FROZEN, do not change) | single ListView | All copy is Hinglish (10, 70, 72, 73, 82; title "Hoola ka PC"). fontSize 11 (155). | 3 (frozen) |
| hoola_samaj_screen | What Hoola learned + Community list / detail | list | 15 emoji lines: community emoji leading at fontSize 24 (73, 203, 217). The emoji acts as the icon (chrome). | 2 |
| id_locker_screen | Pehchaan / ID Locker | list | fontSize 11.5 (82, 194). Clean otherwise. | 1 |
| influencer_screen | Influencer manager desk + deal page + cards | ChoiceChip row (370) | fontSize 11 (191, 233, 348, 555). w800 (84, 198, 296, 344). ✗ glyph (86). | 2 |
| insurance_screen | Insurance assistant + client page | ChoiceChip Wrap (Premium/Customer/Claim) | No error state (0). w800 x7 (166, 167, 215, 259). fontSize 11.5 (151, 293, 345, 406). | 2 |
| interior_screen | Interior Sahayak desk + project page + quote / order / change cards | ChoiceChip row (344) | Raw Color (999). ⚠ glyph warnings (640, 735, 834, 1013). fontSize 11 (752, 848, 985, 1010). w800 x8. | 2 |
| ispnoc_screen | ISP NOC desk + fault page + cards | ChoiceChip Wrap (Aaj/Alarm/Tickets/Network/...) | 1,255 lines. Hinglish tab "Aaj" plus "Light ka hisaab", "Subah ka note", "Script ka link copy", "Alarm ki timeline", "${n} mile" (436, 520, 658, 752, 1236). fontSize 11 (754, 1029, 1057, 1062). | 3 |
| itadmin_screen | IT Admin Sahayak + person / guide pages + review | ChoiceChip Wrap (Today/Licence/Log/Guides/...) | w800 x14 (74, 123, 213, 286). fontSize 11 (441, 484, 868, 934). Radii 10 and 12 mixed. | 2 |
| jaanch_screen | App check (REA) entry | single list | w800 (72, 117). Small and clean. | 1 |
| kalam_screen | Content writer (Write/Article/Ideas/Voice/Niyam) | DefaultTabController + TabBar (98) | Tab "Niyam". Labels "FSSAI licence no. (khane ki cheez)", "Business ka pata", "Juda hai" (153, 672, 689). Dialog "Pehli line #Ad (ASCI niyam)". 1,267 lines. fontSize 11.5 (1092, 1094). | 3 |
| kb | KbField keyboard-safe field helper | widget | Clean shared helper. | 1 |
| keep_alive | "Keep Hoola running" battery / OEM guide | stepper list | Title "${aName} band na ho" and buttons "Theek karo" / "Ho gaya" (Hinglish). 7 raw Color (60, 67, 194, 220). Radii 14 / 16 / 22. | 3 |
| kharcha_screen | AI cost / monthly limit | list | w800 x5 (125, 144, 159, 192). Radius 3 is a one-off. | 1 |
| kitab_screen | Kitab Sahayak (author / book desk) + book / chapter pages | ChoiceChip row (212) | Tabs "Aaj / Kitaabein / Niyam" (212). "Subah ka note" (184). fontSize 11 (206, 397, 586, 613). No error state. | 3 |
| legalres_screen | Legal research (matter, memo, old -> new mapping) | ChoiceChip Wrap (Matter/Saved/Old -> new/Rules) | Strings "nahi mila" and "[citation chahiye]" shown to the user. fontSize 11 (286, 366, 516, 537). No error state. Tab text "Old -> new" uses ASCII ->. | 2 |
| lekhak_screen | Typist and translator (Write/Translation/Improvement/Paper/Rules) | DefaultTabController + TabBar + SegmentedButton (421) | 6 raw Color (693, 694, 847, 849). Radii 10 and 12. | 2 |
| lock_safe | Lock-screen safety banner + maker steps | widget | 5 raw Color (75, 133, 165, 173). fontSize 10.5 (150). Three radii (12, 14, 22). 🔒 inside copy (37). | 2 |
| logistics_screen | Logistics Sahayak + shipment page + EWB / update cards | ChoiceChip Wrap (Today/Shipments/Party/Rules) | w800 x7 (139, 290, 509, 661). No error state. | 2 |
| maps_card | Maps places chat card | card | "Khula hai" (36). ★ rating glyph (35). fontSize 11.5 (72). | 1 |
| market_screen | Compare quotes / standing orders / promo cards | list + cards | fontSize 11 (130, 196, 360, 364). w900 (1 line). 'chosen ✓' pill (175). No error state. | 2 |
| mcp_screen | MCP servers + Composio apps directory | ChoiceChip category filter + list | 12 lines with fontSize under 12 (311, 363, 367, 370), the most in the batch. Radius 26 is a one-off. ⚠ caution (707). | 2 |
| mcp_tools | MCP tool on/off sheet (showMcpTools) | bottom sheet | Radius 24 differs from mcp_screen's 26. Clean otherwise. | 1 |
| motion_screen | Hoola Motion (video jobs + player) | list + chips | 11 raw Color (158, 160, 181, 182). Five radii (4, 8, 10, 12, 18). Emoji chips "📱 Reel 9:16" / "🖥 Wide 16:9" (321-327). '🎬' snack (87). | 3 |
| motiondesk_screen | Motion designer desk + job page + cards | NavigationBar (359-367, the only bottom-nav desk) | Destinations "Aaj / Kaam / Niyam" (363-367). "Extra round ka daam (₹)" (329). fontSize 11 (434, 655-657). ⚠ / ✓ glyphs (434, 497, 657). | 3 |
| mshop_screen | Mobile repair shop (Today/Repair/Recharge/Warranty/Rules) | DefaultTabController + TabBar (85) | 1,342 lines. w800 x14 (97, 130, 132, 202). Raw Color (476). "Phone taiyaar hai" (1250). | 2 |
| niryat_screen | Export desk (Today/Shipments/Buyers) | ChoiceChip Wrap | "Niryat sahayak" title (Hindi name, lowercase s). No error state. | 2 |
| notary_screen | Notary desk (Aaj/Documents/Register/Apostille/Niyam) | ChoiceChip tabs (474) | Hinglish tabs. "Kis document ka stamp?", "Kis act ki fee?", "Final print ka card", "Subah ka note" (235, 404, 412, 426, 671). ⛔ / ⚠ / ℹ emoji levels (654). fontSize 11 (290, 360, 462, 468). | 3 |
| notebook_screen | Notebooks (NotebookLM-like): list, detail, sources, studio | TabBar (506: Sources/Chat/Studio) | 2,239 lines, the largest. 13 raw Color in a studio palette that is not C (34-40). Seven radii (4 to 24). Emoji picker and emoji as notebook icon at fontSize 64 (65, 114, 263, 339). fontSize 10.5 (310, 672, 731, 1074). | 3 |
| notebook_viewers | Notebook output viewers (audio, video, slides, mind map, flashcards...) | multiple screens, 10 Aurora | 5 raw Color (568, 796, 878, 1022). Seven radii (4 to 28). w800 x14 (116, 128, 167, 186). Emoji chrome ❓ 💬 ✓ ↻ (455, 876, 991). | 3 |
| office_screen | Office manager (Aaj/Goods/Repair/Renewal/Team/Kharcha/Note/Niyam) | DefaultTabController + TabBar (119), 8 tabs | Tabs "Aaj / Kharcha / Niyam". "Parts ka intezaar", "Subah ki list kab" (21, 213, 255, 277, 556). With 8 tabs the bar must scroll at 360 px. | 3 |
| operator_screen | Computer Operator (frame, ask / task cards, live screen) | list | Raw Color (101). fontSize 11.5 (257, 275, 320, 398). Radii 12 and 14. | 1 |
| patrakar_screen | Journalist desk (Aaj/Stories/Source/Shikayat/Niyam) | ChoiceChip tabs (416) | Hinglish tabs "Aaj / Shikayat / Niyam" (416) and copy (291, 327). ⛔ / ⚠ glyph lines (90, 92). fontSize 11 (354, 549, 735, 829). No error state. | 3 |
| payroll_screen | Payroll officer (Today/Log/Salary/Rules) + pay run | DefaultTabController + TabBar (76) | w800 (135, 296, 406, 560). No error state. fontSize 11.5 (602). | 1 |
| pc_screen | Mera PC (FROZEN, do not change) | single list | Title "Mera PC". About 20 Hinglish strings ("PC jodiye", "Kuch nahi mila. Doosre shabd try kijiye.", 22, 103, 143-146). fontSize 11 (281, 302, 359). | 3 (frozen) |
| phone_hoola | Hoola on the phone (bubble, widget, permissions) + AppUpdater | list | Raw Color (164, 267). 🎙 inside copy (137, 166). Title "Phone mein Hoola" (Hinglish). | 2 |
| phonedoc_screen | Phone Doctor + case page | list | Hint "phone mein kya dikkat hai?". Radius 16. Fonts 12.5 and up. | 1 |
| photo_card | Made-photo chat card | card | fontSize 11 (135). 2 Colors.* literals. | 1 |

## Shared patterns

**The common desk skeleton** (about 45 of the 63 files):
1. A file header doc comment, then about 7 private helpers re-declared in each file: `_s` (42 files), `_list` (41), `_strs` (21), `_m` (19), `_rs` (9), `_snack` (49) and a `_form(...)` AlertDialog builder (20). There is no shared desk kit, so every desk copies these.
2. `XxxScreen` (StatefulWidget, `int _tab = 0`, `_load()` from `app.api`) with `Scaffold(backgroundColor: C.bgTop, appBar: AppBar(transparent, title, actions: [refresh]))`. 26 of 63 files never use `Aurora`, while others wrap the body in it, so the backgrounds differ between desks.
3. Tabs in four different ways:
   - ChoiceChips in a 44 px horizontal ListView (eventplan, filmdesk, fleet, graphic, homestay, influencer, interior, kitab, notary, patrakar, frontoffice)
   - ChoiceChips in a `Wrap` inside the scrolling list (feedback, franchise, helpdesk, insurance, itadmin, ispnoc, legalres, logistics, niryat, guru)
   - `DefaultTabController` + `TabBar(isScrollable)` (finance, gst, handoff, kalam, lekhak, mshop, office, payroll, hoola_business, notebook)
   - `NavigationBar` (motiondesk only)
4. `RefreshIndicator` -> `ListView(padding: 16,8,16,40..90)` of `Glass` cards, one `XxxPage` detail screen, and two to five chat cards (`XxxCardCard`, `XxxNoteCard`, `...BookingCard`) in the same file.
5. Warnings and blocks drawn as `Text('⚠ $w', style: TextStyle(fontSize: 11..12.5, color: C.warn))`, repeated in about 20 files. There is no shared warning-row widget.
6. Loading = a bare `CircularProgressIndicator` (often a whole Scaffold, e.g. eventplan:481). Empty and error states are ad-hoc text. These desks have no error state at all: franchise, guru, insurance, kitab, legalres, logistics, market, notary, patrakar, payroll.

**Typography drift:** fontSize 11 and 11.5 are standard in most desks (40+ files have text under 12px; 10.5 in frontoffice, hoola_media, lock_safe, notebook_screen). w800 is common (handoff 16, itadmin / mshop / notebook_viewers 14). Few desks use `display()`: 30 of 63 files.

**Colour:** most desks are clean `C.*`. Raw colours concentrate in the non-desk widgets: notebook_screen 13, motion_screen 11, hoola_media 9, keep_alive 7, lekhak 6, lock_safe 5, notebook_viewers 5.

**Radii:** there is no radius token. Values in use are 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26 and 28.

**Naming:** "Sahayak" / "sahayak" casing is inconsistent (Event / Interior / Kitab / Logistics / IT Admin "Sahayak" vs Feedback / Franchise / GST / Niryat "sahayak").

## Dead files

None. Every file has a caller:
- most open from `profile_screen.dart`, `employees_screen.dart` or `chat_screen.dart` (cards)
- `mcp_tools` is used by `mcp_screen`
- `kb` is used by `hoola_cards` and `ask_form_card`
- `game_*` sub-screens open from `game_studio_screen` / `game_desk_screen`
- `filmdesk_producer` opens from `filmdesk_screen:363`
- `NbAudioScreen` and the other viewers are routed inside `notebook_viewers:257`

## Hinglish count

- **Heavy (Hinglish tab labels or 3+ user strings): 15.** pc_screen and hoola_pc_screen (both frozen), homestay, notary, patrakar, office, kitab, motiondesk, helpdesk, ispnoc, kalam, enterprise, keep_alive, gst ("Aaj" tab, "Client ko message"), hoola_business ("Dhoondhiye").
- **Light (1-2 strings): 11.** filmdesk ("Filmein"), filmdesk_producer, gyaan, hoola_media, maps_card, mshop, phone_hoola, phonedoc, legalres, niryat (title), feedback (title).
