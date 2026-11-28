# Segment 04 — Wealth management, asset management, private banking, pensions & retirement, family offices (worldwide)

Research date: 22 Nov 2026. Scope as briefed: advisers/planners (RIA, IFA, CFP), robo-advice, portfolio
tracking and reporting, investment KYC/suitability, funds (mutual funds / ETFs / UCITS), fund administration,
transfer agency, fund accounting / NAV, portfolio management, alternatives (PE, VC, hedge, real estate, private
credit), ESG, pension schemes and trustees, superannuation, 401(k)/IRA, EPF/NPS, retirement income, family
offices, trusts and estates, investor relations, client reporting, wealth compliance.

Source-honesty key: **[S]** = from a page I opened or a search result whose text I read this session (URL in
the Sources list). **[M]** = from memory — verify before relying on it. "check" = I am unsure of the current
state.

---

## 0. The shape of this segment (read first)

1. **Regulated advice is the line, not investing.** Almost every regime separates (a) giving a personal
   recommendation (licensed: US RIA / Reg BI broker, UK FCA advice permission, EU MiFID II investment advice,
   India SEBI Investment Adviser / Research Analyst, Singapore MAS FA licence, Australia AFSL + relevant
   provider, Canada CIRO/CSA registrant) from (b) explaining, calculating, consolidating, tracking, drafting
   and preparing. Hoola's AI employees live in (b), and in (B-tier) assist a named licensed person who signs.
2. **Regulators are now writing "AI used in advice" rules.** SEBI amended the IA Regulations (16 Dec 2024)
   so an IA must disclose to clients the extent of AI tool use and stays solely responsible for data security
   and compliance when it uses AI [S]. MAS issued final Guidelines on AI Risk Management (feedback dated
   7 Oct 2026, covering generative AI and AI agents) after consultation P017-2025 [S]. This means a
   B-tier role must produce an **AI-use disclosure line** and an **audit trail** for the human adviser.
3. **New "middle ground" regimes create demand for prepare-and-explain roles.** UK FCA targeted support went
   live 6 April 2026 for DC pensions and retail investments; FCA research says only 9% of adults received
   advice on pensions/investments in the past year; FCA expects ≥18 million people to be offered help over a
   decade [S]. Australia revived the New Class of Adviser under DBFO in Aug 2026, first only for
   APRA-regulated super and life insurers [S]. These are firm-delivered, so Hoola sells to the *firm* (B tier).
4. **Lost/forgotten money is a huge, measurable consumer pain.** ~31.9m forgotten US 401(k)s holding ~$2.1tn
   (Capitalize, Sept 2025; methodology disputed by NAPA) [S]; A$18.9bn lost + ATO-held super across ~7.3m
   accounts at 30 Jun 2025, A$21.2bn at 30 Jun 2026 [S]; India ₹9,330 crore in 30.9 lakh inoperative EPF
   accounts (Mar 2026) plus LIC unclaimed ~₹5,565 crore [S]; Mexico ~18m unregistered Afore accounts [S];
   Kenya unremitted pension contributions Sh84bn in 2025 (Sh69bn in 2024) [S]. This is the cleanest A-tier
   consumer product in the segment.
5. **The institutional back office is already going agentic — the work is real and documented.** BNY reports
   40+ AI solutions in asset servicing; Alter Domus reports hundreds of agents in production; Canoe reports
   1M+ alternatives documents processed monthly across 44,000+ funds; every serious source stresses human
   review, dual sign-off and audit trails on NAV [S]. Hoola cannot be the administrator of record; it can be
   the preparer/checker for a small manager, family office or emerging administrator.
6. **Advisers already pay for AI admin.** AI note-taker category: Jump 22.68% share, Zocks 10.22% (Financial
   Planning / T3 survey); Orion Dec-2024 survey: 68% of advisers use AI for note-taking, meeting prep,
   documentation; Morgan Stanley Debrief launched June 2024 (client consent required, ~30 min saved per
   meeting by a pilot estimate) [S]. Document extraction (tax returns, estate documents) is a funded
   category: FP Alpha, Holistiplan [S].

### Regional rulebook used throughout (abbreviated in each role as "Regions")

| Region | Advice / conduct | Funds | Pensions / retirement | Investor data rails |
|---|---|---|---|---|
| US | SEC Advisers Act fiduciary duty; Reg BI + Form CRS for broker-dealers (2026 exam focus: account & rollover recommendations) [S]; FINRA; state RIAs; CFP Board | 1940 Act funds, ETFs, Form N-PORT [M] | ERISA/DOL, 401(k), 403(b), IRA, TSP, SECURE 2.0 [M] | IAPD / BrokerCheck (no official public API) [S]; custodian feeds (Schwab, Fidelity, Pershing) [M]; Plaid/Akoya/FDX [M] |
| UK | FCA COBS, Consumer Duty, targeted support (Apr 2026) [S], FOS complaints | UCITS / NURS, AFM value assessments [M] | TPR, auto-enrolment, Pensions Dashboards (connection deadline 31 Oct 2026) [S], pension freedoms, LTA abolished [M] | Origo transfers, pensions dashboards ecosystem [S] |
| EU/EEA | MiFID II suitability & appropriateness, PRIIPs KID, Retail Investment Strategy (political agreement 18 Dec 2025: value-for-money benchmarks, softened inducement rules) [S]; SFDR (SFDR 2.0 proposal 20 Nov 2025: ESG Basics / Transition / Sustainable, 70% threshold) [S] | UCITS, AIFMD II, ELTIF 2.0 [M] | IORP II, PEPP, national 2nd/3rd pillar (e.g. Riester/bAV DE, PER FR) [M] | PSD2/PSD3 + FiDA (check status) [M] |
| Switzerland | FinSA/FinIA, FINMA [M] | CISA [M] | 3-pillar, Pillar 3a [M] | — |
| GCC | DFSA (DIFC), FSRA (ADGM), SCA/CBUAE, CMA Saudi [M] | DIFC/ADGM funds [M] | UAE federal voluntary end-of-service savings (Cabinet Res. 96/2023); DIFC/DEWS (>$1bn AuA Oct 2025) [S]; GOSI Saudi [M] | — |
| India | SEBI IA Regs (AI disclosure, Dec 2024) [S], RA Regs, MFD (AMFI ARN), PMS, AIF | SEBI MF regs, AMFI, RTAs (CAMS/KFintech) [M] | EPFO (inoperative accounts) [S], NPS (PFRDA; AUM >₹18 lakh crore per chairman, Nov 2026 — figures conflict) [S], APY | Account Aggregator (Sahamati), MF Central, CAS from NSDL/CDSL [M] |
| Singapore / SE Asia | MAS FAA, FEAT, AI Risk Management Guidelines (2026) [S]; SC Malaysia, OJK Indonesia, SEC Thailand/Philippines [M] | VCC [M] | CPF (SG), EPF/KWSP (MY), SSS (PH) [M] | SGFinDex [M] |
| China / HK | CSRC/NFRA; SFC HK suitability [M] | Wealth Management Connect [M] | China personal pension nationwide 15 Dec 2024; 72.8m accounts in pilot cities, only 22% contributed [S]; HK MPF → eMPF Platform (last batch Jan 2026) [S] | eMPF platform [S] |
| Japan / Korea | FSA Japan, JFSA customer-oriented principles [M]; FSC/FSS Korea [M] | Investment trusts [M] | New NISA: 28.26m accounts end-2025, target 34m by end-2027; minors allowed from Jan 2027; iDeCo [S]; Korea IRP/DC [M] | — |
| Australia / NZ | ASIC, AFSL, best interests duty, DBFO / New Class of Adviser (Aug 2026, APRA super & life only) [S]; FMA NZ [M] | MIS, ETFs [M] | Superannuation (APRA/ASIC), SMSFs (ATO), lost super A$21.2bn (Jun 2026) [S]; KiwiSaver [M] | CDR (open banking) [M]; ATO / myGov super search [S] |
| Africa | FSCA (SA), SEC Nigeria, CMA Kenya [M] | CIS (SA) [M] | SA two-pot (from 1 Sep 2024; R57–60bn+ withdrawn; repeat claims common; 80% used for debt/essentials) [S]; Nigeria PenCom RSA transfer window (once a year), Personal Pension Plan (ex-micro pension) [S]; Kenya RBA (unremitted Sh84bn) + UFAA unclaimed [S] | — |
| Latin America | CVM Brazil, CNBV Mexico [M] | FIIs/FIDCs Brazil [M] | Brazil previdência aberta (PGBL/VGBL; 13.6m plans Sept 2025; 5% IOF on VGBL >R$300k from mid-2025; portability rules) [S]; Mexico Afore (one switch/year; 813,955 switches Jan–May 2025; agent incentive limits) [S]; Chile AFP [M] | Brazil Open Finance (investments phase — check) [M] |
| Canada | CIRO + CSA Client Focused Reforms (Phase 2 review Dec 2025, 105 firms; KYC gaps, transaction-level suitability) [S] | NI 81-102 [M] | RRSP, TFSA, FHSA, CPP/QPP, RRIF [M] | — |

---

## 1. Consumer / household roles (hired by a person or family)

### 1. Lost & Forgotten Retirement Money Finder
Finds old pension / retirement / provident accounts and walks the person through reclaiming or consolidating.
- **Who hires:** consumer; also employers and HR at exit; NGOs; government outreach.
- **Jobs:** build an employment-history timeline from CV/payslips/tax records; map each employer to its scheme
  (401(k) plan, super fund, EPF establishment, MPF trustee, RSA PFA, Afore); prepare the official searches
  (US: National Registry/DOL Retirement Savings Lost & Found [M]; AU: myGov/ATO super search [S]; IN: EPFO
  UAN/KYC + the new tracing portal reported Jul 2026 [S]; UK: Pension Tracing Service + dashboards [S]); draft
  letters to old plan administrators; checklist of KYC mismatches (name/DOB/Aadhaar/SSN) that block claims;
  compare consolidation options in plain words (fees, insurance lost if a super fund is closed, protected
  benefits); track every claim with deadlines; remind when a statement arrives.
- **Tier A.** The person submits claims herself; Hoola never moves balances. Transfer recommendation that is
  "advice" (e.g. UK DB transfer, safeguarded benefits ≥£30k needs regulated advice [M]) is refused and routed.
- **Data/rails:** her documents; official tracing portals (she logs in); scheme contact registers; dashboards.
- **Evidence of demand:** US ~31.9m forgotten 401(k)s / ~$2.1tn [S]; AU A$21.2bn lost+ATO-held [S]; IN ₹9,330 cr
  inoperative EPF + LIC ₹16,649 cr incl. income [S]; MX 18m unregistered Afore accounts [S]; KE UFAA holds
  unclaimed retirement benefits, only ~6% returned since 2014 per Star editorial [S].
- **Existing products:** Capitalize (US rollovers) [S], Beagle (US, [M]), PensionBee (UK finder/consolidator, [M]).

### 2. Retirement Readiness Calculator & Explainer
- **Who:** consumer, couples; employers as a benefit.
- **Jobs:** pull balances from statements; project at several return/inflation assumptions (shown, not chosen
  for her); state-pension estimate inputs (SSA, UK State Pension forecast, CPP, EPS/NPS annuity); gap to target
  income; effect of contribution changes; employer match left on the table; explain tax wrappers (Roth vs
  traditional, RRSP vs TFSA, PGBL vs VGBL incl. 12% deduction rule [S], NPS 80CCD(1B) [M], NISA/iDeCo [S]);
  sensitivity table; annual refresh reminder.
- **Tier A** (education + calculation; no product pick).
- **Regions:** all; jurisdiction tax tables must be data with a source and review date.
- **Existing:** Vanguard/Fidelity planners, NewRetirement/Boldin [M].

### 3. Retirement Income (Decumulation) Planner Assistant
- **Who:** consumer near/in retirement; B-tier for advice firms.
- **Jobs:** cashflow schedule from pensions/annuities/savings; withdrawal-order scenarios with tax shown;
  required minimum distributions (US RMD dates/amounts), RRIF minimums, super pension minimum drawdown rates,
  UK UFPLS/drawdown tax, SA two-pot rules (one savings-pot withdrawal a year, min R2,000, taxed at marginal
  rate [S]); longevity and sequence-risk illustrations; annuity quote comparison layout (quotes she obtains);
  "what if I withdraw now" impact (SA repeat withdrawals: 62% of claims since Mar 2026 were third withdrawals
  per Momentum [S]); calendar of withdrawal windows.
- **Tier A/B:** A for calculation; recommending a specific drawdown/annuity = licensed adviser (B).
- **Existing:** Income Lab, Timeline (UK) [M].

### 4. Personal Portfolio Tracker & Statement Reader
- **Who:** consumer, sole trader.
- **Jobs:** read broker/fund statements, India CAS (NSDL/CDSL/MF Central), US 1099-B/brokerage PDFs, UK
  platform statements; consolidate holdings; true cost (TER, platform, advice fee, trail commission); XIRR /
  money-weighted return; asset allocation and concentration; duplicate funds overlap; dividends/coupons
  calendar; corporate actions explained; alert on large drawdowns (information, not trading advice).
- **Tier A.** Never places/cancels orders.
- **Rails:** document upload; India Account Aggregator (Sahamati) [M]; Plaid Investments / Akoya [M]; Brazil
  Open Finance investments (check) [M].
- **Existing:** Kubera, Sharesight, Empower Personal Dashboard, INDmoney, Value Research [M].

### 5. Fund Fee & Value Checker
- **Jobs:** read KID/KIID/factsheet/prospectus; compute total cost of ownership over 10/20 years; compare to
  cheaper share class / index alternative (facts, not a pick); detect regular vs direct plan (India), clean vs
  bundled share class (UK), trail commissions (EU inducements); explain EU value-for-money benchmarks once
  live (RIS agreement Dec 2025 [S]); Afore net-return comparison (CONSAR now shows net return on switch forms
  [S]).
- **Tier A.**

### 6. Investment Scam & Unsuitable-Product Checker
- **Jobs:** verify a firm/person on official registers (US IAPD/BrokerCheck [S], FCA register, SEBI IA/RA
  lists, MAS FID, ASIC Professional Register, CIRO, SCA/DFSA, CVM); compare names against regulator warning
  lists; red-flag analysis of a pitch (guaranteed returns, unregistered "AI trading bot", WhatsApp tips groups,
  pressure); explain why a product is high-risk; draft a complaint/report.
- **Tier A.** Overlaps segment on fraud; keep investment-specific.
- **Pain:** FCA investment complaints 58,305 in H1 2025 and 54,280 in H2 2025 [S]; pensions/decumulation
  complaints 94,035 H1 2025, trust-based pension complaints +38% [S].

### 7. Investment Complaint & Ombudsman Case Builder
- **Jobs:** timeline of what was sold and said; collect suitability report/KID/fact-find; check the firm's
  final response deadline (UK 8 weeks then FOS [M]; SEBI SCORES/ODR [M]; AFCA AU [M]; OBSI CA [M]; FINRA
  arbitration US [M]); compute loss illustration; draft complaint letter with blanks; track deadlines.
- **Tier A** (drafts; she sends). Redress paid H1 2025 £283m across all FCA complaint types [S].

### 8. Pension Switch / Portability Explainer
- **Jobs:** explain the switch rule and costs: Mexico Afore (once a year, second only exceptionally; phone
  verification controls; unauthorised-transfer complaint route via CONDUSEF) [S]; Nigeria RSA transfer window
  (once a year, Section 13 PRA 2014) [S]; Brazil portability (no PGBL↔VGBL switch; not after accumulation
  phase) [S]; UK transfers incl. scam checks [M]; US rollover vs leave-in-plan facts (Reg BI rollover focus
  [S]); prepare the forms she signs.
- **Tier A.**

### 9. Tax-Advantaged Account Organiser (NISA / ISA / IRA / RRSP / TFSA / NPS / PEPP)
- **Jobs:** track allowances and used amounts; contribution deadlines; carry-forward rules; "unused account"
  nudge (Japan: only 62.2% of securities-firm NISA accounts had subscriptions in 2025 [S]; China: only 22% of
  personal pension accounts contributed [S]); minor-account rules (NISA under-18 from Jan 2027 [S]); paperwork
  for opening/transfers.
- **Tier A.**

### 10. Household Wealth Organiser ("Family CFO lite")
- **Jobs:** net-worth statement; document vault index (where the will, deeds, policies, account numbers
  masked live); nominee/beneficiary audit across all accounts; insurance-vs-dependants gap explanation; annual
  review checklist; emergency file for spouse ("if something happens to me").
- **Tier A.**

### 11. Estate & Succession Paperwork Preparer (consumer)
- **Jobs:** inventory of assets and nominations; plain-English explanation of the local regime (US probate vs
  revocable trust; UK IHT nil-rate bands; India nominee ≠ legal heir, succession certificate / legal heir
  certificate; Islamic inheritance shares in GCC; civil-law forced heirship EU/LatAm [M]); draft
  will *instructions* for a lawyer; list documents to claim a deceased person's funds; track transmission
  requests at each AMC/RTA/bank.
- **Tier A/B**; the will itself is drafted/witnessed per local law with a lawyer where required.

### 12. Deceased Investor Claims Assistant (for bereaved families)
- **Jobs:** list every holding of the deceased (CAS, statements, mail); per-institution transmission checklist;
  forms prefilled; certified copies tracker; tax on inherited IRA (10-year rule) / super death benefit tax [M];
  follow-up drafts.
- **Tier A.**

### 13. ESG / Values-Based Portfolio Screener (consumer)
- **Jobs:** look through funds to holdings; screen against her stated values (fossil fuels, weapons, tobacco,
  Shariah screens); explain SFDR categories now and SFDR 2.0 (ESG Basics / Transition / Sustainable, 70%
  threshold, naming rules) [S]; greenwashing questions to ask.
- **Tier A** (information; no recommendation).

### 14. Islamic / Shariah-Compliant Investing Checker
- **Jobs:** screen holdings using published ratio methodologies (AAOIFI-style debt/interest income ratios
  [M]); purification amount calculation on dividends; zakat on investments calculation; explain sukuk vs bond.
- **Tier A.** Fatwa/certification stays with a Shariah board.
- **Regions:** GCC, Malaysia (SC Shariah list [M]), Indonesia, UK, South Asia.

### 15. Financial Education Tutor (investing & retirement)
- **Jobs:** lessons on compounding, diversification, fees, risk; quizzes; explain her own statements; prepare
  questions for her adviser meeting.
- **Tier A.**

---

## 2. Adviser / planner practice roles (hired by RIA, IFA, CFP practice, MFD, wealth desk)

### 16. Client Fact-Find & Onboarding Assistant
- **Jobs:** send and chase the fact-find; read uploaded statements/payslips/tax returns into the CRM; flag
  missing items; risk-profile questionnaire administration (firm's own methodology — CIRO says "one risk
  profile fits all is dead" [S]); identity/AML document checklist; household mapping; account-opening packs
  prefilled for signature (DocuSign/Adobe).
- **Tier B:** adviser confirms KYC and risk profile; compliance approves onboarding. Hoola never "passes" KYC.
- **Rails:** CRM (Salesforce FSC, Wealthbox, Redtail, Xplan, Intelliflo [M]); custodian account opening;
  India CKYC/KRA (check) [M]; e-sign.
- **Regions:** US Reg BI/fiduciary + CIP; UK COBS 9 / Consumer Duty; EU MiFID II Art 25 / ESMA suitability
  guidelines; CA CFR KYC (gaps widespread per Dec 2025 review) [S]; SG MAS FAA Notice FAA-N16 [M]; IN SEBI IA
  risk profiling + agreement [M]; AU FASEA/BID [M].
- **Existing:** Jump, Zocks (onboarding/proposal category) [S].

### 17. Meeting Prep & Notes Scribe (with consent)
- **Jobs:** pre-meeting brief (holdings, life events, open tasks, last notes); live/recorded transcription with
  client consent; summary, action items, compliance-ready file note; follow-up email draft; CRM update.
- **Tier B:** adviser reviews before the note becomes the record.
- **Evidence:** Jump 22.68% / Zocks 10.22% share; Orion survey 68% using AI for notes [S]; Morgan Stanley
  Debrief (consent required, saves notes to Salesforce) [S]; Kitces research on note-takers [S].
- **Regions:** call-recording consent laws (US two-party states, GDPR/UK GDPR, India DPDP [M]); MiFID II
  telephone/electronic recording [M]; SEBI AI disclosure [S].

### 18. Suitability / Statement-of-Advice Drafter
- **Jobs:** draft the suitability report (UK), Statement of Advice (AU), Record of Advice, US recommendation
  rationale/Reg BI documentation, MiFID II suitability statement; pull facts from fact-find; cost & charges
  disclosure (ex-ante); alternatives considered; KID attachment list; check consistency between risk profile
  and recommended portfolio and flag gaps.
- **Tier B:** licensed adviser chooses the recommendation and signs. Hoola never invents the recommendation.
- **Regions:** AU DBFO tranche 2 SoA changes (check) [S]; UK targeted support has its own disclosure set [S].

### 19. Financial Plan Builder (adviser's paraplanner)
- **Jobs:** cashflow model from fact-find; goals; insurance gap; tax planning scenarios; retirement income
  plan; estate summary; plan document/presentation; versioning when assumptions change.
- **Tier B** (paraplanning is a known human role; plan advice signed by planner).
- **Existing:** eMoney, MoneyGuide, RightCapital, Voyant [M]; FP Alpha (AI tax/estate/insurance) [S].

### 20. Tax Return & Planning-Opportunity Reader
- **Jobs:** extract fields from tax returns (Form 1040, SA100, ITR, T1); spot planning opportunities from rules
  (unused deductions, Roth conversion window, capital-loss harvesting candidates, 80C/80CCD headroom); summary
  for client meeting.
- **Tier B.**
- **Existing:** Holistiplan, FP Alpha (vendor claims 99.8% extraction accuracy, unverified) [S].

### 21. Estate Document Summariser (for advisers)
- **Jobs:** read wills, trusts, POAs; extract fiduciaries, beneficiaries, distribution terms, trust provisions;
  flowchart; flag stale documents, missing guardians, beneficiary designations that override the will.
- **Tier B** (lawyer interprets).
- **Existing:** FP Alpha Estate Insights 2.0 (hundreds of data points), Holistiplan estate tool, Powder [S].

### 22. Portfolio Rebalancing & Model Drift Monitor (prepare-only)
- **Jobs:** compare accounts to assigned model; drift report; tax-aware rebalance proposal (lots, wash-sale
  windows, CGT); cash needs; trade list file prepared for the adviser's order system.
- **Tier B:** adviser/PM approves; orders placed by humans on the OMS/custodian.
- **Existing:** Orion, iRebal, Envestnet, Morningstar Office [M].

### 23. Tax-Loss Harvesting Preparer
- **Jobs:** identify lots in loss; substitutes that avoid wash-sale/ "bed and breakfast" (UK 30-day) rules;
  estimated tax value; calendar.
- **Tier B.**

### 24. Client Review & Annual Service Evidence Assistant
- **Jobs:** schedule annual reviews; prepare review pack; evidence that ongoing-advice service was delivered
  (UK ongoing advice fee reviews under Consumer Duty [M]; AU fee-disclosure / renewal consents [M]); KYC
  refresh prompts (CFR: reassess suitability when KYC changes [S]).
- **Tier B.**

### 25. Client Communications & Market Update Writer
- **Jobs:** quarterly letters, market commentary in plain English, personalised portfolio commentary from
  attribution data, newsletters; compliance pre-check against financial promotion rules (FCA COBS 4, FINRA
  Rule 2210, SEC Marketing Rule).
- **Tier B:** compliance approves before sending.

### 26. Rollover & Transfer Paperwork Desk
- **Jobs:** 401(k)→IRA and ACATS paperwork; UK pension transfer forms and Origo tracking; super rollovers;
  India MF switch/STP mandates; status chasing; Reg BI rollover rationale template (SEC 2026 focus) [S].
- **Tier B.**

### 27. Practice Compliance File Auditor
- **Jobs:** sample client files; check required documents (fact-find, risk profile, KYC refresh, suitability,
  fee consent, disclosures delivered: Form CRS/ADV 2A, KIDs); list gaps; remediation tracker.
- **Tier B:** compliance officer decides.

### 28. Adviser Practice Ops & Billing Assistant
- **Jobs:** AUM fee billing calculation and reconciliation with custodian; invoice drafts; fee-deduction
  authority tracking; revenue reports; trail commission reconciliation (EU/IN distributors); CPD/CE hours
  tracker.
- **Tier A.** Money moves only via custodian on human instruction.

### 29. Mutual Fund Distributor Desk (India and similar)
- **Jobs:** SIP mandate tracking, failed SIP follow-up, KYC status (KRA) checks, ARN renewal and EUIN
  hygiene, commission statements reconciliation (CAMS/KFintech), nominee updates (SEBI nomination drive),
  investor service requests.
- **Tier A/B.** Distributor may not give advice beyond incidental; SEBI IA vs MFD separation [M].

### 30. Robo-Advice Operations Analyst (for a robo/digital-advice firm)
- **Jobs:** monitor questionnaire drop-offs and contradictions; flag clients whose answers make the algorithm's
  output unsuitable; model portfolio drift; complaints triage; algorithm change log & testing evidence for the
  regulator (FINRA/SEC robo guidance, ASIC RG 255, ESMA suitability guidelines for automated advice [M]).
- **Tier B.**
- **Existing:** Betterment, Wealthfront, Wealthsimple, Nutmeg, Scalable, StashAway, Groww/Kuvera [M].

### 31. Targeted-Support / Guidance Journey Builder (UK and analogues)
- **Jobs:** for a provider, build consumer-segment journeys under FCA targeted support (DC pensions and retail
  investments only; high-risk products excluded) [S]; draft "people like you" suggestions for human sign-off;
  test against Consumer Duty outcomes; MI.
- **Tier B:** firm's authorised individuals approve each segment message.
- **Regions:** UK (Apr 2026) [S]; AU New Class of Adviser in APRA super/life (2026, details pending) [S].

---

## 3. Private banking & family office roles

### 32. Private Client Relationship Associate
- **Jobs:** daily client book brief; consolidated positions across custodians; maturities/coupons/capital
  calls coming; service-request handling (statements, confirmations, address changes); pitchbook assembly;
  meeting notes; KYC refresh calendar.
- **Who:** private bank, multi-family office, wealth boutique.
- **Tier B:** relationship manager owns client; advice/mandate decisions licensed.
- **Existing:** Morgan Stanley AI Assistant (98% advisor teams use, per OpenAI case study) [S].

### 33. Source-of-Wealth / Source-of-Funds Narrative Preparer
- **Jobs:** assemble SoW evidence (business sale docs, inheritance, salary history, property sales), build the
  narrative and timeline, list gaps, prepare PEP/adverse-media search summary from screening tool output.
- **Tier B:** MLRO/compliance decides; never approves the client.
- **Regions:** FATF R.10/12; EU AMLR (2027 [M]); UK JMLSG; MAS 626; HK AMLO; DFSA; SEBI PMLA.

### 34. Credit & Lombard Lending Collateral Monitor (private bank)
- **Jobs:** LTV by pledged portfolio; haircut tables applied; margin-call early warnings; covenant tracking;
  memo drafts.
- **Tier B:** credit decision human; no auto-liquidation.

### 35. Family Office Consolidated Reporting Analyst
- **Jobs:** consolidate custodians, private funds, real assets, direct companies, art/collectibles; entity
  ownership chart; look-through exposure; performance (IRR/TWR) by entity and family branch; liquidity
  ladder; capital-commitment forecast; board/family-council pack.
- **Who:** single/multi family office (~8,030 SFOs in 2024 per Deloitte, projected 9,030 in 2025) [S].
- **Tier A.**
- **Existing:** Addepar, Masttro, Asora, Eton, Canoe for alts documents [S/M].

### 36. Family Office Bill-Pay & Household Admin Controller
- **Jobs:** invoice intake for properties, staff, school fees; coding; approval routing to principals;
  payment file prepared for the bank portal; staff payroll handoff; property and vehicle registers; insurance
  renewal tracker.
- **Tier A** (prepare; principal/CFO releases payments).

### 37. Family Governance & Next-Gen Secretary
- **Jobs:** family constitution drafting support, family council minutes, investment-committee papers, next-gen
  education programme, voting/consent tracking, conflict-of-interest registers.
- **Tier A.**

### 38. Direct Deal / Co-Investment Analyst (family office)
- **Jobs:** read CIMs/teasers; screening memo against the family's criteria; data-room Q&A tracker; comps;
  investment-committee memo draft; post-deal KPI tracking.
- **Tier B:** IC decides.
- **Existing:** Hebbia (IC memo inputs, PitchBook/Preqin integrations) [S].

### 39. Philanthropy & Foundation Grants Officer
- **Jobs:** grant pipeline, due diligence on charities (registers: IRS Pub 78/Form 990, UK Charity Commission,
  India 12A/80G/FCRA), grant agreements drafts, impact reports, minimum distribution (US 5% private
  foundation rule [M]) tracker.
- **Tier A/B.**

### 40. Cross-Border Wealth Compliance Mapper
- **Jobs:** map family's tax residencies and reporting: FATCA/CRS self-certs, FBAR/8938 checklists, PFIC
  warnings for US persons in non-US funds, UK non-dom changes (FIG regime 2025 [M]), India LRS limits and TCS,
  Schedule FA; deadlines calendar; prepare packs for tax adviser.
- **Tier B:** tax adviser signs.

---

## 4. Trusts, estates & fiduciary roles

### 41. Trust Administration Assistant
- **Jobs:** trust deed summary; trustee duty calendar (accounts, distributions, reviews, tax returns —
  US 1041, UK TRS registration, India trust ITR); beneficiary register; distribution requests memo; trustee
  minutes drafts; investment policy review prompts.
- **Who:** professional trustees, trust companies, family offices, individual lay trustees.
- **Tier B:** trustees decide distributions.
- **Regions:** UK Trust Registration Service [M]; Jersey/Guernsey/Cayman/BVI trust companies; Singapore
  Trust Companies Act; India Indian Trusts Act; US state UTC.

### 42. Executor / Estate Settlement Coordinator
- **Jobs:** asset & liability inventory; probate/grant/succession application checklists; creditor notice
  dates; estate account ledger; tax (IHT400 UK, US 706/1041, CGT on death) preparation pack; distribution
  schedule for executor sign-off; final accounts.
- **Tier B** (executor/lawyer).

### 43. Beneficiary Designation & Nominee Auditor
- **Jobs:** read every account's nomination/beneficiary; conflicts with will/trust; outdated (ex-spouse);
  minors without guardian/trustee; SEBI nomination requirements; super binding death benefit nominations
  (lapse dates) [M].
- **Tier A.**

### 44. Power of Attorney / Deputyship Account Manager (support)
- **Jobs:** record keeping for attorneys/deputies (UK OPG annual report [M]); separation of funds evidence;
  expense logs; best-interest decision records.
- **Tier A/B.**

---

## 5. Asset management — front & middle office

### 45. Investment Research Associate (buy-side)
- **Jobs:** earnings call/filing summaries; KPI extraction; model update prep; consensus vs actual; ESG
  controversy digest; news monitoring; research note first drafts.
- **Who:** asset managers, hedge funds, family offices.
- **Tier B:** PM decides. (Research Analyst licensing in India SEBI RA if distributed to clients [M].)
- **Existing:** AlphaSense, Hebbia, Bloomberg GPT tools [S/M].

### 46. Portfolio Manager's Assistant (pre-trade prep)
- **Jobs:** cash and exposure dashboard; what-if trade impact on risk/limits; pre-trade compliance checks
  (prospectus/UCITS limits: 5/10/40 rule [M], issuer, sector); trade idea log; order ticket prepared for the
  OMS (not sent).
- **Tier B.** Orders entered/released by authorised traders.

### 47. Fixed Income & Cash Ladder Analyst
- **Jobs:** maturity ladder; duration/convexity; coupon schedule; call/put dates; credit-rating watch list;
  liquidity buckets (UCITS / SEC 22e-4 liquidity classification [M]).
- **Tier B.**

### 48. Performance Measurement & Attribution Analyst
- **Jobs:** TWR/MWR calculation, benchmark comparison, Brinson attribution, risk stats, GIPS composite
  maintenance checklist, performance commentary.
- **Tier A** (calculation) / B (GIPS compliance claim signed by firm).

### 49. Investment Risk Reporter
- **Jobs:** VaR/stress tests from the risk system output, limit breaches log, liquidity stress (UCITS/AIFMD),
  counterparty exposure, risk committee pack.
- **Tier B.**

### 50. Product & Fund Documentation Writer
- **Jobs:** factsheets, KID/KIID data (PRIIPs cost and performance scenarios), prospectus updates tracking,
  SFDR pre-contractual / periodic templates (and SFDR 2.0 transition) [S], US 497 supplements, UK AFM value
  assessment reports [M]; translation management.
- **Tier B:** legal/compliance approve.
- **Existing:** Kurtosys, FundsDLT? (check) [M].

### 51. Fund Distribution & Dealer Data Analyst
- **Jobs:** EMT/EPT/EET template preparation (FinDatEx) [M], target-market mapping, sales by channel,
  platform due-diligence questionnaires, distributor oversight reporting (MiFID II product governance).
- **Tier A/B.**

### 52. RFP / DDQ Response Writer (institutional sales)
- **Jobs:** answer consultant/LP RFPs and DDQs (ILPA DDQ, AIMA DDQ) from a content library; keep answers
  current; flag changed facts; compliance review routing.
- **Tier B.**
- **Existing:** Glean (DDQ drafts) [S]; Loopio, Responsive, DiligenceVault [M].

### 53. Proxy Voting & Stewardship Assistant
- **Jobs:** meeting calendar; summarise resolutions; apply firm voting policy to draft recommendations;
  engagement log; stewardship report (UK Stewardship Code, Japan code, India SEBI stewardship) [M].
- **Tier B:** stewardship team votes.

---

## 6. Fund operations — administration, transfer agency, NAV, accounting

### 54. NAV Preparation Checker
- **Jobs:** reconcile positions/cash with custodian and broker; price checks vs vendor feeds, stale/zero-price
  flags, tolerance breaks; accrual checks (fees, interest, dividends); NAV movement explanation; four-eyes
  checklist and audit trail.
- **Who:** emerging managers, self-administered funds, small administrators, family offices.
- **Tier B:** fund accountant/administrator strikes and signs NAV; Hoola never publishes NAV.
- **Evidence:** Grant Thornton: AI embedded in NAV production, but "can't remove the human element"; controls
  = reviews, dual sign-off, audit trails [S]; vendor claims of <5-minute NAVs are marketing [S].

### 55. Cash & Trade Reconciliation Clerk
- **Jobs:** daily three-way recs (OMS vs custodian vs administrator), break ageing, root-cause notes,
  corporate-action recs, FX settlement checks.
- **Tier A.**
- **Existing:** Carta agentic cash reconciliation and SOI tagging [S]; Duco, Gresham [M].

### 56. Fund Accounting & Financial Statements Preparer
- **Jobs:** trial balance, expense budgets/accruals, management/performance fee calcs (high-water marks,
  equalisation, crystallisation), annual report draft (IFRS/US GAAP investment company), audit PBC list.
- **Tier B:** auditor opines; directors approve statements.

### 57. Transfer Agency / Investor Servicing Assistant
- **Jobs:** subscription/redemption order checks (cut-offs, minimums, forms complete), investor KYC/AML
  document validation and sanctions screening prep [S Deloitte], register maintenance queries, distribution
  instructions, contract notes, investor queries.
- **Tier B:** TA/AML officer accepts investors; dealing processed by TA system.
- **Regions:** Luxembourg/Ireland TA, US 1940 Act TA (SEC registered), India RTAs (CAMS/KFintech), Cayman.

### 58. Fund Regulatory Reporting Preparer
- **Jobs:** data prep for Form PF / N-PORT / N-CEN (US), AIFMD Annex IV, UCITS/AIF reporting, FATCA/CRS
  reporting, CSSF/CBI returns, SEBI AIF quarterly reports; validation checks; filing calendar.
- **Tier B:** filed by the manager/administrator as the institution — Hoola prepares only.

### 59. Fund Launch & Lifecycle Project Manager
- **Jobs:** launch checklist (vehicle choice: UCITS, ICAV, SICAV-RAIF, VCC, Delaware LP, India AIF Cat I-III,
  ELTIF), service-provider onboarding, document tracker, regulator application timeline, board meeting
  calendar, mergers/liquidations checklist.
- **Tier A.**

### 60. Fund Governance / Board Secretary
- **Jobs:** board packs, minutes drafts, delegate oversight reports (ManCo oversight of administrator,
  depositary, distributors), conflicts register, annual policy reviews.
- **Tier A/B.**

---

## 7. Alternatives — private equity, VC, hedge funds, real estate, private credit

### 61. LP Alternatives Document Processor (for investors)
- **Jobs:** read capital call notices, distribution notices, capital account statements, K-1s, quarterly
  reports; extract amounts and dates; cash forecast; reconcile called vs committed; NAV roll-forward;
  alert on calls due.
- **Who:** family offices, endowments, foundations, wealth managers, HNW individuals.
- **Tier A** (payment of calls released by humans).
- **Existing:** Canoe (1M+ docs/month, 44,000+ funds, hybrid pattern + LLM extraction; vendor claims) [S].

### 62. GP Fund Administration Assistant
- **Jobs:** capital call & distribution calculations per LPA waterfall (pref, catch-up, carry), notices
  drafted, LP capital accounts, management fee offsets, investor portal updates.
- **Tier B:** CFO/administrator approves notices and payments.
- **Existing:** Carta Fund Admin AI, Alter Domus DomusAgents [S].

### 63. Investor Relations & LP Reporting Writer
- **Jobs:** quarterly LP letters, ILPA reporting template population [M], portfolio company KPI collection,
  AGM materials, LP question tracker, data-room hygiene.
- **Tier B.**

### 64. Fundraising CRM & Placement Assistant
- **Jobs:** LP pipeline, meeting notes, materials versions, side-letter request tracker, subscription
  document completeness checks, closing checklist.
- **Tier B** (marketing rules: AIFMD NPPR, US Reg D/Marketing Rule, SEBI AIF private placement) [M].

### 65. Side Letter & MFN Compliance Tracker
- **Jobs:** extract obligations from side letters; MFN election process; obligation calendar (reporting,
  excuse rights, ESG exclusions); breach alerts.
- **Tier B.**

### 66. Deal Diligence Assistant (PE/VC)
- **Jobs:** data-room indexing, red-flag summaries, financial model inputs extraction, management Q&A
  tracker, IC memo first draft, 100-day plan tracker.
- **Tier B.**
- **Existing:** Hebbia [S], Blueflame, Rogo (check) [M].

### 67. Portfolio Monitoring Analyst
- **Jobs:** collect monthly KPIs from portfolio companies; valuation input packs (comps, DCF inputs) for the
  valuation committee (IPEV guidelines [M]); covenant tests for private credit loans; watch list.
- **Tier B:** valuation committee/independent valuer signs.

### 68. Private Credit Loan Agency & Covenant Desk
- **Jobs:** borrower compliance certificates read and tested; interest/fee calculations; amortisation
  schedules; drawdown request checks; notices drafts; amendment trackers.
- **Tier B.**

### 69. Real Estate Fund Asset Manager's Assistant
- **Jobs:** rent roll and lease abstraction; service charge reconciliations; capex tracker; property
  valuation inputs; REIT/fund compliance calendars (India REIT/InvIT, US REIT tests [M]); tenant
  correspondence.
- **Tier A/B.**

### 70. Hedge Fund Operations & Investor Onboarding Analyst
- **Jobs:** subscription docs completeness, investor eligibility evidence (accredited/qualified purchaser,
  professional investor), redemption notice periods/gates calculation, ISDA/CSA collateral calls summary,
  shadow NAV vs administrator.
- **Tier B.**

### 71. VC Cap Table & Portfolio Admin (for angels, syndicates, small VC)
- **Jobs:** track SAFEs/convertible notes and conversions, pro-rata rights calendar, portfolio valuations,
  angel tax/SEIS/EIS/QSBS evidence checklists (UK/US/India [M]), K-1/annual statements.
- **Tier A.**
- **Existing:** Carta, AngelList [M].

---

## 8. ESG & sustainable investing roles

### 72. ESG Data & SFDR / Sustainability Disclosure Preparer
- **Jobs:** collect PAI/indicator data, map holdings to taxonomy eligibility, prepare Annex templates;
  SFDR 2.0 readiness (70% threshold per category, Taxonomy 15% safe harbour, naming rules, entity PAI
  abolished, start-up period 2027-28) [S]; UK SDR labels and anti-greenwashing rule [M]; SEC names rule [M];
  ISSB/IFRS S1-S2 alignment [M].
- **Tier B.**

### 73. Greenwashing & Fund-Name Checker
- **Jobs:** compare marketing text to binding strategy and holdings; flag terms that need a category
  (SFDR 2.0) or label (UK SDR); evidence pack.
- **Tier B:** compliance decides.

### 74. Climate & Stewardship Report Writer
- **Jobs:** TCFD/ISSB-style climate reports for pension schemes (UK TCFD for schemes ≥£1bn [M]) and asset
  managers; financed emissions (PCAF) calculation from provided data; engagement case studies.
- **Tier B.**

---

## 9. Pension schemes, trustees, employers, administrators

### 75. Employer Retirement Plan Administrator Assistant (401(k), auto-enrolment, PF, super)
- **Jobs:** payroll-to-plan contribution files; late-deposit checks; eligibility & auto-enrolment
  re-enrolment dates (UK every 3 years [M]); 401(k) nondiscrimination test data prep; Form 5500 data; EPF ECR
  challans prep and UAN onboarding; super guarantee (SG 12% [M]) calculations and Payday Super readiness
  (from 1 Jul 2026 [M], check); Nigeria remittance schedules (unremitted contributions focus) [S]; Kenya
  unremitted contribution exposure [S].
- **Who:** SMEs, HR/payroll firms, PEOs.
- **Tier A** (employer remits through official rails).

### 76. Pension Trustee Secretary & Board Pack Assistant
- **Jobs:** trustee meeting packs, minutes, risk register, conflicts, TPR General Code own-risk assessment
  (UK) [M], annual Chair's statement / value-for-members draft, implementation statement, member
  communications, trustee knowledge & understanding log.
- **Tier B:** trustees decide; scheme actuary/auditor sign their parts.

### 77. Pension Dashboards & Data Quality Analyst (UK and analogues)
- **Jobs:** member data matching readiness, common/conditional data scoring, find-request match analysis,
  value data production checks, post-connection monitoring (trustees remain responsible after connection)
  [S]; statutory connection by 31 Oct 2026 has passed — ongoing compliance [S].
- **Tier A/B.**
- **Analogues:** HK eMPF data migration [S], EPFO UAN/KYC seeding [S], Afore account registration [S].

### 78. Member Services & Benefit Calculation Assistant (scheme administrator)
- **Jobs:** retirement, transfer-out, death and leaver quotes prepared from scheme rules for administrator
  check; letter drafts; complaint (IDRP) first drafts; SA two-pot claim processing checks (volume: Alexforbes
  >1m savings pot claims) [S]; Nigeria RSA transfer/benefit claims; NPS exit/annuity paperwork.
- **Tier B:** administrator/trustee authorises payment.

### 79. DB Scheme Funding & Risk-Transfer Project Assistant
- **Jobs:** data cleanse tracker for buy-in/buy-out, GMP equalisation project tracking (UK) [M], benefit
  specification drafting support, insurer RFP admin.
- **Tier B:** actuary/trustees.

### 80. Superannuation Fund Member & Compliance Assistant (AU)
- **Jobs:** lost-member reunification campaigns (A$12.7bn fund-held lost super Jun 2025) [S]; insurance-in-super
  opt-in rules (PYS/PMIF) [M]; Retirement Income Covenant strategy evidence [M]; member complaints (AFCA)
  tracking; new class of adviser readiness (2026 revival) [S].
- **Tier B.**

### 81. SMSF Administrator's Assistant (AU)
- **Jobs:** annual return prep pack, member balances, contribution caps, pension minimums, investment strategy
  document draft, audit PBC checklist.
- **Tier B:** SMSF auditor/trustee sign.

### 82. Retirement Plan Fiduciary Fee & Fund Benchmarker
- **Jobs:** 408(b)(2) fee disclosure reading, recordkeeper/fund fee benchmarking, investment policy statement
  monitoring, committee minutes (ERISA fiduciary process evidence) [M]; UK VFM framework data (check) [M].
- **Tier B:** plan fiduciaries decide.

---

## 10. Wealth compliance & oversight roles (inside firms)

### 83. Financial Promotions & Marketing Reviewer
- **Jobs:** pre-review ads, social posts, websites, emails against FCA COBS 4/Consumer Duty, FINRA 2210, SEC
  Marketing Rule (testimonials, performance), SEBI IA advertisement code [M], MAS; produce marked-up version
  with rule references.
- **Tier B:** approver of record is human (FCA s21 approval).

### 84. Consumer Duty / Client Outcomes MI Analyst
- **Jobs:** outcome metrics (price & value, understanding, support, products), vulnerable-customer flags,
  board report draft, fair value assessment data.
- **Tier B.**

### 85. Best Interest / Reg BI & Fiduciary Evidence Assistant
- **Jobs:** check recommendation files for reasonably-available alternatives, cost comparison, rollover
  rationale (SEC 2026 exam focus) [S], Form CRS delivery logs, conflict disclosures.
- **Tier B.**

### 86. Suitability Surveillance Analyst
- **Jobs:** flag accounts whose holdings breach risk profile or concentration rules; switching/churning
  patterns; transaction-level vs portfolio-level suitability (CIRO finding) [S]; MiFID II periodic
  suitability report checks.
- **Tier B:** compliance investigates; no account freeze by AI.

### 87. Complaints Handling Assistant (wealth/pensions firm)
- **Jobs:** classify, set deadlines (FCA DISP, SEBI, AFCA), draft final response, root-cause analysis,
  complaints return data (FCA half-year).
- **Tier B.**

### 88. Personal Account Dealing & Conflicts Monitor
- **Jobs:** employee pre-clearance request checks against restricted lists, holding period rules, gifts &
  entertainment register, outside business activities, code-of-ethics attestations.
- **Tier B.**

### 89. AI-Use Governance & Disclosure Officer (for advice firms)
- **Jobs:** inventory of AI tools used in advice; client disclosure text (SEBI IA/RA requirement) [S];
  MAS AI risk-management mapping (oversight, lifecycle controls, inventory) [S]; EU AI Act creditworthiness
  /insurance high-risk boundaries [M]; testing records; vendor due diligence.
- **Tier B.**

### 90. Regulatory Change Tracker (wealth & pensions)
- **Jobs:** watch regulator feeds (SEC, FINRA, FCA, ESMA, SEBI, PFRDA, MAS, ASIC/APRA, CIRO, FSCA, PenCom,
  CONSAR, SUSEP/PREVIC), summarise what changes, map to policies, owner and deadline tracker.
- **Tier A.**

### 91. Licensing & Registration Admin (firm and adviser)
- **Jobs:** Form ADV annual amendment data, U4/U5 tracking, state notice filings, FCA SM&CR certification
  dates, SEBI IA certification/renewal (NISM), MAS representative notification, CPD hours.
- **Tier B:** filings submitted by the firm.

---

## Pains with evidence (summary)

| Pain | Evidence | Source |
|---|---|---|
| Forgotten retirement accounts | ~31.9m forgotten US 401(k)s, ~$2.1tn; +4.2m in 2025 (estimate disputed) | Capitalize via BusinessWire / NAPA [S] |
| Lost super | A$18.9bn (Jun 2025), A$21.2bn (Jun 2026), ~7.5m accounts | ATO [S] |
| Dormant provident funds | ₹9,330 cr in 30.9 lakh inoperative EPF accounts; LIC unclaimed ~₹5,565 cr | Business Today / Moneylife [S] |
| Unremitted pensions | Kenya Sh84bn (2025) | Nation / Standard [S] |
| Unregistered retirement accounts | Mexico >18m | CONSAR via press [S] |
| Advice gap | UK: only 9% of adults advised on pensions/investments in past year | FCA PS25/22 press release [S] |
| Complaints volume | UK pensions/decumulation 94,035 (H1 2025), investments 58,305 → 54,280 (H2) | FCA aggregate complaints data [S] |
| Early withdrawals harming retirement | SA two-pot: R57–60bn+ withdrawn; majority of 2026 claims are 2nd/3rd withdrawals; 80% for debt/essentials | Nedbank, Momentum via TimesLIVE, Alexforbes [S] |
| Unused accounts | NISA: only 62.2% of securities-firm accounts subscribed in 2025; China personal pension: 22% contributed | Morningstar, Caixin [S] |
| KYC/suitability weak at firms | CSA/CIRO Phase 2 (105 firms): KYC gaps widespread, transaction-level suitability | CIRO / BLG [S] |
| Adviser admin burden | 68% advisers use AI for notes/docs; note-taker category growing fast | Orion survey, Financial Planning [S] |
| Fund ops manual load | BNY 40+ AI solutions; Alter Domus hundreds of agents; Deloitte: 44% FS firms plan agentic AI in production 2026 | BNY, Cinven, Caruso blog [S] |
| Workforce scale | US personal financial advisors ~299,400 jobs (2025), median $105,070; growth 1% 2025–35 | BLS OOH [S] |

---

## Never an AI employee (tier C) in this segment — and why

1. **Discretionary portfolio manager / order placer** — placing, amending or cancelling orders on a client's
   account, or running a discretionary mandate, is licensed (MiFID II portfolio management, SEC adviser
   discretion, SEBI PMS) and moves money/assets. Hoola prepares trade lists only.
2. **Licensed adviser giving a personal recommendation** — "buy this fund / transfer this pension / take this
   annuity" for a specific person is regulated advice everywhere (FCA, MiFID II, SEBI IA, MAS FA, AFSL, CIRO).
   Even UK targeted support is delivered by an authorised firm under its own permission [S].
3. **Pension transfer specialist (UK DB transfers / safeguarded benefits)** — requires a specific qualified
   individual's sign-off [M].
4. **KYC/AML approver or MLRO** — accepting/rejecting an investor or client, or filing a SAR/STR as the
   institution.
5. **NAV striker / fund administrator of record / depositary** — publishing an official NAV, depositary
   oversight and cash-flow monitoring are regulated functions with liability.
6. **Fund director / trustee / pension trustee** — fiduciary decisions (distributions, investment strategy,
   funding) need a natural or corporate person with legal duties.
7. **Scheme actuary / valuation sign-off / independent valuer** — statutory certifications (funding
   valuations, IPEV fair value sign-off by valuation committee, auditor opinion).
8. **Regulatory filer as the institution** — Form PF, AIFMD Annex IV, Form ADV, SEBI returns are filed by the
   registrant under its credentials.
9. **Benefit payer / transfer executor** — releasing pension benefits, rollovers, two-pot withdrawals,
   capital calls and distributions moves money.
10. **Shariah board / ESG label certifier** — certification is a human/board attestation.
11. **Will witness / notary / probate applicant in her name** — legal formalities.
12. **Approver of financial promotions of record (UK s21)** — named approver responsibility.

---

## Top 10 roles to build first and why

1. **#1 Lost & Forgotten Retirement Money Finder** — pure tier A, consumer, every country, enormous and
   sourced money pool (US $2.1tn, AU A$21bn, IN ₹9,330 cr + LIC, MX 18m accounts), official free tracing
   portals she uses herself; strong emotional pull and viral.
2. **#4 Personal Portfolio Tracker & Statement Reader** — the data spine for every other consumer role; works
   from uploaded statements today, AA/Plaid/Open Finance later; India CAS makes it immediate.
3. **#17 Meeting Prep & Notes Scribe** — proven paid demand (Jump/Zocks share, 68% adoption, Morgan Stanley);
   B-tier but low risk because the adviser reviews; sells to RIAs/IFAs/MFDs worldwide.
4. **#16 Client Fact-Find & Onboarding Assistant** — regulators' own reviews show KYC gaps (CIRO Phase 2);
   pairs with #17 and #18 into an "adviser back office" bundle.
5. **#18 Suitability / Statement-of-Advice Drafter** — biggest time sink for licensed advisers; the human signs,
   Hoola drafts with AI-use disclosure (SEBI) and audit trail (MAS).
6. **#2 + #3 Retirement Readiness & Income Planner** (ship together) — huge consumer need around NISA/IRA/
   NPS/super/two-pot; pure calculation and explanation with sourced tax tables.
7. **#61 LP Alternatives Document Processor** — family offices and HNW drown in capital calls/K-1s; Canoe proves
   the market; tier A; calendars and cash forecast are high value.
8. **#35 Family Office Consolidated Reporting Analyst** — ~8–9k SFOs plus MFOs; consolidates #61 and #4;
   premium pricing.
9. **#75 Employer Retirement Plan Administrator Assistant** — SMEs everywhere must remit contributions on time
   (unremitted Sh84bn in Kenya, PenCom remittance enforcement, EPF ECR, super payday rules); tier A; ties to the
   existing payroll employee.
10. **#83 Financial Promotions & Marketing Reviewer** (with #89 AI-Use Governance) — every wealth/asset firm
    must pre-approve marketing; AI-use disclosure is now law in India and supervisory expectation in
    Singapore; clear B-tier with a named approver.

---

## Sources (opened or read in search results this session)

- O*NET Personal Financial Advisors 13-2052.00: https://www.onetonline.org/link/summary/13-2052.00?sourceid=ADE219
- BLS OOH Personal Financial Advisors: https://www.bls.gov/ooh/business-and-financial/personal-financial-advisors.htm
- ISCO 2412 / ESCO investment fund manager mirrors: https://www.openriskmanual.org/wiki/ISCO_Occupation_Group_2412.6_Investment_Fund_Manager ; https://worldoftaxonomy.com/crosswalks/isco_08/2412/esco_occupations
- FCA aggregate complaints 2025 H1: https://www.fca.org.uk/data/complaints-data/aggregate-complaints-data-2025-h1 ; H2: https://www.fca.org.uk/data/complaints-data/aggregate-complaints-data-2025-h2 ; Professional Adviser: https://www.professionaladviser.com/news/4520850/fca-complaints-pensions-investment-gripes-rise
- FCA targeted support PS25/22: https://www.fca.org.uk/publications/policy-statements/ps25-22-supporting-consumers-pensions-investment-decisions-rules-targeted-support ; press release: https://www.fca.org.uk/news/press-releases/millions-extra-help-investments-pensions-decisions ; Brodies: https://brodies.com/insights/pensions/fcas-targeted-support-regime/ ; Deloitte: https://www.deloitte.com/uk/en/blogs/ecrs/the-targeted-support-framework-a-once-in-a-generation-opportunity-to-reform-customer-support.html
- Pensions dashboards: https://www.gov.uk/government/publications/pensions-dashboards-guidance-on-connection-the-staged-timetable/pensions-dashboards-guidance-on-connection-the-staged-timetable ; https://www.thepensionsregulator.gov.uk/trustees/contributions-data-and-transfers/dashboards-guidance/when-your-scheme-needs-to-connect-with-dashboards ; https://www.shoosmiths.com/perspectives/stories/articles/connected-to-pensions-dashboards-what-trustees-must-do-next ; https://www.burges-salmon.com/articles/102o0e8/pensions-dashboards-update-september-2026
- SEBI AI disclosure: https://taxmann.com/post/blog/sebi-mandates-ias-and-ras-to-disclose-use-of-ai-tools-in-providing-investment-advice-research-services-to-clients ; https://www.outlookbusiness.com/amp/story/markets/investment-advisers-research-analysts-should-disclose-ai-tool-usage-to-clients-sebi
- MAS AI risk management: https://www.mas.gov.sg/publications/consultations/2025/consultation-paper-on-guidelines-on-artificial-intelligence-risk-management ; https://www.mas.gov.sg/-/media/mas-media-library/publications/consultations/bd/2025/response-to-feedback-received-on-guidelines-on-artificial-intelligence-risk-management.pdf ; https://www.allenandgledhill.com/vn/publication/articles/34686/mas-publishes-ai-risk-management-guidelines-setting-out-supervisory-expectations-on-responsible-ai-adoption
- SEC 2026 exam priorities: https://whitecase.com/insight-alert/new-priorities-2026-what-investment-advisers-and-broker-dealers-can-expect ; https://www.foley.com/insights/publications/2025/12/sec-releases-its-2026-examination-priorities/
- IAPD / BrokerCheck: https://www.investor.gov/researching-managing-investments/working-investment-professionals/brokers-advisors/using-iapd
- Fund admin AI: https://www.bny.com/corporate/global/en/insights/ai-fund-operations.html ; https://www.deloitte.com/lu/en/our-thinking/future-of-advice/agentic-ai-transforming-asset-servicing.html ; https://grantthornton.com/insights/articles/asset-management/2025/ai-plays-for-smart-fund-admin-and-profitability ; https://www.cinven.com/news-insights/alter-domus-turning-ai-into-a-structural-advantage-in-fund-services/ ; https://rsmus.com/insights/industries/private-equity/ai-in-fund-administration.html ; https://www.getcaruso.com/en-us/resources/blog/agentic-ai-fund-administration-platforms-not-ready ; https://carta.com/uk/en/product-updates/agentic-experiences/
- Adviser AI note-takers: https://www.financial-planning.com/news/jump-zocks-top-category-as-ai-note-taker-adoption-soars ; https://www.kitces.com/blog/ai-notetakers-client-meeting-for-financial-advisors-adoption-satisfaction-trends-research-productivity/ ; https://www.investmentnews.com/advisor-tech/jump-and-zocks-raise-dueling-series-b-funding-rounds/265992
- Morgan Stanley Debrief: https://www.morganstanley.com/press-releases/ai-at-morgan-stanley-debrief-launch ; https://openai.com/index/morgan-stanley/
- FP Alpha / Holistiplan: https://www.financial-planning.com/news/fp-alpha-debuts-estate-insights-2-0 ; https://www.kitces.com/blog/the-latest-in-financial-advisortech-november-2024-holistiplan-new-estate-planning-document-tool-quivr-currentclient-news/
- Canoe Intelligence: https://canoeintelligence.com/ai/ ; https://canoeintelligence.com/behind-the-release-our-product-team-talks-canoe-ai-hybrid-extraction/
- Hebbia: https://www.hebbia.com/blog/how-private-equity-teams-use-hebbia ; Glean PE: https://www.glean.com/solutions/industries/financial-services/private-equity-venture-capital
- SFDR 2.0: https://www.bakermckenzie.com/en/insight/publications/alerts/2025/12/eu-sfdr-2-0-simplified-disclosures-new-categories-stricter-marketing-rules ; https://sidley.com/en/insights/newsupdates/2025/11/sfdr--five-key-takeaways-from-the-european-commissions-proposal
- EU Retail Investment Strategy: https://www.europarl.europa.eu/news/en/press-room/20251215IPR32220/deal-on-new-measures-to-boost-citizens-investments-in-financial-markets ; https://cms.law/en/int/legal-updates/EU-Retail-Investment-Strategy-Political-Agreement-Key-Points-and-Implications-for-EU-and-non-EU-Firms ; https://cdn.ceps.eu/2026/02/Lannoo-No-104-RIS.pdf
- Forgotten 401(k): https://www.businesswire.com/news/home/20250930788421/en ; https://www.napa-net.org/news/2025/10/how-big-of-a-problem-are-forgotten-401ks/
- ATO lost super: https://www.ato.gov.au/about-ato/research-and-statistics/in-detail/super-statistics/super-accounts-data/super-data-lost-unclaimed-multiple-accounts-and-consolidations/total-lost-fund-held-and-ato-held-super ; https://www.ato.gov.au/media-centre/21-billion-dollars-in-lost-super-find-yours
- Australia DBFO / New Class of Adviser: https://www.allens.com.au/insights-news/insights/2026/08/treasury-unveils-measured-policy-responses-to-shield-and-first-guardian-collapses/ ; https://www.professionalplanner.com.au/2026/08/licensees-barred-from-new-class-of-adviser-under-revived-dbfo-reforms/
- India EPF/NPS: https://www.businesstoday.in/personal-finance/news/story/rs-9330-crore-unclaimed-how-to-claim-money-from-inoperative-epf-accounts-544143-2026-07-21 ; https://moneylife.in/article/lics-unclaimed-funds-rise-to-7318-crore-epfo-inoperative-accounts-hold-9330-crore-govt/81108.html ; https://www.angelone.in/news/economy/nps-and-apy-assets-cross-16-lakh-crore-as-subscriber-base-exceeds-9-crore ; https://www.newkerala.com/news/a/pfrda-aims-achieve-rs-100-lakh-crore-pension-207.htm
- Hong Kong eMPF: https://www.hsbc.com.hk/mpf/empf ; https://www.wtwco.com/en-hk/insights/2025/08/important-notes-for-mpf-members-transferring-to-the-empf-platform ; https://news.rthk.hk/rthk/en/component/k2/1808014-20250607.htm
- China personal pension: https://www.caixinglobal.com/2025-08-18/caixin-weekly-nationwide-rollout-of-the-individual-pension-system-102352928.html ; https://www.china-briefing.com/news/private-pension-scheme-expands-nationwide-in-china/ ; https://www.caixinglobal.com/2025-10-30/china-takes-pension-investment-pilot-nationwide-in-bid-to-shore-up-retirement-system-102377582.html
- Japan NISA: https://www.fsa.go.jp/common/conference/danwa/20260520_2.pdf ; https://www.morningstar.com/business/insights/blog/japan-nisa-market-growth-trends
- Family offices: https://www.deloitte.com/global/en/about/press-room/global-edition-explores-the-rapid-expansion-family-offices-and-ffers-vision-of-the-future-landscape.html ; https://www.ubs.com/br/en/wealthmanagement/insights/global-family-office-report.html ; https://www.withintelligence.com/insights/assessing-global-single-family-office-numbers/
- South Africa two-pot: https://personal.nedbank.co.za/learn/blog/2-pot-system-latest-news.html ; https://www.timeslive.co.za/news/business/2026-07-25-retirement-experts-warn-against-repeated-two-pot-withdrawals/ ; https://iol.co.za/mercury/2025-03-05-alexforbes-sees-surge-in-savings-pot-withdrawal-claims-as-new-tax-year-starts/ ; https://allafrica.com/stories/202609150212.html
- Nigeria PenCom: https://www.pencom.gov.ng/wp-content/uploads/2024/02/REVISED-REGULATION-FOR-THE-TRANSFER-OF-RSA.pdf ; https://www.legit.ng/business-economy/economy/1664595-another-27701-nigerian-workers-transfer-window-change-pfas ; https://www.legit.ng/business-economy/industry/1738597-pencom-sets-year-deadline-pfas-open-3-million-funded-pension-accounts/
- Kenya: https://nation.africa/kenya/business/unremitted-pension-deductions-hit-sh85bn-in-blow-to-retirees-5545990 ; https://ufaa.go.ke/faq ; https://www.the-star.co.ke/opinion/leader/2025-08-04-editorial-ufaa-must-return-kenyans-cash-faster ; https://www.rba.go.ke/unclaimed-assets-in-the-retirement-benefits-industry/
- Brazil previdência: https://www.infomoney.com.br/minhas-financas/previdencia-privada-em-2025-como-as-novas-regras-ampliam-o-acesso-ao-produto/ ; https://neofeed.com.br/wealth-management/previdencia-privada-entra-em-modo-rouba-monte-apos-iof-no-vgbl/en/ ; https://www.correio24horas.com.br/politica/previdencia-privada-como-funciona-a-portabilidade-para-fugir-de-taxas-altas-sem-pagar-imposto-0626
- Mexico Afore: https://www.elimparcial.com/dinero/2025/08/01/consar-permite-que-una-segunda-vez-al-ano-te-cambies-de-afore-pero-solo-por-esta-razon/ ; https://tiempo.com.mx/economia/prohiben-premios-por-cambiar-afore-reglas-consar-2026/ ; https://www.tusbuenasnoticias.com/noticias/economia/2025/06/25/47001-guia-para-cambiar-de-afore ; https://www.infobae.com/mexico/2025/10/08/monitor-afore-2025-inbursa-coppel-y-pensionissste-lideran-ranking-segun-el-gobierno-de-mexico/
- UAE end-of-service / DEWS: https://u.ae/en/information-and-services/jobs/Sector-of-employment/employment-in-the-private-sector/end-of-service-benefits-for-employees-in-the-private-sector ; https://www.khaleejtimes.com/business/difcs-dews-savings-scheme-surpasses-1-billion-in-assets?amp=1 ; https://www.pwc.com/m1/en/media-centre/articles/overview-of-end-of-service-benefits-in-uae.html
- Canada CFR: https://www.ciro.ca/node/31701 ; https://www.blg.com/insights/2025/12/csa-ciro-illuminate-enhanced-expectations-in-phase-2-client-focused-reform-sweep ; https://www.wealthprofessional.ca/news/industry-news/one-risk-profile-fits-all-clients-is-dead-as-csa-and-ciro-push-real-kyc/391116

Everything tagged [M] (e.g. specific rule numbers such as UCITS 5/10/40, SG 12%, Payday Super dates, US 5%
foundation payout, UK DB transfer advice threshold, product vendor names like Addepar, Betterment, Orion,
Kurtosys, Loopio) is from memory — verify before building.
