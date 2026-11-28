"""Security scanner reports read together the way a security engineer triages them: SARIF (CodeQL, Semgrep, any SARIF tool), Trivy,
Grype, Semgrep JSON, OWASP ZAP JSON, or a CSV with an id, a severity and where - each finding brought to one shape, duplicates across
tools merged, counted by severity, tool, rule and place; the package upgrades that close the most findings; and, when an older scan
is given after a '## baseline' line, what is new, what was fixed and what is still open, with the date each new one is due under her
own fix-time rules. Nothing is run: the reports are what her tools already produced."""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any

from ..mldesk.table import TableError, read
from .common import SecInputError, col, day, finder, finish


class FindingsError(SecInputError):
    pass


SEVS = ("critical", "high", "medium", "low", "info")
RANK = {s: i for i, s in enumerate(SEVS)}


def _sev(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in ("critical", "crit", "blocker"):
        return "critical"
    if s in ("high", "error", "major", "3"):
        return "high"
    if s in ("medium", "moderate", "warning", "warn", "2"):
        return "medium"
    if s in ("low", "minor", "note", "1"):
        return "low"
    try:   # a CVSS-style number (SARIF security-severity)
        x = float(s)
        return "critical" if x >= 9 else "high" if x >= 7 else "medium" if x >= 4 else "low" if x > 0 else "info"
    except ValueError:
        return "info" if s in ("info", "informational", "none", "0", "unknown", "negligible", "") else "medium"


def _sarif(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for run in d.get("runs") or []:
        tool = ((run.get("tool") or {}).get("driver") or {}).get("name") or "SARIF"
        rules = {r.get("id"): r for r in ((run.get("tool") or {}).get("driver") or {}).get("rules") or []}
        for x in run.get("results") or []:
            rid = x.get("ruleId") or (x.get("rule") or {}).get("id") or "?"
            rule = rules.get(rid) or {}
            props = rule.get("properties") or {}
            sev = _sev(props.get("security-severity")) if props.get("security-severity") else _sev(x.get("level") or (rule.get("defaultConfiguration") or {}).get("level") or "warning")
            loc = ((x.get("locations") or [{}])[0].get("physicalLocation") or {})
            uri = (loc.get("artifactLocation") or {}).get("uri") or ""
            line = (loc.get("region") or {}).get("startLine")
            msg = ((x.get("message") or {}).get("text") or (rule.get("shortDescription") or {}).get("text") or rid)
            out.append({"tool": tool, "rule": rid, "sev": sev, "title": msg[:240], "where": f"{uri}:{line}" if line else uri, "pkg": "", "fixed_in": "",
                        "cwe": ", ".join(t for t in props.get("tags") or [] if "cwe" in str(t).lower())[:80]})
    return out


def _trivy(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for r in d.get("Results") or []:
        tgt = r.get("Target") or ""
        for v in r.get("Vulnerabilities") or []:
            out.append({"tool": "Trivy", "rule": v.get("VulnerabilityID") or "?", "sev": _sev(v.get("Severity")), "title": (v.get("Title") or v.get("VulnerabilityID") or "")[:240],
                        "where": tgt, "pkg": f"{v.get('PkgName', '')}@{v.get('InstalledVersion', '')}", "fixed_in": v.get("FixedVersion") or "", "cwe": ""})
        for m in r.get("Misconfigurations") or []:
            if m.get("Status") == "PASS":
                continue
            out.append({"tool": "Trivy", "rule": m.get("ID") or m.get("AVDID") or "?", "sev": _sev(m.get("Severity")), "title": (m.get("Title") or "")[:240],
                        "where": tgt + (f":{(m.get('CauseMetadata') or {}).get('StartLine')}" if (m.get("CauseMetadata") or {}).get("StartLine") else ""), "pkg": "", "fixed_in": "", "cwe": ""})
        for s in r.get("Secrets") or []:
            out.append({"tool": "Trivy", "rule": s.get("RuleID") or "secret", "sev": _sev(s.get("Severity")), "title": (s.get("Title") or "A secret in the code")[:240],
                        "where": f"{tgt}:{s.get('StartLine')}", "pkg": "", "fixed_in": "", "cwe": ""})
    return out


def _grype(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for m in d.get("matches") or []:
        v, a = m.get("vulnerability") or {}, m.get("artifact") or {}
        fx = (v.get("fix") or {}).get("versions") or []
        out.append({"tool": "Grype", "rule": v.get("id") or "?", "sev": _sev(v.get("severity")), "title": (v.get("description") or v.get("id") or "")[:240],
                    "where": ", ".join(l.get("path", "") for l in a.get("locations") or [])[:160], "pkg": f"{a.get('name', '')}@{a.get('version', '')}",
                    "fixed_in": fx[0] if fx else "", "cwe": ""})
    return out


def _semgrep(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for x in d.get("results") or []:
        ex = x.get("extra") or {}
        cwe = (ex.get("metadata") or {}).get("cwe") or ""
        out.append({"tool": "Semgrep", "rule": x.get("check_id") or "?", "sev": _sev(ex.get("severity")), "title": (ex.get("message") or "")[:240],
                    "where": f"{x.get('path', '')}:{(x.get('start') or {}).get('line', '')}", "pkg": "", "fixed_in": "", "cwe": (", ".join(cwe) if isinstance(cwe, list) else str(cwe))[:80]})
    return out


def _zap(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for site in d.get("site") or []:
        for a in site.get("alerts") or []:
            rc = str(a.get("riskcode", ""))
            sev = {"3": "high", "2": "medium", "1": "low", "0": "info"}.get(rc, _sev(a.get("riskdesc", "").split(" ")[0]))
            inst = a.get("instances") or [{}]
            out.append({"tool": "ZAP", "rule": str(a.get("pluginid") or a.get("alertRef") or "?"), "sev": sev, "title": (a.get("name") or a.get("alert") or "")[:240],
                        "where": (inst[0].get("uri") or site.get("@name") or "")[:200] + (f" (+{len(inst) - 1})" if len(inst) > 1 else ""), "pkg": "", "fixed_in": "",
                        "cwe": f"CWE-{a['cweid']}" if a.get("cweid") not in (None, "", "-1", "0") else ""})
    return out


def _csv(text: str) -> list[dict[str, Any]]:
    head, rows = read(text, "The findings")
    ix = {"rule": col(head, r"id", r"ruleid", r"rule", r"cve", r"vulnerabilityid", r"check"), "sev": col(head, r"severity", r"sev", r"risk", r"level", r"priority"),
          "title": col(head, r"title", r"name", r"description", r"message", r"summary"), "where": col(head, r"file", r"path", r"location", r"where", r"url", r"asset", r"target"),
          "line": col(head, r"line", r"startline"), "pkg": col(head, r"package", r"pkg", r"component", r"library"), "ver": col(head, r"version", r"installedversion"),
          "fix": col(head, r"fixedversion", r"fixedin", r"fix", r"fixversion"), "tool": col(head, r"tool", r"scanner", r"source")}
    if ix["sev"] is None or (ix["rule"] is None and ix["title"] is None):
        raise FindingsError("The CSV needs a severity column and an id or title column.")
    g = lambda r, k: r[ix[k]] if ix[k] is not None else ""   # noqa: E731
    return [{"tool": g(r, "tool") or "CSV", "rule": g(r, "rule") or g(r, "title")[:60], "sev": _sev(g(r, "sev")), "title": (g(r, "title") or g(r, "rule"))[:240],
             "where": g(r, "where") + (f":{g(r, 'line')}" if g(r, "line") else ""), "pkg": (g(r, "pkg") + (f"@{g(r, 'ver')}" if g(r, "ver") else "")) if g(r, "pkg") else "",
             "fixed_in": g(r, "fix"), "cwe": ""} for r in rows]


def parse(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    t = str(text or "").strip()
    if not t:
        raise FindingsError("Paste a scanner report: SARIF, Trivy, Grype, Semgrep or ZAP JSON, or a CSV.")
    parts = [p for p in re.split(r"(?m)^##\s+.*$", t) if p.strip()] if re.search(r"(?m)^##\s+", t) else [t]
    out, kinds = [], []
    for p in parts:
        p = p.strip()
        if p[:1] in "[{":
            try:
                d = json.loads(p)
            except ValueError as e:
                raise FindingsError(f"The JSON could not be read: {e}")
            if isinstance(d, dict) and "runs" in d:
                f, k = _sarif(d), "SARIF"
            elif isinstance(d, dict) and "Results" in d:
                f, k = _trivy(d), "Trivy"
            elif isinstance(d, dict) and "matches" in d:
                f, k = _grype(d), "Grype"
            elif isinstance(d, dict) and "results" in d and isinstance(d["results"], list):
                f, k = _semgrep(d), "Semgrep"
            elif isinstance(d, dict) and "site" in d:
                f, k = _zap(d), "ZAP"
            else:
                raise FindingsError("This JSON is not SARIF, Trivy, Grype, Semgrep or ZAP output.")
        else:
            try:
                f, k = _csv(p), "CSV"
            except TableError as e:
                raise FindingsError(str(e))
        out += f
        kinds.append(k)
    return out, kinds


def _key(f: dict[str, Any]) -> str:
    """The same finding from two tools or two scans: a CVE on a package, else the rule at a place."""
    if re.match(r"(CVE|GHSA|GO|PYSEC|RUSTSEC)-", f["rule"], re.I) and f["pkg"]:
        return f"{f['rule'].upper()}|{f['pkg'].split('@')[0].lower()}"
    return f"{f['rule'].lower()}|{re.sub(r'^(file://)?\.?/', '', f['where'].lower())}"


def _merge(fs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    for f in fs:
        k = _key(f)
        if k in by:
            o = by[k]
            if RANK[f["sev"]] < RANK[o["sev"]]:
                o["sev"] = f["sev"]
            if f["tool"] not in o["tools"]:
                o["tools"].append(f["tool"])
            o["fixed_in"] = o["fixed_in"] or f["fixed_in"]
        else:
            by[k] = {**f, "key": k, "tools": [f["tool"]]}
    return by


SLA_DEFAULT = {"critical": 7, "high": 30, "medium": 90, "low": 180}


def _ver(v: str) -> tuple:
    return tuple((0, int(x), "") if x.isdigit() else (1, 0, x) for x in re.split(r"[.\-+:~]", str(v or "")) if x)


def analyse(text: str, sla: dict[str, float] | None = None, scan_date: Any = None) -> dict[str, Any]:
    t = str(text or "")
    m = re.search(r"(?mi)^##\s*baseline\b.*$", t)
    cur_t, base_t = (t[:m.start()], t[m.end():]) if m else (t, "")
    fs, kinds = parse(cur_t)
    cur = _merge(fs)
    base = _merge(parse(base_t)[0]) if base_t.strip() else None
    issues, add = finder()
    sl = {**SLA_DEFAULT, **{k: v for k, v in (sla or {}).items() if v}}
    sd = day(scan_date) if scan_date else date.today()
    rows = sorted(cur.values(), key=lambda f: (RANK[f["sev"]], f["rule"]))
    for f in rows:
        f["status"] = "new" if base is not None and f["key"] not in base else "open"
        if f["sev"] in sl and (base is None or f["status"] == "new"):
            f["due"] = (sd + timedelta(days=int(sl[f["sev"]]))).isoformat()
    fixed = sorted((base[k] for k in base if k not in cur), key=lambda f: RANK[f["sev"]]) if base is not None else []
    counts = {s: sum(1 for f in rows if f["sev"] == s) for s in SEVS}
    pk: dict[str, dict[str, Any]] = {}
    for f in rows:
        if f["pkg"] and f["fixed_in"]:
            n = f["pkg"].split("@")[0]
            p = pk.setdefault(n, {"pkg": n, "now": f["pkg"].split("@", 1)[1] if "@" in f["pkg"] else "", "to": "", "closes": 0, "worst": "info"})
            cands = [v for v in re.split(r"[,\s|]+", f["fixed_in"].strip()) if v]
            above = sorted((v for v in cands if not p["now"] or _ver(v) > _ver(p["now"])), key=_ver)
            first = above[0] if above else cands[0]
            if not p["to"] or _ver(first) > _ver(p["to"]):
                p["to"] = first
            p["closes"] += 1
            if RANK[f["sev"]] < RANK[p["worst"]]:
                p["worst"] = f["sev"]
    ups = sorted(pk.values(), key=lambda p: (RANK[p["worst"]], -p["closes"]))
    def tally(k: str) -> list[dict[str, Any]]:
        d: dict[str, list[int]] = {}
        for f in rows:
            keys = f["tools"] if k == "tools" else [f[k] or "(none)"]
            for x in keys:
                d.setdefault(x, [0, 0])
                d[x][0] += 1
                d[x][1] += RANK[f["sev"]] <= 1
        return [{"name": n, "count": c[0], "serious": c[1]} for n, c in sorted(d.items(), key=lambda kv: (-kv[1][1], -kv[1][0]))[:15]]
    if counts["critical"] or counts["high"]:
        add("bad" if counts["critical"] else "warn", "Serious findings", f"{counts['critical']} critical and {counts['high']} high finding(s).",
            f"Fix critical within {sl['critical']:g} days and high within {sl['high']:g} (your rules).")
    fixable = sum(1 for f in rows if f["fixed_in"])
    if ups:
        u = ups[0]
        add("info", "Upgrades", f"{len(ups)} package upgrade(s) close {fixable} finding(s); first {u['pkg']} {u['now']} -> {u['to']} ({u['closes']}, worst {u['worst']}).",
            "Upgrade the packages in this order, then scan again.")
    if base is not None:
        new = [f for f in rows if f["status"] == "new"]
        nser = [f for f in new if RANK[f["sev"]] <= 1]
        if nser:
            add("bad", "New serious", f"{len(nser)} new critical / high finding(s) since the baseline, e.g. {nser[0]['rule']} at {nser[0]['where'] or nser[0]['pkg']}.",
                "Stop these before they ship.")
        add("info", "Since the baseline", f"{len(new)} new, {len(fixed)} fixed, {len(rows) - len(new)} still open.", "")
    dup = len(fs) - len(cur)
    res = {"kinds": kinds, "raw": len(fs), "findings": len(rows), "merged": dup, "counts_sev": counts, "rows": rows[:600], "fixed": fixed[:200],
           "new": sum(1 for f in rows if f.get("status") == "new") if base is not None else None, "baseline": base is not None,
           "upgrades": ups[:40], "fixable": fixable, "by_tool": tally("tools"), "by_rule": tally("rule"), "by_where": tally("where"), "sla": sl, "scan_date": sd.isoformat(),
           "verdict": f"{len(rows)} finding(s): {counts['critical']} critical, {counts['high']} high, {counts['medium']} medium"
                      + (f"; {sum(1 for f in rows if f.get('status') == 'new')} new, {len(fixed)} fixed" if base is not None else "")}
    res["note"] = ("Severities are the tools' own (a SARIF security-severity number mapped the CVSS way). Due dates are the scan date plus your fix-time rules. "
                   "A finding the tools did not report is not proof it is absent.")
    return finish(res, issues)
