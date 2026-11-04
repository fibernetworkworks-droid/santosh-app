# The agriculture industry across the world - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A AGRICULTURE INDUSTRY AI EMPLOYEES"*. Thirteenth in the series. Agriculture here means the whole
food-and-fibre chain: crop farming (field, horticulture, plantation, protected cultivation), animal husbandry (dairy, poultry, small
ruminants, piggery), fisheries and aquaculture, forestry and agro-forestry, farm inputs (seed, fertiliser, crop protection,
machinery, irrigation), post-harvest (storage, cold chain, processing, grading), markets and trade (mandi, FPO, exporters, retail),
farm finance and insurance, extension, research and agritech, and the public programmes around all of it.

**12 fields, 125 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Schemes, laws and
  numbers named are from memory and **must be re-checked on primary text, per state and country** before any desk is built:
  in India the Insecticides Act 1968 and Rules (dealer licences, CIB&RC registration), Fertiliser Control Order, Seeds Act 1966
  (and any new Seeds law), Essential Commodities Act, state APMC acts and e-NAM, MSP announcements, PM-KISAN, PMFBY (crop insurance
  cut-off and loss-assessment rules), Kisan Credit Card norms, Soil Health Card, AgriStack / Farmer ID, FPO schemes, WDRA warehouse
  receipts (e-NWR), FSSAI, APEDA export rules and phytosanitary certification, NPOP organic standards, GI tags, DGCA drone rules
  (agri-drone operation), Animal Husbandry and veterinary-practice rules (Indian Veterinary Council Act), Fisheries schemes (PMMSY),
  groundwater regulation and water-use rights; globally FAO/Codex standards, GlobalG.A.P., USDA/EPA/FDA FSMA, EU CAP and
  pesticide approvals, ILO child-labour and seasonal-worker rules.
- Existing Hoola pieces to build on (no farm-specific employee exists yet): `mospi` (official Indian statistics, including
  agriculture), Maps (plot geometry, mandi distance, route matrix), WhatsApp opt-in campaigns and voice calls (Hinglish/regional
  languages: farmers rarely type), Khata (udhaar with traders/input dealers), `appmaker` (farmer, FPO or dairy-collection apps with
  offline outbox), Data Desk + pylab (yield, cost, price math), the research engine (scheme and technique lookups with sources),
  the Bazar shops and ONDC shopping (inputs), Guru Sahayak (agri-education), vision review (leaf/pest photos as a *aid*), `site`
  builder (FPO and farm-to-home sites), and weather/geo layers via Maps and official feeds. The Mera-PC freeze is untouched: this register
  creates no PC-side requirement.

## The findings that shape every agriculture desk
### 1. The expert with the licence is the agronomist, the vet, the pesticide dealer, the assessor and the sub-registrar
Ladder as before: **A** admin/prepare, **B** assist (check / draft / advise within label and local-recommendation limits),
**C** reserved. Reserved here: prescribing or dispensing a restricted pesticide/veterinary drug, a vet diagnosis and treatment
of a sick animal, crop-insurance loss assessment, quality certification (organic, GAP, seed certification, grading as official
grader), phytosanitary and export certificates, land title/tenancy documents, a loan sanction, a spray/drone operation by an
uncertified operator, a food-safety release, and any statement that overrides the state agri department's or label's recommendation.
**The AI explains, plans, records and reminds; the farmer decides and the licensed person certifies.**

### 2. The farmer's real problems are information, timing, price, credit and risk, in her own language
Which crop and variety for this soil and rainfall; when to sow, irrigate, spray, harvest; what pest is this and what is
the label-approved action; which scheme applies and how to claim; what is the mandi price today and where to sell; how to get a loan or
insurance paid; how to store without losing quality; how to plan inputs and credit with traders. Most of this is **advice-grade
information with sources and dates plus records and calendars**, delivered by voice/WhatsApp in a local language: Hoola's strength.
The AI must show the *source* (state agri university package of practices, ICAR, KVK, label, MSP notice) for each recommendation, state the date and
uncertainty, and refer to a human extension officer for anything off-label.

### 3. Weather and prices are volatile; honest ranges beat false precision
Yield and price forecasts are wrong often. Every employee shows a **range, basis and date**, never "guaranteed". No investment advice on
commodity futures; no encouraging debt for risky ventures; no leaking farmer data to traders. The farmer's data (plot, crop, income, loan)
is sensitive (DPDP; AgriStack consent).

### 4. The supply chain is fragmented and cash-linked; trust is the product
Middlemen, weights, rates, delays in payment, quality disputes, adulterated inputs (spurious seeds/pesticides), cold-chain gaps, and
cooperative governance. Records (weight slips, grading, advance, payments), verification (licence of the dealer, batch/expiry of the
input, genuine seed tags) and transparent price discovery are tier A and high value.

### 5. Climate, sustainability and safety are now part of farming
Heat stress, floods, drought, soil carbon, residue burning, water footprints, antimicrobial resistance (AMR) from animal antibiotics,
pesticide residues, and export MRL rejections. Compliance and traceability employees help; sustainability claims must be evidenced.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)

### 1. Farm planning, agronomy & crop management  (farmer-facing, voice-first)
1. Crop & Variety Planner - suggests crop/variety options from soil data, rainfall, season, water, market and risk, citing the state agri university / ICAR package of practices; ranges for yield and cost - B - farmer / extension officer
2. Soil Health Interpreter - reads Soil Health Card or lab report in plain words, nutrient gaps, fertiliser plan within recommended doses (cost per acre), organic matter options - B - agronomist / KVK
3. Sowing-window & Seed-rate Advisor - calendar by region and variety, seed treatment steps, spacing, population targets - B - agronomist
4. Irrigation Scheduler - crop stage, soil moisture inputs from sensors or user, weather forecast, water cost; drip/sprinkler plans; saves water - B - farmer
5. Nutrient & Fertiliser Planner (INM) - split doses, timing, foliar sprays, cost sheets, subsidy eligibility; stays within recommended doses - B - agronomist
6. Pest & Disease Identifier (photo aid) - suggests likely problems from leaf/fruit/insect photos with confidence and look-alikes; always "confirm with your local agri officer" for high-impact decisions; **diagnosis reserved** - B - agronomist / plant doctor
7. Integrated Pest Management Coach - thresholds, scouting schedule, biological and cultural controls first, label-approved options only, pre-harvest interval and re-entry rules - B - plant protection officer
8. Pesticide Safety & Label Checker - reads the product label (registered use, dose, PHI, PPE, bee/water cautions), flags banned/restricted products, compatibility, mixing sequence - B - dealer / plant protection officer
9. Spray Calendar & Weather Window - recommends spray days by wind/rain/temperature and PHI countdown to harvest; logs each spray (record for residue compliance) - A - farmer
10. Weed Management Planner - timing, mechanical and herbicide options per label, resistance rotation - B - agronomist
11. Crop Stage Tracker & Reminder - growth-stage checklist, critical stages (flowering, grain fill), tasks due, voice reminders in the local language - A - farmer
12. Harvest Readiness Advisor - maturity indices, moisture, colour/brix tests, weather risk, labour/machine booking - B - farmer / agronomist
13. Crop Rotation & Soil Fertility Planner (multi-year) with legumes, cover crops, fallows - B - agronomist
14. Farm Diary & Cost Ledger - inputs, labour, machinery, sales per plot and crop; profit per acre; photos; works offline - A - farmer
15. Organic Farming Guide & Records (NPOP conversion plan, input approvals, buffer zones, certification documents) - B - certification body decides
16. Natural / Regenerative Farming Coach (bio-inputs preparation, composts, mulching; evidence tags) - B - extension officer
17. Horticulture Specialist Assistant (orchards, vegetables, flowers: pruning, training, bloom management, post-harvest) - B - horticulturist
18. Plantation Crops Assistant (tea, coffee, rubber, spices, coconut, sugarcane: age-wise practices, yield records, replanting plans) - B - plantation manager
19. Protected Cultivation Controller Advice (polyhouse climate targets, fertigation recipes, pest watch; sensors) - B - grower
20. Mushroom, Apiary & Sericulture Coach (stepwise care, disease signs, yields) - B - specialist
21. Seed Production Planner (isolation distance, roguing, certification stages, tags) - B - seed grower + certification agency
22. Farm Labour Planner (sowing/harvest crews, attendance, daily wage, advances, women-worker safety rules; pay on tap) - A - farmer
23. Farm Safety Reminder (PPE, sprayer calibration, machinery guards, heat stress, snakebite first-aid pointers) - A - farmer
24. Agri Calendar for the Village (festivals, sowing, canal releases, mandi days, scheme deadlines) - A - panchayat / FPO

### 2. Climate, weather, water & land
25. Weather Alert Agent (official forecast feeds; heat, cold wave, hail, cyclone, heavy rain, frost; crop-specific actions; voice call) - A - farmer
26. Seasonal Outlook Interpreter (monsoon onset/progress, ENSO signals; "wait, not forecast" language) - B - agronomist
27. Drought & Flood Planner (contingency crops, water storage, evacuation of seed/stock, insurance steps) - B - extension officer
28. Water Budget Planner (borewell/canal/tank water, crop water needs, rainwater harvesting sizing, groundwater rules) - B - water engineer
29. Farm Pond & Micro-irrigation Designer Assistant (sizing, subsidy applicability, drawings; **engineer certifies**) - B - agri-engineer
30. Soil & Water Conservation Planner (contour bunds, check dams, terracing; MGNREGA works eligibility) - B - watershed officer
31. Land Records Reader (7/12, khasra, khatauni, mutation status, boundary disputes lists; **legal opinion reserved**) - A/B - revenue consultant
32. Plot Mapper (GPS boundary capture, area calculation, Maps overlays, survey numbers) - A - farmer
33. Tenancy & Lease Records Assistant (share-cropping/lease terms, advance, crop rights; state-law caution; **legal reviewed**) - B - advocate
34. Carbon & Climate Programme Navigator (soil carbon projects, regenerative payments, verification steps; red flags for unverified buyers) - B - sustainability consultant
35. Agroforestry & Tree Planter's Assistant (species choice, spacing, permissions to fell, income timeline, carbon) - B - forest officer

### 3. Inputs: seed, fertiliser, crop protection, machinery
36. Input Finder & Price Comparer (nearby dealers via Maps, price quotes provided by dealers, ONDC listings; genuine-label checks) - A - farmer
37. Dealer Verification Assistant (licence number, batch, expiry, authorised-brand checks; fake-seed/pesticide red flags) - B - farmer / agri officer
38. Input Subsidy & Scheme Navigator (seed, drip, mechanisation, solar pumps: eligibility, documents, steps, deadlines) - A - CSC / extension officer
39. Farm Machinery Matcher (tractor/implement choice by acreage, soil, crop, fuel cost; custom hiring centres) - A - farmer
40. Custom Hiring & Machinery Sharing Scheduler (FPO/CHC bookings, hours, fuel, operator, payments) - A - FPO / CHC manager
41. Machinery Maintenance Planner (service hours, parts, spares, breakdown help) - A - owner
42. Agri-drone Spray Service Coordinator (certified operators, no-fly checks, SOP, area sums, label compliance; **operator and safety rules**) - B - drone operator
43. Input Dealer's Assistant (stock, batch/expiry, licence calendar, credit ledger, farmer demand, safe-use counselling scripts) - A - dealer
44. Seed Company QA Assistant (germination test results, lot tracking, labelling, complaints) - A/B - seed QA
45. Fertiliser Distribution & POS Reconciler (sales vs stock vs subsidy records) - A - retailer / cooperative
46. Biological Inputs Maker's Assistant (biofertiliser, biopesticide batch records, quality tests, shelf-life) - B - producer

### 4. Livestock, dairy, poultry & animal health
47. Dairy Farm Manager (herd register, ear-tag, breeding/AI dates, calving, feed ration, milk yield per animal, vet visits) - A - dairy farmer
48. Ration Balancer (feed formulation from available fodder/concentrate within nutrient requirements; cost per litre) - B - animal nutritionist
49. Breeding & AI Scheduler (heat signs, insemination records, pregnancy checks, calving forecast) - A/B - vet / AI technician
50. Animal Health Watcher (vaccination calendar FMD/HS/BQ/PPR etc., deworming, tick control, mastitis checks; symptoms checklist; **diagnosis and treatment by veterinarian**) - B - veterinarian
51. Antibiotic Stewardship Guard (withdrawal periods, milk/meat/egg discard dates, banned antibiotic list, record of every treatment) - B - veterinarian
52. Milk Collection Centre Assistant (fat/SNF recording, rates, payments, lot reconciliation, adulteration flags; cooperative bill) - A - dairy cooperative
53. Poultry Farm Manager (batches, FCR, mortality, vaccination, feed, temperature/humidity logs, biosecurity) - A/B - poultry farmer
54. Goat/Sheep/Pig/Small-ruminant Planner (breeding, grazing, deworming, market timing) - B - farmer / vet
55. Fodder & Pasture Planner (crop calendars for green fodder, silage, hay, water, stock rates) - B - animal nutritionist
56. Animal Disease Outbreak Watch (official notifications, movement restrictions, vaccination drives, safe-trade checklists) - A/B - veterinary officer
57. Animal Identification & Traceability Record Keeper (tags, movement permits, health certificates) - A - farmer / department
58. Livestock Market Assistant (price discovery, buyer verification, transport permit, welfare rules for transport) - A - farmer
59. Dairy Processing Quality Assistant (pasteurisation logs, microbiological tests, cold chain, FSSAI documents) - B - dairy plant QA
60. Veterinary Clinic Assistant (appointments, records, vaccination reminders, inventory; see healthcare vet role) - A - vet

### 5. Fisheries & aquaculture
61. Aquaculture Pond Manager (stocking, feed, water-quality logs: DO, pH, ammonia, salinity; harvest planning) - A/B - fish farmer
62. Fish Health & Biosecurity Watch (mortality, disease signs, farm hygiene, notifiable disease prompts; **vet/fisheries expert diagnosis**) - B - aquatic vet
63. Fishing Trip & Catch Log (boat, safe-zone/weather alerts, catch records, fish-landing center sales) - A - fisher
64. Seafood Traceability & Export Documents Helper (catch certificate, HACCP, EU/US rules checklist) - B - exporter
65. Fish Market & Cold-chain Tracker (ice, storage temperature, auction price, transport) - A - fish trader

### 6. Post-harvest, storage, processing & value addition
66. Post-harvest Loss Reducer (drying, grading, curing, packaging, pre-cooling advice by crop) - B - post-harvest technologist
67. Warehouse Receipt Assistant (WDRA/e-NWR: deposit, grading, receipt, pledge financing steps) - A/B - warehouse manager
68. Cold-storage Manager (rental booking, temperature logs, inventory, power cost, quality alerts) - A - cold-chain operator
69. Grain Storage Pest Guard (moisture checks, fumigation safety rules, insect monitoring, record of treatments) - B - storage manager
70. Grading & Sorting Quality Assistant (image-based sorting aid, Agmark/APEDA grade tables, rejects log; **official grading reserved**) - B - grader
71. Primary Processing Planner (flour mill, oil press, dal mill, jaggery, spice, pulping: yields, costs, FSSAI licence checks) - B - processor
72. Food Safety Records (HACCP-style logs, supplier approvals, traceability lots, recalls; **QA releases**) - B - QA manager
73. By-product & Waste Valorisation Advisor (straw, husk, bagasse, whey, manure: biogas, compost, feed uses) - B - agri-engineer
74. Packaging & Branding Assistant for Farm-direct Products (labels, FSSAI declarations, barcode, shelf-life claims) - B - regulatory + marketing
75. Agro-processing Cluster Planner (shared facilities, FPO units, capex, scheme support) - B - project consultant

### 7. Markets, price discovery & trade
76. Mandi Price Reader (official daily arrivals and rates from public feeds, nearby markets distance and transport cost, simple trend with date) - A - farmer
77. Sell-or-Store Advisor (price seasonality from history, storage cost, loan interest, quality loss; scenarios not promises) - B - farmer
78. MSP & Procurement Navigator (procurement centre, registration, quality norms, payment status checks) - A - farmer
79. e-NAM / Online Mandi Assistant (registration, lot entry, assay request, bids, payment tracking; official portal on user's tap) - A - farmer
80. Contract Farming Checker (terms, buyback price, quality specs, dispute clauses; **legal review before signing**) - B - FPO / advocate
81. Trader & Buyer Verifier (past payment record, licences, references; red flags) - B - FPO
82. Weighment & Payment Ledger (weight slips, deductions, due dates, UPI receipts, Khata for dues) - A - farmer / trader
83. Farmer-to-Consumer Sales Desk (WhatsApp catalogue, orders, delivery routes, subscription boxes, hygiene rules, payments via UPI cards) - A - farm-direct seller
84. Export Readiness Assistant (APEDA registration, residue/MRL test reports, phytosanitary, packing, buyer docs; **certificates by authorities**) - B - exporter
85. Commodity Trader's Desk (stock, quality lots, positions, dispatches; not trading advice) - A - trader
86. Retail Grocery Sourcing Assistant (farm-direct procurement, quality specs, price benchmarks) - A - buyer
87. Food-miles & Traceability Storyteller (QR page with farm origin, practices, test reports; claims evidence) - B - brand

### 8. Farm finance, insurance & government schemes
88. Scheme Navigator (PM-KISAN, state schemes, subsidies, KCC, PMFBY, solar pump, FPO support: eligibility, documents, how to apply, deadlines, status checks) - A - CSC / farmer
89. Kisan Credit & Loan Assistant (document list, eligibility, EMI/interest calculator, repayment calendar; **bank decides**) - A - farmer
90. Crop Insurance Companion (enrolment cut-offs, premium, sum insured, loss-intimation steps within 72 hours, photo evidence capture, claim tracking; **loss assessment reserved**) - B - farmer / insurer
91. Farm Accounting & GST/Tax Assistant (agri income exemptions, input GST credits for agri-business, TDS on contracts; **CA files**) - B - CA
92. FPO Finance Manager (member share ledger, equity, working capital, bank reconciliation, grants utilisation) - A - FPO CEO
93. Microfinance & SHG Ledger Assistant (savings, loans, meetings, repayment, bank linkage) - A - SHG leader
94. Subsidy Claim Packager (invoices, geotag photos, bank details, forms; submission on user tap) - A - farmer / dealer
95. Disaster Relief Claim Assistant (damage evidence, panchnama steps, compensation schemes) - B - farmer / revenue officer
96. Farm Succession & Land Partition Planner (legal-heir steps, mutation; **advocate**) - B - advocate

### 9. Extension, education & knowledge
97. Digital Extension Officer (voice Q&A in dialects, state package of practices, ICAR/KVK advisories, source-cited, escalate to human) - B - extension officer
98. Krishi Vigyan Kendra (KVK) Programme Assistant (training calendars, demos, farmer registration, follow-up surveys) - A - KVK coordinator
99. Agri Student Tutor (agronomy, soil science, plant pathology, animal science; Guru Sahayak) - A - faculty
100. Farm School for Women & Youth Farmers (short lessons by voice/WhatsApp, local language, practical demos) - A - NGO / extension
101. Field Demonstration Recorder (plot design, treatments, data capture, comparison reports) - A - researcher / KVK
102. Research Data Assistant (trial design randomisation, ANOVA in pylab, plots, report skeleton) - B - agricultural researcher
103. Literature & Technology Scout (new varieties, techniques, patents; sources and caution) - A - research head
104. Knowledge Base Curator (state-specific practices, local names for pests/crops, glossary in 10+ languages) - A - extension unit

### 10. FPOs, cooperatives & community institutions
105. FPO Secretary's Assistant (member registry, meetings, AGM minutes, share certificates, compliance filings under Companies/Cooperative law) - A - FPO CEO / secretary
106. Collective Input Purchase Planner (demand aggregation, tenders, bulk discounts, distribution) - A - FPO
107. Collective Marketing Manager (grading, pooling, brand, buyer negotiation support, payout waterfall) - A - FPO
108. Cooperative Governance Auditor's Assistant (bylaws check, election calendar, loan records, conflict-of-interest flags) - B - registrar / auditor
109. Women Farmers' Collective Assistant (SHG-FPO linkages, training, micro-enterprise plans) - A - NGO
110. Village Agri-entrepreneur (Krishi Mitra) Toolkit (service pricing, dealer relationships, customer follow-up) - A - entrepreneur

### 11. Agritech, precision agriculture & data
111. Satellite/Drone Crop Monitor (NDVI/vigour maps from open or provider imagery, anomaly zones, scouting plan; ranges, not diagnoses) - B - agronomist
112. IoT Sensor Data Wrangler (soil moisture, weather station, tank level, pump status; alerts; offline-first) - A - agritech engineer
113. Yield Estimation Assistant (crop cuts, sampling design, remote signals; error range) - B - agronomist
114. Variable-rate Prescription Preparer (zone-wise seed/fertiliser plans for compatible machines; **farmer approves**) - B - precision-ag consultant
115. Farm Robotics & Automation Planner (milking, feeding, weeding robots; safety, ROI) - B - engineer
116. AgriStack / Farmer-ID Data Steward (consent artefacts, dedupe, privacy) - A/B - data officer
117. Agri Market Intelligence Analyst (area/yield/price series from MoSPI, state data; pylab; sources) - A - analyst
118. Agri-startup Founder Copilot (problem validation, field pilots, subsidy/grant finder, compliance map) - A - founder

### 12. Government, regulation & public good
119. Pesticide & Fertiliser Inspector's Assistant (sampling log, test result tracking, case file; **enforcement human**) - B - inspector
120. Seed Certification Officer's Assistant (field inspections schedule, lot tags, test results) - A - certification officer
121. Agricultural Statistics Collector (crop-cutting experiments, area enumeration, data QC) - A - statistics officer
122. Disease & Pest Surveillance Network Assistant (reports from farmers, mapped outbreaks, advisory drafting) - B - plant protection officer
123. Food Security & Procurement Planner (stocks, PDS pipeline, buffer norms; scenario tables) - B - policy analyst
124. Climate-resilient Agriculture Planner (district adaptation plans, crop shifts, extension schedules) - B - agriculture department
125. Farmer Grievance & Helpline Agent (Kisan Call Centre style: voice, escalation, status tracking) - A - helpline lead

## NEVER an AI Employee (tier C)
Prescribe, sell or dispense a restricted pesticide or veterinary drug; diagnose and treat a sick animal as a vet; recommend
off-label or banned chemical use; declare an official crop-insurance loss or a procurement grade; issue organic, GAP or
phytosanitary certificates; sign land, lease or sale documents; sanction a loan or deny a claim; operate a drone/spray without
a certified operator and the rules; order a culling or quarantine; promise yields, prices or insurance payouts; pressure a
farmer into debt or contracts; leak farmer data to buyers/lenders without consent; scrape mandi portals against their terms.

## Suggested build order
1. **Wave 1 - voice-first farmer basics (tier A, no licence required)**: 11, 14, 24, 25, 32, 36, 38, 76, 78, 82, 83, 88, 89, 97 - works in Hindi/Marathi/regional voice and WhatsApp, builds on official data (MoSPI, weather, mandi feeds).
2. **Wave 2 - advice with sources and a named human**: 1-10, 12, 22, 47-53, 67, 68, 77, 79, 90, 92, 105-107.
3. **Wave 3 - regulated, safety- or certificate-adjacent**: 6, 8, 15, 21, 42, 50, 51, 62, 70, 72, 80, 84, 111, 114, 119, 120.
Fit to Hoola: department **"Agriculture & Allied"**; Hoola has no farm role yet, so Wave 1 is a new base, not an extension: a **Kisan Sahayak** that
lives on voice calls and WhatsApp. Reuse the voice stack (Gemini/OpenAI Live in Indian languages), Maps (plots, mandi distances),
`mospi` (official statistics), Khata (trader dues), `appmaker` (offline farmer/FPO/dairy apps), pylab (cost, yield, ration, ANOVA),
the research engine with citations (schemes, practices), vision review (leaf/animal photos as aids), Pehchaan Locker (Aadhaar-masked
scheme forms), approval cards for every submission, and the website builder (FPO sites).
**Best first pilots**: (a) a **dairy village / milk collection cooperative** (52, 47, 49, 50, 82: daily, cash-linked, records heavy) and
(b) an **FPO** (105-107, 92, 83) - they have an owner, members, money and records. A single-farmer **Kisan Sahayak** (11, 14, 25, 76, 88) is the
mass-market consumer product and can ride the same engines.

## Open questions for the owner
- Which segment first: **individual farmers** (mass, low-ARPU, voice), **dairy cooperatives/FPOs** (institutional, records), **input dealers/agri-
  retailers**, **exporters/processors**, or **government/NGO programmes**? I'd start with dairy cooperative + FPO.
- Language and channel: which languages first and is the main channel **voice call**, **WhatsApp voice notes** or an app? Farmers rarely type.
- Which state(s)? Package of practices, scheme rules, mandi rules and pesticide recommendations differ by state; each is a data pack
  with a citation, and must be kept current by a named maintainer.
- Disease and pest advice: confirm the escalation rule (always cite and say "confirm with your agri officer") and the no-banned-chemical
  rule before any pest/photo employee (6, 8, 10) ships.
- Farmer data and consent: AgriStack / Farmer-ID integration, DPDP, no sharing with lenders/buyers without consent.
- "GO per field" turns any field into a sourced report with package-of-practices, scheme rules and the Insecticides Act checked on primary text.
