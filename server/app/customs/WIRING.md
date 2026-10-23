# WIRING for customs
summary: Customs Sahayak (import & customs desk: import shipments I-0001 with supplier / origin / Incoterm / value / mode / port / IGM / BL-AWB / CHA, 8-digit HS suggestions that stay 'andaaza' until she confirms (learned per description), document checklist by goods + mode + FTA with BIS / FSSAI / quarantine / WPC / CDSCO / EPR / Legal Metrology / DGFT flags, assessable value per Valuation Rules 2007 rule 10(2) and landed cost ONLY from her rates, clearance timeline from her / CHA updates with Section 46(3) BE deadline and demurrage / detention from her free days; Bill of Entry data goes to her CHA only on her tap; Hoola never files on ICEGATE or pays duty)
db: app.customs.models
router: app.customs.api            (make_router(require_key, current_tenant); all routes under /api/customs, key-protected; no public routes)
tools: app.agent.customs_tools     (CUSTOMS_TOOLS / CUSTOMS_LABELS / CUSTOMS_HANDLERS) ; voice: yes (customs, customs_dekho)
employee: duty customs_work = [customs, customs_dekho, file_read] {label "Import & customs", say "import ke kaagaz ki list, HS code jaanch, clearance ka hisaab (filing aapki haan se, CHA / aap file karte hain)"} ; role customs_desk {label "Import & customs desk", duties [customs_work, records, reminders]} ; preset importer {label "Importer / customs desk", role customs_desk, rules ["Bill of Entry ka data CHA ko sirf owner ki haan ke card se", "Duty rate / exchange rate / free days sirf owner ya CHA ke diye hue", "HS code ka sujhaav andaaza hai, owner / CHA pakka karein"]} ; READ tools: [customs_dekho]
  - staff (staff:<id>) may add shipments, lines, HS suggestions / confirmations, documents and timeline updates; owner-only: settings, cancel. Customers (customer:...) are refused. The filing card is never approved by any tool: only POST /api/customs/filings/{id}/decide (her app tap, exact card hash; a shipment change after the card makes it stale).
push: customs_filing -> ("Import filing: aapki haan chahiye", "{say}")   (only when filing.status == "waiting")
push: customs_alert -> ("Import / customs", "{say}")
push: customs_day -> ("Aaj ka import desk", "{say}")
  (customs_shipment: no push, it updates in place; publish only)
worker: app.customs.service.tick   (call every minute, e.g. `await asyncio.to_thread(customs.tick)`; alerts once each: BE due / late (late once a day), demurrage / detention near (once) and running (once a day), duty after assessment; morning note once a day at her morning_time when there is something)
prompt: IMPORT / CUSTOMS: goods coming INTO India -> `customs action=new` (supplier, origin, Incoterm, invoice value + currency, mode, port, BL/AWB, lines). HS code: `customs action=hs` gives only a suggestion: say "andaaza hai, CHA / Tariff se pakka kijiye"; `hs_confirm` only when SHE or her CHA confirms. Duty rates, exchange rate, free days, statuses: only what she / CHA said, never guess. Filing: `customs action=filing` sends HER a card; say "aapki haan ka card bheja hai"; Hoola never files a Bill of Entry on ICEGATE and never pays duty (exports = Niryat Sahayak).
persona: Import ke kaam mein HS code ko sirf andaaza kaho, duty rate khud mat batao, BE filing ke liye "aapki haan ka card bheja hai" kaho; ICEGATE par file / duty payment aap ya CHA karte hain.
flutter: CustomsScreen in lib/ui/customs_screen.dart ; profile tile title "<name> · Import & customs" subtitle "Import ke kaagaz, HS code jaanch, clearance aur demurrage ka hisaab; filing aapki haan se" icon Icons.local_shipping_rounded ; cards: customs_filing -> CustomsFilingCard (also in calls: yes; one card per data['filing']['id'], updated in place) ; customs_shipment -> CustomsShipmentCard (also in calls: no; one card per data['shipment']['id'], updated in place) ; customs_alert -> CustomsAlertCard (also in calls: yes) ; customs_day -> CustomsDayCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)` + `Native.openExternal(url:)`. Also exported: CustomsShipmentPage(app:, id:).
features: customs
env: CUSTOMS_LLM (default true; "false" = no model call for HS suggestions, heading table + her learned codes only)
requirements: none (openpyxl via officegen, already present)
android: none
neighbours: niryat (v0.110 exports: reused rules.INCOTERMS / FTA / COUNTRIES / fob_value / iec_ok; export shipping bill / RoDTEP stay there), logistics (LR / e-way bill for the inland leg after out of charge), courier (courier pickups / tracking; this module only does the courier-mode import checklist), warehouse (stock after the goods arrive), gstp (IGST credit in GSTR-3B: the BE flows via ICEGATE into GSTR-2B), operator (Computer Operator could open ICEGATE for status with her login; not called by this module), chatfiles / officegen (BE data sheet Excel).
claude_md: |
  ## v0.1xx Customs Sahayak: Hoola as an importer's import & customs desk ("Import & customs desk" on the Employee page)
  - Owner's spec: prepares document lists -> checks HS codes -> tracks clearance -> waits for her Haan on FILING (Hoola never files a
    Bill of Entry on ICEGATE and never pays duty; her customs broker (CHA) or she files).
  - Server `server/app/customs/{rules,models,service,api}.py`, tools `customs` / `customs_dekho` (`agent/customs_tools.py`, chat + calls),
    duty `customs_work`, role `customs_desk`, preset `importer`, API `/api/customs/*`, app Profile > Customs Sahayak
    (`lib/ui/customs_screen.dart`: Aaj / Shipments / HS jaanch / Niyam, `CustomsShipmentPage`), cards CustomsFilingCard (`customs_filing`,
    her tap), CustomsShipmentCard (`customs_shipment`, in place), CustomsAlertCard (`customs_alert`), CustomsDayCard (`customs_day`).
    Tests `server/tests/test_logi_customs.py` (5).
  - Shipments I-0001: supplier, supplier country, country of origin, Incoterm 2020 (niryat's table + meaning), place, invoice no / date / value
    + currency, freight / insurance (real amounts only), mode sea / air / courier / land, port, BE type home / warehouse / ex-bond, IGM, BL / AWB,
    containers, shipping line, CHA, ETA, FTA claim, DGFT licence, her free days + per-day rates, other landing charges. Long digit runs (card /
    Aadhaar / account numbers) are masked from any text.
  - HS code helper: 8-digit ITC-HS / Customs Tariff check (format, chapter, Section / Chapter notes that usually decide the code (16 chapters),
    GIR 1-6), regulator flags by HS prefix + words (FSSAI + FICS, plant / animal quarantine, CDSCO drugs / devices MD-15 / cosmetics COS-2,
    CIB&RC, WPC ETA, TEC MTCTE, BIS CRS R-number / ISI incl. toys / steel / footwear QCOs, EPR plastic / e-waste / battery / tyre, drone import
    ban, used goods, gold via nominated agencies, arms, e-cigarettes, chemicals + SDS, Legal Metrology import labels for retail packs) and the
    DGFT ITC(HS) Schedule I policy line ('check', never a verdict). Suggestions: her own confirmed code for the same description first
    (`customs_hs_memory`), then the model (JSON, only 8-digit codes kept, description = data), else a heading table; always 'andaaza';
    `hs_confirm` (her / CHA) makes it pakka and learns it.
  - Document checklist per shipment: invoice, packing list, BL / AWB / courier waybill / LR, IEC, GSTIN, CHA authorisation + KYC (CBLR 2018),
    freight / insurance proof for EXW-FOB / CFR terms (else rule 10(2) loading), FTA = certificate of origin + CAROTAR Form I information,
    DGFT licence, one line per regulator flagged, warehousing bond, BoE copy to the AD bank for IDPMS. have / missing / na (na on a required
    paper = owner only).
  - Value + duty: assessable value = CIF per Customs Valuation Rules 2007 rule 10(2) as amended by G.S.R. 1202(E) (2017): freight not known =
    20% of FOB, insurance not known = 1.125% of FOB, air freight capped at 20% of FOB, no 1% landing charges; FOB from the invoice by Incoterm;
    EXW / DAP / DDP notes; rupees only at HER exchange rate (CBIC notified). Duty per line ONLY from her rates: BCD, SWS (10% of BCD by default
    when she gives BCD, 0 for exempt goods), AIDC, IGST on AV + BCD + SWS + AIDC (Customs Tariff Act s.3(7)), compensation cess; a missing
    rate = "rate chahiye", never guessed; landed cost = AV + BCD + SWS + AIDC + her charges (IGST shown as GST credit).
  - Clearance timeline (shipped, arrived, IGM, BE filed (+ number), query / exam, assessed, duty paid (+ amount she says), out of charge,
    delivered, empty container returned) only from her / CHA updates, dated as given. Clocks: Section 46(3) BE by the end of the day (incl.
    holidays) before the vessel's arrival (arrival day for Bangladesh / Maldives / Myanmar / Pakistan / Sri Lanka), late presentation charges
    unless waived; Section 47(2) duty same day for self-assessed / next day after a returned BE, else interest; demurrage from arrival with HER
    port / CFS free days (stops at delivery) and detention with HER container free days (stops at empty return); amounts only from her
    per-day rates. Worker alerts once each, morning note.
  - Filing (her Haan): `request_filing` refuses while blockers remain (lines, unconfirmed / non-8-digit HS, invoice value, supplier, origin,
    IEC, required papers) -> `customs_filing` card with the exact BE data and a sha256 hash; any shipment change makes it stale. ONLY
    `POST /api/customs/filings/{id}/decide {yes, hash}` (by_tap) approves: BE data sheet Excel (shipment, lines + HS + her rates, documents,
    timeline) as her file + WhatsApp / email draft to her CHA she sends + ICEGATE steps when she files herself (submit, e-Sanchit upload and
    e-payment are hers). After BE filed no new card.
  - Never: filing on ICEGATE, paying duty, inventing duty / exchange rates, free days or statuses, calling a suggested HS code final.
  - Sources (23 Oct 2026): jawaharcustoms.gov.in Public Notice 29/2024 (Section 46(3): BE before the end of the day preceding arrival, same day
    for listed neighbours, late presentation charges capped Rs 50,000, waiver via e-Sanchit / ACL); psabdp.com (Section 47(2): duty same day for
    self-assessed BE, one day after a returned BE); scconline.com blog 12 Oct 2017 (Customs Valuation Amendment Rules 2017, G.S.R. 1202(E):
    20% / 1.125% / air freight cap, cost of transport definition); cleartax.in CAROTAR 2020 (notified 21 Aug 2020, in force 21 Sep 2020; Rule 3
    BE declaration, Rule 4 Form I + 5 years, Rule 5 10 / 15 days, Rule 6 verification 45 days); mondaq.com LKS "Union Budget 2026: changes in
    customs law and duty rates" (Budget 1 Feb 2026: tariff rationalisation from 1 May 2026, exemptions lapsing / extended to 31 Mar 2028,
    advance ruling validity 5 years - so rates must come from the current Tariff, never built in); eximpe.com BIS importer's guide 2026 (9 Feb
    2026, upd. 28 Mar 2026: CRS R-number / ISI per model and factory, Manakonline status, WPC ETA, LMPC); DGFT Notification 54/2015-20 (9 Feb
    2022) drone import prohibition; PECA 2019 (e-cigarettes). Regulator lists by HS prefix are starters for 'check', not legal advice.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/customs_screen.dart (record patterns in collection-for, PopupMenuButton const items, Native.openExternal(url:)). No ICEGATE / CBIC API exists for importers to read BE status without a registered login, so the timeline is only what she / her CHA reports (no tracking fetch). Section 46(3) wording was read from a 2024 JNCH public notice whose OCR was partly garbled (neighbour-country list and the ICD / air note should be checked against the Act); the CHA's word wins. The model HS prompt was tested only with a scripted answer. Regulator prefix lists are a hand-made subset and will need tuning (QCOs change often). Push titles are suggestions for push.PUSH_KINDS.
