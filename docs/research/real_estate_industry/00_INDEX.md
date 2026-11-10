# The real estate industry, function by function - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A REAL ESTATE INDUSTRY AI EMPLOYEE LIST"*. Ninth in the series, directly after
`construction_industry/` (123 roles, which already covers the BUILDER's side: land feasibility, approvals, RERA project
compliance, handover, FM and society management; cross-referenced here as CI#). This one is the MARKET side: the broker,
the buyer and seller, the tenant and landlord, the valuer, the lender, the registrar, the investor and the platform.

**14 fields, 107 candidate AI Employees.**

## How honest this is
- No new web research for this file, and unlike construction there is no sourced job census in the repo to build on. The
  register is **domain knowledge, not sourced**; all legal references are from memory and **must be re-checked on
  primary text, per state** before any desk is built: RERA 2016 and the state RERA rules (agent registration, advertising
  with registration number, 70% escrow, defect liability), Transfer of Property Act 1882, Registration Act 1908 and state
  stamp-duty / registration schedules, Indian Contract Act, Model Tenancy Act 2021 (states adopt their own), state rent-control
  acts, Benami Transactions (Prohibition) Act, Income-tax Act provisions on property (TDS on purchase, capital gains,
  rent), GST on construction services, FEMA rules for NRI purchases, SARFAESI / IBC for distressed assets, IBBI registered-valuer
  rules, SEBI REIT / InvIT regulations, Consumer Protection Act, DPDP Act 2023. Abroad: Fair Housing / RESPA / MLS rules (US),
  AML for real estate (FATF), and local licensing of agents.
- Nothing is built. Hoola today has `property_manager`, `society_manager`, `architect_assistant`, a Khata ledger, Maps,
  WhatsApp opt-in campaigns, `website` builder (listing sites, forms, maps, galleries), HyperFrames/VR assets for walkthrough
  media, Pehchaan Locker (masked IDs), doc studio + HOOLA PRINT, and the Bazar shops. Live listing portals do not allow scraping:
  the register assumes the user's own data, public records and official APIs only (non-negotiable rule: official routes only).

## The findings that shape every real-estate desk
### 1. The legal act belongs to the registered person: sub-registrar, advocate, registered valuer, RERA-registered agent, CA
Same ladder as before: **A** admin/prepare, **B** assist (check / draft / estimate for a named human), **C** reserved.
Reserved here: executing or registering a sale deed or lease, giving a title opinion, issuing a valuation report, quoting
a legal price as a registered agent without registration, accepting token money, certifying RERA/escrow,
approving a home loan, issuing a no-dues or possession letter, a stamp-duty payment, a TDS/tax filing in someone's name,
and any binding agreement signed for a person. The AI **prepares and checks the file; the person executes.**

### 2. The biggest customer problem is TRUST and VERIFICATION, not search
Fake listings, double sales, forged documents, encumbrances, unapproved layouts, builders without RERA registration,
rent deposits not returned, unexplained maintenance charges. An employee that stands on the **buyer's/tenant's side** and
runs a checklist (RERA number is real and in date, plot is in an approved layout, the seller is the recorded owner,
loan or litigation exists, the carpet area matches the agreement, the stamp duty figure is right) is lawful and is
exactly Hoola's "your avatar works for you" idea. It never says a title is clear; it says what it checked and what it could
not.

### 3. Real estate is a records, calendar and money business around a few large decisions
Property papers, rent cycles, EMIs, TDS challans, maintenance dues, lease renewals, agreement clauses, inspections,
repairs, tax: scattered across WhatsApp, drawers and email. A memory-plus-calendar employee (property vault, due dates,
rent roll, paper trail) is tier A and sticky for a landlord or small investor.

### 4. Data, fairness and portal rules are the edge
Valuation and credit models can discriminate by locality, caste or religion proxies; the US Fair Housing Act and Indian
equality norms bar discriminatory ads and tenant screening on protected traits; scraping portals breaks terms (and
Hoola's rule). Rent-and-price estimates must show their comparables and their error range, never one confident number.

---
## THE REGISTER  (seat - AI Employee - what it does - tier - the human who decides)
Seats: [B] buyer/tenant, [S] seller/landlord, [A] agent/broker/dealer, [D] developer/promoter (see CI#), [L] lender/valuer/legal,
[I] investor/fund, [O] operator (PM/FM/co-living/co-working), [G] government/regulator.

### 1. Property search, discovery & buyer advisory
1. [B] Requirement Interviewer - budget, commute, schools, family, vastu/direction wishes, financing; writes a search brief - A - buyer
2. [B] Locality Analyst - commute (Maps), water/power reliability, flood/zone layers, schools/hospitals within radius, price trend from public registry data - A - buyer
3. [B] Listing Triage Assistant - the buyer's own saved links and shared listings compared in one grid; flags missing facts (floor, age, RERA, parking) - A - buyer
4. [B] Site-visit Planner & Note-taker - route, checklist (damp, leaks, light, noise, water pressure), photo notes, comparison score - A - buyer
5. [B] Affordability & Home-loan Estimator - EMI, eligibility bands, total cost incl. stamp duty, registration, GST, brokerage, interiors, maintenance deposit (pylab) - A - buyer
6. [B] Rent-vs-Buy & Investment Calculator - cash-flow, capital gains, tax effect, scenarios; ranges not point forecasts - A - buyer
7. [B] Under-construction Risk Checker - RERA page status, promoter history, escrow note, delay record, litigation flags from public portals - B - buyer / advocate
8. [B] Resale Property Due-diligence Checklist Runner - documents list, chain of title index, tax receipts, society NOC, loan clearance, pending dues; **opinion reserved** - B - advocate
9. [B] NRI Buyer Assistant - FEMA/repatriation basics, power-of-attorney checklist, tax residency flags, remote visit scheduling; **advice by CA/advocate** - B - CA / advocate
10. [B] Senior-living & Special-needs Housing Matcher (accessibility, healthcare proximity, community) - A - family
11. [B] Student & Migrant Housing Finder (PG, shared flats, co-living; verified-owner check, rule list, fair rent range) - A - tenant

### 2. Brokerage & dealer operations
12. [A] Broker CRM Assistant - lead capture (opt-in), follow-ups, site-visit calendar, deal stages, WhatsApp templates in Hinglish - A - broker
13. [A] Listing Writer & Media Producer - description, floor-plan labelling, photo captions, 30-sec walkthrough video (HyperFrames), no false claims, RERA number on ads - B - broker + compliance
14. [A] Property Matching Engine - matches an owner's inventory with client requirements; explains the match with facts - A - broker
15. [A] Brokerage Compliance Assistant - agent registration validity (RERA), commission agreement templates, receipts, GST on brokerage - A - broker principal
16. [A] Token-money & Booking Tracker - receipts, deadlines, refund conditions, cancellations; **money handled by the parties** - A - broker
17. [A] Agreement-draft Assistant - leave & license, sale agreement, letter of intent drafts from templates with blanks; **advocate reviews, parties sign** - B - advocate
18. [A] Commission Reconciler - split between brokers, referral fees, TDS, aging dues - A - accounts
19. [A] Channel-partner Manager (for developers): partner onboarding, site-visit attribution, payout statements, dispute log - A - sales head
20. [A] Auction & Distressed-asset Scout (SARFAESI / bank / court auction notices from official gazettes; eligibility, EMD, dates) - B - investor / advocate

### 3. Leasing, rentals & tenancy
21. [S] Landlord Desk - rent roll, escalation clause, due-date reminders (WhatsApp opt-in), receipts, arrears ageing, TDS on rent where applicable - A - landlord
22. [S] Tenant Screening Assistant - verified identity docs (masked), income proof check, reference calls scripted, past-rent history; **no discrimination on protected traits; decision by landlord** - B - landlord
23. [S] Lease Drafting & Registration Planner (Model Tenancy Act state variant, leave-and-licence term, police verification where required, stamp/registration steps) - B - advocate
24. [B] Tenant Rights Helper - deposit rules, notice periods, maintenance obligations, how to document a dispute; **not legal advice** - A - tenant
25. [S] Rent Escalation & Renewal Planner - benchmark rent, clause dates, notice drafts - A - landlord
26. [S] Property Inspection Kit - move-in/move-out condition report with photo timeline, damage claim worksheet (comparison, depreciation) - A - landlord / tenant
27. [S] Rental Yield Optimiser - comparable rents, vacancy cost, capex payback, furnished vs unfurnished (pylab) - A - landlord
28. [O] Co-living / PG Operator Assistant - bed-level occupancy, rent cycles, house rules, KYC, food/laundry rosters, complaints - A - operator
29. [O] Co-working / Serviced-office Assistant - desk bookings, invoices, meeting rooms, member onboarding, visitor passes - A - operator
30. [O] Short-stay / Holiday-home Host Assistant - calendar sync, guest messaging, cleaning rosters, pricing prompts, guest KYC where required - A - host

### 4. Property & community management
31. [O] * Property Manager Assistant (existing) - rent roll, tenants, maintenance, utility bills, inspections - A - property manager
32. [O] * Society / Association Manager (existing; state law differs) - dues, notices, meetings, AGM, vendors, complaints - A - secretary
33. [O] Maintenance Ticket Router - complaint to vendor to closure with photos, SLA clock, cost approval - A - FM / manager
34. [O] Vendor Marketplace Coordinator - plumbers, electricians, painters, pest control: quotes, ratings, payouts on tap - A - manager
35. [O] Utility & Common-area Billing Assistant - water/power/DG split, meter reading sheets, slab calculation - A - accountant
36. [O] Visitor, Gate & Parking Manager - passes, delivery logging, parking allotment - A - security head
37. [O] Resident Communication Desk - notices, polls, event bookings, multilingual announcements - A - committee
38. [O] Society Compliance Calendar - audit, registrar returns, lifts/fire/insurance renewals, structural audit due dates - A - secretary
39. [O] Redevelopment Process Assistant - member consent tracking, developer comparison, agreement checklist, timeline of statutory steps; **legal steps reserved** - B - committee + advocate

### 5. Transactions, registration & legal
40. [L] Title-search Index Builder - links 7/12 or property-card, mutation, index-II, encumbrance, litigation records into a chain-of-title timeline; **opinion by advocate** - B - advocate
41. [L] Sale-deed Draft Assistant (parties, schedule of property, payment schedule, covenants, stamp duty computation) - B - advocate
42. [L] Stamp-duty & Registration Fee Calculator (state, gender/senior concessions, e-stamping flow, ready-reckoner rate lookup) - A - buyer / advocate
43. [L] Registration Slot & Document Packer (appointment, ID proofs, witnesses, NOC list) - A - parties / advocate
44. [L] Mutation & Khata Transfer Tracker - after-registration steps (revenue, municipal, society, electricity, water) - A - owner
45. [L] Power-of-Attorney & Will Drafting Assistant (property context; **advocate reviews; witnesses and registration human**) - B - advocate
46. [L] Succession & Inheritance Navigator (legal-heir certificate, mutation, family settlement outline, tax) - B - advocate
47. [L] Property Dispute File Assistant (chronology, evidence index, notices, RERA/consumer/civil forum route chart) - B - advocate
48. [L] Encroachment & Boundary Dispute Mapper (survey vs record overlays via GIS; **court decides**) - B - surveyor / advocate
49. [L] Benami / Black-money Red-flag Screener (cash component hints, mismatch of declared value, unrelated payer; reports to the user, not authorities) - B - CA / advocate

### 6. Home loans, valuation & finance
50. [L] Loan Document Collector (KYC, income, property papers, bank statements; completeness before lender submission) - A - borrower
51. [L] Loan Offer Comparer (rate type, processing fee, prepayment rules, insurance add-ons, total cost; pylab) - A - borrower
52. [L] Loan Servicing Assistant (EMI calendar, prepayment impact, rate reset alerts, interest certificate for tax) - A - borrower
53. [L] Underwriter's Property Pack Assistant (lender side: valuation, legal report, approvals, LTV working; **credit decision reserved**) - B - credit officer
54. [L] Valuation Report Drafter (comparable table, cost/income approach worksheets, photos; **issued only by a registered valuer**) - B - registered valuer
55. [L] Automated Valuation Sanity Checker (flags outliers vs comparables, stale data, missing area basis) - B - valuer / lender
56. [L] Property-tax & Municipal Dues Tracker (assessment, payment due, rebates, arrears) - A - owner
57. [L] Capital-gains & Property Tax Planner (holding period, indexation rules as applicable, exemptions, TDS on sale; **CA files**) - B - CA
58. [L] Insurance Advisor for Property (home, fire, content, landlord cover; claims checklist) - A/B - agent

### 7. Investment, REITs & funds
59. [I] Real-estate Deal Screener - location, yield, cap rate, stress cases (vacancy, rate rise), exit multiples; ranges not forecasts - A - investor
60. [I] Fractional / Co-investment Platform Checker (disclosure completeness, SEBI-regulated vs unregulated, fee structure, exit rights) - B - investor
61. [I] REIT / InvIT Tracker (NAV, distributions, occupancy, tenant concentration, debt maturity from filings) - A - investor
62. [I] Portfolio Dashboard (owned units, rents, loans, valuation estimate ranges, tax lots; Pehchaan Locker) - A - investor
63. [I] Acquisition Due-diligence Coordinator (commercial: lease abstracts, rent rolls, estoppel-like confirmations, technical audit list) - B - deal team
64. [I] Lease Abstractor (extracts terms from lease PDFs: rent, escalation, lock-in, break options, reinstatement; flags unusual clauses) - B - lawyer
65. [I] Fund Reporting Assistant (investor statements, capital calls, distributions waterfall checks; pylab) - A - fund accountant
66. [I] ESG & Green-certification Tracker for Assets (IGBC / GRIHA / LEED status, energy intensity) - A - asset manager (CI#110)

### 8. Developer sales & marketing (see CI#92-99 for the project/RERA/handover side)
67. [D] Launch Planner (pricing strategy tables, inventory release, phase plan, demand tests; pylab) - A - sales head
68. [D] Digital Marketing Assistant (RERA-compliant ads, landing pages, lead forms, WhatsApp opt-in; **no guaranteed-return claims**) - B - marketing + legal
69. [D] Sales Gallery Concierge (voice/chat on site and web: unit availability, payment plan, floor plan Q&A from approved data only) - A - sales manager
70. [D] Demand-letter & Collections Tracker (milestone demands, interest, reminders) - A - CRM head (CI#92)
71. [D] Resale / Transfer-of-allotment Desk (NOC rules, fee, documents) - A - CRM
72. [D] Customer Grievance Desk (RERA complaint prevention: log, escalate, close, evidence) - A - customer care
73. [D] Brand & Reputation Monitor (reviews, RERA complaints, social posts; sentiment topics) - A - marketing

### 9. Commercial, retail, industrial & land
74. [A] Commercial Leasing Assistant (tenant requirement, floor-plate fit, rent benchmarks, fit-out period, incentives) - A - leasing broker
75. [A] Retail Site-selection Analyst (footfall proxies from public data, competitor map, catchment demographics; no scraping) - A - retailer / broker
76. [A] Warehouse & Logistics Park Matcher (highway access, docks, clear height, fire NOC, power, rent) - A - broker
77. [A] Agricultural / NA Land Assistant (land-use zone, conversion process, 7/12 reading, water access, buyer eligibility rules by state) - B - advocate / revenue consultant
78. [D] Plotted-layout Development Assistant (approved layout checklist, plot numbering, roads/open-space ratios, sale deed readiness) - B - architect / advocate (CI#1-6)
79. [A] Land Aggregation Tracker (owner list, consent status, rate negotiations, deal pipeline) - A - land manager

### 10. Valuation, appraisal & research
80. [L] Market Research Analyst (absorption, launches, rental indices, supply pipeline from public sources; pylab) - A - research head
81. [L] Comparable-sales Collector (registry-index data, own transactions, stated sources; **no portal scraping**) - A - valuer
82. [L] Rent-and-price Index Builder (hedonic models with shown error bands) - B - economist
83. [L] Hazard & Resilience Screener (flood, seismic, heat, coastal) with disclosure statement for lenders/buyers - B - consultant
84. [L] Neighbourhood Change Monitor (new transit, rezoning notices, master-plan changes from gazettes) - A - planner

### 11. Government, regulators & city administration
85. [G] RERA Authority Assistant (complaint intake, hearing schedules, project-update compliance checks; **orders reserved**) - B - authority officer
86. [G] Sub-registrar Office Assistant (appointment load, document checklists, valuation-rate lookup; **registration reserved**) - A - registrar
87. [G] Municipal Property-tax Desk (assessment data, notices, collections, grievance routing) - A - municipal officer
88. [G] Land-record Digitisation Assistant (scan QA, OCR of legacy records, survey mapping) - B - revenue officer
89. [G] Affordable Housing Scheme Navigator (PMAY and state schemes: eligibility, documents, subsidy steps) - A - citizen / CSC
90. [G] Slum & Redevelopment Authority Assistant (survey, eligibility lists, consent tracking) - B - authority
91. [G] Housing-data Open-data Publisher (de-identified statistics, dashboards) - A - data officer

### 12. Proptech platform operations
92. [O] Listing Verification Agent (owner identity, document match, geotag photos, duplicate detection; **platform policy decides**) - B - trust & safety
93. [O] Fraud & Scam Detector (fake listings, advance-fee rental scams, impersonation; flags only) - B - trust & safety
94. [O] Platform Support Desk (buyers, owners, brokers; escalations) - A - support
95. [O] Search Quality & Ranking Auditor (fairness, spam, stale listings) - B - product
96. [O] Fair-housing Compliance Reviewer (flags discriminatory ad text and filters) - B - compliance
97. [O] Data Partnership Manager (consents, licence terms, delisting requests, DPDP rights) - A - DPO

### 13. Home services & adjacent businesses
98. [B] Home Interiors Planner (links to `interior_designer`): budget, layouts, vendor quotes, schedule - A - owner
99. [B] Move-in / Relocation Coordinator (packers, utilities transfer, address changes, checklist) - A - household
100. [B] Home-warranty & Appliance Tracker (bills, warranties, AMC dates, service requests) - A - household
101. [B] Home Renovation Contractor Finder & Quote Comparer (scope, rates sanity vs norms from CI#38) - A - owner
102. [B] Smart-home Setup Assistant (links to Ghar/Home Assistant; **controls remain gated**) - A - owner
103. [O] Mortgage-insurance & Rent-guarantee Claim Assistant (documents, timelines) - A - owner

### 14. Education, advice & community
104. [B] First-time Buyer Tutor (process map, jargon, costs, red flags, in local languages; no advice on a specific deal) - A - public
105. [A] Broker Exam & CPD Coach (RERA agent examination prep, ethics, state law basics) - A - broker
106. [B] Landlord-Tenant Law Explainer (state act summaries with sources and dates; refers to advocate) - B - public
107. [I] Real-estate Investor Education Coach (risk, leverage, due diligence; no stock-style tips) - A - public

## NEVER an AI Employee (tier C)
Sign, execute or register a sale deed, lease, POA or will; give a title opinion or say a title is clear; issue a valuation
report; accept or hold token money; certify RERA, carpet area or escrow; approve a loan or decide a tenancy applicant on
protected traits; pay stamp duty or tax or file a return in a person's name; negotiate and bind a person to a deal;
publish a listing or ad without the owner/broker's approval and a RERA number where required; scrape a listing
portal or post as a person; make guaranteed-return or "assured appreciation" claims; contact tenants/residents in a
way that pressures or harasses.

## Suggested build order
1. **Wave 1 - owner/tenant-side records and money (tier A, no legal act)**: 5, 6, 21, 25, 26, 31-35, 38, 42, 44, 50-52, 56, 62, 98-100.
2. **Wave 2 - brokers and buyers' checklists (A/B with a named person)**: 1-4, 7, 8, 12-18, 22-24, 40, 41, 43, 64.
3. **Wave 3 - valuation, lender, investor and platform trust (regulated, human-signed)**: 53-55, 59-61, 63, 92, 93, 96.
Fit to Hoola: department **"Real Estate & Property"** next to Construction; extend `property_manager` and `society_manager`
(live), reuse Khata (16, 18, 21, 70), Maps (2, 4), WhatsApp opt-in campaigns (12, 21, 68), Pehchaan Locker (14, 50, 62), pylab
(5, 6, 27, 59), research engine (80, 106), the website builder for listing sites (13, 69), HyperFrames (13), approval cards
for every execution step, state rule packs as data. **Best first pilot: the landlord / small investor** (21, 25, 26, 52,
56, 62) - a Hindi/Marathi-speaking owner with 1-5 flats, rent in WhatsApp, TDS in a drawer - plus a **tenant/buyer verification
checklist** (7, 8, 24): fastest to value, no brokerage fight, no signing.

## Open questions for the owner
- Which seat first: **owner/landlord**, **buyer/tenant**, **broker/dealer**, **developer sales**, or **platform**? Brokers are
  the paying B2B user, owners the stickiest B2C one.
- Which state(s)? Stamp duty, registration, tenancy and society law differ; each state's rule pack must be maintained.
- Listings: Hoola must not scrape portals (official routes only). Which data sources will it use: the user's own data, public
  registry (index-II), RERA public pages, and partner APIs? A partnership with one portal may unlock search.
- Money handling: the AI never holds token money or rent; confirm that Hoola stays a record and reminder layer (with UPI
  cards only on the user's tap).
- Fair-housing and tenant-screening policy: no scoring on religion/caste/diet/gender/marital status; confirm the line before
  any screening employee ships.
- "GO per field" turns each field into a sourced report with the state laws and registrar procedures checked.
