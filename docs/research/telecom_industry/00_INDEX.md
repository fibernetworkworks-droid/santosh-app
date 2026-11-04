# The telecom industry across the world - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A TELECOM INDUSTRY AI EMPLOYEES"*. Sixteenth in the series. Telecom here means: mobile operators (MNO/MVNO),
fixed broadband and fibre (FTTH, cable, LCO/ISP), enterprise connectivity and managed networks, tower and passive infrastructure, data
centres and cloud-edge, submarine cables and satellite, network equipment vendors, OSS/BSS software, IoT/M2M connectivity, messaging and
voice platforms (CPaaS, A2P SMS), and the regulators, retailers and installers around them. Newtika's own roots are in this industry
(the repo owner is Fibernetworkworks / FNW), which makes it the most natural pilot in the whole series.

**9 fields, 108 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Rules and standards
  named are from memory and **must be re-checked on primary text per country** before any desk is built: in India the Telecommunications
  Act 2023 and the rules made under it, DoT licence conditions (Unified Licence incl. ISP category), TRAI regulations (quality of
  service, tariff reporting, MNP, unsolicited commercial communication / DLT, KYC and SIM issuance rules, customer-complaint redressal),
  Right-of-Way rules and the Gati Shakti sanchar portal, spectrum and tower norms (EMF limits), IPDR/log retention and lawful-interception
  duties, Sanchar Saathi / CEIR, PM-WANI, BharatNet, DPDP Act 2023; abroad ITU/3GPP/GSMA standards, FCC and Ofcom rules, ePrivacy/GDPR, EU
  NIS2 and the Cyber Resilience Act, net-neutrality rules, Open RAN specs, TM Forum frameworks (eTOM, SID, Open APIs).
- **Already in Hoola** (extend, do not rebuild): the `isp_noc` duty ("ISP network (NOC)": reads OLT alarms, finds the real fault, explains
  in plain words, files tickets to the right team; equipment changes only on her tap) with tools `noc` / `noc_dekho`, the `isp` front-desk
  kind ("Broadband / cable / LCO": plans and prices, area, new connection steps, router-restart checklist, support number; plan changes and
  discounts only on the owner's yes; technician number never given to the customer), the `cyber_security` / `cyber_analyst` roles (alerts,
  suspicious mail/link/file, incident notes; block/wipe on her tap), `it_helpdesk`, Maps (route matrix, fault-site distance), `fleet`
  (technician vehicles), Khata (subscriber dues), WhatsApp opt-in, `appmaker` (subscriber app, technician app with offline outbox, NAKSHA
  shift-only location), Data Desk + pylab (churn, capacity), the research engine, doc studio (installation forms, invoices), the PC Operator
  (vendor portals) and the PAISA gateway (recharge). Roles with `*` exist in some form. The Mera-PC freeze is untouched.

## The findings that shape every telecom desk
### 1. The licence belongs to the operator; the AI works inside the operator's duties, never over them
Ladder as before: **A** admin/prepare, **B** assist (diagnose / draft / plan for a named engineer), **C** reserved.
Reserved here: changing live network configuration or equipment without an engineer's tap (an AI can propose the change and a roll-back
plan; **configuration push is reserved**), spectrum or licence filings, lawful-interception and data-disclosure requests, SIM issuance /
KYC acceptance, subscriber disconnection for non-payment or fraud beyond policy, emergency-service routing changes, safety-critical
tower or fibre-splice work (a person climbs and splices), tariff changes, and any statement to a regulator as the licensee.
**The AI watches, diagnoses, plans and prepares; the NOC engineer, field technician and licensee act.**

### 2. Telecom runs on alarms, tickets and trucks: the exception workflow is the product
A network produces thousands of alarms; most are noise, a few are real; a fibre cut or an OLT outage affects thousands of customers within
minutes. The money is in **mean time to detect/repair, truck rolls avoided, churn avoided, and bills collected**. Correlating alarms to a
root cause, telling the right customers and the right crew, and keeping a clean record is exactly what a logged, rule-based employee does
best, with a human on every change.

### 3. Customers' pain is outage, speed, bills, SIM/KYC and spam
"Net nahi chal raha", "speed kam hai", "bill zyada aaya", "SIM block ho gayi", "spam calls", "porting problem", "recharge atka". A first-line
agent that diagnoses (router checks, outage lookup, line tests with the operator's tools) and escalates with a complete ticket resolves most calls
before a technician is sent; the rest go with the evidence attached. Fraud (SIM swap, OTP theft, fake KYC) is the grievous harm: **never ask
for or store OTP/PIN**, never disclose account data without verified identity.

### 4. Infrastructure is physical, regulated and shared
Fibre routes, ducts, poles, towers, power, batteries, shelters, right-of-way permits, landowner agreements, EMF compliance, and shared
infrastructure between operators. Records (asset registers, route maps, splice diagrams, permit trackers) are tier A and the biggest
quiet cost saver; field work stays human and safety-first (heights, roads, live power).

### 5. Security and resilience are national issues
Networks are critical infrastructure; threats include DDoS, BGP hijacks, SS7/Diameter abuse, SIM-box fraud, insider access, supply-chain risks.
The AI helps with monitoring and drills but any containment action (blocking, rerouting, blacklisting) needs an authorised engineer and an audit trail.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [M] mobile operator/MVNO, [B] broadband/fibre/cable/ISP/LCO, [E] enterprise/managed services, [I] infrastructure (tower, data centre, cable), [V] vendor/software, [R] regulator/policy.

### 1. Network planning, design & engineering
1. [B] FTTH Route Planner - routes along roads/poles/ducts from Maps and the user's survey, splitter ratios, OLT placement, drop lengths, BOM and cost; **engineer approves** - B - network planner
2. [M] RF Planner's Assistant - coverage prediction inputs, site candidates, propagation parameters, drive-test summaries; clearly "model estimates, not guarantees" - B - RF engineer
3. [B] Capacity & Oversubscription Planner - port and uplink utilisation, growth forecasts, upgrade triggers (pylab) - B - network planner
4. [M] Spectrum & Interference Analyst - band plans, neighbour lists, interference flags from measurements; licence-filing prep by the regulatory team - B - spectrum engineer
5. [I] Site Acquisition & Tower Siting Assistant - candidate locations, landowner checks, local permits list, EMF compliance prerequisites, access roads (Maps) - A - site acquisition manager
6. [I] Right-of-Way Permit Tracker - authority approvals, fees, restoration deposits, route clearances, deadlines (Gati Shakti / state portals on the user's tap) - A - RoW manager
7. [M/B] Transport & Backhaul Planner (microwave, fibre, leased lines, protection paths, latency budgets) - B - transport engineer
8. [E] SD-WAN & Enterprise Network Designer's Assistant (site lists, links, SLAs, QoS policy drafts, BOQ) - B - solutions architect
9. [I] Data-centre Capacity Planner (power, cooling, racks, cross-connects, tenants) - B - facility manager
10. [I] Subsea & Long-haul Route Risk Assistant (route surveys, hazards, landing-station permits, repair-ship scheduling) - B - cable project manager
11. [M] Small-cell, DAS & In-building Planner (venues, indoor maps, hardware lists) - B - RF engineer
12. [V] Network Design Documentation Assistant (HLD/LLD templates, naming conventions, IP/VLAN plans, diagram consistency checks) - A - network architect
13. [B/M] IP Address & Resource Manager (IPv4/IPv6 allocations, ASN, route objects, RPKI reminders; changes by engineers) - A/B - network engineer
14. [R] Network Rollout Tracker for Government Schemes (BharatNet-type projects: village connectivity, uptime reports, claims evidence) - A - project manager

### 2. Fibre construction, installation & field operations
15. [B] Fibre Rollout Project Manager's Assistant (daily progress, trenching metres, joint-box counts, vendor teams, material consumption, photo evidence; links to Construction register) - A - rollout manager
16. [B] Splice & OTDR Records Keeper (splice loss, OTDR traces, test sheets, as-built route and splice diagrams; **acceptance by supervisor**) - A/B - field supervisor
17. [B] Installation Scheduler (new connection slots, technician skills, route and travel time (Maps), customer confirmations) - A - field-ops head
18. [B] Technician Helper App (voice/photo checklists: ONT setup, signal levels, Wi-Fi survey, customer sign-off, offline sync; location on shift only) - A - technician
19. [B] Truck-roll Avoider (remote diagnosis first: ONT status, light levels, line tests via vendor tools; sends technician only when needed) - B - field-ops head
20. [B/M] Field Workforce Manager (shift planning, skills, safety training validity, vehicle assignment, overtime; welfare checks) - A - ops manager
21. [B] Inventory & Drop-cable Stores Assistant (ONTs, routers, fibre drums, connectors; serial tracking, returns, theft flags) - A - store in-charge
22. [B] Subcontractor Manager (rates, work orders, measurement, payment on completion, quality claims; Theka-style) - A - contractor manager
23. [I] Tower Maintenance Scheduler (preventive visits, climber safety certificates, battery/DG fuel, rectifier checks, spares) - A - tower ops
24. [I] Tower Safety Compliance Assistant (climber training, harness inspections, incident logs; **work permits by supervisor**) - B - safety officer
25. [B/M] Fault-site Logistics Planner (crew, tools, splice kits, traffic permits, restoration time estimate) - A - NOC / field ops

### 3. Network operations centre: monitoring, faults, assurance  (extends `isp_noc`)
26. * ISP NOC Assistant (existing) - OLT alarm reading, real-fault finding, plain-words summary, correct team ticket; equipment changes only on tap - A/B - NOC engineer
27. [M/B] Alarm Correlator (groups alarms by topology and time, suppresses downstream noise, highlights probable root cause with evidence; ranks by customers affected) - B - NOC engineer
28. [B] Outage Communicator (affected customers by cable/OLT/feeder; ETA messages in local languages, status page, WhatsApp opt-in; honest "estimated") - A - NOC / customer care
29. [M/B] Fault Ticket Manager (assignment, SLA clocks, escalation ladder, vendor RMA, closure checks) - A - NOC manager
30. [M/B] Performance Monitoring Analyst (latency, loss, jitter, throughput, utilisation, error counters; baselines and anomalies; ranges, not certainties) - B - performance engineer
31. [M] Customer-experience Analytics (call drops, throughput per cell, app-level quality, complaint heatmaps; geo layers via Maps) - A - CX/network analytics
32. [B/M] Fibre-cut Locator Assistant (OTDR distance to map position, nearest handholes/poles, crew dispatch suggestion; **crew confirms on site**) - B - NOC engineer
33. [M/B] Change-management Assistant (maintenance windows, impact analysis, rollback plans, approvals, post-change checks; **configuration push by engineer**) - B - change manager
34. [M/B] Configuration Compliance Checker (golden configs, drift detection, vendor security baselines, audit logs) - B - network engineer
35. [B] Router & ONT Fleet Manager (firmware versions, vulnerabilities, staged rollouts, rollback; **rollout approval by engineer**) - B - CPE manager
36. [M/B] Power & Battery Monitor (site power alarms, DG fuel, battery health, outage forecast with grid data) - A - infrastructure ops
37. [M/B] Disaster & Resilience Planner (flood/cyclone/earthquake readiness, restoration priority list, emergency roaming/hotspot plans, critical customers list) - B - resilience manager
38. [M/B] Root-cause Analysis Writer (post-incident reports, timeline, contributing factors, corrective actions; **blameless, engineer-owned**) - B - service-assurance lead
39. [M/B] Network Automation Assistant (runbook execution in sandbox mode, pre-checks, dry-run diffs; **production changes only on tap**) - B - automation engineer

### 4. Customer care, sales & retail  (extends `isp` front desk)
40. * ISP Front Desk (existing) - plans, areas, new-connection steps, router-restart checklist, ticket; discounts only on owner's yes - A - ISP owner / support manager
41. [M/B] Customer Support Agent (voice/WhatsApp/web: outage lookup, bill explanation, plan change request, speed test guidance, tech visit booking; verified-identity rules; escalates) - A - contact-centre head
42. [M/B] Speed & Wi-Fi Troubleshooter (guided steps, placement, channel, interference, device checks; sends diagnostic data to the ticket) - A - support
43. [M/B] Billing Explainer (itemised charges, taxes, prorations, usage, credit notes; dispute steps) - A - billing support
44. [M/B] Plan Advisor (usage-based recommendations, fair comparison with current plan and honest limits (fair-use, throttling), no mis-selling; **plan changes need the customer's consent**) - B - sales / customer
45. [M/B] New-connection Sales Assistant (serviceability check by address, documents, installation estimate, KYC checklist, e-sign; **KYC accept by operator**) - A - sales
46. [M] SIM, eSIM & Porting Assistant (MNP steps, UPC, KYC re-verification, eSIM activation; **operator completes**) - B - retail / customer
47. [M/B] Churn Predictor & Retention Offerer (signals: tickets, usage drops, bill shock; explainable; offers within policy; no dark patterns; **offers approved by retention manager**) - B - retention head
48. [M/B] Collections & Dunning Assistant (reminders by due date, language, grace period, payment links (PAISA), regulatory disconnect rules; hardship routing; no harassment) - A/B - collections head
49. [M/B] Complaint & Regulator Escalation Handler (SLA, appellate authority steps, TRAI/DoT/consumer-forum cases; **responses by officers**) - A/B - nodal officer
50. [M/B] Retail Store & Franchise Assistant (stock, SIM/ONT, activation logs, commission, audits; fraud flags) - A - store manager
51. [M/B] Subscriber App & Self-care Builder (usage, bills, tickets, speed test, recharge; appmaker) - A - product
52. [B] Local Cable/ISP Owner Copilot (LCO: subscriber ledger, collection agents, renewals, complaints, cable-route issues, GST, Khata; lives in WhatsApp) - A - LCO owner
53. [M/B] Senior & Accessibility Care Agent (slow voice, large text, family-assisted support, assistive devices info) - A - customer care
54. [M/B] Multilingual Voice Agent (Hindi, Marathi, Tamil, etc. for IVR replacement, call summaries, handoff context) - A - contact-centre head
55. [M/B] Quality Coach for Agents (call review samples, empathy and accuracy rubric, coaching notes; not punitive scores) - B - team leader

### 5. Billing, revenue assurance, finance & OSS/BSS
56. [M/B] Rating & Billing Verifier (usage records vs tariff, free-unit logic, discounts, taxes; discrepancy samples) - A/B - billing ops
57. [M/B] Revenue Assurance Analyst (leakage: unbilled usage, wrong tariffs, SIM-box bypass, partner settlement gaps; flags with evidence) - B - revenue assurance head
58. [M] Roaming & Interconnect Settlement Assistant (TAP/RAP files, IOT rates, dispute packs; **settlement signed by finance**) - B - wholesale finance
59. [M/B] Partner & Reseller Commission Calculator (distributors, retailers, channel partners; plans, targets, clawbacks) - A - channel finance
60. [M/B] AR/AP & Collections Reconciler (receivables ageing, bank matching, bad-debt provision data; Khata, Tally) - A - finance
61. [M/B] Tariff & Product Catalogue Manager (plans, bundles, promotions, validity, regulatory tariff filings data; **filings by regulatory team**) - A/B - product manager
62. [M/B] Tariff-impact Simulator (price moves on ARPU, churn, revenue; scenario ranges via pylab) - B - pricing manager
63. [V] BSS/OSS Implementation Assistant (requirements, data migration mapping, test scripts, cutover checklists) - A - project lead
64. [M/B] Inventory & Asset Register Keeper (network elements, serials, locations, warranties, depreciation feeds) - A - OSS admin
65. [M/B] Network Cost Allocation Analyst (cost to serve by route/site/customer, opex vs capex, power costs) - A - finance + network

### 6. Security, fraud, trust & regulatory compliance
66. [M/B] Fraud Detection Assistant (SIM swap patterns, subscription fraud, SIM-box, IRSF, wangiri, spam-call farms; explainable rules, alerts to analysts; **block by fraud team**) - B - fraud analyst
67. [M/B] SIM Swap & Account-takeover Guard (extra verification steps, cooling periods, customer alerts; **never asks OTP in chat**) - B - security team
68. [M/B] Spam & Scam-call Filter Assistant (DLT consent and template checks, complaint ingestion, number reputation signals; regulatory action by the compliance team) - B - compliance
69. [M/B] DLT / Commercial-communication Compliance Assistant (header and template registration support, content-category checks, opt-in evidence; **registration by sender**) - A/B - messaging compliance
70. [M/B] Lawful-interception & Disclosure Request Tracker (log, validity checks of orders, deadlines, minimum-necessary views; **execution by authorised nodal officer**) - A - compliance / legal
71. [M/B] Data-retention & Log Manager (IPDR/CDR retention periods, secure deletion, access audit; privacy requests) - A/B - DPO
72. [M/B] Cybersecurity Watcher (DDoS patterns, BGP anomalies, vulnerable CPE, credential stuffing; containment proposals; **action by security engineer**) - B - CISO
73. [M/B] Network Security Configuration Auditor (SS7/Diameter firewall rules, management-plane exposure, privilege use) - B - security engineer
74. [M/B] EMF & Radiation Compliance Tracker (site measurements, limits, certificates, public queries with factual answers) - A - compliance
75. [M/B] Regulatory Return & KPI Preparer (QoS parameters, tariff reports, subscriber data, financial returns; **submission by authorised officer**) - A/B - regulatory affairs
76. [M/B] Licence & Authorisation Tracker (licence fees, renewals, compliance conditions, audit schedules, bank guarantees) - A - regulatory head
77. [M/B] Emergency-service & Public-safety Readiness Checker (112 routing tests, location accuracy reports; **changes by engineers**) - B - public-safety lead
78. [M/B] Child-safety & Content Blocking Order Handler (court/DoT blocking orders: intake, implementation checklist, audit; **implementation by authorised engineer**) - B - legal / NOC
79. [M/B] Privacy & Consent Manager (marketing consents, DND preferences, data-sharing, DPDP rights requests) - A - DPO
80. [M/B] Insider Risk & Access Reviewer (privileged access, unusual queries on subscriber data, joiner-mover-leaver) - B - security

### 7. Enterprise, IoT, cloud & digital services
81. [E] Enterprise Solutions Assistant (RFP response drafting from the product library, BOQ, SLAs, risk matrix; **bid approvals by commercial head**) - B - presales
82. [E] SLA Monitoring & Credit Calculator (uptime, latency, MTTR vs contract; credit statements) - A - service delivery manager
83. [E] Managed-service Desk (tickets for customers' sites, CPE visibility, change requests, monthly service reports) - A - service desk
84. [E] Leased-line & Internet-leased-circuit Order Manager (feasibility, delivery milestones, site surveys, cutover, billing start) - A - provisioning
85. [E] IoT Connectivity Manager (SIM fleets, usage pooling, anomalies, remote SIM actions on the owner's tap, device onboarding) - A/B - IoT product manager
86. [E] IoT Solutions Planner (use-case to connectivity choice: LoRaWAN, NB-IoT, LTE-M, 5G, Wi-Fi; coverage and cost; battery life math) - B - solutions architect
87. [E] CPaaS / Messaging Platform Assistant (SMS/WhatsApp/voice APIs, throughput, deliverability, compliance headers, billing; official routes only) - A/B - platform team
88. [E] Cloud & Edge Interconnect Planner (cross-connects, latency to clouds/IXPs, routing policy suggestions; **engineer applies**) - B - network architect
89. [E] Smart-city & Campus Network Assistant (public Wi-Fi/PM-WANI, CCTV backhaul, sensors; privacy review) - B - project architect
90. [E] Private 4G/5G Planner (industrial sites, spectrum options, device lists, SLAs) - B - solutions architect

### 8. Satellite, submarine, broadcast & emerging connectivity
91. [I] Satellite Terminal Support Assistant (LEO/VSAT/GEO user setup, dish alignment guidance, obstruction checks via photos, troubleshooting; **installation by qualified installer where needed**) - A/B - support / installer
92. [I] Satellite Capacity & Link-budget Assistant (rain fade, elevation, EIRP, margin tables via pylab) - B - satellite engineer
93. [I] Submarine Cable Operations Assistant (fault tickets, repair-ship schedules, capacity leases, consortium accounting) - A - cable ops
94. [I] Broadcast & Cable TV Operations Assistant (headend logs, channel packages, set-top inventory, subscriber billing; copyright/ carriage rules) - A - cable operator
95. [I] Rural & Last-mile Connectivity Planner (PM-WANI hotspots, BharatNet node usage, solar/battery sites, community entrepreneurs) - B - project lead
96. [V] Open-RAN & Network-vendor Integration Assistant (interface specs, test cases, interop reports) - B - integration engineer
97. [V] Network Equipment Vendor Support Assistant (RMA, firmware advisories, entitlement, docs search with citations) - A - TAC engineer
98. [R] Spectrum Auction & Licensing Analyst (valuation scenarios, coverage obligations, bidder rules; **bids by the licensee**) - B - regulatory strategist

### 9. People, learning, procurement & company functions
99. [M/B] Telecom Field Skills Trainer (fibre splicing basics, ONT config, safety at height, customer handling; voice/video in local languages; practicals under instructors) - A - training head
100. [M/B] Network Engineer Tutor (TCP/IP, optical, RF, 5G core; certifications Prep; Guru Sahayak) - A - learner
101. [M/B] Procurement & Vendor Manager (RFQs, vendor scorecards, import duties, warranty, lead times; **PO approval by authorised signatory**) - A - procurement
102. [M/B] Supply-chain Planner for Network Material (stock levels, lead times, forecast by rollout plan) - A - supply-chain head
103. [M/B] HR & Contract-labour Compliance Assistant (field crews, ESI/PF, licences, working-at-height certificates) - A - HR
104. [M/B] Finance & Capex Planner (build cases, payback per route/site, depreciation, funding schedule; pylab) - A - CFO
105. [M/B] Sustainability & Energy Reporter (power use, renewable share, e-waste, emissions per bit; evidence and uncertainty) - A/B - ESG lead
106. [M/B] Board & Investor Reporting Assistant (KPIs: ARPU, churn, capex, coverage, EBITDA; footnotes and sources) - A - IR / finance
107. [M/B] Startup / Small-ISP Founder Copilot (licence path, equipment choice, business plan, capex, subscriber ramp, compliance map, vendor shortlist) - A/B - founder
108. [R] Policy Analyst for Telecom (rollout, affordability, digital-divide data, regulatory impact; sources) - B - think-tank / regulator

## NEVER an AI Employee (tier C)
Push configuration to a live network, upgrade firmware fleet-wide, reroute or block traffic, or shut down a service without an
authorised engineer's confirmation; climb a tower, splice or work near live power (humans only); accept or reject SIM/KYC; issue, port
or swap a SIM; disconnect a subscriber outside the written policy; disclose subscriber data, call records or location to any requester
outside a validated lawful order handled by the nodal officer; ask for or store OTP/PIN/passwords; file or sign regulatory returns,
spectrum bids, licence applications or tariff filings as the licensee; change emergency-service routing; target subscribers with
dark-pattern retention or unsolicited marketing against DND/DLT rules; scrape competitor or vendor portals against terms.

## Suggested build order
1. **Wave 1 - small ISP and LCO operations (tier A, extends what exists)**: extend 26 and 40 with 17, 18, 21, 28, 29, 42, 43, 45, 48, 51, 52, 15, 22, 64.
2. **Wave 2 - network assurance with an engineer in the loop**: 1, 3, 16, 19, 27, 30, 32, 33, 35, 38, 41, 44, 47, 49, 56, 60, 66, 75.
3. **Wave 3 - regulated or high-impact**: 33, 34, 39 (automation), 57, 67-73, 77, 78, 85-87 - need licensed engineers, audit trails, strict caps.
Fit to Hoola: department **"Telecom & Connectivity"**. Hoola already has an ISP network (NOC) duty, the `isp` front desk and the cyber roles, built from
the owner's own world, so Wave 1 is the **most mature starting point in the whole series**: a **complete employee suite for a local ISP/LCO** (owner
copilot + NOC assistant + support agent + billing/collections + technician app + stores + subscriber app). Reuse Maps (1, 17, 25, 32), fleet
(technician vehicles), Khata (48, 52, 60), PAISA (recharge, dues), `appmaker` (subscriber and technician apps with offline outbox and NAKSHA shift location),
WhatsApp opt-in (28, 48), pylab (3, 62, 92), research engine (108), approval cards for every configuration, disconnection, discount and filing,
vendor-portal PC Operator on her tap, and Hoola's **audit trail + caps + kill switches** as the compliance proof.
**Best first pilot: a local ISP / cable LCO with 500-20,000 subscribers** (the owner's own FNW network is the natural first customer and design partner):
daily pains - outages, collections, installations, support calls, router stock. Then a fibre contractor, then regional ISPs; mobile operators and tower
companies later (heavy security, vendor integrations, regulatory sign-off).

## Open questions for the owner
- Which seat first: **local ISP / LCO** (your own network, fastest), **fibre rollout contractors**, **regional ISPs/MSOs**, **enterprise connectivity**, or **mobile
  operators/tower cos**? I'd start with the ISP/LCO suite and use FNW as the design partner.
- Equipment access: which NMS/OLT vendors does FNW use (Huawei/ZTE/Nokia/VSOL/others)? Official APIs, SNMP/TL1/NETCONF with read-first and change-on-tap,
  or vendor portals? That decides how deep the NOC assistant can go safely.
- Customer data: subscriber records, call/IPDR logs and KYC are regulated; confirm retention, access roles and lawful-request handling before any
  data-heavy employee ships.
- Field safety: confirm technician location is shift-only with consent, and that no AI instruction ever sends a person to a hazardous task without a
  supervisor's approval.
- "GO per field" turns any field into a sourced report with the Telecommunications Act 2023, DoT licence terms and TRAI regulations checked on primary text.
