# The healthcare industry, field by field — AI Employees register

Owner's ask (4 Nov 2026): *"DEEP RESEARCH ON HEALTHCARE INDUSTRY OF ENTIRE WORLD AND EXTRACT AI EMPLOYEES LIST FROM EVERY FIELD IN HEALTHCARE"*.

**23 fields, 160 candidate AI Employees.** Same method as `docs/research/building_industry/`: split every field into
jobs, then ask of each job what software may *prepare* and what a licensed human must *decide / sign*.

## How honest this is (read first)
- Web search in this session returned thin, mostly secondary pages (WHO nav pages, vendor blogs, law-firm guides).
  Only the facts under "Sourced" below were seen in a source. **The role register itself is domain knowledge, not a
  sourced census** - no page here lists "all healthcare jobs". Treat it as a structured first draft for the owner to
  prune, not as verified.
- Nothing here is built. Only one healthcare employee exists today: `health_int` (HL7/FHIR/ABDM paper desk,
  `server/app/enterprise/`, hire key `ent_health_int`).

### Sourced (seen this session)
- WHO: health workers sit in ISCO-08 sub-major group 22 (Health Professionals) and minor group 325 (Associate
  Professionals); care assistants 5321 / 5322. Global stock >70 million, ~67% women, projected 2030 shortfall
  revised up to ~11 million (was 10 million). Framework: Workforce 2030 (WHA 69.19), WHA78.16 (2025). -
  https://www.who.int/teams/health-workforce
- Admin AI is the part already moving: ambient scribes, coding, prior authorisation, appeals, balance collection;
  US CMS-0057-F gave payers 72 h (expedited) / 7 days (standard) decision times from 1 Jan 2026, and every denial
  in CMS's WISeR model is still decided by a licensed clinician. Vendor figures (e.g. "$360B savings") are
  directional only. - https://www.revelemd.com/blog/why-himss-2026-mattered-for-medical-practices
- India: CDSCO draft Medical Device Software guidance (Oct 2025) separates SiMD from SaMD, risk-classified; the
  Telemedicine Practice Guidelines 2020 let a registered practitioner consult remotely; ABDM (ABHA, Healthcare
  Professionals Registry), DPDP Act 2023 and IT Act 2000 apply to health data. Draft status to be re-checked on
  cdsco.gov.in. - https://practiceguides.chambers.com/practice-guides/digital-healthcare-2026/india

## The three findings that shape every desk

### 1. ASSIST / PREPARE / DECIDE - healthcare is gated at the *decision*, not the paperwork
Same shape as the building register's PREPARE/SUBMIT/CERTIFY. Every clinical act has a licensed decider
(registered practitioner, pharmacist, radiologist, QP, qualified person for pharmacovigilance, medical officer).
Software's safe ceiling is: **admin, documentation, retrieval, scheduling, coding, checking, drafting, reminders,
reconciliation, summarising** - and in clinical work **a second pair of eyes that raises a flag, never the final
call**. Three tiers used below:
- **A - Admin / prepare**: build first. No clinical judgement; wrong output costs time or money, not harm.
- **B - Clinical assist**: drafts or flags for a named licensed human who decides and signs. Needs the
  human-in-loop card on every output and a regulator check (SaMD).
- **C - Reserved**: the act itself (diagnose, prescribe, dose, triage-final, sign a report/certificate, deny a
  claim, release a batch). **Never an AI Employee.** Hoola drafts the file; the licensee acts.

### 2. Regulation is by function, and it differs by country - the desk must carry a country switch
| Area | India | US | EU/UK | Note |
|---|---|---|---|---|
| Practice | NMC / state councils; Telemedicine Guidelines 2020 | state boards | national councils | remote consult needs a registered practitioner |
| Software that diagnoses/treats | CDSCO MDR 2017 (SaMD draft 2025) | FDA SaMD / CDS rules | MDR + **EU AI Act high-risk** | tier B tools can become regulated devices |
| Health data | DPDP 2023, ABDM consent | HIPAA | GDPR special-category | consent + purpose-limit + minimum necessary |
| Drugs | Drugs & Cosmetics Act, Schedule H/H1/X | FDCA | EMA / MHRA | an AI never dispenses a scheduled drug |
| Sex-selection / abortion / mental health | PCPNDT, MTP, MHCA 2017 | state law | national | hard refusals, not tuning |
Hoola's existing rule already matches: money and sending go through a tap, and ID/health numbers sit in the
Pehchaan Locker with masked references.

### 3. The unowned room is administration (tier A), because that is where the people are
Clinical roles are 70M+ workers short by ~11M; admin, coding, billing, prior-auth, scheduling, supply, compliance
and documentation are where clinicians lose their time and where software carries no diagnostic risk. The build
order below follows that.

---

## THE REGISTER
Columns: **AI Employee** - what it does - tier - the human who decides. `*` = Hoola already has the plumbing.

### 1. Primary care, clinics, telehealth (GP, family medicine, OPD)
1. Appointment & Queue Manager - bookings, no-show chase, token queue (`queue` lane exists) - A - front desk
2. Clinic Receptionist (voice/WhatsApp) - FAQs, timings, directions, reschedules - A - clinic owner
3. Pre-visit Intake Assistant - collects history, meds, allergies into a form for the doctor - A/B - doctor reviews
4. Ambient Scribe - consult to SOAP note draft - B - doctor edits & signs
5. Follow-up & Recall Coordinator - vaccines, chronic review, lab-due reminders - A - doctor sets rules
6. Referral Coordinator - letters, tracking the loop closed - A - doctor
7. Teleconsult Ops Assistant - links, consent, e-prescription *draft*, payment - A/B - doctor signs
8. Patient Message Triage (inbox) - sorts admin vs clinical, flags red-flag words to a human at once - B - nurse/doctor

### 2. Hospitals - inpatient, ED, ICU, surgery, OT
9. Bed & Admission Flow Manager - bed state, discharge readiness, transfer - A - bed manager
10. Discharge Summary Drafter - from the chart - B - consultant signs
11. Rounds Prep Assistant - overnight events, trends, pending results per patient - B - doctor
12. ED Intake Assistant - registration, vitals capture, wait-time messaging - A - triage nurse
13. Early-Warning Watcher (NEWS2/sepsis-style flags) - raises, never orders - B - ICU/ward nurse (regulated if it predicts)
14. OT Scheduler - theatre lists, instrument sets, turnover - A - OT in-charge
15. Surgical Consent & Checklist Preparer - WHO checklist forms, consent packet - A - surgeon
16. Infection-Control Surveillance Assistant - clusters from lab data, hand-hygiene audit tallies - B - infection-control officer
17. Medical Records (MRD) Clerk - indexing, retrieval, record requests, legal copies - A - MRD head
18. Hospital Front-office / Insurance Desk - pre-auth packet, cashless intimation (Hoola `ins` lane) - A - TPA desk
19. Patient Experience / Complaints Handler - logs, routes, drafts replies - A - patient-relations head

### 3. Nursing, midwifery, allied health
20. Nursing Shift Planner - rosters, ratios, leave swaps - A - nurse manager
21. Handover (SBAR) Drafter - ward summary - B - outgoing nurse confirms
22. Medication-round Checker - flags schedule/allergy/duplication on the chart; does not give - B - nurse + pharmacist
23. Care-plan Drafter - nursing diagnoses & goals - B - nurse signs
24. Wound/Pressure-injury Tracker - photo series & healing curve - B - wound nurse
25. Physio / Rehab Plan Companion - exercise sheet, adherence tracking - B - physio
26. Dietitian Assistant - meal plans from rules, allergy checks - B - dietitian
27. Speech/Occupational Therapy Session Planner - A/B - therapist
28. Midwifery Partogram & ANC Visit Tracker - B - midwife/OB

### 4. Medical specialties
29. Radiology Worklist Prioritiser - ranks the queue, flags critical studies - B (SaMD) - radiologist reads & signs
30. Radiology Report Drafter - structured template pre-fill - B - radiologist
31. Pathology Slide Pre-screen - highlights areas - B (SaMD) - pathologist
32. Cardiology ECG/Holter Pre-reader - measurements, flags - B (SaMD) - cardiologist
33. Oncology Tumour-board Packet Builder - history, imaging, guideline refs - B - MDT
34. Oncology Trial-matching Assistant - eligibility screen - B - oncologist
35. Mental-health Check-in Companion - mood logs, PHQ-9/GAD-7 collection, crisis hand-off to a human line - B - clinician (never therapy, never diagnosis)
36. Ophthalmology Screening Pre-reader (diabetic retinopathy) - B (SaMD) - ophthalmologist
37. Dental Chair-side Scribe & Treatment-plan Estimator - A/B - dentist
38. Dermatology Photo Triage Organiser - B - dermatologist
39. Paediatric Growth & Vaccination Tracker (IAP/WHO charts) - A/B - paediatrician
40. Obstetrics Antenatal Schedule & Risk-flag List - B - obstetrician
41. Orthopaedics Pre-op Templating Assistant - B - surgeon
42. Anaesthesia Pre-op Assessment Collector - B - anaesthetist
43. Dialysis Session Log & Supply Planner - A - nephrology unit
44. Chronic-disease Coach (diabetes, BP, COPD, CKD) - reminders, logs, escalate abnormal readings - B - treating doctor

### 5. Diagnostics & laboratories
45. Lab Order & Sample-tracking Clerk - barcodes, chain-of-custody, TAT alerts - A - lab manager
46. Phlebotomy / Home-collection Scheduler - routes & slots (Hoola Maps) - A - lab ops
47. Result Delivery Assistant - sends reports only after release, explains reference ranges neutrally - A/B - pathologist released
48. QC & Calibration Logger (Westgard rules) - flags drift - B - lab director
49. Critical-value Caller - alerts the responsible clinician, logs acknowledgement - B - lab technologist
50. NABL/CAP/ISO 15189 Documentation Assistant - SOPs, audit packs - A - quality manager
51. Reagent & Consumable Reorder Planner - A - store in-charge
52. Genomics Report Assembler - variant list to template - B - geneticist signs
53. Imaging-centre Operations Assistant - slots, preps, radiation-dose log (AERB) - A - centre head

### 6. Pharmacy
54. Prescription Reader & Interaction Checker - reads script, checks interactions/doses, flags - B - pharmacist decides
55. Dispensing Workflow Assistant - queue, labelling, substitution *proposal* - A/B - pharmacist
56. Inventory & Expiry Manager - batch, FEFO, near-expiry markdown - A - store pharmacist
57. Schedule H/H1/X Register Keeper - audit-ready logs (the register itself, never the sale) - A - registered pharmacist
58. Refill-reminder & Adherence Companion - A/B - pharmacist
59. Hospital Formulary Assistant - formulary lookups, therapeutic-equivalent list - B - P&T committee
60. Medicine-price & Generic Finder (Jan Aushadhi, NPPA ceilings) - A - consumer/pharmacist
61. Compounding & IV Admixture Record Keeper - B - pharmacist

### 7. Pharma & biotech R&D
62. Literature Surveillance Agent - PubMed/preprints on a target, with citations (Hoola research engine) - A - scientist
63. Target / Hypothesis Brief Writer - B - research lead
64. Protocol Drafter - trial protocol skeleton from guidance - B - medical monitor
65. Site-feasibility & Recruitment Planner - A - clinical-ops lead
66. Informed-consent Document Preparer (plain-language, translations) - B - ethics committee approves
67. CRF / Data-management Assistant - query generation, reconciliation - A/B - data manager
68. Biostatistics Programmer Assistant - SAP tables, TLF shells (pylab sandbox) - B - statistician signs
69. Medical Writer - CSR sections, IB updates - B - medical writer/physician
70. Clinical-trial Registry Updater (CTRI, ClinicalTrials.gov) - A - sponsor

### 8. Pharmacovigilance, regulatory affairs, quality
71. Case Intake Processor - ICSR from emails/forms, MedDRA coding *proposal* - B - safety physician
72. Signal-detection Screener - disproportionality tables - B - PV physician (QPPV decides)
73. Aggregate-report Drafter (PSUR/PBRER/DSUR sections) - B - QPPV
74. Regulatory Dossier Assembler (CTD modules, eCTD checks) - A/B - regulatory head
75. Label & Artwork Change Tracker - A - regulatory
76. Submission-query Responder (drafts) - B - regulatory
77. Deviation / CAPA Drafter - A/B - QA head
78. Batch Record Reviewer (flags gaps) - B - QA; **batch release is reserved (C) - Qualified Person**
79. Audit-readiness Assistant (GMP/GCP/GVP mock audits) - A - QA
80. Stability-study Scheduler & Trend Plotter - A - QC

### 9. Pharma manufacturing & supply chain
81. Demand Forecaster (formulation-level) - A (pylab) - supply planner
82. Cold-chain Monitor - temperature excursions, vaccine VVM logs - B - QA/cold-chain officer
83. Distributor & Stockist Reconciler - A - sales-ops
84. Track-and-trace / Serialisation Checker - A - supply-chain QA
85. Counterfeit / Quality-complaint Handler - B - QA
86. Medical Representative Planner & Call Reporter (compliant with UCPMP) - A - sales manager

### 10. Medical devices & medtech
87. Device Classification & Pathway Advisor (CDSCO/FDA/MDR) - B - regulatory affairs
88. Technical-file / DHF Assembler (ISO 13485, IEC 62304, ISO 14971 risk file) - A/B - QA/RA
89. Complaint & Vigilance (MDR reports) Intake - B - vigilance officer
90. Biomedical Equipment Maintenance Scheduler (PM/CM, AMC, calibration) - A - biomedical engineer
91. Installed-base Service Dispatcher - A - field service
92. Clinical-evaluation Report Drafter - B - clinical-affairs lead
93. Cybersecurity SBOM Watcher for connected devices - A/B - product security

### 11. Payers, insurers, TPAs, government schemes
94. Policy Explainer & Eligibility Checker - A - insurer
95. Claim Intake & Document Completeness Checker - A - claims desk
96. Claim Adjudication Assistant - flags rule hits and missing proofs; **denial is reserved (C)** - B - claims medical officer
97. Fraud/Waste/Abuse Screener (duplicate, upcoding, ghost patients) - B - SIU investigator
98. Prior-authorisation Packager - gathers clinicals for the request - A/B - utilisation reviewer decides
99. Network & Empanelment Manager (hospital tariffs, credentialing) - A - provider relations
100. PM-JAY / Ayushman Bharat Claims Assistant (packages, HBP codes, pre-auth) - A - hospital scheme desk
101. Member Support Agent (cashless, reimbursement status) - A - member services
102. Underwriting Document Reader (declaration checks) - B - underwriter decides
103. Actuarial Data Preparer (pylab: loss ratios, claim triangles) - A - actuary signs

### 12. Revenue cycle, billing, coding
104. Medical Coder (ICD-10/11, CPT, PCS, SNOMED) *proposal* - B - certified coder
105. Charge-capture Auditor - A - billing manager
106. Claim Scrubber - A - billing
107. Denial-management & Appeals Drafter - A/B - billing lead
108. Patient-billing Estimator (price transparency) - A - billing
109. Collections Assistant (balance, payment links, plans; fair-practice rules) - A - finance
110. Package/Tariff Maintainer - A - finance
111. GST / TDS / Statutory Compliance for hospitals - A - finance head

### 13. Health IT, digital health, interoperability (builds on `health_int`)
112. Healthcare Integration Engineer * (HL7 v2, FHIR R4, ABDM M1/M2/M3 packs) - A/B - IT head
113. EHR/HIS Implementation Analyst - requirement to build sheets, test scripts - A - project lead
114. Terminology Mapper (SNOMED CT, LOINC, ICD) - B - clinical informaticist
115. Master Patient Index De-duplicator - match proposals only - B - MRD/HIM
116. Consent & Data-sharing Manager (ABDM consent artefacts, DPDP requests) - A - data protection officer
117. Health-app Compliance Reviewer (store policies, DPDP, SaMD scoping) - A/B - founder/legal
118. Clinical-informatics Dashboard Builder - A - CMIO
119. Cybersecurity & Breach-response Assistant (HIPAA/DPDP drills) - B - CISO
120. Wearable & Remote-monitoring Data Wrangler - A/B - care team

### 14. Public health & government
121. Disease-surveillance Analyst (IDSP-style signals, outbreak curves) - B - epidemiologist
122. Immunisation Programme Planner (U-WIN, cold chain, due-lists) - A - district immunisation officer
123. Health-campaign Communicator (multi-language messages, myth-busting from WHO/MoHFW) - A - health officer reviews
124. Health-scheme Navigator for citizens (eligibility, documents, nearest empanelled hospital) - A - CSC/ASHA
125. District Health Information Reporter (HMIS/DHIS2) - A - data officer
126. Maternal & Child Health Tracker (RCH, MCP card, ANC/PNC due list) - A/B - ANM/ASHA
127. Food-safety / Licensing Assistant (FSSAI) - A - officer
128. Air-quality & Heat-health Alert Drafter (Hoola Maps, no medical advice) - A - health authority
129. Disaster & Mass-casualty Coordinator - bed/blood/ambulance picture - B - incident commander

### 15. Emergency care, EMS, blood services
130. Dispatch Assistant - nearest unit (Maps matrix), address validation - A/B - dispatcher decides
131. Ambulance Crew Documentation Scribe - B - paramedic
132. Blood-bank Inventory & Donor Recall Manager - A - blood-bank officer
133. Organ-allocation List Preparer (registry data only) - B - transplant coordinator

### 16. Long-term, home, palliative and elder care
134. Home-visit Scheduler & Route Planner - A - agency
135. Caregiver Companion (medication prompts, family updates) - A/B - nurse
136. Fall/Activity Alert Responder (sensor feed to a human) - B - care staff
137. Palliative-care Symptom Diary Assistant - B - palliative physician
138. Elder-care Admin (insurance, pension, documents) - A - family/agency

### 17. Wellness, fitness, nutrition, sleep
139. Personal Wellness Coach (habit, step, sleep logs, non-medical) - A - none (stays non-clinical)
140. Diet & Meal Planner (IFCT food data, regional cuisines) - A/B - dietitian for conditions
141. Yoga/Exercise Plan Builder - A/B - trainer/physio
142. Corporate Wellness Programme Manager - A - HR

### 18. Traditional medicine (AYUSH, TCM, Kampo, Unani)
143. Ayurveda Clinic Assistant (prakriti questionnaire, pathya-apathya diet sheet, herb-name normaliser) - A/B - vaidya
144. Herb-drug Interaction Flagger - B - practitioner
145. AYUSH Product Licensing Assistant (AYUSH licence, claims limits under D&C / Magic Remedies Act) - A - regulatory
146. Panchakarma/Therapy Scheduler - A - clinic

### 19. Medical education, training, research
147. Exam-prep Tutor for MBBS/NEET-PG/nursing (Hoola Guru Sahayak) - A - faculty
148. Clinical Case Simulator (patient-actor roleplay) - A/B - faculty
149. Logbook & Competency Tracker (NMC CBME) - A - department
150. Continuing Medical Education (CME) Credit Tracker - A - council
151. Research-methods Assistant (sample size, protocol, ethics submission) - B - guide/PI
152. Systematic-review Screener - A/B - reviewers
153. Ethics-committee Secretariat Assistant - A - member-secretary

### 20. Hospital business & facility operations
154. Hospital Procurement Officer (tenders, rate contracts, vendor comparison) - A - purchase head
155. Biomedical Waste & NABH/JCI Compliance Tracker - A - quality head
156. HR & Credentialing Assistant (doctor licences, privileges, CPD expiry) - A - medical director
157. Facility & Energy Manager (OT air changes, medical gas, backup power) - A - engineer

### 21. Veterinary & One Health
158. Veterinary Clinic Assistant (booking, vaccination, species-specific dose tables as reference) - A/B - vet
159. Zoonosis & Antimicrobial-resistance Surveillance Analyst - B - public-health vet

### 22. Cross-cutting: AI governance & patient advocacy
160. Clinical-AI Governance Officer - model inventory, bias/drift checks, incident log for every tier-B employee above - B - AI governance committee. **This one is the gate for all the others.**

---

## What to NEVER make an AI Employee (tier C - drafts only, a licensee acts)
Diagnose; prescribe or change a dose; dispense a scheduled drug; final triage; sign or release a lab/radiology/
pathology report; certify death/fitness/disability; deny a claim; release a pharma batch; approve a trial
protocol or sign a CSR; decide organ allocation; sex determination; run therapy as a therapist; any patient
contact that implies the assistant is a clinician. This mirrors the building register: *"an agent that drafts
those certificates and lets the licensee sign is useful and lawful; an agent that signs or files them is forgery."*

## Suggested build order (owner decides)
1. **Wave 1 - tier A, one tenant-ready each**: Clinic Receptionist + Appointment Manager (1,2,5), Lab Ops (45,47),
   Pharmacy Inventory & Expiry (56,57), Billing/Claim Scrubber/Coder-proposal (104-107), Insurance/PM-JAY desk (18,100).
2. **Wave 2 - first tier B with the human-in-loop card**: Ambient Scribe (4), Discharge Summary (10), Med-round
   Checker (22), Prescription Checker (54).
3. **Wave 3 - the long tail** by field (pharma regulatory/PV, medtech QMS, public health), after 160 (governance)
   exists.
Fit to Hoola: group them in AI Employees > a new **"Healthcare & Life Sciences"** department (the hub already has
"Education, Research & Lab" and "Enterprise Systems & ERP"); `health_int` moves into it; tier-B roles use the
existing approval-card/trust-ladder rails; hire adds the desk and gates nothing (the v0.453 rule).

## Not done / open questions for the owner
- No sourced census exists yet; the next step would be primary sources per field (NMC/ICMR/CDSCO/FDA/EMA lists,
  ISCO-08 unit groups, NCO-2015 codes) - say "GO per field" and each becomes a sourced report like the building ones.
- Which wave first, and which country's rules lead (India assumed).
- The existing `employee/roles.py` structure has not been extended; this file is research only.
