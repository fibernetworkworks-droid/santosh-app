# Hoola phone app design audit, batch A (63 files in lib/ui)

Method: source read only (Flutter cannot run here). Per file, scripted counts: raw `Color(0x..)` outside `C`, `fontSize` under 12, `w800`/`w900`, tab mechanism, emoji or symbol glyphs in strings, loading indicators, callers (grep of public classes across lib/). Then the files with the highest counts were read by hand. Line numbers are where the problem shows. Severity: 3 = visible, everywhere on the screen; 2 = noticeable; 1 = minor.

Design system reference: `glass.dart` has `C` tokens, `display()` (Sora), Manrope body via theme, and `Glass` / `Aurora` / `Press` / `GradientButton` / `GlassButton` / `Pill` / `Caption` / `Stagger`. There is NO radius scale, NO type scale (only `display(size)`), and NO desk/section/empty-state widget. That gap explains most of the drift below.

## Per-file table

| file | what it is | layout | top issues (line) | sev |
|---|---|---|---|---|
| ads_screen | Performance-marketer desk (Meta/Google ads) + chat cards | DefaultTabController + TabBar (4) | Tab labels Hinglish 'Hisaab', 'Niyam' (133,136); 'Meta se lao' / 'Meta jodo (Niyam)' (184), 'Juda hai' (711), 'Facebook se jodo' (720), 'Hatao' (734), 'Token se jodo' (747); ⛔/⚠ glyph chrome (573); 3 sizes <12 | 3 |
| aftersales_screen | After-sales / AMC desk (visits, machines, team) | ChoiceChip tabs (426) + detail pages | 13x w800 (e.g. 284,324); 5 Aurora instances; ✓ in button labels (932,946); 1,513 lines, monolith | 2 |
| agents_screen | Agent catalogue browser (tiers / fields) | list + chip filters | **DEAD: AgentsScreen has no caller in lib/**; 'Sab tiers' / 'Sab fields' (98,112); raw Color; radii 14/16/22 | 2 |
| app_android | Android build / data / store panels inside App Studio | panels | 11 sizes <12; ★☆ / ✓○ text glyphs as status (28,524,677); radii 8/10/12 | 2 |
| app_components | App Studio components panel | panel | Clean; no loading/empty state | 1 |
| app_connect | App Studio connectors panel | panel | Clean; no loading/error state | 1 |
| app_design_screen | App Studio screen (plan, looks, screens, boards) | TabBar (372) + ChoiceChip (619) + SegmentedButton (803): three tab idioms in one file | 'SABSE SAHI IDEA' 11px w800 letterSpacing caps (521); 'Sab', 'Hatao', 'Sab screens' (619,728,801,816,1206); 17 sizes <12 (135,188,1007); 4 raw Colors; radii 6/8/10/12/14/99; ⚖ ✓ glyphs (272,782,835) | 3 |
| app_family | App Studio partner/rider apps panel | panel | Clean | 1 |
| app_ios | iPhone build / App Store / code / match panels | panels | 6 sizes <12; ✓○ glyph status (265,363) | 2 |
| app_jaanch | App Studio test/rollout panel | panel | File name only Hinglish; UI clean | 1 |
| app_logic | App Studio logic panel | panel | 'Lagu karo' button | 2 |
| app_login | App Studio sign-in panel | panel | 4 sizes <12 | 1 |
| app_money | Owner's money panel (hisaab, udhaar, stock) | panel | Words 'udhaar' / 'paise mile' in UI copy | 1 |
| app_naksha | App Studio live map / route panel | panel | Clean | 1 |
| app_ops | App Studio running-health panel | panel | Clean | 1 |
| app_owndb | App Studio own-database panel | panel | Clean | 1 |
| app_pay | App Studio payments panel | panel | Clean | 1 |
| app_safety | App Studio security-gate panel | panel | 1 raw Color; radius 4 (outlier) | 1 |
| app_track | App Studio live-tracking panel | panel | Clean | 1 |
| appcheck_screen | App Jaanch (REA) screen + chat card | list | Thin; no empty state | 1 |
| appreview_screen | App-review report screen + cards | list + detail page | ✓ glyph lists (519); 3 ChoiceChip rows | 1 |
| approve_key_screen | Approval-fingerprint key setup | form | Clean, small | 1 |
| arch_desk | Software architecture desk (designs, PR review) | list -> detail | No Aurora, plain `AppBar` + default bg (145): looks unlike other desks; ✓✗ glyph lines (470-487) | 2 |
| archassist_screen | Architect-assistant desk (projects, area, approvals) | ChoiceChip tabs (279/294) | No Aurora (bg only); 7 sizes <12; 8x w800; ✓✗⚠ glyph status (835,892,963); 'submit karo' copy | 2 |
| artifact_screen | Artifact (page) viewer + chat card + call pill | page + card | **10 raw Colors** (492-499 etc.), 📄 emoji in status strings (692-695), radii 12/14/26/999 | 3 |
| artifacts_screen | My pages list | list | Fine; radius 13 (outlier) | 1 |
| artistmgr_screen | Artist-manager desk (gigs, artists, releases) | ChoiceChip tabs (341/354) | No Aurora; 5x w800 | 1 |
| ask_form_card | Chat form card | card | Fine | 1 |
| attach | File-picker helper (not a screen) | helper | Hinglish snack source strings via tr() (48,66,76) | 1 |
| audit_screen | Audit desk (TB, day book) | ChoiceChip | ✓ inside button labels (264-266) | 1 |
| bahar_screen | Outside-channels pairing (WhatsApp/Telegram/Slack/Teams) | form/list | Clean | 1 |
| banquet_screen | Banquet / hall desk | ChoiceChip tabs (399/410) | No Aurora; ✓✗⚠ glyph status (251,359,500); 5x w800 | 2 |
| blender_screen | 3D Studio (Blender) screen + card | list + card | 4 ChoiceChip rows; fine otherwise | 1 |
| bluetooth_panel | Bluetooth devices panel | list | Fine | 1 |
| booking_screen | Booking / job card panel (inside deals) | ChoiceChip + form | 'Na' button (256) beside 'Yes'; 5x w800 | 2 |
| brand_screen | Brand designer desk | TabBar (4) | ⛔/⚠ glyph (857); 'Sab platform'; radii 12/14/16 | 1 |
| browser_live | Live browser view (chat card / screen / call thumb) | card + screen | **15 raw Colors** (27 red 0xFFDC2626, 120 0xFF0E1220, 153/184 0xFFC026D3 magenta, 183, 309); 6 sizes <12; radii 3/6/11/12 | 3 |
| cad_desk | CAD engineer desk | list | ✓✗⚠ glyph status (153,163,186) | 1 |
| calendar_screen | Calendar screen + event card | list | 👥 emoji (55); 'MANA KIYA' caps state | 2 |
| call_quality_screen | Call scorecards | list | 👍👎 emoji (180); title 'Call ki jaanch' | 2 |
| call_rate_card | Post-call rating card | card | 'Call kaisi rahi?' prompt | 2 |
| call_receipt | Call receipt card | card | 1 size <12; w800 | 1 |
| callcentre_screen | Call-centre desk (script, calls, rules) | ChoiceChip tabs (369) | 'AI message le' (433) mixed; 6x w800; ⚠ glyph (592,719); 1 raw Color | 2 |
| chai_screen | Chai-stall desk | TabBar (55) | Tab 'Galla' (55); title 'Chai stall sahayak' (54); 9x w800 | 2 |
| compliance_screen | Compliance desk (filings, certificates) | ChoiceChip tabs (457/472) | No Aurora; 9 sizes <12; 'portal par file karo' button copy | 2 |
| contracts_screen | Contract-manager desk | ChoiceChip tabs (414/429) | No Aurora; 9 sizes <12; 7x w800; ✗ glyph (974) | 2 |
| cosec_screen | Company-secretary desk | ChoiceChip tabs (263/278) | Tabs 'Aaj', 'Niyam' (263); 'file karo', 'Card banao'; 9 sizes <12; ✗ glyphs (665,833) | 3 |
| courier_screen | Courier desk (parcels, COD) | ChoiceChip tabs (467/483) | Tabs 'Aaj','Niyam' (467); 'Aage' (75), 'Pahunche'/'Sab' filters (263), 'COD ka hisaab' (324), 'Pickup ka pata' (372), 'Courier sahayak' (471); 11x w800; ⛔⚠ glyphs (595,597,791) | 3 |
| customs_screen | Customs / import desk | ChoiceChip tabs (256) | 9 sizes <12; 'Customs Sahayak' title | 2 |
| cyber_screen | Cyber-security desk | ChoiceChip tabs (479) | Tabs 'Aaj', 'Niyam' (478); 'yeh normal hai' copy; 9x w800 | 2 |
| daftar_screen | School office desk + share card | ChoiceChip tabs | Fine | 1 |
| darzi_screen | Tailor desk (orders, measurements) | TabBar (95-99) | Title 'Darzi sahayak' (93); **16x w800** (106,145,147,213); 5 Aurora; 1,633 lines | 2 |
| deal_screen | Deals / orders / UPI pay + cards | many ChoiceChip rows | **23x w800 + w900** (89,104,427,450,707); 13 ChoiceChip rows; 1,872 lines, biggest file; 9 sizes <12 | 3 |
| desk_cards | Chat cards (sheet match, doc edit, memory chips) - NOT a desk template | cards | 'Chat chhoti karo' copy; 6 sizes <12; radii 10/12/20/24 | 1 |
| devops_screen | DevOps desk | ChoiceChip tabs (461) | Tabs 'Aaj', 'Niyam'; 'Theek' button (164); **15 sizes <12** mono 11 (500,630,681,707,936); 3 raw Colors | 3 |
| devsahayak_screen | Developer Sahayak phone screen (sessions, PRs) | ChoiceChip tabs (646) | 3 raw Colors; 'Haan, PR kholo' / 'Haan, shuru karo' button copy; 1,574 lines | 2 |
| docwriter_screen | Docs writer desk | ChoiceChip tabs (323/336) | Tabs 'Aaj','Niyam' (323), 'Docs sahayak' (325), 'Aage' (68), 'Product jodo' (263), 'Hatao' (272), 'Shabd jodo' (315); 10x w800; uses NavigationBar (430) too | 3 |
| dosti_screen | Hoola Network friends screen + card | TabBar (240-243) | Fine | 1 |
| dpo_screen | Data-protection officer desk | ChoiceChip tabs (588/603) | Tabs 'Aaj','Niyam' (588); 'DPA sign hai' (308); '⚠ baaki:' (559); 10 sizes <12; 14 plain `Card(` | 3 |
| drive_screen | Google Drive screen + reconnect card | list | Fine | 1 |
| drivers_screen | Driver / fleet desk | ChoiceChip tabs (563) | 8x w800 | 1 |
| editdesk_screen | Video edit desk | ChoiceChip tabs (266/277) | No Aurora; ✗ glyph (301,620); 6 emoji/glyph lines | 1 |
| email_screen | Email settings screen | list + chips | Visible copy is Hinglish source through `app.g()` (381-392, 446, 481); in English mode it shows only what `tr()` covers; 'Shant' / 'Sab' chips (432); ✓ in snack (131) | 3 |
| employee_inbox | Business inbox tab + thread screen + cards | SegmentedButton (82) + list | 2 raw Colors; radii 14/20/99 | 1 |

## Counts

- Hinglish-heavy (user-facing strings, not comments): **13 files** — ads, app_design_screen, cosec, courier, cyber, devops, docwriter, dpo, email, chai, calendar/call_quality/call_rate_card (titles/prompts). Lighter mixing in about 12 more.
- Raw `Color(0x..)` outside `C`: browser_live 15, artifact_screen 10, app_design_screen 4, devops 3, devsahayak 3, employee_inbox 2, plus 4 files with 1.
- `fontSize` under 12: 42 of 63 files; worst app_design_screen 17, devops 15, app_android 11, dpo 10.
- `w800`/`w900`: deal 23, darzi 16, aftersales 13, courier 11, docwriter 10.
- Tab mechanisms: ChoiceChip-in-Wrap ~24 desks, TabBar 6 (ads, brand, chai, darzi, dosti, app_design), SegmentedButton 2, and app_design_screen mixes all three.
- Desk tab vocabulary split: half say 'Today / Rules', half say 'Aaj / Niyam' (cosec, courier, cyber, devops, docwriter, dpo, ads).
- Confirm-dialog wording split: 'Leave it' 14 files, 'Keep it' 10, 'Cancel' 12.
- Background split: desks without `Aurora` use flat `C.bgTop` (archassist, artistmgr, banquet, compliance, contracts, cosec, courier, docwriter, dpo, editdesk) or the theme default (arch_desk).
- 45 files each define their own `String _s(dynamic)` (and most also define `_m` / `_strs` / `_list`).

## Shared patterns

Almost every desk repeats the same layout:

```
Scaffold(backgroundColor: C.bgTop?, appBar: AppBar(transparent, title: '<avatar> · <Role>' or '<X> Sahayak'),
  body: Aurora?(RefreshIndicator(ListView(padding 16,8,16,60, [
    Wrap(spacing 6, [for (i,t) in tabs ChoiceChip(label: t, selected: _tab==i)]),
    if (_busy) LinearProgressIndicator(),
    if (_d == null) Center(CircularProgressIndicator()) else [_today(), ..., _rulesTab()][_tab],
  ]))))
```

Tab sets follow a fixed order: Today -> domain lists -> Rules. Tapping a row opens a detail `XxxPage` (its own Scaffold). Chat-side `XxxCard` widgets confirm with a Haan/approve button. Example: cyber_screen.dart 470-483.

Error handling is ad hoc. Most screens catch and show a SnackBar. None draws an inline error state with Retry. If the first load fails, `_d` stays null and the spinner never stops (e.g. cyber 482).

No shared desk template exists. `desk_cards.dart` holds chat cards only (SheetMilaanCard, DocEditCard, MemorySavedChip, CompactChip, MemoryUsedChip).

### Proposed `DeskScaffold` (new `lib/ui/desk_kit.dart`)
- `DeskScaffold({title, role, tabs: List<DeskTab(label, icon, builder)>, load: Future<Map> Function(), actions, fab})`. It always uses Aurora + RefreshIndicator, keeps one tab bar style (a scrollable chip row with the selected chip in accent), and handles loading, error and empty states: a skeleton while loading, a `DeskError(message, onRetry)` when the load fails, and a `DeskEmpty(icon, text, action)` when there is nothing to show.
- `DeskSection(title, trailing)` and `DeskRow(title, subtitle, status: DeskStatus.ok|warn|bad|wait)`. These replace the glyph status prefixes (✓ ✗ ⚠ ⛔ ○ ★) with an icon and colour from `C`.
- `confirmDialog(context, title, body, yes:, no: 'Cancel')`, so cancel buttons all say the same thing.
- One `util/json.dart` with `s()`, `m()`, `strs()`, `list()`, replacing the 45 copies.
- Add to glass.dart: `R.sm 8 / md 12 / lg 16 / pill 999` and a type scale (`T.caption 12`, `T.body 14`, `T.title 16 w700`). Cap the weight at w700, and treat 12px as the floor.
- Standard tab names: 'Today', 'Rules' (no 'Aaj' / 'Niyam'). Titles: '<avatar> · <Role in English>'. Drop 'Sahayak' from titles.

## Dead / suspect
- `agents_screen.dart`: AgentsScreen is referenced nowhere in lib/. It is dead.
- `app_*` panels (16 files) are reached only through app_design_screen. They are alive but nested.
- `attach.dart` is a helper, not a screen (used by brand_screen and video_editor).
