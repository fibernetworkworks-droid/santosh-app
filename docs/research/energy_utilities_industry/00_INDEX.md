# The energy & utilities industry across the world - AI Employees register

Owner's ask (5 Nov 2026): *"NOW A ENERGY AND UTILITIES INDUSTRY AI EMPLOYEES"*. Twenty-fourth in the series. Energy and utilities here means:
power generation (thermal, hydro, nuclear, solar, wind, storage, biomass), transmission and distribution (grid operators, discoms), power markets and trading,
oil and gas (upstream, midstream, downstream, retail fuel and LPG), city gas distribution, renewables developers and rooftop-solar installers (EPC), EV charging,
energy services and efficiency, carbon and hydrogen markets, water and wastewater utilities, district heating/cooling, and the regulators, consumers and
workers around them. Telecom and logistics infrastructure, government utility desks (GV#110-112) and manufacturing energy monitoring (MF#57) are cross-referenced.

**10 fields, 125 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Laws and codes named are from memory and
  **must be re-checked on primary text per country and utility** before any desk is built: in India the Electricity Act 2003 and its rules (consumer rights, open access,
  net metering/gross metering, rooftop programmes such as PM Surya Ghar), CERC and State Electricity Regulatory Commission regulations and the Grid Code, CEA regulations on safety
  and installation, power-market rules (exchange trading, ancillary services), the Energy Conservation Act and BEE schemes (PAT, star labelling, ECBC), MNRE guidelines and ALMM
  lists, the carbon market framework, PNGRB regulations for gas, the Petroleum Act and PESO licensing, LPG distributorship rules, EV-charging guidelines, the Water Act; abroad NERC
  reliability standards, IEC 61850/60870/62443, IEEE 1547, OSHA/NFPA 70E, EU grid codes, IEA data conventions. Rules change often (tariffs, subsidies, net-metering caps).
- **Already in Hoola** (extend, do not rebuild): **solar_check** (Google Solar API Building Insights: roof area, panels, sunshine, kWh; honest "not covered" when not covered), **Ghar / Home Assistant**
  (`app/home.py`: home devices read-only by default; control gated; AC 20-28 C, geyser/heater read-only by name), the government discom customer roles in the GV register, Maps (site routes, feeder
  geography), `mospi` (official energy/price statistics), pylab and Data Desk (load, tariff and bill maths), the research engine (tariff orders and regulations with sources), Khata/PAISA (bill collection),
  WhatsApp opt-in and voice in Indian languages (outage and billing agents), `appmaker` (field-crew and customer apps, shift-only location), the Engineering Desk (FEA/thermal/flow/fatigue, drawings),
  `iiot` (Industrial IoT architect, paper only), `isp_noc` pattern (alarm correlation and plain-words fault summary; same pattern reusable for substations), vision review, and HYPERFRAMES/Avatar films
  (customer education). Roles with `*` exist in some form. The Mera-PC freeze is untouched.

## The findings that shape every energy & utilities desk
### 1. Electricity, gas, pressure and chemistry kill people: the AI never operates the system; authorised, trained, permitted humans do
Ladder as before: **A** admin/prepare, **B** assist (forecast / analyse / draft / flag for a named engineer), **C** reserved.
Reserved here: switching, tripping, closing breakers, changing protection settings, setpoints, relay logic or interlocks; dispatching generation or load; issuing or cancelling permits-to-work and
lockout/tagout; declaring equipment safe or de-energised; energising a customer connection; shutting down or isolating gas, pressure or process systems; approving tariff or regulatory filings; emergency
grid actions (load shedding, black-start); disconnecting a consumer; and anything on a SCADA/EMS/DCS write path. **The AI works on the IT side of a strict one-way boundary: it reads exported data, forecasts,
schedules, drafts and reminds. Control actions are performed by licensed operators through certified systems and recorded.** Any future control link must be a safety-rated, human-confirmed, audited gateway built by a licensed integrator.

### 2. Reliability, safety and cost are the three numbers: SAIDI/SAIFI/CAIDI and AT&C losses, incident rates, and cost per unit
Utilities lose money to technical and commercial losses, theft, billing errors, outage restoration delays, maintenance backlogs and poor forecasts. The best AI use is mundane and high-value: load and
renewable forecasting, outage correlation and customer messaging, meter-to-cash accuracy, asset condition data, work-order planning, vegetation and corridor management, and field-crew productivity. These are tier A/B
with engineers in the loop and measurable results.

### 3. The consumer side is where most people meet energy: bills, outages, subsidies, rooftop solar and EV charging
A household's pains are bill shock, wrong readings, long outages, disconnection notices, new-connection delays, subsidy paperwork, vendor trust for solar, and choosing efficient appliances. A customer-side Hoola employee
(plain-language bill explainer, outage and complaint tracker, subsidy navigator, solar and EV planner, appliance advisor) fits Hoola's brand and needs no utility's approval; the utility-side counterparts need integration.

### 4. Energy transition adds complexity: variable renewables, storage, distributed energy, EVs, carbon markets
Forecasting, flexibility, demand response, battery dispatch plans, virtual power plants, curtailment, and certificates (RECs, carbon credits) are data-heavy and rule-heavy. Market and trading roles are tier B at most and require
licensed participants; "trading advice" is a regulated activity in many markets.

### 5. Operational technology security is national-security territory
Grid and pipeline cyber attacks cause blackouts and explosions. Rules: read-only data diodes where possible, segmentation (IEC 62443), signed audited access, no standing credentials, incident response with regulators (CERT-In rules in
India). Hoola's inherited rules apply: secrets never reach the model, audit trails, caps and kill switches.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [G] generation (thermal/hydro/nuclear/renewables/storage), [T] transmission and grid operations, [D] distribution utility/discom, [M] power markets and trading, [O] oil and gas (upstream/mid/down, retail fuel, LPG, CGD), [R] renewables developers/EPC/installers, [E] EV and energy services, [W] water and wastewater utilities, [C] consumer/prosumer/business customer, [X] regulator/policy/ecosystem.

### 1. Power generation & plant operations  [G]
1. Plant Performance Analyst (heat rate, availability, auxiliary consumption, outage causes, benchmarking; pylab) - B - plant manager
2. Generation Forecaster (wind/solar output from weather feeds and plant data, ranges not points; day-ahead and intraday) - B - scheduling engineer
3. Preventive Maintenance Planner for Plants (outage planning, spare parts, work orders, CMMS records) - A - maintenance head
4. Predictive Maintenance Analyst (vibration, temperature, oil analysis trends on turbines, transformers, gearboxes; remaining-life ranges; **engineer decides**) - B - reliability engineer
5. Operations Log & Shift Handover Assistant (voice-captured logs, event timelines, handover summaries, deviation notes) - A - shift engineer
6. Permit-to-Work and Isolation Records Assistant (permit registers, validity, handover; lists for LOTO review; **authorised persons issue and apply**) - B - permit issuer
7. Fuel & Coal Logistics Planner (rake/truck scheduling, stock yards, quality grades, GCV/ash tracking, demurrage control) - A - fuel manager
8. Water, Chemistry & Environmental Compliance Assistant (boiler/cooling water chemistry logs, emission data, effluent, ash utilisation, consent conditions; **occupier files**) - B - environment manager
9. Hydro Reservoir & Flood Planning Assistant (inflow forecasts, rule curves, release scenarios; **dam safety engineers decide**) - B - hydrology engineer
10. Wind Farm Operations Assistant (turbine SCADA exports, curtailment analysis, blade inspection photos, crane scheduling, access safety) - B - O&M manager
11. Solar Plant O&M Assistant (string/inverter alarms, soiling and degradation analysis, cleaning schedules, thermography review, warranty claims) - B - O&M engineer
12. Battery Storage Operations Assistant (state of charge/health, cycling plans, thermal alarms, degradation tracking, dispatch proposals; **operator confirms**) - B - storage operator
13. Biomass & Waste-to-Energy Plant Assistant (feedstock logistics, moisture/calorific data, emissions logs) - A/B - plant manager
14. Nuclear Plant Documentation Assistant (procedure libraries, change records, training records, regulatory correspondence tracking; **licensed staff only; no safety-system interface**) - A - plant documentation unit
15. Plant Safety Case & Incident Reporter (near-miss and incident logs, root-cause templates, corrective-action tracking; **safety head leads**) - B - safety manager
16. Plant Procurement & Spares Assistant (critical spares, lead times, vendor performance, obsolescence) - A - procurement
17. Plant Training Simulator Coach (scenario briefs, quizzes, procedure walk-throughs; **supervisor signs competencies**) - A - training head

### 2. Transmission & grid operations  [T]
18. Substation Alarm Correlator (like the ISP NOC pattern: groups alarms by topology and time, likely root cause, switching proposals as text for the operator; **no control commands**) - B - control-room engineer
19. Load Forecaster (short/medium/long term; temperature, calendar, events; ranges; MAPE tracking; pylab) - B - system planning
20. Outage Planning & Clearance Coordinator (maintenance outage requests, clash checks, impact studies, approvals tracker; **grid operator approves**) - B - outage coordinator
21. Protection Settings Records Assistant (relay settings database, change requests, test reports, coordination study documents; **protection engineer approves and applies**) - B - protection engineer
22. Line Patrol & Inspection Assistant (drone/photo defect triage, hotspot lists, corridor encroachment flags, work orders) - B - transmission O&M
23. Right-of-way & Vegetation Management Planner (corridor clearances, cutting schedules, landowner communication, permits; Maps) - A - ROW manager
24. Transformer Health Analyst (DGA trends, loading, temperature, age; condition scores with reasons; **engineer decides replacement**) - B - asset engineer
25. Grid Planning Study Assistant (data prep for load flow and contingency studies, report skeletons; **planner runs certified tools and concludes**) - B - planning engineer
26. Grid Code & Regulatory Compliance Tracker (obligations, reports, test schedules for generators and users; evidence) - A - compliance
27. Energy Accounting & Scheduling Reconciler (interchange schedules vs actuals, deviation settlement checks, REA/DSM statements) - A/B - scheduling / energy accounting
28. Control-room Log & Event Reporter (event timelines, disturbance reports drafts, root-cause summaries; **GM approves**) - B - system operator
29. Grid Cybersecurity Watcher (OT asset inventory, access logs, anomalous traffic, patch status; incident drills; **security team responds**) - B - OT security lead
30. Interconnection Application Tracker (generator and large-load connection studies status, documents, fees, deadlines) - A - interconnection engineer

### 3. Distribution utilities / discoms  [D]  (consumer-facing counterparts in section 8)
31. Feeder Loss Analyst (AT&C loss by feeder/DT, energy audit, outliers, theft hotspots as leads; **field verification; no accusations**) - B - distribution engineer
32. Outage Management Assistant (customer call clustering, fault location hints, crew dispatch suggestions, restoration ETAs with ranges, status messages in local languages) - B - outage coordinator
33. Meter Data Management Assistant (AMI/AMR reads validation, missing/estimated data flags, tamper alerts as leads, billing determinant checks) - B - metering engineer
34. Billing & Collections Assistant (bill accuracy checks, exception queues, payment reminders respecting rules, arrears plans; **disconnection only per regulation and human sign-off**) - A/B - revenue manager
35. New Connection & Load Extension Desk (application checks, site documents, estimate drafts, inspection scheduling, status messages; **engineer approves, energising by authorised staff**) - B - connection engineer
36. Distribution Planning Assistant (transformer loading, voltage, capex prioritisation scenarios, renewable hosting capacity; pylab) - B - planning engineer
37. Field Crew Dispatcher & Work-order Manager (priority, skills, location, parts, safety briefings, offline app; shift-only location) - A - field manager
38. Safety Observation Assistant (field audits, near-miss intake, LOTO compliance checks via checklists and photos; **safety officer decides**) - B - safety officer
39. Vigilance & Theft-detection Case Assistant (consumption anomalies, evidence packets, notice drafts; **vigilance officer decides; due process**) - B - vigilance officer
40. Subsidy & DBT Reconciliation Assistant (agriculture, domestic, industrial tariff subsidies, claims, government receivables) - A - finance
41. Smart Meter Rollout Programme Manager (installs tracking, vendor performance, comms, customer complaints) - A - programme manager
42. Demand Response & Peak-management Assistant (programmes, notifications, enrolments, event logs, settlement; consent-based) - B - DR manager
43. Distributed Energy Interconnection Assistant (rooftop solar/net-metering applications, document checks, inspection scheduling, meter swaps) - A/B - connection engineer
44. Regulatory Filing Assistant for Discoms (ARR/true-up data prep, tariff petitions drafts, compliance reports; **management and regulator process; filings by authorised officer**) - B - regulatory affairs
45. Consumer Grievance Redressal Assistant (CGRF intake, deadlines, evidence, response drafts; **forum decides**) - B - grievance officer
46. Utility Contact-centre Agent (outages, bills, new connections, tamper reports; multilingual voice/WhatsApp; escalate) - A - contact-centre head

### 4. Power markets, trading & energy management  [M]
47. Market Data Analyst (exchange prices, volumes, congestion, fuel prices; dashboards with sources) - A - market analyst
48. Bid Preparation Assistant (portfolio constraints, price scenarios, schedule proposals; **licensed trader submits**) - B - trader
49. Portfolio Risk Reporter (VaR-style exposures, mark-to-market, limit checks; pylab; **risk committee decides**) - B - risk manager
50. PPA Contract Assistant (term sheets, clause libraries, tariff formulas, delivery obligations, change-in-law clauses; **lawyer reviews**) - B - contracts manager
51. Open Access & Banking Settlement Assistant (applications, scheduling, charges calculation, energy accounting) - A/B - open-access cell
52. Renewable Certificate & Carbon-credit Tracker (REC issuance/redemption, carbon-credit registries, vintages; no trading advice; **registered participants transact**) - A - sustainability / trading
53. Imbalance & Deviation Settlement Analyst (DSM charges, forecast-to-actual error analysis, improvement actions) - B - scheduling
54. Demand-side Procurement Planner for Large Consumers (tariff options, open-access vs discom, PPA options, savings scenarios; ranges) - B - energy manager
55. Hedging and Fuel Procurement Analyst (coal/gas/oil contracts, index formulas, scenario analysis; **treasury/commercial head decides**) - B - fuel procurement
56. Virtual Power Plant / Aggregator Assistant (device enrolment, consent, dispatch rules, payouts calculation; **aggregator operator confirms**) - B - aggregator ops

### 5. Oil, gas & fuels  [O]
57. Upstream Data Assistant (well logs, production data cleaning, decline curves, reserve estimates as scenarios; **geoscientist/petroleum engineer concludes**) - B - petroleum engineer
58. Drilling Operations Reporter (daily drilling reports, NPT analysis, cost tracking, HSE observations) - A - drilling supervisor
59. Pipeline Integrity Assistant (inline inspection anomalies lists, corrosion trends, cathodic protection readings, pigging schedules; **integrity engineer decides**) - B - integrity engineer
60. Pipeline Leak & Anomaly Watcher (SCADA-exported flow/pressure trends, imbalance flags, alert escalation; **control room acts**) - B - pipeline controller
61. Refinery Planning Assistant (crude assay data, LP model inputs, product slate scenarios; pylab; **planners run licensed LP tools**) - B - refinery planner
62. Process Safety Management Assistant (HAZOP/LOPA records, MOC tracking, safety-critical elements tests, action closure) - B - process safety engineer
63. Retail Fuel Station Copilot (daily sales, stock/tank dips reconciliation, density and quality checks, pump calibrations, staff shifts, cash and card settlements, weights & measures verification dates) - A - dealer
64. LPG Distributor's Assistant (cylinder stock, deliveries, refill bookings, safety checks, subsidy DBT status, customer complaints, route plans) - A - distributor
65. City Gas Distribution Operations Assistant (connection pipeline, pressure surveys, meter reading, leak complaints, safety inspections of installations; **licensed inspectors certify**) - B - CGD operator
66. Fuel Quality & Adulteration Watcher (sampling schedules, test results, anomalies, mobile lab logs; **enforcement by authorities**) - B - quality officer
67. Oil & Gas Logistics Planner (tank trucks, rail rakes, terminals, product movement, demurrage; cross-ref logistics) - A - supply chain
68. Hydrocarbon Accounting Assistant (volumes, allocations, royalties and cess calculations, JV statements; **finance signs**) - B - accounting
69. Dangerous Goods & Terminal Safety Assistant (loading permits, vapour recovery records, fire-system tests, drills) - B - terminal manager
70. Energy Transition Strategy Analyst (hydrogen, biofuel, CCUS options, cost curves from public data; scenarios) - B - strategy

### 6. Renewables development, EPC & rooftop solar  [R]
71. * Solar Site Assessor (existing `solar_check`) - roof area, panel count, sunshine, kWh from Google Solar data; **honest "not covered" cases** - B - installer / owner
72. Rooftop Solar Proposal Builder (consumption analysis from bills, system size, payback ranges, subsidy applicability, financing options, PDF quote; shows assumptions) - B - installer
73. Solar Installation Project Manager (survey checklist, BOM, schedule, permits, net-metering application, commissioning checklist; **electrical supervisor signs**) - A/B - EPC project manager
74. Installer Business Copilot (leads, quotes, deposits, vendor payments, warranty tracking, customer follow-up on WhatsApp; Khata) - A - installer
75. Solar Design Checker (string sizing, voltage windows, cable losses, earthing and protection lists vs standards; **designer approves**) - B - design engineer
76. Subsidy & Net-metering Navigator (PM Surya Ghar and state schemes: eligibility, documents, portals steps on the user's tap, status tracking) - A - consumer / installer
77. Wind & Solar Resource Assessor (long-term data analysis, P50/P90 scenarios, uncertainty; **independent engineer certifies**) - B - resource analyst
78. Land & Permitting Tracker for Large Projects (title checks, consents, grid approvals, environmental clearances, community engagement logs) - A - development manager
79. Project Finance Model Assistant (cash-flow models, tariffs, debt sculpting, sensitivities; pylab; **lender case owned by CFO**) - B - project finance
80. Procurement & Supply-chain Assistant for Renewables (module/inverter bids, ALMM/BCD compliance checks, logistics, quality inspections) - A/B - procurement
81. Commissioning & Handover Documentation Assistant (test reports, as-builts, O&M manuals, warranties; **engineers sign acceptance**) - A - commissioning engineer
82. Hybrid & Storage Project Designer's Assistant (sizing studies, dispatch strategies, revenue stacking scenarios) - B - systems engineer
83. Community Solar and Mini-grid Operator's Assistant (member enrolment, billing, prepaid vending, tamper alerts, maintenance, tariff communication; rural settings) - A - mini-grid operator
84. Agrivoltaic & Solar-pump Advisor (farm sizing, pump selection, scheme eligibility; cross-ref agriculture) - B - farmer / installer
85. Green Hydrogen Project Assistant (electrolyser sizing, offtake modelling, safety case documentation) - B - project engineer

### 7. EV charging & energy services  [E]
86. EV Charging Network Operator Assistant (charger uptime, tickets, tariffs, roaming settlements, site planning with Maps, utilisation analytics) - A - CPO ops
87. EV Driver Companion (nearest chargers by connector and status, trip planning with charging stops, cost comparison, fault reporting; official data sources) - A - EV driver
88. Fleet Electrification Planner (route energy needs, charger sizing, TCO scenarios, charging schedules vs tariffs; pylab) - B - fleet manager
89. Charging Site Developer's Assistant (grid connection requests, load analysis, permits, civil/electrical checklists, landlord agreements) - A/B - site developer
90. Energy Service Company (ESCO) Assistant (baseline data, savings measurement and verification, performance contracts, reports) - B - ESCO engineer
91. Building Energy Manager's Assistant (BMS exports, anomaly detection, scheduling recommendations, comfort constraints; **facility manager decides**) - B - energy manager
92. Industrial Energy Audit Assistant (data collection sheets, load profiles, loss tables, savings scenarios with payback; BEE-style report skeletons; **certified auditor signs**) - B - energy auditor
93. Appliance & Lighting Efficiency Advisor (star ratings, payback calculators, subsidy schemes, bulk procurement packs) - A - household / institution
94. District Cooling/Heating Operations Assistant (plant efficiency, load forecasts, billing, maintenance) - B - operator
95. Microgrid Controller's Assistant (resource forecasts, dispatch plans, islanding procedures; **operators run controls**) - B - microgrid operator

### 8. Consumers, prosumers & businesses  [C]
96. Bill Explainer & Energy Coach (reads the electricity/gas bill, tariff slabs, fixed charges, units, taxes, meter reading checks; usage tips for the household; Hinglish) - A - household
97. Outage & Complaint Tracker (outage reports with proof, complaint numbers, escalation ladder to CGRF/ombudsman, drafts) - A/B - household
98. New Connection / Name-change / Load-change Helper (documents, fees, forms, appointment steps; official portals on the user's tap) - A - consumer
99. Rooftop Solar Buyer's Guide (vendor comparison on total cost and warranty, subsidy steps, red-flag scams, net-metering process; independent of installers) - A/B - household
100. Home Energy Monitor (Ghar integration: appliance usage read-only, anomaly alerts, bill forecasts; controls gated by the home-control switch) - A - household
101. Appliance Purchase Advisor (running cost vs price, star ratings, inverter vs non-inverter, repair vs replace) - A - household
102. Business Energy Cost Optimiser (tariff category check, power factor, demand charges, TOD, open access options; savings estimate ranges; **energy manager decides**) - B - business owner
103. Fuel & Gas Safety Coach (LPG handling, leak checks, regulator inspection due dates, emergency numbers; plain language) - A - household
104. Subsidy & Scheme Finder for Energy (LPG, solar, pumps, efficiency, EV incentives) - A - citizen
105. EV Ownership Planner (total cost of ownership, home charger installation checklist, tariffs, battery care) - A - EV buyer
106. Power-cut Survival Planner (inverter/battery sizing, critical loads list, generator safety, medical-device backup cautions) - A/B - household

### 9. Water & wastewater utilities  [W]
107. Water Utility Operations Assistant (supply schedules, pumping logs, leakage reports, tanker allocation; **engineers operate**) - A/B - water engineer
108. Non-revenue Water Analyst (DMA balance, night flow analysis, meter errors, leak hotspot leads; field verification) - B - NRW engineer
109. Water Quality Monitoring Assistant (lab results register, chlorine residual logs, standards limit checks, alert drafts; **water quality officer decides actions**) - B - quality officer
110. Wastewater Plant Operations Assistant (process logs, effluent compliance, sludge handling, energy use; **operators control**) - B - plant operator
111. Water Billing & Customer Desk (connection requests, meter readings, bills, complaints, leak reports; multilingual) - A - water utility
112. Stormwater & Flood Response Planner (rainfall data, drain capacity, pump station readiness, complaint hotspots; **municipal engineers decide**) - B - drainage engineer
113. Rural Water Scheme Assistant (hand-pump/borewell status, user committees, O&M funds, water-quality tests) - A - panchayat engineer
114. Irrigation Canal Scheduler (release schedules, tail-end equity checks, farmer notifications; cross-ref agriculture) - B - irrigation engineer

### 10. Regulators, policy, education & ecosystem  [X]
115. Tariff Order Analyst (regulatory orders, tariff schedules comparisons across states, impact calculators; sources cited) - A - analyst
116. Regulatory Commission Case Assistant (petition intake, document index, hearing schedule, issue lists, draft orders for commission staff; **commission decides**) - B - commission secretariat
117. Energy Data & Statistics Publisher (supply, demand, capacity, emissions dashboards from official data; definitions and caveats) - A - data office
118. Policy Impact Assessor (scenario modelling of subsidies, carbon price, renewable targets; pylab; assumptions listed) - B - policy analyst
119. Energy Safety Inspector's Assistant (inspection checklists, installation certificate records, accident statistics; **electrical inspector certifies**) - B - electrical inspectorate
120. Energy Skills Trainer (electrician, lineman, solar technician, safety, meter reading; voice and video in local language; practicals under instructors) - A - training institute
121. Energy Engineering Tutor (power systems, machines, thermodynamics, renewables; Prayogshala labs; Guru Sahayak) - A - student
122. Climate & Emissions Reporter (scope 1/2 inventories, emission factors with sources, verification trail; **verifier signs**) - B - sustainability lead
123. Just-transition & Community Engagement Planner (coal region livelihoods, retraining, local consultations summaries) - B - planner
124. Energy Startup Founder Copilot (idea validation, regulatory map, pilot partners, grants, safety/licensing path) - A/B - founder
125. Critical Infrastructure Resilience Planner (hazard maps, interdependency checks, restoration priorities, drills; **authorities decide**) - B - resilience lead

## NEVER an AI Employee (tier C)
Operate, switch, trip or reclose equipment; change protection settings, setpoints, interlocks or relay logic; issue or cancel permits-to-work, lockouts or de-energisation declarations; energise a connection or declare equipment safe; dispatch generation, shed load or
black-start the grid; open or shut pipeline, valve or gas isolation without an authorised operator; sign inspection, safety, calibration or compliance certificates as the competent person; submit regulatory filings, bids on an exchange or market trades as the
licensed participant; disconnect a consumer outside regulation and human sign-off; give trading or investment advice; write to SCADA/EMS/DCS or any control network; handle explosives or hazardous materials; accuse a consumer of theft; scrape utility or exchange portals against terms.

## Suggested build order
1. **Wave 1 - consumer-side and small business (tier A, no grid risk)**: 96-101, 103-106, 72, 74, 76, 87, 63, 64, 71 (extend `solar_check`), 102.
2. **Wave 2 - utility and installer back-office with an engineer in the loop**: 31, 33-35, 37, 43, 45, 46, 51, 73, 75, 80, 86, 88-92, 107, 111, 115, 119.
3. **Wave 3 - plant, grid, pipeline and market roles (OT-adjacent, read-only, strict audit)**: 1-6, 18-30, 32, 36, 38, 47-49, 53, 57-62, 65, 108-110, 118 - need licensed engineers, certified gateways and regulator-aware governance.
Fit to Hoola: department **"Energy & Utilities"**; Hoola already has **solar_check**, the **Ghar/Home Assistant** layer (read-only by default; gated controls), the ISP-NOC alarm-correlation pattern (reusable for substations and plants), the Engineering Desk, Maps, pylab and the research engine. Wave 1 is a **household and small-business "Bijli Sahayak"**
that explains bills, tracks outages and complaints, guides solar and EV decisions, and monitors home energy. Reuse WhatsApp/voice in local languages, Khata/PAISA, `appmaker` (installer and field-crew apps with shift-only location), HYPERFRAMES (customer education), approval cards for every filing, bid,
subsidy application and payment, and the inherited OT rule: **read-only and audited, never a path to controls**.
**Best first pilots**: (a) a **rooftop-solar installer** (71-76) - leads, proposals using `solar_check`, subsidy paperwork, project tracking, Khata; (b) **household Bijli Sahayak** (96-101) with Ghar read-only monitoring; (c) a **petrol pump or LPG distributor** (63, 64) - daily reconciliation and compliance calendars;
(d) a **small discom or mini-grid operator** later (31-35, 37, 83). Large generators, grid operators and refineries come last: OT security, safety cases and procurement are heavy.

## Open questions for the owner
- Which side first: **households**, **rooftop-solar installers**, **fuel/LPG dealers**, **small utilities and mini-grids**, **EV charging**, or **large plants and grid operators**? I'd start with households + solar installers because `solar_check` and Ghar exist.
- Data sources: tariff orders, CERC/SERC data, exchange prices, discom bill formats and solar subsidy portals; which official sources and APIs are available, and will discoms provide consumer-data access (smart meters) with consent?
- OT boundary: confirm Hoola stays read-only on SCADA/DCS exports and never writes to control systems, and that any future control gateway is built by a licensed integrator with human confirmation.
- Safety posture: confirm electrical-safety guidance to consumers is limited to "call a licensed electrician/discom" for anything beyond basic tips, and that no AI instruction leads a person to touch live equipment.
- Which states first? Tariffs, net-metering caps, subsidies and rules vary; each is a maintained data pack with dated sources.
- "GO per field" turns any field into a sourced report with the Electricity Act, CERC/SERC regulations, CEA safety rules, PNGRB, PESO and BEE rules checked on primary text.
