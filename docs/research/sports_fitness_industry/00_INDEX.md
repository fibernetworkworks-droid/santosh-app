# The sports & fitness industry across the world - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A SPORTS AND FITNESS INDUSTRY AI EMPLOYEES"*. Eighteenth in the series. Sports and fitness here means: elite and
professional sport (athletes, coaches, clubs, leagues, federations), grassroots, school and college sport, officiating, sports science and
medicine, anti-doping and integrity, venues and events, broadcast and fan engagement, esports, the fitness industry (gyms, studios, personal
training, yoga, group classes, wellness apps, wearables), outdoor and adventure sport, sports retail and equipment, nutrition and supplements,
para-sport, and the governance, safeguarding and law around all of it. Health, nutrition and physiotherapy slices are in the healthcare family
of registers (cross-referenced, not repeated); film and media production are in the film register.

**8 fields, 108 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Rules and bodies named are from
  memory and **must be re-checked on primary text per sport, country and federation** before any desk is built: the World Anti-Doping Code and
  NADA India (prohibited list changes every year; therapeutic-use exemptions), IOC and international federation rules, India's National Sports
  Governance legislation and the Sports Authority of India / Khelo India schemes, player-agent regulations (FIFA and others), safeguarding
  policies for minors, medical rules on concussion and return-to-play, gym/fitness-centre licensing and building-safety norms, consumer
  protection for memberships and auto-renewals, supplement regulation (FSSAI nutraceuticals, contamination risks), data-protection rules for
  biometric and health data (DPDP, GDPR), betting and fantasy-gaming laws (which changed sharply in India in 2025 and differ by state/country).
- **Existing Hoola pieces to build on**: no gym/sports employee exists yet (the `coaching` kinds in roles are for education). Reusable engines:
  Maps (venue routes, grounds, run routes), the `salon` and `tailor` style appointment front desks (class and trainer slots), `appmaker`
  (member, academy and club apps with offline outbox and shift-only location), WhatsApp opt-in campaigns (renewals, class reminders), Khata
  (membership dues, fee instalments), PAISA gateway (memberships, AutoPay plans with customer consent), COUPON/STOCK engines (supplement and kit
  shop), Create Studio, HOOLA FRAMES and Avatar Films (workout videos, highlight reels, coaching clips), HOOLA PRINT (training plans, scouting
  reports), pylab and Data Desk (load, performance and pricing maths), vision review (technique photos as aids), research engine with citations,
  Guru Sahayak (coach education), the dietitian and physio roles from the healthcare register, voice stack (Indian languages), and `website`
  builder (academy and club sites). Roles with `*` exist in some form.

## The findings that shape every sports & fitness desk
### 1. The medical, safety and integrity decisions belong to doctors, referees, anti-doping authorities and coaches; the AI supports them
Ladder as before: **A** admin/prepare, **B** assist (plan / analyse / draft / flag for a named person), **C** reserved.
Reserved here: return-to-play or fitness-to-compete decisions (team doctor), diagnosis and treatment of injuries or conditions (physio/
doctor, cross-ref healthcare), prescribing supplements or medication, selection and contract decisions, officiating decisions in a
live match (humans, with VAR-style tools they control), anti-doping findings and sanctions, safeguarding case decisions, any
automatic penalty or exclusion of an athlete, and every use of an athlete's biometric, medical or location data beyond consent.
**The AI plans, tracks, analyses and reminds; the coach, doctor, referee and federation decide.**

### 2. Most of the industry is small, local and run on WhatsApp
Millions of gyms, yoga studios, academies, clubs, turf bookings, coaches and school teams. Pains: membership churn and renewals,
class and trainer scheduling, fee collection, no-shows, fake attendance, injuries and liability, equipment maintenance, trainer attrition,
tournament logistics, sponsor reports. Hoola's owner-copilot pattern (front desk + records + reminders + collections) fits directly.

### 3. Performance and wellness advice is useful but dangerous when it overreaches
Training load, nutrition, sleep and recovery advice can cause overtraining, eating disorders, relative energy deficiency, dehydration
and injuries, especially in young athletes and in weight-class sports. Supplement and "fat-loss" markets are full of unsafe claims and
contaminated products (anti-doping risk). The AI must stay within **evidence-cited, conservative, range-based guidance**, refer to
qualified professionals for medical issues, refuse extreme diets, steroid/SARMs/peptides advice and anything for minors that pushes weight loss.

### 4. Data on bodies is the most sensitive data in the industry
Heart rate, sleep, GPS tracks, injury history, body composition, menstrual cycle, video of training. Athletes in contract sport face
pressure to share it with employers; amateurs face apps that sell it. Rules: informed consent, purpose limitation, athlete ownership and
right to delete, no use in contract or selection decisions without agreed policy, minors' data under parental consent, no surveillance of
private life.

### 5. Integrity, safeguarding and fair play are non-negotiable
Match-fixing, doping, abuse of athletes (especially minors), harassment, age fraud, and gambling harms are the sports industry's
systemic risks. Detection AI is tier B at most: it raises a flag with evidence for an integrity or safeguarding officer, never accuses.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [A] athlete/player, [T] coach/team/club, [F] federation/league/event/venue, [G] gym/studio/fitness business, [C] consumer/fan, [S] school/grassroots, [X] sports science/medicine/integrity.

### 1. Athlete development & performance  [A]
1. Personal Training Plan Builder - periodised plans from the athlete's sport, level, calendar and constraints (strength, endurance, speed, mobility), with evidence-cited methods and conservative load progression; **coach reviews for competitive athletes** - B - coach / athlete
2. Workout Logger & Progress Coach - sessions, sets, distances, perceived effort, personal bests, trend charts; voice logging; offline - A - athlete
3. Running/Cycling/Swim Coach (pace zones, interval sessions, race-day pacing and fuelling plans from user data; injury-sign stop rules) - B - coach / athlete
4. Technique Feedback Assistant (video/photo review with cues for form in lifts, bowling action, golf swing, swim stroke, yoga asana; confidence and "look-alike faults"; **coach confirms for corrective work**) - B - coach
5. Skill Drills Library (sport-specific drills with progressions, age-appropriate, equipment alternatives) - A - coach / athlete
6. Mental Skills Coach (routines, breathing, focus, goal-setting, pre-competition plans; **no therapy**; refers distress to a qualified professional) - B - sport psychologist
7. Recovery & Sleep Planner (routines, travel recovery, cold/heat use cautions, sleep hygiene; uses wearable data only with consent) - B - sports scientist
8. Nutrition Planner (hydration, fuelling around training/competition, culturally fitting Indian diets, budget meals; **conditions or weight cuts need a registered dietitian**; no extreme restriction, no supplement prescribing) - B - dietitian
9. Young Athlete Development Guide (long-term athlete development stages, growth/maturation cautions, sampling not early specialisation, parent coaching) - B - coach / parent
10. Athlete Career & Education Planner (dual career, scholarships, trials, quotas, exam schedules, post-career pathways) - A - athlete / counsellor
11. Athlete Wellbeing Check-in (mood/fatigue/pain questionnaires, trend flags; **welfare officer/clinician follows up; confidentiality rules**) - B - welfare officer
12. Women & Female-athlete Health Companion (cycle-aware training options chosen by the athlete, RED-S warning signs, pregnancy/postpartum return guides; **clinician for medical issues**) - B - sports physician / athlete
13. Masters & Older-adult Athlete Coach (safe progressions, balance, strength, event choices, health-screen reminders) - B - coach
14. Para-athlete Training Assistant (classification-aware plans, adaptive equipment, accessibility of venues; **classifier and medical staff decide eligibility**) - B - para coach
15. Competition Calendar & Entry Manager (races, tournaments, trial dates, qualification windows, entry forms and fees, travel plans; submissions on athlete's tap) - A - athlete

### 2. Coaching, team management & tactics  [T]
16. Practice Planner (session plans from objectives, time, squad size, equipment; drills diagrams) - A - coach
17. Squad & Roster Manager (availability, attendance, selection pools, roles, communications; **selection decisions by coach**) - A - team manager
18. Match Preparation Analyst (opponent patterns from video/event data the team owns or licensed, set-piece review, scouting sheet; **coach decides tactics**) - B - analyst
19. Video Tagging & Highlights Assistant (auto-tag events, clip lists, player reels, coaching clips via Hoola video engines; labelled automated) - A - analyst
20. Performance Analyst (event data, tracking data, xG-type metrics, trends, benchmarking; pylab; uncertainty shown) - B - analyst
21. Load Monitoring Assistant (training load, session RPE, acute:chronic patterns, travel; flags for staff; **no automatic benching, no medical conclusion**) - B - sports scientist
22. Injury Prevention Screener (movement screens results, risk factors lists, prehab plans; **medical staff clear**) - B - physio
23. Rehab Programme Tracker (physio-prescribed exercises, adherence, pain logs, milestone criteria; **return-to-play by team doctor**) - B - physio
24. Recruitment & Scouting Assistant (candidate lists from data, video clips, trial scheduling, character-reference tracking; bias checks; **recruitment staff decide**) - B - scout
25. Talent ID Pathway Manager (age-group squads, testing days, pathway reviews, late-developer flags; **fair selection rules shown**) - B - academy director
26. Academy Operations Assistant (training schedules, school liaison, accommodation, parental communication, safeguarding checks) - A - academy manager
27. Team Travel & Logistics Coordinator (flights, hotels, visas, kit, equipment cases, anti-doping whereabouts reminders; Maps) - A - team manager
28. Kit & Equipment Manager (inventory, sizing, laundry, repair, order cycles) - A - kit manager
29. Team Communications Assistant (WhatsApp group messages, parent notices, match reports, social posts, multilingual) - A - team manager
30. Coach Education Tutor (coaching badges, session design, safeguarding, first aid, ethics; Guru Sahayak) - A - coach

### 3. Sports medicine, science & wellbeing  [X]
31. Sports Medicine Records Assistant (injury registry, consult notes templates, medical clearance forms, TUE paperwork reminders; confidential; **doctor owns every entry**) - A - team doctor
32. Concussion Protocol Tracker (baseline tests records, symptom logs, graduated return-to-play steps checklist; **clearance only by licensed clinician**) - B - team doctor
33. Physiotherapy Clinic Assistant (bookings, plans, exercise videos, outcome measures, billing; cross-ref healthcare) - A - physio
34. Biomechanics Report Drafter (motion-capture or video measurements into standard reports; **biomechanist interprets**) - B - biomechanist
35. Performance Testing Lab Assistant (VO2/lactate/jump/sprint test protocols, calibration logs, result sheets, normative comparisons) - A/B - sports scientist
36. Sports Nutrition Records & Supplement Auditor (batch-tested products lists, label checks vs prohibited list, contamination risk flags; **dietitian approves**) - B - dietitian / anti-doping officer
37. Athlete Health-data Steward (consent registry, access logs, minimisation, deletion; DPDP/GDPR) - B - DPO
38. Heat, Altitude & Environment Planner (WBGT, hydration, acclimatisation schedules; event cancellation criteria suggestions to organisers) - B - sports scientist
39. First-aid & Emergency Action Plan Builder (venue-specific EAP, AED locations, ambulance routes, drills; **medical lead approves**) - B - medical officer
40. Doping-control Preparation Helper (whereabouts filings reminders, TUE paperwork, rights and procedures guide for athletes; **anti-doping authority decides**) - A - athlete / support staff

### 4. Leagues, federations, clubs & event operations  [F]
41. Federation Secretariat Assistant (membership registers, affiliations, minutes, notices, compliance calendar under national sports governance rules) - A - secretary
42. Competition Scheduler (fixtures with constraints: venues, travel, rest days, broadcast slots, fairness metrics; **league office approves**) - B - competition manager
43. Registration & Eligibility Checker (age, residence, category, transfer windows, documents; **eligibility rulings by committees**) - B - registrar
44. Tournament Director's Assistant (draws/seeding by rule, bracket management, court/field allocation, live score entry, results publishing) - A - tournament director
45. Officials Roster & Appointments Manager (referee/umpire availability, grades, assignments, conflicts, travel, fees) - A - officials manager
46. Match Report & Discipline Case Prep (match reports to case packets, charge sheet drafts from rulebook; **disciplinary panel decides**) - B - disciplinary secretary
47. Grants & Sponsor Funding Manager (Khelo India-type schemes, CSR, sponsorship proposals, reporting) - A - development officer
48. Venue Booking & Turf Management (slots, pricing, maintenance, floodlights, utilities; owner copilot; Khata) - A - venue owner
49. Stadium Operations Planner (staffing, crowd flow, ingress/egress, security rosters, concession stock; **safety officer approves**) - B - venue manager
50. Event Ticketing & Fan Experience Manager (ticket tiers, dynamic pricing within consumer law, accessibility seats, fraud screens, refunds) - A/B - ticketing manager
51. Volunteer Programme Manager (recruit, rota, training, accreditation, thank-yous) - A - event manager
52. Anti-doping Programme Administrator (testing plans from risk assessment, athlete pool registers, sample logistics, results management paperwork; **results management by authority**) - B - anti-doping officer
53. Integrity Monitoring Analyst (betting-market anomalies reported by licensed monitors, suspicious-pattern leads, intelligence log; **integrity unit investigates**) - B - integrity officer
54. Safeguarding Case Manager (reports intake, risk assessments, DBS-style checks tracking, timelines, restricted access; **designated safeguarding lead decides**) - B - safeguarding lead
55. Governance & Elections Assistant (voter lists, nomination checks, ballots, minutes, conflict declarations; **returning officer decides**) - B - governance committee
56. Sports Law Assistant (contract clause libraries, regulation lookups, dispute timelines, CAS-style procedure steps; **lawyer advises**) - B - sports lawyer
57. Agent & Transfer Compliance Assistant (registrations, fee caps, documentation, solidarity-payment calculations; **federation/agents regulate**) - B - compliance
58. Sponsorship Activation Analyst (reach, impressions, content performance, ROI ranges, fair attribution) - A - partnerships manager
59. Broadcast & Rights Operations Assistant (feeds, graphics lists, rights windows, geo-restrictions, highlight clearances) - A - broadcast ops
60. Esports Tournament Operations Assistant (brackets, anti-cheat reports intake, server logistics, player contracts basics, age and region rules) - A/B - tournament organiser
61. Esports Coach Analyst (VOD review, scrim data, draft analysis, role performance; wellbeing and sleep limits) - B - esports coach

### 5. Fitness industry: gyms, studios, trainers  [G]
62. Gym Owner Copilot (memberships, renewals, attendance, plan prices, trainer commissions, equipment maintenance, WhatsApp-based operations, Khata) - A - gym owner
63. Front-desk & Membership Assistant (enquiry handling, tour booking, trial passes, membership options explained fairly, freeze/cancellation per policy) - A - gym front desk
64. Membership Retention Assistant (attendance drop alerts, check-in nudges, goal reminders, win-back offers within policy; no dark patterns) - A/B - gym manager
65. Class & Trainer Scheduler (timetable optimisation, capacity, waitlists, substitutions, room use, instructor skills) - A - studio manager
66. Personal Trainer's Assistant (client records, session plans, progress photos with consent, measurements, reminders, invoices; **trainer owns programming**) - B - personal trainer
67. Group-class Programming Assistant (class formats, music/timing sheets, progressions, regressions, accessibility options) - B - instructor
68. Pre-participation Screening Helper (PAR-Q style forms, flags for medical clearance, contraindication prompts; **no clearance by AI**) - B - trainer / physician
69. Member Safety & Incident Reporter (injury logs, equipment faults, emergency drills, insurance claims data) - A - gym manager
70. Equipment Maintenance Scheduler (machines, cardio, free weights, flooring, AC/ventilation, spares, service history) - A - facility manager
71. Pricing & Promotions Analyst (peak/off-peak pricing, discount depth, lifetime value, auto-renew fairness; pylab; consumer-law check) - B - gym owner
72. Fitness Marketing Assistant (reels, class promos, transformation stories with consent and honest disclaimers, local SEO; claims checker) - B - marketing
73. Franchise & Multi-branch Controller (brand standards audits, KPIs by branch, royalty calculation) - A - franchise manager
74. Wellness Programme Manager for Companies (challenges, participation, privacy-safe aggregate reports, vendor coordination) - A - HR / wellness vendor
75. Yoga & Meditation Studio Assistant (class booking, teacher rosters, retreat logistics, student progress notes; safe-practice cautions) - A - studio owner
76. Martial Arts, Dance & Swimming Academy Assistant (belt/level tracking, grading event planning, parent communication, safety ratios) - A - academy owner
77. Home-fitness Coach (online/video classes, equipment-free plans, small-space workouts, injury-safe cues) - B - subscriber
78. Corporate/Community Run & Walk Club Organiser (routes via Maps, pacing groups, safety, volunteers, charity events) - A - club organiser
79. Senior-fitness & Rehab-adjacent Class Assistant (chair-based, balance classes, falls prevention basics; **medical referral rules**) - B - instructor

### 6. Consumers & fans  [C]
80. Fitness Buddy (daily motivation, habit tracking, steps/workouts, plain-language explanations of exercise myths; evidence cited; no body shaming) - A - user
81. Weight-management Coach (healthy habits, sustainable pace, behaviour tracking; **refuses crash diets, minors' dieting, eating-disorder triggers; clinical weight management by clinicians**) - B - dietitian / doctor
82. Wearable Data Interpreter (sleep, HRV, resting HR, steps trends in plain words; "wellness information, not diagnosis"; arrhythmia or chest-pain red flags prompt medical care) - B - user / clinician
83. Beginner Starter Guide (first-week plans, gym etiquette, equipment orientation, injury-avoid basics, budget kit) - A - user
84. Supplement & Product Fact-checker (ingredient labels, claim checks, banned-substance flags, contamination risk notes, price comparison; no endorsements) - B - dietitian
85. Injury Triage Information Assistant (red flags when to see a doctor, RICE-type info with up-to-date guidance, home-care limits; **not diagnosis**) - B - physio / doctor
86. Outdoor & Adventure Planner (treks, cycling routes, water sports: route, weather, permits, safety kit lists, guide verification, emergency contacts; **operators certified**) - B - adventure guide
87. Fan Companion (fixtures, scores, official highlights, rules explainer, ticket info, travel, accessibility; official sources) - A - fan
88. Fantasy & Betting Harm Guard (education on risks, spending limits tools, self-exclusion pointers, legal-status warnings per state/country; **no tips, no promotion of gambling**) - B - responsible-gaming officer
89. Local Sports Finder (turf, courts, academies, leagues, coaches nearby with verified details; booking via official channels) - A - user
90. Parents' Companion (choosing a sport, safe coaching, injuries, fees, cultivating love of sport, spotting abuse red flags) - A - parent
91. Sports Quiz & Learning Companion (history, rules, science of sport; games) - A - user
92. Disability Sport Navigator (adaptive sports, classification basics, clubs, scholarships, accessible venues) - A - athlete / family

### 7. Schools, colleges & grassroots  [S]
93. School PE & Sports Teacher Assistant (lesson plans, fitness tests, attendance, house competitions, safety checklists; Fit-India-style protocols) - A - PE teacher
94. Inter-school Competition Organiser (entries, age verification, fixtures, transport, results, certificates) - A - sports coordinator
95. College Sports Office Assistant (quota/trial schedules, eligibility records, scholarships, travel permissions, injury forms) - A - sports officer
96. Community Sports Club Secretary (membership, fees, fixtures, coaches, grants, insurance, volunteer rota; Khata) - A - club secretary
97. Talent Camp & Trial Organiser (registration, grouping, assessments, scouting forms, parent communication, safeguarding; **selection by panel**) - A - camp director
98. Village/Rural Sports Programme Coordinator (kits distribution, coaches training, tournaments, social inclusion, women's participation) - A - NGO / panchayat
99. Playground & Facility Safety Auditor (checklists, photos, repair requests, inspection calendar) - A - facility officer
100. Child-protection in Sport Training Assistant (modules for coaches, parents, young athletes; reporting channels) - A - safeguarding trainer

### 8. Sports business, retail, media & technology
101. Sports Retail & Equipment Store Assistant (inventory by size/sport, supplier orders, repairs, rentals, demos, warranty, WhatsApp orders) - A - store owner
102. Equipment Selection Advisor (shoes, rackets, bikes, helmets by use, body measures, budget; fit and safety guidance, no brand pushing) - B - customer / store
103. Product Design & Testing Assistant for Manufacturers (specs, test protocols, standards (e.g. helmets) tracking, field-trial feedback summaries) - B - product engineer
104. Sports Content Producer (match reports, highlights scripts, social clips, explainers, multilingual commentary drafts; labelled AI; rights-cleared footage only) - B - editor
105. Sports Data & Analytics Product Assistant (data cleaning, API docs, model validation, dashboard builds) - A - data team
106. Athlete Brand & Endorsement Manager (media kits, content calendar, endorsement compliance (ASCI), sponsor deliverables, invoicing; **athlete signs**) - A/B - athlete manager
107. Sports Tourism & Events Planner (destination events, packages, permits, accommodation, local partners) - A - tour operator
108. Sports Startup Founder Copilot (problem validation, pilots with clubs, grants, athlete data consent patterns, regulatory map) - A/B - founder

## NEVER an AI Employee (tier C)
Clear an athlete to play or return from injury/concussion; diagnose or treat an injury or illness; prescribe supplements, medication, hormones or
extreme diets; assign weight-cut targets to minors; make selection, contract, transfer or disciplinary decisions; decide a match
official's call in play; find a doping violation, impose a sanction or accuse anyone of match-fixing; open or close a safeguarding case or
contact a child alone; share or sell athlete medical, biometric or location data without informed consent; monitor an athlete's private
life; push gambling, tips or odds; advertise unsafe supplement claims; train on minors' videos without guardian consent; promise results,
weight loss or medals.

## Suggested build order
1. **Wave 1 - owner-copilots for the small business (tier A, extends the front-desk + Khata + WhatsApp pattern)**: 62-65, 69, 70, 48, 96, 93, 94, 101, 2, 15, 80, 83, 89.
2. **Wave 2 - coaching and fitness assist with a named human**: 1, 3, 5, 16-21, 29, 41, 42, 44, 45, 66, 67, 71, 72, 74, 77, 104.
3. **Wave 3 - medical, integrity, safeguarding and data-sensitive**: 4, 8, 11, 12, 21-24, 31, 32, 36, 37, 40, 52-54, 68, 81, 82, 85, 88.
Fit to Hoola: department **"Sports & Fitness"**; start by cloning the proven owner-copilot pattern (front desk, records, reminders, collections) into a **Gym / Academy Sahayak**
and a **Club Secretary**, then add the athlete-facing coaching layer. Reuse `appmaker` (member/academy apps, attendance by QR, offline outbox), PAISA (memberships,
AutoPay with consent), Khata, WhatsApp opt-in, Maps, pylab (load, pricing, nutrition maths), Create Studio and FRAMES (workout and highlight videos), vision review
(technique photos as aids), voice stack (coach in local language), research engine (evidence-cited advice), approval cards for pricing, discounts, selections, refunds and
anything medical, and Hoola's **audit trail + consent registry** for athlete data.
**Best first pilots**: (a) a **neighbourhood gym or yoga studio** (62-65, 70, 66) - cash-linked, WhatsApp-run, high churn, small-ticket but numerous; (b) a **sports academy or
school team** (26, 17, 29, 94, 96) with parents in the loop; (c) a **consumer fitness buddy** (2, 80-83) in Hindi/Marathi. Elite federations and leagues come later: governance, data
and integrity requirements are heavy.

## Open questions for the owner
- Which side first: **gyms/studios**, **academies and clubs**, **individual athletes and fitness consumers**, **schools**, or **federations/leagues**? I'd start with gym/studio and
  academy owners because the copilot pattern already exists.
- Body data: confirm the consent, minimisation and delete-by-default rules for wearables, photos and videos before any athlete-facing employee ships; confirm that minors' data is parent-consented only.
- Medical boundary: confirm that Hoola never gives injury diagnosis, return-to-play clearance, supplement prescriptions or extreme-diet plans, and always refers to a doctor/dietitian.
- Gambling and fantasy: the register keeps Hoola out of betting promotion entirely (harm-guard only); the legal status differs by state/country and changed recently in India - confirm that position.
- Which sport(s) first? Cricket, kabaddi, football, badminton, running, yoga and gym dominate India; each sport adds rule packs, drills libraries and data models.
- "GO per field" turns any field into a sourced report with the WADA Code, federation rules, safeguarding and medical guidelines checked on primary text.
