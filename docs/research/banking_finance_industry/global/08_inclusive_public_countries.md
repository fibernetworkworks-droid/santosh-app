# 08 - SME & inclusive finance, public sector & education + country packs

Segment owner: research brief `BRIEF.md`. Date of research: 22 Nov 2026.

How to read this:
- Tiers: **A** = admin / prepare / explain / calculate (safe, the user acts); **B** = assists a named
  accountable person (loan officer, supervisor, caseworker, Shariah board, ombudsman) who decides / signs;
  **C** = never an AI employee (listed at the end with the reason).
- "Sourced" = a page actually opened in this research (listed in Sources). Anything else is marked
  **(from memory - verify)**. Country facts in Part 2 are mostly from memory and say so; the few that were
  checked this session carry a ✓.
- Hard limits from the brief apply to every role: no money moved, no loan / claim / account / KYC approved
  or declined, no regulatory filing AS the institution, no signed opinions, no PIN / OTP / CVV / passwords.

Occupation anchors used (taxonomy codes from memory - verify): ISCO-08 2413 Financial analysts, 2412
Financial and investment advisers, 3312 Credit and loans officers, 4211 Bank tellers, 4214 Debt collectors,
3313 Accounting associate professionals, 2422 Policy administration professionals, 3353 Government social
benefits officials, 2310/2330 Teachers, 2635 Social work and counselling professionals, 1211 Finance managers,
2120 Statisticians, 3411 Legal and related associate professionals; O*NET 13-2072 Loan Officers, 13-2052
Personal Financial Advisors, 13-1041 Compliance Officers, 13-2061 Financial Examiners, 19-3011 Economists,
43-4061 Eligibility Interviewers (Government Programs), 21-1093 Social and Human Service Assistants,
13-2071 Credit Counselors, 33-3021 Detectives and Criminal Investigators (fraud), 25-xxxx teachers;
ESCO "microfinance officer", "credit union manager", "financial inclusion officer" (check ESCO URIs).

---

## Demand evidence (pains, sourced)

| Pain | Number | Source |
|---|---|---|
| Adults still without any account | ~1.3-1.4 bn; account ownership 79% globally, 75% in LMICs; 15% have mobile money; SSA 40% mobile money (2024) | World Bank Global Findex 2025 press release + blog |
| Formal MSME finance gap (emerging markets) | US$5.7 tn (~19% of GDP); ~US$8 tn incl. informal; women-owned firms ~US$1.9 tn | IFC SME finance page; World Bank SME finance topic (MSME Finance Gap report, Mar 2025) |
| Smallholder farmer finance gap | US$170 bn/yr (ISF 2022) -> >US$200 bn/yr (ISF 2025); agri-SMEs US$106 bn | CPI report citing ISF; NextBillion on ISF 2025 |
| Cost of sending US$200 remittance | 6.49% global average Q1 2025 (6.36% Aug 2025 site); 8.78% into Sub-Saharan Africa; SDG target 3%, G20 5x5 | World Bank Remittance Prices Worldwide, Issue 53 |
| Savings groups | SAVIX MIS 13.8 m members / 547k groups / 75 countries; CARE FY24 20.7 m members, 515k groups, 67 countries; ~100 m incl. India SHGs (CGAP) | vsla.net; CARE FY24 snapshot; CGAP |
| Mobile money scale | 2.3 bn registered accounts, 593 m monthly active, >US$2 tn transactions in 2025; ~30 m registered agents (verify in PDF) | GSMA State of the Industry 2026 |
| Scams globally | ~US$1.03 tn lost in 12 months; only 4% of victims recover; 3-4% of GDP in Pakistan, Kenya, South Africa | GASA / Feedzai Global State of Scams 2024 |
| US fraud | US$12.5 bn reported 2024 (+25%); investment scams US$5.7 bn; age 60+ losses US$2.4 bn | FTC Consumer Sentinel press release Mar 2025 |
| Complaints to ombudsman | UK FOS 305,918 complaints 2024/25 (+54%), 34% upheld, motor finance 76,160 | FOS press release Jul 2025 |
| Refugees blocked by KYC | Legal / practical barriers to SIM, bank and mobile-money accounts in a majority of 20 priority countries (2019); 79-country UNHCR/DLA Piper mapping 2026 | UNHCR blog + 2026 summary; GSMA 2019 |
| Supervisors adopting gen AI | 42 authorities surveyed Jan-Mar 2025, many experimenting with gen AI for supervision; suptech study of 112 authorities in 97 countries | BIS FSI Brief 26; BIS WP 1309 |
| Financial literacy | 39 economies measured in OECD/INFE 2023 survey (knowledge, behaviour, attitudes, digital literacy, well-being) | OECD/INFE 2023 report page |

---

# PART 1 - ROLES

## A. Small-business & micro-enterprise finance

### 1. Small-Business Loan Readiness Officer
Packs a small firm's credit file so a lender can say yes or no faster.
- Hires: sole trader, SME, accountant, CDFI/MFI as a front door.
- Jobs: (1) list the documents a named lender/scheme asks for; (2) build 12-24 month cash-flow and DSCR from
  bank statements / ledger; (3) compute affordable loan size and EMI/amortisation at quoted rate; (4) draft the
  business plan / use-of-funds note from her facts; (5) check the owner's credit report for errors before applying;
  (6) compare offers by APR / total cost incl. fees and collateral; (7) flag red-flag terms (personal guarantee,
  confession of judgment, daily-debit MCAs); (8) track application status and lender questions; (9) diary covenant
  and repayment dates after the loan.
- Tier A (the lender decides; owner signs).
- Data/rails: open banking / Account Aggregator statements, accounting (QuickBooks, Xero, Tally, Zoho), credit bureau
  self-reports, tax returns, GST/VAT returns.
- Regional: US SBA 7(a)/504 + state small-business credit (SBA eligibility rules); UK British Business Bank Start Up
  Loans + Recovery Loan Scheme successor (Growth Guarantee Scheme) (verify); EU national promotional banks (KfW,
  Bpifrance, ICO, CDP) + EIF guarantees; India MUDRA / CGTMSE / TReDS / Account Aggregator-based OCEN (verify);
  Indonesia KUR; Brazil Pronampe; Mexico NAFIN; Nigeria BOI / CBN interventions; Kenya Hustler Fund; Saudi Monsha'at
  + Kafalah; UAE Khalifa Fund; Australia SME Guarantee Scheme ended - check; Canada BDC + CSBFP.
- Existing products: QuickBooks Capital / lending (the plugin in this environment exposes "qbo_lending_get_offers"
  and "approval factors" - evidence the pattern exists); Lendio, Fundera (US marketplaces, from memory - verify);
  Funding Options / Swoop (UK, from memory - verify).
- Pains: IFC MSME gap US$5.7 tn (sourced).

### 2. Public Credit-Guarantee & Subsidised-Loan Scheme Navigator
Finds which state-backed loan, guarantee or interest-subsidy scheme a business fits and prepares the claim forms.
- Hires: SME, micro-entrepreneur, chamber of commerce, accountant.
- Jobs: eligibility screen against scheme rules; collateral-free limit check; interest-subvention arithmetic; required
  certificates list (MSME/Udyam, tax clearance, women/youth status); draft application; track scheme deadlines and
  budget windows; prepare claim for subsidy reimbursement; renewal reminders.
- Tier A.
- Rails: scheme portals (JanSamarth India, SBA Lender Match, BBB finder), tax portals.
- Regional: as role 1 plus EU state-aid de minimis ceiling (EUR 300k over 3 yrs since 2024 - verify); GCC SME banks.
- Products: JanSamarth (government portal, from memory - verify).

### 3. Grants, Rebates & Business-Support Finder (public money, non-repayable)
Matches an SME / NGO to grants, tax credits and rebates and drafts the application.
- Hires: SME, startup, NGO, farmer co-op, school.
- Jobs: search official grant databases; eligibility matrix; budget template; narrative draft from her facts only;
  match-funding calculation; deadline calendar; post-award reporting and audit checklist; R&D tax credit
  pre-qualification worksheet.
- Tier A (she submits).
- Rails: Grants.gov / SAM.gov (US), EU Funding & Tenders portal, UK Find a Grant, India Startup India / state portals,
  Kenya Youth Enterprise Fund (verify).
- Products: the "grant-rfp-writer" skill in this environment (Claude small-business plugin) is direct evidence;
  Instrumentl (US, from memory - verify).

### 4. Invoice & Supply-Chain Finance Helper
Turns unpaid invoices into working capital through regulated factoring / reverse-factoring rails.
- Hires: SME supplier, exporter.
- Jobs: ageing analysis; list invoices eligible for a platform; compute discount cost vs overdraft; prepare upload
  files; reconcile buyer payments to discounted invoices; MSME late-payment interest calculation (India MSMED Act 45
  days, EU Late Payment Directive 60 days, UK Prompt Payment Code); dispute letters to slow payers; export-credit
  insurance hand-off.
- Tier A.
- Rails: India TReDS (RXIL, M1xchange, Invoicemart); Mexico NAFIN Cadenas Productivas; EU factoring; UK Fair Payment
  Code; e-invoicing feeds (KSeF, SdI, CFDI) make invoice provenance verifiable.
- Products: Tradeshift, Taulia, C2FO (from memory - verify).

### 5. Micro-Enterprise Cash-Book Keeper (voice / chat bookkeeping)
Keeps a simple daily book for an informal shop, stall or artisan by voice note or photo of receipts.
- Hires: informal micro-enterprise, street vendor, kirana, market trader.
- Jobs: record sales / purchases / udhaar in local language; daily cash count; stock list; credit owed by customers
  with reminders she sends; weekly profit; simple VAT/GST threshold watch; produce a 6-month statement a lender or MFI
  can read; separate household vs business money.
- Tier A.
- Rails: mobile-money statements (M-Pesa, MTN MoMo, bKash), UPI, WhatsApp Business.
- Regional: Kenya/Tanzania/Uganda (M-Pesa statements accepted by digital lenders), India (Khatabook-style), Nigeria
  (OPay/Moniepoint POS), Indonesia (BukuWarung), LatAm (Mercado Pago).
- Products: Khatabook, OkCredit (India), BukuWarung (Indonesia), Kippa (Nigeria) - all from memory - verify.

### 6. Business Formalisation Assistant
Walks an informal business through registration so it can borrow, invoice and get public support.
- Hires: informal entrepreneur, NGO programme.
- Jobs: pick the simplest legal form (Brazil MEI, Argentina Monotributo, Mexico RESICO, India Udyam + GST composition,
  Kenya single business permit, Philippines BMBE); fee and tax comparison; document list; draft forms; track
  registration; first-year tax calendar; set up business bank / mobile-money merchant account (her tap).
- Tier A.
- Rails: government one-stop portals (gov.br, Udyam, eCitizen Kenya, SAT).

### 7. Merchant Payments Onboarding & Acceptance Helper
Gets a small shop accepting QR / instant payments and reconciles settlements.
- Hires: micro-merchant, SME.
- Jobs: compare MDR / fees across acquirers; prepare onboarding KYB documents; generate static/dynamic QR via
  official app; daily settlement reconciliation; chargeback / dispute evidence pack; refund policy text; cash vs
  digital split for tax; detect fake "payment received" screenshots.
- Tier A.
- Rails: Pix, UPI, PromptPay, QRIS, DuitNow, PayNow, FedNow (via bank), PayShap, InstaPay, Bre-B.
- Pains: GSMA notes fraud and transaction taxes as persistent problems (sourced, SOTIR 2026).

## B. Microfinance & community finance

### 8. Microfinance Borrower Coach
Helps a borrower understand and keep up with micro-loans without over-borrowing.
- Hires: consumer / micro-entrepreneur, NGO.
- Jobs: show true APR / effective interest incl. fees and compulsory savings; repayment schedule and reminders;
  multiple-lending / over-indebtedness check (total EMI vs income); restructuring request draft; explain rights under
  client-protection rules; record payments and receipts; spot illegal lenders / loan-app harassment and how to report.
- Tier A.
- Regional: India RBI microfinance framework 2022 (household income cap, 50% FOIR) (from memory - verify); Cambodia
  over-indebtedness concerns; Kenya CBK digital credit provider licensing (2022); Philippines SEC lending company
  rules; Nigeria FCCPC digital lending regulations 2025 (verify).
- Products: Kiva borrower tools; Tala / Branch customer apps (from memory - verify).

### 9. MFI Loan Officer Field Assistant
Prepares field visits and cash-flow appraisals for a loan officer, who decides.
- Hires: MFI, NBFC-MFI, SACCO, credit union, rural bank.
- Jobs: route plan for collections; pre-fill client KYC checklist (no approval); household cash-flow appraisal
  worksheet; group-liability roster; PAR watch per officer; overdue follow-up scripts; meeting minutes in local
  language; photo/document completeness check; early-warning notes (crop failure, migration).
- Tier B (loan officer + credit committee decide).
- Rails: core banking (Mifos/Fineract, Musoni, Oradian), bureau pulls by the institution, satellite crop data.
- Products: Apollo Agriculture - field officers collect data, AI models give instant eligibility feedback while with
  the farmer, final decision automated (sourced GSMA). Note for Hoola: the decision stays with the human - we only
  prepare.

### 10. MFI Portfolio & Social-Performance Analyst
Produces the PAR, provisioning and client-protection reports an MFI's board and regulator expect.
- Hires: MFI, cooperative bank, impact investor.
- Jobs: PAR30/90 and write-off trend; vintage analysis; provisioning per local norms; client-protection
  self-assessment (Cerise+SPTF Universal Standards); interest-rate transparency check; funder covenant reporting;
  over-indebtedness indicators; board pack draft.
- Tier B (CFO / CEO sign).
- Regional: MIX legacy data now in Atlas (verify); regulators: RBI, BSP, CBK, BoG, OJK, SBP.

### 11. Co-operative & Credit-Union Treasurer Assistant
Runs the money side of a co-op or credit union for an elected treasurer.
- Hires: SACCO, credit union, agri/dairy co-op, housing co-op.
- Jobs: member share and deposit ledger; loan eligibility arithmetic per bylaws (x times savings); dividend / patronage
  rebate calculation; liquidity ratio; AGM financial pack; statutory return draft; member statements; bylaw rule checks
  on new loans; audit-trail export.
- Tier B (treasurer / board sign; regulator filing by the co-op).
- Regional: Kenya SASRA (deposit-taking SACCOs); US NCUA (5300 call report); Canada provincial; UK PRA/FCA credit
  unions; India state co-op registrars + RBI for UCBs; Philippines CDA; Ireland Registry of Credit Unions (CBI).
- Products: Chamasoft (Kenya, from memory - verify).

### 12. Savings-Group Record Keeper (SHG / VSLA / chama / tontine / ROSCA)
Digital passbook and calculator for a member-run savings group.
- Hires: the group, its federation, NGO (CARE, Plan, Catholic Relief Services).
- Jobs: meeting-day savings and loan entries; share-out calculation at cycle end; interest on internal loans; fines
  and social fund; member passbooks by voice/photo; attendance; rotation order and payout schedule (ROSCA); quorum and
  constitution checks; group-grading data for bank linkage; reminders in local language.
- Tier A (the group decides; cash stays in the box / group account).
- Rails: SAVIX MIS (sourced), mobile wallets for group accounts, India NRLM / LokOS (from memory - verify).
- Pains: SAVIX 13.8 m members; CARE 20.7 m members (sourced).
- Products: DreamSave, Chamasoft, Ensibuuko (from memory - verify).

### 13. SHG Federation & Bank-Linkage Officer Assistant
Prepares savings groups for bank credit and tracks linkage.
- Hires: SHG federation, NGO, bank's financial-inclusion desk, NRLM block office.
- Jobs: group grading per bank format; credit-linkage file; repayment tracking across groups; interest-subvention claims;
  NPA watch; training calendar; federation MIS reports.
- Tier B (bank branch manager decides).
- Regional: India NABARD SHG-Bank Linkage; Bangladesh/Nepal similar; Africa VSLA-bank linkage (CARE).

### 14. Chit-Fund / ROSCA Safety Checker
Tells a member whether a rotating-savings scheme is a registered chit fund or a Ponzi.
- Hires: consumer.
- Jobs: check registration with the registrar; foreman commission and discount arithmetic; real return calculation;
  red flags (guaranteed returns, recruitment bonus); exit rights; complaint route.
- Tier A.
- Regional: India Chit Funds Act 1982 + BUDS Act 2019 (unregulated deposit ban) (verify); Kenya pyramid-scheme warnings
  (CMA); Nigeria SEC Ponzi warnings; Philippines SEC advisories.

### 15. Community Development / Mission Lender Loan Packager
Prepares loan files and impact data for CDFIs, community banks and mission lenders.
- Hires: CDFI, community bank, social lender.
- Jobs: borrower technical-assistance plan; file completeness; impact metrics (jobs, low-income area); grant/fund
  compliance reporting (CDFI Fund TLR - verify); portfolio monitoring; covenant reminders.
- Tier B.
- Regional: US CDFI Fund; UK Responsible Finance / CDFIs; Canada Community Futures.

## C. Agri & rural finance

### 16. Farmer Finance Assistant
Gets a farmer the cheapest crop / input / equipment credit and keeps it serviced.
- Hires: smallholder, farmer, FPO, agri-input dealer.
- Jobs: crop-cycle cash-flow plan; compare KCC / crop loan / input credit / BNPL-for-inputs; interest-subvention and
  prompt-repayment rebate math; land-record and document checklist; warehouse-receipt finance explanation; repayment
  calendar matched to harvest; insurance-premium share; price-risk notes (no trading advice).
- Tier A.
- Rails: land records (India Bhulekh, Kenya Ardhisasa), satellite NDVI, weather, mandi prices.
- Regional: India KCC + PM-Kisan + PMFBY (verify); Kenya Apollo, One Acre Fund; Nigeria Anchor Borrowers
  (CBN, wound down - verify); Brazil Pronaf + Plano Safra; Indonesia KUR; Philippines ACPC; US USDA FSA loans.
- Products: Apollo Agriculture (sourced, >100k farmers per FAO observatory); KhetScore India increased formal credit
  uptake ~20 pp in Odisha (sourced IFPRI).
- Pains: smallholder gap US$170-200+ bn/yr (sourced).

### 17. Crop & Livestock Insurance Claim Preparer (insurer-adjacent hand-off)
Documents a loss and prepares the claim; the insurer decides.
- Hires: farmer, FPO, MFI.
- Jobs: policy and trigger explanation (index vs indemnity); loss photo / geo-tag pack; deadline tracker (e.g. 72-hour
  intimation); claim form; follow-up; payout reconciliation into the account.
- Tier A.
- Regional: India PMFBY / Crop Insurance app; Kenya ACRE Africa; Mexico Agroasemex; US RMA. (from memory - verify)

### 18. Agri Value-Chain / Producer-Organisation Treasurer
Calculates member payments for a dairy/coffee/cocoa co-op or FPO.
- Hires: FPO, dairy co-op, outgrower scheme, aggregator.
- Jobs: produce-intake ledger by quality grade; price x quantity - deductions per member; input-credit recoveries; bulk
  payout file (her tap on the bank / mobile-money bulk rail); traceability record (EUDR due diligence data for
  coffee/cocoa - verify); member statements; working-capital need forecast.
- Tier B (board / manager approves payouts).
- Regional: EU Deforestation Regulation traceability (applies from Dec 2025 large, 2026 small - verify); Fairtrade
  premium accounting.

## D. Agents, correspondents & last-mile cash

### 19. Mobile-Money Agent / Banking-Correspondent Back-Office
Keeps a shop agent's float, cash and commission straight and spots fraud.
- Hires: individual agent, super-agent, BC.
- Jobs: daily float vs cash reconciliation; rebalancing alert; commission statement check; transaction-limit and KYC-tier
  rules explainer; suspicious pattern flag (split deposits, reversal scams, SIM swap); customer receipt log; tax on
  commission; agent-agreement obligations.
- Tier A (no transaction executed by the AI).
- Rails: M-Pesa, MTN MoMo, Airtel Money, bKash, GCash, Wave, OPay/Moniepoint; India AePS / BC; Brazil correspondentes.
- Regional: Kenya CBK agent guidelines; Nigeria CBN agent banking + shared-agent rules; Bangladesh BB MFS rules;
  India RBI BC model; Pakistan branchless banking (SBP).
- Pains: ~30 m registered agents (GSMA 2026, verify); fraud flagged as a persistent problem (sourced).

### 20. Agent-Network Manager Assistant
For the MNO / bank team that runs thousands of agents.
- Hires: MNO, bank, fintech.
- Jobs: agent activity and liquidity dashboard; dormant agent list; compliance visit checklist; mystery-shop analysis;
  fraud cluster detection for review; agent training content; regulator agent-return draft.
- Tier B (network manager; regulator return filed by the institution).

## E. Remittances, migrants, refugees

### 21. Remittance Cost Comparer & Family Money Planner
Finds the cheapest safe way to send money home and plans the family budget around it.
- Hires: migrant worker, diaspora family.
- Jobs: compare total cost (fee + FX margin) for the exact corridor and amount; recipient payout options (account,
  wallet, cash pickup); schedule; track what family spent / saved; savings goal at home; warn about hawala / unlicensed
  senders and scam "agents"; tax on remittance (US 1% excise on cash remittances from 2026 - verify).
- Tier A.
- Rails: World Bank Remittance Prices Worldwide (sourced), provider rate APIs, Wise / Remitly public quotes.
- Regional: US (CFPB Remittance Rule disclosures); GCC exchange houses (Al Ansari, Lulu); UK FCA-authorised EMIs;
  Philippines BSP; Mexico (largest US corridor); India (largest receiver).
- Products: Monito, Wise comparison (from memory - verify).
- Pains: 6.36-6.49% global average, 8.78% to SSA (sourced).

### 22. Migrant-Worker Money & Rights Assistant
Protects a cross-border worker's pay, contract and documents.
- Hires: migrant worker, NGO, diaspora association.
- Jobs: payslip vs contract check; recruitment-fee debt calculator; end-of-service gratuity calc (GCC labour laws);
  WPS salary-delay complaint draft; bank / wallet account opening documents in host country; pension portability note;
  repatriation of savings; trafficking / debt-bondage red flags and helplines.
- Tier A.
- Regional: UAE WPS + end-of-service rules; Saudi Musaned / Qiwa; Qatar WPS; Philippines DMW/OWWA; Nepal FEB; Malaysia
  EPF; ILO conventions (from memory - verify).

### 23. Refugee & Displaced-Person Finance Navigator
Finds which accounts, SIMs and cash assistance a refugee can legally access with the documents they hold.
- Hires: refugee, asylum-seeker, UNHCR partner NGO, humanitarian cash programme.
- Jobs: list documents accepted for KYC in that country (UNHCR ID, proof of registration); compare account / wallet
  options; cash-assistance schedule and entitlement explainer; budget on assistance; scam warnings; restore credit
  history from home country (letters); referral to legal aid.
- Tier A.
- Evidence: KYC remains a persistent barrier; UNHCR urges risk-based KYC per FATF; Zambia lets mobile-money providers
  accept refugee IDs (sourced UNHCR).
- Regional: EU Payment Accounts Directive right to a basic account incl. asylum seekers; Uganda, Kenya, Jordan, Turkey
  (ESSN card), Colombia (PEP/PPT for Venezuelans) (from memory - verify).

### 24. Humanitarian Cash & Voucher Assistance Coordinator
Plans and reconciles cash transfers for an NGO or UN agency.
- Hires: NGO, UN agency, government disaster agency.
- Jobs: transfer-value calculation (minimum expenditure basket); beneficiary list de-duplication for review; payment
  file prep for her approval; reconciliation of paid / unpaid; post-distribution monitoring survey analysis; donor
  report; complaint log; sanctions-screening request to the compliance owner.
- Tier B (programme manager authorises; compliance screens).
- Rails: CaLP standards, mobile-money bulk APIs, WFP SCOPE, RedRose (from memory - verify).

## F. Women, youth, inclusion

### 25. Women's Finance & Entrepreneur Coach
Helps a woman build her own credit record, savings and business finance.
- Hires: woman entrepreneur, women's group, NGO, bank's women-banking unit.
- Jobs: own-name account and ID checklist; collateral-free and women-targeted scheme finder; joint vs sole property /
  loan explainer; savings plan; business cash book; safe-money plan in economic-abuse situations (hidden-account
  safety, referral to helplines); succession / nomination.
- Tier A.
- Evidence: women-owned MSME gap ~US$1.9 tn (sourced World Bank).
- Regional: India Stand-Up India / Mahila schemes; Nigeria BOI women fund; Kenya Women Enterprise Fund; We-Fi (World
  Bank) programmes; US SBA Women's Business Centers (from memory - verify).

### 26. Youth & First-Job Money Coach
First account, first salary, first loan - without the traps.
- Hires: student, young worker, parent, school.
- Jobs: first budget; payslip and tax explained; student-loan repayment options; BNPL / payday-loan cost; build a
  credit history safely; first investing explainer (no recommendations); scam warnings (money mules, job scams).
- Tier A.
- Regional: US income-driven repayment (changes under 2025 law - verify); UK Plan 2/5 student loans; Australia HELP;
  money-mule recruitment warnings (UK, EU Europol).

## G. Islamic finance

### 27. Islamic Personal Finance Assistant
Keeps a household's money Shariah-aligned and explains Islamic products in plain words.
- Hires: Muslim consumer worldwide.
- Jobs: screen a stock / fund against published AAOIFI-style ratios (debt, interest income, sector) and show the
  numbers; explain murabaha / ijara home-finance cost vs a conventional mortgage (same APR math); purification amount
  of non-compliant income; halal budget; flag riba in a loan offer; zakat-ready asset list; takaful vs insurance
  explainer; inheritance (faraid) share calculation for the family to take to a scholar.
- Tier A (scholar / Shariah board rules on edge cases).
- Regional: Malaysia (BNM Shariah Advisory Council, IFSA 2013); GCC (central Shariah boards in UAE, Bahrain, Oman);
  Saudi; Pakistan (SBP Islamic banking, riba elimination by 2027 per court - verify); Indonesia (OJK + DSN-MUI); UK
  (Alternative Finance), Nigeria (Jaiz, non-interest banking).
- Products: Wahed - human review panel screens investments, then automated portfolios; claims AAOIFI certification
  (sourced TechCrunch / Wikipedia). Musaffa, Zoya stock screeners (from memory - verify).

### 28. Zakat, Sadaqah & Waqf Calculator / Planner
Calculates zakat correctly and plans giving.
- Hires: individual, family office, mosque, Islamic charity, SME.
- Jobs: nisab check (gold/silver price of the day); zakatable assets incl. business stock, receivables, investments;
  debts deductible per chosen school; lunar-year date tracking; distribution log to eligible categories; Saudi ZATCA
  zakat return prep for companies (business zakat is a statutory filing in KSA - she files); waqf income reports.
- Tier A (KSA corporate zakat filing by the company; scholar on disputed items).
- Regional: Saudi ZATCA (statutory corporate zakat); Malaysia state zakat centres + tax rebate; Pakistan (Zakat &
  Ushr deduction); Indonesia BAZNAS; elsewhere voluntary.

### 29. Islamic SME & Trade-Finance Structure Explainer
Prepares the paperwork for murabaha / ijara / musharaka / salam financing for the bank and its Shariah board.
- Hires: SME, Islamic bank / window.
- Jobs: sequence of the contract steps (ownership before sale); cost-plus schedule; asset and invoice evidence pack;
  late-payment charity clause check; tawarruq flags; Shariah audit checklist; financial reporting per AAOIFI FAS vs IFRS.
- Tier B (Shariah board + bank decide).

### 30. Sukuk & Islamic-Fund Compliance Analyst
Screens and monitors Islamic investments for a fund, bank or treasury.
- Hires: asset manager, Islamic bank, sovereign / pension fund.
- Jobs: index/portfolio screening; sukuk structure summary (ijara, wakala, mudaraba); asset-backing / tangibility ratio;
  purification calculations; Shariah board meeting pack; AAOIFI/IFSB standard mapping; ESG-sukuk use-of-proceeds
  tracking.
- Tier B.

### 31. Takaful Hand-off Assistant
Explains and compares family / general takaful and prepares the application or claim for the operator.
- Hires: consumer, SME.
- Jobs: wakala vs mudaraba model fees; surplus distribution explainer; coverage gap; documents; claim pack; renewal dates.
- Tier A (operator underwrites / decides).

## H. Debt, credit health, literacy

### 32. Debt Advice Triage & Budget Rebuilder
Gets an over-indebted household to a priority-debt plan and to free regulated advice.
- Hires: consumer, employer wellbeing scheme, NGO.
- Jobs: income and expenditure statement (UK Standard Financial Statement format); priority vs non-priority debts
  (rent, energy, tax first); minimum-payment vs payoff math; hardship / breathing-space request letters; statute-of-
  limitation dates (check per country); insolvency-option explainer (DRO, IVA, Chapter 7/13, consumer proposal) for a
  licensed adviser; referral.
- Tier A for triage; B where a licensed debt adviser / insolvency practitioner acts.
- Regional: UK Breathing Space + MoneyHelper + StepChange; US NFCC credit counselling; Canada LITs; Australia National
  Debt Helpline + financial counsellors; Germany Schuldnerberatung; South Africa debt review (NCR); India no personal
  insolvency in force (IBC Part III not notified - verify).
- Products: StepChange online debt remedy (from memory - verify).

### 33. Credit-Report Checker & Dispute Writer
Reads her bureau reports, finds errors and drafts disputes.
- Hires: consumer, SME owner.
- Jobs: pull reports from each bureau's free channel (her login); find duplicates, wrong defaults, fraud accounts; draft
  disputes with evidence; track statutory response time (US FCRA 30 days); score-impact explainer; fraud alert / freeze
  instructions; rebuild plan.
- Tier A.
- Regional: US annualcreditreport.com; UK statutory report; EU GDPR access + correction; India free annual report; South
  Africa free annual report; Australia free report every 3 months (from memory - verify).
- Products: Credit Karma (from memory - verify).

### 34. Adult Financial-Literacy Tutor
Teaches money basics in her language at her pace with quizzes from her own life.
- Hires: consumer, employer, NGO, central bank literacy programme.
- Jobs: lessons (budget, interest, inflation, risk, insurance, pensions, digital safety); quiz and progress; worked
  examples on her real numbers; scam spotting drills; certificates; voice-first for low-literacy users.
- Tier A.
- Evidence: OECD/INFE 2023 measured 39 economies incl. digital literacy and well-being (sourced).
- Regional: national strategies - India NCFE, UK MoneyHelper, US FLEC/MyMoney.gov, Brazil ENEF, Indonesia OJK SIKAPI,
  Malaysia FEN, Singapore MoneySense, Australia Moneysmart (from memory - verify).

### 35. School Financial-Education Teacher's Assistant
Builds lesson plans and assessments mapped to the curriculum.
- Hires: teacher, school, education ministry, NGO.
- Jobs: curriculum mapping (PISA financial literacy framework, national standards); lesson plans; age-appropriate
  simulations (budget game, interest calculator); marking rubric drafts (teacher marks); parent letters; progress data.
- Tier B (teacher grades).
- Regional: US states mandating personal-finance courses (number rising, verify); England citizenship/maths; Singapore;
  OECD PISA FL.

### 36. Financial Counsellor / Coach Caseload Assistant
Back-office for a human financial counsellor at an NGO, employer or council.
- Hires: NGO, local authority, employer EAP.
- Jobs: intake summaries; budget sheets; letters to creditors for the counsellor to sign; benefit checks (role 37);
  follow-up reminders; outcome reporting to funders; referral directory.
- Tier B.

## I. Government benefits & social payments

### 37. Benefits & Entitlements Navigator
Finds every benefit, subsidy and tax credit a household qualifies for and prepares the applications.
- Hires: consumer, family, carer, NGO.
- Jobs: eligibility screen (income, household, disability, age); application drafts; document list; renewal / recertif-
  ication dates; change-of-circumstances notices; overpayment explainer; appeal / reconsideration letter; benefit vs
  work earnings calculator (cliff effects).
- Tier A (agency decides).
- Regional: US SNAP, WIC, EITC/CTC, Medicaid, SSI; UK Universal Credit, Pension Credit (low take-up); Canada CCB/GIS;
  Australia Centrelink; Brazil Bolsa Família / CadÚnico; Mexico Bienestar programmes; South Africa SASSA grants; India
  PM-Kisan, PMJDY-linked DBT, state pensions; Indonesia PKH; Philippines 4Ps; Kenya Inua Jamii; EU national schemes.
- Products: mRelief SNAP screener + outreach chatbot; Frontline Q (Frontline Justice + Josef) for SNAP denials; Imagine
  LA + Nava navigator chatbot; Code for America + Anthropic SNAP Policy Navigator (all sourced).

### 38. Caseworker & Eligibility-Officer Assistant (government side)
Helps a public caseworker apply policy correctly and faster.
- Hires: welfare agency, social-security office, municipality.
- Jobs: policy Q&A with citations to the manual; case summary from documents; missing-verification list; notice draft
  in plain language; deadline queue; error-pattern spotting for QC; translation of notices.
- Tier B (official decides and signs every determination).
- Products: Code for America / Anthropic caseworker SNAP navigator; Nava LA chatbot for navigators; California open-
  source caseworker assistant pilot (sourced Route Fifty).

### 39. G2P / Social-Payment Reconciliation Officer
Reconciles benefit payrolls and payment failures for a government payer.
- Hires: social-protection ministry, treasury, payment agency.
- Jobs: payroll vs beneficiary register match; failed / returned payment list; dormant account detection; duplicate /
  deceased flag for review; payment-provider SLA report; grievance log analysis; audit trail.
- Tier B.
- Rails: India DBT/PFMS + Aadhaar Payment Bridge; Brazil Caixa; Pakistan BISP; Philippines Landbank; ISO 20022 bulk files.

### 40. Public Pension & Post-Office Savings Explainer
Explains state pensions and government savings products and fills the forms.
- Hires: consumer, retiree.
- Jobs: state-pension forecast request; contribution gaps and voluntary top-up math; government savings scheme rates
  and tax (UK NS&I, India Post Office schemes / PPF / SCSS, US Treasury I-bonds, Japan JP Bank); maturity calendar;
  nomination; life-certificate reminders.
- Tier A.

### 41. Small-Taxpayer Help Desk (public-facing explainer)
Plain-language help for micro-businesses and individuals dealing with the tax authority.
- Hires: consumer, sole trader, tax authority (as a front-desk aid).
- Jobs: which return / regime applies; threshold watch (VAT/GST); e-invoicing readiness for small sellers (see Part 2);
  notice explanation; payment-plan request draft; deadline calendar.
- Tier A (she files) / B for the authority's own staff.

## J. Consumer protection, complaints, fraud

### 42. Complaint & Ombudsman Escalation Writer
Turns a grievance against a bank / lender / insurer into a complaint that gets answered, then escalates on time.
- Hires: consumer, SME.
- Jobs: identify the firm's complaints procedure; draft complaint with timeline and evidence; diary the firm's response
  deadline (UK 8 weeks; India RBI 30 days; EU per PSD2 15 business days for payments - verify); escalate to the right
  ombudsman/ADR (Part 2 table); compensation calculation (interest on refunds); track outcome.
- Tier A.
- Pains: UK FOS 305,918 complaints, +54%, 34% upheld (sourced).
- Products: Resolver (UK, from memory - verify).

### 43. Scam-Victim Recovery & Reporting Assistant
The hour after a scam: what to do, in order, in that country.
- Hires: consumer, SME.
- Jobs: immediate steps checklist (call bank via the number on the card, freeze, change passwords - never collect them);
  build the evidence timeline (screenshots, transaction refs); file police / cyber report on the official channel (Part 2);
  reimbursement claim (UK APP mandatory reimbursement up to GBP 85k since Oct 2024; Australia Scams Prevention Framework;
  Singapore Shared Responsibility Framework - verify); credit freeze; recovery-scam warning; emotional-support referral.
- Tier A.
- Pains: GASA US$1.03 tn, 4% recover, half of scams finish within 24 h (sourced); FTC US$12.5 bn (sourced).

### 44. Fraud-Helpline & Cybercrime-Unit Intake Assistant
Structures victim reports for a helpline, police cyber unit or anti-scam centre.
- Hires: police cybercrime unit, national anti-scam centre, bank fraud team, consumer helpline NGO.
- Jobs: call/chat intake to a structured report; classify scam type; extract IBAN/UPI IDs/wallets/URLs for the officer;
  link to existing cases; draft freeze requests for an officer to send; victim updates; trend report; multilingual intake.
- Tier B (officer acts; any freeze is by the bank / police).
- Regional: India I4C 1930 + Citizen Financial Cyber Fraud Reporting; Singapore Anti-Scam Command; Indonesia IASC (OJK);
  Thailand AOC 1441; Australia National Anti-Scam Centre; UK Report Fraud; US IC3 (from memory - verify).

### 45. Consumer-Protection Market-Monitoring Analyst (for an authority or watchdog)
Reads complaints, ads and product terms to find harm early.
- Hires: consumer-protection agency, financial conduct regulator, consumer NGO.
- Jobs: complaint-database clustering; unfair-terms scan of T&Cs; ad / social-media finfluencer monitoring; dark-pattern
  checks on app flows; price/APR comparisons; mystery-shop scripts and analysis; briefing notes.
- Tier B (authority acts).
- Regional: US CFPB complaint database; UK FCA Consumer Duty; EU CPC network; Australia ASIC DDO; Brazil Senacon /
  consumidor.gov.br.

### 46. Ombudsman / ADR Case-Handler Assistant
Supports the ombudsman's own staff.
- Hires: financial ombudsman, ADR body.
- Jobs: case intake and jurisdiction check; chronology from both sides' files; precedent search of published decisions;
  draft provisional view for the case-handler; redress calculator; correspondence drafts; caseload analytics.
- Tier B (ombudsman decides).

## K. Central banks, regulators, supervisors, deposit insurers

### 47. Central-Bank Economic & Monetary-Policy Research Assistant
- Hires: central bank, finance ministry, think tank.
- Jobs: data pulls (CPI, GDP, credit, FX); nowcasting prep; literature summaries; policy-meeting briefing drafts; speech
  fact-checks; chart packs; text analysis of communications.
- Tier B (economists / MPC decide).

### 48. Financial-Stability & Macro-Prudential Analyst Assistant
- Jobs: systemic-risk dashboards; stress-test data prep; household / corporate debt maps; property-market indicators;
  FSR chapter drafts; network/interconnectedness data checks.
- Tier B.

### 49. Payment-System Oversight & Statistics Assistant
- Jobs: incident-report triage from operators; PFMI self-assessment mapping; payment statistics validation; instant-
  payment fraud trend analysis; fee/interchange monitoring; ISO 20022 migration tracking.
- Tier B.

### 50. Supervisory Returns & Early-Warning Analyst (prudential suptech)
- Hires: banking supervisor, insurance supervisor, co-op regulator.
- Jobs: validate regulatory returns (completeness, cross-checks); ratio trends vs peers (capital, liquidity, NPLs);
  early-warning scorecards; on-site examination prep packs; board-minute and policy-document review summaries; examiner
  report drafts; follow-up tracking of findings.
- Tier B (examiner / supervisor decides).
- Evidence: BIS survey of 42 authorities - many using gen AI for supervision, concentrated in automating supervisory
  processes (sourced FSI Brief); suptech drivers across 112 authorities (sourced WP 1309).

### 51. Conduct-Supervision Assistant
- Jobs: complaint-data trends per firm; product-term and fee reviews; sales-incentive analysis; vulnerable-customer
  outcome metrics; consumer-duty / fair-treatment evidence review; thematic review drafts.
- Tier B.

### 52. AML/CFT Supervisor & FIU Analyst Assistant
- Hires: FIU, AML supervisor.
- Jobs: STR/SAR triage and enrichment for the analyst; typology matching; network graphs from reports; institution AML
  risk scoring for supervisory planning; FATF mutual-evaluation evidence prep; dissemination drafts to law enforcement.
- Tier B (analyst decides what is disseminated).
- Regional: goAML (UNODC) used by many FIUs; FinCEN; NCA UKFIU; FIU-IND; FATF standards.

### 53. Licensing & Authorisation Officer Assistant
- Jobs: application completeness against the regulator's checklist; fit-and-proper document checks for the officer;
  business-plan and capital adequacy model sanity checks; Q&A letter drafts; timeline tracking against statutory clocks.
- Tier B (licence granted only by the authority).

### 54. Enforcement & Investigations File Preparer
- Jobs: evidence index; chronology; transaction analysis; draft notices for lawyers; precedent penalty table; disclosure
  bundle checks.
- Tier B.

### 55. Regulatory Policy & Consultation Analyst
- Jobs: summarise consultation responses; cross-jurisdiction comparison (Basel, IOSCO, IAIS, FATF, FSB); impact-assessment
  arithmetic; drafting support for rules (officials own the text); FAQ updates.
- Tier B.

### 56. Innovation-Hub / Regulatory-Sandbox Officer Assistant
- Jobs: sandbox application screening for completeness; test-plan and consumer-safeguard checklist; monthly test
  reporting templates; exit report drafts.
- Tier B.

### 57. Deposit-Insurer Payout-Readiness Analyst
- Hires: deposit insurance corporation.
- Jobs: single-customer-view (SCV) file validation; coverage calculation per depositor per bank; payout simulation data
  checks; bank data-quality findings; public-awareness survey analysis; IADI Core Principles self-assessment.
- Tier B.
- Regional: FDIC (US$250k), UK FSCS (GBP 85k -> GBP 120k from Dec 2025 - verify), EU DGSD EUR 100k, India DICGC Rs 5 lakh,
  Japan DICJ, Korea KDIC, Nigeria NDIC, Kenya KDIC, Malaysia PIDM, Brazil FGC.

### 58. Deposit-Protection & Bank-Failure Helper (public-facing)
- Hires: consumer, SME.
- Jobs: is my bank / product covered; how much is protected (joint, trusts); spread deposits over limits; what happens in
  a failure; claim steps.
- Tier A.

### 59. Central-Bank / Regulator Public-Enquiries & Register-Check Assistant
- Hires: regulator (as front desk) or consumer.
- Jobs: is this firm licensed (public registers - FCA Register, SEC EDGAR/IAPD, RBI NBFC list, MAS FID); warning-list checks
  (IOSCO I-SCAN); plain answers to rule FAQs; route complaint to right body.
- Tier A.

## L. Development finance & public finance

### 60. DFI Investment-Officer Due-Diligence Assistant
- Hires: DFI (IFC, EBRD, ADB, AfDB, FMO, BII, DEG, Proparco, US DFC), impact investor.
- Jobs: data-room review; IFC Performance Standards / E&S gap list; financial model checks; KYC/integrity due-diligence
  document requests (decision by the integrity team); investment memo draft; covenant set; portfolio-monitoring reminders.
- Tier B (investment committee decides).

### 61. Credit-Line, Guarantee & On-Lending Programme Monitor
- Jobs: partner-bank sub-loan eligibility checks against programme criteria; disbursement and utilisation tracking;
  results indicators (women-owned SMEs, climate); guarantee claim files; reporting to donors.
- Tier B.

### 62. Impact & Results Reporting Analyst
- Jobs: indicator frameworks (IRIS+, HIPSO, 2X Criteria for gender); data collection templates; clean and aggregate
  partner data; impact report drafts; GHG accounting for portfolio (PCAF) prep.
- Tier B.

### 63. Public Treasury & Cash-Management Analyst
- Hires: finance ministry, treasury, state/municipal finance department.
- Jobs: cash-flow forecast of government accounts; Treasury Single Account balances; debt-service calendar; auction
  calendar notes; budget execution reports; arrears tracking; PEFA indicator evidence.
- Tier B.

### 64. Grants-to-Public-Bodies & Procurement Payment Compliance Assistant
- Jobs: invoice vs contract vs delivery 3-way match for officials; eligibility of expenses under grant rules; late-payment
  interest; audit-file preparation.
- Tier B.

---

## Never an AI employee (tier C) in this segment
| Task | Reason |
|---|---|
| Approving / declining a micro-loan, crop loan, SME loan or guarantee | Credit decision is the lender's licensed act; fair-lending / RBI / CBK rules hold a named person accountable |
| Disbursing / collecting cash for a savings group, chama, co-op or agent float | Money moves only by the members / agent on official rails |
| Performing KYC / onboarding decision for refugees, agents or customers | Regulated CDD decision of the institution |
| Issuing a fatwa / Shariah compliance certificate | Reserved to the Shariah board / qualified scholar |
| Granting or refusing a social benefit, deciding an appeal | Statutory official decision; due-process rights |
| Filing a regulatory return, STR/SAR, or a zakat / tax return AS the entity | Filer is the entity / its officer |
| Setting monetary policy, approving a licence, imposing a penalty, ordering a bank resolution | Public-law powers of named officials |
| Deciding an ombudsman complaint | Statutory adjudication |
| Freezing an account / ordering a hold for a scam victim | Bank / police / court power |
| Paying deposit insurance claims | Insurer's statutory act |
| Investing donor / DFI money, signing a guarantee | Investment committee / board |
| Running a chit fund / ROSCA as foreman | Licensed role (India Chit Funds Act) and money handling |
| Licensed debt advice / insolvency proposals in jurisdictions that regulate them (UK FCA debt counselling, US credit counsellors certified for bankruptcy) | Requires authorisation; AI drafts, adviser gives advice |

## Top 10 roles to build first and why
1. **Scam-Victim Recovery & Reporting (43)** - largest measured pain (US$1 tn, 4% recover), time-critical, pure tier A,
   needs only the country pack (Part 2 fraud channel column).
2. **Benefits & Entitlements Navigator (37)** - proven demand (mRelief, Code for America, Frontline Q), money for the user
   with no lending risk, works in every country.
3. **Complaint & Ombudsman Escalation Writer (42)** - FOS volumes +54%; the country pack gives each ombudsman and deadline.
4. **Small-Business Loan Readiness Officer (1)** - US$5.7 tn gap; reuses Hoola's open-banking / bookkeeping data.
5. **Micro-Enterprise Cash-Book Keeper (5)** - voice-first, the entry door for informal businesses and the data that later
   feeds roles 1, 2, 8.
6. **Savings-Group Record Keeper (12)** - tens of millions of members on paper; simple arithmetic, high trust.
7. **Remittance Cost Comparer (21)** - measurable saving (6.4% -> ~3% on cheapest), daily habit for migrants.
8. **Islamic Personal Finance + Zakat (27/28)** - ~1.9 bn Muslims (from memory - verify), weak tooling, arithmetic-heavy.
9. **Farmer Finance Assistant (16)** - US$170-200 bn gap; evidence that digital tools raise formal credit (KhetScore +20 pp).
10. **Debt Advice Triage (32)** - high harm, clear legal templates per country, hands off cleanly to free licensed advice.
(Institution roles 50-52 are high value but B2G sales cycles are long; build after the consumer packs prove reliable.)

---

# PART 2 - COUNTRY PACKS

**Status:** compiled mostly **from memory - verify each cell against the official site before shipping a pack.**
Cells marked ✓ were checked against a page opened in this research (see Sources). Names change often
(e.g. FIRS -> Nigeria Revenue Service; AFIP -> ARCA; UK Action Fraud -> Report Fraud) - every pack needs a
`checked_on` date and a `review_by` date, the same rule Hoola's BAHI rules files already use.

Suggested pack schema (one JSON per country):
`{country, currency, central_bank, banking_regulators[], securities_regulator, ombudsman[], instant_payments[],
open_banking{framework, status}, credit_bureaus[], tax_authority, e_invoicing{mandate, scope, dates},
data_protection_law, fraud_reporting[], deposit_insurance, source_urls[], checked_on, review_by}`

## Table 1 - Regulators, central bank, complaints body, currency

| Country | Banking regulator(s) | Securities regulator | Central bank | Financial ombudsman / complaints | Currency |
|---|---|---|---|---|---|
| United States | Fed, OCC, FDIC, NCUA, state regulators; CFPB (consumer) | SEC, FINRA (SRO), CFTC | Federal Reserve | No single ombudsman: CFPB complaint portal; state AGs; FINRA arbitration | USD |
| Canada | OSFI (prudential), FCAC (conduct), provincial | CIRO + provincial (OSC, AMF Québec...) | Bank of Canada | OBSI; ADR Chambers Banking Ombuds Office (single designated body planned - verify) | CAD |
| Mexico | CNBV | CNBV | Banco de México | CONDUSEF | MXN |
| Brazil | Banco Central do Brasil (CMN rules) | CVM | BCB | BCB complaints + consumidor.gov.br + Procon; bank ouvidorias | BRL |
| Argentina | BCRA (SEFyC) | CNV | BCRA | BCRA Usuarios Financieros; Defensa del Consumidor | ARS |
| Colombia | Superintendencia Financiera (SFC) | SFC | Banco de la República | Defensor del Consumidor Financiero (per entity) + SFC | COP |
| United Kingdom | PRA (Bank of England) + FCA | FCA | Bank of England | Financial Ombudsman Service ✓ | GBP |
| Ireland | Central Bank of Ireland (+ ECB SSM) | Central Bank of Ireland | CBI / Eurosystem | FSPO | EUR |
| Germany | BaFin + Bundesbank (+ ECB SSM) | BaFin | Bundesbank / ECB | Ombudsmann der privaten Banken, Sparkassen/Volksbanken schemes, BaFin Schlichtungsstelle | EUR |
| France | ACPR (Banque de France) | AMF | Banque de France / ECB | Bank médiateurs; Médiateur de l'AMF; Médiateur de l'assurance | EUR |
| Netherlands | DNB (prudential) + AFM (conduct) | AFM | DNB / ECB | Kifid | EUR |
| Spain | Banco de España (+ ECB) | CNMV | BdE / ECB | BdE complaints service (new independent Financial Customer Authority planned - verify) | EUR |
| Italy | Banca d'Italia (+ ECB) | CONSOB | BdI / ECB | ABF (Arbitro Bancario Finanziario); ACF (CONSOB) | EUR |
| Switzerland | FINMA | FINMA | Swiss National Bank | Swiss Banking Ombudsman | CHF |
| Sweden | Finansinspektionen | Finansinspektionen | Sveriges Riksbank | ARN; Konsumenternas Bank- och finansbyrå | SEK |
| Norway | Finanstilsynet | Finanstilsynet | Norges Bank | Finansklagenemnda | NOK |
| Denmark | Finanstilsynet | Finanstilsynet | Danmarks Nationalbank | Pengeinstitutankenævnet | DKK |
| Finland | FIN-FSA (Finanssivalvonta) | FIN-FSA | Bank of Finland / ECB | FINE (Insurance & Financial Advisory Board) | EUR |
| Poland | KNF | KNF | NBP | Rzecznik Finansowy | PLN |
| UAE | CBUAE (onshore); DFSA (DIFC); FSRA (ADGM) | SCA (onshore; verify 2025 renaming) / DFSA / FSRA | CBUAE | Sanadak (financial ombudsman unit, 2024 - verify) | AED |
| Saudi Arabia | SAMA | Capital Market Authority (CMA) | SAMA | SAMA Consumer Protection ("SAMA Cares") | SAR |
| Qatar | Qatar Central Bank; QFCRA (QFC) | QFMA | QCB | QCB Consumer Protection dept | QAR |
| Egypt | CBE (banks); FRA (non-bank) | FRA | Central Bank of Egypt | CBE consumer protection / complaints | EGP |
| Turkey | BDDK (BRSA) | SPK (CMB) | TCMB | Banks Association of Turkey customer complaints committee; consumer arbitration boards | TRY |
| Israel | Bank of Israel - Banking Supervision | Israel Securities Authority | Bank of Israel | BoI Public Enquiries Unit | ILS |
| Nigeria | CBN; NDIC; SEC (capital markets) | SEC Nigeria | Central Bank of Nigeria | CBN Consumer Protection Dept; FCCPC | NGN |
| Kenya | CBK; SASRA (SACCOs) | Capital Markets Authority | Central Bank of Kenya | CBK complaints; no statutory banking ombudsman (verify) | KES |
| South Africa | Prudential Authority (SARB) + FSCA (twin peaks); NCR (credit) | FSCA | South African Reserve Bank | National Financial Ombud Scheme SA (merged from 2024 - verify); FAIS Ombud | ZAR |
| Ghana | Bank of Ghana | SEC Ghana | Bank of Ghana | BoG consumer recourse / complaints office | GHS |
| India | RBI | SEBI | Reserve Bank of India | RBI Integrated Ombudsman Scheme; SEBI SCORES; IRDAI Bima Bharosa | INR |
| Pakistan | State Bank of Pakistan; SECP (NBFCs) | SECP | SBP | Banking Mohtasib Pakistan; SECP complaints | PKR |
| Bangladesh | Bangladesh Bank; IDRA; MRA (microfinance) | BSEC | Bangladesh Bank | BB Financial Integrity & Customer Services Dept | BDT |
| Sri Lanka | Central Bank of Sri Lanka | SEC Sri Lanka | CBSL | Financial Ombudsman Sri Lanka | LKR |
| Indonesia | OJK (prudential + conduct) | OJK | Bank Indonesia (payments, monetary) | OJK consumer service; LAPS SJK (ADR) | IDR |
| Philippines | Bangko Sentral ng Pilipinas | SEC Philippines | BSP | BSP Consumer Assistance Mechanism | PHP |
| Vietnam | State Bank of Vietnam | State Securities Commission | SBV | SBV complaints; no ombudsman | VND |
| Thailand | Bank of Thailand | SEC Thailand | Bank of Thailand | BOT Financial Consumer Protection Center (1213) | THB |
| Malaysia | Bank Negara Malaysia | Securities Commission Malaysia | BNM | Ombudsman for Financial Services (OFS); SIDREC (securities) | MYR |
| Singapore | MAS | MAS | MAS | FIDReC | SGD |
| China | NFRA (National Financial Regulatory Administration) + PBOC | CSRC | People's Bank of China | NFRA consumer protection; financial dispute mediation centres | CNY |
| Hong Kong | HKMA | SFC | HKMA (de facto) | Financial Dispute Resolution Centre (FDRC) | HKD |
| Japan | Financial Services Agency | FSA + SESC; JFSA | Bank of Japan | FINMAC; Japanese Bankers Association ADR | JPY |
| South Korea | Financial Services Commission + FSS | FSC / FSS | Bank of Korea | FSS Financial Dispute Mediation Committee | KRW |
| Australia | APRA (prudential) + ASIC (conduct) | ASIC | Reserve Bank of Australia | AFCA | AUD |
| New Zealand | RBNZ (prudential) + FMA (conduct) | FMA | RBNZ | Banking Ombudsman Scheme; FSCL; IFSO; FDRS | NZD |

## Table 2 - Payments, open banking, credit bureaus

| Country | Instant payment system | Open banking / open finance | Credit bureaus |
|---|---|---|---|
| United States | FedNow; RTP (The Clearing House); Zelle overlay | CFPB s.1033 Personal Financial Data Rights rule (2024; reconsideration / litigation - verify status) | Equifax, Experian, TransUnion (+ specialty: ChexSystems) |
| Canada | Interac e-Transfer; Real-Time Rail (Payments Canada, delayed - verify) | Consumer-driven banking framework (FCAC, legislation 2024-25 - verify) | Equifax Canada, TransUnion Canada |
| Mexico | SPEI (+ CoDi, DiMo) | Fintech Law art. 76 (partially implemented - verify) | Buró de Crédito, Círculo de Crédito |
| Brazil | Pix | Open Finance Brasil (BCB) | Serasa Experian, Boa Vista, SPC Brasil, Quod; Cadastro Positivo; BCB SCR |
| Argentina | Transferencias 3.0 (interoperable QR / transfers, BCRA) | No formal framework (verify) | BCRA Central de Deudores; Veraz (Equifax); Nosis |
| Colombia | Bre-B ✓ (live 6 Oct 2025; 34 m users in 6 months) | Open finance decree 1297/2022 + SFC rules (voluntary -> mandatory roadmap - verify) | DataCrédito Experian, TransUnion Colombia |
| United Kingdom | Faster Payments | Open Banking (CMA9 order -> Open Banking Ltd); Data (Use and Access) Act 2025 smart-data / open finance (verify) | Experian, Equifax, TransUnion |
| Ireland | SEPA Instant (EU Instant Payments Regulation) | PSD2 (PSD3/PSR and FiDA pending at EU level - verify) | Central Credit Register (CBI); ICB |
| Germany | SEPA Instant; Wero (EPI) rollout | PSD2 | SCHUFA; CRIF; Creditreform |
| France | SEPA Instant; Wero | PSD2 | Banque de France FICP / FCC (negative only); no positive bureau |
| Netherlands | SEPA Instant; iDEAL (moving to Wero) | PSD2 | BKR |
| Spain | Bizum (on SEPA Inst) | PSD2 | CIRBE (BdE); ASNEF-Equifax; Experian Badexcug |
| Italy | SEPA Instant; Bancomat Pay | PSD2 | Centrale Rischi (BdI); CRIF; Experian; CTC |
| Switzerland | SIC5 instant (from Aug 2024) | Market-led open banking (bLink, SIX) - no mandate | ZEK; IKO |
| Sweden | Swish; RIX-INST (Riksbank, TIPS-based - verify) | PSD2 | UC; Creditsafe; Dun & Bradstreet |
| Norway | Straks / Vipps MobilePay | PSD2 (EEA) | Gjeldsregisteret (debt register); Experian; Dun & Bradstreet |
| Denmark | Straksclearing; MobilePay | PSD2 | RKI (Experian); Debitor Registret |
| Finland | SEPA Instant; MobilePay | PSD2 | Suomen Asiakastieto (Enento); positive credit register (Incomes Register-based, 2024-25 - verify) |
| Poland | Express Elixir; BLIK | PSD2 (PolishAPI standard) | BIK; KRD; BIG InfoMonitor; ERIF |
| UAE | Aani (Instant Payment Platform) | CBUAE Open Finance Regulation 2024 ✓ (trust framework, API hub, mandatory for CBUAE-licensed) | Al Etihad Credit Bureau |
| Saudi Arabia | sarie (IPS) | SAMA Open Banking Framework: AIS then PIS (2nd release Sep 2024), licensing 2026 ✓ | SIMAH |
| Qatar | Fawran (2024 - verify) | QCB open banking regulation (verify) | Qatar Credit Bureau |
| Egypt | InstaPay | CBE open banking rules (verify) | I-Score |
| Turkey | FAST (TCMB) | Open banking under TCMB / law 6493, API gateway (verify) | KKB (Findeks) |
| Israel | Zahav (RTGS); instant via MASAV / new instant scheme (verify) | Financial Information Services Law 2021 (open banking) | BoI Credit Data Register + licensed bureaus (BDI, others - verify) |
| Nigeria | NIP (NIBSS Instant Payments) | CBN Open Banking Regulatory Framework 2021; operational rollout 2025 (verify) | CRC Credit Bureau, FirstCentral, CreditRegistry |
| Kenya | PesaLink; M-Pesa (mobile money) | No formal framework (CBK consultations - verify) | Metropol, TransUnion Kenya, Creditinfo Kenya |
| South Africa | PayShap (+ RTC) | None yet (SARB / IFWG position paper - verify) | TransUnion, Experian, XDS, Compuscan (Experian) |
| Ghana | GhIPSS Instant Pay (GIP); mobile-money interoperability | BoG open API / guidelines (verify) | XDS Data Ghana, Dun & Bradstreet Ghana, Hudson Price |
| India | UPI; IMPS | Account Aggregator (RBI NBFC-AA, Sahamati) | TransUnion CIBIL, Experian, Equifax, CRIF High Mark |
| Pakistan | Raast | SBP open banking framework (draft / 2024 - verify) | SBP eCIB; Tasdeeq; DataCheck |
| Bangladesh | Binimoy (IDTP) | None | Bangladesh Bank CIB |
| Sri Lanka | LankaPay CEFTS / JustPay / LankaQR | None | CRIB |
| Indonesia | BI-FAST; QRIS | SNAP (Standar Nasional Open API Pembayaran, BI) | SLIK (OJK); private bureaus (Pefindo Biro Kredit, CLIK - verify) |
| Philippines | InstaPay; PESONet (batch) | BSP Open Finance Framework (Circular 1122, 2021) | Credit Information Corporation + accredited bureaus (TransUnion PH, CIBI, CRIF) |
| Vietnam | NAPAS 247 | SBV Circular 64/2024 open API (verify) | CIC (state); PCB (Vietnam Credit Information JSC) |
| Thailand | PromptPay | BOT "Your Data" open-data initiative (verify) | National Credit Bureau (NCB) |
| Malaysia | DuitNow / Real-time Retail Payments Platform (PayNet) | BNM open-finance policy work (exposure drafts - verify) | CCRIS (BNM); CTOS; Experian Malaysia |
| Singapore | FAST; PayNow | MAS Financial-Industry API guidelines; SGFinDex (government-led data sharing) | Credit Bureau Singapore; Experian Credit Bureau SG |
| China | IBPS (PBOC); NetsUnion (wallets); CIPS (cross-border RMB) | No open-banking regulation | PBOC Credit Reference Center; Baihang; Pudao |
| Hong Kong | FPS (Faster Payment System) | HKMA Open API Framework (4 phases) | TransUnion HK; Multiple Credit Reference Agencies model (verify) |
| Japan | Zengin system (24/7 since 2018) | Banking Act open-API regime (electronic payment agents, 2017) | CIC, JICC, KSC (JBA) |
| South Korea | KFTC interbank 24/7 transfers; BOK-Wire+ | MyData (Credit Information Act 2020) | KCB (Korea Credit Bureau), NICE |
| Australia | NPP (Osko, PayTo) | Consumer Data Right (banking live; energy; non-bank lending) | Equifax, Experian, illion |
| New Zealand | No national real-time scheme; Payments NZ API Centre (verify) | Customer and Product Data Act 2025 (banking first - verify) | Centrix, Equifax NZ, illion |

## Table 3 - Tax authority + e-invoicing, data protection, fraud reporting

| Country | Tax authority | E-invoicing mandate (status) | Main data-protection law | Fraud / scam reporting channel |
|---|---|---|---|---|
| United States | IRS (+ state DoRs) | None federal; voluntary (verify) | Sectoral: GLBA, FCRA; state laws (CCPA/CPRA...) | FTC ReportFraud.ftc.gov ✓ (Sentinel); FBI IC3; bank |
| Canada | CRA (+ Revenu Québec) | None (consultation on e-invoicing - verify) | PIPEDA; Québec Law 25 | Canadian Anti-Fraud Centre; police |
| Mexico | SAT | CFDI 4.0 mandatory for all | LFPDPPP (new 2025 law - verify) | CONDUSEF; Policía Cibernética; 089 |
| Brazil | Receita Federal (+ state SEFAZ, municipal) | NF-e / NFC-e / NFS-e mandatory; national NFS-e + CBS/IBS reform from 2026 (verify) | LGPD (ANPD) | Police (online B.O.); bank + Pix MED (special return mechanism) |
| Argentina | ARCA (ex-AFIP) | Factura electrónica mandatory | Ley 25.326 (AAIP) | UFECI (cyber prosecutors); police |
| Colombia | DIAN | Factura electrónica mandatory (+ payroll e-doc) | Ley 1581/2012 (SIC) | CAI Virtual (Policía Nacional) |
| United Kingdom | HMRC | None; mandatory e-invoicing announced for later (2029 - verify) | UK GDPR + DPA 2018 (ICO); DUA Act 2025 | Report Fraud (ex-Action Fraud, verify name); 7726 spam text; 159 bank line |
| Ireland | Revenue | None yet; phased B2B from 2028 aligned to ViDA (verify) | GDPR (DPC) | Garda National Economic Crime Bureau; local Garda |
| Germany | Finanzverwaltung (BZSt / Länder) | Must receive B2B e-invoices from 1 Jan 2025; issue from 2027 (>EUR 800k) / 2028 all (verify) | GDPR + BDSG | Police (Onlinewache); Verbraucherzentrale |
| France | DGFiP | Sept 2026: all must receive, large/mid issue; SMEs issue Sept 2027 ✓ (Sept 2026 start - verify go-live) | GDPR (CNIL) | 17Cyber; PHAROS; Perceval (card fraud); Info Escroqueries 0805 805 817 |
| Netherlands | Belastingdienst | B2G only; B2B via ViDA later | GDPR (AP) | Fraudehelpdesk; police |
| Spain | AEAT | Verifactu (software records, 2026-27 phased) + B2B e-invoice under Ley Crea y Crece (regulation pending - verify) | GDPR + LOPDGDD (AEPD) | INCIBE 017; Policía / Guardia Civil |
| Italy | Agenzia delle Entrate | SdI mandatory B2B/B2C since 2019 | GDPR (Garante) | Polizia Postale (commissariatodips.it) |
| Switzerland | ESTV / FTA (+ cantons) | None (QR-bill standard) | revFADP 2023 (FDPIC) | National Cyber Security Centre (BACS) report form; police |
| Sweden | Skatteverket | B2G only | GDPR (IMY) | Police; bank |
| Norway | Skatteetaten | B2G (EHF/Peppol); B2B plans (verify) | GDPR via EEA (Datatilsynet) | Police; Økokrim |
| Denmark | Skattestyrelsen | B2G (OIOUBL/Peppol); digital bookkeeping law | GDPR (Datatilsynet) | Police |
| Finland | Vero | B2G; B2B right to e-invoice on request | GDPR | Police |
| Poland | KAS / Ministry of Finance | KSeF mandatory B2B from 1 Feb 2026 (>PLN 200 m) and 1 Apr 2026 (most); penalties deferred (verify) ✓ | GDPR (UODO) | CERT Polska (incydent.cert.pl); police |
| UAE | Federal Tax Authority | E-invoicing pilot 2026, mandatory phased from 2027 (verify) | PDPL (Federal Decree-Law 45/2021); DIFC/ADGM own laws | Dubai Police eCrime; Aman; Abu Dhabi Police |
| Saudi Arabia | ZATCA (tax, zakat, customs) | FATOORA: phase 1 2021, phase 2 integration in waves | PDPL (SDAIA) | Kollona Amn app; bank; 990 (verify) |
| Qatar | General Tax Authority | E-invoicing planned (verify) | Law 13/2016 (PDPPL) | MOI Cybercrime Combating Center (Metrash2) |
| Egypt | Egyptian Tax Authority | E-invoice + e-receipt mandatory | PDPL Law 151/2020 (exec regs - verify) | MOI cybercrime unit; CBE |
| Turkey | GİB (Revenue Administration) | e-Fatura / e-Arşiv mandatory above thresholds | KVKK | Police cybercrime; USOM |
| Israel | Israel Tax Authority | Invoice allocation-number model (from 2024, thresholds falling) | Privacy Protection Law (Amendment 13, 2025) | Israel National Cyber Directorate 119; police |
| Nigeria | Nigeria Revenue Service (ex-FIRS) | Large (>N5 bn) live Nov 2025; medium 1 Jul 2026; small 2027 ✓ | Nigeria Data Protection Act 2023 (NDPC) | EFCC; NPF-NCCC; bank |
| Kenya | KRA | eTIMS mandatory for all VAT and non-VAT businesses (verify) | Data Protection Act 2019 (ODPC) | DCI cybercrime; Safaricom 333 for M-Pesa fraud (verify) |
| South Africa | SARS | None yet (VAT modernisation proposal - verify) | POPIA (Information Regulator) | SAPS; SABRIC; bank |
| Ghana | GRA | E-VAT rollout (phased) | Data Protection Act 2012 (DPC) | Cyber Security Authority (292); police |
| India | CBDT (income tax) / CBIC + GSTN | GST e-invoice (IRN) for turnover > Rs 5 crore | DPDP Act 2023 (rules 2025) | 1930 / cybercrime.gov.in (I4C); Sanchar Saathi Chakshu |
| Pakistan | FBR | Sales-tax e-invoicing / POS integration (expanding 2025 - verify) | No comprehensive law (bill pending) | NCCIA (ex-FIA Cyber Crime Wing, verify); SBP |
| Bangladesh | NBR | EFD / e-VAT (verify) | Personal Data Protection Ordinance 2025 (verify) | Police cyber unit; BB |
| Sri Lanka | Inland Revenue Department | None (verify) | PDPA 2022 (phased) | Sri Lanka CERT; CID |
| Indonesia | DJP (Coretax) | e-Faktur mandatory for VAT | UU PDP 2022 | Indonesia Anti-Scam Centre (OJK IASC); OJK 157 |
| Philippines | BIR | EIS e-invoicing phased (large taxpayers, verify) | Data Privacy Act 2012 (NPC) | CICC 1326 (AFASA 2024); PNP-ACG |
| Vietnam | General Department of Taxation | E-invoice mandatory (Decree 70/2025 -> Decree 254/2026 from 1 Jul 2026) ✓ | Decree 13/2023 + PDP Law 2025 (effective 2026 - verify) | Police (A05); tinnhiemmang.vn |
| Thailand | Revenue Department | e-Tax Invoice voluntary | PDPA 2019 | Anti Online Scam Operation Center 1441; police online |
| Malaysia | LHDN (Inland Revenue Board) | MyInvois phased 2024-26; exemption threshold raised RM1 m -> RM3 m from 1 Sep 2026 ✓ | PDPA 2010 (amended 2024) | National Scam Response Centre 997 |
| Singapore | IRAS | InvoiceNow (Peppol) phased for GST-registered from late 2025 (verify) | PDPA 2012 (PDPC) | ScamShield 1799; police e-services |
| China | State Taxation Administration | Fully digitalised e-fapiao (Golden Tax IV) rolling out nationally | PIPL 2021 (+ DSL, CSL) | 96110 anti-fraud hotline; National Anti-Fraud Center app |
| Hong Kong | Inland Revenue Department | None | PDPO (PCPD) | Anti-Deception Coordination Centre 18222; Scameter |
| Japan | National Tax Agency | Qualified Invoice System (Oct 2023); e-invoice (Peppol JP) voluntary | APPI (PPC) | Police #9110; consumer hotline 188 |
| South Korea | National Tax Service | Electronic tax invoice mandatory (corporates + individuals above threshold) | PIPA (PIPC) | 112; FSS 1332; KISA 118 |
| Australia | ATO | B2G Peppol; no B2B mandate | Privacy Act 1988 (2024 amendments) | Scamwatch / National Anti-Scam Centre; ReportCyber; Scams Prevention Framework Act 2025 |
| New Zealand | Inland Revenue | B2G Peppol | Privacy Act 2020 | Netsafe; NCSC (ex-CERT NZ) own-your-online; 7726 |

## Deposit insurance (bonus column for the packs; all from memory - verify)
US FDIC USD 250k; Canada CDIC CAD 100k; Mexico IPAB 400k UDIS; Brazil FGC BRL 250k; UK FSCS (GBP 85k -> 120k from
1 Dec 2025 - verify); EU DGS EUR 100k (all EU rows); Switzerland esisuisse CHF 100k; Norway NOK 2 m; Poland BFG
EUR 100k; Turkey TMSF; India DICGC Rs 5 lakh; Nigeria NDIC N5 m (raised 2025 - verify); Kenya KDIC KES 500k (verify);
South Africa CoDI ZAR 100k (from 2024); Malaysia PIDM RM 250k; Singapore SDIC SGD 100k; Hong Kong DPS HKD 800k;
Japan DICJ JPY 10 m; Korea KDIC KRW 100 m (from Sep 2025 - verify); Australia FCS AUD 250k; NZ DCS NZD 100k (2025);
Philippines PDIC PHP 1 m (2025 - verify); Indonesia LPS IDR 2 bn; China RMB 500k; Saudi DPF; UAE none explicit (verify).

---

# Sources (opened / returned in this research, 22 Nov 2026)
- World Bank Global Findex 2025 press release: https://www.worldbank.org/en/news/press-release/2025/07/16/mobile-phone-technology-powers-saving-surge-in-developing-economies
- World Bank blog on Findex: https://blogs.worldbank.org/en/allaboutfinance/digital-technology-is-unlocking-financial-inclusion
- IFC SME finance: https://ifc.org/smefinance ; World Bank SME finance: https://www.worldbank.org/en/topic/smefinance?amp=1 ; IFC MSME factsheet: https://ifc.org/content/dam/ifc/doc/2024/msme-s-factsheet-ifc-financial-institutions-group.pdf
- CPI, climate finance gap for small-scale agrifood (citing ISF): https://www.climatepolicyinitiative.org/publication/the-climate-finance-gap-for-small-scale-agrifood-systems/
- ISF 2025 smallholder gap: https://nextbillion.net/news/press-release-isf-advisors-launches-global-report-on-200-billion-smallholder-finance-gap-amid-rising-climate-pressures
- World Bank Remittance Prices Worldwide Q1 2025: https://remittanceprices.worldbank.org/sites/default/files/rpw_main_report_and_annex_q125_1_0.pdf ; homepage https://remittanceprices.worldbank.org/node/1
- SAVIX / VSL Associates: https://www.vsla.net ; CARE FY24 VSLA snapshot: https://care.org/wp-content/uploads/2024/10/FY24-VSLA-Annual-Report-Snapshot.pdf ; CGAP savings groups: https://www.cgap.org/blog/savings-groups
- GSMA State of the Industry on Mobile Money 2026: https://www.gsma.com/newsroom/press-release/mobile-money-accounted-for-2-trillion-in-transactions-in-2025-doubling-since-2021-as-active-accounts-continue-to-grow/
- GASA Global State of Scams 2024: https://www.gasa.org/post/global-state-of-scams-report-2024-1-trillion-stolen-in-12-months-gasa-feedzai
- FTC 2024 fraud data: https://www.ftc.gov/news-events/news/press-releases/2025/03/new-ftc-data-show-big-jump-reported-losses-fraud-125-billion-2024
- UK FOS 2024/25: https://www.financial-ombudsman.org.uk/news/financial-ombudsman-service-receives-305000-complaints-2024-25
- BIS FSI Brief 26 (gen AI in supervision): https://www.bis.org/fsi/fsibriefs26.pdf ; BIS WP 1309 suptech: https://www.bis.org/publ/work1309.htm
- OECD/INFE 2023 adult financial literacy survey: https://www.oecd.org/en/publications/2023/12/oecd-infe-2023-international-survey-of-adult-financial-literacy_8ce94e2c.html
- UNHCR refugee financial inclusion: https://www.unhcr.org/blogs/unlocking-financial-access-for-refugees-dla-piper-unhcr-june2025panel-london/ ; 2026 summary https://www.unhcr.org/sites/default/files/2026-06/UNHCR-financial-inclusion-summary-findings-2026.pdf ; GSMA 2019 Displaced & Disconnected https://www.gsma.com/mobilefordevelopment/wp-content/uploads/2019/04/Displaced-Disconnected-WEB2.pdf
- Apollo Agriculture (GSMA): https://www.gsma.com/solutions-and-impact/connectivity-for-good/mobile-for-development/blog/ai-driven-smallholder-farmer-lending-in-africa-insights-from-apollo-agriculture/ ; IFPRI AI in smallholder finance: https://www.ifpri.org/blog/the-emerging-role-of-ai-tools-in-smallholder-finance/ ; FAO agritech observatory: https://agritechobservatory.review.fao.org/fr/apollo-agriculture
- Benefits AI: mRelief https://academy.openai.com/public/blogs/turning-benefits-eligibility-into-groceries-with-ai ; Frontline Q https://www.abajournal.com/news/article/frontline-justice-and-josef-design-new-ai-tool-to-protect-public-benefits ; Nava/Imagine LA https://www.navapbc.com/news/pilot-ai-chatbot-benefits ; Code for America + Anthropic https://www.govexec.com/technology/2026/05/anthropic-code-america-pilot-ai-tools-snap/413464/ ; California caseworker assistant https://www.route-fifty.com/artificial-intelligence/2026/03/open-source-ai-assistant-shows-promise-california-caseworkers-service-delivery/412378/
- Wahed: https://techcrunch.com/?p=1500122 ; https://www.Wikipedia.org/wiki/Wahed_(company)
- Colombia Bre-B: https://banrep.gov.co/en/news/six-months-operation-bre-b-34-million-registered-users
- Poland / Belgium / France e-invoicing: https://www.vertexinc.com/node/8086 ; https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467108896/eInvoicing%2Bin%2BPoland
- Vietnam e-invoice: https://www.pwc.com/vn/en/publications/2026/260709-new-rules-einvoice-edocument.pdf
- Malaysia MyInvois threshold: https://www.hasil.gov.my/wp-content/uploads/20260830-Kenyataan-Media-HASiL_AMBANG-PENGECUALIAN-E_INVOIS-DINAIKKAN.pdf ; https://thestar.com.my/news/nation/2026/08/30/over-11-million-businesses-to-benefit-from-higher-e-invoicing-threshold-says-lhdn
- Nigeria e-invoicing: https://www.forvismazars.com/ng/en/services/tax/tax-alerts/nrs-phased-e-invoicing-rollout ; https://techcabal.com/2026/04/16/all-you-need-to-know-about-e-invoicing-in-nigeria/
- UAE open finance: https://cliffordchance.com/content/dam/cliffordchance/briefings/2024/05/uae-open-finance-regulation.pdf ; https://www.pinsentmasons.com/out-law/guides/uae-open-finance
- Saudi open banking: https://openbankingexpo.com/news/saudi-central-bank-issues-second-release-of-open-banking-framework ; https://www.clydeco.com/en/insights/2026/03/sama-new-licensing-framework-for-open-banking

Everything else (scheme names, statute numbers, hotline numbers, most country-table cells, product names Khatabook,
OkCredit, BukuWarung, Kippa, Chamasoft, DreamSave, Ensibuuko, StepChange, Credit Karma, Resolver, Monito, Lendio,
Tala, Branch) is **from memory - verify** before it reaches a user.
