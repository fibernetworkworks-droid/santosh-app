# Segment 07 — Accounting, Tax, Audit Practice, Corporate Finance and Business Finance Operations (worldwide)

Research date: 22 Nov 2026. Sources opened are listed at the end. Anything marked "(from memory - verify)" was not re-checked on a live page in this session.

## 0. How this segment was built

**Human occupations covered (taxonomy anchors)**
- US BLS OOH: Accountants and Auditors (1,595,200 jobs in 2025; types: public, management, government, external auditor, internal auditor, IT auditor; tasks: examine statements, compute taxes and prepare returns, inspect books for fraud risk, maintain records, recommend cost cuts, write reports) [BLS-1]; Bookkeeping, Accounting and Auditing Clerks (~1.5M jobs, projected **-6% 2025-35** "because software automation of routine tasks" - remaining work shifts to analysis/advisory) [BLS-2]. Also (from memory - verify) BLS: Payroll and Timekeeping Clerks, Billing and Posting Clerks, Tax Preparers, Tax Examiners/Collectors, Financial Managers (Controllers/Treasurers), Budget Analysts, Financial Analysts, Cost Estimators, Compliance Officers.
- ILO ISCO-08 (from memory - verify): 2411 Accountants, 2412 Financial and investment advisers, 3313 Accounting associate professionals, 3352 Government tax and excise officials, 4311 Accounting and bookkeeping clerks, 4313 Payroll clerks, 1211 Finance managers, 3343 Administrative/executive secretaries (company secretarial).
- EU ESCO (from memory - verify): accountant, auditor, tax advisor, tax compliance officer, payroll clerk, financial controller, budget analyst, cost analyst, credit controller, accounts payable/receivable clerk, company secretary, sustainability reporting specialist.
- UK SOC 2020 (from memory - verify): 2421 Chartered and certified accountants, 3531 Estimators/valuers, 4122 Book-keepers, payroll managers and wages clerks, 3532 Brokers..., 2423 Management consultants; Australia ANZSCO 2211 Accountants (Auditors, Company Secretaries and Corporate Treasurers = 2212), 5511 Accounting Clerks, 5512 Bookkeepers, 5513 Payroll Clerks.
- Industry org charts (CFO office): Controller -> GL accountant, AP, AR/credit control, payroll, fixed assets, inventory/cost accountant, revenue accountant, consolidation/technical accounting, SEC/external reporting; Treasurer -> cash management; Head of Tax -> indirect, direct, transfer pricing, tax technology; FP&A; Internal audit/SOX; Company secretary; Sustainability reporting.

**Demand context (evidence)**
- Talent shortage: ~300,000-340,000 US accountants left the profession 2019-2023; CPA exam candidates peaked 2016 at 102,291 and fell yearly; AICPA National Pipeline Advisory Group (2024) report [AICPA-search, NYSSCPA, CFO Dive].
- Late payment: QuickBooks 2026 report - **59% of US small businesses have invoices 30+ days overdue (up from 47%)**; 55% on net-30 terms have overdue invoices vs 26% on immediate terms; 2025 report average owed >$17,000 [QB-2026, QB-2025]. Xero Q2 2026: average wait 29.3 days, payments ~9 days late. GoCardless ANZ: 41% of Australian SMBs paid >14 days late on average [late-payment search].
- Payroll errors: EY survey (500+ payroll pros) - 1 in 5 US payrolls contain errors, **$291 per error**, 15 corrections per period, ~29 weeks/year of a payroll FTE spent fixing [EY-payroll].
- Tax authority friction: US National Taxpayer Advocate 2025 report - IRS suspended 13M+ returns for review; ~3.6M refunds beyond normal timeframe; amended returns = Most Serious Problem #1 [TAS-2025].
- AI is real and funded: Basis (AI agents for accounting firms, demonstrated autonomous end-to-end 1065 return) raised $100M at $1.15B, Feb 2026 [Basis]; Numeric (close) $51M Nov 2025; Rillet reported $100M Series C Aug 2026 (single source - verify) [Rillet]; BlackLine Verity Prepare multi-agent reconciliation GA 27 Jul 2026 [BlackLine]; Ramp AP agents (coding, approval routing, fraud) [Ramp]; Blue J/CPA.com 2026 survey: **60% of US firms use AI tax research, up from 33%** [BlueJ-survey].
- Compliance wave (structural demand): EU ViDA adopted 11 Mar 2025 - mandatory e-invoicing + digital reporting for cross-border B2B from 1 Jul 2030, phased to Jan 2035 [ViDA]; Belgium B2B Peppol from 1 Jan 2026, France from 1 Sep 2026 (SME phase Sep 2027), Poland KSeF 2026-27, Germany issuance from 2027 (>EUR 800k turnover), Saudi ZATCA wave 25 by 1 Feb 2027 (threshold SAR 187,500), Malaysia MyInvois relaxation to 31 Dec 2027 [mandates]; UK MTD for Income Tax live April 2026 for sole traders/landlords >£50k, £30k from 2027, £20k from 2028 [MTD]; India e-invoice IRN >₹5 cr AATO, 30-day reporting cap for ≥₹10 cr since 1 Apr 2025 [India-IRN]; Brazil CBS/IBS test year 2026 (1% shown on invoices, offset), split payment slipping to 2028 [Brazil]; Pillar Two GIR first deadline 30 Jun 2026, side-by-side package 5 Jan 2026 [Pillar2]; CSRD Omnibus I: scope >1,000 employees AND >€450M turnover, transposition by 19 Mar 2027 [CSRD]; UK Companies House director ID verification deadline 17 Nov 2026 - only 55% of directors verified by end June 2026 [ECCTA].

**Cross-cutting hard limits applied to every role below:** prepares, checks, explains, calculates, drafts, tracks, reminds. Never moves money (payment runs are staged for a human tap in the bank/ERP), never submits a return or e-invoice "as" the taxpayer unless the named human approves that exact file and the rail is the official one (and where law requires a licensed signer - e.g. IRS PTIN preparer signature, UK agent, Indian CA certification - the human signs), never signs an audit opinion, financial statements, valuation, tax opinion or statutory certificate; never asks for PIN/OTP/password (portal logins happen through the user's own session/OAuth/API token typed in the app vault, never in chat).

Tier key: **A** = admin/prepare (safe), **B** = assists a named licensed/accountable person who reviews and signs. Tier C list at the end.

Region shorthand used in "Regional" lines: US, EU, UK, GCC, IN, SEA, CN/HK, JP/KR, AU/NZ, AF (NG/KE/ZA), LATAM (BR/MX), CA.

---

## A. Bookkeeping and transaction processing

### 1. Bookkeeper (books-in-a-box)
Keeps the general ledger current from bank feeds, receipts and invoices.
- Hires: sole trader, SME, accounting firm (as staff augmentation).
- Jobs: import bank/card feeds; categorise transactions with learned rules; match receipts/bills to transactions; flag duplicates and personal spend; maintain chart of accounts; post recurring journals; prepare monthly trial balance and simple P&L/balance sheet; produce "questions for owner" list; keep audit trail of every change.
- Tier A. Owner/accountant approves rule changes and closes the period.
- Data/rails: open banking (US Plaid/MX/Finicity; UK/EU PSD2 AIS; IN Account Aggregator; AU CDR; BR Open Finance; SG SGFinDex - check), card feeds, QuickBooks/Xero/Sage/Zoho/MYOB/Tally/Freee APIs, OCR of receipts.
- Regional: chart-of-accounts standards differ - France PCG, Spain PGC, Germany SKR03/04 (DATEV), Brazil SPED ECD plano referencial, China CAS charts, Japan blue-return (aoiro) bookkeeping, India Schedule III; Germany GoBD record-keeping rules; Portugal SAF-T; Poland JPK.
- Existing: Pilot, Bench (shut Dec 2024 then acquired - from memory - verify), Puzzle, Digits, Xero JAX/AI (from memory - verify), QuickBooks Intuit Assist, Basis [Basis].

### 2. Receipt & expense capture clerk
Turns photos, emails and e-receipts into coded, policy-checked expense records.
- Hires: employee, SME, enterprise finance.
- Jobs: read receipts (any language/currency); extract VAT/GST amounts; match to card lines; check against policy (per-diem, limits, alcohol); chase missing receipts; mileage logs; build expense report for approver; prepare reclaimable VAT list (incl. foreign VAT refund files).
- Tier A. Manager approves; reimbursement paid by human.
- Data: card feeds, email inbox, Expensify/SAP Concur/Ramp/Brex/Spendesk/Pleo APIs.
- Regional: HMRC mileage rates; US IRS standard mileage + accountable plan; Germany per-diem tables (Verpflegungsmehraufwand); EU 8th/13th Directive foreign VAT refunds; India GST ITC only on valid tax invoice with GSTIN; Japan qualified invoice (since Oct 2023) needed for consumption tax credit.
- Existing: Ramp, Brex, Expensify, SAP Concur, Pleo, Spendesk (from memory - verify).

### 3. Accounts payable clerk (bill processor)
Captures supplier bills, codes them, matches to PO/receipt and stages payment runs.
- Hires: SME, mid-market, shared service centre, accounting firm.
- Jobs: inbox/portal intake; extract header + lines; GL/cost-centre coding from history; 2-/3-way match; duplicate and fraud checks (bank-detail change, lookalike vendor); approval routing; early-pay discount and due-date optimisation; payment-run proposal for human release; supplier statement reconciliation; remittance advice drafting; withholding (TDS/WHT) computation on bills.
- Tier A. Approver signs off; treasury/owner releases payment in bank.
- Data: ERP/accounting APIs, e-invoice networks (Peppol, KSeF, IRN, NF-e downloads), bank payment file formats (ISO 20022 pain.001, NACHA, BACS, SEPA).
- Regional: IN TDS sections + MSME 45-day rule (43B(h)); UK Prompt Payment reporting for large companies; EU Late Payment Directive; AU Payment Times Reporting; KR/JP subcontract payment laws (from memory - verify); BR boleto/Pix pay-outs.
- Existing: Ramp AP agents, Vic.ai, Stampli (Billy), Tipalti, Bill.com, Medius, AvidXchange [Ramp, AP-search].

### 4. Supplier onboarding & vendor master keeper
Collects and checks supplier details before first payment.
- Hires: SME, enterprise procurement/finance.
- Jobs: send onboarding pack; collect tax forms (W-9/W-8BEN-E, GST/VAT certificates, PAN, bank letter); validate tax IDs against official lookups (EU VIES, UK VAT API, India GSTIN, US TIN matching via IRS e-Services - check, ABN Lookup, Brazil CNPJ); sanctions/watchlist screening; bank-account ownership check (UK Confirmation of Payee, EU VoP from Oct 2025); dedupe vendor master; periodic re-validation.
- Tier A. Procurement/finance approves activation.
- Regional: EU Verification of Payee (Instant Payments Regulation); UK CoP; US 1099 vendor tracking; IN MSME Udyam status.
- Existing: Tipalti, Coupa supplier portal, Kodiak/Trustpair (from memory - verify).

### 5. Purchase order & procure-to-pay coordinator
Runs requisition to PO to receipt for small teams without a procurement desk.
- Hires: SME, NGO, school.
- Jobs: turn requests into requisitions; compare quotes; draft POs; check budget availability; track deliveries/GRNs; chase partial deliveries; flag price variances; contract renewal reminders.
- Tier A. Budget holder approves PO.
- Data: ERP/procurement (Coupa, Zip, Procurify, Odoo), email.
- Existing: Zip, Coupa, Procurify (from memory - verify).

### 6. Billing & invoicing clerk (order-to-cash front end)
Produces correct, compliant sales invoices on time.
- Hires: sole trader, SME, agency, subscription business.
- Jobs: create invoices from orders/time/milestones; apply right tax codes and place-of-supply rules; generate e-invoices in local format; credit/debit notes; recurring and usage billing; multi-currency; invoice delivery via email/portal/Peppol; check customer master (tax ID, address).
- Tier A. Owner approves first-of-kind and credit notes.
- Data: CRM/orders, Stripe/Chargebee, accounting API, e-invoice rails.
- Regional: see role 23 (e-invoicing). Japan qualified invoice registration numbers; China fapiao (fully digitalised e-fapiao); Mexico CFDI 4.0 with receptor data matching SAT records exactly [CFDI]; India IRN/QR.
- Existing: Stripe Invoicing, Chargebee, Zoho Invoice, QuickBooks invoice agent.

### 7. Credit controller / collections agent (AR)
Gets customers to pay, politely and on time.
- Hires: SME, B2B supplier, accounting firm for clients.
- Jobs: daily aged-debtor list; reminder sequences tuned to customer history; draft personalised dunning emails/WhatsApp; promise-to-pay tracking; dispute logging and routing; statement of account; pay-link creation for customer tap; escalation pack (late-payment interest calculation, letter before action) for owner; DSO reporting.
- Tier A (sending reminders after owner sets rules); legal escalation decided by owner/lawyer.
- Data: accounting AR, payment gateway (Stripe/Razorpay/Paystack/Pix/Mercado Pago), email/messaging.
- Regional: UK Late Payment of Commercial Debts Act interest (8% over base); EU Late Payment Directive; IN MSMED Act Samadhaan portal (from memory - verify); US FDCPA applies to consumer debt collection only (B2C collection = careful, tier B); AU/NZ; Brazil protesto.
- Existing: Chaser, Upflow, Tesorio, HighRadius, GoCardless, QuickBooks reminders [QB-2026].

### 8. Cash application & payment matcher
Matches incoming money to invoices.
- Hires: mid-market, enterprise SSC, marketplace.
- Jobs: read bank statements (camt.053/MT940/BAI2) and remittances; match one-to-many payments; handle short-pays and deductions (claims, chargebacks); unapplied cash queue; post receipts; gateway settlement reconciliation (gross, fees, refunds).
- Tier A.
- Regional: Pix end-to-end IDs (BR), UPI RRN (IN), SEPA Instant, FedNow/RTP, Faster Payments; virtual-account collection in SEA.
- Existing: HighRadius, Billtrust, Esker (from memory - verify).

### 9. Bank & card reconciliation clerk
Proves every ledger cash line matches the bank.
- Hires: SME, firm, SSC.
- Jobs: daily/monthly bank rec; outstanding cheques/deposits in transit; unexplained items list; intercompany cash matching; credit card statement rec; petty cash counts.
- Tier A; preparer/reviewer sign-off by human.
- Existing: BlackLine Verity Prepare (multi-agent reconciliation, GA Jul 2026) [BlackLine], FloQast AI agents [FloQast], Numeric.

### 10. Fixed asset & lease accountant
Keeps the asset register and lease schedules right.
- Hires: SME, mid-market.
- Jobs: capitalise vs expense decisions drafted with policy; asset tagging; book and tax depreciation (multiple books); disposals; impairment indicators list; IFRS 16 / ASC 842 lease schedules (ROU asset, liability, interest); lease modification remeasurement.
- Tier A/B (judgement areas reviewed by controller).
- Regional: tax depreciation differs everywhere (US MACRS/bonus/§179, UK capital allowances/full expensing, IN block-of-assets WDV, DE AfA tables, JP depreciation, AU instant asset write-off, CA CCA classes).
- Existing: Sage Fixed Assets, LeaseQuery, Visual Lease, NetSuite FAM (from memory - verify).

### 11. Inventory & cost accountant
Values stock and works out product cost.
- Hires: manufacturer, retailer, restaurant, distributor.
- Jobs: stock valuation (FIFO/weighted average; LIFO only US GAAP); standard cost vs actual variances; landed cost (duty, freight); BOM cost roll-ups; shrinkage/obsolescence provisions; stock count reconciliation; COGS journal; recipe costing for food.
- Tier A/B.
- Existing: NetSuite, Odoo, Katana, MarketMan, inventory-planner tools.

### 12. Revenue recognition & billing accountant
Applies IFRS 15 / ASC 606 to contracts.
- Hires: SaaS, project business, construction, mid-market.
- Jobs: contract review for performance obligations; SSP allocation; deferred revenue waterfalls; percentage-of-completion; contract asset/liability roll-forward; commissions capitalisation (ASC 340-40); disclosure tables.
- Tier B (controller/technical accountant decides judgements).
- Existing: Rillet [Rillet], Maxio, Chargebee RevRec, Zuora RevPro, NetSuite ARM.

### 13. Multi-currency & intercompany accountant
Handles FX revaluation and intercompany balances in groups.
- Hires: SME group with subsidiaries, mid-market.
- Jobs: FX rates from central banks; unrealised/realised gains; intercompany invoicing and matching; netting proposals; mismatch resolution list; elimination entries prep; loan interest calculations.
- Tier A/B.

---

## B. Payroll and people costs

### 14. Payroll preparer (domestic)
Calculates pay correctly every cycle and prepares filings for approval.
- Hires: SME, accounting/payroll bureau, NGO.
- Jobs: collect hours/overtime/leave; compute gross-to-net (income tax, social security, pension, health); statutory leave pay (sick, maternity, paternity); deductions (loans, garnishments); variance check vs last run (EY: 1 in 5 payrolls have errors, $291 each [EY-payroll]); payslips; payment file for human release; statutory return drafts; year-end forms.
- Tier A (calculation/preparation); employer approves run and pays.
- Data/rails & regional systems: US federal/state/local withholding, FICA, FUTA/SUTA, Form 941/940, W-2, state new-hire reporting; UK PAYE RTI (FPS/EPS), NIC, auto-enrolment pensions, P60/P11D; IN TDS on salary (Form 24Q/16), EPF/ESI/PT, labour codes (from memory - verify status); DE Lohnsteuer, social insurance (DEÜV), ELStAM; FR DSN; ES SILTRA; IT UniEmens; NL loonaangifte; AU Single Touch Payroll Phase 2, superannuation (payday super from Jul 2026 - from memory - verify); NZ payday filing; CA CPP/EI, T4, ROE; JP year-end adjustment (nenmatsu chosei), resident tax; KR 4 major insurances; SG CPF, IR8A; MY EPF/SOCSO/EIS/PCB; PH SSS/PhilHealth/Pag-IBIG; GCC: UAE WPS + GPSSA for nationals, KSA GOSI + Mudad/WPS; ZA PAYE/UIF/SDL + IRP5; KE PAYE, NSSF, SHIF, Housing Levy; NG PAYE, pension (PenCom), NHF; BR eSocial, FGTS, INSS, 13th salary; MX IMSS, ISR, CFDI de nómina, INFONAVIT.
- Existing: Gusto, ADP, Paychex, Deel, Rippling, Remote, Papaya, Xero/QuickBooks Payroll, Keka/greytHR (IN), Employment Hero (AU).

### 15. Global payroll & employer-of-record coordinator
Keeps multi-country payroll inputs, providers and reconciliations aligned.
- Hires: scale-up with staff in several countries.
- Jobs: gather inputs per country by cut-off; check provider output vs inputs; reconcile gross-to-net registers to GL and bank; track country registration (employer IDs, PE risk flags for counsel); contractor vs employee misclassification checklist for lawyer; currency funding schedule.
- Tier A/B (HR/legal decides classification).
- Existing: Deel, Remote, Oyster, Papaya Global, Multiplier.

### 16. Time, attendance & overtime checker
Turns timesheets into payable hours under local rules.
- Hires: shops, restaurants, construction, care, security firms.
- Jobs: compute overtime/premiums (US FLSA + state daily OT, e.g. California); break compliance flags; shift differentials; minimum wage checks by state/country; award interpretation (AU modern awards); holiday pay averaging (UK); timesheet anomalies.
- Tier A.
- Existing: Deputy, When I Work, Tanda (AU), Homebase (from memory - verify).

### 17. Payroll tax & social-security filings tracker
Calendar + preparer for every employer return and deposit.
- Hires: SME, bureau.
- Jobs: due-date calendar per jurisdiction; deposit amount calculations (human pays); return drafts; notice reading and response drafts (e.g. IRS CP notices, HMRC penalty notices); state/local account registrations checklist; annual reconciliations (941 vs W-2, FPS vs P60).
- Tier A; employer/agent submits.

### 18. Employee benefits & pension contributions administrator
- Hires: SME, HR.
- Jobs: pension auto-enrolment assessment (UK), 401(k) deferral checks and late-deposit flags (US DOL), superannuation guarantee calc (AU), EPF/NPS (IN), CPF (SG), gratuity and end-of-service benefit accrual (GCC, IN), benefits-in-kind valuation (UK P11D, IN perquisites), reconciliation to provider statements.
- Tier A/B (trustee/administrator decides).

### 19. Contractor & freelancer payments + information-return clerk
- Hires: SME, platform, agency.
- Jobs: collect W-9/W-8; 1099-NEC/MISC/K and 1042-S prep; IR35/CEST check pack (UK) for the deciding engager; DAC7/platform reporting data (EU); India TDS 194J/194C; Australia TPAR; contractor invoice checks.
- Tier A/B.

---

## C. Close, consolidation and financial reporting

### 20. Month-end close coordinator
Runs the close checklist and gets the books to a reviewable state.
- Hires: SME with controller, mid-market, firm for clients.
- Jobs: close calendar and task list with owners; accrual and prepayment schedules; reconciliations tracker; flux/variance commentary drafts; journal entry preparation with support; cut-off checks; close status report; lock period after controller sign-off.
- Tier A/B; controller approves journals and signs off close.
- Existing: Numeric, FloQast, BlackLine, Trintech, Basis, Rillet [Numeric, FloQast, BlackLine].

### 21. Consolidation & group reporting accountant
- Hires: groups, mid-market, PE portfolio.
- Jobs: collect subsidiary packs; translate currencies (IAS 21/ASC 830); intercompany eliminations; minority interest; acquisition accounting schedules; group TB; segment reporting data; consolidation journals with evidence.
- Tier B (group controller decides).
- Existing: OneStream, Workiva, CCH Tagetik, Prophix, NetSuite OneWorld (from memory - verify).

### 22. Financial statements & disclosure drafter
Drafts annual/interim statements and notes from the TB under the right framework.
- Hires: SME needing statutory accounts, accounting firm, listed company reporting team.
- Jobs: map TB to statement lines; draft notes and accounting policies; disclosure checklist (IFRS, US GAAP, IFRS for SMEs, FRS 102/105 UK, Ind AS/AS India, J-GAAP, K-IFRS, ASPE Canada, AASB RDR Australia, Chinese ASBE, HKFRS, local GAAPs); comparatives; XBRL/iXBRL tagging (SEC, ESEF, HMRC/Companies House, MCA India, ACRA Singapore); tie-out checks.
- Tier B: directors approve and sign statements; auditor opines.
- Existing: Workiva, Silverfin (EU firms), CaseWare, Caseware Cloud, CCH, DataSnipper for tie-outs.

### 23. Technical accounting memo writer
Researches standards and drafts position papers.
- Hires: controller, CFO, firm.
- Jobs: research IFRS/ASC on a transaction (leases, revenue, financial instruments IFRS 9/ASC 326 CECL, business combinations, share-based payment, crypto, IFRS 18 presentation transition from 2027 - from memory - verify); draft memo with alternatives; impact quantification; disclosure draft.
- Tier B: controller/auditor accepts the conclusion.

### 24. SEC / listed-company reporting assistant
- Hires: listed issuers, pre-IPO.
- Jobs: 10-K/10-Q/8-K/20-F drafting support, tie-outs, MD&A data, SEC comment letter response drafts, EDGAR iXBRL checks; equivalents: UK listing rules and ESEF, India SEBI LODR results, HKEX, SGX, ASX continuous disclosure calendars.
- Tier B (CFO/CEO certify; counsel reviews).

### 25. SOX / internal controls tester (ICFR)
- Hires: listed company, pre-IPO, internal audit.
- Jobs: risk-control matrix maintenance; walkthrough documentation; sample selection; test of controls with evidence; deficiency log and severity draft; user access reviews; segregation-of-duties conflicts; remediation tracking.
- Tier B (control owner and internal audit conclude; management certifies).
- Regional: US SOX 302/404; Japan J-SOX; India IFC (Companies Act s.134); UK new Provision 29 of Corporate Governance Code (from 2026 - from memory - verify); China C-SOX.
- Existing: AuditBoard, Workiva, MindBridge.

---

## D. FP&A, management accounting and CFO office

### 26. Budget builder (annual budget & forecast)
- Hires: SME, NGO, school, department heads.
- Jobs: driver-based budget templates; collect inputs from managers; headcount plan costs; rolling forecast updates; scenario versions; budget vs actual monthly; reforecast commentary.
- Tier A; CFO/board approves budget.
- Existing: Datarails, Runway, Mosaic (acq. by Bill - from memory - verify), Cube, Pigment, Anaplan, Planful.

### 27. Cash-flow forecaster & treasury assistant
- Hires: SME, startup, mid-market.
- Jobs: 13-week cash forecast from AR/AP/payroll/tax calendars; weekly actual vs forecast; covenant headroom; liquidity alerts; FX exposure summary; draft funding options list; bank-fee analysis.
- Tier A; owner/treasurer moves money and decides hedges.
- Existing: Agicap, Kyriba, Trovata, Float (UK), Fathom.

### 28. Management accounts & KPI reporter
- Hires: SME, franchise, PE portfolio company.
- Jobs: monthly management pack; margin by product/customer/location; unit economics (CAC, LTV, churn for SaaS; table turns for restaurants); board deck charts; plain-language narrative.
- Tier A.
- Existing: Fathom, Syft, Spotlight Reporting, Jirav, Digits.

### 29. Variance & profitability analyst
- Hires: mid-market, manufacturer.
- Jobs: price/volume/mix bridges; cost-centre variance; customer profitability; ABC costing; pricing proposals with margin impact; make-vs-buy analysis.
- Tier A/B.

### 30. Business case & investment appraisal analyst
- Hires: SME capex decision, NGO projects, councils.
- Jobs: NPV/IRR/payback models; sensitivity; lease-vs-buy; financing comparisons; public-sector cost-benefit (UK Green Book - from memory - verify).
- Tier A; decision by owner/board.

### 31. Fractional CFO assistant (for the human fractional CFO or owner)
- Hires: startup, SME, fractional CFO firms.
- Jobs: weekly finance memo; runway and burn; board pack prep; investor update drafts; cap table checks with scenario dilution; covenant and compliance calendar; pricing reviews; fundraise data room index.
- Tier B (the CFO/founder decides and signs).
- Existing: Pilot (CFO services), Puzzle, Runway, Carta (cap table).

### 32. Startup finance setup & compliance assistant
- Hires: founders.
- Jobs: entity-choice comparison pack for adviser; registration checklists (EIN, VAT/GST, payroll registration); chart of accounts setup; Delaware franchise tax and annual report reminders; 83(b) election deadline reminder (30 days - user files); R&D credit data collection; SAFE/convertible note accounting; option pool and 409A data prep for valuer.
- Tier A/B.
- Regional: US Delaware/Form 5472 for foreign-owned; UK SEIS/EIS advance assurance packs, R&D (merged scheme); India DPIIT recognition, angel tax (abolished 2024 - from memory - verify); SG startup exemptions; Estonia e-Residency.

### 33. Board & investor reporting pack builder
- Hires: startups, PE/VC portfolio companies, NGOs (trustee reports).
- Jobs: quarterly KPI pack; investor update email; reconciled numbers; covenant compliance certificate draft for CFO signature.
- Tier A/B.

---

## E. Indirect tax and e-invoicing

### 34. VAT/GST return preparer
- Hires: SME, firm, mid-market.
- Jobs: tax-code review of ledger; input tax eligibility checks; reverse charge, partial exemption; return figures and reconciliation to ledger; draft return for filer; payment amount for human to pay; amendments/corrections.
- Tier A/B (filer = taxpayer or agent).
- Regional: UK MTD for VAT via API; EU member-state returns + OSS/IOSS; IN GSTR-1/3B/9 with 2B/IMS reconciliation; AU BAS; NZ GST; SG GST F5 (IRAS); MY SST; TH VAT; JP consumption tax with qualified invoices; KR VAT with electronic tax invoice (NTS); CN VAT with Golden Tax IV; GCC VAT (KSA, UAE, Bahrain, Oman); ZA VAT201; KE VAT with eTIMS; NG VAT (TaxPro Max); CA GST/HST/QST; MX IVA/DIOT; BR ICMS/PIS/COFINS now CBS/IBS transition.
- Existing: Avalara, Vertex, Sovos, Taxually, Fonoa, Clear (IN).

### 35. E-invoicing compliance clerk (clearance & Peppol)
Makes each invoice legally valid in its country's e-invoice system.
- Hires: any business selling B2B in a mandated country.
- Jobs: map invoice data to local schema (UBL/Peppol BIS 3.0, Factur-X/ZUGFeRD, XRechnung, FA(3) KSeF, ZATCA UBL + QR + cryptographic stamp, IRN JSON, CFDI 4.0 XML, NF-e/NFS-e, SAT complements like Carta Porte); validate before submission; track clearance status and rejections; fix and resubmit for approval; archive per retention rules; inbound e-invoice retrieval and booking.
- Tier A (technical submission through certified provider/API after approval rules set by business).
- Regional (dates per [mandates], [India-IRN], [CFDI], [Brazil], [ViDA]): EU ViDA cross-border 2030; BE 2026; FR Sep 2026/2027 via PDP platforms; PL KSeF 2026-27; DE receive 2025 / issue 2027-28; IT SdI since 2019; ES Verifactu + B2B (check); GR myDATA; RO e-Factura; HU RTIR; KSA FATOORAH waves; UAE 2026-27 Peppol-based (check); EG ETA; MY MyInvois; SG InvoiceNow; AU/NZ Peppol; JP Peppol (JP PINT); IN IRN >₹5 cr, 30-day cap ≥₹10 cr; CN e-fapiao; KR e-tax invoice; LATAM CFDI MX, NF-e BR, Chile DTE, Colombia DIAN, Peru SUNAT; KE eTIMS; NG e-invoicing pilot (check); ZA (planned - check).
- Existing: Sovos, Pagero (Thomson Reuters), Avalara E-Invoicing, Edicom, Comarch, Storecove, ClearTax.

### 36. US sales tax nexus & filing assistant
- Hires: e-commerce, SaaS, SME selling across states.
- Jobs: economic nexus monitoring (Wayfair thresholds per state); product taxability mapping; exemption certificate collection/validity; marketplace facilitator rules; return prep per state; registration checklists; voluntary disclosure data for adviser.
- Tier A/B.
- Existing: Avalara, TaxJar (Stripe), Anrok, Numeral, Kintsugi.

### 37. Cross-border e-commerce tax clerk (OSS/IOSS, digital services)
- Hires: online sellers, SaaS, marketplace sellers.
- Jobs: where-is-VAT-due for each sale; OSS/IOSS returns; non-resident VAT/GST registrations (UK, AU, NZ, SG, IN OIDAR, CA, JP, KR, GCC, ZA, KE); digital services taxes; marketplace deemed-supplier checks; DAC7 data.
- Tier A/B.
- Existing: Fonoa, Taxually, Paddle/Lemon Squeezy (merchant of record).

### 38. Customs, duties & excise accountant
- Hires: importers, exporters, manufacturers.
- Jobs: HS classification support pack for broker; landed cost; duty drawback claims data; import VAT postponed accounting (UK PVA, EU); EUDR/CBAM reporting data (EU CBAM definitive phase 2026 - check); excise returns (alcohol, tobacco, fuel); free-zone records (GCC).
- Tier B (licensed customs broker files where required).

### 39. Indirect tax reconciliation & audit-defence analyst
- Hires: mid-market, enterprise.
- Jobs: return-to-ledger-to-e-invoice-portal three-way recon (e.g. India GSTR-2B vs books, KSeF vs ledger, SAF-T submissions); notice reading; response pack drafting; penalty and interest calculations.
- Tier B.

---

## F. Direct tax, corporate tax and international

### 40. Corporate income tax return preparer
- Hires: SME, firm, mid-market.
- Jobs: book-to-tax adjustments; tax depreciation; loss carryforward schedules; credits (R&D); return drafting in local form; tax provision inputs; quarterly/advance tax instalments; extension and filing calendar.
- Tier B (signed by officer and paid preparer/agent where required).
- Regional: US 1120/1120-S/1065 + state; UK CT600 (iXBRL); IN ITR-6 + tax audit (3CD by CA); DE KSt/GewSt via ELSTER; FR liasse fiscale; JP hojinzei; AU company tax return; CA T2; BR ECF; MX declaración anual; ZA ITR14; KE iTax; NG CIT (TaxPro Max); UAE CT (9% from 2023) via EmaraTax; KSA zakat/CIT.
- Existing: Basis (autonomous 1065) [Basis], CCH Axcess, Thomson Reuters CoCounsel Tax, Lacerte/ProConnect, Taxfyle, Black Ore (from memory - verify).

### 41. Tax provision (ASC 740 / IAS 12) preparer
- Hires: listed/PE-backed companies.
- Jobs: current and deferred tax calculations; ETR reconciliation; uncertain tax positions schedule; valuation allowance analysis inputs; disclosure tables; Pillar Two top-up tax estimate in provision.
- Tier B.
- Existing: ONESOURCE Tax Provision, Longview, Corptax (from memory - verify).

### 42. Transfer pricing documentation assistant
- Hires: groups, mid-market, firms.
- Jobs: intercompany transaction inventory; functional analysis questionnaires; benchmark search support (human selects comparables); master file/local file drafts (OECD BEPS Action 13); CbCR data; segmentation of P&L; year-end TP adjustments calculation.
- Tier B (TP adviser/finance owns conclusions).
- Regional: IN Form 3CEB by CA; CN contemporaneous docs; DE Verrechnungspreis rules; US §482/6662; AU; MX; BR new OECD-aligned TP rules from 2024.

### 43. Pillar Two / global minimum tax data assistant
- Hires: MNE groups >€750M.
- Jobs: data-point collection by constituent entity; transitional CbCR safe harbour tests; GloBE ETR calc support; GIR data population; QDMTT local filings calendar (first GIR deadline 30 Jun 2026 most jurisdictions; side-by-side package Jan 2026) [Pillar2].
- Tier B.

### 44. Withholding tax & treaty relief clerk
- Hires: anyone paying cross-border (royalties, services, interest, dividends).
- Jobs: determine WHT rate; treaty eligibility pack (TRC, Form 10F IN, W-8BEN-E); WHT return/certificate prep; reclaim files.
- Tier A/B.

### 45. Tax research assistant
- Hires: firms, in-house tax teams, sole practitioners.
- Jobs: answer tax questions with cited primary sources; draft client emails; compare jurisdictions; track law changes and summarise; draft memos for review.
- Tier B (adviser signs the advice). Evidence: 60% of US firms now use AI tax research [BlueJ-survey].
- Existing: Blue J, CoCounsel Tax, Bloomberg Tax AI, TaxGPT, CCH AnswerConnect [BlueJ-survey].

### 46. Tax notice & audit response assistant
- Hires: consumer, SME, firm.
- Jobs: read notices (IRS CP2000, HMRC enquiry letters, Indian GST/IT notices on portals, ATO letters); explain in plain language; identify deadline; compute agreed/disputed amounts; gather evidence; draft response for human signature; track case.
- Tier A/B (representation by licensed agent where required - US EA/CPA/attorney with Form 2848).
- Evidence: TAS 2025 report - 13M+ returns suspended, amended returns MSP #1 [TAS-2025].

### 47. Tax incentives & R&D credit claims assistant
- Hires: tech/manufacturing SMEs, firms.
- Jobs: identify eligible activities from project records; staff time apportionment; qualifying cost schedules; technical narrative drafts; claim forms for adviser (US Form 6765, UK merged R&D scheme/ERIS, CA SR&ED T661, AU RDTI, IN Section 35 - check, SG EIS (from memory - verify)).
- Tier B.

### 48. Indirect-direct tax calendar & obligations tracker (compliance calendar)
- Hires: SME, firm (per client), group tax.
- Jobs: build obligations register per entity/jurisdiction; reminders; evidence of filing/payment; late-penalty exposure.
- Tier A.

---

## G. Personal tax

### 49. Personal tax return preparer (individual)
- Hires: consumers, freelancers, landlords; tax firms as staff.
- Jobs: document checklist; read slips (W-2/1099, P60, Form 16/26AS/AIS, T4, PAYG summaries, nenkin/withholding slips); deduction/relief eligibility explanation; draft return; compare regimes (e.g. India old vs new regime); estimated payments; refund tracking.
- Tier A for self-filers using official free tools; Tier B when a paid preparer signs (US PTIN).
- Regional: US 1040 + state; UK Self Assessment + MTD ITSA from Apr 2026 [MTD]; IN ITR + AIS reconciliation; AU myTax / tax agents; CA T1; DE ELSTER Einkommensteuer; FR prefilled déclaration; ES Renta Web; JP kakutei shinkoku (e-Tax); KR year-end settlement; SG mostly pre-filled; GCC: no personal income tax (mostly) - zakat in KSA; ZA eFiling; KE iTax; NG; BR IRPF pre-filled; MX declaración anual.
- Existing: TurboTax/Intuit Assist, H&R Block AI, TaxAct, ClearTax, Taxfix (EU), Wealthsimple Tax (CA).

### 50. MTD / quarterly-update assistant for sole traders & landlords
- Hires: UK sole traders/landlords (and equivalents: US quarterly 1040-ES, IN advance tax).
- Jobs: keep digital records; categorise income/expenses; prepare quarterly updates for software submission by user; estimate year-end liability; remind deadlines (first updates 7 Aug 2026, 7 Nov 2026) [MTD].
- Tier A.

### 51. Expat, non-resident & cross-border individual tax organiser
- Hires: expats, digital nomads, NRIs.
- Jobs: residency day counts; foreign income and FTC schedules; FBAR/FATCA 8938 data; UK SRT; NRI DTAA relief pack; exit tax flags for adviser.
- Tier B.

### 52. Crypto & investment gains tax calculator
- Hires: retail investors.
- Jobs: import exchange/broker data; cost basis (FIFO/HIFO/pooling UK s.104/AU); capital gains schedules; wash-sale/30-day rules; DAC8/CARF reporting awareness (EU DAC8 from 2026 - from memory - verify); Form 8949 drafts.
- Tier A.
- Existing: Koinly, CoinTracker, Divly (from memory - verify).

### 53. Household employer & domestic worker payroll helper
- Hires: households employing nannies/maids/drivers.
- Jobs: US Schedule H; UK nanny PAYE; SG FDW levy; HK MPF; GCC domestic worker contracts/WPS; IN — no statutory payroll for most domestic help but contract templates.
- Tier A.

### 54. Personal finance paperwork & document vault organiser (tax evidence)
- Hires: consumers.
- Jobs: keep receipts and statements by tax year; retention countdown; produce packs for accountant; mortgage/visa income evidence packs.
- Tier A.

---

## H. Audit (external audit support and internal audit)

### 55. Audit PBC (prepared-by-client) request coordinator
- Hires: companies being audited, NGOs, schools.
- Jobs: track auditor request list; gather documents; reconcile schedules; answer queries with evidence; deadline chasing; lead schedules.
- Tier A.
- Existing: Suralink, AuditBoard, Inflo.

### 56. Audit staff assistant (for audit firms)
- Hires: audit firms (engagement teams).
- Jobs: tie-out and vouching (DataSnipper-style); sampling; analytics (journal entry testing); confirmation tracking; workpaper drafting; risk assessment questionnaires; going-concern data analysis.
- Tier B: engagement partner reviews and signs opinion (ISA/PCAOB/local).
- Regional: PCAOB (US public), AICPA SAS (US private), ISA via IAASB (most countries), FRC (UK), NFRA/ICAI (IN), ASIC/AUASB (AU), CPAB (CA), JICPA (JP), local regulators.
- Existing: DataSnipper, MindBridge, Inflo, Caseware IDEA, KPMG Clara, Deloitte Omnia (from memory - verify).

### 57. Internal audit & risk assistant
- Hires: mid-market, NGOs, public sector.
- Jobs: risk register; audit plan drafting; fieldwork testing; continuous controls monitoring (duplicate payments, ghost vendors, split POs); findings and action tracker; IIA Global Internal Audit Standards (2025) mapping.
- Tier B (CAE concludes).
- Existing: AuditBoard, MindBridge, Galvanize/Diligent HighBond.

### 58. Fraud & forensic accounting analyst
- Hires: SME owners, firms, insurers, lawyers.
- Jobs: transaction anomaly detection; Benford analysis; vendor-employee matching; expense abuse detection; timeline reconstruction; evidence index for investigator/lawyer.
- Tier B (investigator/lawyer draws conclusions; no accusations by AI).

### 59. Grant & donor audit / compliance reporter (NGOs)
- Hires: NGOs, charities, universities.
- Jobs: fund accounting by restriction; budget vs actual per grant; allowable-cost checks (US Uniform Guidance 2 CFR 200, single audit thresholds); donor report drafts; FCRA (IN) quarterly returns; UK Charity SORP accounts.
- Tier A/B.

---

## I. Accounting/CPA/CA practice operations

### 60. Practice manager (firm workflow & client onboarding)
- Hires: accounting/tax firms.
- Jobs: client onboarding (engagement letters, KYC/AML for the firm's own obligations - e.g. UK MLR, EU AMLD); job/deadline tracking per client; capacity planning; client document requests; WIP and billing; reminders; time capture.
- Tier A; partner signs engagement letters; AML risk decided by MLRO.
- Existing: Karbon, TaxDome, Canopy, Financial Cents, IRIS, Xero Practice Manager.

### 61. Client communications & questions agent (for firms)
- Hires: firms.
- Jobs: triage client emails; draft replies; send standard checklists; chase missing info; plain-language explanations; status updates.
- Tier A/B.

### 62. Tax season organiser (firm-side)
- Hires: tax firms.
- Jobs: pre-season organisers; document intake and indexing; prior-year comparison; data entry into prep software; review notes for preparer; e-file status tracking; extension list.
- Tier A/B.
- Existing: Basis, TaxDome, SurePrep (Thomson Reuters), Gruntworx (from memory - verify).

### 63. Firm quality & review checklist assistant
- Hires: firms.
- Jobs: apply review checklists; detect inconsistencies across return/accounts; QM standards documentation (ISQM 1); CPD tracking for staff.
- Tier B.

### 64. Advisory insight generator for firms (proactive client advice drafts)
- Hires: firms.
- Jobs: scan client books for opportunities (cash, tax planning, pricing, overdue AR); draft advisory notes for partner; client health scores.
- Tier B.

---

## J. Company secretarial and statutory filings

### 65. Company secretary assistant (statutory compliance calendar)
- Hires: SME, startup, corporate service providers, firms.
- Jobs: entity register; annual return/confirmation statement prep; accounts filing deadlines; director/PSC/UBO register maintenance; board/shareholder resolutions and minutes drafts; share allotment forms; registered office changes.
- Tier A/B (director/company secretary signs; licensed CSP files where required).
- Regional: UK Companies House (identity verification for directors/PSCs - transition closed 17 Nov 2026; only 55% of directors verified by end Jun 2026 [ECCTA]); IN MCA21 (AOC-4, MGT-7, DIR-3 KYC, DPT-3, MSME-1); SG ACRA BizFile+ AGM/annual return; HK Companies Registry + significant controllers register; AU ASIC annual review + director ID; NZ Companies Office; US state annual reports + BOI (FinCEN BOI narrowed to foreign companies in 2025 - from memory - verify); CA federal/provincial + ISC register; UAE UBO + ESR (ESR repealed for later periods - check); DE Transparenzregister; FR greffe; ZA CIPC + BO; KE BRS; NG CAC; BR Junta Comercial; MX SAT/RPC.
- Existing: Diligent Entities, Inform Direct (UK), Osome, Sleek (SG/HK), Vakilsearch (IN) (from memory - verify).

### 66. Cap table & equity administrator
- Hires: startups, private companies.
- Jobs: keep cap table; model rounds; vesting schedules; ESOP grant docs drafts; share register reconciliation; equity accounting (IFRS 2/ASC 718) inputs; EMI/ISO/ESOP tax notices (UK EMI notifications, US 3921).
- Tier A/B.
- Existing: Carta, Pulley, Ledgy, Qapita, Vestd.

### 67. Statutory regulatory returns clerk (non-tax government filings)
- Hires: SMEs in regulated sectors.
- Jobs: statistics office surveys (e.g. ONS, Census Bureau), central bank FX/FDI returns (IN FC-GPR/FLA, ODI; BR BCB RDE; ZA SARB), trade licence renewals (GCC), economic substance, charity commission returns.
- Tier A.

---

## K. ESG and sustainability reporting

### 68. Sustainability / ESG data & report preparer
- Hires: mid-market/large companies, suppliers asked by customers, firms.
- Jobs: collect energy/fuel/travel data; Scope 1/2/3 calculation with emission factors (GHG Protocol); double materiality assessment support; ESRS datapoints (CSRD scope now >1,000 employees and >€450M turnover [CSRD]); ISSB IFRS S1/S2; supplier questionnaires (CDP, EcoVadis); assurance-ready evidence; India BRSR; UK SRS (from memory - verify); Australia AASB S2 mandatory climate disclosure from 2025 (from memory - verify); California SB 253/261; Japan SSBJ; China CSDS (check).
- Tier B (management approves; assurance provider opines).
- Existing: Workiva ESG, Watershed, Sweep, Persefoni, Normative, Greenly.

### 69. Carbon border & product footprint clerk
- Hires: exporters to EU, manufacturers.
- Jobs: CBAM embedded emissions data from suppliers; product carbon footprint; EU Deforestation Regulation due-diligence data; digital product passport data.
- Tier B.

---

## L. Financing, invoice finance and grants (finance-ops side)

### 70. Invoice financing & working-capital applications preparer
- Hires: SMEs.
- Jobs: compare factoring/invoice discounting/supply-chain finance offers; prepare debtor ledger and ageing for the financier; application packs; track fees and effective APR; reconcile financed invoices.
- Tier A (lender decides; owner signs and accepts).
- Regional: IN TReDS (RXIL, M1xchange, Invoicemart) for MSME receivables; UK invoice finance (ABFA - from memory - verify); US factoring; EU SCF; BR duplicatas escriturais; MX factoraje via NAFIN.
- Existing: Fundbox, Stenn (collapsed Dec 2024 - from memory - verify), Kriya, Drip Capital, KredX.

### 71. Business loan & credit application pack preparer
- Hires: SMEs.
- Jobs: financial statements and projections pack; bank statement analysis; DSCR calc; collateral list; application form drafts; covenant tracking after loan.
- Tier A (lender decides).

### 72. Grants & subsidy finder + applicant
- Hires: SMEs, NGOs, researchers, farmers.
- Jobs: search eligible grants; eligibility checklist; budget and narrative drafts; deadline tracking; post-award spend tracking and reporting; audit-ready evidence.
- Tier A/B.
- Regional: US SAM.gov/Grants.gov + SBIR; EU Horizon Europe/EIC, structural funds; UK Innovate UK; IN Startup India Seed Fund, PLI, state subsidies; SG EDG/PSG; AU state grants; CA IRAP; GCC funds (Monsha'at KSA, Khalifa Fund UAE); AF (e.g. Tony Elumelu Foundation); BR FINEP.

### 73. Government incentive & tax-holiday compliance tracker
- Hires: companies in SEZs/free zones/incentive schemes.
- Jobs: track conditions (employment, investment, export thresholds), prepare compliance reports, flag clawback risk.
- Tier A/B.

---

## M. Specialist industry accounting roles (high demand niches)

### 74. Construction & job-cost accountant
- Jobs: job costing, WIP schedules, retention, progress billing (AIA G702/703), CIS (UK) deductions and returns, subcontractor compliance, certified payroll (US Davis-Bacon). Tier A/B.

### 75. Property & landlord accountant
- Jobs: rent ledger, deposits, service charge accounts, landlord statements, property tax deductions, MTD ITSA for landlords, NRL (UK non-resident landlord). Tier A.

### 76. Restaurant & retail accountant
- Jobs: POS-to-ledger daily sales recon, tips allocation and tip reporting, food cost %, inventory counts, delivery platform settlement recon (Uber Eats/Swiggy/Zomato/Talabat/iFood/Rappi). Tier A.

### 77. E-commerce & marketplace accountant
- Jobs: Amazon/Shopify/Flipkart/Shopee/Mercado Libre settlement reconciliation, fee breakdowns, returns, TCS/TDS on e-commerce (IN 194-O/TCS), marketplace VAT. Tier A.
- Existing: A2X, Link My Books, Synder.

### 78. Nonprofit & fund accountant
- Jobs: restricted/unrestricted funds, donation receipts (80G IN, Gift Aid UK, US 501(c)(3) acknowledgements), Form 990 data, charity returns. Tier A/B.

### 79. Professional services / agency accountant
- Jobs: time-to-billing, WIP, utilisation, project margin, retainers. Tier A.

### 80. Agriculture & farm accountant
- Jobs: crop/livestock records, subsidy claims (EU CAP, US USDA), farm tax averaging, mandi/APMC receipts (IN). Tier A.

### 81. Healthcare practice accountant
- Jobs: clinic revenue cycle to ledger, insurer remittance recon, doctor payouts/locum invoices, GST/VAT exemptions on medical. Tier A.

### 82. Public-sector / municipal accountant assistant
- Hires: councils, panchayats, schools, government agencies.
- Jobs: fund/budget accounting, encumbrances, IPSAS/GASB reporting drafts, grant reconciliations, procurement compliance, PFMS (IN). Tier B.

---

## Never an AI employee (tier C) in this segment

| Task | Why reserved for a human |
|---|---|
| Signing an audit opinion / review report / assurance report (ISA, PCAOB, ISAE 3000, CSRD assurance) | Statutory: only a registered auditor/firm can sign; personal liability and independence rules |
| Signing financial statements / directors' report / CEO-CFO certifications (SOX 302/906) | Law places this on named directors/officers |
| Signing a tax return as paid preparer or as taxpayer; certifying tax audit reports (IN 3CD), TP certificates (3CEB), 15CB, GST certificates | Requires licensed signer (PTIN/CA/registered agent) or the taxpayer's own declaration |
| Representing a taxpayer before an authority (IRS Form 2848, HMRC agent, appellate hearings) | Licensed representation; AI drafts only |
| Releasing payments, payroll funding, tax payments, approving a payment run | Money moves only on the human's tap |
| Concluding employee vs contractor status, PE exposure, IR35 status determination | Legal determination with liability; adviser/engager decides |
| Choosing comparables and concluding arm's-length price; giving a tax opinion / "should" opinion | Professional judgement with penalty-protection implications |
| Business valuation sign-off (409A, fairness opinions, purchase price allocation sign-off) | Credentialed valuer; reliance by third parties |
| Deciding audit adjustments, materiality, going-concern conclusion, control deficiency classification | Auditor/management judgement |
| Approving journals, closing/locking periods, accepting write-offs and provisions | Accountable controller/owner |
| Filing statutory/regulatory reports as the institution where a named officer certifies (e.g. charity trustees' declarations, XBRL filings with digital signature of director/CA) | Named officer certification; digital signature belongs to the person |
| Accusing anyone of fraud, reporting to police/FIU | Investigator/MLRO decision |
| Holding the user's tax portal password/OTP/digital signature certificate | Hoola rule: never collected; user logs in through official delegation (agent access, API tokens, OAuth) |

---

## Top 10 roles to build first and why

1. **Bookkeeper (role 1)** – the foundation every other role reads from; biggest market (every SME), clerical work BLS says is being automated (-6% jobs) [BLS-2]; proven by Pilot/Puzzle/Digits/Basis.
2. **Credit controller / collections agent (7)** – urgent, measurable pain: 59% of US small businesses have invoices 30+ days overdue [QB-2026]; quick wins without touching money (drafts + pay links the customer taps).
3. **Accounts payable clerk (3)** – high-volume, clearly bounded; staged payment runs fit the "human taps" rule; strong vendor evidence (Ramp, Vic.ai, Stampli) [Ramp].
4. **E-invoicing compliance clerk (35)** – regulation-driven forced demand across EU (ViDA 2030, BE/FR/PL/DE 2026-28), KSA, Malaysia, India, LATAM [ViDA, mandates]; same core engine reused per country schema.
5. **VAT/GST return preparer (34)** – recurring monthly/quarterly job everywhere; pairs with 35; Hoola already has India GST pieces.
6. **Payroll preparer (14)** – error-prone and costly ($291/error, 1 in 5 payrolls) [EY-payroll]; country packs can be added one by one; human runs and funds payroll.
7. **Month-end close coordinator (20)** – the AI-close market is heavily funded (Numeric, Rillet, BlackLine Verity, FloQast) proving willingness to pay; mid-market wedge.
8. **Cash-flow forecaster (27)** – owners' top question ("will I make payroll?"), built purely on data already captured by 1/3/7/14.
9. **Personal tax return preparer + MTD quarterly assistant (49/50)** – mass consumer and sole-trader market with new obligations (UK MTD ITSA from Apr 2026, thresholds falling to £20k by 2028) [MTD]; tax authority friction is documented [TAS-2025].
10. **Practice manager + tax research assistant for firms (60/45)** – firms face a talent shortage (300-340k US accountants left 2019-23) [AICPA-search] and are already buying AI (60% use AI tax research) [BlueJ-survey]; selling to firms multiplies reach to their clients.

(Honourable mentions: company secretary assistant (65) – ECCTA ID verification and annual filings create calendar pain [ECCTA]; grants finder (72); ESG preparer (68) for suppliers answering customer questionnaires even after CSRD scope cuts.)

---

## Sources (opened or returned by live search in this session)

- [BLS-1] US BLS OOH, Accountants and Auditors: https://www.bls.gov/ooh/business-and-financial/accountants-and-auditors.htm (opened)
- [BLS-2] US BLS OOH, Bookkeeping, Accounting, and Auditing Clerks: https://www.bls.gov/ooh/office-and-administrative-support/bookkeeping-accounting-and-auditing-clerks.htm (opened)
- [ViDA] European Commission ViDA: https://taxation-customs.ec.europa.eu/taxation/vat/vat-digital-age-vida_en ; adoption news https://taxation-customs.ec.europa.eu/news/adoption-vat-digital-age-package-2025-03-11_en ; Deloitte https://www.deloitte.com/be/en/services/tax/blogs/final-go-for-the-vida-package.html
- [mandates] Sovos mandate tracker https://sovos.com/taxapedia/?p=29 ; Taxually https://www.taxually.com/blog/e-invoicing-mandates-by-country-2026 ; VATupdate worldwide mandates PDF https://www.vatupdate.com/wp-content/uploads/2026/07/2026-09-27-Worldwide_E-Invoicing_Mandates.pdf ; Tradeshift https://tradeshift.com/resources/compliance/worldwide-e-invoicing-compliance-2026/
- [AICPA-search] AICPA pipeline report news https://www.aicpa-cima.com/news/article/pool-of-accounting-graduates-continues-to-shrink-in-u-s-aicpa-report-finds ; NYSSCPA https://www.nysscpa.org/article-content/in-report-aicpa-advisory-group-offers-recommendations-to-solve-talent-shortage-082224 ; CFO Dive https://www.cfodive.com/news/us-accounting-degree-graduates-plunge-auditing-accountant-audit/696890/
- [Basis] Business Wire https://www.businesswire.com/news/home/20260224020999/en/ ; CPA Practice Advisor https://www.cpapracticeadvisor.com/2026/02/24/basis-raises-100-million-to-deploy-ai-agents-for-accounting-firms/178759/
- [Rillet] CPA Trendlines https://cpatrendlines.com/2026/08/24/rillets-raise-100-million-bets-on-fewer-accountants/ (single source - verify)
- [Numeric] CB Insights https://www.cbinsights.com/compare/basis-10-vs-numeric-2 ; TechCrunch https://techcrunch.com/?p=2896647
- [TAS-2025] National Taxpayer Advocate 2025 Annual Report, Most Serious Problems https://www.taxpayeradvocate.irs.gov/reports/2025-annual-report-to-congress/most-serious-problems/ ; KPMG summary https://kpmg.com/us/en/taxnewsflash/news/2026/01/national-taxpayer-advocate-report-congress.html
- [QB-2026] QuickBooks 2026 Small Business Late Payments Report https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2026/ ; [QB-2025] https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2025/ ; UK edition https://quickbooks.intuit.com/uk/blog/small-business-late-payments-report-2025/
- [EY-payroll] EY survey via Business Wire https://www.businesswire.com/news/home/20221222005093/en/EY-survey-Payroll-errors-average-$291-each-impacting-the-economy
- [CSRD] EY https://www.ey.com/en_gl/technical/csrd-technical-resources/eu-adopts-major-reforms-to-streamline-csrd-sustainability-report ; DLA Piper https://knowledge.dlapiper.com/dlapiperknowledge/globalemploymentlatestdevelopments/2026/corporate-sustainability-reporting-directive-amendments-under-omnibus-i-finalised ; CMS https://cms.law/en/lux/legal-updates/final-adoption-of-omnibus-i-directive-simplifying-csrd-and-csddd
- [Pillar2] EY https://www.ey.com/en_gl/insights/tax/why-pillar-two-compliance-demands-focus-as-major-filing-deadline-looms ; Revenue Ireland https://www.revenue.ie/en/companies-and-charities/pillar-two/dates/index.aspx ; KPMG https://kpmg.com/xx/en/our-insights/eu-tax/etf-579-oecd-clarifies-globe-information-return-central-filing.html
- [Brazil] Sovos https://sovos.com/taxapedia/?p=53 ; Edicom https://edicomgroup.com/blog/brazil-tax-reform ; ITR https://www.internationaltaxreview.com/article/2fplripsb35tzaek3i5mo/sponsored/brazils-consumption-tax-reform-enters-test-phase
- [MTD] GOV.UK MTD for Income Tax https://www.gov.uk/government/collections/making-tax-digital-for-income-tax ; ICAEW https://www.icaew.com/technical/tax/making-tax-digital/mtd-guidance/mtd-and-income-tax ; KPMG https://kpmg.com/uk/en/insights/tax/tmd-making-tax-digital-for-income-tax-is-now-live.html
- [Ramp / AP-search] Ramp https://ramp.com/blog/agentic-ai/agentic-ai-for-accounts-payable ; CPA Practice Advisor https://www.cpapracticeadvisor.com/?p=170422 ; G2 https://www.g2.com/compare/stampli-vs-vic-ai
- [BlueJ-survey] CPA Practice Advisor https://www.cpapracticeadvisor.com/2026/06/23/blue-j-and-cpa-com-survey-finds-ai-adoption-among-tax-firms-has-nearly-doubled-in-one-year/185545/ ; Thomson Reuters https://tax.thomsonreuters.com/blog/how-to-choose-the-best-ai-tax-research-tool/
- [India-IRN] Fonoa https://www.fonoa.com/resources/blog/india-imposes-a-new-time-limit-to-report-invoices-in-the-invoice-registration-portals ; ClearTax https://www.cleartax.in/s/e-invoicing-gst ; Tally https://tallysolutions.com/gst/e-invoicing-threshold/
- [ECCTA] Pinsent Masons https://www.pinsentmasons.com/out-law/news/uk-directors-spotlight-id-verification-deadline-looms ; Law Debenture https://www.lawdebenture.com/news-insights/millions-of-directors-still-unverified-the-17-november-deadline-is-closer-than-it-looks ; HSF Kramer https://www.hsfkramer.com/fr/notes/corporate/2026-posts/company-law-uk-government-publishes-updated-eccta-transition-plan
- [BlackLine] CPA Practice Advisor https://www.cpapracticeadvisor.com/2026/07/28/blackline-introduces-multi-agent-ai-system-verity-prepare/187516/ ; [FloQast] https://www.floqast.com/blog/the-next-evolution-of-accounting-ai-visual-agentic-and-built-by-you
- [CFDI] KPMG https://kpmg.com/us/en/taxnewsflash/news/2025/11/mexico-updates-electronic-invoicing-cfdi-2026-tax-reform.html ; VATupdate https://www.vatupdate.com/2026/03/17/sat-updates-cfdi-4-0-catalogs-march-2026-changes-affect-customs-records-no-schema-modifications/
- Late payment others (Xero, GoCardless ANZ): via search results, e.g. https://blog.xero.com/?p=38603

Caveat: most product names, regional systems and thresholds not tied to a bracketed source above are from memory and must be verified per country before a role's country pack ships. Many search summaries relied on vendor content; dates for Poland KSeF, UAE e-invoicing, Brazil split payment and several payroll rules conflict between sources.
