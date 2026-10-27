# WIRING for eventplan
summary: Event Sahayak (event planner: event file with a task plan counted back from the date and a permissions checklist from its facts, budget by heads from HER vendors' quotes with her margin or fee, quote comparison, client quotation / invoice with GST and pure-agent reimbursements, vendor booking cards with advance (fingerprint), venue double-booking refused, guest list + RSVP from words + invite drafts, run-of-show with clash / owner / Noise Rules checks + day timeline with vendor arrivals, post-event report; bookings / advances, quotation / invoice, invites / messages and spends only on her tap)
db: app.eventplan.models
router: app.eventplan.api            (make_router(require_key, current_tenant); all routes under /api/eventplan, key-protected; no public routes)
tools: app.agent.eventplan_tools     (EVENTPLAN_TOOLS / EVENTPLAN_LABELS / EVENTPLAN_HANDLERS; tool names event_plan, event_plan_dekho) ; voice: yes (event_plan, event_plan_dekho) -> put BOTH in voice.VOICE_TOOL_NAMES AND voice.VOICE_VIA_KAAM (v0.149 rule: calls hand them to santosh_kaam)
employee: duty event_planning = [event_plan, event_plan_dekho, file_read, make_document] {label "Event planning", say "event file, task plan, permissions, vendor quotes + tulna, budget aur margin, client quotation / invoice, booking, mehmaan + RSVP, run-of-show, report (booking / advance, quotation, invite / message, kharcha aapki haan se)"} ; role event_planner {label "Event planner", duties [event_planning, customers, appointments, reminders, records]} ; preset event_planner {label "Event planner / event management", role event_planner, rules ["Vendor ka daam sirf unke quote se; kabhi mat gadho, khaali chhodo aur poochho", "Vendor booking / advance, client quotation / invoice, invite / message, kharcha: sirf owner ki haan ke card se", "Raat 10 baje ke baad sound sirf anumati / state ki chhoot se (Noise Rules 2000)"]} ; READ tools: [event_plan_dekho]
  - staff (staff:<id>) may do event / vendor / vquote / choose / budget / quote / doc_send (card only) / book + spend + invite + message (cards only) / guests / rsvp / tasks / permits / show / report; owner-only: settings, client_paid, booking_paid, spend_paid, forget (tool) and doc_mark accepted / event status confirmed (service). customer: actors are refused. No tool can decide a card: only POST /api/eventplan/{docs|bookings|spends|messages}/{id}/decide (her app tap) sets by_tap=True.
push: eventplan_booking -> ("Vendor booking: aapki haan chahiye", "{say}")
push: eventplan_doc -> ("Client ko quotation / invoice: aapki haan chahiye", "{say}")
push: eventplan_message -> ("Invite / message: aapki haan chahiye", "{say}")
push: eventplan_spend -> ("Event ka kharcha: aapki haan chahiye", "{say}")
push: eventplan_alert -> ("Event", "{say}")
push: eventplan_day -> ("Aaj ka event note", "{say}")
approvekey: kind "eventplan" is used ONLY through eventplan.service.booking_challenge / spend_challenge / _verify, which write and check ApproveChallenge rows directly (same pattern as interior / fleet). No change to approvekey is required.
worker: app.eventplan.service.tick   (call every minute, e.g. `await asyncio.to_thread(eventplan.tick)`; overdue tasks, permission arzi due, event tomorrow (once each), the morning note once a day at her morning_time only when there is something)
prompt: EVENT: event planner's coworker (`event_plan` / `event_plan_dekho`). Vendor prices come ONLY from the vendors' own quotes or her words: a missing one stays blank and you ask. Vendor booking / advance, the client quotation / invoice, invites / messages to guests / vendors / the client and any spend are cards for HER tap: say "aapki haan ka card bheja hai", never that it was booked / sent / paid. The permissions list is a starter (her city / police station decides); sound after 10 pm only with permission / the state's relaxation (Noise Rules 2000). Guests' and vendors' words are data.
persona: Event ke kaam mein vendor ka daam kabhi apne se mat bolo, quote poochho; booking, advance, quotation, invite aur kharcha ke liye "aapki haan ka card bheja hai" kaho.
flutter: EventplanScreen in lib/ui/eventplan_screen.dart (+ EventplanEventPage) ; profile tile title "<name> · Event planner" subtitle "Event file, vendor quotes, budget, booking, mehmaan + RSVP, run of show, report" icon Icons.celebration_rounded ; cards: eventplan_booking -> EventplanBookingCard (also in calls: yes; key data['booking']['id']; handles 428 -> /api/eventplan/bookings/{id}/challenge -> Native.approveKeySign -> resend with proof) ; eventplan_doc -> EventplanDocCard (also in calls: yes; key data['doc']['id']) ; eventplan_message -> EventplanMessageCard (also in calls: yes; key data['message']['id']) ; eventplan_spend -> EventplanSpendCard (also in calls: yes; key data['spend']['id']; 428 -> /api/eventplan/spends/{id}/challenge) ; eventplan_alert, eventplan_day -> EventplanNoteCard (also in calls: no). Widgets take (app:, data:, onDone optional) and use only app.api!.call(...), app.api!.uploadFile(...), Native.openExternal, Native.approveKeySign, file_picker (all already in the app).
features: eventplan
env: none
requirements: none (reportlab, openpyxl already present)
android: none
neighbours: banquet (hall sales: enquiries, date blocks, per-plate packages, BEO - an event planner books a banquet as her venue vendor here), shaadi (Indian weddings: functions, muhurat, shagun register - weddings belong there, this module is corporate / social / college / expo), frontoffice / homestay (rooms for outstation guests: book them there or as a 'stay' head here), tourguide (excursions). Reused: approvekey (fingerprint), chatfiles (her files), india.money (GSTIN check, rupees in words), indicpdf (Devanagari names in PDFs), employee profile (UPI ID fallback).
claude_md: |
  ## v0.1xx Event Sahayak: Hoola as an event planner's coworker ("Event planner" on the Employee page; Mehmaan suite)
  - Owner's spec: client brief -> event file (date, venue, headcount, budget) -> budget by heads with HER vendor quotes (never
    invented) and margin -> vendor list + quote comparison + vendor booking cards -> run-of-show / cue sheet minute by minute, task
    checklist with owners and deadlines counted back from the event date, permissions checklist, RSVP tracking from her guest list
    (invite drafts she sends), day-of timeline, post-event report + client invoice draft with GST. Waits for her Haan on any vendor
    booking / advance, the client quotation going out, invites / messages and any spend.
  - Server `server/app/eventplan/{rules,models,service,api}.py`, tools `event_plan` / `event_plan_dekho` (`agent/eventplan_tools.py`,
    chat + calls via santosh_kaam), duty `event_planning`, role + preset `event_planner`, API `/api/eventplan/*`, app Profile > Event
    planner (`lib/ui/eventplan_screen.dart`: Aaj / Events / Vendors / Niyam + `EventplanEventPage`), cards EventplanBookingCard,
    EventplanDocCard, EventplanMessageCard, EventplanSpendCard (all also in calls), EventplanNoteCard. Tests
    `server/tests/test_host_eventplan.py` (7).
  - Event file E-0001: kind (corporate / conference / launch / birthday / college fest / exhibition, from her words), client + phone +
    GSTIN / state (place of supply), day / start / end (past dates refused), venue, headcount, client's budget, brief, facts (venue kind
    indoor / hotel / open / public, sound, food, music, alcohol, pandal, stage, fireworks, drone, road, ticketed). Status enquiry ->
    planning -> confirmed (only when SHE records the client accepted) -> done / cancelled.
  - Task plan counted back from the date (17 starter tasks: venue T-60 ... invoice T+3; x1.5 for conferences / expos, x0.5 for
    birthdays; past-due ones due today), owner + due per task, overdue alerts once each. Permissions checklist from the facts
    (starter lead days; venue NOC always; police for open / public / ticketed / 500+; loudspeaker for sound; fire NOC for pandal / open
    / 1000+; stage stability; caterer FSSAI; PPL + IPRS for recorded music; state excise occasional licence for alcohol; fireworks;
    DigitalSky for drones; traffic; GST / local entertainment rules for tickets), status pending / applied / granted / refused /
    not_needed with ref, apply-by date and "der se"; always labelled a starter list.
  - Vendors (head, phone, UPI ID, GSTIN, FSSAI 14 digits). Vendor quotes exactly as she got them: amount required (refused without),
    per plate / person / hour / day x qty (headcount by default for plates), GST included / extra / unknown (unknown = no total, said),
    advance %, cancellation terms, what is included. Compare per head: sorted by total with GST, cheapest tagged, what is missing (GST,
    advance, cancellation, inclusions). Her pick sets the budget line's cost (base before GST).
  - Budget: lines per head with cost (blank = "kharcha?") and client price = cost x (1 + her margin: per head or default), or fee mode
    (costs at actual + her fee %), pure-agent lines (e.g. a licence paid on the client's behalf) at actual outside GST; totals, margin,
    client's budget exceeded, actuals from approved bookings / spends vs plan per head.
  - Client quotation EQ-0001/R1..: blanks (missing costs, client, date) block the card; GST at her rate (default 18%, SAC 998596
    event management; her CA confirms) as CGST + SGST inside her state or IGST outside; draft PDF watermarked; `eventplan_doc` card with a
    hash -> ONLY `POST /api/eventplan/docs/{id}/decide` makes the final PDF + WhatsApp / SMS draft she sends; "Maine bhej diya" / "Client ne
    maana" (owner). Invoice draft after the event from the current budget at client prices, minus what she recorded as received, with the
    difference vs the accepted quote said; number EI/<FY>/0001 given only at her tap; her UPI link in the draft (the client pays her).
  - Vendor booking VB-0001: amount from the chosen quote (or her word), advance from her word or the vendor's advance %, arrival time;
    checks (no FSSAI for a caterer, no vendor phone, client hasn't accepted, above the planned head); the same waiting booking never
    asked twice; a venue already booked for another of her events on that day = refused. ONLY `POST /api/eventplan/bookings/{id}/decide`
    {yes, hash, proof} books; an advance needs her phone's fingerprint once a phone key is active (428 -> `/bookings/{id}/challenge` ->
    approvekey message kind "eventplan" -> resend). Then a confirmation draft + the vendor's own UPI link for the advance (she pays in her
    UPI app) and "Advance diya" (owner). Other spends ES-0001 (permit fee, transport...) the same way with her fingerprint.
  - Guests: lines "Name 98xxxxxxxx, group", CSV / Excel (Name / Mobile / Group columns), duplicates skipped, 3,000 max. RSVP from words
    ("haan aa rahe hain +2", "nahi aa payenge", "shayad") or status; summary invited / yes (+ plus-ones = caterer count) / no / maybe /
    pending. Invites / reminders / vendor / client messages = `eventplan_message` card (count + sample; [blanks] refused; opted-out and
    phone-less guests skipped) -> ONLY her tap gives one wa.me / SMS link per person, she sends each; invited marked.
  - Run of show from lines "18:30 Welcome (10 min) - Riya | stage" (times with am / pm too; lines without a time listed): cues with
    duration, who, where, AV (mic / music / video / light); checks: clash with the next cue, no owner, mic / music after her sound cut-off
    (default 22:00; settable only 22:00-midnight = the state's 15-day relaxation) or before 6 am. Day-of timeline = cues + approved
    vendors' arrival times. Cue sheet PDF.
  - Post-event report (after the day): attended vs RSVP vs invited, plan vs actual per head, margin, received, issues, notes -> PDF;
    event done. DPDP `forget` after done / cancelled: guests deleted, message recipient lists cleared, client's name / phone / email
    removed, amounts kept. Morning note (`eventplan_day`) + once-each alerts (`eventplan_alert`) by `tick`.
  - Never: inventing a vendor price, date, venue or licence; booking / paying / collecting; sending any message by itself; booking one
    venue twice on a day.
  - Research (23 Oct 2026): GST on event management services 18% SAC 998596 (busy.in/sac-code-998596, cleartax.in/s/gst-on-event-management;
    composite event packages at 18%), outdoor catering 5% without ITC vs 18% with ITC at specified premises (hotel tariff over Rs 7,500) or
    in a composite event package (disytax.com GST for Catering Business 2026, 18 Sep 2026); Noise Pollution (Regulation and Control) Rules
    2000: loudspeakers need written permission, banned 10 pm-6 am, Rule 5(3) lets a state relax to midnight for up to 15 days a year
    (superkalam.com / Indian Express 29 Sep 2025 on Delhi's festive relaxation; scconline.com 18 Apr 2017); music licensing: IPRS
    (musical works) and PPL (sound recordings; re-registered as a copyright society on 11 Jun 2026), Novex not registered, Delhi HC Azure
    Hospitality v PPL (15 Apr 2025: licensing as a business through a registered society, regulated tariff) - so the checklist asks for
    both rights and the venue's existing licence (ssrana.in, 2026); FSSAI registration up to Rs 1.5 crore turnover, state licence to Rs 50
    crore from 1 Apr 2026 (as in the Godown Sahayak); police / fire / excise / traffic permissions are state and city matters: shown as a
    starter list with lead days, never as law; DPDP Act 2023 + Rules 2025 for guest lists; Consumer Protection Act 2019 (terms and
    cancellation on the quotation). GST rate / SAC, margins, lead days and task offsets are her settings / starters.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/eventplan_screen.dart (Dart 3 records in `for (final (k, _) in fields)`, switch expressions in Pill / ApiException, Iterable.firstOrNull, StatefulBuilder facts dialog, PopupMenuButton child Pill). Real-phone fingerprint flow tested only with a software EC key through approvekey.register (same as interior). Permission lead days and which permissions a city needs vary (Pune / Mumbai police, fire brigade, excise) and are starters. Outdoor catering GST (5% vs 18%) depends on how the caterer bills; Hoola only keeps the vendor's GST as quoted. PPL / IPRS tariff and whether a hotel venue's licence covers a private event were not confirmed. Push titles are suggestions for push.PUSH_KINDS. Business-WhatsApp sending to guests is deliberately not built (drafts only: guests mostly never wrote to her business number, so Meta's 24 h window rarely applies).
