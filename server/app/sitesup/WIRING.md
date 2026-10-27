# WIRING for sitesup
summary: Site Sahayak (construction site supervisor: activity plan vs done with look-ahead and delay reasons, labour attendance per contractor / trade with normal + overtime hours and wage-register numbers, material received / used / balance with challans, toolbox talks, PPE / height / scaffold / excavation / pour / electrical / welfare checklists, near-miss / accident register with the Form XI clock, pour cards with IS 456 sample counts, cube tests at 7 / 28 days and curing dates, snags with EXIF-stripped photos, DPR PDF + WhatsApp text; works ON a Theka project (delays into its hindrance diary, material into its stock); indent / purchase, anything to the client and any stop-work order only on her tap)
db: app.sitesup.models
router: app.sitesup.api            (make_router(require_key, current_tenant); all routes under /api/sitesup, key-protected; no public routes)
tools: app.agent.sitesup_tools     (SITESUP_TOOLS / SITESUP_LABELS / SITESUP_HANDLERS) ; voice: yes (sitesup, sitesup_dekho)
employee: duty site_supervision = [sitesup, sitesup_dekho, file_read, theka_dekho] {label "Site supervision", say "roz ka kaam vs plan, hazri, site par maal, safety / toolbox talk, cube test, snag, DPR (indent, client ko report aur kaam rokna aapki haan se)"} ; role site_supervisor {label "Site supervisor", duties [site_supervision, contract_work, records, reminders]} ; preset site_supervisor {label "Construction site / supervisor", role site_supervisor, rules ["Material indent / kharid sirf owner ki haan (card) se", "Client ko DPR / message sirf owner ki haan se", "Kaam rokne ka order sirf owner ka; jaan ka khatra ho to pehle log hatao", "Naap / progress jaisa bataya waisa hi likho"]} ; READ tools: [sitesup_dekho]
  - staff (staff:<id>, e.g. the site engineer / foreman on the Hoola Network team) may log progress, attendance, material, toolbox talks, checklists, incidents, pours, cubes, snags, photos and RAISE indent / stop-work / DPR cards; the tool refuses customer actors and the owner-only actions (settings, reported, forget, closing a site). No tool can decide a card: only POST /api/sitesup/indents/{id}/decide, /reports/{id}/decide, /stops/{id}/decide and /stops/{id}/lift (her app taps).
push: sitesup_indent -> ("Site: indent aapki haan chahiye", "{say}")
push: sitesup_stop -> ("Site: kaam rokna hai?", "{say}")
push: sitesup_report -> ("Client ke liye report taiyaar", "{say}")
push: sitesup_alert -> ("Site", "{say}")      (always; incident ones are urgent)
push: sitesup_day -> ("Aaj ka site note", "{say}")
  (pc_file for the register Excel uses the existing pc_file kind)
worker: app.sitesup.service.tick   (call every minute, e.g. `await asyncio.to_thread(sitesup.service.tick)`; cube tests due tomorrow / today / late and curing end (once each), Form XI deadline 2 h before and when passed, morning note at her morning_time, DPR reminder at her dpr_time when a site has entries today but no DPR)
approvekey: kind "sitesup" (indent with an amount, once a phone key is active). Uses approvekey's own ApproveChallenge table + `_check` (same as fleet). If approvekey keeps a list of known kinds / card_digest per kind, add "sitesup" -> service.indent_card(tenant, id)["hash"].
prompt: SITE SUPERVISOR: site ka roz ka kaam (`sitesup action=progress` exactly as reported, delay with its reason), hazri (`attendance`: contractor / trade / count / hours), maal aaya / laga (`material` with challan), toolbox talk, checklist, ghatna (`incident`: death / injury / collapse = tell her the Form XI deadline and first aid / 112 first), pour + cube result, snag + photo, DPR (`dpr`). Indent / purchase, DPR or any message to the client, and stop-work become CARDS for her tap: say "aapki haan ka card bheja hai", never that it was ordered / sent / stopped. Never invent quantities, prices or test results; salaries are payroll's job. If a site is linked to a Theka project, BOQ / measurement book / RA bills stay in `theka`.
persona: Site par kaam / hazri / maal jaisa bataya waisa hi likho; indent, client ko report aur kaam rokna "aapki haan ka card bheja hai"; hadsa ho to pehle ilaaj / 112 aur log hatana, phir notice ki ghadi batao.
flutter: SitesupScreen in lib/ui/sitesup_screen.dart (SitesupSitePage for one site) ; profile tile title "<name> · Site supervisor" subtitle "Roz ka kaam, hazri, maal, safety, cube test, snag, DPR" icon Icons.construction_rounded ; cards: sitesup_indent -> SitesupIndentCard (also in calls: yes; key data['indent']['id']) ; sitesup_stop -> SitesupStopCard (also in calls: yes; key data['stop']['id']) ; sitesup_report -> SitesupReportCard (also in calls: yes; key data['report']['id']) ; sitesup_alert -> SitesupAlertCard (also in calls: yes) ; sitesup_day -> SitesupDayCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`, `app.api!.uploadFile(...)`, `Native.openExternal`, `Native.approveKeySign` and image_picker (already a dependency).
features: site_supervisor
env: SITESUP_DIR (default data/sitesup) - where site photos (EXIF-stripped JPEG) are kept; tests point it at tmp
requirements: none (reportlab, openpyxl, Pillow already present)
android: none
neighbours: theka (v0.117: BOQ, measurement book, RA bills, hindrance diary / EOT, project material - sitesup links a site to a theka project and writes delays / labour totals into its diary and material into its stock; it never edits BOQ / MB / bills); payroll (salaries); archassist (drawings / approvals), interior (interior fit-out snags), propagent, rentdesk, society (other Makaan builders); office / helpdesk (vendors / repairs); approvekey (fingerprint).
claude_md: |
  ## v0.1xx Site Sahayak: Hoola as a construction site supervisor ("Site supervisor" on the Employee page)
  - Owner's spec: daily progress by activity vs plan (look-ahead, delays with reasons) -> labour attendance per contractor / trade with
    hours and the wage-register numbers (payroll keeps salaries) -> material received / used / balance at site with indent requests ->
    safety (toolbox talk log, PPE / height / scaffolding / excavation checklists, near-miss and accident register) -> quality (pour
    cards, cube tests at 7 / 28 days, snag list with photos, EXIF stripped) -> DPR PDF + WhatsApp draft to the client. Waits for her Haan
    on any material indent / purchase, any report or message to the client, any stop-work order (and lifting it).
  - Server `server/app/sitesup/{rules,models,service,api}.py`, tools `sitesup` / `sitesup_dekho` (`agent/sitesup_tools.py`, chat + calls),
    duty `site_supervision`, role + preset `site_supervisor`, API `/api/sitesup/*`, app Profile > Site supervisor
    (`lib/ui/sitesup_screen.dart`: Aaj / Sites / Niyam + `SitesupSitePage`), cards SitesupIndentCard, SitesupStopCard, SitesupReportCard,
    SitesupAlertCard, SitesupDayCard. Tests `server/tests/test_ghar_sitesup.py` (7).
  - Works ON a Theka (v0.117) project: `site theka_project=` links it; `plan from_boq` makes one activity per BOQ item (dates hers);
    activity views show the measurement-book quantity next to site progress; a delay reason / day's labour total / incident / stop-work
    goes into the Theka hindrance diary (client-side reasons like drawing / department / front not given count for the EOT letter);
    material received / used mirrors into the Theka project stock. BOQ, MB, RA bills and EOT letters stay in theka.
  - Plan + progress: activities (code, unit, qty, start / finish, contractor, material it needs); progress exactly as reported (no future
    dates, over-plan quantity pointed out); state per activity = planned % (linear over its dates) vs done % -> on_track / behind (her
    behind_pct, 10) / late; delay kinds from Hinglish words (rain, material, labour, drawing, client, power, equipment, quality, safety).
    Look-ahead (her lookahead_days, 21): coming activities + material each still needs vs balance at site -> "indent card banayein?".
  - Labour: gang rows {contractor, trade, count, hours} or named workers; trade words (mistri, beldar, sariya, sutar...); same day +
    contractor + trade (+ worker) replaces, never doubles. Over her day limit (8) = overtime at twice the rate, rounded per OSH Central
    Rules 2026 (15-30 min = half hour, more = full hour); a named worker over 48 hours in a week flagged; > 12 hours = check her state's
    spread-over rule. Register per period: man-days, normal hours, OT hours per contractor / trade; rupees only from HER daily rate per
    trade as a check on the contractor's labour bill (salary = payroll). Excel (labour, workers, material, safety). Aadhaar / PAN never in
    the register: an ID only as a Pehchaan Locker {id:...} reference; long numbers in any text are blanked.
  - Material: in (supplier, challan, vehicle, quality ok) / used / return / waste; duplicate challan refused, can't use more than is at site.
    Indent IND-0001 (items, need by, supplier, amount ONLY from her / the supplier's quote; checks: stock already at site, 60+ days of
    use, date passed, price unknown) -> `sitesup_indent` card with a hash; ONLY `POST /api/sitesup/indents/{id}/decide {yes, hash, proof}`
    (by_tap) decides; with an amount and an active phone key her fingerprint is required (approvekey kind "sitesup", 428 -> `/challenge`);
    approved -> supplier WhatsApp draft she sends -> "order bhej diya" -> material received against the indent. Hoola never orders or pays.
  - Safety: toolbox talks (topic of the day, people vs present), 7 checklists (ppe, height, scaffold, excavation, pour, electrical, welfare)
    with critical items: a critical "no" = an unsafe condition -> "move people away now" + a stop-work card SW-001 for HER tap
    (`/stops/{id}/decide`); a whole-site stop marks the site stopped; lifting needs her tap AND what was fixed (`/stops/{id}/lift`).
    Incident register INC-001: near_miss / first_aid / injury / death / dangerous (scaffold / formwork / staging / excavation / wall / slab
    collapse, crane, fire, electric shock) / property; Form XI clock per OSH Central Rules 2026 r.7: death forthwith (Inspector-cum-
    Facilitator, DM / SDO, police, family), injury off work 48 h+ within 12 h after the 48 h, dangerous occurrence within 12 h; first aid /
    112 / keep the scene first; Form XI draft text; "reported" (owner) with her reference; death / dangerous also prepare a stop-work card;
    tick reminds 2 h before and when passed. Her state's form / portal decides the exact format.
  - Quality: pour card PC-001 (element, grade, volume, cement, source, slump, pre-pour checks) -> samples by IS 456 cl. 15.2.2 (1-5 cum 1,
    6-15 2, 16-30 3, 31-50 4, +1 per extra 50 cum; 3 cubes each), cube sets at 7 / 28 days (+56 for PPC / PSC), curing until (7 days OPC,
    10 days blended cement or hot dry weather; IS 456 cl. 13.5.1). Cube result in N/mm2 (kN refused): 7-day indicative (~65%); 28-day vs
    IS 456 Table 11 defaults (individual >= fck - 4 for M20+, fck - 3 for M15; mean of 4 consecutive >= fck + max(0.825 x sd, 4 / 3),
    assumed sd 3.5 / 4 / 5) unless her QA plan's limits are set; fail = alert to her / engineer (core / load test is the engineer's call).
    Snags SN-001 (location, trade, contractor, due) open -> fixed (a "fixed" photo) -> verified; photos re-encoded from pixels (JPEG
    <= 1600 px; EXIF / GPS / camera gone) in `data/sitesup/<tenant>/<site>/`.
  - DPR DPR-0001: the day's work, manpower by contractor, material in / used, hindrances, behind-plan activities, toolbox / checklists /
    incidents, pours + cubes, snags, weather / tomorrow / remarks, overall progress table, material balance, up to 4 photos -> PDF (her
    file) + WhatsApp text -> `sitesup_report` card (hash; a newer DPR for the same day makes the older card stale); ONLY her tap
    (`/reports/{id}/decide`): via self = wa.me link from her phone + "Maine bhej diya", via business = the business WhatsApp (official
    Cloud API) only to a client who has written to that number; blanks refuse sending. Other client messages (`message`) the same way.
  - Morning note at her time (incident notices due, stop-work active, behind-plan / material short for 7 days, cube tests today, curing,
    cards waiting, today's toolbox topic); DPR reminder at her dpr_time. DPDP: `forget` (owner, only after the site is done) blanks
    workers' names / ID references, incident names and the client's contact; counts and registers stay.
  - Never: ordering / paying / sending to the client / stopping work without her tap, inventing quantities / prices / results, salaries
    (payroll), BOQ / MB / bills (theka), Aadhaar numbers in registers.
  - Research (23 Oct 2026): OSH Code 2020 in force 21 Nov 2025; OSH (Central) Rules 2026, G.S.R. 345(E) 8 May 2026 - 48 h a week, overtime
    beyond 8 h a day for daily-wage workers at double wages with 15-30 min = half hour / > 30 min = full hour rounding, free yearly
    health check for building workers aged 40+, welfare (drinking water, toilets, first aid, shelter, creche), Form I registration on the
    Shram Suvidha portal (scconline.com/blog/post/2026/05/13/osh-central-rules-2026-key-highlights-and-compliance-guide/); Rule 7 notice of
    accidents and dangerous occurrences, Form XI: death forthwith, 48 h+ injury within 12 h after, dangerous occurrence 12 h; collapse of
    scaffolding / formwork / excavation and falls from height are dangerous occurrences; state rules may differ
    (taxclue.in/blog/rule-7-osh-central-rules-2026-notice-of-accidents-and-dangerous-occurrences/); BOCW cess 1% stays with theka (v0.117,
    S.O. 2322(E) 8 May 2026); IS 456:2000 cl. 15 / 16 sampling + acceptance and IS 516 (Part 1 / Sec 1):2021 cube testing, 150 mm cubes, 3 per
    sample, water curing 27 +/- 2 C, 7-day indicative (infralens.in/handbook/cube-test-acceptance; published summaries differ on the
    individual-result limit, e.g. dmc-education.com 27 Jul 2026 says fck - 3 for all grades, so limits are her QA plan's setting); IS 456
    cl. 13.5.1 curing 7 / 10 days; NBC 2016 Part 7 (constructional practices and safety) with IS 3696 (scaffolds / ladders) and IS 3764
    (excavation) behind the checklists (good-practice wording, not legal text); DPDP Act 2023 / Rules 2025 for workers' data. Checklist
    items, the 10% behind limit, 21-day look-ahead and the 65% 7-day expectation are starter values.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/sitesup_screen.dart (Dart 3 records in field lists, switch expressions, StatefulBuilder checklist dialog, image_picker). The fingerprint path was tested with approvekey._check patched (same as fleet), not a real phone. Business WhatsApp send tested with a fake inbox.send. Real Form XI formats differ by state (Central Rules used; state OSH rules may change timelines / forms) and Hoola does not file it. IS 456 Table 11 individual-result limit differs between published summaries: defaults are configurable per her QA plan. DPR PDF uses Helvetica (Latin text; Devanagari words in notes would print as '?'; lekhak's Chromium printer could be used later). Theka mirroring relies on theka.service.diary / material / boq_items / project_view signatures as of v0.117. Push titles are suggestions for push.PUSH_KINDS.
