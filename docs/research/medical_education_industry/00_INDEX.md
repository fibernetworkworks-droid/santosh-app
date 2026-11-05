# The medical education industry, function by function - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A MEDICAL EDUCATION INDUSTRY AI EMPLOYEE LIST"*. Sixth in the series after `healthcare_industry/`
(160 roles), `pharmacy_industry/` (118), `hospital_industry/` (128), `medical_devices_industry/` (118) and
`diagnostics_industry/` (108). This one is the industry that TRAINS the people the others employ: MBBS to super-speciality,
nursing, dental, pharmacy, allied health, AYUSH, CME/CPD, entrance and licensing-exam preparation, simulation, the
medical college as an institution, and the education-technology and publishing businesses around it. Roles already in
earlier registers (HC#147-153, PH#117) are cross-referenced and not counted.

**12 fields, 107 candidate AI Employees.**

## How honest this is
- No new web research for this file. It is **domain knowledge, not a sourced census**. Bodies and rules named are from
  memory and **must be re-checked on primary text** before building: NMC (Competency-Based Medical Education curriculum,
  logbooks, minimum standard requirements, attendance rules, NExT licensing exam plan), NBEMS (DNB), INC (nursing),
  DCI (dental), PCI (pharmacy), NCISM / NCH (AYUSH), NAAC / NIRF (institution rankings), state health-university rules, NEET-UG /
  NEET-PG / FMGE counselling (MCC), UGC rules for deemed universities, and abroad ACGME / USMLE / PLAB / GMC / AMC
  requirements. NExT and several NMC rules have changed repeatedly: check current status.
- Nothing is built. Hoola already has a strong head start: **Guru Sahayak** (personal tutor, hint ladder, mastery,
  SM-2 spaced repetition, exam mode, guardian card), **Shiksha** (classes, learners with consent, question bank,
  gradebook), **Pathyakram** (curriculum & exam designer), **Daftar** (school office), **Shodh** (research assistant),
  **pylab** (locked Python), **Prayogshala** (3D practical labs) - all in `server/app/` (guru, shiksha, pathyakram,
  daftar, shodh, prayog). A medical-education desk would extend them, not start from zero.

## The findings that shape every medical-education desk
### 1. The licence belongs to the teacher, the examiner and the institution - never to the software
Same ladder as before: **A** admin/prepare, **B** assist (draft / flag / tutor for a named human), **C** reserved.
Reserved here: summative marks and pass/fail decisions, entrustment ("this resident may do it unsupervised"),
signing a logbook or a clinical competency assessment, admission/counselling allotment, faculty appointment and
promotion, accreditation declarations, cheating/misconduct verdicts, proctoring decisions against a student,
and medical advice to a real patient disguised as "practice".

### 2. Students are the product's end user, and the biggest honest win is TUTORING and PRACTICE
Medical students and residents drown in volume: anatomy, pharmacology, case reasoning, drug names, exam banks. A tutor
that explains, quizzes, spaces review (SM-2), builds image-based questions, runs a **virtual patient** that the student
interviews, and shows weak areas is lawful, safe and sticky. Rules: cite the textbook/guideline, show the hint ladder,
mark everything "for study, not for patient care", never hand a real patient's plan. Guru's exam mode (hints only)
already exists for supervised settings.

### 3. Competency-based education is a paperwork engine - tier A at scale
CBME demands logbooks, certifiable skills, SDL/AETCOM entries, attendance (75/80% rules), internal-assessment records,
rotation schedules, research/thesis milestones and faculty development hours, all signed by someone. Tracking,
reminders, completeness checks and report assembly are exactly where staff time disappears, with no clinical risk.

### 4. Assessment integrity and bias are the regulated edge
AI for grading, proctoring, admissions or "readiness" scoring is high-risk in the EU AI Act and sensitive everywhere:
bias, appeals, transparency, data protection (DPDP; students may be minors at 17). Any tier-B role that scores a human
needs a documented rubric, a second human on high-stakes cases, and an appeal path.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)

### 1. Pre-admission: entrance coaching & counselling
1. NEET / Entrance Study Planner - syllabus map, weekly plan, spaced repetition, weakness-driven revision (Guru Sahayak) - A - student / parent
2. Entrance MCQ Coach - adaptive practice with worked solutions and error taxonomy; no leaked papers, no fake "predicted" paper claims - A - coaching faculty
3. Mock-test Runner & Rank Estimator (percentile from past public cut-off data, pylab; **estimate labelled as estimate**) - A - coaching faculty
4. Counselling Choice-list Assistant (MCC / state counselling rules, past closing ranks, category & domicile rules; **student decides**) - A - counsellor
5. College Compare Desk (fees, seats, bond/stipend, clinical material, NMC recognition status) - A - counsellor
6. Document Checklist & Form Filler (certificates, domicile, income, reservation, medical fitness) - A - parent / counsellor
7. Scholarship & Education-loan Finder (state schemes, banks, repayment calculators) - A - family
8. Study-abroad Pathway Advisor (FMGE route, MBBS abroad country vs NMC rules, recognition warnings) - B - licensed overseas-education counsellor
9. Parent Support Agent (stress, expectations, FAQs; refers mental distress to a human helpline) - A/B - counsellor

### 2. Undergraduate medical education (MBBS) - tutoring & learning
10. Anatomy Tutor (dissection-room prep, structure quizzes, radiology cross-sections, 3D via Hoola engines) - A - anatomy faculty
11. Physiology & Biochemistry Concept Tutor (pathway walk-throughs, numeric problems in pylab) - A - faculty
12. Pharmacology Mnemonic & Drug-class Coach (class tables, ADR/interaction recall) - A - faculty
13. Pathology & Microbiology Image Quiz Builder (slide / gram-stain / culture sets with explanations) - A - faculty
14. Clinical Reasoning Coach (case vignette -> differentials -> investigations -> management reasoning, Socratic) - B - clinical faculty
15. Virtual Patient Simulator (history-taking roleplay with scripted case bank, finds missed questions; **study only**) - B - clinical faculty
16. OSCE / Viva Rehearsal Partner (station scripts, timer, checklist feedback) - A/B - skill-lab faculty
17. Practical Lab Companion (Prayogshala-style virtual experiments, results to journal) - A - faculty
18. Community-medicine / Biostatistics Helper (sample size, epidemiology exercises, survey design in pylab) - A - PSM faculty
19. Forensic Medicine & Toxicology Case-law Reader (statutes, case summaries with sources) - A - faculty
20. Language Support Tutor (Hinglish / regional explanations of the same concept; English-medium exam terms kept) - A - faculty
21. Peer Study Group Organiser (rooms, spaced topic rotation, doubt-queue to faculty) - A - class coordinator
22. Student Wellbeing Check-in (burnout scales, sleep/habits nudges; **human counsellor hand-off, crisis protocol**) - B - college counsellor

### 3. Postgraduate & super-speciality training (MD/MS/DNB/DM/MCh)
23. NEET-PG / NExT-style Exam Coach (subject maps, error log, timed practice) - A - student
24. Thesis & Dissertation Coach (research question, design, sample size, ethics, statistics shell, reference formatting; student's own data and writing) - B - guide / supervisor
25. Literature Review Assistant (search strategy, screening log, extraction tables, citation check via Shodh) - B - guide
26. Case Presentation & Journal-club Preparer (structured slides outline, critical-appraisal checklists CONSORT / STROBE / PRISMA) - A - resident
27. Procedure Log Keeper (counts, supervision level entered by supervisor, gaps vs required numbers) - A - HOD
28. Rotation & Duty Roster Planner (work-hour limits, postings, leave swaps) - A - PG coordinator
29. Speciality Board Exam Prep (clinical + viva; mirrors NBEMS / international board styles) - A - resident
30. Research-methods Statistician Assistant (pylab analysis templates, assumption checks, plots; **interpretation reviewed by statistician**) - B - biostatistician
31. Manuscript Preparation Assistant (IMRaD scaffolds, guideline checklists, journal-fit lookup; no fabricated data/refs) - B - authors

### 4. Nursing, dental, pharmacy & allied-health education
32. Nursing Student Tutor (fundamentals, care plans, NCLEX-style and INC-syllabus practice) - A - nursing faculty
33. Nursing Clinical-skills Checklist Coach (injection, catheter, wound care step checklists; competency signed by clinical instructor) - A/B - clinical instructor
34. Nursing Care-plan Practice Generator (NANDA/NIC/NOC patterns on case scenarios) - A - faculty
35. Dental Education Assistant (tooth charting practice, radiograph quiz, case-based planning exercises) - A - dental faculty
36. Pharmacy Student Companion (D.Pharm / B.Pharm / Pharm.D: PH#117 plus dispensing role-play) - A - faculty
37. Physiotherapy / OT / MLT / Radiography Skills Tutors (technique checklists, case drills) - A - respective faculty
38. Paramedic & EMT Scenario Trainer (protocol drills, triage practice with synthetic scenes) - A/B - EMS instructor
39. Community Health Worker / ASHA Training Companion (voice-first, local language, job-aid lessons and refreshers) - A - district health trainer

### 5. AYUSH & traditional medicine education
40. Ayurveda Student Tutor (Sanskrit shloka explanation with source, dravyaguna tables, practical clinical correlation) - A - BAMS faculty
41. Unani / Siddha / Homeopathy Study Companions (materia medica recall, repertory exercises; source-cited) - A - respective faculty
42. Yoga & Naturopathy Course Assistant (asana libraries, anatomy cross-links, safe-practice cautions) - A - faculty
43. Integrative Medicine Evidence Reader (RCT summaries with grade and limits) - B - research faculty

### 6. Continuing education (CME / CPD) & faculty development
44. CME Credit Tracker (state / national council credits, certificates, renewal windows; HC#150) - A - doctor / council
45. Personalised CME Recommender (gap-based from the clinician's practice mix and recent guideline changes) - A - doctor
46. Guideline Update Digest (new ICMR / WHO / specialty-society guidelines summarised with source and date) - B - clinician reviews
47. Journal Club Moderator for Practitioners (weekly paper, critical questions, quiz) - A - society
48. Case-based Quiz for Practising Clinicians (anonymised cases, rationale, references) - A/B - CME director
49. Faculty Development Programme Planner (MET, assessment writing, research methods; hours tracked) - A - medical-education unit
50. Educator Teaching-portfolio Builder (evidence, feedback summaries, promotion file shell; **promotion by committee**) - A - faculty

### 7. Assessment: questions, exams & grading
51. MCQ / SAQ / LAQ Item Writer (blueprint-aligned, Bloom level tags, key and distractor rationale; **faculty reviews every item**) - B - subject faculty (extends Pathyakram)
52. Item Analysis & Question-bank Curator (difficulty, discrimination, distractor efficiency, retire / revise list via pylab) - A - assessment cell
53. Exam Blueprint & Paper Assembler (CBME competency map, mark weight, no repeat across sittings) - A - exam controller
54. OSCE Station Designer & Examiner Pack Builder (checklists, global-rating anchors, standardised-patient scripts) - B - OSCE coordinator
55. Rubric-based Draft Grader for Written Answers (marks per rubric criterion with quoted evidence; **second human marks all high-stakes**) - B - examiner decides
56. Practical / Viva Scheduling Coordinator (examiner pairing, conflict-of-interest checks, room logistics) - A - exam cell
57. Internal Assessment Tracker (continuous assessment, eligibility for university exam, attendance thresholds) - A - IQAC / registrar
58. Result Processing & Moderation Assistant (consolidation, grace-mark rule application, tabulation checks; **declaration by controller**) - A - controller of examinations
59. Re-evaluation & Grievance Handler (request intake, anonymised re-mark packet) - A - exam cell
60. Plagiarism & Authorship-integrity Screener (similarity reports, reference-existence checks; **verdict by committee**) - B - research integrity officer
61. Proctoring Flag Reviewer (online exams: flags only, no automatic penalty, appeal path) - B - exam controller

### 8. Clinical training operations: wards, simulation & skills labs
62. Simulation-lab Scheduler & Equipment Manager (mannequins, task trainers, consumables, calibration) - A - simulation director
63. Scenario Designer (debrief scripts, learning objectives, observer checklists for emergency / OB / paediatric / OT scenarios) - B - simulation faculty
64. Debrief Note Assistant (transcript to structured feedback by objective; **facilitator-led**) - B - facilitator
65. Standardised-patient Trainer & Scheduler - A - skills-lab coordinator
66. Clinical Posting Allocator (students x wards x batches, fairness, leave) - A - clinical coordinator
67. Competency Sign-off Tracker (skills required, observed attempts, assessor name, expiry; **sign-off by assessor only**) - A - clinical coordinator
68. Entrustable Professional Activity (EPA) Dashboard (levels recorded by supervisors; progression recommendation to the committee) - B - competency committee
69. Logbook Completeness Checker (missing signatures, wrong formats, inconsistent counts) - A - HOD
70. Patient Safety Learning Packager (de-identified incidents turned into teaching cases) - B - patient-safety + education lead
71. Rural Posting / Internship Coordinator (placements, stipends, housing, travel via Maps) - A - internship coordinator

### 9. Institution management: the medical college as an organisation
72. Admissions Office Assistant (post-counselling document verification, fee collection, hostel allotment) - A - registrar
73. Student Records & Attendance Tracker (biometric / app attendance, shortage notices, condonation files) - A - registrar
74. Fee, Stipend & Scholarship Accountant (instalments, bond recovery, stipend sheets, TDS) - A - accounts
75. Hostel, Mess & Transport Manager - A - warden / administrator
76. Library & Resource Desk (e-resources access, citation help, interlibrary requests, subscription analytics) - A - librarian
77. NMC / University Compliance Calendar (annual disclosure, minimum standard requirements, faculty-student ratios, inspection prep; **declarations by dean**) - A - dean / compliance cell
78. Inspection-readiness Auditor (checklists vs MSR, evidence binder by department, gap list) - B - dean
79. NAAC / NIRF Data Compiler (criteria mapping, evidence indexing, narrative drafts; **submission by IQAC head**) - A/B - IQAC head
80. Faculty Records & Eligibility Checker (qualification, experience-years, publications requirement for designations) - A - registrar
81. Faculty Recruitment & Roster Assistant (advertisements, shortlisting checklist; **panel decides**) - A - HR / registrar
82. Student Grievance & Anti-ragging Cell Assistant (case intake, timeline, mandatory-report prompts; **committee acts**) - B - anti-ragging committee
83. Mental Health & Student Support Cell Assistant (appointment triage to human counsellors, anonymised trend reporting) - B - counsellor
84. Alumni & Placement Desk (internship / residency opportunities, fellowships, alumni mentoring match) - A - alumni cell
85. College Finance & Budget Controller (department budgets, equipment purchases, funding gaps, pylab forecasts) - A - finance officer
86. Research Cell Manager (ethics-committee scheduling, funding calls, ICMR / DST / DBT grant trackers) - A - research cell head
87. Institutional Ethics Committee Secretariat (agenda, protocol packets, minutes, SAE flow; HC#153) - A - member secretary

### 10. Licensing, credentials & international movement
88. Medical Registration Helper (state council registration, NMC portal documents, renewal reminders) - A - doctor
89. Foreign-graduate Licensing Pathway Planner (FMGE / NExT, internship equivalence, document order) - A - student
90. USMLE / PLAB / AMC / MCCQE Prep Coach (step-wise plan, question practice, error log) - A - student
91. Residency Application Assistant (CV, personal statement structure, LOR tracker, programme research, interview practice; **applicant's own words**) - A/B - applicant / mentor
92. Credential Verification Packager (primary-source verification requests ECFMG / state, notarisation checklist) - A - applicant
93. Visa & Relocation Planner for Clinicians - A - applicant
94. CPD Revalidation File Builder (UK GMC appraisal, other jurisdictions: reflective logs, feedback, evidence) - A - doctor

### 11. Publishing, ed-tech & content businesses
95. Medical Textbook Content Editor Assistant (consistency checks, reference verification, figure-credit tracking; **author / editor approve**) - B - editor
96. Question-bank Product Manager (coverage maps, user-error analytics, update cycles) - A - product lead
97. Lecture Video Producer (slides to narrated animated video; Hoola FRAMES; accuracy review gate) - B - faculty reviewer
98. Mnemonic & Visual-Aid Designer (concept diagrams, flashcards, image-occlusion cards) - A - faculty
99. Translation & Localisation Editor (Hindi / regional medical terms, glossary control) - B - bilingual faculty
100. Learner Analytics Analyst (cohort retention, weak-topic heatmaps, churn, pylab) - A - ed-tech lead
101. Accessibility Assistant (captions, alt-text, screen-reader-safe slides, dyslexia-friendly formats) - A - content lead
102. Integrity & Copyright Checker for Course Content (licence trail for images, no scraped paywalled material) - B - legal / editor
103. Community Forum Moderator (answers FAQs, flags unsafe advice or exam-leak posts; **removals by moderator**) - B - community manager

### 12. Public engagement & patient/health education (the lay audience)
104. Patient Education Material Writer (reading-level checked, multi-language, source-cited, clinician-approved; HC#108) - B - clinician approves
105. School Health Education Planner (hygiene, menstrual health, vaccination awareness sessions) - A - school health officer
106. Health-literacy Quiz & Myth-buster (WHO / MoHFW-sourced) - A - public-health educator
107. Community Training for First Aid & CPR (certified instructor curriculum, scheduling, certificate tracking) - A - certified instructor

## NEVER an AI Employee (tier C)
Declare marks, results, pass/fail or ranks; sign a logbook, competency or entrustment decision; allot a seat or
counselling choice; certify attendance condonation; hire, promote or discipline faculty; rule on misconduct,
cheating, ragging or plagiarism; submit accreditation or inspection declarations; give a real patient a plan under
the label "study"; impersonate a supervising doctor; use a student's data for model training without consent.

## Suggested build order
1. **Wave 1 - extend what Hoola already has (tier A, student-facing)**: 1, 2, 10-13, 16-18, 20-21, 23, 32, 44, 88, 90 on Guru Sahayak + Prayogshala + SM-2.
2. **Wave 2 - college paperwork engine (tier A/B)**: 27, 28, 57, 67, 69, 73, 77-80, 85-87.
3. **Wave 3 - assessment and simulated-patient tools (B, human-signed)**: 14, 15, 24, 51, 52, 54, 55, 58, 61, 63, 68.
Fit to Hoola: department **"Medical Education"** beside Healthcare / Pharmacy / Devices / Diagnostics; reuse Guru Sahayak (hint
ladder, mastery, SM-2, exam mode), Shiksha (classes, question bank, gradebook), Pathyakram (blueprints, rubrics), Daftar
(office), Shodh (research), pylab (statistics), Prayogshala (virtual labs), HOOLA FRAMES (lecture videos), approval cards.
Best first pilot: one NEET-PG / NEET-UG coaching institute or a single nursing college - tutoring and practice need no
clinical sign-off, and a coaching business buys on results within a season.

## Open questions for the owner
- Which learner first: **NEET-UG aspirants**, **MBBS students**, **PG/NEET-PG residents**, **nursing students**, or **practising
  doctors (CME)**? Each has a different buyer, a different price, and a different exam calendar.
- Sell to the student (B2C, low ticket, many) or to the institution (B2B, one decision-maker, deployment through the
  college)? The second needs the Wave 2 paperwork employees and sets the data-protection bar higher.
- Which language mix leads (English, Hinglish, Hindi, Marathi...)? Medical exams are English, but understanding often starts
  in the mother tongue; the register assumes bilingual explanation with English exam terms intact.
- Will Hoola use real exam questions/books? Copyright and leaked-paper risk are serious; the register assumes
  faculty-authored or properly licensed content only.
- "GO per field" turns each into a sourced report with NMC / university rules checked on primary text.
