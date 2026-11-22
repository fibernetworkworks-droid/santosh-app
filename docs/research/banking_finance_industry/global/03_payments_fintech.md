# Segment 03 - Payments, cards, remittance, fintech infrastructure and digital assets (worldwide)

Researched 22 Nov 2026. Every role below follows the brief's hard limits: the AI PREPARES, CHECKS, EXPLAINS,
CALCULATES, DRAFTS, TRACKS and REMINDS. It never moves money, never authorises / declines / reverses a payment,
never accepts or refuses a merchant, never freezes an account, never decides a dispute as the issuer or the
acquirer, never files an STR / SAR / regulatory return AS the institution, never signs a key or a wallet
withdrawal, and never asks for a PIN / OTP / CVV / card number / password / seed phrase. Card numbers appear only
as the last 4 digits; wallet addresses and transaction hashes are fine (they are public).

How sources are marked: **[opened]** = the page was opened and read; **[search]** = the source was found and its
content read through the search result summary (title + URL seen, text summarised by the search tool, not opened
in full); **(from memory - verify)** = not checked in this research.

---

## Part 1. The jobs that exist (occupation taxonomies + industry org charts)

Payments is thinly represented in official taxonomies; most payment jobs sit inside broader codes. The useful codes:

| Taxonomy | Code / title | What it covers in payments |
|---|---|---|
| O*NET / US SOC | 13-2099.04 Fraud Examiners, Investigators and Analysts **[opened]** | payment fraud, mule, AML investigation tasks: review suspected fraud, analyse financial data for irregularities, prepare written reports, gather documents, recommend actions, keep databases of fraud information, coordinate with law enforcement, recover losses |
| O*NET / US SOC | 13-1041 Compliance Officers; 13-1041.07 Regulatory Affairs Specialists (from memory - verify) | AML / sanctions / licensing / scheme compliance |
| O*NET / US SOC | 43-4041 Credit Authorizers, Checkers and Clerks; 43-3071 Tellers; 43-3099 Financial Clerks, All Other; 43-3011 Bill and Account Collectors (from memory - verify) | card authorisation exceptions, payment operations clerks, dispute clerks, collections / dunning |
| O*NET / US SOC | 11-3031.01 Treasurers and Controllers; 13-2051 Financial and Investment Analysts (from memory - verify) | payment-firm treasury, settlement, liquidity |
| ISCO-08 | 3313 Accounting associate professionals, 4311 Accounting and bookkeeping clerks, 4312 Statistical, finance and insurance clerks, 2413 Financial analysts, 3359 Regulatory government associate professionals (from memory - verify) | payment ops, reconciliation, settlement |
| ESCO | "financial fraud examiner", "anti-money laundering analyst", "payment service provider" occupations sit under ISCO 2411/2413/3313 (from memory - verify) | same |
| UK SOC 2020 | 3534 Finance and investment analysts and advisers; 4122 Book-keepers, payroll managers and wages clerks; 2424 Business and financial project management (from memory - verify) | |
| ANZSCO | 599611 Bank Worker? / 552211 Bookkeeper / 224999 Information and Organisation Professionals nec (from memory - verify) | |

Industry org-chart reality (job boards and bank / PSP structures, from memory - verify specific titles on
LinkedIn / Indeed): issuer side = card programme manager, card operations, disputes / chargeback analyst, fraud
analyst, collections; acquirer / PSP side = merchant onboarding (KYB) analyst, merchant underwriter, risk analyst
(transaction laundering, MCC), chargeback / representment specialist, settlement and reconciliation analyst,
scheme compliance manager, treasury / liquidity; bank payments = payment operations (repairs, returns,
investigations), SWIFT / ISO 20022 specialist, correspondent banking KYC, sanctions screening analyst (L1/L2),
nostro reconciliation; remittance / MTO = compliance officer, payout partner manager, payment ops; mobile money =
agent network manager, float manager, reversals desk; crypto / VASP = KYC analyst, travel-rule operator,
blockchain investigator, custody operations, listing analyst, market surveillance, MLRO; fintech / BaaS =
partner-bank oversight, programme compliance, complaints handler, regulatory reporting.

The roles in Part 3 group these tasks into 72 hireable AI employees.

---

## Part 2. Regional reference card (rails, rule-makers, dispute and fraud regimes)

Use this table instead of repeating every system in every role. Each role then names the differences that matter.

| Region | Real-time / domestic rails | Card schemes | Open banking / finance | Key payment / fraud rules and regulators | Crypto / stablecoin regime |
|---|---|---|---|---|---|
| US | FedNow, RTP (TCH), ACH (Nacha), Fedwire, Zelle | Visa, Mastercard, Amex, Discover | CFPB s.1033 rule enjoined and under reconsideration; new proposal sent to OIRA Aug 2026 **[search]** | Reg E (EFT errors / unauthorised), Reg Z (card billing errors), Remittance Transfer Rule (Reg E subpart B), state money transmitter licences (NMLS), FinCEN MSB / BSA, OFAC; CFPB complaints doubled to 6.6m in 2025 **[search]** | GENIUS Act: OCC final rule for permitted payment stablecoin issuers (Oct 2026), FinCEN/Treasury AML rule proposed **[search]**; 1099-DA broker reporting (from memory - verify); NY BitLicense |
| EU / EEA | SEPA Instant (Instant Payments Regulation: send instant + Verification of Payee from Oct 2025 - from memory - verify), SEPA CT/DD, TIPS, national (Bizum, iDEAL/Wero, Swish in SE) | Visa, Mastercard, national (Cartes Bancaires, girocard, Bancomat) | PSD2 today; PSD3 + Payment Services Regulation provisionally agreed 27 Nov 2025, IBAN-name check, PSP liability where VoP failures contribute; impersonation-fraud reimbursement scope disputed between commentators **[search]** | PSD2 SCA, Interchange Fee Regulation caps, EBA / national competent authorities, DORA incident reporting, AMLR / AMLA | MiCA fully applicable 30 Dec 2024, CASP authorisation (Art. 59), Transfer of Funds Regulation 2023/1113 + EBA travel-rule guidelines EBA/GL/2024/11; EBA Op/2025/08 on PSD2-MiCA interplay for e-money tokens **[search]**; DAC8 tax reporting (from memory - verify); digital euro: Council mandate Dec 2025, ECB says pilot 2027 / first issuance possibly 2029 if law passes in 2026 **[search]** |
| UK | Faster Payments, Bacs, CHAPS, Confirmation of Payee | Visa, Mastercard, Amex | UK Open Banking (OBIE / JROC, now Open Banking Ltd, from memory - verify) | PSR APP reimbursement (from Oct 2024, cap £85,000; 89% of in-scope losses reimbursed in first 15 months), FCA safeguarding CASS 15 + resolution pack CASS 10A + monthly safeguarding return (PS25/12, from May 2026) **[search]**; Consumer Credit Act s.75 (from memory - verify); FOS | FCA cryptoasset registration; new regime under FSMA (from memory - verify) |
| Gulf / GCC | UAE Aani / IPP, Saudi sarie, Bahrain Fawri+, Qatar Fawran (from memory - verify) | Visa, Mastercard, mada (KSA), UAE Jaywan (from memory - verify) | UAE Open Finance (CBUAE), Saudi SAMA Open Banking (from memory - verify) | CBUAE stored-value / retail payment regulations, SAMA, DFSA / FSRA | Dubai VARA (Issuance Rulebook May 2025), ADGM FSRA, CBUAE Payment Token Services for Dirham tokens, SCA licence overlap **[search]** |
| India | UPI (incl. UPI Autopay, UPI Lite, UPI on credit), IMPS, NEFT, RTGS, AePS, BBPS | RuPay, Visa, Mastercard, Diners | Account Aggregator (RBI NBFC-AA, Sahamati) | RBI TAT for failed transactions, Integrated Ombudsman (13.34 lakh complaints FY25, credit cards second largest) **[opened]**, PA / PG guidelines, PPI master directions, e-mandate rules, LRS / FEMA, cybercrime 1930 / NCRP; digital payment frauds 13,516 cases = 56.5% of reported bank frauds FY25 (RBI annual report, >= Rs 1 lakh) **[search]** | FIU-IND registration for VDA SPs, 30% tax + 1% TDS (s.194S) (from memory - verify); e-Rupee CBDC pilot |
| Singapore / SE Asia | PayNow, FAST, PromptPay (TH), DuitNow (MY), QRIS / BI-FAST (ID), InstaPay / PESONet (PH), NAPAS (VN); Project Nexus (from memory - verify) | Visa, Mastercard, NETS, national QR | SG SFA / API exchange; MY, TH open banking programmes (check) | MAS Payment Services Act; MAS-IMDA Shared Responsibility Framework for phishing scams from 16 Dec 2024 (losses shared between victims, FIs, telcos; no cap) **[search]**; BSP, BOT, BNM, OJK | MAS DPT licensing + stablecoin framework (from memory - verify) |
| China / Hong Kong | CNAPS, IBPS, NetsUnion; Alipay, WeChat Pay; HK FPS | UnionPay | (none equivalent) | PBoC non-bank payment rules; HKMA Stored Value Facilities licensing | Mainland ban on crypto trading; e-CNY; HK Stablecoins Ordinance in force 1 Aug 2025, HKMA licence + public register, first licences reported 2026 **[search]**; HK SFC VATP licensing |
| Japan / Korea | Zengin, BOJ-NET, Japan code payments (PayPay); Korea KFTC, KakaoPay, Toss | JCB, BC Card (KR) | Japan electronic payment agency rules; Korea MyData | Japan Payment Services Act (FSA), Korea Electronic Financial Transactions Act (FSC) (from memory - verify) | Japan FSA crypto-exchange registration + stablecoin rules (2023); Korea Virtual Asset User Protection Act (2024) (from memory - verify) |
| Australia / NZ | NPP / PayTo, BECS, eftpos | Visa, Mastercard, eftpos | Consumer Data Right (ACCC / Treasury) | ePayments Code, AFCA, Scams Prevention Framework Act 2025 (banks, telcos, platforms) - from memory - verify commencement and designations; AUSTRAC | AUSTRAC DCE registration; digital asset platform licensing bill (from memory - verify) |
| Africa | Kenya M-Pesa / PesaLink; Nigeria NIP (NIBSS), eNaira (CBDC); South Africa PayShap, RTC; PAPSS (pan-African) | Visa, Mastercard, Verve (NG) | Nigeria CBN open banking guidelines (2023), go-live announced for Aug 2025 then delayed, phased rollout reported (status unverified) **[search]** | CBK National Payment System Act, CBN, SARB / Prudential Authority; mobile money > USD 2 trillion in 2025, 2.3bn registered / 593m active accounts, "fraud remains widespread" (GSMA) **[opened]** | Kenya VASP Act 2025 (from memory - verify); SA FSCA treats crypto as financial product; Nigeria SEC digital asset rules (check) |
| Latin America | Brazil Pix (Pix Automático live June 2025, Resolução BCB 482; MED 2.0 multi-layer fund blocking for fraud, launch around late 2025) **[search]**; Mexico SPEI / CoDi / DiMo; Colombia Bre-B (from memory - verify) | Visa, Mastercard, Elo (BR), Carnet (MX) | Brazil Open Finance (166m+ active consents, 100m+ users reported Apr 2026 **[search]**); Mexico Fintech Law open APIs (partial) | BCB, CMN; Mexico CNBV / Banxico; MED limited to fraud / scams / coercion, not commercial disputes **[search]** | Brazil Law 14.478/2022 + BCB VASP rules (from memory - verify) |
| Canada | Lynx, ACSS, Interac e-Transfer; Real-Time Rail (in build) | Visa, Mastercard, Interac debit, Amex | Consumer-driven banking framework (legislated 2024-25, check) | Retail Payment Activities Act (Bank of Canada supervises PSPs, registration 2024), FINTRAC, Code of Conduct for the Credit and Debit Card Industry (from memory - verify) | CSA crypto trading platform registration, stablecoin as "value-referenced crypto assets" (from memory - verify) |
| Global | SWIFT (ISO 20022 CBPR+: coexistence ended 22 Nov 2025 at ~97% adoption; structured / hybrid address only after 14 Nov 2026; MT end-of-life Nov 2027) **[search]** | scheme rule books | - | FATF R.16 (wire transfer / travel rule), card scheme rules, PCI DSS v4.0.1 (future-dated requirements mandatory 31 Mar 2025) **[search]** | FATF 7th targeted update (Jul 2026): 83% of surveyed jurisdictions have travel-rule laws, almost half took no enforcement action, most on-chain illicit activity now involves stablecoins **[search]**; CBDCs: ~137-146 jurisdictions exploring, only a few fully launched (Bahamas, Jamaica, Nigeria per CRS; other counts disagree) **[search]** |

---

## Part 3. The AI employees (72 roles)

Format for each role: **one-line**, **Hires**, **Jobs**, **Tier / who decides**, **Data and rails**,
**Region differences**, **Evidence it is doable**.

### A. For people and sole traders (consumer payment safety and admin)

#### 1. Card Dispute Helper
Prepares and files the paperwork when a card charge is wrong, unauthorised, or for goods never received.
- **Hires:** consumer, sole trader.
- **Jobs:** (1) read the statement / app screenshot and identify the disputed line (last 4 digits only); (2) classify: unauthorised, billing error, not received, not as described, duplicate, cancelled subscription still billed; (3) check the merchant-first step and draft the merchant contact; (4) calculate the legal and scheme deadlines (Reg Z 60 days from statement, Reg E 60 days, scheme 120 days typical, RBI shadow-reversal TAT) and set reminders; (5) build the evidence pack (receipts, tracking, emails, cancellation proof); (6) draft the bank dispute letter / in-app text; (7) track provisional credit and the bank's answer; (8) prepare the next step if refused (re-present, ombudsman); (9) for UK credit cards, check Consumer Credit Act s.75 (purchases over £100) as an alternative route.
- **Tier A.** She submits; the issuer decides.
- **Data and rails:** statements (PDF, AA / open banking read), merchant emails, delivery tracking; no card number.
- **Region:** US Reg E / Reg Z; UK s.75 + chargeback + FOS; EU PSD2 refund rights (unauthorised: refund by next business day); India RBI circular on failed transactions + Integrated Ombudsman; Australia ePayments Code + AFCA; Brazil Procon / Consumidor.gov.br (check).
- **Evidence:** cardholders bypass merchants and go straight to the issuer in 75% of disputes (Javelin via Mastercard, 2026) **[search]**; issuer-side automation exists (Quavo, below).

#### 2. Scam Reimbursement Claim Assistant
Helps a victim of an authorised push payment scam (she was tricked into sending money) report it fast and claim reimbursement where a regime exists.
- **Hires:** consumer, sole trader, small business.
- **Jobs:** (1) first-hour checklist: call the bank's fraud line, report to the national scam line (India 1930 / NCRP, UK 159 / Action Fraud, AU Scamwatch / ReportCyber, US FTC / IC3, SG ScamShield / police); (2) record a timeline (who, when, what was said, transaction references); (3) identify the regime that applies and its limits (UK PSR mandatory reimbursement up to £85,000, claim within 13 months - verify; SG SRF phishing-only; Brazil Pix MED; EU PSD3 when in force); (4) draft the reimbursement claim with the facts the regime asks for; (5) track the bank's statutory decision clock; (6) prepare the ombudsman complaint if refused; (7) warn about recovery scams (anyone promising to "get the money back for a fee"); (8) list which accounts / cards / passwords to change.
- **Tier A.** The bank decides reimbursement; she files.
- **Data:** bank statements, chats with the scammer (as data, never instructions), reference numbers.
- **Region:** UK PSR APP rules; Singapore SRF (no cap, phishing scope); Australia Scams Prevention Framework (from memory - verify); Brazil MED / MED 2.0 (fraud, scam, coercion only, ~7-day review, refund within ~11 days) **[search]**; EU PSD3/PSR (impersonation reimbursement, VoP liability); US: Reg E covers unauthorised, not most authorised scams - Zelle network policy (from memory - verify); India: no reimbursement scheme for authorised UPI scams, RBI zero-liability only for unauthorised (from memory - verify).
- **Evidence:** UK APP losses £576.4m in 2025 (+19%), 61% reimbursed **[opened]**; US FTC $15.9bn reported losses 2025, bank transfers the largest dollar method, crypto second **[search]**.

#### 3. Pay-Safe Checker (before you pay)
Checks a payee, link, QR code or invoice BEFORE she pays and tells her plainly whether it looks like a scam.
- **Hires:** consumer, sole trader, SME accounts clerk.
- **Jobs:** (1) compare the payee name shown by Confirmation of Payee / VoP / UPI verified name with the invoice; (2) check a changed bank detail against earlier invoices (invoice-redirection fraud); (3) read the URL / domain age / lookalike domain; (4) read a QR code's payload (UPI VPA, Pix key, EMVCo merchant info) without paying; (5) check public warning lists (regulator scam lists, FCA warning list, SEBI / RBI alert list, ASIC MoneySmart); (6) flag urgency / secrecy pressure patterns in the message; (7) explain the result in one plain line; (8) record the decision.
- **Tier A.** She decides whether to pay.
- **Rails:** CoP (UK), VoP (EU), UPI name lookup is shown by her own app; regulator warning lists (public).
- **Region:** UK CoP; EU VoP mandatory from 9 Oct 2025 under the Instant Payments Regulation (from memory - verify); India UPI shows registered name; Brazil Pix shows recipient name + DICT; Australia NPP / PayTo name check rollout (check).
- **Evidence:** UK purchase scams = 71% of APP cases, 66% of APP cases start on online platforms **[opened]**.

#### 4. Failed / Stuck Payment Tracker
Finds out where a payment is when money left her account but did not arrive, and pushes the right party within the right time.
- **Hires:** consumer, sole trader, SME.
- **Jobs:** (1) read the transaction reference (UTR, RRN, end-to-end id, UETR); (2) explain the status and the rule-book deadline (India RBI TAT harmonisation: auto-reversal T+1 for UPI/IMPS failures with compensation per day of delay - verify; SEPA Instant 10 s; FedNow; SWIFT gpi tracker); (3) draft the complaint to the sending bank with the right reference; (4) for SWIFT, read the gpi status / ask the bank for camt.029 / MT199 trace; (5) compute any compensation owed (India per-day compensation); (6) track and escalate to ombudsman; (7) detect duplicates.
- **Tier A.**
- **Rails:** bank statements, AA / open banking reads; SWIFT gpi Tracker access is the bank's (she asks the bank).
- **Region:** India RBI TAT circular + UPI dispute (UDIR); EU SEPA rulebooks; UK Faster Payments; Brazil Pix (instant, refund via MED only for fraud); global SWIFT gpi.
- **Evidence:** RBI ombudsman notes failed digital payments as a continuing burden **[search]**.

#### 5. Subscriptions and Mandates Manager
Lists every recurring charge, mandate and autopay she has, and prepares cancellations.
- **Hires:** consumer, sole trader, SME.
- **Jobs:** (1) find recurring charges from statements (card-on-file, e-mandates, UPI Autopay, Pix Automático, PayTo, SEPA direct debits, app-store subscriptions); (2) show cost per month / year and price rises; (3) remind before free trials end and before renewal; (4) draft cancellation emails / show the exact cancellation path; (5) for SEPA DD, compute the 8-week no-questions refund window; (6) draft a mandate revocation to the bank; (7) check that the charge stopped next cycle; (8) dispute (hand to role 1) if it did not.
- **Tier A.** She cancels.
- **Rails:** statements, AA / open banking; UPI Autopay / e-mandate lists visible in her own app.
- **Region:** EU SEPA DD refund 8 weeks / 13 months unauthorised; India RBI e-mandate rules (pre-debit notification, AFA above limit - verify); Brazil Pix Automático (authorisation via Open Finance, cancel any time) **[search]**; US FTC click-to-cancel rule was vacated by a court in 2025 (from memory - verify), state auto-renewal laws apply; Australia PayTo.
- **Evidence:** consumer subscription apps exist (Rocket Money in US, from memory - verify); Brazil Pix Automático adoption **[search]**.

#### 6. Remittance Sender Assistant
Finds the cheapest safe way to send money home and prepares the transfer paperwork.
- **Hires:** consumer, migrant worker, sole trader paying family abroad.
- **Jobs:** (1) compare total cost (fee + FX margin vs mid-market) for her corridor across providers; (2) check the provider's licence in her country (public register); (3) explain receive options (bank, mobile wallet, cash pick-up); (4) prepare the KYC documents list and purpose code; (5) compute tax / reporting thresholds (India LRS USD 250k + TCS, US no tax to sender but recipient-country rules); (6) reminders for regular transfers when the rate is good; (7) check the receiver details are complete (IBAN, IFSC, mobile money number); (8) track the transfer and the provider's cancellation window.
- **Tier A.** She sends from her own provider app.
- **Data:** World Bank Remittance Prices Worldwide data (open data), provider price pages.
- **Region:** US Remittance Transfer Rule: pre-payment disclosure and 30-minute cancellation (from memory - verify); EU Cross-border Payments Regulation; UAE exchange houses (CBUAE); India LRS / FEMA, inward FIRC; Kenya / Nigeria mobile money receive; Mexico SPEI / DiMo; Philippines e-wallets.
- **Evidence:** global average cost of sending $200 was 6.49% in Q1 2025 (SDG target 3%), sub-Saharan Africa 8.78% **[search]**; Wise and others publish comparisons (from memory - verify).

#### 7. Card Fees and FX Checker
Audits her card / wallet statements for foreign-exchange mark-ups, dynamic currency conversion and hidden fees.
- **Hires:** consumer, traveller, sole trader.
- **Jobs:** (1) list every fee line; (2) compute the FX mark-up vs the reference rate on the date; (3) spot dynamic currency conversion (paying in her home currency abroad); (4) compare against her card's published tariff; (5) draft a fee reversal request where a fee broke the tariff; (6) suggest cheaper settings ("always pay in local currency"); (7) yearly fee summary.
- **Tier A.**
- **Region:** EU Cross-Border Payments Regulation requires DCC mark-up disclosure vs ECB rate (from memory - verify); India forex mark-up + TCS on overseas card spend (check current rule); US no rule on DCC.
- **Evidence:** EU regulation on currency conversion transparency exists (from memory - verify).

#### 8. Wallet and Prepaid Card Admin
Keeps track of her e-wallets, prepaid / gift cards and stored balances, their limits and expiry.
- **Hires:** consumer, small trader.
- **Jobs:** (1) list wallets, balances, KYC tier and monthly limits; (2) remind before balance / gift-card expiry; (3) prepare the documents to upgrade KYC; (4) draft closure / balance refund requests; (5) flag dormant accounts; (6) explain what protection a wallet has (safeguarding vs deposit insurance); (7) track wallet disputes.
- **Tier A.**
- **Region:** India PPI master direction (min-KYC vs full-KYC, limits); EU / UK e-money safeguarding (not deposit-insured); US pass-through FDIC insurance only when records are right (Synapse lesson: ~$85m missing in FBO accounts) **[search]**; China SVF; Kenya M-Pesa tiers.
- **Evidence:** Synapse collapse and FDIC custodial-account recordkeeping proposal **[search]**.

#### 9. Payments Complaint and Ombudsman Escalation Drafter
Turns any payment problem that a firm did not fix into a correct, on-time escalation to the right ombudsman or regulator portal.
- **Hires:** consumer, sole trader, SME.
- **Jobs:** (1) pick the right body (RBI Integrated Ombudsman, UK FOS, AFCA, CFPB portal, EU national ADR / FIN-NET, Brazil BCB / Consumidor.gov.br, SG FIDReC, HK FDRC, Kenya CBK, Nigeria CBN CPD); (2) check eligibility (waited the firm's final response window: e.g. UK 8 weeks, India 30 days); (3) assemble the timeline and evidence; (4) draft the complaint in the body's format and word limits; (5) compute compensation asked (where rules set it); (6) track replies and deadlines; (7) prepare the appeal.
- **Tier A.**
- **Evidence:** RBI ombudsman 13.34 lakh complaints FY25 (+13.55%), credit cards second largest **[opened]**; CFPB 6.6m complaints 2025 **[search]**.

#### 10. Mobile Money Helper
Helps a mobile-money user with reversals, limits, agent issues and statements.
- **Hires:** consumer, market trader, small shop (Kenya, Tanzania, Ghana, Uganda, Nigeria, Bangladesh bKash, Pakistan JazzCash, Philippines GCash).
- **Jobs:** (1) draft a wrong-number reversal request with the transaction code; (2) explain tier limits and charges, compute the cheapest way to send; (3) produce a statement summary for a loan / landlord; (4) warn on common SIM-swap / fake-reversal SMS scams; (5) track a pending reversal; (6) list nearby agent options (public data); (7) escalate to the regulator's consumer desk.
- **Tier A.**
- **Rails:** her own statements (SMS / PDF), M-Pesa / operator public tariff tables.
- **Evidence:** 2.3bn registered accounts, $2tn value 2025, fraud "remains widespread" **[opened]**.

#### 11. Crypto Holder Records and Tax Assistant
Keeps a clean record of a person's crypto buys, sells, swaps and transfers and prepares tax schedules for an accountant.
- **Hires:** consumer, sole trader, accounting firm (on behalf of clients).
- **Jobs:** (1) import exchange CSVs / APIs (read-only keys) and public wallet addresses; (2) match transfers between own wallets; (3) compute cost basis by the country's method (FIFO, share pooling UK, average); (4) classify staking, airdrops, mining as income where the rules say so; (5) produce the schedule (US Form 8949 / 1099-DA reconciliation, UK SA108, India Schedule VDA with 30% and TDS credit, AU CGT); (6) flag missing cost basis; (7) reconcile exchange-issued tax forms; (8) remind deadlines.
- **Tier B** (the accountant / taxpayer signs and files).
- **Region:** US 1099-DA from 2025 transactions; EU DAC8 from 2026; OECD CARF (from memory - verify all); India s.115BBH 30% + 1% TDS s.194S; Japan miscellaneous income; Germany 1-year holding exemption (from memory - verify).
- **Evidence:** crypto tax software (Koinly, CoinTracker - from memory - verify).

#### 12. Crypto Wallet Safety Checker
Checks addresses, contracts and approvals before she sends or signs, and spots crypto scams.
- **Hires:** consumer, small business holding crypto.
- **Jobs:** (1) check a receiving address against public sanctions lists (OFAC SDN addresses) and public scam reports; (2) read a token contract / approval request and explain what it allows; (3) list her outstanding token approvals and draft revocation steps; (4) check the network chosen matches the receiver (wrong-network loss); (5) detect "recovery service" and "pig-butchering" patterns in chats; (6) checklist for seed-phrase safety (never typed anywhere, never shared - the AI never asks for it); (7) prepare a police / exchange report after a theft with on-chain trace links.
- **Tier A.** She signs; the AI never touches keys.
- **Rails:** public blockchain explorers / node APIs, OFAC list.
- **Evidence:** illicit crypto volume $154bn in 2025 with stablecoins 84% of illicit volume; $3.4bn stolen (Chainalysis) **[search]**; FTC: investment scams ~half of US losses **[search]**.

### B. For merchants and small businesses (accepting and paying)

#### 13. Chargeback Representment Agent (merchant side)
Fights chargebacks the merchant should win, on time, with the evidence the scheme rules require.
- **Hires:** e-commerce merchant, SaaS, travel, marketplace seller, PSP (for its merchants).
- **Jobs:** (1) pull new disputes from the PSP; (2) read the reason code (Visa 10.x/13.x, Mastercard 48xx, Amex, RuPay, UnionPay) and the deadline; (3) decide-to-fight recommendation (win odds vs amount vs fee) for her approval; (4) gather evidence (order, IP / device, delivery proof, log-ins, terms accepted, prior undisputed transactions for Visa Compelling Evidence 3.0); (5) draft the rebuttal letter; (6) submit through the PSP on her approval; (7) track pre-arbitration and arbitration decisions and fees; (8) win-rate report by reason code; (9) feed losses to prevention (role 14).
- **Tier A/B.** Merchant (or PSP analyst) approves each submission; the issuer / scheme decides.
- **Rails:** Stripe / Adyen / Checkout / Razorpay / PayU / Cashfree dispute APIs, Shopify orders, courier APIs.
- **Region:** scheme rules are global; RuPay / NPCI dispute timelines in India; UnionPay; local schemes (Cartes Bancaires, Elo).
- **Evidence:** 261m chargebacks / $33.8bn in 2025, forecast 324m by 2028; merchant cost $128 per chargeback; ~45% fraudulent (first- or third-party) (Mastercard / Datos / Javelin) **[search]**; Chargeflow ($35m Series A, 15,000+ merchants, success-based fee), Justt ($30m Dec 2024; Flows Nov 2026) **[search]**.

#### 14. Chargeback and Fraud-Ratio Prevention Manager
Keeps the merchant's dispute and fraud ratios under scheme thresholds before penalties start.
- **Hires:** merchant, PSP, acquirer.
- **Jobs:** (1) compute VAMP ratio (fraud + disputes on CNP / settled transactions) and Mastercard ECM / EFM ratios monthly and daily; (2) forecast breaching thresholds; (3) recommend pre-dispute tools (Visa RDR / Order Insight, Mastercard Ethoca / Consumer Clarity) and refund-before-dispute rules for her approval; (4) find the top causes (descriptor confusion, delivery delay, subscription cancellation friction); (5) draft a clearer billing descriptor and receipt; (6) detect card-testing / enumeration bursts; (7) produce the remediation plan acquirers ask for.
- **Tier A/B.**
- **Region:** VAMP thresholds: acquirer Excessive 70 bps from June 2025, Above Standard 50 bps from Jan 2026; merchant Excessive 220 bps (150 bps in LAC), dropping to 150 bps in several regions from Apr 2026; enumeration 20% with a 300,000 floor (sources disagree - verify with Visa) **[search]**.
- **Evidence:** Visa VAMP fact sheet 2025 **[search]**.

#### 15. Payment Acceptance Setup Assistant
Helps a small business choose and open a payment gateway / POS / QR and collect the onboarding documents.
- **Hires:** sole trader, SME, NGO, new e-commerce store.
- **Jobs:** (1) compare PSPs on fees, settlement speed, methods (cards, UPI, Pix, wallets, BNPL), country coverage; (2) build the KYB document pack (registration, tax id, beneficial owners, bank proof, website policies); (3) check the website has the policies schemes / PSPs require (refund, privacy, terms, contact, prices in currency); (4) explain MCC and prohibited / restricted business lists; (5) fill the application drafts; (6) track approval and reserve conditions; (7) set up payment links / QR / soundbox; (8) test a live small payment checklist.
- **Tier A.** The PSP decides.
- **Region:** India PA guidelines (only RBI-authorised PAs; merchant KYC / CKYC); EU PSD2 + SCA; Brazil Pix keys + subadquirentes; US ISO / payfac; Kenya Lipa na M-Pesa till / paybill; Gulf: CBUAE / SAMA licensed PSPs.
- **Evidence:** PSP self-serve onboarding is common; AI KYB agents exist on the PSP side (role 26).

#### 16. Payments Reconciliation Clerk (SME)
Matches every order, payment, refund, fee and payout across gateways, marketplaces and the bank.
- **Hires:** SME, D2C brand, marketplace seller, accounting firm.
- **Jobs:** (1) pull settlement reports (gateway, marketplace, wallet, UPI / Pix collections, BNPL); (2) match to orders / invoices and to the bank payout; (3) explain the gap (fees, GST / VAT on fees, chargebacks, reserves, FX, rolling holds, TCS / TDS withholding); (4) flag missing payouts and late settlements; (5) produce journal entries for her accountant; (6) compute effective cost of acceptance per method; (7) alert on duplicate refunds; (8) month-end pack.
- **Tier A** (her accountant posts / signs).
- **Rails:** PSP APIs, marketplace seller APIs (Amazon SP-API, Flipkart, Shopify Payments), bank statements via AA / open banking, ledger (QuickBooks, Xero, Tally, Zoho).
- **Region:** India GST on MDR + TCS by e-commerce operators (s.52 CGST) + TDS 194-O; EU VAT on fees reverse charge; US 1099-K thresholds (from memory - verify).
- **Evidence:** End Close (payment reconciliation agent, $3.5m seed Nov 2026), Fazeshift (AR agents incl. payment reconciliation, $22m) **[search]**.

#### 17. Merchant Fee and Statement Auditor
Reads the acquirer statement and shows what the business really pays and where it overpays.
- **Hires:** retailer, restaurant, hotel, SME.
- **Jobs:** (1) decode statement lines (interchange, scheme fees, markup, non-qualified surcharges); (2) compute effective rate by card type; (3) compare against the contract price; (4) find downgrades (missing Level 2/3 data, late settlement, AVS); (5) check surcharging is legal and correctly disclosed; (6) model switching to IC++ or another provider; (7) draft a renegotiation letter; (8) track the promised price next month.
- **Tier A.**
- **Region:** EU IFR caps 0.2% debit / 0.3% credit consumer cards (from memory - verify) and surcharge ban on consumer cards; UK caps on domestic; US Durbin debit cap, state surcharge laws, Visa/MC surcharge rules; India zero MDR on RuPay debit / UPI P2M (from memory - verify); Australia RBA surcharging rules (under review - check).
- **Evidence:** statement-audit consultancies exist (from memory - verify).

#### 18. PCI DSS Compliance Assistant (merchant)
Works out which PCI self-assessment the business needs and prepares the evidence.
- **Hires:** merchant, SaaS, small service provider.
- **Jobs:** (1) map how card data flows (hosted page, iframe, direct post, API, POS); (2) pick the SAQ (A, A-EP, B-IP, C-VT, D); (3) produce the evidence list (scripts inventory, ASV scan reports, policies); (4) track quarterly scans and annual dates; (5) draft policies; (6) check the new e-commerce script requirements (6.4.3 / 11.6.1) and the SAQ A eligibility criterion; (7) answer the acquirer's compliance request.
- **Tier B** (the merchant officer attests; a QSA signs a ROC).
- **Evidence:** 51 of 64 v4.0 requirements were future-dated and became mandatory 31 Mar 2025; SAQ A changes (PCI SSC) **[search]**.

#### 19. Failed-Payment Recovery Assistant (dunning)
Recovers subscription and invoice payments that failed, without spamming customers.
- **Hires:** SaaS, subscription box, gym, school, utility, NGO (recurring donations).
- **Jobs:** (1) classify decline codes (insufficient funds, expired card, do-not-honour, SCA required); (2) set a retry schedule within scheme retry limits; (3) draft customer reminders with a pay link / UPI / Pix QR; (4) prompt card updater / network token use (via PSP); (5) recommend switching mandates (UPI Autopay, Pix Automático, SEPA DD); (6) report recovered revenue; (7) stop retries on hard declines (scheme rules penalise excessive retries).
- **Tier A** (rules approved by the business; the PSP retries).
- **Region:** Visa / Mastercard retry limits (from memory - verify); India e-mandate AFA rules; EU SCA (MIT exemptions).

#### 20. Marketplace and Platform Payout Operations
Runs the paperwork of paying sellers / drivers / creators on a platform.
- **Hires:** marketplace, gig platform, creator platform, fintech.
- **Jobs:** (1) compute each payee's payout statement (gross, commission, refunds, holds, tax withheld); (2) check payee KYC complete before payout eligibility; (3) prepare the payout file for her approval; (4) handle failed payouts (wrong account, name mismatch); (5) answer payee "where is my money" questions; (6) prepare year-end tax forms (US 1099-K / 1099-NEC, EU DAC7, India TCS / 194-O certificates); (7) reconcile the platform's escrow / nodal / FBO account; (8) flag payees on sanctions lists for human review.
- **Tier A/B.** A finance human releases the payout file.
- **Region:** India escrow / nodal account rules for PAs; EU DAC7 platform reporting; US 1099-K; Brazil split payments (Pix); Kenya B2C M-Pesa.

#### 21. Cross-border Receivables and Export Proceeds Assistant
Helps exporters and freelancers get paid from abroad cheaply and keep the papers regulators ask for.
- **Hires:** freelancer, exporter, software services firm, accounting firm.
- **Jobs:** (1) compare receiving accounts (bank SWIFT, Wise / Payoneer / Skydo-type collection accounts, PayPal) on total cost; (2) produce the invoice with the right purpose code and bank details; (3) obtain and file inward remittance certificates (India e-FIRC / FIRA); (4) track export realisation deadlines (India FEMA / EDPMS, 15 months - verify); (5) reconcile FX received vs invoice; (6) GST zero-rating / LUT reminders (India), VAT reverse-charge wording (EU); (7) chase late foreign clients.
- **Tier A** (the bank / AD dealer and her CA decide / certify).
- **Region:** India FEMA + RBI EDPMS + softex; China SAFE rules on FX receipts (check); Brazil câmbio contract; Nigeria CBN export proceeds repatriation (check); EU / UK freer.

#### 22. Corporate Card and Spend Program Admin
Runs the admin of a small company's corporate / virtual cards.
- **Hires:** SME, startup, NGO.
- **Jobs:** (1) draft the card policy and limits per role; (2) prepare card requests for approval; (3) match card spend to receipts; (4) chase missing receipts; (5) flag policy breaches and duplicate subscriptions; (6) code to the ledger; (7) prepare limit-change requests for the admin's tap; (8) offboarding checklist (cancel cards of leavers).
- **Tier A.** The admin issues / freezes cards in the provider console.
- **Rails:** Ramp, Brex, Expensify, Pleo, RazorpayX, Spendesk APIs.
- **Evidence:** Brex describes AI-native multi-agent onboarding / spend flows **[search]**.

#### 23. E-commerce Fraud Rules Assistant
Helps a merchant tune fraud rules and 3-D Secure so fewer good orders are declined and fewer bad ones pass.
- **Hires:** e-commerce merchant, PSP.
- **Jobs:** (1) analyse past orders vs chargebacks / fraud reports; (2) propose rules (velocity, BIN country vs IP, mismatched names) for her approval; (3) estimate false-decline cost; (4) recommend SCA exemptions (TRA, low value) where the PSP supports them; (5) detect card-testing attacks; (6) prepare the manual-review queue summary; (7) monthly fraud report.
- **Tier A/B.** The merchant's fraud manager switches rules on.
- **Rails:** Stripe Radar, Adyen RevenueProtect, Sift, Signifyd APIs (from memory - verify).
- **Region:** EU / UK SCA mandatory; India AFA on cards; US liability shift via 3DS.

#### 24. Crypto and Stablecoin Acceptance Assistant
Helps a business decide whether and how to accept stablecoins / crypto, and keeps the books right.
- **Hires:** merchant, exporter, freelancer, NGO.
- **Jobs:** (1) compare licensed acceptance providers by country; (2) explain settlement options (auto-convert to fiat vs hold); (3) check the legal position in her country (accepted, restricted, banned); (4) set up accounting treatment and tax notes; (5) reconcile received payments to invoices with on-chain hashes; (6) refund policy for wrong-amount / wrong-network payments; (7) travel-rule information requests from the provider.
- **Tier A.**
- **Region:** EU MiCA (EMT / ART rules; e-money tokens need EMI / bank issuer); US GENIUS Act; HK Stablecoins Ordinance; UAE CBUAE Payment Token Services (Dirham tokens); China mainland ban; India tax + FIU registration of provider.

### C. Payment firm, issuer, acquirer and bank operations

#### 25. Card Issuing Program Manager Assistant
Prepares and keeps current the documents and controls of a card programme (bank, neobank, fintech).
- **Hires:** issuer bank, fintech issuer, BIN sponsor, BaaS provider.
- **Jobs:** (1) draft programme documents (cardholder terms, fee schedule, disclosures, network product forms); (2) track scheme mandates and their dates per BIN range; (3) maintain the fee and limits matrix; (4) prepare BIN sponsor / partner bank review packs; (5) monitor complaints by programme; (6) produce monthly programme KPIs (active cards, spend, disputes, fraud bps); (7) prepare scheme quarterly operating certificates (QOC / QMR) for a human to submit.
- **Tier B.** The programme manager signs and submits.
- **Rails:** processor data (Marqeta, Galileo, Nium, Thales, M2P), scheme portals (human login).
- **Region:** US CARD Act / Reg Z / Reg E / Durbin; EU PSD2 + IFR; India RBI credit card / debit card master direction (2022, from memory - verify); Brazil BCB card rules; Gulf CBUAE.

#### 26. Merchant Onboarding (KYB) Analyst Assistant
Collects and checks everything an acquirer / PSP needs before a human approves a merchant.
- **Hires:** acquirer, payfac, PSP, marketplace.
- **Jobs:** (1) gather documents and data from the applicant; (2) verify company registry, tax id, directors and UBOs against official registries; (3) screen principals against sanctions / PEP / adverse media; (4) check MATCH / TMF (Mastercard / Visa terminated-merchant lists) via the acquirer's access; (5) review the website (products vs declared MCC, prohibited items, policies); (6) compute a risk score from the acquirer's policy; (7) write the underwriting memo with the reasons; (8) list missing items for the applicant; (9) set the review date.
- **Tier B.** The underwriter approves / declines and sets reserves.
- **Rails:** company registries (Companies House, MCA21, SEC EDGAR, Receita Federal CNPJ, ACRA), KYB data vendors, sanctions lists, scheme MATCH.
- **Region:** EU AMLR UBO registers; India PA guidelines + CKYC; Brazil CNPJ; Gulf trade licence registries; US state SOS + FinCEN BOI (status changed in 2025 - from memory - verify).
- **Evidence:** Arva AI (YC) KYB agents claim 80% ops cost cut; Taktile KYB agents + KYBench; Vivox AI merchant KYB; Worth ($30m) onboarding / underwriting; Moxo ("underwriters keep every call") **[search]**.

#### 27. Merchant Risk Monitoring Analyst
Watches live merchants for fraud, transaction laundering and scheme-rule breaches after onboarding.
- **Hires:** acquirer, PSP, payfac.
- **Jobs:** (1) daily scorecards (volume spikes, refund / dispute rates, ticket size drift, off-hours); (2) website / product change monitoring (MCC drift, prohibited products, transaction laundering); (3) VAMP / ECM exposure per merchant (role 14 for the acquirer portfolio); (4) recommend reserve / hold / review for a human; (5) prepare scheme brand-protection responses (Visa VIRP / Mastercard BRAM letters); (6) draft merchant contact asking for invoices / shipping proof; (7) periodic re-KYB reminders; (8) closure memo draft.
- **Tier B.** A risk human decides holds, reserves and termination.
- **Evidence:** StackAI / Persistent agentic merchant-risk offers **[search]**.

#### 28. Acquirer Dispute Operations Analyst
Handles disputes at volume inside an acquirer / PSP: deadlines, merchant notices, pre-arbitration files.
- **Hires:** acquirer, PSP.
- **Jobs:** (1) ingest network dispute feeds (Visa VROL, Mastercom); (2) notify the merchant with deadline and needed evidence; (3) check merchant evidence against reason-code requirements; (4) prepare responses for analyst approval; (5) compute liability and debit / credit entries for approval; (6) track pre-arb / arbitration fees and deadlines; (7) scheme compliance-case preparation; (8) daily ageing report.
- **Tier B.** The analyst submits; the network / issuer decides.

#### 29. Issuer Dispute and Claims Investigator Assistant
Investigates cardholder and account-holder disputes inside a bank within the legal clocks.
- **Hires:** issuer bank, credit union, neobank, wallet issuer.
- **Jobs:** (1) open the case from the customer's words; (2) classify Reg E error vs Reg Z billing error vs scheme reason; (3) set statutory deadlines (provisional credit at 10 business days, 45 / 90-day resolution under Reg E; Reg Z 2 billing cycles / 90 days - verify) and RBI TAT; (4) gather authorisation logs, device, 3DS, location, prior disputes; (5) draft the investigation summary with recommended outcome; (6) draft the chargeback to the network for analyst approval; (7) draft customer letters (provisional credit, final decision with reasons); (8) first-party-fraud ("friendly fraud") pattern flags; (9) ageing / regulator reports.
- **Tier B.** A human investigator decides provisional credit and the outcome.
- **Region:** US Reg E / Reg Z; UK FCA DISP + PSRs 2017; EU PSD2 Art. 73 (refund unauthorised by next business day); India RBI customer liability circular (zero liability if reported in 3 days) + TAT; Brazil Pix MED for fraud; Australia ePayments Code.
- **Evidence:** Quavo (ARIA AI investigator, Reg E / Reg Z / Visa / MC / Nacha deadlines; 20-25% auto-resolution on low-complexity Reg E claims - vendor claim) **[search]**; issuers spend $9-10 per dispute (Mastercard) **[search]**.

#### 30. Card Operations Clerk
Handles the routine exceptions of the card lifecycle.
- **Hires:** issuer, processor, fintech.
- **Jobs:** (1) work exception queues (embossing file rejects, address returns, undelivered cards); (2) tokenisation exceptions (Apple Pay / Google Pay provisioning failures) - investigation summaries; (3) reissue lists after a compromise alert (CAMS / Visa CAMS alerts) prepared for approval; (4) limit-change requests checked against policy; (5) card closure confirmations; (6) dormant card reports; (7) prepare daily ops MI.
- **Tier A/B.** A human performs the card action in the processor console.

#### 31. Payment Operations Exceptions Analyst (bank payments)
Repairs, returns and investigates payments that the straight-through flow could not process.
- **Hires:** bank, PSP, EMI, remittance firm.
- **Jobs:** (1) read rejected / returned ISO 20022 messages and their reason codes (pacs.002, pacs.004, camt.056 / camt.029, camt.110 investigations); (2) propose the repair (missing BIC, invalid IBAN, unstructured address) for approval; (3) draft beneficiary-bank enquiries; (4) match returns to originals; (5) compute charges and back-value; (6) prepare recall requests; (7) daily queue-ageing and SLA report; (8) feed recurring errors to fix lists.
- **Tier B.** The operator releases the repaired payment.
- **Region:** SWIFT CBPR+ (structured / hybrid address only after 14 Nov 2026; Stop and Recall mandate Nov 2027; MT end-of-life Nov 2027) **[search]**; SEPA rulebooks (R-transactions); Fedwire ISO 20022 (from memory - verify); UPI / IMPS / NEFT returns; Pix devolução.
- **Evidence:** SWIFT open-source address-structuring tool **[search]**.

#### 32. Settlement and Reconciliation Analyst (payment firm)
Reconciles scheme, clearing-house and bank settlements against the firm's ledger every day.
- **Hires:** acquirer, issuer, PSP, EMI, remittance company, mobile-money operator.
- **Jobs:** (1) load scheme settlement reports (Visa VSS, Mastercard GCMS / IPM, NPCI raw data, Pix DICT / SPI statements, ACH / Nacha files); (2) three-way match: scheme vs ledger vs bank; (3) explain breaks (timing, FX, fees, reversals, chargebacks, late presentments); (4) nostro / vostro reconciliation; (5) unmatched-item ageing and write-off proposals for approval; (6) fee invoice reconciliation (role 46); (7) month-end evidence for auditors.
- **Tier B.** A controller approves adjustments and write-offs.
- **Evidence:** Fragment ($12m, double-entry ledger controls for payments reconciliation), Xelix ($160m AP agentic, statement reconciliation), Safebooks ($15m) **[search]**.

#### 33. Payments Treasury and Liquidity Analyst
Forecasts the money a payment firm needs at each scheme, bank and corridor, so payments do not fail.
- **Hires:** PSP, remittance firm, EMI, crypto exchange (fiat side), marketplace.
- **Jobs:** (1) daily cash position across settlement and nostro accounts; (2) forecast prefunding needs per corridor / partner (holidays, cut-offs); (3) propose top-up transfers for a treasurer's approval; (4) scheme collateral requirements tracking; (5) FX exposure summary and hedge suggestions for the treasurer; (6) intraday liquidity alerts on RTGS / instant rails; (7) concentration / bank counterparty limits; (8) treasury report.
- **Tier B.** The treasurer moves money.
- **Rails:** bank APIs / SWIFT MT940/camt.053, partner balances, FX rate feeds.

#### 34. Safeguarding and Client-Money Officer Assistant
Prepares the daily safeguarding reconciliation, the resolution pack and the regulator returns of a payment / e-money firm.
- **Hires:** EMI, payment institution, wallet, remittance company, BaaS fintech, marketplace with escrow.
- **Jobs:** (1) compute relevant funds owed to customers vs money held in safeguarding / FBO / escrow accounts each business day; (2) explain shortfalls / excesses and propose corrections for approval; (3) maintain the resolution pack (account letters, records to return funds); (4) prepare the monthly safeguarding return (UK REP027 within 15 business days of month-end) for a human to submit; (5) prepare the annual safeguarding audit evidence; (6) check permissible investments; (7) for BaaS, reconcile the fintech's sub-ledger to the bank's FBO balance and flag mismatches; (8) breach notification draft.
- **Tier B.** The safeguarding officer / director signs; auditors opine.
- **Region:** UK CASS 15 + CASS 10A + SUP 16.14A (PS25/12) **[search]**; EU EMD2 / PSD2 Art. 10 (PSD3 replaces); US state MTL permissible investment rules + FDIC custodial-account recordkeeping proposal (post-Synapse) **[search]**; India PPI escrow / PA nodal escrow rules; Singapore PS Act safeguarding; Kenya trust accounts for mobile money.
- **Evidence:** Synapse ~$85m shortfall **[search]**; FCA rules from May 2026 **[search]**.

#### 35. Payment Fraud Analyst Assistant
Works fraud alerts on payments and accounts and prepares the analyst's decisions.
- **Hires:** bank, PSP, wallet, neobank, remittance firm.
- **Jobs:** (1) triage alerts (score, rule hit, device, behaviour, beneficiary newness); (2) build the case summary with the timeline; (3) draft customer contact scripts (confirm the payment, scam warning); (4) check the beneficiary against mule / fraud consortium data the firm subscribes to; (5) recommend release / hold for the analyst; (6) record APP-scam reimbursement assessment facts (role 2's institutional twin); (7) tune rule proposals; (8) daily fraud MI and loss reporting.
- **Tier B.** The analyst releases / blocks; the firm decides reimbursement.
- **Region:** UK PSR reimbursement + Faster Payments delays allowed for suspected fraud (from Oct 2024, from memory - verify); EU PSD3 fraud data sharing; India RBI MuleHunter.AI / NPCI fraud risk management (from memory - verify); Singapore SRF duties; Brazil BCB fraud data sharing + MED; Australia SPF.
- **Evidence:** UK Finance prevented £1.68bn unauthorised fraud 2025 **[opened]**; RBI DG said frauds per transaction rising since July 2025 **[search]**.

#### 36. Mule Account and Money-Laundering Investigator Assistant
Investigates accounts receiving and moving scam money, and drafts the report the MLRO decides to file.
- **Hires:** bank, PSP, wallet, mobile-money operator, VASP.
- **Jobs:** (1) build the flow graph (in / out, layering, rapid pass-through); (2) link accounts by device / IP / KYC overlaps; (3) gather KYC and transaction evidence; (4) draft the STR / SAR narrative; (5) prepare law-enforcement information requests and freeze requests for a human; (6) respond to inter-bank recall / fraud notices; (7) case closure memo.
- **Tier B.** The MLRO decides and files; a human freezes.
- **Region:** US FinCEN SAR (30 days); UK NCA SAR + DAML; EU FIUs under AMLR; India FIU-IND STR + I4C; Brazil COAF; Nigeria NFIU; Kenya FRC; Australia AUSTRAC SMR.
- **Evidence:** O*NET fraud-examiner tasks map one-to-one (analyse irregularities, prepare reports, recommend actions) **[opened]**.

#### 37. AML Transaction Monitoring Analyst Assistant (payments / MSB)
Clears transaction-monitoring alerts in a payment firm or money-service business.
- **Hires:** PSP, EMI, remittance company, MSB, BaaS bank.
- **Jobs:** (1) L1 alert review with documented reasoning; (2) customer risk-profile check (expected vs actual activity); (3) request-for-information drafts to customers; (4) escalate to L2 with summary; (5) periodic review (CDD refresh) reminders; (6) threshold / scenario tuning analysis; (7) QA sampling of closed alerts; (8) MI for the MLRO / board.
- **Tier B.** A human closes or escalates; the MLRO files.
- **Evidence:** see 38 for alert-automation vendors.

#### 38. Sanctions Screening L1 Reviewer (payments)
Reviews sanctions-screening hits on payments and customers and documents why each is a false positive or must be escalated.
- **Hires:** bank, PSP, remittance company, VASP, trade-finance desk.
- **Jobs:** (1) compare the hit with the listed party (name, DOB, nationality, address, vessel IMO, BIC); (2) check the payment's other fields (purpose, ports, goods); (3) apply the firm's good-guy / whitelist rules; (4) write the disposition reason; (5) escalate likely true matches to L2 with evidence; (6) prepare licence / blocking report drafts for the human; (7) list-update impact analysis; (8) alert-quality metrics regulators ask for.
- **Tier B.** L2 / compliance decides block / reject; the institution reports.
- **Region:** OFAC (US), UN, EU consolidated list, UK OFSI, Canada SEMA, Australia DFAT, Singapore MAS TFS, India MHA / UAPA lists, UAE local terrorist list; secondary-sanctions exposure for Russia / Iran corridors.
- **Evidence:** false-positive rates 90-99% (Sayari, WorkFusion); WorkFusion "Tara" automates L1 sanctions payment alerts (>70% manual-review cut, vendor claim); SymphonyAI 92% fewer false positives at a Spanish bank **[search]**.

#### 39. Correspondent Banking and Nostro KYC Analyst
Prepares due diligence on respondent banks and payment partners.
- **Hires:** correspondent bank, payment bank, remittance firm, EMI using partner banks.
- **Jobs:** (1) collect and check the Wolfsberg CBDDQ / FCCQ; (2) review the respondent's licence, ownership, AML programme, sanctions exposure; (3) adverse-media research; (4) RMA / SWIFT relationship inventory review; (5) risk-rating memo; (6) periodic-review reminders; (7) nested-relationship / payable-through questions; (8) exit / de-risking impact note.
- **Tier B.** The correspondent-banking committee decides.
- **Evidence:** remittance de-risking keeps costs high (WB RPW) **[search]**.

#### 40. Cross-border Payments and ISO 20022 Message Specialist
Makes cross-border payment messages correct before they go out and explains the new ISO 20022 rules.
- **Hires:** bank, PSP, corporate treasury, remittance firm, fintech building on SWIFT.
- **Jobs:** (1) validate pacs.008 / pain.001 fields against CBPR+ / HVPS+ usage guidelines; (2) convert unstructured addresses to structured / hybrid (Nov 2026 rule); (3) map legacy MT103 fields to MX; (4) pre-validation of beneficiary account (SWIFT Payment Pre-validation, where the bank has it); (5) explain gpi tracker statuses; (6) prepare charges (OUR / SHA / BEN) explanations; (7) build test messages for certification; (8) purpose-code and regulatory-reporting codes per country (India purpose codes, China SAFE codes, UAE purpose of payment codes).
- **Tier A/B.**
- **Evidence:** SWIFT ISO 20022 migration milestones + free address-structuring tool **[search]**.

#### 41. Instant-Payment Scheme Participation Analyst
Prepares the documents, tests and reports for joining and staying compliant in a real-time payment scheme.
- **Hires:** bank, PSP, TPAP, EMI joining FedNow, RTP, Pix, UPI, SEPA Inst, NPP, PayNow / FAST, PromptPay, PayShap, SPEI.
- **Jobs:** (1) map the scheme rulebook into a requirement checklist; (2) prepare the participation application pack; (3) build conformance-test cases and record results; (4) track scheme change releases (e.g. UPI circulars, Pix regulation updates, EPC rulebook versions); (5) prepare mandatory reporting (availability, fraud, dispute stats); (6) draft operating procedures (24/7 support, dispute handling); (7) VoP / CoP implementation checklist.
- **Tier B.** Scheme officer submits; the operator approves.
- **Region:** NPCI UPI (market-share cap on TPAPs - deadline extended, check), BCB Pix regulation, EPC SCT Inst rulebook + EU IPR, Fed FedNow operating circular, NPPA, ABA Thailand, BSP InstaPay, BI-FAST.

#### 42. Open Banking / Open Finance Compliance and Integration Analyst
Keeps a bank's or a third party's open-banking obligations and integrations in order.
- **Hires:** bank (data holder / ASPSP), TPP / fintech (AISP / PISP), FIU / FIP in India, CDR accredited data recipient.
- **Jobs:** (1) registration / accreditation dossier drafts (FCA AISP/PISP, eIDAS QWAC tracking, CDR accreditation, Sahamati / RBI AA onboarding, Open Finance Brasil participant); (2) consent records and dashboard text review; (3) API availability / performance reporting prepared for submission; (4) incident / outage notice drafts; (5) map data fields to the standard (UK OB, Berlin Group, FDX, CDR, ReBIT AA, OFB); (6) consent-expiry and re-authentication reminders (UK 90-day rule changes, check); (7) data-minimisation review; (8) customer complaint analysis.
- **Tier B.**
- **Region:** UK OB; EU PSD2 -> PSD3/PSR (dashboard duty); US s.1033 enjoined + new proposal (Aug 2026) **[search]**; Australia CDR; India AA; Brazil Open Finance (166m+ consents) **[search]**; Nigeria (delayed launch) **[search]**; UAE / Saudi open finance; Canada consumer-driven banking.

#### 43. Payments Licensing and Regulatory Returns Preparer
Prepares licence applications, renewals and periodic returns of a payment / money-transmission firm for the officer who files.
- **Hires:** PSP, EMI, MTO, wallet, BaaS fintech, payment aggregator, VASP (see 60 for crypto).
- **Jobs:** (1) licence map: which licence in which state / country for which activity; (2) application dossier drafts (business plan, AML programme, governance, IT and outsourcing, safeguarding); (3) renewal and fee calendar; (4) periodic returns (US NMLS MSB call reports, state reports; UK FCA FSA056 / REP017 payments fraud report; EU national returns; RBI PA / PPI returns; MAS PS Act returns; Bank of Canada RPAA reports); (5) change-in-control / new director notifications; (6) regulator Q&A drafts; (7) evidence for regulator examinations.
- **Tier B.** The compliance officer / director signs and submits.
- **Region:** US 49-state MTL + NMLS; EU PSD2 passporting (PSD3 re-authorisation timing - check); UK FCA; India RBI PA / PPI / cross-border PA; Singapore MAS MPI/SPI; HK SVF; UAE CBUAE RPSCS; Brazil BCB IP authorisation; Canada RPAA; Nigeria CBN PSSP / MMO / switching licences; Kenya CBK PSP.

#### 44. Card Scheme Rules and Mandate Tracker
Reads every scheme bulletin and rule change and turns it into a dated to-do list for the firm.
- **Hires:** issuer, acquirer, PSP, processor.
- **Jobs:** (1) collect Visa Business News, Mastercard Global Operations Bulletins, Amex, Discover, UnionPay, RuPay, local schemes; (2) summarise what changes, for whom, by when; (3) map changes to the firm's products / systems; (4) create tasks and owners; (5) track evidence of compliance; (6) quarterly compliance status; (7) fines / non-compliance assessment exposure tracking.
- **Tier A/B.**
- **Evidence:** VAMP launched April / June 2025 with phase-ins - example of high-impact mandates **[search]**.

#### 45. Interchange and Scheme Fee Analyst
Checks that scheme fees and interchange charged to the firm are right, and models pricing.
- **Hires:** issuer, acquirer, PSP, large merchant.
- **Jobs:** (1) reconcile monthly scheme fee invoices to volumes; (2) find mis-billed fees and draft disputes to the scheme; (3) model interchange income (issuer) or cost (acquirer) under new rates; (4) check regulated caps (EU IFR, US Durbin, Australia RBA, India MDR); (5) merchant pricing proposals (IC++ / blended) for sales; (6) quarterly fee trend report.
- **Tier A/B.**

#### 46. Bank-Fintech / BaaS Partner Oversight Analyst
Helps a partner bank (or the fintech) run oversight of each fintech programme.
- **Hires:** sponsor bank, BaaS middleware, fintech.
- **Jobs:** (1) programme due-diligence file; (2) monthly KPI and complaint review per programme; (3) marketing / disclosure review (e.g. "FDIC-insured" claims); (4) sub-ledger to FBO reconciliation evidence (role 34); (5) AML / sanctions coverage checks of the fintech; (6) consent-order / enforcement-action requirement tracking; (7) annual review pack; (8) exit-plan readiness.
- **Tier B.** The bank's third-party risk committee decides.
- **Region:** US interagency third-party risk guidance (2023) + FDIC deposit-insurance misrepresentation rule (from memory - verify) + recordkeeping proposal **[search]**; India co-branding / digital lending rules; UK agents and distributors of EMIs; EU outsourcing guidelines / DORA.

#### 47. Payments Customer Support Agent
Answers customers of a PSP / wallet / remittance app within the firm's policy and hands decisions to staff.
- **Hires:** PSP, wallet, neobank, remittance company, mobile-money operator, crypto exchange.
- **Jobs:** (1) "where is my money" answers from the real transaction status; (2) explain fees, limits, holds, KYC requests; (3) collect dispute / complaint details and open the case; (4) refund requests prepared for staff approval; (5) scam-victim first response (role 2 path); (6) KYC document collection guidance (never passwords / OTP); (7) complaint logging with regulatory clocks; (8) hand-off summaries.
- **Tier A/B.** Staff decide refunds, unblocks, limit changes.
- **Evidence:** CFPB complaints doubled 2025 **[search]**; ticket deflection products common (from memory - verify).

#### 48. Payments Complaints Handling and Root-Cause Analyst
Runs the firm's regulatory complaint process and finds the causes.
- **Hires:** bank, PSP, EMI, MTO, VASP.
- **Jobs:** (1) classify complaints to the regulator's taxonomy; (2) track statutory response clocks (UK DISP 15 business days for payments / 35 days; India 30 days; CFPB portal 15 / 60 days - verify); (3) draft final responses for approval; (4) ombudsman case files; (5) root-cause analysis and trend reports; (6) Consumer Duty outcome evidence (UK); (7) regulator complaint returns (FCA DISP return, RBI, AFCA reporting).
- **Tier B.**

#### 49. Remittance Operations Officer Assistant (MTO)
Runs the daily operations of a money-transfer business: holds, payouts, partners, cancellations.
- **Hires:** money-transfer operator, exchange house, fintech remitter.
- **Jobs:** (1) work compliance-hold queues with summaries (role 37/38); (2) payout-partner failure handling and re-routing proposals; (3) cancellation / refund processing within rule windows for approval; (4) corridor rate and fee table updates prepared for approval; (5) receiver-bank detail validation per country; (6) partner settlement reconciliation; (7) consumer disclosures / receipts check (US Remittance Rule); (8) corridor performance reports (cost vs WB RPW benchmark).
- **Tier B.**
- **Region:** US Reg E subpart B + state MTL; EU PSD2; UAE CBUAE exchange houses / WPS; Philippines BSP; Nigeria CBN IMTO guidelines (FX rules changed 2024, check); India RDA / MTSS; PAPSS for Africa.

#### 50. Mobile Money Operations and Agent Network Analyst
Supports a mobile-money operator's agent network, float and reversals.
- **Hires:** mobile-money operator, agent aggregator, telco fintech, super-agent.
- **Jobs:** (1) agent float forecasting and rebalancing suggestions; (2) reversal request validation (both parties, time windows); (3) agent KYC / performance scorecards; (4) agent fraud pattern flags (split transactions, fake reversals); (5) trust-account reconciliation; (6) commission statements; (7) regulator returns drafts; (8) agent training material.
- **Tier B.**
- **Region:** Kenya CBK + NPS Act; Tanzania BoT; Ghana BoG; Nigeria CBN (PSB / MMO); Bangladesh BB MFS; Pakistan SBP branchless banking; Philippines BSP.
- **Evidence:** GSMA SOTIR 2026 **[opened]**.

#### 51. Payment Incident and Outage Reporting Assistant
Prepares major-incident notifications that payment firms must file within hours.
- **Hires:** bank, PSP, EMI, scheme participant, VASP.
- **Jobs:** (1) classify the incident against the regulator's criteria; (2) draft the initial / intermediate / final reports in the required template; (3) keep the incident timeline; (4) customer-communication drafts; (5) scheme notifications (UPI downtime reports, Pix incident reports); (6) post-incident review pack; (7) DORA major ICT incident register.
- **Tier B.** The incident manager files.
- **Region:** EU DORA (initial report within 4 h of classification / 24 h of detection - verify), UK FCA / PSR incident reporting, RBI cyber incident reporting (6 h, CERT-In), MAS (1 h notice - verify), HKMA, APRA CPS 230, Brazil BCB.

#### 52. Payments Security Compliance Analyst (service provider)
Prepares PCI DSS / PIN / 3DS / P2PE evidence for payment service providers.
- **Hires:** processor, PSP, payfac, tokenisation provider.
- **Jobs:** (1) scope and data-flow documentation; (2) control evidence collection for the QSA; (3) quarterly / semi-annual requirement calendar (e.g. targeted risk analyses, segmentation tests every 6 months for SPs); (4) policy drafts; (5) gap remediation tracking; (6) AOC distribution to clients; (7) scheme registration (Visa Global Registry, Mastercard SDP) renewals.
- **Tier B.** QSA signs ROC; officer signs AOC.

#### 53. Payments Integration and Testing Assistant
Helps a fintech's team integrate a payment API correctly and pass certification.
- **Hires:** fintech, SaaS adding payments, ISV, small bank.
- **Jobs:** (1) read the provider docs and produce an integration checklist; (2) generate sandbox test cases (success, decline codes, 3DS challenge, refunds, webhooks out of order, idempotency); (3) validate webhook signature handling; (4) map provider status codes to the app's states; (5) prepare scheme / NPCI / Pix certification test evidence; (6) go-live checklist; (7) monitor error rates after launch.
- **Tier A.**
- **Region:** NPCI UPI certification; BCB Pix homologação; EMV / scheme certification for terminals; Open banking conformance suites.

#### 54. Authorisation-Rate and Checkout Optimiser
Finds why good payments are declined and proposes fixes.
- **Hires:** merchant, PSP, subscription business.
- **Jobs:** (1) decline analysis by issuer, BIN, country, method, reason code; (2) propose network tokens, account updater, local acquiring, retries (within limits); (3) payment-method mix recommendations per country (UPI, Pix, iDEAL / Wero, Bizum, PayNow, PromptPay, M-Pesa, Boleto); (4) 3DS friction analysis; (5) A/B test plans; (6) revenue-impact estimates; (7) monthly report.
- **Tier A.**

#### 55. Fintech Marketing and Disclosure Compliance Reviewer
Checks fintech ads, app copy and terms for misleading payment / deposit-insurance / fee / crypto claims before launch.
- **Hires:** fintech, wallet, BaaS bank, crypto platform, BNPL.
- **Jobs:** (1) review copy against rules (deposit-insurance claims, "free", APR / fee disclosure, crypto risk warnings); (2) flag required disclaimers; (3) track approvals; (4) maintain an approved-claims library; (5) social-media / influencer post checks; (6) record evidence for regulators.
- **Tier B.** Compliance approves.
- **Region:** UK FCA financial promotions (s.21 approver, crypto promotion regime since Oct 2023); EU MiCA marketing rules; US UDAAP + FDIC sign / misrepresentation rule; India RBI / ASCI guidelines; Singapore MAS crypto advertising restrictions; Australia ASIC.

#### 56. Payment Firm Policy and Procedures Writer
Writes and keeps current the policies and procedure manuals payment regulators and partner banks require.
- **Hires:** startup PSP / EMI / MTO / VASP, BaaS fintech.
- **Jobs:** (1) policy set from a template map per licence (AML/CTF, sanctions, fraud, complaints, safeguarding, outsourcing, BCP, ICT risk, data protection); (2) align with the firm's real processes; (3) version control and annual review reminders; (4) board approval packs; (5) gap reports when rules change; (6) staff attestations tracking.
- **Tier B.** The board approves.

#### 57. G2P and Social-Transfer Payment Reconciliation Assistant
Helps government departments and NGOs check that benefit / cash-transfer payments reached the right people.
- **Hires:** government department, NGO, humanitarian agency, programme implementer bank.
- **Jobs:** (1) reconcile beneficiary list vs payment file vs bank / wallet credit confirmations; (2) explain failed credits (account closed, name mismatch, Aadhaar not seeded, wallet inactive); (3) prepare re-payment lists for approval; (4) duplicate-beneficiary checks; (5) sanctions screening of recipients where donors require it; (6) grievance case tracking; (7) donor / audit reports.
- **Tier A/B.** Programme officer approves payment files.
- **Region:** India DBT / PFMS / APBS; Brazil Bolsa Família via Caixa / Pix; Kenya Inua Jamii; Philippines 4Ps; Nigeria NASSP; humanitarian cash (CALP network standards - from memory - verify).

#### 58. Humanitarian Cash and Voucher Delivery Assistant
Helps an NGO pick and run a cash-delivery mechanism and keep donor-compliant records.
- **Hires:** NGO, UN agency implementing partner.
- **Jobs:** (1) compare delivery options (mobile money, prepaid cards, bank, agent cash-out, vouchers) by cost, reach and risk; (2) FSP due-diligence pack; (3) data-protection and consent forms for recipients; (4) payment schedules and reconciliation; (5) sanctions / counter-terrorism screening records; (6) fraud and diversion monitoring summaries; (7) donor reporting.
- **Tier A/B.**

### D. Digital assets (crypto, stablecoins, tokenisation, CBDC)

#### 59. VASP Customer Onboarding (KYC) Analyst Assistant
Collects and checks KYC for a crypto exchange / wallet provider before a human approves the customer.
- **Hires:** exchange, broker, custodian, OTC desk, crypto ATM operator.
- **Jobs:** (1) document and liveness result review (from the KYC vendor); (2) source-of-funds / source-of-wealth questionnaires and evidence checks; (3) sanctions / PEP / adverse media; (4) on-chain exposure check of declared wallets; (5) risk rating; (6) RFI drafts; (7) EDD memo for high-risk customers; (8) periodic refresh.
- **Tier B.** Compliance approves / rejects.
- **Region:** EU MiCA + AMLR; US FinCEN MSB + state BitLicense; UK FCA MLRs; India FIU-IND; Singapore MAS PSN02; UAE VARA rulebooks; Japan FSA; Korea VAUPA + real-name account rules.

#### 60. Travel Rule Compliance Operator
Makes sure every crypto transfer carries and checks the originator / beneficiary information the travel rule requires.
- **Hires:** exchange, custodian, payment firm with crypto, stablecoin issuer.
- **Jobs:** (1) identify the counterparty VASP for an outgoing / incoming transfer; (2) counterparty VASP due diligence (licence, jurisdiction, travel-rule capability); (3) prepare and check IVMS101 data; (4) unhosted-wallet ownership proof checks (EU: transfers over EUR 1,000 to / from self-hosted wallets - verify) ; (5) handle missing / incomplete information per the policy (execute, reject, return, suspend recommendation for a human, per ESMA / EBA guidance); (6) sunrise-problem tracking (counterparty in a country without the rule); (7) record keeping and regulator reports; (8) protocol interoperability issues (TRP, TRUST, Sygna, VerifyVASP).
- **Tier B.** Compliance decides to hold / reject / return.
- **Region:** EU TFR 2023/1113 + EBA/GL/2024/11 (applicable from 30 Dec 2024, no de minimis) **[search]**; US BSA travel rule USD 3,000 threshold (from memory - verify); Singapore, Japan, Korea, UAE, Canada, Switzerland thresholds differ; FATF: 83% have laws, half no enforcement **[search]**.
- **Evidence:** VerifyVASP, Notabene and others (VerifyVASP commentary on EBA guidelines) **[search]**.

#### 61. Blockchain Transaction Monitoring and Investigation Analyst
Reviews on-chain risk alerts and traces funds for crypto firms and their investigators.
- **Hires:** exchange, custodian, stablecoin issuer, bank with crypto exposure, law firm, insolvency practitioner.
- **Jobs:** (1) triage alerts from Chainalysis / TRM / Elliptic (sanctioned, mixer, darknet, scam, stolen funds exposure); (2) trace flows across chains and bridges; (3) write the investigation memo with hashes; (4) draft STR / SAR narrative for the MLRO; (5) freeze-request drafts to issuers / exchanges for a human; (6) prepare evidence packs for victims' lawyers or police; (7) monitoring rules tuning.
- **Tier B.**
- **Evidence:** illicit volume $154bn 2025, sanctioned entities ~$104bn, stablecoins 84% (Chainalysis); TRM reports $158bn **[search]**.

#### 62. Crypto Custody and Wallet Operations Reconciliation Assistant
Reconciles what the custodian's books say against what is actually on-chain, every day.
- **Hires:** exchange, custodian, fund holding crypto, stablecoin issuer, payment firm.
- **Jobs:** (1) pull on-chain balances of all controlled addresses; (2) reconcile to the internal ledger and customer liabilities; (3) explain breaks (pending deposits, fees, chain forks, dust, staking rewards); (4) hot / warm / cold allocation vs policy; (5) prepare withdrawal batches and cold-storage movement requests for the signers' approval; (6) proof-of-reserves / proof-of-liabilities data preparation for the auditor; (7) incident log for lost / stuck deposits (wrong network, missing memo / tag) and recovery requests; (8) daily custody report.
- **Tier B.** Human key-holders sign; auditors attest.
- **Region:** MiCA custody obligations (segregation, register of positions); NY DFS custody guidance; HK SFC VATP 98% cold storage (from memory - verify); Japan FSA cold-wallet rules; US SAB 121 rescinded 2025 (from memory - verify).

#### 63. Crypto Licensing and Regulatory Reporting Preparer (CASP / VASP)
Prepares the licence dossier and periodic reports of a crypto business.
- **Hires:** CASP / VASP, token issuer, law firm.
- **Jobs:** (1) licence map by country (MiCA CASP per Art. 59 + passporting; VARA; MAS DPT; HK SFC VATP; Japan FSA; Korea FIU; India FIU-IND; Kenya VASP; US state MTL / BitLicense; Canada CSA); (2) application dossier drafts (programme of operations, governance, ICT, custody, complaints, conflicts, AML); (3) MiCA white-paper drafting and notification calendar; (4) periodic regulatory returns and statistics; (5) change notifications; (6) regulator Q&A drafts; (7) PSD2 / EMI interplay for e-money tokens (EBA Op/2025/08) **[search]**.
- **Tier B.** Management body signs; the firm files.

#### 64. Stablecoin Reserve and Attestation Assistant
Prepares the daily reserve reconciliation and the monthly attestation pack of a stablecoin issuer.
- **Hires:** stablecoin issuer, e-money token issuer, bank issuing tokenised deposits, fintech distributing stablecoins.
- **Jobs:** (1) daily: tokens outstanding (on-chain supply across chains) vs reserve assets; (2) reserve composition vs permitted assets and concentration limits; (3) redemption queue and liquidity stress tests; (4) monthly public reserve report draft; (5) evidence for the accountant's attestation; (6) mint / burn reconciliation to fiat flows; (7) freeze / blacklist request log for compliance decisions; (8) regulator returns.
- **Tier B.** Issuer's officers sign; accountants attest.
- **Region:** US GENIUS Act + OCC part 15 final rule (Oct 2026: monetisation, stress-testing, FX risk requirements; yield presumption dropped) + FinCEN AML proposal **[search]**; EU MiCA EMT / ART (reserve, redemption at par); HK Stablecoins Ordinance (HKMA licence, register) **[search]**; Singapore MAS SCS framework; Japan PSA stablecoin rules; UAE CBUAE PTS.

#### 65. Token Listing and Product Due-Diligence Analyst
Prepares the review file before an exchange lists a token or launches a crypto product.
- **Hires:** exchange, broker, custodian.
- **Jobs:** (1) collect the token's white paper, team, contracts, audits, tokenomics; (2) smart-contract risk summary (admin keys, upgradeability, blacklist functions); (3) legal-classification questions for counsel (security / e-money / utility by country); (4) liquidity and market-abuse risk; (5) sanctions / illicit exposure check; (6) listing memo with recommendation; (7) post-listing monitoring plan.
- **Tier B.** Listing committee decides; counsel classifies.

#### 66. Crypto Market-Abuse Surveillance Analyst Assistant
Reviews trade-surveillance alerts on a crypto venue and drafts suspicious-order reports for the human.
- **Hires:** exchange, broker.
- **Jobs:** (1) review wash-trading, spoofing, pump-and-dump, insider (pre-listing) alerts; (2) build the order book / account timeline; (3) link accounts; (4) draft STOR / suspicious-order report narrative; (5) insider list maintenance around listings; (6) surveillance MI.
- **Tier B.**
- **Region:** MiCA Title VI market abuse (STORs to NCA); Japan JVCEA; Korea VAUPA unfair-trading rules; HK SFC.

#### 67. Crypto Tax Reporting Operations (for platforms)
Prepares the tax-information reports a crypto platform must issue to customers and tax authorities.
- **Hires:** exchange, broker, custodian.
- **Jobs:** (1) build customer cost-basis records; (2) generate draft 1099-DA (US), DAC8 / CARF reports (EU / OECD), India Form 26QE / 194S TDS returns, Japan payment records; (3) reconcile to the ledger; (4) customer tax statements; (5) correction / re-issue tracking; (6) deadline calendar.
- **Tier B.** The platform files.
- **Region:** see role 11; all (from memory - verify).

#### 68. Crypto Customer Recovery and Support Specialist
Helps exchange / wallet customers with lost deposits, stuck transactions and account recovery - safely.
- **Hires:** exchange, wallet, custodian.
- **Jobs:** (1) diagnose wrong-network / missing-memo deposits from the hash; (2) prepare the recovery request with fee and risk for staff approval; (3) stuck-transaction explanation (gas, nonce) and options; (4) account-recovery identity checks routed to staff (never seed phrases); (5) impersonation-scam warnings; (6) complaint logging under MiCA / local rules.
- **Tier A/B.**

#### 69. CBDC and Tokenised-Money Readiness Assistant
Prepares banks, PSPs and merchants for CBDC pilots and tokenised-deposit / DLT settlement projects.
- **Hires:** bank, PSP, merchant, government department.
- **Jobs:** (1) summarise the CBDC design (holding limits, offline, privacy, intermediary role) for the market; (2) readiness checklist (wallet distribution, KYC tiers, acceptance at POS); (3) pilot reporting templates; (4) cost / revenue model for intermediaries; (5) merchant acceptance guides; (6) track project timelines (digital euro: pilot 2027 / issuance 2029 if law passes; e-CNY; e-Rupee; Project mBridge / Agorá - from memory - verify); (7) staff training notes.
- **Tier A.**
- **Region:** ECB digital euro (Council mandate Dec 2025) **[search]**; PBoC e-CNY; RBI e-Rupee; CBN eNaira (low adoption, from memory - verify); Bahamas Sand Dollar; Jamaica JAM-DEX **[search]**.

#### 70. Embedded-Finance Product Compliance Mapper
Maps what licences, partners and rules a non-financial company needs to embed payments, cards, wallets or stablecoins.
- **Hires:** SaaS, marketplace, retailer, telco, gig platform.
- **Jobs:** (1) activity analysis (are we transmitting money? issuing e-money? an agent?); (2) licence-or-partner options per country; (3) partner shortlist questions (BaaS, BIN sponsor, PA, EMI); (4) flow-of-funds diagrams; (5) customer terms and disclosure list; (6) compliance programme checklist; (7) launch timeline.
- **Tier B.** Counsel advises; management decides.
- **Region:** US MTL exemptions (agent of payee - state by state); EU commercial-agent / limited-network exclusions under PSD2 (tightened in PSD3); India PA rules (marketplace must use authorised PA); UK EMD agent / distributor regimes.

#### 71. Payments Data and Regulatory Statistics Preparer
Prepares the payment statistics returns central banks and schemes ask for.
- **Hires:** bank, PSP, EMI, scheme participant.
- **Jobs:** (1) map internal data to the statistics template (ECB payment statistics regulation, BIS CPMI red book inputs, RBI PSS data, BCB returns, Fed surveys); (2) data quality checks; (3) fraud statistics returns (EBA fraud reporting guidelines, UK REP017); (4) reconciliations to finance; (5) variance explanations; (6) submission calendar.
- **Tier B.**

#### 72. Payments Regulatory Change Monitor
Tracks new payment and crypto rules in every country the firm operates in and turns them into impact notes.
- **Hires:** PSP, bank, EMI, VASP, law firm, consultancy.
- **Jobs:** (1) watch regulator sites and journals (EBA, ESMA, FCA, PSR, CFPB, OCC, FinCEN, RBI, NPCI, BCB, MAS, HKMA, CBUAE, VARA, CBN, CBK, Banxico, Bank of Canada, FATF); (2) summarise what changed; (3) impact note per product; (4) consultation-response drafts; (5) dated implementation plan; (6) board / committee update.
- **Tier A/B.**
- **Evidence:** the 2025-26 change load alone: PSD3/PSR, VoP, VAMP, ISO 20022 address rule, CASS 15, GENIUS rules, s.1033 rewrite, MED 2.0, FATF updates (all above).

---

## Part 4. Pains with evidence (demand)

| Pain | Evidence | Source |
|---|---|---|
| Chargebacks are rising and expensive | 261m chargebacks / $33.8bn in 2025 -> 324m / $41.7bn by 2028; merchants spend $128 per chargeback ($46 fees + $82 internal); issuers $9-10; ~45% fraudulent; 75% of cardholders skip the merchant | Mastercard insights + Javelin white paper **[search]** |
| Scams move money people send themselves | US FTC $15.9bn reported losses 2025 (3m reports), bank transfers largest dollar method, crypto second, investment scams ~half | FTC via Spokesman / Payments Dive / AARP **[search]** |
| UK APP fraud still rising despite reimbursement | APP losses £576.4m (+19%), investment fraud +40%, 66% of cases start online; 61% reimbursed overall, 89% of in-scope under PSR | UK Finance Annual Fraud Report 2026 **[opened]**, PSR **[search]** |
| Complaint volume about payments grows | India RBI ombudsman 13.34 lakh complaints FY25 (+13.55%); CFPB 6.6m complaints 2025 (double 2024), money-transfer complaints in the top categories | RBI / Tribune **[opened]**, CFPB **[search]** |
| India digital payment fraud | 13,516 digital payment fraud cases = 56.5% of reported bank frauds FY25 (cases >= Rs 1 lakh); FY24 UPI fraud 13.42 lakh incidents / Rs 1,087 crore | RBI annual report via Business Standard; Parliament data via YourStory **[search]** |
| Remittances cost too much | 6.49% average to send $200 (Q1 2025) vs 3% SDG target; sub-Saharan Africa 8.78% | World Bank RPW **[search]** |
| Mobile money is huge and fraud-prone | $2tn+ value 2025, 2.3bn accounts, 593m active, fraud "widespread" | GSMA SOTIR 2026 **[opened]** |
| Compliance alerts swamp teams | sanctions screening false positives 90-99% | Sayari, WorkFusion **[search]** |
| Crypto crime | $154bn illicit 2025, 84% stablecoins, $3.4bn stolen; FATF: half of travel-rule jurisdictions not enforcing | Chainalysis via The Block / Gizmodo; FATF **[search]** |
| BaaS ledger failures lose customer money | Synapse ~$85m missing; FDIC recordkeeping proposal | Business Journalism / Finextra **[search]** |
| Rule-change overload in 2025-26 | PSD3/PSR deal (Nov 2025), SWIFT address rule (Nov 2026), VAMP phases, FCA CASS 15 (May 2026), OCC GENIUS final rule (Oct 2026), s.1033 rewrite, Pix MED 2.0, PCI v4 future-dated | see Part 2 **[search]** |

---

## Never an AI employee (tier C) in this segment

| Task kept for humans | Why |
|---|---|
| Initiating, approving, releasing, reversing or recalling a payment, payout, refund, top-up or treasury transfer | money moves only on the user's own tap / the authorised officer's release through official rails |
| Authorising or declining card / payment transactions in real time, setting a customer's limit | an institution's credit / risk decision with liability |
| Deciding a dispute as the issuer or acquirer, granting or reversing provisional credit, final Reg E / Reg Z decision | statutory decision of the regulated entity; consumer-protection liability |
| Approving or rejecting a merchant, a customer (KYC / KYB), a VASP counterparty or a respondent bank | regulated onboarding decision; MLRO / underwriter accountability |
| Freezing, blocking or closing accounts or wallets; adding a merchant to MATCH / TMF | rights-affecting action; scheme and legal liability; tipping-off rules |
| Filing a SAR / STR / STOR / sanctions blocking report, incident report or regulatory return AS the institution | the institution's legal duty; signed by the MLRO / named officer; tipping-off offence risk |
| Signing a safeguarding audit, a PCI ROC / AOC, a stablecoin reserve attestation or proof-of-reserves opinion | reserved to auditors / QSAs / accountable officers |
| Holding or using private keys, MPC shares, seed phrases; signing on-chain transactions; minting or burning tokens | custody of client assets; never shareable with an AI |
| Collecting PIN, OTP, CVV, full card numbers, passwords, seed phrases | security rule; PCI DSS; scam vector |
| Setting merchant reserves, holds or pricing; applying scheme fines to merchants | commercial and contractual decision of the acquirer |
| Classifying a token as a security / e-money / commodity, or giving a licence / legal opinion | reserved legal advice |
| Personalised investment advice on crypto ("buy / sell this coin") | licensed advice in most jurisdictions |
| Negotiating with or paying ransom / extortion, or engaging "recovery agents" | illegal or scam-prone |

---

## Top 10 roles to build first and why

1. **Scam Reimbursement Claim Assistant (2)** - the biggest, fastest-growing consumer pain on every continent (US $15.9bn, UK £576m APP, India digital fraud = 56.5% of bank fraud); work is documents + deadlines + drafting, fully tier A; regimes now exist to claim against (UK PSR, SG SRF, Pix MED, EU PSD3).
2. **Pay-Safe Checker (3)** - prevention before the money leaves; cheap to run (payee-name, link, QR payload, warning lists), every user every day, fits Hoola's chat and phone.
3. **Card Dispute Helper (1)** - 261m chargebacks a year, 75% of cardholders go straight to the issuer; deadline calculation and evidence packs are exactly what an AI does well.
4. **Merchant Chargeback Representment Agent (13)** - proven willingness to pay (Chargeflow / Justt funding, success fees); merchant cost $128 per chargeback; clear APIs at every PSP.
5. **Payments Reconciliation Clerk for SMEs (16)** - every online seller has multi-gateway / marketplace settlement gaps; reads reports and drafts entries, no money moves; investor activity (End Close, Fazeshift) shows demand.
6. **Remittance Sender Assistant (6)** - 6.49% average cost vs 3% target, hundreds of millions of senders (Gulf -> South Asia, US -> LatAm, Europe -> Africa); comparison + paperwork, tier A.
7. **Subscriptions and Mandates Manager (5)** - recurring rails exploded (UPI Autopay, Pix Automático, PayTo, SEPA DD); every household wins money back; read-only data.
8. **Failed / Stuck Payment Tracker plus Ombudsman Escalation Drafter (4 + 9)** - India alone 13.34 lakh ombudsman complaints; TAT-based compensation rules give a concrete win; can ship as one employee for consumers.
9. **Sanctions Screening L1 Reviewer and AML TM Assistant (38 + 37)** - for institutions: 90-99% false positives, vendors already sell L1 agents, high measurable ROI, tier B with a named analyst.
10. **Travel Rule Compliance Operator and Blockchain Investigation Analyst (60 + 61)** - every CASP in 83% of FATF jurisdictions now has the duty, enforcement starting; stablecoins carry most illicit flow; MiCA / GENIUS / HK rules make this mandatory work.

---

## Sources

Opened and read:
- O*NET 13-2099.04 Fraud Examiners, Investigators and Analysts - https://www.onetonline.org/link/summary/13-2099.04
- GSMA, Mobile money $2tn in 2025 - https://www.gsma.com/newsroom/press-release/mobile-money-accounted-for-2-trillion-in-transactions-in-2025-doubling-since-2021-as-active-accounts-continue-to-grow/
- UK Finance Annual Fraud Report 2026 press release - https://www.ukfinance.org.uk/news-and-insight/press-release/fraud-report-2026-press-release
- Tribune India on RBI Ombudsman FY25 - https://www.tribuneindia.com/news/business/rbi-ombudsman-sees-13-34-lakh-complaints-in-fy25-loans-credit-cards-dominate

Found and read through search summaries (not opened in full; pages attempted returned 403 where noted):
- Mastercard, true cost of a chargeback 2025 (403 on open) - https://www.mastercard.com/sg/en/news-and-trends/Insights/2025/what-s-the-true-cost-of-a-chargeback-in-2025.html ; Javelin 2026 white paper - https://www.mastercard.com/content/dam/mccom/shared/news-and-trends/insights/2026/2026-javelin-chargebacks-white/2026%20Chargebacks%20Javelin%20White%20Paper.pdf
- World Bank Remittance Prices Worldwide Q1 2025 (403 on homepage) - https://remittanceprices.worldbank.org/sites/default/files/rpw_main_report_and_annex_q125_1_0.pdf
- FTC 2025 fraud losses - https://www.spokesman.com/stories/2026/apr/03/americans-lost-a-record-159-billion-to-scams-in-20 ; https://www.paymentsdive.com/news/bank-transfer-fraud-losses-crypto-federal-trade-commission/743202/
- PSR APP scam data - https://www.psr.org.uk/media/b50p3mlm/psr-2024-app-scam-performance-data-february-2026.pdf
- EBA travel rule guidelines - https://www.eba.europa.eu/publications-and-media/press-releases/eba-issues-travel-rule-guidance-tackle-money-laundering-and-terrorist-financing-transfers-funds-and ; EBA Op 2025/08 - https://eba.europa.eu/sites/default/files/2025-07/bde8c438-bb3f-4343-a158-f42b7afc9650/EBA%20Op%202025%2008%20%28No-Action%20letter%20on%20PSD2-MICA%20interplay%29.pdf
- Chargeflow Series A - https://www.crowdfundinsider.com/2025/11/255792-chargeflow-announces-35m-series-a/ ; Justt Flows - https://www.prnewswire.com/il/news-releases/justt-launches-flows-its-new-chargeback-automation-engine-302929137.html
- CFPB 2025 Consumer Response Annual Report - https://www.consumerfinance.gov/data-research/research-reports/2025-consumer-response-annual-report/ ; https://bankingjournal.aba.com/2026/04/cfpb-received-6-6m-consumer-complaints-in-2025/
- RBI Ombudsman annual report 2024-25 - https://website.rbi.org.in/web/rbi/-/publications/annual-report-of-ombudsman-scheme-2024-25
- Pix MED 2.0 - https://www.vixio.com/insights/pc-brazils-pix-sets-new-standard-fraud-dispute-button ; https://www.pagbrasil.com/blog/pix/med-2-0/ ; https://idec.org.br/sites/default/files/idec_contribution_to_med_2.0_proposals_5_and_6.docx.pdf
- PSD3 / PSR - https://www.dlapiper.com/en/insights/publications/2026/03/psd3-and-psr ; https://www.pwc.com/cz/cs/blog/rizeni-rizik/psd-3-the-psr-payments-reform.html ; https://www.onespan.com/node/135191
- OCC GENIUS Act final rule - https://www.arnoldporter.com/en/perspectives/advisories/2026/10/implementing-the-genius-act-the-occs-final-rule ; https://clsbluesky.law.columbia.edu/2026/11/17/davis-polk-discusses-occs-final-regulatory-framework-to-implement-genius-act/ ; https://www.mofo.com/resources/insights/261028-occ-finalizes-rule-implementing
- FATF targeted updates - https://www.fatf-gafi.org/en/publications/Fatfrecommendations/targeted-update-virtual-assets-vasps-2025.html ; https://www.fatf-gafi.org/en/news/targeted-updated-va-vasps-2026.html (403 on open)
- Visa VAMP fact sheet 2025 (PDF text not extractable) - https://corporate.visa.com/content/dam/VCOM/corporate/visa-perspectives/security-and-trust/documents/visa-acquirer-monitoring-program-fact-sheet-2025.pdf ; Checkout.com VAMP thresholds (403 on open) - https://support.checkout.com/hc/en-us/articles/23330844282514 ; Solidgate - https://docs.solidgate.com/risks/monitoring-programs/visa/
- SWIFT ISO 20022 - https://www.swift.com/standards/iso-20022/iso-20022-bytes/journey-continues
- CBDC tracker - https://www.atlanticcouncil.org/programs/geoeconomics-center/digital-currencies/ ; CRS - https://www.everycrsreport.com/reports/IF11471.html ; SAFE policy letter - https://safe-frankfurt.de/fileadmin/user_upload/editor_common/Policy_Center/SAFE_Policy_Letter_112.pdf
- CFPB s.1033 - https://www.consumerfinancemonitor.com/2026/08/06/cfpb-sends-new-section-1033-open-banking-proposal-to-oira-for-review/ ; https://www.cozen.com/news-resources/publications/2026/section-1033-compliance-date-open-banking-rule-enjoined-and-under-reconsideration
- Reconciliation / AR agents - https://www.irishtimes.com/business/2026/11/17/irish-founded-end-close-raises-35m-in-seed-capital/ ; https://fortune.com/2026/10/13/startup-causa-prima-20-million-billing-disputes-ai-agents/ ; https://news.crunchbase.com/fintech/fazeshift-accounts-receivable-ai-finance-ops-startup-funding/
- KYB / onboarding agents - https://ycombinator.com/companies/arva-ai ; https://taktile.com/ai-agents-kyb-onboarding ; https://thepaypers.com/crypto-web3-and-cbdc/news/colibrix-one-selects-vivox-ai-to-automate-merchant-kyb-checks ; https://www.brex.com/journal/rebuilding-onboarding-ai-native ; https://www.moxo.com/lp/merchant-operations
- Singapore SRF - https://www.mas.gov.sg/news/media-releases/2024/mas-and-imda-announce-implementation-of-shared-responsibility-framework-from-16-december-2024 ; https://www.mas.gov.sg/regulation/guidelines/guidelines-on-shared-responsibility-framework
- Hong Kong stablecoins - https://www.hkma.gov.hk/eng/key-functions/international-financial-centre/stablecoin-issuers ; https://www.linklaters.com/insights/blogs/fintechlinks/2025/august/hong-kong-launches-new-stablecoin-regime ; global stablecoin appendix - https://www.gibsondunn.com/wp-content/uploads/2026/03/Fintech-and-Digital-Asssets-Global-Stablecoin-Rules-in-Focus-03.13.26_Appendix1.pdf
- India frauds - https://www.business-standard.com/finance/news/bank-frauds-reduced-in-fy25-but-amount-rose-three-fold-rbi-125052900696_1.html ; https://yourstory.com/2025/12/upi-frauds-peak-in-fy24-show-signs-of-decline-parliament-data ; https://www.business-standard.com/economy/news/frauds-per-transaction-on-the-rise-since-july-rbi-dg-t-rabi-sankar-125110701752_1.html
- Sanctions screening false positives - https://sayari.com/?p=2305 ; https://www.workfusion.com/solutions/streamline-transaction-sanctions-screening-alert-review/ ; https://www.symphonyai.com/financial-services/sanctions-screening/
- Nigeria open banking - https://techcabal.com/2025/10/16/nigerias-open-banking-still-in-the-works/ ; https://www.vanguardngr.com/2025/10/nigerias-open-banking-will-happen-soon-cbn/
- FCA safeguarding - https://www.fca.org.uk/firms/emi-payment-institutions-safeguarding-requirements ; https://cms.law/en/gbr/legal-updates/fca-strengthens-safeguarding-regime-for-payments-and-e-money-firms2 ; https://www.regulationtomorrow.com/2025/08/ps25-12-changes-to-the-safeguarding-regime-for-payments-and-e-money-firms/
- Synapse / FDIC - https://businessjournalism.org/2025/02/synapse/ ; https://finextra.com/newsarticle/44752/fdic-plans-to-strengthen-custodial-deposit-rules-following-synapse-collapse ; https://www.alston.com/en/insights/publications/2024/09/fdic-rule-custodial-account-recordkeeping
- Quavo issuer disputes - https://www.quavo.com/issuing-banks/ ; https://www.quavo.com/compliance/
- Brazil Open Finance / Pix Automático - https://bemobi.com/open-finance-reaches-100-million-users-and-accelerates-the-evolution-of-pix/ ; https://thepaypers.com/payments/news/pix-launches-pix-automatico-in-brazil
- Chainalysis 2026 crypto crime - https://www.theblock.co/post/384753/crypto-crime-150-billion-usd-2025-state-actors-scale-onchain-chainalysis ; https://gizmodo.com/illicit-crypto-flows-climbed-to-154-billion-in-2025-as-nation-states-evade-sanctions-report-finds-2000708055 ; TRM - https://www.trmlabs.com/reports-and-whitepapers/2026-crypto-crime-report
- PCI DSS v4 - https://blog.pcisecuritystandards.org/important-updates-announced-for-merchants-validating-to-self-assessment-questionnaire-a ; https://blog.pcisecuritystandards.org/now-is-the-time-for-organizations-to-adopt-the-future-dated-requirements-of-pci-dss-v4-x

From memory - verify before use: all items marked "(from memory - verify)" above, including O*NET codes other than 13-2099.04, ISCO / UK SOC / ANZSCO codes, EU VoP date, EU IFR cap figures, US Reg E / Reg Z exact clocks, FTC click-to-cancel status, India TAT compensation amounts, crypto tax rules (1099-DA, DAC8, CARF), Kenya VASP Act, Australia Scams Prevention Framework details, Gulf rail names, travel-rule thresholds outside the EU, DORA / MAS / RBI incident clocks.
