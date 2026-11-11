# Accounts Assistant research 01 - what Hoola ALREADY has (code read, 11 Nov 2026)

Read-only inventory of the tree (paths under `server/app/`, file:line from the 11 Nov tree). **The headline: the accounting pieces
exist but live in SEVEN engines that never feed each other** - `gstp` (GST practitioner), `analyst` (books + bank), `appmaker`
gst / hisaab / tally (sales of a Hoola-built app), `thok` (wholesale), `office` (vendor bills + petty cash), `payroll`, and the
stateless `finops` / `finguard` / `enterprise` calculators - and **none keeps a double-entry ledger**. The Accounts employee mostly
ORCHESTRATES and JOINS them.

## 1. Invoicing + outward GST
- `appmaker/gst.py` (v0.355/0.356): GSTIN format + check digit (:49/:57), rates 0/0.25/3/5/12/18/28 (pre GST 2.0, no 40%), HSN/SAC per
  product, `compute` :187 CGST+SGST vs IGST by place of supply, Rule 46 `number_for` :148 INV/2026-27/0001 once per order, full credit
  notes `credit_for`/`credit` :289/:319 on CN/FY. Settings in `AppProject.backend["gst"]`. `app_banao action=gst|credit_note`,
  `GET/PUT /api/apps/{ref}/gst`. Own limits: prices GST-inclusive; "e-invoicing (IRN) and GST returns are NOT done"; no partial CNs.
- `appmaker/receipt.py` `_tax_invoice` :190 - server PDF (ReportLab, Devanagari), 15-min signed link.
- `site/shopplus.py` (v0.452) - website orders ride a hidden `_web_orders` row on the SAME INV series (`invoice_pdf` :146, `credit_on_cancel` :179).
- `thok/service.py` (v0.107) wholesale: `take_order` :464 (stock + party credit limit + e-way bill limit checks), `bill` :542 on her
  "haan", `invoice_pdf` :650; tables thok_settings / parties / items / orders / payments / purchases; tools thok / thok_dekho;
  `/api/thok/*`; phone thok_screen.dart. IRN / EWB never generated, only checked.
- `bazar/connectors/native2.py` packs gst_invoice (:125-129), quotation, udhar.
- ~13 per-vertical invoice series (editdesk, archassist, graphic, kitab, podcast, influencer, artistmgr, motiondesk, eventplan, banquet,
  frontoffice, theka RA / sub bills, mshop) - each its own series + PDF, none posts to gstp or a ledger.
- `appmaker/gstr1.py` (v0.373) `build` :54 - offline-tool JSON b2b / b2cl / b2cs / cdnr / cdnur / hsn / doc_issue for app sales;
  `GET /api/apps/{ref}/gstr1`; NOT: exports, nil/exempt, advances, amendments, e-commerce tables, the 2025 HSN B2B/B2C split.
- `retaildesk/online.py` `gst_split` :129 (stateless). `logistics/ewb.py` `bulk_json` :40 (NIC bulk upload) + optional GSP client on her
  own keys, `ewb_ready` :1065 -> `ewb_request` :1115 -> `decide_ewb` :1200 after her tap.
- GSTIN lookup: `publicapis/box.py` :174-195 (v0.765) gstin_verify / compliance / returns / hsn_code via gstinapi.in (paid, daily cap,
  bad check digit refused free); local validators gstp/rules.valid_gstin :296, appmaker/gst, native2 :43.

## 2. Purchases, ITC, GST returns - THE CORE: `gstp/` (v0.93 GST Sahayak; service.py 1,780 lines, rules.py 297)
Tables gst_settings, gst_clients (GSTIN, scheme monthly / qrmp / composition, AATO, einvoice flag, portal username only), gst_docs (sales +
purchase documents with lines, ITC flag, `paid_on` for Rule 37, problems), gst_2b, gst_returns, gst_notices, gst_learn (item -> HSN/rate,
supplier -> blocked credit). Tools `gst` / `gst_dekho` (agent/gst_tools.py); `/api/gst/*` (main.py ~8548-8718); phone gst_screen.dart from
Profile; a morning job (worker.py ~1085).
- bill entry `add_doc` :548 / `_build_doc` :466 with `rules.check_line` :236 (GST 2.0 slabs - old 12/28% flagged after 22-09-2025, HSN
  digits vs turnover, intra / inter head, arithmetic, duplicates, Sec 17(5) `blocked_hint` :261);
- `import_register` :707 - Tally / Vyapar / Busy / Excel / CSV registers (fuzzy header map `_HEAD` :604);
- `import_2b` :765 - portal JSON (b2b, b2ba, cdnr, cdnra, ecom, impg) or Excel;
- `reconcile` :837 - matched / mismatch / only_2b / only_books / ineligible / rcm + IMS accept / reject / pending SUGGESTIONS;
  `ims_decide` :906 records only her decision; `ims_apply` :943 + `fetch_2b` :925 go through the **Computer Operator browsing
  gst.gov.in**; `supplier_drafts` :967;
- `gstr1_json` :1008 / `prepare_gstr1` :1157 + review Excel;
- `prepare_gstr3b` :1206 - 3.1(a-e), 3.2, 4A ITC only from 2B minus IMS reject / pending, 4B(1) 17(5), 4B(2) Rule 37 reversal, legal
  set-off for least cash (`rules.set_off` :267), interest + late fee, GSTR-1 vs 3B mismatch (DRC-01B risk); CMP-08 :1338;
- `file_return` :1519 after her yes - the Computer Operator uploads / fills and **stops before submit**; EVC / DSC + challan stay hers;
  `mark_filed` :1550 records the ARN;
- notices (ASMT-10, DRC-01/01A/01B/01C, GSTR-3A, REG-*) with reply forms + day limits, `notice_draft` :1605; calendar :1649 (state group,
  scheme, 3-year time bar, GSTR-9 reminder).
Limits: GSTR-9 / 9C reminder only; no IRN; bill photos / PDFs read by the model via `file_read` then `gst action=bill` - no structured
GST-invoice extractor.

`office/service.py` (v0.85): `office_bills` :181 (vendor bill, due date, GST, MSME 45-day + Rule 37 180-day + duplicate checks),
`bill_add` :1302 / `bill_paid` :1332, petty cash `office_petty` :169, spend approval cards; `/api/office/bills`; NOT linked to gstp.
`thok.purchase` :954 (stock + average cost, agreed_days), `pay_supplier` :1020, `payables` :1042, TDS on purchase rule.

## 3. Bank + reconciliation
- `enterprise/calc.py` `reconcile` :215 - ref + amount first, then exact amount with date +/- days, each line once; outputs bank-only /
  books-only; STATELESS (rows passed in); tool `bank_int action=reconcile`.
- `analyst/service.py` `import_bank` :612 - Excel / CSV only (PDF -> "download Excel / CSV"), header detect, fingerprint dedupe, learned
  narration rules `fin_rules` (`set_category` :665) -> `cash` :689 (in / out, burn, runway, recurring, 13-week forecast with open bills);
  table fin_txns; `POST /api/finance/bank`; tool `paisa action=bank`. **Does not match against books.**
- `finguard/statement.py` parse_csv :68 / charges :151 / spend :203 (stateless).
- `retaildesk/online.py` `reconcile` :53 (sales vs gateway settlements net of fee); `paygate/gw.py` reads Razorpay `/v1/settlements` +
  Cashfree with her keys (:171, :305).
- `galla/` - day's takings from UPI notifications, payment-app CSVs, cash she tells it; table galla_entries; `/api/galla/*`.
- `bazar/connectors/sms_parser.py` - bank / UPI SMS she shares -> spend entries.
- `handoff/aa.py` (v0.116) - reviews an AA consent with her and hands her to her AA app; "no financial data ever comes to Hoola via AA".
- `sheetmilaan.py` (tool `sheet_milaan`) - two sheets compared by a key column.

## 4. Receivables / payables / ageing
| Piece | Storage | What | Entry |
|---|---|---|---|
| analyst FinItem (`add_item` :778, `import_items` :800, `aging` :844, `reminder_drafts` :884) | fin_items (receivable / payable, credit_days, msme, agreed_days) | ageing buckets; MSME payables at risk (15/45 days), MSMED interest 3x bank rate (analyst/rules.py :16-19) | `paisa action=bill/bills_file/bill_paid/reminders`, `/api/finance/aging`, `/api/finance/items` |
| finops/ledger.py ageing :30, three_way :53 | stateless | buckets by party; PO / GRN / invoice qty + price match (no tax / discount / freight / duplicate checks) | `vitt_sahayak` |
| thok party ledger (allocate :753 oldest-first, receive :794, cheque :837 PDC / bounced + Sec 138 dates, outstanding :875, statement_file :920) | thok_payments, thok_parties | full wholesale debtor ledger | thok |
| appmaker/khata.py | `_khata` rows, append-only | her app customers' credit + reminders | app_banao action=khata, phone app_money.dart |
| net/khata.py (v0.106) | - | credit between two Hoola businesses, mirrored | /api/net/khata |
| employee BizDue (models.py :184) | employee_dues | money customers owe (from her / a sheet / Tally); WhatsApp customers ask via biz_my_dues / biz_pay_link / biz_promise | /api/employee/dues* |

## 5. TDS / income tax
- `finops/tax.py` `tds_reconcile` :19 - books vs 26AS/AIS by (party, section); no rates / sections invented; no PAN / TAN / threshold checks.
- `audit/rules.py` :149 - **TDS table under the new Act (Sec 393, TY 2026-27)**: contractor (old 194C), professional 194J(b), technical
  194J(a), rent 194-I, commission 194H, interest 194A with thresholds + rates; `tds_nature` maps ledger words -> nature. Used only to
  DETECT missed TDS - the only reusable rate table.
- `payroll/` salary TDS (Sec 392, new / old regime). `compliance/rules.py` :207-227 TDS challan (7th), Form 140 non-salary / Form 138
  salary statements, TCS (only with a TAN); `compliance/service.py` links GST + payroll dues.
- advance tax: `finops/goals.advance_tax` :55 (from memory), `analyst.advance_tax` :951, `native2 _tax_calendar` :810.
- NOT built: TDS at payment time, challan data, Form 140 / 26Q return file, Form 16A, lower-deduction / PAN-missing logic, portal fetch of 26AS.

## 6. Tally + other software
- `appmaker/tally.py` (v0.374) `build` :86 / `voucher` :67 - app invoices / credit notes -> Tally XML Sales / Credit Note vouchers,
  configurable ledger names (`set_names` :31); `/api/apps/{ref}/tally`; "Hoola never connects to her Tally".
- **Live TallyPrime via the PC bridge (FROZEN: desktop/, server/app/pc/)**: `desktop/santosh_desktop/tally.py` reads collections on port
  9000, writes only a simple two-ledger voucher; server `bazar/connectors/pc.py` :13-49 tools `tally_report` (companies, ledgers,
  receivables, payables, sales, purchases, receipts, payments, daybook, stock, ledger) + `tally_entry` -> `tally_voucher` (Tier-2 card,
  amount_paise 0 so a spend limit can never auto-approve); needs the PC online; also `pc_do` / ax_snapshot.
- Readers of Tally exports: `analyst.parse_books` :291 (TB / P&L / BS, Tally groups, learned ledger -> head `map_ledger` :461,
  `POST /api/finance/books`); `audit.import_tb` :269 + `import_daybook` :305 (the only voucher-level Tally reader); `gstp.import_register`.
- Others: `appmaker/connect_packs.py` :85-125 zoho_books (add customer) / quickbooks (sales receipt) action packs, NOT VERIFIED; Bazar MCP
  directory: Zoho MCP (Books, Invoice, Inventory, Payroll - tools she ticks), Razorpay MCP, PayPal / Stripe / Square / Ramp / Mercury (the
  `tally` entry there is Tally.so FORMS); no QuickBooks / Xero MCP; Composio + SAP / NetSuite OData via `enterprise/run.py` (dry run ->
  plan hash approval -> idempotent batches -> verify).

## 7. Payroll - `payroll/` (v0.94)
pay_settings / employees / attendance / advances / runs; tools payroll / payroll_dekho; `/api/payroll/*`; phone payroll_screen.dart. LOP,
OT, Code on Wages 50% rule, EPF / EPS / EDLI, ESIC, state PT, TDS, advances, F&F + gratuity :925, bonus :968; files :817 = payslip PDFs,
salary register, NEFT bulk file :847, EPFO ECR `ecr_text` :804, ESIC sheet. Never pays. Posts NO journal (analyst `_payroll_cost` :536 reads it).

## 8. Reports + month-end
- `appmaker/hisaab.py` (v0.361) month ZIP of CSVs for the CA (sales / invoice / credit-note registers, HSN + rate summary, khata) - app +
  website sales only; `GET /api/apps/{ref}/hisaab`; App Studio "hisaab-zip".
- `analyst` (v0.95) TB / figures (`set_figures` :444 for photo / PDF reads) -> P&L + BS (`rules.statements` :111), bank-style ratios
  (current, DSCR, TOL/TNW, debtor / creditor / stock days) + trend, `report` :979 MIS Excel + one-page PDF, `approve_share` :1093 on her
  tap, `loan_check`, alerts, morning job; tables fin_snapshots / txns / rules / items / loans; phone finance_screen.dart (Hisaab / Cash /
  Lena-Dena / Loan).
- `audit/` (v0.96) materiality SA 320, analytics, journal-entry tests (Sundays, round amounts, back-dated, duplicates), cash rules
  (Sec 34(3)/221/219), TDS misses, Benford, sampling, confirmations, working-papers Excel - JE tests reusable as month-end checks.
- `enterprise/calc.due_calendar` :274, `compliance/` calendar + monthly certificate draft, `retaildesk/shop.py`.

## 9. Document intake / OCR
`agent/file_tools.py file_read` :36-90 = MarkItDown -> local Tesseract OCR (12 Indian languages; paid vision only when weak) -> UPI QR ->
`billparse.parse`. `billparse.py` (v0.59) invoice2data templates for UTILITY bills only (MSEDCL, Tata Power, Adani, BEST, BESCOM, TNEB,
BSES, Goa, BSNL, Jio, Airtel, Vi, MGL, IGL, MNGL) - **no GSTIN / HSN / tax lines**. Mail: `BILL_RE` (mailbox/service.py :33), triage
bucket bills_payments :922, rules can label "Bills", `email_attachment do=read` - nothing pushes mail into gstp / office_bills /
fin_items. WhatsApp: no bill intake. PC files: pc_search / pc_read.

## 10. Desks + UI
- `employee/hire.py` :92 `accounts` = live False, no does / needs / never, no group. Live finance Hub: paisa_sahayak, vitt_sahayak,
  risk_desk (FIN_GROUP), bank_int, regtech (ENT_GROUP).
- TWO employee systems: the Hub (`hire.py`, hired_employees, trust seekh / saathi / bharosa) and the older role packs `employee/roles.py`
  - role `accounts` "Hisaab-kitaab sahayak" (:256, duties collections / records / email / reminders only), `gst_practitioner` (:285,
  gst_work), `financial_analyst` (:325), `payroll_officer` (:328), `audit_assistant`, presets finance / payroll / gst_practitioner /
  audit_firm / wholesale (:551-596); a duty = a tool set (`DUTIES` :9-80).
- `employee/deskroom.py` (v0.799) - `tools_of(key)` = [key, key+"_dekho"] (**assumes the tool name = the Hub key**); spec -> forms; run
  as owner; console deptdesk.js. Phone has no deskroom client.
- Phone (from Profile): finance_screen, gst_screen, payroll_screen, thok_screen, app_money. **Web console has NO GST / Analyst / Payroll /
  Thok page** - only deskroom + App Studio's hisaab ZIP.

## Biggest gaps (an accountant does it, no code does)
1. No general ledger / chart of accounts / vouchers / opening balances / Hoola-made trial balance / period lock.
2. Nothing unified: app / website invoices, gst_docs, thok bills, ~13 vertical series, office_bills, fin_items, khata, BizDue, payroll
   never post to one book (app invoices don't reach gstp's GSTR-1 / 3B; office bills don't become gstp purchases).
3. No GST purchase-bill extraction (OCR + billparse = utility bills only); no auto-intake from mail / WhatsApp.
4. No stored bank reconciliation vs books; no PDF statements; no feed; no BRS with uncleared cheques.
5. TDS on payments not built (rates only in the audit detection table; no challan, no 26Q / Form 140 file, no 16A, no PAN-missing rate).
6. GST gaps: no GSTR-9 / 9C prep, no GSTR-1A, no IRN via an IRP API, no partial CNs, no TCS / GSTR-8, no RCM self-invoice.
7. No month-end close: checklist, accruals / prepaids, depreciation / fixed assets, closing stock / COGS, flux from Hoola's own books.
8. No vendor payment run (only payroll has a bank bulk file); three-way match on pasted rows only; no MSME Form-1.
9. No READ integration with Zoho Books / QuickBooks / Tally (Tally bridge is frozen desktop + online PC, two-ledger writes, no GST ledgers).
10. No multi-client CA bookkeeping (gstp has GST clients only).
11. No expense claims / reimbursement audit; no IT notice responder; no ITR.
12. Surfaces: no console desk for gstp / analyst / payroll / thok; deskroom's one-tool-per-key assumption does not fit an employee that
    spans gst, paisa, vitt_sahayak, office, payroll, tally_*; the old roles.py `accounts` role lacks gst_work / finance_analysis.
