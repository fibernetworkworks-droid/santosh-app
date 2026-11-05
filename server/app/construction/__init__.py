"""v0.512.0 CONSTRUCTION & REAL ESTATE - Wave 1 (records and money, tier A); Wave 2 v0.531.0 (file-
builders and checkers, tier B); Wave 3 v0.550.0 (model-level and certificate-adjacent, C11-C15).

The construction employee department built on `docs/CONSTRUCTION_EMPLOYEE_PLAN.md` and the register
`docs/research/building_industry/07_ai_employees_register.md` (123 candidate AI Employees, 15 fields).

Wave 1 register #s shipped here / by extensions: 61 (store), 62 (theka subs rate basis + advances),
64 + 70 (sitesup voice log + variance), 67 (meetings), 71 (theka wage calc), 75 + 76 + 78 (quality),
85 + 87 + 90 (labour desk), 88 (theka RA bill, already lived - trail noted), 91 (books),
92 + 98 (customer money + handover).

Wave 2: 9 + 16 (drawqa), 28-32 + 34 + 36 (approvals), 35 + 93 (rera), 37-39 + 41 + 49 + 73 (qs),
44-46 + 51 (contracts), 52-56 + 58 (tender), 72 + 81 (quality EHS extensions).

Wave 3 (v0.550.0, plan §7 C11-C15): 18-21 (bim: IFC read / BCF write / IDS subset / CDE / clash /
4D-5D), 10-12 (predesign: load take-down, preliminary sizing, MEP, fire rows), 22-24 + 26 (survey:
traverse, shoelace, grid volumes, CSV deviations, RERA carpet), 47 (delay working papers), 82
(quality incident investigation), 104 + 110-118 (green: meters/ECBC/daylight/carbon/water/credits/
Cx/T&C/M&V). The open-format law: the card says what was read (IFC yes, PDF never a model, E57/LAS
and CPM never computed); `india.json` joins the state packs for the national code rows.

Wave 3.5 (v0.565.0): the FIVE Wave-3 stragglers homed per the plan §5's original mapping - 25
(const_bim: the as-built SET register, completeness on HER list, marks by name), 27 (const_survey:
GeoJSON rings read as text, areas ONLY in projected metres - degree layers refused, overlay values
recorded as HER readings), 74 (const_predesign: formwork contact area by geometry, striking time vs
IS 456 cl 11.3 Table 10 pack rows - OPC + ambient > 15 degC scope, else refused, props vs the
supplier table's allowable, scaffold tag register by name), 77 (const_survey: setting-out sheets,
as-laid vs design plan deviations, level checks with the sign kept), 109 (const_bim: the twin as a
DATA-LINK register asset -> GUID, sensor feed rows with sourced bands flagged, COBie Component CSV
check). Three new tier-C rows: approve the as-built set / order formwork striking / tag a scaffold
safe. No new tools - the three desks grew actions.

THE LAW (construction/gates.py, repeated in every tool docstring and the prompt block): Hoola PREPARES
the record and the working paper; the named human decides. Tier A rows Hoola owns end to end with the
owner's tap on every outward step; tier C outputs (sign, certify, file, approve, accept work, release
payment, decide entitlement) are refused with the name of the human who must do it.

INERTNESS: importing this package touches nothing - no threads, no files, no network. Tables come up
only through db.init_db's import of construction.models; services act only when called."""
