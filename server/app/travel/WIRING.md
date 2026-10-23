# WIRING for travel
summary: Yatra Sahayak (travel agent: trips T-0001 for her family or agency clients, traveller IDs only as Pehchaan Locker references, day-by-day plan with only real places and no invented times / fares, pasted quotes or her Amadeus key compared by price / time / rating, IRCTC booking windows (60-day ARP, Tatkal 10 / 11 am with Aadhaar OTP, chart time), documents checklist with passport 6-month / visa / Schengen insurance notes, packing, reminders, client quote PDF with her markup; booking only on her tap, Hoola's browser stops at payment, she pays)
db: app.travel.models
router: app.travel.api            (make_router(require_key, current_tenant); all routes under /api/travel, key-protected; no public routes)
tools: app.agent.travel_tools     (TRAVEL_TOOLS / TRAVEL_LABELS / TRAVEL_HANDLERS) ; voice: yes (travel, travel_dekho)
employee: duty travel_work = [travel, travel_dekho, order_karo, file_read] {label "Travel agent", say "yatra ka plan, train / flight / hotel ki tulna, kaagaz taiyaar, Tatkal / check-in yaad (booking aur payment aapki haan se)"} ; role travel_agent {label "Travel agent", duties [travel_work, customers, reminders, records]} ; preset travel_agency {label "Travel agency / tour operator", role travel_agent, rules ["Booking sirf owner ke tap ke card se; payment owner khud karti hain", "Kiraya / samay kabhi andaaze se mat likho", "ID number sirf Pehchaan Locker reference se"]} ; READ tools: [travel_dekho]
  - staff (staff:<id>) may plan trips, add options / travellers, compare, ask for booking / quote cards; owner-only actions: settings, cancel, forget, booked. Customers (customer:*) are refused. No tool action can approve: only POST /api/travel/bookings/{id}/decide and POST /api/travel/quotes/{id}/decide (her app tap).
push: travel_booking -> ("Yatra: booking ki haan chahiye", "{say}")   (only when data.status == "waiting")
push: travel_quote -> ("Graahak ka quote taiyaar", "{say}")
push: travel_reminder -> ("Yatra yaad", "{say}")
push: travel_day -> ("Aaj ki yatra", "{say}")
  (travel_trip: no push; card only)
worker: app.travel.service.tick   (call every minute, e.g. `await asyncio.to_thread(travel.tick)`; each reminder once per trip: booking opens (ARP 08:00), Tatkal 30 min before, chart time (booked trains), web check-in window, passport validity, eve of the trip with missing documents; morning note at her morning_time when a trip is within 7 days or a card waits; marks booked trips done after the end date)
prompt: YATRA: trips -> `travel action=new` (dates, travellers, budget, wishes); plan with `action=itinerary`; fares / timings ONLY from what she pasted (`action=options`) or her partner key, never guessed; IRCTC has no public API, so give the IRCTC / RailOne link + `travel_dekho what=train` windows. Booking = `travel action=book` -> a card for HER tap; never say it is booked / approved; after her tap Hoola's browser stops at payment and she pays. Traveller IDs only as {id:...} locker references; never read a full ID out.
persona: Yatra mein kiraya ya samay andaaze se kabhi mat bolo; booking ke liye "aapki haan ka card bheja hai, pay aap karengi" kaho; Tatkal / check-in ka samay yaad dilao.
flutter: TravelScreen in lib/ui/travel_screen.dart ; profile tile title "<name> · Travel agent" subtitle "Yatra plan, train / flight / hotel tulna, kaagaz, Tatkal yaad; booking aapki haan se" icon Icons.luggage_rounded ; cards: travel_booking -> TravelBookingCard (also in calls: yes; one card per data['id'], updated in place) ; travel_quote -> TravelQuoteCard (also in calls: yes; key data['id']) ; travel_trip -> TravelNoteCard (also in calls: no; key data['trip']['id']) ; travel_reminder -> TravelNoteCard (also in calls: yes) ; travel_day -> TravelNoteCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)` + `Native.openExternal`. Also existing kind pc_file is published for the quote PDF (source "travel").
features: travel
env: none (her Amadeus key / secret are typed in the app: PUT /api/travel/partner, sealed with the bazar vault)
requirements: none (httpx, reportlab already present)
android: none
neighbours: shop (Order karo: IRCTC / redBus / MakeMyTrip playbooks + Computer Operator that stops at payment; decide_booking calls shop.service.order), operator (OTP / CAPTCHA by her), idvault (traveller IDs), india.days (holidays near the trip), chatfiles (quote PDF), maps (links only). Safar suite: logistics, fleet, warehouse, courier, drivers, customs (none overlap: this one is passenger travel).
claude_md: |
  ## v0.1xx Yatra Sahayak: Hoola as a travel agent ("Travel agent" on the Employee page)
  - Owner's spec: builds itineraries -> compares hotels and trains -> keeps documents ready -> waits for her Haan on BOOKING AND
    PAYING (Hoola never pays). Server `server/app/travel/{rules,models,adapters,service,api}.py`, tools `travel` / `travel_dekho`
    (`agent/travel_tools.py`, chat + calls), duty `travel_work`, role `travel_agent`, preset `travel_agency`, API `/api/travel/*`,
    app Profile > "<name> · Travel agent" (`lib/ui/travel_screen.dart`: Aaj / Trips / Niyam + `TravelTripPage`), cards
    TravelBookingCard (`travel_booking`), TravelQuoteCard (`travel_quote`), TravelNoteCard (`travel_trip`, `travel_reminder`, `travel_day`).
    Tests `server/tests/test_logi_travel.py` (8).
  - Trips T-0001 for her own family (mode own) or her agency's clients (mode agency: client name / phone / email). Travellers: name,
    age, gender, berth; an ID number she gives goes into the Pehchaan Locker (`idvault.save`) and the trip keeps ONLY the {id:...}
    reference + masked form; free text (prefs / notes / pasted quotes) runs through `idvault.capture` (and card-like numbers are cut)
    before it is stored. Passport expiry date kept (not the number). DPDP: `forget` blanks client + travellers after done / radd.
  - Itinerary: model JSON (site.ai.ask_json) of real, well-known places only; code then replaces any clock time, rupee amount or phone
    number that is not in her brief with [samay?] / [daam?] / [number?]; Google Maps search link per place; her chosen transport is put
    on its day with its given time; no model = a plain day-by-day frame she fills. Labelled "AI ka sujhav: khulne ka samay khud check".
  - Options (train / flight / bus / hotel / cab): parsed from what she pastes (one per line: name, flight / train number, HH:MM-HH:MM,
    overnight duration, ₹ price, per night, rating x/5 or stars, refundable / non-refundable, class) or typed; unpriced = "daam pata
    nahi" and sorted last. Partner adapter interface (`adapters.py`, `set_transport` for tests): Amadeus Flight Offers Search with HER
    key / secret (typed only in the app, verified with the token call, sealed with the bazar vault, never returned), INR prices only.
    Comparison per mode: total (hotels x nights), cheapest / fastest / best rated tags, links (IRCTC, RailOne, redBus, MSRTC, Google
    Flights / Hotels, MakeMyTrip). IRCTC has no public API for third parties (only its own site / app and authorised agents / B2B
    partners under IRCTC agreements), so Hoola never scrapes it: links + her pasted results + the booking windows.
  - Rail rules (`rules.py`): ARP 60 days (journey day not counted), booking opens 08:00, first 15 minutes only Aadhaar-authenticated
    IRCTC users (from 1 Oct 2025; agents barred first 10 min); Tatkal one day before at 10:00 AC / 11:00 non-AC, online only for
    Aadhaar-authenticated users with Aadhaar OTP (15 Jul 2025), authorised agents barred 10:00-10:30 / 11:00-11:30; first chart 8 h
    before for departures after 2 pm, 9 pm previous night for 5 am-2 pm, 8 pm previous evening for midnight-5 am, final chart 30 min
    before; classes 1A..2S, quotas GN / TQ / PT / LD / SS / HP...; original photo ID list for trains and flights.
  - Documents checklist per trip (ticks + her file_id per item): train ID + e-ticket, Tatkal Aadhaar-verified account, flight ID +
    boarding pass + DigiYatra (optional; 38 airports), bus ticket, hotel voucher; abroad: passport valid 6 months after return (Schengen
    3 months, issued within 10 years), visa with the official portal (visa type is NOT guessed: only Nepal / Bhutan no-visa are stated;
    others "official site par check karein"; UK / USA / Canada / Australia / Schengen = visa needed), return ticket, travel insurance
    (must for Schengen: EUR 30,000 medical), forex, photos; minors' age proof, seniors' age proof for lower-berth quota. Packing list by
    days / month / kind (hill, beach, pilgrimage, business) / abroad / kids. Holidays within 3 days of the trip from `india.days`
    (her state) -> "bheed aur kiraya zyada".
  - Booking (her tap, in code): `travel action=book` only makes a `travel_booking` card (B-0001: option, travellers with masked IDs,
    class / quota, price or "site par dikhega", Tatkal note, route, sha256 hash; booking an option also chooses it). ONLY
    `POST /api/travel/bookings/{id}/decide {yes, hash}` (by_tap) acts, refused when the option / travellers changed after the card.
    Yes -> `shop.service.order` (Order karo: IRCTC / redBus / MakeMyTrip playbook + Computer Operator; passengers with {id:...} refs the
    operator types from the locker; "Stop at payment") -> she does OTP / CAPTCHA / payment herself; status synced from the shop order
    (waiting_payment / placed -> booked with the PNR). Modes without a Hoola-run site -> "self" with the link. `booked` (owner) records
    PNR + what she paid; trip turns booked when every chosen option is booked.
  - Agency quote: chosen options with prices (missing price = refused, never guessed) + HER markup % / fixed + optional GST on her
    service charge (0 / 5 / 18, her CA decides) -> `travel_quote` card; ONLY `POST /api/travel/quotes/{id}/decide` makes the PDF
    (reportlab: plan days, lines, cost, charge, GST, total, per person, her terms) as her file + WhatsApp / email draft she sends;
    a newer quote makes older cards stale.
  - Reminders (`tick`, once each): booking opens, Tatkal (30 min before), chart time (booked trains: check PNR status), web check-in
    window (usually 48 h to 60 / 75 min before; airline decides), passport too short, eve of the trip with missing documents; morning
    note at her time.
  - Never: paying, guessing fares / timings / visa types, scraping IRCTC / airline / OTA sites, storing plain ID numbers, sending a
    quote / message to a client by itself.
  - Sources (23 Oct 2026): outlooktraveller.com "Indian Railways new rule: Aadhaar verification compulsory for early reservations"
    (1 Oct 2025, 60-day window, agents 10 min); theweek.in 16 Jul 2025 (Tatkal Aadhaar OTP, agents 30 min); angelone.in / scroll.in
    (Tatkal Aadhaar-authenticated users from 1 Jul 2025); savedelete.com IRCTC chart preparation time 2026 (secondary); superkalam.com
    15 Jun 2026 (DigiYatra 38 airports, voluntary); outlooktraveller.com (DigiYatra for international transit at DEL / BOM / BLR / HYD
    from 1 Jun 2026, press report); passportindia.gov.in; official visa portals listed in `rules.VISA`; Amadeus for Developers Flight
    Offers Search API.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI annotations for lib/ui/travel_screen.dart. Amadeus calls were tested only against an httpx MockTransport shaped from its documented responses; Amadeus has been changing its Self-Service developer programme, so check that her key still works (test vs prod host) before relying on it. The chart-time rule comes from a secondary 2026 article (labelled so; IRCTC can change it). The Order karo IRCTC / redBus / MakeMyTrip runs were not exercised here (shop.service.order is monkeypatched in tests); many of these sites refuse data-centre IPs (then v0.92 moves the job to her PC). Visa needs are deliberately not filled in beyond Nepal / Bhutan / clear visa-required countries. Web check-in windows are generic (airline rules differ). Push titles are suggestions for push.PUSH_KINDS.
