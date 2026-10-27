# WIRING for courier
summary: Courier Sahayak (courier desk: parcel with dead + volumetric weight -> PIN serviceability + the carrier's OWN rate quotes ranked by her rules (Shiprocket / Delhivery with her keys) -> booking card that ONLY her tap books (hash, fingerprint once a phone key is active) -> AWB + label PDF + pickup; tracking in the carrier's own words, NDR -> customer draft + re-attempt / RTO card; "where is my parcel?" for her and for a customer (only their own, by number); COD remittance sheet matched; daily manifest; return labels through the Wapsi desk's client on her tap)
db: app.courier.models
router: app.courier.api            (make_router(require_key, current_tenant); all routes under /api/courier, key-protected; no public routes)
tools: app.agent.courier_tools     (COURIER_TOOLS / COURIER_LABELS / COURIER_HANDLERS) ; voice: yes (courier, courier_dekho)
  ALSO customer-safe business-WhatsApp tools in the same file: COURIER_BIZ_TOOLS / COURIER_BIZ_HANDLERS / COURIER_BIZ_LABELS
  (biz_parcel_status, biz_parcel_fix). Wire them exactly like WAPSI_BIZ_* / biz_repair_status: append COURIER_BIZ_TOOLS to
  `employee/inbox.BIZ_TOOLS`, merge COURIER_BIZ_HANDLERS into `inbox.BIZ_HANDLERS` and COURIER_BIZ_LABELS into `inbox.BIZ_LABELS`,
  and add both names to `CUSTOMER_TOOLS` (so they reach agent HANDLERS for owner-approved asks, but are never offered to the owner's
  model). Optional inbox system line: "Parcel kahan hai? -> biz_parcel_status (sirf isi number ke parcel); delivery atki ho to din /
  pata -> biz_parcel_fix (sirf likhna, faisla dukaan ka)."
employee: duty courier_desk = [courier, courier_dekho, biz_parcel_status, biz_parcel_fix, file_read] {label "Courier desk", say "parcel book karna (aapke tap par), tracking, delivery atki to graahak se baat ka draft, COD milaan, return label"} ;
  role courier_desk {label "Courier desk (Courier Sahayak)", duties [courier_desk, customers, records, reminders]} ;
  preset courier {label "Online dukaan / parcel bhejne wale", role courier_desk, after_hours "note", slot_minutes 30,
  rules ["Courier booking / return label sirf owner ke tap se (wallet kat-ta hai)", "Courier ka status jaisa unhone bataya; apni taraf se tareekh nahi", "Graahak ko sirf uska parcel"]} ;
  READ tools: [courier_dekho, biz_parcel_status]
  - staff (staff:<id>) may make parcels, check rates, make cards, enter AWBs, track and draft messages; `rules`, `settings`, `forget` are
    owner-only in the tool. Customer actors are refused by `courier` / `courier_dekho` (they get only the biz_ tools).
    kind_of: treat `courier` as "action" (it only ever creates cards; the booking itself happens only in POST /api/courier/cards/{id}/decide).
approvekey (app/approvekey.py) — add one kind (the decide route already calls ak.verify("courier", card_id, proof) when a phone key is
  active and the card has money=True: booking / return label / RTO may charge her courier wallet):
  in card_digest:
    elif kind == "courier":                       # a courier booking / return label that may charge her courier wallet
        from .courier import service as cs
        card = cs.approval_card(tenant, target)
        if card is None: raise ApproveError("Yeh card ab baaki nahi hai.")
        show = {"title": card["title"], "payee": card["payee"], "amount": card["amount"], "hash": card["hash"]}
  in needed(): `if kind in (..., "courier"): return True`
  in challenge(): add "courier" to the allowed kinds tuple.
  (Until wired, a tenant WITH an active phone key gets 400 on money cards from ak.verify refusing the unknown kind; tenants without a
  phone key are unaffected.)
push: courier_card -> ("Courier: aapki haan chahiye", "{card.body.title} - {card.body.say}")   (only when card.status == "waiting")
push: courier_parcel -> ("Parcel: {parcel.number}", "{parcel.status_label}: {parcel.raw}")      (only when event in ("exception", "rto", "delivered", "out_for_delivery"); not for new / book / picked)
push: courier_day -> ("Aaj ka courier note", "{text}")
worker: app.courier.service.tick   (call every minute, e.g. `await asyncio.to_thread(courier.tick)`; it polls tracking itself every COURIER_POLL_MIN (30) per tenant for parcels on her API carriers, morning note once a day at morning_time when there is something, manifest reminder once at manifest_time when parcels wait for pickup)
prompt: COURIER: parcel bhejna -> `courier action=new` (pata, PIN, phone, wazan, dabba ka naap, COD / prepaid), phir `action=check` (PIN + courier ke apne rate; rate kabhi apni taraf se mat bolo), phir `action=book` sirf CARD banata hai: "aapki haan ka card bheja hai" kaho, booking / return label / NDR re-attempt kabhi khud mat kaho ki ho gaya. "Parcel kahan hai?" -> `courier_dekho what=where q=...` aur courier ke shabd waise hi batao (koi tareekh apni taraf se nahi). Carrier ki chaabi chat mein kabhi nahi.
persona: Parcel ki baat par courier ke shabd hi bolo, apni taraf se din mat batao; booking ya return label ke liye "aapki haan ka card bheja hai" kaho.
flutter: CourierScreen in lib/ui/courier_screen.dart ; profile tile title "<name> · Courier desk" subtitle "Pickup book (aapke tap par), parcel kahan hai, NDR, COD milaan, return label" icon Icons.local_shipping_rounded ;
  cards: courier_card -> CourierActionCard (also in calls: yes; one card per data['card']['id'], updated in place; it waits for her tap) ;
  courier_parcel -> CourierParcelCard (also in calls: no; one card per data['parcel']['id'], updated in place) ;
  courier_day -> CourierDayCard (also in calls: no).
  pc_file events with source "courier" (label PDF, manifest Excel) use the existing pc_file card.
  All widgets take (app:, data:) and use only `app.api!.call(...)`, `app.api!.uploadFile(...)`, `app.api!.fingerprintProof('courier', id)`,
  `Native.openExternal` and `package:file_picker` (already a dependency).
features: courier
env: COURIER_DIR (default data/courier: label PDFs) ; COURIER_POLL_MIN (default 30: minutes between tracking polls per tenant) ;
  COURIER_BLUEDART_BASE (default https://apigateway.bluedart.com/in/transportation; tests / sandbox only). Shiprocket / Delhivery base URLs
  come from Wapsi's WAPSI_SHIPROCKET_BASE / WAPSI_DELHIVERY_BASE (same clients).
requirements: none (httpx, openpyxl already present)
android: none
claude_md: |
  ## v0.1xx Courier Sahayak: Hoola as the courier desk ("Courier desk" on the Employee page)
  - Owner's spec: books pickups -> answers "where is my parcel?" -> handles return labels. House rules: a booking that can charge her
    courier wallet = her tap (card + hash, fingerprint once a phone key is active); return labels for refunds go through the Wapsi desk.
  - Server `server/app/courier/{rules,carriers,models,service,api}.py`, tools `courier` / `courier_dekho` (`agent/courier_tools.py`, chat +
    calls) + customer-safe `biz_parcel_status` / `biz_parcel_fix` for the business WhatsApp inbox, duty / role `courier_desk`, preset
    `courier`, API `/api/courier/*`, app Profile > Courier desk (`lib/ui/courier_screen.dart`: Aaj / Parcel / COD / Niyam +
    `CourierParcelPage`), cards CourierActionCard (`courier_card`, waits for her tap, also in calls), CourierParcelCard (`courier_parcel`),
    CourierDayCard (`courier_day`). Tests `server/tests/test_logi_courier.py` (6, fake Shiprocket / Delhivery transport).
  - One adapter interface (`courier/carriers.py`): check (PIN serviceability + rates), book, label, track, ndr, cancel, reverse. The
    Shiprocket and Delhivery clients ARE Wapsi's (`wapsi/couriers.py`, subclassed: same token cache, HTTP helper and test transport);
    the reverse pickup is Wapsi's own `book`. Shiprocket: GET /courier/serviceability, POST /orders/create/adhoc, /courier/assign/awb,
    /courier/generate/pickup, /courier/generate/label, GET /courier/track/awb/{awb}, POST /ndr/{awb}/action, /orders/cancel. Delhivery:
    /c/api/pin-codes/json, /api/kinko/v1/invoice/charges/.json, /api/cmu/create.json (Prepaid | COD), /api/p/packing_slip, /fm/request/new,
    /api/v1/packages/json, /api/p/update (RE-ATTEMPT), /api/p/edit (cancel). Blue Dart: tracking only (DHL developer portal JWT, contract
    customers). DTDC / Ekart / Xpressbees / India Post / local: manual (she books in their app / counter, types the AWB, opens their own
    page); their rates also come through her Shiprocket account. Keys typed only in the app, checked, sealed with the bazar vault, never
    shown to the model; her Wapsi Shiprocket / Delhivery keys count too.
  - Parcel P-0001: customer (name, phone, address, city, state, PIN), items, value, prepaid / COD + amount, dead weight + L x B x H ->
    volumetric = L*B*H/5000 (her divisor), chargeable = the higher, rounded up to 0.5 kg; blocking checks (address / 6-digit PIN / 10-digit
    phone, pickup address, weight, COD amount, prohibited goods: cash, fireworks / fuel / gas, weapons, drugs; restricted goods warned:
    loose lithium batteries, aerosols, medicine, jewellery; e-way bill number needed above the Rule 138 limit via `thok.rules.eway_needed`
    (Rs 50,000 inter-state, 1 lakh inside some states; seller state from her GSTIN, unknown buyer state = inter-state); not serviceable / no
    COD on that PIN). `check` stores the carrier's own quotes and ranks them by HER rules in her words ("sabse sasta / sabse tez", "COD par
    Delhivery", "5 kg se upar Xpressbees", "Ekart mat lena", max rate, max days); a quote without a rate stays without one.
  - Cards B-0001 (`courier_cards`): book (carrier, rate as quoted, weight, COD, to), reverse (return label), ndr (re-attempt with day /
    address / phone, or RTO), cancel. Hash = card body + the parcel as it is (address, PIN, phone, weight, dims, COD, value, e-way no, items);
    any change after the card = stale. `decide(by_tap=True)` only from `POST /api/courier/cards/{id}/decide {yes, hash, proof}`; money
    cards need her fingerprint once a phone key is active (approvekey kind `courier`). Book -> AWB, applied weight / freight if the carrier
    says, pickup request, label PDF (public https only, every redirect checked) as her file + `data/courier/<tenant>/<parcel>.pdf`.
  - Tracking: worker poll every 30 min (`tick`) for parcels on API carriers; the carrier's words kept exactly (`raw`) + expected date only
    when the carrier gave one; 8 states (booked, picked, in_transit, out_for_delivery, delivered, rto, exception, cancelled); words that
    match none keep the old state. Exception = NDR with reason (not available, phone, address, refused, COD not ready, asked later) ->
    `ndr_message` draft (wa.me / sms, "hum kabhi OTP / PIN nahi maangte") she sends, then the re-attempt / RTO card. Customers answer on the
    business WhatsApp with `biz_parcel_fix` (recorded, her card made, nothing sent). "3 attempts then RTO" said.
  - "Where is my parcel?": `courier_dekho what=where q=` (P-number / order / AWB / phone / name; refreshes tracking) for her;
    `biz_parcel_status` = only parcels with THAT WhatsApp number: status, carrier's words, AWB, carrier's link, COD to keep ready; no
    address, no other customer, no internal notes.
  - COD remittance: her carrier's CSV / Excel (columns found by name: AWB, COD / remitted amount, UTR / CRF id, date, order) -> matched by
    AWB; pending (delivered COD not in any sheet, days since delivery, late only after HER own `remit_days`), mismatch (amount differs),
    unknown AWBs, duplicates skipped. Manifest: parcels waiting for pickup (Excel with a courier-boy sign column), reminder at her time.
  - Return labels: from an approved Wapsi return (`wapsi_ref`: the Wapsi desk's `book_pickup` on her tap, Wapsi's rules kept: only approved
    returns), from a delivered parcel (`ref`), or customer details; reverse parcel + card; the pickup goes through the same Wapsi client.
  - DPDP: `forget` blanks a finished parcel's personal details (AWB, amounts, dates kept for accounts); customers never see others' parcels.
  - Never: booking / charging / cancelling / NDR action without her tap, inventing a status / rate / date, asking a customer for OTP / PIN,
    taking COD money, generating an e-way bill, scraping a carrier's site.
  - Research (23 Oct 2026): Shiprocket API endpoints as documented by Shiprocket's API helpsheet (support.shiprocket.in/support/solutions/
    articles/43000337456) and SDK mirrors (skillsdirectory.com ankitjh4-shiprocket; packagist tims/shiprocket-php-sdk: serviceability,
    adhoc order, assign AWB, generate pickup / label, track AWB, NDR); Shiprocket NDR practice (support.shiprocket.in "How to process an
    NDR": re-attempt with corrected address / phone / date, RTO; couriers make 3 attempts then RTO); Delhivery B2C API (pin-codes,
    invoice charges, cmu create, packing slip, pickup request, NDR update, cancel; packagist nguyendachuy/laravel-delhivery-api mirror of
    delhivery-express-api-doc.readme.io); Blue Dart tracking API v0.1 on developer.dhl.com (api-reference/bd-tracking-shipment: JWT from
    the Authenticator API, GET with loginid / lickey, contract customers); India Post: no public tracking API for small senders found
    (only third-party aggregators) -> manual; DTDC / Ekart / Xpressbees APIs only under business contracts -> manual / via Shiprocket.
    E-way bill limits from CGST Rule 138 as already in thok (v0.107). Volumetric divisor 5000 cm3/kg = common Indian courier practice (her
    setting).
not_verified: No real carrier account was called (all tests use a fake httpx transport shaped from the docs / SDK mirrors). Exact fields to re-check on her account: Shiprocket `/ndr/{awb}/action` body (`action: re-attempt|return`, deferred_date) and whether `/courier/assign/awb` returns `freight_charges`; Shiprocket label_url host (S3) must pass the public-address check; Delhivery invoice-charges params (md / ss / pt / cgm) and the pickup request JSON (`pickup_time`, `pickup_date`, `expected_package_count`), whether `/api/p/update` RE-ATTEMPT needs extra fields; Blue Dart token URL (`/token/v1/login` with ClientID / clientSecret headers) and XML element names (Status / ScanDetail / ScanDate / ScanTime / ScannedLocation) were inferred, not tested; the tracking page URL `https://shiprocket.co/tracking/{awb}` is from memory (other carriers link to their home page only). Remittance sheet column names vary by carrier (matched by column families). Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/courier_screen.dart. The approvekey `courier` kind needs the snippet above; push titles are suggestions.
