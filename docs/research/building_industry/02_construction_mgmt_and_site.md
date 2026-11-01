# CONSTRUCTION MANAGEMENT & SITE ROLES — COMPLETE JOB LIST (India primary, international noted)

## 0. SOURCES ACTUALLY READ, AND THEIR LIMITS (read this before trusting any code or clause below)

| Source | What I got | Status |
|---|---|---|
| **NCO-2015** (Directorate General of Employment) — official PDFs at https://dge.gov.in/nco-2015 ; Vol I https://dge.gov.in/dge/sites/default/files/2022-07/National_Classification_of_Occupations_Vol_I-2015.pdf ; Vol II-B https://labour.gov.in/sites/default/files/National%20Classification%20of%20Occupations_Vol%20II-B-%202015.pdf | **dge.gov.in and labour.gov.in both refused the download in this session** (TLS/proxy reset, HTTP 503). I instead used a third-party machine-readable transcription of the NCO-2015 tables: http://gilesd-j.com/shared_resources/blogs/251128_India_NOC/250614%20-%202015%20NCO%20Draft%20Data%20Table.csv (3,452 rows, from https://www.r-bloggers.com/2025/11/indias-2015-national-classification-of-occupations-data-file/). | **Codes below are from that transcription, whose own author warns it was built by manual entry + LLM parsing and may contain errors.** Treat every 8-digit code as *to be confirmed against the BIS/DGE PDF*. The 4-digit stems are ISCO-08-aligned (NCO-2015 is explicitly aligned to ISCO-08 per the Vol II-B release letter), so the 4-digit level is safe. |
| **CPWD Works Manual 2022** — https://www.ndmc.gov.in/departments/Departments/Finance/nodal_cell/CPWD%20Works%20Manual%202022.pdf | Downloaded and read in full (91 pp). | **Primary. Direct quotes below.** |
| **SOP to CPWD Works Manual 2022** — https://www.ndmc.gov.in/departments/Departments/Finance/nodal_cell/SOP%20to%20CPWD%20Works%20Manual%202022.pdf | Downloaded and read (330 pp). SOP 5/10, 5/11, 5/12, 5/20, 5/24 read verbatim. | **Primary. This is where the test-check percentages live.** |
| **BOCW Act 1996, s.38** | Read via https://www.advocatekhoj.com/library/bareacts/buildingandother/38.php | Secondary host, text consistent across 3 sources. indiacode.nic.in and audit.hrylabour.gov.in both refused in this session. |
| **BOCW Central Rules 1998** (Rule 209 safety officer + Schedule VIII; Rules 55–57, 73 lifting appliances; Form V) | Only via search snippets and a courtkutchehry index. | **Schedule VIII qualification text: NOT FOUND in a verifiable source.** |
| **OSH Code 2020 + OSHWC (Central) Rules 2026** | https://www.scconline.com/blog/post/2026/05/13/osh-central-rules-2026-key-highlights-and-compliance-guide/ ; https://employmentlaw.lkslaw.com/osh-central-rules-2026 ; https://www.taxclue.in/blog/section-22-osh-code-2020-safety-committee-and-safety-officers/ | **MATERIAL WARNING: multiple sources say the OSHWC (Central) Rules, 2026 (G.S.R. 345(E), notified and in force 8 May 2026) supersede ~15 central rule-sets *including the BOCW Central Rules, 1998*.** The carve-outs were truncated in every snippet. Sources disagree on the safety-officer threshold for construction (BOCW s.38 = 500; secondary readings of OSH Code s.22(2) = 250 for building/construction). **Gazette text NOT verified.** Everything marked "BOCW" below should be re-checked against G.S.R. 345(E). |
| **RERA Act 2016** | indiacode.nic.in returned HTTP 403 for both PDFs. Provisions below reconstructed from MoHUA FAQ/commentary found in search and my own knowledge of the Act. | **Section *numbers* are reliable; exact wording is NOT verbatim-verified.** Primary: https://www.indiacode.nic.in/bitstream/123456789/19012/1/reraact.pdf |
| **NBC 2016 (SP 7:2016)** Part 2 Administration (Annex A, qualifications of registered professionals), Part 7 Construction Management, Practices and Safety | BIS does not publish SP 7 free; https://bis.gov.in/others/national-building-code/ . Part 7's six-section structure and "construction project management" scope confirmed only via secondary summaries. **Part 2 is under revision — BIS circulated a wide-circulation draft of a Fourth Revision in March 2025.** | **Clause-level text: NOT FOUND (paywalled).** |
| **CEA (Measures relating to Safety and Electric Supply) Regulations, 2010** consolidated to 4th amendment | Read in full locally; canonical copy https://www.cbip.org/CEARegulations/July%202019/Consolidated%20Regulation%20CEA%20Safety.pdf | **Primary, quoted.** BUT: CEA's own 2024 compendium (https://cea.nic.in/wp-content/uploads/notification/2024/08/Compendium_of_Regulations_by_CEA.pdf) lists a **2023 replacement**. Re-check. |
| **IS 516 Part 5** (NDT of concrete) | BIS drafts via services.bis.gov.in confirm Part 5 Sec 1 supersedes IS 13311(Part 1):1992 (UPV) and Part 5 Sec 4 supersedes IS 13311(Part 2):1992 (rebound hammer). | Confirmed in substance; **edition year disputed (2018 vs 2021) across BIS listings.** |
| **ISO 19650-2** | UK BIM Framework guidance https://ukbimframework.org/wp-content/uploads/2020/02/ISO_19650_Guidance_Part_2_Processes_for_Project_Delivery_ThirdEdition.pdf | Normative clause text paywalled; roles confirmed via official UK BIM Framework guidance. |
| **NEC4 ECC** | https://www.neccontract.com/news/what-nec4-ecc-supervisors-do,-and-need-to-know ; https://www.ceca.co.uk/wp-content/uploads/2022/09/CECA-NEC4-Bulletin-No.-21-The-Role-of-the-Supervisor-September-2022.pdf | Good. |
| **FIDIC 2017 "the Engineer" / Contractor's Representative (cl. 3.1, 4.3)** | **NOT FOUND** — no accessible primary or reliable secondary text surfaced. Stated below from general knowledge and flagged. |
| **CIOB** role definitions, **PMI** (PMBOK/Construction Extension) role definitions | **NOT FOUND** as free primary text. CIOB's *Code of Practice for Project Management for the Built Environment* and PMI's standards are paywalled. Not cited. |
| **Factories Act 1948 applicability to site**; **state Shops & Establishments** | **NOT FOUND** verified. Reasoning given below is analytical, flagged as such. |
| future.indiankanoon.org | **Blocked in this session (DNS).** Would need allow-listing to pull BOCW Central Rules text. |

**The single most load-bearing primary finding of this research** (quoted verbatim, and it answers your "who signs what" question for Indian government work) is CPWD SOP 5/24 + Works Manual para 5.6.4 — reproduced in full at §8 below.

---

## 1. OVERALL DELIVERY

**1.1 Project Director / Projects Head / General Manager (Projects)**
- *Indian site title:* "Project Head", "GM-Projects", "Sr. VP-Projects". Government equivalent: **Chief Engineer (CE)** / **Superintending Engineer (SE)**.
- NCO-2015: `1323.0300` General Manager, Construction / General Manager Construction Projects; also `1120.1300` Director, Construction; `1120.1200` Working Proprietor, Construction.
- *Does:* Owns the portfolio P&L and the delivery strategy across several sites — approves budgets, contract strategy and the baseline programme, resolves escalations the PM cannot, chairs the monthly review, and is the interface to the board/client CXO.
- *Deliverables:* Project execution plan / PEP, contract & procurement strategy, approved budget and cash-flow, monthly MIS / board pack, change-control and claims decisions, stage-gate approvals, project closeout report.
- *Employed by:* Developer, EPC contractor, PMC, government department (as CE/SE).
- **GATE:** In CPWD, the SE/CE tier carries *named* statutory-manual duties, not merely managerial ones: for works above ₹10 crore the **provisional and final completion certificates must be recorded by "EE and SE or CE"** (Works Manual **para 5.17.1(i)(b)** and **5.17.2**); where third-party QA is deployed "**SE/CE shall monitor the compliance of observations of TPQA by the Engineer-in-Charge**" (para 5.6.4); and "**an Officer not below the rank of SE draws a quarterly programme of inspection**" with the NIT-approving authority inspecting at prescribed RA-bill stages (SOP 5/12 ¶3). In private development, the **promoter** (not the project director) is the statutory person under RERA — see 1.9.

**1.2 Project Manager (construction)**
- NCO-2015: `1323.0100` Manager, Construction / Manager Construction Projects.
- *Does:* Runs one project day to day — drives the programme, chairs the weekly site/coordination meeting, approves subcontractor and material calls, administers the contract (EOT, variations, notices), and signs off the monthly valuation and progress report.
- *Deliverables:* Baseline + revised programmes, weekly/monthly progress reports, DPR roll-up, minutes, contract notices and correspondence, variation orders, EOT determinations, risk register, cash-flow, handover/closeout file.
- *Employed by:* Contractor, developer, PMC.
- **GATE:** No standalone Indian licence. Contractually named: under **NEC4 ECC the *Project Manager* is a named contractual role** who "decides the date of completion and certifies it", notifies early warnings, changes the Scope and can stop the works — and these powers are *his alone* unless delegated (CECA NEC4 Bulletin No. 21). Under **FIDIC** the equivalent certifying actor is "the Engineer" (cl. 3) — *NOT FOUND verbatim*. Under **CDM 2015 (UK)**, if there is more than one contractor the client must appoint a **principal contractor** to "plan, manage, monitor and coordinate the construction phase" (https://www.designingbuildings.co.uk/wiki/CDM_2015_principal_contractor) — India has **no CDM equivalent**; BOCW puts the duty on the *employer*, not on a designated coordinator.

**1.3 Construction Manager**
- NCO-2015: `1323.0100` / `1323.9900` Construction Managers, Other.
- *Does:* Owns the physical build — sequences trades on the ground, allocates labour/plant across fronts, clears interface clashes, and drives the look-ahead to the daily labour deployment.
- *Deliverables:* 3-week look-ahead, labour & plant histogram, daily/weekly progress report (DPR/WPR), method statements, pour cards and permits-to-work sign-offs, snag clearance plan.
- *Employed by:* Contractor (main/EPC); occasionally the developer in a "construction management" (CM-at-risk) delivery.
- **GATE:** None statutory in India. **Internationally this is the CIOB's core professional territory** — CIOB chartered membership (MCIOB) is the market credential; *CIOB's own definition NOT FOUND (paywalled)*.

**1.4 PMC (Project Management Consultant) Team Leader / Resident Engineer**
- NCO-2015: `1323.0100`.
- *Does:* Leads the client's consultant team on site — reviews and recommends (does not execute) the contractor's programme, quality and bills, issues instructions on the client's behalf, and certifies progress for payment.
- *Deliverables:* Monthly PMC report, certified RA bills / payment recommendations, NCRs and observation reports, inspection reports, design-review comments, EOT recommendations, completion recommendation.
- *Employed by:* PMC firm engaged by developer/government/PSU.
- **GATE:** The *recommendation vs certification* line is the gate. In CPWD, a private consultant **cannot displace the departmental officer**: "All the correspondences with contractors shall be made by **Engineer-in-Charge** as defined in GCC" (Works Manual **para 5.6.1(2)**), and where a private consultant is appointed, "the T/S authority shall ensure timely availability of drawings and details from the consultant(s)" (para 5.6.2(3)) — the consultant produces, the department signs. In the MoRTH/NHAI model the equivalents are the **Authority Engineer** and, on BOT/HAM, the **Independent Engineer** (see 4.9/4.10).

**1.5 Owner's Representative / Employer's Representative**
- NCO-2015: `1323.0100` (no distinct family).
- *Does:* Is the single named person through whom the owner speaks — holds the owner's decision authority on site, accepts or rejects work on the owner's behalf, and protects the owner's commercial position.
- *Deliverables:* Instructions/site orders, approvals and rejections, decision log, owner's monthly report, acceptance and handover certificates.
- *Employed by:* Developer / institutional owner (or PMC seconded into the role).
- **GATE:** Contractual naming is the whole point of the role — FIDIC "Employer's Representative", NEC4 "Client's Agent"/Project Manager. **In India, the owner's representative cannot sign away the promoter's RERA liabilities** (s.11, s.14, s.18 attach to the *promoter*).

**1.6 Development Manager**
- NCO-2015: **No distinct NCO-2015 family — NOT FOUND.** Nearest: `1323.0100`, or `1120.1300` Director, Construction.
- *Does:* Runs the project as an investment before and around construction — land/approvals, feasibility and residual land value, product mix, appointing consultants and contractors, funding drawdowns, sales/leasing interface.
- *Deliverables:* Feasibility and development appraisal, approvals tracker, consultant appointments, development programme, drawdown schedules, investor reports, exit/handover plan.
- *Employed by:* Developer, landowner, fund/investor (DM-fee model), or a specialist DM firm.
- **GATE:** If the entity is the "promoter", **the whole RERA apparatus is the gate**: project registration before any advertisement or sale (s.3), the **70% separate-account rule with a three-way professional certification** (s.4(2)(l)(D): withdrawals in proportion to percentage of completion, "certified by an engineer, an architect and a chartered accountant in practice" — in Maharashtra these are the **Architect's Form 1, Engineer's Form 2, CA's Form 3**), quarterly website updates (s.11(1)), and annual audit of the project account by a CA in practice. Penalty for contravention of "any other provision" can extend to 5% of the estimated project cost (s.61).

**1.7 Engineer-in-Charge (the pivotal Indian statutory-manual role — government works)**
- *Indian title:* **Executive Engineer (EE)** / Divisional Officer. Supported by **Assistant Engineer (AE)** and **Junior Engineer (JE)**.
- NCO-2015: `2142.0100` Civil Engineer, General / `1323.0100`.
- *Does:* Is the department's legally-operative contract counterparty on one division's works — approves material samples and sources, inspects, test-checks measurements, passes bills, decides hindrances and EOT, records completion.
- *Deliverables:* Site order book entries, approved material samples register, test register (Annexure-54 proforma), checklists approved for important items, inspection programme, passed RA/final bills, hindrance decisions, compensation-under-clause-2 notices, provisional & final completion certificates, occupancy certificate application, as-built drawings.
- *Employed by:* CPWD / state PWD / PSU engineering wing.
- **GATE — THE sharpest "who signs what" in Indian practice, quoted:**
  - **"The officer who records/test checks the measurements for an item of work will be responsible for the quality, quantity/measurements and dimensional accuracy of that item of work… The Engineer-in-Charge shall be responsible for the overall quality of work."** (Works Manual **para 5.6.4**.)
  - **"The Engineer-in-Charge should test check 10% of the measurements recorded by his/her subordinates at least every alternate bill for works at his/her headquarter, and at least every third bill for works outside his/her headquarter."** Plus a mandatory **"at least 10% test check of the measurements of RCC items so as to ensure structural safety of building"**, **not less than 10% of plumbing**, and on steel receipt **"test check 10% of the total consignment received in a month"** with permitted variation **0.5% for bars ≤12 mm and 1% above** — exceed it on the low side and **"100% check of the measurements is carried out by the Engineer-in-Charge, and detailed investigation into the reasons for the shortage recorded."** (SOP **5/24 ¶2**.)
  - **"Samples for 10% of mandatory tests are collected by the Engineer-in-Charge. 10% of the field tests are got done by the Engineer-in-Charge in their presence."** (SOP **5/10 ¶8**.)
  - **"The Engineer-in-Charge shall obtain the Occupancy Certificate, wherever required, from local bodies with the help of concerned Architect/Consultant before handing over of buildings."** (Works Manual **para 5.17.3(1)**.)
  - Labour: **"Engineer-in-Charge ensures that the labour employed by the contractor is paid regularly as per prevailing labour laws… ensures submissions of prescribed returns by contractors and scrutinizes them."** (SOP **5/11**.)

**1.8 Contracts Manager / Contract Administrator**
- NCO-2015: nearest `1330.0200` Contract Officer (telephony-flavoured family — poor fit); **a construction-specific family is NOT FOUND.**
- *Does:* Reads the contract against reality — issues and answers notices to time-bar, builds and defends EOT/variation/claim positions, manages subcontract back-to-back terms and insurance/bond expiry.
- *Deliverables:* Contract register, notices and replies, EOT submissions with delay analysis, variation files, claim and counter-claim submissions, subcontract agreements, bond/insurance tracker, dispute/arbitration brief.
- *Employed by:* Contractor, developer, PMC, claims consultancy.
- **GATE:** No licence. Hard deadlines *are* the gate: CPWD **"In case of receipt of any notice from the contractor regarding hindrance or events under Clause 5.2 of GCC, the Engineer in Charge shall within 10 days of receipt of such notice, reply to the contractor"** and **"The contractor may apply to the Engineer-in-Charge within 14 days in writing for extension of time"** (Works Manual **5.15(1)**; SOP **5/25 ¶1**). NEC4's early-warning and compensation-event clocks are the international analogue.

**1.9 Promoter's Authorised Signatory (RERA) — a *job* in Indian development, not just a title**
- NCO-2015: NOT FOUND (not an occupation in NCO).
- *Does:* Signs and files everything the Authority sees — registration and extension applications, the quarterly QPR, the declaration on the separate account, and the certificates bundle.
- *Deliverables:* RERA registration application + Form B declaration, quarterly project progress reports (apartments booked, floor-wise photographs, approval status), Architect/Engineer/CA withdrawal certificates, annual audited project account, completion/occupancy certificates filed with the Authority.
- *Employed by:* The promoter entity itself (director/partner, or an officer holding a board authorisation).
- **GATE:** **This is the single most personally-exposed office in Indian private construction.** RERA s.11(4)(b) obliges the promoter "to obtain the completion certificate or the occupancy certificate, or both, as applicable… and to make it available to the allottees"; s.14(3) carries the **five-year defect-rectification liability (rectify within 30 days of notice)**; s.4(2)(l)(D) the 70% account; s.59–61 the penalties (up to 10% of estimated project cost / imprisonment for non-registration contravention of s.3 orders; up to 5% for other contraventions). *Section wording above is reconstructed, not verbatim-verified — indiacode returned 403.*

---

## 2. PLANNING AND CONTROLS

**2.1 Planning Engineer**
- NCO-2015: nearest `2142.0100`; `7313.1202` "Planner" exists but sits in a craft family (wrong fit). **A construction planning-engineer family is NOT FOUND.**
- *Does:* Builds and maintains the WBS and the CPM network, updates progress against it weekly, and produces the look-aheads, S-curves and the delay narrative that the claims case later rests on.
- *Deliverables:* Baseline programme (L1–L4), weekly/monthly updated programme, 3-week look-ahead, S-curve / progress-measurement system, resource & cash-flow histograms, delay/impact analysis (as-planned vs as-built, time impact analysis), catch-up/recovery programme, monthly progress narrative.
- *Employed by:* Contractor, PMC, developer, claims consultancy.
- **GATE:** No statutory gate. Commercial credentials only (Oracle Primavera P6 certification; AACE PSP/EVP; PMI-SP). Contractually the *programme itself* becomes gated: in NEC4 an **Accepted Programme** is a contract document and the Project Manager's acceptance/non-acceptance is a formal act.

**2.2 Scheduler (Primavera P6 / MS Project operator)**
- NCO-2015: NOT FOUND as a distinct family.
- *Does:* Operates the tool — codes activities, loads resources and costs, runs the update cycle and the out-of-sequence/retained-logic housekeeping, and issues the standard report set.
- *Deliverables:* XER/XML files and baselines, update logs, variance and float reports, look-aheads, dashboard extracts.
- *Employed by:* Contractor, PMC, offshore project-controls service centre (large Indian export market for exactly this).
- **GATE:** None.

**2.3 Project Controls Manager**
- NCO-2015: nearest `1323.0100`.
- *Does:* Owns the integrated cost-time-risk system — makes the schedule, the cost ledger and the earned-value engine agree, and signs off the monthly forecast (EAC) the business is held to.
- *Deliverables:* Cost-loaded programme, earned-value report (PV/EV/AC, CPI/SPI, EAC/ETC), change register, trend and forecast report, cost-report-to-schedule reconciliation, contingency drawdown, risk register with QSRA output.
- *Employed by:* EPC contractor, PMC, developer, owner's team.
- **GATE:** None statutory.

**2.4 Cost Controller / Cost Engineer**
- NCO-2015: `2141.0800` Engineering Estimator / Estimation Engineer; accounting-side `2411.0300` Cost Accountant; `4311.0600` Clerk, Cost Accounting.
- *Does:* Tracks committed vs incurred vs forecast cost against budget line by line, codes and accrues invoices and subcontract certificates, and explains each variance.
- *Deliverables:* Cost report / cost-value reconciliation (CVR), commitment register, accruals, budget-transfer notes, cost-to-complete, cash-flow forecast, subcontract payment certificates.
- *Employed by:* Contractor, developer, PMC.
- **GATE:** No construction licence. If the deliverable is a *statutory* cost record, the gate shifts to a professional: **cost audit / cost records under the Companies Act must be certified by a Cost Accountant in practice (ICMAI)**, and the RERA cost certificate by a **CA in practice**. *(Companies Act cost-audit applicability to construction companies: NOT verified in this session.)*

**2.5 Document Controller**
- NCO-2015: `2622.0601` Document Coder/Processor; also `2621.0100` Archivist. Construction-specific: **NOT FOUND.**
- *Does:* Is the single gate every drawing, transmittal, RFI and submittal passes through — numbers and registers it, routes it for review, distributes the current revision and withdraws the superseded one, and can tell you on demand which revision was on site on a given date.
- *Deliverables:* Master document register (MDR), drawing register with revision history, transmittals, RFI/submittal/NCR logs, correspondence register, distribution matrix, superseded-drawing archive, handover O&M dossier index.
- *Employed by:* Contractor, PMC, developer, consultant.
- **GATE:** No licence, but **this role produces the evidence base for every statutory and contractual claim**. CPWD makes the equivalent records mandatory and *named*: online **inspection register** on PMS "to be accessed through PMS for maintaining online record of all site inspections made from the start of work to its completion" (Works Manual **para 5.7(1)**), plus **site order book, physical inspection register, cement register, dismantle register** under SOP **5/14**, and a **"Guard file… maintained at all work sites, containing copies of all inspection reports to-date"** which **"the Engineer-in-Charge invariably reviews and signs"** (SOP 5/10 ¶¶9,12).

**2.6 EDMS / CDE Manager — "Information Manager" (ISO 19650)**
- NCO-2015: NOT FOUND.
- *Does:* Runs the common data environment — sets the container naming and status codes (WIP/Shared/Published/Archive), enforces the approval workflow, and reports on information delivery against the MIDP.
- *Deliverables:* CDE configuration and access matrix, information-delivery plans (TIDP per task team, consolidated into the **MIDP**), the **detailed responsibility matrix**, BIM Execution Plan (pre- and post-appointment), model federation and clash reports, information-model acceptance records, COBie/asset-data drop.
- *Employed by:* Lead appointed party (main contractor) or appointing party (client) — the standard is deliberately role-not-title.
- **GATE:** **ISO 19650-2 names the parties, not the job:** *appointing party* (client — "has overall accountability for assigning responsibility of information management functions to their appointed parties", to be done before engaging any lead appointed party), *lead appointed party* (must "coordinate and compile each of the TIDPs into an MIDP"), *appointed party / task team*. The **information management function is nominated in the tender response (cl. 5.3.1)** and competence is assessed at cl. 5.1.1 and 5.3.1 (https://ukbimframework.org/wp-content/uploads/2020/02/ISO_19650_Guidance_Part_2_Processes_for_Project_Delivery_ThirdEdition.pdf). "BIM Manager"/"Information Manager" are **not standardised titles**. India: no statutory CDE duty; BIS has *proposed* adding "construction project management including use of Building Information Modelling" to the NBC Part 7 revision (BIS panel agenda, services.bis.gov.in) — **not yet in force**.

**2.7 BIM Manager / BIM Coordinator / BIM Modeller**
- NCO-2015: the CSDCI qualification packs are explicitly NCO-aligned — e.g. **CON/Q2101 "BIM Designer – Interior Design and VR Integration", NSQF Level 6** (https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/CON_Q2101_v1.0.pdf — **note: that QP is marked "Deactivated", deactivation date 02/01/2025**). Modeller/designer families map under `2142`/`3118` (`3118.0200` Draughtsperson, Civil; `3118.0500` Draught person, Structural).
- *Does:* Authors/federates the models, runs clash detection and resolution rounds, and produces the quantity and sequencing outputs the site actually uses.
- *Deliverables:* Discipline and federated models, clash matrices and resolution logs, model-based quantities (5D), 4D sequence, shop/coordination drawings, as-built model.
- *Employed by:* Contractor, consultant, BIM service firm (large Indian outsourcing market).
- **GATE:** None statutory. NSQF/CSDCI qualification packs are the Indian skilling credential.

**2.8 Risk Manager**
- NCO-2015: NOT FOUND.
- *Does:* Runs the register and the quantitative models — facilitates risk workshops, owns mitigation actions, and produces the P50/P80 cost and time numbers contingency is set from.
- *Deliverables:* Risk register, QSRA/QCRA (Monte Carlo) outputs, contingency recommendation, risk-review minutes, opportunity log.
- *Employed by:* Owner, PMC, EPC contractor, lender's engineer.
- **GATE:** None.

**2.9 Commercial Manager / Quantity Surveyor (contractor-side)**
- NCO-2015: **"Quantity Surveyor" does not exist as an NCO-2015 occupational title — NOT FOUND** (and ISCO-08 has none either). Nearest: `2141.0800` Engineering Estimator/Estimation Engineer; `3315.0100` Valuer.
- *Does:* Owns the money in the contract — takes off and agrees quantities, prices variations, issues subcontract orders and valuations, and runs the monthly CVR that says whether the job is making or losing.
- *Deliverables:* Bills of quantities, taking-off sheets, rate analysis, interim valuations and payment applications, subcontract orders and final accounts, variation accounts, CVR, final account.
- *Employed by:* Contractor, PMC, developer, independent QS practice.
- **GATE:** No Indian statutory licence (contrast UK: RICS/MRICS is the market gate and RICS Red Book governs valuation). **Where a QS output becomes statutory in India it must be re-signed by a gated professional**: the RERA withdrawal certificate needs "an engineer, an architect and a chartered accountant in practice", not a QS.

**2.10 Estimator / Tendering Engineer**
- NCO-2015: `2141.0800` Engineering Estimator / Estimation Engineer.
- *Does:* Builds the bid — takes off quantities from tender drawings, builds rate analyses from first principles or the schedule of rates, collects vendor/subcontractor quotes, and assembles the priced bid with its qualifications.
- *Deliverables:* Quantity take-off, rate analysis, resource norms, bid price build-up, technical and commercial bid documents, deviation/qualification schedule, post-bid clarification replies.
- *Employed by:* Contractor; government side the **NIT-approving authority's** estimating wing.
- **GATE:** In CPWD the estimate and tender *processing* are gated by a personal certificate: SOP includes the required statement **"Certified that I have personally conducted a test check of all the computed… tenders"** and the officer certifies **"as he/she could ascertain from such test check as he/she had been able to carry out"** (SOP text at Works-Manual SOP, tender-scrutiny SOP). Also: **"Mode of measurements for payment purpose will be decided by the NIT approving authority"** (Works Manual para 5.4-series, line: *"(6) Mode of measurements for payment purpose will be decided by the NIT approving authority"*).

---

## 3. SITE EXECUTION

**3.1 Site Engineer**
- NCO-2015: `2142.0100` Civil Engineer, General; `2142.0200` Civil Engineer, Building; `2142.0300` Civil Engineer, Structural; services variants `2142.0301` Plumbing Site Engineer, `7412.1002` Site Engineer-Control Panel.
- *Does:* Sets out and supervises a defined work front — reads the drawing, checks line/level/reinforcement/formwork before the pour, keeps the labour and material moving, and writes the day's record.
- *Deliverables:* Daily progress report (DPR), pour cards / checklists, reinforcement and shuttering check records, level and setting-out records, material requisitions and indents, site instruction/diary entries, RFI raising, measurement sheets feeding the MB.
- *Employed by:* Contractor (overwhelmingly), developer, PMC.
- **GATE:** No licence to be a "site engineer" in India. But in CPWD the equivalent cadre officer personally carries the quality liability: **"All items of work irrespective of their cost are recorded/verified by the Junior Engineer/Assistant Engineer of the work"** and *the recorder owns the quality* (SOP 5/24 ¶1(iii)(a); Works Manual 5.6.4). **Local-body gate:** state building byelaws (framed on NBC 2016 Part 2) require the **owner's appointed engineer/structural engineer/supervisor to be registered/empanelled with the local authority and to file supervision certificates** — e.g. Odisha's notification sets a **registered supervisor** at diploma in civil engineering/architectural assistantship + 2 years, or ITI civil draftsmanship + 5 years under a qualified architect or civil engineer (https://urban.odisha.gov.in/sites/default/files/2023-09/07032017_352_Notification%20of%20technical%20persons.pdf). **NBC Part 2 Annex A text itself: NOT FOUND (paywalled).**

**3.2 Execution Engineer**
- NCO-2015: `2142.0100`.
- *Does:* Same field as 3.1 with an output bias — chases the day's targets (pour volume, blockwork area, plaster area) across gangs and clears the blockers.
- *Deliverables:* DPR, pour/activity completion records, labour deployment sheet, hindrance notes, material consumption statements.
- *Employed by:* Contractor.
- **GATE:** As 3.1.

**3.3 Site In-charge / Project In-charge (the default Indian title)**
- NCO-2015: `1323.0100` or `3123.0100` depending on seniority.
- *Does:* Is the contractor's most senior person physically on that site — answers to the client and the inspectorate, controls spend within limits, and is the person everyone from the labour contractor to the local authority deals with.
- *Deliverables:* Everything the site issues upward (DPR, WPR, bills, safety reports, statutory registers) plus site-level correspondence and the handover file.
- *Employed by:* Contractor; on small works the labour/petty contractor's own in-charge.
- **GATE:** **Practically the person on whom BOCW/OSH "employer" duties land first in an inspection**, even though the Act names the *employer*. The statutory risk is strict: BOCW Act s.38 duties, Central Rules registers, notice of commencement (BOCW Act **s.46** — notification to the local authority **at least 30 days before** construction begins, per https://factohr.com/bocw-act-1996/ — *section number pairing confirmed in search but the verbatim provision was NOT retrieved*).

**3.4 Site Supervisor (and the *registered* supervisor)**
- NCO-2015: **`3123.0100` Work Supervisor, Construction** (plus `3123.0200` insulation, `3123.0300`/`.0301`/`.0302` plumbing & pipefitting, `3123.0400` Electrical Supervisor-Wiring, `3123.0500`/`.0700` painting); `3112.0100` **Overseer, Civil Engineering**.
- *Does:* Stands over the gang — allocates the day's work, checks workmanship as it happens, calls material, enforces basic safety.
- *Deliverables:* Daily labour report and attendance input, work-front checklists, material requisitions, quality snag lists, shift handover note.
- *Employed by:* Contractor, subcontractor, labour contractor.
- **GATE:** **This is where the Indian gate is real and local.** State building byelaws (per NBC 2016 Part 2) license classes of **registered supervisor** who must file a **certificate of supervision** with the local body; qualifications are set by state notification (Odisha example at 3.1). **BIS deliberately refused to standardise the title** — the committee noted the varying use of "surveyor/building surveyor/supervisor" under state byelaws with different qualifications and "decided not to use the generic word 'surveyor' or such other words" (NBC drafting note surfaced in search). **Electrical supervisor is a *hard* licence — see 9.4.**

**3.5 Foreman / Charge-hand / Mistri / Mukadam**
- NCO-2015: `3123.0100`-family (`3123.0301` Plumbing Foreman etc.); craft-side `7112.0100` Stone Mason, `7112.0200` Bricklayer, `7115.0200` Carpenter (Construction), `7115.0201` Assistant Shuttering Carpenter, `7214.1101` Assistant Bar Bender and Fixer, `7119.0301` Assistant Scaffolder, `7215.0100`/`.0101` Rigger; labour `9312.9900` Construction and Maintenance Labourers Other, `9313.9900` Building Construction Labourers Other, `9313.0201`/`.0301`/`.0401` Helpers.
- *Does:* Leads a trade gang hands-on and sets the pace and the standard of the physical work.
- *Deliverables:* Gang attendance/output record, piece-rate measurement input, tool and tackle issue record, toolbox-talk attendance.
- *Employed by:* Contractor, subcontractor, labour contractor (the *mukadam* is usually the labour contractor's own man).
- **GATE:** None on the foreman. But **the people under him trigger the employer's gates**: BOCW registration of the establishment (the Act applies to establishments employing, or having employed in the preceding 12 months, **ten or more building workers** — s.1(4)), BOCW worker registration & welfare-board cess, and the **BOCW cess at 1% of the cost of construction** under the BOCW Cess Act 1996. *Cess rate not re-verified this session.*

**3.6 Billing Engineer (a distinctly Indian job)**
- NCO-2015: NOT FOUND as a title. Nearest `2141.0800` / `2142.0100`.
- *Does:* Converts executed work into money — measures or verifies measurements, writes the measurement sheets/MB, assembles the RA bill with abstracts and deviation statements, and reconciles it against the client's certification and the subcontractor's claim.
- *Deliverables:* **Measurement Book (MB) entries / e-MB**, measurement sheets, abstracts, **Running Account (RA) bills**, deviation statements (extra/substituted items), secured-advance statements, material reconciliation (cement/steel), subcontractor bills, final bill, no-claim certificate.
- *Employed by:* Contractor, PMC, developer; government side = JE/AE.
- **GATE — the most precisely prescribed records in Indian construction (CPWD SOP 5/20, verbatim):**
  - **"The payments to contractors and others for the work done or other services rendered are made on the basis of measurements recorded in the Measurement Book."**
  - **"These books are considered as very important accounts records and maintained very carefully and accurately as these may have to be produced as evidence in a court of law."**
  - MBs serially numbered division-wide, register in **form CPWA 92**, with a sub-divisional register "showing the names of persons, i.e. **Assistant Engineer/Junior Engineer, to whom the Measurement Books are issued**".
  - **"The signature of the contractor or his/her authorized representative is obtained in the Measurement Book for each set of measurements."**
  - **"The measurements are recorded in ink."** · **"No entry is erased or overwritten… corrected by crossing out… initialed and dated by the officer recording/checking measurements."** · pages **machine numbered**, no blank page left or torn out, blanks cancelled by diagonal lines, attested and dated.
  - Cancellation: **"endorsed by the dated initials of the Officer ordering the cancellation… the reasons for cancellation being also recorded."**
  - Each set must open with: full name of work as in the agreement, location, number and date of agreement, date of written order to commence, date of actual completion, date of recording measurements, reference to previous measurements.
  - **"Recording of measurements only by authorized persons."**
  - 2022 default is electronic: **"All measurements are to be done as per provisions of GCC and abstract of schedule of measurements and payments are to be entered through PFMS portal of CPWD using E-MB module"** (Works Manual **para 5.12**); physical MBs are the exception, governed by SOP 5/20 (para 5.12.1).
  - **No measurement = no payment, with one narrow exception:** advance payment can be made **"on a running account bill form for the work done… and measurements submitted by him, but not checked or work done but not measured"** (para 5.12.5) — and **"Ad-hoc payments amounting to 75% of the eligible running account bill/due stage payment shall be…"** (para 5.18-series).

**3.7 Junior Engineer (JE) / Assistant Engineer (AE) / Executive Engineer (EE) — government cadre**
- NCO-2015: `3112.0100` Overseer, Civil Engineering (JE-level technician); `2142.0100` (AE/EE).
- *Does:* JE records measurements and watches the work daily; AE check-measures and personally inspects before passing a bill; EE (Engineer-in-Charge) test-checks and passes.
- *Deliverables:* MB entries, check-measurement attestations, site order book entries, test registers, bill papers.
- *Employed by:* CPWD / state PWD / municipal engineering / PSU.
- **GATE — the exact signature chain, verbatim from SOP 5/24 ¶1:**
  - **"The Assistant Engineer satisfies himself/herself before passing a bill for payment, or before submitting it to the Divisional Officer for payment, that the work or supply billed for has actually been carried out/completed in accordance with the terms and conditions of the contract. In cases where there is no AE, JE has to comply above provisions before submitting bill to the Divisional officer."**
  - **"The Assistant Engineer is to personally inspect all the works of any magnitude and submit the same to division office before for payment."**
  - **Works at sub-divisional HQ: AE must "check measurements not less than 50% of the cumulative value of the work done recorded/verified by the Junior Engineer before any running/final bill is paid." Outside HQ: "not less than 50% of the cumulative value of work done before preparing final bills or before making payment of alternate running/final bills."**
  - **"No test check is required in case AE records/checks 100% measurements of works. Only a certificate to that effect is sufficient that 'measurement recorded by AE 100%'."**
  - **"For the purpose of test check, 'measurements' means the 'corresponding monetary value of measurements of work done.' This, however, does not apply to 'Levels', in which case the test check has to be based on the number of levels recorded."**
  - **Mandatory 100%/50% categories** — items that "owing to their situation cannot subsequently be checked": all work below ground level (concrete, masonry, steelwork in foundation); fabricated steel encased in masonry/concrete; **reinforcement in RCC/RB work**; woodwork/ironwork hidden by ceilings, wall panelling, floor boarding; bitumen painting under mud phuska/tiles; waterproofing compounds in gauging cement; pipes buried in floor or masonry; earthing installation and cable laying. Plus high-unit-rate items: RCC, sunk ashlar/marble, stone/marble wall lining, steel cladding and structural glazing, teakwood chowkhats/frames/trusses, joinery, costly brass fittings, **"all major equipments for AC, lifts, Generator sets, Sub-station equipments, fire works"**, and "any other items desired by Engineer-in-Charge."
  - Repetitive work: **"the Assistant Engineer (Elect) should test check 100% of all items of at least one unit, taken at random, besides test checking isolated and individual items in other units to bring the total extent of check measurement to the desired limit of 50%."** Plumbing: **"not less than 50% of the plumbing work for sanitary and water supply."**
  - Levels: **"The Assistant Engineer should exercise test check at least to the extent of 50%… The test check of the levels is carried out independently by each officer."**
  - Road sub-base/base: **"The Assistant Engineer test checks not less than 50%, and the Engineer-in-Charge, not less than 10% of the supply of materials in each length of 1 km before the work of laying is started."**
  - **Attestation and the collective record:** **"The individual items checked is clearly shown in the Measurement Book, and the result recorded by the officer concerned. The items thus checked are attested by the dated initials of the checking Officer."** · **"A collective record of all the check carried out from time to time is prepared in each Measurement Book. The result is indicated by the word 'Satisfactory' or 'Unsatisfactory'… Unsatisfactory result is communicated to the JE or both the JE and AE as the case may be."**
  - **Discretionary waivers are explicit and limited:** outside-HQ works up to 20% of the AE's tender-acceptance power need no AE check-measurement, but **"He will, however, have to accept general responsibility for the correctness of the bill as a whole."** Same formula for the EE at 20% (outside HQ) / 10% (at HQ).
  - **Independent accounts check:** the **Divisional Accountant** must "test check the accuracy of calculations", and after his check the officer **"should enter the word 'Check and bill'"** (SOP, documentation-of-accounts section).
  - Horticulture parallel: SO(H)/AD(H)/DD(H) at the same 100%/50%/10% tiers, with **100% test check by AD(H) for hidden/perishable items (manure, pesticides, seasonal plants)**.

**3.8 Draughtsman / CAD Technician**
- NCO-2015: `3118.0100` Architectural, **`3118.0200` Civil**, `3118.0300` Electrical, `3118.0401`/`.0402` Mechanical, `3118.0500` Structural, `3118.0600` Topographical, `3118.0201` Plumbing Draftsman, `3118.0301` Draftsman, `3118.9900` Others.
- *Does:* Produces and revises the drawings the site builds from — GFC sets, shop drawings, bar-bending schedules, as-builts.
- *Deliverables:* GFC/shop drawings, BBS, layouts, as-built drawings, revision clouds and registers.
- *Employed by:* Consultant, contractor, PMC.
- **GATE:** None. But the *as-built* is gated downstream: CPWD **para 5.17.3** ties as-built drawings to handover, and the occupancy certificate application depends on them.

**3.9 Overseer / Work Supervisor (public works technician tier)**
- NCO-2015: `3112.0100` Overseer, Civil Engineering; `3112.9900` Civil Engineering Technicians, Other; `3123.0100` Work Supervisor, Construction.
- *Does:* Measures, records, and watches work on behalf of the department below JE level.
- *Deliverables:* Measurement entries, muster/attendance records for departmental labour, daily reports.
- *Employed by:* PWD / municipal body / panchayat.
- **GATE:** Recording authority only where authorised (SOP 5/20: "Recording of measurements only by authorized persons").

---

## 4. QUALITY

**4.1 QA/QC Manager**
- NCO-2015: nearest `2141.0100` **Works Inspector, Engineering / Inspection Engineer**; `1223.0102` Manager Material Testing.
- *Does:* Owns the project quality system — writes the QAP/ITP set, runs the inspection and test regime, raises and closes NCRs, and holds the release/hold points that stop work.
- *Deliverables:* **Project Quality Plan, Inspection & Test Plans (ITPs), checklists, NCR/CAR register and closures, material approval register, test-result compilation and trend charts, concrete-cube register, calibration register, internal audit reports, quality dossier / handover QA file, method-statement reviews.**
- *Employed by:* Contractor, PMC, developer, third-party QA agency.
- **GATE:** No Indian statutory licence for the person. **The system is gated by procurement value in CPWD: "For budgeted works, engagement of TPQA agency will be done for the works above Rs 20 crores or as per the directions issued from time to time by the CPWD Directorate. For Deposit works, TPQA provisions will be made as per MOU. For all other contracts where no TPQA is engaged, the existing QA units of Project Regions/Regions… shall carry out the Quality Assurance checks on random basis."** (Works Manual **para 7.2.1(3)**.) Vigilance overlay: **"The Chief Technical Examiner's Organization is the technical wing of the Central Vigilance Commission"** and inspects CPWD works "from the vigilance angle… for works of any magnitude"; the EiC must **"accompany CTE… and issue inspection paras of the CTE to the contractor as his own observations"** and must **not** quote CTE in correspondence with the contractor (paras 7.1.1, 7.1.2).

**4.2 QA/QC Engineer**
- NCO-2015: `2141.0100`; inspector-tier `3139.5001` Quality Control Inspector.
- *Does:* Executes the ITP on the ground — witnesses and signs inspections at each hold point, samples materials, logs tests, writes NCRs.
- *Deliverables:* Signed ITP/checklist records, pour cards, NCRs, test requests and reports, concrete cube register, welding/coating inspection records, material inspection reports (MIR).
- *Employed by:* Contractor, PMC, TPQA agency.
- **GATE:** The *checklist* is a CPWD-mandated artefact with a named approver: **"As and when any important item is taken up for execution, the Junior Engineer/Assistant Engineer should go through the specifications and invariably make a checklist… This checklist is got approved from the Engineer-in-Charge, and is shown to the inspecting officers."** Illustrative list: foundation work including reinforcement and shuttering, brickwork, cast-in-situ mosaic flooring, doors & windows, plumbing including water-supply pipelines, roof treatment, earth filling. Sample checklists for raft concrete, columns/beams/slabs, water-supply lines, brickwork and plastering are at **Annexure-26** (SOP **5/10 ¶13**).

**4.3 Materials Engineer**
- NCO-2015: `1223.0102` Manager Material Testing; `2111.1100` Material Scientist; `2141.0100`.
- *Does:* Approves what may be built with — qualifies sources and vendors, approves mix designs and trial mixes, and keeps the material-test regime ahead of the pour.
- *Deliverables:* Approved-source and approved-sample registers, concrete mix designs and trial-mix reports, cement/steel/aggregate/water test reports, material reconciliation statements, batching-plant calibration records.
- *Employed by:* Contractor, RMC supplier, PMC, third-party lab.
- **GATE (CPWD, verbatim, SOP 5/10):** **"samples of various materials are approved by the Engineer-in-Charge"**; **"Approved samples of materials are signed by the approving authority and the contractor and preserved till the end of the project"**; **"The material non-conforming to specifications are promptly rejected and removed from site"**; **"It is incumbent upon the Engineer-in-Charge to keep a watch over regular testing of materials before making payment at the stage of each running bill. For this purpose, a proforma as per Annexure-54 is prescribed."** Cement/steel consumption monitoring is separately mandated (Works Manual **5.6.7**, SOP **5/13**). Standards gate the methods: **IS 456:2000** (plain & RC code of practice), **IS 1199** (sampling/testing fresh concrete), **IS 516** (strength tests), **IS 2386** (aggregate tests), **IS 383:2016** (aggregates), **IS 2720** (soil tests), **IS 1786** (HSD reinforcement), **IS 3025** (water). *(These IS numbers are from domain knowledge; only IS 516 Part 5's supersession of IS 13311 was verified this session.)*

**4.4 Site Lab Technician / Lab In-charge (cube-testing)**
- NCO-2015: `3111.0200` Laboratory Assistant, Soil; `3111.0300` Chemical; `3111.0100` Physical; `3112.0701` Assistant Laboratory and Field Technician; `3119.0100` Laboratory Assistant, Engineering; `9313.0601` Helper Laboratory and Field Technician.
- *Does:* Casts, cures and crushes cubes; runs slump, temperature, sieve, moisture, compaction and field density tests; logs and reports.
- *Deliverables:* Cube register with 7/28-day results, slump and temperature records, field density (sand replacement/core), sieve analysis, compaction/Proctor, calibration certificates for the compression machine and balances.
- *Employed by:* Contractor's site lab, RMC plant, independent NABL lab, government QA unit.
- **GATE:** **Sampling is a named act in CPWD: "Samples for tests are taken mostly by the Junior Engineers, or some by the Assistant Engineers. Samples for 10% of mandatory tests are collected by the Engineer-in-Charge. 10% of the field tests are got done by the Engineer-in-Charge in their presence."** (SOP 5/10 ¶¶7–8.) Independent testing facilities are themselves governed: Works Manual **para 5.7.2 / SOP 5/16 "Govt./Private Independent Testing Facilities"**. In private work the market gate is **NABL accreditation (ISO/IEC 17025)** of the lab, not a licence on the technician.

**4.5 Third-party Inspector / TPQA Agency Engineer**
- NCO-2015: `2141.0100` Works Inspector, Engineering / Inspection Engineer.
- *Does:* Inspects and reports to the *client*, not the builder — independent audits of workmanship, material and records, with observations the contractor must answer.
- *Deliverables:* TPQA inspection reports and observation registers, compliance-closure reports, stage-clearance certificates, audit scorecards.
- *Employed by:* Third-party agency appointed by the owner/department (**not** by the contractor — that is the point).
- **GATE:** **Appointment is mandatory by value in CPWD (>₹20 crore for budgeted works, para 7.2.1(3)) and the *monitoring duty is personally assigned*: "In case of works where TPQA is deployed, SE/CE shall monitor the compliance of observations of TPQA by the Engineer-in-Charge" (para 5.6.4). Where CPWD's own QA unit has checked, "the removal of defects shall be ensured within reasonable time by the Engineer-in-Charge and the QA unit."**

**4.6 NDT Technician**
- NCO-2015: NOT FOUND as a titled family. Nearest `3139.5001` Quality Control Inspector; `7543.x` quality-inspector families (manufacturing-flavoured).
- *Does:* Runs non-destructive tests — on concrete UPV and rebound hammer, core extraction, cover meter, half-cell; on steel/welds UT, RT, MPI, DPT.
- *Deliverables:* NDT reports with equipment and calibration details, UPV/rebound correlation and classification, core-test reports, weld radiographs and interpretation sheets, repair recommendations.
- *Employed by:* Specialist NDT firm, third-party inspection agency, contractor (rarely in-house).
- **GATE:** **Personnel certification is the gate in practice, not in Indian statute: ASNT SNT-TC-1A / ISO 9712 Level I/II/III, and for welds CSWIP/AWS-CWI.** Method standards: **UPV and rebound hammer have moved — IS 516 (Part 5) Section 1 supersedes IS 13311(Part 1):1992 (UPV) and IS 516 (Part 5) Section 4 supersedes IS 13311(Part 2):1992 (rebound hammer)**, per BIS draft texts (services.bis.gov.in/tmp/16864_02092024102949_9.pdf and related). **Edition year is inconsistent across BIS listings (2018 vs 2021) — confirm in the BIS catalogue before citing.**

**4.7 Welding Inspector / Coating Inspector**
- NCO-2015: nearest `3122.4702` Welding Supervisor; `3122.4200` Supervisor and Foreman, Welding and Flame Cutting.
- *Does:* Qualifies welders and procedures, witnesses welding, checks fit-up, preheat, consumables and interpass, and signs the weld and coating records.
- *Deliverables:* WPS/PQR, welder qualification records (WQT), weld maps and visual inspection reports, NDT referrals, DFT/holiday-test and surface-prep records, coating inspection reports.
- *Employed by:* Contractor, fabricator, third-party inspection agency, owner.
- **GATE:** CSWIP 3.1/3.2, AWS-CWI, NACE/AMPP CIP (coatings) are the de facto gates. No Indian statutory licence. *Structural steel code: IS 800:2007; welding IS 814/IS 9595 — from domain knowledge, not verified this session.*

**4.8 Snagging / De-snagging / Completion Engineer**
- NCO-2015: NOT FOUND. Nearest `2141.0100`.
- *Does:* Walks finished space unit by unit against the specification and marks every defect, drives trades to close them, and re-inspects until the unit can be handed over.
- *Deliverables:* Snag lists per unit/floor, snag-closure registers with photographic evidence, pre-handover inspection reports, handover/possession checklist, defect-liability-period (DLP) log, O&M and warranty dossier.
- *Employed by:* Developer, PMC, contractor; increasingly specialist snagging firms for buyers.
- **GATE:** In CPWD, snagging is formalised into the **provisional completion certificate "with a list of outstanding balance items of work that need to be completed in accordance with the provisions of the contract"**, recorded by **EE up to ₹10 crore and EE + SE or CE above ₹10 crore** (para 5.17.1); the **Final Completion Certificate** is recorded by the same authorities **"under whose tenure the work is completed"**, and on composite works **"the completion certificate shall also be recorded by the Executive Engineer concerned of the minor component of work"** (para 5.17.2). In private housing, the snag list is the practical front line of the promoter's **RERA s.14(3) five-year defect liability (rectify within 30 days of notice)**.

**4.9 Authority Engineer (government highway/infrastructure model)**
- NCO-2015: `2142.0600` Civil Engineer, Highways and Roads / `1323.0100`.
- *Does:* Is the Authority's supervision consultant on an EPC contract — reviews design, approves drawings, inspects and tests, certifies interim payments and completion.
- *Deliverables:* Design review and approval records, monthly progress reports to the Authority, interim payment certificates, test/quality audit reports, provisional and final completion certificates, as-built verification.
- *Employed by:* Consultancy appointed by NHAI/MoRTH/state authority.
- **GATE:** Role, powers and personnel qualifications are fixed by the **Model EPC Agreement / Authority Engineer ToR** — minimum qualifications and experience per key-personnel slot are contractually mandatory, and only named personnel may sign. *MoRTH/NHAI document text NOT retrieved this session.*

**4.10 Independent Engineer (PPP/BOT/HAM)**
- NCO-2015: `1323.0100` / `2142.0600`.
- *Does:* Acts for both parties under the concession agreement — certifies construction completion and provisional COD, monitors O&M against the maintenance manual, and determines disputes within its remit.
- *Deliverables:* Completion/provisional certificate, punch list, O&M inspection reports, tests-on-completion reports, determinations.
- *Employed by:* Jointly appointed under the Concession Agreement (paid by the concessionaire, reporting to both).
- **GATE:** Appointment, independence and certification powers are prescribed in the **Model Concession Agreement**; **the Independent Engineer's completion certificate is the condition precedent to tolling/annuity**, so it is the highest-value signature in Indian infrastructure. *MCA text NOT retrieved this session.*

**4.11 Structural Engineer (design + site certification)**
- NCO-2015: `2142.0300` Civil Engineer, Structural.
- *Does:* Designs and then certifies the structure as built — issues GFC structural drawings, answers site queries, inspects critical stages (reinforcement before pour, major pours), and signs the structural stability certificate.
- *Deliverables:* Structural design basis report and calculations, GFC drawings, BBS approvals, structural stability/safety certificate, peer-review responses, structural-audit reports for existing buildings.
- *Employed by:* Design consultancy, developer, PMC, or empanelled with the local authority.
- **GATE:** **A real named-person gate in India.** State building byelaws (framed on NBC 2016 Part 2) require a **structural engineer registered/empanelled with the local authority** to sign the structural design and the stability certificate submitted with the building permit and with the occupancy application; secondary summaries of Part 2 describe "a qualified structural engineer empanelled with the local authority, as defined in the State Bye-Laws". Several municipal corporations additionally mandate **periodic structural audit** of buildings beyond an age threshold by an empanelled structural engineer. **NBC Part 2 Annex A verbatim: NOT FOUND (BIS paywall).** Not nationally licensed: India has **no statutory Professional Engineer licensure** comparable to PE/CEng — the Engineers Bill has never been enacted, so registration is *municipal and state*, not national.

**4.12 Geotechnical Engineer**
- NCO-2015: `2142.0100`; lab tier `3111.0200` Laboratory Assistant, Soil.
- *Does:* Specifies and interprets the ground investigation, sets safe bearing capacity and foundation type, designs/validates excavation support and dewatering, and reviews pile test results.
- *Deliverables:* Geotechnical investigation report, borelogs, SBC recommendation, foundation design basis, slope-stability and shoring design, pile load test interpretation, settlement monitoring review.
- *Employed by:* Geotechnical consultancy, developer, contractor, PMC.
- **GATE:** No personal licence. Test standards gate the numbers: **IS 2720 (soil tests), IS 1892 (subsurface investigation), IS 2911 (piles, incl. load tests)** — *from domain knowledge, not verified this session.*

---

## 5. SAFETY AND ENVIRONMENT

**5.1 EHS Manager / Head-EHS**
- NCO-2015: `3257.0600` **Health, Safety and Environment Officer**; `2141.2500` Safety Engineer; `2141.2600` Occupational Health and Safety Specialist; `2263.9900` Environmental and Occupational Health and Hygiene Professionals, Other.
- *Does:* Builds and runs the HSE management system across sites — risk assessments, permit regimes, training, audits, incident investigation, and the statutory reporting.
- *Deliverables:* HSE plan and policy, HIRA/risk assessments, job safety analyses, permit-to-work system, induction and toolbox-talk records, PPE issue register, inspection and audit reports, **accident/dangerous-occurrence notifications**, incident investigation reports with CAPA, monthly HSE statistics (LTIFR, man-hours), emergency plan and mock-drill records.
- *Employed by:* Contractor, developer, PMC; occasionally a third-party HSE consultancy.
- **GATE:** See 5.2 — the *Safety Officer* is the statutorily named person; the EHS Manager often *is* that person but the title carries no statute.

**5.2 Safety Officer — THE named statutory person on an Indian site**
- NCO-2015: `3257.0600` HSE Officer; `2141.2500` Safety Engineer.
- *Does:* Advises the employer and enforces on the ground — inspects, stops unsafe work, investigates incidents, runs the safety committee, and keeps the statutory safety records.
- *Deliverables:* Safety inspection reports, safety committee minutes, incident/accident notices and investigation reports, training records, scaffold/excavation/lifting inspection records, statutory registers and returns.
- *Employed by:* The employer (contractor or, where it directly employs, the developer).
- **GATE — quote and the live uncertainty:**
  - **BOCW Act 1996, s.38:** *"In every establishment wherein five hundred or more building workers are ordinarily employed, the employer shall constitute a Safety Committee"* consisting of employer and worker representatives in prescribed numbers, with **worker representatives not fewer than employer representatives**; and in such establishments **"the employer shall also appoint a safety officer"** whose **qualifications and duties are prescribed by rules** (https://www.advocatekhoj.com/library/bareacts/buildingandother/38.php).
  - **BOCW Central Rules 1998, Rule 209:** sub-rule (1) requires the appointment, sub-rule (2): *"Duties, qualifications and the conditions of service of safety officers appointed under sub-rule (1) shall be as provided in Schedule VIII"*, and *"Such safety officers may be assisted by suitable and adequate staff."* A commonly-cited construction scale is **1 officer up to 500 workers, 2 up to 1,000, 3 up to 2,000** — **I could not verify this against Schedule VIII; the Schedule VIII text was NOT FOUND in a citable source.** A CAG audit report records the state analogue: *"Rule 251 of RBOCW Rules stipulates constitution of a safety committee and appointment of a safety officer in every establishment wherein 500 or more building workers are ordinarily employed"* (https://cag.gov.in/uploads/download_audit_report/2025/Chapter-V-06995917360a956.94687032.pdf).
  - **⚠ SUPERSESSION RISK — the most important open question in this whole report:** multiple sources state the **OSHWC (Central) Rules, 2026 (G.S.R. 345(E), 8 May 2026)** supersede ~15 central rule-sets *including the BOCW Central Rules, 1998*, and secondary readings of **OSH Code 2020 s.22(2)** put the safety-officer threshold for **building or other construction work at 250 workers** (vs 500 under BOCW), with s.22(1) letting the appropriate government require a safety committee by order rather than by a fixed headcount; one commentary reads the Central Rules as **Rule 14 (safety committee, 500+)** and **Rule 18 (safety-officer scale, 2 officers up to 1,000)** (https://www.taxclue.in/blog/section-22-osh-code-2020-safety-committee-and-safety-officers/ ; https://www.taxclue.in/blog/rule-14-osh-central-rules-2026-safety-committee/ ; https://employmentlaw.lkslaw.com/osh-central-rules-2026). **Verify against the Gazette before relying on any threshold.** Note also that state BOCW rules remain relevant where the state has not replaced them.
  - **Confirmed new construction-specific duties under the 2026 Central Rules** (per https://www.scconline.com/blog/post/2026/05/13/osh-central-rules-2026-key-highlights-and-compliance-guide/): free **annual health examination for building and construction workers aged 40+** by a qualified medical practitioner who issues the **Form-VIII** certificate to both employer and employee; **quarterly mock drills**; drinking water, first aid, rest room and shelter, creche. **Notification duties with hard clocks: death — immediate notice to the Inspector-cum-Facilitator, the District Magistrate/SDO, the police station and the victim's family; injury causing ≥48 hours' incapacity — report within 12 hours after those 48 hours; dangerous occurrence even without injury — within 12 hours to the Inspector-cum-Facilitator and the DM/SDO.** Listed dangerous occurrences include **building or scaffolding collapse, crane or lifting-equipment failure, falls from height and falling objects.** Registration is on the **Shram Suvidha Portal in Form-I**, certificate in **Form-III to be displayed at a visible place**, existing establishments to update Form-I within **6 months**, changes within **30 days**, closure notified within **30 days in Form-V**.
  - **Establishment coverage:** BOCW applies to every establishment employing, or having employed on any day in the preceding 12 months, **ten or more building workers** (s.1(4)); **notice of commencement to the local authority at least 30 days before work starts (s.46)**. *Both from secondary sources this session.*

**5.3 Safety Supervisor / Safety Steward**
- NCO-2015: `3257.0600` (same family, lower tier); `5414.0111` Security Supervisor is a different job.
- *Does:* Patrols the work fronts enforcing PPE, barricading, edge protection and permits, runs toolbox talks, and reports hazards upward.
- *Deliverables:* Daily safety observation/patrol reports, toolbox-talk registers, PPE issue records, unsafe-act/condition log, work-permit sign-offs, scaffold tag records.
- *Employed by:* Contractor, subcontractor.
- **GATE:** Not a statutory office; the *assisting staff* contemplated by Rule 209(1) ("may be assisted by suitable and adequate staff"). Indian market credential: NSQF/NSDC construction safety QPs, CLI/RLI Advanced Diploma in Industrial Safety, NEBOSH IGC.

**5.4 Fire Safety Officer**
- NCO-2015: `3119.0900` Fire Officer; `3119.1000` Fire Inspectors, Other.
- *Does:* During construction: maintains fire points, hot-work permits, means of escape and the emergency plan. At completion: drives the fire NOC — tests the fire system with the fire service and closes their observations.
- *Deliverables:* Hot-work permits, fire-extinguisher and hydrant inspection records, fire drill and evacuation records, fire-fighting installation test reports, **fire NOC / fire safety certificate application and the fire-service inspection compliance file**.
- *Employed by:* Developer, contractor, facility operator; the issuing side is the **state Fire Service**.
- **GATE:** **This is a hard, project-stopping gate in India and it is state law, not central.** For buildings above the height/occupancy thresholds in the state Fire Prevention & Life Safety Act and the local byelaws (both built on **NBC 2016 Part 4 "Fire and Life Safety"**), a **provisional fire NOC is required before construction and a final fire NOC before occupancy** — and **the occupancy certificate will not issue without it**. Several states additionally require a **licensed/empanelled fire-safety consultant or fire officer** to sign the fire system's completion certificate, and periodic fire-safety certificates thereafter. **NBC Part 4 and state Act text: NOT FOUND (BIS paywall / state-specific).**

**5.5 Environmental Officer / EC Compliance Officer**
- NCO-2015: `3257.0400` Environmental Compliance Inspector; `3257.0300` Environment Science and Protection Technician; `3257.0500` Environmental Engineering Technician; `2133.0200` Environment Scientist.
- *Does:* Keeps the project inside its environmental consents — dust, noise and water monitoring, C&D waste routing, sewage/STP operation, and the half-yearly compliance reporting.
- *Deliverables:* **Environmental management plan, ambient air/noise/water monitoring reports, C&D waste management plan and disposal manifests, half-yearly EC compliance reports to MoEFCC/SEIAA and the SPCB, consent-to-establish/consent-to-operate applications and renewals, tree-cutting/transplantation permissions, hazardous-waste records.**
- *Employed by:* Developer, contractor, environmental consultancy.
- **GATE:** **Environmental Clearance under the EIA Notification 2006 (as amended) is required for building and construction projects above the notified built-up-area thresholds, and the EC's conditions bind the promoter**, who must file **half-yearly compliance reports**. Separately, **Consent to Establish / Consent to Operate from the State Pollution Control Board under the Water Act 1974 and the Air Act 1981**, and **C&D Waste Management Rules 2016** duties on the waste generator. *All from domain knowledge — none verified in this session; the EIA Notification building-sector thresholds have been repeatedly amended and litigated and must be checked against the current notification.*

**5.6 Occupational Health — doctor / first-aider / ambulance room; Welfare Officer**
- NCO-2015: `2635.0100` Labour Welfare Officer; `3212.0701` Medical Laboratory Technician (ancillary).
- *Does:* Runs first aid and the health-examination programme; the welfare officer runs creche, canteen, rest shelters, drinking water, latrines and the worker grievance channel.
- *Deliverables:* First-aid register, health examination records (**Form-VIII** certificates), creche and canteen registers, welfare-amenity inspection records, grievance register.
- *Employed by:* Employer (contractor or developer).
- **GATE:** **BOCW Central Rules / the 2026 Central Rules make these *amenities* mandatory, not optional**: drinking water, first aid, rest room and shelter, creche, quarterly mock drills, and the **annual health examination for construction workers aged 40+ certified in Form-VIII by a qualified medical practitioner**. Worker-registration and **welfare-board cess** duties sit alongside (BOCW Welfare Cess Act 1996).

**5.7 Competent Person (lifting appliances, lifting gear, scaffolds, pressure plant) — a *statutorily defined* person**
- NCO-2015: NOT FOUND (it is a legal status, not an occupation).
- *Does:* Tests and examines cranes, hoists, winches, derricks, chains, slings and shackles, and certifies them fit; examines scaffolds and excavation support.
- *Deliverables:* **Certificate of initial and periodical test and examination** — BOCW **Form V** for winches, derricks and accessory gear, issued under **Rules 56 and 73(b) and Schedule I**, carrying the competent person's name, position, **registration/authority number**, test result and seal (https://bocw.hp.gov.in/pdf/Form5June2012_A1b.pdf); register of lifting appliances; scaffold inspection/tag records.
- *Employed by:* Independent testing establishment (not the contractor) — that is structurally the point.
- **GATE:** BOCW Central Rules define a **"competent person"** as a person **approved by the Chief Inspector**, belonging to an Indian testing establishment, with suitable qualifications, experience and skill for testing, examination, annealing and certification. Lifting-appliance provisions sit at **Rules 55–61** (construction, periodic test and examination, safe-load indicators, SWL marking) and lifting gear at **Rules 69–73**. **The 12-month periodicity and the weekly scaffold-inspection frequency commonly quoted in industry: NOT VERIFIED — the rule text was not retrievable (future.indiankanoon.org is blocked in this session and must be allow-listed to pull it).** DGFASLI publishes declarations of competent persons (https://dgfasli.gov.in/public/Admin/Cms/AllPdf/Declaration_of_CP_dated_10_07_2020.pdf).

---

## 6. SURVEY AND SETTING OUT

**6.1 Land Surveyor**
- NCO-2015: `2165.0200` Surveyor, Topographical; `2165.0400` Photogrammetric; `2165.0600` Hydrographic; `2165.0500` Mine; `2165.9900` Cartographers and Surveyors, Other; `1323.0200` **Manager, Land Survey**; `3112.0600` Surveyor, Tidal.
- *Does:* Establishes the legal and physical extent of the site — boundary demarcation against the title documents, topographic survey, contours, and the control network everything else is set out from.
- *Deliverables:* Boundary/demarcation plan, topographic survey drawing with contours, total-station/GNSS raw data and coordinate schedules, control-point schedule with benchmarks, area statement, encroachment report, cut-fill/earthwork volume computation.
- *Employed by:* Developer, consultant, contractor, survey firm; state **revenue department / DILR** for cadastral work.
- **GATE:** **Cadastral/boundary survey for legal purposes is state-gated in India**: the revenue department's **licensed surveyor / Amin / DILR** is the person whose measurement is admissible for mutation and boundary disputes — a private surveyor's plan is evidence, not a record. **Survey of India** holds the national geodetic framework and (historically) restricted-category map/coordinate controls. *No single verifiable national licence URL found — state-by-state. NOT FOUND for a central provision.*

**6.2 Site Surveyor / Setting-out Engineer**
- NCO-2015: `2165.0200`; `7422.1801` Site Surveyor / RF Site Surveyor (telecom-flavoured — poor fit for building).
- *Does:* Puts the drawing on the ground and checks it stayed there — grid lines, column centres, levels, verticality of cores and columns, and as-built deviation checks.
- *Deliverables:* Setting-out records with coordinates and offsets, grid-line and level check sheets, verticality/plumb records for cores and columns, benchmark transfer records, **as-built survey and deviation reports**, floor-to-floor height records.
- *Employed by:* Contractor, PMC.
- **GATE:** None personal. Becomes gated by *tolerance*: CPWD's level test-check rule explicitly treats levels differently — **"the test check has to be based on the number of levels recorded"**, with **AE at not less than 50%** and the levels **"carried out independently by each officer"**, readings **"scored out wherever necessary"** and serious mistakes escalated (SOP 5/24 note + levels SOP). Setting-out error is also where structural non-conformance begins, which pulls in 4.11.

**6.3 Total Station / GNSS Operator; Chainman**
- NCO-2015: nearest `3112.9900` Civil Engineering Technicians, Other; `3112.0701` Assistant Laboratory and Field Technician. Chainman: `9312.9900`/`9313.9900`.
- *Does:* Operates the instrument and holds the staff/prism — occupies stations, records observations, downloads and hands over the data.
- *Deliverables:* Raw observation files, station occupation sheets, instrument calibration/collimation records, field books.
- *Employed by:* Contractor, survey firm.
- **GATE:** None. Instrument **calibration records** are the QA requirement.

**6.4 Quantity Surveyor on site (measurement QS)**
- NCO-2015: **NOT FOUND** (see 2.9). Nearest `2141.0800`.
- *Does:* Measures what was actually built against the BOQ item-by-item, jointly with the client's engineer, and agrees the quantity before it becomes money.
- *Deliverables:* Joint measurement sheets, **MB entries**, quantity reconciliation against BOQ and against drawings, variation quantification, material reconciliation, final measurement.
- *Employed by:* Contractor, PMC, developer, independent QS practice.
- **GATE:** **The joint signature is the gate: "The signature of the contractor or his/her authorized representative is obtained in the Measurement Book for each set of measurements"** (SOP 5/20 ¶6.G) — i.e. a measurement without the contractor's signature, or recorded by an unauthorised person, is not a payable measurement in government practice.

---

## 7. LABOUR AND PLANT

**7.1 Labour Contractor / Petty Contractor / Subcontractor interface**
- NCO-2015: `1120.1200` Working Proprietor, Construction; the *interface manager* role maps to `1323.0100`/`3123.0100`.
- *Does:* Supplies and runs gangs on piece-rate or day-rate; the principal employer's interface person issues work fronts, verifies attendance and output, and certifies the gang bill.
- *Deliverables:* Labour supply agreement/work order, daily attendance and deployment sheet, piece-rate measurement sheets, gang bills and payment records, **wage registers and wage slips**, ID cards, PF/ESI challans, licences.
- *Employed by:* The labour contractor is an employer in its own right; the interface person is employed by the main contractor.
- **GATE:** **This is the densest compliance node on an Indian site.** Contract Labour (Regulation & Abolition) Act 1970 — **principal employer's registration + contractor's licence**, with the principal employer liable for wages if the contractor defaults; **Inter-State Migrant Workmen Act 1979** where workers are recruited across states; **BOCW** registration and cess; **EPF & ESI**; **Minimum Wages**; **Payment of Wages**. CPWD puts the duty on a named officer: **"Engineer-in-Charge ensures that the labour employed by the contractor is paid regularly as per prevailing labour laws, and that no arrears are allowed to accumulate on this account"**; **"ensures submissions of prescribed returns by contractors and scrutinizes them"**; and if the Engineer-in-Charge cannot act on the **Labour Officer's** advice under the Contractor's Labour Regulations, **"he/she immediately reports the matter to his/her higher Authority for obtaining directions"** (SOP **5/11**). **⚠ The CLRA and ISMW Central Rules are among those reported superseded by the OSHWC (Central) Rules, 2026 — re-verify the register/licence forms.**

**7.2 Manpower Planner / IR Officer**
- NCO-2015: `2635.0100` Labour Welfare Officer (nearest); planner: NOT FOUND.
- *Does:* Converts the programme into a labour histogram and then chases it — sourcing, mobilisation, camp allocation, and handling unrest, absenteeism and union/local issues.
- *Deliverables:* Labour histogram and mobilisation plan, skill-mix plan, labour camp allocation and inspection records, grievance and disciplinary records, settlement/agreement minutes, headcount MIS.
- *Employed by:* Contractor, developer.
- **GATE:** None personal; triggers 7.1's statutory set and the labour-camp/welfare amenity rules.

**7.3 Timekeeper / Muster Clerk**
- NCO-2015: **`4110.0500` Time Keeper**.
- *Does:* Records who worked, where, and for how long — biometric/manual attendance, overtime, and the data the wage register is built from.
- *Deliverables:* **Muster roll, attendance register, overtime register, wage register, wage slips, employment cards/ID, register of workers, advance and fine/deduction registers.**
- *Employed by:* Contractor, labour contractor.
- **GATE:** **These are *statutory registers an employer must keep and produce to the Inspector* — the clerk produces them but the *employer* is liable for their accuracy and preservation.** Under the OSHWC regime the registration and return forms are now portal-based (**Form-I registration on the Shram Suvidha Portal, Form-III certificate displayed at a visible place, Form-V closure**). **The specific register forms under the BOCW Central Rules vs the 2026 Central Rules: NOT VERIFIED — this is exactly where the supersession bites.**

**7.4 Plant & Machinery Manager**
- NCO-2015: nearest `1324.0100` Manager, Material Control/Manager Materials (logistics-flavoured); `3122.5200` Supervisor and Foreman, Machinery Fitting and Repairing; `7233.0700` Mechanic, Earth Moving Machinery.
- *Does:* Owns the fleet — deployment against the programme, hire-vs-own calls, preventive maintenance, fuel control, spares, and keeping every machine's certification current.
- *Deliverables:* Plant register with hour/km meters, deployment and idling reports, preventive maintenance schedules and job cards, breakdown log, fuel consumption and reconciliation, hire agreements and invoices, **statutory test certificates for lifting appliances, insurance and (for road-registered plant) fitness and PUC**.
- *Employed by:* Contractor, plant hire firm.
- **GATE:** **The test certificate chain in 5.7 is the manager's hard gate** — a crane without a current competent-person certificate (BOCW **Form V**, Rules 56/73(b), Schedule I) must not lift. Operators of cranes/hoists are separately gated in practice by trade certification; road-registered plant carries **Motor Vehicles Act** fitness and driver licensing.

**7.5 Plant Operators (crane, batching plant, earthmoving)**
- NCO-2015: **`8343.0200`–`8343.0900`** Crane Operator (diesel-electric, pneumatic, hydraulic, mobile, EOT, gantry, overhead, derrick, derrick-magnetic); `8343.9900` Crane, Hoist and Related Plant Operators, Other; **`8114.0200` Batching and Mixing Plant Operator (Construction)**; `8342.9900` Earth Moving and Related Plant Operators, Other; `8341.0300` Tractor Driver, Construction; `8342.1900` Sand Blast Operator, Construction; `7215.0100`/`.0101` Rigger.
- *Does:* Operates the machine, carries out the pre-start check, and refuses an unsafe lift or load.
- *Deliverables:* Daily pre-start/pre-use checklists, logbook (hours, loads, lifts), defect reports, lift plans acknowledged (for critical lifts), batching plant batch records and calibration logs.
- *Employed by:* Contractor, plant hire firm.
- **GATE:** No central Indian operator licence for site plant (unlike many jurisdictions). Gates that do bite: **the machine's competent-person certificate**, the **lift plan** for critical lifts, and **MV Act licensing for road-going plant**. Batching plant: calibration records are the QA gate (and a batching plant in a fixed yard may itself be a **factory** — see 9.6).

**7.6 Store Keeper / Site Stores In-charge**
- NCO-2015: **`4321.0100` Store Keeper**; `4321.0200` Store Distributor; `4321.0401` Manager-Stores Operation; `4321.0501` Store Ops Assistant; `4321.0302` Incoming Inspection Technician.
- *Does:* Receives, inspects, stores and issues material against indents, and keeps the stock account that must reconcile to consumption.
- *Deliverables:* **Goods receipt notes (GRN), material inspection reports, bin cards, stock ledger, issue slips/indents, cement register, steel register, dismantled-material register, returnable/non-returnable gate passes, scrap register, stock reconciliation and physical verification reports.**
- *Employed by:* Contractor, developer.
- **GATE:** **Cement and steel are *specially* controlled in Indian government practice**: consumption monitoring is mandated (Works Manual **5.6.7**, SOP **5/13** "Monitoring of Cement and Steel and Other Materials and Check on their Consumption"), the **cement register and dismantle register are named site documents** (SOP **5/14**), steel receipts are **test-checked 10% monthly by the Engineer-in-Charge** with **permitted variation of 0.5% (bars ≤12 mm) / 1% (larger)** and a breach triggering **100% check plus a recorded investigation** (SOP 5/24 ¶2(iii)). For purchases, **"measurements and details thereof are to be recorded in the Measurement Book if the purchase is…"** — i.e. even material receipt lands in the MB.

**7.7 Logistics / Material Coordinator / Expeditor**
- NCO-2015: `1324.0100` Manager, Material Control; **`1324.0102` Material Co-ordination Manager**; `3122.4000` Supervisor and Foreman, Material and Freight Handling; `3323.0200` Purchasing Agent / `3323.0401` Purchase Executive.
- *Does:* Makes material arrive when the programme needs it — tracks POs against the look-ahead, chases vendors, plans inbound logistics, over-dimensional-cargo permits and site unloading.
- *Deliverables:* Material requirement schedule tied to the programme, PO/delivery tracker, expediting reports, inbound logistics plan, ODC route permits, delivery schedules and unloading plans, shortage/escalation log.
- *Employed by:* Contractor, developer, EPC.
- **GATE:** None personal. GST e-way bill and (for ODC) state transport permits are the compliance artefacts. **Sand/aggregate/soil movement needs a valid mineral transit pass / royalty clearance under the state minor-mineral rules — a frequent stop-work cause in India.** *Not verified this session.*

**7.8 Security Supervisor; Gate / Weighbridge Clerk**
- NCO-2015: `5414.0111` Security Supervisor; `5414.0121` CCTV Supervisor; gate clerk nearest `4321.0100`.
- *Does:* Controls access and material movement in and out; weighs and records every inbound/outbound load.
- *Deliverables:* Gate inward/outward register, weighbridge slips and tare/gross records, material gate passes, visitor and labour access records, incident/theft reports, CCTV logs.
- *Employed by:* Contractor, developer, security agency.
- **GATE:** **Private Security Agencies (Regulation) Act 2005** licenses the *agency* and prescribes guard training/verification. Weighbridge: **Legal Metrology Act 2009** — the weighbridge must be verified and stamped, and the slip is the primary quantity evidence for bulk material. *Neither verified this session.*

---

## 8. SPECIALIST SITE MANAGEMENT

**8.1 Formwork Engineer**
- NCO-2015: nearest `2142.0300` Civil Engineer, Structural; craft `7115.0201` Assistant Shuttering Carpenter.
- *Does:* Designs or validates the formwork and its support, plans the cycle, and sets the striking criteria tied to concrete strength.
- *Deliverables:* Formwork design and calculations, formwork/shuttering layout drawings, cycle plan, **striking/de-shuttering schedule with strength criteria**, pre-pour formwork and props checklist, formwork inspection and sign-off record, repair/replacement register.
- *Employed by:* Contractor, formwork system supplier (Doka/PERI-type), consultant.
- **GATE:** **IS 456:2000 fixes the minimum stripping times/strength criteria — striking early is both a structural and a legal exposure.** Internationally, formwork is **temporary works** and therefore gated by **BS 5975** procedural control (see 8.2). India has **no statutory temporary-works sign-off** — that is the single biggest structural gap between Indian and UK/EU site governance.

**8.2 Temporary Works Coordinator (TWC) / Falsework Coordinator — the international gate India lacks**
- NCO-2015: **NOT FOUND.**
- *Does:* Controls the whole temporary-works process on a site — maintains the temporary works register, ensures every item has a design and a design check at the right category, and **issues the permit to load and the permit to strike**.
- *Deliverables:* **Temporary works register, design brief per item, temporary works design + independent design check certificate (BS 5975 check categories), erection-complete inspection record, permit to load, permit to dismantle/strike, TWC appointment letter.**
- *Employed by:* Principal contractor (appointed in writing).
- **GATE:** **BS 5975** sets the procedural framework (Designated Individual → Temporary Works Coordinator → Temporary Works Supervisor), with the **TWC's signed permit to load as the control point**. Under **CDM 2015** the principal designer must ensure the contractor's temporary-works designer has access to relevant health-and-safety information and that there is technical interaction with the permanent-works designer (https://www.designingbuildings.co.uk/wiki/CDM_2015_principal_designer_duties). **Who appoints the TWC under BS 5975: NOT FOUND in a citable authority this session** (only a practice-exam site asserted it is the Principal Contractor — not reliable). **India: no equivalent statutory role. Falsework/scaffold codes exist (IS 14687 falsework guidelines, IS 2750 steel scaffolding, IS 3696 scaffolding/ladder safety — from domain knowledge, not verified) but no named sign-off person.**

**8.3 Piling / Foundation Engineer**
- NCO-2015: `2142.0300` Civil Engineer, Structural; `2142.0100`; drilling supervision `3121.0200` Supervisor and Foreman, Well Drilling.
- *Does:* Runs the piling rigs and the pile record — monitors boring/driving, concrete volume vs theoretical, cut-off levels, and interprets integrity and load tests.
- *Deliverables:* **Pile driving/boring records per pile (depth, strata, time, concrete volume, overbreak), pile layout and as-built pile position plan, reinforcement cage records, pile integrity test (PIT/low-strain) reports, initial and routine pile load test reports, cut-off level and pile cap records, deviation/remedial pile proposals.**
- *Employed by:* Piling specialist contractor, main contractor, geotechnical consultant, PMC.
- **GATE:** **This is "work below ground level which owing to its situation cannot subsequently be checked" — in CPWD it is in the mandatory-check list, which means the recording officer's personal liability attaches and the AE may be required to record or 100%-check it** (SOP 5/24 ¶1(iii)(b), ¶1(iv)(a)(i)). Test standards: **IS 2911** (design & construction of pile foundations, incl. load tests). *Not verified this session.*

**8.4 High-rise / Core Engineer (jump-form, slipform)**
- NCO-2015: `2142.0200`/`2142.0300`.
- *Does:* Drives the vertical cycle — core jump/climb sequence, verticality and survey control at height, concrete pumping and placing logistics, crane and hoist interface.
- *Deliverables:* Core cycle plan, jump/climb sequence and anchor records, **verticality and plumb records per lift**, concrete pumping plan, high-strength concrete mix and temperature records, climbing-system inspection and anchor-load test records, wind/weather stop criteria.
- *Employed by:* Contractor, formwork system supplier.
- **GATE:** Climbing formwork anchors and the loading of partially-cured concrete are classic **temporary works** (8.2) — internationally permit-to-load gated, **in India ungated by statute**. The **lifting appliances** on the core (hoists, cranes) carry the BOCW **Form V** competent-person certification (5.7). Fire during high-rise construction is a specific NBC Part 4 / state fire-service concern (5.4).

**8.5 MEP Coordination Engineer**
- NCO-2015: `2142.0301` Plumbing Site Engineer; `7412.1002` Site Engineer-Control Panel; `3123.0300`/`.0302` plumbing supervision; `3123.0400` Electrical Supervisor-Wiring.
- *Does:* Makes services fit and sequence — coordinates HVAC/electrical/plumbing/fire routes against structure and ceiling voids, clears clashes, fixes sleeve and cut-out locations before the pour, and sequences services installation against finishes.
- *Deliverables:* Coordinated services drawings and composite ceiling/shaft sections, clash resolution log, **sleeve and cut-out drawings issued *before* the pour**, builder's work schedule, services shop drawings and approvals, hanger/support layout, pre-pour services clearance sign-off.
- *Employed by:* Contractor, MEP subcontractor, PMC, consultant.
- **GATE:** No personal licence for coordination. **But each service it coordinates is separately gated: electrical installation work must be done by a State-licensed electrical contractor under the direct supervision of a certificate-of-competency holder (see 9.4); plumbing/water connection work is licensed-plumber work under municipal byelaws; lifts come under the state Lifts & Escalators Act; fire systems under the state fire service.**

**8.6 Commissioning Manager**
- NCO-2015: nearest `2144.1402` Service Engineer-Installation and Commissioning.
- *Does:* Takes the building from built to working — plans and sequences pre-commissioning, commissioning and integrated systems testing, chairs the commissioning meetings, and owns the completion documentation that triggers handover.
- *Deliverables:** **Commissioning plan and sequence, system-by-system pre-commissioning checklists, commissioning procedures, test records (balancing, flushing, pressure, insulation resistance, earth resistance, relay/protection, lift load tests), integrated systems test (IST) / cause-and-effect matrix results, snag/punch lists A & B, O&M manuals, as-built drawings, warranties, training records, taking-over certificate.**
- *Employed by:* Contractor, developer, specialist commissioning/CxA firm, PMC.
- **GATE:** **Energisation is legally gated. CEA (Measures relating to Safety and Electric Supply) Regulations 2010 reg. 43 "Approval by Electrical Inspector"** must precede energisation of installations above the prescribed voltage; **reg. 29(2): "No electrical installation work which has been carried out in contravention of sub-regulation (1) shall either be energised or connected to the works of any supplier"**; **reg. 30 "Periodical inspection and testing of Installations"** and **reg. 31 "Testing of consumer's installation."** Lifts need a **licence/permission to operate from the state Lift Inspector**. Fire systems need the **final fire NOC**. And the whole bundle feeds the **occupancy certificate** — which in CPWD **"the Engineer-in-Charge shall obtain… from local bodies with the help of concerned Architect/Consultant before handing over of buildings"** (para 5.17.3(1)), and in private development is the **promoter's** duty under RERA s.11(4)(b). ⚠ **CEA's 2024 compendium indicates a 2023 replacement of the 2010 Regulations — confirm the current regulation numbers.**

**8.7 T&C (Testing and Commissioning) Engineer**
- NCO-2015: `2144.1402` Service Engineer-Installation and Commissioning; discipline-specific `2142.0900` Civil Engineer, Public Health (for PHE systems).
- *Does:* Performs the tests — fills in the test sheets, witnesses with the client/consultant, and re-tests after defects.
- *Deliverables:* Signed test sheets per system and per circuit, calibration certificates of test instruments, balancing reports (air/water), hydrostatic and pneumatic test records, insulation-resistance and earth-continuity records, protection-relay settings and test records, functional test records, witness sign-off sheets.
- *Employed by:* MEP subcontractor, contractor, third-party T&C agency.
- **GATE:** See 8.6. **Electrical testing and the certificate of completion for an installation is tied to the *competency-certificate holder*, not the engineer's job title** (CEA reg. 29(1)).

**8.8 Electrical Supervisor / Wireman — a real, hard Indian personal licence**
- NCO-2015: **`3123.0400` Electrical Supervisor, Wiring**; `3122.6000` Line Supervisor, Electrical; `7411.9900` Building and Related Electricians, Other.
- *Does:* Supervises every electrical installation, alteration and repair on site and signs the installation's completion/test certificate; the wireman/permit-holder does the work.
- *Deliverables:* Installation completion and test certificates, earth-resistance and insulation-resistance test records, as-installed single-line diagrams and panel schedules, the **register of designated persons**, energisation applications to the Electrical Inspector.
- *Employed by:* State-licensed electrical contractor; the main contractor engages that contractor.
- **GATE — quoted verbatim from the CEA (Measures relating to Safety and Electric Supply) Regulations, 2010 (consolidated: https://www.cbip.org/CEARegulations/July%202019/Consolidated%20Regulation%20CEA%20Safety.pdf):**
  - **Reg. 29(1): "No electrical installation work, including additions, alterations, repairs and adjustments to existing installations, except such replacement of lamps, fans, fuses, switches, domestic appliances of voltage not exceeding 250V and fittings as in no way alters its capacity or character, shall be carried out upon the premises of or on behalf of any consumer, supplier, owner or occupier… except by an electrical contractor licensed in this behalf by the State Government and under the direct supervision of a person holding a certificate of competency and by a person holding a permit issued or recognised by the State Government."**
  - **Reg. 3(3): "No person shall be designated under sub-regulation (1) unless,— (i) he possesses a certificate of competency or electrical work permit, issued by the Appropriate Government. (ii) his name is entered in the register referred to in sub-regulation (2)."** Reg. 3(2) requires the owner/consumer/contractor to **"maintain a register wherein the names of the designated persons and the purpose for which they are engaged, shall be entered"**, and **reg. 4(1)–(2)**: that register **"shall be produced before the Electrical Inspector when required"**, and if the designated person lacks the qualification **"he shall recommend the removal of the name of such persons from the register."**
  - So: **three distinct licensed persons — the licensed electrical *contractor* (firm), the *certificate-of-competency holder* (supervisor) who must give direct supervision, and the *permit holder* (wireman) who does the work — plus a register the Electrical Inspector can demand.** ⚠ Confirm against the **2023** replacement.

**8.9 Lift / Escalator Erection & Inspection**
- NCO-2015: NOT FOUND distinctly; nearest `2144.1402`.
- *Does:* Erects, tests and maintains lifts; the inspector licenses them to carry people.
- *Deliverables:* Lift installation and test records, load/overspeed/brake test certificates, lift licence application and renewal, AMC and periodic inspection records.
- *Employed by:* Lift OEM/erector; inspection side = **state Lift Inspector / Electrical Inspectorate**.
- **GATE:** **State Lifts and Escalators Acts/Rules require permission to erect and a licence to operate, with periodic inspection** — and CPWD's SOP flags lifts among the **high-unit-rate items requiring special test check** ("all major equipments for AC, lifts, Generator sets, Sub-station equipments, fire works", SOP 5/24 ¶1(iv)(b)(vii)). *State Act text not verified this session.*

**8.10 Façade Engineer**
- NCO-2015: nearest `2142.0300`; glazing craft `7125.0100` Glazier (Construction).
- *Does:* Designs/validates the cladding system and proves it — structural glazing design, thermal and wind-load checks, mock-up performance testing, and installation supervision.
- *Deliverables:* Façade design basis and calculations, shop drawings, **performance mock-up (PMU) test reports (air/water/structural)**, anchor pull-out test records, glass and sealant compatibility certificates, installation checklists, maintenance (BMU) access plan.
- *Employed by:* Façade consultancy, façade subcontractor, developer.
- **GATE:** No personal licence. **CPWD puts "steel cladding, structural glazing etc." in the high-unit-rate mandatory test-check class** (SOP 5/24 ¶1(iv)(b)(iii)). Anchor and mock-up test reports are the de facto acceptance gate.

**8.11 Precast / RMC Yard Manager**
- NCO-2015: **`8114.0200` Batching and Mixing Plant Operator (Construction)**; `1321.0500`-style plant manager families; `3122.x` manufacturing supervision.
- *Does:* Runs a production facility — mix design and batching control, mould and demoulding cycle, curing, element marking, storage, dispatch and erection sequencing.
- *Deliverables:* Batch records, cube results per batch, mix-design and calibration records, element identification and traceability register, dispatch notes and erection sequence, lifting-insert pull-out test records.
- *Employed by:* Contractor's precast yard, RMC/precast supplier.
- **GATE:** **This is the one place where the *Factories Act 1948* genuinely bites on a construction supply chain.** A fixed precast or RMC plant carries on a *manufacturing process* in *premises*, so it can be a **"factory" under s.2(m)** — bringing factory licensing, a **Manager named in Form 2 (notice of occupation)**, the **Factories Act safety-officer threshold (1,000 workers under s.40B)**, statutory registers and annual returns, and **Electricity-Rules first-aid/resuscitation signage "in every factory as defined in clause (m) of section 2 of the Factory Act, 1948… in which electricity is used"** (CEA reg. 28(1), read in the text). **Whereas the construction *site* itself is normally outside the Factories Act and inside BOCW/OSH Chapter XI. This analytical boundary is NOT verified against a source in this session — it is the most commonly misapplied gate in Indian construction and should be confirmed.**

**8.12 Demolition Engineer**
- NCO-2015: `2142.0100`; labour `9312.9900`.
- *Does:* Surveys the structure, designs the sequence and the temporary support, controls dust/noise/debris, and manages the hazardous-material (asbestos) element.
- *Deliverables:** Structural/pre-demolition survey, demolition method statement and sequence drawings, temporary support/propping design, hazardous-material (asbestos) survey and removal records, **C&D waste manifests**, exclusion-zone and public-protection plan, permits from the local body, post-demolition certificate.
- *Employed by:* Demolition specialist, contractor, developer; government side under CPWD's **para 8.3 "Demolition of Un-safe Buildings/Structures"** and **8.4 "Disposal of Government Buildings"** (which require a **sanctioned survey report**, a reserve price fixed on assessed salvage value, and approval by the delegated authority).
- **GATE:** **BIS is actively adding "safety in construction including demolition operations of tall buildings" to the NBC Part 7 revision** (BIS panel agenda via services.bis.gov.in) — i.e. currently thin. **C&D Waste Management Rules 2016** bind the generator. Municipal demolition permission and, for unsafe buildings, the s.264-type municipal notice process apply. *Not verified this session.*

**8.13 Tunnel / Deep Excavation Engineer**
- NCO-2015: `2142.0100`; mining-adjacent supervision `3121.0100` Supervisor and Foreman, Mining and Quarrying.
- *Does:* Controls ground and support — monitors convergence/settlement, directs support installation, manages dewatering, ventilation and gas monitoring, and runs the instrumentation response plan.
- *Deliverables:* Excavation support design and method statement, instrumentation and monitoring plan with trigger levels (green/amber/red) and readings, daily face/excavation log, dewatering records, gas and ventilation monitoring records, settlement monitoring of adjacent structures, third-party property pre-condition survey.
- *Employed by:* Contractor (tunnelling/metro/deep-basement specialist), geotechnical consultant, PMC.
- **GATE:** No construction-specific national gate; metro/rail projects carry their own safety regimes (RDSO/CMRS inspection and **Commissioner of Metro Rail Safety sanction before passenger operation**). Confined space and excavation provisions sit in the BOCW Central Rules. *Not verified this session.*

**8.14 Licensed Plumber / Sanitary Inspector interface**
- NCO-2015: `3123.0300` Supervisor and Foreman, Plumbing and Pipe Fitting; `3123.0301` Plumbing Foreman; `3123.0302` Plumbing Supervisor; `2142.0301` Plumbing Site Engineer; `3257.0100` Sanitary Inspector; `7112.0201` Plumbing Mason.
- *Does:* Installs and tests water supply and drainage; applies for and obtains the water and sewer connection.
- *Deliverables:* Plumbing layout and as-builts, pressure and leak test records, water/sewer connection application and sanction, drainage completion certificate, STP commissioning records.
- *Employed by:* Plumbing subcontractor; the licensing side is the **municipal corporation / water board**.
- **GATE:** **Most Indian municipal byelaws require water-supply and drainage connection work to be executed by a *licensed plumber* registered with the water board, and the plumbing completion certificate he signs is an input to the occupancy certificate.** **CPWD requires AE test-check of "not less than 50% of the plumbing work for sanitary and water supply" and EE "not less than 10%" (SOP 5/24 ¶1(v)(c), ¶2(ii)(b)) — and pipes buried in floor or masonry are in the cannot-subsequently-be-checked mandatory class.** *Byelaw text state-specific, NOT verified.*

---

## 9. CROSS-CUTTING GATES WORTH STATING ONCE (so no job above has to repeat them)

1. **No national Indian engineering licence.** There is no PE/CEng equivalent; the Engineers Bill was never enacted. Gating is (a) **municipal/state registration** of architects, structural engineers, supervisors, plumbers and electrical supervisors under building byelaws built on **NBC 2016 Part 2**, (b) **Council of Architecture registration under the Architects Act 1972**, which is the only *protected title* in the Indian built environment, and (c) **contract**. Consequence: the most consequential Indian signature on private work is an **architect's or structural engineer's certificate filed with a local body**, not an engineer's licence.
2. **Who signs what, Indian government work** — the chain is: **JE records → AE check-measures ≥50% of value and personally inspects → Divisional Accountant test-checks calculations and the officer enters "Check and bill" → EE (Engineer-in-Charge) test-checks 10% (plus mandatory 10% RCC, 10% plumbing, 10% monthly steel receipt) and passes → EE records provisional and final completion certificates (with SE or CE above ₹10 crore) → EE obtains the occupancy certificate.** Every test check must be **shown item-by-item in the MB and attested by the checking officer's dated initials**, with a **collective record marked "Satisfactory"/"Unsatisfactory"** per MB. (CPWD Works Manual 2022 paras 5.6.4, 5.12, 5.17.1–5.17.3; SOP 5/10, 5/20, 5/24.)
3. **Who signs what, Indian private development** — **promoter** (RERA registration, quarterly QPR, s.11(4)(b) completion/occupancy, s.14(3) five-year defects), **architect + engineer + CA in practice** (the three-way 70%-account withdrawal certificate, s.4(2)(l)(D); Maharashtra Forms 1/2/3), **registered structural engineer** (stability certificate), **licensed electrical supervisor** (energisation), **fire service** (fire NOC), **local body** (completion/occupancy certificate).
4. **Who signs what, international** — **NEC4:** *Project Manager* certifies Completion and runs all contract management; *Supervisor* tests, notifies Defects (only up to the defects date, cl. 43.2) and **issues the Defects Certificate** to Client, Project Manager and Contractor (cl. 13.6, 44.3) — and the Supervisor **cannot** do Project Manager acts unless delegated. **CDM 2015:** client appoints a **Principal Designer** (pre-construction phase) and a **Principal Contractor** (construction phase) whenever there is more than one contractor; for a domestic client, the contractor in control becomes PC by default. **BS 5975:** Designated Individual / **Temporary Works Coordinator** / Temporary Works Supervisor, with the TWC's **permit to load** as the control point. **ISO 19650-2:** *appointing party* / *lead appointed party* / *appointed party*, with the **information management function nominated in the tender response (cl. 5.3.1)** and competence assessed at cl. 5.1.1 and 5.3.1. **FIDIC 2017 "the Engineer"/Contractor's Representative: NOT FOUND.** **CIOB and PMI role definitions: NOT FOUND (paywalled).**
5. **Statutory registers an Indian construction employer must keep** (names and forms now in flux): registration (**Form-I** on Shram Suvidha, certificate **Form-III** displayed, closure **Form-V**), register of workers, **muster roll, wage register, wage slips, overtime register, advance/fine register**, accident and dangerous-occurrence records with the 12-hour/immediate clocks, **health examination Form-VIII** for construction workers 40+, **register of designated persons** (electrical, CEA reg. 3(2)), lifting-appliance register and **Form V** competent-person certificates, and — on government works — **site order book, online PMS inspection register, cement register, dismantle register, test register, guard file, MB register (CPWA 92)**. ⚠ **The BOCW/CLRA/ISMW register forms are reported superseded by the OSHWC (Central) Rules, 2026 — confirm against G.S.R. 345(E) before building any compliance product on them.**

---

## 10. WHERE THE WORK IS ARITHMETIC OR RECORD-KEEPING vs WHERE IT NEEDS A PERSON ON SITE

Read as: **(a) computation** = deterministic, checkable, automatable; **(b) document/record production** = drafting, assembling, registering, templating — automatable *up to the signature*; **(c) physical presence or personal legal liability** = cannot be delegated to a machine without breaking the law or the evidence chain.

**Overall delivery (1.1–1.9)**
- (a) Budget roll-up and variance, cash-flow modelling, EAC/forecast, delay quantum, contract-notice *deadline* arithmetic (the 10-day reply, 14-day EOT application, 30-day BOCW pre-commencement notice, 30-day RERA defect rectification, 12-hour accident report).
- (b) PEP, monthly MIS/board pack, minutes, contract notices and replies, EOT/variation files, RERA registration and quarterly QPR assembly, closeout file.
- (c) Chairing the decision that resolves an escalation; **recording the completion certificate (EE, with SE/CE above ₹10 crore) after physical inspection — para 5.17.2 ties it to the officer "under whose tenure the work is completed"**; the promoter's/authorised signatory's declarations under RERA; the Independent Engineer's completion certificate.

**Planning and controls (2.1–2.10)**
- (a) **Almost entirely computation**: CPM forward/backward pass, float, resource levelling, earned value (PV/EV/AC, CPI/SPI, EAC/ETC), S-curves, cost-value reconciliation, quantity take-off and rate analysis, Monte Carlo risk, as-planned-vs-as-built and time-impact analysis.
- (b) Programme documents, dashboards, registers (document, drawing, RFI, submittal, NCR, risk, change), transmittals, TIDP/MIDP, BEP, responsibility matrix, bid documents.
- (c) **Very little.** Two exceptions: progress *verification* (claimed % vs physical reality — someone must look), and the tender-scrutiny certificate where a CPWD officer must certify **"that I have personally conducted a test check of all the computed… tenders"**. **This family is the single most automatable in the entire list.**

**Site execution (3.1–3.9)**
- (a) Quantity computation from dimensions, abstracting, deviation statements, RA-bill arithmetic and running totals, secured advance, material reconciliation (cement/steel vs theoretical consumption), **the test-check percentage arithmetic itself (50% of cumulative value, 10% of measurements, 0.5%/1% steel variance)**.
- (b) DPR/WPR, MB/e-MB entries, measurement sheets and abstracts, RA bills, checklists, site order book entries, material indents, as-builts.
- (c) **Heavy and irreducible.** CPWD states it in terms a machine cannot satisfy: **"The Assistant Engineer is to personally inspect all the works of any magnitude"**; **"The officer who records/test checks the measurements for an item of work will be responsible for the quality, quantity/measurements and dimensional accuracy of that item"**; **"The signature of the contractor or his/her authorized representative is obtained in the Measurement Book for each set of measurements"**; **"The measurements are recorded in ink"** and **"No entry is erased or overwritten"** on a book that **"may have to be produced as evidence in a court of law"**; **"Recording of measurements only by authorized persons."** And the mandatory class — foundations, reinforcement, buried pipes, encased steel — exists *precisely because* it cannot be checked later: if nobody was standing there, the fact is gone.

**Quality (4.1–4.12)**
- (a) Statistical evaluation of cube results (mean, standard deviation, acceptance criteria), mix-design proportioning, UPV/rebound correlation and classification, cover and dimensional tolerance checks, test-frequency arithmetic against pour volume, NCR ageing/trend.
- (b) QAP/ITP/checklists, NCR register and closures, test-report compilation, material approval register, calibration register, quality dossier, TPQA observation registers.
- (c) **Witnessing is the product.** A test result with no witness is a number, not a record: **sampling itself is a named physical act — "Samples for tests are taken mostly by the Junior Engineers, or some by the Assistant Engineers. Samples for 10% of mandatory tests are collected by the Engineer-in-Charge. 10% of the field tests are got done by the Engineer-in-Charge in their presence."** Likewise **"Approved samples of materials are signed by the approving authority and the contractor and preserved till the end of the project."** Hold-point release, pre-pour reinforcement inspection, NDT on the actual element, and the structural engineer's stability certificate are all presence-plus-liability.

**Safety and environment (5.1–5.7)**
- (a) Thinnest arithmetic of any family: LTIFR/man-hours, exposure and monitoring averages against limits, PPE and amenity ratios against headcount, **and the threshold arithmetic that decides whether a statutory officer is required at all (500 vs 250 workers — itself currently uncertain)**.
- (b) HSE plan, HIRA/JSA, permits, training and toolbox registers, inspection reports, statutory notifications and registers, mock-drill records, EC half-yearly compliance reports, C&D manifests.
- (c) **The most personal-liability-dense family in the list, and the least automatable.** The *Safety Officer* is a statutorily appointed named person (BOCW s.38 / Rule 209 / Schedule VIII; OSH Code s.22(2)); the **competent person** who certifies a crane in **Form V** must be *approved by the Chief Inspector* and belong to a testing establishment; the notification clocks start at a physical event and name real recipients (Inspector-cum-Facilitator, District Magistrate/SDO, police station, the victim's family); the **health examination is certified by a qualified medical practitioner in Form-VIII**; and stopping unsafe work is an act of authority exercised in a place. **Nothing here can be discharged by producing a document.**

**Survey and setting out (6.1–6.4)**
- (a) **Almost pure computation**: coordinate geometry, traverse adjustment and closure, level reduction, cut-fill and earthwork volumes (grid/section/prismoidal), verticality deviation, as-built vs design deviation, area computation.
- (b) Setting-out records, control-point schedules, level sheets, as-built survey drawings, deviation reports, area statements.
- (c) Occupying the station and holding the staff; **joint measurement with the contractor's representative** (the MB signature); the licensed revenue surveyor's demarcation where legal boundary matters.

**Labour and plant (7.1–7.8)**
- (a) Wage computation (minimum wage, overtime, deductions), PF/ESI computation, labour histogram vs programme, plant utilisation and idling %, fuel reconciliation, stock reconciliation (opening + receipts − issues − closing), **BOCW cess on cost of construction**.
- (b) **The heaviest *statutory record-production* load of any family**: muster roll, wage register and slips, overtime/advance/fine registers, register of workers, Form-I/III/V, GRNs, bin cards, stock ledger, cement/steel/dismantle registers, gate passes, plant register, test certificates, hire agreements, PO trackers.
- (c) Physical verification of attendance against bodies on site (ghost-worker risk is the whole reason timekeeping exists); physical stock verification; **the competent person's test of the lifting appliance**; receiving and inspecting material at the gate; the licensed electrical supervisor's **direct supervision** of installation work; and the principal employer's exposure under CLRA if the contractor does not pay.

**Specialist site management (8.1–8.14)**
- (a) Formwork and falsework design calculations and striking-time/strength criteria; pile capacity, concrete volume vs theoretical, settlement and convergence against trigger levels; façade wind/thermal/structural calculations; commissioning balancing and test-value evaluation; crane lift-plan load/radius/configuration checks; batching plant calibration.
- (b) Method statements, design and check certificates, temporary works register, pile records, instrumentation logs, PMU and anchor test reports, commissioning plans and test sheets, O&M manuals and as-builts, energisation and licence applications.
- (c) **The permits are physical acts by named people and this is where India differs most from international practice.** Internationally, the **TWC's permit to load and permit to strike** gate the whole temporary-works chain under BS 5975 — a signature given after walking the erected falsework. **India has no statutory equivalent**, so the same risk is carried informally by the formwork/site engineer with no named-person protection. What *is* gated in India is energisation (**CEA reg. 29(1)**: licensed contractor + **direct supervision** by a certificate-of-competency holder + permit-holder doing the work; reg. 29(2): work done in contravention **"shall not either be energised or connected"**; reg. 43 Electrical Inspector approval), lifts (state Lift Inspector licence), fire (final NOC before occupancy), and — for a fixed precast/RMC yard — potentially the **Factories Act named Manager**. Pile and foundation work is the canonical case of (c) swallowing (a) and (b): **it is in the "cannot subsequently be checked" class, so if the recording officer was not present, no amount of computation or documentation can reconstruct the fact.**

---

## 11. EXPLICIT "NOT FOUND" LIST (so nothing above is mistaken for verified)
- **NCO-2015 8-digit codes:** every code in this report is from a third-party transcription whose author flags possible errors; dge.gov.in and labour.gov.in both refused download in this session. **4-digit stems are ISCO-08-aligned and safe; 8-digit suffixes are TO BE CONFIRMED.**
- **NCO-2015 has no family for:** Quantity Surveyor, Planning Engineer, Project Controls, Document Controller (construction), BIM/CDE/Information Manager, Billing Engineer, Temporary Works Coordinator, NDT Technician, Risk Manager, Development Manager, Commissioning Manager (only `2144.1402` Service Engineer-Installation and Commissioning), Snagging Engineer.
- **BOCW Central Rules 1998 Schedule VIII** (safety officer qualifications and duties) — text not retrievable.
- **BOCW Central Rules lifting-appliance periodicity (the commonly quoted 12 months) and scaffold inspection frequency (weekly)** — not verified.
- **Whether and how far the OSHWC (Central) Rules, 2026 supersede the BOCW Central Rules 1998**, and **the correct safety-officer threshold for building/construction work (500 vs 250)** — unresolved, and it is the most consequential open question here.
- **RERA Act verbatim text** — indiacode returned 403; section numbers reliable, wording reconstructed.
- **NBC 2016 Part 2 (Annex A qualifications of registered professionals), Part 4 (Fire & Life Safety), Part 7 (Construction Management, Practices and Safety)** — BIS paywall; only scope/structure confirmed, and **Part 2 is under a Fourth Revision (draft March 2025)**.
- **CIOB** and **PMI** role definitions — paywalled, not cited.
- **FIDIC 2017 cl. 3 "the Engineer"** and **cl. 4.3 Contractor's Representative** — no accessible text found.
- **BS 5975** — who appoints the TWC, and the check-category table — no citable authority retrieved.
- **Factories Act 1948 applicability boundary between a construction site and a precast/RMC yard** — analytical, not sourced.
- **CPWD SOP 5/14 (site documents) and 5/16 (independent testing facilities) detail** — located but not read in full.
- **CEA Safety Regulations: the 2010 text was read verbatim, but CEA's 2024 compendium indicates a 2023 replacement** — regulation numbers in 8.8/8.6 may have moved.
- **IS 516 Part 5 edition year** — BIS listings disagree (2018 vs 2021).
- **EIA Notification 2006 building-sector thresholds, BOCW cess rate, IS 2911/2720/1892/456 stripping tables, state fire Acts, state Lifts Acts, Legal Metrology, Private Security Agencies Act, minor-mineral transit passes** — stated from domain knowledge, none verified this session.
- **future.indiankanoon.org is blocked by this session's network settings** — allow-listing it would let me pull the BOCW Central Rules and Schedule VIII verbatim, which is the largest single gap.