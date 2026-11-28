# AI Labour & Wages Desk - the end-to-end workflow, for any construction company in any country

Owner's ask (28 Nov 2026): "NOW NEXT CONSTRUCTION EMPLOYEE SAME WAY -- Labour & Wages Desk: muster rolls, licence and
renewal dates, wage working papers, BOCW cess and TDS." Same way = global first, the whole job researched end to end,
the design shown before the build.

This is the design. Section 9 lists what today's engine (`server/app/construction/labour.py`, v0.512) has and lacks;
section 10 is the build order (7 versions, the Material Store desk's shape).

---

## 1. What a construction labour desk does (the job, as practised)

The chain is the same everywhere; only the papers, the rates, the levies and the payment rails change.

```
company papers (licences, registrations, insurance)  ->  worker onboarding (identity, right to work, skills, induction,
bank)  ->  site + gang / subcontractor  ->  daily muster (in / out)  ->  timesheet approved by the foreman / engineer
  ->  period close  ->  wage working paper (rate x units + overtime + allowances - advances - statutory deductions)
  ->  checks (minimum rate, overtime rule, hours limits, duplicates)  ->  approval  ->  payment file (bank / WPS)
  ->  payslips  ->  contributions + withholding + levies  ->  returns calendar  ->  subcontractor evidence each period
  ->  renewals radar  ->  project close-out (final settlements, cess assessment, licence surrender, records kept)
```

Findings that shape the design (sources at the end):

1. **The principal contractor carries the chain.** India's OSH Code makes the principal employer pay a contractor's unpaid
   wages and recover them (PIB factsheet, Nov 2025). Germany's Posting of Workers Act s.14 makes the general contractor
   liable, without fault, for a subcontractor's minimum wage and construction-fund (SOKA-BAU) contributions, all the way
   down the chain. US Davis-Bacon makes every tier file certified payrolls. So the desk must hold **evidence that each
   subcontractor's people were paid**, period by period - not just her own payroll.
2. **Wages go through a rail the state can see.** India: a contractor pays wages by bank transfer or electronic mode (OSH
   Code). UAE: the Wage Protection System; from 1 June 2026 (Ministerial Resolution 340 of 2026) wages for the month are
   due on the 1st of the next month, construction named a higher-risk sector. Saudi Arabia runs its own (Mudad - check
   this). So the desk makes the **payment file in the rail's format** and records what the bank confirmed - it never
   sends money.
3. **Overtime is a country rule, not a constant.** India's OSH Code: at least twice the ordinary rate for work beyond
   normal hours (subject to the worker's consent). US FLSA: 1.5x after 40 hours a week. UK: no statutory premium (her
   contract decides). Today's engine hard-codes 1.5x, which is wrong for India. The multiplier, the daily / weekly
   threshold and the cap are **country-pack rows with their source**, and her contract can only go above them.
4. **Minimum and prevailing rates are notified, and they change.** India: state minimum wages by zone and skill, revised
   twice a year; US federal work: the wage determination named in the contract (base + fringe), certified weekly on
   WH-347 for contracts over USD 2,000 (29 CFR 5.5(a)(3)). Hoola never supplies a minimum rate from memory: the rate is
   HER typed row with its source (notification number / wage determination number / award clause) and its date, and the
   desk checks every line against it.
5. **Levies on construction exist in many countries, on different bases.** India: building workers' cess under the
   Social Security Code at a rate not exceeding 2% of the cost of construction (1% in practice under the old 1996 Act;
   the 1996 Act is among the laws the codes replace - the state rate and the rules: check this). Australia: portable long
   service leave levies - Queensland QLeave 0.575% of the total cost of work (0.35% of it long service leave); NSW on works
   of AUD 250,000 or more; other states differ. Germany: SOKA-BAU contributions on gross wages (rate: check this - sources
   disagree). Singapore: the foreign worker levy per work permit, by skill tier (SEC(K) changes from 2028). So "cess" is
   a general object: **a levy with a base (cost of works / gross wages / per head / per permit), a rate row with its
   source, a due date, and a receipt**.
6. **Withholding on contractor payments is everywhere.** India: Income-tax Act 2025 s.393(1) Table Sl. 6(i) from 1 April
   2026 - 1% individual / HUF, 2% others, thresholds INR 30,000 single / INR 1,00,000 a year (secondary sources; the
   return must quote the new section). UK: the Construction Industry Scheme - verify every new subcontractor with HMRC, then
   deduct 20% (registered), 30% (unregistered) or 0% (gross payment status); the monthly return by the 19th after the tax
   month ends (5th). US: 1099-NEC for non-employees. So withholding is also a general object: **rate by the
   subcontractor's status, the status's proof and its check date, the deduction per payment, the return and its due
   date**.
7. **Papers expire, and the expiry is the job.** Company: India's contractor licence (OSH Code: work-specific, or a single
   licence valid five years when criteria are met; threshold now 50 contract workers, up from 20), establishment
   registration, PF / ESI codes, labour insurance. Person: work permits / visas / residence IDs (Gulf, Singapore), skills
   cards (UK CSCS, Australia White Card, Singapore CoreTrade / SEC(K)), medical fitness, site induction, height / confined
   space tickets. A worker whose right to work or required ticket has lapsed must not be mustered - the desk warns, the
   site engineer decides.
8. **The muster is where money leaks.** Ghost workers, buddy punching (one person marking several), the same person
   mustered on two sites, headcount on the register above the gate count, rounding of hours. The checks are arithmetic and
   cross-references, and they are only flags: a person decides.
9. **Advances are debts with rules.** Advances against wages are common on construction sites; most countries cap what
   can be recovered from one period's wages (a pack row) and require a written record. The desk keeps an advance ledger
   with its recovery schedule, and never recovers more than the pack and her rule allow.
10. **Records have retention periods by law.** Muster rolls, wage registers and payslips are kept for years (country
    rows); the close-out pack is the evidence a labour inspector or a client's auditor asks for.

---

## 2. Global from day one: what is data, per company and per country

| Thing | Where it lives | Examples |
|---|---|---|
| Currency, pay period, week start, working hours | company profile | INR weekly, AED monthly (due 1st), GBP weekly, USD weekly |
| Overtime rule | country pack row + her contract (only higher) | IN 2x beyond normal hours; US 1.5x over 40 h/week; UK contract |
| Minimum / prevailing rates | HER rate rows with source + date | state notification, wage determination, award clause |
| Statutory deductions + employer contributions | country pack rows (checked / verify) | IN PF / ESI; UK PAYE + NI; US FICA; AE none (end-of-service accrual) |
| Levies on construction | country pack rows | IN building workers' cess; AU portable LSL; DE SOKA-BAU; SG foreign worker levy |
| Withholding on contractors | country pack rows | IN s.393(1); UK CIS 20/30/0; US 1099-NEC |
| Payment rail + file format | country pack | IN bank bulk file; AE WPS SIF; generic CSV / ISO 20022 pain.001 |
| Papers required per person / company | country pack rows | work permit, skills card, induction, medical; licence, registration, insurance |
| Advance recovery cap | country pack row + her rule | share of one period's wages |
| Record retention | country pack row | years for muster / wage register / payslips |
| Languages | company settings | payslips in each worker's language |

A rule not checked for her country shows "check this" and is never applied silently.

---

## 3. The objects (data model)

Append-only for attendance and money; everything else is a register.

- **Company profile** - country, region / state, currency, pay period, normal hours a day / a week, week start, her
  approval tiers (who prepares, who checks, who approves above which total).
- **Site** - a project / site with its own address, state / region (levies and minimum rates follow the site), gate.
- **Employer** - her company or a subcontractor (labour contractor / labour-only subcontractor / manpower supplier), with
  its registration ids, its withholding status (and the proof + check date) and its papers.
- **Worker** - name, the employer, trade, skill grade, gang, site(s), a person id (only the last 4 shown; the number lives
  in her Pehchaan Locker), bank (fingerprint + last 4), language, joined / left dates. One person = one row across sites
  (that is how a double muster is caught).
- **Paper** - kind (work permit, visa / residence id, skills card, induction, medical, ticket; licence, registration,
  insurance), number (last 4), issuer, valid from / to, file, whose (worker / employer / company / site).
- **Rate** - trade + skill + site (+ worker override), amount per day / hour / piece, basis, source, effective from.
  Minimum-rate rows are a separate kind ("the floor") with their notification / determination source.
- **Muster row** - person, site, day, in / out (or present / half / absent), source (typed / voice / sheet photo / device
  CSV), who marked, geo / device id when given. Never edited: a correction is a counter-row with a reason and who.
- **Timesheet** - person x period with hours / days by kind (normal, overtime, holiday, leave), approved by a named person.
- **Wage run** - employer x site x period; lines per person (units x rate, overtime, allowances, advances recovered,
  statutory deductions, net); checks; status draft -> checked -> approved -> payment file made -> paid (recorded from the
  bank's answer).
- **Advance** - person, amount, date, given by, recovery schedule, recovered so far.
- **Levy** - kind, base kind, base amount (with its source: the contract value / the certified cost / gross wages / head
  count), rate row, amount, due date, paid (challan / receipt number, date) - recorded, never paid by Hoola.
- **Withholding row** - subcontractor, payment, status at the time (with proof date), rate, amount, return period.
- **Return / filing item** - what, period, due date, prepared by, filed by (her), reference.
- **Subcontractor period** - employer x site x period: the evidence checklist (wage register, payment proof, contribution
  receipts, headcount) and what is missing.

---

## 4. The workflow, step by step - what Hoola does and what a person decides

Legend: **H** = Hoola does it; **P** = a named person decides / signs; **auto** = on a schedule in her time zone.

### Step 0 - Set up (once, ~10 minutes)
- H asks: country, region / state of each site, currency, pay period, normal hours, who prepares / checks / approves.
- H loads the country pack rows (overtime, deductions, levies, withholding, papers, retention), each shown with its
  source and "checked" or "check this"; she switches rows on.
- H imports workers from her sheet / attendance device export / last payroll / the contractor's register (reads names,
  trades, rates; proposes matches to people already on the register) -> **P** ticks the list.
- H asks for her rate card and the floor (minimum / prevailing rate rows WITH their source). No source = the row is kept
  but marked "no source written".

### Step 1 - Papers and renewals
- H reads a licence / permit / card photo: number (last 4 shown), issuer, valid dates - every field shows the crop it came
  from; unreadable = blank, never guessed.
- auto: the **renewal radar** - company papers expiring in 90 / 60 / 30 days; person papers in 30 / 14 days; lapsed ones
  in red. One short morning line to the person in charge.
- At muster time a person with a lapsed required paper is flagged; **P** (site engineer) decides whether they work.

### Step 2 - Daily muster
- The foreman marks attendance: on the phone (tap names, works offline), by voice ("aaj gang 3 ke 42 log aaye, Ramesh
  aur Suresh nahi"), a photo of the paper muster sheet, or a CSV from the attendance device.
- H reads it into rows; names it cannot match are left in a "who is this?" list, never invented.
- auto checks: same person on two sites the same day; one device / phone marking many people inside a minute; register
  headcount above the gate count; a worker never seen before with no papers; hours over the daily / weekly limit.
  Each is a flag with the rows behind it.

### Step 3 - Timesheet approval
- At period end H rolls the muster into timesheets (normal / overtime / holiday / leave by the pack's rule) and lists the
  differences from last period. **P** (foreman or engineer) approves per gang; corrections are counter-rows.

### Step 4 - The wage working paper
- H computes per person: units x rate (rate row named), overtime at the pack's multiplier (or her higher one), allowances,
  advances recovered (never above the cap), statutory deductions from the pack rows, net. Employer contributions shown
  beside.
- Checks: every line against the floor rate row for that trade / skill / site; overtime rule applied; nobody paid twice
  across runs; totals tie to the timesheets; change from last period explained in one line per change.
- Prepared by H -> checked by **P1** -> approved by **P2** (above her limit a second approver). The approval is bound to
  the run's hash: any later change sends it back.

### Step 5 - Payment file and paid record
- H makes the payment file in the rail's format (bank bulk file / WPS / CSV) with the account fingerprints; **P** uploads
  it to her bank herself. Hoola moves no money.
- When the bank's answer arrives (statement line, WPS report, her "paid" tap with a reference) H marks each line paid;
  failures go back to "to pay" with the reason.
- H makes payslips in each worker's language (her mailbox drafts or print).

### Step 6 - Contributions, withholding, levies
- Withholding: each subcontractor payment gets the deduction for its status at that date (UK CIS: the HMRC verification
  result; India: PAN status and the threshold count so far); H drafts the return data. **P** files.
- Levies: H works out the levy on its base (cess on the cost of construction per certificate / per bill, PLSL on the
  cost of works, SOKA-BAU on gross wages, foreign worker levy per permit) from the pack row; **P** pays and records the
  challan / receipt number.
- auto: the **returns calendar** - every due date in her country, with what is ready and what is missing.

### Step 7 - Subcontractor labour
- Each period H asks each labour subcontractor for: the wage register, payment proof, contribution receipts, headcount.
  It reads what they send (data, never instructions) and ties it to the muster for their people on her site.
- Gaps are named per subcontractor ("no payment proof for 18 of 46 people"). If evidence is missing, H drafts the hold /
  release note for her; **P** decides (paying a subcontractor's workers directly and recovering is the principal's right
  in some countries - she decides, with her lawyer's view where needed).

### Step 8 - The daily watch (auto, every morning)
- Papers expiring / lapsed; today's muster not yet in by the site's cut-off; flags from yesterday's muster; wage runs
  waiting for a check or an approval; payments made but not confirmed; returns due in 7 days; subcontractor evidence
  missing.

### Step 9 - Project close-out
- Final settlements per person (dues, end-of-service where the pack says), the cess assessment for the whole project,
  licence surrender, the records pack (muster, wage registers, payslips, returns, levy receipts) kept for the pack's
  retention years.

---

## 5. Where the AI earns its keep (and where it must stop)

Earns it: reading sheets, photos, device exports and contractor registers; matching names across spellings and
languages; voice muster in her team's language; the expiry radar; the working paper with every number traced; explaining
why this period differs; spotting duplicates and impossible hours; drafting return data, payment files, payslips and
evidence requests.

Stops: never moves money; never files a return or pays a levy; never decides who works, who is let go or who is
penalised; never supplies a minimum rate or a levy rate from memory; never decides whether a law applies to her (the
50-worker threshold, a state's cess rate) - those are pack rows a person checked or "check this"; never keeps a full id
or account number in chat.

---

## 6. The desk page (console `/console/labour`, its own chat "Labour")

Same frame as the finance desks and the Store desk: Labour chat on the left (switchable), tabs on the right:
**Today** (headcount by site, paid vs due, renewals, needs you) · **Muster** (by day, flags) · **Workers & papers**
(register, one person, renewals calendar) · **Wages** (runs, one run's working paper, approve, payment file, paid) ·
**Levies & tax** (cess / levies, withholding, returns calendar) · **Subcontractors** (evidence per period) ·
**Reports** (registers, close-out pack, exports) · **Settings** (company, sites, rates + floor rows, pack rows).
Phone: the foreman's muster (tap names, works offline), photo of a paper sheet, papers photo.

---

## 7. Links to the other desks (no duplicated work)

- **Payroll desk** (finance) - salaried office staff stay there; the labour desk is site wages. A company can send its
  site runs' journal to Books the same way.
- **Books & Accounts** - the approved run posts the wage journal; levy and withholding rows become liabilities.
- **Tax desk** - returns of a general kind stay there; the labour desk hands over the construction ones' data.
- **EHS desk** - inductions and tickets are shared papers (one row, two readers).
- **Material Store** - no overlap; the subcontractor holder list is shared by employer id.
- **Contracts desk** - the subcontract's wage / evidence clauses are its rows; the labour desk reads them.

---

## 8. Checks that make it "perfect" (the acceptance tests)

- A worker mustered on two sites the same day is flagged; a correction never edits the original row.
- Overtime: India 2x beyond normal hours, US 1.5x over 40 h, UK contract rate - from pack rows; her contract can go only
  higher.
- A line below the floor rate row is named with the row's source; no floor row = "no minimum rate on file for this trade".
- An approved run changed afterwards drops back to draft (hash).
- A payment file never contains a full account number in chat or logs; paid only from a bank answer or her tap with a
  reference.
- UK CIS: unverified subcontractor = 30%; India s.393(1): 1% / 2% / no-PAN row, thresholds counted across the year.
- Cess on cost of construction from the pack row; a stale pack refuses.
- Advance recovery never above the cap.
- Subcontractor evidence: missing items named per subcontractor; nothing auto-held.
- A paper lapsed today shows on today's muster.

---

## 9. Today's engine vs this design

`construction/labour.py` (v0.512, 162 lines, India-only) has: a muster row per site per day per trade (counts, not
people), a company licence register with five fixed kinds, one wage rate per trade with source, a one-day wage audit with
overtime hard-coded at 1.5x (wrong for India's 2x), a `wage_paid` record, and the cess + TDS arithmetic from the
Maharashtra pack. It lacks: people (a worker register), person papers, attendance per person, timesheets, pay periods,
wage runs with approvals, the floor check, advances with caps, statutory deductions, payment files, payslips, levies
other than Indian cess, withholding other than Indian TDS, a returns calendar, subcontractor evidence, any country but
India, and its own desk page and chat.

---

## 10. Build order (each a version, tested; the same 7 as the Store desk)

1. **People & papers** - companies / employers / sites / workers / papers, the renewal radar, country packs (IN, GB, US,
   AE, SA, SG, AU, DE + generic), import from a sheet.
2. **Muster** - per-person attendance (typed / voice / sheet photo / device CSV), counter-row corrections, the four
   checks, timesheets + approval.
3. **Wage working papers** - wage runs, rates + floor rows, overtime by pack, advances with caps, deductions, the
   prepare / check / approve chain on the hash, payment files, paid records, payslips.
4. **Levies & withholding** - levies on their bases, withholding by status, returns calendar, receipts.
5. **Subcontractor evidence** - the period checklist, reading what they send, gaps, hold / release drafts.
6. **The desk page + Labour chat** - `/console/labour`, kind `labour`, NEW tool `labour_desk` (drafts only).
7. **Phone** - the foreman's muster, sheet photos, papers.

---

## Sources

- India, four labour codes in force from 21 Nov 2025: PIB release https://www.pib.gov.in/PressReleasePage.aspx?PRID=2192463 ;
  PIB factsheet (contractor pays by bank / electronic mode; principal employer liable for unpaid wages)
  https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251122702801.pdf ; OSH Code text
  https://www.indiacode.nic.in/bitstream/123456789/22041/1/2020-37.pdf ; contract labour under the OSH Code
  https://www.india-briefing.com/news/india-contract-labour-laws-osh-code-47641.html/ ,
  https://www.lkslaw.com/insights/articles/contract-labour-under-the-new-regime-an-overview ;
  codes overview https://ksandk.com/labour-employment/all-four-labour-codes-enforced-from-21-november-2025/ ;
  cess under the Social Security Code https://www.lawrbit.com/article/indias-new-labour-codes/
- India TDS s.393(1): https://www.incometaxindia.gov.in/w/section-393-6 ,
  https://cleartax.in/s/section-393-of-income-tax-act , https://www.taxheal.com/?p=120691
- UK CIS: https://www.gov.uk/what-you-must-do-as-a-cis-contractor/make-deductions-and-pay-subcontractors ,
  https://www.gov.uk/what-you-must-do-as-a-cis-contractor/file-your-monthly-returns
- US Davis-Bacon certified payroll: https://www.dol.gov/agencies/whd/forms/wh347 ,
  https://www.dol.gov/agencies/whd/government-contracts/prevailing-wage-resource-book/db-compliance-principles
- Australia portable long service levies: https://www.qleave.qld.gov.au/building-and-construction/levy-payers/what-is-the-levy ,
  https://www.nsw.gov.au/employment/rights-responsibilities/portable-long-service/bci-long-service-payments-scheme/long-service-levy ,
  https://actleave.act.gov.au/change-to-construction-levy/
- UAE WPS 2026: https://www.morganlewis.com/pubs/2026/05/uae-introduces-new-wage-protection-system-resolution-effective-1-june-2026 ,
  https://u.ae/en/information-and-services/jobs/Sector-of-employment/employment-in-the-private-sector/payment-of-wages ,
  https://mohre.gov.ae/en/guidance-and-awareness-portal-new/wages-protection-system
- Germany general contractor liability and SOKA-BAU:
  https://www.zoll.de/EN/Businesses/Work/Foreign-domiciled-employers-posting/Minimum-conditions-of-employment/Employers-liability/employers-liability_node.html ,
  https://ela.europa.eu/sites/default/files/2024-07/PF_2023_DE-InnovativeLiabilityLegis_CL.pdf ,
  https://www.zoll.de/EN/Businesses/Work/Foreign-domiciled-employers-posting/Minimum-conditions-of-employment/Holiday-fund-procedures/holiday-fund-procedures_node.html
- Singapore foreign worker levy: https://www.mom.gov.sg/passes-and-permits/work-permit-for-foreign-worker/foreign-worker-levy/what-is-the-foreign-worker-levy ,
  https://mom.gov.sg/passes-and-permits/work-permit-for-foreign-worker/sector-specific-rules/construction-sector-requirements

Not yet read from a primary source (shown as "check this" in the packs): Saudi Mudad rules, SOKA-BAU's current rate,
Victoria / NSW levy percentages, India's state cess rate under the Social Security Code rules, UK nil-return rule from
April 2026.
