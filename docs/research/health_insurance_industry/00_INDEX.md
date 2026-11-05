# The health insurance industry, function by function - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A HEALTH INSURANCE INDUSTRY AI EMPLOYEE LIST"*. Seventh in the series after `healthcare_industry/`
(160 roles), `pharmacy_industry/` (118), `hospital_industry/` (128), `medical_devices_industry/` (118),
`diagnostics_industry/` (108) and `medical_education_industry/` (107). This one is the money side: the insurer, the
third-party administrator (TPA), the broker/agent/POSP, the government scheme, the employer's group plan, the
reinsurer, the claims-exchange platform, and the aggregators and insurtech around them. Payer roles already in earlier
registers (HC#94-103, HO#78-85, PH-side claims) are cross-referenced and not counted.

**13 fields, 108 candidate AI Employees.**

## How honest this is
- No new web research for this file. It is **domain knowledge, not a sourced census**. Rules named are from memory and
  **must be re-checked on primary text** before building: IRDAI (Health Insurance regulations and the 2024 master
  circular on health insurance business - cashless, claim settlement timelines, grievance, standardisation), Insurance
  Act 1938, Protection of Policyholders' Interests regulations, IRDAI TPA and broker/POSP rules, Insurance Ombudsman
  Rules 2017, NHCX (National Health Claims Exchange) and ABDM, PM-JAY / state schemes / CGHS / ECHS / ESIC rules,
  GST on premiums, DPDP Act 2023. Abroad: US ACA, CMS-0057-F prior-auth timelines, HIPAA, state insurance law (NAIC),
  EU/UK conduct rules, Solvency II for reinsurers. Several Indian circulars were revised in 2024-2025: check dates.
- Nothing is built. Hoola's relevant plumbing today: the Bazar insurance connectors, `ins` lane (policies/premium
  reminders, renewals - an agent-side desk already exists in `employee/roles.py`: "insurance agent"), Khata ledger,
  WhatsApp opt-in campaigns, document reading, Data Desk + pylab, `health_int` (HL7 / FHIR / ABDM), approval cards.

## The findings that shape every health-insurance desk
### 1. The decision rights are the product and they are regulated
Ladder as before: **A** admin/prepare, **B** assist (flag / draft for a named human), **C** reserved. Reserved here:
underwriting acceptance/decline/loading, claim denial or repudiation, claim settlement amount sign-off, fraud
accusation, policy cancellation, medical opinion on necessity, reserving and pricing sign-off by the appointed
actuary, regulatory filings, and anything that gives advice on suitability without the licensed adviser. Rule in the
US/EU/India alike: **an AI may speed up, never be the sole basis of a denial** (CMS WISeR keeps clinician decisions;
IRDAI expects human-reviewed rejections with reasons; EU AI Act classes insurance pricing/underwriting of health as
high-risk). Every denial letter must carry a human name and reasons the customer can contest.

### 2. The customer's pain is the claim: delay, rejection, jargon, paperwork
Policyholders buy cover once and meet the insurer on the worst day. Most pain is: which documents, which hospital is
cashless, why was it cut (co-pay, room-rent proportionate deduction, non-payables, sub-limits, waiting periods,
pre-existing), how long, who do I call. An AI Employee that stands on the **customer's** side (checks documents before
filing, explains deductions in plain language, tracks the clock, escalates to the grievance ladder / Ombudsman) is
useful and lawful, and Hoola's brand is exactly "your avatar works for you".

### 3. Three sides, three different buyers
- **Insurer / TPA** (claims cost, fraud, speed, regulators)
- **Intermediary** (agent, broker, POSP, bank-assurance, aggregator, employer HR)
- **Policyholder / hospital / employer** (cashless pre-auth, final bill, reimbursement, renewals)
A feature that is a win for one can be a loss for another (faster fraud detection vs faster payout). The register tags
the seat each role serves in the first bracket.

### 4. Data and fairness are the regulated edge
Health data is special-category (DPDP, HIPAA, GDPR). Underwriting AI that uses health, genetics or lifestyle can
discriminate; pricing models need explainability, no proxies for caste/religion/disability, and audit trails. Rule-based
checks with printed reasons beat black boxes. Hoola's pattern: every flag shows its rule and its source.

---
## THE REGISTER  (seat - AI Employee - what it does - tier - the human who decides)
Seats: [I] insurer / TPA, [X] intermediary, [P] policyholder / hospital / employer, [G] government scheme, [R] reinsurer / regulator.

### 1. Product design, pricing & actuarial
1. [I] Product Design Assistant - benefit grids, exclusions, waiting periods, sub-limits drafted from the filed template and IRDAI standardisation; **filing by the appointed actuary / compliance** - B - product head
2. [I] Competitor Product Benchmarker - plan features, premiums, claim ratios across insurers from public documents - A - product head
3. [I] Pricing Data Preparer - claims, exposure, trend and loadings tables cleaned and reconciled (pylab); **rate sign-off by the appointed actuary** - A - actuary
4. [I] Experience Analyst - loss ratios, claim frequency/severity by age, city, hospital tier, disease cluster; run-off triangles - A - actuary
5. [I] Medical Inflation & Hospital-price Watcher - tariffs, procedure price trends, device price ceilings - A - actuary
6. [I] Reserving Assistant - IBNR triangles, method comparison tables; **reserve sign-off reserved** - B - appointed actuary
7. [I] Pricing Fairness Auditor - tests rating factors for proxy discrimination and unexplainable jumps - B - chief risk officer
8. [R] Reinsurance Treaty Analyst - cession tables, large-loss lists, bordereaux checks - A - reinsurance manager
9. [I] Wellness-programme Designer - rewards design, incentive caps, evidence sources (no pressure to disclose conditions) - B - product + compliance

### 2. Distribution: agents, brokers, POSPs, banks, aggregators, employers
10. [X] Needs Analysis Assistant - family, income, city, existing cover, conditions asked as a structured form; suggests *questions to ask*, not a recommendation - A - licensed adviser
11. [X] Plan Comparison Explainer - side-by-side of premium, cover, room-rent cap, co-pay, waiting periods, network hospitals, claim-settlement history, in plain Hinglish; **suitability call by the adviser** - B - agent / broker
12. [X] Quote & Proposal Form Filler - fills the proposal from the customer's documents, flags missing/contradictory answers; **customer signs the declaration** - A - agent
13. [X] Material-facts Checker - prompts about pre-existing disease disclosure so the customer does not under-declare (most rejected claims start here) - B - agent / customer
14. [X] KYC & Document Collector (Aadhaar-masked, PAN, bank, medical reports; Pehchaan Locker rules) - A - agent
15. [X] Lead Qualifier & Follow-up Scheduler (opt-in WhatsApp, call-back slots, no cold-spam) - A - agent
16. [X] POSP Training Companion - IRDAI POSP syllabus, product knowledge quizzes, mock exam - A - POSP
17. [X] Renewal Reminder & Portability Advisor - upcoming renewals, no-claim bonus, portability window rules, premium history (the existing `ins` lane) - A/B - agent
18. [X] Agent Commission & Compliance Tracker - commissions, clawbacks, mis-selling complaint log; licence/CE renewal - A - principal officer
19. [X] Aggregator Comparison Compliance Checker (claims honest ranking, sponsored-label rules) - B - compliance
20. [P] Group Policy Benchmarker for Employers (cover per head, sum insured, maternity, parents, premium, claims ratio, TPA scorecard) - A - HR head
21. [P] Employee Benefits Helpdesk (enrolment windows, add dependents, e-cards, FAQs, who-to-call; empowers HR) - A - HR

### 3. Underwriting & policy administration
22. [I] Proposal Intake Triage - completeness, ID match, simple rule-based routing to auto-accept / medical / refer; **decline is human** - B - underwriter
23. [I] Medical Report Reader - extracts values from pathology/ECG/discharge summaries into structured fields with page cites - A/B - underwriter
24. [I] Underwriting Rule Engine Explainer - shows which rule fired (age band, BMI, HbA1c, smoking), the manual page, the loading table - B - underwriter decides
25. [I] Referral Case Summariser - one-page brief of the file with the open questions - B - senior underwriter
26. [I] Policy Issuance & Endorsement Clerk (schedule, e-card, member add/delete, address/nominee change with proof) - A - policy servicing
27. [I] Free-look & Cancellation Handler (refund calc, proof, timelines) - A - servicing
28. [I] Premium Collection & Mandate Tracker (e-mandate, bounce chase, grace-period alerts, GST invoice) - A - finance
29. [I] Renewal Underwriting Reviewer (post-claim re-rating rules vs IRDAI limits; **no unfair loading**) - B - underwriter
30. [I] Portability & Migration Intake Assistant - accepts the previous insurer's data, credits waiting periods per rule - A/B - underwriter
31. [I] Genetic/Wearable Data Guard - blocks use of data that the law or the insurer's filed policy does not allow - B - compliance

### 4. Cashless, pre-authorisation & hospital network
32. [P] Pre-auth Packager for Hospitals - fills the cashless request from the chart: diagnosis, planned procedure, estimate, doctor, ICD/package code, attachments (HO#80) - A/B - TPA desk
33. [I] Pre-auth Reviewer's Assistant - checks policy status, waiting period, sub-limits, package rates, medical necessity criteria against the filed guideline; **approval/denial human** - B - medical officer
34. [I] Query/Enhancement Responder (hospital replies to insurer queries; drafts from chart) - B - TPA desk (HO#81)
35. [P] Cashless Eligibility Checker for the Patient (is this hospital in network, estimated co-pay, room-rent cap) - A - patient / front desk
36. [I] Network Hospital Onboarding Assistant (empanelment documents, tariff comparison, NABH/NABL check, geo-coverage map) - A - provider relations
37. [I] Hospital Tariff Benchmarker (same procedure across hospitals; outlier prices flagged) - A/B - provider relations
38. [I] Network Quality Scorecard (claims turnaround, complaint rate, readmission rate, overcharging flags) - B - network head
39. [P] Final Bill Auditor for Hospitals (non-payables, package vs actual, discharge docs; HO#82) - A - billing
40. [I] Discharge Authorisation Clock (live pre-auth/discharge timers; the 2-hour discharge-approval-style rules where they apply, alert to a person) - A - claims desk
41. [G] PM-JAY / State Scheme Pre-auth Desk (HBP package selection, mandatory documents, photos, geo-tagged evidence, auto-approval windows) - A/B - scheme desk

### 5. Claims management
42. [I] Claim Intake & Document Completeness Checker (OCR, required-document list by claim type, missing-item request letter) - A - claims desk
43. [I] Claim Registration Clerk (policy match, member, hospital, dates, ICD/CPT mapping proposal) - A - claims desk
44. [I] Medical Scrutiny Assistant - timeline of admission, investigations, procedure; compares with the diagnosis/package; flags gaps, not conclusions - B - claims medical officer
45. [I] Coverage & Exclusion Checker - waiting periods, pre-existing disease rules (with moratorium), room-rent proportionate deduction math, co-pay, sub-limits; every line shows its clause - B - claims adjudicator
46. [I] Payable Amount Calculator (itemised, non-payables list, tariff cap, deductible; transparent worksheet) - A - claims desk
47. [I] Rejection-letter Drafter (reason, clause quoted, documents considered, appeal path, ombudsman details; **signed by a named decision-maker**) - B - claims head
48. [I] Settlement & Payment Reconciler (UTR matching, partial settlements, TDS/GST, hospital vs reimbursement) - A - finance
49. [I] Claim Status Messenger (every status change to the customer, in their language) - A - claims desk
50. [I] Reimbursement Claim Assistant for Customers (document checklist, pre-submission self-check, deadlines) - A - customer (see 78)
51. [I] Subrogation & Third-party Recovery Tracker (motor-accident cases, other-insurer overlap) - A - recoveries
52. [I] Claims Quality Auditor (sample of settled claims re-checked, overpayment/underpayment rate) - B - claims QA head
53. [I] Ageing & Turnaround Monitor (claims pending beyond regulatory timelines, escalation) - A - claims head
54. [I] Large-claim / Catastrophe Surge Planner (staffing, reinsurance notification, queue rules after floods/epidemics) - A - claims head

### 6. Fraud, waste & abuse (FWA)
55. [I] Provider Pattern Analyst (billing outliers, upcoding, unbundling, cloned discharge summaries) - B - SIU investigator
56. [I] Duplicate-claim & Identity-match Detector (same member in two hospitals the same night, ghost patients) - B - SIU
57. [I] Document Authenticity Checker (stamps, fonts, metadata consistency; **forgery claim only by investigator**) - B - SIU
58. [I] Hospital Geo-and-Travel Plausibility Checker (impossible distances, hospital capacity) - B - SIU
59. [I] Cashless Misuse Detector (planned procedure upgraded after approval; unnecessary admissions; short-stay patterns) - B - SIU + medical officer
60. [I] Investigator Case Builder (timeline, evidence table, interview questions; **allegation reserved**) - B - SIU head
61. [R] Industry Blacklist & Intelligence Sync (IIB-type shared fraud data within privacy law) - A/B - SIU + compliance
62. [I] Fraud-model Fairness & False-positive Auditor - B - chief risk officer

### 7. Customer service, grievance & ombudsman
63. [I] Contact-centre Agent (voice/WhatsApp: policy, claim, premium, network, forms; escalates distress or complaint to a human) - A - customer-care head
64. [I] Grievance Intake & Classifier (IRDAI grievance categories, due dates, acknowledgement) - A - grievance officer
65. [I] Grievance Response Drafter (facts from the file, clause, remedy options) - B - grievance officer signs
66. [I] Ombudsman Case File Assembler (Insurance Ombudsman Rules 2017 packet: policy, claim file, rejection letter, correspondence index) - A - legal
67. [I] Consumer-court Defence Packet Builder - A/B - legal counsel
68. [I] Voice-of-customer Analyst (complaints, calls, reviews: topics, spikes, root causes, pylab) - A - CX head
69. [I] Multilingual Document Translator (policy wording, letters in regional languages, glossary-locked) - B - bilingual reviewer
70. [I] Accessibility Assistant (large print, audio policy summary, WhatsApp voice for elderly) - A - CX

### 8. Compliance, regulation & governance
71. [I] Regulatory Change Watcher (IRDAI circulars, GST, DPDP, health-ministry notices -> impact list) - A - compliance head
72. [I] Filing Calendar & Return Assembler (IRDAI returns, MIS, audit schedules; **submission by the principal officer**) - A - compliance
73. [I] Policy-wording Plain-Language Reviewer (flags jargon, ambiguity, hidden exclusions; contra-proferentem risk) - B - legal + product
74. [I] Mis-selling Detector (call-recording keyword review, cooling-off, free-look compliance, proposal discrepancies) - B - compliance
75. [I] Claims-data Privacy Guard (access audit, consent artefact tracking, minimum-necessary views) - B - DPO
76. [I] Model Governance Officer (inventory, bias/drift tests, human-override rates for every tier-B employee; HC#160) - B - AI governance committee
77. [I] Audit Support Assistant (internal/statutory audit samples, evidence index) - A - internal audit

### 9. Policyholder-side advocacy & wellbeing (the customer's own AI Employee)
78. [P] Claim Companion - tracks hospitalisation: what to do before admission (intimation, cashless request), documents at discharge, filing deadlines, follow-ups; **never a medical or legal opinion** - A - policyholder
79. [P] Deduction Explainer - reads the settlement letter and explains each cut with the policy clause; suggests questions to ask the insurer - B - policyholder / adviser
80. [P] Rejection Appeal Drafter - reasons-to-points mapping, supporting documents list, grievance letter, ombudsman complaint steps with limitation dates - B - policyholder / lawyer
81. [P] Policy Vault - all policies, premiums, renewal dates, nominees, family members, e-cards, one place (Pehchaan Locker rules) - A - policyholder
82. [P] Coverage Gap Advisor (compare cover with city hospital costs, family size; prompts to review, not a sales push) - A/B - policyholder / adviser
83. [P] Premium-tax & 80D Helper (receipts, limits, parents' cover; **tax filing by the filer**) - A - policyholder / CA
84. [P] Hospital Estimate Comparer (cashless vs reimbursement, room-rent trap, package quotes) - A - policyholder
85. [P] Chronic-care Cover Planner (disease management programmes, OPD covers, wellness rewards) - A/B - policyholder

### 10. Government schemes & public payers
86. [G] Beneficiary Eligibility Navigator (PM-JAY, state schemes, CGHS, ECHS, ESIC: documents, nearest empanelled hospital, how to claim) - A - CSC / scheme helper
87. [G] Scheme Hospital Claim Tracker (package, geotag/photo proof, pre-auth, discharge, payment ageing) - A - hospital scheme desk
88. [G] Scheme Audit & Anomaly Analyst (district/hospital outliers, duplicate IDs; **action by authority**) - B - state health agency
89. [G] Fund-flow & Reimbursement Reconciler (state vs central shares, hospital payments, arrears) - A - finance officer
90. [G] Grievance & Helpline Assistant for Beneficiaries (multilingual, voice-first, escalates to nodal officer) - A - helpline lead
91. [G] Enrolment Camp Organiser & Follow-up Caller - A - district health officer

### 11. Data, interoperability & claims-exchange infrastructure
92. [I] NHCX / ABDM Integration Engineer (claims exchange messages, HCX codes, consent artefacts; `health_int` lane) - A/B - integration lead
93. [I] FHIR Claim/Coverage Mapper (HL7 FHIR claim, coverage eligibility, ClaimResponse resources) - A/B - integration lead
94. [I] Code-Mapping Assistant (ICD-10 / CPT / HBP / hospital package codes to payer codes; ambiguous maps flagged) - B - clinical coder
95. [I] Master Data Reconciler (member, provider, policy IDs, duplicates) - A - data steward
96. [I] Data Quality & Lineage Auditor - A - data governance
97. [I] De-identified Analytics Sandbox Builder (for pricing/research with DPDP-safe datasets) - B - DPO + analytics head
98. [I] Cybersecurity Watcher for Claims Systems (access anomalies, exfiltration patterns, incident drills) - B - CISO

### 12. Finance, operations & enterprise functions
99. [I] Claims-cost Dashboard Builder (loss ratio, TAT, leakage, hospital mix; pylab) - A - CFO
100. [I] GST, Statutory & Accounting Assistant (premium GST, input credit, commissions, TDS) - A - finance
101. [I] Vendor & Outsourcing Manager (TPA SLAs, call-centre SLAs, medical-panel fee invoices) - A - operations
102. [I] Capacity & Staffing Planner (claims desks, call volumes by season: monsoon, dengue, festival season) - A - operations
103. [I] Investment & Solvency Data Prep (asset-liability data cleaning; **investment decisions human**) - A - CIO / actuary
104. [I] HR & Training Assistant for Claims/UW staff (competency matrix, mock claims, refreshers) - A - HR
105. [I] Business Continuity & Surge Planner (data-centre failover, claim-system downtime pack) - A - COO

### 13. Education, research & public interest
106. [P] Insurance Literacy Tutor (what is co-pay, sub-limit, waiting period, portability; for the public and school/college courses) - A - educator
107. [R] Health-economics Research Assistant (claims data studies, cost-effectiveness, HTA evidence) - B - researcher
108. [R] Policy Analyst for Regulators and Think-tanks (market conduct, complaint trends, product standardisation outcomes) - B - regulator analyst

## NEVER an AI Employee (tier C)
Decline, load or cancel a policy; deny, repudiate or short-settle a claim as the sole decision; allege fraud against a
person or hospital; certify medical necessity; appoint or remove a network hospital; set rates or reserves; sign a
regulatory return or reinsurance treaty; advise a customer to buy as if licensed; contact a patient to pressure a
claim withdrawal; misuse health or genetic data beyond consent; make an ombudsman or court filing in someone's name.

## Suggested build order
1. **Wave 1 - customer-side + admin (tier A, no regulated decision)**: 14, 15, 17, 21, 26, 32, 35, 39, 42, 43, 46, 48, 49, 50, 53, 63, 64, 78, 79, 80, 81, 86, 87.
2. **Wave 2 - assist with a named human**: 11-13, 33, 34, 44, 45, 47, 65, 66, 73, 74, 92-94.
3. **Wave 3 - fraud, pricing, underwriting AI (regulated, needs model governance 76)**: 3-7, 22-25, 55-62, 88, 97.
Fit to Hoola: department **"Health Insurance & Payers"** beside Healthcare / Pharmacy / Devices / Diagnostics / Medical
Education; extend the existing insurance-agent employee (`ins` lane) for [X], reuse hospital insurance-desk roles (HO#80-82) for
cashless [P], Khata ledger (28, 48), WhatsApp opt-in (15, 49), Pehchaan Locker (14, 81), pylab (3, 4, 6, 99), `health_int`
(92, 93), approval cards for every signer step. **Best first pilot: the customer side** - a policyholder or an agent: Claim
Companion + Deduction Explainer + Appeal Drafter + Policy Vault (78-81) - it fits Hoola's "your avatar works for you" brand
and needs no insurer deployment. Second pilot: a hospital's TPA desk (32, 34, 39) because the hospital already pays for that pain.

## Open questions for the owner
- Which seat first: **policyholder / agent** (B2C or B2B2C, fastest), **hospital TPA desk** (HO overlap), **TPA/insurer claims** (large
  deals, deep integration, strict model governance), or **government schemes**?
- Customer-side employees must never act as the adviser or the lawyer; confirm the disclaimer wording and whether
  an IRDAI-registered adviser must be in the loop for Wave 2 (11-13).
- Which country leads? India (IRDAI/NHCX/PM-JAY) is assumed; the US prior-auth/denial-appeal market is large but
  HIPAA-heavy and crowded.
- Do you want the claims employees to submit through NHCX directly, or only prepare packets beside the hospital's/TPA's system?
- "GO per field" turns each into a sourced report with IRDAI circulars and NHCX specs checked on primary text.
