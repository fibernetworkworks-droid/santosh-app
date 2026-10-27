# WIRING for logistics
summary: Logistics Sahayak (logistics coordinator: shipments S-0001 with GSTIN-checked consignees, LR / delivery challan / packing list PDFs by code + Thok invoice link, e-way bill readiness with Rule 138 limits / 200 km-a-day validity / ODC / 180-day document age / extension window and the NIC JSON, filing only on her tap via her GSP or the portal, tracking only from real updates + forwarded location shares + the courier desk, late / EWB-expiry / no-news alerts once each, Hinglish customer drafts she sends (business WhatsApp only on her tap), POD photo with EXIF stripped closes it, claim-notice date on damage)
db: app.logistics.models
router: app.logistics.api            (make_router(require_key, current_tenant); all routes under /api/logistics, key-protected; no public routes)
tools: app.agent.logistics_tools     (LOGISTICS_TOOLS / LOGISTICS_LABELS / LOGISTICS_HANDLERS) ; voice: yes (logistics, logistics_dekho)
employee: duty logistics_work = [logistics, logistics_dekho, file_read] {label "Logistics", say "shipment, LR / challan / packing list, e-way bill ki taiyaari, tracking, graahak ko update draft (e-way bill portal par aur graahak ko message sirf aapke tap se)"} ; role logistics_coordinator {label "Logistics coordinator", duties [logistics_work, customers, records, reminders]} ; preset logistics {label "Dispatch / transport / logistics", role logistics_coordinator, rules ["E-way bill banana / Part B / extension sirf owner ke tap se", "Graahak ko message owner bhejti hai; Hoola sirf draft", "Tracking sirf driver / transporter / courier ki batayi baat se, kabhi andaaza nahi"]} ; READ tools: [logistics_dekho]
  - staff (staff:<id>) may create / update shipments, add updates, locations, papers, drafts, POD; owner-only in the tool: settings, ewb_number, cancel. customer:* actors are refused. E-way bill filing is NEVER done by any tool: the tool only makes the `logistics_ewb` card; only POST /api/logistics/ewb/{id}/decide (her app tap) runs it. Business WhatsApp only via POST /api/logistics/messages/{id}/send (her tap).
push: logistics_ewb -> ("E-way bill: aapka tap chahiye", "{say}")
push: logistics_alert -> ("Logistics · {number}", "{text}")
push: logistics_day -> ("Aaj ka dispatch", "{text}")
  (logistics_update: no push (a draft, shown in chat); logistics_shipment: no push, updates in place)
worker: app.logistics.service.tick   (call every minute: `await asyncio.to_thread(logistics_service.tick)`; alerts run at most every 10 min, each alert once per shipment (late vs ETA + her grace hours, e-way bill expiring in the 8-hour window / expired / 360-day limit, no news for silent_h hours while moving); morning note once a day at her morning_time when she has shipments)
prompt: LOGISTICS: maal bhejna / gaadi / LR / e-way bill / "maal kahan hai" -> `logistics` (new / update / docs / ewb_ready / ewb / draft). Tracking ONLY from her / driver / transporter / courier words (`action=update` with their exact words, `location` for a forwarded location link); never invent a status, place or ETA. E-way bill filing (generate / Part B / extend / consolidated) = `action=ewb` makes a card: say "aapke tap ka card bheja hai", never say it is filed. Customer updates are drafts she sends; [blanks] stay blanks.
persona: Maal / gaadi ki baat par sirf wahi batao jo driver / transporter / courier ne bataya; e-way bill portal par aur graahak ko message sirf unke tap se ("card bheja hai").
flutter: LogisticsScreen in lib/ui/logistics_screen.dart ; profile tile title "<name> · Logistics" subtitle "Shipment, LR / challan, e-way bill, tracking, graahak ko update" icon Icons.local_shipping_rounded ; cards: logistics_ewb -> LogisticsEwbCard (also in calls: yes; key by data['ask']['id']) ; logistics_update -> LogisticsUpdateCard (also in calls: yes; key by data['message']['id']) ; logistics_shipment -> LogisticsShipmentCard (also in calls: no; one card per data['shipment']['id'], updated in place) ; logistics_alert -> LogisticsAlertCard (also in calls: yes; key by data['id'] + data['kind']) ; logistics_day -> LogisticsDayCard (also in calls: no). All widgets take (app:, data:) and use `app.api!.call(...)`, `app.api!.uploadFile(...)` (POD photo, multipart field `file` + `stage` / `receiver` / `remarks` / `short` / `damaged`), image_picker (already a dependency) and `Native.openExternal`.
features: logistics
env: LOGISTICS_DIR (default "data/logistics"; where POD / loading / damage photos are kept per tenant / shipment, EXIF stripped)
requirements: none (reportlab, openpyxl, Pillow, httpx already present)
android: none
neighbours: courier desk (MOD courier): `logistics.service._courier_track` calls `app.courier.service.track_awb(tenant, courier=..., awb=...)` -> {status: delivered|in_transit|out_for_delivery|picked|booked|cancelled|failed|rto|returned, events: [{at, what, where}]} when that module exists (else the app says "courier desk se judta hai"); coordinator: please make sure the courier builder exposes exactly this function (or adapt the one-line call). fleet / drivers (trucks, permits, duties, trip sheets) are theirs: shipments only store vehicle no + driver name / phone. thok (v0.107): `thok_order` fills a shipment from a BILLED Thok invoice and `docs which=invoice` returns `thok.service.invoice_file`; e-way bill limits come from `thok.rules.EWB_INTRA / EWB_INTER` (one table). employee.inbox: business WhatsApp send (24 h window rules unchanged). operator (Computer Operator) can fill the EWB portal for her (she does login OTP); not started from this module.
claude_md: |
  ## v0.1xx Logistics Sahayak: Hoola as a logistics coordinator ("Logistics coordinator" on the Employee page)
  - Owner's spec: tracks every shipment -> updates customers -> prepares dispatch documents. House rules: a customer message is a draft
    SHE sends (wa.me / SMS) or goes by business WhatsApp only on her tap; generating / changing an e-way bill on the portal is a filing
    and happens only on her tap.
  - Server `server/app/logistics/{rules,ewb,models,service,api}.py`, tools `logistics` / `logistics_dekho` (`agent/logistics_tools.py`, chat +
    calls), duty `logistics_work`, role `logistics_coordinator`, preset `logistics`, API `/api/logistics/*`, app Profile > Logistics
    (`lib/ui/logistics_screen.dart`: Aaj / Shipments / Party / Niyam, `LogisticsShipmentPage`), cards LogisticsEwbCard (`logistics_ewb`),
    LogisticsUpdateCard (`logistics_update`), LogisticsShipmentCard, LogisticsAlertCard, LogisticsDayCard. Tests
    `server/tests/test_logi_logistics.py` (8).
  - Shipments S-0001 (direction out / in / carry for a transporter): consignor = her settings, consignee from her party book (GSTIN check
    digit + state code, PIN, phone), goods [{name, HSN, qty, UQC unit from Hinglish words, taxable value, GST %}] or "cement 120 bag @ 380",
    invoice / challan no (<= 16 chars) + date + reason (NIC sub-supply types), weight, packages, mode road / rail / air / ship / courier,
    own / hired / courier, transporter (name, GSTIN / TRANSIN, phone), vehicle no (format check incl. BH series), ODC, driver, LR no,
    freight paid / to pay / TBB, from / to, km, dispatch / ETA in her words ("kal shaam", "25-10 6 pm", "2 din"). A BILLED Thok invoice
    (`thok_order`) fills party, lines, value and tax.
  - Papers by code (reportlab, as her files + pc_file cards): LR / goods receipt in three copies (consignor original, consignee, driver /
    office) with carrier registration, consignor / consignee + GSTIN, packages said to contain, actual weight, declared value, freight basis,
    GTA GST note (5% RCM / 18% with ITC from 22 Sep 2025), invoice + e-way bill no, the liability line (10 x freight, not above declared
    value, unless a higher risk rate was agreed; claim notice within 180 days); delivery challan (CGST Rule 55: number <= 16 chars, place of
    supply, HSN, taxable value, tax, triplicate) when goods move without an invoice; packing list; Thok tax invoice link; e-way bill JSON.
  - E-way bill: `ewb_ready` = blockers (doc no / date, 180-day-old document, GSTINs, PINs, items, HSN, value, distance) + warnings + the
    NIC fields (supplyType, subSupplyType, docType, from / to GSTIN + state codes, item list with HSN / UQC / rates, CGST+SGST vs IGST,
    transMode, transDistance, vehicleNo, vehicleType R / O); needed or not from `thok.rules` limits (Rs 50,000 inter-state; state intra
    limits). Validity: 1 day per 200 km (ODC 20 km), a day ends at midnight of the next day. `ewb` makes a `logistics_ewb` card (hash of
    the payload) for generate / part_b (vehicle change + reason) / extend (only inside 8 h before - 8 h after expiry; place, PIN, remaining
    km, reason) / consolidated (2+ EWBs on one vehicle). ONLY `POST /api/logistics/ewb/{id}/decide {yes, hash}` (her tap) acts; a shipment
    changed after the card = stale. With her GSP joined (base URL, client id / secret, GSTIN, EWB API user + password typed only in the app,
    sealed with the bazar vault, never shown back) the NIC action (GENEWAYBILL / VEHEWB / EXTENDVALIDITY / GENCEWB) is sent and the EWB
    number / valid-upto saved; otherwise the bulk-upload JSON + portal steps (she logs in with her OTP; MFA mandatory on the EWB portal
    for all from 1 Apr 2025) and she tells the 12-digit number (`ewb_number`; valid-upto from her or worked out from the km).
  - Tracking: timeline entries only from her / driver / transporter words (status read from Hinglish words: nikal gaya, raste mein, naka /
    rok liya, gaadi kharab, out for delivery, maal utar gaya...), forwarded location links (Google Maps coordinates / short links), and the
    courier desk for AWBs (`app.courier.service.track_awb`, new events only). Nothing invented: no words = refused; a delay needs its real
    reason. Alerts once each: late vs ETA + her grace hours, e-way bill expiring (extension window) / expired / 360-day limit while moving,
    no news for `silent_h` hours while moving ("driver se location share karwaiye"). Daily dispatch board + morning note; on-time % per
    transporter from real ETA vs delivery.
  - Customer drafts (Hinglish: dispatch, in transit, delay, out for delivery, delivered, custom) with wa.me / SMS links; unknown facts stay
    [blanks]; parties who said no get none; "Maine bhej diya" marks sent; business WhatsApp send only from her tap, hash-checked, only
    to a customer who wrote to the business number (Meta 24 h window rules in employee.inbox), never with blanks left.
  - POD (or loading / damage) photo: re-encoded from pixels (EXIF / GPS / camera gone) in `data/logistics/<tenant>/<shipment>`, closes the
    shipment as delivered with the receiver's name; shortage / damage -> the claim-notice date (booking + 180 days, s.16) and the carrier's
    liability limit. Cancel reminds her to cancel the EWB on the portal (24 h). Register Excel (shipments + on-time sheet).
  - Never: filing on the EWB portal or sending a customer message without her tap, making up a status / place / ETA, taking or paying money
    (freight, COD, claims), tracking a driver beyond what is shared.
  - Sources (23 Oct 2026): cleartax.in/s/time-limit-for-e-way-bill-generation (GSTN advisory 17 Dec 2024: from 1 Jan 2025 no EWB for
    documents older than 180 days, extension max 360 days from generation; validity 1 day per 200 km, ODC 1 day per 20 km; penalty Rs 10,000
    or tax); taxmann.com "Multi-factor authentication on e-invoice and e-way bill portals will be mandatory for all taxpayers" (AATO > 20 cr
    1 Jan 2025, > 5 cr 1 Feb 2025, all 1 Apr 2025); docs.logitax.in/Docs/Create_Eway_bill (NIC e-way bill JSON field names: supplyType,
    subSupplyType, docType INV / CHL, transMode, transDistance, vehicleType R / O, itemList); CGST Rule 138 (Part A / Part B; Part B not needed
    up to 50 km within the state to the transporter) and Rule 55 (delivery challan); bnblegal.com Carriage by Road Act 2007 bare act (s.3
    registration, s.8 goods forwarding note, s.9 goods receipt in triplicate, s.10-12 liability, s.16 180-day notice, s.17); legitquest.com
    Carriage by Road Rules 2011 (Rule 12(1): 10 x freight, not above declared value); disytax.com GTA guide 2026 (GTA 5% without ITC or 18%
    with ITC from 22 Sep 2025, consignment note makes a GTA); mahagst.gov.in GSTN advisory (Oct 2025) on enhanced inter-operable services between
    EWB portals. Grace / silence hours are her settings, not rules.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI annotations for lib/ui/logistics_screen.dart (uses Dart 3 records in const lists, image_picker, api.call / uploadFile). No real GSP or NIC e-way bill call was made: the GSP client follows the NIC API v1.03 action names (ACCESSTOKEN, GENEWAYBILL, VEHEWB, EXTENDVALIDITY, GENCEWB) and header names most GSPs pass through, but each GSP's paths / auth / encryption differ (auth_path / api_path are settable; direct NIC access needs its own RSA/AES encryption, not built) - test with her GSP's sandbox first. The bulk-upload JSON `version` string ("1.0.0621") and exact field set must be checked against the portal's current bulk tool; the portal's Excel utility is the reference. Part B / extension / consolidated payload fields (reasonCode, extnRsnCode, consignmentStatus, tripSheetEwbBills) are from the NIC API docs as commonly published, not run. Courier tracking depends on the courier desk module exposing `track_awb` (tested with a monkeypatched function only). Business WhatsApp send tested with a fake inbox.send. LR liability text and GTA rates are plain-words guidance, not legal / tax advice; e-way bill state intra-state limits come from thok.rules (only the states listed there).
