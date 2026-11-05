# The fashion & beauty industry across the world - AI Employees register

Owner's ask (4 Nov 2026): *"NOW A FASHION AND BEAUTY INDUSTRY AI EMPLOYEES"*. Twelfth in the series. Fashion = apparel, footwear,
accessories, jewellery, textiles, luxury and fast fashion, tailoring and boutiques, design schools, retail and e-commerce.
Beauty = cosmetics and personal care brands, salons and spas, hair and skin services, makeup artistry, grooming, wellness-adjacent
services, and the creator/influencer ecosystem around both.

**11 fields, 123 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Laws and standards
  named are from memory and **must be re-checked on primary text per country** before any desk is built: India's Drugs and
  Cosmetics Act + Cosmetics Rules 2020 (import registration, labelling, BIS standards), Legal Metrology (Packaged Commodities)
  Rules, BIS hallmarking for gold/silver jewellery, textile/garment labelling and care-label norms, ASCI advertising code and CCPA
  endorsement and dark-pattern guidelines, Consumer Protection Act and e-commerce rules; EU Cosmetics Regulation 1223/2009 (CPNP,
  safety report, responsible person, animal-testing ban), US MoCRA 2022 and FDA labelling, EU textile labelling and the coming
  Digital Product Passport / ecodesign rules, REACH and restricted substances (azo dyes), supply-chain due-diligence rules,
  garment-factory social standards (SA8000, WRAP, BSCI), trademark/design/copyright law, and platform marketplace policies.
- **Already in Hoola** (extend, do not rebuild): `tailor` ("Darzi sahayak": orders, measurements per customer, trial and
  delivery dates, 'ready' messages, price on her yes), the `salon` front-desk role (30-min slots, services and prices, stylists,
  booking rules), Create Studio (Image, Video, Brand kit, posters, AI casting, My creations), HOOLA FRAMES, Avatar Films
  (product films, 9:16 reels), HOOLA PRINT (lookbooks, catalogues), `shop`/Bazar connectors and the website `shop` (cart, UPI QR,
  stock), Khata (udhaar), social media manager (Instagram/Facebook/LinkedIn/YouTube), WhatsApp opt-in campaigns, COUPON/STOCK/DELIVERY
  engines, `appmaker` (store apps), Maps, vision review. Roles with `*` exist in some form.

## The findings that shape every fashion & beauty desk
### 1. Taste is human; the safety, claims and records are not
Ladder as before: **A** admin/prepare, **B** assist (draft / check / suggest for a named human), **C** reserved.
Reserved here: design sign-off, brand voice and creative direction, product safety assessment (cosmetic safety assessor /
qualified person), regulatory notification and licence applications, any cosmetic or treatment claim that is medical,
chemical or laser procedures, patch-test decisions, hallmark certification, quality approval of a production lot, pricing
and discount approvals, influencer contracts and payments, and anything that touches a person's body (hair, skin, nail, makeup,
tattoo, piercing, threading, waxing, massage). **The AI suggests, tracks and prepares; the designer, formulator, stylist and
dermatologist decide and perform.**

### 2. Fashion is a trend-to-inventory business with thin margins and huge waste
Fast cycles (design drops, seasonal lines), size/fit problems (return rates 20-40% online), unsold stock, markdown timing,
sourcing delays, factory compliance, and counterfeit/copy risk. Biggest wins: demand and size-curve forecasting, fit
guidance, returns reduction, inventory allocation, markdown scheduling, supplier tracking and tech packs. All tier A/B.

### 3. Beauty is a claims, safety and trust business
Every ingredient list, shade, SPF/anti-ageing claim and "dermatologist tested" statement is regulated. Allergic reactions,
counterfeit products, unlicensed salon treatments, and misleading before/after images are the harm. The AI must show
which rule or evidence supports a claim and **block** unsupported claims, disclose ads/influencer ties, and never diagnose skin
or hair disease (that is dermatology: Hoola's healthcare rules apply, AI skin analysis can itself be a medical device).

### 4. The service side (salons, tailors, boutiques) is appointment-and-craft, run on WhatsApp
Millions of one-to-ten-person businesses: bookings, regulars, advances, trial dates, measurements, festival rush, consumables stock,
staff commission, UPI collections, ratings. Hoola's existing front-desk and Darzi Sahayak are exactly this; the register extends them
with what the owner actually loses sleep over: no-shows, late deliveries, stock-outs, staff leaving with clients, cash leakage.

### 5. Body image, consent and cultural care are part of the design
Retouching, "beauty filters", sizing language, skin-tone representation and age-targeted marketing affect real people. Hoola's
rule: no body-shaming copy, no under-18 targeting for anti-ageing or slimming, labelled retouching in ads (as local law requires),
and a likeness/consent registry for models (same as the film register).

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)

### 1. Fashion design, trend & product development
1. Trend Researcher - runway, street, social, search and sales signals into trend boards with sources and dates, colour and silhouette trends by market; ranges not predictions - A - design head
2. Mood-board & Concept Assistant - references, palettes, fabric ideas, story themes (Create Studio images; **designer curates**) - B - designer
3. Design Sketch Variation Generator - garment/silhouette/pattern variants from the designer's line; originality and look-alike check against public designs - B - designer
4. Pattern Grading & Size Chart Assistant - base block to grade rules by region (S-M-L, EU/UK/US/IN sizes), measurement tables, tolerances - B - pattern master
5. Tech Pack Builder - flats, BOM, trims, stitch details, measurements, labels, packaging, costing rows in a standard format - A/B - merchandiser
6. Fabric & Trim Sourcing Assistant - supplier search from the user's lists, swatch library, MOQ, lead times, price history, sustainability certificates - A - sourcing manager
7. Cost Sheet & Margin Planner - fabric, CMT, wastage, duties, freight, markup; price ladders by market (pylab) - A - merchandiser
8. Sample Tracker - proto, fit, size-set, pre-production, TOP samples; comments, approvals, re-sample counts - A - merchandiser
9. Print & Textile Pattern Designer (repeat tiles, colourways, Indian craft motifs with source credit; **cultural heritage and GI (e.g. Banarasi) rules shown**) - B - textile designer
10. Colour Management Assistant (Pantone/Lab values, lab-dip approvals, dye-lot tracking, colour-fastness test records) - A - technical designer
11. Collection Planner (assortment: categories, price points, drops, depth/width, calendar, buy plan) - B - merchandise planner
12. Costume & Bridal Design Assistant (event brief, culture-specific details like lehenga/saree/sherwani structure, fittings plan) - B - designer
13. Fashion Education Tutor (design theory, pattern-making, textiles, history; Guru Sahayak) - A - faculty
14. Heritage Craft Documenter (artisan techniques, motifs, GI tags, provenance stories; **artisan consent and credit**) - A - NGO / designer

### 2. Manufacturing, sourcing & supply chain (apparel, footwear, textile, leather)
15. Production Planner (orders to lines, capacity, critical path, TNA calendar) - A - production manager
16. Factory Compliance Tracker (SA8000/WRAP/BSCI audits, wages, hours, fire safety, child-labour checks, corrective actions) - A/B - compliance manager
17. Order & Shipment Tracker (PO, ex-factory, booking, ETD/ETA, documents) - A - merchandiser
18. QC Inspection Assistant (AQL sampling plans, defect classification, inspection reports, photo records; **QA signs**) - B - QA manager
19. Material Requirements Planner (BOM explosion, shortage alerts, fabric consumption trends) - A - planner
20. Subcontractor & Job-worker Manager (rates, bundles, payments, wastage) - A - factory owner
21. Wage & Piece-rate Calculator (bundle tickets, incentives, PF/ESI; pay on tap) - A - factory accounts
22. Restricted-substances (RSL) & Chemical Compliance Checker (REACH/azo/formaldehyde, test reports expiry) - B - sustainability manager
23. Export Documents Assistant (invoice, packing list, certificates of origin, GSP/FTA, drawback; CHA files) - A/B - export manager
24. Leather & Footwear Technical Assistant (last specs, hide grading, tanning compliance) - B - technical manager
25. Hallmarking & Jewellery Production Tracker (purity, BIS HUID workflow, weight loss/wastage, karigar ledger; **hallmark by assaying centre**) - A/B - jeweller
26. Gemstone & Diamond Certificate Checker (certificate numbers, grading lab references, mismatch flags; no appraisal of value) - B - jeweller
27. Textile Mill/Spinning Planner (yarn counts, loom schedules, process yields) - A - mill manager
28. Digital Product Passport Compiler (materials, origin, care, recyclability data for EU rules) - A/B - sustainability lead

### 3. Retail, merchandising & e-commerce (fashion)
29. * Boutique Assistant (extends Darzi Sahayak / shop) - catalogue, WhatsApp orders, stock, size availability, customer measurements, delivery - A - boutique owner
30. Merchandise Allocation Planner (store/size/colour allocation, replenishment, pylab) - B - planner
31. Size & Fit Advisor - body measurement inputs (user-entered), brand size charts, review-based fit notes; "usually runs small" with data; no body judgement - B - customer / merchandiser
32. Returns Reducer (return reasons, sizing mismatches, fabric/colour expectation gaps, fix suggestions) - A - e-commerce head
33. Markdown & Pricing Optimiser (price elasticity ranges, markdown calendar, discount caps; **approval by merchandiser**) - B - merchandise head
34. Product Listing Writer (titles, bullets, SEO, size/care details; claims checked vs spec sheet) - A - catalogue team
35. Fashion Photography Planner (shot lists, model/location/studio schedule, AI-generated lifestyle images labelled as such) - B - creative producer
36. Virtual Try-on Assistant (garment visualisation on user-provided photo with consent; deletes images; "visual guide, not exact fit") - B - customer
37. Visual Merchandising Assistant (store layout, window themes, planograms, seasonal changes) - B - VM head
38. Omnichannel Order Router (ship-from-store, split shipments, stock accuracy) - A - ops
39. Marketplace Manager (Myntra/Amazon/Ajio-style: official seller APIs only; listings, order sync, settlement reconciliation) - A - marketplace manager
40. Customer Stylist (wardrobe organiser from user's own photos, outfit suggestions by occasion, budget, weather, culture; nothing bought without user's tap) - A - customer
41. Gifting & Occasion Planner (festival, wedding, trousseau checklists, vendor timelines) - A - customer / planner
42. Resale & Rental Platform Assistant (authenticity checks by seller documents, condition grading photos, damage deposit logic) - B - platform trust team
43. Counterfeit Detector (brand authentication checklists from labels/stitching/serials; flags, not verdicts) - B - brand protection

### 4. Luxury, jewellery & accessories
44. Client Relationship Manager (private clients: preferences, sizes, occasions, anniversaries, discreet follow-ups; consent-based) - A - client advisor
45. Bespoke Order Tracker (custom pieces: measurements, materials, approvals, ateliers, delivery) - A - atelier manager
46. Gold & Metal Rate Tracker (daily rates from official/exchange sources, making-charge calculators, GST, old-gold exchange math) - A - jeweller
47. Gold Savings Scheme Manager (instalment tracking, redemption rules, legal scheme compliance; **regulated deposit-type rules flagged**) - B - jeweller + legal
48. Certification & Provenance Vault (hallmark, GIA/IGI, invoice, warranty; QR provenance records) - A - jeweller
49. Insurance & Valuation Reminder (periodic valuation dates; **appraisal by certified valuer**) - A - owner
50. Watch/Bag Authentication Intake Assistant (serials, images, documents; sends to human authenticator) - B - authenticator

### 5. Cosmetics & personal-care product development (beauty brands)
51. Formulation Idea Assistant (ingredient function tables, compatibility notes from literature; **formulator designs and tests**) - B - formulation chemist
52. INCI Ingredient List Builder (descending order rules, naming normalisation, allergen flags) - B - regulatory + formulator
53. Cosmetic Safety Report Assistant (exposure calculations, margin of safety worksheets, toxicology data compilation; **safety assessor signs**) - B - safety assessor
54. Stability & Challenge Test Tracker (storage conditions, time points, preservative efficacy, packaging compatibility) - A - QC
55. Claims Substantiation Checker (every claim mapped to test/evidence: SPF, hypoallergenic, dermatologist-tested, vegan, cruelty-free; ASCI/EU claim criteria) - B - regulatory + marketing
56. Regulatory Dossier Assistant (EU CPNP, US MoCRA facility registration/listing, India import registration/labelling; **notification by responsible person**) - B - regulatory manager
57. Label & Packaging Compliance Reviewer (mandatory fields, batch/expiry, net quantity, warnings, languages, symbols) - B - regulatory
58. Batch Record & QC Assistant (GMP-for-cosmetics ISO 22716 records, deviations, release checklist; **QA releases**) - B - QA manager
59. Shade-range & Skin-tone Inclusivity Auditor (coverage across undertones, test-subject diversity records, naming sensitivity) - B - product manager
60. Sustainability & Ingredient Sourcing Assistant (palm oil, mica, microplastics, packaging recyclability, supply transparency) - B - sustainability head
61. Contract-manufacturing Coordinator (briefs, MOQ, sample rounds, quality agreements, timelines) - A - brand ops
62. Adverse-reaction (Cosmetovigilance) Intake (customer complaints, severity triage, regulator reporting prep; **medical advice referred to doctors; safety officer decides**) - B - safety officer
63. Fragrance & Allergen Documentation Assistant (IFRA limits tables, declared allergens, SDS) - B - perfumer + regulatory

### 6. Beauty retail, brands & e-commerce
64. Beauty Advisor (concern-based guidance: dryness, shade matching from user photo, routine building; not medical, patch-test advice, no diagnosis, ingredient clash warnings) - B - customer (dermatologist for medical)
65. Shade-matching Assistant (skin-tone estimate from photo with lighting-calibration caveat; multiple choices; no skin-tone ranking) - B - customer
66. Routine Planner (AM/PM sequence, actives spacing, SPF reminders, product shelf-life/PAO tracker) - A - customer
67. Counterfeit & Grey-market Watcher (marketplace listings vs authorised distributor list) - A/B - brand protection
68. Beauty Subscription Box Manager (curation rules, sample logistics, churn analysis) - A - brand ops
69. Retail Counter Training Coach (product knowledge, consultation scripts, inclusivity) - A - training head
70. Inventory & Expiry Manager (batch/expiry, FEFO, near-expiry offers, recalls; Hoola warehouse tools) - A - ops
71. Recall Handler (affected batches, notices, returns logistics, authority reporting drafts; **recall decision human**) - B - QA/regulatory
72. Loyalty & CRM Assistant (opt-in, routine reminders, birthdays, repurchase cycles) - A - CRM head

### 7. Salons, spas, barbers & grooming services  (extends the salon front-desk)
73. * Salon Front Desk (existing) - services, prices, stylists, bookings, no-show handling - A - salon owner
74. Appointment Optimiser (stylist skills, service durations, overlaps, buffer, resource constraints like chair/basin/laser room) - A - salon manager
75. Client Profile & Treatment Memory (formulas, colour history, sensitivities, patch-test dates, before/after photos with consent) - A - stylist
76. Patch-test & Aftercare Reminder (hair dye, chemical treatments, waxing, facials; follows owner's SOP) - A/B - stylist
77. Package & Membership Manager (prepaid sessions, expiry, rollover, pro-rata refunds, gift cards) - A - salon owner
78. Commission & Payroll Assistant (service-wise commission, tips, advances, leave, UPI settlement) - A - salon accountant
79. Consumables & Product Stock (colour tubes, creams, wax, towels, retail products; usage per service) - A - salon manager
80. Hygiene & Licence Compliance Tracker (sterilisation logs, linen cycles, local trade licence, fire NOC, staff training records) - A - salon manager
81. Treatment Menu & Price Designer (service bundles by cost-to-serve, local competitor ranges; pylab) - B - salon owner
82. Retention Assistant (rebooking reminders by service cycle: haircut 6 weeks, facial 4, colour touch-up 5; WhatsApp opt-in) - A - salon owner
83. Bridal/Event Booking Planner (multi-person schedule, trials, travel, advance, staff roster for rush days) - A - makeup artist / salon
84. Freelance Makeup-artist Assistant (leads, bookings, travel, kit checklist, invoicing, portfolio site) - A - makeup artist
85. Barber/Grooming Queue Manager (walk-ins, tokens, wait time messages) - A - barber
86. Tattoo, Piercing & Nail Studio Compliance Assistant (age checks, consent forms, sterile logs, aftercare sheets; **no under-age procedures; practitioner decides**) - B - studio owner
87. Spa & Wellness Scheduler (treatment rooms, therapist skills, contraindication intake form routed to therapist; **no medical advice**) - A/B - spa manager
88. Laser/Aesthetic Clinic Operations Assistant (booking, consents, maintenance, consumables; **clinical decisions by licensed doctor**) - A - clinic manager
89. Mobile Beauty Service Dispatcher (home visits: routes, kit, safety check-ins, pricing zones; Maps) - A - ops

### 8. Tailoring, boutiques & bespoke craft  (extends Darzi Sahayak)
90. * Darzi Sahayak (existing) - orders, per-customer measurements, trial and delivery dates, 'ready' messages - A - tailor
91. Measurement Capture Assistant (photo/video-guided measurement for tailors, customer-entered fields with sanity checks, previous-order carry-forward) - B - tailor
92. Pattern & Cutting Planner (fabric yardage from measurements and design, cutting layout hints, wastage) - B - master cutter
93. Alteration & Repair Desk (quick-turn jobs, pricing rules, pickup/delivery) - A - tailor
94. Festival-rush Planner (Diwali/Eid/wedding season capacity, deadlines, overtime, advance caps) - A - tailor
95. Karigar/Artisan Ledger (piece-work jobs, embroidery batches, advances, payouts, quality returns) - A - boutique owner
96. Wedding Trousseau Planner (outfit list by ceremony, fabrics, jewellery, accessories, timeline, budget) - A - bride/family
97. Uniform & School/Corporate Garment Order Manager (size lists, bulk quotes, deliveries, reorders) - A - tailor / supplier
98. Home Textile & Furnishing Stitcher Assistant (curtain/sofa covers: measuring sheets, fabric calculator) - A - tailor

### 9. Marketing, media, creators & community
99. Brand Voice & Campaign Planner (seasonal narratives, launch calendars, influencer briefs; Brand kit rules) - B - brand manager
100. Fashion Lookbook & Campaign Producer (HOOLA PRINT + Create Studio images/reels; model consent registry; retouch labelled) - B - creative director
101. Influencer Discovery & Brief Manager (fit scoring by audience data they share, rate cards, content rules, disclosure #ad reminders; **contracts and payments human**) - A/B - marketing head
102. Social Media Manager (existing social desk applied: Reels scripts, product launches, comments triage) - B - social lead
103. Creator Assistant for Fashion/Beauty Influencers (content calendar, brand deal tracker, disclosure checks, media kit, invoicing) - A - creator
104. Review & UGC Analyst (themes in reviews, fit/quality/colour complaints, product insights) - A - product / CX
105. Event & Fashion-show Planner (run of show, designers, models casting, backstage, tickets, sponsors) - A - event producer
106. PR & Media Kit Assistant (press lists, embargoes, product loan tracking) - A - PR
107. Ad Claim Compliance Reviewer (ASCI/CCPA/EU: before/after, endorsements, "100% natural", price claims, sale tags) - B - legal
108. Model & Talent Booking Assistant (casting calls, comp cards, rates, age/hour rules for minors, consent for AI likeness) - A - booker
109. Cultural Sensitivity Checker (religious motifs, attire norms, appropriation risks per market, naming) - B - brand manager

### 10. Business, finance, sustainability & compliance
110. Merchant Finance Assistant (GST invoices for apparel slabs, e-way bills, TDS on commission, settlement reconciliation) - A - accountant
111. Working-capital & Inventory Financing Planner (stock turn, payables, seasonal cash gaps; pylab) - A - owner
112. Brand Protection Assistant (trademark watch, design registrations, copy-listing takedown drafts; **filing by rights holder/counsel**) - B - IP counsel
113. Sustainability Reporter (materials, water, energy, emissions, take-back; sources and uncertainty shown) - A/B - ESG lead
114. Circularity & Take-back Coordinator (collection, repair, resale, recycling partners, credits) - A - sustainability lead
115. Franchise & Store-network Manager (onboarding, royalties, audits, stock rules) - A - franchise head
116. Salon/Boutique Licensing & Compliance Calendar (trade licence, fire NOC, shop & establishment, GST, EPF/ESI, cosmetic licences) - A - owner
117. Data Privacy Assistant (customer photos, skin data, measurements, health sensitivities; DPDP/GDPR consent, deletion) - B - DPO
118. Skin-image & Body-data Guard (blocks storage/training use of body images beyond consent; auto-delete) - B - DPO

### 11. Wellness-adjacent & education
119. Beauty Training Academy Tutor (cosmetology, hair, makeup, nail courses; practical checklists, safety rules; Guru Sahayak) - A - trainer
120. Salon Business Coach (pricing, utilisation, staff retention, local marketing; no financial advice) - A - owner
121. Grooming Guide for Teens/Adults (age-appropriate skincare basics, hygiene, myths vs facts; no products pushed to minors) - A/B - educator
122. Eating-disorder & Body-image Safety Guard (flags harmful goals, redirects to human support; blocks diet/slimming ad pushes to minors) - B - wellbeing lead
123. Modest-fashion & Accessibility-wear Stylist (adaptive clothing, sensory-friendly textiles, mobility needs) - A - stylist

## NEVER an AI Employee (tier C)
Approve a design for production or a lot for sale; sign a cosmetic safety report or claim as true; notify a regulator; perform or
decide a chemical, laser, injectable or invasive procedure; diagnose skin/hair/scalp disease or advise treatment as a doctor;
decide whether a customer is fit for a treatment (patch-test and contraindication decisions are the practitioner's); issue a
hallmark or appraisal; accept an influencer contract or payment; publish a retouched or AI-generated model image without labels
and consent; target minors with slimming/anti-ageing products; clone a model's face/voice without recorded consent; scrape
marketplaces; make unsubstantiated "dermatologist-approved" or "organic" claims; store or train on customer photos beyond consent.

## Suggested build order
1. **Wave 1 - extend what Hoola already runs (tier A, owners feel it the same week)**: 29, 73, 90 + 74, 75, 77-79, 82, 91, 93-95, 29-34, 70, 110, 116.
2. **Wave 2 - design, production and brand assist**: 4-8, 11, 15, 18, 35, 55, 57, 64-66, 99-102, 104, 107.
3. **Wave 3 - regulated or consent-sensitive**: 22, 36, 53, 56, 58, 62, 65, 71, 76, 86, 88, 108, 112, 117, 118, 122.
Fit to Hoola: department **"Fashion & Beauty"**; extend the live `tailor` and `salon` roles first (they exist and have real owners),
then the boutique/e-commerce layer on the existing shop + COUPON/STOCK/DELIVERY engines, then the brand side. Reuse Create Studio
and HOOLA FRAMES (lookbooks, reels, 35, 100), Brand kit, social desk (102), WhatsApp opt-in (82), Khata (78, 95), `appmaker`
(salon/boutique apps with booking and loyalty), Maps (89, 41), pylab (7, 33, 81, 111), Pehchaan Locker (customer consent records),
approval cards for every price, discount, claim and payout, and the film register's **likeness-consent registry** for models.
**Best first pilot: a salon or boutique owner with 2-15 staff** - bookings, regulars, advances, stock, commissions, festival rush.
That is high-frequency, cash-linked, WhatsApp-native, and Hoola has the base. Second pilot: a **small D2C beauty/fashion brand** (claims
checker, label review, returns reducer, creator briefs).

## Open questions for the owner
- Which side first: **service owners** (salon, boutique, makeup artist, tailor), **fashion brands/retail**, **beauty brands**, or **creators**?
  I'd start with service owners because the product base already exists.
- Which market first? India's rules (Cosmetics Rules 2020, BIS hallmarking, ASCI) lead; EU/US rules are a separate pack.
- Skin and body data: confirm the consent, retention (delete after the session by default) and no-training rules before any
  photo-based employee (31, 36, 64, 65, 91) ships.
- Claims policy: confirm that Hoola blocks unsupported cosmetic claims even when a brand asks for them.
- "GO per field" turns any field into a sourced report with the Cosmetics Rules, BIS hallmarking and ASCI text checked.
