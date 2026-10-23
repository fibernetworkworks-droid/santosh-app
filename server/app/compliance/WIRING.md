# WIRING for compliance
summary: Compliance Sahayak (compliance officer: which statutory duties apply from her business facts and why, a compliance calendar of GST / TDS-TCS / PF-ESIC / PT / LWF / labour-code returns / Shop Act / FSSAI / fire / pollution / trade + factory licence / MSME-1 / ROC basics with due dates, owners, saboot files, status, reminders and starter penalties with sources; GST / payroll / Daftar renewals / CS items read from those Sahayaks, not copied; done only with a file or her word; portal filing card and the monthly compliance certificate sign-off only on her tap)
db: app.compliance.models
router: app.compliance.api            (make_router(require_key, current_tenant); all routes under /api/compliance, key-protected; no public routes)
tools: app.agent.compliance_tools     (COMPLIANCE_TOOLS / COMPLIANCE_LABELS / COMPLIANCE_HANDLERS) ; voice: yes, but declare only compliance_dekho in calls and put `compliance` in VOICE_VIA_KAAM (v0.149 slim-call rule: Sahayak writes go through santosh_kaam)
employee: duty compliance_work = [compliance, compliance_dekho, file_read] {label "Compliance", say "statutory calendar, saboot, reminders, certificate draft (portal filing aur sign-off aapki haan se)"} ; role compliance_officer {label "Compliance officer", duties [compliance_work, records, reminders]} ; preset compliance {label "Compliance officer", role compliance_officer, rules ["Kaam 'ho gaya' sirf saboot (challan / ack) ya owner ke kehne par", "Portal par file / payment / submit kabhi Hoola nahi: owner khud", "Certificate sign-off sirf owner ke tap se", "Tareekh / penalty / section kabhi gadhna nahi: source nahi to [citation chahiye]"]} ; READ tools: [compliance_dekho]
  - staff (staff:<id>) may add evidence, mark done WITH a file, ask for a filing card, nudge drafts, build; owner-only in the tool: facts, settings, add, na, reopen, forget, done with her_word. Customers are refused. Filing cards and certificates are decided only by POST /api/compliance/filings/{id}/decide and /api/compliance/certs/{id}/decide (by_tap=True).
push: compliance_filing -> ("Compliance: aapki haan chahiye", "{say}")
push: compliance_cert -> ("Compliance certificate: sign-off", "{say}")
push: compliance_alert -> ("Compliance yaad", "{say}")
push: compliance_day -> ("Aaj ka compliance note", "{say}")
  (push compliance_filing / compliance_cert only while data.filing.status / data.cert.status == "waiting")
worker: app.compliance.service.tick   (call every minute, e.g. `await asyncio.to_thread(compliance.tick)`; rebuilds the calendar once a day, reminders at her windows (7/3/1/0 days) once each, overdue once + weekly with penalty andaaza, 1st-5th of the month a "certificate draft banaun?" nudge for last month, morning note at morning_time when there is something)
prompt: COMPLIANCE: statutory dates / "kya compliance baaki hai" -> `compliance_dekho what=day|calendar|applicability`; her business facts -> `compliance action=facts`. Never invent a due date, section, fee or penalty: use the catalogue (dated starters with sources) and say "CA / CS / vakil se pakka karwaiye". GST returns live in the GST Sahayak, PF / ESIC in Payroll, renewals in Daftar, ROC in Company Secretary: point there. "Ho gaya" only with the challan / ack file (`action=done file_id=`) or her own word; portal filing and the monthly certificate are cards for her tap: never say filed / signed yourself, never log in / pay / submit on a portal.
persona: Compliance mein tareekh aur penalty sirf calendar se bolo, "CA se pakka karwaiye" kaho; file / sign-off ke liye "aapki haan ka card bheja hai"; portal par login / payment aap khud.
flutter: ComplianceScreen in lib/ui/compliance_screen.dart (+ ComplianceItemPage) ; profile tile title "<name> · Compliance officer" subtitle "GST, TDS, PF, licence, pollution ki tareekhein; saboot; monthly certificate" icon Icons.fact_check_rounded ; cards: compliance_filing -> ComplianceFilingCard (also in calls: yes; one card per data['filing']['id'], updated in place) ; compliance_cert -> ComplianceCertCard (also in calls: yes; key data['cert']['id']) ; compliance_alert -> ComplianceNoteCard (also in calls: no) ; compliance_day -> ComplianceNoteCard (also in calls: no). All widgets take (app:, data:) and use only app.api!.call(...), app.api!.chatFile, Native.openExternal, pickAttachmentsOfType.
features: compliance
env: none
requirements: none (openpyxl, reportlab already present)
android: none
neighbours: gstp (GST returns: read via gstp.service.clients / calendar), payroll (PF / ESIC / salary TDS: payroll.service.employees / calendar), office (Daftar renewals: office.service.renewals; a renewal whose name says FSSAI / fire / shop / trade / consent / factory replaces that licence item here), cosec (Company Secretary, same suite, optional: if app.cosec.service.calendar(tenant) exists and returns rows, ROC + MSME-1 items are read from it, else starters here), vakil / legalres / contracts / notary / pidesk / dpo (other Kanoon builders; no overlap: DPDP / CERT-In duties belong to dpo, contract renewals to contracts).
claude_md: |
  ## v0.1xx Compliance Sahayak: Hoola as a business's compliance officer ("Compliance officer" on the Employee page; Kanoon suite)
  - Owner's spec: applicability check from her business facts -> statutory compliance calendar with due dates, owners, evidence upload,
    status, reminders, overdue penalties as starters with sources -> monthly compliance certificate draft for her sign-off. Marking done =
    evidence or her word; certificate sign-off and any portal filing = her tap. Reuses gstp / payroll / office renewals (read, not copied).
  - Server `server/app/compliance/{rules,models,service,api}.py`, tools `compliance` / `compliance_dekho` (`agent/compliance_tools.py`),
    duty `compliance_work`, role `compliance_officer`, preset `compliance`, API `/api/compliance/*`, app Profile > Compliance officer
    (`lib/ui/compliance_screen.dart`: Aaj / Calendar / Lagu kya / Certificate / Niyam + `ComplianceItemPage`), cards ComplianceFilingCard,
    ComplianceCertCard, ComplianceNoteCard. Tests `server/tests/test_law_compliance.py` (9).
  - Facts (`rules.clean_facts`): entity (proprietor / partnership / LLP / pvt / public / OPC / trust / society / HUF), state (name or GST
    code; from the GSTIN too), employees, contract workers + contractor, turnover, GSTIN (check digit) + scheme, TAN / salary TDS / TCS,
    PT liability, sectors, food kind / licence, pollution category, factory, fire NOC, MSE dues > 45 days, AGM date, licence valid-till
    dates. `questions` = what she still has to answer.
  - Catalogue (37 duties, `rules.CATALOGUE`): applies(facts) -> yes / no + why; freq monthly | quarterly | half | yearly | calendar year
    | expiry (from HER licence date, lead days: FSSAI 120, consent 120, fire / shop / factory 60, trade 30) | AGM-relative | once | her
    date | gst (gstp.rules.obligations reused). Penalty starters: TDS / TCS statement Rs 200 / day (s.427) capped at the tax + s.461/462,
    late deposit 1.5% / month (s.398(3)); FSSAI D-1 / D-2 Rs 100 / day; MH PT 1.25% / month + Rs 1,000 / return; GST late fee via
    gstp.rules.late_fee; MSME-1 Sec 405(4); consent renewal 4 months early = 5% rebate, late 25 / 50 / 100%; DIR-3 KYC Rs 5,000. Entries
    with no source read get "[citation chahiye]" + verify (AOC-4 / MGT-7 / DPT-3 / AGM / LLP forms / env statement / Shop Act / fire /
    POSH IC): "CA / CS se pakka". Her own date always wins (`due_override`).
  - Calendar: `build` (daily in tick, idempotent; window -62 / +92 days) makes items C-0001 per duty per period with default owner per
    area; a "tell me the date" item when a licence / AGM date is missing, replaced once she gives it. Linked: GST Sahayak clients ->
    gstp.calendar rows, Payroll employees -> payroll.calendar, Daftar renewals (licence words match = that licence item not made),
    Company Secretary (cosec.service.calendar, when present) -> shown as linked rows with their own status; done there.
  - Done: an evidence file (chat file_id, checked via chatfiles; staff may add) or, owner only, her word (`done_how` evidence | word);
    ack / ARN / challan no. kept (secrets / card / Aadhaar / PAN masked); lagu nahi = owner + a reason (goes in the certificate).
  - Filing: `filing_request` -> `compliance_filing` card (hash of label / period / due / portal / steps) -> ONLY POST
    /api/compliance/filings/{id}/decide (by_tap) -> item `file_ok` + steps; she logs in / OTP / pays / submits herself; a changed item =
    stale. Certificate: `certificate(month)` = own items due that month + still-open older ones + linked rows, counts, exceptions,
    Hinglish text; `cert_request` -> `compliance_cert` card; ONLY POST /certs/{id}/decide re-builds the content and needs the same hash
    -> signed + PDF (indicpdf for Devanagari, ReportLab fallback) "app tap = sign-off, not a digital signature".
  - Worker: reminders 7 / 3 / 1 / 0 days (her windows), overdue once + weekly with penalty andaaza, certificate nudge 1st-5th, morning note.
    Register Excel (calendar + what applies + sources). Nudge = WhatsApp draft to the person responsible (she sends). DPDP
    `forget_person` (name off items and team).
  - Never: logging in / paying / submitting on a portal, marking done without a file or her word, signing the certificate, inventing a
    date / fee / section, legal advice.
  - Research (23 Oct 2026): TDS / TCS tax year 2026-27 under the Income-tax Act 2025: deposit 7th (March TDS 30 Apr, TCS 7 Apr), Forms 138
    / 140 / 143 / 144 quarterly 31 Jul / 31 Oct / 31 Jan / 31 May (143 Q4 15 May), s.398 interest, s.427 Rs 200 a day, s.461/462
    (studycafe.in/tds-and-tcs-due-date-compliance-calendar-for-tax-year-2026-27-419614.html, secondary: verify with CBDT); labour codes in
    force 21 Nov 2025, Central Rules notified 8 May 2026 (ksandk.com/newsletter/labour-codes-central-rules-2026/); OSH Central Rules 2026
    (G.S.R. 345(E)): Form I registration on Shram Suvidha, annual return Form XVII by the last day of February after each calendar year,
    contractor half-yearly Form XVIII, contract labour licence at 50+ (blog.ipleaders.in/osh-central-rules-2026-registration-hours-contract-labour/,
    23 Sep 2026); PF / ESIC 15th, POSH annual report 31 Jan (pockethrms.com/tools/hr-compliance-calendar-india/, undated); Maharashtra PT
    notification 28 Feb 2026: PTRC 15th (Rs 1 lakh+ a year) / annual 15 Mar, PTEC 15 Jun, 1.25% / month, Rs 1,000 per return
    (calcguru.in/?p=529, Jun 2026); MH LWF June / December, due 15 Jul / 15 Jan (factohr.com/labour-welfare-fund/maharashtra/, Dec 2025;
    contribution figures conflict, so no amount is shown); FSSAI D-1 31 May, D-2 milk 31 Oct / 30 Apr, Rs 100 a day (cleartax.in/s/fssai-annual-returns);
    MSME-1 31 Oct / 30 Apr, Sec 405(4) (calcguru.in/?p=5764, Aug 2026); Air Act consent guidelines 29 Jan 2025: renewal 4 months early =
    5% rebate, late 25 / 50 / 100% (corporateprofessionals.com, Feb 2025); DIR-3 KYC triennial from 31 Mar 2026, due 30 June, Rs 5,000
    late (equitylist.co/blog-post/dir-3-kyc; MCA amendment 31 Dec 2025). GST dates / late fee reuse the v0.93 GST Sahayak rules.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/compliance_screen.dart (Dart 3 records in `_form`, switch expressions, `api.call(..., query:)`). The cosec link assumes `app.cosec.service.calendar(tenant)` returning a dict with due / late / items lists or a list of rows with label|title|form and due|due_on (cosec is built in parallel; if its shape differs the link silently stays off and ROC starters are used here). Dates are starters from secondary sources (CBDT / MCA / state notifications decide); the TCS Form 143 Q1-Q3 dates (31 Jul / 31 Oct / 31 Jan) follow the StudyCafe table and should be checked; labour annual-return date may differ by state rules (state OSH rules not encoded). PT for states other than Maharashtra and LWF for other states are "her date" items only. Real portal filings are never done by Hoola (no portal API used); the Computer Operator flow for opening forms was not exercised. Certificate PDF with Devanagari needs Chromium on the VPS (ReportLab fallback otherwise). Push titles are suggestions for push.PUSH_KINDS.
