# Segment 06: Risk, compliance, financial crime, regulatory reporting, internal audit and governance (worldwide)

Research date: 22 Nov 2026. Rules used for every role: the AI prepares, checks, explains, calculates, drafts, tracks and reminds. It never files a SAR/STR or regulatory return as the institution, never freezes or exits an account, never clears or confirms a sanctions hit, never approves or declines KYC, a loan or a claim, never signs an audit opinion, attestation or certification, and never asks for PIN, OTP, CVV, card numbers or passwords.

**Source marking.** "[opened]" means I opened the page or it was a search result I read. "[from memory - verify]" means I did not check it this session.

---

## 0. Key findings first (evidence of demand)

| Finding | Number | Source |
|---|---|---|
| Global cost of financial crime compliance | US$206.1 bn (2023 study); 2024 regional studies: US+Canada $61 bn, EMEA $85 bn, APAC $45 bn | LexisNexis Risk [opened] https://risk.lexisnexis.com/about-us/press-room/press-release/20230926-global-financial-crime-compliance-costs ; https://risk.lexisnexis.com/about-us/press-room/press-release/20240221-true-cost-of-compliance-us-ca ; https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20240306-true-cost-of-compliance-emea |
| False positives from transaction monitoring | About 70-95% of alerts are false positives; 2-10% of alerts become an STR | SWIFT Institute working paper [opened] https://swift.com/swift-resource/252235/download |
| US SAR volume | About 4.7 m SARs in FY2024 (about 12,870 a day); about 3.8 m original filings in calendar 2024 | FinCEN infographic [opened] https://www.fincen.gov/sites/default/files/shared/FinCEN-Infographic-Public-2025-508.pdf ; Thomson Reuters https://www.thomsonreuters.com/en-us/posts/corporates/sars-report-2024 ; FinCEN SAR stats https://fincen.gov/reports/sar-stats/sar-filings-industry |
| Time to write a SAR narrative | "Several hours per narrative" | Co-Investigator AI paper, arXiv 2509.08380 [opened] https://arxiv.org/abs/2509.08380 |
| Regulatory change workload | 38% of firms spend at least one full working day a week tracking regulatory change (Thomson Reuters, older data). CUBE 2025: 98% automate part of regulatory change management, and a change still takes more than a year to implement | https://www.familywealthreport.com/article.php/Compliance-Corner:-Regulatory-Change-Management-Costs-Seen-Rising-- ; https://www.thomsonreuters.com/en-us/posts/investigation-fraud-and-risk/2023-cost-of-compliance-report/ [opened as search results] |
| UK complaints | FOS received 305,726 new complaints in 2024/25, up 54% and the highest in six years | https://www.financial-ombudsman.org.uk/news/financial-ombudsman-service-receives-305000-complaints-2024-25 [opened] |
| US complaints | CFPB received about 3.19 m complaints in 2024 and about 6.64 m in 2025 | https://www.consumerfinance.gov/data-research/research-reports/2024-consumer-response-annual-report/ ; https://files.consumerfinance.gov/f/documents/cfpb_2025-cr-annual-report_2026-03.pdf [opened] |
| India complaints | RBI Integrated Ombudsman received 13,34,244 complaints in FY2024-25, up 13.55%. Banks were 81.5% of complaints at the ombudsman offices; loans and credit cards were the top categories | https://website.rbi.org.in/web/rbi/-/publications/annual-report-of-ombudsman-scheme-2024-25 [opened] |
| US model risk rules changed | SR 11-7 was **superseded on 17 Apr 2026** by interagency SR 26-2 / OCC Bulletin 2026-13, which is principles-based and materiality-focused, mostly relevant above $30 bn in assets, and also replaces SR 21-8 (BSA/AML models). Generative and agentic AI are reportedly out of formal scope "for now" | https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm [opened]; https://www.orrick.com/en/Insights/2026/04/Agencies-Overhaul-Model-Risk-Management-Guidance-for-Banks-Heres-What-Changed |
| EU AI Act high-risk dates | Digital Omnibus provisional deal of 7 May 2026 moves stand-alone Annex III high-risk systems, including credit scoring, to **2 Dec 2027**. Check formal Official Journal adoption | https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/ ; https://www.hoganlovells.com/en/publications/eu-legislators-agree-to-delay-for-highrisk-ai-rules [opened] |
| DORA live | Applied from 17 Jan 2025. First ICT third-party register of information had a reference date of 31 Mar 2025, reported to the ESAs by 30 Apr 2025, and is filed every year. The first critical ICT providers were designated in Nov 2025 | https://eba.europa.eu/activities/direct-supervision-and-oversight/digital-operational-resilience-act/preparation-dora-application ; https://www.cssf.lu/en/2025/04/guidance-for-correction-of-most-frequent-issues-identified-in-the-submitted-registers-of-information-under-dora/ [opened] |
| Investor money is flowing to compliance agents | Norm Ai (regulatory compliance agents for banks, asset managers and insurers) reportedly raised a $120 m Series C at a $1.2 bn valuation in July 2026. ValidMind (model risk documentation and validation) raised seed funding | https://enterprisedna.co/resources/news/norm-ai-120m-series-c-compliance-agents-enterprise-2026/ ; https://venturebeat.com/ai/ai-risk-management-startup-validmind-raises-8-1m-to-help-banks-comply-with-regulations [opened as search results] |

**What this means for Hoola.** The work in this segment is huge, repetitive, document-heavy and deadline-driven, so it suits AI. The final decision in it is legally reserved to named humans: the MLRO/BSA officer, the SMF (Senior Manager Function) holder, the board, the chief risk officer and the head of internal audit. The safe product shape is **"the analyst's first draft plus the evidence file"**, and a named human always signs. The second best fit is **small firms** (fintechs, NBFCs, money service businesses, brokers, crypto firms, credit unions, IFAs, CA firms advising them). They carry the same obligations as a bank with a compliance team of one, and no enterprise vendor serves them well.

## 1. Occupations scanned (taxonomies)

- **O\*NET / US BLS:** 13-1041.00 Compliance Officers. New O\*NET tasks include "Identify compliance issues that require follow-up or investigation", "Keep informed regarding pending industry changes", "Provide assistance to internal or external auditors in compliance reviews" and "Verify that all firm and regulatory policies and procedures have been documented, implemented, and communicated" [opened] https://www.onetonline.org/link/details/13-1041.00. Also scanned: 13-2099.04 Fraud Examiners, Investigators and Analysts; 13-2099.02 Risk Management Specialists; 13-2011 Accountants and Auditors (internal auditors); 13-2041 Credit Analysts; 13-2054 Financial Risk Specialists; 15-1212 Information Security Analysts; 11-3031.01 Treasurers and Controllers; 43-6011 Executive Secretaries (corporate secretarial) [from memory - verify codes].
- **ISCO-08:** 2411 Accountants (incl. internal auditor), 2413 Financial analysts, 2421 Management and organisation analysts (risk analyst), 2619 Legal professionals n.e.c. (compliance officer), 3359 Regulatory government associate professionals, 3343 Administrative and executive secretaries [from memory - verify].
- **ESCO:** "compliance officer", "anti-money laundering officer", "risk analyst", "credit risk analyst", "internal auditor", "fraud investigator", "data protection officer", "company secretary", "ICT risk manager" [from memory - verify].
- **UK SOC 2020:** 2421 Chartered and certified accountants, 2433 Actuaries, 3534 Finance and investment analysts, 3581 Inspectors of standards and regulations, 4214 Company secretaries and administrators [from memory - verify].
- **ANZSCO:** 224212 Compliance officer-type roles, 221214 Internal Auditor, 224711 Management Consultant (risk) [from memory - verify].
- **Bank org charts (Three Lines model, IIA 2020):** 1st line = business plus 1st line risk/controls ("1LoD control officers", KYC operations, fraud operations). 2nd line = Compliance (FCC, AML, sanctions, conduct, regulatory compliance, privacy), Risk (credit, market, liquidity/ALM, operational, model, technology/cyber, third-party, climate), regulatory reporting (often sits in Finance). 3rd line = Internal Audit. Plus Company Secretariat, Legal and Board.

---

## 2. AI-employee roles (numbered)

Shared rails for most roles: case and alert files (CSV/PDF exports from Actimize, SAS, Oracle FCCM, Fenergo, Hawk, Napier and similar), core banking statements, policy libraries, regulator websites and RSS feeds, document readers, and sanctions lists (OFAC SDN, UN Consolidated, EU FSF, UK OFSI, plus national lists from MAS, HKMA, India MHA/UNSC and others). I list only the extras per role.

Regional shorthand used below:
- **US:** FinCEN/BSA, OCC, Fed, FDIC, CFPB, SEC/FINRA, NYDFS
- **EU:** EBA/ESMA/EIOPA, AMLA (Frankfurt, live from 2025; direct supervision from 2028 [from memory - verify]), AMLR (applies from Jul 2027 [from memory - verify]), DORA, GDPR, AI Act
- **UK:** FCA, PRA, NCA (SARs), OFSI, ICO, FOS
- **GCC:** UAE CBUAE/goAML, DFSA, FSRA, Saudi SAMA/SAFIU
- **IN:** RBI, SEBI, IRDAI, FIU-IND/FINnet 2.0, PMLA, DPDP Act 2023 + Rules 2025, CERT-In 6-hour rule
- **SG:** MAS (Notice 626, MAS 610/1003 returns, TRM, Notice 644/655 [from memory - verify]), STRO
- **HK/CN:** HKMA, SFC, JFIU; PBOC, NFRA, CSRC, PIPL
- **JP/KR:** FSA/JAFIC; FSC/FSS/KoFIU
- **AU/NZ:** AUSTRAC (Tranche 2 reforms from 2026 [from memory - verify]), APRA (CPS 230 from 1 Jul 2025, CPS 234, APRA Connect), ASIC, AFCA; NZ RBNZ/FMA/DIA
- **Africa:** Nigeria NFIU, CBN, NDPA; Kenya FRC, CBK, ODPC; South Africa FIC (goAML), Prudential Authority, FSCA, POPIA, FICA
- **LatAm:** Brazil COAF, BCB (Pix MED fraud refund mechanism), LGPD; Mexico UIF, CNBV, Banxico
- **CA:** FINTRAC, OSFI (E-23 model risk guideline from May 2027 [from memory - verify], B-10, B-13), FCAC, PIPEDA/Quebec Law 25

### A. Financial crime: AML/CFT, KYC, sanctions, fraud

**1. Alert Triage Analyst (AML transaction monitoring L1).** Works through monitoring alerts, writes the disposition rationale and recommends close or escalate.
- Who hires: banks, NBFCs/lenders, fintechs and EMIs, money service businesses, crypto exchanges/VASPs, brokers.
- Jobs: pull the alert plus 6-12 months of account history; summarise the counterparties and flows; match against typologies (structuring, rapid movement, funnel accounts, mule patterns, trade-based ML); check prior alerts and cases; compare against the customer's KYC profile (expected turnover, occupation); write a disposition note; recommend close, escalate or "needs more information"; group related alerts into one case; measure the queue and how long alerts wait.
- Tier B. The L1/L2 analyst or MLRO closes or escalates.
- Rails: case system exports, core banking, KYC file, open banking / Account Aggregator data where it exists.
- Region: US BSA (31 CFR 1020.320); EU AMLD6 now, AMLR from 2027; UK MLR 2017 and POCA; IN PMLA plus RBI KYC Master Direction; SG MAS 626; AU AML/CTF Act; ZA FICA; BR Circular BCB 3.978; CA PCMLTFA.
- Evidence: SymphonyAI Sensa agents https://www.symphonyai.com/sensa ; WorkFusion, Lucinity, Hummingbird, Silent Eight, Quantexa, Napier [from memory - verify].

**2. SAR/STR Narrative Drafter.** Turns an escalated case into a regulator-ready narrative and a filing worksheet for the MLRO.
- Who hires: same as role 1, plus casinos, real estate agents, lawyers/accountants (DNFBPs).
- Jobs: build the who/what/when/where/why/how narrative; tabulate transactions with totals; check FinCEN SAR field completeness; prepare the goAML XML draft (UAE, ZA, NG, many others); prepare UK NCA DAML-request wording; track filing deadlines (US 30 days, extendable to 60; UK "as soon as practicable"; IN FIU-IND STR within 7 days of suspicion; check the rest); track continuing SARs (US 90-day review); keep tipping-off safe wording in every customer-facing note.
- Tier B. The MLRO, BSA officer or Principal Officer decides and files.
- Rails: FinCEN BSA E-Filing (human submits), goAML, FINnet 2.0, AUSTRAC Online, FINTRAC FWR, NCA SAR Portal.
- Evidence: arXiv 2509.08380 (Co-Investigator AI); SymphonyAI says it cuts drafting time by 40-60% (vendor claim).

**3. KYC / CDD Onboarding Reviewer.** Checks a customer file before a human approves it.
- Who hires: banks, NBFCs, fintechs, brokers, wealth managers, crypto firms, payment firms, CA/law firms (DNFBPs).
- Jobs: document checklist by customer type; extract data from ID, address proof and company papers; check data matches across documents; ask for missing items; screen against the risk-rating methodology and draft the risk score; flag high-risk industry or geography; check expiry dates; write the CDD memo; ask for an EDD trigger review.
- Tier B. The KYC officer approves.
- Rails: India CKYCR, DigiLocker, Aadhaar offline e-KYC/V-CIP (bank-run), PAN verification; UK Companies House API; EU business registers / BRIS; SG Myinfo; ZA CIPC; BR Receita CNPJ; US Secretary of State filings; liveness checks through licensed vendors (Onfido, Sumsub, Jumio, IDfy [from memory - verify]).
- Region: Aadhaar data handling is restricted by law; US CIP rule; EU AMLR CDD; UAE CBUAE.

**4. Beneficial Ownership (UBO) Mapper.** Unravels company structures down to the natural persons who own or control them.
- Who hires: banks, corporate service providers, law firms, private banks, trade finance desks.
- Jobs: draw the ownership tree from registry extracts; compute indirect percentages; flag circular holdings, nominees, trusts and bearer shares; compare declared UBOs with registers; list missing evidence; prepare the UBO declaration form.
- Tier A/B.
- Rails: Companies House PSC register; EU UBO registers (public access limited after the CJEU 2022 ruling [from memory - verify]); India MCA21 SBO; US Corporate Transparency Act (BOI reporting narrowed to foreign companies in 2025 [from memory - verify]); OpenCorporates; GLEIF LEI.
- Evidence: Moody's Orbis, Kyckr, Encompass [from memory - verify].

**5. Enhanced Due Diligence & PEP Researcher.** Builds the EDD pack for high-risk customers, PEPs and their relatives and close associates.
- Who hires: private banks, correspondent banking teams, wealth managers, crypto firms.
- Jobs: open-source adverse media research with dated citations; source-of-wealth and source-of-funds narrative from documents; PEP status and relationship mapping; litigation and enforcement checks; summary of the risk with open questions; questions to ask the client; reminders for periodic review.
- Tier B. The MLRO or senior management approves the PEP relationship (EU/UK rules require senior management approval).
- Rails: news APIs, court records (India eCourts, US PACER, UK BAILII), enforcement lists (FCA, SEC, SEBI orders), Wikidata/OpenSanctions PEP data.
- Evidence: ComplyAdvantage, LSEG World-Check, Dow Jones Risk & Compliance, OpenSanctions [from memory - verify].

**6. Sanctions Screening Hit Reviewer.** Prepares the review of name and payment screening hits.
- Who hires: banks, payment firms, trade finance, insurers, exporters, logistics firms.
- Jobs: compare hit vs. customer data points (DOB, nationality, address, identifiers); score likely false positive with reasons; check the 50% rule (OFAC) or ownership/control (EU/UK); check secondary sanctions and sectoral restrictions (SSI); check vessel/IMO and dual-use goods for trade; draft escalation to the sanctions officer; draft the blocking/reject report worksheet (OFAC 10 business days [from memory - verify]); track list updates and re-screen.
- Tier B. **The decision to clear, block or reject is human, always.**
- Rails: OFAC SDN/consolidated XML, UN, EU, UK OFSI/FCDO consolidated list, MAS, Canada SEMA, Australia DFAT, Japan MOF, Switzerland SECO; ISO 20022 pacs.008 fields for payment screening.
- Evidence: Silent Eight, Facctum, LSEG, Fircosoft (Moody's) [from memory - verify].

**7. Sanctions & Export-Control Regulatory Tracker.** Watches list changes and new designations and works out who in the book is affected.
- Who hires: banks, exporters, freight forwarders, crypto firms.
- Jobs: diff list updates daily; summarise new designations and general licences; re-screen the impacted book; draft customer-facing questions; track wind-down general licence dates; check export controls (US EAR/BIS Entity List, EU dual-use regulation 2021/821, UK SECO-equivalent [check]).
- Tier A.
- Rails: OFAC recent actions RSS; EU sanctions map; UK OFSI notices.

**8. Fraud Case Investigator Assistant.** Builds the fraud case file and timeline.
- Who hires: banks, card issuers, fintechs, insurers, e-commerce/payment firms.
- Jobs: timeline from transactions, logins and device events; identify mule accounts and linked parties; classify fraud type (APP/authorised push payment, account takeover, first-party, card-not-present, synthetic ID); calculate losses; prepare a chargeback/dispute evidence pack; draft the law-enforcement referral pack; prepare reimbursement assessment notes; recommend controls.
- Tier B. The fraud manager decides reimbursement or account action.
- Region: UK PSR APP reimbursement (mandatory since 7 Oct 2024, cap £85k [from memory - verify]); India RBI Master Directions on fraud risk (2024) and the NPCI chargeback/UDIR flow; SG Shared Responsibility Framework (from Dec 2024 [from memory - verify]); AU Scams Prevention Framework Act 2025 [from memory - verify]; BR Pix MED; US Reg E/Reg Z.
- Evidence: Feedzai, Featurespace, Sardine, BioCatch, Hawk [from memory - verify].

**9. Scam & Mule Network Analyst.** Links accounts, devices and beneficiaries into networks and drafts intelligence notes.
- Who hires: banks, PSPs, telecom-bank partnerships.
- Jobs: graph linked parties; score mule likelihood; draft a 314(b) information-sharing request (US); draft requests through India I4C/Sahyog and NCRP [check]; summarise scam typologies; check confirmation-of-payee mismatches.
- Tier B.
- Rails: UK Confirmation of Payee (Pay.UK); EU Verification of Payee (from Oct 2025 [from memory - verify]); India NPCI.

**10. Card & Payment Dispute Evidence Preparer.** Prepares chargeback and representment packs.
- Who hires: merchants, acquirers, PSPs, issuers.
- Jobs: classify the reason code (Visa/Mastercard); collect evidence; draft the representment letter; track deadlines; check Visa Compelling Evidence 3.0 eligibility; summarise the win rate.
- Tier A for merchants, B for issuers.
- Rails: Stripe/Adyen/Razorpay dispute APIs; Visa VROL; Mastercard Mastercom.
- Evidence: Chargebacks911, Justt, Chargeflow [from memory - verify].

**11. Internal Fraud / Employee Conduct Investigator Assistant.** Prepares HR/fraud investigation files.
- Who hires: banks, NBFCs, insurers, large firms.
- Jobs: expense and procurement anomaly scans; segregation-of-duties conflicts; interview question plans; evidence log with chain of custody; draft findings report.
- Tier B. The investigator and HR or legal decide.

**12. Financial Crime Risk Assessment Writer (EWRA/BWRA).** Builds the enterprise-wide or business-wide ML/TF/PF risk assessment.
- Who hires: every regulated firm.
- Jobs: inherent risk scoring by product, customer, geography and channel; control effectiveness mapping; residual risk heatmap; link to the national risk assessment and FATF mutual evaluations; draft the board paper; track the action plan.
- Tier B. The MLRO and board approve.
- Region: FATF Recommendation 1; UK MLR reg 18; EU AMLR Art. 10 [from memory - verify]; India RBI KYC MD para 5A; AUSTRAC ML/TF risk assessment (strengthened under the 2024 amendment).

**13. AML Model & Scenario Tuning Assistant.** Prepares below-the-line testing, threshold tuning analysis and coverage mapping.
- Who hires: banks, fintechs.
- Jobs: map typology coverage to scenarios; run above/below-the-line sampling analysis; prepare the threshold change rationale; prepare the data lineage checklist; draft the model documentation; set up the monitoring dashboard.
- Tier B. Model owner and model risk management approve.
- Region: US SR 26-2 now replaces SR 21-8 for BSA/AML models (Apr 2026) [opened]; EBA guidelines; MAS AI/data analytics guidance.

**14. Correspondent Banking & Payments Transparency Checker.** Checks the correspondent due diligence questionnaire (Wolfsberg CBDDQ) and payment message transparency.
- Who hires: banks, PSPs.
- Jobs: pre-fill and check the CBDDQ; review respondent answers; check FATF R.16 travel rule field completeness in pacs.008/MT103; track the ISO 20022 migration (SWIFT co-existence ended Nov 2025 [from memory - verify]); draft RFIs to counterparties.
- Tier B.
- Rails: SWIFT KYC Registry, ISO 20022 messages.

**15. Crypto / VASP Compliance Analyst.** Travel rule, wallet screening and VASP obligations.
- Who hires: exchanges, custodians, fintechs with crypto, banks with crypto clients.
- Jobs: check travel rule data completeness (EU TFR 2023/1113, FATF R.16); summarise wallet risk from analytics exports; prepare the MiCA CASP authorisation checklist; monitor the FIU-IND VASP registration (India); prepare tax reporting worksheets under CARF/DAC8 (from 2026 [from memory - verify]).
- Tier B.
- Rails: Chainalysis, Elliptic and TRM Labs exports (customer's own licence); Notabene/TRUST travel rule.

**16. Periodic KYC Refresh Coordinator.** Runs re-KYC campaigns.
- Who hires: banks, NBFCs, brokers, insurers.
- Jobs: list customers due by risk tier; draft outreach (no OTP or PIN requests); track responses; prepare the pending list for restrictions decided by humans; report campaign status.
- Tier A.
- Region: India periodic updation by risk (2/8/10 years) [from memory - verify] and RBI's 2025 relaxations; EU/UK risk-based review.

**17. MLRO Annual Report Preparer.** Drafts the MLRO's annual report to the board.
- Who hires: every regulated firm.
- Jobs: compile metrics (alerts, SARs, training completion, audit findings, open issues); summarise regulatory change; list resource asks; draft the board paper.
- Tier B. The MLRO signs.
- Region: UK FCA SYSC 3.2.6G; EU AMLR compliance manager reporting; similar in other regimes [check].

### B. Regulatory change, compliance monitoring and testing

**18. Regulatory Change Horizon Scanner.** Reads every new rule, circular, consultation and enforcement action and tells each business line what applies to it.
- Who hires: banks, NBFCs, fintechs, brokers, AMCs, insurers, CA/law firms, regtech-light SMEs.
- Jobs: daily digest per regulator; applicability assessment against the firm's licences and products; obligation extraction ("must/shall"); effective date and deadline tracking; consultation response reminders; gap list against current policies; action owner assignment; board and audit committee summary.
- Tier A (assessment Tier B).
- Rails: regulator RSS feeds and websites (RBI notifications, SEBI circulars, MAS, FCA, Federal Register, EUR-Lex, ESMA Q&A, HKMA circulars, APRA, CBUAE rulebook, CBN circulars, BCB normativos).
- Evidence: Norm Ai, CUBE, Ascent, Corlytics, Thomson Reuters Regulatory Intelligence, Wolters Kluwer, Regology [from memory except Norm Ai].

**19. Obligation Register & Control Mapper.** Keeps the obligations register mapped to policies, procedures and controls.
- Who hires: same as role 18.
- Jobs: build the obligations library; map each obligation to policy clause, process and control; find orphan controls and unmapped obligations; draft new control descriptions; keep version history; produce an audit-ready traceability report.
- Tier A.

**20. Policy & Procedure Writer.** Drafts and updates the policy library from regulation.
- Who hires: every regulated entity, especially small fintechs and NBFCs.
- Jobs: draft AML, KYC, sanctions, complaints, outsourcing, IT, BCP, privacy, whistleblowing and conflicts-of-interest policies; compare with the regulator template; redline changes from new circulars; produce a clean version and a version log; schedule annual review; draft attestation workflow.
- Tier B. Board or committee approves.

**21. Compliance Monitoring & Testing Analyst.** Runs the compliance monitoring plan (CMP).
- Who hires: banks, brokers, AMCs, wealth firms, insurers.
- Jobs: draft the risk-based monitoring plan; design test scripts; pull samples; test (e.g. suitability files, KYC files, disclosure, call recordings transcripts); record exceptions; rate issues; draft report and management actions; follow-up tracking.
- Tier B. Head of compliance owns the rating.
- Region: FCA SYSC 6.1; FINRA Rule 3110/3120 supervisory controls; SEBI compliance officer duties; MAS.

**22. Marketing & Financial Promotions Reviewer.** Checks ads, social posts, websites and scripts before they go live.
- Who hires: banks, fintechs, brokers, crypto firms, AMCs, insurers, finfluencer agencies.
- Jobs: check "fair, clear and not misleading" (UK FCA COBS 4 / PS on crypto promotions); risk warnings present; performance claims with periods; APR representative examples (UK CONC 3); US FINRA Rule 2210 and SEC Marketing Rule; India SEBI ad code and finfluencer restrictions (2024) [from memory - verify], RBI fair practices code; draft fixes; keep approval log.
- Tier B. Approver (UK s21 approver) signs.
- Evidence: Saifr, Red Oak, Hadrius, Norm Ai [from memory - verify].

**23. Communications Surveillance Reviewer.** Reviews flagged emails, chats and calls for conduct and market abuse.
- Who hires: banks, brokers, AMCs, trading firms.
- Jobs: triage lexicon and model hits; summarise the conversation with context; classify risk (insider dealing, collusion, off-channel communications, mis-selling, complaints not logged); draft escalation; prepare the record-keeping check.
- Tier B.
- Region: SEC/CFTC off-channel recordkeeping fines (2022-25); EU MAR; UK MAR and SYSC 10A recording; SEBI PIT regulations.
- Evidence: Behavox, Global Relay, Smarsh, Shield [from memory - verify].

**24. Trade Surveillance Alert Analyst.** Prepares market abuse alert reviews.
- Who hires: brokers, banks, exchanges, AMCs.
- Jobs: reconstruct order book and timeline; check news around the trade; classify spoofing, layering, front-running or wash trades; draft STOR (UK/EU) or SAR wording; maintain the PIT/insider list.
- Tier B. **A human files the STOR.**
- Region: EU/UK MAR STOR; US FINRA; India SEBI PIT / exchange alerts; HK SFC.

**25. Personal Account Dealing & Conflicts Register Keeper.** Manages employee trading pre-clearance and conflicts.
- Who hires: banks, brokers, AMCs, research firms, CA/audit firms (independence).
- Jobs: check pre-clearance requests vs. restricted/watch lists; reconcile holdings statements; track holding periods; gifts and entertainment register; outside business interests; conflicts register; annual attestation.
- Tier A/B.
- Evidence: StarCompliance, ComplySci, MCO [from memory - verify].

**26. Licence & Regulatory Obligations Calendar Keeper.** Tracks every periodic filing, renewal, fee and attestation.
- Who hires: small fintechs, NBFCs, brokers, PSPs, MSBs (US state licences, NMLS), payment aggregators (India RBI PA licence).
- Jobs: build the calendar; prepare the checklist and data needed per filing; send reminders; prepare the evidence folder; track US state MSB licence renewals and surety bonds.
- Tier A.
- Rails: NMLS, FCA Connect, RBI CIMS, SEBI SI portal.

**27. Regulator Inspection & Exam Readiness Coordinator.** Prepares for regulator exams and on-site inspections.
- Who hires: banks, NBFCs, brokers, insurers.
- Jobs: pre-exam request list (first-day letter) tracker; document index; draft responses to the inspection questionnaire; mock interview prep; matters requiring attention (MRA) or risk mitigation plan (RMP) tracker; remediation evidence pack; responses to the RBI Risk Assessment Report (RAR) / inspection compliance.
- Tier B.

**28. Remediation & Issue Management Tracker.** Runs the issues/actions register (audit, regulator, self-identified).
- Who hires: banks, NBFCs, fintechs.
- Jobs: log issues with owner, due date and rating; chase owners; check closure evidence; ageing reports; overdue escalation; draft validation request.
- Tier A.

**29. Consent Order / Enforcement Lessons Analyst.** Reads peers' enforcement actions and turns them into checks for this firm.
- Who hires: banks, fintechs, brokers.
- Jobs: digest enforcement actions (OCC, Fed, FinCEN, FCA Final Notices, RBI penalties, MAS, AUSTRAC); extract the failure pattern; map it to the firm's controls; draft "could this happen here" test.
- Tier A.

### C. Regulatory reporting (prudential and statistical)

**30. Prudential Return Preparer (capital).** Prepares capital adequacy returns from finance and risk data.
- Who hires: banks, NBFCs, investment firms, building societies, cooperative banks.
- Jobs: map GL and risk data to templates; compute RWA by approach (standardised credit risk, operational risk SMA); check validation rules; reconcile to FINREP/financial statements; variance analysis vs. prior period with explanations; draft the reporting memo; prepare sign-off pack.
- Tier B. **The CFO or reporting head submits.**
- Region: EU COREP/FINREP (EBA reporting framework 4.x, DPM 2.0 [from memory - verify]), CRR3 from 1 Jan 2025; UK PRA (Basel 3.1 from 1 Jan 2027 [from memory - verify]); US FR Y-9C, FFIEC 031/041 call report, FR Y-14 for large BHCs (Basel III endgame re-proposal status - check); India RBI returns via CIMS/XBRL (Form A, BSR, CRILC); SG MAS 610 / MAS 637; HK HKMA banking returns; AU APRA ARF via APRA Connect; CA OSFI BCAR; ZA BA returns; BR BCB (Documento 2061 etc. - check); GCC CBUAE / SAMA Basel returns.
- Evidence: Regnology, Wolters Kluwer OneSumX, AxiomSL (Adenza/Calypso), Workiva [from memory - verify].

**31. Liquidity & ALM Reporting Analyst.** LCR, NSFR, ALMM, structural liquidity and interest-rate-risk returns.
- Who hires: banks, NBFCs, cooperative banks.
- Jobs: compute LCR/NSFR from position data; prepare India Structural Liquidity Statement, Interest Rate Sensitivity and LCR returns; IRRBB EVE/NII scenarios; FR 2052a (US); maturity ladder; daily liquidity dashboard; ILAAP draft sections.
- Tier B.

**32. Large Exposure & Concentration Reporter.**
- Jobs: aggregate connected counterparties; compute limit usage; prepare LE returns (EU COREP LE, India LEF, MAS 639 [from memory - verify]); draft breach notifications for humans.
- Tier B.

**33. Statistical & Central Bank Data Returns Clerk.** Prepares BSR, credit and deposit statistics, AnaCredit, and FX transaction returns.
- Who hires: banks, NBFCs, AD Category banks (India FEMA returns: FC-GPR, ODI, EDPMS/IDPMS follow-ups).
- Jobs: data mapping and validation; error resolution; resubmission tracking; FEMA reporting checks on SOFTEX/EDPMS overdue export bills.
- Tier A/B.

**34. Tax-Transparency Reporting Preparer (FATCA/CRS).**
- Who hires: banks, AMCs, insurers, brokers, trusts.
- Jobs: self-certification review; indicia checks; reportable account list; XML schema validation; draft remediation outreach; India Form 61B, US IRS IDES, HMRC AEOI portal.
- Tier B. Responsible officer files.

**35. Regulatory Reporting Data Quality & Reconciliation Analyst.**
- Jobs: lineage maps; BCBS 239 principles self-assessment; reconcile returns to ledger; resubmission root cause analysis; data dictionary upkeep.
- Tier A/B.

**36. Pillar 3 & Disclosure Drafter.** Public disclosures drafts (Pillar 3, ICAAP summaries, risk sections of annual report).
- Tier B. Board approves.

### D. Risk management (credit, market, liquidity, operational, model, stress testing)

**37. Credit Risk Analyst Assistant (portfolio).** Monitors the loan book and drafts credit risk reports.
- Who hires: banks, NBFCs, MFIs, fintech lenders, cooperative banks, credit funds.
- Jobs: portfolio quality dashboards (DPD buckets, vintage, roll rates); early warning signal lists (stock statement delays, GST/filing gaps, bureau deterioration); covenant compliance tracking; watchlist memos; SMA/NPA classification check and reporting (India IRACP; check the new ECL framework from Apr 2027 [from memory - verify]); IFRS 9 / CECL stage movement analysis; limit breach reports.
- Tier B. **The credit committee decides; the AI never approves or declines.**
- Rails: credit bureau extracts (CIBIL/Experian/CRIF; US FICO; UK CRAs), India Account Aggregator, GSTN data via GSP, CRILC.

**38. Credit Memo / Annual Review Drafter.** Drafts credit appraisal and annual review notes from financials.
- Jobs: spread financials; ratio analysis; cash-flow projections; security cover; industry note; risk mitigants; deviations list.
- Tier B. The sanctioning authority decides.
- Evidence: nCino, Moody's QUIQspread, Abrigo [from memory - verify].

**39. Expected Credit Loss (IFRS 9 / CECL / Ind AS 109) Calculation Assistant.**
- Jobs: staging rules; PD/LGD/EAD data preparation; macro overlays memo; sensitivity tables; reconciliation of the allowance roll-forward; auditor queries pack.
- Tier B. CFO, CRO and auditors sign off.

**40. Market Risk Reporting Analyst.**
- Jobs: VaR/ES and sensitivity reports from risk system extracts; limit utilisation and breach notes; P&L attribution and backtesting exceptions; FRTB SA data checks; daily risk commentary.
- Tier B.

**41. Counterparty Credit & Collateral Analyst Assistant.**
- Jobs: exposure and collateral reconciliation; margin call dispute summaries; CSA term extraction; SA-CCR inputs; uncleared margin rule checks.
- Tier B.

**42. Operational Risk & RCSA Facilitator.** Runs risk and control self-assessments and the loss event database.
- Who hires: banks, NBFCs, fintechs, insurers.
- Jobs: draft RCSA questionnaires per process; collate answers; propose ratings with rationale; key risk indicator (KRI) tracking with thresholds; loss event capture and classification (Basel event types); near-miss log; scenario analysis workshop pack.
- Tier B.
- Evidence: Archer, MetricStream, ServiceNow IRM, LogicGate [from memory - verify].

**43. Incident & Breach Notification Clock Keeper.** When something breaks, it runs every regulator clock at once and drafts each notice.
- Who hires: banks, NBFCs, PSPs, fintechs, insurers.
- Jobs: classify the incident against each regime's thresholds; start parallel clocks; draft initial, intermediate and final notifications; collect facts; maintain the timeline; prepare customer notices.
- Clocks: EU DORA major ICT incident (initial within 4h of classification and at most 24h of awareness [from memory - verify]), GDPR 72h; India CERT-In 6h and RBI timelines; US 36h bank-regulator computer-security notice; SEC 8-K Item 1.05 within 4 business days; NYDFS 500 72h; SG MAS 1h [from memory - verify]; AU APRA CPS 234 72h and NDB scheme; HK HKMA; UAE.
- Tier B. **The firm's designated person files.**

**44. Model Risk Documentation & Validation Assistant.** Drafts model documentation and the validation workpapers.
- Who hires: banks, lenders, insurers, fintechs, asset managers.
- Jobs: model inventory upkeep and tiering by materiality; documentation templates (purpose, data, methodology, limitations); reproduce performance tests (discrimination, calibration, stability/PSI); benchmark challenger; draft validation findings; ongoing monitoring reports; model change log.
- Tier B. The independent validator and model owner sign.
- Region: US SR 26-2 / OCC 2026-13 (replaced SR 11-7, Apr 2026) [opened]; UK PRA SS1/23 (from May 2024); Canada OSFI E-23 (revised, from 2027 [from memory - verify]); EU ECB TRIM guide and CRR internal models; India RBI model risk draft directions (2024-25 [from memory - verify]); SG MAS.
- Evidence: ValidMind https://venturebeat.com/ai/ai-risk-management-startup-validmind-raises-8-1m-to-help-banks-comply-with-regulations ; Yields.io, Monitaur, SAS Model Manager [from memory - verify].

**45. AI Governance & AI Act Compliance Officer Assistant.** Keeps the AI inventory and builds the evidence for AI rules.
- Who hires: banks, insurers, fintechs, lenders, any firm deploying AI.
- Jobs: AI system inventory and risk classification (EU AI Act Annex III: credit scoring and life/health insurance pricing are high-risk); conformity checklist (risk management, data governance, logging, human oversight, transparency, accuracy); fundamental rights impact assessment draft (deployers that are banks/insurers); bias/fairness testing summaries (US ECOA/Reg B adverse action reasons, CFPB circulars); vendor AI due diligence; ISO/IEC 42001 gap analysis; NIST AI RMF mapping; board AI risk report.
- Tier B.
- Region: EU AI Act (high-risk moved to 2 Dec 2027 per provisional May 2026 deal - check final) [opened]; Colorado AI Act (delayed to 30 Jun 2026 [from memory - verify]); UK principles-based approach with FCA AI Lab; SG MAS FEAT/Veritas and AI risk management guidelines (consultation 2025 [from memory - verify]); HKMA GenAI guidance; India RBI FREE-AI framework (Aug 2025 [from memory - verify]); China generative AI interim measures and algorithm filing.
- Evidence: Credo AI, Holistic AI, Fairly AI, Monitaur, OneTrust AI governance [from memory - verify].

**46. Stress Testing & Scenario Analysis Assistant.**
- Jobs: scenario narrative drafting; macro variable mapping; sensitivity runs from the firm's models; reverse stress test write-up; ICAAP/ILAAP sections; CCAR/DFAST documentation support; recovery plan indicator calibration.
- Tier B.
- Region: US Fed stress tests; EBA EU-wide stress test; BoE ACS; RBI stress tests in the FSR; APRA.

**47. Risk Appetite & Board Risk Report Drafter.**
- Jobs: compile the risk dashboard vs. appetite metrics; RAG commentary; trend charts; emerging risks; draft board risk committee paper and minutes extracts.
- Tier B.

**48. Recovery & Resolution Planning (RRP) Assistant.**
- Jobs: critical functions mapping; recovery option playbook; indicators; solvent wind-down plan for fintechs/EMIs (UK safeguarding and wind-down plans); data for resolvability.
- Tier B.

**49. Interest & Pricing Fairness Analyst.**
- Jobs: price/value assessment (UK Consumer Duty fair value); loan pricing vs. risk-based pricing policy; interest computation checks (India RBI fair lending circular 2024 on interest charged, penal charges); refund calculation worksheets.
- Tier B.

### E. Conduct, consumer duty, complaints and vulnerable customers

**50. Complaints Handling Assistant.** Classifies, investigates and drafts responses to customer complaints, and tracks deadlines.
- Who hires: banks, NBFCs, fintechs, insurers, brokers, AMCs, credit unions.
- Jobs: classify by product and root cause; deadline clocks; gather account history; draft final response letters with referral rights; redress calculation; regulator-reportable flags; ombudsman case pack; root cause analysis.
- Deadline clocks: UK DISP 8 weeks with FOS referral wording; EU PSD2 15 business days; India RBI 30 days then RB-IOS; US CFPB portal 15/60 days; AU AFCA RG 271 30 days; SG FIDReC; HK FDRC; ZA ombuds; BR Consumidor.gov / BCB.
- Tier B. A named handler approves the final response.
- Evidence: complaint volumes above (FOS 305,726; CFPB 3.19 m; RBI 13.34 lakh).

**51. Complaints MI & Regulatory Complaints Return Preparer.**
- Jobs: FCA complaints return (DISP 1.10); APRA/ASIC IDR data reporting; RBI internal ombudsman annual report; trend analysis; board MI.
- Tier A/B.

**52. Consumer Duty / Fair Treatment Outcomes Monitor.**
- Who hires: UK firms first; also any firm with fair-treatment rules.
- Jobs: outcomes testing for products, price/value, understanding and support; customer journey sludge audit; communications readability testing; annual board Consumer Duty report draft; distribution chain information sharing.
- Tier B. The board signs.
- Region: UK PRIN 2A (from Jul 2023/Jul 2024); EU retail investment strategy (check); AU DDO (design and distribution obligations); SG Fair Dealing; India RBI customer service directions.

**53. Vulnerable Customer Support Coordinator.**
- Jobs: flag vulnerability signals; prepare tailored communication options; record needs (with consent); forbearance options summary; check arrears communication rules; referral to free debt advice.
- Tier B.

**54. Collections Conduct Reviewer.**
- Jobs: review call transcripts and scripts for harassment rules (US FDCPA/Reg F 7-in-7; India RBI recovery agent code; UK CONC 7); check calling-hour windows; draft corrective coaching notes.
- Tier A/B.

**55. Product Governance & New Product Approval Pack Preparer.**
- Jobs: target market definition; product risk assessment across compliance, credit, ops and IT; distribution strategy; testing results; approval committee paper; post-launch review.
- Tier B.

**56. Suitability & Advice File Checker.**
- Who hires: wealth managers, IFAs, brokers, insurers.
- Jobs: check the fact-find vs. recommendation; risk profile match; costs and charges disclosure (MiFID II, PRIIPs KID); US Reg BI care obligation documentation; India SEBI RIA/IA rules; switching justification; sample QA.
- Tier B.

### F. Data privacy, cyber, third-party and operational resilience

**57. Privacy Operations Assistant (DSAR, RoPA, DPIA).**
- Who hires: banks, fintechs, insurers, brokers, any firm handling personal data.
- Jobs: data subject request intake and deadline (GDPR 1 month; CCPA 45 days; India DPDP Rules 2025 timelines - check; LGPD 15 days; Singapore PDPA); search and redact; record of processing activities; DPIA drafts; consent records; cross-border transfer assessments (SCCs/TIA, DPDP restricted-country lists); retention schedules; breach assessment.
- Tier B. **DPO / Grievance officer decides.**
- Region: GDPR / UK GDPR; India DPDP Act 2023 + DPDP Rules 2025 (phased commencement - check); CCPA/CPRA and state laws; China PIPL; Brazil LGPD; South Africa POPIA; Nigeria NDPA 2023; Kenya DPA 2019; Japan APPI; Korea PIPA; Saudi PDPL; UAE PDPL; Canada PIPEDA/Law 25.
- Evidence: OneTrust, TrustArc, Transcend, DataGrail [from memory - verify].

**58. Cyber Risk & Control Assurance Assistant.**
- Jobs: map controls to frameworks (NIST CSF 2.0, ISO 27001:2022, CIS); compile evidence; vulnerability ageing reports; draft security policies; questionnaire answers; board cyber report; tabletop exercise scripts; penetration test finding tracker.
- Tier B. CISO owns.
- Region: NYDFS 23 NYCRR 500 (amended Nov 2023; annual certification by 15 Apr - human signs); EU DORA / NIS2; India RBI IT governance directions (2023) and SEBI CSCRF (2024); SG MAS TRM + cyber hygiene notice; HK HKMA C-RAF; AU CPS 234; SWIFT CSP attestation; PCI DSS 4.0.1.

**59. Third-Party / Vendor Risk Analyst.**
- Who hires: banks, NBFCs, fintechs, insurers, AMCs.
- Jobs: vendor inventory and criticality tiering; due diligence questionnaire review; SOC 2 / ISO report reading with exceptions noted; contract clause checks (audit rights, sub-outsourcing, exit, data location); concentration risk; ongoing monitoring (news, financial health); exit plans; outsourcing notifications to regulators.
- Tier B.
- Region: EU DORA Art. 28-30 and EBA outsourcing guidelines; UK PRA SS2/21; US interagency TPRM guidance (Jun 2023); India RBI IT outsourcing directions (2023) and outsourcing of financial services; SG MAS outsourcing guidelines; AU CPS 230 (from 1 Jul 2025); HK HKMA.
- Evidence: Prevalent (Mitratech), OneTrust TPRM, ProcessUnity, Whistic, SecurityScorecard [from memory - verify].

**60. DORA Register of Information Builder.** Builds and validates the annual ICT third-party register.
- Who hires: EU banks, investment firms, payment/e-money firms, insurers, crypto CASPs, fund managers.
- Jobs: collect contracts; fill the ITS templates (B_01-B_99); LEI/EUID checks; function-to-provider mapping; validation rule pre-check against ESA feedback; resubmission fixes.
- Tier A/B.
- Evidence: EBA RoI FAQ and CSSF list of frequent errors [opened].

**61. Operational Resilience & BCP Mapper.**
- Jobs: important business services list; impact tolerances; mapping of people, processes, technology, facilities and third parties; severe-but-plausible scenario testing write-ups; self-assessment document; BCP/DR test reports; crisis communication drafts.
- Tier B.
- Region: UK FCA/PRA (fully in force 31 Mar 2025); EU DORA resilience testing incl. TLPT; AU CPS 230; HK OR-2; SG MAS BCM guidelines; India RBI operational resilience guidance (2024); Basel Principles for Operational Resilience.

**62. Information Security Questionnaire Responder.** Answers bank and corporate client security and compliance questionnaires from a knowledge base.
- Who hires: fintechs and vendors selling to banks.
- Tier A. A human approves before sending.
- Evidence: Vanta, Drata, Conveyor, Loopio [from memory - verify].

### G. Internal audit

**63. Internal Audit Planning Assistant.**
- Who hires: banks, NBFCs, insurers, fintechs, co-ops, audit firms doing outsourced IA.
- Jobs: audit universe upkeep; risk-based annual plan scoring; coverage of regulatory "must-audit" items (e.g. India RBI risk-based internal audit; concurrent audit); resource plan; audit committee plan paper.
- Tier B. The CAE and audit committee approve.
- Region: IIA Global Internal Audit Standards (effective 9 Jan 2025 [from memory - verify]); UK CIIA financial services code; India RBI RBIA guidelines; US FDICIA.

**64. Audit Fieldwork Assistant (test of controls).**
- Jobs: walkthrough notes; risk and control matrix; test scripts; sample selection with documented method; testing of evidence (e.g. KYC files, loan files, access reviews, reconciliations); exceptions log; workpaper cross-referencing; data analytics (full-population tests, duplicates, outliers).
- Tier B. The auditor concludes.
- Evidence: AuditBoard AI, Workiva, TeamMate+ (Wolters Kluwer), MindBridge [from memory - verify].

**65. Audit Report Writer & Issue Follow-up.**
- Jobs: draft findings with condition/criteria/cause/effect/recommendation; rating rationale; management response collection; follow-up validation tracker; audit committee summary.
- Tier B. **The CAE signs the opinion.**

**66. Concurrent / Branch Audit Assistant (India + similar).**
- Jobs: daily/monthly concurrent audit checklists (cash, KYC, advances, forex, CTR/STR compliance); exception reports; compliance from branch; consolidated report.
- Tier B. Concurrent auditor (CA firm) signs.

**67. SOX / ICFR Controls Testing Assistant** (banks' financial reporting controls).
- Jobs: control narratives; test of design and operating effectiveness; deficiency evaluation worksheet; management certification pack.
- Tier B. Management and auditors sign. (India: IFC under Companies Act; Japan J-SOX.)

**68. External Auditor & Regulator Request (PBC) Coordinator.**
- Jobs: track "prepared by client" lists; collect documents; check completeness; status reports; draft responses to auditor queries.
- Tier A.

### H. Governance, board and company secretarial (banks and financial institutions)

**69. Board & Committee Secretary Assistant.**
- Who hires: banks, NBFCs, insurers, AMCs, fintechs, co-op banks, listed companies.
- Jobs: annual board calendar; agenda and pack assembly from papers; action log; minutes draft from notes/recording; resolutions; attendance and quorum check; committee charter reviews; board evaluation questionnaire; regulatory board-level requirements list (e.g. RBI requirements on board committees, ACB/RMCB meetings; UK SM&CR responsibilities map).
- Tier B. **The company secretary finalises and the chair signs.**
- Evidence: Diligent, BoardPAC, Nasdaq Boardvantage [from memory - verify].

**70. Statutory Filings & Corporate Secretarial Clerk (financial institution).**
- Jobs: India MCA forms (MGT-7, AOC-4, DIR-12), RBI NBFC returns, SEBI LODR disclosures; UK Companies House confirmations and PSC updates; US state annual reports; registers upkeep; disclosure timing checks (LODR 24h / 30 min for some events).
- Tier A/B. A director or company secretary files.

**71. Fit & Proper / Senior Managers Regime Assistant.**
- Jobs: UK SM&CR statements of responsibilities and the management responsibilities map; certification regime annual assessments; regulatory references; conduct rules breach reporting worksheets; India RBI fit and proper declarations for directors; HK Manager-in-Charge; SG MAS IAC guidelines; AU FAR (Financial Accountability Regime, banks from Mar 2024); Ireland SEAR.
- Tier B.

**72. Related-Party & Insider Lending Monitor.**
- Jobs: related-party register; flag loans/transactions to directors and relatives; limits checks (US Reg O; India Banking Regulation Act s.20 and RBI directions); board approval tracking; disclosure pack.
- Tier B.

**73. Whistleblowing & Speak-up Case Coordinator.**
- Who hires: banks, NBFCs, listed companies, insurers, NGOs.
- Jobs: anonymous intake channel (case number, no identity required); acknowledge within deadlines (EU Whistleblowing Directive: 7 days acknowledge, 3 months feedback); triage; investigation plan; anti-retaliation checks; case summaries for the audit committee; regulator whistleblowing interface (FCA, SEC whistleblower, SEBI) info for the reporter.
- Tier B. Investigators and the whistleblowing champion decide. Confidentiality is strict.
- Evidence: NAVEX, EQS, Whispli, Vault [from memory - verify].

**74. Ethics, Code of Conduct & Training Administrator.**
- Jobs: annual code attestations; mandatory training assignment and tracking (AML, sanctions, privacy, anti-bribery); quizzes from policy; completion MI; overdue chasers.
- Tier A.

**75. Anti-Bribery & Corruption (ABC) Due Diligence Assistant.**
- Jobs: third-party/intermediary ABC questionnaires; gifts and hospitality register; red-flag review; FCPA/UK Bribery Act s.7 adequate-procedures evidence; India PCA 2018 corporate liability notes.
- Tier B.

### I. ESG, climate and sustainability risk

**76. Climate Risk & Disclosure Drafter.**
- Who hires: banks, insurers, AMCs, listed NBFCs.
- Jobs: TCFD/ISSB IFRS S2 disclosure draft; physical and transition risk heatmap of the loan book; financed emissions (PCAF) calculation workbook; scenario narratives (NGFS); data gap list; climate stress test templates.
- Tier B. The board approves.
- Region: ISSB adopted or adopting in Australia (AASB S2 from 2025), UK SRS (consultation 2025 [from memory - verify]), Japan SSBJ, SG, HK (HKEX), Brazil CVM, Nigeria; EU CSRD/ESRS (Omnibus scaled back 2025-26 - check), SFDR; ECB climate expectations; India RBI climate disclosure draft (2024) and SEBI BRSR Core; US SEC climate rule withdrawn/defended (2025) and California SB 253/261 - check.

**77. Sustainable Finance Taxonomy & Greenwashing Checker.**
- Jobs: classify loans/products against EU Taxonomy / Singapore-Asia Taxonomy / India climate finance taxonomy (draft 2025 [from memory - verify]); green bond use-of-proceeds tracking; fund naming rules (ESMA guidelines 2024; UK SDR labels); marketing claims check for greenwashing.
- Tier B.

**78. ESG Due Diligence & E&S Risk Screening Assistant (lending).**
- Jobs: Equator Principles / IFC Performance Standards screening; E&S action plan tracking; exclusion list check; client ESG questionnaire summaries.
- Tier B.

### J. Supporting roles for small regulated firms and their advisers

**79. "Compliance Officer for One" (small fintech/NBFC/MSB/broker).** A bundle of roles 16, 18, 20, 26, 28, 50 and 57 for a firm with a one-person compliance team.
- Tier A/B.
- Why: obligations are the same as a bank; enterprise tools are priced out. Strongest SME wedge.

**80. Compliance Consultancy / CA-firm Copilot.** Lets an advisory firm serve many regulated clients (gap assessments, policy drafting, inspection prep, concurrent audit).
- Tier B. The partner signs deliverables.

---

## 3. Never an AI employee (tier C) in this segment

| Reserved act | Why |
|---|---|
| Filing a SAR/STR/STOR or regulatory return as the institution | Legal obligation of the MLRO/BSA officer/Principal Officer or designated reporting officer; personal liability; submission credentials belong to named people |
| Deciding to file or not file a SAR; clearing a true sanctions match; giving consent/DAML | Judgement reserved to the nominated officer; tipping-off and sanctions breach are criminal offences |
| Freezing, blocking, rejecting or exiting a customer/account/payment | Affects customer rights; legal duty of the firm; needs named authority |
| Approving/declining KYC, a loan, a credit limit, a claim or a refund | Credit and onboarding decisions are reserved; EU AI Act high-risk human oversight; ECOA/Reg B adverse action duties |
| Signing an audit opinion, ICFR/SOX certification, NYDFS 500 certification, CFO/CRO attestation, compliance certificate | Personal certification by named officers |
| Approving a model for use / signing an independent validation | Model governance requires independent human validators |
| Board decisions, resolutions, approving policies, risk appetite | Directors' fiduciary duties |
| Reporting to law enforcement as a whistleblower's representative, determining retaliation | Legal protection and confidentiality obligations |
| Holding a regulated controlled/senior-manager function (MLRO, SMF, DPO statutory role, CISO accountability) | Regimes require a named fit-and-proper human |
| Investigating or interviewing employees as the decision-maker in disciplinary matters | Employment law, natural justice |
| Accessing law-enforcement, FIU or 314(a) confidential information beyond the officer | Restricted by statute |
| Typing passwords/OTPs/PIN to regulator portals | Credentials are personal; never share |

## 4. Top 10 roles to build first and why

1. **Regulatory Change Horizon Scanner (18) + Obligation Register (19).** Every regulated firm worldwide needs it, it is Tier A, it works from public regulator feeds with no customer data, and the demand is proven (Norm Ai unicorn, CUBE and TR surveys). Start with RBI/SEBI/IRDAI, FCA, MAS, US Federal Register/FinCEN/OCC, EUR-Lex/EBA.
2. **SAR/STR Narrative Drafter (2) + Alert Triage Analyst (1).** The single biggest manual cost in the US$200 bn+ financial-crime spend; 70-95% of alerts are false positives and each narrative takes hours. Tier B with the MLRO deciding fits Hoola's "prepare, human decides" law exactly.
3. **Complaints Handling Assistant (50).** Huge volumes (CFPB 3.19 m to 6.64 m a year, FOS 305k, RBI 13.3 lakh), hard regulator clocks and template-able letters. Serves banks and small lenders alike.
4. **KYC/CDD Onboarding Reviewer (3) + Periodic KYC Refresh (16).** Constant volume, document-reading work, and clear official rails (CKYCR, DigiLocker, Companies House, Myinfo).
5. **Sanctions Screening Hit Reviewer (6).** High false-positive pain; public list data; the human clears.
6. **Incident & Breach Notification Clock Keeper (43).** DORA, CERT-In 6h, the US 36h rule, GDPR 72h, SEC 4 days. Parallel clocks are error-prone and the penalties are high; a deadline-and-draft tool is Tier A/B and easy to trust.
7. **Third-Party Risk Analyst (59) + DORA Register Builder (60).** New mandatory work (DORA from 2025, CPS 230 from Jul 2025, RBI outsourcing). Reading SOC 2 reports and contracts is LLM-strong.
8. **Compliance Officer for One (79).** Bundles roles for small fintechs, NBFCs, payment aggregators, MSBs and brokers. It fits Hoola's SME users and nobody serves this market well.
9. **Model Risk & AI Governance Assistant (44 + 45).** Rules are new and moving (SR 26-2 Apr 2026, PRA SS1/23, OSFI E-23, EU AI Act Dec 2027, RBI FREE-AI). Documentation and inventory work is the bottleneck.
10. **Board & Committee Secretary Assistant (69) + Internal Audit Fieldwork Assistant (64).** Packs, minutes, action logs, sampling and workpapers are steady and high-volume. The work is Tier B, and it serves banks and the CA/audit firms that act for them.

## 5. Sources

Opened or read as search results this session:
- O*NET Compliance Officers https://www.onetonline.org/link/details/13-1041.00
- LexisNexis True Cost of FCC https://risk.lexisnexis.com/about-us/press-room/press-release/20230926-global-financial-crime-compliance-costs ; https://risk.lexisnexis.com/about-us/press-room/press-release/20240221-true-cost-of-compliance-us-ca ; https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20240306-true-cost-of-compliance-emea
- SWIFT Institute paper on TM false positives https://swift.com/swift-resource/252235/download ; Columbia SIPA https://www.sipa.columbia.edu/detecting-financial-crimes-evaluating-efficacy-automated-transaction-monitoring
- FinCEN https://www.fincen.gov/sites/default/files/shared/FinCEN-Infographic-Public-2025-508.pdf ; https://fincen.gov/reports/sar-stats/sar-filings-industry ; Thomson Reuters SAR report https://www.thomsonreuters.com/en-us/posts/corporates/sars-report-2024
- Co-Investigator AI https://arxiv.org/abs/2509.08380 ; SymphonyAI Sensa https://www.symphonyai.com/sensa
- Thomson Reuters cost of compliance 2023 https://www.thomsonreuters.com/en-us/posts/investigation-fraud-and-risk/2023-cost-of-compliance-report/ ; regulatory change article https://www.familywealthreport.com/article.php/Compliance-Corner:-Regulatory-Change-Management-Costs-Seen-Rising--
- FOS 2024/25 https://www.financial-ombudsman.org.uk/news/financial-ombudsman-service-receives-305000-complaints-2024-25
- CFPB https://www.consumerfinance.gov/data-research/research-reports/2024-consumer-response-annual-report/ ; https://files.consumerfinance.gov/f/documents/cfpb_2025-cr-annual-report_2026-03.pdf
- RBI Ombudsman 2024-25 https://website.rbi.org.in/web/rbi/-/publications/annual-report-of-ombudsman-scheme-2024-25 ; https://www.business-standard.com/finance/news/rbi-ombudsman-complaints-fy25-rise-loans-credit-cards-125120101346_1.html
- SR 26-2 https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm ; Orrick https://www.orrick.com/en/Insights/2026/04/Agencies-Overhaul-Model-Risk-Management-Guidance-for-Banks-Heres-What-Changed ; KPMG https://kpmg.com/us/en/articles/2026/model-risk-management-revised-interagency-guidance-reg-alert.html ; Moody's https://www.moodys.com/web/en/us/insights/banking/from-sr117-to-sr262-managing-model-risk-when-models-dont-stand-still.html
- EU AI Act Omnibus https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/ ; https://www.hoganlovells.com/en/publications/eu-legislators-agree-to-delay-for-highrisk-ai-rules ; https://www.pinsentmasons.com/Out-Law/News/Rules-high-risk-AI-delayed-under-EU-omnibus-deal
- DORA RoI https://eba.europa.eu/activities/direct-supervision-and-oversight/digital-operational-resilience-act/preparation-dora-application ; https://www.cssf.lu/en/2025/04/guidance-for-correction-of-most-frequent-issues-identified-in-the-submitted-registers-of-information-under-dora/ ; https://www.esma.europa.eu/digital-operational-resilience-act-dora
- Norm Ai https://www.citi.com/ventures/perspectives/pressrelease/investing-in-norm-ai.html ; https://enterprisedna.co/resources/news/norm-ai-120m-series-c-compliance-agents-enterprise-2026/ ; ValidMind https://venturebeat.com/ai/ai-risk-management-startup-validmind-raises-8-1m-to-help-banks-comply-with-regulations

Everything else is marked "[from memory - verify]" inline. That covers most regional deadlines and thresholds and the vendor lists other than Norm Ai, ValidMind and SymphonyAI. Check them before building on them.
