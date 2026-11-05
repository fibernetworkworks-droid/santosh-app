# The building & construction industry - AI Employees register

Owner's ask (4 Nov 2026): *"PERFECT NOW A AI EMPLOYEE IN BUILDING AND CONSTRUCTION INDUSTRY"*. Eighth in the series after the
healthcare family (healthcare, pharmacy, hospital, medical devices, diagnostics, medical education, health insurance).
Unlike those, **the research already exists**: `docs/research/building_industry/` has 276 jobs from six sourced reports
(design, site, trades, cost/contract, approvals/developer/FM, digital/survey/sustainability). This file does not redo
it - it turns those 276 jobs into **AI Employees**, merging jobs that one employee would naturally do, dropping the
physical-only ones, and tagging each with the tier and the human gate. Report references: R1 design, R2 site, R3 trades,
R4 cost/contract, R5 approvals/developer/FM, R6 digital/survey/sustainability (section letters as in the reports).

**15 fields, 123 candidate AI Employees.**

## How honest this is
- The job list is sourced (see the six reports and their own "NOT FOUND" lists). The *AI Employee* grouping and the tier
  tags are my judgement, not sourced. No new web research this turn. Legal references come from the reports and must be
  re-checked on primary text per state: building permission, fire, lifts, structural audit and society law are **state
  subjects** (Maharashtra / MahaRERA and the MoHUA Model Building Bye-Laws 2016 are the worked example).
- **Already in Hoola** (do not rebuild; extend): `architect_assistant` (office, drawing register, approvals, FSI estimate),
  `interior_designer`, `site_supervisor`, `site_manager` (Theka sahayak), `property_manager`, `society_manager`; planned in
  `docs/DESIGN_DESK_PLAN.md` (design & consultancy + engineering disciplines with no role yet). Engine pieces: CAD
  (`app/engineering/`: CadQuery, FEA, DFM, drawings, DXF, STEP), `site/` website builder, Maps, Khata, doc studio + HOOLA PRINT,
  pylab, Data Desk, `appmaker` (apps for contractors), WhatsApp opt-in, vision review of drawings/photos.
- Roles marked `*` exist in some form today; `+` = planned in DESIGN_DESK_PLAN.

## The findings that shape every construction desk (from the reports, restated)
### 1. PREPARE / SUBMIT / CERTIFY (R5)
The application is the owner's act, the technical certification is reserved to a named licensee on a specific register,
and preparation is unreserved. Software's room is the *prepare* column: **70-80% of the labour, almost none of the
liability.** *"An agent that drafts those certificates and lets the licensee sign is useful and lawful; an agent that
signs or files them is forgery."* Tiers: **A** admin/prepare, **B** assist (check / draft / calculate for a named
licensee), **C** reserved (certify, sign, submit, approve a design, accept work, release payment, issue a notice).

### 2. Design is largely UNGATED in India; certificates and execution are gated (R1)
HVAC design needs no licence; electrical and plumbing design ungated; fire is the hardest gate (only a Licensed Agency
may issue Form A/B); structural stability certificates need an engineer on that corporation's own register; the
Architects Act protects the title not the practice (CoA v. Mukesh Goyal, SC 2020). Plus the "-on-Record" appointments
(Construction Engineer, Geotechnical, Town Planner, Quality Auditor in zones IV-V, Empanelled Architect as approving
authority). So design-side employees can go further than in most professions; certificate-side ones cannot.

### 3. What is machine-readable decides coordination (R6)
Open and checkable: IFC (ISO 16739-1), IDS, bSDD, BCF, COBie, gbXML/IDF, LandXML, E57/LAS, GeoJSON, GeoPackage. Closed:
`.rvt .pln .dgn .dwg .nwd`. *"Without an IDS, 'we exchanged IFC' guarantees nothing checkable"* and *"every Indian
regulatory submission is a DWG or a PDF."* A point cloud carries no semantics. Employees must say which of these they
actually read, never claim model-level checking from a PDF.

### 4. Where the money is: measurement, billing, claims, approvals, and who pays whom (R4, R5)
Construction runs on measurement (IS 1200), abstracts/BOQ, running-account bills, retention, price variation, GST on works
contract, labour cess, TDS, RERA escrow, delay and claim notices. Much is arithmetic (determined) or record-keeping;
legal outcomes (LDs, delay analysis) are **not** computable by code - only the working papers are. This is Hoola's sweet
spot: structured records, checks in code, nothing invented, a person signs.

### 5. Sites are physical; the AI Employee works the records around the site (R2, R3)
The mason, bar bender, scaffolder, rigger and crane operator are people. What the AI does is the muster, measurement,
work-order, wage basis, safety paperwork, material reconciliation and photo evidence around them (R3 section 8: records and
measurement software can own end to end; the physical work, never).

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)

### 1. Land, feasibility & development  (R5 B1-B4, A5-A6)
1. Land Scout & Feasibility Analyst - candidate plots, zoning, FSI/TDR, setbacks, comparables, rough development appraisal (IRR/payback in pylab) - A - developer
2. Title Due-Diligence Assistant - 7/12 or equivalent, mutation, encumbrance, litigation, index-II; red-flag list for the advocate; **legal opinion reserved** - B - title advocate
3. Land Records Fetcher & Reconciler (state portals' public data, survey numbers, area reconciliation) - A - revenue consultant
4. Development Manager (DM) Assistant - milestones, consultants' deliverables, approvals chase, budget vs actuals - A - DM / developer
5. Project Finance Desk - drawdown schedule, interest during construction, escrow flows, lender MIS pack - A - CFO
6. JV / Land-owner Agreement Tracker (area-sharing, revenue-sharing, timelines, obligations) - A - legal head

### 2. Architecture, design & consultancy  (R1)
7. * Architect's Office Assistant - drawing register, transmittals, submissions list, revision control, meeting minutes, FSI estimate - A - principal architect
8. + Concept & Space-Programme Assistant - brief to area statement, adjacency matrix, massing options from rules - B - architect
9. + Building-bye-law Checker - setbacks, height, FAR, parking, ventilation, stair widths against the rule set of the chosen authority; shows clause per check; **compliance statement reserved** - B - licensed architect
10. + Structural Pre-design Assistant - load take-down, member sizing by IS code tables, preliminary quantities; **design and stability certificate reserved to the registered engineer** - B - structural engineer
11. + MEP Design Assistant - load estimates (electrical, HVAC, plumbing, fire), pipe/duct sizing tables, equipment schedules; ungated design but **energisation / execution gates stay** - B - MEP consultant
12. + Fire-safety Design Checker - travel distances, refuge, hydrant/sprinkler demand, NBC part 4 rule hits; **Form A/B by the Licensed Agency only** - B - fire consultant
13. * Interior Designer Assistant - moodboard, layouts, material schedules, BOQ, vendor quotes, client approvals - A - interior designer
14. + Landscape & Urban-design Assistant - planting schedules, hardscape quantities, water demand, SUDS checks - B - landscape architect
15. + Acoustics / Façade / Lighting Specialist Assistants - daylight and glare tables, façade U-values, lux plans - B - specialist
16. + Drawing QA Reviewer - dimension, level, scale, layer, title-block, cross-reference, North-point checks; sheet-set completeness (vision on PDFs, geometry on DWG/IFC where open) - B - project architect
17. Design Coordination Manager - consultant deliverable tracker, RFI log, design-change register and impact on cost/time - A - design manager

### 3. Digital delivery: BIM, survey, reality capture  (R6 A-B)
18. BIM Manager / Information Manager Assistant - EIR/BEP drafting, ISO 19650 naming, LOD/LOI matrices, model health reports - A/B - BIM manager
19. CDE & Document Controller - folders, status codes, transmittal, revisions, superseded copies, audit trail - A - document controller
20. Clash Detection Coordinator - runs open-format (IFC/BCF) clash checks, groups issues, assigns to trades, tracks closure - B - BIM coordinator
21. 4D/5D Planner - model-linked schedule and cost, quantity take-off from IFC with formula trail - B - planner / QS
22. Land Survey Data Processor (total-station / GNSS / LandXML, contours, boundary vs record) - B - licensed surveyor signs
23. Drone Survey & Photogrammetry Processor (orthomosaic, DSM, volumes, progress comparison) - B - survey lead
24. Laser Scan / Point-cloud Reality Capture Assistant (registration QA, deviation maps, as-built vs design) - B - scan technician
25. As-built Documentation Assistant - redlines to as-built set, completeness before handover - A - site architect / QS
26. RERA Carpet-area Measurement Assistant - area statements from plans, tolerance checks, discrepancy report; **certification reserved** - B - project architect / CE
27. GIS Analyst - plot overlays, flood/seismic/zoning layers, catchment and access maps - A - planner

### 4. Approvals, permits & statutory compliance  (R5 A1-A14)
28. Approvals Tracker (Liaison Officer Assistant) - per-authority checklist, status, queries, fees, validity dates; state-specific permission map - A - liaison manager
29. Building-permission File Assembler - forms, drawings, ownership, NOCs, undertakings packaged as DWG/PDF sets; **submission by owner / licensee** - A/B - licensed professional
30. Fire NOC Packet Preparer - system schedules, design summary, previous NOC history; **issued only by the authority / Licensed Agency** - B - fire consultant
31. Environmental Clearance & Consent Tracker (EIA triggers, CRZ, tree permission, CTE/CTO from pollution boards) - A/B - EC consultant
32. Utility Liaison Assistant - electricity load sanction, water, sewer, drainage, gas; documents, deposits, site readiness - A - liaison
33. Heritage / AAI / CRZ Clearance Screener (is the plot affected? which NOC?) - B - specialist
34. Statutory Calendar (licences, renewals, inspections, lifts, DG, boiler, labour licence, BOCW registration) - A - compliance officer
35. RERA Compliance Manager - project registration, quarterly updates, 70% escrow tracking, Form 3/4/5 data, project-status page; **declarations by promoter / CA / architect / engineer** - A/B - promoter + CA
36. Occupancy / Completion Certificate Packet Builder - plans as built, test certificates, NOCs, fire/lift/structural compliances - A/B - licensed architect

### 5. Estimating, quantity surveying & cost  (R4 A-B)
37. Quantity Take-off Assistant - IS 1200 measurement from drawings/IFC with formula trail; measurement-sheet output; **determined arithmetic, partially determined classification** - B - QS
38. Rate Analyst - rate build-up (material + labour + plant + overhead + profit) from SOR, market quotes, productivity coefficients - B - estimator
39. BOQ Builder & Abstract Pricer - items, descriptions, units, rates, escalation, abstract of cost - A/B - estimator
40. Cost Planner & Value Engineer - option cost comparison, elemental cost plans, VE ideas with quantified impacts - B - cost manager
41. Cost Controller - budget vs committed vs actual vs forecast; EAC, variance reasons - A - cost manager
42. Cash-flow & Budget Manager - S-curves, drawdown, retention, payment timing, funding gaps (pylab) - A - project finance
43. Earned-value Analyst - PV/EV/AC, CPI/SPI, forecasts (arithmetic fully determined; progress % is a judgement) - A/B - planner / PM

### 6. Contracts, commercial & disputes  (R4 C)
44. Contracts Administrator - contract register, obligations, notice periods, insurance and bond validity, correspondence log - A - contracts manager
45. Variation & Change-order Assistant - instruction to cost/time impact paper, approval trail - A/B - commercial manager
46. Claims Assistant - entitlement matrix, notice-compliance check, quantified claim working paper; **notice and claim submission reserved** - B - claims consultant
47. Delay Analyst's Working-paper Builder - baseline vs updates, as-planned vs as-built, windows; **the conclusion is not computable** - B - forensic planner
48. Liquidated-damages Calculator (arithmetic only; legal entitlement reserved) - B - contracts manager + legal
49. Retention, Price-variation & Escalation Calculator (formulae from the contract and published indices) - A - QS
50. Dispute / Arbitration Bundle Assistant - indexed bundles, chronology, exhibits, witness-statement skeletons - A/B - counsel
51. Insurance & Bonds Coordinator (CAR, WC, PI, performance/retention guarantees, expiry alerts) - A - contracts / finance

### 7. Tendering & procurement  (R4 D-E)
52. Tender Manager's Assistant - tender notices watch, pre-qualification checklist, bid/no-bid sheet, document calendar - A - tender manager
53. Tender Document Writer - technical and commercial volumes from templates and past bids; compliance matrix - B - bid manager
54. Bid Pricer - BOQ pricing, sub-contractor quotes, risk and opportunity register, margin sensitivity (pylab) - B - bid manager
55. Pre-qualification Dossier Builder (turnover, similar works, certificates, solvency) - A - bid manager
56. Procurement Manager's Assistant - requisition to PO cycle, vendor comparison statements, negotiation points - A - procurement manager
57. Purchase Engineer - technical specs sheets, bid equalisation, delivery schedules - B - purchase engineer
58. Vendor Developer - vendor registry, GST/MSME/KYC checks, past performance score, blacklisting log - A - procurement head
59. Expediter & Logistics Coordinator - supplier chase, dispatch tracking, transport permits, site delivery slots (Maps) - A - procurement
60. Import/Customs Coordinator (materials and plant: HS code, duty, bill of entry documents) - A - EXIM
61. Material Planner & Store Manager - consumption norms, min-max, GRN, issue, reconciliation, wastage analysis, cement/steel stock - A - store in-charge
62. Subcontract & Work-order Manager - scope, rates, measurement basis, advances, running bills (theka sahayak extension) - A - contracts / site

### 8. Planning & project controls  (R2 section 2)
63. Project Planner / Scheduler - WBS, CPM network, resource-loaded schedule, look-ahead (2-3 week), critical path (loops refused) - A/B - planner
64. Progress Measurement Assistant - daily progress reports from photos/forms, physical % by activity, variance to plan - A - site engineer
65. Resource & Productivity Analyst - manpower histograms, output per gang, benchmark vs norms (pylab) - A - project manager
66. Risk & Issues Register Keeper - risks, owners, mitigation, status, escalation - A - PM
67. Meeting Secretary (OAC / site / coordination) - minutes, action items, due dates, chasing - A - PM
68. Project Director's Dashboard - cost, time, quality, safety, cash, approvals in one view; weekly pack - A - project director
69. Construction Management / PMC Assistant (third-party client side: reviews, certificates drafted for the PMC's sign-off) - B - PMC lead

### 9. Site execution, quality & measurement  (R2 sections 3, 4, 6)
70. * Site Supervisor Assistant - daily log, attendance, instructions, photos, snag notes, stage checks - A - site engineer
71. * Site Manager (Theka Sahayak) - gang-wise work orders, measurement, wage calc by rate basis, advances, payouts per tap - A - contractor
72. Pour & Concrete Records Keeper - cube register, slump, mix design, pour cards, 7/28-day results vs grade acceptance (IS 456 criteria); **acceptance by QA engineer** - B - QA engineer
73. Rebar Bar-bending Schedule Assistant - BBS from drawings, cutting plans, wastage - B - structural/site engineer
74. Formwork & Scaffold Planner - striking times, load checks per supplier tables, inspection tags - B - site engineer
75. Quality Auditor's Assistant - inspection and test plans (ITP), checklists per activity, NCR log, hold-point tracking - A/B - QA/QC manager
76. Material Test Register Keeper (NABL lab results, cement/steel/aggregate lots, expiry, retest) - A - QC engineer
77. Setting-out & Level Check Recorder (survey points, tolerances, as-built vs design) - A/B - survey engineer
78. Snagging & Punch-list Manager - photos, rooms, defects by trade, close-out verification (R5 C6) - A - QA engineer
79. Specialist Works Coordinators: waterproofing, façade, MEP installation, lifts, fire systems - installation sequence, test records, warranty terms - B - respective specialists
80. Concrete-Pump, Crane & Plant Scheduler (hire, hours, fuel, maintenance, operator licence) - A - plant manager

### 10. Safety, health, environment & labour  (R2 section 5, 7; R4 F4)
81. EHS Officer's Assistant - toolbox talks, permits-to-work (height, hot work, confined space, excavation), PPE register, inspection checklists, incident log - A/B - safety officer
82. Incident Investigation Assistant - timeline, witness question lists, root-cause tools, corrective actions; **findings by the safety officer** - B - safety head
83. Safety Training & Competency Tracker (induction, working at height, scaffolder card, operator licence) - A - EHS
84. Environmental Monitoring Assistant (dust, noise, water, waste manifests, C&D waste, tree/dewatering consents) - A - EHS
85. Labour Compliance Desk (contract labour licence, BOCW registration, ESI/PF, minimum wages, muster rolls, labour cess) - A - compliance officer
86. Labour Camp & Welfare Manager (accommodation, canteens, creche norms, health camps) - A - labour welfare officer
87. Wage & Payment Auditor (daily/weekly wages, piece-rate bases, advances, deductions, digital payments; **pay on the owner's tap**) - A - accounts

### 11. Finance, tax & accounts for builders  (R4 F)
88. Running-account (RA) Bill Processor - measurement to bill to deductions (retention, TDS, GST, labour cess) to payable; certification of the bill is the engineer's - A/B - billing engineer (R4 A3)
89. GST on Works Contract Assistant - classification, rate, input credit, e-invoicing/e-way flows, reverse charge flags; **classification judgement flagged** - B - tax consultant
90. BOCW Cess & TDS Calculator (percentage determined; base per rules) - A - accounts
91. Builder's Accounting & Reconciliation (project-wise books, inter-project transfers, vendor ageing) - A - accountant
92. Customer Payment & Demand-letter Manager (milestone-linked demands, interest, receipts, loan disbursement coordination) - A - CRM head
93. Escrow / RERA Account Reconciler (70% rule, withdrawals vs certified progress; **withdrawal certificates by CA/architect/engineer**) - B - CA

### 12. Sales, marketing & customer journey  (R5 B5-B9)
94. Project CRM & Sales Assistant (opt-in lead follow-ups, site-visit scheduling, unit holds, price sheets) - A - sales head
95. Project Marketing Assistant (RERA-compliant advertisements with registration number, brochures, walkthrough videos via HyperFrames/VR assets) - B - marketing + legal
96. Agreement-for-sale & Documentation Assistant (draft from template, schedule of payments, carpet-area schedule; **registration and legal sign-off reserved**) - B - legal manager
97. Customer Handover / Possession Manager (checklists, snag closure, key handover, utility transfers) - A - handover manager
98. Customer Care & Defect-liability Desk (post-possession tickets, DLP clock, vendor dispatch, warranty tracking) - A - service head
99. Investor / Lender Reporting Assistant (project updates, KPIs, MIS packs) - A - IR / finance

### 13. Operations: facility, property & community  (R5 C; existing property/society employees)
100. * Property Manager Assistant - rent roll, tenants, maintenance, utility bills, inspections - A - property manager
101. * Society / Association Manager - maintenance dues, notices, meetings, AGM minutes, complaints, vendors (state society law differs) - A - society secretary / manager
102. Facilities Manager's Assistant (CAFM-type: work orders, PPM, SLAs, vendor scorecards, space use) - A - FM head
103. MEP Maintenance Planner (PPM plans for HVAC, DG, UPS, pumps, lifts; fault logs; spares) - A - chief engineer
104. Energy Manager / Auditor Assistant (meter data, tariffs, benchmarking, savings projects, ECBC checks; pylab) - B - energy auditor
105. Lift / Fire / STP / WTP Compliance Tracker (AMC, inspection dates, operator logs, discharge limits) - A - FM
106. Housekeeping & Security Rosters (shifts, patrol logs, visitor records) - A - FM
107. Structural-safety & Building-audit Scheduler (periodic audits, defects tracker; **certification by the registered engineer**) - A - society / owner
108. Asset & Space Manager (asset register, warranty, depreciation; asset information from handover) - A - asset manager
109. Digital Twin Data Steward (asset data model, sensor feeds, COBie handover, naming) - B - asset information manager

### 14. Sustainability, commissioning & performance  (R6 C-D)
110. Green Building Consultant's Assistant (IGBC / GRIHA / LEED credit tracker, evidence binder, calculations; **assessor decides**) - B - AP / CP
111. ECBC / Energy-code Compliance Checker (envelope, lighting, HVAC prescriptive tables; whole-building simulation inputs) - B - ECBC assessor
112. Energy Modelling Assistant (EnergyPlus/IDF input preparation, results tables, sensitivity) - B - energy modeller
113. Daylight & Thermal-comfort Analyst (open tools; results explained, not certified) - B - building physicist
114. Embodied Carbon / LCA Assistant (material quantities x EPD factors, hot-spot list) - B - LCA assessor
115. Water, Rainwater & Waste Planner (demand, recharge, STP sizing sheets, C&D waste plans) - B - consultant
116. Commissioning Authority's Assistant (Cx plan, functional test scripts, issue log, seasonal tests; **Cx sign-off reserved**) - B - commissioning manager
117. T&C Records Keeper (test certificates, balancing reports, as-installed values vs design) - A - T&C engineer
118. M&V Analyst (measurement and verification of savings, baseline models in pylab) - B - energy analyst

### 15. Visualisation, marketing media & training
119. Architectural Visualiser (renders, walkthroughs, VR scenes from models; Hoola image/video engines) - A - visualiser
120. Presentation & Report Designer (design reports, board packs, HOOLA PRINT) - A - architect / PM
121. Construction Skill Trainer (trade skill modules in local languages: BIM basics, safety, bar bending, tiling, with voice and video; CSDCI QP-aligned) - A - training centre
122. Construction Student Tutor (civil / architecture: IS codes, structures, estimating exercises; Guru Sahayak) - A - faculty
123. Contractor Business Coach (pricing, bidding, cash flow, GST, labour law basics for small builders; no legal or tax advice) - A/B - contractor / CA

## NEVER an AI Employee (tier C)
Sign or stamp a drawing, structural design, stability, fire, MEP, completion or occupancy certificate; file a permission
application in the licensee's or owner's name; certify RERA percentage completion or escrow withdrawal; accept or
reject work on site (inspection pass, concrete cube acceptance); approve a design or a change order; sign a contract;
release a payment or a bank guarantee; issue a notice, termination or LD deduction; decide delay entitlement;
certify measurement or an RA bill; give a safety clearance or permit-to-work; certify green rating, commissioning or
energy audit; give a structural-safety verdict.

## Suggested build order
1. **Wave 1 - records and money (tier A, builders pay for it at once)**: 61, 62, 64, 67, 70, 71, 75, 78, 85, 87, 88, 90, 91, 92, 98 - extend the existing Theka Sahayak/Site Supervisor.
2. **Wave 2 - the file-builders and checkers**: 9, 16, 28, 29, 35, 36, 37-39, 44-46, 52-56, 72, 73, 81, 93.
3. **Wave 3 - model-level and certificate-adjacent**: 18-21, 10-12, 22-24, 26, 47, 82, 104, 110-118 (needs open formats and a licensee on every output).
Fit to Hoola: department **"Construction & Real Estate"**; extend `site_manager` (Theka Sahayak) and `site_supervisor` first (the
live field tools), then `architect_assistant`; reuse engineering CAD/DXF/vision review, doc studio + HOOLA PRINT, Maps
(59), Khata (87-92), pylab (1, 42, 43, 65, 118), WhatsApp opt-in (94), `appmaker` (a contractor/PMC app), HyperFrames (95, 119),
approval cards for every signer step, state-by-state rule packs as data (not code).
**Best first pilot**: a small contractor or a mid-size builder on ONE project in ONE state (Maharashtra, best documented) -
daily site log + measurement + wage/RA-bill + material reconciliation + RERA/escrow paperwork. It is record-keeping with
direct cash impact; no certificate is signed by software.

## Open questions for the owner
- Which seat first: **contractor / site** (existing Theka Sahayak, mass market, mobile-first), **builder-developer** (approvals,
  RERA, sales), **architect/consultant** (DESIGN_DESK_PLAN), or **FM/society** (property/society employees)?
- State first? The register assumes Maharashtra/MahaRERA; building rules differ in every state, so rule packs are data
  that someone must own and keep current (a recurring cost).
- Are drawings DWG/PDF only (likely) or IFC? Model-level checks (Wave 3) only work on open formats and sit above the market's
  habits; start with PDF/DWG-based checking and document handling.
- Voice-first for site workers in local languages: Hindi/Marathi supervisors do not type - a voice-and-photo daily-log flow
  is the likely winning interface (extends the call/voice stack).
- "GO per field" turns any field into an engineering-grade spec with the exact IS codes and state rules checked.
