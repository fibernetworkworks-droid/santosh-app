# WIRING for archassist
summary: Architect's assistant (Archassist Sahayak: project file per client with 7/12 / property card / title checklist, area statement + FSI / premium / TDR / setback / height / parking checks from her numbers against UDCPR 2020 / DCPR 2034 starter tables (always "rule book se pakka kijiye"), drawing register with revisions, transmittals, BPMS / AutoDCR approval + NOC checklist with a submission card, consultants / RFIs / minutes, fee stages + GST invoices; issuing drawings, "submit karo" and invoices only on her tap, invoices with her fingerprint)
db: app.archassist.models
router: app.archassist.api            (make_router(require_key, current_tenant); all routes under /api/archassist, key-protected; no public routes)
tools: app.agent.archassist_tools     (ARCHASSIST_TOOLS / ARCHASSIST_LABELS / ARCHASSIST_HANDLERS) ; voice: yes (archassist, archassist_dekho)
employee: duty arch_work = [archassist, archassist_dekho, file_read, make_document, lekhak] {label "Architect office", say "project file, plot ke kaagaz, area statement / FSI jaanch (andaaza), drawing register, approval checklist, RFI, minutes, fee invoice (issue / submit / invoice aapki haan se)"} ; role architect_assistant {label "Architect's assistant", duties [arch_work, records, reminders, email]} ; preset architect {label "Architect / design office", role architect_assistant, rules ["Drawing, transmittal, submission aur invoice sirf owner ki haan ke card se", "FSI / setback jaanch andaaza hai: rule book se pakka", "Plot area / fee / % kaam kabhi khud se nahi"]} ; READ tools: [archassist_dekho]
  - staff (staff:<id>) may make projects, papers, area checks, drawings, RFIs, minutes and the CARDS (transmittal / submit / invoice); the tool refuses customer actors entirely and these owner-only actions: settings, fee, paid, sub_update, forget, approval status granted / not_needed, project status done / dropped. No tool can issue / submit / number an invoice: only POST /api/archassist/{transmittals|submissions|invoices}/{id}/decide (her app tap, card hash checked again against the live data).
push: archassist_transmittal -> ("Drawings issue karne ki haan?", "{say}")
push: archassist_submission -> ("Submission ki taiyaari", "{say}")
push: archassist_invoice -> ("Invoice ki haan chahiye", "{say}")
push: archassist_alert -> ("Architect office", "{say}")
push: archassist_day -> ("Aaj ka office note", "{say}")
  (archassist_area: no push, it is the answer to her own ask)
approvekey: kind "archassist" is used ONLY on approvekey's own table via archassist.service.invoice_challenge / _verify_fingerprint (same pattern as fleet); no change to approvekey.card_digest needed. If the coordinator prefers central kinds, add `elif kind == "archassist": card = archassist.service.approval_card(tenant, target)` with show {title: label, payee: client, amount: amount_text}.
worker: app.archassist.service.tick   (call every minute, e.g. `await asyncio.to_thread(archassist.tick)`; RFI past due once, granted approvals with valid_to at 60 / 30 / 7 / 0 days once each, invoice unpaid 30 days once, morning note once a day at her morning_time when there is something)
prompt: ARCHITECT: project file -> `archassist action=project` (her plot numbers only; area in sqm / sqft / guntha), papers with `action=doc`, FSI / setback / height / parking -> `action=area` and ALWAYS say "yeh andaaza hai, rule book / authority se pakka kijiye" (never call it final, never invent a plot area, road width, fee or % done). Drawings -> `action=drawing` (revision needs what changed). Sending drawings / certificates to anyone = `action=transmittal`, BPMS / AutoDCR / NOC = `action=submit`, fee bills = `action=invoice`: each only makes a card - say "aapki haan ka card bheja hai", never say issued / submitted / billed. Portal login, fee, OTP are hers. Aadhaar / PAN only as {id:...}.
persona: Architect ke kaam mein FSI / setback ko hamesha "andaaza, rule book se pakka" bolo; drawing bhejna, submit ya invoice ho to "aapki haan ka card bheja hai" kaho; plot area, fee ya % khud se kabhi mat bolo.
flutter: ArchassistScreen in lib/ui/archassist_screen.dart (+ ArchProjectPage) ; profile tile title "<name> · Architect's assistant" subtitle "Project file, FSI jaanch, drawing register, approval, RFI, fee invoice" icon Icons.architecture_rounded ; cards: archassist_transmittal -> ArchTransmittalCard (data {transmittal, say}; also in calls: yes; key by data['transmittal']['id']) ; archassist_submission -> ArchSubmissionCard (data {submission, say}; also in calls: yes; key by data['submission']['id']) ; archassist_invoice -> ArchInvoiceCard (data {invoice, say}; also in calls: yes; key by data['invoice']['id']) ; archassist_area -> ArchAreaCard (data {project, ok, say, checks, statement}; also in calls: yes) ; archassist_alert -> ArchNoteCard (also in calls: no) ; archassist_day -> ArchNoteCard (also in calls: no). Widgets use only `app.api!.call(...)`, `app.api!.chatFile(conv, name, bytes)` (drawing / paper files), `app.conversationId`, `app.aName`, `Native.openExternal`, `Native.approveKeySign`, `pickAttachmentsOfType`.
features: archassist
env: none
requirements: none (reportlab, openpyxl, python-docx via officegen already present)
android: none
neighbours: theka (contractor BOQ / RA bills), sitesup (site supervisor: daily progress on site), interior (interior designer BOQ / installation), propagent (broker listings), rentdesk, society; lekhak (letters / agreements), officegen, chatfiles (drawings as her files), approvekey (fingerprint), india.pincode / india.money (PIN + GSTIN check, rupee words). studio3d / 3D Studio not present in this tree (renders can link later). gstp files GST; Hoola here only prepares the tax invoice.
claude_md: |
  ## v0.1xx Archassist Sahayak: Hoola as an architect's assistant ("Architect's assistant" on the Employee page)
  - Owner's spec: project file per client (plot details, 7/12 / property card / title checklist) -> area statement & zoning checks
    from HER plot numbers against the rule set she picks -> drawing register with revision history -> building-permission / NOC
    checklist by authority -> consultant coordination (RFIs, minutes) -> fee stages and GST invoices. Waits for her Haan on: any
    drawing / transmittal issued, any invoice, any submission.
  - Server `server/app/archassist/{rules,models,service,api}.py`, tools `archassist` / `archassist_dekho` (`agent/archassist_tools.py`,
    chat + calls), duty `arch_work`, role `architect_assistant`, preset `architect`, API `/api/archassist/*`, app Profile >
    "<name> · Architect's assistant" (`lib/ui/archassist_screen.dart`: Aaj / Projects / Consultants / Niyam; `ArchProjectPage`: Plot /
    Area-FSI / Drawings / Approval / Coordination / Fee), cards ArchTransmittalCard, ArchSubmissionCard, ArchInvoiceCard (fingerprint),
    ArchAreaCard, ArchNoteCard. Tests `server/tests/test_ghar_archassist.py` (7).
  - Project file P-001: client (mobile checked, GSTIN check digit, PAN only as a Pehchaan Locker {id:...}), site + India Post PIN check,
    authority (maha_bpms / mcgm_autodcr / pmrda / midc_bpams / custom), rule set, use, plot (survey / CTS no, area in sqm / sqft / guntha /
    acre, road width, road widening + reservation, flags trees / near_airport / heritage / coastal / railway / highway / promoter + units),
    13 Maharashtra title papers (7/12, property card, ferfar, title search, deed, NA order, measurement plan, zone / DP remarks, road width
    proof, POA, tax, society NOC, old sanction) have / missing / na with her files. DPDP `forget` after done / dropped.
  - Area statement by code (`rules.area_statement`): net plot (gross - widening - reservation, or FSI on gross by her flag), basic /
    premium / TDR from the STARTER band table for the road width (UDCPR 2020 non-congested 1.10 + 0.50 + TDR 0.40-1.40 => max 2.00 /
    2.25 / 2.50 / 2.75 / 3.00 for 9 / 12 / 15 / 24 / 30 m roads, 1.10 below 9 m; congested basic 1.50 / 2.00 with premium / TDR asked;
    DCPR 2034 suburbs 1.00 + 0.50 + TDR 0.50-1.00 by 9 / 12 / 18 / 27 m; island city basic 1.33, premium / TDR asked), her own numbers
    override every value; proposed built-up -> within basic / needs premium + TDR (how much) / over max; ancillary (60 / 80%) and
    fungible (35%) as notes; height 15 m+ = high-rise (NBC 2016); front margin by road (starter 3 / 4.5 / 6 m); side / rear 3 m low-rise,
    H/5 capped 12 m above 15 m; ground coverage, open space 10% (plots 4,000 sq m+), amenity 5% (20,000 sq m+), parking ONLY from her
    per-unit rule. Every result carries "Rule book (aur authority) se pakka kijiye: yeh andaaza hai, final nahi."
  - NOCs from the facts (`rules.nocs`): fire (15 m+ or assembly / commercial use), tree authority (Maharashtra Trees Act 1975; 50+ year
    heritage trees), AAI NOCAS height (airport CCZM), environment clearance (built-up 20,000 sq m+, EIA 2006 item 8(a)), heritage, CRZ
    (MCZMA), railway, highway, RERA (promoter, 500 sq m+ or 8+ units, Sec 3), structural stability; her statuses pending / needed /
    applied / query / granted / refused / not_needed with ref, date and valid_to (reminders at 60 / 30 / 7 / 0 days).
  - Submission S-001 (`submission_request`): snapshot of papers, drawings, area numbers; blockers (title / property card / measurement /
    zone / deed missing, rule fails, no area statement, empty drawing register, CoA no. missing or expired, CC needs building permission,
    plinth / OC need CC, OC needs every NOC granted) -> card with hash; ONLY `POST /api/archassist/submissions/{id}/decide` approves (the
    snapshot is rebuilt and must still match; blockers refuse). She logs in, pays the scrutiny fee and does OTP on the portal herself;
    then `update` submitted / query / granted / refused with the inward / permission number.
  - Drawing register: sheet no. (A-101), title, discipline (A / S / E / P / M / F / L / I / C), scale, status draft / for_approval /
    for_construction / superseded, revisions R0 -> R1 (P3 -> P4, A -> B) each with date, what changed (required), file and by; issue
    history per sheet. Transmittal T-0001 (client / authority / consultant / contractor, purpose, sheets at their current revision,
    copies, warnings for missing files / not-for-construction / no CoA) -> card with hash; revising a sheet makes waiting cards stale;
    ONLY `POST /api/archassist/transmittals/{id}/decide` issues it: transmittal PDF (with CoA no. and a received-by line) as her file,
    issue history, WhatsApp / email draft she sends. RERA Form 1 style architect's certificate DRAFT (her site % only, RERA no. needed)
    becomes a register sheet issued only through a transmittal.
  - Consultants (structural / MEP / electrical / plumbing / HVAC / fire / landscape ...), RFI-001 (out / in, sheets, due; drafts she sends;
    late = reminder once), meeting minutes M-001 from her points only (Word file via officegen, action-by + date, tick done).
  - Fee: percent of project cost or lump sum (her agreement); stages starter = the CoA reference split 10 / 20 / 20 / 25 / 25 (appointment,
    concept, approval drawings, working drawings + tender, construction) - hers to change, must total 100. Invoice card per stage or for an
    extra (her amount; nothing invented): GST 18% SAC 998321, CGST + SGST same state / IGST other state by GSTIN state codes, no GST
    without her GSTIN; expected client TDS 10% u/s 393(1) Income-tax Act 2025 above Rs 50,000 a year. ONLY `POST /api/archassist/
    invoices/{id}/decide` numbers it (PREFIX/FY/001), with her fingerprint once a phone key is active (428 -> /challenge, approvekey
    message kind "archassist"); PDF + WhatsApp draft + her UPI link (the client pays her directly); `paid` (owner) records money + TDS.
  - Morning note + worker reminders (RFI late, approval validity, invoice unpaid 30 days, CoA registration date). Register Excel per project.
  - Never: issuing / submitting / invoicing without her tap, logging in to BPMS / AutoDCR / MahaRERA, paying fees, calling a zoning check
    final, inventing plot area / FSI / fee / % done / dates, storing Aadhaar / PAN.
  - Sources (23 Oct 2026): thehitavada.com 24 Nov / 6 Dec / 10 Dec 2020 (UDCPR notified 2 Dec 2020, premium + TDR loading); 1acre.in Pune
    FSI calculator notes (UDCPR basic 1.10 non-congested, congested 1.50 / 2.00, premium up to 0.50, TDR up to 1.40, max 3.00, H/5 capped
    12 m above the Table 6D height); studiomatrx.org Mumbai FSI page (DCPR 2034 basic 1.00 suburbs / 1.33 island, fungible ~35%, verified
    10 May 2026: values to re-check); studiomatrx.org profession & fees (CoA Conditions of Engagement and Scale of Charges, representative
    stage split 10 / 20 / 20 / 25 / 25, Architects Act 1972); housiey.com building approval process Maharashtra 2025 (Maha BPMS, 7/12 /
    property card / title, CC, OC, deemed approval after 60 days); midcindia.org BPAMS revision notice Jan 2026; busy.in SAC 998321
    (architectural advisory services, 18%); studycafe.in TDS chart FY 2026-27 (Sec 393(1) professional fees 10%, Rs 50,000) as used in
    v0.115; open-exam-prep MahaRERA guide + WIRC-ICAI notes (Form 1 architect / Form 2 engineer / Form 3 CA certificates for withdrawals
    from the 70% account, RERA Sec 4(2)(l)(D)); MCGM EoDB CCZM guidelines + community.verified.realestate (AAI NOCAS height NOC); EIA
    Notification 2006 item 8(a) (20,000 sq m built-up). All tables are STARTERS: her rule book / authority decides.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/archassist_screen.dart (Dart 3 records in for-loops, Iterable.indexed, app.api!.chatFile / app.conversationId / app.aName assumed as in other screens). The UDCPR / DCPR band tables are from secondary sources and memory of the regulations (UDCPR Table 6-G-style bands, DCPR Reg 30 Table 12 suburbs bands) - flagged as starters everywhere; island-city premium / TDR, congested premium / TDR, UDCPR parking (Table 8) and exact margin tables were deliberately left for her numbers. MahaRERA Form 1 wording is a plain draft, not the official format. BPMS / AutoDCR steps are generic (no public API; she logs in herself). Fingerprint path tested with approvekey patched (same flow as fleet), not a real phone. Push titles are suggestions for push.PUSH_KINDS.
