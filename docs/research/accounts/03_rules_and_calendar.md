# Accounts Assistant research 03 - the job, the rules, the calendar (Indian SMBs, as of 11 Nov 2026)

**Honesty first.** Most government portals did not answer from the research sandbox (gst.gov.in, tutorial.gst.gov.in, einvoice1,
ewaybillgst, mahagst, esic, udyamregistration, taxinformation.cbic.gov.in; incometaxindia.gov.in + mca.gov.in 403). Primary pages read:
incometax.gov.in (ERI types), sahamati.org.in (FAQ / FIU), cbic-gst.gov.in (home + advisory listings). Everything else is secondary
(Taxguru, Taxmann, Taxscan, TaxTMI, Trilegal, BDO, Mondaq, Business Today / Standard, Tally, Busy), often quoting the notification by
number and date. Tags: **[V-PRIMARY]** read on a government / SRO page; **[SECONDARY-CONFIRMED]** two+ independent secondary sources
agree (cite the notification before hard-coding); **[UNVERIFIED]** memory or one weak source.
**The design law this forces: every due date, rate, threshold and form number lives in DATA with `source` + `checked_on`, never in code**
- this one year renumbered the whole Income-tax Act, added three GSTR-3B locks and moved the EPF ceiling.

## 1. The accountant's real job (practice, not law)
- **Daily**: vouchers (sales, purchases from PDFs / WhatsApp photos / paper, payments, receipts, contra, journals, petty cash) with GST
  rules that matter at entry (place of supply -> IGST vs CGST+SGST, the GSTIN captured - it drives GSTR-1 and ITC); **bank + UPI entries -
  the biggest daily grind in shops** (dozens to hundreds of small credits, narrations like `UPI/CR/<RRN>/<name>/<VPA>`, gateway settlements
  net of MDR / refunds to split back to gross); cash book + petty cash; e-invoice / e-way bill (often the dispatch clerk).
- **Weekly**: receivables ageing + reminders + udhaar; payables - who to pay (MSME 45-day rule, GST Rule 37 180 days); stock (GRN vs bill,
  stock journal, job work); chasing missing purchase bills.
- **Monthly**: purchase register vs GSTR-2B + IMS and acting in IMS before 3B (**the most time-consuming GST step**); GSTR-1 / IFF; GSTR-3B;
  TDS deduct at payment / credit, deposit by the 7th, PAN-validity check; payroll (PF ECR + ESI by the 15th, PT, salary TDS); month-end
  close (BRS, accruals / prepaids, depreciation, GST ledgers vs books, key-party confirmations, owner MIS: sales, GP, cash, receivables, payables).
- **Quarterly**: TDS / TCS statements (31 Jul / 31 Oct / 31 Jan / 31 May), advance tax (15 Jun / Sep / Dec / Mar), QRMP returns + CMP-08,
  TDS certificates, ITC-04.
- **Yearly**: finalisation + stock valuation, fixed-asset register + depreciation (Companies Act + Income-tax), tax audit (old 44AB = new
  s.63 / Form 26), statutory audit, ITR, GSTR-9 / 9C by 31 Dec, ROC (AOC-4, MGT-7/7A, ADT-1, DPT-3, MSME-1 half-yearly, DIR-3 KYC now
  triennial), exporters' LUT by 31 Mar.
- **Where time + penalties concentrate** (practice view): (1) ITC matching + chasing non-filing / wrong-GSTIN suppliers; (2) bank / UPI
  reconciliation + gateway splits; (3) TDS mistakes (wrong section / rate, inoperative PAN -> higher rate, late statements, expense
  disallowance); (4) late 3B (auto-computed 18% interest that cannot be edited down); (5) the MSME 45-day disallowance at year end;
  (6) e-way bill detentions; (7) ROC Rs 100/day uncapped additional fees.

## 2. GST in November 2026
**2.1 GSTR-1 / 1A / 3B and the locks.** GSTR-1 by the 11th; QRMP IFF (months 1-2) and quarterly GSTR-1 by the 13th [UNVERIFIED current].
GSTR-1A (2024): optional amendment / addition for the same period after GSTR-1 and BEFORE 3B [SECONDARY-CONFIRMED].
**From the July 2025 tax period the auto-populated outward liability in 3B (from GSTR-1 / 1A / IFF) is NON-EDITABLE - fix only via GSTR-1A
before 3B** (GSTN advisory June 2025) [SECONDARY-CONFIRMED]. From the November 2025 period Table 3.2 (inter-state to unregistered /
composition / UIN) is also locked [SECONDARY-CONFIRMED]. **From the January 2026 period interest on a late 3B is system-computed into Table
5.1 of the NEXT period's 3B - can be raised, not lowered**; rule 88B(1) cash-ledger benefit auto-applied; a "Tax Liability Break-up" table
auto-filled from document dates; IGST may be paid from CGST / SGST ITC in any order once IGST ITC is used (advisory 30-01-2026) [SECONDARY-
CONFIRMED]. ITC Table 4 still editable, pre-filled from 2B; one source says filing may be BLOCKED on an ITC vs 2B mismatch from Jan 2026
[UNVERIFIED - treat as warn-or-block]. GSTR-2B static on the **14th**; IMS changes after the 14th need **"Recompute GSTR-2B"** before 3B.
**2.2 IMS.** Launched 14 Oct 2024: Accept / Reject / Pending per supplier record; no action = deemed accepted at 2B generation. Legal backing
Finance Act 2025, in force **1 Oct 2025** (Notification 16/2025-CT, 17 Sep 2025): s.34(2) recipient reverses ITC on a supplier credit note;
s.38 statement built on recipient actions [SECONDARY-CONFIRMED]. Oct 2025 changes: some credit notes / downward amendments may stay Pending
for a limited time; the recipient can declare the actual ITC to reverse; a rejected credit note goes back onto the supplier's liability
[SECONDARY, time limits unconfirmed]. IMS Offline Tool 21-22 Apr 2026. **The assistant's monthly core loop**: pull IMS -> match the purchase
register -> propose accept / reject / pending WITH a reason (not received under s.16(2)(b), wrong GSTIN, duplicate, rate mismatch, credit-
note dispute) -> owner / CA taps -> recompute 2B -> reconcile with the Table 4 draft.
**2.3 ITC conditions** [long-standing, UNVERIFIED on primary]: s.16(2) invoice + receipt + supplier paid tax + return filed; s.16(2)(aa) +
rule 36(4) only as in 2B (since 1 Jan 2022); **s.16(4) time limit = 30 Nov of the next FY or the annual return, whichever earlier**
(s.16(5)/(6) relief for 2017-18 to 2020-21); **Rule 37** supplier unpaid 180 days -> reverse with interest, re-claim on payment; **Rule 37A**
supplier has not filed 3B by 30 Sep of next FY -> reverse by 30 Nov, re-claim when filed; s.17(5) blocked credits.
**2.4 Reverse charge** [UNVERIFIED]: s.9(3) services (GTA unless forward charge, advocates, sponsorship, directors, security from non-body-
corporate (Oct 2024), commercial rent from unregistered to registered (Oct 2024; composition later excluded)); self-invoice within 30 days
(rule 47A, Nov 2024); RCM paid in CASH then claimed as ITC.
**2.5 E-invoicing**: mandatory B2B + exports when AATO > Rs 5 cr in any year since 2017-18 (Notification 10/2023-CT, 1 Aug 2023)
[SECONDARY-CONFIRMED]; **30-day reporting rule for AATO >= Rs 10 cr from 1 Apr 2025** (advisory 5 Nov 2024) [SECONDARY-CONFIRMED]; MFA
mandatory on e-invoice + EWB portals; a B2B invoice without a required IRN is not valid - buyer's ITC at risk.
**2.6 E-way bill**: from 1 Jan 2025 no EWB on a base document older than 180 days (errors 820 / 4043); total validity incl. extensions max
360 days [SECONDARY-CONFIRMED]; Rs 50,000 threshold (states may differ for intra-state); 2026 "Ship-to GSTIN" + voluntary closure possibly on
hold [UNVERIFIED].
**2.7 GST 2.0**: 56th Council (3 Sep 2025) -> slabs **0 / 5 / 18 / 40%**, 12% + 28% removed, precious metals special rates stay, effective
**22 Sep 2025** [SECONDARY-CONFIRMED; notification numbers UNVERIFIED]. Compensation cess removed for most goods; tobacco / pan masala moved
later (~Feb 2026) and the **Health Security se National Security Cess (HSNS Act No. 35 of 2025)** applies to pan masala etc. [V-PRIMARY:
CBIC home lists the Act, HSNS Cess Notifications 01-03/2026, HSNS RET-01 advisories]. No confirmed 57th / 58th Council rate outcomes found.
**=> the HSN -> rate master needs a DATED rate history** (old rates for invoices before 22 Sep 2025; credit notes use the original's rate).
**2.8 Annual, QRMP, fees, interest, the 3-year bar** [mostly UNVERIFIED amounts]: GSTR-9 31 Dec (optional up to Rs 2 cr AATO), 9C above
Rs 5 cr; QRMP up to Rs 5 cr, PMT-06 by the 25th, quarterly 3B 22nd / 24th by state group; late fees s.47 (Rs 50/day, Rs 20 nil; caps by AATO
Rs 2,000 / 5,000 / 10,000, nil Rs 500; GSTR-9 Rs 200/day capped 0.04%-0.5% of turnover); interest s.50 18%; **the 3-year filing bar
(Notification 28/2023-CT) is IN FORCE: barring from 1 Dec 2025 (Oct 2022 GSTR-1 / 3B and FY 2020-21 GSTR-9 barred), rolling** [SECONDARY-
CONFIRMED].
**2.9 How software files**: GSTN does not open APIs to arbitrary apps - a **GSP** holds the pipe, an **ASP** works through a GSP. Taxpayer
consent: gst.gov.in > My Profile > **Manage API Access** -> enable, pick the GSP-ASP pair + duration -> per-session OTP -> a refreshable token;
per GSTIN. Since the July 2025 security advisory she is mailed / texted whenever an ASP takes OTP consent (ASP, GSP, time, validity); the
portal has View Logs (30 days), **Revoke Active Token**, View Revoked Token; a new GSP-ASP authorisation may be needed even if old access
works. **Filing itself still needs her EVC (OTP) or DSC** - a preparer uploads and saves, she signs and submits = "it prepares, she files".
E-invoice / EWB via IRPs (NIC einvoice1/2 + private IRPs) through a GSP or direct credentials (direct mainly for large taxpayers).

## 3. Income tax
**3.1 The Income-tax Act, 2025 is in force from 1 Apr 2026** [SECONDARY-CONFIRMED]: "previous / assessment year" -> one **"tax year"**;
amounts paid / credited up to 31 Mar 2026 stay under the 1961 Act, from 1 Apr 2026 the 2025 Act; FY 2025-26 returns are 1961-Act returns.
**Income-tax Rules, 2026** notified 20 Mar 2026 (effective 1 Apr 2026, ~500 -> 333 rules, every form renumbered).
**3.2 TDS / TCS**: s.192 salary -> **s.392**; 194A / C / H / I / J / Q / O / R / M / IA / 195 etc. -> **s.393 one table** (Table 1 residents,
2 non-residents, 3 any person; each entry has a payment code, e.g. 1008/1009 rent, 1029 dividend, 1064/1065 cash withdrawal; quoting 1961
sections fails validation); 15G/15H -> s.393(6) Form 121; TCS s.206C -> **s.394**; TAN / statements s.397; certificates s.395. Rates /
thresholds "largely carried over": contractors 1% (individual / HUF) / 2% (others) item 6(i); old 194M item 6(ii); professional 10% Rs 30,000
(technical 2%; item numbering disputed); rent 2% machinery / 10% land-building above Rs 50,000/month; commission Rs 20,000; old 194Q
(0.1% above Rs 50 lakh, buyer turnover > Rs 10 cr) = item **8(ii)**; **TCS on sale of goods 206C(1H) OMITTED from 1 Apr 2025** (194Q alone).
**Read the s.393 table text before coding any rate** (could not be opened) [UNVERIFIED at item level]. Hoola's `audit/rules.py` :149 already
carries an s.393 detection table - reconcile it against the primary text.
**3.3 Forms (Rules 2026)** [SECONDARY-CONFIRMED]: 24Q -> **138**, 26Q -> **140**, 27Q -> **144**, 27EQ -> **143**, Form 16 -> **130**, 16A ->
**131**, 16B-16E -> 132, 27D -> 133, 26QB-26QE -> 141, 26QF -> 142, 15G/15H -> 121, 12BB -> 124, 12BA -> 123, 13 -> 128, 24G -> 137,
15CA/15CB -> 145/146, 27C -> 127, **3CA/3CB/3CD (tax audit) -> Form 26 under s.63**.
**3.4 Due dates**: TDS deposit by the 7th (March by 30 Apr); statements Q1 31 Jul, Q2 31 Oct, Q3 31 Jan, Q4 31 May; TCS statement 15th after
the quarter; Form 130 by 15 Jun; Form 131 within 15 days of the statement due date [UNVERIFIED under the new rules]. Advance tax 15 Jun 15% /
15 Sep 45% / 15 Dec 75% / 15 Mar 100% (presumptive 100% by 15 Mar) [UNVERIFIED carry-over]. ITR AY 2026-27: ITR-1/2 31 Jul 2026; **ITR-3..7
non-audit business / profession 31 Aug 2026 (permanent Finance Act 2026 change to s.139(1))**; tax audit report 30 Sep 2026; audit-case ITR
31 Oct 2026; TP 30 Nov 2026 [SECONDARY-CONFIRMED]. Revised returns up to 12 months from the end of the tax year (31 Mar 2027), fee from 1 Jan
(Rs 5,000 / Rs 1,000 if income <= Rs 5 lakh). Tax audit penalty reported as flat Rs 75,000 (<= 1 month late) / Rs 1.5 lakh from TY 2026-27
[SECONDARY, single]. Audit thresholds (old 44AB) Rs 1 cr / Rs 10 cr with <= 5% cash; profession Rs 50 lakh (75 lakh presumptive) [UNVERIFIED].
**3.5 MSME 45 days**: old 43B(h) = **s.37(2)(g)** of the 2025 Act (MoF Rajya Sabha reply 21 Jul 2026), from TY 2026-27 [SECONDARY citing an
official reply]; micro + small (not medium) suppliers; deductible only when paid unless paid within MSMED s.15 (15 days without a written
agreement, max 45 with one). => a vendor master with Udyam number + category + a "days outstanding vs 15 / 45" alarm before 31 Mar.
**3.6 Filing via software**: **[V-PRIMARY]** incometax.gov.in ERI page - Type 1 (Department utilities via the portal), **Type 2 (own software
filing through the Department's API)**, Type 3 (offline utilities). [SECONDARY] registration under Others > e-Return Intermediary;
undertaking + bank guarantee (Type 1), plus an audit report for Types 2 / 3; Type 2 passes sandbox tests (erihelp@incometax.gov.in); APIs:
login, **Add Client (taxpayer validates by OTP)**, e-Verify, acknowledgement; she still e-verifies. **TDS statements are NOT filed via the ERI
API** - prepared with Protean RPU / FVU and uploaded on the portal (TAN login) or via a TIN-FC; no public deductor API [UNVERIFIED for the
138 / 140 era].

## 4. Payroll statutory
**Labour Codes: all four in force from 21 Nov 2025** [SECONDARY-CONFIRMED]; **Central Rules notified 8 May 2026** (where the Centre is the
appropriate government; under the SS Code also private establishments in more than one state); most states had not notified final rules by
mid-2026 (Gujarat had) - so state rules govern many points. Payroll points: one wage definition - **basic + DA >= 50%** of remuneration
(excess excluded allowances added back -> higher PF / gratuity / bonus / leave base); PF / ESI contribution RATES unchanged; gratuity for
fixed-term after 1 year; standard appointment letter (update within 3 months, OSH Central Rules); wages by the 7th, F&F within 2 working days
[UNVERIFIED]; one annual return (OSH, Central).
**PF**: ECR + payment by the **15th**; employee 12% / employer 12% (8.33% EPS up to the ceiling + 3.67% EPF) + EDLI + admin [UNVERIFIED admin
rates]; **wage ceiling Rs 15,000 -> Rs 25,000 approved by Cabinet 16 Sep 2026** (~51 lakh more workers) - **effective date + EPS treatment
UNVERIFIED: read the EPFO notification before changing payroll logic**; late = 12% interest (7Q) + 14B damages. **ESI**: by the 15th; 0.75% /
3.25%; wages up to Rs 21,000 (Rs 25,000 disability) [UNVERIFIED]. **Professional Tax (Maharashtra)**: men <= Rs 7,500 nil, 7,501-10,000 Rs 175,
> Rs 10,000 Rs 200 (Rs 300 in February, Rs 2,500 a year); women nil up to Rs 25,000 [conflicting]; PTRC monthly if last year's liability
>= Rs 1 lakh else annual [UNVERIFIED]; PTEC Rs 2,500/yr; **due dates moved to the 15th by the MH PT (Amendment) Rules 2026 (notification
28 Feb 2026, rule 11(3))** - PTEC 15 Jun, periodic PTRC 15th of next month (read the notification) [SECONDARY]. Other states differ; some
(Delhi, UP, Haryana) have none - a per-state data table. **Salary TDS**: s.392; Form 124 (old 12BB) claims, Form 123 perquisites; Form 138
quarterly; Form 130 by 15 Jun; new regime default with Rs 12 lakh effective nil + Rs 75,000 standard deduction (Finance Act 2025) [UNVERIFIED
carry-over].
Hoola's `payroll/` (v0.94) already does LOP, OT, the 50% rule, EPF / ESIC / PT / TDS, ECR text, ESIC sheet, F&F, bonus - check its ceilings.

## 5. MSME
Udyam: free, self-declared, Aadhaar + PAN; 2025 Budget classes micro <= Rs 2.5 cr investment / Rs 10 cr turnover, small <= 25 / 100, medium
<= 125 / 500 [UNVERIFIED]; turnover / investment pulled from ITR + GSTN. **MSME Form 1** (MCA s.405, 2019 order): companies owing micro /
small (not medium) suppliers beyond 45 days from acceptance; half-yearly **30 Apr (Oct-Mar) / 31 Oct (Apr-Sep)**; LLPs / firms /
proprietors don't file [SECONDARY-CONFIRMED]. Samadhaan: the MSE supplier applies, the state MSEFC conciliates / arbitrates; MSMED s.16
interest = compound **3x RBI bank rate** monthly rests, s.23 non-deductible. **TReDS** mandatory for companies with turnover > Rs 250 cr +
all CPSEs (MSME notification 7 Nov 2024, by 31 Mar 2025) [SECONDARY-CONFIRMED].

## 6. Bank data
**AA**: **[V-PRIMARY]** Sahamati FAQ - FIPs + FIUs must be licensed regulated entities (RBI, SEBI, IRDAI, PFRDA, DoR); "a Fintech startup not
regulated ... cannot be an FIU"; TSPs are the only unregulated participants (they implement APIs, never consume data in their own name); each
AA publishes a board-approved pricing policy. => Hoola cannot pull bank data via AA itself; routes = statement upload, connected-banking
partners, or a regulated FIU partner (consent artefacts, purpose codes, retention limits).
**Statements + UPI pain** [practice]: PDF (often password = DOB / PAN based), bank-specific Excel / CSV, MT940 / CAMT.053 from corporate
net-banking; hundreds of small UPI credits, `UPI/<RRN>/<payer>/<VPA>/<bank>`, no invoice reference, soundbox / QR batch settlements, gateway
payouts net of MDR / refunds / chargebacks (need the settlement report to split), reversals + failed-then-credited duplicates. Match keys:
**UTR / RRN, amount + date window, payer VPA learned from history**.
**Bank APIs** (shape, UNVERIFIED): ICICI, HDFC, Axis, Kotak, Yes, IDFC corporate APIs (balance, statement, NEFT / RTGS / IMPS / UPI payouts,
beneficiaries, webhooks) need a current account + corporate onboarding + IP whitelist + mTLS + maker-checker; usually consumed through a
platform (Tally, Zoho, RazorpayX, Open). Reads realistic via a partner; payments stay her tap.

## 7. Compliance calendar (monthly GST filer, employer, TDS deductor, Maharashtra; Co = private limited, Prop = audited proprietor)
| Day | What | Who | If missed |
|---|---|---|---|
| 7th | TDS / TCS deposit (March -> 30 Apr) | Co, Prop with TDS | interest 1%/month not deducted, 1.5%/month deducted not paid; expense disallowance [UNVERIFIED new-Act numbers] |
| 10th | GSTR-7 / GSTR-8 | if applicable | late fee + interest |
| 11th | GSTR-1 | both | Rs 50/day capped; buyers lose ITC visibility |
| 13th | IFF (QRMP) | QRMP | - |
| 14th | GSTR-2B generated; IMS actions then Recompute 2B | both | wrong ITC: interest + penalty |
| 15th | PF ECR + payment; ESI | employers | 12% + damages |
| 15th | MH PT PTRC (moved to the 15th; check) | employers | interest + late fee |
| 20th | GSTR-3B + payment (QRMP 22nd / 24th; PMT-06 25th) | both | 18% auto interest (not editable down); late fee capped by AATO; 3-year bar after |
| always | e-invoice within 30 days (AATO >= Rs 10 cr); EWB before movement | both | invalid invoice, buyer ITC denied, s.122 / s.129 |
| always | Rule 37 - supplier bills unpaid at 180 days | both | ITC reversal + interest |

| Month | Items | Penalty |
|---|---|---|
| Apr | 30 Apr March TDS; **MSME-1** (Oct-Mar); GSTR-4 (composition); ITC-04 half-yearly | s.405(4); GSTR-4 late fee |
| May | 31 May Q4 statements (138 / 140 / 144); Q4 TCS (143) 15 May | Rs 200/day (old 234E) up to the TDS; Rs 10k-1 lakh (old 271H) |
| Jun | 15 Jun advance tax 15%; Form 130; MH PTEC; 30 Jun DPT-3; **DIR-3 KYC triennial** (G.S.R. 943(E) 31 Dec 2025) | interest; DIN deactivated + Rs 5,000 |
| Jul | 15 Jul Q1 TCS; 31 Jul Q1 TDS statements; ITR non-business | as above |
| Aug | **31 Aug ITR non-audit business / profession** | Rs 5,000 / 1,000 + interest; loss c/f barred |
| Sep | 15 Sep advance tax 45%; **30 Sep tax audit (Form 26)**; AGM; ADT-1 | Rs 75k / Rs 1.5 lakh (reported) |
| Oct | 25 Oct ITC-04; **31 Oct audit-case ITR; MSME-1 (Apr-Sep); Q2 statements**; AOC-4 ~30 Oct | ROC Rs 100/day uncapped |
| Nov | **30 Nov s.16(4) last date for last FY's ITC + Rule 37A reversals**; MGT-7/7A ~29 Nov; TP ITR | ITC lost for ever; ROC Rs 100/day |
| Dec | 15 Dec advance tax 75%; **31 Dec GSTR-9 / 9C**; revised ITR fee-free till 31 Dec | Rs 200/day capped |
| Jan | 31 Jan Q3 statements; revised ITR fee from 1 Jan | |
| Feb | MH PT Rs 300 month; Form 124 proofs | |
| Mar | 15 Mar advance tax 100%; **MSME 45-day year-end check (s.37(2)(g))**; LUT; new invoice series; CMP-02; MH PT annual (15 Mar); 31 Mar revised ITR window closes | MSE dues not deductible; 3x bank-rate interest |
Event-driven: GST registration / amendment / cancellation / refunds; Forms 145 / 146 before foreign remittances; property TDS (Form 141 within
30 days); ROC board meetings (4/yr, <= 120-day gap), MGT-14, CHG-1.

## 8. What this means for the design
1. Rules as DATA with `source` + `checked_on`: dated HSN -> rate history (before / after 22 Sep 2025); s.393 old -> new map; form map
   (24Q -> 138 ...); state PT tables; PF / ESI ceilings (watch the Rs 25k date); every due date.
2. The monthly loop: bank + UPI recon -> purchase register vs IMS (accept / reject / pending proposals) -> owner / CA taps -> recompute 2B ->
   GSTR-1 / 1A draft checked BEFORE 3B (3B liability is locked to it) -> 3B draft with interest as the portal will compute it -> TDS worksheet
   (s.393 entry, rate, PAN status) -> PF / ESI / PT sheet -> MIS pack.
3. Year-end watchers: MSE vendors past 15 / 45 days; Rule 37 at 180 days; non-filing suppliers (Rule 37A); the 30 Nov s.16(4) cliff; the
   3-year GST bar on any unfiled return; DIR-3 KYC per director.
4. Filing channels: GST via a GSP (her API enable + OTP + EVC / DSC); ITR via an ERI (Type 2 API or an ERI partner); TDS statements as FVU
   files the CA uploads. Every submit + payment = her tap.
5. Bank data: uploads + connected-banking partners first; AA only via a regulated FIU partner.

## Still needs a primary read before a hard rule is coded
(1) the s.393 table text (items, rates, thresholds); (2) TDS due dates under Rules 2026; (3) the Jan 2026 3B advisory number + whether an
ITC mismatch BLOCKS filing; (4) IMS credit-note pending limits; (5) the EPF Rs 25k effective date + EPS treatment; (6) the MH PTRC monthly
due date; (7) late-fee / penalty amounts (GST caps, s.405(4), new-Act 234E / 271H / 234B-C equivalents); (8) Udyam thresholds; (9) whether
the EWB Ship-to-GSTIN change is live.

## Sources
Primary: incometax.gov.in/iec/foportal/help/eri/servicesavailable (ERI types) · sahamati.org.in/faqs/ (FIU must be regulated, AA pricing
policy, TSPs) · cbic-gst.gov.in (HSNS Act 35/2025, HSNS cess notifications 01-03/2026, 2FA advisory).
GST: taxmann.com gstn-enhances-gstr-3b-interest-and-itc-functionality + taxscan.in (advisory 30-01-2026) · mahagst.gov.in advisory 386 Table
3.2 (listed, unreachable) · elplaw.in (June 2025 3B lock) · taxguru.in gst-amendments-finance-act-2025 + bdo.in (Notification 16/2025-CT,
s.34 / s.38 from 1 Oct 2025) · treelife.in (GST 2.0, 3B block claim) · business-standard.com + taxguru.in (IMS Oct 2025) · taxo.online
(IMS Offline Tool 22.04.2026; 3-year bar) · taxmann.com + taxscan.in (3-year bar) · taxscan.in + tallysolutions.com (e-invoice 30-day rule,
Rs 5 cr) · binarysemantics.com + busy.in (EWB 180 / 360 days, 2026 proposals) · business-standard.com + scconline.com (56th Council) ·
tallysolutions.com + taxmann.com (ASP / GSP, API access, OTP alerts).
Income tax: india-briefing.com (s.393) · taxguru.in tabular TDS · blog.tdsman.com 2026/06 (form map) · businesstoday.in 2026-03-11 +
taxscan.in (Rules 2026, Form 26) · taxguru.in + incometaxindia.gov.in tutorial 71 (206C(1H) omitted, 194Q) · businesstoday.in 2026-06-17 +
busy.in (31 Aug ITR, revised returns, audit penalty) · taxguru.in (43B(h) = s.37(2)(g)) · tinpan.proteantech.in + incometax.gov.in
api-specifications (ERI).
Payroll / MSME / MCA: trilegal.com (Central Rules 8 May 2026) · mondaq.com + greythr.com (Codes in force, 50% rule) · scconline.com
2026/09/17 + businesstoday.in (EPF Rs 25k) · taxguru.in (MH PT due dates) · bankbazaar.com + kredily.com (MH PT slabs) · jurishour.in +
thetaxcorp.in (MSME-1) · mondaq.com + taxmann.com (TReDS Rs 250 cr) · taxguru.in + legalraasta.com (DIR-3 KYC triennial).
