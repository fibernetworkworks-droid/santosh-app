# The medical devices industry, function by function - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A MEDICAL DEVICES INDUSTRY AI EMPLOYEE LIST"*. Fourth in the series after
`healthcare_industry/` (160 roles), `pharmacy_industry/` (118) and `hospital_industry/` (128). This one covers the
company that DESIGNS, MAKES, CLEARS, SELLS and SERVICES the device: syringe to MRI to diagnostic app. Overlaps with
earlier registers are cross-referenced (HC# / PH# / HO#) and not counted.

**15 fields, 118 candidate AI Employees.**

## How honest this is
- No new web research for this file. The register is **domain knowledge, not a sourced census**. Standards and laws
  below are from memory and **must be re-checked on the primary text** before any desk is built: ISO 13485, ISO 14971,
  IEC 62304, IEC 62366-1, IEC 60601 family, ISO 10993, ISO 14155, IEC 81001-5-1, ISO 11135 / 11137 / 17665 (sterilisation),
  EU MDR 2017/745 + IVDR 2017/746, FDA 21 CFR 820 (QMSR, aligning to ISO 13485 - check the effective date), FDA 510(k) /
  De Novo / PMA, India Medical Devices Rules 2017 (classes A-D, CDSCO licences - check current form numbers), IMDRF
  guidance, UDI rules.
- Nothing is built. Hoola today has relevant plumbing only: Data Desk + pylab (statistics), research engine, document
  studio / HOOLA PRINT (controlled documents), engineering desk (CAD, FEA, DFM - `app/engineering/`), `health_int`,
  Maps, approval cards.

## The findings that shape every device desk
### 1. The gate is the DEVICE FILE and the people who sign it
Tier ladder as before: **A** admin/prepare, **B** assist (flag / draft for a named licensee), **C** reserved.
Reserved in this industry: approving a design (design review sign-off), accepting a risk-benefit conclusion, product
release and Declaration of Conformity, Management Representative / PRRC / Authorised Representative duties, clinical
evaluation conclusions, a regulator submission under the company's name, a field-safety corrective action decision,
sterilisation validation sign-off, calibration pass/fail on a measuring instrument. An AI **prepares and checks the
file; a named person signs it.**

### 2. Medical devices are traceability businesses
The same chain of records must connect: user need -> requirement -> design -> risk -> verification -> validation ->
manufacture -> lot/serial -> UDI -> distribution -> complaint -> CAPA -> recall. An AI Employee that keeps the chain
unbroken (and flags a broken link) is lawful, safe and the biggest value in a small manufacturer's life. This is
Hoola's strength: structured records, checks in code, nothing invented.

### 3. Software is now a device
Any tier-B role that classifies or predicts for patient care can itself be SaMD (CDSCO draft 2025; EU MDR rule 11;
FDA CDS guidance; EU AI Act high-risk) - this register's own AI Employees included. Each such role needs the
human-in-loop card and the governance employee (HC#160).

### 4. Where the buyer pain is
Small and mid-size makers (India has thousands, many in the MSME bracket) cannot afford a full QA/RA department:
technical files, ISO 13485 documents, licence renewals, audits, UDI labels, complaint handling and vigilance reports
are done by one or two people. Tier-A/B document and tracking employees fit exactly there.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)

### 1. Product strategy & clinical need
1. Unmet-need Scout - clinician interviews to need statements, literature + patent evidence (Hoola research) - A - product manager
2. Market & Reimbursement Analyst - procedure volumes, price bands, tender history, coverage codes - A - business head
3. Competitor Device Tracker - approvals, recalls, label claims across markets - A - product manager
4. Intended-use & Indications Drafter - wording options mapped to regulatory class impact - B - regulatory + clinical lead
5. Regulatory Strategy Mapper - target markets x class x pathway x timeline x cost - B - RA head

### 2. Design & development (ISO 13485 cl. 7.3, IEC 62304)
6. User-needs to Requirements Traceability Keeper - links needs, specs, tests, risks; gap report - A - systems engineer
7. Design Input/Output Document Assembler (DHF / design dossier) - A/B - design lead
8. Design-review Packet Builder & Minutes Taker - action items tracked; **review approval reserved** - A - design lead
9. Usability Engineering File Assistant (IEC 62366-1: use scenarios, hazard-related use errors, summative plan) - B - human-factors lead
10. Mechanical Design Check Companion - tolerance stack, DFM hints, material shortlist (Hoola CAD / FEA / DFM) - B - design engineer
11. Biocompatibility Plan Mapper (ISO 10993-1 endpoints by contact type and duration) - B - toxicologist / RA
12. Electrical Safety & EMC Test-plan Builder (IEC 60601-1, -1-2, particular standards) - B - test engineer
13. Embedded Firmware Reviewer (coding-standard check, static-analysis triage; IEC 62304 class) - B - software lead
14. Software Lifecycle Documentation Generator (SDP, SRS, SDD, SOUP list, release notes) - A/B - software lead
15. SOUP / Open-source Licence & Vulnerability Watcher (SBOM, CVE feed) - A/B - software + security lead
16. Design-transfer Checklist Runner (drawings, specs, work instructions, supplier readiness) - A - operations
17. Design-change Impact Assessor - what needs re-verification, re-labelling, re-notification - B - change-control board

### 3. Risk management (ISO 14971) & usability
18. Hazard Analysis Drafter - candidate hazards, sequences, harms from known lists (MAUDE-style categories) - B - risk-management lead
19. FMEA / FTA Table Keeper (dFMEA, pFMEA, scoring consistency checks) - A/B - quality engineer
20. Risk-Control Traceability Checker - every control has a verification; residual risk summary draft - B - risk-management lead
21. Benefit-Risk Summary Drafter - **acceptability conclusion reserved** - B - clinical + RA + top management
22. Post-market Risk Feedback Loop - pulls complaints / literature back into the risk file - B - risk lead

### 4. Software as a Medical Device & digital health devices
23. SaMD Classification Advisor (IMDRF significance x state matrix; MDR rule 11; CDSCO draft) - B - RA head
24. Algorithm Change Protocol Planner (predetermined change control concept) - B - AI lead + RA
25. Clinical-AI Performance Evaluator (sensitivity / specificity / CI, subgroup and drift reports via pylab) - B - clinical scientist
26. Dataset Provenance & Bias Auditor (sources, consent, demographics, label quality) - B - data science lead
27. Cybersecurity Threat-model Assistant (IEC 81001-5-1; STRIDE tables; patch plans) - B - security lead
28. Interoperability Conformance Checker (HL7 / FHIR / DICOM / IEEE 11073 messages; `health_int` lane) - A/B - integration lead
29. App-Store Medical Claims Checker (claims vs intended use vs class) - B - RA

### 5. Quality management system (ISO 13485 / FDA QMSR)
30. Document Control Clerk (versions, approvals, effective dates, obsolete pull) - A - QA manager
31. SOP Author & Reviewer mapped to clauses - A/B - QA manager
32. Training Matrix Keeper (role x SOP x evidence x re-train date) - A - QA
33. Internal Audit Planner & Runner (risk-based schedule, checklists, findings log) - A - internal auditor
34. Management Review Packet Builder (inputs per 5.6: audits, complaints, CAPA, regulatory changes) - A - management representative
35. CAPA Manager (open, root-cause tool prompts, actions, effectiveness check) - A/B - QA head
36. Nonconformance Report (NCR) Clerk & Trend Analyst (pylab Pareto, SPC) - A - QA
37. Supplier Qualification & Audit Assistant (approved supplier list, questionnaires, scorecards) - A - purchasing/QA
38. Calibration & Equipment Tracker (instrument list, due dates, certificate filing; **pass/fail by calibrator**) - A - metrology
39. Change-control Workflow Keeper - A - QA
40. Quality Records Retention Scheduler (device lifetime + regulator periods) - A - QA
41. MDSAP / ISO 13485 Certification Audit Readiness Assistant - mock audit, evidence binder - A/B - QA head
42. Regulatory Intelligence Watcher (FDA, EU Commission / MDCG, CDSCO notices, standard revisions) - A - RA head

### 6. Regulatory affairs & market access
43. Technical File / Technical Documentation Assembler (EU MDR Annex II-III, CSDT/STED for India) - A/B - RA manager
44. 510(k) Predicate Finder & Substantial-Equivalence Table Drafter - B - RA manager
45. FDA eSTAR / eCTD-style Submission Packager (completeness check, cross-references) - A/B - RA manager
46. CDSCO Licence & Import-registration Assistant (Test licence, manufacturing and import forms, plant master file, device master file) - A - RA India lead
47. Notified Body Query Responder (drafts; **submission reserved**) - B - RA manager
48. UDI Manager (GS1 / HIBCC identifiers, data records to GUDID / EUDAMED / India UDI as live) - A - RA / data steward
49. Labelling & IFU Compliance Checker (symbols per ISO 15223-1, languages, mandatory elements) - B - RA + clinical
50. Declaration of Conformity & Certificate Tracker (expiries, scope, Authorised Representative) - A - RA
51. Product-registration Matrix Keeper (country x product x status x renewal) - A - RA
52. Import/Export & HS-code Assistant (customs, free-sale certificates, apostille lists) - A - EXIM
53. Reimbursement & Coding Dossier Assistant (HCPCS / CPT cross-walk, HTA submission shells) - A/B - market-access lead
54. PRRC / Responsible-person Evidence Binder (EU MDR Art. 15 duties logged; **person remains human**) - A - PRRC

### 7. Clinical evaluation & investigations
55. Clinical Literature Search & Appraisal Agent (systematic protocol, screen log, extraction table) - B - clinical scientist
56. Clinical Evaluation Report (CER) Drafter (MDCG 2020-13 structure, equivalence tables) - B - clinical affairs lead signs
57. Clinical Investigation Plan Drafter (ISO 14155) - B - clinical lead + biostatistician
58. Site & Ethics-committee Submission Assistant (CDSCO CT / CTRI, EC packets) - A/B - clinical ops
59. Investigator Brochure & Informed-consent Pack Builder - B - clinical lead
60. Study Monitoring Scheduler & Report Drafter - A/B - CRA
61. Statistical Analysis Plan Shell (pylab) - B - biostatistician signs
62. PMCF Plan & Survey Runner - post-market clinical follow-up questionnaires and registry feeds - A/B - clinical affairs

### 8. Manufacturing & production
63. Production Planner & Line Scheduler (cleanroom slots, lot sizes) - A - production head
64. Device History Record (DHR) Assembler - lot traveller to completed record, missing entries flagged - A/B - production QA
65. In-process Inspection Logger & SPC Charts (Cp/Cpk, control limits via pylab) - A - quality engineer
66. Cleanroom & Environmental Monitoring Reviewer (particle counts, bioburden trends) - B - microbiologist
67. Sterilisation Cycle Record Reviewer (EtO / gamma / steam: dose / cycle data vs validated parameters; **load release reserved**) - B - sterilisation lead
68. Process Validation Protocol & Report Drafter (IQ/OQ/PQ, Gauge R&R) - B - validation engineer
69. Packaging Validation Planner (ISTA / ASTM F1980 accelerated ageing, seal strength) - B - packaging engineer
70. Shelf-life & Real-time Ageing Tracker - A - R&D/QA
71. Lot Traceability Mapper (component lot -> finished lot -> customer) - A - QA
72. Nonconforming Product Disposition Assistant (rework instructions, MRB packet; **disposition by MRB**) - B - MRB chair
73. OEE & Yield Analyst (pylab) - A - plant head
74. Tooling & Mould Maintenance Scheduler - A - maintenance
75. Product Release Dossier Compiler - checks every release criterion is met; **release reserved** - B - authorised releaser

### 9. Supply chain, procurement & distribution
76. Component Obsolescence & Alternate-source Watcher - A - supply-chain lead
77. Supplier Change Notification Handler (PCNs routed to change control) - A - supply-chain + QA
78. Demand Forecaster & S&OP Planner (pylab) - A - planner
79. Implant & Consignment Stock Tracker (surgeon-wise, hospital-wise, expiry) - A - sales ops
80. Cold-chain / Controlled-storage Monitor (reagents, biologic-coated devices) - B - warehouse QA
81. Distributor Qualification & Territory Manager (licences, GDP-type records) - A - commercial head
82. Distributor Stock & Tender Compliance Checker - A - sales ops
83. Recall Execution Assistant (affected lots, consignee list, effectiveness checks, notices drafted) - B - QA/RA; **field action decision reserved**
84. Counterfeit & Grey-market Watcher (marketplaces, serial checks) - A/B - brand protection

### 10. Sales, marketing, training & service
85. Tender & Institutional Sales Assistant (eligibility checks, forms, price schedules) - A - sales head
86. Clinical Specialist Case-support Scheduler (OT attendance logs, no clinical decisions) - A - clinical specialist manager
87. Promotional Material Compliance Checker (claims vs intended use / label; no off-label) - B - regulatory + medical reviewer
88. Surgeon / Clinician Training Programme Organiser (cadaver labs, proctor schedules, CME logs) - A - training lead
89. Customer Onboarding & Installation Coordinator (site readiness, power / space checklist, DICOM / HL7 setup) - A - service head
90. Field-service Dispatcher & Spare-parts Planner (Maps, SLA clocks) - A - service head
91. Preventive-maintenance Planner for Installed Base - A - service
92. Service-report Drafter (technician notes to structured record; failure-mode coding) - A/B - service engineer signs
93. Remote Diagnostic Log Analyst (error logs to likely fault tree) - B - service engineer decides
94. Warranty & Contract (AMC / CMC) Manager - A - service finance

### 11. Post-market surveillance & vigilance
95. Complaint Intake & Triage (email / phone / portal to structured record; reportability *flag*) - B - complaint handler / vigilance officer decides
96. Adverse-event Report Drafter (FDA MDR / EU vigilance MIR / CDSCO) - B - vigilance officer submits
97. Literature Surveillance for Safety (device family + competitors) - B - clinical affairs
98. Trend Reporter (PSUR / PMSR sections, UTD complaint rate tables, pylab) - B - PMS lead
99. Field Safety Notice Drafter (FSCA; **decision reserved**) - B - RA + management
100. Returned-device Analysis Coordinator (RMA, teardown checklist, root-cause links to CAPA) - A/B - quality engineer
101. Registry & Real-world-evidence Collector (outcomes from partner hospitals, de-identified) - B - clinical affairs

### 12. IVD (diagnostic kits & analysers) specifics
102. IVD Performance Study Planner (analytical + clinical performance, sample sizes via pylab) - B - IVD scientist
103. Reagent Lot-release Record Compiler - A/B - QC
104. Reference-range & Stability Study Tracker - A - IVD lab
105. External Quality Assessment (EQA) Enrolment & Result Tracker - A - customer-quality

### 13. Reprocessing, refurbishment & after-use
106. Reusable Device Reprocessing Validator Assistant (IFU cleaning / disinfection / sterilisation claims evidence) - B - reprocessing lead
107. Refurbished-equipment Records Keeper (second-hand imaging / ventilators: history, parts changed, safety tests) - A/B - biomedical head
108. End-of-life, Take-back & e-waste Compliance Tracker - A - EHS

### 14. Business, finance & company functions
109. Device Costing & Pricing Analyst (BOM roll-up, yield, margin by channel, pylab) - A - finance
110. Grant / Scheme / Incentive Finder (PLI, state MSME, BIRAC, Make-in-India, export promotion) - A - founder/CFO
111. Investor-diligence Data-room Builder (regulatory + QMS + IP evidence index) - A - CEO
112. IP & Freedom-to-operate Assistant (patent landscape, claim charts for counsel) - B - IP counsel
113. EHS & Facility Compliance Tracker (cleanroom, EtO emissions, waste, fire, factory licence) - A - EHS officer
114. Contract Manufacturer / OEM Relationship Manager (quality agreements, forecasts, audits) - A - supply-chain + QA
115. Founder Copilot for MedTech Start-ups (stage-gate plan, budget, who-to-hire, risks) - A - founder

### 15. Education, standards & community
116. Standards Subscription Librarian (which clause of which standard applies; cites, never reproduces copyrighted text) - A - RA/QA
117. Biomedical-engineering Student Tutor (design controls, 14971 worked examples; Guru Sahayak) - A - faculty
118. Device Hackathon / Incubator Mentor (regulatory reality check for ideas) - A - incubator manager

## NEVER an AI Employee (tier C)
Approve a design review or design freeze; accept residual risk or the benefit-risk conclusion; sign the Declaration
of Conformity, CER, CoA, calibration certificate or technical file; release a product lot or sterile load;
disposition nonconforming product; decide a recall / field safety action; submit to a regulator or notified body;
act as PRRC / Authorised Representative / Management Representative; report an adverse event as the legal
manufacturer without the vigilance officer; make clinical claims or give clinical advice; install, calibrate or
service safety-critical equipment unsupervised.

## Suggested build order
1. **Wave 1 - records that never forget (tier A)**: 30, 32, 33, 35, 36, 38, 42, 46, 48, 50, 51, 71, 85, 90, 94.
2. **Wave 2 - the file-builders (A/B, signer in the loop)**: 6, 7, 14, 19, 20, 34, 43, 49, 55, 56, 64, 95, 96, 98.
3. **Wave 3 - SaMD / clinical / sterility (B, regulated, needs governance HC#160)**: 23-27, 61, 67, 99.
Fit to Hoola: department **"MedTech & Devices"** beside Healthcare / Pharmacy; reuse engineering desk (10, 74), Data Desk
+ pylab (25, 36, 61, 65, 73, 98, 102), research engine (1, 3, 55, 97), doc studio + HOOLA PRINT (controlled docs),
`health_int` (28), Maps (90), approval cards for every signer step. The strongest first pilot: one Indian MSME
manufacturer (disposables, orthopaedic, diagnostics) with 1-2 QA/RA staff.

## Open questions for the owner
- Which segment first: **disposables/consumables**, **orthopaedic/implants**, **diagnostics/IVD**, **imaging/capital
  equipment**, or **digital/SaMD**? Each changes which standards lead.
- Which markets lead: India (CDSCO), US (FDA), EU (MDR)? The records are shared; the forms are not.
- Do you want the QMS employees to BE the system of record (document control, CAPA) or to sit beside the customer's
  existing eQMS? The first is bigger and needs electronic-record validation (21 CFR Part 11-type) evidence.
- "GO per field" turns each into a sourced report with the standards and rules checked on primary text.
