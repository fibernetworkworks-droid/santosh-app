# Hoola Construction & Real Estate — the AI Employee (plan)

Owner's ask: *"PERFECT NOW A AI EMPLOYEE IN BUILDING AND CONSTRUCTION INDUSTRY"* (4 Nov 2026), and this
session: *"LETS WORK ON HOOLA AI EMPLOYEE. READ THE CONSTRUCTION AI EMPLOYEE PDF --- BUILD THE PLAN FOR
HOOLA AI CONSTRUCTION EMPLOYEE"*.

Eighth in the AI-employee series. This is the plan only. **Nothing is built until she says GO on a
wave.** The register it builds on is now in the tree at
`docs/research/building_industry/07_ai_employees_register.md` (123 candidate AI Employees, 15 fields,
transcribed from her PDF so every session can grep it), which itself compresses the six sourced reports
in the same folder (276 jobs). Read the register first; this plan only decides **what ships, in what
order, behind which gates**.

---

## 1. The check first: what Hoola ALREADY has here (verified in the tree, 5 Nov 2026)

The v0.372 lesson (a 1,789-line tool nearly duplicated) and the register's own instruction — *"do not
rebuild; extend"* — mean the plan starts from what exists. Every row below was read in the source, not
remembered.

| Already shipped | What the tree actually holds | Register #s | Verdict |
|---|---|---|---|
| `server/app/theka/` — *site_manager, Theka sahayak* | 10 tables: settings, tenders, projects, BOQ (`theka_boq`), measurement book (`theka_mb`), bills, subs, sub-bills, material, diary; tools `theka` / `theka_dekho` in `agent/theka_tools.py` | 52 (tender watch), 62 (subs), 71 (wage basis, work orders), 88 (RA bill, partial) | **The contractor's commercials exist.** Extend, never rebuild. |
| `server/app/sitesup/` — *site_supervisor* | 12 tables: sites, activities, progress, labour, material, indent, safety, stops, **pour, cube, snag** (+ rules.py, api.py, WIRING.md); tools `sitesup` / `sitesup_dekho` | 70 (daily log), 64 (progress, partial), 72 (pour/cube records, partial), 78 (snag, partial), 81 (safety log, partial) | **The field diary exists, with concrete records already.** Extend. |
| `architect_assistant` (`agent/archassist_tools.py`) + `interior_designer` | project file, FSI estimate, drawing register, approvals, RFI, fee invoice; interiors end to end | 7, 13 | **Done.** Do not rebuild. |
| `property_manager`, `society_manager` | letting, society running | 100, 101 | Done for the operations field; their gaps (102–109) are a later wave. |
| `server/app/employee/hire.py` + `roles.py` | the AI Employees Hub: hire rows with `group` headings (Game / Software / Education / Enterprise), `live` flags, pitches; console sidebar `hire` section | — | **The delivery vehicle.** Construction gets its own group row here. |
| `server/app/engineering/` — CAD Engineer | CadQuery solids, FEA, CAM, 2D views, drawing PDF, DXF/STEP, a locked Python sandbox | (product CAD) | Not buildings — but its **sandbox** is the pattern for the calculation lanes. |
| Engines | `docstudio/` (pdf/docx/xlsx/pptx/html generators = HOOLA PRINT), `pylab/` (locked analytics), `net/khata.py` (KhataAccount/KhataEntry ledger), `payroll/`, `kharcha/`, `maps.py`, `appmaker`, WhatsApp campaigns (official API), vision review, approval cards (`approvekey.py` + phone `approve_sheet.dart`), live voice stack (`voice.py`) | named per row below | Reuse — each appears in the phase tables with its register #. |

**So the gap is not "a construction employee".** The site diary and the contractor's commercials already
exist and are hireable. The gap is:

1. **The builder's paper machine** — approvals/RERA files, bye-law checks, QTO/BOQ working papers,
   contracts/claims, tendering: nothing exists (Wave 2).
2. **The shared construction core** — one register of who is hired, one tier gate, one state-rule-pack
   loader, one IS-1200 formula library: nothing exists (Phase C0).
3. **Money around the site** — labour law, store reconciliation, demand letters, handover, builder's
   books: fragments exist inside theka/sitesup but no owned desk (Wave 1).
4. **Voice-first field input** — the supervisors who feed all of the above do not type (§8).

## 2. The gate — PREPARE, never CERTIFY (the spine of the whole department)

From the research, held in one line: **the application is the owner's act, the technical certification is
reserved to a named licensee on a specific register, and preparation is unreserved** — 70–80% of the
labour, almost none of the liability. *"An agent that drafts those certificates and lets the licensee
sign is useful and lawful; an agent that signs or files them is forgery."*

| Tier | Meaning | How it lands in code |
|---|---|---|
| **A** — admin / prepare | records, registers, muster, bills-as-drafted, demands, calendars | Hoola owns end to end; the human taps to send or pay. Approval card on every outward step (WhatsApp demand letter, payout, report). |
| **B** — assist a named licensee | checks, drafts, calculations **for** an architect / engineer / QS / CA who signs | Every output is a **working paper addressed to the professional**, shows the clause/rule it applied and its source+date, and ends with the signer line empty. The tool description and system prompt both say who signs. |
| **C** — reserved | certify, sign, submit, approve a design, accept work, release a certificate | **Refusal texts in `construction/gates.py`**, wired like `fence.py`: the model cannot produce these even if asked, the card/prompt says who must do it instead. |

The NEVER list is the register's, verbatim (§9 here). Two hard extensions of the house rules for this
department: **money never moves without the tap** (a wage payout, a RA-bill payment, a demand letter all
wait for the card — same law as payroll today), and **no number without a trail** (every computed
quantity/rate/percentage carries the formula and the input rows that produced it, so a QS can re-check
it on paper — the `is1200.py` law in §6).

## 3. The four open questions — answered here, on the record (she can overturn any)

| Question (from the register) | Answer the plan is built on | Why |
|---|---|---|
| **Which seat first?** | **Contractor / site** — extend the live Theka Sahayak + Site Supervisor (Wave 1). | Both are shipped, hireable and field-tested; the seat is mass-market and mobile-first; every Wave-1 item is tier A (no licence risk); it touches cash in week one (measurement → RA bill → wages), which is what makes a builder pay. Builder-developer (approvals/RERA/sales) is Wave 2 and needs a customer with a live project; architect/consultant belongs to `DESIGN_DESK_PLAN.md`; FM/society employees already exist and their gaps can wait. |
| **State first?** | **Maharashtra / MahaRERA** as the worked example, exactly as the register assumes. | Best documented (the reports' worked example); UDCPR + Model Building Bye-Laws + MahaRERA cover the most ground. Rule packs are **data with an owner and a checked-on date** (§6) — expansion to another state happens when a paying customer in that state asks, never speculatively. |
| **Drawings: DWG/PDF or IFC?** | **PDF/DWG-first for Wave 2; open formats (IFC/BCF/IDS) only in Wave 3.** | The register's finding 3: every Indian regulatory submission is a DWG or a PDF, and "without an IDS, 'we exchanged IFC' guarantees nothing checkable". So Wave 2 does **document-level** checking (vision + text layers + scale bars) and says so; it never claims model-level checking. Wave 3 reads IFC/IDS and still labels what it read. |
| **Voice-first?** | **Yes — voice + photo is the primary input for site records** (§8). | Hindi/Marathi supervisors do not type; the call/voice stack, `SantoshService` background stream and photo attach already exist. The daily log that must be filled *at the site* is the winning wedge. |

## 4. The boundary with DESIGN_DESK_PLAN (anti-duplication, written down)

`docs/DESIGN_DESK_PLAN.md` already owns **the design & consultancy disciplines**. The two plans must
never double-build (the v0.372 lesson). The split, by register number:

| Register #s | Owner | Note |
|---|---|---|
| 7, 13 | shipped (`architect_assistant`, `interior_designer`) | not touched by this plan |
| 8, 9, 10, 11, 12, 14, 15, 16, 17 | **Design Desk plan** (its discipline phases) | This plan builds only the **9 bye-law checker's state-pack mechanism** as shared infrastructure (`construction/statepacks/`), which the Design Desk checker then consumes — one pack loader, two consumers. |
| everything else (1–6, 18–124) | **this plan** | — |

If she later GOs both plans in the same week, the Desk/Hub groups stay separate but `statepacks/`,
`gates.py` and `docstudio` remain single-owner shared modules.

## 5. The shape in Hoola

**Hub.** One new group heading in `server/app/employee/hire.py`, beside `GAME_GROUP`/`SW_GROUP`/
`EDU_GROUP`/`ENT_GROUP`:

```
CONST_GROUP = "Construction & Real Estate"   # v0.5XX the construction employees' heading in the Hub
```

Hire rows are added **per wave, `live:True` only when the phase ships** (the EDU_GROUP precedent:
v0.453 put already-live suites into the Hub with a pitch each). Wave 1 rows:

| Hire key (new) | Register #s | Pitch (one line, Hinglish-friendly) | Backing |
|---|---|---|---|
| `site_supervisor` (exists) | 64, 70 | *Site ka roznama: awaaz aur photo se, bina typing.* | extend `sitesup/` |
| `site_manager` (exists) | 62, 71, 88 | *Theka sahayak: nap → RA bill → theka.* | extend `theka/` |
| `const_store` | 61 | *Saaman aaya, gaya, bacha — sab hisaab.* | new tables beside `sitesup` |
| `const_labour` | 85, 87, 90, 91 | *Mazdoor kaayda, wages, BOCW cess, kitaab.* | new `construction/labour.py` + `payroll` reuse |
| `const_quality` | 72, 75, 76, 78 | *Pour, cube, ITP, NCR, punch — record sab ka.* | extend `sitesup` pour/cube/snag + new ITP/NCR tables |
| `const_meetings` | 67 | *Baithak ke minute aur action, khud peeche.* | new small module, `docstudio` minutes |
| `const_customer` | 92, 98 | *Demand letter se possession tak, grahak ke paise.* | new tables + WhatsApp official API |

Wave 2 adds: `const_approvals` (28–34, 36), `const_rera` (35, 93), `const_qs` (37–39, 41, 49),
`const_contracts` (44–46, 48, 50, 51), `const_tender` (52–56, 58–60), `const_drawqa` (9, 16, 73).
Wave 3 adds: `const_bim` (18–21, 25, 109), `const_survey` (22–24, 27, 77), `const_predesign` (10–12, 74),
`const_perf` (82, 104, 110–118). The register rows with no wave yet (1–6, 40, 42, 43, 45?, 47, 57, 63,
65, 66, 68, 69, 79, 80, 83, 84, 86, 89, 94–99, 102, 103, 105–108, 119–123) stay out of the Hub until she
asks — listed honestly in §12.

**Server layout** (one new package; per-desk modules follow the `theka`/`sitesup` shape — models in the
package, `X_TOOLS / X_LABELS / X_HANDLERS` in `agent/`, registered in `agent/tools.py`, mounted in
`main.py`, models imported in `db.init_db`):

```
server/app/construction/
  register.py      # the 123-row register as DATA (id, name, field, tier, human_gate, wave, status)
  gates.py         # tier-C refusal texts + is_tier_c() used by every construction tool
  statepacks/      # rule packs as data: maharashtra.json first (schema in §6)
  is1200.py        # IS 1200 measurement formulae, each returning {qty, formula, inputs} (Wave 2)
  labour.py        # C4 tables: muster, licence, BOCW, ESI/PF, cess, minimum-wage rates
  customer.py      # C5 tables: demands, receipts, handover, DLP tickets
  quality.py       # C6 tables: ITP, NCR, hold points, material-test lots (pour/cube/snag stay in sitesup)
```

**Client.** Console: the Hub group + one Construction desk page per hire (the Systems/Enterprise desk
pattern). Phone: extend `lib/ui/sitesup_screen.dart` and `theka_screen.dart` first (voice-log button,
RA-bill card); new screens only where a desk needs one (`store_screen.dart`, `labour_screen.dart`,
`demand_screen.dart`) following `sitesup_screen.dart`'s structure. Voice: the call stack gets the
construction tools via the `VOICE_VIA_KAAM` lane first (heavy tools are never declared to Gemini Live —
the voice law); only `sitesup` log actions earn a place in `VOICE_TOOL_NAMES` if the pilot proves them
everyday call work.

## 6. Two laws that make this desk trustworthy: state packs and formula trails

**The state-pack law.** Every rule (setback, FAR, fire clause, RERA form, minimum wage, cess %) is a row
in `construction/statepacks/<state>.json`, never code:

```json
{"state": "maharashtra", "authority": "UDCPR 2020 / MahaRERA / BOCW Act 1996",
 "rule_id": "udcpr.setback.residential", "value": {...}, "clause": "6.1",
 "source": "UDCPR 2020, notified 2 Dec 2020", "checked_on": "2026-11-05", "owner": "research session + named human"}
```

The loader refuses a pack older than its `refresh_by` date (a stale pack makes the checker say **"ye
niyam purana hai, ~ dated — pehle verify karo"** instead of answering), every checker output prints its
clause + source + checked-on date, and packs are versioned in-repo so a change is a diff she can read.
Someone must own the refresh (a recurring cost — said plainly in §11).

**The formula-trail law.** Every computed number (quantity, rate build-up, wage, deduction, % complete
where arithmetic) is stored with its formula and input row-ids (`is1200.py` returns `{qty, formula,
inputs}`), rendered on the working paper as the measurement sheet a QS would rule by hand. Recompute and
the trail must reproduce the number bit-for-bit — that is the test. Legal conclusions (delay entitlement,
LD liability, classification for GST) are **never** computed — only the working paper is produced, per
register finding 4.

## 7. The waves → phases (each phase = one shippable version: server + tests + console + phone + CI)

### Wave 1 — records and money (tier A; the register: *"builders pay for it at once"*)

Members: 61, 62, 64, 67, 70, 71, 75, 78, 85, 87, 88, 90, 91, 92, 98.

| Phase | Ships | The work, concretely | Files |
|---|---|---|---|
| **C0** | The department scaffold | `CONST_GROUP` in the Hub with the two existing employees re-parented into it; `register.py` (the 123 rows as data, `status` per row: live/extension/new); `gates.py` tier-C refusals wired into `fence.py`-style checks; the construction system-prompt block ("PREPARE, never CERTIFY; every output names its human"); `statepacks/` loader + `maharashtra.json` v0 (no checker uses it yet). | `employee/hire.py`, NEW `construction/` package, `agent/prompts.py`, tests |
| **C1** | **Daily site records, voice-first** (70, 64) | The voice+photo daily log (§8): supervisor speaks, Hoola fills activities/progress/labour/safety rows (`SsActivity/SsProgress/SsLabour/SsSafety` — tables already exist), asks the five missing questions, sends the DPR card; physical % by activity with variance to plan; the DPR as a one-tap WhatsApp/PDF share. | extend `sitesup/service.py` + `agent/sitesup_tools.py`, `voice` lane, tests `test_v0XXX_const_c1.py` |
| **C2** | **Measurement → money** (88, 62, 71) | MB entries → RA bill draft with the deductions chain (retention, TDS, GST on works contract, labour cess) → payable total, all with trails; subcontract work-orders: scope, rate basis, advances, running sub-bills (ThekaSub/ThekaSubBill exist — add rate-basis + advance ledger); wage calc from theka's rate basis, payout on **her tap** through payroll. | extend `theka/service.py` + `agent/theka_tools.py`, `payroll/` reuse, tests |
| **C3** | **Store & material** (61) | GRN, issue, min-max per consumption norm, reconciliation (indent vs issue vs consumed → wastage %), cement/steel lot stock; the daily shortage alert on the DPR. | NEW `construction/store.py` (beside sitesup's SsMaterial/SsIndent, which stay), tools, tests |
| **C4** | **Labour law & books** (85, 87, 90, 91) | Muster rolls from C1's labour rows; contract-labour licence + BOCW registration + renewals on a statutory calendar; ESI/PF and minimum-wage checks (rates from the state pack); BOCW cess + TDS calculator (determined % on a stated base); builder's project-wise books on `net/khata.py` primitives with vendor ageing. | NEW `construction/labour.py`, `statepacks` wage rows, tests incl. pack-staleness |
| **C5** | **Customer money & handover** (92, 98) | Milestone-linked demand letters (template + carpet-area schedule + interest clause shown), receipts, loan-disbursement coordination notes; handover checklists + snag closure (reads SsSnag) + key/utility transfer tracker + DLP clock with vendor dispatch. | NEW `construction/customer.py`, docstudio templates, WhatsApp official API (opt-in), tests |
| **C6** | **Quality & meeting records** (67, 72, 75, 76, 78) | ITP per activity with hold points + NCR log + close-out tracking; pour/cube records graduate to IS 456 grade-acceptance **drafts** (acceptance stays the QA engineer's — tier B edge inside a tier A desk, said on the card); material-test lot register (NABL results, retest dates); meeting minutes with action chasing. | NEW `construction/quality.py`, extend `sitesup`, tests |

Wave 1 exit test: one real contractor runs a week on C1–C5 — log by voice each evening, one RA bill
produced with its trail, one wage payout per tap, one demand letter sent — and zero tier-C outputs
anywhere.

### Wave 2 — the file-builders and checkers (tier B; a named licensee on every output)

Members: 9, 16, 28, 29, 35, 36, 37–39, 44–46, 52–56, 72, 73, 81, 93.

| Phase | Ships | The work, concretely | Files |
|---|---|---|---|
| **C7** | **Approvals office** (28–34, 36) | Per-authority checklist + status + fees + validity calendar (state-pack rows); the building-permission **file assembler**: forms, drawing sets, ownership, NOCs, undertakings packaged as DWG/PDF via docstudio — submission stays with the owner/licensee; fire-NOC packet, EC/CTE-CTO tracker, utility liaison, heritage/AAI/CRZ screener, OC/CC packet builder. | `statepacks` approvals rows, NEW `construction/approvals.py`, docstudio, tests |
| **C8** | **QS desk** (37–39, 41, 49) | IS 1200 take-off from drawings (vision + scale-bar; PDF/DWG-first) with the formula trail; rate build-up from SOR/quotes; BOQ + abstract; cost controller (budget vs committed vs actual); retention/price-variation/escalation by contract formula. **Never** a certificate of measurement. | NEW `construction/is1200.py` + `qs.py`, pylab for the heavy arithmetic, tests incl. recompute-bit-for-bit |
| **C9** | **RERA & escrow** (35, 93) | Project registration data pack, quarterly update drafts, Form 3/4/5 data prep, 70% escrow tracking + reconciliation vs certified progress; the declarations stay with promoter/CA/architect/engineer (tier B, named on every form). | NEW `construction/rera.py`, `statepacks` MahaRERA rows, tests |
| **C10** | **Contracts, tendering, drawing QA** (9, 16, 44–46, 52–56, 72, 73, 81) | Contract register + obligations + notice-period alerts; variation papers + claims **working papers** (entitlement matrix, notice-compliance check — submission reserved); tender watch + bid/no-bid sheet + pre-qualification dossier + bid price pack; BBS drafts from drawings; EHS permits-to-work **drafts** + toolbox-talk records (the permit itself is the safety officer's — tier B); bye-law checker consuming the shared state packs (Design Desk consumes the same loader). | NEW `construction/contracts.py`, `tender.py`, extend `quality.py`, vision lane, tests |

### Wave 3 — model-level and certificate-adjacent (open formats + a licensee on every output)

Members: 18–21, 10–12, 22–24, 26, 47, 82, 104, 110–118. **SHIPPED v0.560.0** (C11–C15; built as
0.550.0 — the dev chain's collision wave took 0.551–0.559 while it sat built) after Wave 2
proved the packs and the trails. The register's 23 waved members are all homed (`register.py
WAVE3_HOME`); the plan's earlier stragglers shipped as Wave 3.5 below.

| Phase | Ships | The honest limit printed on every card |
|---|---|---|
| **C11** ✅ | BIM/Information desk `const_bim` (18–21): pure-Python IFC STEP reader (classes, GUIDs, declared quantities, placements), model health, ISO 19650 naming, CDE register + supersede + transmittals, clash candidates on declared axis-aligned extents (+ NOT-CHECKABLE counted), BCF 2.1 zip out, IDS subset check (entity + property facets; rest UNVERIFIED), 4D mapping + 5D rows on the model's own quantities (qty × rate only with a sourced rate) | *"Model-level check on the open formats only. A PDF was never a model."* |
| **C12** ✅ | Pre-design desk `const_predesign` (10–12): IS 875 load take-down + IS 456 cl 39.3 preliminary sizing (50 mm module, rounding shown) + cl 23.2.1 depth route (spans > 10 m refused), MEP estimates on FED factors, fire rule rows (clause + source) → declared vs limit, fire demand arithmetic | *"PRELIMINARY working paper for <the named engineer>. The stability certificate / Form A-B is theirs."* |
| **C13** ✅ | Survey desk `const_survey` (22–24, 26): coords + LandXML CgPoints, loop traverse closure, shoelace boundary vs the 7/12, grid cut/fill volumes (kept separate), CSV deviations with RMS (E57/LAS NOT parsed), RERA carpet statement under HER wall policy vs the MahaRERA 3% pack row, discrepancy pack sign EMPTY. Delay desk `const_delay` (47): baseline + as-built as DATA (criticality = HER marks, no CPM), windows, slip days, notice-compliance arithmetic, working paper for the forensic planner. #82 incident investigations ride `const_quality` (close needs the safety head's name; open actions block) | *every result "explained, not certified"* |
| **C15** ✅ | Green & performance desk `const_green` (104, 110–118): meters + her bill's tariff slabs + EPI benchmark, ECBC/daylight sourced rows, the energy-model INPUT register (EnergyPlus not run), EPD carbon hot-spots (factor source required), CPHEEO water + RWH on her IMD station, green-credit tracker (a sum; the rating is the assessor's), Cx scripts + issue log, T&C tolerance arithmetic, M&V least-squares baseline (a, b, r2 printed) + the savings identity, her IPMVP option | *"Records + arithmetic; every certification refused."* |

Shipped together with: the national `statepacks/india.json` (IS 875 / IS 456 / CPHEEO rows, cited;
`rule_row(state, id)` reads the state pack first, both refuse when stale), two new tier-C gate rows
("certify an area statement", "certify a survey"), 29 new tables, 10 new tools (registry 569 → 579),
5 Hub hires, VOICE_VIA_KAAM, tests `test_v0550_construction_w3.py` (24).

### Wave 3.5 — the five stragglers (v0.565.0; owner: "GO WAVE 3.5")

Members: 25, 27, 74, 77, 109 — the Wave-3 rows the owner's Wave-3 GO excluded, homed per §5's original
mapping onto the existing desks (NO new tools; the three desks grew actions). Same laws: open formats,
recorded names, tier C refusals. **SHIPPED v0.565.0.**

| Phase | Ships | The honest limit printed on every card |
|---|---|---|
| **C11b** ✅ | **As-built + twin on `const_bim`** (#25, #109): the as-built SET register — HER required list, received/na marks BY NAME, completeness % + missing list (the set's approval stays with the site architect / QS — new tier-C row) · the digital twin as a DATA-LINK register: asset → IFC GUID + model, sensor feed rows with a SOURCED band flagged out-of-band (the twin is a register, never a live 3D view or a sensor platform) · COBie Component CSV check (required headers, rows missing asset/type) | *"Completeness is arithmetic on YOUR list; approval is the site architect's. The twin is a data link, not a 3D view."* |
| **C13b** ✅ | **GIS + setting-out on `const_survey`** (#27, #77): GeoJSON read as TEXT for Polygon/MultiPolygon rings — CRS recorded as fed, areas ONLY in projected metres (degree layers REFUSED: a degree has no square metres; inner rings counted, never silently subtracted) · flood / seismic / zoning overlays as HER readings (the map is never fetched or interpreted) · setting-out sheets + as-laid vs design plan deviations (RMS, out-of-tolerance) · level checks with the sign KEPT (up ≠ down) | *"Lat/lng has no square metres and we don't pretend otherwise; the zoning value is YOUR reading off the map."* |
| **C12b** ✅ | **Formwork & scaffold on `const_predesign`** (#74): contact-area take-off by plain geometry on HER dims (slab soffit / beam soffit + 2 sides / column 4 faces / wall both faces) · striking time vs the IS 456 cl 11.3 **Table 10** pack rows (7 new national rows: 11 → 18; OPC + ambient > 15 °C ONLY — blending cements and cold weather REFUSED, the maturity maths is the engineer's) · props vs the supplier table's allowable (source required) · scaffold tag register (ok / defective / altered, competent person's NAME) — the striking ORDER and the tag itself stay tier C (two new rows) | *"The take-off and the table comparison are ours; the strike order and the green tag are the site engineer's / competent person's."* |

Shipped together with: `india.json` 11 → 18 rows (IS 456 Table 10 striking periods, scope said on the
row), tier-C gate 30 → 33 rows (approve the as-built set / order formwork striking / tag a scaffold
safe), 7 new tables (cbim_asbuilts + docs, ctwin_assets + readings, cgis_layers + overlays,
cpd_scaffolds), registry STILL 580, Hub rows + prompt block + `__init__` carry Wave 3.5, tests
`test_v0565_construction_w35.py`.

## 8. The voice-first daily log (the wedge, designed now so C1 builds it once)

The supervisor's evening, one flow: he calls (or the scheduled briefing calls him — the morning-briefing
pattern exists), speaks Hinglish: *"Aaj slab ki nayi castting hui, Dooley gang ne brickwork kiya, do
majdoor absent, cement do bag bache."* Hoola writes `SsProgress` (activity + qty from the BOQ item),
`SsLabour` (gang, present/absent), `SsMaterial` (stock delta), asks the five questions the log still
needs (*"safety talk hua? koi stop? koi snag?"*), stores the photos he sends into the same day's rows,
then reads back the one-line summary and pushes the DPR card to the owner. Everything is tier A; nothing
is sent anywhere without the card if it leaves the tenant. The same rows feed C2's measurement and C4's
muster — that reuse is the whole reason voice-first is the wedge and not a gimmick.

## 9. What Hoola will never do (tier C — verbatim from the register, wired in `gates.py`)

Sign or stamp a drawing, structural design, stability, fire, MEP, completion or occupancy certificate;
file a permission application in the licensee's or owner's name; certify RERA percentage completion or
escrow withdrawal; accept or reject work on site (inspection pass, concrete cube acceptance); approve a
design or a change order; sign a contract; release a payment or a bank guarantee; issue a notice,
termination or LD deduction; decide delay entitlement; certify measurement or an RA bill; give a safety
clearance or permit-to-work; certify green rating, commissioning or energy audit; give a
structural-safety verdict; approve the as-built set; order formwork struck; tag a scaffold safe.

## 10. The pilot (what "GO" should start)

One small contractor or mid-size builder, ONE project, ONE state (Maharashtra): daily site log by voice
+ measurement + wage/RA-bill + material reconciliation + RERA/escrow paperwork. Record-keeping with
direct cash impact; no certificate signed by software. Success measured in the owner's own numbers: the
log kept daily without typing, the RA-bill cycle from MB to submission shortened, zero wage disputes from
the muster, and every output that needed a human signature carried an empty signer line with the right
name printed under it.

## 11. Effort, cost, honesty

- **Sizes** (one version each, house ritual): C0 ~half a session; C1, C2, C4, C5 ~one session each; C3,
  C6 smaller; Wave 2 phases are one-to-two sessions each (C8 the largest — the IS 1200 library is the
  single biggest build in the plan); Wave 3 only after a customer proves demand.
- **Recurring costs, named**: state-pack refresh (a human owns each pack; the loader enforces the date),
  Maps usage for expediter/logistics rows (billed per element — the maps law), storage for site photos
  (the largest tenant-data growth in the house so far), model calls for vision QA of drawings (Wave 2).
- **Tests, per phase**: tables+tools CRUD, the trail-recompute law, tier-C refusals, pack staleness,
  approval-card gating on every send/pay, voice-log parsing fixtures (Hinglish phrases from the pilot).
  A `construction` quality card (`python -m app.quality construction`) in the `app/quality` pattern:
  right tool for every one of the register's 15 fields, wrong family 0, gates all refusing.
- **Version ritual**: unchanged — `main.py APP_VERSION` + `pubspec` (+build) + test pins, commit
  `vX.Y.Z: <summary>`, push main, CI, APK link + VPS commands. Server-first phases deploy without an APK.

## 12. Not in this plan (said plainly)

Register rows outside Waves 1–3.5 (1–6, 40, 42–43, 57, 63, 65–66, 68–69, 79–80, 83–84, 86, 89, 94–99,
102–103, 105–108, 119–123) wait for her word or a paying customer; FM/society gaps (102–109 except the
twin steward #109 and the energy row #104) belong to the existing property/society employees; the Design
Desk disciplines stay in `DESIGN_DESK_PLAN.md` (§4); nothing here builds a WhatsApp automation beyond
the official API; and no phase touches the frozen Mera PC / desktop surface.
