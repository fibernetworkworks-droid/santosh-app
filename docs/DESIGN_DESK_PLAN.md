# Hoola Design Desk — the Design & Consultancy AI employee (plan)

Owner's ask: *"Design & consultancy — architecture, structure, MEP, interiors, landscape/urban, and the
specialists (geotech, facade, acoustics, traffic, fire, vastu) ... LETS DEVELOPE THIS AI HOOLA EMPLOYEE ---
PLANING FIRST"*.

This is the plan only. Nothing is built until she says GO on a phase.

---

## 1. The check first: what Hoola ALREADY has here

v0.372 nearly duplicated a 1,789-line tool, and the only thing that caught it was looking before building. So
this plan starts with what exists, and the answer changes the shape of the whole desk.

| Already shipped | What it covers | Verdict |
|---|---|---|
| `architect_assistant` — *Architect's assistant* | project file, FSI check (andaaza), drawing register, approvals, RFI, fee invoice | **The architect's OFFICE is done.** Do not rebuild it. |
| `interior_designer` | brief, measurement, moodboard, BOQ-quote, vendor order, snag, handover | **Interiors are done.** Do not rebuild. |
| `site_supervisor` | daily work, attendance, materials, safety, cube test, snag, DPR | site execution, not design |
| `site_manager` — *Theka sahayak* | tender, measurement, RA bill, department payment, retention | contractor commercials, not design |
| `property_manager`, `society_manager` | letting, society running | after handover |
| `engineering/` — CAD Engineer | CadQuery solids, FEA, CAM, 2D views, drawing PDF, **a locked Python sandbox** | **mechanical/product CAD, not buildings** — but its sandbox is the thing to reuse |

**So the gap is not "architecture".** It is the **engineering and specialist disciplines that have no role at
all**, and the cross-discipline work a real consultancy sells:

1. **Structural** — nothing exists.
2. **MEP** — HVAC, electrical, plumbing/public health, fire protection: nothing exists.
3. **Specialists** — geotechnical, facade, acoustics, traffic, fire & life safety, vastu: nothing exists.
4. **Landscape / urban / planning** — nothing exists.
5. **Cross-discipline coordination** — the drawing/model coordination, code compliance and design-stage QA
   that is the actual product of a consultancy: nothing exists.

The Design Desk is therefore **the engineering half of design plus the coordinator**, sitting beside the
architect's assistant rather than on top of it. `architect_assistant` keeps the office and the approvals;
the Design Desk does the disciplines.

---

## 2. The gate — and why it is the spine of this desk, not a footnote

The enterprise suite's one real lesson: **find out who may legally sign what, before designing anything.**
Here that question has sharper teeth than it did for ERP, because a building that fails kills people and the
law names the person who carries that.

What this desk will therefore be, in one line: **it prepares; her licensed professional signs.** The same
shape as `regtech` (prepares every filing, files none).

| | |
|---|---|
| **Architects Act 1972** | s.37 protects the **title**, not the practice of architecture (*Council of Architecture v. Mukesh Goyal*, SC 2020) — my first draft of this plan overstated it. The **signing** limits come from the Model Building Bye-Laws, not the Act. Hoola will never call itself an architect, never sign, and never let a result imply either. |
| **Structural** | a structural design submitted to a municipal body must carry a licensed/registered structural engineer's name and stamp. Hoola computes and shows the working; a person stamps it. |
| **Municipal licensing** | cities license their own engineers/supervisors/architects in categories by building size. Hoola is none of them. |
| **Fire, environment, height, lifts** | each has its own authority and its own signatory. |
| **RERA** | withdrawals from the designated account need an engineer, an architect and a CA to certify separately. |

### Pinned so far (approvals/FM research landed 1 Nov 2026)
The rule across the whole industry, in one line from the research: **the application is the owner's act, the
technical certification is reserved to a named licensed professional on a specific register, and preparation
is unreserved.** Software's ceiling is the *prepare* column — which is 70-80% of the labour and almost none
of the liability. Verbatim conclusion worth keeping: *"An agent that drafts those certificates and lets the
licensee sign is useful and lawful; an agent that signs or files them is forgery."*

Registers that matter for THIS desk (each one a named signatory Hoola can never be):

| Deliverable | Who may certify it |
|---|---|
| Building plan sanction / IOD / CC | **COA-registered architect** (any size), or a **ULB-licensed engineer / building surveyor / supervisor within class limits** — and filing happens only from a registered professional's login |
| Structural design + **Structural Stability Certificate** | a **structural engineer registered with that specific Corporation** — an unregistered engineer's certificate is worthless |
| Soil report | a **geotechnical engineer** |
| Fire scheme, Form A / Form B | a **Licensed Agency** licensed by the Director of Fire Services; the CFO issues the NOC |
| Electrical installation | **licensed electrical contractor + supervisor** (state Licensing Board); Electrical Inspector energises |
| Plumbing completion | a **ULB-licensed plumber** |
| Completion certificate / OC | **registered architect** signs, plus structural engineer, licensed fire agency, plumber, electrical contractor; the ULB Commissioner issues the OC |
| RERA account withdrawal | **three separate people**: architect (Form 1), engineer (Form 2), practising CA with a valid ICAI COP (Form 3) — the bank may not release without all three |
| EIA | application must come through a **QCI/NABET-accredited consultant organisation**; legal position partly **unsettled** |
| Statutory energy audit | an **Accredited** energy auditor — a merely *Certified* one may not sign it |

### The design disciplines, pinned (design research landed 1 Nov 2026)

**The headline, and it is good news that also sharpens the rule: in India, DESIGN is largely ungated.
CERTIFICATES and EXECUTION are gated.**

| Discipline | Is the DESIGN gated? | What is gated |
|---|---|---|
| **HVAC** | **No gate at all** — no licence, no stamp. MBBL Appendix E does not list a mechanical/HVAC professional | ECBC compliance route; refrigerants under the ODS Rules |
| **Electrical** | **Design ungated** | energising needs the **Electrical Inspector's** written approval above 650 V (CEA Regs 2010, Reg. 43); the installation must be executed and certified by a **licensed contractor + supervisor**. *"Software may produce the design; it may not produce the completion/test certificate."* |
| **Plumbing / PHE** | **Design ungated** | execution by a **ULB-licensed plumber**, with competence limits (e.g. up to 500 sqm plot, 4 storeys); STP/ETP discharge needs SPCB consent |
| **Fire protection** | design ungated, but **this is the hardest gate in the country** | Maharashtra Fire Act 2006: only a **"Licensed Agency"** may issue **Form A / Form B**; the digital signature must match the one on its licence, no word may be added to or deleted from the Form, and licences are class-restricted. **Software must never generate this certificate.** |
| **Architecture** | **the title is protected, not the practice** — Architects Act s.37(1) bars anyone unregistered from using *"the title and style of architect"* (criminal under s.37(2)); *Council of Architecture v. Mukesh Goyal* (SC, 17 Mar 2020) reads it as title protection | **signing** comes from MBBL App. E: an architect may sign all plans *"except engineering services of multi-storeyed/special buildings"*, within area limits |
| **Structural** | design ungated in itself | the **Structural Stability Certificate** needs an engineer on **that Corporation's own register** |

### The category I had missed entirely: the "-on-Record" appointments
MBBL makes several **named statutory appointments** that are bigger gates than most design jobs, and the plan
had none of them:

- **Construction Engineer on Record (CER)** — **mandatory for every building except load-bearing up to 3
  storeys**, certifies construction safety (Form-13)
- **Geotechnical Engineer on Record (GER)** — a named appointment (MBBL 6.3.8), not just "a specialist"
- **Quality Auditor on Record (QAR/QAAR)** — **mandatory in seismic zones IV and V**
- **Town Planner on Record (TPR)** — named appointment
- **Structural Design Review Panel** — an **authority-constituted** panel, not a private peer review
- **Empanelled Architect** — a private architect who **literally is the approving authority** for residential
  buildings up to 15 m and 500 sqm, holding a security deposit, indemnity bond and liability insurance, and
  strikeable off the panel. A category the software must model explicitly rather than treat as "an architect".

### What this changes in the build
1. **The disciplines can go further than I assumed.** Structural, HVAC, electrical and plumbing *design* —
   calculations, sizing, schedules, specifications — carry no Indian licence. That is the desk's real room.
2. **The certificate is the hard line, not the design.** So the refusal is specific and small: Hoola never
   produces Form A/B, a stability certificate, a completion certificate, a test certificate, or RERA Form
   1/2/3. It produces the *calculation and the drawing those certificates rest on*.
3. **An "-on-Record" role is a person, and the desk must say whose record it is.** Any paper touching CER /
   GER / QAR / TPR work names the appointed professional and is marked as prepared for them.
4. **One job is flagged "near-fully automatable" by the research itself**: the **document controller /
   drawing register manager**. `architect_assistant` already holds the drawing register — so that is where
   it belongs, extended, not a new role. Every one above is stated in this plan as
a design constraint, and the plan's claims get replaced with quoted provisions and URLs before any code is
written. Nothing in this desk will assert a legal requirement Hoola has not read.

### What that means in code, not in a prompt
- Every deliverable is marked **DRAFT — for a qualified professional's review, not certified** (the CAD
  drawing PDF already does exactly this; reuse that title block language).
- No result ever says a design "is safe", "is compliant" or "is approved". It says what was checked, against
  which clause, with which numbers, and what was not checked.
- A submission is **prepared, never submitted**. The submit button is hers, outside Hoola.
- The calculation refuses rather than guesses — the `calc.py` discipline from v0.375: under-specified input,
  a load case not covered, a span outside the code's range → it names the gap instead of producing a number.

---

## 3. The one design decision that decides whether this desk is real

**Every number must be computed in code and shown, never produced by the model.**

v0.374/v0.375 established this for the enterprise sums, and here it matters more: a wrong beam depth looks
exactly as confident as a right one, and nobody checks a number that arrived in a sentence. So:

- The model's job is to **read her brief, pick the question, and explain the answer**.
- The arithmetic lives in `app/design/calc/` — plain Python, deterministic, unit-tested against worked
  examples from the codes themselves.
- Every result carries **the clause, the inputs, the formula, the intermediate values and the check** —
  shown, so a structural engineer can audit it in a minute. That is what makes a stamp possible.

**The sandbox we already have is the right home for the heavy ones.** `engineering/guard.py` +
`runner.py` + `sandbox.py` already run untrusted calculation scripts with no network, a cut-down builtins,
memory/CPU limits and a lockdown that survives a missing network namespace (v0.361). Building calculations
reuse that, unchanged. We do not build a second sandbox.

---

## 4. The disciplines, and what each one actually does

Eleven parts, one desk — the `erp` 16-part pattern (one role, many jobs, `job=` on the call), not eleven
tools, because it is one consultancy doing one project.

| # | Part | What it produces | Where the numbers come from |
|---|---|---|---|
| 1 | **brief** | design brief, area programme, stacking, site constraints | her words + statutory limits |
| 2 | **feasibility** | FSI/FAR envelope, setbacks, height, ground coverage, parking, saleable vs carpet | bye-laws (**`architect_assistant` already estimates FSI — extend it, do not duplicate**) |
| 3 | **structural** | load take-down, member sizing, foundation sizing, lateral system, quantity of steel/concrete | IS 456, IS 875 parts 1-3, IS 1893, IS 800 — computed |
| 4 | **geotech** | bearing capacity from a soil report, settlement, foundation type recommendation, pile capacity | IS 6403, IS 8009, IS 2911 — computed from HER soil report, never invented |
| 5 | **HVAC** | heat load, airflow, duct and pipe sizing, equipment schedule, ECBC envelope + system check | ISHRAE/ASHRAE method, ECBC 2017 — computed |
| 6 | **electrical** | load schedule, diversity, cable sizing, voltage drop, earthing, DG/UPS sizing, SLD | IS 732, IS 3043, CEA regs — computed |
| 7 | **plumbing / public health** | fixture units, water demand, tank sizing, pipe sizing, drainage slopes, STP/rainwater | NBC 2016 Part 9, IS 1172 — computed |
| 8 | **fire & life safety** | occupant load, exit widths, travel distance, staircase count, refuge, sprinkler/hydrant demand | NBC 2016 Part 4 — computed, and the clause quoted |
| 9 | **facade / envelope** | wind pressure, glazing selection, U-value/SHGC, thermal bridging, waterproofing details | IS 875 Part 3, ECBC — computed |
| 10 | **acoustics / specialists** | reverberation, partition STC/Rw, traffic noise, daylight factor, vastu reading | standards + an honest "this needs a specialist" where it does |
| 10b | **on-Record support** | the papers a CER / GER / QAR / TPR appointment rests on, each naming the appointed professional | MBBL 6.3.6 / 6.3.8 |
| 11 | **coordination** | cross-discipline clash and consistency check, drawing register, design-stage QA, consultant RFIs | rules over the drawings/models themselves |

Vastu is in because Indian clients ask for it. It is handled honestly: it is **stated as a client
preference and checked as geometry** (orientation, entrance direction, room placement), never dressed up as
engineering and never allowed to override a code requirement.

---

## 5. What it reads and writes

### Reads (official and open formats only)
- Her own drawings and models: **IFC** (buildingSMART, open), DWG/DXF, PDF
- Her reports: soil investigation, survey, existing-building records
- The codes themselves: IS codes, NBC 2016, ECBC — as **structured rule tables Hoola maintains**, each entry
  carrying its clause reference. Not scraped, not guessed: entered from the published standard with the
  citation, and a rule with no citation is not used.

### Writes
Papers and models, never a system of record:
calculation sheet · design basis report · member/equipment schedule · load schedule · specification ·
drawing register · RFI · design-stage QA checklist · compliance matrix (clause → how met → evidence) ·
quantity statement for the QS · an IFC/DXF export where it has genuinely modelled something

### Never
Signs anything · submits to any authority · says "approved" or "safe" · overrides a code because the model
thinks it is fine · produces a number without its working.

---

## 6. Build phases

Each ships as its own version, with tests, console and phone, the way every desk has.

| Phase | What ships | Why this order |
|---|---|---|
| **0** | The licence/gate research written into `rules.py` as quoted provisions (approvals/FM half **landed**, design half pending); the honest-draft title block; the refusal vocabulary | nothing is built on a legal claim we have not read |
| **1** | The desk exists: hire it, 11 parts, papers, project file; **brief + feasibility** working, reusing `architect_assistant`'s FSI rather than duplicating it | the smallest thing that is useful on its own |
| **2** | **`design/calc/` + the rule tables**, on the existing engineering sandbox: structural load take-down and member sizing, with every clause cited and worked-example tests | the heart; if the numbers are not auditable nothing else matters |
| **3** | **Fire & life safety + plumbing** — the two most codified, so the most checkable: occupant load, exits, travel distance, fixture units, tank and pipe sizing | highest certainty per unit of work, and fire is where a wrong answer is worst |
| **4** | **HVAC + electrical** — heat load, duct/pipe, load schedule, cable sizing, voltage drop | the two biggest MEP spends |
| **5** | **Geotech + facade** from her own soil and wind data | both strictly input-driven, so both refuse loudly without data |
| **6** | **Coordination**: read her IFC, cross-discipline consistency, compliance matrix, design-stage QA, RFIs | the thing a consultancy actually sells |
| **7** | **Acoustics, landscape/urban, vastu** + the honest "needs a specialist" boundary | the long tail |
| **8** | A **proof card** like the coding/tool cards: fixed design problems with known right answers, scored | the only way to claim it works |

---

## 7. How we will know it is real (not "tests pass")

The last three versions taught this the hard way — a module with green tests and no caller, a route that
existed but 500'd. So:

- **A proof card with known answers.** Worked examples out of the codes and standard textbooks, where the
  right answer is published. Score = did Hoola get the number, and did it cite the right clause.
- **A structural engineer must be able to audit one sheet in a minute.** If the working is not legible, it
  has failed regardless of the number.
- **Every refusal is tested.** Missing soil data, a span out of range, a load case not covered, a clause we
  do not hold — each must refuse by name, not produce something.
- **Reachability is tested by calling it**, not by asserting a route exists.

---

## 8. Decisions I need from her before Phase 1

1. **Who is the user?** A practising architect/engineer's office (she has the licence, Hoola does the
   volume), or a developer/owner who wants to check what a consultant gave them? This changes the whole tone
   and I would build the first.
2. **Which discipline first after feasibility** — structural (biggest fear, biggest liability) or MEP
   (biggest spend, most routine)? My recommendation: **structural**, because it forces the auditable-working
   discipline on us while the desk is small.
3. **Which codes do we buy and enter?** IS codes are copyrighted and sold by BIS. We can cite clause numbers
   and enter the rules we hold legitimately, but she will need licensed copies of the ones we encode. I need
   her word on which ones, and I will not encode a rule from a secondary source.
4. **Residential, commercial, or industrial first?** The occupancy drives nearly every code table.
5. **Does the desk draw, or only calculate and schedule?** Drawing production is a much bigger build; the
   calculations and schedules are where the value starts.

---

## 8b. A sourcing caveat to carry into the job list

**Partly solved.** Two researchers could **not** retrieve the NCO-2015 occupation-code tables — every official
mirror (labour.gov.in, dge.gov.in, ncs.gov.in) returned 404, a reset, or a redirect. NCO-2015 aligns to
ISCO-08 at the 4-digit family level, so families are reliable; **8-digit NCO titles are NOT VERIFIED and
will be marked as such** rather than printed as fact — EXCEPT for the trades, where a third
researcher found the codes a different way: every CSDCI/IESC **Qualification Pack PDF prints its own
NCO-2015 alignment code**, so trade codes are sourced from the QP itself and are reliable. The lesson is
worth keeping: when the official index is unreachable, the code may still be printed on a document that
cites it. Also: building permission, fire, lifts, trees,
structural audit and society law are **state subjects** — nothing is uniform nationally, and the job list
will use Maharashtra/MahaRERA + MoHUA's Model Building Bye-Laws 2016 as the worked example and say so.

## 9. What this plan will NOT promise

It will not say Hoola designs a building. It prepares the engineering work of a design: the calculations
with their clauses, the schedules, the specifications, the coordination checks and the compliance matrix —
auditable, refusing where it has no basis, and unsigned. The signature, the submission and the
responsibility stay with her licensed professional, because that is both the law and the right place for
them.
