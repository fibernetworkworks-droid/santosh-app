"""v0.512.0 CONSTRUCTION & REAL ESTATE - Wave 1 (records and money, tier A).

The construction employee department built on `docs/CONSTRUCTION_EMPLOYEE_PLAN.md` and the register
`docs/research/building_industry/07_ai_employees_register.md` (123 candidate AI Employees, 15 fields).

Wave 1 register #s shipped here / by extensions: 61 (store), 62 (theka subs rate basis + advances),
64 + 70 (sitesup voice log + variance), 67 (meetings), 71 (theka wage calc), 75 + 76 + 78 (quality),
85 + 87 + 90 (labour desk), 88 (theka RA bill, already lived - trail noted), 91 (books),
92 + 98 (customer money + handover).

THE LAW (construction/gates.py, repeated in every tool docstring and the prompt block): Hoola PREPARES
the record and the working paper; the named human decides. Tier A rows Hoola owns end to end with the
owner's tap on every outward step; tier C outputs (sign, certify, file, approve, accept work, release
payment, decide entitlement) are refused with the name of the human who must do it.

INERTNESS: importing this package touches nothing - no threads, no files, no network. Tables come up
only through db.init_db's import of construction.models; services act only when called."""
