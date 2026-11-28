"""A COBOL record layout (a copybook, or the DATA DIVISION of a program) worked out the way the compiler lays it out: every field's
offset and length from its PICTURE and USAGE (DISPLAY, COMP / BINARY, COMP-3 / PACKED-DECIMAL, COMP-1 / COMP-2, COMP-5), OCCURS,
REDEFINES, level-88 conditions; the type each field becomes in Java, Python, C# and SQL; SQL DDL, a Java record and a Python decoder;
and one record decoded from its bytes (EBCDIC or ASCII, packed and zoned signs) so a translation can be checked against real data.
Pasted text is data."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


class LayoutError(ValueError):
    pass


ENCODINGS = ("cp037", "cp1140", "cp500", "cp273", "cp1047", "ascii")


def _clean(text: str) -> str:
    """Fixed-format source (sequence area 1-6, indicator 7, code 8-72) or free format, into plain lines; comments dropped."""
    lines = str(text or "").replace("\t", "    ").splitlines()
    body = [ln for ln in lines if ln.strip()]
    fixed = bool(body) and sum(1 for ln in body if len(ln) > 6 and (ln[:6].strip() == "" or ln[:6].strip().isdigit()) and ln[6] in " *-/Dd") >= 0.8 * len(body)
    out: list[str] = []
    for ln in lines:
        if fixed:
            if len(ln) > 6 and ln[6] in "*/":
                continue
            code = ln[7:72] if len(ln) > 7 else ""
            if len(ln) > 6 and ln[6] == "-" and out:
                c = code.strip()
                if c[:1] in "'\"":
                    c = c[1:]
                    out[-1] = out[-1].rstrip()
                    if out[-1][-1:] in "'\"":
                        out[-1] = out[-1][:-1]
                out[-1] += c
                continue
            out.append(code.rstrip())
        else:
            s = ln.split("*>")[0].rstrip()
            if s.lstrip().startswith("*"):
                continue
            out.append(s)
    return "\n".join(out)


def _expand(pic: str) -> str:
    p = pic.upper()
    p = re.sub(r"(.)\((\d+)\)", lambda m: m.group(1) * min(int(m.group(2)), 100000), p)
    return p


def _pic(pic: str) -> dict[str, Any]:
    e = _expand(pic)
    edit = bool(re.search(r"[Z*,.+\-B0/$]|CR|DB", e.replace("9", "").replace("V", "").replace("S", "").replace("P", "")))
    if re.fullmatch(r"[XA]+", e):
        return {"cls": "alnum", "chars": len(e), "digits": 0, "scale": 0, "signed": False}
    if re.search(r"[XA]", e):
        return {"cls": "alnum", "chars": len(e.replace("V", "")), "digits": 0, "scale": 0, "signed": False}
    signed = e.startswith("S")
    body = e[1:] if signed else e
    if edit:
        n = len(body.replace("V", "")) - (1 if ("CR" in body or "DB" in body) else 0)
        d = sum(1 for c in body if c in "9Z*")
        sc = len(re.sub(r"[^9Z*]", "", body.split(".")[-1])) if "." in body else (len(re.sub(r"[^9Z*]", "", body.split("V")[-1])) if "V" in body else 0)
        return {"cls": "edited", "chars": n, "digits": d, "scale": sc, "signed": any(c in body for c in "+-") or "CR" in body or "DB" in body}
    if not re.fullmatch(r"[9VP]+", body):
        raise LayoutError(f"PICTURE {pic}: not a picture I can read.")
    digits = body.count("9")
    scale = len(body.split("V")[1].replace("P", "")) if "V" in body else 0
    return {"cls": "num", "chars": digits, "digits": digits, "scale": scale, "signed": signed, "p": body.count("P")}


def _size(pc: dict[str, Any], usage: str, sep: bool) -> int:
    if pc["cls"] != "num":
        return pc["chars"]
    d = pc["digits"]
    if usage in ("COMP-3", "PACKED-DECIMAL", "COMPUTATIONAL-3"):
        return d // 2 + 1
    if usage in ("COMP", "BINARY", "COMP-4", "COMP-5", "COMPUTATIONAL", "COMPUTATIONAL-4", "COMPUTATIONAL-5"):
        return 2 if d <= 4 else 4 if d <= 9 else 8
    return d + (1 if sep else 0)


USAGE_RE = r"(?:USAGE\s+(?:IS\s+)?)?(COMP(?:UTATIONAL)?(?:-[1-5])?|BINARY|PACKED-DECIMAL|DISPLAY|POINTER|INDEX)\b"


def parse(text: str) -> list[dict[str, Any]]:
    src = _clean(text)
    up = re.sub(r"'[^']*'|\"[^\"]*\"", lambda m: m.group(0), src)
    m = re.search(r"\b(?:WORKING-STORAGE|FILE|LINKAGE|LOCAL-STORAGE)\s+SECTION\s*\.", up, re.I)
    proc = re.search(r"\bPROCEDURE\s+DIVISION\b", up, re.I)
    if proc:
        up = up[:proc.start()]
    up = re.sub(r"^\s*(?:FD|SD)\s+[\w-]+[^.]*\.", "", up, flags=re.I | re.M)
    up = re.sub(r"\b[\w-]+\s+SECTION\s*\.", " ", up, flags=re.I)
    up = re.sub(r"\b(?:DATA|ENVIRONMENT|IDENTIFICATION)\s+DIVISION\s*\.", " ", up, flags=re.I)
    _ = m
    ents = []
    for st in re.split(r"\.(?=\s|$)", up):
        s = " ".join(st.split())
        mm = re.match(r"^(\d{1,2})\s+(.*)$", s)
        if not mm:
            continue
        lvl, rest = int(mm.group(1)), mm.group(2)
        if lvl not in range(1, 50) and lvl not in (66, 77, 88):
            continue
        nm = re.match(r"^([A-Za-z0-9][\w-]*)\b\s*(.*)$", rest)
        name, rest2 = ("FILLER", rest) if not nm or nm.group(1).upper() in ("PIC", "PICTURE", "REDEFINES", "OCCURS", "VALUE", "USAGE", "COMP", "COMP-3", "BINARY") else (nm.group(1).upper(), nm.group(2))
        e: dict[str, Any] = {"level": lvl, "name": name, "raw": s[:200]}
        U = rest2.upper()
        if lvl == 88:
            v = re.search(r"VALUES?\s+(?:ARE\s+|IS\s+)?(.*)$", rest2, re.I)
            e["values"] = v.group(1).strip()[:120] if v else ""
            ents.append(e)
            continue
        p = re.search(r"\bPIC(?:TURE)?\s+(?:IS\s+)?(\S+)", rest2, re.I)
        if p:
            e["pic"] = p.group(1).upper()
        u = re.search(USAGE_RE, U)
        e["usage"] = (u.group(1).replace("COMPUTATIONAL", "COMP") if u else "DISPLAY").upper()
        if e["usage"] == "COMP-0":
            e["usage"] = "COMP"
        r = re.search(r"\bREDEFINES\s+([\w-]+)", U)
        if r:
            e["redefines"] = r.group(1)
        o = re.search(r"\bOCCURS\s+(\d+)(?:\s+TO\s+(\d+))?(?:\s+TIMES)?(?:.*?DEPENDING\s+ON\s+([\w-]+))?", U)
        if o:
            e["occurs"] = int(o.group(2) or o.group(1))
            e["occurs_min"] = int(o.group(1))
            if o.group(3):
                e["depending"] = o.group(3)
        e["sep"] = bool(re.search(r"\bSIGN\s+(?:IS\s+)?(?:LEADING|TRAILING)\s+SEPARATE", U))
        e["sync"] = bool(re.search(r"\bSYNC(?:HRONIZED)?\b", U))
        val = re.search(r"\bVALUE\s+(?:IS\s+)?(.+)$", rest2, re.I)
        if val:
            e["value"] = val.group(1).strip()[:60]
        ents.append(e)
    if not ents:
        raise LayoutError("No data items found - paste a copybook (01 / 05 levels with PIC clauses) or a DATA DIVISION.")
    return ents


def _tree(ents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    for e in ents:
        if e["level"] == 88:
            if stack:
                stack[-1].setdefault("conds", []).append({"name": e["name"], "values": e.get("values", "")})
            continue
        if e["level"] == 66:
            continue
        node = {**e, "kids": []}
        lvl = 1 if e["level"] == 77 else e["level"]
        node["_l"] = lvl
        while stack and stack[-1]["_l"] >= lvl:
            stack.pop()
        if stack:
            stack[-1]["kids"].append(node)
        else:
            roots.append(node)
        stack.append(node)
    return roots


def _lay(node: dict[str, Any], off: int, rows: list[dict[str, Any]], path: str, names: dict[str, dict[str, Any]], issues: list[dict[str, Any]], depth: int, occ_in: str = "") -> int:
    """Lay out node at off; return its length (one occurrence)."""
    if node.get("redefines"):
        tgt = names.get(node["redefines"])
        if tgt is None:
            issues.append({"sev": "warn", "text": f"{node['name']} REDEFINES {node['redefines']}, which is not in the paste - laid out at the next free byte."})
        else:
            off = tgt["offset"]
    full = f"{path}.{node['name']}" if path else node["name"]
    row: dict[str, Any] = {"level": node["level"], "name": node["name"], "path": full, "offset": off, "depth": depth, "usage": node.get("usage", "DISPLAY"),
                           "pic": node.get("pic", ""), "occurs": node.get("occurs", 0), "redefines": node.get("redefines", ""), "conds": node.get("conds", []),
                           "depending": node.get("depending", ""), "value": node.get("value", ""), "in_occurs": occ_in}
    rows.append(row)
    if node["kids"]:
        row["group"] = True
        cur = off
        end = off
        for k in node["kids"]:
            ln = _lay(k, cur, rows, full, names, issues, depth + 1, occ_in or (node["name"] if node.get("occurs", 0) > 1 else ""))
            kk = names[k["name"]] if k["name"] in names and names[k["name"]].get("_id") == id(k) else None
            occ = k.get("occurs") or 1
            if k.get("redefines"):
                start = (names.get(k["redefines"]) or {"offset": cur})["offset"]
                end = max(end, start + ln * occ)
            else:
                cur += ln * occ
                end = max(end, cur)
            _ = kk
        length = end - off
        row.update(length=length, kind="group", type={"java": "", "python": "", "csharp": "", "sql": ""})
    else:
        usage = row["usage"]
        if usage in ("COMP-1",):
            pc, length = {"cls": "float", "digits": 7, "scale": 0, "signed": True, "chars": 4}, 4
        elif usage in ("COMP-2",):
            pc, length = {"cls": "float", "digits": 15, "scale": 0, "signed": True, "chars": 8}, 8
        elif usage in ("POINTER", "INDEX"):
            pc, length = {"cls": "ptr", "digits": 0, "scale": 0, "signed": False, "chars": 4}, 4
        elif not row["pic"]:
            issues.append({"sev": "warn", "text": f"{node['name']} has no PICTURE and no children - counted as 0 bytes."})
            pc, length = {"cls": "alnum", "digits": 0, "scale": 0, "signed": False, "chars": 0}, 0
        else:
            pc = _pic(row["pic"])
            if pc["cls"] != "num" and usage not in ("DISPLAY",):
                issues.append({"sev": "warn", "text": f"{node['name']}: USAGE {usage} on a non-numeric picture {row['pic']}."})
            length = _size(pc, usage, node.get("sep", False))
        if node.get("sync") and usage in ("COMP", "BINARY", "COMP-4", "COMP-5", "COMP-1", "COMP-2") and length in (2, 4, 8) and off % length:
            pad = length - off % length
            issues.append({"sev": "info", "text": f"{node['name']} is SYNCHRONIZED: {pad} slack byte(s) before it (offset {off + pad})."})
            off += pad
            row["offset"] = off
            length += 0
        row.update(length=length, cls=pc["cls"], digits=pc["digits"], scale=pc["scale"], signed=pc["signed"], kind=_kind(pc, usage),
                   type=_types(pc, usage, length, node["name"]))
        if pc.get("p"):
            issues.append({"sev": "info", "text": f"{node['name']}: PICTURE {row['pic']} has P (scaling) positions - the stored digits are scaled by a power of ten."})
    node["_id"] = id(node)
    names[node["name"]] = {**row, "_id": id(node)}
    return row["length"]


def _kind(pc: dict[str, Any], usage: str) -> str:
    if pc["cls"] == "alnum":
        return "text"
    if pc["cls"] == "edited":
        return "edited"
    if pc["cls"] == "float":
        return "float"
    if pc["cls"] == "ptr":
        return "pointer"
    if usage in ("COMP-3", "PACKED-DECIMAL"):
        return "packed"
    if usage in ("COMP", "BINARY", "COMP-4", "COMP-5"):
        return "binary"
    return "zoned"


def _types(pc: dict[str, Any], usage: str, length: int, name: str) -> dict[str, str]:
    if pc["cls"] in ("alnum", "edited"):
        sql = f"CHAR({length})"
        if re.search(r"DATE|DT\b|-DT-", name) and length in (8, 10):
            sql += "  -- a date? check its format"
        return {"java": "String", "python": "str", "csharp": "string", "sql": sql}
    if pc["cls"] == "float":
        return {"java": "double" if pc["digits"] > 7 else "float", "python": "float", "csharp": "double" if pc["digits"] > 7 else "float",
                "sql": "DOUBLE PRECISION" if pc["digits"] > 7 else "REAL"}
    if pc["cls"] == "ptr":
        return {"java": "long", "python": "int", "csharp": "IntPtr", "sql": "BIGINT"}
    d, s = pc["digits"], pc["scale"]
    if s > 0 or d > 18:
        return {"java": "BigDecimal", "python": "Decimal", "csharp": "decimal", "sql": f"DECIMAL({d},{s})"}
    if usage in ("COMP", "BINARY", "COMP-4", "COMP-5"):
        sql = "SMALLINT" if d <= 4 else "INTEGER" if d <= 9 else "BIGINT"
    else:
        sql = f"DECIMAL({d},0)"
    return {"java": "int" if d <= 9 else "long", "python": "int", "csharp": "int" if d <= 9 else "long", "sql": sql}


def _ident(name: str, style: str) -> str:
    parts = [p for p in re.split(r"[-_]", name.lower()) if p]
    if not parts:
        return "field"
    if style == "camel":
        s = parts[0] + "".join(p.capitalize() for p in parts[1:])
    elif style == "pascal":
        s = "".join(p.capitalize() for p in parts)
    else:
        s = "_".join(parts)
    return ("f_" + s) if s[0].isdigit() else s


def analyse(text: str, encoding: str = "cp037", sample: str = "") -> dict[str, Any]:
    t = str(text or "")
    if len(t) > 2_000_000:
        raise LayoutError("That is longer than 2 MB.")
    ents = parse(t)
    roots = _tree(ents)
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    names: dict[str, dict[str, Any]] = {}
    records = []
    for r in roots:
        n0 = len(rows)
        ln = _lay(r, 0, rows, "", names, issues, 0)
        records.append({"name": r["name"], "length": ln * (r.get("occurs") or 1), "fields": len(rows) - n0})
    leaves = [r for r in rows if not r.get("group")]
    for r in leaves:
        if r["kind"] == "packed" and r["digits"] % 2 == 0:
            issues.append({"sev": "info", "text": f"{r['name']}: PIC {r['pic']} COMP-3 has an even number of digits ({r['digits']}) - the packed field still takes {r['length']} bytes; the extra half-byte is always 0."})
        if r["kind"] == "float":
            issues.append({"sev": "warn", "text": f"{r['name']} is {r['usage']} (IBM hexadecimal floating point on z/OS, not IEEE): the values do not convert bit for bit - convert through a decimal and check them."})
        if r["kind"] == "zoned" and r["signed"]:
            issues.append({"sev": "info", "text": f"{r['name']}: a signed zoned number - the sign is in the zone of the last byte (C / D / F in EBCDIC, an overpunch letter in ASCII files), not a '-' character."}) if len([i for i in issues if "signed zoned" in i["text"]]) < 1 else None
        if re.search(r"(?:^|-)(?:YY|YR|YEAR)(?:-|$)", r["name"]) and r["digits"] == 2:
            issues.append({"sev": "warn", "text": f"{r['name']}: a two-digit year - the translation must apply the same window (or the century field) the old code uses."})
        if re.search(r"DATE", r["name"]) and r["digits"] == 6 and r["kind"] in ("zoned", "packed"):
            issues.append({"sev": "warn", "text": f"{r['name']}: a 6-digit date (YYMMDD?) - two-digit year; check how the century is decided."})
    for r in rows:
        if r.get("depending"):
            issues.append({"sev": "warn", "text": f"{r['name']} OCCURS ... DEPENDING ON {r['depending']}: the record length changes with the data - the layout here is its longest form."})
        if r.get("redefines"):
            issues.append({"sev": "info", "text": f"{r['name']} REDEFINES {r['redefines']}: the same bytes read two ways - the translation needs both views (a union / two classes) and the rule for which one applies."})
    seen: set[str] = set()
    issues2 = []
    for i in issues:
        if i["text"] not in seen:
            seen.add(i["text"])
            issues2.append(i)
    issues = issues2
    rec = records[0]
    flat = [r for r in leaves if r["length"] > 0]
    ddl = _ddl(records, rows)
    java = _java(rows, roots)
    py = _python(rows, roots, encoding)
    decoded = decode(sample, rows, encoding) if str(sample or "").strip() else None
    if decoded:
        issues += decoded["issues"]
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    out_rows = [{k: r.get(k) for k in ("level", "name", "path", "offset", "length", "pic", "usage", "kind", "digits", "scale", "signed", "occurs",
                                        "redefines", "depending", "conds", "type", "group", "depth", "value", "in_occurs")} for r in rows]
    return {"records": records, "rows": out_rows[:3000], "fields": len(flat), "length": rec["length"], "issues": issues,
            "counts": {k: sum(1 for i in issues if i["sev"] == k) for k in order},
            "kinds": {k: sum(1 for r in flat if r["kind"] == k) for k in ("text", "zoned", "packed", "binary", "edited", "float", "pointer")},
            "ddl": ddl, "java": java, "python": py, "decoded": decoded, "encoding": encoding,
            "verdict": ", ".join(f"{r['name']}: {r['length']} bytes" for r in records[:4]) + f" - {len(flat)} fields"
                       + (f", {sum(1 for r in flat if r['kind'] == 'packed')} packed" if any(r["kind"] == "packed" for r in flat) else "") + ".",
            "note": ("Laid out as IBM Enterprise COBOL does with default options: no slack bytes unless SYNCHRONIZED, binary sizes from the digits "
                     "(TRUNC(STD)), the longest OCCURS DEPENDING ON. Offsets start at 0 (add 1 for a COBOL listing).")}


def _ddl(records: list[dict[str, Any]], rows: list[dict[str, Any]]) -> str:
    out = []
    by_rec: dict[str, list[dict[str, Any]]] = {}
    cur = None
    for r in rows:
        if r["depth"] == 0:
            cur = r["name"]
            by_rec[cur] = []
            if not r.get("group"):
                by_rec[cur].append(r)
            continue
        if cur and r.get("group") and r.get("occurs", 0) > 1 and not r.get("in_occurs"):
            by_rec[cur].append({**r, "type": {"sql": ""}})
        elif cur and not r.get("group") and r["name"] != "FILLER" and not r.get("redefines") and r["length"] and not r.get("in_occurs"):
            by_rec[cur].append(r)
    for rec, fs in by_rec.items():
        if not fs:
            continue
        cols = []
        for f in fs[:400]:
            nm = _ident(f["name"], "snake")
            if f.get("occurs") and f["occurs"] > 1:
                cols.append(f"  -- {nm}: OCCURS {f['occurs']} - a child table, one row per occurrence")
                continue
            cols.append(f"  {nm} {f['type']['sql'].split('  --')[0]}" + (f"  -- {f['type']['sql'].split('--')[1].strip()}" if "--" in f["type"]["sql"] else ""))
        body = ",\n".join(c for c in cols if not c.lstrip().startswith("--"))
        notes = "\n".join(c for c in cols if c.lstrip().startswith("--"))
        out.append(f"CREATE TABLE {_ident(rec, 'snake')} (\n{body}\n);" + (f"\n{notes}" if notes else ""))
    return "\n\n".join(out)


def _java(rows: list[dict[str, Any]], roots: list[dict[str, Any]]) -> str:
    out = ["import java.math.BigDecimal;", ""]
    for r in [x for x in rows if x["depth"] == 0][:4]:
        fs = [x for x in rows if x["path"].startswith(r["name"] + ".") and not x.get("group") and x["name"] != "FILLER" and not x.get("redefines")]
        if not r.get("group"):
            fs = [r]
        out.append(f"public record {_ident(r['name'], 'pascal')}(")
        out.append(",\n".join(f"    {f['type']['java']}{'[]' if f.get('occurs', 0) > 1 else ''} {_ident(f['name'], 'camel')}" for f in fs[:300]))
        out.append(") {}\n")
    return "\n".join(out)


def _python(rows: list[dict[str, Any]], roots: list[dict[str, Any]], encoding: str) -> str:
    rec = [x for x in rows if x["depth"] == 0][0]
    fs = [x for x in rows if (x["path"].startswith(rec["name"] + ".") or x is rec) and not x.get("group") and x["name"] != "FILLER"]
    lines = ["from decimal import Decimal", "", f"ENC = {encoding!r}", "",
             "def _packed(b, scale):",
             "    h = b.hex()",
             "    sign = -1 if h[-1] in 'bd' else 1",
             "    return sign * Decimal(int(h[:-1] or '0')).scaleb(-scale)", "",
             "def _zoned(b, scale, signed):",
             "    if ENC == 'ascii':",
             "        s = b.decode('ascii')",
             "        last = s[-1]",
             "        neg = last in '}JKLMNOPQRp'",
             "        d = {'{': '0', '}': '0'}.get(last) or (str('ABCDEFGHI'.index(last) + 1) if last in 'ABCDEFGHI' else str('JKLMNOPQR'.index(last) + 1) if last in 'JKLMNOPQR' else last)",
             "        s = s[:-1] + d",
             "    else:",
             "        neg = signed and (b[-1] >> 4) == 0xD",
             "        s = ''.join(str(x & 0x0F) for x in b)",
             "    return (-1 if neg else 1) * Decimal(int(s)).scaleb(-scale)", "",
             f"def decode_{_ident(rec['name'], 'snake')}(rec: bytes) -> dict:",
             "    return {"]
    for f in fs[:300]:
        sl = f"rec[{f['offset']}:{f['offset'] + f['length']}]"
        k, nm = f["kind"], _ident(f["name"], "snake")
        if k in ("text", "edited"):
            ex = f"{sl}.decode(ENC)"
        elif k == "packed":
            ex = f"_packed({sl}, {f['scale']})"
        elif k == "zoned":
            ex = f"_zoned({sl}, {f['scale']}, {f['signed']})"
        elif k == "binary":
            ex = f"Decimal(int.from_bytes({sl}, 'big', signed={f['signed']})).scaleb(-{f['scale']})" if f["scale"] else f"int.from_bytes({sl}, 'big', signed={f['signed']})"
        else:
            ex = f"{sl}  # {k}: convert by hand"
        lines.append(f"        {nm!r}: {ex},")
    lines.append("    }")
    return "\n".join(lines) + "\n"


def _bytes(sample: str, encoding: str) -> bytes:
    s = str(sample or "").strip()
    hx = re.sub(r"[\s:]", "", s)
    if re.fullmatch(r"(?:[0-9A-Fa-f]{2})+", hx) and len(hx) >= 4 and (len(set(hx.lower())) > 2 or len(hx) > 8):
        return bytes.fromhex(hx)
    try:
        return s.encode(encoding if encoding != "ascii" else "ascii")
    except (UnicodeEncodeError, LookupError):
        return s.encode("latin-1", "replace")


def decode(sample: str, rows: list[dict[str, Any]], encoding: str = "cp037") -> dict[str, Any]:
    if encoding not in ENCODINGS:
        raise LayoutError("Encoding: " + ", ".join(ENCODINGS))
    b = _bytes(sample, encoding)
    out = []
    issues: list[dict[str, Any]] = []
    tlen = max((r["offset"] + r["length"] * max(1, int(r.get("occurs") or 1)) for r in rows if not r.get("redefines")), default=0)
    if len(b) < tlen:
        issues.append({"sev": "warn", "text": f"The sample is {len(b)} bytes; the record is {tlen} - the fields past the end are not decoded."})
    elif len(b) > tlen:
        issues.append({"sev": "info", "text": f"The sample is {len(b)} bytes; the record is {tlen} - {len(b) - tlen} byte(s) after it were not read (another record type, or a longer layout)."})
    for r in rows:
        if r.get("group") or r["offset"] + r["length"] > len(b) or not r["length"]:
            continue
        raw = b[r["offset"]:r["offset"] + r["length"]]
        val: Any
        bad = ""
        k = r["kind"]
        try:
            if k in ("text", "edited"):
                val = raw.decode(encoding if encoding != "ascii" else "ascii", "replace")
                if raw and set(raw) == {0}:
                    bad = "low-values (all X'00')"
            elif k == "packed":
                h = raw.hex()
                if not re.fullmatch(r"[0-9]*[a-f]", h) or h[-1] not in "abcdef":
                    bad = f"not valid packed decimal (X'{h.upper()}')"
                    val = None
                else:
                    val = str((-1 if h[-1] in "bd" else 1) * Decimal(int(h[:-1] or "0")).scaleb(-r["scale"]))
                    if h[-1] == "f" and r["signed"]:
                        bad = "sign F (unsigned) in a signed field"
            elif k == "zoned":
                if encoding == "ascii":
                    s = raw.decode("ascii", "replace")
                    last = s[-1:]
                    neg = last in "}JKLMNOPQR" or last == "p"
                    rep = {"{": "0", "}": "0"}.get(last) or (str("ABCDEFGHI".index(last) + 1) if last in "ABCDEFGHI" else str("JKLMNOPQR".index(last) + 1) if last in "JKLMNOPQR" else last)
                    digits = s[:-1] + rep
                else:
                    if any((x >> 4) not in (0xF, 0xC, 0xD) or (x & 0xF) > 9 for x in raw[:-1]) or (raw[-1] & 0xF) > 9:
                        raise ValueError
                    neg = (raw[-1] >> 4) == 0xD
                    digits = "".join(str(x & 0xF) for x in raw)
                if not digits.isdigit():
                    raise ValueError
                val = str((-1 if neg else 1) * Decimal(int(digits)).scaleb(-r["scale"]))
            elif k == "binary":
                n = int.from_bytes(raw, "big", signed=bool(r["signed"]))
                val = str(Decimal(n).scaleb(-r["scale"])) if r["scale"] else n
                if r["digits"] and abs(n) >= 10 ** r["digits"]:
                    bad = f"{abs(n)} has more digits than PIC {r['pic']} allows (fine under TRUNC(BIN), cut under TRUNC(STD))"
            else:
                val = raw.hex().upper()
        except ValueError:
            val, bad = None, f"not a valid number (X'{raw.hex().upper()}')"
        if bad:
            issues.append({"sev": "warn", "text": f"{r['name']} at offset {r['offset']}: {bad}."})
        out.append({"name": r["name"], "offset": r["offset"], "length": r["length"], "kind": k, "hex": raw.hex().upper(), "value": val, "bad": bad})
    return {"bytes": len(b), "fields": out[:2000], "issues": issues, "encoding": encoding}
