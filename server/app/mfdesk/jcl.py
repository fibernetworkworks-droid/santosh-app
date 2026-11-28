"""JCL read for modernization: jobs, steps, the program each step runs (the real one under IKJEFT01 / IKJEFT1B, from RUN PROGRAM),
procedures, DD statements, the datasets each step reads and writes, generation data groups, sort control cards, utilities, and what
breaks a rerun - a dataset created NEW and catalogued even when the step fails, steps that run after a failure. Pasted JCL is data."""
from __future__ import annotations

import re
from typing import Any


class JclError(ValueError):
    pass


UTIL = {"IEFBR14": "does nothing (allocates / deletes datasets through its DD statements)", "IEBGENER": "copies a dataset",
        "ICEGENER": "copies a dataset (DFSORT's IEBGENER)", "SORT": "sort / merge (DFSORT or SyncSort)", "ICEMAN": "sort (DFSORT)",
        "ICETOOL": "sort utility (DFSORT)", "SYNCSORT": "sort (SyncSort)", "IDCAMS": "VSAM / catalog work (define, delete, REPRO)",
        "IKJEFT01": "TSO in batch (usually runs a DB2 program)", "IKJEFT1B": "TSO in batch (usually runs a DB2 program)",
        "IEBCOPY": "copies library members", "IEHLIST": "lists catalog / volume entries", "DFSRRC00": "IMS region (runs an IMS program)",
        "FTP": "file transfer", "IEBUPDTE": "updates library members", "ADRDSSU": "dump / restore datasets", "DSNUTILB": "DB2 utility (load, unload, reorg)"}


def _statements(text: str) -> list[tuple[int, str, str, str, list[str]]]:
    """(line, name, op, operands, instream lines) - continuation lines joined."""
    out: list[tuple[int, str, str, str, list[str]]] = []
    lines = str(text or "").replace("\t", " ").splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()[:72]
        if not ln.startswith("//") or ln.startswith("//*"):
            i += 1
            continue
        m = re.match(r"^//(\S*)\s+(\S+)\s*(.*)$", ln)
        if not m:
            i += 1
            continue
        name, op, rest = m.group(1), m.group(2).upper(), m.group(3)
        ops = re.split(r"\s+(?=(?:[^']*'[^']*')*[^']*$)", rest.strip(), maxsplit=1)[0] if rest.strip() else ""
        no = i + 1
        while ops.endswith(",") and i + 1 < len(lines) and lines[i + 1].startswith("// ") and not lines[i + 1].startswith("//*"):
            i += 1
            nxt = lines[i].rstrip()[:72][2:].strip()
            ops += re.split(r"\s+(?=(?:[^']*'[^']*')*[^']*$)", nxt, maxsplit=1)[0]
        inst: list[str] = []
        if op == "DD" and re.match(r"^(?:\*|DATA)(?:,|\s|$)", ops.upper()):
            dlm = re.search(r"DLM=(?:'([^']+)'|(\S\S))", ops.upper())
            end = (dlm.group(1) or dlm.group(2)) if dlm else None
            while i + 1 < len(lines):
                nx = lines[i + 1]
                if (end and nx.startswith(end)) or (not end and (nx.startswith("//") or nx.startswith("/*"))):
                    break
                inst.append(nx.rstrip()[:80])
                i += 1
        out.append((no, name, op, ops, inst))
        i += 1
    return out


def _kw(ops: str) -> dict[str, str]:
    d: dict[str, str] = {}
    depth, cur, parts, q = 0, "", [], False
    for ch in ops:
        if ch == "'":
            q = not q
        if not q:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append(cur)
                cur = ""
                continue
        cur += ch
    if cur:
        parts.append(cur)
    for i, p in enumerate(parts):
        k, eq, v = p.partition("=")
        if eq:
            d[k.strip().upper()] = v.strip()
        elif i == 0:
            d["_"] = p.strip()
    return d


def analyse(text: str) -> dict[str, Any]:
    t = str(text or "")
    if len(t) > 5_000_000:
        raise JclError("That is longer than 5 MB.")
    st = _statements(t)
    if not any(op in ("JOB", "EXEC") for _, _, op, _, _ in st):
        raise JclError("No JCL found - paste the job: the //NAME JOB card, its EXEC steps and their DD statements.")
    jobs: list[dict[str, Any]] = []
    job: dict[str, Any] | None = None
    step: dict[str, Any] | None = None
    procs: list[str] = []
    for no, name, op, ops, inst in st:
        if op == "JOB":
            job = {"name": name, "line": no, "steps": [], "class": _kw(ops).get("CLASS", ""), "jcllib": []}
            jobs.append(job)
            step = None
        elif op == "JCLLIB" and job:
            job["jcllib"].append(_kw(ops).get("ORDER", ""))
        elif op == "PROC":
            procs.append(name)
        elif op == "EXEC":
            if job is None:
                job = {"name": "(no JOB card)", "line": no, "steps": [], "class": "", "jcllib": []}
                jobs.append(job)
            k = _kw(ops)
            pgm = k.get("PGM", "")
            proc = k.get("PROC", "") or ("" if pgm else k.get("_", ""))
            step = {"name": name or f"(step {len(job['steps']) + 1})", "line": no, "pgm": pgm.upper(), "proc": proc.upper(), "cond": k.get("COND", ""),
                    "parm": k.get("PARM", "")[:80], "dds": [], "runs": "", "sort": [], "sysin": [], "util": UTIL.get(pgm.upper(), "")}
            job["steps"].append(step)
        elif op == "DD" and step is not None:
            k = _kw(ops)
            dsn = k.get("DSN", k.get("DSNAME", "")).upper()
            disp = k.get("DISP", "").upper().strip("()")
            dparts = [x.strip() for x in disp.split(",")] + ["", "", ""]
            dd = {"name": name, "dsn": dsn, "disp": dparts[0] or ("NEW" if dsn.startswith("&&") else "NEW" if not dsn else ""), "normal": dparts[1], "abnormal": dparts[2],
                  "sysout": k.get("SYSOUT", ""), "instream": bool(inst), "dummy": k.get("_", "").upper() == "DUMMY",
                  "gdg": (re.search(r"\(([+-]?\d+)\)$", dsn) or [None, ""])[1] if dsn else "", "temp": dsn.startswith("&&")}
            step["dds"].append(dd)
            if inst:
                body = "\n".join(inst)
                if name.upper() in ("SYSIN", "SYSTSIN") or step["pgm"] in ("SORT", "ICEMAN", "SYNCSORT", "IKJEFT01", "IKJEFT1B", "IDCAMS"):
                    step["sysin"] += inst[:40]
                m = re.search(r"\bRUN\s+PROGRAM\s*\(\s*([A-Z0-9#@$]+)\s*\)(?:.*?PLAN\s*\(\s*([A-Z0-9#@$]+)\s*\))?", body.upper(), re.S)
                if m:
                    step["runs"] = m.group(1)
                    step["plan"] = m.group(2) or ""
                if step["pgm"] in ("SORT", "ICEMAN", "SYNCSORT", "ICETOOL") or name.upper() == "SYSIN":
                    for mm in re.finditer(r"\b(?:SORT|MERGE|INCLUDE|OMIT|OUTREC|INREC|SUM)\s+\S+", body.upper()):
                        step["sort"].append(mm.group(0)[:80])
    rows = []
    issues: list[dict[str, Any]] = []
    written: dict[str, str] = {}
    for jb in jobs:
        for s in jb["steps"]:
            prog = s["runs"] or s["pgm"] or s["proc"]
            reads = [d["dsn"] for d in s["dds"] if d["dsn"] and d["disp"] in ("SHR", "OLD") and not d["temp"]]
            writes = [d["dsn"] for d in s["dds"] if d["dsn"] and d["disp"] in ("NEW", "MOD") and d["normal"] != "DELETE" and not d["temp"]]
            deletes = [d["dsn"] for d in s["dds"] if d["dsn"] and d["normal"] == "DELETE" and not d["temp"]]
            for d in s["dds"]:
                if d["dsn"] and d["disp"] == "NEW" and d["normal"] == "CATLG" and d["abnormal"] in ("", "CATLG", "KEEP") and not d["temp"]:
                    issues.append({"sev": "warn", "area": "Rerun", "text": f"{jb['name']}.{s['name']}: {d['dsn']} is created NEW and kept catalogued if the step fails {'(NEW,CATLG)' if not d['abnormal'] else '(NEW,CATLG,' + d['abnormal'] + ')'} - a rerun stops on 'dataset already exists'.",
                                   "fix": "DISP=(NEW,CATLG,DELETE), or a delete step (IEFBR14 / IDCAMS DELETE) before it."})
                if d["disp"] == "OLD":
                    issues.append({"sev": "info", "area": "Datasets", "text": f"{jb['name']}.{s['name']}: {d['dsn']} opened OLD - exclusive use while the job runs; the new world needs the same lock (or none, on purpose)."}) if not any("opened OLD" in i["text"] and d["dsn"] in i["text"] for i in issues) else None
            for w in writes:
                written[w] = f"{jb['name']}.{s['name']}"
            rows.append({"job": jb["name"], "step": s["name"], "program": prog, "via": ("IKJEFT01 RUN PROGRAM" if s["runs"] else "PGM" if s["pgm"] else "PROC" if s["proc"] else ""),
                         "util": s["util"] if not s["runs"] else "", "cond": s["cond"], "reads": reads, "writes": writes, "deletes": deletes,
                         "temp": [d["dsn"] for d in s["dds"] if d["temp"]], "gdg": [f"{d['dsn']}" for d in s["dds"] if d["gdg"]], "sort": s["sort"][:10],
                         "sysin": s["sysin"][:12], "dds": [{k: d[k] for k in ("name", "dsn", "disp", "normal", "abnormal", "sysout", "instream", "dummy")} for d in s["dds"]][:60],
                         "plan": s.get("plan", "")})
            if s["proc"] and not s["pgm"]:
                issues.append({"sev": "info", "area": "Procedures", "text": f"{jb['name']}.{s['name']} runs the procedure {s['proc']} - paste the PROC too, or its programs stay off the map."}) if s["proc"] not in procs else None
            if s["sort"]:
                issues.append({"sev": "info", "area": "Batch", "text": f"{jb['name']}.{s['name']}: a sort ({'; '.join(s['sort'][:3])}) - the new sort needs the same keys, the same order of equal keys (EQUALS) and the same collating order (EBCDIC, not ASCII)."})
    gdgs = sorted({d["dsn"].split("(")[0] for jb in jobs for s in jb["steps"] for d in s["dds"] if d["gdg"]})
    if gdgs:
        issues.append({"sev": "info", "area": "Datasets", "text": f"{len(gdgs)} generation data group(s) ({', '.join(gdgs[:4])}): (+1) makes a new generation, (0) reads the latest - the new world needs the same versioning (dated files or object versions) and the same number kept."})
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda x: order[x["sev"]])
    progs = sorted({r["program"] for r in rows if r["program"] and r["program"] not in UTIL and r["via"] != "PROC"})
    datasets = sorted({d for r in rows for d in r["reads"] + r["writes"]})
    flows = [{"dsn": d, "from": written[d], "to": f"{r['job']}.{r['step']}"} for r in rows for d in r["reads"] if d in written and written[d] != f"{r['job']}.{r['step']}"]
    return {"jobs": [{"name": j["name"], "steps": len(j["steps"]), "class": j["class"]} for j in jobs], "steps": rows[:1000], "programs": progs,
            "utilities": sorted({r["program"] for r in rows if r["program"] in UTIL}), "datasets": datasets[:2000], "gdgs": gdgs, "flows": flows[:500],
            "procs": procs, "issues": issues, "counts": {k: sum(1 for i in issues if i["sev"] == k) for k in order},
            "verdict": f"{len(jobs)} job(s), {len(rows)} step(s): {len(progs)} of your program(s), {len({r['program'] for r in rows if r['program'] in UTIL})} utilit(ies), {len(datasets)} dataset(s).",
            "note": "Read from the JCL text: symbolic parameters (&NAME) are not filled in and procedures are expanded only when pasted. The scheduler (which job runs after which) is not in JCL."}
