# The logistics industry, function by function - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A LOGISTICS INDUSTRY AI EMPLOYEE LIST"*. Tenth in the series (healthcare family x7, construction,
real estate, now logistics). Logistics = moving and storing goods: road, rail, air, sea, inland waterways, courier/express,
last-mile, warehousing, cold chain, freight forwarding, customs, 3PL/4PL, e-commerce fulfilment, reverse logistics,
and the shippers/consignees who buy it.

**11 fields, 117 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo for this industry: the register is **domain
  knowledge, not sourced**. Rules named are from memory and **must be re-checked on primary text** before any desk is built:
  Motor Vehicles Act 1988 and Central Motor Vehicles Rules (permits, fitness, axle load, dangerous goods, driver licence),
  Carriage by Road Act 2007 (consignment note, carrier liability), GST e-way bill rules and e-invoice thresholds,
  FASTag / toll rules, AIS-140 vehicle tracking, Motor Transport Workers Act, Customs Act and ICEGATE filings, DGFT / IEC,
  IATA Dangerous Goods Regulations (air), IMDG Code (sea), Merchant Shipping and port rules, Railways Act and FOIS, the
  National Logistics Policy 2022 / ULIP / PM Gati Shakti, ONDC logistics protocol, FSSAI / pharma cold-chain norms, drug
  GDP rules. Abroad: FMCSA hours-of-service (US), CMR / ADR (EU), C-TPAT, Incoterms 2020, Hague-Visby / Rotterdam rules.
- **Already in Hoola** (extend, do not rebuild): `warehouse_manager` ("Godown": bin-wise stock, GRN, pick list, cycle count),
  `fleet_manager` ("Fleet / gaadiyan": vehicle papers and reminders, diesel/average, service, tyres, trips, loads),
  `courier_desk` ("Courier Sahayak": parcel booking on her tap, tracking, NDR), `logistics_coordinator` (shipments, LR /
  challan, e-way bill prep, tracking), plus `supply_opt` (enterprise supply-chain optimisation with reorder/dead-stock sums)
  and server modules `fleet`, `courier`, `logistics`. Engine pieces: Maps (route matrix, geocoding, `maps_nearest`,
  `maps_route_plan` proposal), Khata (freight dues), WhatsApp opt-in, `appmaker` (driver/rider apps), Data Desk + pylab,
  Hoola's PC Operator (for portals), doc studio (LR, challan, packing list PDFs). Roles with `*` exist in some form.

## The findings that shape every logistics desk
### 1. The gates are the driver's licence, the vehicle's papers, the customs broker and the signature on a consignment note
Ladder as before: **A** admin/prepare, **B** assist (compute / check / draft for a named person), **C** reserved.
Reserved: assigning a driver to a trip as employer-of-record, certifying fitness or load safety, signing the LR / bill of
lading / airway bill as carrier, filing a customs entry (licensed customs broker, CHA), declaring dangerous goods (DGSA /
certified shipper), certifying a temperature chain release, paying duty or fines, insurance claim admission, and any
real-time vehicle or aircraft control. **The AI plans and prepares; the dispatcher, broker and driver act.**

### 2. Logistics is a thin-margin, exception-heavy, document-heavy business
Margin sits in: empty return trips, detention/demurrage, rejected deliveries, missing PODs, route deviations, fuel, toll,
damaged goods claims, mis-declared weight, payment delays. Most hours go to chasing status across WhatsApp, calls,
portals and Excel. Exception handling (where is the truck, why is it late, who is paying detention) is the product. All
tier A: very high value and no clinical-style risk.

### 3. Safety and driver welfare are the human limit
Fatigue, speeding, overload, night driving, lone-driver risk, hazardous cargo, and gig-rider heat/accidents. An AI that
proposes a schedule must obey hours-of-service, never push a driver, never penalise automatically, and keep a human in the
loop for incidents. Rider apps need consent and data minimisation (location only on shift, as Hoola's NAKSHA rule).

### 4. Data is fragmented; official channels beat scraping
Carriers' tracking, ports, customs, railways and portals vary by country. Hoola's rule: official APIs, carrier-provided
tracking links, ULIP/ONDC where available, EDI/webhooks from partners, and the user's own data. No unofficial scraping.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)

### 1. Shipper side: orders, planning & procurement of transport
1. Shipment Request Intake - order to shipment: origin, destination, weight/volume, dimensions, pickup window, special handling, declared value - A - logistics manager
2. * Logistics Coordinator (existing) - shipments, LR / challan, e-way bill prep, tracking, delay chase - A - logistics manager
3. Freight Rate Comparator - quotes from carriers/forwarders side by side (landed cost, transit, reliability), contract vs spot - A - procurement
4. Carrier Selection Assistant - scorecard (on-time %, damage rate, claims aging, capacity, compliance) applies shipper rules; **award by shipper** - B - transport manager
5. Freight RFQ & Tender Manager - tender documents, lane bundles, bid comparison, award scenarios (pylab) - B - head of transport
6. Transport Budget & Forecast Planner - lane volumes, seasonal peaks, rate trends, cost per kg/pallet/order - A - supply-chain head
7. Packaging & Cartonisation Advisor - box sizing, dimensional weight, pallet patterns, damage rate by pack type - B - packaging engineer
8. Shipment Consolidation Planner - combining orders into full-truck/container loads, milk-run routes, cut-off times - A - planner
9. Customer Delivery-promise Estimator - cut-offs, pincode serviceability, SLA windows, public holidays; honest "estimated, not guaranteed" - A - customer service
10. Insurance & Declared-value Advisor (cargo insurance options, exclusions, claim documents) - A/B - risk manager

### 2. Road freight: trucking, fleet & dispatch
11. * Fleet Manager (existing) - vehicle papers, expiry reminders (insurance, fitness, permit, PUC, tax), diesel/average, service, tyres - A - fleet owner
12. Trip Planner & Load Matcher - assigns loads to vehicles by capacity, location, legal hours, compatibility; **dispatch decision by the dispatcher** - B - dispatcher
13. Route Planner (Maps; truck-attributes aware where the data exists: height, weight, hazmat limits, toll plazas, ghat sections) - B - dispatcher
14. Empty-return (Backhaul) Finder - nearby loads from the owner's network and partner exchanges, within hours-of-service - A - fleet owner
15. Driver Hours & Rest Planner - tracks driving/rest, suggests legal stops; **never pushes beyond limits** - B - dispatcher
16. Driver Onboarding & Documents Desk (licence validity, badge, medical, police verification, training dates) - A - HR / fleet
17. Driver Wage & Trip Settlement (per-km/per-trip, advances, tolls, fuel, tyre costs, deductions, bonus rules; pay on tap) - A - accounts
18. Toll & FASTag Reconciler (plaza list, charges vs trip, disputes) - A - fleet accounts
19. Fuel Monitoring Analyst (fuel card/tank data, mileage per trip vs norm, theft patterns; flags only) - B - fleet manager
20. Preventive Maintenance Scheduler (km/hour based, parts inventory, workshop jobs, downtime, tyre retread) - A - maintenance head
21. Vehicle Breakdown Responder (nearest mechanic/tow via Maps, cargo transfer plan, customer message) - A - dispatcher
22. Trailer, Container & Pallet Pool Tracker (location, utilisation, loss, repair) - A - asset manager
23. Detention & Waiting-time Auditor (gate-in/out stamps, free time, bills to customer) - A - commercial
24. Permit & Compliance Calendar (national/state permits, road tax, driver licence renewal, hazmat licence) - A - compliance officer
25. E-way Bill & E-invoice Preparer (data from invoice, Part A/B, vehicle update, extension reminders; **filing on the tax-registered user's tap**) - B - consignor / CA
26. LR / Consignment Note & POD Desk (prints LR, scans POD, matches to invoice, shortage/damage remarks) - A - branch manager
27. Freight Billing & Collection Assistant (rate cards, GST, detention, short-delivery deductions, aging; Khata) - A - accounts
28. Transport Marketplace / Broker Assistant (load-posting, truck-booking, advance and balance schedule, vehicle verification) - A - broker
29. Hazardous-goods Road Transport Checker (labels, TREM card, placards, driver training, route restrictions) - B - DG safety adviser

### 3. Last-mile, courier & e-commerce delivery
30. * Courier Desk (Courier Sahayak, existing) - booking on tap, tracking, NDR (non-delivery report) handling - A - shop owner
31. Pincode Serviceability & Rate Estimator (multi-carrier, COD, weight slabs) - A - merchant
32. Delivery Slot Scheduler (customer choices, capacity, rider load) - A - dispatch
33. Rider Dispatch Optimiser (batching, sequence, ETA with traffic, fairness across riders) - B - hub manager
34. NDR / RTO Reduction Assistant (customer call/WhatsApp scripts, address fix, reschedule; patterns of rejects) - A - merchant
35. COD Reconciler (collections vs remittances, mismatches, aging) - A - finance
36. Proof-of-delivery Collector (photo, OTP, signature; mismatch alerts) - A - hub manager
37. Address Quality Engine (parse, geocode, pincode fix, landmark capture, `maps_address_check` grading) - B - data team
38. Rider Welfare & Safety Assistant (heat alerts, shift limits, accident protocol, insurance claims help) - A/B - rider-ops head
39. Gig Rider Onboarding & Payout (KYC masked, vehicle docs, payouts per task, incentives) - A - rider-ops
40. Returns (Reverse Logistics) Coordinator (return reasons, pickup, QC, refurbish/resale/destroy decisions by rule) - A/B - returns manager
41. Hyperlocal Merchant Delivery Assistant (small shops: order to rider to customer; links to Bazar/ONDC) - A - shop owner
42. Parcel Locker & Pickup-point Manager - A - network ops

### 4. Warehousing, fulfilment & inventory
43. * Warehouse Manager (existing "Godown") - bin-wise stock, GRN, pick lists, cycle count, stock alerts - A - warehouse head
44. Inbound Dock Scheduler (appointments, gate pass, unloading crews) - A - warehouse head
45. Putaway & Slotting Optimiser (ABC velocity, bin size, pick path) - B - warehouse head
46. Wave & Batch Picking Planner (orders, SKUs, zones, packers; pylab simulations) - B - ops manager
47. Packing Station Assistant (carton choice, weight check, label print, inserts) - A - packing lead
48. Cycle-count & Inventory Reconciliation Analyst (variances by cause, shrinkage patterns) - B - inventory control
49. FEFO/Expiry Manager (batch, expiry, quarantine rules, near-expiry markdowns) - A - quality + ops
50. Warehouse Labour Planner (shifts, headcount per forecast, productivity, overtime) - A - ops manager
51. Warehouse Safety & Audit Assistant (fire, racking inspections, forklift certification, incident logs) - A/B - safety officer
52. Cross-dock & Transshipment Coordinator - A - hub ops
53. Dark-store / Quick-commerce Slotting Assistant (small-assortment fast-turn rules) - B - category + ops
54. 3PL Billing Engine (storage, handling, value-added, pallet-days, minimums; invoice proofs) - A - 3PL finance
55. WMS Implementation Analyst (requirements, process maps, test scripts, master data load checks) - A - project lead
56. Inventory Visibility Reporter (multi-warehouse position, in-transit, allocated, free; for ERP `supply_opt`) - A - supply planner

### 5. Cold chain & special cargo
57. Cold-chain Monitor (sensor/logger feeds for reefers and cold rooms, excursion alerts, evidence pack; **product disposition by QA**) - B - quality head
58. Pharma GDP Compliance Assistant (SOP evidence, qualification records, mapping studies, deviations) - B - responsible person (PH#41)
59. Perishables Route & Shelf-life Planner (transit time vs shelf life, crossing legs) - B - fresh-supply planner
60. Reefer Container Pre-trip & Power Monitor (genset fuel, setpoints, alarms) - B - reefer ops
61. Hazmat / DG Documentation Preparer (SDS, UN number, packing group, shipper's declaration drafts; **declaration by certified shipper**) - B - DG safety adviser
62. Oversize / Project Cargo Planner (route survey data, permits list, escort plan, lifting equipment) - B - project logistics head
63. Livestock, Valuables & Art Transport Checker (special-licence lists, insurance, chain-of-custody) - A/B - specialist
64. Battery & E-waste Logistics Checker (lithium-battery classification, packaging rules, EPR documentation) - B - DG adviser

### 6. Freight forwarding, customs & international trade
65. Freight Forwarder's Booking Assistant (quote to booking to cut-offs to documentation across sea/air/road legs) - A - forwarder
66. Incoterms Advisor (who pays/risks what at each point; contract wording checks) - B - trade lawyer / forwarder
67. HS Code Classifier (suggestions with rationale and rulings; **classification by the importer/CHA**) - B - customs broker
68. Customs Documentation Preparer (invoice, packing list, BoL/AWB cross-checks, Shipping Bill / Bill of Entry data sheets; **filing by licensed CHA**) - B - CHA
69. Duty & Landed-cost Calculator (BCD, IGST, cess, exemptions, FTA benefits with rules shown; pylab) - A - importer
70. Export Incentive Tracker (RoDTEP, drawback, advance authorisation obligations, deadlines) - A/B - export manager
71. Letter-of-Credit Document Checker (UCP 600 style discrepancies list; **bank decides**) - B - trade finance officer
72. Sanctions & Restricted-party Screener (names, vessels, ports, end-use flags; **clearance by compliance**) - B - compliance officer
73. Origin Certificate & FTA Rules Assistant (rules-of-origin tests, supplier declarations, certificate packets) - B - trade compliance
74. Shipping Line / Airline Schedule Tracker (via official carrier tracking), delay & rollover alerts - A - forwarder
75. Container Demurrage & Detention Controller (free-time clocks, extension requests, dispute packets) - A - forwarder / importer
76. Bill-of-Lading / AWB Draft Checker (consignee, notify, marks, weight, charges; carrier/forwarder issues the final) - B - documentation team
77. Port & Terminal Slot Coordinator (gate slots, truck appointments, congestion alerts) - A - port-ops
78. Customs Query & Notice Responder (drafts replies; **submission by CHA/importer**) - B - customs broker
79. Trade-compliance Calendar (IEC renewal, bond expiries, export obligations, advance authorisation) - A - compliance

### 7. Rail, air, sea & inland-water operations
80. Rail Freight Booking Assistant (FOIS/RMS-style indent steps, rake planning, siding schedules; filing by the user) - A - rail logistics manager
81. Air Cargo Booking & Load-planning Assistant (ULD building, DG acceptance checks, cut-offs) - B - airline cargo / forwarder
82. Ship Chartering Assistant (voyage estimates, laytime/demurrage calcs; **fixture by chartering manager**) - B - chartering manager
83. Port Call Coordinator (agent tasks, berth windows, bunkers, crew change docs) - A - ship agent
84. Cargo Stowage & Lashing Checker (planning aids against class rules; **master/ chief officer decides**) - B - ship planner
85. Inland Waterways / Coastal Shipping Planner (low-volume bulk, tide windows, route restrictions) - B - operator
86. Terminal Yard Optimiser (container stacking, crane sequences, gate flow) - B - terminal planner

### 8. Control tower, visibility & exception management
87. Control-tower Agent - single view of all shipments across modes, exceptions ranked by impact and time left - A - control-tower lead
88. ETA Predictor (historical lanes, traffic, weather, port congestion; shows range and confidence) - B - planner
89. Exception Resolver (delay, damage, short, wrong address, stuck at customs; suggests fixes and drafts messages) - B - ops manager
90. Customer Notification Agent (proactive WhatsApp/SMS/email, multilingual, opt-in) - A - customer service
91. Claims Handler (damage/loss/shortage packet: LR, POD, photos, survey, contract terms, liability calc; **admission and settlement human**) - B - claims manager
92. Cargo Insurance Claim Assistant - A/B - risk manager
93. Visibility Data Normaliser (carrier events, EDI, webhooks, ULIP/ONDC messages to one status model) - A - integration lead
94. Weather & Disruption Watcher (floods, strikes, port closures, border delays; reroute options) - A - control tower
95. Security & Theft-risk Analyst (route hot-spots, tamper alerts, seal numbers; incident response with police liaison) - B - security head

### 9. Planning, analytics & network design
96. Network Design Analyst (hub location, lane structure, make/buy transport; scenarios in pylab) - B - supply-chain head
97. Demand & Load Forecaster (orders to loads by lane and day) - A - planner
98. Transport Cost Analyst (cost-to-serve, fuel/toll share, leakage, benchmark per tonne-km) - A - finance + ops
99. Sustainability & Emissions Reporter (ton-km, emission factors, GLEC/ISO 14083 style; shows factors and uncertainty) - A/B - ESG lead
100. Electrification Planner (EV fleet pilot: range, charging, TCO) - B - fleet strategist
101. Safety Analytics (harsh events, accident causes, near-miss patterns; coaching prompts not penalties) - B - safety head
102. Fraud & Anomaly Detector (fake PODs, duplicate invoices, route deviations, collusion patterns; flags only) - B - audit
103. Carrier & Vendor Performance Reviewer (quarterly scorecards, improvement plans) - A - procurement

### 10. Finance, contracts, people & company functions
104. Freight Audit & Payment Assistant (invoice vs contract vs POD, duplicate/over-charge detection; **payment on approver's tap**) - A - finance
105. Transport Contract Manager (rate cards, SLAs, penalties, renewals, liability clauses) - A - legal / procurement
106. GST, TDS & Statutory Assistant for transporters (GTA/RCM rules, TDS on freight, e-invoicing thresholds) - B - CA
107. Working-capital & Freight-finance Assistant (invoice discounting, fuel advances, EMI calendar for vehicles) - A - owner
108. Labour & Compliance Desk for drivers and warehouse staff (wages, ESI/PF, shifts, rest, licences) - A - HR
109. Training Coach (driver safety, defensive driving, hazmat awareness, warehouse safety, local language voice) - A - training head
110. Small Transporter Business Coach (pricing per km/tonne, utilisation, cash cycle, taxes basics; no tax or legal advice) - A/B - owner / CA

### 11. Platform, government & ecosystem
111. Freight Marketplace Trust Agent (vehicle and owner verification, RC match, load-fraud flags, rating fairness) - B - platform trust
112. ULIP / ONDC Logistics Integration Assistant (message schemas, test payloads, certification checklist) - A/B - integration lead
113. Port Community / Customs Single-window Helper (documents readiness, status chase; filing by the registered user) - A - trade desk
114. Transport Department Services Assistant (permits, fitness, DL, tax; appointments and fees on user's tap) - A - fleet owner / driver
115. Logistics Park / Multi-modal Hub Planner (land, rail, road linkage, utilities, tenant mix) - B - planner
116. Public Logistics Dashboard Publisher (de-identified indicators, lead times, costs by corridor) - A - policy analyst
117. Student Tutor for Supply-chain & Logistics (courses, case studies, Incoterms, WMS basics; Guru Sahayak) - A - faculty

## NEVER an AI Employee (tier C)
Control a vehicle, vessel or aircraft; assign or schedule a driver beyond legal hours; sign an LR, bill of lading or airway bill
as carrier; file a customs entry, shipping bill or bill of entry; declare dangerous goods; release a temperature-excursion
batch; pay a fine, duty or freight on its own; admit or settle a claim; decide a customs classification dispute; impose
a rider/driver penalty automatically; open or tamper with a seal; track a person's location outside their shift; scrape
carrier/portal data against its terms.

## Suggested build order
1. **Wave 1 - exceptions, documents and money (tier A)**: extend existing 2, 11, 26, 30, 43 with 1, 3, 9, 17, 18, 23, 24, 27, 31, 34-36, 44, 48, 49, 87, 90, 104.
2. **Wave 2 - planning with a dispatcher in the loop**: 4, 8, 12-15, 25, 33, 37, 45, 46, 57, 59, 65, 69, 88, 89, 91.
3. **Wave 3 - international, DG and regulated corners (human-signed)**: 61, 62, 67, 68, 71, 72, 76, 78, 82, 84 - need a licensed CHA / DG adviser at the customer.
Fit to Hoola: department **"Logistics & Supply Chain"**; extend the four existing employees first (they have real tools), then add
control-tower and finance layers. Reuse Maps matrix and route plan (12, 13, 33), Khata (17, 27, 35, 104), appmaker for driver and rider
apps with consent-based NAKSHA location (16, 38, 39), WhatsApp opt-in (34, 90), Data Desk + pylab (46, 97, 98, 99), PC Operator for
carrier portals the user logs into (74, 80), doc studio for LR/challan/packing lists (26, 61, 68), approval cards for every file/pay/sign step.
**Best first pilot: a small transporter or an SME trader with 5-50 trucks or a regional courier franchise** - truck papers,
trip settlement, POD collection, e-way bills, freight billing and Khata for freight dues. These pains are daily, cash-linked and
live in WhatsApp; Hoola already has the fleet and logistics base.

## Open questions for the owner
- Which seat first: **small transporter / fleet owner**, **SME shipper (trader, manufacturer)**, **e-commerce merchant (courier + COD)**,
  **3PL / warehouse**, or **freight forwarder / exporter**? Each uses different employees from the same engine.
- Carrier data: which carriers' official APIs / ULIP / ONDC access will Hoola use for tracking (no scraping)?
- Driver/rider apps: confirm consent text and location-only-on-shift policy before any tracking employee ships.
- International/customs: the register assumes a licensed CHA signs; confirm whether Hoola works for the CHA, the importer, or both.
- "GO per field" turns any field into a sourced report with the exact Indian rules (MV Act, e-way, customs) checked on primary text.
