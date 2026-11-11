# Hoola GST & Accounts Employee - the plan

Owner, 11 Nov 2026: *"NOW LETS BUILD THE ACCOUNT ASSISTANT EMPLOYEE --- DO DEEP RESEARCH AND MAKE A PERFECT PLAN FOR IT"*, then
*"LET WE DEVELOP A FULL GST AND ACCOUNT EMPLOYEE --- I HAVE WHITEBOOK APIS OF GST"*.

Research behind every line here (read the one you need, not all):
- `docs/research/accounts/01_what_hoola_has.md` - every accounting piece already in the code, with file:line.
- `docs/research/accounts/02_market_and_ai_agents.md` - Tally / Zoho / Vyapar / Clear / AI Accountant + QuickBooks / Xero / Digits / Ramp agents.
- `docs/research/accounts/03_rules_and_calendar.md` - GST, the Income-tax Act 2025, payroll, MSME, bank data, the compliance calendar.
- `docs/research/accounts/04_whitebooks_api.md` - the WhiteBooks GST / e-Invoice / e-Way Bill API, implementation grade.
- `docs/research/banking_finance_industry/00_INDEX.md` rows 101-119 (the register this employee comes from).

---

## 1. The three findings that shape everything

**1. Hoola already has most of the accountant - in seven engines that never talk.** `gstp` (GST Sahayak, v0.93) already checks every bill
line against GST 2.0, imports Tally / Vyapar / Busy registers, imports GSTR-2B, reconciles books vs 2B with IMS suggestions, prepares
GSTR-1 JSON and GSTR-3B with least-cash set-off, handles notices and the calendar. `analyst` reads trial balances and bank statements;
`appmaker` makes Rule-46 invoices, GSTR-1 JSON, Tally XML and the CA month ZIP; `thok` runs wholesale billing and a debtor ledger;
`office` keeps vendor bills and petty cash; `payroll` does PF / ESI / PT / TDS; `finops` / `finguard` / `enterprise` reconcile and age.
None posts to one book, none has a console page, and `gstp` reaches the GST portal through the Computer Operator BROWSING gst.gov.in.
**So this employee is mostly ORCHESTRATION + one register + a real API pipe - not a rebuild.**

**2. WhiteBooks turns "prepare for the CA" into "prepare, and she files from Hoola".** WhiteBooks is a GSTN-licensed GSP; its real contract
(the OpenAPI specs in its Developer Hub - NOT its prose docs, which describe an OAuth API that does not exist on the live server) covers
GSTR-1 / 1A / 3B / 2B / IMS / 9 / 9C / CMP-08, ledgers, challans, notices, e-invoice IRN and e-way bills. Every filing still ends in HER
act: the GST login OTP and the EVC OTP sent to her authorised signatory. That is exactly Hoola's "her tap" law - the pipe changes, the law
does not.

**3. AI is no longer the moat; trust mechanics and the conversation are.** Every ledger in 2026 reads bills and matches bank lines. What
none has is WhatsApp + voice + Hinglish over HER real books, with the trust mechanics the market converged on: drafts never direct posts,
confidence-grouped "ready to post", a reason on every suggestion, review-only first, locked periods, bill protection before payment, and
honest measured accuracy instead of "98%".

---

## 2. What she gets (the pitch, in her words)

*"Mera accountant jo kabhi chhutti nahi leta."* Every bill she forwards on WhatsApp becomes a checked entry. Every month her GST is
prepared, matched against what her suppliers filed, and filed from Hoola when she gives the OTP - before the 11th and the 20th, never
after the lock. She asks "Sharma ji ka kitna baaki hai?" or "is mahine GST kitna banega?" in a call and the answer comes from her own
numbers. Her CA gets a clean pack every month instead of a box of bills.

**The employee** - Hub key `accounts` (the existing "Accounts Assistant" row goes live, renamed **GST & Accounts**), department Business.

**It does**
- GST end to end: register, GSTR-1 / 1A, IMS actions, 2B recompute, GSTR-3B, CMP-08, GSTR-9 / 9C drafts, challans, ledgers, notices - prepared,
  checked, filed on her OTP.
- e-invoice (IRN) and e-way bills from any Hoola invoice, on her tap, with the 30-day IRP window watched.
- Bill intake from WhatsApp / email / photo / PDF into checked purchase entries.
- Bank + UPI reconciliation with a reason on every match.
- Receivables / payables, MSME 15 / 45-day and Rule 37 180-day watches, collections reminders she sends.
- TDS worksheets on payments (s.393 of the 2025 Act), the compliance calendar, month-end close, the CA hand-off pack.

**It never** (tier C, enforced in code, said on every relevant answer)
- Moves money, pays a challan, or pays a supplier - a challan is a CPIN she pays at her bank; a payment run is a bank file she uploads.
- Files without her OTP: the GST login OTP and the EVC OTP are hers; DSC filing is not supported (her DSC stays on her machine).
- Holds her GST portal password; never asks for or stores PIN / OTP / CVV / card / bank passwords; IRP / EWB API passwords only through the
  sealed-credential door, never chat, never logged.
- Gives tax or legal advice as a professional; certifies; signs an audit, 9C, or a financial statement.
- Silently changes a filed / locked month; silently posts a guessed entry.
- Scrapes net-banking or becomes an Account Aggregator FIU.

---

## 3. The design laws (each one is a test)

1. **One register, many sources.** A new `accounts` register holds every document once (sales, purchases, expenses, receipts, payments,
   credit / debit notes, journals) with its SOURCE (app order, website order, thok bill, gstp doc, office bill, a vertical desk's invoice,
   a WhatsApp photo, a bank line, her Tally) and a stable key so the same invoice never lands twice. The seven engines feed it through
   adapters; they keep working exactly as today.
2. **Rules are data, with `source` + `checked_on`.** GST rate history (before / after 22 Sep 2025), HSN -> rate, the s.393 TDS table, form
   numbers (24Q -> 138 ...), due dates, state PT, PF / ESI ceilings, late-fee caps - JSON files under `server/app/bahi/rules/`, each row
   carrying where it came from and when it was last read. A row whose `checked_on` is older than its `review_by` makes the answer say so.
   Nothing marked UNVERIFIED in research 03 becomes a computed number until a primary read clears it.
3. **Drafts, never direct.** Every proposed entry, IMS action, return section and IRN is a DRAFT with a CONFIDENCE and a REASON
   ("matched: amount + date +/-2 days + narration RAZORPAY*"). Sure drafts are grouped ("12 bills look certain - tap once; 3 need you").
4. **Review-only first.** A new tenant starts in Seekh (every draft waits). Her rules ("Airtel bills -> Telephone") become deterministic,
   visible, previewable ("this changes 214 past entries") and undoable. Saathi / Bharosa trust only ever widens what posts without a tap -
   never filing, never money.
5. **Locked periods.** A filed GST period and a month her CA closes are LOCKED; any later change becomes an amendment proposal (GSTR-1A
   before 3B, a GSTR-1 amendment after) on an approval queue, never an edit.
6. **The lock calendar drives the work.** Since July 2025 the GSTR-3B liability is locked to GSTR-1 / 1A, and interest is auto-computed and
   cannot be lowered. So every check runs BEFORE the 11th / the 20th, and the e-invoice 30-day window (AATO >= Rs 10 cr) is watched daily.
7. **Every number comes from a tool result.** Voice and chat answers quote her register / her portal data; an estimate says it is one.
8. **Bill protection before any payment card**: changed bank / UPI details for a supplier, duplicate invoice number from the same GSTIN,
   amount far outside that supplier's history, a cancelled / suspended GSTIN, an unknown supplier.
9. **Measured honesty.** Per-tenant correction rate, posted-then-edited rate, share of documents touched - shown to her and her CA.
10. **Idempotent government calls.** Every IRN / EWB / save response persisted before anything else; a timeout is RECOVERED
    (GETIRNBYDOCDETAILS within 72 h, getewaybillgeneratedbyconsigner), never re-fired; one in-flight call per document.

---

## 4. The WhiteBooks pipe (how Hoola talks to GSTN)

**Keys - never in chat, never in the repo.** In the VPS `.env` (Hoola reads them, no route returns them):
```
WHITEBOOKS_ENV=sandbox                 # sandbox | production
WHITEBOOKS_EMAIL=<the WhiteBooks developer account email>
WHITEBOOKS_GST_CLIENT_ID=...           WHITEBOOKS_GST_CLIENT_SECRET=...
WHITEBOOKS_EINV_CLIENT_ID=...          WHITEBOOKS_EINV_CLIENT_SECRET=...
WHITEBOOKS_EWB_CLIENT_ID=...           WHITEBOOKS_EWB_CLIENT_SECRET=...
```
(The Hub shows a separate pair per product; if her account has one pair, the GST pair is used for all three.)

**Module** `server/app/bahi/wb.py` (the package is `bahi`, not `accounts` - `app/accounts.py` is the sign-in module) - one client over the three specs: `client_id` / `client_secret` headers + `email` query on every
call, the sandbox / production base from `WHITEBOOKS_ENV`, **branch on `status_cd` (HTTP is 200 even on failure)**, WB_ERR / GSTN / NIC
codes mapped to plain English, the EWB password scrubbed from every log line (it rides a query string), a per-tenant rate guard
(sandbox 60/min), a call meter (WhiteBooks bills per call) with a daily cap per tenant, and a recorder for contract tests.

**Per-taxpayer connection** (table `acc_gst_conn`, one row per GSTIN): `gstin, state_cd, gst_username, txn, enabled_until, last_refresh,
status`; e-invoice `username` + sealed password + `auth_token` + `token_at`; EWB `username` + sealed password. Passwords sealed exactly like
the enterprise endpoint credentials (v0.397 CONNECT): typed in the app / console, sealed on arrival, returned by no route.

**The connect walk (a card per step, in chat and on the desk)**
1. "Enable API access": the card shows the exact portal path (gst.gov.in -> My Profile -> Manage API Access -> Yes -> pick BVM IT Consulting /
   WhiteBooks + Hoola -> a duration up to 30 days) and how to see / revoke Hoola's token later (View Logs -> Active Tokens).
2. "Send the OTP": her tap -> `otprequest` -> the OTP arrives on HER registered mobile / email.
3. She types the OTP into the card (the v0.76 OTP box law: straight into the call, never stored, never shown to the model) -> `authtoken`.
4. Hoola refreshes the session quietly while it is valid; when it lapses, ONE card asks again - never a loop of OTP requests.
5. e-invoice / EWB: the card explains creating the API user on the e-invoice portal "through GSP" (BVM IT Consulting) and takes the
   username + password in the sealed form.

**Filing walk (EVC)**: draft -> `retsave` -> poll `retstatus` -> `retsum` shown as a plain summary + "this is what will be filed" ->
`newproceedfile` -> her **File** tap -> `otpforevc` to the authorised signatory -> she types the EVC OTP -> `retevcfile` -> the ARN is
recorded and shown. A GSTR-3B also needs `retoffset` (the set-off plan she approved) and, if cash is short, a PMT-06 challan (a CPIN she
pays at her bank - Hoola never pays).

**Before production (owner, D2)**: WhiteBooks' Terms forbid resale / sublicensing without written agreement - serving many Hoola users
needs a signed ASP / reseller agreement. Until it exists, production connects ONLY her own GSTINs; every other tenant sees the free
sandbox / prepare-only mode.

---

## 5. The phases (each = one shippable version: server + tests + console desk + phone where it applies)

### A0 - Foundation (no taxpayer data yet) - BUILT v0.807.0 (package `server/app/bahi/`, routes `/api/bahi/*`, desk `bahi.js`; see HISTORY)
- `bahi/` package: the register tables (`acc_docs`, `acc_lines`, `acc_parties` with GSTIN / PAN / Udyam / MSME class / bank details
  history, `acc_rules`, `acc_periods` with lock state, `acc_events` audit trail), the rules-as-data files with source + checked_on, the
  confidence / reason / draft model.
- `bahi/wb.py` client + `acc_gst_conn` + the sealed credentials + the call meter; **a sandbox contract test** that runs every call we
  use against `apisandbox.whitebooks.in` with the sandbox GSTIN and OTP 575757 and RECORDS the real response shapes (the specs do not
  document success bodies - this is where `txn`, `refid`, `int_tran_id`, `auth-token`, IRN / AckNo shapes get pinned). vps-ops job
  `wb_check` (the sandbox keys live on the VPS; the job prints pass / fail per call, never a key).
- Hub: `accounts` live as **GST & Accounts** (does / needs / never filled), hiring adds the desk and gates no existing tool (EDU_OPEN law).
- Console: its own page **GST & Accounts** (`static/console/bahi.js`, view `accountsdesk`) - home (this month's state: what is filed, what is due, what needs her),
  then tabs per phase as they land. Deskroom's one-tool-per-employee shape does not fit an employee that spans gst / paisa / office /
  payroll, so it gets a real page like the Leads / Film desks.
- Adapters (read-only into the register): appmaker + website orders, gstp docs, thok bills / purchases, office bills, analyst fin_items.

### A1 - GST connect + public checks
- The connect walk (section 4), token state on the desk, revoke instructions.
- Supplier checks with NO OTP: `/public/search` (GSTIN active / cancelled / suspended, legal name), `/public/rettrack` (did the supplier
  file GSTR-1 / 3B for the period - drives Rule 37A and the "supplier not filed" nudge), `/public/pref` (QRMP). Replaces the paid gstinapi
  lookups for GST status (gstinapi stays for what WhiteBooks lacks).
- `gstp.fetch_2b` / `ims_apply` move from the Computer Operator to the API (the browser path stays as the fallback when the API is down).

### A2 - The monthly ITC loop (IMS + 2B) - the most time-consuming GST step, done well
- Pull IMS invoices (all sections) + 2B; match against the purchase register with `gstp.reconcile` (kept) + the register.
- A proposal per record with a REASON: accept (matched), reject (wrong GSTIN / not ours / duplicate), pending (goods not received -
  s.16(2)(b), credit-note dispute), each with confidence; one tap per group.
- Her tap -> `ims/save` -> poll status -> `gstr2b/gen2b` + `get2b` (the recompute the portal needs after the 14th) -> the Table 4 ITC draft.
- Supplier nudges drafted for her to send (wa.me / her approved template) for records missing from 2B; Rule 37 (180 days unpaid) and Rule
  37A (supplier not filed by 30 Sep) watches.

### A3 - GSTR-1 / 1A, before the lock
- One outward register from every source; `gstp.gstr1_json` extended (the 2025 HSN B2B / B2C split, exports, nil / exempt, advances,
  e-commerce tables - today's stated gaps) and checked with `/gstr1/validatehsnsum`.
- The pre-11th check: missing invoices, B2B reported as B2C, wrong GSTIN, rate vs HSN, e-invoice IRNs that GSTN has but the register lacks
  (`/gst/einvoice/irnlist`).
- Save -> summary -> file on her EVC OTP; GSTR-1A for corrections found after GSTR-1 but before 3B (the only fix since the July 2025 lock).

### A4 - GSTR-3B + payment
- Compare Hoola's `prepare_gstr3b` with the portal's `/gstr3b/autoliab` + `syscalcintrst`; every difference shown with its cause.
- Save -> the least-cash set-off plan (`rules.set_off`, kept) -> `retoffset` on her approval -> if cash is short, a PMT-06 challan (CPIN) she
  pays at her bank -> file on her EVC OTP. Interest shown exactly as the portal will compute it (it can no longer be lowered).
- CMP-08 for composition dealers on the same walk.

### A5 - e-invoice + e-way bill
- An IRN from any Hoola invoice (appmaker, thok, office, the vertical desks' series) on her tap; INV-01 v1.1 built from the register;
  every response persisted first; timeouts recovered via GETIRNBYDOCDETAILS; duplicates (2150) adopted; the IRP (NIC1 / NIC2) stored per IRN.
- The 30-day IRP window (AATO >= Rs 10 cr) watched daily ("4 invoices expire in 3 days"); the 24-hour cancel window shown on the card;
  cancel the EWB first (2174).
- E-way bill from the IRN or standalone (`logistics/ewb.py` field mapping reused), Part-B / vehicle updates, extend, consolidate; the
  180-day document and 360-day validity limits checked before the call.
- Signed QR + IRN printed on Hoola's invoice PDFs (receipt.py / thok / shopplus).

### A6 - Bills in, checked (the WhatsApp wedge)
- A structured GST-invoice extractor (GSTIN, invoice number, date, place of supply, HSN, quantity, rate, taxable, CGST / SGST / IGST, cess,
  total) - local OCR first (existing `ocr` / `docread`), a vision call only when weak, every field cross-checked by arithmetic and by the
  supplier's GSTIN status; the result is a DRAFT purchase with confidence + reason, never posted silently.
- Intake from WhatsApp (her own number / the business inbox), forwarded email (the mailbox `bills_payments` bucket), photos and PDFs in chat,
  PC files; duplicate and bill-protection checks at intake.

### A7 - Bank + UPI reconciliation (stored)
- Statement import: PDF (incl. password-protected - she types the password once into the box, never stored), Excel / CSV, MT940.
- UPI narration parsing (`UPI/<RRN>/<payer>/<VPA>`), gateway settlement splits (Razorpay / Cashfree reports via `paygate`), match keys
  UTR / RRN -> amount + date window -> learned payer VPA; each match carries its reason; a "Categorise" holding tab for what it cannot place.
- A stored bank reconciliation statement (uncleared cheques, bank-only, books-only) per month; `enterprise/calc.reconcile` + `analyst`
  rules reused.

### A8 - Payables, receivables, TDS
- One party master (GSTIN, PAN + PAN-status flag, Udyam + micro / small / medium, agreed days, bank details with change history).
- Ageing from the register; MSME 15 / 45-day alarms (s.37(2)(g) of the 2025 Act) before 31 Mar; Rule 37 180-day; collections reminders
  drafted in her voice and sent by her tap (existing reminder / khata paths), with a payment link (paygate) - STOP respected.
- **TDS on payments**: the s.393 table as DATA (read from the primary text first - research 03 marks the item numbers UNVERIFIED; reconcile
  with `audit/rules.py` :149), the TDS on each payment worksheet, the challan due by the 7th, the quarterly Form 140 data (the FVU file her
  CA uploads - there is no public deductor API), 26AS / AIS match (`finops.tds_reconcile`, kept).
- A vendor payment run as a bank bulk file she uploads (payroll's NEFT file pattern) - never paid by Hoola.

### A9 - Her book (Tally / Zoho) and the CA hand-off
- Export: the register -> Tally XML / JSON vouchers (extends `appmaker/tally.py` to purchases, receipts, payments, journals with GST tax
  ledgers), imported by her or her CA; Zoho Books via OAuth (her consent) - read her org's chart of accounts, write DRAFT entries.
- Live Tally: today's bridge is in the FROZEN PC code (`desktop/`, `server/app/pc/`) - reading her ledgers live needs her explicit freeze
  exception (D3); without it, Tally stays export / import.
- **The monthly CA pack** (ZIP): vouchers in Tally format + source documents + the GSTR-1 / 2B / 3B worksheets + the bank reconciliation +
  open questions; her CA can mark a month CLOSED (locks it).

### A10 - Month-end, year-end, calendar
- Close checklist per month (bank reconciled, IMS done, 1 / 3B filed, TDS deposited, payroll posted, accruals listed) with evidence links.
- MIS from the register (sales, GP, cash, receivables, payables) - the voice / WhatsApp daily cash line ("aaj Rs 42,300 aaya, Rs 18,900
  gaya, kal Sharma ji ka Rs 12,000 due") batched into one message.
- GSTR-9 / 9C drafts from `/gstr9/getautocal` + `get8adetails` + the register; the s.16(4) 30 Nov ITC cliff, Rule 37A, the rolling
  3-year filing bar, DIR-3 KYC, MSME-1 half-yearly - all in the calendar (`compliance/` + `gstp` calendar, merged, rules as data).
- The nightly accuracy sweep (Puzzle-style, in code): same party in several ledgers, same narration across parties, round-sum cash, rate vs
  HSN, Sec 34(3) cash limits (from `audit`), each flag with a fix button.

### A11 - CA practice mode (after her own business works)
- Many client GSTINs under one CA (`gst_clients` already exists): per-client connect, a portfolio view (who is filed, who is blocked on
  what), document chase over WhatsApp, the monthly packs. Needs the D2 agreement.

### A12 - The proof: the ACCOUNTS card
- `python -m app.quality accounts`: a fixed set of documents, statements and periods run end to end against the WhiteBooks SANDBOX (connect,
  IMS loop, GSTR-1 save + summary, 3B save + offset, IRN generate / recover / cancel, EWB) and against planted traps (duplicate bill,
  cancelled supplier GSTIN, changed bank details, B2B as B2C, a locked-period edit, a guessed rate) - scored in code; vps-ops
  `accounts_card`. No live filing ever happens in the card.

---

## 6. Voice and chat

- Tools: one `accounts` tool (+ `accounts_dekho` reads) with actions per phase; the existing `gst` / `paisa` / `office` / `payroll` tools stay
  for their own users. On a call, `accounts_dekho` reads are declared (everyday questions: dues, GST this month, cash today); every change
  goes through `santosh_kaam` and a card.
- Words that admit the family: GST, GSTR, 3B, ITC, IMS, e-invoice, IRN, e-way bill, TDS, bill, khata, baaki, hisaab, bank reconcile, CA.
- Answers in her language rules (English default per `hoola_language`), numbers only from tool results.

## 7. Data, safety, privacy
- New tables nullable-safe, registered in `db.init_db` + `ensure_table()`; `acc_events` is append-only (who / what / when / before / after).
- GST data stays per tenant; no other tenant ever sees it; exports only on her tap.
- PAN / Aadhaar of parties masked in model-visible text (the existing `pii.mask_sensitive`); bank account numbers last 4 only.
- Passwords (IRP / EWB) sealed; OTPs never stored; WhiteBooks keys only in `.env`; the EWB password scrubbed from logs.
- A kill switch `accounts_enabled` and a separate `accounts_filing` (filing calls refused when off - prepare-only mode).

## 8. Decisions only the owner can make
- **D1 The book.** (a) only sit on her existing book (Tally / Zoho) - Hoola keeps no register; (b) **[recommended] Hoola keeps a working
  REGISTER of every document (not a full double-entry ledger) and exports vouchers to her book** - small shops with no book get khata +
  register + the CA pack; (c) a full double-entry ledger in Hoola (a much bigger build, and CAs resist a shadow book).
- **D2 WhiteBooks for many users.** Sign a written ASP / reseller agreement with WhiteBooks (their Terms require it) - until then production
  connects only her own GSTINs. Also ask them for: the per-call rate card, which calls are billed, success response shapes, session
  lifetimes, and whether production uses IP allow-listing.
- **D3 Live Tally.** Reading / writing her Tally live needs an exception to the Mera PC freeze; otherwise export / import only.
- **D4 Who pays the WhiteBooks calls** - included in Hoola or passed through; and the daily call cap per tenant.
- **D5 The first pilot.** Her own business GSTIN(s), sandbox first, then production for her GSTIN only.

## 9. What to do right now (owner)
1. Sign up / log in at the WhiteBooks Developer Hub, open **Credentials**, and put the SANDBOX keys in the VPS `.env` with the names in
   section 4 (`WHITEBOOKS_ENV=sandbox`). Never paste them in chat.
2. Say **GO A0** - Phase A0 is safe on sandbox keys alone and pins the real response shapes before anything touches her GSTIN.

## 10. Not in this plan (said plainly)
ITR filing (needs an ERI registration - Type 2 API - which Newtika does not hold); TDS return FILING (no public deductor API - the FVU goes
through her CA / TIN-FC); Account Aggregator bank feeds (needs a regulated FIU partner); DSC signing; payroll redesign (the v0.94 engine stays,
its ceilings re-checked against the PF Rs 25,000 change when EPFO notifies it); statutory / tax audit opinions (the `audit` desk prepares,
the auditor signs).
