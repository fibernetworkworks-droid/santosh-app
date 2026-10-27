# WIRING for rentdesk
summary: Rentdesk Sahayak (property manager: units, tenants with Aadhaar / PAN only in the Pehchaan Locker, leave & licence / rent tenancies with state checklist (MH s.55 IGR e-registration + police information), rent / deposit / maintenance ledger billed per licence month, receipts with HRA fields, UPI link to HER UPI ID, Galla credit only as a hint, reminder DRAFTS; agreement Word draft for her lawyer; renewal / escalation / lock-in dates; repairs to her vendors; move-in / move-out inspection with EXIF-free photos; deposit settlement; every message to a tenant, deposit deduction, rent change / notice and repair spend only on her tap, money cards fingerprint-signed; Hoola never takes or pays money)
db: app.rentdesk.models
router: app.rentdesk.api            (make_router(require_key, current_tenant); all routes under /api/rentdesk, key-protected; no public routes)
tools: app.agent.rentdesk_tools     (RENTDESK_TOOLS / RENTDESK_LABELS / RENTDESK_HANDLERS) ; voice: yes (rentdesk, rentdesk_dekho)
  ALSO customer-safe business-WhatsApp tools in the same file: RENTDESK_BIZ_TOOLS / RENTDESK_BIZ_HANDLERS / RENTDESK_BIZ_LABELS
  (biz_rent_status, biz_rent_repair). Wire exactly like COURIER_BIZ_* (v0.139): append RENTDESK_BIZ_TOOLS to `employee/inbox.BIZ_TOOLS`,
  merge RENTDESK_BIZ_HANDLERS into `inbox.BIZ_HANDLERS` and RENTDESK_BIZ_LABELS into `inbox.BIZ_LABELS`, add both names to
  `CUSTOMER_TOOLS` (never offered to the owner's model). Optional inbox system line: "Kirayedar ka kiraya / baaki -> biz_rent_status
  (sirf isi number ki kirayedari, UPI link malik ke UPI ID par); kuch toota / kharab -> biz_rent_repair (sirf darj, kharcha malik tay karengi)."
employee: duty rentdesk_work = [rentdesk, rentdesk_dekho, biz_rent_status, biz_rent_repair, file_read] {label "Property manager", say "kirayedar, kiraya / deposit ka hisaab, receipt, reminder draft, agreement draft, renewal, repair, move-in / move-out, deposit hisaab (har message, katauti, kiraya badlav aur repair kharcha aapki haan se)"} ; role property_manager {label "Property manager", duties [rentdesk_work, reminders, records, collections]} ; preset rentdesk {label "Kiraye ki property / PG / dukaan", role property_manager, rules ["Kirayedar ko har message sirf owner ke tap se", "Deposit se katauti, kiraya badhana, notice, repair kharcha: sirf owner ki haan ke card se", "Paisa mila sirf owner batati hain; Hoola paise nahi leta / deta"]} ; READ tools: [rentdesk_dekho, biz_rent_status]
  - staff (staff:<id>) may: checklist ticks, agreement draft, receipt PDF, pay link, message DRAFTS, rent change / notice / repair / deduction CARDS (never decide them), repairs + vendors, inspections, settlement lines, register. Owner-only in the tool: settings, unit, person, tenancy, update, activate, received, charge, waive, refund_done, forget. Customer actors are refused by `rentdesk` / `rentdesk_dekho` (they get only the biz_ tools).
  - No tool decides anything: only POST /api/rentdesk/approvals/{id}/decide (her app tap, card hash; deduction + repair need her fingerprint once a phone key is active: 428 -> POST .../challenge, message kind "rentdesk" signed on approvekey's own table, same as fleet) and POST /api/rentdesk/messages/{id}/send (her tap; via self = her own WhatsApp / SMS link, via business = inbox.send inside Meta's 24 h window).
push: rentdesk_approval -> ("Kiraya: aapki haan chahiye", "{say}")
push: rentdesk_message -> ("Kirayedar ke liye message taiyaar", "{say}")
push: rentdesk_alert -> ("Kiraya / property", "{say}")   (only when data.kind in renewal | checklist | forget, or data.request.urgent is true)
push: rentdesk_day -> ("Aaj ka kiraya note", "{say}")
  (rentdesk_receipt: no push, it is her own action; publish only)
worker: app.rentdesk.service.tick   (call every minute, e.g. `await asyncio.to_thread(rentdesk.tick)`; bills new licence months, reminder drafts once per charge stage (before due / after grace), renewal windows once each, escalation cards, registration / police nudge 7 days after start once, DPDP forget nudge 90 days after the refund once, morning note once a day at her morning_time when there is something)
prompt: RENTDESK: kirayedar / kiraya / deposit / agreement / repair / move-out ki baat -> `rentdesk` (read with `rentdesk_dekho`). Kiraya, deposit, stamp duty, area, taarikh sirf uske number; Hoola gadhta nahi. "Paisa mila" sirf owner ke kehne par (`action=received`); Galla ki UPI sirf ishaara. Kirayedar ko message = draft (`action=message`), deposit katauti / kiraya badlav / notice / repair kharcha = card: kaho "aapki haan ka card / draft bheja hai", kabhi mat kaho ki bhej diya ya maan liya. Aadhaar / PAN sirf locker reference. Agreement draft vakil ke liye hai, kanooni salah nahi. IGR / police portal khud nahi kholna: unke steps batao.
persona: Kirayedar ko message ya deposit katauti / kiraya badlav par "aapki haan ka card bheja hai" kaho; kiraya / deposit / stamp duty apni taraf se kabhi mat bolo; paise khud kabhi nahi.
flutter: RentdeskScreen in lib/ui/rentdesk_screen.dart ; profile tile title "<name> · Property manager" subtitle "Kirayedar, kiraya, deposit, agreement, repair, move-out" icon Icons.house_rounded ; cards: rentdesk_approval -> RentdeskApprovalCard (also in calls: yes; one card per data['approval']['id'], updated in place; optional onDone) ; rentdesk_message -> RentdeskMessageCard (also in calls: yes; key by data['message']['id']) ; rentdesk_receipt -> RentdeskReceiptCard (also in calls: no; key by data['payment']['id']) ; rentdesk_alert -> RentdeskAlertCard (also in calls: yes) ; rentdesk_day -> RentdeskDayCard (also in calls: no). Widgets take (app:, data:) and use `app.api!.call(...)`, `app.api!.uploadFile(path, name, bytes, fields:)` (inspection photos), `Native.approveKeySign`, `Native.openExternal(url:)`, `pickAttachmentsOfType` (attach.dart), `ApiException` (api.dart).
features: rentdesk
env: none
requirements: none (reportlab, Pillow, python-docx / openpyxl via officegen already present)
android: none
neighbours: propagent (broker: listings, tenant leads, site visits, commission - a deal it closes becomes a rentdesk tenancy); society (housing society manager: society maintenance bills - rentdesk only records what the tenant pays her); sitesup / interior / archassist (not related); helpdesk / aftersales / office (office IT / appliance dealers / office vendors - rentdesk keeps its own small vendor list for rented units); employee inbox (BizDue mirror + biz tools); galla (UPI credit hint); idvault (Aadhaar / PAN); approvekey (fingerprint, kind "rentdesk"); officegen + chatfiles (Word / Excel / PDF as her files); payroll (staff salaries, not here); gstp (GST returns if she charges GST on commercial rent).
claude_md: |
  ## v0.1xx Rentdesk Sahayak: Hoola as a property manager ("Property manager" on the Employee page; Makaan suite)
  - Owner's spec: keeps units and tenants -> rent + deposit + maintenance ledger with due dates, receipts and reminders -> leave &
    licence / rent agreement drafts and renewal / escalation dates -> police tenant verification + agreement registration checklist ->
    maintenance requests to vendors -> move-in / move-out inspection with photos and the deposit settlement statement. Waits for her
    Haan on: any deduction from a deposit, any rent increase / notice, any message to a tenant, any repair spend. Money never moves.
  - Server `server/app/rentdesk/{rules,models,service,api}.py`, tools `rentdesk` / `rentdesk_dekho` (`agent/rentdesk_tools.py`, chat +
    calls) + customer-safe `biz_rent_status` / `biz_rent_repair` for tenants on her business WhatsApp, duty `rentdesk_work`, role
    `property_manager`, preset `rentdesk`, API `/api/rentdesk/*`, app Profile > "<name> · Property manager" (`lib/ui/rentdesk_screen.dart`:
    Aaj / Units / Kirayedar / Haan / Repair / Niyam + `RentdeskTenancyPage` with ledger, receipts, checklist, inspection, deposit
    settlement), cards RentdeskApprovalCard (`rentdesk_approval`), RentdeskMessageCard (`rentdesk_message`), RentdeskReceiptCard
    (`rentdesk_receipt`), RentdeskAlertCard (`rentdesk_alert`), RentdeskDayCard (`rentdesk_day`). Tests `server/tests/test_ghar_rentdesk.py` (6).
  - Units U-001 (flat / house / room / PG bed / shop / office / godown; residential vs commercial; area, rent ask, deposit ask,
    maintenance only as her numbers; inventory list; agency owner name / phone). Tenants P-001 (phone 10 digits, kind individual /
    family / student / company / firm, GSTIN + composition flag for GST notes, members, no_messages); Aadhaar / PAN go straight into the
    Pehchaan Locker (`idvault.save`, person "kirayedar P-001"), only {id:...} + masked kept; free text scrubbed (OTP / PIN / card /
    12-digit / PAN). Cross-module writes (idvault, BizDue, chatfiles) always run after Rentdesk's own session closes (SQLite locks).
  - Tenancies T-0001 (draft -> active -> notice -> ended): kind leave_licence (default in MH) | rent | mta (Model Tenancy Act states),
    start + months -> end, rent, deposit, maintenance + who pays, due day, escalation % every N months, lock-in, notice months, her
    stamp duty / registration fee. Activate refuses a unit already let; money fields of a live tenancy change only via a rent-change card.
    Notes per tenancy: deposit vs the MTA cap (2 months residential / 6 non-residential, only in MTA-aligned states), TDS (Income-tax
    Act 2025 s.393(1): individual / HUF tenant 2% once a year when rent > Rs 50,000 a month, Table 2(i), Form 141 (replaces 26QC); company /
    firm 10%, Table 2(ii).D(b), old 194-I), GST (residential to an individual for living: none; residential to a GST-registered tenant
    for business: 18% RCM; commercial: 18% forward charge if she is registered, RCM by a registered tenant from 10 Oct 2024 when she
    isn't, composition tenants excluded from 16 Jan 2025; PG / hostel up to Rs 20,000 per person per month with 90+ days stay exempt),
    MH s.55 registration line, MTA Rent Authority + 3-month notice line. Checklist (state-wise): KYC, written agreement, MH IGR online
    e-registration (s.55: landlord's duty; else the tenant's version prevails; up to 3 months / Rs 5,000) and police information (auto via
    Leave and Licence 2.0 for registered e-L&L where rolled out, else police station / portal; BNS s.223), other states: Registration Act
    s.17 for 12+ months + local police, MTA Rent Authority in 2 months; society intimation, move-in inspection, deposit receipt.
  - Ledger: worker bills rent (rent history = escalations she approved) and tenant-paid maintenance per licence month up to today +
    her reminder days; deposit charge on activation; advance paid ahead is applied to new months. `received` (owner only) allocates to the
    oldest open lines, numbers receipts R/<FY>/0001, Galla UPI credit of the same amount within 3 days = "sirf ishaara", receipt PDF
    (reportlab A5: landlord name / address / PAN masked, or full PAN from the locker only if she turned `receipt_full_pan` on; period
    lines; revenue-stamp box for cash > Rs 5,000) and HRA notes (Form 124 from 1 Apr 2026 asks the landlord PAN when rent > Rs 1 lakh a
    year). Charges are mirrored as `BizDue` so a tenant who writes to her business number sees only their own dues (biz_rent_status +
    UPI link to her UPI ID); paid lines close the BizDue. Void payment re-opens lines. One-off charges (electricity / water / late fee per
    agreement) and waivers are owner-only.
  - Messages: reminder (remind_before days before due), late (after grace days), receipt, rent change / notice / renewal letter text,
    refund summary, repair update, custom - all DRAFTS (`rentdesk_message`), once per charge stage, never for tenants who said no;
    OTP / PIN / card text refused. ONLY `POST /messages/{id}/send {via, hash}` sends: self = her own WhatsApp / SMS link (marked sent),
    business = `employee.inbox.send` (tenant must have written to the business number; 24 h window enforced there).
  - Cards (`rentdesk_approval`, A-0001; hash over what is shown + the state it was made from read again at the tap, so any change =
    stale): rent_change (her number or her agreement's escalation %; worker makes one when an escalation date is within 30 days; checks:
    above the agreement %, MTA 3-month notice) -> on Haan: rent history, unpaid future rent lines updated, revision letter (Word) +
    message draft; notice (vacate with notice / lock-in checks, or renewal offer) -> letter + draft, status notice; repair (vendor quote,
    30%+ above her usual for that trade flagged, who pays: owner or tenant up to her minor-repair limit) -> tenant charge only if she
    approved and the tenant pays; deduction (deposit settlement). Money kinds (deduction, repair) need her fingerprint once a phone key
    is active (approvekey message kind "rentdesk").
  - Repairs M-0001 from her / staff words or the tenant's WhatsApp (category by Hinglish words: plumber / electrician / appliance /
    carpenter / painter / pest / gas / internet / civil; urgent words like gas leak / chingari / current / paani bhar -> safety line);
    same open category on the unit = joined; vendor list with a WhatsApp draft link she opens; done only after the spend card when quoted.
  - Inspections: move-in / move-out with standard rooms x items + her inventory, conditions good / fair / damaged / missing, meters,
    keys; photos re-encoded from pixels (Pillow, no exif written: GPS / camera / time gone) in data/rentdesk/<tenant>/<inspection>;
    compare = items worse at move-out (normal wear and tear noted, no amount suggested). Settlement: deposit held - pending dues - HER
    deduction lines (amount + reason + photos) = refund (or tenant owes); no deduction and no dues = approved straight away; numbers
    frozen at her approval, dues closed "from deposit", statement PDF + refund message draft; she sends the refund and taps "Maine de
    diya" -> tenancy ended, unit vacant. DPDP `forget` (owner, only after the refund): name -> "Purana kirayedar P-001", phone / email /
    address / members / IDs (locker rows deleted) / inspection photos removed, amounts and receipt numbers kept for her accounts; worker
    nudges 90 days after move-out.
  - Agreement: Word draft (officegen) "DRAFT - not legal advice", parties, premises, period, fee, escalation, deposit (interest free,
    refundable less dues / damage beyond wear and tear), maintenance / utilities, use, repairs (minor by tenant up to her limit), 24 h
    entry notice, notice, lock-in, licence-only clause (MH s.24), registration + police clause (MH s.55) with her stamp duty / fee or
    [blanks], inventory annexure, signatures + witnesses; every missing fact listed as a blank. Signing / registration happen on IGR by her.
  - Never: moving money, sending a message by itself, inventing rent / deposit / stamp duty / area / dates, scraping IGR / police /
    portals, storing plain ID numbers.
  - Sources (checked 23 Oct 2026): advocatekhoj.com Maharashtra Rent Control Act 1999 s.55 bare text; rentu.in 27 May 2026 (Maharashtra
    online L&L e-registration, stamp duty + fee online, unregistered agreements lack validity); punekarnews.in 3 Jun 2025 (Leave and
    Licence 2.0: registered L&L data to CCTNS / all 1,203 police stations, BNS s.223 cases); addressadvisors.com Sep 2026 (viral "rent rules
    2026" are not law; MTA-aligned: Assam, Arunachal, A&N, DNH&DD, Lakshadweep; UP / AP / TN / Uttarakhand on an older draft);
    housing.com (Rajya Sabha 25 Jul 2022); blog.tdsman.com Jun 2026 (s.393(1) Table 2(ii).D(a)/(b), 2% / 10%, Rs 50,000 a month, from 1
    Apr 2026); incometax.gov.in Form 141 help (rent by individual / HUF = Table 2(i), Schedule A; replaces 26QB / 26QC / 26QD / 26QE);
    incometaxindia.gov.in 194-IB page (2%, last month of the year / tenancy, 20% without PAN capped); angelone.in 1 Apr 2026 (HRA Form 124,
    landlord PAN > Rs 1 lakh, relationship, Pune / Bengaluru / Hyderabad / Ahmedabad added to 50% metros); cleartax.in RCM on commercial
    rent (10 Oct 2024; Notfn 07/2025-CT(R) composition exclusion from 16 Jan 2025); bajajfinserv.in 18 Jun 2026 (PG / hostel Rs 20,000 per
    person per month, 90 days); DPDP Act 2023 + Rules 2025. State deposit caps beyond MTA states, stamp duty rates and registration fees
    are not built in: her numbers from the IGR calculator / sub-registrar.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/rentdesk_screen.dart (Dart 3 records in `_form`, switch expressions, `Press` / `Glass(margin:, border:)` / `Caption` from glass.dart, `api.uploadFile(fields:)`). Business-WhatsApp send tested only with a fake `inbox.send`; the BizDue mirror and Galla hint use the real tables. Fingerprint flow tested with approvekey patched (same as fleet). Receipt / settlement PDFs are Latin-only reportlab (Devanagari names print as '?'; names are usually typed in Latin; lekhak's Chromium printer could be used later). The Maharashtra e-registration / police rules are summarised from bare text + news, not legal advice; whether the IGR Leave and Licence 2.0 police auto-share covers her area is for her to confirm. Income-tax Act 2025 table numbers come from secondary sources (tdsman blog) + the official Form 141 help page.
