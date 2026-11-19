"""Import & customs rules Hoola works to (researched 23 Oct 2026; sources in WIRING.md). Pure functions, no I/O.

Never invented: duty RATES (BCD / IGST / cess / AIDC) and the exchange rate come only from her (from the Customs Tariff /
CBIC notification / her CHA). The only numbers built in are statutory ones: SWS 10% of BCD (Finance Act 2018 s.110, where not
exempt), Customs Valuation Rules 2007 rule 10(2) as amended by G.S.R. 1202(E) (2017): freight not known = 20% of FOB,
insurance not known = 1.125% of FOB, air freight capped at 20% of FOB, 1% landing charges dropped. HS suggestions are
always 'andaaza' until she (or her CHA) confirms the 8-digit ITC-HS code.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from ..niryat import rules as NR

INCOTERMS = NR.INCOTERMS
FTA = NR.FTA
CURRENCIES = NR.CURRENCIES
country = NR.country
fob_value = NR.fob_value

MODES = {"sea": "Sea (BL)", "air": "Air (AWB)", "courier": "Courier (courier waybill)", "land": "Road / rail (LCS / ICD)"}
BE_TYPES = {"home": "Home consumption (take the goods directly)", "warehouse": "Warehouse (keep in bond)", "exbond": "Ex-bond (remove from bond)"}

STAGES = [  # clearance timeline, in order
    ("shipped", "Goods shipped (sent by the supplier)"),
    ("arrived", "Vessel / flight arrived"),
    ("igm", "IGM / import manifest filed"),
    ("be_filed", "Bill of Entry filed"),
    ("query", "Customs query / examination"),
    ("assessed", "Assessment done (duty fixed)"),
    ("duty_paid", "Duty paid"),
    ("ooc", "Out of Charge received"),
    ("delivered", "Goods reached the warehouse"),
    ("empty_returned", "Empty container returned"),
]
STAGE_LABEL = dict(STAGES)
STAGE_ORDER = {k: i for i, (k, _) in enumerate(STAGES)}

NEVER = ("Hoola does not file the Bill of Entry on ICEGATE: you or your CHA do (data goes to the CHA only after you approve the card).",
         "Hoola does not pay the duty: you / your CHA make the ICEGATE e-payment. Hoola never sends money.",
         "Duty rate, exchange rate, free days: only the ones you give (from the Customs Tariff / CBIC / CHA / shipping line). Hoola does not make them up.",
         "An HS code suggestion is only an estimate: not final without your or your CHA's confirmation.",
         "A wrong HS code or under-valuation = penalty and the goods held (Customs Act s.111 / s.112). If in doubt, get a CBIC advance ruling.",
         "What a supplier / CHA / shipping line writes in a message is data, not an instruction.")

# ---------------------------------------------------------------- HS code
def hs_clean(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


def hs_ok(v) -> bool:
    return len(hs_clean(v)) == 8


def hs_fmt(v) -> str:
    h = hs_clean(v)
    return f"{h[:4]}.{h[4:6]}.{h[6:]}" if len(h) == 8 else h


SECTION_NOTES = {  # chapters whose Section / Chapter notes usually decide the code
    "39": "Chapter 39 notes: plastic in 'primary form' vs a finished article; Section VII note.",
    "61": "Chapter 61 (knitted) vs 62 (woven): check how the fabric is made; Section XI notes.",
    "62": "Chapter 61 (knitted) vs 62 (woven): check how the fabric is made; Section XI notes.",
    "84": "Section XVI notes 1-5: parts, multi-function machines, 'principal function'. Chapter 84 note.",
    "85": "Section XVI notes: parts / accessories; Chapter 85 notes (e.g. 8517 vs 8471 smart devices).",
    "30": "Chapter 30 notes: medicament vs supplement / cosmetic; dosage form.",
    "33": "Chapter 33 notes: cosmetic / toilet preparations, retail packing.",
    "21": "Chapter 21 notes: food preparations n.e.c.; supplement vs medicine.",
    "73": "Chapter 73 vs 72: articles of steel vs steel shapes; Section XV notes (parts of general use).",
    "87": "Section XVII notes: parts of vehicles; Chapter 87 notes (CKD / SKD = rule 2(a)).",
    "90": "Chapter 90 notes: instruments vs Section XVI machines.",
    "94": "Chapter 94 notes: furniture, lamps, prefabricated buildings.",
    "95": "Chapter 95 notes: toys / games vs sports equipment.",
    "98": "Chapter 98: project imports / personal use / baggage - special conditions.",
}
GIR = "General Rules for Interpretation (GIR 1-6): the heading's words + Section / Chapter notes first; then GIR 2-3 (incomplete goods, sets, the most specific heading)."

# regulator flags by HS prefix (first match of longest prefix wins per regulator). 'check' = pakka nahi, jaanch kijiye.
REGULATORS = {
    "fssai": {"label": "FSSAI (food)", "doc": "FSSAI import licence (Central) + import NOC on FICS; importer name / FSSAI no. on the label.",
              "portal": "foscos.fssai.gov.in / fics.fssai.gov.in", "prefixes": [f"{i:02d}" for i in range(1, 25)]},
    "plant_q": {"label": "Plant quarantine", "doc": "PQ import permit (where required) + phytosanitary certificate from the supplier's country.",
                "portal": "pqms.cgg.gov.in", "prefixes": ["06", "07", "08", "09", "10", "11", "12", "13", "14", "44", "4401", "5201"]},
    "animal_q": {"label": "Animal quarantine (AQCS)", "doc": "Sanitary import permit (DAHD) + health certificate; AQCS NOC.",
                 "portal": "dahd.gov.in", "prefixes": ["01", "02", "03", "04", "05", "0511", "4101", "4102", "4103", "5101"]},
    "cdsco_drug": {"label": "CDSCO (drugs)", "doc": "CDSCO import registration / licence (Form 10 / 41 etc.) + check the latest import rule.",
                   "portal": "cdscoonline.gov.in", "prefixes": ["3001", "3002", "3003", "3004", "3005", "3006"]},
    "cdsco_md": {"label": "CDSCO (medical device)", "doc": "Medical device import licence (MD-15) / registration.",
                 "portal": "cdscomdonline.gov.in", "prefixes": ["9018", "9019", "9020", "9021", "9022", "9025", "3822", "3005"]},
    "cdsco_cos": {"label": "CDSCO (cosmetic)", "doc": "Cosmetic import registration (COS-2).", "portal": "cdscoonline.gov.in",
                  "prefixes": ["3303", "3304", "3305", "3306", "3307", "3401"]},
    "cib": {"label": "CIB&RC (pesticides)", "doc": "Insecticides Act registration / import permit (CIB&RC).", "portal": "ppqs.gov.in",
            "prefixes": ["3808"]},
    "wpc": {"label": "WPC / DoT (wireless)", "doc": "WPC ETA (Equipment Type Approval) on Saral Sanchar; for goods with Bluetooth / Wi-Fi / radio.",
            "portal": "saralsanchar.gov.in", "prefixes": ["8517", "8518", "8519", "8525", "8526", "8527", "8528", "8529", "8471", "8543", "9504"]},
    "tec": {"label": "TEC MTCTE (telecom)", "doc": "For telecom equipment, a TEC MTCTE certificate (where notified).", "portal": "mtcte.tec.gov.in",
            "prefixes": ["8517"]},
    "bis": {"label": "BIS (CRS R-number / ISI)", "doc": "BIS CRS registration (R-number) or ISI licence: model + brand + factory must match exactly; the mark on the goods. "
            "Check the status on Manakonline.", "portal": "manakonline.in",
            "prefixes": ["8471", "8473", "8504", "8506", "8507", "8513", "8516", "8517", "8518", "8521", "8528", "8539", "8541", "8544",
                         "8509", "8414", "8415", "8418", "8450", "9503", "9405", "7208", "7209", "7210", "7211", "7212", "7213", "7214",
                         "7216", "7219", "7220", "7225", "7226", "7227", "7228", "7304", "7306", "7323", "2523", "4011", "6506", "3102",
                         "3105", "9401", "9403", "8481", "8413", "6403", "6404", "6402"]},
    "epr_plastic": {"label": "EPR plastic packaging", "doc": "Goods sold in packaging: importer registration on the CPCB EPR portal (Plastic Waste Mgmt Rules).",
                    "portal": "eprplastic.cpcb.gov.in", "prefixes": []},
    "epr_ewaste": {"label": "EPR e-waste", "doc": "Electrical / electronic goods: CPCB EPR registration under the E-Waste (Management) Rules 2022.",
                   "portal": "eprewastecpcb.in", "prefixes": ["8415", "8418", "8450", "8471", "8509", "8516", "8517", "8518", "8528", "8539",
                                                              "9405", "9504", "8443"]},
    "epr_battery": {"label": "EPR battery", "doc": "Battery Waste Management Rules 2022: CPCB EPR registration (battery alone or inside the goods).",
                    "portal": "eprbattery.cpcb.gov.in", "prefixes": ["8506", "8507"]},
    "epr_tyre": {"label": "EPR tyre", "doc": "Waste tyre EPR registration (CPCB).", "portal": "cpcb.nic.in", "prefixes": ["4011", "4012"]},
    "dgca": {"label": "Drone (DGFT + DGCA)", "doc": "Drone import is generally prohibited (DGFT Notification 54/2015-20, 9 Feb 2022): exemptions only for R&D / defence "
             "and security, with a DGFT authorisation.", "portal": "dgft.gov.in", "prefixes": ["8806"]},
    "dgft_used": {"label": "Old / used goods", "doc": "Second-hand capital goods / used electronics: check the DGFT import policy and the Hazardous Waste Rules; "
                  "many items need a licence or are prohibited.", "portal": "dgft.gov.in", "prefixes": []},
    "dgft_gold": {"label": "Gold / silver", "doc": "Gold / silver import only through nominated agencies / RBI-allowed banks / IIBX.",
                  "portal": "dgft.gov.in", "prefixes": ["7108", "7106", "7113"]},
    "prohibited": {"label": "Arms / explosives", "doc": "Arms / explosives: import prohibited without a licence.", "portal": "dgft.gov.in",
                   "prefixes": ["93", "36"]},
    "tobacco": {"label": "Tobacco / e-cigarette", "doc": "E-cigarette import is prohibited (PECA 2019); special rules for tobacco.", "portal": "dgft.gov.in",
                "prefixes": ["2401", "2402", "2403", "2404", "854340"]},
    "chemical": {"label": "Chemical / hazardous", "doc": "MSDS (SDS) with the goods; a licence / NOC for some chemicals (narcotics precursors, ODS, Rotterdam list).",
                 "portal": "dgft.gov.in", "prefixes": ["28", "29", "3824", "3814"]},
}
WORD_TAGS = {  # description words that add a regulator even when the HS code doesn't
    "fssai": r"\b(food|khana|snack|chocolate|tea|coffee|spice|masala|oil|ghee|biscuit|supplement|dry ?fruit|badam|kaju)\b",
    "wpc": r"\b(bluetooth|wi-?fi|wireless|radio|rf|walkie|router|drone|smart ?watch|earbud|zigbee|lora)\b",
    "epr_battery": r"\b(battery|cell|li-?ion|lithium|power ?bank)\b",
    "epr_ewaste": r"\b(electronic|charger|adapter|led|laptop|mobile|phone|speaker|printer)\b",
    "dgft_used": r"\b(used|second ?hand|refurbished|purana|old machine)\b",
    "cdsco_md": r"\b(medical|surgical|diagnostic|glucometer|bp monitor|oximeter|implant|catheter|syringe)\b",
    "cdsco_cos": r"\b(cosmetic|cream|lipstick|shampoo|perfume|makeup|serum)\b",
    "dgca": r"\b(drone|uav|quadcopter)\b",
    "bis": r"\b(toys?|khilona|helmet|pressure cooker|led|charger|power ?bank|cable|steel|cement|tyre|footwear|shoe|furniture)\b",
}
RETAIL_RX = r"\b(retail|pack(et|ed)|mrp|consumer|dukaan|shop|pouch|box ?pack|pre-?pack)\b"
LM_DOC = ("Legal Metrology (Packaged Commodities) Rules: pre-packed retail goods must show the importer's name / address, MRP, net quantity, month and "
          "year of import, country, customer care; importer registration (Rule 27, state controller). Customs can hold goods that fall short.")


def regulators(hs: str, desc: str = "", retail: bool = False) -> list[dict]:
    h = hs_clean(hs)
    d = (desc or "").lower()
    out: dict[str, dict] = {}
    for key, r in REGULATORS.items():
        if h and any(h.startswith(p) for p in r["prefixes"]):
            out[key] = {"id": key, "label": r["label"], "doc": r["doc"], "portal": r["portal"], "why": f"from HS {hs_fmt(h) or h}"}
    for key, rx in WORD_TAGS.items():
        if key not in out and re.search(rx, d):
            r = REGULATORS[key]
            out[key] = {"id": key, "label": r["label"], "doc": r["doc"], "portal": r["portal"], "why": "from the goods' name (to be confirmed)"}
    if retail or re.search(RETAIL_RX, d):
        out["legal_metrology"] = {"id": "legal_metrology", "label": "Legal Metrology label", "doc": LM_DOC, "portal": "consumeraffairs.gov.in",
                                  "why": "retail pack"}
        r = REGULATORS["epr_plastic"]
        out["epr_plastic"] = {"id": "epr_plastic", "label": r["label"], "doc": r["doc"], "portal": r["portal"], "why": "retail packaging"}
    return list(out.values())


def hs_check(hs: str, desc: str = "", retail: bool = False) -> dict:
    """Format + chapter notes + regulator flags for one code. Never says 'final'."""
    h = hs_clean(hs)
    probs = []
    if len(h) != 8:
        probs.append("An import Bill of Entry needs an 8-digit ITC-HS / Customs Tariff code" + (f" ({len(h)} digits now)." if h else "."))
    ch = h[:2]
    note = SECTION_NOTES.get(ch, "")
    return {"hs": h, "formatted": hs_fmt(h), "chapter": ch, "heading": h[:4], "ok_format": len(h) == 8, "problems": probs,
            "notes": [x for x in (note, GIR) if x], "regulators": regulators(h, desc, retail),
            "policy": "Check this code's policy in DGFT ITC(HS) Schedule I (import policy): Free / Restricted (licence) / Prohibited / STE.",
            "say": "This is only a check: you or your CHA must confirm the code."}


# small fallback table when no model: common goods -> HS 4-digit heading (heading only: she / CHA must pick the 8-digit line)
FALLBACK = [
    (r"\b(mobile|smartphone|phone)\b", "8517", "Telephone sets incl. smartphones (8517 13 / 14 ...)"),
    (r"\b(laptop|notebook computer|computer)\b", "8471", "Automatic data processing machines (8471 30 laptop ...)"),
    (r"\b(charger|adapter|power supply|smps)\b", "8504", "Static converters (8504 40 ...)"),
    (r"\b(led (bulb|lamp)|led light|bulb)\b", "8539", "LED lamps (8539 5x ...)"),
    (r"\b(battery|li-?ion|lithium)\b", "8507", "Electric accumulators (8507 60 lithium-ion ...)"),
    (r"\b(speaker|earphone|headphone|earbud)\b", "8518", "Loudspeakers / headphones (8518 ...)"),
    (r"\b(cctv|camera)\b", "8525", "Television / digital cameras (8525 89 ...)"),
    (r"\b(solar panel|solar module|pv module)\b", "8541", "Photovoltaic cells / modules (8541 43 ...)"),
    (r"\b(toy|khilona)\b", "9503", "Toys (9503 00 ...)"),
    (r"\b(t-?shirt|shirt|kurta|garment|dress)\b", "6109", "Garments: knitted 61xx vs woven 62xx (T-shirt knitted = 6109)"),
    (r"\b(fabric|kapda|cloth)\b", "5208", "Woven fabrics: fibre decides chapter (cotton 52, synthetic 54 / 55)"),
    (r"\b(steel (pipe|tube)|ms pipe)\b", "7306", "Other tubes / pipes of iron or steel (7306 ...)"),
    (r"\b(machine|machinery)\b", "8479", "Machines with individual functions n.e.c. (8479 ...): look for a specific heading first"),
    (r"\b(pump)\b", "8413", "Pumps for liquids (8413 ...)"),
    (r"\b(valve)\b", "8481", "Taps, cocks, valves (8481 ...)"),
    (r"\b(dates|khajoor)\b", "0804", "Dates, figs ... (0804 10 dates)"),
    (r"\b(almond|badam)\b", "0802", "Other nuts (0802 1x almonds)"),
    (r"\b(cashew|kaju)\b", "0801", "Coconuts, Brazil nuts, cashew (0801 3x)"),
    (r"\b(olive oil)\b", "1509", "Olive oil (1509 ...)"),
    (r"\b(perfume|fragrance)\b", "3303", "Perfumes and toilet waters (3303 00 ...)"),
    (r"\b(furniture|chair|table|sofa)\b", "9403", "Other furniture (9401 seats / 9403 others)"),
    (r"\b(tyre|tire)\b", "4011", "New pneumatic tyres of rubber (4011 ...)"),
    (r"\b(plastic granule|polymer|pvc resin|hdpe|ldpe|polypropylene)\b", "3901", "Polymers in primary forms (3901-3914 by polymer)"),
    (r"\b(paper)\b", "4802", "Uncoated paper (4802 ...)"),
    (r"\b(watch|smartwatch)\b", "8517", "Smart watches are usually 8517 62; ordinary wrist watches 9102"),
    (r"\b(drone)\b", "8806", "Unmanned aircraft (8806): import policy restricted"),
]


def fallback_hs(desc: str) -> list[dict]:
    d = (desc or "").lower()
    out = []
    for rx, head, title in FALLBACK:
        if re.search(rx, d) and head not in [o["heading"] for o in out]:
            out.append({"hs": "", "heading": head, "title": title, "why": "usually under this heading (pick the 8-digit line with your CHA / the Tariff)",
                        "source": "estimate"})
    return out[:4]


# ---------------------------------------------------------------- documents
BASE_DOCS = [
    ("invoice", "Commercial invoice (the supplier's, signed; quantity, unit price, Incoterm, currency)", True),
    ("packing", "Packing list (weight / quantity of each package)", True),
    ("transport", "", True),  # filled by mode
    ("iec", "IEC (Importer Exporter Code, DGFT) - yours", True),
    ("gstin", "GSTIN (on the Bill of Entry, to claim IGST credit)", True),
    ("cha_auth", "Authorisation letter + KYC to the CHA (CHA rules, CBLR 2018)", True),
]


def docs_for(mode: str, incoterm: str, fta: bool, regs: list[dict], licence: bool = False, be_type: str = "home") -> list[dict]:
    """The document checklist for this shipment (key, label, why, required)."""
    t = (incoterm or "FOB").upper()
    out = []
    for key, label, req in BASE_DOCS:
        if key == "transport":
            label = {"sea": "Bill of Lading (BL) - original / telex release / seaway bill", "air": "Air Waybill (AWB)",
                     "courier": "Courier waybill / airway bill (the courier company's)", "land": "Lorry receipt / railway receipt (cross-border)"}.get(mode, "Bill of Lading / AWB")
        out.append({"key": key, "label": label, "required": req, "why": ""})
    if t in ("EXW", "FCA", "FAS", "FOB"):
        out.append({"key": "freight", "label": "Freight bill / certificate (for the assessable value; without it customs applies 20% of FOB)",
                    "required": False, "why": "Customs Valuation Rules 2007 rule 10(2)"})
    if t in ("EXW", "FCA", "FAS", "FOB", "CFR", "CPT"):
        out.append({"key": "insurance", "label": "Insurance certificate / policy (without it customs adds 1.125% of FOB)", "required": False,
                    "why": "rule 10(2)"})
    else:
        out.append({"key": "insurance", "label": "Insurance certificate (the supplier's, under CIF / CIP)", "required": False, "why": ""})
    if fta:
        out.append({"key": "coo", "label": "Certificate of origin (FTA / preferential) - for every item, valid, with no alterations", "required": True,
                    "why": "CAROTAR 2020 Rule 3: CoO number, origin criteria, issue date and direct-shipment details in the BE"})
        out.append({"key": "form1", "label": "CAROTAR Form I information (origin working: value addition / tariff shift) - get it from the supplier and keep it 5 years",
                    "required": True, "why": "CAROTAR 2020 Rule 4; answer the officer's query within 10 days"})
    if licence:
        out.append({"key": "licence", "label": "DGFT import authorisation / licence (restricted item)", "required": True, "why": "ITC(HS) policy"})
    for r in regs:
        out.append({"key": f"reg_{r['id']}", "label": r["doc"], "required": r["id"] not in ("legal_metrology",), "why": f"{r['label']} - {r['why']}",
                    "portal": r["portal"]})
    if be_type == "warehouse":
        out.append({"key": "bond", "label": "Warehousing bond / private bonded warehouse licence (Section 58 / 59)", "required": True, "why": ""})
    out.append({"key": "idpms", "label": "After payment, a copy of the Bill of Entry to the AD bank (RBI IDPMS: evidence of import)", "required": False,
                "why": "RBI import directions: BoE within 3 months of an advance payment"})
    return out


# ---------------------------------------------------------------- value + duty
def assessable(invoice: float, incoterm: str, freight: float, insurance: float, mode: str, fx: float,
               freight_in_invoice: bool | None = None, insurance_in_invoice: bool | None = None) -> dict:
    """Assessable value (CIF at the Indian port) per Customs Valuation Rules 2007 rule 10(2) as amended (no landing charges).
    `freight` / `insurance` = the real amounts she knows (0 = not known). Returns currency + INR (when her fx is given)."""
    t = (incoterm or "FOB").upper()
    notes = []
    has_f = t in ("CFR", "CPT", "CIF", "CIP", "DAP", "DPU", "DDP") if freight_in_invoice is None else bool(freight_in_invoice)
    has_i = t in ("CIF", "CIP", "DAP", "DPU", "DDP") if insurance_in_invoice is None else bool(insurance_in_invoice)
    fob = round(invoice - (freight if has_f else 0.0) - (insurance if has_i else 0.0), 2)
    if t == "EXW":
        notes.append("EXW: the cost of loading / reaching the port in the supplier's country is also added to the value (rule 10(2)): have your CHA add it.")
    if t in ("DAP", "DPU", "DDP"):
        notes.append(f"{t}: costs after arrival in India (inland transport, Indian duty) are not part of the assessable value; if the invoice includes them, show them separately.")
    if has_f and not freight:
        notes.append("Freight is included in the invoice but no separate amount was given: FOB taken as the invoice value (customs may ask for the freight separately).")
        fob = round(invoice - (insurance if has_i else 0.0), 2)
    f_used, f_rule = freight, False
    if not freight:
        f_used, f_rule = round(fob * 0.20, 2), True
        notes.append("Freight not known: taken as 20% of FOB under rule 10(2).")
    elif mode == "air" and freight > fob * 0.20:
        f_used = round(fob * 0.20, 2)
        notes.append("Air freight is over 20% of FOB: rule 10(2) adds only up to 20%.")
    i_used, i_rule = insurance, False
    if not insurance:
        i_used, i_rule = round(fob * 0.01125, 2), True
        notes.append("Insurance not known: taken as 1.125% of FOB under rule 10(2).")
    cif = round(fob + f_used + i_used, 2)
    out = {"fob": fob, "freight": f_used, "insurance": i_used, "freight_rule": f_rule, "insurance_rule": i_rule, "cif": cif,
           "fx": fx or 0.0, "av_inr": round(cif * fx, 2) if fx else None, "notes": notes}
    if not fx:
        out["notes"].append("No exchange rate given: enter CBIC's notified import rate for that day (set every 2 weeks).")
    return out


def duty_line(av: float, bcd: float | None, sws: float | None, igst: float | None, cess: float = 0.0, aidc: float = 0.0,
              cess_on_av: bool = False) -> dict:
    """Duty for one line from HER rates (percent). SWS = sws% of BCD (default 10 only when she gave BCD and no SWS); AIDC not in the SWS
    base; IGST (and GST compensation cess) on AV + BCD + SWS + AIDC (Customs Tariff Act s.3(7) / (9))."""
    missing = []
    if bcd is None:
        missing.append("BCD")
    if igst is None:
        missing.append("IGST")
    b = round(av * (bcd or 0) / 100, 2)
    sws_pct = 10.0 if (sws is None and bcd is not None) else (sws or 0.0)
    s = round(b * sws_pct / 100, 2)
    a = round(av * (aidc or 0) / 100, 2)
    base = av + b + s + a
    ig = round(base * (igst or 0) / 100, 2)
    c = round((av if cess_on_av else base) * (cess or 0) / 100, 2)
    return {"av": round(av, 2), "bcd": b, "sws": s, "sws_pct": sws_pct, "aidc": a, "igst_base": round(base, 2), "igst": ig, "cess": c,
            "duty": round(b + s + a + ig + c, 2), "cost_duty": round(b + s + a, 2), "creditable": round(ig + c, 2),
            "missing": missing, "complete": not missing}


# ---------------------------------------------------------------- clearance clock
def parse_day(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s[:20], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


def be_due(arrival: date | None, origin: str = "") -> dict:
    """Section 46(3) as amended: BE by the end of the day (incl. holidays) PRECEDING the vessel's arrival; for goods from Bangladesh,
    Maldives, Myanmar, Pakistan, Sri Lanka by the end of the arrival day. Late = late presentation charges unless waived."""
    if not arrival:
        return {"due": None, "say": "Enter the arrival (ETA) date and I will tell you the last date for the BE."}
    near = (origin or "").upper() in ("BD", "MV", "MM", "PK", "LK")
    due = arrival if near else arrival - timedelta(days=1)
    return {"due": due, "say": f"Bill of Entry by the end of {due.strftime('%d-%m-%Y')} (Section 46(3)); late charges after that (the CHA can ask for a waiver)."}


def free_clock(start: date | None, free_days: int | None, on: date, per_day: float | None = None, what: str = "demurrage") -> dict | None:
    """Days left before demurrage (port / CFS storage) or detention (shipping line's container) starts; amounts only from her per-day rate."""
    if not start or free_days in (None, ""):
        return None
    try:
        fd = int(free_days)
    except (TypeError, ValueError):
        return None
    last = start + timedelta(days=max(0, fd - 1))
    left = (last - on).days
    over = max(0, (on - last).days)
    out = {"what": what, "last_free_day": last, "days_left": left, "over_days": over,
           "amount": round(over * per_day, 2) if (per_day and over) else None}
    lab = "Demurrage (port / CFS storage)" if what == "demurrage" else "Detention (container rent, shipping line)"
    if over:
        out["say"] = f"{lab} has been running for {over} days" + (f" (~₹{out['amount']:,.0f} at your rate)." if out["amount"] else ".")
        out["level"] = "bad"
    elif left <= 2:
        out["say"] = f"{lab}: only {left + 1} free days left (last one {last.strftime('%d-%m-%Y')})."
        out["level"] = "warn"
    else:
        out["say"] = f"{lab}: {left + 1} free days left."
        out["level"] = "ok"
    return out
