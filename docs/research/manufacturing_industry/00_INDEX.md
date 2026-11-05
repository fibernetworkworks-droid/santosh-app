# The manufacturing industry across the world - AI Employees register

Owner's ask (5 Nov 2026): *"NOW A MANUFACTURING INDUSTRY AI EMPLOYEES"*. Twenty-first in the series. Manufacturing here means turning materials
into goods: discrete (automotive, machinery, electronics, appliances, furniture, toys), process (chemicals, plastics, metals, paper, cement, food),
textile and garment, packaging, MSME job shops and tool rooms, foundries and forging, contract manufacturers, and the engineering, quality, maintenance,
supply-chain, EHS, automation and digital functions inside every plant. Pharma plants, medical-device makers and fashion/beauty makers have their own
registers (cross-referenced as PH#, MD#, FB#); logistics (goods movement) is LG#; construction and agriculture are separate.

**10 fields, 133 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Laws and standards named are from memory
  and **must be re-checked on primary text per country and sector** before any desk is built: in India the Factories Act 1948 and state rules, the four
  Labour Codes (status and effective dates to verify), ESI/PF, BIS standards and Quality Control Orders (QCOs; mandatory certification marks), BIS
  licences (ISI), Legal Metrology, PESO for explosives/petroleum, pollution-board consent to establish/operate (CTE/CTO), hazardous-waste and
  EPR rules, Boilers Act, GST and e-way bill, Udyam/MSME payment-timeline rules (45-day payment), PLI and state incentive schemes; abroad ISO 9001,
  IATF 16949, ISO 14001, ISO 45001, ISO 50001, IEC 61508/62443 (functional safety and industrial cybersecurity), CE/UL/RoHS/REACH, OSHA, EU Machinery
  Regulation, GDPR for employee data, EU CBAM/CSDDD for exporters.
- **Already in Hoola** (extend, do not rebuild): the **Engineering Desk** (`app/engineering/`: CAD Engineer with CadQuery parts, ISO fasteners/gears/bearings H-library,
  assemblies + BOM + mass, FEA (stress, heat, modes, buckling, plastic, contact, flow), **DFM** for FDM/SLA/SLS/MJF/metal PBF/CNC/sheet/moulding, CAM G-code, real drawings with
  ISO 286 fits and ISO 2768, mechanisms/URDF/MuJoCo, STEP/GLB/STL/3MF/DXF) and tool `eng_calc`; the Enterprise suite's **PLM** desk (BOM explode, where-used, change records;
  caps stated), **supply_opt** (reorder point with safety stock, dead stock, stock-out date), **ERP/BPA/ecom** desks, **TPM** (critical path, capacity, metrics, RAID,
  readiness), `warehouse_manager` ("Godown": bin stock, GRN, pick lists, cycle counts), `fleet_manager`, Khata and GST/HISAAB/Tally exports, PAISA payments, Data Desk + pylab,
  research engine, doc studio, `appmaker` (supervisor/operator apps with offline outbox, QR scan field, dashboards), WhatsApp opt-in, voice stack in Indian languages, vision review,
  and `iiot` (Industrial IoT Architect: paper design only, not live). Roles with `*` exist in some form. The Mera-PC freeze is untouched.

## The findings that shape every manufacturing desk
### 1. The machine, the line and the batch belong to people with authority and liability; the AI never touches the physical process
Ladder as before: **A** admin/prepare, **B** assist (analyse / schedule / draft / flag for a named engineer), **C** reserved.
Reserved here: writing to a PLC, DCS, robot or CNC controller or changing a safety interlock, setpoint or alarm limit in a running process; releasing a product lot or
signing a conformity/quality certificate; declaring a machine safe to run or a lockout complete; accepting or rejecting nonconforming material on authority; stopping/starting a line
on its own; approving a supplier, a design freeze, a process validation or an ECN; reporting an accident or environmental release to authorities; hiring, firing, disciplining; and
handling hazardous materials. **The AI watches, analyses, schedules, drafts and reminds in read-only or simulation mode; the engineer, operator, quality head and plant manager decide
and act.** Any link to control systems is read-only unless a licensed integrator has built a safety-rated, human-confirmed gateway.

### 2. Manufacturing wins and loses on a few numbers: OEE, yield, OTIF, cost per unit, inventory turns, downtime, scrap, safety
Most plants, especially the MSME majority, run on Excel, WhatsApp and memory: no real-time view of what was produced, what was rejected, why a machine stopped, what material is short,
or whether a customer order will ship on time. Gains: capturing shop-floor data cheaply (voice, QR, photo, simple apps), planning with real constraints, preventive maintenance,
supplier follow-up, quality traceability and clean costing. These are tier A/B and have immediate payback.

### 3. Safety, quality and traceability are legal and contractual; documentation is half the job
Factory licences, safety audits, near-miss logs, calibration, ISO/IATF documents, customer audits, PPAP/FAIR packs, batch records, supplier certificates, test reports, BIS marking.
A tireless record-keeper that never forgets a due date and never fabricates an entry is the biggest quiet value, and it keeps the plant audit-ready and the owner out of trouble.

### 4. IT/OT convergence creates a cybersecurity and reliability hazard
Plants are increasingly connected: machine data to cloud, remote support, ERP-MES links. Ransomware and mis-configurations stop lines. The AI stays on the IT side of the boundary
(historian data, work orders, alarms export), with signed, audited, least-privilege access, and never becomes a path to the PLC.

### 5. India's manufacturing is MSME clusters: thousands of job shops, small factories, tool rooms, foundries, textile units
Typical pains: late payments, order inflow volatility, drawing/spec confusion, rework, vendor delays, power cuts, skilled-operator shortage, compliance paperwork, no costing, export documentation.
A WhatsApp-native, voice-first, local-language owner-copilot is the highest-leverage product. Cluster-level services (shared testing, group purchasing, common facility centres) are a second wedge.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [E] engineering/R&D, [P] production planning and operations, [Q] quality and testing, [M] maintenance and reliability, [S] supply chain and procurement, [H] EHS and people, [D] digital/OT/automation, [F] finance and business, [O] MSME owner / cluster, [R] regulation and trade.

### 1. Product design, engineering & NPI  [E]
1. * CAD/Design Engineer's Assistant (existing Engineering Desk) - parts and assemblies from a brief, standard parts (ISO fasteners, gears, bearings), BOM, mass, drawings with fits and tolerances; **engineer approves** - B - design engineer
2. * Design for Manufacturability Reviewer (existing DFM) - measured walls, overhangs, inside corners, draft, undercuts, setups, bends by process; FAIL means redesign with reasons - B - manufacturing engineer
3. * Simulation Engineer's Assistant (existing FEA/flow/fatigue/contact) - stress, thermal, modal, buckling, joint and fatigue checks; limits stated; **analyst owns conclusions** - B - CAE engineer
4. Requirements & Spec Writer (customer RFQ to technical spec, ambiguities list, acceptance tests, standards map) - B - systems / application engineer
5. Material Selection Assistant (properties tables, cost, availability, standards, corrosion/temperature limits, alternatives; sources cited) - B - materials engineer
6. Tolerance Stack & GD&T Checker (stack-up calculations, datum schemes consistency, inspection feasibility) - B - design engineer
7. Prototype & Rapid-manufacturing Coordinator (3D print/CNC/laser/sheet prototype quotes, lead times, test plan, learnings log) - A - NPI engineer
8. Bill of Materials Manager (multi-level BOM, variants, revisions, where-used, cost roll-up, alternates; PLM desk) - A - engineering data manager
9. Engineering Change Manager (ECR/ECN workflow, impact analysis on stock/WIP/suppliers/documents, approvals tracking; **change board approves**) - B - change board
10. Standards & Compliance Mapper (CE/BIS/UL/IEC clauses to design checklists; test plan; evidence index; **certifier decides**) - B - compliance engineer
11. Reverse-engineering & Drawing Recovery Assistant (scan/photo to dimensional sketches and draft CAD; accuracy limits; IP checks) - B - design engineer
12. Technical Documentation Writer (manuals, work instructions, safety labels, multilingual, illustrated steps; HOOLA PRINT) - A/B - technical writer
13. R&D Lab Notebook Assistant (experiments plans, data capture, statistics via pylab, DoE design, reproducibility; Notebook) - B - R&D scientist
14. Patent & Prior-art Scout (landscape search with sources, claim charts for counsel; **attorney advises**) - B - IP counsel
15. Cost Engineering Assistant (should-cost models: material, machining time, overheads, tooling amortisation; target-costing options) - B - cost engineer
16. Tooling, Die & Mould Designer's Assistant (design checks, cooling/gating guidelines, wear parts lists, maintenance schedule) - B - tool designer
17. Sustainability & Ecodesign Assistant (LCA data, recyclability, restricted substances, repairability; evidence-based) - B - ecodesign lead

### 2. Production planning, scheduling & shop-floor operations  [P]
18. Demand-to-Plan Assistant (sales orders and forecasts to MRP inputs, capacity check, shortage alerts, what-ifs; pylab) - B - production planner
19. Finite-capacity Scheduler (job-shop/flow-shop scheduling with setups, due dates, maintenance windows, operators; explains trade-offs; **planner approves**) - B - production planner
20. Daily Production Control (shift plan, WIP board, expedite list, deviation reasons, hand-over notes) - A - production supervisor
21. Shop-floor Data Collector (voice/QR/photo entry of quantities, rejects, stoppage reasons by operators in local language; offline) - A - operator / supervisor
22. OEE & Downtime Analyst (availability, performance, quality losses, Pareto of stoppage reasons, top-3 actions; pylab) - A - plant manager
23. Work-order & Routing Manager (operations sequence, standard times, tooling lists, instructions, status; **ECR for changes**) - A - process engineer
24. Line Balancing & Layout Assistant (takt time, cycle times, station loads, ergonomics flags, material flow; **industrial engineer decides**) - B - industrial engineer
25. Standard Time & Method Study Assistant (video-based time study support with operator consent, motion elements, allowance rules) - B - industrial engineer
26. Changeover (SMED) Coach (changeover steps analysis, internal vs external tasks, checklists, tracking) - B - lean lead
27. Kanban & Material Flow Planner (min-max cards, supermarket sizing, replenishment signals) - A - production planner
28. Subcontract & Job-work Manager (challans, material sent/received, rates, quality returns, reconciliations; GST job-work rules) - A - production / accounts
29. Order Promising & Customer Update Agent (OTIF calendar, honest ship-date ranges, delay messages in customer's language; **sales head approves commitments**) - B - sales / planning
30. Batch / Lot Tracking Assistant (raw lot to WIP to finished goods traceability, forward/backward trace on demand) - A - quality / production
31. Packing & Dispatch Coordinator (packing lists, labels, barcode checks, truck loading plan, e-way bill prep; cross-ref logistics register) - A - dispatch
32. Plant Visual Management Dashboard (shop boards on TV/phone: output vs plan, rejects, safety days; no worker-level shaming) - A - plant manager
33. Lean/Kaizen Facilitator (waste walks, 5S audits, suggestion tracking, A3 reports, savings validation) - A - lean manager
34. Tool Crib & Consumables Manager (issues, returns, regrind life, breakage analysis, reorder) - A - tool-crib in-charge
35. Rework & Scrap Analyst (causes, cost, trends, containment suggestions; **QA disposition by MRB**) - B - quality engineer

### 3. Quality management & testing  [Q]
36. Incoming Inspection Assistant (supplier lot sampling plans (AQL), checklists, measurement records, certificate matching, accept/reject recommendation; **inspector or QA head decides**) - B - incoming QC
37. In-process Control Assistant (control plans, SPC charts (X-bar/R, p-chart), Cp/Cpk, out-of-control rules alerts, containment steps) - B - quality engineer
38. Final Inspection & Test Record Keeper (test reports, serial-wise data, golden sample comparisons, certificates of conformity drafts; **QA head signs**) - A/B - QA
39. Measurement System Analysis Assistant (Gauge R&R, calibration intervals, drift trends, uncertainty tables) - B - metrology engineer
40. Calibration Manager (instrument register, due dates, certificates, out-of-tolerance impact assessment; **calibration lab certifies**) - A - metrology
41. Nonconformance & CAPA Manager (8D/5-Why/Ishikawa templates, owner and deadline tracking, effectiveness checks; **QA head closes**) - A/B - quality manager
42. Customer Complaint Handler (intake, containment, root cause tracking, response drafts within customer formats; **quality head approves responses**) - B - customer quality
43. Supplier Quality Manager (scorecards, audits plan, SCARs, PPM tracking, certificates validity) - A - SQE
44. PPAP/FAIR/APQP Pack Assembler (document checklists, evidence index, dimensional results tables; **customer approves**) - A/B - quality engineer
45. ISO/IATF Documentation Assistant (procedures, work-instruction control, internal audit schedules, management review inputs, clause mapping; **management rep owns**) - A/B - management representative
46. Internal Audit Runner (checklists by process, findings log, follow-up) - A - internal auditor
47. Visual Inspection Assistant (camera-based defect flags on photos/video as an aid; confidence and false-negative warnings; **inspector confirms critical defects**) - B - inspector
48. Test Lab Scheduler & Records (test rigs, samples queue, standards methods, uncertainty, reports; NABL-style documentation) - A - lab head
49. BIS/ISI Marking & QCO Compliance Assistant (scheme requirements, test frequencies, records, factory inspection prep; **licensee responsible**) - B - quality head
50. Traceability & Recall Simulator (mock recall exercises, affected lots, customers, time to trace; **recall decisions human**) - B - quality manager
51. Statistical Analysis Assistant for Quality (hypothesis tests, DOE results, capability studies in pylab with assumptions checks) - B - quality engineer

### 4. Maintenance, reliability & asset management  [M]
52. Preventive Maintenance Planner (PM schedules by hours/cycles/calendar, checklists, spares kits, shutdown planning; CMMS) - A - maintenance manager
53. Breakdown Logger & Root-cause Coach (voice entry of faults, downtime codes, repair actions, 5-Why prompts, repeated-failure flags) - A - maintenance engineer
54. Predictive Maintenance Analyst (vibration/temperature/current data, trends and thresholds, remaining-life ranges with uncertainty; alerts to engineers; **no automatic stops**) - B - reliability engineer
55. Spare Parts & MRO Inventory Manager (criticality, min-max, vendor lead times, obsolete parts, cross-references, kitting) - A - stores / maintenance
56. Lubrication & Condition-based Routes Assistant (route cards, oil analysis tracking, schedules) - A - maintenance technician
57. Energy & Utilities Monitor (compressed air, steam, power factor, DG usage, chiller efficiency; leak and waste alerts; pylab) - B - energy manager
58. Lockout/Tagout Records Assistant (LOTO permits log, isolation checklists, audit trail; **authorised persons apply locks**) - B - maintenance supervisor
59. AMC & Vendor Service Tracker (contracts, response times, invoices vs work, warranty claims) - A - maintenance / purchase
60. Asset Register & Lifecycle Planner (age, cost of ownership, overhaul windows, replacement business cases) - A - asset manager
61. Boiler, Pressure Vessel & Statutory Equipment Tracker (inspection certificates, competent person visits, safety valve tests; **competent person certifies**) - A - EHS / maintenance
62. Technician Skills Coach (troubleshooting trees, safety reminders, manuals Q&A with sources, voice in local languages) - A - technician
63. TPM (Total Productive Maintenance) Facilitator (autonomous maintenance checklists, loss trees, pillar scorecards) - A - TPM lead

### 5. Supply chain, procurement & materials  [S]
64. * Supply Planner (existing supply_opt) - reorder point with safety stock, dead stock, stock-out dates, lead-time variability - B - planner
65. Procurement Officer's Assistant (RFQs, comparative statements, PO tracking, delivery follow-up, price history) - A - purchase manager
66. Vendor Development & Onboarding Assistant (capability questionnaires, document checks (GST, MSME, quality certs), trial orders, scorecards) - A - supplier development
67. Supplier Risk Monitor (single-source exposure, financial/news signals from lawful sources, country risks, alternates) - B - supply-chain risk
68. Inbound Logistics Coordinator (supplier dispatch tracking, gate scheduling, freight comparison; cross-ref logistics) - A - logistics
69. Inventory Optimisation Analyst (ABC/XYZ, safety-stock policy, slow movers, write-off risks; pylab) - B - inventory manager
70. Make-or-Buy & Outsourcing Analyst (cost, capacity, risk scenarios) - B - operations head
71. Import/Export Compliance Assistant for Materials (HS, duty, licences, MOOWR/bond schemes, drawback; **CHA/officer decides**) - B - EXIM
72. Raw-material Price Watcher (steel, aluminium, polymers, copper indices, hedging scenarios explained; no trading advice) - A - purchase / finance
73. Contract Manufacturing Coordinator (quality agreements, forecasts, audits, change notices) - A - supply management
74. Scrap, By-product & Waste Sales Manager (grading, bids, weights, GST, environmental rules) - A - stores / EHS
75. Counterfeit & Grey-market Component Guard (electronics: traceability, authorised distributors, test flags) - B - supply quality
76. Customer Collaboration Desk (order forecast sharing, portal updates, EDI mapping, ASN labels) - A - sales ops

### 6. EHS, people & skills  [H]
77. EHS Officer's Assistant (hazard registers, risk assessments (HIRA/JSA), toolbox talks, PPE issue, inspection checklists, safety KPIs) - A/B - safety officer
78. Incident & Near-miss Reporter (voice/photo intake, classification, investigation templates, corrective actions; **investigations led by safety head; statutory reporting by occupier**) - B - EHS manager
79. Permit-to-work Assistant (hot work, confined space, height permits, validity, handover; **authorised issuers sign**) - B - permit issuer
80. Chemical & Hazmat Compliance Tracker (SDS library, storage compatibility matrix, inventory limits, labelling, emergency plans; **competent person approves**) - B - EHS
81. Environmental Compliance Assistant (CTE/CTO conditions, stack/effluent monitoring logs, hazardous waste manifests, EPR returns; **filings by occupier**) - A/B - environmental officer
82. Factory Licence & Statutory Calendar (Factories Act licence, registrations, returns, medical exams, fire NOC, boiler, lifts, labour codes filings) - A - compliance officer
83. Occupational Health Assistant (medical exam schedules, exposure monitoring records, ergonomic assessments; **doctor decides fitness**) - B - factory medical officer
84. Skilled-worker Training Matrix (machine authorisations, certifications, refreshers, multi-skilling, apprenticeship tracking) - A - HR / training
85. Shop-floor Training Coach (voice/video SOP training in local language, quizzes, practical sign-off by supervisor) - A - trainer
86. Attendance, Shift & Wage Assistant (muster, overtime limits, piece-rate, advances, PF/ESI; **payments on owner's tap**) - A - HR / accounts
87. Contract-labour Compliance Desk (contractor licences, wages register, safety induction, principal-employer obligations) - A - HR / compliance
88. Recruitment & Skills Matching Assistant (operator trials, trade tests scheduling; fair hiring rules) - A/B - HR
89. Grievance & Safety Suggestion Channel (anonymous intake, routing, closure tracking; **committee decides**) - B - HR head
90. Emergency Preparedness Assistant (mock drills, evacuation plans, assembly counts, first-aid inventory, onsite emergency plan upkeep) - A - safety officer
91. Ergonomics & Fatigue Risk Advisor (task analysis, job rotation plans; privacy-safe; no worker surveillance) - B - ergonomist

### 7. Industrial automation, OT/IIoT, MES & cybersecurity  [D]
92. Industrial IoT Architect's Assistant (existing iiot paper desk, to be made live) - device lists, protocols (Modbus, OPC UA, MQTT), network zones, data models, BOM; paper design only - B - automation architect
93. Machine Data Integration Assistant (read-only connectors to historians/PLC gateways via OPC UA/MQTT; data dictionary, unit checks, tag mapping tests; **no write-back**) - B - controls engineer
94. MES Implementation Analyst (requirements, shop-floor flows, master data, test scripts, cutover) - A - project lead
95. ERP/MES Integration Mapper (work orders, material issues, confirmations, quality results; sync checks) - A/B - integration lead
96. PLC/Robot Program Reviewer (static review of exported programs against coding standards, interlock lists, unusual logic; **never uploads to controller**) - B - controls engineer
97. Digital Twin & Simulation Assistant (discrete-event models of lines, bottleneck studies, layout what-ifs, pylab) - B - simulation engineer
98. OT Cybersecurity Watcher (asset inventory, patch status, network exposure, anomalous remote-access logs; segmentation advice per IEC 62443; **response by security team**) - B - OT security lead
99. Robotics & Automation Business-case Builder (cobots, vision systems, AGVs: payback, safety standards, workforce transition plans) - B - automation engineer
100. Machine Vision Project Assistant (use-case scoping, lighting/optics selection, dataset labelling plans, validation metrics; false-reject trade-offs) - B - vision engineer
101. Edge Data & Dashboard Builder (appmaker/Grafana-style dashboards from CSV/API exports; offline sync) - A - IT / production
102. AI Model Governance for Plants (inventory of AI uses, validation, drift, human override rates, change control; HC#160 pattern) - B - AI governance committee
103. CNC Programmer's Assistant (existing CAM G-code: toolpath ideas, feeds and speeds tables, collision checks in simulation; **programmer proves out on machine**) - B - CNC programmer
104. 3D Printing / Additive Manufacturing Planner (orientation, supports, build packing, post-processing, cost per part; DFM) - B - AM engineer

### 8. Cost, finance & business management  [F]
105. Product Costing Assistant (material, labour, overhead, scrap, setup amortisation; margins by customer/product; quote support) - A/B - cost accountant
106. Quote & Estimation Desk (RFQ intake, drawings read, process routing, cost build-up, margin options, lead time; **owner sets price**) - B - estimator
107. Order Book & Delivery Tracker (customer orders, status, delays, payments due; WhatsApp updates) - A - sales / planning
108. Accounts Receivable & Collections for Manufacturers (MSME Samadhaan/45-day rules awareness, reminders, ageing, statement tone; Khata) - A - accounts
109. GST, E-way & Compliance Assistant (job-work, RCM, ITC reconciliation, e-invoicing thresholds; **CA files**) - B - accountant
110. Working-capital & Funding Navigator (cash cycle, factoring, CGTMSE, MUDRA, PLI, state subsidies, export credit; **lender decides**) - A/B - owner / CFO
111. Capex Planner (machine purchase cases, payback, depreciation, finance options; scenarios) - B - CFO
112. Plant Performance Reporter (monthly pack: OEE, OTIF, scrap, cost, safety, energy; commentary drafts for owners) - A - controller
113. Customer Audit & Visit Coordinator (visit prep, evidence binders, action trackers) - A - quality / sales
114. MSME Owner Copilot (daily dashboard on WhatsApp: today's orders, shortages, machine status, receivables, tasks; voice) - A - owner
115. Founder Copilot for Manufacturing Start-ups (idea to factory: process choice, layout, licences, funding, first customers, cost model) - A/B - founder

### 9. Sector-specific desks  [E/P/Q]
116. Auto-component Supplier Assistant (IATF, PPAP, line audits, JIT call-offs, customer score cards) - B - quality / sales
117. Electronics & EMS Assistant (BOM risk, AVL, SMT line OEE, solder profiles, ESD controls, traceability, test coverage) - B - EMS engineer
118. Textile & Garment Production Assistant (cut plans, bundle tracking, line efficiency, piece-rate wages, buyer compliance audits; cross-ref fashion register) - A - production manager
119. Food Processing Plant Assistant (batch records, HACCP/FSSAI logs, shelf-life tests, cold chain; cross-ref agriculture/pharma GDP) - B - QA manager
120. Foundry & Forging Assistant (heat records, melting charge calc, defect analysis, die life, pattern inventory) - B - metallurgist
121. Plastics & Packaging Plant Assistant (mould schedules, cycle times, resin lot tracking, colour matching, regrind control) - B - production engineer
122. Chemicals & Process Plant Assistant (batch recipes, reactor logs, yield and mass balance, hazardous inventory, emergency plans; **chemist/engineer approves**) - B - process engineer
123. Heavy Fabrication & Welding Shop Assistant (WPS/PQR records, welder qualification, NDT schedules, weld maps) - B - welding engineer
124. Furniture, Woodwork & Handicraft Workshop Assistant (cut lists, material optimisation, customer orders, artisan payment records) - A - workshop owner
125. Machine Builder / SPM Assistant (project BOM, subassembly milestones, FAT/SAT checklists, commissioning punch-lists) - A - project manager

### 10. Clusters, regulators, education & ecosystem  [O/R]
126. Industrial Cluster Coordinator (common facility centre bookings, group purchasing, shared testing, training calendars, cluster dashboard) - A - cluster manager
127. Export Readiness Assistant (certifications, buyer requirements, packaging, documentation, EU CBAM/REACH awareness; **certifiers and CHA decide**) - B - exporter
128. Government Scheme Navigator for Manufacturers (PLI, PMEGP, CLCSS, state subsidies, GeM registration, MSME benefits; eligibility screening; **authority sanctions**) - A - owner
129. Industry Inspector's Assistant (inspection schedules, checklists, findings log; **inspector decides**) - B - labour/factory inspector
130. Skills & ITI Training Assistant (curriculum aligned to NSQF, trainee logbooks, trade tests prep; Guru Sahayak) - A - trainer
131. Engineering Student Tutor (manufacturing processes, metrology, industrial engineering, CAD/CAM; Prayogshala labs) - A - student
132. Technology Transfer & Industry-Academia Match Assistant (needs/capabilities matching, project proposals, IP basics) - A/B - incubator
133. Circular Manufacturing Planner (remanufacturing, material recovery, take-back, EPR obligations) - B - sustainability lead

## NEVER an AI Employee (tier C)
Write to or reprogram a PLC, DCS, robot or CNC controller, or change a safety interlock, alarm limit or setpoint in a running process; stop or start a line, bypass a guard, or declare a machine safe or a lockout complete; release a lot, sign a
CoC/CoA or quality certificate, or disposition nonconforming material; approve a supplier, design freeze, process validation or ECN; certify calibration or statutory inspections; investigate or report an accident or environmental release to authorities as the occupier;
hire, fire or discipline; handle hazardous materials; use camera analytics to score or surveil individual workers; scrape supplier/customer portals against terms; sign contracts or pay vendors without the owner's explicit tap.

## Suggested build order
1. **Wave 1 - MSME owner-copilot and shop-floor records (tier A, WhatsApp/voice native)**: 114, 21, 20, 22, 107, 108, 65, 53, 52, 55, 77 (log side), 82, 86, 105, 106, 64.
2. **Wave 2 - planning, quality and engineering assist with a named engineer**: 1-3, 8, 9, 18, 19, 23, 30, 36-38, 41-43, 45, 54, 66, 69, 87, 94, 112.
3. **Wave 3 - safety-critical, OT-adjacent or certificate-adjacent roles**: 44, 47, 49, 50, 54 (predictive), 58, 61, 78-81, 93, 96, 98, 100, 102, 116, 122 - need licensed engineers, read-only gateways and strict audit trails.
Fit to Hoola: department **"Manufacturing & Industry"**; the Engineering Desk (CAD/DFM/FEA/CAM), PLM, supply_opt, TPM, ERP/BPA desks, warehouse and fleet employees already give Hoola the deepest
head start of any series entry on the engineering and planning side, but **nothing yet exists for shop-floor operations, quality records, maintenance or EHS**; those are the new base.
Reuse `appmaker` (operator/supervisor apps with QR scan, offline outbox, dashboards), voice and WhatsApp in local languages, vision review, pylab (SPC, OEE, DoE, forecasting), Data Desk,
Khata/GST/Tally, PAISA, approval cards for every release, disposition, payment and filing, and the audit trail. Keep every OT link **read-only**.
**Best first pilots**: (a) an **MSME job shop / small factory** (CNC, fabrication, plastics, garments) with a WhatsApp-voice **owner copilot + shop-floor logger + maintenance and quality records**
(114, 21, 22, 52, 53, 36, 41, 106-108) - daily pain, cash-linked, no OT integration risk; (b) an **engineering design/NPI team** using the existing Engineering Desk (1-9, 15, 16);
(c) a **cluster body** (126, 128). Large OEMs and process plants come later: security, validation and integration are heavy.

## Open questions for the owner
- Which side first: **MSME owners**, **engineering/NPI teams**, **mid-size plants (quality + maintenance)**, **clusters/associations**, or **OEM suppliers**? I'd start with MSME owners and keep using the Engineering Desk for engineering teams.
- Sector: which verticals first (auto components, fabrication, plastics, textiles, electronics, food processing)? Each adds standards, defect catalogues and process templates.
- OT boundary: confirm Hoola stays read-only on machine data, never writes to controllers, and never scores individual workers by camera or sensor.
- Languages and channel: shop-floor users prefer voice in Hindi/Marathi/Gujarati/Tamil; confirm voice-note and QR-scan input as first-class.
- Compliance posture: BIS/ISO/IATF documents and test records are legal evidence; confirm an immutable audit trail and electronic-record validation for any customer who needs it.
- "GO per field" turns any field into a sourced report with the Factories Act, Labour Codes, BIS QCOs, ISO/IATF and IEC 62443 text checked on primary documents.
