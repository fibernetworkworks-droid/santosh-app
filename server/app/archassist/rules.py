"""Archassist Sahayak rules: STARTER rule tables (editable), area / unit helpers, the zoning check, document and approval
checklists, fee + GST + TDS maths. Every number here is a starting point to check against the rule book; nothing is final.

Research (23 Oct 2026, sources in WIRING.md): UDCPR 2020 (Maharashtra, notified 2 Dec 2020, amended since) non-congested basic
FSI 1.10, premium up to 0.50, TDR up to 1.40 on 30 m+ roads, max 3.00; congested basic 1.50 (< 9 m road) / 2.00 (>= 9 m);
side / rear margins above the low-rise height = H/5 capped at 12 m. DCPR 2034 (Mumbai) zonal basic FSI 1.00 suburbs / 1.33
island city, premium + TDR by road width, fungible compensatory area (Reg 31(3)) on premium. Architects Act 1972 (CoA),
CoA Conditions of Engagement & Scale of Charges (representative stage split 10 / 20 / 20 / 25 / 25, her agreement decides),
GST on architectural services SAC 998321 @ 18%, TDS on professional fees: Income-tax Act 2025 Sec 393(1) (old 194J) 10% above
Rs 50,000 a year (client deducts), RERA 2016 Sec 4(2)(l)(D) + MahaRERA Form 1 (architect's certificate) for withdrawals from the
70% account, EIA Notification 2006 item 8(a) (built-up >= 20,000 sq m), AAI NOCAS height NOC inside airport CCZM, Maharashtra
(Urban Areas) Protection and Preservation of Trees Act 1975 (tree permission), NBC 2016 (high-rise = 15 m and above)."""
from __future__ import annotations

import math
import re
from typing import Any

NEVER = [
    "Koi drawing / transmittal client ya authority ko aapke tap ke bina issue nahi hota.",
    "Koi invoice aapke tap ke bina number nahi paata, na bhejta hai.",
    "Koi submission (BPMS / AutoDCR / NOC) aapke tap ke bina 'submit karo' nahi banta; portal par login / fee / OTP aap khud.",
    "FSI / setback / parking ki jaanch sirf andaaza hai: rule book aur authority ka faisla hi final.",
    "Plot ka area, rate, fee, tareekh khud se nahi banti: aapke number, warna khaali.",
    "Hoola paise nahi leta, nahi bhejta; Aadhaar / PAN sirf Pehchaan Locker ke reference se.",
]
CHECK_LINE = "Rule book (aur authority) se pakka kijiye: yeh andaaza hai, final nahi."

SQFT = 0.09290304
UNITS = {"sqm": 1.0, "sq m": 1.0, "sq.m": 1.0, "m2": 1.0, "meter": 1.0, "sqft": SQFT, "sq ft": SQFT, "sq.ft": SQFT, "ft": SQFT,
         "guntha": 101.17, "gunta": 101.17, "acre": 4046.86, "hectare": 10000.0, "ha": 10000.0}

# ---------------------------------------------------------------- starter rule sets (all editable by her `overrides`)
# fsi bands: (road_from_m, road_to_m (exclusive, None = up), basic, premium, tdr). None = unknown (she must give it).
RULESETS: dict[str, dict[str, Any]] = {
    "udcpr": {
        "label": "UDCPR 2020 (Maharashtra, non-congested)",
        "fsi": [(0, 9, 1.10, 0.0, 0.0), (9, 12, 1.10, 0.50, 0.40), (12, 15, 1.10, 0.50, 0.65), (15, 24, 1.10, 0.50, 0.90),
                (24, 30, 1.10, 0.50, 1.15), (30, None, 1.10, 0.50, 1.40)],
        "front": [(0, 9, 3.0), (9, 18, 4.5), (18, 30, 6.0), (30, None, 6.0)],
        "low_rise_m": 15.0, "side_low": 3.0, "side_div": 5.0, "side_cap": 12.0,
        "ancillary_pct": {"residential": 60, "commercial": 80},
        "open_space": {"min_plot": 4000.0, "pct": 10.0}, "amenity": {"min_plot": 20000.0, "pct": 5.0},
        "notes": ["Ancillary FSI premium par (residential 60% / commercial 80% tak) - rule book check.",
                  "Road widening / reservation dene par in-situ FSI / TDR - Reg dekhiye.",
                  "TOD zone / metro ke paas alag FSI ho sakta hai."],
    },
    "udcpr_congested": {
        "label": "UDCPR 2020 (Maharashtra, congested / gaothan)",
        "fsi": [(0, 9, 1.50, None, None), (9, None, 2.00, None, None)],
        "front": [], "low_rise_m": 15.0, "side_low": None, "side_div": 5.0, "side_cap": 12.0,
        "ancillary_pct": {"residential": 60, "commercial": 80}, "open_space": None, "amenity": None,
        "notes": ["Congested area ke premium / TDR aur margins aapke shehar ki table se daaliye."],
    },
    "dcpr_suburbs": {
        "label": "DCPR 2034 (Mumbai suburbs)",
        "fsi": [(0, 9, 1.00, 0.0, 0.0), (9, 12, 1.00, 0.50, 0.50), (12, 18, 1.00, 0.50, 0.70), (18, 27, 1.00, 0.50, 0.90),
                (27, None, 1.00, 0.50, 1.00)],
        "front": [], "low_rise_m": 15.0, "side_low": None, "side_div": None, "side_cap": None,
        "ancillary_pct": {}, "open_space": None, "amenity": None, "fungible_pct": 35.0,
        "notes": ["Fungible compensatory area (Reg 31(3)) premium par - alag se.", "Margins DCPR Reg 41 se daaliye."],
    },
    "dcpr_island": {
        "label": "DCPR 2034 (Mumbai island city)",
        "fsi": [(0, None, 1.33, None, None)],
        "front": [], "low_rise_m": 15.0, "side_low": None, "side_div": None, "side_cap": None,
        "ancillary_pct": {}, "open_space": None, "amenity": None, "fungible_pct": 35.0,
        "notes": ["Island city premium / TDR road width se: DCPR Reg 30 Table 12 ke number daaliye."],
    },
    "custom": {"label": "Apni table (aapke number)", "fsi": [], "front": [], "low_rise_m": 15.0, "side_low": None,
               "side_div": None, "side_cap": None, "ancillary_pct": {}, "open_space": None, "amenity": None, "notes": []},
}

# ---------------------------------------------------------------- plot / title papers (Maharashtra; editable list)
PLOT_DOCS = [
    ("seven_twelve", "7/12 utara (gaon / NA zameen)"), ("property_card", "Property card (city survey)"),
    ("ferfar", "Ferfar / mutation entries"), ("title", "Title search report / title certificate (vakil)"),
    ("deed", "Sale deed / conveyance / lease"), ("na_order", "NA order / sanad (non-agricultural)"),
    ("measurement", "Measurement / demarcation plan (TILR / city survey)"), ("zone", "Zone certificate / DP remarks"),
    ("road_width", "Road width proof (DP / municipal)"), ("poa", "Power of attorney (agar owner khud nahi)"),
    ("tax", "Property tax / bijli bill"), ("society_noc", "Society NOC (redevelopment ho to)"),
    ("old_sanction", "Purana sanction / OC (alteration ho to)"),
]

AUTHORITIES: dict[str, dict[str, Any]] = {
    "maha_bpms": {"label": "Maha BPMS (Maharashtra UDCPR shehar / parishad)", "portal": "Maha BPMS",
                  "steps": ["Architect login (CoA no.) par project banaiye", "Plot details + 7/12 / property card upload",
                            "Drawings (DWG/PDF) upload, scrutiny fee bharna (aap khud)", "Scrutiny / site visit query ka jawab",
                            "Building permission -> commencement certificate (CC)", "Plinth checking certificate",
                            "Completion + occupancy certificate (OC)"]},
    "mcgm_autodcr": {"label": "MCGM (Mumbai) online building permission (AutoDCR)", "portal": "MCGM EoDB / AutoDCR",
                     "steps": ["Architect / LS login, proposal file", "AutoDCR drawing scrutiny", "IOD / building permission",
                               "Commencement certificate (CC)", "Further CC / plinth", "Occupancy certificate + BCC"]},
    "pmrda": {"label": "PMRDA (Pune region)", "portal": "PMRDA BPMS",
              "steps": ["Online proposal", "Scrutiny fee", "Building permission + CC", "Plinth checking", "OC"]},
    "midc_bpams": {"label": "MIDC BPAMS (industrial plot)", "portal": "MIDC BPAMS",
                   "steps": ["Online application", "Plan approval", "Fire NOC (MIDC fire)", "Commencement", "Completion / OC"]},
    "custom": {"label": "Doosri authority", "portal": "", "steps": ["Aapki authority ke steps daaliye"]},
}
STAGES = ["building_permission", "cc", "plinth", "oc"]
STAGE_LABEL = {"building_permission": "Building permission / IOD", "cc": "Commencement certificate", "plinth": "Plinth checking",
               "oc": "Occupancy / completion", "noc_fire": "Fire NOC", "noc_tree": "Tree authority NOC", "noc_airport": "AAI height NOC",
               "noc_env": "Environment clearance (SEIAA)", "noc_heritage": "Heritage NOC", "noc_crz": "CRZ (MCZMA)",
               "noc_railway": "Railway NOC", "noc_highway": "Highway / NHAI NOC", "rera": "RERA project registration",
               "structural": "Structural design + stability (licensed engineer)", "other": "Doosra"}


def nocs(facts: dict[str, Any], height: float | None, bua: float | None) -> list[dict[str, str]]:
    """NOCs this project likely needs, each with WHY in her words. Flags come from her (near airport, trees...)."""
    out: list[dict[str, str]] = []
    h, b = height or 0.0, bua or 0.0
    use = str(facts.get("use") or "residential")
    if h >= 15.0 or use in ("assembly", "commercial", "hospital", "school", "hotel", "mall", "industrial"):
        out.append({"key": "noc_fire", "why": f"Height {h:g} m (15 m+ = high-rise, NBC 2016) ya use {use}: fire NOC / CFO approval."})
    if facts.get("trees"):
        out.append({"key": "noc_tree", "why": "Plot par ped kaatne / hatane: Tree Authority permission (Maharashtra Trees Act 1975; "
                                              "50+ saal purana = heritage tree)."})
    if facts.get("near_airport"):
        out.append({"key": "noc_airport", "why": "Airport ke CCZM zone mein: AAI NOCAS height NOC (site ke coordinates + top elevation)."})
    if b >= 20000.0:
        out.append({"key": "noc_env", "why": f"Total built-up {b:,.0f} sq m (20,000+): environment clearance (EIA 2006 item 8(a))."})
    if facts.get("heritage"):
        out.append({"key": "noc_heritage", "why": "Heritage building / precinct: heritage committee NOC."})
    if facts.get("coastal"):
        out.append({"key": "noc_crz", "why": "Coastal (CRZ) area: MCZMA clearance."})
    if facts.get("railway"):
        out.append({"key": "noc_railway", "why": "Railway line ke paas: railway NOC."})
    if facts.get("highway"):
        out.append({"key": "noc_highway", "why": "National / state highway ke paas: highway authority NOC."})
    if facts.get("promoter") and (b > 500 or int(facts.get("units") or 0) > 8):
        out.append({"key": "rera", "why": "Bechne ke liye project, 500 sq m+ ya 8+ flat: RERA registration (Sec 3), har ad par RERA no."})
    if h > 0 or b > 0:
        out.append({"key": "structural", "why": "Structural design + stability certificate licensed structural engineer se."})
    return out


# ---------------------------------------------------------------- numbers + units
def num(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.\-]", "", str(v).replace(",", ""))
    try:
        return float(s) if s not in ("", "-", ".") else None
    except ValueError:
        return None


def area_sqm(v, unit: str = "") -> float | None:
    """'2,400 sqft' / '5 guntha' / 450 -> square metres (plain numbers = sq m unless unit says)."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v) * UNITS.get(unit.strip().lower(), 1.0) if unit else float(v)
    s = str(v).lower()
    n = num(re.sub(r"[a-z.]+\s*$", "", s.strip()) or s)
    if n is None:
        return None
    u = unit.strip().lower()
    if not u:
        for k in sorted(UNITS, key=len, reverse=True):
            if k in s:
                u = k
                break
    return round(n * UNITS.get(u, 1.0), 3)


def band(rows: list, road: float | None):
    if road is None:
        return None
    for r in rows:
        lo, hi = r[0], r[1]
        if road >= lo and (hi is None or road < hi):
            return r
    return None


def ruleset(key: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base = RULESETS.get(key or "udcpr") or RULESETS["udcpr"]
    rs = {k: (list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v)) for k, v in base.items()}
    rs["key"] = key if key in RULESETS else "udcpr"
    rs["starter"] = True
    o = dict(overrides or {})
    for k in ("basic", "premium", "tdr", "front", "side", "rear", "max_height", "ground_coverage_pct", "parking_per_unit",
              "parking_min", "open_space_pct", "fungible_pct"):
        if o.get(k) not in (None, ""):
            rs["her_" + k] = num(o[k])
    return rs


# ---------------------------------------------------------------- the zoning check
def _c(status: str, item: str, got: Any = None, need: Any = None, note: str = "") -> dict[str, Any]:
    return {"status": status, "item": item, "got": got, "need": need, "note": note}


def area_statement(plot: dict[str, Any], proposal: dict[str, Any], rs: dict[str, Any]) -> dict[str, Any]:
    """Area statement + checks from HER plot and proposal numbers against the chosen (starter / her) rule set."""
    gross = num(plot.get("area_sqm"))
    checks: list[dict[str, Any]] = []
    if not gross:
        return {"ok": False, "checks": [_c("check", "Plot area", None, None, "Plot area (7/12 / property card ke hisaab se) chahiye.")],
                "say": "Plot area chahiye - tabhi area statement banega.", "check_line": CHECK_LINE}
    widen = num(plot.get("road_widening_sqm")) or 0.0
    reserve = num(plot.get("reservation_sqm")) or 0.0
    net = round(gross - widen - reserve, 3)
    on_gross = bool(plot.get("fsi_on_gross"))
    base_area = gross if on_gross else net
    road = num(plot.get("road_width_m"))
    b = band(rs.get("fsi") or [], road)
    basic = rs.get("her_basic", b[2] if b else None)
    premium = rs.get("her_premium", b[3] if b else None)
    tdr = rs.get("her_tdr", b[4] if b else None)
    missing = [n for n, v in (("road width", road), ("basic FSI", basic)) if v is None]
    lay = {"gross_plot": gross, "road_widening": widen, "reservation": reserve, "net_plot": net,
           "fsi_on": "gross" if on_gross else "net", "road_width_m": road,
           "basic_fsi": basic, "premium_fsi": premium, "tdr_fsi": tdr}
    if basic is not None:
        lay["basic_area"] = round(base_area * basic, 2)
    if premium is not None:
        lay["premium_area"] = round(base_area * premium, 2)
    if tdr is not None:
        lay["tdr_area"] = round(base_area * tdr, 2)
    known = [x for x in (basic, premium, tdr) if x is not None]
    lay["max_fsi"] = round(sum(known), 3) if basic is not None else None
    lay["max_area"] = round(base_area * lay["max_fsi"], 2) if lay["max_fsi"] is not None else None
    if premium is None or tdr is None:
        checks.append(_c("check", "Premium / TDR", None, None, "Is rule set mein premium / TDR ka number nahi: apni table se daaliye."))
    # proposed built-up
    floors = proposal.get("floors") or []
    bua = sum((num(f.get("area_sqm") if isinstance(f, dict) else f) or 0.0) for f in floors)
    if not bua:
        bua = num(proposal.get("bua_sqm")) or 0.0
    lay["proposed_bua"] = round(bua, 2)
    if bua and lay.get("basic_area") is not None:
        lay["consumed_fsi"] = round(bua / base_area, 3)
        if bua <= lay["basic_area"]:
            checks.append(_c("ok", "FSI", lay["consumed_fsi"], basic, "Basic FSI ke andar."))
        elif lay["max_area"] is not None and bua <= lay["max_area"] + 0.01:
            need_p = round(min(bua - lay["basic_area"], lay.get("premium_area") or 0), 2)
            need_t = round(max(0.0, bua - lay["basic_area"] - (lay.get("premium_area") or 0)), 2)
            checks.append(_c("warn", "FSI", lay["consumed_fsi"], lay["max_fsi"],
                             f"Basic se upar: premium ~{need_p:g} sq m" + (f" + TDR ~{need_t:g} sq m" if need_t else "") +
                             " lagega (premium paise authority ko, aapke client se)."))
        else:
            checks.append(_c("fail", "FSI", lay["consumed_fsi"], lay["max_fsi"],
                             f"Proposed {bua:,.0f} sq m max {lay['max_area'] or 0:,.0f} se zyada (is table ke hisaab se)."))
        anc = (rs.get("ancillary_pct") or {}).get(str(proposal.get("use") or "residential"))
        if anc:
            checks.append(_c("check", "Ancillary FSI", None, f"{anc}%", "Ancillary area premium par alag - rule book check."))
        if rs.get("fungible_pct") or rs.get("her_fungible_pct"):
            checks.append(_c("check", "Fungible", None, f"{rs.get('her_fungible_pct', rs.get('fungible_pct')):g}%",
                             "Fungible compensatory area premium par (DCPR Reg 31(3))."))
    # height + margins
    h = num(proposal.get("height_m"))
    low = rs.get("low_rise_m") or 15.0
    if h:
        mh = rs.get("her_max_height")
        if mh is not None:
            checks.append(_c("ok" if h <= mh else "fail", "Height", h, mh, "Aapki di hui height seema."))
        if h >= low:
            checks.append(_c("warn", "High-rise", h, f"< {low:g}", "15 m+ = high-rise (NBC 2016): fire NOC, refuge / lift / stair rules."))
    fb = band(rs.get("front") or [], road)
    front_need = rs.get("her_front", fb[2] if fb else None)
    fp = num(proposal.get("front_m"))
    if fp is not None:
        if front_need is None:
            checks.append(_c("check", "Front margin", fp, None, "Front margin ki table daaliye."))
        else:
            checks.append(_c("ok" if fp >= front_need else "fail", "Front margin", fp, front_need, f"Road {road or '?'} m ke hisaab se."))
    side_need = rs.get("her_side")
    if side_need is None and h:
        if h < low and rs.get("side_low") is not None:
            side_need = rs["side_low"]
        elif h >= low and rs.get("side_div"):
            side_need = round(min(h / rs["side_div"], rs.get("side_cap") or 99), 2)
    rear_need = rs.get("her_rear", side_need)
    for key, label, need in (("side_m", "Side margin", side_need), ("rear_m", "Rear margin", rear_need)):
        got = num(proposal.get(key))
        if got is None:
            continue
        if need is None:
            checks.append(_c("check", label, got, None, "Is height ke liye margin ki table daaliye."))
        else:
            checks.append(_c("ok" if got >= need else "fail", label, got, need,
                             "H/5 (max 12 m) high-rise ke liye" if h and h >= low and rs.get("side_div") else "Starter table."))
    gc = rs.get("her_ground_coverage_pct")
    fp_area = num(proposal.get("footprint_sqm"))
    if gc is not None and fp_area:
        pct = round(fp_area * 100 / net, 1) if net else None
        checks.append(_c("ok" if pct is not None and pct <= gc else "fail", "Ground coverage", pct, gc, "% of net plot."))
    # open space / amenity on big plots
    for key, label in (("open_space", "Open space"), ("amenity", "Amenity space")):
        o = rs.get(key)
        pct = rs.get("her_open_space_pct") if key == "open_space" else None
        if o and gross >= o["min_plot"]:
            p = pct if pct is not None else o["pct"]
            got = num(proposal.get(key + "_sqm"))
            need = round(gross * p / 100, 2)
            checks.append(_c("check" if got is None else ("ok" if got >= need else "fail"), label, got, need,
                             f"Plot {o['min_plot']:,.0f} sq m+ = {p:g}% (starter)."))
    # parking
    units = int(num(proposal.get("units")) or 0)
    ppu = rs.get("her_parking_per_unit")
    got_p = num(proposal.get("parking"))
    if ppu is not None and units:
        need = max(math.ceil(units * ppu), int(rs.get("her_parking_min") or 0))
        if got_p is not None:
            checks.append(_c("ok" if got_p >= need else "fail", "Parking", got_p, need, f"{units} unit x {ppu:g} (aapka niyam)."))
        else:
            checks.append(_c("check", "Parking", None, need, "Proposal mein kitni parking hai?"))
    elif units or got_p is not None:
        checks.append(_c("check", "Parking", got_p, None, "Parking ki table (UDCPR Table 8 / DCPR Reg 44) se per-unit number daaliye."))
    for n in missing:
        checks.append(_c("check", n, None, None, f"{n} chahiye."))
    fails = [c for c in checks if c["status"] == "fail"]
    warns = [c for c in checks if c["status"] in ("warn", "check")]
    say = (f"Area statement: net plot {net:,.2f} sq m" + (f", max FSI {lay['max_fsi']:g} = {lay['max_area']:,.0f} sq m" if lay.get("max_area") else "")
           + (f", proposed {bua:,.0f} sq m" if bua else "") + ". "
           + (f"{len(fails)} jagah niyam se bahar. " if fails else "") + (f"{len(warns)} cheezein dekhni hain. " if warns else "")
           + CHECK_LINE)
    return {"ok": not fails, "statement": lay, "checks": checks, "ruleset": rs.get("label", ""), "starter": True,
            "notes": list(rs.get("notes") or []), "say": say, "check_line": CHECK_LINE}


# ---------------------------------------------------------------- fee / GST / TDS
FEE_STAGES = [("appointment", "Appointment / advance", 10.0), ("concept", "Concept design manzoor", 20.0),
              ("approval", "Drawings for approval / sanction", 20.0), ("working", "Working drawings + tender", 25.0),
              ("construction", "Construction ke dauraan + completion", 25.0)]
GST_RATE = 18.0
SAC = "998321"
TDS_PCT = 10.0
TDS_LIMIT = 50000.0


def stage_amount(fee: dict[str, Any], pct: float) -> float | None:
    basis = fee.get("basis")
    if basis == "lump":
        tot = num(fee.get("lump"))
    else:
        p, cost = num(fee.get("percent")), num(fee.get("project_cost"))
        tot = (p * cost / 100) if p is not None and cost is not None else None
    return round(tot * pct / 100, 2) if tot else None


def gst_split(amount: float, her_gstin: str, client_gstin: str = "", client_state: str = "", rate: float = GST_RATE) -> dict[str, Any]:
    if not her_gstin:
        return {"taxable": round(amount, 2), "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "total": round(amount, 2), "gst": False,
                "note": "Aapka GSTIN nahi diya: bina GST ka bill (services ki seema Rs 20 lakh; pakka CA se)."}
    mine = her_gstin[:2]
    theirs = (client_gstin[:2] if client_gstin else "") or (client_state or "")
    tax = round(amount * rate / 100, 2)
    if theirs and theirs != mine:
        return {"taxable": round(amount, 2), "cgst": 0.0, "sgst": 0.0, "igst": tax, "total": round(amount + tax, 2), "gst": True,
                "note": f"Doosra state: IGST {rate:g}% (SAC {SAC})."}
    half = round(tax / 2, 2)
    return {"taxable": round(amount, 2), "cgst": half, "sgst": round(tax - half, 2), "igst": 0.0, "total": round(amount + tax, 2),
            "gst": True, "note": f"CGST + SGST {rate / 2:g}% each (SAC {SAC})" + ("" if theirs else "; client ka state pata nahi, same state maana.")}


def tds_expected(fy_before: float, this_amount: float) -> dict[str, Any]:
    """Client deducts 10% under Sec 393(1) (Income-tax Act 2025; old 194J) once the FY total crosses Rs 50,000."""
    total = fy_before + this_amount
    if total <= TDS_LIMIT:
        return {"tds": 0.0, "note": f"Is saal kul {total:,.0f} (Rs 50,000 tak TDS nahi)."}
    base = this_amount if fy_before > TDS_LIMIT else total
    return {"tds": round(base * TDS_PCT / 100, 2),
            "note": "Client 10% TDS kaatega (Sec 393(1), Income-tax Act 2025) - fee par, GST par nahi; 26AS / Form 16A mein dekhiye."}


def fy_of(d) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def sheet_ok(sheet: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/\-]{0,23}", sheet or ""))


def next_rev(cur: str) -> str:
    """P0 -> P1, A -> B, R2 -> R3, 0 -> 1; blank -> 'R0'."""
    c = (cur or "").strip()
    if not c:
        return "R0"
    m = re.fullmatch(r"([A-Za-z]*)(\d+)", c)
    if m:
        return f"{m.group(1)}{int(m.group(2)) + 1}"
    if re.fullmatch(r"[A-Y]", c, flags=re.I):
        return chr(ord(c) + 1)
    return c + "-1"


DISCIPLINES = {"A": "Architecture", "S": "Structure", "E": "Electrical", "P": "Plumbing", "M": "Mechanical / HVAC", "F": "Fire",
               "L": "Landscape", "I": "Interior", "C": "Civil / site"}
PURPOSES = {"for_approval": "For approval", "for_construction": "For construction", "for_information": "For information",
            "for_comments": "For comments", "for_submission": "For submission to authority", "for_tender": "For tender"}
TO_KINDS = {"client": "Client", "authority": "Authority", "consultant": "Consultant", "contractor": "Contractor", "other": "Other"}
CONSULTANT_KINDS = {"structural": "Structural", "mep": "MEP", "electrical": "Electrical", "plumbing": "Plumbing", "hvac": "HVAC",
                    "fire": "Fire", "landscape": "Landscape", "interior": "Interior", "surveyor": "Surveyor", "liaison": "Liaison", "other": "Other"}
