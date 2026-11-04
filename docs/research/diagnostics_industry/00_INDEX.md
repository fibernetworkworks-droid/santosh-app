# The diagnostics industry, function by function - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A DIAGNOSTICS INDUSTRY AI EMPLOYEE LIST"*. Fifth in the series after `healthcare_industry/`
(160 roles), `pharmacy_industry/` (118), `hospital_industry/` (128) and `medical_devices_industry/` (118). This one is the
company that TESTS: the pathology lab, the imaging centre, the collection network, the reference lab, the genomics lab,
the teleradiology reporting hub and the chain that runs them. Test KIT makers are in the devices register (MD#102-105);
roles already listed elsewhere are cross-referenced (HC# / PH# / HO# / MD#) and not counted.

**13 fields, 108 candidate AI Employees.**

## How honest this is
- No new web research for this file. It is **domain knowledge, not a sourced census**. Standards and laws named are from
  memory and **must be re-checked on primary text** before building: ISO 15189:2022, NABL accreditation criteria, CAP,
  CLIA (US), ISO 22870 (point-of-care), Clinical Establishments Act, AERB licensing for X-ray / CT / nuclear medicine,
  PCPNDT Act (ultrasound), Bio-Medical Waste Rules 2016, DPDP Act 2023 / ABDM consent, ICMR guidance on genomic and AI
  work, DICOM / HL7 / FHIR, and CDSCO rules where the lab's own software is a device.
- Nothing is built. Hoola's relevant plumbing today: `queue` tokens, Maps (home-collection routes), WhatsApp campaigns
  (opt-in), Data Desk + pylab (QC statistics), `health_int` (HL7 / FHIR / ABDM), doc studio, approval cards.

## The findings that shape every diagnostics desk
### 1. The signature is the product
A diagnostic result has value only once a named, registered professional has verified and signed it (pathologist,
radiologist, microbiologist, clinical biochemist, geneticist). Same ladder as before: **A** admin/prepare,
**B** assist (flag / draft / pre-read for a named signer), **C** reserved. Reserved here: releasing or amending a
report, interpretive comment, critical-value clinical advice, pass/fail on QC and calibration, acceptance/rejection of
a specimen against criteria beyond the written rule, sex of the fetus (never), and any statement of diagnosis.

### 2. The pre-analytical phase is where 60-70% of lab errors live - and it is all tier A
Wrong patient, wrong tube, wrong fasting, haemolysis, delayed transport, lost sample, duplicate order, mislabelled
barcode. Order entry, collection scheduling, labelling, transport tracking and rejection logging need no clinical
judgement and fix the biggest error class. Post-analytical is the next: report delivery, critical-value call, amended
report trail. The analytic middle (the analyser, the read) stays human-verified.

### 3. Diagnostics is a logistics and volume business
Home collection, hub-and-spoke sample transport, batching, turnaround time (TAT), reference-lab outsourcing,
B2B collection centres, corporate and insurer wellness camps. Routes, slots, batch planning, TAT alerts, and
reconciliation of who owes whom are where margin is won - tier A, and Hoola already has Maps and queues.

### 4. Imaging and sequencing are the AI-regulated corner
A tool that reads an image or a variant and suggests a finding is SaMD (CDSCO draft 2025; FDA; EU MDR rule 11; EU AI
Act high-risk). It may only *flag, prioritise or pre-fill* for the signer, with the human-in-loop card and the
governance employee (HC#160). Worklist prioritisation and structured-report pre-fill are the lowest-risk entrance.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)

### 1. Patient access, ordering & home collection
1. Test Finder & Preparation Guide - "which test, what fasting, what cost" from the catalogue; never says what a result means - A - lab manager
2. Order Intake Assistant - doctor prescription / package / corporate list to a clean order, duplicate and panel-overlap flags - A - registration lead
3. Appointment & Slot Manager (walk-in, home, imaging with prep rules and equipment slots) - A - operations head
4. Home-collection Route Planner (Maps matrix, phlebotomist skills, time windows, fasting-first priority) - A - collection manager
5. Phlebotomist Assistant App-voice (tube list, order of draw, patient ID read-back prompts) - A - phlebotomy supervisor
6. Collection Quality Auditor (haemolysis / insufficient-volume rates by phlebotomist, retraining prompts) - A - collection manager
7. Consent & Declaration Collector (HIV / genetic / PCPNDT-type declarations, language-appropriate; **scripted, never counselling**) - A - lab head
8. Pre-test Counselling Scheduler (hands off to a human counsellor; genetic / HIV / oncology panels) - A - counsellor
9. Price, Package & Discount Quoter (corporate / insurer rates, GST) - A - commercial head
10. Patient Support Agent (WhatsApp / voice: status, rescheduling, reports resend, bill copy; routes clinical questions to a person) - A - customer-care head

### 2. Sample logistics & the pre-analytical phase
11. Barcode & Labelling Verifier (order-tube-patient match, relabel queue) - A - lab operations
12. Sample Chain-of-custody Tracker (collection -> hub -> lab, temperature, time stamps) - A - logistics head
13. Transport Temperature Monitor (logger data, excursion alerts, cool-pack rules) - B - QA lead
14. Specimen Acceptance Rule-checker (volume, tube type, haemolysis index, time since collection; **reject by written rule, escalate doubtful**) - B - technologist in charge
15. Rejection & Recollection Coordinator (calls patient, new slot, charges waived per policy) - A - customer care
16. Reference-lab (Send-out) Router (test -> best partner lab by cost / TAT / accreditation) - A - outsourcing manager
17. Courier & Hub Reconciler (manifests vs received, missing-sample hunt) - A - logistics

### 3. Clinical pathology, biochemistry, haematology & immunoassay
18. Worklist Builder & Batch Planner (analyser load, STAT priority, reflex rules entered by pathologist) - A - lab supervisor
19. Auto-verification Rule Keeper (delta checks, critical flags, interference indices; **rules approved by the director, release by rule or human**) - B - lab director
20. Delta-check & Plausibility Flagger (patient history, impossible combinations) - B - technologist
21. Critical-value Caller (finds the right clinician / contact, escalation ladder, read-back logged) - B - technologist / pathologist (extends HC#49)
22. Westgard / QC Rule Monitor (daily QC, shifts, trends, Levey-Jennings plots via pylab) - B - QC officer
23. Calibration & Reagent-lot Verification Tracker (new-lot vs old-lot comparison tables) - B - QC officer
24. Reagent & Consumable Stock Planner (usage per test, expiry, shipments, cold storage) - A - store in-charge
25. Analyser Maintenance & Downtime Scheduler (daily/weekly, service calls, uptime) - A - biomedical + lab
26. Interference & Haemolysis Trend Reporter - A - lab supervisor
27. Reference-interval Assistant (age / sex / pregnancy ranges, local verification studies via pylab) - B - clinical biochemist
28. Report Drafter - Interpretive Comment Library (pre-approved comments chosen by the pathologist, never generated clinical advice) - B - pathologist
29. Report Layout & Multi-language Printer (trend charts, units, SI/conventional) - A - lab IT
30. Report Delivery Assistant (WhatsApp / email / portal after release; patient copy, doctor copy; ABDM linking) - A - lab operations (extends HC#47)

### 4. Microbiology & infection diagnostics
31. Culture Reading Log Keeper (plate read times, growth notes entered by technologists) - A - microbiologist
32. AST Interpretation Table Assistant (CLSI / EUCAST breakpoints lookup; **interpretation by microbiologist**) - B - microbiologist
33. Antibiogram Builder (yearly, ward, organism; HO#66) - A/B - microbiologist
34. Outbreak / Cluster Alert (same organism, same hospital, same week) - B - infection-control officer
35. TB, Malaria & Notifiable Disease Reporter (case forms for IDSP / Nikshay-type portals; **notification by the lab director**) - B - lab director
36. Blood-culture Positivity Alerting (time-to-positivity, call to ward) - B - technologist

### 5. Molecular diagnostics, genomics & cytogenetics
37. NGS Run Planner (pooling, indexes, flow-cell loading sheets) - A - molecular lab head
38. Bioinformatics Pipeline Runner (QC metrics gates, version-pinned pipeline, reproducible logs; **run only on approved pipelines**) - B - bioinformatician
39. Variant Annotation Assembler (ClinVar / gnomAD / literature references pulled with sources; **classification is the geneticist's**) - B - clinical geneticist
40. ACMG-style Evidence Table Pre-filler - B - clinical geneticist signs
41. Genomic Report Template Filler (HC#52) - B - geneticist
42. PCR Plate Layout & Contamination-control Tracker (no-template controls, positive controls, area log) - A - molecular head
43. Genetic Data Consent & Re-contact Manager (what was consented, research use, withdrawal) - A - data-protection officer
44. Cytogenetics Karyotype Case Tracker (case, band images, TAT) - A - cytogeneticist
45. Pharmacogenomic Report Mapper (gene-drug tables by guideline CPIC / DPWG; **prescriber decides**) - B - clinical pharmacologist

### 6. Histopathology & cytology
46. Case Accessioning & Block/Slide Tracker (gross description entered by the pathologist, block counts, slide labels) - A - histology lead
47. Histology Process Scheduler (processor loads, staining runs, special stains) - A - histology lead
48. Digital Slide Triage (scanner queue priority, focus / tissue-detection QC, pathologist worklist order) - B (SaMD at the edge) - pathologist
49. Synoptic Report Pre-filler (CAP-style checklists populated from the pathologist's dictation, empty fields flagged) - B - pathologist signs
50. Frozen-section Time Keeper & OT Communication - A - pathologist
51. Cytology Screening Assistant (Pap / FNAC slide pre-screen: marks areas to look at) - B (SaMD) - cytopathologist
52. Tumour-board Slide & Report Packet Builder (HC#33) - A - pathologist

### 7. Imaging centres (X-ray, CT, MRI, USG, nuclear, mammography)
53. Imaging Order Validator (indication, pregnancy screen questions, contrast risk fields, appropriateness criteria lookup) - B - radiologist decides
54. Contrast & Renal-function Prep Messenger (creatinine due, hydration advice per protocol) - A/B - radiology manager
55. Modality Scheduler (scanner utilisation, protocol length, turnaround cleaning) - A - radiology manager
56. Worklist Prioritiser (STAT flags, ED vs OPD, aging) - B - radiologist (HC#29)
57. Critical-finding Escalation Tracker (radiologist marks, assistant calls and logs) - B - radiologist
58. Structured Report Pre-fill (templates by study, measurements pulled from the viewer, normal-text phrases chosen by radiologist) - B - radiologist
59. Prior-study Fetcher & Comparison Packer (PACS history, previous report summary) - A - radiology admin
60. Dose Register & Radiation-safety Keeper (DAP / CTDI log, TLD, AERB dates) - A - RSO (extends HO#45)
61. PCPNDT Form F & Register Keeper (ultrasound centres; **sex of fetus never recorded or stated**) - A - registered sonologist
62. AI-reader Result Tray (displays vendor AI marks for the radiologist; **flag only; logs concordance**) - B - radiologist
63. Nuclear-medicine Isotope Order & Decay Calendar - A/B - nuclear physician / RSO
64. Mammography Recall & Screening Tracker (BI-RADS, call-back, follow-up due) - B - radiologist
65. Teleradiology Case Router (nearest qualified reader, subspecialty, SLA clock, reader load) - A - teleradiology hub manager
66. Teleradiology Quality Reviewer (second-read sampling, discrepancy log, peer-review packets) - B - radiology QA lead

### 8. Point-of-care, screening camps & wearables
67. Point-of-care Device Fleet Manager (glucometer / HbA1c / ECG / spirometer: QC logs, operator competency, result sync) - A - POCT coordinator (ISO 22870)
68. Screening Camp Organiser (permits, staff, kits, eligibility lists, follow-up) - A - community-health lead
69. Screening Result Follow-up Caller (abnormals reminded to see a doctor; **no interpretation**) - A/B - clinician-supervised nurse
70. Corporate / Insurer Wellness Programme Reporter (aggregate, de-identified analytics, pylab) - A - account manager
71. Remote-monitoring Data Normaliser (wearable and home-device readings to FHIR observations) - A/B - integration lead

### 9. Quality, accreditation & compliance
72. NABL / ISO 15189 Documentation Assistant (quality manual, SOP map to clauses, audit packs; HC#50) - A - quality manager
73. Internal Audit & Proficiency-testing (PT / EQA) Tracker - A - quality manager
74. PT / EQA Result Evaluator (z-scores, bias plots via pylab; **corrective-action decision by director**) - B - quality manager
75. Measurement-uncertainty & Method-verification Assistant (precision, bias, linearity statistics) - B - lab scientist
76. Non-conformance & CAPA Manager (lab flavour: mislabel, TAT breach, wrong report) - A/B - quality manager
77. Amended-report Control (every amendment reason, who was told, original kept; **amendment itself by the pathologist**) - B - director
78. Staff Competency & Training Matrix (per test per person, re-assessment dates) - A - quality manager
79. Document Control & Licence Calendar (NABL scope, state licence, AERB, BMW authorisation, fire, pollution) - A - compliance officer
80. Bio-medical Waste Log Keeper (colour categories, weights, manifests) - A - waste officer (HO#95)
81. Biosafety & Needle-stick Incident Register - A - safety officer
82. Privacy & Access Auditor (unusual report access, DPDP requests, retention) - B - data-protection officer

### 10. Lab information, interfaces & data
83. LIS Interface Monitor (analyser-LIS, LIS-HIS HL7 queues, failed messages, test-code mismatches) - A/B - lab IT (extends HC#112)
84. Test Master & Catalogue Maintainer (LOINC mapping, units, ranges, synonyms) - B - clinical informaticist
85. Instrument Middleware Rules Tester (auto-verification regression tests after any change) - B - lab IT + director
86. ABDM / FHIR Diagnostic Report Publisher (consent-driven sharing of results) - A/B - IT head
87. Downtime Pack Generator (paper requisitions, labels, result-recording sheets) - A - lab IT
88. Data-quality Auditor (duplicate patients, missing DOB / sex, impossible values) - A - lab IT
89. De-identified Dataset Builder for research (rule-based, audit trail, ethics approval referenced) - B - data-protection officer

### 11. Business, finance & network operations
90. Diagnostic Chain Controller (centre P&L, test mix, utilisation, TAT by centre, pylab) - A - operations head
91. Franchise / Collection-centre Manager (onboarding, KYC, training, stock, royalty calculation) - A - franchise manager
92. Doctor-referral & Fee-split Compliance Checker (flags referral-incentive patterns that breach law, Cuts-Practice rules) - B - compliance + legal; **legal decision human**
93. Corporate Contract & Invoicing Desk (rates, monthly statements, receivables chase) - A - finance
94. Insurer / TPA Billing for Lab & Imaging (cashless approvals, pre-auth packs; HC#18, HO#80) - A - billing
95. Reagent-rental & Instrument-placement Contract Tracker (committed volumes vs actual) - A - procurement
96. Test-demand Forecaster (seasonal: dengue, monsoon, flu, health-check peaks) - A - planner
97. Capital-equipment Business-case Builder (new MRI / sequencer: volume, margin, payback) - A - CEO / CFO
98. GST, Accounting & Statutory Returns Assistant - A - finance
99. Marketing & Reputation Manager (reviews analysis, compliant claims; no "accuracy guaranteed" language) - B - marketing + medical director

### 12. Public-health, veterinary & specialised diagnostics
100. Public-health Lab Network Coordinator (district labs, sample referral to state labs, outbreak batches) - A - state lab officer
101. Veterinary Diagnostic Lab Assistant (species ranges, zoonosis flags, herd reports) - A/B - veterinary pathologist
102. Food & Water Testing Lab Assistant (FSSAI / BIS parameter sets, limits table, sample log) - A/B - analyst
103. Forensic / Toxicology Chain-of-custody Keeper (legal sample handling, no result interpretation) - A - forensic analyst
104. Drug-of-abuse & Workplace Screening Desk (consent, split sample, MRO hand-off) - A/B - medical review officer
105. Blood-donor Screening Lab Assistant (TTI test logs, deferral registry; HC#132) - A/B - blood-bank medical officer

### 13. Education & community
106. Pathology / Radiology Resident Case-bank Builder (de-identified teaching sets, quiz mode) - A - department head
107. Technologist Skills Tutor (MLT / radiography: pre-analytical errors, QC rules, Guru Sahayak) - A - faculty
108. Patient Education Sheet Writer (what the test measures, how to prepare; no diagnosis) - B - pathologist approves

## NEVER an AI Employee (tier C)
Release, amend or withdraw a report; write the interpretive comment or the impression; classify a variant or grade a
tumour; accept a QC run or declare a method verified; approve a critical-value script; decide a specimen's fitness
beyond a written rule; tell a patient or family what a result means; state a foetal sex; notify a notifiable disease
as the lab; approve an auto-verification rule or a referral arrangement; sign accreditation records.

## Suggested build order
1. **Wave 1 - pre-analytical + logistics + business (tier A)**: 2, 3, 4, 10, 11, 12, 15, 16, 17, 24, 25, 30, 72, 79, 83, 90, 91, 93.
2. **Wave 2 - quality and flags with a signer in the loop**: 14, 19-23, 55-60, 73-78, 84.
3. **Wave 3 - SaMD corner (needs governance HC#160 and a licensed reader)**: 38-40, 48, 51, 58, 62, 64, 65.
Fit to Hoola: department **"Diagnostics & Imaging"** beside Healthcare / Pharmacy / Devices; reuse Maps (4, 65), `queue`
(3), WhatsApp opt-in (10, 30), pylab (22, 27, 74, 75, 96), `health_int` (83, 86), research engine (39, 108), approval
cards for every signer step. Best first pilot: one 3-10 centre regional pathology chain with a home-collection business -
logistics pain is acute, the owner decides fast, and Wave 1 never touches a result.

## Open questions for the owner
- Which first: **pathology + collection** (high volume, simplest), **imaging centres / teleradiology**, or **genomics**?
- Should Hoola sit BESIDE the customer's LIS (read-only feeds + WhatsApp) or become the LIS for small labs? The second is
  a huge product and needs validation evidence for electronic records.
- Who holds the signing seat in the pilot - must be named (pathologist / radiologist / lab director) before any tier-B role.
- Pre-analytical logistics employees can ship without clinical review; the first report-touching employee (30) must
  pass the amended-report rule (77).
- "GO per field" turns each into a sourced report with ISO 15189 / NABL / AERB / PCPNDT text checked.
