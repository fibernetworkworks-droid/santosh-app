# WIRING for interior
summary: Interior Sahayak (interior designer: client brief per room, site measurement with areas worked out by code, moodboard with her photos / labelled AI pictures / 3D Studio render, room-wise BOQ from HER rate card with blanks instead of invented rates or sizes, quotation PDF with GST + design fee + payment stages, vendor work orders, change orders, installation schedule with clashes, snag photos without EXIF, handover warranty sheet in her words; quote to the client, vendor orders (fingerprint), price-changing change orders and payment requests only on her tap)
db: app.interior.models
router: app.interior.api            (make_router(require_key, current_tenant); all routes under /api/interior, key-protected; no public routes)
tools: app.agent.interior_tools     (INTERIOR_TOOLS / INTERIOR_LABELS / INTERIOR_HANDLERS) ; voice: yes (interior, interior_dekho)
employee: duty interior_work = [interior, interior_dekho, file_read, photo_banao] {label "Interior design", say "client ka brief, site naap, moodboard, BOQ aur quotation (aapke rate), vendor order, installation schedule, snag list, handover warranty (quote client ko / vendor order / daam badalne wala badlav / paise maangna aapki haan se)"} ; role interior_designer {label "Interior designer", duties [interior_work, customers, appointments, reminders, records]} ; preset interior {label "Interior designer / modular kitchen studio", role interior_designer, rules ["Rate, naap, brand ka daam kabhi mat gadho: khaali chhodo aur poochho", "Quotation client ko, vendor order, daam badalne wala badlav, paise maangna: sirf owner ki haan ke card se", "Apne aap ko 'architect' mat likho (Architects Act s.37)"]} ; READ tools: [interior_dekho]
  - staff (staff:<id>) may do brief / measure / concept / boq / quote (draft) / quote_send (card only) / order + change + pay_request (cards only) / task / snag; owner-only actions are refused by the tool itself (settings, rate, rate_import, paid, handover, forget; quote_mark accepted and snag_status closed are owner-only in service). customer: actors are refused. No tool can decide a card: only POST /api/interior/{quotes|orders|changes|stages}/{id}/decide (her app tap) sets by_tap=True.
push: interior_quote -> ("Quotation: aapki haan chahiye", "{say}")
push: interior_order -> ("Vendor order: aapki haan chahiye", "{say}")
push: interior_change -> ("Badlav se daam badla: aapki haan chahiye", "{say}")
push: interior_payment -> ("Client se paise maangne ki haan", "{say}")
push: interior_alert -> ("Interior", "{say}")
push: interior_day -> ("Aaj ka interior note", "{say}")
  (interior_concept: no push; it is the moodboard result in the chat)
approvekey: kind "interior" is used ONLY through interior.service.order_challenge / _verify_fingerprint, which write and check ApproveChallenge rows directly (same pattern as fleet). No change to approvekey.card_digest / needed / challenge is required (optional: add "interior" to the kinds list there if the coordinator wants approvekey.challenge to serve it too).
worker: app.interior.service.tick   (call every minute, e.g. `await asyncio.to_thread(interior.tick)`; late installation tasks and due payment stages once each, the morning note once a day at her morning_time only when there is something)
prompt: INTERIOR: interior designer's coworker (`interior` / `interior_dekho`). Rates come ONLY from her rate card or her words, sizes ONLY from the site measurement or her words, brand prices never guessed: a missing one stays blank and you ask her. The quotation going to the client, any vendor order, a change order that changes the price and any payment request are cards for HER tap: say "aapki haan ka card bheja hai", never that it was sent / ordered. Messages to clients / vendors are drafts she sends. AI moodboard pictures are labelled "AI se bana" and are only a suggestion. Never call her or her firm an "architect" unless she gave a Council of Architecture number.
persona: Interior ke kaam mein rate ya naap kabhi apne se mat bolo, khaali chhod kar poochho; quote client ko, vendor order, daam badalne wala badlav aur paise maangna "aapki haan ka card bheja hai" kaho.
flutter: InteriorScreen in lib/ui/interior_screen.dart (+ InteriorProjectPage) ; profile tile title "<name> · Interior designer" subtitle "Brief, naap, moodboard, BOQ-quote, vendor order, snag, handover" icon Icons.chair_rounded ; cards: interior_quote -> InteriorQuoteCard (also in calls: yes; key by data['quote']['id'], update in place) ; interior_order -> InteriorOrderCard (also in calls: yes; key data['order']['id']; handles 428 -> /api/interior/orders/{id}/challenge -> Native.approveKeySign -> resend with proof) ; interior_change -> InteriorChangeCard (also in calls: yes; key data['change']['id']) ; interior_payment -> InteriorPaymentCard (also in calls: yes; key data['stage']['id']) ; interior_concept -> InteriorConceptCard (also in calls: no) ; interior_alert, interior_day -> InteriorNoteCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`, `app.api!.uploadFile(...)`, `app.api!.absolute / authHeaders` (snag photos), `Native.openExternal`, `Native.approveKeySign`, image_picker, file_picker (all already in the app).
features: interior
env: none
requirements: none (reportlab, openpyxl, Pillow already present)
android: none
neighbours: theka (contractor BOQ / measurement book / RA bills: an interior firm that does govt / large fit-outs as a contractor uses theka), sitesup (site supervisor daily progress + labour on the same site), archassist (architect's assistant: drawings, approvals, CoA fee stages), propagent / rentdesk / society (property side). Reused: photogen (AI pictures, labelled), brand (kit colours for the palette), blender3d (3D render, if on the server), chatfiles (her files / PDFs), approvekey (fingerprint for vendor orders), employee profile (UPI ID fallback), india.money (GSTIN check, rupees in words).
claude_md: |
  ## v0.1xx Interior Sahayak: Hoola as an interior designer's coworker ("Interior designer" on the Employee page)
  - Owner's spec: client brief per room -> site measurement sheet -> concept / moodboard -> room-wise BOQ with HER rates and a
    quotation PDF with GST -> payment stages -> vendor / carpenter work orders -> installation schedule -> handover snag list with
    photos and warranty sheet. Waits for her Haan on: the quotation going to the client, any vendor order, any change order that
    changes the price, any payment request. Never invents rates, sizes or brand prices (blanks).
  - Server `server/app/interior/{rules,models,service,api}.py`, tools `interior` / `interior_dekho` (`agent/interior_tools.py`, chat +
    calls), duty `interior_work`, role `interior_designer`, preset `interior`, API `/api/interior/*`, app Profile > Interior designer
    (`lib/ui/interior_screen.dart`: Aaj / Projects / Rate card / Vendors / Niyam + `InteriorProjectPage`), cards InteriorQuoteCard,
    InteriorOrderCard, InteriorChangeCard, InteriorPaymentCard (all also in calls), InteriorConceptCard, InteriorNoteCard.
    Tests `server/tests/test_ghar_interior.py` (8).
  - Projects IP-0001: client, phone, site, PIN, client_state (place of supply), home type, carpet area (hers), client's budget,
    style, target handover. Brief per room (style, budget, must / avoid, notes; client words = data, OTP / card-like numbers cut).
  - Measurement: L / W / H in her words (12, 12.5, 12'6", 12 ft 6 in, 3.6 m, 3600 mm) + doors / windows -> floor, ceiling, net wall
    (openings taken off), perimeter, skirting (door widths taken off) by code; a missing number stays missing ("baaki naap"); Excel sheet.
  - Concept: palette from 11 styles (a design suggestion) or her brand kit colours, her own photos, up to 3 photogen pictures from the
    room's type / size / style / must-haves (always "AI se bana", sujhav only), or a 3D Studio render (blender3d) of the measured room.
  - Rate card: HER selling rates per unit before GST (code, kind, unit, spec / brand in her words, HSN / SAC, GST %), Excel / CSV
    import (rows without a rate refused). BOQ lines by code / close name (difflib >= 0.82); qty from her words or from the measured area
    (ceiling -> false ceiling, net wall -> painting, floor -> flooring, skirting / perimeter on ask); unit mismatch is said, not converted
    into a guess; a rate or qty she has not given = blank; Excel.
  - Quotation Q-0001/R1.. (new revision supersedes the old): works subtotal, design fee by her mode (percent of works / per sq ft of HER
    carpet area / flat / none; a per-sq-ft fee without the area = blank), GST per rate on works + design fee (SAC 998391) as CGST+SGST
    inside her state (from her GSTIN) or IGST outside, total in words, payment schedule from her stage template (starter 10 / 50 / 35 /
    5, must total 100; amounts add up exactly), terms, validity. Draft PDF watermarked "DRAFT - NOT SENT"; blanks block the card.
    `quote_request` -> `interior_quote` card (hash of client, lines, totals, validity) -> ONLY `POST /api/interior/quotes/{id}/decide
    {yes, hash}` makes the final PDF (her file) + WhatsApp / SMS draft she sends; then "Maine bhej diya" / "Client ne maana" (owner) ->
    contract + stages. After acceptance the BOQ is locked: changes only by change order.
  - Change orders CO-0001: added lines priced from her rate card (blanks refused), removed BOQ lines, delta with GST by code; delta 0 =
    applied at once; otherwise `interior_change` card -> her tap -> BOQ updated (lines tagged CO), positive delta = a new payment stage,
    negative = taken off the last unpaid stages; client message draft asks for the client's written OK.
  - Payment requests: `pay_request` -> `interior_payment` card (hash of project, client, stage, amount, UPI) -> her tap -> message draft +
    her UPI link (her setting, else the Employee profile) she sends; "Paise mile" (owner) with amount / UTR, short payment said. Hoola never
    collects money.
  - Vendor work orders WO-0001: the vendor's rate is HER word (never the client rate), qty from the BOQ line; missing rate / qty / amount
    refused; checks: vendor rate not below the client rate (no margin), finish after handover; the same waiting order is never asked
    twice; `interior_order` card -> her tap AND her phone's fingerprint once a phone key is active (approvekey kind "interior": 428 ->
    `/orders/{id}/challenge` -> sign -> resend) -> work-order PDF + vendor message draft. She pays the vendor herself.
  - Schedule: tasks by trade / room / vendor / dates; warnings: the same vendor busy on another project at the same time, a later trade
    starting before an earlier one is finished in that room (civil -> plumbing -> electrical -> false ceiling -> painting -> flooring ->
    carpentry -> furniture -> decor -> cleaning), past the handover date, Sunday (society rules). Snags with photos re-encoded from
    pixels (EXIF / GPS / camera gone) in `data/interior/<tenant>/<project>/`, before / fixed photos, closed only by her. Handover (owner;
    open snags block unless force + reason): warranty sheet PDF per work kind in HER warranty words (missing ones named), snag list,
    client sign line, unpaid stages said. DPDP `forget` after done / cancelled: client personal details + snag photos removed, numbers kept.
  - Morning note (`interior_day`) + once-each alerts (late task, stage due) by `tick`.
  - Title rule: settings refuse "architect" in her title / firm without a CoA number (CA/YYYY/NNNNN); PDFs say Interior Designer.
  - Research (23 Oct 2026): busy.in/gst-rates/interior-work (interior design consultancy SAC 998391 18%, interior works labour + material
    SAC 9954 18%, pure labour 9987 18%, modular furniture HSN 9403 18%; composite contracts at one rate; after GST 2.0 of 22 Sep 2025
    the page shows the same 18%; homeowners can't take ITC, and CGST Act s.17(5)(c)/(d) blocks ITC on works contracts for immovable
    property - so the rate is her setting per line, her CA confirms); indiacode.nic.in Architects Act 1972 (A1972-20) s.37 + scconline.com
    18 Mar 2020 (unregistered persons may practise but may not call themselves "architect") + freepressjournal.in 2 Aug 2026 (Council of
    Architecture public advisory: only registered persons may use the title, prosecution under ss.36-37 and BNS 2023);
    designcafe.com 10 Feb 2026 (designer fee = flat, percentage of the project or per sq ft) and interiorcompany.com FAQs (10% initial,
    40% at the execution milestone, catalogue products paid before delivery) - so fee and stages are her settings with a starter;
    plyreporter.com 14 Mar 2024 (Plywood and Wooden Flush Door Shutters QCO 2024, IS 303 / 710 / 4990 / 2202, moved to 28 Feb 2025, small
    28 May / micro 28 Aug 2025; later status not confirmed - a "BIS mark" spec is hers to write); lexplosion.in / mondaq.com
    (Environment (Construction and Demolition) Waste Management Rules 2025, notified Apr 2025, in force 1 Apr 2026: debris goes to an
    authorised collection / processing route); Consumer Protection Act 2019 (deficiency in service s.2(11), e-Jagriti) for scope,
    timelines and warranty disputes - the quote, change orders in writing and the warranty sheet are the paper trail; DPDP Rules 2025
    (notified 13-14 Nov 2025, phased to May 2027) for client data. GST rates, fee and stages are starters, not rules.
not_verified: Flutter screen + cards could not be compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/interior_screen.dart (Dart 3 records in `for (final (k, _) in fields)`, regex lookbehind in `_parseLines`, Iterable.firstOrNull, uploadFile with an empty file for a snag without a photo). PDFs use reportlab Helvetica, so Devanagari names / words in a quote show as boxes (Latin / Hinglish is fine); switch to lekhak's Chromium printer if her clients need Hindi / Marathi quotations. photogen and blender3d were not called for real (tests replace `_make_picture`; render3d only checked for the missing-measurement refusal). The real-phone fingerprint flow was tested with a software EC key through approvekey.register. GST rate per line / design-fee SAC are plain-words starters for her CA to confirm. Push titles are suggestions for push.PUSH_KINDS.
