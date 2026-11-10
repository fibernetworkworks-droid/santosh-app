# The legal & professional services industry across the world - AI Employees register

Owner's ask (5 Nov 2026): *"NOW A LEGAL AND PROFESSIONAL SERVICES INDUSTRY AI EMPLOYEES"*. Twenty-third in the series. Legal and professional services here means:
advocates, law firms and in-house legal teams; courts-facing litigation practice; corporate and commercial law; intellectual property; arbitration, mediation and legal aid;
notaries, document writers and registrars; chartered accountants, auditors and tax practitioners; company secretaries; consultants (management, engineering, IT, ESG); HR, recruitment, staffing and
payroll firms; BPO/KPO and IT-services shops; valuers, surveyors and translators; and the bar councils, institutes and regulators that license them. Banking/finance practice (CA work for
companies) was partly covered in the finance register (BF#101-118); government courts and registries in the government register (GV#84-97); both are cross-referenced, not repeated.

**13 fields, 138 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Rules named are from memory and **must be re-checked on primary text per country and profession**
  before any desk is built: in India the Advocates Act 1961 and Bar Council of India Rules (including the limits on advertising and solicitation, duty of confidentiality, and professional conduct),
  the Bharatiya Sakshya Adhiniyam 2023 provisions on privileged communications, BNS/BNSS, CPC, the Limitation Act, the Arbitration and Conciliation Act, the Mediation Act 2023, IBC, the Companies Act
  and LLP Act, ICAI and ICSI codes of ethics and their certification powers, the Notaries Act, the Registration Act, the Legal Services Authorities Act, DPDP Act 2023 (lawyers and firms as data fiduciaries),
  court practice directions on use of AI and on citations; abroad ABA Model Rules (competence, confidentiality, supervision of non-lawyer assistance), UK SRA/Law Society guidance, EU AI Act (administration of
  justice is a high-risk use), and the many court sanctions imposed on lawyers who filed unverified AI-generated citations.
- **Already in Hoola** (extend, do not rebuild): **Lawyer's junior** (`legal_junior` with tools `vakil` / `vakil_dekho`: court diary, hearing dates, cause list, limitation *estimate*, drafts for the advocate,
  client update drafts, fee ledger; filing, messages and fee demands on her tap), **Legal researcher** (`legal_research`: Acts and judgments from official sources with the source for every statement; prior-law-to-new-law
  tables; memo goes out only on her yes), **Company secretary** (`cosec_work`: MCA form dates, board/AGM notices and minutes, registers; sending and filing on her tap), **Notary & documentation desk** (`notary_work`: affidavit,
  declaration, POA, indemnity and NOC drafts from the party's facts, stamp duty only from her rate table, register and receipts, apostille steps; final print on her yes), **Compliance officer** (`compliance_work`),
  `hr_admin`, the Enterprise **regtech** desk (due calendar), Pehchaan Locker (masked IDs), the Doc Studio and HOOLA PRINT (court-formatted PDFs), the research engine (R0-R9: cited dossiers, claim checks, figure checks),
  Notebook, pylab, Khata (client dues), PAISA, WhatsApp opt-in, voice in Indian languages, and `appmaker`. Roles with `*` exist in some form. The Mera-PC freeze is untouched.

## The findings that shape every legal & professional desk
### 1. The professional licence is personal: only the advocate, CA, CS, notary or auditor practises; the AI is a supervised assistant, never the practitioner
Ladder as before: **A** admin/prepare, **B** assist (research / draft / check / calculate for a named professional), **C** reserved.
Reserved here: giving legal, tax, audit or valuation opinions to clients as a practitioner; appearing before a court or tribunal; signing, verifying or filing pleadings, returns, certificates, audit reports or
registered documents; attesting or notarising; certifying a company secretarial or CA matter; deciding conflicts of interest; negotiating and binding a client to a deal; settling money; arbitral and judicial decisions;
disciplinary matters; and any statement of fact to a court. **Unauthorised practice of law and unauthorised professional certification are offences in many places.** The AI must never be presented to the public
as a lawyer or CA. **It researches, drafts, organises, calculates, reminds and checks; the professional reviews, signs and takes responsibility.** Hoola's existing employees already carry this wording.

### 2. The biggest AI risk in this industry is the fabricated authority: hallucinated cases, sections and figures
Courts around the world have sanctioned lawyers for citing non-existent cases produced by AI. Therefore **every legal statement carries a source the lawyer can open**
(official gazette, India Code, court website, SCC-type database the firm licenses), a quote check against the text, a date for currency, and an "unverified" label when it cannot verify. Hoola's research engine already
refuses to state a figure or authority that no fetched page or calculation supports; the legal desks reuse that gate. **No citation leaves the system unless the cited text was fetched and the proposition matched.**

### 3. Confidentiality and privilege are the product's foundation
Client files are privileged. Sending a client's facts to an unvetted model or tool can waive privilege and breach duties. Hoola's rules for this industry: per-client (matter) separation, no cross-matter learning, no
training on client data, redaction defaults, secrets masked, access logs, retention policy, data-localisation options, and the Pehchaan Locker for IDs. Conflicts checks and ethical walls are enforced in the data model, not by hope.

### 4. Most of the industry is small: solo advocates, small CA/CS practices, notary desks, staffing agencies and consultants who run on WhatsApp, diaries and Excel
Pain: dates and limitation, client communication, document drafting from templates, fee follow-up, bundle preparation, compliance calendars, notices from departments, TDS/GST due dates, bookkeeping of many small
clients, onboarding KYC, and winning clients without breaching advertising limits. A voice/WhatsApp-native practice copilot with strict human review is the most valuable product, and it fits Hoola's owner-copilot pattern.

### 5. Access to justice is a public good; the AI must be careful in that role
Ordinary people also need help (rent disputes, consumer complaints, wills, labour claims). Plain-language information, forms and next-step guidance with referral to legal aid is valuable; presenting it as individual legal advice,
or discouraging a person from getting a lawyer where one is needed, is harmful. Information-not-advice labelling, jurisdiction and date shown, and a human referral path are mandatory.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [L] advocate/law firm/in-house, [T] tax/audit/accounting practice, [S] company secretary/compliance/corporate services, [N] notary/documentation/registrar services, [C] consultancy/advisory, [H] HR/recruitment/staffing, [B] BPO/KPO/IT services, [V] valuer/surveyor/translator/language services, [R] regulator/bar/institute/legal aid, [P] public/client.

### 1. Litigation & courts practice  [L]
1. * Lawyer's Junior (existing) - court diary, next dates, cause lists, limitation estimates (stated as estimates), client update drafts, fee ledger; **advocate decides and files** - A - advocate
2. Case File Organiser - matter folders, document indexing, chronology of facts, party lists, evidence tags with page references, paginated bundles; per-matter separation - A - advocate / clerk
3. Pleading & Notice Drafter - plaints, written statements, replies, legal notices, applications, affidavits drafted from the advocate's instructions and templates, with blanks for unknown facts, correct court formats, and a sources table; **advocate settles, verifies and signs** - B - advocate
4. Legal Research Memo Writer (extends Legal Researcher) - issue framing, statutes and judgments from official sources, proposition-to-text verification, adverse authority flagged, currency date; **advocate reviews every authority** - B - advocate
5. Citation & Quote Verifier - checks every citation exists, matches court/date/bench, quotes match the text, overruled status; produces a pass/fail table; **mandatory before any filing** - B - advocate
6. Case Chronology & Timeline Builder (events from documents and pleadings, contradictions flagged) - B - advocate
7. Evidence & Exhibit Manager (exhibit lists, marking, admissibility checklists under evidence law, certificate requirements for electronic records; **advocate decides tactics**) - B - advocate
8. Hearing Brief Preparer (one-page briefs, proposed arguments from the advocate's outline, anticipated questions, authorities list) - B - advocate
9. Cross-examination Question Outliner (issue-wise question trees from the record; **advocate conducts**) - B - advocate
10. Limitation & Deadline Calculator (rules library with day counts, exclusions, condonation notes; displays the working; **advocate confirms**) - B - advocate
11. Court Fee & Stamp Duty Calculator (state-wise tables, valuation rules; shows source and date) - A/B - clerk / advocate
12. E-filing & Registry Assistant (checklists per court, defect lists, format conversion, bookmarking; submissions on the advocate's tap through official portals) - A - clerk
13. Order Tracking & Compliance Reminder (orders passed, directions with deadlines, compliance affidavits due, next steps) - A - advocate
14. Client Communication Desk (status updates in plain language and the client's language, document requests, appointment scheduling, consent for recordings; **advocate approves substantive advice**) - B - advocate
15. Fee Estimate & Billing Assistant (matter budgets, time capture, invoices, GST, advance tracking, follow-up reminders (Khata); no fee-sharing violations) - A - advocate
16. Appeal & Revision Screener (limitation, appealable orders, grounds extraction from judgment, record checklist; **advocate decides**) - B - advocate
17. Criminal Defence Assistant (FIR/chargesheet index, bail application drafts from facts, custody and remand date trackers, prison visit scheduling; **advocate decides strategy**) - B - criminal-law advocate
18. Family-law Practice Assistant (maintenance affidavits, asset schedules, custody timelines, mediation prep; sensitivity and child-welfare rules) - B - family-law advocate
19. Consumer & Labour Forum Assistant (complaint drafts, relief calculators, evidence lists, forum jurisdiction pointers) - B - advocate / paralegal
20. Property & Civil Litigation Assistant (title chains, ownership documents, survey records indices, injunction checklists; **opinion by advocate**) - B - advocate
21. Appearance & Briefing Coordinator (junior assignments, court-day plans, travel, clerk tasks, document carrying lists) - A - chambers manager
22. Chambers Manager (conflict screen requests, intake forms, KYC, matter numbers, document retention, staff tasks) - A - chambers head

### 2. Corporate, commercial & contracts  [L/S]
23. Contract Drafting Assistant (agreements from clause libraries and playbooks; fill-in from term sheets; alternative clauses; jurisdiction notes; **lawyer reviews**) - B - lawyer
24. Contract Review & Redline Assistant (risk flags against playbook, missing clauses, ambiguous terms, deviations summary, negotiating positions; **lawyer decides**) - B - lawyer
25. Due-diligence Coordinator (data-room index, request lists, document review tags, issues lists, red-flag report drafts, tracker for closing conditions) - B - deal team
26. M&A / Transaction Closing Assistant (checklists, signature packets, conditions precedent tracker, execution versions, post-closing items) - A - associate
27. Corporate Housekeeping Assistant (board packs, resolutions, registers, share transfers, charge registrations; **CS/director signs**) - A/B - company secretary
28. Startup Legal Pack Builder (founders' agreements, ESOP policy outlines, SAFE/convertible notes templates, IP assignment, privacy policy and terms; **lawyer vets**) - B - startup lawyer
29. Regulatory Mapping Assistant (which licences, registrations and filings apply to a business type and state; references and deadlines) - B - compliance lawyer
30. Employment-law Assistant (offer/termination letters from policy, POSH committee records, standing orders checks, labour code mapping; **HR head/lawyer decides**) - B - employment lawyer
31. Real-estate Transaction Assistant (title search index, agreement drafts, stamp duty, RERA checks; cross-ref real-estate register; **advocate opinion**) - B - property lawyer
32. Insolvency & Restructuring Assistant (claims register, creditor communications, plan comparison, CIRP timelines; **RP/IRP decides**) - B - insolvency professional
33. Competition, FEMA & Securities Compliance Assistant (filings thresholds, deadline calendar, document checklists; **lawyer/CS signs**) - B - regulatory lawyer
34. Data-protection & Privacy Counsel Assistant (DPDP/GDPR gap checklists, privacy notices, consent artefacts, breach notification drafts, data-processing agreements; **counsel signs**) - B - privacy counsel
35. Tech & IT Contract Assistant (SaaS terms, SLAs, source-code escrow, open-source licence compatibility) - B - tech lawyer
36. Legal Operations Analyst (matter spend, turnaround, outside-counsel performance, templates usage, savings; pylab) - A - GC office
37. In-house Legal Helpdesk (staff questions answered from policy library with sources, triage to counsel, NDA generator within rules) - B - in-house counsel
38. Contract Lifecycle Manager (repository, renewals, obligations extraction, alerts, approvals workflow) - A - contracts manager

### 3. Intellectual property  [L]
39. Trademark Search & Filing Assistant (public register searches, similarity reports, class selection, specification drafting, status tracking, opposition deadlines; **attorney files and advises**) - B - trademark attorney
40. Patent Landscape & Prior-art Assistant (search strategies, claim charts, family trees, freedom-to-operate lists; sources shown; **patent agent concludes**) - B - patent agent
41. Patent Drafting Assistant (invention disclosure to draft claims options, figures list, specification skeleton; **patent agent owns claims**) - B - patent agent
42. Copyright & Licensing Assistant (work registers, assignment/licence drafts, collecting-society memberships, royalty clauses; moral-rights notes) - B - IP lawyer
43. IP Portfolio & Renewal Tracker (renewal fees, deadlines, annuities, status changes, docketing) - A - IP paralegal
44. Infringement Evidence Packager (screenshots with hashes, timestamps, test purchases records, cease-and-desist drafts; **counsel sends**) - B - IP lawyer
45. Domain & Brand Protection Monitor (lookalike domains, marketplace listings leads; UDRP/notice drafts; **rights holder/counsel files**) - B - brand protection
46. IP Valuation Support (royalty-rate comparables, cost/income approach worksheets; **valuer signs**) - B - valuer

### 4. Tax, audit, accounting & finance advisory  [T]  (cross-ref BF#101-118)
47. CA Practice Manager (clients, deadlines, document requests by WhatsApp, fee billing, notices tracker) - A - CA
48. Bookkeeping & Accounting Assistant (bank feeds matching, ledger coding, vouchers; Tally XML, GST invoices) - A - accountant
49. GST/TDS/Income-tax Return Preparer (data to returns, reconciliation with 2B/26AS/AIS, mismatch lists; **CA files and signs**) - B - CA
50. Tax Notice Responder (draft replies with legal references and facts from records; deadlines tracking; **CA signs**) - B - CA
51. Tax Planning Scenario Builder (regime comparisons, deductions, advance tax, capital gains lots; ranges and assumptions stated; **CA advises**) - B - CA
52. Statutory Audit Assistant (sampling, confirmations, working-paper index, analytical review, ratio and trend analysis; **auditor forms and signs opinion**) - B - auditor
53. Internal Audit Assistant (risk-based plan, test steps, evidence log, draft observations; **audit head signs**) - B - internal auditor
54. Forensic Accounting Assistant (transaction pattern screens (Benford, duplicates, round-sums), timelines, ledger link analysis; **no accusation; forensic accountant concludes**) - B - forensic accountant
55. Valuation Assistant (DCF/comps worksheets, discount-rate builds from published sources, sensitivity tables; **registered valuer signs**) - B - valuer
56. Transfer-pricing Documentation Assistant (functional analysis, benchmarking sets from licensed databases, report drafts; **TP specialist concludes**) - B - TP specialist
57. Payroll & Compliance Processor (salary calculations, TDS on salary, PF/ESI/PT, Form 16 data, payslips; **payments on owner's tap**) - A - payroll manager
58. GST Registration & Compliance Onboarding Assistant (document checklists, HSN/SAC mapping, filing calendars for small clients) - A - CA staff
59. Financial Due-diligence & QoE Assistant (quality of earnings adjustments, working capital analysis, debt-like items lists) - B - transaction-services team
60. ESG / BRSR Reporting Assistant (data collection templates, emission factors with sources, assurance trail) - B - ESG consultant

### 5. Company secretarial, compliance & corporate services  [S]
61. * Company Secretary Assistant (existing) - MCA form dates, board/AGM notices and minutes, registers, e-form data; **filing on her yes** - A - company secretary
62. * Compliance Officer Assistant (existing) - obligations register by law, owners, due dates, evidence, reminders, audit prep - A - compliance officer
63. Incorporation & Changes Assistant (name search drafts, MoA/AoA templates, DIN/DSC checklists, director KYC, address/capital changes; **professional certifies**) - B - CS
64. Secretarial Audit Assistant (checklists vs Act/SEBI rules, evidence index, draft report; **PCS signs**) - B - practising CS
65. Listed-company Disclosures Assistant (LODR event calendar, board outcome drafts, shareholding pattern data, insider trading window tracker; **compliance officer decides**) - B - compliance officer
66. FEMA / RBI Filings Assistant (FC-GPR/ODI/ECB forms data, AD bank documents, due dates; **authorised dealer/CS files**) - B - CS / CA
67. Licence & Registration Tracker (FSSAI, shop, labour, pollution, import-export, professional licences; renewals) - A - compliance executive
68. Policy Library Manager (POSH, whistleblower, code of conduct, anti-bribery, data policies; version control, training attestations) - A - compliance
69. Compliance Training Assistant (module delivery in local languages, quizzes, completion tracking, refreshers) - A - L&D / compliance
70. Whistleblower & Ethics Case Manager (intake channel, triage, anonymity protections, investigation tracker; **committee decides**) - B - ethics officer
71. Beneficial Ownership & KYC Corporate Services Assistant (UBO registers, KYC refresh, sanctions screening support; **compliance decides**) - B - corporate-services provider
72. Regulatory Change Watcher (new laws, notifications, case law with impact notes by client type; sources) - A - compliance / firm

### 6. Notary, documentation & registration services  [N]
73. * Notary & Documentation Desk (existing) - affidavits, declarations, POA, indemnity, NOC drafts from party facts; stamp from her table; register, receipts, apostille steps; **notary attests** - A - notary
74. Document Writer's Assistant (agreements, rent, sale, gift, will drafts from templates for deed writers/petition writers; blanks for facts; **lawyer/writer owns**) - B - document writer
75. Registration Appointment & Checklist Assistant (sub-registrar slots where available, document lists, witness and ID checks, e-stamp steps; registrar decides) - A - parties / writer
76. KYC for Execution Assistant (ID matching with masked storage, photo/biometric requirements, minors/incapacity flags routed to humans) - B - notary
77. Translation & Certified-copy Coordinator (sworn/certified translation workflows with the translator; legalisation steps) - A - notary / translator
78. Will & Estate Planning Assistant (asset inventory, nomination status, will drafts with testator's instructions, probate/succession checklist; **lawyer reviews; witnesses and registration human**) - B - estate lawyer

### 7. ADR, mediation, arbitration & legal aid  [R/L]
79. Arbitration Case Manager (pleadings tracker, procedural orders, hearing schedules, document exchange, fee schedules; **tribunal decides**) - A - arbitration secretary
80. Arbitrator's Assistant (chronology, issues list, authority summaries with verified citations, award skeleton from the arbitrator's findings; **arbitrator decides and signs**) - B - arbitrator
81. Mediation Facilitator's Assistant (intake forms, issue maps, session notes, settlement term sheet drafts; neutrality; **mediator leads**) - B - mediator
82. Legal Aid Intake Assistant (eligibility screening, issue classification, document checklists, panel lawyer matching and scheduling; **LSA decides**) - A - legal-aid officer
83. Lok Adalat / Pre-litigation Settlement Coordinator (claims data, calculations of compensation (motor accident, bank recovery), notices, scheduling) - A - legal-services authority
84. Paralegal Training Coach (plain-language modules on rights, forms, procedure; para-legal volunteer support in local languages) - A - NGO / legal-aid clinic
85. Court-annexed Mediation Scheduler (parties, mediators, rooms, referral data) - A - court administrator

### 8. Management & advisory consulting  [C]
86. Consulting Research Analyst (market scans, benchmarking, competitor profiles, regulation maps, with cited sources and dates; research engine) - A/B - consultant
87. Proposal & Deck Builder (client briefs to proposals, work plans, fee tables, case studies, HOOLA PRINT/Slides; claims checked) - B - partner / manager
88. Financial Modelling Assistant (three-statement/DCF templates, sensitivity analysis in pylab, assumptions book, error checks; **model owner approves**) - B - modeller
89. Engagement Manager's Assistant (workplans, risks, status reports, client communications, meeting notes, action trackers) - A - engagement manager
90. Interview & Survey Analyst (transcripts coding, themes, quotes, anonymisation, statistics) - B - consultant
91. Process Improvement Assistant (process maps, bottleneck analysis, KPIs, quick-win lists; SOP drafts) - B - process consultant
92. Policy & Regulatory Advisory Assistant (stakeholder maps, impact assessments, consultation response drafts) - B - policy consultant
93. Engineering/Architecture Consultancy Back-office (drawings registers, transmittals, submissions, time sheets; cross-ref construction register) - A - consultancy admin
94. IT & Technology Advisory Assistant (architecture options, vendor comparisons, TCO models, risk registers; cross-ref software architect employee) - B - technology consultant
95. Sustainability / ESG Advisory Assistant (materiality assessment support, data gap analysis, targets benchmarking) - B - ESG consultant
96. Knowledge Management Assistant (case libraries, templates, lessons learned, expert finders, confidentiality filters) - A - KM lead
97. Freelance Consultant's Copilot (leads, proposals, contracts, invoices, GST/TDS, time tracking, client check-ins; Khata) - A - consultant

### 9. HR, recruitment, staffing & payroll services  [H]
98. * HR Admin Assistant (existing `hr_admin`) - leave, attendance, letters, policy FAQs - A - HR manager
99. Recruitment Coordinator (job descriptions, sourcing lists from lawful sources and the client's data, screening questions, interview scheduling, feedback collection; **no auto-rejection on protected traits; recruiter/hiring manager decide**) - A/B - recruiter
100. Resume Screening Assistant (skills-based summaries with reasons; bias audit logs; candidate right to human review) - B - recruiter
101. Staffing Agency Operations Assistant (candidate bench, client orders, deployment, timesheets, billing, compliance docs; contract-labour rules) - A - staffing manager
102. Onboarding & Documentation Assistant (offer letters, KYC, background-check consents, PF/ESI enrolment, induction schedule) - A - HR operations
103. Payroll Compliance Assistant (see 57; for service bureaus: multi-client payroll runs, statutory challans, returns calendars) - A - payroll bureau
104. HR Policy & Employee Relations Assistant (policy Q&A with sources, grievance intake, ER case tracker; investigation reports drafted from the investigator's notes; **HR head decides**) - B - HR business partner
105. Performance & Learning Planner (goal tracking, feedback prompts, development plans, learning paths; no covert surveillance scoring) - A - HR / managers
106. Workforce Planning Analyst (headcount scenarios, attrition analysis, cost models; pylab; fairness checks) - B - HR analytics
107. Immigration & Mobility Assistant (visa document checklists, timelines, relocation plans; **immigration attorney advises**) - B - mobility specialist
108. Campus & Skill-hiring Coordinator (college partnerships, assessments scheduling, offers tracking; skills tests) - A - talent acquisition

### 10. BPO, KPO & IT services  [B]
109. Delivery Manager's Assistant (project plans, SLAs, capacity, risks, status, client escalations) - A - delivery manager
110. Service Desk Agent (tickets triage, knowledge base answers, escalation, customer updates) - A - service-desk lead
111. Quality Monitor for Contact Centres (sampled call scoring on rubric with evidence; coaching notes; employee review rights; no punitive automation) - B - QA lead
112. Back-office Process Automation Assistant (RPA candidate identification, process documentation, exception handling lists) - B - automation lead
113. Data Annotation & Review Coordinator (task allocation, guidelines, quality sampling, inter-annotator agreement stats) - A/B - operations manager
114. KPO Research Analyst (due diligence, market research, financial research tasks with sources and QC) - B - analyst
115. IT Services Estimator (WBS, effort/cost scenarios, risk contingencies, proposal text) - B - presales
116. Software Development Services Assistant (existing Developer Sahayak coding loop, PR/CI discipline; client reporting) - B - engineering manager
117. Security & Data-handling Compliance Assistant for Outsourcers (client-specific controls, access reviews, clean-desk audits, breach drills) - B - security lead
118. Offshore-onshore Coordination Assistant (time zones, handoffs, meeting notes, escalations, cultural briefings) - A - project manager

### 11. Valuers, surveyors, translators & language services  [V]
119. Translator's Workbench (translation memory, glossary control, draft translation for review, QA checks; **translator signs/certifies**) - B - translator
120. Interpreter Scheduling Assistant (languages, availability, legal-court rules, confidentiality briefs) - A - interpreter coordinator
121. Valuer's Report Assistant (property/plant/machinery/business valuation worksheets, comparables tables, photos, standard-based report skeletons; **registered valuer signs**) - B - valuer
122. Surveyor's Assistant (site survey data processing, drawings, quantities, report templates; **licensed surveyor signs**) - B - surveyor
123. Insurance Surveyor / Loss Assessor's Assistant (claim files, photos, loss calculations, policy clause mapping; **surveyor's report signed by licensed surveyor**) - B - insurance surveyor
124. Court-appointed Commissioner / Local Inspection Assistant (inspection checklists, photo log, report skeleton; **commissioner signs**) - B - commissioner
125. Transcription & Legal Stenography Assistant (hearing transcripts with speaker labels, redaction, accuracy marks; certified by the stenographer) - A/B - stenographer

### 12. Regulators, bar councils, institutes & legal education  [R]
126. Bar Council / Institute Registry Assistant (enrolment documents checks, CPD tracking, renewals, complaint intake and routing; **disciplinary committee decides**) - A/B - council secretary
127. Professional Ethics Advisor (rule lookups with sources, scenario Q&A, conflict and confidentiality prompts, advertising-rule checks for firm websites and social posts; **ethics committee interprets**) - B - professional / compliance
128. Legal Education Tutor (law students: case briefing, moot prep, statute reading, exam practice, citation training; Guru Sahayak) - A - student
129. Moot Court & Advocacy Trainer (argument practice with feedback on structure and authority use; mock bench questions) - A - student / junior
130. Legal Clinic Supervisor's Assistant (client intake, student task tracking, supervision logs, outcomes data) - A - clinic supervisor
131. Law Reform & Legal Research Institute Assistant (comparative law tables, consultation analysis, bill drafts' impact notes; sources) - B - researcher
132. Court Technology Adviser (e-filing usability, document standards, translation tools evaluation) - B - judiciary IT

### 13. Public-facing legal information  [P]
133. Citizen Legal Information Guide (plain-language "what are my rights" and process maps for common issues: rent, consumer, labour, family, cyber fraud, RTI; jurisdiction and date shown; legal-aid referral; **information, not advice**) - B - citizen
134. Consumer Complaint Drafter (e-commerce, bank, telecom, insurance; evidence list, correct forum, relief; cross-ref other registers) - A/B - citizen
135. Tenancy & Property Rights Helper (agreements checklist, deposits, notices, registration steps; cross-ref real estate) - A/B - citizen
136. Labour & Employment Rights Helper (wages, notice, PF/ESI, POSH, termination; helplines and forums) - A/B - worker
137. Small-business Legal Starter (registration choices, contracts basics, GST, labour compliance, IP basics; "ask a lawyer" triggers) - A/B - micro-entrepreneur
138. Document Checker for Individuals (reads an agreement or notice and highlights terms, deadlines, risks in plain words; not a legal opinion) - B - citizen

## NEVER an AI Employee (tier C)
Appear in court or before a tribunal; sign, verify or file pleadings, returns, certificates, audit reports, registered documents or attestations as the professional; give legal, tax, audit or valuation opinions to a client or the public as
if licensed; decide conflicts of interest; bind a client to a settlement or contract; handle client money; certify a company-secretarial, CA, notarial or valuer matter; issue judgments, awards or disciplinary decisions;
cite any case, statute, section or figure it has not verified from the source text; reveal or use privileged or confidential client information outside the matter; train on client files; advertise or solicit in breach of professional rules; scrape
paid legal databases against licences; discriminate in hiring or screening on protected traits; present itself as a lawyer or CA.

## Suggested build order
1. **Wave 1 - extend the existing six (tier A, practice copilots for solo advocates, small CA/CS firms, notary desks)**: 1-2, 10-15, 21, 22, 47, 48, 57, 58, 61, 62, 67, 73, 98 + 27, 43, 75, 97.
2. **Wave 2 - verified research and drafting with a named professional**: 3-9, 17-20, 23-26, 28-30, 34, 37, 38, 39, 49-53, 63-66, 74, 99, 101, 102, 104, 119, 127, 133-138.
3. **Wave 3 - regulated, judgement-heavy or sensitive**: 16, 31-33, 35, 40-42, 44, 45, 54-56, 59, 70, 71, 80, 81, 100, 106, 107, 111, 121-126 - need senior review, ethical walls, bias tests, appeal paths.
Fit to Hoola: department **"Legal & Professional Services"** beside Finance & Banking; **Hoola already has five legal/compliance employees (Lawyer's junior, Legal researcher, Company secretary, Notary desk, Compliance officer) and the verified-research engine**, so Wave 1-2 is mostly
completing the suite and enforcing the citation-verification gate everywhere. Reuse the research engine's claim and figure checks as the **Citation & Quote Verifier**, Doc Studio and HOOLA PRINT (court-ready PDFs), Notebook (matter notes), Khata/PAISA (fees), WhatsApp opt-in and voice (client communication in Indian languages),
Pehchaan Locker (KYC), pylab (limitation and compensation calculators, financial models), `appmaker` (client portals), approval cards for every filing, message and fee demand, and strict per-matter separation with an audit trail.
**Best first pilots**: (a) a **solo advocate or small chamber** (1-5, 10, 13-15, 21, 22) in a district court - diary, limitation, drafts with verified citations, client updates, fee follow-up; (b) a **small CA/CS practice** (47-50, 57, 61, 62, 67) -
deadline and notice management by WhatsApp; (c) a **notary/deed-writer desk** (73-75); (d) the **citizen legal information guide** (133-138) as a mass-market trust product with legal-aid referral. Large firms and courts come later: security
reviews, ethical walls and procurement are heavy.

## Open questions for the owner
- Which side first: **advocates/chambers**, **CA/CS practices**, **notary and deed-writer desks**, **in-house legal teams**, **HR/staffing agencies**, **consultancies**, or **citizens** (information only)? I'd start with advocates plus small CA/CS because the employees exist.
- Authority gate: confirm that **no citation, section or judgment is shown as authority unless the text was fetched from an official or licensed source and the proposition matched**, and that unverified items are labelled in red; confirm the firm's own subscribed databases are used only under their licences.
- Confidentiality: confirm per-matter separation, no training on client data, redaction defaults, and data-localisation options before any firm pilot; decide whether Newtika offers on-premise or dedicated-tenant hosting for law firms.
- Public information boundary: confirm the "information, not advice; ask a lawyer/legal-aid" wording, and that Hoola never presents itself as a lawyer or CA.
- Advertising rules: Bar Council limits on advertising and solicitation apply to firms; confirm the marketing employees (if any) stay within them.
- "GO per field" turns any field into a sourced report with the Advocates Act, BCI Rules, ICAI/ICSI codes, the Mediation Act and court AI-use directions checked on primary text.
