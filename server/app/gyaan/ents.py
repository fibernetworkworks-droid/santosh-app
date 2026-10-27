"""Gyaan entities (v0.135): the names in her knowledge (people, firms / shops, with honorifics in 3 scripts) pulled out of
every chunk by plain rules, kept with a spelling-forgiving key, so:

  - "Gupta ji ka last bill" finds every piece that names Ramesh Gupta / गुप्ता जी, whatever the spelling or script
  - `related(name)` = which other names appear in the same documents (a small "who is connected to whom" graph)

No model, no guessing: only names that LOOK like names (honorific + name, Name + ji / bhai / sir, firm suffix words, two or
more capitalised words that aren't form labels). Masked text only (chunks are already masked), so no ID number is a name."""
from __future__ import annotations

import re
from typing import Any

from . import norm

HONOR = {"shri", "shree", "sri", "smt", "shrimati", "mr", "mrs", "ms", "dr", "adv", "ca", "er", "prof", "kumari", "km",
         "late", "sau", "kum", "श्री", "श्रीमती", "डॉ", "डॉ.", "सौ", "कु", "स्व"}
AFTER = {"ji", "jee", "sir", "madam", "mam", "bhai", "bhaiya", "sahab", "saheb", "seth", "tai", "didi", "bhau", "kaka",
         "जी", "भाई", "साहब", "सर", "ताई", "दीदी", "भाऊ", "काका", "सेठ"}
FIRM = {"traders", "trader", "enterprises", "enterprise", "industries", "agency", "agencies", "stores", "store", "kirana",
        "medical", "medicals", "pharma", "pharmacy", "hospital", "clinic", "pvt", "ltd", "llp", "sons", "brothers", "bros",
        "corporation", "solutions", "services", "motors", "electricals", "electronics", "textiles", "mart", "bank",
        "finance", "foods", "dairy", "jewellers", "jewellery", "builders", "construction", "constructions", "infra",
        "logistics", "transport", "travels", "tours", "academy", "classes", "school", "college", "hotel", "restaurant",
        "caterers", "hardware", "paints", "steels", "cement", "fabrics", "garments", "boutique", "studio", "labs",
        "laboratory", "diagnostics", "associates", "consultants", "co", "company", "group", "mills", "udyog",
        "ट्रेडर्स", "एंटरप्राइजेज", "एंटरप्राइज़ेज", "स्टोर्स", "स्टोर", "किराना", "मेडिकल", "हॉस्पिटल", "क्लिनिक", "उद्योग",
        "एजेंसी", "इंडस्ट्रीज", "ज्वेलर्स", "बैंक", "डेयरी", "ट्रांसपोर्ट"}
# capitalised words that are form / document labels, not names
LABEL = {"date", "total", "invoice", "bill", "amount", "the", "dear", "sir", "madam", "subject", "from", "to", "page", "tax",
         "gst", "gstin", "rs", "inr", "no", "number", "name", "address", "phone", "mobile", "email", "qty", "rate", "item",
         "description", "hsn", "sac", "cgst", "sgst", "igst", "net", "grand", "sub", "balance", "due", "paid", "payment",
         "receipt", "order", "customer", "seller", "buyer", "ship", "bill to", "terms", "conditions", "thank", "thanks",
         "regards", "yours", "sincerely", "faithfully", "please", "kindly", "note", "notes", "important", "agreement",
         "rent", "deposit", "month", "year", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
         "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
         "december", "india", "maharashtra", "pune", "mumbai", "nagpur", "akola", "nashik", "goa", "delhi", "state", "city",
         "district", "pin", "code", "ifsc", "account", "bank", "branch", "upi", "id", "ref", "reference", "status", "report",
         "summary", "details", "list", "table", "section", "chapter", "part", "annexure", "schedule", "form", "copy",
         "original", "duplicate", "signature", "authorised", "authorized", "signatory", "for", "of", "and", "in", "on", "at",
         "by", "with", "a", "an", "is", "this", "that", "our", "your", "my", "we", "you", "i", "it", "be", "are", "was",
         "hello", "hi", "good", "morning", "evening", "team", "office", "head", "manager", "owner", "director", "partner",
         "proprietor", "mrp", "price", "cost", "fee", "fees", "charge", "charges", "discount", "offer", "free", "new", "old"}
_LAT = re.compile(r"[A-Za-z][A-Za-z.&'-]*")
_TOKEN = re.compile(r"[A-Za-z][A-Za-z.&'-]*|[ऀ-ॿ]+|\S")
_VOWEL = re.compile(r"[aeiouy]+")


def skel(word: str) -> str:
    """Spelling-forgiving key of one word: phon, then vowels dropped after the first letter (traders / tredars -> trdrs)."""
    p = norm.phon(word).replace(" ", "")
    if not p:
        return ""
    return p[0] + _VOWEL.sub("", p[1:])


def key_of(name: str) -> str:
    toks = [t.strip(".,") for t in name.split()]
    toks = [t for t in toks if t and t.lower().strip(".") not in HONOR and t.lower() not in AFTER and t not in AFTER]
    ks = [skel(t) for t in toks]
    return " ".join(k for k in ks if len(k) >= 2)


def _cap(t: str) -> bool:
    return bool(_LAT.fullmatch(t)) and (t[0].isupper()) and t.lower().strip(".") not in LABEL and len(t.strip(".")) >= 2


def _deva(t: str) -> bool:
    """A Devanagari word that can be part of a name (not ने / से / का / है ...)."""
    return bool(re.fullmatch(r"[ऀ-ॿ]+", t)) and (t in FIRM or bool(norm.words(t)))


def find(text: str) -> list[tuple[str, str]]:
    """-> [(display name, kind person | firm | name)] in the text, de-duplicated by key."""
    out: dict[str, tuple[str, str]] = {}
    for line in (text or "").splitlines():                # a name never runs across a line break
        _find_line(line, out)
    return list(out.values())


def _find_line(text: str, out: dict[str, tuple[str, str]]) -> None:
    toks = _TOKEN.findall(text or "")
    n = len(toks)

    def add(words: list[str], kind: str) -> None:
        name = " ".join(words).strip(" .,")
        k = key_of(name)
        if not k or len(k) < 3 or len(name) > 60:
            return
        if all(w.lower().strip(".") in LABEL or w.lower() in FIRM for w in words if w.lower().strip(".") not in HONOR):
            return
        old = out.get(k)
        if not old or (kind != "name" and old[1] == "name"):
            out[k] = (name, kind)

    i = 0
    while i < n:
        t = toks[i]
        tl = t.lower().strip(".")
        # 1. honorific + 1-3 name words (Latin capitalised or Devanagari)
        if tl in HONOR or t in HONOR:
            j, words = i + 1, [t]
            while j < n and len(words) < 4 and (_cap(toks[j]) or (_deva(toks[j]) and toks[j] not in AFTER)):
                words.append(toks[j])
                j += 1
            if len(words) >= 2:
                firm = any(w.lower() in FIRM or w in FIRM for w in words)
                add(words, "firm" if firm else "person")
                i = j
                continue
        # 2. capitalised / Devanagari run, maybe ending in a firm word
        if _cap(t) or (_deva(t) and t not in AFTER and t not in HONOR):
            j, words = i, []
            while j < n and len(words) < 5 and (_cap(toks[j]) or toks[j].lower() in FIRM or toks[j] in FIRM
                                                or (_deva(toks[j]) and toks[j] not in AFTER and toks[j] not in HONOR)
                                                or toks[j] == "&"):
                words.append(toks[j])
                j += 1
            while words and words[-1] == "&":
                words.pop()
            fi = next((x for x, w in enumerate(words) if x > 0 and (w.lower() in FIRM or w in FIRM)), -1)
            if fi > 0:                                            # a firm name ends at its (last) firm word
                first = fi
                while fi + 1 < len(words) and (words[fi + 1].lower() in FIRM or words[fi + 1] in FIRM):
                    fi += 1
                j = i + fi + 1
                words = words[max(0, first - 3):fi + 1]
            nxt = toks[j].lower() if j < n else ""
            firm = any(w.lower() in FIRM or w in FIRM for w in words[1:])
            deva = all(_deva(w) for w in words)
            if words and (nxt in AFTER or (j < n and toks[j] in AFTER)):
                add(words[-2:], "person")                         # "Ramesh Gupta ji", "गुप्ता जी"
            elif firm and len(words) >= 2:
                add(words, "firm")                                # "Shree Ganesh Traders", "गणेश ट्रेडर्स"
            elif len(words) >= 2 and not deva and sum(1 for w in words if _cap(w)) >= 2:
                add(words[:4], "name")                            # "Kunal Patil", "Lotus Residency"
            i = max(j, i + 1)
            continue
        # 3. lowercase Hinglish "gupta ji" / "ramesh bhai"
        if re.fullmatch(r"[a-z]{3,}", t) and i + 1 < n and toks[i + 1].lower() in AFTER and t not in LABEL \
                and t not in norm.STOP:
            add([t.capitalize()], "person")
            i += 2
            continue
        i += 1


def index(c, chunk_id: int, doc_id: str, text: str) -> int:
    rows = [(key_of(nm), nm, kind, chunk_id, doc_id) for nm, kind in find(text)]
    rows = [r for r in rows if r[0]]
    if rows:
        c.executemany("INSERT INTO ents(key, name, kind, chunk_id, doc_id) VALUES(?,?,?,?,?)", rows)
    return len(rows)


def match(c, query_variants: list[str], limit: int = 40) -> tuple[list[int], list[str]]:
    """Chunks naming someone / something the question names. A name matches when all its key words are in the question,
    or the question has its last word (surname / firm word) plus an honorific, or it is a one-word name."""
    qkeys: list[str] = []
    for v in query_variants:
        for w in re.findall(r"[A-Za-z]+|[ऀ-ॿ]+", v):
            if w.lower() in norm.STOP or w.lower() in LABEL or w in AFTER or w.lower() in AFTER or w.lower() in HONOR:
                continue
            k = skel(w)
            if len(k) >= 3 and k not in qkeys:
                qkeys.append(k)
    if not qkeys:
        return [], []
    cand: dict[str, tuple[str, int]] = {}
    for k in qkeys[:12]:
        for r in c.execute("SELECT key, name FROM ents WHERE key=? OR key LIKE ? OR key LIKE ? OR key LIKE ? LIMIT 200",
                           (k, k + " %", "% " + k, "% " + k + " %")):
            if r["key"] not in cand:
                cand[r["key"]] = (r["name"], 0)
    names: list[str] = []
    keys: list[str] = []
    qset = set(qkeys)
    for key, (nm, _) in cand.items():
        parts = key.split()
        got = sum(1 for p in parts if p in qset)
        firmish = parts and parts[-1] in {skel(f) for f in ("traders", "enterprises", "stores", "store", "agency")}
        if got == len(parts) or (got >= 1 and len(parts) >= 2 and parts[-1] in qset and not firmish) or \
                (got >= 2 and got >= len(parts) - 1):
            keys.append(key)
            names.append(nm)
    if not keys:
        return [], []
    qs = ",".join("?" * len(keys))
    ids = [r[0] for r in c.execute(f"SELECT DISTINCT chunk_id FROM ents WHERE key IN ({qs}) LIMIT ?", (*keys, limit))]
    return ids, list(dict.fromkeys(names))


def top(c, q: str = "", limit: int = 40) -> list[dict[str, Any]]:
    """The names in her knowledge: how many documents each appears in (most first), optionally filtered."""
    args: list[Any] = []
    sql = ("SELECT key, MIN(name) AS name, MAX(kind) AS kind, COUNT(DISTINCT doc_id) AS docs FROM ents ")
    if q:
        k = key_of(q)
        sql += "WHERE key LIKE ? OR key LIKE ? "
        args += [f"%{k}%" if k else "%", f"%{skel(q)}%"]
    sql += "GROUP BY key ORDER BY docs DESC, name LIMIT ?"
    args.append(limit)
    return [{"name": r["name"], "kind": r["kind"], "docs": r["docs"], "key": r["key"]} for r in c.execute(sql, args)]


def related(c, name: str, limit: int = 12) -> dict[str, Any]:
    """Who / what appears in the same documents as this name, and those documents' titles."""
    k = key_of(name)
    if not k:
        return {"name": name, "found": False, "docs": [], "related": []}
    docs = [r[0] for r in c.execute("SELECT DISTINCT doc_id FROM ents WHERE key=? OR key LIKE ? OR key LIKE ?",
                                    (k, k + " %", "% " + k))]
    if not docs:
        return {"name": name, "found": False, "docs": [], "related": []}
    qs = ",".join("?" * len(docs))
    titles = [{"doc_id": r["id"], "title": r["title"], "source": r["source"]}
              for r in c.execute(f"SELECT id, title, source FROM docs WHERE id IN ({qs}) ORDER BY added DESC LIMIT 20", docs)]
    rel = [{"name": r["name"], "kind": r["kind"], "together": r["n"]}
           for r in c.execute(f"SELECT key, MIN(name) AS name, MAX(kind) AS kind, COUNT(DISTINCT doc_id) AS n FROM ents "
                              f"WHERE doc_id IN ({qs}) AND key != ? GROUP BY key ORDER BY n DESC LIMIT ?",
                              (*docs, k, limit))]
    return {"name": name, "found": True, "docs": titles, "related": rel}
