# WIRING for propagent
summary: Property Sahayak (real estate agent / broker: listings with carpet area, RERA project number + MahaRERA QR, owner's mandate, photos without EXIF / GPS, claim checks; buyer / tenant leads from her words synced to the Telecaller call list; matching with reasons; site visits ordered by Maps distance with client / owner message drafts; deals with stamp duty / registration only from HER rates, TDS notes under Income-tax Act 2025 s.393, NRI notes, IDs in the Pehchaan Locker; token receipt / offer letter / checklist / commission bill drafts; commission tracking; DPDP forget. Listing public, every client / owner message and every money paper only on her tap)
db: app.propagent.models
router: app.propagent.api        (make_router(require_key, current_tenant); all routes under /api/propagent and key-protected EXCEPT the public listing page GET /api/propagent/page/{token} and /page/{token}/photo/{n}, which check their own random 24-char token and show only what she approved: never owner name / phone / full address; CSP default-src 'none', noindex, no-store)
tools: app.agent.propagent_tools (PROPAGENT_TOOLS / PROPAGENT_LABELS / PROPAGENT_HANDLERS) ; voice: yes (propagent, propagent_dekho)
employee: duty propagent_work = [propagent, propagent_dekho, file_read, telecall, telecall_dekho] {label "Property / broker", say "listings, graahak ki zaroorat se milaan, site visit, deal ke kaagaz aur commission (public listing, har message aur paise wale kaagaz aapki haan se)"} ; role real_estate_agent {label "Real estate agent", duties [propagent_work, telecalling, appointments, reminders, records]} ; preset real_estate {label "Property dealer / broker", role real_estate_agent, rules ["Listing public / portal / poster sirf owner ki haan ke card se", "Graahak ya malik ko har message pehle owner ki haan", "Daam, kiraya, area, stamp duty kabhi khud se nahi", "RERA project ke har ad mein project number + QR + agent number"]} ; READ tools: [propagent_dekho]
  - staff (staff:<id>) may add / change listings and leads, add photos, plan visits, log visit feedback, make deals and ask for any card (publish / message / document). Owner-only (enforced in the tool): settings, deal_status, commission_got, forget. Customer actors are refused. No tool ever decides a card: only POST /api/propagent/cards/{id}/decide (her app tap with the card hash; document cards with money need her fingerprint once a phone key is active, approvekey kind "propagent" — uses approvekey's ApproveChallenge table + `_check`, like fleet; no approvekey edit needed unless approvekey keeps an allow-list of kinds: then add "propagent").
push: propagent_card -> ("Property: aapki haan chahiye", "{say}")
push: propagent_alert -> ("Property", "{say}")
push: propagent_day -> ("Aaj ka property note", "{say}")
  (propagent_visit / propagent_listing: no push; propagent_listing is a refresh-only event {listing, number, status})
worker: app.propagent.service.tick   (every minute, e.g. `await asyncio.to_thread(propagent.tick)`; visit reminders 1 day / 2 h before (once each, alert only), RERA agent registration expiry at the tightest of 60 / 30 / 7 / 0 days (once each), morning note once a day at her morning_time when there is something)
prompt: PROPERTY: listings / buyer / tenant / site visit / token / commission ki baat -> `propagent` (and `propagent_dekho` to read). Daam, kiraya, area, ready reckoner, stamp duty rates ONLY from her / the owner (never invent; missing = ask). Listing public (page / portal text / sheet / poster), ANY message to a graahak or malik, and token receipt / offer letter / commission bill = a card: say "aapki haan ka card bheja hai", never that it is posted / sent. Portals (99acres, MagicBricks, Housing, NoBroker) have no API: she posts herself; never scrape them or RERA / IGR sites. Aadhaar / PAN of clients go in `ids_text` (Pehchaan Locker). Agreements are drafts for her lawyer, not legal advice.
persona: Property mein daam / area / stamp duty kabhi apne se mat bolo; listing public karna, graahak ya malik ko message, ya paise wala kaagaz: "aapki haan ka card bheja hai" kaho.
flutter: PropagentScreen in lib/ui/propagent_screen.dart ; profile tile title "<name> · Real estate agent" subtitle "Listings, graahak, site visit, deal ke kaagaz, commission" icon Icons.home_work_rounded ; cards: propagent_card -> PropagentCardCard (also in calls: yes; one card per data['card']['id'], updated in place; takes optional onDone) ; propagent_visit -> PropagentVisitCard (also in calls: yes; key data['visit']['id']) ; propagent_alert -> PropagentAlertCard (also in calls: yes) ; propagent_day -> PropagentDayCard (also in calls: no). Pages PropagentListingPage / PropagentLeadPage / PropagentDealPage (same file). All widgets take (app:, data:) and use `app.api!.call(...)`, `app.api!.uploadFile(...)` (photo), `app.api!.absolute` + `authHeaders` (photos), `Native.approveKeySign`, `Native.openExternal`, `image_picker` (already a dependency).
features: propagent
env: none (Google Maps distance uses the existing GOOGLE_MAPS_API_KEY when set; without it the visit keeps her order with her gap_minutes; the public page link uses the existing PUBLIC_BASE_URL)
requirements: none (Pillow, openpyxl, python-docx, reportlab already present)
android: none
claude_md: |
  ## v0.1xx Property Sahayak: Hoola as a real estate agent / broker's coworker ("Real estate agent" on the Employee page; Makaan suite)
  - Owner's spec: keeps her listings -> matches buyer / tenant leads -> plans site visits -> prepares deal paperwork -> tracks
    commission. Waits for her Haan on: any listing going public, any message to a client or owner, any paper that names money.
  - Server `server/app/propagent/{rules,models,service,api}.py`, tools `propagent` / `propagent_dekho` (`agent/propagent_tools.py`, chat +
    calls), duty `propagent_work`, role `real_estate_agent`, preset `real_estate`, API `/api/propagent/*`, app Profile > "<name> · Real estate
    agent" (`lib/ui/propagent_screen.dart`: Aaj / Listings / Graahak / Deals / Niyam + listing, lead and deal pages), cards
    PropagentCardCard (`propagent_card`), PropagentVisitCard, PropagentAlertCard, PropagentDayCard. Tests `server/tests/test_ghar_propagent.py` (7).
  - Listings L-0001 (sale / rent / lease; flat, house, row house, plot, shop, office, godown, land, PG): facts only from her / the owner,
    money words ("52 lakh", "1.2 cr", "15k"), carpet area (RERA meaning; super built-up alone flagged), full address kept private, owner's
    mandate (consent to market, exclusive, commission %), photos re-encoded by Pillow (EXIF incl. GPS / camera / time dropped; an owner's
    home must not leak its location) in `data/propagent/<tenant>/<listing>`, MahaRERA QR as its own photo kind. Checks: no mandate / no
    price / no area = can't go public; new RERA project needs the project number (MahaRERA P5 + 10 digits), the QR and her RERA agent number
    (A5 + 10 digits, not expired); claim words ("guaranteed / assured return", "RERA approved", "best / No.1", "clear title", fake urgency,
    "5 min from") + Kalam's claim finder are warnings. `describe` writes text from her facts; a model line with any number not in the facts
    is thrown away.
  - Publish = `propagent_card` (where page | copy | sheet) with a hash of the public fields + photos + her agent number; ONLY her tap
    (`POST /api/propagent/cards/{id}/decide`) makes it public. Page = random-token public page (no owner name / phone / address, CSP 'none',
    noindex); copy = text she pastes on her own portal account / WhatsApp status; sheet = Excel for her own portal upload. Any later change
    takes the page down until she taps again; sold / rented / withdrawn = 410. Poster through the Brand Sahayak (its own final approval),
    only after a publish. Portals have no public API (only scrapers exist): Hoola never posts or scrapes.
  - Leads B-0001 (buyer / tenant): her words -> need (purpose, kind, BHK incl. "2 ya 3", budget range in lakh / crore / k, localities incl.
    "X mein", furnishing, NRI, loan); synced to the Telecaller list (a person makes the call); consent false for cold lists. Matching: purpose
    / kind must fit, budget with a 10% stretch, BHK, locality, furnishing, carpet, "no" feedback removed, NRI never shown agricultural land
    (FEMA NDI Rules 2019); reasons + misses in Hinglish; `buyers_for` the other way. Share / message = card with the exact text (wa.me /
    SMS after her tap, she sends; "Bhej diya" marks it); refused for opted-out / cold leads and listings without the owner's mandate.
  - Site visits V-0001: listings ordered nearest-next by Google Maps distance (server key; unknown = her order + her gap minutes), times
    from her visit minutes, clash with other visits warned, booked in the Employee appointment book when set up, client + owner message
    cards made (never sent). Feedback (pasand / nahi / mehnga / sochenge) moves the lead to negotiating and hides rejected listings.
  - Deals D-0001: agreed price / rent, token, ready reckoner value (HER number); stamp duty + cess + registration only from HER rates per
    area (settings `rates`: stamp_pct, cess_pct, women_less_pct, reg_pct, reg_cap, reg_flat; missing = "chahiye"), on the higher of price and
    ready reckoner value; TDS: sale 1% under s.393(1) Table Sl. 3(i) (old 194-IA) when the total is Rs 50 lakh or more (stamp value counts),
    NRI seller = non-resident TDS (old 195, TAN, CA's rate, 15CA / 15CB); rent 2% under s.393(1) Table Sl. 2(i) (old 194-IB) above Rs 50,000 a
    month; commission per side from her % / months (or a fixed amount), GST 18% (SAC 997222) only when she is GST-registered, TDS on commission
    note (s.393(1) Sl. 1(ii), 2% above Rs 20,000). Checklists for sale (title chain, 7/12 / property card, OC / CC, plan, encumbrance, RERA +
    10% advance rule, society NOC, loan, NRI) and rent (leave & licence registration in MH, police verification). Buyer / seller Aadhaar /
    PAN in `ids_text` go to her Pehchaan Locker; the deal keeps only references.
  - Papers (token receipt, offer letter, agreement checklist, commission bill): plain drafts with [____] blanks, "DRAFT - vakil / CA se
    check karwaiye"; a `propagent_card` with the amount; her tap (fingerprint once a phone key is active, approvekey kind "propagent") makes
    Word + PDF as her files. A deal change makes waiting paper cards stale. Commission received only on her word; report of what is due.
  - DPDP: `forget` a lead (after lost / closed) or a listing's owner (after sold / rented / withdrawn): personal fields blanked, their locker
    IDs deleted, counts kept. Worker: visit reminders, RERA renewal reminders, morning note (visits, follow-ups, deal dates, cards waiting,
    stale listings, commission due).
  - Never: posting on portals, scraping portals / RERA / IGR, inventing prices / areas / rates / dates, sending messages, taking or paying
    money (token / commission), legal advice.
  - Sources (checked 23 Oct 2026): calcguru.in/?p=4950 (RERA agent registration 2026: MahaRERA Rs 10,590 / Rs 1,00,590, 5 years, Certificate
    of Competency mandatory from 1 Jan 2024, s.62 penalty); therealtytoday.com (MahaRERA order 8 Apr 2025: QR code top-right + registration
    number + website on every ad, up to Rs 50,000, 10 days to fix; mandate from 1 Aug 2023) + housing.com (QR from 1 Aug 2023);
    blog.tdsman.com May 2026 (s.393(1) Table Sl. 3(i) = old 194-IA, 1%, Rs 50 lakh, from 1 Apr 2026; NRI seller s.195 rule) and June 2026
    (s.393(1) Sl. 1(ii) = old 194H, 2%, Rs 20,000); calcguru.in/?p=5521 (s.393(1) Sl. 2(i) = old 194-IB, 2% above Rs 50,000 a month, PAN only);
    busy.in SAC 997222 (building sales on fee / commission, 18% after GST 2.0); property portals have no public listing API (only scraper
    services list them, e.g. scrapingbee.com). Stamp duty / registration differ by state and area: only her numbers are used.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/propagent_screen.dart (Dart 3 records in collection-for, switch expressions, image_picker, api.absolute / authHeaders). Google Maps visit ordering tested with a fake distance function only. Brand poster path (`brand.service.make`) not exercised in tests. Telecaller sync uses telecall.service.add_lead as it is (tested); the Employee appointment booking is best-effort (skipped when she has no Employee profile / hours). The approvekey "propagent" kind relies on approvekey accepting any kind string in ApproveChallenge / `_check` (as fleet / shikayat do); real fingerprint flow not run on a phone. TDS / GST / FEMA lines are plain-words notes, not tax or legal advice; MahaRERA number formats (P5 / A5 + 10 digits) are checked only for Maharashtra, other states only for being present. Neighbours in the Makaan suite: rentdesk (after a rent deal: leave & licence, tenant ledger, deposit, move in / out — propagent stops at the deal and checklist), sitesup, interior, archassist, society (society NOC is a checklist line only).
