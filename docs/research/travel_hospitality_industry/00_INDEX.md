# The travel & hospitality industry across the world - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A TRAVEL AND HOSPITALITY INDUSTRY AI EMPLOYEES"*. Nineteenth in the series. Travel and hospitality here means: hotels,
resorts, homestays, hostels and short-stay hosts; restaurants, cafes, cloud kitchens, catering and bars; travel agencies, tour operators, DMCs,
OTAs and guides; airlines, airports, railways, buses, cabs and cruise; events, MICE and weddings; attractions, theme parks, heritage and
wildlife tourism; tourism boards and regulators; and the travellers and guests themselves. Logistics (goods), real estate and sports tourism
are in other registers (cross-referenced).

**8 fields, 116 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Rules named are from memory and
  **must be re-checked on primary text per country and state** before any desk is built: in India the Ministry of Tourism's approval and
  classification schemes, state tourism rules, the Foreigners Act obligations to report foreign guests (Form C / FRRO reporting), police
  guest-register norms, GST slabs on room tariffs and food, state excise/liquor licences, FSSAI licensing and hygiene, fire and building
  NOCs, the DGCA passenger charter and refund rules, IRCTC and railway agent rules (Tatkal windows, ticket-transfer limits), travel
  insurance and visa/e-visa rules, forest and wildlife permit rules, adventure-sport safety guidelines, tourist-guide licensing; abroad
  IATA/NDC and GDS norms, EU Package Travel Directive, ADA and equality accessibility duties, PCI DSS (card data must never enter chat or the
  model), GDPR/DPDP for passport and guest data, work-time and tip laws for staff.
- **Already in Hoola** (extend, do not rebuild): **Travel agent** (`travel_work`: trip plans, train/flight/hotel comparison, papers, Tatkal /
  check-in reminders; **bookings and payments on her tap**; tools `travel`, `travel_dekho`, `order_karo`), **Tour guide** (`tour_work`: enquiry
  to booking, group file, day plan, safety and weather, headcount, intro script, licence reminders; confirmations, guest messages, refunds,
  discounts and spends on her yes), **Homestay host** (`homestay_work`: rooms, booking calendar with no double booking, OTA mail/calendar
  files, guest ID in the Locker, Form C, housekeeping, advance/balance UPI links, accounts), the `restaurant` / tiffin front-desk kind (menu and
  prices, delivery area, table booking, large orders on the owner's yes), `server/app/travel/` (service, rules, adapters, WIRING), Maps (route
  matrix, places, nearby, Street View links), Khata, PAISA, WhatsApp opt-in, voice calls, `appmaker`, HYPERFRAMES/Avatar films (property and
  tour films), the website builder (hotel and tour sites, booking forms, galleries), COUPON/STOCK/DELIVERY (restaurant and shop engines),
  Pehchaan Locker (masked guest IDs), the Bazar connectors (cab, ONDC, UPI) and ENGINE pieces from the logistics register for fleets. Roles with `*`
  exist in some form.

## The findings that shape every travel & hospitality desk
### 1. The licence belongs to the property, the operator and the guide; money and safety are the red lines
Ladder as before: **A** admin/prepare, **B** assist (compare / plan / draft / flag for a named person), **C** reserved.
Reserved here: booking or cancelling and taking payment (only on the customer's or owner's explicit tap through official rails; never hold card data),
overbooking decisions that bump a guest, refund and compensation decisions, safety clearances (fire, lifts, adventure activity, food safety
release, structural), police/FRRO guest reporting filings (by the licensee on tap), alcohol service decisions (age/intoxication), visa advice
as an agent, guiding or driving duties, and anything involving a minor's custody or a guest's ID beyond the lawful use. **The AI plans,
compares, remembers, reminds and drafts; the owner, manager, chef, pilot and guide decide and act.**

### 2. Travel is a research-and-trust problem for guests and a utilisation problem for operators
Guests drown in options, hidden fees, fake reviews, scams, visa rules and last-minute changes. Operators live on occupancy, rate, repeat
business, review scores, staffing, and food cost. The AI is strong at the **comparison, itinerary, document and reminder** work, and at the
operator's rate/occupancy/waste dashboards. It must show prices with the *total*, the rules with the *source and date*, and say "I cannot
see live availability" when it cannot.

### 3. The industry runs on shifts, seasons and thin margins; hospitality labour is the product
Rosters, no-shows, tips, overtime, training, high turnover, seasonal peaks, and guest-facing emotional labour. AI should reduce
admin and risk (rostering, onboarding, compliance), not monitor or score staff in ways that harm them. Staff safety (night work, harassment
by guests, food safety, heat in kitchens) is part of the design.

### 4. Safety, health and responsible-tourism are core
Food safety (FSSAI/HACCP), fire and evacuation, water safety, adventure risks, altitude and heat, wildlife-human conflict, women's solo travel
safety, accessibility, child protection (trafficking and exploitation in tourism), over-tourism and waste. Every employee carries a safety
rule set, and high-risk activities are always supervised by certified humans.

### 5. Payments, ID and personal data are sensitive; official channels only
Passport, Aadhaar, visa, health declarations, payment cards, travel patterns. Hoola's rules: IDs only in the Pehchaan Locker with masked references,
no PIN/OTP/CVV/card number in chat, payments only through official gateways on the user's tap, no scraping of OTAs/airline sites against terms,
and no storing of data longer than the lawful purpose requires.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [G] guest/traveller, [A] travel agent/tour operator/DMC/OTA/guide, [H] hotel/resort/homestay/hostel, [R] restaurant/cafe/cloud kitchen/catering, [T] transport/airline/airport/rail/cab/cruise, [E] events/MICE/weddings/attractions, [B] tourism board/regulator/community.

### 1. Trip planning & guest-side travel  [G]
1. * Trip Planner (existing Travel agent) - destinations, season, budget, group, pace, interests; day-wise itinerary with realistic timings, buffers, alternatives and source dates; **bookings only on the user's tap** - A - traveller
2. Flight/Train/Bus/Cab Comparer - options from official sources and user-provided quotes with total cost (baggage, seats, meals, change fees), timings, risk of misconnect; fare rules summarised; Tatkal and booking-window reminders - A - traveller
3. Stay Finder & Comparer - hotels/homestays by location, safety, reviews analysis (fake-review caution), amenities, cancellation terms, true cost with taxes and fees; maps distance to plans - A - traveller
4. Travel Document Checklist (passport validity, visa/e-visa, vaccinations, insurance, forex, local permits like ILP/forest, children's documents, entry rules; **official sources cited with date; embassy confirms**) - B - traveller
5. Visa Application Preparer (document packing, forms data, photos, appointment slots; filing and fees on the user's tap; **no visa-approval promises**) - B - traveller
6. Itinerary Organiser (bookings in one timeline, tickets, vouchers, confirmations from mail with consent; offline copy; share with family) - A - traveller
7. Trip Reminder & Check-in Agent (web check-in windows, baggage limits, airport time, train platform, hotel check-in, weather) - A - traveller
8. Disruption Assistant (delays/cancellations: rights under airline/rail rules, rebooking options, hotel extensions, refund and claim drafts; **carriers decide**) - B - traveller
9. Budget & Expense Tracker (trip budget, currency conversion, split with friends, receipts, settlement UPI cards on tap) - A - traveller
10. Local Guide Companion (voice/offline: phrases, etiquette, festivals, scams to avoid, food guide with dietary needs, public transport, safety tips by area) - A - traveller
11. Solo & Women Traveller Safety Companion (check-ins with trusted contacts by consent, area advisories from official sources, safe-transport tips; **emergency numbers; no false guarantees**) - B - traveller
12. Family & Senior Travel Planner (pace, accessibility, medical needs, rest breaks, child-friendly options, insurance, wheelchair access info) - A/B - traveller
13. Pilgrimage & Religious Travel Assistant (yatra rules, darshan slots via official sites on tap, accommodation by trust, crowd calendars, health advisories) - A - pilgrim
14. Adventure & Outdoor Trip Planner (trek difficulty, altitude acclimatisation, permits, certified operators check, gear list, weather windows, emergency plans; **operators certify safety**) - B - traveller
15. Business Travel Copilot (policy-compliant options, expense rules, meeting-based scheduling, visas, duty-of-care alerts; **approver decides**) - B - traveller / travel desk
16. Travel Insurance Explainer (cover types, exclusions, claim documents, pre-existing conditions; **insurer decides claims**) - A/B - traveller
17. Travel Scam Detector (fake booking sites, taxi/tout scams, rental-deposit scams, fake tickets; official channel pointers) - A/B - traveller
18. Sustainable & Responsible Travel Advisor (low-impact routes, local businesses, waste, wildlife ethics, cultural respect, carbon estimates with ranges) - A - traveller
19. Post-trip Memory Maker (photo albums, trip videos with HOOLA FRAMES, journal, review drafts honest; consent for faces) - A - traveller

### 2. Travel agencies, tour operators, DMCs & guides  [A]
20. * Travel Agent's Desk (existing) - customer enquiries to quotes, itinerary packs, document checklists, reminders, supplier follow-ups; payments on tap - A - agent
21. Tour Package Builder (costing by day with supplier rates, margins, taxes/TCS, group size breakpoints, optional extras; PDF/WhatsApp quote) - A/B - tour operator
22. * Tour Guide Assistant (existing) - enquiry to booking, group file, day plan, safety and weather, headcount, intro script, licence reminders - A - guide
23. Supplier & Rate Manager (hotels, transport, activities: rate sheets, contract validity, allotments, release dates, payment terms) - A - contracting manager
24. Group Tour Operations Desk (rooming lists, transport manifests, meal counts, dietary and medical flags, tour manager briefs, daily reports) - A - operations manager
25. Quote-to-Booking Converter (versions, follow-ups, deposit schedules, terms acceptance, confirmation vouchers; **payment on customer's tap**) - A - sales
26. Cancellation & Refund Calculator (supplier penalties, customer policy, GST/TCS adjustments; **refund approval by manager**) - A/B - accounts
27. DMC Local Experience Curator (verified local activities, safety ratings from operators, language options, accessibility) - B - destination manager
28. Corporate & Incentive Travel Planner (budget bands, group dynamics, venues, activities, branded elements, compliance) - B - MICE planner
29. Wedding & Destination Event Travel Coordinator (guest travel blocks, arrivals/departures, shuttles, room allocations, RSVP data) - A - event coordinator
30. Visa & Documentation Desk for Agents (checklists per country/profile, appointments, refusals analysis; **consular decision not promised**) - B - visa executive
31. Tour Guide Training Coach (history/culture scripts with sources, storytelling, safety, first aid, languages; licensing prep; Guru Sahayak) - A - guide
32. Review & Reputation Manager (collect reviews with consent, reply drafts, issue patterns) - A - owner
33. Travel Content Producer (itineraries, blogs, reels, destination films; rights-cleared; honest claims) - B - marketing
34. Agency Accounts & GST/TCS Assistant (commission, markups, supplier payables, TCS on overseas packages, invoices; **CA files**) - B - accountant
35. OTA/Marketplace Operations Assistant (listings sync, rate parity checks, content quality, customer service; official APIs only) - A - marketplace ops
36. Fraud Screener for Travel Sellers (stolen-card patterns, fake enquiries, chargeback evidence) - B - risk analyst

### 3. Hotels, resorts, homestays & hostels  [H]
37. * Homestay Host Assistant (existing) - rooms, booking calendar, OTA files, guest ID in Locker, Form C, housekeeping, advance/balance UPI links, accounts - A - host
38. Hotel Front-desk Assistant (enquiries, bookings, check-in/out, guest messages in many languages, local info, complaints routing) - A - front-office manager
39. Reservation & Channel Manager Assistant (inventory across OTAs/direct, overbooking guard, rate parity, stop-sell rules; **rate changes on approval**) - A/B - reservations manager
40. Revenue Management Analyst (pickup curves, comp-set rates from lawful sources, demand events, pricing recommendations with ranges; pylab; **GM approves rates**) - B - revenue manager
41. Housekeeping Planner (room status, cleaning sequence, staffing by occupancy, linen, lost-and-found, inspections checklists with photos) - A - housekeeping manager
42. Maintenance & Engineering Assistant (work orders, preventive schedules for HVAC, lifts, water, power, DG, safety systems; vendor SLAs) - A - chief engineer
43. Guest Experience Concierge (voice/WhatsApp: restaurant booking, tours, cabs, laundry, special requests, local events; escalates; guest preferences with consent) - A - concierge
44. Guest Profile & Loyalty Manager (preferences, stay history, special occasions, consent-based offers, points rules) - A - guest relations
45. Guest Complaint & Service Recovery Assistant (log, empathy scripts, compensation within approved ranges; **manager approves compensation**) - B - duty manager
46. Police/FRRO Guest Reporting Assistant (Form C and guest register preparation, deadlines, checklists; **licensee files**) - A/B - hotel manager
47. Hotel Security & Safety Officer's Assistant (fire drills, CCTV retention policy, incident logs, key control, women-safety protocol; **security head decides**) - B - security manager
48. F&B Operations Assistant for Hotels (banquet orders, room service tickets, stock, menu costing, waste logs) - A - F&B manager
49. Events & Banquets Sales Assistant (enquiry handling, hall availability, quotes, BEO sheets, vendor coordination) - A - banquet sales
50. Hotel HR Assistant (rosters, shift swaps, training matrix, onboarding, compliance with wage/hours laws; wellbeing checks) - A - HR manager
51. Procurement & Inventory Assistant (supplier comparison, par levels, GRN, wastage, quality checks) - A - purchase manager
52. Hostel/Dorm Manager's Assistant (bed-level booking, check-in KYC, quiet hours, lockers, community events, curfew rules) - A - hostel manager
53. Resort Activities Coordinator (schedules, guide assignments, equipment checks, safety briefings, waivers) - A/B - activities manager
54. Spa & Wellness Desk (treatment booking, therapist rosters, consent forms, contraindication intake; cross-ref fashion/beauty register) - A - spa manager
55. Property Manager for Short-stay Portfolios (multi-listing sync, cleaning crews, owner statements, damage claims evidence) - A - portfolio manager
56. Sustainability Operations Assistant (energy/water/waste tracking, certifications evidence, towel/linen programmes, local sourcing) - A/B - sustainability manager
57. Hotel Finance & Night-audit Assistant (daily revenue reconciliation, city ledger, GST slabs, deposits, bad-debt aging; Tally; **GM/accountant signs**) - B - night auditor
58. Hotel Brand & Marketing Assistant (OTA content, direct-booking campaigns, photos, reviews management, local partnerships; claims honest) - B - marketing manager
59. Hospitality Training Coach (service standards, languages, safety, upselling ethics; role-play voice) - A - trainer

### 4. Restaurants, cafes, cloud kitchens, catering & bars  [R]
60. * Restaurant Front Desk (existing restaurant/tiffin kind) - menu and prices, table booking, delivery area, timing; large orders on owner's yes - A - restaurant owner
61. Menu Engineer & Costing Assistant (recipe costing, margins, price tests, contribution mix; allergen labelling support) - B - chef / owner
62. Kitchen Production Planner (prep lists by forecast, par stock, batch scheduling, station load) - A - head chef
63. Inventory & Wastage Controller (daily stock, FEFO, spoilage logs, supplier orders, theft flags) - A - kitchen manager
64. Food Safety & HACCP Assistant (temperature logs, cleaning checklists, supplier approvals, allergen matrix, FSSAI renewals, pest-control records; **FBO/food-safety supervisor responsible**) - B - food-safety supervisor
65. Order Aggregator Manager (Zomato/Swiggy/ONDC-style: official partner APIs, menu sync, rating issues, payout reconciliation) - A - restaurant owner
66. Table & Reservation Optimiser (turns, no-show handling, deposits where lawful, waitlist messaging, party sizes) - A - manager
67. Staff Roster & Tips Assistant (shift patterns, tip-pool rules, wage compliance, training, leave) - A - manager
68. Catering & Event Menu Planner (guest counts, dietary needs, quantities, staffing, equipment, logistics, quotes) - A/B - caterer
69. Cloud Kitchen Network Manager (multi-brand menus, prep sharing, rider SLAs, outlet performance, delivery radius via Maps) - A - operations head
70. Bar & Beverage Controller (stock variances, pour costs, licence conditions, age-check procedures, responsible-service rules; **service decisions by staff**) - B - bar manager
71. Customer Loyalty & Feedback Assistant (opt-in WhatsApp offers, reviews, recovery of unhappy diners, birthday offers) - A - owner
72. Street Food & Small Eatery Copilot (daily sales via UPI, best hours, raw material, FSSAI basics, cash-leak checks) - A - vendor
73. Chef's Recipe Assistant (scaling, substitutions, techniques, seasonal ideas, nutrition estimates labelled approximate; allergens flagged) - A - chef
74. Restaurant Delivery & Dispatch Assistant (own riders, batching, ETA, packaging, complaints) - A - owner

### 5. Transport: airlines, airports, rail, bus, cab & cruise  [T]
75. Airline Customer Care Assistant (booking changes within fare rules, baggage tracing, disruption messages, compensation rules explained; **agents approve exceptions**) - A/B - customer-care lead
76. Airport Passenger Services Guide (wayfinding, queue times from official feeds, lounges, accessibility services, lost-and-found) - A - airport authority
77. Crew & Rostering Assistant (duty-time legality checks, pairings, reserve use, training expiries; **crew controller decides**) - B - crew control
78. Airline Network & Schedule Analyst (demand forecasts, load factors, route profitability scenarios; pylab) - B - network planner
79. Railway/Bus Operator Assistant (timetables, platform info, crowd alerts, complaints, ticket-checks data; operations by railway staff) - A - operator
80. Cab/Ride-hailing Fleet Copilot (driver documents, shifts, maintenance, earnings, safety incident log, route planning; see logistics fleet) - A - fleet owner
81. Airport Ground-handling Coordinator (turnaround checklists, equipment, baggage flow; **safety officers rule**) - B - ground-ops manager
82. Cruise & Ferry Hospitality Assistant (itineraries, shore excursions, muster drills, dietary and medical manifests, onboard services) - A/B - cruise director
83. Aviation Safety Reporting Assistant (voluntary report intake, classification, trend dashboards; **safety manager owns investigations**) - B - safety manager
84. Maintenance Records Assistant for Aircraft/Buses (task cards, parts, airworthiness directive tracking; **certifying engineer signs**) - B - maintenance control
85. Mobility-as-a-Service Planner (multimodal door-to-door options, accessibility, tickets integration with user's tap) - A - traveller / transit authority

### 6. Events, MICE, weddings & attractions  [E]
86. Event Planner's Assistant (brief, budget, vendors, timeline, run of show, risk plan, permits, volunteer rota) - A - event manager
87. Venue Finder & Negotiation Prep (capacity, layout, catering rules, acoustics, parking, accessibility, quotes comparison) - A - planner
88. Wedding Planner Copilot (guest list, RSVPs, rituals schedule, vendors, travel blocks, budget, cultural customs by community) - A - wedding planner / family
89. Conference/Exhibition Operations Assistant (registration, badges, agenda, speakers, sponsors, floor plans, lead capture, feedback) - A - organiser
90. Attraction & Theme-park Operations Assistant (ticketing, queues, ride maintenance logs, crowd control, lost children protocol; **safety officer decides**) - B - park manager
91. Museum/Heritage Visitor Guide (audio tours in many languages, exhibit explanations with sources, accessibility, school programmes) - A - curator
92. Wildlife & Eco-tourism Assistant (permit slots on official portals via tap, zone rules, safari etiquette, conservation info, local guide linkage; **forest dept rules**) - B - eco-lodge / guide
93. Festival & Mela Crowd Planner (crowd estimation, flow, medical posts, lost-and-found, water, sanitation, emergency routes; **authorities approve**) - B - event authority
94. Entertainment Venue Ticketing Assistant (seat maps, pricing tiers, anti-bot checks, refunds, accessibility) - A/B - box office
95. Casino/Gaming Hospitality Compliance Guard (where legal: ID checks, self-exclusion, responsible-gaming; **no promotion**) - B - compliance officer

### 7. Tourism boards, regulators & community  [B]
96. Destination Marketing Assistant (campaigns, itineraries, influencers (disclosure), data on markets; honest claims; multilingual) - B - tourism board
97. Tourism Statistics & Insights Analyst (arrivals, occupancy, spending, seasonality, satisfaction; official data; pylab) - A - tourism department
98. Tourist-guide & Operator Licensing Assistant (applications, document checks, renewals, complaints; **licensing authority decides**) - B - licensing officer
99. Hotel Classification & Inspection Assistant (checklists, scoring templates, photos, reports; **inspectors decide**) - B - inspection team
100. Tourist Safety & Grievance Helpline (multi-language intake, routing to police/health/transport, follow-up; escalation to humans) - A/B - helpline lead
101. Community-based Tourism Enabler (homestay clusters, craft sales, guide training, fair pricing, booking tools, grant schemes) - A - NGO / village committee
102. Heritage Conservation & Carrying-capacity Planner (visitor flow limits, wear monitoring, seasonal management scenarios) - B - site manager
103. Responsible-tourism Reporter (waste, water, energy and community benefit indicators; evidence trail) - A/B - destination manager
104. Crisis Communication Assistant (floods, disease outbreaks, protests, security incidents: advisory drafts with official sources; **spokesperson approves**) - B - tourism authority
105. Child-protection in Tourism Guard (training, reporting channels, operator codes; flags concerns to humans; no profiling of travellers) - B - protection officer
106. Accessible Tourism Auditor (venue accessibility checklists, photos, route barriers; recommendations; **auditors certify**) - B - accessibility consultant

### 8. Platforms, technology & business functions
107. Booking Engine & Payments Assistant (website bookings, UPI/gateway links, deposits, invoices, reconciliation; PCI scope kept off the model) - A - operator
108. Rate-Shopper & Competitive Intelligence (lawful sources, user-supplied data, public listings; no scraping against terms) - B - revenue analyst
109. Review Intelligence Analyst (themes across platforms, response drafts, escalation) - A - owner / GM
110. Dynamic Pricing Guardrail Auditor (fairness, consumer-law checks, surge caps, discrimination tests) - B - compliance
111. Travel API Integration Assistant (GDS/NDC/OTA/ONDC schemas, test payloads, certification checklists) - A/B - integration lead
112. Customer Data & Privacy Steward (passport/ID handling, retention, consent, access requests, breach drills) - B - DPO
113. Travel Tech Startup Copilot (problem validation, supplier access, compliance map, grants, pilot design) - A/B - founder
114. Hospitality Education Tutor (hotel operations, culinary basics, tourism geography, service excellence; Guru Sahayak) - A - student
115. Multilingual Voice Concierge (Hindi, Marathi, Tamil, English etc. for hotels, tours, taxis; offline phrase packs) - A - operator
116. Sustainable Procurement Advisor (local, seasonal, certified sourcing; supplier verification; food miles estimates) - A/B - purchasing

## NEVER an AI Employee (tier C)
Take payment, store card data, or confirm/cancel a booking without the customer's or owner's explicit tap through official rails; bump or
deny a guest, or decide refunds/compensation outside approved ranges; clear a fire, lift, food-safety or adventure activity for operation; file
guest/police/FRRO reports as the licensee; serve alcohol or decide intoxication; promise visas, refunds or safety; guide or drive tourists; act on
a minor's custody or location; surveil staff or guests beyond lawful purpose; scrape OTAs/airline sites against terms; manipulate prices with
dark patterns or discriminatory dynamic pricing; share passport/ID/guest data without lawful consent; promote gambling.

## Suggested build order
1. **Wave 1 - extend the three live employees and add the owner-copilots (tier A)**: 1, 2, 3, 6, 7, 9, 20, 22, 37-39, 41, 43, 60, 61, 63, 66, 71 + 25, 26, 72, 107.
2. **Wave 2 - operators and planners with a named human**: 4, 8, 10, 21, 23-24, 29, 40, 42, 44-46, 48-51, 62, 64, 65, 67, 68, 86-89.
3. **Wave 3 - safety, regulated or sensitive**: 5, 11, 14, 15, 30, 46, 47, 53, 64, 70, 77, 83, 84, 90, 93, 95, 105.
Fit to Hoola: department **"Travel & Hospitality"**; three employees (Travel agent, Tour guide, Homestay host) and the restaurant front-desk already exist,
so Wave 1 is the **second most mature starting point** after telecom: connect them into complete suites (the guest's trip planner and the host's property
manager are the two sides of one marketplace). Reuse Maps (itineraries, nearby, route matrix, Street View links), `server/app/travel` rules and adapters,
Pehchaan Locker (masked guest IDs), Form C reminders, PAISA and UPI cards on tap, Khata, WhatsApp opt-in and voice (concierge in Indian languages),
`appmaker` (hotel/guest and restaurant apps), COUPON/STOCK/DELIVERY engines (restaurant ordering), HYPERFRAMES and Avatar Films (property and tour films),
pylab (pricing, costing, demand), approval cards for every booking, refund, rate change and filing.
**Best first pilots**: (a) a **homestay/hotel owner** (37-39, 41, 43, 46) with a **tour guide / small travel agent** (20-22, 25) in one destination cluster - the three existing
employees become a coherent product; (b) a **restaurant or cloud-kitchen owner** (60-66, 71); (c) a **consumer trip planner** (1-9, 17). Airlines, airports and large hotel chains come later:
integrations, safety regulation and procurement are heavy.

## Open questions for the owner
- Which side first: **travellers** (B2C), **homestay/hotel owners**, **travel agents and guides**, **restaurants/cloud kitchens**, or **transport and attractions**? I'd start with the
  homestay + guide + small agent cluster because three employees already exist.
- Data and inventory: live availability requires official partner APIs (OTAs, IRCTC, airlines, ONDC); which partnerships should Newtika pursue first? Without them the AI plans and compares but cannot confirm real-time inventory.
- Payments and ID: confirm that card data never touches Hoola (hosted gateway only), guest IDs stay masked in the Locker, and Form C/FRRO filings stay the licensee's tap.
- Safety positioning: confirm that adventure/wildlife/pilgrimage features always route through certified operators and official permits and carry no safety guarantees.
- Which destinations/languages first (Konkan, Goa, Himachal, Rajasthan, Kerala; Hindi/Marathi/English)? Local rule packs and place data are maintained assets.
- "GO per field" turns any field into a sourced report with tourism rules, FSSAI, DGCA, Form C and state excise checked on primary text.
