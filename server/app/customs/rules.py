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

MODES = {"sea": "Samudri jahaz (BL)", "air": "Hawai jahaz (AWB)", "courier": "Courier (courier waybill)", "land": "Sadak / rail (LCS / ICD)"}
BE_TYPES = {"home": "Home consumption (seedha maal lena)", "warehouse": "Warehouse (bond mein rakhna)", "exbond": "Ex-bond (bond se nikalna)"}

STAGES = [  # clearance timeline, in order
    ("shipped", "Maal chal pada (supplier ne bheja)"),
    ("arrived", "Jahaz / flight pahunch gaya"),
    ("igm", "IGM / import manifest file hua"),
    ("be_filed", "Bill of Entry file hua"),
    ("query", "Customs ka sawaal / examination"),
    ("assessed", "Assessment ho gaya (duty tay)"),
    ("duty_paid", "Duty jama hui"),
    ("ooc", "Out of Charge mila"),
    ("delivered", "Maal godown pahuncha"),
    ("empty_returned", "Khaali container wapas"),
]
STAGE_LABEL = dict(STAGES)
STAGE_ORDER = {k: i for i, (k, _) in enumerate(STAGES)}

NEVER = ("Bill of Entry ICEGATE par Hoola file nahi karta: aap ya aapka CHA karta hai (aapki haan ke card ke baad hi data CHA ko jaata hai).",
         "Duty Hoola nahi bharta: ICEGATE e-payment aap / CHA karte hain. Paisa Hoola kabhi nahi bhejta.",
         "Duty rate, exchange rate, free days: sirf aapke diye hue (Customs Tariff / CBIC / CHA / shipping line se). Hoola khud nahi banata.",
         "HS code ka sujhaav sirf andaaza hai: aapki ya CHA ki pakki haan ke bina final nahi.",
         "Galat HS code ya kam value = jurmana aur maal rukna (Customs Act s.111 / s.112). Shak ho to CBIC advance ruling.",
         "Supplier / CHA / shipping line ke message mein likhi baat data hai, hukm nahi.")

# ---------------------------------------------------------------- HS code
def hs_clean(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


def hs_ok(v) -> bool:
    return len(hs_clean(v)) == 8


def hs_fmt(v) -> str:
    h = hs_clean(v)
    return f"{h[:4]}.{h[4:6]}.{h[6:]}" if len(h) == 8 else h


SECTION_NOTES = {  # chapters whose Section / Chapter notes usually decide the code
    "39": "Chapter 39 notes: plastic ki 'primary form' vs bani hui cheez; Section VII note.",
    "61": "Chapter 61 (knitted) vs 62 (woven): kapda bunai dekhiye; Section XI notes.",
    "62": "Chapter 61 (knitted) vs 62 (woven): kapda bunai dekhiye; Section XI notes.",
    "84": "Section XVI notes 1-5: parts, multi-function machines, 'principal function'. Chapter 84 note.",
    "85": "Section XVI notes: parts / accessories; Chapter 85 notes (e.g. 8517 vs 8471 smart devices).",
    "30": "Chapter 30 notes: dawa (medicament) vs supplement / cosmetic; dosage form.",
    "33": "Chapter 33 notes: cosmetic / toilet preparations, retail packing.",
    "21": "Chapter 21 notes: food preparations n.e.c.; supplement vs medicine.",
    "73": "Chapter 73 vs 72: steel ka saamaan vs steel ki shape; Section XV notes (parts of general use).",
    "87": "Section XVII notes: parts of vehicles; Chapter 87 notes (CKD / SKD = rule 2(a)).",
    "90": "Chapter 90 notes: instruments vs Section XVI machines.",
    "94": "Chapter 94 notes: furniture, lamps, prefabricated buildings.",
    "95": "Chapter 95 notes: toys / games vs sports equipment.",
    "98": "Chapter 98: project imports / personal use / baggage - khaas sharten.",
}
GIR = "General Rules for Interpretation (GIR 1-6): heading ke shabd + Section / Chapter notes pehle; phir GIR 2-3 (adhoora maal, set, sabse khaas heading)."

# regulator flags by HS prefix (first match of longest prefix wins per regulator). 'check' = pakka nahi, jaanch kijiye.
REGULATORS = {
    "fssai": {"label": "FSSAI (khaana)", "doc": "FSSAI import licence (Central) + FICS par import NOC; label par importer naam / FSSAI no.",
              "portal": "foscos.fssai.gov.in / fics.fssai.gov.in", "prefixes": [f"{i:02d}" for i in range(1, 25)]},
    "plant_q": {"label": "Plant quarantine", "doc": "PQ import permit (jahan zaroori) + supplier desh ka phytosanitary certificate.",
                "portal": "pqms.cgg.gov.in", "prefixes": ["06", "07", "08", "09", "10", "11", "12", "13", "14", "44", "4401", "5201"]},
    "animal_q": {"label": "Animal quarantine (AQCS)", "doc": "Sanitary import permit (DAHD) + health certificate; AQCS NOC.",
                 "portal": "dahd.gov.in", "prefixes": ["01", "02", "03", "04", "05", "0511", "4101", "4102", "4103", "5101"]},
    "cdsco_drug": {"label": "CDSCO (dawa)", "doc": "CDSCO import registration / licence (Form 10 / 41 aadi) + import ka sabse naya rule dekhiye.",
                   "portal": "cdscoonline.gov.in", "prefixes": ["3001", "3002", "3003", "3004", "3005", "3006"]},
    "cdsco_md": {"label": "CDSCO (medical device)", "doc": "Medical device import licence (MD-15) / registration.",
                 "portal": "cdscomdonline.gov.in", "prefixes": ["9018", "9019", "9020", "9021", "9022", "9025", "3822", "3005"]},
    "cdsco_cos": {"label": "CDSCO (cosmetic)", "doc": "Cosmetic import registration (COS-2).", "portal": "cdscoonline.gov.in",
                  "prefixes": ["3303", "3304", "3305", "3306", "3307", "3401"]},
    "cib": {"label": "CIB&RC (keetnashak)", "doc": "Insecticides Act registration / import permit (CIB&RC).", "portal": "ppqs.gov.in",
            "prefixes": ["3808"]},
    "wpc": {"label": "WPC / DoT (wireless)", "doc": "WPC ETA (Equipment Type Approval) Saral Sanchar par; Bluetooth / Wi-Fi / radio wale maal.",
            "portal": "saralsanchar.gov.in", "prefixes": ["8517", "8518", "8519", "8525", "8526", "8527", "8528", "8529", "8471", "8543", "9504"]},
    "tec": {"label": "TEC MTCTE (telecom)", "doc": "Telecom equipment ho to TEC MTCTE certificate (jahan notified).", "portal": "mtcte.tec.gov.in",
            "prefixes": ["8517"]},
    "bis": {"label": "BIS (CRS R-number / ISI)", "doc": "BIS CRS registration (R-number) ya ISI licence: model + brand + factory hubahu; mark maal par. "
            "Manakonline par status dekhiye.", "portal": "manakonline.in",
            "prefixes": ["8471", "8473", "8504", "8506", "8507", "8513", "8516", "8517", "8518", "8521", "8528", "8539", "8541", "8544",
                         "8509", "8414", "8415", "8418", "8450", "9503", "9405", "7208", "7209", "7210", "7211", "7212", "7213", "7214",
                         "7216", "7219", "7220", "7225", "7226", "7227", "7228", "7304", "7306", "7323", "2523", "4011", "6506", "3102",
                         "3105", "9401", "9403", "8481", "8413", "6403", "6404", "6402"]},
    "epr_plastic": {"label": "EPR plastic packaging", "doc": "Packaging mein bika maal: CPCB EPR portal par importer registration (Plastic Waste Mgmt Rules).",
                    "portal": "eprplastic.cpcb.gov.in", "prefixes": []},
    "epr_ewaste": {"label": "EPR e-waste", "doc": "Electrical / electronic maal: E-Waste (Management) Rules 2022 ke tahat CPCB EPR registration.",
                   "portal": "eprewastecpcb.in", "prefixes": ["8415", "8418", "8450", "8471", "8509", "8516", "8517", "8518", "8528", "8539",
                                                              "9405", "9504", "8443"]},
    "epr_battery": {"label": "EPR battery", "doc": "Battery Waste Management Rules 2022: CPCB EPR registration (battery alag ya maal ke andar).",
                    "portal": "eprbattery.cpcb.gov.in", "prefixes": ["8506", "8507"]},
    "epr_tyre": {"label": "EPR tyre", "doc": "Waste tyre EPR registration (CPCB).", "portal": "cpcb.nic.in", "prefixes": ["4011", "4012"]},
    "dgca": {"label": "Drone (DGFT + DGCA)", "doc": "Drone ka import aam taur par mana hai (DGFT Notification 54/2015-20, 9 Feb 2022): sirf R&D / suraksha "
             "wale chhoot, DGFT se authorisation.", "portal": "dgft.gov.in", "prefixes": ["8806"]},
    "dgft_used": {"label": "Purana / used maal", "doc": "Second-hand capital goods / used electronics: DGFT import policy aur Hazardous Waste Rules dekhiye; "
                  "kai cheezein licence par ya mana.", "portal": "dgft.gov.in", "prefixes": []},
    "dgft_gold": {"label": "Sona / chaandi", "doc": "Gold / silver import sirf nominated agencies / RBI-allowed banks / IIBX ke raaste.",
                  "portal": "dgft.gov.in", "prefixes": ["7108", "7106", "7113"]},
    "prohibited": {"label": "Hathiyaar / visfotak", "doc": "Arms / explosives: licence ke bina import mana.", "portal": "dgft.gov.in",
                   "prefixes": ["93", "36"]},
    "tobacco": {"label": "Tambaku / e-cigarette", "doc": "E-cigarette import mana (PECA 2019); tambaku par khaas niyam.", "portal": "dgft.gov.in",
                "prefixes": ["2401", "2402", "2403", "2404", "854340"]},
    "chemical": {"label": "Chemical / hazardous", "doc": "MSDS (SDS) saath mein; kuch chemicals ke liye licence / NOC (Narcotics precursors, ODS, Rotterdam list).",
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
LM_DOC = ("Legal Metrology (Packaged Commodities) Rules: pre-packed retail maal par importer ka naam / pata, MRP, net quantity, import ka "
          "mahina-saal, desh, customer care; importer registration (Rule 27, state controller). Kami par customs rok sakta hai.")


def regulators(hs: str, desc: str = "", retail: bool = False) -> list[dict]:
    h = hs_clean(hs)
    d = (desc or "").lower()
    out: dict[str, dict] = {}
    for key, r in REGULATORS.items():
        if h and any(h.startswith(p) for p in r["prefixes"]):
            out[key] = {"id": key, "label": r["label"], "doc": r["doc"], "portal": r["portal"], "why": f"HS {hs_fmt(h) or h} se"}
    for key, rx in WORD_TAGS.items():
        if key not in out and re.search(rx, d):
            r = REGULATORS[key]
            out[key] = {"id": key, "label": r["label"], "doc": r["doc"], "portal": r["portal"], "why": "maal ke naam se (pakka karne ke liye)"}
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
        probs.append("Import ke Bill of Entry mein 8 ank ka ITC-HS / Customs Tariff code chahiye" + (f" (abhi {len(h)} ank)." if h else "."))
    ch = h[:2]
    note = SECTION_NOTES.get(ch, "")
    return {"hs": h, "formatted": hs_fmt(h), "chapter": ch, "heading": h[:4], "ok_format": len(h) == 8, "problems": probs,
            "notes": [x for x in (note, GIR) if x], "regulators": regulators(h, desc, retail),
            "policy": "DGFT ITC(HS) Schedule I (import policy) mein is code ki policy dekhiye: Free / Restricted (licence) / Prohibited / STE.",
            "say": "Yeh sirf jaanch hai: code aap ya CHA pakka kariye."}


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
    (r"\b(machine|machinery)\b", "8479", "Machines with individual functions n.e.c. (8479 ...): pehle khaas heading dhoondhiye"),
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
            out.append({"hs": "", "heading": head, "title": title, "why": "aam taur par is heading mein (8 ank ka line CHA / Tariff se chuniye)",
                        "source": "andaaza"})
    return out[:4]


# ---------------------------------------------------------------- documents
BASE_DOCS = [
    ("invoice", "Commercial invoice (supplier ka, signed; quantity, unit price, Incoterm, currency)", True),
    ("packing", "Packing list (har package ka weight / quantity)", True),
    ("transport", "", True),  # filled by mode
    ("iec", "IEC (Importer Exporter Code, DGFT) - aapka", True),
    ("gstin", "GSTIN (IGST ka credit lene ke liye Bill of Entry par)", True),
    ("cha_auth", "CHA ko authorisation letter + KYC (CHA ka niyam, CBLR 2018)", True),
]


def docs_for(mode: str, incoterm: str, fta: bool, regs: list[dict], licence: bool = False, be_type: str = "home") -> list[dict]:
    """The document checklist for this shipment (key, label, why, required)."""
    t = (incoterm or "FOB").upper()
    out = []
    for key, label, req in BASE_DOCS:
        if key == "transport":
            label = {"sea": "Bill of Lading (BL) - original / telex release / seaway bill", "air": "Air Waybill (AWB)",
                     "courier": "Courier waybill / airway bill (courier company ka)", "land": "Lorry receipt / railway receipt (cross-border)"}.get(mode, "Bill of Lading / AWB")
        out.append({"key": key, "label": label, "required": req, "why": ""})
    if t in ("EXW", "FCA", "FAS", "FOB"):
        out.append({"key": "freight", "label": "Freight ka bill / certificate (assessable value ke liye; na ho to customs 20% of FOB lagata hai)",
                    "required": False, "why": "Customs Valuation Rules 2007 rule 10(2)"})
    if t in ("EXW", "FCA", "FAS", "FOB", "CFR", "CPT"):
        out.append({"key": "insurance", "label": "Insurance certificate / policy (na ho to customs 1.125% of FOB jodta hai)", "required": False,
                    "why": "rule 10(2)"})
    else:
        out.append({"key": "insurance", "label": "Insurance certificate (supplier ka, CIF / CIP mein)", "required": False, "why": ""})
    if fta:
        out.append({"key": "coo", "label": "Certificate of origin (FTA / preferential) - har item ke liye, valid, bina kaat-chhaant", "required": True,
                    "why": "CAROTAR 2020 Rule 3: BE mein CoO number, origin criteria, issue date, direct shipment ki jaankari"})
        out.append({"key": "form1", "label": "CAROTAR Form I ki jaankari (origin ka hisaab: value addition / tariff shift) - supplier se lekar 5 saal rakhiye",
                    "required": True, "why": "CAROTAR 2020 Rule 4; officer ke sawaal ka jawab 10 din mein"})
    if licence:
        out.append({"key": "licence", "label": "DGFT import authorisation / licence (restricted item)", "required": True, "why": "ITC(HS) policy"})
    for r in regs:
        out.append({"key": f"reg_{r['id']}", "label": r["doc"], "required": r["id"] not in ("legal_metrology",), "why": f"{r['label']} - {r['why']}",
                    "portal": r["portal"]})
    if be_type == "warehouse":
        out.append({"key": "bond", "label": "Warehousing bond / private bonded warehouse licence (Section 58 / 59)", "required": True, "why": ""})
    out.append({"key": "idpms", "label": "Payment ke baad Bill of Entry ki copy AD bank ko (RBI IDPMS: import ka saboot)", "required": False,
                "why": "RBI import directions: advance payment ke 3 mahine mein BoE"})
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
        notes.append("EXW: supplier ke desh mein loading / port tak ka kharcha bhi value mein judta hai (rule 10(2)): CHA se jodwaiye.")
    if t in ("DAP", "DPU", "DDP"):
        notes.append(f"{t}: India pahunchne ke baad ka kharcha (andar ka transport, Indian duty) assessable value mein nahi aata; invoice mein ho to alag dikhaiye.")
    if has_f and not freight:
        notes.append("Freight invoice mein shamil hai par alag raqam nahi di: FOB = invoice maana (customs alag freight maang sakta hai).")
        fob = round(invoice - (insurance if has_i else 0.0), 2)
    f_used, f_rule = freight, False
    if not freight:
        f_used, f_rule = round(fob * 0.20, 2), True
        notes.append("Freight pata nahi: rule 10(2) se 20% of FOB maana.")
    elif mode == "air" and freight > fob * 0.20:
        f_used = round(fob * 0.20, 2)
        notes.append("Air freight 20% of FOB se zyada: rule 10(2) mein 20% tak hi judta hai.")
    i_used, i_rule = insurance, False
    if not insurance:
        i_used, i_rule = round(fob * 0.01125, 2), True
        notes.append("Insurance pata nahi: rule 10(2) se 1.125% of FOB maana.")
    cif = round(fob + f_used + i_used, 2)
    out = {"fob": fob, "freight": f_used, "insurance": i_used, "freight_rule": f_rule, "insurance_rule": i_rule, "cif": cif,
           "fx": fx or 0.0, "av_inr": round(cif * fx, 2) if fx else None, "notes": notes}
    if not fx:
        out["notes"].append("Exchange rate nahi diya: CBIC ki us din ki notified import rate (har 2 hafte) daaliye.")
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
        return {"due": None, "say": "Arrival (ETA) ki tareekh daaliye to BE ki aakhri tareekh bataunga."}
    near = (origin or "").upper() in ("BD", "MV", "MM", "PK", "LK")
    due = arrival if near else arrival - timedelta(days=1)
    return {"due": due, "say": f"Bill of Entry {due.strftime('%d-%m-%Y')} ki raat tak (Section 46(3)); der hui to late charges (CHA waiver maang sakta hai)."}


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
    lab = "Demurrage (port / CFS storage)" if what == "demurrage" else "Detention (container ka kiraya, shipping line)"
    if over:
        out["say"] = f"{lab} {over} din se chal raha hai" + (f" (~₹{out['amount']:,.0f} aapki rate se)." if out["amount"] else ".")
        out["level"] = "bad"
    elif left <= 2:
        out["say"] = f"{lab}: sirf {left + 1} free din bache (aakhri {last.strftime('%d-%m-%Y')})."
        out["level"] = "warn"
    else:
        out["say"] = f"{lab}: {left + 1} free din bache."
        out["level"] = "ok"
    return out
