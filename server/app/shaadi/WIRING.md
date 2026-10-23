# WIRING for shaadi
summary: Shaadi Sahayak (wedding planner for Indian weddings of every community: functions per community with dates only from her and the muhurat only as the family pandit gave it, panchang facts for her dates, day-wise timeline with the 10 pm noise rule, checklist counted back from the first function, guests per side with RSVP per function and caterer headcount, room blocks with overbooking refused in code, guest travel handed to the Travel Sahayak, vendors with HER quotes and payment schedules, budget by function and head, shagun register owner-only + Dowry Rules list of presents, invite drafts, marriage registration checklist; vendor booking / advance / payment / spend (fingerprint), client quote / payment request and every message to guests only on her tap)
db: app.shaadi.models
router: app.shaadi.api            (make_router(require_key, current_tenant); all routes under /api/shaadi, key-protected; no public routes)
tools: app.agent.shaadi_tools     (SHAADI_TOOLS / SHAADI_LABELS / SHAADI_HANDLERS) ; voice: yes -> put BOTH `shaadi` and `shaadi_dekho` into voice.VOICE_TOOL_NAMES AND voice.VOICE_VIA_KAAM (v0.149 rule: calls hand Sahayak work to santosh_kaam)
employee: duty shaadi_work = [shaadi, shaadi_dekho, file_read, india_info] {label "Shaadi planning", say "functions, dates (muhurat panditji ka), mehmaan + RSVP, rooms, vendors, budget, checklist, timeline, shagun register (vendor booking / payment / kharch, client quote, mehmaanon ko message: aapki haan se)"} ; role wedding_planner {label "Wedding planner", duties [shaadi_work, customers, appointments, reminders, records]} ; preset wedding {label "Wedding planner / shaadi ki taiyaari", role wedding_planner, rules ["Muhurat kabhi mat nikalo: panditji ka faisla, sirf unki batayi baat likho", "Vendor ka daam, tareekh, room rate kabhi mat gadho: khaali chhodo aur poochho", "Booking, advance, payment, kharch, client quote aur mehmaanon ko message: sirf owner ki haan ke card se", "Shagun register sirf owner ke liye; dahej ka hisaab kabhi nahi"]} ; READ tools: [shaadi_dekho]
  - staff (staff:<id>) may build the file (new / update / function / timeline / checklist / guest / rsvp / room / room_assign / vendor / budget / invite_text / invite_design) and make cards (book / pay / spend / quote / client_pay / message: cards only); owner-only actions are refused by the tool itself (settings, paid, spend_paid, gift, gift_remove, gift_list, trip, forget) and shaadi_dekho what=gifts is owner-only. customer: actors are refused. No tool can decide a card: only POST /api/shaadi/cards/{id}/decide (her app tap) sets by_tap=True.
push: shaadi_card -> ("Shaadi: aapki haan chahiye", "{say}")      (push only while data.card.status == "waiting")
push: shaadi_alert -> ("Shaadi", "{say}")
push: shaadi_day -> ("Aaj ka shaadi note", "{say}")
approvekey: kind "shaadi" is used ONLY through shaadi.service.challenge / _verify_fingerprint, which write and check ApproveChallenge rows directly (same pattern as fleet / interior). No change to approvekey is required.
worker: app.shaadi.service.tick   (call every minute, e.g. `await asyncio.to_thread(shaadi.service.tick)`; function tomorrow (with its timeline), checklist item due today, vendor payment due: once each; morning note once a day at her morning_time only when there is something)
prompt: SHAADI: wedding planner's coworker (`shaadi` / `shaadi_dekho`). Dates come from her; for a date show panchang FACTS (`shaadi_dekho what=panchang`) but NEVER suggest or calculate a muhurat: the family's pandit decides it, store it only as she says with muhurat_by. Vendor prices / room rates are only what the vendor quoted her: missing = ask. Vendor booking / advance / payment, any spend, the client quote / payment request and every message or invite to guests are cards for HER tap: say "aapki haan ka card bheja hai", never that it was booked / paid / sent. The shagun register is hers alone (never tell staff / guests / other avatars); never keep or draft anything about dowry (Dowry Prohibition Act 1961); refuse to plan a marriage where the bride is under 18 or the groom under 21.
persona: Shaadi mein muhurat kabhi khud mat batao ("panditji batayenge"), daam kabhi mat gadho; booking, payment, kharch aur mehmaanon ko message par "aapki haan ka card bheja hai" kaho; shagun ka hisaab sirf owner se.
flutter: ShaadiScreen in lib/ui/shaadi_screen.dart (+ ShaadiWeddingPage) ; profile tile title "<name> · Wedding planner" subtitle "Functions, muhurat (panditji ka), mehmaan + RSVP, rooms, vendors, budget, shagun" icon Icons.favorite_rounded ; cards: shaadi_card -> ShaadiCardCard (also in calls: yes; key by data['card']['id'], update in place; handles 428 -> /api/shaadi/cards/{id}/challenge -> Native.approveKeySign -> resend with proof) ; shaadi_alert, shaadi_day -> ShaadiNoteCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`, `app.api!.uploadFile(...)`, `Native.openExternal`, `Native.approveKeySign`, file_picker (all already in the app).
features: shaadi
env: none
requirements: none (reportlab, openpyxl already present; PDFs with Hindi / Marathi names go through app.indicpdf)
android: none
neighbours: eventplan (corporate / social events: run-of-show, RSVPs — shaadi is the wedding-specific one), banquet (hall sales, date blocks, BEO: the venue's side; shaadi keeps the family / planner side), frontoffice + homestay (the hotel / homestay's own booking of the rooms shaadi blocks for guests; shaadi only allocates guests inside blocks she got), travel (guest trains / flights: `to_trip` makes a draft trip there with names only), brand (invite card design with its own final-artwork approval), india.days (panchang + holidays), approvekey (fingerprint for money cards), employee (UPI ID fallback, team), chatfiles (her files).
claude_md: |
  ## v0.1xx Shaadi Sahayak: Hoola as a wedding planner's coworker ("Wedding planner" on the Employee page; Mehmaan suite)
  - Owner's spec: wedding file with community-aware functions (sagai, haldi, mehendi, sangeet, shaadi, reception ... editable), dates
    (panchang facts via india.days only; muhurat = the family pandit's decision, never invented), guest list per side with RSVP per
    function, room block / allocation, guest travel (Travel Sahayak), vendors with HER quotes, budget by function and head, payment
    schedule with advances, day-wise timeline, checklist counted back from the date, shagun / gift register (owner-only, never shared),
    invite drafts (Brand for designs), wedding registration checklist only. Waits for her Haan on: vendor booking / advance, client quote,
    any message / invite to guests, any spend.
  - Server `server/app/shaadi/{rules,models,service,api}.py`, tools `shaadi` / `shaadi_dekho` (`agent/shaadi_tools.py`, chat + calls via
    santosh_kaam), duty `shaadi_work`, role `wedding_planner`, preset `wedding`, API `/api/shaadi/*`, app Profile > Wedding planner
    (`lib/ui/shaadi_screen.dart`: Aaj / Shaadiyan / Niyam + `ShaadiWeddingPage` tabs Functions / Mehmaan / Rooms / Vendors / Budget /
    Checklist / Shagun / Cards), cards ShaadiCardCard (`shaadi_card`, also in calls), ShaadiNoteCard (`shaadi_alert`, `shaadi_day`).
    Tests `server/tests/test_host_shaadi.py` (7).
  - Wedding W-001: 17 communities (Hindu North, Marathi, Gujarati, Punjabi, Sikh, Marwari, Bengali, Tamil, Telugu, Malayali, Kannada,
    Jain, Muslim, Christian, Parsi, interfaith / court marriage, other) each with a starter function list she edits (add / rename /
    remove); dates and times ONLY from her (same-day clashes warned); `panchang` = tithi / paksha / nakshatra / vaar / amanta month /
    sunrise + state holidays for HER dates from app.india.days, with "muhurat panditji se" on ritual functions; `muhurat` stored only as
    she says with `muhurat_by`. Child marriage refused in code (bride < 18 / groom < 21, Prohibition of Child Marriage Act 2006); any
    dowry wording refused (Dowry Prohibition Act 1961).
  - Timeline per function from her start time (starter rows by function type; ritual row = her muhurat or blank), day-wise plan with
    booked vendors; DJ / band / loudspeaker running past 10 pm warned (Noise Pollution Rules 2000 rule 5). Checklist (23 starter items +
    community extras: church banns, nikahnama / qazi, gurdwara, SMA notice, agiary...) due dates counted back from the FIRST function
    (after-wedding items from the LAST), states late / today / soon, she ticks; morning note + once-each alerts.
  - Guests: side bride / groom / common, phone (same phone = same guest), adults / kids, invited functions, diet, city, arrival / departure,
    travel from, no-messages; CSV / Excel import with Hinglish headers; RSVP per function (only where invited); headcount per function
    (yes / maybe / pending / no, kids, diet, side) with "plates between yes and yes + maybe + pending" for the caterer.
  - Rooms: blocks (place, label, capacity, check-in / out, her rate) -> allocation checked night by night: heads never above capacity,
    stay inside the block (overbooking refused). Travel: guests grouped by city + arrival; `trip` (owner) makes a DRAFT Travel Sahayak trip
    with names only.
  - Vendors (venue, decor, caterer, photographer, mehendi, DJ, band, pandit / qazi / priest, makeup, transport, invites ...): quote = HER word
    (per plate x plates only from her two numbers), what's included, payment schedule [{label, amount | pct of her quote, due}] (sum <= quote,
    no amount = refused, approved kists locked), same-kind / same-vendor-other-wedding clashes warned, quote comparison per kind.
  - Cards (`shaadi_cards`, SC-0001, sha256 of what the card shows, rebuilt from the data at the tap: any change = stale): vendor_book (+ its
    advance), vendor_pay (one kist), spend (her amount) = money cards: her phone's fingerprint once a phone key is active (approvekey kind
    "shaadi" via `/cards/{id}/challenge`); client_quote (agency mode: her planning fee percent of budget / flat + her lines, GST only with
    her GSTIN at her % (event management SAC 998596, her CA confirms), stages adding up exactly, PDF + client draft), client_pay (draft +
    UPI link to HER UPI ID), message (invite / RSVP / info to filtered guests or booked vendors: text from real facts only, [blanks] block,
    no-messages / no-phone guests skipped and named; on her tap one wa.me / SMS link per person, she sends). ONLY `POST
    /api/shaadi/cards/{id}/decide {yes, hash}` (by_tap) decides; same waiting card never made twice. After approval she pays herself and
    taps "Maine de diya" (UTR tail); a vendor fully paid = done.
  - Budget: her planned amounts per function x head (+ total) vs committed (booked vendor quotes, shared equally across their functions;
    approved spends) vs paid; over-budget warnings.
  - Shagun register (owner only: tool refuses staff, chat sees masked names "Sunita M.", full only in her app): giver, relation, side, for
    bride / groom / both, function, cash / UPI / cheque / gold / item, value; Rs 2 lakh+ cash from one person in a day warned (income-tax,
    old s.269ST; CA decides); list of presents PDF in the Dowry Prohibition (Maintenance of Lists of Presents) Rules 1985 shape (description,
    approximate value, giver, relationship, signature lines for bride and bridegroom) as her file.
  - Registration CHECKLIST only by law (Hindu Marriage Act 1955 s.8 for Hindu / Sikh / Jain / Buddhist; nikahnama + state registration;
    Indian Christian Marriage Act 1872; Parsi Marriage and Divorce Act 1936; Special Marriage Act 1954 30-day notice) + Maharashtra 1998 Act
    90-day note (date shown); Hoola never files.
  - DPDP `forget` (owner, after done / cancelled): guest names -> "Mehmaan N", phones / cities / travel / notes and the client's contact
    removed; counts and money kept; gifts only when she says include_gifts.
  - Research (23 Oct 2026): event management incl. wedding planning 18% GST, SAC 998596 (cleartax.in/s/gst-on-event-management; busy.in
    SAC 998596; gimbooks.com 2026 guide), outdoor catering 18% / restaurant-type 5% and banquet rates depend on the supplier (mondaq.com Apr
    2025, pre-GST 2.0, so GST % is her setting); wedding gifts to the bride / groom exempt without limit, Income-tax Act 2025 s.92(3)(b)
    (old s.56(2)(x) proviso), and cash of Rs 2 lakh+ from one person in a day / one event attracts a 100% penalty (calcguru.in/?p=4169, 4 Aug
    2026, citing new s.186 / s.451; old 269ST / 271DA); Dowry Prohibition (Maintenance of Lists of Presents to the Bride and Bridegroom) Rules
    1985 rule 2 (bnblegal.com bare act; wcd.nic.in): list in writing at / soon after marriage, short description, approximate value, giver,
    relationship, signed by bride and bridegroom; Maharashtra Regulation of Marriage Bureaus and Registration of Marriages Act 1998: register
    within 90 days, both + three witnesses, igrmaharashtra.gov.in (citizenmatters.in Feb 2022); Special Marriage Act 1954 30-day notice;
    Prohibition of Child Marriage Act 2006 (21 / 18); Noise Pollution (Regulation and Control) Rules 2000 rule 5 (no loudspeaker 10 pm - 6 am;
    states may relax to midnight a few days a year). Checklist days, timeline offsets and community function lists are starters, not rules.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/shaadi_screen.dart (Dart 3 records in `for (final (k, _) in fields)`, switch expressions in Pill / _title, Iterable.firstOrNull, CheckboxListTile onChanged returning a Future). Real panchang values are the existing india.days calculation (±5 min); community function lists and checklist offsets are researched starters but not verified per sub-community. brand.service.make (invite design) and travel.service.new_trip were not called for real (travel monkeypatched in tests; invite_design untested). Fingerprint flow tested with a software EC key via approvekey.register. The Income-tax Act 2025 section numbers for marriage gifts / cash limits come from one secondary source (calcguru, Aug 2026): the app text says "old s.269ST, CA se poochhiye". Push titles are suggestions for push.PUSH_KINDS.
