# The pharmacy industry, job by job - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A PHARMACY INDUSTRY AI EMPLOYEE LIST"*. Follows `docs/research/healthcare_industry/`
(which has 22 fields and a few pharmacy roles #54-61 and #62-86); this register goes deep on pharmacy alone, from the
shop counter to the drug factory to the regulator.

**18 fields, 118 candidate AI Employees.**

## How honest this is
- No new web research was run for this file (the earlier healthcare searches returned thin secondary pages). The
  register is **domain knowledge, not a sourced census**; legal references are from memory and **must be
  re-checked on the primary text** before any desk is built (cdsco.gov.in, pharmacycouncilindia.org, nppaindia.nic.in).
- Nothing here is built. Hoola today has only pharmacy-adjacent plumbing: Bazar connectors, bills/UPI cards, shop
  lists, Maps, the Data Desk and `pylab`. No pharmacy desk exists.

## The findings that shape every desk
### 1. In pharmacy the gate is the REGISTERED PHARMACIST and the QUALIFIED PERSON
Same ASSIST / PREPARE / DECIDE ladder as healthcare, with sharper edges:
- **A - Admin / prepare**: stock, expiry, billing, registers, orders, paperwork, reminders. Build first.
- **B - Assist**: checks and drafts for a named licensee (interaction flag, dossier draft, deviation write-up).
- **C - Reserved**: dispensing a prescription drug, substituting, counselling-as-clinician, releasing a batch,
  signing a CoA, approving a label/dossier, selling a controlled drug. **Never an AI Employee.**
Indian anchors (verify): Pharmacy Act 1948 (a registered pharmacist supervises dispensing); Drugs & Cosmetics Act
1940 + Rules 1945 (Schedules H, H1, X, G; GMP in Schedule M, revised 2023); NDPS Act for narcotics; DPCO / NPPA
price ceilings; UCPMP for promotion; Telemedicine Guidelines 2020 for the prescription origin; e-pharmacy rules
still draft - confirm status. Outside India: FDA 21 CFR 210/211 + DSCSA, EU GMP + FMD, WHO GDP/GMP.

### 2. Pharmacy is a *records* business - which is exactly where software is safe
Half the legal burden is registers: Schedule H/H1 sale register, X register, purchase invoices, batch/expiry,
temperature logs, batch manufacturing records, deviations, CAPA, stability, pharmacovigilance cases. An AI Employee
that keeps these audit-ready (and never invents an entry) is lawful and useful; one that sells or releases is not.

### 3. Commercial truth: margins are thin, expiry and credit kill shops
Dead stock, near-expiry, stockist credit cycles, MRP vs ceiling price, generic substitution margin, and returns are
where a small pharmacy loses money. Tier-A inventory/finance employees pay for themselves first.

---
## THE REGISTER  (AI Employee - what it does - tier - human who decides)

### 1. Retail / community pharmacy
1. Pharmacy Billing & GST Clerk - bills, batch-wise sale, GST/HSN, returns - A - owner
2. Prescription Reader - reads script photo/handwriting into a draft line list - B - pharmacist verifies
3. Interaction & Dose Checker - flags duplicate therapy, allergy, interaction, max dose - B - pharmacist decides
4. Substitution Proposer - generic/brand equivalents with price; **substitution is the pharmacist's act** - B - pharmacist
5. Schedule H/H1 Register Keeper - entries from the sale, ready for inspector - A - registered pharmacist
6. Expiry & FEFO Manager - near-expiry list, return-to-stockist, markdown plan - A - store
7. Reorder Planner - demand per salt, lead time, min-max (pylab) - A - owner
8. Refill & Adherence Reminder - chronic-patient WhatsApp prompts (opt-in) - A - pharmacist
9. Counter Query Assistant - "yeh dawai kis kaam aati hai" from package-insert facts, always "doctor se poochhiye" - B - pharmacist
10. Home-delivery Dispatcher - routes, rider slots, cold items - A - owner
11. Customer Credit (udhaar) Ledger - reuses Khata engine - A - owner
12. Inspector-visit Readiness Assistant - licence, register, cold-chain, pharmacist-present checklist - A - owner

### 2. Hospital pharmacy
13. Formulary Manager - formulary/non-formulary, therapeutic equivalents, P&T packets - B - P&T committee
14. Ward Stock & Indent Planner - par levels, indent vs issue - A - pharmacy in-charge
15. Unit-dose Cart Preparer - lists per patient, label draft - B - pharmacist checks
16. IV Admixture & Compatibility Checker - stability/compat table lookup - B - pharmacist
17. Antimicrobial Stewardship Watcher - restricted-antibiotic use, de-escalation prompts, DDD tallies - B - ID physician / stewardship pharmacist
18. High-alert Medicine Auditor - insulin, heparin, KCl, chemo; LASA names - B - pharmacist
19. Narcotic & Controlled Drug Reconciler - ward vs pharmacy count, discrepancy report - B - pharmacist in charge
20. Medication-error Reporter - incident draft, categorisation (NCC MERP) - A/B - patient-safety officer
21. Discharge Medication Reconciler - admission list vs discharge list differences - B - pharmacist/doctor

### 3. Clinical pharmacy & patient counselling
22. Medication Review Assistant (polypharmacy, Beers/STOPP lists) - B - clinical pharmacist
23. Renal/Hepatic Dose-adjustment Prompter - B - clinical pharmacist
24. Therapeutic Drug Monitoring Scheduler - level due dates, flags - B - clinical pharmacist
25. Pregnancy/Lactation Safety Lookup - B - pharmacist
26. Patient Counselling Sheet Drafter - plain-language, multi-language - B - pharmacist signs off
27. Adverse-event Intake from Patients - structured questions, routes to PV - B - PV
28. Vaccine Schedule & Due-list - A/B - pharmacist/doctor

### 4. E-pharmacy / online
29. Order Intake & Rx Verification Queue - checks a valid prescription is attached; **verification is the pharmacist's** - A/B - pharmacist
30. Catalogue & Salt-composition Curator - clean names, composition, schedule tags - A - catalogue lead
31. Dynamic Price & Ceiling Checker - MRP vs NPPA ceiling - A - pricing
32. Fulfilment & Packaging Planner (cold chain, tamper seals) - A - ops
33. Returns & Quality-complaint Handler - A/B - QA pharmacist
34. Fraud Screener (fake Rx, repeat controlled buys) - B - compliance
35. Telepharmacy Counsellor Scheduler - A - ops

### 5. Wholesale, distribution & cold chain
36. Stockist Order & Credit Manager - A - distributor
37. Batch Recall Executor - recall notice to downstream, trace by batch - B - QA head
38. Cold-chain Monitor - logger data, excursion report, product disposition *proposal* - B - QA
39. Beat Planner & Delivery Route Optimiser (Maps matrix) - A - sales
40. Reconciliation & Claims Clerk (scheme, expiry, damage claims with company) - A - accounts
41. GDP Compliance Assistant (WHO GDP / Schedule M-style records) - A - responsible person
42. Narcotics/Psychotropic Movement Tracker (statutory returns) - A/B - licensee

### 6. Pharma manufacturing (formulation, API, packaging)
43. Production Planner & Line Scheduler - A - production head
44. Batch Manufacturing Record (BMR) Assembler - fills template from MES/eBMR data - A/B - production
45. In-process Check Logger & SPC Plotter - A - IPQA
46. Equipment Cleaning & Changeover Tracker - A - production/QA
47. Preventive-maintenance & Calibration Scheduler - A - engineering
48. Yield & OEE Analyst (pylab) - A - plant head
49. Warehouse Material-status Controller (quarantine/approved/rejected labels) - A/B - warehouse QA
50. Utilities & Environmental Monitoring Reviewer (HVAC, water, particle counts) - B - QA microbiologist
51. Packaging Artwork & Line-clearance Checker - B - QA
52. Tech-transfer Document Assembler - A/B - tech-transfer lead
53. Process-validation Protocol & Report Drafter - B - validation head
54. Revised Schedule M / cGMP Gap Assessor - maps SOPs to clauses - B - QA head

### 7. Quality control & quality assurance
55. Sample & Lab Schedule Planner - A - QC head
56. HPLC/GC Data Reviewer - integrity flags, system-suitability, audit-trail anomalies; **result approval is human** - B - QC reviewer
57. OOS/OOT Investigator's Assistant - phase-1 checklist, trend context - B - QC head
58. Deviation Writer & Classifier - minor/major/critical *proposal* - B - QA head
59. CAPA Tracker & Effectiveness Checker - A - QA
60. Change-control Impact Assessor - lists affected docs/SOPs/regs - B - QA
61. SOP Author & Reviewer (version control, training matrix) - A - QA
62. Certificate of Analysis Drafter - from released results; **signature reserved** - B - QC head
63. **Batch Release Dossier Compiler** - gathers BMR, QC, deviations, checks completeness; **release is the Qualified Person / authorised person (C)** - B
64. Supplier Qualification & Audit Planner - A - QA
65. Data-integrity (ALCOA+) Auditor - B - QA head
66. Stability Programme Manager - pull schedule, trend, shelf-life proposal - B - stability lead
67. Self-inspection & Mock-audit Runner - A - QA
68. Document Control Clerk - A - QA

### 8. Regulatory affairs
69. Regulatory Intelligence Watcher - CDSCO/FDA/EMA notices, circulars, banned FDC lists - A - regulatory head
70. Dossier Assembler (CTD / ACTD / Form 44-type, eCTD check) - A/B - regulatory
71. Label, Leaflet & Artwork Reviewer vs rules - B - regulatory
72. Licence & Renewal Tracker (mfg, wholesale, retail, NOC) - A - regulatory
73. Query Response Drafter - B - regulatory
74. Import/Export Licence Assistant (Form 10, NOC, DGFT, DMF) - A - EXIM
75. Variation & Post-approval Change Tracker - A/B - regulatory
76. Pricing Filing Assistant (NPPA Form I/V, DPCO) - A/B - pricing/regulatory
77. Market-authorisation Map (which product in which country, which status) - A - regulatory

### 9. Pharmacovigilance & medical information
78. ICSR Intake & Duplicate Detector - B - safety physician
79. MedDRA Coding Proposer - B - PV coder
80. Literature Screener for Safety - B - PV
81. Signal-screening Tables (pylab) - B - QPPV/PV physician
82. PSUR/PBRER Section Drafter - B - QPPV
83. Medical Information Responder (unsolicited HCP queries; approved-label answers only) - B - medical-affairs
84. Product-quality Complaint Router - A - QA

### 10. R&D, formulation & analytical
85. Literature & Patent Landscape Agent (Hoola research engine) - A - R&D head
86. Formulation DoE Planner (design-of-experiments tables, pylab) - B - formulation scientist
87. Excipient Compatibility Lookup - B - formulation
88. Analytical Method Development Notebook (ELN) Assistant - A - analyst
89. Method Validation Report Drafter (ICH Q2) - B - analytical head
90. Bioequivalence Study Planner & Stats Shell - B - biostatistician
91. Impurity & Nitrosamine Risk Assessor - rule-based triage, flags for human - B - QA/regulatory
92. Patent Expiry & FTF/Paragraph IV-type Watcher (India: Section 3(d) notes) - A - IP counsel

### 11. Clinical research & CRO
93. Site-feasibility & Recruitment Tracker - A - clinical ops
94. Informed-consent Pack Preparer - B - ethics committee
95. CRF Query Generator - A/B - data manager
96. TMF (trial master file) Completeness Checker - A - clinical ops
97. Monitoring Visit Report Drafter - B - CRA
98. SAE Intake & Expedited-report Timer - B - safety physician
99. CTRI / Registry Updater - A - sponsor

### 12. Sales, marketing & medical affairs
100. Medical-representative Planner & Call Reporter (UCPMP-compliant logs) - A - sales manager
101. Promotional Material Compliance Checker (claims vs label, no off-label) - B - medical/regulatory reviewer
102. Doctor-engagement CME Organiser (no inducements; expenses logs) - A - compliance
103. Tender & Institutional Sales Assistant - A - sales
104. Market-intelligence Analyst (IQVIA-style secondary data, pylab) - A - brand manager

### 13. Procurement, supply chain, exports
105. API & Excipient Procurement Buyer - vendor comparison, COA checks - A - purchase head
106. Demand-supply Forecaster (S&OP) - A - planner
107. Shortage & Allocation Watcher (essential-medicine list) - A - supply chain
108. Customs, HSN & Export-docs Assistant - A - EXIM
109. Serialisation / Track-and-trace Reconciler - A - supply-chain QA

### 14. Specialised: compounding, radiopharmacy, AYUSH, veterinary
110. Compounding Record & Beyond-use-date Keeper - B - compounding pharmacist
111. Radiopharmacy Decay & Dose-calendar Planner (AERB records) - B - radiopharmacist
112. AYUSH Pharma Formulation Record Keeper (classical texts, GMP for AYUSH) - A/B - formulation head
113. Veterinary Drug Dispenser's Assistant (species/dose reference, withdrawal periods) - B - vet

### 15. Government, public pharmacy & drug control
114. Jan Aushadhi Kendra Assistant (stock, rates, indent, reporting) - A - kendra owner
115. Drug-inspector Sampling & Case Tracker - A - drugs control officer
116. Essential Medicines Supply Dashboard (state tender, stock-out alerts) - A - state procurement

### 16. Pharmacy education & professional development
117. D.Pharm / B.Pharm / Pharm.D Tutor & Practical Planner (PCI syllabus; Guru Sahayak) - A - faculty
(CPD credit tracking and licence-renewal reminders ride the healthcare register #150.)

### 17. Pharmacy business, finance & IT
118. Pharmacy Chain Controller - multi-store stock transfer, shrinkage, GST, loyalty, margin by salt - A - owner

## NEVER an AI Employee (tier C)
Dispense or hand over a prescription medicine; accept or cancel a prescription; substitute a drug; counsel as
if a clinician; sell Schedule H1/X/narcotic stock; release a batch; sign a CoA, label, dossier or licence form;
approve OOS conclusion; classify a deviation as final; submit to a regulator; promote off-label.

## Suggested build order
1. **Wave 1 (retail & distribution, tier A, pays back in weeks)**: 1, 5, 6, 7, 11, 12, 36, 37, 40.
2. **Wave 2 (assist with pharmacist-in-loop card)**: 2, 3, 4, 8, 9, 14, 19, 29.
3. **Wave 3 (factory, QA/RA, PV)**: 44, 56, 58, 63, 69-73, 78-82 - these need a licensed QA/QP owner at the customer
   and Revised Schedule M evidence, so pilot with one friendly manufacturer.
Fit to Hoola: department **"Pharmacy & Pharma Industry"** beside the Healthcare one; reuse Khata (11), Maps (10, 39),
Data Desk + pylab (7, 48, 81, 104), research engine (69, 85), HyperFrames (leaflet videos), Pehchaan Locker rules
(never store patient IDs unmasked).

## Open questions for the owner
- Which side first: **shop pharmacy** (fast, many users) or **manufacturing/QA** (rich, fewer buyers)?
- Prescription photos are health data (DPDP) - confirm retention window and consent text before Wave 2.
- Confirm status of India's e-pharmacy rules before any online-pharmacy desk (29-35).
- Next step on "GO per field": re-verify each law above from primary text and add sourced per-field reports.
