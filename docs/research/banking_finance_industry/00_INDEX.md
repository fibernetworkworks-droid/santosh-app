# The banking & finance industry across the world - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A BANKING AND FINANCE INDUSTRY AI EMPLOYEES"*. Fifteenth in the series. Banking & finance here means:
retail and corporate banking, lending and NBFCs, payments and UPI, cards, wealth and investing, stock broking and capital markets, asset
and fund management, treasury, trade finance, risk/compliance/AML, accounting, audit and tax practice, SME and rural finance
(microfinance, SHGs, cooperatives), fintech and regtech, and the regulators and consumers around them. Health insurance has its own register
(`health_insurance_industry/`, HI#); general insurance and pensions appear here only as hand-offs.

**10 fields, 132 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Rules named are from
  memory and **must be re-checked on primary text per country and regulator** before any desk is built: in India RBI (KYC Master
  Direction, digital-lending guidelines, Fair Practices Code, Ombudsman scheme, NBFC scale-based regulation, payment aggregator and
  UPI/NPCI rules, Account Aggregator framework via Sahamati), PMLA and FIU-IND reporting, CKYC, credit information companies,
  SARFAESI/IBC, SEBI (stock brokers, mutual funds, PMS, investment advisers and research analysts, KRA/KYC, algo-trading rules, insider
  trading), PFRDA, IRDAI, GST/TDS/Income-tax, Companies Act and Ind AS, ICAI audit standards, FEMA/LRS, DPDP Act 2023; abroad Basel III,
  MiFID II, Dodd-Frank/SEC/FINRA/CFPB, PSD2/open banking, FATF recommendations, GDPR, the EU AI Act (credit scoring and insurance pricing
  are high-risk uses) and supervisory model-risk rules (SR 11-7-style).
- **Already in Hoola** (extend, do not rebuild): the Enterprise suite's `bank_int` desk (Banking Integration: RBI + Sahamati AA, reconcile,
  caps named in every result), `regtech` (due calendar), the Tally connector and Tally XML export, GST/Khata/HISAAB month ZIP and
  GSTR-1 JSON (appmaker), the PAISA payment gateway layer (Razorpay/Cashfree/PhonePe official APIs, refunds on her tap), UPI cards and
  UPI result handling (money moves only on her tap), broker connectors in the Bazar (Upstox/Dhan one-tap OAuth; Zerodha Kite/FYERS
  sticky MCP; Groww pending; **every order/login is her tap**), the `ins` insurance-agent employee, MoSPI official statistics,
  pylab, Data Desk, research engine, doc studio + HOOLA PRINT (statements, reports), Pehchaan Locker (masked PAN/Aadhaar),
  WhatsApp opt-in, Khata. Roles with `*` exist in some form.
- **Non-negotiables inherited from CLAUDE.md** (they are the spine of this register): money never moves without the user's tap; Hoola
  never asks for or accepts PIN, OTP, CVV, card numbers or passwords in chat; broker access is "caution"; official routes only; no
  personal-WhatsApp automation; ID numbers only through the locker with masked references.

## The findings that shape every finance desk
### 1. Finance is the most regulated industry: every act has a licensed decider, and money movement is the line Hoola never crosses
Ladder as before: **A** admin/prepare, **B** assist (check / draft / explain / calculate for a named person), **C** reserved.
Reserved here: moving money or placing an order on its own (only on the user's tap, through the user's own account or the bank's
rails), approving or declining a loan, deciding a claim, giving personalised investment, tax or insurance advice without the registered
adviser/CA in the loop, filing an STR/SAR (the money-laundering reporting officer), signing audit opinions or financial statements,
onboarding a customer (KYC accept/reject), freezing an account, regulatory filings, and any trading decision (algos need registered
strategy and risk controls). **The AI prepares, checks, explains and reminds; the registered person decides and the customer taps.**

### 2. Customers' pain is jargon, fees, scams, paperwork and bad advice
Hidden charges, mis-selling, loan trap terms, KYC loops, EMI stress, UPI frauds and fake loan apps, delayed refunds, tax confusion,
investment tips from social media. An AI that stands on the **customer's** side (reads the terms, shows total cost, flags red flags,
tracks due dates, drafts the complaint, explains the tax effect, refuses to push a product) is useful and consistent with Hoola's brand.
Fraud is the #1 consumer harm in Indian digital finance: scam warning is a feature.

### 3. Institutions drown in compliance, reconciliation and exceptions
Banks and NBFCs spend most operating cost on onboarding/KYC, collections, reconciliations, regulatory returns, audit trails and
customer service. Document-heavy, rule-based, exception-driven: tier A/B with a human decision on every adverse outcome. Fairness
matters: models may not discriminate (caste, religion, gender, locality proxies), must be explainable (reasons for denial), and need
model-risk governance (inventory, validation, drift, override rates).

### 4. Markets: Hoola is a research and discipline tool, never a tipster
SEBI regulates advice: investment advice needs a registered adviser, research needs a registered analyst, algos need broker approval.
An AI Employee can explain products, track the portfolio, compute risk, show sources, remind of goals and costs, and place an order only
on the user's confirmed tap through a broker's official API. It never promises returns, never says "buy/sell this" as advice, never uses
non-public information, and discloses that it is not a registered adviser.

### 5. Trust architecture: audit, explainability, kill-switches
Every action leaves an immutable trail (who/what/why/data used); every output shows its basis; every adverse decision has a reason a
customer can contest and a human reviewer; every autonomous flow has caps, rate limits and a kill switch; secrets never enter the model.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [C] consumer/individual, [B] bank/NBFC/lender, [M] markets/wealth/funds, [F] firm finance/CA/tax, [S] SME/rural/microfinance, [R] regulator/policy.

### 1. Personal finance & consumer protection  [C]
1. Money Manager - income/expense tracking from the user's own statements (via Account Aggregator consent or uploads), budgets, bills calendar, UPI summaries, goals; read-only - A - user
2. Fee & Charges Auditor - reads bank/card statements for fees, interest, forex mark-ups, penal charges; shows total cost; drafts a dispute - A - user
3. Loan Reader & Comparator - EMI, APR/XIRR, processing fees, prepayment and foreclosure rules, insurance add-ons, balloon traps; shows the total cost; refuses to push a lender - A - user
4. Credit Score Coach - explains the report (utilisation, enquiries, delinquencies), dispute steps for errors, safe improvement plan; no "score guarantee" - A - user
5. Debt Repayment Planner - snowball/avalanche, cash-flow stress tests, negotiation script, credit counselling pointers (pylab) - A - user
6. Fraud & Scam Shield - checks messages/calls/links for known scam patterns (fake KYC, loan-app harassment, investment groups, "UPI refund", sextortion), explains actions: block, report to 1930/cybercrime, bank hotline; **never asks the user for OTP/PIN** - A/B - user
7. UPI & Payment Safety Coach - explains collect-request traps, QR traps, limits, dispute window, chargeback steps - A - user
8. Complaint & Ombudsman Drafter - bank/NBFC grievance ladder: bank nodal officer, Ombudsman portal, evidence list, timelines; drafts letters - A/B - user
9. KYC Helper - checklist for bank/broker/MF KYC, CKYC, Aadhaar-masked flow, video-KYC prep; **onboarding decisions by the institution** - A - user
10. Family Finance Vault - accounts, policies, nominees, loans, subscriptions, passwords never stored, document locker; emergency sheet for family - A - user
11. Tax Companion (individual) - income sources, deductions, TDS (Form 26AS/AIS reconciliation), advance tax dates, ITR data prep; **filing by the user/CA** - B - user / CA
12. Home-buying Finance Planner (EMI vs rent, stamp duty, TDS on purchase, loan eligibility ranges; links to real-estate register) - A - user
13. Retirement & Pension Planner (NPS/EPF/PPF/annuity basics, corpus ranges, inflation, sequence risk; not advice) - A/B - user
14. Student-loan & Education Finance Assistant (loan types, interest subvention, tax benefit, repayment plan) - A - student/parent
15. Senior-citizen Finance Guard (scam alerts, nominee updates, safe-banking habits, family notification with consent) - A/B - senior/family
16. NRI Finance Navigator (NRE/NRO/FCNR, FEMA/LRS limits, DTAA basics, repatriation steps; **CA confirms**) - B - NRI / CA
17. Gold & Savings Product Explainer (SGB, digital gold, FDs, RDs: rates, tax, liquidity, risks) - A - user

### 2. Retail & commercial banking operations  [B]
18. Customer Service Agent (voice/WhatsApp/web: balance, statement, card block request routing, branch locator, FAQs; escalates; no sensitive data in chat) - A - contact-centre head
19. Account-opening Assistant (document collection, form fill, checks completeness, status; **approval by bank**) - A - branch / digital onboarding
20. KYC/CDD Reviewer's Assistant (document authenticity checks, name matching, adverse media hints; risk rating *suggestion*; **KYC officer decides**) - B - KYC officer
21. Periodic KYC Refresh Manager (due list, outreach, document handling) - A - KYC ops
22. Branch Operations Assistant (queue, cash planning, forms, audit checklists, appointment booking) - A - branch manager
23. Card Operations Assistant (dispute intake, chargeback documents, card replacements, limits requests routed) - A - card ops
24. Dispute & Chargeback Analyst (evidence packages for networks, deadlines, reason codes) - A/B - disputes team
25. Back-office Reconciliation Assistant (nostro/vostro, ATM, payment rails, GL, suspense-item ageing; break classification) - A/B - ops
26. Cash & ATM Logistics Planner (cash forecasting, replenishment routes with Maps, vault limits) - A - cash ops
27. Statement & Letter Generator (certificates, interest letters, balance confirmation, multilingual; template control) - A - ops
28. Customer Complaint Handler (classification, SLA clock, root cause tagging, regulator report prep; **final response by the officer**) - A/B - grievance officer
29. Collections Assistant (early-bucket reminders within RBI recovery rules: timing, language, no harassment; settlement offers within policy; **hardship decisions human**) - B - collections head
30. Employee Banking Copilot (policy lookups, product rules, circular summaries with source) - A - frontline staff

### 3. Lending: retail, MSME, NBFC & digital lending  [B]
31. Loan Application Intake (documents, income proofs, bank-statement analysis via AA with consent, completeness) - A - loan officer
32. Underwriter's Assistant (cash-flow tables, bureau summary, ratio analysis, policy rule hits, exception list; shows reason codes; **credit decision reserved**) - B - credit officer
33. Alternate-data Cash-flow Analyst (GST returns, bank flow, UPI patterns with consent; stability ranges; fairness-tested) - B - credit analyst
34. Credit Memo Drafter (borrower profile, financials, risks, covenants, structure; **credit committee approves**) - B - credit officer
35. Collateral & Legal Verification Packager (title search index, valuation report receipt, charge creation checklist, CERSAI; **legal opinion by empanelled advocate**) - A/B - legal officer
36. Loan Documentation Assistant (agreements from templates, KFS/key fact statement for digital lending, schedule of charges; **sanction letter by authorised person**) - B - loan ops
37. Disbursement & Post-sanction Checker (conditions precedent list, end-use checks, insurance, NACH mandates; **release by the bank on authorised approval**) - A - loan ops
38. Early-warning Watcher (EWS: GST filing gaps, cheque bounces, sector stress, covenant breaches; flags only) - B - risk monitoring
39. NPA & Recovery Case Assistant (ageing, notices under SARFAESI/IBC steps, auction notices, legal chronology; **action by recovery/legal**) - B - recovery head
40. Digital-lending Compliance Guard (LSP agreements, consent logs, KFS, cooling-off, no unauthorised access to contacts/photos, grievance redress, data localisation checks) - B - compliance officer
41. Co-lending Reconciler (share splits, interest, servicing fees, remittances) - A - finance ops
42. Microfinance Group Loan Assistant (JLG/SHG cycles, attendance, collections, over-indebtedness checks, borrower-protection rules; **no coercive recovery**) - A/B - field officer
43. Gold-loan Operations Assistant (valuation sheets, LTV, auction notices, insurance; **assayer values**) - A - branch
44. Vehicle & Equipment Finance Assistant (dealer docs, RC/insurance, hypothecation records) - A - loan ops
45. Supply-chain Finance Assistant (invoice discounting: invoice verification via e-invoice/GST, buyer confirmation, dilution tracking) - B - SCF desk
46. Trade-finance Document Checker (LC/BG documents vs terms, UCP 600/URC rules lists; **bank officer examines**) - B - trade operations
47. Project & Corporate Lending Analyst (cash-flow models, DSCR, sensitivities, covenants; pylab) - B - credit analyst
48. Borrower Education Assistant (repayment rights, fair practices, grievance) - A - lender

### 4. Payments, UPI, cards & fintech infrastructure  [B]
49. * Payments Reconciliation Assistant (gateway settlements vs orders/bills; Razorpay/Cashfree/PhonePe APIs; refunds only on tap) - A - merchant / finance
50. Merchant Onboarding Assistant (KYC docs, business checks, MCC, risk tiers; **acquirer decides**) - A/B - payment aggregator ops
51. Payment Fraud Detector (velocity, device, geo, mule patterns; explainable rule hits; **block/release by risk analyst**) - B - fraud analyst
52. Chargeback & Refund Desk (rules by network, evidence, timelines) - A - merchant ops
53. UPI Dispute & Mandate Assistant (autopay mandates, UDIR dispute flows, NPCI reason codes) - A - operations
54. Settlement & Float Monitor (T+x, nodal account positions, escrow rules; **treasury decisions human**) - B - treasury ops
55. Open-banking / AA Integration Assistant (consent artefacts, FIP/FIU schemas, testing; `bank_int` lane) - A/B - integration lead
56. API Gateway & Partner Manager for Banks (sandbox, keys rotation reminders, certification checks) - A - platform team
57. Wallet & Prepaid Instrument Compliance Checker (KYC tiers, limits, interoperability, escrow) - B - compliance
58. Cross-border Payments Assistant (purpose codes, LRS/FEMA checks, SWIFT message drafts; **authorised dealer decides**) - B - forex ops

### 5. Wealth, investing & asset management  [M]
59. Portfolio Tracker (read-only consolidation of demat/MF/NPS/FD via CAS/AA; P&L, XIRR, asset allocation, fees; connectors only on her tap) - A - investor
60. Goal-based Planner (goals, time horizons, SIP maths, inflation, scenario ranges; not advice) - A/B - investor
61. Mutual-fund Research Desk (factsheet reader, expense ratio, tracking error, manager history, overlap, risk metrics from AMFI/AMC disclosures; shows sources) - A - investor
62. Risk Profiling Assistant (questionnaire with suitability notes; **registered adviser finalises**) - B - adviser
63. Registered Investment Adviser's Copilot (client meeting prep, KYC/risk profile, model portfolios, rebalance proposals, suitability documentation; **adviser signs**) - B - RIA
64. Research Analyst's Assistant (filings summarisation, comps tables, model checking; **analyst publishes with disclosures**) - B - SEBI-registered analyst
65. Portfolio Manager's Assistant (PMS: mandate checks, drift, trade proposals; **PM decides; compliance pre-checks**) - B - portfolio manager
66. Order Placement Assistant (prepares an order ticket from the user's instruction, shows charges/risks, requires explicit confirm tap via broker's official API; no discretionary trading) - A - investor
67. Tax-loss & Capital-gains Planner (lots, holding periods, set-off rules, advance tax; **CA confirms**) - B - investor / CA
68. SIP & Rebalancing Reminder (bands, thresholds, costs; no auto-trades without tap) - A - investor
69. Fund Operations Assistant (NAV checks, corporate actions, reconciliation, fee calculation; **fund accountant signs**) - A/B - fund ops
70. Alternative-investment Due-diligence Assistant (AIF/REIT/PE: disclosure completeness, fee waterfall, liquidity; flags unregulated schemes) - B - analyst
71. Investor-onboarding & Suitability Document Assistant (KYC, risk, FATCA, nomination) - A - wealth ops
72. Wealth-client Relationship Manager (family tree, events, tax calendar, philanthropy; consent) - A - private banker
73. Retail Investor Education Coach (basics of equity, debt, risk, scams, SEBI rules; myths vs facts; no stock tips) - A - public

### 6. Capital markets, broking & trading  [M]
74. Broker Back-office Assistant (contract notes, margin statements, settlement obligations, client funds reconciliation, ledger checks) - A - broker ops
75. Margin & Risk Monitor (exposure, concentration, intraday alerts to the RMS desk; **square-off decisions by risk team**) - B - risk manager
76. Trade Surveillance Assistant (market-abuse patterns: spoofing, layering, front-running, client-code changes; alerts with evidence; **compliance reviews**) - B - surveillance officer
77. Client Suitability & Complaint Handler for Brokers (SCORES, arbitration prep, logs) - A/B - compliance
78. Algo Strategy Documentation & Testing Assistant (strategy spec, backtest, risk limits, kill-switch checks; broker/exchange approval required; **no unapproved algos**) - B - quant lead
79. Order-routing Best-execution Analyst (slippage, venue stats; reports) - B - trading head
80. IPO / Primary-market Assistant (application checklists, UPI mandate steps, allotment status; no allotment guessing) - A - investor / merchant banker
81. Merchant Banker's Document Assistant (DRHP section drafts from company data, due-diligence checklists; **banker and company sign**) - B - merchant banker
82. Derivatives Education & Risk Explainer (payoff diagrams, margin, Greeks basics, loss-rate stats from SEBI studies; warnings) - A - retail investor
83. Corporate Actions Tracker (dividends, splits, rights, buybacks; election deadlines) - A - investor / ops
84. Market Data & Event Digest (results calendar, macro releases, filings; neutral summaries with sources) - A - investor
85. Quant Research Assistant (factor tests, backtesting in pylab, overfitting checks, transaction-cost realism; hypotheticals labelled) - B - quant researcher
86. Treasury Front-office Assistant (rates, curves, hedging scenarios, limits monitoring; **dealer decides**) - B - treasurer

### 7. Risk, compliance, audit & regulatory technology  [B/R]
87. AML Transaction Monitoring Triage (alerts clustered, false-positive reduction, narrative drafts for analysts; **STR filing by the MLRO**) - B - AML analyst
88. Sanctions & PEP Screening Assistant (name matching with explainable scores; true-match decisions by compliance) - B - compliance
89. Regulatory Change Watcher (RBI/SEBI/IRDAI/PFRDA/NPCI circulars -> impact list, owners, deadlines) - A - compliance head
90. Regulatory Return Preparer (data pulls to templates, reconciliation, checks; **submission by authorised officer**) - A/B - reporting head
91. Model Risk & AI Governance Officer (model inventory, validation packs, bias and drift monitoring, override rates for every tier-B employee) - B - model risk committee
92. Credit-risk Analytics Assistant (PD/LGD/EAD data prep, stress testing under supervisory scenarios, IFRS 9/Ind AS 109 ECL working papers; **risk committee approves**) - B - risk head
93. Market & Liquidity Risk Reporter (VaR, LCR/NSFR calculations, limit breaches; pylab) - B - ALM
94. Operational Risk & Incident Assistant (loss events, near misses, RCA templates, BCP tests) - A/B - op-risk
95. Internal Audit Assistant (sampling, test scripts, evidence index, draft findings; **audit head signs**) - A/B - internal auditor
96. Fraud Investigation Assistant (timeline, link analysis, evidence packet, interview questions; **allegation reserved**) - B - fraud investigator
97. Cyber & Third-party Risk Assistant (vendor questionnaires, access reviews, incident drills, DPDP breach notice drafts) - B - CISO
98. Whistleblower & Ethics Channel (anonymous intake, triage, protection rules) - B - ethics officer
99. Conduct & Mis-selling Reviewer (call/chat samples vs suitability rules; coaching, not punishment by AI) - B - compliance
100. Policy & Procedure Librarian (version control, change impacts, staff attestations) - A - compliance

### 8. Accounting, audit, tax & corporate finance (CA firms, company finance teams)  [F]
101. * Bookkeeping Assistant (bank-feed matching, ledger coding, vouchers; Tally XML/Khata/HISAAB; GST invoices) - A - accountant
102. GST Return Preparer (GSTR-1/3B data, ITC reconciliation vs 2B, mismatch list; **filing by taxpayer/CA on tap**) - B - CA
103. TDS/TCS Compliance Assistant (sections, rates, thresholds, challans, 24Q/26Q data, notices) - B - CA
104. Income-tax Notice Responder (draft replies from facts and law references; **CA signs**) - B - CA
105. Statutory Audit Assistant (sampling, confirmations, working-paper index, ratio analysis, going-concern indicators; **auditor opines**) - B - auditor
106. Financial Statements Preparer (Ind AS/IFRS notes drafts, consolidation checks, tie-outs; **management and auditor sign**) - B - financial controller
107. FP&A Analyst (budgets, forecasts, variance analysis, rolling cash-flow, scenarios; pylab) - A - finance head
108. Month-end Close Manager (checklists, accruals, intercompany eliminations, flux explanations) - A - controller
109. Treasury & Cash Pooling Planner (cash visibility, FX exposure, short-term investments policy; **CFO decides**) - B - treasurer
110. Payables & Receivables Desk (invoice matching, payment runs on approver tap, ageing, collections reminders) - A - finance ops
111. Expense & Travel Audit Assistant (policy checks, duplicates, receipts, fraud flags) - A/B - finance ops
112. Valuation Assistant (DCF/comps worksheets, sensitivity tables, data sources; **registered valuer signs**) - B - valuer
113. Cap-table & Equity Compensation Assistant (ESOP schedules, vesting, valuations inputs, 409A-style/FMV prompts, board resolutions drafts; **legal** ) - B - CFO / counsel
114. M&A Due-diligence Coordinator (data-room indices, request lists, financial red flags, working-capital checks) - B - deal team
115. ESG & Sustainability Finance Reporter (BRSR data, emissions, taxonomy mapping, evidence; assurance by assurer) - B - ESG lead
116. Company Secretary's Assistant (ROC filings data, board minutes, resolutions, registers, compliance calendar; **CS certifies**) - A/B - company secretary
117. CA Practice Manager (clients, deadlines, document requests via WhatsApp, fee billing, notices tracker) - A - CA firm
118. Startup Finance Copilot (burn, runway, fundraising materials, grants/schemes, compliance map, founder basics) - A/B - founder / CFO

### 9. SME, rural & inclusive finance  [S]
119. Small Business Finance Assistant (bookkeeping, GST, working-capital planning, loan options, scheme eligibility like MUDRA/CGTMSE; **lender decides**) - A - owner
120. Invoice & Receivables Chaser (reminders, ageing, e-invoices, factoring options, Khata) - A - SME
121. SHG/Cooperative Accountant (savings, loans, meeting minutes, audit tallies, bank linkage) - A - SHG / cooperative
122. Rural Credit Navigator (KCC, crop loans, interest subvention, insurance links; farm register cross-ref) - A - farmer / officer
123. Financial Inclusion Business-correspondent Assistant (BC agent: customer onboarding, cash-in/out logs, limits, fraud alerts, commissions) - A/B - BC agent
124. Women-entrepreneur Finance Coach (schemes, SHG linkage, business plans, bank visits prep) - A - coach / NGO
125. Gig-worker Finance Companion (irregular income smoothing, tax, insurance, emergency fund, UPI-wise tracking) - A - gig worker
126. Remittance & Migrant-worker Money Guide (cheap transfer options, scam warnings, family budgeting) - A - migrant worker

### 10. Regulators, policy & education  [R]
127. Supervisory Analyst's Assistant (returns analysis, thematic reviews, inspection prep; **supervisory action by the regulator**) - B - supervisor
128. Consumer Protection Case Assistant (complaint triage, pattern detection across banks, escalation to inspection) - B - regulator ombudsman office
129. Financial Literacy Educator (school/college/community modules, local-language voice, scam drills; Guru Sahayak) - A - educator
130. Policy & Economic Research Assistant (inflation, credit growth, FX, fiscal tables from MoSPI/RBI/IMF with sources; pylab) - A - analyst
131. Financial Inclusion Impact Evaluator (survey design, outcomes, causal checks, honest limits) - B - researcher
132. Cybercrime Helpline Assistant (intake of financial fraud complaints, evidence checklist, bank liaison steps, 1930 flows) - A/B - police cyber cell

## NEVER an AI Employee (tier C)
Move money, place or cancel an order, change a mandate, or approve a payment without the account holder's explicit tap through
official rails; ask for or store PIN, OTP, CVV, card numbers or passwords; approve or deny a loan, card, claim or account;
accept or reject KYC; freeze an account; file an STR/SAR or any regulatory return as the institution; give personalised investment,
tax, legal or insurance advice as if registered; guarantee returns or tell anyone to buy/sell a security; trade on non-public
information; run an unapproved algo; sign an audit opinion, financial statement, valuation or certificate; recover a debt by
threats or contacting third parties against rules; discriminate on protected traits; read contacts/photos/SMS of a borrower beyond
consent; scrape bank or broker portals against their terms.

## Suggested build order
1. **Wave 1 - consumer protection and books (tier A, read-only, high trust value)**: 1-3, 6-8, 10, 49, 59, 61, 101, 102, 107, 117, 119-121.
2. **Wave 2 - institution assist with a named decider**: 9, 11, 18-21, 28, 29, 31-34, 40, 55, 60, 62, 63, 66, 87-91, 103-106, 110.
3. **Wave 3 - regulated, high-impact or market-sensitive**: 32, 36, 39, 42, 51, 64, 65, 75-78, 81, 92, 96, 112-114, 127.
Fit to Hoola: department **"Finance & Banking"**; start with the **consumer** employees (they need no institution): a **Paisa Sahayak** that
reads statements (AA/uploads), warns about scams, compares loans, tracks the portfolio read-only and drafts complaints - then extend the existing
`bank_int`, `regtech`, Tally, GST/HISAAB and PAISA layers for SMEs and CA firms. Reuse Account Aggregator (via `bank_int`), UPI cards, broker
connectors (tap-only), Khata, pylab (3, 5, 13, 60, 85), the research engine with citations (89, 130), Pehchaan Locker (masked IDs), WhatsApp
opt-in (29, 120), HOOLA PRINT (statements, credit memos), approval cards for every payment, order, filing and signature, the voice stack for
scam warnings in Indian languages, and Hoola's **audit trail + caps + kill switches** as the compliance proof.
**Best first pilots**: (a) the **consumer Paisa Sahayak** (1-8, 59, 61) - viral, trust-building, no regulator signs anything, and fraud
protection is a daily need; (b) a **small CA firm or accounting practice** (101-104, 117) - GST/TDS notice pains, WhatsApp document
chasing, Tally; (c) an **SME owner** (119-121). Banks and NBFCs come later: procurement, security audits and model-risk governance are heavy.

## Open questions for the owner
- Which side first: **consumers**, **SMEs and CA firms**, **banks/NBFCs**, **wealth/broking**, or **rural/inclusive finance**? I'd start with consumers
  plus CA firms because they need no institution's approval.
- Advice boundary: confirm Hoola stays an **education and tracking** tool (no personalised "buy/sell" or tax advice) unless a SEBI-registered
  adviser or a CA is in the loop; consider whether Newtika wants a registered RIA partner for assist-with-adviser features.
- Data access: Account Aggregator consent flows, bank/broker official APIs only, no screen-scraping; confirm DPDP consent text and retention.
- Money rule: confirm Hoola never initiates a payment or order without the user's explicit tap, even for scheduled items (reminders only).
- Fairness and explainability: confirm that credit-related employees show reason codes and are tested for bias before any lender pilot.
- "GO per field" turns any field into a sourced report with RBI/SEBI/PMLA/IRDAI text checked on primary documents.
