# Segment 05: Capital markets, investment banking, broking & trading, market infrastructure and treasury (worldwide)

Research date: 22 Nov 2026. Hard limits from the brief apply to every role: the AI never places, cancels or
affirms an order or trade, never releases a settlement instruction or payment, never approves an account /
KYC / margin / limit, never publishes research or a rating under its own name, never files a regulatory
report as the institution, never signs a prospectus, fairness opinion or valuation. It prepares, checks,
calculates, explains, drafts, tracks and reminds; a named human decides.

Legend: **Tier A** = admin/prepare, safe for the user alone. **Tier B** = assists a named licensed or
accountable person who decides and signs. **Tier C** = reserved for humans (listed at the end).
"from memory - verify" marks facts I did not open a page for.

---

## 0. Where the jobs come from (taxonomies used)

| Taxonomy | Codes in this segment | Source |
|---|---|---|
| O*NET / US SOC | 41-3031.00 Securities, Commodities & Financial Services Sales Agents (30 tasks: place bids/offers, watch markets, order tickets, check transactions for regulatory compliance, design hedging strategies, calculate commissions, forward orders to exchanges...; titles Broker, Commodities Broker, Equity Trader, Trader) | https://www.onetonline.org/link/summary/41-3031.00 (opened) |
| O*NET | 13-2051.00 Financial & Investment Analysts (26 tasks: price securities offered to the public, financial models for transaction impact, prepare deal execution materials, valuation, monitor developments, presentations) | https://www.onetonline.org/link/summary/13-2051.00 (opened) |
| O*NET (from memory - verify) | 13-2099.04 Fraud examiners (surveillance overlap), 43-4011 Brokerage clerks, 43-3099 / 43-9041 securities processing clerks, 11-3031.01 Treasurers and Controllers, 13-2054 Financial Risk Specialists, 13-2052 Personal Financial Advisors (adjacent) | onetonline.org |
| US BLS OOH | Securities, commodities and financial services sales agents, median pay $78,140 (May 2024) | https://www.bls.gov/ooh/sales/securities-commodities-and-financial-services-sales-agents.htm (via search) |
| ILO ISCO-08 (from memory - verify) | 3311 Securities and finance dealers and brokers; 2413 Financial analysts; 1211 Finance managers (treasurer); 3313 Accounting associate professionals; 4312 Statistical, finance and insurance clerks | ilo.org/public/english/bureau/stat/isco |
| EU ESCO (from memory - verify) | stockbroker, securities broker, commodity trader, financial trader, foreign exchange trader, investment analyst, corporate investment banker, treasury manager, back office specialist, investor relations manager, credit analyst | esco.ec.europa.eu |
| UK SOC 2020 (from memory - verify) | 3532 Brokers, 2422 Finance & investment analysts and advisers, 1131 Financial managers & directors, 4122 Book-keepers/payroll (adjacent), 3534 Finance and investment analysts | ons.gov.uk |
| ANZSCO (from memory - verify) | 222111 Commodities Trader, 222112 Finance Broker, 222113 Insurance broker (adj), 222211 Financial Market Dealer, 222212 Futures Trader, 222213 Stockbroking Dealer, 224711 Management Consultant (adj), 221214 Internal Auditor (adj) | abs.gov.au |

Bank/broker org charts the roles below are carved from: Front office (IBD: coverage, M&A, ECM, DCM, leveraged
finance; Markets: sales, trading, structuring, research, market making), Middle office (risk, product control,
trade support, compliance/surveillance), Back office (settlements, reconciliations, asset servicing, collateral,
custody, regulatory reporting, client onboarding), Treasury (ALM, liquidity, funding, FTP), Infrastructure
(exchanges, CCPs, CSDs, registrars, rating agencies), Issuer side (IR, company secretary, corporate treasury).

---

## 1. Region reference (named once, referenced per role as R-codes)

| Code | Region | Regulators, venues, infrastructure, rules |
|---|---|---|
| R-US | United States | SEC, FINRA (BrokerCheck, Rule 2210 communications, 2241 research, Reg BI), CFTC/NFA (futures, swaps), MSRB (munis); NYSE, Nasdaq, Cboe, CME; DTCC (NSCC, DTC, CTM affirmation), CAT (Consolidated Audit Trail), OCC; T+1 since 28 May 2024; customer protection Rule 15c3-3, net capital 15c3-1; FINRA arbitration; Reg SHO. |
| R-EU | EU/EEA | ESMA + national NCAs (BaFin, AMF, CONSOB, AFM, CSSF...); MiFID II/MiFIR (best execution, transaction reporting, RTS 6 algo controls), MAR (insider lists, STORs), CSDR (settlement discipline, cash penalties), EMIR (derivatives reporting, margin), SFTR, PRIIPs KID, Prospectus Regulation / Listing Act; FASTER withholding-tax directive (from memory - verify dates); T2S settlement; T+1 on 11 Oct 2027. |
| R-UK | United Kingdom | FCA (Consumer Duty, CASS client assets, UK MAR, financial promotions), PRA (bank liquidity/ALM), Bank of England (CCPs, CSD), LSE, LCH, ICE, Euroclear UK & International (CREST); Financial Ombudsman Service; T+1 on 11 Oct 2027. |
| R-GCC | Gulf | Saudi CMA + Tadawul, Edaa (CSD), Muqassa (CCP); UAE SCA + ADX, DFM; DIFC DFSA, ADGM FSRA; Qatar QFMA; Bahrain CBB; Sharia-compliant sukuk and screens. (from memory - verify) |
| R-IN | India | SEBI (SCORES complaints, SMART ODR, RA/IA registration, LODR disclosures, algo/API framework for retail, ICDR for IPOs/DRHP), NSE, BSE, MCX, NCDEX; NSDL, CDSL (demat); clearing NSCCL/ICCL; RBI (forex, G-secs, Retail Direct, ALM for banks, LCR); T+1 fully from Jan 2023 (from memory - verify); IEPF unclaimed shares. |
| R-SG | Singapore / SE Asia | MAS, SGX + CDP; Malaysia SC + Bursa; Indonesia OJK + IDX + KSEI; Thailand SEC + SET; Philippines SEC + PSE; Vietnam SSC + HOSE. (from memory - verify) |
| R-CNHK | China / Hong Kong | CSRC, SSE, SZSE, BSE, ChinaClear, Stock Connect; HK SFC, HKMA, HKEX, CCASS (Hong Kong studying shorter settlement - check). (from memory - verify) |
| R-JPKR | Japan / Korea | Japan FSA, JPX (TSE, OSE), JSCC, JASDEC, NISA tax-free accounts; Korea FSC/FSS, KRX, KSD, KOFIA. (from memory - verify) |
| R-ANZ | Australia / NZ | ASIC, ASX (CHESS replacement: clearing Release 1 in 2026, settlement/sub-register 2028-29), AFCA complaints, RBA FMI oversight; NZ FMA, NZX. ASX source: https://www.asx.com.au/markets/clearing-and-settlement-services/chess-replacement (via search), https://www.waterstechnology.com/trading-tech/7951687/asx-chess-replacement-to-be-delivered-in-phases-with-clearing-first-in-2026 |
| R-AF | Africa | Nigeria SEC (Investments and Securities Act 2025), NGX, CSCS; Kenya CMA, NSE, CDSC; South Africa FSCA, Prudential Authority, JSE, Strate. Kenya NSE added 49,363 new accounts in 2025 (https://www.zawya.com/en/economy/africa/kenya-nse-gets-49-363-new-share-accounts-as-ipo-season-kicks-off-with-sale-of-kpc-s17ab09e, via search); Nigeria ISA 2025 (https://webiis08.mondaq.com/nigeria/economic-analysis/1734368/nigeria-capital-markets-highlights-of-the-key-activities-in-2025-and-outlook-for-2026, via search). |
| R-LATAM | Latin America | Brazil CVM, B3 (exchange + CSD + CCP), BCB, Pix for cash legs/retail funding, Tesouro Direto; Mexico CNBV, BMV, BIVA, Indeval; Chile CMF; Colombia SFC. (from memory - verify) |
| R-CA | Canada | CIRO (merged IIROC+MFDA), CSA provincial regulators (OSC, AMF...), TSX/TMX, CDS, OBSI ombudsman; T+1 since 27 May 2024. (from memory - verify) |
| R-GLOBAL | Cross-border | SWIFT + ISO 20022 (CBPR+ coexistence ended Nov 2025; structured/hybrid addresses and MT101 end in Nov 2026 window, possibly extended - check: https://www.swift.com/standards/iso-20022/iso-20022-bytes/journey-continues via search), ISDA/CSA, GMRA/GMSLA, IOSCO, BCBS (LCR, NSFR, IRRBB), LEI (GLEIF), ANNA/ISIN, FIX protocol. |

---

## 2. Roles

Grouped A-K. Each: what it does / who hires / jobs-to-be-done / tier & who decides / data & rails / region
notes / existing products.

### A. Retail investors and self-directed traders (consumer, sole trader)

**1. Portfolio Statement Reader**
- Reads every broker, demat, fund and pension statement she has and explains, in one plain view, what she owns, what it cost and what changed.
- Hires: consumer, sole trader.
- Jobs: parse PDF/CSV statements and contract notes; merge holdings across brokers; compute cost basis and unrealised gain; flag concentration (one stock > X% of wealth); list dividends/interest received; spot holdings she forgot (old demat, dormant account); explain each instrument in one line; month-on-month change; export a clean sheet.
- Tier A. She decides everything; no advice "buy/sell".
- Data/rails: statement uploads; India CAS (NSDL/CDSL consolidated account statement) and Account Aggregator; UK/EU open banking does not cover investments (check); US Plaid Investments; broker read-only APIs (Upstox, Zerodha Kite, Interactive Brokers Flex).
- Regions: R-IN CAS is the easiest global case; R-US 1099-B/composite statements; R-EU annual cost & charges statements under MiFID II; R-ANZ CHESS holding statements.
- Products: Robinhood Cortex answers portfolio questions on live account data (https://robinhood.com/us/en/support/articles/robinhood-cortex, via search); INDmoney, Kuvera (IN), Sharesight (ANZ/UK) - from memory - verify.

**2. Investor Education Coach**
- Teaches market basics in her language at her pace: what a share, bond, ETF, option, IPO, settlement cycle is; checks understanding with quizzes.
- Hires: consumer, students, NGOs, investor-protection funds, brokers (for client education), exchanges.
- Jobs: lessons tied to her real questions; glossary; simulated (paper) portfolios; explain a news event's market mechanics; risk-of-loss explainers; jargon-free reading of a KID/KIM/fact sheet; course progress; certificate prep for NISM/SIE/CISI basics.
- Tier A. No personalised recommendation.
- Data/rails: regulator investor-education material (SEBI investor site, FINRA/Investor.gov, FCA, ASIC Moneysmart, MAS MoneySense); exchange learning portals.
- Regions: all; language coverage matters (Hindi/Bahasa/Portuguese/Swahili/Arabic). Nigeria SEC notes fewer than 4% of Nigerians invest (headline seen via search, https://businessday.ng/?p=1015138 - verify).
- Products: Zerodha Varsity (IN, from memory), Public.com Alpha copilot (https://axios.com/2025/11/17/ai-stock-market-public, via search).

**3. Derivatives Reality-Check Coach**
- Before she trades F&O/CFDs/options, shows the maths: breakeven, margin, worst case, cost of trading, and the published loss statistics.
- Hires: consumer, brokers (as a protective tool), regulators/NGOs.
- Jobs: payoff and breakeven calculator; margin and leverage explainer; total cost (brokerage, taxes, spreads) per round trip; "what if it gaps 5%"; her own past F&O P&L from contract notes; reminder of regulator loss stats; cooling-off nudge; journal prompts.
- Tier A. Never places or blocks a trade.
- Data/rails: contract notes, broker P&L reports; exchange margin files (SPAN/VaR files from NSE, CME); option chains.
- Regions: R-IN - SEBI: 93% of over 1 crore individual F&O traders lost money FY22-FY24, aggregate losses over Rs 1.8 lakh crore (https://www.sebi.gov.in/media-and-notifications/press-releases/sep-2024/updated-sebi-study-reveals-93-of-individual-traders-incurred-losses-in-equity-fando-between-fy22-and-fy24-aggregate-losses-exceed-1-8-lakh-crores-over-three-years_86906.html, opened); FY25 follow-up 91% (https://moneylife.in/article/91-percentage-of-retail-traders-lost-money-in-derivatives-losses-in-fo-surged-41-percentage-to-rs105-lakh-crore-in-fy25-sebi-study/77613.html, via search). R-EU/UK - ESMA standard warning "74-89% of retail investor accounts lose money when trading CFDs" (https://www.esma.europa.eu/node/84933, via search). R-ANZ ASIC CFD product intervention (from memory - verify).
- Products: few; broker-side risk disclosures only. Gap = opportunity.

**4. Broker Fee & Charges Auditor**
- Checks every contract note and statement against the broker's published tariff and the law; finds overcharges, hidden FX spreads and inactivity fees.
- Hires: consumer, sole trader, small family office.
- Jobs: extract per-trade brokerage, exchange fees, stamp duty, STT/FTT, GST/VAT; recompute from tariff; FX conversion spread on foreign trades; custody/AMC/dormancy fees; annual cost & charges vs MiFID disclosure; compare brokers on her actual activity; draft a query to the broker.
- Tier A.
- Data/rails: contract notes, tariff sheets, statements.
- Regions: R-IN STT/stamp duty schedules; R-EU MiFID ex-post cost disclosure; R-UK Consumer Duty fair value; R-US SEC Section 31 fee/FINRA TAF (from memory - verify).
- Products: none dominant (consumer comparison sites only).

**5. Capital Gains & Tax-Lot Calculator (investments)**
- Turns her trades and corporate actions into the capital-gains schedule her tax return or accountant needs.
- Hires: consumer, sole trader, accounting firms.
- Jobs: FIFO/specific-lot cost basis; adjust for splits/bonus/mergers/rights; short vs long term by local holding periods; wash-sale/bed-and-breakfasting rules; foreign-currency gains; dividend and withholding tax summary with treaty credit; grandfathering (India 31 Jan 2018 rule, from memory - verify); export to tax software format.
- Tier A (B when an accountant signs the return).
- Data/rails: contract notes, broker tax P&L, 1099-B, CAS; tax portals (India AIS/26AS, US IRS, UK HMRC) read only.
- Regions: R-US wash-sale 30 days; R-UK 30-day bed-and-breakfast + Section 104 pooling; R-IN STCG/LTCG and Schedule 112A; R-ANZ CGT 50% discount; R-CA superficial loss; R-JPKR NISA tax-free (from memory - verify all).
- Products: Koinly/CoinTracker (crypto), Sharesight, TaxBit; Hoola can be multi-asset and multi-country.

**6. Corporate Actions Tracker (retail)**
- Tells her about every dividend, split, bonus, rights issue, buyback/tender, merger and AGM on what she holds, with what she must do and by when.
- Hires: consumer, small investors, family offices.
- Jobs: watch exchange announcements for her holdings; explain mandatory vs voluntary events; calculate rights entitlement and renunciation value; buyback acceptance-ratio maths; deadline reminders; check the credit actually landed; tax effect.
- Tier A. She tenders/applies herself through her broker.
- Data/rails: exchange announcement feeds (NSE/BSE, SEC EDGAR 8-K, RNS, ASX), registrar notices, broker statements.
- Regions: all; buyback tender route specific to R-IN; DRIP in R-US/R-ANZ.
- Products: broker apps notify partially; DTCC says corporate-action processing costs the industry ~$58bn a year (https://www.dtcc.com/insights/2025/staggering-stats-understanding-inefficiencies-within-corporate-actions-processing, opened).

**7. IPO / Primary Issue Explainer & Application Tracker**
- Reads an IPO prospectus/DRHP/S-1 and explains the business, risks, valuation vs peers, use of proceeds and lock-ups; tracks her application, allotment and refund.
- Hires: consumer, sole trader.
- Jobs: prospectus summary with page refs; risk factors in plain words; peer P/E comparison; subscription status by category; allotment probability maths; ASBA/UPI mandate status; refund/unblock tracking; listing-day calendar; NCD/bond issue explainer too.
- Tier A. No "apply" recommendation.
- Data/rails: SEBI/SEC EDGAR filings, exchange IPO pages, registrar allotment status pages.
- Regions: R-IN ASBA/UPI-blocked IPO funds; R-US S-1/F-1; R-EU prospectus + Listing Act; R-CNHK STAR/HKEX; R-AF Kenya IPO season (KPC listing, via search above).
- Products: none consumer-grade with grounding; Rogo drafts IPO documents for banks (https://sacra.com/research/rogo, via search).

**8. Investment Scam & Registration Checker**
- Before she trusts a "tip" group, adviser, app or broker, checks it is really registered and flags known scam patterns.
- Hires: consumer, NGOs, banks (customer protection).
- Jobs: look up registration (SEBI RA/IA/broker, FINRA BrokerCheck, FCA register, ASIC, MAS, SFC); compare against warning lists (FCA warning list, IOSCO I-SCAN); recognise pump-and-dump, guaranteed returns, fake trading apps, "VIP group" tells; reverse-search the app/website; draft a report to the regulator/cyber police.
- Tier A.
- Data/rails: public registers and warning lists.
- Regions: R-US FINRA 2026 report flags GenAI as accelerant for cyber fraud (https://www.debevoise.com/insights/publications/2025/12/finras-2026-regulatory-oversight-report-continued, via search); R-IN SEBI unregistered-adviser drives; IOSCO I-SCAN global (from memory - verify).
- Products: register lookups exist; few unify them.

**9. Broker & Market Complaint Drafter**
- Turns her problem (wrong trade, unauthorised trade, delayed payout, mis-selling) into a complete complaint with evidence and follows the escalation ladder.
- Hires: consumer, sole trader, legal-aid NGOs.
- Jobs: timeline from contract notes, emails, statements; identify the rule breached; draft to broker grievance cell; escalate to regulator portal and ombudsman/arbitration in order and on time; track deadlines; prepare an arbitration claim bundle.
- Tier A (B if a lawyer files).
- Data/rails: SEBI SCORES + SMART ODR; FINRA arbitration; FOS (UK); AFCA (AU); OBSI (CA); FSCA/Ombud (ZA).
- Evidence of demand: SEC received a record 53,753 tips, complaints and referrals in FY2025 (https://www.troutman.com/insights/sec-fy-2025-enforcement-results-reveal-changing-priorities-from-record-numbers-to-investor-protection/, via search); SEC OIEA closed 31,472 investor contact files in FY2025 (https://sec.gov/data/investor-complaints-data, via search); SEBI SCORES ~4-5k complaints disposed per month (https://www.business-standard.com/markets/news/sebi-resolves-over-4k-investor-complaints-via-scores-platform-in-mar-2025-125041400786_1.html, via search).
- Products: none specialised.

**10. Unclaimed Shares & Dividends Recovery Assistant**
- Finds shares/dividends of hers or a deceased relative that went unclaimed and prepares the recovery papers.
- Hires: consumer, legal heirs, small law/CA firms.
- Jobs: search unclaimed registers; reconstruct holdings from old certificates; transmission checklist (death cert, succession, nomination); prepare IEPF-5 style claim; physical-to-demat conversion steps; registrar correspondence tracker.
- Tier A (claims signed by her).
- Data/rails: India IEPF search, registrar portals; US state unclaimed property (MissingMoney); UK Gretel/registrar searches (from memory - verify).
- Regions: R-IN huge backlog of physical-share claims; R-US state escheatment; R-UK, R-ANZ (ASIC MoneySmart unclaimed).
- Products: specialist human agencies; little AI.

**11. Account Transfer & Nominee/Succession Helper**
- Handles moving holdings between brokers/demat accounts, closing dormant accounts, adding nominees and transmission after death.
- Hires: consumer.
- Jobs: transfer form pack (ACATS, off-market transfer, delivery instruction slip); checklist per depository; track status; reconcile what arrived; nominee updates; transmission document list.
- Tier A.
- Data/rails: broker forms, depository rules (DTC ACATS, NSDL/CDSL, CREST, CHESS HIN/SRN).
- Regions: as R-codes; R-ANZ HIN vs SRN distinction.
- Products: none.

**12. Bonds & Fixed-Income Explainer for Savers**
- Explains government bonds, T-bills, corporate bonds and bond funds; calculates yields and compares to bank deposits.
- Hires: consumer, retirees, small trusts.
- Jobs: YTM / current yield / after-tax yield; duration "what if rates move 1%"; ladder builder (paper); credit rating meaning; auction calendar; coupon tracker; compare with FD/CD rates.
- Tier A.
- Data/rails: RBI Retail Direct, TreasuryDirect, UK DMO gilts, Tesouro Direto (BR), Kenya DhowCSD / M-Akiba (from memory - verify), rating agency public lists.
- Products: few.

**13. Shareholder Voice (Proxy & AGM Assistant)**
- Summarises AGM/EGM resolutions on her holdings, what proxy advisers said, and helps her vote or ask a question.
- Hires: consumer, small investors, investor associations.
- Jobs: notice summary; related-party transactions in plain words; director pay vs performance; e-voting deadline reminders; draft AGM questions; record her votes.
- Tier A.
- Data/rails: company notices; e-voting portals (NSDL e-voting, Broadridge ProxyVote, Computershare).
- Products: Broadridge (institutional), Tumelo/passthrough voting (UK, from memory - verify).

**14. Trading Journal & Behaviour Reviewer**
- For active traders: keeps the journal, measures win rate, average loss vs gain, overtrading, revenge trading; shows patterns honestly.
- Hires: consumer, prop-firm aspirants.
- Jobs: import fills; tag setups; P&L stats; drawdown; cost drag; rule adherence vs her own written plan; weekly review; flag loss-chasing sequences.
- Tier A. Never trades.
- Data/rails: broker trade history exports/APIs (read only).
- Products: Tradervue, Edgewonk (from memory - verify).

### B. Retail and institutional brokerage firms (broker-dealer, stockbroker, futures commission merchant)

**15. Client Onboarding Pack Preparer (broker)**
- Prepares and checks a new client's account-opening file so the broker's compliance officer can approve it.
- Hires: broker, wealth platform, fintech.
- Jobs: document checklist by client type (individual, HUF, company, trust, NRI/foreign); data extraction and cross-check (name/DOB/address across documents); suitability/appropriateness questionnaire scoring; risk-profile draft; sanctions/PEP pre-screen result summary; FATCA/CRS self-cert check; W-8BEN validity; derivative-segment income-proof check; missing-items email.
- Tier B. KYC approval and account activation = compliance officer (tier C act).
- Data/rails: KRA (India KYC registration agencies), CKYC, DigiLocker; US CIP; EU AMLD; sanctions lists (OFAC, UN, EU, UK HMT).
- Regions: R-IN KRA + in-person verification; R-US FINRA 2090/2111, Reg BI Form CRS; R-EU MiFID appropriateness; R-UK FCA appropriateness for complex products.
- Products: Alloy, Sumsub, Signzy (IN) for KYC flows - from memory - verify.

**16. Broker Client Service Desk Agent**
- Answers client questions (statement, margin, corporate action, tax P&L, payout status) from the broker's own data and drafts replies.
- Hires: broker, exchange member.
- Jobs: classify tickets; answer from account data; draft replies; escalate grievances; track SLAs vs regulator timelines; collect evidence; monthly complaint stats for disclosure.
- Tier B (staff send).
- Data/rails: broker back-office (e.g. Omnesys/63 Moons, Broadridge BPS, FIS), ticketing.
- Regions: R-IN brokers must publish monthly complaint data (e.g. https://www.angelone.in/wp-content/uploads/pdfs/Investor-Complaints-Data-Aug-2025.pdf, via search).
- Products: generic CX AI (Intercom/Zendesk) not markets-aware.

**17. Margin & Risk Notice Preparer**
- Watches client margin utilisation and prepares margin-call notices, shortfall explanations and square-off warnings for the risk desk.
- Hires: broker, FCM, prime broker.
- Jobs: compute margin shortfall from exchange files; pledged collateral haircut view; prepare client notice drafts; peak-margin evidence; ageing of debit balances; reasons log for each square-off; daily risk summary for RMS head.
- Tier B. Margin calls, limits, liquidations = risk manager.
- Data/rails: exchange/clearing margin files (SPAN, NSE VaR files, CME SPAN 2), RMS systems, pledge (MTF) records.
- Regions: R-IN peak margin rules; R-US Reg T + FINRA 4210; R-EU EMIR for OTC.
- Products: vendor RMS systems; AI notice drafting rare.

**18. Best-Execution & TCA Report Preparer**
- Prepares best-execution monitoring and transaction-cost analysis reports for the best-ex committee.
- Hires: broker, asset manager trading desk.
- Jobs: venue/broker statistics; slippage vs arrival/VWAP; order-routing review; Rule 606/605 report drafts (US); RTS 28-style annual reports where still required (check); exceptions list; committee pack narrative.
- Tier B.
- Data/rails: OMS/EMS fills, market data, FIX logs.
- Regions: R-US Rule 605/606; R-EU/UK MiFID best execution (RTS 28 removed - check).
- Products: Abel Noser, Virtu ITG TCA, BestX (from memory - verify).

**19. Broker Regulatory Reporting Preparer**
- Builds and checks the broker's recurring regulatory submissions so the compliance officer can file.
- Hires: broker, exchange member, FCM.
- Jobs: data pulls for daily/weekly/monthly reports; field validation; reconcile counts vs books; exceptions with root cause; calendar of due dates; prior-period comparison; draft explanations for regulator queries.
- Tier B. Filing = institution's officer.
- Data/rails: CAT (US), FOCUS reports, MiFIR transaction reports via ARM, SEBI/exchange reporting portals, CFTC large-trader.
- Regions: per R-codes.
- Products: Regnology, Kaizen, Bovill (from memory - verify).

**20. Marketing & Communications Compliance Reviewer**
- Reviews ads, social posts, app copy, research teasers and emails against financial-promotion rules before the principal approves.
- Hires: broker, fintech, asset manager, exchange.
- Jobs: flag performance claims, missing risk warnings, "guaranteed" language, cherry-picked returns; required disclaimers per region; finfluencer contract checks; archive & approval log; FINRA filing check list.
- Tier B (registered principal approves).
- Data/rails: draft content, rulebooks.
- Regions: R-US FINRA 2210 (FINRA 2026 report says GenAI implicates supervision, communications, recordkeeping, fair dealing rules - https://www.dlapiper.com/insights/publications/2025/12/finra-flags-generative-ai-risks-and-governance-expectations, via search); R-UK FCA financial promotions + finfluencer guidance; R-IN SEBI finfluencer restrictions (from memory - verify); R-EU ESMA marketing guidelines.
- Products: Saifr, Red Oak (from memory - verify).

**21. Licensing & Continuing-Education Tracker**
- Tracks every registered person's exams, licences, CE/CPD hours and renewal dates.
- Hires: broker, bank, sole registered rep.
- Jobs: register of reps and licence types; renewal alerts; study plans for SIE/Series 7/63/65, NISM modules, CISI, CSI; CE completion evidence; U4/U5-style change list.
- Tier A.
- Data/rails: FINRA CRD (read via firm), NISM portal, FCA certification regime records.
- Products: firm LMS tools; partial.

**22. Client Money & Asset Segregation Reconciliation Preparer**
- Prepares the daily client-money/asset reconciliations a broker must run and lists breaks for the CASS/compliance officer.
- Hires: broker, custodian, FCM.
- Jobs: reconcile client ledger vs bank and depository; segregation calculation; shortfall/excess explanation; aged breaks; attestation pack; regulator-format return draft.
- Tier B.
- Data/rails: bank statements (camt.053), depository holdings, back-office ledgers.
- Regions: R-US 15c3-3 reserve computation; R-UK CASS 6/7, CMAR; R-IN SEBI upfront collection + weekly client funds reporting (from memory - verify); R-ANZ ASIC client money rules.
- Products: Duco, SmartStream, Gresham (see role 53).

### C. Investment banking and capital markets (advisory, ECM, DCM)

**23. Pitchbook & Comps Analyst**
- Produces the first draft of pitch materials: company profile, trading comparables, precedent transactions, league tables.
- Hires: boutique banks, M&A advisers, corporate development, PE.
- Jobs: pull financials; normalise metrics; comps table with multiples; precedent deal list; football-field chart; market overview slides; banker-style formatting; source citations per number; refresh when markets move.
- Tier B. Banker owns and presents.
- Data/rails: filings (EDGAR, Companies House, MCA21, CNINFO), market data, paid databases (CapIQ, PitchBook, Refinitiv) via the firm's licence.
- Regions: data access differs; language of filings (Japanese/Chinese/Portuguese).
- Products: Rogo (Felix agent: models, IPO documents, decks; $160M raise at ~$2B valuation, Apr 2026 - https://www.beri.net/article/rogo-160m-series-d-investment-banking-ai-agents-2026, via search); Hebbia Matrix (https://www.hebbia.com/resources/hebbia-vs-rogo, via search).

**24. Financial Model Builder & Checker**
- Builds and audits DCF, LBO, merger/accretion-dilution and three-statement models; finds formula errors.
- Hires: bank, boutique, corporate finance team, CA/advisory firm, PE.
- Jobs: build model from filings; scenario switches; sensitivity tables; formula/link audit; circularity check; roll-forward to new quarter; reconcile to reported numbers; model book documentation.
- Tier B.
- Data/rails: Excel files, filings.
- Products: Rogo audits formula errors and rolls forward 40-tab models (https://www.hebbia.com/resources/rogo-competitors, via search); Macabacus (from memory).

**25. M&A Due-Diligence Data-Room Assistant**
- Organises the data room, redacts personal data, tracks buyer Q&A and summarises contracts.
- Hires: sell-side adviser, law firm, corporate, PE buyer.
- Jobs: index and file naming; PII redaction; contract summaries (change of control, assignment, exclusivity); Q&A log with owner and status; red-flag report; disclosure schedule draft; access-log review.
- Tier B (counsel/banker sign off).
- Data/rails: VDR (Datasite, Intralinks, Ansarada) APIs.
- Products: Datasite Redaction AI 120+ PII types, 100M+ redactions in a year (vendor claim, https://www.datasite.com/en/resources/ai-at-datasite, via search); Intralinks AI (https://www.intralinks.com/guides/virtual-data-room-in-ma).

**26. Target / Buyer Screener & Teaser-CIM Drafter**
- Builds buyer or target long-lists with a reason for each and drafts the teaser and CIM from management material.
- Hires: boutique bank, SME business broker, corporate development.
- Jobs: screen by sector/size/geography; strategic-fit rationale; ownership and contact research; teaser draft (anonymised); CIM sections; NDA tracker; outreach log.
- Tier B.
- Data/rails: company registries, news, deal databases.
- Regions: SME M&A brokers worldwide; R-AF/R-LATAM thin data.
- Products: Grata, Sourcescrub (from memory - verify).

**27. IPO Readiness & Offer-Document Drafting Assistant**
- Helps issuers and their bankers/lawyers prepare the DRHP/prospectus/S-1: section drafts from company material, consistency checks, regulator comment tracker.
- Hires: issuer CFO, merchant banker / book-running lead manager, law firm.
- Jobs: readiness gap list (governance, audited periods, related parties); draft business/industry/MD&A sections from sources; cross-document consistency (numbers match financials); risk-factor library; regulator observation-letter tracker; red-herring changes log; post-issue reporting calendar.
- Tier B. Lead manager due diligence certificate and directors' responsibility = human (tier C signatures).
- Data/rails: audited financials, board minutes, regulator filing portals (SEBI, SEC EDGAR, HKEX e-submission).
- Regions: R-IN SEBI ICDR; R-US Securities Act + SEC review; R-EU Prospectus Regulation/Listing Act; R-CNHK CSRC filing + HKEX; R-GCC Tadawul main/Nomu.
- Products: Rogo drafts IPO documents (https://kleinerperkins.com/perspectives/rogo-the-ai-platform-for-global-finance, via search).

**28. Debt Capital Markets Deal Assistant**
- Supports bond and loan deals: pricing comps, term-sheet comparison, covenant extraction, investor feedback logs.
- Hires: bank DCM, corporate treasury issuer, NBFC issuer.
- Jobs: new-issue concession analysis vs secondary curve; comparable bonds table; term-sheet vs indenture diff; covenant summary; rating-agency pack draft; investor order-book log (read only); post-deal tombstone.
- Tier B.
- Data/rails: bond data (Bloomberg/Refinitiv via licence, exchange debt segments, FINRA TRACE), indentures.
- Regions: R-IN EBP (electronic book platform) for private placements; R-US 144A/Reg S; R-GCC sukuk structures; R-LATAM debentures (Brazil).
- Products: Bloomberg, DealVector (from memory - verify).

**29. Valuation Workpaper Preparer**
- Prepares valuation workpapers (DCF, multiples, option pricing) and the evidence file for the registered valuer/adviser who signs.
- Hires: advisory firm, registered valuer, CA firm, startup (ESOP/409A-like valuations).
- Jobs: assemble inputs; WACC build with sources; method comparison; sensitivity; draft report sections; regulatory-format checklist.
- Tier B. Valuation opinion signed by registered valuer (C).
- Regions: R-IN IBBI registered valuers; R-US 409A, ASC 820; R-UK/EU IVS.

**30. Deal Closing Checklist Keeper**
- Tracks every condition precedent, signature, regulatory approval and funds-flow item to closing.
- Hires: law firm, bank, corporate.
- Jobs: CP checklist from SPA/credit agreement; owner and due dates; approval tracker (competition, FDI, regulator); signature page collation; funds-flow memo draft for human approval; post-closing obligations calendar.
- Tier A.
- Products: Litera Transact, DealCloud (from memory - verify).

**31. ECM Investor Targeting & Bookbuilding Support**
- Prepares investor target lists and summarises demand for the syndicate desk.
- Hires: bank ECM, issuer IR.
- Jobs: shareholder ID from filings (13F, register analysis); investor-fit scoring; roadshow schedule; feedback notes; book summary (read-only from the bookrunner system); allocation rationale draft for the syndicate head.
- Tier B. Allocation = syndicate desk (C).
- Data/rails: 13F/13D, shareholder registers, CRM.
- Products: Ipreo/S&P (from memory), Q4.

**32. Equity Research Associate (sell-side support)**
- Drafts earnings previews/reviews, updates models after results, maintains coverage files for a licensed analyst.
- Hires: broker research desk, independent research house, registered research analyst.
- Jobs: earnings preview; post-results note draft; model update; channel-check summaries; estimates vs consensus; chart pack; disclosure block checklist; publishing calendar.
- Tier B. The report is published under the registered analyst with certification (C).
- Data/rails: filings, transcripts, market data.
- Regions: R-US FINRA 2241/Reg AC; R-EU MiFID research unbundling (partly relaxed - check); R-IN SEBI Research Analyst Regulations; R-UK.
- Products: AlphaSense SuperAnalyst (June 2026, https://www.globenewswire.com/de/news-release/2026/06/03/3305976/0/en/alphasense-introduces-superanalyst-the-always-on-ai-agent-for-decision-grade-intelligence.html, via search); Bloomberg AI earnings-call summaries (https://www.bloomberg.com/company/press/bloomberg-launches-ai-powered-earnings-call-summaries, via search).

**33. Credit Research Assistant**
- Reads issuer financials, indentures and rating reports; builds credit metrics and covenant headroom for a credit analyst.
- Hires: bank credit desk, bond fund, NBFC treasury, independent research.
- Jobs: leverage/coverage metrics; covenant headroom; maturity wall; peer spread comparison; rating-action history; event-risk alerts; credit memo draft.
- Tier B.
- Products: Moody's Research Assistant (claimed up to 80% time saved on data collection, https://www.moodys.com/web/en/us/creditview/blog/research-assistant-new-era.html, via search); S&P Kensho (from memory - verify).

**34. Earnings & Filings Summariser (buy-side / anyone)**
- Summarises earnings calls, filings and exchange announcements for her watch list with links to the source line.
- Hires: consumer, sole trader, advisers, small funds, corporate IR (peers).
- Jobs: transcript summary; guidance changes; Q&A themes; KPI tables; diff vs last quarter; alert on new filing; source-line citations.
- Tier A.
- Products: AlphaSense Smart Summaries (https://www.alpha-sense.com/blog/product/smart-summaries-earnings-analysis/, via search), Quartr, Bloomberg.

**35. Research & Deal Compliance (MNPI, wall-crossing, restricted list) Keeper**
- Maintains wall-crossing logs, insider lists, restricted/watch lists and research-quiet-period calendars for control room staff.
- Hires: bank, broker, listed issuer.
- Jobs: wall-crossing record from emails/notes; insider list in MAR template; restricted list change proposals; quiet-period calendar; conflict-check summaries; audit trail export.
- Tier B. Control room decides.
- Regions: R-EU/R-UK MAR insider lists; R-IN SEBI PIT Regulations (structured digital database); R-US information barriers.
- Products: StarCompliance, ComplySci (from memory - verify).

### D. Sales, trading and market-making support (no live trading)

**36. Market Colour & Morning Note Writer**
- Drafts the desk's morning note, client market-colour updates and end-of-day wraps from data and the desk's own views.
- Hires: broker sales desk, independent dealer, wealth team.
- Jobs: overnight moves; economic calendar; flows summary; desk axes (as given); compliance disclaimer; client-segment versions; translations.
- Tier B (sales/trader approves).
- Data/rails: market data, news wires, desk inputs.

**37. FX Desk & Client Hedge Assistant (bank/dealer side)**
- Prices indicative forwards/swaps, compares quotes, drafts client hedge proposals and documents rationale.
- Hires: bank FX sales, money changer/remittance company, corporate FX broker.
- Jobs: forward points and outright calculation; quote comparison across venues; client exposure summary; hedge proposal draft (ratio, tenors, instruments); suitability/appropriateness check for derivatives; trade-recap draft; FX Global Code disclosures.
- Tier B. Quote and deal = dealer (C).
- Regions: R-IN RBI hedging directions (users must have exposure; from memory - verify); R-US Dodd-Frank swap rules; R-EU EMIR; R-AF Nigeria/Kenya FX liquidity constraints; R-LATAM Brazil BCB FX rules.
- Products: 360T, Refinitiv FXall (execution), Kantox (corporate).

**38. Rates & Fixed-Income Analytics Assistant**
- Builds yield curves, computes DV01/duration/convexity, carry and roll, and prepares relative-value notes.
- Hires: bank rates desk, bond dealer, primary dealer, NBFC treasury, pension fund.
- Jobs: curve build from quotes; bond analytics; swap spread; auction analysis; portfolio PV01 report; scenario P&L; RV note draft.
- Tier B.
- Data/rails: CCIL/NDS-OM (IN), TRACE, Bloomberg via licence, central-bank auction results.

**39. Commodities Market Brief & Hedge Calculator**
- Summarises physical and futures markets and calculates hedge sizes for commodity traders, processors and farmers' organisations.
- Hires: commodity trader, processor, FPO/co-op, SME importer.
- Jobs: daily brief (prices, basis, weather, inventories); hedge ratio and contract count; margin needs; delivery calendar; basis risk explainer; position limits check.
- Tier B (A for education use).
- Data/rails: CME, ICE, MCX/NCDEX, LME, SHFE/DCE, USDA/IGC reports.
- Regions: R-IN MCX/NCDEX FPO hedging; R-LATAM B3 agri futures; R-AF ESX/ACE (Ethiopia/Malawi, from memory - verify).

**40. Derivatives Documentation & Confirmation Drafter**
- Drafts ISDA/CSA schedules from term sheets, compares negotiated terms to the firm's standard, and drafts trade confirmations for review.
- Hires: bank, dealer, corporate treasury, fund.
- Jobs: term-sheet to confirmation; ISDA schedule elections summary; CSA terms (thresholds, MTA, eligible collateral) extraction; deviation report vs playbook; negotiation tracker; CDM (ISDA Common Domain Model) mapping.
- Tier B. Signing = authorised signatories (C).
- Products: ISDA Create, Linklaters/Clause (from memory - verify).

**41. Quant / Systematic Strategy Research Assistant**
- Writes and documents backtests, checks for lookahead and overfitting, and prepares strategy papers for the PM or risk committee.
- Hires: prop shop, hedge fund, broker algo team, sophisticated retail.
- Jobs: data cleaning; backtest code; transaction-cost assumptions; walk-forward tests; overfitting checks; strategy documentation; model-risk pack.
- Tier B (A for retail paper research). No live orders.
- Regions: R-IN SEBI framework for retail algo/API trading requires broker registration of algos (from memory - verify).

**42. Algo Controls & Kill-Switch Evidence Preparer**
- Prepares the annual algorithmic-trading self-assessment and evidence of pre-trade controls, testing and kill-switch drills.
- Hires: broker, HFT/prop firm, exchange member.
- Jobs: inventory of algorithms; control parameter register (price collars, max order size, credit limits); test evidence collation; incident log; self-assessment draft; regulator questionnaire answers.
- Tier B. Kill-switch use and sign-off = human.
- Regions: R-EU/R-UK MiFID II Article 17 + RTS 6; R-US SEC 15c3-5 market access rule; R-IN SEBI algo approvals; R-SG/HK guidelines.

**43. Market-Making & Liquidity Obligations Reporter**
- Measures quoting obligations (spread, presence, size), inventory and hedging and prepares reports for the market-making head and exchange.
- Hires: designated market maker, liquidity provider, exchange (monitoring side).
- Jobs: obligation compliance stats; inventory ageing; P&L attribution (spread vs inventory); exchange rebate reconciliation; breach explanations.
- Tier B.

**44. Pre-Trade Compliance Rule Checker**
- Checks a proposed order or portfolio change against restricted lists, mandate limits, position limits and short-sale rules before a human sends it.
- Hires: broker, asset manager, family office.
- Jobs: restricted/watch-list match; investment mandate limits; exposure/position limits; short-sale locate check; concentration; documented override reasons.
- Tier B.
- Regions: R-US Reg SHO locates; R-EU SSR; R-IN position limits.

### E. Surveillance and market conduct

**45. Trade Surveillance Alert Triage Analyst**
- Investigates trade-surveillance alerts (spoofing, layering, wash trades, front running, marking the close) and drafts a disposition for the analyst.
- Hires: broker, bank, exchange, regulator.
- Jobs: pull orders/trades around the alert; reconstruct timeline; related accounts; news/announcement overlay; false-positive reasoning; disposition draft; escalation case file; QA sampling stats.
- Tier B. Close/escalate decisions human.
- Products: SteelEye Compliance CoPilot on trade alerts, claims up to 90% faster investigation (https://www.crowdfundinsider.com/2024/09/230273-regtech-steeleye-introduces-compliance-copilot-tool-across-trade-surveillance, via search); Nasdaq added GenAI to Market Surveillance (https://www.nasdaq.com/articles/tech-tuesday-integrating-gen-ai-surveillance, via search).

**46. Communications Surveillance Reviewer**
- Reviews flagged chats, emails and voice transcripts for collusion, MNPI leaks, off-channel invites and mis-selling and drafts dispositions.
- Hires: bank, broker, asset manager.
- Jobs: transcript summary in English from any language; risk tagging; context threads; off-channel indicators; disposition draft; lexicon tuning suggestions.
- Tier B.
- Regions: R-US SEC/CFTC off-channel recordkeeping fines (from memory - verify); R-UK MiFID taping.
- Products: SteelEye (in production since Nov 2023, https://a-teaminsight.com/blog/steeleye-integrates-chatgpt-into-compliance-platform-enhancing-market-surveillance-capabilities/), Behavox, Global Relay (from memory - verify).

**47. Personal Account Dealing & Insider Monitor**
- Pre-clears and monitors employees' personal trades against restricted lists and holding periods; tracks insider trading windows at listed issuers.
- Hires: bank, broker, listed company secretary.
- Jobs: pre-clearance check; holding-period watch; broker statement reconciliation; trading-window calendar; designated-person declarations; violation report draft.
- Tier B.
- Regions: R-IN SEBI PIT; R-EU MAR Art. 19 PDMR notifications; R-US 10b5-1 plans.

**48. Suspicious Transaction/Order Report (STOR/SAR) Case Preparer**
- Assembles evidence and drafts the narrative of a suspicious order/transaction report for the MLRO/compliance officer.
- Hires: broker, bank, exchange member.
- Jobs: facts timeline; who/what/when/why suspicious; supporting data tables; regulator template; deadline tracker; record retention.
- Tier B. Filing decision = MLRO (C).
- Regions: R-EU/UK STOR "without delay"; R-US FinCEN SAR 30 days (from memory - verify); R-IN FIU-IND STR.

### F. Middle and back office (post-trade)

**49. Trade Capture & Booking Checker**
- Compares what was traded (chat, voice, FIX) with what was booked and flags wrong price, quantity, account, counterparty or settlement date.
- Hires: bank, broker, asset manager.
- Jobs: parse trade recaps; match to booked trades; flag discrepancies; late-booking report; amendments log with reason; daily P&L-impact list.
- Tier B (trade support fixes).
- Data/rails: OMS/blotters, FIX logs, chat recaps.

**50. Confirmation & Affirmation Chaser (T+1)**
- Tracks unaffirmed/unmatched trades before cut-off and drafts chasers to counterparties and custodians.
- Hires: broker, asset manager, custodian.
- Jobs: exception list vs affirmation deadline; root-cause (SSI mismatch, allocation late); chaser emails; daily match-rate dashboard; recurring-counterparty issues.
- Tier B. Affirming is the firm's act (C).
- Evidence: US industry 9 PM affirmation reached ~94.5-94.8% after T+1, from 88.39% before (DTCC data via search https://www.dtcc.com/equity-trade-volume-insights; the page 404'd when opened, number via search summary - verify); EU same-day match rate 93.4% in Q1 2025 and manual matching raises errors (https://www.dtcc.com/dtcc-connection/articles/2025/july/18/same-day-matching-rates-a-crucial-indicator-in-run-up-to-t1-in-europe, via search).
- Regions: R-US CTM; R-EU/UK T+1 on 11 Oct 2027 with ESMA requiring settlement instructions by 23:59 CET trade date where feasible (https://www.esma.europa.eu/sites/default/files/2026-07/ESMA74-2119945926-3773_T_1_statement.pdf and DTCC comparison https://www.dtcc.com/dtcc-connection/articles/2025/august/06/navigating-t1-in-europe-comparing-uk-eu-roadmaps, via search).

**51. Settlement Fails & Penalties Manager**
- Predicts and works settlement fails, reconciles CSDR cash penalties and drafts buy-in/claim correspondence.
- Hires: broker, custodian, asset manager, bank.
- Jobs: pending-settlement watch; fail reason codes; inventory/funding shortfall alert to treasury; penalty reconciliation vs CSD reports; recharge to responsible party; counterparty fail league table; buy-in notice drafts.
- Tier B. Release/hold of instructions = operations staff.
- Evidence: NSCC fail rate ~2.1% and DTC ~3.0% (April 2026, via search, verify); July 2024 CNS fail 2.12% and DTC non-CNS 3.31% (https://www.sifma.org/news/press-releases/sifma-ici-and-dtcc-release-t1-after-action-report-industry-coordination-led-to-successful-transition-reducing-risk-and-costs-in-the-system, via search).
- Regions: R-EU CSDR penalties (EU Commission may temporarily suspend under T+1 recital); R-UK no equivalent penalty regime (via DTCC comparison above).

**52. SSI & Reference-Data Steward**
- Keeps settlement instructions, counterparty static and security reference data clean and evidence-checked.
- Hires: bank, broker, custodian, asset manager.
- Jobs: SSI change requests with call-back evidence checklist (fraud control); compare against ALERT/DTCC SSI database; LEI validity (GLEIF); ISIN/CFI/FISN checks; stale-record report; four-eyes change log.
- Tier B. Approval of SSI change = ops supervisor (fraud-critical).
- Data/rails: DTCC ALERT, Swift SSI, GLEIF API, ANNA.

**53. Reconciliation Break Investigator**
- Explains cash, position, nostro and trade reconciliation breaks and proposes the fix for operations to apply.
- Hires: bank, broker, custodian, fund administrator, corporate treasury.
- Jobs: classify breaks (timing, reference data, booking, pricing); match across MT/ISO messages (MT940/950, camt.053/054, MT535/semt.002); aged-break reports; root-cause trends; journal-adjustment proposals; control evidence.
- Tier B.
- Products: Duco agentic AI trials cut manual post-trade reconciliation work by an average 76% across 12 institutions (vendor-reported, https://ibsintelligence.com/ibsi-news/duco-clients-cut-reconciliation-workload-by-76-using-agentic-ai/, via search); SmartStream, Gresham.

**54. Corporate Actions Analyst (institutional)**
- Captures events from multiple sources into a golden record, tracks elections and deadlines, calculates entitlements and checks payments.
- Hires: custodian, broker, asset manager, fund administrator.
- Jobs: scrub announcements from vendors/CSDs; resolve source conflicts; notify clients; collect elections; deadline ladder; entitlement calculation; claims on missed income; payment reconciliation.
- Tier B. Election instruction submission = ops.
- Evidence: corporate action processing ~$58bn/yr cost (DTCC, opened above); STP rates 50-70% (https://www.dtcc.com/insights/2024/survey-reveals-opportunities-for-asset-servicing-automation-across-the-industry, via search); error rates up to 5%, ~$5.2bn a year extra cost (https://thevalueexchange.foleon.com/2025/corporate-actions-a-team-sport/the-true-scale-of-the-opportunity, via search).
- Data/rails: ISO 15022/20022 (MT564/566, seev.031), DTCC, Euroclear, Clearstream, NSDL/CDSL.

**55. Withholding-Tax Reclaim & Relief Preparer**
- Prepares relief-at-source and reclaim files on dividends/interest for custodians and investors.
- Hires: custodian, asset manager, family office, high-net-worth consumer.
- Jobs: eligibility by treaty; residence certificates checklist; reclaim forms per market; deadline (statute of limitations) tracker; reclaim status chase; reconcile refunds.
- Tier B.
- Regions: R-EU FASTER directive (digital residence certificates, relief at source - from memory, verify dates); country forms (Germany, Switzerland, France); R-US W-8BEN/QI; R-IN TRC + Form 10F.
- Products: Goal Group, WTax (from memory - verify).

**56. Collateral & Margin Call Analyst**
- Calculates daily variation/initial margin, prepares calls and dispute investigations, and suggests cheapest-to-deliver collateral.
- Hires: bank, dealer, buy-side fund, corporate with derivatives, NBFC.
- Jobs: exposure vs CSA terms; call/return draft; dispute root-cause (trade population, valuation, MTA); eligible-collateral & haircut check; optimisation suggestion; SIMM/IM report; triparty schedule review.
- Tier B. Issuing/agreeing a call and moving collateral = human.
- Products: Cassini pre/post-trade margin analytics (https://www.risk.net/regulation/7264226/how-pre-trade-im-calculation-can-optimise-and-reduce-collateral-drag, via search), OpenGamma, AcadiaSoft (from memory - verify).

**57. Securities Lending & Recall Tracker**
- Tracks loans, recalls around votes/corporate actions, fee accruals and rebate reconciliation.
- Hires: custodian/agent lender, fund, broker.
- Jobs: on-loan positions vs holdings; recall-before-record-date alerts; fee accrual check; collateral adequacy; SFTR reporting fields; billing reconciliation.
- Tier B.
- Regions: R-EU SFTR; R-US SEC 10c-1a reporting (from memory - verify); R-IN SLB segment.

**58. Custody Client Reporting & Proxy Operations Assistant**
- Produces custody statements, answers custody client queries and runs proxy-voting operations.
- Hires: custodian, sub-custodian, CSD participant.
- Jobs: statement packs; holdings certificates; proxy distribution and vote instruction tracking (SRD II); market-practice notes per country; query answers.
- Tier B.
- Regions: R-EU Shareholder Rights Directive II.

**59. Price & Independent Price Verification (IPV) Assistant**
- Checks marks against independent sources, flags stale or illiquid prices, and drafts IPV and fair-value hierarchy notes for product control.
- Hires: bank product control, fund administrator, NBFC treasury.
- Jobs: source comparison; tolerance breaches; stale price list; Level 1/2/3 classification draft; valuation adjustments workpaper; month-end IPV pack.
- Tier B.

**60. Exchange, Clearing & Broker Fee Invoice Reconciler**
- Reconciles invoices from exchanges, CCPs, CSDs, data vendors and executing brokers against activity.
- Hires: broker, asset manager, corporate treasury.
- Jobs: recompute fees from tariffs × volumes; flag over-billing; accrual entries; vendor-licence usage; dispute drafts.
- Tier A.

**61. Regulatory Trade-Reporting Data-Quality Analyst**
- Checks derivatives and transaction reports for completeness and accuracy and fixes rejections before the reporting officer resubmits.
- Hires: bank, broker, fund, corporate (EMIR NFCs).
- Jobs: rejection triage; field validation (UTI, UPI, LEI, ISIN); pairing/matching breaks; back-reporting list; regulator data-quality reports; controls evidence.
- Tier B.
- Regions: R-EU EMIR Refit, MiFIR, SFTR; R-UK equivalents; R-US CFTC Part 43/45, CAT; R-SG/HK/AU/JP OTC derivatives reporting; R-IN CCIL trade repository.

**62. Payment & ISO 20022 Message Exception Analyst**
- Repairs failed or rejected Swift/ISO 20022 messages (missing structured address, wrong BIC/IBAN, purpose codes) and drafts investigations.
- Hires: bank operations, corporate treasury, payment service provider, broker cash management.
- Jobs: decode reject reasons; propose repaired fields; structured-address conversion; investigation (camt.110/111) drafts; return/recall tracking; purpose-code mapping per country.
- Tier B. Release of repaired payment = authorised staff.
- Evidence: CBPR+ coexistence ended Nov 2025; unstructured addresses to be rejected after Nov 2026 window, extension possible (https://www.swift.com/insights/news/iso-20022-bytes-payments-journey-continues, via search).
- Regions: R-IN purpose codes for FX; R-GCC/R-AF correspondent banking constraints.

### G. Market infrastructure (exchanges, CCPs, CSDs, registrars, index providers)

**63. Listing Compliance & Issuer Disclosure Checker (exchange/regulator side)**
- Reviews issuer filings for completeness and timeliness against listing rules and drafts queries to issuers for exchange staff.
- Hires: exchange, regulator, listed issuer (self-check).
- Jobs: filing completeness check; late-filing list; price-sensitive announcement vs price-move check; financial result format validation (XBRL); query letter draft; penalty calculation per rulebook.
- Tier B. Penalty/suspension = exchange (C).
- Regions: R-IN SEBI LODR + exchange SOP fines; R-US Nasdaq/NYSE listing standards; R-EU/UK; R-AF NGX/NSE Kenya; R-GCC Tadawul.

**64. Exchange & Clearing Member Help Desk Agent**
- Answers members' and vendors' rulebook, circular, fee and technical-spec questions from the exchange's own documents.
- Hires: exchange, CCP, CSD.
- Jobs: circular search with citations; spec questions (FIX/ITCH, file formats); certification test scheduling; change-calendar reminders; ticket triage.
- Tier A.
- Regions: ASX CHESS replacement documentation and milestone changes (https://www.asx.com.au/content/dam/asx/markets/clearing-and-settlement-services/technical-committee/2026/chess-replacement-technical-committee-3-september-2026-presentation.pdf, via search).

**65. Clearing Risk & Default-Management Paper Preparer**
- Prepares margin model back-testing, stress-test, concentration and default-fire-drill papers for the CCP risk committee.
- Hires: CCP, clearing broker.
- Jobs: back-testing breach analysis; stress scenarios results summary; member concentration report; default-fund sizing note draft; fire-drill evidence pack; regulator (PFMI) self-assessment draft.
- Tier B. Margin parameters and default declaration = CCP (C).
- Regions: CPMI-IOSCO PFMI globally; R-EU EMIR CCP; R-US CFTC DCO/SEC CA.

**66. Depository Participant Operations Assistant**
- Handles demat/remat requests, pledges, transmissions, freezes on court order (prepared, not executed), and DP audit checklists.
- Hires: depository participant (bank/broker), registrar (RTA).
- Jobs: request validation checklist; signature/document mismatch flags; pledge/margin pledge status; transmission packs; DP internal-audit evidence; investor charter disclosures.
- Tier B.
- Regions: R-IN NSDL/CDSL, RTAs; R-ANZ CHESS sponsored holdings; R-AF CSCS/CDSC/Strate.

**67. Index Methodology & Rebalance Analyst**
- Applies index rules to compute rebalance changes, drafts consultations and change notices.
- Hires: index provider, ETF issuer, exchange.
- Jobs: eligibility screens; weight calculation; capping; turnover estimate; corporate-action adjustments; change-notice draft; methodology consistency checks.
- Tier B. Index committee decides.
- Regions: EU Benchmarks Regulation administrators; R-IN SEBI index provider regulation (from memory - verify).

### H. Issuers: investor relations, company secretary, equity plans

**68. Investor Relations Associate**
- Prepares earnings materials, likely analyst questions, peer-transcript summaries, shareholder analysis and IR website updates.
- Hires: listed company, pre-IPO company, IR agency.
- Jobs: Q&A prep from peers and past calls; script draft; consensus vs results bridge; shareholder ID and targeting; investor meeting notes; perception study summary; IR site and filing calendar.
- Tier B. Spokespersons and disclosure committee approve.
- Products: Q4 Earnings Co-Pilot and IRO Agent (https://www.q4inc.com/platform/platform-features/Secure-AI-for-IR, via search), Nasdaq IR Insight (https://www.nasdaq.com/solutions/nasdaq-ir-insight, via search), Quartr.

**69. Continuous-Disclosure & Listing-Obligations Calendar Keeper**
- Tracks every disclosure deadline and drafts announcements for the company secretary/disclosure committee.
- Hires: listed issuer, company secretary firm, bond issuer.
- Jobs: obligations calendar (results, shareholding pattern, board meeting intimation, related-party disclosures); draft announcement from board decision; materiality test worksheet; XBRL filing prep; insider window open/close.
- Tier B. Filing = compliance officer (C).
- Regions: R-IN LODR timelines (e.g. 30-minute/24-hour disclosures - from memory, verify); R-US 8-K four business days; R-EU/UK MAR "as soon as possible"; R-ANZ ASX continuous disclosure; R-GCC Tadawul.

**70. Registrar & Shareholder Query Helper (issuer side)**
- Answers shareholder questions (dividends not received, address change, lost certificates) from register data and drafts replies.
- Hires: issuer, registrar/transfer agent.
- Jobs: query classification; status lookup; drafted replies; unclaimed dividend reminders campaign; KYC update drives; complaint stats.
- Tier A/B.

**71. Employee Equity Plan Assistant**
- Keeps ESOP/RSU registers, vesting schedules, exercise maths, tax withholding estimates and trading-window reminders.
- Hires: startup, listed company, employee (consumer view).
- Jobs: grant register; vesting calendar; exercise cost and tax estimate; cap-table impact; blackout-window reminders; exercise paperwork pack.
- Tier A (B for company payroll/tax filing).
- Regions: R-US ISO/NSO, 83(b); R-IN perquisite tax; R-UK EMI; R-ANZ ESS.
- Products: Carta, Ledgy, Qapita (from memory - verify).

### I. Corporate treasury (SME to multinational)

**72. Cash Positioning & Forecasting Analyst**
- Builds the daily cash position across banks and a 13-week / 12-month forecast, explains variances.
- Hires: SME, mid-market and large corporate, NGO, accounting firm.
- Jobs: pull balances and statements; categorise flows; forecast from AR/AP/payroll/tax; variance vs actual; scenario (delay of big receipt); minimum-balance alerts; board cash report.
- Tier B (A for owner-managed SMEs: still no money moved).
- Data/rails: bank APIs/open banking (UK/EU PSD2, India AA, Brazil Open Finance), camt.053/MT940, ERP.
- Evidence: 62% of AFP 2025 benchmarking respondents rank forecasting as their hardest task; 73% name cash forecasting the top priority (https://ctmfile.com/story/treasury-cash-forecasting-rising-expectations-growing-complexity-ais-promise, via search); forecasting called "difficult" rose to 53% in 2025 from 39% in 2018 (same).
- Products: HighRadius (claims 95% accuracy - vendor), Kyriba TAI agentic AI (late 2025) (https://www.kognitos.com/blog/top-ai-cash-flow-forecasting-tools-treasury-2026/, via search), Agicap (SME, from memory).

**73. FX Exposure & Hedge Proposal Preparer (corporate)**
- Maps her company's currency exposures and prepares a hedge proposal under the board's policy for the CFO/treasurer.
- Hires: exporter/importer SME, corporate.
- Jobs: exposure register from invoices/POs; netting; policy compliance (hedge ratio bands); instrument comparison (forward, option, natural hedge); cost of hedge; bank quote comparison (provided by her); hedge register and maturity calendar; MTM report.
- Tier B. Deal with bank = treasurer (C).
- Regions: R-IN RBI exposure requirement; R-LATAM BRL/MXN volatility; R-AF NGN/KES liquidity; R-GCC USD pegs (low need).
- Products: Kantox, Bound, MillTech (from memory - verify).

**74. Hedge Accounting Documentation Preparer**
- Writes hedge documentation and runs effectiveness tests for the accountant/auditor.
- Hires: corporate, bank, accounting firm.
- Jobs: designation memo; economic-relationship analysis; regression/dollar-offset tests; OCI/P&L entries draft; disclosure notes draft.
- Tier B (CFO/auditor).
- Regions: IFRS 9 (most), US ASC 815, Ind AS 109.

**75. Bank Account & Mandate Manager**
- Keeps the register of every bank account, signatory and mandate, and prepares bank KYC refresh packs.
- Hires: SME, corporate, NGO, family office.
- Jobs: account inventory; signatory matrix vs board resolutions; dormant-account list; KYC refresh documents; mandate change paperwork; eBAM data (ISO 20022 acmt) where supported.
- Tier A.

**76. Debt & Covenant Compliance Tracker**
- Tracks loans, bonds, repayment schedules and covenant tests; drafts compliance certificates.
- Hires: SME, corporate, NBFC, real-estate developer.
- Jobs: debt register; interest/repayment calendar; covenant calculations from financials; headroom forecast; compliance certificate draft; waiver request draft; rating-trigger watch.
- Tier B (CFO signs certificate).

**77. Short-Term Investment & Policy Checker**
- Compares deposit/MMF/T-bill options and checks proposed placements against the investment policy.
- Hires: corporate, NGO, SME, school/university.
- Jobs: yield comparison net of tax; counterparty limit check; rating requirement check; maturity ladder; policy breach report; board investment report.
- Tier B (treasurer places).
- Evidence: AFP 2026 liquidity survey trends (https://www.financialprofessionals.org/training-resources/resources/survey-research-economic-data/Details/liquidity-survey, via search).

**78. Intercompany Netting & In-House Bank Preparer**
- Prepares intercompany netting cycles, loans, interest calculations and transfer-pricing documentation inputs.
- Hires: multinational, group with subsidiaries.
- Jobs: netting proposal; intercompany loan schedule; interest at arm's-length rate; FX on intercompany; withholding tax flags; settlement instruction drafts (released by humans).
- Tier B.

**79. Bank Fee Analysis Assistant**
- Reads bank fee statements (camt.086 / BSB) and finds overcharges and savings.
- Hires: corporate, SME.
- Jobs: fee extraction; compare to price schedule; volume trends; RFP fee comparison; dispute drafts.
- Tier A.

**80. SME Mini-Treasurer**
- For small businesses with no treasurer: one weekly view of cash, FX exposure, loans and idle balances, with plain-English options.
- Hires: SME, sole trader.
- Jobs: weekly cash note; idle cash sweep options; import/export FX exposure; loan EMI calendar; overdraft usage; "what if a client pays late" scenario; questions to ask the bank.
- Tier A.

### J. Bank treasury and ALM

**81. ALM & IRRBB Analyst Assistant**
- Builds repricing gaps, NII/EVE sensitivity and behavioural assumption papers for the ALM team and ALCO.
- Hires: bank, cooperative bank, NBFC, microfinance lender, building society, credit union.
- Jobs: repricing/maturity gap; NII and EVE shocks (BCBS standard scenarios); deposit behavioural model back-test; prepayment analysis; limit breach report; assumption documentation; model-risk pack.
- Tier B. ALCO decides.
- Evidence of caution: UK Finance calls treasury ALM "par excellence a judgement function" (https://www.ukfinance.org.uk/news-and-insight/blog/ai-in-treasury-ultimate-test-whether-your-processes-work, via search); Bloomberg/Choudhry on agentic AI and ALCO (https://www.bloomberg.com/professional/insights/financial-services/how-are-bank-treasury-priorities-evolving, via search).
- Regions: BCBS IRRBB; R-IN RBI ALM guidelines (structural liquidity, IRS statements); R-US OCC/Fed; R-EU EBA IRRBB guidelines; R-UK PRA.
- Products: QRM, Moody's ALM, SAS ALM with GenAI (https://communities.sas.com/t5/SAS-Innovate-Presentations/Redefining-Risk-Analytics-Through-Generative-AI-The-SAS-ALM/ta-p/968576, via search), Oracle.

**82. Liquidity Regulatory Return Preparer (LCR/NSFR/ALMM)**
- Prepares liquidity returns and explains movements for the treasurer and finance.
- Hires: bank, NBFC, payment bank.
- Jobs: HQLA classification; outflow/inflow run-off rates; LCR/NSFR calculation; day-on-day movement explanation; intraday liquidity metrics; regulator return draft; contingency funding plan test evidence.
- Tier B. Filing = bank (C).
- Regions: BCBS globally; R-IN RBI LCR for banks and NBFC LCR (from memory - verify); R-US LCR/NSFR tailored; R-EU CRR.

**83. Funds Transfer Pricing (FTP) Analyst**
- Calculates FTP curves and charges/credits by product and prepares profitability reports.
- Hires: bank, NBFC.
- Jobs: curve build (cost of funds + liquidity premium); product-level charges; branch/business profitability; behavioural tenor assignments; FTP committee pack.
- Tier B.

**84. Bank Investment Book & Repo Desk Support**
- Supports the bank's securities portfolio and repo funding: holdings analytics, regulatory buckets, repo maturity ladder.
- Hires: bank, primary dealer, NBFC treasury.
- Jobs: HTM/AFS/HFT classification report; SLR/HQLA eligibility; repo/reverse repo ladder; collateral availability; MTM; limit monitoring; central-bank operation calendar.
- Tier B. Dealing = treasury dealer (C).
- Regions: R-IN SLR, CCIL tri-party repo, RBI LAF; R-US Fed facilities; R-EU ECB operations.

**85. Treasury Policy & ALCO Pack Writer**
- Drafts treasury/ALM policies, limit frameworks and the monthly ALCO pack narrative from data.
- Hires: bank, NBFC, insurer treasury, corporate treasury.
- Jobs: policy drafts vs regulator requirements; limit framework; ALCO slides and commentary; minutes draft and action tracker; annual policy review checklist.
- Tier B.

### K. Ratings and other market specialists

**86. Credit Rating Analyst Associate (agency side)**
- Assembles rating committee packages: financial spreads, peer comparisons, methodology scorecard draft, press-release draft.
- Hires: credit rating agency, SME rating agency.
- Jobs: data spreading; methodology factor scoring draft; peer table; surveillance alerts on rated entities; committee memo draft; rationale press-release draft; regulatory disclosure checks.
- Tier B. Rating decision = rating committee (C).
- Regions: R-US SEC NRSRO; R-EU ESMA CRA Regulation; R-IN SEBI CRA Regulations; R-JPKR, R-AF local agencies (GCR, Agusto).
- Products: Moody's Research Assistant (client-facing), internal tools.

**87. Rating & Credit-Trigger Watcher (issuers and investors)**
- Watches ratings of her issuers, counterparties, banks and herself and alerts on actions and contractual triggers.
- Hires: corporate treasury, fund, bank, NBFC issuer, NGO investing reserves.
- Jobs: track rating actions; outlook changes; map triggers in loan/ISDA/CSA documents; impact note; rating-agency meeting prep.
- Tier A.

**88. Sustainable-Bond Framework & Reporting Assistant**
- Drafts green/social/sustainability bond frameworks and allocation/impact reports; prepares material for the external reviewer.
- Hires: issuer, bank DCM, development finance institution, municipality.
- Jobs: framework draft aligned to ICMA principles; eligible-asset register; allocation report; impact metrics calculation with sources; SPO question list; EU GBS checklist.
- Tier B. Second-party opinion = external reviewer (C).
- Regions: ICMA principles global; EU Green Bond Standard; R-IN SEBI green debt framework; R-GCC sukuk; R-LATAM Brazil sovereign sustainable bonds (from memory - verify).

**89. Agricultural & SME Commodity Hedging Helper**
- For farmers' groups and small processors: explains futures/options hedging, computes hedge sizes and costs, and tracks deliveries.
- Hires: FPO/co-op, small processor, SME exporter, NGO programmes.
- Jobs: price-risk explainer; hedge size; margin and cash need; delivery/quality specs; record of hedges; simple P&L; government scheme notes.
- Tier A.
- Regions: R-IN NCDEX/MCX FPO programmes; R-LATAM B3; R-AF commodity exchanges (from memory - verify).

---

## 3. Pains with evidence (demand)

| Pain | Evidence | Source |
|---|---|---|
| Retail derivatives losses are massive and persistent | 93% of over 1 crore Indian individual F&O traders lost money FY22-24, >Rs 1.8 lakh crore; >75% kept trading | SEBI press release (opened) |
| CFD losses in Europe | Standard warning 74-89% of retail CFD accounts lose money | ESMA https://www.esma.europa.eu/node/84933 (via search) |
| Investors complain at record volume | SEC record 53,753 TCRs FY2025; OIEA closed 31,472 investor files | Troutman summary; sec.gov/data/investor-complaints-data (via search) |
| Complaints workload in India | SEBI disposes ~4,000-5,600 SCORES complaints a month | Business Standard (via search) |
| Corporate actions are expensive and manual | ~$58bn/yr cost; STP 50-70%; errors up to 5%, ~$5.2bn/yr | DTCC (opened), DTCC survey, ValueExchange (via search) |
| T+1 squeezes post-trade time | US affirmation ~94-95% by 9 PM; fail rates ~2-3%; EU/UK T+1 11 Oct 2027 | DTCC, SIFMA, ESMA (via search) |
| Reconciliation is labour-heavy | Duco trial: 76% average cut in manual reconciliation work (vendor) | IBS Intelligence (via search) |
| Cash forecasting is the hardest treasury task | 62% AFP 2025 respondents; "difficult" 53% in 2025 vs 39% in 2018 | CTMfile (via search) |
| Supervisors expect human oversight of agents | FINRA 2026 report: first discussion of AI agents; autonomy, scope, auditability risks | Debevoise, DLA Piper (via search) |
| Payment message migration breaks payments | Unstructured addresses rejected after the Nov 2026 window (possible extension) | Swift (via search) |
| Junior banker workload | Rogo and Hebbia growth and funding | Sacra, Kleiner Perkins, Beri (via search) |
| Low market participation in emerging markets | Nigeria SEC: under 4% invest (headline); Kenya added 49k accounts in 2025 | BusinessDay, Zawya (via search) |

---

## 4. Never an AI employee (tier C) in this segment

| Act | Why it stays with a human |
|---|---|
| Placing, modifying, cancelling or routing any order; quoting live as a market maker; algo execution | Market-access and conduct rules (SEC 15c3-5, MiFID Art. 17, SEBI) hold a registered person/firm accountable; also the hard limit "never place/cancel an order". Robinhood/Public now let agents trade - Hoola deliberately does not. |
| Affirming/confirming trades, releasing settlement instructions, buy-in execution | Binding acceptance of a trade and movement of securities/cash. |
| Moving cash or collateral; agreeing a margin call; executing FX/derivative hedges; placing deposits | Money moves only on the user's tap. |
| Approving client onboarding/KYC, setting margin, credit or trading limits, liquidating a client | Regulatory responsibility of the firm's compliance/risk officers. |
| Publishing research or a recommendation as a research analyst; personalised investment advice | Registration (FINRA/SEBI RA/IA, FCA) and analyst certification. |
| Issuing or changing a credit rating; second-party opinion; index committee decision | Rating committee / external reviewer accountability (NRSRO, CRA regs). |
| Signing a prospectus, due-diligence certificate, fairness opinion, valuation report, covenant certificate, hedge designation | Legal liability of directors, merchant bankers, registered valuers, CFOs, auditors. |
| Filing STOR/SAR/STR, regulatory returns, transaction reports or exchange disclosures as the institution | Only the obligated entity's officer may file. |
| Allocating IPO/bond orders; pricing an issue | Syndicate desk/issuer decision. |
| CCP default declaration, margin model parameter changes, exchange penalties, trading suspensions, delisting | Statutory powers of the infrastructure/regulator. |
| ALCO decisions: hedging the balance sheet, using liquidity buffers, setting FTP | Board-delegated decisions of the bank. |
| Approving SSI/bank detail changes | Fraud-critical four-eyes control. |
| Asking for or handling passwords, OTPs, PINs, card numbers, broker login credentials | Hard limit; also broker API keys only through official OAuth, never pasted in chat. |

---

## 5. Top 10 roles to build first and why

1. **Portfolio Statement Reader (1)** - every investor in every country has scattered statements; read-only, tier A, CAS/AA in India and uploads elsewhere; the entry door for all other investor roles.
2. **Derivatives Reality-Check Coach (3)** - the strongest evidence of harm (SEBI 93%, ESMA 74-89%); pure calculation and explanation, tier A; regulators and brokers welcome it.
3. **Investment Scam & Registration Checker (8)** - public registers + warning lists, GenAI-fuelled fraud flagged by FINRA; protective, cheap, global.
4. **Capital Gains & Tax-Lot Calculator (5)** - painful annually, numbers checkable in code, sells to consumers and accounting firms in every tax system.
5. **Corporate Actions Tracker (6, retail) + Corporate Actions Analyst (54, institutional)** - $58bn industry cost; same engine (announcement parsing + entitlement maths) serves both a consumer and a custodian.
6. **Broker & Market Complaint Drafter (9)** - record complaint volumes; clear escalation ladders (SCORES/ODR, FINRA, FOS, AFCA, OBSI); tier A.
7. **Cash Positioning & Forecasting Analyst (72) with SME Mini-Treasurer (80)** - forecasting is the hardest treasury task for 62% of treasurers; open banking/AA rails exist; spans SME to corporate.
8. **Reconciliation Break Investigator (53)** - measurable (76% vendor-reported cut), rule-checkable, sells to banks/brokers/fund admins and corporate treasuries alike; T+1 pressure.
9. **Pitchbook & Comps Analyst + Financial Model Checker (23/24)** - proven willingness to pay (Rogo ~$2B valuation); boutiques and CA/advisory firms outside Wall Street are under-served.
10. **Investor Relations Associate + Continuous-Disclosure Calendar Keeper (68/69)** - every listed company (and fast-growing SME IPO markets in India, Gulf, Africa) has hard deadlines and penalties; drafting + calendar = tier B fit.

Runners-up: Confirmation & Affirmation Chaser (50) ahead of EU/UK T+1 in Oct 2027; FX Exposure & Hedge Proposal Preparer (73) for exporters in volatile-currency markets (LatAm, Africa, India); Trade Surveillance Alert Triage (45).

---

## 6. Sources

Opened directly:
- https://www.onetonline.org/link/summary/41-3031.00
- https://www.onetonline.org/link/summary/13-2051.00
- https://www.sebi.gov.in/media-and-notifications/press-releases/sep-2024/updated-sebi-study-reveals-93-of-individual-traders-incurred-losses-in-equity-fando-between-fy22-and-fy24-aggregate-losses-exceed-1-8-lakh-crores-over-three-years_86906.html
- https://www.dtcc.com/insights/2025/staggering-stats-understanding-inefficiencies-within-corporate-actions-processing
- https://www.dtcc.com/equity-trade-volume-insights (returned 404 when opened; figures come from search snippet - verify)

Read through search results (titles/snippets of real pages; verify before quoting):
- BLS OOH: https://www.bls.gov/ooh/sales/securities-commodities-and-financial-services-sales-agents.htm
- Rogo/Hebbia: https://sacra.com/research/rogo ; https://www.hebbia.com/resources/hebbia-vs-rogo ; https://www.hebbia.com/resources/rogo-competitors ; https://kleinerperkins.com/perspectives/rogo-the-ai-platform-for-global-finance ; https://www.beri.net/article/rogo-160m-series-d-investment-banking-ai-agents-2026
- DTCC/SIFMA T+1: https://www.sifma.org/news/press-releases/sifma-ici-and-dtcc-release-t1-after-action-report-industry-coordination-led-to-successful-transition-reducing-risk-and-costs-in-the-system ; https://www.dtcc.com/dtcc-connection/articles/2025/july/18/same-day-matching-rates-a-crucial-indicator-in-run-up-to-t1-in-europe ; https://www.dtcc.com/dtcc-connection/articles/2025/august/06/navigating-t1-in-europe-comparing-uk-eu-roadmaps
- ESMA T+1: https://www.esma.europa.eu/sites/default/files/2026-07/ESMA74-2119945926-3773_T_1_statement.pdf ; https://esma.europa.eu/press-news/esma-news/one-year-go-t1-settlement-regulatory-framework-complete-now-lets-make-it
- Treasury: https://www.kognitos.com/blog/top-ai-cash-flow-forecasting-tools-treasury-2026/ ; https://www.highradius.com/resources/Blog/agentic-ai-in-treasury-operations/ ; https://ctmfile.com/story/treasury-cash-forecasting-rising-expectations-growing-complexity-ais-promise ; https://www.pwc.com/us/en/services/consulting/business-transformation/library/2025-global-treasury-survey.html ; https://www.financialprofessionals.org/training-resources/resources/survey-research-economic-data/Details/liquidity-survey
- Surveillance: https://www.nasdaq.com/articles/tech-tuesday-integrating-gen-ai-surveillance ; https://www.crowdfundinsider.com/2024/09/230273-regtech-steeleye-introduces-compliance-copilot-tool-across-trade-surveillance ; https://a-teaminsight.com/blog/steeleye-integrates-chatgpt-into-compliance-platform-enhancing-market-surveillance-capabilities/
- SEBI SCORES: https://www.business-standard.com/markets/news/sebi-resolves-over-4k-investor-complaints-via-scores-platform-in-mar-2025-125041400786_1.html ; https://scores.sebi.gov.in/
- SEBI FY25 F&O: https://moneylife.in/article/91-percentage-of-retail-traders-lost-money-in-derivatives-losses-in-fo-surged-41-percentage-to-rs105-lakh-crore-in-fy25-sebi-study/77613.html
- FINRA 2026 report summaries: https://www.debevoise.com/insights/publications/2025/12/finras-2026-regulatory-oversight-report-continued ; https://www.dlapiper.com/insights/publications/2025/12/finra-flags-generative-ai-risks-and-governance-expectations ; primary PDF https://www.finra.org/sites/default/files/2025-12/2026-annual-regulatory-oversight-report.pdf (not opened)
- Corporate actions: https://www.dtcc.com/insights/2024/survey-reveals-opportunities-for-asset-servicing-automation-across-the-industry ; https://thevalueexchange.foleon.com/2025/corporate-actions-a-team-sport/the-true-scale-of-the-opportunity
- IR: https://www.q4inc.com/platform/platform-features/Secure-AI-for-IR ; https://www.nasdaq.com/solutions/nasdaq-ir-insight ; https://quartr.com/insights/investor-relations/streamlining-q-and-a-preparations-for-investor-relations-professionals
- Research: https://www.globenewswire.com/de/news-release/2026/06/03/3305976/0/en/alphasense-introduces-superanalyst-the-always-on-ai-agent-for-decision-grade-intelligence.html ; https://www.bloomberg.com/company/press/bloomberg-launches-ai-powered-earnings-call-summaries ; https://www.alpha-sense.com/blog/product/smart-summaries-earnings-analysis/
- Reconciliation: https://ibsintelligence.com/ibsi-news/duco-clients-cut-reconciliation-workload-by-76-using-agentic-ai/ ; https://a-teaminsight.com/blog/duco-maps-a-path-towards-agentic-post-trade-operations/
- ISO 20022: https://www.swift.com/standards/iso-20022/iso-20022-bytes/journey-continues ; https://www.swift.com/insights/news/iso-20022-bytes-payments-journey-continues
- M&A data rooms: https://www.datasite.com/en/resources/ai-at-datasite ; https://www.intralinks.com/guides/virtual-data-room-in-ma
- Margin: https://www.risk.net/regulation/7264226/how-pre-trade-im-calculation-can-optimise-and-reduce-collateral-drag ; https://www.marketsmedia.com/tradeweb-integrates-margin-optimisation-analytics
- ALM: https://www.ukfinance.org.uk/news-and-insight/blog/ai-in-treasury-ultimate-test-whether-your-processes-work ; https://www.bloomberg.com/professional/insights/financial-services/how-are-bank-treasury-priorities-evolving ; https://communities.sas.com/t5/SAS-Innovate-Presentations/Redefining-Risk-Analytics-Through-Generative-AI-The-SAS-ALM/ta-p/968576
- Ratings: https://www.moodys.com/web/en/us/creditview/blog/research-assistant-new-era.html
- Retail brokerage AI: https://robinhood.com/us/en/support/articles/robinhood-cortex ; https://axios.com/2025/11/17/ai-stock-market-public ; https://fortune.com/2026/09/29/robinhood-trading-agents-hood-openai-anthropic/
- ESMA CFD: https://www.esma.europa.eu/node/84933
- SEC FY2025: https://www.troutman.com/insights/sec-fy-2025-enforcement-results-reveal-changing-priorities-from-record-numbers-to-investor-protection/ ; https://sec.gov/data/investor-complaints-data
- ASX: https://www.asx.com.au/markets/clearing-and-settlement-services/chess-replacement ; https://www.waterstechnology.com/trading-tech/7951687/asx-chess-replacement-to-be-delivered-in-phases-with-clearing-first-in-2026
- Africa: https://www.zawya.com/en/economy/africa/kenya-nse-gets-49-363-new-share-accounts-as-ipo-season-kicks-off-with-sale-of-kpc-s17ab09e ; https://webiis08.mondaq.com/nigeria/economic-analysis/1734368/nigeria-capital-markets-highlights-of-the-key-activities-in-2025-and-outlook-for-2026 ; https://www.cma.or.ke/download/9/cm-soundness-report/6399/capital-markets-soundness-report-cmsr-quarter-4-fy-2025-2026-2.pdf

Gaps not verified (from memory - verify): ISCO/ESCO/UK SOC/ANZSCO code numbers; GCC, SE Asia, China/HK, Japan/Korea, Brazil/Mexico and Canada regulator details; FASTER dates; RBI hedging and LCR specifics; individual vendor names marked "from memory".
