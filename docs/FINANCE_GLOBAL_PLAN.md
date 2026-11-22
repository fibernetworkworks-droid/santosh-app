# Finance & Banking AI Employees - the global build plan

Owner, 22 Nov 2026: *"AI EMPLOYEE MUST BE GENERALIZE -- THAT FROM SMALL BUSINESS TO ENTERPRISE LEVEL CAN USE THIS. EVEN IF USER
WANTS TO USE IT PERSONALLY IT CAN BE ---- THUS PREPARE A PERFECT BACKEND, FRONTEND, LOGIC AND STRATEGIC PLAN FOR BUILD FOR THIS
PHASE WISE"*, after the global register (`docs/research/banking_finance_industry/01_GLOBAL_REGISTER.md`, 516 roles).

This is a plan. Nothing in it is built yet. Read sections 1-3 before writing any code; section 8 is the order of work.

---

## 0. The answer in one page

1. **One employee, every size.** A person, a sole trader, a 50-person business, an accounting firm with 300 clients and a bank all
   hire the same employee (for example *Books & Accounts*). What changes with size is **configuration, not code**: who uses it,
   how many books it holds, which parts are switched on, who must approve what, and how much is recorded. Size is read once at
   setup into a **workspace profile**.
2. **Every country is data.** Tax rates, filing dates, payment rails, regulators, ombudsmen, refund rules, credit bureaus and
   e-invoicing formats live in **country packs** (`fin/packs/<CC>.json`). Every value carries its source, `checked_on` and
   `review_by`. An unchecked value is never used in a calculation: Hoola says *"check this for <country>"*. India becomes one pack
   among many; there is no India-only branch in code.
3. **516 roles become 18 employees with parts.** A customer does not want 516 hires. The register's roles are grouped into **18
   employees**, each with up to ~20 **parts** (the way the ERP desk has 16 parts). The workspace size decides which parts show.
4. **One data spine.** Every employee reads and writes the same **money facts**: entities, books, accounts, transactions,
   documents, parties, obligations and cases. A bank statement imported for the bookkeeper is the same row the cash forecaster,
   the tax preparer and the loan-readiness check read.
5. **Arithmetic in code, never in the model.** Interest, APR, tax, FX, ageing, matching, ECL, DCF, ratios and payroll are pure
   functions with tests. The model picks the job and writes the words; the numbers come from code, each traceable to a document.
6. **The laws are in code, the same at every size.** Money never moves without her tap; the 13 tier C acts are refused by one
   gate module; PIN / OTP / CVV / card numbers / passwords are refused; approvals are bound to a hash; institutions get
   maker-checker on every send.
7. **Build order.** F0 foundation (profile, packs, laws, calc, data spine; today's finance engines moved onto it with no
   behaviour change) → F1 money safety worldwide → F2 household money → F3 business books worldwide → F4 tax worldwide → F5 payroll
   + cash → F6 credit both sides → F7 firm mode → F8 payments → F9 institution mode (financial crime, compliance, risk) → F10
   investments + markets → F11 inclusive + Islamic + digital assets → F12 public sector + proof.

---

## 1. The scale model - one employee, five sizes

### 1.1 The five sizes

| Size | Who | Example |
|---|---|---|
| **Personal** | One person or a household | A salaried person, a pensioner, a family |
| **Solo business** | Sole trader, freelancer, landlord | A plumber, a designer, a gig driver |
| **Business** | SME with a team (2-500) | A shop chain, a clinic, a manufacturer |
| **Firm** | Serves many clients' money | Accounting / CA / CPA firm, financial adviser, broker, bookkeeper |
| **Institution** | Regulated, high volume | Bank, credit union, lender / NBFC, payment firm, fund manager, insurer-adjacent, regulator, government |

A workspace can hold more than one: a business owner's workspace can also keep her household; a firm's workspace holds client
workspaces.

### 1.2 What changes with size (configuration only)

| | Personal | Solo | Business | Firm | Institution |
|---|---|---|---|---|---|
| **Users** | Her (+ family members she invites) | Her (+ her accountant read-only) | Team with roles | Staff + each client sees only their own | Teams, roles, departments, SSO |
| **Books** | Household ledger | One business book + household | One or more entities, branches | One book per client | Many entities, cost centres, products |
| **Approvals** | Her tap | Her tap | Roles + money limits (like Support G10) | Partner review before anything leaves | Maker-checker always; four-eyes on sends |
| **Autonomy** | Hoola does admin freely, sends only on her tap | Same | Trust ladder per part (Learning / Partner / Trusted) | Drafts only; partner sends | Drafts only; named officer decides / files |
| **Volume** | Hundreds of rows | Thousands | Up to millions | Millions across clients | Millions a day, batch imports |
| **Data sources** | Statement upload, open banking, her mail | + gateway, marketplace | + accounting system, payroll, bank feeds | + client portals, practice software | Core banking, data warehouse, APIs |
| **Audit trail** | Simple history | Simple history | Append-only log | Per-client log + reviewer sign-off | Full audit, retention per pack, export |
| **Storage** | SQLite (as today) | SQLite | SQLite / Postgres | Postgres | Postgres, own region |
| **Language** | Hers | Hers | Per user | Per user + per client | Per user |
| **Tier allowed** | A | A | A + B for her own staff | A + B (the licensed person in the firm signs) | A + B (named officer) |

The rule: **a part never changes behaviour by size in code** - it reads `profile.approval_for(action)`,
`profile.autonomy(part)`, `profile.store()` and `profile.audit_level()`. Adding a size later is a profile row, not a code change.

### 1.3 Setup (8 questions, like Support G0)

1. Who is this for? (me / my household / my business / clients of my firm / my institution)
2. Which countries? (residence + where money is earned / held / taxed; several allowed)
3. Base currency (and others in use)
4. Entity type (individual, sole trader, partnership, company, trust, non-profit, bank, lender, broker, fund, payment firm, public body) - from the country pack's list
5. Year end / tax year (from the pack, she can change)
6. What do you want help with? (ticks from the 18 employees; Hoola recommends from her answers)
7. Where is your data? (bank, accounting system, payroll, broker, files) - connect now or later
8. Who else works on it? (invite people, pick their role)

Answers → `profile.preview()` (what will be switched on, which packs, which deadlines) → her tap on the hash → `profile.apply()`.
She can change any answer later; a change shows what moves.

---

## 2. The 18 employees (the register grouped)

Each employee = one Hub entry, one desk, one chat, one tool pair `fin_<key>` / `fin_<key>_dekho`, a list of parts. Ids in
brackets are register ids (`01.37` = part 01 role 37 in the register). Sizes: P personal, S solo, B business, F firm, I institution.

| # | Employee | Sizes | Main parts | Register ids (examples) | Hoola today |
|---|---|---|---|---|---|
| 1 | **Money Safety** | P S B F I | Scam check before paying, scam refund claim, card dispute, complaint & ombudsman letter, credit report check + dispute, identity theft recovery, senior money guardian, deposit-protection check. *Institution side:* scam case preparer, dispute & chargeback case preparer, complaints handler | 01.37, 01.38, 03.1, 01.43, 01.31, 01.39, 01.40, 01.42, 01.11, 01.8, 01.9 | paisa_sahayak (scam, upi, complaint, charges) |
| 2 | **Household Money** (personal CFO) | P S | Budget & cash flow, bills & due dates, subscriptions, savings goals, net worth, forgotten money finder, retirement readiness, benefits & credits check, family finance, student / renter / expat / gig modes, bereavement admin, will & nominee check | 01.21-01.29, 01.45, 01.49-01.51, 01.53-01.64, 01.66 | Wallet (bills on her tap), vitt goal |
| 3 | **Books & Accounts** | S B F I | Bookkeeping, receipts, bills in (AP), invoicing, credit control (AR), cash application, bank & card reconciliation, fixed assets, inventory cost, multi-currency + intercompany, month-end close, consolidation | 07.1-07.13, 07.20-07.21 | bahi (India), vitt ageing / three-way |
| 4 | **Tax** | P S B F I | Personal return organiser, sole-trader quarterly updates, VAT / GST returns, e-invoicing clearance, sales tax, cross-border e-commerce tax, withholding & treaty relief, corporate return prep, tax provision, transfer pricing, Pillar Two data, R&D credits, tax notices, tax calendar | 01.46-01.48, 07.34-07.52 | gst + bahi GSTR / e-invoice (India), vitt advance tax / TDS |
| 5 | **Payroll & People Costs** | S B F I | Payroll prep, time & overtime check, payroll tax & social security filings tracker, benefits & pension contributions, contractor payments + information returns, household employer, global payroll / EOR coordinator | 07.14-07.19, 07.53 | payroll (India) |
| 6 | **Cash & Treasury** | S B F I | Cash-flow forecast, SME mini-treasurer, bank accounts & mandates, bank fee analysis, FX exposure + hedge proposal, debt & covenant tracker, short-term investment policy check, intercompany netting, hedge accounting docs. *Bank:* ALM / IRRBB, liquidity returns, FTP, ALCO pack | 07.27, 05.72-05.85 | - |
| 7 | **Credit & Lending** | P S B F I | *Borrower:* loan shopper & cost explainer, business-loan readiness, invoice / supply-chain finance, trade finance, insolvency helper. *Lender:* intake, income verification, statement analysis, spreading + credit memo, underwriting rule hits, KFS / disclosure, documentation & CP checker, servicing, collections (ethical), loss mitigation, EWS, covenants, ECL, portfolio, securitisation, syndication | 01.33, 02.1-02.14, 02.15-02.78 | paisa_sahayak loans, vitt credit_memo, risk_desk underwrite / kfs / dpd / ecl |
| 8 | **Payments** | P S B F I | *Merchant:* acceptance setup, chargeback representment, chargeback prevention, payments reconciliation, fee audit, dunning, marketplace payouts, export proceeds, corporate cards. *Payment firm / bank:* KYB onboarding, merchant risk, dispute ops, exceptions, settlement recon, safeguarding, ISO 20022 messages, scheme rules tracker, licensing returns, remittance ops, mobile-money agent network | 03.13-03.24, 03.25-03.58 | - |
| 9 | **Investments & Wealth** | P S F I | Portfolio statement reader, fees check, capital gains & tax lots, retirement income planner, pension switch explainer, tax-advantaged accounts, scam & unsuitable-product check, derivatives reality check. *Adviser firm:* fact-find, meeting notes, suitability letter draft, plan builder, rebalancing drift, tax-loss harvest prep, annual review evidence. *Asset manager / fund admin:* research associate, NAV check, transfer agency, fund reporting, LP documents, ESG disclosure | 04.1-04.91, 05.1-05.14 | risk_desk portfolio |
| 10 | **Markets & Post-Trade** | F I | Broker onboarding & service desk, margin notices, best-execution report, pitchbook & comps, model builder & checker, due-diligence data room, IPO drafting, research associate, confirmations, settlement fails, SSI, reconciliation breaks, corporate actions, withholding reclaims, collateral, investor relations, disclosure calendar, equity plans | 05.15-05.71 | risk_desk order ticket / dcf / round trips |
| 11 | **Financial Crime** | B F I | KYC / CDD review, UBO mapping, EDD & PEP research, periodic KYC refresh, sanctions hit review, AML alert triage, SAR / STR narrative draft, fraud case investigation, mule networks, correspondent banking checks, travel rule, crypto monitoring, risk assessment, MLRO report | 06.1-06.17, 03.59-03.61 | vitt aml_triage / sanctions, risk_desk velocity |
| 12 | **Compliance** | S B F I | **Compliance Officer for One**, regulatory change scanner, obligation register & control map, policy writer, monitoring & testing, financial promotions review, licence & obligations calendar, inspection readiness, remediation tracker, complaints MI, consumer-duty outcomes, regulatory returns preparer, statistical returns | 06.18-06.36, 06.50-06.56, 06.79-06.80 | regtech (enterprise) |
| 13 | **Risk** | B F I | Credit portfolio, ECL, market risk, counterparty, operational risk + RCSA, incident & breach clocks, model risk + AI governance, stress testing, risk appetite pack, recovery planning, third-party / DORA register, resilience map, cyber questionnaires, privacy ops | 06.37-06.49, 06.57-06.62 | risk_desk ecl |
| 14 | **Audit & Controls** | B F I | PBC coordinator, audit staff assistant, internal audit planning / fieldwork / report, SOX / ICFR testing, forensic analysis, grant & donor audit | 06.63-06.68, 07.55-07.59 | audit |
| 15 | **Governance & Company Secretary** | B F I | Board & committee packs and minutes, statutory filings calendar, cap table, fit & proper, related-party monitor, whistleblowing case log, ethics training, anti-bribery due diligence | 06.69-06.75, 07.65-07.67 | - |
| 16 | **CFO Office** | S B F | Budget & forecast, management accounts & KPIs, variance & profitability, business cases, board & investor pack, startup finance setup, fractional CFO assistant, grants & incentives, ESG / carbon reporting | 07.26-07.33, 07.68-07.73 | paisa (analyst), bahi month-end MIS |
| 17 | **Community & Inclusive Finance** | P S B I | Micro-business cash book (voice), savings-group records, chit / ROSCA safety, microfinance borrower coach + MFI field assistant, farmer finance + crop claim prep, remittance comparer, migrant & refugee money, women & youth coach, Islamic personal finance + zakat, Islamic SME structures, mobile-money helper | 08.1-08.36, 01.19, 03.10 | - |
| 18 | **Digital Assets** | P S F I | Crypto holdings records + tax, wallet safety check, stablecoin acceptance, VASP onboarding, custody reconciliation, CASP licensing returns, stablecoin reserve attestation, token due diligence, crypto surveillance | 03.11-03.12, 03.24, 03.59-03.70 | - |

**Plus Practice mode** (not an employee, a mode of the firm size): client list, client switcher, client onboarding, engagement
letters, requests to clients, review queue, client portal. It rides every employee above (F7).

**Public sector** roles (benefits caseworker, regulator / supervisor assistants, deposit insurer, G2P reconciliation,
development finance - 08.37-08.64) are parts of employees 1, 2, 11, 12, 13 and 17 under the Institution size with entity type
`public_body`. They come last (F12) because they sell slowly.

**Existing tools map onto the new employees** and keep their names as aliases so nothing breaks: `paisa_sahayak` → 1 / 2 / 7;
`vitt_sahayak` → 2 / 3 / 4 / 7 / 11; `risk_desk` → 7 / 9 / 10 / 13; `bahi` (GST & Accounts) → 3 / 4; `payroll` → 5; `gst` → 4;
`audit` → 14; `paisa` (analyst) → 16; enterprise `bank_int` / `regtech` → 8 / 12; Wallet → 2.

---

## 3. The six laws (same at every size, in code)

1. **Money never moves without her tap.** No part sends a payment, transfer, remittance, order or settlement instruction. Bill
   pay and transfers go through Hoola Wallet / her own banking app on her tap (and her fingerprint for money on the phone). An
   institution's payment release is its own system's maker-checker - Hoola prepares the file.
2. **Tier C is refused by one gate.** `fin/laws.py` holds the 13 tier C acts (register list) as data; every `fin_*` tool calls
   `laws.check(action, profile)` before it runs. Refusals say what Hoola can do instead (prepare the file for the named person).
3. **No secrets in chat.** PIN / OTP / CVV / card number / password refused everywhere (existing rule). Account and ID numbers
   are masked in model context; the ID locker and sealed credentials (existing) are reused.
4. **Figures come from data.** Every number in a reply or document is produced by `fin/calc` from rows on the data spine, and
   carries `source` (document / row / pack value). The checker (existing pipeline checker) sends back any figure with no source.
5. **Rules come from checked packs.** A calculation needing a rate, threshold, deadline or form reads the country pack; a value
   with status `verify` (not checked) stops that calculation and says *"check this for <country>"*. Packs are never edited by the
   model.
6. **The decider is named.** Every tier B output names the role that decides / signs (from the profile: "Credit officer: Priya",
   "MLRO: John"). Approvals and sign-offs are bound to the hash of exactly what was shown.

Two extra rules for regulated places, also in code:
- **Advice wording guard.** Personal-size answers explain options and maths; they never say "you should buy / switch / invest in
  X". The guard rewrites or flags; licensed-advice requests go to the firm's adviser or to the country's free advice service
  (from the pack).
- **EU AI Act and similar.** Credit scoring of people and some insurance pricing are high-risk uses under the EU AI Act (Annex
  III, from memory - verify). Parts that touch creditworthiness of natural persons in the EU run only as tier B for an institution
  that holds the obligations, keep logs, and show the human override. Same pattern for other countries' AI rules as the packs
  name them.

---

## 4. Backend plan

### 4.1 Modules (new `server/app/fin/`)

```
fin/
  profile.py      workspace profile: size, entity type, countries, currencies, year end, people, roles, autonomy, approvals
  spine.py        the data spine models + service (entities, books, accounts, txns, documents, parties, obligations, cases)
  packs/          country packs  <CC>.json   + sector packs  sector_<kind>.json
  pack.py         load, validate (schema), status / freshness, value_of(cc, key, on_date) -> Value | Unchecked
  calc/           pure functions: money, interest/apr, amortise, tax (pack-driven), fx, ageing, match, payroll,
                  ecl, dcf, ratios, forecast, gains (tax lots), covenants
  laws.py         tier C gate, money-out refuse, advice guard, secret refuse, decider naming
  sources/        importers + connectors: csv, ofx, qif, mt940, camt053, pdf statements, open-banking adapters,
                  accounting systems (via enterprise run.py), gateways (read), brokers (read), payroll systems (read)
  cases.py        a "case" = a piece of work (dispute, claim, return, KYC file, audit request) with states + clocks
  calendar.py     obligations from packs x profile -> due dates, reminders, the Today list
  evidence.py     provenance + audit log (append-only), exports
  desks/          one module per employee (18): parts = functions over spine + calc + packs, return drafts / cards
  api.py          /api/fin/*  (profile, packs, spine, cases, calendar, desks, exports, webhooks)
  tools.py        fin_<key> + fin_<key>_dekho tool specs + handlers (registered in agent/tools.py)
```

Existing modules (`finguard`, `finops`, `riskdesk`, `bahi`, `payroll`, `gst`, `enterprise`) are **not deleted**: in F0 their
calculations move behind `fin/calc` and their data behind `fin/spine` adapters; their tools become aliases of the new desks.
Tests for the old tools must stay green.

### 4.2 The data spine (tables)

| Table | What | Notes |
|---|---|---|
| `fin_workspace` | Tenant + profile (size, entity, countries, base currency, year end, autonomy) | One per workspace; a firm has one per client |
| `fin_entity` | Legal entity / person / household | Multi-entity for business and institution |
| `fin_book` | A ledger per entity (chart of accounts from the pack or her system) | Household book = simple categories |
| `fin_account` | Bank, card, wallet, loan, investment, payable, receivable account | Masked number, institution, currency |
| `fin_txn` | Transactions | Amount as integer minor units + ISO 4217 currency; FX rate + source; dedup key; source row |
| `fin_doc` | Documents (bills, invoices, statements, contracts, notices, returns) | Bytes in the files store; fields read out with confidence |
| `fin_party` | Customers, suppliers, employees, lenders, counterparties | Tax ids validated by the pack's check rules |
| `fin_obligation` | Something owed or due (tax, filing, payment, covenant, renewal) | From packs x profile or from documents |
| `fin_case` | Work items with state, owner, clock, decider | Disputes, claims, returns, KYC files, audit requests |
| `fin_draft` | Prepared outputs waiting for the decider (letters, returns, files, packs) | Hash-bound approval |
| `fin_event` | Append-only audit log | Who / what / when / hash; retention from the pack |

Rules: money is never a float (integer minor units + currency, `Decimal` in calc); every row has `source` and `workspace_id`;
the firm size adds `client_id`; institution size writes to Postgres (existing `dbmove.py` path) and partitions `fin_txn` by
month.

The existing GST & Accounts register (`acc_docs`, `acc_bank_lines`...) becomes the first source adapter into the spine, not a
second copy: the spine reads it through a view until F3 moves it.

### 4.3 Country packs

Schema (one file per country, checked by `pack.validate` in CI):

```
{ "cc": "GB", "name": "United Kingdom", "currency": "GBP", "languages": ["en"], "version": 3,
  "sections": {
    "rails":        { "instant": {"value": "Faster Payments", "source": "...", "checked_on": "2026-11-20", "review_by": "2027-05-20", "status": "checked"} , ... },
    "regulators":   { ... }, "ombudsman": { ... }, "scam_refund": { ... }, "fraud_report": { ... },
    "credit_bureaus": { ... }, "open_banking": { ... }, "deposit_insurance": { ... },
    "tax": { "vat_rates": ..., "vat_dates": ..., "income_tax_bands": ..., "year_end": ..., "e_invoicing": ..., "withholding": ... },
    "payroll": { ... }, "entity_types": [ ... ], "id_checks": { "vat_number": "regex + check digit rule" },
    "consumer_credit": { "apr_method": ..., "cooling_off_days": ... },
    "free_advice": { ... }, "holidays": { ... }, "data_law": { ... }, "retention_years": ...,
    "ai_rules": { ... } } }
```

- Every leaf is `{value, source, checked_on, review_by, status}`. `status` is `checked` only when a person opened the official
  page on `checked_on`. Research values start as `verify`.
- `pack.value_of()` returns `Unchecked` for `verify` or past `review_by`; calc refuses on `Unchecked` and the reply says which
  value to check.
- **Floor pack** (like the Telecaller's `world.py`): every country without a pack gets a safe floor - explanations, budgeting,
  document reading, maths with her own numbers - and no rule-dependent output (no tax, no deadlines, no refund rules).
- **Sector packs** (`sector_bank`, `sector_lender`, `sector_broker`, `sector_payment_firm`, `sector_fund`, `sector_vasp`,
  `sector_public`): which returns, registers and clocks a regulated firm of that kind has in each country.
- A vps-ops job `fin_packs_check` reports stale values; the console shows pack freshness per country.
- Starting material: register part 08 Part 2 (45 countries), the GST & Accounts `bahi/rules/*.json` (India, already in this
  shape), the Telecaller `callcentre/world.py` (242 countries' floor + 29 law packs).

### 4.4 Calculation library (`fin/calc`)

Pure, deterministic, fully tested; no I/O; inputs include the pack values they use, outputs include a trace.

- `money` (add / split / round per currency's minor unit and the pack's rounding rule), `fx` (rate with date + source)
- `interest` (simple, compound, flat-to-reducing), `apr` (method per pack: US Reg Z actuarial, EU APRC, UK APR, India IRR...),
  `amortise`, `prepay`, `debt_plan` (snowball / avalanche)
- `tax` engines driven by pack tables: VAT / GST (rates, place of supply, reverse charge), income tax bands, withholding,
  payroll contributions; each country's quirks as pack data, not code branches
- `ageing`, `match` (bank ↔ book, three-way, invoice ↔ payment; reasons + confidence), `dedup`
- `forecast` (cash 13-week / 30-60-90, from obligations + history; confidence bands)
- `gains` (tax lots: FIFO / average / specific per pack)
- `ecl`, `dcf`, `ratios`, `covenant`, `liquidity` (LCR / NSFR from inputs), `fees` (statement fee finder)
- Reuses today's tested code from `finguard/loans.py`, `finops/*.py`, `riskdesk/*.py`, `bahi/*` (moved, not rewritten).

### 4.5 Sources and connectors (read first, write later)

| Kind | Personal / Solo | Business / Firm | Institution |
|---|---|---|---|
| Bank data | Statement upload (CSV / OFX / QIF / PDF), open banking per region (see below) | + bank feeds via accounting system | MT940 / CAMT.053 files, core-banking extract, API |
| Open banking | India AA, UK OBIE, EU PSD2 (through a licensed aggregator), US aggregator, AU CDR, Brazil Open Finance, Saudi / UAE open banking - each in the pack with its status | same | same |
| Accounting | - | QuickBooks, Xero, Zoho Books, Tally, MYOB, Sage, NetSuite, SAP B1 via `enterprise/run.py` (plan → dry run → her tap) | SAP / Oracle / Dynamics via `enterprise/run.py` |
| Tax portals | Official APIs only, per pack (India GSP, UK MTD, EU e-invoicing networks / Peppol, Saudi ZATCA, Malaysia MyInvois ...) | same | same |
| Payments | Her wallet / UPI / card statements | Gateway + marketplace settlement reports (read) | Scheme reports, dispute portals (read) |
| Payroll | - | Payroll system export / API (read) | HR / payroll system |
| Investments | Broker / depository statements (CAS etc.), broker read APIs | same | Custodian files |
| Credit reports | Her own downloaded report (we never pull a bureau on her behalf unless the pack names a consumer route) | Business credit reports she provides | Bureau under the institution's own contract |

Every connector: keys typed in the app or the VPS `.env`, sealed, never in chat; read scopes first; any write follows the
enterprise run path (plan → dry run → her tap → batches → verify, idempotency key per row).

### 4.6 Cases, calendar and jobs

- `fin_case` states: `open → gathering → drafted → waiting_decider → sent / filed by human → tracking → closed`; each state
  change is an event; every case has a clock from the pack (dispute windows, refund deadlines, filing dates, regulator SLAs).
- `calendar.build(profile)` turns pack obligations into dates for this workspace; the worker slot `fin_jobs` refreshes daily,
  sends reminders (reusing push + the reminder ladder from Support G9), and opens a case when a due date nears.
- Batch imports (institution volume) run as background jobs with progress, resume after restart (the turn-inbox / job pattern).

### 4.7 API

`/api/fin/profile` (get / preview / apply), `/api/fin/packs` (list, one, freshness), `/api/fin/spine/*` (import, accounts, txns,
docs, parties), `/api/fin/cases/*`, `/api/fin/calendar`, `/api/fin/desk/<key>/*` (parts, run a part, drafts, approve),
`/api/fin/export/*` (CSV / XLSX / PDF / the pack for an accountant), `/api/fin/hooks/*` (signed webhooks for firms and
institutions). Institution size adds API keys with scopes (reuse the Hoola API wallet pattern) and SSO (OIDC / SAML) in F9.

### 4.8 Tools for the agent

18 tool pairs `fin_<key>` (actions = parts) + `fin_<key>_dekho` (read the desk). Old tool names stay as aliases in
`agent/tools.py`. Family words for admission per employee. Voice: only the `_dekho` readers are declared on a call; changes go
through `santosh_kaam` (existing rule).

---

## 5. Logic plan (how a request flows)

```
her words / an event / a due date
  → which employee + part (router on family words, or the desk she is in)
  → profile (size, countries, autonomy, decider)            fin/profile
  → laws.check(action)                                       refuse tier C here
  → data: spine rows + documents (import if missing, ask once)
  → pack values needed (checked? else "check this")
  → calc (code, with trace)
  → the model writes the words / letter / memo around the numbers
  → checker: every figure has a source, every rule a checked pack value, no advice wording
  → output by autonomy:
        Learning  : draft card, she taps
        Partner   : routine admin done, sends still a card
        Trusted   : routine admin + reminders done; sends still a card (money / filing never auto)
        Firm      : partner review queue
        Institution: maker → checker queue, named decider
  → case + clock + calendar tracking → tell once when done (existing deliver record)
```

Key behaviours:
- **Ask once, remember.** Missing facts (year end, VAT number, employer) are asked once and kept in the profile / spine.
- **Country is per item, not per user.** A freelancer in Germany invoicing a US client: the invoice reads the German VAT pack
  and the cross-border rules; her household reads the German personal pack. Multi-country is normal.
- **Same answer at every size, different hands.** The ECL number is the same calc for a microfinance group and a bank; who sees
  and signs it differs.
- **Explain the maths.** Every calc result can be shown step by step in her language (trace → plain sentences).
- **Honest gaps.** No pack → floor; unchecked value → "check this"; missing data → what to upload; tier C → who must do it.
- **Learning from outcomes.** Each draft's fate (sent unchanged / edited / rejected) is kept as shape only (the Prompting ledger
  pattern) to improve the part; never her figures.

---

## 6. Frontend plan

### 6.1 Console (web)

- **Finance & Banking department** in the AI Employees hub shows the 18 employees with sizes they serve; the setup wizard
  (section 1.3) runs the first time and recommends which to hire.
- **Each employee has its own section** like the SEO / Accounts / Support desks: its chat on the left (files, voice), pages on
  the right:
  - **Today** - due dates, alerts, cases waiting for her, money cards
  - **Work** - cases and drafts with state, clock and decider; open one = the document + its sources + Approve / Edit / Reject
  - **Data** - connected sources, last import, gaps ("3 months of bank statement missing")
  - **Reports** - the part's outputs (forecast, ageing, returns, packs) with Export
  - **Settings** - profile, countries + pack freshness, people + roles, approvals + limits, autonomy per part
- **Size-adaptive layout** (same pages, different density): Personal = large cards, plain words, one action each; Business =
  tables with filters; Firm = client switcher at the top + review queue; Institution = queues, maker-checker, audit view, bulk
  actions, keyboard.
- Numbers in tabular figures; currency and dates formatted by the user's locale; right-to-left for Arabic / Hebrew / Urdu;
  charts through the console chart drawer.
- Reuse: chat kit, desk room forms (deptdesk) for parts without a custom page, HoolaMenu, quality tier row, credits.

### 6.2 Phone

- Personal and Solo sizes get native screens: Money Safety (check a link / payee / QR before paying, start a refund claim),
  Household Money (Today, bills, subscriptions, goals), receipt / statement capture by camera.
- Every size gets the **approval inbox** on the phone: drafts and money cards, fingerprint for money (existing approvekey).
- Business owners get Today + approvals + a read of each desk; deep work stays on the console.

### 6.3 Client portal (firm size)

A firm's client gets a small page (no Hoola account needed, signed link like the Hoola Auto intake): upload what was asked,
answer questions, see status, sign off. Data stays in that client's workspace.

---

## 7. Strategy

### 7.1 Who first and why

1. **Personal + Solo, worldwide** (F1-F2): scams, complaints, credit reports, bills - pain is measured on every continent, tier
   A, no partner needed, and it brings users who later bring their business.
2. **Small business, worldwide** (F3-F5): books, tax, payroll, cash - Hoola's core users today; lifting the India engines to
   packs reuses most of the work.
3. **Firms** (F7): accounting / CA / CPA firms and advisers multiply reach (one firm = hundreds of clients) and pay well; tier B
   sits with their licensed staff.
4. **Small regulated firms** (F9 first parts): "Compliance Officer for One" for small lenders, payment firms, brokers, money
   services - no compliance team, clear deadlines.
5. **Large institutions** (F9-F10 rest): only with the institution mode finished (maker-checker, SSO, audit, own region).
6. **Inclusive and public sector** (F11-F12): big need, slow sales, partner-led (NGOs, MFIs, governments).

### 7.2 Country order

Order by (pack readiness × demand × our users), starting with packs we can check from official English pages:
**India (exists), United Kingdom, United States, UAE, Singapore, Australia, Canada, EU core (Germany, France, Netherlands,
Ireland, Spain, Italy), Saudi Arabia, Malaysia, Indonesia, Philippines, Nigeria, Kenya, South Africa, Brazil, Mexico**, then the
rest of the 45. Every pack ships only after a person checks its values (`checked_on`). This order is a proposal - owner
decision D2.

### 7.3 Pricing (with Hoola Credits, existing)

- Personal: free tier (scam check, complaint letter, budget) + credits for heavy work; the household desk in the personal plan.
- Solo / Business: AI-employee packages per employee (existing package mechanism), priced per region (existing regional
  prices).
- Firm: per client book per month + per seat.
- Institution: annual contract by volume (transactions / cases), own region hosting as an add-on.
- Usage is metered in credits (existing `usage.record`); a pack or a connector never costs extra.

### 7.4 The moat

1. **Checked country packs** with dates - slow to build, hard to copy, and they make every employee usable in a new country at
   once.
2. **One data spine across 18 employees** - the bookkeeper's rows feed tax, cash, credit and audit; point tools cannot.
3. **Same product from a person to a bank** - users grow inside it (household → business → firm client).
4. **Honesty in code** - figures with sources, unchecked rules said, tier C refused - the thing regulators and firms ask first.
5. **Outcome ledger** per part (shape only) improving drafts over time.

### 7.5 Risks and how the plan handles them

| Risk | Handling |
|---|---|
| Wrong rule in a country | Packs checked + dated, `Unchecked` stops calc, review_by expiry, freshness job |
| Looking like regulated advice | Advice wording guard, tier B only for licensed people, free-advice hand-off from the pack |
| Data protection (GDPR, DPDP, CCPA, PIPL, LGPD...) | Data law per pack, consent per source, export / erase (Support G11 pattern), region hosting for institutions |
| A model invents a number | Calc in code, checker rejects unsourced figures |
| Money mistakes | Money never moves without her tap; institutions' own maker-checker |
| Scale (millions of rows) | Postgres + partitioning + batch jobs at institution size; SQLite stays for personal |
| Too many employees to understand | 18 employees, parts by size, setup recommends |
| Open-banking access differs | Statement upload always works; aggregator per region chosen by the owner (D4) |

---

## 8. Phases

Every phase ships on its own with its version ritual, tests, a **card** (quality test that runs the part on fixed cases and
scores it in code, like the other cards) and a done-line. Nothing in a phase is called done that its card did not prove.

### F0 - Foundation (no new employee yet)
- `fin/profile.py` + setup wizard API; `fin/pack.py` + schema + CI validation + floor pack; packs **IN** (moved from
  `bahi/rules`), **GB**, **US** with values marked `verify` until checked.
- `fin/spine.py` tables + importers (CSV / OFX / QIF / MT940 / CAMT.053 / PDF statement reader reused from bahi).
- `fin/calc` = today's finance maths moved behind one API, with traces.
- `fin/laws.py` gate; `fin/evidence.py` audit log.
- Existing `paisa_sahayak`, `vitt_sahayak`, `risk_desk`, `bahi`, `payroll`, `gst`, `audit`, `paisa` run on the new core with
  **no behaviour change** (all their tests stay green).
- **Done when:** a workspace of each size can be created from the wizard; old finance tests green; pack check job runs.

### F1 - Money Safety worldwide (employee 1)
- Scam check before paying, scam refund claim, card dispute, complaint & ombudsman letter, credit report check + dispute,
  identity theft recovery, deposit-protection check; institution side: scam / dispute / complaint case preparers.
- Packs for the first 10 countries of 7.2 (scam refund regimes, fraud reporting, ombudsmen, dispute windows, bureaus) checked.
- Console desk + phone screens (check before paying, start a claim).
- **Card:** 60 cases across 10 countries; deadline and route correct in code; no wrong-country rule; tier C refusals hold.

### F2 - Household Money (employee 2)
- Budget & cash flow, bills, subscriptions, goals, net worth, forgotten money finder, retirement readiness, benefits & credits,
  life modes (student, renter, expat, gig, family), bereavement admin, will & nominee check. Wallet stays the only way bills are
  paid (her tap).
- **Card:** 40 households with statements in 6 countries; categorisation, forecast and bills found within set tolerances.

### F3 - Books & Accounts worldwide (employee 3)
- Bookkeeper, receipts, AP, invoicing, AR, cash application, reconciliation, fixed assets, inventory cost, multi-currency,
  close; accounting-system connectors (QuickBooks, Xero, Zoho, Tally first) through the enterprise run path.
- GST & Accounts (`bahi`) becomes the India configuration of this employee; its register moves into the spine.
- **Card:** 20 businesses' months in 6 countries; reconciliation matches, ageing and close checklist correct in code.

### F4 - Tax worldwide (employee 4)
- Pack-driven VAT / GST engine (rates, place of supply, reverse charge, returns), e-invoicing framework (clearance and Peppol
  styles) with country adapters through official routes only, sales tax (US), cross-border e-commerce tax, withholding,
  personal return organiser + sole-trader quarterly updates, tax notices, tax calendar. Filing stays the human's (tier C as
  agent) unless the pack and her licence allow and she taps.
- **Card:** returns for 6 countries computed from fixed books match hand-computed answers to the cent.

### F5 - Payroll + Cash & Treasury (employees 5 and 6)
- Payroll packs per country (contributions, payslips, filings tracker); contractor information returns.
- Cash forecast (13-week + 30-60-90), SME mini-treasurer, bank fees, FX exposure, covenants; bank ALM parts deferred to F9.
- **Card:** payroll for 6 countries matches hand-computed results; forecast back-tested on held-out months.

### F6 - Credit & Lending, both sides (employee 7)
- Borrower: loan shopper (APR per pack), business-loan readiness pack from the spine, invoice / trade finance helpers.
- Lender (Business / Institution): intake, statement analysis, spreading + memo, rule hits from HER policy, disclosure / KFS per
  pack, documents & CP checker, servicing, ethical collections (contact rules per pack), EWS, covenants, ECL.
- **Card:** APR for 10 countries' methods; memo figures traced; contact-rule violations refused.

### F7 - Firm mode (Practice)
- Client workspaces, client switcher, engagement + requests, client portal, review queue, per-client audit, firm dashboards.
- Adviser parts of employee 9 (fact-find, meeting notes, suitability draft, plan, rebalancing drift) and accountant practice
  parts (practice manager, tax research, fractional CFO - employee 16).
- **Card:** a firm with 50 test clients; isolation (no client sees another), review gate holds, drafts signed by the named person.

### F8 - Payments (employee 8)
- Merchant: acceptance setup, chargeback representment + prevention (scheme rules as sector pack), payments reconciliation,
  fee audit, dunning, payouts, export proceeds.
- Payment firm parts: KYB, merchant risk, dispute ops, exceptions, settlement recon, safeguarding, ISO 20022 checks, scheme rules
  tracker, licensing returns.
- **Card:** representment packs for 3 schemes' reason codes; reconciliation of fixed multi-gateway months.

### F9 - Institution mode + Financial Crime, Compliance, Risk, Audit, Governance (employees 11-15)
- Institution plumbing: Postgres by default, partitions, SSO (OIDC / SAML), scoped API keys + webhooks, maker-checker on every
  draft, region hosting option, retention + export.
- Compliance Officer for One first (small regulated firms), then reg change + obligations, policies, monitoring, promotions,
  calendars, returns preparer; financial crime (KYC / UBO / sanctions / AML triage / SAR drafts / fraud); risk (ECL, op risk,
  incidents, model + AI governance, third-party / DORA register); audit (PBC, fieldwork, SOX); governance (board packs, filings,
  cap table). Bank treasury / ALM parts from F5 land here.
- **Card:** an institution sandbox with 1 M transactions; alert triage and SAR drafts reviewed by a human scorer; maker-checker
  cannot be bypassed; load test.

### F10 - Investments & Markets (employees 9 rest and 10)
- Consumer investing parts worldwide (statement reader, gains, fees, derivatives reality check, scam / registration check).
- Markets and post-trade for firms and institutions (broker desk, pitchbook + models, research associate, confirmations, fails,
  reconciliation breaks, corporate actions, withholding reclaims, IR + disclosure calendar).
- **Card:** tax lots for 6 countries' methods; reconciliation breaks found on fixed files; no order ever placed.

### F11 - Community & Inclusive, Islamic, Digital Assets (employees 17 and 18)
- Voice-first micro cash book, savings groups, chit / ROSCA safety, MFI borrower + field assistant, farmer finance, remittance
  comparer, migrant / refugee money, Islamic personal finance + zakat + Islamic SME structures (Shariah rulings stay with the
  board), crypto records + tax, wallet safety, VASP / travel rule parts.
- **Card:** savings-group books in 4 countries balance; zakat calculations match a scholar-reviewed set; crypto gains match.

### F12 - Public sector + proof
- Benefits caseworker, regulator / supervisor assistants, deposit insurer, G2P reconciliation, development finance monitor.
- **Proof:** every employee's card run live on her server; at least one real user per size (personal, solo, business, firm,
  small regulated firm) using it for a month; pack freshness report clean for shipped countries.

### Summary table

| Phase | Employees | Sizes added | Countries checked at end |
|---|---|---|---|
| F0 | core (existing tools moved) | all five profiles | IN, GB, US (values may still say verify) |
| F1 | 1 Money Safety | P S (+ I case side) | 10 |
| F2 | 2 Household Money | P S | 10 |
| F3 | 3 Books & Accounts | S B | 10 |
| F4 | 4 Tax | P S B | 10 + e-invoicing countries |
| F5 | 5 Payroll, 6 Cash | S B | 10 |
| F6 | 7 Credit | P S B I | 10 |
| F7 | Practice mode + 9 adviser, 16 CFO | F | 10 |
| F8 | 8 Payments | B F I | 10 + schemes |
| F9 | 11-15 + institution mode | I | 15 |
| F10 | 9 rest, 10 Markets | P F I | 15 |
| F11 | 17, 18 | P S B I | 20 |
| F12 | public parts + proof | I (public) | 20+ |

---

## 9. Decisions only the owner can make

| # | Decision | Default if not answered |
|---|---|---|
| D1 | Approve the 18-employee grouping (or rename / split) | As in section 2 |
| D2 | Country order (section 7.2) | As listed |
| D3 | Who checks pack values (her team, a paid reviewer per country, a partner firm) | Hoola marks `verify`; nothing ships until someone checks |
| D4 | Open-banking aggregator per region (licensed partners) | Statement upload only until chosen |
| D5 | Hosting region for institutions (EU data in the EU, Gulf in the Gulf...) | Single region; institution mode waits |
| D6 | Whether tier B for firms requires checking the professional's licence number | Ask for it and show it on drafts; no automatic check |
| D7 | Pricing per size (section 7.3) | Existing credits + packages |
| D8 | Legal review of the advice wording guard and terms per region | Guard on; terms reviewed before F1 ships outside India |

---

## 10. What this plan does not do

- No money moves, no orders, no approvals, no filing as the institution, no signed opinions - ever (tier C).
- No scraping of banks, bureaus or tax portals; official routes and her own documents only.
- No country rule assumed - unchecked = said.
- Insurance itself (policies, claims) stays with the Health Insurance desks; only insurer-adjacent finance parts are here.
- The 516-role register stays the source list; a role not placed in an employee's parts is a gap to place, not to drop.
