"""COBOL programs read for modernization: program id, divisions, paragraphs and sections, the PERFORM / GO TO graph inside the
program and the paragraphs no path reaches, CALLs (static or from data), COPY members, EXEC SQL (statements and tables), EXEC CICS
(programs linked, files, maps, transactions), files (SELECT / ASSIGN / FILE STATUS), size and decision counts, and what makes a
translation risky: ALTER, GO TO, NEXT SENTENCE, REDEFINES, packed and floating numbers, two-digit years, OCCURS DEPENDING ON, a
COMPUTE that truncates. Fixed (columns 8-72) or free format. Pasted code is data."""
from __future__ import annotations

import re
from typing import Any

from . import layout as LY


class CobolError(ValueError):
    pass


VERBS = ("ACCEPT ADD ALTER CALL CANCEL CLOSE COMPUTE CONTINUE DELETE DISPLAY DIVIDE EVALUATE EXIT GO GOBACK IF INITIALIZE INSPECT MERGE "
         "MOVE MULTIPLY OPEN PERFORM READ RELEASE RETURN REWRITE SEARCH SET SORT START STOP STRING SUBTRACT UNSTRING WRITE EXEC").split()
NOT_PARA = set(VERBS) | {"END-IF", "END-PERFORM", "END-EVALUATE", "END-READ", "END-EXEC", "ELSE", "WHEN", "THEN", "NOT", "END",
                         "DECLARATIVES", "USE", "PROCEDURE", "SKIP1", "SKIP2", "SKIP3", "EJECT"}
SYSTEM_COPY = {"SQLCA", "SQLDA", "DFHAID", "DFHBMSCA", "DFHEIBLK", "DFHCOMMAREA", "DFHEIVAR", "DFHRESP"}
SYSTEM_CALL = re.compile(r"^(?:CEE|IGZ|ILBO|DSNHLI|DSNTIAR|DSNALI|CBLTDLI|AIBTDLI|DFH|IEFBR14|ILBOABN0|CEEDAYS|CEELOCT|CEE3ABD|IKJ)")


def _strip_lit(s: str) -> str:
    return re.sub(r"'[^']*'|\"[^\"]*\"", lambda m: "'" + "_" * (len(m.group(0)) - 2) + "'", s)


def split_programs(text: str) -> list[str]:
    src = LY._clean(text)
    marks = [m.start() for m in re.finditer(r"^\s*(?:IDENTIFICATION|ID)\s+DIVISION\s*\.", src, re.I | re.M)]
    if not marks:
        return [src]
    if marks[0] > 0 and src[:marks[0]].strip():
        marks = [0] + marks
    # a nested program (END PROGRAM between) stays with its parent only when it is inside one
    return [src[a:b] for a, b in zip(marks, marks[1:] + [len(src)]) if src[a:b].strip()]


def _paragraphs(proc: str) -> list[dict[str, Any]]:
    paras: list[dict[str, Any]] = []
    cur: dict[str, Any] = {"name": "(start)", "lines": [], "section": ""}
    section = ""
    for ln in proc.splitlines():
        s = ln.rstrip()
        m = re.match(r"^\s{0,3}([A-Z0-9][A-Z0-9-]*)(\s+SECTION)?\s*\.\s*$", s.upper())
        if m and m.group(1) not in NOT_PARA and not m.group(1).isdigit():
            if cur["lines"] or cur["name"] != "(start)":
                paras.append(cur)
            if m.group(2):
                section = m.group(1)
            cur = {"name": m.group(1), "lines": [], "section": section, "is_section": bool(m.group(2))}
            continue
        if s.strip():
            cur["lines"].append(s)
    paras.append(cur)
    if paras and paras[0]["name"] == "(start)" and not paras[0]["lines"]:
        paras = paras[1:]
    return paras


def _targets(body: str, names: set[str]) -> tuple[list[str], list[str]]:
    perf: list[str] = []
    gos: list[str] = []
    for m in re.finditer(r"\bPERFORM\s+([A-Z0-9][A-Z0-9-]*)(?:\s+(?:THRU|THROUGH)\s+([A-Z0-9][A-Z0-9-]*))?", body):
        a = m.group(1)
        if a in names:
            perf.append(a + (">" + m.group(2) if m.group(2) and m.group(2) in names else ""))
    for m in re.finditer(r"\bGO\s+TO\s+((?:[A-Z0-9][A-Z0-9-]*[\s,]*)+?)(?:DEPENDING\b|\.|$|\n)", body):
        for t in re.findall(r"[A-Z0-9][A-Z0-9-]*", m.group(1)):
            if t in names:
                gos.append(t)
    return perf, gos


def _reach(paras: list[dict[str, Any]]) -> set[str]:
    names = [p["name"] for p in paras]
    idx = {n: i for i, n in enumerate(names)}
    term = re.compile(r"\b(?:GOBACK|STOP\s+RUN|EXIT\s+PROGRAM|GO\s+TO\s+[A-Z0-9][A-Z0-9-]*\s*\.?\s*$)", re.S)
    reached: set[str] = set()
    todo = [(names[0], True)] if names else []
    seen: set[tuple[str, bool]] = set()
    while todo:
        n, main = todo.pop()
        if (n, main) in seen:
            continue
        seen.add((n, main))
        reached.add(n)
        p = paras[idx[n]]
        for t in p["perf"]:
            a, _, b = t.partition(">")
            if b:
                for k in range(idx[a], idx[b] + 1):
                    todo.append((names[k], False))
            else:
                todo.append((a, False))
                if paras[idx[a]].get("is_section"):
                    k = idx[a] + 1
                    while k < len(paras) and not paras[k].get("is_section"):
                        todo.append((names[k], False))
                        k += 1
        for t in p["go"]:
            todo.append((t, main))
        last = " ".join(p["lines"][-2:])
        if main and not term.search(last) and idx[n] + 1 < len(names):
            todo.append((names[idx[n] + 1], True))
    return reached


def program(src: str) -> dict[str, Any]:
    raw = src
    up = _strip_lit(src.upper())
    pid = re.search(r"\bPROGRAM-ID\s*\.?\s*['\"]?([A-Z0-9][A-Z0-9-]*)", src.upper())
    name = pid.group(1) if pid else "(no PROGRAM-ID)"
    pd = re.search(r"\bPROCEDURE\s+DIVISION\b[^.]*\.", up)
    proc = up[pd.end():] if pd else ""
    proc_raw = src.upper()[pd.end():] if pd else ""
    lines = [ln for ln in src.splitlines() if ln.strip()]
    loc = len(lines)
    paras = _paragraphs(proc)
    pnames = {p["name"] for p in paras}
    for p in paras:
        p["perf"], p["go"] = _targets("\n".join(p["lines"]), pnames)
    reached = _reach(paras) if paras else set()
    dead = [p["name"] for p in paras if p["name"] not in reached and p["name"] != "(start)"]
    exits = {p["name"] for p in paras if re.fullmatch(r"\s*EXIT\s*\.?\s*", " ".join(p["lines"]) or "EXIT")}
    dead = [d for d in dead if d not in exits]
    # calls
    calls = []
    for m in re.finditer(r"\bCALL\s+(?:'([^']+)'|\"([^\"]+)\"|([A-Z0-9][A-Z0-9-]*))", src.upper()):
        lit = m.group(1) or m.group(2)
        if lit:
            calls.append({"to": lit.strip(), "how": "static"})
        else:
            var = m.group(3)
            vals = re.findall(rf"\bMOVE\s+'([^']+)'\s+TO\s+{re.escape(var)}\b", src.upper()) + re.findall(rf"\b{re.escape(var)}\b[^.]*?\bVALUE\s+'([^']+)'", src.upper())
            calls.append({"to": var, "how": "dynamic", "values": sorted({v.strip() for v in vals})[:10]})
    copies = sorted({m.group(1) for m in re.finditer(r"\bCOPY\s+['\"]?([A-Z0-9][A-Z0-9-]*)", up)})
    sql = []
    tables: set[str] = set()
    for m in re.finditer(r"EXEC\s+SQL\b(.*?)END-EXEC", src.upper(), re.S):
        body = " ".join(m.group(1).split())
        verb = (body.split() or ["?"])[0]
        if verb == "INCLUDE":
            inc = body.split()[1] if len(body.split()) > 1 else ""
            if inc:
                copies = sorted(set(copies) | {inc})
            continue
        for t in re.findall(r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([A-Z0-9_$#@]+(?:\.[A-Z0-9_$#@]+)?)", body):
            if t not in (":",) and not t.startswith(":") and t not in ("SQLCA",):
                if verb == "SELECT" and re.search(rf"\bINTO\s+{re.escape(t)}\b", body) and ":" in body.split("INTO")[1][:3]:
                    continue
                tables.add(t)
        sql.append({"verb": verb, "text": body[:160]})
    # host variables after SELECT ... INTO :X are not tables
    tables = {t for t in tables if not re.search(rf"INTO\s+:{re.escape(t)}", src.upper())}
    cics = []
    cics_prog: list[dict[str, str]] = []
    for m in re.finditer(r"EXEC\s+CICS\b(.*?)END-EXEC", src.upper(), re.S):
        body = " ".join(m.group(1).split())
        cmd = " ".join(body.split()[:2]) if body.split()[:1] in (["SEND"], ["RECEIVE"], ["HANDLE"], ["START"], ["RETURN"]) else (body.split() or ["?"])[0]
        cics.append({"cmd": cmd, "text": body[:140]})
        for kind in ("LINK", "XCTL"):
            mm = re.match(rf"{kind}\b.*?PROGRAM\s*\(\s*(?:'([^']+)'|([A-Z0-9-]+))\s*\)", body)
            if mm:
                cics_prog.append({"to": (mm.group(1) or mm.group(2)).strip(), "how": kind.lower() if mm.group(1) else kind.lower() + " (from data)"})
    files = []
    for m in re.finditer(r"\bSELECT\s+(?:OPTIONAL\s+)?([A-Z0-9][A-Z0-9-]*)\s+ASSIGN\s+(?:TO\s+)?([A-Z0-9'][A-Z0-9-']*)([^.]*)\.", up):
        rest = m.group(3)
        org = re.search(r"ORGANI[SZ]ATION\s+(?:IS\s+)?(\w+)", rest)
        fs = re.search(r"FILE\s+STATUS\s+(?:IS\s+)?([A-Z0-9-]+)", rest)
        files.append({"name": m.group(1), "dd": m.group(2).strip("'"), "org": org.group(1) if org else "SEQUENTIAL", "status": fs.group(1) if fs else ""})
    count = lambda rx: len(re.findall(rx, proc))   # noqa: E731
    stats = {"loc": loc, "paragraphs": len(paras), "statements": sum(count(rf"\b{v}\b") for v in VERBS if v not in ("GO", "EXEC")) + count(r"\bGO\s+TO\b"),
             "if": count(r"\bIF\b"), "when": count(r"\bWHEN\b"), "loops": count(r"\bPERFORM\b[^.\n]*\b(?:UNTIL|VARYING|TIMES)\b"),
             "goto": count(r"\bGO\s+TO\b"), "alter": count(r"\bALTER\b"), "next_sentence": count(r"\bNEXT\s+SENTENCE\b"),
             "compute": count(r"\bCOMPUTE\b"), "rounded": count(r"\bROUNDED\b"), "redefines": len(re.findall(r"\bREDEFINES\b", up[:pd.start()] if pd else up)),
             "comp3": len(re.findall(r"\bCOMP(?:UTATIONAL)?-3\b|\bPACKED-DECIMAL\b", up)), "float": len(re.findall(r"\bCOMP(?:UTATIONAL)?-[12]\b", up)),
             "odo": len(re.findall(r"\bDEPENDING\s+ON\b", up[:pd.start()] if pd else up)), "sort": count(r"\bSORT\b"),
             "string_ops": count(r"\b(?:STRING|UNSTRING|INSPECT)\b")}
    stats["decisions"] = stats["if"] + stats["when"] + stats["loops"]
    stats["complexity"] = 1 + stats["decisions"]
    data_issues: list[dict[str, Any]] = []
    try:
        lay = LY.analyse(src[:pd.start()] if pd else src)
        data = {"records": lay["records"][:30], "fields": lay["fields"], "kinds": lay["kinds"]}
        data_issues = [i for i in lay["issues"] if "two-digit year" in i["text"] or "6-digit date" in i["text"] or "IBM hexadecimal" in i["text"]]
    except LY.LayoutError:
        data = {"records": [], "fields": 0, "kinds": {}}
    iss: list[dict[str, Any]] = []
    add = lambda sev, area, text, fix="": iss.append({"sev": sev, "area": area, "text": f"{name}: {text}", "fix": fix})   # noqa: E731
    if stats["alter"]:
        add("bad", "Control flow", f"ALTER changes where a GO TO jumps while the program runs ({stats['alter']} time(s)) - no translation can read the flow from the text.",
            "Rewrite that logic as an explicit state variable first, with tests, then translate.")
    if stats["goto"]:
        sev = "warn" if stats["goto"] > max(3, stats["paragraphs"] // 4) else "info"
        add(sev, "Control flow", f"{stats['goto']} GO TO statement(s): jumps between paragraphs become loops and returns in the new language.", "Restructure the jumps into PERFORM / loops before or while translating.")
    if stats["next_sentence"]:
        add("warn", "Control flow", f"{stats['next_sentence']} NEXT SENTENCE: it jumps past the next period, not the END-IF - easy to translate wrong.", "Replace with CONTINUE inside explicit scope terminators and test.")
    if dead:
        add("info", "Dead code", f"{len(dead)} paragraph(s) that no PERFORM, GO TO or fall-through reaches: {', '.join(dead[:8])}.", "Check nothing jumps there by ALTER or a GO TO ... DEPENDING ON, then leave them out of the translation.")
    dyn = [c for c in calls if c["how"] == "dynamic"]
    if dyn:
        add("warn", "Calls", f"{len(dyn)} CALL(s) through a data name ({', '.join(c['to'] for c in dyn[:5])}) - the program called is decided while it runs" +
            (f"; values seen: {', '.join(v for c in dyn for v in c.get('values', []))}." if any(c.get("values") for c in dyn) else "."), "List every value the data name can hold so the map is complete.")
    if stats["comp3"]:
        add("info", "Numbers", f"{stats['comp3']} packed-decimal field(s): the new code must use a decimal type (BigDecimal / Decimal / decimal), never floating point.")
    if stats["float"]:
        add("warn", "Numbers", f"{stats['float']} COMP-1 / COMP-2 field(s): IBM hexadecimal floating point - results will differ in the last digits on IEEE hardware.")
    if stats["compute"] and stats["rounded"] < stats["compute"]:
        add("info", "Numbers", f"{stats['compute'] - stats['rounded']} COMPUTE without ROUNDED: COBOL cuts extra decimals off (truncates); the new code must cut too, not round.",
            "In Java: setScale(scale, RoundingMode.DOWN); in Python: quantize(..., rounding=ROUND_DOWN).")
    if stats["redefines"]:
        add("info", "Data", f"{stats['redefines']} REDEFINES: the same bytes read two ways.")
    if stats["odo"]:
        add("warn", "Data", f"{stats['odo']} OCCURS ... DEPENDING ON: records whose length follows the data.")
    for f in files:
        if not f["status"]:
            add("warn", "Files", f"file {f['name']} has no FILE STATUS - an I/O error may go unchecked (or end the program) in a way the new code will not copy.", "Add FILE STATUS and check it, or decide the new code's error handling on purpose.")
    if stats["sort"]:
        add("info", "Batch", f"{stats['sort']} SORT statement(s): the new sort must use the same collating order (EBCDIC sorts lower case before upper case before digits; ASCII the other way round).")
    iss += [{**i, "text": f"{name}: {i['text']}", "area": "Data"} for i in data_issues[:6]]
    online = bool(cics)
    send = sum(1 for c in cics if c["cmd"].startswith(("SEND", "RECEIVE")))
    return {"name": name, "loc": loc, "stats": stats, "paragraphs": [{"name": p["name"], "section": p["section"], "lines": len(p["lines"]),
                                                                       "perform": p["perf"], "goto": p["go"], "dead": p["name"] in dead} for p in paras][:500],
            "dead": dead, "calls": calls + [{"to": c["to"], "how": c["how"]} for c in cics_prog], "copies": copies, "sql": sql[:200], "tables": sorted(tables),
            "cics": cics[:200], "files": files, "online": online, "screens": send, "data": data, "issues": iss, "raw_len": len(raw),
            "proc_lines": len(proc_raw.splitlines())}


def analyse(text: str) -> dict[str, Any]:
    t = str(text or "")
    if len(t) > 10_000_000:
        raise CobolError("That is longer than 10 MB.")
    parts = split_programs(t)
    progs = [program(p) for p in parts]
    progs = [p for p in progs if p["stats"]["paragraphs"] or p["name"] != "(no PROGRAM-ID)"]
    if not progs:
        raise CobolError("No COBOL program found - paste the source with its IDENTIFICATION DIVISION and PROCEDURE DIVISION.")
    if len(progs) > 400:
        raise CobolError("Up to 400 programs at a time - use the Map page for a whole inventory.")
    issues = [i for p in progs for i in p["issues"]]
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    p0 = progs[0]
    verdict = (f"{p0['name']}: {p0['loc']:,} lines, {p0['stats']['paragraphs']} paragraphs, {p0['stats']['decisions']} decisions"
               + (f", {len(p0['dead'])} never reached" if p0["dead"] else "") + (", online (CICS)" if p0["online"] else ", batch")
               + (f"; {len(p0['tables'])} DB2 table(s)" if p0["tables"] else "") + "." if len(progs) == 1 else
               f"{len(progs)} programs, {sum(p['loc'] for p in progs):,} lines; {sum(len(p['dead']) for p in progs)} paragraph(s) never reached.")
    return {"programs": progs, "issues": issues, "counts": {k: sum(1 for i in issues if i["sev"] == k) for k in order}, "verdict": verdict,
            "note": ("Read from the source text: paths decided while the program runs (ALTER, a GO TO ... DEPENDING ON, a CALL through data) are "
                     "listed, not followed. 'Never reached' means no PERFORM, GO TO or fall-through in this program leads there.")}
