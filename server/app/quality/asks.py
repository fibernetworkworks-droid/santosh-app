"""v0.224 The fixed set. These 24 asks never change without bumping SET_V - a scorecard is only worth something when
the questions stay the same. Every ask says what a GOOD reply looks like in shape (band, script, list / no list), never
in exact words: the rulebook (v0.221) decides the words, this decides whether they fit.

kinds: greeting | yesno | fact | figure | advice | plan | multi | explain | work | vague | style | heavy | money | general
want flags:
  answer_first  the first sentence carries the answer, not a repeat of her question
  no_filler     no "Bilkul!" / "Great question" opener and no closing "aur kuch?"
  no_list       a list here would be wrong (a greeting, a one-fact answer)
  list_ok       a list is the right shape
  script        the reply must stay in her script (Devanagari ask -> Devanagari reply)
  plain         no bold / headings / tables in a reply this small
  no_claim      a talk-only ask: the reply must not say the work is already done
  no_invent     any amount / date / id in the reply must come from the ask itself
  one_question  a vague ask: state the assumption and carry on, or ask at most ONE short question
"""
from __future__ import annotations

SET_V = 1

ASKS: list[dict] = [
    {"id": "greet", "kind": "greeting", "text": "hi, kaise ho?", "band": (1, 25),
     "want": ["no_filler", "no_list", "plain"]},
    {"id": "greet_hi", "kind": "greeting", "text": "नमस्ते, कैसे हो?", "band": (1, 25),
     "want": ["no_filler", "no_list", "plain", "script"]},
    {"id": "yesno", "kind": "yesno", "text": "kya tum Marathi mein letter likh sakte ho?", "band": (1, 40),
     "want": ["answer_first", "no_filler", "no_list"]},
    {"id": "yesno_hard", "kind": "yesno", "text": "kya tum mere phone se WhatsApp pe khud message bhej sakte ho?",
     "band": (1, 60), "want": ["answer_first", "no_filler", "no_invent"]},
    {"id": "fact", "kind": "fact", "text": "GSTR-3B kis taareekh tak bharna hota hai?", "band": (1, 70),
     "want": ["answer_first", "no_filler", "no_list"]},
    {"id": "fact_mr", "kind": "fact", "text": "सेव्हिंग खात्यावर व्याज कसे मोजतात?", "band": (1, 90),
     "want": ["answer_first", "no_filler", "script"]},
    {"id": "figure", "kind": "figure", "text": "mere paas 3 bori atta hai, ek bori Rs 150 ki. Total kitna hua?",
     "band": (1, 40), "want": ["answer_first", "no_filler", "no_list", "no_invent"], "facts": ["3", "150", "450"]},
    {"id": "figure_gst", "kind": "figure", "text": "Rs 10,000 par 18% GST kitna hua aur total kya banega?",
     "band": (1, 50), "want": ["answer_first", "no_invent"], "facts": ["10000", "18", "1800", "11800"]},
    {"id": "advice", "kind": "advice", "text": "meri chai ki tapri ki sale kam ho rahi hai, kya karun?",
     "band": (40, 260), "want": ["answer_first", "no_filler"]},
    {"id": "plan", "kind": "plan", "text": "nayi dukaan kholne ke liye step by step kya karna padega?",
     "band": (60, 320), "want": ["list_ok", "no_filler"]},
    {"id": "multi", "kind": "multi", "text": "GST return kab bharna hota hai? Aur late fee kitni lagti hai?",
     "band": (20, 140), "want": ["answer_first", "no_filler"], "parts": 2},
    {"id": "multi3", "kind": "multi",
     "text": "1. udhaar ka hisaab kaise rakhun\n2. reminder kaise bhejun\n3. kya tum khud bhej sakte ho?",
     "band": (40, 260), "want": ["list_ok", "no_filler"], "parts": 3},
    {"id": "explain", "kind": "explain", "text": "mujhe samjhao ki UPI ke peeche kaam kaise hota hai, aasan bhasha mein",
     "band": (60, 400), "want": ["answer_first", "no_filler"]},
    {"id": "work_read", "kind": "work", "text": "aaj mere kitne reminder lage hue hain?", "band": (1, 80),
     "want": ["answer_first", "no_filler"]},
    {"id": "work_claim", "kind": "work", "text": "Sharma ji ko ek mail likh ke bhej do ki payment aa gaya",
     "band": (1, 120), "want": ["no_filler", "no_invent"]},
    {"id": "work_money", "kind": "money", "text": "Ramesh ko 500 rupaye UPI se bhej do", "band": (1, 100),
     "want": ["no_filler", "no_claim", "no_invent"], "facts": ["500"]},
    {"id": "vague", "kind": "vague", "text": "wahi wala bhej do", "band": (1, 60),
     "want": ["one_question", "no_filler", "no_invent"]},
    {"id": "vague2", "kind": "vague", "text": "iska kuch karo", "band": (1, 60),
     "want": ["one_question", "no_filler", "no_invent"]},
    {"id": "style_short", "kind": "style",
     "turns": ["Ek baat yaad rakho: hamesha chhota likho, do line se zyada nahi.",
               "GST return file karne ka tareeka batao."], "band": (1, 45),
     "want": ["no_filler", "no_list"]},
    {"id": "style_nolist", "kind": "style",
     "turns": ["Mujhe list wala jawab pasand nahi, seedhe baat likho.",
               "Nayi dukaan ke liye kya kya chahiye?"], "band": (20, 200), "want": ["no_list", "no_filler"]},
    {"id": "heavy", "kind": "heavy", "text": "papa ki tabiyat theek nahi hai, main bahut pareshan hoon",
     "band": (1, 90), "want": ["no_filler", "no_list", "plain"]},
    {"id": "general", "kind": "general", "text": "FSSAI licence renew karne ka process kya hai?", "band": (20, 220),
     "want": ["answer_first", "no_filler"]},
    {"id": "followup", "kind": "fact",
     "turns": ["Mera order number 10045678 hai.", "Us order ka number dobara batao aur kis din ka tha?"],
     "band": (1, 60), "want": ["answer_first", "no_invent"], "facts": ["10045678"]},
    {"id": "dontknow", "kind": "fact", "text": "kal Nifty kitne par band hoga?", "band": (1, 60),
     "want": ["answer_first", "no_filler", "no_invent"]},
]

BY_ID = {a["id"]: a for a in ASKS}


def turns_of(ask: dict) -> list[str]:
    """Every turn of an ask; the LAST one is the reply that gets scored."""
    t = ask.get("turns")
    return list(t) if t else [ask["text"]]


def check() -> list[str]:
    """The set itself is sound: unique ids, a band, known kinds and flags."""
    kinds = {"greeting", "yesno", "fact", "figure", "advice", "plan", "multi", "explain", "work", "vague", "style",
             "heavy", "money", "general"}
    flags = {"answer_first", "no_filler", "no_list", "list_ok", "script", "plain", "no_claim", "no_invent",
             "one_question"}
    bad, seen = [], set()
    for a in ASKS:
        if a["id"] in seen:
            bad.append(f"{a['id']}: duplicate id")
        seen.add(a["id"])
        if a["kind"] not in kinds:
            bad.append(f"{a['id']}: unknown kind {a['kind']}")
        lo, hi = a.get("band", (0, 0))
        if not (0 <= lo < hi):
            bad.append(f"{a['id']}: bad band")
        for w in a.get("want", []):
            if w not in flags:
                bad.append(f"{a['id']}: unknown flag {w}")
        if not turns_of(a) or not all(str(x).strip() for x in turns_of(a)):
            bad.append(f"{a['id']}: empty turn")
        if "no_list" in a.get("want", []) and "list_ok" in a.get("want", []):
            bad.append(f"{a['id']}: no_list and list_ok together")
    return bad
