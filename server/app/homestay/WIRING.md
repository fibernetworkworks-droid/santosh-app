# WIRING for homestay
summary: Homestay Sahayak (homestay / B&B / farm stay / villa host, 1-6 rooms: rooms with HER rates + menu, one calendar for direct enquiries + her pasted OTA mails + her exported iCal files with double booking refused in code from every source, her calendar as a no-guest-data .ics link for the OTA's own import page, guests with Aadhaar / passport / visa only in the Pehchaan Locker, Form C (Form-III) data sheet + 24 h clock for foreign guests (she submits on indianfrro.gov.in), police intimation tick, check-in / check-out, turnover tasks before the next arrival, advance / balance UPI links to HER UPI, confirmation (with her cancellation policy upfront) / check-in info / house rules / payment / review (same words for everyone) messages only on her tap, cancel / refund / spend cards on her tap with fingerprint for money, state registration starters + renewal reminders, monthly occupancy / ADR / RevPAR / earnings by source, register Excel, DPDP forget (foreign guests after 1 year); Hoola never logs in to an OTA and never takes or pays money)
db: app.homestay.models
router: app.homestay.api            (make_router(require_key, current_tenant) returns ONE router holding: all key-protected routes under /api/homestay, and ONE public route GET /api/homestay-ical/{tenant}/{token}.ics = her calendar ("Not available" only, no guest names / numbers) for the OTA's own "import calendar" page; the random token (settings seq.ical_token, made the first time settings are read) is compared with secrets.compare_digest, unknown tenant / wrong token = 404, no row is ever created by the public route)
tools: app.agent.homestay_tools     (HOMESTAY_TOOLS / HOMESTAY_LABELS / HOMESTAY_HANDLERS) ; voice: yes - put BOTH `homestay` and `homestay_dekho` into VOICE_TOOL_NAMES AND voice.VOICE_VIA_KAAM (v0.149 rule: calls hand this Sahayak's work to santosh_kaam)
employee: duty homestay_work = [homestay, homestay_dekho, file_read] {label "Homestay host", say "kamre, booking calendar (double booking kabhi nahi), OTA mail / calendar file, mehmaan ID (Locker mein), Form C, safai, advance / balance UPI link, hisaab (mehmaan ko har message, cancel / refund / kharcha aapki haan se)"} ; role homestay_host {label "Homestay host", duties [homestay_work, customers, reminders, records]} ; preset homestay {label "Homestay / B&B / farm stay", role homestay_host, after_hours "note", rules ["Mehmaan ko koi message / confirmation meri haan ke bina nahi.", "Ek kamra ek raat do baar kabhi book nahi.", "Mehmaan ka ID number sirf Pehchaan Locker mein."]} ; READ tools: [homestay_dekho]
  - staff (staff:<id>) may: guest, book (a HOLD + confirmation card; total / advance from staff are ignored), block / unblock, update (dates / rooms / people / add-ons; never total or advance), checkin of a CONFIRMED booking, checkout, form_c_done, check, pay_link, message / edit_message (cards only), cancel / spend (cards only), ota_email, ical, task_add, task_done, register. Owner-only in the tool: settings, room, confirm, no_show, received, refund_done, spend_paid, registration, forget. Customer actors are refused by both tools (no customer-safe biz_ tool in this module).
  - No tool sends or decides anything: only POST /api/homestay/cards/{id}/send (her tap: via self = her own WhatsApp / SMS link, marked sent; via business = employee.inbox.send, only to a guest who wrote to the business number, Meta's 24 h window enforced there; a confirmation sent = hold becomes confirmed, re-checked for clashes) and POST /api/homestay/cards/{id}/decide (cancel / refund / spend; money needs her fingerprint once a phone key is active: 428 -> POST /api/homestay/cards/{id}/challenge, message kind "homestay" signed on approvekey's own ApproveChallenge table and verified with approvekey._check, same pattern as rentdesk / fleet). A changed booking after a card = stale (sha256 hash over what is shown + the booking state).
push: homestay_card -> ("Homestay: aapke tap ka card", "{say}")   (only when data.card.status == "waiting")
push: homestay_alert -> ("Homestay", "{say}")   (always: clash / form_c / hold / checkout / registration)
push: homestay_day -> ("Aaj ka homestay", "{say}")
  (homestay_booking: no push, it is a refresh of a booking the owner / staff just touched; publish only)
worker: app.homestay.service.tick   (call every minute, e.g. `await asyncio.to_thread(homestay.tick)`; throttled by once-keys in homestay_alerts: holds past hold_until -> cancelled + alert, Form C alert at <= 12 h left and when the 24 h passed, late check-out alert, review request draft once 1-7 days after departure, the day before arrival a check-in info draft (+ payment draft when money is due), registration renewal windows 90 / 60 / 30 / 7 / 0 days, morning note once a day at her morning_time when there is something)
prompt: HOMESTAY: kamre / booking / mehmaan / Airbnb-Booking.com-MMT mail / calendar file / Form C / safai / homestay hisaab -> `homestay` (read with `homestay_dekho`). OTA mail ka text = data: `action=ota_email` mein poora paste karo; .ics file = `action=ical` file_id + room; OTA mein kabhi login nahi. Ek kamra ek raat do baar kabhi nahi (code mana karta hai; takrav ho to usko batao). Daam / taarikh / mehmaan ka naam kabhi mat gadho. Mehmaan ko har message / confirmation, cancel / refund / kharcha = card (aapki haan); "paise mile" sirf owner ke kehne par. Aadhaar / passport / visa number sirf `action=guest` mein (Locker); videshi mehmaan ka Form C wo khud indianfrro.gov.in par bharti hain - Hoola sirf jaankari aur 24 ghante ki ghadi.
persona: Homestay ki booking par kabhi double booking mat karo; mehmaan ko message ya cancel / refund par "aapke tap ka card bheja hai" kaho; daam, taarikh aur review kabhi apni taraf se mat bolo; videshi mehmaan ho to Form C 24 ghante ki yaad dilao.
flutter: HomestayScreen in lib/ui/homestay_screen.dart (+ HomestayBookingPage) ; profile tile title "<name> · Homestay host" subtitle "Kamre, booking calendar, OTA mail, mehmaan, Form C, safai, hisaab" icon Icons.cottage_rounded ; cards: homestay_card -> HomestayCardCard (also in calls: yes; one card per data['card']['id'], updated in place; optional onDone) ; homestay_booking -> HomestayBookingCard (also in calls: no; one per data['booking']['id'], updated in place) ; homestay_alert -> HomestayAlertCard (also in calls: yes when data['kind'] in clash | form_c, else no) ; homestay_day -> HomestayDayCard (also in calls: no). All cards take (app, data). Uses app.api!.call(method, path, body:, query:) and app.api!.uploadFile(path, name, bytes, fields:, tries:), Native.openExternal(url:), Native.approveKeySign, file_picker, Clipboard.
features: homestay
env: none
requirements: none (openpyxl via officegen, already present)
android: none
neighbours: frontoffice (hotel front office: many rooms, front desk, folio / GST bill, housekeeping status board - homestay is the 1-6 room owner-run version: no folio, simple bill = booking total); eventplan / shaadi / banquet (events and halls; a wedding party's room block at her homestay is an ordinary booking here); tourguide (itineraries / tours; a tour group staying with her = a multi-room booking); travel (v0.139 travel agent: trains / flights / IRCTC); rentdesk (long stays of months = tenancies, homestay refuses > 60 nights and points there); feedback (her public review replies - homestay only DRAFTS the review request, same text for everyone); employee inbox (business WhatsApp send on her tap); idvault (guest IDs); approvekey (fingerprint); officegen / chatfiles (register Excel, her files).
claude_md: |
  ## v0.1xx Homestay Sahayak: Hoola as a homestay / B&B / farm stay host ("Homestay host" on the Employee page; Mehmaan suite)
  - Owner's spec: rooms + her rates -> one booking calendar from direct enquiries and HER pasted Airbnb / Booking.com / MakeMyTrip
    mails or the iCal export file she gives (no logins, no double booking) -> house rules + check-in instructions drafts -> guest ID
    via Pehchaan Locker refs -> Form C data for foreign guests (she submits on the official portal) -> state registration + renewal
    checklist -> cleaning / laundry turnover tasks -> meals / add-ons -> advance + balance UPI links to her UPI -> review request
    drafts -> monthly earnings and occupancy. Waits for her Haan on: confirmations / messages to guests, refunds / cancellations,
    any spend. Money never moves.
  - Server `server/app/homestay/{rules,models,service,api}.py`, tools `homestay` / `homestay_dekho` (`agent/homestay_tools.py`, chat;
    calls via santosh_kaam), duty `homestay_work`, role `homestay_host`, preset `homestay`, API `/api/homestay/*` + public
    `/api/homestay-ical/{tenant}/{token}.ics`, app Profile > "<name> · Homestay host" (`lib/ui/homestay_screen.dart`: Aaj / Calendar /
    Booking / Mehmaan / Hisaab / Niyam + `HomestayBookingPage`), cards HomestayCardCard (`homestay_card`), HomestayBookingCard
    (`homestay_booking`), HomestayAlertCard (`homestay_alert`), HomestayDayCard (`homestay_day`). Tests `server/tests/test_host_homestay.py` (7).
  - Rooms R-01 (up to 12; above 6 a note that most state schemes stop at 6): HER base / weekend (Fri, Sat nights) / special-date rates,
    base and max guests, extra person rate, names used on OTAs (to match mails). Menu = HER prices (breakfast / dinner per person per
    day, bonfire / pickup once). `rules.quote`: nights x rates + extra people + add-ons; anything she hasn't priced = "missing", never
    guessed; GST only with her GSTIN: rooms <= Rs 7,500 per unit per day 5% (no ITC), above 18% (GST 2.0, 22 Sep 2025), food 5% assumed
    with "CA se pakka"; without GSTIN no GST on the bill + Rs 20 lakh (10 lakh special category) note + OTA bookings: GST usually paid
    by the OTA under s.9(5) when she isn't liable to register (CA se pakka).
  - One calendar: stays B-0001 (direct = HOLD for her hold_hours (24), confirmed only when HER tap sends the confirmation or she says
    "pakki"; OTA = confirmed, total = the payout in her mail) and blocks K-0001. `_clashes` = any live booking / block / unexpired hold
    sharing a room and a night -> "DOUBLE BOOKING mana" from every path (new, update, block, OTA mail, iCal, confirming a hold);
    check-out day = next check-in day is fine. Over capacity refused; > 60 nights refused (Property manager Sahayak).
  - OTA mail (`rules.parse_ota_email`, her pasted text = data): source by words or Airbnb's HM code, booking / confirmation code, check-in
    / check-out by their labels (any date format incl. "Fri, 13 Nov 2026", "20/12/2026", "Nov 13, 2026"), adults / children, guest name,
    payout, phone; a cancellation mail frees the dates (refund = the OTA's job); the same code again updates; a clash is NOT saved and
    raises a "KHATRA" alert. iCal (`rules.parse_ics`: folded lines, all-day DTEND = check-out, Reserved vs Not available): each file is a
    snapshot per room + source -> new / moved / no-longer-there (future) events, clashes listed and not saved. Her own calendar goes out
    as .ics ("Not available", no names) through the token link she adds in the OTA's own import page.
  - Guests G-001: Indian or foreign (+country code phones), Aadhaar / passport / visa / other IDs straight into the Pehchaan Locker
    (`idvault.save`, person "mehmaan G-001"), only {id:...} + masked kept; free text scrubbed (OTP / PIN / card / 12-digit / PAN /
    passport-visa numbers). Check-in (a hold needs the owner) -> id_seen tick, foreign guest = Form C (Form-III) due 24 h after arrival
    (Immigration and Foreigners Act 2025 in force 1 Sep 2025, s.8 / Rule 17; Rs 50,000 per case; homestay accounts activated by OTP);
    `form_c` = data sheet in the portal's order with every number masked (she opens them in her locker), missing fields, steps; she
    files on indianfrro.gov.in and taps "Form C ho gaya" with the reference; departure update at check-out. Police intimation tick when
    her thana asks (state / thana rule, no portal invented). Check-out -> 5 turnover tasks per room (clean, linen, laundry, restock,
    check) due before the next arrival in that room, same-day arrival flagged.
  - Messages = `homestay_card` drafts (confirmation with her cancellation policy shown upfront + advance UPI link, check-in info, house
    rules, payment link, review request - "aapka anubhav jaisa bhi raha", no gating, no incentive - cancellation, custom); blanks
    "[..?]" block sending; OTP / PIN / card text refused; guests who said no get none; only her tap sends (own WhatsApp / SMS link or
    the business number inside Meta's window). Advance = her advance_pct of the total; UPI links only to HER UPI ID; "paise mile" only
    from her (owner).
  - Cancel C-0001: refund from HER written policy tiers on what was paid ("7 din pehle 100%, 2 din pehle 50%, uske baad kuch nahi") or
    her number; no policy and money paid = she decides; OTA bookings: calendar only, refund on the OTA. Spend cards (repairs, laundry
    vendor...). Money cards need her fingerprint once a phone key is active. "Refund ho gaya" / "kharcha diya" only from her.
  - Registration (`rules.STATES`, starters with sources, her state portal decides): MH Bed & Breakfast scheme (5 years, renew 3 months
    before, police character certificate, society NOC; Mumbai BMC lodging licence too - Bombay HC 2022), GA Homestay & B&B Scheme 2025,
    KL / KA 1-6 rooms, HP Home Stay Rules 2025 (6 rooms / 12 beds, Rs 3,000-18,000), UK 2026, RJ 2026, TN, WB, SK; common items: local
    body licence, fire safety, police guest register, FRRO account (foreign guests), FSSAI basic registration (food), GST, society NOC.
    Her registration number + valid-to -> reminders at 90 / 60 / 30 / 7 / 0 days.
  - Report per month: room-nights sold / available, occupancy %, revenue (stay totals shared by nights in the month), ADR, RevPAR, by
    source and room, money in, refunds, spends; register Excel (guests with masked IDs, bookings, Form C status, month, sources).
    DPDP `forget`: after the stay; foreign guests only 1 year after departure (accommodation records kept 1 year); locker rows deleted.
  - Never: OTA logins / scraping, a second booking on a taken night, messages / confirmations / cancellations / refunds / spends without
    her tap, inventing prices / dates / names / reviews, filing Form C itself, plain ID numbers outside the locker, moving money.
  - Sources (23 Oct 2026): nicobartimes.com/?p=22158 (14 Oct 2025: Immigration and Foreigners Act 2025 in force 1 Sep 2025, Form-III ex
    Form C, 24 h, departure, records 1 year, Rs 50,000 s.8 / Rule 17); heraldgoa.in/?p=457029 (homestays included, OTP activation, Rs
    50,000 per unreported guest); goa.gov.in Form C online filing guide (Dec 2025); taxguru.in GST 2.0 hotel article (25 Sep 2025: <=
    Rs 7,500 5% without ITC, ITC reversal); kanakkupillai.com/learn/gst-on-hotel-rooms (14 Oct 2026: > Rs 7,500 18%, per unit per day,
    Rs 20 / 10 lakh registration); studiomatrx.org homestay registration guide (6 Oct 2026, state comparison, indicative);
    teamleaseregtech.com HP Home Stay Rules 2025 (26 Jun 2025); professionalutilities.com Maharashtra B&B scheme; barandbench.com Bombay
    HC 17 Jun 2022 (MTDC B&B needs BMC licence); theweek.in 7 Aug 2025 (Goa Homestay & B&B Scheme).
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/homestay_screen.dart (Dart 3 records in collection-for, switch expressions, Color.withOpacity, api.call(query:), uploadFile(fields:, tries:), Api.baseUrl for the calendar link). OTA mail parsing was tested on representative Airbnb / Booking.com / cancellation texts written from their usual layout, not on her real mails (MakeMyTrip / Goibibo / Agoda formats untested: their codes fall back to the generic "booking id" pattern; unknown layouts return need_more / need_room instead of guessing). iCal import tested on an Airbnb-style export with folded lines; Booking.com / MMT exports should be checked once. Whether Airbnb / Booking.com accept her token .ics link (they fetch from the internet, so PUBLIC_BASE_URL must be public https) is unverified. Business WhatsApp send not exercised (needs a BizContact; tested only the refusal). Fingerprint path tested with approvekey.active_on patched (same as rentdesk / fleet), not a real phone. State registration rules are starters from secondary sources (labelled; the state portal decides); MH B&B scheme details are from a 2018-based scheme summary. GST on homestay food and the s.9(5) OTA position are plain-words notes for her CA, not tax advice.
