# WIRING for pidesk
summary: PI Desk Sahayak (private investigator DESK for businesses: business due diligence from official public registries with every fact sourced + red flags + gaps, document tamper SIGNALS (PDF metadata / signature / e-invoice QR vs printed / photo EXIF), fraud evidence files with SHA-256 + hash-chained custody + timeline from chat exports + 1930 / police / bank complaint drafts + BSA s.63 Part A draft + evidence ZIP, employee checks only after the candidate's signed consent; tracking / locating / profiling of people, spouse checks, CDR / bank records, pretexting refused in code; any report going out only on her tap)
db: app.pidesk.models
router: app.pidesk.api            (make_router(require_key, current_tenant); all routes under /api/pidesk, key-protected; no public routes)
tools: app.agent.pidesk_tools     (PIDESK_TOOLS / PIDESK_LABELS / PIDESK_HANDLERS) ; voice: via_kaam (add pidesk, pidesk_dekho to VOICE_TOOL_NAMES AND VOICE_VIA_KAAM per the v0.149 rule: Sahayak tools are not declared in calls, santosh_kaam does them)
employee: duty pi_desk = [pidesk, pidesk_dekho, file_read] {label "PI desk (business jaanch)", say "business due diligence sarkari registry se, kaagaz ki jaanch (signals), dhokhe ke saboot ki file + complaint draft; kisi insaan ki nigrani / pata / profiling kabhi nahi; report bhejna aapki haan se"} ; role pi_desk {label "Private investigator (desk)", duties [pi_desk, records, reminders, research]} ; preset pi_desk {label "Jaanch / verification desk", role pi_desk, rules ["Sirf business ki jaanch, aapke kaagaz aur aapke saboot: kisi insaan ka pata / nigrani / social-media profiling / rishton ki jaanch kabhi nahi", "Candidate ki jaanch sirf unke signed consent ke baad", "Report / saboot kisi ko bhejna sirf owner ki haan ke card se"]} ; READ tools: [pidesk_dekho]
  - staff (staff:<id>) may open cases and do the research / evidence / doc checks / drafts; the tool itself refuses customer actors and the owner-only actions (settings, consent, close, forget). Sharing is never approved by any tool: only POST /api/pidesk/shares/{id}/decide (her app tap).
  - Refusals raise ToolError("REFUSED: ...") with the lawful route; the API answers 403. The refusal count (no content) is in settings.refused.
push: pidesk_share -> ("PI desk: aapki haan chahiye", "{say}")
push: pidesk_alert -> ("PI desk", "{say}")
  (pidesk_case, pidesk_report, pidesk_doc: no push, they update / inform in place)
worker: app.pidesk.service.tick   (call every few minutes, e.g. `await asyncio.to_thread(pidesk.tick)`; once each: fraud money lost but not reported to cyber 2 h after opening, share card waiting 24 h, consent period over, closed case past retention)
prompt: PI DESK: business due diligence / vendor check / document jaanch / dhokhe ke saboot -> `pidesk` (her exact words; every fact must keep its source; say "signals, not verdicts" and "vakil / police se pakka karwaiye"). NEVER locate / track / watch / profile any person, find a home / phone / workplace, check a spouse or relationship, get CDR / bank records, or pretend to be someone: the tool refuses; tell her the lawful route (police / 1930 / court / vakil) and don't try other tools for it. Money lost to fraud: tell her to call 1930 first. Sending a report / pack / complaint = card (`action=share`); never say it was sent.
persona: Business ki jaanch, kaagaz ki jaanch aur dhokhe ke saboot mein madad karo; kisi insaan ka pata / nigrani / rishton ki jaanch kabhi nahi ("woh police / court ka kaam hai"); paisa gaya ho to pehle 1930.
flutter: PideskScreen in lib/ui/pidesk_screen.dart ; profile tile title "<name> · PI desk" subtitle "Business jaanch, kaagaz ki jaanch, dhokhe ke saboot (kisi ki nigrani nahi)" icon Icons.manage_search_rounded ; cards: pidesk_share -> PideskShareCard (also in calls: yes; key by data['share']['id'], updated in place) ; pidesk_report -> PideskReportCard (also in calls: no) ; pidesk_doc -> PideskDocCard (also in calls: no) ; pidesk_case -> PideskNoteCard (also in calls: no; key by data['case']['id']) ; pidesk_alert -> PideskNoteCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`, `app.api!.chatFile(...)`, `Native.openExternal`.
features: pidesk
env: none
requirements: none (uses pikepdf, pypdf, pyhanko via pdftools, pypdfium2, zxing-cpp via qrread, Pillow, reportlab; segno only in tests, already installed)
android: none
claude_md: |
  ## v0.1xx PI Desk Sahayak: a private investigator's DESK for businesses ("Private investigator (desk)" on the Employee page; Kanoon suite)
  - Strictly desk research / verification for BUSINESSES: (1) business due diligence on a company / firm / vendor / customer business,
    (2) checks on documents she holds, (3) fraud evidence files for police / 1930 / court, (4) employee pre-hire verification only after
    the candidate's signed consent. Server `server/app/pidesk/{rules,models,service,api}.py`, tools `pidesk` / `pidesk_dekho`
    (`agent/pidesk_tools.py`, chat; calls via santosh_kaam), duty / role / preset `pi_desk`, API `/api/pidesk/*`, app Profile > PI desk
    (`lib/ui/pidesk_screen.dart`: Aaj / Cases / Niyam + `PideskCasePage`), cards PideskShareCard (her tap), PideskReportCard,
    PideskDocCard, PideskNoteCard. Tests `server/tests/test_law_pidesk.py` (7).
  - REFUSED in code (`rules.guard`, before anything is stored or searched; also in the tool descriptions; API 403, tool "REFUSED: ..."
    with the lawful route): locating / tracking / following / surveilling a private person, finding a home / phone / workplace / live
    location, social-media profiling (social / caller-ID pages are never read), spouse / partner / pre-matrimonial checks, CDR / SIM /
    bank records, GPS trackers / spy apps, pretexting ("bank / police banke"), background checks on a person outside an employee_verify
    case. Due diligence subject must be a business kind (a "person" subject is refused). The fraud file lists the identifiers the other
    side USED, as she saw them, for the police; Hoola never looks them up.
  - Due diligence: identifier checks by code (`check_identifier`: GSTIN check digit + state + PAN entity type, CIN (listed, NIC, state,
    year, type), LLPIN, Udyam, FSSAI 14 digits, PAN (an individual's PAN is masked), IEC) with the official page to confirm status; one
    page at a time read with web.open_website (lines about the business only, sha256 of the page, official = .gov.in / .nic.in / named
    registries; status words like Strike Off / Under liquidation / CIRP / Cancelled / Suspended / Active non-compliant = red flags); her
    paste of results she opened herself (GST search / MCA master data / eCourts after her CAPTCHA) -> CNR numbers, case kinds (NI Act
    138, recovery, IBC, arbitration, consumer), status words ("case hona = galti saabit hona nahi"); web / news by the BUSINESS name
    (web.search_any) with adverse words (fraud, arrest, raid, ED / CBI, FIR, default, NCLT, PMLA...) flagged as "padhiye, aarop = doshi
    nahi"; her notes without a link marked "source chahiye". Report PDF DRAFT (indicpdf for Devanagari, ReportLab otherwise): summary
    (optional model line accepted only if it adds no number), identifiers, findings per section with source + link, timeline, evidence
    with SHA-256, gaps ("kya nahi jaancha"), disclaimer.
  - Document checks = signals, not verdicts (none / some / several / strong): PDF producer / creator editing tools, ModDate after
    CreationDate, incremental saves on unsigned PDFs, many fonts / one font in several subsets, scan-only, file date vs the date on the
    paper, digital signature via pdftools.verify (broken = strong); e-invoice IRP QR (qrread, also rendered from PDF page 1-2 by
    pypdfium2) vs her printed values (GSTIN / bill no / total / date mismatch = strong) + "Verify Signed QR" pointer; UPI QR payee note;
    GSTINs found in the text checked; photos: EXIF editing software, camera date vs claimed date, no EXIF = "WhatsApp hata deta hai,
    kuch saabit nahi".
  - Evidence + custody: every file copied into `data/pidesk/<tenant>/<case>/` (chat files die in 24 h) with SHA-256, duplicates by hash;
    append-only custody log, each entry chained (sha256(prev | entry)); `verify_chain` recomputes the chain and re-hashes every file.
    WhatsApp exports (.txt / .zip, Android + iPhone formats) -> timeline (OTP / card numbers masked, money words marked important);
    receipts / bank SMS text -> UTR / amounts. Complaint DRAFTS: cyber (1930 first + cybercrime.gov.in steps), police (thana receiving;
    FIR BNSS s.173 / old CrPC s.154), bank (report within 3 working days, RBI 6 Jul 2017 limited-liability circular; RBI Ombudsman) with
    timeline + evidence hashes + "[dhara police / vakil tay karenge]" (no offence section invented). Evidence ZIP: files + index.csv +
    custody_log.csv + timeline + BSA s.63(4) Part A details draft (Part B expert is not Hoola's).
  - Employee verify: consent form text for the candidate (purpose, checks, retention, withdrawal); nothing runs (ids, pages, doc checks,
    report) until her signed consent file + date + checks are attached (owner only); reference-request drafts only for checks in the
    consent, to institutions / employers the candidate named, sent by her; reminder when the consent period ends.
  - Sharing: `share_request` -> `pidesk_share` card (hash of case + what + to + content sha) -> ONLY `POST /api/pidesk/shares/{id}/decide
    {yes, hash}` (by_tap); a report / pack changed after the card = stale; yes = wa.me / mailto links + custody "shared ... owner's tap";
    Hoola never sends, files or contacts anyone. DPDP: `forget` after close deletes the evidence folder and personal text (custody stub
    kept); retention reminder after `retention_days` (365).
  - Research (23 Oct 2026): verdictum.in 1 Aug 2026 (HC v State of Rajasthan, 2026 INSC 778: private investigation "an area sans
    regulation", copy sent to the Law Ministry + Law Commission; Private Detective Agencies (Regulation) Bill 2007 never enacted;
    questions on authorised photos / videos, storage and privacy); livelaw.in 28 May 2026 (Supreme Court 22 May 2026 upheld BSA s.63(4):
    certificate Part A with hash value, Part B expert); ksandk.com 16 / 30 Sep 2026 (DPDP and employee background verification: s.7(i)
    not a clear basis for pre-hire checks, notice + purpose-specific consent, checks limited to the role, agency = processor under s.8(2));
    Puttaswamy (2017) privacy, BNS 2023 s.78 stalking, IT Act s.66E / s.72, BNSS s.173 (in force 1 Jul 2024); RBI/2017-18/15 (6 Jul 2017)
    customer liability; cybercrime.gov.in + 1930 (MHA I4C); MCA master data, GST Search Taxpayer, Udyam verify, FoSCoS, eCourts services as
    the official public pages.
  - Neighbours: vakil (case diary / drafts for the advocate), legalres (statutes / judgments), dpo (DPDP records / breach), helpdesk +
    cyber (phishing / CERT-In 6 h), shikayat (consumer complaints), gstp (GST), audit; this desk only investigates documents and public
    business records, never people.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/pidesk_screen.dart (Dart 3 records in collection-for and in a List<(String, IconData, Future<void> Function())>, null-aware map spread `...?f`). web.open_website / web.search_any were monkeypatched in tests (the sandbox has no DNS); MCA / GST / Udyam pages often need a CAPTCHA or JS, so in practice she will mostly use `paste` after opening the page herself. OCR on photo documents only runs when Tesseract is installed. The guard's word lists (Hinglish / English / Hindi) will need tuning with real requests (false refusals possible, e.g. a business called "Pati Traders"). The e-invoice QR's IRP signature is not verified (pointer to the portal's Verify Signed QR). BSA s.63 Part A details are a plain draft, not the Schedule's exact form. Push titles are suggestions for push.PUSH_KINDS.
