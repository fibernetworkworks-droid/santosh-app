"""The 123 AI Employees of the building & construction industry, as DATA (v0.512.0).

Source: the owner's register of 4 Nov 2026, transcribed at
`docs/research/building_industry/07_ai_employees_register.md` (from the six sourced reports in the same
folder - 276 jobs merged into 123 employees). Every row: (register id, name, field, tier, the human who
decides, wave). Tier: A = admin / prepare (Hoola owns the record, the tap decides outward steps),
B = assist a named licensee (working paper addressed to the professional), C = reserved (never built).

The wave column is the build order: 1 = records and money (Wave 1, v0.512.0), 2 = file-builders and
checkers, 3 = model-level and certificate-adjacent (open formats + a licensee on every output),
"" = not waved yet (waits for her word or a paying customer).

Roles marked * in the register existed in some form before this department; + = planned in
docs/DESIGN_DESK_PLAN.md (fields 8-17 stay there - the anti-duplication boundary in the plan §4)."""
from __future__ import annotations

# (id, name, field, tier, human, wave)
ROWS: list[tuple[int, str, int, str, str, str]] = [
    # 1. Land, feasibility & development (R5 B1-B4, A5-A6)
    (1, "Land Scout & Feasibility Analyst", 1, "A", "developer", ""),
    (2, "Title Due-Diligence Assistant", 1, "B", "title advocate", ""),
    (3, "Land Records Fetcher & Reconciler", 1, "A", "revenue consultant", ""),
    (4, "Development Manager (DM) Assistant", 1, "A", "DM / developer", ""),
    (5, "Project Finance Desk", 1, "A", "CFO", ""),
    (6, "JV / Land-owner Agreement Tracker", 1, "A", "legal head", ""),
    # 2. Architecture, design & consultancy (R1) - fields 8-17 stay in DESIGN_DESK_PLAN
    (7, "Architect's Office Assistant *", 2, "A", "principal architect", ""),
    (8, "Concept & Space-Programme Assistant +", 2, "B", "architect", ""),
    (9, "Building-bye-law Checker +", 2, "B", "licensed architect", "2"),
    (10, "Structural Pre-design Assistant +", 2, "B", "structural engineer", "3"),
    (11, "MEP Design Assistant +", 2, "B", "MEP consultant", "3"),
    (12, "Fire-safety Design Checker +", 2, "B", "fire consultant", "3"),
    (13, "Interior Designer Assistant *", 2, "A", "interior designer", ""),
    (14, "Landscape & Urban-design Assistant +", 2, "B", "landscape architect", ""),
    (15, "Acoustics / Facade / Lighting Specialist Assistants +", 2, "B", "specialist", ""),
    (16, "Drawing QA Reviewer +", 2, "B", "project architect", "2"),
    (17, "Design Coordination Manager +", 2, "A", "design manager", ""),
    # 3. Digital delivery: BIM, survey, reality capture (R6 A-B)
    (18, "BIM Manager / Information Manager Assistant +", 3, "A/B", "BIM manager", "3"),
    (19, "CDE & Document Controller +", 3, "A", "document controller", "3"),
    (20, "Clash Detection Coordinator +", 3, "B", "BIM coordinator", "3"),
    (21, "4D/5D Planner +", 3, "B", "planner / QS", "3"),
    (22, "Land Survey Data Processor", 3, "B", "licensed surveyor signs", "3"),
    (23, "Drone Survey & Photogrammetry Processor", 3, "B", "survey lead", "3"),
    (24, "Laser Scan / Point-cloud Reality Capture Assistant", 3, "B", "scan technician", "3"),
    (25, "As-built Documentation Assistant", 3, "A", "site architect / QS", ""),
    (26, "RERA Carpet-area Measurement Assistant", 3, "B", "project architect / CE", "3"),
    (27, "GIS Analyst", 3, "A", "planner", ""),
    # 4. Approvals, permits & statutory compliance (R5 A1-A14)
    (28, "Approvals Tracker (Liaison Officer Assistant)", 4, "A", "liaison manager", "2"),
    (29, "Building-permission File Assembler", 4, "A/B", "licensed professional", "2"),
    (30, "Fire NOC Packet Preparer", 4, "B", "fire consultant", "2"),
    (31, "Environmental Clearance & Consent Tracker", 4, "A/B", "EC consultant", "2"),
    (32, "Utility Liaison Assistant", 4, "A", "liaison", "2"),
    (33, "Heritage / AAI / CRZ Clearance Screener", 4, "B", "specialist", ""),
    (34, "Statutory Calendar", 4, "A", "compliance officer", "2"),
    (35, "RERA Compliance Manager", 4, "A/B", "promoter + CA", "2"),
    (36, "Occupancy / Completion Certificate Packet Builder", 4, "A/B", "licensed architect", "2"),
    # 5. Estimating, quantity surveying & cost (R4 A-B)
    (37, "Quantity Take-off Assistant", 5, "B", "QS", "2"),
    (38, "Rate Analyst", 5, "B", "estimator", "2"),
    (39, "BOQ Builder & Abstract Pricer", 5, "A/B", "estimator", "2"),
    (40, "Cost Planner & Value Engineer", 5, "B", "cost manager", ""),
    (41, "Cost Controller", 5, "A", "cost manager", "2"),
    (42, "Cash-flow & Budget Manager", 5, "A", "project finance", ""),
    (43, "Earned-value Analyst", 5, "A/B", "planner / PM", ""),
    # 6. Contracts, commercial & disputes (R4 C)
    (44, "Contracts Administrator", 6, "A", "contracts manager", "2"),
    (45, "Variation & Change-order Assistant", 6, "A/B", "commercial manager", "2"),
    (46, "Claims Assistant", 6, "B", "claims consultant", "2"),
    (47, "Delay Analyst's Working-paper Builder", 6, "B", "forensic planner", "3"),
    (48, "Liquidated-damages Calculator", 6, "B", "contracts manager + legal", ""),
    (49, "Retention, Price-variation & Escalation Calculator", 6, "A", "QS", "2"),
    (50, "Dispute / Arbitration Bundle Assistant", 6, "A/B", "counsel", ""),
    (51, "Insurance & Bonds Coordinator", 6, "A", "contracts / finance", "2"),
    # 7. Tendering & procurement (R4 D-E)
    (52, "Tender Manager's Assistant", 7, "A", "tender manager", "2"),
    (53, "Tender Document Writer", 7, "B", "bid manager", "2"),
    (54, "Bid Pricer", 7, "B", "bid manager", "2"),
    (55, "Pre-qualification Dossier Builder", 7, "A", "bid manager", "2"),
    (56, "Procurement Manager's Assistant", 7, "A", "procurement manager", "2"),
    (57, "Purchase Engineer", 7, "B", "purchase engineer", ""),
    (58, "Vendor Developer", 7, "A", "procurement head", "2"),
    (59, "Expediter & Logistics Coordinator", 7, "A", "procurement", ""),
    (60, "Import/Customs Coordinator", 7, "A", "EXIM", ""),
    (61, "Material Planner & Store Manager", 7, "A", "store in-charge", "1"),
    (62, "Subcontract & Work-order Manager *", 7, "A", "contracts / site", "1"),
    # 8. Planning & project controls (R2 section 2)
    (63, "Project Planner / Scheduler", 8, "A/B", "planner", ""),
    (64, "Progress Measurement Assistant *", 8, "A", "site engineer", "1"),
    (65, "Resource & Productivity Analyst", 8, "A", "project manager", ""),
    (66, "Risk & Issues Register Keeper", 8, "A", "PM", ""),
    (67, "Meeting Secretary (OAC / site / coordination)", 8, "A", "PM", "1"),
    (68, "Project Director's Dashboard", 8, "A", "project director", ""),
    (69, "Construction Management / PMC Assistant", 8, "B", "PMC lead", ""),
    # 9. Site execution, quality & measurement (R2 sections 3, 4, 6)
    (70, "Site Supervisor Assistant *", 9, "A", "site engineer", "1"),
    (71, "Site Manager (Theka Sahayak) *", 9, "A", "contractor", "1"),
    (72, "Pour & Concrete Records Keeper", 9, "B", "QA engineer", "2"),
    (73, "Rebar Bar-bending Schedule Assistant", 9, "B", "structural/site engineer", "2"),
    (74, "Formwork & Scaffold Planner", 9, "B", "site engineer", ""),
    (75, "Quality Auditor's Assistant", 9, "A/B", "QA/QC manager", "1"),
    (76, "Material Test Register Keeper", 9, "A", "QC engineer", ""),
    (77, "Setting-out & Level Check Recorder", 9, "A/B", "survey engineer", ""),
    (78, "Snagging & Punch-list Manager", 9, "A", "QA engineer", "1"),
    (79, "Specialist Works Coordinators", 9, "B", "respective specialists", ""),
    (80, "Concrete-Pump, Crane & Plant Scheduler", 9, "A", "plant manager", ""),
    # 10. Safety, health, environment & labour (R2 section 5, 7; R4 F4)
    (81, "EHS Officer's Assistant", 10, "A/B", "safety officer", "2"),
    (82, "Incident Investigation Assistant", 10, "B", "safety head", "3"),
    (83, "Safety Training & Competency Tracker", 10, "A", "EHS", ""),
    (84, "Environmental Monitoring Assistant", 10, "A", "EHS", ""),
    (85, "Labour Compliance Desk", 10, "A", "compliance officer", "1"),
    (86, "Labour Camp & Welfare Manager", 10, "A", "labour welfare officer", ""),
    (87, "Wage & Payment Auditor", 10, "A", "accounts", "1"),
    # 11. Finance, tax & accounts for builders (R4 F)
    (88, "Running-account (RA) Bill Processor *", 11, "A/B", "billing engineer", "1"),
    (89, "GST on Works Contract Assistant", 11, "B", "tax consultant", ""),
    (90, "BOCW Cess & TDS Calculator", 11, "A", "accounts", "1"),
    (91, "Builder's Accounting & Reconciliation", 11, "A", "accountant", "1"),
    (92, "Customer Payment & Demand-letter Manager", 11, "A", "CRM head", "1"),
    (93, "Escrow / RERA Account Reconciler", 11, "B", "CA", "2"),
    # 12. Sales, marketing & customer journey (R5 B5-B9)
    (94, "Project CRM & Sales Assistant", 12, "A", "sales head", ""),
    (95, "Project Marketing Assistant", 12, "B", "marketing + legal", ""),
    (96, "Agreement-for-sale & Documentation Assistant", 12, "B", "legal manager", ""),
    (97, "Customer Handover / Possession Manager", 12, "A", "handover manager", ""),
    (98, "Customer Care & Defect-liability Desk", 12, "A", "service head", "1"),
    (99, "Investor / Lender Reporting Assistant", 12, "A", "IR / finance", ""),
    # 13. Operations: facility, property & community (R5 C; existing property/society employees)
    (100, "Property Manager Assistant *", 13, "A", "property manager", ""),
    (101, "Society / Association Manager *", 13, "A", "society secretary / manager", ""),
    (102, "Facilities Manager's Assistant", 13, "A", "FM head", ""),
    (103, "MEP Maintenance Planner", 13, "A", "chief engineer", ""),
    (104, "Energy Manager / Auditor Assistant", 13, "B", "energy auditor", "3"),
    (105, "Lift / Fire / STP / WTP Compliance Tracker", 13, "A", "FM", ""),
    (106, "Housekeeping & Security Rosters", 13, "A", "FM", ""),
    (107, "Structural-safety & Building-audit Scheduler", 13, "A", "society / owner", ""),
    (108, "Asset & Space Manager", 13, "A", "asset manager", ""),
    (109, "Digital Twin Data Steward", 13, "B", "asset information manager", ""),
    # 14. Sustainability, commissioning & performance (R6 C-D)
    (110, "Green Building Consultant's Assistant", 14, "B", "AP / CP", "3"),
    (111, "ECBC / Energy-code Compliance Checker", 14, "B", "ECBC assessor", "3"),
    (112, "Energy Modelling Assistant", 14, "B", "energy modeller", "3"),
    (113, "Daylight & Thermal-comfort Analyst", 14, "B", "building physicist", "3"),
    (114, "Embodied Carbon / LCA Assistant", 14, "B", "LCA assessor", "3"),
    (115, "Water, Rainwater & Waste Planner", 14, "B", "consultant", "3"),
    (116, "Commissioning Authority's Assistant", 14, "B", "commissioning manager", "3"),
    (117, "T&C Records Keeper", 14, "A", "T&C engineer", "3"),
    (118, "M&V Analyst", 14, "B", "energy analyst", "3"),
    # 15. Visualisation, marketing media & training
    (119, "Architectural Visualiser", 15, "A", "visualiser", ""),
    (120, "Presentation & Report Designer", 15, "A", "architect / PM", ""),
    (121, "Construction Skill Trainer", 15, "A", "training centre", ""),
    (122, "Construction Student Tutor", 15, "A", "faculty", ""),
    (123, "Contractor Business Coach", 15, "A/B", "contractor / CA", ""),
]

FIELDS = {1: "Land, feasibility & development", 2: "Architecture, design & consultancy",
          3: "Digital delivery: BIM, survey, reality capture", 4: "Approvals, permits & statutory compliance",
          5: "Estimating, quantity surveying & cost", 6: "Contracts, commercial & disputes",
          7: "Tendering & procurement", 8: "Planning & project controls",
          9: "Site execution, quality & measurement", 10: "Safety, health, environment & labour",
          11: "Finance, tax & accounts for builders", 12: "Sales, marketing & customer journey",
          13: "Operations: facility, property & community", 14: "Sustainability, commissioning & performance",
          15: "Visualisation, marketing media & training"}

WAVE1_IDS = [61, 62, 64, 67, 70, 71, 75, 78, 85, 87, 88, 90, 91, 92, 98]
WAVE2_IDS = [9, 16, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 41, 44, 45, 46, 49, 51, 52, 53, 54, 55, 56, 58, 72, 73, 81, 93]
WAVE3_IDS = [10, 11, 12, 18, 19, 20, 21, 22, 23, 24, 26, 47, 82, 104, 110, 111, 112, 113, 114, 115, 116, 117, 118]

# register id -> where the work lives in Hoola after Wave 1 (the Hub key, or the existing desk that owns it)
WAVE1_HOME: dict[int, str] = {
    61: "const_store", 62: "theka (subcontract & work orders)", 64: "sitesup (progress)",
    67: "const_meet", 70: "sitesup (voice log)", 71: "theka (wage calc)",
    75: "const_quality (ITP/NCR)", 76: "const_quality (test lots)", 78: "const_quality (punch, sitesup snags)",
    85: "const_labour (compliance)", 87: "const_labour (wage audit)", 88: "theka (RA bills)",
    90: "const_labour (cess/TDS)", 91: "const_books", 92: "const_customer (demands)",
    97: "const_customer (handover)", 98: "const_customer (DLP)",
}

# register id -> where the work lives after Wave 2 (v0.531.0). 72 stays with the Wave-1 quality desk
# (pour/cube ride sitesup); #33 heritage/AAI/CRZ screener and #42,43,47,48,50,57,59,60 stay unwaved.
WAVE2_HOME: dict[int, str] = {
    9: "const_drawqa (bye-law rules)", 16: "const_drawqa (review pack)", 28: "const_approvals",
    29: "const_approvals (packet)", 30: "const_approvals (fire NOC)", 31: "const_approvals (EC/CTE-CTO)",
    32: "const_approvals (utility)", 34: "const_approvals (statutory calendar)", 35: "const_rera",
    36: "const_approvals (OC/CC packet)", 37: "const_qs (takeoff)", 38: "const_qs (rates)", 39: "const_qs (BOQ)",
    41: "const_qs (cost control)", 44: "const_contracts", 45: "const_contracts (variations)",
    46: "const_contracts (claims)", 49: "const_qs (retention/PV)", 51: "const_contracts (insurance/bonds)",
    52: "const_tender", 53: "const_tender (packs)", 54: "const_tender (price pack)",
    55: "const_tender (prequal)", 56: "const_tender (procurement rows)", 58: "const_tender (vendors)",
    72: "const_quality + sitesup (pour records, Wave 1)", 73: "const_qs (BBS draft)",
    81: "const_quality (EHS permits & toolbox)", 93: "const_rera (escrow)",
}

# register id -> where the work lives after Wave 3 (v0.550.0, C11-C15). The model-level + certificate-
# adjacent wave: open formats on every card (IFC read / BCF write / IDS subset / LandXML CgPoints /
# CSV-not-E57), a named licensee on every output, criticality and entitlement never computed.
# #82 rides the Wave-1 quality desk (the EHS home, like #81); #25,27,74,77,109 stay unwaved.
WAVE3_HOME: dict[int, str] = {
    10: "const_predesign (load take-down, cl 39.3 size)", 11: "const_predesign (MEP estimates)",
    12: "const_predesign (fire rule rows + demand)", 18: "const_bim (health, naming, IDS)",
    19: "const_bim (CDE, transmittals)", 20: "const_bim (clash, BCF)", 21: "const_bim (4D/5D)",
    22: "const_survey (LandXML CgPoints, traverse, area)", 23: "const_survey (grid volumes)",
    24: "const_survey (CSV deviations)", 26: "const_survey (RERA carpet)",
    47: "const_delay (windows, slips, notice maths)", 82: "const_quality (incident investigation)",
    104: "const_green (meters, tariff, EPI)", 110: "const_green (credits tracker)",
    111: "const_green (ECBC checks)", 112: "const_green (model input register)",
    113: "const_green (daylight WFR)", 114: "const_green (carbon hotspots)",
    115: "const_green (water demand, RWH)", 116: "const_green (Cx scripts + issues)",
    117: "const_green (T&C records)", 118: "const_green (M&V baseline + savings)",
}


def get(eid: int) -> dict | None:
    for r in ROWS:
        if r[0] == eid:
            return {"id": r[0], "name": r[1], "field": r[2], "field_name": FIELDS.get(r[2], ""), "tier": r[3], "human": r[4], "wave": r[5]}
    return None


def wave(w: str) -> list[dict]:
    return [r for r in (get(i) for i, *_ in ROWS) if r and r["wave"] == w]


def field(n: int) -> list[dict]:
    return [r for r in (get(i) for i, *_ in ROWS) if r and r["field"] == n]


def stats() -> dict:
    out = {"total": len(ROWS), "by_tier": {}, "by_wave": {}}
    for r in ROWS:
        out["by_tier"][r[3]] = out["by_tier"].get(r[3], 0) + 1
        out["by_wave"][r[5] or "later"] = out["by_wave"].get(r[5] or "later", 0) + 1
    return out
