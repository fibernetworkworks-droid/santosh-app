# The education industry across the world - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A EDUCATION INDUSTRY AI EMPLOYEES"*. Fourteenth in the series. Education here means the whole
learning system: early childhood, K-12 schools, higher education, vocational and skills training, test-prep and coaching,
teacher training, special-needs education, adult and lifelong learning, language learning, ed-tech and publishing, education
administration and regulation, and the research and policy around it. The medical-education slice already has its own register
(`medical_education_industry/`, ME#); this one is the rest.

**12 fields, 127 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Bodies, laws and
  rules named are from memory and **must be re-checked on primary text per country and board** before any desk is built:
  India's NEP 2020 and its frameworks (NCF), RTE Act 2009, boards (CBSE / ICSE / state boards / NIOS), UGC, AICTE, NCTE, NAAC / NIRF,
  APAAR / Academic Bank of Credits, UDISE+, DIKSHA / PM e-Vidya, Skill India / NSQF, POCSO and child-safeguarding rules, RPwD Act
  2016 (accessibility), DPDP Act 2023 (verifiable parental consent for children's data); abroad COPPA / FERPA (US), GDPR-K and the EU AI
  Act (education and vocational training uses are classed high-risk: admissions, exam scoring, proctoring, behaviour monitoring),
  Section 504 / IDEA (US special education), UK DfE / Ofsted and KCSIE safeguarding rules, accreditation bodies.
- **Already in Hoola** (extend, do not rebuild): **Guru Sahayak** (personal tutor: hint ladder, code-checked answers, exam mode =
  hints only, mastery path with gates, SM-2 spaced practice, book-grounded cites, guardian card), **Shiksha** (classes, learners with
  guardian consent, shared question bank, gradebook, `frameworks.json`), **Pathyakram** (curriculum and exam designer: papers, plans,
  rubrics), **Daftar** (school office: attendance and guardian alert card, unsigned grading from sheet/OMR/Forms/code/rubric,
  timetable, report card from signed-off marks), **Shodh** (research assistant, official APIs only, refs built in code), **pylab**
  (locked Python), **Prayogshala** (3D practical labs, 198 experiments), Create Studio (Image, Video, Voice, Dubbing, Script writer,
  Brand kit), HOOLA FRAMES and Avatar Films (lesson videos), the Interactive Model Lab plan (teacher face, live voice), the website
  builder (school sites, admissions pages), `appmaker` (school/coaching apps, parent chat BAAT, fees PAISA, notifications), WhatsApp
  opt-in, Khata (fee dues), Maps (transport routes). Roles with `*` exist in some form.

## The findings that shape every education desk
### 1. The licence is held by the teacher, the school, the board and the parent; software never holds it
Ladder as before: **A** admin/prepare, **B** assist (draft / tutor / check for a named human), **C** reserved. Reserved here: final
marks, grades, promotion/detention, admission and seat decisions, disciplinary action, learning-disability or mental-health
diagnosis, child-protection decisions and mandatory reports, scholarship awards, certificate issue, teacher appointment and appraisal
decisions, and every use of a child's data beyond consent. **The AI teaches, prepares, tracks and flags; the teacher, school leader,
counsellor and parent decide.** Guru's existing law holds: exam mode = hints only, answers are code-checked, the guardian is told.

### 2. Children are the end user: safety and consent come first
Most learners are minors. Rules (DPDP, COPPA, GDPR-K, safeguarding law) demand verifiable parental consent, data minimisation, no
behavioural advertising, no profiling for non-educational purposes, no biometrics without need, no photos/voices kept longer than
required, protection from grooming and harmful content, and a human safeguarding lead. AI features that rate or rank children (emotion
recognition, "engagement" scoring, predictive dropout) are the **regulated edge**: avoid emotion recognition, allow only transparent
rule-based flags with a human decision, appeal path and parent view.

### 3. Teachers are overloaded with admin; learners need personal pace
Teacher time goes to marking, lesson plans, differentiation, attendance, reports, parent calls, compliance; learners range 3-5
grade levels apart in one class. The proven AI gains are: **personalised practice with feedback, marking support with human review,
lesson-plan drafting, translation and accessibility, and admin automation**, while the relationship stays human. Evidence of learning
outcomes is mixed; every employee reports mastery, not engagement minutes, and shows its sources.

### 4. Equity and language: India is 22 scheduled languages and huge ability spread
Learning in the mother tongue (NEP), low-bandwidth devices, voice-first for emerging readers, offline packs, inclusion of children
with disabilities and first-generation learners. A tutor that only works in English on a fast phone fails most children. The register
assumes Hinglish and regional languages, voice, low-data modes and caregiver-friendly summaries.

### 5. Integrity and credentials need trust
AI makes cheating easy and detection unreliable; AI-generated work cannot be proven by a detector alone. The fix is assessment design
(orals, process evidence, drafts, supervised exams), clear policies, and humans deciding misconduct. Credentials (marksheets,
degrees, micro-credentials) need verification trails (issuer signatures, digital wallets), not AI-made certificates.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)

### 1. Early childhood & foundational learning (ages 3-8)
1. Story & Rhyme Companion - age-appropriate stories, songs and activities in the home language and English, voice-led, session limits, no ads - A - parent / teacher
2. Foundational Literacy & Numeracy (FLN) Coach - letter/sound/number games with mastery tracking by NIPUN/FLN-style milestones; short sessions - B - teacher
3. Parent Activity Guide - daily play-learning activities from home materials, bilingual - A - parent
4. Anganwadi / Preschool Assistant (attendance, growth and milestone records, nutrition register, parent messages, local-language voice; **health referrals by worker**) - A - preschool teacher
5. School-readiness Observation Helper (checklist from teacher observation, not child scoring or labelling) - B - teacher
6. Reading Aloud Practice Listener (children read aloud; feedback on fluency with gentle prompts; audio deleted by default; parent controls) - B - teacher / parent
7. Early-years Safeguarding Checklist (pick-up authorisation, incident log, ratios; **safeguarding lead acts**) - A - preschool head

### 2. Schools (K-12): teaching & learning  (extends Guru Sahayak, Pathyakram)
8. * Personal Tutor (Guru Sahayak) - hint ladder, mastery path, SM-2 practice, exam mode, multilingual - A - student / teacher
9. Homework Helper (explains steps, never just the answer, checks the student's own attempt, parent summary) - A - student
10. Lesson Planner - lessons from curriculum outcomes (NCERT/boards), time, resources, differentiation, assessment items; **teacher edits** - B - teacher (Pathyakram)
11. Worksheet & Quiz Builder - level-differentiated sets with keys and rubric - A - teacher
12. Differentiation Assistant - same topic at three levels, language scaffolds, extension tasks for advanced learners - B - teacher
13. Concept Visualiser - diagrams, animations, 3D models, virtual experiments (Prayogshala), simulations; lesson videos (HOOLA FRAMES) - A - teacher
14. Science Practical Companion (virtual lab, safety, observation tables, error analysis, viva) - A - science teacher
15. Math Coach (stepwise reasoning, error pattern spotting, visual models, mental-math drills, word problems in local contexts; pylab verification) - A - math teacher
16. Language Teacher's Assistant (reading level texts, vocabulary, grammar exercises, translation between mother tongue and English, speaking practice) - A - language teacher
17. Social Science & History Source Reader (primary-source excerpts with citations, map work, timelines, balanced perspectives on contested topics) - B - teacher
18. Arts, Music & Physical Education Planner (activity sequences, safety, inclusive adaptations) - A - teacher
19. Project-based Learning Coach (project design, milestones, rubrics, mentor questions; student keeps authorship) - B - teacher
20. Open-book & Process-evidence Assessor (collects drafts, reflections, version history to support honest authorship; no AI-detector verdicts) - B - teacher
21. Peer-tutoring & Study Group Organiser - A - class teacher
22. Remedial & Catch-up Programme Manager (diagnostic to personalised plan, small-group scheduling, progress to parents) - B - remedial teacher
23. Gifted & Olympiad Coach (challenge sets, proof writing hints, competition calendars) - A - teacher
24. Career & Stream Guidance Companion (interest, aptitude, course/college/job pathways, entrance exams, scholarships; no deterministic prediction; counsellor involved for decisions) - B - school counsellor
25. Study Skills & Exam Wellbeing Coach (time-tables, notes methods, memory techniques, sleep, stress basics; refers distress to humans) - A/B - counsellor
26. Reading Library Assistant (graded readers, recommendations, book club, e-library access) - A - librarian

### 3. Assessment, marking & credentials  (extends Shiksha/Pathyakram/Daftar)
27. Question-bank Builder & Reviewer (blueprint-aligned items with keys and rationales; difficulty/discrimination stats via pylab) - B - subject teacher
28. Exam Paper Designer (blueprint, marks scheme, no repetition, accessibility versions; Pathyakram) - B - exam coordinator
29. Marking Assistant (rubric-based draft marks with quoted evidence; objective items auto-key; **teacher final**) - B - teacher
30. OMR / Sheet Scanner & Mark Entry Checker (scan, validate, discrepancies) - A - exam cell
31. Feedback Writer (specific next steps per student, in language the parent reads) - B - teacher
32. Moderation Assistant (compare markers, outliers, borderline lists, grace rules) - A - exam controller
33. Report Card Builder (signed-off marks, comments from teacher bank, translated copies) - A - class teacher (Daftar)
34. Credential Wallet Assistant (digital marksheets/certificates, issuer verification links, APAAR/ABC integration where available) - A - school / university
35. Plagiarism & Authorship Review Assistant (similarity reports, reference existence, drafts history; **human committee decides**) - B - integrity officer
36. Proctoring Flag Reviewer (online exam flags only: no automatic penalties, no emotion/gaze inference; appeal path) - B - exam controller
37. Scholarship & Merit-list Calculator (published rules, tie-breakers, reservation categories; **committee approves**) - B - scholarship committee
38. Competency-mapping Assistant (outcomes to NEP/NCF competencies, evidence across subjects) - B - curriculum lead

### 4. School operations & administration  (extends Daftar)
39. * School Office Assistant (Daftar) - attendance, timetable, circulars, guardian alerts, fee reminders - A - principal / admin
40. Admissions Desk (enquiry, forms, documents checklist, interaction scheduling, waitlist by policy; **admission decision by the school**) - A - admission head
41. Student Information Records Keeper (profiles, transfer certificates, UDISE+ data, photos with consent) - A - school clerk
42. Fee & Accounts Assistant (fee structure, concessions by policy, receipts, dues, UPI, Khata) - A - accountant
43. Timetable Optimiser (teacher load, rooms, labs, constraints, substitutions) - A - vice principal
44. Teacher Substitution & Leave Manager - A - vice principal
45. Transport Route Planner (Maps, pick-up points, capacity, safety rules, parent ETA notices) - A - transport in-charge
46. Canteen, Hostel & Boarding Manager (menus with allergy flags, hostel registers, visitor logs, health room log) - A - warden
47. School Safety & Drill Planner (fire, disaster, lockdown drills, POCSO committee records, first-aid inventory) - A - safety officer
48. Staff Records & Compliance (qualification, CPD hours, police verification, contracts, leave) - A - HR
49. Parent Communication Desk (multilingual circulars, polls, PTM scheduling, appointment slots; read receipts) - A - class teacher
50. Complaint & Grievance Desk (parents/students/staff: intake, routing, deadlines, closure) - A - principal
51. Board Affiliation & Inspection Readiness Assistant (checklists, data tables, evidence binders; **declarations by principal/management**) - A/B - principal
52. School Website & Admission Page Builder (Hoola website builder: admissions, fees, results, events, gallery, multilingual) - A - principal
53. School Inventory & Procurement Assistant (labs, library, sports, furniture, e-waste) - A - admin officer
54. Alumni & Donor Relations Manager (consent-based outreach, events, scholarships funding) - A - development office

### 5. Teachers, school leaders & professional development
55. Teacher Workload Reducer (auto-drafts for notes, circulars, reports; time saved dashboard) - A - teacher
56. Classroom Management Coach (strategies, scenario role-play, restorative practices; no surveillance scoring of teachers) - B - mentor
57. Teacher CPD Planner (NEP/NISHTHA-style modules, micro-courses, reflection logs, credit tracker) - A - teacher / principal
58. Lesson Observation Note Assistant (structured notes from the observer's input, strengths-first feedback; no automatic ratings) - B - head of department
59. Subject-Knowledge Refresher Tutor (for primary teachers: content gaps, simple explanations, FLN methods) - A - teacher
60. Teacher Recruitment Screener (qualification checks, demo lesson scheduling; **panel decides; no auto-reject on protected traits**) - A/B - HR panel
61. Principal's Dashboard (attendance, assessment, safety, fees, staff, parents; one weekly pack; alerts not rankings of children) - A - principal
62. Education Officer's Assistant (block/district: school visits, data, reports, grievances; **official decisions reserved**) - B - education officer
63. Teacher Education Mentor (B.Ed./D.El.Ed. students: lesson practice, micro-teaching feedback, child psychology case studies) - A - teacher educator

### 6. Learner support, inclusion & wellbeing
64. Accessibility Assistant (text-to-speech, captions, dyslexia-friendly formats, large print, simplified language, Indian Sign Language resources, alt text) - A - special educator
65. Special-needs IEP Drafting Assistant (goals, accommodations, progress logs from teacher/therapist inputs; **IEP by the team and parent**) - B - special educator
66. Learning-difficulty Screening Prompter (checklists for dyslexia/dyscalculia signs, referral guidance; **no diagnosis**) - B - special educator / psychologist
67. Counsellor's Assistant (appointment scheduling, anonymised trend summaries, resource sheets; crisis protocol to a human, no therapy by AI) - B - school counsellor
68. Child-protection Case File Keeper (secure notes, timelines, mandatory reporting reminders; **reports by the designated person**) - A - safeguarding lead
69. Anti-bullying Reporting Channel (anonymous reports, triage, parent/teacher alerts; **actions human**) - B - school committee
70. Language Support for Migrant & Tribal Learners (mother-tongue bridging, bilingual glossaries, story packs) - A - teacher
71. Out-of-school Child Re-entry Navigator (age-appropriate enrolment, bridge courses, documents, schemes) - A - NGO / education officer
72. Scholarship & Entitlement Navigator for Families (RTE 25%, state schemes, uniforms, midday meals, transport; deadlines) - A - parent / CSC
73. Parent Coach (supporting homework without doing it, reading at home, screen-time rules, exam-stress pointers) - A - parent

### 7. Higher education: universities & colleges (non-medical)
74. Course Advisor (degree maps, prerequisites, credit transfer, timetable clashes; **registrar approves**) - A - student advisor
75. Research Methods Coach (design, sampling, ethics, statistics in pylab, writing structure; student's own data and words) - B - supervisor
76. Literature Review Assistant (Shodh: search strategy, screening log, extraction, citation check) - B - researcher
77. Thesis Supervision Tracker (milestones, meeting notes, deadlines, plagiarism checks) - A - supervisor
78. Lab & Equipment Booking Manager (instruments, safety training validity, usage logs, maintenance) - A - lab manager
79. Faculty Workload & Timetable Planner (teaching, research, admin hours; fairness checks) - A - dean
80. Admissions & Selection Assistant (applications, documents, eligibility rules, merit lists; **committee decides; fairness audit**) - B - admissions committee
81. University Student Services Desk (hostel, fee, exam forms, certificates, grievances; multilingual) - A - registrar
82. Research Grants & Funding Finder (calls, eligibility, budget templates, reporting; **PI decides**) - A - research office
83. Accreditation & Ranking Data Compiler (NAAC/NIRF/ABET criteria mapping, evidence index, draft narratives; **IQAC signs**) - A/B - IQAC head
84. Placement & Internship Desk (company outreach, student profiles, interview prep, offer tracking; no discrimination, consent-based sharing) - A - placement officer
85. Alumni Mentoring Matcher - A - alumni office
86. Academic Integrity Training Assistant (what counts as plagiarism, AI use policies, citation tools) - A - library / faculty
87. MOOC & Blended-learning Producer (course design, video scripts, quizzes, captions; Create Studio) - A - instructional designer
88. Higher-ed Curriculum Mapper (outcomes, industry skill frameworks, gaps) - B - curriculum committee

### 8. Skills, vocational training & employability
89. Skills Pathway Advisor (NSQF levels, qualification packs, local jobs, wages, apprenticeships; ranges not promises) - B - career counsellor
90. Trade Skill Trainer (voice and video lessons for electrician, plumber, welder, tailor, driver, beautician, with safety first; practicals under instructor) - A - trainer
91. Assessment & Certification Tracker (training partner side: batch records, assessments, certificates; **assessor body certifies**) - A - training partner
92. Apprenticeship Matching & Records Desk (employers, stipends, logbooks, attendance, compliance) - A - apprenticeship coordinator
93. Digital Literacy Coach (phone basics, UPI safety, email, forms, online safety; local language, low-bandwidth) - A - trainer
94. Soft-skills & Interview Coach (role-play, resume building, mock interviews with feedback) - A - trainer
95. Entrepreneurship Coach (idea to micro-business: costing, pricing, GST basics, schemes; no financial advice) - A/B - mentor
96. Job-readiness Portfolio Builder (verified skills record, project evidence, referrals) - A - trainee
97. Industry Training Programme Designer (competency maps from SOPs, safety modules, assessments) - B - L&D head

### 9. Test prep, coaching & tutoring businesses
98. Coaching Institute Operations Assistant (batches, timetable, attendance, fees, mock tests, parent reports, doubt desks) - A - coaching owner
99. Mock Test Generator & Analyser (blueprint, error taxonomy, topic heatmaps, rank estimators with ranges; no leaked papers) - A - faculty
100. Doubt-solving Desk (queue by topic, AI first answer with steps, escalation to faculty, answer quality tracking) - B - faculty
101. Personal Study Planner (syllabus coverage, revision cycles, SM-2, mock schedule, burnout checks) - A - student
102. Private Tutor's Assistant (lesson notes, parent updates, scheduling, payments, progress reports) - A - tutor
103. Competitive Exam Navigator (UPSC/SSC/banks/engineering/NEET: syllabus maps, notification trackers, form helpers, deadlines) - A - aspirant
104. Language Test Coach (IELTS/TOEFL/PTE style: speaking and writing feedback with rubric caveats) - B - teacher
105. Study Abroad Admissions Assistant (country/course shortlisting, document checklists, SOP structure from the student's own story, visa steps; **no consultant-fee tricks**) - B - counsellor

### 10. Language, culture & lifelong learning
106. Language Conversation Partner (speaking practice with gentle correction, role-plays, pronunciation, culture notes; voice) - A - learner
107. Spoken English for Work Coach (workplace scenarios, voice feedback, vocabulary drills) - A - learner
108. Adult Literacy Facilitator (voice-first letters, numbers, forms, money, health words; dignity-preserving) - A - literacy volunteer
109. Hobby & Skill Learning Companion (music, art, cooking, coding basics; practice plans) - A - learner
110. Senior Learner Companion (slow pace, large text, memory-friendly, digital basics) - A - learner
111. Library & Reading Promotion Assistant (community libraries, reading challenges, local-language books) - A - librarian
112. Civic & Financial Literacy Educator (elections, rights, banking, scams, insurance basics; non-partisan) - A - educator

### 11. Ed-tech, content & publishing
113. Curriculum Content Developer (units, explainers, practice items, rubrics aligned to standards; **subject expert reviews**) - B - subject expert
114. Textbook & Course Editor Assistant (consistency, reading level, bias and inclusion checks, reference verification, image credits) - B - editor
115. Translation & Localisation Editor (glossaries, regional terms, culturally-fit examples) - B - bilingual expert
116. Learning-video Producer (script, narration, animations, captions; Create Studio + FRAMES; accuracy review gate) - B - subject expert
117. Learning Analytics Analyst (mastery, retention, drop-off, equity gaps; privacy-preserving, aggregated; pylab) - A - product lead
118. Adaptive-learning Engine Tuner (item calibration, sequencing rules, safe exploration; transparent rules, human override) - B - learning scientist
119. EdTech Product Compliance Reviewer (child privacy, ads, data retention, accessibility, claims; COPPA/DPDP/GDPR-K) - B - DPO / legal
120. Efficacy Evidence Builder (study design, control groups, outcomes, effect sizes; honest limits) - B - researcher
121. School/College Sales & Onboarding Assistant (demo, pilot plan, teacher training, rollout metrics) - A - ed-tech sales

### 12. Government, policy, funders & community
122. Education Data Steward (UDISE+, enrolment, dropout, learning outcome datasets; quality, de-identification) - A - education department
123. Learning-outcome Survey Assistant (sampling, test items, enumerator guides, analysis in pylab) - B - assessment agency
124. Policy Analyst (budgets, schemes, evaluations, international comparisons with sources) - B - think-tank / department
125. Grant & CSR Education Programme Manager (partners, milestones, impact reports, financial utilisation) - A - foundation
126. Community Learning Centre Coordinator (volunteers, schedules, materials, attendance, parent meetings) - A - NGO
127. Disaster-time Learning Continuity Planner (radio/WhatsApp/offline packs, mobile classes, safe return) - A/B - department

## NEVER an AI Employee (tier C)
Assign final marks, grades, rank, promotion or detention; decide admission, scholarship or placement; discipline or expel a
student or terminate staff; diagnose a learning disability, mental illness or neurodevelopmental condition; make or handle a child
protection decision or mandatory report; record or analyse children's faces, voices or emotions beyond consented educational use
(and never emotion recognition); profile or advertise to children; issue a certificate or degree; accuse a student of cheating
based only on a detector; replace a teacher in a classroom; share student data with third parties without lawful consent;
scrape paywalled content or copyrighted textbooks into training.

## Suggested build order
1. **Wave 1 - extend what exists (tier A, teachers feel it in a week)**: 8, 9, 11, 15, 16, 33, 39, 41, 42, 43, 45, 49, 50, 52, 55, 61, 98, 101.
2. **Wave 2 - assist with a named human**: 2, 10, 12, 22, 24, 27-29, 31, 40, 57, 64, 65, 74-76, 80, 100.
3. **Wave 3 - regulated or child-sensitive**: 6, 20, 35, 36, 37, 60, 66-69, 118-120 - need a safeguarding lead, a DPO, parental consent flows and an appeal path.
Fit to Hoola: department **"Education"** (Shiksha, Guru, Pathyakram, Daftar, Shodh already live); most of Waves 1-2 are *wiring and extension* of existing
tools into complete employees (Teacher, Principal, Coaching Owner, Parent, Student). Reuse Prayogshala (14), Create Studio/FRAMES (13, 116), Maps
(45), `appmaker` + BAAT + PAISA (school and coaching apps), WhatsApp opt-in (49), Khata (42), pylab (15, 27, 99), research engine (76, 124),
vision review (marking scanned answers with teacher confirmation), the interactive-teacher-face plan (live explainers), approval cards for every
mark, admission, certificate and report to a parent, guardian card (existing), and a **child-data policy** (consent, retention, no profiling).
**Best first pilots**: (a) a **small private school or coaching institute** (98, 39-42, 49, 11, 99, 8) - the owner decides, fees are
cash-linked, parents WhatsApp daily; and (b) a **parent-and-child tutor product** (8, 9, 101, 73) in Hindi/Marathi with guardian card.
Municipal or government schools come later: procurement is slow and data rules stricter.

## Open questions for the owner
- Which side first: **schools** (admin + teaching), **coaching/test prep**, **parents and students** (B2C), **skills/vocational**, or **higher
  education**? I'd start with a small private school or coaching institute because Shiksha/Daftar/Guru already exist.
- Which curriculum and languages first (CBSE/state board, Hindi/Marathi/English)? Curriculum packs are data with maintained sources.
- Child-data policy: confirm verifiable parental consent, no emotion recognition, no ads or profiling, default deletion of voice/photo
  data, and a named safeguarding lead for each deployment before any child-facing employee scales.
- Marking and integrity: confirm that AI suggests and humans mark, and that no AI-detector verdict is ever used as proof.
- "GO per field" turns any field into a sourced report with NEP, board rules and child-data laws checked on primary text.
