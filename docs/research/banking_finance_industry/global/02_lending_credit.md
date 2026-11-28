# Segment 02: Lending & Credit, worldwide. Every AI-employee role

Researched 22 Nov 2026. Some sources were opened this session (listed at the end, marked OPENED). Others were only read in search-result summaries (marked SEARCH). Anything marked "from memory - verify" was not checked this session.

## 0. How the segment is built

**Human jobs this list comes from.** The taxonomies are listed here. Codes are from memory unless marked; verify them.
- US BLS OOH "Loan Officers": about 283,000 jobs in 2025, median pay $76,690. Types are commercial, consumer and mortgage. Specialties are loan collection officers and loan underwriters. Duties: find borrowers, gather and verify financials, explain terms, check agreements for compliance, approve or refer (OPENED).
- O*NET 43-4131 Loan Interviewers and Clerks. Tasks: interview applicants, submit files with an underwriting recommendation, verify application and closing documents, record disbursements (OPENED).
- Other O*NET codes (from memory - verify): 13-2072 Loan Officers, 13-2041 Credit Analysts, 13-2053 Insurance Underwriters (an adjacent segment), 43-3011 Bill and Account Collectors, 43-4041 Credit Authorizers/Checkers/Clerks, 13-2099.04 Fraud Examiners, 23-2011 Paralegals (loan documentation).
- ISCO-08 (from memory - verify): 2412 Financial and investment advisers, 2413 Financial analysts (credit analyst), 3312 Credit and loans officers, 4214 Debt collectors, 4312 Statistical, finance and insurance clerks.
- ESCO carries the same occupations as ISCO, with extra entries such as "loan officer", "mortgage broker", "credit risk analyst", "debt collector" and "pawnbroker" (from memory - verify).
- UK SOC 2020 (from memory - verify): 3534 Finance and investment analysts and advisers, 4122 Book-keepers (adjacent), 7122 Debt, rent and other cash collectors, 3531 Estimators (no). UK "Mortgage adviser" is an FCA-regulated activity.
- ANZSCO (from memory - verify): 611211 Insurance Agent (no); 552211 Credit or Loans Officer; 591?? Debt collector. Verify the codes on abs.gov.au.
- Bank org charts commonly have these units: Retail Lending (Personal Loans, Cards, Mortgage, Auto), Business Banking / SME, Commercial & Corporate Banking, Leveraged & Syndicated Finance (origination, agency, portfolio), Project & Infrastructure Finance, Trade & Supply Chain Finance (TSCF), Credit Risk (underwriting, portfolio, EWS, model risk), Loan Operations / Loan Admin / Credit Admin (documentation, CP checking, disbursement, collateral), Collections & Recoveries, Restructuring / Workout / Special Situations, Securitisation / Structured Finance, Credit Bureau & Data, Lending Compliance (fair lending, consumer duty).

**Hard rule for every role below.** The AI never:
- approves or declines credit,
- sets a price or limit as a decision,
- disburses or moves money,
- reports to a credit bureau as the furnisher,
- files with a court or regulator as the institution,
- signs a security document or certificate,
- contacts a debtor outside the hours, channels and frequency the law allows.

A human always decides. For consumers, money moves only on the user's own tap, through official rails.

**Tiers.** A = admin or prepare, done for the user themselves. B = assists a named licensed or accountable human (credit officer, loan officer, underwriter, insolvency practitioner, solicitor, servicer compliance lead). C = never an AI employee; listed at the end.

**Shorthand for rails, used in every role.**
- **Bureaus:** Equifax / Experian / TransUnion (US, UK, Canada, AU, SA, LatAm); CRIF; Schufa (DE); CIBIL, CRIF High Mark, Equifax and Experian India (IN, under CICRA 2005); the PBOC Credit Reference Center and Baihang (CN); CIC and JICC (JP); KCB and NICE (KR); illion (AU); FirstCentral, CRC and CreditRegistry (NG); Metropol, TransUnion KE and Creditinfo (KE); Serasa and Boa Vista (BR); Buró de Crédito and Círculo (MX); the AECB (UAE); SIMAH (KSA).
- **Open banking / account data:** US CFPB 1033 (status in flux - check), UK Open Banking, EU PSD2/PSD3 and FIDA (proposed), India Account Aggregator (Sahamati), Brazil Open Finance, Australia CDR, Saudi Open Banking, UAE Open Finance, Nigeria Open Banking (CBN), Singapore SGFinDex, Japan e-API. Aggregators: Plaid, Finicity, MX, TrueLayer, Tink, Belvo, Finbox, Setu, Mono (Africa), Stitch.
- **Tax / income proof:** IRS IVES and the 4506-C; HMRC; India GSTN, ITR and AIS; Brazil e-CAC and Nota Fiscal; Mexico SAT CFDI.
- **Collateral and registries:** land registries (HMLR, Indian state registries, US county recorders), UCC filing (US), PPSR (AU/NZ), CERSAI (IN), the Companies House charges register (UK), ROC charge forms (IN), PPSA (CA).
- **Trade and markets:** SWIFT MT7xx / ISO 20022 tsmt / tsrv for trade; MERS (US mortgages); LSTA / LMA / APLMA documents; ClearPar (loan settlement); DTCC; ESMA securitisation repositories; EDW (European DataWarehouse).

---

## A. CONSUMER-SIDE ROLES (hired by the borrower, tier A)

### 1. Loan Shopper and Cost Explainer
Compares loan offers and shows their TRUE cost in plain words.
- **Who hires it:** consumers, sole traders.
- **Jobs:**
  - Read offer letters and Key Fact Statements (KFS).
  - Compute APR, total repayable and total interest.
  - Convert flat rates to reducing-balance rates.
  - Expose fees: processing, insurance bundling, prepayment.
  - Compare 2-5 offers side by side.
  - Flag add-ons pushed with the loan.
  - Draft questions to ask the lender.
  - Track how long an offer stays valid.
  - Check the lender's licence on the regulator register.
- **Tier A.** The borrower chooses.
- **Data:** offer PDFs; regulator registers (FCA register, RBI NBFC list, CBK DCP list, ASIC register, NMLS Consumer Access).
- **Regions:**
  - US: TILA / Reg Z APR.
  - EU: CCD2, the SECCI form, standardised APR; applies from 20 Nov 2026.
  - UK: CONC, Consumer Duty.
  - India: KFS / APR mandate; RBI Digital Lending Directions 2025 require the digital view of matching offers with APR (SEARCH).
  - Kenya: 252 licensed DCPs as of July 2026 (SEARCH).
  - Nigeria: FCCPC Digital Lending Regulation 2025 (SEARCH).
  - Brazil: CET (Custo Efetivo Total).
  - Mexico: CAT (Costo Anual Total).
  - Australia: comparison rate.
  - Japan: Money Lending Business Act, interest caps around 15-20% (from memory - verify).
- **Evidence it is doable:** NerdWallet, Credit Karma, BankBazaar, Paisabazaar, Compare the Market, Finder (from memory - verify).

### 2. Credit Report and Score Fixer
Reads the user's own credit reports, finds errors and drafts disputes.
- **Who hires it:** consumers, small businesses.
- **Jobs:**
  - Pull and read reports from every bureau (user-initiated).
  - Spot wrong accounts, duplicates, stale negatives, mixed files and identity-theft lines.
  - Draft dispute letters with evidence.
  - Track the 30-day (US FCRA) and other statutory deadlines.
  - Escalate to the regulator or ombudsman.
  - Explain score factors.
  - Plan utilisation and on-time habits.
  - Set fraud alerts and freezes (the user taps).
- **Tier A.**
- **Data:** bureau reports; the user's ID.
- **Regions:**
  - US: FCRA s.611 (30 days), AnnualCreditReport.com. CFPB counted ~6.6M complaints in 2025, ~88% about credit reporting (SEARCH).
  - UK: statutory report, ICO.
  - India: CICRA; RBI requires bureaus to fix errors within 30 days or pay compensation (from memory - verify).
  - Brazil: Cadastro Positivo.
  - China: PBOC CRC annual free report.
  - EU: GDPR Art. 16 rectification; Schufa.
- **Evidence of pain:** FTC 2013 study found 1 in 5 consumers had an error on at least one report and 5% had errors serious enough to raise costs (SEARCH: FTC press release).
- **Evidence it is doable:** Credit Karma, Experian Boost, Dovly, CreditSage (from memory - verify). Note that "credit repair" is regulated in the US (CROA); no upfront fees.

### 3. Debt Payoff Planner and Restructure Helper
Builds a payoff plan across all the user's debts and drafts hardship requests.
- **Who hires it:** consumers.
- **Jobs:**
  - Inventory every debt.
  - Snowball and avalanche plans.
  - Check whether consolidation actually saves money.
  - Prepay-versus-penalty maths.
  - Draft hardship, forbearance and restructuring requests to the lender.
  - Prepare for a debt-advice session.
  - Find free debt charities.
  - Monthly progress check.
- **Tier A.** Regulated debt advice stays with humans in the UK and similar markets (see C).
- **Regions:**
  - UK: free debt advice through MoneyHelper, StepChange; Breathing Space.
  - US: nonprofit credit counseling; NFCC.
  - Brazil: Desenrola. Serasa counted 80.6M people in default at end 2025 and 83.3M in April 2026 (SEARCH).
  - India: RBI resolution frameworks.
  - South Africa: debt review under the NCA.
  - Singapore: Credit Counselling Singapore.
- **Note:** Hoola already has `paisa_sahayak` covering much of this; extend it to global coverage.

### 4. Mortgage Buyer's Guide (borrower side)
Walks a home buyer from pre-approval to keys.
- **Who hires it:** consumers.
- **Jobs:**
  - Affordability and deposit maths.
  - Stamp duty and closing-cost estimate.
  - Document checklist.
  - Compare Loan Estimates or ESIS.
  - Fixed vs variable stress test.
  - Read the Closing Disclosure and spot changes.
  - Track deadlines: rate lock, appraisal, conditions, completion.
  - Remortgage reminders before a fix ends.
  - Draft questions for the broker or solicitor.
- **Tier A.**
- **Regions:**
  - US: TRID (Loan Estimate within 3 days, Closing Disclosure 3 days before close).
  - EU: Mortgage Credit Directive, ESIS.
  - UK: MCOB.
  - India: home-loan KFS; PMAY (check current status).
  - Australia: NCCP responsible lending; LMI.
  - Canada: OSFI B-20 stress test.
  - Gulf: UAE Central Bank LTV caps.
  - Japan: Flat 35.

### 5. Student Loan Navigator
Optimises repayment and finds relief programmes.
- **Who hires it:** students, graduates, parents.
- **Jobs:**
  - Inventory federal and private loans.
  - Compare repayment plans.
  - PSLF and forgiveness tracking.
  - Prepare consolidation and refinancing trade-offs.
  - Draft servicer complaints.
  - Track recertification dates.
  - Explain default and rehabilitation.
- **Tier A.**
- **Regions:**
  - US: FSA, IDR plans, a heavily changing legal situation (check). CFPB Private Education Loan Ombudsman reported record complaints in its Jan 2026 report (SEARCH).
  - UK: SLC plans 1/2/4/5, repayment through tax.
  - Australia: HELP via ATO.
  - India: Vidya Lakshmi portal, CSIS subsidy.
  - Canada: CSLP.
  - NZ: interest-free loans.

### 6. BNPL and Small-Credit Watchdog
Tracks every buy-now-pay-later and app loan so nothing is missed or stacked.
- **Who hires it:** consumers.
- **Jobs:**
  - Aggregate BNPL plans.
  - Due-date calendar.
  - Warn about stacking.
  - Check the provider is licensed.
  - Spot illegal loan apps: contact-list harvesting, harassment.
  - Draft complaints.
  - Explain late fees.
- **Tier A.**
- **Regions:**
  - UK: FCA regulates Deferred Payment Credit from 15 July 2026 (PS26/1), with affordability checks and FOS access (SEARCH).
  - Australia: BNPL in the NCC from 10 June 2025 as low-cost credit contracts; ASIC RG 281 (SEARCH).
  - EU: CCD2 brings most BNPL into scope from 20 Nov 2026 (SEARCH).
  - India: RBI Digital Lending Directions; the Sachet portal for illegal apps.
  - Kenya: CBK DCP licensing (252 by July 2026, SEARCH).
  - Nigeria: FCCPC registration.
  - Indonesia: OJK fintech lending rules (check).

### 7. Gold / Pawn Loan Assistant (borrower side)
Helps people borrowing against jewellery know their rights.
- **Who hires it:** consumers and micro-businesses (India, SE Asia, Middle East).
- **Jobs:**
  - LTV and maximum loan maths.
  - Check the purity and weight receipt.
  - Interest and bullet-repayment schedule.
  - Auction notice tracking.
  - Compare lenders.
  - Reminders ahead of the LTV breach and auction.
  - Release checklist.
- **Tier A.**
- **Regions:**
  - India: RBI Lending Against Gold and Silver Collateral Directions 2025. LTV is 85% up to ₹2.5 lakh, 80% from ₹2.5-5 lakh, 75% above. Compliance by 1 Apr 2026. Auction reserve price at least 90% of value (SEARCH, verify against the RBI text).
  - Singapore, HK, Thailand, Philippines: pawnbrokers' acts.
  - UK: pawnbroking under CONC.

### 8. Loan-Fraud and Scam Shield (borrower side)
Spots fake lenders, advance-fee scams and impersonation.
- **Who hires it:** consumers.
- **Jobs:**
  - Check lender identity against registers.
  - Advance-fee red flags.
  - Fake-recovery-agent detection.
  - Check whether a "loan approved" SMS or link is genuine (without opening it).
  - Report to the cyber or police portal.
- **Tier A.**
- **Note:** this overlaps the Hoola `paisa_sahayak` scam engine.

---

## B. SME / SOLE-TRADER SIDE (hired by the borrower firm, tier A)

### 9. Business Loan Readiness Assistant
Turns the books into a lender-ready credit pack.
- **Who hires it:** SMEs, sole traders, accountants.
- **Jobs:**
  - Build the 3-year financials and projections.
  - Debt-service coverage (DSCR) and leverage self-check.
  - Prepare the bank-statement analysis lenders run.
  - List collateral.
  - Draft the purpose memo.
  - Fill application forms.
  - Pick suitable products: term loan, overdraft, invoice finance, equipment, revenue-based financing.
  - Find government guarantee schemes.
  - Document checklist.
- **Tier A.**
- **Rails:** accounting APIs (QuickBooks, Xero, Tally, Zoho), open banking / AA, GST returns.
- **Regions:**
  - US: SBA 7(a) and 504 (via lenders).
  - UK: British Business Bank schemes (Growth Guarantee Scheme), Bank Referral Scheme.
  - EU: EIF guarantees.
  - India: CGTMSE, PSB59, Udyam, TReDS.
  - Brazil: Pronampe.
  - Mexico: NAFIN.
  - Kenya: Credit Guarantee Scheme.
  - Saudi: Kafalah.
  - Singapore: EFS.
  - Australia: SME Guarantee Scheme (check).
- **Evidence it is doable:** Lendio, Funding Circle marketplace, Indifi, Lendingkart (from memory - verify); QuickBooks lending tools exist (Intuit Capital tool surfaced in this environment).

### 10. Working-Capital and Invoice Finance Planner
Picks the cheapest way to fund a cash gap and runs the paperwork.
- **Who hires it:** SMEs.
- **Jobs:**
  - Forecast the cash gap.
  - Compare overdraft, factoring, reverse factoring and dynamic discounting by effective annual cost.
  - Prepare the invoice upload set.
  - Reconcile advances and fees.
  - Track recourse exposure.
  - Upload to TReDS or a platform on the user's tap.
- **Tier A.**
- **Regions:**
  - India: TReDS (RXIL, M1xchange, Invoicemart).
  - EU, UK: factoring associations; Late Payment Act.
  - China: supply-chain finance platforms.
  - Brazil: duplicatas escriturais.
  - Mexico: CFDI-based factoring.

### 11. Trade Finance Desk Assistant (exporter / importer side)
Prepares letter of credit (LC) and bank guarantee (BG) applications and shipping documents so the bank finds no discrepancies.
- **Who hires it:** SME importers and exporters, freight forwarders.
- **Jobs:**
  - Read the LC and list the conditions.
  - Build the document checklist: bill of lading, invoice, packing list, certificate of origin, insurance.
  - Pre-check documents against UCP 600 / ISBP 821.
  - Track presentation-period and expiry deadlines.
  - Draft LC amendment requests.
  - Draft BG text against URDG 758.
  - Prepare export-credit insurance applications.
  - Check sanctions-sensitive goods and ports (flag only).
- **Tier A.**
- **Evidence of pain:** ADB 2025 puts the trade-finance gap at about US$2.5tn, with SME rejection around 41% (SEARCH).
- **Regions:** UCP and URDG apply globally.
  - EXIM banks: US EXIM, UKEF, ECGC (IN), Sinosure.
  - Digital trade: the UK Electronic Trade Documents Act 2023, MLETR adopters (Singapore, Bahrain, UK, France, check others), India DGFT eBRC.

### 12. Equipment and Vehicle Finance Comparer (business)
Compares lease and loan for machinery and fleets.
- **Who hires it:** SMEs, fleet owners, farmers.
- **Jobs:**
  - Lease vs buy net present value.
  - Tax depreciation effect.
  - Residual value check.
  - Read the hire-purchase or lease agreement.
  - Insurance and maintenance cost.
  - Track the payment schedule.
  - End-of-lease options.
- **Tier A.**
- **Regions:** IFRS 16 for the lessee; US ASC 842; UK HP.

### 13. Microfinance Group Assistant (borrower / SHG side)
Keeps a self-help or joint-liability group's records straight.
- **Who hires it:** SHGs, JLGs, cooperatives, NGOs.
- **Jobs:**
  - Group meeting minutes.
  - Who-paid-what ledger.
  - Repayment reminders in local languages.
  - Explain loan terms.
  - Track each member's indebtedness against caps.
  - Grievance letters.
  - Literacy content.
- **Tier A.**
- **Regions:**
  - India: RBI MFI framework 2022 (household income cap, 50% FOIR), NRLM SHGs.
  - Bangladesh: MRA.
  - Kenya: chamas.
  - Philippines: CARD.
  - LatAm: Compartamos.
- **Evidence:** Global Findex 2025 found 24% of adults in low- and middle-income economies borrowed formally and 31% from family and friends (SEARCH).

### 14. Insolvency and Restructuring Helper (debtor SME side)
Prepares a distressed small company for talks with creditors.
- **Who hires it:** SMEs, sole traders, their accountants.
- **Jobs:**
  - Creditor list and statement of affairs draft.
  - Cash-flow under scenarios.
  - Draft the restructuring proposal.
  - Explain options: CVA, administration, pre-pack, IBC pre-pack, Chapter 11 Subchapter V, Chapter 13, recuperação judicial.
  - Deadline tracker.
  - Prepare for the meeting with the licensed practitioner.
- **Tier A** (prepare only). The practitioner and the court decide.
- **Regions:**
  - UK: IPs licensed by the RPBs; IVA; Breathing Space.
  - US: Chapter 7 / 11 / 13; Subchapter V.
  - India: IBC 2016, MSME pre-pack, IBBI-registered IPs.
  - EU: Restructuring Directive 2019/1023.
  - Singapore: IRDA 2018.
  - Brazil: Lei 11.101 recuperação judicial / extrajudicial.
  - Australia: small business restructuring.
  - South Africa: business rescue.

---

## C. LENDER-SIDE ROLES (hired by banks, NBFCs, credit unions, fintech lenders, brokers; mostly tier B)

### Origination and sales

### 15. Lead Qualifier and Pre-Screen Assistant
Answers prospects 24/7, checks basic eligibility and books the loan officer.
- **Who hires it:** lenders, brokers, DSAs.
- **Jobs:**
  - Answer product FAQs.
  - Soft eligibility questions (no hard pull without consent).
  - Pre-filled document checklist.
  - Book appointments.
  - Log to the CRM.
  - Consent capture for the bureau pull.
  - Compliance-safe scripts (no "you're approved").
- **Tier B** (the loan officer).
- **Regions:**
  - US: ECOA / Reg B (no discouragement), TCPA.
  - EU AI Act: credit scoring of individuals is high-risk under Annex III; a chatbot must disclose it is AI.
  - UK: Consumer Duty.
  - India: DSA conduct rules, Digital Lending Directions on LSPs.

### 16. Loan Application Intake Clerk
Turns the applicant's documents into a complete, verified file.
- **Who hires it:** lenders.
- **Jobs (the O*NET 43-4131 tasks):**
  - Collect, classify and extract documents: pay slips, tax returns, bank statements, ID, property papers.
  - Spot missing items.
  - Stare-and-compare names and dates.
  - Detect tampered PDFs (flag).
  - Enter data into the loan origination system (LOS).
  - Chase the borrower.
  - Submit the file with a recommendation summary.
- **Tier B.**
- **Rails:** IDP/OCR; LOS (Encompass, nCino, Finastra, FIS, Temenos, Newgen, Nucleus).
- **Evidence it is doable:** Ocrolus, Blend (DocAI, Autopilot agent live with lenders), Tavant TOUCHLESS (SEARCH).

### 17. Income and Employment Verification Assistant
Verifies income from direct sources and calculates qualifying income.
- **Jobs:**
  - Pull payroll and bank data (with consent).
  - Run the income calculation for salaried, self-employed and rental income using agency guides (Fannie Mae Form 1084).
  - Request IRS transcripts through IVES (the lender submits).
  - Verify GST and ITR (India).
  - Flag variance and gaps.
  - Write the worksheet.
- **Tier B.**
- **Regions:** US Fannie/Freddie day-1 certainty, Freddie AIM Check API (Ocrolus integration, SEARCH); India AA + GSTN + ITR; UK HMRC; Brazil Open Finance; Australia CDR.

### 18. Bank-Statement and Cash-Flow Analyst
Reads 6-24 months of statements and produces the cash-flow credit view.
- **Jobs:**
  - Categorise transactions.
  - Detect bounces, NSF, gambling, salary, existing EMIs and circular transactions.
  - Average balances.
  - DSCR from cash.
  - Seasonality.
  - Fraud markers.
  - Lender-ready summary.
- **Tier B.**
- **Evidence it is doable:** Ocrolus, Perfios, Finbox, Plaid, Validis (from memory - verify).

### 19. Mortgage Loan Processor
Runs the file from application to clear-to-close.
- **Jobs:**
  - Order appraisal, title, flood and insurance.
  - Track conditions.
  - Clear prior-to-doc conditions with evidence.
  - TRID timing watch.
  - Borrower updates.
  - Re-disclosure triggers.
  - Final pipeline report.
- **Tier B** (the processor and loan officer, NMLS-licensed where required).
- **Regions:**
  - US: TRID, RESPA, HMDA data, Fannie/Freddie selling guides, MERS.
  - UK: MCOB, conveyancer coordination.
  - Canada: CMHC insurance.
  - Australia: broker best-interests duty.
- **Evidence it is doable:** Blend Autopilot, Tavant, Ocrolus automated conditioning (SEARCH), Better.com "Betsy" (from memory - verify).

### 20. Underwriting Assistant (consumer and mortgage)
Prepares the underwriting decision package. It never decides.
- **Jobs:**
  - Run the policy checklist: DTI, LTV, credit score floors, reserves.
  - Run or read the automated underwriting system (AUS: DU / LPA) findings.
  - List exceptions with mitigants.
  - Check document consistency.
  - Draft the underwriter's notes.
  - Prepare adverse-action reason codes (the underwriter confirms).
  - Fair-lending consistency check.
- **Tier B** (the licensed or authorised underwriter).
- **Regions:**
  - US: ECOA adverse-action specificity (the CFPB said "complex algorithms" are no excuse; Circular 2022-03, from memory - verify).
  - EU: CCD2 right to human intervention and explanation for automated credit decisions; EBA Loan Origination and Monitoring Guidelines (EBA/GL/2020/06); AI Act high-risk.
  - UK: FCA Consumer Duty, CONC 5.2A creditworthiness.
  - India: RBI model governance.

### 21. SME / Commercial Credit Analyst (spreading and credit memo)
Spreads financials and drafts the credit memo with every number traced to its source.
- **Jobs:**
  - Spread statements.
  - Ratio and trend analysis.
  - Peer benchmark.
  - Cash-flow projections and sensitivity.
  - Collateral and guarantor analysis.
  - Draft the risk rating rationale (the rating is proposed, not set).
  - Draft the credit memo.
  - Draft the term sheet.
  - Review notes for the credit committee.
- **Tier B** (the credit officer and committee).
- **Evidence it is doable:** Moody's and S&P Global credit-memo AI; Evalueserve; Aloan (memo plus covenant monitoring, every number cited); EnFi; Uptiq claims 70% time cut (all SEARCH, vendor claims).
- **Regions:** Basel III/IV IRB vs standardised; EBA LOM; RBI.

### 22. Corporate / Leveraged Loan Credit Analyst
The large-corporate version: EBITDA adjustments, leverage and recovery analysis.
- **Jobs:**
  - Build the quality-of-earnings adjustment table.
  - Leverage and interest-cover cases.
  - Recovery waterfall.
  - Industry and peer analysis.
  - Rating-agency report summary.
  - Comparison of documentation terms against market (covenant-lite flags).
  - Committee pack.
- **Tier B.**
- **Regions:** US leveraged lending guidance (status check); ECB leveraged transactions guidance; LMA / LSTA / APLMA.

### 23. Pricing and Profitability Calculator (RAROC)
Computes the price a deal needs; the human sets the price.
- **Jobs:**
  - Funding cost plus expected loss, capital charge and operating cost.
  - RAROC / EVA.
  - Relationship profitability.
  - Price-exception memo.
  - Check against the rate book.
  - Benchmark conversions: SOFR, SONIA, €STR, MCLR / EBLR, CDI (BR), TIIE (MX).
- **Tier B.**

### 24. Broker Panel and Product Matcher (for brokers)
Finds the lenders whose criteria fit a client.
- **Who hires it:** mortgage and commercial brokers.
- **Jobs:**
  - Search lender criteria.
  - Affordability by lender.
  - Draft the suitability report.
  - Fact-find capture.
  - Commission disclosure.
  - Submission pack per lender.
  - Rate-switch reminders for the client book.
- **Tier B** (the regulated adviser signs).
- **Regions:**
  - UK: mortgage advice under MCOB; the suitability letter is the adviser's.
  - Australia: best-interests duty (NCCP Pt 3-5A).
  - Canada: provincial mortgage-broker licensing.
  - US: NMLS / SAFE Act.

### 25. Digital Lending Journey and Disclosure Checker
Makes sure every app-loan journey shows the right disclosures in the right order.
- **Who hires it:** fintech lenders, banks, LSPs.
- **Jobs:**
  - Map screens to rules.
  - Check the KFS / APR shown before signing.
  - Cooling-off and look-up periods.
  - Consent screens.
  - Data-minimisation check (no contacts or gallery access).
  - Grievance-officer display.
  - Archive evidence.
- **Tier B** (the compliance officer).
- **Regions:**
  - India: Digital Lending Directions 2025; multi-lender LSP offer display since 1 Nov 2025 (SEARCH).
  - Indonesia: OJK.
  - Nigeria: FCCPC.
  - Kenya: CBK.
  - UK: DPC rules.
  - EU: CCD2 pre-contract information; Distance Marketing (now folded into the CRD).

### Underwriting data and decision support

### 26. Credit Bureau Report Reader and Bureau Ops Clerk
Reads bureau files for a lender and handles the lender's bureau data duties.
- **Jobs:**
  - Summarise the bureau file.
  - Detect thin-file and new-to-credit borrowers.
  - Prepare the monthly furnishing file and check it (Metro 2 / CICRA format).
  - Reconcile rejects.
  - Process consumer disputes within deadlines (e-OSCAR in the US).
  - Draft dispute responses.
- **Tier B.** The furnisher is accountable for what it reports.
- **Regions:**
  - US: FCRA furnisher duties.
  - India: CIC data submission (the RBI moved to fortnightly reporting in 2025, from memory - verify).
  - EU: GDPR.
  - China: PBOC CRC / Baihang.
  - Brazil: Cadastro Positivo.

### 27. Alternative-Data and Thin-File Credit Assistant
Builds evidence for people with no bureau history.
- **Jobs:**
  - Cash-flow underwriting from open banking.
  - Utility, rent and telecom payments.
  - Psychometric or other alternative data (with caution).
  - Explainability notes.
  - Bias check across protected groups.
  - Consent log.
- **Tier B.**
- **Regions:**
  - US: ECOA disparate impact.
  - EU AI Act high-risk; GDPR Art. 22.
  - India AA; Kenya mobile money (M-Pesa Fuliza); Nigeria Mono.
  - China: Sesame Credit history (regulated narrowly now, check).
- **Evidence it is doable:** Zest AI, Upstart, Nova Credit, Petal (acquired), Tala, Branch (from memory - verify).

### 28. Scorecard and Credit Model Documentation Assistant
Documents and monitors credit models for model risk management.
- **Jobs:**
  - Draft the model development document.
  - Population stability (PSI) and characteristic analysis.
  - Gini / KS drift reports.
  - Override analysis.
  - Validation-finding tracker.
  - Fair-lending testing write-ups.
  - AI Act technical documentation.
- **Tier B** (the model owner, validator and MRM committee).
- **Regions:** US SR 11-7 / OCC 2011-12; UK PRA SS1/23; ECB TRIM / IRB; EU AI Act Annex IV; RBI model risk guidance (check); HKMA; MAS FEAT principles.

### 29. Fraud and First-Party Default Screener (application fraud)
Flags synthetic identities, document fraud and loan stacking for human review.
- **Jobs:**
  - Device and identity consistency.
  - Document tampering checks.
  - Velocity and stacking signals.
  - Mule account indicators.
  - Case notes.
  - Feedback loop on confirmed fraud.
- **Tier B.** Fraud analysts decide; the AI never blocks a customer on its own.
- **Regions:** UK Cifas, National Hunter; US consortium data; India CIBIL and CKYCR; Brazil Serasa anti-fraud.

### 30. Fair-Lending and Responsible-Lending Monitor
Tests decisions and pricing for discrimination and affordability failures.
- **Jobs:**
  - Disparity analysis on approval, pricing and limit.
  - Redlining maps.
  - Prepare HMDA / CRA data.
  - Sample affordability checks against policy.
  - Consumer Duty outcome monitoring.
  - Draft the board report.
- **Tier B** (the compliance officer).
- **Regions:** US ECOA, FHA, HMDA, CRA; UK Consumer Duty; EU CCD2, AI Act; Australia NCCP RG 209.

### Closing, documentation and loan operations

### 31. Loan Documentation and Conditions-Precedent (CP) Checker
Checks the signed facility pack and every CP before the money is released.
- **Jobs:**
  - Build the CP checklist from the facility agreement.
  - Tick each item off against documents.
  - Spot unsigned or undated pages.
  - Check board resolutions and authorities.
  - Check legal-opinion coverage.
  - Draft the CP satisfaction memo for the human.
  - Track conditions subsequent.
- **Tier B** (credit admin and the lawyer).
- **Regions:** LMA / LSTA / APLMA templates; India CERSAI, ROC CHG-1, stamp duty by state; UK Companies House 21-day charge registration; US UCC-1.

### 32. Security and Collateral Registration Tracker
Makes sure every charge, lien and mortgage is registered on time and stays perfected.
- **Jobs:**
  - Registration-deadline calendar.
  - Prepare the filing forms for human submission.
  - Check registry search results.
  - UCC continuation 5-year reminders.
  - Insurance endorsement tracking.
  - Valuation refresh dates.
  - Release and satisfaction on payoff.
- **Tier B.**
- **Regions:** US UCC / county recorder; UK Companies House + HMLR; India CERSAI + ROC + sub-registrar; Australia / NZ PPSR; Canada PPSA; Singapore ACRA; HK Companies Registry; UAE / KSA movable-collateral registries (check).

### 33. Disbursement Prep Clerk
Assembles the disbursement instruction and its checks; a human releases the funds.
- **Jobs:**
  - Check that CPs are met.
  - Compute net disbursement: fees, insurance, existing loan payoff.
  - Check the beneficiary account name (for example confirmation of payee).
  - Tranche schedule against milestones (construction).
  - Prepare the payment file (ISO 20022 pain.001) for maker-checker.
  - Post-disbursement checklist.
- **Tier B.** It never releases funds.
- **Regions:** UK CoP; EU Verification of Payee (Instant Payments Regulation, from Oct 2025); India PFMS / escrow under Digital Lending Directions (disbursement straight to the borrower); Brazil Pix.

### 34. Loan Boarding and Core-System Data Quality Clerk
Gets a new loan into the core banking system correctly.
- **Jobs:**
  - Map terms to system fields.
  - Check the repayment schedule against the agreement.
  - Rate reset and benchmark setup.
  - Fee setup.
  - Reconcile the boarding error report.
  - Data-quality exceptions.
- **Tier B.**

### 35. Mortgage Closing and Post-Closing QC Assistant
Checks closing packages and readies loans for sale or securitisation.
- **Jobs:**
  - Closing-package completeness.
  - TRID tolerance check.
  - Recording follow-up.
  - Trailing documents (final title policy, recorded deed).
  - Post-closing QC sampling against agency guidelines.
  - Defect taxonomy reports.
  - Investor delivery checklist.
- **Tier B.**
- **Regions:** US Fannie/Freddie QC requirements, MERS; UK conveyancing completion; Australia PEXA e-settlement.

### Servicing

### 36. Loan Servicing Customer Assistant
Answers borrowers about their own loan. It never changes the loan by itself.
- **Jobs:**
  - Balance and payoff quotes (from the system).
  - Statement explanation.
  - Escrow analysis explanation.
  - Rate-reset notices.
  - Change requests prepared for a human: address, due date.
  - Prepayment calculations.
  - Interest certificates (India 24(b) and 80C).
  - Complaint intake.
- **Tier B.**
- **Regions:** US RESPA / Reg X servicing rules (error resolution within 30 business days, from memory - verify); UK MCOB 13; India RBI fair practices (property papers returned within 30 days of closure or compensation of ₹5,000 a day, from memory - verify); EU MCD.

### 37. Escrow, Tax and Insurance Monitor
Watches that taxes and insurance on mortgaged property are paid and in force.
- **Jobs:**
  - Escrow analysis.
  - Shortage and surplus maths.
  - Tax-bill tracking.
  - Insurance lapse detection.
  - Force-placed insurance notice drafts (Reg X timing).
  - Flood zone changes.
- **Tier B.**

### 38. Payment Allocation and Reconciliation Clerk
Matches every borrower payment and fixes misapplied ones.
- **Jobs:**
  - Match incoming payments: NACH / ACH / direct debit / Pix / UPI AutoPay.
  - Unapplied cash queue.
  - Bounce and return handling (draft).
  - Fee reversals proposed.
  - Suspense ageing.
  - Daily reconciliation report.
- **Tier B.**
- **Regions:** India NACH / e-mandate bounce rules; US NACHA return codes; EU SEPA Direct Debit R-transactions; Brazil Pix Automático (2025).

### 39. Rate, Index and Benchmark Transition Clerk
Applies rate changes and benchmark resets correctly across a book.
- **Jobs:**
  - Find the rate-reset dates.
  - Fetch published benchmarks (SOFR, SONIA, EURIBOR, MCLR / repo, TIIE, CDI, HIBOR).
  - Compute new instalments and tenor.
  - Draft borrower notices.
  - Reconcile system results against the calculation.
  - EMI / tenor choice letters (India RBI 2023 floating-rate reset rule, from memory - verify).
- **Tier B.**

### 40. Loss Mitigation and Hardship Case Preparer
Builds complete hardship and modification files so servicers can decide fast.
- **Jobs:**
  - Collect the hardship application.
  - Income and expense analysis.
  - Run the waterfall: forbearance, modification, partial claim.
  - Prepare the net present value test.
  - Track deadlines (US Reg X 1024.41 loss-mitigation timelines).
  - Draft the decision letter for the human.
  - Track the trial period.
- **Tier B.**
- **Regions:** US Reg X, FHA / VA / GSE workouts; UK MCOB 13 / CONC 7 forbearance (FG24/2 tailored support, from memory - verify); India restructuring under RBI frameworks; EU NPL Directive (2021/2167) servicer rules.

### 41. Credit Card Account Servicing and Dispute Assistant (issuer side)
Handles cardholder questions, disputes and chargeback prep for the issuer.
- **Jobs:**
  - Statement and fee explanation.
  - Billing-error dispute intake and evidence.
  - Chargeback reason-code mapping (Visa / Mastercard rules).
  - Track statutory deadlines.
  - Draft provisional credit decisions for the human.
  - Limit-increase request prep.
  - Minimum-payment warnings.
- **Tier B.**
- **Regions:**
  - US: Reg Z FCBA (60-day notice, two cycles / 90 days to resolve); CARD Act.
  - UK: s.75 CCA.
  - EU: PSD2 unauthorised refunds.
  - India: RBI Credit Card Master Direction 2022 (billing disputes, closure within 7 days, from memory - verify).
  - Australia: ePayments Code.
  - Brazil: revolving-interest cap at 100% (Lei 14.690/2023, from memory - verify).

### 42. Card Portfolio Ops and Persistent-Debt Monitor
Watches card accounts for persistent debt and unaffordable limit growth.
- **Jobs:**
  - Find customers stuck on minimum payments (UK CONC 6.7 persistent debt, 18 / 27 / 36 months).
  - Draft repay-faster letters.
  - Limit-increase affordability recheck.
  - Promo-rate expiry notices.
  - Dormant-account rules.
  - Reward-liability reports.
- **Tier B.**

### 43. Auto Finance Servicing and Title / Lien Clerk
Runs auto loans and leases after funding.
- **Jobs:**
  - Lien and title perfection tracking (US state DMVs; India RTO hypothecation via Vahan).
  - Insurance tracking.
  - GAP and add-on refund calculation on early payoff.
  - Lease-end inspection scheduling.
  - Repossession-avoidance outreach (compliant).
  - Payoff letters.
- **Tier B.**
- **Regions:**
  - UK: motor finance commission redress scheme, FCA 2025-2026 (check status).
  - US: CFPB auto supervision.
  - India: hypothecation removal through Vahan.

### Collections and recovery (ethical only)

### 44. Early-Stage Collections Assistant (reminders and promise-to-pay)
Sends lawful reminders and records promises, in the borrower's language, within the rules.
- **Jobs:**
  - Pre-due and early-delinquency reminders within permitted channels, hours and frequency.
  - Capture promises to pay.
  - Payment-link delivery (the borrower taps).
  - Hardship triage handed to a human.
  - Vulnerability flags.
  - Call or message summaries.
  - Do-not-contact handling.
- **Tier B** (the collections manager owns policy and authority limits).
- **Evidence it is doable:** Prodigal proAgent (live with 25+ lenders, agencies and debt buyers); Skit.ai voice; Kompato; Credgenics (India, from memory - verify) (SEARCH).
- **Regions:**
  - US: FDCPA / Reg F (7-in-7 call cap, validation notice), TCPA. CFPB reportedly saw ~387k debt-collection complaints in 2025 vs ~207.8k in 2024 (SEARCH, verify).
  - UK: CONC 7, Consumer Duty, vulnerable-customer guidance.
  - India: RBI recovery-agent rules (no calls before 8am or after 7pm, no harassment).
  - EU: NPL Directive.
  - Brazil: CDC art. 42 (no embarrassment).
  - China: harassment bans.
  - Kenya / Nigeria: digital-lender harassment crackdowns.

### 45. Collections Strategy and Segmentation Analyst
Designs who gets what treatment, when; a human approves.
- **Jobs:**
  - Roll-rate and cure-rate analysis.
  - Segment by risk and contactability.
  - Champion / challenger design.
  - Settlement-offer bands proposed.
  - Agency allocation analysis.
  - Cost-to-collect.
  - Complaint-driver analysis.
- **Tier B.**

### 46. Collections QA and Conduct Monitor
Reviews every collections contact for law and fairness.
- **Jobs:**
  - Review transcripts against FDCPA / CONC / RBI rules.
  - Spot threats, misrepresentation and time-bar errors.
  - Vulnerability handling review.
  - Agency audit packs.
  - Complaint root cause.
  - Remediation lists.
- **Tier B.**

### 47. Debt Settlement and Recovery Negotiation Preparer
Prepares settlement proposals within authority limits a human set.
- **Jobs:**
  - Net-recovery maths: settle vs litigate vs sell.
  - Offer letters within the matrix.
  - Payment-plan schedules.
  - Credit-reporting outcome explanation.
  - Closure and no-dues letters.
  - Tax-on-forgiveness notes (US 1099-C).
- **Tier B.**

### 48. Legal Recovery and Enforcement Paralegal
Prepares enforcement paperwork for the lender's lawyer.
- **Jobs:**
  - Limitation-period tracker.
  - Demand and default notices.
  - Draft the case chronology.
  - Evidence bundle.
  - Track hearings.
  - Execution and attachment steps listed.
- **Tier B** (the advocate / solicitor files).
- **Regions:**
  - India: SARFAESI s.13(2) 60-day notice and s.13(4) possession; DRT filing; s.138 NI Act cheque bounce; Lok Adalat.
  - UK: CCA default notices (s.87), CCJs, pre-action protocol for debt claims.
  - US: state foreclosure (judicial vs non-judicial), FDCPA litigation rules.
  - Brazil: execução extrajudicial; alienação fiduciária (Lei 14.711/2023, from memory - verify).
  - China: notarised enforcement.

### 49. Repossession and Collateral Disposal Coordinator
Plans lawful repossession and fair-value sale of collateral.
- **Jobs:**
  - Notice timeline (lawful steps only).
  - Inventory and condition record.
  - Valuation orders.
  - Auction notice drafting with the reserve price.
  - Surplus or deficiency calculation.
  - Borrower redemption notices.
- **Tier B.**
- **Regions:** US UCC Article 9 commercially reasonable sale; India SARFAESI auctions and the RBI gold-auction reserve-price rule (SEARCH); UK HP repossession rules (one-third rule, CCA s.90).

### 50. Debt Sale and Portfolio Transfer Data Room Clerk
Prepares NPL portfolios for sale or transfer.
- **Jobs:**
  - Loan-level data tape cleaning.
  - Document availability index.
  - Borrower-notice drafting.
  - Exclusions for vulnerable, deceased and disputed accounts.
  - Buyer Q&A log.
  - Post-sale reconciliation.
- **Tier B.**
- **Regions:** EU NPL Directive data templates (EBA); India RBI ARC rules and the 2021 transfer-of-loan-exposures directions; US debt-buyer rules (state licensing).

### Credit risk, monitoring and portfolio

### 51. Early-Warning Signals (EWS) Analyst
Watches borrowers for signs of trouble and opens review cases for humans.
- **Jobs:**
  - Monitor account conduct: overdrafts, limit utilisation, bounces.
  - News and litigation alerts.
  - GST / tax filing gaps.
  - Rating changes.
  - Supplier and buyer concentration.
  - Draft watch-list memos.
  - Track action plans.
- **Tier B.**
- **Regions:** India RBI SMA-0/1/2 classification and the fraud / red-flagged account framework (2024 Master Direction, from memory - verify); EU EBA LOM monitoring; ECB NPL guidance; US interagency guidance.

### 52. Covenant Compliance Monitor
Reads loan agreements, tracks every covenant and tests the borrower's figures.
- **Jobs:**
  - Extract financial, information and negative covenants.
  - Calendar for compliance certificates and statements.
  - Recompute ratios from delivered financials using the agreement's definitions.
  - Flag breaches and headroom.
  - Draft waiver and amendment request memos.
  - Chase overdue reporting.
- **Tier B** (the relationship manager and credit officer decide breach consequences).
- **Evidence it is doable:** Aloan and EnFi (covenant monitoring), Covenant IQ (SEARCH); Hypercore, Cardo AI, 9fin (from memory - verify).

### 53. Annual Review and Renewal Pack Builder
Prepares the yearly credit review for every facility.
- **Jobs:**
  - Refresh spreads.
  - Conduct summary.
  - Collateral value refresh.
  - Covenant history.
  - Rating update proposal.
  - Draft the review memo.
  - Renewal term sheet.
  - Calendar of reviews due.
- **Tier B.**

### 54. Provisioning and ECL Calculator
Runs expected-credit-loss and NPA calculations for the finance and risk teams.
- **Jobs:**
  - Stage 1/2/3 classification proposal (significant increase in credit risk tests).
  - Inputs: PD, LGD, EAD.
  - Macro scenario weighting.
  - Management overlay documentation.
  - Reconcile to the general ledger (GL).
  - Disclosure notes draft.
  - India IRAC NPA ageing (90 DPD) and the 2027 ECL transition (check).
- **Tier B** (the CFO / CRO sign; auditors opine).
- **Regions:** IFRS 9; US CECL (ASC 326); India IRAC to ECL; Japan JGAAP (check); China CAS 22.

### 55. Credit Portfolio Analyst and Concentration Monitor
Reports what the loan book looks like and where it is risky.
- **Jobs:**
  - Concentration by sector, name and geography.
  - Vintage curves.
  - Limits against appetite.
  - Stress tests.
  - Large-exposure checks.
  - Climate and transition-risk overlay.
  - Board MI pack.
- **Tier B.**
- **Regions:** Basel large exposures; ECB / EBA stress tests; US CCAR / DFAST; RBI large exposures framework; climate (ECB guide, PRA SS3/19).

### 56. Regulatory Credit Reporting Preparer (lending returns)
Prepares lending-related regulatory returns for the institution's human filer.
- **Jobs:**
  - Map loan data to return templates (FR Y-14, AnaCredit, COREP credit risk, RBI CRILC, central-bank credit registers).
  - Validation rules.
  - Reconciliation to GL.
  - Variance commentary.
  - Submission calendar.
  - Resubmission tracker.
- **Tier B.** The institution files.
- **Regions:** EU AnaCredit; US FR Y-14 / Call Report RC-C; India CRILC / XBRL; UK BoE returns; Brazil SCR (BCB); China PBOC.

### 57. Loan Review / Credit Audit Assistant (second and third line)
Samples files and tests whether policy was followed.
- **Jobs:**
  - Risk-based sampling.
  - Test policy, delegation authority and exceptions.
  - Rating accuracy tests.
  - Documentation gaps.
  - Draft findings.
  - Issue tracker.
  - Trend report to the audit committee.
- **Tier B** (the auditor concludes).

### Corporate, syndicated, project and structured

### 58. Syndicated Loan Agency Assistant
Runs the agent bank's admin work for a syndicate.
- **Jobs:**
  - Notices: utilisation, interest period, rate fixing.
  - Interest and fee calculations per lender share.
  - Lender distribution lists.
  - Amendment consent tracking (majority / all-lender thresholds).
  - KYC refresh reminders.
  - Information-undertaking chasing.
- **Tier B.** The agent's ops staff release payments.
- **Rails:** LMA / LSTA agreements; Debtdomain / Intralinks; Loan IQ.

### 59. Loan Trading and Settlement Clerk
Speeds up secondary-loan trade settlement.
- **Jobs:**
  - Trade confirmation check.
  - Assignment-agreement prep.
  - Consent-request tracking (borrower / agent).
  - Funding-memo calculation.
  - Delayed-compensation maths.
  - KYC packet assembly.
  - Settlement-break list.
- **Tier B.**
- **Evidence of pain:** the LSTA par market averaged ~19.5 days to settle in 2023 and ~15-18 days in early 2024 against the T+7 benchmark (SEARCH: S&P / ClearPar).

### 60. Project Finance Analyst Assistant
Builds and checks project-finance models and monitors construction and operations.
- **Jobs:**
  - Model review: CFADS, DSCR, LLCR, sculpting.
  - Sensitivity cases.
  - Drawdown request checks against the construction budget and independent engineer certificates.
  - Reserve accounts (DSRA, MRA) tracking.
  - Equator Principles environmental and social action-plan tracking.
  - Lender reporting.
- **Tier B.**
- **Regions:** Equator Principles 4; IFC Performance Standards; ECA cover; India NIP / RBI project-finance directions 2025 (from memory - verify); GCC PPP laws.

### 61. Trade Finance Operations Assistant (bank side)
Examines LC and collection documents and prepares the checker's work.
- **Jobs:**
  - Read the MT700 / ISO 20022.
  - Extract document data.
  - Check documents against UCP 600 / ISBP 821 and list discrepancies.
  - Draft the discrepancy notice (the human sends within 5 banking days, UCP Art. 14b / 16).
  - Sanctions and dual-use screening flags.
  - Track presentations.
  - Draft BG issuance.
  - Track claims.
- **Tier B** (the trade checker and sanctions officer decide).
- **Evidence it is doable:** Traydstream; Conpend / Finastra TradeAI (claims checking time cut from 2 days to 10 minutes); HSBC in-house AI doc checking (SEARCH).

### 62. Supply-Chain Finance Programme Analyst
Runs a buyer-led SCF / reverse-factoring programme's onboarding and data.
- **Jobs:**
  - Supplier onboarding packs.
  - Invoice approval file checks.
  - Limit utilisation.
  - Dilution and duplicate-invoice detection.
  - Payables-extension disclosure (IFRS IAS 7 / IFRS 7 supplier-finance disclosures, 2024).
  - Programme reporting.
- **Tier B.**

### 63. Securitisation Operations and Investor Reporting Analyst
Prepares loan tapes and investor reports for securitised pools.
- **Jobs:**
  - Loan-level data template filling (ESMA Annex templates, Reg AB II asset-level data).
  - Eligibility criteria testing.
  - Waterfall and trigger calculations.
  - Servicer report reconciliation.
  - Repurchase (breach) tracking.
  - STS notification support.
- **Tier B** (the issuer / servicer certifies).
- **Regions:** EU Securitisation Regulation 2017/2402 (review under way, check); UK SR 2024; US Reg AB II and risk retention; India RBI securitisation directions 2021; China ABS (CSRC / NAFMII); Japan JFSA.

### 64. Co-Lending and Loan Participation Coordinator
Keeps two or more lenders' shares of the same loan reconciled.
- **Jobs:**
  - Loan-wise split ledgers.
  - Blended-rate calculation.
  - Sweep reconciliation of collections between partners.
  - Default-loss-guarantee (DLG) limit tracking.
  - Partner MIS.
  - Asset-classification sync.
  - Participation-certificate records (US).
- **Tier B.**
- **Regions:** India RBI Co-Lending Arrangements Directions 2025 (in force 1 Jan 2026; blended rate, each lender maintains its own share; DLG up to 5% per secondary source, verify) (SEARCH); US loan participations (bank–fintech partnerships, OCC "true lender" history, check); EU / UK sub-participations.

### 65. Restructuring and Workout Analyst (lender side)
Prepares the lender's view in a workout or insolvency.
- **Jobs:**
  - Liquidity runway.
  - Restructuring options and recovery comparison.
  - Proof-of-claim prep.
  - Inter-creditor and waterfall analysis.
  - Creditor-committee materials.
  - Resolution-plan evaluation matrix (IBC).
  - Track milestones.
- **Tier B** (the workout officer and committee; licensed IPs / courts).
- **Regions:** India IBC (CoC voting, 330-day limit), RBI Prudential Framework (ICA, 2019); US Chapter 11; UK Part 26A restructuring plans; Singapore IRDA; EU Directive 2019/1023; Brazil RJ.

### 66. Insolvency Practitioner's Assistant
Supports a licensed IP / trustee / RP with admin work.
- **Jobs:**
  - Creditor claim intake and verification worksheets.
  - Statutory notice calendar.
  - Asset register.
  - Draft reports to creditors.
  - Meeting minutes.
  - Distribution calculations (the IP approves).
  - Regulatory filing prep (IBBI forms, UK Insolvency (E&W) Rules).
- **Tier B** (the IP signs).

### 67. Sovereign, Development and Microfinance Institution Credit Officer Aide
Supports MFIs, development banks and NGOs lending to the poor.
- **Jobs:**
  - Field-visit report prep in local language.
  - Household income assessment template.
  - Over-indebtedness checks across lenders via the bureau.
  - Group meeting attendance and repayment registers.
  - Social performance (SPI4) reporting.
  - Donor reporting.
- **Tier B.**
- **Regions:** India RBI MFI 2022 framework; Bangladesh MRA; Kenya MFB Act; Philippines BSP / MFI NGOs; Mexico CNBV SOFIPOs; Cerise SPI4; Smart Campaign / Client Protection (now under Cerise+SPTF).

### 68. Credit Union and Cooperative Lending Assistant
Runs member lending admin for small lenders with tiny teams.
- **Jobs:**
  - Member application intake.
  - Share-secured loan calculations.
  - Delinquency lists.
  - Board loan committee packs.
  - Regulatory ratio checks (NCUA, PRA credit unions, RBI / NABARD co-ops).
  - Member communications.
- **Tier B.**

### 69. Pawnbroker / Gold-Loan Branch Assistant (lender side)
Back-office for gold-loan and pawn branches.
- **Jobs:**
  - Valuation worksheet from assayer inputs.
  - LTV computation by tier.
  - Loan ticket and KFS prep.
  - Interest accrual.
  - LTV-breach notices.
  - Auction compliance file (reserve price, notice).
  - Release reconciliation.
- **Tier B.**
- **Regions:** India RBI 2025 gold directions (SEARCH); Singapore Pawnbrokers Act; UK CONC.

### 70. BNPL Provider Operations and Affordability Assistant
Runs the new regulated-BNPL obligations for providers.
- **Jobs:**
  - Proportionate affordability checks (data prep).
  - Pre-contract information.
  - Bureau furnishing setup.
  - Arrears-handling scripts.
  - FOS / AFCA complaint files.
  - Consumer Duty outcome MI.
  - Merchant-partner monitoring.
- **Tier B.**
- **Regions:** UK DPC from 15 July 2026; AU from 10 June 2025; EU CCD2 from 20 Nov 2026; US state-level (NY BNPL licensing law 2025, from memory - verify) (SEARCH for UK, AU, EU).

### 71. Lending Complaints and Ombudsman Case Handler
Investigates lending complaints and drafts responses within deadlines.
- **Jobs:**
  - Triage.
  - Pull the account history.
  - Root cause.
  - Redress calculation proposal.
  - Final response letter draft within the deadline (UK 8 weeks DISP; India RBI Integrated Ombudsman 30 days; AU AFCA IDR 30 days; US CFPB portal 15 / 60 days).
  - Ombudsman file prep.
- **Tier B.**
- **Evidence:** CFPB 6.6M complaints in 2025 (SEARCH).

### 72. Lending Policy and Product Documentation Writer
Keeps credit policy, product notes and procedures current and consistent.
- **Jobs:**
  - Draft policy updates when rules change.
  - Map clauses to regulations.
  - Delegation-of-authority matrices.
  - Procedure manuals.
  - Change logs.
  - Training quizzes.
- **Tier B** (the board / credit committee approves).

### 73. Regulatory Change Tracker for Lending
Turns new lending rules worldwide into impact lists.
- **Jobs:**
  - Watch regulator publications: CFPB, OCC, FCA, PRA, EBA, ECB, RBI, MAS, HKMA, CBUAE, SAMA, CBN, CBK, SARB, BCB, CNBV, APRA / ASIC, OSFI, FSA Japan, FSC Korea, NFRA China.
  - Summarise each change.
  - Gap-analysis template.
  - Implementation-date calendar: CCD2 20 Nov 2026, UK DPC 15 Jul 2026, India Co-Lending 1 Jan 2026, India gold directions 1 Apr 2026 (SEARCH).
- **Tier B.**

### 74. Lending KYC and Onboarding Prep Assistant
Prepares customer-due-diligence files for loan customers; a human approves KYC.
- **Jobs:**
  - Collect and check documents.
  - Beneficial-ownership trees for business borrowers.
  - Screening-hit summaries.
  - Re-KYC schedule.
  - Video-KYC (V-CIP) session prep in India.
- **Tier B.**
- **Note:** this overlaps the Compliance segment; cross-reference it.

### 75. Construction / Development Loan Draw Monitor
Checks each construction drawdown against progress.
- **Jobs:**
  - Budget-to-actual tracking.
  - Draw request versus cost-consultant certificate.
  - Retention maths.
  - Lien-waiver tracking (US).
  - Photo and inspection log.
  - Cost-to-complete test.
  - Draft the draw approval memo.
- **Tier B.**
- **Regions:** India RERA escrow (70% rule); UK monitoring surveyor; US lien waivers.

### 76. Agricultural and Rural Credit Assistant
Supports crop loans, Kisan credit and farm machinery finance.
- **Jobs:**
  - Scale-of-finance calculation.
  - Land-record checks (digital land records, the AgriStack farmer ID in India).
  - Crop insurance linkage (PMFBY).
  - Interest subvention tracking.
  - Seasonal repayment calendar.
  - Weather and price alerts for EWS.
- **Tier B.**
- **Regions:** India KCC / NABARD; Brazil Pronaf / Plano Safra; US FSA farm loans; Kenya / Nigeria agri-guarantee schemes.

### 77. Islamic Finance Structuring and Ops Assistant
Prepares Murabaha, Ijara, Musharaka and Tawarruq transaction steps and checks the sequence.
- **Jobs:**
  - Asset purchase-and-sale sequence checklist.
  - Profit-schedule calculation.
  - Late-payment charity treatment.
  - Shariah board file prep.
  - AAOIFI standard references.
  - Sukuk servicing reports.
- **Tier B** (the Shariah board rules).
- **Regions:** GCC (SAMA, CBUAE, CBB), Malaysia (BNM IFSA 2013), Indonesia, Pakistan, UK Islamic windows.

### 78. Lending Data and MI Analyst
Answers ad-hoc lending questions from the loan book.
- **Jobs:**
  - Funnel conversion.
  - Turnaround-time (TAT) reports.
  - Approval and decline mix.
  - Channel profitability.
  - Delinquency dashboards.
  - Prepayment speeds.
  - Data-dictionary upkeep.
- **Tier B.**

---

## Never an AI employee (tier C) in this segment

| Reserved act | Why it stays human |
|---|---|
| Approving or declining a loan, card or limit; setting a final price or limit | Accountable credit authority under delegation-of-authority. EU AI Act high-risk and CCD2 / GDPR Art. 22 give a right to human intervention. ECOA / Reg B require specific adverse-action reasons. |
| Signing credit committee minutes or the risk rating as final | Board-delegated authority; supervisory accountability (SMCR in the UK, RBI fit-and-proper). |
| Releasing or disbursing funds; debiting a borrower | Payment authorisation requires maker-checker and the customer's mandate. |
| Furnishing or deleting bureau data as the lender's decision | The furnisher is legally liable (FCRA, CICRA). The AI prepares; a human authorises the file. |
| Declaring a default, accelerating a loan, issuing a SARFAESI possession notice, starting foreclosure | Legal act with severe consequences; the lawyer or authorised officer signs. |
| Repossessing collateral; physical recovery visits | Physical and legal act; strict conduct rules (RBI recovery agents, UCC 9-609 breach of the peace). |
| Contacting debtors with threats, or at all outside the lawful hours, channels and frequency | Illegal (FDCPA / Reg F, CONC 7, RBI). An AI must never be configured for it. |
| Giving regulated mortgage advice or a suitability recommendation; regulated debt advice (UK) | FCA-authorised advisers; Australia best-interests duty; SAFE Act licensing. |
| Acting as insolvency practitioner, resolution professional, trustee or receiver | Licensed person (IBBI, RPBs, US trustee). Personal statutory duties. |
| Signing an independent valuation, appraisal or engineer certificate | Licensed appraiser / valuer (USPAP, RICS, IBBI registered valuers). |
| Certifying securitisation reports or STS compliance as the issuer; signing a loan-sale reps & warranties certificate | Issuer / servicer legal liability. |
| Filing lending regulatory returns as the institution | The institution's authorised signatory files. |
| Approving KYC or onboarding a borrower; freezing an account; filing an STR / SAR | Compliance / MLRO decision (see the compliance segment). |
| Deciding a complaint finally, or ombudsman determinations | Accountable complaint handler / ombudsman. |
| Shariah rulings | The Shariah supervisory board. |

---

## Top 10 roles to build first, and why

1. **#1 Loan Shopper and Cost Explainer.** It works the same in every country (APR, KFS, CET, CAT). It needs only documents, so no partner deal is required, and it extends Hoola's existing `paisa_sahayak` loan maths globally.
2. **#2 Credit Report and Score Fixer.** It is the biggest complaint category on earth: about 88% of the CFPB's 6.6M complaints in 2025 were about credit reporting, and the FTC found 1 in 5 consumers have errors. It is document-only and drafts letters with deadlines.
3. **#3 Debt Payoff Planner and Restructure Helper.** Demand is huge (Brazil 80M+ defaulters; UK and US hardship). It is tier A and fits the chat plus reminders pattern.
4. **#9 Business Loan Readiness Assistant.** SMEs are the core Hoola customer, and Hoola already reads books (bahi), bank statements and GST. It reuses Hoola's existing accounts work.
5. **#11 Trade Finance Desk Assistant (SME).** The trade-finance gap is about US$2.5tn and SMEs are rejected about 41% of the time. UCP 600 pre-checks are rule-based, so an AI can do them well and demand is proven (Traydstream, Conpend).
6. **#21 SME / Commercial Credit Analyst (spreading and memo).** This is the most deployed generative-AI use case in commercial credit (Moody's, S&P, Aloan). It is a strong B2B sale to banks, NBFCs and credit unions, and always tier B.
7. **#52 Covenant Compliance Monitor.** A clear deadline-and-calculation job that Hoola's tracking engine suits. There is evidence from Aloan, EnFi and Covenant IQ, and it needs only documents plus the borrower's financials.
8. **#44 Early-Stage Collections Assistant (ethical).** It has the biggest volume and proven vendors (Prodigal, Skit.ai). It needs hard-coded contact windows, frequency caps and vulnerability hand-offs; these mirror rules Hoola already enforces in code.
9. **#31 / #32 Loan Documentation, CP Checker and Security Registration Tracker.** Low risk, high pain: missed charge registrations void security. It is pure checklists and deadlines, and combines naturally with Hoola's document reading.
10. **#64 Co-Lending and Loan Participation Coordinator, plus #25 Digital Lending Journey Checker.** New rules have just hit (India Co-Lending 1 Jan 2026, Digital Lending Directions 2025, UK DPC, EU CCD2), fintech partnerships are booming, and the reconciliation and disclosure work is mechanical.

---

## Pains with evidence (summary)
- CFPB 2025: about 6.6M complaints, about 5.8M (88%) about credit reporting (SEARCH: CFPB 2025 Consumer Response Annual Report; Orrick summary).
- Debt collection complaints: about 207.8k in 2024 (CFPB FDCPA report); about 387k in 2025 per a vendor citing the CFPB (verify) (SEARCH).
- FTC (2013): 1 in 5 consumers had an error on at least one report; 5% had errors serious enough to cause worse terms (SEARCH).
- Trade-finance gap of about US$2.5tn; SME trade-finance rejection about 41% (ADB 2025) vs an older WTO figure of about 50% (SEARCH).
- Brazil: 80.6M people in default at end 2025 and 83.3M in April 2026 (Serasa) (SEARCH).
- Global Findex 2025: only 24% of adults in LMICs borrowed formally and 31% from family and friends (SEARCH).
- LSTA loan settlement averaged about 19.5 days in 2023 against a T+7 benchmark (SEARCH).
- Kenya digital-lender licensing: 252 licensed by July 2026 out of 800+ applications since 2022, after crackdowns on predatory apps (SEARCH).
- CFPB Private Education Loan Ombudsman: record complaint numbers in its Jan 2026 report (SEARCH).

## Existing AI products (evidence it is doable)
- **Mortgage:** Blend (Autopilot agent, DocAI), Tavant TOUCHLESS / MAYA, Ocrolus (automated conditioning, Freddie AIM Check), Addy, Floify, ICE Mortgage Technology (SEARCH).
- **Commercial credit:** Moody's / S&P credit-memo AI, Evalueserve, Aloan, EnFi, Uptiq, Accend, Krida, CreditQuant (SEARCH).
- **Collections:** Prodigal proAgent, Skit.ai (SEARCH); Credgenics, TrueAccord, InDebted (from memory - verify).
- **Trade:** Traydstream, Conpend / Finastra TradeAI, HSBC in-house tool, Surecomp, Bolero (SEARCH).
- **Underwriting / alternative data:** Zest AI, Upstart, Nova Credit, Perfios, Finbox (from memory - verify).

## Sources
OPENED (fetched this session):
- https://www.bls.gov/ooh/business-and-financial/loan-officers.htm
- https://www.onetonline.org/link/summary/43-4131.00

SEARCH (read only in search-result summaries; the pages themselves were not opened, so verify key figures):
- https://files.consumerfinance.gov/f/documents/cfpb_2025-cr-annual-report_2026-03.pdf
- https://infobytes.orrick.com/2026-04-10/cfpb-reports-complaint-volume-doubled-in-2025-citing-surge-in-credit-reporting-disputes/
- https://files.consumerfinance.gov/f/documents/cfpb_fdcpa-2025-annual-report_2025-11.pdf
- https://files.consumerfinance.gov/f/documents/cfpb_pelo-annual-report_2026-01.pdf
- https://search.ftc.gov/news-events/news/press-releases/2013/02/ftc-study-five-percent-consumers-had-errors-their-credit-reports-could-result-less-favorable-terms
- https://nationalmortgageprofessional.com/news/blend-takes-agentic-ai-live-first-mortgage-lenders
- https://nationalmortgageprofessional.com/news/tavant-launches-new-ai-origination-suite
- https://www.housingwire.com/articles/ocrolus-automated-conditioning/
- https://www.gtreview.com/measures-needed-to-close-trade-finance-gap-amid-tariff-upheaval-adb-says/ (gtreview.com/news/global/...)
- https://www.gtreview.com/news/global/half-of-sme-trade-finance-requests-rejected-wto-finds/
- https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12888 (Co-Lending Directions 2025)
- https://website.rbi.org.in/documents/d/rbi/directionsondigitallending
- https://www.scconline.com/blog/post/2025/08/08/rbi-co-lending-directions-2025-joint-lending-framework-banks-nbfcs/
- https://www.business-standard.com/finance/news/gold-loan-ltv-raised-to-85-percent-up-to-rs-2-5-lakh-rbi-125060601173_1.html
- https://ey.com/en_in/insights/strategy-transactions/rbi-gold-loan-guidelines-2025-impact-assessment-and-key-changes
- https://oeil.europarl.europa.eu/oeil/en/procedure-document-summary/pdf?id=1764052 (CCD2)
- https://openbankingtracker.com/blog/ccd2-guide-for-lenders-and-bnpl-providers
- https://www.fca.org.uk/publications/policy-statements/ps26-1-regulation-deferred-payment-credit
- https://www.fca.org.uk/news/press-releases/new-protections-confirmed-buy-now-pay-later-borrowers
- https://www.asic.gov.au/regulatory-resources/credit/buy-now-pay-later-credit-contracts-credit-licensing
- https://www.gtlaw.com.au/insights/asic-provides-important-guidance-on-the-bnpl-and-low-cost-credit-contract-reforms
- https://prodigaltech.com/proagent
- https://www.insidearm.com/news/00092837-prodigal-launches-proagent-to-automate-en/
- https://www.cfodive.com/press-release/20230419-skitai-revolutionizes-the-us-arm-industry-with-scalable-conversational-v/
- https://events.lsta.org/app/uploads/2025/04/Settlement-Data-Review-09Apr25.pdf
- https://finastra.com/applications/tradeai
- https://www.gtreview.com/news/digital-trade/bolero-partners-with-traydstream-to-automate-trade-document-checks/
- https://www.spglobal.com/market-intelligence/en/news-insights/research/2025/07/credit-memo-automation-where-ai-meets-analyst-efficiency
- https://www.moodys.com/web/en/us/insights/banking/future-of-credit-assessment-turning-information-into-better-lending-decisions.html
- https://www.multimodal.dev/agentic-workflows/commercial-lending-ai
- https://informaconnect.com/finovatefall;1/sponsors/aloan/
- https://www.worldbank.org/en/publication/globalfindex/report
- https://nairametrics.com/2025/07/18/world-bank-59-of-adults-in-nigeria-and-others-borrowed-in-2024
- https://www.the-star.co.ke/news/2026-07-14-cbk-licenses-25-more-digital-lenders
- https://webiis10.mondaq.com/consumer-law/1792304/fccpc-digital-lending-regulations-2025-what-it-means-for-digital-lenders
- https://www.serasa.com.br/imprensa/inadimplencia-ultrapassa-806-milhoes-virada-ano-dividas-impedem-sonhos-serasa/
- https://www.serasa.com.br/imprensa/serasa-estudo-impacto-novo-desenrola-brasil-inadimplencia/

Everything else (O*NET / ISCO / ANZSCO codes, US Reg X / Reg F / FCBA specifics, Indian recovery-agent hours and property-paper compensation, UK CONC 6.7 / s.75 / s.87, Basel / IFRS 9 / CECL references, Islamic-finance standards, securitisation regimes, Japan / Korea / China specifics, the US 1033 status, NY BNPL law) is **from memory - verify**.
