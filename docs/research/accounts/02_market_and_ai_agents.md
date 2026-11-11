# Accounts Assistant research 02 - the market: Indian books + AI accounting agents (11 Nov 2026)

Web research only (vendor pages, trade press, review sites). Every accuracy figure is the VENDOR'S own number - no independent
benchmark exists for any of them. UNVERIFIED = not confirmed on a vendor's primary page or a credible independent source.

## The short version
1. **AI is no longer the differentiator.** By 2026 every serious ledger ships "AI reads the bill, AI matches the bank line, a human
   approves": Tally (Docs by Ira, 7.1), Zoho (Zia), Intuit (agents), Xero (JAX), Sage, Digits, Ramp. Hoola cannot win on OCR or
   categorisation alone.
2. **Indian owners already keep their books somewhere** - usually Tally (often run by the CA), Zoho Books, Vyapar, myBillBook, Busy or
   Marg. Hoola should sit ON TOP of her book (like AI Accountant on Tally / Zoho, Biz Analyst on Tally), not be a new ledger.
3. **The unowned gap is the conversation layer** - WhatsApp + voice + Hinglish across all of them. A few small startups try (AI
   Accountant's WhatsApp-to-Tally bot, Startup Khata, Blipko); no major vendor has it (Tally 4.0 only shares invoices on WhatsApp).
4. **Trust = a few mechanics**: drafts never direct posts, confidence-grouped "ready to post", locked periods with an approval queue,
   review-only first then automation she turns on, an explanation per match, anomaly guards (changed bank details, duplicates, odd
   amounts). Hoola's "her tap first" already fits; copy these explicitly.
5. **Legal data rails exist, each with a gate**: GST data via a GSP (the taxpayer enables API access with an OTP for 6 h - 30 days;
   since 7 Nov 2025 she can see and revoke the ASP's token on the portal); e-invoice via an IRP through a GSP; Account Aggregator only
   as or through a regulated FIU; Tally = XML/JSON over HTTP on HER machine; Zoho = OAuth REST, 100 requests / min / organisation.

## A. Indian SMB accounting software and how outside apps connect
**TallyPrime** - the default book for SMEs and their CAs (desktop, licence + TSS). 7.0 (Dec 2025): TallyDrive auto-backup, payments via
Connected Banking (Axis, SBI), IMS ITC reduction with live portal sync, one-step cancel of EWB + e-invoice + voucher. 7.1 (Jun 2026): IMS
reconciliation with a Books View, supplier lookup by GSTIN, ICICI payments, OAuth email, **Docs by Ira** (OCR + AI -> party, GSTIN,
number, date, amounts, GST, lines; matched to masters, duplicate check, **draft vouchers reviewed before posting**; desktop import or the
TallyIra mobile app; rollout "phased" / pricing UNVERIFIED; "save up to 80% time" vendor claim). 7.2 seen in developer notes only.
Earlier: Connected GST 5.0 (file GSTR-1 / 3B / CMP-08 from Tally), Connected Banking 6.0, WhatsApp share 4.0, MSME 43B(h) tracking 4.1.
Connected Banking reality: marketing "145+ banks" = statement-file import; live connectivity listed for Axis, SBI, Kotak, ICICI via Tally
subsidiary Navmaya's aggregator (Tally.NET ID + TSS + OTP, 30-day connections for Axis/Kotak); no evidence of AA or Yodlee.
**How outside apps connect**: XML over HTTP POST to her Tally port (default 9000, Exchange > Data Synchronization, a company must be
open) - the official route; ODBC (read); native JSON / JSONEx from 7.0 (masters, vouchers, reports, "Tally Connector" request/response);
TDL for in-product customisation. **A cloud server cannot reach port 9000 without a local bridge / agent / tunnel** - which is why AI
Accountant ships a sync plugin and RazorpayX's Tally sync is triggered from inside Tally. Licence: internal business use, no
sublicensing, no hosting for third parties, no reverse engineering; no published integrator-specific rules (UNVERIFIED) - reading /
writing HER data through the documented XML/JSON interface on HER licensed copy is the intended use.

**Zoho Books (India)** - cloud SMEs, startups, service firms. Price / org / month ex-GST (third party, UNVERIFIED): Free under Rs 25 L
turnover, Standard ~Rs 899, Professional 1,499, Premium 2,999, Elite 5,999, Ultimate 9,999. Zoho is a GSP: e-invoice (IRN + QR) +
GSTR-1 / 3B from inside the app. Zia: bank-recon agent + AI field prediction (Early Access, enabled by emailing support). API: REST v3,
OAuth 2.0, `https://www.zohoapis.in/books/`, per-module scopes; **100 requests/min/org then the org is blocked (429, code 44)**; daily
caps Free 1k / Standard 2k / Professional 5k / Premium+ 10k; concurrency 5 free / 10 paid. No evidence GST FILING is in the public API.

**Vyapar (+ Vyapar TaxOne = Suvit, bought Nov 2025)** - micro traders; from ~Rs 699/yr. TaxOne (CA side): bank statements (Excel / PDF /
scanned OCR, "400+ banks" claim) and documents -> Tally vouchers, CA practice suite with WhatsApp + Tally sync (~Rs 10-12k/yr). No public
API found. Reviews: data that "disappeared", totals stopped matching, mobile-desktop sync mismatches.
**myBillBook (FloBiz)** - billing + inventory, one-click e-invoice / EWB (vendor), WhatsApp share, OCR (Oct 2026 changelog); ~Rs 399/yr;
API unclear. **Khatabook / Biz Analyst** - free udhaar ledger with WhatsApp reminders; Biz Analyst (bought 2021 ~$10M) = a MOBILE LAYER
OVER TALLY (outstanding, stock, orders, receipts synced to Tally) - the closest precedent for "Hoola on top of Tally". **Busy (IndiaMART,
Rs 500 cr, 2022)** - traders / distributors, desktop, no public API. **Marg ERP** - pharma / FMCG distribution, no public API found.
**Swipe (YC S21)** - WhatsApp-first billing with a PUBLIC API (developers.getswipe.in): invoices, credit notes, POs, challans, e-way bill
and e-invoice (`einvoice=1`, needs the "E-Invoices & EwayBills" plan, government sandbox by default, production by email), 1 req/s/key.
**RazorpayX** - payouts / vendor payments synced to Tally / Zoho; "purpose rules" map a payout purpose to an expense account + tax slab;
payouts missing info wait in a **Categorise** tab; Tally sync triggered from inside Tally; Zoho sync needs a GSTIN on the org.
**Clear (ClearTax)** - GSP + IRP; docs.cleartax.in: GSP APIs, e-invoice, e-way bill, IMS "action recommendations"; sales-led pricing.
**AI Accountant (aiaccountant.com, Karbon Card team)** - the closest Indian analogue: on top of Tally (sync plugin) and Zoho (native);
WhatsApp bill bot: photo -> extraction -> predicted ledger + GST treatment -> **entry prepared, an accountant reviews before it posts**;
450+ customers incl. 100+ CA firms, ISO 27001 / SOC 2 claims; fixed monthly pricing unpublished.
Small others: Startup Khata, Blipko, KhataGO. CA practice tools: TaxOne, Turia (WhatsApp Business API reminders, Mar 2026), Qwikca,
ERPCA, ComplianceDesk, Practive - due-date calendars, document chase over WhatsApp / email, Tally sync.

## B. AI accounting agents worldwide (2024-2026)
| Product | End to end | Trust mechanism | Accuracy claim (vendor) | Price |
|---|---|---|---|---|
| Intuit QuickBooks agents (Jul 2025 ->) | Accounting (categorise, reconcile, anomalies, close), Payments (invoices, reminders, late-payer prediction), Finance (KPIs, forecast), Customer; 2026 payroll + sales-tax | Every AI-drafted entry reviewed + approved before posting; "Ready to post" groups high-confidence items; confidence icons | paid ~5 days faster, up to 12 h/month saved | plan-tiered |
| Xero JAX | Auto bank recon (explains each match, exception queue), month-end agent (prepayment / amortisation journals for approval), Bill Protection beta (unusual amounts, CHANGED BANK DETAILS, unfamiliar suppliers) | explanation per match, exception queue, approval before journals | ~50% less recon time | in plans |
| Sage Intacct / Copilot | AP agent (capture, PO match, coding, duplicates), Close agent, subledger recon | flags + recommendations | n/a | enterprise |
| Zoho Zia | bank-recon agent, field prediction | editable suggestions; accountant reviews | n/a | early access |
| Digits | own ledger, continuous close, Write MCP (Oct 2026) | **locked periods: agent edits to a locked period go to an admin review queue; agents inherit the user's permissions** | 97.8%; 95% touch-free | outcome-based |
| Pilot AI Accountant (Feb 2026) | onboarding, cleanup, categorise, reconcile, close | flags unusual items | "fully autonomous" | $99 AI-only / $499+ with humans |
| Basis ($100M B, Feb 2026) | agents for accounting FIRMS (statements, tax returns) | staff review like a junior's work | 20-50% efficiency | enterprise |
| Rillet / Truewind | AI ERP / AI close layer on Sage / QBO | n/a | n/a | sales-led |
| Puzzle | AI ledger via firms | **Transaction Accuracy Review**: same vendor in several categories, same description across vendors; month-end checklist with confidence + next step per flag | n/a | plan |
| Botkeeper | **shut down Feb 2026** (SMB service ended) | - | - | - |
| Vic.ai | autonomous AP | autopilot vs needs-touch split | 97-99% coding | sales-led |
| Ramp | AP agents, Policy Agent | **starts review-only; she decides when automation turns on** | 85% expense reviews automated at 99% | Ramp Plus |
| Booke / Docyt | AI on QBO / Xero; multi-entity | low-confidence + policy items to humans, thresholds, audit trail | n/a | $129 / ~$299 mo |
| Indian | Tally Docs by Ira, AI Accountant, Vyapar TaxOne | drafts + accountant review | 80% time (Tally) | see A |

**2026 trust design, common to all**: (1) draft then approval; (2) confidence grouping with one-tap posting of the sure group; (3) an
explanation per match; (4) an exception queue; (5) period locks agents cannot silently change; (6) agents act with the user's own
permissions; (7) anomaly guards on payment details; (8) review-only mode first.

## C. Patterns for a chat / voice / WhatsApp-first assistant, and known failures
**Proven patterns**: WhatsApp photo / PDF -> DRAFT voucher with ledger + GST treatment pre-filled -> approve (AI Accountant, Docs by Ira,
myBillBook OCR); bank lines -> suggested voucher + a "Categorise" holding tab (RazorpayX, TaxOne, Tally banking, Zoho prediction);
collections - predict late payers, draft reminders, owner-sent udhaar reminders (QuickBooks Payments agent, Khatabook, Biz Analyst);
IMS / GSTR-2B readiness (Tally 7.1 Books View, Clear IMS recommendations); **since the July 2025 tax period the outward liability in
GSTR-3B (auto-filled from GSTR-1 / 1A / IFF) is HARD-LOCKED** - fix in GSTR-1A before 3B, so a "fix before the lock" check has real value;
ITC in 3B Table 4 comes from GSTR-2B / IMS; **e-invoice 30-day window for AATO >= Rs 10 cr from 1 Apr 2025** (IRP refuses later
reporting) - a "N invoices about to expire" alert is concrete; supplier GSTIN check at entry; changed-bank-details / duplicate-bill
guard before any payment; the CA hand-off pack (CAs want vouchers in THEIR Tally + source documents, not a new dashboard); the Puzzle
accuracy sweep (same vendor across ledgers, same narration across parties) - cheap, deterministic, catches systemic errors.
**Known failures**: systemic miscategorisation (same vendor three ways; accountants still reviewing ~40% after a year - anecdotal);
"98% accuracy" marketing while the 2% compounds into tax exposure (wrong ITC reversed with interest); junior staff over-trusting the
machine; data loss / sync mismatches (Vyapar reviews); vendor death (Botkeeper Feb 2026); GST mismatches the software cannot fix
(supplier not filed, wrong GSTIN / period, B2B reported as B2C) = supplier follow-up on WhatsApp; bank-count overstatement; early-access
gating (do not plan around features that may not be on her plan).

## D. Official data rails a third-party app can legally use
| Rail | Route | Consent | Pricing shape |
|---|---|---|---|
| GST returns data (GSTR-1 / 2B / 3B, IMS, ledgers) | be an ASP tied up with a GSP (Clear, Masters India, IRIS, Cygnet, Quicko, Vayana, FinAGG, WhiteBooks...) | taxpayer enables Manage API Access on the GST portal, picks GSP/ASP, OTP; 6 h - 30 days (verify); from 7 Nov 2025 she sees active ASP tokens (View Logs > Active Tokens) and can revoke; signatory gets email + SMS naming ASP / GSP / validity; per GSTIN | metered per call + onboarding + renewal; no public rate cards |
| e-invoice (IRN) | 6 IRPs (NIC x2, Cygnet, Clear, EY, IRIS); for an app = the GSP route | taxpayer's IRP API user (client id / secret + username / password) | per GSP plan |
| e-way bill | same as e-invoice; EWB API credentials can serve e-invoice | taxpayer credentials | same |
| GSTIN search | no official open API (portal has a CAPTCHA); via GSPs or paid KYC APIs (Hoola already pays gstinapi, v0.765) | none (public data) | per call |
| Bank data - AA | Hoola CANNOT be an FIU unless regulated; partner with a regulated FIU or skip (Sahamati SRO 5 Jun 2026) | AA consent per fetch | via partner |
| Bank data - other | her uploaded statements; the bank feed already inside Tally / Zoho / RazorpayX; bank alert mails in her Gmail | her own login | free |
| Tally | XML / JSON over HTTP to HER Tally via a local bridge; draft / optional vouchers for writes | her machine, her licence | free |
| Zoho Books | OAuth REST on zohoapis.in | OAuth | free, rate-capped |
| Swipe | public REST incl. e-invoice / EWB | API key | paid add-on |
| Payments / collections | Razorpay / Cashfree / PhonePe links (Hoola v0.419), UPI intent on her tap | her gateway keys | MDR |
| WhatsApp | official Cloud API, per-message billing since 1 Jul 2025 | customer opt-in | India utility ~Rs 0.115-0.145 / msg (check Meta's card) |
**An app can never file a return without the taxpayer's own action**: GSTR-1 / 3B filing needs her EVC or DSC; an ASP prepares and
uploads, filing stays her act.

## The 15 ideas to take
1. Sit on her existing book (Tally local XML/JSON, Zoho OAuth, Swipe API, then file export for Busy / Marg / Vyapar / myBillBook).
2. WhatsApp photo / PDF -> DRAFT voucher with ledger + GST pre-filled -> her or her CA's tap posts (in Tally as an optional / draft voucher).
3. "Ready to post" confidence groups ("12 bills look certain - tap once; 3 need you"), never one-by-one fatigue, never silent posting.
4. The reason on every suggestion ("matched because amount + date +/-2 days + narration 'RAZORPAY*'").
5. Review-only first; automation unlocked rule by rule, each rule deterministic and visible.
6. Locked periods: once her CA marks a month filed, any change goes to an approval queue.
7. Bill protection before any payment card: changed bank / UPI, duplicate number from the same GSTIN, amount far outside history, unknown supplier.
8. Monthly GST readiness with the items behind it: purchases missing from 2B / IMS (+ drafted supplier nudge she sends), GSTR-1 errors to
   fix in 1A before the 3B lock, e-invoices near the 30-day limit, cancelled / suspended supplier GSTINs.
9. Nightly accuracy sweep in code: same party across ledgers, same narration across parties, round-sum cash, GST rate vs HSN; each flag with confidence + fix.
10. A daily cash line on WhatsApp / voice from her book or bank - never invented.
11. Collections the Indian way: overdue list -> gentle reminders in her voice, sent by her tap, payment link, STOP respected; MSME 45-day exposure on HER payables.
12. A monthly CA hand-off pack: Tally-importable vouchers + source documents + bank recon status + GSTR-1 / 2B variance list + open questions.
13. GST data through a GSP as an ASP, the OTP consent walked through in chat; show her Active Tokens and how to revoke.
14. Voice / Hinglish questions over her real ledger ("Sharma ji ka kitna baaki hai?") - every number from a tool result.
15. Measure Hoola's own accuracy honestly (correction rate, posted-then-edited, share touched) - shown to her and her CA, no "98%".

## Traps to avoid
Silent posting; marketing accuracy numbers; one wrong rule applied a thousand times (rules need a preview "this changes 214 past
entries" + undo); building a second ledger (the CA rejects a shadow book); assuming a cloud server can reach Tally (local bridge,
offline queue, "Tally is closed" states, port 9000 only to localhost / the bridge); bank-count overstatement; becoming an FIU or scraping
net-banking; filing for her (EVC / DSC is her act; never hold her portal password); storing GST portal / bank credentials; alerts after
the 3B lock / the 30-day IRP window; treating supplier GST mismatches as Hoola's bug; early-access dependencies; vendor concentration
(export any time); WhatsApp cost creep (batch daily summaries); Zoho per-org rate limits; hosting / modifying Tally.

## Sources (URL -> what it supports)
tallysolutions.com/whats-new/ (Tally 1.0-7.1, Connected GST / Banking, IMS, Docs by Ira) · help.tallysolutions.com/release-notes-tally-prime-developer-7/
(JSON / JSONEx in 7.0) · help.tallysolutions.com/?p=149532 + /pre-requisites-for-integrations/ (XML over HTTP, port) ·
tallysolutions.com/tally/docs-by-ira-ai-invoice-processing/ (draft vouchers, review) · help.tallysolutions.com/tally-prime/banking-utilities/connected-banking-feature/
+ tallysolutions.com/connected-banking/terms-and-conditions/ (banks, Navmaya, 30 days) · tallysolutions.com/terms-of-use (licence) ·
zoho.com/books/api/v3/introduction/ (India domain, limits) · zoho.com/books/help/ai-features/ai-features.html (Zia) · tribuneindia.com +
socialsamosa.com (Vyapar-Suvit, TaxOne) · capterra.com Vyapar reviews (data loss) · mybillbook.in + knowledge.mybillbook.in/changelog ·
yourstory.com 2021/03 (Biz Analyst) · corporate.indiamart.com 2022/01/25 (Busy) · developers.getswipe.in (Swipe API) ·
razorpay.com/docs/x/accounting/tally/ + /zohobooks/ (RazorpayX sync, Categorise tab) · docs.cleartax.in (Clear GSP, IMS recommendations) ·
aiaccountant.com (WhatsApp -> reviewed Tally entry) · quickbooks.intuit.com/r/product-update/innovation-agentic-ai-2025/ +
accountingtoday.com (Intuit agents) · xero.com media releases Xerocon Denver / London (JAX, Bill Protection) · sage.com press 2026/04 +
2026/11 · digits.com/blog/what-is-continuous-close/ + cpapracticeadvisor.com 2026/10/13 (Write MCP, locked periods) ·
cpapracticeadvisor.com 2026/02/04 (Pilot), 2026/02/24 (Basis), 2026/02/28 (Botkeeper / Xendoo) · cpatrendlines.com 2026/08/24 (Rillet) ·
puzzle.io/blog/ai-accuracy-review-for-accountants · vic.ai Q1 2026 release · ramp.com/blog/ramp-ap-agents-announcement +
support.ramp.com/policy-agent-overview · beancount.io forum threads (anecdotal AI-categorisation complaints) · cleartax.in/s/hard-locking-in-gstr-3b
(3B hard lock) · mahagst.gov.in GSTN advisory 293 (e-invoice 30-day rule, AATO >= Rs 10 cr) · taxmann.com + octagst.com (ASP OTP alerts,
Active Tokens, revoke from 7 Nov 2025) · learn.quicko.com/gst-portal-manage-api-access + irisgst.com/kb/enable-api-access-2/ (Manage API
Access, 6 h - 30 days) · help.quicko.com GSP billing (pricing shape) · cleartax.in/s/irp-providers-list-india (six IRPs) · vayana / finagg
docs (GSTIN search via GSPs) · sahamati.org.in/faq/ + financialservices.gov.in (FIU must be regulated) · developers.facebook.com WhatsApp pricing.
