# The retail & e-commerce industry across the world - AI Employees register

Owner's ask (5 Nov 2026): *"NOW A RETAIL AND E-COMMERCE INDUSTRY AI EMPLOYEES"*. Twenty-second in the series. Retail and e-commerce here means:
kirana and neighbourhood stores, supermarkets and hypermarkets, specialty and department stores, street vendors and weekly markets, wholesale and
distribution, D2C brands, marketplace sellers, marketplace and quick-commerce platforms, omnichannel and social commerce, B2B commerce, and
the payments, fulfilment, marketing, trust and technology services around them. Fashion/beauty, pharmacy, grocery-as-agriculture, logistics, and
manufacturing slices have their own registers (cross-referenced as FB#, PH#, AG#, LG#, MF#).

**9 fields, 110 candidate AI Employees.**

## How honest this is
- No new web research for this file and no sourced job census in the repo: **domain knowledge, not sourced**. Laws and rules named are from memory and
  **must be re-checked on primary text per country and category** before any desk is built: in India the Consumer Protection (E-Commerce) Rules 2020,
  the CCPA guidelines on dark patterns and misleading advertisements, the FDI policy for marketplace vs inventory models, GST incl. TCS on
  e-commerce operators and registration thresholds, Legal Metrology (Packaged Commodities) rules, BIS Quality Control Orders and compulsory
  registration, FSSAI for food, Drugs and Cosmetics rules for pharmacy and cosmetics, Trade Marks and Copyright law for counterfeits, RBI rules for
  payment aggregators and cash-on-delivery handling, the ONDC protocol and network policy, DPDP Act 2023, state Shops and Establishments acts,
  weights and measures; abroad EU DSA/Omnibus and Consumer Rights Directive, PCI DSS (card data must never enter chat or the model), FTC rules on
  reviews and endorsements, GDPR.
- **Already in Hoola** (extend, do not rebuild): the **website Shop** (cart, checkout, server-side prices and stock, her UPI QR + UTR confirmation, COD, order tracking, Studio Shop tab; SHOP
  PLUS: GST invoice and credit note on one series, AutoPay plans, marketplace seller flow with approval and commission, Shiprocket AWB/label, wishlists, cart reminders; SHOP
  PAISA: gateway payments via her gateway, coupons, verified-buyer reviews), the **app engines** for store apps (COUPON, STOCK never oversold, DELIVERY fees/slots/holidays, VARIANTS,
  KHATA, GST BILL/WAPSI/credit notes, HISAAB month ZIP for the CA, GSTR-1 JSON, Tally export, receipts, BAAT chat, TURANT push), the **Bazar/Connectors** (ONDC shopping, UPI cards,
  ~680 packs, shops), `ecom_arch` (E-Commerce Systems Architect), `courier_desk` (Courier Sahayak), `warehouse_manager` ("Godown"), `chai`/stall (daily UPI sales, best hour, stock order),
  WhatsApp opt-in campaigns, the Meta Ads and Google Ads desks, Social Media Manager, Create Studio/FRAMES/Avatar Films (product films), the SEO employee, the research engine, Data Desk
  + pylab, Khata, PAISA, voice stack in Indian languages, vision review (product photos), `mospi` (official prices/CPI), and the website builder. Roles with `*` exist in some form.

## The findings that shape every retail & e-commerce desk
### 1. The merchant owns the price, the stock, the promise and the customer; money and orders move only on her tap
Ladder as before: **A** admin/prepare, **B** assist (analyse / draft / forecast / flag for the owner), **C** reserved.
Reserved here: setting or changing prices, discounts and refunds beyond approved rules; accepting, cancelling or shipping an order; paying suppliers or refunding customers;
publishing a product claim (safety, health, origin, "genuine"); blocking or banning a customer or seller; account takedowns or listing removals on a marketplace; signing contracts or
tax filings; and every use of customer personal data beyond consent. **The AI prepares, tracks, forecasts and drafts; the owner, buyer and platform trust team decide.** Hoola's
inherited rules stand: money never moves without the user's tap, no card/OTP/PIN in chat, official routes only (no scraping of marketplaces).

### 2. Retail is a thin-margin, high-frequency operations game where the smallest players are the majority
India has ~12 million kirana-type stores and millions of small online sellers and street vendors, whose pains are the same: what to stock, how much cash is stuck in dead stock, credit given to customers (udhaar),
supplier credit, expiry, theft, GST paperwork, customer chasing, and online discovery. The biggest-impact AI is a **WhatsApp/voice owner-copilot** that does stock, ledger, reorder, price checks,
digital catalogue, order intake and reminders. It generalises across stores, e-commerce sellers and distributors.

### 3. E-commerce is a conversion, returns and trust problem more than a technology problem
Traffic cost, conversion, returns and RTO (return-to-origin) rates, fake reviews, counterfeits, delivery promise accuracy, and customer service load decide profit. High-value AI: product content
quality, search/recommendation, size and fit, delivery-promise honesty, returns reduction, fraud screening, support automation, and ad spend discipline (Hoola's rule: ads start only on her confirm).

### 4. Platform responsibility: marketplace and quick-commerce operators carry consumer-law duties
Grievance officers, seller KYC, return/refund timelines, product-safety, counterfeit takedown, price transparency, dark-pattern bans, review authenticity, data protection, and fair treatment of sellers. The
AI in trust and compliance is tier B: it raises, ranks and drafts; humans decide takedowns, bans and penalties, with appeal paths.

### 5. Personalisation must not become manipulation
Dynamic pricing, urgency timers, nudges and personalised offers can slip into dark patterns and discrimination. Rules for every employee below: price changes are rule-based with a visible basis, no fake
scarcity or countdowns, no hidden fees, no pre-ticked add-ons, comparable prices shown in plain terms, consent-based marketing, opt-out always, and fairness tests for pricing and ranking.

---
## THE REGISTER  (AI Employee - what it does - tier - the human who decides)
Seats: [K] kirana/neighbourhood and street retail, [S] store chains/supermarkets/specialty, [D] D2C brand, [M] marketplace seller, [P] marketplace/quick-commerce platform, [W] wholesale/distribution/B2B, [C] customer/shopper, [R] regulator/ecosystem.

### 1. Neighbourhood retail & kirana  [K]
1. Dukaan Copilot (WhatsApp/voice) - daily sales, best hours, cash and UPI summary, today's shortages, udhaar due, supplier calls list; works in the shop owner's language (extends `chai`/Galla aur stock pattern) - A - shop owner
2. Stock & Reorder Assistant - barcode/photo/voice stock entry, fast and slow movers, min-max, expiry list, supplier order drafts (placed on the owner's tap), cash tied-up report - A - shop owner
3. * Udhaar / Khata Manager (existing Khata) - customer credit ledger, reminders in polite local language, limits by history, interest-free notes; **owner decides credit** - A - shop owner
4. Digital Catalogue Builder - photos to listings in minutes: names in local languages, units, prices, GST/HSN, variants; QR and WhatsApp catalogue; sync with the store app - A - shop owner
5. WhatsApp Order Taker - customer orders by voice/text, matches catalogue, confirms stock and price, builds delivery list; payment links on customer's tap; handoff to owner for exceptions - A - shop owner
6. Home-delivery Planner for Small Stores (routes via Maps, batch by area, rider/self delivery, charges per rule, delivery proof) - A - shop owner
7. Local Price & Margin Checker (supplier rates vs MRP vs competitors from the owner's own price notes and lawful public data, margin per item, MRP/overcharge rule reminders; no scraping) - A - shop owner
8. Festival & Season Stocking Planner (past sales, calendar, weather, local events; pylab; scenario ranges) - B - shop owner
9. Weekly Market & Street Vendor Assistant (daily purchase/sale log, wastage, spot-price notes from mandi sources, cash-flow, licence/hawking permit reminders) - A - vendor
10. Shop Compliance Calendar (shop & establishment licence, FSSAI, trade licence, weights & measures verification, GST filing dates, fire safety, EPR if applicable) - A - shop owner
11. Loyalty & Repeat-customer Assistant (opt-in customer list, birthday/anniversary offers, restock reminders, simple points; no data sale) - A - shop owner
12. Shrinkage & Theft Watcher (stock variances, till discrepancies, suspicious patterns; flags only; no worker accusation) - B - shop owner
13. Counter Staff Helper (price/stock lookup by voice, POS tips, billing errors, returns steps, training in local language) - A - cashier
14. Cluster Buying Group Coordinator (neighbouring stores pooling orders, supplier negotiation packs, shared delivery) - A - association

### 2. Store chains, supermarkets & specialty retail  [S]
15. Assortment & Range Planner (category roles, SKU rationalisation, space-to-sales analysis, local assortment; pylab; **category head approves**) - B - category manager
16. Demand Forecaster (SKU x store x day forecasts with promotions, weather, festivals; uncertainty bands; replenishment proposals) - B - planner
17. Replenishment & Allocation Assistant (store orders, DC allocation, cut-offs, shelf-life rules, constraints; exception review) - B - supply planner
18. Planogram & Shelf Compliance Assistant (store layouts, photo audits of shelves with vision aid, gaps and out-of-stocks, task lists) - B - merchandiser
19. Store Operations Assistant (daily checklists, task assignment, tickets to maintenance, openings/closings, audit prep) - A - store manager
20. Store Labour Scheduler (demand-based rosters, legal limits, preferences, shift swaps, training; fairness; **manager approves**) - B - store manager
21. Markdown & Clearance Optimiser (near-expiry and seasonal stock markdown steps with floors, charity routing, waste tracking; consumer-law price rules) - B - merchandise head
22. Loss Prevention Analyst (shrink root causes, exception-based reports, supplier fraud checks; **investigation by LP team; no profiling of customers**) - B - loss-prevention manager
23. Omnichannel Order Orchestrator (ship-from-store, click-and-collect, inventory visibility, split shipments, accuracy) - A - omnichannel head
24. Vendor Collaboration Desk (purchase orders, ASN, invoices three-way match, chargebacks, promotions funding; **buyer approves terms**) - A - buyer
25. Private-label Development Assistant (spec sheets, supplier shortlists, quality plans, labelling compliance (FSSAI/Legal Metrology), cost targets) - B - private-label manager
26. Store Network Planner (site selection with catchment demand, cannibalisation, rent benchmarks, footfall proxies from lawful data; Maps) - B - expansion head
27. Customer Insights & CRM Analyst (segments, basket analysis, lifetime value, churn; privacy by design; pylab) - A/B - CRM head
28. Retail Pricing Analyst (price elasticity, competitive index from lawful sources, promotions ROI; **price changes approved**) - B - pricing manager
29. Visual Merchandising Assistant (store themes, signage, seasonal reset plans, photo evidence) - A - VM manager
30. Retail Finance Controller (store P&L, shrink, labour cost, rent, working capital; month-end packs) - A - finance manager

### 3. D2C brands & online sellers  [D/M]
31. * Online Store Builder & Manager (existing website Shop engine) - products, cart, checkout, UPI/COD, GST invoices, shipping; owner approves price and publish - A - brand owner
32. Product Content Writer (titles, bullets, descriptions, SEO keywords, size charts, FAQs in multiple languages; claims checked against specs; no false claims) - B - merchandiser
33. Product Photography & Video Producer (Create Studio images, FRAMES/Avatar product films, backgrounds, A+ banners; labelled AI-generated where synthetic; no deceptive try-ons) - B - creative lead
34. Marketplace Listing Manager (Amazon/Flipkart/Meesho-style via official seller APIs only: listings sync, content compliance, category attribute fixes, suppression alerts) - A - marketplace manager
35. Pricing & Buy-box Assistant (competitive price monitoring from lawful seller-API data, margin floors, repricing rules; **owner sets rules**) - B - pricing manager
36. Inventory & Multi-channel Sync Assistant (stock across website, marketplaces and stores, oversell prevention, safety stock) - A - ops manager
37. Order Management Desk (order intake, fraud screen, COD confirmation calls/WhatsApp, address validation, packing, AWB (Shiprocket/courier desk), status updates) - A - ops manager
38. RTO & Returns Reduction Assistant (address quality scoring, COD-risk prompts, size guidance, reason analysis, return policy tuning) - B - ops head
39. Returns Processing Assistant (return intake, QC checklists, refund approval proposals, restock/refurbish/dispose decisions per rule, chargeback evidence) - A/B - returns manager
40. Customer Support Agent (WhatsApp/voice/chat; order status, exchanges, product questions from catalogue, escalation, tone; multilingual) - A - support lead
41. Review & Reputation Manager (collect verified reviews with consent, reply drafts, issue clusters; **no fake or incentivised-hidden reviews**) - A - brand manager
42. Performance Marketing Assistant (Meta/Google ad drafts, creative testing, budgets pacing, ROAS vs margin, attribution caveats; create PAUSED, start on her confirm) - B - growth marketer
43. Email/WhatsApp Marketing Assistant (opt-in campaigns, segments, templates approved, abandoned-cart reminders with consent, send-time tests; unsubscribe always) - B - CRM marketer
44. Social Commerce Assistant (Instagram/WhatsApp catalogue, live-selling plans, creator collaborations, link-in-bio shops, disclosure rules) - B - social lead
45. SEO & Content Marketing Assistant (category pages, buying guides, schema, site speed; SEO employee) - B - SEO lead
46. Unit Economics Analyst (CAC, LTV, contribution margin by SKU/channel, returns costs, break-even; pylab) - A/B - finance / founder
47. Subscription & Replenishment Manager (repeat products plans, pause/skip, AutoPay with customer consent, churn reasons) - A - brand
48. Wholesale / B2B Portal Assistant for Brands (reseller onboarding, price tiers, MOQ, credit limits, order forms, statements) - A - sales ops
49. Brand Protection Assistant (counterfeit listing detection leads, trademark watch, notice drafts; **rights holder/counsel files**) - B - brand protection lead
50. D2C Founder Copilot (idea validation, sourcing, pricing, GST/FSSAI/BIS compliance map, launch checklist, funding options) - A/B - founder
51. Dropship & Reseller Safety Guard (supplier verification, quality samples, margin traps, platform-policy checks, scam warnings) - B - seller

### 4. Marketplace, quick-commerce & platform operations  [P]
52. Seller Onboarding & KYC Assistant (documents checks, GST/PAN match, bank verification, category approvals, risk tiers; **trust team approves**) - B - seller operations
53. Catalogue Quality Auditor (duplicate listings, wrong categories, image rules, banned claims, attribute completeness; seller feedback drafts) - A/B - catalogue team
54. Search & Recommendation Quality Analyst (relevance tests, bias/diversity checks, cold-start fairness, sponsored-label compliance) - B - search team
55. Fraud & Abuse Detector (fake orders, return abuse, refund fraud, account takeover, seller collusion; explainable rules; **investigators decide**) - B - risk analyst
56. Counterfeit & Unsafe-product Monitor (notices from rights holders, safety recalls, BIS/QCO checks, keyword and image leads; **takedown by trust team**) - B - product safety lead
57. Grievance Officer's Assistant (complaint intake, timelines under E-Commerce Rules, resolution drafts, transparency report data; **officer decides**) - B - grievance officer
58. Dark-pattern & Pricing-fairness Auditor (checks flows for urgency timers, drip pricing, forced actions; reports to product and legal) - B - compliance
59. Delivery Promise & Slot Engine Auditor (accuracy of promised vs actual, rider capacity, weather impact, honest ETAs) - B - ops analytics
60. Dark-store / Quick-commerce Operations Assistant (assortment per dark store, picking waves, rider assignment, freshness, wastage, SLA 10-20 minutes; rider safety limits) - B - city ops
61. Rider/Delivery-partner Welfare Assistant (heat alerts, shift limits, accident protocol, insurance claims help, payout transparency; no punitive scoring) - A/B - partner ops
62. Marketplace Seller Support (policy Q&A in local language, payout statements, penalty explanations, appeals drafting) - A - seller support
63. Ads Platform Quality Reviewer (ad policy checks, targeting restrictions, children's protection, health/finance claims; **policy team decides**) - B - ads policy
64. ONDC Network Participant Assistant (BAP/BPP onboarding checklists, catalogue schemas, order lifecycle tests, issue and grievance management (IGM) flows) - A/B - integration lead
65. Payments & Settlement Reconciler for Platforms (collections, refunds, seller payouts, TCS/TDS, disputes; **finance signs**) - A/B - settlement ops
66. Platform Data Privacy Steward (consent artefacts, DSAR handling, retention, cross-border rules) - B - DPO
67. Content Moderation Assistant for Reviews/Q&A (spam, abuse, incentivised reviews detection; **moderators decide removals**) - B - moderator

### 5. Wholesale, distribution & B2B commerce  [W]
68. Distributor's Copilot (orders from retailers on WhatsApp/voice, stock, schemes, credit limits, route plans, collections; Khata/GST) - A - distributor
69. Beat & Route Planner (salesman visits, drop density, time windows, van loading; Maps matrix) - A - sales manager
70. Scheme & Trade-promotion Tracker (claims, eligibility, accruals, settlement; **finance approves**) - A/B - trade marketing
71. Retailer Credit Assessor's Assistant (payment history, ageing, exposure limits suggestions; **credit head decides; fairness checks**) - B - credit controller
72. B2B Marketplace Seller Assistant (RFQ responses, bulk pricing sheets, samples, MOQ, export documentation basics) - A/B - trader
73. Cash-and-carry / Mandi Trader Assistant (lots, weights, commissions, advances, quality notes, payment dues; mandi fee compliance) - A - trader
74. Wholesale Price List & Catalogue Publisher (WhatsApp price lists, change notices, availability, bulk discounts) - A - wholesaler
75. Salesman App & Order Capture Assistant (offline order capture, photos, GPS-on-shift only, targets, payouts) - A - field sales
76. Returns & Damage Claims Desk for Distributors (expiry/damage claims with manufacturer, evidence photos, ageing) - A - distributor
77. Procurement Assistant for Retail Buyers (supplier comparison, MOQ, payment terms, quality samples, contracts checklist) - A/B - buyer

### 6. Payments, finance & compliance for retailers  [K/S/D/W]
78. UPI/Card/COD Reconciliation Assistant (settlements vs sales, fees, chargebacks, COD remittance; PAISA gateway; cash handling reports) - A - accountant
79. GST & Invoicing Assistant for Retailers (B2C/B2B invoices, HSN, composition scheme, e-invoice thresholds, returns/credit notes, GSTR-1/3B data; **CA files**) - A/B - CA
80. Working-capital & Supplier Credit Planner (inventory days, payables, loans, factoring options; **lender decides**) - A/B - owner
81. Cash Flow Forecaster (weekly forecasts with festival effects; pylab) - A - owner
82. Tax & Audit Pack Builder (HISAAB month ZIP, Tally export, stock registers; **CA signs**) - A - accountant
83. Loan & Scheme Navigator for Retailers (MUDRA, PM SVANidhi for street vendors, CGTMSE; documents; **bank decides**) - A - shop owner
84. Insurance Advisor for Shops (fire, burglary, stock, liability; claims documents; **insurer decides**) - A/B - owner
85. Digital Payments Safety Coach (QR scams, fake payment screenshots, refund frauds, soundbox pitfalls; step-by-step checks) - A - shop owner / cashier

### 7. Customers & shoppers  [C]
86. Smart Shopper (price comparison with total landed cost, coupons from official sources, genuine-seller checks, return policy summary; **purchase only on the user's tap**) - A - shopper
87. Deal & Price-history Watcher (price drops on products the user follows, from lawful sources; no fake discount detection claims without evidence) - A - shopper
88. Gift & Occasion Shopping Assistant (budget, recipient profile with consent, delivery timing, wrapping, returns; ethical ideas) - A - shopper
89. Product Research Assistant (specs comparison, reliability sources, safety standards (BIS/CE), reviews analysis with fake-review caution, durability) - A/B - shopper
90. Fake Review & Scam Detector (counterfeit signals, too-good-to-be-true prices, fake websites/apps, social-commerce scams; reporting steps) - A/B - shopper
91. Return & Refund Rights Helper (policy lookup, dispute drafts, consumer helpline/forum steps, evidence checklist) - A/B - shopper
92. Family Budget Shopper (monthly grocery lists, substitution suggestions, store comparison, savings tracker) - A - household
93. Sustainable Shopping Advisor (repair, resale, certifications, packaging; evidence-based; no greenwashing) - A - shopper
94. Accessible Shopping Assistant (voice-led shopping for the visually impaired, simple language, large text, local languages) - A - shopper

### 8. Fulfilment, supply & retail technology  [S/D/P]
95. Warehouse & Fulfilment Assistant for E-commerce (inbound, putaway, pick-pack, cycle counts, returns; extends Godown and logistics register) - A - fulfilment manager
96. Carrier Selection & Shipping Rate Assistant (rate cards, pincode serviceability, SLA performance, COD fees, shipping label API on tap; cross-ref logistics) - A - ops
97. POS & Retail Software Implementation Assistant (requirements, product master data, tax setup, training, cutover) - A - retail IT
98. E-commerce Platform Integrator (API mapping among storefront, ERP, payment, courier, marketplace; `ecom_arch` desk) - A/B - integration lead
99. Analytics Dashboard Builder (sales, margin, returns, stock, cohort retention; Data Desk + pylab; no individual customer tracking beyond consent) - A - analytics lead
100. Barcode/RFID/Label Compliance Assistant (GS1 barcodes, Legal Metrology declarations, MRP/date labels, language rules) - B - packaging / compliance
101. Retail Cybersecurity Assistant (POS hygiene, phishing drills, card-data scope reduction (PCI), account takeovers, backup checks) - B - IT security
102. Retail AI Governance Officer (inventory of pricing/ranking/forecast models, bias and drift checks, human override rates; HC#160 pattern) - B - AI governance committee
103. Sustainability & EPR Compliance Assistant (plastic packaging EPR, e-waste, battery rules, take-back, carbon estimates with ranges) - B - sustainability lead

### 9. Education, ecosystem & policy  [R]
104. Retail Skills Trainer (cashier, stocking, customer service, digital tools in local language; certification support) - A - trainer
105. Small-Business E-commerce Coach (how to start selling online: GST, marketplace onboarding, photos, pricing, returns, scams; Guru Sahayak) - A - trainer / mentor
106. Retail Management Tutor (merchandising, supply chain, pricing, consumer behaviour; case studies) - A - student
107. Retail Association & Mall Management Assistant (tenant mix, footfall data, common-area maintenance billing, events) - A - association manager
108. Consumer Protection Case Assistant (complaint intake, pattern detection, escalation to authorities; **regulator decides**) - B - consumer-affairs officer
109. Policy & Market Analyst (retail indices, inflation, FDI/regulation tracking, MoSPI data; sources cited) - A - analyst
110. Street Vendor Rights & Registration Navigator (vending certificates, local rules, scheme linkage, grievance) - A - vendor / NGO

## NEVER an AI Employee (tier C)
Set or change prices, discounts or refunds outside owner-approved rules; accept, cancel, ship or refund an order, or pay a supplier, without the owner's explicit tap through official rails; hold or store card numbers, PINs, OTPs or CVV;
publish product claims it cannot substantiate; write or buy fake reviews, hide genuine negative reviews, or run incentivised-review schemes; use dark patterns (fake urgency, drip pricing, forced add-ons); ban a customer or seller,
delist or take down a listing, or levy a penalty without a human decision and appeal path; discriminate in pricing, credit or ranking by protected traits; sell or share customer data without consent; scrape marketplaces or competitors against terms; sign
contracts or file taxes as the merchant; surveil staff beyond lawful purpose; promise delivery dates it cannot keep.

## Suggested build order
1. **Wave 1 - kirana/shop and small online seller copilots (tier A, WhatsApp/voice, extends Khata + Shop engine)**: 1-5, 7, 10, 3, 31, 32, 36-38, 40, 41, 78, 79, 81, 86, 90.
2. **Wave 2 - growth and operations assist with a named owner/manager**: 6, 8, 11, 15-17, 21, 23, 33-35, 39, 42-47, 68-71, 80, 95-99.
3. **Wave 3 - platform trust, fraud, compliance and pricing-sensitive roles**: 12, 22, 28, 49, 52-67, 72, 100-103 - need grievance officers, appeal paths and fairness testing.
Fit to Hoola: department **"Retail & E-commerce"**; Hoola's existing stack (website Shop with GST/AutoPay/marketplace/Shiprocket/reviews/coupons, app engines for COUPON/STOCK/DELIVERY/VARIANTS/KHATA/HISAAB,
ONDC shopping and Bazar connectors, `ecom_arch`, `courier_desk`, `warehouse_manager`, Meta/Google Ads desks, WhatsApp opt-in, voice) is **already the deepest retail/e-commerce base of any series industry**; Wave 1 is
packaging it into **role-shaped employees** (Dukaan Copilot, Online Store Manager, Seller Support) and adding the owner-copilot layer in voice and WhatsApp.
**Best first pilots**: (a) a **kirana/general store owner** (1-5, 7, 10) in Hindi/Marathi - Khata, stock, reorder, WhatsApp catalogue and orders, UPI summary; (b) a **small online seller / D2C brand** on the website Shop engine
(31-33, 36-43, 79) with marketplace sync via official APIs; (c) a **distributor** (68-71). Large chains and marketplaces come later: data, security and fairness governance are heavy.

## Open questions for the owner
- Which side first: **kirana/neighbourhood stores**, **small online sellers/D2C brands**, **distributors/wholesalers**, **store chains**, or **marketplace/platform trust**? I'd start with kirana + small online sellers since the engines exist.
- Channel: WhatsApp-first (catalogue, orders, payments links) with voice for owners? That implies WhatsApp Business API costs and template approvals; confirm the pricing model.
- Data sources: marketplace seller APIs and ONDC only (no scraping), price intelligence from the owner's own data and lawful public sources: confirm.
- Customer data: opt-in lists only, no sale of data, consent artefacts under DPDP; confirm retention and deletion.
- Fairness: confirm that Hoola's pricing, ranking and credit helpers show their basis and never use protected traits or locality proxies for discrimination.
- "GO per field" turns any field into a sourced report with the E-Commerce Rules 2020, CCPA dark-pattern guidelines, Legal Metrology and GST rules checked on primary text.
