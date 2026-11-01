# The building industry, job by job — the research register

Owner's ask (1 Nov 2026): *"NOW DO DEEP RESARCH ON DESIGN, CONSRTUCTION, BUILDING INDUSTRY ----- FIRST
EXTRACT ALL JOBS FROM IT"*.

**276 distinct jobs**, extracted by six parallel researchers from primary sources, India-primary with
international practice noted. The six full reports sit beside this file and are the actual deliverable — this
index exists so a future session can find the right one in one read instead of loading 576 KB.

| # | File | Jobs | Covers |
|---|---|---|---|
| 1 | `01_design_and_consultancy.md` | 50 | architecture, structural, MEP, interiors, landscape/urban, specialists |
| 2 | `02_construction_mgmt_and_site.md` | 73 | PM/PMC, planning & controls, site execution, quality, EHS, survey, labour & plant, specialist site mgmt |
| 3 | `03_trades_and_skilled_labour.md` | 30 | mason to crane operator, with the Hindi site names and the measurement basis of each |
| 4 | `04_cost_contract_qs_procurement.md` | 37 | QS, estimation, billing, contracts, claims, delay analysis, tendering, procurement |
| 5 | `05_approvals_developer_fm.md` | 42 | liaison & permits, the developer/client side, handover, facilities and operations |
| 6 | `06_digital_survey_sustainability.md` | 44 | BIM/ISO 19650, survey & reality capture, green/energy, commissioning, visualisation |

---

## The three findings that matter more than the list

### 1. PREPARE / SUBMIT / CERTIFY — the shape of every job in this industry
From report 5, and it held true across all six:

> the **application** is the owner's act, the **technical certification** is reserved to a named licensed
> professional on a **specific register**, and **preparation** is unreserved.

Software's ceiling is the *prepare* column — **70-80% of the labour and almost none of the liability**. The
register's own conclusion, worth keeping verbatim:

> *"An agent that drafts those certificates and lets the licensee sign is useful and lawful; an agent that
> signs or files them is forgery."*

### 2. DESIGN is largely ungated in India. CERTIFICATES and EXECUTION are gated.
From report 1. This is the opposite of what you would assume, and it is where the product room is:

- **HVAC design: no licence, no stamp at all.** The Model Building Bye-Laws' Appendix E does not even list a
  mechanical professional.
- **Electrical and plumbing design: ungated.** Energising needs the Electrical Inspector above 650 V
  (CEA Regs 2010, Reg. 43) and the *installation* certificate needs a licensed contractor/supervisor;
  plumbing *execution* needs a ULB-licensed plumber within competence limits.
- **Fire: the hardest gate in the country.** Only a **Licensed Agency** may issue Form A/B; its digital
  signature must match the one on its licence and not a word of the Form may change.
- **Architecture:** Architects Act s.37 protects the **title**, not the practice (*Council of Architecture v.
  Mukesh Goyal*, SC, 17 Mar 2020). The signing limits come from the Bye-Laws, where an architect may sign all
  plans *"except engineering services of multi-storeyed/special buildings"*, within area limits.
- **Structural:** the Stability Certificate needs an engineer on **that Corporation's own register** — an
  unregistered engineer's certificate is worthless.

Plus a statutory category easy to miss entirely — the **"-on-Record" appointments**: Construction Engineer on
Record (mandatory for every building except load-bearing up to 3 storeys), Geotechnical Engineer on Record,
Town Planner on Record, Quality Auditor on Record (mandatory in **seismic zones IV and V**), the
authority-constituted Structural Design Review Panel, and the **Empanelled Architect who literally is the
approving authority** for residential up to 15 m / 500 sqm.

### 3. What is actually machine-readable
From report 6, and it decides any coordination feature:

> *"Without an IDS, 'we exchanged IFC' guarantees nothing checkable."*
> *"Every Indian regulatory submission is a DWG or a PDF."*

IFC is an open **container** whose semantics are project-specific; buildingSMART's **IDS** is the
machine-checkable requirement, **BCF** the open coordination issue, and a point cloud **carries no semantics
at all** — it does not know it is a wall. Open and checkable: IFC (ISO 16739-1), IDS, bSDD, BCF, COBie,
gbXML/IDF, LandXML, E57 (ASTM E2807)/LAS, GeoJSON (RFC 7946), GeoPackage. Closed: `.rvt`, `.pln`, `.dgn`,
`.db1`, `.dwg`, `.nwd`, `.smc`.

---

## A method note: the NCO-2015 codes came out three different ways

Worth recording, because it is the difference between a code you can trust and one you cannot:

| How | Result |
|---|---|
| **Official index** (dge.gov.in, labour.gov.in, ncs.gov.in) | **unreachable** in every attempt — 404, TLS reset, 503, or a redirect to a homepage. Reports 4 and 5 therefore say NOT FOUND rather than guess. |
| **Printed on the Qualification Pack itself** | **reliable.** Every CSDCI / IESC / PSC / ESSCI / SCGJ QP PDF prints its own "Aligned to NCO/ISCO/ISIC Code" field. Reports 3 and 6 extracted ~60 QP PDFs and quote those codes as verified. |
| **A third-party transcription** | **do not trust at 8 digits.** Report 2 used a public CSV transcription of the NCO tables whose own author warns it was built by manual entry plus LLM parsing and may contain errors. |

NCO-2015 is aligned to ISCO-08 at the 4-digit level (the 8-digit form is `<ISCO 4-digit>.<Indian 4-digit>`),
so **4-digit stems are safe everywhere; 8-digit codes are safe only where a QP printed them.** Every report
marks its own codes accordingly.

**And one caveat that applies to the whole register:** building permission, fire, lifts, tree-cutting,
structural audit and society law are **state subjects**. Nothing here is uniform nationally. The reports use
Maharashtra / MahaRERA and MoHUA's Model Building Bye-Laws 2016 as the worked example because they are the
best documented, and flag where states diverge.

---

## What this feeds

- `docs/DESIGN_DESK_PLAN.md` — the first employee planned off this register (the design & consultancy half of
  report 1, plus the engineering disciplines that had no Hoola role at all).
- Every later desk in this industry: site/PM, QS/billing, approvals, FM. Reports 2, 4, 5 and 6 are their
  input, already sourced.
- A standing reminder of what Hoola already covers here, so nothing gets rebuilt: `architect_assistant`
  (the architect's office, drawing register, approvals, FSI estimate), `interior_designer`, `site_supervisor`,
  `site_manager` (Theka sahayak), `property_manager`, `society_manager`.
