# The hospital industry, department by department - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A HOSPITAL INDUSTRY AI EMPLOYEE LIST"*. Third in the series after
`docs/research/healthcare_industry/` (22 fields, 160 roles) and `docs/research/pharmacy_industry/` (17 fields, 118 roles).
This one walks a hospital from the front gate to the board room. Where a role already sits in those registers it is
cross-referenced (HC# = healthcare, PH# = pharmacy) instead of repeated.

**18 fields, 128 candidate AI Employees** (new ones; cross-refs not counted).

## How honest this is
- No new web research for this file (earlier healthcare searches returned only thin secondary pages). The register is
  **domain knowledge, not a sourced census**; standards named (NABH, JCI, NABL, AERB, PCPNDT, BMW Rules 2016, Clinical
  Establishments Act, PM-JAY HBP) are from memory and **must be re-checked on primary text** before building.
- Nothing is built. Hoola has relevant plumbing only: `queue` (clinic tokens), Khata ledger, Maps, Data Desk + pylab,
  `health_int` (HL7/FHIR/ABDM paper desk), approval cards, the Employee trust ladder.

## The findings that shape every hospital desk
### 1. A hospital is ~70% non-clinical work wrapped around a small licensed core
Registration, billing, TPA, records, stores, housekeeping, maintenance, compliance, HR, bed flow, reporting: all
tier A (no clinical judgement). The licensed core (diagnose, order, prescribe, operate, sign, certify) stays human.
Ladder as before: **A** admin/prepare, **B** assist (flag/draft for a named licensee), **C** reserved (never an AI).

### 2. The hospital's real bottlenecks are FLOW and DOCUMENTATION
Bed turnaround, discharge delay, OT idle time, ED boarding, lab TAT, insurance pre-auth wait, and the discharge
summary. An AI Employee that shortens a queue without touching a clinical decision is the safest high-value place.

### 3. Compliance is a calendar, not a document
Licences (Clinical Establishments, fire, bio-medical waste, AERB for X-ray/CT, PCPNDT for ultrasound, blood-bank,
pharmacy, lift, DG, pollution), NABH/JCI cycles, equipment calibration, staff credential expiry, vaccination and
drills. Missing one closes a ward. A tracker that never forgets is tier A and pays at once.

### 4. The clinical-AI rules from the first register still bind
Any tier-B role that predicts or classifies for patient care can become Software as a Medical Device (CDSCO draft
2025; EU AI Act high-risk; FDA). Each needs the human-in-loop card and the governance employee (HC#160).

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)

### 1. Patient access & front office
1. OPD Registration Assistant - ABHA/Aadhaar-masked lookup, UHID creation, duplicates flagged - A - registration head
2. Appointment & Doctor-schedule Optimiser - slots by consult length, overbooking guard - A - OPD manager
3. Queue & Waiting-time Messenger - token status on WhatsApp/screens (Hoola `queue` lane) - A - OPD manager
4. Wayfinding & Visitor Guide (voice/WhatsApp) - departments, timings, visiting rules - A - front-office lead
5. Health-check Package Coordinator - package sheets, fasting rules, report bundle - A - preventive-health lead
6. Pre-admission Counsellor - estimate, documents list, bed type options - A - admission desk
7. Inpatient Admission Clerk - admission note shell, consent packet, ID band data - A - admission desk
8. Call-centre Agent (24x7) - FAQs, bookings, ambulance requests routed to a human - A - call-centre head

### 2. Emergency & trauma
9. ED Triage Pre-sheet (see HC#12) - collects complaint/vitals; **triage category is the nurse's** - A/B - triage nurse
10. ED Tracking Board Keeper - patient status, wait, orders pending, disposition - A - ED in-charge
11. Trauma Team Activator Notifier - paging by criteria set by the hospital - B - trauma lead
12. Stroke / STEMI Pathway Clock - door-to-needle/balloon timers, missed-step alerts - B - physician on pathway
13. Medico-legal Case Documenter - MLC register, police intimation draft - A - ED doctor signs
14. ED Overcrowding Forecaster (pylab) - arrivals by hour, staffing prompt - A - ED head

### 3. Inpatient wards & nursing  (HC#20-28 cover the nursing set; new here)
15. Bed Management Controller (extends HC#9) - bed state, cleaning queue, transfers, predicted discharges - A - bed manager
16. Discharge Planner - flags patients likely ready, checklists (meds, bills, summary, follow-up) - A/B - ward doctor
17. Patient Call-bell & Request Router - request type to the right staff - A - nurse in-charge
18. Diet-order & Kitchen Coordinator - diet order to meal tray, allergy checks - A/B - dietitian
19. Fall-risk & Pressure-injury Screening Tracker (Morse/Braden scores recorded, not decided) - B - nurse
20. Visitor & Attendant Pass Manager - A - security/front desk
21. Bedside Education Sheet Giver - condition/post-op instruction sheets, multi-language - B - nurse/doctor approves

### 4. Intensive care & critical care
22. ICU Flowsheet Aggregator - vitals, vent, infusions, I/O into one trend view - A - ICU nurse
23. Ventilator-bundle & Line-care Checklist Tracker (VAP/CLABSI/CAUTI bundles) - B - ICU in-charge
24. Sedation/Delirium Screen Reminder (RASS, CAM-ICU timings) - B - ICU nurse
25. ICU Family-update Drafter - plain-language status, doctor-approved - B - ICU consultant approves
26. ICU Capacity & Step-down Planner - A - ICU head
27. End-of-life Documentation Assistant (advance directive forms, DNR paperwork shells) - B - treating consultant; law-gated

### 5. Operating theatre, surgery & anaesthesia  (HC#14, 15, 41, 42 exist)
28. Surgical Waitlist Prioritiser - urgency categories entered by surgeon, ordered list - A/B - surgeon/OT committee
29. Pre-op Readiness Checker - labs, consent, fasting, anaesthesia clearance, implant on order - A - OT coordinator
30. Implant & Consumable Preference-card Manager - per-surgeon kits - A - OT in-charge
31. Instrument Count & Sterile-set Tracker - A - OT nurse/CSSD
32. Intra-op Time-stamp Logger (WHO checklist timings, in-room, incision, out-room) - A - circulating nurse
33. Operative Note Drafter - from structured intra-op entries; **surgeon signs** - B - surgeon
34. Post-op Pathway & Early-discharge Tracker (ERAS items) - B - surgeon
35. Surgical-site Infection Follow-up Caller - day 7/30 check, flags to a nurse - B - infection control

### 6. Maternity, neonatal & paediatrics
36. Labour-ward Partogram Recorder (extends HC#28) - timed entries, alert-line flag - B - obstetrician
37. NICU Feed, Weight & Phototherapy Tracker - B - neonatologist
38. Newborn Screening & Vaccine Scheduler (BCG, hep B, hearing, metabolic) - A/B - paediatrician
39. Birth Registration & Certificate Application Helper (hospital forms; registrar acts) - A - records
40. Lactation & Postnatal Follow-up Messenger - A/B - lactation nurse/OB
41. PCPNDT Form F Register Keeper (ultrasound centres; never sex of fetus) - A - registered sonologist

### 7. Hospital diagnostics, blood bank & imaging  (HC#45-53 cover the lab set)
42. Phlebotomy Round Planner (ward draws, timing, labels) - A - lab in-charge
43. Lab-to-ward Result Router with Critical Alerts - B - technologist/ward doctor
44. Radiology Scheduling & Preparation Messenger (contrast, creatinine, fasting) - A - radiology manager
45. Radiation-safety Log Keeper (dose records, TLD badge tracking, AERB licence dates) - A - RSO
46. PACS/RIS Reconciler - orders vs images vs reports; missing-report finder - A - radiology admin
47. Blood-bank Crossmatch Queue & Inventory (extends HC#132) - request, units, expiry, wastage - A/B - blood-bank medical officer
48. Transfusion Reaction Reporter - report shell; haemovigilance - B - transfusion medicine doctor
49. Outsourced-test Sample Courier Tracker - A - lab

### 8. Pharmacy, CSSD & medical gases (see PH#13-21 for hospital pharmacy)
50. CSSD Cycle & Load Tracker - autoclave cycles, BI/CI results, set traceability - A - CSSD in-charge
51. Medical-gas Plant Monitor - manifold pressure, cylinder stock, alarm log - A - biomedical/engineering
52. Narcotic Cabinet Reconciler (see PH#19) - A/B - pharmacist in charge
53. Hospital Formulary & Indent Link (see PH#13, 14) - A - P&T

### 9. Allied health, rehabilitation & mental health  (HC#25-27 exist)
54. Rehab Session Scheduler & Home-programme Messenger - A - physio head
55. Clinical Psychology Intake & Scale Collector (PHQ-9, GAD-7, MoCA) - B - clinical psychologist
56. Social Worker Case Assistant - schemes, ID, ambulance, shelter, funds - A - medical social worker
57. Palliative Referral Finder (triggers list) - B - palliative physician
58. Speech/Swallow Screening Log - B - SLP
59. Audiology & Optometry Slot Planner - A - department

### 10. Quality, patient safety, infection control & accreditation
60. NABH/JCI Standards Tracker - clause-to-evidence map, gaps by department - A - quality head
61. Mock-audit (Tracer) Runner - generates tracer checklists, collects findings - A - quality manager
62. Incident / Near-miss Intake & Classifier - narrative to category *proposal*, no blame text - B - patient-safety officer
63. RCA & CAPA Tracker - 5-why templates, action owners, effectiveness check - A - quality
64. Hand-hygiene & Bundle Compliance Auditor (observation data, trends) - A - infection control
65. HAI Surveillance (NHSN-style definitions, lab + device days → rates) - B - infection-control nurse/ICO
66. Antibiogram Builder (yearly/ward, from lab data, pylab) - A/B - microbiologist
67. Outbreak Cluster Alert (same organism, same ward, same week) - B - infection-control committee
68. Clinical Audit & KPI Dashboard (door-to-needle, readmission, SSI, mortality) - A - quality head
69. Patient Feedback Analyst (reviews, forms, multi-language sentiment + topics) - A - patient-experience head
70. Consent Form Library & Version Controller - A - medical director
71. Mortality & Morbidity Meeting Packet Builder - B - clinical committee

### 11. Medical records, HIM & coding  (HC#17 MRD Clerk, #104 coder exist)
72. Chart Completeness Checker - missing signatures, summaries, consents before discharge - A - HIM head
73. Record Retention & Destruction Scheduler (legal retention periods, per law) - A - HIM head
74. Medico-legal / Court Record Request Handler (verify, log, prepare copy) - A - HIM/legal
75. Death Summary & MCCD Draft Shell; **certification by the certifying doctor** - B - treating doctor
76. ABDM Health-record Linker (FHIR bundles, consent artefacts via `health_int`) - A/B - IT/HIM
77. Research-data De-identifier (rule-based, audit trail) - B - data-protection officer

### 12. Revenue cycle & insurance  (HC#104-111 cover coding/billing/denials)
78. Bed-side Billing Capture (charges from orders; leakage finder) - A - billing head
79. Package-vs-actual Variance Analyst (PM-JAY HBP, corporate tariffs) - A - billing/insurance
80. Cashless Pre-auth Preparer (see HC#18) - A/B - TPA desk
81. TPA Query Responder (drafts reply from chart) - B - TPA desk
82. Final Bill Auditor - itemisation, duplicates, non-payables, discounts approval - A - billing head
83. Insurance Receivables Chaser - ageing, escalation letters - A - accounts
84. Patient Advance/Deposit & Refund Tracker - A - cashier
85. Charity-care / Concession Eligibility Screener (policy rules); **sanction by committee** - A/B - hospital administrator

### 13. Supply chain, stores & biomedical engineering
86. Hospital Procurement Officer (HC#154) - tenders, rate contracts - A - purchase head
87. Par-level & Auto-indent Planner for Consumables - A - store in-charge
88. Implant/High-value Item Traceability (patient-batch link) - A - stores
89. Expiry & Dead-stock Controller - A - stores
90. Biomedical Equipment Register & PM Scheduler (HC#90) - A - biomedical engineer
91. Equipment Downtime Predictor (logs, pylab) - B - biomedical head
92. AMC / CMC Contract Tracker & Invoice Checker - A - purchase/biomedical
93. Capital-equipment Business-case Builder - utilisation, ROI, alternatives - A - CEO/CFO decide
94. Vendor Performance Scorecard - A - purchase

### 14. Facility, engineering & support services
95. Bio-medical Waste Tracker (colour-category weights, manifest, BMW Rules 2016 returns) - A - waste officer
96. Housekeeping Task Dispatcher - bed turnover cleans, terminal cleans, checklists with photo - A - housekeeping supervisor
97. Linen Cycle & Stock Tracker - A - laundry in-charge
98. Kitchen Production & Food-safety Logger (FSSAI temperature logs) - A - catering manager
99. Engineering Rounds & Work-order Manager (HVAC, DG, lifts, UPS, water) - A - plant engineer
100. OT / ICU HVAC & Air-quality Monitor (differential pressure, air changes, particle counts) - B - infection-control + engineer
101. Energy & Water Optimiser (pylab on meter data) - A - engineer
102. Fire-safety & Mock-drill Planner (extinguisher expiry, NOC dates) - A - safety officer
103. Security & Access-control Assistant (visitors, newborn tag drill logs) - A - security head
104. Ambulance Fleet Dispatcher (Maps; extends HC#130) - A/B - transport manager
105. Mortuary Register Keeper - A - mortuary in-charge

### 15. HR, training & credentialing
106. Roster & Overtime Optimiser (nurses/doctors/support, labour law limits) - A - HR manager
107. Credentialing & Privileging File Builder (registrations, degrees, indemnity, expiry) - A - medical director
108. Mandatory-training & Immunisation Compliance Tracker (BLS, fire, hep B, flu) - A - HR/infection control
109. Recruitment Screener (JD match, interview slots; no auto-reject on protected traits) - A/B - HR
110. Locum / Visiting-consultant Payout Calculator (sharing rules) - A - accounts
111. Simulation & Skills-lab Scheduler - A - training head

### 16. Finance, administration & legal
112. Hospital Financial Controller - costing by department, payer mix, cash-flow forecast (pylab) - A - CFO
113. Statutory Compliance Calendar (licences, returns, GST/TDS, PF/ESI, NABH dates) - A - compliance officer
114. Legal & Consumer-case File Assistant (complaint, medical-negligence defence packet from records) - A/B - legal counsel
115. Contract Register & Renewal Watcher (vendors, doctors, TPAs, AMCs) - A - legal
116. Donations / CSR Utilisation Reporter - A - foundation head

### 17. IT, data & cybersecurity  (HC#112-120 exist for integration)
117. HIS Service-desk Agent (tickets, password-reset routing, downtime notices) - A - IT head
118. Downtime-procedure Pack Generator (paper forms, last-known census) - A - IT/nursing
119. Interface Monitor (HL7/FHIR message queues, failed-message alerts) - A/B - integration engineer
120. Backup & Disaster-recovery Test Logger - A - IT
121. Access-audit Reviewer ("break-glass", unusual chart access flags, DPDP/HIPAA) - B - privacy officer

### 18. Leadership, planning & patient experience
122. Hospital MIS Reporter - daily census, ALOS, occupancy, revenue, KPIs for morning huddle - A - administrator
123. Capacity & Service-line Planner (demand forecast, new-wing business case) - A - CEO
124. International Patient Desk (medical tourism: estimates, visas docs lists, interpreter booking) - A - IPD manager
125. Doctor-referral Relationship Tracker - A - business development
126. Community Outreach & Camp Organiser (health camps, screening logs, follow-up) - A - community-health lead
127. Hospital Marketing Compliance Checker (no outcome guarantees; NMC/ASCI/Consumer rules) - B - marketing + medical director
128. Board / Committee Secretary (agendas, minutes, action trackers) - A - hospital administrator

## NEVER an AI Employee (tier C)
Admit/discharge decision; triage category; diagnosis; orders, prescribing, dosing; consent taken as if staff;
sign a discharge summary, operative note, death certificate, MLC, or fitness/disability certificate; transfusion
release; sanction of charity or write-off; credentialing/privileging decisions; incident blame/disciplinary action;
speaking to a patient/family as a clinician.

## Suggested build order
1. **Wave 1 - flow & money (tier A)**: 3, 15, 16, 72, 78, 79, 82, 83, 95, 96, 113, 122.
2. **Wave 2 - compliance & support**: 60-64, 68, 90, 92, 102, 106-108, 117-119.
3. **Wave 3 - assist with human card**: 33, 22-24, 62, 65-67, 12, 36, 121, after HC#160 (AI governance) exists.
Fit to Hoola: department **"Hospital Operations"** under Healthcare; reuse `queue`, Khata (receivables), Maps (104),
Data Desk + pylab (14, 66, 91, 101, 112), `health_int` (76, 119), approval cards. Pilot with one small nursing home or
single-speciality hospital before multi-speciality; their IT is simpler and the owner decides fast.

## Open questions for the owner
- Target: nursing home (20-50 beds), mid-size hospital, or chain? The first changes Wave 1 (most small hospitals lack a HIS,
  so Hoola would BE the system of record: much bigger, risky).
- Which HIS vendors to integrate first (India: Practo-class, Insta, Medixcel, Epic abroad)?
- Patient-data hosting: Indian region only? DPDP and ABDM consent text to be written before any chart-touching employee.
- "GO per field" turns each into a sourced report with the primary regulations checked.
