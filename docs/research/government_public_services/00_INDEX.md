# Government & public services across the world - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A GOVERNMENT AND PUBLIC SERVICES INDUSTRY AI EMPLOYEES"*. Seventeenth in the series. Government and public
services here means: citizen-facing services and e-governance, local government (municipal, panchayat), revenue and land administration,
taxation and customs, public finance and procurement, social-welfare schemes and entitlements, policing, courts and legal aid, elections,
transport and licensing, utilities (power, water, sanitation, waste), urban and rural planning, environment and forests, disaster management,
civil-service HR and training, legislatures and policy, audit and oversight, statistics and open data, libraries/archives/museums, postal
and public broadcasting, and the NGOs, consultants and citizens who deal with them. Health, education, agriculture and housing slices have
their own registers; they are cross-referenced, not repeated.

**12 fields, 129 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Laws and schemes named are
  from memory and **must be re-checked on primary text per country, state and department** before any desk is built: in India the
  Constitution's allocation of subjects, RTI Act 2005, CPGRAMS, e-Office, DigiLocker/UMANG, the Aadhaar Act and its Supreme Court limits,
  DPDP Act 2023 (with its state exemptions), IT Act 2000, General Financial Rules 2017 and GeM, CVC/Lokpal, BNS/BNSS/BSA 2023, eCourts/NJDG/
  CCTNS, ECI rules and the model code of conduct, GST/Income-tax/Customs law, Motor Vehicles Act and Vahan/Sarathi, municipal and panchayat
  acts, RERA, environmental and forest clearances, Disaster Management Act 2005; abroad GDPR Article 22 on automated decisions, the EU AI
  Act (public-benefit eligibility, law enforcement, migration, justice, elections and critical infrastructure are listed high-risk or
  prohibited uses), US APA / FOIA / Privacy Act, UK Equality and Human Rights duties. Public-sector rules vary far more than private ones.
- **Already in Hoola** (extend, do not rebuild): the Computer Operator ("Online form, sarkari portal, bill/certificate download, status
  check, application": the system types ID numbers from the Pehchaan Locker, **OTP / submit / payment remain the user's**), Pehchaan
  Locker (masked IDs), MoSPI official statistics, Bazar connectors, `appmaker` (departmental apps, `appmaker/connect.py` declared HTTP
  actions with her approval tap, signed hooks), Maps (service-centre routes, ward boundaries), WhatsApp opt-in and voice (Indian languages),
  doc studio + HOOLA PRINT (notices, certificates drafts), research engine with citations, Data Desk + pylab, Shodh (research), Khata,
  and the agriculture register's scheme navigator. Roles with `*` exist in some form. The Mera-PC freeze is untouched.

## The findings that shape every government desk
### 1. The authority is statutory and personal: a named officer decides; an AI never holds a public power
Ladder as before: **A** admin/prepare, **B** assist (check / draft / summarise / route for a named officer), **C** reserved.
Reserved here: any decision that grants, denies, cancels or fines (benefit eligibility, licence, permit, tax assessment, visa, pension,
arrest, bail, sentence, judgment, penalty), orders to officials, issuing a certificate or title, signing a sanction, awarding a tender,
elections-related determinations, security clearances, policy choices, and any use of force. Public power is delegated by law to people,
subject to appeal and judicial review; **an automated decision with legal effect needs a human reviewer, reasons, notice and an appeal
route** (GDPR Art. 22, Indian administrative-law principles of natural justice, EU AI Act). **The AI explains, prepares, routes and
tracks; the officer decides and signs.**

### 2. Citizens' pain is queues, forms, rejections, no-status and not knowing their rights
Ten documents for one certificate, offices that are far, rules that differ by state, "come tomorrow", lost files, agents who charge, benefits
that exist but are unclaimed, grievances that vanish. The clearest, most defensible AI value is **on the citizen's side**: which scheme and
document applies, correct forms, queue/slot booking, status chasing, deadlines, grievance and RTI drafting, translations into plain local
language, accessibility, and scam warnings, plus on the department side, intake triage, completeness checks, drafting and records.
Digital divide is the risk: voice, local languages and assisted modes (CSC, ASHA, anganwadi) are not optional.

### 3. Officials drown in files, notes, queries and reports
Government work is note-sheets, file movement, parliamentary/assembly questions, RTI replies, court cases, audit objections, MIS
returns, and review meetings. Drafting, summarising, file tracking, deadline watching and reconciliation are tier A/B, with the officer
owning every word. Records law applies: files are public records, retention and archival rules, RTI exposure; the AI never deletes or
alters a record and logs everything.

### 4. Fairness, transparency and rights are the product, not an add-on
Welfare and enforcement AI have caused real harm abroad (benefit denial by faulty fraud models; biased predictive policing; facial recognition
errors). The register therefore: **forbids** predictive policing/social scoring, mass biometric identification, emotion recognition, and
automatic benefit termination; **requires** explainability, a named reviewer, notice, appeal, bias testing, data minimisation, and
public registers of systems in use. Every high-stakes tool is tier B at most.

### 5. Security, secrecy and procurement integrity
Citizen data is sensitive; classified material must never touch a general model; vendors and models need security clearance and audit;
procurement follows strict rules (GFR/GeM, transparency, no favouritism). Insider threats and corruption are real: every employee below
carries role-based access, immutable logs and no standing credentials.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [C] citizen/business/NGO, [D] department/officer, [L] local government, [J] justice and law-enforcement, [P] policy/oversight, [E] elections/legislature.

### 1. Citizen services & e-governance  [C]
1. Government Services Guide - one place: "what do I need for X" (birth/caste/income certificate, ration card, pension, licence, passport), documents, fees, office, time, with the official source and date; works in voice and local languages - A - citizen
2. Document Locker Assistant - organises the user's certificates (DigiLocker links, scans, expiry reminders, renewals, family members' set); masked IDs in the Pehchaan Locker - A - citizen
3. * Government Portal Operator (existing computer operator) - fills forms from the locker, uploads, checks status, downloads certificates; **OTP, captcha confirmation, fee payment and final submit are the user's** - A - citizen
4. Application Tracker - all open applications, status, next step, deadlines, escalation ladder; drafts reminders to the right office - A - citizen
5. Appointment & Queue Booker (RTO, passport, registrar, hospital OPD, ration shop slots where official systems allow) - A - citizen
6. Grievance Drafter (CPGRAMS, state portals, local ward complaints): facts, rule cited, relief asked, evidence list, escalation levels - A/B - citizen
7. RTI Assistant (finds the Public Information Officer, drafts the application with precise questions, fee instructions, first-appeal timeline; reads replies) - A/B - citizen
8. Scheme Entitlement Navigator (central + state schemes: eligibility screening by the user's data, documents, application route, deadlines; honest "may be eligible" with the rule shown; **department decides**) - B - citizen / CSC
9. Common Service Centre (CSC) Operator's Assistant (service catalogue, fee schedule, document checklist, form filling on citizen's behalf with consent, receipts log) - A - VLE
10. Assisted-mode Voice Agent (kiosk/phone voice in dialects for those who cannot read or type; slow pace, repeat, privacy prompts) - A - citizen / helper
11. Senior-citizen & Disability Access Helper (pension, concessions, accessibility rights, UDID, assistive service booking; plain language) - A - citizen / carer
12. Business Registration Helper (Udyam/MSME, GST, shop licence, FSSAI, trade licence: sequence, forms, costs; **filing on the owner's tap**) - A - entrepreneur
13. Migrant & Gig-worker Benefits Navigator (e-Shram, portable ration, BOCW welfare board, insurance, remittance and ID steps) - A - worker / NGO
14. Notice & Letter Explainer (reads a government notice - tax, municipal, police, court, utility - and explains what it means, deadlines, options; **not legal advice, advocate/CA referral rules**) - B - citizen
15. Scam & Fake-official Detector (fake government websites/apps/calls, "arrest" and "KYC" scams, fee-for-service agents; official-channel pointers) - A/B - citizen
16. Public Information & Alerts Companion (heat, floods, curfews, polling day, water cuts, vaccination drives, official sources only) - A - citizen
17. Citizen Feedback & Co-design Assistant (surveys, ward meetings summaries, participatory budgeting inputs, multilingual) - A - department
18. Public Service Quality Auditor (mystery-shop style complaint analytics from public data: wait times, rejection reasons; no individual shaming) - B - oversight body

### 2. Department back-office & e-office  [D]
19. File Note Drafter (summarises file history, applicable rules, options, draft note for the officer; **officer owns the note**) - B - section officer
20. File & Case Tracker (e-Office/physical movement, pendency ageing, reminders to desks, bottleneck report) - A - department head
21. Draft Reply Assistant (public queries, assembly/parliament question replies, RTI responses; fact checks with sources; **PIO/officer signs**) - B - officer
22. Policy & Circular Librarian (versioned rules, GRs, circulars, amendments, search with citations; supersession map) - A - department
23. Meeting Secretary (review meetings, action trackers, minutes, follow-ups) - A - officer
24. Translation & Plain-language Editor (official documents to regional languages and simple versions; glossary control) - B - language officer
25. Records Management Assistant (classification, retention schedules, archival transfer lists, public-records law compliance; **no deletion without authority**) - A - record officer
26. Data & MIS Compiler (returns from subordinate offices, validation, dashboards, discrepancy queries) - A - MIS officer
27. Inspection & Field-visit Planner (risk-based schedule, checklists, travel (Maps), report templates; findings by inspectors) - A - inspecting authority
28. Training Needs & Learning Assistant for Civil Servants (competency gaps, iGOT-style courses, micro-lessons in local language, completion tracking) - A - training officer
29. Leave, Transfer & Service-book Assistant (rules lookup, forms, entitlement calculators; **competent authority decides**) - A/B - establishment officer
30. Vigilance & Conduct Rule Navigator (gift/conflict/outside-employment rules explained, declarations tracker; **no accusations**) - B - vigilance cell
31. Departmental Budget Tracker (allocation vs expenditure, SNA flows, utilisation certificates, reappropriation proposals) - A - finance officer
32. Audit Objection Responder's Assistant (CAG paras tracking, reply drafts, compliance evidence, ATN timelines) - B - nodal officer
33. Court Case Monitor for Departments (cases list, hearing dates, counter-affidavit deadlines, advocate instructions pack; **advocate files**) - A - legal cell
34. Crisis & Emergency Desk Assistant (control-room logs, resource lists, SOP prompts, situation reports; **incident commander decides**) - B - control room

### 3. Local government: municipal & panchayat  [L]
35. Ward/Panchayat Citizen Desk (property tax queries, water/sanitation complaints, certificates, trade licence, local services, ward office routing) - A - ward officer
36. Property-tax Assistant (assessment records, dues, rebates, notices, payment links on citizen's tap; objections drafting) - A - tax collector
37. Building-permission Scrutiny Assistant (drawing checks vs bye-laws with clause references, document completeness, query letters; **approval by licensed authority**) - B - building officer (see Construction register)
38. Solid-waste Collection Planner (routes by Maps, bin/pickup logs, fleet, complaints, segregation drives) - A - sanitation officer
39. Water & Sanitation Operations Assistant (supply schedules, leak reports, quality test logs, tanker scheduling, billing; **plant operations by engineers**) - A/B - water engineer
40. Street-light, Road & Drain Complaint Router (geotagged reports, contractor work orders, closure photos, SLA clocks) - A - engineering section
41. Local Budget & Works Monitor (works register, bills, measurement, progress, MGNREGA-type muster checks; **engineer certifies**) - A/B - junior engineer / PO
42. Gram Sabha & Panchayat Secretary's Assistant (agenda, minutes, resolutions, beneficiary lists, social audit, village plans) - A - panchayat secretary
43. Urban Planning Analyst (land-use maps, population, transit, flood layers via Maps/GIS, scenario tables; **planners decide**) - B - town planner
44. Markets, Licences & Hawker Management (licence registers, renewals, fee tracking, stall allocations by rule) - A - licensing inspector
45. Public Facilities Booking (halls, grounds, libraries, sports facilities: calendar, fee, approvals) - A - facility manager
46. Smart-city / Command-centre Analyst (traffic, CCTV metadata, sensors; privacy-bound; no facial recognition or social scoring) - B - city IT
47. Public Transport Assistant (timetables, route planner, fare info, delay alerts, accessibility info, complaints; scheduling suggestions to the operator) - A/B - transit authority
48. Street Vendor & Informal Worker Registry Assistant (survey data, ID, scheme linkage, vending certificate steps) - A - ULB

### 4. Revenue, land & registration  [D]
49. Land Records Reader (extracts, mutation status, maps, ownership timelines; **no title opinion**) - A - revenue officer / citizen
50. Mutation & Registration Case Assistant (document checks, notices, objections tracking, fee calculators; **tehsildar/sub-registrar decides**) - B - revenue clerk
51. Survey & Boundary Support (GIS overlays, survey numbers, boundary disputes timelines; surveyors decide) - B - land survey officer
52. Revenue Collection Tracker (land revenue, arrears, recovery notices, receipts) - A - revenue officer
53. Land Acquisition & Compensation Calculator (statutory formula, consent tracking, award drafts; **collector decides**) - B - land acquisition officer
54. Stamp & Registration Valuation Assistant (circle rates, exemptions, duty calc, under-valuation flags) - B - registrar
55. Encroachment & Government-land Monitor (satellite change detection as a *lead* only, field verification required) - B - revenue inspector

### 5. Taxation, customs & public finance  [D]
56. Taxpayer Helpdesk (return filing steps, notices explained, due dates, refund status, TDS/GST reconciliation help; official portals on the user's tap) - A - taxpayer
57. Notice Triage for Tax Departments (classification, deadlines, completeness; **assessment/adjudication by officers**) - B - assessing officer
58. Compliance Risk Screener (rule-based risk indicators from filings and third-party data; explainable; flags for human scrutiny, never auto-demand) - B - risk cell
59. GST Return Reconciliation Assistant (departmental side: mismatch lists, ITC anomaly patterns, outreach letters; **officers act**) - B - GST officer
60. Customs Documentation Reviewer (declaration checks, HS code consistency, valuation red flags; **proper officer decides**) - B - customs officer
61. Public Finance Analyst (budgets, outcome budgets, subsidy flows, tax expenditure, debt sustainability; pylab, sources) - A - finance analyst
62. Treasury & Payment Reconciliation Assistant (DBT status, bank rejects, beneficiary data fixes; **payments authorised by DDO**) - A/B - treasury officer
63. DBT Failure Resolver (name/account mismatch, Aadhaar seeding issues, NPCI mapper checks; drafts beneficiary outreach) - A - welfare officer
64. Revenue Forecasting Assistant (tax buoyancy models, scenarios, uncertainty bands) - B - finance department

### 6. Public procurement & infrastructure projects  [D]
65. Tender Drafting Assistant (technical specs from templates, eligibility criteria, evaluation criteria, GFR/CVC compliance checks, clause libraries; **approval by tender committee**) - B - procurement officer
66. Bid Evaluation Assistant (checklists, document verification, price comparison tables, anomaly flags such as cartel patterns; **committee decides; no auto-award**) - B - tender evaluation committee
67. Vendor & Contract Monitor (contract register, milestones, penalties, extensions, bank guarantees expiry) - A - contract manager
68. Project Monitoring Assistant (physical/financial progress, photo evidence, delay causes, escalation; PMIS dashboards) - A - PMU
69. Quality & Audit Support for Works (test result registers, third-party reports, measurement books checks) - B - quality control cell
70. Anti-corruption Pattern Watcher (conflict-of-interest links, unusual award patterns, split purchases; leads to vigilance) - B - vigilance officer
71. GeM / e-Procurement Helper for Vendors (registration, catalogue, bid steps, documents; MSME benefits) - A - vendor
72. Public-asset Register Keeper (buildings, vehicles, equipment; maintenance, condemnation, insurance) - A - estate officer

### 7. Social welfare, protection & public health admin  [D/C]
73. Beneficiary Registry Assistant (de-duplication, eligibility rule application with printed reasons, verification workflow; **inclusion/exclusion decisions by officer; grievance route mandatory**) - B - welfare officer
74. Pension & Entitlement Processing Assistant (case documents, calculations, life-certificate reminders, grievance; **sanction by authority**) - B - pension officer
75. Child Protection Case Tracker (CWC cases, institutional care register, follow-up dates, restricted access; **decisions by CWC**) - A - child-protection officer
76. Women Safety & Support Services Assistant (helpline logs, shelter availability, legal-aid links, protection-officer case tracking; trauma-informed scripts; humans lead) - B - protection officer
77. Disability Services Coordinator (assessment appointments, certificates, aids distribution, scholarships) - A - social-welfare officer
78. Anganwadi & Nutrition Programme Assistant (growth records, supplementary nutrition stock, home-visit lists, local-language voice; health referrals by workers) - A - ICDS supervisor
79. Public Distribution System (PDS) Monitor (ration shop stocks, e-POS transactions, portability, leakage anomalies; field verification) - B - food officer
80. Labour & Employment Services (employment exchange, skill matching, MGNREGA job cards, wage payment delays, grievance) - A - labour officer
81. Disaster Relief Beneficiary Manager (damage claims, panchnama tracking, compensation status, camp registers) - A - relief officer
82. Public Health Programme Admin (immunisation due lists, supply chains, notifiable-disease report intake; cross-ref healthcare register) - A/B - district health officer
83. Public School Administration Assistant (UDISE+, enrolment, teacher postings, mid-day meal logs; cross-ref education register) - A - block education officer

### 8. Policing, courts, legal aid & corrections  [J]
84. FIR/Complaint Intake Assistant (structured intake of the citizen's account, language support, legal-sections *suggestions for the officer to consider*, receipt and zero-FIR info; **registration and sections by officer**) - B - police station staff
85. Case Diary & Chargesheet Drafting Aid (timeline, evidence index, witness list, forms; **investigating officer owns**) - B - investigating officer
86. Digital Evidence Handler (hash logs, chain of custody, extraction request forms; no analysis conclusions) - A - forensic unit
87. Crime Data Analyst (descriptive statistics, hotspot maps, resource planning; **no predictive policing, no individual risk scores**) - B - police analyst
88. Missing-person & Lost-property Desk (record matching, public alerts per policy, family liaison scripts; humans act) - A/B - police station
89. Traffic Enforcement Assistant (challan data, notices, disputes workflow, black-spot analysis; **penalty issuance by authorised officer**) - B - traffic police
90. Court Registry Assistant (e-filing checks, defect lists, cause-list tracking, notices, service records) - A - court staff
91. Judge's Research & Drafting Assistant (case law retrieval with verified citations, chronology, issue lists, draft orders for the judge's edit; **judge decides and signs; hallucination controls mandatory**) - B - judicial officer
92. Litigant Guide (court procedures, forms, fees, legal aid eligibility, hearing prep checklist, plain-language explanations; **not legal advice**) - A/B - litigant
93. Legal Aid Intake Assistant (eligibility screening, case type routing, documents, panel lawyer scheduling) - A - legal-services authority
94. Case Pendency & Scheduling Analyst (adjournment patterns, listing efficiency; **no judge/lawyer ranking**) - B - court administrator
95. Prison Administration Assistant (inmate records, visitation, medical, parole file tracking, release-date calculators; **releases by authority**) - B - prison officer
96. Probation, Rehabilitation & Reintegration Tracker (check-in scheduling, services, job linkage; **officer decides**) - A - probation officer
97. Notary, Registrar & Document-attestation Assistant (checklists, fee, appointment) - A - registrar

### 9. Elections, legislature & democratic process  [E]
98. Voter Services Assistant (find polling booth, check roll entry, forms 6/7/8 steps, EPIC status, accessibility facilities; official links only) - A - voter
99. Election Logistics Planner (booth lists, staff rosters, material and EVM movement logs, transport routes via Maps, training tracking; **returning officer decides**) - A - election office
100. Voter-roll Quality Assistant (duplicate detection leads, address changes, death records; **field verification and deletion by ERO under notice**) - B - ERO
101. Election Expense & Model-Code Monitor (spending returns checks, complaint intake, ad registers; **enforcement by authorised officials; no partisan targeting**) - B - election observer
102. Legislative Research Assistant (bill tracking, committee reports, comparative laws, question drafting support for members; non-partisan, sources cited) - B - legislator's office
103. Constituency Service Desk (MP/MLA/councillor offices: case intake, referral to departments, follow-up tracking, public meetings) - A - constituency office
104. Legislative Drafting Aid (consistency checks of terms, cross-references, amendments tables; **drafter and legislature decide**) - B - legislative drafter
105. Parliamentary/Assembly Records Assistant (debates search, vote records, speech indexes in local languages) - A - library / secretariat
106. Political Neutrality & Misinformation Guard (flags deepfakes, false claims about voting, official fact-check pointers; no partisan content generation on behalf of parties) - B - election commission / platforms

### 10. Transport, licensing & utilities  [D/C]
107. Driving-licence & Vehicle Services Assistant (learner/permanent DL, RC, fitness, permits, tax, challans: steps, documents, slot booking via Vahan/Sarathi on the user's tap) - A - citizen / RTO
108. RTO Back-office Assistant (document checks, test scheduling, permit registers, fee reconciliation; **licence/permit issue by RTO**) - A/B - RTO staff
109. Road Safety Analyst (accident data, black spots, enforcement planning; humane framing; no blame scoring) - B - road-safety cell
110. Electricity Utility Customer Assistant (new connection, billing, outage, meter, subsidy; **disconnection per rules and regulator**) - A - discom support
111. Utility Operations Analyst (loss analytics, feeder loading, outage correlation; proposals to engineers) - B - discom engineer
112. Water Utility Quality & Billing Assistant (consumer metering, leakage, quality lab logs) - A/B - water utility
113. Public Transport Operator's Assistant (rostering, fleet maintenance, fare reconciliation, real-time feeds) - A - transit operator
114. Airport/Port/Railway Passenger-services Guide (public information, accessibility, grievances; operational decisions by operators) - A - public-sector undertaking

### 11. Environment, forests, disasters & climate  [D/P]
115. Environmental Clearance & Compliance Tracker (conditions, monitoring reports, return deadlines for projects; **authority decides**) - A/B - regulator / project
116. Pollution Monitoring Analyst (AQI, water quality data, source apportionment from public stations, alerts; official advisories only) - A/B - pollution control board
117. Forest & Wildlife Records Assistant (patrol logs, human-wildlife conflict reports, plantation records, GIS) - A - forest officer
118. Disaster Early-warning Communicator (official alerts in local languages across WhatsApp/voice, evacuation info, shelter locations; **alerts originate from the authority**) - A - disaster authority
119. Disaster Preparedness & Response Planner (risk maps, resources, drills, supply routes, volunteer rosters) - B - disaster management officer
120. Post-disaster Damage & Needs Assessor (photo/satellite aided estimates as *leads*, field verification, relief calculations) - B - relief commissioner
121. Climate Adaptation Planner (district/city risk, heat-action plans, flood plans, cost-benefit scenarios; pylab) - B - planner

### 12. Statistics, oversight, policy & education of the public  [P]
122. Official Statistics Assistant (MoSPI/NSO tables, indicators with definitions and caveats, simple charts; source and date shown) - A - citizen / analyst
123. Open-data Publisher (de-identification, metadata, API publishing, dataset documentation; privacy review) - B - data office
124. Policy Evaluation Assistant (programme data, difference-in-differences design suggestions, outcome indicators; honest limits) - B - evaluator
125. Parliamentary/Audit Report Reader (CAG reports, committee findings: summaries, recommendations tracker, follow-up status) - A - citizen / journalist
126. Public Consultation Analyst (comments on draft rules: clustering, representative quotes, stakeholder mapping; **officials respond**) - B - policy unit
127. Civic Education Tutor (rights, duties, how government works, budgeting, voting; non-partisan; schools and adults) - A - educator
128. Foreign Affairs & Consular Services Assistant (passport/visa/PCC/attestation steps, embassy appointments, emergency contacts; official sites only) - A - citizen / consular staff
129. Libraries, Archives & Museum Assistant (cataloguing, digitisation QC, public queries, accessibility, rights metadata) - A - library / archive

## NEVER an AI Employee (tier C)
Grant, deny, cancel or suspend a benefit, licence, permit, visa, tax assessment or pension; register or close an FIR, make an arrest decision,
decide bail, sentence or judgment; order demolition, eviction, attachment or deletion from the voter roll; award a tender; issue a
certificate, title or sanction; decide a disciplinary matter; use facial recognition for mass identification, predictive policing, social
scoring or emotion recognition; target voters or generate partisan campaign content for a party; surveil protest or press;
file or sign anything as a public authority; access or train on classified material; delete or alter a public record; bypass a human
reviewer, notice or appeal for an automated decision; pay or take money for official services.

## Suggested build order
1. **Wave 1 - citizen side and CSC (tier A, no public power)**: 1-8, 10, 14-16, 98, 107, 122, 127 - voice-first, local languages, extending the existing portal operator, locker, MoSPI and WhatsApp/voice stack.
2. **Wave 2 - department assist with a named officer**: 9, 19-26, 28, 31, 33, 35, 36, 38, 40-42, 56, 61, 65, 67, 68, 90, 103, 108.
3. **Wave 3 - sensitive, rights-affecting or oversight roles (only with legal review, bias testing, notice and appeal)**: 37, 57-60, 66, 73, 74, 84-87, 91, 95, 100, 101, 106.
Fit to Hoola: department **"Government & Public Services"**; the citizen-side Wave 1 is Hoola's natural fit (her avatar standing in the queue for her) and
extends the Computer Operator, Pehchaan Locker, MoSPI, Maps, voice calls, WhatsApp and `appmaker`. Department-side pilots must use the declared-action layer
(`appmaker/connect.py`: her approval tap bound to a hash, https + approved host, private IPs refused, no Aadhaar), sealed secrets, and Hoola's audit trail.
**Best first pilots**: (a) a **citizen "Sarkari Sahayak"** for Hindi/Marathi users (1-8, 14-16) with a **CSC/VLE** companion (9) - mass-market, no public power touched,
trust-building; (b) a **gram panchayat or ward office** (35, 36, 42, 40) - a small, visible deployment with an elected body that wants to look responsive; (c) a
**courts-and-police-adjacent litigant guide** (92, 93) only after legal review. Large departments come later: procurement, security audits and policy approvals are slow.

## Open questions for the owner
- Which side first: **citizens** (mass, trust, no sales cycle), **CSC / panchayat / municipal offices**, **state departments** (tenders, long cycles), or **justice/
  law-enforcement-adjacent tools** (highest risk)? I'd start with the citizen Sarkari Sahayak and CSC/panchayat pilots.
- Government procurement and hosting: Indian data residency, MeitY empanelment and security audits will be required for departments; confirm whether Newtika wants to
  pursue empanelment or stay on the citizen/NGO side first.
- Red lines: confirm no predictive policing, no facial recognition, no social scoring, no partisan political content, no automatic benefit denial. These are policy, not
  just engineering, and should be written into the product's public terms.
- Official routes only: Hoola never scrapes or logs in to a portal on someone's behalf without that person's tap; OTP, captcha confirmation, payment and final submit remain
  the citizen's. Confirm this stands for CSC-operated sessions.
- "GO per field" turns any field into a sourced report with the RTI Act, GFR, DPDP, BNSS and state laws checked on primary text.
