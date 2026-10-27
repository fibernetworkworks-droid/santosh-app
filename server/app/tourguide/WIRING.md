# WIRING for tourguide
summary: Tour Guide Sahayak (local guide / small tour operator: tour products with HER price per person / group, duration, group size and places whose timings / tickets are only what she typed; enquiries pasted -> bookings with only what is written; group file with guest IDs + emergency number in the Pehchaan Locker; no overbooking / no double-booked guide in code; booking confirmation (cancellation policy upfront, UPI link to HER UPI), every guest message, refunds, discounts and spends only on her tap (fingerprint for refund / spend); day plan with closed-day / opening-hour clashes and ASI ticket steps, safety brief + Open-Meteo weather, roll call + sheet, multilingual intro scripts, review requests to everyone, Yatra Sahayak link for trains / flights, IITF / IITG / state licence renewals, tips / commission register, DPDP forget)
db: app.tourguide.models
router: app.tourguide.api            (make_router(require_key, current_tenant); all routes under /api/tourguide, key-protected; no public routes)
tools: app.agent.tourguide_tools     (TOURGUIDE_TOOLS / TOURGUIDE_LABELS / TOURGUIDE_HANDLERS) ; voice: yes (tour_guide, tour_guide_dekho) - put BOTH names in VOICE_TOOL_NAMES AND voice.VOICE_VIA_KAAM (v0.149 rule: calls hand this Sahayak's work to santosh_kaam)
employee: duty tour_work = [tour_guide, tour_guide_dekho, file_read] {label "Tour guide", say "tour, enquiry se booking, group file, din ka plan, safety + mausam, ginti, intro script, licence yaad (pakki booking / mehmaan ko message / refund / discount / kharcha aapki haan se)"} ; role tour_guide {label "Tour guide / tour operator", duties [tour_work, customers, reminders, records]} ; preset tour_guide {label "Tour guide / local tours", role tour_guide, rules ["Booking pakki, mehmaan ko message, refund / discount / kharcha sirf owner ki haan ke card se", "Monument ka samay / ticket ka daam sirf owner ka bataya; warna 'pata nahi'", "Group size se zyada booking kabhi nahi"]} ; READ tools: [tour_guide_dekho]
  - staff (staff:<id>) may take enquiries, make / edit group files (not the price), hold slots, ask for confirm / message / refund / discount / spend CARDS, plans, safety, roll calls, scripts, review, travel link. Owner-only: settings, tour (products + prices), received, paid_out, licence, ledger_add, forget, price_total, cancelling a booking. Customers (customer:*) are refused. No tool can decide a card: only POST /api/tourguide/cards/{id}/decide (her app tap).
push: tourguide_card -> ("Tour: aapki haan chahiye", "{say}")   (only when data.card.status == "waiting")
push: tourguide_alert -> ("Tour", "{say}")   (data.kind roll = a guest missing at roll call: high priority)
push: tourguide_day -> ("Aaj ke tour", "{say}")
  (tourguide_booking / tourguide_plan / tourguide_script: no push, cards only)
worker: app.tourguide.service.tick   (call every minute, e.g. `await asyncio.to_thread(tourguide.tick)`; once-keys: licence windows 90 / 60 / 30 / 7 / 0 days + 120 days for IITF / IITG refresher + once when expired, day-before reminder CARD for confirmed tours (never sent by itself), past confirmed tours "ho gaya?" nudge, DPDP forget nudge 90 days after the tour, morning note at her morning_time)
prompt: TOUR GUIDE: enquiries -> `tour_guide action=enquiry text=<her pasted text>` (only what is written is picked up; ask for the rest). Prices, monument timings, closed days and ticket rates come ONLY from her tours (`action=tour places=[...]`); never guess them, say "pata nahi, official board / site se pakka karein". Confirming a booking, any message to guests, refunds, discounts and spends are CARDS (`action=confirm|message|review|refund|discount|spend`): say "aapki haan ka card bheja hai", never that it is confirmed / sent / paid. Overbooking is refused by the code: offer another slot. Trains / flights for a group = `action=travel` (Yatra Sahayak).
persona: Tour ki baat mein monument ka samay ya ticket ka daam andaaze se kabhi mat bolo; booking pakki karne ya mehmaan ko message ke liye "aapki haan ka card bheja hai" kaho; koi mehmaan ginti mein na mile to turant group rokne aur phone karne ko kaho.
flutter: TourguideScreen in lib/ui/tourguide_screen.dart ; profile tile title "<name> · Tour guide" subtitle "Tour, booking, group file, din ka plan, safety, ginti, licence; pakki booking aapki haan se" icon Icons.tour_rounded ; cards: tourguide_card -> TourguideCardCard (also in calls: yes; one card per data['card']['id'], updated in place) ; tourguide_booking -> TourguideBookingCard (also in calls: no; key data['booking']['id'], updated in place) ; tourguide_plan -> TourguidePlanCard (also in calls: yes; data has 'plan' or 'safety') ; tourguide_script -> TourguideScriptCard (also in calls: yes) ; tourguide_alert -> TourguideAlertCard (also in calls: yes) ; tourguide_day -> TourguideDayCard (also in calls: no). All widgets take (app:, data:) (TourguideCardCard also optional onDone) and use only `app.api!.call(...)`, `Native.openExternal`, `Native.approveKeySign`.
features: tourguide
env: none
requirements: none (openpyxl / httpx already present)
android: none
neighbours: travel (v0.139 Yatra Sahayak: `travel_link` calls travel.service.new_trip for the group's trains / flights; fares / IRCTC windows / booking cards stay there, nothing copied), idvault (guest IDs + emergency number), approvekey (fingerprint kind "tourguide" on its own `/challenge` route, verified with approvekey._check like rentdesk / fleet), employee.inbox (business WhatsApp send on her tap), life (Open-Meteo geocode + forecast), officegen / chatfiles (roll-call sheet, register), feedback (optional survey link for review requests), net.ai.llm (place-name suggestions, translations; no-model fallbacks). Mehmaan suite: frontoffice / homestay (Form C for foreigners is the accommodation's duty, not the guide's), eventplan, shaadi, banquet - no overlap.
claude_md: |
  ## v0.1xx Tour Guide Sahayak: Hoola as a local guide's / small tour operator's coworker ("Tour guide" on the Employee page; Mehmaan suite)
  - Owner's spec: tour products (city walk, heritage, temple, trek, food tour) with HER price per person / group, duration, max group
    size -> bookings from her enquiries -> group file (guests, language, pickup, special needs, emergency contact in the locker) -> day
    plan with real places only -> safety brief + weather -> roll call -> guide licence renewals -> tips / commission register ->
    multilingual intro scripts -> review requests. Waits for her Haan on: booking confirmation / any message to guests, refunds /
    discounts, any spend. Server `server/app/tourguide/{rules,models,service,api}.py`, tools `tour_guide` / `tour_guide_dekho`
    (`agent/tourguide_tools.py`, chat + calls via santosh_kaam), duty `tour_work`, role + preset `tour_guide`, API `/api/tourguide/*`,
    app Profile > "<name> · Tour guide" (`lib/ui/tourguide_screen.dart`: Aaj / Booking / Tour / Licence · Hisaab / Niyam +
    `TourguideBookingPage`), cards TourguideCardCard (`tourguide_card`), TourguideBookingCard, TourguidePlanCard, TourguideScriptCard,
    TourguideAlertCard, TourguideDayCard. Tests `server/tests/test_host_tourguide.py` (6).
  - Tours TP-01: kind, city, duration, price per person OR per group (HER numbers; missing = "daam nahi bataya", confirmation
    refused), group_max (0 = bookings refused), min guests, meeting point, includes / excludes, languages, places [{name, stop_min,
    walk_min, open, close, closed_on, ticket_in, ticket_foreign, source, asi}] - timings / tickets ONLY as she typed (with where she
    read them); missing timings are listed as "pata nahi". `suggest` = AI place NAMES only (digits / prices stripped, Maps links,
    labelled "AI sujhav").
  - Bookings B-0001: `enquiry` (her pasted WhatsApp / call / OTA text = data, IDs captured into the locker first, scrubbed; only a
    written date (DD/MM, kal / parso), time (subah 7, 5 pm), guests (4 log / pax), phone, email, language are picked up; the rest is
    listed as missing), group file (guest list with age + nationality; an ID goes to the Pehchaan Locker and only "Aadhaar XXXX XXXX 0124"
    + {id:} stays; emergency number = locker kind other + masked). `hold` / confirm check the slot IN CODE: guests > group size,
    same tour slot over group size (Overbooking), or another of her tours overlapping beyond `parallel_tours` (her team size) = refused.
    Past dates refused; price_total only by the owner.
  - Cards (`tourguide_card`, C-0001, sha256 hash of what is shown + the booking as it is now; any change = stale): confirm (exact
    message with date / time / meeting point / total / advance / includes / HER cancellation policy upfront (Consumer Protection:
    terms shown before the booking; no policy = no confirmation), UPI deep link to HER UPI ID, "hum kabhi OTP / PIN nahi maangte";
    blanks block it), message (reminder / review / custom; OTP / card text refused), refund (<= what she received; policy shown),
    discount (amount or %), spend (amount from her bill / quote only). ONLY `POST /api/tourguide/cards/{id}/decide {yes, hash, via}`
    (by_tap) acts: confirm re-checks the slot at the tap then marks the booking confirmed; via self = she sends from her own WhatsApp
    (the app opens wa.me first), via business = her business number only if the guest wrote to it (Meta 24 h window in
    employee.inbox). Refund / spend need her fingerprint once a phone key is active (428 -> `/challenge`, approvekey message kind
    "tourguide"); she pays herself and taps "Maine de diya" (`paid_out` -> register). Hoola never moves money.
  - Day plan: arrive / leave per stop from her start time + stop minutes (+ walk), clashes with HER opening hours, closed weekday
    warnings, ticket total only from her rates for Indian vs foreign guests (an ASI place without a rate = "rate pata nahi"), ASI
    ticket steps (counter or ASI's ONDC apps; she books). Safety brief by kind (heritage / temple / trek with checklist: trained leader,
    fitness declaration, permits, insurance, turn-back time / food / boat...) + special needs (wheelchair, seniors, children, asthma,
    allergy...) + group size; weather = Open-Meteo via life.geocode / life.weather only for today / tomorrow (rain >= 60% -> rain plan /
    postpone treks; >= 38 C heat; <= 5 C cold). Roll call by names or count: anyone missing = `tourguide_alert` at once ("group rokiye,
    phone kijiye, 15 min mein 112"); roll-call Excel with a column per stop. Intro script templates hinglish / hi / mr / en; other
    languages via the model, kept only if every number / phone survived. Review request only after "done", for everyone (no review
    gating), with her review link or a Feedback Sahayak survey link. `travel` opens a Yatra Sahayak trip for trains / flights.
  - Licences: IITF / IITG Heritage / IITG Adventure (MoT), old RLG, state licence, site permit, first aid, adventure; reminders at
    90 / 60 / 30 / 7 / 0 days, +120 days for IITF / IITG (2-week IITTM online refresher, register well before 4 months), expired =
    "don't guide at monuments without a valid licence". Register: payments she received, tips, commission in / out (commission line
    reminds: tell guests, never force shopping), spends / refunds from cards; month net. GST is a note only (guide services SAC
    998556 18%; tour packages SAC 998555 5% without ITC or 18% with ITC; her CA decides). DPDP `forget` after the tour: names / phones /
    pickup / needs blanked, locker IDs deleted, counts and money kept; nudge after 90 days.
  - Never: inventing prices, timings, ticket rates, availability or reviews; sending anything / confirming / refunding by itself;
    logging in to OTAs / ASI / IRCTC portals; storing plain ID numbers.
  - Sources (23 Oct 2026): tourism.gov.in IITFC modified guideline 11 Jan 2021 (iitf.gov.in; IITF basic / IITG Heritage / Adventure;
    certificate + badge 5 years; IITTM 2-week online refresher, register before 4 months; registration 3 years + 2 at 50%, Rs 2,000 +
    Rs 500 exam); tourism.gov.in Lok Sabha USQ 2713 (17 Mar 2020: MoT stopped RLG licences from 2 Mar 2020); punjabtourism.punjab.gov.in
    state guide licence guidelines; theweek.in 6 Jan 2026 + newsonair.gov.in (ASI online tickets for 170+ monuments on ONDC apps:
    Highway Delite, Pelocal WhatsApp, Abhee; online discount Rs 5 / Rs 50 continues); busy.in SAC 998556 (tourist guide 18%) and 998555
    (tour operator 5% without ITC, after 22 Sep 2025); taxaj.com (tour operator 5% / 18%, TCS only on overseas packages);
    tourism.ladakh.gov.in Trekking regulations (example of state trek rules); Consumer Protection Act 2019 (terms upfront); DPDP Act
    2023 + Rules 2025.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/tourguide_screen.dart (Dart 3 records in _form field lists with collection-if, switch expressions as arguments). Open-Meteo calls were faked in tests (life.geocode / life.weather monkeypatched). Business-WhatsApp send tested only with a fake inbox.send. Fingerprint path tested with approvekey.active_on patched (same as rentdesk / fleet), not a real phone. The model paths (place suggestions, translated intro scripts) were tested with stubbed answers only. GST SAC numbers come from busy.in summaries (998552 vs 998555 differ between pages for tour operators) - shown as notes for her CA. State guide-licence validity varies by state: only the dates she types are used. The Feedback survey link path (review with survey=true) is best-effort and not covered by tests.
