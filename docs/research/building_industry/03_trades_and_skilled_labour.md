# INDIAN BUILDING-TRADES OCCUPATION REGISTER
### Trades that physically build buildings — NCO-2015 codes, NSQF/QP codes, engagement, measurement, and the legal gates

---

## 0. SOURCE BASE (what each claim rests on)

| Source | What it gave | URL |
|---|---|---|
| **IRC:127-2018, Annexure 3 & 4** (IRC = Indian Roads Congress; the annexures are the *consolidated* CSDCI and IESC QP lists, 101 + 33 job roles) | The only single consolidated list of CSDCI + IESC construction job roles with QP code, NSQF level, minimum education and training hours | https://law.resource.org/pub/in/bis/irc/irc.gov.in.127.2018.pdf |
| **CSDCI Qualification Packs (NSDC QP repository)** — I downloaded and text-extracted ~60 current QP PDFs | Current version number, current NSQF level, and the **NCO-2015 alignment code** printed on each QP | `https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/CON_Q0203_v5.0.pdf` (pattern: `CON_Q<code>_v<ver>.pdf`) |
| **IESC Qualification Packs** (Infrastructure Equipment Skill Council) | Plant-operator QP codes, levels, NCO-2015 codes | `https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/IES_Q0103_v4.0.pdf` |
| **WMPSC / Plumbing SSC QPs** (`PSC/Q…`) | Plumber and pipe-fitter job roles | `…/qpPdf/PSC_Q0104_v5.0.pdf` |
| **ESSCI QPs** (`ELE/Q…`) | RAC / HVAC technician roles | `…/qpPdf/ELE_Q3102_v4.0.pdf` |
| **SCGJ QPs** (`SGJ/Q…`) | Solar PV installer | `…/qpPdf/SGJ_Q0101_v4.0.pdf` |
| **CEA (Measures relating to Safety and Electric Supply) Regulations, 2010**, consolidated text (CBIP) | **Verbatim** Reg. 3(3) and Reg. 29(1) — the electrical licensing gate | https://www.cbip.org/CEARegulations/July%202019/Consolidated%20Regulation%20CEA%20Safety.pdf |
| **CAG Performance Audit on Welfare of Building & Other Construction Workers, Appendix 4.1** | The **54 notified categories of BOC workers** (Jharkhand notifications 1051/05-04-2011 and 1951/04-11-2015) — a real statutory occupation list | https://d1jmc0u14z2tmp.cloudfront.net/uploads/download_audit_report/2022/12-Appendices-067c19efa7a3b42.68436109.pdf |
| **NQR (National Qualification Register)** | Current revised qualification files, NQR codes, deactivation dates | https://www.nqr.gov.in/ |
| **DGT CTS / ATS / CITS curricula** (CSTARI mirrors; dgt.gov.in itself was unreachable from this session) | ITI trade names + NSQF levels | e.g. https://www.cstaricalcutta.gov.in/images/CTS%20Mason%20(Building%20Constructor)_CTS_NSQF-4.pdf ; https://www.dgt.gov.in/sites/default/files/2025-01/Plumber_CTS3.0_NSQF-2.5.pdf ; https://www.dgt.gov.in/sites/default/files/2025-01/Wireman_CTS2.0_NSQF-3.pdf ; https://www.dgt.gov.in/sites/default/files/2024-12/Lift%20_%20Escalator%20Mechanic_CTS2.0_NSQF-4.pdf |

**Honest gaps declared up front**
- **BOCW Act 1996 own "Schedule" — NOT VERIFIED.** indiacode.nic.in returned 403 and two mirror copies failed. The Act's operative definitions are s.2(1)(d) "building or other construction work" and s.2(1)(e) "building worker"; I could **not** retrieve them verbatim this session. **The occupation list that actually governs registration is a STATE notification, not a central schedule** — proven by the CAG appendix above (Jharkhand = 54 categories; CAG separately records Punjab's own list starting "Workers engaged in stone cutting, breaking and grinding"). Treat "the BOCW schedule of building workers" as a **state-by-state notified list**.
- **BOCW Central Rules 1998** — labour.gov.in and dgfasli.gov.in both failed. From search extracts: **Rule 65** = "Operation of lifting appliances"; **Rule 81** = "Qualification of operator of lifting winches and of signaller" (conditions include knowledge of inherent risks and periodic medical examination per **Schedule VII**); a further rule requires the operator/rigger/derrick operator to be **above 18 and sufficiently competent and reliable**, and bars anyone under 18 from controlling a lifting appliance or signalling. **Rule numbers for the 18-year and competence clause: NOT VERIFIED** (secondary source only).
- **`future.indiankanoon.org` is blocked in this session's network settings** — it has to be allowed for the BOCW Central Rules and Maharashtra Lifts Act full texts.
- **No NSQF QP found for:** waterproofing applicator (standalone), fire-sprinkler fitter, duct/sheet-metal fabricator (standalone), blaster, piling-rig operator, bhishti/water carrier, site cleaner, watchman. Marked **NOT FOUND** in place.

**Note on QP versions:** IRC:127-2018 captured the 2018 levels. Several have since been **re-levelled** (NSQF now uses half-levels). Where the current QP PDF disagrees with IRC:127, I give **the current QP's** level and say so. NCO-2015 codes are 8-digit (`family.occupation`), e.g. `7214.1101`.

---

## 1. STRUCTURE TRADES

### 1.1 Mason / bricklayer — *mistri, raj mistri, chinai mistri, gawandi (Mar.), kadiyan (Guj.)*
| | |
|---|---|
| **NSQF job roles** | **Brick Mason — CON/Q0113 v4.0, NSQF 4** (electives: General / Plastering; options: VDF Flooring / Random Rubble Works) · **Mason General — CON/Q0103, NSQF 4** (v1.0 only; NCO-2004/7122.20 — this pack is old and being superseded by CON/Q0113) · **Associate Mason — CON/Q0116 v1.0, NSQF 3** · **Assistant Mason — CON/Q0102 v3.0, NSQF 3** · **Helper Mason — CON/Q0101 v4.0, NSQF 2** (option: Manual Earthwork) · **Rural Mason — CON/Q3603 v4.0, NSQF 3.5** (General/Bamboo/CSEB/Random Rubble) · **Assistant Rural Mason — CON/Q3605 v2.0, NSQF 3** · **Rural Mason-Helper — CON/Q3604 v2.0, NSQF 2** |
| **NCO-2015** | **7112.0200** (Brick Mason / Bricklayer) · **7122.0601** (Assistant Mason) · **9313.0301** (Helper Mason — building-construction labourer family) |
| **ITI route** | DGT CTS **Mason (Building Constructor)**, NSQF 4 |
| **Does** | Sets out from grid lines and level marks; lays bricks/blocks/stone in cement mortar to line, plumb and course; builds walls, partitions, parapets, sills, copings, arches, chajjas, drain and manhole chambers; cuts chases and makes good; builds up random-rubble and CSEB masonry; with the *plastering* elective, applies internal/external plaster and VDF flooring |
| **Produces** | Load-bearing and infill masonry walls, plastered surfaces, chambers, plinth, brick-bat coba layers |
| **Engaged** | Overwhelmingly through a **thekedar / labour sub-contractor** on **piece-rate per unit of finished work**; on small private jobs, direct **daily wage** with a **mistri + beldar** gang (1 mistri : 1–2 beldars) |
| **GATE** | **NONE.** No licence, no mandatory certification. Masonry can lawfully be done by an uncertified person. NSQF/RPL certificates are commercial/scheme requirements (PMKVY, contract conditions), not legal ones |

### 1.2 Shuttering carpenter / formwork carpenter — *shuttering mistri, barhai (when wood), centring mistri*
| | |
|---|---|
| **NSQF job roles** | **Shuttering Carpenter — CON/Q3001 v4.0, NSQF 4** · **Shuttering Carpenter – Conventional — CON/Q0310 v1.0, NSQF 4** · **Shuttering Carpenter – System — CON/Q0304 v1.0, NSQF 4** · **Assistant Shuttering Carpenter — CON/Q0302 v3.0, NSQF 3** · **Helper Shuttering Carpenter — CON/Q0301 v3.0, NSQF 2** · Chargehands **CON/Q0311** (conventional) and **CON/Q0306** (system), NSQF 4 · **Foreman Formwork — CON/Q0308, NSQF 5** |
| **NCO-2015** | **7115.0201** (Shuttering Carpenter — also carried by CON/Q0302) · **9313.0401** (Helper Shuttering Carpenter) |
| **Does** | Reads the shuttering drawing; cuts and assembles ply/steel/aluminium panels, soldiers, walers, props, jacks and ties; sets formwork to line, level and camber; checks verticality of column boxes; oils the face; de-shutters at the specified stripping time and stacks panels |
| **Produces** | Column boxes, beam bottoms and sides, slab decking, wall and shear-wall forms, staircase forms, lift-core forms |
| **Engaged** | Almost always **piece-rate per sq m of contact area**, through a formwork sub-contractor who also supplies props/plates; system formwork (Doka/Peri/Mivan) crews are often on the vendor's rolls |
| **GATE** | **NONE** statutory for the carpenter. Note: formwork design and striking times are the **engineer's** responsibility (IS 14687), not the carpenter's licence |

### 1.3 Bar bender / steel fixer — *lohar (loosely), sariya mistri, loha bandhai mistri*
| | |
|---|---|
| **NSQF job roles** | **Bar Bender and Steel Fixer — CON/Q0203 v5.0, NSQF 4** (revised file ratified at the 43rd NSQC, 08-05-2025; NQR `QG-04-CO-03948-2025-V2-CSDCI`) · **Reinforcement Fitter — CON/Q0204 v4.0, NSQF 4** · **Assistant Bar Bender and Steel Fixer — CON/Q0202, NSQF 3** · **Helper Bar Bender and Steel Fixer — CON/Q0201, NSQF 1/2** · **Foreman Reinforcement — CON/Q0205, NSQF 5** |
| **NCO-2015** | **7214.1101** (Bar Bender and Steel Fixer) · **7214.9900** (Reinforcement Fitter) |
| **Does** | Works from the bar bending schedule; cuts and bends bars to shape (cranks, bends, stirrups, chairs); places and ties with binding wire; keeps cover with cover blocks; laps and staggers per the drawing; fixes couplers where specified |
| **Produces** | Reinforcement cages for footings, columns, beams, slabs, walls, piles, pile caps |
| **Engaged** | **Piece-rate per tonne (MT) or per quintal** of steel fixed, through a steel-fixing thekedar; the **BBS tonnage is the money document** |
| **GATE** | **NONE** statutory |

### 1.4 Concreter / concrete mason — *concrete mistri, vibrator wala*
| | |
|---|---|
| **NSQF job roles** | **Mason Concrete — CON/Q0105 v3.0, NSQF 4** (IRC:127-2018 listed it at L3; the current QP says 4) · **Mason Form Finished & Special Concrete — CON/Q0108 v1.0, NSQF 4** · **Foreman – Concrete — CON/Q0110, NSQF 5** |
| **NCO-2015** | **7114.9900** (concrete placers / finishers family) |
| **Does** | Places, spreads, compacts (needle/plate vibrator), screeds, levels and finishes PCC and RCC; makes construction joints; cures; takes cube samples with the lab technician; for form-finished concrete, controls the face finish |
| **Produces** | Footings, columns, beams, slabs, rafts, screeds, exposed-concrete faces |
| **Engaged** | Piece-rate **per cu m** placed, or day-rate as part of the RCC gang with the bar benders and shuttering carpenters (common on turnkey RCC sub-contracts) |
| **GATE** | **NONE** statutory |

### 1.5 Rigger — *khalasi* (the actual site word for the assistant rigger)
| | |
|---|---|
| **NSQF job roles** | **Khalasi (Assistant Rigger) — CON/Q0701 v3.0, NSQF 3** · **Rigger – Structural Erection — CON/Q0702 v3.0, NSQF 3.5** · **Rigger – Precast Erection — CON/Q0703 v3.0, NSQF 3.5** · **Rigger – Piling — CON/Q0704 v2.0, NSQF 4** · Chargehands **CON/Q0705** (structural), **CON/Q0706** (precast), **CON/Q0707** (piling), NSQF 4 · **Foreman – Erection CON/Q0708**, **Supervisor – Erection CON/Q0709**, **Supervisor – Piling CON/Q0710** |
| **NCO-2015** | **7215.0100** (Rigger — Khalasi and Rigger-Precast both carry it) · **7214.0700** (Rigger – Structural Erection) · **7215.9900** (Rigger – Piling) |
| **Does** | Selects slings, shackles, chains, eye-bolts and spreader beams to the load; calculates/looks up SWL; makes the hitch; fixes tag lines; **gives the standard hand/whistle signals to the crane operator**; guides the load in; inspects and rejects damaged tackle |
| **Produces** | Nothing of its own — it is the safe movement and seating of everything heavy |
| **Engaged** | Usually **direct on the erection sub-contractor's rolls** (day rate), because the risk and the signalling discipline make piece-rate unworkable |
| **GATE** | **BOCW Central Rules 1998** — operator/rigger/derrick operator must be **over 18 and "sufficiently competent and reliable"**; **no person under 18** may control a lifting appliance **or give signals** to its operator. **Rule number NOT VERIFIED** (see §0). No individual statutory licence; in practice client/EPC HSE regimes require a third-party rigger competency card (TPI). Not a legal licence |

### 1.6 Scaffolder
| | |
|---|---|
| **NSQF job roles** | **Scaffolder — CON/Q0315 v1.0, NSQF 4** (electives: System / Conventional) · **Scaffolder – System — CON/Q0305 v1.0, NSQF 4** · **Scaffolder Conventional — CON/Q0312 v1.0, NSQF 4** · **Associate Scaffolder – System — CON/Q0316 v1.0, NSQF 3** · **Assistant Scaffolder – System — CON/Q0314 v3.0, NSQF 3** · **Assistant Scaffolder – Conventional — CON/Q0313 v3.0, NSQF 3** · Chargehand Scaffolding – System **CON/Q0307**, Foreman – Scaffolding **CON/Q0309** |
| **NCO-2015** | **NOT FOUND** on the CON/Q0305 / Q0312 PDFs (the alignment field is absent in those versions) |
| **Does** | Erects, alters and dismantles tube-and-coupler, cuplock and system scaffolds; sets base plates and sole boards; plumbs standards, levels ledgers, fits transoms, braces, ties into the structure; lays and secures platform boards; fits toe boards, guard rails and ladder access; tags the scaffold |
| **Produces** | Access scaffolds, birdcages, facade scaffolds, mast climbers' base, formwork support towers, protection fans |
| **Engaged** | **Piece-rate per sq m of elevation or per cu m of scaffold volume**, or hire-and-fix rate from a scaffolding vendor who also supplies material; also day-rate crews for alterations |
| **GATE** | **NONE statutory in India** (contrast UK CISRS). CSDCI's own packs build the 3.6 m threshold into lower roles — e.g. the Assistant Mason pack CON/Q0102 carries the mandatory module **CON/N0101, erecting and dismantling temporary scaffold up to 3.6 m** — which is a *scheme* boundary, not a legal one |

### 1.7 Welder (construction) — *welder, gas-cutter*
| | |
|---|---|
| **NSQF job roles** | **Construction Welder (MIG/TIG/SMAW) — CON/Q1252 v3.0, NSQF 4** (IRC:127-2018 split these as CON/Q1252 MIG, Q1253 TIG, Q1254 SMAW; the current pack is one elective-based QP) · **Senior Construction Welder (MIG/TIG/SMAW) — CON/Q1253 v2.0, NSQF 5** (IRC listed Q1255/Q1256/Q1257 separately) · **Tack Welder — CON/Q1251 v1.0, NSQF 3** · **Gas Cutter – Construction — CON/Q1204 v2.0, NSQF 2** · **Plasma Cutter — CON/Q1207 v2.0, NSQF 4** · **Grinder – Construction — CON/Q1203, NSQF 2** |
| **NCO-2015** | **7212.0303** (Construction Welder) · NCO-2004/7212.20 on the old Tack Welder pack |
| **ITI route** | CTS **Welder**, NSQF 2.5 · CTS **Welder (GMAW & GTAW)**, NSQF 2.5 · CTS **Welder (Fabrication & Fitting)**, NSQF 2.5 · ATS **Structural Welder**, NSQF 3 · ATS **Welder (Gas & Electric)** / **Advance Welder**, NSQF 4 |
| **Does** | Sets current/voltage/gas; cleans and prepares the joint; tacks; runs root, fill and cap passes in the required position (1F–6G); controls distortion; chips, grinds and cleans; presents the weld for visual/DP/UT |
| **Produces** | Structural connections, embedded plates, handrails, ducting, pipe joints, rebar couplers where welding is permitted |
| **Engaged** | **Per joint / per running metre / per kg of deposit** on fabrication sub-contracts; **day rate** where the welder must be a *named qualified welder* on a WPS-controlled job |
| **GATE** | **THE REAL ONE IN PRACTICE, and it is contractual-plus-code, not a trade licence.** No Indian statute licenses welders. But a weld on a code-governed item may only be made by a welder **qualified to the applicable procedure**: <br>• **IS 7310 (Part 1)** — Approval tests for welders *working to approved welding procedures*, fusion welding of steel<br>• **IS 7318 (Part 1):1974** — Approval tests for welders *when welding procedure approval is not required*<br>• **IS 7307 (Part 1)** — Welding procedure approval tests (the WPS/PQR side)<br>• **IS 817 (Part 1):1992 / (Part 2):1996** — Code of practice for training and testing of metal-arc / oxyfuel welders<br>• By specification: **ASME Sec. IX** (WPQ/WQT) and **AWS D1.1** for structural steel<br>**Whether IS 800:2007 itself contains a clause mandating welder qualification: NOT VERIFIED** — I could not retrieve the clause text. Indian Railways' steel-girder practice does mandate it (fresh welders barred from welding until they pass the welder qualification test) but that is railway-specific.<br>**Practical rule: on any pressure, structural-code or client-QA job, an uncertified welder's weld is a rejected weld — and the certificate is per-process, per-position, per-thickness, and expires.** |

### 1.8 Structural steel erector / construction fitter
| | |
|---|---|
| **NSQF job roles** | **Construction Fitter — CON/Q1205 v3.0, NSQF 3.5** · **Associate Construction Fitter — CON/Q1254 v1.0, NSQF 3** · **Assistant Construction Fitter — CON/Q1202 v3.0, NSQF 3** · **Fabricator — CON/Q1206 v5.0, NSQF 4** · **Helper Fabrication — CON/Q1201 v3.0, NSQF 2** · **Multi Skill Technician – Fabrication — CON/Q1210 v1.0, NSQF 3** · **Foreman Fabrication CON/Q1208**, **Supervisor Fabrication CON/Q1209 v2.0, NSQF 6** · **Chargehand – Structural Erection CON/Q0705, NSQF 4** |
| **NCO-2015** | **7214.0800** (Construction Fitter / Assistant Construction Fitter — structural-metal preparers & erectors) · **7213.0200** (Fabricator) |
| **Does** | Marks and fits members; sets columns on base plates to line/level/plumb; aligns with wedges, drifts and turnbuckles; bolts up with HSFG bolts to the specified torque/DTI; checks diagonals; hands over to the welder; installs purlins, bracing, decking |
| **Produces** | Erected steel frames, pipe racks, platforms, staircases, sheeting support |
| **Engaged** | **Per tonne erected** (erection sub-contract), crews on the sub-contractor's rolls |
| **GATE** | **NONE** for the erector personally. The *welds* carry the gate (§1.7); **HSFG bolting** calibration is a QA, not licensing, matter |

### 1.9 Pre-cast erector
| | |
|---|---|
| **NSQF job roles** | **Rigger – Precast Erection — CON/Q0703 v3.0, NSQF 3.5** · **Chargehand – Precast Erection — CON/Q0706, NSQF 4** |
| **NCO-2015** | **7215.0100** |
| **Does** | Receives and inspects panels/hollow-core/beams; fixes lifting inserts; rigs with the correct spreader; lands on shims and levelling bolts; props; grouts the joint/sleeve; checks verticality before releasing the crane |
| **Produces** | Erected pre-cast frames, walls, slabs, staircases, boundary panels |
| **Engaged** | Per piece erected, or day rate on the precast vendor's erection crew |
| **GATE** | **NONE** statutory; BOCW lifting rules (§1.5) and client TPI rigging cards apply |

### 1.10 Pre-stressing technician
| | |
|---|---|
| **NSQF job roles** | **Technician – Prestress — CON/Q0802 v2.0, NSQF 4** · **Assistant Technician – Prestress — CON/Q0801 v3.0, NSQF 3** · **Senior Technician – Prestress — CON/Q0803, NSQF 6** |
| **NCO-2015** | **3112.9900** (Technician – Prestress) · **3123.9900** (Assistant) — note these are *technician* families, not craft families |
| **Does** | Lays ducts and anchorages; threads strand; stresses with the jack to the designed force/elongation; records the stressing log; locks off; cuts and grouts the duct |
| **Produces** | Post-tensioned slabs, beams, girders, PT ground slabs |
| **Engaged** | Almost always **the PT specialist's own employees** (VSL/Freyssinet-type), per sq m or per tonne of strand |
| **GATE** | **NONE statutory.** Stressing is done to the designer's/vendor's procedure under an engineer; practically a vendor-authorised operator only |

---

## 2. FINISHING TRADES

### 2.1 Plasterer — *plaster mistri, palster wala; "safedi" for the finishing coat*
- **NSQF**: no standalone plasterer QP. **Plastering is an ELECTIVE inside Brick Mason — CON/Q0113 v4.0, NSQF 4**. **Separate plasterer QP: NOT FOUND.**
- **NCO-2015**: **7112.0200** (via CON/Q0113). *(ISCO's plasterer family is 7123; the Indian pack maps plastering under the bricklayer code.)*
- **Does**: Hacks and wets the surface; fixes dots and screeds; applies 12/15/20 mm cement-sand plaster in one or two coats; rules to plane; makes grooves, drip moulds and corner beads; neeru/putty finish
- **Produces**: Internal and external plaster, ceiling plaster, bands, drip courses
- **Engaged**: **Piece-rate per sq m**, through a plastering thekedar; on big jobs the rate includes scaffolding
- **GATE**: **NONE**

### 2.2 Tiler — *tiles mistri, marble mistri (for stone), mosaic/kadappa wala*
- **NSQF**: **Mason Tiling — CON/Q0104 v5.0, NSQF 3.5** (IRC:127-2018 had it at L4) · **Mason Marble, Granite and Stone — CON/Q0106 v1.0, NSQF 4** · **Mason Stone — CON/Q0115 v1.0, NSQF 4** (electives Dry Cladding / Wet Cladding; options Terrazzo and Mosaic flooring) · **Mason – Special Finishing / Mason Special Finishes — CON/Q0107 v2.0, CON/Q0114 v1.0, NSQF 4** (option: decorative flooring) · **Foreman Wet Finishing and Flooring — CON/Q0109, NSQF 5**
- **NCO-2015**: **7121.0100 + 7122.0100** (Mason Tiling — roofers + floor layers/tile setters) · **7112.0100** (Mason Stone) · **7122.9900** (Mason Special Finishing) · NCO-2004/7132.10 on the old CON/Q0106
- **Does**: Sets levels and tile layout from the centre line; lays base/screed; fixes vitrified, ceramic, stone with mortar or adhesive; cuts and drills; maintains joint width and slope to drain; grouts and cleans; builds skirting, nosing, dados; dry-cladding with anchors/pins for stone facades
- **Produces**: Floors, dados, wall cladding, skirtings, counters, staircase treads/risers, terrazzo and mosaic floors
- **Engaged**: **Piece-rate per sq ft or per sq m laid** — the single most common piece-rate in Indian finishing work; stone cladding sometimes per sq ft including polishing
- **GATE**: **NONE**

### 2.3 Painter — *painter, putty wala, rangai mistri*
- **NSQF**: **Construction Painter & Decorator — CON/Q0503 v3.0, NSQF 4** (a v4.0 exists at NSQF 3.5 — the level has been revised downward; verify which version the assessment body is using) · **Assistant Construction Painter & Decorator — CON/Q0502 v3.0** (options: varnishing and polishing of wooden surfaces) · **Helper Construction Painter — CON/Q0501 v3.0, NSQF 2** · **Chargehand – Painting & Decorating CON/Q0504, NSQF 4** · **Foreman – Painting & Decorating CON/Q0505, NSQF 5** · **Assistant Paint Inspector CON/Q0407, NSQF 5**
- **NCO-2015**: **7132.0100** (Construction Painter & Decorator)
- **Does**: Scrapes, sands, fills cracks, applies primer, 2–3 coats putty with sanding between, primer, 2 coats emulsion/enamel/texture; masks and protects; for metal, surface prep to the specified standard (St2/St3/SA2½ on industrial work) plus DFT checks; wood polishing/varnishing/melamine
- **Produces**: Painted walls and ceilings, enamelled joinery and grills, textured facades, protective coatings on steel
- **Engaged**: **Piece-rate per sq ft or per sq m** (often "labour-only, material by owner"); industrial painting per sq m with DFT acceptance
- **GATE**: **NONE** for the painter. *Industrial/protective coatings* on client specs may require NACE/FROSIO-certified **inspectors** — a gate on the inspector, not the applicator

### 2.4 POP / false-ceiling / drywall installer — *POP wala, gypsum/partition mistri*
- **NSQF**: **False Ceiling & Dry Wall Installer — CON/Q1107 v3.0, NSQF 4** · **Assistant False Ceiling and Drywall Installer — CON/Q1103 v3.0, NSQF 3** · **Associate False Ceiling and Drywall Installer — CON/Q1112 v1.0, NSQF 3** · **Chargehand CON/Q1109, NSQF 4** · **Foreman CON/Q1111, NSQF 5** · **Helper Interior Finishes — CON/Q1101 v3.0, NSQF 2**
- **NCO-2015**: CON/Q1107 still carries the legacy **NCO-2004/7132.90**; CON/Q1103 carries **NCO-2015/7122.9900**; CON/Q1101 carries **NCO-2015/9313.9900**. **A clean NCO-2015 code for the drywall/false-ceiling installer: NOT FOUND**
- **Does**: Sets the ceiling level with a water/laser level; fixes perimeter channels, suspends GI intermediate/ceiling sections with soffit cleats and hangers at specified centres; screws gypsum board; tapes and joint-compounds; cuts service openings; for drywall partitions, fixes floor/ceiling channels, studs, insulation, double boarding; or runs traditional **POP punning** on brick/RCC
- **Produces**: Gypsum and grid ceilings, cove and drop boxes, drywall partitions, POP punned surfaces, service access panels
- **Engaged**: **Piece-rate per sq ft** (ceiling) and **per sq ft of partition face**, through an interiors sub-contractor
- **GATE**: **NONE**

### 2.5 Waterproofing applicator — *waterproofing wala; "brick-bat coba" gang*
- **NSQF**: **NO STANDALONE QP — NOT FOUND.** Waterproofing appears as a *unit* inside masonry: **CON/N0146 "Carry out brick bat coba waterproofing"**, in the General elective of **Brick Mason CON/Q0113 v4.0**
- **NCO-2015**: **NOT FOUND** (would sit in 7129/7112 family; not asserted)
- **Does**: Surface prep and crack filling; applies cementitious/crystalline slurry, APP/SBS torch-applied membrane, liquid-applied PU/acrylic, bituminous coats; brick-bat coba with slope; chemical injection grouting; forms coving at junctions; makes up-stands and terminations; **ponding/flood test**
- **Produces**: Waterproofed terraces, toilets, basements, water tanks, retaining walls, sunken slabs
- **Engaged**: Almost always a **specialist applicator/system vendor giving a written guarantee (5/10 years)** — **per sq ft including material**, because the guarantee is the product
- **GATE**: **NONE statutory.** The real gate is **manufacturer/system applicator approval** (needed for the warranty to be valid). Torch-applied membranes involve hot work → site hot-work permit, not a trade licence

### 2.6 Glazier / aluminium & facade fabricator — *aluminium fabricator, glass fitter, ACP wala*
- **NSQF**: **Façade Installer — CON/Q1106 v3.0, NSQF 3.5** · **Assistant Façade Installer — CON/Q1104 v3.0, NSQF 3** · **Helper Facade Installer — CON/Q1102 v3.0, NSQF 2** · **Doors & Windows Fixer — CON/Q1105 v3.0, NSQF 3.0** · **Chargehand – Façade Installer CON/Q1108, NSQF 4** · **Foreman – Facade Installation CON/Q1110, NSQF 5**
- **NCO-2015**: **7125.0100** (Façade Installer / Assistant Façade Installer — glaziers family) · **7115.0200** (Doors & Windows Fixer) · **9313.9900** (Helper Facade Installer)
- **Does**: Sets out from the façade grid; fixes brackets/embeds to the slab edge; installs mullions and transoms; glazes with structural or wet sealant, gaskets and setting blocks; fits ACP/stone/terracotta cladding on sub-frames; installs aluminium/uPVC windows, doors, louvres; seals the perimeter; **water-tightness (hose/field) test**
- **Produces**: Unitised and semi-unitised curtain walls, structural glazing, ACP cladding, windows, doors, skylights, spider glazing, railings
- **Engaged**: Façade **specialist sub-contractor**, measured **per sq m of façade area**; small aluminium work per sq ft including material
- **GATE**: **NONE statutory.** Structural silicone glazing requires the **sealant manufacturer's approved applicator** status and project-specific adhesion testing — a warranty gate, not a licence

### 2.7 Stone mason / cladder — see **Mason Stone CON/Q0115 v1.0 (NSQF 4, NCO-2015/7112.0100)** and **Mason Marble, Granite and Stone CON/Q0106 v1.0 (NSQF 4)**. Site names: *marble mistri, patthar mistri, sang-tarash* (carving). Measured **per sq ft**, dry cladding per sq m with anchors. **GATE: NONE**

### 2.8 Flooring specialist — covered by **Mason Tiling CON/Q0104**, **Mason – Special Finishing CON/Q0107/Q0114** (decorative flooring), **Mason Form Finished & Special Concrete CON/Q0108** (VDF/IPS), **Foreman Wet Finishing and Flooring CON/Q0109**. Includes IPS, VDF, epoxy, PU, trowel-finished and polished concrete, wooden/laminate flooring. Measured **per sq ft / per sq m**. **GATE: NONE**; epoxy/PU systems need applicator approval for warranty

### 2.9 Joiner / building carpenter — *barhai, furniture mistri*
- **NSQF**: **Doors & Windows Fixer — CON/Q1105 v3.0, NSQF 3.0 (NCO-2015/7115.0200)**. A general building/finish **carpenter-joiner QP under CSDCI: NOT FOUND** (CSDCI's carpentry packs are all *shuttering* carpentry). IRC:127-2018 Annexure 6 names "Building Carpenter" as a workman category with no QP attached
- **ITI route**: DGT CTS **Carpenter**, NSQF 4
- **Does**: Makes and hangs door/window frames and shutters; fits hardware; builds and installs modular/site-built cabinetry, wardrobes, panelling, counters, skirting; wooden flooring and decking
- **Produces**: Frames, shutters, joinery, fitted furniture, panelling
- **Engaged**: **Per piece (per door/shutter/frame)** or **per sq ft of furniture surface area** — the dominant interiors measure; carpentry gangs often direct day-wage for an interior fit-out
- **GATE**: **NONE**

---

## 3. MEP TRADES — *this is where the legal gates actually are*

### 3.1 Electrician / wireman — *bijli mistri, wireman, bijliwala*
| | |
|---|---|
| **NSQF job roles** | **Construction Electrician – LV — CON/Q0603 v5.0, NSQF 4** · **Assistant Electrician — CON/Q0602 v4.0, NSQF 3** · **Associate Electrician — CON/Q0607 v1.0, NSQF 3** · **Associate Electrician-Aide — CON/Q0606 v1.0, NSQF 2** · **Helper Electrician — CON/Q0601 v4.0, NSQF 2** · **Foreman – Electrician Works (Construction) CON/Q0604, NSQF 5** · **Supervisor – Electrical Works CON/Q0605, NSQF 6** |
| **NCO-2015** | **7411.0100** (building and related electricians — carried by BOTH CON/Q0602 and CON/Q0603) · **9313.0501** (Helper Electrician) |
| **ITI route** | CTS **Wireman**, NSQF 3 (v3.0 also NSQF 3) · ATS **Wireman**, NSQF 5 · CTS **Electrician** (Power sector; level not retrieved — **NOT VERIFIED**) |
| **Does** | Lays conduit (concealed/surface) and cable trays; pulls wire; terminates in boards; installs switchboards, DBs, MCBs/RCCBs, switches, sockets, fixtures, fans; earthing pits and earth continuity; megger/IR, earth resistance, polarity and continuity testing; energises circuits |
| **Produces** | The building's electrical installation: conduiting, wiring, DBs, panels, earthing, lighting and power points |
| **Engaged** | **Point rate** is the Indian norm — ₹ per *point* (light/fan/socket), plus per-metre for cable and per-piece for DBs/panels — through an electrical contractor; **and the contractor must be licensed (below)** |
| **GATE — THE HARDEST ONE IN BUILDING WORK. VERBATIM:** | **CEA (Measures relating to Safety and Electric Supply) Regulations, 2010, Regulation 29(1):** *"No electrical installation work, including additions, alterations, repairs and adjustments to existing installations, except such replacement of lamps, fans, fuses, switches, domestic appliances of voltage not exceeding 250V and fittings as in no way alters its capacity or character, shall be carried out upon the premises of or on behalf of any consumer, supplier, owner or occupier … **except by an electrical contractor licensed in this behalf by the State Government and under the direct supervision of a person holding a certificate of competency and by a person holding a permit issued or recognised by the State Government.**"* <br>**Regulation 29(2):** *"No electrical installation work which has been carried out in contravention of sub-regulation (1) shall either be energised or connected to the works of any supplier."* <br>**Regulation 3(3):** *"No person shall be designated under sub-regulation (1) unless,— (i) he possesses a certificate of competency or electrical work permit, issued by the Appropriate Government. (ii) his name is entered in the register referred to in sub-regulation (2)."* — and **Reg. 3(2)** requires the owner/occupier to **maintain a register of designated persons and the purpose for which they are engaged**; **Reg. 4(1)** requires that register to be produced to the Electrical Inspector on demand. |
| **What that means operationally** | Three separate pieces of paper, all state-issued (by the **State Electrical Licensing Board / Electrical Inspectorate**, under rules framed via Reg. 29, e.g. the **Maharashtra Electrical Licensing Board Rules, 2017**): (1) the **firm's electrical contractor LICENCE**, (2) a **supervisor's Certificate of Competency** giving direct supervision, (3) the working man's **wireman PERMIT**. **An uncertified person may not lawfully do building electrical installation work, and the work may not be energised or connected to the supply if they did.** The only carve-out is like-for-like replacement of lamps, fans, fuses, switches, fittings and domestic appliances ≤250 V that does not alter capacity or character. CSDCI builds the rule into its own packs: **CON/Q0603's entry requirement is "Preferably 10th Standard / Low Voltage license from any Govt. recognized Licensing Authority"**, and **CON/Q0605 Supervisor – Electrical Works requires "compulsorily having Low Voltage license"**. |

### 3.2 Plumber — *plumber, nalsaaz, nal mistri*
| | |
|---|---|
| **NSQF job roles (WMPSC / Plumbing SSC)** | **Plumber – General — PSC/Q0104 v5.0, NSQF 4** (option: installation of insulation on pipes) · **Assistant Plumber – General — PSC/Q0102 v5.0, NSQF 3** · **Plumber (General) Helper — PSC/Q0101 v1.0, NSQF 1** · **Plumber (General)-II — PSC/Q0110, NSQF 4** · **Plumber (Maintenance & Servicing) — PSC/Q0112, NSQF 3**; **…Assistant — PSC/Q0109, NSQF 2** · **Plumber (Operations) — PSC/Q0108, NSQF 3** · **Plumbing Mason — PSC/Q0106, NSQF 3** · **Plumber (Welder) — PSC/Q0105, NSQF 3**; **…Assistant — PSC/Q0103, NSQF 2** · **Plumber (Pumps & E/M Mechanic) — PSC/Q0111, NSQF 4** · **Plumbing Draftsman — PSC/Q0201, NSQF 5** |
| **NCO-2015** | **7126.0105** (Assistant Plumber – General). Older packs still carry NCO-2004 codes: 7136.10 / 7136.90 (plumber), 7122.20 (plumbing mason), 7212.10 (plumber-welder), 7233.40 (pumps mechanic), 3118.20 (plumbing draftsman) |
| **ITI route** | CTS **Plumber** v3.0, **NSQF 2.5** (an earlier CTS Plumber was NSQF 4) · CITS **Plumber**, NSQF 3.5 · ATS **Plumber**, NSQF 5 |
| **Does** | Sets out from the plumbing drawing; cuts, threads, solvent-welds or fusion-welds GI/CPVC/UPVC/PPR/PEX; lays soil, waste, vent, rain-water and water-supply lines with the correct slope and supports; chases walls and sleeves slabs; installs sanitary fixtures, CP fittings, traps, floor drains, water meters, valves; pressure-tests and flushes; installs pumps and overhead/underground tanks |
| **Produces** | The building's water-supply, drainage, soil/waste/vent and rain-water systems; sanitary fixtures; pump sets |
| **Engaged** | **Per point** (each fixture/tap = a point) or **per running metre of pipe laid**, plus per-piece for fixtures, through a plumbing contractor; small jobs on day rate |
| **GATE** | **No central statutory plumber licence.** BUT **municipal licensing is real and common**: many ULBs/water boards require a **licensed plumber** for any connection to the municipal water or sewer main, and only such a plumber's signature is accepted on the connection application. **Which cities/rules: NOT VERIFIED in this session** — must be checked per ULB (e.g. Delhi Jal Board, BWSSB, BMC licensed plumber schemes). **Treat the water/sewer connection, not the internal plumbing, as the gated act.** Internal plumbing itself: no licence |

### 3.3 Pipe fitter
- **NSQF**: **Pipeline Fitter — PSC/Q0107 v2.0, NSQF 3.5** (electives: Industrial Pipe Fitting / Municipal Pipe Fitting)
- **NCO-2015**: **NOT FOUND** on the v2.0 PDF
- **Does**: Spool fabrication and erection; fit-up, alignment, root gap; flange bolting; supports and hangers; hydro-test
- **Engaged**: Per inch-dia or per running metre, on MEP/industrial sub-contracts
- **GATE**: **NONE** for the fitter. **Welded** joints carry the welder-qualification gate (§1.7); gas piping is separately regulated (PNGRB/gas utility authorised agency — **NOT VERIFIED**)

### 3.4 HVAC technician / refrigeration mechanic / duct fabricator
- **NSQF**: **HVAC Technician — ELE/Q3112 v2.0, NSQF 4 (ESSCI)** — **this version is marked "Deactivated-NSQC Approved", deactivation date 31/07/2024**; the current revised qualification is on NQR as **`QG-04-EH-044992025-V2-ESSCI`, NCrF/NSQF Level 4**, with **HVAC Supervisor** as the progression path. Related: **Field Technician – Air Conditioner — ELE/Q3102 v4.0, NSQF 4 (NCO-2015/7421.0401)** · **Field Technician Refrigerator — ELE/Q3103 v1.0, NSQF 4 (NCO-2015/7421.0501)** · **Sr. Technician RACW — ELE/Q3105 v4.0, NSQF 5**
- **ITI route**: CTS **Refrigeration and Air Conditioning Technician** (level **NOT VERIFIED**); CTS **Sheet Metal Worker** (level **NOT VERIFIED**)
- **Duct fabricator**: **NO STANDALONE QP — NOT FOUND.** Nearest is **Construction Fabricator (CSDCI) v1.0, NSQF 4**, which carries an optional **Sheet Metal Fitting** module
- **Does**: Installs indoor/outdoor units, VRF/chiller piping, insulation, drain lines; brazes copper; evacuates and charges refrigerant; fabricates and installs GI/pre-insulated ducting, grilles, diffusers, dampers, VAV boxes; AHU installation; testing, adjusting and balancing (TAB)
- **Produces**: Air-conditioning and ventilation installations, duct networks, chiller/VRF piping, AHU/FCU rooms
- **Engaged**: **Per TR installed** (AC) or per sq m of duct surface area and per running metre of piping, through an HVAC sub-contractor; service technicians per call/per unit
- **GATE**: **No Indian trade licence.** But: (a) HVAC electrical connection falls under the **CEA Reg. 29 electrician gate** (§3.1); (b) **refrigerant handling** is regulated under the **Ozone Depleting Substances (Regulation and Control) Rules** / HCFC phase-out and India's **Montreal Protocol / Kigali** obligations — **specific mandatory servicing-technician certification requirement: NOT VERIFIED**; (c) ammonia and large chiller plants may attract Factories Act rules on competent persons — **NOT VERIFIED**

### 3.5 Fire sprinkler fitter / fire-fighting system installer
- **NSQF**: **NOT FOUND.** No dedicated fire-sprinkler-fitter QP located. Nearest routes: **Pipeline Fitter PSC/Q0107** and **Plumber – General PSC/Q0104**
- **BOCW recognition**: the work *is* a notified BOC worker category — **category 40, "Installation and repair of fire-fighting system"** (CAG Appendix 4.1)
- **Does**: Installs the wet/dry riser, hydrant and sprinkler mains, branch lines, sprinkler heads at the specified spacing and K-factor, pumps, valves, flow switches; hydro-tests to the specified pressure; commissions with the fire pump
- **Produces**: Hydrant/sprinkler systems, pump room, risers
- **Engaged**: Fire-protection specialist sub-contractor; per sprinkler head, per running metre of pipe, per pump set
- **GATE**: **The gate is on the BUILDING, not the trade.** The installation must be certified/approved by the **State Fire Service / Chief Fire Officer** for the fire NOC and occupancy certificate (under state Fire Prevention and Life Safety Acts, following **NBC 2016 Part 4**). An uncertified fitter is not illegal; an uncertified **system** cannot get the fire NOC. Specific state Act/rule citation: **NOT VERIFIED**

### 3.6 Lift installer / lift & escalator mechanic
- **NSQF / DGT**: **No SSC QP found.** The DGT route is the real one: **CTS "Lift and Escalator Mechanic", 2-year, NSQF 4** (v2.0, Power sector) · **CITS "Lift & Escalator Mechanic", NSQF 4.5** · **ATS "Lift Mechanic", NSQF 5**. Also an NQR-listed short course **"Jr. Lift Erector"** (West Bengal SCTVESD)
- **Does**: Erects the guide rails, car and counterweight frames, ropes, machine, controller, landing and car doors; aligns and plumbs the shaft; wires the safety circuit; sets the overspeed governor and buffers; load/safety-gear tests; commissions
- **Produces**: The installed, tested lift/escalator/moving walk
- **Engaged**: **The lift OEM's or its authorised dealer's own erection crew** — per lift, on the licensed firm's rolls. Rarely thekedar labour
- **GATE — REAL, and state-level** | Under the state **Lift Acts** (Bombay Lifts Act 1939 and successors; Delhi Lifts Rules; **Maharashtra Lifts, Escalators and Moving Walks Act, 2017**, brought into force **1 November 2026** by notification dated 22 October 2026): <br>• the owner must obtain **permission before erection**, and *"on grant of permission under sub-section (3), the owner shall get lift or escalator or moving walk erected or installed by **approved contractor holding a valid licence under this Act**"*<br>• the **erection, maintenance and testing LICENCE is issued by the Chief Electrical Inspector**; licence form and conditions are prescribed by rules under **section 37**<br>• completion must be intimated within **one month**, then a **working licence/permission** follows from the Electrical Inspector (Lifts) after inspection<br>**So: a lift may legally be installed only by a LICENSED LIFT CONTRACTOR, and may not be operated without the working licence.** Whether the individual mechanic needs a personal certificate: **NOT FOUND / NOT VERIFIED** — the licence attaches to the firm. Plus **CEA Reg. 29** covers the lift's electrical installation. BOCW category 43 ("Installation and repair of lift, escalator etc.") recognises the workers |

### 3.7 Solar PV installer — *Suryamitra*
- **NSQF**: **Solar PV Installer (Suryamitra) — SGJ/Q0101 v4.0, NSQF 4 (Skill Council for Green Jobs)**; current revised file approved at the **38th NSQC, 30 May 2024**, NQR code **`QG-04-ES-02628-2024-V2-SCGJ`** · **Solar PV Installer – Electrical — SGJ/Q0102 v4.0, NSQF 4** · PwD variant **PWD/SGJ/Q0101 v2.0**, which prints the occupation as **"Solar Panel Installation Technician", NCO-2015/7421.1401**
- **NOS**: SGJ/N0101 site survey · N0102 procurement · N0103 civil & mechanical installation · N0104 electrical installation · N0105 testing and commissioning
- **Does**: Site/shadow survey; fixes the mounting structure and ballast/anchors; lays and clamps modules; strings and DC cabling with the right polarity; inverter, ACDB/DCDB, earthing and SPD; meter and net-metering interface; IV/insulation testing; commissions
- **Produces**: Rooftop/ground-mount PV array, inverter room, net-metered connection
- **Engaged**: EPC/channel-partner crews, **per kW installed**; Suryamitra-trained technicians feed this
- **GATE** | The **grid-connection side is gated**: net-metering/grid interconnection must be done through the **DISCOM-empanelled vendor** and the installation must clear DISCOM inspection and the **Electrical Inspector** before synchronisation; the AC side falls squarely inside **CEA Reg. 29**. BOCW category 48 ("Installation of energy conservation structure including solar panels") recognises the workers. **Specific DISCOM empanelment rule citation: NOT VERIFIED** (state/DISCOM-specific) |

---

## 4. PLANT AND EQUIPMENT OPERATORS (Infrastructure Equipment Skill Council unless noted)

| Trade / site name | QP code & version | NSQF | NCO-2015 | What they do / produce |
|---|---|---|---|---|
| **Tower crane operator** (*crane operator*) | **IES/Q0122 v4.0** | 4 | **8343.0700** (Tower Crane Operator) | Hoists and slews all materials to the working floor; works blind to the rigger's signals/radio; respects the load chart and radius; luffs/trolleys; parks in free-slew at wind limit |
| **Junior tower crane operator / Signalman** | **IES/Q0123 v4.0** | 3 | 8343.0700 | Second operator and the ground/floor signaller |
| **Hydra crane operator** (*hydra wala*) | **IES/Q0108 v4.0** | 4 | **8343.0500** (Mobile Crane Operator) | Pick-and-carry lifting for frames, precast, pipes |
| **Tyre-mounted crane operator** | **IES/Q0109 v4.0** | 4 | 8343.0500 | Outrigger set-up, boom/jib lifts |
| **Crawler crane operator** | **IES/Q0110 v4.0** | 4 | 8343.0500 | Heavy lifts, piling rig base machine, erection |
| **Junior operator crane** | **IES/Q0111 v4.0** | 3 | 8343.0500 | Assistant crane operator |
| **Excavator operator** (*JCB wala* loosely, *poclain wala*) | **IES/Q0103 v4.0** | 4 | **8342.2001** | Excavation, trenching, slope cutting, breaking with rock breaker; loads tippers |
| **Junior excavator operator** | **IES/Q0104 v4.0** | 3 | 8342.2001 | — |
| **Backhoe loader operator** (*JCB wala* — the actual word) | **IES/Q0101 v4.0** | 4 | **8342.2101** | Trenching + loading + backfilling in one machine; the default Indian site machine |
| **Junior backhoe operator** | **IES/Q0102 v4.0** | 3 | 8342.2101 | — |
| **Wheel loader operator** | **IES/Q0105 v4.0** | 4 | 8342.2101 | Stockpile loading, aggregate feed |
| **Skid steer loader operator** | **IES/Q0126 v4.0** | 4 | 8342.2101 | Confined-space muck shifting |
| **Compactor / road roller operator** (*roller wala*) | **IES/Q0106 v4.0** | 4 | 8342.2101 | Compacts subgrade/GSB/WMM/bituminous layers to the specified passes and density |
| **Paver operator** (*paver wala*) | **IES/Q0120 v4.0** | 4 | **8342.1800** | Lays bituminous/concrete pavement to thickness, level and camber |
| **Junior paver operator / Screedman** | **IES/Q0121 v4.0** | 3 | 8342.1800 | Screed control, joint matching |
| **Hot mix plant operator** | **IES/Q0114 v4.0** | 4 | 8342.1800 | Produces bituminous mix to the job-mix formula |
| **Junior hot mix plant operator** | **IES/Q0115 v1.0** | 3 | NOT FOUND | — |
| **Batching plant operator** (*batching plant wala*) | **IES/Q0116 v4.0** | 4 | **8114.0200** (Batching Plant Operator) | Loads the mix design, controls aggregate/cement/water/admixture weighing and moisture correction, prints the batch slip, keeps the plant calibrated |
| **Junior batching plant operator** | **IES/Q0117 v1.0** | 3 | NOT FOUND | — |
| **Transit mixer operator** (*mixer wala, transit mixer driver*) | **IES/Q0118 v4.0** ("Transit and Self-Loading Mixer Operator") | 4 | **8114.0300** | Carries RMC within the permitted time, controls drum speed, does not add water, delivers at the slump |
| **Junior transit mixer operator** | **IES/Q0119 v1.0** | 3 | NOT FOUND | — |
| **Concrete pump / boom placer operator** (*pump wala, boom placer wala*) | **IES/Q0107 v4.0** | 4 | **8114.0300** (Concrete Pump Operator) | Sets up and primes the pump, places concrete through the boom/pipeline, controls blockages, cleans out |
| **Aerial work platform operator** (incl. telescopic handler) | **IES/Q0127 v4.0** | 4 | NOT FOUND | Man-lift/boom-lift/scissor-lift access for façade and MEP work |
| **Borewell drill machine operator** (*driller, boring wala*) | **IES/Q0124 v2.0** | 4 | **8342** (4-digit only on the pack) | Bores wells and holes; DTH/rotary drilling |
| **Junior borewell drill machine operator** | **IES/Q0125 v2.0** | 3 | 8342 | — |
| **Crusher operator** | **IES/Q0112** (junior **IES/Q0113**) | 4 / 3 | NOT FOUND | Produces graded aggregate |
| **Bulldozer operator** (*dozer wala*) | **MIN/Q0205** (Mining SSC) | 4 | NOT FOUND | Site clearing, mass earth cutting and pushing |
| **Grader operator** | **MIN/Q0430** | 4 | NOT FOUND | Fine grading to level and camber |
| **Dumper operator** | **ISC/Q0403** (Iron & Steel SSC) | 4 | NOT FOUND | Haulage of earth/aggregate |
| **Compressor operator** | **MIN/Q0415** | 4 | NOT FOUND | Air for jackhammers, drilling, cleaning |
| **Mechanic (Engine / Hydraulic / Electrical-Electronics-Instrumentation)** | **IES/Q1101, Q1103, Q1105** (juniors **Q1102, Q1104, Q1106**) | 4 / 3 | NOT FOUND | Keeps the plant running |
| **Supervisor (Plant & Machinery)** / **Supervisor Maintenance (Infrastructure Equipment)** | **IES/Q0201 / IES/Q1201** | **7** | NOT FOUND | Plant management |
| **Piling rig operator** | **NOT FOUND** — no IESC QP located | — | — | Nearest NSQF cover is on the **rigging/piling** side: **Rigger – Piling CON/Q0704 v2.0 (NSQF 4)**, **Chargehand – Piling CON/Q0707 (4)**, **Supervisor – Piling CON/Q0710 (6)**; and the base crawler machine via **IES/Q0110**. IRC:127-2018 Annexure 6 lists "Drilling Rig Operator" and "Bentonite Solution Circulation Operator" as workman categories with no QP |

**GATE for ALL plant operators:**
1. **If the machine is driven on a public road** (transit mixer, tipper, hydra, truck-mounted crane, roller moving between sites), the operator needs a **driving licence for a transport/heavy vehicle under the Motor Vehicles Act 1988**, and the machine needs registration, fitness and insurance. **This is the one hard legal gate on operators, and it is a driving licence, not a crane licence.**
2. **For lifting appliances on site: BOCW Central Rules 1998.** Rule 65 "Operation of lifting appliances"; **Rule 81 "Qualification of operator of lifting winches and of signaller"** (conditions include knowledge of the inherent risks of operating lifting appliances and **periodic medical examination per Schedule VII**); the operator/rigger/derrick operator must be **over 18 and "sufficiently competent and reliable"**; **no person under 18** may control a lifting appliance, scaffold winch, or give signals to the operator; the employer must ensure **every crane driver or lifting operator has adequate skill and training for that particular appliance**. *(Rule numbering for the last two: **NOT VERIFIED**.)*
3. **Third-party inspection of the appliance** (crane, hoist, chain pulley block, slings) at prescribed intervals is required under the BOCW Rules — **that certificate is on the MACHINE, and it is the one most often asked for on site**.
4. **There is NO Indian statutory personal crane-operator licence.** The "crane operator competency card" that EPCs and clients demand comes from **third-party certifiers or the IESC QP + assessment**, enforced by contract and HSE policy, not by law.

---

## 5. SUPPORT, EARTHWORK AND CIVIL-WORKS ROLES

| Role / site name | QP / NCO | What they do | Engagement |
|---|---|---|---|
| **Unskilled labourer / helper — *beldar, mazdoor, majdoor, coolie*** | **Helper Mason CON/Q0101 v4.0, NSQF 2, NCO-2015/9313.0301** (option: Manual Earthwork) · **Helper Shuttering Carpenter CON/Q0301 v3.0, NSQF 2, NCO-2015/9313.0401** · **Helper Electrician CON/Q0601 v4.0, NSQF 2, NCO-2015/9313.0501** · **Helper Construction Painter CON/Q0501 v3.0, NSQF 2** · **Helper Interior Finishes CON/Q1101 v3.0, NSQF 2, NCO-2015/9313.9900** · **Helper Facade Installer CON/Q1102 v3.0, NSQF 2, 9313.9900** · **Helper Fabrication CON/Q1201 v3.0, NSQF 2** · **Helper – Construction Laboratory and Field Technician CON/Q0401, NSQF 2** · **Pavement Layer (Helper) CON/Q1001 v3.0, NSQF 2** | Mixes mortar/concrete by hand or mixer, carries and stacks material, excavates and backfills by hand, cures, cleans, serves the mistri, dismantles. **This is 40–60% of any Indian site's headcount and the group whose work is hardest to measure** | **Daily wage through a thekedar**, usually paid weekly or fortnightly in cash or to the thekedar in lump; muster roll kept by the thekedar's munshi, not the main contractor. **Migrant, high churn, often no bank account in their own name at the site** |
| **Barbender helper** | **Helper / Assistant Bar Bender and Steel Fixer CON/Q0201 (L1/2), CON/Q0202 (L3)** | Carries, straightens, holds bars for cutting/bending, ties | Day rate in the steel-fixing gang; often absorbed into the per-tonne piece rate |
| **Site cleaner / housekeeping** | **NOT FOUND** — no QP. BOCW recognised indirectly | Debris removal, water removal, access clearing, toilet/canteen cleaning | Day rate, often a separate housekeeping contractor |
| **Watchman / security — *chowkidar*** | **NOT FOUND** as a construction QP; security QPs sit with the **Security Sector Skill Development Council**. **BOCW notified category 26: "Chowkidar (watchman)"** (CAG Appendix 4.1) | Gate control, material in/out, night watch | Monthly, direct or through a security agency (then **PSARA licensing applies to the AGENCY** — Private Security Agencies (Regulation) Act 2005) |
| **Store assistant / store keeper** | **Store Assistant – Construction CON/Q1501 v3.0, NSQF 3, NCO-2015/4321.0100** · **Junior Store Keeper – Construction CON/Q1502, NSQF 4.5–5** · **Store Keeper – Construction CON/Q1503, NSQF 6** | Receives against the challan/PO, records GRN, issues against indent, maintains bin cards and stock, raises reconciliation | Monthly staff, usually on the main contractor's rolls — **this role is a records role, and is the one most displaced by software** |
| **Surveyor's chainman / assistant surveyor** | **Assistant Surveyor CON/Q0901 v5.0, NSQF 2, NCO-2015/2165.9900** · **Surveyor CON/Q0902 v4.0, NSQF 5.5, NCO-2015/2165.0200** (entry: ITI/Diploma in Civil or Land Surveying) | Holds the staff/prism, clears the line, marks and protects pegs and benchmarks, assists in setting out grid lines, levels and layouts | Assistant on day rate; Surveyor on monthly staff |
| **Driller (rock) / *jackhammer wala*** | **NOT FOUND** (IESC covers borewell only: IES/Q0124). IRC:127-2018 Annexure 6 lists "Driller" and "Rock Excavator/Breaker" as workman categories | Drills blast holes to pattern, depth and inclination; jackhammer/wagon drill | Per running metre drilled, through a rock-excavation contractor |
| **Blaster / shot-firer** | **NSQF QP: NOT FOUND.** IRC:127-2018 Annexure 6 lists "Blaster" | Charges holes, connects the initiation train, fires, inspects for misfires | Specialist contractor, per cu m of rock |
| **GATE (blasting) — REAL AND CRIMINAL** | Explosives are governed by the **Explosives Act 1884** and the **Explosives Rules 2008** (PESO — Petroleum and Explosives Safety Organisation). **Possessing, transporting and using explosives requires a PESO licence, and firing requires a licensed/competent shot-firer under those Rules.** This is **the clearest case of "an uncertified person legally cannot do this"** in all of construction. **Exact rule numbers: NOT VERIFIED in this session** |
| **Well sinker / pneumatic well sinker / diver** | **NOT FOUND**. BOCW notified categories 9 ("Well diggers") and 14 ("Scum remover divers from wells"); IRC Annexure 6 lists "Well sinker" and "Pneumatic Well Sinker" | Sinks open wells/caissons, dewatering, mucking | Specialist gang, per metre of sinking |
| **Pavement layer** | **Pavement Layer CON/Q1002 v2.0, NSQF 4, NCO-2015/7112.0500 & 9312.0100** · **Pavement Layer (Helper) CON/Q1001 v3.0, NSQF 2** · **Foreman – Roads & Runways CON/Q1003, NSQF 5** · **Supervisor – Roads & Runways CON/Q1004, NSQF 6** | Lays and finishes flexible/rigid pavement, kerbs, paver blocks | Per sq m |
| **Bhishti / water carrier** | **NO QP, NO NCO code found — NOT FOUND.** The word survives on site for the person who waters curing concrete and masonry and keeps the water drums full. Historically a distinct occupation; now absorbed into *beldar* | Curing, dust suppression, water supply to the gang | Day rate |
| **Quality / lab** | **Construction Laboratory & Field Technician CON/Q0402, NSQF 4** · **Quality Technician CON/Q0403, NSQF 6** · **Construction UT / MPT / DPT Tester CON/Q0404 / Q0405 / Q0406, NSQF 3** · **Assistant Paint Inspector CON/Q0407, NSQF 5** | Cube sampling and testing, slump, field density, NDT of welds and concrete | Monthly staff or TPI agency |
| **EHS** | **EHS Steward CON/Q1401, NSQF 4** (entry requires a **compulsory Certification Course in Industrial Safety**) · **Supervisor – Site EHS CON/Q1402, NSQF 6** (same compulsory certification) | Permits, toolbox talks, PPE, incident reporting | Monthly staff |
| **Draughtsman** | **Draughtsman CON/Q1301, NSQF 4** (entry: ITI/Diploma Civil); DGT CTS **Draughtsman (Civil)** | Shop and layout drawings | Monthly staff |
| **Supervision / chargehand layer across every trade** | Chargehand = NSQF 4, Foreman = NSQF 5, Supervisor = NSQF 6 in every CSDCI family (e.g. **Supervisor Structure CON/Q0111, Supervisor Finishes CON/Q0112**, both L6; the current **Supervisor Structure (Technical)** file is at **NSQF 5.5**) | The chargehand is the person who **actually counts the work and the heads** — the pivot of any site record system | Chargehand often inside the thekedar's gang; Foreman/Supervisor on the contractor's rolls |

### The statutory occupation list that actually matters
BOCW registration in each state runs off a **state notification**, not a central schedule. Jharkhand's (Notification 1051 of 05-04-2011 and 1951 of 04-11-2015, reproduced in CAG Appendix 4.1) lists **54 categories**, which is the best available picture of how the law sees these trades:

1 stone cutting/breaking/grinding · 2 **Mason or those engaged in laying bricks** · 3 **Painter for construction works** · 4 **Carpenter** · 5 **Fitter or bar bender** · 6 **Plumbers engaged in pipe repair on roads** · 7 **Electrician** · 8 Mechanic · 9 **Well diggers** · 10 **Welder** · 11 Main labourer · 12 Sprayman or mixer man in road construction · 13 Wood/stone packers · 14 Scum remover divers from wells · 15 Hammer man · 16 Thatchers · 17 Technician · 18 Blacksmith · 19 Saw operator · 20 Call kar · 21 **Mixer (Machine) operator** · 22 **Pump operator** · 23 Concrete mixture maker · 24 **Roller operator** · 25 **Helper involved in operations of heavy machinery** · 26 **Chowkidar (watchman)** · 27 Mosaic polisher · 28 Tunnel worker · 29 **Marble worker** · 30 Road construction worker · 31 breaking rocks or mine · 32 mud works · 33 production of lime · 34 flood management · 35 planning related to construction of dams/bridges/roads/buildings · 36 non-Factories-Act brick work · 37 construction of pandals · 38 **Sewerage works** · 39 **Electric works (including wiring, distribution, and panel fixing etc.)** · 40 **Installation and repair of fire-fighting system** · 41 **Installation and repair of cooling and heating system** · 42 Installation and repair of safety equipment machine · 43 **Installation and repair of lift, escalator etc.** · 44 **Installation and repair of grills/doors/windows made of iron or any other metal** · 45 Installation and repair of water conservation structures · 46 **Internal works and carpeting, false ceiling, lighting, plaster of Paris workers etc.** · 47 **Installation, cutting and glazing of glass panels** · 48 **Installation of energy conservation structure including solar panels** · 49 Installation of modular units including kitchens · 50 **Construction and installation of pre-fabricated concrete modules** · 51 sports/entertainment facilities · 52 road signs, accessories, bus stops, stands · 53 rotary, fountains · 54 public parks, walking tracks, landscaping

*(CAG separately records Punjab notifying its own list, and Jharkhand's being "54 categories of works and other categories of workers" — so the count and wording differ by state.)*

---

## 6. HOW THEY ARE ENGAGED — the four models, and why it decides who records the work

| Model | Who it covers | Who holds the record | Consequence |
|---|---|---|---|
| **Direct, on the contractor's rolls (monthly)** | Supervisors, foremen, chargehands, surveyor, storekeeper, EHS, lab, lift OEM crews, licensed electrical supervisor, PT technicians | The contractor's HR/payroll. PF/ESI deducted. Attendance by biometric or register | Fully recordable in software today |
| **Through a labour contractor / *thekedar* / *petty contractor* / *mukadam*** | The overwhelming majority of mason, bar bender, shuttering carpenter, painter, tiler, helper labour | **The thekedar's own munshi**, in a hand-written *haaziri* (muster) notebook. The main contractor sees only the thekedar's monthly bill | **This is the central data problem.** The main contractor often does not know the individual worker's name. Worker identity, wage rate and actual days worked exist only in the thekedar's book. BOCW/CLRA registers are reconstructed after the fact |
| **Piece-rate (*thoka / theka* work)** | Masonry, plaster, tiling, painting, false ceiling, bar bending, shuttering, waterproofing, flooring | **Joint measurement sheet** signed by the contractor's engineer and the thekedar | The money is the *measurement*, not the attendance. Attendance is kept only for statutory compliance and for advances |
| **Daily wage, direct and informal (*nukkad* / labour chowk hiring)** | Beldar, cleaner, bhishti, casual helper on small and residential sites | Nobody, or a notebook | Least recordable; cash paid daily |

**Why this matters:** on a piece-rate gang the *attendance* record and the *payment* record measure two different things and are reconciled only through advances. Any software that assumes "attendance × rate = wage" will be wrong for most of the Indian building workforce.

---

## 7. WAGE / MEASUREMENT BASIS — how each trade's work becomes money, and who measures it

> Measurement conventions below follow **IS 1200 (Methods of measurement of building and civil engineering works, multi-part)** and the **CPWD Delhi Schedule of Rates (DSR)** unit conventions for public work. *I did not fetch IS 1200 or the DSR in this session — the unit conventions are stated as standard Indian practice and should be confirmed against the current DSR/IS 1200 part before being hard-coded.*

| Trade | Primary basis | Unit | Who measures | Where it is recorded |
|---|---|---|---|---|
| Mason / bricklayer | Piece-rate | **per cu m** of brickwork (half-brick walls **per sq m**) | Site engineer + thekedar, **joint measurement** | Measurement Book (MB) / joint measurement sheet |
| Plasterer | Piece-rate | **per sq m** (or per sq ft on private work), thickness-specific; openings deducted per IS 1200 | Site engineer + thekedar | MB |
| Concreter | Piece-rate or day | **per cu m** placed | Engineer, against the **batching-plant slip + pour card** | Pour card / concrete register |
| Shuttering carpenter | Piece-rate | **per sq m of contact area** | Engineer + formwork sub-contractor | Shuttering measurement sheet |
| Bar bender / steel fixer | Piece-rate | **per MT or per quintal** fixed | Engineer, against the **bar bending schedule** | BBS + steel reconciliation statement |
| Scaffolder | Piece-rate / hire | **per sq m of elevation**, or **per cu m of scaffold volume**, or hire-and-fix per month | Engineer + scaffolding vendor | Scaffold measurement + hire register |
| Rigger | **Day rate** | per shift | Supervisor | Muster roll |
| Welder (structural) | Piece-rate | **per joint**, **per running metre of weld**, or **per kg of deposited metal**; fabrication often **per MT** | QA/QC engineer, against the **weld map and NDT report** | Weld register / WPS-welder log |
| Structural steel erector | Piece-rate | **per MT erected** | Engineer | Erection measurement |
| Precast erector | Piece-rate | **per piece erected** | Engineer | Erection log |
| Tiler / stone cladder | Piece-rate | **per sq ft or per sq m laid**; skirting **per running metre**; nosing per rm | Engineer + thekedar | MB / interior measurement sheet |
| Painter | Piece-rate | **per sq ft or per sq m** of painted surface, coat-count specific; industrial **per sq m with DFT** | Engineer (DFT by inspector) | MB / coating inspection report |
| False ceiling / drywall | Piece-rate | **per sq ft** of ceiling; partition **per sq ft of face area** | Interiors engineer | Interior measurement sheet |
| Waterproofing | Piece-rate, material inclusive | **per sq ft / sq m**, system-specific; guarantee attached | Engineer, plus the **ponding/flood test** record | Measurement + guarantee certificate |
| Glazier / façade | Piece-rate | **per sq m of façade area**; windows **per sq m or per piece** | Façade engineer | Façade measurement |
| Joiner / carpenter (finish) | **Per piece / per sq ft** | per door, per shutter, per sq ft of furniture surface | Interiors engineer | Interior measurement |
| Electrician | **Point rate** | **per point** (light/fan/socket), plus per running metre of cable/conduit, per piece for DB/panel | MEP engineer | Point schedule / MEP measurement |
| Plumber | **Point rate + length** | **per point** (fixture), **per running metre of pipe** by diameter, per piece for fixtures | MEP engineer | Point schedule |
| Pipe fitter | Piece-rate | **per inch-dia** or per running metre | MEP/QA engineer | Fit-up and test packs |
| HVAC | Piece-rate | **per TR installed**; ducting **per sq m of sheet surface area** (the classic GI duct measure) or **per kg of sheet**; piping per rm | MEP engineer | HVAC measurement + TAB report |
| Fire sprinkler | Piece-rate | **per sprinkler head**, per rm of pipe, per piece of pump/valve | MEP engineer, then **Fire Officer inspection** | Hydro-test certificate, fire NOC |
| Lift installer | **Per lift** | per unit, lump sum | OEM + **Electrical Inspector (Lifts)** | Erection completion intimation, working licence |
| Solar PV | **Per kW installed** | per kWp | EPC + **DISCOM inspection** | Commissioning report, net-metering agreement |
| Plant operators | **Per machine-hour or per shift**, sometimes **per cu m moved / per MT crushed / per cu m pumped** | hour / shift / output | Plant in-charge via the **logbook / hour meter**; batching plant via the **batch slip** | Equipment logbook, hour-meter reading, batch slips, trip slips |
| Transit mixer | **Per trip / per cu m delivered** | trip or cu m | Gate + pour card | Delivery challan (time-stamped — the 90/120-minute limit lives here) |
| Helper / beldar | **Day rate** | per day, per shift | Thekedar's munshi, countersigned by the chargehand | Haaziri notebook → thekedar's bill |
| Watchman, cleaner, store | **Monthly** | month | HR / admin | Payroll |
| Surveyor's chainman | Day rate | per day | Surveyor | Muster roll |
| Driller | Piece-rate | **per running metre drilled** | Engineer | Drilling log |
| Blaster | Piece-rate | **per cu m of rock blasted** | Engineer | Explosives magazine register (statutory, PESO) |
| Roller / paver operator | Per shift or **per sq m of layer laid** | shift / sq m | Road engineer, against compaction test results | Layer measurement + density test |

**The single structural fact:** for most Indian building trades **the money document is a MEASUREMENT (joint measurement sheet / MB entry), not an attendance record.** Attendance exists for statutory compliance and advances. Any product that wants to pay these people has to get the measurement right, with two signatures on it.

---

## 8. WHAT A SOFTWARE PRODUCT CAN AND CANNOT DO FOR THESE ROLES

### 8.1 RECORDS AND MEASUREMENT — software can own this end to end

**Fully automatable (the record is the product):**
- **Worker master and identity** — name, trade, NCO/QP classification, skill level, Aadhaar-linked ID (held in a vault, masked in use), bank/UPI details, BOCW registration number, ESI/UAN, date of entry, thekedar he belongs to. **This register is legally required under BOCW/CLRA and today exists as loose paper.**
- **Attendance** — geo-fenced face/biometric punch, gang-wise bulk marking by the chargehand, shift and overtime, in/out at the gate. Must support **thekedar-wise sub-musters**, because that is the real unit.
- **Piece-rate measurement capture** — structured measurement entry per trade in that trade's own unit (cu m / sq m / sq ft / MT / rm / point / piece / per TR / per kW), with photo evidence, location (block/floor/grid/room), and a **two-signature joint-measurement workflow** (engineer + thekedar). This is the highest-value thing such a product can do, and the thing no attendance app does.
- **Automatic quantity reconciliation** — BBS tonnage vs steel fixed vs steel issued; batching-plant slips vs cu m placed vs cu m paid; shuttering panel area vs contact area billed; paint litres issued vs sq m painted. **Theft and over-billing in Indian construction live in exactly these gaps.**
- **Wage calculation** — day rate, piece rate, mixed, overtime, minimum-wage floor check per state and per skill category (unskilled/semi-skilled/skilled/highly-skilled, the categories state minimum-wage notifications actually use), deductions, advances already drawn against a piece-rate bill.
- **Payment** — wage slips, bank/UPI payout files, thekedar RA bills with deductions and retention. **Money must still move only on the owner's tap.**
- **Material issue and store** — GRN against challan/PO, indent-based issue, bin card, stock, reconciliation, returnable material (shuttering, scaffolding, props) with hire-period tracking.
- **Plant records** — hour-meter readings, logbooks, fuel issue vs hours, trip slips, hire bills, breakdown and service history.
- **Statutory registers** — BOCW and CLRA registers of workmen, wages, overtime, fines, advances, accidents; Form XIII/XVI-type outputs; the **register of designated persons required by CEA Reg. 3(2)** for electrical work — which is a legal document the Electrical Inspector can demand under Reg. 4(1), and which almost nobody keeps properly.
- **The GATE as data** — hold and expire each worker's certificate: wireman permit number and validity, electrical supervisor certificate of competency, welder WPQ (per process, per position, per thickness, with expiry and continuity-of-employment date), driving licence class and validity, lift contractor licence, PESO explosives licence, third-party crane/sling/chain-block inspection certificates with next-due dates, medical examination due dates under BOCW Schedule VII. **This is pure records work and it is the single most defensible thing software can do for a safety-critical trade: block the work order if the certificate on file has expired.**
- **Productivity and rate benchmarking** — actual output per man-day per trade against the DSR/estimate.

**Hard but doable:**
- Getting the **thekedar** to use it at all. He is the data owner, often semi-literate in English, and the current notebook serves his interests (opacity). Needs a Hindi/vernacular, voice-first, offline, 2-minute-a-day interface, and a reason for *him* to want it (faster RA bill, fewer disputes).
- Measurement **from photos** — assistive (count tiles, estimate wall area), never authoritative. Must remain a draft the engineer signs.
- Offline-first with reliable sync — basements, shafts, rural sites have no signal.

### 8.2 THE PHYSICAL WORK — software cannot do any of it

No software lays a brick, bends a bar, plumbs a column box, strikes an arc, hangs a lift car, pulls a wire, lays a tile, torches a membrane, or signals a crane. Specifically, and worth saying plainly:

- **Judgement in the hand.** Whether the mortar is right, whether the concrete has taken its initial set, whether the plaster is ready for the second coat, whether the weld pool is running — these are tactile and visual judgements made in seconds, thousands of times a day, by a person standing there.
- **Setting out and correction.** The mistri who finds the wall out by 15 mm and absorbs it over three courses is doing an act of improvisation software cannot specify in advance.
- **Safety-critical signalling.** The rigger's hand signal to a blind tower-crane operator is a human protocol with a human's life in it; BOCW's rules put a named competent person there on purpose.
- **The gated acts themselves.** Software cannot *be* the licensed electrical contractor, the certificate-of-competency holder supervising the installation, the permit-holding wireman, the qualified welder on a WPS, the licensed lift contractor, or the PESO-licensed shot-firer. The law places those acts on **named certified humans**. Software can only verify, schedule and record them.
- **Inspection and sign-off.** The Electrical Inspector's energisation approval, the Fire Officer's NOC, the Electrical Inspector (Lifts) working licence, the third-party crane certificate — these are acts of public authority. Software prepares the file; it does not grant the approval.
- **Negotiation.** The rate a thekedar accepts, the extra claimed for a difficult floor, the dispute over a deduction — settled by people.

### 8.3 The honest dividing line

> **Software can own the paper trail of construction completely, and it can own the gate: who is allowed to do what, with which certificate, valid until when, and what was measured, by whom, countersigned by whom, for how much money.**
> **It owns none of the work.** Its value is that in Indian construction the paper trail is *currently worse than the work* — the building stands up, and the records of who built it, how much they built, what they were owed, and whether they were legally allowed to build it, do not exist in usable form. That gap, not the trowel, is the product.

### 8.4 Three cautions for a product built on this list

1. **Do not model wages as attendance × rate.** Most of this workforce is paid on measurement. Build measurement first; attendance is the compliance layer, not the pay layer.
2. **Do not model the worker as your customer's employee.** He is usually the thekedar's. The data model needs a first-class *labour contractor* entity sitting between establishment and worker, or the statutory registers will not come out right.
3. **Treat the certificate as a hard gate, not a field.** For electrical work, welding on code items, lift erection and blasting, an uncertified person is not merely untrained — the work is unlawful or unacceptable, and in the electrical case **may not even be energised or connected to the supply (CEA Reg. 29(2))**. A system that lets a work order be issued to a person whose permit has expired has created a legal exposure, not a UX problem.

---

## 9. ITEMS EXPLICITLY NOT FOUND / NOT VERIFIED

| Item | Status |
|---|---|
| BOCW Act 1996 own Schedule, and verbatim s.2(1)(d)/(e) definitions | **NOT VERIFIED** — indiacode.nic.in 403; two mirrors failed. The governing occupation lists are **state notifications** (Jharkhand's 54 categories reproduced above from CAG) |
| BOCW Central Rules 1998 — exact rule numbers for the 18-year / "sufficiently competent and reliable" operator clause and the employer's crane-driver training duty | **NOT VERIFIED** — labour.gov.in and dgfasli.gov.in both failed; `future.indiankanoon.org` is blocked in this session's network settings and must be allowed. Rule 65 (operation of lifting appliances) and Rule 81 (qualification of operator of lifting winches and of signaller, Schedule VII medicals) are confirmed by name |
| Standalone NSQF QP for: **waterproofing applicator, fire-sprinkler fitter, duct/sheet-metal fabricator, blaster, piling-rig operator, rock driller, well sinker, site cleaner, bhishti** | **NOT FOUND** |
| General building/finish **carpenter-joiner** QP under CSDCI | **NOT FOUND** (only Doors & Windows Fixer CON/Q1105; DGT CTS Carpenter exists, NSQF 4) |
| NCO-2015 codes for: scaffolder (CON/Q0305/Q0312), surveyor QP CON/Q0902 PDF, pipeline fitter PSC/Q0107, several junior IESC operators, dozer/grader/dumper/compressor QPs, drywall installer (CON/Q1107 still carries legacy NCO-2004/7132.90) | **NOT FOUND** on the QP PDFs themselves |
| **IS 800:2007** clause mandating welder qualification | **NOT VERIFIED** — could not retrieve clause text. The qualification standards themselves (IS 817, IS 7307, IS 7310, IS 7318; ASME IX; AWS D1.1) are confirmed |
| Individual **lift mechanic** personal competency requirement under state Lift Acts | **NOT FOUND** — the licence attaches to the **contractor/firm**, issued by the Chief Electrical Inspector; rules under s.37 of the Maharashtra Act were not retrieved |
| Which Indian ULBs mandate a **licensed plumber** and under which bye-law | **NOT VERIFIED** — municipal, must be checked per city |
| Mandatory refrigerant-handling technician certification in India | **NOT VERIFIED** |
| DISCOM empanelment rule citation for solar net-metering installers | **NOT VERIFIED** — state/DISCOM specific |
| **PESO Explosives Rules 2008** exact rule numbers for the shot-firer competency | **NOT VERIFIED** (the Act/Rules and the licensing regime are correctly named) |
| Complete **DGT CTS trade list** with revised NSQF levels | **PARTIAL** — `dgt.gov.in` returned 503/TLS failures throughout this session. Confirmed individually: Mason (Building Constructor) NSQF 4 · Plumber CTS 3.0 NSQF 2.5 (older CTS Plumber NSQF 4; CITS 3.5; ATS 5) · Wireman CTS NSQF 3 (ATS 5) · Welder CTS 3.0 NSQF 2.5 · Welder (GMAW & GTAW) NSQF 2.5 · Welder (Fabrication & Fitting) NSQF 2.5 · ATS Structural Welder NSQF 3 · ATS Welder (Gas & Electric) / Advance Welder NSQF 4 · Lift & Escalator Mechanic CTS NSQF 4 (CITS 4.5, ATS Lift Mechanic 5) · Carpenter NSQF 4 (filename-inferred). **Electrician, Painter (General), Surveyor, Draughtsman (Civil), Sheet Metal Worker, RAC Technician levels: NOT VERIFIED.** DGT states CTS runs across **169 NSQF-compliant trades** |
| Current CSDCI level revisions vs IRC:127-2018 | Several roles were **re-levelled** after 2018 (e.g. Mason Tiling L4→3.5; Mason Concrete L3→4; Assistant Mason L2→3; Rigger-Structural L3→3.5; Construction Painter & Decorator L3→4, and a v4.0 at 3.5). **Always read the level off the current QP PDF, not off IRC:127** |

**Sources:**
- [IRC:127-2018 (CSDCI + IESC consolidated QP annexures)](https://law.resource.org/pub/in/bis/irc/irc.gov.in.127.2018.pdf)
- [CEA (Measures relating to Safety and Electric Supply) Regulations 2010 — consolidated](https://www.cbip.org/CEARegulations/July%202019/Consolidated%20Regulation%20CEA%20Safety.pdf)
- [CAG Performance Audit, Appendix 4.1 — 54 notified BOC worker categories](https://cag.gov.in/uploads/download_audit_report/2022/12-Appendices-067c19efa7a3b42.68436109.pdf)
- [National Qualification Register](https://www.nqr.gov.in/)
- CSDCI/IESC/WMPSC/ESSCI/SCGJ QP PDFs — pattern `https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/<SSC>_Q<code>_v<ver>.pdf`, e.g. [Bar Bender and Steel Fixer CON/Q0203 v5.0](https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/CON_Q0203_v5.0.pdf), [Construction Electrician – LV CON/Q0603 v5.0](https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/CON_Q0603_v5.0.pdf), [Excavator Operator IES/Q0103 v4.0](https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/IES_Q0103_v4.0.pdf), [Plumber – General PSC/Q0104 v5.0](https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/PSC_Q0104_v5.0.pdf), [Solar PV Installer SGJ/Q0101 v4.0](https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/SGJ_Q0101_v4.0.pdf), [HVAC Technician ELE/Q3112 v2.0 (deactivated 31/07/2024)](https://s3.ap-south-1.amazonaws.com/nsdcproddocuments/qpPdf/ELE_Q3112_v2.0.pdf)
- DGT/CSTARI curricula: [Mason (Building Constructor) CTS NSQF 4](https://www.cstaricalcutta.gov.in/images/CTS%20Mason%20(Building%20Constructor)_CTS_NSQF-4.pdf), [Plumber CTS 3.0 NSQF 2.5](https://www.dgt.gov.in/sites/default/files/2025-01/Plumber_CTS3.0_NSQF-2.5.pdf), [Wireman CTS 2.0 NSQF 3](https://www.dgt.gov.in/sites/default/files/2025-01/Wireman_CTS2.0_NSQF-3.pdf), [Lift & Escalator Mechanic CTS 2.0 NSQF 4](https://www.dgt.gov.in/sites/default/files/2024-12/Lift%20_%20Escalator%20Mechanic_CTS2.0_NSQF-4.pdf), [Welder CTS 3.0 NSQF 2.5](https://www.cstaricalcutta.gov.in/sites/default/files/2026-06/Welder_CTS3.0_NSQF-2.5.pdf)
- [Maharashtra Lifts, Escalators and Moving Walks Act 2017](https://prsindia.org/files/bills_acts/acts_states/maharashtra/2018/2018MH15.pdf) · [commencement 1 Nov 2026](https://www.scconline.com/blog/?p=399876)
- [BOCW Act 1996 (India Code)](https://indiacode.nic.in/bitstream/123456789/9608/1/building-and-other-construction-workers-act-1996.pdf) *(fetch failed this session)*

Working files (QP PDFs + extracted text, IRC:127 text, CEA text, CAG appendix text) are in `/tmp/claude-0/-home-user-santosh-app/a51840d3-ad9f-5ff8-8281-4d40cc5f3548/scratchpad/` under `qp/`, `ies/`, `mep/`, `law/`.