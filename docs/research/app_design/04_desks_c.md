# Hoola phone app - design audit, batch C (lib/ui p..y + lib/ui/studio)

Method: read-only source scan (Flutter cannot run here). Per file: class names, build(), tab labels, and counted
metrics - raw `Color(0x..)`, text under 12px (`fontSize` 8-11.x, or `body(9-11.x)` in Studio), `w800/w900`,
ChoiceChip / TabBar, emoji glyphs, Hinglish string literals (a Hindi-word list matched against quoted strings),
empty / loading / error handling, and whether any other file in lib/ references the file's classes.
Line numbers are the first few hits, not every hit. Severity: 3 = fix first, 2 = noticeable, 1 = polish.

Legend: "small N" = count of sub-12px font sizes; "w8/9 N" = w800+w900 uses; "raw N" = raw Color literals;
"HG N" = Hinglish literals.

## Per-file table

| file | what it is | layout | top design issues (line numbers) | sev |
|---|---|---|---|---|
| photoassist_screen | Photo Sahayak desk (photographer's assistant) + shoot page | ChoiceChip tab row (268: Aaj / Shoots / Studio / Niyam) | HG 16 - tab 'Aaj', 'Niyam'; captions 139 'HOLD KHATAM HONE WALE', 154 'Khatam', 155 'Jagah', 169 'Khaali hai?'; ALL-CAPS Caption headings 136-145; small 6 (11.5 @192, 262, 429, 641); raw colour 395; load error = raw `$e` snackbar x7, spinner forever | 3 |
| photos_screen | Google Photos picker card + screen | list | clean; only basic empty text; no error state beyond snack | 1 |
| pidesk_screen | PI (investigator) desk + case page | ChoiceChip tabs (285: Aaj / Cases / Niyam) | HG 8 (202 '1930 / CYBERCRIME REPORT BAAKI', 203 'CONSENT BAAKI', 272 'Badlo', 285 'Aaj'); ALL-CAPS mixed headings; small 3 (11 @110, 701); w8/9 7 | 2 |
| podcast_screen | Podcast producer desk + episode page | ChoiceChip tabs (413: 7 tabs Aaj...Niyam) | HG 12 (174 'RELEASE BAAKI', 223 'Naam', 257 'Details hatao', 334 'Track jodo'); 7 tabs = horizontal scroll at 360px; emoji glyphs as status (501 '✗') x6 | 2 |
| postgres_screen | Her Postgres DB link + write card | form + list | small 1 (103); radius 12 one-off; mostly fine | 1 |
| prayog_screen | Prayogshala 3D labs catalogue | list (families) | clean English; no small text; fine | 1 |
| procedures_screen | "Learned jobs" (procedures) list + card | list | small 7 (11 @190, 199, 221); raw colour 264; radii 6 / 8 mixed; w8/9 6 | 2 |
| product_screen | Product manager desk + opportunity page | ChoiceChip tabs (435: Today...Rules) | 1021 lines; w8/9 9; raw colour 147; small 143, 813; '★' glyph 206 | 2 |
| propagent_screen | Property agent desk + listing page | ChoiceChip tabs | 987 lines; w8/9 7; '⚠' glyph 237; HG 1 ('Page band' 508); small 912, 940 | 2 |
| publicapis_screen | Public APIs catalogue (2,100+ APIs) | search + chips + list | raw colour 259; small 3 (201, 286, 301=11) | 1 |
| qa_screen | QA Sahayak (app tester) + target page | ChoiceChip tabs | w8/9 15 (highest in batch); small 6 (319, 564, 673, 843); radii 10 / 14 | 2 |
| reels_screen | Hoola Reels (shared reels -> notes), saved reels | list + detail | raw 3 (434, 435, 618); small 4 (359, 409, 630 = 11); radii 12/14/26; HG 5 ('Kab yaad dilaun?' 161; 'pata_nahi' keys 329-348 - check they are not displayed) | 2 |
| rentdesk_screen | Property manager (rent) desk | ChoiceChip tabs (340: Aaj / Units / **Kirayedar** / **Yes** / Repair / Niyam) | WORST HG: 25+ literals - 'Naam' 116/177, 'Jodo' 125/180, 'Baaki' 238/284, '... din' 228/235, '$start se $end' 281, 'Repair darj' 303, 'Badlo' 325, 'Vendor ko WhatsApp' 417, 'Kab se' / 'Kyon' 480/488; tab 'Yes' is a broken translation of 'Haan' (cards waiting); w800 on every row title (254, 278, 407); small 5 (595, 603=11, 632, 696) | 3 |
| samudaay_screen | Community manager (Telegram groups) | ChoiceChip tabs (5 chip uses) | 923 lines; w8/9 11; '⚠' glyph 822; small 414, 442; own `_Head` widget duplicating Caption | 2 |
| screen_link | Hoola Screen (TV / monitor pairing) | single page | w8/9 5 in a 205-line file; no loading indicator at all | 1 |
| scroll_screen | Reel-app screen-time tracker + chart | dashboard (custom bars) | raw colour 12 (159, 160, 238...) - most in a non-studio file; small 17 incl. fontSize 10 (219, 245, 336-340 hour axis) and 10.5 (489); radii 3/4/5/6; w8/9 11 | 3 |
| seo_screen | SEO employee desk + SeoCard | sections list | small 5 (194, 208, 289, 330 all 11.5); no tab row although long | 1 |
| seva_screen | Customer support desk + ticket page | ChoiceChip tabs (528: 6 tabs) | 896 lines; small 340, 490, 825; '...' glyph 1; otherwise consistent | 1 |
| shaadi_screen | Wedding planner desk + wedding page | ChoiceChip tabs (217) + 8-tab inner row (625) | 8 inner tabs overflow 360px (scroll row); small 4 (462, 549, 782 = 11); w8/9 7 | 2 |
| sheets_screen | Google Sheets card + list | list | clean | 1 |
| shikayat_screen | Complaint handler desk (Seva suite) | ChoiceChip tabs | 1026 lines; raw `$e` snack x10; small 297, 331, 612, 752; own `_SummaryTile` | 2 |
| shiksha_screen | Education desk + paper page | ChoiceChip tabs | w8/9 9; small 197, 398 | 1 |
| shodh_screen | Research assistant + project page | list + detail | small 100, 267; fine | 1 |
| shop_screen | "Order karo" (shopping sites up to payment) | single list | header comment Hinglish; small 144; fine | 1 |
| shopping_screen | Orders + MCP tokens for Claude / ChatGPT | list | raw colour 149; uses "Santosh" internal name in comments only | 1 |
| site_blog | Website blog page | list + editor | HG 1 ('Hatao (chhupao)' 135) | 1 |
| site_dash | Website dashboard (visits / orders) | dashboard + custom painter | small 4 (115, 117, 119 = 11, 195); HG '$n din' 163; radii 2/3 | 2 |
| site_hosting | Launch / DNS / domain / care cards + panels (8 classes) | cards | 830 lines; small 7 (288, 322, 539, 627); emoji '🌐' as list bullet 65; no AppBar (embedded) | 2 |
| site_screen | Website builder home (TabBar: My websites / 'Ideas (1 lakh)') + stages / board / leads | **TabBar** (429) - unlike the desks | 1116 lines; raw 5 (90, 118, 134); radii 8/12/99; 'Ideas (1 lakh)' Indian-English; HG 'Mana' 366, 'Sab' 546, 'Hatao' 676, 'Badlo' 760; '✓' 94 | 3 |
| site_spec | Website spec card (architect) | card | HG 'Badlo' 47 | 1 |
| sitesup_screen | Construction site supervisor desk + site page | ChoiceChip tabs | HG 4 ('Look-ahead din' 224, 'Beldar rate / din' 226, 'Din (7/28/56)' 461); '⚠' 401; small 163, 648, 764 | 2 |
| slides_screen | Google Slides card + list | list | clean | 1 |
| society_screen | Housing society manager + flat page | ChoiceChip tabs (593: 8 tabs) | 1142 lines (largest); 8 tabs; small 7 (402, 535, 575, 979); w8/9 10; HG 'Band' 188, 'din' 418 | 2 |
| studio_screen | Barrel: re-exports studio/* | - | 7 lines; not a screen (fine) | 1 |
| telecall_screen | Telecaller desk | **TabBar** (153 Today / Log ...) + ChoiceChips inside | mixes TabBar and ChoiceChip tab styles; raw `$e` snack x12 (most) | 2 |
| theka_screen | Contractor desk + project page | list + detail | HG 7 ('Kaam name' 81/95, '$x din' 118, 'Aaj' 184) | 2 |
| thok_screen | Wholesale trader desk + order card | list | HG 'Udhaar din' 133; small 193, 394 | 1 |
| tourguide_screen | Tour guide desk + booking page | ChoiceChip tabs (403: Aaj / Booking / Tour / 'Licence · Hisaab' / Niyam) | HG 22 ('Tour badlo' 167, 'Naam' 168, 'Hisaab' 235, 'Darj' 241); '⚠' 745; small 395, 640, 759, 813 | 3 |
| travel_screen | Travel agent desk + settings panel | sections | HG 'PLAN (DIN-BA-DIN)' 402, 'Din $n' 404, '$x din' 387; w8/9 6 | 2 |
| tv_screen | Hoola TV (live channels) + player | grid | raw 3 (162, 164, 477); small 188 (10.5), 231, 535; emoji flag '🌍' 137 | 2 |
| upi_result_card | UPI app's answer card after a payment | card | emoji status ✅/❌/⏳ as chrome; small 82, 110 | 1 |
| vakil_screen | Advocate desk + matter page | ChoiceChip tabs (401) | small 7 (104, 230, 295, 667 = 11); HG '$x din' 221 | 2 |
| video_editor | Video job card, player, editor screen | list + player | raw 266; radii 6/12/14; small 291, 636 | 1 |
| video_shrink | Shrink-video dialog (top-level fn, no public class) | dialog | small 130; reached via a function (2 importers), not dead | 1 |
| voice_engine_screen | Call voice engine picker | list | clean | 1 |
| voice_id_screen | Voice ID enrolment (who is speaking) | list + enrol page | clean, 3 ChoiceChips | 1 |
| voice_learned_screen | What Hoola learned from her calls | list | header comment Hinglish only; clean | 1 |
| wapsi_screen | Returns & refunds desk + return page | ChoiceChip tabs (325: Aaj / Returns / Refund / Niyam) | HG 6 ('Aaj' 181, 'Refund baaki' 197, 'Mana' 197, 'Badlo' 259); w900 711; w8/9 11; '⚑' 564 | 2 |
| warehouse_screen | Warehouse desk + bin page | ChoiceChip tabs | HG 'Niyam badlo' 313, 'Aaj' 335, 'Mana' 479, 'rakhna baaki' 533; small 343, 473, 635 | 2 |
| web_screen | In-app browser | WebView | no AppBar title/state; fine | 1 |
| youtube_screen | YouTube card + screen | list | raw 3 (26, 51, 168 incl. Colors.white 52); small 10.5 @52; radii 4/10/12 | 1 |
| studio/studio_kit | Studio's OWN design kit: `SC` palette, `sora()` / `body()` styles, sList/sMap helpers | kit | parallel token system: `SC.teal #5EEAD4` vs `C.teal #2DD4BF`, `SC.violet #C9BEFF` vs `C.violet #7C5CFF`, SC.card/field raw (17-19); `body()` defaults to **w600** so every studio text is semibold; raw 15 | 3 |
| studio/studio_home | Studio home (starters, projects, month meter) | list + hero | raw 9 (33, 35, 37...); body(10.5) 279; radii 2/12/16/18/20/24/999 (7 radii in one file); no Glass - own cards | 2 |
| studio/studio_new | New video screen | form | raw 12 (311, 317, 419); radii x7; HG 'band' 467 | 2 |
| studio/studio_project | Project (storyboard, timeline, shots) | timeline + cards | body(9) 526 and body(9.5) 486/494 (smallest text in batch, on a timeline); w8/9 11; radii x9 | 3 |
| studio/studio_approve | Price sheet / approval card | sheet | ALL-CAPS labels 204, 287; body(11.5) x5; HG 'Video banane ka kharcha' 206, 'Mana' 380 (on a money card) | 2 |
| studio/studio_audio | Audio + brand tabs | tabs inside project | 'LIP SYNC' / 'NARRATION' at body(10) 223-224; HG 'Logo badlo' 404; w8/9 7 | 2 |
| studio/studio_cast | Cast tab | grid | radii x6; fine otherwise | 1 |
| studio/studio_final | Final video screen | single | HG 'Link · 10 din' 182 | 1 |
| studio/studio_render | Render progress | stepper | labels 185 small; fine | 1 |
| studio/studio_shot | Shot editor | form | 'MODEL (AUTOMATIC)' body(10.5) w800 382; raw 257 | 2 |
| studio/studio_takes | Takes picker | grid | w900 294; '✓' 244 | 1 |

## Shared patterns

**The desk skeleton (≈25 of the files here, and the same in the rest of lib/ui):**
`Scaffold(backgroundColor: C.bgTop)` -> transparent `AppBar(title: '${aName} · <Role>', actions: [refresh])` ->
`Column[ SizedBox(height: 44, horizontal ListView of ChoiceChip tabs), if (_busy) LinearProgressIndicator(2),
Expanded(_d == null ? CircularProgressIndicator : RefreshIndicator(switch (_tab) {...})) ]`; tab 0 is
"Today"/"Aaj" (a summary `Glass` with the server's `say` line + "waiting for your yes" cards), the last tab is
"Rules"/"Niyam" (settings + "never" list). Inside each tab: `ListView` of `Glass` cards, `Caption` headings in
ALL CAPS, row titles in `w800`, meta lines at 12.5 / 11.5 in `C.muted` / `C.faint`, actions as `GradientButton` /
`GlassButton`. Each desk also exports 3-7 chat card widgets (`XCardCard`, `XNoteCard`, `XDayCard`) used by chat.
Reference instance: rentdesk_screen.dart 338-380.

**They do NOT share code.** Every desk file re-declares its own top-level helpers: `_s()` exists in 116 files,
`_list()` ~91, `_snack()` ~95, `_form()` (the text-field dialog) in 57, `_strs()` 41, `_n()` 28 - byte-identical
copies (compare society_screen 19-31, rentdesk_screen 18-30, vakil_screen 16-37). The tab row, the load / busy /
refresh scaffold and the "cards waiting" block are copy-pasted per desk. There is no `desk_kit.dart`. Only
glass.dart widgets (Glass, Caption, GradientButton, GlassButton, Pill) are shared.

**Consequences visible across the batch:**
- Error state: no desk has an error state. `_load()` catches and shows the raw exception text (`_snack(context, '$e')`,
  e.g. rentdesk 97-99); if the first load fails `_d` stays null and the spinner spins forever. 23/23 desks checked.
- Tab styles diverge: desks use ChoiceChip rows; site_screen and telecall_screen use Material `TabBar`; telecall mixes both.
- Tab counts of 6-8 (podcast 7, society 8, shaadi inner 8) depend on horizontal scrolling at 360px with no affordance.
- Sub-12px text is routine: 11.5 is the house "meta" size in almost every desk; 10-11 in scroll_screen, site_dash,
  vakil, rentdesk, Studio timeline (9 / 9.5).
- Emoji glyphs (⚠ ✓ ✗ ★ ⚑ 🌐 🌍 ✅) used as status chrome instead of icons in ~16 files.
- Studio is a separate design dialect: own `SC` palette (teal / violet differ from `C`), own `sora()` / `body()`
  styles with a w600 default, no `Glass`, 6-9 distinct corner radii per file (2 ... 999).

## Dead files

None. Every file's public classes are referenced elsewhere in lib/ (studio_screen.dart is an export barrel;
video_shrink.dart is reached through a top-level function, 2 importers). Only `studio_screen.dart` itself has no
own class.

## Hinglish counts (user-facing literals)

- Heavy (6+ literals): rentdesk_screen (25+), tourguide_screen (22), photoassist_screen (16), podcast_screen (12),
  pidesk_screen (8), theka_screen (7), wapsi_screen (6) = **7 files**.
- Light (1-5): reels, warehouse, sitesup, site_screen, travel, tv, society, studio_approve, vakil, thok,
  studio_new, studio_final, studio_audio, site_spec, site_dash, site_blog, propagent = **17 files**.
- Clean: the remaining ~37 files (notably all the Google suite cards, voice_* screens, seva, shikayat, shiksha,
  telecall, qa, samudaay, studio core screens).
Recurring leftovers: tab names 'Aaj' / 'Niyam' (photoassist, pidesk, podcast, rentdesk, tourguide, wapsi), action
'Badlo' / 'Jodo' / 'Darj' / 'Mana', unit 'din', 'Baaki'. rentdesk tab 'Yes' (340) is a mistranslation of 'Haan'.
